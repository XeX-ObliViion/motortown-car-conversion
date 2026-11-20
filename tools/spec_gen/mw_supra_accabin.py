"""MW Supra with the AC Supra cabin (user 2026-11-20: "use the interior from the AC supra"; keep it RHD like the AC car).
Run after supra_kit_fixups.py on cars/mw_supra.json. The AC cockpit parts (COCKPIT_HR, STEER_HR, shifter) come in from
the AC geometry, moved by OFF into the MW shell (AC body sits ~11 cm higher: roof 124.3 vs 112.2, rear glass 96.6 vs
84.6; windscreen x matches within 1 cm). MW KIT00_INTERIOR leaves the Body. Gauges / wheel / dash sockets / seats /
eye are the AC Supra's own values shifted by OFF. The 110k-tri AC cockpit makes the Body dense -> Body reduce."""
import json, sys
p = sys.argv[1] if len(sys.argv) > 1 else "cars/mw_supra.json"
s = json.load(open(p)); ac = json.load(open("cars/ac_supra.json"))
OFF = [1.0, 0.0, -11.0]
sh = lambda v: [round(v[k] + OFF[k], 2) for k in range(3)]
shb = lambda b: sh(b[:3]) + sh(b[3:])
AC_GEO, AC_TEX = ac["geometry_dir"], ac["texture_dir"]
src = {"geo": AC_GEO, "prefix": "AC_SUPRA", "xform": {"t": [OFF[0], -OFF[1], OFF[2]]}}

body = s["meshes"]["Body"]
body["parts"] = [q for q in body["parts"] if (q if isinstance(q, str) else q["part"]) != "KIT00_INTERIOR"]
body["parts"] = [q for q in body["parts"] if not (isinstance(q, dict) and q.get("geo") == AC_GEO)]   # re-runnable
body["parts"] += [dict(src, part="COCKPIT_HR", skip_groups=[35, 38, 39, 40, 42],
                       note="AC needles out (game needles; boost needle stays), AC room-mirror glass out"),
                  dict(src, part="STEER_HR"), dict(src, part="SHIFT_BASE"), dict(src, part="SUPRA_INT_SHIFT_BASE")]
body["reduce"] = 0.35
body["drop_boxes"] = [[2.4, -11, 95, 8, 11, 107.8], shb([6, -14, 102, 23, 14, 113.5])]
body["boxes_union"] = True
body["uv_split"] = [u for u in body.get("uv_split", []) if u.get("to") != "Gauges"] + [
    dict(u, box3d=shb(u["box3d"])) for u in ac["meshes"]["Body"]["uv_split"] if u.get("to") == "Gauges"]

# AC interior materials -> AC texture slots (AC slot keys are material names; MW ones are hashes: no clash)
AC_INT = [k for k in ac["texture_slots"] if k.startswith(("supra_interior", "Interior_black", "supra_ext_windows_seam"))]
for k in AC_INT:
    s["texture_slots"][k] = ac["texture_slots"][k]
slots = {ac["texture_slots"][k] for k in AC_INT if ac["texture_slots"][k].startswith("Tex_")}
for t in slots:
    s.setdefault("texture_sources", {})[t] = ac["texture_sources"][t]
    s.setdefault("texture_dirs", {})[t] = AC_TEX
s["masked_texture_slots"] = sorted(set(s.get("masked_texture_slots", [])) | {"Tex_AC_SUPRA_INT_DETAILS"})
s["texture_upscale"] = {"Tex_AC_SUPRA_INT_DETAILS": 2}

# steering wheel, gauges, needles: the AC car's, shifted
e = dict(ac["extract"]["SteeringWheel"]); e.pop("pivot", None); e.pop("tilt_deg", None)
e["center"] = sh(e["center"])
s["extract"] = {"SteeringWheel": e}
s["dashboard"] = {"sockets": [dict(k, loc=sh(k["loc"])) for k in ac["dashboard"]["sockets"]], "parent_socket": "SteeringWheel"}
for k in ("gauge_faces", "gauge_ranges", "needle_color", "emissive_slots"):
    s[k] = ac[k]

# RHD cockpit: AC seats / eye / room mirror, shifted
bp, abp = s["blueprint"], ac["blueprint"]
bp["seats"] = {k: sh(v) for k, v in abp["seats"].items()}
bp["cockpit_camera"] = sh(abp["cockpit_camera"])
bp["components"]["RoomMirror_GEN_VARIABLE"] = sh(abp["components"]["RoomMirror_GEN_VARIABLE"])
bp["component_rotations"]["RoomMirror_GEN_VARIABLE"] = abp["component_rotations"]["RoomMirror_GEN_VARIABLE"]
bp["components"]["FrontDomeLightSlot_GEN_VARIABLE"] = sh(abp["components"]["FrontDomeLightSlot_GEN_VARIABLE"])
s.setdefault("mesh_names", {}).setdefault("SteeringWheel", "MW_SUPRA")
json.dump(s, open(p, "w"), indent=1)
print("AC cabin in: %d AC materials, eye %s" % (len(AC_INT), bp["cockpit_camera"]))
