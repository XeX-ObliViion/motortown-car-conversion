"""Shared S550 (BeamNG s550pewpiw mod) garage parts for every Mustang port from that mod (user 2026-11-17: all the mod's
parts purchasable on both, GT350R and GT500 drag): body kits (aero rows), the wheelie bar, the mod's 9 liveries as
garage paint schemes (skins), and its engines / gearboxes (user 2026-11-17: fit every car, like the base rows: VehicleTypes Small + Pickup).
Kit and wheelie-bar meshes come from the drag extraction (~/nfs-work/bng/s550drag/geo, prefix S550D: every variant, with
the paint on BeamNG's second UV set = the livery layout).
usage: from s550_parts import apply; apply(spec, stock={...})   (both spec generators call it)"""
import os

GEO = os.path.expanduser("~/nfs-work/bng/s550drag/geo").replace("\\", "/")
TEX = os.path.expanduser("~/nfs-work/bng/s550drag/textures").replace("\\", "/")
SKIN_SRC = os.path.expanduser("~/mt-work/bng/s550/vehicles/s550").replace("\\", "/")
CARS = ["BNG_GT350R", "BNG_GT500D"]          # every S550 port: the engine / gearbox rows fit all of them
SRC = {"prefix": "S550D", "geo": GEO}

# slot -> [(tag, display name, [S550D parts])]
KITS = {
    "FrontBumper": [("GT500", "Shelby GT500 Front Bumper", ["S550_BUMPER_F_GT500"]),
                    ("GT350R", "Shelby GT350R Front Bumper", ["S550_BUMPER_F_GT350R"]),
                    ("GT350", "Shelby GT350 Front Bumper", ["S550_BUMPER_F_GT350"]),
                    ("GT", "Mustang GT Front Bumper", ["S550_BUMPER_F_GT"]),
                    ("ECOBOOST", "EcoBoost Front Bumper", ["S550_BUMPER_F_ECOBOOST"]),
                    ("FL_GT", "Mustang GT Facelift Front Bumper", ["S550_BUMPER_F_FACELIFT_GT"]),
                    ("FL_ECOBOOST", "EcoBoost Facelift Front Bumper", ["S550_BUMPER_F_FACELIFT_ECOBOOST"]),
                    ("BULLITT", "Bullitt Front Bumper", ["S550_BUMPER_F_BULLITT"]),
                    ("RTR", "RTR Front Bumper", ["S550_BUMPER_F_RTR"]),
                    ("RTR_FL", "RTR Facelift Front Bumper", ["S550_BUMPER_F_RTR_FACELIFT"]),
                    ("DEBERTI", "DeBerti Front Bumper", ["S550_BUMPER_F_DEBERTI"]),
                    ("MACH1", "Mach 1 Front Bumper", ["S550_BUMPER_F_MACH1"])],
    "RearBumper": [("GT500", "Shelby GT500 Rear Bumper", ["S550_BUMPER_R_GT500"]),
                   ("GT350", "Shelby GT350 Rear Bumper", ["S550_BUMPER_R_GT350"]),
                   ("FL", "Facelift Rear Bumper", ["S550_BUMPER_R_FACELIFT"]),
                   ("FL_DIFF", "Facelift Rear Bumper + Diffuser", ["S550_BUMPER_R_FACELIFT", "S550_BUMPER_R_FACELIFT_DIFFUSER"]),
                   ("DEBERTI", "DeBerti Rear Bumper", ["S550_BUMPER_R_DEBERTI"]),
                   ("MACH1", "Mach 1 Rear Bumper", ["S550_BUMPER_R_MACH1"]),
                   ("MACH1_ALT", "Mach 1 Rear Bumper (alt decals)", ["S550_BUMPER_R_MACH1_ALT"])],
    "Bonnet": [("GT500", "Shelby GT500 Hood", ["S550_HOOD_GT500"]),
               ("GT350", "Shelby GT350 Hood", ["S550_HOOD_GT350"]),
               ("TWIN", "Twin Turbo Hood", ["S550_HOOD_TWIN"]),
               ("TWIN2", "Twin Turbo Hood (smooth)", ["S550_HOOD_TWIN2"]),
               ("GT", "Mustang GT Hood", ["S550_HOOD"]),
               ("FL", "Facelift Hood", ["S550_HOOD_FACELIFT"]),
               ("DEBERTI", "DeBerti Hood", ["S550_HOOD_DEBERTI"]),
               ("MACH1", "Mach 1 Hood", ["S550_HOOD_MACH1"]),
               ("MACH1_ALT", "Mach 1 Hood (alt decals)", ["S550_HOOD_MACH1_ALT"])],
    "Fender": [("GT500", "Shelby GT500 Fenders", ["S550_FENDER_L_GT500", "S550_FENDER_R_GT500", "S550_FENDERBADGE_L_GT500", "S550_FENDERBADGE_R_GT500"]),
               ("GT350", "Shelby GT350 Fenders", ["S550_FENDER_L_GT350", "S550_FENDER_R_GT350"]),
               ("GT", "Mustang GT Fenders", ["S550_FENDER_L", "S550_FENDER_R"]),
               ("FL", "Facelift Fenders", ["S550_FENDER_L_FACELIFT", "S550_FENDER_R_FACELIFT"]),
               ("DEBERTI", "DeBerti Fenders", ["S550_FENDER_L_DEBERTI", "S550_FENDER_R_DEBERTI"])],
    "RearWing": [("GT500", "Shelby GT500 Wing", ["S550_WING_GT500_A", "S550_WING_GT500_B", "S550_WING_GT500_C", "S550_WING_GT500_D"]),
                 ("GT350R", "Shelby GT350R Wing", ["S550_SPOILER_GT350R"]),
                 ("GT350", "Shelby GT350 Spoiler", ["S550_SPOILER_GT350"]),
                 ("GT", "Mustang GT Spoiler", ["S550_SPOILER"]),
                 ("FL", "Facelift Spoiler", ["S550_SPOILER_FACELIFT"]),
                 ("RTR", "RTR Spoiler", ["S550_SPOILER_RTR"]),
                 ("RTR_FL", "RTR Facelift Spoiler", ["S550_SPOILER_RTR_FACELIFT"]),
                 ("MACH1", "Mach 1 Spoiler", ["S550_SPOILER_MACH1"])],
    # the drag wheelie bar as an add-on (Trunk slot: free on the Tuscan base); "none" = 4 hidden fuel-tank triangles
    "Trunk": [("WHEELIEBAR", "Drag Wheelie Bar", ["S550_WHEELIEBAR"]),
              ("NONE", "No Wheelie Bar", [])],
}
KIT_PARTS = {p for rows in KITS.values() for _, _, ps in rows for p in ps}
WING_SOCKET = [-215.0, 0.0, 99.0]           # trunk-lid top (spoilers sit from z 98.2); wing meshes offset by -socket

# the mod's paint_design liveries (s550.jbeam): BeamNG skins are colour masks over the paint. "Race Queen": grey
# 129,128,129 = paint; stripes: red = paint 1, green = paint 2 (offered in black and in white); police: black = paint;
# the itasha / Snivy designs cover the whole car
LIVERIES = [("drag", "'Race Queen' Livery", "grey", None), ("police", "Police Livery", "black", None),
            ("stripes", "Stripes (black)", "red", (15, 15, 15)), ("stripes", "Stripes (white)", "red", (240, 240, 240)),
            ("stripes_gt500", "GT500 Stripes (black)", "red", (15, 15, 15)), ("stripes_gt500", "GT500 Stripes (white)", "red", (240, 240, 240)),
            ("racestripealt", "Racing Stripes Asymmetrical (black)", "red", (15, 15, 15)),
            ("racestripealt", "Racing Stripes Asymmetrical (white)", "red", (240, 240, 240)),
            ("racestripe", "Racing Stripes Triple (black)", "red", (15, 15, 15)),
            ("racestripe", "Racing Stripes Triple (white)", "red", (240, 240, 240)),
            ("snivy", "Snivy Livery", None, None), ("dia", "Dia Kurosawa Itasha", None, None),
            ("mai", "Mai Sakurajima Itasha", None, None)]


def livery_pngs():
    """-> {label: png path}: each mod livery as an RGBA vinyl (alpha 0 where the car's paint shows)."""
    from PIL import Image
    import numpy as np
    out = {}
    for name, label, clear, col in LIVERIES:
        a = np.array(Image.open("%s/s550_skin_%s.dds" % (SKIN_SRC, name)).convert("RGBA")).astype(int)
        rgb = a[..., :3]
        if clear == "grey":
            d = np.abs(rgb - np.array([129, 128, 129])).max(-1); a[..., 3] = np.clip((d - 6) * 40, 0, 255)
        elif clear == "black":
            a[..., 3] = np.clip((rgb.max(-1) - 12) * 12, 0, 255)
        elif clear == "red":
            # green share = stripe coverage (antialiased edges blend red -> green)
            g = rgb[..., 1] / np.maximum(1, rgb[..., 0] + rgb[..., 1])
            a[..., 3] = np.clip(g * 255, 0, 255); a[..., :3] = col
        png = "%s/s550_livery_%s%s.png" % (TEX, name, "" if col is None else "_" + ("black" if col[0] < 128 else "white"))
        Image.fromarray(a.astype("uint8")).save(png)
        out[label] = png
    return out


# ------------------------------------------------------------------ engines / gearboxes (the mod's own drivetrains)
def lerp(tb, x):
    if x <= tb[0][0]:
        return tb[0][1]
    for (x0, y0), (x1, y1) in zip(tb, tb[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return tb[-1][1]


def engine(row, name, tq, lim, base_row, base_asset, mass, cost, boost=None, real_peak=None, note="", sound_dir=None):
    """mod torque table (Nm by rpm) x forced-induction factor (1 + psi / 14.7), as the drag GT500; factory engines with
    a published rating (EcoBoost, Hellcat) are scaled to it (user's drag GT500 stays unscaled by request)."""
    pts = [(r, t * (1 + (boost(r) if boost else 0) / 14.7)) for r, t in tq if r > 0]
    peak = max(t for r, t in pts if r <= lim)
    k = real_peak / peak if real_peak else 1.0
    e = {"row": row, "base_row": base_row, "asset": row, "base_asset": base_asset, "display_name": name,
         "mass": mass, "cost": cost, "max_torque_nm": round(peak * k), "max_rpm": lim,
         "curve": [[round(r / lim, 4), round(t / peak, 3)] for r, t in pts] + [[5.0, 0.15]],
         "curve_note": note, "physics_from": base_asset, "idle_throttle": 0.0009}
    if sound_dir:
        e["sound_cue"] = {"cue_base": "Cars/Parts/Engine/Sound/s58/SC_V8Engine", "dir": sound_dir,
                          "loops": [["l%d" % (i + 1), r] for i, r in enumerate([800, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000])],
                          "note": "the mod's own Forza Mustang GT recordings (art/sound/engine/fm7/for_mustanggt_15, Exhaust on_*)"}
    return e


I4 = [[1000, 245], [1500, 257], [2000, 267], [2500, 279], [3000, 285], [3500, 286], [4000, 282], [4500, 269], [5000, 258], [5500, 248], [6000, 229], [6500, 204], [7000, 198]]
V6 = [[1000, 179], [1500, 268], [2000, 313], [2500, 340], [3000, 358], [3500, 370], [4000, 380], [4500, 378], [5000, 372], [5500, 361], [6000, 347], [6500, 328], [6800, 303], [7000, 300]]
V8 = [[1000, 262], [1500, 393], [2000, 459], [2500, 498], [3000, 524], [3500, 543], [4000, 557], [4600, 570], [5000, 567], [5500, 556], [6000, 535], [6500, 504], [7000, 468], [7500, 437]]
HC = [[500, 507], [1000, 579], [2000, 605], [3000, 628], [4000, 644], [4500, 653], [5000, 660], [5500, 666], [6000, 670], [6500, 660]]
H64 = [[500, 447], [1000, 499], [2000, 546], [3000, 568], [4000, 599], [4500, 623], [5000, 635], [5500, 644], [6000, 624], [6500, 590]]
I6 = [[500, 140], [1000, 390], [1500, 330], [2000, 350], [2500, 350], [3000, 350], [3500, 351], [4000, 360], [4500, 371], [5000, 380], [5500, 364], [6000, 334], [6500, 320], [7000, 300], [7500, 265], [8000, 230], [8500, 207], [9000, 190]]
EB_EFF = [[0, 0], [900, .08], [1000, .09], [1500, .27], [2000, .9], [2500, 1]]
TT_EFF = [[0, 0], [650, .17], [1400, .29], [2000, .41], [2500, .54], [3000, .65], [4000, .79], [5000, .88], [6000, .93], [7000, .9]]

ENGINES = [
    engine("BNG_S550_ECOBOOST", "2.3L EcoBoost I4 Turbo (S550)", I4, 6500, "I4_150HP", "Cars/Parts/Engine/I4Sport_150HP", 150, 12000,
           boost=lambda r: 13.7 * lerp(EB_EFF, r), real_peak=434,
           note="mod s550_engine_i4 + stock turbo (wastegate 13.7 psi, spool table); real 2015-17 rating 434 Nm (320 lb-ft), ECU 6500"),
    engine("BNG_S550_V6", "3.7L Cyclone V6 (S550)", V6, 6800, "V6Sport_400HP", "Cars/Parts/Engine/V6Sport_DOHC_200HP", 170, 9000,
           note="mod s550_engine_v6 NA table (380 Nm, = the real 3.7), V6 ECU 6800"),
    engine("BNG_S550_COYOTE", "5.0L Coyote V8 (S550)", V8, 7000, "SmallBlock_320HP", "Cars/Parts/Engine/S58", 200, 20000,
           note="mod s550_engine NA table (570 Nm @4600), stock ECU 7000", sound_dir="BNG_S550_COYOTE"),
    engine("BNG_S550_HEMI64", "6.4L HEMI V8 (S550)", H64, 6000, "SmallBlock_320HP", "Cars/Parts/Engine/Hemi392_525HP", 230, 26000,
           note="mod challenger_engine_6.4 NA table (644 Nm), stock ECU 6000"),
    engine("BNG_S550_HELLCAT", "6.2L Supercharged Hellcat V8 (S550)", HC, 6000, "SmallBlock_320HP", "Cars/Parts/Engine/Hemi392_525HP", 250, 60000,
           boost=lambda r: min(1.9 * 1.65 * r / 1000, 11.6), real_peak=881,
           note="mod challenger_engine_hellcat + Hellcat roots supercharger (1.9 psi/1k x 1.65, real 11.6 psi); real 881 Nm (650 lb-ft), ECU 6000"),
    engine("BNG_S550_ITSJUSTA6_SC", "itsjusta6 I6 Supercharged (S550 drag)", I6, 8500, "SmallBlock_320HP", "Cars/Parts/Engine/S58", 210, 45000,
           boost=lambda r: 24 * 0.065 * r / 1000,
           note="mod ryls550_engine1 + VMP supercharger (24 psi/1k x 0.065), Holley ECU 8500; fictional drag engine, unscaled"),
    engine("BNG_S550_ITSJUSTA6_TT", "itsjusta6 I6 Twin Turbo (S550 drag)", I6, 8500, "SmallBlock_320HP", "Cars/Parts/Engine/S58", 215, 50000,
           boost=lambda r: 12 * lerp(TT_EFF, r),
           note="mod ryls550_engine + twin turbos (boost-by-gear default 12 psi, spool table), Holley ECU 8500; fictional, unscaled"),
]
FD = 3.73 / 3.31          # both ports run the 3.73 final drive on the game's FD_3.31 row: folded into the gear ratios


def gearbox(row, name, ratios, base_asset, cost, mass, note):
    keys = ["R"] + [str(i + 1) for i in range(len(ratios) - 1)]
    return {"row": row, "base_row": "6SpeedSportsLP670", "asset": row, "base_asset": base_asset, "display_name": name,
            "cost": cost, "mass": mass, "ratios": {k: round(v * FD, 3) for k, v in zip(keys, ratios)},
            "note": note + "; real final 3.73 folded in (game row FD_3.31)"}


GEARBOXES = [
    gearbox("BNG_S550_6MT", "Getrag MT82 6-Speed (S550)", [-3.73, 4.236, 2.538, 1.665, 1.2387, 1.0, 0.704],
            "Cars/Parts/Transmission/Manual6SpeedSports_LP670", 5000, 90, "mod s550_transmission_6M"),
    gearbox("BNG_S550_6MT_GT", "Getrag MT82 6-Speed GT (S550)", [-3.73, 3.657, 2.43, 1.686, 1.315, 1.0, 0.651],
            "Cars/Parts/Transmission/Manual6SpeedSports_LP670", 5500, 90, "mod s550_transmission_6M_gt"),
    gearbox("BNG_S550_6AT", "6R80 6-Speed Automatic (S550)", [-3.4, 4.17, 2.34, 1.52, 1.14, 0.86, 0.69],
            "Cars/Parts/Transmission/TQ4SpeedMuscle", 6000, 100, "mod s550_transmission_6A on the game torque-converter automatic (7.20: More Tuning bases no longer parse)"),
    gearbox("BNG_S550_10AT", "10R80 10-Speed Automatic (S550)", [-4.86, 4.7, 2.99, 2.15, 1.77, 1.52, 1.28, 1.0, 0.85, 0.69, 0.64],
            "Cars/Parts/Transmission/TQ4SpeedMuscle", 9000, 105, "mod s550_transmission_10A on the game torque-converter automatic"),
]


def apply(spec, stock):
    """Add the shared S550 garage parts to a Mustang spec. stock = {slot: tag} of the car's own (default) parts.
    Strips those parts out of the Body (they become the slot's default rows)."""
    car = spec["car"]
    body = spec["meshes"]["Body"]["parts"]
    pname = lambda p: p if isinstance(p, str) else p["part"]
    spec["meshes"]["Body"]["parts"] = [p for p in body if pname(p) not in KIT_PARTS]
    for k in [k for k in spec["meshes"] if k.startswith("Aero_")]:
        del spec["meshes"][k]
    aero = []
    for slot, rows in KITS.items():
        rows = sorted(rows, key=lambda r: r[0] != stock[slot])           # the car's own part first
        for tag, name, ps in rows:
            mesh = "Aero_%s_%s" % (slot, tag)
            off = [-x for x in WING_SOCKET] if slot == "RearWing" else None
            parts = [dict(SRC, part=p, **({"offset": off} if off else {})) for p in ps] or \
                    [dict(SRC, part="S550_FUELTANK", only_boxes=[[-90, 0, 14, -70, 20, 20]])]
            spec["meshes"][mesh] = {"parts": parts, "aero": True}
            aero.append({"row": "%s_%s_%s" % (car, slot, tag), "slot": slot, "part_type": slot, "mesh": mesh,
                         "display_name": name + (" (stock)" if tag == stock[slot] else "")})
        spec.setdefault("part_overrides", {})[slot] = "%s_%s_%s" % (car, slot, stock[slot])
    spec["aero_parts"] = aero
    # kit materials the car never had (Mach 1 decals, Shelby badges, the wheelie bar's tyre): own texture slots,
    # textures from the drag extraction
    import glob, re
    for p in KIT_PARTS | {"S550_FUELTANK"}:
        for f in glob.glob("%s/S550D_%s_A.dae" % (GEO, p)):
            for m in re.findall(r'<material id="m\d+" name="([^"]+)"', open(f).read()):
                if m in spec["texture_slots"] or m.startswith("s550_paint") and m == "s550_paint":
                    continue
                if m in ("s550_glass", "s550_glass_int"):
                    spec["texture_slots"][m] = "Glass"; continue
                slot = "Tex_BNG_" + re.sub(r"[^A-Za-z0-9]+", "_", m).upper().strip("_")
                spec["texture_slots"][m] = slot; spec["texture_sources"][slot] = m + ".png"
                spec.setdefault("texture_dirs", {})[slot] = TEX
    socks = [x for x in spec.setdefault("sockets", {}).setdefault("Body", []) if x["name"] != "RearWing"]
    spec["sockets"]["Body"] = socks + [{"name": "RearWing", "loc": WING_SOCKET, "rot": [0, 0, 0],
                                        "note": "trunk-lid top: game universal wings sit here; our wing meshes are offset by -loc"}]
    spec["strip_part_slots"] = sorted(set(spec.get("strip_part_slots", [])) | {"Bonnet", "FrontBumper", "RearBumper", "RearWing", "Trunk", "Fender"})
    # liveries = garage paint schemes (skins: the game's BodyMaterialList, vinyl over the paint colour on paint UV0)
    spec["skins"] = {"dir": TEX, "pick": [], "baked": livery_pngs()}
    for k in ("overlay_textures", "masked_texture_slots"):
        spec.pop(k, None)
    spec["texture_slots"].pop("s550_skin_drag", None)
    spec["texture_sources"].pop("Tex_BNG_S550_SKIN_DRAG", None)
    for k in [k for k in spec["meshes"] if k.startswith("Aero_SideSkirt_")]:
        del spec["meshes"][k]
    spec["part_overrides"].pop("SideSkirt", None)
    # the mod's engines / gearboxes: rows (with their assets) live in the GT500D spec, limited to the S550 ports
    if car == "BNG_GT500D":
        cp = spec.setdefault("custom_parts", {})
        cp["engines"] = [e for e in cp.get("engines", []) if not e["row"].startswith("BNG_S550_")] + ENGINES
        cp["transmissions"] = [t for t in cp.get("transmissions", []) if not t["row"].startswith("BNG_S550_")] + GEARBOXES
    return spec
