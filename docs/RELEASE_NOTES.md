# Blender Android 11 — native three-minute crash recovery (experimental)

User request: Automatically save work every three minutes, after reported crashes while adding/deleting bones and importing GLBs.

Implemented using **Blender's own native Auto Save Temporary Files**:
- At addon registration/startup, enable \`bpy.context.preferences.filepaths.use_auto_save_temporary_files=True\`.
- Set \`bpy.context.preferences.filepaths.auto_save_time=3\` (minutes).
- Retain at least two manual Save Versions (using \`save_version >= 2\`), so ordinary saves provide .blend1 and .blend2 backups.
- On loading another .blend file, reassert native autosave settings.
- File menu includes **Recover Auto Save...**, which uses Blender's own \`wm.recover_auto_save\` file picker.
- No custom Python save timer, no periodic \`bpy.ops.wm.save_as_mainfile\`, no silent overwriting current .blend, no forced mode switches, and no new GPU draw work.

**IMPORTANT RIGGING LIMITATION:** Blender's Python API explicitly warns that Edit and Sculpt mode data may not be captured in native temporary Auto Save files. Do not assume a bone currently being moved/added/deleted is fully preserved. Users doing rigging should manually save after meaningful editing milestones and before risky bone deletion. The three-minute interval is a recovery target, not a guarantee of exactly 180 seconds on a frozen/crashed Android device or during modal operations. Temp files may disappear if Android clears the app cache, on reinstall, or if the process has not reached its first autosave.

**Recovery:** Open Blender > File > Recover Auto Save..., choose most recent timestamped autosave, and immediately Save As to a safe new file in shared storage. Back up important projects externally before uninstalling/upgrading an APK with a new CI test signature.

All existing Android 11, Mali graphics, GLB guard, Bone Safe, Rig Lite and depth test changes remain. This is a backup safety addition, **not a fix** for the underlying bone/Vulkan native crash.

Verification: Source and packaging tests verify settings and presence of the recovery operator. GitHub cannot demonstrate that Android permissions, temp directory persistence or actual recovery after a crash work on the physical phone.

Sources:
- https://docs.blender.org/api/5.2/bpy.types.PreferencesFilePaths.html
- https://docs.blender.org/manual/en/latest/troubleshooting/recover.html
