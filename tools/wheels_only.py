"""Make a wheels-only build dir (<build>/_wheels/<CAR>) from a car build: same car name and textures, only the meshes
that go to /Game/Cars/Parts/Wheels. For re-importing rims without rebuilding the whole car (build_many.py).
usage: wheels_only.py <build dir> ...   (prints the new dirs)"""
import json, os, re, sys
for b in sys.argv[1:]:
    c = json.load(open(os.path.join(b, "car.json")))
    w = [m for m in c["meshes"] if m.get("dest") == "/Game/Cars/Parts/Wheels"]
    if not w:
        continue
    used = set()
    for m in w:
        used |= {re.sub(r"^o\d_", "", l.split()[1]) for l in open(m["obj"]) if l.startswith("usemtl ")}
    out = dict(c, meshes=w, textures={k: v for k, v in c["textures"].items() if k in used}, skins=[],
               paintable_texture_slots=[s for s in c.get("paintable_texture_slots", []) if s in used],
               masked_texture_slots=[s for s in c.get("masked_texture_slots", []) if s in used], emissive_slots={})
    d = os.path.join(os.path.dirname(b.rstrip("/\\")), "_wheels", c["car"]); os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, "car.json"), "w"), indent=1)
    print(d.replace("\\", "/"))
