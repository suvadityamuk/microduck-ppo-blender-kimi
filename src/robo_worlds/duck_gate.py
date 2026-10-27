"""Feasibility gate for a generated Microduck world (runs after Blender exported scene.json).

Structural checks (decide which tasks survive, and what the designer LLM is told to fix):
  * the world compiles, free objects settle, the robot does not spawn inside anything, the head camera sees a
    reasonably lit scene;
  * on the traversability grid: every task's start is on walkable floor and every sub-goal is reachable in order
    (gates closed until their plate is pressed, hazards avoided); a gate task must actually NEED its gate; a push
    object must have room to be pushed to its goal.
Dynamic check (informational): the planner expert drives Pollen's stock walking policy through each task a few
times; the success rate is the baseline the world-specialised policy has to beat.

    python -m robo_worlds.duck_gate worlds_duck/<w> [--episodes 3] [--json]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

from . import duck_scene as ds
from . import planner as pl

ROOT = Path(__file__).resolve().parents[2]
STOCK = ROOT / "checkpoints_cache" / "duck" / "policies" / "velstand.onnx"
MIN_TASKS, MIN_MULTI = 4, 2


def _fmt(p):
    return f"({p[0]:.2f}, {p[1]:.2f})"


def structural(scene, grid):
    zones = {z["name"]: z for z in scene["zones"]}
    plates = {p["name"]: p for p in scene.get("plates", [])}
    gates = scene.get("gates", {})
    objects = {b["name"]: b for b in scene["bodies"] if b["kind"] == "object"}
    obj_obstacles = [(np.array(b["pos"][:2]), _obj_r(b)) for b in objects.values()]
    out = {}
    for t in scene["tasks"]:
        issues = []
        avoid = [zones[z] for z in t.get("avoid", [])]
        start = np.array(t["start"][:2])
        others = [o for n, o in zip(objects, obj_obstacles) if n != t.get("object")]
        U_closed = grid.unsafe(avoid=avoid, closed_gates=list(gates.values()), obstacles=others)
        if grid.static_unsafe[grid.cell(start)] and grid.hard[grid.cell(start)]:
            issues.append(f"start {_fmt(start)} is on an obstacle / wall / edge; move it to open floor")
        for z in avoid:
            if np.linalg.norm(start - np.array(z["center"])) < z["radius"] + 0.12:
                issues.append(f"start {_fmt(start)} is inside or touching hazard {z['name']!r}")

        def reach(a, b, U, rad, what):
            p = grid.astar(a, b, U, goal_radius=rad)
            if p is None:
                issues.append(f"{what}: no walkable path from {_fmt(a)} to {_fmt(b)} for a robot 0.2 m wide "
                              "(blocked by walls, edges taller than 2.5 cm, closed gates or hazards); open a passage "
                              "at least 0.35 m wide, add a ramp, or move the goal")
            return p

        if t["kind"] == "goto":
            z = zones[t["goal"]]
            reach(start, z["center"], U_closed, z["radius"] - 0.06, f"goal {t['goal']!r}")
        elif t["kind"] == "visit":
            a = start
            for g in t["goals"]:
                z = zones[g]
                reach(a, z["center"], U_closed, z["radius"] - 0.06, f"visit {g!r}")
                a = np.array(z["center"])
        elif t["kind"] == "gate":
            p = plates[t["plate"]]
            gate = gates[t["gate"]]
            reach(start, p["center"], U_closed, p["size"] / 2 - 0.04, f"plate {t['plate']!r}")
            z = zones[t["goal"]]
            open_g = [g for n, g in gates.items() if n != t["gate"]]
            U_open = grid.unsafe(avoid=avoid, closed_gates=open_g, obstacles=others)
            reach(np.array(p["center"]), z["center"], U_open, z["radius"] - 0.06, f"goal {t['goal']!r} after opening {t['gate']!r}")
            if grid.astar(np.array(p["center"]), z["center"], U_closed, goal_radius=z["radius"] - 0.06) is not None:
                issues.append(f"goal {t['goal']!r} can be reached WITHOUT opening gate {t['gate']!r}: close the room around the "
                              f"goal with walls so the gate's doorway (at {_fmt(gate['center'])}) is the only way in")
        elif t["kind"] == "push":
            b = objects[t["object"]]
            o = np.array(b["pos"][:2])
            z = zones[t["goal"]]
            r = _obj_r(b)
            if np.linalg.norm(o - np.array(z["center"])) < z["radius"] + 0.1:
                issues.append(f"object {t['object']!r} already starts (almost) inside goal {t['goal']!r}; put them >= 0.5 m apart")
            # the object travels on the grid inflated by its own radius, not the robot's
            U_obj = grid.unsafe(avoid=avoid, closed_gates=list(gates.values()), obstacles=others) & grid.static_unsafe
            p_obj = grid.astar(o, z["center"], U_obj, goal_radius=max(0.03, z["radius"] - r))
            if p_obj is None:
                issues.append(f"object {t['object']!r} at {_fmt(o)} cannot be pushed to goal {t['goal']!r}: clear a straight-ish "
                              "lane of flat floor (no steps, ramps or walls) between them")
            u = (np.array(z["center"]) - o)
            u = u / max(1e-6, np.linalg.norm(u))
            behind = o - u * (r + 0.16)
            if grid.static_unsafe[grid.cell(behind)] and grid.hard[grid.cell(behind)]:
                issues.append(f"no room behind {t['object']!r} (at {_fmt(behind)}) for the robot to push it towards the goal; "
                              "keep 0.35 m of free floor on the far side of the object")
            reach(start, behind, grid.unsafe(avoid=avoid, closed_gates=list(gates.values()), obstacles=obj_obstacles), 0.06,
                  f"the spot behind {t['object']!r}")
        out[t["name"]] = issues
    return out


def _obj_r(b):
    g = b["geoms"][0]
    return float(g["size"][0]) if g["kind"] == "sphere" else float(np.hypot(g["size"][0], g["size"][1]))


def physical(scene):
    """Settling of free objects, spawn collisions and brightness, using the full CPU model."""
    issues, notes = [], {}
    m = ds.build_cpu_model(scene)
    d = mujoco.MjData(m)
    fq = m.jnt_qposadr[m.joint("trunk_base_freejoint").id]
    # park the robot far outside the room while objects settle
    d.qpos[fq:fq + 3] = [50, 50, 0.13]
    mujoco.mj_forward(m, d)
    objs = [b for b in scene["bodies"] if b["kind"] == "object"]
    p0 = {b["name"]: d.qpos[m.jnt_qposadr[m.joint(b["name"] + "_free").id]:][:3].copy() for b in objs}
    for _ in range(int(1.5 / m.opt.timestep)):
        mujoco.mj_step(m, d)
    for b in objs:
        a = m.jnt_qposadr[m.joint(b["name"] + "_free").id]
        mv = float(np.linalg.norm(d.qpos[a:a + 2] - p0[b["name"]][:2]))
        if mv > 0.04 or d.qpos[a + 2] < -0.01:
            issues.append(f"object {b['name']!r} does not rest where it was placed (moved {mv * 100:.0f} cm in 1.5 s): it overlaps "
                          "something or sits on a slope / edge; put it on flat open floor")
    robot_geoms = {i for i in range(m.ngeom) if m.body(m.geom_bodyid[i]).rootid == m.body("trunk_base").id}
    renderer = mujoco.Renderer(m, 120, 160)
    opt = mujoco.MjvOption()
    opt.geomgroup[:] = [1, 1, 0, 0, 1, 0]
    bright = []
    for t in scene["tasks"]:
        x, y, yaw = t["start"]
        mujoco.mj_resetData(m, d)
        d.qpos[fq:fq + 3] = [x, y, ds.STAND_Z + 0.005]
        d.qpos[fq + 3:fq + 7] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
        mujoco.mj_forward(m, d)
        hits = set()
        for c in d.contact[:d.ncon]:
            g1, g2 = c.geom1, c.geom2
            if (g1 in robot_geoms) != (g2 in robot_geoms):
                other = g2 if g1 in robot_geoms else g1
                nm = m.geom(other).name
                if nm not in ("floor",) and c.dist < -0.004:
                    hits.add(nm.split("__")[0])
        if hits:
            issues.append(f"task {t['name']!r}: the robot would spawn inside {sorted(hits)} at {_fmt((x, y))}; move the start to open floor")
        renderer.update_scene(d, camera="head_camera", scene_option=opt)
        bright.append(float(renderer.render().mean()))
    notes["head_brightness"] = float(np.mean(bright)) if bright else None
    if bright and np.mean(bright) < 45:
        issues.append(f"the scene is too dark for the robot's camera (mean brightness {np.mean(bright):.0f}/255); use brighter "
                      "floor/wall materials and a stronger light / ambient")
    return issues, notes


def dynamic(world_dir, episodes):
    from .duck_sim import DuckSim
    from .expert import Expert

    sim = DuckSim(world_dir, STOCK, seed=0, dr=True)
    ex = Expert(sim)
    out = {}
    for tn in sim.tasks:
        ok, fails, phases = 0, [], []
        for ep in range(episodes):
            sim.reset(tn, seed=ep)
            ex.reset()
            while True:
                _, done, info = sim.step(ex.act())
                if done:
                    break
            ok += info["success"]
            phases.append(sim.state.phase)
            if not info["success"]:
                fails.append(info["failure"])
        out[tn] = {"rate": ok / episodes, "failures": fails, "max_phase": int(max(phases))}
    return out


def validate(world_dir, episodes=3):
    world_dir = Path(world_dir)
    scene = ds.load_scene(world_dir)
    hm = ds.height_map(scene, gates_open=True)
    grid = pl.Grid(hm, scene)
    s = structural(scene, grid)
    phys, notes = physical(scene)
    passing = [t for t, iss in s.items() if not iss]
    kinds = {t["name"]: t["kind"] for t in scene["tasks"]}
    dyn = dynamic(world_dir, episodes) if episodes > 0 and not phys else {}
    fb = []
    fb += phys
    for t, iss in s.items():
        for i in iss:
            fb.append(f"task {t!r}: {i}")
    n_multi = sum(kinds[t] != "goto" for t in passing)
    ok = not phys and len(passing) >= MIN_TASKS and n_multi >= MIN_MULTI
    if not ok and not phys:
        fb.append(f"only {len(passing)} tasks are feasible ({n_multi} multi-step); the world needs >= {MIN_TASKS} feasible tasks with "
                  f">= {MIN_MULTI} multi-step ones")
    return {"world": str(world_dir), "ok": ok, "passing": passing, "structural": s, "physical": phys, "notes": notes,
            "baseline": dyn, "feedback": "\n".join(fb)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world")
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = validate(a.world, a.episodes)
    if a.json:
        print("GATE_RESULT " + json.dumps(r))
    else:
        print(json.dumps(r, indent=2))


if __name__ == "__main__":
    sys.exit(main())
