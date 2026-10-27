"""Privileged expert for the Microduck tasks: plans on the traversability grid and emits 13-D commands at 10 Hz.

It sees the true state (robot pose, object poses, gate states); the learned high-level policy only sees the head
camera, proprioception and the instruction. The low-level walking policy executes the commands.
"""

from __future__ import annotations

import math

import numpy as np

from . import planner as pl

REPLAN_S = 1.0


class Expert:
    def __init__(self, sim, v_max=pl.V_MAX, seed=0):
        self.sim = sim
        self.grid = pl.Grid(sim.hm, sim.scene)
        self.v_max = v_max
        self.rng = np.random.default_rng(seed)
        self.reset()

    def reset(self):
        self.path = None
        self.path_key = None
        self.t_plan = -1e9
        self.mode = "approach"
        self.turn_cmd = 0.0

    def _unsafe(self, extra_obstacles=()):
        sim = self.sim
        t = sim.state.task
        avoid = [sim.zones[z] for z in t.get("avoid", [])]
        closed = [g for n, g in sim.gates.items() if sim.d.qpos[sim.gate_q[n]] < g["travel"] * 0.9]
        obstacles = list(extra_obstacles)
        for b in sim.objects:  # objects not being pushed are obstacles
            if t["kind"] != "push" or b["name"] != t.get("object"):
                obstacles.append((sim.object_pos(b["name"])[:2], self._obj_radius(b)))
        return self.grid.unsafe(avoid=avoid, closed_gates=closed, obstacles=obstacles)

    @staticmethod
    def _obj_radius(b):
        g = b["geoms"][0]
        return float(g["size"][0]) if g["kind"] == "sphere" else float(np.hypot(g["size"][0], g["size"][1]))

    def _goto(self, target, radius, key, extra_obstacles=(), final=True, v_max=None):
        sim = self.sim
        p, yaw = sim.pose()
        if self.path is None or self.path_key != key or sim.time - self.t_plan > REPLAN_S:
            path = self.grid.astar(p[:2], np.asarray(target), self._unsafe(extra_obstacles), goal_radius=radius)
            self.t_plan = sim.time
            if path is not None:
                self.path, self.path_key = path, key
            elif self.path_key != key:
                self.path = None
        if self.path is None or len(self.path) < 1:
            return np.array([pl.V_WALK_MIN, 0.0, 0.8]), 9.9  # lost: walk a small circle and try again
        path = [p[:2]] + list(self.path[1:]) if len(self.path) > 1 else [p[:2], self.path[0]]
        vx, vy, wz, dist = pl.pursue(p[:2], yaw, path, v_max=v_max or self.v_max, final=final)
        return np.array([vx, vy, wz]), dist

    def act(self):
        sim = self.sim
        st = sim.state
        goals = sim.subgoals()
        cmd = np.zeros(13, np.float32)
        if st.done or st.phase >= len(goals):
            return cmd
        g = goals[st.phase]
        if g[0] == "zone":
            z = sim.zones[g[1]]
            tw, _ = self._goto(z["center"], max(0.04, z["radius"] - 0.08), ("zone", g[1]))
        elif g[0] == "plate":
            p = sim.plates[g[1]]
            tw, _ = self._goto(p["center"], max(0.03, p["size"] / 2 - 0.05), ("plate", g[1]))
        else:
            tw = self._push(g[1], g[2])
        cmd[:3] = tw
        return cmd

    def _push(self, obj, goal):
        sim = self.sim
        b = next(x for x in sim.objects if x["name"] == obj)
        r = self._obj_radius(b)
        o = sim.object_pos(obj)[:2]
        gz = sim.zones[goal]
        gc = np.array(gz["center"])
        to_goal = gc - o
        dist_goal = float(np.linalg.norm(to_goal))
        u = to_goal / max(dist_goal, 1e-6)
        p, yaw = sim.pose()
        rel = o - p[:2]
        behind = o - u * (r + 0.16)
        # pushing mode: the robot is behind the object, roughly facing the goal
        along = float(np.dot(rel, u))
        lateral = float(np.cross(u, rel))
        heading_err = pl.wrap(math.atan2(u[1], u[0]) - yaw)
        if self.mode == "push" and (along < 0.02 or abs(lateral) > r + 0.03 or abs(heading_err) > 0.9):
            self.mode = "approach"
        if self.mode == "approach":
            if np.linalg.norm(p[:2] - behind) < 0.07:
                if abs(heading_err) < 0.25:
                    self.mode = "push"
                else:
                    return np.array([pl.V_WALK_MIN, 0.0, float(np.clip(1.8 * heading_err, -1.0, 1.0))])
            else:
                tw, _ = self._goto(behind, 0.05, ("behind", tuple(np.round(behind, 1))), extra_obstacles=[(o, r + 0.04)])
                return tw
        # push: aim through the object's centre towards the goal, correcting the lateral offset
        aim = o + u * 0.15 - (lateral * 0.8) * np.array([-u[1], u[0]])
        err = pl.wrap(math.atan2(aim[1] - p[1], aim[0] - p[0]) - yaw)
        return np.array([0.32 if abs(err) < 0.6 else pl.V_WALK_MIN, 0.0, float(np.clip(1.8 * err, -1.0, 1.0))])
