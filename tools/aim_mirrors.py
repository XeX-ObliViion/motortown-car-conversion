"""Aim component-placed side mirrors (bases where the mirror is a recentred glass mesh on LeftSideMirror /
RightSideMirror components: Magis, Fortem, Raton, Vista...) from the cockpit camera, after a ps_to_mt run.
usage: aim_mirrors.py cars/<car>.json [--write]   (then run ps_to_mt again and tools/check_mirrors.py)
- the glass normal comes from the built mesh (back in car space if it is already counter-rotated)
- left: eye ray reflects straight back, 0.15 outward; the mesh is counter-rotated so it stays on its housing
- right on a shared mesh ("<mesh>:mirror", component scale Y -1): its own copy of the left glass, RightSideMirror,
  counter-rotated in the mirrored frame (as on the 993 RWB); the yaw sign flips under scale Y -1
- right with its own mesh (Raton SideMirror_Right): aimed like the left, 0.15 outward to +Y"""
import copy, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fortem_mirror_aim as F
import check_mirrors as C


def car_normal(spec, build, mesh):
    m = C.load(build, mesh)
    t = np.concatenate(list(m.values()))
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]).sum(0)
    cr = spec["meshes"][mesh].get("counter_rotate", {})
    if cr.get("rot"):   # undo the bake: v = R^-1 q, or v = S R^-1 S q in the mirrored frame
        S = np.array([1, -1, 1.0])
        n = (n @ C.rot(cr["rot"])) if not cr.get("mirror_frame") else S * ((S * n) @ C.rot(cr["rot"]))
    return list(n / np.linalg.norm(n))


def main():
    path = sys.argv[1]; spec = json.load(open(path))
    build = os.path.expanduser(spec.get("out_dir", "~/mt-work/build/%s" % spec["car"]))
    if os.path.basename(build.rstrip("/\\")) == "meshes":
        build = os.path.dirname(build.rstrip("/\\"))
    eye = spec["blueprint"]["cockpit_camera"]
    comps = spec["mirror_components"]
    rots = spec["blueprint"].setdefault("component_rotations", {})
    left = next(k for k in comps if k.startswith("Left"))
    right = next(k for k in comps if k.startswith("Right"))
    lm = comps[left]
    nL = car_normal(spec, build, lm); cL = spec["recentered"][lm]
    b = F.aim(nL, cL, eye, -spec.get("mirror_outward", 0.15))
    rL = [b[1], b[2], 0]
    print("left  %s normal %s rot %s (match %.4f)" % (lm, np.round(nL, 3).tolist(), rL, b[0]))
    spec["meshes"][lm]["counter_rotate"] = {"rot": rL}
    rots[left] = rL
    rm, _, flip = comps[right].partition(":")
    if flip and rm != lm:
        # its own glass, built mirrored (part "mirror": true) because the component has scale Y -1 (993 RWB: the
        # right glass sits 8 cm behind the left one, so a copy of the left glass missed its housing)
        nR = car_normal(spec, build, rm); cR = spec["recentered"][rm]
        b = F.aim(nR, cR, [eye[0], -eye[1], eye[2]], -spec.get("mirror_outward", 0.15))
        rR = [b[1], -b[2], 0]
        spec.setdefault("mirror_meshes", {})[right] = rm
        spec["meshes"][rm]["counter_rotate"] = {"rot": rR, "mirror_frame": True}
        print("right %s (own mirrored glass) rot %s (match %.4f)" % (rm, rR, b[0]))
    elif flip:
        b = F.aim(nL, cL, [eye[0], -eye[1], eye[2]], -spec.get("mirror_outward", 0.15))
        rR = [b[1], -b[2], 0]
        own = spec.setdefault("mirror_meshes", {}).setdefault(right, "RightSideMirror")
        md = copy.deepcopy(spec["meshes"][lm]); md["counter_rotate"] = {"rot": rR, "mirror_frame": True}
        spec["meshes"][own] = md
        print("right %s (copy of %s, mirrored frame) rot %s (match %.4f)" % (own, lm, rR, b[0]))
    else:
        nR = car_normal(spec, build, rm); cR = spec["recentered"][rm]
        b = F.aim(nR, cR, eye, spec.get("mirror_outward", 0.15))
        rR = [b[1], b[2], 0]
        spec["meshes"][rm]["counter_rotate"] = {"rot": rR}
        print("right %s normal %s rot %s (match %.4f)" % (rm, np.round(nR, 3).tolist(), rR, b[0]))
    rots[right] = rR
    if "--write" in sys.argv:
        json.dump(spec, open(path, "w"), indent=1)
        json.load(open(path))


if __name__ == "__main__":
    main()
