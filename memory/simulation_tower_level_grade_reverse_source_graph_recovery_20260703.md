# Simulation Tower Level Grade Reverse Source Graph Recovery - 2026-07-03

## Context

Simulation training, tower defense, and level-grade tables had useful forward
links from stages/configs toward enemies, cards, items, spawners, levels, and
grade entries. Reverse lookup from those targets still required manual SQL.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for:

- `enemy_used_by_simulation_training_card`
- `simulation_training_card_used_by_pool`
- `enemy_used_by_tower_defense_stage`
- `item_recommended_by_tower_defense_stage`
- `tower_defense_spawner_used_by_stage`
- `level_uses_level_grade_config`
- `level_grade_entry_in_config`

The level-grade importer also links level-looking `LevelGradeTable` config keys
to level nodes with `level_grade_config_for_level`.

## Validation

```bat
python -B -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\simulation_tower_reverse_validation_20260703.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Temporary graph result:

```text
Source graph: 1691485 nodes, 3819382 edges, 2289352 aliases
```

SQLite reverse-pair checks:

| Forward | Reverse | Count |
|---|---|---:|
| `simulation_training_card_enemy` | `enemy_used_by_simulation_training_card` | 28 |
| `simulation_training_pool_has_card` | `simulation_training_card_used_by_pool` | 125 |
| `tower_defense_enemy` | `enemy_used_by_tower_defense_stage` | 96 |
| `tower_defense_recommended_building_item` | `item_recommended_by_tower_defense_stage` | 82 |
| `tower_defense_stage_spawner` | `tower_defense_spawner_used_by_stage` | 22 |
| `level_grade_config_for_level` | `level_uses_level_grade_config` | 14 |
| `level_grade_config_has_grade` | `level_grade_entry_in_config` | 197 |

All seven pairs had `0` missing reverse edges and `0` extra reverse edges.
