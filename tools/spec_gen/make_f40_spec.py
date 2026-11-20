"""spec for the SRP pack's slang_ferrari_f40 (AC; customised F40: LM-style splitter/diffuser/wing, BBS wheels, factory turbo
tune) on the Raton (mid-engine base, as the Diablo). Frames: geo/*.dae = x fwd, y LEFT, z up (cm); kn5 dummies + 2.9 z
= dae. Spec boxes/sockets are Motor Town (y right) unless noted |y|. data.acd is left packed (AC's encrypted data):
performance from ui_car.json (681 Nm @4000, 567 bhp @7500, 1175 kg) + real F40 gearing (FerrariChat: 2.77/1.71/1.23/
0.96/0.77, final 10/29 = 2.9; reverse not published -> 2.50)."""
import json, math, re, os
import numpy as np
from PIL import Image
ROOT = r"C:/Users/noust/OneDrive/Documents/claude/ps2motortown/"
SRC = r"C:/Users/noust/nfs-work/ac/f40/"
T = "Tex_AC_F40_"
inv = json.load(open(SRC + "inventory.json"))
special = {"carPaint": "Paint", "EXT_Glass": "Glass", "INT_Glass": "Glass", "EXT_Glass_Black": "Glass"}
REAL = {"Seats_Leather": (118, 16, 16),
        "EXT_Plastic": (14, 14, 14)}   # lamp surrounds / rear panel: black (NULL detail baked white = white rings, user 2026-11-19)     # real F40: red cloth buckets (the mod's detail map is grey)
slots, src = {}, {}
DETAIL_ART = ("BADGING", "ext_plate_front", "ext_plate_rear", "Ferrari_Badges_009", "INT_Pedali_NM")
def tex_stats(f):
    a = np.asarray(Image.open(SRC + "textures/" + f).convert("RGBA").resize((64, 64)), dtype=np.float32)
    return a[..., :3].mean((0, 1)), a[..., 3].mean() / 255.0
for m in inv["materials"]:
    n, tx = m["name"], m["tex"]
    dif, det = tx.get("txDiffuse", ""), tx.get("txDetail", "")
    if n in special:
        slots[n] = special[n]; continue
    tag = re.sub(r"[^A-Za-z0-9]", "", n).upper()[:22]
    if n in DETAIL_ART and det:      # the art itself is the detail map (badges, plates): use it as the texture
        slots[n] = T + tag; src[T + tag] = det; continue
    if "MultiMap" in m["shader"] and det and os.path.exists(SRC + "textures/" + det) and os.path.exists(SRC + "textures/" + dif):
        drgb, dal = tex_stats(dif)
        if dal < 0.3 or drgb.mean() < 6 or n in REAL:
            # AC multimap with a transparent / black diffuse: the colour is the detail map (tiled) -> bake its mean colour,
            # times the diffuse's AO when it has one (Unicorn lesson: rims/interior came out white or untextured)
            col = np.array(REAL.get(n, tex_stats(det)[0]), np.float32)
            a = np.asarray(Image.open(SRC + "textures/" + dif).convert("L"), dtype=np.float32)
            if a.mean() > 6:
                a = a / max(1.0, a[a > 8].mean() if (a > 8).any() else a.mean())
                img = Image.fromarray(np.clip(a[..., None] * col, 0, 255).astype(np.uint8), "RGB")
            else:
                img = Image.new("RGB", (8, 8), tuple(int(c) for c in col))
            out = "F40BAKE_%s.png" % tag
            img.save(SRC + "textures/" + out)
            slots[n] = T + tag; src[T + tag] = out
            continue
    s = T + re.sub(r"[^A-Za-z0-9]", "", dif.rsplit(".", 1)[0]).upper()[:22]
    slots[n] = s; src[s] = dif
# solid white for the throttle body (user 2026-11-19: "pure white and blocked off"); used by INTAKEJOIN's cap too
Image.new("RGB", (8, 8), (235, 235, 235)).save(SRC + "textures/F40_WHITE.png")
slots["F40_WHITE"] = T + "WHITE"; src[T + "WHITE"] = "F40_WHITE.png"
# hubs (dae frame, y left) from the tyre bounds; wheel offset = (-x, +y, -z) in MT frame
hub = {"LF": (115.3, 81.7, 34.4), "RF": (115.1, -81.7, 34.4), "LR": (-132.7, 81.6, 34.4), "RR": (-132.9, -81.6, 34.4)}
off = lambda h: [round(-h[0], 2), round(h[1], 2), round(-h[2], 2)]
wheel = lambda k: {"parts": [{"part": "WHEEL_" + k, "offset": off(hub[k])}, {"part": "DISC_" + k, "offset": off(hub[k])}], "reduce": 0.3}
HEADF, SIGF, TAIL, REV, SIGR, POD = "HeadF40", "SigF40F", "TailF40", "RevF40", "SigF40R", "HeadPod"
g = lambda part, groups, **k: dict({"part": part, "groups": groups}, **k)
chassis = [i for i in range(36) if i not in (7, 21)]
TB = [-158, 0, 68, -138, 7.5, 84]   # throttle-body tube (CHASSIS 35, |y|) -> white; tools/spec_gen/make_f40_intake.py joins it to the duct
rear = [i for i in range(29) if i not in (1, 11, 14, 16, 17, 18, 20)]          # 1 = INT_Glass duplicate of the rear screen
frunk_plain = [0, 3, 4, 5, 13, 14, 15, 16]                                   # defrost, reflectors (lit through the glass)
cockpit = [i for i in range(52) if i not in (5, 7, 8, 14, 32, 34) and not 45 <= i <= 51]   # 45-51 = the 7 static AC needles (white "painted" needles, user 2026-11-19)
NEEDLE_SKIP = [[59, 9.5, 64, 64.5, 16.2, 72], [63, 39, 69, 70, 46.5, 76.5]]   # AC fuel + water needles (|y|); oil/oil-press/turbo stay
body_parts = [g("CHASSIS", [i for i in chassis if i != 35]), g("CHASSIS", [35], skip_boxes=[TB]),
              g("CHASSIS", [35], only_boxes=[TB], slot=T + "WHITE"), "INTAKEJOIN", g("REAR_CAWL", rear), g("FRUNK", frunk_plain),
              g("DOOR_LEFT", [0, 1, 2, 3, 4, 5, 6, 8, 9]),
              g("DOOR_LEFT", [7], normal_filter={"axis": 0, "min": -0.75}, slot="Paint"),     # mirror housings (body colour)
              g("CHASSIS", [21], normal_filter={"axis": 0, "min": -0.75}, slot="Paint"),
              g("COCKPIT_HR", cockpit), g("COCKPIT_HR", [7], skip_boxes=NEEDLE_SKIP),
              "EXT_GLASS_CHASSIS", "WIPER", "F_PLATE", "SUSP_LF", "SUSP_RF", "SUSP_LR", "SUSP_RR", "STEER_HR",
              # lamps: glass layers glow, reflectors stay plain behind them
              g("FRUNK", [2], slot=HEADF), g("FRUNK", [1, 6, 17, 18], slot=SIGF),
              g("REAR_CAWL", [11, 14, 20], slot=TAIL), g("CHASSIS", [7], slot=TAIL), g("REAR_CAWL", [17], slot=REV),
              g("REAR_CAWL", [16, 18], slot=SIGR)]
eye = (-5.0, -30.6, 93.0)      # cushion top z 34: F40 sits low and reclined; 93 keeps the right mirror clear of the door frame (96: 15% hidden)
mir = (22.0, 0.0, 102.0)       # where the AC rear-view mirror glass was (dropped: game RoomMirror)
d = [m - e for m, e in zip(mir, eye)]; dl = math.sqrt(sum(x * x for x in d)); d = [x / dl for x in d]
r = [-1.0, 0.0, 0.02]; rl = math.sqrt(sum(x * x for x in r)); r = [x / rl for x in r]
n = [a - b for a, b in zip(r, d)]; nl = math.sqrt(sum(x * x for x in n)); X = [-x / nl for x in n]
myaw = math.degrees(math.atan2(X[1], X[0])); mpitch = math.degrees(math.asin(X[2]))
MAIN_N, SMALL_N = (-0.953, 0.0, 0.303), (-1.0, 0.0, -0.02)
sock = lambda p, nn: [round(p[0] + 0.4 * nn[0], 2), round(-p[1] + 0.4 * nn[1], 2), round(p[2] + 0.4 * nn[2], 2)]
rot = lambda nn: [0, -90, round(-90 + math.degrees(math.asin(nn[2])), 1)]
GA = slots["Gauges"]
spec = {
    "car": "AC_F40", "display_name": "Ferrari F40 (SRP, LM-style)", "prefix": "AC_F40",
    "base_vehicle": "Raton", "drivetrain": "rwd", "wheel_align": True,   # AC wheels carry ~0.8 deg static camber (sway when spun)
      # real car is RWD; the base is 4WD/AWD
    "base_row": "Sports_01", "base_wheel": "Vista", "default_slot": "Bottom", "source_scale": 100.0,
    "geometry_dir": SRC + "geo", "texture_dir": SRC + "textures",
    "out_dir": "C:/Users/noust/mt-work/build/AC_F40/meshes", "cost": 400000, "wheel_part": True,
    "wheel_display_name": "BBS Wheels (F40)",
    "texture_slots": slots, "texture_sources": src,
    "meshes": {
        "Body": {"parts": body_parts},   # no LOD0 reduction: it collapsed the round shift knob (user 2026-11-19) and small parts
        "Popup": {"parts": [g("FRUNK", [8, 10, 11, 12]), g("FRUNK", [7, 9], slot=POD)],
                  "note": "F40 pop-up pods (closed in the model); lights.ksanim Head_Lights: 35 deg about the hinge (x 146.9, z 67.5)"},
        "SideMirror_Left": {"parts": [g("DOOR_LEFT", [7], slot="Mirror", normal_filter={"axis": 0, "max": -0.75})],
                            "planar_uv": {}, "recenter": True},
        "SideMirror_Right": {"parts": [g("CHASSIS", [21], slot="Mirror", normal_filter={"axis": 0, "max": -0.75})],
                             "planar_uv": {"flip_u": True}, "recenter": True},
        "Wheel_L": wheel("LF"), "Wheel_R": wheel("RF"), "Wheel_RL": wheel("LR"), "Wheel_RR": wheel("RR")},
    "mirror_components": {"LeftSideMirror_GEN_VARIABLE": "SideMirror_Left", "RightSideMirror_GEN_VARIABLE": "SideMirror_Right"},
    "rear_wheel_meshes": True, "rear_wheel_part": True,
    "mesh_names": {"Wheel_L": "AC_F40_L", "Wheel_R": "AC_F40_R", "Wheel_RL": "AC_F40_REAR_L", "Wheel_RR": "AC_F40_REAR_R",
                   "SteeringWheel": "AC_F40"},
    "final_slot_names": {"Paint": "Body_0", "Glass": "Glass", HEADF: "HeadLight", POD: "HeadLight", TAIL: "TailLight",
                         REV: "ReverseLight", "Signal_L_F": "LeftSignalLight", "Signal_R_F": "RightSignalLight",
                         "Signal_L_R": "LeftSignalLight", "Signal_R_R": "RightSignalLight"},
    "wheels": {"front_x": 115.2, "rear_x": -132.8, "half_track": 81.7, "rear_half_track": 81.6, "z": 38.2, "rear_z": 39.2,   # -8 cm ride height total (user 2026-11-19: -5 then -3; higher mount = lower body)
               
               "radius": 33.7, "auto_arches": False, "note": "AC hubs (wheelbase 248 = real 2450 mm)"},
    "collision_boxes": [{"center": [5, 0, 40], "size": [440, 198, 50]}, {"center": [-20, 0, 90], "size": [200, 150, 48]}],
    "strip_part_slots": ["Bonnet", "Fender", "LSD0", "LSD1", "SideSkirt"],
    "sockets": {"Body": [{"name": "Exhaust_Left", "loc": [-222, -10, 31], "rot": [0, 180, 0]},
                         {"name": "Exhaust_Right", "loc": [-222, 10, 31], "rot": [0, 180, 0]},
                         {"name": "RearWing", "loc": [-205, 0, 118], "rot": [0, 0, 0], "note": "top of the F40's own wing"},
                         {"name": "TaxiRoofSign", "loc": [-20, 0, 116], "rot": [0, 0, 0]},
                         {"name": "TrailerHitch", "loc": [-222, 0, 22], "rot": [0, 0, 0]}]},
    "blueprint": {
        "seats": {"DriverSeat_GEN_VARIABLE": [-5, -30.6, 12], "PassengerSeat1_GEN_VARIABLE": [-5, 30.6, 12]},
        "cockpit_camera": list(eye),
        "components": {"RoomMirror_GEN_VARIABLE": list(mir), "FrontDomeLightSlot_GEN_VARIABLE": [10, 0, 104],
                       "HeadLight_Left_GEN_VARIABLE": [170, -68, 56], "HeadLight_Right_GEN_VARIABLE": [170, 68, 56],
                       "BlinkerLight_01_GEN_VARIABLE": [192, 72, 47], "BlinkerLight_02_GEN_VARIABLE": [192, -72, 47],
                       "TaliLight_01_GEN_VARIABLE": [-217, -48, 66], "TaliLight_02_GEN_VARIABLE": [-217, 48, 66],
                       "ReverseLight_01_GEN_VARIABLE": [-216, -70, 66], "ReverseLight_02_GEN_VARIABLE": [-216, 70, 66]},
        "component_rotations": {"RoomMirror_GEN_VARIABLE": [round(mpitch, 1), round(myaw, 1), 0]},
        "keep_body_materials": 1, "body_mass": 900, "cdo_names": {"BodyMaterialName": "Body_0"}},
    "extract": {"SteeringWheel": {"from": "Body", "center": [38.3, -30.6, 75.9], "radius": 18.5, "x_range": [26, 50],
                                  "uv_box": [-99, -99, 99, 99], "uv_slots": [slots[k] for k in ("INT_Skins", "INT_Metal_Black", "steer_fer", "Stw_Bolts", "INT_Plastic")],
                                  "socket": "SteeringWheel", "align_x": True, "reduce": 0.5}},
    "signal_lamps": [{"tag": "_F", "from": SIGF, "box": [140, -110, 30, 210, 0, 70]},
                     {"tag": "_F", "from": SIGF, "box": [140, 0, 30, 210, 110, 70]},
                     {"tag": "_R", "from": SIGR, "box": [-230, -110, 40, -200, 0, 90]},
                     {"tag": "_R", "from": SIGR, "box": [-230, 0, 40, -200, 110, 90],
                      "note": "real F40 (EU): outer round rear lamps are the amber turn signals, inner pair stop/tail"}],
    "lamp_slots": {HEADF: {"kind": "head", "texture_slot": slots["Fog_Light_Glass"]},
                   POD: {"kind": "head", "texture_slot": slots["Head_Light_Glass"]},
                   TAIL: {"kind": "tail", "texture_slot": slots["Rear_Light_Glass"]},
                   REV: {"kind": "reverse", "texture_slot": slots["Rear_Light_Glass"]},
                   "Signal_L_F": {"kind": "signal", "texture_slot": slots["Turn_Signal_Glass"]},
                   "Signal_R_F": {"kind": "signal", "texture_slot": slots["Turn_Signal_Glass"]},
                   "Signal_L_R": {"kind": "signal", "texture_slot": slots["Rear_Light_Glass"]},
                   "Signal_R_R": {"kind": "signal", "texture_slot": slots["Rear_Light_Glass"]}},
    "popup": {"hinge": [146.9, 67.5], "angle": 35.0, "seconds": 0.5,
              "note": "lights.ksanim Head_Lights: quaternion z 0.3 = 34.9 deg about the lateral axis through the HEAD_LIGHTS node"},
    "dashboard": {"attach_none": True, "sockets": [
        {"name": "Niddle_RPM", "loc": sock((69.8, 24.6, 77.8), MAIN_N), "rot": rot(MAIN_N)},
        {"name": "Niddle_Speed", "loc": sock((69.8, 35.8, 77.7), MAIN_N), "rot": rot(MAIN_N)},
        {"name": "Niddle_Fuel", "loc": sock((61.8, -12.8, 68.0), SMALL_N), "rot": rot(SMALL_N)},
        {"name": "Niddle_Temp", "loc": sock((66.6, 42.8, 72.8), SMALL_N), "rot": rot(SMALL_N)}],
        "note": "AC ARROW_RPM / SPEED / FUEL (centre console) / WATER pivots; oil, oil-pressure and turbo keep the AC needles"},
    "gauge_style": {"face_color": [8, 8, 9], "ink": [238, 238, 238], "minor_ink": [205, 205, 205], "red_color": [225, 30, 25],
                    "font_file": "arialbd.ttf"},
    "gauge_faces": {GA: [
        {"center": [0.2408, 0.2479], "face": [0.2408, 0.2479, 0.235], "radius": 0.2, "rotate": 0, "min": 0, "max": 220,
         "text_step": 20, "line_step": 10, "start": 140, "end": 400, "font": 0.12, "captions": [["MPH", 0.32, 90]],
         "caption_font": 0.09, "note": "Veglia 0-360 km/h redrawn in mph"},
        {"center": [0.7675, 0.2491], "face": [0.7675, 0.2491, 0.23], "radius": 0.2, "rotate": 0, "min": 0, "max": 10,
         "text_step": 1, "line_step": 0.5, "start": 140, "end": 400, "red_from": 7.75, "font": 0.15,
         "captions": [["RPM x1000", 0.32, 90]], "caption_font": 0.08},
        {"center": [0.5058, 0.675], "face": [0.5058, 0.675, 0.1], "radius": 0.085, "rotate": 0, "min": 0, "max": 1, "text_step": 1,
         "line_step": 0.25, "start": 210, "end": 330, "font": 0.3, "labels": {"0": "E", "1": "F"}},
        {"center": [0.329, 0.9448], "face": [0.329, 0.9448, 0.054], "radius": 0.046, "rotate": 0, "min": 40, "max": 120, "text_step": 80,
         "line_step": 20, "start": 210, "end": 330, "font": 0.3, "labels": {"40": "C", "120": "H"}, "red_from": 110}]},
    "gauge_ranges": {"RPM": {"max": 10}, "Speed": {"max": 220, "value_scale": 1.609344}},
    "needle_color": [240, 120, 20], "needle_width": 0.3,
    "emissive_slots": {"Gauges": {"texture_slot": GA, "glow": 2.0}},
    "masked_texture_slots": [slots[k] for k in ("Holes", "Setrab", "Welding_Seams", "Ridges_002", "INT_Symbols", "Display_Symbols",
                                                 "Zigzag", "Front_Grids", "Lock_003", "Door_Key_Hole", "Bolts", "Ferrari_Badges_009")],
    "performance_source": "ui_car.json (mod tune 'factory boosted'): 681 Nm @4000, 567 bhp @7500, curve to 7850; 1175 kg; real F40 gearing",
    "custom_parts": {
        "transmissions": [{"row": "AC_F40_5MT", "base_row": "6SpeedSportsLP670", "asset": "AC_F40_5MT",
                           "base_asset": "Cars/Parts/Transmission/Manual6SpeedSports_LP670", "display_name": "5-Speed Manual (F40)",
                           "cost": 9000, "mass": 80,
                           "ratios": {k: round(v * 2.9 / 3.31, 3) for k, v in
                                      {"R": -2.5, "1": 2.77, "2": 1.71, "3": 1.23, "4": 0.96, "5": 0.77}.items()},
                           "note": "final 2.9 (10/29) folded in (game row FD_3.31): ratio x 2.9/3.31"}],
        "engines": []},
    "part_overrides": {"Engine": "AC_F40_V8TT", "Transmission": "AC_F40_5MT", "FinalDriveRatio": "FD_3.31",
                       "CoolantRadiator": "SmallRadiator_110", "Tire0": "PerformanceTire_46", "Tire1": "PerformanceTire_46",
                       "Tire2": "PerformanceTire_46", "Tire3": "PerformanceTire_46",
                       "Wheel0": "AC_F40", "Wheel1": "AC_F40", "Wheel2": "AC_F40_REAR", "Wheel3": "AC_F40_REAR",
                       "BrakePad0": "BrakePad_Small_02", "BrakePad1": "BrakePad_Small_02", "BrakePad2": "BrakePad_Small_02",
                       "BrakePad3": "BrakePad_Small_02", "Headlight": "AC_F40_Popup"},
    "drivetrain_note": "Raton: mid-engine RWD (F40: mid-engine RWD).",
}
ui = json.load(open(r"C:/Users/noust/nfs-work/ac/srp_f40_src/content/cars/slang_ferrari_f40/ui/ui_car.json", encoding="utf-8-sig"))
tc = [(float(a), float(b)) for a, b in ui["torqueCurve"] if float(a) >= 500]
mx, lim = max(t for _, t in tc), 7850
curve = [[round(rr / lim, 4), round(t / mx, 4)] for rr, t in tc] + [[5.0, 0.15]]
spec["custom_parts"]["engines"].append({
    "row": "AC_F40_V8TT", "base_row": "SmallBlock_320HP", "asset": "AC_F40_V8TT", "base_asset": "Cars/Parts/Engine/S58",
    "display_name": "2.9 Twin-Turbo V8 (F40)", "mass": 210, "cost": 90000, "max_torque_nm": round(mx), "max_rpm": lim,
    "curve": curve, "curve_note": "ui_car.json torqueCurve (boost included: 681 Nm @4000)",
    "physics_from": "Cars/Parts/Engine/FordSmalBlock302_V8_5L_320HP", "idle_throttle": 0.0009,
    "sound_cue": {"cue_base": "Cars/Parts/Engine/Sound/s58/SC_V8Engine", "dir": "AC_F40", "loops": [["l1", 1155], ["l2", 2200], ["l3", 2900], ["l4", 3600], ["l5", 5000], ["l6", 6400], ["l7", 7600]], "note": "the car's own bank (slang_ferrari_f40.bank): F40_ex_idle / ex_on_verylow / low_2 / mid / high / max_2; all recorded at the idle pitch (77 Hz = 1155 rpm flat-plane firing), resampled to each band offline by tools/spec_gen/make_f40_loops.py (band-limited; verylow_low = 2900 band)"}})
json.dump(spec, open(ROOT + "cars/ac_f40.json", "w"), indent=1)
print("room mirror rot", round(mpitch, 1), round(myaw, 1)); print("baked", sorted(k for k in src if "F40BAKE" in src[k]))
