# FindTarget Selector Replay Recovery - 2026-07-02

## Context

Follow-up to `reports/mission_order/findtarget_selector_boundary_audit.json`.
The boundary audit had already found 24 decoded `FindTargetAction` items, 7
unique `bodyMiddleOpaque` byte shapes, 30 ambiguous first-FindTarget records,
and zero accepted TargetSettings candidates inside the decoded body-middle
region.

## Work Done

Added `scripts/story_recovery/build_findtarget_selector_replay_audit.py`.
The probe replays the saved body-middle hex from the boundary audit against:

- the current `read_buff_target_settings_envelope_partial` helper in
  `scripts/build_data_index.py`
- selector Finder/Validator/PostProcessor tag maps from
  `reports/mission_order/selector_formatter_tag_audit.json`

The probe is report-only. It does not promote FindTarget chain consumption.

## Results

Generated:

- `reports/mission_order/findtarget_selector_replay_audit.json`
- `reports/mission_order/findtarget_selector_replay_audit.md`

Summary from the replay:

- unique body-middle shapes: 7
- source decoded FindTarget items: 24
- source ambiguous first-FindTarget records: 30
- TargetSettings accepted candidates: 0
- TargetSettings exact body-middle end hits: 0
- member-count=3 anchors: 62
- selector union-tag hits: 877
- selector nonzero union-tag hits: 121
- plausible selector order anchors: 62
- nonzero plausible selector order anchors: 19
- zero-only plausible selector order anchors: 43
- exact boundary proofs: 0
- chain-safe FindTarget consumptions: 0
- ambiguous records explained: 0

The TargetSettings envelope path remains rejected for these bytes. The useful
signal is the smaller set of 19 nonzero selector-order anchors, especially the
repeating first anchors on the `tar`, `thunderTarDmg`, `ballPos`, `abe`, and
`main` shapes. The all-zero anchors are expected to be noisy because tag `0` is
valid in all three selector families.

## Interpretation

FindTarget chain consumption should remain disabled. The current evidence can
rank likely selector-reader states, but it still does not consume selector
formatter payloads to a known boundary such as `selectorOwner` or item end.

## Next Step

Use the 19 nonzero selector-order anchors as the next narrow target:

1. Inspect IL2CPP bodies for the concrete selector formatter payload types hit
   by those anchors, starting with tags `0x0003`, `0x0001`, `0x0008`, and
   `0x0006`.
2. Add one payload-length probe for the simplest formatter body that appears in
   multiple shapes.
3. Re-run this replay and only consider promoting parser logic when at least
   one anchor consumes to an independently known end offset.
