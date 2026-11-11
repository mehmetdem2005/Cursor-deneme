#!/usr/bin/env python3
"""Patch Android 12-only device information fields in the upstream Blender DEX.

Android 11 (API 30) does not define Build.SOC_MANUFACTURER / Build.SOC_MODEL.
The upstream BlenderActivity.publishHardwareNames() reads both and catches
Exception (not NoSuchFieldError), so the activity can die before native init.

We replace only those two field accesses in BlenderActivity smali. We do NOT
claim this resolves any native library / Vulkan compatibility issues.
"""
from pathlib import Path
import sys


UPSTREAM_FIELD_SUBSTITUTIONS = {
    "Landroid/os/Build;->SOC_MANUFACTURER:Ljava/lang/String;":
        "Landroid/os/Build;->MANUFACTURER:Ljava/lang/String;",
    "Landroid/os/Build;->SOC_MODEL:Ljava/lang/String;":
        "Landroid/os/Build;->HARDWARE:Ljava/lang/String;",
}


def patch_smali(root: Path) -> Path:
    matches = sorted(root.glob("smali*/org/blender/blender/BlenderActivity.smali"))
    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one upstream BlenderActivity.smali, got "
            + str(len(matches))
            + ". APK must be decoded with dex processing enabled."
        )
    smali_path = matches[0]
    content = smali_path.read_text(encoding="utf-8")
    if "publishHardwareNames()V" not in content:
        raise RuntimeError("Unexpected BlenderActivity: no publishHardwareNames() method")
    if "onCreate(Landroid/os/Bundle;)V" not in content:
        raise RuntimeError("Unexpected BlenderActivity: missing onCreate()")

    for old, new in UPSTREAM_FIELD_SUBSTITUTIONS.items():
        count = content.count(old)
        if count != 1:
            raise RuntimeError(f"Expected one {old!r}, found {count}; do not release unpatched DEX")
        content = content.replace(old, new)

    if any(old in content for old in UPSTREAM_FIELD_SUBSTITUTIONS):
        raise RuntimeError("Unsupported Android API 31 field remains in BlenderActivity")
    smali_path.write_text(content, encoding="utf-8")
    return smali_path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_compat.py <apktool-decoded-directory>")
    path = patch_smali(Path(sys.argv[1]))
    print(f"Patched API 31 SOC fields for Android 11 in {path}")


if __name__ == "__main__":
    main()
