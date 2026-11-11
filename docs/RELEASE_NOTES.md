# Android 11 Mali Material Preview crash & Rig Lite

Status: experimental, not tested on the target Redmi Note 8 Pro.

The user confirmed Material Preview crashes and dense GLB weight/rig interaction is too slow. The unofficial Blender Android port uses Vulkan only and older Mali drivers show geometry artifacts. Native root cause cannot be established without a crash trace.

Changes:
- View > Mobile Performance > Safe Texture (No EEVEE) uses Blender Solid shading with color_type TEXTURE; this displays the active UV image texture, NOT full PBR shader preview. No expensive EEVEE material shader compilation.
- View > Mobile Performance > Rig / Weight Paint Lite ON enables a low-overhead, opt-in mode-specific viewport display for Pose and Weight Paint. It keeps bones, weight colours, deformers and mesh data intact. Flat solid shading, no shadows/cavity/specular, no relationship or motion-path lines, weight contours or floor grid.
- OFF restores previous viewport shading and overlays. The profile is automatically reverted before saving .blend, then reapplied after saving. On opening a different .blend, the mode profile stops.
- Only one simple 400ms mode timer; no per-frame object scan, modifier mutation, automatic decimation or bones changes.
- Previous Android 11 fixes, half-res buffers, GLB import and native bounded idle polling remain unchanged.

Known limitations:
- EEVEE Material Preview sphere button still exists and may crash the Mali driver; choose the alternative command instead.
- Solid Texture preview needs a UV map and active texture image node, and does not show PBR metals, roughness or normal maps in full.
- Heavy base meshes will still require CPU/GPU deform work when posing or painting. This reduces overlays and shaders, not vertex counts, so zero lag cannot be promised.
- CI checks the ZIP and code, not Blender runtime registration, device FPS or on-device shader stability.
- The APK is signed using a new temporary key each build. Back up project files before uninstall/reinstall; prior run-16 is retained.

Sources:
https://blenderandroid.github.io/
https://docs.blender.org/api/5.2/bpy.types.View3DShading.html
https://docs.blender.org/api/5.3/bpy.types.View3DOverlay.html
https://projects.blender.org/blender/blender/issues/161453
