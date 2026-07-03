# Selector TargetSettings Chain Source Graph Recovery - 2026-07-03

## Context

`reports/mission_order/selector_targetsettings_chain_summary.json` maps focused
SelectorData, TargetSettings, and FindTargetAction MemoryPack bodies back to
GameAssembly direct calls and setter store offsets. This is body-wiring
evidence: it proves deserializer-to-setter call order and setter field store
offsets, but it does not prove safe byte boundaries for nested SelectorData or
TargetSettings payloads.

This evidence complements the selector formatter tag graph and the FindTarget
payload/replay/boundary graph ingests. The latter still report zero exact
TargetSettings body-middle end hits and zero chain-safe FindTarget
consumptions.

## Change

`tools/endfield_source_graph.py` now ingests the selector TargetSettings chain
summary after the canonical selector formatter tag audit.

New node kinds:

- `selector_chain_method`
- `selector_chain_setter_call`
- `selector_chain_store_offset`
- `selector_chain_field`
- `selector_chain_alias_warning`
- `selector_chain_direct_call`

New edges:

- `has_selector_chain_selected_target`
- `has_selector_chain_setter_sequence`
- `selector_chain_deserializer_has_setter_call`
- `selector_chain_setter_call_candidate`
- `selector_chain_deserializer_calls_setter`
- `has_selector_chain_store_offset`
- `selector_chain_setter_has_store_offset`
- `selector_chain_setter_stores_field`
- `selector_chain_field_stored_by_setter`
- `has_selector_chain_alias_warning`
- `selector_chain_method_has_alias_warning`
- `selector_chain_alias_warning_candidate`
- `has_selector_chain_direct_call`
- `selector_chain_method_has_direct_call`
- `selector_chain_direct_call_callee`

Ambiguous multi-candidate setter calls are not promoted as resolved
`selector_chain_deserializer_calls_setter` edges. They remain represented as
`selector_chain_setter_call_candidate` rows plus separate
`selector_chain_alias_warning` nodes.

## Validation

Static checks passed:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

A focused temporary database called only
`ingest_selector_targetsettings_chain_summary()` against the real chain summary
JSON. Results:

| Item | Count |
|---|---:|
| `selector_chain_method` nodes | 131 |
| `selector_chain_setter_call` nodes | 53 |
| `selector_chain_store_offset` nodes | 32 |
| `selector_chain_field` nodes | 32 |
| `selector_chain_alias_warning` nodes | 4 |
| `selector_chain_direct_call` nodes | 140 |
| `has_selector_chain_selected_target` edges | 5 |
| `has_selector_chain_setter_sequence` edges | 5 |
| `selector_chain_deserializer_has_setter_call` edges | 53 |
| `selector_chain_setter_call_candidate` edges | 57 |
| `selector_chain_deserializer_calls_setter` edges | 49 |
| `has_selector_chain_store_offset` edges | 32 |
| `selector_chain_setter_has_store_offset` edges | 32 |
| `selector_chain_setter_stores_field` edges | 32 |
| `selector_chain_field_stored_by_setter` edges | 32 |
| `has_selector_chain_alias_warning` edges | 4 |
| `selector_chain_alias_warning_candidate` edges | 8 |
| `has_selector_chain_direct_call` edges | 140 |
| `selector_chain_direct_call_callee` edges | 171 |

The 53 setter-call records include 4 ambiguous two-candidate calls. This
explains the 57 candidate edges and 49 resolved deserializer-to-setter edges.

## Notes

Use this graph evidence to answer body-wiring questions such as which
deserializer calls which setter and which setter writes which field offset. Do
not use it alone to enable FindTargetAction chain consumption or to mark
TargetSettings/SelectorData payloads fully decoded; byte-boundary proof must
come from sample replay or decoder validation.
