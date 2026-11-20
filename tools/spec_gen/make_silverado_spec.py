"""spec for the AC Highway Outlaws '87 Silverado (chevy_silverado_1987_lowboost, 'Texas Speed 87' Silverado') on the game's
Ranch pickup (Pickup_02) so the bed works: MTVehicleCargoSpace resized to the Silverado bed, the tailgate cut out of the
body into the base's Tailgate door mesh (hinge socket DoorHinge_Tailgate_01 at its bottom edge).
Frames: geo/*.dae = x fwd, y LEFT, z up (cm, ground ~0); spec boxes/sockets are Motor Town (y right) unless noted |y|.
AC: TOTALMASS 2850 kg, RWD, 4 gears 3.54/2.59/2.10/1.61 R-2.07 FINAL 2.00, LIMITER 8000, power.lut NA 548 Nm @5000,
TURBO_0 + TURBO_1 MAX_BOOST 1.59 each (x4.18)."""
import json, math, re
ROOT = r"C:/Users/noust/OneDrive/Documents/claude/ps2motortown/"
SRC = r"C:/Users/noust/nfs-work/ac/silverado/"
T = "Tex_AC_SV_"
inv = json.load(open(SRC + "inventory.json"))
special = {"BODY": "Paint", "vrido": "Glass", "parachoques": "Trim", "grade": "Trim", "R2": "Trim", "EXT_RRimChrome": "Trim",
           "ac_Material #267": "Trim", "R3": "Bottom", "ac_Material #131": "Bottom", "EXT_RRimBlack": "Bottom", "muffler": "Bottom",
           "ac_Material #39": "Bottom", "ac_Material #25": "Bottom", "carbon": T + "CARBON"}
slots, src = {}, {T + "CARBON": "SILV_CARBON.png"}   # carbon door etc.: AC colour comes from a tiled detail map -> plain dark carbon
for m in inv["materials"]:
    n, tex = m["name"], m["tex"].get("txDiffuse", "")
    if n in special:
        slots[n] = special[n]; continue
    s = T + re.sub(r"[^A-Za-z0-9]", "", tex.rsplit(".", 1)[0]).upper()[:22]
    slots[n] = s; src[s] = tex
PAL, LUZ, FAR, DASH = slots["shine"], slots["lanterna"], slots["farois"], slots["ac_Material #149"]
assert slots["opaqe"] == PAL   # both sample the same colour-palette picture (EDITARCORES)
# hubs from the wheel meshes (dae frame, y left); offset moves each wheel to its own hub (MT frame)
hub = {"LF": (185.03, 83.2, 36.34), "RF": (187.49, -83.19, 36.34), "LR": (-149.23, 87.28, 36.34), "RR": (-146.56, -87.28, 36.34)}   # wheel bbox centres
off = lambda h: [round(-h[0], 2), round(h[1], 2), round(-h[2], 2)]
# fronts +2 in diameter (user: "a couple inches bigger to look proportionate"): 62.7 -> 67.8 cm, width kept
FRONT_UP = 1.08
wheel = lambda key: {"parts": [dict({"part": "WHEEL_" + key, "offset": off(hub[key])},
                                    **({"scale": [FRONT_UP, 1, FRONT_UP]} if key in ("LF", "RF") else {}))],
                     **({"reduce": 0.3} if key in ("LF", "RF") else {})}   # rears unreduced: the 30% LOD left the drag radial out of round (user)
TG = [-290, 0, 66, -272, 85.5, 103]      # tailgate panel |y| box (rear view + depth histogram): above the bumper, inside the lamps
TGP = ("022-0-22-44", "011-0-11-22", "007-0-7-14", "025-0-25-50", "026-0-26-52")
HEAD, TAIL, SIDEF = "HeadSV", "TailSV", "SideSV"
body_parts = [({"part": p, "skip_boxes": [TG]} if p in TGP else p) for p in (
    "022-0-22-44", "011-0-11-22", "007-0-7-14", "025-0-25-50", "026-0-26-52",
    "000-0-0-0", "003-0-3-6", "008-0-8-16", "010-0-10-20", "012-0-12-24", "013-0-13-25", "015-0-15-30", "016-0-16-32",
    "017-0-17-34", "018-0-18-36", "019-0-19-38", "024-0-24-48", "OBJECT004", "OBJECT013", "OBJECT021",
    "LINE001", "LINE002", "PIPECAP",   # PIPECAP: tools/spec_gen/make_silverado_pipecap.py (dark caps in the side pipes)
    "SUSP_LF", "SUSP_RF", "SUSP_LR", "SUSP_RR", "STEER_HR",
    "OLEO", "BATERIA", "PLANE001", "PLANE002",          # oil / volts dials keep their own static needles
    "SCION_DRAG_BOOT_LODA_SUB0", "SCION_DRAG_BOOT_LODA_SUB1", "SHOOT_SRTAPS", "OBJECT213", "EXTRA_1_SUB5")] + [
    {"part": "OBJECT010", "slot": "Gauges"}, {"part": "OBJECT011", "slot": "Gauges"},
    {"part": "009-0-9-18", "slot": HEAD}, {"part": "OBJECT012", "slot": HEAD}, {"part": "OBJECT020", "slot": HEAD},
    {"part": "004-0-4-8", "slot": SIDEF}, {"part": "OBJECT014", "slot": SIDEF},
    {"part": "OBJECT001", "slot": TAIL}, {"part": "OBJECT002", "slot": TAIL}, {"part": "OBJECT015", "slot": TAIL},
    {"part": "OBJECT016", "slot": TAIL}, {"part": "OBJECT017", "slot": TAIL}, {"part": "OBJECT018", "slot": TAIL},
    {"part": "OBJECT019", "slot": TAIL}, {"part": "OBJECT005", "slot": TAIL}]
# left out: PLANE003 (carbon tonneau over the bed: the bed has to carry cargo, user 2026-11-18), RPM / VELOCIDADE / GASOLA /
# AGUA / TURBO (AC needles: the game's needles turn on the redrawn dials)
tailgate_parts = [{"part": p, "only_boxes": [TG]} for p in TGP]
eye = (25.0, -49.0, 140.0)    # bench cushion top z ~75 (x 20..60): seat = cushion - 16, eye = seat + 81 (the Ranch's own seat->eye)
mir = (68.0, -2.0, 150.0)     # under the windscreen header
d = [m - e for m, e in zip(mir, eye)]; dl = math.sqrt(sum(x * x for x in d)); d = [x / dl for x in d]
r = [-1.0, 0.0, 0.02]; rl = math.sqrt(sum(x * x for x in r)); r = [x / rl for x in r]
n = [a - b for a, b in zip(r, d)]; nl = math.sqrt(sum(x * x for x in n)); X = [-x / nl for x in n]
myaw = math.degrees(math.atan2(X[1], X[0])); mpitch = math.degrees(math.asin(X[2]))
# needle sockets: AC needle pivots (kn5 dummies, z -13.4 to the dae frame) 0.4 cm proud of the dial faces
MAIN_N, SIDE_N = (-0.957, 0.015, 0.289), (-0.905, 0.381, 0.19)       # face normals (MT frame)
sock = lambda p, nn: [round(p[0] + 0.4 * nn[0], 2), round(-p[1] + 0.4 * nn[1], 2), round(p[2] + 0.4 * nn[2], 2)]
rot_main = [0, -90, round(-90 + math.degrees(math.asin(MAIN_N[2])), 1)]
# socket Z = into the face: (-a sin yaw, a cos yaw, -sin tilt) = -SIDE_N -> yaw -112.7 (yaw -90 = facing straight back)
rot_side = [0, round(math.degrees(math.atan2(SIDE_N[0], -SIDE_N[1])), 1), round(-90 + math.degrees(math.asin(SIDE_N[2])), 1)]
spec = {
    "car": "AC_SILVERADO", "display_name": "Chevrolet Silverado 1987 'Texas Speed' (Highway Outlaws)", "prefix": "AC_SILVERADO",
    "base_vehicle": "Ranch", "drivetrain": "rwd",   # real car is RWD; the base is 4WD/AWD
    "base_dir": "Pickup_02", "base_row": "Pickup_02", "base_wheel": "RanchPickup",
    "base_wheel_mesh": "RanchPickup", "default_slot": "Bottom", "source_scale": 100.0,
    "geometry_dir": SRC + "geo", "texture_dir": SRC + "textures",
    "out_dir": "C:/Users/noust/mt-work/build/AC_SILVERADO/meshes", "cost": 60000, "wheel_part": True,
    "wheel_display_name": "Weld Drag Wheels (Silverado)",
    "texture_slots": slots, "texture_sources": src,
    "meshes": {
        "Body": {"parts": body_parts, "reduce": 0.4,
                 "drop_boxes": [[60, -12, 140, 80, 8, 158]],     # nothing there yet; keeps the game RoomMirror spot clear
                 "drop_note": "boxes in MT frame (y right)"},
        "Tailgate": {"parts": tailgate_parts, "reduce": 0.4,
                     "note": "Ranch Tailgate door (Van_RearSwingDoor -90 deg about the mesh socket DoorHinge_Tailgate_01)"},
        "Wheel_L": wheel("LF"), "Wheel_R": wheel("RF"), "Wheel_RL": wheel("LR"), "Wheel_RR": wheel("RR")},
    "rear_wheel_meshes": True, "rear_wheel_part": True, "wheel_align": True,   # AC wheels carry 0.6 deg camber/toe -> wobbled in game
    "mesh_names": {"Wheel_L": "AC_SILVERADO_L", "Wheel_R": "AC_SILVERADO_R", "Wheel_RL": "AC_SILVERADO_REAR_L",
                   "Wheel_RR": "AC_SILVERADO_REAR_R", "SteeringWheel": "AC_SILVERADO"},
    "final_slot_names": {"Paint": "Body_0", "Glass": "Window", HEAD: "HeadLight", TAIL: "TailLight", slots["blackcasamba"]: "CargoBed",
                         "Signal_L_F": "LeftSignalLight", "Signal_R_F": "RightSignalLight",
                         "Signal_L_R": "LeftTailLight", "Signal_R_R": "RightTailLight",
                         "Signal_L_V": "ReverseLight", "Signal_R_V": "ReverseLight"},
    "wheels": {"front_x": 186.2, "rear_x": -147.9, "half_track": 82.5, "rear_half_track": 87.5, "z": 35.0, "rear_z": 35.5,
               "radius": 31.5, "auto_arches": False,
               "note": "AC hubs (wheelbase 334 = long bed); front r 31.5, rear drag radial r 35.5"},
    "collision_boxes": [{"center": [-5, 0, 41.5], "size": [575, 205, 27]},          # floor / chassis z 28..55
                        {"center": [131.5, 0, 82.5], "size": [279, 205, 55]},       # nose + cab lower to z 110
                        {"center": [55, 0, 136], "size": [140, 180, 52]},           # cab z 110..162
                        {"center": [-145, -94, 83.5], "size": [274, 20, 57]},       # bed sides (open bed between)
                        {"center": [-145, 94, 83.5], "size": [274, 20, 57]}],
    "sockets": {"Body": [{"name": "Exhaust", "loc": [242, 113, 68], "rot": [0, 90, 90]},     # front side pipes (LINE001/002)
                         {"name": "Winch0", "loc": [272, 0, 55], "rot": [0, 0, 0]},
                         {"name": "TrailerHitch", "loc": [-297, 0, 48], "rot": [0, 0, 0]}],
                "Tailgate": [{"name": "DoorHinge_Tailgate_01", "loc": [-279, 0, 66.5], "rot": [0, 0, -90]}]},
    "blueprint": {
        "seats": {"DriverSeat_GEN_VARIABLE": [27, -49, 59], "PassengerSeat1_GEN_VARIABLE": [27, 49, 59]},
        "cockpit_camera": list(eye),
        "components": {"RoomMirror_GEN_VARIABLE": list(mir), "FrontDomeLightSlot_GEN_VARIABLE": [20, 0, 158],
                       "HeadLight_Left_GEN_VARIABLE": [258, -69, 72], "HeadLight_Right_GEN_VARIABLE": [258, 69, 72],
                       "BlinkerLight_01_GEN_VARIABLE": [245, 97, 54], "BlinkerLight_02_GEN_VARIABLE": [245, -97, 54],
                       "TaliLight_01_GEN_VARIABLE": [-283, -94, 88], "TaliLight_02_GEN_VARIABLE": [-283, 94, 88],
                       "ReverseLight_01_GEN_VARIABLE": [-283, -94, 79], "ReverseLight_02_GEN_VARIABLE": [-283, 94, 79],
                       # no mirrors in the AC model: the Ranch's own (Bus) mirrors on the door tops, aimed from this eye
                       "LeftSideMirror_GEN_VARIABLE": [95, -106, 126], "RightSideMirror_GEN_VARIABLE": [95, 106, 126],
                       # bed: inside x -272..-10, |y| < 84, floor z 55 (Ranch box: extent 100, scale 1.248/0.858/0.661)
                       "MTVehicleCargoSpace_GEN_VARIABLE": [-141, 0, 121.1]},
        "component_scales": {"MTVehicleCargoSpace_GEN_VARIABLE": [1.31, 0.84, 0.661]},
        "component_rotations": {"RoomMirror_GEN_VARIABLE": [round(mpitch, 1), round(myaw, 1), 0],
                                "LeftSideMirror_GEN_VARIABLE": [-4.5, -16.7, -0.3], "RightSideMirror_GEN_VARIABLE": [-0.8, 30.0, 0]},
        "keep_body_materials": 1, "body_mass": 1650, "room_mirror_aim_z": 0.02},
    "extract": {"SteeringWheel": {"from": "Body", "center": [80.5, -49.1, 103.5], "radius": 22.0, "x_range": [64, 92],
                                  "uv_box": [-99, -99, 99, 99], "uv_slots": [PAL],
                                  "socket": "SteeringWheel", "align_x": True, "reduce": 0.5}},
    "signal_lamps": [{"tag": "_V", "from": TAIL, "box": [-290, -110, 70, -260, 110, 82.5],
                      "note": "real 81-87 C/K: clear reverse inset at the bottom of each corner lamp"},
                     {"tag": "_R", "from": TAIL, "box": [-290, -110, 82.5, -260, -60, 97]},
                     {"tag": "_R", "from": TAIL, "box": [-290, 60, 82.5, -260, 110, 97],
                      "note": "red stop/tail/turn (US: the red lamp flashes); LeftTailLight/RightTailLight light for tail, brake and blink"},
                     {"tag": "_F", "from": SIDEF, "box": [220, -110, 40, 260, 0, 70]},
                     {"tag": "_F", "from": SIDEF, "box": [220, 0, 40, 260, 110, 70]}],
    "lamp_slots": {HEAD: {"kind": "head", "texture_slot": FAR},
                   TAIL: {"kind": "tail", "texture_slot": LUZ},
                   "Signal_L_F": {"kind": "signal", "texture_slot": LUZ}, "Signal_R_F": {"kind": "signal", "texture_slot": LUZ},
                   "Signal_L_R": {"kind": "signal_tail_red", "texture_slot": LUZ}, "Signal_R_R": {"kind": "signal_tail_red", "texture_slot": LUZ},
                   "Signal_L_V": {"kind": "reverse", "texture_slot": LUZ}, "Signal_R_V": {"kind": "reverse", "texture_slot": LUZ}},
    "dashboard": {"attach_none": True, "sockets": [
        {"name": "Niddle_RPM", "loc": sock((99.0, 40.3, 105.7), MAIN_N), "rot": rot_main},
        {"name": "Niddle_Speed", "loc": sock((98.8, 55.5, 105.7), MAIN_N), "rot": rot_main},
        {"name": "Niddle_Fuel", "loc": sock((98.4, 66.7, 110.0), SIDE_N), "rot": rot_side},
        {"name": "Niddle_Temp", "loc": sock((98.2, 66.7, 101.5), SIDE_N), "rot": rot_side}],
        "note": "AC needle pivots RPM / VELOCIDADE / GASOLA / AGUA; side pod faces the driver (yaw -112.7)"},
    "gauge_style": {"face_color": [6, 6, 7], "ink": [235, 235, 235], "minor_ink": [200, 200, 200], "red_color": [225, 30, 25],
                    "font_file": "arialbd.ttf"},
    "gauge_faces": {DASH: [
        {"center": [0.354, 0.235], "face": [0.354, 0.235, 0.215], "radius": 0.18, "rotate": 0, "min": 0, "max": 120,
         "text_step": 20, "line_step": 10, "start": 140, "end": 400, "font": 0.13, "captions": [["MPH", 0.32, 90]],
         "caption_font": 0.09, "note": "stock 81-87 C/K 0-120 mph speedo, redrawn on the game's needle sweep"},
        {"center": [0.8065, 0.5908], "face": [0.8065, 0.5908, 0.19], "radius": 0.16, "rotate": 0, "min": 0, "max": 8,
         "text_step": 1, "line_step": 0.5, "start": 140, "end": 400, "red_from": 7.5, "font": 0.15,
         "captions": [["RPM x1000", 0.32, 90]], "caption_font": 0.08, "note": "AC art 0-7k; limiter 8000"},
        {"center": [0.8258, 0.0877], "face": [0.8258, 0.0877, 0.06], "radius": 0.05, "rotate": 0, "min": 0, "max": 1, "text_step": 1,
         "line_step": 0.25, "start": 210, "end": 330, "font": 0.3, "labels": {"0": "E", "1": "F"}},
        {"center": [0.944, 0.1894], "face": [0.944, 0.1894, 0.05], "radius": 0.042, "rotate": 0, "min": 40, "max": 120, "text_step": 80,
         "line_step": 20, "start": 210, "end": 330, "font": 0.3, "labels": {"40": "C", "120": "H"}, "red_from": 110}]},
    "gauge_ranges": {"RPM": {"max": 8}, "Speed": {"max": 120, "value_scale": 1.609344}},
    "needle_color": [240, 90, 20], "needle_width": 0.3,
    "emissive_slots": {"Gauges": {"texture_slot": DASH, "glow": 2.0}},
    "masked_texture_slots": [slots["ac_Material #111"]],
    "mirror_check": {"base_side_mirrors": ["LeftSideMirror_GEN_VARIABLE", "RightSideMirror_GEN_VARIABLE"]},
    "skins": {"dir": SRC + "textures", "pick": [], "baked": {
        "Texas Speed Teal (stock)": SRC + "textures/SILV_SKIN_teal.png", "Two-Tone Red": SRC + "textures/SILV_SKIN_red.png",
        "Two-Tone Black": SRC + "textures/SILV_SKIN_black.png", "Two-Tone Green": SRC + "textures/SILV_SKIN_green.png"}},
    "performance_source": "AC data: TOTALMASS 2850 (ui 1324 kg), RWD, 4 gears 3.54/2.59/2.10/1.61 R-2.07 FINAL 2.00, LIMITER 8000, MINIMUM 1000; power.lut NA 548 Nm @5000; TURBO_0+TURBO_1 MAX_BOOST 1.59 each (x4.18 = 2290 Nm; ui 2168 bhp / 2546 Nm)",
    "custom_parts": {
        "transmissions": [{"row": "AC_SILVERADO_4SPD", "base_row": "6SpeedSportsLP670", "asset": "AC_SILVERADO_4SPD",
                           "base_asset": "Cars/Parts/Transmission/Manual6SpeedSports_LP670", "display_name": "4-Speed Drag (Silverado)",
                           "cost": 6000, "mass": 90,
                           "ratios": {g: round(v * 2.00 / 3.31, 3) for g, v in
                                      {"R": -2.07, "1": 3.54, "2": 2.59, "3": 2.10, "4": 1.61}.items()},
                           "note": "AC final 2.00 folded in (game row FD_3.31): ratio x 2.00/3.31"}],
        "engines": []},
    "part_overrides": {"Engine": "AC_SILVERADO_V8_TT", "Transmission": "AC_SILVERADO_4SPD", "FinalDriveRatio": "FD_3.31",
                       "CoolantRadiator": "SmallRadiator_110",
                       "Tire0": "PerformanceTire_46", "Tire1": "PerformanceTire_46",
                       "Tire2": "PerformanceDragTireStrip", "Tire3": "PerformanceDragTireStrip",
                       "Wheel0": "AC_SILVERADO", "Wheel1": "AC_SILVERADO", "Wheel2": "AC_SILVERADO_REAR", "Wheel3": "AC_SILVERADO_REAR",
                       "BrakePad0": "BrakePad_Small_02", "BrakePad1": "BrakePad_Small_02", "BrakePad2": "BrakePad_Small_02", "BrakePad3": "BrakePad_Small_02"},
    "drivetrain_note": "Ranch is RWD (AC: RWD). Street fronts, drag radials at the rear like the AC truck.",
}
# MATCH the mod's rated output (user rule: never scale): ui_car.json torqueCurve already includes both turbos
# (2168 bhp / 2546 Nm), so the curve carries the boost and no boost part is fitted.
_ui = json.load(open(r"C:/Users/noust/nfs-work/ac/highway_outlaws/Highway Outlaws Official/content/cars/chevy_silverado_1987_lowboost/ui/ui_car.json", encoding="utf-8-sig"))
lut = [(float(a), float(b)) for a, b in _ui["torqueCurve"] if 500 <= float(a) < 8000] + [(8000, 172)]
mx, lim = max(t for _, t in lut), 8000
curve = [[round(rr / lim, 4), round(t / mx, 4)] for rr, t in lut] + [[5.0, 0.05]]
_hp = max(rr * t / 7121 for rr, t in lut)   # metric hp; bhp = rpm*Nm/7127
print("engine: peak %.0f Nm, peak %.0f hp (target 2546 Nm / 2168 bhp)" % (mx, _hp))
spec["custom_parts"]["engines"].append({
    "row": "AC_SILVERADO_V8_TT", "base_row": "SmallBlock_320HP", "asset": "AC_SILVERADO_V8_TT", "base_asset": "Cars/Parts/Engine/S58",
    "display_name": "Twin-Turbo V8 (Texas Speed Silverado)", "mass": 250, "cost": 60000, "max_torque_nm": mx, "max_rpm": lim,
    "curve": curve, "curve_note": "ui_car.json torqueCurve, boost included (2546 Nm / 2168 bhp); no boost part",
    "physics_from": "Cars/Parts/Engine/FordSmalBlock302_V8_5L_320HP", "idle_throttle": 0.0009,
    "sound_cue": {"cue_base": "Cars/Parts/Engine/Sound/s58/SC_V8Engine", "dir": "AC_SILVERADO",
                  "loops": [["l1", 817], ["l2", 1635], ["l3", 2886], ["l4", 4360], ["l5", 6823]],
                  "note": "the car's own bank lm_chevy_silverado_1987.bank (vgmstream): ext_idle817, ext_1635a, 2886a, 4360a, 6823a (rpm in the names)"}})
json.dump(spec, open(ROOT + "cars/ac_silverado.json", "w"), indent=1)
print("room mirror rot", round(mpitch, 1), round(myaw, 1), "sockets", [s["loc"] for s in spec["dashboard"]["sockets"]], rot_main, rot_side)
print("slots", sorted(set(slots.values())))
