# Blender Lite Android 11 — v32 Paint Guard (experimental)

This build preserves the v31 native render divisor=2, UI DPI=96, low-memory flag, original Android looper, 128px texture preview limit, disabled GPU subdivision, Solid/Flat startup, and 3-minute native autosave.

What changed:
- Object Mode-only, user-triggered Prepare Texture Paint; preconfigures existing VIEW_3D areas across Blender screens in low-cost Solid/Flat without entering any paint mode or touching materials/UVs/bones/weights.
- Object Mode-only Safe Texture Preview (Solid / texture color); opt-in. It does NOT invoke EEVEE Material Preview.
- User-triggered diagnostic markers (mode, memory RSS, loaded-image dimension metadata only), best-effort Download/Blender/paint-guard.log. No project paths or names.
- Reversible view settings, including initially inactive workspaces, and extra static/mock regression tests.
- Release ZIP includes original v31 APK verified against SHA-256 c0a345b6496a903228932b6dd3425ffdbdf21a7d25b169996c3bd3e4a938f31b.

Known limitations:
- This is an APK repack, not a source-level native Blender Vulkan driver fix. Real Redmi Note 8 Pro Texture Paint crash can persist, especially during 3D painting, larger image uploads or Material Preview.
- GitHub Actions tests do NOT execute the native UI on a real Mali GPU. Paint support must be validated on device before claiming a fix.
- Never uninstall the current APK before backing up .blend files and painted images. The CI test signing key may differ from v31, preventing in-place updates.
- Save painted texture images separately; Blender's 3-minute auto-save alone does not guarantee unsaved image pixels persist.
- Both APKs use org.blender.blender; they cannot be installed side-by-side.

Device acceptance checks: empty cube Edit, Pose, Weight Paint, 256px Texture Paint, brush/undo, Image Save, .blend Save/Reload, then 512px and mouse project. Capture logcat/tombstone on crash.
