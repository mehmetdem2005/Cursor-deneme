# Blender Android 11 Ultra Rig Survival — 4x render divisor, severe quality sacrifice

**Experimental APK. Not yet tested on the user's Redmi Note 8 Pro.** The primary goal is to edit a small number of bones and paint weights, then save the .blend; image quality, Material Preview and rendered textures are NOT priorities.

## What changed

- The pinned upstream Android Blender engine explicitly allows \`debug.blender.renderdiv\` values 1–4. This build forces **4** app-locally using the previously established ARM64 dynamic-property hook. Window buffer width/height become one-quarter each (1/16 total pixels, 93.75% fewer than full resolution). The same upstream function scales touch input to match. Actual GPU load is NOT guaranteed to drop by 93.75%, as vertex/rigging and shader costs remain.
- Force \`debug.blender.lowmem=1\` **inside Blender only** to enable its native low-memory configuration, independently from the phone's physical 8 GB RAM.
- Set Blender viewport AA **OFF**, anisotropic filtering **OFF**, uploaded texture clamp **128**, and GPU subdivision **OFF**.
- The new **ULTRA RIG: ON (minimum GPU)** profile runs at startup and after loading a .blend. All 3D viewports are Solid/Flat, no cavity, shadows, highlights, grid, relationship/motion paths or weight contour lines. Keep overlays, bone drawings, weight-paint color ramp and brushes enabled. The profile avoids EEVEE Material Preview by default; opening Material Preview manually can still crash old Mali Vulkan drivers.
- **ULTRA RIG: OFF (restore)** restores original viewport settings for the current session (but the low-res Vulkan buffer requires rebuilding/reinstalling a different APK to change, since it is set when the native window starts).
- Temporary viewport settings are restored around Blender .blend saves and before loading another .blend; model, skeleton, geometry, weights and UVs are never modified by the Ultra Rig profile.
- Native three-minute Auto Save and native Recovery menu added in previous change remain.

## What this does not solve

The user reported crashes after ~5 armature bones and while deleting bones. This number is too small to be an actual model complexity limit. If it crashes even in an empty scene with seven bones, the native Android Vulkan overlay or Blender armature edit/undo path is faulty and must be repaired using actual Android crash logs or a source rebuild. The ultra-low pixel resolution cannot fix CPU-side armature bugs. The GPU may still draw incorrect triangles on old Mali drivers.

## Safety and recovery

Back up any user files before upgrading, as each GitHub Actions build uses a new self-signed certificate and Android may demand uninstalling the old APK. Native Auto Save may not preserve active Edit Mode changes; save manually in Object/Pose mode after each few bones. Keep the original GLB intact.

Use the plain File → Save As to save into shared storage. If the model view is too pixelated to position bones, use the previously published run-19 (2x divisor) release; do not change native scale while the app is running.

Sources:
- upstream GHOST_AndroidMemoryTier.hh, explicit renderdiv range 1..4: https://github.com/simfeo/blender/blob/android-alpha-4/intern/ghost/intern/GHOST_AndroidMemoryTier.hh
- Blender API texture limit enum: https://docs.blender.org/api/5.1/bpy.types.PreferencesSystem.html
