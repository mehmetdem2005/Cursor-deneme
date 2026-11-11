# Armature edit crashes: structured root-cause investigation

## Hardware and reproduction
Redmi Note 8 Pro, Android 11, 8GB RAM, Mali-G76. Armature begins crashing after creating several bones and during deletion of bones after the fifth. This is NOT an expected Blender per-armature bone limit.

## Competing hypotheses
1. Overlay armature GPU drawing or selection-buffer defect on Mali Vulkan: adding bones increases instancing and picking draws. Test STICK drawing style versus default octahedral.
2. Heavy GLB mesh + armature dependency and resource exhaustion: test pure armature scene; use temporary bounds display for linked meshes to isolate.
3. Upstream bug in editbone manipulation / selection / undo / bone collections: Blender has issue reports #140636, #151082, #164168, #165778, some fixed upstream. Identify source revision and compare native stack before cherry-picking patches.
4. Native code import hooks and adaptive event loop in this project's Android 11 APK: previous full-buffer run-20 is available; native event hook effects are not excluded.
5. Resource limits/Android low-memory killer: obtain kernel/Android exit reason and memory log. Do not infer from 8GB RAM that memory cannot run out.

## Changes in this trial
An opt-in Python UI switch changes Armature.display_type to STICK and can optionally change selected armature-linked Mesh object's display_type to BOUNDS. No editbone/posebone mutation, no bound mesh deletion, no modifier removal and no GPU driver patch. User can restore manually, and a save hook prevents writing the temporary appearance to the project. A monitor uses len(edit_bones) in edit mode and len(bones) otherwise every 750ms, logs only changes, and does not hold native RNA editbone references across deletion. If the fatal crash occurs immediately after a bone delete the last count can be the prior one.

## Not guaranteed
If the native crash is in armature data structures or undo, changing only display draw style will NOT fix it. A reproducible empty-scene .blend and native tombstone / symbolicated trace are the next minimum inputs.

Upstream armature overlay: source/blender/draw/engines/overlay/overlay_armature.cc
Upstream Android port: https://blenderandroid.github.io/
Bug examples:
https://projects.blender.org/blender/blender/issues/140636
https://projects.blender.org/blender/blender/issues/151082
https://projects.blender.org/blender/blender/issues/164168
