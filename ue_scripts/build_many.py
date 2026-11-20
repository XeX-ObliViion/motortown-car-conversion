# Run build_car.py for several build dirs in ONE editor session (PSCAR_DIRS = ;-separated), then quit.
import os, unreal
src = open("C:/UE/Projects/MotorTown/Scripts/build_car.py", encoding="utf-8").read()
quit_after = os.environ.pop("PSCAR_QUIT", None)
for d in [x for x in os.environ.get("PSCAR_DIRS", "").split(";") if x]:
    os.environ["PSCAR_BUILD_DIR"] = d
    try:
        exec(compile(src, "build_car.py", "exec"), {"__name__": "build_car"})
        unreal.log("BUILD_MANY ok " + d)
    except Exception as e:
        unreal.log_error("BUILD_MANY FAIL %s: %s" % (d, e))
unreal.SystemLibrary.quit_editor()
