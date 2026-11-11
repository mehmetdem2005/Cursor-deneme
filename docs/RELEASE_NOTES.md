# Minimal Ultra GPU Rescue for Android 11 Mali

Experimental; not tested on the actual Redmi Note 8 Pro. Previous v24–v26 GitHub jobs were still queued at last check, so do not assume a new APK is ready.

This variant bundles ONLY addon/ultra_survival.py as the Blender startup module. Old 40KB+ diagnostic addon remains in GitHub for reference, but is NOT loaded into the APK. It removes overlapping save handlers, repeated logging and extra timers.

GPU settings: 4x native framebuffer divisor (1/4 of width and height; 1/16 pixels), native low-memory mode, Solid/Flat viewport, antialiasing and anisotropic filtering off, texture limit 128, GPU Subdivision off. Blender Render Simplify is on with viewport subdivision max level 0 and viewport volume resolution 0. Weight color and bone selection overlays remain enabled.

Additional automatic per-mode GPU optimization: in EDIT_ARMATURE mode only, meshes bound to the active armature use BOUNDS instead of full triangles. They revert to their original display type when leaving Edit Armature, including on entry to PAINT_WEIGHT. Armature itself uses STICK. A single lightweight timer detects mode changes every ~1.1 seconds; the system does not toggle every brush stroke.

Use View > Ultra GPU / Rig Rescue to disable box view if the mesh silhouette is needed to align bones. Use Ultra GPU OFF to restore original scene/display settings before a final Save As. If a recovery file is saved while the profile is active, Blender may save its temporary display and simplify settings, but bone weights and geometry are unchanged.

Blender's native 3-minute Auto Save and Recover Auto Save menu remain. Edit Mode changes may be missing from native temporary autosaves; manually save after bone milestones.

CAUTION: the 4x downscaled window may make touch precision unusable, and pixel reduction does not guarantee 93.75% faster rig operations. Bone deletion crashes may come from Blender native armature code or Mali Vulkan driver, which requires logcat to diagnose.

Code, tests and APK packaging can be validated by CI when GitHub starts the queued run. A queued workflow is not a downloadable APK.
