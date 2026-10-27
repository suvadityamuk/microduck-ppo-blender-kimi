# A frozen-lake ice-fishing village at the Microduck's scale: glare ice between red and blue
# huts, dark open fishing holes to steer around, grit paths, a wooden dock with a lookout
# ramp, and a smokehouse yard behind a sluice gate opened by a brass plate.
w = rw.world("a_frozen_lake_ice_fishing_village_where_",
             "A frozen-lake ice-fishing village: red and blue huts on glare ice, dark fishing "
             "holes, a wooden dock with a lookout ramp, and a smokehouse yard behind a sluice gate.",
             theme="frozen lake ice-fishing village")
w.sky(top=(0.32, 0.48, 0.70), bottom=(0.88, 0.82, 0.72))
w.light(color=(1.0, 0.86, 0.68), azimuth_deg=210, elevation_deg=34, ambient=0.45)

# ---------------- materials ----------------
snow = w.material("snow", color=(0.90, 0.93, 0.98), color2=(0.76, 0.83, 0.94),
                  pattern="noise", scale=5, roughness=0.95, friction=1.1)
ice = w.material("glare_ice", color=(0.58, 0.80, 0.93), color2=(0.88, 0.96, 1.0),
                 pattern="marble", scale=2.5, roughness=0.04, friction=0.08)
grit = w.material("grit_path", color=(0.70, 0.68, 0.62), color2=(0.50, 0.47, 0.40),
                  pattern="concrete", scale=9, roughness=0.9, friction=1.5)
dock = w.material("dock_planks", color=(0.60, 0.44, 0.27), color2=(0.42, 0.28, 0.14),
                  pattern="wood", scale=5, roughness=0.7, friction=0.8)
wall_snow = w.material("snow_banks", color=(0.87, 0.91, 0.97), color2=(0.70, 0.78, 0.90),
                       pattern="noise", scale=4, roughness=0.95)
red_wood = w.material("red_hut_boards", color=(0.70, 0.13, 0.09), color2=(0.50, 0.08, 0.05),
                      pattern="wood", scale=4, roughness=0.6)
blue_wood = w.material("blue_hut_boards", color=(0.15, 0.34, 0.60), color2=(0.09, 0.22, 0.42),
                       pattern="wood", scale=4, roughness=0.6)
ochre_wood = w.material("ochre_hut_boards", color=(0.84, 0.58, 0.16), color2=(0.62, 0.40, 0.09),
                        pattern="wood", scale=4, roughness=0.6)
tar = w.material("tarred_boards", color=(0.14, 0.12, 0.10), color2=(0.06, 0.05, 0.05),
                 pattern="wood", scale=4, roughness=0.85)
roof = w.material("roof_shingles", color=(0.22, 0.24, 0.28), color2=(0.12, 0.13, 0.16),
                  pattern="tiles", scale=10, roughness=0.8)
brass = w.material("brass", color=(0.86, 0.66, 0.28), color2=(0.60, 0.44, 0.16),
                   pattern="brushed", scale=20, roughness=0.35, metallic=1.0)
steel = w.material("stovepipe_steel", color=(0.30, 0.32, 0.36), color2=(0.18, 0.19, 0.22),
                   pattern="brushed", scale=15, roughness=0.4, metallic=0.9)
glow = w.material("warm_lamplight", color=(1.0, 0.72, 0.30), roughness=0.3, emission=0.9)
flag = w.material("flag_red", color=(0.92, 0.10, 0.08), roughness=0.5)
fish_mat = w.material("fish_silver", color=(0.78, 0.82, 0.86), color2=(0.52, 0.56, 0.62),
                      pattern="brushed", scale=12, roughness=0.35, metallic=0.7)
crate_mat = w.material("crate_pine", color=(0.76, 0.60, 0.38), color2=(0.56, 0.42, 0.24),
                       pattern="wood", scale=6, roughness=0.7, friction=0.7)
ball_mat = w.material("packed_snowball", color=(0.95, 0.97, 1.0), color2=(0.85, 0.89, 0.96),
                      pattern="noise", scale=12, roughness=0.55, friction=0.5)

# ---------------- room, floors, structure ----------------
w.room(size=(3.6, 3.4), floor=snow, wall=wall_snow, wall_height=0.3)

w.patch("glare_ice_sheet", center=(0.05, 0.0), size=(2.5, 1.9), material=ice)
w.patch("dock_boards", center=(0.0, -1.42), size=(3.6, 0.56), material=dock)
w.patch("grit_path_east", center=(1.55, -0.02), size=(0.5, 2.24), material=grit)
w.patch("grit_path_west", center=(-1.55, -0.295), size=(0.5, 1.69), material=grit)

# smokehouse yard in the NW corner: two interior walls, gate in the vertical one
w.wall("smoke_fence_east", start=(-1.15, 1.7), end=(-1.15, 1.05), height=0.3,
       material=dock, openings=[(0.325, 0.40)])
w.wall("smoke_fence_south", start=(-1.8, 1.05), end=(-1.15, 1.05), height=0.3, material=dock)
w.gate("smoke_gate", center=(-1.15, 1.375), width=0.40, yaw_deg=0, height=0.24,
       material=tar, frame_material=brass)
w.plate("smoke_plate", center=(-0.88, 1.32), size=0.2, opens="smoke_gate", material=brass)

# lookout deck on the dock, reached by a ramp from the east
w.platform("lookout_platform", center=(-1.45, -1.42), size=(0.6, 0.5), height=0.05, material=dock)
w.ramp("lookout_ramp", start=(-0.9, -1.42), end=(-1.15, -1.42), width=0.4, rise=0.05, material=dock)

# wind-piled snow lumps along the north bank
w.bumps("snow_lumps", center=(0.0, 1.58), size=(1.8, 0.2), max_height=0.012, count=25,
        material=snow, seed=11)

# ---------------- zones ----------------
w.zone("hole_north", center=(-0.45, 0.5), radius=0.16, kind="hazard",
       color=(0.02, 0.08, 0.16), label="the north fishing hole")
w.zone("hole_mid", center=(0.1, 0.1), radius=0.17, kind="hazard",
       color=(0.02, 0.08, 0.16), label="the middle fishing hole")
w.zone("hole_south", center=(-0.35, -0.55), radius=0.15, kind="hazard",
       color=(0.02, 0.08, 0.16), label="the south fishing hole")
w.zone("smokehouse", center=(-1.38, 1.26), radius=0.2, kind="goal",
       color=(0.95, 0.6, 0.2), label="the smokehouse yard")
w.zone("lookout_deck", center=(-1.45, -1.42), radius=0.18, kind="goal",
       color=(0.4, 0.8, 0.5), label="the lookout deck")
w.zone("hut_door_red", center=(-0.3, 0.93), radius=0.16, kind="goal",
       color=(0.9, 0.2, 0.15), label="the red hut's door")
w.zone("hut_door_blue", center=(0.75, 0.93), radius=0.16, kind="goal",
       color=(0.2, 0.45, 0.95), label="the blue hut's door")
w.zone("dock_spot", center=(0.9, -1.42), radius=0.2, kind="goal",
       color=(0.95, 0.85, 0.25), label="the lantern on the dock")
w.zone("fish_rack_spot", center=(1.55, 0.15), radius=0.18, kind="goal",
       color=(0.95, 0.5, 0.15), label="the fish-drying rack")

# ---------------- huts (colliding fixtures, real meshes) ----------------
def ice_hut(name, pos, yaw, boards, body_size, roof_half, roof_rise, roof_len):
    bx, by, bh = body_size
    h = w.fixture(name, pos=(pos[0], pos[1], 0.0), yaw_deg=yaw)
    h.box("body", size=(bx, by, bh), pos=(0, 0, bh / 2), material=boards)
    rf = rw.mesh_prism([(-roof_half, 0.0), (roof_half, 0.0), (0.0, roof_rise)], roof_len)
    rw.move(rf, pos=(0, roof_len / 2, bh), rot_deg=(90, 0, 0))
    h.mesh("roof", rf, material=roof)
    h.box("snow_ridge", size=(0.07, roof_len + 0.02, 0.025), pos=(0, 0, bh + roof_rise + 0.005),
          material=snow, collision=False)
    h.box("door", size=(0.15, 0.025, 0.22), pos=(-0.04, -by / 2 - 0.004, 0.11),
          material=tar, collision=False)
    h.box("window", size=(0.11, 0.02, 0.10), pos=(0.14, -by / 2 - 0.003, 0.20),
          material=glow, collision=False)
    h.cylinder("stovepipe", 0.018, 0.16, pos=(0.13, 0.08, bh + roof_rise + 0.04),
               axis="z", material=steel, collision=False)
    h.cylinder("pipe_cap", 0.028, 0.015, pos=(0.13, 0.08, bh + roof_rise + 0.125),
               axis="z", material=steel, collision=False)
    return h

ice_hut("red_ice_hut", (-0.3, 1.38), 0, red_wood, (0.5, 0.45, 0.34), 0.30, 0.17, 0.53)
ice_hut("blue_ice_hut", (0.75, 1.35), 0, blue_wood, (0.55, 0.5, 0.38), 0.32, 0.18, 0.58)
ice_hut("ochre_ice_hut", (1.2, -0.6), 180, ochre_wood, (0.45, 0.42, 0.30), 0.25, 0.14, 0.48)

# smokehouse inside the gated yard
sm = w.fixture("smokehouse", pos=(-1.66, 1.56, 0.0))
sm.box("body", size=(0.22, 0.22, 0.30), pos=(0, 0, 0.15), material=tar)
sm.box("roof_slab", size=(0.26, 0.26, 0.03), pos=(0, 0, 0.315), material=roof)
sm.cylinder("chimney", 0.028, 0.22, pos=(0.05, 0.05, 0.40), axis="z", material=steel, collision=False)
sm.box("vent_glow", size=(0.06, 0.02, 0.05), pos=(0, -0.105, 0.18), material=glow, collision=False)

# ---------------- village props (decor, modelled meshes) ----------------
def lantern(name, pos):
    d = w.decor(name, pos=(pos[0], pos[1], 0.0))
    post = rw.mesh_lathe([(0.045, 0.0), (0.032, 0.02), (0.014, 0.05), (0.014, 0.40),
                          (0.030, 0.43), (0.030, 0.44)], segments=24)
    d.mesh("post", post, material=steel)
    d.box("lamp_head", size=(0.07, 0.07, 0.085), pos=(0, 0, 0.49), material=brass, collision=False)
    d.sphere("bulb", 0.028, pos=(0, 0, 0.49), material=glow, collision=False)
    cap = rw.mesh_lathe([(0.055, 0.535), (0.0, 0.575)], segments=24)
    d.mesh("cap", cap, material=brass, collision=False)

lantern("dock_lantern", (0.9, -1.6))
lantern("west_path_lantern", (-1.6, 0.72))
lantern("north_lantern", (1.5, 1.45))

# fish-drying rack with silver fish on the east grit path
rack = w.decor("fish_rack", pos=(1.55, 0.45, 0.0))
rack.cylinder("post_l", 0.016, 0.42, pos=(-0.21, 0, 0.21), axis="z", material=dock)
rack.cylinder("post_r", 0.016, 0.42, pos=(0.21, 0, 0.21), axis="z", material=dock)
rack.cylinder("crossbar", 0.012, 0.48, pos=(0, 0, 0.40), axis="x", material=dock)
fish_shape = [(-0.045, 0.0), (-0.020, 0.016), (0.018, 0.020), (0.045, 0.0),
              (0.018, -0.020), (-0.020, -0.016)]
for i, fx in enumerate([-0.15, -0.05, 0.05, 0.15]):
    f = rw.mesh_prism(fish_shape, 0.012)
    rw.move(f, pos=(fx, 0.0, 0.335), rot_deg=(90, 0, 0))
    rack.mesh(f"fish_{i}", f, material=fish_mat, collision=False)
    rack.cylinder(f"string_{i}", 0.003, 0.05, pos=(fx, 0, 0.372), axis="z",
                  material=tar, collision=False)

# dock pile: lathe barrel, fish crates and a rope coil
pile = w.decor("dock_pile", pos=(1.55, -1.52, 0.0), yaw_deg=-5)
barrel = rw.mesh_lathe([(0.0, 0.0), (0.070, 0.0), (0.088, 0.05), (0.095, 0.12),
                        (0.088, 0.19), (0.070, 0.24), (0.0, 0.24)], segments=32)
rw.move(barrel, pos=(0.06, -0.02, 0.0))
pile.mesh("barrel", barrel, material=dock)
pile.box("crate_a", size=(0.20, 0.20, 0.12), pos=(-0.10, 0.03, 0.06), material=crate_mat)
pile.box("crate_b", size=(0.16, 0.16, 0.10), pos=(-0.10, 0.03, 0.17), material=crate_mat,
         rot_deg=(0, 0, 12), collision=False)
rope = rw.mesh_torus(0.055, 0.018)
rw.move(rope, pos=(0.07, 0.12, 0.02))
pile.mesh("rope_coil", rope, material=grit, collision=False)

# wooden sled with a red bedroll, parked on the dock
sled = w.decor("sled", pos=(-0.55, -1.58, 0.0), yaw_deg=8)
sled.box("runner_l", size=(0.40, 0.03, 0.05), pos=(0, -0.085, 0.025), material=dock)
sled.box("runner_r", size=(0.40, 0.03, 0.05), pos=(0, 0.085, 0.025), material=dock)
for i, sx in enumerate([-0.13, 0.0, 0.13]):
    sled.box(f"slat_{i}", size=(0.09, 0.23, 0.02), pos=(sx, 0, 0.06), material=crate_mat)
sled.box("bedroll", size=(0.20, 0.16, 0.07), pos=(0.03, 0, 0.105), material=flag, collision=False)

# firewood stack by the smokehouse fence
wp = w.decor("wood_pile", pos=(-1.60, 0.92, 0.0))
for i, (ly, lz) in enumerate([(-0.045, 0.035), (0.045, 0.035), (0.0, 0.095)]):
    wp.cylinder(f"log_{i}", 0.035, 0.42, pos=(0, ly, lz), axis="x", material=dock)

# tip-up fishing rigs with red flags beside each hole
def tipup(name, pos, yaw):
    t = w.decor(name, pos=(pos[0], pos[1], 0.0), yaw_deg=yaw)
    t.box("stick_a", size=(0.18, 0.02, 0.015), pos=(0, 0, 0.02), material=dock, rot_deg=(0, 0, 45))
    t.box("stick_b", size=(0.18, 0.02, 0.015), pos=(0, 0, 0.035), material=dock, rot_deg=(0, 0, -45))
    t.cylinder("spindle", 0.006, 0.14, pos=(0, 0, 0.09), axis="z", material=steel)
    t.box("flag", size=(0.06, 0.005, 0.04), pos=(0.035, 0, 0.14), material=flag, collision=False)

tipup("tipup_north", (-0.18, 0.55), 20)
tipup("tipup_mid", (0.36, 0.05), -35)
tipup("tipup_south", (-0.60, -0.48), 70)

# little three-legged fishing stool by the north hole
st = w.decor("fishing_stool", pos=(-0.64, 0.40, 0.0), yaw_deg=15)
st.cylinder("seat", 0.055, 0.025, pos=(0, 0, 0.085), axis="z", material=dock)
for i, (lx, ly) in enumerate([(-0.035, -0.035), (0.035, -0.035), (0.0, 0.045)]):
    st.cylinder(f"leg_{i}", 0.008, 0.08, pos=(lx, ly, 0.04), axis="z", material=dock)

# channel-marker buoys frozen into the ice edge
def buoy(name, pos):
    b = w.decor(name, pos=(pos[0], pos[1], 0.0))
    body = rw.mesh_lathe([(0.0, 0.0), (0.045, 0.01), (0.055, 0.07), (0.035, 0.14),
                          (0.013, 0.18), (0.013, 0.24), (0.030, 0.26), (0.0, 0.29)], segments=24)
    b.mesh("body", body, material=flag)
    b.sphere("top", 0.02, pos=(0, 0, 0.27), material=ball_mat, collision=False)

buoy("buoy_south", (-1.05, -0.98))
buoy("buoy_east", (1.36, 0.75))

# ---------------- free objects ----------------
w.ball("snowball", pos=(0.6, -0.5), radius=0.06, mass=0.05, material=ball_mat)
w.crate("fish_crate", pos=(-1.0, -0.7), size=(0.12, 0.10, 0.08), mass=0.06, material=crate_mat)

# ---------------- tasks ----------------
HOLES = ["hole_north", "hole_mid", "hole_south"]

w.task_goto("cross_the_glare_ice", goal="hut_door_red", start=(0.9, -1.42, 90), avoid=HOLES,
            instruction="Cross the glare ice to the little red hut's door, and keep well clear of the dark open fishing holes.",
            paraphrases=["Walk over the shiny ice to the red hut, minding the holes.",
                         "Make your way across the frozen lake to the red hut's doorway without stepping in a fishing hole."])
w.task_goto("climb_the_lookout", goal="lookout_deck", start=(0.35, -1.42, 180), avoid=HOLES,
            instruction="Walk west along the wooden dock, go up the little ramp and stand on the lookout deck.",
            paraphrases=["Climb the ramp onto the raised deck at the west end of the dock.",
                         "Go up onto the wooden lookout platform above the dock."])
w.task_gate("smokehouse_sluice", plate="smoke_plate", goal="smokehouse", start=(-0.9, 0.2, 45), avoid=HOLES,
            instruction="Step on the round brass plate by the smokehouse fence to lift the wooden sluice gate, then walk into the smokehouse yard.",
            paraphrases=["Press the brass plate in front of the smokehouse and go through the gate it opens.",
                         "Stand on the shiny plate to raise the sluice gate, then enter the smokehouse yard."])
w.task_push("roll_the_snowball", object="snowball", goal="hut_door_blue", start=(0.55, -0.78, 90), avoid=HOLES,
            instruction="Push the big snowball across the ice to the blue hut's door.",
            paraphrases=["Roll the snowball over the glare ice to the blue hut.",
                         "Shove the snowball all the way up to the blue hut's doorway."])
w.task_visit("evening_rounds", goals=["hut_door_red", "fish_rack_spot", "dock_spot"],
             start=(0.0, -1.42, 90), avoid=HOLES,
             instruction="Do the evening rounds: stop at the red hut's door, then visit the fish-drying rack on the grit path, then finish by the lantern on the dock.",
             paraphrases=["Check the red hut, then the fish rack, then the dock lantern.",
                          "Go to the red hut's door first, then the drying rack, and end by the glowing dock lantern."])
w.task_push("crate_to_the_dock", object="fish_crate", goal="dock_spot", start=(-1.05, -0.42, 90), avoid=HOLES,
            instruction="Shove the wooden fish crate off the ice and onto the dock, stopping by the lantern.",
            paraphrases=["Push the fish crate across the ice to the lantern on the dock.",
                         "Slide the crate of fish over the frozen lake to the wooden dock."])
