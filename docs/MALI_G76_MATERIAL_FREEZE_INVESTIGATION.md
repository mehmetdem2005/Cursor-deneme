# Blender Lite v33 material-induced WHOLE PHONE freeze: Mali-G76

Status 2026-11-20: CRITICAL, root cause unconfirmed. STOP risky on-device reproductions.
User reports phone display and physical lock/power button unresponsive while operating Material UI, requiring forced reboot.
Installed exact APK during hard freeze has not been established. This is more severe than normal Blender ANR.

## Version evidence
- v33 release: android11-exp-run-34, base 06694e9f804404c24367da9f7a600f17f012f08e.
- Current Android repo repacks a prebuilt libblender.so from simfeo/blender android-alpha-4; no native Vulkan source rebuild.
- Build 37 added separate material-color menu (NOT standard UI repair).
- Build 39 remapped Material + and New to Python, disabled preview thumbnail; device-wide safety NOT verified.

## Inspected source: concrete high-memory risk
- Upstream source source/blender/draw/engines/eevee/eevee_shadow.cc in simfeo/blender android-alpha-4.
- Code comments describe 512MB shadow atlas allocation even for small material preview.
- Native code caps shadow pool to 16MB ONLY if physical memory < 6 GiB.
- On an 8GB Android phone this cap may not engage. Physical RAM is not Vulkan GPU memory budget.
- Newer Wanderson-Magalhaes/blender_for_android v5.3.0-android caps EEVEE shadow pool at 64MB regardless of RAM.
- This code difference is proven. Its causality for this phone freeze is NOT proven.

## Source patch experiments implemented but NOT released as APK
- Python startup candidate limits scene.eevee.shadow_pool_size RNA enum to 16 MB on all scenes.
- SOURCE-only patch scripts/patch_mobile_shadow_pool.py removes old <6GiB condition; requires native rebuild.
- Offline tests/test_material_gpu_budget.py verifies behavior without any Android GPU.
- No phone test or publication is safe yet. Shadow quality changes and the Blender scene property may persist in saved projects.

## Additional risk evidence
- ARM G76 MC4 Redmi Note 8 Pro Vulkan shader/UBO issues: https://community.arm.com/forums/f/mobile-graphics-and-gaming-forum/47814/mali-g76-mc4-vulkan-driver-bug
- Another engine reports Mali G76 Vulkan issues under Android 10/11: https://forums.unrealengine.com/t/artifacts-and-crashes-on-some-android-gpus-and-versions-when-vulkan-is-enabled/2536208
- Latest Blender Android 5.3 changed Vulkan resource/framebuffer lifetime; source and APK require Android 12+: https://blenderandroid.github.io/updates/2026-11-11-s24-v5-3-0-android/

## Diagnostic and acceptance
Do not rerun Material Add / New on target device until source-level Vulkan fixes are validated on test hardware.
An Android bugreport after restart (without relaunching Blender) may capture prior GPU/ANR issues but availability varies by OEM.
Logs may contain private information; redact before sharing publicly. No root, reflashing or random GPU driver APK.
Acceptance requires full standard Material UI (+ slot, New, copy, nodes, color, roughness, assign, save/reload, preview) on real Android11/Mali-G76, without a system freeze.

Never equate GitHub CI Python success with GPU driver success.