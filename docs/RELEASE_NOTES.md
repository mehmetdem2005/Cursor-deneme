# Blender Lite v39 Audio Safe — Android 11 experimental

The 22 November 2026 MIUI report contains (1) Blender SIGSEGV in Android /system/lib64/libaaudio_internal.so AudioStream::MyPlayerBase::playerSetVolume at 02:00:03 and (2) an Android NativeActivity.onPause wait ANR at 01:57:51. Earlier Mali crashes remain separately possible.

The pinned upstream Android port reads internalDataPath/blender_args.txt before native GHOST_android_launch; Blender supports -noaudio. v39 makes BlenderActivity create this argument file before super.onCreate if absent. Existing custom argument files are not overwritten. The native Blender engine itself and system AAudio driver are unchanged. Material Properties preview removal added in v38 is no longer enabled by default. An optional A/B override remains for future tests.

This is a targeted unverified mitigation, not proof of a root-cause fix. No real phone test was possible in CI. Keep .blend projects backed up; v31 rollback included in ZIP. Two APKs share one package identifier and signing may differ. Do not use the v39 APK for critical editing until a basic blank scene / Material New / app background test succeeds. If the phone locks again, stop using this test build.
