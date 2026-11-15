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
EXTRA_ENTRY = "scripts/startup/touch_modeling.py"


def install(decoded: Path, addon: Path, extra: Path | None = None) -> Path:
    payload = decoded / "assets" / "blender_runtime.zip"
    if not payload.is_file():
        raise ValueError("Missing upstream assets/blender_runtime.zip")
    source = addon.read_bytes()
    compile(source, str(addon), "exec")
    entries = {ENTRY: source}
    if extra is not None:
        probe = extra.read_bytes()
        compile(probe, str(extra), "exec")
        entries[EXTRA_ENTRY] = probe

    with ZipFile(payload, "r") as zf:
        names = zf.namelist()
        if any(entry in names for entry in entries):
            raise ValueError("Refusing to overwrite upstream module")
        if not any(n.startswith("scripts/startup/") for n in names):
            raise ValueError("Upstream runtime has no scripts/startup directory")
        before = {i.filename: (i.CRC, i.file_size, i.compress_size) for i in zf.infolist()}

    with ZipFile(payload, "a", compression=ZIP_DEFLATED, compresslevel=6) as zf:
        for name, contents in entries.items():
            zf.writestr(name, contents)

    with ZipFile(payload, "r") as zf:
        for name, contents in entries.items():
            if zf.read(name) != contents:
                raise ValueError("Startup module not copied into runtime: " + name)
        after = {i.filename: (i.CRC, i.file_size, i.compress_size) for i in zf.infolist()}
        if len(after) != len(before) + len(entries):
            raise ValueError("Unexpected runtime archive entry count")
        for filename, original in before.items():
            if after.get(filename) != original:
                raise ValueError("Blender runtime archive entry changed: " + filename)

    print("Bundled optional startup scripts:", ", ".join(entries))
    return payload


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit("Usage: patch_runtime.py <apktool-folder> <safe_edit.py> [touch_modeling.py]")
    install(Path(sys.argv[1]), Path(sys.argv[2]),
            Path(sys.argv[3]) if len(sys.argv) == 4 else None)
