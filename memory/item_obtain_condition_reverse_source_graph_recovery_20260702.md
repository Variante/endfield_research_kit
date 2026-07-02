# Item Obtain Condition Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph coverage for item obtain condition semantics.

New reverse edges:

- `item_obtain_condition_type -> item_obtain_condition` as `item_obtain_type_has_condition`
- `item_obtain_condition -> item_obtain_way` as `item_obtain_condition_shows_obtain_way`
- check target node -> `item_obtain_condition` as `item_obtain_check_used_by_condition`

Existing forward edges are preserved:

- `item_obtain_condition_has_type`
- `item_obtain_way_show_condition`
- typed check-reference edges such as `item_obtain_condition_refs_dungeon`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\item_acquisition_condition_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,009` nodes
- `3,146,261` edges
- `2,277,554` aliases

Parity checks:

- `item_obtain_condition_has_type`: `53`
- `item_obtain_type_has_condition`: `53`
- `item_obtain_way_show_condition`: `32`
- `item_obtain_condition_shows_obtain_way`: `32`
- typed forward check references: `53`
- `item_obtain_check_used_by_condition`: `53`

Reverse check target node kinds:

- `dungeon`: `27`
- `factory_tech`: `13`
- `wiki_entry`: `12`
- `item`: `1`

## Notes

The condition graph can now be traversed from acquisition condition types,
obtain-way visibility conditions, and concrete check targets back to the
conditions that use them. This helps answer questions such as which obtain ways
are gated by a dungeon or factory-tech requirement without scanning inbound
edges manually.
