# AbilitySystemData CmdMapping Recovery - 2026-06-29

## Summary

This pass resolved the two `AbilitySystemData` diagnostic rows left by the
previous recovery pass. The issue was not encryption. The current parser stopped
inside `ModeData.cmdMapping` because it treated the mapping as exactly four raw
words. Some modes have those four header words followed by a bounded string-list
value segment.

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
cmdMapping_with_values 6
```

Compared with the prior pass, `ability_diagnostic` dropped from 2 to 0 while
`$unparsed` stayed at 0.

## Code Change

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now parses
`ModeData.cmdMapping` through `ReadAbilitySystemModeCmdMapping`:

- always preserves the four observed header words
- treats `[0, 0, 0, 0]` as the empty mapping form
- treats `[0, 1, 1, 0]` as the observed non-empty form and consumes the following
  bounded string list
- leaves any other header shape visible with a `layoutNote` instead of guessing

The helper intentionally names this as a mode cmd-mapping layout rather than a
fully proven generic `SerializeFieldDictionary<BattleCommandType,string>`
decoder. The raw header semantics still need more samples.

## Failure Root Cause

The previous parser consumed only:

```text
cmdMappingRawWords = [0, 1, 1, 0]
```

It then started the next `ModeData` at the following word. In the failing rows,
that word is actually a one-entry value-list count, followed by an aligned skill
id string.

Yvonne:

```text
modePayloadOffset = 2372

mode1 ult:
  normalAttackList count @2568 = 5
  cmdMapping header @2788..2800 = [0, 1, 1, 0]
  value-list count @2804 = 1
  value string @2808 = chr_0017_yvonne_ult_attack1_1
  next real modeId @2844 = ult_end

mode2 ult_end:
  cmdMapping header @2952..2964 = [0, 1, 1, 0]
  value-list count @2968 = 1
  value string @2972 = chr_0017_yvonne_ult_attack3_2
  next real modeId @3008 = talent_1

mode3 talent_1:
  cmdMapping header @3116..3128 = [0, 1, 1, 0]
  value-list count @3132 = 1
  value string @3136 = chr_0017_yvonne_attack5
```

Tangtang:

```text
modePayloadOffset = 2304

mode1 ult:
  normalAttackList count @2500 = 5
  cmdMapping header @2700..2712 = [0, 1, 1, 0]
  value-list count @2716 = 1
  value string @2720 = chr_0027_tangtang_ult_attack3
  next real modeId @2756 = ult_end

mode2 ult_end:
  cmdMapping header @2864..2876 = [0, 1, 1, 0]
  value-list count @2880 = 1
  value string @2884 = chr_0027_tangtang_ult_attack5
```

Laevat had the same hidden final-mode value segment. Because it occurred in the
last mode, the old parser did not crash, but it silently shifted
`SkillDataBundle` parsing. The new parser exposes:

```text
mode2 ult cmdMapping.values = [chr_0016_laevat_ult_attack1]
```

and no longer emits a misleading `skillDataBundle` for that row.

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

The warnings are existing project warnings from `AnimeStudio`, `AnimeStudio.Utility`,
and YAML converter TODO markers, not new errors from this change.

Focused extraction inputs:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk
```

Output root:

```text
tmp\ability_system_cmdmapping_after_20260629
```

Observed non-empty mappings:

```text
data_chr_0016_laevat:   mode ult      -> chr_0016_laevat_ult_attack1
data_chr_0017_yvonne:   mode ult      -> chr_0017_yvonne_ult_attack1_1
data_chr_0017_yvonne:   mode ult_end  -> chr_0017_yvonne_ult_attack3_2
data_chr_0017_yvonne:   mode talent_1 -> chr_0017_yvonne_attack5
data_chr_0027_tangtang: mode ult      -> chr_0027_tangtang_ult_attack3
data_chr_0027_tangtang: mode ult_end  -> chr_0027_tangtang_ult_attack5
```

## Remaining Unknowns

The four-word `cmdMapping` header is only partially understood. It may be a
specialized serialized dictionary header, but the exact meaning of the first,
third, and fourth words is not proven. The parser therefore preserves all four
words and only consumes the value list for the observed `[0, 1, 1, 0]` form.

The broader `AbilitySystemData` tail remains only partially decoded. Next useful
steps:

- parse `SkillDataBundle.defaultCmdMapping` with the same cautious header +
  bounded-value-list strategy if matching evidence appears
- decode `AbilitySystemData.uiData` scalar fields from IL2CPP metadata order
- build a reusable but evidence-backed `SerializeFieldDictionary` helper only
  after we have enough key/value samples across multiple field types
