# Model interactive-template source graph recovery - 2026-07-02

## Context

The previous model-prefab slice made decoded `ModelTable.prefabPath` values
queryable without claiming missing exported renderable assets. The next
conservative bridge is decoded interactive-template usage.

`Json_Interactive` entries already produced `interactive_template_data ->
model_config_model` edges from exact `componentModelData.modelId` or
`modelComponent` evidence. That was useful but made model-centric queries less
direct because the consumer was the intermediate decoded data node, not the
resolved `interactive_template` node.

## Graph Change

`tools/endfield_source_graph.py` now also adds:

- `model_config_used_by_interactive_template`

from `model_config_model` to `interactive_template` whenever the decoded
interactive template names an exact model component. This is runtime/container
evidence from decoded game-data payloads, not an exported renderable binding.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\model_template_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,007 nodes, 3,120,771 edges, 2,277,552 aliases
- `model_config_model`: 1,201 nodes
- `interactive_template`: 271 nodes
- `interactive_template_uses_model`: 418 data-level edges
- `model_config_used_by_interactive_template`: 209 compact model-to-template edges
- retained `model_prefab`: 1,152 nodes
- retained `model_config_uses_prefab`: 1,202 edges
- retained `model_config_asset_entity`: 215 edges
- `prefab_path`: 1,152 aliases on `model_prefab`
- `model_config_prefab_path`: 1,202 aliases on `model_config_model`
- `model_prefab_stem`: 1,152 aliases

Example model consumers:

- `int_doodad_ore_cluster_originium` -> `int_weekraid_mine`
- `int_fixable_robot` -> `int_fixable_props`, `int_fixable_robot`
- `int_doodad_placeholder_postmodel` -> `int_doodad_common`,
  `int_doodad_core_mine`, `int_doodad_core_plant`, `int_drop_common`
- `int_laser_unmove_01` -> `int_laser`, `int_laser_move`

This advances the asset semantics gap by showing which decoded interactive
containers use a model even when exported renderable assets remain absent.

The same validation also covered two graph-query hygiene improvements:

- Lua module focus payloads are normalized to focus-name arrays, with
  `focusCounts` retained when the audit source has per-focus hit counts.
- Query seed ranking now prefers `model_prefab` nodes for `prefab_path` and
  `model_prefab_stem` aliases while retaining `model_config_prefab_path` on
  model rows.

## Follow-up: world entity model consumers

The graph now also adds reverse model-consumer edges when world-entity detail ids resolve to `model_config_model` nodes. This covers direct `world_entity` rows plus shared `add_world_entity_detail_ref_edges` callers for `world_entity_instance` and `world_entity_script_slot` owners.

Validation command:

```bat
python tools\endfield_source_graph.py build --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,007 nodes, 3,125,477 edges, 2,277,552 aliases
- retained `model_config_used_by_interactive_template`: 209 edges
- added `model_config_used_by_world_entity`: 267 edges
- added `model_config_used_by_world_entity_instance`: 4,368 edges
- added `model_config_used_by_world_entity_script_slot`: 71 edges

A query for `int_fixable_robot --kind model_config_model` now shows its interactive templates, direct world entity, and many world entity instances from the model node, making model-centric recovery usable without starting from each map/entity container.
