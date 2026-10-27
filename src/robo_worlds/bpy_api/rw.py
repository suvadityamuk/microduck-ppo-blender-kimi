"""`rw` -- the world-building API an LLM uses *inside Blender* to design a world for the Microduck robot.

This module only runs inside Blender's Python (``Blender --background --python runner.py``).
It wraps bpy so a designer script can:

* lay out a room at the scale of a 25 cm bipedal robot: walls, doorways, ramps, steps, platforms, rubble,
  floor patches with their own friction (ice, rubber, sand ...), and the gravity of the place,
* model props from primitives or arbitrary Blender meshes (modifiers, booleans, lathes ...),
* add mechanisms the robot operates with its body: gates opened by pressure plates, balls and crates it pushes,
* paint everything with procedural node materials baked to PNG swatches (no image model anywhere),
* mark hazard and goal zones and declare the (often multi-step) tasks the robot must learn,
* ``save()`` everything as ``scene.json`` + OBJ meshes + textures for the MuJoCo side (``robo_worlds.duck_scene``).

Coordinates: metres, z up, the floor is the z = 0 plane and the room is centred on the origin.
Angles are radians unless the name says ``_deg``.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

# ----------------------------------------------------------------------------- robot / world facts
ROOM_MIN, ROOM_MAX = 1.6, 4.0      # side length of the room (m)
WALL_H_MIN, WALL_H_MAX = 0.12, 0.6
DUCK_RADIUS = 0.09                 # footprint radius used for clearance checks
DUCK_HEIGHT = 0.27                 # standing height incl. head
PASSAGE_MIN = 0.26                 # narrowest gap the robot may be asked to walk through
STEP_MAX = 0.025                   # tallest single step (the stock gait handles ~1.5 cm, training may stretch it)
SLOPE_MAX_DEG = 12.0
RAMP_RISE_MAX = 0.12
BUMP_MAX = 0.015
PATTERNS = ("flat", "noise", "wood", "tiles", "bricks", "checker", "marble", "brushed", "stripes", "dots",
            "fabric", "concrete", "rust", "hex")
TASK_KINDS = ("goto", "gate", "push", "visit")
MULTI_STEP = ("gate", "push", "visit")


class WorldError(ValueError):
    """Raised for design mistakes the LLM must fix (the message is fed back to it)."""


def _v3(v, name="vector"):
    v = [float(x) for x in v]
    if len(v) != 3:
        raise WorldError(f"{name} must have 3 components, got {v}")
    return v


def _rgb(c):
    c = [float(x) for x in c][:3]
    if len(c) != 3:
        raise WorldError(f"colour must be (r, g, b) in 0..1, got {c}")
    return [min(1.0, max(0.0, x)) for x in c]


def _unit(v, name):
    v = np.array(_v3(v, name))
    n = np.linalg.norm(v)
    if n < 1e-6:
        raise WorldError(f"{name} must be non-zero")
    return (v / n).tolist()


def _snake(s):
    s = re.sub(r"[^a-z0-9_]+", "_", str(s).lower()).strip("_")
    if not s:
        raise WorldError("names must contain letters or digits")
    return s


# ----------------------------------------------------------------------------- materials
class Material:
    """A procedural material. ``pattern`` picks a node graph; ``color``/``color2`` its two colours.

    scale: pattern repeats across one texture tile (tiles are 15 cm on objects, 50 cm on floor/table/wall;
    periodic patterns are snapped to integers so they tile seamlessly).
    roughness 0..1, metallic 0..1, emission >= 0 (glow strength), alpha < 1 for glass-like looks.
    """

    def __init__(self, name, color=(0.7, 0.7, 0.7), pattern="flat", color2=None, scale=6.0, roughness=0.6,
                 metallic=0.0, emission=0.0, alpha=1.0, stretch=1.0, friction=1.0):
        if pattern not in PATTERNS:
            raise WorldError(f"material {name!r}: pattern must be one of {PATTERNS}")
        self.name = _snake(name)
        self.color = _rgb(color)
        self.color2 = _rgb(color2) if color2 is not None else [max(0.0, c * 0.6) for c in self.color]
        self.pattern = pattern
        self.scale = float(max(0.5, min(60.0, scale)))
        self.roughness = float(min(1.0, max(0.0, roughness)))
        self.metallic = float(min(1.0, max(0.0, metallic)))
        self.emission = float(max(0.0, min(5.0, emission)))
        self.alpha = float(min(1.0, max(0.25, alpha)))
        self.stretch = float(max(0.2, min(20.0, stretch)))
        self.friction = float(max(0.05, min(2.0, friction)))  # sliding friction of surfaces made of this material (ice 0.05)
        self._baked = None

    # -- node graph ------------------------------------------------------------------
    def _build_nodes(self, mat):
        mat.use_nodes = True
        nt = mat.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        emit = nt.nodes.new("ShaderNodeEmission")
        emit.inputs["Strength"].default_value = 1.0
        nt.links.new(emit.outputs[0], out.inputs[0])
        coord = nt.nodes.new("ShaderNodeTexCoord")
        mapping = nt.nodes.new("ShaderNodeMapping")
        nt.links.new(coord.outputs["UV"], mapping.inputs["Vector"])
        c1 = (*self.color, 1.0)
        c2 = (*self.color2, 1.0)
        p = self.pattern
        s = self.scale
        periodic = p in ("tiles", "bricks", "checker", "stripes", "fabric", "hex", "dots")
        if periodic:
            s = max(1.0, round(s))
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = c1
        ramp.color_ramp.elements[1].color = c2
        mapping.inputs["Scale"].default_value = (s, s / self.stretch, s)

        def link_fac(node_out):
            nt.links.new(node_out, ramp.inputs["Fac"])
            nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])

        if p == "flat":
            emit.inputs["Color"].default_value = c1
        elif p in ("noise", "concrete", "rust"):
            n = nt.nodes.new("ShaderNodeTexNoise")
            n.inputs["Scale"].default_value = 1.0
            n.inputs["Detail"].default_value = {"noise": 2.0, "concrete": 6.0, "rust": 8.0}[p]
            n.inputs["Roughness"].default_value = {"noise": 0.5, "concrete": 0.7, "rust": 0.85}[p]
            nt.links.new(mapping.outputs[0], n.inputs["Vector"])
            ramp.color_ramp.elements[0].position = {"noise": 0.35, "concrete": 0.4, "rust": 0.45}[p]
            ramp.color_ramp.elements[1].position = {"noise": 0.65, "concrete": 0.6, "rust": 0.6}[p]
            link_fac(n.outputs["Fac"])
        elif p in ("wood", "marble", "brushed", "stripes"):
            w = nt.nodes.new("ShaderNodeTexWave")
            w.wave_type = "BANDS"
            w.bands_direction = "Y" if p != "marble" else "DIAGONAL"
            w.inputs["Scale"].default_value = 1.0
            w.inputs["Distortion"].default_value = {"wood": 3.0, "marble": 8.0, "brushed": 0.3, "stripes": 0.0}[p]
            w.inputs["Detail"].default_value = {"wood": 3.0, "marble": 4.0, "brushed": 6.0, "stripes": 0.0}[p]
            w.inputs["Detail Scale"].default_value = {"wood": 1.5, "marble": 1.0, "brushed": 40.0, "stripes": 1.0}[p]
            nt.links.new(mapping.outputs[0], w.inputs["Vector"])
            if p == "stripes":
                ramp.color_ramp.interpolation = "CONSTANT"
                ramp.color_ramp.elements[1].position = 0.5
            if p == "brushed":
                ramp.color_ramp.elements[0].position = 0.3
                ramp.color_ramp.elements[1].position = 0.7
            link_fac(w.outputs["Fac"])
        elif p in ("tiles", "bricks"):
            b = nt.nodes.new("ShaderNodeTexBrick")
            b.offset = 0.0 if p == "tiles" else 0.5
            b.inputs["Scale"].default_value = 1.0
            b.inputs["Mortar Size"].default_value = 0.03 if p == "tiles" else 0.04
            b.inputs["Color1"].default_value = c1
            b.inputs["Color2"].default_value = (*[min(1, x * 1.15) for x in self.color], 1.0)
            b.inputs["Mortar"].default_value = c2
            if p == "tiles":
                b.inputs["Brick Width"].default_value = 1.0
                b.inputs["Row Height"].default_value = 1.0
            else:
                b.inputs["Brick Width"].default_value = 1.0
                b.inputs["Row Height"].default_value = 0.5
            nt.links.new(mapping.outputs[0], b.inputs["Vector"])
            nt.links.new(b.outputs["Color"], emit.inputs["Color"])
        elif p == "checker":
            ch = nt.nodes.new("ShaderNodeTexChecker")
            ch.inputs["Scale"].default_value = 1.0
            ch.inputs["Color1"].default_value = c1
            ch.inputs["Color2"].default_value = c2
            nt.links.new(mapping.outputs[0], ch.inputs["Vector"])
            nt.links.new(ch.outputs["Color"], emit.inputs["Color"])
        elif p in ("dots", "hex"):
            vo = nt.nodes.new("ShaderNodeTexVoronoi")
            vo.inputs["Scale"].default_value = 1.0
            vo.inputs["Randomness"].default_value = 0.0 if p == "dots" else 0.0
            vo.distance = "EUCLIDEAN"
            vo.feature = "F1" if p == "dots" else "DISTANCE_TO_EDGE"
            nt.links.new(mapping.outputs[0], vo.inputs["Vector"])
            ramp.color_ramp.interpolation = "CONSTANT"
            ramp.color_ramp.elements[1].position = 0.3 if p == "dots" else 0.06
            if p == "hex":  # thin edges in colour2, cells in colour1
                ramp.color_ramp.elements[0].color, ramp.color_ramp.elements[1].color = c2, c1
            link_fac(vo.outputs["Distance"])
        elif p == "fabric":
            w1 = nt.nodes.new("ShaderNodeTexWave")
            w1.bands_direction = "X"
            w1.inputs["Scale"].default_value = 1.0
            w2 = nt.nodes.new("ShaderNodeTexWave")
            w2.bands_direction = "Y"
            w2.inputs["Scale"].default_value = 1.0
            mix = nt.nodes.new("ShaderNodeMath")
            mix.operation = "MULTIPLY"
            nt.links.new(mapping.outputs[0], w1.inputs["Vector"])
            nt.links.new(mapping.outputs[0], w2.inputs["Vector"])
            nt.links.new(w1.outputs["Fac"], mix.inputs[0])
            nt.links.new(w2.outputs["Fac"], mix.inputs[1])
            link_fac(mix.outputs[0])
        return mat

    def bake(self, out_png: Path, size: int = 512):
        """Bake the colour of this material on a unit plane to a PNG swatch (one UV repeat)."""
        if self.pattern == "flat":
            return None  # flat colours need no texture
        scene = bpy.context.scene
        mat = bpy.data.materials.new(f"_bake_{self.name}")
        self._build_nodes(mat)
        bpy.ops.mesh.primitive_plane_add(size=1.0, calc_uvs=True)
        plane = bpy.context.active_object
        plane.data.materials.append(mat)
        img = bpy.data.images.new(f"_bake_{self.name}", size, size, alpha=False)
        tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        mat.node_tree.nodes.active = tex_node
        bpy.ops.object.select_all(action="DESELECT")
        plane.select_set(True)
        bpy.context.view_layer.objects.active = plane
        scene.render.bake.margin = 2
        scene.render.bake.use_clear = True
        bpy.ops.object.bake(type="EMIT", use_clear=True, margin=2)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        # MuJoCo shades without gamma correction, so store the linear values as-is ("Raw" view transform).
        img.filepath_raw = str(out_png)
        img.file_format = "PNG"
        img.save_render(str(out_png))
        bpy.data.objects.remove(plane, do_unlink=True)
        bpy.data.images.remove(img)
        bpy.data.materials.remove(mat)
        return out_png

    def to_json(self, texture_rel: str | None):
        return {"name": self.name, "rgba": [*self.color, self.alpha], "color2": self.color2, "pattern": self.pattern,
                "texture": texture_rel, "roughness": self.roughness, "metallic": self.metallic,
                "emission": self.emission, "friction": self.friction}


# ----------------------------------------------------------------------------- joints
class Joint:
    def __init__(self, kind, axis, range, damping, stiffness, friction, spring_ref=0.0):
        self.kind = kind
        self.axis = _unit(axis, "joint axis")
        lo, hi = float(range[0]), float(range[1])
        if hi <= lo:
            raise WorldError(f"joint range must be (low, high) with high > low, got {range}")
        self.range = [lo, hi]
        self.damping = float(max(0.0, damping))
        self.stiffness = float(max(0.0, stiffness))
        self.friction = float(max(0.0, friction))
        self.spring_ref = float(spring_ref)

    def to_json(self):
        return {"type": self.kind, "axis": self.axis, "range": self.range, "damping": self.damping,
                "stiffness": self.stiffness, "frictionloss": self.friction, "springref": self.spring_ref}


def hinge(axis=(0, 0, 1), range=(0.0, 1.57), damping=0.02, stiffness=0.0, friction=0.0, spring_ref=0.0):
    """Revolute joint about `axis` through the child body's origin. `range` in radians."""
    lo, hi = range
    if hi - lo > 2 * math.pi + 1e-6:
        raise WorldError("hinge range may not exceed a full turn")
    return Joint("hinge", axis, range, damping, stiffness, friction, spring_ref)


def slide(axis=(1, 0, 0), range=(0.0, 0.08), damping=1.0, stiffness=0.0, friction=0.0, spring_ref=0.0):
    """Prismatic joint along `axis`. `range` in metres (keep travel <= 0.12 so the arm can follow)."""
    return Joint("slide", axis, range, damping, stiffness, friction, spring_ref)


# ----------------------------------------------------------------------------- geometry helpers
def _active_or(obj):
    return obj if obj is not None else bpy.context.active_object


def mesh_box(size, bevel=0.0, segments=3, name="box"):
    """A box (full extents) centred at the origin, optionally bevelled. Returns the Blender object."""
    sx, sy, sz = _v3(size, "size")
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width = float(min(bevel, min(sx, sy, sz) * 0.45))
        m.segments = int(max(1, segments))
        m.limit_method = "ANGLE"
    return o


def mesh_cylinder(radius, length, vertices=48, bevel=0.0, axis="z", name="cylinder"):
    """A cylinder centred at the origin along `axis` ('x','y' or 'z')."""
    bpy.ops.mesh.primitive_cylinder_add(radius=float(radius), depth=float(length), vertices=int(vertices))
    o = bpy.context.active_object
    o.name = name
    if axis == "x":
        o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "y":
        o.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    if bevel > 0:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width = float(min(bevel, radius * 0.5, length * 0.45))
        m.segments = 3
        m.limit_method = "ANGLE"
    return o


def mesh_sphere(radius, segments=32, name="sphere"):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=float(radius), segments=int(segments), ring_count=int(segments // 2))
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return o


def mesh_torus(major_radius, minor_radius, name="torus"):
    bpy.ops.mesh.primitive_torus_add(major_radius=float(major_radius), minor_radius=float(minor_radius))
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return o


def mesh_lathe(profile, segments=48, name="lathe", smooth=True):
    """Revolve a 2D profile [(r, z), ...] (r >= 0, from bottom to top) around the z axis: bowls, vases, bottles.

    The profile is an open polyline; the first and last points are closed onto the axis automatically.
    """
    pts = [(float(r), float(z)) for r, z in profile]
    if len(pts) < 2:
        raise WorldError("lathe profile needs at least 2 points")
    if pts[0][0] > 1e-6:
        pts = [(0.0, pts[0][1])] + pts
    if pts[-1][0] > 1e-6:
        pts = pts + [(0.0, pts[-1][1])]
    verts, faces = [], []
    n = int(segments)
    for r, z in pts:
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for k in range(len(pts) - 1):
        for i in range(n):
            a, b = k * n + i, k * n + (i + 1) % n
            c, d = (k + 1) * n + (i + 1) % n, (k + 1) * n + i
            faces.append((a, b, c, d))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(clean_customdata=False)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    # merge the degenerate ring(s) on the axis
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    if smooth:
        bpy.ops.object.shade_smooth()
    return o


def mesh_prism(points, height, name="prism"):
    """Extrude a closed 2D polygon [(x, y), ...] (counter-clockwise) from z=0 to z=height."""
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 3:
        raise WorldError("prism needs >= 3 points")
    n = len(pts)
    verts = [(x, y, 0.0) for x, y in pts] + [(x, y, float(height)) for x, y in pts]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(clean_customdata=False)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def mesh_boolean(a, b, op="DIFFERENCE", keep_b=False):
    """Boolean modifier on `a` with `b` (DIFFERENCE / UNION / INTERSECT). `b` is hidden unless keep_b."""
    m = a.modifiers.new(f"bool_{op.lower()}", "BOOLEAN")
    m.operation = op
    m.object = b
    m.solver = "EXACT"
    if not keep_b:
        b.hide_set(True)
        b.hide_render = True
        b["_rw_helper"] = True
    return a


def mesh_join(objects, name="joined"):
    """Join several Blender mesh objects into one."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


def move(obj, pos=None, rot_deg=None, scale=None):
    """Set an object's location / rotation (degrees, XYZ) / scale. Returns the object."""
    if pos is not None:
        obj.location = Vector(_v3(pos, "pos"))
    if rot_deg is not None:
        obj.rotation_euler = [math.radians(a) for a in _v3(rot_deg, "rot_deg")]
    if scale is not None:
        obj.scale = Vector(_v3(scale, "scale"))
    return obj


def _evaluated_triangles(obj):
    """Return (verts Nx3 in object-world space, tris Mx3, uvs Mx3x2 or None, normals Mx3x3)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        me.calc_loop_triangles()
        mw = np.array(obj.matrix_world)
        V = np.array([v.co[:] for v in me.vertices], dtype=np.float64)
        if len(V) == 0:
            raise WorldError(f"mesh {obj.name!r} has no vertices")
        Vh = np.c_[V, np.ones(len(V))] @ mw.T
        V = Vh[:, :3]
        tris = np.array([[me.loops[i].vertex_index for i in t.loops] for t in me.loop_triangles], dtype=np.int64)
        if len(tris) == 0:
            raise WorldError(f"mesh {obj.name!r} has no faces")
        uvs = None
        if me.uv_layers.active is not None:
            uv_data = me.uv_layers.active.data
            uvs = np.array([[uv_data[i].uv[:] for i in t.loops] for t in me.loop_triangles], dtype=np.float64)
        # normals: smooth faces use corner normals, flat faces the face normal
        R = mw[:3, :3]
        cn = np.array([n.vector[:] for n in me.corner_normals], dtype=np.float64) if len(me.corner_normals) else None
        normals = np.zeros((len(tris), 3, 3))
        for k, t in enumerate(me.loop_triangles):
            if me.polygons[t.polygon_index].use_smooth and cn is not None:
                normals[k] = cn[list(t.loops)] @ R.T
            else:
                fn = np.array(t.normal[:]) @ R.T
                normals[k] = fn
        nrm = np.linalg.norm(normals, axis=2, keepdims=True)
        normals = normals / np.where(nrm < 1e-9, 1.0, nrm)
        if np.linalg.det(R) < 0:  # mirrored transform flips winding
            tris = tris[:, ::-1]
            uvs = uvs[:, ::-1] if uvs is not None else None
            normals = normals[:, ::-1]
        return V, tris, uvs, normals
    finally:
        ev.to_mesh_clear()


def _box_project_uvs(V, tris, normals, metres_per_repeat):
    """Triplanar box projection: each triangle gets UVs from the plane most aligned with its normal."""
    uvs = np.zeros((len(tris), 3, 2))
    fn = normals.mean(axis=1)
    ax = np.argmax(np.abs(fn), axis=1)
    P = V[tris] / metres_per_repeat  # (M,3,3)
    for k in range(len(tris)):
        a = ax[k]
        if a == 0:
            uvs[k] = P[k][:, [1, 2]]
        elif a == 1:
            uvs[k] = P[k][:, [0, 2]]
        else:
            uvs[k] = P[k][:, [0, 1]]
    return uvs


def _write_obj(path: Path, V, tris, uvs, normals):
    # compact: unique positions; per-corner uv/normal
    lines = ["# exported by robo_worlds rw"]
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in V]
    lines += [f"vt {u:.6f} {v:.6f}" for tri in uvs for u, v in tri]
    lines += [f"vn {x:.5f} {y:.5f} {z:.5f}" for tri in normals for x, y, z in tri]
    for k, t in enumerate(tris):
        idx = [f"{t[i] + 1}/{3 * k + i + 1}/{3 * k + i + 1}" for i in range(3)]
        lines.append("f " + " ".join(idx))
    path.write_text("\n".join(lines) + "\n")



def _quat_of(rot_deg=None, axis="z"):
    """Quaternion (w, x, y, z) of an XYZ euler rotation (degrees) applied after aligning the primitive's axis."""
    q_axis = {"z": Quaternion(), "x": Euler((0, math.pi / 2, 0)).to_quaternion(),
              "y": Euler((math.pi / 2, 0, 0)).to_quaternion()}[axis]
    q = Euler([math.radians(a) for a in (rot_deg or (0, 0, 0))]).to_quaternion() if rot_deg is not None else Quaternion()
    r = q @ q_axis
    return [r.w, r.x, r.y, r.z]


# ----------------------------------------------------------------------------- bodies
class Body:
    """A rigid body: a static fixture, a decor piece, a moving part (gate) or a free object (ball, crate)."""

    def __init__(self, world, name, pos, yaw_deg=0.0, parent=None, joint=None, kind="fixture"):
        self.world = world
        self.name = _snake(name)
        self.pos = _v3(pos, f"{self.name}.pos")
        self.yaw = math.radians(float(yaw_deg))
        self.parent = parent
        self.joint = joint
        self.kind = kind  # fixture | decor | part | object
        self.geoms = []
        self.mass = None
        self.spawn = None
        self.children = []
        self.role = None  # wall | ramp | steps | platform | patch | bumps | gate_frame | gate | plate | ball | crate

    # -- primitives (sizes are FULL extents; rot_deg = extra XYZ rotation in degrees) ------------------
    def _add(self, g):
        if g["name"] in {x["name"] for x in self.geoms}:
            raise WorldError(f"body {self.name!r} already has a geom named {g['name']!r}")
        self.geoms.append(g)
        return self

    def _common(self, name, pos, material, collision, rot_deg, axis="z"):
        return {"name": _snake(name), "pos": _v3(pos, "pos"), "quat": _quat_of(rot_deg, axis),
                "material": self.world._mat_name(material), "collision": bool(collision)}

    def box(self, name, size, pos=(0, 0, 0), material=None, rot_deg=None, collision=True, yaw_deg=None):
        sx, sy, sz = _v3(size, "size")
        if min(sx, sy, sz) <= 0:
            raise WorldError(f"{self.name}.{name}: box size must be positive full extents, got {size}")
        if yaw_deg is not None and rot_deg is None:
            rot_deg = (0, 0, yaw_deg)
        return self._add({"kind": "box", "size": [sx / 2, sy / 2, sz / 2], **self._common(name, pos, material, collision, rot_deg)})

    def cylinder(self, name, radius, length, pos=(0, 0, 0), axis="z", material=None, rot_deg=None, collision=True):
        if radius <= 0 or length <= 0:
            raise WorldError(f"{self.name}.{name}: radius/length must be positive")
        if axis not in ("x", "y", "z"):
            raise WorldError("axis must be 'x', 'y' or 'z'")
        return self._add({"kind": "cylinder", "size": [float(radius), float(length) / 2],
                          **self._common(name, pos, material, collision, rot_deg, axis)})

    def capsule(self, name, radius, length, pos=(0, 0, 0), axis="z", material=None, rot_deg=None, collision=True):
        if radius <= 0 or length <= 0:
            raise WorldError(f"{self.name}.{name}: radius/length must be positive")
        return self._add({"kind": "capsule", "size": [float(radius), float(length) / 2],
                          **self._common(name, pos, material, collision, rot_deg, axis)})

    def sphere(self, name, radius, pos=(0, 0, 0), material=None, collision=True):
        if radius <= 0:
            raise WorldError(f"{self.name}.{name}: radius must be positive")
        return self._add({"kind": "sphere", "size": [float(radius)], **self._common(name, pos, material, collision, None)})

    def mesh(self, name, obj, material=None, collision=None, uv_scale=0.25):
        """Attach a Blender mesh object (its world transform is read in this body's frame).
        On fixtures and objects the convex hull is the collider (collision=False makes it visual only);
        on decor and moving parts meshes are visual only."""
        if obj is None or obj.type != "MESH":
            raise WorldError(f"{self.name}.{name}: mesh() needs a Blender MESH object")
        if collision is None:
            collision = self.kind in ("fixture", "object")
        obj["_rw_used"] = True
        V, *_ = _evaluated_triangles(obj)
        if len(V) > 60000:
            raise WorldError(f"{self.name}.{name}: mesh has {len(V)} vertices; keep meshes under 60k vertices")
        return self._add({"name": _snake(name), "kind": "mesh", "obj": obj, "material": self.world._mat_name(material),
                          "collision": bool(collision) and self.kind in ("fixture", "object"), "uv_scale": float(uv_scale),
                          "pos": ((V.min(axis=0) + V.max(axis=0)) / 2).tolist(), "quat": [1.0, 0.0, 0.0, 0.0]})

    def child(self, name, joint, pos, yaw_deg=0.0):
        c = Body(self.world, name, pos, yaw_deg, parent=self, joint=joint, kind="part")
        self.children.append(c)
        self.world._register(c)
        return c

    # -- export ---------------------------------------------------------------------------
    def world_matrix(self):
        M = Matrix.Translation(Vector(self.pos)) @ Matrix.Rotation(self.yaw, 4, "Z")
        return (self.parent.world_matrix() @ M) if self.parent is not None else M

    def to_json(self, out_dir: Path):
        geoms = []
        for g in self.geoms:
            gj = {k: v for k, v in g.items() if k != "obj"}
            if g["kind"] == "mesh":
                V, tris, uvs, normals = _evaluated_triangles(g["obj"])
                if uvs is None:
                    uvs = _box_project_uvs(V, tris, normals, g["uv_scale"])
                rel = f"meshes/{self.name}__{g['name']}.obj"
                _write_obj(out_dir / rel, V, tris, uvs, normals)
                gj["file"] = rel
                gj["bbox"] = [V.min(axis=0).tolist(), V.max(axis=0).tolist()]
            geoms.append(gj)
        return {"name": self.name, "kind": self.kind, "role": self.role, "parent": self.parent.name if self.parent else None,
                "pos": self.pos, "yaw": self.yaw, "joint": self.joint.to_json() if self.joint else None,
                "geoms": geoms, "mass": self.mass, "spawn": self.spawn}

    # -- footprint (world xy boxes of colliding geometry, for layout checks) --------------
    def _aabbs(self):
        out = []
        M = np.array(self.world_matrix())
        for g in self.geoms:
            if not g["collision"]:
                continue
            if g["kind"] == "mesh":
                V, *_ = _evaluated_triangles(g["obj"])
                P = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3]
                out.append((P.min(axis=0), P.max(axis=0)))
                continue
            s = np.array(g["size"], dtype=float)
            if g["kind"] == "box":
                h = s
            elif g["kind"] == "sphere":
                h = np.full(3, s[0])
            else:
                h = np.array([s[0], s[0], s[1] + (s[0] if g["kind"] == "capsule" else 0)])
            R = np.array(Quaternion(g["quat"]).to_matrix())
            corners = np.array([[a, b, c] for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]) * h
            P = corners @ R.T + np.array(g["pos"])
            P = (np.c_[P, np.ones(len(P))] @ M.T)[:, :3]
            out.append((P.min(axis=0), P.max(axis=0)))
        return out


# ----------------------------------------------------------------------------- the world
class World:
    def __init__(self, name, description="", theme=""):
        self.name = _snake(name)
        self.description = str(description)
        self.theme = str(theme)
        self.materials = {}
        self.bodies = {}
        self.order = []
        self.zones = []
        self.plates = []
        self.gates = {}
        self.tasks = []
        self.room_cfg = None
        self.env = {"sky": {"top": [0.35, 0.5, 0.7], "bottom": [0.05, 0.05, 0.08]},
                    "light": {"color": [1.0, 0.97, 0.92], "ambient": 0.3, "azimuth_deg": 30.0, "elevation_deg": 60.0},
                    "floor": None, "gravity": 9.81}
        self._default_mat = self.material("default_grey", color=(0.6, 0.6, 0.62))

    # -- look ------------------------------------------------------------------------------
    def material(self, name, **kw):
        m = Material(name, **kw)
        if m.name in self.materials:
            raise WorldError(f"material {m.name!r} already exists")
        self.materials[m.name] = m
        return m

    def _mat_name(self, material):
        if material is None:
            return self._default_mat.name
        if isinstance(material, Material):
            if material.name not in self.materials:
                raise WorldError(f"material {material.name!r} was not created via world.material()")
            return material.name
        if material in self.materials:
            return material
        raise WorldError(f"unknown material {material!r}")

    def sky(self, top, bottom):
        self.env["sky"] = {"top": _rgb(top), "bottom": _rgb(bottom)}
        return self

    def light(self, color=(1, 0.97, 0.92), azimuth_deg=30.0, elevation_deg=60.0, ambient=0.3):
        self.env["light"] = {"color": [max(0.3, c) for c in _rgb(color)], "azimuth_deg": float(azimuth_deg) % 360,
                             "elevation_deg": float(min(85.0, max(25.0, elevation_deg))), "ambient": float(min(0.6, max(0.1, ambient)))}
        return self

    def gravity(self, g):
        """Gravity magnitude in m/s^2 (Earth 9.81, Mars 3.71, Moon 1.62)."""
        g = float(g)
        if not 1.5 <= g <= 12.0:
            raise WorldError("gravity must be between 1.5 and 12 m/s^2")
        self.env["gravity"] = g
        return self

    # -- the room ------------------------------------------------------------------------------
    def room(self, size=(3.0, 3.0), floor=None, wall=None, wall_height=0.3):
        """The enclosing room: a floor of `size` (x, y) metres centred on the origin and four walls around it."""
        sx, sy = float(size[0]), float(size[1])
        if not (ROOM_MIN <= sx <= ROOM_MAX and ROOM_MIN <= sy <= ROOM_MAX):
            raise WorldError(f"room size must be {ROOM_MIN}..{ROOM_MAX} m per side, got {size}")
        if not WALL_H_MIN <= wall_height <= WALL_H_MAX:
            raise WorldError(f"wall_height must be {WALL_H_MIN}..{WALL_H_MAX} m")
        self.room_cfg = {"size": [sx, sy], "wall_height": float(wall_height)}
        self.env["floor"] = self._mat_name(floor)
        b = self.fixture("room_walls", (0, 0, 0))
        b.role = "wall"
        t = 0.06
        wm = wall or floor
        b.box("north", (sx + 2 * t, t, wall_height), (0, sy / 2 + t / 2, wall_height / 2), material=wm)
        b.box("south", (sx + 2 * t, t, wall_height), (0, -sy / 2 - t / 2, wall_height / 2), material=wm)
        b.box("east", (t, sy, wall_height), (sx / 2 + t / 2, 0, wall_height / 2), material=wm)
        b.box("west", (t, sy, wall_height), (-sx / 2 - t / 2, 0, wall_height / 2), material=wm)
        return b

    # -- bodies ----------------------------------------------------------------------------
    def _register(self, b: Body):
        if b.name in self.bodies:
            raise WorldError(f"a body named {b.name!r} already exists")
        self.bodies[b.name] = b
        self.order.append(b.name)

    def fixture(self, name, pos, yaw_deg=0.0):
        """A static, colliding body (furniture, crates, pillars, machinery). `pos` z is usually 0."""
        b = Body(self, name, pos, yaw_deg, kind="fixture")
        self._register(b)
        return b

    def decor(self, name, pos, yaw_deg=0.0):
        """A static, NON-colliding body: purely visual (posters, hanging lamps, distant scenery, floor decals)."""
        b = Body(self, name, pos, yaw_deg, kind="decor")
        self._register(b)
        return b

    def wall(self, name, start, end, height=0.25, thickness=0.04, material=None, openings=()):
        """A straight interior wall from `start` (x, y) to `end` (x, y). `openings` = [(distance_from_start, width), ...]
        leaves doorways (width >= 0.30) in it; put a gate() in a doorway to close it."""
        p0, p1 = np.array(start, float), np.array(end, float)
        L = float(np.linalg.norm(p1 - p0))
        if L < 0.1:
            raise WorldError(f"wall {name!r} is shorter than 10 cm")
        if not 0.08 <= height <= WALL_H_MAX or not 0.02 <= thickness <= 0.2:
            raise WorldError(f"wall {name!r}: height 0.08..{WALL_H_MAX} m, thickness 0.02..0.2 m")
        yaw = math.degrees(math.atan2(*(p1 - p0)[::-1]))
        b = self.fixture(name, (*p0, 0.0), yaw_deg=yaw)
        b.role = "wall"
        cuts = sorted((float(d), float(w)) for d, w in openings)
        x = 0.0
        k = 0
        for d, w in cuts + [(L + 1e9, 0.0)]:
            if w and w < 0.30:
                raise WorldError(f"wall {name!r}: doorway width {w} < 0.30 m (the robot needs ~0.26 m)")
            a, z = x, min(L, d - w / 2)
            if z - a > 0.01:
                b.box(f"seg{k}", (z - a, thickness, height), ((a + z) / 2, 0, height / 2), material=material)
                k += 1
            x = d + w / 2
        return b

    def patch(self, name, center, size, material, yaw_deg=0.0):
        """A floor surface patch (2 mm proud) whose friction is its material's `friction`: ice 0.05-0.15,
        polished metal 0.3, wood 0.6, rubber mat 1.5. Patches may overlap the floor and each other."""
        b = self.fixture(name, (center[0], center[1], 0.0), yaw_deg)
        b.role = "patch"
        sx, sy = float(size[0]), float(size[1])
        if not (0.15 <= sx <= ROOM_MAX and 0.15 <= sy <= ROOM_MAX):
            raise WorldError(f"patch {name!r}: each side 0.15..{ROOM_MAX} m")
        b.box("surface", (sx, sy, 0.002), (0, 0, 0.001), material=material)
        return b

    def ramp(self, name, start, end, width=0.4, rise=0.06, material=None):
        """A solid wedge rising from the floor at `start` (x, y) to height `rise` at `end` (x, y).
        Slope <= 12 degrees; pair it with a platform() of the same height at its top end."""
        p0, p1 = np.array(start, float), np.array(end, float)
        L = float(np.linalg.norm(p1 - p0))
        rise = float(rise)
        if not 0.01 <= rise <= RAMP_RISE_MAX:
            raise WorldError(f"ramp {name!r}: rise must be 0.01..{RAMP_RISE_MAX} m")
        slope = math.degrees(math.atan2(rise, L))
        if slope > SLOPE_MAX_DEG:
            raise WorldError(f"ramp {name!r} is {slope:.1f} degrees steep; make it longer (max {SLOPE_MAX_DEG} degrees, "
                             f"needs length >= {rise / math.tan(math.radians(SLOPE_MAX_DEG)):.2f} m)")
        if not PASSAGE_MIN + 0.04 <= width <= 2.0:
            raise WorldError(f"ramp {name!r}: width {PASSAGE_MIN + 0.04}..2.0 m")
        yaw = math.degrees(math.atan2(*(p1 - p0)[::-1]))
        b = self.fixture(name, (*p0, 0.0), yaw_deg=yaw)
        b.role = "ramp"
        w = width / 2
        verts = [(0, -w, 0), (L, -w, 0), (L, -w, rise), (0, w, 0), (L, w, 0), (L, w, rise)]
        faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (0, 2, 5, 3)]
        me = bpy.data.meshes.new(f"{name}_wedge")
        me.from_pydata(verts, [], faces)
        me.validate()
        me.update()
        o = bpy.data.objects.new(f"{name}_wedge", me)
        bpy.context.scene.collection.objects.link(o)
        b.mesh("wedge", o, material=material, collision=True, uv_scale=0.4)
        b.ramp_info = {"start": p0.tolist(), "end": p1.tolist(), "width": float(width), "rise": rise}
        return b

    def platform(self, name, center, size, height, material=None, yaw_deg=0.0):
        """A raised flat area (a stage, a dais, a deck). Reach it with a ramp() or steps(); a bare edge taller than
        2.5 cm is a wall to the robot."""
        if not 0.005 <= height <= RAMP_RISE_MAX:
            raise WorldError(f"platform {name!r}: height 0.005..{RAMP_RISE_MAX} m")
        b = self.fixture(name, (center[0], center[1], 0.0), yaw_deg)
        b.role = "platform"
        b.box("deck", (float(size[0]), float(size[1]), float(height)), (0, 0, height / 2), material=material)
        return b

    def steps(self, name, start, end, width=0.4, n=3, total_rise=0.06, material=None):
        """`n` solid steps climbing from `start` (x, y) towards `end` (x, y), each <= 2.5 cm tall and >= 12 cm deep."""
        p0, p1 = np.array(start, float), np.array(end, float)
        L = float(np.linalg.norm(p1 - p0))
        n = int(n)
        if n < 1 or total_rise / n > STEP_MAX + 1e-6:
            raise WorldError(f"steps {name!r}: each step must be <= {STEP_MAX} m tall (use more steps)")
        if L / n < 0.12:
            raise WorldError(f"steps {name!r}: each tread must be >= 0.12 m deep (the robot's foot is ~9 cm long)")
        yaw = math.degrees(math.atan2(*(p1 - p0)[::-1]))
        b = self.fixture(name, (*p0, 0.0), yaw_deg=yaw)
        b.role = "steps"
        d = L / n
        for i in range(n):
            h = total_rise * (i + 1) / n
            b.box(f"step{i}", (d, width, h), (d * (i + 0.5), 0, h / 2), material=material)
        return b

    def bumps(self, name, center, size, max_height=0.012, count=30, material=None, seed=0):
        """A field of small random blocks (rubble, cobbles, cables, roots) the robot must step over (<= 1.5 cm)."""
        if not 0.003 <= max_height <= BUMP_MAX:
            raise WorldError(f"bumps {name!r}: max_height 0.003..{BUMP_MAX} m")
        rng = np.random.default_rng(int(seed))
        b = self.fixture(name, (center[0], center[1], 0.0))
        b.role = "bumps"
        sx, sy = float(size[0]), float(size[1])
        for i in range(int(min(120, max(4, count)))):
            w, l, h = rng.uniform(0.03, 0.09), rng.uniform(0.03, 0.12), rng.uniform(0.3, 1.0) * max_height
            b.box(f"b{i}", (w, l, h), (rng.uniform(-sx / 2, sx / 2), rng.uniform(-sy / 2, sy / 2), h / 2), material=material,
                  rot_deg=(0, 0, float(rng.uniform(0, 180))))
        return b

    # -- mechanisms & objects -----------------------------------------------------------------
    def gate(self, name, center, width=0.36, yaw_deg=0.0, height=0.24, material=None, frame_material=None):
        """A portcullis-style gate in a doorway at `center`, its panel spanning `width` along the local y axis
        (yaw_deg turns it). It starts closed and rises when the robot steps on a plate() that opens it.
        Build the wall around it with wall(..., openings=[...]) so the doorway is the only way through."""
        if not 0.30 <= width <= 0.8:
            raise WorldError(f"gate {name!r}: width 0.30..0.8 m")
        if not 0.15 <= height <= 0.5:
            raise WorldError(f"gate {name!r}: height 0.15..0.5 m")
        n = _snake(name)
        fr = self.fixture(f"{n}_frame", (center[0], center[1], 0.0), yaw_deg)
        fr.role = "gate_frame"
        top = height + DUCK_HEIGHT + 0.06
        for s in (-1, 1):
            fr.box(f"post{'l' if s < 0 else 'r'}", (0.05, 0.04, top), (0, s * (width / 2 + 0.02), top / 2), material=frame_material or material)
        fr.box("lintel", (0.05, width + 0.08, 0.04), (0, 0, top + 0.02), material=frame_material or material)
        travel = DUCK_HEIGHT + 0.04
        g = fr.child(n, slide(axis=(0, 0, 1), range=(0.0, travel), damping=5.0), pos=(0, 0, 0.003))
        g.role = "gate"
        g.box("panel", (0.025, width, height), (0, 0, height / 2), material=material)
        self.gates[n] = {"part": n, "frame": fr.name, "center": [float(center[0]), float(center[1])], "width": float(width),
                         "yaw": math.radians(yaw_deg), "travel": travel, "height": float(height)}
        return g

    def plate(self, name, center, size=0.18, opens=None, material=None, yaw_deg=0.0):
        """A pressure plate on the floor (6 mm tall). When either foot of the robot is on it, gate `opens` rises
        and stays open."""
        n = _snake(name)
        if opens is None or _snake(opens) not in self.gates:
            raise WorldError(f"plate {name!r}: opens= must name an existing gate (create the gate first)")
        if not 0.12 <= size <= 0.4:
            raise WorldError(f"plate {name!r}: size 0.12..0.4 m")
        b = self.fixture(n, (center[0], center[1], 0.0), yaw_deg)
        b.role = "plate"
        b.box("pad", (size, size, 0.006), (0, 0, 0.003), material=material)
        self.plates.append({"name": n, "center": [float(center[0]), float(center[1])], "size": float(size),
                            "yaw": math.radians(yaw_deg), "opens": _snake(opens)})
        return b

    def ball(self, name, pos, radius=0.04, mass=0.03, material=None, spawn_jitter=0.05):
        """A free ball the robot pushes with its feet and shins (radius 0.03-0.07 m, mass 0.01-0.12 kg)."""
        if not 0.03 <= radius <= 0.07 or not 0.01 <= mass <= 0.12:
            raise WorldError(f"ball {name!r}: radius 0.03..0.07 m, mass 0.01..0.12 kg")
        b = Body(self, name, (pos[0], pos[1], radius), 0.0, kind="object")
        b.role = "ball"
        b.mass = float(mass)
        b.spawn = {"jitter": [float(spawn_jitter)] * 2, "yaw_jitter": math.pi}
        b.sphere("ball", radius, material=material)
        self._register(b)
        return b

    def crate(self, name, pos, size=(0.10, 0.10, 0.08), mass=0.05, material=None, yaw_deg=0.0, spawn_jitter=0.04):
        """A light free box the robot shoves along the floor (sides 0.06-0.16 m, mass 0.02-0.15 kg). Decorate it with
        more geometry (visual: collision=False)."""
        sx, sy, sz = _v3(size, "crate size")
        if not (0.06 <= sx <= 0.16 and 0.06 <= sy <= 0.16 and 0.04 <= sz <= 0.14) or not 0.02 <= mass <= 0.15:
            raise WorldError(f"crate {name!r}: sides 0.06..0.16 m, height 0.04..0.14 m, mass 0.02..0.15 kg")
        b = Body(self, name, (pos[0], pos[1], sz / 2), yaw_deg, kind="object")
        b.role = "crate"
        b.mass = float(mass)
        b.spawn = {"jitter": [float(spawn_jitter)] * 2, "yaw_jitter": math.radians(20)}
        b.box("box", (sx, sy, sz), material=material)
        self._register(b)
        return b

    def zone(self, name, center, radius=0.15, kind="goal", color=(0.2, 0.9, 0.3), label=None):
        """A flat marked disc on the floor. kind='goal' (a place to reach / deliver to) or 'hazard' (lava, acid, a
        hole, a laser grid ...: the robot must never step into it)."""
        if kind not in ("hazard", "goal"):
            raise WorldError("zone kind must be 'hazard' or 'goal'")
        if not 0.08 <= radius <= 0.6:
            raise WorldError(f"zone {name!r}: radius 0.08..0.6 m")
        self.zones.append({"name": _snake(name), "center": [float(center[0]), float(center[1])], "radius": float(radius),
                           "kind": kind, "color": _rgb(color), "label": label or _snake(name).replace("_", " ")})
        return self

    # -- tasks -----------------------------------------------------------------------------
    def _zone(self, ref, kind, task):
        z = {x["name"]: x for x in self.zones}.get(_snake(ref))
        if z is None or z["kind"] != kind:
            raise WorldError(f"task {task!r}: {ref!r} is not a {kind} zone")
        return z["name"]

    def _task(self, name, kind, start, instruction, paraphrases, avoid, **kw):
        if not instruction:
            raise WorldError(f"task {name!r} needs an instruction")
        x, y, yaw = (list(start) + [0.0])[:3]
        hz = [self._zone(a, "hazard", name) for a in avoid]
        self.tasks.append({"name": _snake(name), "kind": kind, "start": [float(x), float(y), math.radians(float(yaw))],
                           "start_jitter": [0.08, 0.08, math.radians(25)], "avoid": hz, "instruction": str(instruction),
                           "paraphrases": [str(p) for p in paraphrases], **kw})
        return self

    def task_goto(self, name, goal, start, avoid=(), instruction="", paraphrases=()):
        """Walk from `start` (x, y, yaw_deg) into goal zone `goal`, never entering the `avoid` hazard zones."""
        return self._task(name, "goto", start, instruction, paraphrases, avoid, goal=self._zone(goal, "goal", name))

    def task_gate(self, name, plate, goal, start, avoid=(), instruction="", paraphrases=()):
        """Multi-step: step on `plate`, which opens its gate, then walk through the gate into goal zone `goal`."""
        p = {x["name"]: x for x in self.plates}.get(_snake(plate))
        if p is None:
            raise WorldError(f"task {name!r}: unknown plate {plate!r}")
        return self._task(name, "gate", start, instruction, paraphrases, avoid, plate=p["name"], gate=p["opens"],
                          goal=self._zone(goal, "goal", name))

    def task_push(self, name, object, goal, start, avoid=(), instruction="", paraphrases=()):
        """Multi-step: walk around behind ball/crate `object` and push it into goal zone `goal`."""
        ob = self.bodies.get(_snake(object))
        if ob is None or ob.kind != "object":
            raise WorldError(f"task {name!r}: {object!r} is not a ball() or crate()")
        return self._task(name, "push", start, instruction, paraphrases, avoid, object=ob.name, goal=self._zone(goal, "goal", name))

    def task_visit(self, name, goals, start, avoid=(), instruction="", paraphrases=()):
        """Multi-step: visit the goal zones `goals` in this order (2-4 of them)."""
        if not 2 <= len(goals) <= 4:
            raise WorldError(f"task {name!r}: visit 2..4 goal zones")
        return self._task(name, "visit", start, instruction, paraphrases, avoid, goals=[self._zone(g, "goal", name) for g in goals])

    # -- checks & export --------------------------------------------------------------------
    def _check(self):
        if self.room_cfg is None:
            raise WorldError("call w.room(...) to create the room first")
        sx, sy = self.room_cfg["size"]
        n_mesh = sum(g["kind"] == "mesh" for b in self.bodies.values() for g in b.geoms if b.role not in ("ramp",))
        if n_mesh < 3:
            raise WorldError(f"only {n_mesh} modelled mesh(es): model at least 3 theme props as real Blender meshes "
                             "(rw.mesh_lathe / mesh_boolean / bevelled mesh_box / raw bpy) attached with body.mesh(...)")
        if not 4 <= len(self.tasks) <= 7:
            raise WorldError(f"declare 4..7 tasks (got {len(self.tasks)})")
        kinds = {t["kind"] for t in self.tasks}
        if len(kinds) < 3:
            raise WorldError(f"use at least 3 different task kinds (goto / gate / push / visit); got {sorted(kinds)}")
        if sum(t["kind"] in MULTI_STEP for t in self.tasks) < 2:
            raise WorldError("at least 2 tasks must be multi-step (task_gate, task_push or task_visit)")
        names = [t["name"] for t in self.tasks]
        if len(set(names)) != len(names):
            raise WorldError("task names must be unique")
        for b in self.bodies.values():
            if not b.geoms:
                raise WorldError(f"body {b.name!r} has no geometry")
            M = np.array(b.world_matrix())
            for g in b.geoms:
                p = (M @ np.array([*g["pos"], 1.0]))[:3]
                if b.kind != "decor" and (abs(p[0]) > sx / 2 + 0.1 or abs(p[1]) > sy / 2 + 0.1):
                    raise WorldError(f"{b.name}.{g['name']} is at {np.round(p, 2).tolist()}, outside the {sx}x{sy} m room")
                if p[2] > 2.5 or p[2] < -0.05:
                    raise WorldError(f"{b.name}.{g['name']} is at height {p[2]:.2f} m (keep 0..2.5 m)")
        for z in self.zones:
            c = z["center"]
            if abs(c[0]) + z["radius"] > sx / 2 or abs(c[1]) + z["radius"] > sy / 2:
                raise WorldError(f"zone {z['name']!r} sticks out of the room")
        for t in self.tasks:
            x, y = t["start"][:2]
            if abs(x) > sx / 2 - DUCK_RADIUS or abs(y) > sy / 2 - DUCK_RADIUS:
                raise WorldError(f"task {t['name']!r}: start {t['start'][:2]} is outside the room or touching a wall")
        used = {t.get("plate") for t in self.tasks}
        for p in self.plates:
            if p["name"] not in used:
                pass  # a plate without a task is allowed (decorative puzzle element)

    def save(self, out_dir, texture_size=512):
        """Validate, bake materials, export meshes and write scene.json into out_dir."""
        out = Path(out_dir)
        self._check()
        if out.exists():
            for sub in ("meshes", "textures"):
                shutil.rmtree(out / sub, ignore_errors=True)
        (out / "meshes").mkdir(parents=True, exist_ok=True)
        (out / "textures").mkdir(parents=True, exist_ok=True)
        used = {g["material"] for b in self.bodies.values() for g in b.geoms}
        used |= {self.env["floor"]} if self.env["floor"] else set()
        scene = bpy.context.scene
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 8
        scene.cycles.use_denoising = False
        scene.view_settings.view_transform = "Raw"
        scene.view_settings.look = "None"
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = d.type != "CPU"
            scene.cycles.device = "GPU"
        except Exception:
            scene.cycles.device = "CPU"
        surfaces = {self.env["floor"]} | {g["material"] for b in self.bodies.values() if b.role in ("patch", "wall", "ramp", "platform")
                                           for g in b.geoms}
        mats = {}
        for name in sorted(used):
            m = self.materials[name]
            png = m.bake(out / "textures" / f"{name}.png", size=(1024 if name in surfaces else texture_size))
            mats[name] = {**m.to_json(f"textures/{name}.png" if png else None), "surface": name in surfaces}
        bodies = [self.bodies[n].to_json(out) for n in self.order]
        for bj in bodies:
            b = self.bodies[bj["name"]]
            if hasattr(b, "ramp_info"):
                bj["ramp"] = b.ramp_info
        doc = {"name": self.name, "description": self.description, "theme": self.theme, "env": self.env,
               "room": self.room_cfg, "materials": mats, "bodies": bodies, "zones": self.zones, "plates": self.plates,
               "gates": self.gates, "tasks": self.tasks, "format": "robo_worlds.duck/1"}
        (out / "scene.json").write_text(json.dumps(doc, indent=2))
        return out


# ----------------------------------------------------------------------------- module-level convenience
_WORLD = None


def world(name, description="", theme=""):
    """Create the (single) World of this script."""
    global _WORLD
    _WORLD = World(name, description, theme)
    return _WORLD


def current_world():
    return _WORLD
