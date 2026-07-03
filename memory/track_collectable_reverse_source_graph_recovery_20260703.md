# Track Map And Scene Collectable Reverse Source Graph Recovery - 2026-07-03

## Scope

The world-structure graph already exposed authored track-map links, track-map
points, and scene collectables from structured tables. This pass adds reverse
indexes so level- and item-centered queries can answer:

- which track-map points start or end at this level;
- which track-map links start, pass through, or end at this level;
- which scene collectable rows use this item;
- which collectable conversion rows produce this item, when present.

This is authored table evidence only. It does not prove live route navigation,
runtime unlock state, placed world-instance activation, or final collectable
availability in a save file.

## Source Tables

- `TrackMapPointTable.json`
- `TrackMapLinkTable.json`
- `SceneCollectableItemTable.json`

These are ingested through `ingest_world_semantics()`.

## Graph Change

New reverse edge kinds:

- `level_has_track_point_start`
- `level_has_track_point_end`
- `level_has_track_link_start`
- `level_has_track_link_mid`
- `level_has_track_link_end`
- `item_used_by_scene_collectable`
- `item_receives_scene_collectable_conversion`

These mirror existing forward edges:

- `track_point_starts_at_level`
- `track_point_ends_at_level`
- `track_link_starts_at_level`
- `track_link_passes_level`
- `track_link_ends_at_level`
- `scene_collectable_item`
- `scene_collectable_converts_to_item`

The item reverse payload preserves `sceneId` and `maxCount`; conversion reverse
payloads preserve the source item and required count.

## Validation

Focused temporary graph:

```bat
tmp\track_collectable_reverse_validation.sqlite
```

Focused ingest:

- `ingest_world_semantics()`

Forward/reverse counts:

- `track_point_starts_at_level`: 32 / `level_has_track_point_start`: 32
- `track_point_ends_at_level`: 32 / `level_has_track_point_end`: 32
- `track_link_starts_at_level`: 64 / `level_has_track_link_start`: 64
- `track_link_passes_level`: 64 / `level_has_track_link_mid`: 64
- `track_link_ends_at_level`: 64 / `level_has_track_link_end`: 64
- `scene_collectable_item`: 37 / `item_used_by_scene_collectable`: 37
- `scene_collectable_converts_to_item`: 0 /
  `item_receives_scene_collectable_conversion`: 0

Node counts in the focused graph:

- `track_map_point`: 32
- `track_map_link`: 64
- `scene_collectable`: 37
- `level`: 208
- `item`: 5

Smoke queries:

```bat
python tools\endfield_source_graph.py query indie_dg008 --kind level --db tmp\track_collectable_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query int_campfire_v2 --kind item --db tmp\track_collectable_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query 50 --kind track_map_link --db tmp\track_collectable_reverse_validation.sqlite --limit 16
```

The `indie_dg008` query now shows track point/link start, mid, and end reverse
edges from the level. The `int_campfire_v2` query shows scene collectable usage
rows with authored scene and maximum-count payloads.
