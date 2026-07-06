# Material Usage Source Graph Query - 2026-07-06

## Scope

Added `material-usage` to `tools/endfield_source_graph.py` for compact lookup
of recovered material, texture, shader, PathID, exported asset, and renderable
asset-entity evidence.

The original understanding report calls models/materials moderate-confidence:
texture extraction is strong and material/texture relations exist, but semantic
entity-level reconstruction and renderer fidelity are still incomplete. This
query makes the existing material graph easier to inspect without claiming
runtime material variant selection.

## Query Behavior

Examples:

```bat
python tools\endfield_source_graph.py material-usage M_actor_aglina_body_01 --kind material --limit 14
python tools\endfield_source_graph.py material-usage M_actor_aglina_body_01_p47F6D19FCC054A29.json --kind asset --limit 14
python tools\endfield_source_graph.py material-usage 4484747192473637154 --kind unity_pathid --limit 12
python tools\endfield_source_graph.py material-usage actor_aglina_body_01 --kind asset_entity --limit 12
python tools\endfield_source_graph.py material-usage T_actor_aglina_body_01_D_p3964D919B12E7B43.png --kind asset --limit 12
```

The command can start from:

- semantic `material` nodes from Material JSON;
- exported material/texture `asset` rows;
- `asset_entity` renderable groups;
- `unity_pathid` texture or shader slots;
- `shader_program`, `shader`, or lab `texture` nodes.

For semantic material seeds, it links the material node to matching exported
material JSON assets such as
`StreamingAssets-materials/Material/M_actor_aglina_body_01_p47F6D19FCC054A29.json`.
For exported material assets, it attempts the reverse match back to the
semantic material node.

Returned groups include:

- `semanticMaterials`
- `materialAssets`
- `materials`
- `textures`
- `shaders`
- `entities`
- `pathidsAssets`

## Evidence Model

High-value edges include:

- `uses_shader_pathid`
- `uses_texture_pathid`
- `material_shader_pathid_resolves_unity_asset`
- `material_texture_pathid_resolves_unity_asset`
- `material_texture_pathid_exports_asset`
- `asset_export_used_by_material_texture_slot`
- `entity_uses_material`
- `material_used_by_asset_entity`
- `entity_uses_texture`
- `texture_used_by_asset_entity`
- `referenced_by_material`
- `shader_program_pathid`
- `shader_program_family`

Smoke checks showed:

- `M_actor_aglina_body_01` exposes shader PathID, `_BaseMap`,
  `_DiffRampMap`, `_ShadowLutTex`, matching exported material assets, and
  entity consumers.
- The exported material JSON asset resolves back to the semantic material and
  entity/material relationships.
- The shader PathID `4484747192473637154` surfaces shader-program and material
  slot references.
- `actor_aglina_body_01` surfaces material and texture consumers from the
  renderable entity group.
- `T_actor_aglina_body_01_D_p3964D919B12E7B43.png` surfaces material and entity
  references for a concrete exported texture.

## Interpretation

Treat output as source-graph evidence from exported asset indexes,
Material JSON, and AnimeStudio AssetMap PathID resolution. It can explain which
material JSON references which texture/shader slots and which renderable entity
groups reference the exported material or texture assets.

Do not treat this as proof of:

- runtime material variant selection;
- complete renderer state;
- HLSL decompilation correctness;
- texture color-space or sampler correctness;
- animation/controller-driven material swaps;
- every original AB loading warning being clean.

Use `material-usage` with `entity-assets`, `shader-usage`, and `used-by` for
deeper asset follow-up.

## Validation

Validated syntax and smoke lookups:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py material-usage --help
python tools\endfield_source_graph.py material-usage M_actor_aglina_body_01 --kind material --limit 14
python tools\endfield_source_graph.py material-usage M_actor_aglina_body_01_p47F6D19FCC054A29.json --kind asset --limit 14
python tools\endfield_source_graph.py material-usage 4484747192473637154 --kind unity_pathid --limit 12
python tools\endfield_source_graph.py material-usage actor_aglina_body_01 --kind asset_entity --limit 12
python tools\endfield_source_graph.py material-usage T_actor_aglina_body_01_D_p3964D919B12E7B43.png --kind asset --limit 12
```
