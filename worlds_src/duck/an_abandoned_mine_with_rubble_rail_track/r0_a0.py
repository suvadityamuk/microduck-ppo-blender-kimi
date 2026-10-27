# An abandoned mine at duck scale: a rail line with ore carts runs down the west side, a rockfall of
# rubble chokes the main chamber, a glistening seep slicks the south floor, an open shaft yawns by the
# winch, and a rusty cage gate guards the old lift in the east wall.
w = rw.world("an_abandoned_mine_with_rubble_rail_track",
             "A forgotten mine gallery: rails and ore carts on a gravel bed, rubble from a cave-in, a "
             "slick seep, a fenced-off open shaft and a caged lift behind a rusty portcullis.",
             theme="abandoned mine")
w.sky(top=(0.22, 0.26, 0.38), bottom=(0.62, 0.52, 0.40))
w.light(color=(1.0, 0.90, 0.72), azimuth_deg=150, elevation_deg=62, ambient=0.45)
w.gravity(9.81)

# --- materials ---
floor_rock = w.material("gallery_floor", color=(0.44, 0.41, 0.37), color2=(0.31, 0.29, 0.27),
                        pattern="concrete", scale=5, roughness=0.9, friction=0.9)
wall_rock  = w.material("gallery_wall", color=(0.50, 0.45, 0.39), color2=(0.34, 0.30, 0.27),
                        pattern="noise", scale=3, roughness=0.95)
planks     = w.material("old_planks", color=(0.62, 0.47, 0.30), color2=(0.44, 0.32, 0.19),
                        pattern="wood", scale=5, roughness=0.8, friction=0.7)
timber     = w.material("pit_props", color=(0.42, 0.31, 0.20), color2=(0.30, 0.21, 0.13),
                        pattern="wood", scale=4, roughness=0.85, friction=0.8)
steel      = w.material("rail_steel", color=(0.58, 0.59, 0.63), color2=(0.36, 0.37, 0.41),
                        pattern="brushed", scale=12, roughness=0.35, metallic=1.0)
rust       = w.material("deep_rust", color=(0.60, 0.32, 0.14), color2=(0.34, 0.17, 0.08),
                        pattern="rust", scale=4, roughness=0.8, metallic=0.3)
brass      = w.material("tarnished_brass", color=(0.85, 0.65, 0.25), color2=(0.55, 0.40, 0.15),
                        pattern="brushed", scale=16, roughness=0.35, metallic=1.0)
wet        = w.material("seep_water", color=(0.55, 0.76, 0.80), color2=(0.78, 0.92, 0.94),
                        pattern="marble", scale=3, roughness=0.05, friction=0.12)
hole       = w.material("pit_dark", color=(0.04, 0.04, 0.05), roughness=1.0)
rubble_mat = w.material("rubble_stone", color=(0.52, 0.49, 0.45), color2=(0.35, 0.33, 0.30),
                        pattern="noise", scale=14, roughness=0.95, friction=1.0)
gravel     = w.material("track_gravel", color=(0.47, 0.44, 0.40), color2=(0.33, 0.31, 0.28),
                        pattern="dots", scale=22, roughness=0.95, friction=1.0)
ore        = w.material("ore_chunk", color=(0.22, 0.20, 0.26), color2=(0.45, 0.38, 0.30),
                        pattern="noise", scale=8, roughness=0.4, metallic=0.6)
glow       = w.material("lantern_glow", color=(1.0, 0.74, 0.32), roughness=0.4, emission=0.9)

w.room(size=(3.4, 3.0), floor=floor_rock, wall=wall_rock, wall_height=0.35)

# --- the caged lift: a walled-off chamber in the east, only way in is the gate ---
w.wall("lift_wall_w", start=(1.0, -0.6), end=(1.0, 0.6), height=0.3, material=wall_rock,
       openings=[(0.6, 0.42)])
w.wall("lift_wall_s", start=(1.0, -0.6), end=(1.7, -0.6), height=0.3, material=wall_rock)
w.wall("lift_wall_n", start=(1.0, 0.6), end=(1.7, 0.6), height=0.3, material=wall_rock)
w.gate("lift_gate", center=(1.0, 0.0), width=0.42, yaw_deg=0, height=0.26,
       material=rust, frame_material=steel)
w.plate("lift_plate", center=(0.45, 0.55), size=0.18, opens="lift_gate", material=brass)

# --- loading dock: raised plank deck in the north-west, reached by a ramp ---
w.platform("dock", center=(-1.25, 0.95), size=(0.75, 0.75), height=0.06, material=planks)
w.ramp("dock_ramp", start=(-1.25, 0.13), end=(-1.25, 0.57), width=0.5, rise=0.06, material=planks)

# --- ground features: gravel bed, rubble from the cave-in, slick seep, dark shaft mouth ---
w.patch("track_bed", center=(-0.35, 0.0), size=(0.5, 2.9), material=gravel)
w.bumps("rubble_main", center=(0.0, -0.25), size=(0.7, 0.5), max_height=0.012, count=45,
        material=rubble_mat, seed=7)
w.bumps("rubble_dock", center=(-0.6, 0.6), size=(0.5, 0.4), max_height=0.012, count=25,
        material=rubble_mat, seed=3)
w.patch("seep", center=(0.55, -1.2), size=(0.6, 0.4), material=wet)
w.patch("shaft_mouth", center=(0.7, -0.7), size=(0.4, 0.4), material=hole)

# --- rail track: joined meshes of sleepers and steel rails (visual only) ---
track = w.decor("rail_track", pos=(-0.35, 0.0, 0.0))
sleepers = []
for i in range(19):
    s = rw.mesh_box((0.24, 0.07, 0.015), bevel=0.003)
    rw.move(s, pos=(0, -1.44 + i * 0.16, 0.008))
    sleepers.append(s)
track.mesh("sleepers", rw.mesh_join(sleepers), material=timber)
rails = []
for dx in (-0.06, 0.06):
    r = rw.mesh_box((0.03, 2.95, 0.03), bevel=0.004)
    rw.move(r, pos=(dx, 0, 0.03))
    rails.append(r)
track.mesh("rails", rw.mesh_join(rails), material=steel)

# --- ore carts: tub, steel rim, four wheels and a load of ore ---
def make_cart(name, x, y):
    c = w.fixture(name, pos=(x, y, 0), yaw_deg=90)
    tub = rw.mesh_box((0.30, 0.22, 0.13), bevel=0.015)
    rw.move(tub, pos=(0, 0, 0.115))
    c.mesh("tub", tub, material=rust)
    rim = rw.mesh_box((0.32, 0.24, 0.025), bevel=0.008)
    rw.move(rim, pos=(0, 0, 0.185))
    c.mesh("rim", rim, material=steel, collision=False)
    for i, (sx, sy) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        c.cylinder("wheel%d" % i, 0.04, 0.025, pos=(0.135 * sx, 0.075 * sy, 0.04),
                   axis="x", material=steel, collision=False)
    c.sphere("ore1", 0.045, pos=(-0.06, -0.03, 0.20), material=ore, collision=False)
    c.sphere("ore2", 0.040, pos=(0.05, 0.04, 0.20), material=ore, collision=False)
    c.sphere("ore3", 0.035, pos=(0.00, -0.06, 0.21), material=ore, collision=False)

make_cart("ore_cart_north", -0.35, 1.05)
make_cart("ore_cart_mid", -0.35, 0.35)

# --- timber support frame by the north wall ---
frame = w.decor("timber_frame", pos=(0.35, 1.38, 0))
for sx in (-1, 1):
    frame.box("post", size=(0.06, 0.06, 0.5), pos=(0.22 * sx, 0, 0.25), material=timber)
frame.box("lintel", size=(0.56, 0.07, 0.07), pos=(0, 0, 0.5), material=timber)
frame.box("brace", size=(0.5, 0.05, 0.05), pos=(0, 0, 0.4), material=timber, rot_deg=(0, 22, 0))

# --- powder barrels in the south-east corner ---
def make_barrel(name, x, y):
    b = w.fixture(name, pos=(x, y, 0))
    body = rw.mesh_lathe([(0.07, 0.0), (0.085, 0.06), (0.09, 0.12), (0.085, 0.18), (0.07, 0.24)])
    b.mesh("body", body, material=planks)
    for z in (0.05, 0.19):
        band = rw.mesh_torus(0.088, 0.008)
        rw.move(band, pos=(0, 0, z))
        b.mesh("band", band, material=steel, collision=False)

make_barrel("barrel_a", 1.45, -1.2)
make_barrel("barrel_b", 1.3, -1.35)

# --- lantern post lighting the lift gate ---
lp = w.decor("lantern_post", pos=(0.72, 0.28, 0))
post = rw.mesh_lathe([(0.035, 0.0), (0.02, 0.02), (0.012, 0.05), (0.012, 0.42), (0.02, 0.45)])
lp.mesh("post", post, material=steel)
arm = rw.mesh_box((0.16, 0.02, 0.02), bevel=0.004)
rw.move(arm, pos=(-0.07, 0, 0.44))
lp.mesh("arm", arm, material=steel)
cage = rw.mesh_box((0.07, 0.07, 0.09), bevel=0.006)
rw.move(cage, pos=(-0.14, 0, 0.38))
lp.mesh("cage", cage, material=rust)
lp.sphere("bulb", 0.025, pos=(-0.14, 0, 0.38), material=glow)

# --- winch by the open shaft ---
wn = w.decor("winch", pos=(0.12, -0.6, 0))
wn.box("frame_l", size=(0.04, 0.04, 0.16), pos=(-0.09, 0, 0.08), material=timber)
wn.box("frame_r", size=(0.04, 0.04, 0.16), pos=(0.09, 0, 0.08), material=timber)
drum = rw.mesh_cylinder(0.05, 0.16, bevel=0.005, axis="x")
rw.move(drum, pos=(0, 0, 0.14))
wn.mesh("drum", drum, material=rust)

# --- boulders edging the shaft ---
b1 = w.fixture("boulder_a", pos=(0.62, -0.42, 0))
s1 = rw.mesh_sphere(0.08)
rw.move(s1, pos=(0, 0, 0.05), scale=(1.0, 0.85, 0.75))
b1.mesh("rock", s1, material=rubble_mat)
b2 = w.fixture("boulder_b", pos=(0.98, -0.92, 0))
s2 = rw.mesh_sphere(0.07)
rw.move(s2, pos=(0, 0, 0.04), scale=(0.9, 1.0, 0.7))
b2.mesh("rock", s2, material=rubble_mat)

# --- tool corner: crate and a leaning pickaxe ---
tc = w.fixture("tool_crate", pos=(1.35, 1.3, 0), yaw_deg=15)
bx = rw.mesh_box((0.22, 0.18, 0.14), bevel=0.01)
rw.move(bx, pos=(0, 0, 0.07))
tc.mesh("box", bx, material=planks)
strap = rw.mesh_box((0.23, 0.03, 0.15), bevel=0.004)
rw.move(strap, pos=(0, 0, 0.07))
tc.mesh("strap", strap, material=steel, collision=False)
pk = w.decor("pickaxe", pos=(1.08, 1.38, 0), yaw_deg=25)
handle = rw.mesh_cylinder(0.012, 0.32, axis="z")
rw.move(handle, pos=(0, 0, 0.16), rot_deg=(0, 18, 0))
pk.mesh("handle", handle, material=timber)
head = rw.mesh_box((0.16, 0.02, 0.025), bevel=0.006)
rw.move(head, pos=(0.05, 0, 0.30), rot_deg=(0, 18, 0))
pk.mesh("head", head, material=steel)

# --- a loose chunk of ore to shove ---
w.ball("ore_chunk", pos=(-0.35, -0.6), radius=0.05, mass=0.05, material=ore)

# --- zones ---
w.zone("open_shaft", center=(0.7, -0.7), radius=0.2, kind="hazard", color=(0.95, 0.3, 0.1),
       label="the open shaft")
w.zone("lift_cage", center=(1.35, 0.0), radius=0.2, kind="goal", color=(0.95, 0.8, 0.2),
       label="the lift cage")
w.zone("dock", center=(-1.25, 1.0), radius=0.2, kind="goal", color=(0.3, 0.85, 0.35),
       label="the green mark on the loading dock")
w.zone("cart_bay", center=(-0.35, -1.25), radius=0.18, kind="goal", color=(0.9, 0.5, 0.15),
       label="the orange cart bay at the end of the rails")
w.zone("tool_corner", center=(0.9, 1.15), radius=0.18, kind="goal", color=(0.35, 0.55, 0.95),
       label="the blue mark in the tool corner")
w.zone("winch_spot", center=(0.1, -0.85), radius=0.15, kind="goal", color=(0.8, 0.3, 0.8),
       label="the purple mark by the winch")

# --- tasks ---
w.task_goto("dock_shift", goal="dock", start=(0.0, -1.2, 90), avoid=["open_shaft"],
            instruction="Pick your way north through the grey rubble from the cave-in, climb the plank "
                        "ramp and stop on the green mark on the loading dock.",
            paraphrases=["Cross the rockfall and go up the wooden ramp to the dock.",
                         "Get up onto the loading dock, minding the loose rubble."])
w.task_gate("ride_the_lift", plate="lift_plate", goal="lift_cage", start=(-0.9, -0.2, 0),
            avoid=["open_shaft"],
            instruction="Step on the brass plate by the lantern post to wind up the rusty cage gate, "
                        "then walk through and stand inside the lift cage.",
            paraphrases=["Press the brass floor plate to open the cage gate, then go into the lift.",
                         "Open the lift with the brass plate near the lantern and step into the cage."])
w.task_push("ore_to_bay", object="ore_chunk", goal="cart_bay", start=(-0.9, -0.6, 0),
            avoid=["open_shaft"],
            instruction="Shove the dark lump of ore south along the rail line, past the sleepers, into "
                        "the orange cart bay at the end of the tracks.",
            paraphrases=["Push the ore chunk down the rails to the orange mark.",
                         "Roll the dark rock along the track bed into the cart bay."])
w.task_visit("inspection_round", goals=["tool_corner", "dock", "cart_bay"], start=(1.0, -1.2, 90),
             avoid=["open_shaft"],
             instruction="Do the foreman's inspection round: the blue mark in the tool corner first, "
                         "then the green mark up on the loading dock, and finish at the orange cart bay.",
             paraphrases=["Check the tool corner, then the dock, then the cart bay at the end of the rails.",
                          "Visit the blue mark, climb to the dock, and end down at the cart bay."])
w.task_goto("seep_crossing", goal="tool_corner", start=(-0.6, -1.2, 60), avoid=["open_shaft"],
            instruction="Cross the glistening wet seep in the south floor — it is slick as ice — and "
                        "stop on the blue mark in the tool corner.",
            paraphrases=["Get over the slippery wet patch to the tool corner.",
                         "Mind the slick seep on your way to the blue mark by the crate."])
w.task_goto("shaft_watch", goal="winch_spot", start=(-1.3, -0.5, 0), avoid=["open_shaft"],
            instruction="Go to the purple mark by the winch, but give the open shaft a wide berth — "
                        "never step into the dark pit.",
            paraphrases=["Stand by the winch near the shaft, keeping well clear of the hole.",
                         "Reach the purple winch mark without going anywhere near the pit edge."])
