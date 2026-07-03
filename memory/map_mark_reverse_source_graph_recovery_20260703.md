# Map Mark Reverse Source-Graph Recovery - 2026-07-03

## Scope

Decoded level map marks already linked outward to displayed items, rewards,
activities, activity stages, system interactives, and minigames. This pass adds
the reverse edges so queries starting from those target nodes can discover the
map marks that surface them.

## Added Reverse Edges

- `item_displayed_by_map_mark`
- `reward_used_by_map_mark`
- `activity_used_by_map_mark`
- `activity_stage_used_by_map_mark`
- `system_interactive_used_by_map_mark`
- `minigame_used_by_map_mark`

## Validation

Focused temp graph:
`tmp/map_mark_reverse_validate.sqlite`

The validation seeded item economy, reward catalog, activity achievement rows,
and decoded config semantics.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `map_mark_displays_item` | 109 | `item_displayed_by_map_mark` | 109 |
| `map_mark_rewards` | 42 | `reward_used_by_map_mark` | 42 |
| `map_mark_activity` | 42 | `activity_used_by_map_mark` | 42 |
| `map_mark_activity_stage` | 35 | `activity_stage_used_by_map_mark` | 35 |
| `map_mark_system_instance` | 122 | `system_interactive_used_by_map_mark` | 122 |
| `map_mark_minigame` | 103 | `minigame_used_by_map_mark` | 103 |

`python -m py_compile tools\endfield_source_graph.py` passed.
