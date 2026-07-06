# Entity Assets Source Graph Query Recovery - 2026-07-06

## Context

The July 1 understanding report marks texture extraction as high confidence
but model/material semantics as only moderate. The source graph already links
exported asset entities to LOD model files, material JSON files, texture files,
model config rows, interactive templates, weapons, and selected gameplay
references. Before this note, inspecting one semantic renderable usually meant
combining `used-by`, generic `query`, model binding reports, and material edge
lookups manually.

## Change

`tools/endfield_source_graph.py` now supports:

```bat
python tools\endfield_source_graph.py entity-assets TERM
```

The command resolves asset-oriented seeds in this order:

- `asset_entity`
- `model_config_model`
- `model_prefab`
- `world_entity`
- `world_entity_instance`
- `interactive_template`

For an `asset_entity`, it returns direct evidence for:

- LOD models: `entity_has_lod_model`
- materials: `entity_uses_material`
- textures: `entity_uses_texture`
- model config and model-view controller bindings
- interactive template, weapon, MonoBehaviour, and gameplay asset bindings

It also follows direct material JSON assets one hop to material shader and
texture slot evidence such as `uses_shader_pathid`, `uses_texture_pathid`, and
PathID-to-export links when those edges exist in the graph.

The graph currently has two representations for material data: exported
material JSON `asset` nodes and semantic `material` nodes parsed from material
JSON. `entity-assets` derives semantic material names from material asset
filenames such as `M_actor_endminf_body_01_p8FCFD092D6518071.json`, matches
the corresponding `material` node, and follows its shader/texture PathID
evidence. This exposes a practical render chain without changing the graph
schema.

## Validation Examples

Actor part with model/material/texture evidence:

```bat
python tools\endfield_source_graph.py entity-assets actor_aglina_body_01 --limit 8
```

Expected evidence includes five LOD model rows, one material row, and texture
slot rows such as `_BaseMap`.

Interactive model binding:

```bat
python tools\endfield_source_graph.py entity-assets int_collection_common_postmodel --limit 8
```

Expected evidence includes the exported postmodel asset entity and its model
file. Cross-check with:

```bat
python tools\endfield_source_graph.py model-bindings --status strong_exact_graph_edge --term int_collection_common --limit 3
```

Character part with material slot evidence:

```bat
python tools\endfield_source_graph.py entity-assets actor_aglina_face_01 --limit 12
```

Expected evidence includes exported LODs plus material/texture slot bindings
when present in the current asset index.

Semantic material and shader PathID chain:

```bat
python tools\endfield_source_graph.py entity-assets StreamingAssets/actor_endminf_body_01 --limit 12
```

Expected evidence includes semantic material
`material:StreamingAssets:M_actor_endminf_body_01`, `uses_shader_pathid` to
`pathid:4484747192473637154`, and shader program evidence for
`HGRP/CharacterNPR_Skin`.

## Boundary

This query summarizes exported asset-index and source-graph evidence. It does
not prove original runtime material assignment, shader compatibility, animation
controller behavior, IK/facial layers, or full Unity renderer fidelity.
