# Gacha light cull-view and survivor contract

This is an offline audit of the installed fallback binaries and the selected
Gacha camera/room evidence. Endfield and Unity were not launched. The checker
was regenerated and then passed with `--check` on 2026-08-14.

Inputs:

- `GameAssembly.dll`: SHA-256
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
- `UnityPlayer.dll`: SHA-256
  `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`
- `global-metadata.dat`: SHA-256
  `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`
- regenerated source audit:
  `scratch/reverse_engineering/gacha_light_cull_view/audit.json`, SHA-256
  `5f60c4388d1b771efdfe18d4642a3e01ffebc1e6cade14093b3e615de22f0629`.

## Shipped cull mode and generic gate

The installed shipped route is normal light culling, not the fallback path:
the native manager constructor writes zero to `manager+0x9d8`, the managed
`useFallbackLightCulling` setter has no direct UnityPlayer call/jump, and its
only absolute pointer is the internal-call registry slot. The normal/fallback
branch at `UnityPlayer!0x181051A5E` therefore selects the normal candidate
core for the source-closed installed state.

The selected Gacha physical camera supplies occlusion dimensions `0 x 0`, so
the native occlusion allocation/update path is skipped. For each active
`SceneLight6Rarity` row, native initialization writes:

```text
genericRecord.mask  = 1 << GameObject.layer
genericRecord.flags = 0x701
```

Gacha room activation moves the room to layer 30. The selected camera cull
view mask is `0x40010008`, so all twelve authored room rows pass the exact
generic gate at `UnityPlayer!0x181051FDE`:

```text
genericRecord.flags bit0 &&
(genericRecord.mask & selectedCullView.mask) != 0
```

This gate is not the final cull result. `HGCamera` calls `CullLights` before
`DispatchBatchCullingJobs`; the latter consumes existing view batches and is
not the producer of the Light record or the synchronous temporary AABB bit.

## Exact authored-room constraints

The normal native core accepts punctual types 0 and 2, uses a 256-row visible
input cap, and sorts accepted rows by priority then ascending camera-distance
squared before applying the live `HGSettingParameters.punctualLightMaxCount`.
All twelve authored room priorities are zero and no distances tie.

`Spot Light (20)` is guaranteed absent on the settled camera sample at
`t=10.7`. It fails the point-sphere top-plane branch with the
aspect-independent squared rejection margin `81.4967041015625`
(`0x42A2FE50`), before the unresolved horizontal AABB planes. Therefore the
authored room can contribute at most eleven rows.

If admitted, the remaining rows have this exact strict relative order:

1. `Spot Light (12)`
2. `Spot Light (19)`
3. `Linear Light (12)`
4. `Linear Light (13)`
5. `Linear Light (14)`
6. `Spot Light (17)`
7. `Linear Light (15)`
8. `Spot Light (18)`
9. `Spot Light (9)`
10. `Spot Light (11)`
11. `Spot Light (10)`

This is a subsequence constraint, not an exact selected-list reconstruction:
unrelated native Light entities on admitted layers can interleave, any of the
eleven can still fail the live horizontal-plane/AABB test, and the punctual
native producer's 256-row result bound can truncate the final list.

The native cull-view predicate itself is now source-pinned. The ordinary
scheduled batch path tests the candidate AABB center/extent against six
normalized planes stored at view `+0x58/+0x5C`; only `cameraType == 0x80`
selects the alternate distance predicate
`distanceSquared <= (max(candidateExtent) + view.occlusionScreenSizeMinimumSquared@+0x34)^2`.
Neither selected predicate reads the constructor's screen-size word at view
`+0x18`. Thus “horizontal AABB” is no longer an unknown native equation: the
remaining uncertainty is the live plane values, candidate bounds, camera type,
and unrelated native-light population for the settled frame.

The desktop settings/culling-cap audit resolves
`PunctualLightMaxCount=256`. `HGCullingSystem.CullLights` is already invoked
with `maxCount=256`, so `SetupState`'s `min(survivorCount, cap)` cannot further
truncate that native result on the installed Windows route. This closes the
runtime cap as a remaining unknown; it does not close the horizontal AABB
planes, the complete unrelated native-light population, or the live camera
cull-view inputs. The generated source evidence is
`unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/light_cull_cap_recovery.json`.

## Recovery boundary

The cull mode, room layer/mask gate, one guaranteed authored exclusion, native
sort order, and authored maximum contribution are now source-pinned. The
remaining lighting inputs are the live final render-target aspect/culling
matrix and candidate bounds (which supply the six plane values and AABB test
inputs), the selected camera type/cull-view state, and the complete unrelated
native-light population. The desktop punctual-light cap is source-closed at
256 and adds no further truncation because the native producer already
receives `maxCount=256`. No Unity or lab patch is justified by this audit, and
authored JSON is not substituted for native cull output.

Reproduce with:

```bat
python scratch\reverse_engineering\gacha_light_cull_view\audit_gacha_light_cull_view.py --check
python unity_endfield_graph_shader_lab\tools\audit_light_cull_cap.py --check
```
