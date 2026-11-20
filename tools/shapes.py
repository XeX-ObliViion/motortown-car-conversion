"""Simple primitives added to a car's meshes, and painted texture details: what a low-poly source cabin lacks
(MW Diablo SV: the real car's round leather steering wheel with spokes and a badged hub, the chrome gated shifter,
round dash vents, red seat piping, the climate-control stack instead of MW's aftermarket radio).

spec["add_shapes"] = [{mesh, type, slot, uv | uv_box, ...}], positions in the mesh's frame (car space; the turning
SteeringWheel's own hub frame, spin axis X). Every shape is one material slot; uv is a single texture point (a swatch)
or uv_box [u0, v0, u1, v1] (image coords) maps a disc/cap face onto a texture rectangle (a badge).
"snap": [axis, sign, offset] moves the shape's anchor along that axis to the first Body surface (ray cast), then by
offset, e.g. a vent onto the dash face.
spec["texture_paint"][slot] = [{op, box (image coords 0..1), ...}], painted after the upscale, before gauge faces."""
import json, math, os, random

V = lambda *a: list(a)
add = lambda a, b: [a[i] + b[i] for i in range(3)]
sub = lambda a, b: [a[i] - b[i] for i in range(3)]
mul = lambda a, s: [x * s for x in a]
dot = lambda a, b: sum(a[i] * b[i] for i in range(3))
cross = lambda a, b: [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def norm(a):
    l = math.sqrt(dot(a, a)) or 1.0
    return [x / l for x in a]


def basis(n):
    """two unit vectors perpendicular to n (u tends toward +y or +z so discs/tubes are oriented predictably)"""
    n = norm(n)
    ref = [0, 0, 1] if abs(n[2]) < 0.9 else [0, 1, 0]
    u = norm(cross(ref, n)); return u, cross(n, u)


class Out:
    def __init__(self): self.tris = []   # (p0, p1, p2, n0, n1, n2, uv0, uv1, uv2)

    def tri(self, p, n, uv):
        # winding: cross(b - a, c - a) along the normal (same as the exported source meshes)
        fn = cross(sub(p[1], p[0]), sub(p[2], p[0]))
        if dot(fn, add(add(n[0], n[1]), n[2])) < 0:
            p, n, uv = [p[0], p[2], p[1]], [n[0], n[2], n[1]], [uv[0], uv[2], uv[1]]
        self.tris.append((p, n, uv))

    def quad(self, a, b, c, d, na, nb, nc, nd, uva, uvb, uvc, uvd):
        self.tri([a, b, c], [na, nb, nc], [uva, uvb, uvc]); self.tri([a, c, d], [na, nc, nd], [uva, uvc, uvd])


def tube(o, pts, r, seg=10, closed=False, uv=(0, 0), up=None):
    """a tube along a polyline; r = radius or [r_a, r_b] for an elliptical section (r_a along `up`)"""
    ra, rb = (r, r) if not isinstance(r, (list, tuple)) else r
    n = len(pts); rings = []
    for i in range(n):
        if closed: d = sub(pts[(i + 1) % n], pts[i - 1])
        else: d = sub(pts[min(i + 1, n - 1)], pts[max(i - 1, 0)])
        d = norm(d)
        if up: a = norm(sub(up, mul(d, dot(up, d)))); b = cross(d, a)
        else: a, b = basis(d)
        ring = []
        for k in range(seg):
            t = 2 * math.pi * k / seg
            off = add(mul(a, ra * math.cos(t)), mul(b, rb * math.sin(t)))
            nrm = norm(add(mul(a, math.cos(t) / ra), mul(b, math.sin(t) / rb)))
            ring.append((add(pts[i], off), nrm))
        rings.append(ring)
    m = n if closed else n - 1
    for i in range(m):
        A, B = rings[i], rings[(i + 1) % n]
        for k in range(seg):
            k2 = (k + 1) % seg
            o.quad(A[k][0], B[k][0], B[k2][0], A[k2][0], A[k][1], B[k][1], B[k2][1], A[k2][1], uv, uv, uv, uv)
    if not closed:   # end caps
        for ring, c, sgn in ((rings[0], pts[0], -1), (rings[-1], pts[-1], 1)):
            d = norm(sub(pts[-1], pts[-2]) if sgn > 0 else sub(pts[0], pts[1]))
            for k in range(seg):
                o.tri([c, ring[k][0], ring[(k + 1) % seg][0]], [d, d, d], [uv, uv, uv])


def disc(o, c, n, r, seg=24, uv=(0, 0), uv_box=None, flip_u=False):
    """a flat disc facing n; r = radius or [r_u, r_v] (ellipse); uv_box maps it onto an image rectangle"""
    ru, rv = (r, r) if not isinstance(r, (list, tuple)) else r
    n = norm(n); u, v = basis(n)

    def tuv(cu, cv):
        if not uv_box: return uv
        x0, y0, x1, y1 = uv_box
        fu = (cu + 1) / 2; fu = 1 - fu if flip_u else fu
        return (x0 + (x1 - x0) * fu, 1 - (y0 + (y1 - y0) * (1 - (cv + 1) / 2)))
    for k in range(seg):
        t0, t1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        p0 = add(c, add(mul(u, ru * math.cos(t0)), mul(v, rv * math.sin(t0))))
        p1 = add(c, add(mul(u, ru * math.cos(t1)), mul(v, rv * math.sin(t1))))
        o.tri([c, p0, p1], [n, n, n], [tuv(0, 0), tuv(math.cos(t0), math.sin(t0)), tuv(math.cos(t1), math.sin(t1))])


def cylinder(o, c0, c1, r, seg=24, uv=(0, 0), cap0_uv_box=None, flip_u=False):
    """a closed cylinder; cap0 (at c0) may carry a texture (the hub badge)"""
    tube(o, [c0, c1], r, seg, uv=uv)
    o.tris = o.tris[:-2 * seg]   # replace tube's flat caps with discs
    d = norm(sub(c0, c1))
    disc(o, c0, d, r, seg, uv, cap0_uv_box, flip_u)
    disc(o, c1, mul(d, -1), r, seg, uv)


def ellipsoid(o, c, r, seg=14, uv=(0, 0)):
    rings = []
    for i in range(seg // 2 + 1):
        ph = math.pi * i / (seg // 2) - math.pi / 2
        ring = []
        for k in range(seg):
            t = 2 * math.pi * k / seg
            d = [math.cos(ph) * math.cos(t), math.cos(ph) * math.sin(t), math.sin(ph)]
            ring.append((add(c, [d[j] * r[j] for j in range(3)]), norm([d[j] / r[j] for j in range(3)])))
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(seg):
            k2 = (k + 1) % seg
            o.quad(A[k][0], B[k][0], B[k2][0], A[k2][0], A[k][1], B[k][1], B[k2][1], A[k2][1], uv, uv, uv, uv)


def box(o, c, size, uv=(0, 0), top_uv_box=None, yaw=0.0):
    """an axis-aligned box (optionally turned by yaw about z); top_uv_box textures the +z face (a shift gate)"""
    hx, hy, hz = [s / 2 for s in size]
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    R = lambda p: [p[0] * cy - p[1] * sy, p[0] * sy + p[1] * cy, p[2]]
    P = lambda x, y, z: add(c, R([x, y, z]))
    faces = [((0, 0, 1), [(-1, -1), (1, -1), (1, 1), (-1, 1)]), ((0, 0, -1), None), ((1, 0, 0), None),
             ((-1, 0, 0), None), ((0, 1, 0), None), ((0, -1, 0), None)]
    for n, _ in faces:
        nn = R(list(n)); a, b = basis(nn)
        # the 4 corners of this face
        corners = []
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            if n[2]: q = [su * hx, sv * hy, n[2] * hz]
            elif n[0]: q = [n[0] * hx, su * hy, sv * hz]
            else: q = [su * hx, n[1] * hy, sv * hz]
            corners.append(q)
        uvs = [uv] * 4
        if n == (0, 0, 1) and top_uv_box:
            x0, y0, x1, y1 = top_uv_box   # +x (forward) = image top, +y = image right
            uvs = [(x0 + (x1 - x0) * (q[1] / hy + 1) / 2, 1 - (y0 + (y1 - y0) * (1 - (q[0] / hx + 1) / 2))) for q in corners]
        pts = [P(*q) for q in corners]
        o.quad(*pts, nn, nn, nn, nn, *uvs)


def ray_hit(tris, o, d):
    """nearest t > 0 where o + t*d meets a triangle (Moller-Trumbore)"""
    best = None
    for a, b, c in tris:
        e1, e2 = sub(b, a), sub(c, a); p = cross(d, e2); det = dot(e1, p)
        if abs(det) < 1e-9: continue
        inv = 1 / det; s = sub(o, a); u = dot(s, p) * inv
        if u < 0 or u > 1: continue
        q = cross(s, e1); v = dot(d, q) * inv
        if v < 0 or u + v > 1: continue
        t = dot(e2, q) * inv
        if t > 0.01 and (best is None or t < best[0]): best = (t, (a, b, c))
    return best


def feature_edges(tris, lo, hi, angle, min_len):
    """sharp edges (dihedral > angle) of the triangles inside a box: the outline of a seat's bolsters, for piping"""
    key = lambda p: tuple(round(x, 2) for x in p)
    edges = {}
    for a, b, c in tris:
        if not all(lo[k] <= q[k] <= hi[k] for q in (a, b, c) for k in range(3)): continue
        n = norm(cross(sub(b, a), sub(c, a)))
        for p, q in ((a, b), (b, c), (c, a)):
            edges.setdefault(tuple(sorted((key(p), key(q)))), []).append(n)
    out, seen = [], set()
    cosmax = math.cos(math.radians(angle))
    for (p, q), ns in edges.items():
        if math.dist(p, q) < min_len: continue
        k = tuple(sorted((tuple(round(x * 2) for x in p), tuple(round(x * 2) for x in q))))
        if k in seen: continue   # the MW cabin repeats its shells several times: one tube per edge
        if len(ns) == 2 and dot(ns[0], ns[1]) < cosmax:
            seen.add(k); out.append((list(p), list(q)))
    return out


def cabin_remap(m, cfg):
    """move a flat-coloured slot's triangles inside a box onto a texture region (box-projected UVs), so cabin
    panels that had one plain colour pick up a material texture (alcantara grain)"""
    lo, hi = cfg["box"][:3], cfg["box"][3:]; u0, v0, u1, v1 = cfg["uv_box"]; size = cfg.get("size_cm", 180.0)
    src = next((s for s in m["slots"] if s["slot"] == cfg["from"]), None)
    dst = next((s for s in m["slots"] if s["slot"] == cfg["to"]), None)
    if src is None or dst is None: raise SystemExit("cabin_remap: missing slot %s" % cfg)
    keep = {"positions": [], "normals": [], "uvs": []}; moved = 0
    P, N = src["positions"], src["normals"]
    for i in range(0, len(P), 3):
        c = [sum(P[i + j][k] for j in range(3)) / 3 for k in range(3)]
        if not all(lo[k] <= c[k] <= hi[k] for k in range(3)):
            for k in ("positions", "normals", "uvs"): keep[k] += src[k][i:i + 3]
            continue
        n = norm(cross(sub(P[i + 1], P[i]), sub(P[i + 2], P[i])))
        ax = max(range(3), key=lambda k: abs(n[k])); a, b = [k for k in range(3) if k != ax]
        uv = [[u0 + (u1 - u0) * min(1, max(0, (q[a] - lo[a]) / size)),
               1 - (v0 + (v1 - v0) * min(1, max(0, (q[b] - lo[b]) / size)))] for q in P[i:i + 3]]
        dst["positions"] += P[i:i + 3]; dst["normals"] += N[i:i + 3]; dst["uvs"] += uv; moved += 1
    src.update(keep)
    print("cabin_remap: %d %s tris -> %s" % (moved, cfg["from"], cfg["to"]))


def tessellate(m, cfg):
    """round off a low-poly cabin: Phong tessellation of the triangles inside a box (slots listed). Each triangle
    becomes level^2 smaller ones bulged toward smoothed vertex normals (faces within `angle` degrees blend); edges
    that are creases, open, or shared with untouched triangles stay straight so nothing cracks."""
    lo, hi = cfg["box"][:3], cfg["box"][3:]; L = cfg.get("level", 3); alpha = cfg.get("alpha", 0.6)
    cosa = math.cos(math.radians(cfg.get("angle", 45)))
    key = lambda p: tuple(round(x, 2) for x in p)
    tris = []   # (slot, i, selected)
    for s in m["slots"]:
        if s["slot"] == "Glass": continue
        P = s["positions"]
        for i in range(0, len(P), 3):
            c = [sum(P[i + j][k] for j in range(3)) / 3 for k in range(3)]
            sel = s["slot"] in cfg["slots"] and all(lo[k] <= c[k] <= hi[k] for k in range(3))
            tris.append((s, i, sel))
    fn = {}; groups = {}; edges = {}
    for t, (s, i, sel) in enumerate(tris):
        P = s["positions"]
        n = norm(cross(sub(P[i + 1], P[i]), sub(P[i + 2], P[i])))
        if dot(n, add(add(s["normals"][i], s["normals"][i + 1]), s["normals"][i + 2])) < 0: n = mul(n, -1)
        fn[t] = n
        ks = [key(P[i + j]) for j in range(3)]
        for j in range(3):
            if sel: groups.setdefault(ks[j], []).append(t)
        for j in range(3):
            edges.setdefault(("t",) + tuple(sorted((ks[j], ks[(j + 1) % 3]))), []).append((t, sel))
    def vnorm(t, k):
        acc = [0.0, 0.0, 0.0]
        for u in groups.get(k, [t]):
            if dot(fn[t], fn[u]) >= cosa: acc = add(acc, fn[u])
        return norm(acc)
    out = {}
    for t, (s, i, sel) in enumerate(tris):
        if not sel: continue
        P = s["positions"]; ks = [key(P[i + j]) for j in range(3)]
        vn = [vnorm(t, ks[j]) for j in range(3)]
        soft = []
        for j in range(3):
            users = edges[("t",) + tuple(sorted((ks[j], ks[(j + 1) % 3])))]
            ok = all(se for _, se in users) and len({tuple(sorted(key(tris[u][0]["positions"][tris[u][1] + q]) for q in range(3))) for u, _ in users}) == 2
            if ok:
                for u, _ in users:
                    if u == t: continue
                    ok = ok and all(dot(vnorm(u, ks[q]), vn[q]) > 0.995 for q in (j, (j + 1) % 3))
            soft.append(ok)
        UV = s["uvs"][i:i + 3]
        def point(b):
            p = [sum(b[j] * P[i + j][k] for j in range(3)) for k in range(3)]
            zero = [j for j in range(3) if b[j] < 1e-9]
            # a point on a hard edge (the one opposite the vertex whose weight is 0) stays on the straight edge
            if len(zero) == 0 or (len(zero) == 1 and soft[(zero[0] + 1) % 3]):
                proj = [0.0, 0.0, 0.0]
                for j in range(3):
                    d = dot(sub(p, P[i + j]), vn[j]); proj = add(proj, mul(sub(p, mul(vn[j], d)), b[j]))
                p = add(mul(p, 1 - alpha), mul(proj, alpha))
            n = norm([sum(b[j] * vn[j][k] for j in range(3)) for k in range(3)])
            uv = [sum(b[j] * UV[j][k] for j in range(3)) for k in range(2)]
            return p, n, uv
        grid = {(a, c): point(((L - a - c) / L, a / L, c / L)) for a in range(L + 1) for c in range(L + 1 - a)}
        o = out.setdefault(id(s), (s, {"positions": [], "normals": [], "uvs": []}))[1]
        def emit(*ids):
            for q in ids:
                pp, nn, uu = grid[q]; o["positions"].append(pp); o["normals"].append(nn); o["uvs"].append(uu)
        for a in range(L):
            for c in range(L - a):
                emit((a, c), (a + 1, c), (a, c + 1))
                if a + c < L - 1: emit((a + 1, c), (a + 1, c + 1), (a, c + 1))
    n_in = 0
    for s, add_ in out.values():
        keep = {"positions": [], "normals": [], "uvs": []}
        for (s2, i, sel) in tris:
            if s2 is s and not sel:
                for k in keep: keep[k] += s[k][i:i + 3]
            elif s2 is s: n_in += 1
        for k in keep: s[k] = keep[k] + add_[k]
    print("tessellate: %d tris x%d" % (n_in, L * L))


def add_shapes(spec):
    for cfg in spec.get("cabin_remap", []) + [dict(c, _t=1) for c in spec.get("tessellate", [])]:
        path = os.path.join(spec["out_dir"], cfg.get("mesh", "Body") + ".json"); m = json.load(open(path))
        (tessellate if cfg.get("_t") else cabin_remap)(m, cfg)
        json.dump(m, open(path, "w"))

    shapes = spec.get("add_shapes")
    if not shapes: return
    body_tris = None
    meshes = {}
    for sh in shapes:
        mname = sh["mesh"]
        if mname not in meshes:
            meshes[mname] = json.load(open(os.path.join(spec["out_dir"], mname + ".json")))
        if sh.get("snap") or sh["type"] == "piping":
            if body_tris is None:
                B = meshes.get("Body") or json.load(open(os.path.join(spec["out_dir"], "Body.json")))
                body_tris = [tuple(s["positions"][i:i + 3]) for s in B["slots"] for i in range(0, len(s["positions"]), 3)
                             if s["slot"] != "Glass"]
        o = Out(); uv = tuple(sh.get("uv", (0, 0)))
        uv = (uv[0], 1 - uv[1])   # swatch given in image coords
        c = sh.get("center")
        if sh.get("snap"):
            ax, sg, off = sh["snap"]; d = [0, 0, 0]; d[ax] = sg
            hit = ray_hit(body_tris, c, d)
            if hit is None: raise SystemExit("add_shapes: snap found no surface for %s" % sh)
            t, (a, b, c3) = hit
            c = list(c); c[ax] += sg * (t + off)
            if sh.get("align"):   # face the shape along the surface it sits on (a vent on a sloping dash)
                n = norm(cross(sub(b, a), sub(c3, a)))
                sh = dict(sh, normal=mul(n, -1) if dot(n, d) > 0 else n)
            print("add_shapes: %s snapped to %s" % (sh.get("note", t), [round(x, 1) for x in c]))
        if sh.get("offset"):
            c = add(c, sh["offset"])
        t = sh["type"]
        if t == "torus":   # ring about axis n
            n = norm(sh["normal"]); u, v = basis(n); R = sh["R"]; seg = sh.get("seg", 40)
            pts = [add(c, add(mul(u, R * math.cos(2 * math.pi * k / seg)), mul(v, R * math.sin(2 * math.pi * k / seg)))) for k in range(seg)]
            tube(o, pts, sh["r"], sh.get("tseg", 10), closed=True, uv=uv, up=n)
        elif t == "tube":
            pts = [add(c, p) for p in sh["points"]] if c else sh["points"]
            tube(o, pts, sh["r"], sh.get("seg", 10), uv=uv, up=sh.get("up"))
        elif t == "spokes":   # bars from a hub radius to a rim radius in the Y-Z plane, at the given angles
            for a in sh["angles"]:
                d = [0, math.cos(math.radians(a)), math.sin(math.radians(a))]
                p0 = add(c, add(mul(d, sh["r0"]), [sh.get("x0", 0), 0, 0]))
                p1 = add(c, add(mul(d, sh["r1"]), [sh.get("x1", 0), 0, 0]))
                tube(o, [p0, p1], sh["section"], sh.get("seg", 8), uv=uv, up=[1, 0, 0])
        elif t == "disc":
            disc(o, c, sh["normal"], sh["r"], sh.get("seg", 24), uv, sh.get("uv_box"), sh.get("flip_u", False))
        elif t == "cylinder":
            c1 = add(c, sh["axis"])
            cylinder(o, c, c1, sh["r"], sh.get("seg", 24), uv, sh.get("cap_uv_box"), sh.get("flip_u", False))
        elif t == "ellipsoid":
            ellipsoid(o, c, sh["r"], sh.get("seg", 14), uv)
        elif t == "box":
            box(o, c, sh["size"], uv, sh.get("top_uv_box"), sh.get("yaw", 0))
        elif t == "piping":   # thin tubes along a box's sharp edges, pushed slightly outward
            for p, q in feature_edges(body_tris, sh["box"][:3], sh["box"][3:], sh.get("angle", 40), sh.get("min_len", 2)):
                if sh.get("exclude") and any(all(e[k] <= x[k] <= e[k + 3] for k in range(3)) for e in sh["exclude"] for x in (p, q)):
                    continue
                tube(o, [p, q], sh["r"], 6, uv=uv)
        elif t == "quad":   # double-sided patch from 4 points (a glass strip filling a gap in the source window)
            a, b, c4, d = sh["points"]; n = norm(cross(sub(b, a), sub(c4, a))); m_ = mul(n, -1)
            o.quad(a, b, c4, d, n, n, n, n, uv, uv, uv, uv); o.quad(a, b, c4, d, m_, m_, m_, m_, uv, uv, uv, uv)
        else:
            raise SystemExit("add_shapes: unknown type %s" % t)
        m = meshes[mname]
        slot = next((s for s in m["slots"] if s["slot"] == sh["slot"]), None)
        if slot is None:
            slot = {"slot": sh["slot"], "positions": [], "normals": [], "uvs": []}; m["slots"].append(slot)
        for p, n, u in o.tris:
            slot["positions"] += p; slot["normals"] += n; slot["uvs"] += [list(x) for x in u]
        print("add_shapes: %s %s -> %s/%s, %d tris" % (t, sh.get("note", ""), mname, sh["slot"], len(o.tris)))
    for mname, m in meshes.items():
        json.dump(m, open(os.path.join(spec["out_dir"], mname + ".json"), "w"))


def texture_paint(im, ops):
    from PIL import ImageDraw
    W, H = im.size
    d = ImageDraw.Draw(im)
    rnd = random.Random(7)
    for op in ops:
        x0, y0, x1, y1 = int(op["box"][0] * W), int(op["box"][1] * H), int(op["box"][2] * W), int(op["box"][3] * H)
        col = tuple(op.get("color", (20, 20, 22)))
        k = op["op"]
        if k == "fill":   # flat colour with a little grain (alcantara / satin plastic)
            d.rectangle([x0, y0, x1, y1], fill=col + (255,))
            g = op.get("noise", 0)
            if g:
                px = im.load()
                for y in range(y0, y1, 2):
                    for x in range(x0, x1, 2):
                        e = rnd.randint(-g, g)
                        px[x, y] = tuple(max(0, min(255, v + e)) for v in col) + (255,)
        elif k == "buttons":   # the climate stack: rows of small rounded keys, a pair of round dials
            d.rectangle([x0, y0, x1, y1], fill=col + (255,))
            rows, cols = op.get("rows", 3), op.get("cols", 5)
            bw, bh = (x1 - x0) / (cols + 1), (y1 - y0) / (rows + 2)
            for r in range(rows):
                for cc in range(cols):
                    bx = x0 + bw * (cc + 0.5) + bw * 0.1; by = y0 + bh * (r + 0.4)
                    d.rounded_rectangle([bx, by, bx + bw * 0.8, by + bh * 0.65], radius=int(bh * 0.15),
                                        fill=(58, 58, 62, 255), outline=(90, 90, 96, 255))
                    d.rectangle([bx + bw * 0.3, by + bh * 0.12, bx + bw * 0.5, by + bh * 0.2], fill=(220, 120, 30, 255))
            for cx in (x0 + (x1 - x0) * 0.25, x0 + (x1 - x0) * 0.75):
                cy = y1 - bh * 0.9; rr = bh * 0.7
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(40, 40, 44, 255), outline=(150, 150, 156, 255), width=max(1, int(rr * 0.15)))
        elif k == "gate":   # an open chrome shift gate: polished plate, black slots (5-speed dog-leg, R left)
            for y in range(y0, y1):
                s = 150 + int(80 * (1 - abs((y - y0) / (y1 - y0) - 0.35)))
                d.line([(x0, y), (x1, y)], fill=(s, s, s + 4, 255))
            w, h = x1 - x0, y1 - y0; sw = max(2, int(w * 0.06))
            xs = [x0 + w * f for f in (0.2, 0.4, 0.6, 0.8)]
            ym = y0 + h * 0.5
            d.rectangle([xs[0], ym - sw / 2, xs[-1], ym + sw / 2], fill=(10, 10, 10, 255))
            for i, x in enumerate(xs):
                d.rectangle([x - sw / 2, y0 + h * 0.15, x + sw / 2, y0 + h * 0.85], fill=(10, 10, 10, 255))
        elif k == "vent":   # round air vent: dark bowl, horizontal slats
            d.ellipse([x0, y0, x1, y1], fill=(10, 10, 11, 255))
            n = op.get("slats", 5); h = (y1 - y0) / (n + 1)
            for i in range(n):
                yy = y0 + h * (i + 1)
                d.rectangle([x0 + (x1 - x0) * 0.08, yy - h * 0.18, x1 - (x1 - x0) * 0.08, yy + h * 0.18], fill=(62, 62, 66, 255))
            d.ellipse([x0 + (x1 - x0) * 0.42, y0 + (y1 - y0) * 0.42, x1 - (x1 - x0) * 0.42, y1 - (y1 - y0) * 0.42], fill=(80, 80, 85, 255))
        elif k == "grille":   # speaker grille: dark mesh of dots
            d.ellipse([x0, y0, x1, y1], fill=(14, 14, 15, 255))
            step = max(3, (x1 - x0) // 14)
            for yy in range(y0 + step, y1, step):
                for xx in range(x0 + step, x1, step):
                    if ((xx - (x0 + x1) / 2) ** 2 + (yy - (y0 + y1) / 2) ** 2) < ((x1 - x0) / 2 - step) ** 2:
                        d.ellipse([xx - step * 0.3, yy - step * 0.3, xx + step * 0.3, yy + step * 0.3], fill=(48, 48, 52, 255))
        elif k == "wood":   # woodgrain veneer (1970s dash panels); grain runs along image x, or y with "vertical"
            base = col if op.get("color") else (92, 52, 28)
            d.rectangle([x0, y0, x1, y1], fill=tuple(base) + (255,))
            vert = op.get("vertical")
            span = (x1 - x0) if vert else (y1 - y0)
            for i in range(int(span * 0.8)):
                p0 = rnd.uniform(0, span); w = rnd.uniform(0.3, 1.6); dk = rnd.uniform(0.55, 1.15)
                c2 = tuple(max(0, min(255, int(v * dk))) for v in base) + (255,)
                wob = rnd.uniform(-0.01, 0.01) * span
                if vert: d.line([(x0 + p0, y0), (x0 + p0 + wob, y1)], fill=c2, width=max(1, int(w)))
                else: d.line([(x0, y0 + p0), (x1, y0 + p0 + wob)], fill=c2, width=max(1, int(w)))
        elif k == "pod":   # dark round gauge pod with a bezel ring (box = its bounding ellipse)
            d.ellipse([x0, y0, x1, y1], fill=col + (255,), outline=tuple(op.get("ring", (150, 150, 155))) + (255,),
                      width=max(2, int((x1 - x0) * 0.03)))
        elif k == "alcantara":   # suede: per-pixel grain plus soft mottled patches where the nap catches light
            import numpy as np
            from PIL import Image
            w, h = x1 - x0, y1 - y0; r = np.random.default_rng(op.get("seed", 3))
            fine = r.normal(0, op.get("grain", 5), (h, w))
            blot = Image.fromarray(r.normal(0, 1, (max(2, h // 24), max(2, w // 24))).astype(np.float32), mode="F")
            fine += np.asarray(blot.resize((w, h), Image.BICUBIC)) * op.get("mottle", 4)
            arr = np.clip(np.array(col, float)[None, None, :] + fine[..., None], 0, 255).astype(np.uint8)
            im.paste(Image.fromarray(arr, "RGB").convert(im.mode), (x0, y0))
        elif k == "swatch":
            d.rectangle([x0, y0, x1, y1], fill=col + (255,))
        else:
            raise SystemExit("texture_paint: unknown op %s" % k)
