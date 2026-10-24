"""Wheel-arch skins for a car ported straight from Most Wanted (M3 GTR, 993 RWB...): the body's arch / quarter areas move
into a mandatory Fender slot ("Stock Fenders"), and every MW kit whose shell is widened there gets its own Fender row
("Kit N Widebody") with that kit's complete skin inside the zones. Its bumpers / skirts lose the zones, so a widebody
replaces the stock panel instead of sitting over it (no stock arch / wheel well showing underneath).
Same models on both sides (MW KIT00 vs KITnn), so the zone cut alone joins them edge to edge.
usage: add_arch_fenders.py <cars/<spec>.json>"""
import json, os, re, sys
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from add_mw_parts import samples                     # area-weighted surface samples (MT cm)

spec_path = sys.argv[1]
spec = json.load(open(spec_path))
geo = os.path.expanduser(spec["geometry_dir"])
pre = spec["prefix"]
sc = spec.get("source_scale", 100.0)
wh = spec["wheels"]
ZR = wh.get("radius", 32) + 24.0
ZY = wh.get("half_track", 75) - 30.0
zl = [[wh["front_x"], wh["z"], ZR, ZY], [wh["rear_x"], wh.get("rear_z", wh["z"]), ZR, ZY]]
# zones stop at the bumper cut lines (the stock bumpers' x_range), so bumpers stay whole with any fender option
def _cut(slot, i, dflt):
    for p in spec["meshes"].get("Aero_%s_KIT00" % slot, {}).get("parts", []):
        if isinstance(p, dict) and p.get("x_range"):
            return p["x_range"][i]
    return dflt
XR = [_cut("RearBumper", 1, -9999), _cut("FrontBumper", 0, 9999)]
zkeep, zdrop = {"mode": "keep", "list": zl, "x_range": XR}, {"mode": "drop", "list": zl, "x_range": XR}
spec["arch_zones"] = zl
f = lambda part: os.path.join(geo, "%s_%s_A.dae" % (pre, part))

# the stock body: zones out of the Body mesh, into "Stock Fenders"
for p in spec["meshes"]["Body"]["parts"]:
    if isinstance(p, dict) and p.get("part") == "KIT00_BODY":
        p["zones"] = zdrop
# the stock bumpers / skirts are cut from KIT00_BODY too: their zone parts now come from Stock Fenders
for slot in ("FrontBumper", "RearBumper", "SideSkirt"):
    for p in spec["meshes"].get("Aero_%s_KIT00" % slot, {}).get("parts", []):
        if isinstance(p, dict) and p.get("part") == "KIT00_BODY":
            p["zones"] = zdrop
spec["meshes"]["Aero_Fender_KIT00"] = {"parts": [{"part": "KIT00_BODY", "zones": zkeep}], "aero": True, "double_sided": True}
rows = [r for r in spec.get("aero_parts", []) if not r.get("arch_fender")]
rows.append({"row": "%s_Fender_KIT00" % spec["car"], "slot": "Fender", "part_type": "Fender", "mesh": "Aero_Fender_KIT00",
             "display_name": "Stock Fenders", "arch_fender": True})
nop = spec.setdefault("not_optional_part_types", [])
if "Fender" not in nop:
    nop.append("Fender")
spec.setdefault("part_overrides", {})["Fender"] = "%s_Fender_KIT00" % spec["car"]   # default fitted

# widebody kits
base = cKDTree(samples([f("KIT00_BODY")], sc, step=1.0))
kits = sorted({m.group(1) for x in os.listdir(geo) for m in [re.match(r"%s_(KIT\d\d)_BODY_A\.dae$" % pre, x)] if m and m.group(1) != "KIT00"})
for kit in kits:
    S = samples([f(kit + "_BODY")], sc, step=2.0)
    inz = np.zeros(len(S), bool)
    for x0, z0, r0, y0 in zl:
        inz |= (np.abs(S[:, 1]) >= y0) & ((S[:, 0] - x0) ** 2 + (S[:, 2] - z0) ** 2 <= r0 ** 2)
    frac = float((base.query(S[inz])[0] > 2.0).mean()) if inz.sum() > 50 else 0.0
    wide = frac > 0.25
    print("%s arch zones off the stock body: %.0f%%%s" % (kit, 100 * frac, " -> widebody" if wide else ""))
    if not wide:
        continue
    mesh = "Aero_Fender_%s" % kit
    spec["meshes"][mesh] = {"parts": [{"part": kit + "_BODY", "zones": zkeep}], "aero": True, "double_sided": True}
    lab = next((r["display_name"].rsplit(" ", 2)[0] for r in rows if r.get("mesh", "").endswith("_" + kit)
                and r["slot"] in ("SideSkirt", "FrontBumper")), "Kit %d" % int(kit[3:]))
    rows.append({"row": "%s_Fender_%s" % (spec["car"], kit), "slot": "Fender", "part_type": "Fender", "mesh": mesh,
                 "display_name": "%s Widebody" % lab, "arch_fender": True})
    for slot in ("FrontBumper", "RearBumper", "SideSkirt"):
        m = spec["meshes"].get("Aero_%s_%s" % (slot, kit))
        for p in (m or {}).get("parts", []):
            if isinstance(p, dict) and p.get("part") == kit + "_BODY":
                p["zones"] = zdrop
spec["aero_parts"] = rows
json.dump(spec, open(spec_path, "w"), indent=1)
print("%s: %d arch-fender rows" % (spec["car"], sum(1 for r in rows if r.get("arch_fender"))))
