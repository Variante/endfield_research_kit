# Factory Seed Reverse Source-Graph Recovery - 2026-07-03

## Scope

`FactorySeedItemTable` maps seed item ids to their interactive pickup/doodad ids.
The source graph already had forward edges from each `factory_seed_item` to its
`item` and `system_interactive` nodes. This pass adds reverse lookup edges so
item and interactive queries can find the seed config that uses them.

## Added Edges

- `item_has_factory_seed_config`
- `system_interactive_used_by_factory_seed_item`

## Validation

Focused temp graph:
`tmp/factory_seed_reverse_validate.sqlite`

The validation seeded `ingest_factory_interaction_lookup_semantics()` only.

| Edge | Count |
| --- | ---: |
| `factory_seed_item_item` | 13 |
| `item_has_factory_seed_config` | 13 |
| `factory_seed_item_doodad` | 13 |
| `system_interactive_used_by_factory_seed_item` | 13 |

Node counts in the focused graph:

| Node kind | Count |
| --- | ---: |
| `factory_seed_item` | 13 |
| `item` | 45 |
| `system_interactive` | 23 |

`python -m py_compile tools\endfield_source_graph.py` passed.
