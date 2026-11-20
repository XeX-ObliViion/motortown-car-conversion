# Every wheel mesh (/Game/Cars/Parts/Wheels) of every build: any slot whose material derives from the game's
# M_Sketchfab_Base (no skeletal/instanced usage -> plain white in the cooked game, 2026-11-14) is reparented to that
# car's M_PaintTex, which gets the usage flags. Writes build/fix_wheel_mats.txt.
import unreal, json, os, glob, re
EAL = unreal.EditorAssetLibrary; MEL = unreal.MaterialEditingLibrary
out, flagged = [], set()


def base_of(m):
    while isinstance(m, unreal.MaterialInstance):
        m = m.get_editor_property("parent")
    return m


for cj in glob.glob("C:/Users/noust/mt-work/build/*/car.json"):
    car = json.load(open(cj))
    name = car.get("car")
    wheels = [m for m in car.get("meshes", []) if m.get("dest") == "/Game/Cars/Parts/Wheels"]
    if not name or not wheels:
        continue
    pt = unreal.load_asset("/Game/Cars/Models/%s/M_PaintTex" % name)
    if pt is None:
        out.append("%s: NO M_PaintTex" % name); continue
    if name not in flagged:   # our own wheel-capable masters (M_TexMasked: rim badges) get the usage flags
        for mat in (pt, unreal.load_asset("/Game/Cars/Models/%s/M_TexMasked" % name)):
            if mat is None:
                continue
            mat.set_editor_property("used_with_skeletal_mesh", True)
            mat.set_editor_property("used_with_instanced_static_meshes", True)
            MEL.recompile_material(mat)
            EAL.save_asset(mat.get_path_name().split(".")[0], only_if_is_dirty=False)
        flagged.add(name)
    fixed = bad = 0
    for w in wheels:
        sm = unreal.load_asset("/Game/Cars/Parts/Wheels/" + w["name"])
        if sm is None:
            out.append("%s: mesh %s missing" % (name, w["name"])); continue
        for sl in sm.get_editor_property("static_materials"):
            mi = sl.get_editor_property("material_interface")
            b = base_of(mi)
            bn = b.get_name() if b else "None"
            if bn == "M_Sketchfab_Base" and isinstance(mi, unreal.MaterialInstanceConstant):
                p = mi.get_path_name().split(".")[0]
                mi.modify(); MEL.set_material_instance_parent(mi, pt)
                rubber = re.search(r"TIRE|TYRE|RUBBER|TREAD", p, re.I) is not None
                MEL.set_material_instance_scalar_parameter_value(mi, "Metallic", 0.0 if rubber else 0.6)
                MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", 0.85 if rubber else 0.35)
                EAL.save_asset(p, only_if_is_dirty=False); fixed += 1
            elif bn not in ("M_PaintTex", "M_TexMasked", "M_Body", "M_Palette") and not bn.startswith("M_Body"):
                bad += 1; out.append("  %s %s: base %s" % (w["name"], sl.get_editor_property("material_slot_name"), bn))
    out.append("%s: %d wheel slots moved to M_PaintTex, %d other bases" % (name, fixed, bad))
open("C:/Users/noust/mt-work/build/fix_wheel_mats.txt", "w").write("\n".join(out))
unreal.SystemLibrary.quit_editor()
