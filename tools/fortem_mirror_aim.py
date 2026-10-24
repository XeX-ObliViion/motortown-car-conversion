"""Aim the Fortem/Magis-style shared side mirror (one recentred glass mesh; the right component = the same mesh at
scale Y -1): find the component rotation (pitch, yaw) that turns the glass's own facing so the eye ray reflects straight
back, slightly outward. Uses ps_to_mt.rot_axes, so the result matches how the game/our counter_rotate interpret it.
usage: fortem_mirror_aim.py <spec.json> <part> <group> [source_scale]
prints the left and right rotations for blueprint.component_rotations and the meshes' counter_rotate."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps_to_mt as P


def unit(v):
    L = math.sqrt(sum(x * x for x in v)) or 1
    return [x / L for x in v]


def aim(n_glass, centre, eye, outward):
    d = unit([centre[k] - eye[k] for k in range(3)])
    r = unit([-1, outward, -0.02])
    want = unit([r[k] - d[k] for k in range(3)])
    best = None
    for pi in range(-300, 301):
        p = pi / 10
        for yi in range(-450, 451, 2):
            y = yi / 10
            X, Y, Z = P.rot_axes([p, y, 0])
            v = [n_glass[0] * X[k] + n_glass[1] * Y[k] + n_glass[2] * Z[k] for k in range(3)]
            dot = sum(v[k] * want[k] for k in range(3))
            if best is None or dot > best[0]:
                best = (dot, p, y)
    return best


def main():
    spec = json.load(open(sys.argv[1])); part = sys.argv[2]; group = int(sys.argv[3])
    P.PS_SCALE = float(sys.argv[4]) if len(sys.argv) > 4 else spec.get("source_scale", 1000.0)
    geo = os.path.expanduser(spec["geometry_dir"])
    path = os.path.join(geo, "%s_%s_%s.dae" % (spec["prefix"], part, spec.get("lod", "A")))
    tex, tris = P.load_dae(path)[group]
    left = [t for t in tris if sum(P.to_mt(c[0])[1] for c in t) < 0]
    n = unit([sum(P.nrm_mt(c[1])[k] for t in left for c in t) for k in range(3)])
    cen = [sum(P.to_mt(c[0])[k] for t in left for c in t) / (3 * len(left)) for k in range(3)]
    eye = spec["blueprint"]["cockpit_camera"]
    L = aim(n, cen, eye, -0.15)
    # right component = scale Y -1: its glass normal is the left one mirrored; it sits at the mirrored centre
    nr = [n[0], -n[1], n[2]]; cr = [cen[0], -cen[1], cen[2]]
    # with scale Y -1 the rotation acts on the mirrored geometry: search on the un-mirrored normal toward the
    # mirrored target (equivalent to aiming the right glass), as done for the 911
    Rr = aim(n, [cr[0], -cr[1], cr[2]], [eye[0], -eye[1], eye[2]], -0.15)
    print("glass normal", [round(x, 3) for x in n], "centre", [round(x, 1) for x in cen])
    print("left  rot [%.1f, %.1f, 0] (match %.4f)" % (L[1], L[2], L[0]))
    print("right rot [%.1f, %.1f, 0] (match %.4f)" % (Rr[1], -Rr[2], Rr[0]))   # yaw sign flips under scale Y -1 (checked on the 997: -6.1, 7.8)


if __name__ == "__main__":
    main()
