#!/bin/sh
# Rebuild PS_Dealers_P.pak (permanent dealer spots for the ProStreet cars + the NFS dealership) from the CURRENT game files.
# Run after every Motor Town update:  sh rebuild_dealers.sh            (client: installs into the game)
#                                     PLATFORM=server sh rebuild_dealers.sh   (server: ~/mt-work/srvdealers, not installed)
# Steps: pull Jeju_World.umap/.uexp (and the Seoguipo Luxury Cars cell) from the game's pak, clone the spots listed in
# spots.txt, copy the showroom to the Ara dragstrip lot (nfs_dealership/showroom.txt), add its bays + map icon
# (nfs_dealership/spots_nfs.txt from gen_spots.py), relabel the icon, pack, install.
# The game's AES key is read from ~/mt-work/aes.key (kept out of this script on purpose).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
GAME="/d/SteamLibrary/steamapps/common/Motor Town/MotorTown/Content/Paks"
REPAK=~/tools/repak/bin/repak.exe
MP=~/tools/mappatch-bin/mappatch.exe
MAP=MotorTown/Content/Maps/Jeju/Jeju_World
# world-partition cells holding the Seoguipo Luxury Cars showroom (most of it, and two with the last doors and props)
CELLS="9MJDS5G1ANMPZP6AB7AG07IOP 0CQVO96316ODFBXZTYO1EOVIS APG1ASZRGET45TTJPO57GBMLJ"
if [ "$PLATFORM" = server ]; then
    SRCPAK=~/mt-server/local/MotorTown/Content/Paks/MotorTown-WindowsServer.pak; WORK=~/mt-work/srvdealers_build
    export MAPPATCH_SKIP_MID=1   # saved dynamic materials crash the server on load
else
    SRCPAK="$GAME/MotorTown-Windows.pak"; WORK=~/mt-work/dealers
fi
# full mappings (incl. blueprint structs, dumped on the local server with DumpUSMAP): without them the light vendor,
# spotlights and car lift are unreadable raw exports and get left out
USMAP="$(cygpath -w ~/mt-work/MotorTown-full.usmap)"
export DOTNET_ROOT="$(cygpath -w ~/tools/dotnet8)"
w() { cygpath -w "$1"; }
rm -rf "$WORK"; mkdir -p "$WORK/src" "$WORK/tmp" "$WORK/stage/MotorTown/Content/Maps/Jeju"
for ext in umap uexp; do
    "$REPAK" --aes-key "$(cat ~/mt-work/aes.key)" get "$SRCPAK" "$MAP.$ext" > "$WORK/src/Jeju_World.$ext"
    for c in $CELLS; do
        "$REPAK" --aes-key "$(cat ~/mt-work/aes.key)" get "$SRCPAK" "$MAP/_Generated_/$c.$ext" > "$WORK/src/$c.$ext"
    done
done
py -3.13 "$HERE/nfs_dealership/gen_spots.py" > /dev/null
"$MP" clone "$(w "$WORK/src/Jeju_World.umap")" "$USMAP" "$(w "$WORK/tmp/a.umap")" "$(w "$HERE/spots.txt")" | tail -1
prev="$WORK/tmp/a.umap"; n=0
for c in $CELLS; do
    n=$((n + 1))
    "$MP" transplant "$(w "$prev")" "$USMAP" "$(w "$WORK/tmp/t$n.umap")" "$(w "$WORK/src/$c.umap")" "$(w "$HERE/nfs_dealership/showroom.txt")" "NFSD${n}_" | tail -3
    prev="$WORK/tmp/t$n.umap"
done
cp "$prev" "$WORK/tmp/b.umap"; cp "${prev%.umap}.uexp" "$WORK/tmp/b.uexp"
"$MP" clone "$(w "$WORK/tmp/b.umap")" "$USMAP" "$(w "$WORK/tmp/c.umap")" "$(w "$HERE/nfs_dealership/spots_nfs.txt")" | tail -1
"$MP" label "$(w "$WORK/tmp/c.umap")" "$USMAP" "$(w "$WORK/stage/$MAP.umap")" NFSD_MapIcon NFS | tail -2
"$REPAK" pack --version V11 "$WORK/stage" "$WORK/PS_Dealers_P.pak"
if [ "$PLATFORM" = server ]; then
    echo "server pak: $WORK/PS_Dealers_P.pak"
    exit 0
fi
until ! tasklist | grep -qi MotorTown-Win64; do echo "waiting for the game to close..."; sleep 5; done
cp "$WORK/PS_Dealers_P.pak" "$GAME/"
echo "installed PS_Dealers_P.pak"
