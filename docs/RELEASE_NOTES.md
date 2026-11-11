# Blender Lite Android 11 — patched Java API 31 accesses, native support unverified

Fix included in this build:
- The upstream BlenderActivity calls Android's Build.SOC_MANUFACTURER and Build.SOC_MODEL before starting the native window. Both fields were added in API 31 (Android 12). On Android 11 a missing field may throw NoSuchFieldError, which upstream's catch(Exception) does not handle. Both field accesses are replaced in the DEX with Build.MANUFACTURER (API 4) and Build.HARDWARE (API 8).
- Repacked the actual upstream Blender Lite Android application. No external application, streaming service or substitute 3D engine.
- Installs with minSdkVersion 30, arm64-v8a; APK is zip-aligned and self-signed by CI.
- Automated tests assert the two dangerous field references are removed from the packed app's smali before build.

**Still unverified:** The app has not been run on an Android 11 device. Upstream requires Android 12; a native linker incompatibility or older Mali Vulkan driver can still crash it before UI. A successful CI build and valid signature do not prove real runtime compatibility.

**Important installation:** The experimental signing key is regenerated with each build. You must back up .blend files and uninstall earlier experimental Blender APKs before installing this version. Do not uninstall the official upstream Blender if you need its stored files without backing them up first.

Source: https://github.com/simfeo/blender/tree/android-alpha-4
Android SDK Build.SOC fields: https://developer.android.com/reference/android/os/Build
License: upstream GPL-2.0-or-later; this repository publishes its patch sources.

If app still closes instantly, the next requirement is an Android crash trace (Java NoSuchFieldError vs linker vs Vulkan). On Android 11: Settings > About phone > tap MIUI version until Developer options appear; enable Developer options > Take bug report or capture via adb. Do not share any whole bugreport publicly without removing personal information.
