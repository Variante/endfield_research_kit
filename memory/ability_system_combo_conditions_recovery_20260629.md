# AbilitySystemData Combo Condition Recovery - 2026-06-29

## Scope

Focused pass on `Beyond.Gameplay.Core.AbilitySystemData` rows exported from
the three `data_chr_*` chunks previously used for AbilitySystemData recovery.
The goal was to replace the remaining `SkillDataBundle` combo-condition raw
tail with named fields backed by IL2CPP metadata and raw payload offsets.

## Metadata Evidence

`global-metadata.dat` reports IL2CPP metadata v29 with SHA-256:

```text
cf822277f316021dabdce1f21249a01d016e411cea08daf7daa49973e54cc2df
```

The reliable field source for this pass was global metadata plus the
MemoryPack wrapper metadata. Direct DummyDll reflection of `Gameplay.Beyond.dll`
is not reliable in this checkout because the generated assembly contains
duplicate blank type names.

Recovered field order:

```text
Beyond.Gameplay.Core.SkillDataBundle
0  allNormalAttackId: List<string>
1  allActiveSkillId: List<string>
2  allPassiveSkillId: List<string>
3  normalAttackList: List<string>
4  enabledBreakingNormalAttacks: List<string>
5  enabledPassiveSkills: List<string>
6  normalSkillId: string
7  ultimateSkillId: string
8  plungingAttackStartId: string
9  plungingAttackEndId: string
10 dodgeSkillId: string
11 comboSkillConditions: List<ComboSkillCondition>
12 comboSkillId: string
13 comboSkillSpecialNodeName: string
14 defaultCmdMapping: SerializeFieldDictionary<BattleCommandType, string>
```

```text
Beyond.Gameplay.Core.ComboSkillCondition
0 comboSkillEvent: AbilitySystem.Event
1 comboSkillCheckAction: SequenceActionData
2 comboSkillConditionImmediately: bool
```

```text
Beyond.Gameplay.Core.SequenceActionData
0 actionData: managed-reference action/check data list
1 onlyExecuteWhenSourceIsMainChar: bool
2 onlyExecuteWhenSourceIsGuard: bool
```

`SerializeFieldDictionary<TKey,TValue>` serializes `_keyData` before
`_valueData`, which matches the observed `defaultCmdMapping` payload:
key count, int32 keys, value count, aligned string values.

## Parser Change

`AnimeStudio.CLI/Exporter.cs` now passes the managed-reference RID lookup into
`TryReadAbilitySystemSkillDataBundle` and decodes:

```text
comboSkillConditions.count
for each condition:
  comboSkillEvent
  comboSkillCheckAction.actionData.count
  comboSkillCheckAction.actionData[] managed-reference RIDs
  comboSkillCheckAction.onlyExecuteWhenSourceIsMainChar
  comboSkillCheckAction.onlyExecuteWhenSourceIsGuard
  comboSkillConditionImmediately
comboSkillId
comboSkillSpecialNodeName
defaultCmdMapping
```

The parser guards counts, requires combo action RIDs to resolve to recovered
managed-reference headers, and falls back to the existing partial diagnostic path
if the structure does not match.

Observed `AbilitySystem.Event` values are now annotated with names:

```text
9   OnAddedBuff
12  OnTakeDamage
13  OnOutputDamage
21  OnPoiseZero
60  OnAfterTakePhysicalInfliction
101 OnBeforeTakeDamage
102 OnOutputBuff
121 OnEnemyBeforeTakeSpellInfliction
151 OnSetWeakness
204 OnBuffEndsEarly
205 OnBeforeAddedBuff
241 OnPoiseKnotBreak
302 OnBeforeOutputDamage
```

## Validation

Command pattern:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe <chunk> tmp\ability_system_combo_conditions_named_after_20260629\<chunk> --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op All --map_type JSON --export_type JSON --types MonoBehaviour:Both --names '^data_chr_' --dummy_dlls tools\DummyDll
```

Chunks:

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
SkillDataBundle rows: 28
defaultCmdMapping rows: 28
comboSkillCondition entries: 36
combo action managed-reference links: 94
```

`defaultCmdMapping` keys are `(0, 3, 4)` for all 28 rows, matching:

```text
Attack
NormalSkill
ComboSkill
```

All recovered `SequenceActionData` bool fields are false in this focused corpus.
The only non-empty `comboSkillSpecialNodeName` is:

```text
data_chr_0028_wulfa_p257DC63C8AB3111F: ComboRingQte
```

## Remaining Unknowns

This pass decodes through `SkillDataBundle.defaultCmdMapping`. Later
`AbilitySystemData` sections still remain in `remainingRawWords`; the largest
focused row after this change is `data_chr_0028_wulfa` with 359 remaining raw
words. The next useful target is the section following `SkillDataBundle`, likely
UI, attribute, or entity-related ability configuration based on the remaining
string hints.
