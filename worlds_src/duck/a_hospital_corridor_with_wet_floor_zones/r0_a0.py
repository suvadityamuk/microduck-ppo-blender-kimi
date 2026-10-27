w = rw.world("a_hospital_corridor_with_wet_floor_zones",
             "A bright hospital corridor with freshly mopped wet-floor zones under yellow caution signs, "
             "frosted-glass sliding doors opened by floor pads, supply carts to steer around, and rounds "
             "through the ward, the X-ray bay and the operating theatre.",
             theme="hospital corridor")
w.sky(top=(0.62, 0.76, 0.92), bottom=(0.96, 0.97, 0.98))
w.light(color=(1.0, 0.98, 0.94), azimuth_deg=120, elevation_deg=65, ambient=0.45)

# ---------------- materials ----------------
m_floor  = w.material("vinyl_tiles", color=(0.90, 0.92, 0.94), color2=(0.76, 0.83, 0.86), pattern="tiles", scale=5, roughness=0.35, friction=0.7)
m_wall   = w.material("wall_paint", color=(0.88, 0.93, 0.90), color2=(0.60, 0.75, 0.69), pattern="stripes", scale=12, roughness=0.85)
m_wet    = w.material("wet_vinyl", color=(0.58, 0.79, 0.95), color2=(0.85, 0.95, 1.0), pattern="marble", scale=3, roughness=0.05, friction=0.12)
m_rug_blue   = w.material("blue_rug", color=(0.20, 0.45, 0.85), color2=(0.13, 0.32, 0.68), pattern="fabric", scale=20, friction=1.3)
m_mat_yellow = w.material("yellow_mat", color=(0.95, 0.78, 0.12), color2=(0.84, 0.64, 0.08), pattern="dots", scale=25, friction=1.2)
m_rug_red    = w.material("red_rug", color=(0.80, 0.22, 0.22), color2=(0.62, 0.14, 0.14), pattern="fabric", scale=20, friction=1.2)
m_mat_white  = w.material("white_mat", color=(0.93, 0.95, 0.96), color2=(0.84, 0.88, 0.90), pattern="fabric", scale=20, friction=1.1)
m_steel  = w.material("brushed_steel", color=(0.72, 0.74, 0.78), color2=(0.55, 0.58, 0.62), pattern="brushed", scale=30, roughness=0.3, metallic=1.0)
m_white  = w.material("white_plastic", color=(0.96, 0.97, 0.98), roughness=0.35)
m_red    = w.material("signal_red", color=(0.85, 0.10, 0.12), roughness=0.4)
m_yellow = w.material("caution_yellow", color=(0.98, 0.80, 0.06), roughness=0.5)
m_teal   = w.material("curtain_teal", color=(0.12, 0.55, 0.52), color2=(0.08, 0.42, 0.40), pattern="fabric", scale=15, roughness=0.7)
m_black  = w.material("rubber_black", color=(0.08, 0.08, 0.10), roughness=0.9, friction=1.6)
m_glass  = w.material("frosted_glass", color=(0.80, 0.92, 0.96), roughness=0.15, alpha=0.5, emission=0.05)
m_screen = w.material("monitor_glow", color=(0.30, 0.70, 0.90), emission=0.6)
m_light  = w.material("light_panel", color=(1.0, 1.0, 0.98), emission=0.9)
m_green  = w.material("linen_green", color=(0.65, 0.82, 0.72), color2=(0.52, 0.72, 0.60), pattern="fabric", scale=25)
m_blue   = w.material("plastic_blue", color=(0.20, 0.40, 0.80), roughness=0.4)
m_pad_green = w.material("pad_green", color=(0.20, 0.70, 0.40), roughness=0.5)
m_bag    = w.material("iv_bag", color=(0.85, 0.95, 1.0), roughness=0.1, alpha=0.6)

# ---------------- room & structure ----------------
w.room(size=(4.0, 3.2), floor=m_floor, wall=m_wall, wall_height=0.35)

# corridor walls with doorways; rooms off the north and south sides
w.wall("corridor_wall_north", start=(-2.0, 0.6), end=(2.0, 0.6), height=0.3, thickness=0.04,
       material=m_wall, openings=[(0.85, 0.42), (3.15, 0.42)])
w.wall("corridor_wall_south", start=(-2.0, -0.6), end=(2.0, -0.6), height=0.3, thickness=0.04,
       material=m_wall, openings=[(0.85, 0.42), (3.15, 0.42)])
w.wall("divider_north", start=(0.0, 0.6), end=(0.0, 1.6), height=0.3, thickness=0.04, material=m_wall)
w.wall("divider_south", start=(0.0, -0.6), end=(0.0, -1.6), height=0.3, thickness=0.04, material=m_wall)

# sliding glass doors (gates) and their floor pads
w.gate("supply_door", center=(1.15, 0.6), width=0.42, yaw_deg=90, height=0.24, material=m_glass, frame_material=m_steel)
w.gate("theatre_door", center=(1.15, -0.6), width=0.42, yaw_deg=90, height=0.24, material=m_glass, frame_material=m_steel)
w.plate("supply_plate", center=(1.25, 0.38), size=0.2, opens="supply_door", material=m_blue)
w.plate("theatre_plate", center=(1.25, -0.38), size=0.2, opens="theatre_door", material=m_pad_green)

# wet-floor zones (very slippery) and coloured goal rugs
w.patch("wet_floor_ward", center=(-1.15, 0.32), size=(0.75, 0.5), material=m_wet)
w.patch("wet_floor_mid", center=(0.15, -0.28), size=(0.8, 0.44), material=m_wet)
w.patch("rug_reception", center=(-1.72, 0.1), size=(0.34, 0.34), material=m_rug_red)
w.patch("rug_ward", center=(-0.9, 1.05), size=(0.38, 0.38), material=m_rug_blue)
w.patch("mat_supply", center=(1.2, 1.1), size=(0.4, 0.4), material=m_mat_yellow)
w.patch("mat_theatre", center=(1.3, -1.1), size=(0.4, 0.4), material=m_mat_white)

# X-ray scanning bay: blue ramp up to a low white platform
w.ramp("xray_ramp", start=(-1.2, -0.7), end=(-1.2, -1.0), width=0.45, rise=0.05, material=m_rug_blue)
w.platform("xray_platform", center=(-1.2, -1.25), size=(0.7, 0.5), height=0.05, material=m_mat_white)

# ---------------- zones ----------------
w.zone("disinfectant_spill", center=(-0.1, 0.25), radius=0.15, kind="hazard", color=(0.3, 1.0, 0.25), label="the green disinfectant spill")
w.zone("reception", center=(-1.7, 0.1), radius=0.18, kind="goal", color=(0.9, 0.2, 0.2), label="the red rug at reception")
w.zone("ward_a", center=(-0.9, 1.05), radius=0.2, kind="goal", color=(0.25, 0.5, 0.95), label="the blue rug by the hospital bed")
w.zone("supply_room", center=(1.2, 1.1), radius=0.22, kind="goal", color=(0.95, 0.8, 0.15), label="the yellow mat in the supply room")
w.zone("operating_theatre", center=(1.3, -1.1), radius=0.22, kind="goal", color=(0.95, 0.95, 0.97), label="the white mat by the operating table")
w.zone("xray_bay", center=(-1.2, -1.25), radius=0.18, kind="goal", color=(0.6, 0.3, 0.9), label="the purple ring on the X-ray platform")
w.zone("delivery_spot", center=(1.5, 0.0), radius=0.18, kind="goal", color=(0.2, 0.85, 0.45), label="the green circle at the nurse's station")

# ---------------- modelled props ----------------
_pc = [0]
def part(body, obj, mat, coll=True):
    _pc[0] += 1
    body.mesh("m%d" % _pc[0], obj, material=mat, collision=coll)

def build_supply_cart(name, pos, yaw_deg):
    c = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_box((0.34, 0.20, 0.02), bevel=0.005); rw.move(o, pos=(0, 0, 0.08)); part(c, o, m_steel)
    o = rw.mesh_box((0.34, 0.20, 0.02), bevel=0.005); rw.move(o, pos=(0, 0, 0.24)); part(c, o, m_white)
    for yy in (-0.095, 0.095):
        o = rw.mesh_box((0.34, 0.012, 0.03), bevel=0.003); rw.move(o, pos=(0, yy, 0.265)); part(c, o, m_steel, False)
    for xx in (-0.165, 0.165):
        o = rw.mesh_box((0.012, 0.20, 0.03), bevel=0.003); rw.move(o, pos=(xx, 0, 0.265)); part(c, o, m_steel, False)
    for xx in (-0.15, 0.15):
        for yy in (-0.085, 0.085):
            o = rw.mesh_cylinder(0.008, 0.22); rw.move(o, pos=(xx, yy, 0.16)); part(c, o, m_steel, False)
    o = rw.mesh_cylinder(0.008, 0.20, axis="y"); rw.move(o, pos=(-0.19, 0, 0.30)); part(c, o, m_steel, False)
    for yy in (-0.085, 0.085):
        o = rw.mesh_cylinder(0.006, 0.05, axis="x"); rw.move(o, pos=(-0.175, yy, 0.30)); part(c, o, m_steel, False)
    for xx in (-0.14, 0.14):
        for yy in (-0.085, 0.085):
            o = rw.mesh_cylinder(0.028, 0.018, axis="y"); rw.move(o, pos=(xx, yy, 0.028)); part(c, o, m_black)
    o = rw.mesh_box((0.09, 0.004, 0.028)); rw.move(o, pos=(0.05, -0.103, 0.24)); part(c, o, m_red, False)
    o = rw.mesh_box((0.028, 0.004, 0.09)); rw.move(o, pos=(0.05, -0.103, 0.24)); part(c, o, m_red, False)
    o = rw.mesh_cylinder(0.014, 0.06); rw.move(o, pos=(-0.08, 0.03, 0.28)); part(c, o, m_blue, False)
    o = rw.mesh_cylinder(0.012, 0.05); rw.move(o, pos=(-0.05, -0.04, 0.275)); part(c, o, m_red, False)
    o = rw.mesh_box((0.10, 0.12, 0.06), bevel=0.005); rw.move(o, pos=(0.06, 0.0, 0.12)); part(c, o, m_teal, False)

def build_bed(name, pos, yaw_deg):
    b = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_box((0.68, 0.30, 0.03), bevel=0.008); rw.move(o, pos=(0, 0, 0.17)); part(b, o, m_steel)
    o = rw.mesh_box((0.64, 0.28, 0.05), bevel=0.015); rw.move(o, pos=(0, 0, 0.21)); part(b, o, m_white)
    o = rw.mesh_box((0.34, 0.28, 0.02), bevel=0.008); rw.move(o, pos=(0.12, 0, 0.245)); part(b, o, m_teal, False)
    o = rw.mesh_box((0.14, 0.20, 0.04), bevel=0.015); rw.move(o, pos=(-0.24, 0, 0.245)); part(b, o, m_white, False)
    o = rw.mesh_box((0.02, 0.30, 0.16), bevel=0.006); rw.move(o, pos=(-0.35, 0, 0.25)); part(b, o, m_blue)
    o = rw.mesh_box((0.02, 0.30, 0.12), bevel=0.006); rw.move(o, pos=(0.35, 0, 0.23)); part(b, o, m_blue)
    for xx in (-0.28, 0.28):
        for yy in (-0.11, 0.11):
            o = rw.mesh_cylinder(0.012, 0.17); rw.move(o, pos=(xx, yy, 0.085)); part(b, o, m_steel)
    o = rw.mesh_box((0.30, 0.012, 0.05), bevel=0.003); rw.move(o, pos=(0.05, 0.145, 0.28)); part(b, o, m_steel, False)

def build_op_table(name, pos, yaw_deg):
    t = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_cylinder(0.12, 0.02); rw.move(o, pos=(0, 0, 0.01)); part(t, o, m_steel)
    o = rw.mesh_cylinder(0.05, 0.19); rw.move(o, pos=(0, 0, 0.105)); part(t, o, m_steel)
    o = rw.mesh_box((0.55, 0.26, 0.04), bevel=0.01); rw.move(o, pos=(0, 0, 0.21)); part(t, o, m_white)
    o = rw.mesh_box((0.50, 0.22, 0.02), bevel=0.008); rw.move(o, pos=(0, 0, 0.24)); part(t, o, m_green, False)
    o = rw.mesh_box((0.10, 0.16, 0.03), bevel=0.01); rw.move(o, pos=(-0.18, 0, 0.255)); part(t, o, m_white, False)

def build_nurse_desk(name, pos, yaw_deg):
    d = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_box((0.22, 0.46, 0.20), bevel=0.01); rw.move(o, pos=(0, 0, 0.10)); part(d, o, m_white)
    o = rw.mesh_box((0.26, 0.50, 0.02), bevel=0.008); rw.move(o, pos=(0, 0, 0.21)); part(d, o, m_blue)
    o = rw.mesh_box((0.02, 0.03, 0.05)); rw.move(o, pos=(-0.05, 0.08, 0.245)); part(d, o, m_black, False)
    o = rw.mesh_box((0.015, 0.15, 0.11)); rw.move(o, pos=(-0.05, 0.08, 0.31)); part(d, o, m_black, False)
    o = rw.mesh_box((0.004, 0.13, 0.09)); rw.move(o, pos=(-0.06, 0.08, 0.31)); part(d, o, m_screen, False)
    o = rw.mesh_box((0.10, 0.06, 0.008)); rw.move(o, pos=(-0.05, -0.10, 0.225)); part(d, o, m_white, False)

def build_shelf(name, pos, yaw_deg):
    s = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_box((0.02, 0.68, 0.34)); rw.move(o, pos=(0.11, 0, 0.17)); part(s, o, m_steel)
    for yy in (-0.34, 0.34):
        o = rw.mesh_box((0.24, 0.02, 0.34)); rw.move(o, pos=(0, yy, 0.17)); part(s, o, m_steel)
    for zz in (0.06, 0.17, 0.28):
        o = rw.mesh_box((0.22, 0.66, 0.015)); rw.move(o, pos=(0, 0, zz)); part(s, o, m_white)
    goods = [((0.07, 0.09, 0.06), (-0.02, -0.18, 0.098), m_white),
             ((0.06, 0.08, 0.05), (0.0, 0.05, 0.093), m_blue),
             ((0.08, 0.10, 0.07), (-0.02, 0.22, 0.103), m_green),
             ((0.06, 0.09, 0.05), (0.0, -0.10, 0.203), m_red),
             ((0.07, 0.07, 0.06), (-0.02, 0.15, 0.208), m_white),
             ((0.09, 0.12, 0.05), (-0.02, 0.0, 0.313), m_teal)]
    for size, gpos, gmat in goods:
        o = rw.mesh_box(size, bevel=0.005); rw.move(o, pos=gpos); part(s, o, gmat, False)

def build_crate_stack(name, pos, yaw_deg):
    c = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_box((0.18, 0.18, 0.12), bevel=0.008); rw.move(o, pos=(0, 0, 0.06)); part(c, o, m_blue)
    o = rw.mesh_box((0.15, 0.15, 0.10), bevel=0.008); rw.move(o, pos=(0.01, 0.01, 0.17)); part(c, o, m_white)
    o = rw.mesh_box((0.11, 0.11, 0.08), bevel=0.006); rw.move(o, pos=(-0.01, 0.0, 0.26)); part(c, o, m_teal)

def build_bin(name, pos, yaw_deg):
    b = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_lathe([(0.0, 0.0), (0.055, 0.0), (0.06, 0.02), (0.06, 0.13), (0.065, 0.14), (0.065, 0.15), (0.0, 0.15)])
    part(b, o, m_yellow)
    o = rw.mesh_box((0.03, 0.025, 0.012)); rw.move(o, pos=(0, -0.07, 0.008)); part(b, o, m_steel, False)
    o = rw.mesh_box((0.035, 0.004, 0.045)); rw.move(o, pos=(0, -0.062, 0.08)); part(b, o, m_red, False)

def build_wheelchair(name, pos, yaw_deg):
    c = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    for yy in (-0.13, 0.13):
        o = rw.mesh_torus(0.085, 0.012); rw.move(o, pos=(0, yy, 0.085), rot_deg=(90, 0, 0)); part(c, o, m_black)
    o = rw.mesh_box((0.22, 0.22, 0.025), bevel=0.006); rw.move(o, pos=(0, 0, 0.135)); part(c, o, m_teal)
    o = rw.mesh_box((0.025, 0.22, 0.15), bevel=0.006); rw.move(o, pos=(-0.11, 0, 0.215)); part(c, o, m_teal)
    for yy in (-0.07, 0.07):
        o = rw.mesh_box((0.09, 0.04, 0.01)); rw.move(o, pos=(0.13, yy, 0.03)); part(c, o, m_steel, False)
    for yy in (-0.10, 0.10):
        o = rw.mesh_box((0.14, 0.03, 0.015)); rw.move(o, pos=(-0.02, yy, 0.185)); part(c, o, m_black, False)
        o = rw.mesh_cylinder(0.005, 0.05, axis="y"); rw.move(o, pos=(-0.125, yy, 0.30)); part(c, o, m_steel, False)

def build_xray_machine(name, pos, yaw_deg):
    m = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_box((0.10, 0.16, 0.42), bevel=0.01); rw.move(o, pos=(0, 0, 0.21)); part(m, o, m_white)
    o = rw.mesh_box((0.30, 0.08, 0.05), bevel=0.008); rw.move(o, pos=(0.17, 0, 0.37)); part(m, o, m_steel)
    o = rw.mesh_box((0.08, 0.10, 0.10), bevel=0.01); rw.move(o, pos=(0.30, 0, 0.32)); part(m, o, m_white)
    o = rw.mesh_box((0.015, 0.10, 0.14)); rw.move(o, pos=(0.055, 0, 0.24)); part(m, o, m_black, False)
    o = rw.mesh_cylinder(0.008, 0.005, axis="x"); rw.move(o, pos=(0.065, 0.02, 0.26)); part(m, o, m_screen, False)
    o = rw.mesh_cylinder(0.008, 0.005, axis="x"); rw.move(o, pos=(0.065, -0.02, 0.22)); part(m, o, m_red, False)

def build_stool(name, pos, yaw_deg):
    s = w.fixture(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_cylinder(0.07, 0.015); rw.move(o, pos=(0, 0, 0.008)); part(s, o, m_steel)
    o = rw.mesh_cylinder(0.012, 0.15); rw.move(o, pos=(0, 0, 0.075)); part(s, o, m_steel)
    o = rw.mesh_cylinder(0.09, 0.02); rw.move(o, pos=(0, 0, 0.16)); part(s, o, m_teal)

def build_caution_sign(name, pos, yaw_deg):
    s = w.decor(name, pos=pos, yaw_deg=yaw_deg)
    o = rw.mesh_box((0.15, 0.008, 0.19)); rw.move(o, pos=(-0.033, 0, 0.093), rot_deg=(0, 16, 0)); part(s, o, m_yellow, False)
    o = rw.mesh_box((0.15, 0.008, 0.19)); rw.move(o, pos=(0.033, 0, 0.093), rot_deg=(0, -16, 0)); part(s, o, m_yellow, False)
    o = rw.mesh_cylinder(0.008, 0.07, axis="y"); rw.move(o, pos=(0, 0, 0.185)); part(s, o, m_steel, False)
    o = rw.mesh_box((0.11, 0.004, 0.08)); rw.move(o, pos=(-0.033, -0.007, 0.093), rot_deg=(0, 16, 0)); part(s, o, m_white, False)
    o = rw.mesh_box((0.11, 0.004, 0.08)); rw.move(o, pos=(0.033, 0.007, 0.093), rot_deg=(0, -16, 0)); part(s, o, m_white, False)
    o = rw.mesh_box((0.014, 0.003, 0.030)); rw.move(o, pos=(-0.033, -0.010, 0.098), rot_deg=(0, 16, 0)); part(s, o, m_black, False)
    o = rw.mesh_box((0.014, 0.003, 0.010)); rw.move(o, pos=(-0.033, -0.010, 0.072), rot_deg=(0, 16, 0)); part(s, o, m_black, False)
    o = rw.mesh_box((0.014, 0.003, 0.030)); rw.move(o, pos=(0.033, 0.010, 0.098), rot_deg=(0, -16, 0)); part(s, o, m_black, False)
    o = rw.mesh_box((0.014, 0.003, 0.010)); rw.move(o, pos=(0.033, 0.010, 0.072), rot_deg=(0, -16, 0)); part(s, o, m_black, False)

build_supply_cart("corridor_cart", (-0.5, -0.42, 0.0), 5)
build_supply_cart("supply_cart", (0.55, 0.9, 0.0), -12)
build_bed("ward_bed", (-1.6, 1.18, 0.0), 0)
build_op_table("operating_table", (0.5, -1.15, 0.0), 0)
build_nurse_desk("nurse_desk", (1.86, 0.0, 0.0), 0)
build_shelf("supply_shelf", (1.8, 1.2, 0.0), 0)
build_crate_stack("linen_crates", (0.35, 1.42, 0.0), 12)
build_bin("biohazard_bin", (0.12, 0.48, 0.0), 0)
build_wheelchair("wheelchair", (-1.65, -0.3, 0.0), 25)
build_xray_machine("xray_machine", (-1.8, -1.25, 0.0), 0)
build_stool("surgeon_stool", (1.78, -0.82, 0.0), 0)
build_caution_sign("caution_sign_ward", (-1.15, 0.02, 0.0), 0)
build_caution_sign("caution_sign_mid", (0.2, -0.53, 0.0), 0)

# IV drip stand by the hospital bed
d = w.decor("iv_stand", pos=(-1.45, 1.44, 0.0))
o = rw.mesh_lathe([(0.0, 0.0), (0.05, 0.0), (0.05, 0.012), (0.012, 0.02), (0.006, 0.38), (0.02, 0.40), (0.006, 0.42), (0.0, 0.42)])
part(d, o, m_steel, False)
o = rw.mesh_cylinder(0.003, 0.06, axis="x"); rw.move(o, pos=(0.03, 0, 0.40)); part(d, o, m_steel, False)
o = rw.mesh_box((0.05, 0.025, 0.09), bevel=0.008); rw.move(o, pos=(0.05, 0, 0.345)); part(d, o, m_bag, False)

# surgical lamp over the operating table
d = w.decor("surgical_lamp", pos=(0.12, -1.15, 0.0))
o = rw.mesh_lathe([(0.0, 0.0), (0.04, 0.0), (0.04, 0.012), (0.008, 0.02), (0.008, 0.58), (0.0, 0.58)])
part(d, o, m_steel, False)
o = rw.mesh_box((0.30, 0.05, 0.04), bevel=0.008); rw.move(o, pos=(0.17, 0, 0.58)); part(d, o, m_steel, False)
o = rw.mesh_lathe([(0.0, 0.02), (0.10, 0.02), (0.10, 0.05), (0.04, 0.10), (0.0, 0.10)]); rw.move(o, pos=(0.32, 0, 0.46))
part(d, o, m_white, False)
o = rw.mesh_cylinder(0.07, 0.005); rw.move(o, pos=(0.32, 0, 0.482)); part(d, o, m_light, False)

# red cross sign over the reception end
d = w.decor("red_cross_sign", pos=(-1.98, 0.0, 0.0))
o = rw.mesh_box((0.02, 0.26, 0.26), bevel=0.01); rw.move(o, pos=(0, 0, 0.32)); part(d, o, m_white, False)
o = rw.mesh_box((0.012, 0.07, 0.20)); rw.move(o, pos=(0.014, 0, 0.32)); part(d, o, m_red, False)
o = rw.mesh_box((0.012, 0.20, 0.07)); rw.move(o, pos=(0.014, 0, 0.32)); part(d, o, m_red, False)

# fire extinguisher by the corridor wall
d = w.decor("fire_extinguisher", pos=(0.72, 0.52, 0.0))
o = rw.mesh_lathe([(0.0, 0.0), (0.035, 0.0), (0.042, 0.02), (0.042, 0.13), (0.025, 0.155), (0.012, 0.165), (0.012, 0.18), (0.0, 0.18)])
part(d, o, m_red, False)
o = rw.mesh_cylinder(0.006, 0.05, axis="x"); rw.move(o, pos=(0.035, 0, 0.175)); part(d, o, m_black, False)

# bright ceiling light panels
for k, xx in enumerate((-1.2, 0.2, 1.5)):
    d = w.decor("ceiling_light_%d" % k, pos=(xx, 0.0, 0.0))
    o = rw.mesh_box((0.5, 0.25, 0.02), bevel=0.005); rw.move(o, pos=(0, 0, 1.15)); part(d, o, m_light, False)
    o = rw.mesh_box((0.54, 0.29, 0.015), bevel=0.004); rw.move(o, pos=(0, 0, 1.165)); part(d, o, m_steel, False)

# free object to shove: a small white supply crate
w.crate("supply_crate", pos=(0.65, 0.0), size=(0.10, 0.10, 0.08), mass=0.05, material=m_white)

# ---------------- tasks ----------------
w.task_goto("wet_round_to_reception", goal="reception", start=(1.3, -0.15, 180), avoid=["disinfectant_spill"],
            instruction="Walk the length of the corridor to the red rug under the big red cross at reception. "
                        "The shiny blue patches are freshly mopped and very slippery, and don't step in the green spill.",
            paraphrases=["Head west down the corridor to the red rug at reception, careful on the wet floor.",
                         "Go to the red-cross end of the corridor and stop on the red rug, avoiding the green spill."])

w.task_goto("xray_appointment", goal="xray_bay", start=(-0.95, -0.15, 180), avoid=["disinfectant_spill"],
            instruction="Go through the open doorway across the corridor into the X-ray room, walk up the blue ramp "
                        "onto the white platform and stand in the purple ring for your scan.",
            paraphrases=["Cross the corridor to the X-ray room and step up onto the scanner platform.",
                         "Enter the X-ray room, climb the little blue ramp and wait in the purple ring."])

w.task_gate("restock_supply_room", plate="supply_plate", goal="supply_room", start=(-0.6, 0.3, 0), avoid=["disinfectant_spill"],
            instruction="Step on the blue floor pad by the glass sliding door to open the supply room, then go inside "
                        "and stop on the yellow mat.",
            paraphrases=["Press the blue pad to slide open the supply-room door, then walk in to the yellow mat.",
                         "Open the supply room with the blue floor pad and stop on the yellow mat inside."])

w.task_gate("scrub_in", plate="theatre_plate", goal="operating_theatre", start=(-1.2, -0.32, 0), avoid=["disinfectant_spill"],
            instruction="Step on the green floor pad to open the operating theatre's sliding door, then go in and stand "
                        "on the white mat by the operating table.",
            paraphrases=["Press the green pad, wait for the glass door to rise, and go into the theatre.",
                         "Open the theatre door with the green floor pad and stop on the white mat inside."])

w.task_push("deliver_supplies", object="supply_crate", goal="delivery_spot", start=(0.3, 0.0, 0), avoid=["disinfectant_spill"],
            instruction="Push the little white supply crate along the corridor into the green circle at the nurse's station desk.",
            paraphrases=["Shove the white box down the corridor to the green ring by the desk.",
                         "Deliver the supply crate: push it into the green circle at the nurse's station."])

w.task_visit("nurse_rounds", goals=["ward_a", "xray_bay", "reception"], start=(1.2, 0.0, 180), avoid=["disinfectant_spill"],
             instruction="Do your rounds: first the blue rug by the hospital bed in the ward, then up the ramp onto the "
                         "X-ray platform, and finish on the red rug at reception.",
             paraphrases=["Check the ward, then the X-ray bay, then reception, in that order.",
                          "Make your rounds: the bed's blue rug, the purple scanner ring, then the red rug at the front."])
