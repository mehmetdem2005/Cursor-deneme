#!/usr/bin/env python3
"""Read-only checks: exactly which Blender material GPU risks remain in a source tree.

No native build. Never runs a material operator or opens a 3D viewport.
Outputs short risk evidence; does not handle user files or logs.
"""
import argparse
import json
from pathlib import Path
from patch_mobile_shadow_pool import OLD, RELATIVE_PATH

PREVIEW_FILE = "scripts/startup/bl_ui/properties_material.py"
RESOURCE_FILE = "source/blender/gpu/vulkan/vk_resource_pool.cc"

def inspect(root):
    root=Path(root)
    result={"evidence_only": True, "safe_to_install": False,
            "issues":[]}
    cpp=(root/RELATIVE_PATH).read_text(encoding="utf-8")
    panel=(root/PREVIEW_FILE).read_text(encoding="utf-8")
    gpu=(root/RESOURCE_FILE).read_text(encoding="utf-8")
    result["old_6_gib_shadow_gate"]=OLD in cpp
    result["standard_material_add_preserved"]='object.material_slot_add' in panel
    result["standard_material_new_preserved"]='new="material.new"' in panel
    result["eevee_preview_panel"]=("MATERIAL_PT_preview," in panel)
    result["legacy_framebuffer_discard_api"]=(
        "discard_framebuffers_for_view(" in gpu)
    result["newer_framebuffer_retire_api"]=(
        "take_framebuffers_for_view(" in gpu)
    if result["old_6_gib_shadow_gate"]:
        result["issues"].append("8GB phones may retain desktop EEVEE atlas budget")
    if result["eevee_preview_panel"]:
        result["issues"].append("GPU material thumbnail preview remains enabled")
    if result["legacy_framebuffer_discard_api"]:
        result["issues"].append("Older Vulkan image-view lifetime path detected")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("blender_source_root", type=Path)
    args=p.parse_args()
    print(json.dumps(inspect(args.blender_source_root),indent=2,sort_keys=True))


if __name__=="__main__":
    main()
