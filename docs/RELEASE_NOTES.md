# Blender Android 11 — adaptive idle CPU loop (experimental)

**Status: NOT BENCHMARKED ON THE PHONE.** Same real Blender 5.3 Lite engine, Android 11 compatibility, GLB Import shortcut, Mali Safe profile and half-resolution renderdiv=2 as before.

Investigation of pinned upstream source found that Android's \`android_main\` uses \`ALooper_pollOnce(0)\` in a loop after Blender initializes and runs \`WM_main_loop_body\` every iteration. Blender's \`wm_draw_update\` already respects redraw invalidation; the CPU loop, however, has no built-in idle wait.

This release adds a second private native import redirect in \`libblender.so\`: \`ALooper_pollOnce\` to \`blender_pollOnce\`, implemented by the bundled ARM64 \`librenderdiv_shim.so\` that delegates to the real Android looper. Zero-timeout polls wait 10ms for 800ms after Android events, then 24ms when idle. Android looper **wakes immediately** when input arrives; no event dropping or frozen frame. Other timeout values are unchanged. Blender still gets its normal main loop and animation updates. 60fps playback may be slightly constrained during prolonged no-input activity.

The previous renderdiv=2 hook is retained, along with viewport AA disabled and optional Mali Safe. The optional GLB importer still uses official glTF 2.0; File > Open is for .blend.

**Limitations:** This addresses *idle CPU spin*, not GPU shader complexity, vertex throughput, viewport occlusion or Mali Vulkan driver triangles. No on-device FPS/heat proof yet. Black speckles might also be z-fighting from multiple copies of the mouse imported at exactly the same coordinates. Check object duplicates in Outliner before concluding the Mali driver is at fault.

Native patch is pinned to the exact original SHA-256 and refuses unknown ELF symbols; GitHub CI validates both imported shim functions inside the signed APK.

Back up project files before uninstall/install (CI uses rotating test signing keys). If the new release causes input, animation or startup problems, roll back to the previous successful run-15 release.

Sources:
- https://github.com/simfeo/blender/blob/android-alpha-4/intern/ghost/intern/GHOST_AndroidMain.cc
- https://github.com/simfeo/blender/blob/android-alpha-4/source/blender/windowmanager/intern/wm.cc
- https://blenderandroid.github.io
