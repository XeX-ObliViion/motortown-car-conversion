#!/bin/sh
# Build one car's meshes in the hidden full editor; retries the sporadic exit 127 (editor not launched, empty log).
# usage: ue_build.sh <BUILD_NAME e.g. MW_M3GTR>
for try in 1 2 3; do
  PSCAR_BUILD_DIR=C:/Users/noust/mt-work/build/$1 PSCAR_QUIT=1 /c/UE/UE_5.5/Engine/Binaries/Win64/UnrealEditor.exe C:/UE/Projects/MotorTown/MotorTown.uproject -ExecutePythonScript="C:/UE/Projects/MotorTown/Scripts/build_car.py" -unattended -nop4 -nosplash -RenderOffscreen > /c/Users/noust/mt-work/build/$1_build.log 2>&1
  rc=$?
  if [ $rc -ne 127 ]; then
    echo "$1 build $rc (try $try)"
    # paintable texture slots: make sure their MIs really use M_PaintTex (build_car's assignment didn't always stick)
    PSCAR_ONLY=$1 /c/UE/UE_5.5/Engine/Binaries/Win64/UnrealEditor.exe C:/UE/Projects/MotorTown/MotorTown.uproject -ExecutePythonScript="C:/UE/Projects/MotorTown/Scripts/fix_rim_parents.py" -unattended -nop4 -nosplash -RenderOffscreen > /dev/null 2>&1
    exit $rc
  fi
  sleep 5
done
echo "$1 build failed 3x (127)"; exit 127
