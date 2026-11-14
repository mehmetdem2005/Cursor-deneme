#!/usr/bin/env python3
"""Preserve the v31 release APK byte-for-byte inside a verified dual-APK ZIP."""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED

OLD_NAME = 'Blender-Lite-v31-ORIGINAL.apk'
NEW_NAME = 'Blender-Lite-v32-PAINT-GUARD.apk'
OLD_SHA256 = 'c0a345b6496a903228932b6dd3425ffdbdf21a7d25b169996c3bd3e4a938f31b'
OLD_SIZE = 203146975

NOTES = """Blender Lite Android 11 experimental

v31 Original: preserved byte-for-byte from android11-exp-run-31.
v32 Paint Guard: one-shot Texture Paint preparation, manual Solid texture
preview, and non-sensitive diagnostic markers. No native Vulkan engine fix.

Both APKs share Android package name org.blender.blender.
They cannot be installed simultaneously as independent apps.
This build may use a new signing certificate, so installing v32 on top of
v31 may fail. BACK UP .blend projects, images and external assets first.
Do not uninstall the previous app until backups are verified.

Texture Paint: select mesh in Object Mode; View > Safe GPU / Rig >
Prepare Texture Paint; then manually enter Texture Paint.
Use Safe Texture Preview only if needed.
Logs may appear at Download/Blender/paint-guard.log (if permitted).
Save painted image separately, not only the .blend file.

No physical Mali-G76 Android 11 Texture Paint test was performed by CI.
If Texture Paint still closes, capture Android logcat/tombstone and
compare empty scene vs 256px image vs actual project.
"""


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def package(old_path, new_path, target, expected_sha=OLD_SHA256,
            expected_size=OLD_SIZE):
    old_path, new_path, target = map(Path, (old_path, new_path, target))
    if not old_path.is_file() or not new_path.is_file():
        raise ValueError('Both actual APK files are required')
    if old_path.stat().st_size != expected_size:
        raise ValueError('v31 APK size changed')
    old_sha = file_sha256(old_path)
    if old_sha.lower() != expected_sha.lower():
        raise ValueError('v31 APK SHA256 mismatch; refusing release')
    new_sha = file_sha256(new_path)
    if old_sha == new_sha:
        raise ValueError('Old and new APK bytes are identical')
    manifest = (f'{old_sha}  {OLD_NAME}\n'
                f'{new_sha}  {NEW_NAME}\n')
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, 'w', compression=ZIP_STORED,
                 allowZip64=True) as archive:
        archive.write(old_path, OLD_NAME)
        archive.write(new_path, NEW_NAME)
        archive.writestr('SHA256SUMS.txt', manifest)
        archive.writestr('INSTALL_NOTES.txt', NOTES)
    with ZipFile(target) as archive:
        assert archive.namelist() == [OLD_NAME, NEW_NAME,
                                      'SHA256SUMS.txt', 'INSTALL_NOTES.txt']
        bad = archive.testzip()
        if bad is not None:
            raise ValueError('Corrupt ZIP member: ' + bad)
        for name, expected in ((OLD_NAME, old_sha), (NEW_NAME, new_sha)):
            digest = hashlib.sha256()
            with archive.open(name) as reader:
                for data in iter(lambda: reader.read(1024 * 1024), b''):
                    digest.update(data)
            if digest.hexdigest() != expected:
                raise ValueError('ZIP member failed SHA256: ' + name)
    return old_sha, new_sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('old_apk')
    parser.add_argument('new_apk')
    parser.add_argument('zip_output')
    args = parser.parse_args()
    old_sha, new_sha = package(args.old_apk, args.new_apk, args.zip_output)
    print('v31 preserved:', old_sha)
    print('v32 built:', new_sha)
    print('ZIP verified:', args.zip_output)


if __name__ == '__main__':
    main()
