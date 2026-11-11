#!/usr/bin/env python3
"""Adapt decoded APK metadata for an Android 11 installation experiment.

Changing the manifest is NOT equivalent to making native Blender Android-11-safe.
"""
from pathlib import Path
import re
import sys


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_sdk.py <decoded-apk-directory>")

    root = Path(sys.argv[1])
    manifest_path = root / "AndroidManifest.xml"
    manifest = manifest_path.read_text(encoding="utf-8")

    updated, replacements = re.subn(
        r'android:minSdkVersion\s*=\s*(["\x27])\d+\1',
        'android:minSdkVersion="30"',
        manifest,
        count=1,
    )
    if not replacements:
        tag = re.search(r"<uses-sdk\b[^>]*>", manifest, re.DOTALL)
        if tag is None:
            # Apktool can omit this tag and place SDK levels exclusively in apktool.yml.
            updated = manifest
        else:
            updated = manifest[:tag.end() - 1] + ' android:minSdkVersion="30"' + manifest[tag.end() - 1:]

    manifest_path.write_text(updated, encoding="utf-8")

    apktool_config = root / "apktool.yml"
    modified_yaml = False
    if apktool_config.exists():
        contents = apktool_config.read_text(encoding="utf-8")
        contents, found = re.subn(
            r'(?m)^(\s*minSdkVersion:\s*)(["\x27]?)\d+\2(\s*)$',
            r"\g<1>'30'\g<3>",
            contents,
            count=1,
        )
        if found:
            apktool_config.write_text(contents, encoding="utf-8")
            modified_yaml = True

    if not (replacements or modified_yaml or re.search(r"<uses-sdk\\b", manifest)):
        raise SystemExit("No SDK information found in manifest or apktool.yml")
    print("Declared minSdkVersion now 30; runtime compatibility remains unverified.")


if __name__ == "__main__":
    main()
