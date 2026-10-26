# WebUI page recovery

The main page guides follow the WebUI navigation order. Read the owning guide
before changing a builder, generated contract, or frontend consumer.

- [`story.md`](story.md): conversations, ordering, options, media, and evidence.
- [`gameplay.md`](gameplay.md): Characters, Weapons, Essences, Equipment, Items,
  Enemies, Combat stages, and Activities; skills, buffs, projectiles, item effects,
  buildings, and recipes.
- [`map.md`](map.md): level ownership, spatial evidence, render layers, and Story links.
- [`characters.md`](characters.md): identity merging, localization, models, and overrides.
- [`text.md`](text.md): localized table discovery and row rendering.
- [`audio.md`](audio.md): Wwise identity, decoded media, semantics, and annotations.
- [`assets.md`](assets.md): visual assets, exported media, and semantic references.
- [`data_inspector.md`](data_inspector.md): Decoded, with Files and SQL
  modes over export stores and a published decoded-dataset source.
- [`updates.md`](updates.md): previous/current export comparison.

Gameplay subpage and debug-page guides:

- [`activities.md`](activities.md): Gameplay’s Activities tab and supporting
  tables from the shared Text publication; no standalone page or builder.
- [`recovery.md`](recovery.md): per-block volume and per-file-type L1–L4
  recovery state, and the measured-versus-declared boundary the page enforces.

Supplementary publication and recovery guides:

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
