"""spec for the Most Wanted (Remaster) Mazda RX-7 FC "Savanna" -> cars/mw_rx7fc.json, on the Fortem (small RWD coupe).
Starts from the make_spec bootstrap (cars/mw_rx7fc.bootstrap.json, mw_elise template; db record mwr:RX7FC).
Remaster CARS/RX7FC (modder AJ_Lethal, 2019): standard MW layout but the interior is spread over KIT00_INTERIOR and
both *_SIDE_MIRROR parts (seats / wheel / dash); the real mirror housings are BASE g4 (paint) + g5 (glass, MISC).
RHD (JDM Savanna). Lamps: one atlas in 4 states (0x841740E6 off, 0x7353CEE1 brake, 0x87E1ACA8 tail, 0xDDCDAA3F alt);
BASE 0x02B52399 = the shared MW tail-lamp material.
Source data (MW Remaster attributes rx7fc): 200 lb-ft peak (271 Nm) + induction HIGH_BOOST 0.1, MAX_RPM 8500, red line
7000, 5MT 3.47/2.00/1.37/1.00/0.72 R3.29, final 4.10, 1285 kg, wheelbase 2430, track 1450/1440."""
import json, math, os, sys

ROOT = r"C:/Users/noust/OneDrive/Documents/claude/ps2motortown/"
s = json.load(open(ROOT + "cars/mw_rx7fc.bootstrap.json"))
T = "Tex_RX7FC_"
STAGE = sys.argv[1] if len(sys.argv) > 1 else "full"
s.update({"car": "MW_RX7FC", "display_name": "Mazda RX-7 Savanna FC (Most Wanted)", "prefix": "RX7FC",
          "geometry_dir": "~/nfs-work/db/mwr/RX7FC/geo", "texture_dir": "~/nfs-work/db/mwr/RX7FC/tex/textures",
          "cost": 42000, "drivetrain": "rwd", "wheel_display_name": "RX-7 FC 15in", "source_scale": 100.0})
ts = dict(s["texture_slots"])
LAMP = T + "BRAKELIGHT"
ts.update({"0x943D5ECE": "Paint", "0x1B049702": "Bottom", "0x0DCB6701": "Bottom", "0xE1326F01": "Bottom", "0x32283A11": "Bottom",
           "0x4C95C6F8": "Bottom", "0x7B220DDF": "Glass", "0xE2A5C626": "Glass", "0x7811C146": "Bottom",
           "0x428A2D74": T + "MISC", "0x64C0CA74": T + "BADGING", "0x808F3574": T + "INTERIOR", "0xF96AA794": "Bottom",
           "0x841740E6": LAMP, "0x01F40B32": LAMP, "0x7353CEE1": LAMP, "0x87E1ACA8": LAMP,
           # lens layers over the reflectors (not duplicates: DDCDAA3F = front lenses, 02B52399 = rear housings)
           "0xDDCDAA3F": LAMP, "0x02B52399": LAMP,
           "0x428E03FC": T + "TIRE", "0xB470E050": T + "RIM"})
s["texture_slots"] = ts
s["texture_sources"] = {T + "MISC": "0x428A2D74", T + "BADGING": "0x64C0CA74", LAMP: "0x841740E6", T + "INTERIOR": "0x808F3574",
                        T + "TIRE": "0x428E03FC", T + "RIM": "0xB470E050"}
INT = ["KIT00_INTERIOR", "KIT00_LEFT_SIDE_MIRROR", "KIT00_RIGHT_SIDE_MIRROR"]
s["meshes"] = {
    # BASE g3 + g20 = window frame + glass (KIT00_FRONT_WINDOW duplicates them); g4/g5 = mirror housings + glass
    "Body": {"parts": [{"part": "BASE", "groups": [i for i in range(21) if i not in (4, 5)]}, "KIT00_BODY", "KIT00_HOOD",
                       "KIT00_SPOILER", {"part": "BASE", "groups": [4], "slot": "Paint"}] + INT},
    "Wheel_L": {"parts": [{"part": "KIT00_FRONT_TIRE", "offset": [0, 11.0, 0]}], "slot_rename": {"Trim": "Bottom"}},
    "Wheel_R": {"parts": [{"part": "KIT00_FRONT_TIRE", "mirror": True, "offset": [0, -11.0, 0]}], "slot_rename": {"Trim": "Bottom"}},
}
if STAGE == "survey":   # interior pieces as separate meshes, to see which are duplicates
    s["meshes"]["Body"]["parts"] = [p for p in s["meshes"]["Body"]["parts"] if p not in INT]
    for p in INT:
        s["meshes"]["Dbg_" + p] = {"parts": [p]}
s["mirror_components"] = {"LeftSideMirror_GEN_VARIABLE": "LeftSideMirror", "RightSideMirror_GEN_VARIABLE": "LeftSideMirror:mirror"}
s.pop("mirror_meshes", None)
# left mirror glass: BASE g5 (x 20..26, y -97..-78, z 65..76); its non-rear faces stay on the body as housing paint
s["meshes"]["LeftSideMirror"] = {"parts": [{"part": "BASE", "groups": [5], "slot": "Mirror", "normal_filter": {"axis": 0, "max": -0.75},
                                            "box": [10, -110, 55, 35, -60, 85]}], "recenter": True, "planar_uv": {}}
s["meshes"]["Body"]["parts"].append({"part": "BASE", "groups": [5], "slot": "Paint", "normal_filter": {"axis": 0, "min": -0.75}})
s["mesh_names"] = {"Wheel_L": "MW_RX7FC_R", "Wheel_R": "MW_RX7FC_L", "SteeringWheel": "MW_RX7FC"}

# ---- lamps: one atlas (off state 0x841740E6). Front (x > 100) = head slot; rear strip (rows .66-.93, low u = outboard):
# outer round = turn signal, middle rounds = brake/tail, white box = reverse; top bar on the hatch = high-mount brake
HEAD = T + "HEADLAMP"
s["texture_sources"][HEAD] = "0x841740E6"
s["slot_boxes"] = [{"from": LAMP, "to": HEAD, "box": [100, -120, -10, 260, 120, 120], "note": "front lamps (bumper, corners, fogs)"}]
s["signal_lamps"] = [
    {"tag": "_F", "from": LAMP, "box": [100, -120, -10, 260, 120, 120], "uv_box": [0.0, 0.14, 0.34, 0.26], "uv_centroid": True,
     "note": "amber front corner lamps (atlas amber bar)"},
    {"tag": "_P", "from": LAMP, "box": [100, -120, -10, 260, 120, 120], "uv_box": [0.46, 0.34, 0.98, 0.48], "uv_centroid": True,
     "note": "clear bumper turn/park lamps (FC S5 front turn signals)"},
    {"tag": "_R", "from": LAMP, "box": [-260, -120, 30, -150, 120, 70], "uv_box": [0.0, 0.66, 0.30, 0.93], "uv_centroid": True,
     "note": "rear turn: outer round lens (stays amber-tinted in every MW lamp state)"},
    {"tag": "_V", "from": LAMP, "box": [-260, -120, 30, -150, 120, 70], "uv_box": [0.66, 0.66, 0.80, 0.93], "uv_centroid": True,
     "note": "reverse: the white box beside the plate"}]
s["lamp_slots"] = {HEAD: "head", LAMP: "tail",
                   "Signal_L_F": {"kind": "signal", "texture_slot": HEAD}, "Signal_R_F": {"kind": "signal", "texture_slot": HEAD},
                   "Signal_L_P": {"kind": "signal", "texture_slot": HEAD}, "Signal_R_P": {"kind": "signal", "texture_slot": HEAD},
                   "Signal_L_R": {"kind": "signal", "texture_slot": LAMP}, "Signal_R_R": {"kind": "signal", "texture_slot": LAMP},
                   "Signal_L_V": {"kind": "reverse", "texture_slot": LAMP}, "Signal_R_V": {"kind": "reverse", "texture_slot": LAMP}}
s["final_slot_names"] = {"Paint": "Body", "Glass": "Windows", HEAD: "HeadLight", LAMP: "TailLight", T + "TIRE": "Wheel_01",
                         "Signal_L_F": "LeftSignalLight", "Signal_R_F": "RightSignalLight", "Signal_L_P": "LeftSignalLight",
                         "Signal_R_P": "RightSignalLight", "Signal_L_R": "LeftSignalLight", "Signal_R_R": "RightSignalLight",
                         "Signal_L_V": "ReverseLight", "Signal_R_V": "ReverseLight"}
s["no_red_lens"] = True
s["blueprint"]["components"].update({
    "HeadLight_Left_GEN_VARIABLE": [150, -56, 62], "HeadLight_Right_GEN_VARIABLE": [150, 56, 62],   # pop-up lids (closed in MW)
    "BlinkerLight_01_GEN_VARIABLE": [208, 52, 25], "BlinkerLight_02_GEN_VARIABLE": [208, -52, 25],
    "TaliLight_01_GEN_VARIABLE": [-206, -47, 51], "TaliLight_02_GEN_VARIABLE": [-206, 47, 51],
    "BlinkerLight_03_GEN_VARIABLE": [-201, 68, 51], "BlinkerLight_04_GEN_VARIABLE": [-201, -68, 51]})

# ---- wheels: arches measured 122.4 / -121.8 (wheelbase 2442, real 2430); arch tops z 47.3 / 49.7 -> same tyre gap as the Cayman
s["wheels"] = {"front_x": 122.4, "rear_x": -121.8, "half_track": 72.5, "rear_half_track": 72.0, "z": 13.5, "rear_z": 17.0,
               "radius": 31.1, "auto_arches": True, "note": "MW track 1450/1440; 205/60R15 (r 31.4)"}

# ---- performance: MW Remaster rx7fc engine table x induction HIGH_BOOST 1.1 (full boost) = 298 Nm / ~207 hp
# (real 1989-91 Turbo II: 200 hp, 196 lb-ft); MW red line 7000 = limiter
eng = s["custom_parts"]["engines"][0]
BOOST = 1.1
lbft = [[800, 100], [1762, 165], [2725, 190], [3688, 200], [4650, 190], [5612, 175], [6575, 150], [7538, 130], [8500, 110]]
MX = 7000.0
pts = [[r_, v * BOOST * 1.3558] for r_, v in lbft if r_ <= 7600]
pk = max(v for _, v in pts)
eng.update({"display_name": "13B-T Rotary Turbo (RX-7 FC)", "max_rpm": MX, "max_torque_nm": round(pk, 1),
            "curve": [[round(r_ / MX, 4), round(v / pk, 4)] for r_, v in pts] + [[5.0, 0.15]],
            "curve_note": "MW Remaster rx7fc TORQUE x HIGH_BOOST 1.1 (turbo at full boost), lb-ft -> Nm",
            "sound_cue": {"cue_base": "Cars/Parts/Engine/Sound/s58/SC_V8Engine", "dir": "MW_RX7FC",
                          "note": "MW Remaster SOUND/ENGINE/GIN_Mazda_RX7.gin (engineaudio maz_rx7, used by rx7fc), 6 loops",
                          "loops": [["l1", 1563], ["l2", 2058], ["l3", 2838], ["l4", 3761], ["l5", 5048], ["l6", 6779]]}})
peak_hp = max(eng["max_torque_nm"] * t * f * MX / 7121 for f, t in eng["curve"] if f <= 1.0)
print("engine: peak %.1f Nm, peak %.0f hp (source: 200 lb-ft x 1.1 boost; real Turbo II 200 hp)" % (eng["max_torque_nm"], peak_hp))
FD, FD_ROW = 4.10, ("112", 4.11)
tr = s["custom_parts"]["transmissions"][0]
tr.update({"display_name": "5-Speed Manual (RX-7 FC)",
           "ratios": {g: round(v * FD / FD_ROW[1], 3) for g, v in
                      {"R": -3.29, "1": 3.47, "2": 2.00, "3": 1.37, "4": 1.00, "5": 0.72}.items()},
           "note": "MW Remaster rx7fc ratios; final 4.10 (game row 112 = 4.11)"})
s["part_overrides"]["FinalDriveRatio"] = FD_ROW[0]
s["blueprint"]["body_mass"] = 1285 - 456
s["performance_source"] = "MW Remaster rx7fc: 200 lb-ft (+10% boost), red line 7000, 5MT 3.47/2.00/1.37/1.00/0.72 R3.29 FD4.10, 1285 kg"

# ---- cockpit (RHD: driver at +y). wheel ring centre (7, 35.4, 57.8) r ~18; seats x -77..15; headliner z 98..103
eye = (-40.0, 35.4, 87.0)
s["blueprint"]["seats"] = {"DriverSeat_GEN_VARIABLE": [eye[0] + 3, eye[1], eye[2] - 79],
                           "PassengerSeat1_GEN_VARIABLE": [eye[0] + 3, -eye[1], eye[2] - 79]}
s["blueprint"]["cockpit_camera"] = list(eye)
mir = (-2.0, 0.0, 93.5)   # the modelled mirror (glass x -1.7, y +-9, z 90.4..96.5) is dropped below
d = [m - e for m, e in zip(mir, eye)]; dl = math.sqrt(sum(x * x for x in d)); d = [x / dl for x in d]
r = [-1.0, 0.0, 0.02]; rl = math.sqrt(sum(x * x for x in r)); r = [x / rl for x in r]
n = [a - b for a, b in zip(r, d)]; nl = math.sqrt(sum(x * x for x in n)); X = [-x / nl for x in n]
s["blueprint"]["components"]["RoomMirror_GEN_VARIABLE"] = list(mir)
s["blueprint"]["component_rotations"]["RoomMirror_GEN_VARIABLE"] = [round(math.degrees(math.asin(X[2])), 1),
                                                                     round(math.degrees(math.atan2(X[1], X[0])), 1), 0]
s["blueprint"]["components"]["FrontDomeLightSlot_GEN_VARIABLE"] = [-30, 0, 98]
s["meshes"]["Body"]["drop_boxes"] = [[-12, -12, 88, 3, 12, 97.5]]   # modelled rear-view mirror (the game supplies a working one)
s["extract"] = {"SteeringWheel": {"from": "Body", "center": [7.0, 35.4, 57.8], "radius": 20.0, "x_range": [-3, 17],
                                  "socket": "SteeringWheel", "align_x": True, "uv_slots": [T + "INTERIOR"]}}
# gauges on the cluster (normal (-0.95, 0, 0.30): 17.5 deg back): uv (u, row) -> car space via uv_to_3d
TILT = math.degrees(math.asin(0.30)); NRM = (-0.954, 0.0, 0.30)
def sock(name, p):
    return {"name": name, "loc": [round(p[k] + 0.4 * NRM[k], 2) for k in range(3)], "rot": [0, -90, round(-90 + TILT, 1)]}
s["dashboard"] = {"sockets": [sock("Niddle_Speed", (35.13, 45.31, 60.23)), sock("Niddle_RPM", (35.5, 35.62, 61.4)),
                              sock("Niddle_Fuel", (35.86, 28.52, 62.56)), sock("Niddle_Temp", (34.37, 28.82, 57.75))],
                  "parent_socket": "SteeringWheel"}
s["gauge_faces"] = {T + "INTERIOR": [
    {"center": [0.785, 0.355], "face": [0.785, 0.355, 0.2], "radius": 0.19, "min": 0, "max": 120, "text_step": 20,
     "line_step": 10, "start": 140, "end": 400, "font": 0.17, "captions": [["MPH", 0.32, 90]], "caption_font": 0.12}]}
s["gauge_ranges"] = {"RPM": {"max": 8}, "Speed": {"max": 120}}

# ---- body kits + sockets
s["mw_kits"] = {"front_split": 160.0, "rear_split": -160.0}
s["sockets"] = {"Body": [
    {"name": "Exhaust_Left", "loc": [-210, 60, 12], "rot": [0, 180, 0]}, {"name": "Exhaust_Right", "loc": [-210, -60, 12], "rot": [0, 180, 0]},
    {"name": "RearWing", "loc": [-200, 0, 72], "rot": [0, 0, 0]},
    {"name": "TaxiRoofSign", "loc": [-45, 0, 107], "rot": [0, 0, 0]},
    {"name": "TrailerHitch", "loc": [-214, 0, 22], "rot": [0, 0, 0]}]}
# ---- liveries: full-body MW vinyl sets only (user rule from the Cayman; small stickers -> global decals later)
BL = ["01RAZORCALLAHAN", "02TUROSATO", "03RONNIEMCCREA", "04JOEVEGA", "05WESALLEN", "06HECTORDOMINGO", "07KIRANAZAKATO",
      "08JADEBARRETT", "09PIERREDUPONT", "10KARLSMIT", "11LOUPARK", "12ISABELDIAZ", "13VICTORVASQUEZ", "14VINCEKILIC",
      "15TONYHO"]
pick = (["BODY%02d" % i for i in range(1, 13)] + ["BODYFLAME%02d" % i for i in (1, 2, 3, 4, 5, 6, 7, 8, 10)]
        + ["BODYTRIBAL%02d" % i for i in range(1, 11)] + ["BODYSTRIPE%02d" % i for i in range(1, 11)]
        + BL + ["CARBONFIBER", "COPGTO", "BMW_24", "CROSS"])
s["skins"] = {"dir": "~/nfs-work/db/mwr/RX7FC/vin/textures", "pick": pick,
              "labels": {b: "Blacklist " + b[:2] + " " + b[2:].title() for b in BL}}
# ---- user 2026-11-20: static needles, unlit gauges, pop-ups, white badge backing
# MW's own 3D needles + hub (white swatches) sat over the game's live needles ("painted-on lines")
s["meshes"]["Body"]["drop_uv_boxes"] = [
    {"slot": T + "INTERIOR", "uv": [0.56, 0.79, 0.63, 0.85], "box": [28, 20, 52, 38, 50, 68], "note": "needles (white triangle art)"},
    {"slot": T + "INTERIOR", "uv": [0.66, 0.83, 0.72, 0.89], "box": [28, 20, 52, 38, 50, 68], "note": "tach hub"}]
# night glow: cluster faces -> Gauges slot, glow masked to the six dial circles (u, row, r)
s["meshes"]["Body"]["uv_split"] = [{"from": T + "INTERIOR", "to": "Gauges", "box": [0.12, 0.12, 1.0, 1.0],
                                     "box3d": [28, 20, 52, 38, 50, 68]}]
s["emissive_slots"] = {"Gauges": {"texture_slot": T + "INTERIOR", "glow": 2.0, "mask_from_gauges": True,
                                  "glow_circles": [[0.786, 0.781, 0.21], [0.244, 0.649, 0.115], [0.479, 0.649, 0.115],
                                                   [0.244, 0.884, 0.115], [0.474, 0.884, 0.115]]}}
# badges: the BADGING atlas has real alpha (white RGB where transparent)
s["masked_texture_slots"] = sorted(set(s.get("masked_texture_slots", [])) | {T + "BADGING"})
# pop-ups: closed lids = KIT00 hood lid panels; lamp pods = the STYLE02 hood's raised pods turned back down by the
# lid angle. Fit KIT00 lid -> STYLE02 lid: 20 deg front-up about (x 175, z 49), median error 0.2 cm.
HINGE, ANG = [175.0, 49.0], 20.0
pod = []
for sy in (-1, 1):
    lid_box = [165, 36, 36, 206, 70, 58] if sy > 0 else [165, -70, 36, 206, -36, 58]
    pod.append({"part": "KIT00_HOOD", "box": lid_box})
    pbox = [168, 36, 10, 212, 72, 60] if sy > 0 else [168, -72, 10, 212, -36, 60]
    xf = {"xform": {"rot_y": {"deg": ANG, "pivot": HINGE}}}
    pod.append(dict(xf, part="STYLE02_HOOD", groups=[0, 3, 4, 6, 7], box=pbox))
    pod.append(dict(xf, part="STYLE02_HOOD", groups=[2, 5], box=pbox, slot="HeadPod"))
s["meshes"]["Popup"] = {"parts": pod}
s["popup"] = {"hinge": HINGE, "angle": ANG, "seconds": 0.5,
              "note": "MW KIT00 (closed) vs STYLE02 (raised) hood lids: 20 deg about (175, 49)"}
s["lamp_slots"]["HeadPod"] = {"kind": "head", "texture_slot": HEAD}
s["final_slot_names"]["HeadPod"] = "HeadLight"
s["blueprint"].setdefault("cdo_names", {})["BodyMaterialName"] = "Body"   # pods painted natively (Fortem paint = Body)
s["part_overrides"]["Headlight"] = "MW_RX7FC_Popup"
s["blueprint"]["components"].update({"HeadLight_Left_GEN_VARIABLE": [205, -53, 45], "HeadLight_Right_GEN_VARIABLE": [205, 53, 45]})
s.pop("TODO", None)
json.dump(s, open(ROOT + "cars/mw_rx7fc.json", "w"), indent=1)
print("wrote cars/mw_rx7fc.json (%s)" % STAGE)
