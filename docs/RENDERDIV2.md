# Half-resolution Vulkan buffer experiment — 8 GB Mali device

This application is for Redmi Note 8 Pro (8 GB variant) with Android 11 and Mali-G76 MC4. The upstream Android port uses a 6 GiB threshold before halving window buffers, so a device with ~8 GiB normally keeps full resolution.

## Mechanism

Upstream `intern/ghost/intern/GHOST_AndroidMemoryTier.hh` contains a property override `debug.blender.renderdiv`, used by both render buffer geometry and input coordinate mapping. Android user apps cannot write `debug.*` system properties directly.

We therefore ship a scoped native ELF shim. `libblender.so` imports `__system_property_get@LIBC` from Bionic. The deterministic patch renames only this import to a unique unversioned symbol `blender_renderdiv_get`, and adds `DT_NEEDED=librenderdiv_shim.so`. The wrapper returns string `2` for this ONE property and delegates every other system property lookup to Bionic. This bypasses no Android privilege; the value remains private to Blender.

This enables the existing native geometry code (`ANativeWindow_setBuffersGeometry`) to halve dimensions, and its input mapping logic to scale coordinates. A 2000x900 display should render ~1000x450 pixels: 75% fewer buffer pixels, with Android upscaling.

## Limitations

- Upstream uses Vulkan only; it has no GLES fallback. Some Mali-G76 driver rendering artifacts may remain.
- Exact output resolution, GPU FPS and startup compatibility must be verified on a real phone.
- Rendering UI may be less sharp; if unreadable revert immediately.
- `viewport_aa=OFF` is set to reduce the chance of Android 11 Mali MSAA faults. This can produce jagged edges.
- Pixel count decrease is not a comparable 75% RAM reduction or FPS increase.
- Existing work remains safe only if user saves files to shared storage and backs up before uninstall; test-key rotation requires uninstall/reinstall.
- Future clean fix: compile the upstream native engine with a device- or preference-driven buffer divisor rather than patched ELF imports.
