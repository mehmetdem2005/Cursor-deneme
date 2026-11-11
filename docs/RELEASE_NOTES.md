# Blender Lite / Android 11 experimental

**This APK is NOT confirmed to run Blender on Android 11.**

It is a re-signed and repackaged copy of the real Android Blender Lite alpha-4 application with the declared minSDK changed from 31 to 30. The Blender C/C++ binary is unchanged. Native dependencies and GPU behavior on Android 11 may prevent startup.

- Target: Android 11 (API 30), arm64-v8a, Vulkan GPU.
- Test device: Redmi Note 8 Pro / Mali-G76 MC4.
- Blender is already contained inside the APK. No external Blender app or remote server is needed.
- Package/signature: original package ID, NEW experimental key. Uninstall other Blender APKs signed by different keys before installation and back up projects.
- If installation fails or the app displays black, collect a logcat and any \`Download/blender-startup.log\`.
- The workflow verifies the APK's signature/manifest/arm64 payload, not actual editor operation. Do not claim the port works until on-device tests pass.

Source of included Blender code: https://github.com/simfeo/blender/tree/android-alpha-4

Port and source license: GNU GPL. Experimental Android 11 manifest/repackaging source is in this repository.
