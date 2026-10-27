w = rw.world("a_circus_ring_with_a_sawdust_floor_a_tig",
             "A big-top circus at duck scale: a sawdust floor around a red centre ring, a narrow plank up to the "
             "striped tightrope stage, giant balls, a flaming hoop and a lion's cage behind a steel portcullis.",
             theme="circus big top")
w.sky(top=(0.28, 0.16, 0.42), bottom=(0.85, 0.55, 0.40))
w.light(color=(1.0, 0.93, 0.80), azimuth_deg=120, elevation_deg=60, ambient=0.45)

sawdust = w.material("sawdust", color=(0.80, 0.64, 0.42), color2=(0.64, 0.48, 0.30), pattern="noise", scale=5, roughness=0.95, friction=0.9)
tent = w.material("tent_stripes", color=(0.86, 0.14, 0.16), color2=(0.94, 0.88, 0.74), pattern="stripes", scale=4, roughness=0.7)
ring_red = w.material("ring_red", color=(0.78, 0.10, 0.12), color2=(0.88, 0.22, 0.18), pattern="noise", scale=8, roughness=0.6, friction=0.8)
grease = w.material("greasepaint", color=(0.42, 0.30, 0.62), color2=(0.70, 0.58, 0.92), pattern="marble", scale=3, roughness=0.05, friction=0.1)
plank = w.material("worn_plank", color=(0.72, 0.52, 0.30), color2=(0.55, 0.38, 0.20), pattern="wood", scale=6, roughness=0.8, friction=0.7)
gold = w.material("show_gold", color=(0.90, 0.70, 0.25), color2=(0.65, 0.48, 0.16), pattern="brushed", scale=20, roughness=0.3, metallic=1.0)
red = w.material("circus_red", color=(0.85, 0.10, 0.12), roughness=0.4)
blue = w.material("circus_blue", color=(0.12, 0.35, 0.85), roughness=0.4)
yellow = w.material("star_yellow", color=(0.98, 0.80, 0.10), roughness=0.4)
white = w.material("chalk_white", color=(0.93, 0.92, 0.88), roughness=0.7)
iron = w.material("cage_iron", color=(0.42, 0.44, 0.48), color2=(0.30, 0.32, 0.36), pattern="brushed", scale=15, roughness=0.35, metallic=0.9)
flame = w.material("flame", color=(1.0, 0.35, 0.05), color2=(1.0, 0.72, 0.10), pattern="noise", scale=4, roughness=0.4, emission=0.9)

w.room(size=(3.4, 3.2), floor=sawdust, wall=tent, wall_height=0.35)

# --- the lion's cage (south-east corner): iron walls, steel portcullis, star plate opener ---
w.wall("cage_side", start=(1.05, -1.6), end=(1.05, -0.75), height=0.28, thickness=0.04, material=iron)
w.wall("cage_front", start=(1.05, -0.75), end=(1.7, -0.75), height=0.28, thickness=0.04, material=iron,
       openings=[(0.30, 0.36)])
w.gate("cage_gate", center=(1.35, -0.75), width=0.36, yaw_deg=90, height=0.24, material=iron, frame_material=red)
w.plate("star_plate", center=(-0.85, 1.0), size=0.2, opens="cage_gate", material=yellow)

# --- floors: red centre ring and the clown's spilled greasepaint (very slippery) ---
w.patch("centre_ring_floor", center=(0, 0), size=(1.3, 1.3), material=ring_red)
w.patch("grease_patch", center=(-1.03, -0.35), size=(0.7, 0.65), material=grease)

# --- tightrope stage: narrow plank ramp up to a striped platform ---
w.ramp("tightrope_plank", start=(0.95, 0.55), end=(0.95, 0.95), width=0.36, rise=0.06, material=plank)
w.platform("tightrope_stage", center=(0.95, 1.25), size=(0.9, 0.6), height=0.06, material=tent)

# --- zones ---
w.zone("fire_hoop", center=(-0.3, 0.75), radius=0.16, kind="hazard", color=(1.0, 0.4, 0.05), label="the flaming hoop")
w.zone("centre_ring", center=(0, 0), radius=0.2, kind="goal", color=(1.0, 0.85, 0.2), label="the gold circle in the centre ring")
w.zone("stage_top", center=(0.95, 1.3), radius=0.2, kind="goal", color=(0.3, 0.8, 1.0), label="the tightrope stage")
w.zone("lion_cage", center=(1.3, -1.15), radius=0.18, kind="goal", color=(0.95, 0.55, 0.15), label="the lion's cage")
w.zone("clown_corner", center=(-1.25, -1.25), radius=0.2, kind="goal", color=(0.9, 0.3, 0.8), label="the clown corner")

# --- props (real meshes) ---
# flaming hoop on a stand (decor; the hazard zone keeps the robot out)
hoop = w.decor("flaming_hoop", pos=(-0.3, 0.75, 0.0))
ring = rw.mesh_torus(0.13, 0.018)
rw.move(ring, pos=(0, 0, 0.17), rot_deg=(90, 0, 0))
hoop.mesh("hoop", ring, material=flame)
pole = rw.mesh_cylinder(0.012, 0.17)
rw.move(pole, pos=(0, 0, 0.085))
hoop.mesh("pole", pole, material=iron)
base = rw.mesh_cylinder(0.06, 0.02)
rw.move(base, pos=(0, 0, 0.01))
hoop.mesh("base", base, material=iron)

# ringmaster's podium at the edge of the ring
pod = w.fixture("ringmaster_podium", pos=(0.62, -0.05, 0.0))
body = rw.mesh_lathe([(0.0, 0.0), (0.15, 0.0), (0.15, 0.03), (0.11, 0.05), (0.10, 0.20), (0.13, 0.23), (0.13, 0.26), (0.0, 0.26)])
pod.mesh("body", body, material=red)
band = rw.mesh_cylinder(0.135, 0.03)
rw.move(band, pos=(0, 0, 0.245))
pod.mesh("gold_band", band, material=gold, collision=False)

# giant circus balls with painted stripes
gb1 = w.fixture("giant_red_ball", pos=(-1.35, 1.30, 0.0))
s1 = rw.mesh_sphere(0.20)
rw.move(s1, pos=(0, 0, 0.20))
gb1.mesh("ball", s1, material=red)
st1 = rw.mesh_torus(0.20, 0.016)
rw.move(st1, pos=(0, 0, 0.20))
gb1.mesh("stripe", st1, material=white, collision=False)

gb2 = w.fixture("giant_blue_ball", pos=(0.5, -1.30, 0.0))
s2 = rw.mesh_sphere(0.18)
rw.move(s2, pos=(0, 0, 0.18))
gb2.mesh("ball", s2, material=blue)
st2 = rw.mesh_torus(0.18, 0.016)
rw.move(st2, pos=(0, 0, 0.18), rot_deg=(90, 0, 0))
gb2.mesh("stripe", st2, material=yellow, collision=False)

# chalk circle marking the ring
circle = w.decor("chalk_circle", pos=(0, 0, 0.0))
ct = rw.mesh_torus(0.62, 0.02)
rw.move(ct, pos=(0, 0, 0.015))
circle.mesh("circle", ct, material=white)

# striped big-top poles in the corners
for i, (px, py) in enumerate([(-1.62, -1.52), (1.62, -1.52), (-1.62, 1.52), (1.62, 1.52)]):
    p = w.decor(f"tent_pole_{i}", pos=(px, py, 0.0))
    col = rw.mesh_lathe([(0.0, 0.0), (0.05, 0.0), (0.035, 0.04), (0.03, 1.05), (0.05, 1.1), (0.0, 1.12)])
    p.mesh("column", col, material=tent)
    fin = rw.mesh_sphere(0.045)
    rw.move(fin, pos=(0, 0, 1.14))
    p.mesh("finial", fin, material=gold)

# the real tightrope wire strung above the stage (decor)
wire = w.decor("tightrope_wire", pos=(0.95, 1.5, 0.0))
for sx in (-0.35, 0.35):
    wp = rw.mesh_cylinder(0.015, 0.4)
    rw.move(wp, pos=(sx, 0, 0.26))
    wire.mesh(f"pole_{sx}", wp, material=gold)
wc = rw.mesh_cylinder(0.006, 0.72, axis="x")
rw.move(wc, pos=(0, 0, 0.46))
wire.mesh("wire", wc, material=iron)

# clown's barrel with iron hoops
bar = w.fixture("clown_barrel", pos=(-1.55, -1.45, 0.0))
bm = rw.mesh_lathe([(0.0, 0.0), (0.10, 0.0), (0.115, 0.06), (0.125, 0.15), (0.115, 0.24), (0.10, 0.30), (0.0, 0.30)])
bar.mesh("staves", bm, material=plank)
for z in (0.06, 0.24):
    bh = rw.mesh_cylinder(0.118, 0.02)
    rw.move(bh, pos=(0, 0, z))
    bar.mesh(f"hoop_{z}", bh, material=iron, collision=False)

# lion's pedestal inside the cage
ped = w.fixture("lion_pedestal", pos=(1.52, -1.42, 0.0))
pc = rw.mesh_cylinder(0.09, 0.1, bevel=0.01)
rw.move(pc, pos=(0, 0, 0.05))
ped.mesh("pedestal", pc, material=red)
pt = rw.mesh_torus(0.09, 0.012)
rw.move(pt, pos=(0, 0, 0.09))
ped.mesh("trim", pt, material=gold, collision=False)

# --- free objects ---
w.ball("seal_ball", pos=(-0.2, -1.1), radius=0.05, mass=0.03, material=yellow)
w.crate("popcorn_crate", pos=(-1.0, -0.95), size=(0.09, 0.09, 0.08), mass=0.04, material=red)

# --- tasks ---
w.task_goto("into_the_spotlight", goal="centre_ring", start=(-1.2, 0.4, -20), avoid=["fire_hoop"],
            instruction="Waddle into the big red ring and stand in the gold circle at its centre.",
            paraphrases=["Go stand in the middle of the circus ring.",
                         "Walk to the gold circle in the centre ring."])
w.task_goto("walk_the_wire", goal="stage_top", start=(0.95, -0.4, 90), avoid=["fire_hoop"],
            instruction="Cross the sawdust and climb the narrow wooden plank onto the striped tightrope stage, keeping clear of the flaming hoop.",
            paraphrases=["Walk up the little plank to the tightrope stage.",
                         "Go up the ramp onto the striped stage, minding the fire hoop."])
w.task_gate("open_the_cage", plate="star_plate", goal="lion_cage", start=(-0.7, -1.2, 90), avoid=["fire_hoop"],
            instruction="Step on the yellow star plate by the giant red ball to lift the cage gate, then walk into the lion's cage.",
            paraphrases=["Press the yellow plate near the big red ball, then go into the lion's cage.",
                         "Stand on the star plate to open the steel gate and enter the cage."])
w.task_push("push_the_seal_ball", object="seal_ball", goal="clown_corner", start=(0.35, -0.85, 180), avoid=["fire_hoop"],
            instruction="Push the little yellow ball across the sawdust into the pink clown corner by the barrel.",
            paraphrases=["Shove the yellow ball into the clown corner.",
                         "Roll the little ball over to the pink circle."])
w.task_visit("grand_parade", goals=["centre_ring", "stage_top", "clown_corner"], start=(1.35, 0.3, 180), avoid=["fire_hoop"],
             instruction="Do a grand parade: stand in the gold circle in the centre ring, climb the plank to the tightrope stage, then finish in the clown corner.",
             paraphrases=["Visit the centre ring, then the stage, then the clown corner.",
                          "Parade through the ring, up to the stage, and end in the clown corner."])
w.task_goto("cross_the_greasepaint", goal="centre_ring", start=(-1.43, -0.9, 30), avoid=["fire_hoop"],
            instruction="Cross the shiny purple greasepaint slick the clowns spilled — it is very slippery — and stop in the gold circle in the centre ring.",
            paraphrases=["Skate over the slippery purple patch to the centre ring.",
                         "Carefully cross the spilled greasepaint to the middle of the ring."])
