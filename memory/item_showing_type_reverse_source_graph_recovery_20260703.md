# Item Showing-Type Reverse Source-Graph Recovery - 2026-07-03

## Scope

`ItemTable.showingType` already produced `item_has_showing_type` edges from
items to item showing-type nodes. This pass adds the reverse edge so queries
starting from an item display category can discover all items assigned to it.

## Added Reverse Edge

- `item_showing_type_has_item`

## Validation

Focused temp graph:
`tmp/item_showing_type_reverse_validate.sqlite`

The validation seeded `ingest_item_economy()` only.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `item_has_showing_type` | 2,376 | `item_showing_type_has_item` | 2,376 |

`ItemShowingTypeTable` defines 10 explicit display categories. Current item
rows also use `showingType` value `0` as a large default bucket with 1,537
items.

`python -m py_compile tools\endfield_source_graph.py` passed.
