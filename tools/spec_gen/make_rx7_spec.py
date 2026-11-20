"""first-pass spec for the AC Mazda RX-7 FD (D&O Canito, 8 Second Shootout) on the Magis (patterns: ac_supra for the Magis, ac_civiceg for AC)"""
import json, math
ROOT = r"C:/Users/noust/OneDrive/Documents/claude/ps2motortown/"
T = "Tex_AC_FD_"
slots = {
    "carpaint": "Paint", "black_ext": T + "BLACK", "black_int": T + "BLACK", "black_glass_ext": T + "BLACK", "chrome_ext": "Trim",
    "chrome_int": "Trim", "lights_reflector_ext": T + "LIGHTS", "lights_chrome": T + "LIGHTS", "lights_glass_ext": "Glass",
    "clear_lights_glass_ext": "Glass", "defrost_glass": "Defrost", "brake_calipers": T + "CALIPER", "brake_disc": T + "DISC",
    "misc": T + "MISC", "plastic_ext": T + "PLASTIC", "st_wheel": T + "STEER", "stitching": T + "STITCH",
    "interior_lod0": T + "INTERIOR", "needles": T + "NEEDLEAC", "display_int": T + "DISPLAY", "seat_plastic": T + "SEATPL",
    "detail_plastic_int": T + "DETAIL", "plastic_int": T + "DASHPL", "dash_leather": T + "DASHLE", "cloth": T + "CLOTH",
    "carpet": T + "CARPET", "grill_int": T + "GRILL", "headliner": T + "HEADLINER", "leather_a": T + "LEATHERA",
    "MIRROR_PLACEMENT": "Mirror", "pedals": T + "PEDALS", "rubber_int": T + "RUBBERI", "seat_leather": T + "SEAT",
    "glass_ext": "Glass", "rubber_ext": T + "RUBBER", "undercarriage": T + "UNDER", "black_metal_ext": T + "WIPER",
    "glass_int": "Glass", "floormats": T + "FLOORMAT", "EXT_TIR_RUBBER": T + "TIRE", "_2Default_Material": T + "RIMSILVER",
    "_28___Default": T + "RIM", "scion_drag_misc": T + "WBAR", "scion_drag_misc2": T + "WBAR2", "ENGINE_BRUSHMETAL": "Trim",
    "02 - Default": "Trim",
}
src = {T + "LIGHTS": "lights_lod0.dds", T + "CALIPER": "EXT_CALIPER.dds", T + "DISC": "EXT_BRAKEDISC.dds", T + "MISC": "EXT_MISC_AO_BAKED.png",
       T + "PLASTIC": "EXT_PLASTIC_BAKED.png", T + "STEER": "ST_WHEEL_AO_BAKED.png", T + "STITCH": "INT_STITICHING.dds",
       T + "INTERIOR": "interior_lod0.dds", T + "NEEDLEAC": "INT_NEEDLE_AO.dds", T + "DISPLAY": "INT_DISPLAY.dds",
       T + "SEATPL": "INT_SEAT_PLASTIC_AO_BAKED.png", T + "DETAIL": "INT_DETAIL_PLASTIC_AO_BAKED.png", T + "DASHPL": "INT_DASH_PLASTIC_AO_BAKED.png",
       T + "DASHLE": "INT_DASH_LEATHER_AO_BAKED.png", T + "CLOTH": "INT_CLOTH_AO_BAKED.png", T + "CARPET": "INT_CARPET_AO_BAKED.png",
       T + "GRILL": "INT_GRILL_AO_BAKED.png", T + "HEADLINER": "INT_HEADLINER_AO_BAKED.png", T + "LEATHERA": "INT_LEATHER_A_AO_BAKED.png",
       T + "PEDALS": "INT_PEDALS_AO_BAKED.png", T + "SEAT": "INT_SEAT_LEATHER_AO_BAKED.png", T + "UNDER": "EXT_UNDERCARRIAGE.dds",
       T + "FLOORMAT": "INT_CARPET_TEXTURE.dds", T + "TIRE": "slick (3).png", T + "RIM": "rimblack.dds",
       T + "WBAR": "scion_drag_misc_diffuse.dds", T + "WBAR2": "scion_drag_misc2_diffuse.dds",
       T + "BLACK": "black.dds", T + "RUBBER": "EXT_RUBBER_AO_BAKED.png", T + "RUBBERI": "INT_RUBBER_AO_BAKED.png", T + "WIPER": "EXT_WIPERS_AO_BAKED.png", T + "RIMSILVER": "rim_silver.png"}
# hub dummies (exporter frame: x fwd, y left, z up from the lowest point): wheel mesh offset = (-x, +y, -z)
hub = {"LF": (130.5, 72.8, 35.3), "RF": (130.6, -72.8, 35.3), "LR": (-112.2, 73.0, 35.3), "RR": (-112.1, -73.0, 35.3)}
off = lambda h: [round(-h[0], 2), round(h[1], 2), round(-h[2], 2)]
wheel = lambda key: {"parts": [{"part": "WHEEL_" + key, "offset": off(hub[key])},
                               {"part": "DISC_" + key, "offset": off(hub[key]), "note": "disc on the wheel (spins with it)"}], "reduce": 0.3}
body_parts = [
    "EXT_BODY", "EXT_BODY_BLACK", "EXT_BODY_MISC", "EXT_BODY_PLASTIC", "EXT_BODY_REFLECTOR", "EXT_BODY_RUBBER", "EXT_BODY_TEXTURED",
    "EXT_BLACK_GLASS", "EXT_BODY_ANTENNA", "EXT_BODY_MIRROR_L", "EXT_BODY_MIRROR_R", "EXT_MIRROR_L_BLACK", "EXT_MIRROR_L_RUBBER",
    "EXT_MIRROR_R_BLACK", "EXT_MIRROR_R_RUBBER", "EXT_TRUNK", "EXT_TRUNK_BLACK", "EXT_TRUNK_BLACK_GLASS", "EXT_TRUNK_RUBBER",
    "EXT_UNDERCARRIAGE", "EXT_WIPER_L_METAL", "EXT_WIPER_L_RUBBER", "EXT_WIPER_R_METAL", "EXT_WIPER_R_RUBBER",
    "GEO_EXT_WINDOWS", "Z_EXT_BACKLIGHT_CLEAR_GLASS", "Z_INT_GLASS_FRONT", "Z_INT_GLASS_LF", "Z_INT_GLASS_REAR", "Z_INT_GLASS_RF",
    "MOTORHOOD", "SUSP_LF", "SUSP_RF", "SUSP_LR", "SUSP_RR", "INT_FLOORMATS",
    "CYLINDER003_SUB0", "SCION_DRAG_BOOT_LODA_SUB0", "SCION_DRAG_BOOT_LODA_SUB1", "TURBINA_LFG_GMT_SUB1",   # drag chute + mount, side-exit turbo pipe (user: keep every source part)
    # front bumper: 3 daytime bulb + 8 driving-lamp reflector = lit with the headlights; 10-12 = amber corner indicators
    {"part": "FRONT_BUMPER", "groups": [0, 1, 2, 4, 5, 6, 7, 9]}, {"part": "FRONT_BUMPER", "groups": [3, 8], "slot": "HeadFD"},
    {"part": "FRONT_BUMPER", "groups": [10, 11, 12], "slot": "SigF"},
    # pop-up headlamps (closed in the model): bulb + reflector
    # pop-up pods (LIGHT_FRONT): own skeletal mesh "Popup" (tools/make_popup.py), not in the Body
    {"part": "EXT_SIDE_INDICATOR_L", "slot": "SigF"}, {"part": "EXT_SIDE_INDICATOR_R", "slot": "SigF"},
    # rear (late FD round lamps): brake ring + third light = tail, outer rounds = indicators, bumper lamps = reverse
    {"part": "EXT_BRAKELIGHT", "slot": "TailFD"}, {"part": "GEO_EXT_BRAKE_CENTER", "slot": "TailFD"},
    {"part": "EXT_INDICATOR_LR", "slot": "SigR"}, {"part": "EXT_INDICATOR_RR", "slot": "SigR"},
    {"part": "REAR_BUMPER", "groups": [2, 3, 4, 5, 6, 7, 8, 9]}, {"part": "REAR_BUMPER", "groups": [0, 1], "slot": "RevFD"},
    # cockpit: AC needles out (the game's turn at the same hubs) except the oil gauge's (no game needle there); AC room mirror glass out
    {"part": "COCKPIT_HR", "skip_groups": [0, 1, 2, 3, 6, 7, 8, 9, 29], "note": "needles (oil kept) + room mirror glass"},
    "STEER_HR",
]
eye, mir = (-33.0, 39.9, 104.0), (15.2, 0.0, 110.0)
d = [m - e for m, e in zip(mir, eye)]; dl = math.sqrt(sum(x * x for x in d)); d = [x / dl for x in d]
r = [-1.0, 0.0, 0.017]; rl = math.sqrt(sum(x * x for x in r)); r = [x / rl for x in r]
n = [a - b for a, b in zip(r, d)]; nl = math.sqrt(sum(x * x for x in n)); X = [-x / nl for x in n]
myaw = math.degrees(math.atan2(X[1], X[0])); mpitch = math.degrees(math.asin(X[2]))
tilt = -1.1   # dial plane leans 1.1 deg down -> roll -90 + tilt
spec = {
    "car": "AC_RX7FD", "display_name": "Mazda RX-7 FD (8 Second Shootout)", "prefix": "AC_RX7FD",
    "base_vehicle": "Magis", "default_slot": "Bottom", "source_scale": 100.0,
    "geometry_dir": "C:/Users/noust/nfs-work/ac/rx7_fd/geo", "texture_dir": "C:/Users/noust/nfs-work/ac/rx7_fd/textures",
    "out_dir": "C:/Users/noust/mt-work/build/AC_RX7FD/meshes", "cost": 90000, "wheel_part": True,
    "wheel_display_name": "Drag Wheels (8 Second RX-7 FD)",
    "texture_slots": slots, "texture_sources": src,
    "meshes": {
        "Body": {"parts": body_parts, "reduce": 0.4, "drop_slots": ["Defrost", "Tex_AC_FD_CALIPER"],
                 "drop_boxes": [[11, -15, 104, 22, 15, 117]], "drop_note": "AC static room mirror housing (the game's RoomMirror goes there)"},
        "SideMirror": {"parts": [{"part": "EXT_MIRROR_L", "slot": "Mirror"}], "recenter": True, "planar_uv": {},
                       "counter_rotate": {"rot": [-3.5, -26.0, 0]}},
        "RightSideMirror": {"parts": [{"part": "EXT_MIRROR_R", "slot": "Mirror", "mirror": True}], "recenter": True, "planar_uv": {},
                            "counter_rotate": {"rot": [-1.1, 4.0, 0], "mirror_frame": True}},
        "Popup": {"parts": [{"part": "LIGHT_FRONT", "groups": [2, 3, 4, 5, 6]}, {"part": "LIGHT_FRONT", "groups": [0, 1], "slot": "HeadFD"}], "drop_slots": ["Glass"],
                  "note": "pop-up headlamp pods (closed); hinge across the car at x 168.81, z 71.39; AC lights.ksanim opens 52.4 deg (front edge up)"},
        "Wheel_L": wheel("LF"), "Wheel_R": wheel("RF"), "Wheel_RL": wheel("LR"), "Wheel_RR": wheel("RR")},
    "rear_wheel_meshes": True, "rear_wheel_part": True,
    "mesh_names": {"Wheel_L": "AC_RX7FD_L", "Wheel_R": "AC_RX7FD_R", "Wheel_RL": "AC_RX7FD_REAR_L", "Wheel_RR": "AC_RX7FD_REAR_R",
                   "SteeringWheel": "AC_RX7FD"},
    "final_slot_names": {"Paint": "Body", "Glass": "Window", "HeadFD": "HeadLight", "TailFD": "TailLight", "RevFD": "ReverseLight",
                         "Signal_L_F": "LeftSignalLight", "Signal_R_F": "RightSignalLight",
                         "Signal_L_R": "LeftSignalLight", "Signal_R_R": "RightSignalLight"},
    "mirror_components": {"LeftSideMirror_GEN_VARIABLE": "SideMirror", "RightSideMirror_GEN_VARIABLE": "RightSideMirror:mirror"},
    "mirror_meshes": {"RightSideMirror_GEN_VARIABLE": "RightSideMirror"},
    "wheels": {"front_x": 130.55, "rear_x": -112.15, "half_track": 72.8, "rear_half_track": 73.0, "z": 32.0, "rear_z": 35.5,
               "radius": 31.75, "auto_arches": False,
               "note": "AC hubs; front tyre r 31.75, drag rear r 35.15 (z ~ tyre radius, as the Civic EG)"},
    "collision_boxes": [{"center": [0, 0, 45], "size": [418, 172, 50]}, {"center": [-35, 0, 100], "size": [180, 130, 40]},
                        {"center": [-294, 0, 14], "size": [12, 78, 12], "note": "wheelie bar wheels (user: make it solid)"}],
    "strip_part_slots": ["RearWing"],
    "sockets": {"Body": [{"name": "Exhaust_Left", "loc": [-213, 40, 28], "rot": [0, 180, 0]},
                         {"name": "Exhaust_Right", "loc": [-213, 40, 28], "rot": [0, 180, 0]},
                         {"name": "RearWing", "loc": [-196, 0, 80], "rot": [0, 0, 0]},
                         {"name": "TaxiRoofSign", "loc": [-40, 0, 125], "rot": [0, 0, 0]},
                         {"name": "TrailerHitch", "loc": [-212, 0, 28], "rot": [0, 0, 0]}]},
    "blueprint": {
        "seats": {"DriverSeat_GEN_VARIABLE": [-30, 39.9, 22], "PassengerSeat1_GEN_VARIABLE": [-30, -39.9, 22]},
        "cockpit_camera": list(eye),
        "components": {"RoomMirror_GEN_VARIABLE": list(mir), "FrontDomeLightSlot_GEN_VARIABLE": [-25, 0, 112],
                       "HeadLight_Left_GEN_VARIABLE": [190, -60, 60], "HeadLight_Right_GEN_VARIABLE": [190, 60, 60],
                       "BlinkerLight_01_GEN_VARIABLE": [196, 60, 47], "BlinkerLight_02_GEN_VARIABLE": [196, -60, 47],
                       "TaliLight_01_GEN_VARIABLE": [-195, -62, 75], "TaliLight_02_GEN_VARIABLE": [-195, 62, 75]},
        "component_rotations": {"RoomMirror_GEN_VARIABLE": [round(mpitch, 1), round(myaw, 1), 0],
                                "LeftSideMirror_GEN_VARIABLE": [-3.5, -26.0, 0], "RightSideMirror_GEN_VARIABLE": [-1.1, 4.0, 0]},
        "keep_body_materials": 1, "body_mass": 860, "room_mirror_aim_z": 0.017,
        "cdo_names": {"BodyMaterialName": "Body"}},   # pods painted natively like the Panther's (Magis paint slot = Body)
    "extract": {"SteeringWheel": {"from": "Body", "center": [18.5, 39.85, 76.46], "radius": 17.5, "x_range": [8, 30],
                                  "uv_box": [-99, -99, 99, 99], "uv_slots": [T + "STEER", T + "STITCH"],
                                  "socket": "SteeringWheel", "align_x": True, "reduce": 0.5}},
    "signal_lamps": [{"tag": "_F", "from": "SigF", "box": [60, -100, 0, 260, 100, 120]},
                     {"tag": "_R", "from": "SigR", "box": [-260, -100, 0, -100, 100, 120]}],
    "lamp_slots": {k: {"kind": v, "texture_slot": T + "LIGHTS"} for k, v in
                   (("HeadFD", "head"), ("TailFD", "tail"), ("RevFD", "reverse"), ("Signal_L_F", "signal"), ("Signal_R_F", "signal"),
                    ("Signal_L_R", "signal_tail"), ("Signal_R_R", "signal_tail"))},
    "dashboard": {"sockets": [
        {"name": "Niddle_RPM", "loc": [39.2, 39.7, 81.05], "rot": [0, -90, -90 + tilt]},
        {"name": "Niddle_Speed", "loc": [38.8, 50.94, 77.95], "rot": [0, -90, -90 + tilt]},
        {"name": "Niddle_Fuel", "loc": [37.21, 25.89, 76.7], "rot": [-(90 + tilt), 0, -180]},
        {"name": "Niddle_Temp", "loc": [37.9, 32.78, 75.14], "rot": [-(90 + tilt), 0, -180]}],
        "parent_socket": "SteeringWheel",
        "note": "sockets = AC ARROW_* hubs, 0.4 cm proud; dial plane ~vertical (1.1 deg down); fuel/temp dials sit left of their hubs (turned 90, as the Supra)"},
    "texture_upscale": {T + "INTERIOR": 4},
    "gauge_style": {"face_color": [8, 8, 8], "ink": [240, 240, 236], "minor_ink": [190, 190, 190], "red_color": [225, 30, 25],
                    "font_file": "arialbd.ttf"},
    "texture_patches": {T + "INTERIOR": [{"center": [0.6, 0.665], "radius": 0.085, "fill": [8, 8, 8], "all": True},
                                         {"center": [0.9, 0.665], "radius": 0.085, "fill": [8, 8, 8], "all": True}]},
    "gauge_faces": {T + "INTERIOR": [
        {"center": [0.2518, 0.2552], "face": [0.2518, 0.2552, 0.245], "radius": 0.22, "rotate": 0, "min": 0, "max": 160,
         "text_step": 20, "line_step": 10, "start": 140, "end": 400, "font": 0.12, "captions": [["MPH", 0.3, 90]], "caption_font": 0.08,
         "note": "JDM 180 km/h art redrawn in mph"},
        {"center": [0.7481, 0.2506], "face": [0.7481, 0.2506, 0.245], "radius": 0.22, "rotate": 0, "min": 0, "max": 10,
         "text_step": 1, "line_step": 0.5, "start": 140, "end": 400, "red_from": 9, "font": 0.13,
         "captions": [["x1000 RPM", 0.3, 90]], "caption_font": 0.07, "note": "AC art 0-9k; game sweep to 10k (limiter 9000)"},
        {"center": [0.6517, 0.7084], "radius": 0.11, "rotate": 90, "min": 0, "max": 1, "text_step": 1, "line_step": 0.25,
         "start": 210, "end": 330, "font": 0.25, "labels": {"0": "E", "1": "F"}},
        {"center": [0.9947, 0.6704], "radius": 0.11, "rotate": 90, "min": 40, "max": 120, "text_step": 80, "line_step": 20,
         "start": 210, "end": 330, "font": 0.25, "labels": {"40": "C", "120": "H"}, "red_from": 110}]},
    "gauge_ranges": {"RPM": {"max": 10}, "Speed": {"max": 160, "value_scale": 1.609344}},
    "needle_color": [240, 90, 20], "needle_width": 0.4,
    "emissive_slots": {"Gauges": {"texture_slot": T + "INTERIOR", "glow": 2.0, "mask_from_gauges": True},
                       "NeedleGlow": {"texture_slot": "Tex_RX7FD_NEEDLE", "glow": 2.0}},
    "masked_texture_slots": [T + "STITCH"],
    "performance_source": "AC data (do_canito_rx7): TOTALMASS 1305, RWD, 6 gears 3.827/2.360/1.685/1.312/1.0/0.793 R-1.902 FINAL 3.9, LIMITER 9000, MINIMUM 750; power.lut NA 307 Nm @5000; TURBO_0 MAX_BOOST 2.5 (x3.5) ref 5000",
    "custom_parts": {
        "transmissions": [{"row": "AC_RX7FD_6MT_DRAG", "base_row": "6SpeedSportsLP670", "asset": "AC_RX7FD_6MT",
                           "base_asset": "Cars/Parts/Transmission/Manual6SpeedSports_LP670", "display_name": "6-Speed Drag (8 Second RX-7 FD)",
                           "cost": 8000, "mass": 60,
                           "ratios": {g: round(v * 3.9 / 3.31, 3) for g, v in
                                      {"R": -1.902, "1": 3.827, "2": 2.360, "3": 1.685, "4": 1.312, "5": 1.0, "6": 0.793}.items()},
                           "note": "AC final 3.9 folded in (game row FD_3.31): ratio x 3.9/3.31"}],
        "engines": []},
    "part_overrides": {"Engine": "AC_RX7FD_ROTARY_DRAG", "Transmission": "AC_RX7FD_6MT_DRAG", "FinalDriveRatio": "FD_3.31",
                       "CoolantRadiator": "SmallRadiator_110", "Turbocharger": "PS_Boost_315psi",
                       "Tire0": "PerformanceTire_46", "Tire1": "PerformanceTire_46",
                       "Tire2": "PerformanceDragTireStrip", "Tire3": "PerformanceDragTireStrip",
                       "Wheel0": "AC_RX7FD", "Wheel1": "AC_RX7FD", "Wheel2": "AC_RX7FD_REAR", "Wheel3": "AC_RX7FD_REAR",
                       "BrakePad0": "BrakePad_Small_02", "BrakePad1": "BrakePad_Small_02", "BrakePad2": "BrakePad_Small_02", "BrakePad3": "BrakePad_Small_02",
                       "BrakeBalance": "BrakeBalance_F60", "Headlight": "AC_RX7FD_Popup"},
    "popup": {"hinge": [168.81, 71.39], "angle": 52.4, "seconds": 0.5, "note": "AC lights.ksanim: LIGHT_FRONT 0 -> 52.4 deg about the lateral axis through (x 168.81, z 71.39)"},
    "add_shapes": [   # wheelie bar (user 2026-11-13; the AC car has none): two chrome-moly tubes from the rear subframe to small wheels, cross brace
        {"mesh": "Body", "type": "tube", "slot": "Trim", "uv": [0.5, 0.5], "r": 1.6, "seg": 10, "points": [[-150, -32, 22], [-212, -31, 16], [-292, -28, 16]]},
        {"mesh": "Body", "type": "tube", "slot": "Trim", "uv": [0.5, 0.5], "r": 1.6, "seg": 10, "points": [[-150, 32, 22], [-212, 31, 16], [-292, 28, 16]]},
        {"mesh": "Body", "type": "tube", "slot": "Trim", "uv": [0.5, 0.5], "r": 1.3, "seg": 8, "points": [[-286, -28, 16.5], [-286, 28, 16.5]]},
        {"mesh": "Body", "type": "tube", "slot": "Trim", "uv": [0.5, 0.5], "r": 1.1, "seg": 8, "points": [[-212, -31, 16], [-212, 31, 16]]},
        {"mesh": "Body", "type": "cylinder", "slot": T + "BLACK", "uv": [0.5, 0.5], "center": [-294, -33, 14], "axis": [0, -4, 0], "r": 6, "seg": 16},
        {"mesh": "Body", "type": "cylinder", "slot": T + "BLACK", "uv": [0.5, 0.5], "center": [-294, 33, 14], "axis": [0, 4, 0], "r": 6, "seg": 16},
        {"mesh": "Body", "type": "tube", "slot": "Trim", "uv": [0.5, 0.5], "r": 0.8, "seg": 6, "points": [[-294, -37, 14], [-294, 37, 14]]}],
    "drivetrain_note": "Magis is RWD (AC: RWD). Front street tyres, KM3-00 drag radials at the rear like the AC car.",
}
lut = [(500, 160), (1000, 213), (1500, 243), (2000, 269), (2500, 285), (3000, 291), (3500, 297), (3750, 299), (4000, 301), (4500, 304),
       (5000, 307), (5500, 306), (6000, 300), (6500, 293), (7000, 284), (7500, 273), (8000, 259), (8500, 245), (9000, 224)]
mx, lim = 307.0, 9000
curve = [[round(rr / lim, 4), round(t / mx, 4)] for rr, t in lut] + [[5.0, 0.15]]
spec["custom_parts"]["engines"].append({
    "row": "AC_RX7FD_ROTARY_DRAG", "base_row": "I4_150HP", "asset": "AC_RX7FD_ROTARY", "base_asset": "Cars/Parts/Engine/S58",
    "display_name": "Turbo Rotary Drag (8 Second RX-7 FD)", "mass": 130, "cost": 45000, "max_torque_nm": mx, "max_rpm": lim,
    "curve": curve, "curve_note": "AC power.lut (NA, 307 Nm @5000); boost from PS_Boost_315psi (1 + 0.08 x 31.5 = x3.52 = AC 2.5 bar)",
    "physics_from": "Cars/Parts/Engine/I4Sport_150HP", "idle_throttle": 0.00045,
    "sound_cue": {"cue_base": "Cars/Parts/Engine/Sound/s58/SC_V8Engine", "dir": "AC_RX7FD",
                  "loops": [["l1", 1000], ["l2", 1500], ["l3", 3000], ["l4", 4500], ["l5", 5500], ["l6", 7000]],
                  "note": "the FD bank (nzng_mazda_rx7_fd.bank, vgmstream): RX8_EX_IDLE / ONIDLE / ONVERYLOW / ONLOW / ONMID / ONHIGH; rpm from the spectrum (2-rotor firing = 4th half-order); 2 s loops. The do_canito rx7_2 low loops sounded tinny (user)"}})
json.dump(spec, open(ROOT + "cars/ac_rx7fd.json", "w"), indent=1)
print("room mirror rot", round(mpitch, 1), round(myaw, 1), "ratios", spec["custom_parts"]["transmissions"][0]["ratios"])
