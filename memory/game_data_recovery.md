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
  GameplayTagQuery. DirectionSettings now composes independently owned source
  and target references recursively; Selector postprocessors compose Projection,
  shapes, ExcludeTarget's recursive target, PriorityFilter's BuffFindSettings
  and ShuffleTarget's concrete BlackboardInt through separate typed parents.
  CircularOrderSort and NavMeshPathPositionProcessor add owned generated-setter
  transfers, typed scalar/target children and explicit primitive cursor reads;
  their stored declarations do not establish ordering or navigation effects.
  Positive Timeline/ForceSync source elements now have independent buffered
  cursor and ordered owned-field programs; original-span element receipts
  deliberately leave nullable runtime adapters, positive lists and root
  admission open.
  Their separate static composition now proves original-type adapter and
  wrapper-formatter registration, concrete constructor contexts through shared
  code thunks, typed GetValue/formatter forwarding and the root's identical
  Timeline list carrier. The separate reference lane proves the buffered FF
  null branch's complete cursor accounting and original output clear. Its
  class-owned ABI distinguishes the non-null helper's by-value wrap from the
  byref original output and reader. Its selected non-null helper now proves
  the saved Reader reload, preserved input wrap slot, distinct owned generic
  parameters, actual second-interface lookup and concrete formatter/getter
  fallbacks through original output and return. This remains conditional on
  compatible runtime contexts and the reviewed provider result. The separate
  positive parent proof now preserves its own Reader/output saves, wrapper-owned
  Activator MethodInfo and created local through child dispatch, conversion and
  both complete returns. Provider and Activator MVARs have reciprocal ownership.
  The concrete wrapper metadata selects the creation branch when runtime
  attributes describe that same class; the abstract direct-zero alternative
  cannot replace it. The actual CreateInstance call matches its registered
  shared entry. A class-key prefix independently kills unused incoming byref
  bits before use, without proving helper purity. Runtime class/metadata parity,
  full creation/cache/provider effects remain open. A separate source-wrapper
  proof now consumes the buffered FF byte, updates all four cursors and clears
  the wrapper byref through a complete return under the disabled-barrier state.
  Each selected concrete constructor preserves its receiver and stores its
  original-type allocation result into the owned instance field. Allocation
  contents, actual constructor invocation and active barrier behavior remain
  conditional or unresolved; original nullable child/cursor composition is open.
  The same positive Timeline/ForceSync source-field programs now continue through
  complete no-call/no-object-write/no-Reader-write return suffixes, with exact
  stack and nonvolatile restoration. This closes their earlier final-store
  boundary while retaining the disabled-barrier and typed-call conditions.
  Timeline's child calls carry separately closed ReadValue contexts. Their
  actual helper now has a complete selected Reader/local-output/return proof
  with reciprocal provider/formatter parameter ownership. Its separately
  registered Object entry differs, leaving named body identity open. The
  dispatcher matches the original adapter's first optimized case and inlines
  it; complete selected FF and positive clear/conversion paths are separately
  proved. This cannot reuse the ordinary fallback for that outer call. Sequence
  concrete adapter/wrapper registration, closed constructor thunk and typed
  source forwarding are now independently joined; its nested formatter/getter
  pointers use the ordinary fallbacks. The actual formatter helper now has an
  independently required same-MethodInfo key/class and complete typed-reference
  return proof for both ReadValue and list control. The selected initialized
  cache and correctly typed normal returns remain conditions; indirect global
  calls and cache-miss effects remain unproved. Physical wrapper GetFormatter effects,
  original child cursor composition and complete root composition remain open;
  no child grammar, positive list or root is admitted by it.
  Sequence's inline action-array source now has complete selected FF,
  null/empty array and single/repeated positive-element programs through return,
  with owned ReadArray overload/element-context joins, direct cursor transfers,
  same-Reader child destinations and both normalized flags. Typed helper/child
  returns and compatible runtime context selection remain conditions; actual
  Empty/allocation identity/effects and child cursor composition remain open.
  A selected buffered existing-list loop now proves the signed count/cursor,
  null temporary reference, element dispatch, reference append and saved-count
  back edge. The root's actual ReadPackable helper now has a complete selected
  same-Reader/initialized-output/typed-dispatch/return proof, and a local caller
  joins that return to the owned timeline field. Complete null/new-list paths
  reuse the proved loop; the actual capacity constructor joins its owned class
  contexts and preserves the capacity/allocation result through return. Open
  generic field offsets do not name its observed reference slot. Fresh-list
  zero count, array capacity, allocation/static-field effects and runtime
  selection remain conditional or unresolved. Original element cursor
  composition, full root entry/tail and physical span/provider effects remain
  open. The actual reset helper's index-zero/version update is independently proved;
  initialization and actual runtime selection are unobserved.
  Nullable child framing now joins the actual ReadValue helper, concrete
  forwarding and complete source returns: FF advances one byte; the positive
  adapter peeks without consuming the source header. The direct Timeline,
  Sequence and ForceSync overheads compose with their child advances, and an
  audit checks the unchanged certified original storage spans against these
  equations. Callback native advances, string-helper cursor/global effects,
  stable Reader aliases and full list/root composition remain distinct;
  source-only receipts gain no admission from the arithmetic check.
  The action base and generated base wrapper are independently authenticated as
  abstract. The original adapter's `InitEager` allocation/context/key/RegisterWrap
  flow and concrete union formatter registration are now proved. The actual
  tag helper has complete buffered one-byte and three-byte UInt16 paths plus
  the high-marker zero/false path, with all four cursors and restored state.
  Reserved markers gain no canonical null admission. The selected abstract
  adapter branch now initializes a zero wrapper local without a direct Activator
  call and preserves the same Reader/local through both complete child-output
  returns. The union's AL-false branch clears its wrapper output and returns
  through an actual jump to the independently proved disabled shared barrier.
  Matching runtime attributes and initialized contexts remain conditions.
  The action adapter's declared virtual slot and void/byref ABI now join the
  exact original element, reciprocal generic parent and owned indexed array
  output through the
  [callback binding contract](../scripts/game_data/contracts/buff_action_array_callback_binding_native.json).
  The abstract base's raw slot remains structural-only. A missing unique closed
  compiled registration does not exclude runtime generic inflation; provider
  cache identity and the live vtable/MethodInfo still require independent proof.
  The [registration-state contract](../scripts/game_data/contracts/buff_formatter_registration_state_native.json)
  now connects the complete RegisterWrap caller and public Type lookup to their
  actual dictionary/result helpers. Setter and named lookup share the exact
  closed dictionary context and static address expression; the selected named
  hit returns its full reference output. Dictionary effects, physical inlined
  lookup control and runtime state remain open, including provider loads from
  storage without on-disk backing. The
  [dictionary lookup contract](../scripts/game_data/contracts/buff_formatter_dictionary_lookup_native.json)
  now checks the actual named caller target, sign-cleared word/remainder index,
  unsigned guard, finite node route and full hit/miss output through restored
  returns under explicit storage/helper/disabled-barrier conditions. Anonymous
  slot meanings remain structural; hash/equality helper semantics, setter
  mutation and live cache/class/callback selection are still unresolved.
  The [comparer-dispatch contract](../scripts/game_data/contracts/buff_formatter_comparer_dispatch_native.json)
  now connects the actual UInt16 selectors, unsigned record scan, signed offset
  arithmetic, function/context pair and complete ordinary/specialized returns.
  Runtime interface/slot identity and opaque object/payload child semantics
  remain open; compiled target declarations do not establish live selection.
  The [preparation/fallback contract](../scripts/game_data/contracts/buff_formatter_dispatch_fallback_native.json)
  separately proves the actual load/tail transfer, stored-byte gates, original
  receiver/context/UInt16 forwarding and conditional nonnull result returns.
  Child search/initialization effects and deeper resolver code-versus-table
  boundaries remain unproved; an owned native range is not automatically code.
  Actual virtual callback/class/provider selection, positive union/child cursor
  composition and global effects remain open; static registration does not
  select a runtime object.
  The selected new-child PickTarget union route now joins its current UInt16
  table index, complete null-cast return, closed wrapper ReadPackable context
  thunk, actual shared helper and full wrapper output/barrier/caller return.
  The same Reader and generic parameter/local-output ownership are retained.
  Old bundle tag ordinals are not reused. The maintained PickTarget storage
  reader now joins its seven source results to inherited/concrete setters and
  the separately owned BlackboardInt and recursive TargetSettings children.
  BlackboardInt's complete ordinary program writes its key, flag and integer
  through the same closed int/int base; VAR indices are resolved through their
  owning generic container instead of being treated as argument ordinals.
  The complete corpus and independent original-element/root replays now validate
  that extension. Exact PickTarget action returns also survive as local receipts
  when their enclosing Timeline element refuses at a following action; this
  grants no enclosing list or root admission. Its named consumer independently
  reads the owned Data key, target and index and forwards the index to GetValue.
  Aggregate/key argument forwarding, evaluated index and target-group effects
  remain separate. Reused-wrapper paths, allocation/refill/error parity, actual
  array/provider selection and gameplay target selection remain open.
  The reached EffectLineCenter child now has independently validated current
  source/setter transfers across AbilityAction, EffectAction and its concrete
  Data. Its current inherited declaration includes `bigEffectTarget`, absent
  from the historical candidate. The complete buffered header and FF output-clear
  return are now proved, and its bounded recursive decoder composes independently
  owned target and effect-configuration values. Actual child wrapper instance
  types must match each closed source context. Original source-element replay,
  the complete current corpus gate and selected canonical root replay have now
  passed with prior admissions retained. The derived action closes additional
  source elements; related partial roots still stop at the positive Timeline
  list boundary. Enclosing list/root admission and observed effect execution
  remain separate.
  The independent consumer contract now proves the closed Data reference and
  fieldless derived receiver, complete preparation caller, conditional byref
  target substitution and disjoint aggregate-buffer forwarding to the complete
  Vector3 subtraction leaf. Under the unpatched caller and both getters' checked
  primary returns, center-position minus source-position is written into the
  unserialized `centerOffset`, distinct from persisted `positionOffset`.
  Ordinary parent `OnCreate` caches the same loaded configuration reference.
  Other getter/IFix paths, reference stability across the action lifetime,
  parent execution consumption and observed effects remain open. Separate
  current Data reloads are not assumed to denote the same object.
  Independent trail point consumers now prove ordered Single deformation and
  twelve-byte writeback, followed by conditional source copying, constructor
  reference stores and append/growth control. Whole no-resize copying requires
  stable source values and valid distinct-header/storage/capacity conditions;
  Selected small/snapshot/bounded-vector, REP and aligned temporal-loop Array.Copy
  paths now have conditional byte-preservation proofs, with explicit memory,
  overlap, runtime stride/selection and parent return/frame/bitset conditions.
  Non-temporal store coverage and ordering before following stores now also have
  an independent proof, now joined to the actual parent array-reference
  publication store and complete getter byte transfer. Old-point reads require
  actual publication visibility and observation, stable compatible references,
  live stride and the existing memory/frame/selection conditions; these remain
  unproved runtime selections. The complete backward-overlap program now also
  has a conditional byte proof, including delayed pipeline stores and every
  tail remainder. All selected copy programs now join the complete actual
  dispatch on one native image, with exact integer-domain coverage and both
  option-false fallthroughs checked. This closes conditional complete store-value
  coverage; only REP additionally requires clear DF, and non-temporal visibility
  retains its explicit boundary. Actual publication/read observation, live stride,
  general old-value preservation during resize, allocation/reference lifetime,
  renderer submission and the parent configuration join remain open. Details
  stay in the owning MemoryPack topic and reviewed consumer contracts.
  TickInterval's existing current Skill normal-source contract and shared Buff
  Sequence declaration provide a concrete parent/child recovery starting point.
  Canonical zero/FF Finder children now have an independent source/type proof;
  recursive Selector routing consumes it with fail-closed native gates.
  TickInterval's complete conditional caller, inherited/concrete setters,
  cached getter, FF return and formatter now join source returns to owned Data
  fields. Its separate helper composition now joins the full physical Sequence
  output and selected buffered primitive sources; the isolated stored-parent
  reader completely replays original parents with independent metadata-boundary
  agreement and unchanged recursive children. It supplies Tick and recursive
  native proofs separately rather than extending a cached validator return.
  The fresh zero-Finder family gate records complete-root gains without source
  drift or regressions. Tick's complete current new-child union output/return
  now has a separate reviewed proof, reusing the existing shared union facts.
  Recursive registration requires both independently owned packets and matching
  current wrapper/Data identities. Fresh complete native context, the full
  family gate and original recursive parent/enclosing source-element replay
  now pass after integration; original source identities and hashes are
  preserved, with no Tick-integration root gains or regressions. Previous
  cached evidence is not relabeled. Native action callback cursor equality
  and positive-list/root admission remain open, along with
  runtime context/provider selection and observed tick effects. The consumer
  lane must prove the generic Data reference and frame/counter/timer guards
  before stating scheduling behavior. The existing SSE lane decoder now
  completely decodes the selected OnTick body, including signed count-to-Single
  conversion; operand ownership and MXCSR/runtime selections remain separate.
  Its separate named consumer claims prove only the false-IFix getter's
  `AlwaysReturnTrue` policy. The strict closed-reference witness currently
  refuses the concrete suffix gap; OnReset uses an Int32-backed ResetReason
  enum, whose receiver/argument forwarding still needs proof.
  Hurt-animation curves share the same recursive Direction owner. Camera-control
  actions compose their named parent, AnimationCurve children and shared
  nullable string-list context; string interpretation remains conditional.
  Other reached children remain refusals until independently proved.
  Resource-cost, timed-marker, stack-storage and scalar-calculation
  parents now have named source/destination proofs and independent typed children.
  GameplayTag width admission requires an explicit closed unmanaged source proof;
    differing registered and optimized reader entries are authenticated separately.
    Skill cooldown, mode switching, super-armor checks and debug printing also
    have named source/destination proofs. Inline color storage requires its
    own source-copy, cursor and destination proof; object size alone is insufficient.
  Stored conditions still do not establish their evaluation.
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
   The shared AnimationCurve reader now names wrap modes and Keyframe words
   through native source/cursor/destination copies; time-dilation and
   hurt-animation parents compose it with independently proved targets,
   direction and Blackboard providers. Shared directions now recursively compose
   independently owned source and target references; unsupported nested target
   variants remain refusals. Their compiled start/stop and animation calls
   are separate consumer evidence, with live argument ownership and effects
   still open. Reuse this curve child when recovering the remaining camera,
   movement parents instead of creating another anonymous
   curve grammar.
   Timed-marker creation and tag/object/physical-infliction conditions now
   compose independently typed providers, targets and queries. The query's
   explicit stack-output-to-field proof distinguishes its runtime extent
   from its variable-length serialized grammar. Reuse that distinction when
   recovering other output-buffer transfers; an instance getter after a
   typed source call is not another source read. Their consumer-call claims
   remain separate from argument ownership, quantifiers and evaluated effects.
   AddTag and ForEach now independently join source-proved tag elements and
   the shared recursive sequence owner. GameplayTag's inline wrapper requires
   an explicit reference-argument-to-receiver projection, rather than boxed
   offset coincidence. SpawnAbilityEntity now composes named recursive fields
   after separate raw12 return-buffer/registered-reader and inline raw16
   cursor/copy proofs. Stored names, targets and lifecycle flags still leave
   tag attachment, iteration order, entity ownership and live effects open.
   CameraImpulse now has independent parent, impulse-definition and inline
   envelope field proofs, including its inline vector cursor and complete
   provider-result-buffer copy. Curves and targets close on original spans;
   evaluated impulse shape, signal lookup and camera ownership remain open.
   NotNextCheckAction's four inherited stored fields now have an independent
   recursive action receipt outside the earlier selected damage pair. Its
   returned control result and the enclosing sequence's interpretation still
   require consumer evidence.
   Selected fieldless condition consumers now independently prove their closed
   generic data reference slot and incoming-instance path to a named target or
   mask read. Reuse this strict witness only for fieldless immediate subclasses;
   classes with their own fields, complete call arguments and evaluated mask
   predicates require separate proofs.
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
