"""Import a pop-up headlamp glTF (tools/make_popup.py) as SkeletalMesh + Skeleton + AnimSequence, give it the car's own
materials (from the static Popup mesh build_car made, by slot), check the axes against the car-space bounds, save.
env: PSCAR_POPUP_GLTF (file), PSCAR_POPUP_CAR (e.g. AC_RX7FD), PSCAR_POPUP_EXPECT "cx,cy,cz,ex,ey,ez" (car space), PSCAR_QUIT"""
import os
import unreal

EAL = unreal.EditorAssetLibrary


def log(m):
    unreal.log_warning("[PSPOPUP] " + m)


def main():
    src = os.environ["PSCAR_POPUP_GLTF"]; car = os.environ["PSCAR_POPUP_CAR"]
    dest = "/Game/Cars/Models/%s/Headlight" % car
    if EAL.does_directory_exist(dest):
        EAL.delete_directory(dest)
    t = unreal.AssetImportTask()
    t.filename = src; t.destination_path = dest; t.automated = True; t.save = False; t.replace_existing = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    paths = EAL.list_assets(dest, recursive=True)
    log("imported: %s" % paths)
    skel = anim = None
    for p in paths:
        a = unreal.load_asset(p)
        if isinstance(a, unreal.SkeletalMesh):
            skel = a
        elif isinstance(a, unreal.AnimSequence):
            anim = a
    if not skel or not anim:
        log("FAILED: skeletal mesh %s anim %s" % (skel, anim)); return
    # names the headlight part row points at
    EAL.rename_asset(skel.get_path_name().split(".")[0], dest + "/Headlight_Skel")
    EAL.rename_asset(anim.get_path_name().split(".")[0], dest + "/Headlight_Popup")
    skel = unreal.load_asset(dest + "/Headlight_Skel"); anim = unreal.load_asset(dest + "/Headlight_Popup")
    # materials: the static Popup mesh build_car made carries the car's materials under the final slot names
    st = unreal.load_asset("/Game/Cars/Models/%s/Popup" % car)
    by_slot = {}
    if st:
        for i, sm in enumerate(st.static_materials):
            by_slot[str(sm.material_slot_name)] = sm.material_interface
    # raw glTF slot -> final slot name (the car spec's final_slot_names; PSCAR_POPUP_FINAL as JSON), RX-7 default
    import json
    final = json.loads(os.environ.get("PSCAR_POPUP_FINAL") or '{"Paint": "Body", "Glass": "Window", "HeadFD": "HeadLight"}')
    # skel.materials hands back copies: edit them, then assign the whole list back (and re-read before reusing)
    mats = list(skel.materials)
    for m in mats:
        raw = str(m.material_slot_name)
        name = final.get(raw, raw)
        mi = by_slot.get(name) or by_slot.get(raw)
        m.material_slot_name = name
        if mi:
            m.material_interface = mi
        log("slot %s -> %s (%s)" % (raw, name, mi.get_path_name() if mi else "NO MATERIAL"))
    MEL = unreal.MaterialEditingLibrary
    # materials must be usable on a skeletal mesh, or the cooked game draws the default (plain grey/white):
    # our own materials (lamps) get the usage flag; textured instances of the game's master get a copy on our own
    # skeletal-capable master (the game's M_Body already supports it: the Panther's pods use it)
    master = None
    for m in mats:
        mi = m.material_interface
        if not mi:
            continue
        path = mi.get_path_name()
        if isinstance(mi, unreal.Material) and path.startswith("/Game/Cars/Models/"):
            mi.set_editor_property("used_with_skeletal_mesh", True)
            MEL.recompile_material(mi)
            EAL.save_asset(path.split(".")[0])
            log("skeletal usage on %s" % path)
        elif isinstance(mi, unreal.MaterialInstanceConstant) and mi.get_editor_property("parent") and                 mi.get_editor_property("parent").get_path_name().startswith("/Game/Cars/Models/"):
            # lamp instance on our own lamp material (glows on the HeadLight parameter): flag the parent, keep it
            par = mi.get_editor_property("parent")
            par.set_editor_property("used_with_skeletal_mesh", True)
            MEL.recompile_material(par)
            EAL.save_asset(par.get_path_name().split(".")[0])
            log("skeletal usage on %s (parent of %s)" % (par.get_path_name(), path))
        elif isinstance(mi, unreal.MaterialInstanceConstant) and path.startswith("/Game/Cars/Models/"):
            tex = MEL.get_material_instance_texture_parameter_value(mi, "Base Texture")
            if not tex:
                log("no Base Texture on %s" % path)
                continue
            if master is None:
                mp = dest + "/M_PodTex"
                master = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_PodTex", dest, unreal.Material, unreal.MaterialFactoryNew())
                t = MEL.create_material_expression(master, unreal.MaterialExpressionTextureSampleParameter2D, -500, 0)
                t.set_editor_property("parameter_name", "Base Texture")
                MEL.connect_material_property(t, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
                master.set_editor_property("used_with_skeletal_mesh", True)
                MEL.recompile_material(master)
            name = "MI_Pod_" + str(m.material_slot_name)
            new = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            MEL.set_material_instance_parent(new, master)
            MEL.set_material_instance_texture_parameter_value(new, "Base Texture", tex)
            m.material_interface = new
            log("pod copy %s -> %s (%s)" % (path, name, tex.get_name()))
        else:
            log("left as is: %s (%s)" % (path, type(mi).__name__))
    skel.set_editor_property("materials", mats)
    for m in skel.materials:
        log("final %s = %s" % (m.material_slot_name, m.material_interface.get_path_name() if m.material_interface else None))
    # no physics asset: the Panther's pop-up skeleton has none; ours (made by the importer) would give the part
    # component physics bodies (pods spawned attached but never showed on the car, 2026-11-12)
    pa = skel.get_editor_property("physics_asset")
    skel.set_editor_property("physics_asset", None)
    if pa:
        EAL.delete_asset(pa.get_path_name().split(".")[0])
        log("physics asset removed")
    b = skel.get_bounds()
    log("bounds origin %s extent %s; expected %s" % (b.origin, b.box_extent, os.environ.get("PSCAR_POPUP_EXPECT")))
    log("anim length %.3f s" % anim.get_play_length())
    for p in EAL.list_assets(dest, recursive=True):
        EAL.save_asset(p)
    log("DONE %s" % EAL.list_assets(dest, recursive=True))


main()
if os.environ.get("PSCAR_QUIT") == "1":
    unreal.SystemLibrary.quit_editor()
