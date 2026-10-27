"""Navigation for the Microduck in a generated world: traversability grid, A*, pure pursuit, push control.

The grid comes from `duck_scene.height_map` (top-down heights of static colliders). A move between neighbouring
cells is allowed when the height change is a step the robot can take; cells near walls, cliff edges, closed
gates and (optionally) hazard zones are unsafe for the robot's footprint. The expert turns a path into the
same 13-D command the low-level walking policy consumes: twist (vx, vy, wz) + head pose + body pose.
"""

from __future__ import annotations

import heapq
import math

import numpy as np
from scipy import ndimage

STEP_TOL = 0.028        # largest height change between neighbouring 2 cm cells the robot may cross
STEP_SOFT = 0.010       # height changes above this (real steps / ramp sides) cost extra: prefer ramps and flat ground
OBSTACLE_H = 0.13       # anything taller is an obstacle even when reached by a ramp
ROBOT_R = 0.10          # footprint radius used for inflation
HAZARD_MARGIN = 0.07
V_MAX, W_MAX = 0.35, 1.0
V_WALK_MIN = 0.28  # the stock gaits have a dead band: smaller forward commands do not start a gait


class Grid:
    def __init__(self, hm: dict, scene: dict):
        self.H = hm["H"]
        self.res, self.x0, self.y0 = hm["res"], hm["x0"], hm["y0"]
        self.nx, self.ny = self.H.shape
        self.scene = scene
        H = self.H
        edge = np.zeros_like(H, bool)
        dx = np.abs(np.diff(H, axis=0)) > STEP_TOL
        dy = np.abs(np.diff(H, axis=1)) > STEP_TOL
        edge[:-1] |= dx
        edge[1:] |= dx
        edge[:, :-1] |= dy
        edge[:, 1:] |= dy
        hard = edge | (H > OBSTACLE_H)
        soft = np.zeros_like(H, bool)
        sx_ = np.abs(np.diff(H, axis=0)) > STEP_SOFT
        sy_ = np.abs(np.diff(H, axis=1)) > STEP_SOFT
        soft[:-1] |= sx_
        soft[1:] |= sx_
        soft[:, :-1] |= sy_
        soft[:, 1:] |= sy_
        hard[0, :] = hard[-1, :] = hard[:, 0] = hard[:, -1] = True
        r = int(math.ceil(ROBOT_R / self.res))
        disk = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
        self.hard = hard
        self.static_unsafe = ndimage.binary_dilation(hard, structure=disk)
        # traversal cost: extra for stepping over edges, and for hugging walls / edges
        clear = ndimage.distance_transform_edt(~(hard | soft)) * self.res
        self.cost = 1.0 + 3.0 * np.clip((0.22 - clear) / 0.12, 0, 1) + 25.0 * ndimage.binary_dilation(soft, iterations=1)
        self.xs = self.x0 + np.arange(self.nx) * self.res
        self.ys = self.y0 + np.arange(self.ny) * self.res
        self.X, self.Y = np.meshgrid(self.xs, self.ys, indexing="ij")

    # -- coordinates --
    def cell(self, p):
        i = int(round((p[0] - self.x0) / self.res))
        j = int(round((p[1] - self.y0) / self.res))
        return min(max(i, 0), self.nx - 1), min(max(j, 0), self.ny - 1)

    def point(self, c):
        return np.array([self.x0 + c[0] * self.res, self.y0 + c[1] * self.res])

    def height_at(self, p):
        return float(self.H[self.cell(p)])

    # -- masks --
    def disc(self, center, radius):
        return np.hypot(self.X - center[0], self.Y - center[1]) <= radius

    def segment_mask(self, center, yaw, half_len, half_width):
        c, s = math.cos(yaw), math.sin(yaw)
        lx = (self.X - center[0]) * c + (self.Y - center[1]) * s
        ly = -(self.X - center[0]) * s + (self.Y - center[1]) * c
        return (np.abs(lx) <= half_width) & (np.abs(ly) <= half_len)

    def unsafe(self, avoid=(), closed_gates=(), obstacles=()):
        """Unsafe-cell mask. avoid: hazard zone dicts; closed_gates: gate dicts; obstacles: (center, radius)."""
        U = self.static_unsafe.copy()
        for z in avoid:
            U |= self.disc(z["center"], z["radius"] + HAZARD_MARGIN)
        for g in closed_gates:
            U |= self.segment_mask(g["center"], g["yaw"], g["width"] / 2 + 0.05, 0.02 + ROBOT_R)
        for c, rad in obstacles:
            U |= self.disc(c, rad + ROBOT_R)
        return U

    # -- search --
    def astar(self, start, goal, U, goal_radius=0.0):
        """8-connected A* from world point start to the nearest safe cell within goal_radius of goal.
        Returns a list of world points or None."""
        s = self.cell(start)
        H = self.H
        if U[s]:  # starting inside an inflated region (e.g. next to a wall): allow walking out of it
            U = U.copy()
            U[self.disc(start, ROBOT_R * 1.5) & ~self.hard] = False
        gmask = self.disc(goal, max(goal_radius, self.res)) & ~U
        if not gmask.any():
            return None
        gc = self.cell(goal)
        open_ = [(0.0, s)]
        g = {s: 0.0}
        parent = {s: None}
        nbr = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
        found = None
        while open_:
            f, c = heapq.heappop(open_)
            if gmask[c]:
                found = c
                break
            gc_ = g[c]
            for di, dj, w in nbr:
                n = (c[0] + di, c[1] + dj)
                if not (0 <= n[0] < self.nx and 0 <= n[1] < self.ny) or U[n]:
                    continue
                if abs(H[n] - H[c]) > STEP_TOL:
                    continue
                ng = gc_ + w * self.cost[n]
                if ng < g.get(n, 1e18):
                    g[n] = ng
                    parent[n] = c
                    heapq.heappush(open_, (ng + math.hypot(n[0] - gc[0], n[1] - gc[1]), n))
        if found is None:
            return None
        path = []
        c = found
        while c is not None:
            path.append(self.point(c))
            c = parent[c]
        path = path[::-1]
        return _simplify(path, self, U)

    def reachable(self, start, goal, U, goal_radius):
        return self.astar(start, goal, U, goal_radius) is not None


def _line_free(a, b, grid, U):
    n = int(np.linalg.norm(b - a) / (grid.res * 0.5)) + 2
    prev = None
    for t in np.linspace(0, 1, n):
        c = grid.cell(a + (b - a) * t)
        if U[c]:
            return False
        if prev is not None and abs(grid.H[c] - grid.H[prev]) > STEP_TOL:
            return False
        prev = c
    return True


def _simplify(path, grid, U):
    if len(path) <= 2:
        return path
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1 and not _line_free(path[i], path[j], grid, U):
            j -= 1
        out.append(path[j])
        i = j
    return out


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def pursue(pos, yaw, path, lookahead=0.25, v_max=V_MAX, final=True):
    """Pure pursuit on a polyline. Returns (vx, vy, wz, dist_to_end)."""
    pts = np.asarray(path)
    d_end = float(np.linalg.norm(pts[-1] - pos))
    # closest segment, then the point `lookahead` further along
    best, best_i, best_t = 1e9, 0, 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        t = float(np.clip(np.dot(pos - a, ab) / max(1e-9, np.dot(ab, ab)), 0, 1))
        dd = np.linalg.norm(a + ab * t - pos)
        if dd < best:
            best, best_i, best_t = dd, i, t
    target, remain = None, lookahead
    p = pts[best_i] + (pts[best_i + 1] - pts[best_i]) * best_t if len(pts) > 1 else pts[0]
    for i in range(best_i, len(pts) - 1):
        seg_end = pts[i + 1]
        L = float(np.linalg.norm(seg_end - p))
        if L >= remain:
            target = p + (seg_end - p) / max(L, 1e-9) * remain
            break
        remain -= L
        p = seg_end
    if target is None:
        target = pts[-1]
    err = wrap(math.atan2(target[1] - pos[1], target[0] - pos[0]) - yaw)
    wz = float(np.clip(2.0 * err, -W_MAX, W_MAX))
    # always keep walking and turn on an arc: world-specialised gaits lose the turn-on-the-spot skill, and the stock
    # gait needs a forward command above its dead band anyway
    vx = V_WALK_MIN if abs(err) > 1.2 else max(V_WALK_MIN, v_max * math.cos(err))
    return float(vx), 0.0, wz, d_end
