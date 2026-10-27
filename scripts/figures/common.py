"""Shared helpers for the thumbnail and promo renders: worlds list, free cameras, 1080p renderer, segmentation cutout."""
import json, math, sys
from pathlib import Path
import mujoco, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from robo_worlds.duck_sim import DuckSim  # noqa: E402

STOCK = str(ROOT / "checkpoints_cache/duck/policies/velstand.onnx")
WORLDS = sorted(p for p in (ROOT / "worlds_duck").iterdir() if p.is_dir() and not p.name.startswith("_"))

def theme(world):
    return json.loads((Path(world) / "scene.json").read_text()).get("theme", Path(world).name)

def sim(world, policy=STOCK, dr=False, seed=0, w=1920, h=1080):
    s = DuckSim(str(world), policy, seed=seed, dr=dr)
    s.m.vis.global_.offwidth = max(w, s.m.vis.global_.offwidth)
    s.m.vis.global_.offheight = max(h, s.m.vis.global_.offheight)
    s.m.vis.quality.shadowsize = 8192
    return s

class Cam:
    def __init__(self, s, w=1920, h=1080):
        self.s, self.r = s, mujoco.Renderer(s.m, h, w)
        self.cam = mujoco.MjvCamera(); self.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        self.opt = mujoco.MjvOption()
    def overview(self, az=135, el=-38, scale=1.0):
        sx, sy = self.s.scene["room"]["size"]
        self.cam.lookat[:] = [0, 0, 0.0]; self.cam.distance = 1.05 * max(sx, sy) * scale
        self.cam.azimuth, self.cam.elevation = az, el
        return self
    def follow(self, dist=0.55, az=None, el=-14, height=0.10):
        p, yaw = self.s.pose()
        self.cam.lookat[:] = [p[0], p[1], p[2] - 0.13 + height]; self.cam.distance = dist
        self.cam.azimuth = math.degrees(yaw) + 200 if az is None else az
        self.cam.elevation = el
        return self
    def frame(self):
        self.r.update_scene(self.s.d, camera=self.cam, scene_option=self.opt)
        return self.r.render()
    def robot_mask(self):
        m = self.s.m
        root = m.body("trunk_base").id
        robot = np.array([m.body_rootid[m.geom_bodyid[g]] == root for g in range(m.ngeom)])
        self.r.enable_segmentation_rendering()
        self.r.update_scene(self.s.d, camera=self.cam, scene_option=self.opt)
        seg = self.r.render(); self.r.disable_segmentation_rendering()
        ids, types = seg[..., 0], seg[..., 1]
        return (types == int(mujoco.mjtObj.mjOBJ_GEOM)) & (ids >= 0) & robot[np.clip(ids, 0, m.ngeom - 1)]
