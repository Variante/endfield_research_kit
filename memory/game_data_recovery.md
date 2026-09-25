# Game-data recovery

This topic owns durable conclusions about installed data formats, gameplay and
audio semantics, native consumers, and the source graph. It does not own WebUI
presentation, page build commands, or AnimeStudio implementation mechanics.
This file is the topic's entry point; the per-family evidence lives in
[`game_data/`](game_data/README.md).

## Why this topic remains

The WebUI page guides explain how recovered data is published. This topic is
still required because many evidence contracts are shared by several pages or
exist before any page projection: overlay behavior, binary framing, native
build gates, runtime/static distinctions, and cross-domain graph provenance.

## Refresh and evidence rules

```bat
python -m scripts.game_data.extraction.verify_export_freshness
.\export.bat --from-game
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

- StreamingAssets is the fallback; Persistent is the active overlay. Changed
  logical paths replace their fallback file as a whole unless a format-specific
  contract proves record-level merging.
- Native claims require the selected `GameAssembly.dll` plus
  `global-metadata.dat` gate. Missing or mismatched inputs skip that evidence
  and leave the last validated report untouched.
- Metadata default blobs require their primitive backing type. Applying the
  signed compressed-`Int32` decoder to a byte-backed enum invents negative
  values from ordinary byte IDs. Resolve the backing type from the selected
  MetadataRegistration before using those IDs; the native enum helper supports
  reviewed byte and `Int32` cases and fails closed on other types.
- A source-only classifier must not inherit that gate merely because native
  evidence once motivated its interpretation. The maintained direct gate
  callers are limited to current runtime-capture identity, metadata enum reads,
  and consumers of pinned methods, code windows, field offsets, registrations,
  or native contracts; current-export Story classifiers validate their own
  tables, object-index stage signatures, and source fingerprints instead.
- **`inputSetSha256` identifies one audit run, not the game build.** It covers
  the exporter binary and the absolute asset roots, so rebuilding AnimeStudio
  or moving the install changes it with the game data untouched. It is
  therefore only a join key between the generated artifacts of one run -- the
  VFS audit summary, its ledger, and the corpus reports built from them -- and
  a fresh audit regenerates every side together. No tracked contract is gated
  on it and no reader decodes differently because of it; whether a contract's
  rows apply is decided by its `nativeInputs` against the installed build, and
  by the corpus gate that validates those contracts before it decodes.
- Hash checks survive only where they guard something git does not: the
  installed build against `nativeInputs`, native code bytes against a recorded
  window or body hash, installed game files such as the iFix patch, and a
  generated report against the inputs it was built from. A contract's own
  bytes, one contract's hash recorded in another, and Python restating a
  contract's values are not gates, because git already owns tracked files.
- A test must not hardcode an `inputSetSha256`: it changes on every exporter
  rebuild. Read it from the fixture's own audit summary.
- A field name, code address, registration order, hash collision, filename,
  proximity, or available asset is not ownership or runtime execution.
- Preserve source root, logical path, file hash, record offset, parser/schema
  version, and validation status through every join.
- Exact parsers require bounded positive fixtures, malformed/truncated/trailing
  negatives, exact consumption, and a current-corpus sweep.
- Build-specific counts, hashes, tokens, addresses, and full inventories belong
  in reports or versioned code contracts.

## Re-resolving a native identity after a client update

A contract that pins a superseded build is not evidence that its subject is
gone. Only the *managed name* survives an update, so a stale contract is
migrated by resolving its names against the selected build, never by carrying
an address forward. `scripts/game_data/il2cpp/method_resolver.py` owns that
direction. It pins nothing: it derives `Il2CppCodeRegistration` from the
selected `GameAssembly.dll` against the complete image-name set of the selected
`global-metadata.dat`, so it runs unchanged on a future build, while every
consumer holding a recorded registration address fails closed on the next one.

Three name classes drift without any source change, and each needs its own
route rather than being read as a deletion:

- **Compiler-generated closures.** `<Owner>b__<ordinal>_<index>` carries the
  declaring method's slot in `ordinal`. Adding any method above the owner
  renumbers it. Resolve by owner plus lambda index; the index is stable.
- **Burst direct-call wrappers.** `<Kernel>_<token>$BurstDirectCall` is named
  after the wrapped job's metadata token, which renumbers on every update.
  Resolve with the token wildcarded, accepting only a unique hit. The drift is
  an insertion, not a reshuffle, which is the cheap cross-check on a wildcard
  match: across the nine wrappers the lab records, every token moved by one
  identical offset, each resolved independently by name.
- **Recorded display forms.** `Execute(int)` and `SetCustomPerDrawData<T>` are
  not metadata names. Strip the decoration, and use the recorded parameter
  types only to separate overloads -- a partial or unrecognised spelling leaves
  the ambiguity visible instead of selecting one.

A resolved body extent is the gap to the next method pointer: an exact bound on
the region, an upper bound on the instructions, not a proven function length.
Re-resolution restores identity and address only; the bytes usually changed, so
the old contract's conclusions about them stay unvalidated until re-derived.

## Installed-data model

The installed client exposes overlapping logical data through VFS catalogs and
payload roots. Maintained readers cover Unity bundles and AssetMaps, structured
Tables and JsonData, video, audio, Terrain, Streaming/DynamicStreaming, selected
ExtendData families, and native-gated contracts. A verified outer VFS boundary
proves byte identity and availability, not the inner payload schema.

Stable cross-format rules:

- Unity object identity is source/CAB plus PathID. A global PathID or basename
  is never sufficient.
- Table ids and localized strings are authored values; they do not by
  themselves prove a runtime consumer.
- Serialized TypeTrees are preferred when exact. `$partial`, `$unparsed`, and
  `$inferred` remain visible and must not be upgraded by a later name match.
- Runtime-mutable properties preserve their authored initializer but cannot be
  treated as final action targets without excluding later writes.
- Exact spatial transforms prove authored placement, not spawning, activation,
  visibility, or interaction.

## Where the detail lives

[`game_data/`](game_data/README.md) holds the per-family evidence, organised by
**level** (how deep the interpretation goes) and **lane** (which kind of data).
This file keeps what every one of them depends on -- the refresh and evidence
rules above, the installed-data model, the shared asset/spatial and source-graph
contracts below, and the topic-wide remaining gaps.

A level can only be asked once the one below it is answered, and a claim may
cite evidence only from its own level or below:

| Level | Question it answers |
| --- | --- |
| **1. Where the bytes are** | Which block, which reader, which container? |
| **2. How the bytes are framed** | Where does a record start and end, and is the file consumed exactly? |
| **3. What the fields are** | Which field is a count, offset, enum or matrix -- proven outside the bytes? |
| **4. What it means** | What does a record own, name or reach in the game? |

Most wrong conclusions recorded there came from reading a level-4 meaning off a
level-2 framing -- a field name, an address order, or a filename standing in for
a proof.

The client's own `EndfieldVfsBlockType` enum is the authoritative list of what
the installed data contains. `game_data/` documents **world** (`Streaming`,
`DynamicStreaming`, `Terrain`, `IV`), **audio**, **gameplay** (the `Table`
Buff/Skill subset), **catalog** (`ExtendData`, `BundleManifest`), **Unity
assets** (`Bundle`, `Video`), and **code** (`IFixPatchOut`). An **extraction** lane
owns the AnimeStudio reader itself plus how far each family's reader is proven.
A **story** lane sits beside them with no block of
its own: [`game_data/story_carriers.md`](game_data/story_carriers.md) owns what
a serialized LevelScript action, Timeline record, or spatial carrier proves
about Story activation and placement. Two cross-lane files sit beside them for the
serialization framework (MemoryPack and its IL2CPP formatter resolution) and the
native read path down to `ReadFile`. Unity asset identity is in
[`game_data/unity_assets.md`](game_data/unity_assets.md), with the container
index in [`game_data/containers_cabmap.md`](game_data/containers_cabmap.md).
The selected-build main-grid vector widths, area records, and authored area
index relations in DynamicStreaming belong to
[`game_data/world_dynamic_streaming.md`](game_data/world_dynamic_streaming.md).
Only **text** remains elsewhere: `Table` text and `JsonData` conversations are
presentation-facing and belong to
[`webui/story_recovery.md`](webui/story_recovery.md). IFix replacement-target,
VM operand, and external-signature evidence, with its patch-currentness boundary, is in
[`game_data/ifix_patch.md`](game_data/ifix_patch.md).
[`game_data/README.md`](game_data/README.md) carries the full block-to-lane table.

Read [`game_data/settled_and_open.md`](game_data/settled_and_open.md) before
reopening `InitChunkData`/`StreamingChunkData` slot typing or HIRC type
coverage. It records the conclusions a later session should not re-derive, and
the inherited blockers that turned out to be misdiagnosed on re-test.

Per-build member orders belong in their tracked `scripts/game_data/contracts/*_native.json`
contracts, not in memory prose. The gameplay lane is the worked example: 213
per-tag Buff action layouts live in their contracts, and
[`game_data/gameplay_semantics.md`](game_data/gameplay_semantics.md) keeps only
the root framing and the rules every contract shares.

The story lane's code sits on this side too. The serialized-gameplay readers
(`scripts/game_data/levelscript_binary.py`, the other `*_binary.py` readers and
their `codecs/`) and the reviewed native facts that Story, Mission Pipeline and
Map consume (the `scripts/game_data/*_native.py` loaders) are installed-data code, and
those builders import them rather than decoding bytes themselves. The
conclusions do not move. What a decoded carrier proves stays in
[`game_data/story_carriers.md`](game_data/story_carriers.md), and what it
means for published Story stays in
[`webui/story_recovery.md`](webui/story_recovery.md).

## Asset and spatial semantics

AssetMap rows, PPtrs, prefab/component dependencies, material slots, textures,
controllers, clips, effects, and scene records form an evidence chain. A later
link must retain the earlier physical identity and cannot be substituted by a
normalized-name match.

World registries, LevelData, streaming matrices, NPC proxies, authored pins,
and trigger geometry use separate identity domains. Script-wide context and
proximity never fan out to sibling slots. Dynamic getters and runtime lists are
non-spatial unless a pinned producer proves one immutable authored target.

Semantic asset ownership belongs in
[`game_data/unity_assets.md`](game_data/unity_assets.md);
Map publication belongs in [`webui/map.md`](webui/map.md).

## Source graph

Canonical database:

```text
reports/source_graph/endfield_source_graph.sqlite
```

The graph indexes evidence already produced by owning builders. It is a query
and provenance surface, not an authority that may invent new recovery logic.

```bat
python tools\endfield_source_graph.py query IDENTIFIER
python tools\endfield_source_graph.py story STORY_KEY --limit-lines 8
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Default builds retain only exact AssetMap rows consumed by WebUI material,
shader, texture, and FMV edges. Full builds are for exhaustive Unity
object/PathID investigation. Every edge keeps an evidence kind; availability,
registration, address order, and mission environment context never become
ownership or chronology.

Before deleting or renaming a generated report, search graph readers and rebuild
the database if that report is an input.

## Diagnostics

Use the closest owning report first:

```text
reports/export/
reports/animestudio/
reports/assets/
reports/audio/
reports/source_graph/
reports/story/build/
reports/story/recovery/
```

Revisitable format probes belong in `scratch/<topic>/`; disposable extraction
and before/after evidence belongs in `tmp/<topic>/`.

## Remaining gaps

- Streaming's next advance requires independent record-end evidence or a
  bounded runtime carrier witness. Keep selector9 held until its component
  mapping indices and write span are authenticated; do not repeat anonymous
  load-width or target-distance statistics. Multi-target clusters need extents;
  neither zero values nor a loop skip establishes validity or sizeof.
  Marker13's observed gap profiles are anonymous, and serialized absence is
  not a numeric selector.
  Marker17 body profiles are structurally closed but anonymous. Marker15 still
  needs a concrete producer, source extent or independently bounded unread
  region: repeating a 16-byte native load does not prove record size. Its
  directory is bounded, not its records; missing count keys remain unsupported.
  Paired Init/Streaming paths, serialized ordinals and ordered witnesses do not
  prove concrete runtime root/key receipt, fresh key state, absence of overrides
  or execution. Native Info provenance is conditional, not a concrete record.
  Keep field namespaces and runtime semantics behind those gaps. Then Terrain
  block/channel semantics, DynamicStreaming's other nested main records,
  auxiliary fields beyond the now-proved descriptor-21 stored name prefix and
  live grid/area selection,
  irradiance supplied-root/VFS identity, selected read provider, and room
  record semantics; manifest,
  mmap, patch, and JsonData body semantics.
- Continue Streaming nested element/byte-body framing using the bottom-up
  queue below, whose current Streaming framing state is in
  [`game_data/world_chunk_slots.md`](game_data/world_chunk_slots.md).
  Init slot 7 now has a selected native descriptor-major byte consumer with a
  log-only extent comparison. A current complete-corpus gate proves that
  descriptor 21 stores each paired root name's first 63 bytes under the same
  ID; long suffixes are absent from the slot. Other component labels, a
  concrete runtime root/file receipt, and the large unread run remain open.
  Further field names follow structural closure, not the reverse.
- Continue SkillData action-union recovery after the reviewed timeline
  shared-sequence reader. It now walks every later timeline record only while
  all reached routes match the current native contract, and otherwise retains
  the exact first-record prefix. It also handles positive passive action maps
  followed by an empty timeline list when every reached route is admitted.
  A complete ActionGroup can rejoin the selected top-level terminal;
  unsupported action children, other ActionGroup shapes, and runtime
  execution remain open. The corpus now retains positive passive and shared
  timeline reader first refusals explicitly. It classifies a physical action
  tag only when the reader fails at a union-tag check, so nested counts and
  profile markers cannot masquerade as routes. Current coverage is in the
  generated SkillData corpus report, with the evidence boundary in
  [`game_data/serialization_memorypack.md`](game_data/serialization_memorypack.md).
- Continue BuffData recursive naming from the corrected compact stacking and
  timeline joins. The selected native readers now own the signed-length
  `stackingKey`, two-byte `stackingType`, following raw GameplayTag array, and
  empty `timelineActions` list through the trigger tail. Positive timeline
  bodies still have structural endpoints; anonymous action interiors and
  positive modifier children need their own recursive ownership proofs.
  Action-wrapper receipts may be shown as bounded spans in the debug Inspector,
  but they do not make the enclosing BuffData file a complete named schema.
  Current coverage is in the generated BuffData corpus and child receipts;
  the durable boundary is in
  [`game_data/serialization_memorypack.md`](game_data/serialization_memorypack.md).
- Recover more exact gameplay action/selector/formula contracts without
  treating native names as byte-layout proof. Selected `DamageUnit` enum fields,
  calculation subtype identities, and two subtypes' enum parameters now close
  across exact Skill/Buff records. A separately authenticated, unpatched
  `MultiplyAttributeCalculation.Evaluate` body computes selected attribute
  times resolved multiplier plus addition. A separate unpatched
  `AtkScaleCalculation.Evaluate` body multiplies attacker ATK by resolved
  `atkScale`; `DefiniteValueCalculation.Evaluate` returns a resolved value,
  optionally multiplied by a resolved scale. The selected unpatched
  `BreakingAttackCalculation.Evaluate` body combines attacker ATK, defender
  break-damage scalar, and two resolved multipliers with explicit
  Single/Double conversions. The selected normal-entity DamageAction caller
  now proves the snapshot/simple/calculation selector and the simple
  `attackerAttributes[2] × resolved unit atkScale` intermediate; stored
  evaluator subtypes may be bypassed by the simple branch. A separate
  `_ProcessDamage` caller now joins a nonnull stored `poiseCalculation` to the
  intermediate `PoisePackData.calcResult` after a before-calculation modifier;
  the selected `DefiniteValueCalculation` evaluator gives its conditional
  resolved-value expression. A further selected Poise result contract proves
  after-calculation modifiers, output/taken Poise scalars, signed modifier
  construction, and the guarded controller path that converts Double to
  Single and records a readback `realDelta`. The selected slot-87 vtable census
  finds five AbilitySystem types using base `ApplyModifier`; the God override
  returns failure on its unpatched branch. Runtime receiver identity, live
  invocation, calculation subtype selection, patch state, provider values,
  final damage, and an observed
  character-specific applied Poise amount remain unresolved.
- Audio: the HIRC layout and shipped decision-tree traversal are structurally
  closed against the Wwise SDK and current bank corpus. A current-build
  SDK/native gate types twelve stock effect families; proprietary Convolution
  Reverb and Mastering Suite parameters remain opaque. Remaining value naming,
  other plug-in blocks, and a host process for layers 5 and 6 remain in the queue
  in [`game_data/audio_overview.md`](game_data/audio_overview.md). Keep closing
  authored and observed consumers through exact Event/media traversal while
  preserving runtime branch and audibility gaps.
- Audio's native catalog was reviewed on the previous build; on another
  build `scripts/webui/audio/semantics/native_callsite_rederivation.py`
  re-proves it by name (callsites, voice routes, music groups and
  transitions, selector setters, timeline and footstep anchors, ModelView
  routes). Still open: the playback call chains (their links are delegate
  callbacks, native engine stages and sibling entry points, which need a
  per-relation model, not a linear call check), the callsite rows withheld
  for real code changes (literals moved into config classes, one sink no
  longer reached), and static selector fields at offset 0, which need the
  type's static-storage load proved before a bare dereference counts.
- Improve exact prefab, renderer, material, animation, and world-instance
  ownership.
- Keep native gates and source-graph provenance deterministic across client
  updates.
