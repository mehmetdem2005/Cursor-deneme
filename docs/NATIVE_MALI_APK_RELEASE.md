# Blender Lite v33 — Native Mali EEVEE 16MB Budget experimental APK

**WARNING:** The user reported a complete device freeze with Material operations on Redmi Note 8 Pro Android11 Mali-G76. DO NOT treat this APK as safe on that device. This prerelease is for controlled laboratory devices only.

Based on v33 Mali Depth Guard, with original upstream android-alpha-4 libblender.so; no Android API increase.
Adds exact-match binary ARM64 machine-code patch to EEVEE ShadowModule::init() that preserves previously computed min(scene.shadow_pool_size,16) on high-RAM phones by replacing one conditional selection with a NOP.
Verifies actual sysconf PLT callsites, 10 surrounding instructions, and that only 4 bytes change; rejects wrong native engine, architecture, or duplicate patch.
IMPORTANT: This is a binary hotfix to the existing native engine, **not** a complete native rebuild or driver upgrade.
Retains standard Material panel operations; no fake atom-only menu. However Material New, shader compilation, Material Preview and Vulkan GPU driver can STILL freeze or crash. No Mali-G76 test has been performed.

Tests include preexisting Blender Lite regression suite, new ARM64 patch safety tests, signed APK verification, extraction and native opcode verification. These prove APK structure and precise patch insertion only.
GPU FPS, power, shader performance, scene reliability and Material stability are unmeasured and **not guaranteed**.
Preserved v31 original byte-for-byte in dual-APK ZIP. APKs share org.blender.blender; backup files and original APK before any install.
Native patch details: scripts/patch_native_mali_shadow_elf.py, 0x27D817C `csel w9,w9,w23,gt` -> AArch64 NOP (0xd503201f).
Patch changes one EEVEE memory condition only, not the other native Vulkan framebuffer lifetime issues.

**Do not test on your only phone.** Hardware lab acceptance must precede claiming repair.