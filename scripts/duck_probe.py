"""Command-tracking probe for low-level walking policies in the CPU sim (BAM): fixed commands, measured response.

    python scripts/duck_probe.py worlds_duck/<w> a.onnx b.onnx ...
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from robo_worlds.duck_sim import DuckSim  # noqa: E402

CMDS = {"fwd0.3": (0.3, 0, 0), "fwd+left": (0.3, 0, 0.5), "fwd+right": (0.3, 0, -0.5), "turnL": (0, 0, 0.8), "turnR": (0, 0, -0.8)}


def probe(world, onnx, start=None, seconds=4.0, seeds=(0, 1)):
    sim = DuckSim(world, onnx, dr=False)
    start = start or sim.scene["tasks"][0]["start"]
    out = {}
    for name, c in CMDS.items():
        v, w, fell = [], [], 0
        for s in seeds:
            sim.reset(next(iter(sim.tasks)), seed=s, start=start)
            p0, y0 = sim.pose()
            yaws, prev = 0.0, y0
            for _ in range(int(seconds * 10)):
                sim.step(np.r_[c, np.zeros(10)])
                _, y = sim.pose()
                yaws += math.remainder(y - prev, 2 * math.pi)
                prev = y
            p, _ = sim.pose()
            d = p[:2] - p0[:2]
            # forward speed along the mean heading
            h = y0 + yaws / 2
            v.append(float(d @ np.array([math.cos(h), math.sin(h)])) / seconds)
            w.append(yaws / seconds)
            fell += sim.state.failure == "fell"
        out[name] = {"v_fwd": round(float(np.mean(v)), 3), "yaw_rate": round(float(np.mean(w)), 2), "fell": fell}
    return out


if __name__ == "__main__":
    world = sys.argv[1]
    res = {Path(p).stem: probe(world, p) for p in sys.argv[2:]}
    for k, r in res.items():
        print(f"{k:16s} " + "  ".join(f"{n}: v={x['v_fwd']:+.3f} w={x['yaw_rate']:+.2f}{' F' * x['fell']}" for n, x in r.items()))
    print("PROBE_JSON " + json.dumps(res))
