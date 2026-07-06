# Character Recovery Candidate Report Recovery - 2026-07-06

## Summary

Refined `emit_character_recovery_candidates()` in
`tools/endfield_source_graph.py` so the generated source-graph follow-up report
uses renderable `asset_entity` evidence and handles `actor_lod_<actor>` asset
tokens as the real actor instead of grouping them under a fake `lod` actor.

This is a source-graph report improvement only. It does not change WebUI
output, Unity character lab manifests, model extraction, asset extraction, or
any recovered character assets.

## Problem

The older `reports/source_graph/character_recovery_candidates.json` was useful
but incomplete:

- It grouped `M_actor_lod_aglina_*` and similar material assets as actor
  `lod`.
- It ignored `asset_entity` nodes, even though those are the graph's curated
  renderable LOD-model groupings.
- It only emitted JSON, making quick human review awkward.

## Current Report Behavior

The refreshed report now:

- maps `S_actor_lod_<actor>`, `T_actor_lod_<actor>`, `M_actor_lod_<actor>`,
  `A_actor_lod_<actor>`, and `AC_actor_lod_<actor>` to `<actor>`;
- also maps renderable `asset_entity` names such as `actor_endminf_body_01`;
- includes `asset_entity` counts in each candidate and weights them like mesh
  evidence in the review score;
- emits both `character_recovery_candidates.json` and
  `character_recovery_candidates.md`.

## Validation

Validated by refreshing the ignored generated report from the current SQLite
source graph.

Observed:

- Candidate count increased from 57 to 134.
- No generated candidate has actor key `lod`.
- Conservative matching covers 7,867 report-relevant nodes across 134 actor
  tokens.
- Actor-like `asset_entity` matching covers 522 nodes across 37 actor tokens.
- Raw `actor_lod_*` nodes in report-relevant kinds include 203 `asset` and
  201 `material` nodes; the old regex grouped 403 of them as `lod`, while the
  refreshed extractor groups 0 as `lod`.
- `zhuangfy` remains the top candidate with asset, asset-entity, material,
  texture, and animation evidence.
- `aglina` is now a real candidate with former `actor_lod_aglina_*` material
  evidence contributing to `aglina`.
- `endminf` now includes 25 `asset_entity` records in addition to asset and
  material evidence.

Top refreshed candidates:

```text
zhuangfy 1191 {'animation_clip': 352, 'asset': 225, 'asset_entity': 33, 'material': 26, 'texture': 26}
wulfa 855 {'animation_clip': 293, 'asset': 106, 'asset_entity': 15, 'material': 19, 'texture': 23}
dapan 840 {'asset': 770, 'asset_entity': 10, 'material': 10}
endminf 575 {'asset': 424, 'asset_entity': 25, 'material': 17}
mifu 407 {'animation_clip': 9, 'asset': 182, 'asset_entity': 30, 'material': 17, 'texture': 18}
```

`python -m py_compile tools\endfield_source_graph.py` passes.

Relevant `asset_entity` graph context:

- `entity_has_lod_model`: 30,830
- `model_lod_of_asset_entity`: 30,830
- `entity_uses_material`: 1,962
- `material_used_by_asset_entity`: 1,962
- `entity_uses_texture`: 8,581
- `texture_used_by_asset_entity`: 8,581
