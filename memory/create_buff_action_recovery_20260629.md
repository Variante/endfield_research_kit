# CreateBuffAction Recovery - 2026-06-29

## Scope

Focused on `Beyond.Gameplay.Core.CreateBuffAction/Data` warnings in the targeted
`data_chr_*` MonoBehaviour slice exported from installed VFS chunks.

Validation output:

```text
tmp/create_buff_action_decode_after_20260629
```

Validated chunks:

```text
68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
71FC2E71A9F249B382BF8DAED3BCEE65.chk
FBAD673F662CF3EACDDB14A65999F7EF.chk
```

## Evidence

Two read-only subagents checked the same issue from different sides:

- payload layout: 5 real `CreateBuffAction/Data` payloads in the focused slice;
  all are from the `68B3...chk` source and all have the same nine-word
  post-context tail.
- metadata layout: installed `global-metadata.dat` confirms the exact
  `CreateBuffAction+Data` field order; DummyDll/Cpp2IL-generated DLLs do not
  expose these classes cleanly as normal Cecil types.

Metadata-proven field order after inherited `AbilityActionData`:

1. `buffs`
2. `count`
3. `targetSettings`
4. `buffSource`
5. `contextKey`
6. `autoFinishByAction`
7. `inheritSkillIdList`
8. `asChildBuff`
9. `inheritSourceSkillCastId`
10. `inheritSourceSkillCastInfo`
11. `isExtra`
12. `overrideBuffIconDuration`
13. `buffIconDurationSource`

## Implementation

AnimeStudio now promotes `CreateBuffAction/Data` from raw `$unparsed` heuristic
output to a `$decoded` + `$partial` structured record when the bounded payload
shape matches. It consumes the complete payload and emits:

- inherited `AbilityActionData` prefix;
- `buffs` as count-prefixed aligned buff-id strings plus four reserved zero
  words;
- `count` as `BlackboardDouble`;
- partial `TargetSettings` diagnostics;
- `buffSource` as a 32-bit enum/hash word;
- `contextKey` as an aligned string;
- `postContextTail` with the metadata field order and the raw tail words.

This is intentionally still partial. The unresolved parts are not hidden:

- exact generic/list type behind `buffs` and `inheritSkillIdList`;
- byte boundaries inside the post-context tail;
- `BuffIconDurationSourceSetting` wire shape;
- existing `TargetSettings` selector/suffix semantics.

## Validation

Targeted CLI export after the patch:

```text
json files: 31
parse errors: 0
CreateBuffAction/Data decoded partial records: 5 real payloads
CreateBuffAction/Data unparsed records: 0
remaining wrapped unparsed records:
  Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data: 7
  Beyond.Gameplay.Core.AbilitySystemData: 2
```

The five real `CreateBuffAction/Data` records all carry the same post-context
tail words:

```text
0x00000000 0x00000000 0x00000000 0x00000000
0x00000001 0x00000000 0x00000000 0x00000000
0x00000000
```

## Next Work

Next focused targets remain:

- `CheckBuffStackNumAdvanced/Data`: 7 records, now structurally traced but still
  not semantically promoted.
- `AbilitySystemData`: 2 records, broad payload and higher risk than the small
  action/condition data shapes.