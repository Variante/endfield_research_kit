# Spaceship Credit Shop ZMD-Machine Alias Investigation - 2026-07-06

## Question

The controller-alias census identified `int_system_spaceship_credit_shop` as
an unresolved model binding with a controller reference to
`anm_map01_zmdmachine_1_001_01`. This pass checks whether the spaceship credit
shop has real placement/template evidence and whether the ZMD-machine alias is
an exported renderable target.

## Evidence

Model binding query:

```bat
python tools\endfield_source_graph.py model-bindings --term int_system_spaceship_credit_shop --sort usage --limit 20
```

The currently generated ignored report under `reports/source_graph/` listed:

- `modelId=int_system_spaceship_credit_shop`
- Status: `no_exported_renderable_candidate`
- Prefab path:
  `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_system_spaceship_credit_shop.prefab`
- `hasRadius=true`
- `interactiveTemplateUses=2`
- No direct or candidate exported asset entity from model id or prefab stem.

However, direct SQLite inspection showed that the old report was hiding
instance-only world placement evidence:

- `world_entity_instance:25800050006`
- `world_entity_instance:9800000033`

Both instances have:

```json
{
  "detailId": "int_system_spaceship_credit_shop",
  "entityType": 32,
  "position": {"x": -82.114, "y": 1.35, "z": -7.564},
  "rotation": {"x": 0.0, "y": 89.9998, "z": 0.0},
  "source": "StreamingAssets"
}
```

Both are linked by `world_entity_instance_uses_model` and reverse
`model_config_used_by_world_entity_instance` edges with `detailId` evidence.
They are also registered from both Persistent and StreamingAssets
`GameplayConfig/WorldEntityRegistry.json` roots.

The binding report generator was patched in this pass to expose
`worldEntityInstanceUses` and `placementUses`. A temp-regenerated report now
shows:

```json
{
  "modelId": "int_system_spaceship_credit_shop",
  "status": "no_exported_renderable_candidate",
  "hasRadius": true,
  "worldEntityUses": 0,
  "worldEntityInstanceUses": 2,
  "placementUses": 2,
  "interactiveTemplateUses": 2
}
```

The decoded model-table row is a postmodel prefab wrapper:

```json
{
  "modelId": "int_system_spaceship_credit_shop",
  "duplicateModelId": "int_system_spaceship_credit_shop",
  "prefabPath": "Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_system_spaceship_credit_shop.prefab",
  "scale": 1.0,
  "flag": 1,
  "tailInt": 0
}
```

The interactive template exists in both source roots:

- `interactive_template_data:StreamingAssets:int_system_spaceship_credit_shop`
- `interactive_template_data:Persistent:int_system_spaceship_credit_shop`

Template summaries identify a system interactive:

- `name=int_system_spaceship_credit_shop`
- `objectType=int_system_spaceship_credit_shop`
- `factionIndex=4`
- `components=7`
- first component: `Core_InteractiveRootComponentData`
- model component: `int_system_spaceship_credit_shop`
- next component: `Core_TriggerZoneComponentForIntData`

The model-view state controller is the source of the renderable alias:

- Node: `model_view_state_controller:int_system_spaceship_credit_shop`
- Path:
  `Persistent/Data/Json/Interactive/ModelViewStateControllerData/int_system_spaceship_credit_shop.json`
- Summary:
  - `modelId=int_system_spaceship_credit_shop`
  - `clipInfos=2`
  - `effects=0`
  - `modelAnimatorDatas=1`
  - `preTickAnimator=false`
  - clips:
    - `A_anm_map01_zmdmachine+1_001_closeidle_01`
    - `A_anm_map01_zmdmachine+1_001_open_01`
  - animator strings: `base`, `idle`, `Status`, `play`

Controller edges include:

- `model_view_state_controller_has_clip_asset`
  `A_anm_map01_zmdmachine+1_001_closeidle_01`
  from `clipAssetInfos`.
- `model_view_state_controller_has_clip_asset`
  `A_anm_map01_zmdmachine+1_001_open_01`
  from `clipAssetInfos`.
- `model_view_state_controller_animator_references_clip`
  for the same two clips from `modelAnimatorDataClipRefs`.
- `model_view_state_controller_animator_references_effect`
  `gameplay_effect:P_anm_map01_zmdmachine+1_001_01`
  from `modelAnimatorDataEffectRefs[0]`.

A temp-regenerated alias-enriched report maps that effect ref to:

```text
asset_entity:StreamingAssets/anm_map01_zmdmachine_1_001_01
```

with:

- `lodModelCount=3`
- `materialCount=0`
- `textureCount=0`

Exported asset index checks found:

- 0 entries containing `int_system_spaceship_credit_shop`.
- 0 entries containing `spaceship_credit_shop`.
- 3 exact model entries containing `anm_map01_zmdmachine_1_001_01`:
  - `StreamingAssets/Mesh/S_anm_map01_zmdmachine_1_001_01_lod0_pADFC20AFB0A87DF6.obj`
  - `StreamingAssets/Mesh/S_anm_map01_zmdmachine_1_001_01_lod1_pC37F930709457DF6.obj`
  - `StreamingAssets/Mesh/S_anm_map01_zmdmachine_1_001_01_lod2_p4900A78EB5127DF6.obj`
- 3 plus-form entries containing `anm_map01_zmdmachine+1_001_01`:
  - `StreamingAssets/Animator/P_anm_map01_zmdmachine+1_001_01_p8A3D4C9DEE7D7A94.fbx`
  - `StreamingAssets/Mesh/S_anm_map01_zmdmachine+1_001_01_COL1_UM01_pCAE6D141C94A29F5.obj`
  - `StreamingAssets/Mesh/S_anm_map01_zmdmachine+1_001_01_COL1_UM02_p19A61230ED39BD9B.obj`

The graph has an exact effect-to-animator match:

- `effect_name_matches_export_base_asset`
  from `gameplay_effect:P_anm_map01_zmdmachine+1_001_01` to
  `StreamingAssets/Animator/P_anm_map01_zmdmachine+1_001_01_p8A3D4C9DEE7D7A94.fbx`
  with `asset_stem_pathid_suffix` evidence.
- Reverse `asset_matched_by_gameplay_effect` edge from the animator asset back
  to the gameplay effect.

The graph has two exported `anm_map01_zmdmachine` asset entities:

- `asset_entity:StreamingAssets/anm_map01_zmdmachine_1_001_01`
  - 3 LOD meshes.
  - 0 material relations.
  - 0 texture relations.
- `asset_entity:StreamingAssets/anm_map01_zmdmachine+1_001_02`
  - 2 LOD meshes.
  - 0 material relations.
  - 0 texture relations.

Nearby name-adjacent files can confuse interpretation:

- Collision meshes for `+1_001_01`:
  - `S_anm_map01_zmdmachine+1_001_01_COL1_UM01`
  - `S_anm_map01_zmdmachine+1_001_01_COL1_UM02`
- Sibling model family `anm_map01_zmdmachine+1_001_02`.
- Material/texture family `anm_map01_zmdmachine+1_004_01`:
  - `M_anm_map01_zmdmachine+1_004_01`
  - `T_anm_map01_zmdmachine+1_004_01_D`
  - `T_anm_map01_zmdmachine+1_004_01_NRO`

The `+1_004_01` material/texture family is real, but current graph/index
relations do not attach it to exact
`asset_entity:StreamingAssets/anm_map01_zmdmachine_1_001_01`.

## Interpretation

`int_system_spaceship_credit_shop` is a placed, system-style interactive with
both world-instance evidence and template evidence. It should not be treated as
runtime-only or template-only just because the older binding report only counted
compact `world_entity` edges.

The strongest renderable target is:

```text
asset_entity:StreamingAssets/anm_map01_zmdmachine_1_001_01
```

Confidence is stronger than the fake-robot ZMD-machine case in placement terms:

- There are two concrete world entity instances at the same coordinate.
- The interactive template has seven components and a trigger-zone component,
  consistent with a real system interaction.
- The controller references two ZMD-machine clips and a ZMD-machine effect.
- The effect has an exact exported animator FBX match.
- The normalized effect stem has an exact exported mesh entity with three LODs.

The confidence limit remains material coverage:

- No exact material or texture relation is represented for
  `anm_map01_zmdmachine_1_001_01`.
- Nearby `+1_004_01` material/texture assets are name-adjacent but not currently
  linked by graph evidence.
- Absence from generated indexes means "not recovered here", not proof the
  original Unity asset had no material assignment.

## Tooling Implication

The model binding candidate generator now records:

- `worldEntityUses`: compact `world_entity_uses_model` count.
- `worldEntityInstanceUses`: direct `world_entity_instance_uses_model` count.
- `placementUses`: combined placement count used for unbound-row status and
  CLI world/usage sorting.

This prevents placed interactives that only have instance-level registry edges
from being under-ranked or misread as having no world placement.

## Next Checks

- Refresh the ignored source-graph reports when a broader report rebuild is
  next useful, so `reports/source_graph/model_config_asset_binding_candidates.*`
  reflects the new placement fields.
- Inspect prefab or Animator metadata for
  `P_anm_map01_zmdmachine+1_001_01` to determine whether the `+1_004_01`
  material family is actually related or only a sibling visual family.
- Promote controller aliases only as a separate binding class until prefab or
  asset-map evidence proves a direct renderable binding.
