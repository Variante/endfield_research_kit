# Item Type Reverse Source-Graph Recovery - 2026-07-03

## Scope

`ItemTable.type` already produced `item_has_type` edges from items to item type
nodes. This pass adds the reverse edge so queries starting from an item type can
discover all items assigned to that category.

## Added Reverse Edge

- `item_type_has_item`

## Validation

Focused temp graph:
`tmp/item_type_reverse_validate.sqlite`

The validation seeded `ingest_item_economy()` only.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `item_has_type` | 2,376 | `item_type_has_item` | 2,376 |

`ItemTypeTable` defines 93 item type rows; current `ItemTable` rows use 88
distinct type values. The largest current buckets are item types `8`, `47`,
`6`, `19`, and `100`.

`python -m py_compile tools\endfield_source_graph.py` passed.
