# Advanced Buff Stack Recovery - 2026-06-29

## Scope

Focused on `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data` managed-reference
payloads that remained `$unparsed` in the targeted `data_chr_*` MonoBehaviour
slice.

Validation output:

```text
tmp/advanced_buff_decode_after_20260629
```

Validated chunks:

```text
68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
71FC2E71A9F249B382BF8DAED3BCEE65.chk
FBAD673F662CF3EACDDB14A65999F7EF.chk
```

## Evidence

Payload evidence found 7 real `CheckBuffStackNumAdvanced/Data` records in the
focused slice. They form 4 semantic variants:

- Antal pair: `checkType=Id`, one buff id, `compare=GE`, value `1.0`.
- Ardelia: `checkType=Tag`, empty buff-id list, tags `NoGuard` and
  `SpellInflict`, `compare=Equals`, value `0.0`.
- Wulfa pair: `checkType=Id`, two buff ids, `compare=LT`, value `1.0`.
- Zhuangfy pair: `checkType=Tag`, one buff id plus `PulseInflict` tag,
  `compare=GE`, value `1.0`.

Local IL2CPP metadata from installed `global-metadata.dat` confirms
`Beyond.Gameplay.Core.CheckBuffStackNumAdvanced+Data` has exactly these fields
after inherited `AbilityActionData`:

1. `checkTarget`
2. `buffSettings`
3. `buffStackNumType`
4. `compareType`
5. `value`
6. `limitSkillCastId`

Supporting metadata:

- `BuffFindSettings`: `checkType`, `buffIdList`, `tagQuery`.
- `BuffFindSettings+CheckType`: `Id`, `Tag`, `Environment`, `Context`.
- `BuffStackNumType`: `BuffCount`, `BuffIdCount`.
- `Beyond.CompareType`: `LT`, `LE`, `GT`, `GE`, `Equals`.

## Implementation

AnimeStudio now promotes matching `CheckBuffStackNumAdvanced/Data` payloads from
raw `$unparsed` heuristic output to `$decoded` + `$partial` structured records.
It consumes the full payload and emits:

- inherited `AbilityActionData` prefix;
- partial `TargetSettings` diagnostics;
- partial `BuffFindSettings` diagnostics;
- `buffStackNumType`;
- `compareType`;
- `BlackboardDouble value`;
- `limitSkillCastId`.

This remains partial by design. The unresolved parts are still visible:

- `TargetSettings.selectorData` RID semantics and suffix words;
- exact generic type name behind `BuffFindSettings.buffIdList`;
- unobserved `BuffFindSettings` `Environment` and `Context` variants.

## Validation

Targeted CLI export after the patch:

```text
json files: 31
parse errors: 0
CheckBuffStackNumAdvanced/Data real records: 7
CheckBuffStackNumAdvanced/Data decoded partial records: 7
CheckBuffStackNumAdvanced/Data unparsed records: 0
remaining wrapped unparsed records:
  Beyond.Gameplay.Core.AbilitySystemData: 2
```

The only remaining unparsed type in the focused three-chunk slice is now
`AbilitySystemData`, which is broader and should be handled separately.