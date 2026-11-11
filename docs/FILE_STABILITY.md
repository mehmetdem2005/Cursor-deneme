# File import crash / stability experiment

Status: source-side protection added; on-device file load has NOT been verified. Previous known-opening releases remain published.

## Why this version exists

The Android 11 Redmi Note 8 Pro successfully shows the Blender interface but the user reports that both \`.blend\` opening and \`.glb\` importing end with an immediate app exit.

Potential causes cannot be isolated without a native crash log: GPU driver faults under newly loaded geometry/shaders, system low-memory kill, bad Android content URI/storage permission, unhandled importer errors, or unsupported file data.

- Blender Android's upstream acknowledges Android low-memory kills on heavy scenes.
- In another Android Blender port, a user reported that disabling GPU subdivision stopped crashing when loading .blend scenes.
- Upstream Lite **does not include Draco glTF decompression**, so some Draco-compressed GLBs cannot be imported (but that alone is not evidence of this crash).
- The process runs on Android 11 below upstream's stated API 31 minimum. Native compatibility has not been proven for file opening.

## Conservative mitigation

- Start the application with \`bpy.context.preferences.system.use_gpu_subdivision=False\` to bypass an optional, driver-sensitive GPU path; the CPU subdiv modifier remains available.
- Clamp maximum uploaded viewport texture size to 512, to reduce GPU memory pressure from imported assets. Render output data and image files are not overwritten.
- Remove automatic viewport appearance edits. Balanced and Fast remain manual choices under View -> Mobile Performance.
- Remove Python references to existing Blender SpaceView3D objects that become invalid after a .blend reload; only restore a viewport if it is still live.
- Attach tiny \`load_pre\`/\`load_post\` callbacks that log memory snapshots before and after .blend reads. Log a memory snapshot every ~12 seconds only when RSS changed significantly.
- Add View -> Mobile Performance -> Write File Load Diagnostic. It writes a marker prior to the user's next open/import attempt.
- No .blend or GLB files are modified, no native Blender libraries replaced.

## Diagnosis without Termux

1. Keep original .blend and .glb files outside the app and back them up.
2. Test a freshly saved default cube .blend (created in this Android Blender build), then a very small GLB with no textures, then the troublesome file.
3. Use File > Open for .blend and File > Import > glTF 2.0 for .glb. If crashes only happen when selecting a file from Android's file manager, examine Android SAF/content URI path handling separately.
4. Before reproducing, select View > Mobile Performance > Write File Load Diagnostic.
5. After a crash, use a file manager to look for \`Download/blender-startup.log\` and \`Download/Blender/mobile-file-debug.log\`. The first is upstream's native log; the second records memory and file-load events. It may not be writable without file access permission.
6. If neither log identifies the crash, retrieve Android logcat or a bugreport, filtering for \`org.blender.blender\`, \`libblender.so\`, \`SIGSEGV\`, \`SIGABRT\`, \`VK_ERROR_DEVICE_LOST\`, \`OutOfMemoryError\`, or \`lowmemorykiller\`. Bugreports can include private data; remove sensitive information before sharing.

If a native crash happens before Blender's Python load_post callback, the log will only show load_pre; this is expected, not evidence of a complete fix.

## Repro checkpoints

- Opening Blender interface (previous release: verified by user).
- Opening saved cube .blend (unverified).
- Importing tiny uncompressed .glb (unverified).
- Opening larger assets (unverified).
- FPS, RAM, shader compilation (unmeasured).

Sources:
- https://blenderandroid.github.io/updates/2026-09-07-main-android-alpha-3/
- https://devtalk.blender.org/t/issues-porting-blender-to-android-tablets/35419/188
- https://github.com/simfeo/blender/tree/android-alpha-4
