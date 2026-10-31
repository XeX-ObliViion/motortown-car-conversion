"""Most Wanted (Rework IV) garage parts on a car already ported from ProStreet (same real car in both games).

The MW model of the car is fitted onto the ProStreet body (ICP on surface samples, per-axis scale + offset in Motor Town
cm), then every MW-only piece is added as extra garage parts labelled "Most Wanted ...", next to the ProStreet ones:
  * FrontBumper / RearBumper: each MW KITnn_BODY cut ahead of / behind the ProStreet stock bumper's inner edge, minus
    what lies on the ProStreet body (drop_coincident_with); the rear keeps the ProStreet exhaust,
  * SideSkirt: MW kits' sills / flares (KITnn_BODY between the cuts, minus what lies on the ProStreet panels that stay
    fitted; the ProStreet skirts come off, so the MW sill must fill their place),
  * Bonnet: MW KIT00_HOOD and STYLEnn_HOOD (+ STYLEnn_ATTACHMENTn scoops),
  * RearWing: the car's own MW spoilers (KIT00 / STYLEnn / ALTnn / NEW_STYLEnn), shifted into the RearWing socket.
MW materials: the MW paint hash -> Paint, shared hashes as in make_spec, the MW car's own textures as new slots
"Tex_MW<CAR>_<name>" read from the MW texture dir (texture_dirs). Rows are tagged "mw": true so a re-run replaces them.
usage: add_mw_parts.py <cars/<ps spec>.json> <MW CAR e.g. SUPRA> [--fit-only]"""
import json, os, re, sys
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ps_to_mt as P                                    # load_dae
from make_spec import SHARED

MW_SCALE = 100.0
GLOBAL_TEX = os.path.expanduser("~/nfs-work/mwglobal_tex/textures")   # AssetDumper export of MW GLOBAL/GLOBALB.LZC


def samples(paths, scale, step=4.0):
    """area-weighted surface points (MT cm) of the DAEs"""
    pts = []
    for path in paths:
        if not os.path.exists(path):
            continue
        for _, tris in P.load_dae(path):
            for t in tris:
                a, b, c = (np.array([cn[0][0] * scale, -cn[0][1] * scale, cn[0][2] * scale]) for cn in t)
                area = np.linalg.norm(np.cross(b - a, c - a)) / 2
                n = max(1, int(area / (step * step)))
                r = np.random.default_rng(len(pts)).random((n, 2))
                r[r.sum(1) > 1] = 1 - r[r.sum(1) > 1]
                pts.append(a + r[:, :1] * (b - a) + r[:, 1:] * (c - a))
    return np.vstack(pts)


def fit(src, dst, iters=30):
    """per-axis s, t with dst ~ s*src + t. The Rework IV models of cars ProStreet also has are (near-)copies in the same
    space, so start at identity and refine with trimmed one-way ICP (MW body+hood -> ProStreet body+bumpers+hood;
    the MW stock body is roughly a subset), scale clamped to +-3%."""
    s, t = np.ones(3), np.zeros(3)
    td = cKDTree(dst)
    d0, _ = td.query(src)
    for it in range(iters):
        d, i = td.query(src * s + t)
        m = d <= min(np.percentile(d, 60), 4.0)
        A, B = src[m], dst[i[m]]
        for k in range(3):
            if k == 1:
                s[1] = np.dot(A[:, 1], B[:, 1]) / np.dot(A[:, 1], A[:, 1]); t[1] = 0
            else:
                M = np.vstack([A[:, k], np.ones(len(A))]).T
                s[k], t[k] = np.linalg.lstsq(M, B[:, k], rcond=None)[0]
        s = np.clip(s, 0.97, 1.03)
    d, _ = td.query(src * s + t)
    if np.median(d) >= np.median(d0):
        s, t, d = np.ones(3), np.zeros(3), d0
    return s, t, float(np.median(d)), float(np.percentile(d, 90))


def main():
    spec_path, mw = sys.argv[1], sys.argv[2].upper()
    spec = json.load(open(spec_path))
    db = json.load(open(os.path.join(ROOT, "db", "cars.json")))
    r = db["mw:" + mw]
    mgeo = os.path.expanduser(r["geometry_dir"])
    mtex = os.path.expanduser(r["texture_dir"])
    pgeo = os.path.expanduser(spec["geometry_dir"])
    pbase = spec["prefix"].rsplit("_KIT", 1)[0]
    pk = pbase + "_KIT00"
    pfile = lambda part: os.path.join(pgeo, "%s_%s_A.dae" % (pk, part))
    mfile = lambda part: os.path.join(mgeo, "%s_%s_A.dae" % (mw, part))
    files = set(os.listdir(mgeo))
    ps_ref = ["BODY", "TRUNK", "DOOR_LEFT", "DOOR_RIGHT", "BUMPER_FRONT", "BUMPER_REAR", "HOOD", "SKIRT_LEFT",
              "SKIRT_RIGHT", "FENDER_FRONT_LEFT", "FENDER_FRONT_RIGHT"]
    ps_scale = spec.get("source_scale", 1000.0)
    dst = samples([pfile(p) for p in ps_ref], ps_scale, step=1.0)
    src = samples([mfile("KIT00_BODY"), mfile("KIT00_HOOD")], MW_SCALE)
    s, t, med, p90 = fit(src, dst)
    print("%s <- MW %s: s=%s t=%s  residual median %.2f cm, 90%% %.2f cm" % (spec["car"], mw, np.round(s, 4),
                                                                               np.round(t, 2), med, p90))
    if "--fit-only" in sys.argv:
        return
    xf = {"s": [round(float(v), 5) for v in s], "t": [round(float(v), 3) for v in t]}
    src_opts = {"geo": r["geometry_dir"], "src_scale": MW_SCALE, "xform": xf, "prefix": mw}

    def bx(parts):   # x extent (MT cm) of ProStreet stock pieces
        xs = [cn[0][0] * ps_scale for p in parts if os.path.exists(pfile(p)) for _, tr in P.load_dae(pfile(p))
              for tri in tr for cn in tri]
        return (min(xs), max(xs)) if xs else None
    fb, rb = bx(["BUMPER_FRONT"]), bx(["BUMPER_REAR", "BUMPER_REAR_EXTRA"])
    F = fb[0] if fb else 120.0
    R = rb[1] if rb else -120.0
    car_parts = {p if isinstance(p, str) else p["part"] for m in spec["meshes"].values() if not m.get("aero")
                 for p in m.get("parts", [])}
    # everything the ProStreet car keeps showing (body, doors, glass, lamps...): MW kit triangles lying on it are dropped
    ref = sorted(p for p in car_parts | {"BODY"} if os.path.exists(pfile(p)) and not re.search(r"TIRE|WHEEL|RIM|BRAKE$|DRIVER|SEAT", p))
    ps_dc = {"parts": ref, "prefix": pk, "tol": 1.5}
    mw_dc = dict(src_opts, parts=["KIT00_BODY"], tol=1.0)
    exhaust = [{"part": "EXHAUST", "prefix": pk, "align_to_grille": {"regex": "GRILL|MESH", "max": 35.0}}] if os.path.exists(pfile("EXHAUST")) else []
    # MW kit shells repeat the body sides / panel edges a little off the ProStreet surface (the two models are near
    # copies, not identical): drop what lies on or under the ProStreet panels that stay fitted (flicker, dark shards),
    # keep what stands proud of them (lips, sills, flares) and what is away from them (where the replaced part was)
    # (the stock ProStreet fenders / hood / bumpers are garage parts: Aero_<slot>_KIT00 meshes, not the Body)
    stock = lambda *slots_: [p["part"] if isinstance(p, dict) else p for sl in slots_
                             for p in spec["meshes"].get("Aero_%s_KIT00" % sl, {}).get("parts", [])
                             if (p.get("prefix", pk) if isinstance(p, dict) else pk) == pk]
    vis = lambda drop, extra: {"prefix": pk, "tol": 2.5, "far": 6.0,
                               "parts": sorted({p for p in ref + extra if not re.search(drop, p)
                                                and not re.search(r"GLASS|WINDOW|BASE", p) and os.path.exists(pfile(p))})}
    ds_kit = vis(r"BUMPER|SKIRT|EXHAUST", stock("Fender", "Bonnet"))
    ds_hood = vis(r"HOOD", stock("Fender", "FrontBumper"))
    # nearest-part trimming: every ProStreet stock piece, labelled; the slot's own stock parts are the ones replaced
    allps = sorted({p for p in ref + stock("Fender", "Bonnet", "FrontBumper", "RearBumper", "SideSkirt")
                    if os.path.exists(pfile(p)) and not re.search(r"BASE", p)})
    kn = lambda slot: {"prefix": pk, "parts": allps, "replaced": [p for p in stock(slot) if p in allps],
                       "proud": 2.5, "far": 6.0, "lamp_clear": 8.0}
    wh = spec.get("wheels", {})
    zmax = max(wh.get("z", 30), wh.get("rear_z", 30)) + wh.get("radius", 32) + 12.0   # skirts: up to the arch tops
    # the ProStreet bumper fills openings the MW kit leaves (its lamp holes sit elsewhere), never past the kit
    fill = lambda slot: [{"part": p, "prefix": pk, "fill_gaps": {"far": 4.0, "edge": 1.0, "drop_far": True}}
                         for p in stock(slot) if p in allps and not re.search(r"EXHAUST", p)]

    # drop earlier MW rows/meshes
    spec["aero_parts"] = [x for x in spec.get("aero_parts", []) if not x.get("mw")]
    spec["meshes"] = {k: v for k, v in spec["meshes"].items() if not (k.startswith("Aero_") and "_MW" in k)}
    rows = []

    # wheel-arch skin zones: the body's arch / quarter areas move into the (mandatory) Fender slot, so any widebody
    # fender row replaces them as the panel's skin instead of sitting over the stock arches
    wh = spec.get("wheels", {})
    ZR = wh.get("radius", 32) + 24.0
    ZY = wh.get("half_track", 75) - 30.0
    zl = [[wh.get("front_x", 130), wh.get("z", 30), ZR, ZY], [wh.get("rear_x", -130), wh.get("rear_z", wh.get("z", 30)), ZR, ZY]]
    zl = spec.get("arch_zones_override", zl)     # seam-following box zones (ps_to_mt zone_depth), e.g. the Viper
    zkeep, zdrop = {"mode": "keep", "list": zl, "x_range": [R, F]}, {"mode": "drop", "list": zl, "x_range": [R, F]}
    spec["arch_zones"] = zl
    # idempotent: start from the ProStreet meshes as they were before any arch zones (kept in spec["ps_meshes"])
    if "ps_meshes" not in spec:
        spec["ps_meshes"] = {k: v for k, v in spec["meshes"].items() if not (k.startswith("Aero_") and "_MW" in k)}
    spec["meshes"].update(json.loads(json.dumps(spec["ps_meshes"])))
    bparts = spec["meshes"]["Body"]["parts"]
    for i_, p_ in enumerate(bparts):
        if (p_ if isinstance(p_, str) else p_.get("part")) == "BODY":
            bparts[i_] = dict({"part": "BODY"} if isinstance(p_, str) else p_, zones=zdrop)
    for mname, m_ in spec["meshes"].items():
        if not mname.startswith("Aero_") or "_MW" in mname:
            continue
        code = mname.rsplit("_", 1)[1]
        wide = [p_ for p_ in m_["parts"] if isinstance(p_, dict) and p_.get("part") == "WIDEBODY"]
        if mname.startswith("Aero_Fender_"):
            m_["parts"] = [p_ for p_ in m_["parts"] if not (isinstance(p_, dict) and p_.get("zones"))]
            if wide:
                # ProStreet widebody: its whole shell inside the zones is the arch skin
                fend = [p_["part"] for p_ in m_["parts"] if isinstance(p_, dict) and p_.get("part", "").startswith("FENDER")
                        and p_.get("prefix") == wide[0]["prefix"]]
                m_["parts"].append({"part": "WIDEBODY", "prefix": wide[0]["prefix"], "zones": zkeep,
                                    "drop_coincident_with": {"parts": fend, "prefix": wide[0]["prefix"], "tol": 1.0,
                                                             "also": [{"prefix": pk, "parts": [p_ for p_ in stock("SideSkirt")
                                                                                               if os.path.exists(pfile(p_))]}]},
                                    "blend": {"prefix": pk, "parts": ["BODY"], "zones": zl, "band": 15.0, "max": 10.0}})
                skn = {"prefix": pk, "parts": [p_ for p_ in stock("SideSkirt") if os.path.exists(pfile(p_))], "replaced": [],
                       "proud": 1.5, "far": 6.0, "lamp_clear": 8.0, "keep_far": True}
                for p_ in wide:
                    p_["zones"] = zdrop
                for p_ in m_["parts"]:
                    if isinstance(p_, dict) and p_.get("part") == "WIDEBODY" and skn["parts"]:
                        p_["keep_nearest"] = skn      # the stock skirts stay fitted: no widebody copy on them
                # the stock arch skin wherever the widebody shell leaves the zone open (no holes)
                m_["parts"].append({"part": "BODY", "prefix": pk, "zones": zkeep, "fill_gaps": {"far": 8.0, "edge": 1.0}})
            else:
                m_["parts"].append({"part": "BODY", "prefix": pk, "zones": zkeep})
        else:
            for p_ in wide:
                p_["zones"] = zdrop

    def add(slot, code, parts, label):
        mesh = "Aero_%s_MW%s" % (slot, code)
        spec["meshes"][mesh] = {"parts": parts, "aero": True}
        if slot in ("FrontBumper", "RearBumper", "SideSkirt"):
            spec["meshes"][mesh]["min_island"] = 150.0     # cm2: loose fragments left by the trims
        if slot in ("FrontBumper", "RearBumper", "SideSkirt", "Bonnet", "Fender"):
            spec["meshes"][mesh]["double_sided"] = True     # no see-through panels from behind
        rows.append({"row": "%s_%s_MW%s" % (spec["car"], slot, code), "slot": slot, "part_type": slot, "mesh": mesh,
                     "display_name": "Most Wanted " + label, "mw": True})

    part = lambda name, **kw: dict(src_opts, part=name, **kw)
    kits = sorted({m.group(1) for f in files for m in [re.match(r"%s_(KIT\d\d)_BODY_A\.dae$" % mw, f)] if m})
    # MW exhaust tips: each MW kit body carries one marker per tip (0xBCF8A18B / 0xBD7CF15E, game space, metres);
    # the Carbon EXHAUST_STYLE01 tip (modelled at the origin, pointing into the car) goes on each, in the rear
    # bumper's fit. Replaces the ProStreet exhaust, which never matched the MW bumpers' exits
    markers = {}
    mpath = os.path.expanduser("~/nfs-work/markers/%s.markers" % mw)
    if os.path.exists(mpath):
        for line in open(mpath, encoding="utf-8", errors="ignore"):
            f_ = line.split()
            if len(f_) == 6 and f_[0] == "MARKER" and f_[2] in ("0xBCF8A18B", "0xBD7CF15E"):
                m_ = re.match(r"%s_(KIT\d\d)_BODY_A$" % mw, f_[1])
                if m_:
                    pt = (round(float(f_[3]) * 100, 2), round(-float(f_[4]) * 100, 2), round(float(f_[5]) * 100, 2))
                    markers.setdefault(m_.group(1), set()).add(pt)
    tipgeo = os.path.expanduser("~/nfs-work/db/nfsc/EXHAUST/geo")
    for k_, v_ in {"EXHAUST_CHROME": "Trim", "EXHAUST_MUFFLER": "Bottom", "EXHAUST_FACE": "Bottom"}.items():
        spec.setdefault("texture_slots", {}).setdefault(k_, v_)
    _wb_cache = {}
    def widebody(kit):
        if kit == "KIT00":
            return False
        if "base" not in _wb_cache:
            _wb_cache["base"] = cKDTree(samples([mfile("KIT00_BODY")], MW_SCALE, step=1.0) * np.array(xf["s"]) + np.array(xf["t"]))
        S_ = samples([mfile(kit + "_BODY")], MW_SCALE, step=2.0) * np.array(xf["s"]) + np.array(xf["t"])
        inz = np.zeros(len(S_), bool)
        for z_ in zl:
            inz |= np.array([P.zone_depth(z_, q, 0) is not None for q in S_])
        if inz.sum() < 50:
            return False
        d_, _ = _wb_cache["base"].query(S_[inz])
        frac = float((d_ > 2.0).mean())
        print("  %s arch zones off the stock body: %.0f%%%s" % (kit, 100 * frac, " -> widebody" if frac > 0.25 else ""))
        return frac > 0.25

    def mw_tips(kit):
        if kit not in markers or not os.path.isdir(tipgeo):
            return []
        rx = XF.get("RearBumper", xf) if carbon else xf
        sx, tx = np.array(rx["s"]), np.array(rx["t"])
        out = []
        for pt in sorted(markers[kit]):
            # side exits (marker ahead of the rear bumper, at the sill): the tip points into the car sideways
            side = pt[0] > R + 20 and abs(pt[1]) > 60
            x_ = {"s": [round(float(v), 5) for v in sx], "t": [round(float(v), 3) for v in sx * np.array(pt) + tx]}
            if side:
                x_["rot_z"] = -90.0 if pt[1] > 0 else 90.0
            out.append({"geo": tipgeo, "src_scale": MW_SCALE, "prefix": "EXHAUST", "part": "STYLE01_LEVEL1", "xform": x_})
        return out
    # Carbon split (Rework IV ports Carbon cars: same model, same space). Each MW kit shell = the Carbon base body + the
    # kit's bumpers / skirts merged; subtracting the Carbon base body leaves the kit pieces, and the Carbon stock
    # bumper / skirt pieces label them by slot along the original seams. Each slot is then fitted on its own: the
    # Carbon stock piece onto the ProStreet stock piece, so the kit pieces meet the ProStreet seams
    cgeo = os.path.expanduser("~/nfs-work/db/nfsc/%s/geo" % mw)
    carbon = os.path.isdir(cgeo) and os.path.exists(os.path.join(cgeo, "%s_KIT00_BODY_A.dae" % mw))
    XF = {}
    if carbon:
        cfile = lambda p_: os.path.join(cgeo, "%s_%s_A.dae" % (mw, p_))
        cparts = sorted({m.group(1) for f in os.listdir(cgeo) for m in [re.match(r"%s_(KIT00_[A-Z_]+?)_A\.dae$" % mw, f)] if m})
        pieces = {"FrontBumper": ["KIT00_FRONT_BUMPER"], "RearBumper": ["KIT00_REAR_BUMPER"], "SideSkirt": ["KIT00_SKIRT"]}
        base = [p_ for p_ in cparts if not re.search(r"BUMPER|SKIRT|EXHAUST|TIRE|BRAKE|DRIVER|INTERIOR|SPOILER|WINDOW|_T0$|BADGING", p_)]
        S0, T0 = np.array(xf["s"]), np.array(xf["t"])
        for slot, cps in list(pieces.items()) + [("Bonnet", ["KIT00_HOOD"])]:
            dstp = [pfile(p_) for p_ in stock(slot) if os.path.exists(pfile(p_))]
            if not dstp or not all(os.path.exists(cfile(c)) for c in cps):
                XF[slot] = xf; continue
            src = samples([cfile(c) for c in cps], MW_SCALE) * S0 + T0
            dst = samples(dstp, ps_scale, step=1.0)
            # fit on the stretch both pieces cover (a Carbon skirt also runs along the lower arches)
            inx = (src[:, 0] >= dst[:, 0].min() - 3) & (src[:, 0] <= dst[:, 0].max() + 3)
            s2, t2, med2, p902 = fit(src[inx] if inx.sum() > 100 else src, dst)
            XF[slot] = {"s": [round(float(v), 5) for v in S0 * s2], "t": [round(float(v), 3) for v in T0 * s2 + t2]}
            print("  carbon %s fit: s=%s t=%s  residual median %.2f, 90%% %.2f cm" % (slot, np.round(s2, 4), np.round(t2, 2), med2, p902))
        copt = lambda slot: {"geo": cgeo, "src_scale": MW_SCALE, "xform": XF[slot], "prefix": mw}
        def cpart(kit, slot):
            return dict(part(kit + "_BODY"), xform=XF[slot],
                        drop_coincident_with=dict(copt(slot), parts=base, tol=0.5),
                        slot_label=dict(copt(slot), pieces=pieces, keep=slot),
                        keep_nearest=kn(slot), refine_drop=4)
        spec.setdefault("mw_parts", {}).setdefault(mw, {})["carbon_slot_fit"] = XF
    for kit in kits:
        n = int(kit[3:])
        lab = "Stock" if n == 0 else "Kit %d" % n
        wb = widebody(kit)
        if carbon:
            fb, rb_, sk = cpart(kit, "FrontBumper"), cpart(kit, "RearBumper"), dict(cpart(kit, "SideSkirt"), z_max=zmax)
        else:
            fb = part(kit + "_BODY", x_range=[F, 99999], keep_nearest=kn("FrontBumper"), x_clip=True, refine_drop=4)
            rb_ = part(kit + "_BODY", x_range=[-99999, R], keep_nearest=kn("RearBumper"), x_clip=True, refine_drop=4)
            sk = part(kit + "_BODY", x_range=[R, F], keep_nearest=kn("SideSkirt"), x_clip=True, refine_drop=4, z_max=zmax)
        if wb:
            for p_ in (fb, rb_, sk):
                p_["zones"] = zdrop
            fx = XF.get("SideSkirt", xf) if carbon else xf
            knf = dict(kn("Fender"), replaced=sorted(set(["BODY"] + [p_ for p_ in stock("Fender")])),
                       keep_far=True)   # nothing stock is left inside the zones: keep vent / scoop insides (Viper Kit 3/4)
            add("Fender", kit, [dict(part(kit + "_BODY"), xform=fx, zones=zkeep, keep_nearest=knf, refine_drop=3,
                                     blend={"prefix": pk, "parts": ["BODY"] + [p_ for p_ in stock("Fender") if p_ != "BODY"],
                                            "zones": zl, "band": 15.0, "max": 10.0,
                                            # skin edges onto the stock surface: flush round the lamps, no see-through
                                            "snap": 2.5})]
                + [{"part": p_, "prefix": pk, "zones": zdrop} for p_ in stock("Fender") if p_ != "BODY"]
                # stock fender where the MW shell leaves the zone open (Viper: black ring round the headlamps, open vents)
                + [{"part": p_, "prefix": pk, "zones": zkeep, "fill_gaps": {"far": 10.0, "edge": 1.0}}
                   for p_ in stock("Fender") if p_ != "BODY"], lab + " Widebody")
        add("FrontBumper", kit, [fb] + fill("FrontBumper"), lab + " Front Bumper")
        add("RearBumper", kit, [rb_] + fill("RearBumper") + (mw_tips(kit) or exhaust), lab + " Rear Bumper")
        if n:
            add("SideSkirt", kit, [sk] + [{"part": p, "prefix": pk, "fill_gaps": {"far": 8.0, "edge": 1.0}} for p in stock("SideSkirt")],
                lab + " Side Skirts")
    hoods = sorted({m.group(1) for f in files for m in [re.match(r"%s_((?:KIT00|STYLE\d\d))_HOOD_A\.dae$" % mw, f)] if m})
    for h in hoods:
        hx = {"xform": XF["Bonnet"]} if carbon else {}
        parts = [dict(part(h + "_HOOD", keep_nearest=kn("Bonnet"), refine_drop=4), **hx)] + [dict(part(m.group(0)[len(mw) + 1:-6]), **hx) for f in sorted(files)
                                       for m in [re.match(r"%s_%s_ATTACHMENT\d_A\.dae$" % (mw, h), f)] if m]
        add("Bonnet", h, parts, "Stock Hood" if h == "KIT00" else "Hood %d" % int(h[5:]))
    sock = next((x for x in spec["sockets"]["Body"] if x["name"] == "RearWing"), {"loc": [0, 0, 0]})
    wxf = {"s": xf["s"], "t": [xf["t"][k] - sock["loc"][k] for k in range(3)]}
    wings = sorted({m.group(1) for f in files
                    for m in [re.match(r"%s_((?:KIT00|STYLE\d\d|ALT\d\d|NEW_STYLE\d\d)_SPOILER(?:_CF)?)_A\.dae$" % mw, f)] if m})
    for w in wings:
        m = re.match(r"(KIT00|STYLE|ALT|NEW_STYLE)(\d*)_SPOILER(_CF)?", w)
        lab = ("Stock Wing" if m.group(1) == "KIT00" else "%sWing %d" % ({"ALT": "Alt ", "NEW_STYLE": "New "}.get(m.group(1), ""),
                                                                          int(m.group(2)) + (1 if m.group(1) == "ALT" else 0)))
        add("RearWing", w, [dict(part(w), xform=wxf)], lab + (" (Carbon)" if m.group(3) else ""))
    spec["aero_parts"] += rows

    # materials of every MW piece
    used = {}
    for row in rows:
        for p in spec["meshes"][row["mesh"]]["parts"]:
            if "geo" not in p or p.get("prefix") != mw:   # ProStreet pieces / Carbon exhaust tips (own slots)
                continue
            for tex, tris in P.load_dae(mfile(p["part"])):
                used[tex] = used.get(tex, 0) + len(tris)
    ts = spec["texture_slots"]
    tsrc = spec.setdefault("texture_sources", {})
    tdirs = spec.setdefault("texture_dirs", {})
    masked = spec.setdefault("masked_texture_slots", [])
    tag = "MW" + re.sub(r"[^A-Z0-9]", "", mw)
    # hash -> (name, dir): the MW car's own textures, then MW GLOBALB (shared carbon / grilles / radiators)
    lib = {}
    for d in (GLOBAL_TEX, mtex):
        if os.path.isdir(d):
            for f in os.listdir(d):
                m = re.match(r"(0x[0-9A-F]{8})_(.+)\.dds$", f, re.I)
                if m:
                    lib[m.group(1).upper().replace("0X", "0x")] = (m.group(2).upper(), d, f)
    new = {}
    for h, cnt in sorted(used.items(), key=lambda x: -x[1]):
        if h in ts:
            continue
        name, d, f = lib.get(h, (h.upper(), None, None))      # MW Viper: materials carry names, not hashes
        if not d:
            cands = [v for v in lib.values() if v[0].endswith("_" + name) or v[0] == name]
            if not cands and "CARBON" in name:
                cands = [v for v in lib.values() if v[0] == "CARBONFIBRE"]
            hit = next((v for v in cands if v[1] == mtex), cands[0] if cands else None)   # the car's own first
            if hit:
                d, f = hit[1], hit[2]
        slot = None
        if h in SHARED and SHARED[h] != "Bottom":
            slot = SHARED[h]
        elif h == r.get("paint_guess") or re.search(r"(^|_)SKIN\d$|^BODY(_TOP|_LEFT|_RIGHT|_REAR|_FRONT)?$|DOORLINE", name):
            slot = "Paint"
        elif re.search(r"CHROME|ALUMIN|METAL", name):
            slot = "Trim"
        elif re.search(r"CARBOTTOM|PLASTIC|RUBBER|WINDOW_MASK|LICENSE|^BOTTOM$|PLAINNOTHING|SOLIDGREY|_N$|DAMAG", name):
            slot = "Bottom"
        elif d and re.search(r"CARBON|GRILL|INTERCOOLER|RADIATOR|BADGING|NEON|VENT|MESH|SKIN", name):
            key = re.sub(r"[^A-Za-z0-9]", "", name)[:24]
            slot = "Tex_%s_%s" % ("MWG" if d == GLOBAL_TEX else tag, key)
            tsrc[slot] = f.split("_", 1)[0]
            tdirs[slot] = d
            try:
                from PIL import Image
                if Image.open(os.path.join(d, f)).convert("RGBA").getextrema()[3][0] < 128 and slot not in masked:
                    masked.append(slot)                        # see-through grilles
            except Exception:
                pass
        if not slot:
            slot = SHARED.get(h, "Bottom")
        ts[h] = slot
        new[h] = (name, slot, cnt)
    spec.setdefault("mw_parts", {})[mw] = {"xform": xf, "front_cut": round(F, 1), "rear_cut": round(R, 1),
                                           "residual_cm": [round(med, 2), round(p90, 2)]}
    json.dump(spec, open(spec_path, "w"), indent=1)
    print("  %d MW parts (%d kits, %d hoods, %d wings); new material slots: %s" % (
        len(rows), len(kits), len(hoods), len(wings), {h: v for h, v in new.items()}))


if __name__ == "__main__":
    main()
