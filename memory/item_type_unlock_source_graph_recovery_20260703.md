# Item Type Unlock Source-Graph Recovery - 2026-07-03

## Scope

`ItemTypeTable.unlockSystemType` stores authored unlock gates for item
categories, but the source graph previously only emitted item type definition
and name-text edges. This pass promotes the unlock field into the existing
`gameplay_unlock` vocabulary so unlock queries can discover gated item types.

## Added Edges

- `item_type_unlock_system`
- `gameplay_unlock_controls_item_type`

The `item_type` node data now also carries `unlockSystemType`.

## Validation

Focused temp graph:
`tmp/item_type_unlock_validate.sqlite`

The validation seeded `ingest_item_economy()` only.

| Edge | Count |
| --- | ---: |
| `item_type_unlock_system` | 93 |
| `gameplay_unlock_controls_item_type` | 93 |

Non-default unlock samples:

| Item type | Unlock |
| --- | --- |
| `5` | `251` |
| `19` | `251` |
| `65` | `502` |
| `99` | `56` |

`python -m py_compile tools\endfield_source_graph.py` passed.
