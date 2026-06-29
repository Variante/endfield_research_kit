# AbilitySystemData Recovery - 2026-06-29

## Summary

This pass focused on the remaining focused `data_chr_*` `AbilitySystemData`
records that still fell through to generic `$unparsed` output.

Result on the three targeted installed chunks:

- JSON files exported: 31
- JSON parse errors: 0
- real `AbilitySystemData` records: 28
- `AbilitySystemData` records with `$decoded`: 28
- `AbilitySystemData` records with `$partial`: 28
- diagnostic partial `AbilitySystemData` records: 2
- `AbilitySystemData` records still marked `$unparsed`: 0
- all `$unparsed` records in this focused slice: 0

The exporter change is intentionally diagnostic for the two problematic rows,
not a claim that the whole payload is fully understood.

## Code Change

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now keeps the existing structured
partial `AbilitySystemData` decode path, but catches `InvalidDataException` for
this type and emits a bounded type-specific diagnostic when the top-level prefix
is plausible:

- `shapeData.detectedRadius`
- `shapeData.detectedHeight`
- `modeConfig.modeCount`
- `modeConfig.modeCountOffset`
- `modeConfig.modePayloadOffset`
- parse-failure message
- aligned string hints from the mode/tail payload
- filtered gameplay string hints from the mode/tail payload
- RID links from the mode/tail payload
- raw word preservation for the mode/tail payload

Regular partial `AbilitySystemData` rows now also include `remainingRidLinks`
when their preserved tail contains managed-reference RID links.

This replaces generic `$unparsed` output for known `AbilitySystemData` prefixes
with explicit `$decoded`, `$partial`, `$diagnostic` output. It does not suppress
the unknowns: the two unresolved rows stay visibly diagnostic.

## Validation

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result:

```text
Build succeeded.
0 Warning(s)
0 Error(s)
```

Focused extraction inputs:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk
```

Output root:

```text
tmp\ability_system_data_diag_final_20260629
```

CLI shape:

```bat
AnimeStudio.CLI.exe <chunk> tmp\ability_system_data_diag_final_20260629\<short> --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op All --map_type JSON --export_type JSON --types MonoBehaviour:Both --names "^data_chr_" --dummy_dlls tools\DummyDll
```

Final counter:

```text
json_files 31
parse_errors 0
ability_real_data 28
ability_decoded 28
ability_partial 28
ability_diagnostic 2
ability_regular_with_remainingRidLinks 23
ability_unparsed 0
all_unparsed 0
```

Diagnostic rows:

```text
data_chr_0017_yvonne_p8AFE39FD805DA3CD.json
  offset 2360 length 2936 modeCount 4
  parseFailure: non-ASCII byte in modeConfig.modes.modeId at 2808
  aligned hints: confront, default, isStrafe, ult, default,
    chr_0017_yvonne_ult_attack1_1, chr_0017_yvonne_ult_attack2_1,
    chr_0017_yvonne_ult_attack2_2, chr_0017_yvonne_ult_attack3_1,
    chr_0017_yvonne_ult_attack3_2, chr_0017_yvonne_ult_attack1_1,
    ult_end
  RID links: CheckDamageDecorateMask/Data, CheckTargetsEqual/Data,
    CheckTagMatch/Data, CheckObjectTypeMatch/Data

data_chr_0027_tangtang_p6912F02D53A7F3E0.json
  offset 2292 length 2980 modeCount 3
  parseFailure: non-ASCII byte in modeConfig.modes.modeId at 2720
  aligned hints: confront, default, isStrafe, ult, default,
    chr_0027_tangtang_attack1, chr_0027_tangtang_attack2,
    chr_0027_tangtang_attack3, chr_0027_tangtang_attack4,
    chr_0027_tangtang_attack5, chr_0027_tangtang_ult_attack3,
    ult_end
  RID links: CheckDamageDecorateMask/Data, CheckObjectTypeMatch/Data,
    CheckSpellInflictionType/Data
```

## Metadata Evidence

The IL2CPP metadata pass used:

```text
D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat
SHA-256 CF822277F316021DABDCE1F21249A01D016E411CEA08DAF7DAA49973E54CC2DF
metadata version 29

D:\Program Files\Endfield Game\GameAssembly.dll
SHA-256 94031E453C02DA2BA185493A9E2D7EC76D8409F4239CA7D48DBB27B840E61284
```

Field order for `Beyond.Gameplay.Core.AbilitySystemData`:

```text
0 shapeData: Beyond.Gameplay.BasicShapeData
1 modeConfig: Beyond.Gameplay.Core.ModeConfig
2 skillDataBundle: Beyond.Gameplay.Core.SkillDataBundle
3 uiData: AbilitySystemData.UIData
4 dashBuff: List<BuffInput>
5 buffDuringPoiseExist: List<BuffInput>
6 buffDuringZeroPoise: List<BuffInput>
7 plungingAttackData: AbilitySystemData.PlungingAttackData
8 battleRootData: AbilitySystemData.BattleRootData
9 poiseBrokenEndTime: float
10 poiseKnotBreakImmobilizeTime: float
11 playPoiseBrokenEffect: bool
12 unlockAfterOutScreen: bool
13 overrideMarkTargetDistance: bool
14 customMarkTargetDistance: float
15 overrideMarkTargetHeight: bool
16 customMarkTargetHeight: float
17 accurateMarkTargetDistance: bool
18 defaultHitEffect: string
19 entityBlackboard: List<Beyond.Blackboard.DataPair>
20 bakedMeshPoints: SerializeFieldDictionary<string, AbilitySystemData.BakedMeshPointList>
21 bakedMeshPointBonePathList: List<string>
22 extraShapesData: SerializeFieldDictionary<MountPoint, BasicShapeData>
23 skillCameraConfig: SerializeFieldDictionary<string, SkillCameraConfig>
24 overrideDeadEffect: bool
25 deadEffect: Beyond.Gameplay.EffectActionCfg
26 effectScale: float
27 isPlayHitFlash: bool
28 hitFlashAsset: string
29 healthType: Beyond.Gameplay.Core.HealthType
30 preloadAbilityEntities: SerializeFieldDictionary<string, int>
31 maxPotentialEffectBuffId: string
```

`ModeData` field order is also known from metadata and matches the current prefix
parser through `animBoolName`. The unresolved area is the dictionary-heavy tail:

```text
overrideStateClip: bool
overrideClipMapping: SerializeFieldDictionary<int,string>
overrideAnimCfg: bool
animCfgPath: string
overrideModelKey: bool
modelKey: string
mountPointDefIndex: int
overrideCmdMapping: bool
cmdMapping: SerializeFieldDictionary<BattleCommandType,string>
```

## Remaining Unknowns

The two diagnostic rows are probably not encrypted. They start with the same
valid shape floats and mode-vector signature as the decoded rows. The failure is
more likely an unhandled `ModeData` dictionary/tail variant around `ult` /
`confront` mode data.

The payload tail after `skillDataBundle` is not fully decoded yet. Metadata shows
it contains `uiData`, buff lists, plunging/battle-root data, blackboard data,
dictionaries, effects, health type, preload ability entities, and potential buff
id. Current JSON preserves that tail as strings, RID links, and raw words.

Next useful parser work:

- implement real `SerializeFieldDictionary<K,V>` decoding for `ModeData`
  `overrideClipMapping`, `cmdMapping`, and `SkillDataBundle.defaultCmdMapping`
- use the metadata field order to parse `AbilitySystemData.uiData` and simple
  scalar fields after `skillDataBundle`
- only then attempt the nested list/dictionary fields such as buff lists,
  baked mesh points, extra shapes, skill camera config, and preload ability
  entities
