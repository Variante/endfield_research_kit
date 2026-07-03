# Asset Entity LOD Model Reverse Source Graph Recovery - 2026-07-03

## Context

Aggregate `asset_entity` nodes group exported model LOD files with their
materials and textures. Material and texture asset queries now have reverse
links back to the reconstructed asset entity, but model LOD file queries still
only traversed from entity to model through `entity_has_lod_model`.

## Finding

`tools/endfield_source_graph.py` now emits:

- `model_lod_of_asset_entity`

The reverse edge points from each exported model asset file back to its
aggregate `asset_entity`, preserving the original LOD evidence stem and relation
payload including `rel` and `pid` where available.

## Validation

Focused temporary graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DB: `tmp/asset_entity_lod_reverse.sqlite`

Asset-only ingest counts:

- `entity_has_lod_model`: 30,830
- `model_lod_of_asset_entity`: 30,830

Sample reverse edges showed Persistent model assets such as
`Persistent/Mesh/S_actor_endminf_body_01_lod0_*.obj` pointing back to
`asset_entity:Persistent/actor_endminf_body_01` with the original PathID payload.
