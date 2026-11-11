# Blender Android 11 — File Loading Stability Trial (not device-verified)

The user confirmed that Android 11 can launch the upstream Blender Lite UI, but reported crashes when opening .blend or .glb files. This is a conservative mitigation, not a claim that the crash is fixed.

- Turn OFF GPU Subdivision by default in Blender Python preferences. CPU subdivision still works.
- Restrict GPU texture preview uploads to 512 pixels by default to avoid some GPU memory exhaustion on Mali.
- Disable the prior release's **automatic** Balanced viewport effect changes. The menu remains available manually.
- Stop holding references to Blender viewport RNA objects through a .blend file reload.
- Log file loading and process memory snapshots to \`Download/Blender/mobile-file-debug.log\` (if permitted) and Blender's normal \`Download/blender-startup.log\`.
- Add **View → Mobile Performance → Write File Load Diagnostic** to mark the log before attempting file open.
- No modification of Blender's C/C++ rendering libraries or user assets.
- Android 11 Java API patch retained, upstream Blender APK SHA-256 pinned, test signature and ARM64 verified by GitHub Actions.
- **CAUTION:** The test APK's signing certificate differs each build, so upgrading requires backing up projects and uninstalling the previous test package.

Use File > Open for .blend and File > Import > glTF 2.0 for .glb; for a small model where normal import still crashes, provide the last lines of the two log files, with private file paths removed.

Both target file formats **remain unverified on Android 11** until real phone tests pass. Revert to run-7 or run-9 if this build has a regression.

Details: docs/FILE_STABILITY.md
