# Blender Lite Android 11 — optional Mobile Performance profiles

This build is a conservative experiment based on the confirmed-starting Java compatibility release (run 7). The previous release stays available as a rollback option.

Changes:
- Include a single Python startup module in Blender's existing runtime payload: \`scripts/startup/mobile_speed.py\`.
- On the blank default startup screen only, apply a balanced profile: FXAA, 2x anisotropic filtering, 1024 texture clamp, disable solid-view shadows and cavity (grid and tools remain).
- On any 3D viewport, open **View → Mobile Performance** to choose **Fast** (disable viewport antialiasing, anisotropic filtering, extra shading and viewport floor grid) or restore original settings during the same running session.
- Existing .blend files are not automatically modified. No geometry, actual render resolution, render quality, camera, or Blender binary code changes.
- Keep original Vulkan and Android JNI libraries completely unchanged.
- The APK retains the earlier Android 11 Java API-field correction.

Caveats:
- **No physical Redmi Note 8 Pro benchmark or FPS measurement yet.** Some lag comes from CPU scheduling or Mali Vulkan shader compilation and may not be fixable with Python preferences.
- The source APK's renderer **already** defaults to half-resolution buffers on devices with <6 GB RAM. We do not reduce the window further.
- The temporary test signing certificate changes each CI run. Back up projects and preferences before uninstalling the older experimental APK. Installer cannot update older package without a matching signature.
- If Python UI startup module fails, the core Blender engine remains unmodified, and the known-working prior release remains available.

Source: https://github.com/simfeo/blender/tree/android-alpha-4
Project source/patched packaging: https://github.com/mehmetdem2005/Cursor-deneme
Upstream GPL-2.0-or-later.
