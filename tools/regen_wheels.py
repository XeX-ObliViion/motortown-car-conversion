"""Regenerate ONLY the wheel OBJs of each car from source (fresh input for wheel_mats.py): runs ps_to_mt.py on a copy
of the spec that keeps just the Wheel_* meshes, writing to a temp dir, then copies those OBJs over the build's.
usage: regen_wheels.py <spec.json> ...   (rim packs: run ps_rims.py / mw_rims.py / ac_rims.py instead)"""
import json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps_to_mt as P

for sp in sys.argv[1:]:
    spec = json.load(open(sp))
    if spec.get("kind") or "meshes" not in spec:
        continue
    real = os.path.expanduser(spec["out_dir"])
    tmp = os.path.join(tempfile.gettempdir(), "regen_wheels", spec["car"])
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, "meshes"))
    shutil.copytree(os.path.join(os.path.dirname(real), "textures"), os.path.join(tmp, "textures"))   # some steps read them
    t = dict(spec, out_dir=os.path.join(tmp, "meshes"), extract={}, dashboard=None, needle_color=None,
             meshes={k: v for k, v in spec["meshes"].items() if k.startswith("Wheel")})
    for k in ("geometry_dir", "texture_dir"):
        if k in t:
            t[k] = os.path.expanduser(t[k])
    try:
        P.build(t)
        to_obj, _ = P.axis_map(os.path.dirname(os.path.dirname(real)))   # the real build root holds the axis test
        P.write_objs(t, to_obj)
    except Exception as e:
        print("FAIL %s: %r" % (spec["car"], e)); continue
    objs = [f for f in os.listdir(os.path.join(tmp, "meshes")) if f.endswith(".obj")]
    if not objs:
        print("FAIL %s: no wheel OBJs" % spec["car"]); continue
    for f in objs:
        shutil.copy(os.path.join(tmp, "meshes", f), os.path.join(real, f))
    print("%s: %d wheel OBJs regenerated" % (spec["car"], len(objs)))
