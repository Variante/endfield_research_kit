# Game Mechanic Parameter Reverse Source Graph Recovery - 2026-07-03

## Context

`GameMechanicConditionTable` parameter strings already resolved to items,
rewards, characters, enemies, levels, and game mechanic nodes where the string
shape made that interpretation safe. Those links were forward-only from the
condition node, so starting from a referenced character, level, or mechanic did
not directly answer which authored condition parameter used it.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for game-mechanic
condition parameter references:

- `item_used_by_game_mechanic_condition_param`
- `reward_used_by_game_mechanic_condition_param`
- `character_used_by_game_mechanic_condition_param`
- `enemy_used_by_game_mechanic_condition_param`
- `level_used_by_game_mechanic_condition_param`
- `game_mechanic_used_by_condition_param`

The reverse edges preserve the same source, evidence, and parameter payload as
the forward edges, including `realType` and `valueType`.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\game_mechanic_param_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,805,117 edges.
Forward/reverse counts matched:

- `game_mechanic_condition_param_item`: 0 / `item_used_by_game_mechanic_condition_param`: 0
- `game_mechanic_condition_param_reward`: 0 / `reward_used_by_game_mechanic_condition_param`: 0
- `game_mechanic_condition_param_character`: 22 / `character_used_by_game_mechanic_condition_param`: 22
- `game_mechanic_condition_param_enemy`: 0 / `enemy_used_by_game_mechanic_condition_param`: 0
- `game_mechanic_condition_param_level`: 13 / `level_used_by_game_mechanic_condition_param`: 13
- `game_mechanic_condition_param_mechanic`: 296 / `game_mechanic_used_by_condition_param`: 296
