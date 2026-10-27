# `rw` — build a world for the Microduck in Blender

You write ONE Python script that runs inside Blender 5.1 (headless). `rw`, `bpy` and `math` are already imported;
`numpy as np` and `from mathutils import Vector, Matrix` are available if you import them. Do not import anything
else, do not read or write files, do not call `w.save()` (the harness does).

## The robot
The Microduck is a 25 cm tall, 0.74 kg bipedal robot duck (14 small servos, a camera in its head about 27 cm above
the floor that mostly sees the floor ahead). It walks at up to ~0.3 m/s, turns on the spot, needs a gap of at least
0.30 m to pass, can step up at most 2.5 cm at once and climb ramps of at most 12 degrees. It has no arms: it acts
with its body and feet (stepping on pressure plates, shoving balls and crates).

## The stage
- Metres, z up, the floor is z = 0. The room is centred on the origin: `w.room(size=(sx, sy))` spans
  x in [-sx/2, sx/2], y in [-sy/2, sy/2] (each side 1.6 .. 4.0 m; 2.5-3.5 m is typical).
- Everything colliding must be inside the room. Purely visual scenery (`w.decor`) may stand anywhere.
- Leave clear walking lanes >= 0.35 m wide between obstacles. The robot plans routes on its own.

## World and look
```python
w = rw.world("snake_case_name", "one evocative sentence", theme="...")
w.sky(top=(r,g,b), bottom=(r,g,b))                   # colours are floats 0..1
w.light(color=(r,g,b), azimuth_deg=0..360, elevation_deg=25..85, ambient=0.1..0.6)
w.gravity(9.81)                                      # optional, 1.5..12 m/s^2 (Moon 1.62, Mars 3.71)
m = w.material("name", color=(r,g,b), color2=(r,g,b), pattern="wood", scale=8, roughness=0.6,
               metallic=0.0, emission=0.0, alpha=1.0, stretch=1.0, friction=1.0)
#   pattern: flat noise wood tiles bricks checker marble brushed stripes dots fabric concrete rust hex
#   Materials are procedural Blender node graphs baked to textures. friction (0.05..2.0) is the sliding friction
#   of floors, patches, ramps and objects made of it: ice 0.05-0.12, wet tiles 0.3, wood 0.6, carpet 1.0, rubber 1.6.
#   The robot learns from its camera: use bright, contrasting, DISTINCT floor colours/patterns per area (it mostly
#   sees the floor) and tall colourful landmarks; dark scenes are rejected.
w.room(size=(3.0, 3.0), floor=m_floor, wall=m_wall, wall_height=0.3)   # REQUIRED, call first
```

## Terrain and structure (all static and colliding)
```python
w.wall("name", start=(x, y), end=(x, y), height=0.25, thickness=0.04, material=m, openings=[(dist_from_start, width)])
    # interior wall; openings (width >= 0.30) are doorways. Divide the room into areas with walls.
w.patch("name", center=(x, y), size=(sx, sy), material=m, yaw_deg=0)
    # a floor surface 2 mm proud: ice sheet, oil slick, rubber mat, sand ... its material's friction applies
w.ramp("name", start=(x, y), end=(x, y), width=0.4, rise=0.06, material=m)
    # solid wedge rising from the floor at start to `rise` at end; slope <= 12 deg (length >= rise / 0.21)
w.platform("name", center=(x, y), size=(sx, sy), height=0.06, material=m)    # raised deck, reach it by a ramp/steps
w.steps("name", start=(x, y), end=(x, y), width=0.4, n=3, total_rise=0.06, material=m)  # <= 2.5 cm per step, >= 12 cm treads
w.bumps("name", center=(x, y), size=(sx, sy), max_height=0.012, count=30, material=m, seed=0)  # rubble / cobbles / cables
```
Put a platform's ramp so the ramp's high end touches the platform edge at the same height. A bare platform edge
taller than 2.5 cm is a wall to the robot.

## Props
```python
f = w.fixture("crate_stack", pos=(x, y, 0), yaw_deg=0)   # static, collides (furniture, machines, pillars, boulders)
d = w.decor("hanging_lamp", pos=(x, y, 0), yaw_deg=0)     # static, visual only (no collisions)
```
Geometry on a body (positions in the body's frame; sizes are FULL extents; rot_deg = extra XYZ rotation in degrees):
```python
b.box("name", size=(sx, sy, sz), pos=(x, y, z), material=m, rot_deg=(0, 0, 0), collision=True)
b.cylinder("name", radius, length, pos=(...), axis="z", material=m, rot_deg=None, collision=True)  # axis 'x'|'y'|'z'
b.capsule("name", radius, length, pos=(...), axis="z", material=m)
b.sphere("name", radius, pos=(...), material=m)
b.mesh("name", blender_object, material=m, collision=None)
```
`b.mesh` attaches ANY Blender mesh object you model with bpy (modifiers, booleans, bevels, curves converted to mesh,
lathes ...). Its current world transform is its pose in the body frame, so build it around the origin and place it with
`rw.move(obj, pos=..., rot_deg=..., scale=...)`. On fixtures meshes collide by their convex hull; on decor they are
visual only. Mesh helpers (each returns a bpy object):
```python
rw.mesh_box(size, bevel=0.0)            rw.mesh_cylinder(radius, length, vertices=48, bevel=0.0, axis="z")
rw.mesh_sphere(radius)                   rw.mesh_torus(major_radius, minor_radius)
rw.mesh_lathe([(r, z), ...], segments=48)   # revolve a profile around z: vases, barrels, lamp posts, columns
rw.mesh_prism([(x, y), ...], height)        # extrude a polygon
rw.mesh_boolean(a, b, op="DIFFERENCE")      # also "UNION", "INTERSECT"
rw.mesh_join([o1, o2, ...])
rw.move(obj, pos=(x,y,z), rot_deg=(rx,ry,rz), scale=(sx,sy,sz))
```
Model at least 3 theme props as real Blender meshes, and make things look like what they are (rims, legs, panels,
rivets, labels as geometry). Remember the scale: the robot is 25 cm tall, a "table" is a 40 cm tall platform it
cannot climb, a mug is the size of its head.

## Mechanisms and free objects
```python
w.gate("gate", center=(x, y), width=0.36, yaw_deg=0, height=0.24, material=m, frame_material=m2)
    # portcullis in a doorway; its panel spans `width` along the gate's local y (yaw_deg turns it). Starts CLOSED,
    # rises when the robot steps on a plate that opens it. Build walls with an opening exactly where the gate is.
w.plate("plate", center=(x, y), size=0.18, opens="gate", material=m)   # pressure plate (create the gate first)
w.ball("ball", pos=(x, y), radius=0.04, mass=0.03, material=m)          # free ball (r 0.03-0.07 m, 0.01-0.12 kg)
c = w.crate("crate", pos=(x, y), size=(0.10, 0.10, 0.08), mass=0.05, material=m)   # light free box to shove
```

## Zones
```python
w.zone("lava_pool", center=(x, y), radius=0.2, kind="hazard", color=(1, 0.3, 0.05), label="the lava pool")
w.zone("dock", center=(x, y), radius=0.18, kind="goal", color=(0.2, 0.9, 0.3), label="the green landing pad")
```
Hazards (lava, acid, holes, radiation, lasers ...) must never be stepped into; goals are places to reach / deliver to.

## Tasks (4..7 per world; >= 3 different kinds; >= 2 multi-step)
`start=(x, y, yaw_deg)` is where the robot begins (on open floor, >= 0.25 m from walls and hazards).
```python
w.task_goto("name", goal="dock", start=(x, y, yaw), avoid=["lava_pool"], instruction="...", paraphrases=[...])
w.task_gate("name", plate="plate", goal="vault", start=(...), avoid=[...], instruction="...", paraphrases=[...])
    # multi-step: step on the plate (opens its gate), then walk through the gate into the goal zone.
    # The goal must be unreachable while the gate is closed (enclose it with walls; the gate is the only way in).
w.task_push("name", object="ball", goal="dock", start=(...), avoid=[...], instruction="...", paraphrases=[...])
    # multi-step: go behind the object and shove it into the goal (keep a flat lane >= 0.5 m wide between them)
w.task_visit("name", goals=["a", "b", "c"], start=(...), avoid=[...], instruction="...", paraphrases=[...])
    # multi-step: visit 2-4 goal zones in order
```
Write instructions the way a person would speak to the robot, naming things by how they LOOK from a duck's eye
height ("the yellow plate by the barrels", "the blue rug past the ice"). Give 2-3 paraphrases each.

## What makes a good world
- A coherent, specific theme at the duck's scale, with 4-8 well-modelled props that make it obvious.
- Physical challenges that are hard, slow or unsafe to practise with a real robot: ice and oil (low friction),
  low or high gravity, ramps and steps near their limits, rubble, hazards to steer around, gates that need the
  right sequence, objects to shove. Weave them into the theme, and make the tasks cross them.
- Several distinct areas (walls, platforms, different floors) so routes are interesting; tasks start in
  different places and go to different places.
- Everything inside its limits: the harness checks paths, step heights, spawn spots and lighting; any error message
  you get back is precise — fix exactly what it says.
