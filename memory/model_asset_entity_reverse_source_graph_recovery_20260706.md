# Model Asset Entity Reverse Source-Graph Recovery - 2026-07-06

## Scope

This pass added reverse lookup edges in the shared
`add_model_asset_entity_edges()` helper. The helper links semantic owners such
as model configs, interactive templates, weapons, world harvestables, enemies,
and MonoBehaviour frontier entries to resolved exported model `asset_entity`
nodes.

The new edges mirror only exact resolved asset-entity matches already emitted by
the helper. They do not infer renderer usage, prefab hierarchy, animation
binding, or runtime spawn behavior.

## Added Edges

- `asset_entity_used_by_model_config`
- `asset_entity_used_by_model_view_state_controller`
- `asset_entity_used_by_interactive_template`
- `asset_entity_used_by_harvestable`
- `asset_entity_used_by_world_tree`
- `asset_entity_used_by_planting_crop`
- `asset_entity_used_by_weapon_model`
- `asset_entity_used_by_enemy`
- `asset_entity_used_by_monobehaviour_frontier_entry`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:
`tmp/model_asset_entity_reverse_validate.sqlite`

The validation seeded:

- `ingest_assets()`
- `ingest_decoded_config_semantics()`
- `ingest_world_harvestable_semantics()`
- `ingest_weapon_semantics()`
- `ingest_enemy_semantics()`
- `ingest_monobehaviour_frontier_report()`

| Forward edge | Forward count | Reverse edge | Reverse count | Missing reverse |
| --- | ---: | --- | ---: | ---: |
| `model_config_asset_entity` | 215 | `asset_entity_used_by_model_config` | 215 | 0 |
| `model_view_state_controller_asset_entity` | 86 | `asset_entity_used_by_model_view_state_controller` | 86 | 0 |
| `interactive_template_asset_entity` | 82 | `asset_entity_used_by_interactive_template` | 82 | 0 |
| `harvestable_uses_model_asset` | 0 | `asset_entity_used_by_harvestable` | 0 | 0 |
| `world_tree_uses_model_asset` | 2 | `asset_entity_used_by_world_tree` | 2 | 0 |
| `planting_crop_uses_model_asset` | 0 | `asset_entity_used_by_planting_crop` | 0 | 0 |
| `weapon_model_asset_entity` | 130 | `asset_entity_used_by_weapon_model` | 130 | 0 |
| `enemy_uses_model_asset` | 0 | `asset_entity_used_by_enemy` | 0 | 0 |
| `monobehaviour_frontier_entry_model_asset_entity` | 99 | `asset_entity_used_by_monobehaviour_frontier_entry` | 99 | 0 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `asset_entity` | 10,678 |
| `model_config_model` | 1,280 |
| `model_view_state_controller` | 399 |
| `interactive_template` | 271 |
| `planting_crop` | 16 |
| `weapon` | 71 |
| `enemy` | 289 |
| `monobehaviour_frontier_entry` | 726 |
