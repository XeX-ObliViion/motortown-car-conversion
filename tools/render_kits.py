"""Depth-buffered 3/4 renders of a converted car with a chosen set of meshes, to inspect garage parts (MW kits) for
z-fighting, holes and stray dark pieces before testing in game.
usage: render_kits.py <build_dir> <out.png> <mesh,list | "kit:<CODE>"> [width]
  kit:MWKIT03 -> every non-aero mesh + Aero_{FrontBumper,RearBumper,SideSkirt}_MWKIT03 + the stock bonnet / fender /
  wing; missing kit slots fall back to the stock KIT00 mesh.
Backfaces are culled like the game. Triangles closer than 0.4 cm in depth to a different mesh's surface are tinted
magenta (z-fight risk); dark "Bottom" slot pieces render near-black like in game."""
import json, os, sys
import numpy as np
from PIL import Image

B, out, sel = sys.argv[1], sys.argv[2], sys.argv[3]
WIDTH = int(sys.argv[4]) if len(sys.argv) > 4 else 900
SLOT = {"Paint": (215, 120, 40), "Paint2": (230, 230, 230), "Bottom": (22, 22, 24), "Trim": (170, 170, 175),
        "Glass": (90, 120, 140), "Mirror": (220, 220, 240)}
md = os.path.join(B, "meshes")
names = [f[:-5] for f in os.listdir(md) if f.endswith(".json")]
try:       # only the meshes the current build uses (old builds can leave stale mesh files behind)
    _cur = {m["name"] for m in json.load(open(os.path.join(B, "car.json")))["meshes"]}
    names = [n for n in names if n in _cur]
except Exception:
    pass
if sel.startswith("kit:"):
    code = sel[4:]
    want = [n for n in names if not n.startswith("Aero_") and not n.startswith("Wheel")]
    for slot in ("FrontBumper", "RearBumper", "SideSkirt"):
        n = "Aero_%s_%s" % (slot, code)
        want.append(n if n in names else "Aero_%s_KIT00" % slot)
    hood = os.environ.get("HOOD")          # e.g. HOOD=MWSTYLE05 to view an MW hood with the kit
    if hood and "Aero_Bonnet_%s" % hood in names:
        want.append("Aero_Bonnet_%s" % hood)
    elif "Aero_Bonnet_KIT00" in names:
        want.append("Aero_Bonnet_KIT00")
    if "Aero_Fender_%s" % code in names:
        want.append("Aero_Fender_%s" % code)
    elif "Aero_Fender_KIT00" in names:
        want.append("Aero_Fender_KIT00")
    wings = sorted(n for n in names if n.startswith("Aero_RearWing_") and "MW" not in n)
    want += wings[:1]
else:
    want = sel.split(",")
texs = {}
T, C, M, NS = [], [], [], []   # triangles (n,3,3), colours, mesh index, stored normals
for mi, m in enumerate(want):
    p = os.path.join(md, m + ".json")
    if not os.path.exists(p):
        continue
    for s in json.load(open(p))["slots"]:
        sl = s["slot"]
        tp = os.path.join(B, "textures", sl[4:] + ".png") if sl.startswith("Tex_") else None
        im = None
        if tp and os.path.exists(tp):
            im = texs.setdefault(tp, np.asarray(Image.open(tp).convert("RGBA")))
        P = np.array(s["positions"]).reshape(-1, 3, 3)
        if not len(P):
            continue
        NN = np.array(s["normals"]).reshape(-1, 3, 3).mean(1)
        if im is not None:
            U = np.array(s["uvs"]).reshape(-1, 3, 2).mean(1)
            h, w = im.shape[:2]
            px = im[((1 - U[:, 1]) % 1 * h).astype(int) % h, (U[:, 0] % 1 * w).astype(int) % w]
            keep = px[:, 3] >= 128
            P, col, NN = P[keep], px[keep, :3].astype(float), NN[keep]
        else:
            col = np.tile(np.array(SLOT.get(sl, (230, 60, 60) if "Signal" in sl or "Lamp" in sl else (200, 0, 200)),
                                   float), (len(P), 1))
        T.append(P); C.append(col); M.append(np.full(len(P), mi)); NS.append(NN)
T, C, M, NS = np.vstack(T), np.vstack(C), np.concatenate(M), np.vstack(NS)
if os.environ.get("BYMESH"):        # colour by mesh (which part owns what), legend printed
    PAL = np.array([(230,120,40),(40,140,230),(60,190,80),(220,60,60),(200,200,60),(160,80,200),(80,200,200),(120,120,120),(250,160,200),(140,90,40)], float)
    C = PAL[M % len(PAL)]
    print("legend:", {want[i]: tuple(int(v) for v in PAL[i % len(PAL)]) for i in range(len(want))})
if os.environ.get("BOX"):          # close-up: BOX=x0,y0,z0,x1,y1,z1 keeps triangles whose centroid is inside
    b_ = np.array([float(v) for v in os.environ["BOX"].split(",")]); c_ = T.mean(1)
    k_ = ((c_ >= b_[:3]) & (c_ <= b_[3:])).all(1)
    T, C, M, NS = T[k_], C[k_], M[k_], NS[k_]
# winding convention of these meshes: the side the stored normals agree with (the game culls by winding)
GN = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
CONV = 1.0 if np.mean(np.sign((GN * NS).sum(1))) >= 0 else -1.0


STATS = []


def render(yaw, pitch):
    a, b = np.radians(yaw), np.radians(pitch)
    # camera looks along -d; Motor Town: x forward, y right, z up
    fwd = np.array([np.cos(b) * np.cos(a), np.cos(b) * np.sin(a), np.sin(b)])   # from car towards camera
    right = np.cross([0, 0, 1], fwd); right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    V = np.stack([right, up, fwd])
    Q = T @ V.T                                         # (n,3,3): screen x, y, depth (bigger = closer)
    front = (GN @ fwd) * CONV > 0                       # faces the camera (by winding)
    Qf, Cf, Mf = Q[front], C[front], M[front]
    nw = np.cross(T[front][:, 1] - T[front][:, 0], T[front][:, 2] - T[front][:, 0])
    nw /= np.linalg.norm(nw, axis=1, keepdims=True) + 1e-9
    light = np.array([0.4, -0.3, 0.85]); light /= np.linalg.norm(light)
    shade = 0.45 + 0.55 * np.abs(nw @ light)
    x0, x1 = Q[..., 0].min(), Q[..., 0].max(); y0, y1 = Q[..., 1].min(), Q[..., 1].max()
    S = (WIDTH - 20) / (x1 - x0)
    W, H = WIDTH, int((y1 - y0) * S) + 20
    zb = np.full((H, W), -1e9); ib = np.full((H, W), -1, int)
    zf = np.full((H, W), 1e9)                           # depth gap to the next surface of another mesh
    mb = np.full((H, W), -1, int)
    sx = (Qf[..., 0] - x0) * S + 10; sy = (y1 - Qf[..., 1]) * S + 10; sz = Qf[..., 2]
    for i in range(len(Qf)):
        xa, ya = sx[i], sy[i]
        bx0, bx1 = max(int(xa.min()), 0), min(int(xa.max()) + 1, W - 1)
        by0, by1 = max(int(ya.min()), 0), min(int(ya.max()) + 1, H - 1)
        if bx1 < bx0 or by1 < by0:
            continue
        gx, gy = np.meshgrid(np.arange(bx0, bx1 + 1) + 0.5, np.arange(by0, by1 + 1) + 0.5)
        d = (ya[1] - ya[2]) * (xa[0] - xa[2]) + (xa[2] - xa[1]) * (ya[0] - ya[2])
        if abs(d) < 1e-9:
            continue
        l1 = ((ya[1] - ya[2]) * (gx - xa[2]) + (xa[2] - xa[1]) * (gy - ya[2])) / d
        l2 = ((ya[2] - ya[0]) * (gx - xa[2]) + (xa[0] - xa[2]) * (gy - ya[2])) / d
        l3 = 1 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if not m.any():
            continue
        z = l1 * sz[i, 0] + l2 * sz[i, 1] + l3 * sz[i, 2]
        Y, X = np.nonzero(m); z = z[m]; Y += by0; X += bx0
        cur = zb[Y, X]; curm = mb[Y, X]
        closer = z > cur
        # remember how close the two front-most surfaces of DIFFERENT meshes are
        other = (curm >= 0) & (curm != Mf[i])
        gap = np.abs(z - cur)
        upd = other & (closer | (gap < zf[Y, X]))
        zf[Y[upd], X[upd]] = np.where(closer[upd], gap[upd], np.minimum(zf[Y[upd], X[upd]], gap[upd]))
        zb[Y[closer], X[closer]] = z[closer]; ib[Y[closer], X[closer]] = i; mb[Y[closer], X[closer]] = Mf[i]
        zf[Y[closer & ~other], X[closer & ~other]] = 1e9
    img = np.full((H, W, 3), 238.0)
    hit = ib >= 0
    img[hit] = Cf[ib[hit]] * shade[ib[hit]][:, None]
    zfight = hit & (zf < 0.4)
    img[zfight] = img[zfight] * 0.3 + np.array([255, 0, 255]) * 0.7
    STATS.append(zfight.sum() / max(hit.sum(), 1))
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


VIEWS = [tuple(float(a) for a in v.split(",")) for v in os.environ.get("VIEWS", "150,12;-150,12;30,12;90,3").split(";")]
views = [render(*v) for v in VIEWS] + [Image.new("RGB", (1, 1), "white")] * max(0, 4 - len(VIEWS))
Wt = max(v.width for v in views)
sheet = Image.new("RGB", (Wt * 2, max(views[0].height, views[1].height) + max(views[2].height, views[3].height)), "white")
sheet.paste(views[0], (0, 0)); sheet.paste(views[1], (Wt, 0))
sheet.paste(views[2], (0, views[0].height)); sheet.paste(views[3], (Wt, views[0].height))
sheet.save(out)
print("wrote %s (%d triangles) zfight %.2f%%" % (out, len(T), 100 * float(np.mean(STATS))))
