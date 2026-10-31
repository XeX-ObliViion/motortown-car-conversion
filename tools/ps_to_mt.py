"""Convert one ProStreet car (DAE parts exported by AssetDumper from the player's own install) into Motor Town mesh
descriptions: one JSON per Motor Town mesh (Body, Door_L, ..., Wheel_L/R), positions already in Motor Town's frame
(cm, X forward, Y right, Z up, origin on the ground at the car's centre), triangles grouped by material slot.
The editor-side script (build_meshes.py) turns each JSON into a StaticMesh. Nothing from the game is shipped.

usage: ps_to_mt.py <car_spec.json>"""
import json, math, re
import os
import sys
import xml.etree.ElementTree as ET

NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
PS_SCALE = 10.0 * 100.0      # DAE units are 1/10 m; Motor Town uses cm
WHEEL_MESH_SCALE = 0.6466   # 32.2 cm (ProStreet/MW tyre) / 49.8 cm (game wheel mesh, Zino_L bounds)
_COINCIDENT_CACHE = {}       # drop_coincident_with reference surfaces, by option


def load_dae(path):
    """-> list of (material_texture_hash, [((pos,nrm,uv) x3) ...])"""
    root = ET.parse(path).getroot()
    mats = [m.get("name", "").replace("TextureMTL-", "") for m in root.iterfind(".//c:material", NS)]
    if any(mats.count(m) > 1 or m.startswith("Material") for m in mats if not m.startswith("0x")):
        # modder cars (Remaster Diablo): generic names ("Material", repeated) -> key by the effect's texture hash
        fx = {e.get("id"): (re.findall(r"texture-(0x[0-9A-Fa-f]+)", ET.tostring(e, encoding="unicode")) or ["?"])[0]
              for e in root.iterfind(".//c:effect", NS)}
        mats = [fx.get(m.find("c:instance_effect", NS).get("url", "#")[1:], n) if not n.startswith("0x") else n
                for m, n in zip(root.iterfind(".//c:material", NS), mats)]
    out = []
    for geom in root.iterfind(".//c:geometry", NS):
        mesh = geom.find("c:mesh", NS)
        src = {s.get("id"): [float(x) for x in s.find("c:float_array", NS).text.split()] for s in mesh.iterfind("c:source", NS)}
        stride = {s.get("id"): int(s.find("c:technique_common/c:accessor", NS).get("stride")) for s in mesh.iterfind("c:source", NS)}
        vin = mesh.find("c:vertices", NS)
        pos_id = vin.find("c:input[@semantic='POSITION']", NS).get("source")[1:]
        for ti, tri in enumerate(mesh.iterfind("c:triangles", NS)):
            inputs = {i.get("semantic"): i for i in tri.findall("c:input", NS)}
            nstride = max(int(i.get("offset")) for i in inputs.values()) + 1
            idx = [int(x) for x in tri.find("c:p", NS).text.split()]
            uv_id = inputs["TEXCOORD"].get("source")[1:] if "TEXCOORD" in inputs else None
            n_id = inputs["NORMAL"].get("source")[1:] if "NORMAL" in inputs else None
            voff = int(inputs["VERTEX"].get("offset"))
            noff = int(inputs["NORMAL"].get("offset")) if n_id else None
            tris = []
            for k in range(0, len(idx), nstride * 3):
                corners = []
                for c in range(3):
                    base = k + c * nstride
                    vi = idx[base + voff]
                    p = src[pos_id][3 * vi:3 * vi + 3]
                    n = src[n_id][3 * idx[base + noff]:3 * idx[base + noff] + 3] if n_id else [0, 0, 1]
                    uv = src[uv_id][stride[uv_id] * vi:stride[uv_id] * vi + 2] if uv_id else [0, 0]
                    corners.append((p, n, uv))
                tris.append(corners)
            mat_index = int(tri.get("material", "material%d" % ti).replace("material", "") or ti)
            tex = mats[mat_index] if mat_index < len(mats) else "?"
            out.append((tex, tris))
    return out


def to_mt(p, mirror=False, offset=(0, 0, 0)):
    x, y, z = p[0] * PS_SCALE, -p[1] * PS_SCALE, p[2] * PS_SCALE
    if mirror:
        y = -y
    return [x + offset[0], y + offset[1], z + offset[2]]


def nrm_mt(n, mirror=False):
    x, y, z = n[0], -n[1], n[2]
    if mirror:
        y = -y
    return [x, y, z]


def zone_ymin(z_, zc):
    """inner |y| limit of an arch zone: cylinders [x, z, r, ymin] have one; box zones {"box": [x0, x1, z0, z1],
    "ymin": [[z_below, y], ...]} step it by height (deep arch liners low down, outboard of the trunk lid higher up)"""
    if not isinstance(z_, dict):
        return z_[3]
    for zb, y in z_["ymin"]:
        if zc < zb:
            return y
    return z_["ymin"][-1][1]


def zone_depth(z_, q, tol):
    """how far point q (MT cm) lies inside the zone (distance to its nearest edge), None when outside by > tol.
    A box's bottom face is not an edge (it only bounds the zone below the car)"""
    if isinstance(z_, dict):
        x0, x1, z0, z1 = z_["box"]
        d = min(q[0] - x0, x1 - q[0], z1 - q[2], abs(q[1]) - zone_ymin(z_, q[2]))
        return d if d >= -tol and q[2] >= z0 - tol else None
    rr = ((q[0] - z_[0]) ** 2 + (q[2] - z_[1]) ** 2) ** 0.5
    if abs(q[1]) < z_[3] - tol or rr > z_[2] + tol:
        return None
    return min(z_[2] - rr, abs(q[1]) - z_[3])


def load_src(geo, prefix, pname, lod, opts):
    """load_dae for a part, honouring per-part source options (Most Wanted pieces on a ProStreet car):
    "geo" (another export dir), "src_scale" (that game's DAE scale) and "xform" {"s": [sx,sy,sz], "t": [tx,ty,tz]}, a
    per-axis fit applied in Motor Town cm (MT = s * MT_src + t). Positions are mapped back into this spec's source units,
    so everything downstream (to_mt, x_range, drop_coincident_with) works unchanged."""
    g = os.path.expanduser(opts.get("geo", geo))
    path = os.path.join(g, "%s_%s_%s.dae" % (opts.get("prefix", prefix), pname, lod))
    if not os.path.exists(path):
        return None
    groups = load_dae(path)
    ss, xf = opts.get("src_scale"), opts.get("xform")
    if not ss and not xf:
        return groups
    ss = ss or PS_SCALE
    s, t = (xf or {}).get("s", [1, 1, 1]), (xf or {}).get("t", [0, 0, 0])
    rz = (xf or {}).get("rot_z")             # degrees about Z before the fit (side-exit exhaust tips)
    if rz:
        import math
        cz, sz_ = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    def mp(p):
        q = [p[0] * ss, -p[1] * ss, p[2] * ss]
        if rz:
            q = [q[0] * cz - q[1] * sz_, q[0] * sz_ + q[1] * cz, q[2]]
        q = [q[k] * s[k] + t[k] for k in range(3)]
        return (q[0] / PS_SCALE, -q[1] / PS_SCALE, q[2] / PS_SCALE)
    return [(tex, [tuple((mp(cn[0]),) + tuple(cn[1:]) for cn in tri) for tri in tris]) for tex, tris in groups]


def build(spec):
    global PS_SCALE
    PS_SCALE = spec.get("source_scale", 10.0 * 100.0)   # Most Wanted (2005/Rework) DAEs are 10x larger: 100
    geo = spec["geometry_dir"]
    prefix = spec["prefix"]
    lod = spec.get("lod", "A")
    tex_slot = spec["texture_slots"]          # texture hash -> slot name
    default_slot = spec.get("default_slot", "Trim")
    os.makedirs(spec["out_dir"], exist_ok=True)
    report = {}
    for mesh_name, mdef in spec["meshes"].items():
        slots = {}
        for part in mdef["parts"]:
            pname = part if isinstance(part, str) else part["part"]
            opts = {} if isinstance(part, str) else part
            src_groups = load_src(geo, prefix, pname, lod, opts)
            if src_groups is None:
                report.setdefault("missing", []).append(pname)
                continue
            mirror = opts.get("mirror", mdef.get("mirror", False))
            offset = opts.get("offset", mdef.get("offset", [0, 0, 0]))
            force = opts.get("slot", mdef.get("slot"))
            for gi, (tex, tris) in enumerate(src_groups):
                if "groups" in opts and gi not in opts["groups"]:   # pick source triangle groups by index (Elise mirror glass)
                    continue
                if gi in opts.get("skip_groups", []):                # ...and leave them out of the housing
                    continue
                slot = force or tex_slot.get(tex, default_slot)
                # overlay_textures {hash: {base, slot, parts, lift}}: MW draws some atlases additively over the paint
                # (993 RWB crest/RWB badging: black = no effect). Those groups render as the base slot (Paint) plus a
                # copy lifted along the normal into a masked overlay slot (alpha from luminance, see write_textures)
                ov = spec.get("overlay_textures", {}).get(tex)
                ovb = None
                if ov and not force and pname in ov.get("parts", [pname]):
                    slot = ov["base"]
                    ovb = slots.setdefault(ov["slot"], {"positions": [], "normals": [], "uvs": []})
                bucket = slots.setdefault(slot, {"positions": [], "normals": [], "uvs": []})
                nf = opts.get("normal_filter")   # keep only triangles whose average normal[axis] is within [min, max]
                dc = opts.get("drop_coincident_with")
                dc_key = json.dumps(dc, sort_keys=True) if dc else None
                if dc and dc_key not in _COINCIDENT_CACHE:
                    # e.g. a widebody shell: keep only where it differs from the stock body (vertices within tol cm of
                    # the reference part's vertices count as coincident)
                    tol = dc.get("tol", 1.0); g = set()
                    refs = [load_src(geo, dc["prefix"], rp, lod, dc) or []
                            for rp in dc.get("parts", [dc.get("part")])]       # one part or several (body + doors)
                    for ex_ in dc.get("also", []):                             # more references under other prefixes
                        refs += [load_src(geo, ex_["prefix"], rp, lod, ex_) or [] for rp in ex_["parts"]]
                    for _, rt in (x for r in refs for x in r):
                        for t in rt:
                            # sample the reference SURFACE (not just its vertices) every ~tol cm, so a shell lying on
                            # it with different tessellation still counts as coincident
                            a, b, c = (to_mt(cn[0]) for cn in t)
                            edge = max(sum((a[k] - b[k]) ** 2 for k in range(3)), sum((a[k] - c[k]) ** 2 for k in range(3)),
                                       sum((b[k] - c[k]) ** 2 for k in range(3))) ** 0.5
                            n = max(1, int(edge / tol) + 1)
                            for i in range(n + 1):
                                for j in range(n + 1 - i):
                                    u, v = i / n, j / n
                                    q = [a[k] + u * (b[k] - a[k]) + v * (c[k] - a[k]) for k in range(3)]
                                    g.add(tuple(round(x / tol) for x in q))
                    _COINCIDENT_CACHE[dc_key] = g   # kept out of the spec: the spec is written back to JSON
                xr = opts.get("x_range")
                # drop_on_surface {prefix, parts, tol, far}: drop triangles lying on or inside a reference surface
                # (signed distance along its normal < tol cm, within far cm of it). MW kit side pieces copy whole
                # body sides that sit on the ProStreet doors / fenders (flicker) or under them; only what stands proud
                # of the ProStreet body (sills, flares) is kept, plus anything away from it (where the stock skirt was)
                ds = opts.get("drop_on_surface")
                ds_key = "ds:" + json.dumps(ds, sort_keys=True) if ds else None
                if ds and ds_key not in _COINCIDENT_CACHE:
                    import numpy as np
                    from scipy.spatial import cKDTree
                    pts, nrm = [], []
                    for rp in ds["parts"]:
                        for _, rt in load_src(geo, ds["prefix"], rp, lod, ds) or []:
                            for t in rt:
                                a, b, c = (np.array(to_mt(cn[0])) for cn in t)
                                nv = np.mean([nrm_mt(cn[1]) for cn in t], 0)
                                nv /= np.linalg.norm(nv) + 1e-9
                                k = max(3, int(np.linalg.norm(np.cross(b - a, c - a)) / 2))
                                r = np.random.default_rng(len(pts)).random((k, 2)); m = r.sum(1) > 1; r[m] = 1 - r[m]
                                pts.append(a + r[:, :1] * (b - a) + r[:, 1:] * (c - a)); nrm.append(np.repeat(nv[None], k, 0))
                    P_, N_ = np.vstack(pts), np.vstack(nrm)
                    _COINCIDENT_CACHE[ds_key] = (cKDTree(P_), P_, N_)
                def clip_x(corners):
                    # x_clip: cut triangles exactly at the x_range planes (straight seams) instead of keeping whole
                    # triangles by centroid (saw-tooth edges with gaps into the body)
                    poly = [corners[0], corners[1], corners[2]]
                    for lim, keep_ge in ((xr[0], True), (xr[1], False)):
                        out_ = []
                        for k in range(len(poly)):
                            A, B_ = poly[k], poly[(k + 1) % len(poly)]
                            xa, xb = to_mt(A[0])[0], to_mt(B_[0])[0]
                            ina = xa >= lim if keep_ge else xa <= lim
                            inb = xb >= lim if keep_ge else xb <= lim
                            if ina:
                                out_.append(A)
                            if ina != inb and xa != xb:
                                t = (lim - xa) / (xb - xa)
                                mix = lambda a, b: [a[i] + t * (b[i] - a[i]) for i in range(len(a))]
                                out_.append((mix(A[0], B_[0]), mix(A[1], B_[1]), mix(A[2], B_[2])))
                        poly = out_
                        if len(poly) < 3:
                            return []
                    return [(poly[0], poly[k], poly[k + 1]) for k in range(1, len(poly) - 1)]
                if xr and opts.get("x_clip"):
                    tris = [sub for c in tris for sub in clip_x(c)]
                # slot_label {geo, src_scale, xform, prefix, pieces: {label: [parts]}, keep}: keep only the triangles
                # whose nearest labelled reference piece is `keep` (an MW kit shell split along the Carbon stock
                # bumper / skirt pieces: same model, so the split lands exactly on the original seams)
                sl_ = opts.get("slot_label")
                sl_key = "sl:" + json.dumps(sl_, sort_keys=True) if sl_ else None
                if sl_ and sl_key not in _COINCIDENT_CACHE:
                    import numpy as np
                    from scipy.spatial import cKDTree
                    pts, lab = [], []
                    for lb, rps in sl_["pieces"].items():
                        for rp in rps:
                            for _, rt in load_src(geo, sl_["prefix"], rp, lod, sl_) or []:
                                for t in rt:
                                    a, b, c = (np.array(to_mt(cn[0])) for cn in t)
                                    k = max(3, int(np.linalg.norm(np.cross(b - a, c - a)) / 2))
                                    r = np.random.default_rng(len(pts)).random((k, 2)); m = r.sum(1) > 1; r[m] = 1 - r[m]
                                    pts.append(a + r[:, :1] * (b - a) + r[:, 1:] * (c - a)); lab += [lb] * k
                    _COINCIDENT_CACHE[sl_key] = (cKDTree(np.vstack(pts)), np.array(lab))
                def sl_drop(m):
                    tree_, L_ = _COINCIDENT_CACHE[sl_key]
                    if m[0] < sl_.get("x_min", -1e9):
                        return False     # x_min: the labelling only applies ahead of x (Viper MW fender lamp surround)
                    return L_[tree_.query(m)[1]] != sl_["keep"]
                # keep_nearest {prefix, parts, replaced, proud, far, lamp, lamp_clear}: each piece of a kit shell is
                # given to the nearest ProStreet stock part. Kept only when that part is one the kit replaces (bumper /
                # skirt / hood), when it stands proud of the panel (lips, flares: > proud cm out), or when it is far
                # from every part (new shapes). Never over lamps unless lamp_clear cm in front. Cuts then follow the
                # ProStreet seams even where the MW model's surface drifts away from the ProStreet one
                kn = opts.get("keep_nearest")
                kn_key = "kn:" + json.dumps(kn, sort_keys=True) if kn else None
                if kn and kn_key not in _COINCIDENT_CACHE:
                    import numpy as np
                    from scipy.spatial import cKDTree
                    pts, nrm, lab = [], [], []
                    for pi_, rp in enumerate(kn["parts"]):
                        for _, rt in load_src(geo, kn["prefix"], rp, lod, kn) or []:
                            for t in rt:
                                a, b, c = (np.array(to_mt(cn[0])) for cn in t)
                                nv = np.mean([nrm_mt(cn[1]) for cn in t], 0); nv /= np.linalg.norm(nv) + 1e-9
                                k = max(3, int(np.linalg.norm(np.cross(b - a, c - a)) / 2))
                                r = np.random.default_rng(len(pts)).random((k, 2)); m = r.sum(1) > 1; r[m] = 1 - r[m]
                                pts.append(a + r[:, :1] * (b - a) + r[:, 1:] * (c - a)); nrm.append(np.repeat(nv[None], k, 0))
                                lab.append(np.full(k, pi_))
                    rep = np.array([p_ in kn["replaced"] for p_ in kn["parts"]])
                    lamp = np.array([bool(re.search(kn.get("lamp", "LIGHT|LAMP|GLASS"), p_)) for p_ in kn["parts"]])
                    P_ = np.vstack(pts)
                    _COINCIDENT_CACHE[kn_key] = (cKDTree(P_), P_, np.vstack(nrm), np.concatenate(lab), rep, lamp)
                def kn_drop(m):
                    tree_, P_, N_, L_, rep, lamp = _COINCIDENT_CACHE[kn_key]
                    dd, ii = tree_.query(m)
                    sd = sum((m[k] - P_[ii][k]) * N_[ii][k] for k in range(3))
                    if dd > kn.get("far", 6.0):
                        # away from every ProStreet panel: new shapes outside the car stay; the MW shell's inner
                        # walls / undersides (inside the car, behind the panels) go, or they show through seams
                        # keep_far_boxes [[x0,|y|0,z0,x1,|y|1,z1]]: inner surfaces kept there anyway (MW side-gill insides,
                        # Viper Kit 2: without them the stock fender's gill recess showed black through the openings)
                        if any(b_[0] <= m[0] <= b_[3] and b_[1] <= abs(m[1]) <= b_[4] and b_[2] <= m[2] <= b_[5]
                               for b_ in kn.get("keep_far_boxes", [])):
                            return False
                        return sd < 0 and not kn.get("keep_far")
                    li = L_[ii]
                    if rep[li]:
                        return False
                    if kn.get("edge") and dd * dd - sd * sd > kn["edge"] ** 2:
                        return False        # past that panel's edge: it does not cover this piece
                    tuck = kn.get("tuck", 1.0)
                    if -kn.get("far", 6.0) < sd < -tuck:
                        # just behind a ProStreet panel: hidden where the panel covers it, and it closes the seam
                        # where the two models' edges don't meet (no see-through gaps)
                        return False
                    if lamp[li]:
                        # only directly over the lamp (not beside it: bumper-mounted lamps would leave holes)
                        return sd < kn.get("lamp_clear", 8.0) and dd * dd - sd * sd <= 2.25
                    return sd < kn.get("proud", 2.5)
                # align_to_grille {regex, max}: move this part's left / right halves (exhaust tips) onto the centre of
                # the matching grille opening of the parts built so far (MW rear bumpers put their exhaust openings
                # elsewhere than the ProStreet bumper)
                ag = opts.get("align_to_grille")
                ag_off = {}
                if ag:
                    import numpy as np
                    allm = [[to_mt(cn[0]) for cn in t] for t in tris]
                    if allm:
                        A_ = np.array(allm).reshape(-1, 3)
                        gp = [np.array(b_["positions"]) for sl_x, b_ in slots.items()
                              if re.search(ag.get("regex", "GRILL"), sl_x) and b_["positions"]]
                        clusters = []
                        if gp:
                            G = np.vstack(gp)
                            G = G[(G[:, 0] < A_[:, 0].max() + 25) & (G[:, 2] < A_[:, 2].max() + 25)]
                            # grille openings: group points by 4 cm cells, flood-filled
                            cells = {}
                            for q in G:
                                cells.setdefault(tuple((q // 4).astype(int)), []).append(q)
                            seen = set()
                            for c0 in cells:
                                if c0 in seen:
                                    continue
                                stack, grp = [c0], []
                                seen.add(c0)
                                while stack:
                                    c = stack.pop(); grp += cells[c]
                                    for dx in (-1, 0, 1):
                                        for dy in (-1, 0, 1):
                                            for dz in (-1, 0, 1):
                                                nb = (c[0] + dx, c[1] + dy, c[2] + dz)
                                                if nb in cells and nb not in seen:
                                                    seen.add(nb); stack.append(nb)
                                if len(grp) >= 6:
                                    g_ = np.array(grp); clusters.append((g_.min(0) + g_.max(0)) / 2)
                        used = {}
                        for side in (-1, 1):
                            ex = A_[(A_[:, 1] * side) > 0]
                            if not len(ex) or not clusters:
                                continue
                            ec = (ex.min(0) + ex.max(0)) / 2
                            ci = int(np.argmin([abs(c[1] - ec[1]) + abs(c[2] - ec[2]) for c in clusters]))
                            gc = clusters[ci]
                            d_ = np.array([0.0, gc[1] - ec[1], gc[2] - ec[2]])     # sideways / height only
                            if np.linalg.norm(d_[1:]) > ag.get("max", 35.0):
                                continue
                            if ci in used:
                                # two tip sets for one opening: keep the one that moves least, hide the other
                                other = used[ci]
                                if np.linalg.norm(d_[1:]) < np.linalg.norm(ag_off[other][1:]):
                                    ag_off[other] = None; ag_off[side] = d_; used[ci] = side
                                else:
                                    ag_off[side] = None
                            else:
                                ag_off[side] = d_; used[ci] = side
                    report.setdefault("exhaust_aligned", {})[mesh_name] = {k: (None if v is None else [round(float(x), 1) for x in v]) for k, v in ag_off.items()}
                fg = opts.get("fill_gaps")
                fg_tree = None
                if fg:
                    # e.g. the ProStreet skirt under an MW skirt: keep only the strips the MW piece doesn't cover (the
                    # gap between a lower MW sill and the ProStreet door bottom); pieces behind or in front of it go
                    import numpy as np
                    from scipy.spatial import cKDTree
                    pts, nrm = [], []
                    for b_ in slots.values():
                        Pb = np.array(b_["positions"]).reshape(-1, 3, 3)
                        if not len(Pb):
                            continue
                        for t in Pb:
                            a, b, c = t
                            nv = np.cross(b - a, c - a); ar = np.linalg.norm(nv) / 2; nv /= np.linalg.norm(nv) + 1e-9
                            k = max(3, int(ar / 0.5))
                            r = np.random.default_rng(len(pts)).random((k, 2)); m = r.sum(1) > 1; r[m] = 1 - r[m]
                            pts.append(a + r[:, :1] * (b - a) + r[:, 1:] * (c - a)); nrm.append(np.repeat(nv[None], k, 0))
                    if pts:
                        P_fg, N_fg = np.vstack(pts), np.vstack(nrm)
                        fg_tree = cKDTree(P_fg)
                    def fg_drop(m):
                        if fg_tree is None:
                            return False
                        dd, ii = fg_tree.query(m)
                        if dd > fg.get("far", 8.0):
                            return bool(fg.get("drop_far"))    # bumpers: only fill holes, never stick out past the kit
                        sd = sum((m[k] - P_fg[ii][k]) * N_fg[ii][k] for k in range(3))
                        return dd * dd - sd * sd <= fg.get("edge", 1.0) ** 2
                    tris = [c for c in tris if not fg_drop([sum(to_mt(cn[0])[k] for cn in c) / 3 for k in range(3)])]
                zn = opts.get("zones")
                if zn:
                    # wheel-arch zones [[x, z, r, ymin], ...]: the body's arch / quarter areas live in the Fender slot,
                    # so a widebody fender replaces them as the panel's skin. Both sides are cut exactly on the zone
                    # surface (after splitting to ~4 cm), so the stock body and the skin meet edge to edge
                    def zf(c, z_):           # >0 inside the arch cylinder
                        m = to_mt(c[0], mirror, offset)
                        return z_[2] ** 2 - ((m[0] - z_[0]) ** 2 + (m[2] - z_[1]) ** 2)
                    def zg(c, z_, sg):       # >0 on the outer side of the ymin plane
                        m = to_mt(c[0], mirror, offset)
                        return sg * m[1] - zone_ymin(z_, m[2])
                    def mix(A, B_, t):
                        return tuple([[A[j][i] + t * (B_[j][i] - A[j][i]) for i in range(len(A[j]))] for j in range(3)])
                    def clipf(poly, fn, keep_pos):
                        out_ = []
                        for k in range(len(poly)):
                            A, B_ = poly[k], poly[(k + 1) % len(poly)]
                            fa, fb = fn(A), fn(B_)
                            ia, ib = (fa >= 0) == keep_pos, (fb >= 0) == keep_pos
                            if ia:
                                out_.append(A)
                            if ia != ib and fa != fb:
                                out_.append(mix(A, B_, fa / (fa - fb)))
                        return out_ if len(out_) >= 3 else []
                    def split(c, depth=4):
                        ms = [to_mt(cn[0], mirror, offset) for cn in c]
                        near = any(zone_depth(z_, ms[0], 60) is not None if isinstance(z_, dict) else
                                   abs(((ms[0][0] - z_[0]) ** 2 + (ms[0][2] - z_[1]) ** 2) ** 0.5 - z_[2]) < 60 for z_ in zn["list"])
                        edge = max(sum((ms[a][k] - ms[b][k]) ** 2 for k in range(3)) ** 0.5 for a, b in ((0, 1), (1, 2), (0, 2)))
                        if depth == 0 or edge < 4.0 or not near:
                            return [c]
                        a, b, cc = c; ab, bc, ca = mix(a, b, .5), mix(b, cc, .5), mix(cc, a, .5)
                        return [x for t in ((a, ab, ca), (ab, b, bc), (ca, bc, cc), (ab, bc, ca)) for x in split(t, depth - 1)]
                    new_tris = []
                    xr_z = zn.get("x_range")          # zones stop at the bumper lines: bumpers stay whole with any fender
                    def cons(z_, sg):
                        if isinstance(z_, dict):     # box zone: x / z planes plus the (stepped) ymin
                            x0, x1, z0, z1 = z_["box"]
                            fs = [lambda c_: to_mt(c_[0], mirror, offset)[0] - x0, lambda c_: x1 - to_mt(c_[0], mirror, offset)[0],
                                  lambda c_: to_mt(c_[0], mirror, offset)[2] - z0, lambda c_: z1 - to_mt(c_[0], mirror, offset)[2],
                                  lambda c_, z_=z_, sg=sg: zg(c_, z_, sg)]
                        else:
                            fs = [lambda c_, z_=z_: zf(c_, z_), lambda c_, z_=z_, sg=sg: zg(c_, z_, sg)]
                        if xr_z:
                            fs += [lambda c_: to_mt(c_[0], mirror, offset)[0] - xr_z[0],
                                   lambda c_: xr_z[1] - to_mt(c_[0], mirror, offset)[0]]
                        return fs
                    for c in tris:
                        # except [[x0,|y|0,z0,x1,|y|1,z1]]: triangles centred there are left as they are (Viper MW Kit 2
                        # skirt: its side gill sits inside the front fender zone, cut away it left the stock recess showing)
                        cm_ = [sum(to_mt(cn[0], mirror, offset)[k] for cn in c) / 3 for k in range(3)]
                        if any(b_[0] <= cm_[0] <= b_[3] and b_[1] <= abs(cm_[1]) <= b_[4] and b_[2] <= cm_[2] <= b_[5]
                               for b_ in zn.get("except", [])):
                            new_tris.append(c)
                            continue
                        for sub in split(c):
                            sg = 1 if sum(to_mt(cn[0], mirror, offset)[1] for cn in sub) >= 0 else -1
                            if zn["mode"] == "keep":
                                pieces = []
                                for z_ in zn["list"]:
                                    pp_ = list(sub)
                                    for f_ in cons(z_, sg):
                                        pp_ = clipf(pp_, f_, True) if pp_ else []
                                    if pp_:
                                        pieces.append(pp_)
                            else:
                                pieces = [list(sub)]
                                for z_ in zn["list"]:
                                    nxt = []
                                    for pp_ in pieces:
                                        inside = pp_
                                        for f_ in cons(z_, sg):     # outside = not(f1) | (f1 & not f2) | ...
                                            out_ = clipf(inside, f_, False) if inside else []
                                            if out_:
                                                nxt.append(out_)
                                            inside = clipf(inside, f_, True) if inside else []
                                    pieces = nxt
                            for pp_ in pieces:
                                new_tris += [(pp_[0], pp_[k], pp_[k + 1]) for k in range(1, len(pp_) - 1)]
                    tris = new_tris
                bl = opts.get("blend")
                bl_tree = None
                if bl:
                    # morph the skin onto the reference surface near the zone edge (weight 1 at the edge, 0 at `band` cm
                    # inside), so the widebody's panel meets the stock panel without a step
                    import numpy as np
                    from scipy.spatial import cKDTree
                    bkey = "bl:" + json.dumps({k: v for k, v in bl.items() if k != "band"}, sort_keys=True)
                    if bkey not in _COINCIDENT_CACHE:
                        pts = []
                        for rp in bl["parts"]:
                            for _, rt in load_src(geo, bl["prefix"], rp, lod, bl) or []:
                                for t in rt:
                                    a, b, c = (np.array(to_mt(cn[0])) for cn in t)
                                    k = max(3, int(np.linalg.norm(np.cross(b - a, c - a)) / 2 / 0.25))
                                    r = np.random.default_rng(len(pts)).random((k, 2)); m = r.sum(1) > 1; r[m] = 1 - r[m]
                                    pts.append(a + r[:, :1] * (b - a) + r[:, 1:] * (c - a))
                        P_bl = np.vstack(pts)
                        _COINCIDENT_CACHE[bkey] = (cKDTree(P_bl), P_bl)
                    bl_tree, P_bl = _COINCIDENT_CACHE[bkey]
                    def blend_q(q):
                        if bl.get("snap"):
                            # snap: any kit vertex within `snap` cm of the stock surface goes onto it, so the skin's
                            # edges sit flush (Viper MW Kit 3: fender skin ~1-2 cm proud round the headlamps, see-through)
                            dd, ii = bl_tree.query(q)
                            if dd <= bl["snap"]:
                                return list(P_bl[ii])
                        ds_ = [d_ for d_ in (zone_depth(z_, q, 1) for z_ in bl["zones"]) if d_ is not None]
                        din = min(ds_) if ds_ else None
                        if din is None:
                            return q
                        w = max(0.0, 1.0 - max(din, 0.0) / bl.get("band", 15.0))
                        if w <= 0:
                            return q
                        dd, ii = bl_tree.query(q)
                        if dd > bl.get("max", 10.0):
                            return q
                        return [q[k] + w * (P_bl[ii][k] - q[k]) for k in range(3)]
                rd = opts.get("refine_drop")
                if rd and (dc or ds or kn or sl_):
                    # triangles that are partly on a reference surface are split (up to rd levels, down to ~1.5 cm)
                    # before the drop tests below, so trims follow the reference panel's edge instead of leaving
                    # notches and gaps along whole source triangles
                    def drop_pt(q):
                        m = to_mt(q)
                        if sl_ and sl_drop(m):
                            return True
                        if kn and slot not in kn.get("keep_slots", []) and kn_drop(m):
                            return True
                        if dc:
                            tl = dc.get("tol", 1.0); k = tuple(round(v / tl) for v in m)
                            if any((k[0] + a, k[1] + b, k[2] + c) in _COINCIDENT_CACHE[dc_key]
                                   for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)):
                                return True
                        if ds:
                            tree_, P_, N_ = _COINCIDENT_CACHE[ds_key]
                            dd, ii = tree_.query(m)
                            if dd <= ds.get("far", 6.0):
                                sd = sum((m[k] - P_[ii][k]) * N_[ii][k] for k in range(3))
                                # only when the point is over/under the panel itself (not past its edge)
                                if sd < ds.get("tol", 2.5) and dd * dd - sd * sd <= ds.get("edge", 1.2) ** 2:
                                    return True
                        return False
                    def refine(c, depth):
                        pts = [cn[0] for cn in c] + [[sum(cn[0][k] for cn in c) / 3 for k in range(3)]]
                        st = [drop_pt(q) for q in pts]
                        ms = [to_mt(cn[0]) for cn in c]
                        edge = max(sum((ms[a][k] - ms[b][k]) ** 2 for k in range(3)) ** 0.5 for a, b in ((0, 1), (1, 2), (0, 2)))
                        if depth == 0 or all(st) or not any(st) or edge < 1.5:
                            return [c]
                        mid = lambda A, B_: tuple([[(A[j][i] + B_[j][i]) / 2 for i in range(len(A[j]))] for j in range(3)])
                        a, b, cc = c; ab, bc, ca = mid(a, b), mid(b, cc), mid(cc, a)
                        return [x for t in ((a, ab, ca), (ab, b, bc), (ca, bc, cc), (ab, bc, ca)) for x in refine(t, depth - 1)]
                    tris = [sub for c in tris for sub in refine(c, rd)]
                for corners in tris:
                    if sl_ and sl_drop([sum(to_mt(cn[0])[k] for cn in corners) / 3 for k in range(3)]):
                        continue
                    # keep_slots: e.g. MW mesh grilles sit recessed behind the ProStreet surface, inside the car, and
                    # were trimmed as inner shell (Viper Kit 4: black bumper openings)
                    if kn and slot not in kn.get("keep_slots", []) and kn_drop([sum(to_mt(cn[0])[k] for cn in corners) / 3 for k in range(3)]):
                        continue
                    # skip_boxes / only_boxes [[x0,|y|0,z0,x1,|y|1,z1]] (both sides): leave out, or keep only, triangles
                    # centred there (Viper MW Kit 4: the stock fender round the headlamps, where the MW shell sat proud)
                    if opts.get("skip_boxes") or opts.get("only_boxes"):
                        cm_ = [sum(to_mt(cn[0], mirror, offset)[k] for cn in corners) / 3 for k in range(3)]
                        inb = lambda bl_: any(b_[0] <= cm_[0] <= b_[3] and b_[1] <= abs(cm_[1]) <= b_[4] and b_[2] <= cm_[2] <= b_[5] for b_ in bl_)
                        if inb(opts.get("skip_boxes", [])) or (opts.get("only_boxes") and not inb(opts["only_boxes"])):
                            continue
                    if "z_max" in opts and sum(to_mt(cn[0])[2] for cn in corners) / 3 > opts["z_max"]:
                        continue            # e.g. side skirts: nothing above the sills / arch tops

                    if ds:
                        tree_, P_, N_ = _COINCIDENT_CACHE[ds_key]
                        cm = [sum(to_mt(cn[0])[k] for cn in corners) / 3 for k in range(3)]
                        dd, ii = tree_.query(cm)
                        # keep_boxes [[x0,|y|0,z0,x1,|y|1,z1]]: not dropped there (mesh `lift` raises it over the door)
                        kb_ = any(b_[0] <= cm[0] <= b_[3] and b_[1] <= abs(cm[1]) <= b_[4] and b_[2] <= cm[2] <= b_[5]
                                  for b_ in ds.get("keep_boxes", []))
                        if dd <= ds.get("far", 6.0) and not kb_:
                            sd = sum((cm[k] - P_[ii][k]) * N_[ii][k] for k in range(3))
                            if sd < ds.get("tol", 2.5) and dd * dd - sd * sd <= ds.get("edge", 1.2) ** 2:
                                continue
                    if dc:
                        tol = dc.get("tol", 1.0)
                        def near(q):
                            k = tuple(round(v / tol) for v in to_mt(q))
                            return any((k[0] + a, k[1] + b, k[2] + c) in _COINCIDENT_CACHE[dc_key]
                                       for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1))
                        # keep_boxes: [x0,y0,z0,x1,y1,z1] regions where the shell is kept even when it lies on the
                        # reference (Challenger: the strip behind the door bottom the stock skirt fills, the widebody
                        # skirt doesn't)
                        cm = [sum(to_mt(cn[0])[k] for cn in corners) / 3 for k in range(3)]
                        kept = any(all(bx[k] <= cm[k] <= bx[k + 3] for k in range(3)) for bx in dc.get("keep_boxes", []))
                        coinc = all(near(cn[0]) for cn in corners)
                        if dc.get("keep_only"):     # the inverse: keep only what lies on the reference (MW doors cut
                            if not coinc:           # out of the one-piece MW body along the ProStreet door panels)
                                continue
                        elif not kept and coinc:
                            continue
                    if xr and not opts.get("x_clip"):
                        cx = sum(to_mt(cn[0])[0] for cn in corners) / 3
                        if not (xr[0] <= cx <= xr[1]):
                            continue
                    if nf:
                        nv = sum(nrm_mt(cn[1], mirror)[nf.get("axis", 0)] for cn in corners) / 3
                        if nv < nf.get("min", -9) or nv > nf.get("max", 9):
                            continue
                    if ag_off and ag_off.get(1 if sum(to_mt(cn[0])[1] for cn in corners) > 0 else -1, 0) is None:
                        continue            # a duplicate exhaust set (its opening is taken)
                    order = (0, 2, 1) if not mirror else (0, 1, 2)   # Y flip changes winding; mirroring flips it back
                    sc = opts.get("scale")   # per-axis scale about the part origin (+offset), e.g. wider tyres [1, 1.45, 1]
                    for c in order:
                        p, n, uv = corners[c]
                        q = to_mt(p, mirror, offset)
                        if bl_tree is not None:
                            q = blend_q(q)
                        if ag_off:
                            cy = sum(to_mt(cn[0])[1] for cn in corners)
                            o_ = ag_off.get(1 if cy > 0 else -1)
                            if o_ is not None:
                                q = [q[k] + float(o_[k]) for k in range(3)]
                        if sc:
                            q = [(q[k] - offset[k]) * sc[k] + offset[k] for k in range(3)]
                        bucket["positions"].append(q)
                        bucket["normals"].append(nrm_mt(n, mirror))
                        bucket["uvs"].append([uv[0], uv[1]])
                        if ovb is not None:
                            nn = nrm_mt(n, mirror); lf = ov.get("lift", 0.05)
                            ovb["positions"].append([q[k] + lf * nn[k] for k in range(3)])
                            ovb["normals"].append(nn); ovb["uvs"].append([uv[0], uv[1]])
        for a, b in mdef.get("slot_rename", {}).items():   # e.g. the tyre ring -> a dark rubber material
            if a in slots:
                src = slots.pop(a); dst = slots.setdefault(b, {"positions": [], "normals": [], "uvs": []})
                for k in dst: dst[k] += src[k]
        for k in mdef.get("drop_slots", []):   # e.g. the tyre on a wheel: Motor Town draws its own tyre around the rim
            slots.pop(k, None)
        for box in mdef.get("drop_boxes", []):   # remove source parts the game supplies itself, e.g. its own room mirror
            lo, hi = box[:3], box[3:]
            for b in slots.values():
                keep = {k: [] for k in b}
                for i in range(0, len(b["positions"]), 3):
                    if not all(all(lo[a] <= b["positions"][i + j][a] <= hi[a] for a in range(3)) for j in range(3)):
                        for k in b:
                            keep[k] += b[k][i:i + 3]
                b.update(keep)
        for db in mdef.get("drop_uv_boxes", []):
            # remove triangles of a slot whose UVs all fall in a box, e.g. a source model's own 3D gauge needles that
            # sample a colour swatch of the dial atlas (993 RWB: the "ghost" needles behind our live ones)
            b = slots.get(db["slot"])
            if not b:
                continue
            u0, v0, u1, v1 = db["uv"]
            keep = {k: [] for k in b}
            n0 = len(b["positions"]) // 3
            for i in range(0, len(b["positions"]), 3):
                if not all(u0 <= b["uvs"][i + j][0] <= u1 and v0 <= b["uvs"][i + j][1] <= v1 for j in range(3)):
                    for k in b:
                        keep[k] += b[k][i:i + 3]
            b.update(keep)
            print("drop_uv_boxes %s %s: %d -> %d tris" % (mesh_name, db["slot"], n0, len(b["positions"]) // 3))
        kb = mdef.get("keep_boxes")
        if kb:   # keep only triangles fully inside one of the boxes (MW doors carved out of a one-piece body)
            for b in slots.values():
                keep = {k: [] for k in b}
                for i in range(0, len(b["positions"]), 3):
                    if any(all(all(bx[a] <= b["positions"][i + j][a] <= bx[a + 3] for a in range(3)) for j in range(3))
                           for bx in kb):
                        for k in b:
                            keep[k] += b[k][i:i + 3]
                b.update(keep)
            for k in [k for k, b in slots.items() if not b["positions"]]:
                slots.pop(k)
        es = mdef.get("edge_snap")
        if es and slots:
            # edge_snap {prefix, parts, dist}: the kit skin's OPEN edges (edges used by one triangle) within dist cm of
            # those stock parts move onto them, so the panel closes against e.g. the headlamp instead of leaving a
            # see-through gap (Viper MW fenders: up to 6 cm off the lamps). Interior vertices stay put (no crumpling)
            import numpy as np
            from scipy.spatial import cKDTree
            R = np.vstack([np.array([to_mt(cn[0]) for cn in t]) for rp in es["parts"]
                           for _, rt in (load_src(geo, es["prefix"], rp, lod, {}) or []) for t in rt])
            # sample the reference surface densely so edge vertices land on the surface, not just its vertices
            Rt = R.reshape(-1, 3, 3); smp = []
            for t in Rt:
                k = max(3, int(np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])) / 0.5))
                r = np.random.default_rng(len(smp)).random((k, 2)); m = r.sum(1) > 1; r[m] = 1 - r[m]
                smp.append(t[0] + r[:, :1] * (t[1] - t[0]) + r[:, 1:] * (t[2] - t[0]))
            Rs = np.vstack(smp); rtree = cKDTree(Rs)
            key = lambda v: (round(v[0], 2), round(v[1], 2), round(v[2], 2))
            cnt = {}
            for b_ in slots.values():
                P_ = b_["positions"]
                for i in range(0, len(P_), 3):
                    for a_, c_ in ((0, 1), (1, 2), (2, 0)):
                        e_ = tuple(sorted((key(P_[i + a_]), key(P_[i + c_]))))
                        cnt[e_] = cnt.get(e_, 0) + 1
            edge_v = {v for e_, n_ in cnt.items() if n_ == 1 for v in e_}
            moved = {}
            for v in edge_v:
                d_, j_ = rtree.query(v)
                if d_ <= es.get("dist", 7.0):
                    moved[v] = Rs[j_].tolist()
            for b_ in slots.values():
                b_["positions"] = [moved.get(key(q), q) for q in b_["positions"]]
            report.setdefault("edge_snap", {})[mesh_name] = len(moved)
        lf = mdef.get("lift")
        if lf and slots:
            # lift {prefix, parts, off, box [x0,|y|0,z0,x1,|y|1,z1], edge, depth}: kit vertices in box lying under (or
            # within off cm of) the stock surface move out to off cm above it. Supra MW Kit 5: the side scoop dips under
            # the stock door, which showed through a hole with flickering edges; lifted it reads as a shallow scoop
            import numpy as np
            from scipy.spatial import cKDTree
            smp, nrm = [], []
            for rp in lf["parts"]:
                for _, rt in load_src(geo, lf["prefix"], rp, lod, {}) or []:
                    for t in rt:
                        T_ = np.array([to_mt(cn[0]) for cn in t])
                        n_ = np.cross(T_[1] - T_[0], T_[2] - T_[0]); a_ = np.linalg.norm(n_); n_ /= a_ + 1e-9
                        if np.dot(n_, np.mean([nrm_mt(cn[1]) for cn in t], 0)) < 0:
                            n_ = -n_
                        k = max(3, int(a_ / 0.5))
                        r = np.random.default_rng(len(smp)).random((k, 2)); m = r.sum(1) > 1; r[m] = 1 - r[m]
                        smp.append(T_[0] + r[:, :1] * (T_[1] - T_[0]) + r[:, 1:] * (T_[2] - T_[0])); nrm.append(np.repeat(n_[None], k, 0))
            Rs, Rn = np.vstack(smp), np.vstack(nrm); rtree = cKDTree(Rs)
            bx, off, edge = lf["box"], lf.get("off", 0.6), lf.get("edge", 2.0)
            n_l = 0
            for b_ in slots.values():
                P_ = np.array(b_["positions"], float)
                if not len(P_):
                    continue
                inb = ((P_[:, 0] >= bx[0]) & (P_[:, 0] <= bx[3]) & (np.abs(P_[:, 1]) >= bx[1]) & (np.abs(P_[:, 1]) <= bx[4])
                       & (P_[:, 2] >= bx[2]) & (P_[:, 2] <= bx[5]))
                idx = np.nonzero(inb)[0]
                if not len(idx):
                    continue
                dd, jj = rtree.query(P_[idx])
                sd = ((P_[idx] - Rs[jj]) * Rn[jj]).sum(1)
                ok = (sd < off) & (dd * dd - sd * sd <= edge * edge) & (sd > -lf.get("depth", 15.0))
                P_[idx[ok]] += (off - sd[ok])[:, None] * Rn[jj[ok]]
                n_l += int(ok.sum())
                b_["positions"] = P_.tolist()
            report.setdefault("lift", {})[mesh_name] = n_l
        if mdef.get("double_sided"):
            # kit panels are single-sided shells: seen from behind (low angles, inside the arches) they vanish. Add a
            # reversed copy of every triangle (the culled side shows the panel instead of a hole)
            for b in slots.values():
                n_ = len(b["positions"])
                for i in range(0, n_, 3):
                    for j in (0, 2, 1):
                        b["positions"].append(list(b["positions"][i + j]))
                        b["normals"].append([-v for v in b["normals"][i + j]])
                        b["uvs"].append(list(b["uvs"][i + j]))
        mi = mdef.get("min_island")
        if mi:
            # trimmed kit shells (x_range / drop_coincident_with / drop_on_surface) leave loose fragments: teeth along
            # the cuts and slivers under the sills. Drop connected pieces (shared vertex positions, all slots) whose
            # total area is under min_island cm2
            tri = [(sl, i) for sl, b in slots.items() for i in range(0, len(b["positions"]), 3)]
            parent = list(range(len(tri)))
            def find(a):
                while parent[a] != a:
                    parent[a] = parent[parent[a]]; a = parent[a]
                return a
            first = {}
            area = []
            for ti, (sl, i) in enumerate(tri):
                ps = slots[sl]["positions"][i:i + 3]
                u = [ps[1][k] - ps[0][k] for k in range(3)]; v = [ps[2][k] - ps[0][k] for k in range(3)]
                cx = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
                area.append(0.5 * sum(c * c for c in cx) ** 0.5)
                for q in ps:
                    key = tuple(round(c * 20) for c in q)
                    if key in first:
                        ra, rb = find(ti), find(first[key])
                        if ra != rb:
                            parent[ra] = rb
                    else:
                        first[key] = ti
            tot = {}
            for ti in range(len(tri)):
                r = find(ti); tot[r] = tot.get(r, 0.0) + area[ti]
            drop = {ti for ti in range(len(tri)) if tot[find(ti)] < mi}
            if drop:
                for sl, b in slots.items():
                    keep = {k: [] for k in b}
                    for ti, (s2, i) in enumerate(tri):
                        if s2 == sl and ti not in drop:
                            for k in b:
                                keep[k] += b[k][i:i + 3]
                    b.update(keep)
                for k in [k for k, b in slots.items() if not b["positions"]]:
                    slots.pop(k)
                report.setdefault("islands_dropped", {})[mesh_name] = len(drop)
        rs = mdef.get("radius_slot")
        if rs:
            # tyre part of a wheel model that shares the rim's texture: triangles beyond the rim lip go to a rubber slot
            dst = slots.setdefault(rs["slot"], {"positions": [], "normals": [], "uvs": []})
            for sl, b in list(slots.items()):
                if sl == rs["slot"] or ("from" in rs and sl not in rs["from"]):
                    continue
                keep = {k: [] for k in b}
                for i in range(0, len(b["positions"]), 3):
                    t = b["positions"][i:i + 3]
                    out = sum((q[0] ** 2 + q[2] ** 2) ** 0.5 for q in t) / 3 > rs["r"]
                    for k in b:
                        (dst[k] if out else keep[k]).extend(b[k][i:i + 3])
                b.update(keep)
            for k in [k for k, b in slots.items() if not b["positions"]]:
                slots.pop(k)
        mr = mdef.get("max_radius")
        if mr:
            # rim-only wheels: drop triangles beyond the rim lip (a car wheel model that carries its own tyre; the
            # game draws its tyre itself, so ours showed as a second, white tyre in the garage preview)
            for b in slots.values():
                keep = {k: [] for k in b}
                for i in range(0, len(b["positions"]), 3):
                    t = b["positions"][i:i + 3]
                    if sum((q[0] ** 2 + q[2] ** 2) ** 0.5 for q in t) / 3 <= mr:
                        for k in b:
                            keep[k] += b[k][i:i + 3]
                b.update(keep)
            for k in [k for k, b in slots.items() if not b["positions"]]:
                slots.pop(k)
        if mesh_name.startswith("Wheel_"):
            # Motor Town wheel components are scaled down (game rims are modelled ~50 cm in radius; Zino 0.61, Cora
            # 0.665): ours use WHEEL_MESH_SCALE so the game's rims fit at ~32 cm, and our own wheels are pre-enlarged
            # by its inverse so they keep their real size
            k = 1.0 / spec.get("wheel_mesh_scale", WHEEL_MESH_SCALE)
            for b in slots.values():
                b["positions"] = [[v * k for v in p] for p in b["positions"]]
        if mdef.get("recenter"):
            # e.g. a Magis-style SideMirror: the mesh lives in its component's local space; the component goes to
            # this centre (left) and to its Y-mirror with scale Y -1 (right), see make_mt_assets mirror_components
            allp = [p for b in slots.values() for p in b["positions"]]
            if allp:
                c = [sum(p[k] for p in allp) / len(allp) for k in range(3)]
                for b in slots.values():
                    b["positions"] = [[p[0] - c[0], p[1] - c[1], p[2] - c[2]] for p in b["positions"]]
                spec.setdefault("recentered", {})[mesh_name] = [round(v, 2) for v in c]
        sn = mdef.get("smooth_normals")
        if sn:
            # flat-shaded source meshes (Diablo rim lip: every triangle edge showed as a grid line): per vertex, average
            # the face normals of all triangles sharing its position within `sn` degrees of its own face
            import math
            cos_ = math.cos(math.radians(float(sn)))
            for b_ in slots.values():
                P_ = b_["positions"]; fn = []
                for i in range(0, len(P_), 3):
                    e1 = [P_[i + 1][k] - P_[i][k] for k in range(3)]; e2 = [P_[i + 2][k] - P_[i][k] for k in range(3)]
                    n_ = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
                    l_ = math.sqrt(sum(v * v for v in n_)) or 1.0
                    # keep the source winding's side: flip to agree with the stored vertex normals
                    s_ = 1.0 if sum(n_[k] * sum(b_["normals"][i + j][k] for j in range(3)) for k in range(3)) >= 0 else -1.0
                    fn.append([s_ * v / l_ for v in n_])
                groups = {}
                for i, q in enumerate(P_):
                    groups.setdefault(tuple(round(v, 2) for v in q), []).append(i)
                out = []
                for i, q in enumerate(P_):
                    f0 = fn[i // 3]; acc = [0.0, 0.0, 0.0]
                    for j in groups[tuple(round(v, 2) for v in q)]:
                        f1 = fn[j // 3]
                        if sum(f0[k] * f1[k] for k in range(3)) >= cos_:
                            acc = [acc[k] + f1[k] for k in range(3)]
                    l_ = math.sqrt(sum(v * v for v in acc)) or 1.0
                    out.append([v / l_ for v in acc])
                b_["normals"] = out
        pu = mdef.get("planar_uv")
        if pu is not None:
            # e.g. side-mirror glass: the game stretches the live reflection over UV 0..1, so project the glass flat
            # (u along Y, 1 at the -Y edge; v along Z with image top = v 1 in our UV convention, see texture rows)
            allp = [p for b in slots.values() for p in b["positions"]]
            ya, yb = min(p[1] for p in allp), max(p[1] for p in allp)
            za, zb = min(p[2] for p in allp), max(p[2] for p in allp)
            for b in slots.values():
                b["uvs"] = [[(yb - p[1]) / (yb - ya) if not pu.get("flip_u") else (p[1] - ya) / (yb - ya),
                             (p[2] - za) / (zb - za)] for p in b["positions"]]
        cr = mdef.get("counter_rotate")
        if cr:
            # the component is rotated (UE rotator, to aim the mirror capture) but the glass must stay where the
            # source model has it: bake the inverse rotation into the (recentred) mesh. With "mirror_frame" the
            # component also has scale Y -1 (right mirror sharing the left glass): v = S R^-1 S g
            import math
            pch, yaw = math.radians(cr["rot"][0]), math.radians(cr["rot"][1])
            def inv(v):
                x, y, z = v
                x, y = x * math.cos(-yaw) - y * math.sin(-yaw), x * math.sin(-yaw) + y * math.cos(-yaw)
                x, z = x * math.cos(-pch) - z * math.sin(-pch), x * math.sin(-pch) + z * math.cos(-pch)
                return [x, y, z]
            mf = cr.get("mirror_frame")
            S = (lambda v: [v[0], -v[1], v[2]]) if mf else (lambda v: v)
            for b in slots.values():
                b["positions"] = [S(inv(S(q))) for q in b["positions"]]
                b["normals"] = [S(inv(S(q))) for q in b["normals"]]
                # (S R^-1 S is a proper rotation, det +1: the winding stays)
        for sp in mdef.get("uv_split", []):
            # triangles of one slot whose UVs fall in a texture box (u0, row0, u1, row1; row = 1 - v) get their own
            # slot, e.g. the instrument faces so they can glow
            if sp["from"] not in slots:
                continue
            src = slots[sp["from"]]; keep = {k: [] for k in src}; take = slots.setdefault(sp["to"], {k: [] for k in src})
            u0, r0, u1, r1 = sp["box"]
            for i in range(0, len(src["uvs"]), 3):
                inside = all(u0 <= src["uvs"][i + j][0] <= u1 and r0 <= 1 - src["uvs"][i + j][1] <= r1 for j in range(3))
                dst = take if inside else keep
                for k in src:
                    dst[k] += src[k][i:i + 3]
            slots[sp["from"]] = keep
        for et in mdef.get("extra_triangles", []):
            # generated geometry, e.g. flush glass covers over lamp recesses (car-space triangles, outward winding)
            b = slots.setdefault(et["slot"], {"positions": [], "normals": [], "uvs": []})
            P = et["positions"]
            for i in range(0, len(P), 3):
                a, c, d_ = P[i], P[i + 1], P[i + 2]
                u = [c[k] - a[k] for k in range(3)]; w = [d_[k] - a[k] for k in range(3)]
                nn = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
                ln = sum(x * x for x in nn) ** 0.5 or 1
                for q in (a, c, d_):
                    b["positions"].append(list(q)); b["normals"].append([x / ln for x in nn]); b["uvs"].append([0.5, 0.5])
        sts = spec.get("stripes") or []
        for st in (sts if isinstance(sts, list) else [sts]):
            # painted stripes (a vinyl in ProStreet): cut the paint triangles along planes (axis 1 = y bands for
            # bonnet/roof stripes, axis 2 = z bands for side stripes) and move the parts inside a band (and inside
            # x_range) to a second paint slot (-> Body_02). Faces are filtered by |normal y| (top: max_abs_ny,
            # side: min_abs_ny).
            if st["from"] not in slots:
                continue
            if st.get("meshes") and not any(mesh_name.startswith(m) for m in st["meshes"]):
                continue                     # e.g. hood/trunk stripes only: Body + Aero_Bonnet, not the bumpers
            ax = st.get("axis", 1)
            src = slots[st["from"]]; keep = {k: [] for k in src}
            dst = slots.setdefault(st["to"], {k: [] for k in src})
            cuts = sorted({v for b_ in st["bands"] for v in b_})
            xr = st.get("x_range", [-1e9, 1e9])
            prof = sorted(st.get("profile") or [[0, 0]])
            def val(q, prof=prof, ax=ax):
                # band coordinate: q[ax] minus the profile offset at q's x (profile [[x, dz], ...], linear in between,
                # held past the ends) so a side stripe can follow a beltline that drops toward the front
                x = q[0]
                if x <= prof[0][0]:
                    dz = prof[0][1]
                elif x >= prof[-1][0]:
                    dz = prof[-1][1]
                else:
                    j = next(k for k in range(1, len(prof)) if x <= prof[k][0])
                    t = (x - prof[j - 1][0]) / ((prof[j][0] - prof[j - 1][0]) or 1)
                    dz = prof[j - 1][1] + t * (prof[j][1] - prof[j - 1][1])
                return q[ax] - dz
            def inband(c):
                # except_boxes [[x0,y0,z0,x1,y1,z1]]: no stripe there (Viper MW Kit 4 diffuser bar)
                if any(all(b_[k] <= c[k] <= b_[k + 3] for k in range(3)) for b_ in st.get("except_boxes", [])):
                    return False
                return any(lo <= val(c) <= hi for lo, hi in st["bands"]) and xr[0] <= c[0] <= xr[1]
            def lerp(a_, b_, t):
                return [a_[k] + (b_[k] - a_[k]) * t for k in range(len(a_))]
            moved = 0
            for i in range(0, len(src["positions"]), 3):
                P3, N3, U3 = src["positions"][i:i + 3], src["normals"][i:i + 3], src["uvs"][i:i + 3]
                ny = abs(sum(n[1] for n in N3) / 3)
                if ny > st.get("max_abs_ny", 9) or ny < st.get("min_abs_ny", -1) or                         max(val(q) for q in P3) < cuts[0] or min(val(q) for q in P3) > cuts[-1] or                         max(q[0] for q in P3) < xr[0] or min(q[0] for q in P3) > xr[1]:
                    for k in src:
                        keep[k] += src[k][i:i + 3]
                    continue
                pieces = [[(P3[j], N3[j], U3[j]) for j in range(3)]]
                for c in cuts:                      # split every piece by the plane coordinate[ax] = c
                    nxt = []
                    for pg in pieces:
                        a_, b_ = [], []
                        for j in range(len(pg)):
                            cur, nx_ = pg[j], pg[(j + 1) % len(pg)]
                            fc, fn = val(cur[0]) - c, val(nx_[0]) - c
                            fc = 0 if abs(fc) < 1e-6 else fc; fn = 0 if abs(fn) < 1e-6 else fn
                            if fc <= 0:
                                a_.append(cur)
                            if fc >= 0:                 # a vertex on the plane belongs to both pieces
                                b_.append(cur)
                            if fc * fn < 0:
                                t = fc / (fc - fn)
                                v = (lerp(cur[0], nx_[0], t), lerp(cur[1], nx_[1], t), lerp(cur[2], nx_[2], t))
                                a_.append(v); b_.append(v)
                        nxt += [x for x in (a_, b_) if len(x) >= 3 and any(abs(val(v[0]) - c) > 1e-6 for v in x)]
                    pieces = nxt
                for pg in pieces:
                    cen = [sum(v[0][k] for v in pg) / len(pg) for k in range(3)]
                    tgt = dst if inband(cen) else keep
                    for j in range(1, len(pg) - 1):     # fan
                        for v in (pg[0], pg[j], pg[j + 1]):
                            tgt["positions"].append(v[0]); tgt["normals"].append(v[1]); tgt["uvs"].append(v[2])
                        moved += tgt is dst
            slots[st["from"]] = keep
            if not dst["positions"]:
                del slots[st["to"]]
            elif moved:
                print("stripes %s (axis %d): %d triangles in the bands" % (mesh_name, ax, moved))
        for dec in spec.get("decals", []):
            # side-projected painted decals (a ProStreet vinyl such as the '71 R/T strobe stripe): polygons in side
            # view (x, z), "left" for y < 0 and "right" for y > 0 (separate so lettering reads on both sides). Side-
            # facing paint triangles are cut along every edge line of the polygons they overlap; the pieces whose centre
            # is inside a polygon move to the second paint slot (-> Body_02)
            if dec["from"] not in slots:
                continue
            src = slots[dec["from"]]; keep = {k: [] for k in src}
            dst = slots.setdefault(dec["to"], {k: [] for k in src})
            if dec.get("meshes") and not any(mesh_name.startswith(m) for m in dec["meshes"]):
                continue
            top = dec.get("projection") == "top"   # top view (x, y) for bonnet/trunk stripes; "polys" serve both sides
            B_ = 1 if top else 2
            sides = {-1: dec.get("polys", []), 1: dec.get("polys", [])} if top else                 {-1: dec.get("left", []), 1: dec.get("right", [])}
            boxes = {sd: [(min(p[0] for p in pl), min(p[1] for p in pl), max(p[0] for p in pl), max(p[1] for p in pl))
                          for pl in pls] for sd, pls in sides.items()}
            def inpoly(x, z, pl):
                r = False
                for j in range(len(pl)):
                    (x1, z1), (x2, z2) = pl[j], pl[j - 1]
                    if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
                        r = not r
                return r
            def lerp(a_, b_, t):
                return [a_[k] + (b_[k] - a_[k]) * t for k in range(len(a_))]
            moved = 0
            for i in range(0, len(src["positions"]), 3):
                P3, N3, U3 = src["positions"][i:i + 3], src["normals"][i:i + 3], src["uvs"][i:i + 3]
                ny = sum(n[1] for n in N3) / 3
                sd = -1 if sum(q[1] for q in P3) < 0 else 1
                tx0, tx1 = min(q[0] for q in P3), max(q[0] for q in P3)
                tz0, tz1 = min(q[B_] for q in P3), max(q[B_] for q in P3)
                hit = [k for k, b in enumerate(boxes[sd]) if b[0] <= tx1 and tx0 <= b[2] and b[1] <= tz1 and tz0 <= b[3]]
                nz = sum(n[2] for n in N3) / 3
                facing = nz >= dec.get("min_up_nz", 0.2) if top else ny * sd >= dec.get("min_side_ny", 0.35)
                if not hit or not facing:
                    for k in src:
                        keep[k] += src[k][i:i + 3]
                    continue
                pieces = [[(P3[j], N3[j], U3[j]) for j in range(3)]]
                for k in hit:
                    pl = sides[sd][k]
                    for j in range(len(pl)):
                        (ax_, az), (bx, bz) = pl[j - 1], pl[j]
                        if max(ax_, bx) < tx0 or min(ax_, bx) > tx1 or max(az, bz) < tz0 or min(az, bz) > tz1:
                            continue                 # an edge clear of the triangle can't cross any of its pieces
                        f = lambda q: (q[0] - ax_) * (bz - az) - (q[B_] - az) * (bx - ax_)
                        nxt = []
                        for pg in pieces:
                            a_, b_ = [], []
                            for m in range(len(pg)):
                                cur, nx_ = pg[m], pg[(m + 1) % len(pg)]
                                fc, fn = f(cur[0]), f(nx_[0])
                                fc = 0 if abs(fc) < 1e-6 else fc; fn = 0 if abs(fn) < 1e-6 else fn
                                if fc <= 0:
                                    a_.append(cur)
                                if fc >= 0:             # a vertex on the line belongs to both pieces
                                    b_.append(cur)
                                if fc * fn < 0:
                                    t = fc / (fc - fn)
                                    v = (lerp(cur[0], nx_[0], t), lerp(cur[1], nx_[1], t), lerp(cur[2], nx_[2], t))
                                    a_.append(v); b_.append(v)
                            nxt += [x for x in (a_, b_) if len(x) >= 3 and any(abs(f(v[0])) > 1e-6 for v in x)]
                        pieces = nxt
                for pg in pieces:
                    cx = sum(v[0][0] for v in pg) / len(pg); cz = sum(v[0][B_] for v in pg) / len(pg)
                    tgt = dst if any(inpoly(cx, cz, sides[sd][k]) for k in hit) else keep
                    for j in range(1, len(pg) - 1):
                        for v in (pg[0], pg[j], pg[j + 1]):
                            tgt["positions"].append(v[0]); tgt["normals"].append(v[1]); tgt["uvs"].append(v[2])
                        moved += tgt is dst
            slots[dec["from"]] = keep
            if not dst["positions"]:
                del slots[dec["to"]]
            elif moved:
                print("decals %s: %d triangles" % (mesh_name, moved))
        for tw in spec.get("surface_tweaks", []):
            # thin trim tucked under a panel (Chevelle chrome wheel-arch lips, normal y ~0.58) sits in the panel's
            # shadow and flickers in game: lift it outward (along +-y by side) and turn its shading normals outward
            if tw["from"] not in slots:
                continue
            b = tw["box"]                   # [x0, |y|0, z0, x1, |y|1, z1]: both sides
            sl = slots[tw["from"]]; lift = tw.get("lift", 0.25); bl = tw.get("normal_blend", 0.6); n_ = 0
            for i in range(0, len(sl["positions"]), 3):
                P3 = sl["positions"][i:i + 3]
                if not all(b[0] <= q[0] <= b[3] and b[1] <= abs(q[1]) <= b[4] and b[2] <= q[2] <= b[5] for q in P3):
                    continue
                sd = 1 if sum(q[1] for q in P3) > 0 else -1
                for j in range(3):
                    p = sl["positions"][i + j]; sl["positions"][i + j] = [p[0], p[1] + sd * lift, p[2]]
                    nv = sl["normals"][i + j]
                    nv = [nv[0] * (1 - bl), nv[1] * (1 - bl) + sd * bl, nv[2] * (1 - bl)]
                    L = sum(x * x for x in nv) ** 0.5 or 1
                    sl["normals"][i + j] = [x / L for x in nv]
                n_ += 1
            if n_:
                print("surface tweak %s %s: %d tris" % (mesh_name, tw["from"], n_))
        for rule in spec.get("signal_lamps", []):
            # turn signals: triangles of a slot (optionally inside a car-space box / texture box / on amber texels) move
            # to Signal_L (y < 0, the car's left) or Signal_R; final_slot_names makes them LeftSignalLight /
            # RightSignalLight, the slot names the game flashes (M_TurnSignalLight param TurnLight)
            if rule["from"] not in slots:
                continue
            for ax_, at in rule.get("cuts", []):
                # split the source slot's triangles along the plane coordinate[ax_] = at first, so a box can take part
                # of a lamp face made of a few big triangles (Chevelle tail lamps: outer half blinker, inner half tail)
                s0 = slots[rule["from"]]; s1 = {k: [] for k in s0}
                for i in range(0, len(s0["positions"]), 3):
                    vs = [(s0["positions"][i + j], s0["normals"][i + j], s0["uvs"][i + j]) for j in range(3)]
                    f = [v[0][ax_] - at for v in vs]
                    f = [0 if abs(x) < 1e-6 else x for x in f]
                    pcs = [vs]
                    if min(f) < 0 < max(f):
                        a_, b_ = [], []
                        for j in range(3):
                            cur, nx_, fc, fn = vs[j], vs[(j + 1) % 3], f[j], f[(j + 1) % 3]
                            if fc <= 0:
                                a_.append(cur)
                            if fc >= 0:
                                b_.append(cur)
                            if fc * fn < 0:
                                t = fc / (fc - fn)
                                v = tuple([cur[m][k] + (nx_[m][k] - cur[m][k]) * t for k in range(len(cur[m]))] for m in range(3))
                                a_.append(v); b_.append(v)
                        pcs = [x for x in (a_, b_) if len(x) >= 3]
                    for pg in pcs:
                        for j in range(1, len(pg) - 1):
                            for v in (pg[0], pg[j], pg[j + 1]):
                                s1["positions"].append(list(v[0])); s1["normals"].append(list(v[1])); s1["uvs"].append(list(v[2]))
                slots[rule["from"]] = s1
            src = slots[rule["from"]]; keep = {k: [] for k in src}
            tag = rule.get("tag", "")         # per-texture slot names (Signal_L_F / Signal_L_R): one lens texture each
            names = {"Signal_L": "Signal_L" + tag, "Signal_R": "Signal_R" + tag}
            sides = {s_: slots.setdefault(names[s_], {k: [] for k in src}) for s_ in ("Signal_L", "Signal_R")}
            box, ubox = rule.get("box"), rule.get("uv_box")
            img = None
            if rule.get("amber") or rule.get("white"):
                from PIL import Image
                img = Image.open(os.path.join(os.path.dirname(os.path.expanduser(spec["out_dir"])), "textures",
                                              rule["from"].replace("Tex_", "") + ".png")).convert("RGB")
            def amber(uvs):
                hits = 0
                for w in ((1/3, 1/3, 1/3), (.6, .2, .2), (.2, .6, .2), (.2, .2, .6)):
                    u = sum(w[j] * uvs[j][0] for j in range(3)) % 1; r_ = (1 - sum(w[j] * uvs[j][1] for j in range(3))) % 1
                    R, G, B = img.getpixel((min(img.width - 1, int(u * img.width)), min(img.height - 1, int(r_ * img.height))))
                    if rule.get("white"):     # clear / white lens sections (reverse lamps in a tail cluster)
                        hits += min(R, G, B) > 120 and max(R, G, B) - min(R, G, B) < 45
                    else:
                        hits += R > 60 and R > 1.25 * G and G > 0.35 * R and B < 0.55 * G
                return hits >= 3
            n = {"Signal_L": 0, "Signal_R": 0}
            for i in range(0, len(src["positions"]), 3):
                P3 = src["positions"][i:i + 3]; U3 = src["uvs"][i:i + 3]
                ok = (not box or all(all(box[a] <= q[a] <= box[a + 3] for a in range(3)) for q in P3)) and                      (not ubox or all(ubox[0] <= q[0] % 1 <= ubox[2] and ubox[1] <= (1 - q[1]) % 1 <= ubox[3] for q in U3)) and                      (img is None or amber(U3))
                side = "Signal_L" if sum(q[1] for q in P3) < 0 else "Signal_R"
                n[side] += ok
                if ok and rule.get("copy"):
                    # overlay: the lamp keeps its own slot (e.g. TailLight, which the game needs for its lamp logic);
                    # a copy lifted along the normal carries the signal material (masked to the clear lens section)
                    lift = rule.get("lift", 0.08)
                    N3 = src["normals"][i:i + 3]
                    sides[side]["positions"] += [[P3[j][k] + lift * N3[j][k] for k in range(3)] for j in range(3)]
                    sides[side]["normals"] += [list(x) for x in N3]; sides[side]["uvs"] += [list(x) for x in U3]
                    for k in src:
                        keep[k] += src[k][i:i + 3]
                    continue
                dst = sides[side] if ok else keep
                for k in src:
                    dst[k] += src[k][i:i + 3]
            slots[rule["from"]] = keep
            if not keep["positions"]:
                del slots[rule["from"]]                 # no empty slots left behind
            for s_ in names.values():
                if not slots[s_]["positions"]:
                    del slots[s_]
            if n["Signal_L"] or n["Signal_R"]:
                print("signal lamps %s: %s -> L %d / R %d tris" % (mesh_name, rule["from"], n["Signal_L"], n["Signal_R"]))
        for sb in spec.get("slot_boxes", []):
            if sb.get("meshes") and not any(mesh_name.startswith(m_) for m_ in sb["meshes"]):
                continue                 # e.g. MW kit meshes only (not the Body's lamp housings)
            # move a slot's triangles inside a car-space box to another slot, no left/right split (993: the lamp atlas
            # serves headlamps and the tail bar; the bar becomes one TailLight slot on the Zino base)
            if sb["from"] not in slots:
                continue
            src = slots[sb["from"]]; keep = {k: [] for k in src}
            dst = slots.setdefault(sb["to"], {k: [] for k in src}); bx = sb["box"]
            for i in range(0, len(src["positions"]), 3):
                ay = sb.get("abs_y")     # box y range applies to |y| (both sides)
                inside = all(all(bx[a] <= (abs(src["positions"][i + j][a]) if ay and a == 1 else src["positions"][i + j][a]) <= bx[a + 3]
                                 for a in range(3)) for j in range(3))
                for k in src:
                    (dst if inside else keep)[k] += src[k][i:i + 3]
            slots[sb["from"]] = keep
            if sb.get("drop"):           # remove them instead (Diablo: mirror glass that lives in the SideMirror meshes)
                slots.pop(sb["to"], None)
            for k in [k for k in (sb["from"], sb["to"]) if k in slots and not slots[k]["positions"]]:
                slots.pop(k)
        gb = mdef.get("grille_backing") or spec.get("grille_backing")
        if gb:
            # a dark surface `depth` cm behind each grille face (MW mesh grilles: the openings behind them were empty,
            # so the wheel / ground showed through, Viper Kit 3 side vent)
            dst = None
            for gs in gb["slots"]:
                if gs not in slots:
                    continue
                dst = dst or slots.setdefault(gb.get("to", "Bottom"), {"positions": [], "normals": [], "uvs": []})
                src = slots[gs]
                # double_sided meshes already carry a reversed copy (second half): backing those put the black layer
                # 2 cm IN FRONT of the grille (Viper Kit 4: grille openings read solid black). Originals only
                n_src = len(src["positions"]) // 2 if mdef.get("double_sided") else len(src["positions"])
                for i in range(0, n_src, 3):
                    n = [sum(src["normals"][i + j][k] for j in range(3)) / 3 for k in range(3)]
                    ln = sum(x * x for x in n) ** 0.5 or 1
                    for j in range(3):
                        dst["positions"].append([src["positions"][i + j][k] - n[k] / ln * gb.get("depth", 2.0) for k in range(3)])
                        dst["normals"].append(list(src["normals"][i + j])); dst["uvs"].append([0.5, 0.5])
        bs = mdef.get("backstop")
        if bs and slots:
            # backstop: a dark copy of the stock panels `depth` cm under this kit piece, only where the kit surface
            # lies outward of it. Any opening or edge gap in the kit then shows a dark inner skin (as the MW car's own
            # inner body does) instead of the ground / sky behind: nothing on the body is see-through
            import numpy as np
            from scipy.spatial import cKDTree
            K = np.vstack([np.array(b_["positions"]) for b_ in slots.values() if b_["positions"]])
            Kc = K.reshape(-1, 3, 3).mean(1)
            Kpaint = np.concatenate([np.full(len(b_["positions"]) // 3, k_ == "Paint") for k_, b_ in slots.items()
                                     if b_["positions"]])
            ktree = cKDTree(Kc)
            # slot: Bottom (dark inner body) or Paint (gaps closed up in body colour, the user's choice for the Viper
            # widebody fenders 2026-10-29)
            dst = slots.setdefault(bs.get("slot", "Bottom"), {"positions": [], "normals": [], "uvs": []})
            dep = bs.get("depth", 3.0)
            for rp in bs["parts"]:
                for _, rt in load_src(geo, bs["prefix"], rp, lod, {}) or []:
                    T = np.array([[to_mt(cn[0]) for cn in t] for t in rt])
                    if not len(T):
                        continue
                    N = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
                    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
                    S = np.array([[nrm_mt(cn[1]) for cn in t] for t in rt]).mean(1)
                    N *= np.sign((N * S).sum(1, keepdims=True) + 1e-9)      # outward, by the stored normals
                    C = T.mean(1) - N * dep
                    dd, ii = ktree.query(C)
                    out_ = ((Kc[ii] - C) * N).sum(1)                       # kit surface outward of the backstop
                    keep = (dd < bs.get("reach", 12.0)) & (out_ > 0.5)
                    for t, n, kp in zip(T[keep], N[keep], Kpaint[ii[keep]]):
                        # a Paint backstop stays dark behind grilles / dark kit faces (white showed through the
                        # Supra Kit 5 grilles)
                        d_ = dst if kp else slots.setdefault("Bottom", {"positions": [], "normals": [], "uvs": []})
                        q = t - n * dep
                        if np.dot(np.cross(q[1] - q[0], q[2] - q[0]), n) < 0:
                            q = q[[0, 2, 1]]
                        for v in q:
                            d_["positions"].append(v.tolist()); d_["normals"].append(n.tolist()); d_["uvs"].append([0.5, 0.5])
        out = {"name": mesh_name, "slots": [{"slot": k, **v} for k, v in slots.items()]}
        with open(os.path.join(spec["out_dir"], mesh_name + ".json"), "w") as f:
            json.dump(out, f)
        report[mesh_name] = {k: len(v["positions"]) // 3 for k, v in slots.items()}
    return report


def extract_meshes(spec):
    """Move triangles of one mesh into a new mesh centred on a pivot, e.g. the steering wheel out of the body so the
    game can turn it. spec["extract"][name] = {from, center, radius (in the Y-Z plane), x_range}; the pivot is the
    centre of the selected triangles, written back as spec["extract"][name]["pivot"]."""
    import math
    for name, e in spec.get("extract", {}).items():
        path = os.path.join(spec["out_dir"], e["from"] + ".json")
        src = json.load(open(path))
        cy, cz = e["center"][1], e["center"][2]
        keep_slots, take_slots = [], []
        for sl in src["slots"]:
            k = {"slot": sl["slot"], "positions": [], "normals": [], "uvs": []}
            t = {"slot": sl["slot"], "positions": [], "normals": [], "uvs": []}
            P = sl["positions"]
            for i in range(0, len(P), 3):
                inside = all(math.hypot(P[i + j][1] - cy, P[i + j][2] - cz) <= e["radius"] and
                             e["x_range"][0] <= P[i + j][0] <= e["x_range"][1] for j in range(3))
                dst = t if inside else k
                for key in ("positions", "normals", "uvs"):
                    dst[key] += sl[key][i:i + 3]
            if k["positions"]:
                keep_slots.append(k)
            if t["positions"]:
                take_slots.append(t)
        allp = [p for sl in take_slots for p in sl["positions"]]
        if not allp:
            raise SystemExit("extract %s: nothing selected" % name)
        piv = [(min(p[a] for p in allp) + max(p[a] for p in allp)) / 2 for a in range(3)]
        for sl in take_slots:
            sl["positions"] = [[p[0] - piv[0], p[1] - piv[1], p[2] - piv[2]] for p in sl["positions"]]
        tilt = 0.0
        if e.get("align_x"):
            # the game spins a steering wheel about its local X: fit the wheel plane x = a*z + b, stand it upright and
            # give the socket the matching pitch so it still looks tilted but turns without wobbling
            pts = [p for sl in take_slots for p in sl["positions"]]
            mz = sum(p[2] for p in pts) / len(pts); mx = sum(p[0] for p in pts) / len(pts)
            a = sum((p[2] - mz) * (p[0] - mx) for p in pts) / sum((p[2] - mz) ** 2 for p in pts)
            tilt = math.atan(a)
            c, s_ = math.cos(tilt), math.sin(tilt)
            for sl in take_slots:
                sl["positions"] = [[p[0] * c - p[2] * s_, p[1], p[0] * s_ + p[2] * c] for p in sl["positions"]]
                sl["normals"] = [[n[0] * c - n[2] * s_, n[1], n[0] * s_ + n[2] * c] for n in sl["normals"]]
        sc = e.get("scale")   # e.g. 1.12: the MW M3 GTR wheel looked too small in game
        if sc:
            for sl in take_slots:
                sl["positions"] = [[v * sc for v in p] for p in sl["positions"]]
        e["pivot"] = piv
        e["tilt_deg"] = round(math.degrees(tilt), 2)
        socks = spec.setdefault("sockets", {}).setdefault(e["from"], [])
        if e.get("socket") and not any(x["name"] == e["socket"] for x in socks):
            # add it when missing: without the socket the game mounts no wheel at all (Chevelle: cloned spec lost it)
            socks.insert(0, {"name": e["socket"], "loc": [0, 0, 0], "rot": [0, 0, 0]})
        for sock in socks:   # the game attaches the turning wheel at this socket
            if sock["name"] == e.get("socket"):
                # socket_offset: move where the game mounts the wheel (e.g. lower it so the dials show over the rim)
                so = e.get("socket_offset", [0, 0, 0])
                sock["loc"] = [round(piv[k] + so[k], 2) for k in range(3)]
                sock["rot"] = [-e["tilt_deg"], 0, 0]   # pitch down along the steering column
        json.dump({"name": e["from"], "slots": keep_slots}, open(path, "w"))
        json.dump({"name": name, "slots": take_slots}, open(os.path.join(spec["out_dir"], name + ".json"), "w"))
        print("extracted %s from %s: %d tris, pivot (%.1f, %.1f, %.1f), radius %.1f" % (
            name, e["from"], len(allp) // 3, piv[0], piv[1], piv[2],
            max(math.hypot(p[1] - piv[1], p[2] - piv[2]) for p in allp)))


def measure_arches(spec):
    """Wheel fitment: find each wheel-arch opening in the body (largest gap in the outer-skin vertices, |y| > 78 cm,
    in z bands 20-30 cm, near the guessed axle) and use its centre as the wheel's x. Guessed positions were visibly
    off on the 350Z (rear 2.4 cm back). With spec wheels.auto_arches the measured values replace front_x/rear_x."""
    # the body plus the stock body-kit pieces (bumpers/fenders/skirts become separate meshes with add_body_kits)
    names = ["Body"] + [n for n, md in spec["meshes"].items() if md.get("aero") and n.endswith("KIT00")]
    pts = []
    for n in names:
        m = json.load(open(os.path.join(spec["out_dir"], n + ".json")))
        pts += [p for sl in m["slots"] for p in sl["positions"] if abs(p[1]) > 78]
    w = spec["wheels"]
    found = {}
    for key in ("front_x", "rear_x"):
        x0 = w[key]; centres = []
        for z0 in (20, 25, 30):
            xs = sorted(p[0] for p in pts if abs(p[2] - z0) < 3 and abs(p[0] - x0) < 70)
            best = None
            for a, b in zip(xs, xs[1:]):
                if a <= x0 + 40 and b >= x0 - 40 and (best is None or b - a > best[1] - best[0]):
                    best = (a, b)
            if best and best[1] - best[0] > 40:
                centres.append((best[0] + best[1]) / 2)
        if centres:
            found[key] = round(sum(centres) / len(centres), 1)
    print("wheel arches: measured %s (spec %s)" % (found, {k: w[k] for k in ("front_x", "rear_x")}))
    if w.get("auto_arches"):
        w.update(found)


def place_mirror_sockets(spec):
    """Motor Town's side mirror mesh is the reflective glass only; its socket (SideMirror_L/_R) sits on the glass with
    X pointing away from the glass normal (Zino: yaw -17 for the left mirror). Computed from the glass triangles."""
    import math
    for mesh_name, sock_name in spec.get("mirror_sockets", {}).items():
        m = json.load(open(os.path.join(spec["out_dir"], mesh_name + ".json")))
        P = [p for sl in m["slots"] for p in sl["positions"]]
        N = [n for sl in m["slots"] for n in sl["normals"]]
        if not P:
            continue
        c = [sum(p[k] for p in P) / len(P) for k in range(3)]
        n = [sum(v[k] for v in N) / len(N) for k in range(3)]
        l = math.sqrt(sum(x * x for x in n)); x = [-v / l for v in n]
        eye = spec.get("blueprint", {}).get("cockpit_camera")
        if eye and spec.get("mirror_aim", True):
            # aim like an adjusted real mirror: the driver's eye ray reflects to straight back, a little outward.
            # The mirror normal is parallel to (reflected - incoming); socket X = -normal (Zino convention).
            d = [c[k] - eye[k] for k in range(3)]; dl = math.sqrt(sum(v * v for v in d)); d = [v / dl for v in d]
            out = spec.get("mirror_outward", 0.15) * (1 if c[1] > 0 else -1)
            r = [-1.0, out, 0.0]; rl = math.sqrt(sum(v * v for v in r)); r = [v / rl for v in r]
            nn = [r[k] - d[k] for k in range(3)]; nl = math.sqrt(sum(v * v for v in nn))
            x = [-v / nl for v in nn]
        rot = [round(math.degrees(math.asin(max(-1, min(1, x[2])))), 2), round(math.degrees(math.atan2(x[1], x[0])), 2), 0]
        socks = spec.setdefault("sockets", {}).setdefault(mesh_name, [])
        socks[:] = [s for s in socks if s["name"] != sock_name] + [{"name": sock_name, "loc": [round(v, 2) for v in c], "rot": rot}]
        print("mirror socket %s on %s: loc %s rot %s" % (sock_name, mesh_name, [round(v, 1) for v in c], rot))


def rot_axes(r):
    """UE FRotator [pitch, yaw, roll] (deg) -> its X, Y, Z axes in world space (FRotationMatrix)."""
    import math
    p, y, ro = (math.radians(v) for v in r)
    cp, sp, cy, sy, cr, sr = math.cos(p), math.sin(p), math.cos(y), math.sin(y), math.cos(ro), math.sin(ro)
    return ([cp * cy, cp * sy, sp],
            [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp],
            [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp])


def axes_rot(X, Y, Z):
    """Axes -> FRotator [pitch, yaw, roll] (FMatrix::Rotator)."""
    import math
    pitch = math.degrees(math.atan2(X[2], math.sqrt(X[0] ** 2 + X[1] ** 2)))
    yaw = math.degrees(math.atan2(X[1], X[0]))
    _, SY, _ = rot_axes([pitch, yaw, 0])
    dot = lambda a, b: sum(a[i] * b[i] for i in range(3))
    roll = math.degrees(math.atan2(dot(Z, SY), dot(Y, SY)))
    return [round(pitch, 3), round(yaw, 3), round(roll, 3)]


def to_parent_frame(loc, rot, ploc, prot):
    """A car-space socket transform expressed in a parent socket's frame (e.g. the Magis Dashboard component hangs
    off the Body socket SteeringWheel)."""
    dot = lambda a, b: sum(a[i] * b[i] for i in range(3))
    PX, PY, PZ = rot_axes(prot)
    d = [loc[i] - ploc[i] for i in range(3)]
    local_loc = [round(dot(d, PX), 3), round(dot(d, PY), 3), round(dot(d, PZ), 3)]
    SX, SYa, SZ = rot_axes(rot)
    to_local = lambda v: [dot(v, PX), dot(v, PY), dot(v, PZ)]
    return local_loc, axes_rot(to_local(SX), to_local(SYa), to_local(SZ))


def make_dashboard(spec):
    """Motor Town's MTDashboard draws the gauge faces itself and turns needle meshes at sockets named
    Niddle_RPM / Niddle_Speed / Niddle_Fuel / Niddle_Temp on its DashboardMesh (car space). We give the car a
    Dashboard mesh that is only a tiny hidden triangle carrying those sockets, placed on the car's own cluster."""
    dash = spec.get("dashboard")
    if not dash:
        return
    import math
    c = dash["sockets"][0]["loc"]
    tri = [[c[0] + 0.5, c[1], c[2]], [c[0] + 0.5, c[1] + 0.1, c[2]], [c[0] + 0.5, c[1], c[2] + 0.1]]
    slots_out = [{"slot": "Glass", "positions": tri, "normals": [[-1, 0, 0]] * 3, "uvs": [[0, 0]] * 3}]
    mfd = dash.get("mfd")
    if mfd:
        # the game's upper MFD widget (turn-signal arrows, headlight, handbrake, low fuel, TCS, overheat icons on a
        # transparent background) renders onto Dashboard faces named DashboardUpperMFD (material M_WidgetRender)
        by = {x["name"]: x for x in dash["sockets"]}
        anc = [by[n]["loc"] for n in mfd["anchor"]]
        mid = [sum(a[k] for a in anc) / len(anc) for k in range(3)]
        t = math.radians(-90 - by[mfd["anchor"][0]]["rot"][2])      # dial panel tilt from the needle roll
        n = [-math.cos(t), 0.0, -math.sin(t)]                          # towards the driver
        up = [-math.sin(t), 0.0, math.cos(t)]; right = [0.0, 1.0, 0.0]
        cen = [mid[k] + mfd.get("up", 5) * up[k] + mfd.get("right", 0) * right[k] + mfd.get("out", 0.2) * n[k] for k in range(3)]
        w, h = mfd.get("width", 8) / 2, mfd.get("height", 1.6) / 2
        P = lambda a, b: [cen[k] + a * w * right[k] + b * h * up[k] for k in range(3)]
        BL, BR, TL, TR = P(-1, -1), P(1, -1), P(-1, 1), P(1, 1)
        quad = [BL, TL, BR, BR, TL, TR]                    # json order: geometric normal = facing (as in Body)
        uvs = [[0, 1], [0, 0], [1, 1], [1, 1], [0, 0], [1, 0]]
        if dash.get("parent_socket"):
            parent = next(x for x in spec["sockets"]["Body"] if x["name"] == dash["parent_socket"])
            quad = [to_parent_frame(q, [0, 0, 0], parent["loc"], parent.get("rot", [0, 0, 0]))[0] for q in quad]
            nl = to_parent_frame([parent["loc"][k] + n[k] for k in range(3)], [0, 0, 0], parent["loc"], parent.get("rot", [0, 0, 0]))[0]
        else:
            nl = n
        slots_out.append({"slot": "DashboardUpperMFD", "positions": quad, "normals": [nl] * 6, "uvs": uvs})
        print("dashboard MFD strip at %s (%sx%s cm)" % ([round(x, 1) for x in cen], mfd.get("width", 8), mfd.get("height", 1.6)))
    json.dump({"name": "Dashboard", "slots": slots_out}, open(os.path.join(spec["out_dir"], "Dashboard.json"), "w"))
    socks = dash["sockets"]
    if dash.get("parent_socket"):
        # bases whose Dashboard component attaches to a Body socket (Magis: DashboardAttachSocketName defaults to
        # SteeringWheel, while the Zino sets None): express the car-space dial positions in that socket's frame
        parent = next(x for x in spec["sockets"]["Body"] if x["name"] == dash["parent_socket"])
        socks = []
        for x in dash["sockets"]:
            l, r = to_parent_frame(x["loc"], x["rot"], parent["loc"], parent.get("rot", [0, 0, 0]))
            socks.append({"name": x["name"], "loc": l, "rot": r})
        print("dashboard sockets relative to %s %s %s: %s" % (dash["parent_socket"], parent["loc"], parent.get("rot"),
                                                              [(x["name"], x["loc"]) for x in socks]))
    spec.setdefault("sockets", {})["Dashboard"] = socks


def make_needles(spec):
    """Per-car gauge needles (spec "needle_color" [r,g,b]): the game turns Muscle_01 Niddle / SmallNiddle on every car
    (white). Same size and frame as those (pointing +X from the pivot, 0.8 cm tail, 1.6 cm wide at the hub, 0.47 cm
    thick in +Z; small = half), as closed prisms in one glowing slot NeedleGlow (texture Tex_<car>_NEEDLE)."""
    if not spec.get("needle_color"):
        return
    for name, k in (("Needle", 1.0), ("SmallNeedle", 0.5)):
        outline = [(-0.8, -0.4), (0.3, -0.55), (4.39, -0.12), (4.39, 0.12), (0.3, 0.55), (-0.8, 0.4)]   # CCW from +Z
        # spec needle_width scales the width only (the user: the game-sized needles looked too thick on the 350Z)
        wk = spec.get("needle_width", 0.5)
        outline = [(x * k, y * k * wk) for x, y in outline]
        z0, z1 = 0.02 * k, 0.47 * k
        pos, nrm = [], []
        def tri(a, b, c):
            ab = [b[i] - a[i] for i in range(3)]; ac = [c[i] - a[i] for i in range(3)]
            n = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]]
            l = math.sqrt(sum(v * v for v in n)) or 1.0
            pos.extend([list(a), list(b), list(c)]); nrm.extend([[v / l for v in n]] * 3)
        top = [(x, y, z1) for x, y in outline]; bot = [(x, y, z0) for x, y in outline]
        for i in range(1, len(outline) - 1):
            tri(top[0], top[i], top[i + 1])            # +Z
            tri(bot[0], bot[i + 1], bot[i])            # -Z
        for i in range(len(outline)):
            j = (i + 1) % len(outline)
            tri(bot[i], bot[j], top[j]); tri(bot[i], top[j], top[i])   # sides, outward for a CCW outline
        json.dump({"name": name, "slots": [{"slot": "NeedleGlow", "positions": pos, "normals": nrm,
                                            "uvs": [[0.5, 0.5]] * len(pos)}]},
                  open(os.path.join(spec["out_dir"], name + ".json"), "w"))
    tag = "Tex_%s_NEEDLE" % spec["car"].split("_", 1)[1]
    spec.setdefault("emissive_slots", {})["NeedleGlow"] = {"texture_slot": tag, "glow": spec.get("needle_glow", 2.0)}
    print("needles: %s %s" % (tag, spec["needle_color"]))


def axis_map(build_root):
    """How UE's OBJ importer maps axes, measured by the editor's axis test (min/max of a (100,50,25) triangle).
    Returns a function MT(x,y,z) -> OBJ (x,y,z) that lands on the wanted MT coordinates after import."""
    res = json.load(open(os.path.join(build_root, "axis_test_result.json")))
    mn, mx = res["min"], res["max"]
    # which UE axis received each OBJ axis, and with which sign
    ue_of_obj = {}
    for obj_axis, mag in ((0, 100.0), (1, 50.0), (2, 25.0)):
        for ue_axis in range(3):
            if abs(abs(mx[ue_axis]) - mag) < 0.5 and mx[ue_axis] > 0.5:
                ue_of_obj[obj_axis] = (ue_axis, 1.0)
            elif abs(abs(mn[ue_axis]) - mag) < 0.5 and mn[ue_axis] < -0.5:
                ue_of_obj[obj_axis] = (ue_axis, -1.0)
    if len(ue_of_obj) != 3:
        raise SystemExit("axis test not understood: %s" % res)

    def to_obj(v):
        out = [0.0, 0.0, 0.0]
        for obj_axis, (ue_axis, sign) in ue_of_obj.items():
            out[obj_axis] = v[ue_axis] * sign
        return out
    det_flip = None
    return to_obj, ue_of_obj


def write_objs(spec, to_obj):
    meshes = []
    for mesh_name in list(spec["meshes"]) + list(spec.get("extract", {})) + (["Dashboard"] if spec.get("dashboard") else []) +             (["Needle", "SmallNeedle"] if spec.get("needle_color") else []):
        d = json.load(open(os.path.join(spec["out_dir"], mesh_name + ".json")))
        path = os.path.join(spec["out_dir"], mesh_name + ".obj")
        with open(path, "w") as f:
            f.write("# %s from ProStreet %s (converted on the player's PC)\n" % (mesh_name, spec["car"]))
            vi = 1
            for s in d["slots"]:
                f.write("g %s\nusemtl %s\n" % (s["slot"], s["slot"]))
                for p, n, uv in zip(s["positions"], s["normals"], s["uvs"]):
                    o, no = to_obj(p), to_obj(n)
                    f.write("v %.4f %.4f %.4f\nvn %.5f %.5f %.5f\nvt %.5f %.5f\n" % (o[0], o[1], o[2], no[0], no[1], no[2], uv[0], uv[1]))  # no flip: the importer flips V and the DAE UVs are D3D (top-left)
                for t in range(len(s["positions"]) // 3):
                    a = vi + 3 * t
                    f.write("f %d/%d/%d %d/%d/%d %d/%d/%d\n" % (a, a, a, a + 2, a + 2, a + 2, a + 1, a + 1, a + 1))  # reversed: after the Y flip our order is clockwise, OBJ front is counter-clockwise
                vi += len(s["positions"])
        m = {"name": spec["mesh_names"].get(mesh_name, mesh_name), "obj": path.replace(chr(92), "/")}
        if mesh_name.startswith("Wheel"):
            m["dest"] = "/Game/Cars/Parts/Wheels"
        if mesh_name == "SteeringWheel":
            m["dest"] = "/Game/Cars/Parts/SteeringWheels"
        if mesh_name == "Body":
            if "collision_boxes" in spec:
                m["collision_boxes"] = spec["collision_boxes"]
            else:
                m["collision"] = "convex"
        if spec.get("meshes", {}).get(mesh_name, {}).get("bbox_collision"):
            # e.g. door components: one box round the mesh so the game can trace/interact with it
            ps_ = [q for s_ in d["slots"] for q in s_["positions"]]
            lo = [min(q[k] for q in ps_) for k in range(3)]; hi = [max(q[k] for q in ps_) for k in range(3)]
            m["collision_boxes"] = [{"center": [round((lo[k] + hi[k]) / 2, 2) for k in range(3)],
                                     "size": [round(max(1.0, hi[k] - lo[k]), 2) for k in range(3)]}]
        if mesh_name in spec.get("sockets", {}):
            m["sockets"] = spec["sockets"][mesh_name]
        meshes.append(m)
    return meshes


def draw_gauge(im, g):
    """Paint a crisp gauge face into a texture so the game's live needles have a readable scale. Angles follow
    Motor Town's MTDashboard: degrees clockwise from 3 o'clock, value min at `start`, max at `end`.
    `aspect` (= cm per u / cm per row on the dash triangles, from measure_gauge_aspect) pre-squashes the face
    vertically so it is round on the car: the gauge is drawn on a square canvas, then resized and pasted."""
    a_ = g.get("aspect", 1.0)
    rot_ = g.get("rotate", 0.0)   # degrees counter-clockwise in the texture (dial art drawn rotated, e.g. the R34 cluster)
    if abs(a_ - 1.0) > 1e-3 or abs(rot_) > 1e-3 or g.get("flip_x"):
        from PIL import Image
        W, H = im.size
        cx, cy = g["center"][0] * W, g["center"][1] * H
        ext = g["radius"] * W
        if "face" in g:
            ext = max(ext, g["face"][2] * W + abs(g["face"][0] * W - cx), g["face"][2] * W + abs(g["face"][1] * H - cy) / a_)
        half = int(ext * 1.1) + 2
        tmp = Image.new("RGBA", (2 * half, 2 * half), (0, 0, 0, 0))
        g2 = dict(g, aspect=1.0, rotate=0.0, flip_x=False, center=[half / tmp.width, half / tmp.height])
        g2["radius"] = g["radius"] * W / tmp.width
        if "face" in g:
            g2["face"] = [(half + g["face"][0] * W - cx) / tmp.width, (half + (g["face"][1] * H - cy) / a_) / tmp.height,
                          g["face"][2] * W / tmp.width]
        draw_gauge(tmp, g2)
        tmp = tmp.resize((tmp.width, max(1, int(round(tmp.height * a_)))), Image.LANCZOS)
        if g.get("flip_x"):   # dash art mapped mirrored on the car (MW Rockport PD4): mirror the face so it reads right
            tmp = tmp.transpose(Image.FLIP_LEFT_RIGHT)
        if abs(rot_) > 1e-3:
            tmp = tmp.rotate(rot_, resample=Image.BICUBIC, expand=True)
            half = tmp.width // 2
        im.alpha_composite(tmp, (int(round(cx - half)), int(round(cy - tmp.height / 2))))
        return
    import math
    from PIL import ImageDraw, ImageFont
    W, H = im.size
    d = ImageDraw.Draw(im)
    cx, cy = g["center"][0] * W, g["center"][1] * H
    # per-car style (spec "gauge_style", merged into each entry; entries may override): the real car's cluster look
    tup = lambda c, a=255: tuple(int(v) for v in c[:3]) + (a,)
    face_col = tup(g.get("face_color", [8, 8, 10]))
    ink = tup(g.get("ink", [245, 245, 245]))
    minor_ink = tup(g.get("minor_ink", g.get("ink", [245, 245, 245])))
    red_col = tup(g.get("red_color", [230, 40, 30]))
    cap_col = tup(g.get("caption_color", g.get("ink", [200, 200, 200])))
    font_file = "C:/Windows/Fonts/" + g.get("font_file", "arialbd.ttf")
    if "face" in g:   # dial face (centre/radius may differ from the needle pivot, e.g. a dial holding two gauges)
        fx, fy, fr = g["face"][0] * W, g["face"][1] * H, g["face"][2] * W
        d.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], fill=face_col)
        if g.get("face_inner"):   # e.g. a darker centre disc, brushed-metal look: [colour, radius fraction]
            ic, f_ = g["face_inner"]
            d.ellipse([fx - fr * f_, fy - fr * f_, fx + fr * f_, fy + fr * f_], fill=tup(ic))
        if g.get("ring"):         # bezel ring: [colour, width as a fraction of the face radius]
            rc, rw = g["ring"]
            d.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], outline=tup(rc), width=max(1, int(fr * rw)))
    r = g["radius"] * W
    font = ImageFont.truetype(font_file, max(8, int(r * g.get("font", 0.2))))
    lo, hi, a0, a1 = g["min"], g["max"], g["start"], g["end"]
    def ang(v):
        return math.radians(a0 + (v - lo) / (hi - lo) * (a1 - a0))
    def pt(v, f):
        a = ang(v)
        return cx + f * r * math.cos(a), cy + f * r * math.sin(a)
    v = lo; n = 0
    while v <= hi + 1e-6:
        major = abs((v - lo) / g["text_step"] - round((v - lo) / g["text_step"])) < 1e-6
        red = g.get("red_from") is not None and v >= g["red_from"]
        col = red_col if red else (ink if major else minor_ink)
        t_in = g.get("tick_major", 0.74) if major else g.get("tick_minor", 0.84)
        d.line([pt(v, t_in), pt(v, g.get("tick_outer", 0.97))], fill=col,
               width=max(2, int(r * (g.get("tick_w_major", 0.045) if major else g.get("tick_w_minor", 0.025)))))
        if major and g.get("numbers", True):
            label = g.get("labels", {}).get("%g" % v, ("%g" % (v / g.get("label_div", 1))))
            x, y = pt(v, g.get("number_radius", 0.52))
            d.text((x, y), label, fill=red_col if red else ink, font=font, anchor="mm")
        v = round(v + g["line_step"], 6)
    for txt, f, a in g.get("captions", []):   # e.g. ("x1000 RPM", 0.35, 90)
        cf = ImageFont.truetype(font_file, max(7, int(r * g.get("caption_font", 0.12))))
        d.text((cx + f * r * math.cos(math.radians(a)), cy + f * r * math.sin(math.radians(a))), txt,
               fill=cap_col, font=cf, anchor="mm")


AI_UPSCALER = os.path.expanduser("~/tools/realesrgan/realesrgan-ncnn-vulkan.exe")
AI_CACHE = os.path.expanduser("~/mt-work/ai_upscale_cache")


def ai_upscale(im, src_path):
    """4x AI upscale of a source texture (Real-ESRGAN x4plus model), cached by source file name + mtime."""
    import subprocess
    from PIL import Image
    os.makedirs(AI_CACHE, exist_ok=True)
    real = src_path.split("#")[0]
    key = "%s%s_%d" % (os.path.basename(real).rsplit(".", 1)[0], ("_" + src_path.split("#")[1]) if "#" in src_path else "",
                        int(os.path.getmtime(real)))
    out = os.path.join(AI_CACHE, key + "_x4.png")
    if not os.path.exists(out):
        inp = os.path.join(AI_CACHE, key + "_in.png")
        im.save(inp)
        subprocess.run([AI_UPSCALER, "-i", inp, "-o", out, "-n", "realesrgan-x4plus"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return Image.open(out).convert("RGBA")



def tex_files(spec, name):
    """Source .dds files for a texture slot name. Spec texture_sources {<name>: "0xHASH"} picks by hash: Most Wanted
    dumps truncate names (ON/OFF variants share one) and some names don't match the contents."""
    ts = spec.get("texture_sources", {})
    h = ts.get(name) or ts.get("Tex_" + name)   # keyed by slot name, with or without "Tex_"
    if h:
        return [f for f in os.listdir(tex_dir(spec, name)) if f.upper().startswith(h.upper() + "_")]
    return [f for f in os.listdir(tex_dir(spec, name)) if f.endswith("_" + name + ".dds")]


def tex_dir(spec, name):
    """Texture folder for a slot: spec "texture_dirs" {<name>: dir} (textures of another car/game, e.g. Most Wanted kit
    pieces on a ProStreet car), else spec texture_dir."""
    td = spec.get("texture_dirs", {})
    return os.path.expanduser(td.get(name) or td.get("Tex_" + name) or spec["texture_dir"])


def write_skins(spec):
    """NFS vinyl liveries as garage skins. Spec "skins": {"dir": <vinyl texture dir>, "pick": [<name>, ...]}: the body's
    paint UV0 is the vinyl layout (MW: checked with the car's DEBUG vinyl), so each vinyl colour texture (with alpha)
    goes onto the paint as-is; build_car makes an M_VinylBody instance per skin (paint Color under the vinyl).
    Truncated dump names can be shared by the colour layer and its mask: take the file with real alpha."""
    sk = spec.get("skins")
    if not sk:
        return []
    from PIL import Image
    d = os.path.expanduser(sk["dir"])
    tdir = os.path.join(os.path.dirname(spec["out_dir"]), "textures")
    os.makedirs(tdir, exist_ok=True)
    out = []
    for name, path in sk.get("baked", {}).items():     # pre-baked liveries (transfer_livery.py: MW boss vinyls)
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            print("skin %s: not found" % name); continue
        key = re.sub(r"[^A-Za-z0-9]", "", name)
        png = os.path.join(tdir, "SKIN_%s.png" % key)
        Image.open(path).convert("RGBA").save(png)
        out.append({"name": key, "png": png.replace(chr(92), "/"), "label": sk.get("labels", {}).get(name, name)})
    for name in sk["pick"]:
        cands = [f for f in os.listdir(d) if f.endswith("_" + name + ".dds") or re.search(r"_%s\.dds$" % re.escape(name), f)]
        best = None
        for f in cands:
            im = Image.open(os.path.join(d, f)).convert("RGBA")
            lo, hi = im.split()[3].getextrema()
            score = (hi - lo) + (0 if im.convert("RGB").getextrema()[0] == im.convert("RGB").getextrema()[1] else 1)
            if best is None or score > best[0]:
                best = (score, im)
        if not best:
            print("skin %s: not found" % name); continue
        key = re.sub(r"[^A-Za-z0-9]", "", name)       # asset-safe: "BMW_24" -> MI_SKIN_BMW_24 would end in _<digits>
        png = os.path.join(tdir, "SKIN_%s.png" % key)
        best[1].save(png)
        out.append({"name": key, "png": png.replace(chr(92), "/"), "label": sk.get("labels", {}).get(name, name)})
    print("skins: %d" % len(out))
    return out

def write_textures(spec):
    from PIL import Image
    out = {}
    tdir = os.path.join(os.path.dirname(spec["out_dir"]), "textures")
    os.makedirs(tdir, exist_ok=True)
    for slot in set(spec["texture_slots"].values()):
        if not slot.startswith("Tex_"):
            continue
        tex_name = slot[4:]
        src = tex_files(spec, tex_name)
        if not src:
            continue
        png = os.path.join(tdir, tex_name + ".png")
        im = Image.open(os.path.join(tex_dir(spec, tex_name), src[0])).convert("RGBA")
        if slot in spec.get("alpha_from_luma", []):
            # additive MW decal atlas -> masked: opacity from brightness (black = see-through to the paint below)
            from PIL import ImageOps
            a = ImageOps.grayscale(im.convert("RGB")).point(lambda v: 0 if v < 28 else min(255, (v - 28) * 6))
            im.putalpha(a)
        g_ = spec.get("texture_gain", {}).get(slot)
        if g_:
            # darken / brighten a whole texture (MW carbon read light grey in Motor Town's lighting)
            from PIL import ImageEnhance
            im = Image.merge("RGBA", ImageEnhance.Brightness(im.convert("RGB")).enhance(g_).split() + (im.getchannel("A"),))
        for patch in spec.get("texture_patches", {}).get(slot, []):
            # erase painted (red) needles inside a circle, so only the game's live needles show on the dial
            W, H = im.size
            cx, cy, r = patch["center"][0] * W, patch["center"][1] * H, patch["radius"] * W
            fill = tuple(patch.get("fill", [18, 18, 20])) + (255,)
            px = im.load()
            for y in range(max(0, int(cy - r)), min(H, int(cy + r) + 1)):
                for x in range(max(0, int(cx - r)), min(W, int(cx + r) + 1)):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                        R, G, B, A = px[x, y]
                        if R > 100 and R > 1.7 * G and R > 1.7 * B:
                            px[x, y] = fill
        scale = spec.get("texture_upscale", {}).get(slot, 1)
        if slot in spec.get("ai_upscale", []):
            # Real-ESRGAN x4 (realesrgan-ncnn-vulkan, GPU): sharp edges instead of a blurry resize; cached per source
            im = ai_upscale(im, os.path.join(tex_dir(spec, tex_name), src[0]))
            scale = max(1, scale // 4)
        if scale > 1:
            im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
        style = spec.get("gauge_style", {})
        faces = [dict(style, **g) for g in spec.get("gauge_faces", {}).get(slot, [])]
        for g in faces:
            keep = None
            if g.get("clip_below") is not None:
                # dials cut off by something in the art (the Elise's info display): keep the original below that row
                W_, H_ = im.size
                y0 = int(g["clip_below"] * H_)
                keep = (y0, im.crop((0, y0, W_, H_)))
            draw_gauge(im, g)
            if keep:
                im.paste(keep[1], (0, keep[0]))
        im.save(png)
        for es_name, es in spec.get("emissive_slots", {}).items():
            if es.get("texture_slot") == slot and es.get("mask_from_gauges"):
                # glow mask: only the painted gauge faces light up, so the slot may cover the whole dash
                from PIL import ImageDraw
                glow = Image.new("RGBA", im.size, (0, 0, 0, 255))
                if any("glow_color" in g for g in faces):
                    # real backlighting: only the markings light up, in the car's own illumination colour (350Z amber,
                    # BMW orange-red...). M_Glow emits texture^3 x Glow, so colours are written as cube roots.
                    cr = lambda c: [int(round(255 * (max(0, v) / 255.0) ** (1 / 3.0))) for v in c]
                    for g in faces:
                        gc = cr(g.get("glow_color", g.get("ink", [245, 245, 245])))
                        rc = cr(g.get("glow_red", g.get("red_color", [230, 40, 30])))
                        if g.get("glow_face"):   # white-faced dials: the face itself is backlit, the markings stay dark
                            fc = cr(g["glow_face"])
                            draw_gauge(glow, dict(g, face_color=fc, face_inner=None, ring=None, ink=[0, 0, 0],
                                                  minor_ink=[0, 0, 0], red_color=rc, caption_color=[0, 0, 0]))
                        else:
                            draw_gauge(glow, dict(g, face_color=[0, 0, 0], face_inner=None, ring=None, ink=gc,
                                                  minor_ink=gc, red_color=rc, caption_color=gc))
                else:
                    mask = Image.new("L", im.size, 0); md = ImageDraw.Draw(mask)
                    for g in faces:
                        if "face" in g:
                            fx, fy, fr = g["face"][0] * im.width, g["face"][1] * im.height, g["face"][2] * im.width
                            md.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], fill=255)
                    glow.paste(im, (0, 0), mask)
                gpng = os.path.join(tdir, tex_name + "_GLOW.png")
                glow.save(gpng)
                out["Tex_" + tex_name + "_GLOW"] = gpng.replace(chr(92), "/")
        out[slot] = png.replace(chr(92), "/")
    if spec.get("needle_color"):
        tag = "Tex_%s_NEEDLE" % spec["car"].split("_", 1)[1]
        png = os.path.join(tdir, tag[4:] + ".png")
        Image.new("RGBA", (8, 8), tuple(spec["needle_color"]) + (255,)).save(png)
        out[tag] = png.replace(chr(92), "/")
    return out


def detail_textures(spec):
    """Give one mesh its own sharper texture: spec detail_textures [{mesh, from, box: [u0, row0, u1, row1], to, size}].
    The box of the source texture is cut out, AI-upscaled twice (x16) and resized to `size` (w, h); the mesh's
    triangles in slot `from` are moved to slot `to` with UVs remapped into the crop. E.g. the R34's steering wheel
    covers ~160x330 px of the 512 px interior texture (the user: "could be upscaled more")."""
    from PIL import Image
    pngs = {}
    tdir = os.path.join(os.path.dirname(spec["out_dir"]), "textures")
    os.makedirs(tdir, exist_ok=True)
    for dt in spec.get("detail_textures", []):
        src_name = dt["from"][4:]
        src = tex_files(spec, src_name)[0]
        src_path = os.path.join(spec["texture_dir"], src)
        im = Image.open(src_path).convert("RGBA")
        W, H = im.size
        u0, r0, u1, r1 = dt["box"]
        crop = im.crop((int(u0 * W), int(r0 * H), int(round(u1 * W)), int(round(r1 * H))))
        big = ai_upscale(ai_upscale(crop, src_path + "#%s" % dt["to"]), src_path + "#%s_2" % dt["to"])
        big = big.resize(tuple(dt.get("size", big.size)), Image.LANCZOS)
        png = os.path.join(tdir, dt["to"][4:] + ".png")
        big.save(png)
        pngs[dt["to"]] = png
        mj = os.path.join(spec["out_dir"], dt["mesh"] + ".json")
        d = json.load(open(mj))
        for sl in d["slots"]:
            if sl["slot"] == dt["from"]:
                sl["slot"] = dt["to"]
                sl["uvs"] = [[(u - u0) / (u1 - u0), 1 - ((1 - v) - r0) / (r1 - r0)] for u, v in sl["uvs"]]
        json.dump(d, open(mj, "w"))
        print("detail texture %s: %s box %s -> %s %s" % (dt["mesh"], dt["from"], dt["box"], dt["to"], big.size))
    spec["_detail_pngs"] = pngs


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    for k in ("geometry_dir", "out_dir", "texture_dir"):   # specs may use ~/ paths
        if k in spec:
            spec[k] = os.path.expanduser(spec[k])
    print(json.dumps(build(spec), indent=1))
    extract_meshes(spec)
    if "wheels" in spec:
        measure_arches(spec)
    make_dashboard(spec)
    make_needles(spec)
    place_mirror_sockets(spec)
    detail_pngs = spec.get("detail_textures") and (detail_textures(spec) or spec.pop("_detail_pngs"))
    tmp = sys.argv[1] + ".tmp"   # keeps the computed pivots for the blueprint/socket step; atomic write
    with open(tmp, "w") as f:
        json.dump(spec, f, indent=1)
    os.replace(tmp, sys.argv[1])
    root = os.path.dirname(os.path.dirname(spec["out_dir"]))
    if os.path.exists(os.path.join(root, "axis_test_result.json")):
        to_obj, mapping = axis_map(root)
        print("axis mapping (obj axis -> ue axis, sign):", mapping)
        car = {"car": spec["car"], "meshes": write_objs(spec, to_obj), "skins": write_skins(spec),
               "textures": dict(write_textures(spec), **(detail_pngs or {})),
               "emissive_slots": spec.get("emissive_slots", {}), "final_slot_names": spec.get("final_slot_names", {}),
               "lamp_slots": spec.get("lamp_slots", {}),
               "paintable_texture_slots": spec.get("paintable_texture_slots", []),
               "masked_texture_slots": spec.get("masked_texture_slots", [])}
        with open(os.path.join(os.path.dirname(spec["out_dir"]), "car.json"), "w") as f:
            json.dump(car, f, indent=1)
        print("wrote car.json with %d meshes, %d textures" % (len(car["meshes"]), len(car["textures"])))
    else:
        print("no axis test yet: run the editor axis test first")
