# AbilitySystemData Entity Blackboard Recovery - 2026-06-29

## Scope

Focused pass on `Beyond.Gameplay.Core.AbilitySystemData.entityBlackboard`,
immediately after `defaultHitEffect`. This pass decodes the focused
`Beyond.Blackboard+DataPair` records and the proven-empty wrappers that follow,
then stops before `skillCameraConfig`.

## Metadata And Raw Evidence

`AbilitySystemData` field order after `defaultHitEffect`:

```text
19 entityBlackboard: List<Beyond.Blackboard+DataPair>
20 bakedMeshPoints: SerializeFieldDictionary<string, AbilitySystemData.BakedMeshPointList>
21 bakedMeshPointBonePathList: List<string>
22 extraShapesData: SerializeFieldDictionary<MountPoint, BasicShapeData>
23 skillCameraConfig: SerializeFieldDictionary<string, SkillCameraConfig>
```

`Beyond.Blackboard+DataPair` metadata fields:

```text
key: string
valueDouble: double
valueStr: string
isDynamic: bool
```

The raw focused payloads match this direct order for `entityBlackboard`. This is
different from the earlier `BuffInput.assignItems` payload, which uses a custom
assign-pair layout rather than direct `DataPair` field order.

After `entityBlackboard`, all focused rows have empty wrappers for:

```text
bakedMeshPoints
bakedMeshPointBonePathList
extraShapesData
```

The next non-empty section is `skillCameraConfig`, so this pass stops there.

## Parser Change

`AnimeStudio.CLI/Exporter.cs` now exposes:

```text
entityBlackboard.count
entityBlackboard.entries[].key
entityBlackboard.entries[].valueDouble
entityBlackboard.entries[].valueStr
entityBlackboard.entries[].isDynamic
bakedMeshPoints
bakedMeshPointBonePathList
extraShapesData
```

The parser uses a local reader and advances the main reader only after all
entries and the three empty wrappers decode. `ManagedReferencePayloadReader` now
has a finite `ReadDouble` helper for these `DataPair.valueDouble` fields.

## Validation

Command pattern:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe <chunk> tmp\ability_system_entity_blackboard_after_20260629\<chunk> --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op All --map_type JSON --export_type JSON --types MonoBehaviour:Both --names '^data_chr_' --dummy_dlls tools\DummyDll
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
entityBlackboard rows: 28
bakedMeshPoints rows: 28
extraShapesData rows: 28
```

`entityBlackboard` count distribution:

```text
0: 18 rows
1: 5 rows
2: 2 rows
3: 1 row
4: 1 row
6: 1 row
```

Observed keys:

```text
EntityBB_isCombo
EntityBB_combo_index
EntityBB_combo_type
EntityBB_skill_bg_type
EntityBB_ns_atkscale1
EntityBB_ns_atkscale2
EntityBB_ns_atb
EntityBB_abilityentity_water01
EntityBB_abilityentity_water02
EntityBB_abilityentity_water03
EntityBB_abilityentity_rate_spellvulnerable
EntityBB_abilityentity_rate_spellvulnerable_02
EntityBB_abilityentity_duration_spellvulnerable
EntityBB_ComboUseCount
EntityBB_Combo_QTE_Trigger
EntityBB_Combo_qte_proto_use
EntityBB_NormalSkill_wolf_gain_usp
EntityBB_noguard_count
EntityBB_atb_contain
EntityBB_SwordNum
EntityBB_normalskill_1_moveto
```

All observed entries have an empty `valueStr` and `isDynamic = true`.
Non-zero numeric values observed:

```text
EntityBB_combo_type = 2.0
EntityBB_skill_bg_type = 99.0
EntityBB_Combo_qte_proto_use = 1.0
```

## Remaining Unknowns

The remaining raw tail now starts at:

```text
skillCameraConfig: SerializeFieldDictionary<string, SkillCameraConfig>
```

That section has non-empty dictionaries and nested `SkillCameraConfig` values
containing clip references, path hashes, and collision shape lists. It should be
handled in a separate pass. Later sections still include effect settings,
health type, preload ability entities, and `maxPotentialEffectBuffId`.
