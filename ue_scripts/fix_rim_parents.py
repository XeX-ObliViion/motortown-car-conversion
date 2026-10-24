# Every build's paintable texture slots (car.json paintable_texture_slots) -> MI parent = that car's M_PaintTex.
# build_car's own assignment didn't stick on some builds (PS rims, PS car wheels stayed on M_Sketchfab_Base).
import unreal, json, os, glob
EAL = unreal.EditorAssetLibrary; MEL = unreal.MaterialEditingLibrary
out = []
only = os.environ.get("PSCAR_ONLY")
for cj in glob.glob("C:/Users/noust/mt-work/build/*/car.json"):
    car = json.load(open(cj))
    slots = car.get("paintable_texture_slots") or []
    name = car.get("car")
    if not slots or not name or (only and name != only):
        continue
    folder = "/Game/Cars/Models/" + name
    pt = unreal.load_asset(folder + "/M_PaintTex")
    if pt is None:
        out.append("%s: no M_PaintTex" % name); continue
    fixed = 0
    for s in slots:
        mi = unreal.load_asset(folder + "/MI_" + s.replace("Tex_", ""))
        if not isinstance(mi, unreal.MaterialInstanceConstant):
            continue
        if mi.get_editor_property("parent") != pt:
            mi.modify(); MEL.set_material_instance_parent(mi, pt)
            EAL.save_asset(folder + "/MI_" + s.replace("Tex_", ""), only_if_is_dirty=False); fixed += 1
    out.append("%s: %d of %d reparented" % (name, fixed, len(slots)))
open("C:/Users/noust/mt-work/build/fix_rim_parents.txt", "w").write("\n".join(out))
unreal.SystemLibrary.quit_editor()
