"""Build the ProStreet aftermarket rim pack (CARS/GROUP01..08, 96 wheel designs) for Motor Town.

Every ProStreet wheel shares one frame and size (radius 32.2 cm, the same as the stock 350Z wheel) and the same parts:
tyre (texture 0xE4CEA024 -> Bottom), generic chrome (0xBF30889B -> Trim) and the design's own GROUPgg_KITkk_WHEEL texture.
So each rim is built exactly like the 350Z's stock wheel: unmirrored + offset +11.5 is the right-hand mesh, mirrored +
offset -11.5 the left-hand one (the 350Z spec's mesh_names swap). Output: one build dir with OBJs, textures, car.json
(for build_car.py) and rims.json (for make_mt_assets.py: one Wheel part row per rim).

usage: ps_rims.py <rims_spec.json>"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps_to_mt as P   # noqa: E402

TYRE, CHROME = "0xE4CEA024", "0xBF30889B"


def main():
    spec = json.load(open(sys.argv[1]))
    out_root = os.path.expanduser(spec["out_dir"])          # .../build/PS_Rims/meshes
    build_root = os.path.dirname(os.path.dirname(out_root))  # .../build (holds axis_test_result.json)
    to_obj, _ = P.axis_map(build_root)
    all_meshes, all_textures, rims = [], {}, []
    # real wheel names, e.g. "BBS LM", pulled from ProStreet (part_fedata HAL ids -> LANGUAGES/English_Global.bin)
    names_file = spec.get("names")
    names = json.load(open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), names_file), encoding="utf-8")) if names_file else {}
    for g in spec["groups"]:
        gid = "GROUP%02d" % g
        geo = os.path.expanduser(spec["geo_root"].format(g=g))
        tex = os.path.expanduser(spec["tex_root"].format(g=g))
        tex_by_hash = {f.split("_")[0]: f for f in os.listdir(tex) if f.endswith(".dds")}
        kits = sorted({m.group(1) for f in os.listdir(geo)
                       for m in [re.match(r"%s_(KIT\d+)_WHEEL_TIRE_%s_A\.dae$" % (gid, spec["variant"]), f)] if m})
        gspec = {"car": spec["car"], "geometry_dir": geo, "prefix": gid, "out_dir": out_root, "texture_dir": tex,
                 "default_slot": "Trim", "texture_slots": {TYRE: "Bottom", CHROME: "Trim"}, "meshes": {}, "mesh_names": {}}
        for kit in kits:
            part = "%s_WHEEL_TIRE_%s" % (kit, spec["variant"])
            hashes = {t for t, _ in P.load_dae(os.path.join(geo, "%s_%s_A.dae" % (gid, part)))}
            for h in hashes - {TYRE, CHROME}:
                f = tex_by_hash.get(h)
                if f:   # e.g. 0xBE6A2EE9_GROUP01_KIT01_WHEEL.dds -> slot Tex_GROUP01_KIT01_WHEEL
                    gspec["texture_slots"][h] = "Tex_" + f.split("_", 1)[1][:-4]
            short = "G%02d%s" % (g, kit.replace("KIT", "K"))          # G01K01
            asset = "%s_%s" % (spec["car"], short)                    # PS_Rims_G01K01 (pack_car packs <car>_*)
            gspec["meshes"]["Wheel_%s_R" % short] = {"parts": [{"part": part, "offset": [0, 11.5, 0]}]}
            gspec["meshes"]["Wheel_%s_L" % short] = {"parts": [{"part": part, "mirror": True, "offset": [0, -11.5, 0]}]}
            gspec["mesh_names"]["Wheel_%s_R" % short] = asset + "_R"
            gspec["mesh_names"]["Wheel_%s_L" % short] = asset + "_L"
            rims.append({"row": asset, "left": asset + "_L", "right": asset + "_R",
                         "display_name": names.get(short, "ProStreet Rim %d-%s" % (g, kit[3:]))})
        P.build(gspec)
        all_meshes += P.write_objs(gspec, to_obj)
        all_textures.update(P.write_textures(gspec))
        print("%s: %d rims" % (gid, len(kits)))
    build_dir = os.path.dirname(out_root)
    # paintable rims: every rim texture slot uses the paintable textured material and is renamed Wheel_01, the slot
    # name the rows' ColorSlots picker targets (like the game's Civo/Bulko rims)
    rim_slots = sorted(all_textures)
    json.dump({"car": spec["car"], "meshes": all_meshes, "textures": all_textures,
               "final_slot_names": {s_: "Wheel_01" for s_ in rim_slots}, "paintable_texture_slots": rim_slots},
              open(os.path.join(build_dir, "car.json"), "w"), indent=1)
    json.dump(rims, open(os.path.join(build_dir, "rims.json"), "w"), indent=1)
    print("total %d rims, %d meshes, %d textures -> %s" % (len(rims), len(all_meshes), len(all_textures), build_dir))


if __name__ == "__main__":
    main()
