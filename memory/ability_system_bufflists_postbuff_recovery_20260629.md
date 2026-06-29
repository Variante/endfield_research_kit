# AbilitySystemData Buff Lists And Post-Buff Scalars - 2026-06-29

## Scope

Focused pass on the `Beyond.Gameplay.Core.AbilitySystemData` tail after
`uiData`. This pass decodes the three metadata-backed buff lists and the scalar
section through `defaultHitEffect`, then intentionally stops before
`entityBlackboard`.

## Metadata Evidence

The authoritative field order comes from:

```text
D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat
version: 29
sha256: cf822277f316021dabdce1f21249a01d016e411cea08daf7daa49973e54cc2df
```

Relevant `AbilitySystemData` fields:

```text
4  dashBuff: List<BuffInput>
5  buffDuringPoiseExist: List<BuffInput>
6  buffDuringZeroPoise: List<BuffInput>
7  plungingAttackData: AbilitySystemData.PlungingAttackData
8  battleRootData: AbilitySystemData.BattleRootData
9  poiseBrokenEndTime: float
10 poiseKnotBreakImmobilizeTime: float
11 playPoiseBrokenEffect: bool
12 unlockAfterOutScreen: bool
13 overrideMarkTargetDistance: bool
14 customMarkTargetDistance: float
15 overrideMarkTargetHeight: bool
16 customMarkTargetHeight: float
17 accurateMarkTargetDistance: bool
18 defaultHitEffect: string
19 entityBlackboard: List<Beyond.Blackboard+DataPair>
```

Nested field order:

```text
BuffInput
  buffId: string
  assignBlackboard: bool
  assignItems: List<DataPair>

PlungingAttackData
  startDuration: float
  endDuration: float
  enableOverridePlungingAttackDownSpeed: bool
  overridePlungingAttackDownSpeed: float

BattleRootData
  overrideBattleRoot: bool
  rootMountPoint: MountPoint
```

`BuffInput.assignItems` uses a custom/wrapper-affected `DataPair` layout in this
payload. The observed focused records parse as:

```text
targetKey: string
inputValueKey: string
useDirectValue: bool
directValueType: int32
numericValue: float
stringValue: string
```

The parser keeps count guards and local-reader fallback around this slice.

## Parser Change

`AnimeStudio.CLI/Exporter.cs` now decodes, after `uiData`:

```text
dashBuff
buffDuringPoiseExist
buffDuringZeroPoise
plungingAttackData
battleRootData
poiseBrokenEndTime
poiseKnotBreakImmobilizeTime
playPoiseBrokenEffect
unlockAfterOutScreen
overrideMarkTargetDistance
customMarkTargetDistance
overrideMarkTargetHeight
customMarkTargetHeight
accurateMarkTargetDistance
defaultHitEffect
```

`battleRootData.rootMountPoint` is named for observed low enum values using:

```text
0 None
1 HeadBar
2 FootBar
3 LockPoint
4 HeadStatus
5 DmgTxtSpawnPoint
```

## Validation

Command pattern:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe <chunk> tmp\ability_system_postbuff_after_20260629\<chunk> --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op All --map_type JSON --export_type JSON --types MonoBehaviour:Both --names '^data_chr_' --dummy_dlls tools\DummyDll
```

Focused chunks:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk
```

Results:

```text
json_files: 31
parse_errors: 0
AbilitySystemData rows: 28
AbilitySystemData decoded: 28
AbilitySystemData diagnostics: 0
AbilitySystemData $unparsed: 0
all $diagnostic: 0
all $unparsed: 0
uiData rows: 28
dashBuff rows: 28
plungingAttackData rows: 28
defaultHitEffect rows: 28
```

Buff-list observations:

```text
dashBuff count 1: 25 rows
dashBuff count 2: 3 rows
buffDuringPoiseExist count 0: 28 rows
buffDuringZeroPoise count 0: 28 rows
```

Observed `dashBuff` IDs:

```text
buff_common_dash: 27
buff_common_dash_immune: 2
buff_chr_0016_laevat_ult_dash: 1
buff_chr_0030_zhuangfy_dash: 1
```

Observed assign item values:

```text
targetKey=dodgeSkillId, inputValueKey="", useDirectValue=true, directValueType=0, numericValue=0.0, stringValue=common_character_perfect_dodge: 30
targetKey=dodgeSkillId, inputValueKey="", useDirectValue=true, directValueType=0, numericValue=0.0, stringValue=chr_0030_zhuangfy_perfect_dodge: 1
```

Post-buff observations:

```text
battleRootData: overrideBattleRoot=false, rootMountPoint=None in all 28 rows
one plunging override: data_chr_0030_zhuangfy, override speed 200.0
no mark-target scalar override outliers in the focused rows
```

`defaultHitEffect` is now decoded for all rows. Eight rows have an empty default
hit effect; the rest point at character/common hit effect ids such as
`P_fxbat_endminm_common_hit_01`, `P_fxbat_chen_common_hit_01`, and
`P_fxbat_mifu_attack_01_hit`.

## Remaining Unknowns

The next remaining section starts at:

```text
entityBlackboard: List<Beyond.Blackboard+DataPair>
```

The focused rows show count-zero and several non-empty `EntityBB_*` variants.
Both metadata and raw probes indicate `DataPair` is custom/wrapper affected, so
it should be handled in its own pass rather than folded into this scalar slice.
Later sections after `entityBlackboard` still include dictionaries, baked mesh
points, extra shapes, skill camera config, effect settings, health type, preload
ability entities, and `maxPotentialEffectBuffId`.
