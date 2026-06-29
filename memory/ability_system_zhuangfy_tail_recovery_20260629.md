# AbilitySystemData Zhuangfy Tail Recovery - 2026-06-29

## Summary

This pass resolved the remaining focused `AbilitySystemData` row that did not
emit a `skillDataBundle`: `data_chr_0030_zhuangfy`.

The issue was not encryption and not a broad string-boundary problem. The
`UltMode` `ModeData` tail contained real extended-tail fields that the parser did
not yet understand:

- `overrideStateClip = true`
- empty `overrideClipMapping` header
- `overrideAnimCfg = true`
- `animCfgPath = Data/Json/AnimationConfig/anim_cfg_chr_0030_zhuangfy_ult.json`
- `overrideModelKey = true`
- `modelKey = chr_0030_zhuangfy_ult_postmodel`
- `overrideCmdMapping = true`
- `cmdMapping` entry from `Attack` to `chr_0030_zhuangfy_attack1_ult`

After parsing those fields, the bundle starts naturally at the next offset.

Focused validation result:

```text
json_files 31
parse_errors 0
ability_real_data 28
ability_decoded 28
ability_partial 28
ability_diagnostic 0
ability_unparsed 0
all_unparsed 0
skillBundle_rows 28
skillBundle_combo_zero 1
skillBundle_combo_nonzero 27
missing_skillBundle []
```

This improves `skillBundle_rows` from 27/28 to 28/28.

## Code Change

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now handles the zhuangfy
extended-tail shape:

- `overrideClipMapping` with the observed empty two-word header `[0, 0]`
- `overrideCmdMapping = true` with a bounded BattleCommandType-to-skill-id string
  dictionary

The parser does **not** broaden `IsLikelyAbilitySystemSectionString` to include
`chr_`. That would be unsafe because mode-local fields can legitimately contain
`chr_` strings before the real `SkillDataBundle` boundary.

## Boundary Evidence

The previous compact tail for `UltMode` covered absolute offsets `3384..5112`.
The real extended tail boundary is `3564`.

Key offsets:

```text
3384 overrideStateClip = 1
3388 overrideClipMapping header word 0 = 0
3392 overrideClipMapping header word 1 = 0
3396 overrideAnimCfg = 1
3400 animCfgPath = Data/Json/AnimationConfig/anim_cfg_chr_0030_zhuangfy_ult.json
3468 overrideModelKey = 1
3472 modelKey = chr_0030_zhuangfy_ult_postmodel
3508 mountPointDefIndex = 0
3512 overrideCmdMapping = 1
3516 cmdMapping key count = 1
3520 cmdMapping key = Attack
3524 cmdMapping value count = 1
3528 cmdMapping value = chr_0030_zhuangfy_attack1_ult
3564 SkillDataBundle.allNormalAttackId count = 11
```

The validated zhuangfy `skillDataBundle` prefix now includes:

```text
allNormalAttackId: 11
allActiveSkillId: 7
allPassiveSkillId: 1
normalAttackList: 5
enabledBreakingNormalAttacks: 1
enabledPassiveSkills: 1
comboSkillConditions.count: 2
```

The `UltMode` output now includes:

```text
overrideStateClip: true
overrideClipMapping.headerRawWords: [0, 0]
overrideAnimCfg: true
animCfgPath: Data/Json/AnimationConfig/anim_cfg_chr_0030_zhuangfy_ult.json
overrideModelKey: true
modelKey: chr_0030_zhuangfy_ult_postmodel
overrideCmdMapping: true
cmdMapping.entries:
  Attack -> chr_0030_zhuangfy_attack1_ult
```

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
tmp\ability_system_zhuangfy_tail_after_20260629
```

## Remaining Unknowns

The `overrideClipMapping` header `[0, 0]` is treated as an observed empty mapping
shape. Non-empty clip mappings are still unsupported and should fail back to the
partial diagnostic path rather than being guessed.

The `cmdMapping` dictionary now has proven key/value semantics for the observed
`overrideCmdMapping = true` zhuangfy row. The earlier non-override
`[0, 1, 1, 0] + string-list` form remains preserved as an observed mode
cmd-mapping shape, but the meaning of all header words is still not fully proven.

The next high-value target is decoding `ComboSkillCondition` entries so the
parser can continue past `comboSkillConditions.count` for the 27 rows with
non-empty combo-skill conditions.
