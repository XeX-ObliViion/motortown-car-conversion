"""Assetto Corsa KN5 (v5/v6) -> per-part COLLADA files in the layout ps_to_mt.load_dae reads (like the NFS exports:
<prefix>_<PART>_A.dae, metres, x forward / y left / z up, so a spec uses source_scale 100), plus the embedded textures.
usage: kn5_to_obj.py <file.kn5> <out_dir> [prefix]          (no args after the kn5: inventory only)
Parts = top-level groups of the node tree (e.g. WHEEL_LF, DOOR_L, STEER_HR, BODY); every mesh keeps its material name.
Read-only on the input; refuses files that aren't plain sc6969 (encrypted/protected models are not handled)."""
import os, struct, sys
import numpy as np


class R:
    def __init__(self, b):
        self.b, self.o = b, 0
    def u(self, fmt):
        v = struct.unpack_from(fmt, self.b, self.o); self.o += struct.calcsize(fmt); return v
    def i(self): return self.u("<i")[0]
    def f(self): return self.u("<f")[0]
    def byte(self): return self.u("<B")[0]
    def s(self):
        n = self.i(); v = self.b[self.o:self.o + n].decode("utf-8", "replace"); self.o += n; return v
    def raw(self, n):
        v = self.b[self.o:self.o + n]; self.o += n; return v


def parse(path):
    r = R(open(path, "rb").read())
    assert r.raw(6) == b"sc6969", "not a plain KN5 (protected or another format)"
    ver = r.i()
    if ver > 5:
        r.i()
    textures = []
    for _ in range(r.i()):
        r.i(); name = r.s(); size = r.i(); textures.append((name, r.raw(size)))
    materials = []
    for _ in range(r.i()):
        m = {"name": r.s(), "shader": r.s()}
        r.byte(); r.byte(); r.i()                         # blend mode, alpha tested, depth mode
        m["props"] = {}
        for _ in range(r.i()):
            n = r.s(); m["props"][n] = r.f(); r.raw(36)   # value + vec2/vec3/vec4
        m["tex"] = {}
        for _ in range(r.i()):
            slot = r.s(); r.i(); m["tex"][slot] = r.s()
        materials.append(m)
    meshes = []; dummies = {}
    def node(parent_m, top):
        cls = r.i(); name = r.s(); nchild = r.i(); r.byte()
        M = parent_m
        if cls == 1:
            M = np.array(r.u("<16f"), float).reshape(4, 4) @ parent_m   # row-vector convention: v' = v @ M
            dummies[name.upper()] = M
        elif cls in (2, 3):
            r.byte(); r.byte(); r.byte()
            if cls == 3:
                for _ in range(r.i()):
                    r.s(); r.raw(64)
            nv = r.i(); stride = 44 if cls == 2 else 76
            V = np.frombuffer(r.raw(nv * stride), dtype="<f4").reshape(nv, stride // 4)
            ni = r.i(); I = np.frombuffer(r.raw(ni * 2), dtype="<u2").astype(int)
            mat = r.i(); r.i(); r.f(); r.f()                          # layer, lodIn, lodOut
            if cls == 2:
                r.raw(16); r.byte()                                  # bounding sphere + renderable (static meshes only)
            assert ni % 3 == 0 and (ni == 0 or I.max() < nv), (name, nv, ni)
            meshes.append({"name": name, "top": top, "mat": mat, "pos": V[:, 0:3], "nrm": V[:, 3:6], "uv": V[:, 6:8],
                           "idx": I.reshape(-1, 3), "M": parent_m, "skinned": cls == 3})
        if cls == 1 and name.upper().startswith("STEER_"):
            top = name   # steering wheel sits inside the cockpit group; keep it its own part
        for _ in range(nchild):
            node(M, top if top else name if cls == 1 and parent_m is not ROOT else top)
    ROOT = np.eye(4)
    node(ROOT, None)
    assert r.o == len(r.b), "trailing bytes: %d" % (len(r.b) - r.o)   # self-check: the whole file was consumed
    for m in materials:
        if m["name"].startswith("Material"):
            m["name"] = "ac_" + m["name"]   # ps_to_mt.load_dae re-keys "Material*" names by NFS texture hash; AC has none
    for m in meshes:
        m["dummies"] = dummies   # hub pivots for axes()
    return ver, textures, materials, meshes


def world(m):
    P = np.c_[m["pos"], np.ones(len(m["pos"]))] @ m["M"]
    N = m["nrm"] @ m["M"][:3, :3]
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    return P[:, :3], N


AC_TO_MW = None   # set from the wheel nodes: AC is Y up; forward/left axes are measured, not assumed


def axes(meshes):
    """AC car frame -> MW-style frame (x fwd, y left, z up): find forward and left from the wheel group centres."""
    c = {k: meshes[0]["dummies"][k][3, :3] for k in ("WHEEL_LF", "WHEEL_RF", "WHEEL_LR")}   # hub pivots, not mesh means (calipers skew those)
    lf, rf, lr = c["WHEEL_LF"], c["WHEEL_RF"], c["WHEEL_LR"]
    fwd = lf - lr; fwd /= np.linalg.norm(fwd); left = lf - rf; left /= np.linalg.norm(left)
    up = np.cross(fwd, left)
    return np.array([fwd, left, up])   # rows: MW x, y, z in AC coordinates


def write_dae(path, parts, materials):
    mats = sorted({materials[m["mat"]]["name"] for m in parts})
    out = ['<?xml version="1.0"?><COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">',
           "<library_effects>"] + ['<effect id="fx%d"><profile_COMMON><newparam sid="s"><surface type="2D"><init_from>%s</init_from></surface></newparam></profile_COMMON></effect>'
                                   % (k, materials_tex(materials, n)) for k, n in enumerate(mats)] + ["</library_effects><library_materials>"]
    out += ['<material id="m%d" name="%s"><instance_effect url="#fx%d"/></material>' % (k, n, k) for k, n in enumerate(mats)]
    out.append("</library_materials><library_geometries>")
    for gi, m in enumerate(parts):
        P, N, U = m["P"], m["N"], m["uv"]
        out.append('<geometry id="g%d"><mesh>' % gi)
        for sid, A, st in (("p", P, 3), ("n", N, 3), ("t", np.c_[U[:, 0], 1 - U[:, 1]], 2)):   # AC v down -> v up
            out.append('<source id="g%d%s"><float_array count="%d">%s</float_array><technique_common><accessor stride="%d"/></technique_common></source>'
                       % (gi, sid, A.size, " ".join("%.6g" % x for x in A.ravel()), st))
        out.append('<vertices id="g%dv"><input semantic="POSITION" source="#g%dp"/></vertices>' % (gi, gi))
        out.append('<triangles material="material%d" count="%d"><input semantic="VERTEX" source="#g%dv" offset="0"/><input semantic="NORMAL" source="#g%dn" offset="0"/><input semantic="TEXCOORD" source="#g%dt" offset="0"/><p>%s</p></triangles></mesh></geometry>'
                   % (mats.index(materials[m["mat"]]["name"]), len(m["idx"]), gi, gi, gi, " ".join(map(str, m["idx"].ravel()))))
    out.append("</library_geometries></COLLADA>")
    open(path, "w").write("".join(out))


def materials_tex(materials, name):
    m = next(x for x in materials if x["name"] == name)
    return m["tex"].get("txDiffuse", "")


def main():
    path = sys.argv[1]
    ver, textures, materials, meshes = parse(path)
    tris = sum(len(m["idx"]) for m in meshes)
    print("KN5 v%d: %d textures, %d materials, %d meshes, %d triangles" % (ver, len(textures), len(materials), len(meshes), tris))
    tops = {}
    for m in meshes:
        tops.setdefault(m["top"], [0, 0]); tops[m["top"]][0] += 1; tops[m["top"]][1] += len(m["idx"])
    for t, (n, k) in sorted(tops.items(), key=lambda kv: -kv[1][1]):
        print("  %-40s %4d meshes %8d tris" % (t, n, k))
    if len(sys.argv) < 3:
        return
    out, prefix = sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "AC")
    os.makedirs(os.path.join(out, "geo"), exist_ok=True); os.makedirs(os.path.join(out, "textures"), exist_ok=True)
    for n, data in textures:
        open(os.path.join(out, "textures", n), "wb").write(data)
    A = axes(meshes)
    groups = {}
    for m in meshes:
        P, N = world(m)
        m["P"], m["N"] = P @ A.T, N @ A.T
        groups.setdefault((m["top"] or "ROOT").upper().replace(" ", "_"), []).append(m)
    zmin = min(g["P"][:, 2].min() for gs in groups.values() for g in gs)   # ground = lowest point (tyre bottoms)
    for gs in groups.values():
        for g in gs:
            g["P"] = g["P"] - [0, 0, zmin]
    for part, gs in groups.items():
        write_dae(os.path.join(out, "geo", "%s_%s_A.dae" % (prefix, part)), gs, materials)
    import json
    json.dump({"version": ver, "materials": [{k: v for k, v in m.items() if k != "props"} for m in materials],
               "parts": {p: sum(len(g["idx"]) for g in gs) for p, gs in groups.items()}}, open(os.path.join(out, "inventory.json"), "w"), indent=1)
    print("wrote %d parts -> %s" % (len(groups), out))


if __name__ == "__main__":
    main()
