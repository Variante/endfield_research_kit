# Dungeon Training Reverse Source-Graph Recovery - 2026-07-06

## Scope

This pass added reverse lookup edges for direct Dungeon and Factory Dungeon
table relationships already emitted by `tools/endfield_source_graph.py`.

The edges are exact inverses of authored table fields. They do not infer dungeon
unlock state, combat routing, stamina rules, rewards, or runtime progression.

## Added Edges

- `dungeon_type_has_dungeon`
- `dungeon_in_series`
- `level_has_dungeon`
- `enemy_used_by_dungeon`
- `character_related_to_dungeon`
- `domain_has_dungeon`
- `game_mechanic_category_has_dungeon_series`
- `dungeon_category2nd_has_series`
- `map_mark_type_used_by_dungeon_type`
- `domain_has_factory_dungeon`
- `factory_dungeon_required_by`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:
`tmp/dungeon_reverse_validate.sqlite`

The validation seeded `ingest_dungeon_training_semantics()`.

| Forward edge | Forward count | Reverse edge | Reverse count | Missing reverse |
| --- | ---: | --- | ---: | ---: |
| `dungeon_has_type` | 215 | `dungeon_type_has_dungeon` | 215 | 0 |
| `dungeon_series_includes` | 370 | `dungeon_in_series` | 370 | 0 |
| `dungeon_uses_level` | 316 | `level_has_dungeon` | 316 | 0 |
| `dungeon_enemy` | 274 | `enemy_used_by_dungeon` | 274 | 0 |
| `dungeon_related_character` | 29 | `character_related_to_dungeon` | 29 | 0 |
| `dungeon_in_domain` | 46 | `domain_has_dungeon` | 46 | 0 |
| `dungeon_series_game_category` | 60 | `game_mechanic_category_has_dungeon_series` | 60 | 0 |
| `dungeon_series_category2nd` | 106 | `dungeon_category2nd_has_series` | 106 | 0 |
| `dungeon_type_map_mark_type` | 18 | `map_mark_type_used_by_dungeon_type` | 18 | 0 |
| `factory_dungeon_domain` | 46 | `domain_has_factory_dungeon` | 46 | 0 |
| `factory_dungeon_requires` | 34 | `factory_dungeon_required_by` | 34 | 0 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `dungeon` | 215 |
| `dungeon_type` | 18 |
| `dungeon_series` | 106 |
| `level` | 127 |
| `enemy` | 94 |
| `character` | 22 |
| `gameplay_domain` | 2 |
| `game_mechanic_category` | 13 |
| `dungeon_category2nd` | 7 |
| `map_mark_type` | 6 |
