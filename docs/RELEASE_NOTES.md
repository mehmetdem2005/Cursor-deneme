# Blender 5.3 Lite / Android 11: experimental 50%-per-axis render buffers

Target: Redmi Note 8 Pro, 8 GB RAM, Mali-G76 MC4, Android 11.

This variant attempts to force the upstream Blender's `GHOST_android_render_scale_divisor() = 2` behavior even when 8 GB of physical RAM prevents the source's low-memory auto-trigger.

### What changes

- Add `librenderdiv_shim.so`, a tiny ARM64 native library with one purpose: report `2` **only** for Blender's `debug.blender.renderdiv` query. Every other property request goes to Android unchanged.
- Redirect the single imported `__system_property_get` ELF dynamic symbol in the exact pinned `libblender.so` to `blender_renderdiv_get`, and add a direct native dependency on the shim. The rest of the native Blender image remains unmodified (except ELF relocation metadata adjusted by patchelf).
- Blender's existing window and touch code remains in control. It sets Android window buffers to width/2 x height/2, and scales touch input. Pixel processing is 25% of native resolution **if the shim is honored by this binary**. This is NOT a promise of 4x FPS; neither memory nor geometry is reduced 75%.
- Force viewport anti-aliasing OFF at startup to avoid a reported Vulkan+MSAA Mali-G76 driver issue.
- Retain previously working Android 11 activity compatibility and native Blender runtime.
- Test ABI, APK signing, ELF import and helper dependency in CI.

### Safety / rollback

**Experimental. This has NOT been run on the target phone.** Native ELF symbol redirection may fail to load on some Android firmware. If startup crashes or the UI misbehaves, go back to run-10. Do not erase projects or format the phone.

GitHub CI uses an ephemeral signing key. Before uninstalling an old build, **back up all .blend/.glb files outside app storage**.

Known driver issue documentation: https://forums.unrealengine.com/t/artifacts-and-crashes-on-some-android-gpus-and-versions-when-vulkan-is-enabled/2536208

Upstream sources: https://github.com/simfeo/blender/tree/android-alpha-4
