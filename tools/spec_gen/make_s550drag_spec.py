"""Spec for the BeamNG Ford Shelby GT500 drag car (s550pewpiw mod, "Drag (A)" = config GT500_DCT + wheelie bar + drag
wheels; value 200000) -> cars/bng_gt500d.json. Built on the finished GT350R port (same S550 body, lamps, seats,
mirrors, wheels position); parts from bng/bng_to_parts.py (~/nfs-work/bng/s550drag/geo, prefix S550D) incl. every
bumper / hood / spoiler / fender variant of the mod as garage upgrades (user 2026-11-16: the twin-turbo hood etc.
purchasable). Drivetrain = the mod's own (user 2026-11-16): Voodoo torque table + roots supercharger, ECU limiter 7500,
7-speed DCT 3.397/2.186/1.626/1.285/1.029/0.839/0.634 R2.79, final 3.73, LSD. Digital dash: the game's
W_TachoWithDigitalSpeed (tach + digital speed, as the Kuda trucks), fuel/temp and the MFD drawn on the GT500's LCD.
usage: python tools/spec_gen/make_s550drag_spec.py"""
import copy, glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEO = os.path.expanduser("~/nfs-work/bng/s550drag/geo").replace("\\", "/")
TEX = os.path.expanduser("~/nfs-work/bng/s550drag/textures").replace("\\", "/")
CAR, PFX = "BNG_GT500D", "S550D"
g = json.load(open(os.path.join(ROOT, "cars", "bng_gt350r.json")))
s = copy.deepcopy(g)

parts = sorted(os.path.basename(f)[len(PFX) + 1:-len("_A.dae")] for f in glob.glob(GEO + "/%s_*_A.dae" % PFX))
mats = sorted({m for f in glob.glob(GEO + "/*.dae") for m in re.findall(r'<material id="m\d+" name="([^"]+)"', open(f).read())})


def tex_slot(m):
    return "Tex_BNG_" + re.sub(r"[^A-Za-z0-9]+", "_", m).upper().strip("_")


# garage parts: slot -> [(row suffix, display name, [parts], extra opts)]; first = stock GT500
KITS = {
    "FrontBumper": [("GT500", "Shelby GT500 Front Bumper", ["S550_BUMPER_F_GT500"]),
                    ("GT", "Mustang GT Front Bumper", ["S550_BUMPER_F_GT"]),
                    ("ECOBOOST", "EcoBoost Front Bumper", ["S550_BUMPER_F_ECOBOOST"]),
                    ("FL_GT", "Mustang GT Facelift Front Bumper", ["S550_BUMPER_F_FACELIFT_GT"]),
                    ("FL_ECOBOOST", "EcoBoost Facelift Front Bumper", ["S550_BUMPER_F_FACELIFT_ECOBOOST"]),
                    ("GT350", "Shelby GT350 Front Bumper", ["S550_BUMPER_F_GT350"]),
                    ("GT350R", "Shelby GT350R Front Bumper", ["S550_BUMPER_F_GT350R"]),
                    ("BULLITT", "Bullitt Front Bumper", ["S550_BUMPER_F_BULLITT"]),
                    ("RTR", "RTR Front Bumper", ["S550_BUMPER_F_RTR"]),
                    ("RTR_FL", "RTR Facelift Front Bumper", ["S550_BUMPER_F_RTR_FACELIFT"]),
                    ("DEBERTI", "DeBerti Front Bumper", ["S550_BUMPER_F_DEBERTI"]),
                    ("MACH1", "Mach 1 Front Bumper", ["S550_BUMPER_F_MACH1"])],
    "RearBumper": [("GT500", "Shelby GT500 Rear Bumper", ["S550_BUMPER_R_GT500"]),
                   ("FL", "Facelift Rear Bumper", ["S550_BUMPER_R_FACELIFT"]),
                   ("FL_DIFF", "Facelift Rear Bumper + Diffuser", ["S550_BUMPER_R_FACELIFT", "S550_BUMPER_R_FACELIFT_DIFFUSER"]),
                   ("GT350", "Shelby GT350 Rear Bumper", ["S550_BUMPER_R_GT350"]),
                   ("DEBERTI", "DeBerti Rear Bumper", ["S550_BUMPER_R_DEBERTI"]),
                   ("MACH1", "Mach 1 Rear Bumper", ["S550_BUMPER_R_MACH1"]),
                   ("MACH1_ALT", "Mach 1 Rear Bumper (alt decals)", ["S550_BUMPER_R_MACH1_ALT"])],
    "Bonnet": [("GT500", "Shelby GT500 Hood", ["S550_HOOD_GT500"]),
               ("TWIN", "Twin Turbo Hood", ["S550_HOOD_TWIN"]),
               ("TWIN2", "Twin Turbo Hood (smooth)", ["S550_HOOD_TWIN2"]),
               ("GT", "Mustang GT Hood", ["S550_HOOD"]),
               ("FL", "Facelift Hood", ["S550_HOOD_FACELIFT"]),
               ("GT350", "Shelby GT350 Hood", ["S550_HOOD_GT350"]),
               ("DEBERTI", "DeBerti Hood", ["S550_HOOD_DEBERTI"]),
               ("MACH1", "Mach 1 Hood", ["S550_HOOD_MACH1"]),
               ("MACH1_ALT", "Mach 1 Hood (alt decals)", ["S550_HOOD_MACH1_ALT"])],
    "Fender": [("GT500", "Shelby GT500 Fenders", ["S550_FENDER_L_GT500", "S550_FENDER_R_GT500", "S550_FENDERBADGE_L_GT500", "S550_FENDERBADGE_R_GT500"]),
               ("GT", "Mustang GT Fenders", ["S550_FENDER_L", "S550_FENDER_R"]),
               ("FL", "Facelift Fenders", ["S550_FENDER_L_FACELIFT", "S550_FENDER_R_FACELIFT"]),
               ("GT350", "Shelby GT350 Fenders", ["S550_FENDER_L_GT350", "S550_FENDER_R_GT350"]),
               ("DEBERTI", "DeBerti Fenders", ["S550_FENDER_L_DEBERTI", "S550_FENDER_R_DEBERTI"])],
    "RearWing": [("GT500", "Shelby GT500 Wing", ["S550_WING_GT500_A", "S550_WING_GT500_B", "S550_WING_GT500_C", "S550_WING_GT500_D"]),
                 ("GT", "Mustang GT Spoiler", ["S550_SPOILER"]),
                 ("FL", "Facelift Spoiler", ["S550_SPOILER_FACELIFT"]),
                 ("GT350", "Shelby GT350 Spoiler", ["S550_SPOILER_GT350"]),
                 ("GT350R", "Shelby GT350R Wing", ["S550_SPOILER_GT350R"]),
                 ("RTR", "RTR Spoiler", ["S550_SPOILER_RTR"]),
                 ("RTR_FL", "RTR Facelift Spoiler", ["S550_SPOILER_RTR_FACELIFT"]),
                 ("MACH1", "Mach 1 Spoiler", ["S550_SPOILER_MACH1"])],
}
WING_SOCKET = [-215.0, 0.0, 99.0]           # trunk-lid top (spoilers sit from z 98.2); wing meshes offset by -socket
kit_parts = {p for rows in KITS.values() for _, _, ps in rows for p in ps}
WHEEL = {"S550_WHEEL_06A_20X11", "TIRE_01H_20X11_25_S550"}
STEER = "S550_STEER_GT500"
MIRROR_HOUSINGS = {"S550_MIRROR_L", "S550_MIRROR_R"}
SKIP = {"S550_BRAKEDISC_FL_SPORT", "S550_BRAKEDISC_FR_SPORT", "S550_BRAKEDISC_RL_SPORT", "S550_BRAKEDISC_RR_SPORT",
        "S550_CALIPER_F_SPORT", "S550_CALIPER_R_SPORT", "S550_HALFSHAFT_R", "S550_HUB_F", "S550_HUB_R",
        "S550_WINDSHIELD_INT", "S550_BACKLIGHT_INT", "S550_SIDEGLASS_L_INT", "S550_SIDEGLASS_R_INT",
        "S550_DOORGLASS_L_INT", "S550_DOORGLASS_R_INT", "S550_INTMIRROR",
        # analog cluster fallback + the LCD's static mini screens: the game's widgets draw the digital dash instead
        "S550_GAUGES", "S550_GAUGEGLASS", "S550_GAUGES_SCREEN", "S550_GAUGES_RPM_LCD", "S550_GAUGES_SPEED_LCD",
        "S550_BUMPER_R"}                      # plain rear bumper: its flexbody lands 7 m to the side (broken in the mod)
body_parts = [p for p in parts if p not in WHEEL | SKIP | kit_parts | {STEER}]
body_parts = [{"part": p, "skip_groups": [0]} if p in MIRROR_HOUSINGS else p for p in body_parts]

# materials: the GT350R's mapping, new ones as their own texture slots
slots, sources = dict(g["texture_slots"]), dict(g["texture_sources"])
for m in mats:
    if m not in slots:
        slots[m] = tex_slot(m); sources[tex_slot(m)] = m + ".png"
slots["s550_lcd_b"] = "Bottom"               # the LCD panel itself (flat grey placeholder in the mod) = black screen
sources = {k: v for k, v in sources.items() if k in set(slots.values())}

s.update({
    "car": CAR, "display_name": "Ford Shelby GT500 Drag (BeamNG)", "prefix": PFX,
    "geometry_dir": GEO, "texture_dir": TEX,
    "out_dir": os.path.expanduser("~/mt-work/build/%s/meshes" % CAR).replace("\\", "/"),
    "cost": 200000, "wheel_display_name": "Shelby GT500 Stock 20in (BeamNG)",
    "texture_slots": slots, "texture_sources": sources,
    "mesh_names": {"Wheel_L": CAR + "_L", "Wheel_R": CAR + "_R", "SteeringWheel": CAR},
})
s["meshes"] = {
    # not reduced: the separate livery layer (garage part) has to lie exactly over the full-detail paint surface
    "Body": {"parts": body_parts + [{"part": STEER, "slot": tex_slot("s550_steeringwheel")}], "reduce": 0.4},
    "SideMirror_L": g["meshes"]["SideMirror_L"], "SideMirror_R": g["meshes"]["SideMirror_R"],
    "Wheel_L": {"parts": [{"part": "S550_WHEEL_06A_20X11"}, {"part": "TIRE_01H_20X11_25_S550"}], "reduce": 0.5},
    "Wheel_R": {"parts": [{"part": "S550_WHEEL_06A_20X11", "mirror": True}, {"part": "TIRE_01H_20X11_25_S550", "mirror": True}], "reduce": 0.5},
}
aero = []
for slot, rows in KITS.items():
    for i, (tag, name, ps) in enumerate(rows):
        mesh = "Aero_%s_%s" % (slot, tag)
        off = [-WING_SOCKET[k] for k in range(3)] if slot == "RearWing" else None
        s["meshes"][mesh] = {"parts": [dict({"part": p}, **({"offset": off} if off else {})) for p in ps], "aero": True}
        aero.append({"row": "%s_%s_%s" % (CAR, slot, tag), "slot": slot, "part_type": slot, "mesh": mesh,
                     "display_name": name + ("" if i else " (stock)")})
s["aero_parts"] = aero
s["sockets"] = {"Body": [{"name": "RearWing", "loc": WING_SOCKET, "rot": [0, 0, 0],
                          "note": "trunk-lid top: game universal wings sit here; our wing meshes are offset by -loc"}]}
s["extract"]["SteeringWheel"]["uv_slots"] = [tex_slot(m) for m in mats if "steer" in m or m in (
    "s550_steeringwheel", "s550_capsule", "s550_symbols_embossed", "s550_symbols_gt350")]

# digital dash on the 30 x 8.7 cm LCD (x 43.7, MT y -50.6..-20.9, z 85.9..94.6): MFD | tach + digital speed | fuel, temp
for k in ("gauge_faces", "gauge_style", "texture_upscale"):
    s.pop(k, None)
s["emissive_slots"] = {k: v for k, v in g["emissive_slots"].items() if k != "Gauges"}
X, ZC = 43.55, 90.25                       # 0.15 cm in front of the panel
s["dashboard"] = {
    "sockets": [{"name": "Niddle_RPM", "loc": [X - 0.1, -35.75, ZC], "rot": [0, -90, -90]},
                {"name": "Niddle_Fuel", "loc": [X - 0.1, -28.7, ZC], "rot": [0, -90, -90]},
                {"name": "Niddle_Temp", "loc": [X - 0.1, -23.6, ZC], "rot": [0, -90, -90]}],
    "screens": [{"slot": "TachoMeter", "center": [X, -35.75, ZC], "width": 8.4, "height": 8.4},
                {"slot": "Dashboard_MFD_01", "center": [X, -45.6, ZC], "width": 9.6, "height": 4.8},
                {"slot": "FuelGauge", "center": [X, -28.7, ZC], "width": 4.4, "height": 4.4},
                {"slot": "TempGauge", "center": [X, -23.6, ZC], "width": 4.4, "height": 4.4}]}
s["gauge_widgets"] = {"Gauges/W_Tachometer": "Gauges/W_TachoWithDigitalSpeed"}
s["gauge_text"] = {"RPM": "Speed"}
s["gauge_drop"] = ["Speed"]
s["gauge_ranges"] = {"RPM": {"max": 8}}
s["needle_scales"] = {"RPM": 0.8, "Fuel": 0.8, "Temp": 0.8}

# drivetrain = the mod's (s550_engine_voodoo + supercharger stage 1 + ECU 7500 + 7DCT + 3.73 LSD)
TQ = [[1000, 266], [1500, 400], [2000, 466], [2500, 506], [3000, 533], [3500, 552], [4000, 566], [4500, 577], [5000, 581],
      [5500, 576], [6000, 565], [6500, 548], [7000, 527], [7500, 499], [8000, 451]]
# user 2026-11-16: keep the mod's full output (no scaling to the road car): torque x internals stage1 torqueModMult x
# roots boost (1.5 psi per 1k crank rpm x 1.6 drive ratio, as a pressure ratio over 14.7 psi)
MULT = [[0, .9], [1000, .91], [2000, .91], [3000, .99], [4000, 1.11], [5000, 1.22], [6000, 1.4], [7000, 1.5], [8000, 1.6], [9000, 1.7]]
def lerp(tb, x):
    for (x0, y0), (x1, y1) in zip(tb, tb[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return tb[-1][1]
boosted = [(r, t * lerp(MULT, r) * (1 + 1.5 * 1.6 * r / 1000 / 14.7)) for r, t in TQ]
peak = max(t for r, t in boosted if r <= 7500)
LIM = 7500
curve = [[round(r / LIM, 4), round(t / peak, 3)] for r, t in boosted] + [[5.0, 0.15]]
FD = 3.73 / 3.31
DCT = {"R": -2.79, "1": 3.397, "2": 2.186, "3": 1.626, "4": 1.285, "5": 1.029, "6": 0.839, "7": 0.634}
snd = g["custom_parts"]["engines"][0]["sound_cue"]
s["custom_parts"] = {
    "transmissions": [{"row": CAR + "_7DCT", "base_row": "6SpeedSportsLP670", "asset": CAR + "_7DCT",
                       "base_asset": "Cars/Parts/Transmission/Manual6SpeedSports_LP670",
                       "display_name": "Tremec 7-Speed DCT (Shelby GT500)", "cost": 12000, "mass": 120,
                       "ratios": {k: round(v * FD, 3) for k, v in DCT.items()},
                       "note": "mod s550_transmission_7DCT; real final 3.73 folded in (game row FD_3.31): ratio x 3.73/3.31"}],
    "engines": [{"row": CAR + "_PREDATOR", "base_row": "SmallBlock_320HP", "asset": CAR + "_PREDATOR",
                 "base_asset": "Cars/Parts/Engine/S58", "display_name": "5.2 Supercharged V8 (Shelby GT500 Drag)",
                 "mass": 230, "cost": 90000, "max_torque_nm": round(peak), "max_rpm": LIM, "curve": curve,
                 "curve_note": "mod torque table x internals stage1 mult x roots boost, unscaled (user); ECU limiter 7500",
                 "physics_from": "Cars/Parts/Engine/FordSmalBlock302_V8_5L_320HP", "idle_throttle": 0.0009,
                 "sound_cue": dict(snd, dir=CAR, note="the mod's GT500 recordings are not in the pack: its Voodoo (GT350R) loops")}]}
s["part_overrides"] = dict(g["part_overrides"], **{
    "Engine": CAR + "_PREDATOR", "Transmission": CAR + "_7DCT", "FinalDriveRatio": "FD_3.31",
    "Wheel0": "BNG_Rims_DWVSkinny", "Wheel1": "BNG_Rims_DWVSkinny", "Wheel2": "BNG_Rims_DWVSWide", "Wheel3": "BNG_Rims_DWVSWide",
    "Tire2": "PerformanceDragTireStrip", "Tire3": "PerformanceDragTireStrip"})
for slot, rows in KITS.items():
    s["part_overrides"][slot] = "%s_%s_%s" % (CAR, slot, rows[0][0])
s["strip_part_slots"] = ["Bonnet", "FrontBumper", "RearBumper", "RearWing"]
# 'Race Queen' livery (mod paint_design s550_skin_drag, mapped on the second UV set: re-extract with
# BNG_UV1_MATS=s550_paint): a masked decal layer lifted over the paint, so the body stays paintable under it
SKIN = "Tex_BNG_S550_SKIN_DRAG"
s["texture_slots"]["s550_skin_drag"] = SKIN; s["texture_sources"][SKIN] = "s550_skin_drag.png"
# user 2026-11-17: the livery switchable like a paint scheme -> its own garage part (slot SideSkirt, unused on this car):
# a mesh made only of the lifted livery layer over the Body and the stock GT500 panels; "No Livery" = a few hidden
# triangles under the fuel tank. (0.05 lift clipped at the door handle when the Body was UE-reduced; now unreduced)
LIV_PARTS = [p for p in body_parts] + [p for _, rows in KITS.items() for p in rows[0][2] if "WING" not in p]
s["overlay_textures"] = {"s550_paint": {"base": "Paint", "slot": SKIN, "lift": 0.08, "meshes": ["Aero_SideSkirt_RACEQUEEN"]}}
keep = {SKIN}
s["meshes"]["Aero_SideSkirt_RACEQUEEN"] = {"parts": LIV_PARTS, "aero": True,
    "drop_slots": sorted((set(slots.values()) | {"Paint", "Bottom", "Glass", "Trim", "Mirror"}) - keep)}
s["meshes"]["Aero_SideSkirt_NONE"] = {"parts": [{"part": "S550_FUELTANK", "only_boxes": [[-90, 0, 14, -70, 20, 20]]}], "aero": True}
s["aero_parts"] += [
    {"row": CAR + "_SideSkirt_RACEQUEEN", "slot": "SideSkirt", "part_type": "SideSkirt", "mesh": "Aero_SideSkirt_RACEQUEEN",
     "display_name": "'Race Queen' Livery (stock)"},
    {"row": CAR + "_SideSkirt_NONE", "slot": "SideSkirt", "part_type": "SideSkirt", "mesh": "Aero_SideSkirt_NONE",
     "display_name": "No Livery"}]
s["part_overrides"]["SideSkirt"] = CAR + "_SideSkirt_RACEQUEEN"
s["masked_texture_slots"] = [SKIN]
s["performance_source"] = ("BeamNG s550pewpiw Drag (A) / GT500_DCT: s550_engine_voodoo + v8 internals stage1 + roots "
                           "supercharger stage1, ECU 7500, 7DCT, final 3.73 LSD; real 2020 GT500 760 hp @7300, 625 lb-ft @5000, 1916 kg")
s["blueprint"] = dict(g["blueprint"], body_mass=g["blueprint"]["body_mass"] + 150)   # GT500 is ~150 kg over the GT350R
# user 2026-11-17: seating position 2 cm higher (seats + first-person camera)
s["blueprint"]["seats"] = {k: [v[0], v[1], v[2] + 2] for k, v in g["blueprint"]["seats"].items()}
s["blueprint"]["cockpit_camera"] = [g["blueprint"]["cockpit_camera"][0], g["blueprint"]["cockpit_camera"][1], g["blueprint"]["cockpit_camera"][2] + 2]
s.pop("TODO", None)
s["note"] = "drag GT500 2026-11-16 from the GT350R port: garage kits, mod drivetrain, digital dash (game widgets)"
# user 2026-11-17: every S550 mod part purchasable on both Mustangs (kits, wheelie bar, liveries as paint schemes,
# engines / gearboxes): shared with the GT350R port (tools/spec_gen/s550_parts.py); this car's own parts are the defaults
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s550_parts import apply
apply(s, {"FrontBumper": "GT500", "RearBumper": "GT500", "Bonnet": "GT500", "Fender": "GT500", "RearWing": "GT500", "Trunk": "WHEELIEBAR"})
out = os.path.join(ROOT, "cars", "bng_gt500d.json")
json.dump(s, open(out, "w"), indent=1)
print("-> %s: %d body parts, %d garage parts, curve peak %.0f Nm raw" % (out, len(body_parts), len(aero), peak))
