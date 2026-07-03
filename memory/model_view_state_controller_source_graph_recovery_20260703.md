# Model View State Controller Source Graph Recovery - 2026-07-03

## Finding

The existing model/renderable audit still leaves 161 referenced
`model_config_model` rows without exported `asset_entity` candidates. Sampling
top unresolved rows shows why direct promotion is still unsafe:

- `int_doodad_ore_cluster_iron`, `int_doodad_ore_cluster_originium`,
  `int_doodad_flower_1`, and `int_switch_union_v2` resolve cleanly to decoded
  model rows, prefab stems, model radii, and world placements, but not to
  exported mesh/material entity groups with matching names.
- `int_forklift` has exported mesh/material assets under names such as
  `S_anm_common_forklift+1_001_01_*` and `S_prop_common_forklift+1_001_*`,
  which proves related renderable assets exist, but the decoded model id
  `int_forklift` is not enough evidence by itself to choose the correct
  exported group.
- `int_switch_union_v2` has a decoded
  `ModelViewStateControllerData/int_switch_union_v2.json` entry with clips,
  animator names, and gameplay effects such as
  `P_interactive_universalswitch+1_001_01`; these are strong semantic clues but
  still not a direct renderable binding.

## Graph Change

`tools/endfield_source_graph.py` now adds a model-centric reverse edge when a
decoded ModelViewStateController row references a model:

- existing forward edge:
  `model_view_state_controller_uses_model`
- added reverse edge:
  `model_config_used_by_model_view_state_controller`

This is a query convenience edge for decoded controller evidence. It does not
claim that the model resolves to an exported `asset_entity`.

## Validation

Cheap checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Focused decoded-config ingest:

```bat
python -c "... SourceGraphBuilder(db_path='tmp/model_view_controller_edge.sqlite').ingest_decoded_config_semantics() ..."
```

Result:

- `model_config_used_by_model_view_state_controller`: `399` edges
- sample:
  `model_config_model:int_switch_union_v2 -> model_view_state_controller:int_switch_union_v2`

The existing generated full graph also confirms the underlying evidence:

- `model_view_state_controller:int_switch_union_v2`
  `model_view_state_controller_uses_model`
  `model_config_model:int_switch_union_v2`
- controller clip refs include
  `A_interactive_universalswitch+1_001_01_*`
- controller effect refs include
  `P_interactive_universalswitch+1_001_01`

## Follow-Up

Do not promote the top unbound model rows to `asset_entity` by loose name
matching. The next stronger evidence source should be prefab/component or
AssetMap data that directly links the decoded prefab/controller to concrete
Unity object PathIDs or exported mesh/material groups.
