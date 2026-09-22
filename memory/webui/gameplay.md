# Gameplay page recovery

## Purpose

Gameplay owns playable characters, weapons/equipment, enemies, progression,
skills, Buffs, projectiles, and semantic asset links. It is the destination for
useful data from the retired Progression and Combat & Projectiles pages. Audio
is deliberately not attached while its ownership model is under review.

## Inputs and recovery flow

1. `scripts.webui.gameplay.build_gameplay --stage base --stage audit` reads gameplay Tables
   and exact binary/serialized contracts, localizes entries, and publishes
   sharded data.
2. `--stage projectiles` publishes immutable projectile behavior separately.
   Its input is the `data_projectile_*` MonoBehaviour JSON whose
   `ProjectileTemplateData` and `ProjectileComponentData` references the
   exporter decoded from the bundle's own managed-reference TypeTree
   (`exactTypeTreeDecoded`, registry fully decoded). Any other shape is
   skipped and counted by reason in the output, never adapted: the retired
   hand-decoder shape published inferred names and a partial tail, and a
   JSON export made before the exporter's TypeTree upgrade contains no
   projectile objects at all, because the exact-only gate excluded them.
   An empty dataset therefore points at the export, not at this stage.
3. `--stage asset-refs` joins current Gameplay identities to the Assets index
   and is the sole writer of `webui/data/assets/gameplay_refs.json`.
4. After the curated source graph is current, `--stage combat` publishes
   relationships or an explicit stale/degraded reason.

Primary outputs are `webui/data/lang/<LANG>/gameplay/**`,
`webui/data/gameplay/projectiles.json`, `combat_relationships.json`, and
`gameplay_refs.json`. Audio recovery may still publish `projectile_audio.json`
and `sound_effects.json`, but this page does not consume them.

## Evidence boundary

- Authored stats and level points are shown as authored; final runtime values
  across Buffs, formulas, and IFix remain uncomputed unless directly proven.
- Binary action chains publish only when typed fields consume to exact
  boundaries. Unknown unions, enums, tags, selectors, and action payloads stay
  explicit.
- Native enum names require the selected GameAssembly/metadata gate.
- Projectile ownership distinguishes exact references from inferred
  candidates. Projectile fields are exact TypeTree values: enum members,
  mount-point ids, layer masks, and Wwise event hashes are published as their
  serialized integers, and no member name is inferred. Audio ownership
  remains outside the page until its evidence model is better understood.
- Asset availability, event registration, or graph proximity does not prove
  runtime use.

## Focused refresh

```bat
python -m scripts.webui.gameplay.build_gameplay
python -m scripts.webui.gameplay.build_gameplay --stage projectiles
python -m scripts.webui.gameplay.build_gameplay --stage asset-refs --default-language CN
```

Use the canonical wrapper when cross-page Assets, Audio, source-graph, or
Story inputs changed.

## Remaining gaps

- Improve exact skill-to-projectile and asset ownership.
- Revisit Gameplay audio attachment only after its ownership and runtime
  evidence boundaries are better understood.
- Recover additional action/selector schemas with exact-consumption fixtures.
- Keep runtime formula and tag semantics gated and reproducible.
- Buff coverage is reported without a current denominator: the page consumes
  exported BuffData with Persistent precedence, but no provenance-matched
  BuffData census exists. See the BuffData corpus gap in
  [`../game_data/extraction_payload_boundaries.md`](../game_data/extraction_payload_boundaries.md);
  until it closes,
  an absent lifecycle/stacking/trigger tail cannot be distinguished from an
  unextracted one.
