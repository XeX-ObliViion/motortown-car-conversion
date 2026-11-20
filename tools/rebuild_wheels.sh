# 2026-11-14: wheel slot order (rim 0, lip 1) + lipless rims single picker -> wheels rebuild, tables, cook, pack, install
cd ~/OneDrive/Documents/claude/ps2motortown
B=~/mt-work/build; E=/c/UE/UE_5.5/Engine/Binaries/Win64/UnrealEditor.exe; UE=/c/UE/UE_5.5/Engine/Binaries/Win64/UnrealEditor-Cmd.exe; P=C:/UE/Projects/MotorTown/MotorTown.uproject
DIRS=""
for c in PS_350Z PS_SUPRA PS_ELISE PS_997TT PS_SKYLINE PS_SHELBY67 PS_CHALLENGER71 PS_CHEVELLE PS_VIPER MW_M3GTR MW_993RWB MW_SUPRA MW_VIPER MW_ELISE MW_350Z MW_DIABLOSV MW_COPSUV MW_997TT MW_SKYLINE HEAT_SKYLINE MW_CLIO MW_CORVETTE MW_COPGHOST HEAT_RX7 AC_SUPRA AC_GALLARDO AC_CIVICEG AC_RX7FD AC_UNICORN PS_Rims MW_Rims AC_Rims BNG_Rims; do
  python tools/wheel_mats.py C:/Users/noust/mt-work/build/$c | tail -1
  d=$(python tools/wheels_only.py C:/Users/noust/mt-work/build/$c | tr -d '\r'); DIRS="$DIRS;$d"
done
PSCAR_DIRS="$DIRS" $E $P -ExecutePythonScript="C:/UE/Projects/MotorTown/Scripts/build_many.py" -unattended -nop4 -nosplash -RenderOffscreen > $B/so_many.log 2>&1
L=/c/UE/Projects/MotorTown/Saved/Logs/MotorTown.log; echo "build_many: $(grep -a -c 'BUILD_MANY ok' $L) ok, $(grep -a -c 'BUILD_MANY FAIL' $L) failed"; grep -a "BUILD_MANY FAIL" $L | cut -c1-200
$E $P -ExecutePythonScript="C:/UE/Projects/MotorTown/Scripts/fix_wheel_mats.py" -unattended -nop4 -nosplash -RenderOffscreen > /dev/null 2>&1; grep -v " 0 other\|M_TexMasked" $B/fix_wheel_mats.txt | grep -v "^ " | head -5
$E $P -ExecutePythonScript="C:/UE/Projects/MotorTown/Scripts/dump_wheel_mats.py" -unattended -nop4 -nosplash -RenderOffscreen > /dev/null 2>&1
echo "== wheels whose second slot is not Wheel_01:"; awk -F'\t' '{n[$1]++} n[$1]==2 && $2!="Wheel_01"{print $1, $2}' $TEMP/wheel_mats.txt | cat
echo "== tables, cook, pack"
L2=$(cat tools/ALL_SPECS.txt)
py -3.13 tools/make_mt_assets.py $B/pak_PS_Common $L2 > $B/mt_assets_so.log 2>&1 || { echo FAIL make_mt_assets; tail -5 $B/mt_assets_so.log; exit 1; }
$UE $P -run=cook -targetplatform=Windows -unversioned -cookall -unattended -nop4 -nosplash -nullrhi > $B/cook_so.log 2>&1; grep -E "Success -|Failure -" $B/cook_so.log | tail -1
for s in $L2; do py -3.13 tools/pack_car.py $s 2>&1 | tail -1; done
py -3.13 tools/pack_common.py 2>&1 | tail -1
echo built-waiting-for-game-close
until ! tasklist | grep -qi MotorTown-Win64; do sleep 10; done
G="/d/SteamLibrary/steamapps/common/Motor Town/MotorTown/Content/Paks"
for s in $L2; do c=$(py -3.13 -c "import json;print(json.load(open('$s'))['car'])" | tr -d '\r'); [ -f $B/${c}_P.pak ] && cp $B/${c}_P.pak "$G/"; done
cp $B/PS_Common_P.pak "$G/" && echo done-installed
