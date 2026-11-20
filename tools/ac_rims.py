"""AC rim pack (AC_Rims): every AC car's rims as universal parts for any car. Each car's own wheel meshes are fitted
to that car (shifted sideways, drag slicks up to 37 cm), so they sit wrong on other cars. Here each one is copied,
centred on the hub and scaled uniformly to the game's standard wheel size (32.2 cm tyre radius at the 0.6466 wheel
scale, like the PS/MW packs and the game's own rims). Writes the build dir build_car.py imports + rims.json for
make_mt_assets (spec cars/ac_rims.json, kind rims).
usage: py -3.13 tools/ac_rims.py cars/ac_rims.json"""
import json, os, re, shutil, sys
import numpy as np

spec = json.load(open(sys.argv[1]))
BUILD = os.path.expanduser("~/mt-work/build")
out = os.path.dirname(os.path.expanduser(spec["out_dir"]))
os.makedirs(os.path.join(out, "meshes"), exist_ok=True); os.makedirs(os.path.join(out, "textures"), exist_ok=True)
TARGET = 32.2 / 0.6466          # raw OBJ radius of a game-standard wheel (ps_to_mt pre-enlarges by 1/0.6466)

meshes, textures, rows = [], {}, []


def normalise(src, dst):
    lines = open(src).read().splitlines()
    P = np.array([[float(x) for x in l.split()[1:4]] for l in lines if l.startswith("v ")])
    c = (P.min(0) + P.max(0)) / 2
    r = np.sqrt((P[:, 0] - c[0]) ** 2 + (P[:, 2] - c[2]) ** 2).max()
    k = TARGET / r
    assert 0.6 < k < 1.6, "%s: odd scale %.2f (radius %.1f)" % (src, k, r)
    mats = set()
    with open(dst, "w") as f:
        for l in lines:
            if l.startswith("v "):
                v = (np.array([float(x) for x in l.split()[1:4]]) - c) * k
                f.write("v %.5f %.5f %.5f\n" % tuple(v))
            else:
                if l.startswith("usemtl "):
                    mats.add(re.sub(r"^o\d_", "", l.split()[1]))
                f.write(l + "\n")
    return mats, k, c


for car in spec["cars"]:
    cj = json.load(open(os.path.join(BUILD, car["car"], "car.json")))
    by_name = {m["name"]: m for m in cj["meshes"]}
    for suffix, label in (("", ""), ("_REAR", " (rear)")):
        L, R = by_name.get(car["car"] + suffix + "_L"), by_name.get(car["car"] + suffix + "_R")
        if not (L and R):
            continue
        row = "AC_Rims_" + car["car"].replace("AC_", "") + suffix
        for side, m in (("L", L), ("R", R)):
            dst = os.path.join(out, "meshes", "%s_%s.obj" % (row, side))
            mats, k, c = normalise(m["obj"], dst)
            print("%s_%s: scale %.3f, hub offset %s" % (row, side, k, np.round(c * 0.6466, 1).tolist()))
            meshes.append({"name": "%s_%s" % (row, side), "obj": dst.replace("\\", "/"), "dest": "/Game/Cars/Parts/Wheels",
                           "reduce": m.get("reduce", 0.35)})
            for s in mats:
                if s in cj["textures"]:
                    png = os.path.join(out, "textures", os.path.basename(cj["textures"][s]))
                    shutil.copyfile(cj["textures"][s], png)
                    textures[s] = png.replace("\\", "/")
        rows.append({"row": row, "left": row + "_L", "right": row + "_R", "display_name": car["name"] + label})

json.dump({"car": spec["car"], "meshes": meshes, "textures": textures, "final_slot_names": {}, "paintable_texture_slots": []},
          open(os.path.join(out, "car.json"), "w"), indent=1)
json.dump(rows, open(os.path.join(out, "rims.json"), "w"), indent=1)
print("%d rim rows, %d meshes, %d textures -> %s" % (len(rows), len(meshes), len(textures), out))
