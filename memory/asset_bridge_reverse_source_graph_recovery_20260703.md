# Asset Bridge Reverse Source Graph Recovery - 2026-07-03

## Context

The source graph already connected gameplay entries, item ids, exported assets,
asset entities, gameplay effects, and visual token matches in the forward
direction. Asset-centered queries still had gaps when starting from an exported
asset or reconstructed asset entity and asking which gameplay object, item, or
effect matched it.

## Finding

`tools/endfield_source_graph.py` now emits reverse edges for asset bridge
relationships:

- `asset_used_by_gameplay`
- `asset_entity_used_by_gameplay`
- `asset_matched_by_gameplay_effect`
- `asset_used_as_icon_by`
- `visual_asset_used_by`
- `asset_matched_by_visual_token`

The reverse edges preserve the same source, evidence, and payloads as their
forward matches, including token, asset stem/path, normalized base, model path,
asset entity, and PathID suffix values where applicable.

## Validation

Focused temporary graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DBs:

- `tmp/asset_bridge_reverse.sqlite`
- `tmp/visual_asset_reverse_structured.sqlite`

Focused ingest methods:

- `ingest_assets`
- `ingest_gameplay`
- `ingest_decoded_config_semantics`
- `link_gameplay_effect_export_assets`
- `link_visual_token_export_assets`

Counts:

- `has_gameplay_asset`: 7,960 / `asset_used_by_gameplay`: 7,960
- `has_gameplay_asset_entity`: 132 / `asset_entity_used_by_gameplay`: 132
- `effect_name_matches_export_base_asset`: 441 / `asset_matched_by_gameplay_effect`: 441
- `uses_icon_asset`: 0 / `asset_used_as_icon_by`: 0 in this focused build
- `uses_visual_asset`: 0 / `visual_asset_used_by`: 0 in this focused build
- `visual_token_matches_export_base_asset`: 0 / `asset_matched_by_visual_token`: 0 in this focused build

The focused asset/gameplay build did not include the structured nodes that
carry icon/background payload fields, so a second structured visual-token build
was run with `ingest_assets`, structured semantic ingesters, and
`link_visual_token_export_assets`:

- `uses_icon_asset`: 31,300 / `asset_used_as_icon_by`: 31,300
- `uses_visual_asset`: 992 / `visual_asset_used_by`: 992

Sample reverse rows showed weapon asset entities such as
`asset_entity:StreamingAssets/wpn_claym_0008_01` pointing back to
`weapon:wpn_claym_0008`, preserving `modelPath`, token, model base, and asset
entity payloads. The structured visual-token build showed item/blueprint
sprites and domain buyer icons pointing back to their item and buyer nodes.
