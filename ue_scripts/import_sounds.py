"""Import engine-sound loops (WAV) as looping SoundWaves for a converted car's engine.
Env: PSCAR_SOUND_DIR (folder of <name>.wav), PSCAR_SOUND_DEST (e.g. /Game/Cars/Parts/Engine/Sound/PS_997TT),
PSCAR_QUIT=1 to close the editor afterwards. Run in the full editor like build_car.py."""
import os
import unreal

AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary


def main():
    src, dest = os.environ["PSCAR_SOUND_DIR"], os.environ["PSCAR_SOUND_DEST"]
    for f in sorted(os.listdir(src)):
        if not f.lower().endswith(".wav"):
            continue
        name = os.path.splitext(f)[0]
        if EAL.does_asset_exist(dest + "/" + name):
            EAL.delete_asset(dest + "/" + name)
        t = unreal.AssetImportTask()
        t.filename = os.path.join(src, f); t.destination_path = dest; t.destination_name = name
        t.automated = True; t.replace_existing = True; t.save = True
        AT.import_asset_tasks([t])
        w = unreal.load_asset(dest + "/" + name)
        w.set_editor_property("looping", True)
        EAL.save_loaded_asset(w)
        unreal.log_warning("[PSSOUND] imported %s/%s (%.2f s)" % (dest, name, w.get_editor_property("duration")))
    unreal.log_warning("[PSSOUND] DONE")
    if os.environ.get("PSCAR_QUIT"):
        unreal.SystemLibrary.quit_editor()


main()
