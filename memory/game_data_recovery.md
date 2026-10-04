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

Read progress in four layers:

| Layer | What is proved | Current boundary |
| --- | --- | --- |
| Identity and container | Source, overlay, package and logical-byte identity | Broadly recovered; live provider/root selection remains separate |
| Framing | Bounded records and exact consumption of their owning bytes | Strong corpus coverage, with concentrated partial families |
| Named schema | Independently authenticated field names, types and recursive children | Broad coverage; Buff and Skill concentrate the remaining recursive work |
| Consumer meaning | Authored ownership joins and selected native reads | Selective proofs; activation, live values and output remain separate |

Behavioral and visual parity need their own output evidence. A bounded retained
packet replay does not establish general renderer or gameplay parity. Use the
current outer and family receipts for coverage counts; a matching native-input
gate establishes contract applicability, not a fresh corpus sweep.

Current position of the families with active recovery:

- **JsonData.** The authenticated registry (`scripts.game_data.jsondata_corpus`)
  joins every current logical file to the export by path, length and MD5, and
  assigns each a terminal status. Most families close exact named schemas to
  EOF. LevelScriptData, LevelScriptTemplateData and SkillData keep a
  bounded-partial residue; BuffData has an exact named subset while the rest
  stays format-framed. Shared child grammars and generated-reader routes are
  recovered across the residual corpus before another runtime capture is
  considered. Targeted replays measure advancement separately from whole-file
  closure; only the combined gate publishes current totals. Exact storage remains distinct from
  runtime use. See
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
  Separate Wulfa and Seraph cursors, plus one grouped four-source Zhuangfy
  capture, now have source-scoped complete stored-frame joins. Five Zhuangfy
  action routes are admitted to the shared reader under current native gates.
  A later loss-free grouped Lizhiyan/Pograni cursor now names fields 43-47
  and matches both selected static ActionGroups and top-level continuations
  through physical EOF. Both now close under the complete family gate.
  Complete framing remains distinct from recursively named child schemas:
  the registry publishes `storedFrameExact` while `namedSchemaStatus` remains
  unproved where complete child receipts are absent. Known fields are retained.
  Shared Skill routes can reuse Buff-owned action readers only after their own
  dispatcher, wrapper, source order and nested typed calls are proved. A shared
  union tag alone is insufficient. These admissions reuse
  source-scoped terminal evidence after current provenance revalidation and
  need no duplicate framing capture. Selected
  diagnostics alone never replace the family gate. Remaining action tags are
  ranked by corpus coverage and reusable child proofs before selecting a new
  observer.
- **BuffData.** A 30-field root reader closes selected cohorts from byte zero
  through source ID and physical EOF when every reached child has a native
  receipt; `scripts/game_data/memorypack/buff_corpus.py` combines the reviewed
  root, sole-CreateBuff and selected-source admissions with their child
  receipts. Selected positive-heal claymore, BreakPassing event, and equipment
  suit attribute/damage sources now compose to exact EOF under the complete
  family gate; their local diagnostics stay nonpublishable alone. Registry
  publication requires fresh canonical export replay. DataPair lists and the
  shared AttributeModifierData collection now use forward readers rather than
  historical candidate co-occurrence restrictions. Residual ranking excludes
  already exact roots and distinguishes proved children from a still-unproved
  parent composition. Shared event-map actions now compose the reviewed
  damage-mask condition and main-character target condition, plus the advanced
  Buff-ID condition's independently proved BlackboardString subtype list and
  GameplayTagQuery. Stored conditions still do not establish their evaluation.
  Positive damage, event-action and finder bodies retain
  their explicit recursive blockers.
- **Audio packages.** The complete available AKPK roster now retains sector,
  full-width key, language and package identity. Repeated typed keys and low-word
  collisions stay explicit; neither picks a runtime package or decoded file.
  This inventory supports corpus-wide byte and naming joins without another
  playback capture. See
  [`game_data/audio_overview.md`](game_data/audio_overview.md).
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
- **Unity and presentation.** Standard object and media decoding is established;
  prefab composition, material variants, Animator ownership and effect timing
  remain consumer joins. Retained ribbon output proofs apply only to their
  selected packets ([`game_data/unity_assets.md`](game_data/unity_assets.md)).
- **World.** DynamicStreaming's authored component ownership is recovered under
  its raw-source and template gates. Streaming still has anonymous subgraphs;
  Terrain texture-path bindings remain conditional on the selected resources,
  with channel meaning open; irradiance index ranges do not name record
  encoding or GPU interpretation. Their owning guides are indexed below.
- **Code and native I/O.** Decoded Lua and IFix instructions support static
  references and selected operand joins, while invocation and patch activation
  remain open. The static stream/read chain does not supply a live backing-file
  identity or full-buffer delivery guarantee. See
  [`game_data/ifix_patch.md`](game_data/ifix_patch.md) and
  [`game_data/native_read_path.md`](game_data/native_read_path.md).

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

Recovery work is corpus-first. Choose the next shared reader, child grammar,
provider rule or cross-format join by the authenticated files and distinct
stored shapes it can explain. A familiar character, filename or successful
playback is a representative fixture, not the unit of progress. Keep storage
coverage separate from runtime selection, ownership and output: closing one
runtime question may improve understanding without decoding another file.

- Start each batch from the owning current family receipt and ranked refusals.
  Prefer a shared dependency reached by many sources to another source-specific
  exception. Counts of first stops measure files that may advance; only a
  complete owner replay and family gate measure whole-file closures. Report
  both, and rerank when a newly exposed child becomes the next refusal.
- Compose independently proved child grammars into the shared reader, validate
  representative positive and refusing shapes, then publish the coherent batch
  once through its owning gate and page builder. Preserve exact, structural,
  conditional and unresolved claims in the published result. More probes,
  hook fields or successful checks are not coverage gains by themselves.
- Reuse retained captures, current stored bytes, native consumer proofs and
  selected offline decoding before requesting user work. A current source and
  dependency join can reuse a historical observation; repeating an unchanged
  source does not strengthen its stored grammar. An unobserved runtime branch
  stays unobserved without holding unrelated offline recovery.
- A capture request must state the missing reusable rule, the affected verified
  source cohort or explicitly runtime-only question, and why existing evidence
  cannot decide it. Name the distinct representative branches needed, the
  expected generalization boundary and the acceptance/stop criteria before
  collecting. Do not revisit one unique case for additional sampled fields
  unless those fields can decide a high-value shared join.
- Live capture tooling is internal-only; its repository boundary and the
  instrumentation prohibition are documented in `AGENTS.md`. Saved evidence
  remains useful only within its admitted format, consumer branch and source
  scope. Name the missing state transition or observation before requesting
  further evidence, and diagnose failed admission before repeating a recording.

1. **BuffData.** Rank residual recursive fields after excluding every admitted
   root. Reuse shared DataPair, AttributeModifierData, action and finder
   grammars only through independently proved parent typed calls. Ability and
   Buff event maps have different stored read orders despite sharing their
   SequenceActionData element. General input-list and sibling-action counts
   must follow the reader's bounded framing, not historical source-cohort
   restrictions. New compositions still require all thirty root fields,
   source-ID equality, physical EOF, the complete family gate and canonical
   export replay. Unproved positive-damage and finder/selector interiors stay
   explicit refusals; stored fields establish neither condition truth nor
   gameplay effects.
   Start with reusable event-action children and complete root composition,
   distinguishing an unproved child from a parent missing its composed receipt.
   The source-authenticated residual census owns changing cohort sizes; first
   obligations can overlap and reveal later blockers. The current family sweep
   includes the general shared event-map and AttributeModifier compositions;
   historical receipts from before those readers are coverage baselines only.
2. **LevelScript.** Native/source receipts feed the shared named reader. Only
   a complete owner at physical EOF can be promoted by the combined JsonData
   gate; closing an action may expose a later first stop. Rerank with
   `scripts.game_data.levelscript_first_stop_census` after a gate, then recover
   the highest-value refusals in validated batches. Unlock, travel-pole and
   laser-event headers, string/entity getters and click-enable inputs now have
   reviewed stored routes. These compose through the existing typed child
   grammars; event activation, resolved outputs and provider/cache selection
   remain open. Damage-event filters, integer-list getters and movement and
   navigation stop inputs now have independently reviewed parent routes too; complete
   owners still require EOF, and a closed route can expose a later module gap.
   Promotion rules and wire conclusions live in
   [`game_data/serialization_memorypack.md`](game_data/serialization_memorypack.md).
3. **SkillData.** Historical cursor receipts can be rebound only to unchanged
   logical sources under current parser/native provenance and a complete corpus
   gate. The positive control must retain its previous claim. The verified
   source joins need no duplicate framing capture. Shared action grammars enter
   through independently authenticated dispatcher, wrapper and child-context
   contracts, including reuse of Buff-owned readers.
   Their ActionGroup closure still requires a source-bound terminal selection
   for complete stored framing. This does not prove recursive field naming:
   anonymous children and missing naming receipts remain explicit even at EOF.
   A complete family report owns framing promotion; a sparse report or a closed
   first ActionGroup does not classify the remaining corpus or top-level
   continuation. Rank the residual distinct
   action stops after publication, and reuse authenticated stored framing for
   selection-only replay when its current dependency closure still matches.
4. **Gameplay formulas.** Selected damage/Poise evaluators and callers are
   proven statically ([`game_data/gameplay_semantics.md`](game_data/gameplay_semantics.md));
   receiver identity, live invocation, subtype selection, patch state,
   provider values and final damage remain unresolved.
5. **World.** DynamicStreaming now has selected-native scalar and inline-vector
   component layouts and a direct authored MissionCondition string-slot join;
   Data exposes these only after native, current-roster and raw-byte checks.
   Authored RootComp-to-DataIndex-to-component-instance ownership also closes
   under the raw-source and template gates. Indirect child assignment, spatial
   units and live condition evaluation remain separate joins in
   [`game_data/world_dynamic_streaming.md`](game_data/world_dynamic_streaming.md).
   Streaming needs independent record-end evidence or a bounded
   runtime carrier witness before field names; keep selector9, Marker13 gap
   profiles and Marker17 bodies anonymous; slot-7 field 0 is each group's
   descriptor-ID mask, so its bits stay as anonymous as the IDs. Framing lives
   in `scripts/game_data/streaming/framing.py`; see
   [`game_data/world_chunk_slots.md`](game_data/world_chunk_slots.md) and
   [`game_data/world_chunk_unread_region.md`](game_data/world_chunk_unread_region.md).
   Then Terrain channel meaning and live file selection, DynamicStreaming
   nested main records, auxiliary fields beyond descriptor 21 and live
   grid/area selection, and irradiance root/provider/record semantics.
6. **Audio.** HIRC layout and the shipped decision-tree walk are closed
   against the Wwise SDK and bank corpus. The current AKPK inventory and BKHD
   identity joins support broad offline recovery; preserve full external keys,
   package-qualified bank variants and ordered Event actions. Complete the
   decode pipeline's typed-entry/encoded-byte/decoded-byte provenance before
   asking for more single-sound comparisons. Existing combined recordings
   already supply managed paths, local provider/descriptor entries, successful
   read completions and sparse pre-transform words; selected offline entries
   also have equal decoded PCM. These do not identify every live backing file,
   allocation generation, complete buffer or game decoder instance. A future
   session must target a named shared runtime join and distinct missing consumer
   branches, with acceptance criteria established first. Native plug-in value
   meanings and other offline work remain independent of that session. See
   [`game_data/audio_native_hooks.md`](game_data/audio_native_hooks.md) for the
   retained observation boundaries and
   [`game_data/audio_overview.md`](game_data/audio_overview.md) for the six-layer
   evidence model. Native callsites are re-proved by name on a new build through
   `scripts/webui/audio/semantics/native_callsite_rederivation.py`.
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
