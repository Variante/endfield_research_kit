# Projectile MoveModeData curve recovery - 2026-07-03

## Scope

Follow-up from the refreshed MonoBehaviour frontier using
`tmp/decoded_index_mono_refreshed_20260703`. The largest current residual group
was `MonoBehaviour/StreamingAssets/camera/cinematic/class_ProjectileTemplateData`
with 300 partial files.

Those 300 files are not whole-record decode failures. The serialized TypeTree
still fails while reading the managed-reference registry, but AnimeStudio's
custom registry recovery emits bounded `ProjectileComponentData` payloads.
`ProjectileComponentData.tail.structuredRemainingTail` decoded in all 300
files.

## Evidence

Before this pass, the focused 300-file projectile slice had:

- 306 `MoveModeData` records.
- 292 `MoveModeData/StructuredSuffix` records with
  `structuredDecodeStatus = decoded`.
- 14 `MoveModeData/StructuredSuffix` records with
  `structuredDecodeStatus = failed`.
- The failures were all inside Unity `AnimationCurve` decoding for
  `speedCurve` or `speedScaleWithDistance`.

Runtime metadata check:

```text
Beyond_Gameplay_Core_ProjectileComponentData_MoveModeDataForMemoryPack.set___speedCurve__
Beyond_Gameplay_Core_ProjectileComponentData_MoveModeDataForMemoryPack.set___speedScaleWithDistance__
Beyond_Gameplay_Core_ProjectileComponentData_MoveModeDataForMemoryPack.set___angularSpeedCurve__
```

all take `UnityEngine.AnimationCurve`, so the exporter should keep using the
Unity curve layout here. `Beyond.FAnimationCurve` exists in metadata, but it is
not the `MoveModeData` curve setter type.

## Change

AnimeStudio now reads `AnimationCurve` keyframe float fields with the existing
non-finite-preserving helper instead of rejecting infinity. This keeps Unity
constant/stepped tangent sentinels such as `0x7f800000` as explicit diagnostic
objects:

```json
{ "$nonFinite": "Infinity", "rawInt32": 2139095040, "rawHex": "0x7f800000" }
```

## Validation

Rebuilt the AnimeStudio CLI:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Build result: succeeded with the existing 14 warnings and 0 errors.

Re-exported the three VFS chunks that contain the current 300 projectile
frontier files:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\projectile_curve_after_20260703\68 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_projectile"
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\projectile_curve_after_20260703\fbad --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_projectile"
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\projectile_curve_after_20260703\71 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_projectile"
```

After the change:

- 300 focused projectile JSON files exported.
- 306 `MoveModeData` records found.
- 300/300 `ProjectileComponentData.tail.structuredRemainingTail` records still
  decoded.
- 301 `MoveModeData/StructuredSuffix` records decoded.
- 5 `MoveModeData/StructuredSuffix` records still failed.
- 15 non-finite curve tangent values were preserved explicitly instead of
  aborting the structured suffix view.

Remaining `MoveModeData/StructuredSuffix` field-level failures:

- 2 rows:
  `invalid AnimationCurve keyframe count 26 in ...speedScaleWithDistance`
- 1 row:
  `invalid AnimationCurve keyframe count 1119748096 in ...speedCurve`
- 1 row:
  `invalid AnimationCurve wrap mode 1106247680 in ...speedScaleWithDistance.postInfinity`
- 1 row:
  `invalid AnimationCurve keyframe count 1106247680 in ...speedCurve`

## Current boundary

Do not promote the remaining 5 rows to a named schema yet. Their bytes are
bounded and preserved, and fields decoded before the failing curve remain in
`structuredSuffix`, but the failing curve bodies look like separate serialized
curve-info or sampled-curve variants rather than standard Unity
`AnimationCurve` records. Treat them as the next small projectile sub-frontier,
not as evidence that the parent `ProjectileComponentData` boundary is wrong.
