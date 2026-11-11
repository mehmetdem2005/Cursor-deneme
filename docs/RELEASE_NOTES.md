# Safe Edit v29 — Edit Mode crash isolation

User reports that v28 closes immediately on entering Edit Mode on Redmi Note 8 Pro (Android 11, Mali-G76). There is no device logcat trace, so the root cause is unconfirmed.

This test release removes previously introduced risky runtime actions:
- The APK loads addon/safe_edit.py instead of ultra_survival.py.
- There is NO recurring 1.1-second mode timer, NO changes to armature display style during Edit, NO mesh bounds swapping, NO scene Render Simplify or dependency-graph changes, and NO modifications to weight/bone/model data.
- GPU profile applies only in OBJECT mode once at startup or on file loading; it uses Solid FLAT, no viewport AA, no cavity/shadows/specular and GPU subdivision off; keeps editing overlays and weight colors.
- The native blender_pollOnce shim now delegates the exact original ALooper_pollOnce timeout rather than inserting 10/24ms delays. This may increase idle CPU use but removes custom main-loop pacing when switching modes.
- Native half-resolution 2x framebuffer, compact UI DPI 96, lowmem mode and Android 11 compatibility remain.
- Blender native temporary autosave is enabled every 3 minutes. Edit-mode changes may not be captured; manually save between risky bone operations.

CI tests include source/runtime safeguards that forbid Edit Mode property changes from this startup addon. APK packaging tests do not test actual Mali GPU or native Blender editing. Do not claim crash fixed on device until user tests.

Test on device in this order, after safely backing up .blend and .glb files: start empty scene, enter cube Edit Mode, return Object, add a fresh armature and enter Armature Edit Mode, then test the heavy mouse GLB. If empty scene still fails, collect a system bug report/logcat for Vulkan/SIGSEGV/OOM and compare run-15. Never repeatedly enter a failing mode without a saved file.

Known fallback v15: https://github.com/mehmetdem2005/Cursor-deneme/releases/tag/android11-exp-run-15
