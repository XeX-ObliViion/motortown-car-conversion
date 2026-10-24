"""Flush glass covers over lamp recesses whose source model has no lens cover (Elise front indicators).
Reads the converted mesh JSONs, fits a plate over the lamp triangles of each side and writes it into the spec
as Body extra_triangles (slot Glass). Usage: lens_caps.py cars/<car>.json  (spec key lens_caps, see below)."""
import json, os, sys


def cross(u, w):
    return [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]


def norm(v):
    l = sum(x * x for x in v) ** 0.5 or 1
    return [x / l for x in v]


def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, hi = half(pts), half(reversed(pts))
    return lo[:-1] + hi[:-1]


def main():
    path = sys.argv[1]
    spec = json.load(open(path))
    out_dir = os.path.expanduser(spec["out_dir"])
    tris = []
    winding = []
    for c in spec["lens_caps"]:
        for mesh in c["meshes"]:
            for s in json.load(open(os.path.join(out_dir, mesh + ".json")))["slots"]:
                P, N = s["positions"], s["normals"]
                for i in range(0, len(P), 3):
                    t = P[i:i + 3]
                    fn = cross([t[1][k] - t[0][k] for k in range(3)], [t[2][k] - t[0][k] for k in range(3)])
                    vn = [sum(N[i + j][k] for j in range(3)) for k in range(3)]
                    winding.append(sum(fn[k] * vn[k] for k in range(3)))
                    if s["slot"] in c["slots"]:
                        tris.append(t)
    sign = 1 if sum(1 for w in winding if w > 0) >= len(winding) / 2 else -1   # face normal vs stored normals
    extra = []
    for c in spec["lens_caps"]:
        for side in (-1, 1):
            b = c["box"]
            sel = [t for t in tris if all(b[0] <= q[0] <= b[3] and b[1] <= side * q[1] <= b[4] and b[2] <= q[2] <= b[5] for q in t)]
            if not sel:
                continue
            n = [0, 0, 0]
            for t in sel:
                fn = cross([t[1][k] - t[0][k] for k in range(3)], [t[2][k] - t[0][k] for k in range(3)])
                if fn[0] + fn[2] < 0:          # outward = forward/up for a front lamp
                    fn = [-x for x in fn]
                n = [n[k] + fn[k] for k in range(3)]
            n = norm(n)
            pts = [q for t in sel for q in t]
            cen = [sum(q[k] for q in pts) / len(pts) for k in range(3)]
            e1 = norm(cross(n, [0, 0, 1]) if abs(n[2]) < 0.9 else cross(n, [1, 0, 0])); e2 = cross(n, e1)
            d = max(sum((q[k] - cen[k]) * n[k] for k in range(3)) for q in pts) + c.get("lift", 0.3)
            h = hull([(round(sum((q[k] - cen[k]) * e1[k] for k in range(3)), 3),
                       round(sum((q[k] - cen[k]) * e2[k] for k in range(3)), 3)) for q in pts])
            grow = c.get("grow", 1.0)
            P3 = [[cen[k] + d * n[k] + grow * (a * e1[k] + bb * e2[k]) for k in range(3)] for a, bb in h]
            mid = [cen[k] + d * n[k] for k in range(3)]
            for i in range(len(P3)):
                t = [mid, P3[i], P3[(i + 1) % len(P3)]]
                fn = cross([t[1][k] - t[0][k] for k in range(3)], [t[2][k] - t[0][k] for k in range(3)])
                if sign * sum(fn[k] * n[k] for k in range(3)) < 0:
                    t = [t[0], t[2], t[1]]
                extra += [[round(x, 3) for x in q] for q in t]
            print("lens cap side %+d: %d lamp tris, plate %d pts, normal %s, lift %.1f" % (side, len(sel), len(h), [round(x, 2) for x in n], d))
    spec["meshes"]["Body"]["extra_triangles"] = [{"slot": spec.get("lens_cap_slot", "Glass"), "positions": extra}]
    tmp = path + ".tmp"
    json.dump(spec, open(tmp, "w"), indent=1); json.load(open(tmp)); os.replace(tmp, path)


if __name__ == "__main__":
    main()
