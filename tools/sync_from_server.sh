#!/bin/sh
# Pull newer mod paks from the Bisect server into the local copies (the user's friend also updates the server).
#   sh sync_from_server.sh          -> report only
#   sh sync_from_server.sh --pull   -> download every server pak with a different size, or uploaded 30+ min after our copy
#                                      (our own uploads land a few minutes after the build)
# Server paks are WindowsServer builds: they go to ~/mt-work/build/server and the local server test copy
# (~/mt-server/local), never into the client game (client paks come from the friend's modpack zip).
# Replaced files are kept in ~/mt-work/build/server/replaced/<date>/.
set -e
RC=$(ls -d "$LOCALAPPDATA"/Microsoft/WinGet/Packages/Rclone.Rclone_*/rclone-*/rclone.exe | head -1)
LOCAL=~/mt-work/build/server
TEST=~/mt-server/local/MotorTown/Content/Paks
mkdir -p "$LOCAL"
"$RC" lsl bisect:MotorTown/Content/Paks | while read -r size day time name; do
    case "$name" in MotorTown-WindowsServer.pak) continue ;; esac
    f="$LOCAL/$name"
    lsize=$( [ -f "$f" ] && stat -c %s "$f" || echo 0 )
    lt=$( [ -f "$f" ] && date -r "$f" +%s || echo 0 )
    st=$(date -d "$day ${time%%.*}" +%s)
    if [ "$lsize" != "$size" ] || [ "$st" -gt "$((lt + 1800))" ]; then
        echo "newer on server: $name ($size bytes, $day ${time%%.*}; ours $lsize)"
        if [ "$1" = --pull ]; then
            bak="$LOCAL/replaced/$(date +%Y-%m-%d)"; mkdir -p "$bak"
            [ -f "$f" ] && mv "$f" "$bak/"
            "$RC" copy "bisect:MotorTown/Content/Paks/$name" "$LOCAL/"
            cp "$LOCAL/$name" "$TEST/"
            echo "  pulled $name"
        fi
    fi
done
echo "sync check done"
