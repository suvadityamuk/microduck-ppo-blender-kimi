"""HF Jobs for the Microduck experiment: per-world PPO training (+ CPU evaluation in the same job).

    uv run python scripts/duck_jobs.py bundle
    uv run python scripts/duck_jobs.py train <world> [<world> ...] --iters 1500 [--flavor a100-large] \
        --tag v3 --extra "--inside-fraction 0.5 --ang-std 0.32 --ang-weight 3.0 --warm checkpoints_cache/duck/policies/velstand.onnx"
    uv run python scripts/duck_jobs.py status

Repos default to <your HF user>/duck-worlds-code (private model repo, the code bundle) and
<your HF user>/duck-worlds-results (private dataset, run outputs); override with DUCK_CODE_REPO / DUCK_RESULTS_REPO.

Each job: pytorch CUDA image -> uv -> Pollen's microduck_rl at a pinned commit (mjlab, BAM, rsl_rl) -> our code bundle
from the Hub -> rl/train_world.py -> scripts/duck_eval.py (stock vs specialist, CPU MuJoCo + BAM) -> results to
the dataset repo RESULTS_REPO/<run>/. A background loop uploads checkpoints while training runs.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import time
from pathlib import Path

from huggingface_hub import HfApi, get_token


def _user():
    return HfApi().whoami()["name"]


CODE_REPO = os.environ.get("DUCK_CODE_REPO") or f"{_user()}/duck-worlds-code"
RESULTS_REPO = os.environ.get("DUCK_RESULTS_REPO") or f"{_user()}/duck-worlds-results"
IMAGE = "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime"
MICRODUCK_RL_COMMIT = "b02fdea4902c2b93b7d34a83a6f05da4ececb7d3"
ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data" / "duck_jobs.json"


def bundle():
    api = HfApi()
    api.create_repo(CODE_REPO, repo_type="model", private=True, exist_ok=True)
    api.create_repo(RESULTS_REPO, repo_type="dataset", private=True, exist_ok=True)
    api.upload_folder(repo_id=CODE_REPO, folder_path=str(ROOT), commit_message="code + worlds bundle",
                      allow_patterns=["src/**", "rl/**", "scripts/**", "worlds_duck/**", "checkpoints_cache/duck/policies/*.onnx", "third_party/microduck_rl/src/mjlab_microduck/robot/microduck/**"],
                      ignore_patterns=["**/__pycache__/**", "**/*.pyc"],
                      delete_patterns=["src/**", "rl/**", "scripts/**", "worlds_duck/**"])
    print("bundled ->", CODE_REPO)


SETUP = f"""
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -qq -y --no-install-recommends git curl ca-certificates libgl1 libegl1 >/dev/null
curl -LsSf https://astral.sh/uv/0.11.30/install.sh | sh >/dev/null
export PATH=$HOME/.local/bin:$PATH
git clone -q https://github.com/pollen-robotics/microduck_rl /microduck_rl
cd /microduck_rl && git checkout -q {MICRODUCK_RL_COMMIT}
uv sync --no-progress -q 2>&1 | tail -2
uv pip install -q --python /microduck_rl/.venv/bin/python scipy pillow imageio imageio-ffmpeg
export MICRODUCK_RL=/microduck_rl
PY=/microduck_rl/.venv/bin/python
$PY -c "from huggingface_hub import snapshot_download; snapshot_download('{CODE_REPO}', local_dir='/code')" >/dev/null
cd /code
"""


def train_job(worlds, iters, num_envs, flavor, timeout, tag, eval_eps, extra=""):
    runs = []
    for w in worlds:
        name = f"{tag}/{Path(w).name.strip('_')}"
        runs.append((w, name))
    body = []
    for w, name in runs:
        body.append(f"""
echo "[job] training {w}"
mkdir -p /out/{name}
( while true; do sleep 300; $PY scripts/duck_jobs.py _upload /out/{name} {name} || true; done ) & UP=$!
$PY rl/train_world.py worlds_duck/{w} --iters {iters} --num-envs {num_envs} --out /out/{name} {extra} 2>&1 | grep -v "Patch\\|Module mujoco_warp" | tee /out/{name}/train.log | grep -E "Learning iteration|Mean reward|Episode_Termination/fell|error_vel|done|Error|Traceback" || true
kill $UP || true
echo "[job] selecting a checkpoint for {w}"
$PY scripts/select_ckpt.py /out/{name} worlds_duck/{w} --episodes 8 2>&1 | grep "\\[select\\]" || true
echo "[job] probing {w}"
$PY scripts/duck_probe.py worlds_duck/{w} checkpoints_cache/duck/policies/velstand.onnx /out/{name}/policy.onnx 2>&1 | grep -v "Patch\\|^BAM" | tee /out/{name}/probe.txt | grep -v PROBE_JSON || true
echo "[job] evaluating {w}"
MUJOCO_GL=egl $PY scripts/duck_eval.py worlds_duck/{w} --policies stock=checkpoints_cache/duck/policies/velstand.onnx specialist=/out/{name}/policy.onnx --episodes {eval_eps} --seed0 1000 --out /out/{name}/eval 2>&1 | tail -30 || true
$PY scripts/duck_jobs.py _upload /out/{name} {name}
""")
    script = SETUP + "\n".join(body) + "\necho JOB_DONE\n"
    api = HfApi()
    job = api.run_job(image=IMAGE, command=["bash", "-c", script], flavor=flavor, timeout=timeout,
                      secrets={"HF_TOKEN": get_token()}, labels={"project": "duck-worlds", "kind": "train"})
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    for w, name in runs:
        log[name] = {"job": job.id, "world": w, "iters": iters, "flavor": flavor, "submitted": time.strftime("%Y-%m-%d %H:%M")}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(log, indent=2))
    print(f"job {job.id} ({flavor}) -> {[n for _, n in runs]}")
    return job.id


def _upload(local, name):
    HfApi().upload_folder(repo_id=RESULTS_REPO, repo_type="dataset", folder_path=local, path_in_repo=name,
                          commit_message=f"{name}")


def status():
    api = HfApi()
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    seen = {}
    for name, info in log.items():
        j = info["job"]
        if j not in seen:
            try:
                seen[j] = api.inspect_job(job_id=j).status.stage
            except Exception as e:  # noqa: BLE001
                seen[j] = f"? {e}"
        print(f"{name:60s} {j}  {seen[j]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bundle")
    sub.add_parser("status")
    t = sub.add_parser("train")
    t.add_argument("worlds", nargs="+")
    t.add_argument("--iters", type=int, default=1500)
    t.add_argument("--num-envs", type=int, default=4096)
    t.add_argument("--flavor", default="a100-large")
    t.add_argument("--timeout", default="6h")
    t.add_argument("--tag", default="v1")
    t.add_argument("--eval-episodes", type=int, default=20)
    t.add_argument("--extra", default="", help="extra args for rl/train_world.py")
    u = sub.add_parser("_upload")
    u.add_argument("local")
    u.add_argument("name")
    a = ap.parse_args()
    if a.cmd == "bundle":
        bundle()
    elif a.cmd == "status":
        status()
    elif a.cmd == "train":
        train_job(a.worlds, a.iters, a.num_envs, a.flavor, a.timeout, a.tag, a.eval_episodes, a.extra)
    else:
        _upload(a.local, a.name)


if __name__ == "__main__":
    main()
