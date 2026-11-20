"""Wheel material pass (runs on a build dir before the editor build; idempotent). User report 2026-11-13: rims
fitted to OTHER cars showed white tyres/tread/sidewalls and the AC rims could not be painted.
For every mesh imported to /Game/Cars/Parts/Wheels:
  1. Bottom / Trim (body materials whose colour follows the car they sit on) -> fixed textured materials
     Tex_WHEEL_RUBBER (near-black) / Tex_WHEEL_METAL (grey).
  2. The rim is paintable: a Wheel_01 slot that wasn't paintable becomes paintable; a wheel with paintable or rim
     textures but no Wheel_01 gets its main rim texture mapped to Wheel_01 (AC rims, Heat RX-7).
  3. Paint never reaches the tyre: triangles of a paintable slot beyond TYRE_R x the wheel radius move to a
     non-paintable copy <slot>_TYRE with the same texture (MW wheels carry rim + tyre on one texture).
usage: wheel_mats.py <build dir> [...]"""
import json, os, re, sys

TYRE_R = 0.78
RUBBER, METAL, RIMMETAL = "Tex_WHEEL_RUBBER", "Tex_WHEEL_METAL", "Tex_WHEEL_RIMMETAL"
NOT_RIM = re.compile(r"TIRE|TYRE|TREAD|DISC|DISK|ROTOR|CAP|SKUNK|CALIP|BADGE|LOGO|WHEEL_RUBBER|WHEEL_RIMMETAL|_TYRE$", re.I)


def solid_png(path, rgb):
    if not os.path.exists(path):
        from PIL import Image
        Image.new("RGB", (8, 8), rgb).save(path)


def read_obj(p):
    head, faces, cur = [], [], None
    for l in open(p):
        if l.startswith("f "):
            faces.append((cur, l))
        elif l.startswith("usemtl "):
            cur = re.sub(r"^o\d_", "", l.split()[1])   # order prefix written below
        elif l.startswith("g "):
            pass
        else:
            head.append(l)
    V = [list(map(float, l.split()[1:4])) for l in head if l.startswith("v ")]
    return head, faces, V


def face_r(line, V):
    idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
    return sum((V[i][0] ** 2 + V[i][2] ** 2) ** 0.5 for i in idx) / len(idx)


def face_rmax(line, V):
    return max((V[int(t.split("/")[0]) - 1][0] ** 2 + V[int(t.split("/")[0]) - 1][2] ** 2) ** 0.5 for t in line.split()[1:])


def clip_ring(lines, cut, head, V, T):
    """Split faces on the circle r = cut (r in the X-Z plane): returns (faces inside, faces outside). Straddling faces
    are clipped; new corners (position, UV, normal interpolated) are appended to head, V and T and shared per edge so
    the two sides stay watertight."""
    N = [list(map(float, l.split()[1:4])) for l in head if l.startswith("vn ")]
    cache = {}

    def rad(p):
        return (p[0] ** 2 + p[2] ** 2) ** 0.5

    def corner(tok):
        f = (tok.split("/") + ["", ""])[:3]
        return f

    def lerp(a, b, t):
        return [x + (y - x) * t for x, y in zip(a, b)]

    def cross(ta, tb):
        key = (ta, tb) if ta < tb else (tb, ta)
        if key in cache:
            return cache[key]
        fa, fb = corner(ta), corner(tb)
        pa, pb = V[int(fa[0]) - 1], V[int(fb[0]) - 1]
        lo, hi = 0.0, 1.0                       # bisection on the true radius along the edge
        ina = rad(pa) < cut
        for _ in range(30):
            mid = (lo + hi) / 2
            if (rad(lerp(pa, pb, mid)) < cut) == ina:
                lo = mid
            else:
                hi = mid
        t = (lo + hi) / 2
        p = lerp(pa, pb, t); V.append(p); head.append("v %.6f %.6f %.6f\n" % tuple(p)); parts = [str(len(V))]
        if fa[1] and fb[1]:
            uv = lerp(T[int(fa[1]) - 1], T[int(fb[1]) - 1], t); T.append(uv); head.append("vt %.6f %.6f\n" % tuple(uv))
            parts.append(str(len(T)))
        else:
            parts.append("")
        if fa[2] and fb[2]:
            n = lerp(N[int(fa[2]) - 1], N[int(fb[2]) - 1], t); ln = sum(x * x for x in n) ** 0.5 or 1.0
            n = [x / ln for x in n]; N.append(n); head.append("vn %.6f %.6f %.6f\n" % tuple(n)); parts.append(str(len(N)))
        else:
            parts.append("")
        tok = "/".join(parts).rstrip("/") if not parts[2] else "/".join(parts)
        cache[key] = tok
        return tok

    def fan(poly):
        return ["f %s %s %s\n" % (poly[0], poly[i], poly[i + 1]) for i in range(1, len(poly) - 1)]

    inside, outside = [], []
    for l in lines:
        toks = l.split()[1:]
        ins = [rad(V[int(t.split("/")[0]) - 1]) < cut for t in toks]
        if all(ins):
            inside.append(l); continue
        if not any(ins):
            outside.append(l); continue
        pin, pout = [], []
        for i, t in enumerate(toks):
            u = toks[(i + 1) % len(toks)]
            (pin if ins[i] else pout).append(t)
            if ins[i] != ins[(i + 1) % len(toks)]:
                c = cross(t, u); pin.append(c); pout.append(c)
        inside += fan(pin); outside += fan(pout)
    return inside, outside


def load_gray(path):
    if not path or not os.path.exists(path):
        return None
    from PIL import Image
    return Image.open(path).convert("L")


def face_uv(line, T):
    try:
        uv = [T[int(t.split("/")[1]) - 1] for t in line.split()[1:]]
    except (IndexError, ValueError):
        return None
    return uv


def face_gray(line, T, img):
    uv = face_uv(line, T)
    if not uv:
        return 255
    u = sum(x[0] for x in uv) / len(uv) % 1.0; v = sum(x[1] for x in uv) / len(uv) % 1.0
    W, H = img.size
    return img.getpixel((min(W - 1, int(u * W)), min(H - 1, int((1 - v) * H))))


def atlas(build, texdir, tex, slots, head, T, new):
    """One texture for several fixed wheel slots: grid cells, each face's UVs moved into its slot's cell (new vt lines
    appended to head). A slot whose faces tile (UV span > 1) becomes its average colour. Returns the new slot name."""
    import hashlib, math
    from PIL import Image
    slots = sorted(slots)   # fixed cell order: meshes sharing this atlas (L/R, front/rear) must agree on the layout
    name = "Tex_WATLAS_TYRE_" + hashlib.md5("|".join(sorted(slots)).encode()).hexdigest()[:6]   # TYRE: matte finish
    g = math.ceil(math.sqrt(len(slots))); cell = 1024 if g <= 2 else 512; pad = 4.0 / cell
    img = Image.new("RGB", (g * cell, g * cell), (40, 40, 40))
    nt = len(T)
    for i, s in enumerate(slots):
        cx, cy = i % g, i // g
        src = tex.get(s)
        im = Image.open(src).convert("RGB") if src and os.path.exists(src) else Image.new("RGB", (8, 8), (40, 40, 40))
        tiles = 0; uvs = []
        for l in new[s]:
            uv = face_uv(l, T)
            if uv:
                u0 = math.floor(min(x[0] for x in uv) + 1e-6); v0 = math.floor(min(x[1] for x in uv) + 1e-6)
                uv = [(x[0] - u0, x[1] - v0) for x in uv]
                if max(max(x) for x in uv) > 1.0 + 1e-4:
                    tiles += 1
            uvs.append(uv)
        solid = tiles > 0.05 * max(1, len(uvs))
        if solid:
            im = Image.new("RGB", (cell, cell), im.resize((1, 1), Image.BOX).getpixel((0, 0)))
        img.paste(im.resize((cell, cell), Image.LANCZOS), (cx * cell, cy * cell))
        out = []
        for l, uv in zip(new[s], uvs):
            parts = l.split()[1:]
            if not uv or solid:
                uv = [(0.5, 0.5)] * len(parts)
            refs = []
            for t, (u, v) in zip(parts, uv):
                u = min(max(u, 0.0), 1.0); v = min(max(v, 0.0), 1.0)
                au = (cx + pad + u * (1 - 2 * pad)) / g
                av = 1 - (cy + pad + (1 - v) * (1 - 2 * pad)) / g      # image row from the top = 1 - v
                head.append("vt %.6f %.6f\n" % (au, av)); nt += 1
                f = t.split("/")
                refs.append("/".join([f[0], str(nt)] + f[2:]) if len(f) > 1 else "%s/%d" % (f[0], nt))
            out.append("f " + " ".join(refs) + "\n")
        new[s] = out
    T.extend([None] * (nt - len(T)))
    pth = os.path.join(texdir, name.replace("Tex_", "") + ".png")
    img.save(pth); tex[name] = pth.replace("\\", "/")
    return name


def process(build):
    cj = os.path.join(build, "car.json")
    car = json.load(open(cj))
    tex = car.setdefault("textures", {})
    fsn = car.setdefault("final_slot_names", {})
    paint = car.setdefault("paintable_texture_slots", [])
    texdir = os.path.join(build, "textures"); os.makedirs(texdir, exist_ok=True)
    wheels = [m for m in car["meshes"] if m.get("dest") == "/Game/Cars/Parts/Wheels"]
    if not wheels:
        return
    other_slots = set()
    for m in car["meshes"]:
        if m not in wheels and os.path.exists(m["obj"]):
            other_slots |= {re.sub(r"^o\d_", "", l.split()[1]) for l in open(m["obj"]) if l.startswith("usemtl ")}
    # fixed wheel textures (removed again at the end if no wheel uses them)
    for name, rgb in ((RUBBER, (22, 22, 22)), (METAL, (150, 150, 150)), (RIMMETAL, (150, 150, 150))):
        pth = os.path.join(texdir, name.replace("Tex_", "") + ".png"); solid_png(pth, rgb); tex[name] = pth.replace("\\", "/")
    orig_w1 = {k for k, v in fsn.items() if v == "Wheel_01" and k != RIMMETAL}
    changed = 0
    for m in wheels:
        head, faces, V = read_obj(m["obj"])
        R = max((v[0] ** 2 + v[2] ** 2) ** 0.5 for v in V)
        slots = {}
        for s, l in faces:
            slots.setdefault(s, []).append(l)
        new = {}
        # 1. body materials -> fixed wheel materials
        for s, ls in slots.items():
            t = RUBBER if s == "Bottom" else METAL if s == "Trim" else s
            new.setdefault(t, []).extend(ls)
        # 2. make sure the rim has a paintable Wheel_01
        has_w1 = any(fsn.get(s) == "Wheel_01" for s in new)
        if not has_w1 and RIMMETAL in new:   # copied from an already processed wheel (AC_Rims from the AC cars)
            fsn[RIMMETAL] = "Wheel_01"; has_w1 = True
        if not has_w1:
            # the rim = the slot with the most triangles on the wheel's outer face (dish side), inside the tyre
            ys = [v[1] for v in V]; y0, y1 = min(ys), max(ys); q = 0.3 * (y1 - y0)

            def score(ls):
                yc = [sum(V[int(t.split("/")[0]) - 1][1] for t in l.split()[1:]) / 3 for l in ls if face_r(l, V) < 0.75 * R]
                return max(sum(1 for y in yc if y > y1 - q), sum(1 for y in yc if y < y0 + q))
            cands = [(score(ls), s) for s, ls in new.items()
                     if (s == METAL or (s.startswith("Tex_") and s in tex and not NOT_RIM.search(s))) and s not in other_slots]
            cands = [c for c in cands if c[0] > 0]
            if cands:
                print("  %s rim candidates: %s" % (m["name"], sorted(cands, reverse=True)[:4]))
            if cands:
                rim = max(cands)[1]
                if rim == METAL:   # plain metal is shared with bolts etc. on other wheels: this rim gets its own slot
                    new[RIMMETAL] = new.pop(METAL); rim = RIMMETAL
                fsn[rim] = "Wheel_01"
                print("  %s: rim texture %s -> Wheel_01" % (m["name"], rim))
        for s in new:
            if fsn.get(s) == "Wheel_01" and s not in paint and s in tex:
                paint.append(s)
        # 3. paint never reaches the tyre: the garage replaces the whole rim slot with flat paint, so tyre faces that share
        # the rim texture (MW wheels: the sidewall is on the rim texture) move to a fixed copy: dark faces outside 0.62 R,
        # and anything outside 0.78 R when the texture reaches the tread
        T = [list(map(float, l.split()[1:3])) for l in head if l.startswith("vt ")]
        for s in [s for s in list(new) if s in paint and not s.endswith("_TYRE")]:
            img = load_gray(tex.get(s))
            reach = max(face_r(l, V) for l in new[s]) >= 0.9 * R
            # "dark" relative to this rim's own colour (inner faces), so black/gunmetal rims aren't taken for tyre
            inner = sorted(face_gray(l, T, img) for l in new[s] if face_r(l, V) < 0.6 * R) if img is not None else []
            dark = min(100, 0.6 * inner[len(inner) // 2]) if inner else -1

            # where the tyre starts: the tread rule (0.78 R) and/or where the dark sidewall starts (10th percentile
            # radius of the dark faces outside 0.62 R; light sidewall lettering goes with it)
            cuts = [TYRE_R * R] if reach else []
            darkf = [face_r(l, V) for l in new[s] if img is not None and face_r(l, V) > 0.62 * R and face_gray(l, T, img) < dark]
            if len(darkf) > 20:
                cuts.append(sorted(darkf)[len(darkf) // 10])
            if not cuts:
                continue
            # cut the triangles exactly on that circle (moving whole triangles left a saw-tooth edge, 2026-11-14)
            inside, out = clip_ring(new[s], min(cuts), head, V, T)
            if out:
                ty = s + "_TYRE"
                new[s] = inside
                new.setdefault(ty, []).extend(out)
                tex[ty] = tex[s]
                if not new[s]:
                    del new[s]
                print("  %s: tyre cut at %.2f R: %d triangles of %s -> %s" % (m["name"], min(cuts) / R, len(out), s, ty))
        # 4. the garage also repaints slot 2 (and maybe later ones): like Maja's Wheel Works rims, every fixed part goes
        # into ONE slot (slot 0) with an atlas of their textures; masked badges (alpha cut-outs) can't join it and are dropped
        masked = set(car.get("masked_texture_slots", []))
        for s in [s for s in new if s in masked and fsn.get(s) not in ("Wheel_01", "Wheel_02")]:
            print("  %s: dropped %d badge triangles (%s)" % (m["name"], len(new[s]), s)); del new[s]
        fixed = [k for k in new if fsn.get(k) not in ("Wheel_01", "Wheel_02")]
        if len(fixed) > 1:
            name = atlas(build, texdir, tex, fixed, head, T, new)
            merged = []
            for k in fixed:
                merged += new.pop(k)
            new[name] = merged
            print("  %s: %d fixed slots -> %s" % (m["name"], len(fixed), name))
        # the rim's average colour (sampled at its faces' UVs): make_mt_assets uses it as the default paint colour
        rims = [k for k in new if fsn.get(k) == "Wheel_01" and tex.get(k) and os.path.exists(tex[k])]
        if rims:
            from PIL import Image
            im = Image.open(tex[rims[0]]).convert("RGB"); W_, H_ = im.size; px = []
            for l in new[rims[0]]:
                uv = face_uv(l, T)
                if uv:
                    u = sum(x[0] for x in uv) / len(uv) % 1.0; v = sum(x[1] for x in uv) / len(uv) % 1.0
                    px.append(im.getpixel((min(W_ - 1, int(u * W_)), min(H_ - 1, int((1 - v) * H_)))))
            if px:
                car.setdefault("rim_rgb", {})[m["name"]] = [int(sum(c[i] for c in px) / len(px)) for i in range(3)]
        # 5. the rim and lip become the game's paint material (slots WheelPaint/WheelPaint2 -> M_Body, like the game's and
        # Maja's rims): the garage carries the rim-slot material over to the next rim, so it must be the same everywhere
        for k, (ps, fin) in [(k, ("WheelPaint", "Wheel_01") if fsn.get(k) == "Wheel_01" else ("WheelPaint2", "Wheel_02"))
                             for k in list(new) if fsn.get(k) in ("Wheel_01", "Wheel_02") and k not in ("WheelPaint", "WheelPaint2")]:
            new.setdefault(ps, []).extend(new.pop(k))
            fsn[ps] = fin
        # the game paints colour picker N onto material slot N (garage, 2026-11-14): rim first, lip second
        # the game's rims are [Palette, Wheel_01]; the garage keeps a paint material on slot 1 (and 2 for a lip) when it
        # swaps rim meshes, so ours must match: one fixed slot first, then the rim, the lip, the rest (2026-11-14)
        paint_s = [k for k in new if fsn.get(k) == "Wheel_01"] + [k for k in new if fsn.get(k) == "Wheel_02"]
        rest = [k for k in new if k not in paint_s]
        new = {k: new[k] for k in rest[:1] + paint_s + rest[1:]}
        # UE's OBJ importer orders material slots by NAME, not file order: o<rank>_ prefixes force the order
        # (build_car strips them again)
        written = [l.split()[1] for l in open(m["obj"]) if l.startswith("g ")]
        want = ["o%d_%s" % (min(i, 9), s) for i, s in enumerate(new)]
        if written != want or any(len(new[k]) != len(slots.get(k, [])) for k in new):
            changed += 1
            with open(m["obj"], "w") as f:
                f.writelines(head)
                for (s, ls), w in zip(new.items(), want):
                    f.write("g %s\nusemtl %s\n" % (w, w))   # the importer names + orders slots by the g name
                    f.writelines(ls)
    for name in (RUBBER, METAL, RIMMETAL):
        if not any(name in open(m["obj"]).read() for m in wheels):
            tex.pop(name, None)
    json.dump(car, open(cj, "w"), indent=1)
    print("%s: wheel materials done (%d meshes rewritten)" % (car["car"], changed))


for b in sys.argv[1:]:
    process(os.path.expanduser(b))
