# AbilitySystemData SkillDataBundle Prefix Recovery - 2026-06-29

## Summary

This pass recovered the stable prefix of `Beyond.Gameplay.Core.SkillDataBundle`
inside `AbilitySystemData`.

Before this pass, only 1 of the 28 focused `AbilitySystemData` rows emitted a
`skillDataBundle` object after the `ModeData.cmdMapping` fix. Most rows actually
had a valid bundle prefix, but the parser guessed that each non-empty
`comboSkillConditions` list could be represented by one raw word per entry. That
shifted the reader into a managed-reference RID/object payload and caused the
whole bundle helper to return `false`.

After this pass:

```text
json_files 31
parse_errors 0
ability_real_data 28
ability_decoded 28
ability_partial 28
ability_diagnostic 0
ability_unparsed 0
all_unparsed 0
skillBundle_rows 27
skillBundle_combo_zero 1
skillBundle_combo_nonzero 26
cmdMapping_with_values 6
```

Compared with the previous focused output, `skillBundle_rows` improved from
1/28 to 27/28.

## Code Change

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now decodes
`AbilitySystemData.skillDataBundle` through these proven fields:

```text
allNormalAttackId: List<string>
allActiveSkillId: List<string>
allPassiveSkillId: List<string>
normalAttackList: List<string>
enabledBreakingNormalAttacks: List<string>
enabledPassiveSkills: List<string>
normalSkillId: string
ultimateSkillId: string
plungingAttackStartId: string
plungingAttackEndId: string
dodgeSkillId: string
comboSkillConditions.count: int
```

When `comboSkillConditions.count == 0`, the parser continues through:

```text
comboSkillId: string
comboSkillSpecialNodeName: string
```

When `comboSkillConditions.count > 0`, the parser stops after the count and
leaves the condition objects plus later `SkillDataBundle` fields in
`remainingRawWords`. This is intentional: the list entry schema is not decoded
yet, and the count is now represented honestly instead of pretending each entry
is a single raw word.

## Failure Root Cause

For rows such as Yvonne:

```text
normalSkillId                chr_0017_yvonne_normal_skill
ultimateSkillId              chr_0017_yvonne_ultimate_skill
plungingAttackStartId        chr_0017_yvonne_plunging_attack_start
plungingAttackEndId          chr_0017_yvonne_plunging_attack_end
dodgeSkillId                 common_character_perfect_dodge
comboSkillConditions.count   1
```

The next bytes after the count are not `comboSkillId`; they are a
`ComboSkillCondition` object payload with RID links into managed-reference
condition nodes. The old helper consumed one raw word for the condition, then
tried to read `comboSkillId` from the middle of that payload and failed.

The same pattern appears across 26 focused rows with non-empty combo-skill
conditions.

## Validation

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result:

```text
Build succeeded.
14 Warning(s)
0 Error(s)
```

The warnings are existing AnimeStudio/YAML converter warnings, not new compile
errors from this change.

Focused extraction inputs:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk
```

Output root:

```text
tmp\ability_system_skillbundle_after_20260629
```

Representative decoded bundle prefixes:

```text
data_chr_0017_yvonne
  allNormalAttackId: 15
  allActiveSkillId: 4
  allPassiveSkillId: 0
  comboSkillConditions.count: 1

data_chr_0027_tangtang
  allNormalAttackId: 8
  allActiveSkillId: 4
  allPassiveSkillId: 1
  comboSkillConditions.count: 2

data_chr_0028_wulfa
  allNormalAttackId: 8
  allActiveSkillId: 6
  allPassiveSkillId: 1
  comboSkillConditions.count: 2
```

## Remaining Unknowns

`data_chr_0030_zhuangfy` still does not expose `skillDataBundle`. Its remaining
bytes start at a `buff_chr_0030_zhuangfy_dash` string, which suggests the
preceding `UltMode` compact-tail path consumed a large mode tail and likely
crossed the normal bundle boundary. That should be investigated as a separate
mode-tail boundary issue.

The non-empty `ComboSkillCondition` entry schema remains undecoded. Metadata
confirms the field exists as `List<ComboSkillCondition>`, but the current parser
only trusts and emits the count. Next useful work:

- decode `ComboSkillCondition` entries using RID-link evidence and IL2CPP
  metadata
- then parse `comboSkillId`, `comboSkillSpecialNodeName`, and
  `defaultCmdMapping`
- isolate and fix the `zhuangfy` `UltMode` compact-tail boundary so its bundle
  prefix appears like the other rows
