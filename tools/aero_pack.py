"""Universal NFS aero pack (generic ProStreet + Most Wanted spoilers) for every ported car.

Generic spoilers in both games are modelled around their own mount point, like Motor Town's universal wings, so one
mesh per spoiler works on every car: RearWing rows mount at each car's Body socket RearWing. Output: a build dir with
meshes + car.json (build_car.py) and the pack spec's aero_parts rows written back into the spec (make_mt_assets.py,
kind "aero_pack": VehicleKeys = spec vehicle_keys, BodyMaterialNames key = spec paint_slot).
Spec "sources": [{tag, dir, scale, match (regex on part names), texture_slots, part_type?, cost?}]
usage: aero_pack.py <pack_spec.json>"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps_to_mt as P   # noqa: E402


def label_ps(pt):          # SPOILER_KIT03_LARGE -> "ProStreet Wing 3 (Large)"
    m = re.match(r"SPOILER_KIT(\d+)_(\w+)", pt)
    return "ProStreet Wing %d (%s)" % (int(m.group(1)), m.group(2).title()) if m else pt


def label_mw(pt):          # SPOILER_STYLE05_HATCH_CF -> "Most Wanted Wing 5 Hatch (Carbon)"
    m = re.match(r"(?:SPOILER|ROOF)_STYLE(\d+)((?:_[A-Z]+)*)$", pt)
    if not m:
        return pt
    rest = [x for x in m.group(2).split("_") if x]
    kind = " ".join(x.title() for x in rest if x != "CF")
    what = "Wing" if pt.startswith("SPOILER") else "Roof Scoop"
    return "Most Wanted %s %d%s%s" % (what, int(m.group(1)), (" " + kind) if kind else "", " (Carbon)" if "CF" in rest else "")


LABELS = {"PSW": label_ps, "MWW": label_mw, "MWR": label_mw}


def main():
    path = sys.argv[1]
    spec = json.load(open(path))
    out_root = os.path.expanduser(spec["out_dir"])
    to_obj, _ = P.axis_map(os.path.dirname(os.path.dirname(out_root)))
    meshes_all, textures_all, rows = [], {}, []
    for src in spec["sources"]:
        geo = os.path.expanduser(src["dir"])
        rx = re.compile(src["match"])
        parts = sorted({f[:-6] for f in os.listdir(geo) if f.endswith("_A.dae") and rx.search(f[:-6])})
        g = {"car": spec["car"], "geometry_dir": geo, "prefix": "", "out_dir": out_root,
             "texture_dir": os.path.join(geo, "textures"), "source_scale": src["scale"], "default_slot": "Bottom",
             "texture_slots": src["texture_slots"], "meshes": {}, "mesh_names": {}}
        lab = LABELS.get(src["tag"], lambda s: s)
        ptype = src.get("part_type", "RearWing")
        for pt in parts:
            mesh = "%s_%s" % (src["tag"], pt)
            pre, part = pt.split("_", 1)                     # ps_to_mt joins prefix_part_lod
            g["meshes"][mesh] = {"parts": [{"part": part, "prefix": pre}]}
            row = {"row": "%s_%s" % (spec["car"], mesh), "slot": ptype, "part_type": ptype, "mesh": mesh,
                   "display_name": lab(pt), "cost": src.get("cost", 2000)}
            if src.get("socket"):
                row["socket"] = src["socket"]
            rows.append(row)
        P.build(g)
        meshes_all += P.write_objs(g, to_obj)
        textures_all.update(P.write_textures(g))
        print("%s: %d parts" % (src["tag"], len(parts)))
    build_dir = os.path.dirname(out_root)
    json.dump({"car": spec["car"], "meshes": meshes_all, "textures": textures_all,
               "final_slot_names": {"Paint": spec.get("paint_slot", "Body_01"), "Glass": "Window"}},
              open(os.path.join(build_dir, "car.json"), "w"), indent=1)
    spec["aero_parts"] = rows
    json.dump(spec, open(path, "w"), indent=1)
    print("%d pack rows, %d meshes -> %s" % (len(rows), len(meshes_all), build_dir))


if __name__ == "__main__":
    main()
