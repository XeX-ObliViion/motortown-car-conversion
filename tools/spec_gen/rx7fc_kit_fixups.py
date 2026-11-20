"""after add_body_kits_mw on cars/mw_rx7fc.json (copy of cayman_kit_fixups): exact seams (x_clip) on every x_range cut,
saw-tooth gaps / missing triangles along the kit seams (user 2026-11-19) - and the skirts lifted 0.6 cm off the stock
body (Elise pattern) so the kit panels don't z-fight with the body underneath."""
import json, sys
p = sys.argv[1] if len(sys.argv) > 1 else "cars/mw_rx7fc.json"
s = json.load(open(p))
n = 0
for name, m in s["meshes"].items():
    for part in m.get("parts", []):
        if isinstance(part, dict) and part.get("x_range"):
            part["x_clip"] = True; n += 1
    if name.startswith("Aero_SideSkirt_"):
        # the kits' own wheel-well liners (Bottom) sat on the stock liners in Body: flicker in the wells (KIT02-04)
        m["drop_slots"] = sorted(set(m.get("drop_slots", [])) | {"Bottom"})
        m["lift"] = {"prefix": "RX7FC", "parts": ["KIT00_BODY"], "off": 0.6, "box": [-300, 0, -50, 300, 200, 200],
                     "edge": 2.0, "depth": 1.0}
# widebody (KIT05): its rear haunch above the tail lamp lies within 1 cm of the stock panel in patches, so
# drop_coincident cut it into a ragged step between flare and stock body (user 2026-11-19) -> keep it whole there
for name, m in s["meshes"].items():
    if name == "Aero_SideSkirt_KIT05":
        for part in m["parts"]:
            dc = part.get("drop_coincident_with")
            if dc:
                dc["keep_boxes"] = [[-183, 55, 30, -120, 115, 95], [-183, -115, 30, -120, -55, 95]]
for name, m in s["meshes"].items():   # duplicate lamp-state layers (texture_slots -> Drop) on every mesh
    m["drop_slots"] = sorted(set(m.get("drop_slots", [])) | {"Drop"})
# KIT05 flares: drop_coincident cut the fender panels ragged where they run within 1 cm of the stock panel (Cayman
# widebody lesson, 2026-11-19) -> keep the kit's whole fender panel over both arches (lifted over the stock body)
if "Aero_SideSkirt_KIT05" in s["meshes"]:
    for part in s["meshes"]["Aero_SideSkirt_KIT05"]["parts"]:
        if part.get("drop_coincident_with"):
            part["drop_coincident_with"]["keep_boxes"] = [[x0, sy * 112 if sy < 0 else 52, 22, x1, sy * 52 if sy < 0 else 112, 78]
                                                         for x0, x1 in ((-161, -100), (85, 161)) for sy in (-1, 1)]
# kit wheel-well liners are MISC (like the stock ones in Body): drop the kits' MISC inside the four wells
skirts = [k for k in s["meshes"] if k.startswith("Aero_SideSkirt_")]
s["slot_boxes"] = [b for b in s.get("slot_boxes", []) if not b.get("kit_wells")] + [
    {"meshes": skirts, "from": "Tex_RX7FC_MISC", "to": "Tex_RX7FC_MISC", "drop": True, "abs_y": True, "kit_wells": True,
     "box": box} for box in ([82, 50, -5, 162, 102, 60], [-162, 50, -5, -82, 102, 62])]   # FC arches 122.4 / -121.8
json.dump(s, open(p, "w"), indent=1)
print("x_clip on %d cuts; skirts lifted" % n)
# pop-ups (2026-11-20): the lids / raised pods leave every hood; the Headlight part (mesh Popup) draws them
s2 = json.load(open(p))
for name, m in s2["meshes"].items():
    if name.startswith("Aero_Bonnet_"):
        m["drop_boxes"] = [[165, -72, 10, 212, -36, 70], [165, 36, 10, 212, 72, 70]]; m["boxes_union"] = True
json.dump(s2, open(p, "w"), indent=1)
