"""Turn a car spec's stock body panels into Motor Town aero parts and add ProStreet's alternative kits.

Motor Town body kits are AeroParts rows (PartType FrontBumper / RearBumper / Bonnet / SideSkirt / Fender / RearWing)
whose Aero.Mesh is a static mesh in CAR space (the Zino's bumper sits at x +195, its spoiler at x -193). ProStreet
models every kit piece in car space too, so each piece converts like any other part.

This script edits the spec in place:
  * removes the stock (KIT00) pieces of every handled slot from the Body mesh,
  * adds one mesh per slot and kit ("Aero_<Slot>_<Kit>", parts read with the kit's own prefix),
  * writes spec["aero_parts"] (rows for make_mt_assets) and default part_overrides (the stock pieces).

usage: add_body_kits.py <car_spec.json>"""
import json
import os
import re
import sys

SLOTS = [  # Motor Town slot/part type, ProStreet pieces (in order), display name
    ("FrontBumper", ["BUMPER_FRONT"], "Front Bumper"),
    ("RearBumper", ["BUMPER_REAR", "BUMPER_REAR_EXTRA", "EXHAUST"], "Rear Bumper"),
    ("Bonnet", ["HOOD"], "Hood"),
    ("SideSkirt", ["SKIRT_LEFT", "SKIRT_RIGHT"], "Side Skirts"),
    ("Fender", ["FENDER_FRONT_LEFT", "FENDER_FRONT_RIGHT"], "Front Fenders"),
]
WINGS = [("STOCK", "SPOILER", "Stock Wing"), ("LIP", "SPOILER_LIP", "Stock Lip Spoiler"),
         ("EVO", "SPOILER_EVO", "Gentera Style 402 Wing"),
         ("DRAG", "SPOILER_DRAG", "Gentera Style 403 Wing"),
         # cars whose wings carry their own engine lid (911): the plain lid as a "no wing" choice
         ("BASE", "UNIVERSAL_SPOILER_BASE", "No Wing (Plain Engine Lid)")]


# real ProStreet names (part_fedata generic_body_as / generic_hood_as / generic_widebody / generic_spoiler_*, decoded
# with LANGUAGES/English_Global.bin; Autosculpt kits 01/03/04/11 follow generic_body_as entries 0..3 in order)
BODY_KITS = {"KIT00": "Stock", "KIT01": "Stock Autosculpt", "KIT03": "Stratospeed Formula 4",
             "KIT04": "Stratospeed Formula 5", "KIT11": "Stratospeed Formula 7", "KITW01": "Stratospeed Widebody",
             "KIT06": "Stratospeed Formula 5",
             "KIT08": "Stratospeed Formula 4", "KIT09": "Stratospeed Formula 5"}   # Shelby '67: KIT08/09/11 in order   # Elise: KIT01/06/11, its middle kit takes the unused Formula 5 name
HOODS = {"KIT00": "Stock", "KIT01": "Araxis Sport", "KIT02": "Araxis Sweeper", "KIT03": "Araxis Blitz",
         "KIT04": "Araxis Impact", "KIT05": "Araxis Impact", "KIT06": "Araxis Impact"}   # Elise hoods are 01/02/03/05: the 4th = Impact


def kit_label(kit, slot=None):
    names = HOODS if slot == "Bonnet" else BODY_KITS
    return names[kit] if kit in names else "Kit %d" % int(kit[3:])


def main():
    path = sys.argv[1]
    spec = json.load(open(path))
    base = spec["prefix"].rsplit("_KIT", 1)[0]                      # 350Z / SUPRA
    geo = os.path.expanduser(spec["geometry_dir"])
    files = set(os.listdir(geo))
    have = lambda kit, piece: "%s_%s_%s_A.dae" % (base, kit, piece) in files
    kits = sorted({m.group(1) for f in files for m in [re.match(r"%s_(KIT\w+?)_(BUMPER|HOOD|SKIRT|FENDER)" % base, f)] if m})
    body = spec["meshes"]["Body"]["parts"]
    body_parts = {p if isinstance(p, str) else p["part"] for p in body}
    # stock parts in any car mesh (doors may be their own meshes, e.g. Vista door components)
    car_parts = {p if isinstance(p, str) else p["part"] for m in spec["meshes"].values()
                 if not m.get("aero") for p in m.get("parts", [])}
    handled = {p for _, pieces, _ in SLOTS for p in pieces} | {"SPOILER"}
    spec["meshes"]["Body"]["parts"] = [p for p in body
                                       if (p if isinstance(p, str) else p["part"]) not in handled]
    spec["aero_parts"] = []
    defaults = {}
    for slot, pieces, label in SLOTS:
        for kit in kits:
            parts = [{"part": pc, "prefix": "%s_%s" % (base, kit)} for pc in pieces if have(kit, pc)]
            shell = kit == "KITW01" and have(kit, "WIDEBODY") and slot in ("RearBumper", "Fender")
            # a widebody with no fender pieces (Elise) still gets a Fender row: the shell's front half
            if not shell and (not parts or not have(kit, pieces[0])):
                continue
            if shell:
                # the widebody shell is a whole widened body: keep only where it differs from the stock body (and the
                # stock doors when they live in Body) and hand its rear half to the widebody rear bumper, its front
                # half to the widebody fenders
                ref = ["BODY"] + [d for d in ("DOOR_LEFT", "DOOR_RIGHT") if d in car_parts and have("KIT00", d)]
                dc = {"parts": ref, "prefix": "%s_KIT00" % base, "tol": 1.0}
                sdc = dict(dc, keep_boxes=spec["widebody_keep_boxes"]) if spec.get("widebody_keep_boxes") else dc
                parts.append({"part": "WIDEBODY", "prefix": "%s_KITW01" % base, "drop_coincident_with": sdc,   # boxes: shell only
                              "x_range": [-9999, 0] if slot == "RearBumper" else [0, 9999]})
                if slot == "Fender":
                    # widened doors (Elise side intakes) when the stock doors are part of Body: off-surface triangles only
                    parts += [{"part": d, "prefix": "%s_KITW01" % base, "drop_coincident_with": dc}
                              for d in ("DOOR_LEFT", "DOOR_RIGHT") if d in body_parts and have(kit, d)]
            mesh = "Aero_%s_%s" % (slot, kit)
            spec["meshes"][mesh] = {"parts": parts, "aero": True}
            row = "%s_%s_%s" % (spec["car"], slot, kit)
            spec["aero_parts"].append({"row": row, "slot": slot, "part_type": slot, "mesh": mesh,
                                       "display_name": "%s %s" % (kit_label(kit, slot), label)})
            if kit == "KIT00":
                defaults[slot] = row
    for code, piece, label in WINGS:
        if not have("KIT00", piece):
            continue
        if code == "BASE" and not spec.get("wing_lid_base"):   # only cars whose wings carry the lid (911)
            continue
        mesh = "Aero_RearWing_%s" % code
        # the game mounts RearWing parts on the Body socket RearWing (its own universal wings are modelled relative to
        # it, so it must sit on the trunk lid); our car-space ProStreet wings are shifted into that socket's space
        sock = next((x for x in spec["sockets"]["Body"] if x["name"] == "RearWing"), {"loc": [0, 0, 0]})
        off = [-v for v in sock["loc"]]
        spec["meshes"][mesh] = {"parts": [{"part": piece, "prefix": "%s_KIT00" % base, "slot": "Paint", "offset": off}],
                                "aero": True}
        row = "%s_RearWing_%s" % (spec["car"], code)
        spec["aero_parts"].append({"row": row, "slot": "RearWing", "part_type": "RearWing", "mesh": mesh,
                                   "display_name": label})
        if code in ("STOCK", "LIP") and spec.get("stock_wing"):
            defaults["RearWing"] = row
    spec.setdefault("part_overrides", {}).update(defaults)
    spec["not_optional_part_types"] = ["FrontBumper", "RearBumper", "Bonnet", "SideSkirt", "Fender"]
    json.dump(spec, open(path, "w"), indent=1)
    print("%s: %d kit parts, defaults %s" % (spec["car"], len(spec["aero_parts"]), defaults))


if __name__ == "__main__":
    main()
