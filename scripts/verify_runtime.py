#!/usr/bin/env python3
"""Fail CI if a rebuilt/signed APK silently drops Mobile Speed from Blender's runtime."""
import io
from pathlib import Path
from zipfile import ZipFile
import hashlib
import sys

ENTRY = "scripts/startup/mobile_speed.py"
ASSET = "assets/blender_runtime.zip"


def verify(apk: Path, module: Path) -> None:
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
    print("APK contains the tested Mobile Speed module:",
          hashlib.sha256(source).hexdigest())


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit("Usage: verify_runtime.py <APK> <module.py>")
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
