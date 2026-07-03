# FindTarget Selector Payload Source Graph Recovery - 2026-07-03

## Context

`reports/mission_order/findtarget_selector_payload_priority_audit.json`
classifies FindTarget selector tag hints by selector family, union tag, payload
complexity, MemoryPack wrapper type, and setter fields. This is useful
evidence for the unresolved `TargetSettings` / `SelectorData` semantic gap:
it identifies which selector payload variants are safest to probe first and
which variants contain nested target settings, blackboard values, primitive
fields, or unresolved collections.

The audit is priority evidence only. It does not prove full `TargetSettings`
byte boundaries or make FindTargetAction chain consumption safe.

## Change

`tools/endfield_source_graph.py` now ingests the priority audit after decoded
config semantics.

New node kinds:

- `findtarget_selector_candidate`
- `selector_family`
- `selector_tag`
- `selector_payload_classification`
- `selector_payload_setter`

New edges:

- `has_findtarget_selector_candidate`
- `findtarget_selector_candidate_family`
- `findtarget_selector_candidate_tag`
- `findtarget_selector_candidate_payload_class`
- `findtarget_selector_simplest_probe_candidate`
- `findtarget_selector_zero_tag_candidate`
- `findtarget_selector_candidate_payload_setter`

The ingest materializes the union of regular nonzero candidates and the
separate `zeroTagCandidates` list, because zero-tag rows are not duplicated in
the audit's main `candidates` collection.

## Validation

Static checks passed:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

A focused temporary database called only
`ingest_findtarget_selector_payload_audit()` against the real audit JSON.
Results:

| Item | Count |
|---|---:|
| `findtarget_selector_candidate` nodes | 27 |
| `selector_family` nodes | 3 |
| `selector_tag` nodes | 27 |
| `selector_payload_classification` nodes | 6 |
| `selector_payload_setter` nodes | 31 |
| `has_findtarget_selector_candidate` edges | 27 |
| `findtarget_selector_candidate_family` edges | 27 |
| `findtarget_selector_candidate_tag` edges | 27 |
| `findtarget_selector_candidate_payload_class` edges | 27 |
| `findtarget_selector_simplest_probe_candidate` edges | 8 |
| `findtarget_selector_zero_tag_candidate` edges | 3 |
| `findtarget_selector_candidate_payload_setter` edges | 31 |

Payload class distribution:

| Classification | Candidate count |
|---|---:|
| `empty-instance-only` | 11 |
| `primitive-or-enum` | 7 |
| `nested-target-settings` | 3 |
| `blackboard-value` | 2 |
| `string-or-primitive` | 2 |
| `unresolved-or-collection` | 2 |

The three zero-tag candidates are:

- `finder:0x0000:Core_Selector_AbilityEntityTargetFinder_Data`
  (`empty-instance-only`)
- `validator:0x0000:Core_Selector_AttributeValidator_Data`
  (`primitive-or-enum`)
- `postProcessor:0x0000:Core_Selector_ConvertToBoxCenterPlaneProjectionPoint_Data`
  (`unresolved-or-collection`)

All eight simplest probe candidates are classified as `empty-instance-only`.

## Notes

Use these graph nodes to choose safe future bounded-reader experiments. They
should not be treated as decoded selector payloads; the report itself says the
current replay has zero exact TargetSettings body-middle end hits and zero
chain-safe FindTarget consumptions.

## Replay Audit Follow-Up

`tools/endfield_source_graph.py` also ingests
`reports/mission_order/findtarget_selector_replay_audit.json` after the
priority audit. This companion report records the seven observed
FindTargetAction body-middle byte shapes and the exact replay result that keeps
chain consumption disabled.

Additional node kinds:

- `findtarget_selector_replay_shape`
- `findtarget_replay_failure_reason`

Additional edges:

- `has_findtarget_selector_replay_shape`
- `findtarget_replay_shape_example_file`
- `findtarget_replay_shape_failure_reason`
- `findtarget_replay_shape_selector_tag_hit`
- `findtarget_replay_shape_nonzero_selector_tag_hit`

Focused validation called both FindTarget audit ingests in one temporary
database so shared `selector_tag` nodes were exercised:

| Item | Count |
|---|---:|
| `findtarget_selector_candidate` nodes | 27 |
| `findtarget_selector_replay_shape` nodes | 7 |
| `findtarget_replay_failure_reason` nodes | 4 |
| `selector_tag` nodes | 31 |
| `findtarget_replay_shape_example_file` edges | 7 |
| `findtarget_replay_shape_failure_reason` edges | 15 |
| `findtarget_replay_shape_selector_tag_hit` edges | 101 |
| `findtarget_replay_shape_nonzero_selector_tag_hit` edges | 83 |
| shapes with accepted TargetSettings candidates | 0 |
| shapes with chain-safe FindTarget consumption | 0 |

The validation preserved the negative result: selector tag hits are queryable
evidence, but none of the seven body-middle shapes proves a full
TargetSettings boundary or chain-safe FindTarget decode.

## Boundary Audit Follow-Up

`tools/endfield_source_graph.py` also ingests
`reports/mission_order/findtarget_selector_boundary_audit.json`. This report
is the source of the seven body-middle shapes and records both concrete decoded
FindTarget item samples and first-FindTarget records that remain unsafe to
split.

Additional node kinds:

- `findtarget_selector_boundary_shape`
- `findtarget_selector_boundary_sample`
- `findtarget_ambiguous_record`
- `findtarget_split_status`
- `target_group_key`

Additional edges:

- `has_findtarget_selector_boundary_shape`
- `findtarget_boundary_shape_matches_replay_shape`
- `findtarget_boundary_shape_target_group`
- `has_findtarget_selector_boundary_sample`
- `findtarget_boundary_sample_file`
- `findtarget_boundary_sample_shape`
- `findtarget_boundary_sample_target_group`
- `has_findtarget_ambiguous_record`
- `findtarget_ambiguous_record_file`
- `findtarget_ambiguous_record_split_status`

Focused validation called the priority, replay, and boundary ingests together:

| Item | Count |
|---|---:|
| `findtarget_selector_boundary_shape` nodes | 7 |
| `findtarget_selector_boundary_sample` nodes | 24 |
| `findtarget_ambiguous_record` nodes | 30 |
| `findtarget_split_status` nodes | 1 |
| `target_group_key` nodes | 5 |
| `findtarget_boundary_shape_matches_replay_shape` edges | 7 |
| `findtarget_boundary_shape_target_group` edges | 6 |
| `findtarget_boundary_sample_file` edges | 24 |
| `findtarget_boundary_sample_shape` edges | 24 |
| `findtarget_boundary_sample_target_group` edges | 20 |
| `findtarget_ambiguous_record_file` edges | 30 |
| `findtarget_ambiguous_record_split_status` edges | 30 |
| shape TargetSettings candidates | 0 |
| sample TargetSettings candidates | 0 |

All 30 ambiguous records point to
`findtarget_split_status:ambiguous-union-tag-boundaries`. This preserves the
current decoder gate: header-only union scanning is still not enough to split
these action chains.
