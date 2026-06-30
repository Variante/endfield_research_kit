# AbilitySystemData Skill Camera Recovery - 2026-06-29

## Scope

Focused recovery pass for `Beyond.Gameplay.Core.AbilitySystemData.skillCameraConfig`
inside the `data_chr_*` MonoBehaviour rows exported from the three focused
StreamingAssets VFS chunks:

- `68B3B9B8EB82E88FBFE6A313E6B18FB6.chk`
- `71FC2E71A9F249B382BF8DAED3BCEE65.chk`
- `FBAD673F662CF3EACDDB14A65999F7EF.chk`

Validation output:

- `tmp/ability_system_skill_camera_named_after_20260629/`

## Implemented

AnimeStudio now reads `skillCameraConfig` immediately after the recovered
`entityBlackboard`, `bakedMeshPoints`, `bakedMeshPointBonePathList`, and
`extraShapesData` section.

Recovered layout:

```text
SerializeFieldDictionary<string, Beyond.Gameplay.Core.SkillCameraConfig>
  keys.count
  keys[] as aligned strings
  values.count
  values[] as:
    clip: Unity PPtr<AnimationClip>
    clipPathHash: int64
    collideShapeList: List<Selector.HitBoxFinder.ShapeData>
```

`ShapeData` is decoded as:

```text
shapeType
positionRef
posRefMP
directionRef
dirRefMountPoint
centerOffset: BlackboardVector3
eulerAngle: BlackboardVector3
size: BlackboardVector3
radius: BlackboardDouble
height: BlackboardDouble
limitAngle
angle: BlackboardDouble
limitHeight
maxHeight: BlackboardDouble
useDirection
castDirection
enablePreview
hitEffectTowardsType
```

The `BlackboardDouble` wrapper is still emitted conservatively as three raw
int32 words plus `valueFloatCandidate`, because the IL2CPP metadata exposes the
wrapper type but not enough internal fields to name the three serialized words.

## Validation

Command shape:

```bat
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  <chunk> tmp\ability_system_skill_camera_named_after_20260629 ^
  --game ArknightsEndfield --logger_flags Warning Error ^
  --group_assets ByType --map_op All --map_type JSON ^
  --export_type JSON --types MonoBehaviour:Both --names "^data_chr_" ^
  --dummy_dlls tools\DummyDll
```

Results:

- JSON files: 29 total, including `assets_map.json`.
- `data_chr_*` MonoBehaviour files: 28.
- JSON parse errors: 0.
- `AbilitySystemData` rows: 28.
- rows with `skillCameraConfig`: 28 / 28.
- `skillCameraConfig` value count: 37.
- `collideShapeList` value distribution: 32 values with count 0, 5 values with count 1.
- named `ShapeData` records: 5.
- `$diagnostic` rows in focused `AbilitySystemData`: 0.
- `$unparsed` markers in focused `AbilitySystemData`: 0.

Dictionary key count distribution:

- 22 rows: 1 key.
- 5 rows: 2 keys.
- 1 row: 5 keys.

Observed camera keys:

- `UltimateSkillCamera`: 25
- `UltimateSkillCameraNew`: 3
- `UltimateCamera`: 2
- `UltCamNew`: 1
- `UltimateSkillCamera1`: 1
- `UltCam_1`: 1
- `UltCam_2`: 1
- `UltCam_begin`: 1
- `UltCam_attack`: 1
- `UltCam`: 1

Rows with non-empty `collideShapeList`:

| row | key | centerOffset candidate | size candidate | useDirection | enablePreview |
| --- | --- | --- | --- | --- | --- |
| `data_chr_0005_chen` | `UltimateSkillCamera` | `(-0.7196671, 0.9453516, -0.8213718)` | `(2.7473178, 1.5073005, 3.795744)` | true | true |
| `data_chr_0005_chen` | `UltimateSkillCamera1` | `(-0.8923076, 1.9895091, -2.3028257)` | `(2.2159386, 0.9324267, 4.5117946)` | true | true |
| `data_chr_0007_ikut` | `UltimateSkillCamera` | `(0.0, 3.0, 8.5)` | `(1.0, 0.2, 3.0)` | false | true |
| `data_chr_0022_bounda` | `UltimateSkillCamera` | `(0.0, 3.0, 8.5)` | `(1.0, 0.2, 3.0)` | false | true |
| `data_chr_0028_wulfa` | `UltCam_attack` | `(-1.672572, 0.8137293, -0.10148442)` | `(1.5, 0.65, 1.0)` | true | true |

Remaining `AbilitySystemData.remainingRawWords` count distribution after this
pass:

- 114 words: 16 rows.
- 122 words: 3 rows.
- 123 words: 3 rows.
- 124 words: 4 rows.
- 125 words: 1 row.
- 148 words: 1 row.

The remaining tail starts after `skillCameraConfig`, at the later
`AbilitySystemData` fields:

```text
overrideDeadEffect
deadEffect
effectScale
isPlayHitFlash
hitFlashAsset
healthType
preloadAbilityEntities
maxPotentialEffectBuffId
```

## Metadata Evidence

The local IL2CPP metadata source for this pass was:

```text
D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat
```

Metadata/subagent resolution:

- `clip`: `UnityEngine.AnimationClip`.
- `clipPathHash`: `System.Int64`.
- `collideShapeList`: `List<Beyond.Gameplay.Core.Selector+HitBoxFinder+ShapeData>`.
- `ShapeData` enum values used by the parser:
  - `ShapeType`: `Box=0`, `Capsule=2`, `Sphere=4`.
  - `PositionRef`: `OwnerMountPoint=0`, `InputCenter=2`.
  - `DirectionRef`: `OwnerForward=0`, `OwnerMountPoint=2`, `InputDirection=4`.
  - `CastDirection`: `ZForward=0`, `ZBackward=2`, `XForward=4`, `XBackward=6`, `YForward=8`, `YBackward=10`.
  - `HitEffectTowardsType`: `TowardsAttacker=0`, `TowardsHitBoxCenter=2`.

Important caveat: the MemoryPack wrapper metadata does not expose `clip`, but
the Unity serialized MonoBehaviour payloads do include the `clip` PPtr before
`clipPathHash`. The exporter follows the Unity payload layout.

## Remaining Unknowns

- The internal names of the three serialized words in
  `Beyond.Blackboard.BlackboardDouble` are not fully proven. The middle word is
  consistently a float value candidate in all observed `ShapeData` records, so
  the exporter preserves all three raw words and exposes only a candidate value.
- `EffectActionCfg` / `deadEffect` has not been decoded in this pass. It is the
  next large post-camera field and should be handled separately.
- `preloadAbilityEntities` is known from metadata as
  `SerializeFieldDictionary<string, int>`, but remains in the post-camera tail
  until the later AbilitySystemData fields are decoded.
