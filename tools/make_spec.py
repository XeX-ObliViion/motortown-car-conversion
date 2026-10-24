"""Bootstrap a car spec from the car database (db/cars.json, tools/nfs_db.py) so a new port starts from facts.

Fills: car key, prefix, dirs, source_scale, base template (by base vehicle), texture_slots (known shared hashes +
the car's own textures by role), Body parts (stock parts, game naming), wheels radius, performance (engine curve in
N·m, gears, nearest FinalDriveRatio row, body_mass), engine sound hint. Leaves a "TODO" list for the measured steps
(steering wheel, dials, lamps, mirrors, seats/eye, stance, sockets, kits, dealer bay) - see the skill checklist.
usage: make_spec.py <game:CAR e.g. mw:CORVETTEC6R> <base: Cora|Fortem|Tuscan|Zino|Vista|Magis> <out cars/<name>.json> [CAR_KEY]"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# base vehicle -> a finished spec on that base, used as the template for blueprint/mirror/lamp/dashboard patterns
TEMPLATES = {"Cora": "mw_m3gtr", "Fortem": "mw_993rwb", "Tuscan": "challenger71", "Zino": "350z", "Vista": "skyline",
             "Magis": "supra"}
# material hashes seen across cars (same meaning in both games unless noted)
SHARED = {"0x65FF171E": "Paint", "0xBEBC83C2": "Paint", "0xE5F6A5ED": "Bottom", "0x027FF2DC": "Bottom", "0xCC772AFB": "Bottom",
          "0xCC7AEEF9": "Bottom", "0xBF30889B": "Trim", "0xE4CEA024": "Bottom", "0xE4CEA025": "Bottom", "0x4441A26B": "Trim",
          "0x48A68363": "Trim", "0x7B220DDF": "Glass", "0xD195BE56": "Glass", "0x1B049702": "Bottom", "0x41751DC1": "Bottom",
          "0x721AFF7C": "Bottom", "0x4C95C6F8": "Bottom", "0xE38806E3": "Bottom", "0x4E8CF857": "Bottom"}
FD_ROWS = [("101", 2.73), ("102", 3.08), ("FD_3.31", 3.31), ("103", 3.55), ("104", 3.73), ("105", 4.0), ("112", 4.11),
           ("111", 4.27), ("106", 4.56), ("107", 4.78)]


def main():
    key, base, out = sys.argv[1], sys.argv[2], sys.argv[3]
    db = json.load(open(os.path.join(ROOT, "db", "cars.json")))
    r = db[key]
    game, car = r["game"], r["car"]
    ck = sys.argv[4] if len(sys.argv) > 4 else ("%s_%s" % ("MW" if game == "mw" else "PS", re.sub(r"[^A-Z0-9]", "", car.upper())))
    t = json.load(open(os.path.join(ROOT, "cars", TEMPLATES[base] + ".json")))
    keep = ("base_vehicle", "base_wheel", "default_slot", "keep_body_materials", "final_slot_names", "blueprint",
            "mirror_components", "mirror_meshes", "strip_part_slots", "wheel_part")
    s = {k: json.loads(json.dumps(t[k])) for k in keep if k in t}
    s.update({"car": ck, "display_name": "%s (%s)" % (car.title(), "Most Wanted" if game == "mw" else "ProStreet"),
              "prefix": car if game == "mw" else car + "_KIT00", "geometry_dir": r["geometry_dir"], "texture_dir": r["texture_dir"],
              "out_dir": "~/mt-work/build/%s/meshes" % ck, "cost": 100000, "base_vehicle": base,
              "wheel_display_name": "%s Stock" % car.title(), "source_scale": 100.0 if game == "mw" else 1000.0})
    ts = dict(SHARED)
    if r.get("paint_guess"):
        ts[r["paint_guess"]] = "Paint"
    tx = r.get("textures", {})
    srcs = {}
    for h, n in tx.items():
        role = None
        for pat, rl in ((r"INTERI|DRIVER", "INTERIOR"), (r"HEADLI", "HEADLIGHT"), (r"BRAKEL", "BRAKELIGHT"), (r"BADGING$", "BADGING"),
                        (r"MISC$", "MISC"), (r"(?<!_)RIM$|WHEEL$", "WHEEL"), (r"ENGINE$", "ENGINE")):
            if re.search(pat, n) and not re.search(r"STYLE\d|_N$|DAMAG|GLASS", n):
                role = rl; break
        if role:
            slot = "Tex_%s_%s" % (ck.split("_", 1)[1], role)
            if slot not in srcs.values():
                ts[h] = slot; srcs[h] = slot
    s["texture_slots"] = ts
    s["texture_sources"] = {v: k for k, v in srcs.items()}   # pick textures by hash (MW dump names are unreliable)
    # Body: stock parts in game naming (windows -> Glass); wheels from the stock tyre
    body = []
    for p in r.get("stock_parts", []):
        if re.search(r"DAMAGE|DECAL|DRIVER|TIRE|BRAKE$|_BRAKE|ROLL_CAGE|SPOILER|HOOD", p):
            continue
        body.append({"part": p, "slot": "Glass"} if "WINDOW" in p else p)
    tyre = next((p for p in r.get("stock_parts", []) if "FRONT_TIRE" in p or "WHEEL_TIRE_FRONT" in p), None)
    s["meshes"] = {"Body": {"parts": body}}
    if tyre:
        part = tyre if game == "mw" else tyre.replace("KIT00_", "")
        s["meshes"]["Wheel_L"] = {"parts": [{"part": part, "offset": [0, 11.0, 0]}], "slot_rename": {"Trim": "Bottom"}}
        s["meshes"]["Wheel_R"] = {"parts": [{"part": part, "mirror": True, "offset": [0, -11.0, 0]}], "slot_rename": {"Trim": "Bottom"}}
    s["mesh_names"] = {"Wheel_L": ck + "_R", "Wheel_R": ck + "_L", "SteeringWheel": ck}
    s["wheels"] = {"front_x": 140, "rear_x": -130, "half_track": 76, "z": 20, "rear_z": 20, "radius": r.get("wheel_radius", 33), "auto_arches": True}
    # performance
    pf = r.get("performance", {})
    cp = {"engines": [], "transmissions": []}
    curve = pf.get("torque_lbft") and [[rpm, v * 1.3558] for rpm, v in pf["torque_lbft"]] or pf.get("torque_nm")
    if curve and pf.get("max_rpm"):
        pk = max(v for _, v in curve); mx = pf["max_rpm"]
        cp["engines"].append({"row": ck + "_ENG", "base_row": "SmallBlock_320HP", "asset": ck + "_ENG", "base_asset": "Cars/Parts/Engine/S58",
                              "display_name": "%s engine" % car.title(), "mass": 220, "cost": 30000, "max_torque_nm": round(pk, 1),
                              "max_rpm": mx, "curve": [[round(rpm / mx, 4), round(v / pk, 4)] for rpm, v in curve] + [[5.0, 0.15]],
                              "curve_note": "from db %s; sound: cut GIN loops (%s) or pick a More Tuning engine" % (key, pf.get("gin_accel"))})
    g = pf.get("gears")
    if g and len(g) > 3:
        fw = [x for x in g[2:] if x > 0]
        cp["transmissions"].append({"row": ck + "_%dMT" % len(fw), "base_row": "6SpeedSportsLP670", "asset": ck + "_%dMT" % len(fw),
                                    "base_asset": "Cars/Parts/Transmission/Manual6SpeedSports_LP670", "display_name": "%d-Speed (%s)" % (len(fw), car.title()),
                                    "cost": 8000, "mass": 100, "ratios": dict([("R", -abs(g[0]))] + [(str(i + 1), x) for i, x in enumerate(fw)])})
    s["custom_parts"] = cp
    po = {k: v for k, v in t.get("part_overrides", {}).items() if k.startswith(("Tire", "BrakePad", "CoolantRadiator"))}
    if cp["engines"]:
        po["Engine"] = cp["engines"][0]["row"]
    if cp["transmissions"]:
        po["Transmission"] = cp["transmissions"][0]["row"]
    if pf.get("final_gear"):
        po["FinalDriveRatio"] = min(FD_ROWS, key=lambda x: abs(x[1] - pf["final_gear"]))[0]
    for w in ("Wheel0", "Wheel1", "Wheel2", "Wheel3"):
        po[w] = ck
    s["part_overrides"] = po
    if pf.get("mass"):
        s["blueprint"]["body_mass"] = int(pf["mass"] - 220 - 100 - 136)
    s["performance_source"] = "db %s: %s" % (key, {k: pf.get(k) for k in ("mass", "final_gear", "red_line", "max_rpm", "peak_hp_est")})
    s["TODO"] = ["render parts (tools/render_car.py) and fix texture_slots / Body parts", "steering wheel extract (front render)",
                 "dial sockets + gauge_faces (uv_to_3d)", "lamps: signal rules (amber survey / uv_box)", "mirrors (fortem_mirror_aim for shared-mesh bases)",
                 "seats + cockpit_camera + RoomMirror", "stance from arch edges (skill: stance reference per base)", "sockets: exhaust / RearWing",
                 "kits: add_body_kits(_mw).py", "skins (vinyl_check %s)" % r.get("vinyl_check"), "engine sound", "dealer bay (user F6)"]
    json.dump(s, open(out, "w"), indent=1)
    print("wrote %s (%s on %s): %d body parts, %d textures, engine %s, gearbox %s" % (
        out, ck, base, len(body), len(srcs), bool(cp["engines"]), bool(cp["transmissions"])))


if __name__ == "__main__":
    main()
