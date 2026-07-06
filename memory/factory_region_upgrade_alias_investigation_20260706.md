# Factory Region Upgrade Alias Investigation - 2026-07-06

## Question

The controller-alias census identified
`int_system_fac_region_upgrade_postmodel` as an unresolved model binding with
an alias to `anm_fac_upgradebot_1_001_01`. This pass checks what gameplay
system it belongs to and whether the upgradebot asset family is a plausible
visual recovery target.

## Evidence

Model binding query:

```bat
python tools\endfield_source_graph.py model-bindings --term int_system_fac_region_upgrade --sort usage --limit 20
```

Rows:

- `int_system_fac_region_upgrade_postmodel`
  - Status: `no_exported_renderable_candidate`
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_system_fac_region_upgrade_postmodel.prefab`
  - `interactiveTemplateUses=2`
  - `worldEntityUses=0`
  - No direct or candidate exported asset entity from model id or prefab stem.
- `int_system_fac_region_upgrade_postmode`
  - Status: `runtime_only_or_unreferenced`
  - No radius and no template/world/controller evidence in the current graph.
  - The missing final `l` in `postmode` suggests this may be a typo or dead
    config row.

Direct graph edge counts for `int_system_fac_region_upgrade_postmodel`:

- 2 `interactive_template_uses_model` links.
- 1 `model_view_state_controller_uses_model` link.
- 1 `model_config_has_radius` link.
- 1 `model_config_uses_prefab` link.

The model is used by both copies of the same interactive template:

- `interactive_template_data:StreamingAssets:int_system_fac_region_upgrade`
- `interactive_template_data:Persistent:int_system_fac_region_upgrade`

Both edges use `componentModelData.modelId` evidence.

The decoded template summary shows this is a system/factory-style clickable
interactive:

- `name=int_system_fac_region_upgrade`
- `objectType=int_system_fac_region_upgrade`
- `Category/Interactive/System`
- `components=7`
- `firstComponent=Core_InteractiveRootComponentData`
- `modelComponent=int_system_fac_region_upgrade_postmodel`
- `nextComponent=Core_ClickTriggerComponentForIntData`
- component types include:
  - `View_InteractiveModelComponentData`
  - `Core_BaseControllerData`
  - `Core_ClickTriggerComponentForIntData`

The temp-regenerated alias-enriched binding report maps controller refs to:

```text
asset_entity:StreamingAssets/anm_fac_upgradebot_1_001_01
```

Controller alias refs:

- `A_anm_fac_upgradebot+1_001_01`
- `P_anm_fac_upgradebot+1_001_01`

The model-view state controller confirms the same pattern:

- Node: `model_view_state_controller:int_system_fac_region_upgrade_postmodel`
- Defined by Persistent and StreamingAssets
  `Interactive/ModelViewStateControllerData/int_system_fac_region_upgrade_postmodel.json`
- Decoded summary:
  - `modelId=int_system_fac_region_upgrade_postmodel`
  - `clipInfos=1`
  - `effects=3`
  - `modelAnimatorDatas=2`
  - `preTickAnimator=false`
  - clip: `A_anm_fac_upgradebot+1_001_01`
  - effects:
    - `P_fxint_l_interactive_robot_tip_01`
    - `P_fxint_l_interactive_robot_text_01`
    - `P_fxint_l_interactive_robot_exclamation_01`
  - animator strings include `base`, `Idle`, `effect`, `LevelUp`,
    `visible`, `Visible`, `IsVisible`, and `Hide`
  - animator effect refs additionally include
    `P_anm_fac_upgradebot+1_001_01_COL1`,
    `P_anm_fac_upgradebot+1_001_02_COL1`, and
    `P_anm_fac_upgradebot+1_001_01`

Exported asset checks:

- `webui/data/assets/index.json` has 0 entries for
  `int_system_fac_region_upgrade` or `fac_region_upgrade`.
- The same index has 27 `fac_upgradebot` / `upgradebot` entries.
- Renderable/model assets include:
  - `StreamingAssets/Animator/P_anm_fac_upgradebot+1_001_01_p1CB78DB4F1D4C490.fbx`
  - `StreamingAssets/Mesh/S_anm_fac_upgradebot_1_001_01_lod0_pDD2DA57B7CCBC7D5.obj`
  - `StreamingAssets/Mesh/S_anm_fac_upgradebot_1_001_01_lod1_pAA0F83602AF2C7D5.obj`
  - `StreamingAssets/Mesh/S_anm_fac_upgradebot_1_001_01_lod2_pC7BE3E4ACB63C7D5.obj`
  - `StreamingAssets/Mesh/S_anm_fac_upgradebot_1_001_01_lod3_p07A43FBAF4D2C7D5.obj`
  - additional `S_anm_fac_upgradebot+1_001_02_*` mesh assets.
- UI assets include `btn_fac_upgradebot_icon` sprite/texture files.
- Material and texture files include:
  - `M_anm_fac_upgradebot+1_001_01_p500FFDA1C865E999.json`
  - `M_anm_fac_upgradebot+1_001_02_p4C64F6591B075F46.json`
  - `M_anm_fac_upgradebot+1_001_03_pF3EF05F4AEE1233C.json`
  - `T_anm_fac_upgradebot+1_001_01_D`
  - `T_anm_fac_upgradebot+1_001_01_MRO`
  - `T_anm_fac_upgradebot+1_001_01_N`
  - `T_anm_fac_upgradebot+1_001_02_D/E/MRO/N`

The current source graph `entity-assets anm_fac_upgradebot_1_001_01` view
reports 4 mesh LODs but `materialCount=0` and `textureCount=0`, because the
normal graph has not yet been refreshed after the filename-base fallback
change.

Targeted validation of the new filename-base fallback against
`webui/data/assets/index.json` showed:

```text
anm_fac_upgradebot_1_001_01: group=True, material=1, textures=3
anm_fac_upgradebot_1_001_02: group=False, material=0, textures=0
```

This means a future source-graph refresh should attach the `1_001_01`
material and three textures to `asset_entity:StreamingAssets/anm_fac_upgradebot_1_001_01`.
The `1_001_02` mesh/material family still needs separate handling because its
mesh names use plus-form stems in some files.

## Interpretation

`int_system_fac_region_upgrade_postmodel` is a real system interactive, likely
the factory region upgrade clickable object or presentation actor. It is not
placed through world entity rows in the current graph, but both StreamingAssets
and Persistent template data use it as the view model for
`int_system_fac_region_upgrade`.

The renderable is not exported under the gameplay id. The controller points to
`anm_fac_upgradebot+1_001_01` clip/effect refs, and the asset index contains a
substantial `anm_fac_upgradebot` visual package. This is a strong alias
candidate, especially because the controller animator strings include
`LevelUp`, `Visible`, and `Hide`, which match an upgrade presentation role.

As with door and switch aliases, this should stay an alias candidate until
prefab or AnimeStudio map evidence verifies the binding.

## Next Checks

- Inspect prefab or AnimeStudio map data for
  `int_system_fac_region_upgrade_postmodel` to confirm whether it references
  `anm_fac_upgradebot_1_001_01`.
- After a graph refresh, verify that `entity-assets anm_fac_upgradebot_1_001_01`
  reports the expected material and texture counts from the filename fallback.
- Investigate the `S_anm_fac_upgradebot+1_001_02_*` mesh/material family
  separately; it may be a second state or companion component for the same
  upgradebot visual.
