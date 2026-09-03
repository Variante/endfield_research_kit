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

The shared export sequence and cross-page rules are in
[`../webui_recovery.md`](../webui_recovery.md). Detailed commands and module
ownership remain in [`../../scripts/README.md`](../../scripts/README.md), while
frontend behavior and data layout remain in
[`../../webui/README.md`](../../webui/README.md).

Every guide follows the same order: purpose, inputs, recovery flow, outputs,
evidence boundary, focused refresh, and remaining gaps. Per-build counts and
large inventories belong in `reports/`, not here.
