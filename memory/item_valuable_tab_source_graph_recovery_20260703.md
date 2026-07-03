# Item Valuable-Tab Source-Graph Recovery - 2026-07-03

## Scope

`ItemTypeTable.valuableTabType` is populated on every item type row, but the
source graph previously kept it only as row payload. This pass promotes the tab
bucket into graph nodes so item type queries can traverse to their valuable-tab
group, and tab queries can discover all item types in that group.

## Added Nodes And Edges

- Node kind: `item_valuable_tab`
- Edge: `item_type_valuable_tab`
- Reverse edge: `valuable_tab_has_item_type`

The `item_type` node payload now also carries `valuableTabType`.

## Validation

Focused temp graph:
`tmp/item_valuable_tab_validate.sqlite`

The validation seeded `ingest_item_economy()` only.

| Edge | Count |
| --- | ---: |
| `item_type_valuable_tab` | 93 |
| `valuable_tab_has_item_type` | 93 |

Current export uses 9 tab buckets. The largest bucket is tab `6` with 51 item
types, followed by tab `10` with 19 item types.

`python -m py_compile tools\endfield_source_graph.py` passed.
