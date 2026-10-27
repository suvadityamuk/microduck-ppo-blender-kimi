"""Seam test: lower the X-ray platform deck by DZ metres (runtime only) and re-run the X-ray task for both walkers.

    third_party/microduck_rl/.venv/bin/python results/recheck/xray_seam_test.py 0.002 20
"""
import sys, json, mujoco
sys.path.insert(0, "src")
from robo_worlds.duck_sim import DuckSim
from robo_worlds.expert import Expert
DZ = float(sys.argv[1]); N = int(sys.argv[2])
pols = {"stock": "checkpoints_cache/duck/policies/velstand.onnx", "specialist": "checkpoints_cache/duck/world_policies/a_hospital_corridor_with_wet_floor_zones.onnx"}
res = {}
for name, p in pols.items():
    s = DuckSim("worlds_duck/a_hospital_corridor_with_wet_floor_zones", p, seed=5000, dr=True); ex = Expert(s)
    g = mujoco.mj_name2id(s.m, mujoco.mjtObj.mjOBJ_GEOM, "w_xray_platform__deck"); s.m.geom_pos[g][2] -= DZ
    ok = 0
    for ep in range(N):
        s.reset("xray_appointment", seed=5000 + ep); ex.reset()
        while True:
            _, done, info = s.step(ex.act())
            if done: break
        ok += info["success"]
    res[name] = ok / N; print(name, DZ, ok, "/", N, flush=True)
json.dump(res, open(f"results/recheck/xray_seam_dz{DZ}.json", "w"))
