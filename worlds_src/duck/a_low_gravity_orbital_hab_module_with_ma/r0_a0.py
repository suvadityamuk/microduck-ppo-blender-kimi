# A low-gravity orbital hab module for the Microduck: magnetic hex floor tiles, a glowing coolant
# spill (ice-slick), drifting debris clouds (hazards under floating rock meshes), an airlock behind
# a pressure gate, a hydroponics bay and a raised observation deck. Moon gravity + magnetic grip floors.
import numpy as np

w = rw.world("a_low_gravity_orbital_hab_module_with_ma",
             "A low-gravity orbital habitat module: glowing hex magnetic floor tiles, a slick of spilled "
             "coolant, slowly drifting debris clouds, an airlock behind a pressure gate and a raised "
             "observation deck under the stars.",
             theme="low-gravity orbital hab module")
w.sky(top=(0.05, 0.06, 0.14), bottom=(0.15, 0.18, 0.30))
w.light(color=(0.95, 0.97, 1.0), azimuth_deg=110, elevation_deg=60, ambient=0.5)
w.gravity(1.62)  # Moon-like low gravity; the magnetic tiles keep the duck grounded

# ---------- materials ----------
floor_tiles = w.material("mag_hex_tiles", color=(0.58, 0.64, 0.72), color2=(0.16, 0.62, 0.72),
                         pattern="hex", scale=5, roughness=0.35, metallic=0.35, friction=1.3)
wall_panels = w.material("wall_panels", color=(0.80, 0.82, 0.86), color2=(0.55, 0.60, 0.68),
                         pattern="tiles", scale=4, roughness=0.45, metallic=0.5)
coolant = w.material("coolant", color=(0.30, 0.92, 1.00), color2=(0.85, 1.0, 1.0),
                     pattern="marble", scale=3, roughness=0.05, friction=0.10, emission=0.25)
deck_grate = w.material("deck_grate", color=(0.95, 0.75, 0.15), color2=(0.75, 0.55, 0.10),
                        pattern="brushed", scale=10, roughness=0.5, metallic=0.6, friction=1.1)
hull_white = w.material("hull_white", color=(0.92, 0.93, 0.96), roughness=0.35, metallic=0.15)
rubber_dark = w.material("dark_trim", color=(0.12, 0.13, 0.17), roughness=0.8, friction=1.4)
screen_glow = w.material("screen_glow", color=(0.10, 0.85, 1.00), roughness=0.2, emission=0.9)
warn_orange = w.material("warn_orange", color=(1.0, 0.55, 0.08), roughness=0.5)
grow_pink = w.material("grow_pink", color=(1.0, 0.25, 0.55), emission=0.9, roughness=0.3)
plant_green = w.material("plant_green", color=(0.25, 0.75, 0.30), color2=(0.10, 0.50, 0.15),
                         pattern="noise", scale=6, roughness=0.7)
glass = w.material("pod_glass", color=(0.55, 0.85, 1.0), roughness=0.05, alpha=0.35)
copper = w.material("copper", color=(0.75, 0.50, 0.25), color2=(0.50, 0.30, 0.12),
                    pattern="brushed", scale=15, roughness=0.3, metallic=1.0)
debris_rust = w.material("debris_rust", color=(0.55, 0.38, 0.22), color2=(0.30, 0.18, 0.10),
                         pattern="rust", scale=5, roughness=0.9)
space_mat = w.material("space_window", color=(0.02, 0.03, 0.10), roughness=0.1, emission=0.2)
star_mat = w.material("star", color=(1.0, 1.0, 1.0), emission=1.0)
sign_glow = w.material("sign_glow", color=(1.0, 0.60, 0.10), emission=0.8)

# ---------- room and structure ----------
w.room(size=(3.4, 3.2), floor=floor_tiles, wall=wall_panels, wall_height=0.3)

# starboard wall: separates the airlock chamber (top) and hydroponics bay (bottom) from the main deck;
# one plain doorway into hydroponics, one gated doorway into the airlock
w.wall("eva_wall", start=(0.9, -1.6), end=(0.9, 1.6), height=0.3, thickness=0.04,
       material=wall_panels, openings=[(0.6, 0.5), (2.1, 0.42)])
w.wall("hydro_wall", start=(0.9, -0.4), end=(1.7, -0.4), height=0.3, thickness=0.04, material=wall_panels)

w.gate("airlock_gate", center=(0.9, 0.5), width=0.42, yaw_deg=0, height=0.24,
       material=hull_white, frame_material=warn_orange)
w.plate("airlock_plate", center=(-0.55, 1.2), size=0.2, opens="airlock_gate", material=warn_orange)

# spilled coolant: a glowing, near-frictionless slick across the main walkway
w.patch("coolant_spill", center=(-0.1, -0.6), size=(1.0, 0.6), material=coolant)

# raised observation deck in the port-aft corner, reached by a yellow ramp
w.ramp("obs_ramp", start=(-1.35, -0.4), end=(-1.35, -0.8), width=0.45, rise=0.06, material=deck_grate)
w.platform("obs_deck_platform", center=(-1.35, -1.15), size=(0.7, 0.7), height=0.06, material=deck_grate)

# snaking cable runs the duck can waddle over (12 mm max)
w.bumps("cable_clutter", center=(-0.1, -0.05), size=(0.5, 0.35), max_height=0.012, count=25,
        material=rubber_dark, seed=7)

# ---------- zones ----------
w.zone("debris_alpha", center=(-0.55, 0.5), radius=0.2, kind="hazard", color=(1.0, 0.5, 0.1),
       label="the drifting debris cloud")
w.zone("debris_beta", center=(0.45, -1.1), radius=0.18, kind="hazard", color=(1.0, 0.4, 0.1),
       label="the tumbling scrap field")
w.zone("airlock", center=(1.3, 0.6), radius=0.25, kind="goal", color=(0.2, 0.9, 0.9),
       label="the airlock chamber")
w.zone("console_spot", center=(-0.95, 1.05), radius=0.18, kind="goal", color=(0.2, 0.6, 1.0),
       label="the blue marker by the nav console")
w.zone("obs_deck", center=(-1.35, -1.15), radius=0.2, kind="goal", color=(0.95, 0.8, 0.15),
       label="the yellow observation deck")
w.zone("dock_pad", center=(0.2, 1.3), radius=0.2, kind="goal", color=(0.3, 0.9, 0.3),
       label="the green cargo docking pad")
w.zone("greenhouse", center=(1.3, -1.0), radius=0.22, kind="goal", color=(0.4, 0.95, 0.4),
       label="the hydroponics bay")

# ---------- props (modelled meshes) ----------
# navigation console in the fore-port corner, angled glowing screen and buttons
console = w.fixture("nav_console", pos=(-1.42, 1.34, 0), yaw_deg=45)
base = rw.mesh_box((0.4, 0.24, 0.30), bevel=0.02)
rw.move(base, pos=(0, 0, 0.15))
console.mesh("base", base, material=hull_white)
sframe = rw.mesh_box((0.38, 0.05, 0.22), bevel=0.01)
rw.move(sframe, pos=(0, 0.09, 0.40), rot_deg=(25, 0, 0))
console.mesh("screen_frame", sframe, material=rubber_dark)
screen = rw.mesh_box((0.34, 0.02, 0.18), bevel=0.005)
rw.move(screen, pos=(0, 0.075, 0.432), rot_deg=(25, 0, 0))
console.mesh("screen", screen, material=screen_glow, collision=False)
for i, (bx, bm) in enumerate([(-0.11, screen_glow), (0.0, warn_orange), (0.11, grow_pink)]):
    btn = rw.mesh_box((0.045, 0.035, 0.02), bevel=0.005)
    rw.move(btn, pos=(bx, -0.07, 0.31))
    console.mesh("btn%d" % i, btn, material=bm, collision=False)

# two cryo pods (lathed shells, glass windows, glowing status strips) in the airlock chamber
def cryo_pod(name, px, py):
    pod = w.fixture(name, pos=(px, py, 0), yaw_deg=0)
    shell = rw.mesh_lathe([(0.0, 0.0), (0.13, 0.0), (0.155, 0.05), (0.155, 0.5),
                           (0.13, 0.62), (0.07, 0.70), (0.0, 0.72)], segments=32)
    pod.mesh("shell", shell, material=hull_white)
    ring = rw.mesh_torus(0.155, 0.018)
    rw.move(ring, pos=(0, 0, 0.06))
    pod.mesh("base_ring", ring, material=warn_orange, collision=False)
    win = rw.mesh_box((0.13, 0.05, 0.38), bevel=0.02)
    rw.move(win, pos=(0, -0.125, 0.36))
    pod.mesh("window", win, material=glass, collision=False)
    strip = rw.mesh_box((0.17, 0.03, 0.035), bevel=0.008)
    rw.move(strip, pos=(0, -0.135, 0.60))
    pod.mesh("status", strip, material=screen_glow, collision=False)
cryo_pod("cryo_pod_1", 1.50, 1.42)
cryo_pod("cryo_pod_2", 1.15, 1.42)

# porthole on the north wall: copper rim, dark glass, tiny glowing stars
port = w.decor("porthole", pos=(-0.55, 1.57, 0))
rim = rw.mesh_torus(0.13, 0.03)
rw.move(rim, pos=(0, 0, 0.18), rot_deg=(90, 0, 0))
port.mesh("rim", rim, material=copper)
disc = rw.mesh_cylinder(0.125, 0.02, axis="z")
rw.move(disc, pos=(0, 0.005, 0.18), rot_deg=(90, 0, 0))
port.mesh("glass", disc, material=space_mat)
for i, (sx, sz) in enumerate([(-0.05, 0.22), (0.03, 0.15), (0.06, 0.24), (-0.02, 0.12), (0.0, 0.19)]):
    st = rw.mesh_sphere(0.006)
    rw.move(st, pos=(sx, -0.01, sz))
    port.mesh("star%d" % i, st, material=star_mat, collision=False)

# oxygen tanks by the airlock wall, with torus retaining bands
tanks = w.fixture("o2_tanks", pos=(0.7, 1.46, 0))
for i, (dx, tm) in enumerate([(-0.07, warn_orange), (0.07, hull_white)]):
    tanks.cylinder("tank%d" % i, 0.045, 0.30, pos=(dx, 0, 0.17), axis="z", material=tm)
    tanks.sphere("cap%d" % i, 0.045, pos=(dx, 0, 0.32), material=tm)
    band = rw.mesh_torus(0.048, 0.008)
    rw.move(band, pos=(dx, 0, 0.20))
    tanks.mesh("band%d" % i, band, material=rubber_dark, collision=False)
valve = rw.mesh_cylinder(0.012, 0.05)
rw.move(valve, pos=(-0.07, 0, 0.37))
tanks.mesh("valve", valve, material=copper, collision=False)

# hydroponics rack: shelves, glowing pink grow-lights and green plant domes
rack = w.fixture("hydro_rack", pos=(1.32, -1.48, 0))
for i, dx in enumerate((-0.23, 0.23)):
    rack.box("post%d" % i, size=(0.04, 0.2, 0.5), pos=(dx, 0, 0.25), material=rubber_dark)
for i, z in enumerate((0.08, 0.24, 0.40)):
    rack.box("shelf%d" % i, size=(0.5, 0.2, 0.02), pos=(0, 0, z), material=hull_white)
rack.box("top", size=(0.5, 0.2, 0.03), pos=(0, 0, 0.5), material=rubber_dark)
for i, z in enumerate((0.215, 0.375)):
    lb = rw.mesh_box((0.46, 0.05, 0.015), bevel=0.004)
    rw.move(lb, pos=(0, 0, z))
    rack.mesh("light%d" % i, lb, material=grow_pink, collision=False)
for i, z in enumerate((0.115, 0.275)):
    for j, dx in enumerate((-0.15, 0.0, 0.15)):
        rack.sphere("plant%d_%d" % (i, j), 0.032, pos=(dx, 0, z), material=plant_green, collision=False)

# supply crate stack amidships-port
stack = w.fixture("crate_stack", pos=(-1.5, 0.8, 0))
stack.box("c1", size=(0.28, 0.28, 0.18), pos=(0, 0, 0.09), material=warn_orange)
stack.box("c2", size=(0.24, 0.24, 0.15), pos=(0.02, 0, 0.255), material=hull_white)
stack.box("c3", size=(0.18, 0.18, 0.13), pos=(-0.01, 0, 0.395), material=rubber_dark, rot_deg=(0, 0, 18))
strap = rw.mesh_box((0.30, 0.04, 0.19), bevel=0.004)
rw.move(strap, pos=(0, 0, 0.09))
stack.mesh("strap", strap, material=rubber_dark, collision=False)

# small telescope on the observation deck corner (decor)
scope = w.decor("telescope", pos=(-1.62, -1.42, 0))
sbase = rw.mesh_lathe([(0.0, 0.06), (0.05, 0.06), (0.045, 0.07), (0.012, 0.09), (0.0, 0.10)], segments=24)
scope.mesh("base", sbase, material=rubber_dark)
pole = rw.mesh_cylinder(0.008, 0.16, axis="z")
rw.move(pole, pos=(0, 0, 0.18))
scope.mesh("pole", pole, material=copper)
tube = rw.mesh_cylinder(0.025, 0.22, axis="z")
rw.move(tube, pos=(0, 0, 0.24), rot_deg=(0, 55, 0))
scope.mesh("tube", tube, material=hull_white)
lens = rw.mesh_cylinder(0.027, 0.012, axis="z")
rw.move(lens, pos=(0.095, 0, 0.306), rot_deg=(0, 55, 0))
scope.mesh("lens", lens, material=glass, collision=False)

# floating debris: jittered ico-sphere rocks and panel shards hovering above the hazard rings
def make_rock(r, seed):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r)
    rock = bpy.context.active_object
    g = np.random.default_rng(seed)
    for v in rock.data.vertices:
        v.co.x += g.uniform(-0.35, 0.35) * r
        v.co.y += g.uniform(-0.35, 0.35) * r
        v.co.z += g.uniform(-0.35, 0.35) * r
    rock.data.update()
    return rock

debris_a = w.decor("debris_cloud_a", pos=(-0.55, 0.5, 0))
for i, (r, off) in enumerate([(0.07, (0.02, 0.0, 0.34)), (0.05, (-0.1, 0.06, 0.5)),
                              (0.045, (0.09, -0.08, 0.62)), (0.035, (-0.04, -0.05, 0.75))]):
    rk = make_rock(r, 100 + i)
    rw.move(rk, pos=off, rot_deg=(20 * i, 35 * i, 10 * i), scale=(1.0, 0.8, 1.15))
    debris_a.mesh("rock%d" % i, rk, material=debris_rust)
shard = rw.mesh_box((0.16, 0.01, 0.10), bevel=0.004)
rw.move(shard, pos=(0.06, 0.08, 0.42), rot_deg=(20, 35, 10))
debris_a.mesh("shard", shard, material=hull_white)

debris_b = w.decor("debris_cloud_b", pos=(0.45, -1.1, 0))
for i, (r, off) in enumerate([(0.06, (0.0, 0.02, 0.30)), (0.045, (0.08, -0.05, 0.44)),
                              (0.04, (-0.07, 0.05, 0.55))]):
    rk = make_rock(r, 200 + i)
    rw.move(rk, pos=off, rot_deg=(15 * i, 30 * i, 5 * i), scale=(1.1, 0.85, 1.0))
    debris_b.mesh("rock%d" % i, rk, material=debris_rust)
shard2 = rw.mesh_box((0.12, 0.008, 0.08), bevel=0.003)
rw.move(shard2, pos=(-0.05, -0.06, 0.38), rot_deg=(30, 20, 40))
debris_b.mesh("shard", shard2, material=warn_orange)

# glowing AIRLOCK sign on the main-deck side of the starboard wall
bpy.ops.object.text_add()
txt = bpy.context.active_object
txt.data.body = "AIRLOCK"
txt.data.size = 0.055
txt.data.extrude = 0.004
txt.data.align_x = "CENTER"
bpy.ops.object.convert(target="MESH")
sign = w.decor("airlock_sign", pos=(0.875, 1.05, 0))
rw.move(txt, pos=(0, 0, 0.26), rot_deg=(90, 0, -90))
sign.mesh("letters", txt, material=sign_glow)

# glowing floor guide strips leading to the airlock gate
for i, lx in enumerate((0.05, 0.55)):
    strip_d = w.decor("guide_%d" % i, pos=(lx, 0.45, 0))
    s = rw.mesh_box((0.4, 0.03, 0.008), bevel=0.002)
    rw.move(s, pos=(0, 0, 0.004))
    strip_d.mesh("s", s, material=screen_glow)

# free cargo canister to shove onto the docking pad
w.crate("cargo_canister", pos=(0.2, 0.7), size=(0.10, 0.10, 0.09), mass=0.05, material=hull_white)

# ---------- tasks ----------
w.task_goto("cross_the_coolant", goal="console_spot", start=(0.55, -0.5, 135),
            avoid=["debris_alpha", "debris_beta"],
            instruction="Cross the glowing blue coolant spill nice and slow, then stop on the blue "
                        "marker in front of the navigation console.",
            paraphrases=["Walk over the slippery glowing spill to the blue marker by the nav console.",
                         "Get across the coolant slick and stop at the console's blue marker.",
                         "Carefully waddle over the shiny blue puddle to the navigation console."])
w.task_goto("up_to_the_stars", goal="obs_deck", start=(0.3, -0.2, 185),
            avoid=["debris_alpha", "debris_beta"],
            instruction="Climb the yellow ramp onto the raised observation deck in the far corner.",
            paraphrases=["Walk up the yellow ramp and stand on the observation platform.",
                         "Go up onto the corner deck by the little telescope."])
w.task_gate("cycle_the_airlock", plate="airlock_plate", goal="airlock", start=(-1.0, 0.7, 45),
            avoid=["debris_alpha"],
            instruction="Step on the orange pressure plate under the porthole to open the airlock gate, "
                        "then walk through the doorway into the airlock chamber.",
            paraphrases=["Press the orange floor plate to open the white gate, then go into the airlock.",
                         "Stand on the orange plate by the wall and go through the gate it opens.",
                         "Open the airlock with the orange plate and walk inside."])
w.task_push("dock_the_cargo", object="cargo_canister", goal="dock_pad", start=(0.3, 0.15, 90),
            avoid=["debris_alpha", "debris_beta"],
            instruction="Shove the white cargo canister straight ahead onto the green docking pad.",
            paraphrases=["Push the white canister forward onto the green pad.",
                         "Nudge the cargo canister up to the green docking marker.",
                         "Slide the white crate onto the green pad by the wall."])
w.task_visit("morning_patrol", goals=["greenhouse", "console_spot", "obs_deck"], start=(0.4, 0.2, 310),
             avoid=["debris_alpha", "debris_beta"],
             instruction="Do your rounds: check the green hydroponics bay through the doorway, then the "
                         "blue marker at the nav console, and finish up on the yellow observation deck.",
             paraphrases=["Visit the hydroponics bay, then the nav console, then climb to the observation deck.",
                          "Patrol to the plant room first, then the console marker, then up the yellow ramp.",
                          "Check the greenhouse, then the console, then end on the deck."])
w.task_goto("thread_the_debris", goal="greenhouse", start=(-1.1, 0.2, 335),
            avoid=["debris_alpha", "debris_beta"],
            instruction="Cross the module to the hydroponics bay, keeping well clear of both drifting "
                        "debris fields.",
            paraphrases=["Get to the green plant bay without straying into the floating junk.",
                         "Walk to the hydroponics doorway, steering around the debris clouds.",
                         "Head to the plant shelves past the wall, dodging the tumbling scrap."])
