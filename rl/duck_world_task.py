"""mjlab task: Pollen's Microduck walking recipe, trained INSIDE one generated world.

Built on `make_microduck_velocity_env_cfg` (same robot, BAM actuators, 61-D obs contract, domain randomisation,
rewards), with the generated world swapped in for the flat plane:

* the world's static colliders are added to mjlab's ``terrain`` body (foot contacts and height rays see them),
  its gravity replaces Earth's, its surfaces keep their own friction (ice, wax, rubber ...) with +-15 % DR;
* robots spawn on free floor of the world (start points of precomputed planner paths);
* NAV_FRACTION of the envs get commands from a pure-pursuit controller following planner paths through the room
  (the command distribution the high-level policy will produce); the rest keep the recipe's random commands;
* every inherited curriculum is pinned to its final stage, because training warm-starts from the deployed walk.
"""

from __future__ import annotations

import math
import os
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mjlab.managers import EventTermCfg  # noqa: E402
from mjlab.managers.scene_entity_config import SceneEntityCfg  # noqa: E402
from mjlab.envs.mdp import dr  # noqa: E402

from mjlab_microduck.tasks import mdp as microduck_mdp  # noqa: E402
from mjlab_microduck.tasks.microduck_velocity_env_cfg import MicroduckRlCfg, make_microduck_velocity_env_cfg  # noqa: E402
from mjlab_microduck.tasks.microduck_velstand_env_cfg import _collapse_curricula_to_final  # noqa: E402

from robo_worlds import duck_scene as ds  # noqa: E402

NAV_FRACTION = 0.7
NAV_VMAX = (0.28, 0.4)  # above the stock gait's dead band
N_PATHS = 384
PATH_K = 64


# ----------------------------------------------------------------------------- path library
def build_paths(world_dir: Path, n_paths=N_PATHS, k=PATH_K, seed=0):
    """Random start->goal planner paths over the world's free floor (gates open, hazards avoided), resampled to
    k points by arc length. Cached as nav_paths.npz in the world directory."""
    cache = Path(world_dir) / "nav_paths.npz"
    if cache.exists():
        z = np.load(cache)
        return z["paths"], z["heights"]
    from robo_worlds import planner as pl

    scene = ds.load_scene(world_dir)
    hm = ds.height_map(scene, gates_open=True)
    grid = pl.Grid(hm, scene)
    U = grid.unsafe(avoid=[z for z in scene["zones"] if z["kind"] == "hazard"])
    free = np.argwhere(~U)
    rng = np.random.default_rng(seed)
    paths, heights = [], []
    tries = 0
    while len(paths) < n_paths and tries < n_paths * 6:
        tries += 1
        a, b = free[rng.integers(len(free))], free[rng.integers(len(free))]
        pa, pb = grid.point(a), grid.point(b)
        if np.linalg.norm(pa - pb) < 0.8:
            continue
        p = grid.astar(pa, pb, U, goal_radius=0.05)
        if p is None or len(p) < 2:
            continue
        P = np.asarray(p)
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        s = np.r_[0, np.cumsum(seg)]
        t = np.linspace(0, s[-1], k)
        R = np.stack([np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])], 1)
        paths.append(R)
        heights.append([grid.height_at(q) for q in R])
    paths, heights = np.asarray(paths, np.float32), np.asarray(heights, np.float32)
    np.savez(cache, paths=paths, heights=heights)
    return paths, heights


# ----------------------------------------------------------------------------- events
def inside_mask(num_envs, inside_fraction, device):
    """Fixed split: env i trains inside the room iff (i % 20) < 20 * inside_fraction."""
    return (torch.arange(num_envs, device=device) % 20) < int(round(20 * inside_fraction))


def reset_on_world_floor(env, env_ids, world_dir: str, z_range=(0.12, 0.13), inside_fraction=1.0,
                         asset_cfg=SceneEntityCfg("robot")):
    """Inside envs spawn at a random path start (free floor of the room); outside envs on the open floor around the
    room (same gravity and floor), where random commands cannot drive them into walls. Random yaw."""
    if env_ids is None:
        env_ids = torch.arange(env.num_envs, device=env.device)
    cache = getattr(env, "_duck_paths", None)
    if cache is None:
        P, H = build_paths(Path(world_dir))
        cache = env._duck_paths = (torch.tensor(P, device=env.device), torch.tensor(H, device=env.device))
    P, H = cache
    n = len(env_ids)
    idx = torch.randint(0, P.shape[0], (n,), device=env.device)
    asset = env.scene[asset_cfg.name]
    root = asset.data.default_root_state[env_ids].clone()
    root[:, 0:2] = P[idx, 0]
    root[:, 2] = H[idx, 0] + torch.empty(n, device=env.device).uniform_(*z_range)
    tang = P[idx, 3] - P[idx, 0]
    yaw_path = torch.atan2(tang[:, 1], tang[:, 0])
    if inside_fraction < 1.0:
        room = getattr(env, "_duck_room", None)
        if room is None:
            room = env._duck_room = ds.load_scene(world_dir)["room"]["size"]
        out = ~inside_mask(env.num_envs, inside_fraction, env.device)[env_ids]
        k = int(out.sum())
        if k:
            hx, hy = room[0] / 2 + 0.7, room[1] / 2 + 0.7
            side = torch.randint(0, 4, (k,), device=env.device)
            a = torch.empty(k, device=env.device).uniform_(-1, 1)
            d = torch.empty(k, device=env.device).uniform_(0, 3.0)
            x = torch.where(side < 2, (hx + d) * torch.where(side == 0, 1.0, -1.0), a * (hx + 3.0))
            y = torch.where(side >= 2, (hy + d) * torch.where(side == 2, 1.0, -1.0), a * (hy + 3.0))
            root[out, 0], root[out, 1] = x, y
            root[out, 2] = torch.empty(k, device=env.device).uniform_(*z_range)
    yaw = torch.empty(n, device=env.device).uniform_(-math.pi, math.pi)
    inside = torch.ones(n, dtype=torch.bool, device=env.device) if inside_fraction >= 1.0 else inside_mask(env.num_envs, inside_fraction, env.device)[env_ids]
    yaw = torch.where(inside, yaw_path, yaw)
    root[:, 3] = torch.cos(yaw / 2)
    root[:, 4:6] = 0.0
    root[:, 6] = torch.sin(yaw / 2)
    asset.write_root_link_pose_to_sim(root[:, :7], env_ids=env_ids)
    asset.write_root_link_velocity_to_sim(torch.zeros(n, 6, device=env.device), env_ids=env_ids)
    env._duck_spawn_idx = getattr(env, "_duck_spawn_idx", torch.zeros(env.num_envs, dtype=torch.long, device=env.device))
    env._duck_spawn_idx[env_ids] = idx


# ----------------------------------------------------------------------------- nav command
class NavVelocityCommand(microduck_mdp.VelocityCommandCommandOnly):
    """Recipe velocity command; for a fraction of envs the twist comes from pure pursuit along a planner path."""

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        P, H = build_paths(Path(cfg.world_dir))
        self.P = torch.tensor(P, device=self.device)
        self.n_paths, self.K = self.P.shape[0], self.P.shape[1]
        self.is_nav = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.path_id = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)
        self.prog = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)
        self.vmax = torch.full((self.num_envs,), 0.3, device=self.device)
        self.prog_gain = torch.zeros(self.num_envs, device=self.device)
        self.t_path = torch.zeros(self.num_envs, device=self.device)
        self.seg_len = (torch.linalg.norm(self.P[:, -1] - self.P[:, 0], dim=-1) / (self.K - 1)).clamp(min=1e-3)
        self.inside = inside_mask(self.num_envs, cfg.inside_fraction, self.device) if cfg.inside_fraction < 1.0 else None

    def _pick_paths(self, env_ids):
        """Path starting nearest the robot (random among the 4 nearest starts)."""
        pos = self.robot.data.root_link_pos_w[env_ids, :2]
        d = torch.cdist(pos, self.P[:, 0])
        near = torch.topk(d, k=min(4, self.n_paths), largest=False).indices
        pick = near[torch.arange(len(env_ids), device=self.device), torch.randint(0, near.shape[1], (len(env_ids),), device=self.device)]
        self.path_id[env_ids] = pick
        self.prog[env_ids] = 0

    def _resample_command(self, env_ids):
        super()._resample_command(env_ids)
        new_nav = torch.rand(len(env_ids), device=self.device) < self.cfg.nav_fraction
        if self.inside is not None:
            new_nav = self.inside[env_ids].clone()
        elif self.cfg.open_loop and self.cfg.inside_fraction >= 1.0:
            new_nav = torch.ones(len(env_ids), dtype=torch.bool, device=self.device)
        if self.cfg.open_loop:  # a path is only replayed from the spawn it was aligned with
            new_nav &= self._env.episode_length_buf[env_ids] == 0
        # envs already navigating keep their path until it ends
        keep = self.is_nav[env_ids] & (self.prog[env_ids] < self.K - 2) & (self._env.episode_length_buf[env_ids] > 0)
        self.is_nav[env_ids] = new_nav | keep
        start = env_ids[new_nav & ~keep]
        if len(start):
            if self.cfg.open_loop:  # the robot was spawned on (and aligned with) this path
                self.path_id[start] = self._env._duck_spawn_idx[start]
                self.prog[start] = 0
                self.t_path[start] = 0.0
            else:
                self._pick_paths(start)
            self.vmax[start] = torch.empty(len(start), device=self.device).uniform_(*self.cfg.nav_vmax)
        nav_ids = env_ids[self.is_nav[env_ids]]
        self.is_standing_env[nav_ids] = False

    def _open_loop(self, ids):
        """Commands replayed from the path's geometry (speed v, yaw rate = curvature * v), independent of the
        robot's state, so the policy cannot shape its own commands."""
        P = self.P[self.path_id[ids]]
        seg = torch.linalg.norm(P[:, 1:] - P[:, :-1], dim=-1).clamp(min=1e-4)  # (n, K-1)
        th = torch.atan2(P[:, 1:, 1] - P[:, :-1, 1], P[:, 1:, 0] - P[:, :-1, 0])
        dth = torch.atan2(torch.sin(th[:, 1:] - th[:, :-1]), torch.cos(th[:, 1:] - th[:, :-1]))
        s_cum = torch.cumsum(seg, dim=1)
        self.t_path[ids] += self._env.step_dt
        dist = self.t_path[ids] * self.vmax[ids]
        k = torch.searchsorted(s_cum, dist[:, None]).squeeze(1).clamp(max=self.K - 3)
        ar = torch.arange(len(ids), device=self.device)
        # smooth the heading change of the next ~0.2 m into a yaw rate
        span = 6
        kk = (k[:, None] + torch.arange(span, device=self.device)[None]).clamp(max=self.K - 3)
        turn = torch.gather(dth, 1, kk).sum(1)
        length = torch.gather(seg, 1, kk).sum(1)
        wz = (turn / length * self.vmax[ids]).clamp(-1.0, 1.0)
        done = dist >= s_cum[:, -1]
        self.vel_command_b[ids, 0] = torch.where(done, torch.zeros_like(wz), self.vmax[ids])
        self.vel_command_b[ids, 1] = 0.0
        self.vel_command_b[ids, 2] = torch.where(done, torch.zeros_like(wz), wz)
        self.prog[ids] = k
        fin = ids[done]
        if len(fin):  # path walked: hand the env back to the recipe's random commands
            self.is_nav[fin] = False
            microduck_mdp.VelocityCommandCommandOnly._resample_command(self, fin)

    def _update_command(self):
        super()._update_command()
        ids = self.is_nav.nonzero(as_tuple=False).flatten()
        if len(ids) == 0:
            return
        if self.cfg.open_loop:
            self.prog_gain.zero_()
            self._open_loop(ids)
            return
        pos = self.robot.data.root_link_pos_w[ids, :2]
        yaw = self.robot.data.heading_w[ids]
        paths = self.P[self.path_id[ids]]  # (n, K, 2)
        # advance progress: nearest point within a window ahead of the current index
        win = torch.arange(0, 12, device=self.device)
        cand = (self.prog[ids, None] + win[None]).clamp(max=self.K - 1)
        dist = torch.linalg.norm(torch.gather(paths, 1, cand[..., None].expand(-1, -1, 2)) - pos[:, None], dim=-1)
        new_prog = torch.gather(cand, 1, dist.argmin(1, keepdim=True)).squeeze(1)
        self.prog_gain.zero_()
        self.prog_gain[ids] = (new_prog - self.prog[ids]).float() * self.seg_len[self.path_id[ids]]
        self.prog[ids] = new_prog
        # look 0.35 m ahead (a few waypoints would be ~10 cm: inside the robot's own gait sway, and the command
        # would flip with every step)
        ahead = torch.ceil(0.35 / self.seg_len[self.path_id[ids]]).long()
        look = (self.prog[ids] + ahead).clamp(max=self.K - 1)
        target = paths[torch.arange(len(ids), device=self.device), look]
        err = torch.atan2(target[:, 1] - pos[:, 1], target[:, 0] - pos[:, 0]) - yaw
        err = torch.atan2(torch.sin(err), torch.cos(err))
        vx = torch.where(err.abs() > 1.2, torch.zeros_like(err), self.vmax[ids] * torch.cos(err).clamp(min=0.5))
        wz = (2.0 * err).clamp(-1.0, 1.0)
        done = self.prog[ids] >= self.K - 2
        vx = torch.where(done, torch.zeros_like(vx), vx)
        wz = torch.where(done, torch.zeros_like(wz), wz)
        self.vel_command_b[ids, 0] = vx
        self.vel_command_b[ids, 1] = 0.0
        self.vel_command_b[ids, 2] = wz
        # finished paths: chain a new one from here
        fin = ids[done]
        if len(fin):
            self._pick_paths(fin)


def path_progress(env, command_name="twist", cap=0.4):
    """Metres per second advanced along the planned path (inside envs). Potential-style: standing still earns 0,
    and progress can only be earned once per stretch of path, so it cannot be farmed."""
    term = env.command_manager.get_term(command_name)
    return (term.prog_gain / env.step_dt).clamp(0.0, cap)


class NavVelocityCommandCfg(microduck_mdp.VelocityCommandCommandOnlyCfg):
    world_dir: str = ""
    inside_fraction: float = 1.0
    open_loop: bool = True
    nav_fraction: float = NAV_FRACTION
    nav_vmax: tuple = NAV_VMAX

    def build(self, env):
        return NavVelocityCommand(self, env)


# ----------------------------------------------------------------------------- env cfg
def make_duck_world_env_cfg(world_dir: str, play: bool = False, flat: bool = False, collapse: bool = True,
                            inside_fraction: float = 1.0, progress_weight: float = 0.0):
    world_dir = str(Path(world_dir).resolve())
    scene = ds.load_scene(world_dir)
    build_paths(Path(world_dir))
    cfg = make_microduck_velocity_env_cfg(play=play, rough=False)

    def spec_fn(spec):
        ds.add_world_to_mjlab_spec(spec, scene)
        for g in spec.body("terrain").geoms:  # soften box-edge contacts (as Pollen's rough-terrain recipe)
            g.solref = [0.04, 1.0]
            g.solimp = [0.85, 0.95, 0.001, 0.5, 2.0]

    if not flat:
        cfg.scene.spec_fn = spec_fn
    cfg.scene.env_spacing = 0.0  # every env lives in its own copy of the same room
    cfg.sim.nconmax = 200
    cfg.sim.mujoco.iterations = 30
    cfg.sim.mujoco.ls_iterations = 50
    if not flat:
        cfg.sim.mujoco.gravity = (0.0, 0.0, -float(scene["env"].get("gravity", 9.81)))

    old = cfg.commands["twist"]
    kw = {k: v for k, v in vars(old).items()}
    cmd = NavVelocityCommandCfg(**kw)
    cmd.world_dir = world_dir
    cfg.commands["twist"] = cmd

    if flat:
        cfg.commands["twist"].nav_fraction = 0.0
        if "out_of_terrain_bounds" in cfg.terminations:
            del cfg.terminations["out_of_terrain_bounds"]
        if collapse:
            _collapse_curricula_to_final(cfg)
        return cfg
    cmd.inside_fraction = inside_fraction
    cfg.events["reset_base"] = EventTermCfg(func=reset_on_world_floor, mode="reset",
                                            params={"world_dir": world_dir, "inside_fraction": inside_fraction})
    if progress_weight > 0:
        from mjlab.managers import RewardTermCfg

        cfg.rewards["path_progress"] = RewardTermCfg(func=path_progress, weight=progress_weight, params={"command_name": "twist"})
    # world-surface friction DR (the terrain geoms carry the world materials' friction)
    cfg.events["world_friction"] = EventTermCfg(
        func=dr.geom_friction, mode="reset",
        params={"asset_cfg": SceneEntityCfg("terrain", geom_names=(".*",)), "operation": "scale", "ranges": (0.85, 1.15)})
    if "out_of_terrain_bounds" in cfg.terminations:
        del cfg.terminations["out_of_terrain_bounds"]
    if collapse:
        _collapse_curricula_to_final(cfg)
    return cfg


def rl_cfg(slug: str, max_iterations: int, symmetry: bool = False):
    c = deepcopy(MicroduckRlCfg)
    if symmetry:  # left/right mirror loss (Pollen's 61-D table): forbids yaw bias and mirrored turning
        from mjlab_microduck.tasks.symmetry import SYMMETRY_CFG

        c.algorithm.symmetry_cfg = deepcopy(SYMMETRY_CFG)
    c.experiment_name = f"duckworld_{slug}"
    c.run_name = slug
    c.max_iterations = max_iterations
    c.save_interval = 100
    c.logger = "tensorboard"
    return c
