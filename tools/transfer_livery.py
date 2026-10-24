"""Bake a Most Wanted (Rework IV) vinyl onto a ProStreet port's paint layout (UV0), for boss / preset liveries.

The MW body (KIT00 BODY + HOOD) is placed on the ProStreet body with the fit add_mw_parts stored in spec["mw_parts"];
every ProStreet paint texel (stock body, doors, trunk, KIT00 bumpers / skirts / fenders / hood) is rasterised to a
3D point, matched to the nearest MW paint triangle facing the same way, and the MW vinyl is sampled at that point's MW
UV0. The result is opaque on all paint texels: preset body colour, MW vinyl (colour layer, coverage from its _MASK)
over it. Texels with no MW surface nearby keep the body colour.
usage: transfer_livery.py <cars/<ps spec>.json> <MW CAR> <vinyl name e.g. SUPRA_13VICTORVASQUEZ> <body r,g,b 0-255>
                          <out.png> [size]"""
import json, os, re, sys
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ps_to_mt as P

MW_SCALE = 100.0


def tris_of(path, scale, keep):
    """-> (pos (n,3,3) MT cm, uv (n,3,2)) of the triangles whose material passes keep()"""
    pos, uv = [], []
    if not os.path.exists(path):
        return pos, uv
    for tex, tris in P.load_dae(path):
        if not keep(tex):
            continue
        for t in tris:
            pos.append([[c[0][0] * scale, -c[0][1] * scale, c[0][2] * scale] for c in t])
            uv.append([[c[2][0], 1.0 - c[2][1]] for c in t])   # image space: V down, as the vinyl DDS are stored
    return pos, uv


def main():
    spec_path, mw, vinyl, rgb, out = sys.argv[1:6]
    size = int(sys.argv[6]) if len(sys.argv) > 6 else 2048
    body = np.array([float(x) for x in rgb.split(",")]) / 255.0
    spec = json.load(open(spec_path))
    db = json.load(open(os.path.join(ROOT, "db", "cars.json")))
    r = db["mw:" + mw]
    mgeo = os.path.expanduser(r["geometry_dir"])
    vdir = os.path.join(os.path.dirname(os.path.expanduser(r["texture_dir"]).rstrip("/\\")), "..", "vin", "textures")
    vdir = os.path.normpath(vdir)
    xf = spec["mw_parts"][mw]["xform"]
    s, t = np.array(xf["s"]), np.array(xf["t"])

    # MW paint: the paint hash / body material names (as add_mw_parts)
    mw_paint = lambda tex: tex == r.get("paint_guess") or bool(
        re.search(r"(^|_)SKIN\d$|^BODY(_TOP|_LEFT|_RIGHT|_REAR|_FRONT)?$|DOORLINE", tex))
    mp, mu = [], []
    for part in ("KIT00_BODY", "KIT00_HOOD"):
        a, b = tris_of(os.path.join(mgeo, "%s_%s_A.dae" % (mw, part)), MW_SCALE, mw_paint)
        mp += a; mu += b
    mp = np.array(mp) * s + t
    mu = np.array(mu)
    print("MW paint triangles: %d" % len(mp))

    # ProStreet paint triangles
    slots = spec["texture_slots"]
    # the ProStreet livery layout lives on the shared car-paint material; other Paint-slot materials (e.g. 0xBEBC83C2
    # hood / trunk panels) have their own stretched UVs
    ps_paint = lambda tex: tex == spec.get("vinyl_paint_hash", "0x65FF171E")
    pgeo = os.path.expanduser(spec["geometry_dir"])
    pk = spec["prefix"]
    ps_scale = spec.get("source_scale", 1000.0)
    names = set()
    for k, m in spec["meshes"].items():
        if k == "Body" or (k.startswith("Aero_") and k.endswith("_KIT00")):
            for p in m["parts"]:
                if isinstance(p, str):
                    names.add(p)
                elif not p.get("offset") and p.get("prefix", pk) == pk and p.get("slot", "Paint") == "Paint":
                    names.add(p["part"])
    # visible painted panels only (BASE / lamps / exhaust paint triangles have stretched or overlapping UVs)
    names = {n for n in names if re.match(r"(BODY|DOOR_|TRUNK|HOOD|BUMPER_|SKIRT_|FENDER_|SIDEMIRROR_)", n)}
    pp, pu = [], []
    for n in sorted(names):
        a, b = tris_of(os.path.join(pgeo, "%s_%s_A.dae" % (pk, n)), ps_scale, ps_paint)
        pp += a; pu += b
    pp, pu = np.array(pp), np.array(pu)
    print("ProStreet paint triangles: %d (%s)" % (len(pp), ", ".join(sorted(names))))

    # dense MW samples (tri index per sample) for the nearest-triangle search
    e1, e2 = mp[:, 1] - mp[:, 0], mp[:, 2] - mp[:, 0]
    mn = np.cross(e1, e2)
    area = np.linalg.norm(mn, axis=1) / 2
    mn /= np.maximum(np.linalg.norm(mn, axis=1, keepdims=True), 1e-9)
    step = 0.6
    pts, owner = [], []
    rng = np.random.default_rng(1)
    for i in range(len(mp)):
        k = max(3, int(area[i] / (step * step)))
        q = rng.random((k, 2)); f = q.sum(1) > 1; q[f] = 1 - q[f]
        pts.append(mp[i, 0] + q[:, :1] * e1[i] + q[:, 1:] * e2[i]); owner.append(np.full(k, i))
    pts, owner = np.vstack(pts), np.concatenate(owner)
    tree = cKDTree(pts)

    # rasterise the ProStreet triangles in UV space
    W = H = size
    P3, N3, PX = [], [], []
    pe1, pe2 = pp[:, 1] - pp[:, 0], pp[:, 2] - pp[:, 0]
    pn = np.cross(pe1, pe2); pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    for i in range(len(pp)):
        uv = pu[i] - np.floor(pu[i].min(0))          # tiles -> [0,1)
        xy = uv * [W, H]
        x0, y0 = np.floor(xy.min(0)).astype(int); x1, y1 = np.ceil(xy.max(0)).astype(int)
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        g = np.stack([gx.ravel(), gy.ravel()], 1)
        a, b, c = xy
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (g[:, 0] - c[0]) + (c[0] - b[0]) * (g[:, 1] - c[1])) / d
        l2 = ((c[1] - a[1]) * (g[:, 0] - c[0]) + (a[0] - c[0]) * (g[:, 1] - c[1])) / d
        l3 = 1 - l1 - l2
        tol = 1.0 / max(1.0, abs(d)) ** 0.5           # ~1 texel margin so edges are covered
        m = (l1 >= -tol) & (l2 >= -tol) & (l3 >= -tol)
        if not m.any():
            continue
        L = np.stack([l1[m], l2[m], l3[m]], 1)
        P3.append(L @ pp[i]); N3.append(np.repeat(pn[i][None], m.sum(), 0)); PX.append(g[m].astype(int))
    P3, N3, PX = np.vstack(P3), np.vstack(N3), np.vstack(PX)
    PX[:, 0] = np.clip(PX[:, 0], 0, W - 1); PX[:, 1] = np.clip(PX[:, 1], 0, H - 1)
    print("paint texels: %d" % len(P3))

    # nearest MW triangle facing the same way (normals may be flipped between games: use |dot|)
    dist, idx = tree.query(P3, k=8, distance_upper_bound=4.0)
    ok = np.isfinite(dist)
    tri = np.where(ok, owner[np.minimum(idx, len(owner) - 1)], -1)
    face = np.where(ok, np.abs(np.einsum("nkj,nj->nk", mn[np.maximum(tri, 0)], N3)), 0)
    good = ok & (face > 0.5)
    first = np.where(good.any(1), good.argmax(1), -1)
    hit = first >= 0
    T = tri[np.arange(len(tri)), np.maximum(first, 0)][hit]
    Q = P3[hit]
    # barycentric of the point projected on that MW triangle -> MW UV0
    A, E1, E2 = mp[T, 0], e1[T], e2[T]
    v = Q - A
    d00, d01, d11 = (E1 * E1).sum(1), (E1 * E2).sum(1), (E2 * E2).sum(1)
    d20, d21 = (v * E1).sum(1), (v * E2).sum(1)
    den = np.maximum(d00 * d11 - d01 * d01, 1e-12)
    bv, bw = (d11 * d20 - d01 * d21) / den, (d00 * d21 - d01 * d20) / den
    bv, bw = np.clip(bv, 0, 1), np.clip(bw, 0, 1)
    sm = bv + bw > 1; bv[sm], bw[sm] = bv[sm] / (bv[sm] + bw[sm]), bw[sm] / (bv[sm] + bw[sm])
    UV = mu[T, 0] * (1 - bv - bw)[:, None] + mu[T, 1] * bv[:, None] + mu[T, 2] * bw[:, None]
    UV -= np.floor(UV)
    print("texels on the MW body: %.1f%%" % (100.0 * hit.mean()))

    def load(name):
        for f in os.listdir(vdir):
            if re.search(r"_%s\.dds$" % re.escape(name), f):
                return np.asarray(Image.open(os.path.join(vdir, f)).convert("RGBA")).astype(np.float32) / 255.0
        return None
    col = load(vinyl)
    mask = None
    for mname in (vinyl + "_MASK", vinyl + "_M", vinyl + "_MA", vinyl + "_MAS"):
        mask = load(mname[:23] if len(mname) > 23 else mname)
        if mask is not None:
            break
    if col is None:
        sys.exit("vinyl %s not found in %s" % (vinyl, vdir))

    def sample(img, uv):
        h, w = img.shape[:2]
        x, y = uv[:, 0] * w - 0.5, uv[:, 1] * h - 0.5
        x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
        fx, fy = (x - x0)[:, None], (y - y0)[:, None]
        g = lambda xx, yy: img[np.mod(yy, h), np.mod(xx, w)]
        return (g(x0, y0) * (1 - fx) * (1 - fy) + g(x0 + 1, y0) * fx * (1 - fy) + g(x0, y0 + 1) * (1 - fx) * fy
                + g(x0 + 1, y0 + 1) * fx * fy)
    c = sample(col, UV)
    cov = np.clip(c[:, 3] * 2.0, 0, 1)                 # MW alpha: 0x80 = opaque
    if mask is not None:
        mk = sample(mask, UV)
        cov = np.clip(mk[:, :3].mean(1) * mk[:, 3], 0, 1)
    rgb_hit = c[:, :3] * cov[:, None] + body[None] * (1 - cov[:, None])

    img = np.zeros((H, W, 4), np.float32)
    img[PX[:, 1], PX[:, 0], :3] = body
    img[PX[hit, 1], PX[hit, 0], :3] = rgb_hit
    img[PX[:, 1], PX[:, 0], 3] = 1.0
    # bleed 4 texels past the islands so filtering / mips don't pull in the empty background
    from scipy.ndimage import distance_transform_edt
    filled = img[..., 3] > 0
    _, (iy, ix) = distance_transform_edt(~filled, return_indices=True)
    near = (distance_transform_edt(~filled) <= 4) & ~filled
    img[near, :3] = img[iy[near], ix[near], :3]
    img[near, 3] = 1.0
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(out)
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
