"""Where on a texture does a dashboard needle socket sit? For each socket: the nearest body surface point using the
given texture slot and its UV (u, image row) - put the redrawn gauge face (spec gauge_faces centre) there.
usage: socket_uv.py cars/<car>.json <texture slot>"""
import json, os, sys
import numpy as np

spec = json.load(open(sys.argv[1])); tslot = sys.argv[2]
B = os.path.join(os.path.dirname(os.path.expanduser(spec["out_dir"])), "meshes")
body = json.load(open(os.path.join(B, "Body.json")))
P, U = [], []
for s in body["slots"]:
    if s["slot"] in (tslot, "Gauges"):
        P.append(np.array(s["positions"]).reshape(-1, 3, 3)); U.append(np.array(s["uvs"]).reshape(-1, 3, 2))
P, U = np.concatenate(P), np.concatenate(U)


def closest(p, a, b, c):
    """closest point on triangle abc to p, as barycentric weights (clamped)"""
    n = np.cross(b - a, c - a); nn = n @ n
    if nn < 1e-12:
        return None, 1e9
    q = p - ((p - a) @ n) / nn * n
    v0, v1, v2 = b - a, c - a, q - a
    d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den
    bw = np.clip(np.array([1 - v - w, v, w]), 0, 1); bw /= bw.sum()
    return bw, np.linalg.norm(bw @ np.array([a, b, c]) - p)


for s in spec.get("dashboard", {}).get("sockets", []):
    p = np.array(s["loc"], float); best = None
    cen = P.mean(1); idx = np.argsort(np.linalg.norm(cen - p, axis=1))[:400]
    for i in idx:
        bw, d = closest(p, *P[i])
        if bw is not None and (best is None or d < best[0]):
            bw = bw * 0.96 + 0.04 / 3          # a hair inside the triangle, so the uv lies on the surface
            uv = U[i] - np.floor(U[i].min(0) + 1e-6)
            n = np.cross(P[i][1] - P[i][0], P[i][2] - P[i][0]); n /= np.linalg.norm(n)
            best = (d, bw @ uv, bw @ P[i], n)
    d, uv, sp, n = best
    eye = np.array(spec.get("blueprint", {}).get("cockpit_camera", [0, 0, 0]), float)
    if n @ (eye - sp) < 0:
        n = -n
    seat = sp + 0.4 * n                         # 0.4 cm proud, like the other dial sockets
    print("%-13s surface %.1f cm away  uv centre [%.4f, %.4f]  seat %s" % (s["name"], d, uv[0], 1 - uv[1], np.round(seat, 2).tolist()))
