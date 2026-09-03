# Recovery memory

`memory/` records current, durable recovery knowledge. It is organized by
ownership, not by investigation date.

## Maintenance entry points

- [`webui_recovery.md`](webui_recovery.md): WebUI-wide export flow, shared
  contracts, verification, and links to each page guide.
- [`webui/`](webui/README.md): one recovery guide for each active WebUI page:
  Story, Map, Characters, Gameplay, Audio, Assets, Text, and Updates.
- [`game_story_recovery.md`](game_story_recovery.md): Story evidence, ownership,
  branches, ordering, validation, and remaining reconstruction gaps.
- [`game_data_recovery.md`](game_data_recovery.md): installed formats, gameplay
  and audio semantics, native evidence, and source graph.
- [`asset_recovery.md`](asset_recovery.md): models, materials, media, and
  semantic asset bindings.
- [`animestudio_recovery.md`](animestudio_recovery.md): extraction architecture,
  VFS/schema boundaries, diagnostics, and exporter recovery workflow.
- [`character_render_and_animation_recovery.md`](character_render_and_animation_recovery.md):
  character models, rendering, animation, and parity gaps.

## Retention boundary

These files are intentionally separate. Merge a topic only if its evidence can
no longer exist independently of the proposed owner:

| Topic | Why it is not a WebUI page document |
| --- | --- |
| WebUI recovery | Owns the shared export and publication sequence across pages. |
| Story recovery | Supplies Story evidence to Map, Audio, Mission Pipeline, and the source graph as well as Story. |
| Game-data recovery | Defines raw formats, overlays, native gates, and cross-domain semantics before page projection. |
| Asset recovery | Defines semantic Unity asset/entity ownership reused by several pages and tools. |
| AnimeStudio recovery | Owns extraction correctness and diagnostics, not page semantics. |
| Character render/animation | Owns the optional Unity parity lab and retail observation gates; it is not part of WebUI export. |

## Writing rules

- Update the owning document and replace superseded conclusions; do not append
  session chronology or create dated status snapshots.
- Page guides explain purpose, inputs, recovery flow, outputs, evidence
  boundary, focused refresh, and remaining gaps. Cross-page rules stay in
  `webui_recovery.md`.
- Keep commands and module ownership compact here. Exhaustive command surfaces
  belong in `scripts/README.md` or the matching project skill.
- Put changing counts, hashes, inventories, and generated audits in `reports/`.
  Put revisitable experiments in `scratch/` and disposable intermediates in
  `tmp/`.
- Add a new top-level topic only for a genuinely new durable ownership domain.
  Add a WebUI page guide only when that page is active, and update both WebUI
  indexes in the same change.
