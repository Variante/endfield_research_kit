# Characters page recovery

## Purpose

Characters presents localized identities, playable/non-playable grouping,
portraits and model references, while retaining merge and naming provenance.

## Inputs and recovery flow

1. Character-related Tables supply ids, names, roles, rarity, professions, and
   authored relationships.
2. Exported Texture2D/model data and Assets indexes supply resolvable media.
3. `scripts.webui.characters.build_character_data` localizes records, applies
   conservative identity merges and exclusions, and publishes the page index.
4. User-managed name and merge overrides are read and written through
   `serve.py`; generated exports do not replace them.
5. The Updates comparison optionally publishes a version-change sidecar. It
   builds both comparison catalogs itself, one per export, from that export's
   own tables and converted media only (no Story actor registry), so both sides
   use identical inputs ([`characters`](../../scripts/webui/updates/characters.py)).
   The frontend joins changed ids after recovery and manual merging, only for
   badges and filters.

## Primary generated outputs

`webui/data/lang/<LANG>/characters/index.json` plus referenced Assets entries;
the page snapshot `webui/data/_build/characters/<LANG>.json`; the optional
Updates sidecar `webui/data/updates/characters.json`. Frontend behavior is in
the header comment of `webui/src/features/characters/index.js`.

## Evidence boundary

- Shared names, portraits, model tokens, or proximity are candidates, not proof
  that two source records are the same character.
- Generated identity, explicit user override, and unresolved candidate remain
  visibly distinguishable.
- A missing optional model or portrait is degraded media coverage, not an empty
  character record.
- Added/modified/deleted labels describe a comparison of the two generated
  comparison catalogs (Table and exported-asset evidence, no Story actors);
  they do not describe recovery confidence. Deleted identities are read-only
  old-version snapshots; the sidecar cannot alter grouping, names, merges, or
  evidence.
- Rendering and animation parity is not a claim this page makes; it publishes
  identity and exact asset references only.

## Focused refresh commands

```bat
python -m scripts.webui.characters.build_character_data --languages CN --default-language CN
```

Run `scripts.webui.assets.build_assets` first only when asset indexes changed;
run the full wrapper after extraction or shared Story/manifest changes.

## Highest-value remaining gaps

- Keep false-positive identity merges and exclusions auditable.
- Improve exact character-to-model/material/animation closure.
- Preserve stable override migration when generated ids change.
