#!/usr/bin/env bash
# Refuse unrecognized upstream ELF. Private hook for renderdiv and idle polling.
set -Eeuo pipefail
decoded="${1:?decoded APK dir}"
clang="${2:?Android NDK clang path}"
libdir="$decoded/lib/arm64-v8a"
blender="$libdir/libblender.so"
shim="$libdir/librenderdiv_shim.so"
test -f "$blender"
test -x "$clang"
render_div="${ANDROID_BLENDER_RENDERDIV:-2}"
if [[ "$render_div" != "1" && "$render_div" != "2" && "$render_div" != "3" && "$render_div" != "4" ]]; then
  echo "Invalid renderdiv; use 1, 2, 3 or 4" >&2
  exit 1
fi
command -v patchelf >/dev/null
python3 scripts/patch_blender_elf.py "$blender"
"$clang" -std=c11 -DMOBILE_RENDER_DIVISOR="$render_div" -shared -O2 -fPIC -fvisibility=hidden \
  -Wl,--no-undefined -Wl,-soname,librenderdiv_shim.so \
  -o "$shim" native/renderdiv_shim.c -landroid
patchelf --add-needed librenderdiv_shim.so "$blender"
for symbol in blender_renderdiv_get blender_pollOnce; do
  readelf -Ws "$blender" | grep -E "UND ${symbol}$"
  readelf -Ws "$shim" | grep -E " ${symbol}$"
done
readelf -d "$blender" | grep -F librenderdiv_shim.so
readelf -d "$shim" | grep -F libandroid.so
if readelf -Ws "$blender" | grep -E '__system_property_get@|ALooper_pollOnce@'; then
  echo "Original imported symbol still exists" >&2
  exit 1
fi
echo "Validated renderdiv=$render_div and Android adaptive-idle shim."
