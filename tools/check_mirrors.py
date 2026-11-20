"""Mirror check for a built car (run after ps_to_mt): from the cockpit camera, are the live mirror surfaces the ones the
driver sees? usage: check_mirrors.py cars/<car>.json [...]
For each side mirror: the glass placed where the game puts it (component location + rotation, recentred / counter-rotated
meshes included), the share of its sample points hidden behind body/door triangles (stock glass or housing in front),
and the visible area of non-mirror faces in the housing that face the driver like the glass does (stock glass the
live one doesn't cover, e.g. the MW Diablo's MISC-textured glass quad). Room mirror: body triangles around the RoomMirror
component (a source car's own rear-view mirror) and whether the eye->mirror line is blocked.
Exit code 1 if any car FAILS."""
import json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps_to_mt as P

OCCLUDED_MAX = 0.10     # hidden share of the glass
STOCK_GLASS_MAX = 0.15  # visible glass-facing housing area / live glass area
ROOM_BOX = 9.0          # cm around the RoomMirror component


def load(build, name):
    p = os.path.join(build, "meshes", name + ".json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    return {s["slot"]: np.array(s["positions"], float).reshape(-1, 3, 3) for s in d["slots"] if s["positions"]}


def rot(r):
    X, Y, Z = P.rot_axes(r)
    return np.array([X, Y, Z], float)   # rows = component axes in car space


def glass_in_car(spec, build):
    """{side: (tris in car space, component name)} for every live side mirror glass."""
    out = {}
    comps = spec.get("mirror_components")
    if comps:
        # placement exactly as built: the blueprint make_mt_assets wrote (location, rotation, scale, mesh per component)
        bpp = os.path.expanduser("~/mt-work/build/pak_PS_Common/_work/%s_bp.json" % spec["car"])
        # before the car's first make_mt_assets run there is no blueprint yet: the spec alone places the mirrors
        bp = json.load(open(bpp, encoding="utf-8")) if os.path.exists(bpp) else {
            "Imports": [], "Exports": [{"ObjectName": c, "Data": []} for c in comps]}
        def vec(e, name, keys, dflt):
            for p in e.get("Data", []):
                if p["Name"] == name:
                    v = p["Value"][0]["Value"] if isinstance(p["Value"], list) else p["Value"]
                    return [float(v[k]) for k in keys]
            return dflt
        for e in bp["Exports"]:
            comp = e.get("ObjectName")
            if comp not in comps:
                continue
            # the spec wins where make_mt_assets will apply it (so a re-aim can be checked before the next build)
            sm = next((p["Value"] for p in e.get("Data", []) if p["Name"] == "StaticMesh"), None)
            mname = spec.get("mirror_meshes", {}).get(comp) or (
                bp["Imports"][-sm - 1]["ObjectName"] if isinstance(sm, int) and sm < 0 else comps[comp].partition(":")[0])
            m = load(build, mname)
            if m is None:
                continue
            mesh, _, flip = comps[comp].partition(":")
            loc = np.array(vec(e, "RelativeLocation", "XYZ", [0, 0, 0]))
            if mesh in spec.get("recentered", {}):
                loc = np.array(spec["recentered"][mesh], float) * ([1, -1, 1] if flip else [1, 1, 1])
            r_ = spec.get("blueprint", {}).get("component_rotations", {}).get(comp)
            R = rot(r_ if r_ else vec(e, "RelativeRotation", ("Pitch", "Yaw", "Roll"), [0, 0, 0]))
            # no blueprint yet: a ":mirror" component is the base's scale-Y -1 right mirror
            sc = np.array(vec(e, "RelativeScale3D", "XYZ", [1, -1, 1] if flip and not e.get("Data") else [1, 1, 1]))
            out[comp] = ((np.concatenate(list(m.values())) * sc) @ R + loc, comp)
    else:
        for name, md in spec["meshes"].items():
            if name.startswith("SideMirror") and any(p.get("slot") == "Mirror" for p in md.get("parts", []) if isinstance(p, dict)):
                m = load(build, name)
                if m:
                    out[name] = (np.concatenate(list(m.values())), name)
    return out


def occluders(spec, build):
    tris = []
    for name in spec["meshes"]:
        if name.startswith(("Wheel", "SideMirror", "Aero_", "LeftSideMirror", "RightSideMirror")) or name == "SideMirror":
            continue
        m = load(build, name)
        if m:
            tris += [t for s, t in m.items() if s not in ("Glass", "Mirror")]
    return np.concatenate(tris) if tris else np.zeros((0, 3, 3))


def hits(o, d, T, tmax):
    """does the segment o + s*d (0 < s < tmax) hit any triangle of T (Moller-Trumbore, vectorised)."""
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    p = np.cross(d, e2); det = (e1 * p).sum(1)
    ok = np.abs(det) > 1e-9; inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    s = o - T[:, 0]; u = (s * p).sum(1) * inv
    q = np.cross(s, e1); v = (q * d).sum(1) * inv; t = (q * e2).sum(1) * inv
    return bool(np.any(ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0.05) & (t < tmax - 0.3)))


def area(T):
    return 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)


def samples(T, n=60):
    a = area(T); idx = np.random.default_rng(0).choice(len(T), n, p=a / a.sum())
    r = np.random.default_rng(1).random((n, 2)); f = r.sum(1) > 1; r[f] = 1 - r[f]
    return T[idx, 0] + r[:, :1] * (T[idx, 1] - T[idx, 0]) + r[:, 1:] * (T[idx, 2] - T[idx, 0])


def check(path):
    spec = json.load(open(path))
    build = os.path.expanduser(spec.get("out_dir", "~/mt-work/build/%s" % spec["car"]))
    if os.path.basename(build.rstrip("/\\")) == "meshes":
        build = os.path.dirname(build.rstrip("/\\"))
    eye = np.array(spec["blueprint"]["cockpit_camera"], float)
    occ = occluders(spec, build)
    # nearby subset per test keeps the ray casts cheap
    cent = occ.mean(1)
    fails = []
    print("%s (eye %s)" % (spec["car"], eye.tolist()))
    glass = glass_in_car(spec, build)
    base_m = spec.get("mirror_check", {}).get("base_side_mirrors")   # the base car's own mirror meshes (source model has none)
    for comp in base_m or []:
        mc = np.array(spec["blueprint"]["components"][comp], float)
        side = 1.0 if mc[1] > 0 else -1.0
        seen = not hits(eye, (mc - eye) / np.linalg.norm(mc - eye), occ, np.linalg.norm(mc - eye) - 6)
        back = np.array([-1.0, 0.15 * side, 0.0]); back /= np.linalg.norm(back)
        view = not hits(mc + back * 8, back, occ, 300)      # the glass can see down the side of the car
        print("  %-28s base mirror at %s  eye->mirror %s  view back %s  %s" % (comp, mc.tolist(), "clear" if seen else "BLOCKED",
              "clear" if view else "BLOCKED", "ok" if seen and view else "FAIL"))
        if not (seen and view):
            fails.append(comp)
    if base_m:
        glass = {}
    elif len(glass) < 2 or not len(occ):
        print("  side mirror glass found: %d, body triangles: %d  FAIL" % (len(glass), len(occ)))
        fails.append("no glass")
    for side, (G, comp) in sorted(glass.items()):
        gc = G.reshape(-1, 3).mean(0)
        near = occ[np.linalg.norm(np.cross(cent - eye, gc - eye), axis=1) / np.linalg.norm(gc - eye) < 40]
        pts = samples(G)
        hid = sum(hits(eye, (q - eye) / np.linalg.norm(q - eye), near, np.linalg.norm(q - eye)) for q in pts) / len(pts)
        # housing faces that face the driver like the glass does, around the glass (stock glass left in the body)
        gn = np.cross(G[:, 1] - G[:, 0], G[:, 2] - G[:, 0]).sum(0); gn /= np.linalg.norm(gn)
        if np.dot(gn, eye - gc) < 0:
            gn = -gn
        lo, hi = G.reshape(-1, 3).min(0) - 4, G.reshape(-1, 3).max(0) + 4
        bc = occ.mean(1); inb = np.all((bc >= lo) & (bc <= hi), axis=1)
        H = occ[inb]
        hn = np.cross(H[:, 1] - H[:, 0], H[:, 2] - H[:, 0]); hn /= np.linalg.norm(hn, axis=1, keepdims=True) + 1e-12
        facing = H[(hn @ gn > 0.9) & (area(H) > 1.5)]   # housing rim strips are < 1.5 cm2
        # stock glass lies on the live glass (within 3 cm of its plane, centre inside its outline); the housing's
        # sail / mount panels beside it don't count
        from scipy.spatial import Delaunay
        u = np.cross(gn, [0, 0, 1.0]); u /= np.linalg.norm(u); w = np.cross(gn, u)
        gp = G.reshape(-1, 3) - gc
        hull = Delaunay(np.c_[gp @ u, gp @ w])
        fc = facing.mean(1) - gc if len(facing) else np.zeros((0, 3))
        facing = facing[(np.abs(fc @ gn) < 3) & (hull.find_simplex(np.c_[fc @ u, fc @ w]) >= 0)] if len(facing) else facing   # same side as the glass (the housing's back shell faces away)
        near_g = np.concatenate([near, G])   # behind the live glass doesn't count
        vis = sum(a for t, a in zip(facing, area(facing))
                  if not hits(eye, (t.mean(0) - eye) / np.linalg.norm(t.mean(0) - eye), near_g, np.linalg.norm(t.mean(0) - eye)))
        ratio = vis / area(G).sum()
        if os.environ.get("CHECK_DETAIL"):
            print("    glass bbox", G.reshape(-1, 3).min(0).round(1).tolist(), G.reshape(-1, 3).max(0).round(1).tolist())
            for t in facing:
                print("    facing face", t.mean(0).round(1).tolist(), round(float(area(t[None])[0]), 2))
        # spec mirror_check {hidden_max, note}: the car's own parts in the sightline (993 RWB: cage tube + pillar pod)
        ok = hid <= spec.get("mirror_check", {}).get("hidden_max", OCCLUDED_MAX) and ratio <= STOCK_GLASS_MAX
        print("  %-28s glass %5.1f cm2 at %s  hidden %3.0f%%  stock-glass faces %3.0f%%  %s"
              % (side, area(G).sum(), gc.round(1).tolist(), hid * 100, ratio * 100, "ok" if ok else "FAIL"))
        if not ok:
            fails.append(side)
    rm = spec["blueprint"].get("components", {}).get("RoomMirror_GEN_VARIABLE")
    if rm:
        rm = np.array(rm, float)
        bc = occ.mean(1); stock = occ[np.all(np.abs(bc - rm) <= [ROOM_BOX, ROOM_BOX, 5], axis=1)]   # +-5 cm in z: not the headliner
        # a source car's own mirror: faces around the component that face the driver (the headliner faces down)
        sn = np.cross(stock[:, 1] - stock[:, 0], stock[:, 2] - stock[:, 0]); sn /= np.linalg.norm(sn, axis=1, keepdims=True) + 1e-12
        tv = eye - stock.mean(1); tv /= np.linalg.norm(tv, axis=1, keepdims=True)
        stock = stock[(area(stock) > 0.05) & ((sn * tv).sum(1) > 0.6)]
        if os.environ.get("CHECK_DETAIL"):
            for t in stock:
                print("    room-mirror face", t.round(1).tolist())
        near = occ[np.linalg.norm(bc - (eye + rm) / 2, axis=1) < np.linalg.norm(rm - eye)]
        blocked = hits(eye, (rm - eye) / np.linalg.norm(rm - eye), near, np.linalg.norm(rm - eye) - 4)
        # a stalk is fine, a mirror face (~100 cm2) is not; spec mirror_check.room_max for a named mount part
        ok = area(stock).sum() < spec.get("mirror_check", {}).get("room_max", 20) and not blocked
        print("  %-28s at %s  driver-facing body faces within %g cm: %.0f cm2  line of sight %s  %s"
              % ("RoomMirror", rm.tolist(), ROOM_BOX, area(stock).sum(), "BLOCKED" if blocked else "clear", "ok" if ok else "FAIL"))
        if not ok:
            fails.append("RoomMirror")
    return fails


if __name__ == "__main__":
    bad = {p: f for p in sys.argv[1:] for f in [check(p)] if f}
    print("\nFAIL: %s" % bad if bad else "\nall mirrors ok")
    sys.exit(1 if bad else 0)
