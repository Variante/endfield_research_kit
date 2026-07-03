# NavMesh Area State Reverse Source Graph Recovery - 2026-07-03

## Scope

NavMesh decoded config evidence now has reverse links from shared
`navmesh_area_id` nodes back to both authored LunaArea polygons and
NavMeshStateContainer records.

This improves spatial/navigation structure queries such as:

- which decoded polygons use this owner-local area id;
- which bounds/state records refer to this owner-local area id.

This remains decoded config evidence. It does not prove runtime navigation
availability, pathfinding behavior, or live area-state activation.

## Source Data

Source group:

- `webui/data/game_data/groups/Json_NavMesh.json`

Decoded entry types:

- `LunaArea.json`
- `NavMeshStateContainer.json`

The group currently contains 20 NavMesh entries.

## Graph Change

New reverse edge kinds:

- `navmesh_area_id_has_area`
- `navmesh_area_id_used_by_state_record`

These mirror existing forward edges:

- `navmesh_area_has_area_id`
- `navmesh_state_record_references_area_id`

The graph intentionally uses `navmesh_area_id` as the join node instead of
claiming direct state-record-to-polygon targeting. In the focused validation,
area polygons and bounds36 state records did not share any owner+areaId pair
with both sides present, so direct polygon targeting would be overclaiming.

## Validation

Focused temporary graph:

```bat
tmp\navmesh_reverse_validation.sqlite
```

Validation loaded `webui/data/game_data/groups/Json_NavMesh.json`, created file
nodes for the 20 entries, and dispatched only:

- `add_navmesh_luna_area_edges()`
- `add_navmesh_state_container_edges()`

Node counts:

- `navmesh_area`: 139
- `navmesh_area_id`: 17
- `navmesh_state_container`: 6
- `navmesh_state_record`: 569

Forward/reverse counts:

- `navmesh_area_has_area_id`: 139 /
  `navmesh_area_id_has_area`: 139
- `navmesh_state_record_references_area_id`: 57 /
  `navmesh_area_id_used_by_state_record`: 57

Smoke queries:

```bat
python tools\endfield_source_graph.py query map02:12 --kind navmesh_area_id --db tmp\navmesh_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query blackbox01_dg001:2 --kind navmesh_area_id --db tmp\navmesh_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query blackbox01_dg001:f02:r0001 --kind navmesh_state_record --db tmp\navmesh_reverse_validation.sqlite --limit 16
```

`map02:12` shows polygon-side `navmesh_area_id_has_area` edges.
`blackbox01_dg001:2` shows state-record-side
`navmesh_area_id_used_by_state_record` edges. The record query shows the
forward area-id reference plus the new reverse incoming edge through the same
area-id node.
