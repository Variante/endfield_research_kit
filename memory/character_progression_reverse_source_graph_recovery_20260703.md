# Character Progression Reverse Source Graph Recovery - 2026-07-03

## Context

Character progression tables already exposed level-cost and break-config rows,
but item-centric queries could not directly answer which level costs used gold
or which break configs accepted a specific exp item.

## Change

`tools/endfield_source_graph.py` now emits:

- `character_level_cost_requires_gold`
- `item_gold_cost_for_character_level_cost`
- `item_usable_for_character_break_exp`

The level-cost gold edge links each `CharacterLevelTable` cost row to the
canonical `item_gold` node. The break exp-item reverse edge mirrors the existing
`character_break_config_exp_item` edge from `CharBreakTable.availableExpItems`.

## Validation

```bat
python -B -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\character_progression_reverse_validation_20260703.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Temporary graph result:

```text
Source graph: 1691485 nodes, 3805874 edges, 2289338 aliases
```

SQLite reverse-pair checks:

| Forward | Reverse | Count |
|---|---|---:|
| `character_level_cost_requires_gold` | `item_gold_cost_for_character_level_cost` | 90 |
| `character_break_config_exp_item` | `item_usable_for_character_break_exp` | 13 |

Both pairs had `0` missing reverse edges and `0` extra reverse edges. The graph
contains one canonical `item:item_gold` node.
