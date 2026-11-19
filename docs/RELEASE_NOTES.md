# Blender Lite v33 + Material Guard (experimental, NOT device-verified)

Based on v33 commit 06694e9f804404c24367da9f7a600f17f012f08e. This is NOT a new native Blender/Vulkan engine build.

## New optional path
- Select a mesh in Object Mode and go to View > Safe GPU / Rig > Add Safe Proton Blue / Add Safe Neutron Violet.
- Creates a simple non-node solid-colored Blender material using bpy.data.materials.new, not the Material Properties > New button.
- Switches open Material Properties tab to Object tab before creation; stays in low-cost Solid/Flat viewport.
- No live shader preview, no texture painting, no bloom or glow; the result is only a basic modeling material.
- Phase markers are appended to Download/Blender/material-guard.log when storage permissions allow. Only known event names are written, not file or project names.
- If this also crashes, the last marker (BEFORE_NEW, AFTER_NEW, BEFORE_ASSIGN etc.) helps locate the failing step. Capture a redacted Android logcat/tombstone to diagnose native Vulkan.

## Important limits
- The original Add Material / New UI action is NOT intercepted or fixed; it may still crash the device. Use the alternative menu.
- Existing v33 features (Mali depth-safe viewport, Texture Paint preflight, 3-min autosave, low-memory half-resolution profile) remain.
- GitHub CI verifies Python source, tests and APK packaging only; it cannot verify Blender material creation on Redmi Note 8 Pro Android 11 / Mali-G76.
- v31 original APK remains in the ZIP, SHA256 checked. Both APKs share org.blender.blender and cannot be installed side-by-side. Back up .blend files before switching APKs.

### Device acceptance test
1. In disposable new file, create Sphere, keep Object Mode and Solid view.
2. Avoid opening Material Properties; use View > Safe GPU / Rig > Add Safe Proton Blue.
3. Verify blue tint in Solid view and file save/reload. Repeat for Neutron Violet on a second object.
4. If crash, collect Download/Blender/material-guard.log and Android native crash report.
