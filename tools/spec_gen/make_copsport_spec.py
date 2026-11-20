"""Spec for the Most Wanted Rockport PD5U (MW Remaster CARS/COPSPORT = a modified C6) -> cars/mw_copsport.json.
User 2026-11-15: re-use the MW Corvette port; the PD5U is that car with the cop parts. So: cars/mw_corvette.json
(full-detail C6 body, interior, dials, kits, engine/gearbox rows) + from COPSPORT (same coordinates as CORVETTE, lamps
within 2 cm): the light-bar rear wing (KIT00_DAMAGE0_COP_LIGHTS) and the cop front splitter / rear diffuser bumpers.
Police function (light bar flashing, siren) needs the game's Police base, set up like the PD1U (cars/mw_copghost.json).
usage: python tools/spec_gen/make_copsport_spec.py   (then tools/aim_mirrors.py cars/mw_copsport.json --write)"""
import copy, glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COP = os.path.expanduser("~/nfs-work/db/mwr/COPSPORT").replace("\\", "/")
v = json.load(open(os.path.join(ROOT, "cars", "mw_corvette.json")))
g = json.load(open(os.path.join(ROOT, "cars", "mw_copghost.json")))

s = json.loads(json.dumps(v).replace("MW_CORVETTE", "MW_COPSPORT"))
s["car"] = "MW_COPSPORT"
s["display_name"] = "Rockport PD5U (Most Wanted)"
s["wheel_display_name"] = "Rockport PD5U Stock (Most Wanted)"
s["cost"] = 95000
for k in ("TODO",):
    s.pop(k, None)
# engine / gearbox: the Corvette's own rows (same car), not copies
s.pop("custom_parts", None)
s["part_overrides"]["Engine"] = "MW_CORVETTE_ENG"
s["part_overrides"]["Transmission"] = "MW_CORVETTE_6MT"

# police base, as the PD1U
for k in ("base_vehicle", "base_dir", "base_row"):
    s[k] = g[k]
s["strip_part_slots"] = list(g.get("strip_part_slots", []))
s["base_parts"] = g.get("base_parts", {})

# COPSPORT textures (hash_NAME.dds) next to the Corvette's
cop_tex = {os.path.basename(f).split("_")[0]: os.path.basename(f) for f in glob.glob(COP + "/tex/textures/*.dds")}
for h, slot in (("0xEE80485E", "Tex_COPSPORT_SKIN1"), ("0x644E2504", "Tex_COPSPORT_MISC"), ("0x5B645804", "Tex_COPSPORT_BADGING")):
    s["texture_slots"][h] = slot
    s["texture_sources"][slot] = cop_tex[h]
    s.setdefault("texture_dirs", {})[slot] = COP + "/tex/textures"
s["texture_slots"].setdefault("0x69C032BA", "Tex_MWG_GRILL02")   # MW global grille (in texture_dirs already)
s["texture_slots"].setdefault("0x721AFF7C", "Bottom")

cop = {"prefix": "COPSPORT", "geo": COP + "/geo"}
# light-bar wing on the body; its 96 lens triangles use MW's shared lamp texture 0x721AFF7C (slot Bottom), split by side
s["meshes"]["Body"]["parts"].append(dict(cop, part="KIT00_DAMAGE0_COP_LIGHTS",
                                         note="PD5U light-bar rear wing (MW Remaster COPSPORT)"))
s["meshes"]["Body"].setdefault("uv_split", []).extend([
    {"from": "Bottom", "to": "EmergencyRed", "box": [-9, -9, 9, 9], "box3d": [-240, -80, 70, -180, 0, 110],
     "note": "wing light bar, driver side red (user screenshots 2026-11-15)"},
    {"from": "Bottom", "to": "EmergencyBlue", "box": [-9, -9, 9, 9], "box3d": [-240, 0, 70, -180, 80, 110],
     "note": "wing light bar, passenger side blue"}])
# bumper strobes (user 2026-11-17: flash them like the light bar): copies of the strobe lenses on the Body, lifted
# 0.15 cm off the bumper face, split by side into the Police base's flashing EmergencyRed (driver) / EmergencyBlue
# rear: the diffuser fins' two lens quads each side (COPSPORT MISC = group 1); front: the splitter lamp pods (MW lamp
# texture 0x721AFF7C = group 0)
s["meshes"]["Body"]["parts"] += [
    dict(cop, part="KIT00_DAMAGE0_REAR_BUMPER", groups=[1], only_boxes=[[-226, 42, 36, -214, 54, 55]],
         offset=[-0.15, 0, 0], note="rear bumper strobes"),
    dict(cop, part="KIT00_DAMAGE0_FRONT_BUMPER", groups=[0], only_boxes=[[194, 50, 4, 213, 73, 27]],
         offset=[0.15, 0, 0], note="front splitter strobes")]
s["meshes"]["Body"]["uv_split"].extend([
    {"from": "Tex_COPSPORT_MISC", "to": "EmergencyRed", "box": [-9, -9, 9, 9], "box3d": [-230, -60, 30, -210, 0, 60]},
    {"from": "Tex_COPSPORT_MISC", "to": "EmergencyBlue", "box": [-9, -9, 9, 9], "box3d": [-230, 0, 30, -210, 60, 60]},
    {"from": "Bottom", "to": "EmergencyRed", "box": [-9, -9, 9, 9], "box3d": [190, -80, 0, 216, 0, 30]},
    {"from": "Bottom", "to": "EmergencyBlue", "box": [-9, -9, 9, 9], "box3d": [190, 0, 0, 216, 80, 30]}])
# stock bumpers = the PD5U's cop splitter / diffuser (with their strobes)
# the cop pieces are only the lower half (front up to 51.5 cm, rear up to 57 cm): keep the Corvette's own fascia above
# them (replacing the whole fascia left the area round the headlights / tail lamps see-through, user 2026-11-15);
# the outer corners (|y| > 66) stay Corvette: the cop pieces leave them open (see-through corners, user 2026-11-16)
s["meshes"]["Aero_FrontBumper_KIT00"]["parts"] = [
    dict(v["meshes"]["Aero_FrontBumper_KIT00"]["parts"][0], skip_boxes=[[150, -66, -50, 400, 66, 50]]),
    dict(cop, part="KIT00_DAMAGE0_FRONT_BUMPER")]
s["meshes"]["Aero_RearBumper_KIT00"]["parts"] = [
    v["meshes"]["Aero_RearBumper_KIT00"]["parts"][0],      # whole C6 fascia kept: cutting it left holes beside the fins (user 2026-11-16)
    dict(cop, part="KIT00_DAMAGE0_REAR_BUMPER")]
for a in s.get("aero_parts", []):
    if a["row"] == "MW_COPSPORT_FrontBumper_KIT00":
        a["display_name"] = "PD5U Front Splitter"
    if a["row"] == "MW_COPSPORT_RearBumper_KIT00":
        a["display_name"] = "PD5U Rear Diffuser"

# side mirrors: the Police base places them as components (recentred glass), like the PD1U
for side, comp in (("L", "Left"), ("R", "Right")):
    m = s["meshes"].pop("SideMirror_" + side)
    m["recenter"] = True
    s["meshes"]["SideMirror_" + comp] = m
s.pop("mirror_sockets", None)
for k in ("SideMirror_L", "SideMirror_R"):
    s.get("sockets", {}).pop(k, None)
# Police base: its Dashboard hangs off the SteeringWheel socket; our car-space needle sockets need it unattached
# (as the PD1U; without it the needles were missing, user 2026-11-16)
s["dashboard"]["attach_none"] = True
s["mirror_components"] = {"LeftSideMirror_GEN_VARIABLE": "SideMirror_Left", "RightSideMirror_GEN_VARIABLE": "SideMirror_Right"}

# Police-base lamp components: rear blinkers + reverse lamps too
bp = s["blueprint"]; c = bp["components"]
c["BlinkerLight_03_GEN_VARIABLE"] = [-212, 66, 62]
c["BlinkerLight_04_GEN_VARIABLE"] = [-212, -66, 62]
c["ReverseLight_01_GEN_VARIABLE"] = [-215, -30, 45]
c["ReverseLight_02_GEN_VARIABLE"] = [-215, 30, 45]
# PD5U look (user's MW screenshots 2026-11-15): flat black all over, not paintable (a fixed cop finish); the cop
# skin (SKIN1) on the splitter/diffuser/wing end plates black too (it showed black-and-white patches)
BLACK = "Tex_COPSPORT_BLACK"
for k, val in list(s["texture_slots"].items()):
    if val in ("Paint", "Tex_COPSPORT_SKIN1"):
        s["texture_slots"][k] = BLACK
s["texture_sources"][BLACK] = "COPSPORT_FLATBLACK.png"
s["texture_dirs"][BLACK] = COP + "/tex/textures"
s["final_slot_names"].pop("Paint", None)
s["paintable_texture_slots"] = [x for x in s.get("paintable_texture_slots", []) if x != "Tex_COPSPORT_SKIN1"]
for mdef in s["meshes"].values():                          # body-colour interior trim (uv_split "to": Paint)
    for u in mdef.get("uv_split", []) + mdef.get("recolor_boxes", []):
        if u.get("to") == "Paint":
            u["to"] = BLACK
# MW bumpers are one-sided: the rear diffuser was see-through from behind
for m in ("Aero_FrontBumper_KIT00", "Aero_RearBumper_KIT00"):
    s["meshes"][m]["double_sided"] = True
s["note"] = "PD5U = MW Corvette port + COPSPORT cop parts on the Police base (2026-11-15)"
out = os.path.join(ROOT, "cars", "mw_copsport.json")
json.dump(s, open(out, "w"), indent=1)
print("-> %s (%d meshes)" % (out, len(s["meshes"])))
