# Material PathID Asset Source Graph Recovery - 2026-07-02

## Slice

Added source-graph links that resolve Material JSON texture slots through
AnimeStudio AssetMaps and back to exported WebUI Texture2D assets.

New or expanded link behavior:

- `asset_pid_signed_path_id()` normalizes WebUI asset `pid` suffixes into signed
  Unity PathID values.
- WebUI asset ingest now indexes exported assets by exact signed PathID and by
  export base stem without the `_p<16 hex>` suffix.
- AnimeStudio AssetMap ingest now links `unity_asset -> asset` as `exported_as`
  by exact PathID first, with exact stem and base-stem fallback, source-limited
  to the same `StreamingAssets` or `Persistent` root.
- Material texture PathID references now emit:
  - `material_texture_pathid_resolves_unity_asset`
  - `unity_asset_used_by_material_texture_slot`
  - `material_texture_pathid_exports_asset`
  - `asset_export_used_by_material_texture_slot`
- `asset_usage()` includes the new material texture-slot edge kinds.

## Validation

Compile and whitespace checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Both passed.

A full graph build with real AssetMaps was attempted, but the AssetMap-enabled
build exceeded a 15 minute command timeout before completion. The active graph
build processes were stopped. This is a validation-runtime limit, not a compile
or sampled-data failure.

Sampled real-data validation used five real `StreamingAssets` AssetMap entries
referenced by actor Material JSON:

- `T_actor_aglina_body_01_D`, PathID `4135669062202981187`
- `T_actor_common_face_01_RD`, PathID `5848563174712869001`
- `T_actor_common_femaleskincolor03_lut_D`, PathID `2974746277297921454`
- `T_actor_aglina_cloth_01_D`, PathID `-8686072464031701625`
- `T_actor_aglina_cloth_01_N`, PathID `-9069961497623758259`

The sampled minimal graph command ingested WebUI assets, Material JSON, the
sampled AssetMap, and the new link step into
`tmp\material_pathid_sample.sqlite`.

Resulting edge counts:

- `uses_texture_pathid`: `3111`
- `resolves_to_unity_asset`: `5`
- `exported_as`: `5`
- `material_texture_pathid_resolves_unity_asset`: `104`
- `unity_asset_used_by_material_texture_slot`: `104`
- `material_texture_pathid_exports_asset`: `104`
- `asset_export_used_by_material_texture_slot`: `104`

Representative sample:

- `material:StreamingAssets:M_actor_aglina_body_01` ->
  `asset:StreamingAssets/Texture2D/T_actor_aglina_body_01_D_p3964D919B12E7B43.png`
  as `material_texture_pathid_exports_asset`, evidence `_BaseMap`, with
  `pathidNode` `unity_pathid:4135669062202981187`.
- The reverse query helper now reports the same relationship from the exported
  Texture2D asset through `asset_export_used_by_material_texture_slot`.

## Notes

This closes a practical character/material recovery gap: exported texture files
with `_p<16 hex>` suffixes can now be traced back to the Material texture slot
and Unity AssetMap PathID that referenced them. That makes asset-centric
queries useful for model/material inspection without manually comparing PathID
suffixes, Material JSON, and AssetMap rows.

Full real-AssetMap build counts are still pending because the AssetMap-enabled
source-graph build needs a longer validation window than the normal quick graph
build.
