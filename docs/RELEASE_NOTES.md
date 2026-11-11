# Blender Android 11 — GLB crash investigation and preflight release

The Redmi Note 8 Pro (8GB RAM, Android 11, Mali-G76) sometimes crashes on GLB import after previously importing an uncompressed mouse model. The exact cause is NOT known without the GLB file and crash log.

Deep source review confirmed:
- Upstream Blender glTF reader in io_scene_gltf2/io/imp/gltf2_io_gltf.py loads the complete GLB using f.read(), then constructs many separate mesh, texture, armature and material structures.
- Blender Lite lacks Draco compression bridges in some distributions, and meshopt support depends on a native bridge. KTX2/BasisU is also not guaranteed in this pinned alpha.
- Old Mali drivers may crash when Vulkan material resources are compiled/uploaded; heavy imports may also trigger Android low-memory killing.
- The prior v17 Rig Lite registration passed unit tests but not real-device GLB regression tests. It cannot be exonerated without a controlled comparison.

Added protected File > Import GLB / GLTF shortcut:
- Checks GLB version/magic/length, chunk boundaries, glTF JSON and POSITION accessor indices without reading the binary mesh into memory.
- Detects Draco, meshopt and KTX2 requirements. Blocks unsupported compressed meshes with a message rather than calling a missing bridge.
- High risk threshold: file over 60 MiB, over one million POSITION vertices, or declared buffers over 256 MiB. The user can explicitly check Allow heavy GLB in the file chooser to proceed.
- Switches viewport to Solid/Flat before import to avoid forcing EEVEE Vulkan Material Preview.
- Writes process-memory-stamped GLB_IMPORT_BEGIN, GLB_IMPORT_RETURN, GLB_IMPORT_ERROR and rejection markers to upstream startup logging. Logging may fail without Android storage permission.
- Calls the original Blender glTF import code: no geometry decimation, lost UV, stripped textures or removed bones.

This cannot prevent every native GPU crash. A BEGIN without RETURN is a clue, not a definitive diagnosis: it could be an Android OOM kill, Vulkan driver fault, or fatal native error.

For this guarded behavior use File > Import GLB / GLTF from the top File menu; the original File > Import > glTF bypasses the preflight. Back up .blend files before uninstalling previous test-signed APKs. The known imported-model v15 is preserved for regression comparison.
