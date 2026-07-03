# World Energy Reverse Source Graph Recovery - 2026-07-03

## Context

World Energy tables describe domain point groups, world-level point instances,
enemy lineups, probable gem drops, regular item drops, and level placement.
Forward graph edges existed from the point or group to these targets, but
enemy-, item-, or level-centered queries could not directly enumerate related
World Energy points.

## Finding

`tools/endfield_source_graph.py` now emits reverse World Energy edges:

- `enemy_used_by_world_energy_point`
- `level_has_world_energy_point`
- `item_regular_drop_for_world_energy_point`
- `item_probable_gem_for_world_energy_point`
- `item_custom_gem_for_world_energy_group`
- `item_random_gem_for_world_energy_group`

The reverse edges preserve the original evidence path and payloads, including
enemy level, item count, index, and world-level group context where present.

## Validation

Focused temporary graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DB: `tmp/world_energy_reverse.sqlite`

World-energy semantic counts:

- `world_energy_point_enemy`: 441 / reverse 441
- `world_energy_point_in_level`: 63 / reverse 63
- `world_energy_point_regular_item`: 36 / reverse 36
- `world_energy_point_probable_gem`: 567 / reverse 567
- `world_energy_group_custom_gem_item`: 9 / reverse 9
- `world_energy_group_random_gem_item`: 9 / reverse 9

Sample reverse edges showed enemies such as `enemy:eny_0007_mimicw` pointing
back to `world_energy_point:*` rows with preserved `enemyIds[...]` evidence and
enemy-level payloads.
