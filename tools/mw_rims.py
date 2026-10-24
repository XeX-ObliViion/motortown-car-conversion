"""Build the Most Wanted (2005 / Rework IV) aftermarket rim pack (CARS/WHEELS: 41 branded designs, each in 17-20")
for Motor Town, the same way as ps_rims.py builds ProStreet's.

MW rims share ProStreet's wheel frame: tyre 0xE4CEA024 (-> Bottom) radius 32 cm, y -22.4..0, plus the design's own
<DESIGN>_WHEEL texture; files are <BRAND>_STYLEnn_<SIZE>_25_A.dae. One size per design (spec "size", default 18).
Unmirrored + offset +11.5 = the right-hand mesh, mirrored + offset -11.5 = the left-hand one.
Output: build dir with OBJs, textures, car.json (build_car.py) and rims.json (make_mt_assets.py rows).
usage: mw_rims.py <rims_spec.json>"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps_to_mt as P   # noqa: E402

TYRE, CHROME = "0xE4CEA024", "0xBF30889B"
BRANDS = {"5ZIGEN": "5Zigen", "ADR": "ADR", "BBS": "BBS", "ENKEI": "Enkei", "KONIG": "Konig", "LOWENHART": "Lowenhart",
          "OZ": "OZ Racing", "RACINGHART": "Racing Hart", "ROJA": "Roja", "VOLK": "Volk Racing"}


def main():
    spec = json.load(open(sys.argv[1]))
    out_root = os.path.expanduser(spec["out_dir"])
    build_root = os.path.dirname(os.path.dirname(out_root))
    to_obj, _ = P.axis_map(build_root)
    geo = os.path.expanduser(spec["geo_dir"]); tex = os.path.join(geo, "textures")
    size = str(spec.get("size", 18))
    tex_by_hash = {f.split("_")[0]: f for f in os.listdir(tex) if f.endswith(".dds")}
    designs = sorted({m.group(1) for f in os.listdir(geo) for m in [re.match(r"(\w+_STYLE\d\d)_%s_\d\d_A\.dae$" % size, f)] if m})
    gspec = {"car": spec["car"], "geometry_dir": geo, "prefix": "", "out_dir": out_root, "texture_dir": tex,
             "source_scale": spec.get("source_scale", 100.0), "default_slot": "Trim",
             "texture_slots": {TYRE: "Bottom", CHROME: "Trim", "0xE38806E3": "Bottom"}, "meshes": {}, "mesh_names": {},
             "texture_sources": {}}
    rims = []
    for i, dsn in enumerate(designs, 1):
        part = [f[:-6] for f in os.listdir(geo) if re.match(r"%s_%s_\d\d_A\.dae$" % (dsn, size), f)][0]
        for h, _ in P.load_dae(os.path.join(geo, part + "_A.dae")):
            f = tex_by_hash.get(h)
            if f and h not in gspec["texture_slots"]:
                slot = "Tex_MWR_%s" % dsn                       # texture names are truncated in the dump: by hash
                gspec["texture_slots"][h] = slot; gspec["texture_sources"][slot] = h
        short = "M%02d" % i
        asset = "%s_%s" % (spec["car"], short)
        # ps_to_mt joins prefix_part_lod: prefix = the design, part = "<size>_25"
        pp = part[len(dsn) + 1:]
        gspec["meshes"]["Wheel_%s_R" % short] = {"parts": [{"part": pp, "prefix": dsn, "offset": [0, 11.5, 0]}]}
        gspec["meshes"]["Wheel_%s_L" % short] = {"parts": [{"part": pp, "prefix": dsn, "mirror": True, "offset": [0, -11.5, 0]}]}
        gspec["mesh_names"]["Wheel_%s_R" % short] = asset + "_R"
        gspec["mesh_names"]["Wheel_%s_L" % short] = asset + "_L"
        brand, st = dsn.split("_STYLE")
        rims.append({"row": asset, "left": asset + "_L", "right": asset + "_R",
                     "display_name": "%s Style %d (Most Wanted)" % (BRANDS.get(brand, brand.title()), int(st))})
    P.build(gspec)
    meshes = P.write_objs(gspec, to_obj)
    textures = P.write_textures(gspec)
    build_dir = os.path.dirname(out_root)
    rim_slots = sorted(textures)
    json.dump({"car": spec["car"], "meshes": meshes, "textures": textures,
               "final_slot_names": {s_: "Wheel_01" for s_ in rim_slots}, "paintable_texture_slots": rim_slots},
              open(os.path.join(build_dir, "car.json"), "w"), indent=1)
    json.dump(rims, open(os.path.join(build_dir, "rims.json"), "w"), indent=1)
    print("%d MW rims, %d meshes, %d textures -> %s" % (len(rims), len(meshes), len(textures), build_dir))


if __name__ == "__main__":
    main()
