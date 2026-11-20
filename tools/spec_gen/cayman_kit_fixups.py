"""after add_body_kits_mw on cars/mw_cayman.json: exact seams (x_clip) on every x_range cut - centroid cuts left
saw-tooth gaps / missing triangles along the kit seams (user 2026-11-19) - and the skirts lifted 0.6 cm off the stock
body (Elise pattern) so the kit panels don't z-fight with the body underneath."""
import json, sys
p = sys.argv[1] if len(sys.argv) > 1 else "cars/mw_cayman.json"
s = json.load(open(p))
n = 0
for name, m in s["meshes"].items():
    for part in m.get("parts", []):
        if isinstance(part, dict) and part.get("x_range"):
            part["x_clip"] = True; n += 1
    if name.startswith("Aero_SideSkirt_"):
        # the kits' own wheel-well liners (Bottom) sat on the stock liners in Body: flicker in the wells (KIT02-04)
        m["drop_slots"] = sorted(set(m.get("drop_slots", [])) | {"Bottom"})
        m["lift"] = {"prefix": "CAYMANS", "parts": ["KIT00_BODY"], "off": 0.6, "box": [-300, 0, -50, 300, 200, 200],
                     "edge": 2.0, "depth": 1.0}
# widebody (KIT05): its rear haunch above the tail lamp lies within 1 cm of the stock panel in patches, so
# drop_coincident cut it into a ragged step between flare and stock body (user 2026-11-19) -> keep it whole there
for name, m in s["meshes"].items():
    if name == "Aero_SideSkirt_KIT05":
        for part in m["parts"]:
            dc = part.get("drop_coincident_with")
            if dc:
                dc["keep_boxes"] = [[-183, 55, 30, -120, 115, 95], [-183, -115, 30, -120, -55, 95]]
# kit wheel-well liners are MISC (like the stock ones in Body): drop the kits' MISC inside the four wells
skirts = [k for k in s["meshes"] if k.startswith("Aero_SideSkirt_")]
s["slot_boxes"] = [b for b in s.get("slot_boxes", []) if not b.get("kit_wells")] + [
    {"meshes": skirts, "from": "Tex_CAYMAN_MISC", "to": "Tex_CAYMAN_MISC", "drop": True, "abs_y": True, "kit_wells": True,
     "box": box} for box in ([58, 50, -5, 142, 102, 64], [-184, 50, -5, -96, 102, 64])]
json.dump(s, open(p, "w"), indent=1)
print("x_clip on %d cuts; skirts lifted" % n)
