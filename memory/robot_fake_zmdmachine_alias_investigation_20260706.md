# Robot Fake ZMD-Machine Alias Investigation - 2026-07-06

## Question

The controller-alias census identified `int_robot_fake_postmodel` as an
unresolved model binding with a controller reference to
`interactive_zmdmachine_1_001_s01`. This pass checks whether the fake robot
interactive can be semantically tied to the exported ZMD-machine renderable
family, and what confidence limits remain.

## Evidence

Model binding query:

```bat
python tools\endfield_source_graph.py model-bindings --term int_robot_fake --sort usage --limit 20
```

Rows:

- `int_robot_fake_postmodel`
  - Status: `no_exported_renderable_candidate`
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_robot_fake_postmodel.prefab`
  - `interactiveTemplateUses=2`
  - `worldEntityUses=0`
  - `hasRadius=false`
  - No direct or candidate exported asset entity from model id or prefab stem.

The graph shows both recovered copies of the interactive template use this
model id:

- `interactive_template_data:StreamingAssets:int_robot_fake`
- `interactive_template_data:Persistent:int_robot_fake`

Both edges use `componentModelData.modelId` evidence. The template summaries
identify a normal interactive data row:

- `name=int_robot_fake`
- `objectType=int_robot_fake`
- `factionIndex=4`
- `components=4`
- first component: `Core_InteractiveRootComponentData`

The model-table row is a postmodel prefab wrapper, not an exported asset-name
match:

```json
{
  "modelId": "int_robot_fake_postmodel",
  "duplicateModelId": "int_robot_fake_postmodel",
  "prefabPath": "Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_robot_fake_postmodel.prefab",
  "scale": 1.0,
  "flag": 1,
  "tailInt": 0
}
```

The model-view state controller is the source of the ZMD-machine evidence:

- Node: `model_view_state_controller:int_robot_fake_postmodel`
- Path:
  `Persistent/Data/Json/Interactive/ModelViewStateControllerData/int_robot_fake_postmodel.json`
- Summary:
  - `modelId=int_robot_fake_postmodel`
  - `clipInfos=1`
  - `effects=4`
  - `modelAnimatorDatas=1`
  - `preTickAnimator=false`
  - clip: `A_interactive_zmdmachine+1_001_damage_01`

Controller edges include:

- `model_view_state_controller_has_clip_asset`
  `model_view_clip_ref:A_interactive_zmdmachine+1_001_damage_01`
  from `clipAssetInfos`.
- `model_view_state_controller_animator_references_clip`
  `model_view_clip_ref:A_interactive_zmdmachine+1_001_damage_01`
  from `modelAnimatorDataClipRefs[0]`.
- `model_view_state_controller_animator_references_effect`
  `gameplay_effect:P_interactive_zmdmachine+1_001_s01`
  from `modelAnimatorDataEffectRefs[4]`.
- Other effect refs:
  - `P_interactive_robotemoji_sos_01`
  - `P_interactive_robotsos_middle_01`
  - `P_fxmap_uninteractive_storehous_01`
  - `P_lv005_smokeblack_small_01`

A temp-regenerated alias-enriched model binding report maps the controller
effect ref to the exported asset entity:

```json
{
  "controllerNode": "model_view_state_controller:int_robot_fake_postmodel",
  "controllerName": "int_robot_fake_postmodel",
  "refNode": "gameplay_effect:P_interactive_zmdmachine+1_001_s01",
  "refName": "P_interactive_zmdmachine+1_001_s01",
  "edgeKind": "model_view_state_controller_animator_references_effect",
  "evidence": "modelAnimatorDataEffectRefs[4]",
  "candidateBase": "interactive_zmdmachine_1_001_s01",
  "entity": {
    "node": "asset_entity:StreamingAssets/interactive_zmdmachine_1_001_s01",
    "base": "interactive_zmdmachine_1_001_s01",
    "source": "StreamingAssets",
    "lodModelCount": 4,
    "materialCount": 0,
    "textureCount": 0
  }
}
```

Exported asset index checks:

- 0 entries contain `int_robot_fake`.
- 0 entries contain `robot_fake`.
- 4 entries contain exact `interactive_zmdmachine_1_001_s01`:
  - `StreamingAssets/Mesh/S_interactive_zmdmachine_1_001_s01_lod0_pB7FF62CB1D2793D5.obj`
  - `StreamingAssets/Mesh/S_interactive_zmdmachine_1_001_s01_lod1_p15FCF616B1E793D5.obj`
  - `StreamingAssets/Mesh/S_interactive_zmdmachine_1_001_s01_lod2_pC09883A0A8B093D5.obj`
  - `StreamingAssets/Mesh/S_interactive_zmdmachine_1_001_s01_lod3_p1AA016A39AD993D5.obj`
- 0 entries contain the plus-form string `interactive_zmdmachine+1_001_s01`.
- 17 entries contain broader `interactive_zmdmachine`.

The source graph currently has three exported ZMD-machine asset entities:

- `asset_entity:StreamingAssets/interactive_zmdmachine_1_001_s01`
  - 4 LOD meshes.
  - 0 material relations.
  - 0 texture relations.
- `asset_entity:StreamingAssets/interactive_zmdmachine+1_002_l01`
  - 4 LOD meshes.
  - 1 material relation.
  - 4 texture relations.
- `asset_entity:StreamingAssets/interactive_zmdmachine+1_008_m01`
  - 3 LOD meshes.
  - 1 material relation.
  - 3 texture relations.

The material-bearing neighboring entities use plus-form exported stems. Their
relations include:

- `M_interactive_zmdmachine+1_002_l01`
- `M_interactive_zmdmachine+1_008_m01`
- `T_interactive_zmdmachine+1_008_m01_D`
- `T_interactive_zmdmachine+1_008_m01_NRO`
- shared/default material textures such as `T_default_mro_MRO`.

No material or texture relation is currently recovered for exact
`interactive_zmdmachine_1_001_s01`.

## Interpretation

`int_robot_fake_postmodel` is another controller-alias case: the model table
and template ids are gameplay/postmodel names, while the model-view state
controller points at a visual asset family through animation and effect refs.

The strongest renderable target is:

```text
asset_entity:StreamingAssets/interactive_zmdmachine_1_001_s01
```

Confidence is meaningful but narrower than the upgradebot or organ-door cases:

- The controller explicitly references the same ZMD-machine family through
  both a clip (`A_interactive_zmdmachine+1_001_damage_01`) and an effect
  (`P_interactive_zmdmachine+1_001_s01`).
- The normalized effect stem has an exact exported mesh entity with four LODs.
- There is no direct `int_robot_fake` asset family in the exported asset index.
- There are no recovered material or texture relations for the exact
  `_1_001_s01` entity, even though nearby `+1_002_l01` and `+1_008_m01`
  variants do have material/texture relations.

This suggests the fake robot interactive likely reuses a small/special
ZMD-machine renderable or effect-driven presentation, but the current graph
should still report it as a controller alias rather than a direct model binding.
The missing exact material relation may be real, may depend on runtime prefab
composition not exported into the current index, or may reflect an unrecovered
plus/underscore material naming bridge.

## Recovery Implications

- A future model-binding UI/report can surface
  `interactive_zmdmachine_1_001_s01` as a controller-derived candidate for
  `int_robot_fake_postmodel`.
- It should keep the existing direct-binding status separate from
  controller-alias status, because the prefab/model table does not directly name
  the renderable entity.
- It should expose material coverage as incomplete for this candidate.
- It should not borrow the `+1_002_l01` or `+1_008_m01` materials for
  `_1_001_s01` without stronger evidence, because those are adjacent
  ZMD-machine variants rather than exact stem matches.

## Next Checks

- Compare this pattern with `int_system_spaceship_credit_shop_postmodel`, which
  also aliases into a ZMD-machine family in the controller-alias census.
- Inspect whether any Animator/Prefab exported metadata links
  `P_interactive_zmdmachine+1_001_s01` to materials not visible through the
  current asset index.
- Consider adding a report column for controller-alias material completeness so
  these cases are ranked below aliases with recovered mesh, material, and
  texture coverage.
