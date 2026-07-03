# Stage Difficulty Reverse Source Graph Recovery - 2026-07-03

## Context

Simulation training, tower defense, and level-grade tables already exposed
authored stage and difficulty relationships in the forward direction. Reverse
lookup from enemies, cards, spawners, recommended items, or grade entries still
required manual SQL, which made balancing and stage-composition questions harder
to answer from a known target id.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for selected
stage/difficulty relationships:

- `enemy_used_by_simulation_training_card`
- `simulation_training_card_used_by_pool`
- `enemy_used_by_tower_defense_stage`
- `item_recommended_by_tower_defense_stage`
- `tower_defense_spawner_used_by_stage`
- `level_grade_entry_in_config`
- `level_uses_level_grade_config`

The reverse edges preserve the same source, evidence, and level/count/index
payloads as the forward edges. `level_uses_level_grade_config` is emitted only
when the level-grade config key looks like a level id.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\stage_difficulty_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,819,382 edges.
Forward/reverse counts matched:

- `simulation_training_card_enemy`: 28 / `enemy_used_by_simulation_training_card`: 28
- `simulation_training_pool_has_card`: 125 / `simulation_training_card_used_by_pool`: 125
- `tower_defense_enemy`: 96 / `enemy_used_by_tower_defense_stage`: 96
- `tower_defense_recommended_building_item`: 82 / `item_recommended_by_tower_defense_stage`: 82
- `tower_defense_stage_spawner`: 22 / `tower_defense_spawner_used_by_stage`: 22
- `level_grade_config_has_grade`: 197 / `level_grade_entry_in_config`: 197
- `level_grade_config_for_level`: 14 / `level_uses_level_grade_config`: 14
