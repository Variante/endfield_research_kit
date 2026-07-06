# Ore Cluster Model Binding Investigation - 2026-07-06

## Question

The model binding triage showed unresolved exported-renderable bindings for
ore-cluster interactives. This pass checks whether those rows are false
positives, alternate asset names, or real gaps between gameplay model config
and exported renderable assets.

## Evidence

Command:

```bat
python tools\endfield_source_graph.py model-bindings --term ore_cluster --limit 30
```

Findings:

- `int_doodad_ore_cluster_metal_sp` resolves cleanly with
  `strong_exact_graph_edge`.
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_ore_cluster_metal_sp_postmodel.prefab`
  - Direct graph asset:
    `asset_entity:StreamingAssets/int_doodad_ore_cluster_metal_sp_postmodel`
  - Exported entity data: one LOD model, zero material and texture links in the
    current graph asset entity summary.
- `int_doodad_ore_cluster_iron` is semantically used but has no exported
  renderable candidate.
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_ore_cluster_iron_postmodel.prefab`
  - `worldEntityUses=92`
  - Incoming edge counts include 92 `world_entity_uses_model` and 390
    `world_entity_instance_uses_model` links.
  - Sample world entity edges include `world_entity:2800060365` through
    `world_entity:2800060446`, all sourced from `webui/game_data` with
    `detailId` evidence.
- `int_doodad_ore_cluster_originium` is semantically used but has no exported
  renderable candidate.
  - Prefab path:
    `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_ore_cluster_originium_postmodel.prefab`
  - `worldEntityUses=52`
  - `interactiveTemplateUses=2`
  - Incoming edge counts include 52 `world_entity_uses_model`, 582
    `world_entity_instance_uses_model`, and 2 `interactive_template_uses_model`
    links.
  - The interactive-template links are
    `interactive_template_data:StreamingAssets:int_weekraid_mine` and
    `interactive_template_data:Persistent:int_weekraid_mine`, both with
    `componentModelData.modelId` evidence.
- `int_doodad_ore_cluster_copper_postmodel` has model/radius/prefab config, but
  no world entity, world instance, interactive template, or exported asset
  candidate in this graph pass.
- `int_doodad_ore_cluster_quartz` has model/radius/prefab config and 141
  `world_entity_instance_uses_model` links, but no exported asset candidate.

The graph asset entity table has exactly one `ore_cluster` renderable family
entry:

```text
asset_entity:StreamingAssets/int_doodad_ore_cluster_metal_sp_postmodel
```

The WebUI asset index agrees. Searching `webui/data/assets/index.json` by
family terms found:

- 1 `int_doodad_ore_cluster*` model entry:
  `StreamingAssets/Animator/int_doodad_ore_cluster_metal_sp_postmodel_pD6A4F3AB513B04B0.fbx`
- 6 `M_fx_ore_cluster_hit*` material JSON entries.
- 0 `originium_postmodel`, `copper_postmodel`, or `quartz_postmodel` entries.
- 1 `iron_postmodel` entry, but it is
  `StreamingAssets/Animator/int_forge_iron_postmodel_p17A416D628D212D2.fbx`,
  not an ore-cluster asset.

## Interpretation

The unresolved iron, originium, and quartz rows are not just dead config names.
Iron and originium are high-confidence gameplay model references because they
are used by world entities and world entity instances. Originium is additionally
used by the `int_weekraid_mine` interactive template in both StreamingAssets
and Persistent data. Quartz is weaker than iron/originium because it currently
appears only through world entity instances, but it is still not purely
unreferenced.

The current exported renderable map only exposes the special metal ore-cluster
variant. No obvious alternate exported renderable stem exists for
`int_doodad_ore_cluster_iron_postmodel`,
`int_doodad_ore_cluster_originium_postmodel`,
`int_doodad_ore_cluster_copper_postmodel`, or
`int_doodad_ore_cluster_quartz_postmodel`.

Most likely explanations:

- The missing variants are real extraction/indexing gaps for prefab-bound
  renderables.
- The variants reuse a shared mesh under a non-obvious name that the current
  candidate matcher cannot infer from model id or prefab path alone.
- Some gameplay rows are runtime variant/controllers whose visual selection is
  swapped through another table or prefab child relationship not yet represented
  in the source graph.

## Next Checks

- Inspect AnimeStudio map exports or raw prefab references for the four missing
  prefab stems to determine whether GUID/path aliases point to a shared mesh.
- Compare `ModelConfig`, `WorldEntity`, and `WorldEntityInstance` rows for the
  iron/originium/quartz detail ids to see whether a separate visual override
  field is present.
- If a stable alias source is found, extend the model binding report to emit
  the alias edge separately instead of treating these as plain
  `no_exported_renderable_candidate` rows.
