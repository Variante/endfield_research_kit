# WebUI page recovery

Each active page has one maintenance guide. Read the page guide before changing
its builder, generated contract, or frontend consumer.

- [`story.md`](story.md): conversations, ordering, options, media, and evidence.
- [`map.md`](map.md): level ownership, spatial evidence, render layers, and Story links.
- [`characters.md`](characters.md): identity merging, localization, models, and overrides.
- [`gameplay.md`](gameplay.md): playable/enemy data, skills, buffs, projectiles, and sounds.
- [`audio.md`](audio.md): Wwise identity, decoded media, semantics, and annotations.
- [`assets.md`](assets.md): exported resource inventory and semantic references.
- [`text.md`](text.md): localized table discovery and row rendering.
- [`updates.md`](updates.md): previous/current export comparison.
- [`recovery.md`](recovery.md): per-block volume and per-file-type L1–L4
  recovery state, and the measured-versus-declared boundary the page enforces.
- [`data_inspector.md`](data_inspector.md): generic decoded-dataset publication and debug inspection.

One file here is not a page guide:

- [`story_recovery.md`](story_recovery.md): the Story reconstruction model --
  evidence layers, ownership, branches, ordering, validation, and remaining
  reconstruction gaps -- shared by Story, Map, Audio, standalone Mission
  Pipeline investigation, and the source graph. The carrier-level LevelScript,
  Timeline, native-gate, and spatial-placement rules it used to carry live in
  [`../game_data/story_carriers.md`](../game_data/story_carriers.md).

The shared export sequence and cross-page rules are in
[`../webui_recovery.md`](../webui_recovery.md). Detailed commands and module
ownership remain in [`../../scripts/README.md`](../../scripts/README.md), while
frontend behavior and data layout remain in
[`../../webui/README.md`](../../webui/README.md).

Every page guide follows the same order: purpose, inputs, recovery flow,
outputs, evidence boundary, focused refresh, and remaining gaps. Per-build
counts and large inventories belong in `reports/`, not here.
