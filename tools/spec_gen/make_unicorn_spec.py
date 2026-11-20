"""first-pass spec for the AC 1320Video 'Unicorn' Corvette C5 Z06 (gbe_1320video_unicorn, 8 Second Shootout) on the Tuscan
(patterns: ac_rx7fd for AC + pop-ups, mw_corvette for the Tuscan). Frame notes: kn5_report/kn5_to_obj frame is x fwd,
y LEFT, z up (cm); Motor Town is y RIGHT, so car-space values below (sockets, boxes, seats) use y = -y_kn5."""
import json, math, re
ROOT = r"C:/Users/noust/OneDrive/Documents/claude/ps2motortown/"
SRC = r"C:/Users/noust/nfs-work/ac/unicorn/"
T = "Tex_AC_UC_"
inv = json.load(open(SRC + "inventory.json"))
special = {   # material -> slot (everything else: its own texture slot, named after the texture)
    "car_paint": "Paint", "Glass": "Glass", "window": "Glass", "Glass Int": "Glass", "ac_Material #403": "Glass",
    "HeadLight Glass": "Glass", "ac_Material #188": "Defrost", "Black Glass": "Defrost", "Mirror": "Mirror",
    "Exterior Chrome": "Trim", "Interior Chrome": "Trim",
}
slots, src = {}, {}
for m in inv["materials"]:
    n, tex = m["name"], m["tex"].get("txDiffuse", "")
    if n in special:
        slots[n] = special[n]; continue
    s = T + re.sub(r"[^A-Za-z0-9]", "", tex.rsplit(".", 1)[0]).upper()[:22]
    slots[n] = s; src[s] = tex
# AC multimap materials: the diffuse is a grey AO map, the colour comes from the detail texture (and the 1320Video skin's
# metal_detail_* overrides) -> bake AO x the real colour into a texture per material (user 2026-11-13: rims white,
# interior untextured). Chrome parts of the rims -> the game's Trim.
from PIL import Image
import numpy as np
BAKE = {"EXT_FRimBlack": "RIMBLACK", "EXT_FRimLugs": "RIMBLACK", "EXT_RRimBlack": "RRIMBLACK", "ac_Material #7443": "RRIMBLACK",
        "rollcage": "CAGE", "Interior Plastic": "INTPLASTIC", "Interior Leather": "INTLEATHER", "Carpet": "CARPETB",
        "carpet": "CARPETR", "Body Plastic": "BODYPLASTIC", "metal_rgh_003_#FFFFFFFF": "CALIPER",
        "ac_Material #172": "VENT", "ac_Material #789": "HEADLINER"}   # rear brake ducts + wiper arms: body AO map, really black (user: side vents glitched)
COL = {"RIMBLACK": (14, 14, 15), "RRIMBLACK": (14, 14, 15), "CAGE": (18, 18, 18), "INTPLASTIC": (36, 36, 37),
       "INTLEATHER": (32, 32, 33), "CARPETB": (40, 43, 46), "CARPETR": (30, 30, 31), "BODYPLASTIC": (26, 26, 27), "CALIPER": (99, 0, 0), "VENT": (12, 12, 13), "HEADLINER": (58, 58, 60)}
texof = {m["name"]: m["tex"].get("txDiffuse", "") for m in inv["materials"]}
for mat, tag in BAKE.items():
    out = "%s_UCBAKE_%s.png" % (texof[mat].rsplit(".", 1)[0], tag)
    if tag == "CALIPER":
        Image.new("RGB", (8, 8), COL[tag]).save(SRC + "textures/" + out)
    else:
        a = np.array(Image.open(SRC + "textures/" + texof[mat]).convert("L")).astype(float)
        a = a / max(1.0, a[a > 8].mean() if (a > 8).any() else a.mean())    # used texels average 1
        rgb = np.clip(a[..., None] * np.array(COL[tag], float), 0, 255).astype(np.uint8)
        Image.fromarray(rgb, "RGB").save(SRC + "textures/" + out)
    slots[mat] = T + tag; src[T + tag] = out
for mat in ("EXT_FRimChrome", "EXT_RRimChrome", "ac_Material #267"):
    slots[mat] = "Trim"
Image.new("RGB", (8, 8), (36, 36, 37)).save(SRC + "textures/UC_DASHTOP.png"); src[T + "DASHTOP"] = "UC_DASHTOP.png"   # = baked Interior Plastic
slots["scion_drag_misc"] = T + "CHUTE"; src[T + "CHUTE"] = "C:/Users/noust/nfs-work/ac/rx7_fd/textures/scion_drag_misc_diffuse.dds"
slots["scion_drag_misc2"] = T + "CHUTE2"; src[T + "CHUTE2"] = "C:/Users/noust/nfs-work/ac/rx7_fd/textures/scion_drag_misc2_diffuse.dds"
slots["Black Glass"] = T + "GLASSMASK"; src[T + "GLASSMASK"] = "EXT_glass_mask.dds"   # black frit band (alpha) over the cowl gap
# AC hub dummies (kn5 frame): wheel mesh offset = (-x, +y, -z)
hub = {"LF": (145.9, 73.8, 36.7), "RF": (145.3, -73.8, 36.7), "LR": (-119.5, 72.6, 36.7), "RR": (-120.1, -72.6, 36.7)}
disc = {"LF": "DISC_LF", "RF": "DISC_RF", "LR": "DISC_LR.001", "RR": "DISC_RR"}
off = lambda h: [round(-h[0], 2), round(h[1], 2), round(-h[2], 2)]
wheel = lambda key: {"parts": [{"part": "WHEEL_" + key, "offset": off(hub[key])},
                               {"part": disc[key], "offset": off(hub[key]), "note": "disc on the wheel (spins with it)"}], "reduce": 0.3}
TAIL, REV, HEAD, SIGF = "TailUC", "RevUC", "HeadUC", "SigF"
body_parts = [
    "BODY", "BODY_BLACK", "BODY_PLASTIC", "GRILL_MESH", "OBJECT001", "GRILLS", "EXTERIOR_CHROME", "RUBBER", "LOCKS", "LOD_A", "BLACK_GLASS",
    "_$$3DSIMED$$_", "WIPERS_A_SUB0", "WIPERS_A_SUB1",
    "GLASS", "CHE_3_CORVETTEC5R_04_COCKPIT_LEXANLF_WINDOW_", "CHE_3_CORVETTEC5R_04_COCKPIT_LEXANRF_WINDOW_",
    "SUSP_LF", "SUSP_RF", "SUSP_LR", "SUSP_RR", "_$$3DSIMED$$__008", "_$$3DSIMED$$__023", "_$$3DSIMED$$__028", "_$$3DSIMED$$__029",
    "LICENSE_SUB2", "BUMPERR_A_SUB2", "NUMBER_PLATE_LIGHTS",
    # drag chute (user 2026-11-13: use the RX-7's chute model so it looks like a real part): the do_canito RX-7's bag +
    # mount from its own export, moved to the real Unicorn's spot (bag at the top of the plate pocket, ~35 cm out)
    {"part": "SCION_DRAG_BOOT_LODA_SUB0", "geo": "C:/Users/noust/nfs-work/ac/rx7_fd/geo", "prefix": "AC_RX7FD", "src_scale": 100.0,
     "xform": {"t": [8, 0, 3]}},
    {"part": "SCION_DRAG_BOOT_LODA_SUB1", "geo": "C:/Users/noust/nfs-work/ac/rx7_fd/geo", "prefix": "AC_RX7FD", "src_scale": 100.0,
     "xform": {"t": [8, 0, 3]}},
    "REAL2", "REAL003", "REAL004",   # 1320Video / sponsor stickers on the rear glass (keep every source part)
    "ROLLCAGE",
    # interior (C6-sourced cabin)
    "INTERIOR_PLASTIC", "INTERIOR_LEATHER", "CARPET", "CARPET_S1", "ROOF_LINER", "STITCH", "DOORSILL_A_SUB0", "EVLRABBIT_C5_DRIFT",
    "CENTERCONSOLESTRUCTURE_A_SUB3", "CENTERCONSOLESTRUCTURE_A_SUB5", "CENTERCONSOLESTRUCTURE_A_SUB6",
    "CENTERSTACKBEZELS_A_SUB0", "CENTERSTACKBEZELS_A_SUB2", "CENTERSTACKBEZELS_A_SUB3", "CENTERSTACKBEZELS_A_SUB5",
    "DASHPAD_A_SUB0", "DASHPAD_A_SUB1", "DASHPAD_A_SUB5", "DASHSTRUCTURE_A_SUB1", "DASHSTRUCTURE_A_SUB5",
    "DOORCARDLF_A_SUB0", "DOORCARDLF_A_SUB4", "DOORCARDLF_A_SUB6", "SPEAKERDOORLF_A_SUB0", "SPEAKERDOORLF_A_SUB1",
    "STEERINGCOLUMN_A_SUB0", "GAUGECLUSTER_A_SUB0", "GAUGECLUSTER_A_SUB1", "SHIFT_LIGHT",
    "STEER_HR",
    # front bumper lamps: inner = fog (lit with the headlights), outer amber = turn signals (split by signal_lamps boxes)
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_BUMPERFA_TEXTURED_REFLECTOR_", "slot": HEAD},
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_BUMPERFA_DETAIL_GLASS_RED_", "slot": HEAD},
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_BUMPERFA_DETAIL_GLASS_CLEAR_", "slot": "Glass"},
    # tail: four round lamps (outer pair = turn signals, split below), centre high stop lamp, red side markers
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_TAILLIGHTL_TEXTURED_REFLECTOR_", "slot": TAIL},
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_TAILLIGHTR_TEXTURED_REFLECTOR_", "slot": TAIL},
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_TAILLIGHTL_TAIL_LIGHT_LOD0_.001", "slot": TAIL},
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_TAILLIGHTR_TAIL_LIGHT_LOD0_", "slot": TAIL},
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_LEXANLTL_DETAIL_GLASS_RED_", "slot": TAIL},
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_LEXANRTL_DETAIL_GLASS_RED_", "slot": TAIL},
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_LEXANLTL_DETAIL_GLASS_AMBER_", "slot": TAIL},
    {"part": "CHE_3_CORVETTEC5R_04_LOD0_LEXANRTL_DETAIL_GLASS_AMBER_", "slot": TAIL},
    "CHE_3_CORVETTEC5R_04_LOD0_LEXANLTL_MISC_", "CHE_3_CORVETTEC5R_04_LOD0_LEXANRTL_MISC_",
    {"part": "BRAKELIGHT_BUBLS", "slot": TAIL}, {"part": "BRAKELIGHTS.001", "slot": TAIL}, {"part": "TAILLIGHT_GLASS.001", "slot": TAIL},
    {"part": "GLASSBODYSIDEMARKERR_A_SUB1", "slot": TAIL},
    # reverse lamps: the white lamps either side of the licence plate (real C5 layout)
    {"part": "REVERSE_LIGHTS", "slot": REV}, {"part": "LICENSE", "slot": REV},
]
# left out (user 2026-11-13: always delete what pokes through): HOODLINER_A / TRUNKBAY_A / ENGINE_A_* (black underside geometry showed through the hood),
# ARROW_* (the game's needles turn at the same hubs), BLACK_GLASS* (tint layer over GLASS), GLASS_INT (duplicate),
# DEFROSTER*, CLUSTER_GLASS (would sit between the eye and the game's needles), REARVIEWMIRROR (game RoomMirror), WINGMIRROR* (own meshes)
eye = (-40.0, -38.5, 103.0)          # cushion top z 38 (x -30..-10): eye = cushion + 66, seat = cushion - 17 (AC Supra/RX-7 calibration)
mir = (9.0, -3.0, 108.5)
d = [m - e for m, e in zip(mir, eye)]; dl = math.sqrt(sum(x * x for x in d)); d = [x / dl for x in d]
r = [-1.0, 0.0, 0.02]; rl = math.sqrt(sum(x * x for x in r)); r = [x / rl for x in r]
n = [a - b for a, b in zip(r, d)]; nl = math.sqrt(sum(x * x for x in n)); X = [-x / nl for x in n]
myaw = math.degrees(math.atan2(X[1], X[0])); mpitch = math.degrees(math.asin(X[2]))
tilt = 24.4   # dial plane faces the driver, leaning 24.4 deg back (normal -0.91 x, +0.41 z)
nrm = (-0.911, 0.0, 0.413)
sock = lambda p: [round(p[0] + 0.4 * nrm[0], 2), round(-p[1], 2), round(p[2] + 0.4 * nrm[2], 2)]   # 0.4 cm proud, MT y
spec = {
    "car": "AC_UNICORN", "display_name": "Corvette C5 Z06 'Unicorn' 1320Video (8 Second Shootout)", "prefix": "AC_UNICORN",
    "base_vehicle": "Tuscan", "default_slot": "Bottom", "source_scale": 100.0,
    "geometry_dir": SRC + "geo", "texture_dir": SRC + "textures",
    "out_dir": "C:/Users/noust/mt-work/build/AC_UNICORN/meshes", "cost": 140000, "wheel_part": True,
    "wheel_display_name": "Drag Wheels (Unicorn C5)", "base_wheel": "Vista",
    "texture_slots": slots, "texture_sources": src,
    "meshes": {
        "Body": {"parts": body_parts, "reduce": 0.4, "drop_slots": ["Defrost", "Tex_AC_UC_CALIPER"],
                 "drop_boxes": [[3, -17, 102, 15, 11, 114.5],          # AC rear-view mirror housing (game RoomMirror goes there)
                                [45, -28, 75.5, 50.5, -22, 80.5],        # AC static fuel needle (game needle replaces it)
                                [44, -57, 75, 49.5, -51, 80]],           # AC static coolant needle
                 "drop_note": "boxes in MT frame (y right)"},
        "SideMirror_L": {"parts": [{"part": "WINGMIRRORL_A_SUB2", "slot": "Mirror", "normal_filter": {"axis": 0, "max": -0.75}}], "planar_uv": {}},
        "SideMirror_R": {"parts": [{"part": "WINGMIRRORR_A_SUB3", "slot": "Mirror", "normal_filter": {"axis": 0, "max": -0.75}}], "planar_uv": {"flip_u": True}},
        "Popup": {"parts": [{"part": "HEADLIGHT_L", "groups": [1, 3, 4]}, {"part": "HEADLIGHT_L", "groups": [2], "slot": "HeadPod"},
                            {"part": "HEADLIGHT_R", "groups": [0, 2, 3]}, {"part": "HEADLIGHT_R", "groups": [1], "slot": "HeadPod"}],
                  "note": "C5 pop-up pods (closed in the model; glass left out like the RX-7); AC Lights.ksanim: hinge x 180.3 z 72.6, 25 deg front-up"},
        "Wheel_L": wheel("LF"), "Wheel_R": wheel("RF"), "Wheel_RL": wheel("LR"), "Wheel_RR": wheel("RR")},
    "rear_wheel_meshes": True, "rear_wheel_part": True,
    "mesh_names": {"Wheel_L": "AC_UNICORN_L", "Wheel_R": "AC_UNICORN_R", "Wheel_RL": "AC_UNICORN_REAR_L", "Wheel_RR": "AC_UNICORN_REAR_R",
                   "SteeringWheel": "AC_UNICORN"},
    "final_slot_names": {"Paint": "Body_01", "Glass": "Window", HEAD: "HeadLight", "HeadPod": "HeadLight", TAIL: "TailLight", REV: "ReverseLight",
                         "Signal_L_F": "LeftSignalLight", "Signal_R_F": "RightSignalLight",
                         "Signal_L_R": "LeftTailLight", "Signal_R_R": "RightTailLight"},
    "mirror_sockets": {"SideMirror_L": "SideMirror_L", "SideMirror_R": "SideMirror_R"},
    "wheels": {"front_x": 145.6, "rear_x": -119.8, "half_track": 73.8, "rear_half_track": 72.6, "z": 32.5, "rear_z": 35.5,
               "radius": 32.5, "auto_arches": False,
               "note": "AC hubs (wheelbase 265.4 = AC 2.654); front tyre r 32.5, rear Hoosier drag radial r ~35.5"},
    "collision_boxes": [{"center": [16, 0, 45], "size": [450, 182, 50]}, {"center": [-30, 0, 98], "size": [190, 140, 40]}],
    "strip_part_slots": ["Bonnet", "FrontBumper", "RearBumper"],   # the Tuscan row fits its own hood + bumpers (user 2026-11-13)
    "sockets": {"Body": [{"name": "Exhaust_Left", "loc": [-212, -24, 27], "rot": [0, 180, 0]},
                         {"name": "Exhaust_Right", "loc": [-212, 24, 27], "rot": [0, 180, 0]},
                         {"name": "RearWing", "loc": [-195, 0, 96], "rot": [0, 0, 0]},
                         {"name": "TaxiRoofSign", "loc": [-40, 0, 126], "rot": [0, 0, 0]},
                         {"name": "TrailerHitch", "loc": [-212, 0, 25], "rot": [0, 0, 0]}]},
    "blueprint": {
        "seats": {"DriverSeat_GEN_VARIABLE": [-38, -38.5, 21], "PassengerSeat1_GEN_VARIABLE": [-38, 38.5, 21],
                  "PassengerSeat2_GEN_VARIABLE": [-38, 38.5, 21], "PassengerSeat3_GEN_VARIABLE": [-38, -38.5, 21]},
        "cockpit_camera": list(eye),
        "components": {"RoomMirror_GEN_VARIABLE": list(mir), "FrontDomeLightSlot_GEN_VARIABLE": [-25, 0, 117],
                       "CabinDomeLightSlot_GEN_VARIABLE": [-75, 0, 116],
                       "HeadLight_Left_GEN_VARIABLE": [210, -64, 66], "HeadLight_Right_GEN_VARIABLE": [210, 64, 66],
                       "BlinkerLight_01_GEN_VARIABLE": [222, 82, 39], "BlinkerLight_02_GEN_VARIABLE": [222, -82, 39],
                       "TaliLight_01_GEN_VARIABLE": [-204, -45, 82], "TaliLight_02_GEN_VARIABLE": [-204, 45, 82]},
        "component_rotations": {"RoomMirror_GEN_VARIABLE": [round(mpitch, 1), round(myaw, 1), 0]},
        "keep_body_materials": 1, "body_mass": 1110, "room_mirror_aim_z": 0.02,
        "cdo_names": {"BodyMaterialName": "Body_01"}},   # pods painted natively like the Panther's
    "extract": {"SteeringWheel": {"from": "Body", "center": [23.9, -38.5, 78.4], "radius": 19.5, "x_range": [10, 34],
                                  "uv_box": [-99, -99, 99, 99], "uv_slots": [slots["c6steerwh01"], slots["c6stitch"]],
                                  "socket": "SteeringWheel", "align_x": True, "reduce": 0.5}},
    "signal_lamps": [{"tag": "_F", "from": HEAD, "box": [190, -95, 30, 235, -79, 50]},
                     {"tag": "_F", "from": HEAD, "box": [190, 79, 30, 235, 95, 50]},
                     {"tag": "_R", "from": TAIL, "box": [-215, -80, 70, -190, -53, 95]},
                     {"tag": "_R", "from": TAIL, "box": [-215, 53, 70, -190, 80, 95]}],
    "lamp_slots": {HEAD: {"kind": "head", "texture_slot": slots["textured_reflector"]},
                   "HeadPod": {"kind": "head", "texture_slot": slots["HeadLight Chrome"]},
                   TAIL: {"kind": "tail", "texture_slot": slots["textured_reflector.001"]},
                   REV: {"kind": "reverse", "texture_slot": slots["c4hlightson"]},
                   "Signal_L_F": {"kind": "signal", "texture_slot": slots["textured_reflector"]},
                   "Signal_R_F": {"kind": "signal", "texture_slot": slots["textured_reflector"]},
                   "Signal_L_R": {"kind": "signal_tail_red", "texture_slot": slots["textured_reflector.001"]},
                   "Signal_R_R": {"kind": "signal_tail_red", "texture_slot": slots["textured_reflector.001"]}},
    "dashboard": {"sockets": [
        {"name": "Niddle_RPM", "loc": sock((48.31, 43.82, 80.40)), "rot": [0, -90, round(-90 + tilt, 1)]},
        {"name": "Niddle_Speed", "loc": sock((48.36, 34.80, 80.78)), "rot": [0, -90, round(-90 + tilt, 1)]},
        {"name": "Niddle_Fuel", "loc": [48.21, -25.83, 79.51], "rot": [0, -90, round(-90 + tilt, 1)]},
        {"name": "Niddle_Temp", "loc": [47.29, -53.0, 78.96], "rot": [0, -90, round(-90 + tilt, 1)]}],
        "note": "AC ARROW_RPM/SPEED hubs; fuel/temp = the C5 cluster's own fuel and coolant dials (texture centres mapped to 3D)"},
    "gauge_style": {"face_color": [2, 2, 4], "ink": [150, 178, 245], "minor_ink": [120, 145, 210], "red_color": [235, 30, 25],
                    "font_file": "arialbd.ttf"},
    "gauge_faces": {slots["ac_Material #404"]: [
        {"center": [0.1954, 0.6095], "face": [0.1954, 0.6095, 0.19], "radius": 0.165, "rotate": 0, "min": 0, "max": 8,
         "text_step": 1, "line_step": 0.5, "start": 140, "end": 400, "red_from": 7.5, "font": 0.14,
         "captions": [["RPM x1000", 0.32, 90]], "caption_font": 0.08, "note": "C5 art 0-7k; the Unicorn revs to 8000"},
        {"center": [0.5847, 0.6022], "face": [0.5847, 0.6022, 0.19], "radius": 0.165, "rotate": 0, "min": 0, "max": 200,
         "text_step": 20, "line_step": 10, "start": 140, "end": 400, "font": 0.12, "captions": [["MPH", 0.32, 90]], "caption_font": 0.09},
        {"center": [0.9384, 0.6091], "face": [0.9384, 0.6091, 0.07], "radius": 0.06, "rotate": 0, "min": 0, "max": 1, "text_step": 1,
         "line_step": 0.25, "start": 210, "end": 330, "font": 0.3, "labels": {"0": "E", "1": "F"}},
        {"center": [0.3355, 0.3277], "face": [0.3355, 0.3277, 0.07], "radius": 0.06, "rotate": 0, "min": 40, "max": 120, "text_step": 80,
         "line_step": 20, "start": 210, "end": 330, "font": 0.3, "labels": {"40": "C", "120": "H"}, "red_from": 110}]},
    "gauge_ranges": {"RPM": {"max": 8}, "Speed": {"max": 200, "value_scale": 1.609344}},
    "needle_color": [240, 90, 20], "needle_width": 0.35,
    "emissive_slots": {"Gauges": {"texture_slot": slots["ac_Material #404"], "glow": 2.0},
                       "NeedleGlow": {"texture_slot": "Tex_UNICORN_NEEDLE", "glow": 2.0}},
    "masked_texture_slots": [T + "GLASSMASK"] + [slots[k] for k in ("c6stitch", "c4hlightson", "b375_real_st", "ac_Material #2522", "ac_Material #2677", "ac_Material #802")],
    "performance_source": "AC data (gbe_1320video_unicorn): TOTALMASS 1651, RWD, 6 gears 2.97/2.07/1.43/1.00/0.71/0.57 R-3.28 FINAL 3.15, LIMITER 8000, MINIMUM 900; power.lut NA 560 Nm @5000; TURBO_0+TURBO_1 MAX_BOOST 0.8 each (x2.6 = 1456 Nm, ui 1253 whp)",
    "custom_parts": {
        "transmissions": [{"row": "AC_UNICORN_6MT", "base_row": "6SpeedSportsLP670", "asset": "AC_UNICORN_6MT",
                           "base_asset": "Cars/Parts/Transmission/Manual6SpeedSports_LP670", "display_name": "T56 6-Speed Drag (Unicorn C5)",
                           "cost": 8000, "mass": 100,
                           "ratios": {g: round(v * 3.15 / 3.31, 3) for g, v in
                                      {"R": -3.28, "1": 2.97, "2": 2.07, "3": 1.43, "4": 1.0, "5": 0.71, "6": 0.57}.items()},
                           "note": "AC final 3.15 folded in (game row FD_3.31): ratio x 3.15/3.31"}],
        "engines": []},
    "part_overrides": {"Engine": "AC_UNICORN_LS_TT", "Transmission": "AC_UNICORN_6MT", "FinalDriveRatio": "FD_3.31",
                       "CoolantRadiator": "SmallRadiator_110", "Turbocharger": "PS_Boost_200psi",
                       "Tire0": "PerformanceTire_46", "Tire1": "PerformanceTire_46",
                       "Tire2": "PerformanceDragTireStrip", "Tire3": "PerformanceDragTireStrip",
                       "Wheel0": "AC_UNICORN", "Wheel1": "AC_UNICORN", "Wheel2": "AC_UNICORN_REAR", "Wheel3": "AC_UNICORN_REAR",
                       "BrakePad0": "BrakePad_Small_02", "BrakePad1": "BrakePad_Small_02", "BrakePad2": "BrakePad_Small_02", "BrakePad3": "BrakePad_Small_02",
                       "BrakeBalance": "BrakeBalance_F60", "Headlight": "AC_UNICORN_Popup"},
    "popup": {"hinge": [180.3, 72.6], "angle": 25.0, "seconds": 0.5,
              "note": "AC Lights.ksanim: HEADLIGHT_L/R rotate 25 deg about the lateral axis through their node (x 180.3, z 72.6)"},
    "add_shapes": [   # the C6 dash stops ~15 cm short of the C5 cowl: black tray under the windscreen (user: gap at the bottom of the windshield)
        # (user: still a gap; use the model's dash) -> the dash top continued in the dash's own colour: from under the
        # dash front edge (x 60, z 87.5) down to the windscreen base (x 93, z 79.5), full width
        # (user: the grey plate is obvious) -> same material and texel as the dash top's front edge (x 63, z 87; OBJ uv 0.24/1.309),
        # starting right at that edge
        {"mesh": "Body", "type": "quad", "slot": slots["Interior Plastic"], "uv": [0.24, 1.309],
         "points": [[62, -74, 87.0], [62, 74, 87.0], [93, 74, 79.5], [93, -74, 79.5]]},
    ],
    "drivetrain_note": "Tuscan is RWD (AC: RWD). Front street tyres, Hoosier drag radials at the rear like the AC car.",
}
lut = [(500, 324.15), (1000, 404.05), (1500, 432.53), (2000, 461.95), (2500, 480.78), (3000, 495.3), (3500, 514.39), (4000, 537.3),
       (4500, 555.68), (4750, 560.19), (5000, 560.17), (5500, 549.1), (6000, 524.97), (6500, 503.28), (7000, 487.25), (7500, 457.62), (8000, 408)]
mx, lim = 560.19, 8000
curve = [[round(rr / lim, 4), round(t / mx, 4)] for rr, t in lut] + [[5.0, 0.15]]
spec["custom_parts"]["engines"].append({
    "row": "AC_UNICORN_LS_TT", "base_row": "SmallBlock_320HP", "asset": "AC_UNICORN_LS_TT", "base_asset": "Cars/Parts/Engine/S58",
    "display_name": "Twin-Turbo LS V8 (Unicorn C5)", "mass": 230, "cost": 60000, "max_torque_nm": mx, "max_rpm": lim,
    "curve": curve, "curve_note": "AC power.lut (NA, 560 Nm @4750-5000); boost from PS_Boost_200psi (1 + 0.08 x 20 = x2.6 = AC twin turbos 0.8 + 0.8)",
    "physics_from": "Cars/Parts/Engine/FordSmalBlock302_V8_5L_320HP", "idle_throttle": 0.0009,
    "sound_cue": {"cue_base": "Cars/Parts/Engine/Sound/s58/SC_V8Engine", "dir": "AC_UNICORN",
                  "loops": [["l1", 1120], ["l2", 2650], ["l3", 3470], ["l4", 4640], ["l5", 5420], ["l6", 6710], ["l7", 7810]],
                  "note": "the car's own bank (gbe_1320video_unicorn.bank, vgmstream): SLS_ral idle, SLS_acc_02/05/08/10/13/16 loops; rpm from the spectrum (V8 firing = 8th half-order)"}})
json.dump(spec, open(ROOT + "cars/ac_unicorn.json", "w"), indent=1)
print("room mirror rot", round(mpitch, 1), round(myaw, 1), "sockets", [s["loc"] for s in spec["dashboard"]["sockets"]])
print("slots", len(set(slots.values())))
