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
}
ROLES = ("HEADLIGHT", "BRAKELIGHT", "TIRE", "INTERIOR", "BADGING", "MISC", "ENGINE")


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
            h = sorted(x for x in files.values() if "KIT00_BRAKELIGHT" in x.upper())[0].split("_")[0]
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
    s["meshes"]["Body"]["drop_slots"] = sorted(set(s["meshes"]["Body"].get("drop_slots", [])) | {"LampGlass"})
    json.dump(s, open(path, "w"), indent=1)
    print("mapped %d materials; texture_sources %s" % (len(mats) - len(left), src))
    for k, hs in left:
        print("  unmapped (-> %s): %s %s" % (s.get("default_slot"), k, hs))


if __name__ == "__main__":
    main()
