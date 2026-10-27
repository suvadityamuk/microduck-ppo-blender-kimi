"""Evaluate low-level walking policies on a world's tasks: the planner expert gives the commands, each policy walks.

    python scripts/duck_eval.py worlds_duck/<w> --policies stock=.../velstand.onnx specialist=runs/<w>/policy.onnx \
        --episodes 10 --out results/<w>/eval [--videos 1]

Writes summary.json ({policy: {task: {success, failures, mean_time}}}) and, if rendering works, one chase-camera
video per policy and task.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from robo_worlds.duck_sim import DuckSim  # noqa: E402
from robo_worlds.expert import Expert  # noqa: E402


def run(world, policy, episodes, out, videos, seed0=1000, tasks=None):
    sim = DuckSim(world, policy, seed=seed0, dr=True)
    ex = Expert(sim)
    res = {}
    for tn in (tasks or list(sim.tasks)):
        succ, times, fails = 0, [], Counter()
        for ep in range(episodes):
            sim.reset(tn, seed=seed0 + ep)
            ex.reset()
            frames = []
            rec = videos and ep < videos
            while True:
                _, done, info = sim.step(ex.act())
                if rec:
                    try:
                        frames.append(sim.render("chase", (360, 480)))
                    except Exception as e:  # noqa: BLE001  no GL on this machine
                        print("render failed:", e)
                        rec = False
                if done:
                    break
            if info["success"]:
                succ += 1
                times.append(sim.time)
            else:
                fails[info["failure"].split(" ")[0] if info["failure"] else "?"] += 1
            if rec and frames:
                import imageio.v2 as iio

                iio.mimwrite(out / f"{Path(policy).stem}_{tn}_{ep}.mp4", frames, fps=10, quality=7)
        res[tn] = {"success": succ / episodes, "episodes": episodes, "failures": dict(fails),
                   "mean_time": float(np.mean(times)) if times else None}
        print(f"  {Path(policy).name:24s} {tn:28s} {succ}/{episodes}  {dict(fails)}", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world")
    ap.add_argument("--policies", nargs="+", required=True, help="name=path.onnx")
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--out", required=True)
    ap.add_argument("--videos", type=int, default=1)
    ap.add_argument("--tasks", nargs="*")
    ap.add_argument("--seed0", type=int, default=1000)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for spec in a.policies:
        name, path = spec.split("=", 1)
        if not Path(path).exists():
            print(f"skip {name}: {path} missing")
            continue
        t = time.time()
        print(f"[eval] {name}: {path}", flush=True)
        try:
            summary[name] = run(a.world, path, a.episodes, out, a.videos, tasks=a.tasks, seed0=a.seed0)
        except Exception as e:  # noqa: BLE001  one broken policy must not sink the comparison
            print(f"[eval] {name}: FAILED {type(e).__name__}: {e}", flush=True)
            continue
        summary[name]["_mean_success"] = float(np.mean([v["success"] for k, v in summary[name].items() if not k.startswith("_")]))
        print(f"[eval] {name}: mean success {summary[name]['_mean_success']:.2f} ({time.time() - t:.0f}s)", flush=True)
        (out / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
