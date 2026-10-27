# Hand-written sample in the style the designer LLM is asked to produce (Microduck scale: the robot is 25 cm tall).
w = rw.world("toyshop_after_hours", "A toy shop after closing: a polished checkerboard floor, a skating mat of wax, "
             "a toy-train stage up a ramp and a back stockroom behind a wind-up portcullis.", theme="toy shop after hours")
w.sky(top=(0.20, 0.18, 0.30), bottom=(0.55, 0.45, 0.40))
w.light(color=(1.0, 0.92, 0.80), azimuth_deg=135, elevation_deg=55, ambient=0.35)

floor = w.material("checker_floor", color=(0.85, 0.80, 0.70), color2=(0.45, 0.20, 0.18), pattern="checker", scale=4, roughness=0.5, friction=0.8)
walls = w.material("wallpaper", color=(0.30, 0.55, 0.60), color2=(0.85, 0.80, 0.55), pattern="stripes", scale=10, roughness=0.8)
wax = w.material("waxed_mat", color=(0.75, 0.90, 1.00), color2=(0.95, 0.98, 1.0), pattern="marble", scale=3, roughness=0.05, friction=0.12)
wood = w.material("maple", color=(0.80, 0.60, 0.35), color2=(0.60, 0.40, 0.20), pattern="wood", scale=6, friction=0.7)
red = w.material("toy_red", color=(0.90, 0.15, 0.12), roughness=0.35)
blue = w.material("toy_blue", color=(0.15, 0.35, 0.90), roughness=0.35)
yellow = w.material("toy_yellow", color=(0.98, 0.80, 0.10), roughness=0.4)
brass = w.material("brass", color=(0.85, 0.66, 0.28), color2=(0.6, 0.45, 0.18), pattern="brushed", scale=20, roughness=0.3, metallic=1.0)
felt = w.material("green_felt", color=(0.15, 0.55, 0.25), color2=(0.10, 0.40, 0.18), pattern="fabric", scale=30, friction=1.4)

w.room(size=(3.2, 3.0), floor=floor, wall=walls, wall_height=0.35)

# back stockroom behind an interior wall with one doorway, closed by a wind-up portcullis
w.wall("stockroom_wall", start=(0.6, -1.5), end=(0.6, 1.5), height=0.3, material=walls, openings=[(1.9, 0.42)])
w.gate("toy_gate", center=(0.6, 0.4), width=0.42, yaw_deg=0, material=brass, frame_material=red)
w.plate("gate_plate", center=(-0.3, 0.9), size=0.2, opens="toy_gate", material=yellow)

# skating mat of wax: very slippery
w.patch("wax_mat", center=(-0.7, -0.5), size=(0.9, 0.6), material=wax)

# the train stage: ramp up to a low platform
w.ramp("stage_ramp", start=(-1.35, 0.15), end=(-1.35, 0.55), rise=0.05, width=0.45, material=wood)
w.platform("train_stage", center=(-1.35, 0.95), size=(0.6, 0.8), height=0.05, material=felt)

# a hazard: the open toy-train track pit
w.zone("track_pit", center=(-0.25, -0.05), radius=0.18, kind="hazard", color=(0.1, 0.1, 0.1), label="the open track pit")
w.zone("felt_stage", center=(-1.35, 1.0), radius=0.2, kind="goal", color=(0.2, 0.8, 0.3), label="the green felt stage")
w.zone("stockroom", center=(1.1, 0.4), radius=0.25, kind="goal", color=(0.95, 0.85, 0.2), label="the stockroom")
w.zone("toy_chest_spot", center=(0.15, -1.05), radius=0.2, kind="goal", color=(0.9, 0.3, 0.7), label="the pink rug by the toy chest")
w.zone("counter", center=(-1.15, -1.1), radius=0.18, kind="goal", color=(0.3, 0.6, 1.0), label="the blue rug by the counter")

# props: modelled meshes
chest = w.fixture("toy_chest", pos=(0.15, -1.38, 0.0))
lid = rw.mesh_box((0.5, 0.18, 0.16), bevel=0.02)
rw.move(lid, pos=(0, 0, 0.08))
chest.mesh("body", lid, material=red)
rw.move(band := rw.mesh_box((0.52, 0.2, 0.02), bevel=0.005), pos=(0, 0, 0.12))
chest.mesh("band", band, material=brass, collision=False)

lamp = w.decor("street_lamp", pos=(1.45, -1.3, 0.0))
post = rw.mesh_lathe([(0.05, 0.0), (0.03, 0.02), (0.012, 0.05), (0.012, 0.9), (0.06, 0.95), (0.05, 1.05), (0.0, 1.1)])
lamp.mesh("lamp", post, material=brass)
lamp.sphere("bulb", 0.04, pos=(0, 0, 1.0), material=yellow)

soldier = w.fixture("tin_soldier", pos=(-1.4, -0.4, 0.0))
body = rw.mesh_lathe([(0.07, 0.0), (0.06, 0.05), (0.05, 0.25), (0.06, 0.32), (0.045, 0.38), (0.05, 0.45), (0.0, 0.5)])
soldier.mesh("body", body, material=blue)
hat = rw.mesh_cylinder(0.04, 0.12, bevel=0.01)
rw.move(hat, pos=(0, 0, 0.55))
soldier.mesh("hat", hat, material=red, collision=False)

# blocks and a ball
w.ball("beach_ball", pos=(-0.2, -0.95), radius=0.05, mass=0.03, material=yellow)
block = w.crate("abc_block", pos=(0.25, 0.75), size=(0.09, 0.09, 0.09), mass=0.04, material=blue)

w.task_goto("climb_to_stage", goal="felt_stage", start=(-0.6, 0.2, 90), avoid=["track_pit"],
            instruction="Walk up the ramp onto the green felt stage.",
            paraphrases=["Go up onto the toy-train stage.", "Climb the wooden ramp to the green stage."])
w.task_goto("cross_wax", goal="counter", start=(0.0, -0.4, 180), avoid=["track_pit"],
            instruction="Cross the shiny wax mat carefully and stop on the blue rug by the counter.",
            paraphrases=["Walk over the slippery mat to the blue rug.", "Get to the counter's blue rug without falling."])
w.task_gate("open_stockroom", plate="gate_plate", goal="stockroom", start=(-0.6, 0.3, 0), avoid=["track_pit"],
            instruction="Step on the yellow plate to open the brass gate, then go into the stockroom.",
            paraphrases=["Open the gate with the yellow plate and walk into the back room.",
                         "Press the yellow floor plate, then go through the gate."])
w.task_push("ball_to_chest", object="beach_ball", goal="toy_chest_spot", start=(-0.6, -0.9, 0),
            instruction="Push the yellow beach ball onto the pink rug by the toy chest.",
            paraphrases=["Nudge the yellow ball over to the pink rug.", "Roll the beach ball to the toy chest."])
w.task_visit("patrol", goals=["counter", "felt_stage"], start=(0.2, 0.0, 180), avoid=["track_pit"],
             instruction="Go to the blue rug by the counter, then up onto the green stage.",
             paraphrases=["Visit the counter first, then the felt stage.", "Stop at the blue rug, then climb to the stage."])
