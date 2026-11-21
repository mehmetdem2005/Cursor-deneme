#!/usr/bin/env python3
"""Mali A/B diagnostic: omit GPU-backed Material Properties preview only.

Material creation, node trees, slots, and viewport shading are unaffected.
This is not a Vulkan driver fix.
"""
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile

TARGET = "scripts/startup/bl_ui/properties_material.py"
BEFORE = "    MATERIAL_PT_preview,\n    EEVEE_MATERIAL_PT_context_material,"
AFTER = ("    # Mali A/B: omit GPU-backed properties preview thumbnail.\n"
         "    EEVEE_MATERIAL_PT_context_material,")


def patch_text(raw):
    source = raw.decode("utf-8")
    if source.count(BEFORE) != 1 or source.count(
            "self.layout.template_preview(context.material)") != 1:
        raise ValueError("Unrecognized upstream material UI: refusing patch")
    output = source.replace(BEFORE, AFTER, 1).encode("utf-8")
    compile(output, TARGET, "exec")
    return output


def patch_archive(archive):
    archive = Path(archive)
    with ZipFile(archive) as source:
        names = source.namelist()
        if len(names) != len(set(names)) or names.count(TARGET) != 1:
            raise ValueError("Missing/duplicate material UI entry")
        patch_text(source.read(TARGET))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                dir=archive.parent, prefix="material-guard-", suffix=".zip",
                delete=False) as handle:
            temporary = Path(handle.name)
        with ZipFile(archive) as source, ZipFile(temporary, "w", allowZip64=True) as dest:
            dest.comment = source.comment
            for entry in source.infolist():
                raw = source.read(entry.filename)
                if entry.filename == TARGET:
                    raw = patch_text(raw)
                dest.writestr(entry, raw)
        with ZipFile(archive) as source, ZipFile(temporary) as dest:
            if source.namelist() != dest.namelist():
                raise ValueError("Unexpected runtime entries")
            for name in source.namelist():
                if name != TARGET and source.read(name) != dest.read(name):
                    raise ValueError("Unexpected runtime modification: " + name)
            if b"    MATERIAL_PT_preview," in dest.read(TARGET).split(b"classes = (", 1)[1]:
                raise ValueError("Preview still registered")
        os.replace(temporary, archive)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_material_ui.py <decoded-directory>")
    patch_archive(Path(sys.argv[1]) / "assets/blender_runtime.zip")
    print("[MaterialGuard] Material Properties thumbnail disabled; material editor intact")
