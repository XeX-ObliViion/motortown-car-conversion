# Dump each wheel mesh's material slots -> assigned material (None = engine default, renders grey/white).
import unreal, os
out = open(os.path.join(os.environ.get("TEMP", "C:/Temp"), "wheel_mats.txt"), "w")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_assets_by_path("/Game/Cars/Parts/Wheels", recursive=False):
    if str(a.asset_class_path.asset_name) != "StaticMesh":
        continue
    m = unreal.EditorAssetLibrary.load_asset(str(a.package_name))
    for sm in m.get_editor_property("static_materials"):
        mi = sm.get_editor_property("material_interface")
        parent = ""
        if mi and isinstance(mi, unreal.MaterialInstance):
            p = mi.get_editor_property("parent"); parent = p.get_name() if p else "?"
        out.write("%s\t%s\t%s\t%s\n" % (a.asset_name, sm.get_editor_property("material_slot_name"), mi.get_path_name() if mi else "NONE", parent))
out.close()
unreal.SystemLibrary.quit_editor()
