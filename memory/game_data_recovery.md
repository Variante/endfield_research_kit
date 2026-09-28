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

The current full outer VFS audit, complete Bundle inner audit, Table dump, and
JsonData source/export join establish a strong structural baseline for the
selected installed build. Named-schema coverage is narrower: the JsonData
registry still distinguishes exact named roots from bounded LevelScript,
Skill, and Buff interiors. Selected native contracts establish specific
stored-field writers and readers, but no corpus-wide measure of effective
runtime consumers or behavioral/visual reconstruction parity follows from
those file counts. Current denominators and statuses live in the generated
`reports/animestudio/` receipts; the family boundaries are in
[`game_data/extraction_payload_boundaries.md`](game_data/extraction_payload_boundaries.md).

Both ExtendData source-path catalogs now have current cross-format hash joins:
their `Data/` pairs have independently verified VFS filename-hash witnesses,
and their other pairs match BundleManifest asset-path/hash values. The main
catalog equals those sources as multisets; the initial catalog has one
repeated self-path pair and an asset multiset subset. This settles the stored
hash families, including the VFS hash branch at a 128-byte input, while the
catalog writer and runtime lookup remain open. The owning details are in
[`game_data/extend_data.md`](game_data/extend_data.md).

For SkillData, replay of the older accepted live cursor receipt rebinds its
selected logical files to byte-identical current VFS payloads, including
physical relocations, without selecting newly added bytes by analogy. A
separate exact-source capture closes Purrche's second talent. The later
target-set capture observes every reviewed ambiguous source and that prior
exact source as a positive control. Its complete, loss-free v3 receipt selects
each source's terminal at EOF. Native-gated static ActionGroup interiors and
fields through 42 independently match the direct runtime ranges, so the
authenticated full corpus promotes the reviewed target set to exact stored
layouts. The earlier lossy session remains diagnostic and nonpublishable.
Purrche's base combo ability-range source was read on a Potential-3+ save;
the authored below-Potential-3 branch is not thereby proved to execute.
Other partial SkillData files still contain unsupported children. See
[`game_data/serialization_memorypack.md`](game_data/serialization_memorypack.md)
for the gate and residual boundary.

Further native-gated SkillData readers now close reached positive
`DamageUnit` tag lists, three zero-member selector variants, selected timeline
actions, and passive action continuations. Their complete stored layouts are
counted only after the current authenticated corpus gate rejoins each action
interior to field 42 and the source-bound terminal. The generated SkillData
report owns the changing file counts and first refusals.

LevelScript's selected sequential action-map reader now closes populated
`ParamListForGraph` values through the shared native-gated `ParamKeyValue`
codec and continues through the owner at the exact resulting cursor. The
current authenticated JsonData sweep promotes only files that reach physical
EOF; unsupported unions and later owner members retain bounded partial
status. This is stored-schema recovery, not graph execution.
Positive top-level NPC dictionaries now reuse the exact flattened
`NpcRuntimeProxyData` reader already shared by LevelData and atmospheric NPC
data. Current source identities and physical EOF agree for the reached files;
unsupported nested NPC shapes remain explicit stops.
The reviewed reader now also admits selected `OnScriptEnd`, `NpcProxyGetter`,
`BoolGetterOr`, `EntityHide`, and `ResetSummonTeamAI` routes. Selected native
read/setter order, source-hash-checked focused cursors, and the full JsonData
gate establish whole stored files where the owner reaches physical EOF;
other files advance to a distinct later first stop. Their current coverage
is in the generated JsonData report.
A second native-gated batch admits `OnSpawnerComplete`,
`GetMainLevelCameraController`, `EntityAttachToParent`, and
`SetNpcAtmosphericClusterVisible` with the same full-file EOF rule. Their
stored pointers, names, and booleans do not prove runtime event or action
execution.
The selected `DeadZoneDoRepatriate` route now consumes its stored
`Param<float>` through a native-gated action cursor. The current full JsonData
gate admits the newly closed owners only at physical EOF; later stops remain
partial. The generated corpus report owns the changing counts.
Selected native gates now also admit the two snapshot event headers,
`FinishSceneEffect`, and `GetterInt` at exact stored cursors. They check the current build's
dispatcher and ordered readers; source-hash replay and the full JsonData gate
establish which owners reach physical EOF. Runtime event and effect execution
remain separate questions.
The same native-gated PureGetter path now admits `CompareMissionState` and
`EntityCompare`: both have three typed comparison parameters after the shared
node fields, and their current source spans replay at exact cursors. Stored
getter bytes do not establish evaluation or the runtime comparison result.
The selected `GetMissionState` PureGetter route now has the same native and
source-ledger gate for its stored mission-ID parameter. It advances reviewed
action-map cursors; enclosing files still require the corpus EOF gate, and
the stored ID does not establish a runtime lookup result.
The same reviewed route mechanism now covers `NpcProxyPatrolStop` with two
stored string parameters; its current source cursors and whole-owner results
have been checked by the full authenticated corpus sweep.
`StartLevelSeqLoopSegment` now has the same selected-native and source-cursor
gate, including its nested list-of-strings parameter. The full corpus sweep
keeps later union stops partial and promotes only owners that reach physical
EOF.
`EntityEvent.OnBeingScanned` also has a selected-native ActionHeader route:
all inherited fields, four nested parameter contexts and seven current
source cursors validate. The full corpus sweep promotes only enclosing owners
that reach EOF.
`LevelEvent.OnSquadInFightChanged` now has a selected-native ActionHeader
route for its inherited header and boolean output parameter. Current source
spans replay against the JsonData ledger; enclosing files still require
physical EOF. The stored output reference does not report a live combat state.
`LevelEvent.OnMissionStateChanged` now has a selected-native ActionHeader route
for its mission filters and output references, including a finite filter-state
enum. Current ledger-joined source spans replay exactly. Derived root ID and
EOF corroborate framing, while the full reviewed corpus gate decides which
enclosing files are exact. Stored references do not prove a live transition.
`AddTrackingPointForEntity` now has a selected-native ActionBase route for its
six stored parameters, including finite style and tracking-type enums. Current
ledger-joined source spans replay exactly. Derived root ID and EOF checks
corroborate framing; enclosing owners remain partial wherever a later reviewed
union is absent. Stored marker arguments do not prove a live map marker.
`StartCutsceneAndTeleportAction` now has a selected-native ActionBase route
for its stored destination, mask, cutscene, entity-list and streaming
parameters, including a finite teleport UI enum. Current ledger-joined action
spans replay exactly. Whole-owner exactness still requires the full reviewed
corpus gate to reach physical EOF; stored arguments do not prove a live
cutscene or teleport.
`ManuallyStopGuideGroup` now has a selected-native ActionBase route for one
stored string group ID after the inherited fields. Current ledger-joined spans
replay exactly; reached IDs are concrete authored strings. Whole-owner
promotion still requires the reviewed corpus EOF gate, and stored IDs do not
prove a live guide transition.
`RemoveTrackingPoint` now has a selected-native ActionBase route for one
stored string tracking-point ID after the inherited fields. Current
ledger-joined spans replay exactly; the authored IDs have no local parameter
path or reference. The full reviewed corpus gate determines enclosing-owner
status where later fields or unions remain, and stored IDs do not prove a live
marker removal.
`GetIsLeaderInTriggerVolume` now has a selected-native GetterBase route for a
stored current-script pointer and unsigned trigger-slot parameter. Current
ledger-joined spans replay exactly. Enclosing owners still need the reviewed
corpus EOF gate wherever later unions remain, and stored getter arguments do
not prove live trigger-volume state.
`SendLuaEvent1` now has a selected-native ActionBase route with a nested
seven-member value holding an event-name parameter and a JSON descriptor
string. The native reader's nested instance assignment and current
ledger-joined source spans replay exactly; unresolved inner positions retain
neutral names. A stored event name does not prove runtime firing.
`StartSubGameCountDownByTimer` now has a selected-native ActionBase route for
a finite countdown enum, an output handle, a current-script pointer and a
timer ID. Its current ledger-joined spans replay exactly; enclosing owners
still require the full corpus EOF gate where later actions remain. Stored
timer arguments do not prove a live countdown.
`ShowStartToast` and `StopSubGameCountDownByHandle` now have selected-native
ActionBase routes with exact current ledger-joined source spans. The former
stores two localization keys and two names; the latter stores a handle path
that joins a countdown output handle in the same serialized owner. Later
unions still bound these enclosing owners, and stored links do not prove a
live toast or countdown.
`ShowFinishToast` now has a selected-native ActionBase route for two
localization keys, an icon name and a boolean success field. Its current
source spans replay exactly. The enclosing race action maps also contain
later headers, now covered by reviewed routes. The stored false success value
does not prove a displayed toast.
`ToggleMainHudActionPlayIgnoreMainHud` now has a selected-native ActionBase
route for its action-type string and boolean parameter, with exact current
ledger-joined source spans. Reached owners advance to later chapter-panel
unions; their stored true values do not prove runtime HUD behavior.
`ShowChapterPanelDirect` now has a selected-native ActionBase route for its
finite chapter-effect enum, chapter ID, continuation flag, and version string.
Its current ledger-joined spans replay exactly; some enclosing owners reach
physical EOF while another still stops at a later header. The corpus gate
decides whole-owner promotion, and stored fields do not prove display.
`ShowChapterCompletedPanel` has a separate selected-native branch with the
same four stored chapter parameters. Its ledger-joined spans replay exactly,
including the reached owner after the HUD-action route. Production framing
reaches script ID and physical EOF for the reached owners; the corpus gate
still decides whole-owner promotion.
`SwitchToCamera` now has a selected-native ActionBase route for its camera
output path, blend controls, and optional look-at and spawn fields. Its
ledger-joined source spans replay exactly, including non-null output paths;
the reached owners continue to later camera actions. Stored fields do not
prove a live camera transition.
`StartTrackCamera` and `ExitCamera` now have separate selected-native ActionBase
routes for their stored tracking and blend controls. Their ledger-joined camera
chain spans replay exactly; some reached owners close to script ID and physical
EOF while later unions still stop others. The corpus gate decides owner-level
promotion, and stored fields do not prove runtime camera behavior.
`ResetFollowCamera` now has a separate inherited-only selected-native branch.
Its ledger-joined spans replay exactly, with several reached owners closing to
script ID and physical EOF. Remaining owners stop at other unions; whole-owner
promotion awaits the corpus gate.
`FacSetInteractLockedState`, `ToggleClearScreenButRadioV2`, and
`RemoveNPCDialog` now have separate selected-native ActionBase routes with
ledger-joined exact source spans. Reviewed framing reaches ID and physical
EOF for some enclosing owners; later unions still block others. The corpus
gate remains the whole-owner promotion boundary, and these stored parameters
do not prove runtime effects.
`ScriptEvent.OnLeaderEnterTriggerVolume` now has a selected-native
ActionHeader route with exact ledger-joined source spans. Its stored slot
filter and nullable output complete the reached race action maps alongside
the already reviewed leave header. Derived roots reach script ID and physical
EOF; the full corpus gate decides final whole-owner promotion. A stored
header does not prove a live trigger-volume event.
The selected-native `PostAudioStatusEvent` ActionBase route now validates its
stored trigger flag and two audio event names, with source cursors joined to
the current JsonData summary and ledger. The full corpus EOF gate remains the
owner-level promotion boundary; stored audio event names do not prove playback.
The selected-native `SetEntitiesVisibility` route authenticates the two
boolean parameters, populated entity-pointer lists, and the finite
`ModelVisibleType` parameter at current source cursors. The shared reader
requires that native gate, while owner-level exactness still depends on the
full JsonData EOF gate. Stored visibility settings do not prove a live change.
The `WaterVolumeInfiniteSetHeight` ActionBase route now has a selected-native
stored layout: two boolean parameters, an eight-byte water-volume pointer, and
a float parameter. Its source spans replay at reviewed cursors, while
whole-owner promotion still requires the JsonData EOF gate. These authored
settings do not establish a runtime water-height change.
The selected-native `SetFacMode` route adds one stored boolean parameter after
the inherited action fields. Current source spans replay at reviewed cursors;
the full JsonData gate decides which enclosing files close at EOF. The flag
does not establish a facility state transition.
The selected-native `EnemyPatrolStart` route closes its stored patrol ID and
current constant target-pointer values at ledger-joined source cursors. The
enclosing file advances only if the full JsonData gate reaches physical EOF;
the stored arguments do not prove a runtime patrol transition.
The selected-native `EnableTyphoeaArcheryStage` route now authenticates its
stored level ID, module and script pointers, and stage index. Ledger-joined
source cursors replay exactly. Enclosing LevelScript files still require the
full JsonData EOF gate, and stored arguments do not prove runtime execution.
The selected-native `TyphoeaArcherySetChipId` route authenticates two stored
string parameters after the inherited action fields. Its ledger-joined source
cursors replay exactly, with the shared reader gated on the current native
build. Enclosing LevelScript files still require the full JsonData EOF gate;
the stored IDs do not prove live chip selection.
The selected-native `FinishBuffs` route authenticates one stored
`Param<List<BuffPtr>>` field. Current source cursors contain only null-list
values with local parameter paths; positive list elements remain unsupported.
The selected reader can carry some enclosing files to physical EOF while
others stop at later unreviewed unions. The full JsonData gate decides
whole-file promotion, and stored fields do not prove live buff effects.
Positive `taskMap` entries are a separate LevelScript frontier. The current
sequential reader can reach the task-map header after an exact action map but
stops at unreviewed condition unions inside the entries. A derived root can
walk these stored files to EOF at the direct tier; exact promotion requires
selected condition readers and a complete enclosing task-map cursor.
The selected GameCondition readers now cover the reached monster-spawner state,
snapshot-identification, SNS-dialog completion, and main-HUD conditions. Their
stored fields and current source cursors are authenticated, allowing the
sequential task-map reader to promote files whose remaining entries and final
trigger-volume map reach physical EOF. Other condition variants remain at the
same explicit stop; stored conditions do not prove runtime evaluation.
The next selected task-map set closes the reached map-variable, team-count,
remote-communication, interactive-activation, factory, HUD, technology,
and LSM conditions through authenticated native reader order and source
cursors. The interactive-submit reader's chained continuation now establishes
its ordered entity-pointer, expected-success, and level-string parameters.
Its reached source spans and enclosing sequential root close at physical EOF;
the full JsonData gate remains the publication check for exact corpus status.
Stored conditions do not establish runtime evaluation.

A current source-byte and VFS gate now joins stored `PlayFmvAction.moviePath`
values to installed Video files. The selected native path conditionally selects
an `f_` or `m_` name and falls back to the base id. This joins authored naming
to an installed carrier, not an activated Story scene or observed playback;
the source, Video and native boundaries live in
[`game_data/story_carriers.md`](game_data/story_carriers.md).

The CompressData archive has a selected native path from a compressed
BehaviourTree's stored graph index to an archived JSON body. An exported Unity
object gate also joins authored BehaviourTree source-CAB/PathID identities to
archive ordinals under the export summary's freshness fingerprints. A further
keyed export join follows AssetBundle container paths, AI-config blackboard
pointers, and managed-reference graph-mode pointers to those BehaviourTree
identities; exact `EnemyTable.aiTemplateId` equality reaches unique AI-config
objects for a checked subset. A selected native chain copies
`SCENE_MONSTER.commonInfo.templateid` into `EnemyServerData.enemyId`, transfers
the server data through typed entity-spawn calls, then uses the enemy ID for
the `EnemyTable` lookup. On its successful synchronous path it reads
`aiTemplateId` and loads the formatted `AIConfig` path. The authored gate
checks stored Table row keys against `enemyId`. A separate current-source gate
now joins each authored tag-5 SpawnerConfig monster action's `libraryKey` to
one same-file enemy-library entry; selected native code can retrieve that
entry through server object ID and action ID and load its AI override. The
checked initialization branch also reads separate born-template and behavior
overrides from that item, without reading its stored `enemyId`. It copies
protocol `monsterLibraryKey` separately from `templateid`.
No checked producer equates the selected library entry's stored `enemyId`
with the protocol `templateid`. The export does not
independently authenticate each Unity object's bytes against the current VFS.
The source and selection of a live protocol message or installed spawn
record, alternate paths, scene selection, and live execution remain open. See
[`game_data/extend_data.md`](game_data/extend_data.md).

A corrected AssetMap exporter now reproduces authored container paths for the
previous fallback no-dependency residuals. Those corrected paths resolve to
the physical Bundle in both manifests; the old mismatch was a label artifact,
not a demonstrated Bundle ownership conflict. The historical cause of a small
UI-label subset remains open. See [`game_data/unity_assets.md`](game_data/unity_assets.md).

The current CAB dependency sweep places every selected mapped serialized
external reference inside the BundleManifest's direct-dependency list. Four
manifest-only edges remain; selected synchronous and asynchronous Bundle
loaders both read that list and recurse through it. The producer of those
extra edges and a live selected load remain open. A current object-index gate
joins one `unity default resources` external by source slot and PathID to a
unique installed Mesh object; runtime resolver execution is still unobserved.
The separate unknown-CAB external retains no installed Resources object match.
See [`game_data/extraction_payload_boundaries.md`](game_data/extraction_payload_boundaries.md)
and [`game_data/unity_assets.md`](game_data/unity_assets.md).

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
  Marker17 body profiles are structurally closed but anonymous. A current
  selected-scene gate isolates 16-byte physical gaps at some Marker15 targets,
  but those gaps do not establish a general record extent, producer, or field
  ownership. Its directory is bounded, not its records; missing count keys
  remain unsupported.
  Paired Init/Streaming paths, serialized ordinals and ordered witnesses do not
  prove concrete runtime root/key receipt, fresh key state, absence of overrides
  or execution. Native Info provenance is conditional, not a concrete record.
  Keep field namespaces and runtime semantics behind those gaps. Terrain now
  has an authored `_ConeMaps` shader input and direct sample witness beside
  the selected `LAYER_C` property-binding route; its managed field join,
  installed-file/shader runtime selection and encoded channel meaning remain
  open. Then DynamicStreaming's other nested main records,
  auxiliary fields beyond the now-proved descriptor-21 stored name prefix and
  live grid/area selection,
  irradiance supplied-root/VFS identity, selected read provider, and room
  record semantics; BundleManifest cross-store object identity beyond the now
  authenticated CAB dependency projections and live lookup,
  mmap, patch execution, and remaining JsonData body semantics.
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
  The clean target-set receipt observes every reviewed source, including
  Purrche's base combo variant on a Potential-3+ save, and selects its
  terminal directly after field 42. This is a stored-read witness; it does
  not establish that gameplay selected the authored below-Potential-3 branch.
  The reviewed target-set sources now have a native-gated static action
  interior that rejoins each observed field-0 endpoint, and the full corpus
  promotes them to exact stored layouts. Other partial files need their own
  supported action children before the same promotion is possible.
- Continue BuffData recursive naming from the corrected compact stacking and
  timeline joins. The selected native readers now own the signed-length
  `stackingKey`, two-byte `stackingType`, following raw GameplayTag array, and
  empty `timelineActions` list through the trigger tail. Positive timeline
  bodies still have structural endpoints; anonymous action interiors and
  positive modifier children need recursive ownership proofs. The selected
  `DamageScaleProcessor` child now has native-gated direct field names,
  a selected BlackboardDouble interior, exact raw `zoneName` byte framing,
  and parent-span rejoining. The condition-free and selected one-action
  `CheckDamageDecorateMask`, `CheckDamageType`, `CheckDamageTypeMask`, and the
  selected simple `CheckTagMatch`
  cohorts now have exact stored
  condition and processor children, including selected tag-ten `ModifyCalcResult`
  processors with both exact BlackboardDouble interiors and selected scalar
  processor tags zero and three with one exact BlackboardDouble interior, and a 30-member root
  reader that continues on original bytes through physical EOF. Other processor
  and condition-action branches
  remain open. The
  shared selector child gate also has exact receipts for the selected
  zero-member `CharacterTeamFinder` tag-2 branch and the one-member
  `OwnerSpawnedEntityFinder` tag-13 branch. The selected validator routes
  close zero-member tags 5 and 9 and tag 11's direct `query` member with a
  structurally framed `GameplayTagQuery` body. Other positive finder bodies
  and runtime validator behavior remain open.
  Action-wrapper receipts may be shown as bounded spans in the debug Inspector.
  The sole `CreateBuffAction` branch additionally has selected native child
  ownership for its two-member icon duration setting, input/assignment list,
  BlackboardDouble count, and the reached target, direction and selector
  children. A narrow root reader admits that action only when the other root
  collections are covered; it replays the original bytes through all 30 fields,
  stored source ID and physical EOF. Other action lists remain partial.
  The selected `SetSuperArmorAction` receipt now also owns both direct
  four-member blackboard children; its target settings and runtime application
  remain separate questions.
  A strict selected cohort now has native ownership of all 30 root reads and
  child layouts, contiguous byte-zero-to-EOF receipts, source-ID equality,
  and independent JsonData replay. It includes the empty-recursive-list branch,
  a bounded positive DataPair plus GlobalModifier branch, and the selected
  damage branch with an empty condition or one selected
  `CheckDamageDecorateMask` or `CheckDamageType` action and one selected tag-five
  or tag-ten processor, one `CheckDamageTypeMask` action with one tag-five
  processor, or one simple `CheckTagMatch`, `CheckMainCharacterCondition` or
  selected `CheckBuffStackNumAdvanced`, simple `CheckHp`, or simple
  `CheckPoiseValue` action with one tag-five processor.
  `CheckBuffStackNumAdvanced` also admits the selected tag-nine processor.
  One `CheckDamageDecorateMask` action also
  admits one selected scalar processor tag zero, two or three; a simple
  `CheckTagMatch` action admits scalar tag zero or three. An empty condition with ordered
  tag-five/tag-six processors and the ordered
  `CheckDamageDecorateMask`/`CheckDamageTypeMask` condition with one tag-five
  processor also close the root. Four narrowly selected compound conditions
  also close the root with one tag-five processor: the two OriginSkillType
  combinations (one with nested OrConditionAction) and the ordered
  StackNumAdvanced/DamageType and DecorateMask/StackNumAdvanced/TagMatch
  combinations. Two nested IfElseAction combinations with selected
  CheckMainCharacterCondition, empty failure actions and ReturnFalseAction
  close with tag-five processors. The ordered NotNextCheckAction and
  CheckMainCharacterCondition combination closes with the selected tag-four
  DamageIndependentHealthProcessor and its exact BlackboardDouble child.
  Two selected CheckTwoDirectionAngle actions, each with four simple target
  children and one BlackboardDouble value, close with the ordered tag-five and
  tag-six processor pair through the same 30-field root, source ID and EOF.
  The sole selected CreateBuff
  action branch is also exact. The remaining BuffData files keep their
  recursive blockers. The high-yield next offline cohort stops at positive
  `damageModifier` children with other condition actions and processor
  interiors, or at anonymous event-action interiors. Four reached
  `ModifyDynamicBlackboard` children now have exact nested target and
  BlackboardDouble spans, while their two compound roots remain partial.
  The two selected damage
  sources with positive `attributeModifier` need a separate child proof.
  Current counts and source identities remain in the generated
  BuffData and JsonData corpus reports.
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
  SDK/native gate types twelve stock effect families. Direct registration and
  vtable paths now bound the proprietary Convolution Reverb and Mastering Suite
  parameter reads structurally, while their field meanings remain opaque.
  Remaining value naming,
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
