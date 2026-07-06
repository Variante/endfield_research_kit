# Character Support Dungeon Reverse Source-Graph Recovery - 2026-07-06

## Scope

This pass added reverse lookup edges for character support tables that point to
dungeon ids:

- Character tutorial dungeon bindings.
- Character-to-training-dungeon bindings.
- Character trial dungeon bindings.

The edges mirror authored table references only. They do not infer tutorial
completion, trial availability, character unlock state, or gameplay progression.

## Added Edges

- `dungeon_used_by_tutorial`
- `dungeon_used_by_character_training`
- `dungeon_used_by_trial`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:
`tmp/character_dungeon_reverse_validate.sqlite`

The validation seeded `ingest_character_support_semantics()`.

| Forward edge | Forward count | Reverse edge | Reverse count | Missing reverse |
| --- | ---: | --- | ---: | ---: |
| `tutorial_uses_dungeon` | 44 | `dungeon_used_by_tutorial` | 44 | 0 |
| `character_training_dungeon` | 22 | `dungeon_used_by_character_training` | 22 | 0 |
| `trial_uses_dungeon` | 7 | `dungeon_used_by_trial` | 7 | 0 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `dungeon` | 29 |
| `character_tutorial` | 22 |
| `character` | 29 |
| `character_trial` | 7 |
