# FULL framebuffer diagnostic variant / Android 11 Mali-G76

This release exists to isolate a possible regression from the app-local renderdiv=2 half-resolution optimization. No model data or rigging is changed. Same experimental Blender 5.3 alpha-4 port, GLB guard, Java API30 compatibility, idle-poll shim and View > Mobile Performance > Depth Precision Test.

**Only native renderdiv changes:** compile the app-private property shim with MOBILE_RENDER_DIVISOR=1. This restores the port's full-size Vulkan window buffers on the 8GB phone, versus the previous run-19 renderdiv=2 half-resolution APK. FULL is slower and may use more GPU memory. It is not a recommended performance build.

Compare:
- FAST run-19: https://github.com/mehmetdem2005/Cursor-deneme/releases/tag/android11-exp-run-19
- FULL run-20: this release
Use the identical GLB, identical model viewpoint and Solid/Weight Paint modes. In both, optionally use View > Mobile Performance > Depth Precision Test ON. If FULL is clean but FAST corrupted, the renderdiv2 route is suspect. If both are corrupted, consider Mali Vulkan driver, depth precision and duplicate/coplanar polygons in the GLB.

GitHub validates signing and native dependency, not on-device graphics. Signed with a new temporary key; back up files before changing builds as uninstall may be necessary.
