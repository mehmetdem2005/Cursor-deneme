# Android 11 GLB importer shortcut + Mali Safe viewport (experimental)

Device: Redmi Note 8 Pro, Android 11, 8 GB RAM, Mali-G76 MC4.

## GLB is not a .blend

The reported error reads "File format is not supported in file ... .glb". Blender's **File > Open** is the .blend project reader. It must not open glTF as if it were .blend. The correct menu is **File > Import > glTF 2.0 (.glb/.gltf)**.

This build adds **File > Import GLB / GLTF...** at the top of the File menu, which calls the official Blender \`bpy.ops.import_scene.gltf('INVOKE_DEFAULT')\` file picker and avoids the .blend-file reader. No format conversion, replacement engine or external viewer is involved. If the official glTF add-on has not registered, the shortcut attempts to enable the bundled \`io_scene_gltf2\` module. This does not guarantee all compressed GLB files load: Lite omits support for some Draco/meshopt compressed meshes. Uncompressed GLB is the first test.

## Viewport glitch trial

The previous experimental release forces half-width/half-height Vulkan buffers on 8 GB RAM devices. This reduces buffer pixels by ~75% but **may** reveal Mali driver or scaling artifacts when orbiting/zooming. This build retains that setup, but adds optional **View > Mobile Performance > Mali Safe (graphics glitches)** to turn off viewport anti-aliasing, shadows, cavity, highlights and grid, using flat lighting. The user can choose Restore in the same session. These changes do not remove meshes or change saved model coordinates. **This is a diagnostic/mild workaround, not a tested driver fix.**

The original Blender Lite renderer is Vulkan-only. A true GPU driver fix requires source-level Vulkan work or a different driver / GPU API path, not a Python UI option.

## Release caution

- This is an experimental APK, not yet tested on the user's device.
- Prior working app/SDK compatibility and file stability guards retained.
- CI checks that the GLB shortcut and Mali safe mode are present in the signed APK, along with APK signature, native shim linkage, arm64 ABI.
- Back up .blend and .glb outside app data before uninstalling older test APKs. Each run uses a new signing key, so updates may require uninstall.
- If zoom distortion persists, compare with the previous full-buffer release (run-10) to distinguish render-scale effects from native Mali driver bugs; prior APKs are preserved.
- If importing via the new shortcut shows another error or closes Blender, attach \`Download/blender-startup.log\`, or upload the actual GLB for compression/structure inspection.

Source: https://github.com/simfeo/blender/tree/android-alpha-4
