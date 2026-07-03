# Harvestable Reverse Source-Graph Recovery - 2026-07-03

## Scope

The world-harvestable graph already captured forward references from doodads
and fertilize configs. This pass adds reverse lookup edges for the same
structured table evidence so item/effect queries can show where the game uses
them.

## Added Edges

- `item_used_by_world_doodad`
- `fertilize_config_for_item`
- `fertilize_effect_used_by_item`

## Validation

Focused temp graph:
`tmp/harvestable_reverse_validate.sqlite`

The validation seeded `ingest_world_harvestable_semantics()` only.

| Edge | Count |
| --- | ---: |
| `world_doodad_item` | 16 |
| `item_used_by_world_doodad` | 16 |
| `item_has_fertilize_config` | 2 |
| `fertilize_config_for_item` | 2 |
| `fertilize_item_has_effect_type` | 2 |
| `fertilize_effect_used_by_item` | 2 |

Node counts in the focused graph:

| Node kind | Count |
| --- | ---: |
| `world_doodad` | 86 |
| `fertilize_item` | 2 |
| `fertilize_effect` | 3 |
| `item` | 28 |

`python -m py_compile tools\endfield_source_graph.py` passed.
