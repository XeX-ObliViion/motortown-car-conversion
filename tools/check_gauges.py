"""Gauge check for a converted car (run after ps_to_mt, with check_mirrors.py): every redrawn dial face (spec gauge_faces,
texture centre) must sit on the cluster at a needle socket, on the glowing Gauges slot when the spec splits one out, and
not as part of the steering wheel mesh. User rule (2026-11-13): never ship a car without working gauges or mirrors.
usage: check_gauges.py cars/<car>.json      exit 1 on failure
Converted mesh UVs: v = 1 - image row (so a face centre (u, row) is looked up at (u, 1 - row))."""
import json, os, sys
import numpy as np

spec = json.load(open(sys.argv[1]))
B = os.path.join(os.path.dirname(os.path.expanduser(spec["out_dir"])), "meshes")
body = json.load(open(os.path.join(B, "Body.json")))
sockets = {s["name"]: np.array(s["loc"], float) for s in spec.get("dashboard", {}).get("sockets", [])}
has_gauge_slot = any(s["slot"] == "Gauges" for s in body["slots"])


def bary(q, a, b, c):
    v0, v1, v2 = b - a, c - a, q - a
    d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-12:
        return None
    v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den
    return np.array([1 - v - w, v, w])


eye = np.array(spec.get("blueprint", {}).get("cockpit_camera", [0, 0, 0]), float)
# see-through glass (Glass/Window slots) doesn't hide the dials; a textured "glass" (Heat cluster) does
ALL = [np.array(s["positions"]).reshape(-1, 3, 3) for s in body["slots"] if s["slot"] not in ("Glass", "Window", "Windows")]
ALL = np.concatenate(ALL) if ALL else np.zeros((0, 3, 3))


def blockers(pt):
    """triangles between the eye and a dial (glass included: a Heat cluster glass rendered opaque and hid the dials);
    the steering wheel is left out (the driver looks through it)"""
    d = pt - eye; L = np.linalg.norm(d); d = d / L
    e1 = ALL[:, 1] - ALL[:, 0]; e2 = ALL[:, 2] - ALL[:, 0]; h = np.cross(d, e2); det = (e1 * h).sum(1)
    okd = np.abs(det) > 1e-9; inv = np.where(okd, 1 / np.where(okd, det, 1), 0)
    s_ = eye - ALL[:, 0]; u = (s_ * h).sum(1) * inv; q = np.cross(s_, e1); v = (q @ d) * inv; t = (e2 * q).sum(1) * inv
    return int(((u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0.5) & (t < L - 0.8) & okd).sum())


ok = True
for tslot, faces in spec.get("gauge_faces", {}).items():
    for g in faces:
        u, row = g["center"]; best = None
        # ProStreet/MW/Heat meshes: v = 1 - row; AC meshes keep the flipped v = -row (their uv_split boxes are negative)
        for s in body["slots"]:
            if s["slot"] not in (tslot, "Gauges"):
                continue
            P = np.array(s["positions"]).reshape(-1, 3, 3); U = np.array(s["uvs"]).reshape(-1, 3, 2)
            for p, uv in zip(P, U):
              # compare inside one texture tile: AC meshes keep their UVs whole tiles away (v 1..2 up to 5..6)
              uv = uv - np.floor(uv.min(0) + 1e-6)
              for q in (np.array([u, 1 - row]),):
                b = bary(q, *uv)
                if b is None or (b < -1e-4).any():
                    continue
                pt = b @ p
                name, d = min(((n, np.linalg.norm(pt - l)) for n, l in sockets.items()), key=lambda x: x[1]) if sockets else ("-", 0)
                if best is None or d < best[2]:
                    best = (s["slot"], pt, d, name)
        label = "%s %g-%g" % (g.get("note", "")[:20] or "dial", g.get("min", 0), g.get("max", 0))
        if best is None:
            print("  FAIL %-28s face centre not on the body (in the wheel mesh, or dropped)" % label); ok = False; continue
        slot, pt, d, name = best
        nb = blockers(pt)
        bad = d > 3.0 or (has_gauge_slot and slot != "Gauges") or nb > 0
        ok &= not bad
        print("  %s %-28s at %s on %-14s nearest socket %s (%.1f cm), %d triangles between eye and dial" % ("FAIL" if bad else "ok  ", label, np.round(pt, 1).tolist(), slot, name, d, nb))
print("gauges ok" if ok else "GAUGES FAIL")
sys.exit(0 if ok else 1)
