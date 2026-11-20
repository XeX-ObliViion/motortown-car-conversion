"""first-pass spec for the AC Honda Civic EG AWD on the Neo (patterns: mw_clio for the Neo, ac_gallardo for AC)"""
import json, math
ROOT = r"C:/Users/noust/OneDrive/Documents/claude/ps2motortown/"
clio = json.load(open(ROOT + "cars/mw_clio.json"))
T = "Tex_AC_EG_"
slots = {
    "EXT_glass": "Glass", "Body_molding": "Bottom", "black_solid": "Bottom", "EXT_plastik": "Bottom", "Honda_chrome": "Trim",
    "ac_Material #2282": "Paint", "glass_mask": "Bottom", "SUSP_green": T + "SUSPG", "SUSP_grey": T + "SUSPGR",
    "supra_exterior_metal": "Bottom", "teplinka": "Defrost", "Body_boot": "Paint", "Body": "Paint", "Body_hood": "Paint",
    "skin_paint": "Paint", "Body_mirror": "Paint", "Lights_int": T + "LIGHTS", "Lights_steklo_nm": T + "LIGHTS",
    "glass_lights": "Glass", "EXT_glass_lights": "Glass", "MIRROR": "Mirror", "Lights_steklo_refl": T + "FRLIGHTS",
    "Interior": T + "INTERIOR", "Interior_stick": T + "INTSTICK", "Plastik_black": "Bottom", "carp": T + "CARPET",
    "int_glass": "Glass", "Plastik_grey": T + "PLASTIC", "leither": T + "LEATHER", "Interior_metall": "Trim",
    "pedal": T + "PEDAL", "leither_white": T + "LEATHERW", "tkan": T + "FABRIC", "INT_leather_SW": T + "STEER",
    "INT_details_SW_metal": T + "STEERD", "INT_details_PLASTIC": T + "STEERD", "INT_seam": T + "SEAM",
    "INT_belts": T + "BELT", "Belt": T + "BELT", "INT_metal": T + "GRAD", "INT_plastic": T + "GRAD", "cargrace": "Trim",
    "INT_interiors_carbon": T + "SEATS", "INT_interiors_seat": T + "SEATS", "INT_chassis": T + "CHASSIS",
    "INT_decals": T + "DECALS", "EXT_calipers": T + "CALIPER", "SUSP_black": "Bottom", "_civicccplastic_detail": T + "BAY",
    "Intercooler_Mishimoto_MLine": T + "INTERCOOLER", "ac_Material #30": T + "TIRE", "ac_Material #34": T + "TREAD",
    "ac_Material #39": T + "RIM", "ac_Material #41": T + "RIM", "ac_Material #38": T + "RIM2", "ac_Material #42": T + "CAP",
    "ac_Material #40": T + "RIMB", "ac_Material #27": T + "SKUNK", "ac_Material #1008": T + "ROTOR",
    "ac_Material #25": T + "PRECISION", "ac_Material #28": T + "TRI",
}
src = {T + "SUSPG": "SUSP_green.dds", T + "SUSPGR": "SUSP_grey.dds", T + "LIGHTS": "lights_lod0.dds", T + "FRLIGHTS": "fr_lights.dds",
       T + "INTERIOR": "interior.dds", T + "INTSTICK": "interior_lod0.dds", T + "CARPET": "carp1.dds", T + "PLASTIC": "Plastic1.png",
       T + "LEATHER": "leather.dds", T + "PEDAL": "pedal.dds", T + "LEATHERW": "leather_white.dds", T + "FABRIC": "Djinsa1.dds",
       T + "STEER": "interiors_ao.dds", T + "STEERD": "interiors_details.dds", T + "SEAM": "seam.dds", T + "BELT": "Cockpit_Belt.png",
       T + "GRAD": "gradients.dds", T + "SEATS": "interiors_ao_st185.dds", T + "CHASSIS": "interiors_objects.dds",
       T + "DECALS": "decals.dds", T + "CALIPER": "details_st185.dds", T + "BAY": "plastic_detail.dds",
       T + "INTERCOOLER": "Intercooler_Mishimoto_MLine_Albedo.png", T + "TIRE": "tyre_hoosier2.png", T + "TREAD": "tread.png",
       T + "RIM": "gray 1.dds", T + "RIM2": "gray.dds", T + "CAP": "mtcap.png", T + "RIMB": "black 1.dds",
       T + "SKUNK": "png-clipart-sticker-bomb-skunk-2-racing-logo.png", T + "ROTOR": "ROTOR0.DDS",
       T + "PRECISION": "precisionturbo.png", T + "TRI": "IlUk66sh.png"}
# tyre-tread centres per wheel (exporter frame: y left); the model's wheels sit 1.5-4 cm asymmetric -> each mesh
# is centred on its own tread and the components are placed symmetrically
hub = {"LF": (131.35, 80.05, 30.05), "RF": (128.35, -78.3, 30.05), "LR": (-123.75, 76.1, 30.05), "RR": (-126.45, -72.15, 30.05)}
neg = lambda h: [round(-h[0], 2), round(-h[1], 2), round(-h[2], 2)]
wheel = lambda key, mesh: {"parts": [{"part": "WHEEL_" + key, "offset": neg(hub[key])}], "reduce": 0.3}
body_parts = [
    "BODY", {"part": "BOOT", "skip_groups": [3], "note": "rear-window defroster lines (teplinka) out"}, "R_BUMP",
    {"part": "R_OPTICA", "groups": [0, 2]}, {"part": "R_OPTICA", "groups": [1, 3, 4], "slot": "TailEG"},
    {"part": "R_OPTICA", "groups": [5, 6], "slot": "SigR"}, {"part": "R_OPTICA", "groups": [7], "slot": "Glass"},
    {"part": "ILR", "slot": "SigR"}, {"part": "REV_L", "slot": "RevEG"},
    {"part": "DOOR", "skip_groups": [4, 5], "note": "mirror glass -> SideMirror_L/R"},
    {"part": "F_OPTICA", "groups": [0, 2, 4]}, {"part": "F_OPTICA", "groups": [1, 5], "slot": "HeadEG"},
    {"part": "F_OPTICA", "groups": [3, 6, 7], "slot": "SigF"}, {"part": "IRF", "slot": "SigF"},
    "SKIRT", {"part": "COCKPIT_HR", "skip_groups": [21, 22], "note": "belts-on (worn) set out; the off set stays"},
    "STEER_HR", "SUSP_LR", "SUSP_RR", "BAY004", "INTERCOOLER_MISHIMOTO_MLINE", "FRONT_BUMPER",
    "OBJECT140", "OBJECT141", "OBJECT143", "OBJECT144", "RE", "PRECISION", "PRECISION2", "SKUNK1", "SKUNK2", "TRI"]
# room mirror aim (skill: eye ray reflects straight back, ~2 deg up): n || r - d, X = -n
eye, mir = (-36.0, 31.8, 100.0), (19.4, 0.0, 114.0)
d = [m - e for m, e in zip(mir, eye)]; dl = math.sqrt(sum(x * x for x in d)); d = [x / dl for x in d]
r = [-1.0, 0.0, 0.035]; rl = math.sqrt(sum(x * x for x in r)); r = [x / rl for x in r]
n = [a - b for a, b in zip(r, d)]; nl = math.sqrt(sum(x * x for x in n)); X = [-x / nl for x in n]
yaw = math.degrees(math.atan2(X[1], X[0])); pitch = math.degrees(math.asin(X[2]))
spec = {
    "car": "AC_CIVICEG", "display_name": "Honda Civic EG AWD (8 Second Shootout)", "prefix": "AC_CIVICEG",
    "base_vehicle": "Neo", "base_wheel": "Vista", "base_wheel_mesh": "Micky", "default_slot": "Bottom", "source_scale": 100.0,
    "geometry_dir": "C:/Users/noust/nfs-work/ac/eg_awd/geo", "texture_dir": "C:/Users/noust/nfs-work/ac/eg_awd/textures",
    "out_dir": "C:/Users/noust/mt-work/build/AC_CIVICEG/meshes", "cost": 95000, "wheel_part": True,
    "wheel_display_name": "Drag Wheels (8 Second Civic EG)",
    "texture_slots": slots, "texture_sources": src,
    "meshes": {
        "Body": {"parts": body_parts, "reduce": 0.4, "drop_slots": ["Defrost", "Tex_AC_EG_CALIPER"],
                 "drop_boxes": [[15, -14, 108, 24, 14, 120]], "drop_note": "AC static room mirror (the game's RoomMirror goes there)"},
        "SideMirror_L": {"parts": [{"part": "DOOR", "groups": [5], "slot": "Mirror"}], "planar_uv": {}},
        "SideMirror_R": {"parts": [{"part": "DOOR", "groups": [4], "slot": "Mirror"}], "planar_uv": {"flip_u": True}},
        "Wheel_L": wheel("LF", "L"), "Wheel_R": wheel("RF", "R"), "Wheel_RL": wheel("LR", "RL"), "Wheel_RR": wheel("RR", "RR")},
    "rear_wheel_meshes": True,
    "mesh_names": {"Wheel_L": "AC_CIVICEG_L", "Wheel_R": "AC_CIVICEG_R", "Wheel_RL": "AC_CIVICEG_REAR_L",
                   "Wheel_RR": "AC_CIVICEG_REAR_R", "SteeringWheel": "AC_CIVICEG"},
    "final_slot_names": {"Paint": "Body_01", "Glass": "Window", "HeadEG": "HeadLight", "TailEG": "TailLight", "RevEG": "ReverseLight",
                         "Signal_L_F": "LeftSignalLight", "Signal_R_F": "RightSignalLight",
                         "Signal_L_R": "LeftSignalLight", "Signal_R_R": "RightSignalLight"},
    "mirror_sockets": {"SideMirror_L": "SideMirror_L", "SideMirror_R": "SideMirror_R"},
    "wheels": {"front_x": 129.85, "rear_x": -125.1, "half_track": 79.2, "rear_half_track": 74.1, "z": 30.5, "rear_z": 30.5,
               "radius": 30.05, "auto_arches": False},
    "collision_boxes": [{"center": [6, 0, 38], "size": [400, 168, 46]}, {"center": [-30, 0, 100], "size": [200, 140, 56]}],
    "strip_part_slots": ["FrontBumper", "RearBumper", "Bonnet", "Fender", "Headlight", "SideSkirt", "Trunk", "RearWing"],
    "blueprint": {
        "seats": {"DriverSeat_GEN_VARIABLE": [-36, 31.8, 37], "PassengerSeat1_GEN_VARIABLE": [-36, -31.8, 37],
                  "PassengerSeat2_GEN_VARIABLE": [-36, -31.8, 37], "PassengerSeat3_GEN_VARIABLE": [-36, 31.8, 37]},
        "cockpit_camera": [eye[0], eye[1], eye[2]],
        "components": {"RoomMirror_GEN_VARIABLE": list(mir), "CabinDomeLightSlot_GEN_VARIABLE": [-40, 0, 120],
                       "FrontDomeLightSlot_GEN_VARIABLE": [8, 0, 120],
                       "HeadLight_Left_GEN_VARIABLE": [203, -48, 55], "HeadLight_Right_GEN_VARIABLE": [203, 48, 55],
                       "BlinkerLight_01_GEN_VARIABLE": [193, 72, 55], "BlinkerLight_02_GEN_VARIABLE": [193, -72, 55],
                       "TaliLight_01_GEN_VARIABLE": [-193, -66, 72], "TaliLight_02_GEN_VARIABLE": [-193, 66, 72],
                       "ReverseLight_01_GEN_VARIABLE": [-190, -50, 76], "ReverseLight_02_GEN_VARIABLE": [-190, 50, 76]},
        "component_rotations": {"RoomMirror_GEN_VARIABLE": [round(pitch, 1), round(yaw, 1), 0]},
        "hide_meshes": [], "keep_body_materials": 1, "body_mass": 855},
    "extract": {"SteeringWheel": {"from": "Body", "center": [24.1, 31.8, 71.1], "radius": 19, "x_range": [10, 36],
                                  "uv_box": [-99, -99, 99, 99], "uv_slots": [T + "STEER", T + "STEERD", T + "SEAM"],
                                  "socket": "SteeringWheel", "align_x": True, "reduce": 0.5}},
    "signal_lamps": [{"tag": "_F", "from": "SigF", "box": [100, -100, 0, 260, 100, 120]},
                     {"tag": "_R", "from": "SigR", "box": [-260, -100, 0, -100, 100, 120]}],
    "lamp_slots": {"HeadEG": {"kind": "head", "texture_slot": T + "FRLIGHTS"}, "TailEG": {"kind": "tail", "texture_slot": T + "LIGHTS"},
                   "RevEG": {"kind": "reverse", "texture_slot": T + "LIGHTS"},
                   "Signal_L_F": {"kind": "signal", "texture_slot": T + "FRLIGHTS"}, "Signal_R_F": {"kind": "signal", "texture_slot": T + "FRLIGHTS"},
                   "Signal_L_R": {"kind": "signal", "texture_slot": T + "LIGHTS"}, "Signal_R_R": {"kind": "signal", "texture_slot": T + "LIGHTS"}},
    "dashboard": {"sockets": [
        {"name": "Niddle_RPM", "loc": [58.81, 21.43, 78.83], "rot": [0, -90, -55.2]},
        {"name": "Niddle_Speed", "loc": [59.10, 31.14, 79.60], "rot": [0, -90, -55.2]},
        {"name": "Niddle_Fuel", "loc": [59.05, 38.28, 79.68], "rot": [0, -90, -55.2]},
        {"name": "Niddle_Temp", "loc": [61.5, 38.28, 78.0], "rot": [0, -90, -55.2], "note": "AC has no temp needle: tucked behind the face"}],
        "note": "sockets = AC needle hubs (ARROW_* dummies); dial face tilted 34.8 deg up -> roll -55.2"},
    "texture_upscale": {T + "INTERIOR": 4},
    "gauge_style": {"face_color": [8, 8, 8], "ink": [240, 240, 240], "minor_ink": [200, 200, 200], "red_color": [225, 30, 25],
                    "font_file": "arialbd.ttf"},
    "gauge_faces": {T + "INTERIOR": [
        {"center": [0.7603, 0.2344], "face": [0.7603, 0.2344, 0.235], "radius": 0.2, "rotate": 0, "min": 0, "max": 120,
         "text_step": 20, "line_step": 10, "start": 140, "end": 400, "font": 0.09, "captions": [["MPH", 0.3, 90]], "caption_font": 0.08,
         "note": "JDM km/h art (to 180) redrawn in mph"},
        {"center": [0.7744, 0.7005], "face": [0.7744, 0.7005, 0.215], "radius": 0.185, "rotate": 0, "min": 0, "max": 10,
         "text_step": 1, "line_step": 0.5, "start": 140, "end": 400, "red_from": 9, "font": 0.1,
         "captions": [["x1000", 0.3, 90]], "caption_font": 0.07, "note": "AC art 0-9k; redrawn on the game sweep to 10k (limiter 9500)"}]},
    "gauge_ranges": {"RPM": {"max": 10}, "Speed": {"max": 120, "value_scale": 1.609344}},
    "needle_color": [240, 90, 20], "needle_width": 0.4,
    "masked_texture_slots": [T + "PRECISION", T + "TRI", T + "SKUNK", T + "INTERCOOLER"],
    "performance_source": "AC data: TOTALMASS 1300, AWD 50/50, 6 gears 2.58/2.07/1.67/1.40/1.21/1.05 R-2.449 FINAL 3.3, LIMITER 9500, idle 850; power.lut NA 393 Nm @6250 (K20); TURBO_0 1.75 bar ref 3200",
    "custom_parts": {
        "transmissions": [{"row": "AC_CIVICEG_6SEQ_DRAG", "base_row": "6SpeedSportsLP670", "asset": "AC_CIVICEG_6SEQ",
                           "base_asset": "Cars/Parts/Transmission/Manual6SpeedSports_LP670", "display_name": "6-Speed Sequential Drag (8 Second Civic EG)",
                           "cost": 8000, "mass": 60,
                           "ratios": {"R": -2.442, "1": 2.572, "2": 2.064, "3": 1.665, "4": 1.396, "5": 1.206, "6": 1.047},
                           "note": "AC final 3.3 folded in (FD_3.31)"}],
        "engines": []},
    "part_overrides": {"Engine": "AC_CIVICEG_K20_DRAG", "Transmission": "AC_CIVICEG_6SEQ_DRAG", "FinalDriveRatio": "FD_3.31",
                       "CoolantRadiator": "SmallRadiator_110", "Turbocharger": "PS_Boost_220psi",
                       "Tire0": "PerformanceDragTireStrip", "Tire1": "PerformanceDragTireStrip", "Tire2": "PerformanceDragTireStrip", "Tire3": "PerformanceDragTireStrip",
                       "Wheel0": "AC_CIVICEG", "Wheel1": "AC_CIVICEG", "Wheel2": "AC_CIVICEG", "Wheel3": "AC_CIVICEG",
                       "BrakePad0": "BrakePad_Small_02", "BrakePad1": "BrakePad_Small_02", "BrakePad2": "BrakePad_Small_02", "BrakePad3": "BrakePad_Small_02"},
    "drivetrain_note": "Neo is AWD from the factory (the EG is AWD in AC: FRONT_SHARE 50)",
}
# engine: AC power.lut is the NA torque; boost from PS_Boost_220psi (1 + 0.08 x 22 = x2.76 = AC TURBO_0 1.75 bar)
lut = [(0, 20), (500, 255), (1000, 300), (1500, 310), (2000, 320), (2500, 326), (3000, 333), (3500, 346), (4000, 354), (4500, 358),
       (5000, 361), (5500, 362), (5850, 365), (6050, 390), (6250, 393), (6500, 391), (7000, 385), (7500, 388), (8000, 382), (8500, 370), (9000, 357)]
mx, lim = 393.0, 9500
curve = [[round(r / lim, 4), round(t / mx, 4)] for r, t in lut if r > 0] + [[1.0, 0.88], [5.0, 0.15]]
spec["custom_parts"]["engines"].append({
    "row": "AC_CIVICEG_K20_DRAG", "base_row": "I4_150HP", "asset": "AC_CIVICEG_K20", "base_asset": "Cars/Parts/Engine/S58",
    "display_name": "K20 Turbo Drag (8 Second Civic EG)", "mass": 150, "cost": 45000, "max_torque_nm": mx, "max_rpm": lim,
    "curve": curve, "curve_note": "AC power.lut (NA, 393 Nm @6250); boost from PS_Boost_220psi (x2.76 = AC 1.75 bar)",
    "physics_from": "Cars/Parts/Engine/I4Sport_150HP", "sound_cue": None})
json.dump(spec, open(ROOT + "cars/ac_civiceg.json", "w"), indent=1)
print("room mirror rot", round(pitch, 1), round(yaw, 1))
