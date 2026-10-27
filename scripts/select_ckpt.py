"""Pick the deployable checkpoint of a world-specialised walking policy.

1. Candidates: model_{100,200,300,600,900,1200}.pt (converted to ONNX) and the final policy.
2. Gate on the command-tracking probe (CPU sim, BAM): it must turn the right way while walking
   (yaw > +0.15 rad/s for a left command, < -0.15 for a right one) and drift < 0.15 rad/s when told to go straight.
3. Rank the survivors by task success over --episodes per task on selection seeds (disjoint from the final eval).
Writes <run>/selection.json and copies the winner to <run>/policy.onnx (the trained final weights stay in
final.onnx). If nothing passes the gate, selection.json says so and policy.onnx is removed.

    python scripts/select_ckpt.py <run_dir> worlds_duck/<w> [--episodes 8]
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from duck_probe import probe  # noqa: E402
from pt_to_onnx import convert  # noqa: E402

TURN_MIN, DRIFT_MAX = 0.15, 0.15


def passes(p):
    return p["fwd+left"]["yaw_rate"] > TURN_MIN and p["fwd+right"]["yaw_rate"] < -TURN_MIN and abs(p["fwd0.3"]["yaw_rate"]) < DRIFT_MAX


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("world")
    ap.add_argument("--episodes", type=int, default=8)
    a = ap.parse_args()
    run = Path(a.run)
    final = run / "final.onnx"
    if not final.exists():
        shutil.copy(run / "policy.onnx", final)
    cands = {}
    for n in (100, 200, 300, 600, 900, 1200):
        pt = run / f"model_{n}.pt"
        if pt.exists():
            convert(str(pt), str(run / f"ckpt_{n}.onnx"))
            cands[f"c{n}"] = run / f"ckpt_{n}.onnx"
    cands["final"] = final
    probes = {k: probe(a.world, str(p)) for k, p in cands.items()}
    ok = [k for k, p in probes.items() if passes(p)]
    print("[select] probe gate passed:", ok, flush=True)
    res = {"probes": probes, "passed": ok, "selected": None}
    if ok:
        specs = [f"{k}={cands[k]}" for k in ok]
        subprocess.run([sys.executable, str(ROOT / "scripts" / "duck_eval.py"), a.world, "--policies", *specs, "--episodes",
                        str(a.episodes), "--seed0", "5000", "--videos", "0", "--out", str(run / "select")], check=False)
        s = json.loads((run / "select" / "summary.json").read_text()) if (run / "select" / "summary.json").exists() else {}
        if s:
            best = max(s, key=lambda k: s[k]["_mean_success"])
            res.update(selected=best, selection_success={k: v["_mean_success"] for k, v in s.items()})
            shutil.copy(cands[best], run / "policy.onnx")
    if res["selected"] is None and (run / "policy.onnx").exists():
        (run / "policy.onnx").unlink()
    (run / "selection.json").write_text(json.dumps(res, indent=2))
    print("[select] selected:", res["selected"], res.get("selection_success"), flush=True)


if __name__ == "__main__":
    main()
