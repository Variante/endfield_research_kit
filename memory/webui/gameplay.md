# Gameplay page recovery

## Purpose

Gameplay owns playable characters, weapons/equipment, enemies, progression,
skills, Buffs, projectiles, semantic asset links, and compact playable sound
links. It is the destination for useful data from the retired Progression and
Combat & Projectiles pages.

## Inputs and recovery flow

1. `scripts.build_gameplay --stage base --stage audit` reads gameplay Tables
   and exact binary/serialized contracts, localizes entries, and publishes
   sharded data.
2. `--stage projectiles` publishes immutable projectile behavior separately.
3. `--stage asset-refs` joins current Gameplay identities to the Assets index
   and is the sole writer of `webui/data/assets/gameplay_refs.json`.
4. `scripts.build_audio` publishes language-specific projectile and gameplay
   sound sidecars.
5. After the curated source graph is current, `--stage combat` publishes
   relationships or an explicit stale/degraded reason.

Primary outputs are `webui/data/lang/<LANG>/gameplay/**`,
`webui/data/gameplay/projectiles.json`, `projectile_audio.json`,
`sound_effects.json`, `combat_relationships.json`, and `gameplay_refs.json`.

## Evidence boundary

- Authored stats and level points are shown as authored; final runtime values
  across Buffs, formulas, and IFix remain uncomputed unless directly proven.
- Binary action chains publish only when typed fields consume to exact
  boundaries. Unknown unions, enums, tags, selectors, and action payloads stay
  explicit.
- Native enum names require the selected GameAssembly/metadata gate.
- Projectile and sound ownership distinguishes exact references from inferred
  candidates. Unresolved ownership remains collapsed/debuggable, not assigned.
- Asset availability, event registration, or graph proximity does not prove
  runtime use.

## Focused refresh

```bat
python scripts\build_gameplay.py
python scripts\build_gameplay.py --stage projectiles
python scripts\build_gameplay.py --stage asset-refs --default-language CN
```

Use the canonical wrapper when cross-page Assets, Audio, source-graph, or
Story inputs changed.

## Remaining gaps

- Improve exact skill-to-projectile, asset, and sound ownership.
- Recover additional action/selector schemas with exact-consumption fixtures.
- Keep runtime formula and tag semantics gated and reproducible.
