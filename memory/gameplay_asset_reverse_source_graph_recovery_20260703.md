# Gameplay Asset Reverse Source Graph Recovery - 2026-07-03

## Context

The graph already connected gameplay/effect/visual nodes to exported assets and
asset entities, but asset-centered queries could not directly enumerate many of
those consumers.

## Change

`tools/endfield_source_graph.py` now emits reverse asset lookup edges for:

- `asset_matched_by_gameplay_effect`
- `asset_used_as_icon_by`
- `visual_asset_used_by`
- `asset_matched_by_visual_token`
- `asset_used_by_gameplay`
- `asset_entity_used_by_gameplay`

The reverse rows are emitted next to the existing forward rows and keep the same
evidence plus token/path payloads. Visual-token reverse rows also record the
original forward edge kind as `forwardKind`.

## Validation

Syntax:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DBs:

- `tmp/gameplay_asset_reverse_minimal.sqlite`
- `tmp/visual_asset_reverse_structured.sqlite`

Gameplay/effect subset:

- `has_gameplay_asset`: 7,960 / reverse 7,960
- `has_gameplay_asset_entity`: 132 / reverse 132
- `effect_name_matches_export_base_asset`: 441 / reverse 441

Structured visual-token subset:

- `uses_icon_asset`: 31,300 / reverse 31,300
- `uses_visual_asset`: 992 / reverse 992

The structured subset intentionally skipped decoded-config/gameplay nodes, so
its icon count is lower than the full quick graph's previously observed 34,248
forward `uses_icon_asset` rows. Within the exercised subset, forward and
reverse counts matched exactly.

Sample reverse rows showed weapon model asset entities pointing back to weapon
nodes, item/blueprint sprites pointing back to item nodes, and domain buyer
icons pointing back to buyer nodes.
