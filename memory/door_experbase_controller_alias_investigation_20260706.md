# Door Experbase Controller Alias Investigation - 2026-07-06

## Question

The controller-alias census identified `int_door_experbase_v2_postmodel` as an
unresolved model binding with a clean alias to
`interactive_organdoor_1_001_01`. This pass checks whether that alias is a
useful renderable recovery clue or just a loose animation/effect name.

## Evidence

Model binding query:

```bat
python tools\endfield_source_graph.py model-bindings --term int_door_experbase --sort usage --limit 20
```

The normal report artifact has not yet been refreshed with
`controllerAliasEntities`, but the base rows are:

- `int_door_experbase_v2_postmodel`
  - Status: `no_exported_renderable_candidate`
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_door_experbase_v2_postmodel.prefab`
  - `worldEntityUses=0`
  - `interactiveTemplateUses=2`
  - No direct or candidate exported asset entity from model id or prefab stem.
- `int_door_experbase_v2_0d8_postmodel`
  - Status: `runtime_only_or_unreferenced`
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_door_experbase_v2_0d8_postmodel.prefab`
  - No direct or candidate exported asset entity from model id or prefab stem.

Direct graph edge counts:

- `int_door_experbase_v2_postmodel`
  - 2 `interactive_template_uses_model` links.
  - 1 `model_view_state_controller_uses_model` link.
  - 1 `model_config_has_radius` link.
  - 1 `model_config_uses_prefab` link.
- `int_door_experbase_v2_0d8_postmodel`
  - 1 `model_view_state_controller_uses_model` link.
  - 1 `model_config_has_radius` link.
  - 1 `model_config_uses_prefab` link.

The primary door model is used by both copies of the common door template:

- `interactive_template_data:StreamingAssets:int_door_common_v2`
- `interactive_template_data:Persistent:int_door_common_v2`

Both edges use `componentModelData.modelId` evidence.

The decoded common door template summary is semantically rich:

- `name=int_door_common_v2`
- `objectType=int_door_common_v2`
- `bornTags=1`
- `Category/Interactive/Door`
- `components=7`
- `firstComponent=Core_InteractiveRootComponentData`
- `modelComponent=int_door_experbase_v2_postmodel`
- `nextComponent=Core_InteractiveDoorCommonComponentData:1`
- property keys include `destroy_self`, `dynamic_entity_id`, and
  `use_dynamic_res`
- audio links include `au_int_door_medium_close` and
  `au_int_door_medium_open`
- component types include:
  - `View_InteractiveModelComponentData`
  - `Core_InteractiveDoorCommonComponentData`
  - `Core_InteractiveAudioData`
  - `Core_InteractiveCommonPerformComponentData`
  - `Core_InteractiveDynamicAINavComponentData`

The temp-regenerated alias-enriched binding report shows the same controller
alias for both model ids:

- `A_interactive_organdoor+1_001_01_closeidle_01`
- `A_interactive_organdoor+1_001_01_open_01`
- `A_interactive_organdoor+1_001_01_openidle_01`
- `A_interactive_organdoor+1_001_01_close_01`
- `P_interactive_organdoor+1_001_01`

All five map to:

```text
asset_entity:StreamingAssets/interactive_organdoor_1_001_01
```

The model-view controller nodes confirm the same pattern:

- `model_view_state_controller:int_door_experbase_v2_postmodel`
- `model_view_state_controller:int_door_experbase_v2_0d8_postmodel`

Both are defined by Persistent and StreamingAssets
`Interactive/ModelViewStateControllerData/*.json` files. Their decoded samples
report 4 clip infos, 1 effect id, 1 model animator data entry,
`preTickAnimator=false`, clips beginning with
`A_interactive_organdoor+1_001_01_*`, effects including
`P_interactive_organdoor_idle`, and animator strings such as `irondoor`,
`root`, `off_idle`, `state`, `off_to_on`, `on_idle`, and `on_to_off`.

Exported asset checks:

- `webui/data/assets/index.json` has 0 entries for `int_door_experbase` or
  `door_experbase`.
- It has 11 `interactive_organdoor` / `organdoor` entries:
  - Mesh LODs for `S_interactive_organdoor_1_001_01_lod0`,
    `lod1`, and `lod2`.
  - A collider mesh for `S_interactive_organdoor_1_001_01_Collider_IK`.
  - A collider mesh for `S_interactive_organdoor_1_001_02_Collider_IK`.
  - Texture exports for `T_interactive_organdoor+1_001_01_D`,
    `_E`, `_MRO`, and `_N`.
  - Material JSON:
    `M_interactive_organdoor+1_001_01_p8B217C88B3577E43.json`.
  - Animator override JSON:
    `P_interactive_organdoory_p8A4A5B6047B31E84.json`.
- The source graph `entity-assets` view for
  `interactive_organdoor_1_001_01` reports 3 LOD model edges. Its current
  entity summary has `materialCount=0` and `textureCount=0`, so the material
  and texture entries visible in the flat asset index are not yet attached to
  that asset entity by semantic relation.

## Interpretation

`int_door_experbase_v2_postmodel` is a real gameplay door model id, not a
placeholder. The common door template uses it directly, attaches door-specific
components, links door open/close audio, and assigns category tag
`Category/Interactive/Door`.

The exported renderable is not present under the `int_door_experbase` stem.
However, the model-view controller provides strong alias evidence to the
`interactive_organdoor_1_001_01` exported asset family. The `_0d8` model is
weaker from a gameplay-use standpoint, but it shares the same controller alias
and likely represents a variant or alternate state of the same door visual
family.

This is a better recovery candidate than a generic name search because the
alias comes from decoded controller clip/effect references. It should still
remain an alias candidate until prefab or AnimeStudio map evidence confirms the
renderable relationship.

## Next Checks

- Inspect prefab or AnimeStudio map data for
  `int_door_experbase_v2_postmodel` and `_0d8` to verify whether they reference
  `interactive_organdoor_1_001_01` meshes, materials, or animation controller
  assets.
- Improve asset-entity grouping so `interactive_organdoor_1_001_01` can surface
  the matching `M_interactive_organdoor+1_001_01` material and
  `T_interactive_organdoor+1_001_01_*` textures, not only mesh LODs.
- Compare `int_door_common_v2` against other door templates to see whether
  organ-door visual aliases are a general door-family pattern or specific to
  experiment-base doors.
