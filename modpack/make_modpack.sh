#!/bin/sh
# Build the friends' modpack zip from the CLIENT paks currently installed in Motor Town (never the server paks).
# Output: OneDrive/Documents/NFS Car Pack/NFS_CarPack.zip (shared link: see memory ps2motortown) (+ README). The user shares it with a private
# OneDrive link; third-party mods (More Tuning, Maja's) are linked in the README, not included.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
PAKS="/d/SteamLibrary/steamapps/common/Motor Town/MotorTown/Content/Paks"
OUT=~/OneDrive/Documents/"NFS Car Pack"
STAGE=~/mt-work/modpack_stage
rm -rf "$STAGE"; mkdir -p "$STAGE/NFS Car Pack" "$OUT"
# zzKitFix_*: the friend's MW kit fitment fixes (override our kit meshes, load last)
for f in "$PAKS"/PS_*_P.pak "$PAKS"/MW_*_P.pak "$PAKS"/NFS_*_P.pak "$PAKS"/zzKitFix_*_P.pak; do
    # the economy pak goes out only when it is on the server too (cargo data must match): INCLUDE_ECONOMY=1
    case "$f" in */NFS_Economy_P.pak) [ "$INCLUDE_ECONOMY" = 1 ] || continue ;; esac
    cp "$f" "$STAGE/NFS Car Pack/"
done
cp "$HERE/README.txt" "$STAGE/NFS Car Pack/README.txt"
# F8 menu (spawner + Tuning tab): UE4SS loader + our overlay + only the MTSpawner Lua mod (none of the user's probes)
W="/d/SteamLibrary/steamapps/common/Motor Town/MotorTown/Binaries/Win64"
M="$STAGE/NFS Car Pack/F8 Menu (copy into Win64)"
SP=~/OneDrive/Documents/claude/mt-spawner
mkdir -p "$M/ue4ss/Mods"
cp "$W/dwmapi.dll" "$SP/build/version.dll" "$M/"
printf '[Menu]
ToggleKey=F8
' > "$M/mt_spawner.ini"
cp "$W/ue4ss/UE4SS.dll" "$W/ue4ss/UE4SS-settings.ini" "$W/ue4ss/LICENSE" "$W/ue4ss/MotorTown-5.5.4-0+UE5-1ba38db4.usmap" "$M/ue4ss/"
cp -r "$W/ue4ss/UE4SS_SDK_Backends" "$M/ue4ss/"
cp -r "$W/ue4ss/Mods/shared" "$W/ue4ss/Mods/Keybinds" "$M/ue4ss/Mods/"
cp -r "$SP/lua/MTSpawner" "$M/ue4ss/Mods/"
printf 'MTSpawner : 1

; Built-in keybinds, do not move up!
Keybinds : 1
' > "$M/ue4ss/Mods/mods.txt"
D=$(date +%Y-%m-%d)
rm -f "$STAGE/NFS_CarPack.zip"
(cd "$STAGE" && /c/Windows/System32/tar.exe -a -c -f "NFS_CarPack.zip" "NFS Car Pack")   # Windows bsdtar: zip, no 2 GB limit
# overwrite in place (never delete): OneDrive keeps the same item, so the shared link keeps working
cat "$STAGE/NFS_CarPack.zip" > "$OUT/NFS_CarPack.zip"
cp "$HERE/README.txt" "$OUT/README.txt"
ls -la "$OUT"
