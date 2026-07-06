# Switch Union Model Binding Investigation - 2026-07-06

## Question

`int_switch_union_v2` is the next high-use
`no_exported_renderable_candidate` row after the ore-cluster and flower passes.
This pass checks whether the missing renderable is a true extraction gap or an
alias through the switch/universal-switch runtime controller data.

## Evidence

Triage command:

```bat
python tools\endfield_source_graph.py model-bindings --term int_switch --sort usage --limit 40
```

Findings for `int_switch_union_v2`:

- Model id: `int_switch_union_v2`
- Prefab path:
  `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_switch_union_v2_postmodel.prefab`
- Prefab stem: `int_switch_union_v2_postmodel`
- Status: `no_exported_renderable_candidate`
- `worldEntityUses=20`
- `interactiveTemplateUses=0`
- No direct graph edge to an `asset_entity`.
- No candidate entity from the usual model id, prefab stem, or prefab path
  tokens.

Direct edge counts around `model_config_model:int_switch_union_v2`:

- 20 `world_entity_uses_model` links.
- 24 `world_entity_instance_uses_model` links.
- 5 `world_entity_script_slot_uses_model` links.
- 1 `model_view_state_controller_uses_model` link.
- 1 `model_config_uses_prefab` link.
- 1 `model_config_has_radius` link.

Sample world entity links include `world_entity:2800001294`,
`world_entity:2800001309`, `world_entity:2800001315`,
`world_entity:2800001332`, `world_entity:2800001335`,
`world_entity:2800001336`, `world_entity:2800001363`,
`world_entity:2800001364`, `world_entity:2800001365`,
`world_entity:2800001443`, `world_entity:2800001478`, and
`world_entity:2800001479`, all with `detailId` evidence.

The script-slot edges all use `world_entity_script_slot:13000000033` slots
`40001` through `40005`, also with `detailId` evidence.

The graph has concrete semantic nodes for the id:

- `interactive_object:int_switch_union_v2`
  - Data: `objectId=int_switch_union_v2`, `templateId=int_switch_common`.
  - It is defined by both Persistent and StreamingAssets
    `InteractiveTable.json`.
  - It links to `interactive_template:int_switch_common`.
- `level_data_param:int_switch_union_v2`
  - Referenced by level data strings in:
    - `Json/LevelData/dung01_rdg002/dung01_rdg002_lv_data.json`
    - `Json/LevelData/map01_lv001/map01_lv001_lv_data_sub_sm1l1m2.json`
    - `Json/LevelData/map01_lv002/map01_lv002_lv_data.json`
    - `Json/LevelData/map01_lv002/map01_lv002_lv_data_sub_sm1l2m4.json`
    - `Json/LevelData/map01_lv007/map01_lv007_lv_data.json`
- `model_view_state_controller:int_switch_union_v2`
  - Defined by both Persistent and StreamingAssets
    `Interactive/ModelViewStateControllerData/int_switch_union_v2.json`.
  - The decoded summary reports `modelId=int_switch_union_v2`, 7 clip infos,
    3 emissive hashes, 1 model animator data entry, and
    `preTickAnimator=false`.

The model-view state controller is the important alias clue. It references:

- Clips:
  - `A_interactive_universalswitch+1_001_01_closeidle_01`
  - `A_interactive_universalswitch+1_001_01_open_01`
  - `A_interactive_universalswitch+1_001_01_openidle_01`
  - `A_interactive_universalswitch+1_001_01_close_01`
- Effect:
  - `P_interactive_universalswitch+1_001_01`
- Animator names including `BaseLayer`, `off_idle`, `state`, `off_to_on`,
  `on_idle`, `on_to_off`, `Effect`, `conduit`, `is_locked`,
  `LockedByGameplayLock`, `disable`, `On`, `Off`,
  `int_eswitch_v2_light_disable`, `int_eswitch_v2_light_on`, and
  `int_eswitch_v2_light_available`.

Exported asset checks:

- `webui/data/assets/index.json` has 0 entries for `int_switch_union`,
  `switch_union`, or `union_v2`.
- The same index has 30 `int_switch` entries. Four are concrete switch
  postmodel FBX files:
  - `StreamingAssets/Animator/int_switch_waterstate_wltech01_postmodel_p765CF6B57B5D36B2.fbx`
  - `StreamingAssets/Animator/int_switch_waterstate_xiranturpart_postmodel_pAADD0C379712DF8C.fbx`
  - `StreamingAssets/Animator/int_switch_wltech01_postmodel_p4352735B49C86A63.fbx`
  - `StreamingAssets/Animator/int_switch_wltech02_postmodel_pC40D4EFE67F1FBF0.fbx`
- The graph has 31 `asset_entity` rows with `switch` in the name, including
  generic map switches, water-state switches, WLTech switches, and two
  `interactive_universalswitch` entities.
- `interactive_universalswitch` is a strong semantic neighbor:
  - `webui/data/assets/index.json` has 24 entries for
    `interactive_universalswitch`.
  - `asset_entity:StreamingAssets/interactive_universalswitch_1_001_01`
    has 5 LOD model links.
  - `asset_entity:StreamingAssets/interactive_universalswitch_1_002_01`
    has 4 LOD model links.
  - The asset index contains animator FBX exports:
    `P_interactive_universalswitch+1_001_01_*` and
    `P_interactive_universalswitch+1_002_01_*`.
  - It also contains mesh LODs, textures, and material JSON for
    `interactive_universalswitch_1_001_01` and
    `interactive_universalswitch_1_002_01`.

## Interpretation

`int_switch_union_v2` is not dead config. It is a placed world interactive,
appears in level data, uses the common switch template, participates in
script-slot detail ids, and has its own decoded model-view state controller.

The missing direct renderable binding is likely an aliasing problem rather than
a total asset absence. There is no exported `int_switch_union_v2_postmodel`
entity, but the controller for this model references
`interactive_universalswitch+1_001_01` animation clips and effects, and the
asset index does contain corresponding `interactive_universalswitch` model,
mesh, texture, and material exports.

The current `model-bindings` report is correctly conservative: it should not
auto-bind `int_switch_union_v2` to `interactive_universalswitch_1_001_01` from
name similarity alone. The stronger path is to add or surface explicit
model-view-state-controller alias evidence from clip/effect names to exported
asset entities.

## Next Checks

- Teach the source graph to report model-view-state-controller asset aliases
  for unresolved model configs when clip/effect stems map to exported asset
  entities.
- Verify whether `P_interactive_universalswitch+1_001_01` FBX exports are
  animation/controller-only or usable renderable wrappers around the
  `S_interactive_universalswitch_1_001_01_*` mesh LODs.
- Compare `int_switch_union_v2`, `int_switch_common`, `int_switch_v2`, and
  `int_switch_doorunion_v2` interactive rows to determine whether
  `interactive_universalswitch_1_001_01` is the shared visual for this switch
  family or only one state/controller layer.
