"""Driver's-eye render of a converted car (mesh JSONs + textures in the build dir): checks gauges / cluster / wheel / mirrors
are where the driver sees them before an in-game test (user rule: never ship a car without gauges or mirrors).
usage: render_cockpit.py <cars/spec.json> <out.png> [fov_deg] [pitch_deg, down < 0]   (flat-shaded, textured by each triangle's UV centroid)"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

spec = json.load(open(sys.argv[1])); out = sys.argv[2]; fov = float(sys.argv[3]) if len(sys.argv) > 3 else 80.0
pitch = math.radians(float(sys.argv[4]) if len(sys.argv) > 4 else -12.0)
cp, sp_ = math.cos(pitch), math.sin(pitch)
B = os.path.dirname(os.path.expanduser(spec["out_dir"]))
eye = np.array(spec["blueprint"]["cockpit_camera"], float)
car = json.load(open(os.path.join(B, "car.json")))
texmap = car.get("textures", {})
cache = {}


def tex(slot):
    if slot not in cache:
        f = texmap.get(slot) or texmap.get("Tex_" + slot) or (texmap.get("Tex_Interior_D") if slot == "Gauges" else None)
        try:
            cache[slot] = Image.open(f).convert("RGB") if f else None
        except Exception:
            cache[slot] = None
    return cache[slot]


FLAT = {"Paint": (200, 90, 30), "Glass": None, "Window": None, "Bottom": (30, 30, 32), "Trim": (160, 160, 165), "Mirror": (120, 200, 255)}
W, H = 1600, 900
f = (W / 2) / math.tan(math.radians(fov / 2))
tris = []
for fn in os.listdir(os.path.join(B, "meshes")):
    if not fn.endswith(".json") or fn.startswith("Aero_") and "KIT00" not in fn:
        continue
    m = json.load(open(os.path.join(B, "meshes", fn)))
    for s in m.get("slots", []):
        P = np.array(s["positions"], float).reshape(-1, 3, 3); U = np.array(s["uvs"], float).reshape(-1, 3, 2)
        if fn.startswith(("Wheel", "SideMirror", "RightSideMirror", "Popup")):
            continue   # placed by components in game; mirrors are checked by check_mirrors.py
        col = FLAT.get(s["slot"], "tex")
        if col is None:
            continue
        t = tex(s["slot"]) if col == "tex" else None
        for p, u in zip(P, U):
            rel = p - eye
            rel = np.c_[rel[:, 0] * cp + rel[:, 2] * sp_, rel[:, 1], -rel[:, 0] * sp_ + rel[:, 2] * cp]   # camera pitched down
            if rel[:, 0].min() < 3:   # behind / at the eye (camera looks +x)
                continue
            if t is not None:
                uc = u.mean(0); c = t.getpixel((int(uc[0] % 1 * (t.width - 1)), int(uc[1] % 1 * (t.height - 1))))
            else:
                c = col if col != "tex" else (255, 0, 255)
            n = np.cross(p[1] - p[0], p[2] - p[0]); nl = np.linalg.norm(n) or 1
            shade = 0.55 + 0.45 * abs(n @ np.array([-0.6, 0.2, 0.75]) / nl)
            c = tuple(int(min(255, v * shade)) for v in c)
            scr = [(W / 2 + f * r[1] / r[0], H / 2 - f * r[2] / r[0]) for r in rel]
            tris.append((rel[:, 0].mean(), scr, c))
tris.sort(key=lambda x: -x[0])
img = Image.new("RGB", (W, H), (150, 190, 230)); d = ImageDraw.Draw(img)
for _, scr, c in tris:
    d.polygon(scr, fill=c)
img.save(out)
print("rendered %d triangles from the eye %s -> %s" % (len(tris), eye.tolist(), out))
