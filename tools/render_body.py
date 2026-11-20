"""Quick flat-shaded check render of a build's Body mesh (texture colour per face): side, front, rear, top.
usage: python tools/render_body.py <build dir> <out.png> [mesh name]"""
import json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw

b, outp = os.path.expanduser(sys.argv[1]), sys.argv[2]
car = json.load(open(os.path.join(b, "car.json"))); tex = car["textures"]
fixed = {"Paint": (200, 30, 30), "Glass": (120, 160, 200), "Trim": (190, 190, 190), "Bottom": (60, 60, 60), "Mirror": (240, 240, 255)}
ims = {}


def col(s, uv):
    if s in fixed:
        return fixed[s]
    if s not in tex:
        return (255, 0, 255)
    if s not in ims:
        ims[s] = Image.open(tex[s]).convert("RGB")
    im = ims[s]; W, H = im.size
    return im.getpixel((min(W - 1, int(uv[0] % 1 * W)), min(H - 1, int((1 - uv[1] % 1) * H))))


m = next(m for m in car["meshes"] if m["name"] == (sys.argv[3] if len(sys.argv) > 3 else "Body"))
V, T, F, cur = [], [], [], None
for l in open(m["obj"]):
    if l.startswith("v "): V.append(list(map(float, l.split()[1:4])))
    elif l.startswith("vt "): T.append(list(map(float, l.split()[1:3])))
    elif l.startswith("usemtl"): cur = re.sub(r"^o\d_", "", l.split()[1])
    elif l.startswith("f "): F.append((cur, [t.split("/") for t in l.split()[1:]]))
V = np.array(V); T = np.array(T) if T else np.zeros((1, 2))
cen = np.array([[V[int(p[0]) - 1] for p in f] for _, f in F]).mean(1)
uvs = [np.mean([T[int(p[1]) - 1] for p in f], 0) if len(f[0]) > 1 and f[0][1] else (0, 0) for _, f in F]
cols = [col(s, uv) for (s, _), uv in zip(F, uvs)]
views = [("side (left)", 0, 2, 1, 1, 1), ("front", 1, 2, 0, -1, 1), ("rear", 1, 2, 0, 1, -1), ("top", 0, 1, 2, 1, 1)]
sc = 2.2; out = Image.new("RGB", (2200, 900), "white"); d = ImageDraw.Draw(out)
spots = [(560, 220), (1450, 220), (1900, 220), (560, 650)]
for (name, a, bb, depth, sign, flip), (ox, oy) in zip(views, spots):
    for i in np.argsort(sign * cen[:, depth]):
        s, f = F[i]
        d.polygon([(ox + flip * V[int(p[0]) - 1][a] * sc, oy - V[int(p[0]) - 1][bb] * sc) for p in f], fill=cols[i])
    d.text((ox - 40, oy - 200), name, fill="black")
out.save(outp)
print("bbox", V.min(0).round(1).tolist(), V.max(0).round(1).tolist(), len(F), "faces ->", outp)
