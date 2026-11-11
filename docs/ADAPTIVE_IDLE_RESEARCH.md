# Sustained performance research — Redmi Note 8 Pro (8GB, Mali-G76, Android 11)

## Confirmed in upstream source

1. \`GHOST_AndroidMain.cc\`: after Blender startup, Android polls with timeout 0 and runs WM_main_loop_body continuously. This may waste CPU when the user is not interacting.
2. \`wm.cc\`: WM_main_loop_body processes events, notifications and conditional wm_draw_update. The GPU does not necessarily repaint the whole scene on each main-loop iteration.
3. \`GHOST_AndroidMemoryTier.hh\`: the existing Android port supports a divisor=2 framebuffer mode. Our prior app-private shim invokes it on 8 GB devices; that only reduces framebuffer pixels, not geometry or shader cost.
4. Android Blender port uses Vulkan exclusively, with documented stray triangles on older Mali drivers. Zoom noise is NOT necessarily low FPS; duplicate coplanar geometry can produce z-fighting too.
5. Blender's standard Scene Simplify and texture-limit preferences can reduce costly modifiers and GPU texture memory without rewriting model files; but this does not reduce an already-imported base mesh with no modifiers.

## Implemented this release

Native shim provides bounded polling for timeout=0 (10ms recently active, 24ms idle) and passes through all nonzero timeouts. This prevents an unbounded busy-spin while preserving Android event wakeups. No Vulkan calls or bpy scene contents are modified.

## Deferred due to correctness risks

- Per-gesture switching to bounding boxes can invalidate Blender picking/editing and trigger expensive dependency-graph rebuilds; not activated automatically.
- Reusing an outdated frame after a transformation would cause visual staleness and potentially incorrect edits; keep Blender's built-in redraw path.
- Disabling animations/timers during idle is incorrect; use a modest poll duration.
- Hidden geometry/frustum culling is a native engine responsibility, not safely improved by a Python timer scanning a giant object list.
- Automated decimation or removing small objects would change user data. Do not do it.
- App is Vulkan-only; a real shader/driver workaround needs source-level port work and physical device test, not a claimed setting-only fix.

## Device test

Compare same GLB, number of objects and shading on run-15 vs new release, with 30 seconds inactivity then 30 seconds orbit and after settling. Check responsiveness, heat and animation playback. No specific FPS guarantee. For black speckles, check duplicate objects/multiple imports and test Mali Safe; separate the two causes.

References: the upstream tagged source and https://docs.blender.org/manual/en/5.2/render/cycles/render_settings/simplify.html.
