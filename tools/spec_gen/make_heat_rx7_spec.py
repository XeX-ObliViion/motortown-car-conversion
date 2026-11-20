"""first-pass spec for the NFS Heat Mazda RX-7 Spirit R (car_mazda_rx7spiritr_2002) on the Magis, with every Heat kit set
that has a Motor Town slot (front/rear bumper, skirts, hood, wing, fenders) + native pop-ups (Panther route).
Patterns: heat_skyline.json (Heat materials, kits), ac_rx7fd (Magis, RHD RX-7, pop-ups, seat calibration).
Source frame = heat_dae output (x fwd, y LEFT, z up, metres -> source_scale 100). Heat's origin sits ~19 cm above the
ground (AC RX-7 roof 124 vs Heat 105); Motor Town only needs wheels/body consistent, so the frame is used as is.
Car-space values for Motor Town (sockets, boxes, seats, components) use y RIGHT = -y_source."""
import json, math, os, re
ROOT = r"C:/Users/noust/OneDrive/Documents/claude/ps2motortown/"
SRC = r"C:/Users/noust/nfs-work/db/heat/RX7/"
CAR = "HEAT_RX7"
geo = sorted(f[len(CAR) + 1:-6] for f in os.listdir(SRC + "geo") if f.endswith("_A.dae"))
sets = lambda part: [g[len(part) + 1:] for g in geo if g.startswith(part + "_SET") and not re.search(r"_P\d+$", g)]

slots = {
    "M_Carpaint_Max": "Paint", "M_CarPaint_Max": "Paint", "M_CarpaintNormal_Max": "Paint", "M_CarPaintNormal_Max": "Paint",
    "M_Chassis_Max": "Bottom", "M_Opaque_PlasticRoughBlack_Max": "Bottom", "M_Opaque_PlasticSmoothBlack_Max": "Bottom",
    "M_GrilleA_Max": "Bottom", "M_LicensePlate_Max": "Bottom", "M_CarPaint_Trim_CarbonA_Max": "Bottom", "M_GenericDetail_Max": "Bottom",
    "M_InteriorTiled_Max": "Tex_InteriorTiled_D", "M_InteriorTiledSimple_Max": "Tex_InteriorTiledSimple_D",
    "M_Glass_WindowSurroundRight_Max": "Bottom", "M_Glass_WindowSurroundLeft_Max": "Bottom", "M_Glass_WindowSurround_Max": "Bottom",
    "M_Glass_WindowSurroundRear_Max": "Bottom", "M_Generics_BCLSpoilers_Max": "Bottom",
    "M_Opaque_NickelRough_Max": "Trim", "M_Opaque_NickelSmooth_Max": "Trim", "M_Opaque_AluminumSmooth_Max": "Trim", "M_Opaque_ChromeSmooth_Max": "Trim",
    "M_Interior_Max": "Tex_Interior_D", "M_Engine_Max": "Tex_Engine_D", "M_Badge_Max": "Tex_Badge_D",
    "M_Light_Max": "Tex_Light_SetA_D", "M_LightBucket_Max": "Tex_Light_SetA_D",
    "M_Light_HeadlightSetB_Max": "Tex_Light_HeadLights_SetB_D", "M_LightBucket_HeadLightSetB_Max": "Tex_Light_HeadLights_SetB_D",
    "M_Light_HeadlightSetF_Max": "Tex_Light_HeadLights_SetF_D", "M_Light_TaillightSetF_Max": "Tex_Light_TailLights_SetF_D",
    "M_Rim_Main_Max": "Tex_RimGun", "M_RimBadge_Max": "Tex_RimBadge_D", "M_GlassOpaque_Mirror_Max": "Mirror",
    "M_Glass_WindowFront_Max": "Glass", "M_Glass_WindowRear_Max": "Glass", "M_Glass_WindowSide_Max": "Glass", "M_Glass_Max": "Glass",
    "M_SpoilerGlass_Max": "Glass",
    "M_LightGlassNormal_Orange_Max": "Tex_LensAmber", "M_LightGlass_Orange_Max": "Tex_LensAmber",
    "M_LightGlass_Red_Max": "Tex_LensRed", "M_LightGlassNormal_Red_Max": "Tex_LensRed",
    "M_LightGlassNormal_OuterRed_Max": "LampGlass", "M_LightGlassNormal_Clear_Max": "LampGlass", "M_LightGlass_Clear_Max": "LampGlass",
    "M_LightGlassNormal_HeadLightClearSetB_Max": "LampGlass", "M_LightGlass_HeadLightClearSetB_Max": "LampGlass",
    "M_LightGlass_TailLightClearSetF_Max": "LampGlass", "M_Tire_Max": "Bottom", "M_Caliper_Max": "Bottom", "M_CaliperBadge_Max": "Bottom",
}
LIGHT = "Tex_Light_SetA_D"
TEXD = SRC + "tex/Car_Mazda_RX7SpiritR_2002_Light_SetA_D.png"; TEXE = SRC + "tex/Car_Mazda_RX7SpiritR_2002_Light_SetA_E.png"
# wheel centres from the arch liners (circle fit): front x 122.3 z 16.9, rear x -122.6 (wheelbase 2449 ~ real 2425)
TIRE = {"part": "_RACE01_FL", "geo": "~/nfs-work/db/heat/TIRES/geo", "prefix": "TIRE", "note": "Heat shared tyre (race01), r 31.6 x 26.8 cm"}
pod_off = lambda s: [153.0, -58.3 * s, 53.5]   # 1.5 cm lower: closed pods stood slightly proud of the hood (user)   # offset is applied in the Motor Town frame (y right): L pod -> y -58.3 (user: pods were swapped)    # Heat models the pods at their hinge (rear top edge); AC RX-7 pod spot - (8.2, 0, 19)
body_parts = ["BODY_P0", "BODY_P1", "BODY_P2", "BODY_P3",
              # the steering wheel (Heat composite part 4) on its own slot so the extract takes only it: the hub cylinder
              # also caught the gauge cluster behind it (gauges vanished into the wheel mesh, user 2026-11-13)
              {"part": "BODY_P4", "slot": "Tex_HeatSteer"}, "BODY_P5", "BODY_P6",
              "BODY_P7", "BODY_P8", "BODY_P9", "BODY_P10", "BODY_P11", "BODY_P12",       # Magis: doors + door glass in Body
              "FENDERSCHASSISF_SETA", "FENDERSCHASSISR_SETA", "BOOT_SETA", "EXHAUSTS_SETA", "TAILLIGHTS_SETA",
              "BUMPERCHASSISR_SETA", "MIRRORBASEL_SETA", "MIRRORBASER_SETA",
              {"part": "MIRRORL_SETA", "skip_groups": [2]}, {"part": "MIRRORR_SETA", "skip_groups": [2]}]
meshes = {
    "Body": {"parts": body_parts, "drop_slots": ["LampGlass"], "reduce": 0.6,
             "drop_boxes": [[3, -15, 84, 13, 15, 93.5]], "drop_note": "Heat static rear-view mirror (the game RoomMirror goes there)",
             "uv_split": [{"from": "Tex_Interior_D", "to": "ClusterGlass", "drop": True, "box": [0.70, -0.01, 1.0, 0.19], "box3d": [20, 14, 44, 25, 64, 74],
                           "note": "Heat's gauge glass (grey texture patch, glass shader in Heat): opaque here, it hid the dials"},
                          {"from": "Tex_Interior_D", "to": "Gauges", "box": [-0.01, -0.01, 0.7, 0.6], "box3d": [16, 16, 44, 36, 62, 74]}]},
    "SideMirror": {"parts": [{"part": "MIRRORL_SETA", "slot": "Mirror", "groups": [2]}], "recenter": True, "planar_uv": {},
                   "counter_rotate": {"rot": [-3.7, -0.4, 0]}},
    "RightSideMirror": {"parts": [{"part": "MIRRORR_SETA", "slot": "Mirror", "groups": [2], "mirror": True}], "recenter": True, "planar_uv": {},
                        "counter_rotate": {"rot": [-6.9, -13.0, 0], "mirror_frame": True}},
    "Popup": {"parts": [{"part": "ANIMATEDHEADLIGHTL_SETA", "offset": pod_off(1), "groups": [0, 1]},
                        {"part": "ANIMATEDHEADLIGHTL_SETA", "offset": pod_off(1), "groups": [2], "slot": "HeadPod"},
                        {"part": "ANIMATEDHEADLIGHTR_SETA", "offset": pod_off(-1), "groups": [0, 1]},
                        {"part": "ANIMATEDHEADLIGHTR_SETA", "offset": pod_off(-1), "groups": [2], "slot": "HeadPod"}],
              "drop_slots": ["LampGlass"], "note": "Heat pop-up pods (stock SETA), closed; hinge = their own origin"},
    "Wheel_L": {"parts": [{"part": "WHEELFL_SETA"}, TIRE]},
    "Wheel_R": {"parts": [{"part": "WHEELFL_SETA", "mirror": True}, dict(TIRE, mirror=True)]},
}
aero = []
def kit(slot, label, setname, parts, offset=None):
    mesh = "Aero_%s_%s" % (slot, "KIT00" if setname == "SETA" else setname)
    meshes[mesh] = {"parts": [dict(part=p, **({"offset": offset} if offset else {})) for p in parts], "aero": True, "drop_slots": ["LampGlass"]}
    if slot == "RearBumper":   # its lamps are the reverse lights: no red lens over them
        meshes[mesh]["uv_split"] = [{"from": "Tex_LensRed", "to": "x", "drop": True, "box": [-9, -9, 9, 9]}]
    nice = "Stock" if setname == "SETA" else re.sub(r"^SET([A-Z]+)(?:_ALT([A-Z]))?$", lambda m: "Set %s%s" % (m.group(1), " (alt %s)" % m.group(2) if m.group(2) else ""), setname)
    aero.append({"row": "%s_%s_%s" % (CAR, slot, "KIT00" if setname == "SETA" else setname), "slot": slot, "part_type": slot,
                 "mesh": mesh, "display_name": "%s %s" % (nice, label)})
for s in sets("BUMPERF"):
    ch = "BUMPERCHASSISF_" + s if ("BUMPERCHASSISF_" + s) in geo else "BUMPERCHASSISF_SETA"
    kit("FrontBumper", "Front Bumper", s, ["BUMPERF_" + s, ch])
for s in sets("BUMPERR"):
    kit("RearBumper", "Rear Bumper", s, ["BUMPERR_" + s])
for s in sets("SKIRTS"):
    kit("SideSkirt", "Side Skirts", s, ["SKIRTS_" + s])
for s in sets("HOOD"):
    kit("Bonnet", "Hood", s, ["HOOD_" + s])
WING = [-195, 0, 70]   # Body socket RearWing on the boot lid; Heat spoilers are modelled in car space -> offset by -socket
for s in sets("SPOILER"):
    kit("RearWing", "Wing", s, ["SPOILER_" + s], offset=[-WING[0], 0, -WING[2]])
for s in sets("FENDERFL"):
    if "FENDERFR_" + s in geo:
        sr = "FENDERSR_" + s.split("_")[0] if ("FENDERSR_" + s.split("_")[0]) in geo else "FENDERSR_SETA"
        kit("Fender", "Fenders", s, ["FENDERFL_" + s, "FENDERFR_" + s, sr])

eye, mir = (-41.2, 39.9, 85.0), (7.0, 0.0, 89.0)   # AC RX-7 calibrated eye/room mirror - (8.2, 0, 19); re-checked from the cushion below
d = [m - e for m, e in zip(mir, eye)]; dl = math.sqrt(sum(x * x for x in d)); d = [x / dl for x in d]
r = [-1.0, 0.0, 0.017]; rl = math.sqrt(sum(x * x for x in r)); r = [x / rl for x in r]
n = [a - b for a, b in zip(r, d)]; nl = math.sqrt(sum(x * x for x in n)); X = [-x / nl for x in n]
myaw = math.degrees(math.atan2(X[1], X[0])); mpitch = math.degrees(math.asin(X[2]))
spec = {
    "car": CAR, "display_name": "Mazda RX-7 Spirit R (NFS Heat)", "prefix": CAR,
    "base_vehicle": "Magis", "default_slot": "Bottom", "source_scale": 100.0,
    "geometry_dir": SRC + "geo", "texture_dir": SRC + "tex", "out_dir": "C:/Users/noust/mt-work/build/%s/meshes" % CAR,
    "cost": 85000, "wheel_part": True, "wheel_display_name": "Spirit R Wheels (NFS Heat)",
    "texture_slots": slots, "texture_sources": {"Tex_HeatSteer": "Car_Mazda_RX7SpiritR_2002_Interior_D.png"}, "masked_texture_slots": ["Tex_Badge_D", "Tex_RimBadge_D"], "paintable_texture_slots": ["Tex_RimGun"],
    "meshes": meshes, "aero_parts": aero,
    "mesh_names": {"Wheel_L": CAR + "_L", "Wheel_R": CAR + "_R", "SteeringWheel": CAR},
    "final_slot_names": {"Paint": "Body", "Glass": "Window", "HeadPod": "HeadLight", "HeadLamp": "HeadLight", "TailLamp": "TailLight", "ReverseLamp": "ReverseLight",
                         "Signal_L_F": "LeftSignalLight", "Signal_R_F": "RightSignalLight", "Signal_L_R": "LeftSignalLight",
                         "Signal_R_R": "RightSignalLight", "TailLens": "TailLight", "SigLens_L_F": "LeftSignalLight", "SigLens_R_F": "RightSignalLight"},
    "mirror_components": {"LeftSideMirror_GEN_VARIABLE": "SideMirror", "RightSideMirror_GEN_VARIABLE": "RightSideMirror:mirror"},
    "mirror_meshes": {"RightSideMirror_GEN_VARIABLE": "RightSideMirror"},
    "wheels": {"front_x": 122.3, "rear_x": -122.6, "half_track": 73.0, "z": 14.0, "rear_z": 15.0, "radius": 31.6, "auto_arches": False,
               "note": "hubs from the arch-liner circle fit (Heat frame, hub z ~16.9)"},
    "collision_boxes": [{"center": [-15, 0, 22], "size": [412, 172, 46]}, {"center": [-40, 0, 80], "size": [180, 130, 40]}],
    "strip_part_slots": ["RearWing"],
    "not_optional_part_types": ["Bonnet", "Fender", "FrontBumper", "RearBumper", "SideSkirt"],
    "sockets": {"Body": [{"name": "Exhaust_Left", "loc": [-218, 50, 9], "rot": [0, 180, 0]},
                         {"name": "Exhaust_Right", "loc": [-218, 50, 9], "rot": [0, 180, 0]},
                         {"name": "RearWing", "loc": WING, "rot": [0, 0, 0]},
                         {"name": "TaxiRoofSign", "loc": [-55, 0, 108], "rot": [0, 0, 0]},
                         {"name": "TrailerHitch", "loc": [-224, 0, 10], "rot": [0, 0, 0]}]},
    # lamps: Heat shares one lamp texture (Light_SetA) -> split by position; lens colour is in the glass (R34 lesson)
    # lamps: Heat's lamp textures carry a function mask (_E: A turn, B reverse, R brake, G running) -> ps_to_mt lamp_masks
    # (position boxes put the RX-7's tail assembly in the wrong slots, user 2026-11-13); lens colour stays in the glass
    "lamp_masks": [{"from": [src_], "mask": SRC + "tex/Car_Mazda_RX7SpiritR_2002_%s_E.png" % e,
                    "threshold": 150, "slots": {"turn": "Signal_{side}_{end}", "reverse": "HeadLamp", "brake": "HeadLamp", "run_front": "HeadLamp", "run_rear": "TailLamp"}}
                   for src_, e in ((LIGHT, "Light_SetA"), ("Tex_Light_HeadLights_SetB_D", "Light_HeadLights_SetB"),
                                   ("Tex_Light_HeadLights_SetF_D", "Light_HeadLights_SetF"), ("Tex_Light_TailLights_SetF_D", "Light_TailLights_SetF"))],
    # rear by position (Heat has no turn function; its diffuse shows the amber turn bulb in the OUTER round = '99-spec FD):
    # centre garnish lights = reverse, outer rounds = turn, inner rounds = brake/tail, rear bumper lamps + rear side
    # markers = red tail glow; front fender side markers = amber signals. The mask then splits the front bumper lamps.
    # rear lamps: ONLY the bulbs light (user 2026-11-13), found by Heat's lamp mask (R brake bulbs, G running) and the
    # amber turn bulb in Heat's diffuse; AC RX-7 layout: outer round = turn, rounds = brake/tail, rear bumper bulbs = reverse
    "bulb_rules": [
        {"from": LIGHT, "diffuse": TEXD, "amber": True, "box": [-232, -80, 45, -185, 80, 72], "to": "Signal_{side}_R", "note": "amber turn bulb, outer round"},
        {"from": LIGHT, "mask": TEXE, "ch": "r", "min": 100, "box": [-232, -80, 45, -185, 80, 72], "to": "TailLamp", "note": "brake bulbs (middle + outer rounds)"},
        {"from": LIGHT, "mask": TEXE, "ch": "r", "min": 25, "box": [-232, -47, 45, -185, -30, 72], "to": "TailLamp", "note": "inner round glow"},
        {"from": LIGHT, "mask": TEXE, "ch": "r", "min": 25, "box": [-232, 30, 45, -185, 47, 72], "to": "TailLamp"},
        {"from": LIGHT, "mask": TEXE, "ch": "g", "min": 150, "box": [-240, -75, -10, -205, 75, 45], "to": "ReverseLamp", "note": "rear bumper bulbs = reverse"},
        {"from": LIGHT, "mask": TEXE, "ch": "g", "min": 40, "box": [-240, -100, -10, -100, -75, 45], "to": "TailLamp", "note": "rear side markers"},
        {"from": LIGHT, "mask": TEXE, "ch": "g", "min": 40, "box": [-240, 75, -10, -100, 100, 45], "to": "TailLamp"}],
    "slot_boxes": [
        {"from": LIGHT, "to": "Signal_L_F", "box": [30, -96, 34, 180, -82, 48], "note": "front side markers"},
        {"from": LIGHT, "to": "Signal_R_F", "box": [30, 82, 34, 180, 96, 48]},
        # coloured lenses stay plain coloured glass: only bulbs light (user 2026-11-13)
    ],
    "lamp_slots": {"HeadPod": {"kind": "head", "texture_slot": LIGHT}, "HeadLamp": {"kind": "head", "texture_slot": LIGHT}, "TailLamp": {"kind": "tail", "texture_slot": "Tex_LensRed"},
                   "ReverseLamp": {"kind": "reverse", "texture_slot": LIGHT},
                   "Signal_L_F": {"kind": "signal", "texture_slot": LIGHT}, "Signal_R_F": {"kind": "signal", "texture_slot": LIGHT},
                   "Signal_L_R": {"kind": "signal", "texture_slot": "Tex_LensAmber"}, "Signal_R_R": {"kind": "signal", "texture_slot": "Tex_LensAmber"},
                   "TailLens": {"kind": "tail", "texture_slot": "Tex_LensRed"},
                   "SigLens_L_F": {"kind": "signal", "texture_slot": "Tex_LensAmber"}, "SigLens_R_F": {"kind": "signal", "texture_slot": "Tex_LensAmber"}},
    "blueprint": {
        "seats": {"DriverSeat_GEN_VARIABLE": [-38.2, 39.9, 3.0], "PassengerSeat1_GEN_VARIABLE": [-38.2, -39.9, 3.0]},
        "cockpit_camera": list(eye),
        "components": {"RoomMirror_GEN_VARIABLE": list(mir), "FrontDomeLightSlot_GEN_VARIABLE": [-33, 0, 98],
                       "HeadLight_Left_GEN_VARIABLE": [182, -58, 42], "HeadLight_Right_GEN_VARIABLE": [182, 58, 42],
                       "BlinkerLight_01_GEN_VARIABLE": [198, 70, 28], "BlinkerLight_02_GEN_VARIABLE": [198, -70, 28],
                       "TaliLight_01_GEN_VARIABLE": [-205, -55, 57], "TaliLight_02_GEN_VARIABLE": [-205, 55, 57]},
        "component_rotations": {"RoomMirror_GEN_VARIABLE": [round(mpitch, 1), round(myaw, 1), 0],
                                "LeftSideMirror_GEN_VARIABLE": [-3.7, -0.4, 0], "RightSideMirror_GEN_VARIABLE": [-6.9, -13.0, 0]},   # tools/aim_mirrors.py from the Heat eye (the AC RX-7 values aimed at the sky / into the car)
        "keep_body_materials": 1, "body_mass": 825, "room_mirror_aim_z": 0.017,
        "cdo_names": {"BodyMaterialName": "Body"}},   # pods painted natively (Panther route; Magis paint slot = Body)
    "extract": {"SteeringWheel": {"from": "Body", "center": [12.5, 40.0, 56.5], "radius": 18.5, "x_range": [-4, 30],
                                  "uv_box": [-99, -99, 99, 99], "uv_slots": ["Tex_HeatSteer"],
                                  "socket": "SteeringWheel", "align_x": True}},
    "dashboard": {"sockets": [
        {"name": "Niddle_RPM", "loc": [25.93, 38.86, 61.43], "rot": [0, -90, -90]},
        {"name": "Niddle_Speed", "loc": [26.57, 49.85, 58.62], "rot": [0, -90, -90]},
        {"name": "Niddle_Fuel", "loc": [24.45, 26.35, 57.89], "rot": [0, -90, -90]},
        {"name": "Niddle_Temp", "loc": [24.91, 32.32, 55.18], "rot": [0, -90, -90]}],
        "parent_socket": "SteeringWheel",
        "note": "dial centres of Interior_D mapped onto BODY_P3 (vertical face, normal -x); sockets 0.4 cm proud"},
    "gauge_style": {"face_color": [30, 30, 32], "ink": [240, 240, 236], "minor_ink": [200, 200, 200], "red_color": [225, 30, 25],
                    "font_file": "arialbd.ttf"},
    "gauge_faces": {"Tex_Interior_D": [
        {"center": [0.4346, 0.381], "face": [0.4346, 0.381, 0.18], "radius": 0.16, "rotate": 0, "min": 0, "max": 9, "text_step": 1,
         "line_step": 0.5, "start": 140, "end": 400, "red_from": 8, "font": 0.14, "captions": [["x1000 r/min", 0.32, 90]], "caption_font": 0.07,
         "note": "Heat art 0-9 with a painted needle -> redrawn on the game's sweep"},
        {"center": [0.127, 0.342], "face": [0.127, 0.342, 0.13], "radius": 0.115, "rotate": 0, "min": 0, "max": 160, "text_step": 20,
         "line_step": 10, "start": 140, "end": 400, "font": 0.13, "captions": [["MPH", 0.32, 90]], "caption_font": 0.09, "note": "JDM 180 km/h art -> mph"},
        {"center": [0.156, 0.098], "face": [0.156, 0.098, 0.09], "radius": 0.075, "rotate": 0, "min": 0, "max": 1, "text_step": 1,
         "line_step": 0.25, "start": 210, "end": 330, "font": 0.3, "labels": {"0": "E", "1": "F"}},
        {"center": [0.571, 0.098], "face": [0.571, 0.098, 0.09], "radius": 0.075, "rotate": 0, "min": 40, "max": 120, "text_step": 80,
         "line_step": 20, "start": 210, "end": 330, "font": 0.3, "labels": {"40": "C", "120": "H"}, "red_from": 110}]},
    "gauge_ranges": {"RPM": {"max": 9}, "Speed": {"max": 160, "value_scale": 1.609344}},
    "needle_color": [240, 40, 25], "needle_width": 0.35,
    "emissive_slots": {"Gauges": {"texture_slot": "Tex_Interior_D", "glow": 1.5, "mask_from_gauges": True},
                       "NeedleGlow": {"texture_slot": "Tex_RX7_NEEDLE", "glow": 2.0}},
    "uv_split_note": "Body uv_split moves the cluster faces of Tex_Interior_D to the Gauges slot",
    "popup": {"hinge": [160.6, 50.9], "angle": 52.4, "seconds": 0.5, "hinge_note": "AC RX-7 hinge relative to its pod (8.6 cm in from the rear edge, 3.1 below the top); Heat origin (rear top edge) lifted the pods out of their openings",
              "note": "Heat pods hinge at their origin (rear top edge); opening angle from the AC RX-7 (lights.ksanim 52.4 deg)"},
    "performance_source": "real Mazda RX-7 Spirit R Type A (2002): 13B-REW sequential twin turbo 280 PS @6500, 314 Nm @5000, redline 8000, 1270 kg, 5MT 3.483/2.015/1.391/1.000/0.719 R3.288 final 4.100, RWD",
    "custom_parts": {
        "transmissions": [{"row": CAR + "_5MT", "base_row": "6SpeedSportsLP670", "asset": CAR + "_5MT",
                           "base_asset": "Cars/Parts/Transmission/Manual6SpeedSports_LP670", "display_name": "5-Speed (RX-7 Spirit R)",
                           "cost": 6000, "mass": 55,
                           "ratios": {g: round(v * 4.1 / 3.31, 3) for g, v in {"R": -3.288, "1": 3.483, "2": 2.015, "3": 1.391, "4": 1.0, "5": 0.719}.items()},
                           "note": "real final 4.100 folded in (game row FD_3.31)"}],
        "engines": []},
    "part_overrides": {"Engine": CAR + "_13B", "Transmission": CAR + "_5MT", "FinalDriveRatio": "FD_3.31", "CoolantRadiator": "SmallRadiator_110",
                       "Tire0": "PerformanceTire_46", "Tire1": "PerformanceTire_46", "Tire2": "PerformanceTire_46", "Tire3": "PerformanceTire_46",
                       "Wheel0": CAR, "Wheel1": CAR, "Wheel2": CAR, "Wheel3": CAR,
                       "BrakePad0": "BrakePad_Small_02", "BrakePad1": "BrakePad_Small_02", "BrakePad2": "BrakePad_Small_02", "BrakePad3": "BrakePad_Small_02",
                       "Headlight": CAR + "_Popup", "FrontBumper": CAR + "_FrontBumper_KIT00", "RearBumper": CAR + "_RearBumper_KIT00",
                       "SideSkirt": CAR + "_SideSkirt_KIT00", "Bonnet": CAR + "_Bonnet_KIT00", "Fender": CAR + "_Fender_KIT00",
                       "RearWing": CAR + "_RearWing_KIT00"},
}
lut = [(500, 160), (1000, 213), (1500, 243), (2000, 269), (2500, 285), (3000, 291), (3500, 297), (3750, 299), (4000, 301), (4500, 304),
       (5000, 307), (5500, 306), (6000, 300), (6500, 293), (7000, 284), (7500, 273), (8000, 259), (8500, 245), (9000, 224)]
mx, lim = 314.0, 8500
curve = [[round(rr / lim, 4), round(t / 307.0, 4)] for rr, t in lut if rr <= lim] + [[5.0, 0.15]]
spec["custom_parts"]["engines"].append({
    "row": CAR + "_13B", "base_row": "I4_150HP", "asset": CAR + "_13B", "base_asset": "Cars/Parts/Engine/S58",
    "display_name": "13B-REW Twin Turbo (RX-7 Spirit R)", "mass": 125, "cost": 30000, "max_torque_nm": mx, "max_rpm": lim,
    "curve": curve, "curve_note": "13B rotary shape (AC FD lut) scaled to the factory 314 Nm (280 PS @6500 with the stock twin turbos built in)",
    "physics_from": "Cars/Parts/Engine/I4Sport_150HP", "idle_throttle": 0.0009,
    "sound_cue": {"cue_base": "Cars/Parts/Engine/Sound/s58/SC_V8Engine", "dir": "HEAT_RX7",
                  "loops": [["l1", 1020], ["l2", 1642], ["l3", 2067], ["l4", 2599], ["l5", 3109], ["l6", 3599], ["l7", 4105], ["l8", 4598], ["l9", 5094], ["l10", 5603], ["l11", 6098], ["l12", 6603], ["l13", 7106], ["l14", 7499]],
                  "note": "NFS Heat's own RX-7 audio (user 2026-11-13): idle render + Octane accel layers EXH/ENG/INT tone+noise mixed per rpm (heat/octane_loops.py); rpm checked by the firing frequency"}})
json.dump(spec, open(ROOT + "cars/heat_rx7.json", "w"), indent=1)
print("kits:", {s: sum(a["slot"] == s for a in aero) for s in ("FrontBumper", "RearBumper", "SideSkirt", "Bonnet", "RearWing", "Fender")},
      "room mirror", round(mpitch, 1), round(myaw, 1))
