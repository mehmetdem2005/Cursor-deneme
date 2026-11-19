#!/usr/bin/env python3
"""Patch Blender's EXISTING Material Properties UI; retain all other material panels.

This edits one Python source file inside the bundled Blender runtime. It does
not replace C/C++ operators or the Vulkan graphics backend. The material panel
stays native with normal slots, picker and shader settings. Only the + and New
operator entry points are redirected to guarded data API implementations, while
the expensive GPU material preview subpanel is disabled on Android.
"""
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile
import os
import sys

ENTRY = "scripts/startup/bl_ui/properties_material.py"
SLOT_ORIGINAL = """col.operator("object.material_slot_add", icon='ADD', text="")"""
SLOT_UPDATED = """col.operator("wm.material_ui_slot_add", icon='ADD', text="")"""
NEW_ORIGINAL = 'row.template_ID(ob, "active_material", new="material.new")'
NEW_UPDATED = 'row.template_ID(ob, "active_material", new="wm.material_ui_new")'
PREVIEW_ORIGINAL = "    MATERIAL_PT_preview,\n"


def patch_material_source(source):
    if not isinstance(source, str):
        raise TypeError("Material source must be Unicode")
    for text, name in ((SLOT_ORIGINAL, "material slot +"),
                       (NEW_ORIGINAL, "material New"),
                       (PREVIEW_ORIGINAL, "preview class registration")):
        if source.count(text) != 1:
            raise ValueError(f"Unsupported upstream Material UI ({name}): expected once")
    out = source.replace(SLOT_ORIGINAL, SLOT_UPDATED)
    out = out.replace(NEW_ORIGINAL, NEW_UPDATED)
    out = out.replace(PREVIEW_ORIGINAL, "    # Material GPU preview disabled on Android Mali\n")
    compile(out, ENTRY, "exec")
    assert 'EEVEE_MATERIAL_PT_surface' in out and 'MATERIAL_PT_viewport' in out
    assert 'MATERIAL_UL_matslots' in out
    return out


def install(decoded):
    path = Path(decoded) / "assets" / "blender_runtime.zip"
    if not path.is_file():
        raise ValueError("Blender runtime missing")
    with ZipFile(path) as zf:
        original = zf.read(ENTRY).decode("utf-8")
    modified = patch_material_source(original).encode("utf-8")
    # ZipFile in append mode creates duplicate entries; rewrite atomically
    # and verify every other member's uncompressed contents is unchanged.
    fd = None
    tmp = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix="blender-material-", suffix=".zip",
                                delete=False) as handle:
            tmp = Path(handle.name)
        with ZipFile(path, "r") as src, ZipFile(tmp, "w") as dst:
            for info in src.infolist():
                data = modified if info.filename == ENTRY else src.read(info)
                dst.writestr(info, data)
        with ZipFile(path, "r") as before, ZipFile(tmp, "r") as after:
            if before.namelist() != after.namelist():
                raise ValueError("Runtime member list changed")
            if after.read(ENTRY) != modified:
                raise ValueError("Material UI replacement missing")
            for item in before.infolist():
                if item.filename == ENTRY:
                    continue
                if before.read(item) != after.read(item.filename):
                    raise ValueError("Runtime entry changed: " + item.filename)
        os.replace(tmp, path)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()
    print("Patched existing Material Properties UI (not native GPU):", ENTRY)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_material_ui.py <decoded-apk-directory>")
    install(Path(sys.argv[1]))
