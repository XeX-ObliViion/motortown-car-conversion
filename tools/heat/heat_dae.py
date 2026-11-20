"""Turn HeatExport's raw FBX-SDK COLLADA (<asset>.fbxsdk.dae) into the pipeline's per-part DAE layout.

usage: python heat_dae.py <raw_dir> <geo_out> <CAR> <asset_prefix>
  e.g. heat_dae.py db/heat/R34/raw db/heat/R34/geo R34 car_nissan_skylinegtrvspecr34_1999_

Writes <CAR>_<PART>_A.dae (LOD0, all composite parts) and, for composite meshes whose sections are skinned to more
than one part, <CAR>_<PART>_P<n>_A.dae per part (n = Frosty's PART_n, i.e. the composite part index).
Every triangle list gets a material named after the Heat mesh section (M_Carpaint_Max, M_Glass_WindowFront_Max, ...);
POSITION/NORMAL/TEXCOORD(UV0) share one index so ps_to_mt.load_dae reads them directly.
Frame: Heat is Y-up, X lateral, Z forward, metres. Output = pipeline source frame (X forward, Y left, Z up), metres
(spec "source_scale": 100). Left = +X_heat (right-handed, like Frosty's FBX); R34 check: steering wheel lands on the
right (RHD), triangle winding is CCW-outward (agrees with the stored normals).
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}


def floats(src):
    return [float(x) for x in src.find("c:float_array", NS).text.split()]


def conv(v):   # heat (x lateral, y up, z fwd) -> source (fwd, left, up)
    return (v[2], v[0], v[1])   # Frostbite is right-handed Y-up: +X = left; a pure rotation, winding unchanged


def read_raw(path):
    """-> list of (section_name, positions, normals, uvs, tri_indices, part_per_vertex)"""
    root = ET.parse(path).getroot()
    skins = {}
    for ctl in root.iterfind(".//c:controller", NS):
        skin = ctl.find("c:skin", NS)
        names = ctl.find(".//c:Name_array", NS).text.split()
        vw = skin.find("c:vertex_weights", NS)
        wsrc = [s for s in skin.iterfind("c:source", NS) if s.get("id").endswith("-Weights")][0]
        weights = floats(wsrc)
        vc = [int(x) for x in vw.find("c:vcount", NS).text.split()]
        v = [int(x) for x in vw.find("c:v", NS).text.split()]
        part, k = [], 0
        for n in vc:   # dominant joint per vertex
            best = max(range(n), key=lambda i: weights[v[k + 2 * i + 1]]) if n else None
            part.append(int(names[v[k + 2 * best]].split("_")[1]) if n and names[v[k + 2 * best]].startswith("PART_") else -1)
            k += 2 * n
        skins[skin.get("source")[1:]] = part
    out = []
    for geom in root.iterfind(".//c:geometry", NS):
        mesh = geom.find("c:mesh", NS)
        src = {s.get("id"): s for s in mesh.iterfind("c:source", NS)}
        vin = {}
        for i in mesh.find("c:vertices", NS).findall("c:input", NS):
            vin.setdefault(i.get("semantic"), i.get("source")[1:])   # first TEXCOORD = UV0
        p = floats(src[vin["POSITION"]])
        n = floats(src[vin["NORMAL"]]) if "NORMAL" in vin else None
        t = floats(src[vin["TEXCOORD"]]) if "TEXCOORD" in vin else None
        tri = mesh.find("c:triangles", NS)
        assert len(tri.findall("c:input", NS)) == 1, "expected VERTEX-only triangles"
        idx = [int(x) for x in tri.find("c:p", NS).text.split()]
        nv = len(p) // 3
        name = re.sub(r"_lod\d+(_ncl\d+_\d+)?$", "", geom.get("id")[:-4])   # M_Glass_WindowFront_Max_lod0_ncl1_3 -> section
        out.append((name,
                    [conv(p[3 * i:3 * i + 3]) for i in range(nv)],
                    [conv(n[3 * i:3 * i + 3]) for i in range(nv)] if n else None,
                    [(t[2 * i], t[2 * i + 1]) for i in range(nv)] if t else None,
                    idx, skins.get(geom.get("id"), [-1] * nv)))
    return out


def write_dae(path, groups):
    """groups: list of (material, positions, normals, uvs, tri_indices)"""
    mats = sorted({g[0] for g in groups})
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">',
         '<asset><unit meter="1" name="meter"/><up_axis>Z_UP</up_axis></asset>', '<library_materials>']
    L += ['<material id="%s" name="%s"/>' % (m, m) for m in mats]
    L += ['</library_materials>', '<library_geometries>']
    for gi, (mat, pos, nrm, uv, idx) in enumerate(groups):
        nrm = nrm or [(0, 0, 1)] * len(pos)
        uv = uv or [(0, 0)] * len(pos)
        g = "g%d" % gi
        L.append('<geometry id="%s" name="%s"><mesh>' % (g, mat))
        for sid, data, st in (("pos", pos, 3), ("nrm", nrm, 3), ("uv", uv, 2)):
            flat = " ".join("%.6g" % c for v in data for c in v)
            L.append('<source id="%s-%s"><float_array id="%s-%s-a" count="%d">%s</float_array>'
                     '<technique_common><accessor source="#%s-%s-a" count="%d" stride="%d"/></technique_common></source>'
                     % (g, sid, g, sid, len(data) * st, flat, g, sid, len(data), st))
        L.append('<vertices id="%s-v"><input semantic="POSITION" source="#%s-pos"/></vertices>' % (g, g))
        L.append('<triangles count="%d" material="material%d">'
                 '<input semantic="VERTEX" source="#%s-v" offset="0"/>'
                 '<input semantic="NORMAL" source="#%s-nrm" offset="0"/>'
                 '<input semantic="TEXCOORD" source="#%s-uv" offset="0" set="0"/><p>%s</p></triangles>'
                 % (len(idx) // 3, mats.index(mat), g, g, g, " ".join(map(str, idx))))
        L.append('</mesh></geometry>')
    L += ['</library_geometries>', '</COLLADA>']
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def subset(sec, keep):
    """sections restricted to triangles whose 3 vertices all satisfy keep(vertex_part), reindexed"""
    name, pos, nrm, uv, idx, part = sec
    tris = [idx[i:i + 3] for i in range(0, len(idx), 3) if all(keep(part[j]) for j in idx[i:i + 3])]
    used = sorted({j for t in tris for j in t})
    if not used:
        return None
    remap = {j: k for k, j in enumerate(used)}
    return (name, [pos[j] for j in used], [nrm[j] for j in used] if nrm else None,
            [uv[j] for j in used] if uv else None, [remap[j] for t in tris for j in t])


def part_name(asset, prefix):
    s = asset.replace(".fbxsdk.dae", "")
    s = s[len(prefix):] if s.startswith(prefix) else s
    s = re.sub(r"_mesh$", "", s)
    return (s or "body").upper() if s != "mesh" else "BODY"


def main(raw_dir, geo_out, car, prefix):
    os.makedirs(geo_out, exist_ok=True)
    for f in sorted(os.listdir(raw_dir)):
        if not f.endswith(".fbxsdk.dae"):
            continue
        pname = "BODY" if f == prefix + "mesh.fbxsdk.dae" else part_name(f, prefix)
        secs = read_raw(os.path.join(raw_dir, f))
        write_dae(os.path.join(geo_out, "%s_%s_A.dae" % (car, pname)), [s[:5] for s in secs])
        parts = sorted({p for s in secs for p in s[5]})
        line = "%s_%s: %s" % (car, pname, ", ".join("%s %d" % (s[0], len(s[4]) // 3) for s in secs))
        if len(parts) > 1:
            for p in parts:
                sub = [x for x in (subset(s, lambda q, p=p: q == p) for s in secs) if x]
                write_dae(os.path.join(geo_out, "%s_%s_P%d_A.dae" % (car, pname, p)), sub)
                line += "\n    P%d: %d tris" % (p, sum(len(x[4]) // 3 for x in sub))
        print(line)


if __name__ == "__main__":
    main(*sys.argv[1:5])
