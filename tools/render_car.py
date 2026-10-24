"""Quick textured renders of a converted car (mesh JSONs + textures): side/front/rear/top PNG sheet.
Usage: render_car.py <build_dir> <out.png> [meshes,comma,separated]"""
import json, os, sys
from PIL import Image, ImageDraw
B = sys.argv[1]; out = sys.argv[2]
want = sys.argv[3].split(",") if len(sys.argv) > 3 else None
SLOT = {"Paint": (40, 70, 170), "Paint2": (230, 230, 230), "Bottom": (35, 35, 38), "Trim": (170, 170, 175), "Glass": (150, 185, 205),
        "Mirror": (220, 220, 240)}
texs = {}
items = []
for f in os.listdir(os.path.join(B, "meshes")):
    if not f.endswith(".json") or f == "car.json": continue
    m = f[:-5]
    if want and m not in want: continue
    if not want and (m.startswith("Aero_") and "KIT00" not in m): continue
    for s in json.load(open(os.path.join(B, "meshes", f)))["slots"]:
        im = None; sl = s["slot"]
        p = os.path.join(B, "textures", sl[4:] + ".png") if sl.startswith("Tex_") else None
        tex_slot = sl
        if p and os.path.exists(p):
            im = texs.setdefault(p, Image.open(p).convert("RGBA"))
        P, N, U = s["positions"], s["normals"], s["uvs"]
        for i in range(0, len(P), 3):
            t = P[i:i + 3]; n = [sum(x[k] for x in N[i:i + 3]) / 3 for k in range(3)]
            if im:
                W, H = im.size; u = sum(x[0] for x in U[i:i + 3]) / 3; v = sum(x[1] for x in U[i:i + 3]) / 3
                c = im.getpixel((int(u % 1 * W) % W, int((1 - v) % 1 * H) % H))
                if c[3] < 128:
                    continue        # masked (alpha) texel: see-through
                c = c[:3]
            else:
                c = SLOT.get(sl, (230, 60, 60) if "Signal" in sl else (255, 0, 255))
            shade = 0.55 + 0.45 * max(0, n[2] * 0.5 + abs(n[1]) * 0.3 + 0.4)
            c = tuple(min(255, int(x * shade)) for x in c)
            items.append((t, n, c))
def view(fn_key, fn_proj, sel, W, H):
    im = Image.new("RGB", (W, H), (245, 245, 245)); d = ImageDraw.Draw(im)
    for t, n, c in sorted([x for x in items if sel(x)], key=lambda x: fn_key(x[0])):
        d.polygon([fn_proj(q) for q in t], fill=c)
    return im
S = 2.6
side = view(lambda t: -min(q[1] for q in t), lambda q: ((270 - q[0]) * S, (140 - q[2]) * S), lambda x: x[1][1] < 0.1, int(540 * S), int(150 * S))
front = view(lambda t: max(q[0] for q in t), lambda q: ((110 - q[1]) * S, (140 - q[2]) * S), lambda x: x[1][0] > -0.1, int(220 * S), int(150 * S))
rear = view(lambda t: -min(q[0] for q in t), lambda q: ((110 + q[1]) * S, (140 - q[2]) * S), lambda x: x[1][0] < 0.1, int(220 * S), int(150 * S))
sheet = Image.new("RGB", (side.width, side.height + front.height), "white")
sheet.paste(side, (0, 0)); sheet.paste(front, (0, side.height)); sheet.paste(rear, (front.width + 10, side.height))
sheet.save(out)
