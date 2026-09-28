# Game-data recovery

This topic owns durable conclusions about installed data formats, gameplay and
audio semantics, native consumers, and the source graph. It does not own WebUI
presentation, page build commands, or AnimeStudio implementation mechanics.
This file is the entry point; per-family evidence lives in
[`game_data/`](game_data/README.md), and the mechanics of each reader, gate and
validator live in its module docstring and reviewed contract under `scripts/`.

## Why this topic remains

Many evidence contracts are shared by several pages or exist before any page
projection: overlay behavior, binary framing, native build gates,
runtime/static distinctions, and cross-domain graph provenance.

## Refresh and evidence rules

```bat
python -m scripts.game_data.extraction.verify_export_freshness
.\export.bat --from-game
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Run `--from-game` only when the user asks for an installed refresh.

- StreamingAssets is the fallback; Persistent is the active overlay. A changed
  logical path replaces its fallback file as a whole unless a format-specific
  contract proves record-level merging.
- Native claims require the selected `GameAssembly.dll` plus
  `global-metadata.dat` gate. Missing or mismatched inputs skip that evidence
  and leave the last validated report untouched.
- Metadata default blobs require their primitive backing type: decoding a
  byte-backed enum as a signed compressed `Int32` invents negative IDs. Resolve
  the backing type from the selected MetadataRegistration first; the native
  enum helper supports reviewed byte and `Int32` cases and fails closed.
- A source-only classifier does not inherit the native gate because native
  evidence once motivated it. Direct gate callers are runtime-capture identity,
  metadata enum reads, and consumers of pinned methods, code windows, field
  offsets, registrations or native contracts. Current-export Story classifiers
  validate their own tables, object-index stage signatures and fingerprints.
- **`inputSetSha256` identifies one audit run, not the game build.** It hashes
  the exporter binary and absolute asset roots, so it is only a join key
  between one run's VFS summary, ledger and corpus reports. No contract is
  gated on it and tests must read it from their fixture, never hardcode it.
  Whether a contract applies is decided by its `nativeInputs`.
- Hash checks survive only where git cannot guard: the installed build against
  `nativeInputs`, native code bytes against a recorded window or body hash,
  installed game files such as iFix patches, and a generated report against
  its inputs.
- A field name, code address, registration order, hash collision, filename,
  proximity, or available asset is not ownership or runtime execution.
- Preserve source root, logical path, file hash, record offset, parser/schema
  version and validation status through every join.
- Exact parsers require bounded positive fixtures, malformed/truncated/trailing
  negatives, exact consumption, and a current-corpus sweep.
- Build-specific counts, hashes, tokens, addresses and inventories belong in
  reports or versioned contracts.

## Re-resolving a native identity after a client update

A contract pinned to a superseded build is not evidence that its subject is
gone. Only the managed name survives an update, so a stale contract is
migrated by resolving names against the selected build, never by carrying an
address forward. `scripts/game_data/il2cpp/method_resolver.py` owns that
direction and documents the three name classes that drift without a source
change (compiler-generated closures, Burst direct-call wrappers, recorded
display forms). A resolved body extent is the gap to the next method pointer,
an upper bound rather than a proven length; re-resolution restores identity
only, so the old contract's conclusions about the bytes stay unvalidated until
re-derived. Prefer build-independent claims contracts
(`il2cpp/body_claims.py`) for new consumer claims.

## Installed-data model

The installed client exposes overlapping logical data through VFS catalogs and
payload roots. A verified outer VFS boundary proves byte identity and
availability, not the inner payload schema. The full outer VFS audit, Bundle
inner audit, Table dump and JsonData source/export join give a strong
structural baseline for the selected build. Named-schema coverage is narrower,
and no file count measures effective runtime consumers or behavioral/visual
parity. Current denominators live in the generated `reports/animestudio/`
receipts; per-family reader boundaries are in
[`game_data/extraction_payload_boundaries.md`](game_data/extraction_payload_boundaries.md).

Current position of the families with active recovery:

- **JsonData.** The authenticated registry (`scripts.game_data.jsondata_corpus`)
  joins every current logical file to the export by path, length and MD5, and
  assigns each a terminal status. Most families close exact named schemas to
  EOF. LevelScriptData, LevelScriptTemplateData and SkillData keep a
  bounded-partial residue; BuffData has an exact named subset while the rest
  stays format-framed. The last complete combined gate predates the most
  recent LevelScript integrations, so their whole-owner effect is provisional
  until the next full gate. See
  [`game_data/serialization_memorypack.md`](game_data/serialization_memorypack.md).
- **LevelScript.** The sequential owner reader continues through action maps,
  task maps, NPC, enemy and module dictionaries at exact cursors. Each union
  route moves through three steps: an isolated contract and validator,
  registration in the shared ActionMap/layout with production replay, and
  whole-owner closure only through the full JsonData gate. This is
  stored-schema recovery; no stored action proves runtime execution.
- **SkillData.** Native-gated readers close the reviewed ActionGroup interiors
  and rejoin the selected top-level terminal. The live target-set cursor
  capture is complete and loss-free: every reviewed ambiguous source and the
  positive control verify, so no further capture is needed for that set.
  Purrche's below-Potential-3 branch was unavailable on the user's save; its
  stored source and native logic are recovered, its execution is unobserved.
  The residual partial files stop at mostly distinct action tags.
- **BuffData.** A 30-field root reader closes selected cohorts from byte zero
  through source ID and physical EOF when every reached child has a native
  receipt; the admitted cohort set is the branch logic in
  `scripts/game_data/memorypack/buff_root_no_positive.py` and its child
  receipts. Other files keep recursive blockers in positive `damageModifier`,
  `attributeModifier`, event-action and finder bodies.
- **ExtendData catalogs.** Both StringPathHash catalogs have current
  cross-format hash joins to VFS filename hashes and BundleManifest asset
  paths; the catalog writer and runtime lookup remain open
  ([`game_data/extend_data.md`](game_data/extend_data.md)).
- **CompressData / AI.** A selected native chain runs from a spawn record's
  template ID through `EnemyTable` to a formatted `AIConfig` load, and authored
  BehaviourTree identities join archive ordinals. No checked producer equates a
  SpawnerConfig library entry's stored `enemyId` with the protocol template ID,
  and live spawn selection stays open
  ([`game_data/extend_data.md`](game_data/extend_data.md)).
- **Video carriers.** Stored `PlayFmvAction.moviePath` values join installed
  Video files through a selected native `f_`/`m_` naming branch; that joins
  authored naming, not an activated scene
  ([`game_data/story_carriers.md`](game_data/story_carriers.md)).
- **Bundles.** Corrected AssetMap container paths resolve the former fallback
  residuals, and the CAB dependency sweep places every mapped external
  reference inside the BundleManifest dependency list; manifest-only edges and
  a live selected load stay open
  ([`game_data/unity_assets.md`](game_data/unity_assets.md)).

Stable cross-format rules:

- Unity object identity is source/CAB plus PathID. A global PathID or basename
  is never sufficient.
- Table ids and localized strings are authored values; they do not by
  themselves prove a runtime consumer.
- Serialized TypeTrees are preferred when exact. `$partial`, `$unparsed`, and
  `$inferred` stay visible and are never upgraded by a later name match.
- Runtime-mutable properties keep their authored initializer but are not final
  action targets unless later writes are excluded.
- Exact spatial transforms prove authored placement, not spawning, activation,
  visibility, or interaction.

## Where the detail lives

[`game_data/README.md`](game_data/README.md) holds the four evidence levels,
the block-to-lane table and the file index. A claim may cite evidence only from
its own level or below; most recorded mistakes read a level-4 meaning off a
level-2 framing. Read
[`game_data/settled_and_open.md`](game_data/settled_and_open.md) before
reopening chunk slot typing or HIRC type coverage.

Per-build member orders live in `scripts/game_data/contracts/`; each reader,
gate and validator documents what it proves, and what it does not, in its
module docstring. What a decoded carrier proves about Story stays in
[`game_data/story_carriers.md`](game_data/story_carriers.md); what it means for
published Story stays in [`webui/story_recovery.md`](webui/story_recovery.md).

## Asset and spatial semantics

AssetMap rows, PPtrs, prefab/component dependencies, material slots, textures,
controllers, clips, effects, and scene records form an evidence chain. A later
link keeps the earlier physical identity and is never replaced by a
normalized-name match.

World registries, LevelData, streaming matrices, NPC proxies, authored pins,
and trigger geometry use separate identity domains. Script-wide context and
proximity never fan out to sibling slots. Dynamic getters and runtime lists are
non-spatial unless a pinned producer proves one immutable authored target.

Semantic asset ownership belongs in
[`game_data/unity_assets.md`](game_data/unity_assets.md); Map publication
belongs in [`webui/map.md`](webui/map.md).

## Source graph

The canonical database is `reports/source_graph/endfield_source_graph.sqlite`.
It indexes evidence already produced by owning builders: a query and
provenance surface, never an authority that invents recovery logic.

```bat
python tools\endfield_source_graph.py query IDENTIFIER
python tools\endfield_source_graph.py story STORY_KEY --limit-lines 8
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Default builds keep only the exact AssetMap rows consumed by WebUI material,
shader, texture and FMV edges; full builds are for exhaustive PathID work.
Every edge keeps an evidence kind; availability, registration, address order
and mission context never become ownership or chronology. Before deleting or
renaming a generated report, search graph readers and rebuild the database if
that report is an input.

## Diagnostics

Use the closest owning report first: `reports/export/`, `reports/animestudio/`,
`reports/game_data/`, `reports/assets/`, `reports/audio/`,
`reports/source_graph/`, `reports/story/build/`, `reports/story/recovery/`.
Revisitable probes belong in `scratch/<topic>/`; disposable intermediates in
`tmp/<topic>/`.

## Recovery queue

In priority order. Offline work first; request a live capture only for a
residual that cannot be resolved offline.

1. **LevelScript batch.** Integrate the tracked `0x0366` PlayEffectOnNpc route
   into the shared ActionMap/layout with focused tests and production replay,
   then `0x002B` BlockBattleMusic and `0x002A` BlockAutoMusicChangeCancel.
   Continue the highest first stops in
   `scripts.game_data.levelscript_first_stop_census` (ActionBase `0x00C9`
   FacGetBuildingPosition, `0x0007` AddBuffsToTargetSelves, ActionHeaders
   `0x0040` LevelEvent_OnAetherEnergyLockEndPointScanned and `0x006A`
   LevelEvent_OnEntityHpChanged) as independent routes; turn the
   `0x0032` BuildingPosHintShow probe into a contract once its enum alias is
   resolved. At the batch boundary run the full authenticated JsonData gate
   once, rerank first stops, and replace provisional whole-owner projections.
2. **BuffData.** Promote the isolated gradual positive-damage branch only after
   its reviewed draft contract and reader move into `contracts/` and
   `memorypack/` with focused tests and whole-root replay. The remaining sword
   root needs several new nested grammars; other positive `damageModifier`
   children, the two positive `attributeModifier` sources, anonymous
   event-action interiors and positive finder bodies need their own child
   proofs.
3. **SkillData.** Its residual partial files each stop at a distinct action tag
   with one or two files; rank them before choosing, since LevelScript routes
   currently have better corpus yield.
4. **Gameplay formulas.** Selected damage/Poise evaluators and callers are
   proven statically ([`game_data/gameplay_semantics.md`](game_data/gameplay_semantics.md));
   receiver identity, live invocation, subtype selection, patch state,
   provider values and final damage remain unresolved.
5. **World.** Streaming needs independent record-end evidence or a bounded
   runtime carrier witness before field names; keep selector9, Marker13 gap
   profiles and Marker17 bodies anonymous; slot-7 field 0 is each group's
   descriptor-ID mask, so its bits stay as anonymous as the IDs. Framing lives
   in `scripts/game_data/streaming/framing.py`; see
   [`game_data/world_chunk_slots.md`](game_data/world_chunk_slots.md) and
   [`game_data/world_chunk_unread_region.md`](game_data/world_chunk_unread_region.md).
   Then Terrain channel meaning and live file selection, DynamicStreaming
   nested main records, auxiliary fields beyond descriptor 21 and live
   grid/area selection, and irradiance root/provider/record semantics.
6. **Audio.** HIRC layout and the shipped decision-tree walk are closed against
   the Wwise SDK and bank corpus; value naming, remaining plug-in blocks, a
   host for layers 5 and 6, and the playback call chains stay in
   [`game_data/audio_overview.md`](game_data/audio_overview.md).
   `scripts/webui/audio/semantics/native_callsite_rederivation.py` re-proves
   the native catalog by name on a new build.
7. **Catalog and code.** BundleManifest cross-store identity and live lookup,
   mmap, and IFix patch execution.
8. Improve exact prefab, renderer, material, animation and world-instance
   ownership, and keep native gates and graph provenance deterministic across
   client updates. LevelScript, LevelData, Spawner, Story and the Buff action
   dispatcher resolve union tags by name; literal AbilityActionData tags remain
   in `skill_timeline_shared_sequence`, `buff_residual_actions`, the nested
   selector/processor profiles of `buff_actions`, `buff_corpus` frontier lists,
   receipt `TAG` constants and `buff.py` tables. Their per-route native
   contracts still refuse another build, but convert them before the next
   client update.
