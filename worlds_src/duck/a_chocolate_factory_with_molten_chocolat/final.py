# A chocolate factory at Microduck scale: a wide caramel spill across the tiles, two steaming
# molten-chocolate channels, a ramp up to the packing deck, and a red candy portcullis
# guarding the blue cooling room.
w = rw.world("a_chocolate_factory_with_molten_chocolat",
             "A working chocolate factory at duck scale: a sticky caramel spill across the tiles, two molten-chocolate "
             "channels steaming by the packing deck, and a red candy portcullis guarding the cooling room.",
             theme="chocolate factory")
w.sky(top=(0.42, 0.32, 0.45), bottom=(0.98, 0.78, 0.58))
w.light(color=(1.0, 0.92, 0.78), azimuth_deg=125, elevation_deg=60, ambient=0.42)

# --- materials ---
floor_tiles = w.material("floor_tiles", color=(0.90, 0.85, 0.72), color2=(0.58, 0.40, 0.28), pattern="tiles", scale=5, roughness=0.5, friction=0.7)
wall_mat = w.material("candy_wall", color=(0.94, 0.90, 0.82), color2=(0.72, 0.30, 0.26), pattern="stripes", scale=6, roughness=0.8)
caramel = w.material("caramel_slick", color=(0.96, 0.68, 0.22), color2=(0.84, 0.50, 0.12), pattern="marble", scale=3, roughness=0.08, friction=0.12)
molten = w.material("molten_chocolate", color=(0.30, 0.12, 0.05), color2=(0.58, 0.30, 0.10), pattern="marble", scale=4, roughness=0.06, emission=0.15, friction=0.5)
choc = w.material("dark_chocolate", color=(0.36, 0.19, 0.10), roughness=0.35)
choc_light = w.material("milk_chocolate", color=(0.48, 0.28, 0.15), roughness=0.4)
cocoa = w.material("cocoa_mat", color=(0.40, 0.26, 0.15), color2=(0.28, 0.17, 0.09), pattern="dots", scale=10, roughness=0.9, friction=1.5)
copper = w.material("copper", color=(0.85, 0.55, 0.30), color2=(0.60, 0.35, 0.18), pattern="brushed", scale=12, roughness=0.3, metallic=1.0)
steel = w.material("steel", color=(0.75, 0.78, 0.82), color2=(0.50, 0.53, 0.58), pattern="brushed", scale=16, roughness=0.25, metallic=1.0)
red = w.material("candy_red", color=(0.88, 0.12, 0.15), roughness=0.3)
pink = w.material("fondant_pink", color=(0.95, 0.45, 0.60), roughness=0.5)
mint = w.material("mint_green", color=(0.45, 0.85, 0.60), roughness=0.6)
cream = w.material("cream", color=(0.96, 0.93, 0.85), roughness=0.6)
yellow = w.material("lemon_yellow", color=(0.98, 0.80, 0.12), roughness=0.4)
wood = w.material("oak", color=(0.78, 0.55, 0.30), color2=(0.55, 0.35, 0.18), pattern="wood", scale=6, roughness=0.7, friction=0.7)
candystripe = w.material("candy_stripe", color=(0.90, 0.10, 0.14), color2=(0.96, 0.96, 0.96), pattern="stripes", scale=10, roughness=0.35)
bulb = w.material("warm_bulb", color=(1.0, 0.85, 0.45), emission=1.0, roughness=0.2)

w.room(size=(3.2, 3.0), floor=floor_tiles, wall=wall_mat, wall_height=0.35)

# --- the cooling room (NE corner), walled off with a single gated doorway ---
w.wall("cooling_wall_a", start=(0.60, 0.20), end=(0.60, 1.50), height=0.30, material=wall_mat, openings=[(0.50, 0.42)])
w.wall("cooling_wall_b", start=(0.60, 0.20), end=(1.60, 0.20), height=0.30, material=wall_mat)
w.gate("candy_gate", center=(0.60, 0.70), width=0.42, yaw_deg=0, height=0.24, material=red, frame_material=copper)
w.plate("caramel_plate", center=(-0.05, 1.15), size=0.20, opens="candy_gate", material=yellow)

# --- floors: the great caramel spill, molten pools, a grippy cocoa mat ---
w.patch("caramel_spill", center=(0.0, -0.50), size=(3.16, 0.70), material=caramel)
w.patch("channel_pool", center=(-0.40, 0.70), size=(0.55, 0.30), yaw_deg=20, material=molten)
w.patch("gutter_pool", center=(0.30, 0.40), size=(0.45, 0.26), yaw_deg=-25, material=molten)
w.patch("cocoa_mat", center=(-1.25, 0.05), size=(0.50, 0.30), material=cocoa)

# --- the packing deck: wooden ramp up to a mint platform ---
w.ramp("deck_ramp", start=(-1.25, 0.28), end=(-1.25, 0.70), width=0.45, rise=0.05, material=wood)
w.platform("packing_platform", center=(-1.25, 1.05), size=(0.60, 0.70), height=0.05, material=mint)

# --- spilled cocoa nibs (low rubble) near the enrobing line ---
w.bumps("cocoa_nibs", center=(1.00, -0.05), size=(0.45, 0.25), max_height=0.012, count=25, material=choc, seed=7)

# --- zones ---
w.zone("choc_channel", center=(-0.40, 0.70), radius=0.18, kind="hazard", color=(0.30, 0.12, 0.04), label="the molten chocolate channel")
w.zone("choc_gutter", center=(0.30, 0.40), radius=0.15, kind="hazard", color=(0.35, 0.15, 0.05), label="the molten chocolate gutter")
w.zone("packing_deck", center=(-1.25, 1.10), radius=0.18, kind="goal", color=(0.25, 0.85, 0.35), label="the green packing deck")
w.zone("cooling_room", center=(1.05, 0.60), radius=0.20, kind="goal", color=(0.35, 0.65, 0.95), label="the blue cooling room")
w.zone("wrapper_rug", center=(-1.30, -1.20), radius=0.18, kind="goal", color=(0.95, 0.40, 0.65), label="the pink rug by the wrapping machine")
w.zone("truffle_box", center=(1.20, -1.10), radius=0.20, kind="goal", color=(0.95, 0.55, 0.15), label="the orange truffle-box lid")
w.zone("enrobing_spot", center=(1.30, -0.50), radius=0.18, kind="goal", color=(0.65, 0.40, 0.90), label="the purple mark by the enrober")

# --- props ---
# copper mixing vat with a molten surface and a steel stirrer, inside the cooling room
vat = w.fixture("chocolate_vat", pos=(1.30, 1.15, 0.0))
vat_body = rw.mesh_lathe([(0.02, 0.0), (0.17, 0.0), (0.19, 0.03), (0.19, 0.26), (0.215, 0.30), (0.215, 0.34), (0.17, 0.34), (0.17, 0.30)])
vat.mesh("vat_body", vat_body, material=copper)
soup = rw.mesh_cylinder(0.165, 0.02)
rw.move(soup, pos=(0, 0, 0.29))
vat.mesh("molten_surface", soup, material=molten, collision=False)
paddle = rw.mesh_box((0.035, 0.30, 0.03), bevel=0.005)
rw.move(paddle, pos=(0, 0, 0.40), rot_deg=(0, 18, 0))
vat.mesh("stirrer", paddle, material=steel, collision=False)

# wrapping machine: steel body, red hood, copper rollers, cream label, yellow button
wrap = w.fixture("wrapping_machine", pos=(-1.42, -0.70, 0.0))
wrap.box("body", size=(0.30, 0.26, 0.18), pos=(0, 0, 0.09), material=steel)
wrap.box("hood", size=(0.22, 0.18, 0.10), pos=(0, 0, 0.23), material=red)
rf = rw.mesh_cylinder(0.026, 0.30, axis="x")
rw.move(rf, pos=(0, 0.10, 0.19))
wrap.mesh("roller_front", rf, material=copper, collision=False)
rb = rw.mesh_cylinder(0.026, 0.30, axis="x")
rw.move(rb, pos=(0, -0.10, 0.19))
wrap.mesh("roller_back", rb, material=copper, collision=False)
wrap.box("label", size=(0.02, 0.12, 0.07), pos=(0.155, 0, 0.10), material=cream, collision=False)
wrap.box("button", size=(0.04, 0.04, 0.02), pos=(0.05, 0.04, 0.285), material=yellow, collision=False)

# enrobing machine: an arch with a chocolate curtain and a molten tray
enr = w.fixture("enrobing_machine", pos=(1.43, -0.10, 0.0))
enr.box("leg_left", size=(0.05, 0.30, 0.26), pos=(-0.125, 0, 0.13), material=steel)
enr.box("leg_right", size=(0.05, 0.30, 0.26), pos=(0.125, 0, 0.13), material=steel)
enr.box("top", size=(0.32, 0.32, 0.09), pos=(0, 0, 0.295), material=pink)
for i, yy in enumerate((-0.09, 0.0, 0.09)):
    cur = rw.mesh_cylinder(0.008, 0.12, vertices=16)
    rw.move(cur, pos=(0, yy, 0.20))
    enr.mesh("curtain_%d" % i, cur, material=copper, collision=False)
enr.box("tray", size=(0.20, 0.26, 0.03), pos=(0, 0, 0.045), material=molten, collision=False)

# a giant segmented chocolate bar against the north wall
bar = w.fixture("giant_chocolate_bar", pos=(0.30, 1.42, 0.0))
bar.box("base", size=(0.44, 0.14, 0.05), pos=(0, 0, 0.025), material=choc)
for i, xx in enumerate((-0.145, 0.0, 0.145)):
    for j, yy in enumerate((-0.035, 0.035)):
        bar.box("seg_%d_%d" % (i, j), size=(0.125, 0.055, 0.022), pos=(xx, yy, 0.061), material=choc_light, collision=False)

# a wooden cocoa barrel with steel bands, in the cooling room
barrel = w.fixture("cocoa_barrel", pos=(0.85, 1.30, 0.0))
staves = rw.mesh_lathe([(0.01, 0.0), (0.11, 0.0), (0.135, 0.04), (0.15, 0.13), (0.135, 0.22), (0.11, 0.26), (0.01, 0.26)])
barrel.mesh("staves", staves, material=wood)
for nm, zz in (("band_low", 0.06), ("band_high", 0.20)):
    band = rw.mesh_torus(0.148, 0.012)
    rw.move(band, pos=(0, 0, zz))
    barrel.mesh(nm, band, material=steel, collision=False)

# candy-stripe lamp posts with copper shades and warm bulbs (visual only)
def candy_lamp(name, x, y):
    lamp = w.decor(name, pos=(x, y, 0.0))
    pole = rw.mesh_cylinder(0.020, 0.70, vertices=24)
    rw.move(pole, pos=(0, 0, 0.35))
    lamp.mesh("pole", pole, material=candystripe)
    shade = rw.mesh_lathe([(0.0, 0.0), (0.085, 0.02), (0.05, 0.075), (0.0, 0.085)])
    rw.move(shade, pos=(0, 0, 0.70))
    lamp.mesh("shade", shade, material=copper)
    lamp.sphere("bulb", 0.032, pos=(0, 0, 0.705), material=bulb)

candy_lamp("candy_lamp_cooling", 1.50, 1.40)
candy_lamp("candy_lamp_south", 1.50, -1.40)
candy_lamp("candy_lamp_north", -0.35, 1.45)

# copper pipework with red valve wheels along the east wall (visual only)
pipes = w.decor("copper_pipes", pos=(1.57, 0.0, 0.0))
p_main = rw.mesh_cylinder(0.028, 2.90, axis="y")
rw.move(p_main, pos=(0, 0, 0.24))
pipes.mesh("pipe_main", p_main, material=copper)
p_thin = rw.mesh_cylinder(0.018, 2.90, axis="y")
rw.move(p_thin, pos=(-0.05, 0, 0.31))
pipes.mesh("pipe_thin", p_thin, material=copper)
for k, yy in enumerate((-0.9, 0.1, 0.9)):
    wheel = rw.mesh_torus(0.035, 0.010)
    rw.move(wheel, pos=(-0.06, yy, 0.24), rot_deg=(0, 90, 0))
    pipes.mesh("valve_%d" % k, wheel, material=red)

# scattered gumdrops (visual only)
for nm, gx, gy, gm in (("gumdrop_pink", -0.90, -1.44, pink),
                       ("gumdrop_mint", 0.90, 0.08, mint),
                       ("gumdrop_lemon", -0.90, 1.44, yellow)):
    gd = w.decor(nm, pos=(gx, gy, 0.0))
    drop = rw.mesh_sphere(0.045)
    rw.move(drop, pos=(0, 0, 0.032), scale=(1.0, 1.0, 0.72))
    gd.mesh("drop", drop, material=gm)

# a pushable chocolate truffle
w.ball("truffle", pos=(-0.20, -1.10), radius=0.05, mass=0.05, material=choc)

# --- tasks ---
w.task_goto("climb_the_packing_deck", goal="packing_deck", start=(-1.25, -1.20, 0),
            avoid=["choc_channel", "choc_gutter"],
            instruction="Waddle north across the shiny caramel spill, over the dark cocoa mat, and up the wooden ramp onto the green packing deck.",
            paraphrases=["Cross the sticky caramel and climb the ramp to the green deck.",
                         "Get up onto the packing deck past the caramel spill.",
                         "Head north over the slippery caramel and up the ramp to the green platform."])

w.task_goto("cross_the_caramel", goal="wrapper_rug", start=(0.15, 1.00, 180),
            avoid=["choc_channel", "choc_gutter"],
            instruction="Walk south across the wide caramel spill - it is very slippery - and stop on the pink rug by the wrapping machine.",
            paraphrases=["Cross the gooey caramel floor to the pink rug.",
                         "Make your way over the caramel slick to the rug by the wrapping machine.",
                         "Go south across the sticky stuff and stand on the pink rug."])

w.task_gate("open_the_cooling_room", plate="caramel_plate", goal="cooling_room", start=(0.30, -1.15, 0),
            avoid=["choc_channel", "choc_gutter"],
            instruction="Step on the yellow plate by the north wall to lift the red candy gate, then go through into the blue cooling room.",
            paraphrases=["Press the yellow floor plate to open the red gate, then walk into the cooling room.",
                         "Stand on the yellow plate, let the candy gate rise, and slip into the blue room.",
                         "The cooling room is locked - the yellow plate by the north wall opens its red gate."])

w.task_push("roll_the_truffle", object="truffle", goal="truffle_box", start=(-0.70, -1.10, 90),
            avoid=["choc_channel", "choc_gutter"],
            instruction="Push the round chocolate truffle east across the tiles onto the orange truffle-box lid by the east wall.",
            paraphrases=["Shove the brown truffle ball onto the orange lid.",
                         "Roll the truffle across the floor to the orange patch by the east wall.",
                         "Nudge the chocolate ball home onto the orange truffle box."])

w.task_visit("factory_rounds", goals=["wrapper_rug", "packing_deck"], start=(1.30, -0.90, 135),
             avoid=["choc_channel", "choc_gutter"],
             instruction="Do your rounds: first visit the pink rug by the wrapping machine, then cross the caramel and climb the ramp to the green packing deck.",
             paraphrases=["Check the wrapping machine's pink rug first, then go up to the packing deck.",
                          "Visit the pink rug, then stand on the green deck.",
                          "Rounds time: the pink rug by the wrapper, then up the ramp to the green platform."])

w.task_goto("enrober_shift", goal="enrobing_spot", start=(-0.60, 1.20, 135),
            avoid=["choc_channel", "choc_gutter"],
            instruction="Head to the purple mark by the pink enrobing machine in the south-east corner - mind the two molten chocolate channels on the way.",
            paraphrases=["Go stand on the purple mark next to the enrober.",
                         "Cross the factory to the enrobing machine in the south-east, avoiding the molten chocolate.",
                         "Time for your shift at the enrober: get to the purple mark without stepping in the chocolate channels."])
