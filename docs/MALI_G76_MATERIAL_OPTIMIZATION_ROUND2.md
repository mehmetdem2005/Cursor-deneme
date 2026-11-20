# Round 2: native source-only Material GPU budget optimization

**State:** only a proposed native source patch plus offline tests. NO working or tested APK.
**Why no APK:** last Material operation froze the whole Android 11 Redmi Note 8 Pro, including power/lock responsiveness. A new, unverified binary must not be offered as stable.

## Strict starting point
- The base Blender v33 release is unchanged: tag android11-exp-run-34, commit 06694e9f804404c24367da9f7a600f17f012f08e.
- Original v31 and v33 packages and the main branch remain intact.
- No geometry, materials, shaders or scene settings are touched during startup by this branch.
- Previous research branch changed scene.eevee.shadow_pool_size through Python on load. That persistence risk is deliberately REMOVED from this branch by restoring original v33 safe_edit.py.

## Inspectable risk, not confirmed root cause
- The exact Blender 5.3 Alpha 4 native source has a 6GiB physical RAM condition for the EEVEE shadow pool.
- Above that threshold, a small Material Preview may use the desktop-sized 512MB shadow pool.
- Android 11 Mali-G76 shared-memory graphics driver may stall or lose the device, and the observed full-phone lockup is consistent with more than a normal Python exception.
- 512 / 16 = 32 times lower configured atlas budget in this experiment; this is NOT a measured 32x RAM reduction, FPS improvement or proof that previews won't crash.
- Source provenance: https://github.com/simfeo/blender/blob/android-alpha-4/source/blender/draw/engines/eevee/eevee_shadow.cc
- Newer Blender Android v5.3 caps mobile shadow atlas regardless of RAM; other Vulkan resource lifetime fixes were also made separately.

## What is actually implemented
- scripts/patch_mobile_shadow_pool.py performs exact-match, fail-closed C++ source patch. --apply creates a byte-identical .bak and writes atomically; default is DRY RUN. Supports 16/32/64MB caps.
- scripts/scan_android_material_risks.py is a read-only source compatibility scanner. It checks Material UI, preview, EEVEE cap, and legacy Vulkan view/framebuffer handling.
- tests/test_material_gpu_budget.py covers source patch, backup, double application, no project mutation and budget values.
- tests/test_material_source_scanner.py checks scanner behavior on synthetic fixtures.
- GitHub CI checks all above AND downloads the pinned upstream Alpha-4 source from commit d93bd33cba768e19ee4387a31c0ea137ee2f0047 to verify the patch applies to the actual original. It does not build or run Blender.

## Still required before calling it fixed
1. Collect sanitized crash/ANR and GPU kernel context after reboot without triggering Material again, if records are preserved.
2. Cross-build actual native Blender engine for Android API 30, arm64. Rebuilding existing repackaged APK alone does NOT apply this source patch.
3. Audit Vulkan render pass/framebuffer release and SPIR-V pipeline compilation on Mali-G76; selectively backport fixes from modern fork with version-appropriate semantics. Static code matches do not prove correctness.
4. Instrument GPU memory allocation and shader compile time; validate on a separate identical test device or an isolated test lab first.
5. Test the FULL standard Material UI end-to-end, not bypass buttons: + New, editing, assigning, shader nodes, preview, multiple objects, save/reload, undo and rollback.
6. Only distribute a device-test build after hardware/system safety is established; do not trigger hard-freeze stress tests on the user's sole device.

## Development priorities
**P0:** Native graphics deadlock root cause, confirm Android 11 driver + EEVEE behavior and revert unsafe changes.
**P1:** Bounded Vulkan allocations (current source patch), modern framebuffer/image-view lifetime and shader cache patches.
**P2:** Material thumbnails rendered on-demand with bounded frame budgets, preserving native Material interface. Requires engine code and hardware testing.
**P3:** Runtime FPS, CPU/GPU load and power optimization after P0 stability is verified.

Do not conflate passing tests, CI packaging or source-level optimization with Android Mali Material stability.