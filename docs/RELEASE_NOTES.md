# Blender Lite v33 — Mali Depth Guard (experimental)

Built from v32 Paint Guard. Preserves:
- Native half-resolution render divisor 2 and low-memory flag
- 96 UI DPI, 128px viewport preview texture clamp
- GPU subdivision OFF, anti-aliasing OFF, Solid/Flat GPU defaults
- Native Android looper and 3-minute autosave
- Texture Paint preparation, reversible Safe Texture Preview, diagnostics

### New depth control
- A one-time, reversible near/far viewport clip profile is prepared at app startup and after loading a file **only when Blender is in Object Mode**. This does not change mesh, skinning, armature, UVs, materials, render quality or framebuffer resolution.
- SAFE (default): near 0.05 and far 50.0 Blender units.
- STRONG (manual): near 0.1 and far 20.0 for diagnosing fine Z-fighting; very close details/distant objects can be clipped.
- View > Safe GPU / Rig > Mali Depth Safe, Mali Depth Strong, or Restore Original Depth. Switch to Object Mode before using the menu.
- If a project opens directly in Pose/Edit/Weight Paint, we do not modify GPU viewport state in those modes. Go to Object Mode and choose Mali Depth Safe once.
- Saves made while the new clip profile is active may also save those viewport clip values (not mesh data); Restore Original Depth is provided. Back up .blend first.

### Root cause still not proven
Two prior MouseBody .blend versions were checked: no identical overlapping triangle areas were detected, but both saved clip_start 0.01/clip_end 1000 for 10 viewports. This strongly motivates a depth precision experiment, **not a proven native driver fix**.
The Android alpha-4 Mali/Vulkan known stray triangle issue can remain. No real Mali-G76 GPU test was executed in GitHub CI.
Compare same MouseBody file/view in SAFE and original settings. If artifacts persist, need sanitized device logcat/bugreport and a native Vulkan driver fix.

The GitHub Release includes new v33 APK and a ZIP containing byte-for-byte v31 original (SHA256 c0a345b6496a903228932b6dd3425ffdbdf21a7d25b169996c3bd3e4a938f31b) and new v33 APK, with SHA256SUMS.
Both APKs share package ID org.blender.blender and cannot be installed side-by-side. Test signing may differ; back up user data before changing versions.
