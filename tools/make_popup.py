"""Pop-up headlamps: a converted car's "Popup" mesh (ps_to_mt mesh JSON, car space, cm) -> glTF skeletal mesh with the
game's pop-up layout (Panther Headlight_01_Skel: root "Bone", children "Headlight_L" / "Headlight_R") and one animation
"Headlight_Popup" that turns both pods about the hinge (the game plays it when the lights go on).
usage: make_popup.py <spec.json>      spec "popup": {"hinge": [x, z], "angle": deg (front edge up), "seconds": 0.5}
Writes <build>/<CAR>/popup/Popup.gltf. Axis convention for the UE glTF importer: see TO_GLTF (checked by import_popup.py)."""
import base64, json, math, os, struct, sys

spec = json.load(open(sys.argv[1]))
pu = spec["popup"]
out_dir = os.path.join(os.path.dirname(os.path.expanduser(spec["out_dir"])), "popup")
os.makedirs(out_dir, exist_ok=True)
mesh = json.load(open(os.path.join(os.path.expanduser(spec["out_dir"]), "Popup.json")))


def TO_GLTF(p):
    # car space (cm, X fwd, Y right, Z up) -> glTF (m, right-handed, Y up). UE's glTF importer reads glTF (x, y, z) as
    # UE (x, -z, y)... checked in import_popup.py by comparing bounds; flip here if that check fails
    x, y, z = p
    return (x / 100.0, z / 100.0, -y / 100.0)


hx, hz = pu["hinge"]
joints = {"Bone": (0.0, 0.0, 0.0), "Headlight_L": (hx, -40.0, hz), "Headlight_R": (hx, 40.0, hz)}
names = ["Bone", "Headlight_L", "Headlight_R"]

pos, nrm, uv, jnt, prims = bytearray(), bytearray(), bytearray(), bytearray(), []
vcount = 0
lo, hi = [1e9] * 3, [-1e9] * 3
for sl in mesh["slots"]:
    P, N, U = sl["positions"], sl["normals"], sl["uvs"]
    idx = bytearray()
    for i in range(len(P)):
        g = TO_GLTF(P[i]); n = TO_GLTF(N[i]); nl = math.sqrt(sum(c * c for c in n)) or 1.0
        pos += struct.pack("<3f", *g); nrm += struct.pack("<3f", *(c / nl for c in n))
        uv += struct.pack("<2f", U[i][0], 1.0 - U[i][1])   # glTF v runs down
        jnt += struct.pack("<4B", 1 if P[i][1] < 0 else 2, 0, 0, 0)
        for k in range(3):
            lo[k] = min(lo[k], g[k]); hi[k] = max(hi[k], g[k])
        idx += struct.pack("<I", vcount + i)
    prims.append((sl["slot"], vcount, len(P), idx))
    vcount += len(P)
weights = struct.pack("<4f", 1, 0, 0, 0) * vcount

# rotation about the car's lateral axis, sign chosen so a point ahead of the hinge rises
ang = math.radians(pu["angle"])
ax = TO_GLTF((0.0, 100.0, 0.0)); al = math.sqrt(sum(c * c for c in ax)); ax = [c / al for c in ax]


def rot(q, v):
    x, y, z, w = q; vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


q_open = [c * math.sin(ang / 2) for c in ax] + [math.cos(ang / 2)]
up = TO_GLTF((0, 0, 100.0)); fwd = TO_GLTF((100.0, 0, 0))
if sum(a * b for a, b in zip(rot(q_open, fwd), up)) < 0:
    q_open = [-c for c in q_open[:3]] + [q_open[3]]
assert sum(a * b for a, b in zip(rot(q_open, fwd), up)) > 0
secs, nk = float(pu.get("seconds", 0.5)), 11
times = [secs * k / (nk - 1) for k in range(nk)]
quats = []
for t in times:
    a = ang * t / secs
    q = [c * math.sin(a / 2) for c in q_open[:3]]
    s = math.sin(ang / 2)
    q = [c / s * math.sin(a / 2) for c in q_open[:3]] + [math.cos(a / 2)]
    quats.append(q)

# inverse bind matrices (joints are translations only; column-major)
ibm = bytearray()
for n in names:
    t = TO_GLTF(joints[n])
    ibm += struct.pack("<16f", 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -t[0], -t[1], -t[2], 1)

blob = bytearray(); views = []; accs = []


def add(data, target=None):
    while len(blob) % 4:
        blob.append(0)
    views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), **({"target": target} if target else {})})
    blob.extend(data)
    return len(views) - 1


def acc(view, ctype, count, typ, **kw):
    accs.append({"bufferView": view, "componentType": ctype, "count": count, "type": typ, **kw})
    return len(accs) - 1


a_pos = acc(add(pos, 34962), 5126, vcount, "VEC3", min=lo, max=hi)
a_nrm = acc(add(nrm, 34962), 5126, vcount, "VEC3")
a_uv = acc(add(uv, 34962), 5126, vcount, "VEC2")
a_j = acc(add(jnt, 34962), 5121, vcount, "VEC4")
a_w = acc(add(weights, 34962), 5126, vcount, "VEC4")
materials, primitives = [], []
for slot, start, count, idx in prims:
    materials.append({"name": slot})
    primitives.append({"attributes": {"POSITION": a_pos, "NORMAL": a_nrm, "TEXCOORD_0": a_uv, "JOINTS_0": a_j, "WEIGHTS_0": a_w},
                       "indices": acc(add(idx, 34963), 5125, count, "SCALAR"), "material": len(materials) - 1})
a_ibm = acc(add(ibm), 5126, len(names), "MAT4")
a_t = acc(add(struct.pack("<%df" % nk, *times)), 5126, nk, "SCALAR", min=[0.0], max=[secs])
a_q = acc(add(b"".join(struct.pack("<4f", *q) for q in quats)), 5126, nk, "VEC4")
a_q0 = acc(add(b"".join(struct.pack("<4f", 0, 0, 0, 1) for _ in quats)), 5126, nk, "VEC4")

nodes = [{"name": "Bone", "children": [1, 2]},
         {"name": "Headlight_L", "translation": list(TO_GLTF(joints["Headlight_L"]))},
         {"name": "Headlight_R", "translation": list(TO_GLTF(joints["Headlight_R"]))},
         {"name": "Popup", "mesh": 0, "skin": 0}]
gltf = {
    "asset": {"version": "2.0", "generator": "ps2motortown make_popup.py"},
    "scene": 0, "scenes": [{"nodes": [0, 3]}], "nodes": nodes,
    "meshes": [{"name": "Popup", "primitives": primitives}], "materials": materials,
    "skins": [{"name": "Popup", "joints": [0, 1, 2], "skeleton": 0, "inverseBindMatrices": a_ibm}],
    "animations": [{"name": "Headlight_Popup",
                    "samplers": [{"input": a_t, "output": a_q, "interpolation": "LINEAR"},
                                 {"input": a_t, "output": a_q0, "interpolation": "LINEAR"}],
                    "channels": [{"sampler": 0, "target": {"node": 1, "path": "rotation"}},
                                 {"sampler": 0, "target": {"node": 2, "path": "rotation"}},
                                 {"sampler": 1, "target": {"node": 0, "path": "rotation"}}]}],
    "accessors": accs, "bufferViews": views,
    "buffers": [{"byteLength": len(blob), "uri": "data:application/octet-stream;base64," + base64.b64encode(bytes(blob)).decode()}],
}
out = os.path.join(out_dir, "Popup.gltf")
json.dump(gltf, open(out, "w"))
print("wrote %s: %d verts, %d slots %s, hinge x %.1f z %.1f, open %.1f deg in %.2f s; car-space bounds x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f"
      % (out, vcount, len(prims), [p[0] for p in prims], hx, hz, pu["angle"], secs,
         *(v for k in range(3) for v in (min(p[k] for s in mesh["slots"] for p in s["positions"]),
                                         max(p[k] for s in mesh["slots"] for p in s["positions"])))))
