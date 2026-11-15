# Edit Mode Android touch diagnostic experiment — NOT A VERIFIED FIX

Baseline main: 06694e9f804404c24367da9f7a600f17f012f08e.
Upstream: https://github.com/simfeo/blender/blob/android-alpha-4/intern/ghost/intern/GHOST_SystemAndroid.cc

## Source-grounded issue candidate

Upstream GHOST_SystemAndroid.cc defines:
- TOUCH_SLOP_PX = 48; pending finger touch is not promoted to a left-button drag until movement exceeds this threshold on either axis.
- TOUCH_LONG_PRESS_MS = 500; resting touch is promoted to a right click.
- TOUCH_LONG_PRESS_MOVE_PX = 16; long-press rejection for slightly moving fingers.
- ghost_android_scale_input(AMotionEvent_getX/Y(...)) divides display coordinates by renderdiv.

The existing repack uses renderdiv=2, so a 48-buffer-pixel slop is approximately 96 physical screen pixels (axis-aligned). A short finger drag on a Scale gizmo may be delivered as a tap rather than a drag. This is a **source-backed hypothesis**, not verified on Redmi Note 8 Pro. No native touch classifier was modified in this build.

Do not conflate:
1. selection failure (no vertices selected),
2. native transform operator failure (numeric resize fails),
3. touchscreen gesture classification failure (numeric resize succeeds, interactive fails), and
4. GPU redraw failure (mesh coordinates change but image does not).

## Diagnostic UI

The packaged additional startup script \`addon/touch_modeling.py\` adds:
View > Edit Mode Touch Diagnostics

Open a throwaway cube file, switch to Edit Mode and select a face or vertices before running the probes.

1. Inspect Selection / Log: inspect selected vertex/edge/face counts without mesh modification.
2. Scale Selection 1.25x (Numeric Test): calls Blender native transform.resize EXEC_DEFAULT on the selected elements. This **modifies** geometry; use Undo.
3. Scale Selection 0.80x: same, another numeric factor.
4. Start Blender's Native Interactive Scale: calls Blender native transform.resize INVOKE_DEFAULT (test whether the touch cursor drives modal transform).
5. Start Event Trace: opt-in, bounded last 400 cursor/button events. In the same session, try drag and tap, then use Stop and Save Trace.

Logs should appear in \`/sdcard/Download/Blender/edit-touch-trace.log\`. If the folder is not writable, output is also sent to console. The modal trace uses PASS_THROUGH but may not see events consumed by other Blender modal operators; missing log entries **do not prove** Android never emitted the event. It logs coordinates/modes and selected counts only; not object names, project filenames or typed keys.

Diagnostic changes never automatically select vertices, edit user meshes, or force mode transitions. Snapshot and event tracing are read-only. Numeric scale buttons are clearly marked and are explicit user actions. The native Scale operator owns Blender Undo.

## Controlled A/B diagnostic protocol

- Test with fresh cube, Edit Mode, one face selected.
- A: Tap numeric 1.25x, inspect whether selected vertex coordinate-energy changes.
- B: Undo and tap interactive Scale, then gently drag and release.
- C: Record a finger drag shorter than 96 physical px, then one longer than 120 px.
- D: Compare A/B/C under renderdiv=1 and renderdiv=2 **only using independently rebuilt APK variants**, never changing a property which was statically cached after launch.
- E: Compare current v33 and baseline upstream on the same device if both can be installed with backups.

If A succeeds but B fails and the logger receives MOUSEMOVE without LEFTMOUSE down until a large threshold, investigate GHOST touch slop/classifier in native C++ source. Consider smaller thresholds, correct coordinate units and long-press behavior **after** reproducing the problem. This cannot be fixed in the existing APK with a Python menu alone.

If A fails, inspect edit mesh selection and operator poll/override context. If mesh energy changes but rendered shape does not, investigate Vulkan redraw separately.

## Automated / manual boundary

GitHub tests only verify Python syntax, archive packaging, static safety and signature/ELF properties. They DO NOT simulate real Android touch or prove that the menu successfully registers or an Edit Mode transform succeeds on the physical phone. Avoid releasing anything labeled a fix until a real device passes.

The existing GitHub workflow builds diagnostic APK artifacts on push. It publishes no new GitHub release unless manually dispatched with publish_release=true.

Existing releases v31 and v33 remain unchanged. The full v31 original is preserved byte-for-byte in the generated ZIP.
