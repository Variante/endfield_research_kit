# Game-data recovery

## Current status

Basic installed-data access is solved. The exporter indexes both VFS roots,
finds all required chunks, dumps WebUI-relevant blocks, and exports more than a
million Unity objects without relying on a generic silent fallback.

The remaining work is semantic: proving binary layouts, joining records across
systems, and separating authored configuration from live runtime behavior.

Evidence layers:

1. structured tables and JSON;
2. family-specific MemoryPack, FlatBuffer, and MonoBehaviour decoders;
3. the SQLite source graph joining tables, assets, Story, audio, Lua, and
   selected IL2CPP evidence.

## Refresh

```bat
python scripts\verify_export_freshness.py
.\export.bat
.\export.bat --export-from-game
.\export.bat --export-from-game --with-assets
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Use `--export-from-game` only for an intentional installed-data refresh.

## Known data model

- Both StreamingAssets and Persistent VFS roots matter.
- MissionRuntime uses complete-Persistent-or-whole-Streaming selection; never
  mix roots per file.
- Structured tables are the strongest authored foreign-key source.
- MemoryPack and FlatBuffer layouts must be family-specific and fail closed.
- MonoBehaviour `$partial` output is useful evidence, not a clean decode.
- Source root plus PathID is the safe Unity identity; PathID alone is not
  globally unique.
- Static configuration does not prove runtime evaluator order, server state,
  physics, AI decisions, or final formulas.

Current semantic coverage includes Story and mission data, progression,
economy, factory, world placement, characters, weapons, abilities,
projectiles, combat relationships, audio, videos, materials, and selected
runtime consumers.

Projectile configuration is structurally recovered through exact managed-
reference boundary checks: template skills, lifetime, collision, target
filters, movement segments/modes, effects, sound hashes, and source identity
are preserved. Gameplay-tag entries have both path-plus-id and compact id-only
serialized forms. `ProjectileTemplateData.skillDataBundle` describes behavior
owned by the projectile template; it does not by itself prove which playable
skill spawns that projectile. Skill-page placement therefore stays explicitly
identifier/authored-reference inferred, and unmatched internal templates stay
unassigned. Absence of a projectile template is not evidence of an incomplete
skill: visually ranged behavior can be authored as direct `SkillData` actions,
effects, hitboxes, summons, or another runtime system. Non-zero projectile
sound values are direct Wwise HIRC event IDs;
exact event traversal can link them to decoded media candidates. A Wwise
switch/random container may select one or several candidates at runtime, so
the exported link is not a claim that every candidate always plays.

Current SkillData and BuffData blobs use MemoryPack member counts 47 and 30;
the source graph also accepts the previously observed 45 and 29 variants.
Exact length-prefixed `au_`, `bark_`, and `radio_` references can be followed
through nested buff references and Wwise HIRC to playable media. Exact
character skill ids prove ownership; authored child-skill and enemy-id-prefix
placement remains inferred, while explicit enemy born-buff links are direct.

## Source graph

Primary database:

```text
reports/source_graph/endfield_source_graph.sqlite
```

Typical queries:

```bat
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
python tools\endfield_source_graph.py issues --limit 20
```

Graph edges retain their evidence source. Exact foreign keys, serialized PPtrs,
and typed native paths are stronger than normalized names or token similarity.

## Remaining gaps

- Server-side mission/property producers and activation policy.
- Runtime-selected variants, state machines, and evaluator chronology.
- Additional family-specific MemoryPack/FlatBuffer schemas.
- Broader exact world-streaming scene decoding.
- Complete combat formulas rather than authored inputs and references.
- Runtime projectile spawn/call-site ownership, evaluated blackboard values,
  remaining unnamed projectile enums, and Wwise container selection.
- More exact joins between gameplay identities and runtime assets.
- Per-system negative/certification reports that fail visibly when inputs
  change.

Changing counts belong in `reports/`; durable conclusions belong here.
