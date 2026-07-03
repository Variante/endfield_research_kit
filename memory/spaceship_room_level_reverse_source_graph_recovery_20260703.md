# Spaceship Room Level Reverse Source-Graph Recovery - 2026-07-03

## Scope

Spaceship room level rows already linked outward to room types, upgrade
dialogs, prerequisite levels, rewards, formulas, and room-type unlocks. This
pass added the missing reverse edges for those relationships. Item costs and
grow-cabin planting fields already had reverse edges and were left unchanged.

## Added Reverse Edges

- `story_used_by_spaceship_room_level_upgrade`
- `spaceship_room_level_required_by_level`
- `spaceship_room_type_has_room_level`
- `reward_used_by_spaceship_room_level`
- `spaceship_formula_unlocked_by_room_level`
- `spaceship_room_type_unlocked_by_room_level`

## Validation

Focused temp graph:
`tmp/spaceship_room_level_reverse_validate.sqlite`

Counts from `ingest_spaceship_semantics()`:

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `spaceship_room_level_upgrade_dialog` | 15 | `story_used_by_spaceship_room_level_upgrade` | 15 |
| `spaceship_room_level_condition` | 10 | `spaceship_room_level_required_by_level` | 10 |
| `spaceship_room_level_for_type` | 25 | `spaceship_room_type_has_room_level` | 25 |
| `spaceship_room_level_reward` | 0 | `reward_used_by_spaceship_room_level` | 0 |
| `spaceship_room_level_unlocks_formula` | 23 | `spaceship_formula_unlocked_by_room_level` | 23 |
| `spaceship_room_level_unlocks_room_type` | 5 | `spaceship_room_type_unlocked_by_room_level` | 5 |

CLI smoke checks:

- `python tools\endfield_source_graph.py query growcabin_plant_crylplant_1_1 --kind spaceship_formula --db tmp\spaceship_room_level_reverse_validate.sqlite --limit 12`
  showed `spaceship_formula_unlocked_by_room_level` from
  `grow_cabin_level_1`.
- `python tools\endfield_source_graph.py query grow_cabin_level_1 --kind spaceship_room_level --db tmp\spaceship_room_level_reverse_validate.sqlite --limit 14`
  showed formula unlocks, planting-field unlocks, item cost, and room-type
  context together for the level.
- `python tools\endfield_source_graph.py query 0 --kind spaceship_room_type --db tmp\spaceship_room_level_reverse_validate.sqlite --limit 14`
  resolved the room type and its room-level context.

`python -m py_compile tools\endfield_source_graph.py` passed after the focused
validation build completed.
