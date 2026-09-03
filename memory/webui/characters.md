# Characters page recovery

## Purpose

Characters presents localized identities, playable/non-playable grouping,
portraits and model references, while retaining merge and naming provenance.

## Inputs and recovery flow

1. Character-related Tables supply ids, names, roles, rarity, professions, and
   authored relationships.
2. Exported Texture2D/model data and Assets indexes supply resolvable media.
3. `scripts.build_character_data` localizes records, applies conservative
   identity merges and exclusions, and publishes the page index.
4. User-managed name and merge overrides are read and written through
   `serve.py`; generated exports do not replace them.
5. The Updates comparison optionally publishes `webui/data/updates/characters.json`;
   the frontend joins its ids after recovery and manual merging, only for
   version-change badges and filters.

Primary output: `webui/data/lang/<LANG>/characters/index.json` plus referenced
Assets entries.

Optional Updates sidecar: `webui/data/updates/characters.json`.

## Evidence boundary

- Shared names, portraits, model tokens, or proximity are candidates, not proof
  that two source records are the same character.
- Generated identity, explicit user override, and unresolved candidate remain
  visibly distinguishable.
- A missing optional model or portrait is degraded media coverage, not an empty
  character record.
- Added/modified/deleted labels describe CharacterTable version comparison, not
  recovery confidence. Deleted identities are read-only old-version snapshots;
  the sidecar cannot alter grouping, names, merges, or evidence.
- Rendering and animation parity claims belong in
  [`../character_render_and_animation_recovery.md`](../character_render_and_animation_recovery.md).

## Focused refresh

```bat
python scripts\build_character_data.py --languages CN --default-language CN
```

Run `scripts.build_assets` first only when asset indexes changed; run the full
wrapper after extraction or shared Story/manifest changes.

## Remaining gaps

- Keep false-positive identity merges and exclusions auditable.
- Improve exact character-to-model/material/animation closure.
- Preserve stable override migration when generated ids change.
