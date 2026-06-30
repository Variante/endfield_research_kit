# MonoBehaviour TargetSettings status - 2026-06-30

## Overall MonoBehaviour inventory

Current exported MonoBehaviour JSON under
`export_full/recovered/AnimeStudio-cli/{Persistent,StreamingAssets}/json_by_type/MonoBehaviour`
contains:

- Total JSON files: 1,064,294.
- Files with incomplete markers: 3,644.
- JSON parse errors: 0.
- Top-level metadata-only/raw-data-only fallbacks: 0.
- Files with `serializedTypeTreeError`: 3,644.
- Files with `partialTypeTreeDecode`: 1,707.
- Files with heuristic managed-reference recovery: 1,937.

By source:

- `Persistent`: 1,486 incomplete files, all `partialTypeTreeDecode` with `serializedTypeTreeError`.
- `StreamingAssets`: 2,158 incomplete files, including 1,937 heuristic managed-reference recoveries and 221 partial TypeTree decodes.

The next broad families are repeated `Gameplay.Beyond` managed-reference payloads. The largest current clusters are guide condition/action refs, camera/tutorial action refs, projectile component refs, and display/config refs with useful string hints.

## TargetSettings progress

The current `Beyond.Gameplay.Core.TargetSettings` diagnostic reader already consumed the same stable byte layouts in focused samples:

- 70 `TargetSettings` objects.
- Length distribution: 48 objects at 108 bytes, 22 objects at 100 bytes.

IL2CPP metadata names the field order as:

`targetSource`, `targetGroupKey`, `selectorOwner`, `ownerContextKey`, `centerType`,
`centerContextKey`, `centerToGround`, `selectorData`, `enableAdvancedDirection`,
`advancedDirection`, `selectorDirection`, `target`, `targetContextKey`, `Default`.

`Selector/SelectorData` metadata names:

`finderData`, `validatorData`, `postProcessorData`.

The exporter now emits those names only where the byte evidence supports them:

- `finderDataRid` is used when the link is a null managed-reference sentinel or points to a `Finder/Data` class.
- `validatorDataRid` is used only when the optional selector slot is present and points to a `Validator/Data` class.
- `postProcessorDataCandidates` preserves the two late RID slots under a partial metadata-aware diagnostic instead of naming either one as final.
- `postSelectorFields.rawWords` replaces the older generic `suffixWords`, with the IL2CPP field order recorded but the raw eight-word tail still preserved.

`TargetSettings` remains `$partial`; this change improves naming and auditability without claiming the post-selector tail is fully decoded.

## Validation

Commands/results:

- `.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded.
- Focused direct CLI validation re-exported the three existing advanced-buff sample source groups from `tmp/advanced_buff_decode_after_20260629` into `tmp/targetsettings_selector_after_20260630`.
- Output count: 28 MonoBehaviour JSON files, matching the map entries in those three source groups.
- CLI emitted no warnings or errors in the focused validation run.

Focused JSON analysis after the change:

- `targetSettings`: 70.
- `targetSettingsPartial`: 70.
- `selectorData`: 70.
- `selectorDataPartial`: 70.
- `finderDataRid`: 70.
- `validatorDataRid`: 2.
- `postProcessorDataCandidates`: 70.
- `postSelectorFields`: 70.
- Legacy `suffixWords`: 0.
- TargetSettings length distribution remained `{100: 22, 108: 48}`.

## Remaining unknowns

- Exact byte widths and enum meanings for the post-selector TargetSettings fields:
  `enableAdvancedDirection`, `advancedDirection`, `selectorDirection`, `target`,
  `targetContextKey`, and `Default`.
- Exact serialization shape for `postProcessorData`.
- Whether broader, non-focused samples introduce non-null finder/post-processor variants beyond the current focused set.

These should stay partial until a positive sample proves the missing boundaries.
