# Blender Lite — Android 11 compatibility experiment

**Latest build:** The Android 11 experiment now patches two Android 12-only Java fields in BlenderActivity. It still requires real-device testing; native linker and Vulkan compatibility remain unverified.

**Objective:** One APK that opens the real Blender editor directly on an ARM64 Android phone. This is not RustBlend and not IMATStudy. Development is restricted to this repository's \`main\` branch.

## Status — EXPERIMENTAL / NOT DEVICE-VERIFIED

The original [simfeo/blender Android alpha 4](https://github.com/simfeo/blender/releases/tag/android-alpha-4) provides a native Blender 5.3 Alpha application with modeling, sculpting, animation, touch inputs and Vulkan rendering. Its published APK requires **Android 12 / API 31**. This project tests an **Android 11 / API 30** compatibility adaptation by rebuilding the Android APK manifest and resources. It does **not** rebuild or modify Blender's native engine, and cannot guarantee API 30 runtime compatibility or compatibility with any particular GPU.

**No fake screen / web wrapper / redirect:** the APK's launcher is the original Blender Activity and the included binary is real Blender. An APK successfully installing does **not** prove the editor starts or renders correctly.

## Device target

- Redmi Note 8 Pro, Android 11 (API 30), ARM64, Mali-G76 MC4.
- Blender Lite profile for light modeling, not Cycles or other demanding workloads.
- Vulkan device drivers required. Blender alpha 4 may still have rendering problems on older Mali drivers.
- Expected file size is around 194 MiB before re-signing, so allow additional storage.

## Build on GitHub

Every commit to \`main\` triggers [Blender Android 11 experimental APK](.github/workflows/build.yml). After a successful workflow, find the APK in GitHub Actions artifacts or [Releases](../../releases). Download **blender-lite-android11-api30-JAVA-COMPAT-UNVERIFIED.apk** and transfer to the Android phone.

The build validates the upstream SHA-256, changes the declared Android minimum from 31 to 30, reassembles and signs the package, checks for arm64 native libraries, verifies the signature, and confirms the declared minimum is 30. It is an **experimental repack**, not a native port to API 30.

Do not install this over an existing \`org.blender.blender\` APK signed by another publisher: signatures will conflict. Keep separate backups of .blend projects. The default GitHub Actions signing key is temporary, so updating this test APK may require uninstalling an older one. Its test signing key must not be used for a production release.

## What counts as success?

1. The APK builds with valid signature and arm64 payload.
2. Android 11 installs it without \`INSTALL_FAILED_OLDER_SDK\`.
3. Tapping the app icon launches the real Blender UI, not a splash or black screen.
4. A cube can be edited and a .blend file saved/reopened.
5. GPU, touch navigation and shader rendering pass on the actual Mali device.

Only step 1 is automated here. Steps 2–5 require a real Android 11 phone and runtime logs. If the native binary imports API 31-only symbols, changing the manifest will not solve that: the native port must be rebuilt against API 30 and incompatible calls replaced.

## Upstream and licensing

- Source / release: https://github.com/simfeo/blender/tree/android-alpha-4
- This is an **unofficial** experiment, unaffiliated with the Blender Foundation.
- Blender and its modifications are licensed under the GNU GPL (see upstream repository). The matching upstream source is linked above; this repository contains the complete manifest adaptation and repackaging scripts. Redistribution must retain license notices, corresponding source availability and copyright attributions.
- The original APK is downloaded during CI, not committed to this repository.

See [technical notes](docs/TECHNICAL.md) and [release caveats](docs/RELEASE_NOTES.md).
