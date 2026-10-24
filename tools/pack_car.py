"""Pack one converted car into a Motor Town mod pak (<Car>_P.pak) and install it.

Collects: the cooked meshes/textures/material instances for the car from the cooking project
(Saved/Cooked/Windows/MotorTown/Content/Cars/Models/<Car>/ and Cars/Parts/Wheels/<Car>_*), never the stand-in
materials under Cars/Materials; plus the edited Blueprint and vehicle tables from make_mt_assets.py.
usage: pack_car.py <car_spec.json> [--install]"""
import json
import os
import shutil
import subprocess
import sys

REPAK = os.path.expanduser("~/tools/repak/bin/repak.exe")
PAKS = "D:/SteamLibrary/steamapps/common/Motor Town/MotorTown/Content/Paks"
# MT_PLATFORM=WindowsServer: pack from the dedicated-server cook into ~/mt-work/build/server (never installed locally)
PLATFORM = os.environ.get("MT_PLATFORM", "Windows")
BUILD = os.path.expanduser("~/mt-work/build") + ("" if PLATFORM == "Windows" else "/server")
os.makedirs(BUILD, exist_ok=True)
COOKED = "C:/UE/Projects/MotorTown/Saved/Cooked/%s/MotorTown/Content" % PLATFORM


def main():
    spec = json.load(open(sys.argv[1]))
    car = spec["car"]
    stage = os.path.join(BUILD, "stage_%s_P" % car)
    shutil.rmtree(stage, ignore_errors=True)
    dst = os.path.join(stage, "MotorTown", "Content")
    n = 0
    # cooked meshes, textures, material instances
    model = os.path.join(COOKED, "Cars/Models", car)
    for dirpath, _, files in os.walk(model):
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), COOKED)
            os.makedirs(os.path.join(dst, os.path.dirname(rel)), exist_ok=True)
            shutil.copy2(os.path.join(dirpath, f), os.path.join(dst, rel)); n += 1
    for folder, prefix in (("Cars/Parts/Wheels", car + "_"), ("Cars/Parts/SteeringWheels", car + ".")):
        src = os.path.join(COOKED, folder)
        for f in os.listdir(src) if os.path.isdir(src) else []:
            if f.startswith(prefix):
                os.makedirs(os.path.join(dst, folder), exist_ok=True)
                shutil.copy2(os.path.join(src, f), os.path.join(dst, folder, f)); n += 1
    # the car's generated Blueprint (make_mt_assets.py over ALL specs writes into pak_PS_Common); the shared tables,
    # composites and custom engines/gearboxes go into PS_Common_P.pak via pack_common.py, not into car paks
    gen = os.path.join(os.path.expanduser("~/mt-work/build"), "pak_PS_Common" + ("" if PLATFORM == "Windows" else "_server"), "MotorTown", "Content")
    mine = os.path.join("Cars", "Models", car) + os.sep
    for dirpath, _, files in os.walk(gen):
        if "_work" in dirpath:
            continue
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), gen)
            if not rel.startswith(mine):
                continue
            os.makedirs(os.path.join(dst, os.path.dirname(rel)), exist_ok=True)
            shutil.copy2(os.path.join(dirpath, f), os.path.join(dst, rel)); n += 1
    bad = [r for r, _, fs in os.walk(dst) for f in fs if "Cars" + os.sep + "Materials" in r]
    if bad:
        raise SystemExit("stand-in materials would be packed: %s" % bad[:3])
    out = os.path.join(BUILD, "%s_P.pak" % car)
    subprocess.run([REPAK, "pack", "--version", "V11", stage, out], check=True)
    print("packed %d files -> %s" % (n, out))
    if "--install" in sys.argv and PLATFORM == "Windows":
        shutil.copy2(out, os.path.join(PAKS, os.path.basename(out)))
        print("installed to", PAKS)


if __name__ == "__main__":
    main()
