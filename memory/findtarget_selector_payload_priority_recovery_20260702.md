# FindTarget Selector Payload Priority Recovery - 2026-07-02

## Context

The FindTargetAction chain is still blocked by opaque `bodyMiddle` selector
bytes. The replay audit now joins the saved boundary shapes with selector tag
maps and the selector/TargetSettings MemoryPack metadata catalog, then probes
only selector wrappers whose payload has no setters beyond `instance`.

## Artifacts

- `scripts/story_recovery/build_findtarget_selector_replay_audit.py`
- `scripts/story_recovery/build_findtarget_selector_payload_priority_audit.py`
- `reports/mission_order/findtarget_selector_replay_audit.json` / `.md`
- `reports/mission_order/findtarget_selector_payload_priority_audit.json` / `.md`

## Findings

- Replay remains conservative: exact boundary proofs `0`, chain-safe
  FindTarget consumptions `0`, ambiguous records explained `0`.
- Empty selector payload tags from metadata: `15`.
- Empty-payload prefix attempts: `124`; local prefix successes: `5`; full
  selector order successes: `0`; max consumed selector fields: `1`.
- The smallest `main` body shape confirms both first-family interpretations at
  anchor `0x1e`: `postProcessor` tag `0x0001`
  `Core_Selector_ConvertToPosition_Data` and `finder` tag `0x0001`
  `Core_Selector_CharacterTeamFinder_Data` each consume the union tag plus a
  zero payload member-count byte to `0x21`, then stop at a zero validator tag.
- Other one-field local hits include empty finder payloads such as
  `Core_Selector_MainTargetFinder_Data` and
  `Core_Selector_InFightEnemyFinder_Data`; these are useful byte-shape anchors
  but still not full SelectorData boundaries.
- Payload priority ranking found `24` nonzero selector candidates, `10`
  empty-payload candidates, and `3` nested TargetSettings candidates. Empty
  payloads remain the safest next reader target.
- `0x0000` is not a null selector sentinel. The selector formatter tag audit
  registers real zero-tag types for all three families. The payload-priority
  audit now classifies those rows: Finder `0x0000`
  `Core_Selector_AbilityEntityTargetFinder_Data` is empty-instance-only,
  Validator `0x0000` `Core_Selector_AttributeValidator_Data` has primitive
  attribute/min/max fields, and PostProcessor `0x0000`
  `Core_Selector_ConvertToBoxCenterPlaneProjectionPoint_Data` has an
  unresolved `boxShape` payload.

## Interpretation

The new probe proves that some real FindTargetAction middle bytes contain a
nonzero selector union tag followed by the expected zero-member payload for
fieldless MemoryPack wrapper types. That is a local byte proof only. Chain
consumption must stay disabled until a reader can consume a full SelectorData
record to a known boundary such as `selectorOwner` or the item end.

## Next Steps

1. Do not treat selector tag `0x0000` as null. Add report-only readers for
   actual zero-tag payloads in order of complexity: Finder `0x0000` first
   because it is empty, then Validator `0x0000`, then PostProcessor `0x0000`
   after the shape payload is understood.
2. Decode the highest-volume simple non-empty payloads after the zero-tag path
   is bounded, starting with primitive/string candidates before nested
   TargetSettings.
3. Keep FindTargetAction chain consumption disabled until a full SelectorData
   reader reaches a known boundary such as `selectorOwner` or item end.
