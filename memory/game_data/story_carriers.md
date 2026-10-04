# Story activation and placement carriers

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, story lane.** What a decoded LevelScript action, Timeline record, or
spatial carrier actually owns, reaches, and places -- and the exact-build native
gate and overlay rules that bound every such claim. The Story reconstruction
model these carriers feed, and everything about presenting the result, is
[`../webui/story_recovery.md`](../webui/story_recovery.md).

## LevelScript, Timeline, and native evidence

Selected LevelScript actions prove Story links under explicit gates. That
covers the carriers Story reads, not the whole LevelScript family.

- LevelScript actions, headers, UIDs, callbacks, lists, and target carriers are
  accepted only through versioned parsers and bounded validation.
- Active evidence uses one logical-path overlay. Persistent replaces the
  complete StreamingAssets file; changed shadow data is decoded from active
  bytes or rejected.
- A direct playback carrier requires one typed header-to-action path. Preload,
  load, stop, sibling actions, foreign headers, unresolved graph shapes, and
  raw numeric hits remain diagnostics.
- CallServer ordering requires one complete linear Story-to-callback-to-Story
  closure with no branch, merge, loop, truncation, or ambiguous target. A
  one-sided path adds no cross-Story edge.
- Timeline track/clip ownership proves authored scheduling, not Director
  activation, selected option, or Wwise playback.
- Native evidence is locked to exact `GameAssembly.dll` and metadata hashes.
  Registration order and code addresses never imply Story order.

## Native claims across a client update

- A contract records its build in its own `nativeInputs`/`sources`; no module
  repeats that hash. On another build it reports `mismatched` until the claim
  is proved again, and only names carry over: addresses, tokens, offsets,
  registers and enum values are re-derived, and code registration is located
  from the metadata image names, never pinned.
- Claims that re-prove from the binary have a regenerator (CallServer callback,
  cutscene case resolution, iFix patch, cinematic queue, TeleportParam). Census
  conclusions (identity-carrier negative boundaries, cross-system consumers)
  have none and stay `mismatched` until reviewed again.
- Instruction-shape analyses must survive codegen churn. The current build
  wraps many methods in an iFix patch-flag test, moves rare paths into
  separate `.pdata` fragments, calls unnamed helpers (struct-argument shims,
  inlined copies of named methods), reallocates saved registers, and widens
  short jumps to rel32 `jcc`. A body is the function plus every fragment
  chained to it by `UNW_FLAG_CHAININFO` (`BodyIndex.chained_fragments` in
  `scripts/game_data/il2cpp/body_claims.py`), however reached; a jump-target
  walk misses fragment-to-fragment edges. Follow one level into an unnamed
  helper, name a jump from its opcode, accept any save/restore register pair,
  and label a helper-reached callee as such. Compiler-generated names
  (`<M>d__N`, `<>c__DisplayClassN_M`, `b__N_M`) renumber between builds; match
  them with the ordinal normalized, and only when unique.
- An iFix wrapper may test its patch id after a class-init prologue, so an
  opening-window miss does not prove it absent. The inlined
  `TaskCondition.InvokeOnIsCompleteChangeAction` escapes a hook on the named
  method (`scripts/game_data/mission_task_paths_native.py`).
- `withinActiveArea` is hysteresis, proved from `_CalcWithinAreaHysteresis`:
  `!rangeSensitive || hit(enterShapes) || (prevWithin &&
  !IsNullOrEmpty(exitShapes) && hit(exitShapes))`. The outside list is a hold
  zone, not an exclusion zone ("outside hit clears" was the previous build).
  The inlined call site is tied to it `conditional`ly (`protocol_registry.py`).
- Consumer meanings the Story builders cite are claims about named bodies
  proved on the installed build (`contracts/story_native_consumers.json`,
  `contracts/dialog_finish_native.json`), not pinned tokens. The current
  DialogTreeIfNode, Timeline option-index (a wider current-or-previous gate)
  and `Branch.Execute` order readings are in
  [`story_native_consumers_native.py`](../../scripts/game_data/story_native_consumers_native.py).
- A generated artifact made on one build is current only when its recorded
  native hashes equal the installed build's. The reverse-PPtr audit (Story
  root playback aliases) and `webui/story/dynamic_scene.json` were made on the
  previous build and publish nothing until regenerated. The reverse audit
  regenerates through `scripts.webui.story_recovery.audit_story_objects` after
  an export published with `--animestudio-object-index`; `dynamic_scene.json`
  has no generator (see `scripts/webui/story/dynamic_scene.py`).
- Mission Pipeline `RUNTIME_CONTRACT` rows are re-verified by name each run
  (`scripts/webui/mission_pipeline/runtime_contract_native.py`); a row whose
  chain no longer holds is `link_failed` and needs a fresh reading, not a pin.

## Current mission JsonData carrier boundary

The selected VFS ledger and exported `game/Json` bytes agree for the active
LevelScriptData, LevelData, LevelConfig, SpawnerConfig and MissionRuntimeAsset
families; that direct comparison is needed because the export lacks
per-output provenance, so `verify_export_freshness` alone cannot authenticate
every file's content.

- Changed LevelScriptData, LevelData and SpawnerConfig files close at physical
  EOF with `levelscript_binary.frame_levelscript_declared_root` and declarations
  derived from the matching installed native build: the byte boundary is
  complete, member names stay `direct`. Changed LevelConfig files close under
  `decode_level_config`. Both MissionRuntimeAsset main and meta sets pass their
  named schema readers (`scripts/game_data/schemas/mission_runtime_main.py`);
  the main contract's `currentCorpus` header still identifies the older
  reviewed baseline and is not a current-corpus gate.
- The source path chain is LevelConfig's signed `levelDataPaths` int64 -> the
  authenticated `StringPathHash.bin` bucket/path-offset pair -> active LevelData
  logical path. LevelData `levelScriptBriefDataDict` stores a `dataPath.hash`;
  a unique catalog path plus equality of its dictionary key, embedded
  `scriptId` and LevelScriptData filename stem proves that script reference.
  `spawners[].configId` matches the SpawnerConfig root `configId` and path.
  These are JsonData source-path and typed-id joins; Unity CAB/PathID identity
  applies only when crossing into serialized Unity objects, and a filename
  resemblance alone is insufficient.
- Mission name and description keys resolve directly in the byte-verified
  `TextTable`; matching Dialog prefixes are candidates until a typed
  mission-to-dialog field connects them. A level field, a mission name in a
  LevelData filename, script brief, condition, or `mainPathQuests` array proves
  authored definition or reference, **not** client activation, a server quest
  branch, or a played Story. Producer-to-mission ownership and activation
  order stay unresolved until an exact consumer trace or observed runtime event
  joins them; the source joins never become a Story edge or order on their own.

## Shared mission state and condition connections

[`mission_shared_native.py`](../../scripts/game_data/mission_shared_native.py)
re-evaluates the reviewed named claims in
[`mission_shared_native.json`](../../scripts/game_data/contracts/mission_shared_native.json)
against explicitly selected assembly and metadata paths, with input gates
before and after evaluation. Its bodies are limited to exact `.pdata` extents
and unwind-owned fragments; unnamed helper bytes do not silently supply a
callee. Field predicates match offsets, not typed receivers or complete control
flow. The typed chains below also rely on reviewed instruction and metadata
evidence. All behavior describes native default paths: live IFix selection,
server policy and unvisited runtime execution remain unresolved.

- Mission quest state, objective progress, and LevelScript task state use
  separate message paths. `MissionSystem.Handle_QuestStateUpdate` reaches
  `StartQuest`/`SucceedQuest`; `Handle_MissionStateUpdate` reaches
  `CompleteMission`. Objective updates copy `ObjectiveData` and refresh
  progress. Runtime `ObjectiveData.Copy` callers distinguish logic and display
  destinations in both initial synchronization and later updates; duplicate
  copies of one incoming condition are not independent completion messages.
  Its receiver fields are before-copy snapshots, so a missing old receiver ID
  does not erase the explicitly observed incoming ID.
  Tracking data identifies navigation/presentation targets and does
  not replace a completion condition. These consumers do not establish a
  Mission quest-to-LevelScript task owner.
- `MissionSystem.OnSubConditionProgressChanged` retains an explicit quest
  argument even when the supplied condition's stored `parentQuestId` is null.
  Retained quest definitions can independently locate that condition within a
  combined objective. Restoration observations include a supplied progress
  value that differs from the pre-entry progress cache, followed by another
  request for the same quest and condition with a different supplied value.
  Preserve argument and cache separately; neither callback counts nor their
  values alone identify player actions, incoming objective-map contents, or
  acknowledged server progress. Stored condition types do not authenticate
  the receiver's runtime subtype. Advanced-progress UI refresh remains a
  separate path.
  Active identification evidence now includes `m1m70_q#2`: `StartQuest` enters
  with `isNewQuest=true`, and a later callback supplies progress `1` while the
  pre-entry progress cache is `0`. The explicit quest and stored parent agree;
  archived quest/objective membership selects `CheckSnapshotIdentifySuccess`,
  rather than its reused condition ID alone. Later deactivation retains a
  `True` result and progress `1`; separate carriers record quest success and
  mission completion. These are separate named entries and cache
  snapshots, not a reconstructed request/reply pairing.
- Default Mission client activation and result-callback binding select leaves
  whose virtual `get_conditionType` returns `ClientOnly`. Combined objectives
  recurse into exact `CombineCondition` children and apply that selection to
  their leaves. `MissionSystem.IsServerCondition` classifies the other enum
  values as server conditions. `GameConditionBoth` inherits this activation
  selector; its name does not mean both implementations execute for every
  quest. The symbolic enum/getter checks re-resolve the selected metadata and
  bounded dispatch helper. Their predicates check instruction relationships;
  branch meaning also relies on the reviewed bodies, and does not identify a
  live receiver, IFix replacement or authoritative server rule.
  Photo/identification objectives (`CheckSnapshotIdentifySuccess`) inherit
  `GameConditionClient`, whose default getter returns `ClientOnly`; they are
  now represented by a retained active callback as well as source evidence.
  The admitted restoration and active identification calls share an
  authenticated return into a Boolean delegate specialization: it widens the
  Boolean argument to the supplied progress integer and resolves the Mission
  closure's quest and condition.
  The reviewed default `GameCondition.set_result` path supplies whether the
  changed result equals `True`. These observations therefore demonstrate a
  Boolean-result bridge, not arbitrary numeric counters. The caller witness
  does not reconstruct every earlier frame or select an IFix branch.
  Identification group IDs must be distinguished from an entrust's snapshot
  preset: the mission condition's group joins `SnapshotIdentifyGroupTable`
  to target IDs, then the base and target-family tables supply stored target
  requirements. A sphere-family target can describe an empty interactive
  template rather than a named tree entity; localized scenery does not prove
  its live entity identity. The capture recipe now retains named group
  registration/notification entries and snapshot-condition lifecycle/callback
  context and the callback's supplied string group ID. The closed
  `EventData<string>` layout is proved from its selected generic container,
  sole instance type-parameter field, sequential layout and default class
  size. Open-generic native size/offset rows are placeholders and must never
  supply closed-instance offsets. Layout does not establish argument passing:
  the selected snapshot callback receives this eight-byte value indirectly.
  Preparation separately proves the entry argument's zero-offset pointer load
  reaching a named string comparison, retaining register identity across calls
  and control-flow joins. A small native equality wrapper is followed only
  when it preserves both string arguments and reaches the named two-string
  comparison. Missing or changed proof rejects preparation. An earlier inline
  read failed in a live photo callback; its failed journal remains diagnostic
  evidence and cannot be admitted as a complete collection. Together, layout
  and passing proofs enable a payload-to-condition entry association; the bound group parameter, actual comparison/result,
  IFix selection and progression remain unobserved.
  `InteractiveCheckInt` is a server-condition family, with no declared local
  event-check lifecycle. Named interactive state requests, integer property
  callbacks and incoming packet identities provide separate carriers for its
  investigation. Old/new callback arguments are supplied values, not proof of
  a blackboard write; stored EntityPtr logic IDs, entity server IDs and packet
  IDs must stay distinct until an explicit join is established. Incoming
  property/objective maps and server completion rules remain unresolved.
  The reviewed `interactivePropertyDelivery` claims identify the default
  packet path through `EntityManager.ServerSyncInteractiveProperty` to
  `InteractiveInfo.UpdateServerProperty`, including only unwind-owned native
  fragments. The consumer reaches the retained server-data property blackboard
  and has a separate loaded-entity blackboard branch. An absent
  `InteractiveRootComponent.OnInteractivePropertyUpdate` entry therefore does
  not establish absent property delivery; this default-body distinction does
  not identify the branch executed in an earlier session.
  Conversion reads the wire parameter's real/value type selectors and integer
  list storage. A list field is not a concrete scalar value, and unproved
  generic value-field offsets cannot establish a closed numeric layout. The
  blackboard setter's named dictionary lookup is validated; its remaining
  mutation helpers and existing-value behavior still need their own proof.
  The capture recipe separately retains the property consumer's stored
  entity-data ID, level, template, parent script and generation alongside the
  supplied packet identity, and the navigation consumer's supplied signed
  old/new state arguments alongside its explicit entity argument's stored
  server/level/script identity. These are entry associations, not applied
  writes or authoritative Mission child values. Default navigation dispatch
  is conditional and precedes blackboard setter calls; observed ordering alone
  cannot establish nesting or causal ownership. Incoming Mission objective
  dictionaries remain a separate carrier from both property blackboards.
- `StartQuest` distinguishes restoration from a newly entered quest. The
  world-ready restore path passes `isNewQuest=false`; the quest-state update
  path derives the flag from the prior state. A method entry alone cannot
  identify a new progression. Client lifecycle phase dispatch uses the exact
  `(questId, QuestAction)` pair in `MissionRuntimeAsset.runtimeClientActionMap`,
  reconstructed from matching key/value array positions. A missing key returns
  without an authored ActionMap action; a hit forwards the stored start-node ID
  to `ActionMapAsset.RunAction`. Other script or server effects remain possible.
  An observed null ActionMap key does not mean the phase map is empty: explicit
  mission/start-node carriers and authenticated caller sites can still retain
  its dispatch into an embedded action map.
  Daily variants can share a localized title, root condition IDs and radio
  assets while selecting different scripts and start nodes. Identify the
  observed variant through explicit mission/quest carriers and the retained
  definition; neither the visible title nor a reused radio ID selects it.
  A condition ID alone is not a globally unique mission owner.
  Mission completion observations include the incoming mission-state carrier,
  `CompleteMission` with its supplied succeed ID, and the corresponding
  `Processing` to `Completed` state-event arguments. Cleanup can revisit
  explicitly owned conditions from earlier quests with zero entry progress
  caches. Such deactivation entries are not new quest failures or recomputed
  condition results. A subsequent mission's availability and acceptance need
  their own identity-bearing notifications; adjacency does not establish its
  unlock dependency or reward credit.
- Objective presentation has a separate numeric consumer. The default
  `ObjectiveData.GetValue` supplies its stored condition ID and values
  dictionary to `CollectionExtensions.GetValueOrDefault`. The reviewed
  `Copy` body clears and repopulates a destination dictionary from the incoming
  objective map; named calls and field reads do not authenticate every loop
  key/value transfer. Preserve the incoming map, the copied completion flag
  and the displayed count as separate carriers.
  `CombineCondition` presentation getters sum each child's numeric presentation
  value or target. For an `Objective` displaying a multiple combined condition,
  the default progress getter instead counts children whose
  `GetResultByProgress` comparison passes; its target is the child count.
  `GetResultByProgress` compares current progress with the configured target
  using the virtual comparator. It does not read the cached condition result.
  A single combined condition uses a completion-based presentation; an explicit
  display condition and advanced progress have separate branches. Completed
  objective show data can present its target as progress. These default paths
  explain how partial counts can appear without a per-child Mission callback;
  they do not identify the numeric values delivered in a retained session or
  establish the live IFix branch.
- `CheckTalkOptionFinish` belongs to `GameConditionBoth`. Activation resolves
  and caches its dialog/finish operands, checks existing finish history
  immediately, and binds `Check` to `ON_SYNC_ALL_DIALOG` and `ON_FINISH_DIALOG`;
  deactivation removes both bindings. The corresponding CinematicSystem
  handlers populate or update the client finish-history dictionary before
  raising those notifications. A negative configured finish ID accepts an
  existing history entry; a nonnegative ID must occur in its recorded finish list.
  This can use synchronized prior history and is distinct from a UI exit.
  `SetFinishId` stores a local value and `_SendServer` forwards supplied finish
  IDs/options, but their complete cached-value/request/reply ownership remains
  unresolved. Entry observations from the typed Mission trace recipe show that
  the supplied finish ID can differ from the cached field at `_SendServer`;
  retain both instead of substituting the cache for the outgoing argument.
  Sends have been observed in both `Exiting` and `Exited` states through
  different callers, which does not by itself identify their branch predicate.
  Dialogue wire identities have a separate explicit join: `DataManager` owns
  `DialogIdTable`; the outgoing consumer uses `dialogStrToNum`, and the incoming
  finish consumer uses `dialogNumToStr`. The stored MemoryPack table has bounded
  dialogue/option maps and inverse maps that can be checked through EOF with
  the maintained table readers. Preserve these bytes with the capture. A
  current-source mapping can name an incoming wire ID without timing-based
  pairing, but does not correlate a particular request or expose unsampled
  finish-list contents; it is not a snapshot of the live dictionary.
  A quest configured with `CheckTalkOptionFinish` can have observed success
  and a generic condition deactivation without any entry at the selected
  type's `OnActivate`, `Check`, or `OnDeactivate` hooks. Its default virtual
  type is `CheckTalkFinish`, outside the `ClientOnly` selection above, so the
  default Mission client path explains how those specialized hooks can be
  absent. Matching authored dialog/finish operands to playback still does not
  authenticate the live subtype, IFix selection or server decision.
- `CheckLevelScriptPropertyBool` also inherits `GameConditionBoth` and returns
  the non-`ClientOnly` type `CheckLevelScriptProperty`. Its default local
  `OnActivate` resolves the map, script, property key, comparator and boolean
  operand. `_DoCheck` reads the property, assigns a comparison result and
  registers a property-change listener; `_OnEvent` compares the event value
  with the cached operand, and deactivation removes the listener. This is a
  boolean result path, not a marker counter. `GameCondition.set_result` can
  forward a boolean result through a bound callback to
  `OnSubConditionProgressChanged`, but the Mission callback binder above
  selects `ClientOnly` leaves. These bodies therefore do not prove that a
  stored script-property objective uses that callback in a live mission.
  Individual property writes, incoming objective-map entries and active
  partial progress need their own identity-bearing observations.
  Retained `m1m12_q#2` evidence separates these gaps: its archived combined
  objective checks the marker boolean properties, and its copied root
  completion flag remains false before the final true update and explicit
  quest/mission completion. The screen separately records partial HUD counts.
  No per-condition Mission progress callback is retained for that quest, so
  neither the root flag nor the screen identifies a changed child property or
  the incoming numeric count. Observed LevelScript task notifications carry a
  different script ID from the archived marker operands; their timing cannot
  establish property ownership.
  The property's synchronization consumer is also explicit: the default
  network handler constructs a script pointer from the incoming script ID and
  forwards its property map. The manager resolves that runtime; its
  `ServerSyncProperties` loop obtains the brief-data property-ID map and
  blackboard, looks up each ID, converts its value, writes the mapped key and
  recycles the temporary variable. The reviewed handler does not establish
  scene ownership from the packet's scene field. Missing maps, unknown IDs,
  failed conversions and an unresolved runtime remain distinct refusal paths.
  Complete, ledger-authenticated `LevelData` owners supply the marker scripts'
  `LevelScriptBriefData`: the marker Boolean defaults are false, and their
  numeric IDs map to the exact `bMarker1`/`bMarker2`/`bMarker3` keys. The separate
  full `LevelScriptData` graph has null property fields and only effect-save
  variables in its graph blackboard; that does not erase the brief-data map.
  Its authored actions contain marker property readers but no Boolean setter.
  These stored defaults and the native sync path establish a possible writer
  carrier, not an observed property update or the server rule producing it.
- The retained `m1m43` gathering daily exercises the same distinction through
  an `InteractiveCheckInt` combined objective. Its archived MissionRuntimeAsset
  reuses `m1m41` display-text keys but supplies its own objective and entity
  operands; shared text does not make the mission IDs interchangeable. The
  maintained `mission_trace_inspect` verifies the package and source inventory
  before decoding the bounded recipe in
  `scripts/game_data/contracts/mission_trace_capture.json`.
  In that session the incoming interactive packet IDs match the five archived
  operands, while copied combined-root completion stays false through partial
  HUD advances and becomes true at the final update. Explicit quest-state,
  successor acceptance and mission-state entries complete the observed path.
  This is a case-specific packet-ID/operand match, not a universal equivalence
  between logical IDs and server IDs. No Mission subcondition-progress entry
  names the gathering quest, and neither selected interactive property callback
  nor state-request hook fires. The network hook observes identity fields only:
  delivered property values, applied writes, incoming objective numeric values
  and the selected live consumer remain unresolved. Adjacent packet/objective
  entries and independently visible HUD counts cannot supply those missing
  payloads or causal ownership. The default Server condition selection is
  consistent with the missing local callbacks; absence alone proves no live
  subtype, IFix choice or callback failure.
- `GetScopeMask` uses the virtual force-override tuple when enabled, otherwise
  the authored scope mask; `GetUseGraphScope` reads the authored graph flag.
  Named `ScopeName` flags describe the stored scope domain. These selectors
  do not establish the effective current or graph scope, script availability,
  or condition execution admission.
- `CheckActivityConditionalStageStatus` and `GameConditionServerPlaceHolder`
  inherit the server-condition lane and declare no local `Check`; the activity
  class also declares no activation override. Activity-stage descriptions and
  block-condition admission are configuration consumers, not proof of a local
  stage-state query. Placeholder conditions can compare delivered progress
  locally; the client does not reveal the server criterion that produced it.
  Keep authored stage/comparator/threshold parameters, received progress, and
  authoritative completion policy as distinct evidence. Condition lifecycle
  entries can retain progress equal to the threshold while the cached result
  remains `Undecided`; these snapshots do not observe a `Check` return or prove
  that a local comparison produced `True`.
  Activity configuration supplies a separate stored dependency join:
  `ActivityConditionalMultiStageTable` associates stage, mission and time keys;
  its condition and stage-owner tables retain explicit predicates, while
  `TimeRangeTable` retains candidate opening/closing ranges. A named
  `MissionStateEqual` predicate can establish the configured prerequisite
  independently of adjacent runtime notifications. It does not prove server
  evaluation, the selected range/timezone, or the actual unlock instant.
- LevelScript local condition changes send script/task/condition identity and
  absolute progress (`isAdd=false`). Incoming task-state messages apply task
  state through manager/runtime/task-runtime consumers. Separate condition maps
  look up condition IDs, update `TaskCondition.isCompleted` and invoke its
  completion delegate inline; a hook on the named invoker alone misses this
  path. `TaskCondition.OnTaskStateCompleted` disposes the condition rather than
  writing that flag. The native default `UpdateLevelScriptTaskStartFinish` path
  is a no-op, while script-done synchronization follows its own state update.
  The typed `UpdateTrackingObjectiveCompleted` entry is shared tracking
  behavior: captures include both setting and clearing completion, including
  clearing calls without an intervening observed progress-message handler.
  Its objective-kind argument is not a condition-map key; it does not expose
  unchanged map items or uniquely identify the source condition.
  Neither task IDs nor temporal proximity supply Mission quest ownership.

The reusable entry/field declarations are in
[`mission_trace_capture.json`](../../scripts/game_data/contracts/mission_trace_capture.json).
Interpret their observations with the session's retained profile and explicit
source identities; entry snapshots do not prove successful returns or message
causality. Capture inventories and sequence-level corroboration remain under
`reports/runtime_capture/`.

Use the named MissionRuntimeAsset schema reader for corpus comparisons;
its reviewed baseline count is not a current denominator. Export freshness and
schema closure describe stored definitions, not VFS byte identity or runtime
activation. Changing census counts, exact native windows, excluded proof checks
and inventories stay under `reports/runtime_capture/`.

## LevelScript FMV path to installed Video

`PlayFmvAction._moviePath` is a stored constant `Param<string>`. Each
authenticated `cs_video_*` value resolves to exact Video logical paths under
`Data/Video/PC/Narrative/Cutscene/` -- a base `<id>.usm` or a complete `f_`/`m_`
pair -- through
[`levelscript_fmv_video_corpus.py`](../../scripts/game_data/levelscript_fmv_video_corpus.py)
and the reviewed `levelscript_fmv_video_native.json` consumer route
(`GameAction.PlayFmv` -> `GetGenderedFMVId` -> `Narrative/Cutscene/{0}` ->
VFS lookup). This is **conditional** name resolution: gender, iFix state,
activation, playback, mission ownership and order are not proved. The
per-source join is `reports/story/recovery/current_levelscript_fmv_video_join.json`.

## Spatial carriers

Story is placed on Map only through the exact carrier's own authored geometry
or identity: trigger volumes, constant EntityPtr targets, entity lists, patrol
checkpoints, SpawnerPtr/encounter hosts, NPC proxy dialogs and envTalk,
atmospheric NPC clusters, narrative components, reading points, and 3D radio
actions. Each has its own schema and uniqueness gate, under shared rules:

- every constant or getter field is decoded in formatter order and bounded by
  exact consumption;
- dynamic blackboard values, runtime lists, nullable outputs, validation
  predicates, sibling actions, mission context, and proximity never substitute
  for the carrier identity;
- one Story may have several exact authored points; do not choose, average, or
  collapse them;
- placement does not prove activation, mission ownership, runtime actor
  position, or chronology; per-level coverage belongs in the generated frontier
  and map reports.

## What each carrier's identity domain is

Numerically equal ids in unrelated domains are different identities:

- validated local Story trigger volumes carry their own decoded Box/Sphere
  geometry at an authored X/Z position and rotation. Current-build native
  consumers confirm these ids address the LevelScript-local `triggerVolumes`
  domain through a runtime registered-id bridge; **they are not
  WorldEntityRegistry slots.** Their Story links stay distinct from nominal
  mission context and imply neither mission ownership nor runtime firing.
- MissionArea pins have an exact MissionAreaTable Box/Sphere definition and
  remain **Story-unresolved**; proximity never supplies their Story or order.
- NPC proxy rows use their own domain. A build-locked `NpcProxyGetter` reference
  attaches actions through an exact proxy-id/segment/table join and **never
  reuses a numerically equal world-entity identity.** The unreviewed
  `jumpToCampFireGlobalId` tracking field (by name an optional campfire jump
  target) is accepted only at 0 (`npc_proxy_tracking_fields_are_exact` in
  `scripts/webui/story/source_gap/data.py`); any other value or new field fails
  closed until reviewed.
- current-script slot actions resolve through the pinned
  [`entityptr_script_slot_native.py`](../../scripts/game_data/entityptr_script_slot_native.py)
  contract: the lookup is keyed by the current `LevelScriptRuntime` script id
  and slot in `EntityManager`. A unique WorldEntityRegistry script/slot row
  proves the authored map target; **runtime registration and lifetime stay
  unproven.**
- world scenery receives a Story link when one counted `LevelInteractiveData`
  record stores both its exact `embeddedLogicId` and a NarrativeComponent
  `typeId`. e0m0's four tombs use that direct binding, **not numeric order or
  spatial proximity.**

## Registered shells and slot action bindings

- An `int_empty` shell is a registered, unresolved empty slot in its own layer.
- A registered shell referenced by a strict constant `Param<EntityPtr>` inside
  a validated action record becomes a script target **only when a build-locked
  native formatter contract also proves its named member boundary**
  ([`action_entity_fields_native.py`](../../scripts/game_data/action_entity_fields_native.py));
  unresolved occurrences stay candidates. Neither form inherits sibling Story,
  cutscene, or sequence ownership.
- Script-container files, conditions, and ordering anchors are map-level
  context, not repeated onto sibling slots; a point receives a Story or a file
  **only from an exact script/slot consumer.**
- Every spatial world/script registry slot publishes an observational action
  binding status and action array. `no_reference_observed` means only that
  current decoded LevelScript evidence has no matching constant pointer --
  **not that the slot has no action.** Exact and unresolved references stay
  separate even when both address the same slot.
- A dynamic local-output reference becomes a slot action **only when a pinned
  producer contract proves a same-header constant alias**
  ([`entityptr_output_alias_native.py`](../../scripts/game_data/entityptr_output_alias_native.py));
  validated non-alias outputs remain unplaced.
- The exhaustive per-slot audit -- contracted EntityPtr field states,
  diagnostic-only dynamic `idRef`/output/variable references, and non-spatial
  references that must not become map markers -- belongs in
  `reports/assets/map_recovery/action_binding_index.json`.
