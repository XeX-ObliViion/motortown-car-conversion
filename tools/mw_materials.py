"""Map a Most Wanted car's materials to Motor Town slots for a MW twin spec (after mw_twin.py).

Reads every <CAR>_*_A.dae: material key (hash "0x..." in older Rework files, a NAME in newer ones) -> the textures its
effect samples. A material is mapped by its texture: the car's own files by role (<CAR>_KIT00_HEADLIGHT_* -> Tex_<C>_HEADLIGHT,
BRAKELIGHT, TIRE, INTERIOR, BADGING, MISC, ENGINE), shared MW textures by the hash table below (learned on the MW Supra /
Viper / M3 GTR). Lamp glass goes to slot LampGlass, which the Body drops (it darkened the lamps). Prints what is left
unmapped (default_slot Bottom). Edits the spec in place.
usage: mw_materials.py <cars/mw_<car>.json>"""
import collections, glob, json, os, re, sys

SHARED = {  # shared MW texture hash -> slot
    "0xA7E6EA53": "HEADLIGHT", "0xA532FC46": "HEADLIGHT",                         # L / R headlamp
    "0x02B52399": "BRAKELIGHT", "0x3617DCFC": "BRAKELIGHT", "0xD947F346": "BRAKELIGHT",
    "0x267D188C": "LampGlass", "0xF68EF19F": "LampGlass", "0x01F40B32": "LampGlass",
    "0x7B220DDF": "Glass", "0xD195BE56": "Glass", "0xE7E4EF49": "Glass",
    "0xCC772AFB": "Paint",            # DOORLINE: body paint with the panel lines (Bottom made big black patches)
    "0xBF30889B": "Trim", "0x1B049702": "Bottom", "0x4C95C6F8": "Bottom", "0xE38806E3": "Bottom",
    "0x03C906EF": "Bottom", "0x7811C147": "Bottom", "0x7811C146": "Bottom", "0x4E8CF857": "Bottom",
    "0xE4CEA024": "Bottom", "0xE4CEA025": "Bottom", "0xBD1F0E0A": "Bottom", "0x721AFF7C": "Bottom",
    "0x69C032BA": "Tex_MWG_GRILL02", "0x69C032B9": "Tex_MWG_GRILL01", "0x68100815": "Tex_MWG_RADIATOR",
    "0x0AB88F5D": "Glass", "0x4CDEBFCA": "Glass", "0x60F8B13C": "Glass",   # side / rear window materials (350Z, 997TT, R34)
    "0x427B4565": "Tex_MWG_INTERCOOLER", "0x8C283C65": "Bottom",
}
ROLES = ("HEADLIGHT", "BRAKELIGHT", "TIRE", "RIM", "INTERIOR", "BADGING", "MISC", "ENGINE")


def main():
    path = sys.argv[1]
    s = json.load(open(path))
    car, geo = s["prefix"], os.path.expanduser(s["geometry_dir"])
    texdir = os.path.expanduser(s["texture_dir"])
    files = {f.split("_")[0].upper(): f for f in os.listdir(texdir)}
    mats = collections.defaultdict(set)
    for f in glob.glob(os.path.join(geo, car + "_*_A.dae")):
        if re.search(r"_(DAMAGE|DECAL)", f):
            continue
        t = open(f, encoding="utf-8", errors="ignore").read()
        eff = {e.group(1): re.findall(r"texture-(0x[0-9A-Fa-f]+)", e.group(0))
               for e in re.finditer(r'<effect id="([^"]+)".*?</effect>', t, re.S)}
        for mt in re.finditer(r'<material id="[^"]+" name="([^"]+)">\s*<instance_effect url="#([^"]+)"', t):
            mats[mt.group(1).replace("TextureMTL-", "")] |= set(eff.get(mt.group(2), []))
    ts, src, left = s["texture_slots"], s.setdefault("texture_sources", {}), []

    def role_slot(role, h=None):
        slot = "Tex_%s_%s" % (car, role)
        if role == "HEADLIGHT":     # the lamp texture (HEADLIGHT_O...), not the HEADLIGHT_G glass
            h = next((x for x in files.values() if "KIT00_HEADLIGHT_O" in x.upper()), "").split("_")[0] or h
        elif role == "BRAKELIGHT":  # ON / OFF can't be told from the truncated names: CHECK the picture (MW Supra: OFF)
            # dump names are truncated (SKYLINE_KIT00_BRAKELIGH): match the stem
            h = (sorted(x for x in files.values() if "KIT00_BRAKELIG" in x.upper()) or [h or ""])[0].split("_")[0]
        src.setdefault(slot, h)
        return slot

    for key, hs in sorted(mats.items()):
        slot = ts.get(key)            # make_spec's guesses (paint) stay
        for h in sorted(hs):
            f = files.get(h.upper(), "")
            role = next((r for r in ROLES if "_" + r in f.upper()), None)
            if role:
                slot = role_slot(role, h)
            elif h in SHARED:
                v = SHARED[h]
                slot = role_slot(v) if v in ROLES else v
            if slot:
                break
        if slot:
            ts[key] = slot
        else:
            left.append((key, sorted(hs)))
    # named materials (newer Rework files: BODY, BODY_LEFT, DOORLINE...) that sample the paint material's texture are
    # paint too (make_spec only guessed one of them); unmapped *_GLASS materials are lamp glass
    paint_tex = {h for k, hs in mats.items() if ts.get(k) == "Paint" for h in hs}
    for key, hs in list(left):
        if hs and set(hs) <= paint_tex:
            ts[key] = "Paint"; left.remove((key, hs))
        elif key.endswith("_GLASS"):
            ts[key] = "LampGlass"; left.remove((key, hs))
    # some files of the same car key their groups by texture hash instead of material name (MW Clio: KIT00_BODY):
    # give each hash its material's slot (make_spec's default-ish Bottom guesses give way)
    for key, hs in mats.items():
        if key in ts:
            for h in hs:
                if h not in ts or (ts[h] == "Bottom" and ts[key] != "Bottom"):
                    ts[h] = ts[key]
    if "Tex_%s_BADGING" % car in ts.values():   # badge atlases carry alpha: unmasked they show as dark squares (MW 997TT)
        s["masked_texture_slots"] = sorted(set(s.get("masked_texture_slots", [])) | {"Tex_%s_BADGING" % car})
    # slot names / lamps / wheel paint the game expects (make_spec's base templates carry another car's names)
    fs = {"Paint": s.get("final_slot_names", {}).get("Paint", "Body"), "Glass": s.get("final_slot_names", {}).get("Glass", "Window")}
    for role, name in (("HEADLIGHT", "HeadLight"), ("BRAKELIGHT", "TailLight"), ("RIM", "Wheel_01"), ("TIRE", "Wheel_01")):
        if "Tex_%s_%s" % (car, role) in ts.values():
            fs["Tex_%s_%s" % (car, role)] = name
    s["final_slot_names"] = fs
    s["lamp_slots"] = {k: v for k, v in (("Tex_%s_HEADLIGHT" % car, "head"), ("Tex_%s_BRAKELIGHT" % car, "tail")) if k in ts.values()}
    wheel_tex = [k for k in fs if fs[k] == "Wheel_01" and k.startswith("Tex_")]
    s["paintable_texture_slots"] = wheel_tex[:1]
    # Body: the brake lamps (make_spec leaves them out for some cars) and no BASE copy of the window glass (z-fight)
    parts = s["meshes"]["Body"]["parts"]
    names = [p if isinstance(p, str) else p.get("part") for p in parts]
    for side in ("LEFT", "RIGHT"):
        n = "KIT00_%s_BRAKELIGHT" % side
        if n not in names and os.path.exists(os.path.join(geo, "%s_%s_A.dae" % (car, n))):
            parts.append(n)
    wins = [n for n in names if n and "WINDOW" in n]
    if "BASE" in names and wins:
        parts[names.index("BASE")] = {"part": "BASE", "drop_coincident_with": {"prefix": car, "parts": wins, "tol": 1.0}}
    s["meshes"]["Body"]["drop_slots"] = sorted(set(s["meshes"]["Body"].get("drop_slots", [])) | {"LampGlass"})
    json.dump(s, open(path, "w"), indent=1)
    print("mapped %d materials; texture_sources %s" % (len(mats) - len(left), src))
    for k, hs in left:
        print("  unmapped (-> %s): %s %s" % (s.get("default_slot"), k, hs))


if __name__ == "__main__":
    main()
