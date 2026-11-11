# Blender Android 11 — armature bone edit crash diagnostics (experimental)

**Observed on the Redmi Note 8 Pro:** Rig editing began to crash after adding several bones; deletion of bones beyond roughly the fifth caused an immediate application exit. Five bones are trivially small relative to normal Blender armatures. This is not an established memory-capacity threshold. Exact fault (armature data, undo, GPU buffer allocation or Android Vulkan driver) requires the phone crash log and an independent empty-scene reproduction.

Source review:
- Upstream Blender's Overlay Armature engine draws bone styles through distinct GPU paths (OCTAHEDRAL, STICK, WIRE, etc.), so an opt-in STICK display trial is valuable.
- Blender's issue tracker includes crashes in bone deletion/selection/adding, including #140636, #151082 and #164168, but those issues do NOT prove the current alpha-4 contains the same bug. Several were fixed upstream.
- Mali-G76 on Android 11 is outside the original port's Android 12+ support and has known stray Vulkan triangles.

New **View > Mobile Performance** menu items:
1. **Bone Safe: Stick (lightweight)** uses stick/line representation for the selected armature, hiding bone names only. The imported mesh remains visible.
2. **Bone Safe: Isolate Mesh (bounds)** also renders armature-bound mesh objects as lightweight bounding boxes. This isolates Blender's armature edit path from expensive mesh overlay/draw operations, but removes surface detail until restored.
3. **Bone Safe: OFF / Restore** restores previous armature and mesh viewport display settings.

The mode logs **BONE_COUNT_EDIT_N** / **BONE_COUNT_POSE_N** only when counts/modes change, by a 0.75-second timer. Nothing scans every vertex and no bone is added/deleted automatically. Original UI/display settings are restored before a .blend save and reapplied after saving, and cleared before opening a new .blend. The log is attempted at \`Download/Blender/mobile-file-debug.log\`, plus upstream console output.

**No guarantee the native crash is fixed.** If it also crashes on a brand-new empty scene with 6+ bones, collect a device error trace (SIGSEGV, Vulkan error, armature edit operator) and consider rebuilding the native engine with the corresponding upstream fix. If it only happens with the GLB, the skinned mesh dependency / GPU workload is more suspect.

Quick isolation steps:
- Fresh Blender startup, add Armature without any GLB, go Edit Mode, extrude 7 bones; delete the latest one.
- Import only the known working mouse GLB in a new scene, select the armature and enable Bone Safe: Stick, repeat.
- If still crashes, enable Bone Safe: Isolate Mesh and repeat.
- Back up projects before reinstall; CI uses per-run test signing keys.
- If no mode stabilizes, the native crash trace is required; do not blindly optimize rig data or alter bones.

GitHub CI only validates Python/ELF packaging, not real-device bone editing. Previous run-20 full framebuffer and run-19 reduced framebuffer are kept for rollback.
