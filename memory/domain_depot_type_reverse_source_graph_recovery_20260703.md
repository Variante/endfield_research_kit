# Domain Depot Type Reverse Source-Graph Recovery - 2026-07-03

## Scope

Domain depot upgrade levels, pack-value rows, and integrity-reduce rows already
linked outward to domain depot deliver item/pack type nodes. This pass adds the
reverse edges so queries starting from a deliver type can discover the upgrade
levels, pack-value ranges, and integrity rules that use it.

## Added Reverse Edges

- `domain_depot_item_type_unlocked_by_level`
- `domain_depot_pack_type_unlocked_by_level`
- `domain_depot_item_type_used_by_pack_value`
- `domain_depot_pack_type_used_by_pack_value`
- `domain_depot_item_type_affected_by_integrity_reduce`

## Validation

Focused temp graph:
`tmp/domain_depot_reverse_validate.sqlite`

The validation seeded `ingest_domain_depot_semantics()` only.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `domain_depot_level_unlocks_item_type` | 39 | `domain_depot_item_type_unlocked_by_level` | 39 |
| `domain_depot_level_unlocks_pack_type` | 35 | `domain_depot_pack_type_unlocked_by_level` | 35 |
| `domain_depot_pack_value_item_type` | 45 | `domain_depot_item_type_used_by_pack_value` | 45 |
| `domain_depot_pack_value_pack_type` | 45 | `domain_depot_pack_type_used_by_pack_value` | 45 |
| `domain_depot_integrity_reduce_affects_item_type` | 6 | `domain_depot_item_type_affected_by_integrity_reduce` | 6 |

`python -m py_compile tools\endfield_source_graph.py` passed.
