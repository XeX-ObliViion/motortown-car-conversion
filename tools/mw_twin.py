"""Start a Most Wanted twin of a finished ProStreet port (MW body + MW kits, "Option A" 2026-10-30).

Bootstraps with make_spec.py, then copies from the ProStreet spec everything that only depends on the real car and
its position in car space (MW and PS models line up within ~0.6 cm): drivetrain, stance, collision, sockets,
blueprint (seats, eye, lamps, mirror aim), steering-wheel extract box and gauge setup. Lamp/glass material hashes,
signal rules, mirrors and kits still need the per-car checks (see MODLOG, MW Supra).
usage: mw_twin.py <cars/ps_spec.json> <mw:CAR> <cars/mw_out.json>"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = ("wheels", "collision_boxes", "sockets", "part_overrides", "blueprint", "gauge_style", "gauge_ranges",
        "needle_color", "needle_scales", "dashboard", "gauge_faces", "emissive_slots", "texture_upscale", "texture_dirs",
        "texture_gain", "grille_backing", "ai_upscale", "cost", "default_engine")
AERO = ("FrontBumper", "RearBumper", "Bonnet", "SideSkirt", "Fender", "RearWing")


def main():
    ps_path, key, out = sys.argv[1:4]
    base = json.load(open(ps_path))["base_vehicle"]
    subprocess.check_call([sys.executable, os.path.join(HERE, "make_spec.py"), key, base, out])
    ps, s = json.load(open(ps_path)), json.load(open(out))
    for k in COPY:
        if k in ps:
            s[k] = json.loads(json.dumps(ps[k]))
    s.pop("custom_parts", None)                     # the PS twin's engine / gearbox rows are shared
    po = s.get("part_overrides", {})
    for k in AERO:
        po.pop(k, None)                             # add_body_kits_mw.py sets the MW defaults
    # the base car's own skirts / fenders would stay on the MW body (MW 350Z on the Zino: Zino_SideSkirt_01 / Fender_01)
    s["strip_part_slots"] = sorted(set(s.get("strip_part_slots", [])) | {"SideSkirt", "Fender"})
    for k in ("Wheel0", "Wheel1", "Wheel2", "Wheel3"):
        po[k] = s["car"]
    if "extract" in ps:
        s["extract"] = {n: {k: v for k, v in e.items() if k not in ("pivot", "tilt_deg")} for n, e in ps["extract"].items()}
    s["out_dir"] = "C:/Users/noust/mt-work/build/%s/meshes" % s["car"]
    s["display_name"] = ps["display_name"].replace("(ProStreet)", "(Most Wanted)")
    s["wheel_display_name"] = ps.get("wheel_display_name", "Stock").replace("(ProStreet)", "(Most Wanted)")
    s["performance_source"] = "same drivetrain as %s: %s" % (ps["car"], ps.get("performance_source", ""))
    for k, v in ps.get("texture_sources", {}).items():       # shared MW grille / carbon / metal textures
        if k.startswith("Tex_MWG_"):
            s.setdefault("texture_sources", {})[k] = v
    s["masked_texture_slots"] = sorted(set(s.get("masked_texture_slots", [])) | {"Tex_MWG_GRILL01", "Tex_MWG_GRILL02"})
    mwp = ps.get("mw_parts", {})
    cut = next(iter(mwp.values()), {}) if mwp else {}
    if cut:
        s["mw_kits"] = {"front_split": cut["front_cut"], "rear_split": cut["rear_cut"]}
    json.dump(s, open(out, "w"), indent=1)
    assert json.load(open(out))["car"] == s["car"]
    print("%s: copied %s from %s" % (s["car"], [k for k in COPY if k in ps], ps["car"]))


if __name__ == "__main__":
    main()
