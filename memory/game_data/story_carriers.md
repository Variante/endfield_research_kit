# Story activation and placement carriers

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, story lane.** What a decoded LevelScript action, Timeline record, or
spatial carrier actually owns, reaches, and places -- and the exact-build native
gate and overlay rules that bound every such claim. The Story reconstruction
model these carriers feed, and everything about presenting the result, is
[`../webui/story_recovery.md`](../webui/story_recovery.md).

## LevelScript, Timeline, and native evidence

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
  repeats that hash. On another build it reports `mismatched` until its claim
  is proved again there, and only names carry over: every address, token,
  offset, register and enum value is re-derived. Code registration is located
  from the metadata image names, never pinned.
- Claims that re-prove from the binary have a regenerator (CallServer
  callback, cutscene case resolution, iFix patch, cinematic queue,
  TeleportParam); `scripts/README.md` lists them. Census conclusions
  (identity-carrier negative boundaries, cross-system consumers) have none and
  stay `mismatched` until reviewed again.
- Instruction-shape analyses must survive codegen churn, not match one build's
  text. The current build wraps many methods in an iFix patch-flag test, moves
  rare paths into separate `.pdata` fragments reached by a conditional jump,
  calls unnamed helpers (struct-argument shims and inlined copies of named
  methods), reallocates saved registers, and uses rel32 `jcc` where a short
  jump was. A split-off fragment's unwind info carries `UNW_FLAG_CHAININFO`
  and ends in its owner's RUNTIME_FUNCTION, so a body is the function plus
  every fragment chained to it (`BodyIndex.chained_fragments`), however the
  fragment is reached; a jump-target walk misses fragments reached from other
  fragments. Follow one level into an unnamed helper, name a jump from its
  opcode, and accept any save/restore register pair; label a helper-reached
  callee as such rather than as a direct call. Compiler-generated names
  (`<M>d__N`, `<>c__DisplayClassN_M`, `b__N_M`) renumber between builds; match
  them with the ordinal normalized, and only when unique.
- `withinActiveArea` is a hysteresis rule in the current build:
  `!rangeSensitive || hit(enterShapes) || (prevWithin &&
  !IsNullOrEmpty(exitShapes) && hit(exitShapes))`, proved from
  `_CalcWithinAreaHysteresis`. The outside list is therefore a hold zone, not
  an exclusion zone; the previous build's "outside hit clears" reading no
  longer applies. UpdateWithinActiveArea calls an inlined copy, tied to the
  named body by its five arguments and result store (`conditional`).
- Consumer meanings the Story builders cite are claims about named bodies,
  proved on the installed build (`contracts/story_native_consumers.json`,
  `contracts/dialog_finish_native.json`), not tokens pinned by body hash. On
  the current build DialogTreeIfNode delegates to a new
  `DialogManager.GetIfNextIndex`; the meaning holds (outgoing 1 exactly when
  `GameCondition.result == 1`). The Timeline option index now travels
  `DialogTimelineOptionData.optionIndex` -> `DialogChooseOption` ->
  `TimelineRuntimeUtils.TrySetNewOptionIndex` (every director under the root)
  -> `TimelinePlayable.newOptionIndex`; `Evaluate` commits it to
  `curOptionIndex` and keeps the previous one in `lastOptionIndex`, and
  `CheckWillRuntimeElementEnabled` enables an element whose option index is
  zero or equals the current *or previous* selection -- the gate is wider than
  the previous build's single matching value during a switch. Branch-sequence
  order edges are admitted only while the `Branch.Execute` list-order claim
  holds.
- An iFix-wrapped method can test `IsPatched(<its own patch id>)` after a
  class-initialization prologue; a bounded opening-window search that misses
  the test does not prove the wrapper absent. An inlined copy may retain the
  id test, which supports an inlined-hop claim when its surrounding body and
  arguments also match. `TaskCondition.InvokeOnIsCompleteChangeAction` is inlined into
  `LevelScriptRuntime.UpdateTaskMainObjectiveIsCompleted` on the current
  build: the server progress path invokes `m_onIsCompleteChangeAction` without
  calling the named method, so a runtime hook on that method misses this path;
  `contracts/mission_task_paths.json` still names it and is pinned to the
  previous build.
- A generated artifact made on one build is current only when its recorded
  native hashes equal the installed build's. The reverse-PPtr audit (Story
  root playback aliases) and `webui/story/dynamic_scene.json` were made on the
  previous build and publish nothing until regenerated; the latter still names
  layout-v1 export paths. The reverse audit regenerates through
  `scripts.webui.story_recovery.audit_story_objects`, but only after an
  installed-game export published with `--animestudio-object-index`.
  `dynamic_scene.json` has no generator in the tree: its two builders
  (`build_dynamic_scene_mission_control_audit.py` and the LevelScript
  action-bridge audit) were deleted when it was frozen in `74a263c7`, so
  refreshing it means restoring and porting them from history.
- Mission Pipeline `RUNTIME_CONTRACT` rows are re-verified by name each run;
  a hop reached through an inlined copy is `verified_with_inlined_hops`. A row
  whose chain no longer holds is `link_failed` and needs a fresh reading, not
  a pin; the building-panel lock row had its chain written backwards (the
  public `CheckIsBuilding*Locked` checks call `CheckBuildingLock` and build the
  radio).

## Current mission JsonData carrier boundary

The selected VFS ledger and exported `game/Json` bytes agree for the active
LevelScriptData, LevelData, LevelConfig, SpawnerConfig, and
MissionRuntimeAsset families. The current corpus comparison and focused
changed-file probe are in `reports/story/recovery/current_json_mission_carriers.json`
and `current_json_mission_parser_probe.json`. This direct byte comparison is
needed because the existing export lacks per-output extraction provenance;
`verify_export_freshness` alone cannot authenticate every file's content.

The changed LevelScriptData, LevelData, and SpawnerConfig files close at
physical EOF with `levelscript_binary.frame_levelscript_declared_root` and
declarations derived from the **matching installed native build**. The byte
boundary is complete, while member names remain at the `direct` declaration
tier. Changed LevelConfig files close under `decode_level_config`'s exact
reader. Both current MissionRuntimeAsset main and meta sets pass their complete
named JSON schema readers. The main schema contract now admits two previously
known condition types at their newly observed nested positions and one
`_nextID` guide action shape. Its `currentCorpus` header still identifies the
older reviewed baseline; it is not a current-corpus gate. The current
validation uses the active VFS byte comparison and separately recorded
parser probe.

The exact source path chain is LevelConfig's signed `levelDataPaths` int64 ->
the authenticated `StringPathHash.bin` bucket/path-offset pair -> active
LevelData logical path. The changed LevelData `levelScriptBriefDataDict`
stores a `dataPath.hash`; a unique catalog path plus equality of its
dictionary key, embedded `scriptId`, and LevelScriptData filename stem proves
that authored script reference. Its `spawners[].configId` matches the
SpawnerConfig root `configId` and logical path. The current joins are in
`reports/story/recovery/current_levelconfig_path_joins.json` and
`current_leveldata_carrier_joins.json`. These are JsonData source-path and
typed-id joins; Unity CAB/PathID identity applies only when crossing into
serialized Unity objects, and a filename resemblance alone is insufficient.

For example, the new `gm02m27` main/meta pair explicitly stores
`map02_lv002` as its level, while `gm02m27d1` through `d6` store
`indie_dg016`; the related LevelConfig and LevelData files are now bounded
through the path chain above. Their authored mission-name keys, and each
nonempty mission-description key, resolve directly in the current byte-verified
`TextTable`; matching prefixes in Dialog tables are only candidates until a
typed mission-to-dialog field connects them. A level field, matching mission
name in a LevelData filename, script brief, condition, or `mainPathQuests` array proves
authored definition or reference, **not** that the client activated the
mission, that the server selected a quest branch, or that a particular Story
played. Runtime producer-to-mission/quest ownership and the selected
activation/order path are still unresolved until an exact consumer trace or
observed runtime event joins those identities. Do not turn the new source
joins into a Story edge or chronological order on their own.

## LevelScript FMV path to installed Video

The current `PlayFmvAction` layout in the selected
`levelscript_union_tags.json` contract and the strict
`codecs/levelscript/fmv.py` field decoder identify `_moviePath` as a stored
constant `Param<string>`, not a string inferred from a neighboring action.
The focused current LevelScript replay reaches 19 such actions in 19
source-authenticated files. Rechecking each export's SHA256 and VFS data MD5,
then the tagged string inside that action's physical byte range, finds 19
distinct `cs_video_*` values. Exact audited Video logical paths resolve six
values as a base `<id>.usm` file; the other 13 have one `f_<id>.usm` and one
`m_<id>.usm` file each, all under `Data/Video/PC/Narrative/Cutscene/`.
The per-source and per-file identities are in the generated
`reports/story/recovery/current_levelscript_fmv_video_join.json` receipt.
`levelscript_fmv_video_corpus.py` rechecks this join against the reviewed
`levelscript_fmv_video_native.json` consumer contract, selected native hashes,
the current VFS input set, each source's exported bytes, and each Video file's
audited path/data identity; it fails on a missing base or incomplete gender
pair rather than promoting a name resemblance.

The selected native `PlayFmvAction.Execute` reads its `_moviePath` parameter
and calls `GameAction.PlayFmv`, the route independently listed in the reviewed
`cinematic_queue.json` contract. In the unpatched bodies,
`GameAction.PlayFmv` forwards the name to
`NarrativeUtils.GetGenderedFMVId`, then checks a
`GetCSVideoAssetSubPath` result with `VideoManager.CheckCanPlay`.
`GetGenderedFMVId` selects the literal `f_` or `m_` prefix by narrative
gender, concatenates it with the original id, checks the candidate through
`_CheckIfFMVExists`, and falls back to the unprefixed id if that check fails.
`GetCSVideoAssetSubPath` formats `Narrative/Cutscene/{0}`;
`VideoManager.GetVideoAssetPath` appends `.usm` when needed, and
`TryGetVideoPlayFullPath` calls `Beyond.VFS.VirtualFileSystem.TryGetAssetFullPathInfo`.
The selected method bodies, literal usage cells and branch bytes are recorded
in `reports/story/recovery/current_levelscript_fmv_video_native.json` with
the installed native hashes. This is **conditional** source-to-video name
resolution: the selected gender, active iFix patch state, action activation,
actual playback, mission ownership and chronological order are not proved by
these static bytes or VFS matches.

## Spatial carriers

Story may be placed on Map only through the exact carrier's own authored
geometry or identity. Maintained carrier families include validated trigger
volumes, constant EntityPtr targets, explicit entity lists, patrol checkpoints,
SpawnerPtr/encounter hosts, NPC proxy dialogs and envTalk, atmospheric NPC
clusters, narrative components, reading points, and exact 3D radio actions.

Each family has its own schema and uniqueness gate. These rules are shared:

- every constant or getter field is decoded in formatter order and bounded by
  exact consumption;
- dynamic blackboard values, runtime lists, nullable outputs, validation
  predicates, sibling actions, mission context, and proximity never substitute
  for the carrier identity;
- one Story may have several exact authored points; do not choose, average, or
  collapse them;
- placement does not prove activation, mission ownership, runtime actor
  position, or chronology;
- changing per-level carrier coverage belongs in generated frontier and map
  reports.

## What each carrier's identity domain is

Two carriers can address numerically equal ids in unrelated domains, so the
domain is part of the identity:

- validated local Story trigger volumes carry their own decoded Box/Sphere
  geometry at an authored X/Z position and rotation. Current-build native
  consumers confirm that these ids address the LevelScript-local
  `triggerVolumes` domain through a runtime registered-id bridge; **they are not
  WorldEntityRegistry slots.** Their Story links stay distinct from nominal
  mission context and imply neither mission ownership nor runtime firing.
- MissionArea pins have an exact MissionAreaTable Box/Sphere definition and
  remain **Story-unresolved.** Spatial proximity never supplies their Story
  files or Story order.
- NPC proxy rows use their own identity domain. A build-locked `NpcProxyGetter`
  reference can attach actions through an exact proxy-id/segment/table join; it
  **never reuses a numerically equal world-entity identity.**
- MissionRuntimeAsset `trackingInfoList` rows gained `jumpToCampFireGlobalId`
  on every tracking-info type in the current client (NpcProxy, Pos,
  MissionArea, Entity, Sns, JumpToUI, NPC). It is 0 on every row but one
  PosTrackingInfo; by name an optional campfire (fast-travel) jump target, not
  yet reviewed against native code. The NpcProxy tracking reader accepts it
  only at 0 (`npc_proxy_tracking_fields_are_exact`); any other value, or any
  other new field, fails closed until its meaning is reviewed.
- current-script slot actions resolve through a pinned native resolver
  contract: the runtime lookup is keyed by the current `LevelScriptRuntime`
  script id and slot in `EntityManager`. A unique WorldEntityRegistry
  script/slot row proves the authored map target, while **runtime registration
  and lifetime remain explicitly unproven.**
- world scenery receives a Story link when one counted `LevelInteractiveData`
  record stores both its exact `embeddedLogicId` and a NarrativeComponent
  `typeId`. e0m0's four tombs use that direct binding, **not numeric order or
  spatial proximity.**

## Registered shells and slot action bindings

- An `int_empty` shell is a registered but unresolved empty slot. It is not an
  understood interaction, and it stays in its own unresolved layer.
- A registered shell referenced by a strict constant `Param<EntityPtr>` value
  inside a validated action record becomes a script target **only when a
  build-locked native formatter contract also proves its named member
  boundary**; unresolved occurrences remain candidates. Neither form inherits
  sibling Story, cutscene, or sequence ownership.
- Script-container files, conditions, and ordering anchors are map-level
  context. They are not repeated onto every sibling slot, and a point receives
  a Story or a file **only from an exact script/slot consumer.**
- Every spatial world/script registry slot publishes an observational action
  binding status and an action array. `no_reference_observed` means only that
  current decoded LevelScript evidence contains no matching constant pointer;
  **it is not proof that the slot has no action.** Exact and unresolved
  references stay separate even when both address the same slot.
- A dynamic local-output reference becomes a slot action **only when a pinned
  producer contract proves a same-header constant alias**; validated non-alias
  outputs remain unplaced.
- The exhaustive per-slot audit -- every contracted EntityPtr field state,
  diagnostic-only dynamic `idRef`/output/variable references, and the
  non-spatial references that must not become map markers -- belongs in
  `reports/assets/map_recovery/action_binding_index.json`, not here.
