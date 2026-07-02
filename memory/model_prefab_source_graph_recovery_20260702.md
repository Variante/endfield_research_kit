# Model prefab source graph recovery - 2026-07-02

## Context

`reports/source_graph/model_config_asset_binding_candidates.json` showed a
remaining asset-semantics gap: `161` referenced `model_config_model` rows had
world or interactive-template use but no exported renderable `asset_entity`
candidate.

The follow-up inspection confirmed this should not be treated as a missing
renderable edge:

- `159/161` unbound records have no exported asset-index relation.
- `160/161` point into
  `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels`.
- `148/161` have exact decoded `Json_Interactive` `modelComponent` evidence.
- The high-use rows, such as `int_doodad_ore_cluster_iron`,
  `int_doodad_ore_cluster_originium`, `int_doodad_flower_1`, and
  `int_switch_union_v2`, are decoded config model/prefab facts even when the
  renderable export is absent.

## Graph Change

`tools/endfield_source_graph.py` now creates a conservative prefab layer during
decoded `ModelTable` ingestion:

- `model_prefab` nodes keyed by decoded `prefabPath`
- `model_config_uses_prefab` edges from `model_config_model` to `model_prefab`
- `prefab_path` and `model_prefab_stem` aliases on the prefab node

This preserves original config semantics without promoting speculative
`model_config_model -> asset_entity` links.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\model_prefab_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,007 nodes, 3,120,562 edges, 2,277,552 aliases
- `model_config_model`: 1,201 nodes
- `model_prefab`: 1,152 nodes
- `model_config_uses_prefab`: 1,202 edges
- `prefab_path`: 2,354 aliases
- `model_prefab_stem`: 1,152 aliases
- `model_config_asset_entity`: still 215 edges

Top unbound examples now resolve to prefab nodes:

- `int_doodad_ore_cluster_iron` ->
  `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_ore_cluster_iron_postmodel.prefab`
- `int_doodad_ore_cluster_originium` ->
  `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_ore_cluster_originium_postmodel.prefab`
- `int_doodad_flower_1` ->
  `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_flower_1_postmodel.prefab`
- `int_switch_union_v2` ->
  `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_switch_union_v2_postmodel.prefab`
