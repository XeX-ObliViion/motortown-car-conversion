"""Spec for the BeamNG Ford Shelby GT350R (s550pewpiw mod, config GT350R_M) -> cars/bng_gt350r.json.
Parts come from bng/bng_to_parts.py (~/nfs-work/bng/gt350r/geo, prefix GT350R, metres, x fwd / y left / z up).
Real car (2016-17 Shelby GT350R): 5.2 Voodoo flat-plane V8, 526 hp @ 7500, 429 lb-ft (582 Nm) @ 4750, limiter 8250;
Tremec TR-3160 6MT 3.25/2.24/1.73/1.32/1.00/0.80 R 3.07, final 3.73; curb 3,650 lb (1,656 kg); 295/30R19 F,
315/30R19 R Michelin Pilot Sport Cup 2; RWD, Torsen LSD.
usage: python tools/spec_gen/make_gt350r_spec.py"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEO = os.path.expanduser("~/nfs-work/bng/gt350r/geo")
TEX = os.path.expanduser("~/nfs-work/bng/gt350r/textures")
parts = sorted(os.path.basename(f)[len("GT350R_"):-len("_A.dae")] for f in glob.glob(GEO + "/GT350R_*_A.dae"))
mats = sorted({m for f in glob.glob(GEO + "/*.dae") for m in re.findall(r'<material id="m\d+" name="([^"]+)"', open(f).read())})

WHEEL = {"S550_WHEEL_02A_19X11", "TIRE_01A_19X11_25_S550"}
STEER = "S550_STEER_GT350R"
MIRROR_HOUSINGS = {"S550_MIRROR_L", "S550_MIRROR_R"}
# underbody/suspension the game never shows (or that would not move with the game's wheels): left out
SKIP = {"S550_BRAKEDISC_FL_SPORT", "S550_BRAKEDISC_FR_SPORT", "S550_BRAKEDISC_RL_SPORT", "S550_BRAKEDISC_RR_SPORT",
        "S550_CALIPER_F_SPORT", "S550_CALIPER_R_SPORT", "S550_HALFSHAFT_R", "S550_HUB_F", "S550_HUB_R",
        "S550_WINDSHIELD_INT", "S550_BACKLIGHT_INT", "S550_SIDEGLASS_L_INT", "S550_SIDEGLASS_R_INT",
        "S550_DOORGLASS_L_INT", "S550_DOORGLASS_R_INT"}
body_parts = [p for p in parts if p not in WHEEL | SKIP | {STEER}]
# the mirror glass (material "mirror" = geometry group 0, materials are sorted) becomes the game's live mirrors
body_parts = [{"part": p, "skip_groups": [0]} if p in MIRROR_HOUSINGS else p for p in body_parts if p != "S550_INTMIRROR"]   # the game supplies the room mirror


def tex_slot(m):
    return "Tex_BNG_" + re.sub(r"[^A-Za-z0-9]+", "_", m).upper().strip("_")


slots, sources, lamps, finals = {}, {}, {}, {"Paint": "Body_01", "Glass": "Window"}
signal_lamps = []
for m in mats:
    if m == "s550_paint":
        slots[m] = "Paint"
    elif m in ("s550_glass", "s550_glass_int"):
        slots[m] = "Glass"
    elif m == "mirror":
        slots[m] = "Trim"
    else:
        s = tex_slot(m); slots[m] = s; sources[s] = m + ".png"
        # lamp lenses have no texture of their own in BeamNG (lit at runtime); their UVs map into the shared lamp atlas
        if re.search(r"headlight|runninglight|signal|reverselight|chmsl|taillight|side_rear", m):
            sources[s] = "s550_lights__L.png" if os.path.exists(os.path.join(TEX, "s550_lights__L.png")) else "s550_lights.png"
# lamps: the source car's own lamp materials
for m in mats:
    s = slots[m]
    if re.match(r"s550_headlight__[LR]$", m):
        lamps[s] = {"kind": "head", "texture_slot": s}; finals[s] = "HeadLight"
    elif re.match(r"s550_runninglight__([LR])$", m):            # front DRL bar doubles as the amber indicator
        side = m[-1]; lamps[s] = {"kind": "signal", "texture_slot": s}
        finals[s] = "LeftSignalLight" if side == "L" else "RightSignalLight"
    elif re.match(r"s550_signal_R([LR])_\d$", m):
        # the three tail lamp bars are the brake/tail lamps AND (US) the sequential indicator: tail lamps here, plus a
        # lifted copy that blinks (signal_overlay, as the MW Elise), so braking and blinking both show (user 2026-11-14)
        side = re.match(r"s550_signal_R([LR])", m).group(1); lamps[s] = {"kind": "tail", "texture_slot": s}
        finals[s] = "LeftTailLight" if side == "L" else "RightTailLight"
        signal_lamps.append({"tag": "_R", "from": s, "copy": True, "lift": 0.08})
        lamps.setdefault("Signal_%s_R" % side, {"kind": "signal_overlay", "texture_slot": s})
        finals["Signal_%s_R" % side] = "LeftSignalLight" if side == "L" else "RightSignalLight"
    elif m == "s550_reverselight":
        lamps[s] = {"kind": "reverse", "texture_slot": s}; finals[s] = "ReverseLight"
    elif m == "s550_chmsl":
        lamps[s] = {"kind": "tail", "texture_slot": s}; finals[s] = "TailLight"
    elif m in ("s550_signal_L", "s550_signal_R"):                # mirror repeaters
        lamps[s] = {"kind": "signal", "texture_slot": s}
        finals[s] = "LeftSignalLight" if m.endswith("L") else "RightSignalLight"

spec = {
    "car": "BNG_GT350R", "display_name": "Ford Shelby GT350R (BeamNG)", "prefix": "GT350R",
    "base_vehicle": "Tuscan", "default_slot": "Bottom", "source_scale": 100.0,
    "geometry_dir": GEO.replace("\\", "/"), "texture_dir": TEX.replace("\\", "/"),
    "out_dir": os.path.expanduser("~/mt-work/build/BNG_GT350R/meshes").replace("\\", "/"),
    "cost": 150000, "wheel_part": True, "base_wheel": "Vista", "wheel_display_name": "Shelby GT350R Stock (BeamNG)",
    "texture_slots": slots, "texture_sources": sources,
    "meshes": {
        "Body": {"parts": body_parts + [{"part": STEER, "slot": tex_slot("s550_steeringwheel")}], "reduce": 0.4},
        "SideMirror_L": {"parts": [{"part": "S550_MIRROR_L", "groups": [0], "slot": "Mirror"}], "planar_uv": {}},
        "SideMirror_R": {"parts": [{"part": "S550_MIRROR_R", "groups": [0], "slot": "Mirror"}], "planar_uv": {"flip_u": True}},
        "Wheel_L": {"parts": [{"part": "S550_WHEEL_02A_19X11"}, {"part": "TIRE_01A_19X11_25_S550"}], "reduce": 0.5},
        "Wheel_R": {"parts": [{"part": "S550_WHEEL_02A_19X11", "mirror": True}, {"part": "TIRE_01A_19X11_25_S550", "mirror": True}], "reduce": 0.5},
    },
    "mesh_names": {"Wheel_L": "BNG_GT350R_L", "Wheel_R": "BNG_GT350R_R", "SteeringWheel": "BNG_GT350R"},
    "final_slot_names": finals, "lamp_slots": lamps, "signal_lamps": signal_lamps,
    "wheels": {"front_x": 137.0, "rear_x": -134.5, "half_track": 80, "z": 32, "rear_z": 33, "radius": 32, "auto_arches": True},
    "extract": {"SteeringWheel": {"from": "Body", "center": [17.2, -36.7, 85.7], "radius": 20, "x_range": [5, 32],
                                  "uv_slots": [tex_slot(m) for m in mats if "steer" in m or m == "s550_steeringwheel"],
                                  "uv_box": [-99, -99, 99, 99], "socket": "SteeringWheel", "align_x": True}},
    "mirror_sockets": {"SideMirror_L": "SideMirror_L", "SideMirror_R": "SideMirror_R"},
    # needle pivots = the BeamNG needle props' node origins; face tilt 27.4 deg (big dials) / 35.6 deg (small)
    "dashboard": {"sockets": [
        {"name": "Niddle_RPM", "loc": [43.8, -48.4, 87.7], "rot": [0, -90, -62.6]},
        {"name": "Niddle_Speed", "loc": [43.8, -25.0, 87.7], "rot": [0, -90, -62.6]},
        {"name": "Niddle_Temp", "loc": [42.6, -48.8, 85.1], "rot": [0, -90, -54.4]},
        {"name": "Niddle_Fuel", "loc": [42.1, -25.2, 85.3], "rot": [0, -90, -54.4]}]},
    # dial art (s550_cockpit texture): tach 0-8k (red 7), speedo 0-160 mph + inner km/h, fuel E-F under the speedo,
    # temp C-H under the tach. Redrawn on the game's needle sweep (140..400 deg); GT350R limiter 8250 -> tach to 9
    "gauge_faces": {"Tex_BNG_S550_INTERIOR": [
        {"center": [0.6678, 0.7808], "face": [0.6678, 0.7808, 0.215], "radius": 0.2, "rotate": 0, "min": 0, "max": 160,
         "text_step": 20, "line_step": 10, "start": 140, "end": 400, "font": 0.12, "captions": [["MPH", 0.3, 270]], "caption_font": 0.08},
        {"center": [0.2263, 0.7793], "face": [0.2263, 0.7793, 0.215], "radius": 0.2, "rotate": 0, "min": 0, "max": 9,
         "text_step": 1, "line_step": 0.5, "start": 140, "end": 400, "red_from": 8.25, "font": 0.13,
         "captions": [["x1000 RPM", 0.3, 270]], "caption_font": 0.07},
        {"center": [0.6589, 0.9059], "radius": 0.07, "rotate": 0, "min": 0, "max": 1, "text_step": 1, "line_step": 0.25,
         "start": 210, "end": 330, "font": 0.3, "labels": {"0": "E", "1": "F"}},
        {"center": [0.2085, 0.9015], "radius": 0.07, "rotate": 0, "min": 40, "max": 120, "text_step": 80, "line_step": 20,
         "start": 210, "end": 330, "font": 0.3, "labels": {"40": "C", "120": "H"}, "red_from": 110}]},
    "gauge_style": {"face_color": [12, 12, 12], "ink": [238, 238, 234], "minor_ink": [185, 185, 185], "red_color": [225, 30, 25], "font_file": "arialbd.ttf"},
    "gauge_ranges": {"RPM": {"max": 9}, "Speed": {"max": 160, "value_scale": 1.609344}},
    "needle_color": [235, 60, 25], "needle_width": 0.4,
    "texture_upscale": {"Tex_BNG_S550_INTERIOR": 4},
    "emissive_slots": {"Gauges": {"texture_slot": "Tex_BNG_S550_INTERIOR", "glow": 2.0, "mask_from_gauges": True}},
    # one box low (wheel line up), one for the cabin; from 14 cm above the ground
    "collision_boxes": [{"center": [-7, 0, 48], "size": [476, 184, 68]}, {"center": [-45, 0, 106], "size": [210, 140, 48]}],
    "blueprint": {"seats": {"DriverSeat_GEN_VARIABLE": [-30, -39, 27], "PassengerSeat1_GEN_VARIABLE": [-30, 39, 27]},
                  "components": {"RoomMirror_GEN_VARIABLE": [13, -1, 121], "FrontDomeLightSlot_GEN_VARIABLE": [-5, 0, 128],
                                 "HeadLight_Left_GEN_VARIABLE": [200, -72, 70], "HeadLight_Right_GEN_VARIABLE": [200, 72, 70],
                                 "BlinkerLight_01_GEN_VARIABLE": [195, 75, 66], "BlinkerLight_02_GEN_VARIABLE": [195, -75, 66],
                                 "TaliLight_01_GEN_VARIABLE": [-230, -61, 84], "TaliLight_02_GEN_VARIABLE": [-230, 61, 84]},
                  "component_rotations": {"RoomMirror_GEN_VARIABLE": [6.8, 20.4, 0]},
                  "keep_body_materials": 1, "cockpit_camera": [-30, -39, 106], "body_mass": 1206},
    "strip_part_slots": ["Bonnet", "FrontBumper", "RearBumper"],   # the Tuscan row's own body panels (Unicorn lesson)
    "performance_source": "2016-17 Shelby GT350R: 5.2 Voodoo NA flat-plane V8 526 hp @7500, 429 lb-ft (582 Nm) @4750, limiter 8250; Tremec TR-3160 6MT 3.25/2.24/1.73/1.32/1.00/0.80 R3.07, final 3.73; curb 1656 kg; RWD Torsen",
    "custom_parts": {
        "transmissions": [{"row": "BNG_GT350R_6MT", "base_row": "6SpeedSportsLP670", "asset": "BNG_GT350R_6MT",
                           "base_asset": "Cars/Parts/Transmission/Manual6SpeedSports_LP670",
                           "display_name": "Tremec 6-Speed (Shelby GT350R)", "cost": 7000, "mass": 100,
                           "ratios": {"R": -3.459, "1": 3.662, "2": 2.524, "3": 1.949, "4": 1.487, "5": 1.127, "6": 0.901},
                           "note": "real final 3.73 folded in (game row FD_3.31): ratio x 3.73/3.31"}],
        "engines": [{"row": "BNG_GT350R_VOODOO", "base_row": "SmallBlock_320HP", "asset": "BNG_GT350R_VOODOO",
                     "base_asset": "Cars/Parts/Engine/S58", "display_name": "5.2 Voodoo V8 (Shelby GT350R)",
                     "mass": 200, "cost": 45000, "max_torque_nm": 582, "max_rpm": 8250,
                     # torque / max by rpm/8250: 582 Nm at 4750, 499 Nm (526 hp) at 7500
                     "curve": [[0.0606, 0.5], [0.1212, 0.62], [0.2424, 0.74], [0.3636, 0.85], [0.4848, 0.95], [0.5758, 1.0],
                               [0.6667, 0.98], [0.7879, 0.93], [0.9091, 0.857], [1.0, 0.79], [5.0, 0.15]],
                     "curve_note": "rated 526 hp @7500 = 499 Nm (0.857 of peak), peak 582 Nm @4750",
                     "physics_from": "Cars/Parts/Engine/FordSmalBlock302_V8_5L_320HP", "idle_throttle": 0.0009,
                     "sound_cue": {"cue_base": "Cars/Parts/Engine/Sound/s58/SC_V8Engine", "dir": "BNG_GT350R",
                                   "loops": [["l%d" % (i + 1), r] for i, r in enumerate([800, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000])],
                                   "note": "the mod's own Forza recordings (art/sound/engine/fm7/for_shelbygt350r_16, Exhaust_on_*)"}}]},
    "part_overrides": {"Engine": "BNG_GT350R_VOODOO", "Transmission": "BNG_GT350R_6MT", "FinalDriveRatio": "FD_3.31",
                       "CoolantRadiator": "SmallRadiator_110",
                       "Tire0": "PerformanceTire_15", "Tire1": "PerformanceTire_15", "Tire2": "PerformanceTire_15", "Tire3": "PerformanceTire_15",
                       "Wheel0": "BNG_GT350R", "Wheel1": "BNG_GT350R", "Wheel2": "BNG_GT350R", "Wheel3": "BNG_GT350R",
                       "BrakePad0": "BrakePad_Small_02", "BrakePad1": "BrakePad_Small_02", "BrakePad2": "BrakePad_Small_02", "BrakePad3": "BrakePad_Small_02"},
    "note": "first pass 2026-11-14: seats/camera/body_mass/wheels to be measured; gauges, mirrors, lamps boxes, sound, performance next",
}
out = os.path.join(ROOT, "cars", "bng_gt350r.json")
json.dump(spec, open(out, "w"), indent=1)
print("%d body parts, %d materials (%d lamp slots) -> %s" % (len(body_parts), len(mats), len(lamps), out))
