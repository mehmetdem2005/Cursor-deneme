#!/usr/bin/env python3
"""Append a safe optional performance menu to bundled Blender runtime scripts.

No existing Blender library / Python package is modified. Archive is validated
before and after append; the rest of the runtime ZIP remains byte-for-byte
unchanged at the per-entry compressed-data level (zipfile append strategy).
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import sys

ENTRY = "scripts/startup/mobile_speed.py"


def install(decoded: Path, addon: Path) -> Path:
    payload = decoded / "assets" / "blender_runtime.zip"
    if not payload.is_file():
        raise ValueError("Missing upstream assets/blender_runtime.zip")
    source = addon.read_bytes()
    compile(source, str(addon), "exec")

    with ZipFile(payload, "r") as zf:
        names = zf.namelist()
        if ENTRY in names:
            raise ValueError("Refusing to overwrite upstream module")
        if not any(n.startswith("scripts/startup/") for n in names):
            raise ValueError("Upstream runtime has no scripts/startup directory")
        before = {i.filename: (i.CRC, i.file_size, i.compress_size) for i in zf.infolist()}

    with ZipFile(payload, "a", compression=ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(ENTRY, source)

    with ZipFile(payload, "r") as zf:
        if zf.read(ENTRY) != source:
            raise ValueError("Performance module was not copied into runtime")
        after = {i.filename: (i.CRC, i.file_size, i.compress_size) for i in zf.infolist()}
        if len(after) != len(before) + 1:
            raise ValueError("Unexpected runtime archive entry count")
        for filename, original in before.items():
            if after.get(filename) != original:
                raise ValueError("Blender runtime archive entry changed: " + filename)

    print("Bundled optional performance menu:", ENTRY)
    return payload


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: patch_runtime.py <apktool-folder> <mobile_speed.py>")
    install(Path(sys.argv[1]), Path(sys.argv[2]))
