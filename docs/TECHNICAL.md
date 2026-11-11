# Architecture and next technical checkpoints

## Current packaging approach

Original arm64 native Blender 5.3 Alpha Lite APK -> SHA-256 verification -> Apktool resource/manifest decode -> minSdkVersion 30 -> aapt2 rebuild -> zipalign -> apksigner -> APK validation -> GitHub artifact / prerelease. Original application ID and entry Activity stay unchanged; the user opens Blender directly from the home screen.

This is **not** a source-level Android 11 port. Its purpose is to determine whether the existing native engine happens to tolerate API 30 despite being built for API 31. The Android 11 prerequisite mismatch is intentionally not hidden.

## Runtime issues requiring real testing

1. \`adb install\` must succeed on Android 11.
2. \`adb logcat -c\`, launch, then capture \`adb logcat -d -v time\`; look for linker "cannot locate symbol", missing platform APIs, permissions, Vulkan instance/device errors and Java exceptions.
3. If Blender writes a startup log, retrieve \`Download/blender-startup.log\`.
4. Prove the 3D viewport, basic object creation/editing, viewport orbit, and saving/reopening a \`.blend\` file.
5. Mali-G76 MC4 driver and memory limits must be assessed on physical device; a CI emulator cannot validate the actual GPU.

## If API30 runtime crashes

Do **not** keep editing only the manifest. Fork/pin the upstream Blender source and Android dependency set, lower \`ANDROID_PLATFORM\` / Gradle minSdk to API 30, compile native libraries against the API 30 Bionic/NDK symbol set, adjust any API 31-only Android calls behind runtime guards, and validate GPU behavior on target hardware. The upstream build currently uses a large dependency prefix (tens of GB) and NDK r30+; this is a separate substantial cross-compilation effort.

## Key policy

All changes go to \`main\`. No RustBlend, IMATSTUDY or IMATSTUDYY code is imported or touched. Previous \`Cursor-deneme\` main contained only a 15-byte placeholder README and is replaced by this clean structure.

## Security and integrity

- Upstream alpha4 lite SHA-256: \`5d05835e52377c7d987145b6c35a944804c88e32e114fd53ede4c36edea20ce1\`.
- APKTool version pinned at 2.12.1.
- No downloaded binaries or signing credentials are committed to Git.
- Without repository signing secrets, workflow creates a fresh self-signed test certificate per run. Upgrading test APKs requires the same signing certificate; otherwise uninstall before reinstalling.
- Do not treat installability as proof of compatibility.
