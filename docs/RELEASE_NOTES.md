# Compact UI + GPU Rescue (Android 11 Mali)

The previous v27 4x buffer divisor was too aggressive for a small landscape display: the Blender interface became oversized and hard to navigate. The screenshot also shows the Android on-screen keyboard covering the bottom half after the ViewLayer text field was focused. Back exits the keyboard; it is not a viewport panel.

This release reverts to framebuffer divisor=2 (one half display width and height, one-quarter of native rendered pixels). The app-scoped property hook also supplies debug.blender.uidpi=96, a value explicitly supported by the upstream GHOST_AndroidMemoryTier.hh, to make menus/headers more compact. This DPI is app-scoped; the phone's system display density is unchanged.

The same single-module Ultra GPU runtime remains: Solid/Flat shading, AA off, anisotropic filtering off, texture upload clamp 128, GPU subdivision disabled, viewport Simplify subdivision level 0, shadow/cavity/specular/extra overlays off, armature STICK, 3-minute native auto-save. Necessary bone and Weight Paint overlays stay on.

Automatic BOUNDS mode in Armature Edit is now OFF by default so the user can still see the real mouse model while placing bones. Optional View > Ultra GPU / Rig Rescue > Bone Edit: show mesh as box remains available on demand; it restores the original mesh display in Weight Paint.

This change is **not** a native Mali/Vulkan geometry corruption fix; old driver triangles may still appear. It only fixes the egregious resolution/UI scaling regression while keeping much of GPU savings. Image visual correctness and crash-free 6+ bone edits require real-device verification.

IMPORTANT: Save projects outside app-private storage before reinstalling: Actions signs releases with temporary keys. On the user's screenshot, the Android keyboard can be dismissed using system Back after exiting ViewLayer text editing. If this build cannot open, the known v23 and v27 releases remain available.

Do not automatically decimate or remove mesh data; retain original weights, armature and UV data.
