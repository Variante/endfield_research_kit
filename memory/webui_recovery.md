# WebUI Recovery

The static WebUI is recovered from an installed Endfield client through the
repo's active export/build pipeline. This note keeps the durable recovery
conclusions in one flat file; user-facing usage stays in `README.md`, script
contracts in `scripts/README.md`, and frontend scope in `webui/README.md`.

## Canonical Refresh

From the repo root:

```bat
.\export.bat
python serve.py
```

`export.bat` currently:

1. reuses the existing `export_full/` by default;
2. verifies `export_full/` freshness against the installed game data;
3. rebuilds `export_full/recovered/dialog_id_table_index.json`;
4. rebuilds narrative video/source-link evidence;
5. builds CN Story and Reference data;
6. builds the experimental Mission Pipeline plus the authored Progression,
   Projectile, Factory, and World semantic views;
7. leaves asset indexes and CN audio relinking to `export_assets.bat` unless
   `--with-assets` is passed;
8. rebuilds the local source graph after any requested asset/audio work, keeping
   only original AssetMap rows required by WebUI material/shader/texture/FMV
   edges by default;
9. builds Presentation and Combat from the fresh graph, with Combat also using
   direct AnimeStudio evidence; and
10. leaves the OCR-managed Story order override untouched.

Use `--full-source-graph` for an exhaustive investigative AssetMap graph. Use
`--mission-pipeline-only` for the Story/Mission Pipeline recovery loop; it
preserves the normal Story/Text Tables build but stops before unrelated semantic
views and graph work. If Story sidecars are already current, running
`export.bat --mission-pipeline-data-only` or
`python scripts\build_mission_pipeline_data.py` directly refreshes the current
490-mission graph in a few seconds without rerunning Story/evidence/graph stages.
When Story relation code changed but `export_full/` and the recovered Timeline
inputs did not, `export.bat --mission-pipeline-only --reuse-timeline-orders`
keeps the full Story normalization pass while skipping Timeline recovery. The
wrapper rejects that reuse flag with `--export-from-game` and with the
Story-free data-only mode.
If exported Table inputs are also unchanged, `--reuse-reference` validates the
existing localized reference index and all indexed files, keeps the Text Tables
page available, and avoids rebuilding 67.1 MB across 538 tables. It is likewise
rejected for installed-game refreshes and for the Story-free data-only mode.
Selective AnimeStudio evidence scans now use native filtered filename
enumeration and cache repeated patterns: the exact DialogTree `dlg_*.json` scan
fell from about 72 seconds to 0.4 seconds, Timeline action candidate enumeration
fell to about 6.5 seconds, and FMV binding recovery fell from about 269 seconds
to about 32 seconds with identical non-timestamp output.

Narrative-video recovery also consumes exact typed LevelScript
`PlayFmvAction` target fields. The WebUI treats those as authoritative only
when the native field mapping and normalized `cutscene_*` key agree, preserves
the LevelScript source details in the cutscene debug payload, and may create a
cutscene card that was previously only a source-side Mission Pipeline node.
The current CN build exposes 298 cutscene cards and 53 video-attached Story
keys; 180/188 video references are attached. Gender-prefixed FMV files inherit
only an already-proved canonical base binding.

The 2026-07-21 CN Story build profile found repeated LevelScript path
resolution/decoding, all-pairs weak spatial checks, duplicate LevelScript file
reads, repeated DialogTree JSON parsing, an accidental recursive scan below an
already exact MonoBehaviour root, and expensive all-pairs text similarity.
Lexical source caches, a threshold-equivalent spatial grid, a per-level dialog
catalog, immutable shared DialogTree payloads, exact SequenceMatcher upper
bounds, selective Windows filename enumeration, and lazy Timeline PathID
resolution reduced the canonical CN lean build from the prior 314–338 second
range. The current AnimeStudio lookup indexes the complete small TextAsset
roots plus the complete authored DialogTree/timeline/cutscene filename families
in the million-file MonoBehaviour roots; non-family assets use an exact
PathID-stripped stem lookup. This removes the broad 1.2-million-file filename
pass without turning missing gender variants into thousands of individual
scans. The original-data-complete run with
`--timeline-recovery never --skip-audio-link` completed in 132.973 seconds
wall time (`[CN]`: 130.4 seconds), down from 146.256 seconds before the selective
AnimeStudio index change. Exact scene-key resolution is now memoized by
payload, mission, and resolver identity, while immutable binary inputs under
`export_full/` are read once per build process. The final unchanged-input run
with `--timeline-recovery never --reuse-reference --skip-audio-link` completed
in 124.441 seconds (`[CN]`: 121.7 seconds), a further 6.4% wall-time reduction
from 132.973 seconds without changing an evidence predicate. Timeline reuse
also avoids about 26.9 seconds of failed
installed-Persistent preflight on this checkout. The machine-readable
mission-timeline report now uses compact JSON because its paired Markdown is
the readable view; the current file fell from 93.3 MB to 52.4 MB without a
parsed-payload change.
The later patrol-context build, using the same fast flags, completed in
128.264 seconds; the 3.8-second difference is within the observed run-to-run
range while the added binary join validates only seven playback occurrences
and one LevelData scene. The corresponding Mission Pipeline pass completed in
2.141 seconds.

The 2026-07-22 profile of the expanded binary-recovery build found three more
shared costs rather than a weak evidence pass: the Win32 filename-search API
was rebound 1,634 times, provenance paths were normalized about 94,000 times
through `Path.relative_to`, and independent exact-evidence passes repeatedly
decoded the same validated LevelData member-22 dictionary. Initializing the
Win32 binding once, using equivalent lexical `os.path.relpath` provenance, and
caching the fail-closed dictionary decode by immutable bytes plus the complete
scene script set reduced the current fast CN command from 129.055 to 106.275
seconds wall time (17.7%). Aggregate SHA-256 values remained identical for all
10,887 conversation payloads, all 702 mission sidecars, and the reused
reference bundle. The following direct Mission Pipeline pass completed in
2.202 seconds with 490 missions and 4,461 quests at that checkpoint. The
current complete Persistent MissionRuntime override adds `hidden62_q#19`, so
the live payload now has 490 missions and 4,462 quests.

The next exact-equivalence optimization moves native LevelScript control-graph
preparation out of the per-Story-action lookup. Each file now validates its
action buckets, semantically equivalent duplicate local ids, typed branch
payloads, and header payloads once, then reuses that immutable context for all
targets. The isolated playback-index wall time fell from about 13.3 to 9.2
seconds. With the new BattleSignal producer chains and task-map dependency scan
also enabled, the fast CN Story command completed in 106.847 seconds and the
direct Mission Pipeline pass in 2.094 seconds. The wrapper's data-only mode now
runs the cheap export freshness guard before reuse; direct Python invocation is
only appropriate after freshness has already been established.

The inferred-option-anchor audit no longer performs a second full read of all
10,887 generated conversation files. The language build records the same
18 current report rows as payloads are written, and a regression test compares
the resulting JSON and Markdown byte-for-byte with the retained legacy scan.
This is a safe redundant-I/O removal, not a headline build-speed claim: a warm
repeat still measured 108.784 seconds overall (106.3 seconds inside the CN
Story pass), within ordinary run-to-run variation of the earlier 106.847-second
measurement. The direct Mission Pipeline rebuild after that run measured
2.013 seconds.

Entity-tracking world-interactive dialog recovery now groups wanted exact
global logic IDs by authored scene, validates every LevelData source/mirror
pair, and parses each verified blob once. Candidate uniqueness remains keyed
by `(sceneId, globalLogicId)` and still fails closed unless exactly one record
survives. On the current original-data export this reduced the isolated stage
from 8.216 to 0.871 seconds, from 5,641 to 445 frame parses, while retaining the
same single-row SHA-256 result. The next warm full command measured 90.572
seconds overall (88.1 seconds inside CN Story), but only the isolated roughly
7.3-second reduction is treated as causal because filesystem caching varies
between full runs. Its direct Mission Pipeline rebuild measured 1.993 seconds.

The Timeline preflight is now transactional: empty or missing selected CHKs
are rejected before the existing filtered extraction is removed. If that
disposable extraction is nevertheless absent, exact Actor-root filenames from
the current line-order index may select the current full typed MonoBehaviour
export; SourceFile and PathID validation remains mandatory for every playable,
track, and parent hop. That fallback costs about 15 seconds here and recovers
17 current rows across 13 black Story keys instead of lowering coverage.

After the FMV and prime-node dependency additions were hardened, the unchanged
CN command with `--timeline-recovery never --reuse-reference --skip-audio-link`
measured 102.575 seconds wall time. The immediately following Mission Pipeline
projection measured about 2.2 seconds. Full-build variance remains dominated by
filesystem cache state, so the maintained fast loop is still the data-only
projection when Story sidecars are already current. The hardened corpus passed
288 script tests plus exact generated assertions for eight prime dependencies,
14 unanimous FMV shell bindings, three deliberate FMV non-bindings, and zero
missionless ghost Story keys.

When only Mission Pipeline JSON/frontend work changed,
`--mission-pipeline-data-only` is the intended loop: the current 490-mission
refresh measures 2.094 seconds on the final direct run, without rebuilding
Story, evidence, semantic views, or the source graph. The wrapper retains a
sub-second freshness check before that direct builder. The full script suite
and focused randomized similarity-equivalence audit retain exact binary-derived
matching and ordering behavior.

A later low-overhead pass targets three profile-visible costs without skipping
any original-data stage: AnimeStudio filename-pattern results now remain cached
for the complete builder process instead of evicting broad dialog families
after 32 exact queries; sibling option-template candidates are partitioned by
the already-required option count before the unchanged compatibility checks;
and unchanged generated text is compared as encoded bytes without a separate
existence stat or UTF-8 decode. All 10,887 conversation files were byte-identical
and normalized hashes for all 702 mission sidecars, the Story index, the
49.9 MB mission-timeline report, and mission binding coverage matched the
pre-change build. The script suite passed 290 tests. A concurrent full-run
measurement was too noisy to attribute a reliable end-to-end saving, so the
maintained user-facing speed claim remains the roughly one-to-three-second
data-only projection rather than that full-run timing.

A generic "rebuild Story mission connections but reuse every conversation"
mode is not currently safe. `build_language_bundle()` derives the Story
catalog, builds mission flows, runs ordering-dependent connection and weak-edge
suppression passes, then performs final `storyFiles`/`unlinked` normalization in
one shared in-memory pipeline. Editing old sidecars in place could retain stale
owned relations or change later suppression decisions. The next speed frontier
is a deliberately extracted relation-family pass that removes and rebuilds only
its owned rows, reruns final normalization, and proves byte/semantic equivalence
against a full build. A narrow DialogTree-only prototype is expected to land in
the tens-of-seconds range, but the roughly 2-second data-only mode remains the safe
maintained path today.

Combat performs its own input-mtime guard and degrades with a visible stale
reason if invoked directly against an older graph. This prevents old graph
edges from retaining `direct` confidence after a newer export.

Use `--export-from-game` only when refreshing `export_full/` from the installed
game data. Add `--with-assets` when the same command should also run a combined
Story+asset AnimeStudio export, rebuild asset indexes, and decode/relink CN
audio. Without `--export-from-game`, `--with-assets` reuses existing decoded
assets and relinks audio after the Story rebuild. Run `.\build_updates.bat`
separately for the Updates feed. Use `.\export_assets.bat` separately when only
asset indexes or audio need maintenance.

Generated conversation audio links resolve through the served
`/export_full/structured/Audio/...` route. The frontend normalizes equivalent
relative export/audio forms, and audio-only rows count as visible media when
empty-text rows are hidden, so a recovered playable line is not filtered out.

The game does not need to be running. If it is open, close it before export so
files are not locked.

## Generated Data

Expected browser data:

```text
webui/data/
  manifest.json
  index.json
  actors.json
  lang/CN/index.json
  lang/CN/actors.json
  lang/CN/conv/*.json
  lang/CN/mission/*.json
  mission_pipeline/index.json
  mission_pipeline/missions/*.json
  lang/CN/reference/index.json
  lang/CN/reference/<source>/<table>.json
  lang/CN/presentation/index.json
  updates/latest.json
  assets/index.json
  assets/story_media.json
  assets/videos.json
  assets/bundles/index.json
```

Generated diagnostics and summaries are outputs, not active WebUI inputs.
Keep them under `reports/`.

## Page Contracts

Story:

- With `Show debug info` enabled, every visible file row carries a compact
  `Trigger:` line and every selected file renders a full Story-trigger panel.
  Normal Story mode does not load or display trigger evidence. Both debug
  surfaces read the existing
  language-neutral
  `data/mission_pipeline/index.json -> storyCoverage.storyTriggerManifest`;
  the Story frontend does not create a second trigger inference or consult OCR
  and manual order overrides.
- An exact serialized native event/action path is displayed as an
  original-data playback trigger even when the mission attachment itself is
  context-only. The panel keeps that ownership boundary visible. Direct
  quest/mission-to-Story playback is also labeled as playback, while
  Story-to-quest conditions, context-only rows, dependency-only rows,
  definition-only records, and files with no recovered route explicitly say
  that a playback trigger was not recovered or proven.
- The debug-only compact file-row line shows the first strongest route in evidence order:
  exact native playback, unresolved-owner exact playback, direct playback,
  condition, context, dependency, definition-only, then unknown. The selected
  panel retains every normalized route and expands exact event name, selector,
  action chain, and original source path.

Mission Pipeline:

- Available in normal navigation and read-only; built by `python scripts\build_mission_pipeline_data.py`.
- Story cards consume `storyCoverage.storyTriggerManifest` to show normalized
  evidence chains from quest/mission ownership through server message, native
  event, LevelScript, playback action, and Story terminal. Unresolved playback
  retains an ownership-gap step and definition-only files remain separate;
  compact exact serialized event/action paths are expandable rather than being
  flattened into the attachment label. The route normalizer also unwraps the
  `listener` retained in `worldEntityLevelScriptEvidence`; all 30 currently
  published mission-tracked world-entity routes therefore expose their exact
  native paths instead of collapsing to context rows with zero paths. For
  example, the live `e6m4` card for `radio_e6m4_18` shows Leader slot `80001`
  at script `22800110022` header `6`, then `Split.actions[0]` local `8` and
  `PlayRadio`.
- Exact foreign-dialog Timeline containment uses dedicated parent-Story and
  dialog-Timeline chips in the same route. The live e11m3
  `dlg_e11m3_16` card retains the parent `dlg_e11m3_7`, Timeline
  `dlgtl_e11m3_7_sub_1`, both embedded option ids, surrounding parent lines,
  and the parent's native trigger/action path. It remains
  `causality=context` with `graphEffect=none`; parent content on both sides
  does not become a Story-file order edge.
- The mission-level native-boundary section also consumes
  `storyCoverage.dynamicSceneIdentityCrossReferences`. It renders only rows
  whose typed DynamicScene mission/quest condition belongs to the selected
  mission and shows the exact `IdComp.logicId == LevelScript scriptId`,
  condition operands, LevelScript playback action, and linked Story key. The
  builder fails closed unless the maintained audit still reports
  `directBridgeFound=false` and `missionGraphAction=none`; the cards say
  candidate context, no mission owner, and zero graph edges. The builder also
  freshness-checks the focused action-bridge audit against the identity audit.
  Its one admitted self-target row is rendered with a stronger local-context
  badge and the exact chain
  `slot 80001 -> dlg_c27m3_6 -> ShowSceneDecorationNew(10100282001, false)`.
  The fail-closed bridge payload now also carries the exact embedded Leader
  trigger volume selected by slot `80001`; the live card shows its sphere,
  radius `59`, and position `-757.75, 234.828, -1185.85`, plus the explicit
  negative that the complete trigger-volume schema has no DynamicScene,
  mission/quest, or foreign entity identity.
  The same card still states that mission-condition-to-trigger activation is
  unresolved and retains `storyBinding=false`, `orderEvidence=false`, and
  `missionGraphAction=none`. Current live
  checks show `2100060003` with `e1m2_q#5 = 3`, `e1m2_q#7 != 3`, and
  `cutscene_e1m3_1`, plus `23300000023` with `e7m4 = 3` and
  `cutscene_e7m4_2`.
- The generated trigger manifest and live Mission Pipeline now expose the
  recovered `WhileAction.doAction` control edge. A verified e6m1 card for
  `radio_e6m1_10` displays Leader slot `80003`, script `22800080005`, header
  `24`, then `WhileAction` local `25`, its `doAction` target `26`,
  `IfElseAction` local `28`, `Split` local `29`, and `PlayRadio` local `34`.
  The e7m2, e8m1, and equivalent-duplicate e1m2 paths are present in the same
  trigger manifest. Cards continue to label host-only and world-entity routes
  as context/dependency rather than quest activation or relative Story order.
- The same live view now exposes the last recovered weak-only LevelScript
  control paths. On `sm1l3m2`, `radio_sm1l3m2_8` shows custom event
  `WaitArea`, script `300010007` header `22`, `SwitchInt` local `23`,
  phase-zero `WaitForSecondsInTriggerVolume` local `31`, and its typed success
  edge to `PlayRadio` local `32`; the phase-one and loop-body paths to
  `radio_sm1l3m2_10` and `_12` are present on the same card. On dungeon
  mission `c31m3d5`, `radio_c31m3_16` shows
  `ScriptEvent_OnStartScriptControlledCharMode`, script `35400010010` header
  `130`, `SwitchString` local `141`, case `chr_9000_endmin` to
  `ScriptedCharPatrolStart` local `131`, `Split` local `132`, and
  `PlayRadioAndWait` local `133`. These stay labeled as exact local trigger
  reachability/context: they do not imply server quest activation or global
  Story order. The rebuild has 282 native branch groups and still 1,426 strong
  Story-order edges, so the new typed branch path did not invent chronology.
- Lazy mission payloads embed the source-only Story partial order with reduced
  causal edges, topological frontiers, cycles, quest forks/joins, and exact
  option branches. Exact native Split/IfElse/Switch Story arms and strictly
  observed downstream convergence are displayed in the same partial graph.
  Cross-owner cards joined by the same exact typed LevelScript playback source
  file are retained as `exactLevelScriptPlaybackContext`, not silently
  reassigned to the selected mission. Generic cutscene preloads remain in a
  separate `definitionOnlySourceNodes` list. The current CN payload has 11 of
  the former, two of the latter, and zero unresolved source nodes.
  Conditional rows show their exact event selector plus decoded PureGetter or
  inline-Param predicate operands; exact class-only predicates remain labeled
  without inventing their inner value. Current generated data has exact event
  details for all 71 native branch groups, including trigger slot, spawner,
  entity/property, custom-event, battle-signal, and script-lifecycle selectors.
  The frontend must never present sibling native arms as a recovered total
  playlist; isolated and weak-context-only files stay visible.
- Displays `MissionRuntimeAsset` predecessor topology and quest-state condition
  dependencies without treating `flowIndex` as an exclusive route selector.
  The builder prefers the complete Persistent MissionRuntime override only
  when it covers every StreamingAssets mission filename; otherwise it falls
  back to the coherent StreamingAssets corpus. The index publishes the
  selected root, decision, completeness counts, and exact changed filenames.
  `Show debug info` renders that provenance as a compact source strip; normal
  mode hides it. The current 980/980 override exposes
  `f1m32_q#3` as the exact `dlg_f1m32_2` option-finish objective and adds
  `hidden62_q#19` plus its two non-precedence state relations.
- Routes authored predecessor edges through a visible server-authority gateway.
  The selected-quest trace distinguishes native-proven objective/dialog
  messages and state pushes from the unavailable server successor policy.
- Keeps global-variable, spawner, and LevelScript request/response contracts
  in a separate native-boundary summary with exact fields, asynchronous roles,
  and an explicit not-attached-to-quest label. LevelScript rows distinguish the
  client request, its empty acknowledgement, and the independent server-pushed
  client event; the last identifies only scene/script/event/token and is never
  presented as mission ownership. The exchange descriptions also expose the
  completed token trace: `CallServer.Execute` reads the pushed `ctxToken` as
  `netToken` and returns it on `CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER`, making it
  round-trip correlation context rather than a hidden mission carrier. The
  Story graph applies the same boundary to serialized CallServer event names:
  values equal to `#` plus their own typed action-record UID are retained under
  `levelscriptCallServerCallbacks` with explicit non-Story/non-order/non-owner
  flags and are excluded from nodes, edges, scene placement, and Mission
  Pipeline ownership. This removes the former hash-terminal pseudo-scenes
  without discarding source-file or preceding-scene diagnostics. The current
  punctuation-only `#` and `%` values in two typed
  `PlayDialogAndHideSceneObjectAction` records are handled the same way under
  `levelscriptNonNodeScalarPayloads`: visible diagnostic provenance, no graph
  node or edge. That guard requires exact action-list membership and a
  co-record dialog id. The same exact guard now covers four one-character
  parameters (`P`, `Y`, `e`, and `A`) serialized beside real cutscene ids in
  typed
  `StartCutsceneAndControlSceneObjectAction` and
  `StartCutsceneAndHideSceneObjectAction` records. Those parameters remain
  inspectable with source/action identity and explicit false Story,
  mission-owner, and order flags, but no longer appear as graph events. For
  the remaining generic-symbol topology, all 208 Story-boundary edges are
  typed from physical serialized-map membership: 200 carry exact
  formatter-derived `sourceActions`, and eight header-list boundaries carry
  exact formatter-derived `sourceEvents`. Debug chips and tooltips show those
  names without promoting the weak `levelscriptChain` relation. The localized
  builder also copies them onto exact matching
  `timelineRecovery.sourceBackedSceneEdges` rows, which are the parallel edge
  copy rendered by the Story panel. The
  runtime contract also exposes the complete recursive protobuf identity
  census: zero mission/quest + LevelScript/Story co-carriers across 983 current
  enum-backed CS/SC message classes. Its three weaker scene rows remain
  non-owning: message 317 has no active fallback sender, while messages 111 and
  112 pass `roleBaseInfo.sceneName` only to
  `CharacterPositionCorrection` for server-position reconciliation. The one-way
  `SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE {sceneNumId, scriptId, stage}` row is
  labeled as a server push with no client request or expected response.
  Mission Pipeline now also exposes exact LevelData AirWall state-gated radio
  contexts. The generated Story sidecars contain 61 dependency rows and 61
  visible playback-context rows across 30 missions and 20 radios; reused radio
  names preserve their separate naming owner. Cards state that synchronized
  mission/quest state controls the wall and later local contact can play the
  pushback radio, while explicitly denying transition causality, quest
  activation/completion, Story ownership, and mission order. The runtime
  AirWall contract entered at schema v6 and records the complete
  958-file/822-group decoder census, 58 accepted contexts, two rejected
  inconsistent rows, and zero current IFix AirWall replacements.
  The current schema v7 also exposes the bounded `MissionOptionData` carrier
  audit. It records the exact `missionId`/`callDialogId` layout, but makes the
  native branch exclusivity explicit: a non-empty dialog id plays the dialog
  and exits, while mission acceptance is reachable only when the dialog id is
  empty. The contract publishes the zero-match current-instance census across
  MonoBehaviour indexes, TextAssets, structured JsonData, and installed Lua,
  adds zero Story bindings, and labels the result
  `schema_only_current_export_absent`. The Native boundary panel renders this
  as a closed managed-carrier card with the exact offsets, consumer address,
  zero-instance count, and explicit zero-edge result.
  Schema v8 adds the adjacent mission-property carrier closure. The Native
  boundary now distinguishes 217 authored `MissionRuntimeAsset.properties`
  rows and the server-synchronized `MissionData.propertyDict` from
  `ParamVariable.m_scriptPtr`, which is attached by LevelScript
  property/blackboard event subscriptions. The card exposes the exact
  `properties@0xe0`, `propertyDic@0xf8`, and `m_scriptPtr@0x70` layout, labels
  the result `runtime_context_only_no_mission_levelscript_edge`, and preserves
  the explicit zero-edge boundary.
  Schema v9 adds the implicit action-context closure. The Native boundary card
  shows `ParamSource.CURRENT_MISSION_ID=1004`, 18 MissionRuntime uses, and zero
  LevelScript uses across 4,512 files / 74,839 UID records. It labels all
  current uses as already-owned self-mission property checks, exposes the
  `Param<T>.paramSource` and `get_isCurrentMissionId` tokens, and explicitly
  adds zero mission-to-LevelScript, Story, quest, or order edges.
  Schema v10 adds the complete direct managed identity-carrier census. The
  closed-carrier area reports ten exact candidate types, eight runtime/object
  candidates, and zero unreviewed candidates. It identifies the last newly
  decoded mission/scene pair as HUD/map tracking context, exposes the relevant
  tracking field tokens and native consumer addresses, and keeps the result at
  zero new Story bindings and order edges.
  Schema v11 adds the MetadataRegistration-backed nested managed-carrier
  census. The closed-carrier area reports 25 typed candidates, 14 that depend
  on a nested path, maximum custom-type depth three, and zero unreviewed
  candidates. Its concrete closure card exposes
  `DialogManager.m_pendingItemSubmitter@+0x200` and
  `InventoryItemSubmitter.questId@+0x20`, plus the constructor,
  `TryGetSubmitMsg`, and registration addresses/caller counts. Zero current
  native constructor and registration callers were initially mislabeled as an
  inactive fallback producer.
  Schema v12 corrects that boundary with the shipped XLua producer. The card
  now shows the one exact `SubmitItemCtrl.lua` constructor/registration call,
  the two native `DialogOpenUIPanel` callers (DialogManager plus the generated
  XLua wrapper), 13 typed SubmitItem OpenUI terminals, and zero concrete
  authored quest ids. The bridge is active, but the three parameterized rows
  are stock placeholders and the other ten are empty, so it still adds no
  quest-to-dialog or order edge.
  Schema v13 closes the current fallback-parameter ambiguity and exposes the
  useful part of the authored submission relation. The native boundary card
  pins the `DialogTreeOpenUINode -> DialogManager -> DialogOpenUIPanel ->
  PhaseDialog.lua` pass-through, which JSON-decodes the authored param without
  a quest lookup. It also reports three exact MissionRuntime submission checks,
  two same-AND dialog co-gates, and zero overlap between those dialogs and the
  13 SubmitItem OpenUI terminals. The three affected quest inspectors render
  their exact submission ids and `SubmitItem.json` item/count alternatives;
  co-gates are labeled as non-owning condition context.
  Schema v14 adds the remaining exact authored submission shape:
  `sm2l7m1_q#17` renders the same-AND
  `submit_item_sm2l7m1 + map02_lv008/23100170008` LevelScript-stage co-gate.
  Its tooltip explicitly separates the script's recovered dialog playback
  context from submission UI ownership. The current corpus has exactly one
  such co-gate across 490 missions.
  Schema v17 adds authored tracking and mission-variable inspection without
  changing the graph. With `Show debug info`, objective cards expose all 3,496
  typed tracking rows, exact positions/entity operands, and their normalized
  visibility filters; the structure panel exposes 217 initial property rows
  across 71 missions. This makes the three filtered `sm2l8m1_q#18` markers and
  the exact `f1m19d3_q#7` tracked script/entity slot visible. Normal mode hides
  both blocks, and neither surface claims a writer, completion source, playback
  trigger, ownership relation, or ordering edge.
  Schema v18 pins the filter runtime boundary. Tracking help and the native
  property card now explain the exact
  `TryGetSaveProperty -> DoCompare` evaluator and
  `SC_UPDATE_MISSION_PROPERTY -> property-id lookup -> ToVariable ->
  MissionData.propertyDict -> change event` path. The card reports 204
  property-filtered tracking rows across 46 missions / 110 variable
  identities, while explicitly retaining the unknown server producer and
  timing gap. It also corrects the older embedded property census from the
  Streaming mirror to the effective 217-row / 71-mission corpus.
  Native paths with no network exchange are separated again: BattleSignal is
  shown as local Ability-action dispatch with only signal/value identity, not
  placed into either C->S or S->C lanes.
- Separates proven active mission sends from protocol capability. Mission
  acceptance has no paired response and waits for asynchronous
  `SC_MISSION_STATE_UPDATE`; only `ClientOnly=9999` objective leaves send
  absolute `CS_UPDATE_QUEST_OBJECTIVE` operations with `isAdd=false`; dialog
  finish waits for an asynchronous `SC_FINISH_DIALOG` echo with no correlation
  UUID. `CS_FAIL_MISSION`, `CS_MISSION_EVENT_TRIGGER`, and
  `CS_MISSION_CLIENT_TRIGGER_DONE` remain labeled protocol-defined with native
  sender unconfirmed and never draw an active exchange.
- Uses language-neutral lazy graph payloads, then merges mission names and
  objective text from the selected language's existing Story sidecars.
- Shows exact typed `SubGameInstanceData` mission-to-`bindScriptId` rows on the
  mission shell. The generated registry records 20 bindings across 20 missions
  and explicitly records `storyBindingsAdded: 0`; the cards never attach a
  quest or Story file from SubGame/LevelData co-membership. Each card shows the
  exact network `gameId`, the client start/stop requests, and the asynchronous
  server enter/start/complete/reward/leave pushes. The runtime contract records the current
  native proof that `WorldChallengeGame.SendQuit` reads `bindScriptId` at row
  offset `+0x50`, manually ends the resolved LevelScript, and then sends stop.
  This is labeled lifecycle/cleanup rather than activation. OCR, manual, and
  gameplay cross-references cannot create a pipeline edge.
- Adds exact typed activity quest-level hosts from
  `ActivityDungeonFightingStageTable` and `ActivitySnapShotStageTable`. The
  current payload contains 25 rows across 24 quests and four missions; cards
  and the inspector label them non-owning and `storyBinding: false`.
- Separates action-only DialogTrees from recovered Story files. Exact
  `OnQuestStateChanged -> StartDialogAction` (`0x049e/0x0f`) chains for
  `dlg_a1m4_OpenUI` and
  `dlg_a1m13_OpenUI` render as Open UI runtime terminals with panel/activity
  parameters. They do not become `misc_dlg_*` aliases and do not change Story
  coverage.
- Keeps exact native playback visible even when no mission owner exists. The
  global native-boundary panel now renders ten missionless SubGame nodes as
  `SubGame -> bindScriptId -> native playback -> Story`, covering nine unique
  Story files and fourteen placements. They remain included in the 1,210
  unlinked-mission files and are not counted as connected Story. Exact original-
  data prerequisites/associations are shown as dashed non-owning edges: the
  boss-rush quest/prior-challenge unlock chain and activity stage 6's explicit
  `rankRelatedId`/mission row. Stage 3/4 naming similarities produce no edge.
  The section header also publishes the complete current exported-reference
  census boundary: task ids add zero MissionRuntime consumers and all audited
  rows add zero Story bindings.
- Renders a second missionless original-binary layer for exact serialized
  runtime receivers. The current payload has 161 receiver nodes covering all
  155 exact-native unlinked Story files and 185 placements; no exact-native
  playback row is missing a runtime selector. Cards show the exact event family,
  listener LevelScript, selector fields, local/server transport, and Story
  links while retaining a visible `no mission owner` badge. Entity pointer
  paths, authored slots, spawner/group ids, HP thresholds, patrol/checkpoint
  ids, signals, guide ids, and stage filters come from current-build
  MemoryPack fields; filenames and OCR never create these nodes.
  Debug cards now also show the v8 nominal-mission LevelData comparison. A
  filename/index-derived mission candidate is visibly labeled non-owning; the
  card either names the validated same-level mission host that excludes the
  receiver script or states that no such host exists beside an exact SubGame
  carrier. This closes the static naming route without adding graph edges.
  The 13 BattleSignal receiver nodes additionally show 21 exact local producer
  routes for 20 unique SkillData/BuffData actions. The route is explicitly
  `LOCAL`, with no request/return, and its signal-only receiver boundary is
  shown so causality is not mistaken for mission ownership. Same-script
  task-map mission-state dependencies show exact task/condition ids and
  offsets, plus a visible `not linked to playback control path` boundary.
  The same cards now publish exact Dungeon/SubGame scene context for 18
  receiver scripts and 14 Story keys across six scenes. All 40 placements
  distinguish the seven exact bound scripts from 33 siblings, and attached
  quest/mission/prior-challenge prerequisites remain visibly non-owning.
  Nine sibling receivers additionally show the typed dungeon mission shell;
  mismatched shipped mission/Story families make the `no mission owner`
  boundary visible even when another shell happens to share the Story prefix.
- Organizes its left browser like Story: collapsible mission-type groups with
  naturally ordered mission rows. Graph dragging suppresses node selection
  after a movement threshold, and the unmodified wheel controls graph scale.
- Each graph block combines its short objective with the effective localized
  mission description. `overrideMissionDesc` / `descriptionOverride` replace
  the base description only for the authored quest. Direction badges distinguish
  Story conditions that feed a quest, quest actions that launch Story, and
  scoped context attachments. The selected-node inspector groups those same
  connections, exposes phase/action-slot/confidence evidence, and deep-links to
  the recovered Story file. Trigger routes render every exact serialized native
  event path as a separate causal lane: event summary and selector fields,
  listener LevelScript/header, local or server-backed transport, each traversed
  action, then the Story terminal. Multiple lanes remain alternatives or
  distinct occurrences and never imply a total order.
- Story files are attached per quest only from authored runtime references or
  bounded LevelData, LevelScript, variant-runtime, and unique NPC-proxy
  evidence, never from mission-id co-membership or spatial proximity alone.
- The generated CN coverage is currently 4,072 of 5,282 unique Story files
  across 4,368 mission placements; 1,210 remain unlinked. Of the connected
  total, 106 have non-MissionRuntime nominal Story owners and enter the metric
  only because accepted generated pipeline edges connect them. This is an
  accounting repair; the unlinked denominator is not widened with unrelated
  level-owned Story assets. The exact dynamic
  HP-spawner chain adds only `radio_gm02m20_9` and `radio_gm02m20_18` as
  mission-level `gm02m20` context, with no quest binding and no server exchange.
  The exact typed WorldEntity foreign-key route attaches `radio_e3m2_7`,
  `black_gm02m11_1`, and `cutscene_gm02m11_Activate` as quest context. The UI
  explicitly says that the quest condition and playback script reference the
  same unique entity set; it does not label this as quest/server activation.
  Six `sm2l5m1` patrol radios now use a separate mission-shell relation: exact
  native checkpoint receiver, case-sensitive LevelData alias/world entity,
  same-script patrol producer, framed patrol/checkpoint row, and a unique
  MissionRuntime tracking mission union. The UI lists every candidate quest
  but labels ownership and quest activation/playback/completion false, and
  shows the local route as having no request, server push, or expected reply.
  The expanded receiver whitelist adds `radio_e2m5_19`, `radio_e3m3_7`,
  `radio_sm2l4m2_3`, and level-owned cutscenes
  `cutscene_map02_lv004_lingyuan_1/2/3`. Stage-backed rows show the exact
  server message/fields and expected return `none`; the interactive-property
  row shows no packet join. An exact same-script preload is exposed separately
  and never counted as playback. Exact no-bypass DialogTree quest gates,
  tracked-NPC parent/child navigation, and mirrored interactive progress-lock
  joins are labeled as local non-owning context; they never claim quest
  activation, completion, or a request/reply. Of the remaining unlinked files,
  153 have exact native playback but no decoded
  mission/quest trigger. OCR,
  manual overrides, and observed gameplay cannot increase this metric.
- Mission-named LevelData attachment requires the exact native 43-member
  container and a completely parsed member-22 `LevelScriptBriefData` entry,
  including matching final script id and validated dictionary framing. It is
  displayed as asset-shell context, not logical mission or quest ownership.
- Broad LevelData shells can receive the same bounded asset context through a
  typed MissionRuntime `MissionAreaTrackingInfo.missionAreaId` -> exact
  `MissionAreaTable.subDataParentId` -> identical validated member-22 root-key
  chain. Every authored root/file hit must agree on one mission; filenames are
  ignored and shared roots remain unresolved.
- A complete validated LevelData member-22 container can also scope a sibling
  playback script when every exact MissionRuntime, typed MissionArea, and
  mission-shaped asset anchor in that shell agrees on one mission. The UI calls
  this an authoritative asset-shell union, exposes the anchor rows, and never
  upgrades it to quest playback.
- Typed `EntityTrackingInfo` rows resolve local script/entity-slot targets
  through the native global-script-id calculation and the aligned
  `WorldEntityRegistry` arrays. An exact tracked interactive `type_id` appears
  on the owning quest as configured navigation context. Typed Story actions in
  that same script require exact action-map membership plus an event/control
  path and remain same-script context. Both forms show local/global script ids,
  tracked and event slots, registry detail, source offsets, and an explicit
  no-playback/no-server-exchange label.
- Nested tracking is accepted only from authored
  `mapTrackingToMultiDesc=true` wrappers whose selected `actualList` member is
  an exact `EntityTrackingInfo`, and only when the complete typed owner union is
  one mission. This adds five same-script Story-context links to
  `c27m4d5_q#14` and the exact tracked-interactive context
  `c33m1_q#10 -> dlg_c33m1_17`; neither form is promoted to quest playback,
  completion, order, or server traffic.
- Exact `InteractiveTable` object aliases are accepted only through the fully
  decoded two-map table and template `int_narrative_mission`. For the one proved
  tracked-entity playback bridge, the inspector shows the producer/listener
  scripts, `TravelPoleBegin` header, `EntityCompare` operand, raised custom
  event, and Story target. It separately says the placeholder objective's
  server payload is unavailable.
- MissionArea shape rows can display exact current-build Leader trigger-volume
  geometry when the level-scoped table shape, enter-event slot, union tag,
  member count, and EOF-bounded body all agree. This remains local client
  context, not a server-completion edge.
- Mission-level native event context includes exact client-global-variable
  paths and typed `WaitForNpcProxyReady` paths. Candidate quests are shown when
  several consume the same key/proxy; the UI deliberately stops at mission
  scope and says that no request/response payload was decoded.
- The exact NPC-proxy segment identity is shown as weak mission-shell context
  only when the typed MissionRuntime proxy, every authored proxy mission id,
  registry key/`segmentIdGlobal`, same-scene Story-playing script id, and every
  normalized raw playback occurrence all agree. It currently supplies nine
  direct Story attachments and two exact parent-dialog black-action children.
  Cards expose the proxy and segment ids and explicitly say this is not proved
  NPC activation and has no server request or response.
- PureGetter mission-state branches render in a separate expandable dependency
  section rather than as Story ownership. The current payload has nine Story
  files across eleven mission placements; only the exact single-mission
  `Equal(Processing)` true branch is also weak mission-shell playback context.
  Cards say the getter reads the synchronized local mission cache, sends
  nothing, expects no direct reply, and receives independent upstream mission
  synchronization pushes.
- Exact typed LevelData `RadioTriggerZoneData` rows add four connected radio
  files across six mission-state placements. Each card exposes the concrete
  `hideBeforeMissionId`, `hideAfterMissionId`, or `hideCompleteMissionId` role,
  trigger id, and one-shot flag. Native `OnEnter -> GetMissionState ->
  PlayRadio` makes this state-gated playback context, not quest ownership; all
  client-request, direct-reply, and server-exchange flags remain false. Together
  with PureGetter, these families cover 13 Story files across 17 placements.
- Two exact counted `LevelInteractiveData` entities add
  `radio_c16m4_50/51` under the `c16m4d5` mission-state dependency section.
  Cards expose the `FX_CHANGE_MISSION_ID`/`TYPE_ID` PropertyKeys, popup id,
  entity/template identity, list count, record boundary, and ParamValue map
  offset. They distinguish the local synchronized-state read from the separate
  optional `_RequestInteract` path and do not invent a protocol reply. The
  combined dependency section now covers 15 Story files across 19 placements.
- Mission Pipeline schema 19 adds the independent top-level LevelScript
  interactive-configuration family. Generated sidecars now contain 145 exact
  placements for 131 unique Story keys across 50 mission files, and the
  coverage build moves 52 previously unlinked Story files into connected
  context. Debug routes render
  `mission -> LevelScript -> narrative interactive -> Story`, including the
  local interactive id and authored `type_id`. The label and route explicitly
  keep activation, player interaction, quest causality, ownership, and order
  unresolved. `text_*` rows remain outside the historical Mission Pipeline
  coverage denominator, but schema-4 coverage now publishes their exact routes
  as context-only manifest rows so the card is not visually lossy. The
  source-gap queue closes 106 isolated source-link rows across 43 missions from
  this exact configuration without adding an order edge.
- Mission Pipeline schema 25, coverage schema 10, and source-gap schema 19
  expand the parallel exact LevelData interactive-configuration family. The
  source decoder now finds 234 placements for 229 Story keys across 49
  LevelData assets: 22 null progress locks and 212 exact mission/quest-state
  locks. Of these, 77 placements for 72 keys have publishable pipeline mission
  shells. Routes render
  `mission -> LevelData -> interactive availability condition -> narrative
  interactive -> Story` when a lock exists, retaining the raw combined
  operator/runtime flag, nested combined structure, and each exact state
  owner/target. The state owner is
  availability evidence, not Story ownership or chronology. Non-final records
  use the next typed item; final records require either a complete nonempty
  member-22 BriefData dictionary or the exact environment-only members 21-43
  empty-script suffix through EOF, and retain that provenance. Thirty-four
  finals pass.
  Relative to schema 21, 54 more Story trigger routes move coverage to 4,153
  connected / 1,129 unlinked Story files; context-only manifest coverage rises
  from 65 files / 66 routes to 91 keys / 95 routes. The source queue closes
  179 additional isolated rows while the strict graph remains unchanged at
  1,429 strong Story-order edges.
  The extra definition-level route comes from the exact final `int_horn`
  record in `map01_lv001_lv_data_sub_sm1l1m9`: q13 consumes the registered
  `dlg_sm1l1m9_11` definition, while the LevelData row is available after q16
  completes. The card renders
  `q13 -> LevelData -> q16 availability -> int_horn -> dialog definition`.
  It remains outside the Story denominator because the base definition has
  options but no emitted text conversation, and it is not aliased to the
  separate `misc_dlg_sm1l1m9_11d5` conversation.
- Exact EOF-bounded `Play3DRadio` records can connect a radio to a same-scene
  tracked NPC emitter only when `useNpcProxy` is true and all typed consumers
  agree on one mission. A complete typed TravelPole/entity-compare/custom-event
  route can inherit one authoritative validated LevelData shell. Both render
  as local playback context, never as a quest trigger or server exchange.
- Mission-shell attachments additionally accept exact authored SNS mission-id
  agreement, FocusMode's explicit mission/radio pair, uniquely mission-scoped
  LevelScript action payloads, and serialized black-screen-playable to Timeline
  Actor-root containment joined through `DialogBriefInfo.usedDialogTimelineIds`
  and either the typed parent-dialog playback host or one unique direct
  original-data parent-dialog mission context. Multi-quest parents stop at the
  mission shell. Native playback without a validated mission/quest owner stays
  in `Unassigned Story` instead of being promoted. When a same-file native
  owner event is exact, that row shows normalized MemoryPack event/action tags,
  event payload or trigger slot, and the count of exact
  `ActionHeader.nextId` / `ActionBase.nextId` / typed `Split` /
  `IfElseAction` control paths; the old combined parser pair is labeled legacy.
  Event names come from the complete current-build 230-tag ActionHeader table,
  applied only to proved `headerList` records to avoid cross-union tag
  collisions. Exact `SwitchInt` case/default traversal now supplies a named
  serialized event-owner path for every remaining native-playback file.
- Unassigned custom-event rows additionally show exact typed producer evidence
  when it exists. Current ActionBase tags distinguish
  `RaiseCustomLevelEvent` from `RaiseCustomScriptEvent`; the latter decodes its
  `Param<LevelScriptPtr>` receiver as either the current script or one explicit
  constant script. The current generated sidecars expose 15 producer routes on
  10 unassigned native Story rows. These rows show producer/listener scripts,
  event key, receiver mode, source file, and an explicit local-dispatch/no-
  server-request-or-response label. Producer causality alone does not select a
  mission or quest and therefore does not change coverage.
- Mission acceptance dialog and explicit `NpcProxyEx.missionId` evidence render
  in a separate mission-lifecycle Story section. Remaining same-owner Story
  scene files render in a collapsed `Unassigned Story` section; a file linked
  to another mission's quest is removed from its owner's unassigned list but
  is not copied onto an arbitrary local quest.
- Language sidecars include every exported MissionRuntime mission, including
  variants with no Story index group of their own, so direct and recovered
  cross-mission attachments remain visible. Native action evidence follows the
  complete `_nextID` chain and is labelled as the installed build's fallback
  implementation because IFix can replace it at runtime.
- Exact native FMV rows expose `PlayFmvAction` or
  `StartFmvAndTeleportAction`, the serialized `cs_video_*` field, action tag,
  script, host shell, and all-occurrence completeness. Fourteen current targets
  bind through one exact LevelData mission shell. `cutscene_e3m5_1` and
  `cutscene_e9m3_2` remain unassigned because host coverage is incomplete, and
  the false `cutscene_e1m3_1` page collision is suppressed. All are labeled as
  local presentation with no request or expected server reply.
- DialogTree narrative-mask connections retain every authored parent dialog.
  One accepted parent no longer hides another unresolved use: the connection
  reports complete/partial scope and the pipeline audit separates unresolved,
  wholly unlinked, and partially connected files.
- Prime-node DialogTree dependency rows are rendered separately from stronger
  parent-trunk playback carriers. Their label says that the binary-proven route
  can reach the Story carrier while the quest only observes the parent
  dialog's completion; the inspector exposes the parent Story, serialized
  prime node, PathID, mapping, `dependencyOnly`, and local/no-server boundary.
  The current exact set contains eight files. The frontend must never present
  these rows as quest playback or Story ownership.
- Unassigned black-screen rows now distinguish exact native playback with no
  owner, exact typed containment with no parent scope, and original TextTable
  definitions with no current-build playback consumer recovered. The last
  class is labeled `definition-only` in the corpus summary and connection
  detail rather than being presented as a decoder gap. The current generated
  count is 61.
- DialogTree mission-shell inheritance prefers the typed
  `MissionAreaTrackingInfo -> MissionAreaTable.subDataParentId -> identical
  LevelData member-22 root` join over a mission token parsed from a LevelData
  filename. This connects `black_c27m4_1` to `c27m4d5` while leaving quest
  chronology unknown and keeping the presentation local/no-server-exchange.

Story:

- Built by `python scripts\story_builder\build.py --languages CN --default-language CN`.
- Uses structured dialog/SNS/radio/remote/env talk tables, recovered
  AnimeStudio/Timeline data, `dialog_id_table_index.json`, and
  `story_source_links.json`.
- Conversation JSON is lazy-loaded from `webui/data/lang/<code>/conv/`.
- Recovery uncertainty should stay visible through warnings. Detailed issue
  filters, source/debug blocks, mission timeline evidence, cutscene debug
  panels, and manual order-edit controls are available from the Story
  `Show debug info` toggle.
- Timeline-inferred option responses are promoted only when source evidence
  binds each option index to a distinct candidate response. The known
  source-backed strict `trunkClipOptionIndex` case is `dlg_c28m3_10` group 1;
  the remaining unresolved groups stay inferred.

Reference:

- Built by the Story builder.
- Keeps rows close to exported structured tables and resolves localized display
  text where possible.
- Avoid story-specific interpretation; tables that should not become Story
  conversations can remain Reference-only.

Gameplay:

- Built by `python scripts\build_gameplay_data.py` from authored structured
  tables and localized text.
- Curates characters, weapons, equipment, enemies, and usable items rather
  than exposing arbitrary decoded JSON. Current safe display semantics include
  progression costs/checkpoints, skill text and blackboard values, equipment
  formulas/suits, enemy variants/stat curves/abilities/scalars/buffs/drops, and
  usable-item actions/chest rewards.
- Raw authored values and normalized display aliases must remain distinguishable
  where a formatter transforms the source value. Static data does not establish
  live inventory, server availability, runtime formula order, or encounter state.

Characters:

- Built by `python scripts/build_character_data.py` into
  `webui/data/lang/<LANG>/characters/index.json`.
- The debug-only `人物` page merges all `TextTable.json` `npcName_*` keys,
  playable `CharacterTable` rows, named `NpcTable` and `SNSChatTable` rows,
  and the generated Story actor registry. Each observed name retains its source
  and source key.
- Exported asset evidence recognizes `_actor_`, `_npc_`, `_major_npc_`, and
  `_npc_major_` filename markers. It is grouped by identity, evidence type,
  and asset kind with exact counts and representative paths. An asset-only
  token is shown as an identifier, not promoted to a localized character name.
  Each representative path deep-links to the matching Assets-page entry, and
  the evidence key links to its first representative asset.
- Asset tokens first resolve to an existing table-backed identity by exact
  alias or an unambiguous suffix match, then to a Story actor identity. Only
  unresolved tokens remain asset-only identifiers. Evidence records the chosen
  identity and match rule.
- The left sidebar follows the shared inspector layout: collapsible type and
  evidence-source filters, a horizontal filter-height splitter, a vertical
  pane-width splitter, and an independently scrolling result list.
- Exact display-name matches are grouped only when their normalized set of
  discovered known names also matches. `???` and `？？？` are ignored when
  comparing those sets, so unknown evidence can join a compatible known group,
  but two different known names remain separate. The detail pane preserves
  every underlying identity and keeps evidence partitioned by that identity.
  The frontend renders the full filtered group list at once rather than using
  incremental `Show more` batches.

Display additions roadmap and current status:

1. Landed: a projectile inspector backed by exact AnimeStudio payloads. It presents
   collision, lifetime/range, movement segments, effect lists, alert behavior,
   and sound references; keep inferred enum/hash labels visibly qualified.
2. Landed: a combat relationship explorer that joins curated gameplay records to
   source-graph evidence across characters, enemies, abilities, selectors,
   buffs, projectiles, effects, audio, and assets. Direct and inferred edges
   remain distinguishable, and raw authored values remain available. It now
   also exposes all 162 byte-proven AbilityEntity inherited prefixes and 833
   direct component RID links while excluding the unresolved tails; 135
   character/enemy identifier matches are explicitly inferred. The guarded
   opening through `useFrameTick` is split into
   five exact mirrored fields and six visibly qualified metadata-order fields;
   the following 92-byte `surroundingConfig` is exact-consumed in all 162 roots.
   Fourteen linked SurroundingMovementData mirrors and ten non-consuming
   BaseRotationData next-boundary mirrors match. Enum/hash meanings remain
   qualified, and bytes from `followMountPointConfig` onward stay excluded.
   Character targeting now adds 68 exact-consumed TargetSettings records and
   four non-null finder/validator links proven reachable through component RIDs.
   Six records from two avatar templates without curated Gameplay roots are
   reported but deliberately left unattached.
3. Landed: a factory/economy browser for recipes, items, machines, technology,
   logistics, power, fuel, mining, shops, rewards, and activities. It describes
   authored static configuration, not live throughput, availability, or account
   state. Machine-technology edges resolve building-item ids through
   FactoryBuildingItemTable before targeting machines; unresolved mappings do
   not become dangling edges, and detail panels expose the endpoint-valid
   relation graph.
4. Landed: a static world explorer for levels, placed entities, interactives,
   spawners, models, audio slots, and authored references. Keep runtime world
   state and simulation explicitly out of scope.
5. Landed: a progression/reward graph with 9,836 browsable roots, 15,691 typed
   nodes, and 37,970 direct endpoint-valid relationships across upgrade curves,
   costs, breakthroughs, talents, potentials, item use/obtain paths, rewards,
   and drops. Every edge retains table/row/path evidence and the UI avoids live
   state, probability, and optimal-planner claims.
6. Landed: an entity Presentation explorer with 3,084 curated roots, 7,452
   nodes, and 16,857 endpoint-valid relationships across model configs,
   prefabs, controllers, bounded asset entities, materials, shaders, animation
   configs/states/clips, effects, and representative browser assets. Direct and
   inferred edges remain separate; caps and omissions are explicit, and the
   view does not claim runtime renderer choice, transitions, effect timing, or
   shader behavior.
7. Next: deepen Combat from the `followMountPointConfig` boundary;
   structurally complete selector/target-settings fields stay semantically
   qualified until enum/hash labels and evaluator behavior are proven.

The landed views use isolated generated-data builders and frontend modules with
shared tab navigation, packaging, and `export.bat` integration. The World view
also deduplicates mirrored registry instances while preserving compact source
provenance. Reuse that split so new semantic surfaces do not expand the Story
or Gameplay builders into unrelated domains.

The semantic explorers share a newcomer-facing landing contract: state what a
page answers and why it matters, use plain-language record and relationship
labels, and keep detailed confidence/provenance boundaries in expandable help.
Normal navigation exposes Gameplay and Mission Pipeline. Characters, Progression,
Combat & Projectiles, the retained standalone Combat graph, Factory, World, and
Presentation are gated by the top-right `Show debug info` switch; disabling
debug normalizes an active hidden view to a normal page and URL.
The asset-excluding package replaces `assets.js` with a navigation shim, so the
shim must mirror the same debug-view gating and hash/keyboard fallbacks rather
than exposing hidden pages in packaged builds.
Their feature styles must use the shared light-surface tokens (`--panel`,
`--surface`, and `--panel-bg`) rather than dark fallback colors. Dark surfaces
are reserved for media letterboxing or content that genuinely needs them, not
for ordinary cards, filters, lists, or evidence blocks.
Combat & Projectiles groups its 310 templates by sender. Exact exported
projectile-to-skill ownership edges are direct evidence; derived skill-family
or unique character/enemy identifier matches are inferred, and unsupported or
ambiguous records remain unresolved. World groups records by
authored level ID with localized LevelDesc names and plots coordinate-bearing
records for the selected level on a bounded SVG X/Z map. Global registry rows
without an exported level ID stay unassigned rather than being inferred from
coordinates or entity numbers. These defaults improve orientation without
promoting inferred runtime behavior.

Deferred-view recovery queue:

- keep Combat & Projectiles and the retained standalone Combat graph debug-only
  until sender/skill ownership is semantically trustworthy, ambiguous ownership
  is reduced, and the page presents a quieter task-oriented summary instead of
  a dense recovery graph;
- keep World debug-only until level association and placement semantics have
  stronger evidence, unassigned/global records no longer dominate exploration,
  and the 2D map communicates useful authored structure without noisy sampling.

Candidate follow-on displays, in evidence-first order:

- deepen Combat from `followMountPointConfig` and the remaining BuffData action
  chains, then show more target/filter/action structure without inventing
  evaluator order;
- add an audio cue/event browser across Wwise event/media links, story voices,
  gameplay cues, factory/world audio, and playable decoded media;
- add a mission/quest structure view for authored tasks, conditions, actions,
  areas, level scripts, and map markers while keeping runtime completion state
  out of scope;
- add semantic update drill-down that groups exported changes by these recovered
  entities while retaining the existing previous-export/current-export boundary;
- keep recovery coverage, unresolved layouts, and source-graph provenance as a
  debug-only evidence view rather than mixing diagnostics into normal browsing.

Updates:

- Built by `.\build_updates.bat` or `python scripts\build_updates.py`.
- Reads the saved previous and current export roots from `endfield_paths.bat`;
  the underlying script falls back to `export_1d2/` and `export_full/` when no
  wrapper configuration or explicit paths are supplied.
- Stores scanner cache and feed history under `.game-data-tracker/`.
- Never point the comparison at `webui/`, `reports/`, `memory/`, `scratch/`, or
  `tmp/`.
- Tracks WebUI-facing exported JSON plus exported image/model/video assets and
  decoded audio by default. Use `--skip-audio-updates` to omit audio while
  retaining other assets, or `--skip-asset-updates` for a text-only feed.
- Use `--baseline-only` only when an intentionally empty first/baseline feed is
  desired. Refresh the cached previous baseline after replacing that folder.
- `build_updates_by_patch.bat --init-baseline` seeds a separate original-data
  VFS snapshot from only the current installed version and attaches it to the
  current export. The two source scans use each other as VFS fallback and
  request only patch-workflow-publishable WebUI block families, including CN
  voice; optional uninstalled audit/non-CN audio packages are not treated as a
  broken baseline. `--check` is detection-only. Default apply mode preserves
  the no-change/version-only/repack-only invariant, while logical changes are
  built in a complete cloned staging export. Direct structured VFS files are
  dumped selectively; affected AnimeStudio and audio scopes refresh before
  rotation.
- Only `build_updates.bat` generates `webui/data/updates/latest.json`. For two
  explicit extracted roots, use `build_updates.bat --previous-export-root OLD
  --export-root NEW --refresh-previous-export-baseline`; the original-VFS
  detector does not generate the page by itself.
- Patch publication now uses sibling staging and same-volume archive/current
  renames. The previous export is preserved, occupied preferred archive names
  receive a snapshot suffix, WebUI data is backed up for handled rollback, and
  `build_updates.bat` compares the published archive/current roots. The source
  baseline advances only after extraction stability, WebUI rebuild, and feed
  generation succeed. A journal blocks new work after an unhandled interruption;
  failed published candidates are retained under the operational state root.

Assets:

- Built by `python scripts\build_assets.py`.
- Indexes exported images, models, materials, videos, story media, related
  files, browser previews, and optional demo bundles.
- Keep heavyweight recovery/debugger views out of the static frontend unless a
  new recovery view is intentionally designed.

Serving and packaging:

- Serve locally with `python serve.py` at `http://127.0.0.1:8765/`, or pass a
  port such as `python serve.py 9000`.
- Before starting a default server, check whether `127.0.0.1:8765` is already
  running and reuse it.
- Package with `python scripts\pack_webui.py` or `.\pack_webui.bat`.
- Pass `--skip-audio` to omit the standalone decoded-audio zip.
- Package inputs are `serve.py`, `webui/`, and selected media from
  `export_full/`. `reports/`, `scratch/`, and `tmp/` are not package inputs.

## Inline Media Rules

- `sns_emoji_*` assets render as inline emoji. They do not open hover popovers
  or the full-screen modal. Their resolver only uses exact or emoji-family
  sprite matches; missing emoji sprites stay unresolved instead of falling back
  to numbered sticker or SNS decoration assets.
- `envEmoji_common_*` rows render line-level `emoji` fields using recovered
  Unity prefab aliases, RectTransform layer data, and enter animation curves in
  `story_media.json`.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and related
  `cg_image_*` assets keep normal image proportions. Exact non-emoji SNS media
  does not borrow numbered sticker, decoration, or emoji fallbacks.
- When a line has both an inline `<image=...>` token and matching line-level
  `image`/`images` metadata, the inline token owns the visible display and the
  media strip dedupes it.
- Popovers and the modal preview must stay inside their visual frame and the
  viewport.

Regenerate envEmoji prefab data with:

```bat
python scripts\recover_envemoji_prefabs.py
```

## DialogIdTable Registry

The Story builder uses Endfield's runtime dialog registry,
`Beyond.Gameplay.DialogIdTable`, as offline evidence. The source file is
exported to:

```text
export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json
```

The extractor does not infer placement or branch fields from the MemoryPack
records. It sequentially decodes the complete first 2,633-entry
`DialogBriefInfo` map to its exact next-map boundary and separately extracts
standalone ASCII dialog roots, line-shaped tokens, and option identifiers. This
builds:

```text
export_full/recovered/dialog_id_table_index.json
```

Current baseline:

- `3,849` registered dialog roots.
- `2,633` roots with exact `memorypack_record_key` registration evidence;
  remaining vocabulary-only rows stay explicitly distinguished.
- `0` per-line/trunk tokens in the table.
- `1,407` registered scenes with option identifiers.
- `4,681` option IDs.
- `413` dialogs with authored `usedDialogTimelineIds` lists, containing `425`
  raw references (`424` distinct dialog/Timeline pairs).
- `0` radio entries; radio remains sourced from `RadioTable.json`.

The earlier `4,496`/`1,058` baseline was invalid: the extractor matched the
embedded `dlg_*` substring inside `option_dlg_*` and treated option-only rows
as fake dialog lines. Option IDs now contribute option vocabulary only and can
never register a scene. `DialogBriefInfo` contains no option anchor, branch
target, or per-trunk line list. Its sequentially decoded ninth member does
contain exact Timeline ownership; this is used directly and includes authored
`f_dlgtl_*` values rather than normalizing names.
Each registry row exposes `memoryPackRecordKey` and `registrationEvidence`.
Binary-sensitive consumers such as DialogTree quest-state dependency recovery
must require exact record-key membership; printable token scanning alone is not
positive registration evidence for those links.

Registry-backed reason codes:

- `unregisteredScene`: scene key absent from `DialogIdTable`; the runtime has
  no standard dialog entry point for it.
- `dialogTrunkRowIteration`: scene key present, but no Timeline/DialogTree
  source was recovered; row iteration by scene key prefix is the supported
  direct fallback.

Each conversation payload can include `_debug.runtimeRegistry` so downstream
tools can inspect root registration and option IDs. Current zero trunk/line
counts are an honest schema boundary, not missing recovery work.

If a future update makes the registry extractor report near-zero scenes, inspect
whether `DialogIdTable.json` still contains ASCII `dlg_*` strings. If not, the
table format or encryption changed and needs a targeted offline decoder.

## Game Update Playbook

Most game updates need only:

```bat
.\export.bat --export-from-game
```

Then, if `global-metadata.dat` exists, refresh the IL2CPP metadata canary:

```bat
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --cache-metadata
```

Inspect these drift reports only when the metadata canary changes:

- `reports/option_flow_runtime_metadata_diff.md`
- `reports/option_flow_runtime_metadata_focus_diff.md`
- `reports/option_flow_runtime_metadata_focus.md`
- `reports/option_flow_runtime_metadata.md`

Important interpretation:

- `global-metadata.dat` is useful for runtime vocabulary and method/field drift,
  but it is not the authored story payload.
- A hash-only metadata change with no focus/body-target drift is usually
  harmless.
- A new serialized field on dialog option/tree/timeline focus types is a strong
  candidate for new recovery evidence.
- `DialogTimelineOptionData` still having only `optionIndex`,
  `changeFinishNum`, and `targetFinishNum` means unresolved option targets are
  a runtime method problem, not a hidden serialized field problem.

## Benchmarks

Every `export.bat` run writes a wall-time and process-tree RAM benchmark under
`reports/export_benchmarks/` and updates
`reports/export_benchmark_latest.{md,json}`. Use those files as current truth.
The maintained direct CN Story build is presently on the order of minutes, so
direct runs should have a 10-15 minute shell timeout.

Historical profiling found the main Story-builder costs in repeated file
opens, per-scene regex compilation, mission/LevelScript spatial comparisons,
DialogTree source loading, raw Reference generation, and reopening freshly
written conversation JSON. Prefix/path indexes delivered a large early gain;
future optimization should re-profile before acting because the recovery
surface has since expanded.

A historical EndfieldStudio comparison showed it could rapidly cross-check the
structured Table/Lua/JsonData surface and extract a classified non-material
image subset, but it did not add Story data and omitted material textures,
meshes, AnimationClips, Material JSON, bundle JSON, and AnimeStudio
relationship metadata. It remains a cross-check or preview candidate, not a
replacement for the canonical AnimeStudio export.

## Verification

After a refresh, check:

- Story tab loads and conversation detail lazy-loads.
- SNS emoji stays inline without modal/popover behavior.
- SNS stickers/photos render with normal proportions.
- EnvTalk emoji rows render with recovered prefab layers and replayable enter
  motion.
- Reference tab loads table counts and lazy-loads rows.
- Updates payload tracks the installed `Endfield_Data` root, not generated repo
  folders.
- Assets tab loads counts and can preview images/videos where supported.
- Package dry-run reports expected story media and excludes 3D/model payloads
  by default.

## Story browsing and debug surface

- The Story view now defaults to a quieter browsing surface. The `Show debug
  info` toggle exposes line-order evidence, source/debug panels, mission
  timeline recovery, cutscene debug detail, and manual Story order editing
  controls. Recovery issue and recovery method filters remain visible in both
  normal and debug modes so confidence limits are not hidden from readers.
- Resetting Story filters returns to Story sort and clears chips/search without
  collapsing already-expanded mission groups.
- The WebUI chrome moved to a light neutral palette with muted teal and orange
  accents; kind/category badges remain softly color-coded for scanning.
- The gameplay video story-order matcher now combines OCR segments with
  decoded Story audio-template matches. Audio fingerprints are cached under
  `tmp/ocr/gameplay_video_ocr/audio/`; `au_music*` templates are ignored by default,
  and locked missions are used as threshold controls before applying proposed
  order changes.
- `scripts/download_bilibili_video.py` is the maintained optional intake helper
  for public Bilibili gameplay sources. It writes complete muxed `.mp4` files
  into `videos/`; the OCR worker continues to skip partial `.m4s` and `.lock`
  files.

### Option placement confidence

`inferredOptionLayout` is the generated payload compatibility warning, not a
claim that the WebUI has no display anchor. The current CN build has zero
unplaced option groups. Its raw generated placement-warning set is 93
unregistered table-only scenes, 7 registered key-matched scenes, 1 registered
end-of-scene fallback, and 0 registered gap/unknown scenes. Runtime WebUI
override coverage changes the visible Recovery Issue queue to 73 table-only,
0 key-matched, 0 end-of-scene, and 0 gap/unknown scenes. Twenty-eight scenes
are fully covered and move to `Manual override`; the 73 still needing complete
coverage remain under `Needs manual override`. The fully covered set comprises
20 table-only scenes plus all 7 key-matched scenes and the one end fallback.

The renderer keeps recovered groups inline at their `after` line, labels the
placement method, and uses a scene-level fallback block only when no position
exists. Manual entries in `webui/overrides/options.json` stay visibly tagged
and do not become source evidence. Generated index entries carry
`optionIssueTargets`, which lets the frontend compare exact warning
groups/options with runtime overrides before building filter counts. A fully
covered issue class is removed from its raw queue and replaced by `Manual
override`; partial coverage retains the raw class plus `Needs manual override`.
Original option-layout methods stay visible as recovery provenance even when a
manual display correction wins.

The inferred-reply queue is now empty. Current native control flow proves that
adjacent trunk clips with `clipOptionIndex=0` are shared continuation, not one
reply per option. The CN builder emits 137 such shared-continuation groups: 98
with nonzero option rows, 35 with zero-valued option rows, and 4 with an
incomplete overlapping Runtime Jump retained as later-route uncertainty.
Completed Runtime Jump routes remain higher priority. The 20 former manual
response overrides for the disproven adjacent-line mappings were retired;
unrelated authored/manual response mappings remain intact.

The table-only `dlg_gm01m5_*` and `dlg_gm02m3_*` clusters demonstrate why the
categories must remain distinct: group-number matching is useful but not
universally chronological. Semantic prompt/answer structure pins groups in
those clusters through WebUI-only overrides; the registered `dlg_gm02m2_1..4`
set adds seven explicit manual placements, including two corrections that move
away from the key match. Two terminal groups in `dlg_f1m12_1` and
`dlg_f1m4_6` remain manually confirmed at their automatic end anchors. The
original tables and `DialogIdTable` provide identifiers and text, but no
surviving authored DialogTree/Timeline anchor for these table scenes.

## Narrative video attachment policy

- Story builder now embeds every resolved narrative-video mapping into its
  resolved conversation, replacing the old dialog plus one-cutscene exception.
  This
  covers cutscene, remotecomm, and any other resolved story file; non-name
  evidence such as `timelinePlayable` supplies authored inline timing when
  available.
- Standalone `video_*` rows are still emitted for direct browsing, but they
  carry `attachTo` for the resolved story key. Story sort uses that attachment
  so the standalone video row stays beside the file where the video is inserted.
- Manual rules in `webui/overrides/narrative_videos.json` cover both known
  filename mismatches and false attachments. `attachInline` manually embeds a
  matching video stem into a target story key, and can set `audioFrom` to copy
  source cutscene audio events into that target during audio relink.
  `suppressInline` keeps known false inline attachments standalone-only.
  `cutscene_e1m3_1` is suppressed for `cs_video_e1m3_1` because the filename
  match should not attach that video to the black-screen cutscene.

## Archive duplicate identity

- `radio_e1m1_2d7` and `nar_media_map01_128_1` have the same localized audio
  transcript. Keep `radio_e1m1_2d7` as the mission `e1m1` row; keep
  `nar_media_map01_128_1` available only from Archive/media grouping and from
  the bidirectional file-page link.
