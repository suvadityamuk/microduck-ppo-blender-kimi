"""scene.json (exported by the Blender-side `rw` API, format robo_worlds.duck/1) -> MuJoCo, for the Microduck.

Two consumers share this module:

* the CPU simulator (`duck_sim`): `build_cpu_model()` = full world (gates on slide joints, free balls/crates,
  decor, zones, lights, cameras) + the Microduck walk model attached with a free joint;
* mjlab training (`rl/`): `add_world_to_mjlab_spec()` adds the world to an mjlab scene spec. Static colliders
  go INTO mjlab's ``terrain`` body, so the robot's foot-contact sensor and the foot height-scan rays see ramps,
  steps and patches exactly like the generated terrain they were designed for. Gates are added open and
  static, free objects are left out (the low-level policy learns locomotion; the high-level tasks run on CPU).

Conventions: world colliders are geom group 0 (what height-scan rays see), visuals group 1, the robot's
collision geoms group 3. World surfaces carry `priority=1`, so THEIR friction (ice, rubber, wax) decides the
foot contact instead of MuJoCo's default max-combination with the foot's own friction.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MICRODUCK_RL = Path(os.environ.get("MICRODUCK_RL", ROOT / "third_party" / "microduck_rl"))
ROBOT_DIR = MICRODUCK_RL / "src" / "mjlab_microduck" / "robot" / "microduck"
ROBOT_XML = ROBOT_DIR / "robot_walk.xml"
TILE_M = {"surface": 0.5, "object": 0.15}
STAND_Z = 0.125  # trunk height the walking policies start from


def load_scene(world_dir: str | Path) -> dict:
    world_dir = Path(world_dir)
    scene = json.loads((world_dir / "scene.json").read_text())
    scene["_dir"] = str(world_dir.resolve())
    return scene


def _quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2]


def _yaw_quat(yaw):
    return [math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)]


def _rot(q):
    m = np.zeros(9)
    mujoco.mju_quat2Mat(m, np.asarray(q, float))
    return m.reshape(3, 3)


def body_world_pose(scene: dict, name: str) -> tuple[np.ndarray, list]:
    """World position + quaternion of a body (following parents)."""
    bodies = {b["name"]: b for b in scene["bodies"]}
    b = bodies[name]
    p, q = np.array(b["pos"], float), _yaw_quat(b["yaw"])
    while b["parent"]:
        par = bodies[b["parent"]]
        pq = _yaw_quat(par["yaw"])
        p = np.array(par["pos"]) + _rot(pq) @ p
        q = _quat_mul(pq, q)
        b = par
    return p, q


# ----------------------------------------------------------------------------- spec building blocks
def _add_assets(spec: mujoco.MjSpec, scene: dict, prefix: str = "w_") -> dict:
    """Textures + materials. Returns {material name: spec material name}."""
    wd = Path(scene["_dir"])
    names = {}
    for name, m in scene["materials"].items():
        mname = prefix + name
        mat = spec.add_material(name=mname)
        rough = float(m.get("roughness", 0.6))
        mat.specular = 0.05 + 0.5 * (1 - rough) * (0.5 + 0.5 * m.get("metallic", 0.0))
        mat.shininess = 0.1 + 0.8 * (1 - rough)
        mat.reflectance = 0.1 * float(m.get("metallic", 0.0))
        mat.emission = min(1.0, 0.45 * float(m.get("emission", 0.0)))
        rgba = list(m["rgba"])
        if m.get("texture"):
            tex = spec.add_texture(name=mname + "_tex", type=mujoco.mjtTexture.mjTEXTURE_2D, file=str(wd / m["texture"]))
            mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = tex.name
            rep = 1.0 / TILE_M["surface" if m.get("surface") else "object"]
            mat.texrepeat = [rep, rep]
            mat.texuniform = True
            mat.rgba = [1, 1, 1, rgba[3]]
        else:
            mat.rgba = rgba
        names[name] = mname
    return names


def _geom_type(kind):
    return {"box": mujoco.mjtGeom.mjGEOM_BOX, "sphere": mujoco.mjtGeom.mjGEOM_SPHERE, "cylinder": mujoco.mjtGeom.mjGEOM_CYLINDER,
            "capsule": mujoco.mjtGeom.mjGEOM_CAPSULE, "mesh": mujoco.mjtGeom.mjGEOM_MESH}[kind]


def _add_geom(spec, parent, scene, body, g, mats, frame_pos=None, frame_quat=None, collide=True, group=None,
              prefix="w_", surface_priority=True, mesh_cache=None):
    """Add one rw geom to `parent` (an MjsBody). frame_* re-express body-local poses (used to flatten fixtures
    into the terrain body)."""
    wd = Path(scene["_dir"])
    kw = {}
    pos, quat = np.array(g["pos"], float), list(g.get("quat", [1, 0, 0, 0]))
    if g["kind"] == "mesh":
        mname = prefix + Path(g["file"]).stem
        if mesh_cache is not None and mname not in mesh_cache:
            spec.add_mesh(name=mname, file=str(wd / g["file"]))
            mesh_cache.add(mname)
        kw["meshname"] = mname
        pos, quat = np.zeros(3), [1.0, 0.0, 0.0, 0.0]  # OBJ vertices are already in the body frame
    else:
        kw["size"] = list(g["size"]) + [0.0] * (3 - len(g["size"]))
    if frame_pos is not None:
        R = _rot(frame_quat)
        pos = np.asarray(frame_pos) + R @ pos
        quat = _quat_mul(frame_quat, quat)
    geom = parent.add_geom(name=f"{prefix}{body['name']}__{g['name']}", type=_geom_type(g["kind"]), pos=pos.tolist(),
                           quat=quat, material=mats[g["material"]], **kw)
    m = scene["materials"][g["material"]]
    if collide and g.get("collision", True):
        geom.contype, geom.conaffinity = 1, 1
        geom.group = 0 if group is None else group
        geom.friction = [float(m.get("friction", 1.0)), 0.005, 0.0001]
        geom.condim = 3
        if surface_priority:
            geom.priority = 1
    else:
        geom.contype, geom.conaffinity = 0, 0
        geom.group = 1 if group is None else group
        geom.mass = 0.0 if body["kind"] != "object" else geom.mass
    return geom


def _add_zones(spec, scene, parent):
    for z in scene.get("zones", []):
        c, r = z["center"], z["radius"]
        g = parent.add_geom(name=f"zone__{z['name']}", type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[r, 0.0012, 0],
                            pos=[c[0], c[1], 0.0034], rgba=[*z["color"], 1.0], contype=0, conaffinity=0, group=1)
        g.mass = 0.0
        if z["kind"] == "hazard":
            for k, (rr, col) in enumerate(((0.75, [1.0, 0.55, 0.1, 1]), (0.45, [1.0, 0.9, 0.5, 1]))):
                gg = parent.add_geom(name=f"zone__{z['name']}_core{k}", type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[r * rr, 0.0013 + 0.0002 * k, 0],
                                     pos=[c[0], c[1], 0.0035 + 0.0002 * k], rgba=col if z["color"][0] > 0.5 else [*np.clip(np.array(z["color"]) + 0.3 * (k + 1), 0, 1), 1],
                                     contype=0, conaffinity=0, group=1)
                gg.mass = 0.0
        else:  # goal: a bright ring
            for k in range(16):
                a = 2 * math.pi * k / 16
                gg = parent.add_geom(name=f"zone__{z['name']}_ring{k}", type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.012, r * 0.2, 0.0012],
                                     pos=[c[0] + r * 0.92 * math.cos(a), c[1] + r * 0.92 * math.sin(a), 0.0036],
                                     quat=_yaw_quat(a), rgba=[1, 1, 1, 1], contype=0, conaffinity=0, group=1)
                gg.mass = 0.0


def _add_lights_and_sky(spec, scene, light_scale=1.0, light_dir_jitter=(0.0, 0.0)):
    env = scene["env"]
    L = env["light"]
    az, el = math.radians(L["azimuth_deg"] + light_dir_jitter[0]), math.radians(L["elevation_deg"] + light_dir_jitter[1])
    d = -np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    col = np.array(L["color"]) * 0.8 * light_scale
    spec.worldbody.add_light(name="w_key", pos=(-d * 4).tolist(), dir=d.tolist(), type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL,
                             diffuse=col.tolist(), specular=[0.1] * 3, castshadow=True)
    spec.worldbody.add_light(name="w_fill", pos=[0, 0, 3], dir=[0.2, 0.3, -1], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL,
                             diffuse=[0.3 * light_scale] * 3, specular=[0, 0, 0], castshadow=False)
    amb = L["ambient"] * light_scale
    spec.visual.headlight.ambient = [amb] * 3
    spec.visual.headlight.diffuse = [0.25 * light_scale] * 3
    spec.visual.headlight.specular = [0.02] * 3
    sky = spec.add_texture(name="w_sky", type=mujoco.mjtTexture.mjTEXTURE_SKYBOX, builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT,
                           rgb1=env["sky"]["top"], rgb2=env["sky"]["bottom"], width=512, height=3072)
    return sky


# ----------------------------------------------------------------------------- CPU model (full world + robot)
def world_spec(scene: dict, gates_open: bool = False, include_objects: bool = True, light_scale=1.0,
               light_dir_jitter=(0.0, 0.0)) -> mujoco.MjSpec:
    """The world alone (no robot) as an MjSpec, all mechanisms included."""
    spec = mujoco.MjSpec()
    spec.compiler.degree = False
    spec.option.timestep = 0.005
    spec.option.gravity = [0, 0, -float(scene["env"].get("gravity", 9.81))]
    spec.option.cone = mujoco.mjtCone.mjCONE_PYRAMIDAL
    spec.visual.global_.offwidth = 1280
    spec.visual.global_.offheight = 720
    spec.visual.quality.shadowsize = 4096
    spec.visual.map.znear = 0.01
    mats = _add_assets(spec, scene)
    _add_lights_and_sky(spec, scene, light_scale, light_dir_jitter)
    sx, sy = scene["room"]["size"]
    floor_mat = mats[scene["env"]["floor"]]
    fm = scene["materials"][scene["env"]["floor"]]
    floor = spec.worldbody.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[sx / 2 + 0.5, sy / 2 + 0.5, 0.05],
                                    material=floor_mat, friction=[fm.get("friction", 1.0), 0.005, 0.0001], priority=1, group=0)
    # outside the room: a plain apron so the camera never sees the void
    spec.worldbody.add_geom(name="apron", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[12, 12, 0.05], pos=[0, 0, -0.002],
                            rgba=[0.25, 0.25, 0.27, 1], contype=0, conaffinity=0, group=1)
    _add_zones(spec, scene, spec.worldbody)
    children: dict[str, list] = {}
    roots = []
    for b in scene["bodies"]:
        (children.setdefault(b["parent"], []) if b["parent"] else roots).append(b)
    mesh_cache: set = set()

    def build(parent, b):
        if b["kind"] == "object" and not include_objects:
            return
        pos = list(b["pos"])
        if b["kind"] == "part" and gates_open and b.get("joint"):
            pos[2] += b["joint"]["range"][1] * b["joint"]["axis"][2]
        body = parent.add_body(name=b["name"], pos=pos, quat=_yaw_quat(b["yaw"]))
        if b["kind"] == "object":
            body.add_freejoint(name=b["name"] + "_free")
        j = b.get("joint")
        if j and not gates_open:
            body.add_joint(name=b["name"] + "_joint", type=mujoco.mjtJoint.mjJNT_SLIDE if j["type"] == "slide" else mujoco.mjtJoint.mjJNT_HINGE,
                           axis=j["axis"], range=j["range"], limited=True, damping=j["damping"], armature=0.01)
        for g in b["geoms"]:
            collide = b["kind"] != "decor"
            grp = 4 if b["kind"] == "part" else None  # gate panels: colliding but not in group 0 (occupancy rays); group 4 is rendered
            geom = _add_geom(spec, body, scene, b, g, mats, collide=collide, group=grp, mesh_cache=mesh_cache,
                             surface_priority=b["kind"] == "fixture")
            if b["kind"] == "object" and collide:
                geom.mass = 0.0
                geom.density = 0.0
        if b["kind"] == "object":
            solid = [gm for gm in body.geoms if gm.contype]
            for gm in solid:
                gm.mass = (b["mass"] or 0.05) / max(1, len(solid))
        for c in children.get(b["name"], []):
            build(body, c)

    for b in roots:
        build(spec.worldbody, b)
    spec.worldbody.add_camera(name="overview", pos=[0, -sy * 0.95, max(sx, sy) * 1.05], xyaxes=[1, 0, 0, 0, 0.75, 0.66], fovy=60)
    spec.worldbody.add_camera(name="top", pos=[0, 0, max(sx, sy) * 1.25], xyaxes=[1, 0, 0, 0, 1, 0], fovy=70)
    return spec


def build_cpu_model(scene: dict, gates_open: bool = False, light_scale=1.0, light_dir_jitter=(0.0, 0.0),
                    head_fovy: float = 70.0) -> mujoco.MjModel:
    spec = world_spec(scene, gates_open=gates_open, light_scale=light_scale, light_dir_jitter=light_dir_jitter)
    robot = mujoco.MjSpec.from_file(str(ROBOT_XML))
    for cam in robot.cameras:
        if cam.name == "head_camera":
            cam.fovy = head_fovy
    frame = spec.worldbody.add_frame(pos=[0, 0, 0])
    spec.attach(robot, frame=frame, prefix="")
    # chase camera that keeps the robot in view from a room corner
    sx, sy = scene["room"]["size"]
    spec.worldbody.add_camera(name="chase", pos=[-sx * 0.45, -sy * 0.45, 0.9], mode=mujoco.mjtCamLight.mjCAMLIGHT_TARGETBODY,
                              targetbody="trunk_base", fovy=55)
    return spec.compile()


# ----------------------------------------------------------------------------- mjlab (training)
def add_world_to_mjlab_spec(spec: mujoco.MjSpec, scene: dict, terrain_body: str = "terrain") -> None:
    """Add the world to an mjlab scene spec (called from SceneCfg.spec_fn): static colliders flattened into the
    terrain body (world frame), gates raised and static, decor/zones visual, lights and floor material."""
    mats = _add_assets(spec, scene)
    tb = spec.body(terrain_body)
    # the terrain plane takes the world floor's material and friction
    fm = scene["materials"][scene["env"]["floor"]]
    for g in tb.geoms:
        if g.type == mujoco.mjtGeom.mjGEOM_PLANE:
            g.material = mats[scene["env"]["floor"]]
            g.friction = [float(fm.get("friction", 1.0)), 0.005, 0.0001]
            g.priority = 1
    mesh_cache: set = set()
    for b in scene["bodies"]:
        if b["kind"] == "object":
            continue
        p, q = body_world_pose(scene, b["name"])
        if b["kind"] == "part" and b.get("joint"):
            p = p + np.array(b["joint"]["axis"]) * b["joint"]["range"][1]  # gates open
        for g in b["geoms"]:
            collide = b["kind"] != "decor"
            if collide and b["kind"] in ("fixture", "part"):
                _add_geom(spec, tb, scene, b, g, mats, frame_pos=p, frame_quat=q, collide=True, mesh_cache=mesh_cache)
            else:
                _add_geom(spec, spec.worldbody, scene, b, g, mats, frame_pos=p, frame_quat=q, collide=False, mesh_cache=mesh_cache)
    _add_zones(spec, scene, spec.worldbody)
    _add_lights_and_sky(spec, scene)
    spec.option.gravity = [0, 0, -float(scene["env"].get("gravity", 9.81))]


# ----------------------------------------------------------------------------- height map / traversability
def height_map(scene: dict, res: float = 0.02, ray_top: float = 0.40, gates_open: bool = True) -> dict:
    """Top-down height of static colliders on a `res` grid over the room (rays start at `ray_top`, so overhangs
    higher than the robot are ignored). Returns {'H', 'x0', 'y0', 'res', 'shape'}."""
    spec = world_spec(scene, gates_open=gates_open, include_objects=False)
    m = spec.compile()
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    sx, sy = scene["room"]["size"]
    nx, ny = int(round(sx / res)), int(round(sy / res))
    x0, y0 = -sx / 2 + res / 2, -sy / 2 + res / 2
    H = np.zeros((nx, ny), np.float32)
    geomgroup = np.array([1, 0, 0, 0, 0, 0], np.uint8)  # group 0 only: static colliders
    gid = np.zeros(1, np.int32)
    for i in range(nx):
        for j in range(ny):
            pnt = np.array([x0 + i * res, y0 + j * res, ray_top])
            dist = mujoco.mj_ray(m, d, pnt, np.array([0, 0, -1.0]), geomgroup, 1, -1, gid)
            H[i, j] = ray_top - dist if dist >= 0 else 0.0
    return {"H": H, "x0": x0, "y0": y0, "res": res, "shape": (nx, ny)}
