# MonoBehaviour Core Action/Condition Parent Status - 2026-06-30

This pass followed the `AbilitySystemData` parent-status cleanup pattern for a
small set of action/condition wrapper payloads whose own bytes are fully
consumed, while their nested `TargetSettings` / `SelectorData` objects remain
partial.

## Scope

Focused source:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
```

Validation output:

```text
tmp\core_action_condition_parent_status_after_20260630
```

The promotion applies only to these five parent wrappers:

- `Beyond.Gameplay.Core.Conditions.CheckObjectTypeMatch/Data`
- `Beyond.Gameplay.Core.Conditions.CheckMainCharacterCondition/Data`
- `Beyond.Gameplay.Core.Conditions.CheckTargetsEqual/Data`
- `Beyond.Gameplay.Core.Conditions.CheckBuffStackNum/Data`
- `Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag/Data`

It does not promote nested `TargetSettings`, nested `SelectorData`,
`CreateBuffAction/Data`, or `CheckBuffStackNumAdvanced/Data`.

## Exporter Change

`AnimeStudio.CLI/Exporter.cs` no longer sets parent `$partial` on the five
wrappers above when `reader.EnsureComplete()` succeeds. Each promoted parent now
gets `observedPayloadStatus` explaining that all parent bytes are consumed and
that nested objects carry their own partial markers.

This is a classification fix, not a warning suppression. The nested partial
objects are still emitted in place.

## Validation

Command:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\core_action_condition_parent_status_after_20260630 --game ArknightsEndfield --logger_flags Warning Error --group_assets BySource --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll
```

Result:

- CLI exit code: 0.
- Console warning/error output: none.
- JSON files parsed: 129,407.
- JSON parse errors: 0.

Structure-aware managed-reference counts:

| Class | Count | Decoded | Parent `$partial` | `observedPayloadStatus` |
| --- | ---: | ---: | ---: | ---: |
| `CheckObjectTypeMatch/Data` | 18 | 18 | 0 | 18 |
| `CheckMainCharacterCondition/Data` | 6 | 6 | 0 | 6 |
| `CheckTargetsEqual/Data` | 4 | 4 | 0 | 4 |
| `CheckBuffStackNum/Data` | 3 | 3 | 0 | 3 |
| `CheckBuffStackNumByTag/Data` | 4 | 4 | 0 | 4 |
| `CreateBuffAction/Data` | 5 | 5 | 5 | 0 |
| `CheckBuffStackNumAdvanced/Data` | 3 | 3 | 3 | 0 |

Nested partials under the five promoted parent wrappers remain present:

| Nested layout | Count |
| --- | ---: |
| `Beyond.Gameplay.Core.TargetSettings` | 39 |
| `Beyond.Gameplay.Core.Selector/SelectorData` | 39 |

Across the broader focused `TargetSettings` probe, `TargetSettings` and
`SelectorData` remain partial in all 54 observed samples. The independent
TargetSettings probe found:

- `postProcessorDataCandidates.lateRidA = -2` and `lateRidB = -2` in all 54.
- Post-selector raw tails are 53x `(0,0,0,1,0,0,0,0)` and 1x
  `(0,0,0,1,0,0,1,0)`.
- No non-empty post-processor RID, non-empty `targetContextKey`, or non-default
  direction/context variant was observed.

## Current Classification

The five promoted wrapper parents are byte-consumed and no longer need a parent
partial marker. Remaining warnings are nested semantic uncertainty in
`TargetSettings` and `SelectorData`, plus local unresolved fields in
`CreateBuffAction/Data` and `CheckBuffStackNumAdvanced/Data`.

Next safe work is not another parent cleanup; it needs stronger byte evidence
for either non-empty `SelectorData.postProcessorData`, non-default
`TargetSettings` post-selector tails, `CreateBuffAction` post-context field
boundaries, or `CheckBuffStackNumAdvanced` `BuffFindSettings` variants.

## Additional Wrapper Parent Status Pass

This follow-up extended the parent-status classification to four more small wrappers whose own serialized bytes are consumed, while keeping `CreateBuffAction/Data` and `CheckBuffStackNumAdvanced/Data` parent-partial with explicit reasons.

Implemented in `AnimeStudio.CLI/Exporter.cs`:

- Removed parent `$partial` from byte-consumed wrappers:
  - `CheckHp/Data`
  - `CheckTagMatch/Data`
  - `ModifyDynamicBlackboard/Data`
  - `StoreBuffCount/Data`
- Added `observedPayloadStatus` to those four wrappers.
- Kept `CreateBuffAction/Data` parent `$partial`, but added parent `observedPayloadStatus` and `partialReasons` naming unresolved `buffs`, `postContextTail`, and nested `TargetSettings` issues.
- Kept `CheckBuffStackNumAdvanced/Data` parent `$partial`, but added parent `observedPayloadStatus` and `partialReasons` naming unresolved `BuffFindSettings`, unobserved `Environment` / `Context` variants, and nested `TargetSettings` issues.

Validation output:

```text
tmp\core_wrapper_parent_reason_validation_after_20260630
```

Validation commands covered the focused `68B3` `data_chr_` rows plus the broader `FBAD` `data_chr_0028_wulfa` / `data_chr_0030_zhuangfy` advanced buff-stack rows.

| Metric | Result |
| --- | ---: |
| JSON files parsed | 27 |
| JSON parse errors | 0 |
| Data-level `$unparsed` / `$heuristic` / `decodeError` flags | 0 |

| Class | Count | Decoded | Parent `$partial` | `observedPayloadStatus` | Parent `partialReasons` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `CheckHp/Data` | 2 | 2 | 0 | 2 | 0 |
| `CheckTagMatch/Data` | 2 | 2 | 0 | 2 | 0 |
| `ModifyDynamicBlackboard/Data` | 2 | 2 | 0 | 2 | 0 |
| `StoreBuffCount/Data` | 1 | 1 | 0 | 1 | 0 |
| `CreateBuffAction/Data` | 5 | 5 | 5 | 5 | 5 |
| `CheckBuffStackNumAdvanced/Data` | 7 | 7 | 7 | 7 | 7 |

Nested `TargetSettings` / `SelectorData` partial markers are still present under these wrappers; this pass only corrects parent-level classification.

Current classification: all audited small condition/action wrapper parent byte streams are now either marked byte-consumed or carry explicit parent partial reasons. Remaining real work is nested `TargetSettings` / `SelectorData`, `CreateBuffAction` non-default post-context/list variants, and `CheckBuffStackNumAdvanced` `BuffFindSettings` variants.