"""Most Wanted (2005 / Rework IV) body kits -> Motor Town aero parts.

MW models each body kit as a WHOLE body (<CAR>_KIT00_BODY .. KIT0n_BODY, bumpers included), plus STYLEnn_HOOD hoods
and KIT00/STYLEnn spoilers. Motor Town wants separate garage pieces, so every body is cut by x planes:
  * FrontBumper_<KIT>  = <KIT>_BODY ahead of x = front_split (KIT00 = the stock bumper),
  * RearBumper_<KIT>   = <KIT>_BODY behind x = rear_split,
  * SideSkirt_<KIT>    = <KIT>_BODY between the splits, minus everything that lies on the stock body (drop_coincident_with
                         KIT00_BODY): the kit's own skirts / flares; the stock middle stays in Body,
  * Bonnet_<STYLE>     = KIT00_HOOD (stock) and each STYLEnn_HOOD,
  * RearWing_<STYLE>   = KIT00_SPOILER (stock) and STYLEnn_SPOILER*, shifted by -RearWing socket (as for ProStreet wings).
Edits the spec in place (back it up first). Spec keys: "mw_kits": {"front_split": x, "rear_split": x}.
usage: add_body_kits_mw.py <car_spec.json>"""
import json, os, re, sys


def main():
    path = sys.argv[1]
    spec = json.load(open(path))
    base = spec["prefix"]                                   # e.g. BMWM3GTR (MW files: <CAR>_<PART>_A.dae)
    geo = os.path.expanduser(spec["geometry_dir"])
    files = set(os.listdir(geo))
    have = lambda part: "%s_%s_A.dae" % (base, part) in files
    cfg = spec["mw_kits"]
    F, R = cfg["front_split"], cfg["rear_split"]
    kits = sorted({m.group(1) for f in files for m in [re.match(r"%s_(KIT\d\d)_BODY_A\.dae$" % base, f)] if m})
    hoods = sorted({m.group(1) for f in files for m in [re.match(r"%s_(STYLE\d\d)_HOOD_A\.dae$" % base, f)] if m})
    wings = sorted({m.group(1) for f in files for m in [re.match(r"%s_(STYLE\d\d_SPOILER(?:_CF)?)_A\.dae$" % base, f)] if m})
    # Body keeps only the stock middle; stock hood and spoiler become garage parts
    body = spec["meshes"]["Body"]["parts"]
    out = []
    for p in body:
        name = p if isinstance(p, str) else p["part"]
        if name in ("KIT00_HOOD", "KIT00_SPOILER"):
            continue
        if name == "KIT00_BODY":
            p = {"part": "KIT00_BODY", "x_range": [R, F]}
        out.append(p)
    spec["meshes"]["Body"]["parts"] = out
    spec["meshes"] = {k: v for k, v in spec["meshes"].items() if not k.startswith("Aero_")}
    rows, defaults = [], {}
    car = spec["car"]

    def add(slot, kit, parts, label):
        mesh = "Aero_%s_%s" % (slot, kit)
        spec["meshes"][mesh] = {"parts": parts, "aero": True}
        rows.append({"row": "%s_%s_%s" % (car, slot, kit), "slot": slot, "part_type": slot, "mesh": mesh, "display_name": label})

    dc = {"parts": ["KIT00_BODY"], "prefix": base, "tol": 1.0}
    for kit in kits:
        n = int(kit[3:])
        label = "Stock" if n == 0 else "Kit %d" % n
        add("FrontBumper", kit, [{"part": kit + "_BODY", "x_range": [F, 99999]}], label + " Front Bumper")
        add("RearBumper", kit, [{"part": kit + "_BODY", "x_range": [-99999, R]}], label + " Rear Bumper")
        if n:
            add("SideSkirt", kit, [{"part": kit + "_BODY", "x_range": [R, F], "drop_coincident_with": dc}], label + " Side Skirts")
    defaults["FrontBumper"] = "%s_FrontBumper_KIT00" % car
    defaults["RearBumper"] = "%s_RearBumper_KIT00" % car
    if have("KIT00_HOOD"):
        add("Bonnet", "KIT00", [{"part": "KIT00_HOOD"}], "Stock Hood")
        defaults["Bonnet"] = "%s_Bonnet_KIT00" % car
    for st in hoods:
        add("Bonnet", st, [{"part": st + "_HOOD"}], "Hood %d" % int(st[5:]))
    sock = next((x for x in spec["sockets"]["Body"] if x["name"] == "RearWing"), {"loc": [0, 0, 0]})
    off = [-v for v in sock["loc"]]
    if have("KIT00_SPOILER"):
        add("RearWing", "STOCK", [{"part": "KIT00_SPOILER", "offset": off}], "Stock Wing")
        defaults["RearWing"] = "%s_RearWing_STOCK" % car
    for w in wings:
        add("RearWing", w, [{"part": w, "offset": off}], "Wing %d%s" % (int(w[5:7]), " (Carbon)" if w.endswith("_CF") else ""))
    spec["aero_parts"] = rows
    spec.setdefault("part_overrides", {}).update(defaults)
    spec["not_optional_part_types"] = ["FrontBumper", "RearBumper", "Bonnet"]
    json.dump(spec, open(path, "w"), indent=1)
    print("%s: %d kit parts (%d bodies, %d hoods, %d wings), defaults %s" % (car, len(rows), len(kits), len(hoods),
                                                                          len(wings), defaults))


if __name__ == "__main__":
    main()
