# Asset Entity Material/Texture Reverse Source Graph Recovery - 2026-07-03

## Context

The WebUI asset index already builds aggregate `asset_entity` nodes from model
LOD groups and attaches their material and texture dependencies through
`entity_uses_material` and `entity_uses_texture`. Low-level asset relation
edges also carry broad PathID-style `referenced_by_material` and
`referenced_by_model` links, but texture- or material-centered queries could
not directly enumerate the reconstructed asset entities that use them.

## Finding

`tools/endfield_source_graph.py` now emits reverse aggregate asset-entity edges:

- `material_used_by_asset_entity`
- `texture_used_by_asset_entity`

These reverse edges are intentionally limited to curated `asset_entity`
material/texture relationships. They do not duplicate the much larger raw
`uses_texture` relation set, which already has lower-level reference evidence.
The reverse edges preserve the same material/texture evidence and relation
payload as the forward aggregate edges.

## Validation

Focused temporary graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DB: `tmp/asset_entity_reverse.sqlite`

Asset-only ingest counts:

- `entity_uses_material`: 1,962
- `material_used_by_asset_entity`: 1,962
- `entity_uses_texture`: 8,581
- `texture_used_by_asset_entity`: 8,581

Sample reverse edges showed material JSON assets such as
`Persistent-materials/Material/M_item_cine_musicbox_01_*.json` pointing back to
the corresponding `asset_entity:Persistent/item_cine_musicbox_01` owner with
the original material evidence and relation payload.
