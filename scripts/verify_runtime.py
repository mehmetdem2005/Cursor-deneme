#!/usr/bin/env python3
"""Fail CI if a rebuilt/signed APK silently drops Mobile Speed from Blender's runtime."""
import io
from pathlib import Path
from zipfile import ZipFile
import hashlib
import os
import sys

ENTRY = "scripts/startup/mobile_speed.py"
EXTRA_ENTRY = "scripts/startup/touch_modeling.py"
ASSET = "assets/blender_runtime.zip"


def verify(apk: Path, module: Path, extra: Path | None = None) -> None:
    source = module.read_bytes()
    with ZipFile(apk) as outer:
        if ASSET not in outer.namelist():
            raise ValueError("APK missing original Blender runtime ZIP")
        with ZipFile(io.BytesIO(outer.read(ASSET))) as inner:
            if ENTRY not in inner.namelist():
                raise ValueError("Mobile Speed Python module not found in packaged runtime ZIP")
            packed = inner.read(ENTRY)
            if packed != source:
                raise ValueError("Packed module differs from tested source")
            if not any(n.startswith("scripts/startup/bl_ui/") for n in inner.namelist()):
                raise ValueError("Original Blender UI Python scripts missing")
            compile(packed, ENTRY, 'exec')
            guard = os.environ.get('ANDROID_BLENDER_MATERIAL_GUARD', '1') == '1'
            material_ui = inner.read('scripts/startup/bl_ui/properties_material.py')
            if b'classes = (' not in material_ui:
                raise ValueError('Missing material UI registration')
            preview_registered = b'    MATERIAL_PT_preview,' in material_ui.split(b'classes = (', 1)[1]
            if preview_registered == guard:
                raise ValueError('Signed APK contains wrong Material Guard A/B variant')
            if extra is not None:
                assert EXTRA_ENTRY in inner.namelist(), "Missing Touch Diagnostics module"
                probe = extra.read_bytes()
                if inner.read(EXTRA_ENTRY) != probe:
                    raise ValueError("Packaged touch diagnostics differs from tested source")
                compile(probe, EXTRA_ENTRY, 'exec')
    print("APK contains the tested Mobile Speed module:",
          hashlib.sha256(source).hexdigest())


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        raise SystemExit("Usage: verify_runtime.py <APK> <module.py> [touch_module.py]")
    verify(Path(sys.argv[1]), Path(sys.argv[2]),
           Path(sys.argv[3]) if len(sys.argv) == 4 else None)
