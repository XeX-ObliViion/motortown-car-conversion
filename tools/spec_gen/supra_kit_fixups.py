"""MW Supra kits (user 2026-11-20: KIT05 fitment): Cayman/FC fixups - exact seams (x_clip) on every x_range cut,
kit wheel-well liners (Bottom) dropped, KIT05 flare panels kept whole over both arches and along the fender tops
(drop_coincident cut them ragged / left a slit at the hood seam where they run within 1 cm of the stock panel)."""
import json, sys
p = sys.argv[1] if len(sys.argv) > 1 else "cars/mw_supra.json"
s = json.load(open(p))
n = 0
for name, m in s["meshes"].items():
    for part in m.get("parts", []):
        if isinstance(part, dict) and part.get("x_range"):
            part["x_clip"] = True; n += 1
    if name.startswith("Aero_SideSkirt_"):
        m["drop_slots"] = sorted(set(m.get("drop_slots", [])) | {"Bottom"})
KEEP = [[x0, -115 if sy < 0 else 79, 20, x1, -79 if sy < 0 else 115, 85]          # arches 127.7 / -124.5
        for x0, x1 in ((-166, -82), (86, 158)) for sy in (-1, 1)]
# (fender-top keep boxes tried 2026-11-20: z-fight along the hood seam; the seam strip is handled by the lift box below)
for part in s["meshes"].get("Aero_SideSkirt_KIT05", {}).get("parts", []):
    if part.get("drop_coincident_with"):
        part["drop_coincident_with"]["keep_boxes"] = KEEP
json.dump(s, open(p, "w"), indent=1)
print("x_clip on %d cuts" % n)
# KIT05 runs >1 cm clear of the stock fender except at the hood seam, where the 0.6 cm lift raised its inner edge
# above the hood edge (slit + step at the hood corner) -> KIT05 lifted only outboard of the seam strip (|y| > 79)
s = json.load(open(p))
s["meshes"]["Aero_SideSkirt_KIT05"]["double_sided"] = True   # fender vent ridges are open shells (see-through from the side)
s["meshes"]["Aero_SideSkirt_KIT05"]["lift"]["box"] = [-300, 79, -50, 300, 200, 200]
json.dump(s, open(p, "w"), indent=1)
