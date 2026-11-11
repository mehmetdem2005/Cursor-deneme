# GLB crash surface scan: current Android 11 APK

Risk A: unsupported Draco / meshopt compression. Inspect glTF extensions and use actual is_draco_available/is_meshopt_available probe. Do not assume all GLBs need Draco.

Risk B: Mali Vulkan memory allocation or shader compilation. The Lite Vulkan-only port can render Solid but crash on Material Preview or creating shader resources. The GLB preflight sets Solid and Flat; it is not a native shader fix.

Risk C: Android OOM / GPU pressure. A 2 MB GLB can expand to far more RAM, because the importer reads the complete source file and builds buffers, meshes, materials and textures. The runtime scanner doesn't read mesh binary data, and blocks unusually heavy imports by default.

Risk D: malformed GLB. Magic, version 2, declared size, JSON chunk, subsequent chunk bounds, position accessor indices are checked up front.

Risk E: our own modifications. Prior custom ELF property hook, adaptive idle polling, Python startup and Rig Lite are not device regression-tested. Keep v15 and v16 releases, compare exact same GLB and check a startup log to isolate behavior.

Risk F: user action. File > Open reads .blend projects, File > Import GLB / GLTF uses the glTF import operator. Multiple imports of the same object can cause z-fighting and additional memory use.

User diagnostic: open Download/blender-startup.log and Download/Blender/mobile-file-debug.log, and look for GLB_IMPORT_BEGIN followed by GLB_IMPORT_RETURN. If only BEGIN is visible, get an Android crash report / sanitized logcat. The exact GLB (if user can upload it) will enable inspection of embedded compression and geometry. Native cause cannot be known from screenshots alone.

Upstream code: https://github.com/simfeo/blender/tree/android-alpha-4
Alternative Android 5.3 stable port has glTF KTX2/Vulkan fixes but minimum Android 12, so it is not directly usable with target Android 11 without additional porting.
