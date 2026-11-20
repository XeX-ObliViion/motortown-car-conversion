"""spec for the Most Wanted (Remaster) Porsche Cayman S -> cars/mw_cayman.json, on the Fortem (small RWD coupe, like the
MW Elise). Starts from the make_spec bootstrap (cars/mw_cayman.bootstrap.json, mw_elise template).
Remaster CARS/CAYMANS is a modder add-on: each body (KIT00..KIT05) is ONE merged mesh with its own interior, glass and
engine; BASE holds the lamps (one shared lamp atlas 0x02B52399 -> CAYMANS_KIT00_BRAKELIGHT off/on), badges and the
mirrors (group 2 housings, group 3 glass). Exported to ~/nfs-work/db/mwr/CAYMANS (vfix x86 assetdumper).
Real car (987.1 Cayman S, 2006): 3.4 flat-6 295 hp @6250, 340 Nm @4400-6000 (MW curve: 338.8 Nm, ~296 hp - matches),
6MT 3.82/2.20/1.52/1.22/1.02/0.84 R 3.55, final 3.875, 1340 kg, wheelbase 2415, tyres 235/40R18 F 265/40R18 R.
Liveries (user 2026-11-19): only the FULL-BODY vinyl sets become garage skins; the small stickers go to global decals."""
import json, math, os

ROOT = r"C:/Users/noust/OneDrive/Documents/claude/ps2motortown/"
s = json.load(open(ROOT + "cars/mw_cayman.bootstrap.json"))
T = "Tex_CAYMAN_"
s.update({
    "car": "MW_CAYMAN", "display_name": "Porsche Cayman S (Most Wanted)", "prefix": "CAYMANS",
    "geometry_dir": "~/nfs-work/db/mwr/CAYMANS/geo", "texture_dir": "~/nfs-work/db/mwr/CAYMANS/tex/textures",
    "cost": 95000, "drivetrain": "rwd", "wheel_display_name": "Cayman S 18in",
})
ts = dict(s["texture_slots"])
ts.pop("BODY_LEFT", None); ts.pop("0xCE1FFED0", None)
ts.update({"0xF53E4A70": "Paint", "0x7C947F20": T + "ENGINE", "0x9F3D5F6B": "Bottom", "0x02B52399": T + "BRAKELIGHT",
           "0x076B2CD6": T + "MISC", "0x09AB2696": T + "BADGING", "0xC2C515D6": T + "INTERIOR", "0x32283A11": "Bottom",
           "0x076F035E": T + "TIRE", "0x010CB64A": "Bottom", "0x03C906EF": "Bottom"})
s["texture_slots"] = ts
s["texture_sources"] = {T + "MISC": "0x076B2CD6", T + "BADGING": "0x09AB2696", T + "BRAKELIGHT": "0x487EC448",
                        T + "INTERIOR": "0xC2C515D6", T + "ENGINE": "0x7C947F20", T + "TIRE": "0x076F035E"}
HEAD = T + "HEADLAMP"          # front half of the shared lamp atlas (headlamp reflector + lens art)
s["meshes"] = {
    "Body": {"parts": [{"part": "BASE", "groups": [0, 1]}, "KIT00_BODY", "KIT00_HOOD"],
             "drop_slots": [],
             },
    "LeftSideMirror": {"parts": [{"part": "BASE", "groups": [3], "slot": "Mirror", "normal_filter": {"axis": 0, "max": -0.75},
                                  "box": [0, 0, 60, 40, 120, 90]}],
                       "recenter": True, "planar_uv": {}},
    "Wheel_L": {"parts": [{"part": "KIT00_FRONT_TIRE", "offset": [0, 11.0, 0]}], "slot_rename": {"Trim": "Bottom"}},
    "Wheel_R": {"parts": [{"part": "KIT00_FRONT_TIRE", "mirror": True, "offset": [0, -11.0, 0]}], "slot_rename": {"Trim": "Bottom"}},
}
# mirror housings (paint) + the non-rear faces of the glass part stay on the body
s["meshes"]["Body"]["parts"] += [{"part": "BASE", "groups": [2], "slot": "Paint"},
                                 {"part": "BASE", "groups": [3], "slot": "Paint", "normal_filter": {"axis": 0, "min": -0.75}}]
s["mirror_components"] = {"LeftSideMirror_GEN_VARIABLE": "LeftSideMirror", "RightSideMirror_GEN_VARIABLE": "LeftSideMirror:mirror"}
s.pop("mirror_meshes", None)
s["mesh_names"] = {"Wheel_L": "MW_CAYMAN_R", "Wheel_R": "MW_CAYMAN_L", "SteeringWheel": "MW_CAYMAN"}
# lamps: the shared atlas; front cluster (x > 0) -> headlamp slot, rear stays TailLight
s["slot_boxes"] = [{"from": T + "BRAKELIGHT", "to": HEAD, "box": [100, -100, 0, 260, 100, 120], "note": "headlamp units"}]
s["texture_sources"][HEAD] = "0xCE1FFED0"   # the Remaster dump lacks the headlamp art: copied from the Rework export (same UVs, checked)
s["signal_lamps"] = [
    {"tag": "_F", "from": T + "BRAKELIGHT", "box": [100, -100, 0, 260, 100, 120], "uv_box": [0.8, 0.0, 1.0, 0.3], "note": "front indicators: the small round inner-lower lamp of each headlamp unit (uv top-right cell)"},
    {"tag": "_V", "from": T + "BRAKELIGHT", "uv_box": [0.56, 0.0, 0.90, 0.38], "uv_centroid": True, "copy": True, "lift": 0.08,
     "note": "reverse: inner half of the clear upper section (texture u > 0.56 maps inboard; masked overlay)"},
    {"tag": "_R", "from": T + "BRAKELIGHT", "uv_box": [0.28, 0.0, 0.56, 0.38], "uv_centroid": True, "copy": True, "lift": 0.08,
     "note": "rear indicators: outer half of the clear upper section (987.1: amber bulb behind the clear lens; u < 0.56 = outboard)"}]
s["lamp_slots"] = {HEAD: "head", T + "BRAKELIGHT": "tail",
                   "Signal_L_F": {"kind": "signal", "texture_slot": HEAD}, "Signal_R_F": {"kind": "signal", "texture_slot": HEAD},
                   "Signal_L_R": {"kind": "signal_overlay", "texture_slot": T + "BRAKELIGHT", "mask_gain": 8},
                   "Signal_R_R": {"kind": "signal_overlay", "texture_slot": T + "BRAKELIGHT", "mask_gain": 8},
                   "Signal_L_V": {"kind": "reverse_overlay", "texture_slot": T + "BRAKELIGHT", "mask_gain": 8},
                   "Signal_R_V": {"kind": "reverse_overlay", "texture_slot": T + "BRAKELIGHT", "mask_gain": 8}}
s["final_slot_names"] = {"Paint": "Body", "Glass": "Windows", HEAD: "HeadLight", T + "BRAKELIGHT": "TailLight",
                         T + "TIRE": "Wheel_01", "Signal_L_F": "LeftSignalLight", "Signal_R_F": "RightSignalLight",
                         "Signal_L_R": "LeftSignalLight", "Signal_R_R": "RightSignalLight",
                         "Signal_L_V": "ReverseLight", "Signal_R_V": "ReverseLight"}
# wheels: arches measured from the outer paint (front arch top x ~95 z 52, rear x ~-145 z 53); real wheelbase 2415
s["wheels"] = {"front_x": 96.0, "rear_x": -145.5, "half_track": 74.3, "rear_half_track": 76.4, "z": 17.0, "rear_z": 19.0,
               "radius": 32.3, "auto_arches": True, "note": "real track 1486/1528; tyres 235/40R18 F, 265/40R18 R"}
# performance: the source game's curve matches the rating; real 987.1 gearing
eng = s["custom_parts"]["engines"][0]
eng.update({"display_name": "3.4 Flat-6 (Cayman S)", "max_rpm": 7300.0,
            "sound_cue": {"cue_base": "Cars/Parts/Engine/Sound/s58/SC_V8Engine", "dir": "MW_CAYMAN",
                          "note": "MW Remaster SOUND/ENGINE/GIN_POR_996.gin (the Cayman's MW engine audio; identical to the file the MW 997TT loops were cut from), same 6 loops",
                          "loops": [["l1", 2076], ["l2", 2650], ["l3", 3264], ["l4", 4187], ["l5", 5210], ["l6", 6530]]}})
peak = max(eng["max_torque_nm"] * t * f * eng["max_rpm"] / 7121 for f, t in eng["curve"] if f <= 1.0)
print("engine: peak %.1f Nm, peak %.0f hp (rated 340 Nm / 295 hp)" % (eng["max_torque_nm"], peak))
FD, FD_ROW = 3.875, ("104", 3.73)
tr = s["custom_parts"]["transmissions"][0]
tr.update({"display_name": "6-Speed Manual (Cayman S)",
           "ratios": {g: round(v * FD / FD_ROW[1], 3) for g, v in
                      {"R": -3.55, "1": 3.82, "2": 2.20, "3": 1.52, "4": 1.22, "5": 1.02, "6": 0.84}.items()},
           "note": "real 987.1 ratios; final 3.875 folded in (game row 104 = 3.73)"})
s["part_overrides"]["FinalDriveRatio"] = FD_ROW[0]
s["blueprint"]["body_mass"] = 1340 - 456          # curb weight minus the fitted parts (as the template)
s["performance_source"] = "real 987.1 Cayman S: 295 hp, 340 Nm, 1340 kg, 6MT 3.82/2.20/1.52/1.22/1.02/0.84 R3.55 FD3.875"

# ---- cockpit (measured on the converted mesh with uv_to_3d; MT frame, driver at -y) ----
eye = (-42.0, -34.0, 88.0)      # cushion top z 20.5 (x -29), backrest top z 87 (x -64), headliner z 111.5
s["blueprint"]["seats"] = {"DriverSeat_GEN_VARIABLE": [eye[0] + 3, eye[1], eye[2] - 79],
                           "PassengerSeat1_GEN_VARIABLE": [eye[0] + 3, -eye[1], eye[2] - 79]}   # eye - seat = 79 (Fortem/Elise)
s["blueprint"]["cockpit_camera"] = list(eye)
mir = (8.5, 0.0, 93.3)          # the modelled rear-view mirror (dropped) -> the game's RoomMirror
d = [m - e for m, e in zip(mir, eye)]; dl = math.sqrt(sum(x * x for x in d)); d = [x / dl for x in d]
r = [-1.0, 0.0, 0.02]; rl = math.sqrt(sum(x * x for x in r)); r = [x / rl for x in r]
n = [a - b for a, b in zip(r, d)]; nl = math.sqrt(sum(x * x for x in n)); X = [-x / nl for x in n]
s["blueprint"]["components"]["RoomMirror_GEN_VARIABLE"] = list(mir)
s["blueprint"]["component_rotations"]["RoomMirror_GEN_VARIABLE"] = [round(math.degrees(math.asin(X[2])), 1),
                                                                     round(math.degrees(math.atan2(X[1], X[0])), 1), 0]
s["blueprint"]["components"]["FrontDomeLightSlot_GEN_VARIABLE"] = [-30, 0, 108]
s["meshes"]["Body"]["drop_boxes"] = [[5, -12, 88, 19, 12, 98.5]]
# steering wheel: a flat textured disc in the interior (centre uv (0.845, 0.84)) at (-3.1, -34.0, 65.7), tilted 14.5 deg
s["extract"] = {"SteeringWheel": {"from": "Body", "center": [-3.1, -34.0, 65.7], "radius": 15.0, "x_range": [-9, 3],
                                  "socket": "SteeringWheel", "align_x": True, "discard": True,
                                  "note": "MW wheel = an opaque flat disc that hid the dials in first person: only its pivot/tilt are kept"}}
# a real 3-spoke 987 wheel (365 mm) built in its place
s["add_shapes"] = [
    {"mesh": "SteeringWheel", "type": "torus", "note": "leather rim", "center": [-1, 0, 0], "normal": [1, 0, 0], "R": 17.0,
     "r": [1.6, 2.0], "seg": 48, "tseg": 12, "slot": "Bottom"},
    {"mesh": "SteeringWheel", "type": "spokes", "note": "3 spokes: 3, 9 and 6 o'clock", "center": [0, 0, 0],
     "angles": [-5, 185, -90], "r0": 5.0, "r1": 16.0, "x0": 1.2, "x1": -0.8, "section": [1.0, 3.0], "slot": "Bottom"},
    {"mesh": "SteeringWheel", "type": "cylinder", "note": "airbag hub", "center": [0.2, 0, 0], "axis": [3.4, 0, 0],
     "r": [6.2, 5.6], "seg": 28, "slot": "Bottom"},
    {"mesh": "SteeringWheel", "type": "ellipsoid", "note": "padded hub face", "center": [-0.2, 0, 0], "r": [1.4, 6.0, 5.4],
     "seg": 20, "slot": "Bottom"}]
# gauges: dial art in the interior texture (u, image row): speedo (0.155,0.296) r .023, tach (0.203,0.285) r .028,
# fuel/temp (0.252,0.295) r .023; the faces the driver sees are the vertical ones at x 19.8 (normal -x)
DX = 19.77 - 0.4
s["dashboard"] = {"sockets": [{"name": "Niddle_Speed", "loc": [DX, -43.81, 64.85], "rot": [0, -90, -90]},
                              {"name": "Niddle_RPM", "loc": [DX, -35.44, 66.62], "rot": [0, -90, -90]},
                              {"name": "Niddle_Fuel", "loc": [DX, -26.83, 65.01], "rot": [0, -90, -90]},
                              {"name": "Niddle_Temp", "loc": [DX, -26.83, 65.01], "rot": [0, -90, -90]}],
                  "parent_socket": "SteeringWheel"}
s["gauge_faces"] = {T + "INTERIOR": [
    {"center": [0.155, 0.296], "face": [0.155, 0.296, 0.024], "radius": 0.022, "min": 0, "max": 180, "text_step": 20,
     "line_step": 10, "start": 140, "end": 400, "font": 0.17, "captions": [["MPH", 0.32, 90]], "caption_font": 0.12},
    {"center": [0.203, 0.285], "face": [0.203, 0.285, 0.029], "radius": 0.027, "min": 0, "max": 8, "text_step": 1,
     "line_step": 0.5, "start": 140, "end": 400, "red_from": 7.2, "font": 0.2, "captions": [["x1000 RPM", 0.32, 90]],
     "caption_font": 0.1},
    {"center": [0.252, 0.295], "face": [0.252, 0.295, 0.024], "radius": 0.021, "min": 0, "max": 1, "text_step": 1,
     "line_step": 0.25, "start": 210, "end": 330, "font": 0.4, "labels": {"0": "E", "1": "F"}},
    {"center": [0.252, 0.295], "radius": 0.021, "min": 40, "max": 120, "text_step": 80, "line_step": 20, "start": 30,
     "end": 150, "font": 0.4, "labels": {"40": "C", "120": "H"}, "red_from": 110}]}
s["gauge_ranges"] = {"RPM": {"max": 8}, "Speed": {"max": 180}}
# ---- liveries: full-body vinyl sets only (user) ----
BL = ["01RAZORCALLAHAN", "02TUROSATO", "03RONNIEMCCREA", "04JOEVEGA", "05WESALLEN", "06HECTORDOMINGO", "07KIRANAZAKATO",
      "08JADEBARRETT", "09PIERREDUPONT", "10KARLSMIT", "11LOUPARK", "12ISABELDIAZ", "13VICTORVASQUEZ", "14VINCEKILIC",
      "15TONYHO"]
pick = (["BODY%02d" % i for i in range(1, 13)] + ["BODYFLAME%02d" % i for i in (1, 2, 3, 4, 5, 6, 7, 8, 10)]
        + ["BODYTRIBAL%02d" % i for i in range(1, 11)] + ["BODYSTRIPE%02d" % i for i in range(1, 11)]
        + BL + ["CARBONFIBER", "COPGTO", "BMW_24", "CROSS"])
s["skins"] = {"dir": "~/nfs-work/db/mwr/CAYMANS/vin/textures", "pick": pick,
              "labels": {b: "Blacklist " + b[:2] + " " + b[2:].title() for b in BL}}
# ---- body kits: whole MW kit bodies cut into bumpers / skirts (front arch ends ~x 135, rear ~-180) ----
s["mw_kits"] = {"front_split": 140.0, "rear_split": -182.0}
s["sockets"] = {"Body": [
    {"name": "Exhaust_Left", "loc": [-226, 0, 14], "rot": [0, 180, 0]},     # 987 Cayman S: centre twin tips
    {"name": "Exhaust_Right", "loc": [-226, 0, 14], "rot": [0, 180, 0]},
    {"name": "RearWing", "loc": [-205, 0, 65], "rot": [0, 0, 0]},          # rear lid lip (spoiler base top)
    {"name": "TaxiRoofSign", "loc": [-25, 0, 114], "rot": [0, 0, 0]},
    {"name": "TrailerHitch", "loc": [-228, 0, 25], "rot": [0, 0, 0]}]}
# rear tyres 265 vs 235 front: own rear meshes + a rear wheel row (the game ignores RearLeft/RightWheelMesh)
RW = 265 / 235
s["meshes"]["Wheel_RL"] = {"parts": [{"part": "KIT00_FRONT_TIRE", "offset": [0, 11.0, 0], "scale": [1, RW, 1]}], "slot_rename": {"Trim": "Bottom"}}
s["meshes"]["Wheel_RR"] = {"parts": [{"part": "KIT00_FRONT_TIRE", "mirror": True, "offset": [0, -11.0, 0], "scale": [1, RW, 1]}], "slot_rename": {"Trim": "Bottom"}}
s["mesh_names"].update({"Wheel_RL": "MW_CAYMAN_REAR_R", "Wheel_RR": "MW_CAYMAN_REAR_L"})
s["rear_wheel_meshes"] = True; s["rear_wheel_part"] = True
s["part_overrides"].update({"Wheel2": "MW_CAYMAN_REAR", "Wheel3": "MW_CAYMAN_REAR"})
# lamp light components at this car's lamps (MT frame, left = -y)
s["blueprint"]["components"].update({
    "HeadLight_Left_GEN_VARIABLE": [162, -60, 53], "HeadLight_Right_GEN_VARIABLE": [162, 60, 53],
    "BlinkerLight_01_GEN_VARIABLE": [164, 54, 48], "BlinkerLight_02_GEN_VARIABLE": [164, -54, 48],
    "TaliLight_01_GEN_VARIABLE": [-212, -66, 55], "TaliLight_02_GEN_VARIABLE": [-212, 66, 55],
    "BlinkerLight_03_GEN_VARIABLE": [-208, 70, 60], "BlinkerLight_04_GEN_VARIABLE": [-208, -70, 60]})
s["no_red_lens"] = True   # the lamp art already has red and clear sections (user: red drew over the white parts)
s.pop("TODO", None)
json.dump(s, open(ROOT + "cars/mw_cayman.json", "w"), indent=1)
print("wrote cars/mw_cayman.json")
