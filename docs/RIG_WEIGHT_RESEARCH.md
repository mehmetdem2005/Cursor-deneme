# Material preview and weight/rig performance research

Device: Redmi Note 8 Pro, Android 11, Mali-G76 MC4, 8GB RAM.

Material Preview invokes Blender EEVEE renderer with Vulkan shaders rather than the cheaper Solid viewport. The upstream Android port acknowledges old Mali driver artifacts and has no OpenGL fallback. Root cause of this particular crash requires a device log; memory and Vulkan pipeline compilation are hypotheses.

Blender's API supports Solid shading with color_type TEXTURE, displaying the active UV mapped image while skipping full EEVEE material rendering.

For posing and weight painting, the safest non-destructive first pass removes only viewport extras (cavity, shadow, specular, motion paths, relationship lines and weight contours), leaves bones and weight colours active, and uses flat solid shading. The profile is applied only on rig mode entry, not each paint dab. Save hooks restore before writing a blend to avoid persisting preview settings. Heavy geometry and deformation remain; next native analysis needs real FPS measurements and a frame/cpu trace. Automatically disabling armature modifiers would break rigging, so it is not done.

Test: enter Weight Paint, turn Rig Lite ON, paint and inspect weight ramps; pose a bone and verify mesh deformation; OFF restores; open existing GLB and try Safe Texture rather than native Material Preview. If still crashing, collect Blender startup log and Android tombstone/logcat.

Previous run-16 remains a fallback.
