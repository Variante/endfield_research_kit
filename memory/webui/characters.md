# Characters page recovery

## Purpose

Characters presents localized identities, playable/non-playable grouping,
portraits, model references and a searchable appearance index, while retaining
merge, naming and speaker-attribution provenance.

## Inputs and recovery flow

1. Character-related Tables supply ids, names, roles, rarity, professions, and
   authored relationships.
   `characters/story_speakers.py` reads `DialogTextTable`, `RadioTable`,
   `EnvTalkTable` and `MailSenderTable` directly from the export. Optional
   `Json/GameplayConfig/NpcProxyTable.json` and `NpcProxyExDataTable.json`
   name ambient speakers through explicit overrides or `npcNameId` references.
   No generated Story registry, conversations or Story build are required.
   `characters/appearances.py` retains every authored speaking row and also
   reads `SNSDialogTable.speaker`, `RemoteCommonTable.middleId`, and
   `MailTemplateTable.senderId`. Sender definitions, auxiliary Radio labels,
   remote participants without a middle speaker id, and prose mentions do not
   become additional appearances.
2. Exported Texture2D/model data and Assets indexes supply resolvable media.
3. `scripts.webui.characters.build_character_data` localizes records, applies
   conservative identity merges and exclusions, and publishes the page index
   plus a lazily loaded appearance sidecar for each identity.
4. User-managed name and merge overrides are read and written through
   `serve.py`; generated exports do not replace them.
5. The Updates comparison optionally publishes a version-change sidecar. It
   builds both comparison catalogs itself, one per export, from that export's
   own tables, optional proxy Json and converted media (no generated Story outputs), so both sides
   use identical inputs ([`characters`](../../scripts/webui/updates/characters.py)).
   The frontend joins changed ids after recovery and manual merging, only for
   badges and filters.

## Primary generated outputs

`webui/data/lang/<LANG>/characters/index.json`, per-identity
`characters/appearances/<id>.json` sidecars, and referenced Assets entries;
the page snapshot `webui/data/_build/characters/<LANG>.json`; the optional
Updates sidecar `webui/data/updates/characters.json`. Frontend behavior is in
the header comment of `webui/src/features/characters/index.js`.

The index carries each sidecar's relative path, appearance count, source
families and source signature. The `characterAppearances.v1` sidecar carries
the matching language, identity and signature plus complete source locators,
authored speaker/text references and optional Story candidates. The browser
rejects a sidecar from a different publication instead of combining it with
the selected identity. `webui/src/features/characters/appearances.js` reuses
the shared facets and pager to search all appearances without expanding the
main catalog or truncating results to evidence samples.
The appearance section opens initially and can be collapsed from its heading.
Its open/closed state survives character switches within the page; collapsing
and reopening it preserves the current search, facets and pagination.

## Evidence boundary

- Shared names, portraits, model tokens, or proximity are candidates, not proof
  that two source records are the same character.
- Generated identity, explicit user override, and unresolved candidate remain
  visibly distinguishable.
- An authored speaker id is direct evidence of a speaking record, not proof
  of a unique person or model. Labels without ids become `story_candidate`
  records: whole labels may describe people, groups, roles or narrators.
  Blank/question-mark labels and names mentioned only in prose are excluded.
  Candidate ids use normalized fallback-language labels because localized
  text ids are line-specific. They do not automatically merge with named
  characters; an explicit manual override can resolve an identity.
- A question-mark placeholder with one braced name, such as `？？？{亨德森}`,
  uses `亨德森` for its catalog name and candidate id. This automatically joins
  the plain-name candidate; the former candidate id remains an alias.
  Original labels remain in source samples and explicit
  normalization evidence. Other compound/group and scoped annotations stay intact,
  except explicit ampersand labels marked `异口同声`: these are split into
  participant evidence, preserving the original label and source line on both
  participants. A participant is attached to an existing record only when its
  fallback-language name matches one distinct standalone authored speaker id.
  Otherwise it remains a label candidate. `story_joint_speaker` retains an
  `unresolved` boundary; the name-based join does not become a direct actor id
  on the joint line, and ordinary label candidates are not auto-merged.
- Speaker evidence retains occurrence counts and bounded localized source-line
  samples, independently of Story publication. The separate appearance index
  retains every matching row, including unresolved label and joint-speaker
  attribution; a manually merged identity keeps the original source identity
  on each entry. Scoped NPC proxy ids remain
  separate. Suffix stripping, shared prefab names and icon matches cannot
  establish a canonical name; removing the generated Story dependency also
  removes names attached solely through those guesses.
- Story navigation is optional and checked when requested. A candidate must
  match the last published conversation's exact key, Table/row locator,
  line/content id, raw speaker id, text reference and localized source text;
  label-only speakers additionally match the authored name reference. Large
  text ids are compared through exact source-trace strings, never rounded
  JavaScript numbers. SNS media also matches its authored type and parameters.
  A stale or missing conversation keeps the appearance and its source locator
  visible but supplies no link. This joins one authored row, not a person's
  identity or a canonical playthrough. Deep links carry `line` and/or `cid`;
  content ids disambiguate repeated ambient line ids and open SNS branches.
- A missing optional model or portrait is degraded media coverage, not an empty
  character record.
- Added/modified/deleted labels describe a comparison of the two generated
  comparison catalogs (raw Table, proxy and exported-asset evidence);
  they do not describe recovery confidence. Deleted identities are read-only
  old-version snapshots; the sidecar cannot alter grouping, names, merges, or
  evidence.
- Rendering and animation parity is not a claim this page makes; it publishes
  identity and exact asset references only.
- Search reuses groups, indexed search text and evidence counts until catalog,
  language or merge/name override inputs change. Flag filters remain live.
  A still-selected detail is not re-rendered while typing, preserving expanded
  evidence. Locale changes, debug changes, flag changes and new selections
  still refresh the detail.

## Focused refresh commands

```bat
python -m scripts.webui.characters.build_character_data --languages CN --default-language CN
```

Run `scripts.webui.assets.build_assets` first only when asset indexes changed;
`.\export.bat characters` checks input freshness and rebuilds Characters alone.
Its optional Json inputs are declared in the page registry. Story-only changes
do not require a Characters rebuild; changed raw speaker tables do.

## Highest-value remaining gaps

- Keep false-positive identity merges and exclusions auditable.
- Resolve speaker-label candidates with explicit identity references. Discovering
  names mentioned only in prose remains a separate unresolved extraction task.
- Improve exact character-to-model/material/animation closure.
- Preserve stable override migration when generated ids change.
