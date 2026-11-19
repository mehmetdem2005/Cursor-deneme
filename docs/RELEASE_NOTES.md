# v33 General Material Properties Panel Experiment (NOT a native Vulkan fix)

Based on exact original v33 06694e9f804404c24367da9f7a600f17f012f08e. Main is not changed.

## What changed
- Edits Blender's **standard** Material Properties UI, not a shape-specific menu. For supported object types, + keeps adding a material slot, New keeps creating a material, and the material picker, surface/volume/settings, viewport color, and node editors are retained.
- The + button uses a guarded Python data operation to add a slot; New uses Blender material datablocks, or copies the selected material.
- The default material thumbnail **Preview** subpanel is suppressed to avoid scheduling expensive EEVEE material preview renders on a Mali device, where the preview and the Vulkan driver may hang. The rest of Material Properties is kept.
- Before and after operation markers written to Download/Blender/material-ui.log (when permitted), without model or project names.
- Existing v33 optimizations, depth profile, three-minute autosave, and v31 APK preservation remain.

## Limits / do not misrepresent
- This is a Python GUI/data-path experiment, not a C++ Vulkan fix. It cannot fix GPU driver deadlocks, shader compiler hangs, Material Preview or Rendered view, or all Material operations in native code.
- It is for **all Blender-compatible material objects**, not just the atom model. It does not restrict creation to two colors.
- Material Preview thumbnail is unavailable in this test; materials and shader nodes remain editable, subject to driver limitations.
- GitHub CI checks packaging and mocked Python tests only. Tests on real Redmi Note 8 Pro/Mali-G76 are mandatory before calling it fixed.

## Test
1. Back up .blend and images; don't uninstall original v33 until backed up. APKs share package ID and cannot install side-by-side.
2. Open new, disposable Sphere in Object Mode, Solid view, Material Properties tab.
3. Press + to add an empty slot; click New to create an editable material. Adjust surface color, roughness, nodes (while staying Solid) and save/reopen.
4. Repeat on a mesh and a curve, then existing project.
5. If it stalls, after app closes inspect Download/Blender/material-ui.log and Android bugreport/logcat; last checkpoint helps identify step. ANR vs app force-close must be distinguished.
