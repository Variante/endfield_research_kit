# Model world-entity source graph recovery - 2026-07-02

## Context

The model-prefab and model-interactive-template slices made decoded model
configuration easier to query from the model side without promoting speculative
renderable asset bindings. The remaining high-use unbound models are mostly
world placements from decoded world-entity registries.

Existing graph edges already proved the forward relationship:

- `world_entity_uses_model`
- `world_entity_instance_uses_model`
- `world_entity_script_slot_uses_model`

Those edges are based on decoded `detailId` fields resolving to existing
`model_config_model` rows.

## Graph Change

`tools/endfield_source_graph.py` now emits model-centric reverse edges for the
same decoded evidence:

- `model_config_used_by_world_entity`
- `model_config_used_by_world_entity_instance`
- `model_config_used_by_world_entity_script_slot`

These are query convenience edges for original game-data placement evidence.
They mean "this decoded world entity/detail id resolves to this model config
row." They do not mean an exported renderable asset was found.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\model_world_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,007 nodes, 3,125,477 edges, 2,277,552 aliases
- `world_entity_uses_model`: 267 edges
- `model_config_used_by_world_entity`: 267 edges
- `world_entity_instance_uses_model`: 4,368 edges
- `model_config_used_by_world_entity_instance`: 4,368 edges
- `world_entity_script_slot_uses_model`: 71 edges
- `model_config_used_by_world_entity_script_slot`: 71 edges
- retained `model_config_asset_entity`: 215 edges
- retained `model_config_used_by_interactive_template`: 209 edges

Top decoded world-registry model placements:

| Model config | World entities |
| --- | ---: |
| `int_doodad_ore_cluster_iron` | 92 |
| `int_doodad_ore_cluster_originium` | 52 |
| `int_doodad_flower_1` | 31 |
| `int_doodad_flower_2` | 23 |
| `int_switch_union_v2` | 20 |
| `int_forklift` | 6 |
| `int_doodad_flower_3` | 5 |
| `int_doodad_insect_2` | 5 |
| `int_trchest_common_high` | 5 |

This closes part of the semantic gap for unbound interactive/world models:
querying a model now shows its decoded prefab, decoded interactive-template
consumers, and decoded world placements separately from any exported
`asset_entity` relation.
