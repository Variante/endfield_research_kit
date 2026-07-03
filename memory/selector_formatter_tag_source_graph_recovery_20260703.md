# Selector Formatter Tag Source Graph Recovery - 2026-07-03

## Context

The FindTarget selector payload/replay/boundary graph ingests expose observed
selector tag hints in BuffData FindTargetAction bodies. The canonical tag map,
however, comes from `reports/mission_order/selector_formatter_tag_audit.json`:
Finder, Validator, and PostProcessor cctors register formatter tables with
explicit ActionBase-style `r8` tag constants.

This audit is higher-confidence than raw tag-byte hits. It should be queryable
as the source of truth for selector family/tag-to-formatter mappings, while the
FindTarget replay evidence remains only local byte evidence.

## Change

`tools/endfield_source_graph.py` now ingests the selector formatter tag audit
before the FindTarget selector payload/replay/boundary audits.

New node kinds:

- `selector_formatter_table`
- `selector_formatter`
- `selector_formatter_slot`

Existing shared node kinds:

- `selector_family`
- `selector_tag`

New edges:

- `has_selector_formatter_table`
- `selector_formatter_table_family`
- `selector_formatter_table_has_tag`
- `selector_tag_resolves_formatter`
- `selector_formatter_registered_tag`
- `selector_formatter_table_has_formatter`
- `selector_formatter_metadata_slot`
- `selector_formatter_slot_loads_formatter`
- `selector_formatter_table_has_slot`
- `selector_formatter_slot_inventory_formatter`

The graph preserves cctor/deserializer metadata, registration evidence, metadata
slot addresses, and slot inventory rows. Deserialize `cmp eax` rows remain
diagnostic payload data; the explicit cctor registration rows are the promoted
tag evidence.

## Validation

Static checks passed:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

A focused temporary database called only
`ingest_selector_formatter_tag_audit()` against the real audit JSON. Results:

| Item | Count |
|---|---:|
| `selector_formatter_table` nodes | 3 |
| `selector_tag` nodes | 40 |
| `selector_formatter` nodes | 40 |
| `selector_formatter_slot` nodes | 40 |
| `selector_family` nodes | 3 |
| `has_selector_formatter_table` edges | 3 |
| `selector_formatter_table_has_tag` edges | 40 |
| `selector_tag_resolves_formatter` edges | 40 |
| `selector_formatter_registered_tag` edges | 40 |
| `selector_formatter_table_has_formatter` edges | 40 |
| `selector_formatter_metadata_slot` edges | 40 |
| `selector_formatter_slot_loads_formatter` edges | 40 |
| `selector_formatter_table_has_slot` edges | 40 |
| `selector_formatter_slot_inventory_formatter` edges | 40 |

Per-family tag counts:

- Finder: 20
- Validator: 11
- PostProcessor: 9

The validation found zero duplicate `selector_formatter_table_has_tag` edges.

## Notes

Use this graph evidence to resolve canonical selector tags. Do not use it alone
to claim FindTargetAction chain-safe consumption; the boundary and replay
audits still report zero exact TargetSettings body-middle end hits.
