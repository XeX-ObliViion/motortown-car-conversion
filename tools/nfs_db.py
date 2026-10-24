"""Car database for NFS ProStreet and NFS Most Wanted (Rework IV): one record per drivable car, so a new port starts
from facts instead of re-surveying (see the skill section "Car database").

Per car (cached exports in ~/nfs-work/db/<game>/<CAR>/{geo,tex,vin}):
  parts (KIT00 / BASE), kit bodies, STYLE parts, triangle counts (body, interior, base), bounding box, wheel radius,
  material hashes with use counts and the paint guess, the car's textures by hash, lamp / interior / badge textures,
  vinyl check (does the paint UV0 follow the car's DEBUG vinyl layout?), and from the game databases: torque curve,
  rpm, gears, final drive, mass, engine sound files.
Output: db/cars.json (+ db/cars.md overview).  usage: nfs_db.py [ps|mw|all] [CAR ...]"""
import json, math, os, re, subprocess, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps_to_mt as P   # noqa: E402

HOME = os.path.expanduser("~")
AD = os.path.join(HOME, "tools/assetdumper-x86/AssetDumper.exe")
GAMES = {
    "ps": {"root": r"C:/Program Files (x86)/Electronic Arts/Need for Speed ProStreet/CARS", "ad": "ProStreet", "scale": 1000.0,
           "vlt": os.path.join(HOME, "nfs-work/ps_vlt/main/attributes/db")},
    "mw": {"root": r"D:/SSD GANG/Need for Speed - Most Wanted Rework IV/CARS", "ad": "MostWanted", "scale": 100.0,
           "vlt": os.path.join(HOME, "nfs-work/mw_vlt/main/attributes/db")},
}
SKIP = ("COP", "TRAF", "TRAILER", "TRANE", "PLATES", "SPOILER", "WHEELS", "BRAKE", "ROOF", "RAMP", "YTMRIM", "MOB",
        "RESCHELI", "CEMTR", "GARB", "PIZZA", "TAXI", "BUS", "SEMI", "PETERBILT", "MINIVAN", "PICKUPA", "GROUP", "VINYLS",
        "EXHAUST", "DAMAGE", "SEAT", "ROOFSCOOP")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db")


def export(game, car, what):
    g = GAMES[game]
    src = os.path.join(g["root"], car, what.upper() + ".BIN")
    dst = os.path.join(HOME, "nfs-work/db", game, car, {"geometry": "geo", "textures": "tex", "vinyls": "vin"}[what])
    if not os.path.exists(src):
        return None
    if not os.path.isdir(dst) or not os.listdir(dst):
        subprocess.run([AD, "export", src, "-g", g["ad"], "-o", dst], capture_output=True)
    return dst


def yml_records(path):
    """Tiny reader for Attribulator yml: {record name: text block}."""
    if not os.path.exists(path):
        return {}
    s = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(r"^- ParentName: .*\n  Name: (\S+)\n", s, re.M):
        start = m.end(); nxt = s.find("\n- ParentName:", start)
        out[m.group(1)] = s[start: nxt if nxt > 0 else len(s)]
    return out


def floats_after(block, key):
    m = re.search(r"\b%s:\s*\n(?:\s+Capacity: \d+\n)?\s+Data:\s*\n((?:\s+- [-0-9.eE]+\n)+)" % key, block)
    return [float(x) for x in re.findall(r"- ([-0-9.eE]+)", m.group(1))] if m else None


def scalar(block, key):
    m = re.search(r"\b%s: ([-0-9.eE]+)" % key, block)
    return float(m.group(1)) if m else None


_VLT = {}


def vlt(game, table):
    key = (game, table)
    if key not in _VLT:
        _VLT[key] = yml_records(os.path.join(GAMES[game]["vlt"], table + ".yml"))
    return _VLT[key]


def performance(game, car):
    lc = car.lower()
    if game == "ps":
        r = vlt("ps", "vehicle").get(lc + "_track") or ""
        tq = r and re.search(r"TORQUE:\s*\n\s+MinX: ([0-9.]+)\s+MaxX: ([0-9.]+)\s+MinY: ([0-9.]+)\s+MaxY: ([0-9.]+)", r)
        out = {"mass": scalar(r, "MASS"), "final_gear": scalar(r, "FINAL_GEAR"), "red_line": scalar(r, "RED_LINE"),
               "max_rpm": scalar(r, "MAX_RPM"), "gears": floats_after(r, "GEAR_RATIO")}
        if tq:
            xs, ys = floats_after(r, "XValues") or [], floats_after(r, "YValues") or []
            x0, x1, y0, y1 = (float(v) for v in tq.groups())
            out["torque_nm"] = [[round(x0 + x * (x1 - x0)), round(y0 + y * (y1 - y0), 1)] for x, y in zip(xs, ys)]
        return out
    pv = vlt("mw", "pvehicle")
    name = next((k for k, v in pv.items() if re.search(r"MODEL: %s\b" % re.escape(car), v)), lc)
    rec = pv.get(name, "")
    def ref(cls):
        m = re.search(r"ClassKey: %s\s+CollectionKey: (\S+)" % cls, rec)
        return m.group(1) if m else name
    e = vlt("mw", "engine").get(ref("engine"), ""); t = vlt("mw", "transmission").get(ref("transmission"), "")
    a = vlt("mw", "engineaudio").get(ref("engineaudio"), "")
    tq = floats_after(e, "TORQUE"); idle = scalar(e, "IDLE") or 800; mx = scalar(e, "MAX_RPM")
    out = {"record": name, "mass": scalar(rec, "MASS"), "final_gear": scalar(t, "FINAL_GEAR"), "gears": floats_after(t, "GEAR_RATIO"),
           "red_line": scalar(e, "RED_LINE"), "max_rpm": mx, "engine_audio": ref("engineaudio"),
           "gin_accel": (re.search(r"Filename_GinsuAccel: (\S+)", a) or [None, None])[1]}
    if tq and mx:
        step = (mx - idle) / (len(tq) - 1)
        out["torque_lbft"] = [[round(idle + i * step), v] for i, v in enumerate(tq)]
        out["peak_hp_est"] = round(max(v * (idle + i * step) / 5252 for i, v in enumerate(tq)))
    return out


def survey(game, car):
    g = GAMES[game]; P.PS_SCALE = g["scale"]
    geo = export(game, car, "geometry")
    if not geo or not os.path.isdir(geo):
        return {"car": car, "game": game, "error": "no geometry export"}
    tex = export(game, car, "textures")
    files = [f for f in os.listdir(geo) if f.endswith("_A.dae")]
    if not files:
        return {"car": car, "game": game, "error": "export produced no parts (unsupported format?)"}
    pre = car + "_"
    names = sorted({f[:-6] for f in files})
    texnames = {}
    if tex and os.path.isdir(os.path.join(tex, "textures")):
        texnames = {f.split("_")[0]: f[11:-4] for f in os.listdir(os.path.join(tex, "textures")) if f.endswith(".dds")}
    rec = {"car": car, "game": game, "geometry_dir": geo, "texture_dir": tex and os.path.join(tex, "textures"),
           "stock_parts": [n[len(pre):] for n in names if n.startswith(pre + "KIT00_") or n == pre + "BASE"],
           "kits": sorted({m.group(1) for n in names for m in [re.match(re.escape(pre) + r"(KIT\w+?)_", n)] if m}),
           "styles": sorted({n[len(pre):] for n in names if "_STYLE" in n})[:80],
           "unprefixed_parts": [n for n in names if not n.startswith(pre)][:10]}
    mats, tris, pts = Counter(), {}, []
    for part in ("KIT00_BODY", "KIT00_INTERIOR", "BASE"):
        f = os.path.join(geo, pre + part + "_A.dae")
        if os.path.exists(f):
            grp = P.load_dae(f)
            tris[part] = sum(len(t) for _, t in grp)
            for tx, t in grp:
                mats[tx] += len(t)
                if part != "KIT00_INTERIOR":
                    pts += [P.to_mt(c[0]) for tr in t[::3] for c in tr]
    rec["tris"] = tris
    if pts:
        rec["bbox"] = [[round(min(p[k] for p in pts)), round(max(p[k] for p in pts))] for k in range(3)]
    rec["materials"] = [[h, n, texnames.get(h, "")] for h, n in mats.most_common(14)]
    plain = [h for h, n in mats.most_common() if h not in texnames]
    rec["paint_guess"] = plain[0] if plain else None
    tyre = [f for f in files if "FRONT_TIRE" in f or "WHEEL_TIRE_FRONT" in f]
    if tyre:
        wp = [P.to_mt(c[0]) for _, t in P.load_dae(os.path.join(geo, tyre[0])) for tr in t for c in tr]
        rec["wheel_radius"] = round(max(abs(p[2]) for p in wp), 1)
    rec["textures"] = texnames
    rec["lamp_textures"] = {h: n for h, n in texnames.items() if re.search(r"LIGHT|LAMP|SIDELIGHT", n)}
    rec["interior_textures"] = {h: n for h, n in texnames.items() if re.search(r"INTERI|DRIVER|DASH", n)}
    # vinyl layout check: sample the car's DEBUG vinyl at the paint UV0 of side faces (left should be red, right purple)
    vin = export(game, car, "vinyls")
    dbg = vin and os.path.isdir(os.path.join(vin, "textures")) and [f for f in os.listdir(os.path.join(vin, "textures")) if f.endswith("_DEBUG.dds")]
    if dbg and rec["paint_guess"]:
        from PIL import Image
        im = Image.open(os.path.join(vin, "textures", dbg[0])).convert("RGB"); W, H = im.size
        hit = tot = 0
        body = os.path.join(geo, pre + ("KIT00_BODY" if os.path.exists(os.path.join(geo, pre + "KIT00_BODY_A.dae")) else "BASE") + "_A.dae")
        for tx, t in P.load_dae(body):
            if tx != rec["paint_guess"]:
                continue
            for tr in t[::2]:
                ny = sum(P.nrm_mt(c[1])[1] for c in tr) / 3
                if abs(ny) < 0.8:
                    continue
                u = sum(c[2][0] for c in tr) / 3; v = sum(c[2][1] for c in tr) / 3
                r, g_, b = im.getpixel((int(u % 1 * W) % W, int((1 - v) % 1 * H) % H))
                tot += 1
                hit += (r > 180 and g_ < 90 and b < 90) if ny < 0 else (b > 180 and r > 90 and g_ < 90)
        rec["vinyl_check"] = round(hit / tot, 2) if tot else None
        rec["vinyl_count"] = len([f for f in os.listdir(os.path.join(vin, "textures")) if f.endswith(".dds") and "MASK" not in f])
    rec["performance"] = performance(game, car)
    return rec


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = set(sys.argv[2:])
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "cars.json")
    db = json.load(open(path)) if os.path.exists(path) else {}
    for game in (["ps", "mw"] if which == "all" else [which]):
        root = GAMES[game]["root"]
        for car in sorted(os.listdir(root)):
            if not os.path.isdir(os.path.join(root, car)) or car.startswith(SKIP) or (only and car not in only):
                continue
            if not os.path.exists(os.path.join(root, car, "GEOMETRY.BIN")):
                continue
            try:
                r = survey(game, car)
            except Exception as ex:   # keep going: one odd car must not stop the database
                r = {"car": car, "game": game, "error": repr(ex)[:200]}
            db["%s:%s" % (game, car)] = r
            json.dump(db, open(path, "w"), indent=1)
            print(game, car, r.get("error") or "%s tris body, vinyl %s, %s hp" % (
                r.get("tris", {}).get("KIT00_BODY"), r.get("vinyl_check"),
                r.get("performance", {}).get("peak_hp_est", "?")), flush=True)
    write_md(db)


def write_md(db):
    rows = ["| game | car | body tris | interior tris | kits | wheel r | paint | vinyls (fit) | mass | power |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in sorted(db.items()):
        if r.get("error"):
            rows.append("| %s | %s | error: %s | | | | | | | |" % (r["game"], r["car"], r["error"][:60])); continue
        pf = r.get("performance", {})
        power = pf.get("peak_hp_est") and "%s hp" % pf["peak_hp_est"] or (pf.get("torque_nm") and "%s N·m pk" % max(t for _, t in pf["torque_nm"])) or ""
        rows.append("| %s | %s | %s | %s | %d | %s | %s | %s (%s) | %s | %s |" % (
            r["game"], r["car"], r.get("tris", {}).get("KIT00_BODY", ""), r.get("tris", {}).get("KIT00_INTERIOR", ""),
            len(r.get("kits", [])), r.get("wheel_radius", ""), r.get("paint_guess", ""), r.get("vinyl_count", ""),
            r.get("vinyl_check", ""), pf.get("mass", ""), power))
    open(os.path.join(OUT, "cars.md"), "w", encoding="utf-8").write(
        "# NFS ProStreet + Most Wanted car database\n\nGenerated by tools/nfs_db.py; full records in cars.json.\n\n" + "\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
