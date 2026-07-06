# Doodad Flower Model Binding Investigation - 2026-07-06

## Question

After the ore-cluster pass, the next high-use
`no_exported_renderable_candidate` family is `int_doodad_flower_*`. This pass
checks whether those model ids are gameplay-real environmental interactives,
factory/seed item references, or simply missing exported renderables.

## Evidence

New triage command shape:

```bat
python tools\endfield_source_graph.py model-bindings --status no_exported_renderable_candidate --sort usage --limit 8
```

This ranks unresolved model-config rows after filtering instead of relying on
the report's original order. It places these rows directly after the already
investigated ore-cluster rows:

- `int_doodad_flower_1`: 31 world entity uses.
- `int_doodad_flower_2`: 23 world entity uses.
- `int_doodad_flower_3`: 5 world entity uses.

Family query:

```bat
python tools\endfield_source_graph.py model-bindings --term int_doodad_flower --sort world --limit 8
```

Findings:

- `int_doodad_flower_1`
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_flower_1_postmodel.prefab`
  - `worldEntityUses=31`
  - Edge counts include 31 `world_entity_uses_model` and 253
    `world_entity_instance_uses_model` links.
  - Sample world entity ids include `world_entity:2800060241` through
    `world_entity:2800060248`, all with `detailId` evidence.
- `int_doodad_flower_2`
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_flower_2_postmodel.prefab`
  - `worldEntityUses=23`
  - Edge counts include 23 `world_entity_uses_model` and 213
    `world_entity_instance_uses_model` links.
  - Sample world entity ids include `world_entity:2800060272` through
    `world_entity:2800060279`, all with `detailId` evidence.
- `int_doodad_flower_3`
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_flower_3_postmodel.prefab`
  - `worldEntityUses=5`
  - Edge counts include 5 `world_entity_uses_model` and 45
    `world_entity_instance_uses_model` links.
  - Sample world entity ids include `world_entity:2800060353` through
    `world_entity:2800060357`, all with `detailId` evidence.
- `int_doodad_flower_scion`, `int_doodad_flower_spc_1_postmodel`, and
  `int_doodad_flower_spc_2_postmodel` appear in model config, but are currently
  `runtime_only_or_unreferenced` in this binding report.

Cross-domain graph search adds semantic context. Searching for
`int_doodad_flower` finds:

- `asset_ref:int_doodad_flower_1_postmodel`,
  `asset_ref:int_doodad_flower_2_postmodel`,
  `asset_ref:int_doodad_flower_3_postmodel`, and
  `asset_ref:int_doodad_flower_scion_postmodel` from `FactorySeedItemTable`.
- `audio_collection:int_doodad_flower_1`,
  `audio_collection:int_doodad_flower_2`,
  `audio_collection:int_doodad_flower_3`, and
  `audio_collection:int_doodad_flower_story_1`.
- `interactive_object` nodes for flower, once-only flower, special flower, and
  story flower variants.
- `level_data_param` nodes for flower and special flower variants.

BBFlower has a related but separate footprint:

- `int_doodad_bbflower_1` is also
  `no_exported_renderable_candidate`.
- It has 3 `world_entity_uses_model` links and 98
  `world_entity_instance_uses_model` links.
- It has a `FactorySeedItemTable` asset ref, an audio collection, an
  interactive object, and a level-data param.
- The WebUI asset index contains BBFlower item/icon/seed/powder textures, but
  no `int_doodad_bbflower_1_postmodel` model entry.

Exported asset checks:

- `webui/data/assets/index.json` has 0 entries for `int_doodad_flower`,
  `doodad_flower`, `flower_1_postmodel`, `flower_2_postmodel`, or
  `flower_3_postmodel`.
- A sidecar read-only JSON pass over
  `reports/source_graph/model_config_asset_binding_candidates.json` and
  `webui/data/assets/index.json` independently ranked the top non-ore
  unresolved rows as `int_doodad_flower_1`, `int_doodad_flower_2`,
  `int_switch_union_v2`, `int_doodad_placeholder_postmodel`, and
  `int_empty_postmodel`, and found no exact exported assets for the flower,
  `switch_union`, placeholder, or empty-postmodel stems.
- The source-graph `asset_entity` table has 17 generic `flower` entities, such
  as `bush_map02_cityflower+1_001_01`,
  `grass_hsflower+2_001_01`, and NPC flower props, but no direct
  `int_doodad_flower_*` entity.
- BBFlower texture/icon entries exist in StreamingAssets and Persistent, but
  those are item/UI assets, not the missing world doodad postmodel.

## Interpretation

The `int_doodad_flower_*` rows are gameplay-real world interactives, not dead
model ids. The strong world entity and world instance counts prove that they are
used as placed world detail models. The `FactorySeedItemTable` asset refs and
audio collections show that this family also participates in collection,
seed/factory, and interaction semantics.

The current exported renderable map does not recover the flower postmodel
entities. Unlike ore clusters, this family has no obvious resolved sibling
postmodel in the current `asset_entity` graph. The generic environmental flower
meshes and BBFlower item textures are semantically nearby but are not safe
substitutes for the missing `int_doodad_flower_*_postmodel` bindings.

Most likely explanations:

- The flower world postmodels are present under unrelated vegetation mesh names
  and need prefab/GUID-level alias recovery.
- The current asset-entity grouping loses these prefab-level entities because
  only lower-level mesh/material exports survive with generic environment names.
- Factory/seed/item references preserve the semantic id even when the renderer
  asset is hidden behind a separate prefab child or pooled vegetation system.

## Next Checks

- Inspect AnimeStudio map exports for
  `int_doodad_flower_1_postmodel`,
  `int_doodad_flower_2_postmodel`, and
  `int_doodad_flower_3_postmodel` to look for GUID/path aliases to generic
  `bush_*`, `grass_*`, or `plant_*` meshes.
- Add graph edges from `FactorySeedItemTable` asset refs to model-config rows
  where the `*_postmodel` token matches, so the query output can explain this
  table bridge directly.
- Compare the `level_data_param` and `interactive_object` rows for flower,
  story flower, and special flower variants to identify whether they share a
  common template or runtime collection behavior.
