# Recovery memory

`memory/` records current, durable recovery knowledge. It is organized by
ownership, not by investigation date.

## Maintenance entry points

- [`webui_recovery.md`](webui_recovery.md): WebUI-wide export flow, shared
  contracts, verification, and links to each page guide.
- [`webui/`](webui/README.md): one recovery guide for each active WebUI page:
  Story, Map, Characters, Gameplay, Audio, Assets, Text, Updates, and Recovery,
  plus
  [`webui/story_recovery.md`](webui/story_recovery.md): Story evidence,
  ownership, branches, ordering, validation, and remaining reconstruction gaps,
  shared by every consumer of Story evidence.
- [`game_data_recovery.md`](game_data_recovery.md): installed formats, gameplay
  and audio semantics, native evidence, and source graph.
- [`game_data/`](game_data/README.md): one detail file per installed-data
  evidence domain below that topic: payload families, gameplay semantics, the
  Wwise/HIRC chain, irradiance volumes, terrain layers, chunk/streaming
  schemas, DynamicStreaming grids and area records, IFix patch records, and the
  consolidated slot and HIRC state.

## Retention boundary

These files are intentionally separate. Merge a topic only if its evidence can
no longer exist independently of the proposed owner:

| Topic | Why it is not a WebUI page document |
| --- | --- |
| WebUI recovery | Owns the shared export and publication sequence across pages. |
| Story recovery (`webui/story_recovery.md`) | Supplies Story evidence to Map, Audio, Mission Pipeline, and the source graph as well as Story. |
| Game-data recovery | Defines raw formats, overlays, native gates, and cross-domain semantics before page projection. |

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
  `tmp/`. Those three and `scripts/tests/` are gitignored, so a fact that
  exists only there is not in the repository: keep
  the durable interpretation here, and do not cite such a path as a
  conclusion's only evidence. See the tracked-versus-local-only table in
  `AGENTS.md`.
- Add a new top-level topic only for a genuinely new durable ownership domain.
  Add a WebUI page guide only when that page is active, and update both WebUI
  indexes in the same change.
- `webui/` and `game_data/` are the only subdirectories. A `game_data/` file
  owns one installed-data evidence domain; its cross-family rules, refresh
  commands, and remaining gaps stay in `game_data_recovery.md`. Add one only
  for a genuinely separate family, and update
  [`game_data/README.md`](game_data/README.md), the parent file's index, and
  this file together.
