# Grow Cabin Planting Field Source Graph Recovery - 2026-07-03

## Context

`SpaceshipGrowCabinLvTable` defines which planting fields unlock at each Grow
Cabin level through `unlockPlantingField`. The source graph already represented
Grow Cabin level nodes and their unlocked recipes, but planting-slot expansion
was only present in the row payload.

`SpaceshipGrowCabinBoxIdToUnlockLevelTable` also maps field/box ids `1..9` to
numeric unlock levels, but those edges point at generic numeric
`spaceship_room_level` nodes rather than the concrete `grow_cabin_level_*`
nodes.

## Implementation

`tools/endfield_source_graph.py` now adds:

- `spaceship_grow_cabin_planting_field` nodes
- `spaceship_room_level_unlocks_planting_field`
- `spaceship_planting_field_unlocked_by_room_level`

The implementation is localized to `add_spaceship_specialized_room_level_edges`
for `unlockPlantingField`.

## Validation

Focused validation graph:

```text
nodes spaceship_grow_cabin_planting_field 9
edges spaceship_room_level_unlocks_planting_field 9
edges spaceship_planting_field_unlocked_by_room_level 9
```

Sample evidence:

```text
spaceship_room_level:grow_cabin_level_1
  spaceship_room_level_unlocks_planting_field -> spaceship_grow_cabin_planting_field:1
  spaceship_room_level_unlocks_planting_field -> spaceship_grow_cabin_planting_field:2
  spaceship_room_level_unlocks_planting_field -> spaceship_grow_cabin_planting_field:3

spaceship_grow_cabin_planting_field:1
  spaceship_planting_field_unlocked_by_room_level -> spaceship_room_level:grow_cabin_level_1
```

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query grow_cabin_level_1 --kind spaceship_room_level --db tmp\grow_cabin_planting_field_validation.sqlite --limit 16
python tools\endfield_source_graph.py query 1 --kind spaceship_grow_cabin_planting_field --db tmp\grow_cabin_planting_field_validation.sqlite --limit 12
```

Both queries showed the new forward and reverse planting-field unlock edges.
