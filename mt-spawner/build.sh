#!/usr/bin/env bash
# Builds build/version.dll with the bundled llvm-mingw toolchain.
set -euo pipefail
cd "$(dirname "$0")"

TC="../sr3r-trainer/tools/llvm-mingw-20260922-ucrt-x86_64/bin"
CXX="$TC/x86_64-w64-mingw32-clang++"
CC="$TC/x86_64-w64-mingw32-clang"
IMGUI=../sr3r-trainer/third_party/imgui
MH=../sr3r-trainer/third_party/minhook
OUT=build
mkdir -p "$OUT/obj"

CFLAGS="-O2 -DNDEBUG -DWIN32_LEAN_AND_MEAN -DNOMINMAX -I$IMGUI -I$IMGUI/backends -I$MH/include"
CXXFLAGS="$CFLAGS -std=c++20 -Wall -Wno-unused-function"

objs=()
compile() {  # compile <compiler> <flags> <source>
    local o="$OUT/obj/$(basename "${3%.*}").o"
    if [[ ! -f "$o" || "$3" -nt "$o" || "$3" == src/* ]]; then
        echo "  $3"
        $1 $2 -c "$3" -o "$o"
    fi
    objs+=("$o")
}

echo "Compiling..."
for f in "$MH"/src/buffer.c "$MH"/src/hook.c "$MH"/src/trampoline.c "$MH"/src/hde/hde64.c; do
    compile "$CC" "$CFLAGS" "$f"
done
for f in "$IMGUI"/imgui.cpp "$IMGUI"/imgui_draw.cpp "$IMGUI"/imgui_tables.cpp "$IMGUI"/imgui_widgets.cpp \
         "$IMGUI"/backends/imgui_impl_dx12.cpp "$IMGUI"/backends/imgui_impl_win32.cpp; do
    compile "$CXX" "$CXXFLAGS -Wno-everything" "$f"
done
for f in src/*.cpp; do
    compile "$CXX" "$CXXFLAGS" "$f"
done

echo "Linking $OUT/version.dll"
"$CXX" -shared -o "$OUT/version.dll" "${objs[@]}" -static -s \
    src/version.def -ld3d12 -ldxgi -ld3dcompiler_47 -ldwmapi -lpsapi -luser32 -lgdi32
ls -la "$OUT/version.dll"
