#!/usr/bin/env bash
# Provide renderdiv=2 inside Blender without requiring system privileges.
# STOP on any unexpected upstream ELF signature or linker inconsistency.
set -Eeuo pipefail
decoded="${1:?decoded APK dir}"
clang="${2:?aarch64-linux-android30-clang path}"
export CFLAGS="-O2 -fPIC -fvisibility=hidden"
libdir="$decoded/lib/arm64-v8a"
blender="$libdir/libblender.so"
test -f "$blender"
test -x "$clang"
command -v patchelf >/dev/null
python3 scripts/patch_blender_elf.py "$blender"
"$clang" -shared -O2 -fPIC -Wl,--no-undefined -Wl,-soname,librenderdiv_shim.so \
  -o "$libdir/librenderdiv_shim.so" native/renderdiv_shim.c
patchelf --add-needed librenderdiv_shim.so "$blender"
echo "ELF properties:"
readelf -Ws "$blender" | grep -F blender_renderdiv_get
readelf -d "$blender" | grep -F librenderdiv_shim.so
readelf -Ws "$libdir/librenderdiv_shim.so" | grep -F blender_renderdiv_get
if readelf -Ws "$blender" | grep -q '__system_property_get@'; then
  echo "Old versioned symbol still exists in libblender.so" >&2
  exit 1
fi
if ! readelf -Ws "$blender" | grep -E 'blender_renderdiv_get$' ; then
  echo "Renamed property import is not unversioned" >&2
  exit 1
fi
echo "Verified Blender renderdiv=2 property shim installed (75% fewer buffer pixels, if native path honors the hook)."
