# Material Shader PathID Source Graph Recovery - 2026-07-03

## Context

Material JSON ingest already records shader references as `uses_shader_pathid`
edges from `material` nodes to `unity_pathid` nodes. Texture PathIDs already
had a post-ingest resolver that joins through AnimeStudio asset maps back to
`unity_asset` nodes, but shader PathIDs did not. As a result, material shader
slots stayed at raw PathID evidence even when the asset map had the exact Unity
asset entry.

The important guard is source root: PathIDs can be reused between
`StreamingAssets` and `Persistent`, so material PathID resolution must only
connect to Unity assets whose `source` matches the material source.

## Change

`tools/endfield_source_graph.py` now resolves material shader PathIDs in
`link_material_pathid_unity_assets()` before the existing texture PathID pass.

New edges:

- `material_shader_pathid_resolves_unity_asset`
- `unity_asset_used_by_material_shader_slot`
- `shader_used_by_material_slot` when the resolved Unity asset type is
  `Shader`

The new edge kinds are also included in the asset usage lookup sets so asset
queries can surface shader-slot usage alongside texture-slot usage.

## Validation

Static checks passed:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

A focused fixture created two material roots sharing PathID `123`, plus a
non-shader PathID `456`, and called `link_material_pathid_unity_assets()`.
Results:

| Edge kind | Count |
|---|---:|
| `material_shader_pathid_resolves_unity_asset` | 3 |
| `unity_asset_used_by_material_shader_slot` | 3 |
| `shader_used_by_material_slot` | 2 |

The fixture confirmed:

- `StreamingAssets:MatA` linked to `StreamingAssets:123`.
- `Persistent:MatA` linked to `Persistent:123`.
- The non-shader asset still received the general shader PathID resolution
  edge but not the shader-typed reverse edge.
- Cross-root bad joins were `0`.

## Notes

The resolver intentionally mirrors the texture PathID resolver but does not
create exported-asset edges, because shader assets are not expected to have the
same WebUI-facing exported file relationship as texture slots.
