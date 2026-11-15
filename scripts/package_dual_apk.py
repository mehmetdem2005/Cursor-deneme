#!/usr/bin/env python3
"""Preserve the v31 release APK byte-for-byte inside a verified dual-APK ZIP."""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED

OLD_NAME = 'Blender-Lite-v31-ORIGINAL.apk'
NEW_NAME = 'Blender-Lite-TOUCH-DIAGNOSTIC-UNVERIFIED.apk'
OLD_SHA256 = 'c0a345b6496a903228932b6dd3425ffdbdf21a7d25b169996c3bd3e4a938f31b'
OLD_SIZE = 203146975

NOTES = """Blender Lite Android 11 — touch diagnostic experiment (NOT A VERIFIED SCALE FIX)

v31 ORIGINAL: byte-for-byte preserved from android11-exp-run-31.
New diagnostic APK: includes source-backed touch behavior probes and a native
numeric Scale comparison. Blender native touch classifier is UNMODIFIED.

Test: create disposable cube, enter Edit Mode, select face, then
View > Edit Mode Touch Diagnostics. First Inspect Selection, then numeric Scale,
then interactive Scale and bounded Event Trace. Logs may be written to
Download/Blender/edit-touch-trace.log if Android storage permits.

Real Redmi Note 8 Pro testing has NOT been performed by GitHub CI. Do not
call the diagnostic APK a working fix. Use logcat/device traces to identify
native input failure before changing native C++ or GPU behavior.

Both APKs share package ID org.blender.blender and cannot be installed side by
side. Signing certificates may differ: BACK UP original .blend assets before
uninstalling or reinstalling any build. Keep original v31/v33 releases.
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
    print('diagnostic APK built (not device verified):', new_sha)
    print('ZIP verified:', args.zip_output)


if __name__ == '__main__':
    main()
