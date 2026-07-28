# Endfield game Story recovery

This is the single durable memory note for Story reconstruction, mission and
scene order, quest attachment, dialog branches, option routes, LevelScript
control flow, narrative video placement, and the source-only recovery queue.
Generated reports remain under `reports/`; active workflow contracts remain in
`README.md`, `scripts/README.md`, and `webui/README.md`.

## Current conclusion

The original client data supports a useful **partial order**, not one
authoritative total scene list for every mission. The current strict CN audit
contains:

- 486 missions and 8,853 candidate Story scene placements;
- 1,426 accepted strong scene edges and 820 retained supported-topology edges;
- 1,320 transitively reduced component edges;
- 3,638 comparable pairs out of 248,838 within-mission pairs (1.46%);
- 5,096 isolated scenes and 2,063 scenes with weak/supported evidence only;
- zero cyclic strongly connected components;
- 250 explicit quest forks, 53 quest merges, and 59 authored cross-scene
  option groups.

Unknown relationships must stay unknown. Filename suffixes, file order,
generated rank, OCR, gameplay calibration, and manual WebUI overrides can be
useful display or investigation inputs, but they are not original-data proof.
The July 23 audit removed 781 false chronology promotions without discarding
their source topology: 347 generated `questSequence` relations, 203
`authoredMenu` relations, eight `questFailGuard` relations, and 223 generic
`levelscriptSceneChain` relations. The installed
July 11 binary exposes `QuestInfo.prevQuestIdList` and
`MissionRuntimeAsset.BuildConnectionBetweenLayers` as the inter-quest
dependency contract. It exposes no playback-order contract for the Story
builder's heterogeneous quest-local reference concatenation; menu reachability
can be cyclic, and failed-condition Story references are branch-closing
dependencies rather than a guaranteed two-scene execution order.
The same binary's complete ActionBase formatter table proves that
`levelscriptSceneChain` is not a typed playback relation. The legacy chain view
flattens any Story-looking payload while following `nextId`; those payloads
occur on `PreloadDialogAction` (`0x0377`), `PreloadCutsceneAction` (`0x0376`),
`RemoveNPCDialog` (`0x0389`), `OverrideNPCDialog` (`0x0344`), and stop actions
as well as actual playback actions. It can also join records across separate
physical `ActionSerializedMap` list roots. These references remain useful
control/configuration topology, but only the typed native playback decoder's
exact serialized paths or a decoded dialog-exit relation establish chronology.
The same audit demotes 26 reciprocal file-level `questPrev` projections. In
those cases, distinct directed quest instances project onto the same reusable
Story files in both directions. The quest DAG remains original-data evidence,
but it cannot select one global order for the collapsed file nodes. Each
demoted edge remains inspectable with
`demotionReason=reciprocalQuestProjection`. Reclassifying the generic
LevelScript chains also explains all five formerly remaining cycles:
`a1m13`, `e0m2`, `e2m7`, `e11m2`, and `f1m32`. Each depended on treating a
preload/remove/override reference or a chain crossing serialized list roots as
playback. The strict graph now has zero cycles; no numeric or manual tie-break
was used.

Filename ownership no longer hides an otherwise exact native chain. Starting
from index-backed mission scenes, the strict audit admits a cross-owner Story
key only when its exact serialized event-to-action path is a strict prefix or
extension of an anchored scene path under the same level, script, and event
header. Equal paths, divergent arms, separate events, generic host
co-membership, file order, and `levelscriptChain` do not expand membership.
This adds 21 context placements across 14 missions and exposes 31 strong edges.
For `e11m6`, the original `23100100001` Leader-enter path proves
`dlg_e11m5_9 -> radio_e11m6_39`; `23100100002` proves
`cutscene_map02_lv008_liexi_xs_m_03 ->
cutscene_e11m2467_liexitexiao_03` before the latter cutscene path reaches
`remotecomm_e11m6_1` and `radio_e11m6_4`. These are binary path relations, not
filename, OCR, or manual-order promotions.

The original binary also resolves the misleadingly named ActionBase
`Branch` (`0x002d/0x09`) as an ordered action list, not conditional fan-out.
Runtime metadata gives `_idList` and `m_index`; `Branch.Execute` at
`0x18764d990` reads fields `+0xd0`/`+0xd8`, calls
`ActionBase.SetResultReservedID` for non-final entries and
`SetResultNextID` for the indexed child, increments the index, and resets it at
the list end. Exact full-payload `_idList` decoding restores 43 distinct
event-owner paths across 14 Story keys. Thirteen formerly actionable weak-only
keys become exact-native closed, while c28m1 gains the one new strict edge
`radio_c28m1_9 -> radio_c28m1_15`. Different `Branch.sequence[n]` entries are
not misreported as `Split` arms, and any earlier true `Split` divergence
remains unordered.

The separate cross-reference audit compares only the 1,425 strict direct edges
with the fallible manual and OCR lists. It currently finds manual agreement on
869 edges, disagreement on 244, and 312 uncovered; OCR agrees on 376,
disagrees on 10, and leaves 1,039 uncovered. Twelve strict edges have opposing
manual/OCR judgments. These counts are a review queue, not evidence weights:
neither agreement nor disagreement changes the source graph.

The Mission Pipeline attachment audit is a separate, changing coverage metric
over 490 exported MissionRuntime graphs. The current generated report at
`reports/story/build/mission_pipeline_story_binding_coverage_CN.md` records
5,273 unique pipeline-relevant or exactly connected cross-owner
`dlg`/`sns`/`cutscene`/`black`/`remotecomm`/`radio` files: 4,065 have at least
one original-data connection across 4,361 mission placements and 1,208 remain
unassigned. The denominator now admits 106 Story files whose nominal Story
owner is not one of the 490 MissionRuntime ids only because accepted generated
pipeline edges connect them; this repairs an accounting blind spot and does not
invent 106 new evidence claims. Of the unassigned rows, 153 have an exact current-build native
playback action but still lack a decoded mission/quest trigger. Every one of
those playback routes now has a native ActionHeader event name and exact
serialized control path from the complete installed-build union table. Those rows remain
visible as unresolved evidence rather than being attached by filename or OCR.
The global binary boundary groups the unassigned native-playback files under
158 exact serialized runtime-receiver nodes (182 receiver-to-Story placements),
leaving zero exact-native rows without a decoded runtime selector.
These nodes expose entity/slot/property, script event, spawner,
patrol/checkpoint, signal, guide, and stage selectors but do not count as
mission ownership.
The maintained offline activation-frontier audit now collapses those 158 nodes
to 93 hosting LevelScripts and decodes the next static layer. Seventy scripts
are `Manual`, 13 are `ByEnterStartShape`, and 10 are `SameWithActive`. Ten have
an exact original-data SubGame `bindScriptId` activation scope; the SubGame
rows still carry no mission owner. Of the remainder, 54 are Manual with null
start shapes, null task maps, zero parent script ids, and no incoming literal
cross-script ManualStart target. Across all 93, zero typed MissionRuntime
objective operand names the receiver script and the manual-control audit still
has zero incoming literal cross-script target. Only one receiver script is in
an exact mission-named LevelData host, which remains loading/registration
context rather than playback ownership. The 12 non-SubGame scripts with
non-empty authored start shapes also have zero complete exact matches against
every MissionArea shape on their level under the same 0.001 native-vector
tolerance used by accepted trigger-geometry joins. Nearby areas frequently
differ in type, radius, size, or rotation and remain rejected proximity clues.
An exact positive-length MemoryPack string-token census adds a second bounded
negative: 24 receiver scripts have task maps, but only the already
SubGame-scoped `map02_lv002/22800950006` contains any current MissionRuntime id
token (`a1m6d6`, `a1m6d7`). None of the 83 non-SubGame receiver scripts embeds
one. This closes literal mission-id constants across the complete receiver
LevelScript blobs, including their task maps; it does not close dynamic params,
indirect registries, or server-authored activation.
The task-map layer is now decoded rather than searched only for literals. All
24 task-map receiver scripts consume exactly as 31 tasks and 54 conditions
across 11 concrete root `GameCondition` types: entity/interactive checks,
monster-kill and spawner-complete checks, dialog-option completion,
LevelScript property/stage checks, destination checks, and empty combine
envelopes. No receiver task map contains `CheckMissionState`. These operands
are exact authored evaluation or completion dependencies; they neither
activate the receiver nor identify its mission owner. The highest-value next
offline join was therefore to follow each exact entity, spawner, dialog, area,
property, and foreign LevelScript operand into typed same-level sources. That
pass is now complete for the authored object-bearing operands: 46 of 54
conditions resolve to 53 exact sources—26 current-script entity slots, 15
WorldEntity logic ids, five same-level LevelScripts, three same-receiver Story
keys, three same-level MissionArea rows, and one same-level SpawnerConfig. The
same exact dialog/finish, level/area, level/spawner, level/script, and
level/entity operands were indexed across all MissionRuntime assets; zero
condition has a typed MissionRuntime consumer. The eight conditions without a
source are parameter/property or empty combine envelopes rather than missed
authored-object lookups. This closes the task-condition operand route for
ownership on the current export. Source resolution remains useful debug
context but adds no mission, quest, activation, or order edge.
The first complete id census closes the direct task-id route. The 31 task ids
and 51 distinct condition ids occur only in their LevelScripts, LevelData
`lt:p`/`lt:mp` bookkeeping, 13 exact `ScriptTaskExtraInfoTable` display rows,
and 10 exact `SubGameInstanceDataTable.mainTasks` rows. They have zero
MissionRuntimeAsset occurrences. All ten SubGame task rows target the same
bound receiver script and all ten have null `dungeonMissionId`; they sharpen
task purpose/activation scope without adding an owner. The Mission Pipeline
debug payload now publishes the 13 title/objective metadata rows and ten
SubGame main-task joins alongside their conditions.
The durable details live at
`reports/story/recovery/native_receiver_activation_frontier.{json,md}`.
Mission Pipeline debug cards expose the start policy, validated LevelData
container, SubGame carrier when present, both zero-count ownership checks, and
the fully decoded task-condition operands when present. They now also show the
exact authored source object behind each resolvable operand and would show an
exact typed MissionRuntime consumer if a future export introduced one; the
current consumer count is zero. The audit adds no graph edge.
The follow-up task-completion callback audit also closes the possibility that a
serialized receiver task hides a playback action. The serialized task and
condition records have no action or callback member. In the current fallback
bodies, the sole direct registration path for the completion delegate is
`CheckLevelScriptTaskFinished`, whose callback updates MissionSystem objective
progress rather than executing an ActionMap or Story method. The two exact
MissionRuntime instances of that condition target other level/script/task
tuples, so all 31 receiver tasks have zero typed
`CheckLevelScriptTaskFinished` consumers. Schema v7 continues to publish this
zero explicitly. Future progress on these receivers therefore requires a
different producer/owner registry, a changed export/build, or supported runtime evidence;
task-map proximity and completion callbacks are no longer open ownership
routes.
The exact dungeon-scene join is now represented without reopening those
ownership routes. `DungeonTable.sceneId` intersects `18` receiver scripts and
`14` Story keys on `6` scenes, yielding `40` SubGame scene-context placements:
`7` receivers are the exact `bindScriptId` and `33` are sibling scripts in the
same scene. The `31` attached quest, mission-state, or prior-challenge
conditions gate SubGame availability only. Two complementary current-build
examples pin the boundary: `dung01_bdg003/17500000001` plays
`cutscene_e3m5_2` beside the `MissionStateEqual(e3m5)` boss-rush shell but is
not that shell's bound script, while `dung02_bdg002/41100000004` plays
`cutscene_e9m3_2` beside a first-tier boss rush unlocked by `e9m4_q#1`.
Therefore even an exact same-scene mission/quest prerequisite cannot identify
the Story owner, trigger, or order. Schema v7 publishes this context and the
bound-versus-sibling distinction on the existing receiver cards and adds zero
graph edges. It adds the mission-shell field below without changing that
boundary.
The same typed SubGame rows expose a second, stronger boundary:
`DungeonSubGameData.dungeonMissionId` exists for nine receiver scripts carrying
ten Story keys, but every receiver is a sibling of the exact bound script.
`dung_wolfgd_01` names mission `c6m3` while its sibling receivers play
`radio_c6m1_13` / `dlg_c6m1_24`; `dung_aglina_01` names `c13m2d5` while its
four sibling receivers play `c13m2` radios. `dung_kamiu_01` happens to name
`c33m2`, matching its sibling Story family, but the two mismatches prove that
name agreement cannot change the evidence class. The UI now shows all nine as
typed dungeon mission-shell context with `no mission owner`; no coverage or
graph edge is added.
The rest of the typed whitelist surface is also closed on this export:
`missionWhitelist` and `logicIdWhitelist` are empty on all 469 SubGame rows.
Only `f1m18d1_1` has a `proxyWhitelist`; its three proxies expose two dialogs,
both already connected by stronger exact quest-condition or native-playback
evidence, and all three NpcProxyEx mission ids are blank. This adds no owner,
node attachment, or order edge and does not belong in the unlinked queue.
The adjacent DungeonSubGame death-presentation tail does not reopen the black
Story frontier. `conditionalDeathPerformanceEntries` is empty on all 250
Dungeon rows. Sixteen set `useTeamDieBlackscreen`, but the only nonempty hint
is the generic `dungeon_blackscreen_text` localization key; no row carries a
`black_*` Story id or action. These fields add zero black-scene bindings.
The installed hotfix caveat has now been closed for the same lane. The current
Persistent `Gameplay.Beyond.patch.bytes` is 82,021 bytes
(`737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21`)
and parses to EOF as 30 fixed-method targets, including two anonymous-storey
records. It has zero selected receiver-ownership targets, zero selected
LevelScript task registration/completion targets, and zero explicit references
to the task lane. Its two `MissionSystem` replacements are HUD presentation
methods. Seven targets are dialog/cinematic implementation methods, including
`DialogManager._DoPlayCinematicNode`; they change playback implementation but
introduce no exact mission/task/LevelScript owner. The Mission Pipeline runtime
contract now exposes these counts and the patch hash. This is build-scoped:
repeat the structural audit whenever that hash changes.
In debug mode, the Storyline frontend now consumes this same
`storyCoverage.storyTriggerManifest` for every file row and selected-file
detail panel; normal Story browsing does not load or display the trigger
manifest. Exact serialized native event/action paths are displayed as
playback triggers while retaining any unresolved or context-only mission
ownership boundary. Condition, context, dependency, definition-only, and
missing-route rows are never relabeled as playback triggers. OCR and manual
order overrides remain absent from this display path and therefore cannot
promote trigger evidence.
The maintained runtime-observation path now begins where this static boundary
ends. `scripts/story_recovery/import_mission_runtime_trace.py` validates strict
`missionRuntimeTrace.event.v1` JSONL and emits a normalized
`missionRuntimeTrace.v1` bundle. A trigger route becomes exact only when one
capture chain co-records `_RaiseOnScriptEvent`, the entered ActionHeader/
ActionBase node, and the final Story playback key. Mission and quest state rows
carry an explicit active flag and are snapshotted at playback. The Mission
Pipeline can publish this bundle with `--runtime-trace-bundle`; exact quest ids
place observations on the corresponding node, while mission-only rows stay at
mission scope. Both placement types remain observed temporal context, add no
authored graph edge, and are excluded from the source partial order. No real
gameplay capture has been ingested yet, so this path currently improves the
measurement contract rather than the 4,065/1,208 ownership counts.

The current-build protobuf metadata audit now gives the runtime capture a
complete message-ID inventory: 515 client-to-server and 671 server-to-client
enum entries, with all nine previously known IDs revalidated. The generated
inventory and selected field schemas live in
`reports/story/recovery/protocol_registry_audit.{json,md}` and are rebuilt by
`scripts/story_recovery/build_protocol_registry_audit.py`. Its useful new
Story-facing surface is the LevelScript task family:
`CS_SCENE_UPDATE_SCRIPT_TASK_PROGRESS` (105),
`SC_SCENE_LEVEL_SCRIPT_TASK_STATE_UPDATE` (813),
`SC_SCENE_LEVEL_SCRIPT_TASK_PROGRESS_UPDATE` (815),
`SC_SCENE_LEVEL_SCRIPT_TASK_START_FINISH` (816), and
`SC_SCENE_LEVEL_SCRIPT_SET_DONE` (823). The first four expose exact
`(sceneNumId, scriptId, taskId)` identity; the set-done message stops at
`(sceneNumId, scriptId)`. None co-carries `missionId`, `questId`, or a Story
key. Their current-build native paths are now mapped: local
`LevelScriptRuntime.TaskCondition._OnConditionResultChanged` is the sole direct
native caller of `GameplayNetwork.SendLevelScriptUpdateTaskProgress`, which
constructs message 105 and calls `BaseNetworkSystem.SendMsg`; dedicated
`GameplayNetwork` handlers for 813, 815, 816, and 823 route decoded message
objects into `LevelScriptManager`/`LevelScriptRuntime`. The hash-locked runtime
hook records the local condition change, actual send, and four decoded server
handlers. During message 815 application it also hooks
`TaskCondition.InvokeOnIsCompleteChangeAction` and reads the exact condition id
and post-application `isCompleted` byte. That row is emitted only while the
decoded 815 handler remains active on the same thread and only when the
condition object's scene/script/task identity matches the parent message. If a
handler synchronously raises a LevelScript event, its exact task context is
propagated into the existing event/action/Story chain. This is native runtime
evidence and a capture target, not mission ownership or an authored order edge.

The same protocol/native pass has now separated the four similarly named
mission-event schemas. `SC_SCENE_TRIGGER_CLIENT_MISSION_EVENT` (125) is a real
current-build server-to-client path:
`MissionSystem.Handle_ClientMissionEvent` (token `0x060052a6`, RVA
`0x73bdf58`) reads `missionId` at message-object offset `+0x18` and `eventName`
at `+0x20`, then dispatches the exact pair through the mission-scoped
`MissionEvent_OnCustomEventForMission` surface. This still adds no Story edge.
The refreshed 490 MissionRuntime assets serialize zero action headers and zero
custom-mission-event listeners, and the current LevelScript union audit has
zero matching custom-mission-event records. All 538 real
`clientActionMapKey -> actionMapRaw.actionList` mappings resolve to typed
actions and are already handled separately as quest-transition actions.
`SC_MISSION_EVENT_TRIGGER` (126), `CS_MISSION_EVENT_TRIGGER` (316), and
`CS_MISSION_CLIENT_TRIGGER_DONE` (317) are now a proven bidirectional dead-end
in the installed fallback, not merely schema-only. A complete typed-consumer
census over the mission/quest/scene/dialog/SNS/friend/week-raid SC family shows
every live server-to-client message has exactly one typed gameplay handler
(30+ messages, e.g. `SC_MISSION_STATE_UPDATE -> Handle_MissionStateUpdate`,
`SC_QUEST_STATE_UPDATE -> Handle_QuestStateUpdate`, and the sibling
`SC_SCENE_TRIGGER_CLIENT_MISSION_EVENT` (125) -> `Handle_ClientMissionEvent`).
`SC_MISSION_EVENT_TRIGGER` (126) is the only message in that family with zero
consumer: no method takes it as input, only the generated protobuf
ctor/Clone/Equals/MergeFrom exist. Handlers are auto-bound by
`Beyond.Network.NetUtil.AutoRegisterMessageHandlers` ->
`_ForeachMessageHandlers` reflecting over attributed `Handle_*(ScType)` methods,
so with no handler method there is nothing to register for msgId 126: the client
cannot deliver a mission-event trigger from 126 in this build. On the send side,
constructor xrefs show 316 and 317 (and `CS_FAIL_MISSION` 311) are called only by
their own generated protobuf `.ctor` and `<>c.<.cctor>b__NN_0` lambda factory,
while proven-live siblings have a gameplay caller
(`CS_ACCEPT_MISSION` <- `MissionSystem.AcceptMission` `0x1873b7b48`,
`CS_TRACK_MISSION` <- `MissionSystem.TrackMission` `0x1873c33f0`,
`CS_FINISH_DIALOG` <- `CinematicSystem.SendFinishDialog` `0x1872f0d88`); 316/317
have no gameplay sender. So the client neither sends the CS mission-event trigger
nor consumes the SC one; combined with zero serialized
`MissionEvent_OnCustomEventForMission` listeners, the generic mission-event ->
LevelScript/Story bridge is absent on both the protocol and serialized-listener
sides, and this removes 126/316/317 from the unlinked-file frontier rather than
connecting any file. The only live mission-event inbound path stays 125 ->
`Handle_ClientMissionEvent`, which has zero current serialized listeners.
`Handle_ClientMissionEvent` is IFix-gated (checks `IsPatched`/`GetPatch` id
`0x5eca`); the current Persistent IFix payload's 30 targets replace none of these
methods, so the fallback-negative holds for this build and must be re-audited on
an IFix update. Message 317 must not be paired with 125 merely because their
names are adjacent. Reproduce with
`scratch/reverse_engineering/mission_event_native/scan_inbound_handlers.py`
(typed-consumer census) against the July-11 `global-metadata.dat`.

One tempting interpretation from the independent binary pass was rejected.
Native `MissionSystem.Handle_MissionStateUpdate` copies
`SC_MISSION_STATE_UPDATE.succeedId` into local mission completion state and
passes it as the outcome argument to `CompleteMission`; the typed
`CheckMissionSucceedId._targetMissionsucceedId` condition compares the same
outcome selector. It is not a next-mission ID. Likewise,
`curMainMissionId` is synchronized current-main selection/state rather than a
chronological edge. Header-only traffic can recover message-type timing, while
payload-aware capture is needed for mission, quest, scene, script, task, and
event identities. Even a payload observation remains runtime temporal evidence
until an exact native or serialized bridge proves authored ownership.
The non-owning mission-state surface currently contains 25 Story files across
30 placements. Two nominal owners are outside the MissionRuntime pipeline and
therefore remain outside the ownership denominator. One is
`black_map02_lv003liuhan_1`: the original
`map02_lv003/23300090001` LevelScript task map contains exact task
`cf5a771c` / condition `cb696abe`, current `CheckMissionState` union tag
`0x67` with seven members, and predicate `e7m4 Equal Completed`. The same
script contains the exact black-screen playback, but the task condition is not
on its serialized control path. The UI reports this as a same-script,
dependency-only, client-local cache read with no request or expected return;
it adds no Story binding or ownership edge.
The preceding typed system-carrier pass accounts for 25 connected files.
`DomainDepotConst.depotDeliverMissionId=f1m25`, the exact
`DomainDepotDeliverTargetDialogTable[npcProxyId]` rows, and matching
`DomainDepotDeliverTargetTable.targetId` rows connect 24 residual `dlg_f1m25_*`
files to the f1m25 system mission shell. Native receive-package response
handling calls `_AddDialogInDelivering`; finishing the target dialog sends the
send-package request. The graph exposes
`CS/SC_DOMAIN_DEPOT_RECV_PACKAGE_FOR_DELIVER_{REQ,RSP}{deliverInstId}` and
`CS_DOMAIN_DEPOT_SEND_PACKAGE_FOR_DELIVER_REQ{deliverInstId}` with expected
`SC_DOMAIN_DEPOT_SEND_PACKAGE_FOR_DELIVER_RSP{deliverInstId,rewardValue,extraCreditCount}`.
The six f1m33-group dialog rows are intentionally not duplicated as f1m25
cross-owner placements. Separately, the sole `SkipChapterTable` row directly
co-carries `missionId=e5m1`, `bindDlgId=dlg_e5m0d5_1`, activity id, and
`skipChapterConfigId`; native `SendDoSkipChapter` sends
`CS_DO_SKIP_CHAPTER{SkipChapterConfigId}` and expects the matching
`SC_DO_SKIP_CHAPTER`. Both relations stop at mission-shell context because no
quest id is serialized.
`FactoryBuildingPanelLock` adds no ownership coverage. Its exact
`radio_e1m2_3d5` row is retained as two non-owning dependencies at
`e1m1_q#01` and `e1m4_q#5`; native `FactoryUtil.CheckBuildingLock` reads both
quest states and returns the radio id for local presentation. This path sends
no packet, and the radio filename cannot create an e1m2 owner.
Four previously unassigned registered dialogs now carry exact non-owning
DialogTree quest-state dependencies: `dlg_e7m3_13 -> e7m3_q#33`,
`dlg_f1m10_3 -> f1m10_q#4`, `dlg_f1m19d1_14 -> f1m19d1_q#17`, and
`dlg_f1m4d1_9 -> f1m4d1_q#26`. Each accepted row requires an exact sequential
`DialogIdTable` MemoryPack record key, matching typed DialogTree asset/root,
typed `CheckQuestState`, exact `DialogTreeConnection` component, and a path to
or from a same-root numeric trunk. Native `CheckQuestState.OnActivate` and
`_OnQuestStateChange` read the synchronized local quest cache; typed If/Branch
selectors choose an authored outgoing edge. This evaluation sends no request
and expects no response. The dependency surface is now 20 Story files across
25 mission placements; that dependency pass did not itself change the then-current
4,005/1,266 ownership coverage. `dlg_e1m7_5` is rejected because its isolated alternate root
reaches only unregistered `dlg_e1m7_6/_7` trunks.

The current binary-backed DialogTree playback-carrier pass raises ownership
coverage to 4,018 of the same 5,271 files across 4,299 mission placements,
leaving 1,253 unlinked. Thirteen previously unlinked Story files have 66 exact
typed playback occurrences inside six registered DialogTree assets. Trunk
carriers use only
`DialogTreeTrunkNode._actorNodeData.mfTrunkActionData._trunkId`; next-dialog
carriers use only `DialogTreeDialogNode._dialogId`. Every accepted carrier is a
directed ancestor or descendant of a same-root numeric trunk anchor through
fully resolved typed `DialogTreeConnection` edges. Weak-component siblings,
unique-root sibling branches, subtitle LangKeys, finish-state checks, generic
strings, and filename similarity are excluded.

Ten files inherit one exact parent quest: `dlg_a1m3_12`,
`dlg_a1m7_4..10`, and `dlg_c31m2_27/_28`. Three inherit only an unambiguous
mission shell: `dlg_e10m4_14`, `dlg_gm02m14_3`, and `dlg_sm1l1m9_8`.
`dlg_a1m5_5` and `dlg_sm2l2m1_14` remain as three typed but unscoped
occurrences. The first has conflicting `a1m5`/`hidden36` parent missions; the
second has an exact completion listener but no accepted playback owner.
`dlg_sm1l1m1_16` is no longer unscoped: `sm1l1m1_q#6` uniquely tracks local
world entity `70023`, `WorldEntityRegistry` resolves it to global
`2100070023`, and the same-scene counted LevelInteractiveData record carries
component 94's exact `{FX_CHANGE_MISSION_ID=sm1l1m1, TYPE=Dialog(1),
TYPE_ID=dlg_sm1l1m1_17}` map. The mirrored InteractiveTable resolves
`int_narrative_common`, and the typed DialogTree path from parent `dlg_17`
reaches child `dlg_16`. The result is exact quest navigation/configuration
context plus a possible authored child route, not ownership, guaranteed quest
playback, completion, chronology, or server exchange. Authored trunk
ids are marked reachable rather than guaranteed playback because
`FindTrunkIdForReplacement` and `SetOverrideTrunkId` can replace them at
runtime. Both native playback paths are client-local and create no request or
expected response; later dialog/quest completion synchronization is a separate
protocol event.

The two formerly unscoped DialogTree children now have stricter child-specific
context from original data, while ownership remains false. In registered parent
`dlg_a1m5_2`, an exact root `DialogTreeIfNode` has an all-leaf
`CombineCondition` over seven `a1m5` `CheckQuestState(..., Processing)` leaves;
that node dominates every serialized root-to-`dlg_a1m5_5` carrier path, and all
seven quest ids resolve to the same MissionRuntime. The child is therefore an
authored mission-level branch possibility, not one quest's guaranteed playback.
For `sm2l2m1_q#10`, the sole typed `NpcProxyTrackingInfo` occurrence resolves
through same-scene `NpcProxyTable`, one exact `WorldEntityRegistry` brief, a
missionless `NpcProxyEx` row with sole nonempty parent `dlg_sm2l2m1_13`, and the
registered parent's typed `DialogTreeDialogNode._dialogId=dlg_sm2l2m1_14` route.
This adds navigation/configuration context for the parent and possible child
route only. The tracking row's q26 filter controls marker visibility; it does
not activate the dialog. Both evaluations are local and send no request. The
current DialogTree playback queue has zero unresolved files.

A separate weaker DialogTree dependency tier now connects eight formerly
unassigned files. Native `Graph.get_primeNode` returns serialized `allNodes[0]`,
and a fresh `DialogTree.OnGraphStarted` enters that node when no current node is
set. The maintained join accepts only one registered parent asset, a complete
typed directed connection path from that exact first node, an exact authored
`DialogTextTable` trunk id or registered child dialog id, and one unambiguous
parent `CheckTalkOptionFinish` observer. It recovers `dlg_a1m4_2`,
`dlg_a1m7_3`, `dlg_f1m10_8`, `dlg_f1m10d1_5`, `dlg_f1m28_5`,
`dlg_gm01m22_6/_8`, and `dlg_sm1l6m3_16`. These rows are possible authored
playback containment plus quest dependency only: `ownership=false`,
`questPlayback=false`, and no request or reply. Multiple possible parents,
unregistered child dialogs, nonexistent trunk lines, malformed graphs, and
empty parent scopes fail closed.

The current exact FMV pass decodes 36 original LevelScript actions across 30
normalized cutscene keys. Current union tag/member-count pairs prove
`PlayFmvAction` (`0x035e/14`, derived member 9 `_moviePath`) and
`StartFmvAndTeleportAction` (`0x04a1/16`, final member 16 `_fmvId`). Among the
16 previously unassigned filename-compatible Story targets, all serialized
occurrences agree on one exact LevelData mission shell for 14 and are attached
only at that shell. `cutscene_e3m5_1` remains unlinked because none of its five
invocations has an exact mission host; `cutscene_e9m3_2` remains unlinked
because only one of two invocations is hosted. The negative mapping
`cs_video_e1m3_1 -> cutscene_e1m3_1` remains a diagnostic cross-reference and
cannot create a Story edge. FMV presentation is client-local; these action
fields carry no mission/quest id and prove no server exchange.

An independent exact interactive-progress join adds eight Story context rows
under `sm2l5m1`: seven on q1 and one on q8, producing six net-new radio files in
the strict coverage metric because two rows already had other accepted context.
Every accepted Story occurrence is rooted directly at a constant
`EntityEvent_OnInteractiveStateChanged` target or reaches a literal
`RaiseCustomScriptEvent` listener through an exact producer path. The same
entity must have one byte-identical Streaming/Persistent counted
`LevelInteractiveData` record whose complete progress lock is
`SimpleConditionCheckQuestState(Equal, Completed)`, match the exact
`WorldEntityRegistry` type/detail pair, and resolve to one real MissionRuntime
quest; all occurrences for the Story key must agree. The relation means the
completed quest state gates interactive configuration. It does not mean the
quest owns, starts, plays, or completes the Story, and the local entity-event
path has no request or expected server reply.

The typed left-subtitle pass is deliberately separate from black-screen and
dialog playback. In `dlg_e0m2_4`, node 0's exact
`DialogLeftSubtitleActionData` carries `black_e0m2_1_001/_002`; installed
`DialogLeftSubtitleAction.OnPlay` dispatches the local UI event and stops
without a request. The exact parent dialog has one validated e0m2 LevelData
shell, so `black_e0m2_1` now appears on that mission as local presentation.
No quest placement, black/audio playback, chronology, or server exchange is
claimed.

The disposable per-CHK Timeline extraction is no longer a single point of
failure. When its current Actor paths are missing, the maintained pass accepts
the full typed MonoBehaviour export only when an exact Actor-root filename from
the current line-order index selects one source; SourceFile and PathID remain
validated through the playable, track, and every parent hop. The current
fallback recovers 17 containment rows across 13 black Story keys. The current
aggregate coverage is 4,058 connected / 1,215 unlinked, with 61 definition-only
black rows (55 nonempty audio-metadata-only and six explicit empty likely
legacy mappings), zero unresolved DialogTree playback files, and zero unresolved
left-subtitle, narrative-action, or Timeline-containment files.
The latest original-data-only receiver expansion adds six Story connections
through the same typed WorldEntity foreign-key bridge. `e2m5_q#15` connects
`radio_e2m5_19` through its complete five-enemy set and exact
`OnScriptStageChanged(1)` path. `e3m3_q#13` connects `radio_e3m3_7` through its
two-enemy set and exact entity-interactive-state path. `sm2l4m2_q#4d5` connects
`radio_sm2l4m2_3` plus level-owned Story cutscenes
`cutscene_map02_lv004_lingyuan_1/2/3` through its exact six-interactive set and
stage filters 1/2/3. The stage route exposes one-way
`SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE {sceneNumId, scriptId, stage}` and expects
no reply, but the packet contains no mission/quest id and does not prove that
the quest condition caused the stage change. The first cutscene also has an
exact same-script preload under `OnScriptActive`; that auxiliary action is
reported separately and never treated as playback or as an accepted receiver.
The preceding pass added three Leader-trigger context bindings.
`e3m2_q#3`'s complete
`CheckMonsterKilled` entity set is exactly the `refWorldEntityIdList` of
LevelScript `2800010045`, whose validated Leader-enter path plays
`radio_e3m2_7`. `gm02m11_q#4`'s three direct `InteractiveCheckInt` entities are
a unique subset of LevelScript `22800330000`'s five referenced WorldEntities;
the exact Leader-enter control path reaches `black_gm02m11_1` and
`cutscene_gm02m11_Activate`. Every entity is unique to one canonical
MissionRuntime quest and every same-level LevelData occurrence agrees on the
same script. These are shared authored WorldEntity contexts, not proof that the
quest or a server response activates the trigger.
The preceding original-data-only attachment pass added six context bindings. Five
`radio_c27m4_*` files resolve from `c27m4d5_q#14`'s nested typed
`EntityTrackingInfo` through local script `8`, registry script `26900000008`,
and exact serialized playback paths. `dlg_c33m1_17` resolves from
`c33m1_q#10` through the same nested tracking container, unique global script
`2100600007`, registry slot `40001`, `int_narrative_empty`, and the exact
serialized interactive `type_id` property. These are navigation/configuration
context only: they do not claim quest playback, ordering, completion, or a
server exchange.
The latest binary-first pass adds eleven connected Story files through a
separate weak shell route. Nine direct normalized outputs require an exact
typed MissionRuntime `NpcProxyTrackingInfo`, same-scene `NpcProxyEx` mission
owner, and `WorldEntityRegistry.NpcProxyBriefInfo` whose dictionary key and
positive `segmentIdGlobal` both equal the Story-playing LevelScript global id.
Every raw/native occurrence that normalizes to the output must resolve, and all
occurrences and nonempty proxy owners must agree on one mission. The direct
rows are `dlg_a1m8d1_4`, `dlg_a1m8d2_1`, `dlg_a1m8d3_2`,
`radio_a1m6d1_1`, `black_a1m8d3_2`, and four normalized `misc_dlg_*` outputs
for c17m2/e1m9/e5m3/sm1l1m4. Exact parent containment then scopes
`black_a1m8d1_2` and `black_a1m8d3_1`. The original row places the
d3-looking `dlg_a1m8d3_2` under `a1m8d2`; the filename does not override it.
This relation is only `derived_exact_shell`: native NPC navigation reads proxy
position and no recovered consumer uses `segmentIdGlobal` to start a script.
It proves neither quest/NPC activation nor a server exchange. An initial
four-key audit undercounted because its raw unresolved-key surface omitted
native-black and `dlg -> misc_dlg` normalization; the nine-key census closes
that input gap without loosening the binary rule.
An original-data SubGame registry now adds 20 exact mission-to-bound-LevelScript
runtime-shell rows to the Mission Pipeline, but deliberately adds zero Story
connections: all 20 scripts are parent-zero LevelData roots with no validated
descendants, and none intersects the 182 unresolved native-playback files.
Same-level siblings remain unowned. This keeps the registry useful for the
binary model without inflating the coverage metric.
Two additional original-data enrichments follow the same boundary. The typed
`ActivityDungeonFightingStageTable` and `ActivitySnapShotStageTable` contribute
25 exact `questId -> levelId` rows across 24 quests and four missions; they add
level hosts to quest blocks but zero Story bindings. Separately,
`LevelEvent_OnQuestStateChanged` reaches native `StartDialogAction`
(`0x049e/0x0f`) for
`dlg_a1m4_OpenUI` on Processing/start and `dlg_a1m13_OpenUI` on
Completed/succeed. Their original TextAssets are typed
action-only DialogTrees containing `DialogOpenUIAction` (panels 22 and 21), not
conversations. They are retained as `quest_to_runtime_action` Open UI terminals
with activity parameters and must never be normalized to `misc_dlg_*` or
counted as Story files.
The corrected installed-byte census has 200 typed
`LevelEvent_OnQuestStateChanged` receivers: 191 constant quest filters, 173
unique action targets plus 27 ambiguous targets, and 21 direct chains yielding
29 raw dialog/radio operands. Twenty-seven resolve to exported Story files and
the two rows above resolve only to typed Open UI actions. The parallel
`OnMissionStateChanged` family has 34 receivers and zero direct Story chains;
no generic mission/quest-to-LevelScript activation registry was recovered.
A bounded native audit confirms that this is a real client boundary rather than
a missing direct call. Eleven decoded MissionSystem/MissionRuntime bodies have
zero resolved LevelScript calls, seventeen LevelScript/network bodies have zero
reverse MissionRuntime calls, and the broader two-layer direct-call ancestor
scan also finds no shared bridge. The 546 current MissionRuntime client actions
contain no LevelScript operand; `ManualStartLevelScript` resolves a script and
starts it without carrying mission/quest identity. Protocol schemas remain
split as well: LevelScript packets carry scene/script identity without a
mission, while mission-event packets carry mission/event identity without a
script address. Virtual, delegate, and IFix dispatch remain outside that
negative, so the result rejects a generic edge but does not claim an impossible
server-side relationship.
The whole-metadata mission/script co-carrier census closes one especially
plausible current-client candidate. Only 20 of 63,987 types nominally declare
both identity families, and most are enum/static-constant false positives. The
sole new actionable runtime carrier is the 0x38-byte
`Beyond.Gameplay.TeleportParam`, with `missionId` at `+0x18`,
`levelScriptId` at `+0x20`, `actionId` at `+0x28`, and `performId` at `+0x30`.
Its current direct producers either zero the whole carrier or set only
source/UI/options/reset/callback fields; the server pass-through decoder also
leaves mission, script, action, and performer identity zero. The loading
consumer uses source/script/action for the local teleport-finish LevelScript
event, the callback lane uses callback identity, and presentation uses
`performId`; no audited consumer reads `missionId`. The current 30-target
Gameplay IFix payload replaces none of these methods. `TeleportParam` therefore
adds zero Mission Pipeline bindings and should not be treated as a hidden
mission-to-script bridge. This is bounded to the current direct AOT/fallback
paths and installed IFix payload; future patches and unresolved
indirect/reflection/XLua construction still require fail-closed re-audit.
The current installed Lua chunk independently closes another candidate surface:
zero of the 182 residual native-playback Story ids and zero of their 106
listener/target LevelScript ids occur in its 1,290 valid modules. Only
`cutscene_e1m10_1` and `cutscene_e0m0_1` occurred among the then-current 1,303
unlinked Story
ids, each as an exact character-system phase playback call with no mission,
quest, or script owner. They remain system consumers rather than Mission
Pipeline bindings.
The first positive typed LevelData state/playback co-carrier is now decoded
separately. `FunctionAreaSpecificData` union tag `9` is the seven-member
`RadioTriggerZoneData`; its exact single-item list rows co-carry `radioId` with
`hideBeforeMissionId`, `hideAfterMissionId`, and
`hideCompleteMissionId`. The current data has four valid Story rows and six
mission placements: `radio_e1m3_13`, `radio_gm01m10_1`,
`radio_gm01m16_1`, and `radio_gm01m23_1`. Native
`RadioTriggerZoneHandler.OnEnter` calls `_GetRadioTriggerMissionState`, which
reads those mission fields through `MissionSystem.GetMissionState`, before it
reaches `GameAction.PlayRadio`. This is exact mission-state-gated playback
context, not quest ownership. The handler reads the synchronized local mission
cache and sends no request; `SC_SYNC_ALL_MISSION` and
`SC_MISSION_STATE_UPDATE` remain independent upstream pushes rather than
replies to entering the zone.
An exact `ReadingPopUp`/narrative carrier adds two more dependency bindings.
The `dung01_rdg003_lv_data_sub_c16m4` LevelData member-20 interactive list has
17 counted `LevelInteractiveData` records. Two individually bounded 25-member
records contain a complete two-entry ParamValue map with canonical native
`Beyond.PropertyKeys.FX_CHANGE_MISSION_ID` (`0x04000b50`) equal to `c16m4d5`
and `TYPE_ID` (`0x04000941`) equal to `rp_radio_c16m4_50` or `_51`.
`ReadingPopUpTable.contentId` resolves those ids to `radio_c16m4_50` and `_51`;
the byte-identical InteractiveTable mirrors resolve both entity detail ids to
`int_narrative_common`, whose exact BaseComponentData tag `0x00b3` registers as
`Core_NarrativeComponentData`. Native NarrativeComponent paths read mission
state and start radio/dialog playback. This proves same-entity mission-state
FX/playback dependency only, not Story ownership, quest causality, or
chronology. `ClientCollectNarrative` is local; `_CollectNarrative` may call a
separate `_RequestInteract`, but no exact protocol message/reply is attributed
to the mission-state edge.
Leader-trigger geometry context now consumes only the typed current-build
`eventDetail.triggerSlotIdFilter`. The older aggregate `triggerSlotIds` scan can
include adjacent dictionary values in six current receivers and is no longer
accepted by the geometry matchers.
Black-screen coverage is 127 of 192, leaving 65 unlinked: five have an exact
native trigger but unresolved ownership, two have no recovered trigger route,
and 58 are original TextTable definitions with no
current-build playback consumer recovered. The definition-only negative audit
splits those 58 into 52 nonempty `TextVoIdTable` audio-metadata rows with no
playback consumer and six explicit empty audio mappings that are likely legacy;
none creates a Story edge. No black file is now wholly unlinked solely because
of DialogTree containment. `black_sm1l1m1_1` is connected through one exact
parent but still has another unscoped parent use, so partial coverage remains
reported explicitly.

The maintained source-only audits are:

```bat
python scripts\story_recovery\build_source_story_partial_order.py --language CN
python scripts\story_recovery\build_source_story_order_cross_reference.py --language CN
python scripts\story_recovery\build_source_story_gap_queue.py --language CN
```

They write:

- `reports/mission_order/source_story_partial_order_CN.{json,md}`
- `reports/mission_order/source_story_order_cross_reference_CN.{json,md}`
- `reports/mission_order/source_story_gap_queue_CN.{json,md}`

The gap queue now checks the current-build binary playback index directly
instead of relying only on native rows copied into each mission bundle. A
weaker pre-existing quest-context row can legitimately suppress the redundant
`unlinkedNativePlayback` row, but that data-shaping choice must not turn an
already decoded ActionBase record into an alleged parser gap. Requiring exact
source file, action-list membership, playback class, Story identity, and
GameAssembly mapping reduces the current multi-scene LevelScript parser queue
from 120 contexts to 24. A second exhaustive current-build classification now
closes all 24 remaining contexts as binary-negative rather than actionable
playback decoder gaps. Seven use exact `PreloadCutsceneAction`; the recurring
dialog records are exact `PreloadDialogAction` (`0x0377`),
`OverrideNPCDialog` (`0x0344`), or `RemoveNPCDialog` (`0x0389`); the remaining
radio record is exact `StopRadio` (`0x04b5`); and the other Story strings are
outside the physical `ActionSerializedMap.actionList`. The report preserves
all 24 under `closedNonPlaybackLevelscriptContexts` with per-key action
evidence, while `untypedMultiSceneLevelscriptContexts` is now zero. This
changes prioritization only and creates or removes no scene edge or mission
ownership.

The gap queue also no longer treats every weak-only or isolated row as a
missing LevelScript decoder. The current source graph has 2,063 weak-only
placements: 1,807 have a complete exact native event-to-playback path but no
prefix-comparable second Story action, and 256 retain only non-ordering
topology. The actionable weak-only LevelScript control-flow queue is now zero
in every mission bucket. Two former false positives,
`radio_e6m4_18` and `radio_sm1l1m1_5`, were already exact current-build
`StopRadio` records (`0x04b5/0x09`); the weak-only fallback now applies the
same non-playback formatter map as the multi-scene classifier instead of
relabeling those records as missing decoders. Exact-native singleton,
non-playback, and divergent-event routes stay visible but contribute no
recovery score. Independently, `radio_e6m4_18` has a real playback occurrence
in script `22800110022`: Leader slot `80001 -> Split.actions[0] ->
PlayRadio`. Its mission-tracked world-entity connection already retained that
listener under `worldEntityLevelScriptEvidence`, but the Mission Pipeline
trigger-manifest normalizer did not unwrap the nested field. It now does so
for all 30 published routes in that connection family, restoring exact native
event/action paths to the WebUI without turning shared navigation context into
quest activation, ownership, or relative Story order. Isolated rows are
similarly separated: 223 core placements already have exact native playback
paths, 84 have exact mission-scoped `NpcProxyEx` runtime configuration but no
relative order, and 80 current mission-audit `black_*` definition-only
placements are closed after the complete LevelScript/DialogTree/Timeline
consumer search. The proxy class is accepted only when the generated row
retains the current installed `GameAssembly.dll` mapping and proves
`exDatas[activeCondIndex - 1].dialogId`; it establishes selectable dialog
ownership, not mission activation, quest placement, or cross-row chronology.
These placement counts are a different scope from the global unassigned-black
denominator below. None of the three classes can be ordered by trigger-slot
number, proxy suffix, table/file position, OCR, or manual lists.

The final five main-story weak-only decoder rows are now closed without adding
scene order. The installed ActionBase formatter table maps union tag `0x0501`
to `WhileAction`; its generated MemoryPack setters serialize `_condition`
before `_doID`. Current LevelScript records use the corresponding exact
18-byte shape: one `Param<bool>` followed by the signed local action id.
Following the recovered `WhileAction.doAction` edge restores four event paths:

- e7m2 script `22800180009` Leader slots `80001` and `80002` reach
  `radio_e7m2_15` and `radio_e7m2_3` through separate
  `WhileAction -> WaitForSeconds -> IsLookAtPointInScreen -> IfElse -> Split`
  chains;
- e6m1 script `22800080005` Leader slot `80003` reaches
  `radio_e6m1_10` through locals `25 -> 26 -> 27 -> 28 -> 29 -> 34`;
- e8m1 script `23400010019` Leader slot `80001` reaches
  `radio_e8m1_19` directly through `WhileAction` local `3` to
  `Play3DRadio` local `4`.

The same decoder closes `radio_c31m3_17` and `_18` outside the main-story
bucket. Separately, `radio_e1m2_10d5` was already reached by exact Leader-slot
and script-stage-2 paths, but both traverse duplicate serialized `Split` local
`36` records. The control-path builder accepts duplicates only when every
record has the same typed tag/member count, texts, `nextId`, and decoded branch
targets; conflicting duplicates fail closed. The gap classifier now accepts
that explicitly retained
`exact_serialized_control_path_equivalent_duplicates` status as exact evidence
instead of reporting a decoder gap.

These recoveries are local playback reachability, not a playlist. The two e7m2
radios have different trigger events; the e1m2 row has alternative event paths;
and none of the recovered singleton paths contains a second prefix-comparable
Story action. Trigger-slot numbers, equivalent-record offsets, and action-list
position therefore still supply no relative Story order. More generally, any
path containing `WhileAction.doAction` is excluded from strict prefix-order
promotion because the loop body can repeat; it remains exact trigger
reachability evidence only.

The last four weak-only decoder rows close through two additional exact
ActionBase layouts. The installed formatter and generated setter metadata map
tag `0x04f9`/member count `0x0e` to
`WaitForSecondsInTriggerVolume`. Its inherited field sequence is null
`_areaEntity`, `_failID`, `_seconds`, `_successID`, followed by current-script
`_scriptPtr` and `_triggerSlotId`. In
`map01_lv003/300010007`, the three records select trigger slot `80001` and
serialize success ids `32`, `26`, and `20`, which are respectively
`radio_sm1l3m2_8`, `_10`, and `_12`. Their exact paths begin at the local
`WaitArea` custom-event header, choose phase `0`, `1`, or `2` through
`SwitchInt`, and follow the wait action's success edge to playback. The phase
2 route also traverses `WhileAction`, so its playback is exact but its loop
body remains excluded from strict prefix order.

Tag `0x04bf`/member count `0x0c` is `SwitchString`; its exact fields are
`_caseIDList`, `_caseValueList`, `_defaultID`, and `_value`. In
`dung02_rdg007/35400010010`, the
`ScriptEvent_OnStartScriptControlledCharMode` header reaches local `141`,
whose `chr_9000_endmin` case selects `ScriptedCharPatrolStart` local `131`;
that action continues to `Split` local `132` and
`radio_c31m3_16` at local `133`. Both new decoders require the complete
current-build payload through exact EOF, accept only bounded local ids, and
the wait outcome is traversable only when its receiver decodes as the current
script. The generated gap audit now classifies character weak-only rows as
377 exact plus 41 non-ordering, and other rows as 623 exact plus 115
non-ordering, with zero actionable rows in both.

The former `e6m3` top parser gap is one of those exact negatives.
`map02_lv002/22800100007` plays `radio_e6m3_14` from a Leader-enter listener
for trigger slot `80001`. `dlg_e6m3_13` occurs only in the separate slot
`80002` interactive configuration (`type_id`, `dlg_finish_id`) and a
non-action serialized map record; it has no ActionBase playback record and no
activation/control bridge to the radio.

For example, the former `e11m4` parser gap in
`map02_lv008/23100090002` is fully typed in the original data:
`dlg_e11m4_2` is a `StartDialogAction` under independent leader-enter trigger
slot `80001`, while `radio_e11m4_12` is `PlayRadioAndWait` under slot `80002`.
The two handlers have separate serialized roots and no decoded activation or
control edge between them, so their shared file and quest-property context
still do not prove either order.

The source partial-order and gap-queue audits do not read or write
`webui/overrides/story_order.json` or `webui/data/story_order_ocr.json`. The
cross-reference audit reads both after the strict graph is complete and never
writes them or feeds them back into recovery.

## Evidence policy

### Accepted ordering evidence

- `MissionRuntimeAsset` `questPrev` relations backed by
  `QuestInfo.prevQuestIdList`, except reciprocal projections between reusable
  Story file nodes.
- Direct quest-local Story references such as `_dialogId`, `snsDialogId`,
  `_cutsceneId`, `_remoteCommId`, and `_radioId` establish attachment; they
  order scenes only when another accepted directed relation connects them.
- DialogTree `authoredDirect` connections.
- Exact native event-to-action local-id path prefixes. Under one serialized
  event header, the target of a shorter path precedes a later Story target only
  when its entire path is a strict prefix of the later path. Equal/divergent
  paths and reverse-conflicting evidence remain unordered.
- Exact native branch topology. Divergence through `Split.actions[n]` is a
  source-proven fan-out, while `IfElseAction.true/falseAction` and
  `SwitchInt.case[n]` are conditional arms. These relations preserve sibling
  alternatives without creating an order edge. A convergence is retained only
  when every observed arm route contains the same downstream local ID.
- LevelScript `LevelEvent_OnDialogExit` action chains that pass the strict
  ambiguity controls described below.
- Direct DialogTree/DialogTreeFragment option-to-line paths.
- Runtime Jump option routes only when the generated provenance is exactly
  `timelineRouteBranches` / `runtimeJumpTrack` / `dialogTimeline`.
- Timeline clip option routes when authored option rows have distinct positive
  `optionIndex` values, every branch trunk clip has the matching index, and
  every in-window Runtime Jump occurs after that option's final response clip
  and converges forward to the shared continuation.
- Timeline clip order for lines within one decoded dialog or cutscene asset.

### Retained but non-ordering evidence

- Generated `questSequence` relations assembled from heterogeneous quest-local
  Story reference collections.
- `questFailGuard` failed-condition topology.
- DialogTree `authoredMenu` menu/submenu reachability.
- Generic LevelScript `levelscriptSceneChain` relations. These preserve
  `nextId`-connected Story references, including preload/remove/override/stop
  actions, but do not assert that each referenced file played.
- reciprocal file-level `questPrev` projections from distinct directed quest
  instances.
- LevelScript byte/file order and cross-file numeric proximity.
- Untyped LevelScript membership and Story-call contexts that do not establish
  direction. Hash-shaped payloads require typed opcode/UID classification:
  current `CallServer` values equal `#` plus the owning action-record UID and
  are callback/correlation diagnostics, not Story nodes.
- LevelData quest references, PRTS collection order, trigger/spatial
  proximity, audio tags, and shared Timeline membership.
- `radioContinuation` while its file-adjacency component remains unresolved by
  the strict evidence policy.
- Narrative-video filename candidates without Timeline/source bindings.

### Explicitly rejected as original-data order

- `webui/overrides/story_order.json` and `webui/overrides/options.json`;
- gameplay video, OCR proposals, and the observed `e0m0` calibration;
- `sceneOrderInfo.questOrder`, `flowIndex`, SceneGraph node `order`, and UI
  rank;
- numeric scene suffix, filesystem order, VFS order, or table row order;
- inferred-following-line, default/shared continuation, risk-tagged, or manual
  option mappings.

Strong-edge cycles are preserved as cyclic components. They are never broken
with a filename or display-order tie-breaker.

## Where Story evidence comes from

High-signal structured sources include:

- `MissionRuntimeAsset/<mission>.json` for quest DAGs, conditions, actions,
  tracking, and Story references;
- `LevelScriptData/<level>/<script>.json` for action maps, event headers,
  gates, terminals, play actions, and local `nextId` chains;
- `LevelData` for script host context, parent/control grouping, properties, and
  `lt:p` / `lt:mp` marker references. Mission Pipeline host context requires a
  complete native member-22 `LevelScriptBriefData` dictionary entry, not a raw
  numeric occurrence;
- `DialogTextTable`, `DialogOptionTable`, `DialogSummaryTable`, `RadioTable`,
  SNS tables, `EnvTalkTable`, responsive dialog, reading/PRTS tables, and
  i18n tables for content and identity;
- recovered AnimeStudio DialogTree and Timeline objects for authored line
  order, option paths, Runtime Jump clips, subtitles, and FMV bindings;
- `global-metadata.dat` and `GameAssembly.dll` for runtime vocabulary, union
  tags, serialized field meaning, and focused method/control-flow evidence.

IL2CPP metadata is not an authored playlist. It explains how serialized data
is interpreted; the concrete order still has to come from authored quest,
event, action, tree, or Timeline relations.

The current LevelScript symbol hygiene pass keeps that diagnostic topology
without presenting action-local parameters as events. Across generated CN
mission graphs, 208 remaining generic-symbol edges touch a recognized Story
node. Six same-record one-character values have been removed from graph
identity: `P`, `Y`, `e`, and `A` occur beside the real cutscene id only in exact
typed
`StartCutsceneAndControlSceneObjectAction`/`StartCutsceneAndHideSceneObjectAction`
records, while `#` and `%` occur beside real dialog ids in two exact typed
`PlayDialogAndHideSceneObjectAction` records. All six are retained under
`levelscriptNonNodeScalarPayloads` with explicit
non-Story/non-owner/non-order flags and are excluded from graph nodes and
edges. Every one of the 208 retained boundaries is now typed by physical
`ActionSerializedMap` membership: 200 carry formatter-derived
`sourceActions`, while eight header-list boundaries carry formatter-derived
`sourceEvents`; none is unlabeled and none is labeled from an overlapping
union tag alone. The largest action context families are `PlayRadio`,
`PlayRadioAndWait`, `StartDialogAction`, `RaiseCustomScriptEvent`,
`AddCameraControlState`, and `StartDialogAndTeleportAction`; the header
contexts comprise custom-event, dialog-exit, teleport-finish, and saved-property
events. The WebUI debug graph and native-route display surface these names, but
the edges remain `levelscriptChain` context and never become chronology or
mission ownership merely because their classes are now known. The localized
builder copies the same diagnostic fields onto exact matching
`timelineRecovery.sourceBackedSceneEdges` rows because that parallel edge view
feeds the Story panel; the join requires identical source, target, and edge
kind.

## Quest, mission, and scene model

Quest Tree nodes are `MissionRuntimeAsset.questDic` quest ids. The durable join
is:

```text
MissionRuntimeAsset quest
  -> direct Story ref, runtime action/condition, NPC proxy, or scoped script condition
  -> timelineRecovery.scenePlacement[storyKey]
  -> webui/data/lang/CN/conv/<storyKey>.json
  -> exported structured or AnimeStudio source
```

The strongest direct examples remain:

- `e7m4_q#13` owns `cutscene_e7m4_1` through
  `condition._cutsceneId.constValue`.
- `a1m6d5_q#11` reaches `radio_a1m6d5_1` through a MissionRuntime `PlayRadio`
  action.
- Quest-local Story references, scoped `CheckLevelScriptProperty*` ownership,
  variant MissionRuntime attachments, and NPC-proxy dialog attachments can
  place a scene on a quest.

Quest-to-Story attachment now preserves runtime direction instead of exposing
one undifferentiated file list:

- objective and failure-condition references are `Story -> Quest`, because the
  quest condition waits for dialog, cutscene, radio, or related Story state;
  in particular, `CheckTalkOptionFinish._dialogId` proves a completion listener,
  not that the quest starts that dialog;
- client action references are `Quest -> Story`. In the current native binary,
  `QuestAction` flag slots `1`, `2`, and `4` are
  `OnStartClientAction`, `OnSucceedClientAction`, and
  `OnFailedClientAction`; `SucceedQuest` passes slot `2` and `FailQuest` passes
  slot `4` through `SafeRunQuestAction`;
- LevelData quest references, scoped LevelScript-condition ownership, variant
  MissionRuntime recovery, authored one-hop Story routes, and exact
  `NpcProxyEx.missionId` plus unique tracked-proxy resolution are contextual
  attachments. They establish quest ownership but not a playback direction;
- typed `EntityTrackingInfo` can establish exact navigation/configuration
  context through either its script entity or one uniquely resolved non-script
  `WorldEntityRegistry` entity. It does not turn every Story action or entity
  event in that level into a quest action. Actual quest playback still requires
  a direct client Story action or a proved quest-state handler-to-playback chain;
- spatial proximity is diagnostic only and is never promoted to a Story
  attachment.

Mission Pipeline schema 14 also preserves one exact authored cross-condition
context without changing those direction rules. `sm2l7m1_q#17` requires both
`submit_item_sm2l7m1` and stage-max for LevelScript
`map02_lv008/23100170008` in the same AND objective. The script's exact
dialog-exit path already supplies the strong source edge
`dlg_sm2l7m1_17 -> dlg_sm2l7m1_9`; a separate Leader-enter path also plays
`dlg_sm2l7m1_9`. The installed ActionBase formatter further resolves the
legacy-looking `0x09b9/0x00` records in all three chains as compact tag
`0x00b9`, nine members, `ExitLevelCustomPerformance`. The exit-only
dialog path is that cleanup action, while each `dlg_sm2l7m1_9` chain reaches
the same action through an identical, now fully typed sequence:
`StartDialogAndTeleportAction -> ToggleClearScreenButRadio(false) ->
MainCharMoveTo(walk_end_pos, gait 0) ->
ToggleClearScreenButRadio(true) -> ExitLevelCustomPerformance -> CallServer`.
The terminal compact tag `0x0034`/14 members has the generated
`CallServer` fields: null client-output UIDs, `event_args`, an event name,
`useCustomEvent=false`, `waitForCallback=true`, and `withEventArgs=false`.
The event names close exactly as `#` plus their own eight-hex-digit
CallServer record UIDs (`#5bd318ba`/UID `5bd318ba` and
`#2f436d36`/UID `2f436d36`). The complete current typed corpus follows the
same identity rule, so these are action-local callback/correlation labels,
not server-handler hashes, Story nodes, mission owners, or order evidence.
Story and Mission Pipeline generation now removes them from graph nodes/edges
while retaining explicit `levelscriptCallServerSelfUidCallback` diagnostics;
the generated corpus audit lives in
`reports/story/build/mission_timeline_recovery_CN.json`. The target script's
three exit-action payloads contain
only an unbound zero
`Param<uint>` handle; the movement action has only the authored
`walk_end_pos` parameter. No step contains a mission, submission, item, UI,
branch, or additional Story key; the server handoff likewise serializes no
mission/quest identity. This proves objective co-gating and local
playback/presentation-cleanup context, not that the quest or script opens the
submission UI and not that submission completion triggers either dialog.

A follow-up full generated-graph scan closed the two remaining punctuation-only
nodes. `map02_lv005/23200050003`, record UID `15196cb4`, serializes `#` beside
its real `dlg_sm2l5m1_7` id; sibling script `23200050004`, record UID
`4b93dcf6`, serializes `%` beside `dlg_sm2l5m1_8`. Both are exact
`PlayDialogAndHideSceneObjectAction` (`0x035a/0x0f`) action-list members. With
no identifier body, neither value is a runtime/Story key. The builder retains
their raw bindings plus `levelscriptNonNodeScalarPayload` diagnostics, but
excludes both from graph nodes and edges. The recognizer requires physical
action-list membership, the exact typed opcode, a single ASCII punctuation
character, and a co-record dialog id; it must not be widened to suppress other
symbol payloads without equivalent typed evidence.

Mission-level Story evidence stays separate from quest attachments.
`MissionRuntimeAsset/<mission>_meta.json` NPC accept mode (`mode = 3`, native
`MissionAcceptMode+NPCInfo`) attaches its exact `dialogId` to the mission accept
boundary. An explicit `NpcProxyEx.missionId` attaches its dialog to the mission
shell even when no quest uniquely tracks that proxy. Blank `missionId` rows are
default/unscoped data and are not promoted to a causal quest connection.

The installed LevelScript formatter mapping also identifies opcode
`0x1385/0x00` as `LevelEvent_OnQuestStateChanged`. Completed-state (`3`)
handlers become `Quest -> Story` success actions only when the record is an
exact `headerList` member, contains one filtered quest id, resolves one action
root, follows an unambiguous terminating `_nextID` chain, and contains exact
tagged Story ids. This remains installed-build native evidence and is not
generalized across unknown opcode versions.
The source partial-order audit now preserves the exact source file,
`actionPathLocalIds`, and per-Story `actionPathIndex` for those typed handlers.
It promotes only consecutive typed playback positions on one identical
quest-state path. Current CN data yields eight
`levelscriptQuestStateActionPath` edges across `e11m1`, `f1m9d4`, `gm01m4`,
and `sm1l2m3`; OCR leaves all eight uncovered, while the manual list agrees
with four and leaves four uncovered. Those comparison results do not affect
the edges.

Additional mission-shell connections now come only from exact original-data
joins:

- 1,816 evidence rows attach typed Story playback to mission-named LevelData
  asset shells through the exact native 43-member container and fully parsed
  eight-member `LevelScriptBriefData` value. Final `scriptId` must equal the
  dictionary key, entries must form one contiguous chain, and the preceding
  count must match. This is asset context, not logical mission/quest ownership;
  explicit MissionRuntime conditions may point to a script hosted by a
  different shell;
- 89 evidence rows use typed `MissionAreaTrackingInfo.missionAreaId` -> exact
  `MissionAreaTable.subDataParentId` -> identical validated LevelData
  member-22 root. These add 24 previously unassigned files across `sm2l3m1`,
  `sm2l3m4`, `e0m0`, and `c27m5`. Every root/file hit must agree on one
  MissionRuntime; the c13 root remains rejected as shared by `c13m2` and
  `c13m2d5`, and filenames do not choose the owner;
- 295 evidence rows attach exact LevelScript Story occurrences as
  context when the action payload contains the exact Story id and the
  containing script is independently and uniquely scoped to the MissionRuntime
  by its mission/quest id or a typed mission condition;
- 176 evidence rows use typed `EntityTrackingInfo` plus current native entity
  identity. Twenty-five
  rows decode the exact tracked entity's serialized
  `interactives[slot].properties[type_id]` after its registry object resolves
  through the complete native `InteractiveTable` to template
  `int_narrative_mission`; 149 rows retain a typed Story action reached by an
  exact event/control path in that same script. The former is a configured navigation target and the
  latter is same-script context; neither claims quest playback, chronology, a
  completion callback, or a server exchange. When the event slot and tracked
  slot differ, both values remain visible rather than being bridged. One
  additional row has an exact bridge: `e0m0_q#2` tracks travel-pole slot 40010,
  `LevelEvent_OnTravelPoleBegin` feeds an `IfElseAction` whose `EntityCompare`
  condition reads that same `ScriptEntityPtr`, the true branch raises
  `PLAY_SEQ_1`, and the unique same-level custom-event listener plays
  `cutscene_e0m0_1stZipline`. This proves local playback context only; the
  `GameConditionServerPlaceHolder` server rule and its relation to that local
  playback remain opaque even though the synchronized objective packet is now
  decoded;
- one non-script tracking row, `e8m1_q#12`, resolves local entity logic id
  `83108` through the current `WorldEntityRegistry` to the sole global id
  `23400083108`. An exact `EntityEvent_OnSavePropertyChanged("state")` target
  in `map02_lv004/23400083014` reaches `radio_e8m1_12` through its serialized
  control path. This is exact tracked-entity/property context, not proof that
  the property change completes the server-placeholder objective;
- the full current MissionRuntime corpus contains 1,933 direct
  `GameConditionServerPlaceHolder` objectives across 1,931 quests and 377
  missions. Native `StartQuest` binds client progress callbacks only for
  `ConditionType.ClientOnly=9999`, while the installed placeholder fallback
  returns `int.MaxValue`; therefore the placeholder sends no
  `CS_UPDATE_QUEST_OBJECTIVE`. Its server update is
  `SC_QUEST_OBJECTIVES_UPDATE` keyed by `(questId, conditionId)`. The packet has
  no scene/script/entity/trigger/spawner/Story identity, and condition ids are
  not globally unique. The current Persistent IFix payload has 30 targets
  and replaces none of the placeholder condition-type/activation methods, so
  this fallback is effective in the installed build. Exhaustive exact joins
  over all 193 residual native
  Story keys promoted zero rows; the 139 placeholder rows with authored Story
  references were already connected through those explicit actions;
- 72 rows join an exact level-scoped MissionArea shape to an EOF-bounded
  current-build Leader trigger-volume entry selected by the same typed
  `ScriptEvent_OnLeaderEnterTriggerVolume` slot. They expose exact geometry and
  local client context, not a quest-completion or server-response edge;
- 17 rows scope playback scripts through the complete validated LevelData
  member-22 sibling shell when every original-data anchor in that container
  agrees on one mission. Fourteen of those Story files were previously
  unlinked. The relation remains mission-shell asset context rather than a
  quest trigger;
- six Story paths in `gm02m4` are reached from exact
  `MissionEvent_OnClientGlobalVarChanged` headers carrying the same literal key
  consumed by that one MissionRuntime. Because both q8 and q11 consume the key,
  the graph stops at the mission shell instead of selecting a quest;
- 41 rows join a typed `WaitForNpcProxyReady` step on the exact event-to-Story
  path to an MRA-tracked proxy when all proxy consumers agree on one mission.
  Multiple candidate quests remain visible and no request/response payload is
  inferred;
- 13 FocusMode rows cover 10 Story keys through an authored mission id plus
  `radioIdInteractLocked` pair;
- 44 SNS content rows carry agreeing root `relatedMissionId`, type-12
  `linkMissionId`, and `contentParam` fields; six of those rows newly connect
  previously unassigned SNS files;
- 16 black-screen Story roots resolve through 21 exact serialized playable ->
  Timeline track -> parent PPtr -> Actor root chains. The parent dialog comes
  from the sequentially decoded `DialogBriefInfo.usedDialogTimelineIds` field,
  then either typed parent-dialog playback plus a validated LevelData BriefData
  host or one unique direct parent-dialog mission context supplies asset-shell
  context. `black_c13m3_0d5` now reaches the c13m3 mission shell through its
  exact parent dialog, but remains off a quest because that parent has two
  quest scopes. All 21 recovered clip rows resolve; none remain as an unmapped
  Timeline Actor root.

Typed black-screen actions now participate in the same exact LevelScript
condition scoping as dialog/radio/cutscene actions. This places
`black_e8m5_1` on `e8m5_q#1` through the exact `indie_dg007/26200040000`
MissionRuntime condition and native `0x0310/0x14` playback record. It does not
generalize Story-name ownership to the other black actions.

Dialog-authored narrative masks use a different original-data route. A
`dlg_*.json` TextAsset stores a base64 JSON `m_Script` whose root type is
exactly `Beyond.Gameplay.DialogTree`. After excluding ID-less unreachable
editor nodes, the current logical corpus contains 171
`DialogNarrativeMaskActionData` actions and two
`DialogComplexNarrativeMaskActionData` actions. Only the native-schema fields
`texts[].key` and `textDataList[].langKey.key` are attachment evidence. The 37
Chinese stage-direction literals occupying the same `key` slot and two empty
items are display annotations, not Story ids. A black file inherits placement
only when its exact line id resolves to one Story file, all occurrences agree
on one parent dialog, and that parent has one accepted original-data scope.
Direct quest/mission placement and multi-hop LevelScript/LevelData asset-shell
context remain separately labeled; the action is local client presentation and
does not create a server exchange or a new quest-sequence edge.
The extractor now also retains exact immediate line neighbors from typed
`DialogTreeConnection._sourceNode/_targetNode` references. It accepts a
line-level bracket only when the narrative action node has one incoming and
one outgoing connection and both adjacent nodes are typed parent-dialog trunk
nodes, and when the installed binary's `Graph.get_primeNode = allNodes[0]`
entry reaches the action through that predecessor. Node-array order is used
only for this binary-defined entry identity, never as chronology; editor
coordinates are ignored. This
bracket can close a missing-placement investigation, but it still cannot
create a file-level edge when the parent Story file has lines on both sides.
For example, `black_e11m4_1_001` is authored in
`dlg_e11m4_14` node `3` between exact trunk lines `_006` and `_007`; the
installed action is
`Beyond.Gameplay.DialogNarrativeMaskActionData` at
`nodes[3]._transitionData._actionGroups[0].actions[0]`. The gap queue keeps
that exact embedded placement and closes the isolated black file without
claiming either `dlg_e11m4_14 -> black_e11m4_1` or the reverse.
The source-gap queue now separates that complete two-sided line bracket from
an exact playback consumer whose local line position is still incomplete.
Twenty-nine additional isolated black files have 33 such unresolved
occurrences under 32 exact parent dialogs. Every closure requires the installed
typed narrative action, exact source object and PathID, complete original-data
parent scope, and a serialized path from the binary-defined prime node. They
are closed only as source-link/consumer gaps and retain
`linePlacementStatus=exact_parent_playback_line_position_unresolved`; no
scene-file edge is added. `black_e7m3_1` is the main-story example: node `11`
of `dlg_e7m3_14` contains `black_e7m3_1_003` at
`nodes[11]._transitionData._actionGroups[0].actions[0]`, is reached by
`0 -> 1 -> ... -> 9 -> 11`, and connects onward to node `12` /
`dlg_e7m3_14_007`, but no exact preceding parent trunk is recovered. Its exact
parent playback context is therefore known while its two-sided embedded line
position and any file-level order remain unknown.
The current pipeline emits 83 such connection rows. Three exact parent uses
remain unresolved and visible: one belongs to an otherwise connected file and
two are wholly unlinked. The parent-shell union now resolves
`black_c27m5_1`, `black_e11m7_1`, `black_sm1l2m1_1`, and the second
`black_c31m2_5` parent use. It requires exact typed DialogTree containment,
exact parent-dialog native playback, a complete validated LevelData member-22
host, and agreement from every independent typed MissionArea/position parent
context. `black_c27m4_1` now resolves to the `c27m4d5` mission shell: the
parent dialog plays in `dung02_rdg001/26900010002`, and 15 typed
`MissionAreaTrackingInfo` references join through
`MissionAreaTable.subDataParentId=26900010000` to an identical root in the
same complete LevelData member-22 dictionary. The competing `c27m4` identity
came only from the LevelData filename and is excluded from this typed ownership
decision. Quest placement remains unknown. Two ID-less, connection-less editor
nodes were removed from containment evidence; their files retain their
independent Timeline/native-black attachments. Each accepted connection stays
mission-shell client presentation with `serverExchange: false`, never a quest
gate.

Recovered script-condition placement is also checked against current-build
typed playback as negative evidence. If the condition's `(mapId, scriptId)`
does not equal a typed playback occurrence for that Story key, the quest link
is rejected. For example, the recovered `c31m2_q#6` condition names
`22800810007`, while `dlg_c31m2_7` plays in `22800810006`; the dialog therefore
stays on the validated `c31m2` LevelData asset shell and is not assigned to
`q#6`.

The only currently promoted general LevelScript quest-state gate is
`map01_lv002/200190001`: leader-enter trigger local id 7 waits for
`f1m5_q#18 == Processing`, waits 2.2 seconds, then runs the native `PlayRadio`
action for `radio_f1m5_2`. This proves a quest-state gate/context path, not a
server response or quest-completion effect.

PureGetter mission-state gates are now decoded independently of the
`OnMissionStateChanged` receiver family. The original LevelScript action graph
can put `GetMissionState("<mission>")` behind `CompareMissionState` and select
one Story action through an exact IfElse true/false edge. Every named mission
on that traversed predicate is retained as a direct state dependency, including
completed prerequisites in a nested path; no quest is invented. The clearest
current chain selects `dlg_a1m6d6_2` while `a1m6d6 != Completed`, otherwise
tests `a1m6d7 != Completed` to select `dlg_a1m6d6_4`, and selects
`dlg_a1m6d7_4` only after both tests are false. This evidence comes from the
installed binary, metadata, and original LevelScript bytes. The getter reads
the synchronized local MissionSystem cache, sends no request, and expects no
direct reply; inbound mission synchronization is an independent upstream
server path. These dependency rows are reported separately from attachment
coverage. Only a single-mission `Equal(Processing)` true branch is narrow
enough to add mission-shell playback context; `!= Completed`, completed-state,
and multi-mission branches remain non-owning dependencies.

Several earlier-looking task anchors were rejected after re-reading the
MemoryPack structure: the byte `0x08` in the apparent c16/e5/a1/e7 `taskMap`
records is a `LevelScriptTriggerVolumeData` member count, not `_nextID`.
Consequently those task-to-radio/dialog associations are not pipeline edges.

Authored DialogTree direct routes and LevelScript scene next-id chains may
attach one immediate unassigned neighbor to a uniquely quest-anchored Story
file. Recovery is deliberately non-transitive and excludes authored menus,
file order, cross-file order, property-flow proximity, and spatial proximity.
Serialized variable `.path` defaults are ignored when a differing
`constValue` exists; the latter is the runtime reference.

Recovered parent-mission evidence may resolve to a quest owned by a variant
MissionRuntime. The generated join therefore targets the actual quest's
mission sidecar rather than copying the scene onto every quest in the parent
mission. The source graph independently confirms exact authored chains such as
`a1m6d5_q#11 -> PlayRadio -> radio_a1m6d5_1`.

Those addresses and calls describe the installed build's native fallback.
The same methods contain IFix patch-dispatch paths, but the current
Persistent patch has 30 targets and replaces none of the placeholder
condition-type/activation methods. The WebUI records both the effective current
path and the requirement to re-audit after a patch update.

Quest ancestry orders scenes only when their attached quest sets prove a
strict predecessor relation. Sibling fork branches remain incomparable until
an authored merge or cross-branch edge exists. Sharing a quest, level, script,
or chunk proves membership, not mutual chronology.

Older chunk and spatial work remains useful diagnostically:

- connected Story components can be grouped into strong, weak, or unanchored
  chunks;
- scoped script-condition, variant-runtime, and NPC-proxy attachments improve
  quest ownership;
- quest pins, LevelScript float vectors, trigger volumes, source-file spans,
  and subchunks help investigation and display;
- none of those spatial/file signals become strict scene order by themselves.

## LevelScript control-flow recovery

The recovered ActionBase union names important playback and state actions,
including `PlayRadio`, `PlayRadioAndWait`, `PlayLevelSequenceAction`,
`StartDialogAction`, `StartDialogAndTeleportAction`, `SetBool`, `SetInt`,
`SetIntIncrease`, `ManualStartLevelScript`, and `ManualEndLevelScript`.

For the installed July 11 build, CodeRegistration `0x18b9217d0` resolves 1,313
contiguous ActionBase formatter tags `0x0000..0x0520`. Story playback mappings
are guarded by the normalized MemoryPack union tag plus concrete member count:
`PlayCutsceneAction` is tag `0x0357`, members `0x14`; `PlayRadio` is
`0x0363/0x0d`; `PlayRadioAndWait` is `0x0364/0x0d`; `StartDialogAction` is
`0x049e/0x0f`; and `StartDialogAndTeleportAction` is `0x049f/0x10`. Tags above
`0xf9` use `FA + u16 tag`; smaller tags use a single byte followed immediately
by the subtype member count. The parser now exposes `unionTag` and
`serializedMemberCount` for both layouts. Older audit `code/kind` values such
as `0x0b20/0x00` are retained for compatibility only: that compact envelope is
tag `0x20`, members `0x0b`, `dontLog=false`, not an opcode `0x0b20`. These
installed-build mappings must not be carried across builds without
regenerating the native audit.

The same installed binary now yields the complete `ActionHeader` formatter
table: 230 contiguous tags `0x0000..0x00e5`. The Story parser applies those
names only after `headerList` membership is proved because `ActionHeader`,
`ActionBase`, and `PureGetter` tags numerically overlap. As a result, every one
of the 153 remaining unlinked native playback files has a named event owner and
exact serialized control path across 182 receiver-to-Story placements;
the remaining gap is the producer/consumer bridge to MissionRuntime or server
state, not an unknown event class. The durable audit lives at
`reports/story/recovery/memorypack_union_formatter_tag_audit.{json,md}`.
One concrete collision is now a regression boundary: union tag `0x00b7` with
eight members means `ExitCustomMusicMode` in the `ActionBase` table but
`MissionEvent_OnServerGlobalVarChanged` in the `ActionHeader` table. Thirty-nine
current action records, including three residual activity Story scripts, have
that ActionBase shape. They must never receive the server-event name unless
independent `headerList` membership has first established the header role.

High compact record families are structurally useful but require care:

- legacy pair `0x0bed/0x00` is compact tag `0xed`, members `0x0b`, and carries
  terminal branches that can lead through local refs to concrete play actions;
- legacy pair `0x0a03/0x00` is compact tag `0x03`, members `0x0a`, and is a
  property gate with weaker ownership value;
- current legacy pairs `0x12be/0x00` and `0x12c0/0x00` are tags `0xbe` and
  `0xc0`, each with `0x12` members, for leader enter/leave trigger-volume
  events;
- property-changed and blackboard-change events are listeners, not proof of
  the writer sequence;
- static ActionBase setters do not cover many gameplay/server-owned property
  writes.

Current native control recovery also proves 71
`OnLeaderEnterTriggerVolume -> ManualStartLevelScript` and 69
`OnLeaderLeaveTriggerVolume -> ManualEndLevelScript` edges through authored
`ActionHeader.nextId`. This is event-to-control-action evidence only: 146 of
150 manual-control payloads serialize no literal target level/script id, and
the four literal script-id operands are self-targets. Physical adjacency cannot
turn these into cross-script, Story, or mission attachments.

Two additional exact mission-context joins use those typed paths without
claiming a request/response pair. `MissionEvent_OnClientGlobalVarChanged`
retains its literal variable key and is joined only when all matching
`CheckClientGlobalVar` consumers belong to one mission; `gm02m4` has six such
Story paths, but q8/q11 share the key so no quest is selected. A typed
`WaitForNpcProxyReady` step is joined to MissionRuntime proxy tracking only
when every matching proxy consumer agrees on one mission; the current build has
41 evidence rows. Both relations are local mission context and explicitly say
that no server exchange payload was decoded.

Two more current-build joins remain deliberately mission-scoped. The exact
12-field `Play3DRadio` payload is accepted only when it consumes the record to
EOF, its `radioId` equals the Story key, `useNpcProxy` is true, and one typed
same-scene `NpcProxyTrackingInfo` consumer yields a unique mission. This adds
39 evidence rows and newly connects `radio_e3m3_1` to the `e3m3` shell through
proxy `dengen_map01_e3m301`; it does not claim that q16 starts playback. A
second rule follows the complete typed
`LevelEvent_OnTravelPoleBegin -> EntityCompare -> IfElseAction ->
RaiseCustomLevelEvent -> LevelEvent_OnCustomEvent -> Story` route and then
requires the producer's validated LevelData member-22 shell to have one
authoritative mission union. It newly connects the three
`cutscene_e0m0_2ndZipline*` files to `e0m0`, again as local shell context rather
than quest chronology or a server exchange.

The six black-screen files with typed playback but no validated mission host
all have exact same-file event/control paths. Several are reached by
`ScriptEvent_OnLeaderEnterTriggerVolume` (slots `80001` or `80015`), one by
`LevelEvent_OnEntityHpChanged`, one by `LevelEvent_OnCustomEvent("rookie")`,
one by another leader-enter event through `Split`, and the four physical
occurrences of `black_sm2l6m1_4` by authored `ScriptEvent_OnCustomEvent`
callbacks. The paths use only `ActionHeader.nextId`, `ActionBase.nextId`, the
typed `Split._idList`, and typed `IfElseAction` false/true ids. Native recovery
also names compact tag `0x20` as `BlackScreenFadeOut`, tag `0x52`/members `0x09`
as `CheckBoolIfTrue`, tag `0x04f6` as `WaitForOneFrame`, and confirms that
`IfElseAction` serializes condition, false id, then true id. The exact e9 path
uses the true branch at all three gates.

This closes the event-owner question but not mission ownership. The current
six files comprise nine exact typed playback actions. Across 980
MissionRuntime assets, 874 decoded script-targeting conditions cover 438 unique
`(mapId, scriptId)` pairs; none names these ten playback occurrences or the two
typed a1m6 child scripts. No typed MissionRuntime trigger-slot field contains
`80001` or `80015`. The WebUI therefore shows an exact unscoped native subgraph
and keeps the files off mission/quest blocks.

The remaining 59 cold black files (64 exact line ids) still reject the obvious
indirect routes. A current-build exhaustive audit found zero consumer references
across all 4,512 LevelScripts, 85,447 other structured JSON/data files, raw
DialogTree/Timeline candidates, 13,614 PlayableDirectors, and the generated
typed attachment indexes. The Mission Pipeline labels these rows
`definition_only_unlinked`: the original TextTable definition exists, but no
current-build LevelScript black-screen action, typed DialogTree narrative-mask
action, or serialized Timeline black-text playable consumes it. This is a
bounded installed-build absence result, not a claim that the text was never
used.

Mission Pipeline schema 3 projects every accepted attachment and unresolved
native playback row into a normalized trigger route. This makes the exact event
owner, LevelScript, playback action, selector/control path, and final Story key
inspectable without upgrading context into ownership. It is a presentation of
current evidence, not new proof of global mission order: native registration or
code address order does not establish runtime chronology, and server successor
selection remains unavailable.

The first live runtime bridge is now hash-locked to the audited
`endfield-2026-07-11-gameassembly-0c557367` build. Its host verifies the game
executable, `GameAssembly.dll`, and IL2CPP metadata before attaching, while the
agent observes mission/quest state calls, `_RaiseOnScriptEvent`, action dispatch,
and the currently mapped dialog/radio/remote-communication/cutscene playback
entry points. The current-build SNS final boundary is now included:
`MainCharForceSNSBrain._StartSNSUI` (token `0x06014493`, method index `83090`,
RVA `0x70ef8b4`) reads the exact dialog id from `this+0x128` and chat id from
`+0x130` before the UI call. The dialog id is the original
`SNSDialogTable`/Story key. This is deliberately later than
`SNSSystem._StartForceSNS(chatId, dialogId)`, whose body can reject an already
finished dialog; `SnsTrackingInfo.Execute` is mission-HUD tracking and is not
playback evidence.

The asynchronous SNS gap is narrowed by an exact current-binary
object-identity handoff. `GameAction.StartForceSNS` (token `0x06008049`, index
`32840`, RVA `0x75ed938`) allocates one `ForceSNSQueueItemData`, writes chat
id/dialog id/`showToast` at `+0x18`/`+0x48`/`+0x50`, and passes that same
pointer to `GameAction.AddCinematicItem2Queue` (token `0x0600804b`, index
`32842`, RVA `0x75dcf58`). `MainCharForceSNSBrain.StartForceSNS` (token
`0x060144a7`, index `83110`, RVA `0x70ed65c`) retrieves the pointer from
`CinematicQueueItemHandle+0x18`; only a successful consumer copies its
dialog/chat ids into the brain that later reaches `_StartSNSUI`. The recorder
therefore propagates an existing dispatch chain by pointer identity and checks
all copied values fail closed. It never joins on matching SNS ids, timing, or
queue order. A request that began after the dispatch stack unwound still emits
null ownership at final playback; the handoff preserves evidence but cannot
invent an earlier owner.

Queued dialog recording now has the same request-versus-playback separation.
The current bodies of `PlayDialogAndHideSceneObjectAction.PlayCinematic`,
`StartDialogAction.Execute`, and `StartDialogAndTeleportAction.Execute` call
`GameAction.StartDialog` (token `0x06008038`, index `32823`, RVA `0x75ed524`).
It writes the exact dialog id to `DialogQueueItemData+0x18` and passes that
object to `AddCinematicItem2Queue`. `DialogManager.PlayDialogByHandle` (token
`0x0600f777`, index `63350`, RVA `0x6e15e40`) later recovers the same pointer
from `CinematicQueueItemHandle+0x18`. Its nested `PlayDialogByJsonId` reaches
`DialogManager._PlayDialogInternal` (token `0x0600f84e`, index `63565`, RVA
`0x6e28040`) only after `_CheckCanPlayDialog` succeeds. The recorder now emits
the three action-backed dialog rows at that accepted boundary, carrying the
chain through pointer identity and requiring all five dialog-id observations
to agree. Rejected requests no longer become playback edges. This can reduce
edge counts relative to request-level tracing; the reduction is an evidence
correction, not lost recovery. `StartContinuousDialog` has a distinct
non-queue route and is not upgraded by this proof.

The same current-binary audit expands the string-param action set with
`FlushAndPlayRadio.Execute` (`0x06008dfb`, index `36346`, RVA `0x7672390`),
`StartContinuousDialog.Execute` (`0x06008d39`, index `36152`, RVA
`0x766dbb4`),
`PlayCutsceneIgnoreCinematicQueue.Execute` (`0x06008e23`, index `36386`, RVA
`0x7676618`), `PlayLevelSequenceAction.Execute` (`0x06008e2e`, index `36397`,
RVA `0x767713c`),
`PlayLevelSequenceAndControlSceneObjectsAction.PlayCinematic`
(`0x06008e3d`, index `36412`, RVA `0x7677b24`), `Play3DRadio.Execute`
(`0x06008e0a`, index `36361`, RVA `0x7675670`),
`Play3DRadioAndWait.Execute` (`0x06008e0f`, index `36366`, RVA `0x767514c`),
`PlayDialogAndHideSceneObjectAction.PlayCinematic` (`0x06008cf2`, index
`36081`, RVA `0x7669a84`),
`StartCutsceneAndControlSceneObjectAction.PlayCinematic` (`0x06008e8b`, index
`36490`, RVA `0x767cff4`),
`StartCutsceneAndHideSceneObjectAction.PlayCinematic` (`0x06008ea7`, index
`36518`, RVA `0x767dd14`), `StartCutsceneAndTeleportAction.Execute`
(`0x06008ec7`, index `36550`, RVA `0x767e1ec`),
`StartDialogAndTeleportAction.Execute` (`0x06008ede`, index `36573`, RVA
`0x767f6b0`), and
`StartRemoteCommAndTeleport.Execute` (`0x06008eed`, index `36588`, RVA
`0x768008c`). Exact body scans show each reaches the already mapped
`Param<string>.GetValue` resolver while its concrete action boundary is active.
The control and hide classes have distinct native bases and distinct
`PlayCinematic` overrides; using those exact overrides avoids guessing a
concrete class at an inherited `Execute` entry.

The remaining hide-level-sequence override is now covered too:
`PlayLevelSequenceAndHideSceneObjectsAction.PlayCinematic` is token
`0x06008e4c`, index `36427`, RVA `0x76781bc`; its current body resolves
`_levelSeqId` and calls `GameAction.PlayLevelSequence`. This is binary coverage,
not evidence that a current LevelScript instance exists: the current 3,691
decoded LevelScript files contain no record of this class, `FlushAndPlayRadio`,
or `StartContinuousDialog`. The hooks remain valid for other exact runtime
containers on this hash-locked build.

The same audit rejected name-only candidates. `PlayVoiceNarrative` resolves
`au_*` audio rather than a Story key. `FacPlayInteractLockedRadio` resolves
factory-instance and building ids. `TravelPoleHandoverToCutscene.Execute`
does not read `_cutsceneId`; it calls `CutsceneManager.TryGetCutsceneHandle`
without an id and passes the existing handle to
`TravelPoleBrain.HandoverToCutscene`. The four current typed TravelPole rows are
handover context, not four new cutscene starts. Preload/custom-event/stop/pause
classes are also excluded from final-playback instrumentation. Formatter
presence, class name, and source code address never create a playback edge.

FMV uses a closed current-build map rather than a generic transform.
`PlayFmvAction.Execute` (`0x06008e2b`, index `36394`, RVA `0x7676be4`) and
`StartFmvAndTeleportAction.Execute` (`0x06008ee5`, index `36580`, RVA
`0x767fbe8`) resolve exact native fields. A complete scan of current typed
LevelScript FMV actions found 37/37 decodable records: 30 distinct plain
`cs_video_*` ids plus `f_cs_video_e9m3_1`. Exactly 22 plain ids have a matching
current `cutscene_*` Story file, and those 22 exact pairs are embedded in
`playbackKeyMaps.fmv`. Eight plain ids without a Story file and the separate
gender-prefixed id are intentionally absent and produce missing-key
diagnostics. No general prefix rule, OCR, or manual override participates.

The bridge produces importable JSONL plus separate diagnostics. Observed
sequence and active-quest context remain an overlay: they do not create authored
mission ownership or source order. The present hook cannot recover the
serialized ActionHeader local id from the live event callback and therefore
records null.

Action-backed black-screen capture is now mapped end to end from the current
binary. `ComplexNarrativeBlackScreenAction.Execute` (token `0x06008ca9`, index
`36008`, RVA `0x7660bf0`), `NarrativeBlackScreenAction.Execute` (token
`0x06008ce9`, index `36072`, RVA `0x7668c84`), and
`StartNarrativeBlackScreenAndTeleport.Execute` (token `0x06008d45`, index
`36164`, RVA `0x766e494`) each call
`GameAction.ShowNarrativeBlackScreen` (token `0x0600802b`, index `32810`, RVA
`0x75ec4b0`) synchronously. Current `GameAssembly.dll` bodies and the exact
MetadataRegistration type graph establish the object path:
`UICommonMaskData.textDataList` at `+0x70`,
`List<CommonMaskTextData>._items/_size` at `+0x10/+0x18`, array data at
`+0x20`, and the embedded `Beyond.LangKey.key` pointer at each item `+0x10`.

The current original `TextTable.json` has 249 native `black_*_NNN` line ids.
All normalize without collision to 215 exact Story roots, and each root has the
matching generated Story file. The only generated exceptions are three lines
in the WebUI-authored `black_webui_secret_notice`; they do not exist in the
original table and are excluded from native evidence. The recorder therefore
keeps the concrete action pending, decodes the final mask list, and emits only
when all native line ids have the proved shape and agree on one Story root.
Missing action context, custom/unreadable text, invalid list bounds, malformed
ids, or mixed roots produce diagnostics. OCR, manual overrides, nominal
filenames, and display order are not consulted.

Late-attach MissionSystem state recovery is now implemented from the same
current binary. `MissionSystem.Tick` is token `0x0600522b`, method index
`21034`, RVA `0x34e3890`. Current compiled accessors place `m_idMap`,
`missions`, and `currentQuests` at `this+0x70`, `+0xd8`, and `+0xe0`. The
compiled generic dictionary enumerator proves entries/used-count/version at
`+0x18/+0x20/+0x2c`, array data at `+0x20`, a 24-byte entry stride, and
hash/key/value at entry `+0/+8/+0x10`. The data accessors and field metadata
place both embedded ids at `+0x10` and states at `+0x18`. Metadata constants,
not declaration-order inference, give mission states `0..5` and quest states
`0,2,3,4,5`; both use `Processing=2`.

The recorder takes a bounded one-shot snapshot on Tick, verifies dictionary
versions and bounds, validates every live entry, requires dictionary keys to
equal the embedded mission/quest ids, and requires each current quest to
resolve through the exact string-to-string `m_idMap`. Only after the complete
read succeeds does it seed its quest map and emit the currently processing
mission and quest rows. Any missing dictionary, identity mismatch, unknown
state, concurrent change, or retry exhaustion remains diagnostic and emits no
partial state. OCR, manual overrides, recovered order, and filename patterns do
not participate.

No real trace has been captured because the protected client still refuses the
instrumentation attach, and anti-cheat must not be weakened or bypassed.
Asynchronous dispatch propagation and other unmapped playback entry points
remain the next recorder coverage frontier. The late-attach reader is
hash-locked and testable statically, but remains unobserved until a supported
capture environment is available.

Reading every maintained occurrence carrier materially expands exact trigger
visibility, and strict path-prefix comparisons add
`levelscriptNativeControlPath` order edges. Current counts remain in the
generated binding-coverage and source-partial-order reports. Most scene pairs
remain source-unordered; this is an evidence ceiling, not a request to sort
unknown pairs by suffix, address, file offset, or display rank.

The exact native topology currently exposes 71 Story-bearing branch groups:
32 `Split`, 19 `IfElseAction`, and 20 `SwitchInt`, plus four convergence points
that are present on every observed arm. The 39 conditional groups use 35 exact
typed PureGetter references and four exact inline `Param` values. Operand
recovery is complete for 37 groups: boolean/property paths and constants,
integer/float comparers, random bounds, current/explicit LevelScript targets,
stage case values, mission-state comparisons, and Endministrator gender. The
two remaining e0m2 groups are exactly named `GetConditionResult`, but their
delegate-backed inner condition object is not yet safely decoded. This does
not prevent branch recovery; it limits only the human-readable predicate.
All 71 branch groups now retain an exact serialized event selector; the
selector gap count is zero. The last eight were closed from the current bytes,
not by filename inference: two trigger-volume records serialize slots `80006`
and `80004` with a source-100/null-path `ParamOutput`, four nested `e11m3`
branches share `LevelEvent_OnSpawnerEntityDie` for spawner `23100080001`, the
`f1m18d1` split is selected by entity slot `40002` saved-property `state`, and
the seven-arm `m1m74` switch runs on local `ScriptEvent_OnScriptComplete`.
The spawner-death selector and repeated nested branch path are still one event
context, not four independent chronological triggers. Neither branch arms nor
independent ActionHeaders gain an order merely because they share a file,
numeric suffix, native registration sequence, or code address.

The same files still reject the obvious indirect routes.
Exact line strings and signed i18n ids are absent from current LevelScripts;
common CRC/FNV/DJB2/SDBM/Jenkins/Murmur candidates produce no validated hit,
including against positive-control scripts that serialize their line ids
directly. Native `ShowNarrativeBlackScreen` writes only mask data into a
transient cinematic queue item; it does not populate a reusable authored
`cinematicId`, and callback/handle counters add no owner edge. Hash, queue-id,
and callback promotion remain rejected.

Native schema recovery also closes the earlier PPtr hypothesis:
`UICommonMaskData`, `CommonMaskTextData`, and both dialog narrative-action data
types are ordinary managed inline/runtime data, not Unity objects referenced by
PPtrs. Timeline Common Mask tracks resolve through `FadePlayableAsset` only to
`CutsceneMaskData.color`; they carry no narrative LangKey. Broad exact
CHK+PathID traversal of that visual branch found none of the cold ids. Future
work should therefore follow typed DialogTree/LevelScript/server-registration
consumers, not generic Common Mask PPtr closure.

### `LevelEvent_OnDialogExit`

The July 11 installed client uses CodeRegistration `0x18b9217d0` and
MetadataRegistration `0x18b921c30`. Recovered
MemoryPack formatter mappings identify compact tag `0x55`, members `0x13`
(legacy decoded pair `0x1355/0x00`) as `LevelEvent_OnDialogExit`.

This encoding is build-specific. The same five serialized headers used
`0x1250/0x00` in the older `export_full_1d3d2`, but use `0x1355/0x00` at the
same local ids in the current export. Current native registration loads
metadata slot `0x18e36d3d8` (`LevelEvent_OnDialogExitFormatter`) and registers
ActionHeader union tag `0x55`; the current corpus contains 271 `0x1355` rows
and no `0x1250` rows. Old tag `0x50` now resolves to
`LevelEvent_OnCountdownFinish`, so carrying the historical constant forward
would silently stop re-deriving the dialog-exit edges.

An exit chain is promoted only when:

1. the event header resolves to exactly one same-mission Story scene;
2. `ActionHeader.nextId` resolves unambiguously into `actionList`;
3. each linked action record resolves to zero or one Story scene;
4. record `nextId` links establish the action sequence;
5. self-only references and ambiguous records are discarded.

The current export produces 16 strict dialog-exit edges. The six originally
established edges remain:

- `misc_dlg_c16m4_2d5 -> radio_c16m4_33`
- `misc_dlg_e3m1_1d5 -> radio_e3m1_1d5`
- `dlg_e3m6_105 -> dlg_e3m6_11`
- `dlg_e7m3_3 -> radio_e7m3_6`
- `dlg_sm2l2m7_8 -> black_sm2l2m7_1`
- `black_sm2l2m7_1 -> dlg_sm2l2m7_9`

Ten additional current-export edges cover `e11m2` (one), `e11m4` (two),
`e11m8` (one), `f1m32` (five dialogs converging on `dlg_f1m32_15`), and
`sm2l7m1` (one). All 16 are included in the generated source-only audit's
1,912 strong edges; current-data re-derivation no longer depends on the stale
historical opcode.

A separate attachment audit scans all 271 current `OnDialogExit` headers. Only
21 headers produce 22 raw source-to-target Story edges. Nineteen sources have
one mission owner, but every corresponding target is already attached; three
sources are unassigned. The sole unassigned-target near miss is
`misc_dlg_e3m1_1d5 -> radio_e3m1_1d5`, and it is rejected because the source is
also unassigned. Thus this family currently adds no connection to the 1,356
file remainder. Current tag `0x55` is the local client event; tag `0x8a` is the
distinct `LevelEvent_OnServerDialogExit`, so the local chain is not presented
as a server request/response.

### Local lifecycle, battle-signal, and spawner events

Current-binary schema replay closes several high-count event families without
inventing ownership:

- `ScriptEvent_OnScriptActive` has 16 serialized members and no subtype
  fields. All 1,052 real current headers use `triggerTarget=SELF` with a null
  inherited `_targetScript`.
- `ScriptEvent_OnScriptStageChanged` has 18 members and appends
  `_newStageFilter: Param<int>` and `_newStageOutput: ParamOutput<int>`. All 455
  current headers also use `SELF` with null `_targetScript`; 449 carry a
  constant stage filter, six have no filter, 20 have an output, and 435 have a
  null output. Values such as `10`, `45`, and `122` in the inherited prefix are
  `_validate.idRef` links to local validation nodes, not script or mission ids.
- Both lifecycle events are raised and consumed inside `LevelScriptRuntime`.
  They carry no mission/quest id and no RPC or expected server return. The
  pipeline labels them as local lifecycle/condition nodes and requires a
  separate unique LevelData/MissionRuntime owner before attachment.
- The nine unassigned spawner Story rows decode to six exact
  `OnSpawnerGroupBegin` headers and two exact `OnSpawnerWaveBegin` headers (one
  group header feeds two Story rows). Their constant group/wave keys,
  `SpawnerPtr.id` values, null outputs, and EOF are exact. All live in
  `map02_lv007/10200260001`; the validated LevelData shell and SpawnerConfig
  prove gameplay wiring but no unique MissionRuntime owner, so zero are
  promoted. A typed cross-script dependency does exist: LevelScript
  `10200060009` task `5f624bcc`, condition `87cbeaa6`, uses current
  GameCondition union tag `0x54` (`CheckLevelScriptStageReachMax`) to wait for
  script `10200260001`. It proves gameplay ordering between scripts, not
  mission ownership.
- Five chronology relations inside that unowned e11m1 set are independently
  recoverable without solving ownership. The current generated
  `SpawnerConfig` formatter serializes `waveMap` last, `SpawnerWaveData` in
  eleven fields, and `SpawnerGroupData` in twelve. The fail-closed decoder now
  finds one unique complete nine-wave/20-group parse for
  `sc_map02_lv007_10200260004`, leaving each nested action map opaque but
  requiring exact group and wave boundaries. Wave key `5` has
  `waveMode=PartKilled`, kill count `5`, and target key `4`. Current
  `TimelineWaveBlock.OnInit` resolves mode 2's `waveModeTargetKey` through
  `Timeline.TryGetWaveBlock`, stores that exact block as
  `previousWaveBlock`, and `AllowToSendStart` reads its killed count before the
  dependent wave can start. Exact typed `LevelEvent_OnSpawnerWaveBegin`
  actions therefore prove
  `radio_e11m1_85` (wave 4) -> `radio_e11m1_84` (wave 5). The installed
  Persistent IFix payload's 30 targets replace none of `Timeline.Tick`,
  `TryGetWaveBlock`, `TimelineWaveBlock.OnInit`, `AllowToSendStart`, or
  `StartWave`.
  The same original config nests story-bearing groups `201`, `601`, and `701`
  in waves `2`, `6`, and `7`. Installed
  `TimelineWaveBlock.InitWave` enumerates the decoded group map into
  `groupList`; group mode 1 (`Sequence`) receives the immediately preceding
  block, while mode 2 (`PartKilled`) resolves its named target.
  `TimelineWaveBlock.Tick` calls
  `AllowToStart`, then `StartGroup`, before ticking group actions.
  `StartGroup` synchronously raises `ON_SPAWNER_GROUP_BEGIN`, and `StartWave`
  synchronously raises `ON_SPAWNER_WAVE_BEGIN`. Requiring every possible
  spawning group in a parent wave to descend from one first group therefore
  proves four direct-callback `spawnerWaveGroupPartKilled` edges:
  `radio_e11m1_80 -> radio_e11m1_85`,
  `radio_e11m1_83 -> radio_e11m1_85`,
  `radio_e11m1_84 -> radio_e11m1_92`, and
  `radio_e11m1_92 -> radio_e11m1_45`. The two group-201 callbacks remain
  unordered relative to each other because the binary evidence proves only
  that both precede the wave-4 gate, not listener dispatch order.
  One more exact group route is indirect but still binary-complete. Wave 8 is
  mode-2 `PartKilled` on wave 7 with kill count `2`; group `701` dominates the
  possible wave-7 spawns, while group `801` begins in wave 8. Group-801 action
  `105` is an exact current-script `RaiseCustomScriptEvent("TigerStart")`;
  exact same-script listener header `140` reaches typed cutscene action `151`.
  This proves `radio_e11m1_45 -> cutscene_e11m1_tiger` without treating the
  event-key string alone as evidence. All six spawner edges are uncovered by
  both manual and OCR order lists.
  Sequence/Parallel modes without a complete domination chain, unrelated
  group callbacks, and HP thresholds remain non-ordering. The current HP audit
  now closes the callback-order question negatively rather than leaving it
  merely unstudied. `OnEntityHpChanged.Process` uses the exact Down crossing
  predicate `oldRatio > threshold && newRatio <= threshold`, so one damage
  update can select multiple thresholds. `RegisterTriggerFromLevelScript`
  visits the serialized headers in order, but
  `_DoTryInvokeEventActionTriggerList` snapshots the shared event-key
  dictionary's `Values` and iterates entry indices; `_AddEventListener` uses
  normal Dictionary insertion with reusable free slots. A complete managed
  caller census finds ordinary gameplay components registering
  `GameEntityEvent` key `9` outside LevelScript (including abandon-pack,
  common-Lua-UI, blight-zone, highlight, and rune-column components).
  Consequently the six e11m1 HP listeners cannot be proven to retain their
  serialized relative callback order after earlier key-9 listener removals.
  No `90% -> 65% -> 10%` or `10% -> 5%/1%` Story edge is promoted. All twelve
  Story keys in the former
  `map02_lv007/10200260001` context are now recognized as exact typed native
  playback; their unresolved mission/quest owner remains an ownership gap, not
  an untyped-control-flow gap.
- A separate current `OnSpawnerComplete` listener carries exact constant
  `SpawnerPtr.id=23100270003` and reaches `radio_gm02m20_19`. The sole same-id
  original `SpawnerConfig` is in `map02_lv008` and its authored enemy ids contain
  exactly one current MissionRuntime token, `gm02m20`. This adds mission-shell
  context. Completion is a server push with scene/spawner identity and does not
  identify a quest or prove objective completion.
- Thirty unassigned `OnBattleSignal` Story rows use 25 unique signal strings.
  Every string has an exact current `Core_SendBattleSignalToLevel_Data`
  producer: 36 occurrences across 27 original `SkillData`/`BuffData` files.
  Current AbilityActionData tag is `0x0134`, members `6`; the older `0x011f`
  parser constant is stale. Exact current AbilitySystemData skill lists take
  31/36 actions to enemy templates: agtrinit 6, palesent 6, palecore 1, reaper
  16, and klhound/klhog 2. This still produces no complete typed producer ->
  owner -> selecting-spawner -> MissionRuntime chain: the first two groups lack
  exact spawner/mission edges, palecore conflicts with the listener context,
  reaper lacks a listener-script mission owner, and hound/hog configurations
  are non-unique. Producer-to-listener wiring and most ability ownership are
  exact, but ability ownership is not mission ownership, so zero are promoted.
  Within the current exact-native unlinked queue, 16 Story files use 12 of
  those signals and resolve to 20 producer actions across 13 original
  Skill/Buff files. Native `SendBattleSignalToLevel.ExecuteInternal` at
  `0x186d27734` raises local LevelEvent `0x28` directly; there is no server
  packet. `OnBattleSignal.Process` filters only signal/value and has no sender,
  entity, spawner, mission, or quest selector. All 980 MissionRuntime files
  contain zero relevant identity hits for this subset.

Current binary-first negative audits further constrain the residual set:

- The current residual `OnLeaderEnterTriggerVolume` family contains 71 Story
  keys, 74 exact node/key placements, 76 playback actions, 58 receiver headers,
  and 51 script owners across 13 levels. The event carries only a local
  trigger-slot filter/output. Exhaustive current MissionRuntime, MissionArea,
  position, entity/NPC tracking, script-condition, interactive-entity,
  WorldEntity-group, LevelData, and SpawnerConfig joins find no unique typed
  owner: the LevelData shells are shared for 24 scripts and absent for 27, with
  zero unique mission hosts. Every selected volume has `waitSrvRes=false`, so
  the local Story event is not response-gated. The touch request/response
  carries only `sceneNumId`, `scriptId`, `scriptLocalId`, and `isLeaveAction`;
  its response returns no mission ownership. A separate
  typed WorldEntity bridge now connects three files as quest context: the exact
  `CheckMonsterKilled` set for `e3m2_q#3` and direct `InteractiveCheckInt` set
  for `gm02m11_q#4` resolve through validated
  `LevelScriptBriefData.refWorldEntityIdList` entries to the two playback
  scripts. This does not turn the Leader event into a quest/server activation
  edge; the other 71 files remain unlinked.
- The current residual `OnScriptStageChanged` queue contains 16 Story keys, 19
  playback occurrences, 13 receiver headers, and 12 owning LevelScripts. Eight
  headers filter stage 1, three filter stage 2, one filters stage 3, and one is
  unfiltered; every event targets `SELF`. None of the owning script ids appears
  in the 980 current MissionRuntime assets, the source
  graph has no mission/quest/condition edge, and LevelData yields no mission
  host. The exact upstream route is the one-way server notification
  `SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE {sceneNumId, scriptId, stage}`; current
  metadata has no client request counterpart or expected response. The packet
  supplies runtime causality but no mission/quest identity by itself. The typed
  WorldEntity bridge independently scopes `radio_e2m5_19` and
  `radio_sm2l4m2_3`, plus the latter script's three level-owned Lingyuan
  cutscenes, without claiming condition-to-stage activation. Sixteen pipeline
  files remain unlinked in this family.
- Twenty-three custom-event listener-owner rows cover 19 Story keys and 21
  level/domain/key routes. Exact local producers cover 8/16 ScriptEvent files
  (nine producer/listener pairs because `radio_sm2l5m1_33` has two) and 1/3
  LevelEvent files. None of their seven relevant LevelScript ids occurs in any
  current MissionRuntime asset. The other eight ScriptEvent and two LevelEvent
  files have no matching authored `RaiseCustom*` producer. These transports
  carry only event key, optional arguments, and for ScriptEvent a local script
  receiver; they contain no mission/quest/server identity. They therefore do
  not establish ownership on their own. A stricter surrounding-payload join now
  adds non-owning quest context to four of these ScriptEvent Story keys: every
  occurrence is under the exact same interactive-state route, all copies agree,
  and the byte-identical authored payload has a complete
  `SimpleConditionCheckQuestState(Equal, Completed)` lock for one real
  MissionRuntime quest. Four direct interactive-state Story roots satisfy the
  same proof, for eight context relations total (seven to `sm2l5m1_q#1`, one to
  `sm2l5m1_q#8`). The remaining exact-native Script CustomEvent family is 12
  files.
  The maintained `RaiseCustomScriptEvent` decoder now proves ActionBase
  tag/member `0x0380/0x0b`, the exact event key, and either a current-script or
  constant-script `Param<LevelScriptPtr>` receiver. Across the complete typed
  listener corpus it finds 46 producer records for 40 Story files; 15 routes
  are shown on 10 currently unassigned pipeline rows. That richer local
  causality intentionally leaves the connection count unchanged.
- Three residual `OnTeleportFinish` action ids occur only in their listener
  payloads across current exported JSON. They occur in neither MissionRuntime
  actions nor teleport-validation rows. Native code compares the serialized id
  by exact string equality and later sends `CS_SCENE_TELEPORT_FINISH(tpUuid)`,
  which carries no mission/quest identity; all three remain unlinked.
- Five residual `OnGuideGroupComplete` files use exact serialized guide-group
  ids. Current ActionBase tag/member-count `0x0304/0x09` proves
  `ManuallyStartGuideGroup`; native execution marks these groups client-only,
  and their completion branch skips `CS_COMPLETE_GUIDE_GROUP` before raising
  the local completion event. The three `e0m0` tutorial producers have no
  validated mission host. The Camille producer has a unique `c33m1`
  mission-named LevelData host, but its one group id reaches both
  `radio_c33m1_37` and `radio_c33m2_30` in separate listeners, so it cannot
  select the latter's owner. `guide_group_miasma_ghost` has no exact manual
  start. All five remain unlinked; the pipeline now knows that these manual
  routes have no server exchange.
  Separately, the 37 authored MissionRuntime `CheckGuideGroupComplete`
  conditions retain 36 exact group ids and all use completion mode `All`; none
  names any of these five residual ids. Server-backed guides have the exact
  `CS_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClose }` /
  `SC_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClosed }` exchange, but those
  packets carry no mission/quest/condition identity beyond the guide id.
- The remaining exact `OnAnyEntityDie`/`OnSpecificEntityDie` Story routes expose
  their entity filters but no mission id. One `cutscene_e3m5_2` reuse belongs to
  `dung01_bossrush03_02`, whose original `missionWhitelist` is empty. The other
  death targets lack unique MissionRuntime ownership, so none is promoted.
- The broader combat/encounter audit covers 17 unique Story files, 18 family
  memberships, and 30 exact playback routes across cast-skill, HP-threshold,
  any/specific death, encounter-begin, squad-in-fight, and skip-popup
  receivers. Literal targets resolve to current entity/template rows where
  possible, while direct MissionRuntime target references and all 12 LevelData
  host joins remain empty. A newly decoded dynamic-list path supplies the one
  safe indirect exception: in `map02_lv008/23100270001`, exact
  `OnSpawnerEntitySpawn(23100270003, group 101) -> ListAddValueEntityPtr
  (entity03_01) -> OnEntityHpChanged(Down, 1%)` chains reach
  `radio_gm02m20_9` and `radio_gm02m20_18`, and the sole same-level
  SpawnerConfig names only `gm02m20` in authored enemy ids. Those two gain
  mission-shell context, not quest ownership; the HP event remains local and
  has no server exchange. The equivalent e11 chain has no authored mission
  token, and reused boss-rush subgames still have empty `missionWhitelist`
  fields.
- Six former residual NPC-checkpoint Story files now have an exact non-owning
  `sm2l5m1` mission-shell context. Each accepted occurrence requires the exact
  `OnNpcPatrolCheckpointReach -> Story` control path, a same-script
  `NpcPatrolStart(alias, patrolId)` producer, a fully consumed current
  `NpcPatrolData/9` row whose checkpoint is in range, and a type-13 BriefData
  property resolving the case-sensitive alias through `refWorldEntityIds` and
  `WorldEntityRegistry`. Across all 471 typed `EntityTrackingInfo` rows, the
  14 qualifying same-scene non-script trackers for entities `23200010664`,
  `23200013030`, and `23200013387` all belong to `sm2l5m1`; their quest sets
  remain candidate navigation context only. `radio_sm2l5m1_18` retains both
  exact listener occurrences and two patrol ids. The relation explicitly sets
  ownership, quest activation/playback/completion, client request, expected
  reply, and server exchange to false.
  The seventh patrol file,
  `radio_c27m4_9`, has an exact `ScriptedCharPatrolStart -> patrol point 2 ->
  SendEvent("patrol2end") -> listener -> Story` chain. None of the script,
  patrol, or detail ids is owned by MissionRuntime. A same-level `tangtang*`
  NpcProxy names `c27m4d5`, but patrol alias `tangtang` has no recovered typed
  alias-to-proxy edge, so that correlation remains diagnostic and this one
  scripted-character file stays unlinked.
- All 11 residual interaction/property receivers now have exact local entity
  ownership and native playback chains: ten resolve to current interactive or
  world entities and one to an authored Leader trigger volume. Exact
  MissionRuntime objective/condition/tracking references are zero, none of 471
  typed `EntityTrackingInfo` rows matches, and NPC/LUT/spawner ownership adds no bridge.
  Two nearby mission coordinates were rejected because they serialize no owner
  identity. These local event bodies carry no mission/quest/network payload,
  so all 11 remain unlinked.
- Adding Script property/blackboard listeners expands that entity/property
  audit to 20 unique Story keys across seven event families, all with exact
  serialized listener/control routes. Four property listeners are SELF-scoped;
  four blackboard listeners have same-script `SetInt` producers; the rune-match
  custom event has two exact rune-column receivers. None matches any of 980
  MissionRuntime files, 490 mission sidecars, the typed tracking corpus, or a
  validated Mission/MissionArea LevelData host. Their mapped handlers contain
  no protobuf request or network send. Zero are promoted.
- After the six NPC-checkpoint promotions, the remaining
  guide/scripted-patrol/teleport/dialog-exit/script-complete queue covers 11
  Story files and 11 listener occurrences. It yields zero further promotions, two
  ambiguities, and 15 proven-negative joins. The only ambiguities are the
  Camille guide id's two Story listeners and the untyped `tangtang` patrol
  alias-to-NpcProxy candidate. Native checkpoint, ScriptComplete, DialogExit,
  and teleport bodies prove local event semantics but no mission identity.
- Mission RPCs and LevelScript RPCs occupy separate identity domains: audited
  packets carry mission/quest ids or scene/script/event ids, not both. Matching
  event names across those domains is therefore not accepted as ownership.
- Typed `SubGameInstanceData` provides 20 conflict-free original-data rows that
  carry `dungeonMissionId` and UInt64 `bindScriptId` together. Native subgame
  creation resolves `SC_GAME_MECHANICS_SYNC_ENTER_GAME_INST.gameId` through the
  typed row and constructs the concrete runtime. The exact MemoryPack setter
  writes `bindScriptId` at row offset `+0x50`, and
  `WorldChallengeGame.SendQuit` reads it to resolve and manually end the
  LevelScript before sending the stop request. This proves lifecycle/cleanup
  use, not activation: the audited concrete and shared start paths do not read
  the field. No lifecycle packet carries mission/quest/scene/script ownership
  together. All 20 scripts remain parent-zero roots with no descendants and
  have zero intersection with unresolved native playback, so the pipeline keeps
  them as `subgame_bind_script_runtime` mission-shell evidence only. Same-
  LevelData siblings and ten missionless SubGame playback intersections stay
  rejected as mission ownership until original data supplies the missing owner.
  The latter are no longer visually discarded: an exact occurrence-script join
  exposes ten missionless runtime nodes with nine unique Story files and
  fourteen SubGame-to-Story placements. The complete current exported-reference
  census adds no owner. The ten primary task ids occur only in their SubGame
  rows and `ScriptTaskExtraInfoTable`; three secondary task ids occur only in
  the display table, and the already complete receiver-task audit has zero
  MissionRuntime consumers. Boss `e1m8_q#4` and mission `e3m5` are exact
  `QuestStateEqual`/`MissionStateEqual` unlock prerequisites for the first
  tiers of their respective boss-rush SubGames; the latter now appears on
  `dung01_bossrush03_01 -> bindScriptId 17500000002 ->
  cutscene_e3m5_1` as availability context only. Five other boss rows carry
  only prior-challenge gates, and dungeon series/scene/reward records contain
  no playback owner. The exact
  activity-stage-6 mission/rank association remains separate in native runtime
  storage. The activity stage-3/4 rows do name `a1m6d3/a1m6d4`, but serialize
  no `rankRelatedId` or other exact reference to
  `activity_qingxi_qiangti_3/_4`; matching suffixes and Story names are not
  accepted as identity. None is promoted to ownership.
- The installed IFix patch's 86 `dlgtl_*` strings are an exact
  `_TimelineAsyncCompileProcess` prebind allowlist. Of 56 Story-name transforms,
  53 are already connected by stronger evidence. The three residual files
  (`dlg_e11m5_9`, `dlg_e11m8_9`, `dlg_e5m0d5_1`) have Timeline and
  PlayableDirector parents but no typed mission/quest/level/LevelScript owner;
  the naming transform adds zero coverage.

## Dialog lines and option branches

Intra-conversation line order is usually strong when a DialogTree or Timeline
exists. Numeric line suffixes remain fallback identity only; authored clip
times can skip or reorder suffixes.

The strict audit currently accepts 368 option groups, 767 routes, and 1,597
branch lines:

- 345 groups come from direct DialogTree/DialogTreeFragment paths;
- 22 groups come from exact Runtime Jump Track routes;
- one group comes from exact positive Timeline clip `optionIndex` routes.

It retains 1,964 excluded evidence groups (3,077 options), of which only six
remain actionable, plus 650 groups (732 options) with no explicit route.
Missing routes are not silently converted to branches.

Runtime field evidence establishes the following model:

- `DialogOptionPlayableAsset.GenPlayable` supplies serialized option rows;
- the selected option index flows through the Timeline manager and `+0x98`
  into `DialogChooseOption`;
- `+0x18` is the active option-clip gate used before `SetDialogOption`;
- `TryTriggerTrunkBindingOption` ignores zero-valued trunk clips and only
  activates a candidate whose runtime option field is positive;
- `RuntimeClip.<optionIndex>` and `TimelinePlayable` current/new/last option
  state feed `DoJump` / `DoReverseJump` and `TimelineRuntimeUtils`;
- `RuntimeJumpClip` supplies direction and post-jump state, while its parent
  Runtime Jump Track clip supplies the source `optionIndex`, start, duration,
  and asset PPtr.

This closes the former inferred-adjacent-reply ambiguity. In the pre-fix CN
queue, all 26 `inferredOptionResponse` groups had all-zero candidate trunk
clips and no overlapping raw Runtime Jump route. They are shared Timeline
continuation, not one reply per option. The builder now preserves compact raw
Runtime Jump windows. Missing or malformed jump evidence keeps the warning;
an incomplete overlap remains visible as later-route uncertainty but does not
revive the disproven one-adjacent-line-per-option mapping. Completed Runtime
Jump routes remain higher priority. Audio, speaker consistency, monotonic clip
times, or shared Timeline membership remain corroboration only.

### Option placement boundary

Option-key suffixes and sparse dialog-line gaps are not runtime placement
fields. Authored-control validation found group-number/key matching correct in
only 694 of 2,801 comparable groups, and sparse-gap matching was weaker. The
runtime instead places Timeline options by active clip time and
`TimelineClip.optionIndex`, or follows authored DialogTree connections.

The pre-fix CN layout queue contained 189 inferred groups; 178 of those groups
had no real `DialogIdTable` root. A parser
bug had counted the embedded `dlg_*` substring inside `option_dlg_*` as a fake
dialog line; option-only identifiers now populate option vocabulary without
registering a scene. Unregistered key/gap placements remain useful for static
table browsing, but the WebUI classifies them as table-only display placement
instead of live runtime recovery issues.

Only seven uncovered key-position groups retained a real registry root, all in
`dlg_gm02m2_1..4`. No Timeline, DialogTree, or mission asset survives for those
scenes, so their prompt/answer placements are explicit WebUI-only overrides.
Two key matches were semantically wrong and are corrected manually:

- `dlg_gm02m2_1` g3 moves from `_003` to `_005`;
- `dlg_gm02m2_3` g2 moves from `_002` to `_005`.

The remaining five manual placements happen to match the key fallback, but are
not promoted as a general key-based runtime rule.

### Current Runtime Jump conflict controls

Completed Runtime Jump routes remain higher priority than zero-index shared
continuation. An incomplete overlapping jump is retained on the shared
continuation as unresolved later-route evidence; malformed or missing raw-jump
evidence remains warning-worthy. Audit paths can refer to stale Timeline
folders; only basename-resolved current assets with their parent track clips
count as route evidence.

Useful commands:

```bat
python tools\endfield_source_graph.py option-gaps --conflicts
python tools\endfield_source_graph.py option-route-audit --story dlg_e6m1_10
python scripts\story_recovery\build_timeline_option_flow_audit.py --language CN --only-interesting
python scripts\story_recovery\build_option_response_audio_evidence.py --language CN
```

## Narrative video and FMV placement

Narrative-video identity and Story placement are separate questions. Strong
bindings come from recovered `BeyondFMVPlayableAsset` Timeline objects and
matching source-root PathIDs. Filename similarity alone is not enough.

Current durable rules:

- a Timeline playable can bind an FMV/video stem to a Story key and expose
  clip start/duration;
- canonical PathID joins must preserve `StreamingAssets` versus `Persistent`
  source root;
- manual attach/suppress rules remain WebUI-only evidence;
- a standalone `video_*` row stays standalone until an authoritative Story
  binding exists.

The unresolved follow-up has seven groups. Three have plausible generated
Story targets but no Timeline binding and remain standalone:

- `cs_video_dlg_e1m2_1 -> dlg_e1m2_1`
- `cs_video_e1m3_3 -> dlg_e1m3_3`
- `cs_video_e6m1_1 -> dlg_e6m1_1`

Four have no generated target: `cs_video_dlg_e9m2_3`, `cs_video_e2m8_2`,
`remotecomm_e1m2_2`, and `remotecomm_e1m2_3`.

## `e0m0` calibration and static-data boundary

`e0m0` remains the best control mission for distinguishing membership from
runtime chronology. Strong local facts include:

- `cutscene_e0m0_6 -> cutscene_e0m0_7 -> cutscene_e0m0_8` from the typed
  `indie_dg004/23900030000` scene chain;
- the q#7 `battle_field_clear` terminal branch in `8700040000`, which reaches
  `cutscene_e0m0_New14`, `radio_e0m0_8d8`, and nearby level-sequence actions;
- `text_e0m0_1` as the tombstone reading popup before the related misc-dialog
  sequence;
- `video_cs_video_e0m0_3` as a media mirror Timeline-bound to
  `cutscene_e0m0_3` at start 0 for about 59.75 seconds;
- first/second zipline and selected LevelTimeline marker membership.

The q#11 boss cluster remains the clearest static wall. Script
`indie_dg002/8700050001` proves that its radios and cutscenes belong to one
boss/final-area phase, but action-list order, byte order, local ids, numeric
suffixes, header/getter order, and trigger position do not reproduce runtime
interleaving. Gameplay/server state owns the missing writer sequence.
`radio_e0m0_21` still has no decoded LevelScript trigger.

The archived gameplay-observed order below is a calibration target, not
source-only proof:

```text
cutscene_e0m0_1
cutscene_e0m0_2
radio_e0m0_1
radio_e0m0_1d5
cutscene_e0m0_1stZipline
radio_e0m0_2
radio_e0m0_2d8
cutscene_e0m0_2ndZiplineA
cutscene_e0m0_2ndZiplineB
cutscene_e0m0_2ndZiplineCCamOnly
radio_e0m0_3d2
radio_e0m0_5d6
cutscene_e0m0_13
radio_e0m0_8d4
cutscene_e0m0_New14
radio_e0m0_8d8
radio_e0m0_8d9
cutscene_e0m0_lookingatpatriot
radio_e0m0_9
radio_e0m0_9d5
radio_e0m0_10
cutscene_e0m0_tombstonecollapseCam
radio_e0m0_21
text_e0m0_1
misc_dlg_e0m0_0d5
misc_dlg_e0m0_0d7
misc_dlg_e0m0_0d8
misc_dlg_e0m0_0d9
radio_e0m0_11
radio_e0m0_12
cutscene_e0m0_3
video_cs_video_e0m0_3
radio_e0m0_13
radio_e0m0_14
radio_e0m0_16
radio_e0m0_22
radio_e0m0_23
radio_e0m0_17
radio_e0m0_15
cutscene_e0m0_4
radio_e0m0_20
cutscene_e0m0_5
cutscene_e0m0_6
cutscene_e0m0_7
cutscene_e0m0_8
```

Historical heuristic calibration reduced e0m0 inversions from 22.7% to about
5.1%, but that result mixed observed order with suffix, spatial, and chunk
heuristics. It is useful for finding missing evidence, not as the strict
source-only metric. A separate broad main-story comparison likewise found
31.82% strict inversions and 16.37% coarse-phase inversions against manual
override order; override agreement is not original-game proof.

Gameplay-video OCR/audio matching remains an optional observed-evidence path,
not source-only chronology. The maintained PP-OCRv5 server benchmark on this
machine found frame batches 24-56 materially faster than the old batch 8 and
selected 40 as the stable default (roughly 11.7 fps mean in the repeated
sample). The audit and Story-order scripts expose
`--paddleocr-frame-batch-size`; re-benchmark after model, GPU, or crop changes
instead of treating 40 as universal. OCR proposals stay in
`webui/data/story_order_ocr.json` and never silently overwrite locked manual
orders.

## Source graph and generated audit surface

The source graph is an evidence index, not runtime simulation. The current
canonical relevant-AssetMap CN rebuild contains 2,112,725 nodes, 4,748,203
edges, and 2,285,546 aliases; all 1,140 required original AssetMap identities
matched. Story-recovery queries include:

```bat
python tools\endfield_source_graph.py story dlg_e7m3_3
python tools\endfield_source_graph.py mission-flow e7m3 --limit 40
python tools\endfield_source_graph.py scene-gaps --warning sceneOrderDisorder
python tools\endfield_source_graph.py option-gaps --audit-only
python tools\endfield_source_graph.py option-route-audit --conflicts
python tools\endfield_source_graph.py query "sm2l7m1_q#17"
python tools\endfield_source_graph.py query 23100170008
```

The graph exposes Story/line/option reverse links, MissionRuntime actions and
conditions, quest narrative refs, LevelScript refs and property-flow audits,
scene-order gaps, option conflict evidence, FMV/video bindings, and comparison
reports. It now also exposes three exact quest-to-SubmitItem requirements, two
same-objective dialog co-gates, and one same-objective LevelScript co-gate.
The latter has one exact dialog-exit trigger and one exact playback target;
all 18 new bounded edge payloads retain false submission-UI ownership and
order flags. These links improve explainability; they do not promote
chronology by themselves.

Useful generated report families:

- `reports/mission_order/source_story_partial_order_CN.{json,md}`
- `reports/mission_order/source_story_gap_queue_CN.{json,md}`
- `reports/mission_order/<mission>_evidence_audit.{json,md}`
- `reports/mission_order/levelscript_*`
- `reports/story/build/mission_pipeline_story_binding_coverage_CN.{json,md}`
- `reports/story/recovery/memorypack_union_formatter_tag_audit.{json,md}`
- `reports/scene_order_gap_report_CN.{json,md}`
- `reports/runtime_jump_option_route_audit_CN*.{json,md}`
- `reports/option_response_audio_evidence_CN.{json,md}`
- `reports/narrative_video_override_audit_CN.{json,md}`
- `reports/source_graph/option_branch_gaps.{json,md}`
- `reports/source_graph/unresolved_narrative_video_candidates.{json,md}`
- `reports/mission_graph/mission_dependency_graph.{json,md}`
- `reports/mission_graph/envtalk_attachment.{json,md}`

## The inter-mission dependency graph

The mission-to-mission graph is not serialized as a graph. `*_meta.json`
carries only `missionId`, `acceptMode`, `missionType`, `missionImportance`, and
`rewardId` across all 490 sidecars -- there is no prerequisite field, and
`ChapterMissionChapterTable`/`MissionSelectChapterTable`/`MissionChapterSelectTable`
only map chapter ids onto UI select-chapter names. Mission unlocking is
server-authored.

What the shipped client data *does* state is narrower and exact: a quest
condition in mission A that reads mission B's state, or one of B's quests'
state. `scripts/story_recovery/build_mission_dependency_graph.py` extracts
exactly those, from `CheckMissionState`/`SimpleConditionCheckMissionState`
(`_missionId`) and `CheckQuestState`/`SimpleConditionCheckQuestState`
(`_questId`, whose owner is the literal `<mission>_q#` prefix). Nested
`CombineCondition.subConditions` trees are reached by the ordinary walk.

Current CN corpus: 522 state-condition rows, of which 327 are same-mission
(intra-mission quest flow, already covered by `prevQuestIdList`) and 195 are
cross-mission. Those collapse to **153 edges over 153 missions**. Every target
mission resolves to a real MissionRuntimeAsset; zero dangle.

The operands are never collapsed into one "precedes" relation:

- `requiresCompleted` (141 edges) -- objective waits on `Equal Completed`. This
  is the only class carrying authored precedence.
- `requiresProcessing` (9) -- objective waits on `Equal Processing`. A
  co-active window, not precedence. Eight of the nine declarers are `hidden*`
  missions gated to run *during* a main mission.
- `abortsOnCompleted` (3) -- the reference sits in `failedCondition`, so the
  declaring quest fails when the target completes. Mutual exclusion, the
  opposite of precedence.

The comparer is `Equal` in all 195 rows. Enum numerals are the installed
build's, already pinned above by the native `CheckMissionState` union tag
`0x67` whose decoded predicate reads `e7m4 Equal Completed`: comparer `0` =
`Equal`, state `3` = `Completed`, `2` = `Processing`. Any unrecognized
comparer/state pair is retained as `unclassified` rather than guessed; the
current corpus yields zero such rows.

### Mission-level cycles are a granularity artifact, not a defect

The precedence projection contains exactly one cycle, `db01m1d7 <-> db01m2d5`.
It is not a contradiction. At quest granularity the evidence reads
`db01m2d5_q#8 -> db01m1d7_q#17`, then `db01m1d7_q#18 -> db01m2d5_q#10` and
`db01m1d7_q#19 -> db01m2d5_q#11`: two missions running concurrently and handing
control back twice. Collapsing that onto mission nodes necessarily produces a
cycle that no reordering can remove.

The builder therefore also constructs the quest-granularity graph -- 3,319
nodes over 3,746 intra-mission `prevQuestIdList` edges plus 78 cross-mission
`CheckQuestState Equal Completed` edges -- and confirms it is **acyclic**. A
mission-level cycle is reclassified as an `interleaving` only when that quest
graph is acyclic. If the quest graph were also cyclic the cycle would be
reported under `unexplainedPrecedenceCycles` as a real defect instead. Do not
delete a cycle to make the graph clean; the two outcomes are distinguished by
evidence.

Coverage bound: only missions that happen to gate on another mission's state
appear. **A missing edge is not evidence that two missions are unordered.**

## envTalk: ambient content with exact consumers and no mission owner

`env_*` files sit outside the mission pipeline denominator, which counts only
`black`/`cutscene`/`dlg`/`radio`/`remotecomm`/`sns` (192+257+1,992+2,626+37+169
= 5,273). That exclusion is correct, and it is now measured rather than
assumed.

Identity is exact: `EnvTalkTable` has 1,988 rows and the CN conversation corpus
has exactly 1,988 `env_<envTalkId>.json` files, a verified bijection with zero
leftovers on either side. No filename inference is involved.

`EnvTalkTable` itself is definition-only (text, audio, actor, emoji, duration).
A repository-wide scan for the literal `envTalk` across the entire structured
export returns only 15 files; LevelScriptData contains none, so **no LevelScript
plays an envTalk**. The real consumers are
`NpcProxyTable.dataTable[*].envTalkIds` (plus nested
`lazyDestroyEnvTalkData.envTalkIds`), `NpcProxyExDataTable`,
`AtmosphericNpcClusterDataTable.dataTable[*].envTalkId`, and
`NpcTable[*].envTalkIds`. `scripts/story_recovery/build_envtalk_attachment.py`
reads them by exact field name.

Current primary-consumer split of the 1,988: 57 `questTrackedNpcProxy`, 574
`levelScopedConsumer`, 41 `characterScopedConsumer`, 1,316 `noAuthoredConsumer`.
Atmospheric state context is independent of that primary classification, so a
file can remain level-scoped while gaining a mission/quest availability
context.

The direct navigation path that reaches a quest is one typed join: an objective's
`trackingInfoList[*]` entry of type `NpcProxyTrackingInfo` names an
`npcProxyId`, and that proxy row carries `envTalkIds`. 850 such tracking rows
exist overall; 76 point at envTalk-carrying proxies, covering 57 proxies across
72 quests in 35 missions. The node must declare `$type` itself -- inheriting a
type from an enclosing record is rejected, and a bare proxy-name string
elsewhere in the asset is not a binding. Tightening that gate changed nothing,
which is the point.

**The relation is navigation/configuration context and nothing more.** It means
a quest steers the player toward an NPC that has ambient lines configured on
it. It does not mean the quest plays, owns, starts, or completes those lines,
and it yields no chronology and no server exchange. This mirrors the existing
treatment of typed `EntityTrackingInfo` elsewhere in this note. No mission id
appears on any envTalk-carrying proxy row: all 256 have blank mission fields,
consistent with the earlier NpcProxyEx finding.

### Atmospheric switcher state context

The remaining cluster lead now has an exact, fail-closed join:

`AtmosphericNpcClusterDataTable cluster`
→ complete non-empty `npcIds` set
→ exactly one same-`levelId` active group in
`AtmosphericNpcActiveSwitcherDataTable.groupId2AtmosphericNpcs`
→ the same group's `AtmosphericNpcSwitcherDataTable.groupConfigs` condition.

This is not a proximity or filename match. The cluster's complete NPC set must
be contained by one and only one active group on the same exact level; partial
overlap, cross-level containment, multiple full matches, missing config, and
switcher/config identity mismatch are all rejected. Current data contains 494
cluster rows, 50 with no envTalk id and 444 actual envTalk clusters. All 444
envTalk clusters have one exact active-group match, with zero ambiguous,
partial-only, cross-level, missing, or config-mismatch cases. The active table
has 335 group rows / 333 distinct group ids (nine empty groups and two duplicate
rows); 326 non-empty rows participate in matching.

Of those 444 clusters, 380 carry exact `missionId` / `questId` fields under
their switcher condition; 26 also carry `bindMissionId`. They cover **359
unique envTalk Story files, 52 literal quest references (51 present in
MissionRuntime), and 64 known missions**. The condition tree is preserved as a
dependency rather than collapsed into an ordering rule: combined/reversed
predicates can express
availability windows, exclusion, or co-active state. Three clusters literally
reference absent quest `f1m9d3_q#15` while binding mission `f1m9d4`; the report
keeps that quest unresolved and does not infer an owner from its prefix. There
are no unresolved literal mission ids.

The installed binary establishes what the table fields do. For
`GameAssembly.dll` SHA-256
`0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
and `global-metadata.dat` SHA-256
`90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`,
metadata exposes
`Beyond.Gameplay.Core.AtmosphericNpcSwitcherGroupConfig` with
`switcherId`, `levelId`, `mapId`, `groupId`, `bindMissionId`,
`switcherType`, and `condition`; the active/cluster tables expose the group NPC
map and cluster `envTalkId` / `npcIds`. `AtmosphereNpcMgr` contains
`CheckSwitcherActive` (`0x06013068`, VA `0x187043084`),
`CheckNpcBindMission` (`0x06013069`, VA `0x187042fa8`),
`SetSwitcherActive` (`0x0601306a`, VA `0x183740000`), and
`SetSwitcherDeActive` (`0x0601306b`, VA `0x187043964`).
`_BuildNpcGroupInLevel` (`0x06013066`, VA `0x1833e9ce0`) reads
`ConditionRuntimeBase.GetResult`, registers the group's
`RuntimeGroupData.OnConditionChange`, and maintains active-group state.
`NpcClusterRuntimeInst` separately exposes the cluster's envTalk id and NPC
members while refreshing cluster/NPC visibility.

**This is exact world-state availability context, not playback ownership.**
The condition controls the atmospheric NPC group containing the envTalk
cluster. It does not prove that satisfying the condition plays the line, that
the referenced mission owns it, or that the condition establishes chronology,
completion, or a server exchange. `env_*` therefore remains outside the 5,273
mission Story denominator. Mission Pipeline and the Story trigger manifest
publish these routes with `causality=context`.

The source graph now mirrors the same boundary with 380 explicit atmospheric
state-context nodes and 490 mission-scoped routes. Queries can traverse
mission/quest state -> switcher group -> cluster -> envTalk -> Story, but there
is deliberately no direct mission-to-Story edge. All edges carry
`ownershipStatus=non_owning_context`, `playbackOwnership=false`, and
`orderEvidence=false`, so graph consumers cannot silently promote availability
into playback, ownership, or mission order.

### Five dangling consumer references

Consumer rows name five envTalk ids that `EnvTalkTable` does not define, and
they are reported rather than dropped. `envTalk_c28m3_5/6/7` are absent even
when trimmed. `envTalk_c28m3_4 ` and `envTalk_e11m8_1 ` carry a **trailing
space**; the trimmed `envTalk_e11m8_1` does exist. These are not repaired into
attachments: the runtime does an exact-string lookup, so a whitespace-damaged
id does not resolve in the game either, and silently trimming would invent a
binding the build does not have.

## Node attachment: reaching a mission is not reaching a node

Story binding coverage answers "does this file reach a mission". The pipeline
graph draws *quests*, so the operational question is "does this file reach a
node". `scripts/story_recovery/build_node_attachment_coverage.py` measures the
difference. Current CN corpus:

- 4,461 quest nodes, of which **1,331 (29.8%)** carry at least one Story file;
- **1,705** Story keys reach a quest node;
- **2,363** reach only the mission shell;
- **1,208** reach no mission at all.

The shell-only bucket is therefore twice the fully-unlinked bucket, and it is
the larger real gap. It is dominated by evidence classes that have no quest
granularity to give: 1,703 `leveldata_levelscript_mission_context` rows plus
287 `levelscript_mission_context`, 124 `npc_proxy_ex_mission_context`, and 79
`mission_area_leveldata_mission_context`. Those are asset-host containers and
mission-scoped registries; they identify a mission shell by construction and
cannot select a quest no matter how they are re-read.

Only 178 shell-only rows name a candidate quest at all, 114 name exactly one,
and 59 of those 114 are `pos_tracking_trigger_center_story_context` — spatial
proximity, which the evidence policy keeps diagnostic and never promotes. That
leaves **55 rows over 49 Story files** as the entire realistically-placeable
remainder, and every one carries an explicit self-limiting status
(`same_tracked_npc_is_play3d_emitter_not_quest_trigger`,
`shared_tracked_npc_readiness_context_not_quest_trigger`,
`shared_script_world_entity_tracking_context_not_trigger_gate`,
`same_authored_npc_proxy_segment_not_quest_playback`). Any future placement of
those 49 must be quest-level *context* preserving that status, never playback.

The audit creates no attachment. Do not read "names one candidate quest" as
"attach it"; the main scope selector already promotes genuinely unique quests
(`accepted_unique_parent_quest`), so anything still at shell level was left
there by a path that decided the evidence does not support a node.

### The one new exact lane: quest-objective LevelScript scope

There is a second, independent join that the shell-only rows had not been run
against. Quest objectives already expose `levelScriptIds`, collected from typed
`_scriptId`/`scriptId` operands on the objective's own conditions — exact
original data, not proximity or filename. Cross-joining those against the
shell-only rows' hosting `scriptIds` yields:

- 277 distinct LevelScript ids named by quest objectives, 235 of them unique to
  one quest, and **zero** named by quests in more than one mission;
- **42 shell-only rows over 40 Story files**
  whose hosting script is named by exactly one quest, globally unique and in
  the row's own mission;
- 10 rows rejected as ambiguous.

The relation is quest-level **scope**, not playback: the objective condition
reads the same script that hosts the Story, but it may read a different
property of that script than the one that plays it. This is the same bound the
mission-level `levelscript_condition_scope` rows already carry, refined from
mission to quest by the uniqueness of the script-to-quest mapping.

So the realistically placeable remainder is 40 files by this lane plus at most
49 by the single-candidate lane — under 4% of the 2,363 shell-only files. The
rest are shell-only for structural reasons and no re-reading will move them.

### Closed: conversation-payload cross-references

A complete superset sweep of all connected
`webui/data/lang/CN/conv/*.json` payloads against the prior 1,213-key unlinked
queue returned 107 keys across 110 pairs, and **every one was inadmissible**.
The current 1,208-key queue is a subset after accepted edges moved five files
out, so the negative conclusion still covers it. Of those rows, 102 sit in
`_debug.attachedTo.source.key`, which
`language_bundle.attach_target` builds by pure filename construction
(`f"dlg_{mission}_{scene}"`) for UI grouping; the rest are
`_debug.source.keyCandidates`, `_debug.cutsceneKey`, `_debug.textGroup`, or
derived `relatedScenes`. Using any of them would attach a file on the basis of
the builder's own naming guess. Do not repeat this scan.

Note also that `export_full/.../Data/Json/LevelScriptData/**/*.json` are binary
MemoryPack payloads despite the `.json` extension. A plain-text grep over them
returns zero Story ids and that zero is a measurement artifact, not a finding;
LevelScript Story references must go through the repo's decoder.

## Generic method instantiations and the global event bus

Every earlier direct-call census in this note shared one systematic blind spot:
`tools/endfield-il2cpp/map_body_targets_to_gameassembly.py` names call targets
only from the per-image `Il2CppCodeGenModule.methodPointers` tables, which cover
354,959 entry points. Generic method instantiations live in a different table,
`CodeRegistration.genericMethodPointers` (504,170 slots), and were therefore
reported as unresolved addresses. Any census that concluded "no consumer" while
a generic instantiation sat on the path understated its own coverage.

Naming them requires `Il2CppMetadataRegistration`, which the bridge deliberately
avoided. For the installed July 11 build it is at **`0x18b921c30`**, recovered
from the single `lea rcx, 0x18b9217d0` at `0x180012c19` in the codegen
registration call site (the next `lea` in that block is the metadata pointer).
The candidate validates on shape: `genericMethodTable` 504,620 entries against
504,170 generic method pointers, `fieldOffsets` and `typeDefinitionsSizes` both
63,987, and every table pointer inside `.rdata`/`.data`. A second candidate at
`0x18b921850` decodes to ASCII garbage and is rejected.

Layout for this build: `genericMethodTable` stride is **16** bytes
(`genericMethodIndex`, `methodIndex`, `invokerIndex`, `adjustorThunkIndex`); a
12-byte stride puts 2,000 of 4,000 sampled rows out of range. `methodSpecs`
stride is **12** bytes (`methodDefinitionIndex`, `classIndexIndex`,
`methodIndexIndex`), confirmed exactly by table adjacency: 653,319 x 12 lands 12
bytes below `genericMethodPointers`. Resolving
`genericMethodPointers[slot] -> genericMethodTable -> methodSpecs ->
methodDefinitionIndex` names the open generic definition. This raises the
nameable entry-point count from 354,959 to **500,976**, of which 146,017 are
generic. These addresses are build-pinned exactly like the formatter tables and
must be re-derived after any game update.

This is now maintained rather than ad hoc.
`tools/endfield-il2cpp/map_body_targets_to_gameassembly.py` gained
`DEFAULT_METADATA_REGISTRATION`, `metadata_registration_summary`,
`metadata_registration_is_plausible`, `find_metadata_registration`, and
`build_generic_method_index`, plus the opt-in flags
`--include-generic-instantiations` and `--metadata-registration`. The flag is
**off by default** so every existing report stays byte-identical; enable it
before concluding that a call target has no consumer, and read
`summary.genericInstantiationIndex` to confirm it was active.
`find_metadata_registration` re-derives the address independently and agrees with
the hardcoded default on the July 11 build, so it doubles as the drift check
after a game update. Unit coverage is
`scripts/tests/test_il2cpp_generic_instantiations.py` (synthetic image, no game
files required).

The first use of that capability rewrites what message 125 does.
`MissionSystem.Handle_ClientMissionEvent` (`0x1873bdf58`) reads `missionId` from
`+0x18` and `eventName` from `+0x20` and calls `0x184a428a0`, previously recorded
as an opaque `dispatchTarget` and labelled with the *assumed* consumer surface
`MissionEvent_OnCustomEventForMission`. That address is
**`Beyond.KeyGenerator`2::GetKey`**, which tail-jumps to
**`Beyond.CombineKeyManager::GetKey`** (`0x1846a2e60`) and returns an int; the
handler then passes that int to **`Beyond.EventManager::SendGlobal`**
(`0x187bdfd38`). Message 125 therefore raises a **keyed global event on an
in-process publish/subscribe bus**. It does not reach a serialized
`MissionEvent_OnCustomEventForMission` record, and the earlier "0 consumers"
asset scan was searching the wrong registry rather than proving absence.

`Beyond.EventManager` exposes `BindGlobal`/`UnBindGlobal`,
`SendGlobal` (0 to 5 args), `SendScope`, `ClearByScope`, and
`AddLuaListenGlobal`/`DelLuaListenGlobal` over fields `m_gameEvents`,
`m_eventDispatcher`, `m_luaListeningEvents`, and `s_curScope`. Keys are
`Beyond.CombineKey` values produced by `CombineKeyManager.GetKey` for one, two,
or three parts. **Those keys are runtime-interned, not hashes**: the manager
holds `m_keyHashToKeyInfo`, `m_combineKeyInfos`, and `s_incrementID`, and exposes
`GetStringKey`/`ToString` for in-process reversal only. A CombineKey therefore
**cannot be precomputed offline and searched for as a constant** in
`GameAssembly.dll` or in exported data. Consumers can only be found by naming the
`GetKey` instantiation a listener uses.

Enumerating all seven instantiations of `KeyGenerator`2::GetKey` gives the
complete direct-call producer/consumer map for two-part keys: 35 call sites, all
named. The useful families are

- class instantiation 46436 (four sites): `GameEntityEventUtils::GetKey`,
  `GameScriptEventUtils::GetKey`, and
  **`LevelEventManager::RegisterTriggerFromLevelScript`**;
- class instantiation 4983 (seventeen sites): the global-var family, including
  `SimpleConditionCheckGlobalVar::InnerStartListening`,
  `CheckClientGlobalVar::OnActivate`, `CheckServerGlobalVar::OnActivate`,
  `GlobalVarSystem::Handle_UpdateGameVar`, `GlobalVarSystem::SetClientVar`,
  `MapVarSystem::_Handle_UpdateMapVar`, and `ParamVariableFromMapVar::_InitMapId`;
- class instantiation 5079 (five sites): entity detection conditions;
- class instantiation 1055 (four sites): `MapVarSystem::SetClientMapVar`,
  `MapVarSystem::_Handle_UpdateMapVar`,
  `SimpleConditionCheckMapVar::InnerStartListening`, and
  `MissionSystem::Handle_ClientMissionEvent`.

This independently corroborates the existing static join between
`MissionEvent_OnClientGlobalVarChanged` and its `CheckClientGlobalVar`
consumers: both sides reach the same key namespace through `GlobalVarSystem`.

It also bounds message 125 tightly. Within its own key namespace the only
subscriber-side caller is `SimpleConditionCheckMapVar::InnerStartListening`,
whose serialized form carries `belongMapId` and `mapVarName`, while the handler
writes `missionId` and `eventName`. Sharing an interned key namespace is not a
producer/consumer pairing; even a coincidental mission-id/map-id value match
would not establish the required payload-delegate type. The conclusion in the
recovery queue is unchanged; only its supporting evidence is now correct.

The generic-specialization census now closes the compiled managed typed
consumer question independently of the final call instruction. The exact
publisher body at `0x187bdfd38` is
`EventManager.SendGlobal<Beyond.Gameplay.EventData>`. IL2CPP must retain the
value-type subscriber shape as
`BindGlobal<Beyond.EventData<Beyond.Gameplay.EventData>>` in the AOT method-spec
table even when multiple specializations share one native body or the final
call is indirect. The current table has 653,319 method specs and 504,620 generic
method-table rows, resolving to 137 `SendGlobal` and 51 `BindGlobal`
specializations; the required binding occurs **zero** times. This proves that
the current authored managed client has no typed message-125 subscriber. Native
memory manipulation, runtime reflection, a future IFix payload, and a future
game build remain outside the bound. Reproduce with
`build_protocol_registry_audit.py`; the generated evidence and exact binary
hash are in `protocol_registry_audit.{json,md}`.

The Lua subscription bridge is now closed with the right query. Earlier Lua scans
searched for Story and script *ids*; `AddLuaListenGlobal(eventName)` subscribes by
**name**, so the correct query is the subscription vocabulary. In the recovered
1,290-file VFS dump, `CS.Beyond.EventManager.AddLuaListenGlobal` is referenced by
exactly two files, `Common/Core/MessageManager.lua` and
`UI/RedDot/RedDotManager.lua`. `MessageManager:Register(msg, action)` takes a
numeric `msg` and subscribes `MessageConst.getMsgName(msg)`, so the entire Lua
subscription vocabulary is `Const/MessageConst.lua`: 1,699 names such as
`SHOW_RADIO`, `ON_RADIO_FINISH`, `ON_PLAY_CUTSCENE`, `ON_FINISH_CUTSCENE`,
`ON_MISSION_STATE_CHANGE`, and `ON_QUEST_OBJECTIVE_UPDATE`. It contains **zero**
Story-id-shaped tokens, **zero** mission-id-shaped tokens, and **zero**
LevelScript numeric ids.

That bounds the event **vocabulary** only, and it must not be read as bounding
the Lua layer. Lua handlers subscribed to those names go on to read authored
tables and call native playback with concrete Story ids; see the Lua playback
lane section below.

### Native LevelScript event producers

Naming generic instantiations also makes `Beyond.Gameplay.Core.LevelEventManager`
readable, and that resolves a question this note had recorded as an unanswered
negative. Earlier custom-event producer scans looked for **serialized**
`RaiseCustom*Event` records and found only the `TigerStart` same-script route.
The real producers are native. A direct-call census names 26 callers of
`LevelEventManager::RaiseScriptEvent`, 36 of `_RaiseEntityEvent`, and two of
`_RaiseScriptEvent`. Key families on the script side:

- the serialized action itself, `Beyond.Gameplay.Actions.RaiseCustomScriptEvent::Execute`
  (six sites), which confirms the authored route rather than replacing it;
- `LevelScriptRuntime` lifecycle: `UpdateScriptStarted`, `OnScriptIsDoneChanged`,
  `OnScriptStageChanged`, `UpdateRuntimeState`, `UpdateTaskState`,
  `UpdateTaskMainObjectiveIsCompleted`, `ScriptTaskRuntime::Reset`, and `Tick`;
- `TriggerVolumeManager::_RaiseScriptEvent` (three sites);
- `ParamVariable::_RaiseOnPropertyChangedEvent` and
  `_RaiseOnBBVariableChangedEvent`, i.e. the property/blackboard-write to
  script-event bridge;
- `WorldInfo::OnEntityDie`, i.e. the entity-death to script-event bridge;
- `CharacterScriptedSystem::_StartScriptedChar`, `EncounterBase`1::_PlayOpera`,
  and `GameLevelLoader+LoadingPipeline+LoadFinishStep::DoExecute`;
- **`GameplayNetwork::_Handle_SceneTriggerClientLevelScriptEvent`**.

That last one is the architecturally important route. Message 57
`SC_SCENE_TRIGGER_CLIENT_LEVEL_SCRIPT_EVENT` carries `sceneNumId`, `scriptId`,
`eventName`, and `ctxToken`, and its handler calls `RaiseScriptEvent` directly.
The server can therefore fire **any** LevelScript event by scene, script, and
event name. This is the concrete shape of the server-authoritative activation
surface named as the highest-value binary target, and it upgrades message 57
from `native_handler_proven_elsewhere` to a decoded route into the LevelScript
event system.

The token lane is now decoded end to end as well. The handler stores non-empty
`ctxToken` bytes under the static ParamBlackboard key slot `0x18e2eef08`. A
whole-GameAssembly direct RIP-reference scan finds four references to that slot
in exactly two methods: the handler's initialization/write pair and
`Beyond.Gameplay.Actions.CallServer::Execute` at `0x1845f6000`.
`CallServer::Execute` calls the generic-shared
`ParamBlackboard::TryGetValue` body at `0x1836eb730`, names the result
`netToken` in the typed method chain, and passes it through
`GameAction::TriggerServerEvent` (`0x1845f6640`) and
`GameplayNetwork::TriggerLevelScriptServerEvent` (`0x1845f6710`) to
`CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER::set_CtxToken` (`0x1865a3aac`).
The current installed 30-target Gameplay IFix payload replaces none of those
fallback methods. Message 57's token is therefore a LevelScript server-event
round-trip/correlation value, not a hidden mission or quest carrier.

The complete protobuf carrier census now closes the remaining typed message
surface for this build. Using the MetadataRegistration runtime type table
rather than unresolved metadata placeholders, recursive traversal covers all
983 enum-backed CS/SC message classes and their nested `Proto.*` fields. It
finds 33 mission/quest-bearing message types, 29 `scriptId`-bearing types, and
zero message that carries mission/quest identity beside a LevelScript or Story
identity. A weaker mission/scene pass produces exactly three rows:
`CS_MISSION_CLIENT_TRIGGER_DONE` (317), whose fallback sender is inactive, and
`SC_MISSION_STATE_UPDATE` (112) / `SC_QUEST_STATE_UPDATE` (111), where
`roleBaseInfo.sceneName` is nested beside the mission or quest id.

The two active weak rows are not authored scene ownership.
`Handle_MissionStateUpdate` (`0x1873be300`) and
`Handle_QuestStateUpdate` (`0x1873bf0a0`) read the role snapshot's leader
position, rotation, and scene name and pass them to
`MissionSystem.CharacterPositionCorrection` (`0x1873b84c4`). That method
resolves the scene to a map, checks the current player/controller level and
network-position guards, and may teleport the squad to reconcile server state.
It does not retain the scene as a mission/quest host or address a LevelScript
or Story file. The installed IFix targets none of the two handlers or the
consumer. This adds zero ownership or order edges. Opaque bytes, dynamic
parameter values, server-only schemas, native construction, future IFix, and
future builds remain outside the bound.

### MissionOptionData is an alternate-action carrier, not a dialog bridge

The next exact non-protobuf candidate is now closed. Managed metadata gives
`Beyond.Gameplay.MissionOptionData : DialogTreeOptionBase` two direct string
fields: `missionId` at runtime offset `+0x68` and `callDialogId` at `+0x70`.
`get_optionHandlerType` returns enum value 3 (`Mission`). Its only exact typed
consumer is `MissionOptionHandler._DoAction` (token `0x0600fa1a`, address
`0x186e510a4`, IFix id `0xc337`).

The native control flow rejects the tempting co-carrier join. `_DoAction`
checks `callDialogId` first. A non-empty value calls
`DialogManager.StopAndPlayDialogById` and then jumps to the method end. Only
the empty-dialog branch tests `missionId` and calls
`MissionSystem.AcceptMission`. The two fields are therefore mutually exclusive
action alternatives in the current fallback, not a mission-to-dialog causal
edge. They cannot establish Story ownership or order even if a future record
contains both values.

The current authored-data census is also empty: zero exact instances across
1,325,026 exported MonoBehaviour index rows (3,240,614,105 bytes), 8,195
decoded TextAsset scripts (687,580,854 bytes), 179,925 structured JsonData
files, and 1,291 installed VFS Lua files (20,161,714 bytes). A complete direct
`E8 rel32` census finds no caller of the constructor or handler-type getter;
the only two `_DoAction` callers are the expected option-end and dialog-end
callbacks. The installed 30-target IFix replaces none of the audited methods.
The rerunnable evidence is
`reports/story/recovery/mission_option_carrier_audit.{json,md}`.

This adds zero graph edges and closes `MissionOptionData` for the current
binary/export. Reflection, dynamically constructed names, server-only
construction, unexported object kinds, future IFix, and future builds remain
outside the bound.

### Mission properties do not acquire mission-to-LevelScript identity

The next nested managed-type candidate is also closed.
`MissionRuntimeAsset` carries `missionId` at `+0x10`, serialized
`List<ParamKeyValue> properties` at `+0xe0`, and a separate runtime
`Dictionary<string, ParamVariable> propertyDic` at `+0xf8`.
`MissionSystem.MissionData` instead carries its synchronized
`propertyDict` at `+0x20`. `ParamVariable` contains `m_sendToScript` at
`+0x68` and `m_scriptPtr` at `+0x70`, but that shared value container does not
make every dictionary which stores it a LevelScript relation.

The current authored MissionRuntime corpus has 490 files. Seventy missions
serialize 214 property rows with 186 unique keys. Their complete nested field
shape is only `key/value/type/valueArray/valueBit64/valueString`; no row has a
`LevelScriptPtr`, `scriptId`, `propertyDic`, or `propertyDict` field.
`MissionRuntimeAsset::.ctor` allocates an empty `propertyDic` separately and
does not populate it from `properties`.

All three native mission synchronization paths have the same distinct
semantics. `Handle_SyncAllMission` (`0x1833784e0`, `ToVariable` at `+0x2044`),
`Handle_UpdateMissionProperty` (`0x1873c02e4`, `+0x2c8`), and
`Handle_MissionStateUpdate` (`0x1873be300`, `+0x416`) convert
`Proto.DYNAMIC_PARAMETER` values with
`ParamVariableExtensions.ToVariable` and write `MissionData.propertyDict`.
None calls either LevelScript setter. A whole-GameAssembly direct-call census
instead resolves `SetupOnPropertyChangedEventForLevelScript` only to
`LevelEventManager`/`ScriptEvent.OnPropertyChanged` registration and resolves
the managed `SetupOnBBVariableChangedEventForLevelScript` caller to
`ScriptEvent.OnBBVariableChanged` registration. One additional BB callsite is
native/generic and unmapped, but its local call shape carries a script pointer
and key with no mission identity. Current IFix replaces none of the reviewed
paths.

The hash-pinned rerunnable evidence is
`reports/story/recovery/mission_property_scriptptr_audit.{json,md}`. It adds
zero mission graph edges and classifies the apparent nested join as
`runtime_context_only_no_mission_levelscript_edge`. Indirect/delegate or
reflection construction, unexported data, future IFix, and future builds remain
outside the bounded result.

### Implicit current-mission action parameters do not bridge LevelScript

The action parameter system exposes a real implicit identity source that field
co-carrier scans would otherwise miss. Installed metadata assigns
`ParamSource.CURRENT_MISSION_ID=1004`; `Param<T>` stores `paramSource` and an
action context and exposes `get_isCurrentMissionId`. This made a
LevelScript Story action inheriting mission identity from its execution context
a plausible candidate even when no literal `missionId` field was serialized.

The complete authored census closes that route. All 490 current
MissionRuntime assets contain 18 `paramSource=1004` occurrences across six
missions, and every one is the `_missionId` input of a self-mission property
condition: 17 `CheckMissionIntProperty` rows and one
`CheckMissionBoolProperty` row. None is a Story playback operand. Across all
4,512 raw LevelScript files and 74,839 decoded UID records, the little-endian
value 1004 occurs zero times; validated Param tails and embedded JSON parameter
blobs likewise contain zero current-mission sources.

This proves the implicit context feature exists but is not used as a current
mission-to-LevelScript or mission-to-Story carrier. In MissionRuntime, the
mission owner is already explicit; in LevelScript, the authored source is
absent. The installed 30-target Gameplay IFix replaces none of the reviewed
ActionContext/Param/MissionRuntime paths. The fail-closed report is
`reports/story/recovery/param_source_mission_context_audit.{json,md}` and its
classification is
`implicit_context_only_missionruntime_no_levelscript_story_edge`. Server-only
action graphs, opaque runtime-created Params, reflection/XLua construction,
future IFix, and future builds remain outside the bound.

### The direct managed identity-carrier surface is exhausted

A metadata-wide exact-field census now closes the complete direct managed
carrier class rather than leaving individual type names as an implicit queue.
Across all 63,987 current managed types, ten types place a mission/quest
identity beside a LevelScript/scene identity or Story playback identity. Two
are not value carriers at all (`IdPickerAttribute.StringIdType` is an editor
enum and `PropertyKeys` is a static key catalog); the other eight are all
reviewed.

Three productive pairs were already admitted by their proper bounded evidence
classes: 13 FocusMode mission/radio rows (ten unique radios), 453
NpcProxyEx mission/dialog rows, and 20 SubGame mission/bound-script rows.
They remain mission-shell context or runtime-shell evidence, not generic quest
activation or Story chronology. `MissionOptionData`, `TeleportParam`, and the
inactive `CS_MISSION_CLIENT_TRIGGER_DONE` mission/scene packet are already
closed separately.

The last unreviewed-looking pair was tracking data. Native
`CommonTrackingSystem.AddMissionTrack` (`0x184792ac0`) writes the supplied
mission id into `CommonTrackingPointInfoBase+0x20` and allocates a tracking
key. `CommonTrackingPointInfoBase._UpdateVisible` (`0x183482bb0`) reads
`sceneId` at `+0x30`, maps it through
`GameUtil.GetSystemMapIdByLevelId`, and compares it with the current level's
system map. `TrackingInfoBase.ActivateTrackUnit` and `DeactivateTrackUnit`
only add/remove that HUD/map tracker. None of these methods calls Story
playback, and the installed IFix replaces none of them.

The maintained fail-closed result is
`reports/story/recovery/managed_identity_carrier_census.{json,md}` with
classification `all_direct_managed_identity_carriers_reviewed`. It adds zero
Story bindings or order edges. Nested object graphs, reflection/XLua,
indirect construction, opaque server-only state, unexported asset kinds,
future IFix, and future builds remain outside this direct-field bound.

### The typed nested managed-carrier surface is exhausted to depth three

The remaining managed-type frontier is now bounded with the installed
MetadataRegistration runtime type table rather than the stale local DummyDll
set. Generic collection arguments and custom object fields are followed to
three hops across 63,987 metadata type records / 63,208 unique definitions and
272,743 runtime type entries. The exact result is 25 candidate root types:
11 already co-carry the relevant identity classes directly, 14 require at
least one nested path, all 25 are reviewed, and none remains unclassified.

The productive rows are not new graph evidence. They are the already recovered
AirWall, FocusMode, NpcProxy, SubGame, DomainDepot, and
`RadioTriggerZoneData` contexts. The other paths reduce to previously closed
mission properties/task callbacks, global aggregate managers such as
DataManager/LevelScriptData/MissionSystem, or static registries and key
catalogs. Holding two independently useful subsystem containers on a singleton
does not make their contents foreign keys.

The one newly traced candidate is
`DialogManager.m_pendingItemSubmitter (+0x200) ->
InventoryItemSubmitter.questId (+0x20)`. `DialogManager._SendServer` can pass
the current dialog id and that object to
`CinematicSystem.SendFinishDialog`; `InventoryItemSubmitter.TryGetSubmitMsg`
then supplies the item-submission fields. A whole-GameAssembly direct-call
census still finds zero native `E8` callers of both
`InventoryItemSubmitter..ctor` (`0x1873b0234`) and
`DialogManager.RegisterPendingSubmission` (`0x186e17bc8`), while
`SendFinishDialog` is the only native `TryGetSubmitMsg` caller and current IFix
replaces none of the path. Those counts describe only the AOT native call
surface: the shipped
`Data/LuaScripts/UI/Panels/SubmitItem/SubmitItemCtrl.lua` constructs the
seven-field submitter through XLua and calls `RegisterPendingSubmission` when
submission came from a playing dialog and is not configured for immediate
server submission. `DialogOpenUIPanel` has two native direct callers:
`DialogManager.OpenUI` and its generated XLua wrapper. The earlier inactive-
producer conclusion was therefore wrong.

This active bridge still does not recover a quest-to-dialog edge. The typed
DialogTree census contains 95 terminal `DialogOpenUIAction` rows, including 13
with `panelType=9` matching SubmitItem. Three carry the exact
`DIALOG_OPEN_UI_PARAM_SUBMITITEM` stock placeholder JSON, ten have empty
params, and zero exports a concrete `questId`. The current fallback does not
fill that gap: `DialogTreeOpenUINode.DoAction` passes the original action to
`DialogManager.OpenUI`, `GameAction.DialogOpenUIPanel` forwards its `param`
string and original action object, and hash-pinned shipped
`Data/LuaScripts/Phase/Dialog/PhaseDialog.lua` only JSON-decodes the string and
adds `fromDialog` plus `actionData`. It performs no mission/quest lookup or
submission-identity substitution.

MissionRuntime does supply a separate exact quest-to-submission relation.
There are exactly three `CheckQuestSubmitItem` objectives:
`sm1l1m5_q#4 -> submit_sm1l1m5_phone`,
`sm1l6m3_q#3 -> submit_item_e2m6_2`, and
`sm2l7m1_q#17 -> submit_item_sm2l7m1`. All three resolve in `SubmitItem.json`
to exact item/count alternatives. The first two share an authored
`CombineCondition "{0} and {1}"` with a `CheckTalkOptionFinish`; these are
bounded same-objective co-gates, not playback ownership. Their dialog ids have
zero overlap with the 13 typed SubmitItem OpenUI dialogs, while the third
submission is co-gated by a LevelScript-stage condition instead. The recovered
graph can therefore show quest -> submission requirement and the two dialog
co-gates, but must not add a quest -> OpenUI or order edge.

The maintained fail-closed evidence is
`reports/story/recovery/nested_managed_identity_carrier_census.{json,md}` with
classification `all_nested_managed_identity_carriers_reviewed`. It adds zero
Story bindings and zero order edges. The exact shipped SubmitItem XLua
producer, fallback parameter pass-through, and authored submission-objective
census are now inside the bound. Dynamic mutation or reflection outside that
path, native-only opaque objects, server-only state, paths deeper than three
custom type hops, unexported asset kinds, future IFix, and future builds remain
outside it.

### AirWall state gates recover exact non-owning radio contexts

A broader exact runtime-type census found one productive non-protobuf carrier:
`Beyond.Gameplay.AirWallManager`. `LevelData.airWalls` is member 0 of the
current 43-member MemoryPack object. Its typed `AirWallGroup` rows co-carry
`pushBackRadioId` with `AirWallCheckData -> MissionTotalCheckData ->
MissionCheckData`, including the exact state id, mission-versus-quest flag,
detail state, equality mode, and rise/down any/all combination. Generated
`ForMemoryPack` setters prove the alphabetical eight-member group order:
`bounds`, `checkData`, `defaultOn`, `groupId`, `polyLineWalls`,
`pushBackRadioId`, `scriptId`, and `slotId`.

The guarded decoder consumes all 958 LevelData payloads: 228 files contain 822
AirWall groups with zero parse failures. Of those, 211 are mission checked, 78
carry a radio, and 60 carry both. Exact Story and MissionRuntime/quest joins
retain 58 contexts covering 20 radios and 30 missions, producing 61
record-level mission attachment rows (60 unique mission/radio placements).
Two `e7m3` rows are rejected as authored type inconsistencies because
`e7m3_q#24` or `e7m3_q#18` is marked `isQuest=false`; the builder fails the
whole mixed predicate group closed rather than correcting it from the string.
Reused radio names are attached to the checked mission/quest identities, not
to the Story filename's apparent owner.

The installed native chain establishes the semantics. `_InitMissionListener`
binds mission and quest state events; `_OnMissionStateChanged` and
`_OnQuestStateChanged` route cared identifiers to `AirWallGroupAgent`, whose
state handlers re-evaluate the authored checks. `TriggerMainCharGoBack` reads
the group's pushback radio, and its callback at `0x186f4ecc0` calls
`GameAction.PlayRadio`. Thus synchronized mission/quest state controls whether
the wall is active, while later local player contact causes playback. This is
an exact state-gated playback dependency/context, not playback on the state
transition, quest activation/completion, Story ownership, or mission order.
The current 30-target Gameplay IFix replaces no AirWall method.

It does **not** close the join. Message 57 carries scene/script identity and no
mission or quest identity, exactly mirroring the task packet family. The two
death/property bridges are likewise capability proofs at the architecture level,
not per-Story-file bindings: they show how a gameplay write reaches a script
event, not which authored record fires which Story key. Nothing here promotes a
Story attachment or an order edge. The census is also direct-call only and does
not cover vtable, delegate, IFix, or XLua dispatch.

The practical consequence for the queue is narrower than it looks. These
producers are shared runtime infrastructure reached by every script, so they
cannot select a mission for an unlinked Story file. They do retroactively
explain the recorded negatives: a scan restricted to serialized producer records
could not have found any of them.

### Re-running a blind census, and the Encounter phase machine

Re-running the radio playback census with generic naming demonstrates the blind
spot was real rather than theoretical. `GameAction::PlayRadio` and
`GameAction::PlayRadioAndWait` take 27 direct calls from XLua wrappers, NPC
patrol controllers, air-wall/balloon/focus/narrative components, the
`RadioTriggerZoneHandler`, the serialized `PlayRadio`/`PlayRadioAndWait` actions
and one caller no earlier census could name:
**`Beyond.Gameplay.Core.EncounterBase`1::DealBattlePartDelayGap`**, a generic
instantiation. The same type's `_PlayOpera` is one of the 26
`RaiseScriptEvent` callers. The cutscene census is regenerated below and yields
the BattlerStage result. Treat the older 38-call radio and 33-call cutscene
figures as superseded.

Two caveats on the census itself. Enclosing-method attribution is by
nearest-preceding entry point, so a call inside a method that is in neither
pointer table is attributed to a distant neighbour; rows with implausible
deltas, such as `Task::NotifyDebuggerOfWaitCompletion +0x24ffd8`, are
attribution failures and must not be read as real callers. And the census
remains direct-call only.

`EncounterBase`1` is worth recording in its own right, because it is a second
**client-side deterministic ordering system** of the shape Project C hoped
`BattlerStageActions` would be. Its runtime metadata exposes an explicit ordered
phase model: `EncounterProgress` runs
`None -> Enabled -> IntroPart -> BattlePart -> TailPart -> Completed/Failed`,
with `currentIntroPart`, `currentBattlePart`, `currentTailPart`, `operaIndex`,
`currentTiming`/`nextTiming`, `isInBlackScreen`, `airWallIsShown`, and
`enemyIsShown`. It raises paired begin/end events per part, keys them with
`EVENT_KEY_ACTIVATE`, `EVENT_KEY_START_BATTLE_PART`, `EVENT_KEY_FAIL`,
`EVENT_KEY_PASS_FIRST_INTRO`, and `EVENT_KEY_TELEPORT`, persists
`SAVE_KEY_PASS_FIRST_INTRO`/`SAVE_KEY_BATTLE_COMPLETED`, and sequences
performances by `OperaSignalTriggerMode` (`OnOperaEnd` or
`OnBattlePartDelayGapFinish`). Its `DealBattlePartDelayGap` display class carries
a concrete `radioId`. `EncounterSurvival` adds narrative handles, a kill-enemy
event enum, and ordered tail-part clear timings.

That is a genuinely ordered radio/opera sequence source for encounter content.
It is nevertheless **not currently usable**, for the same reason
`BattlerStageActions` was not: the authored configuration is absent from the
export. `Data/Json` contains no encounter records; the only `Encounter` strings
in `export_full/structured` are the quest ids `c31m1d5_q#Encounter` and
`c31m3d5_q#Encounter`, and the only matching asset filenames are the
`levelseq_e2m7_eliteencounter_*` Timeline assets, whose name is a coincidence.
Record `EncounterBase` as a known ordering system whose data would have to be
recovered from binary scene assets through the IL2CPP field layout, exactly like
`BattlerStageActions`, and do not treat the type's existence as evidence for any
current Story order.

### BattlerStage is live in the binary and unused in the data

Regenerating the cutscene census resolves the long-open `BattlerStageActions`
question. `GameAction::PlayCutscene` and `PlayCutsceneAndGetHandle` take 27
direct calls, and two are the interesting ones:
**`Beyond.Gameplay.Core.BattlerStageActions.PlayCutscene::OnBegin`** and the
generic `EncounterBase`1::_PlayOpera`. So the BattlerStage system is not
vestigial: it is wired to cutscene playback in the installed build.

The type shape is fully recovered and is a clean ordered action list.
`Beyond.Gameplay.BattlerStageData` has four fields, `uid`, `type`,
`isCheckpoint`, and `parameters`, and **does have a MemoryPack formatter**
(`Beyond_Gameplay_BattlerStageDataForMemoryPack`), which corrects the earlier
assumption that no formatter existed. `BattlerStageEnum` enumerates
`DoNothing`, `BlackScreenFadeIn`, `BlackScreenFadeOut`, `PlayFmv`,
`PlayCutscene`, `SpawnEnemy`, `Teleport`, `CheckEnemyKilled`, `WaitForSeconds`,
`AdjustCamera`, `ToggleAirWall`, and `Checkpoint`. The action classes carry
`stageIndex`, `checkpointPropertyKey`, and `StepToNextStage` on the base, and the
per-type configuration (`PlayCutscene.cutsceneId`, `PlayFmv.moviePath`,
`Checkpoint.eventKey`, `WaitForSeconds.duration`) is exposed as getters reading
`stageData.parameters` rather than as backing fields.

There is even a LevelScript hook. `LevelEvent_OnBattlerStageChanged` is a real
ActionHeader union member at tag **`0x004B`**, registered by the same cctor
(`0x1843bb480`) through the same helper (`0x183ead480`) as every other header,
and `scripts/story_builder/levelscript_binary.py` already names it.

**But nothing in the shipped data uses it.** The corpus-wide opcode census over
3,691 LevelScript files, 75,099 records, and 13,188 `headerList` records
contains three shapes whose compact tag is `0x4b`, and **all three sit in
`actionList` or `getterList` roles, none in `headerList`**. Under this note's
own rule that header names apply only after `headerList` membership is proved,
`LevelEvent_OnBattlerStageChanged` therefore has **zero serialized occurrences**.
`BattlerStageData` likewise has no authored file anywhere in `export_full`.

This retires the Project C follow-up that recommended decoding
`BattlerStageActions` from binary scene assets as a boss-cutscene order source.
Even a successful decode could not bind to Story through the LevelScript lane,
because no script listens for stage changes; its only Story reach is
`PlayCutscene::OnBegin -> GameAction::PlayCutscene` with a `cutsceneId` read from
authored `stageData.parameters` that the export does not contain. Treat
BattlerStage as **present in code, absent from data** and do not reopen it unless
a future build ships the authored records or a header with tag `0x4b` appears in
a `headerList`.

### The two native lanes, re-scanned in both directions

The "no bridge between the two native lanes" negative was recorded from a scan
that could not name generic instantiations. It is now re-run with naming on, in
both directions, over a whole-binary sweep of **1,662,080 resolved direct calls**.
Attribution rejects any call site further than `0x8000` from its enclosing entry
point, which discards the nearest-preceding misattributions described above (40
and 255 rejected rows respectively).

LevelScript lane to `MissionSystem`: **18 edges**, and every one is a read or a
panel push. The condition and getter actions
`CheckMissionOrQuestIsComplete`, `CheckMissionOrQuestIsProcessing`,
`GameAction+Mission::CheckMissionQuestId`, `CheckMissionQuestIdComplete`,
`GetMissionState`, `GetQuestState`, `GetMissionSucceedId`, and
`GetMissionSaveProperty{Bool,Float,Int}` call `GetMissionData`, `GetQuestData`,
`GetQuestState`, or `TryGetSaveProperty`; `ShowChapterCompletedPanel` and
`ShowChapterPanelWaitForFinish` call `PushChapterStart`/`PushChapterFinish`.
`LevelScriptRuntime` and `LevelEventManager` themselves call `MissionSystem`
**zero** times. Three of the 18 edges go through the generic
`TryGetSaveProperty`, so they were among the rows the older scan could not name.

`MissionSystem` to the LevelScript lane: **eight edges**. `CompleteMission`,
`DeleteMission`, `FailMission`, `Handle_QuestStateUpdate`,
`Handle_SetQuestEnable`, and `RaiseMissionStateChangeEvent` all call
`LevelEventManager::RaiseLevelEvent`; `PrepareMissionAsset` calls
`ActionMapAsset::Init` and `get_runtimeContext`.

The negative is therefore **confirmed and strengthened, not overturned**. The two
lanes couple in exactly two ways, and neither is an ownership declaration:
LevelScript *reads* mission state through typed getters, and MissionSystem
*broadcasts* a level event on state change. The broadcast direction is already
the decoded and exploited `LevelEvent_OnQuestStateChanged` family (199 occurrences
in the header census), so it adds no new attachment. Nothing in either direction
registers a script, scene, or Story key against a mission or quest.

### The Lua playback lane

Chasing indirect dispatch found a Story playback lane this note had not modelled.
Lua does not only consume presentation notifications: shipped Lua controllers
call the native playback entry points directly through the XLua wrappers, with
Story ids that are either hardcoded in the script or read from an authored table.
`Init.lua` binds `GameAction = CS.Beyond.Gameplay.Actions.GameAction`, and four
files reference `CS.Beyond.Gameplay.Actions` directly.

Three current call sites carry concrete Story ids, and **all three name Story
keys that the gap queue currently lists as `actionableCoreIsolatedSceneKeys`**:

- `Phase/GenderChange/PhaseGenderChange.lua` holds
  `CUT_SCENE_ID = "cutscene_e1m10_1"` and calls
  `GameAction.PlayCutscene(CUT_SCENE_ID, ...)`. The id is an **exact-case match**
  for the registry entry, so this is a clean authored playback binding for
  `cutscene_e1m10_1`, owned by the gender-change phase.
- `Phase/GenderSelect/PhaseGenderSelect.lua` holds
  `EnterCutsceneId = "Cutscene_e0m0_1"` and calls
  `GameAction.PlayCutsceneAndGetHandle(EnterCutsceneId, ...)`. This route is now
  **binary-proven invalid for the current build**, not merely unproven.
  `GameAction.PlayCutsceneAndGetHandle` passes the spelling unchanged through
  `CutsceneManager.PlayCutscene`; `CheckCanPlay` calls
  `NarrativeUtils.GetGenderedCutsceneId` and then
  `CinematicTimelineManagerBase.TryGetCinematicData`. The gender helper either
  tries a gender-prefixed candidate or returns the original string; it performs
  no case fold. `_TryLoadCutsceneDataByName` embeds that result in the resource
  path, `CachedPathAssetLoader.TryLoad` converts the path directly through
  `StringPathHash(string)`, and the reviewed hash path consumes the original
  string bytes without lowercasing. The current 30-target Gameplay IFix replaces
  none of these methods. Therefore `Cutscene_e0m0_1` does not prove playback of
  lowercase `cutscene_e0m0_1`; keep it rejected. Reproduce with
  `build_cutscene_case_resolution_audit.py`, whose build-fingerprint guard
  writes `reports/story/recovery/cutscene_case_resolution_audit.{json,md}`.
- `UI/Panels/ActivitySkipChapter1Confirm/ActivitySkipChapter1ConfirmCtrl.lua`
  subscribes `MessageConst.ON_SKIP_CHAPTER_SUCCESS` to `_OnSkipChapterSuccess`,
  which reads `Tables.skipChapterTable:TryGetValue(skipChapterConfigId)`, takes
  `bindDlgId`, calls `PhaseManager:ExitPhaseFastTo(PhaseId.Level, true)`, and
  then `GameAction.StartDialog(bindDlgId)`.

`SkipChapterTable` itself is **not** a new find: its single row, the
`missionId=e5m1`/`bindDlgId=dlg_e5m0d5_1` pairing, and the
`CS_DO_SKIP_CHAPTER`/`SC_DO_SKIP_CHAPTER` exchange are already recorded earlier
in this note, which correctly stops the relation at mission-shell context. What
the Lua lane adds is the missing **client playback consumer** that completes that
route: the server response surfaces as `ON_SKIP_CHAPTER_SUCCESS`, and the confirm
controller is what actually calls `GameAction.StartDialog(bindDlgId)`.

Apply the usual discipline to the adjacent mission id. The handler reads **only**
`bindDlgId`; it never reads `missionId` and never calls `MissionSystem`. This is
the same shape as the documented NpcProxy case, where an adjacent `missionId` is
consumed by a different guard. The existing mission-shell-context classification
is unchanged, and the dialog's own name references `e5m0d5`, a different mission
from the `e5m1` skip destination.

The general lesson is a coverage one. Story playback owners are not confined to
LevelScript and MissionRuntime: a shipped Lua controller reached through the
global event bus is also a playback owner, and its Story id may live in a small
authored table that no current audit reads.

**Shipped in the Mission Pipeline and Storyline frontends.** The Lua corpus is
not on the export path, so the recovered call sites are pinned in
`build_mission_pipeline_data.py` as `LUA_STORY_PLAYBACK_CALL_SITES`, with exact
provenance (Lua file, symbol, Lua call, native entry), the same way recovered
native tags and RVAs are. They emit a `lua_controller_playback` trigger route
with `causality=playback_owner_unresolved`, `ownerStatus=unresolved`, and
`questTriggerStatus=no_mission_or_quest_identity_serialized`. `cutscene_e1m10_1`
therefore moves from **zero** trigger routes to an exact playback trigger; it
stays owner-unresolved because the gender-change phase serializes no mission or
quest identity. `cutscene_e0m0_1` is deliberately **not** pinned, so it still
displays "no playback trigger recovered" — the capitalised Lua literal is now
known to fail the current case-sensitive native resource lookup. Mission
Pipeline now publishes that failed literal under
`storyTriggerManifest.cutscene_e0m0_1.rejectedPlaybackCandidates`; with
`Show debug info` enabled, the unassigned Story card renders it as a
binary-proven rejected candidate. Its `routes` array remains empty,
`attachmentStatus` remains `unlinked_no_trigger_route`, and the rejection does
not change graph, ownership, or trigger counts.

The manifest's `attachmentStatus` is now route-aware, but only for **playback**
causality. An intermediate version promoted any row with a route, which
silently relabelled five condition/dependency rows as
`trigger_known_owner_unresolved`; that violates this note's rule that condition,
context, dependency, definition-only, and missing-route rows are never relabelled
as playback triggers. The gate is now `causality.startswith("playback")`, moving
exactly one row (153 -> 154 trigger-known, 1,002 -> 1,001 no-route).

The systematic Lua playback pass is now complete for the current 1,290-module
corpus. `build_lua_consumer_reference_audit.py` enumerates all 72 direct
`GameAction.*` calls across 36 methods and classifies the bounded Story playback
surface: ten calls in four modules. Seven are generic handle dispatch in
`CinematicSystem.lua`; one is the already-pinned exact-case
`cutscene_e1m10_1`; one is the binary-rejected case-mismatched
`Cutscene_e0m0_1`; and one is the table-fed SkipChapter `bindDlgId` route already
documented above. No additional exact Story-id literal was recovered. The audit
resolves only direct literals and simple string assignments; table fields,
function arguments, handles, concatenation, and control flow remain unresolved.
Nearby `Tables.*` names are recorded only as triage, not as data-flow proof.

### Authored-table Story-id census

Because the Lua lane reached Story through a small authored table, the whole
table corpus was swept for Story-id-shaped values: 693 tables in
`StreamingAssets/Table`, of which 41 contain them. Cross-checking against the
2,691 `actionableCoreIsolatedSceneKeys` gives 18 table/field pairs that name
actionable rows.

The census produced **no new ownership or activation source**. Every pair that
could have been one is already recorded in this note:
`ReadingPopUpTable.id`/`.contentId`, the four `Prts*` `contentId` families,
`AudioDialogCustomEventTable.dlgId`, `RadioTable.id`, `RemoteCommonTable`,
`FactoryBuildingPanelLock.radioId`, `DomainDepotDeliverTargetDialogTable`, and
`SkipChapterTable.bindDlgId`. The `Prts*`, `ReadingPopUp`, `RadioTable`, and
`RemoteCommonTable` rows are **definitions**, which this note already classifies
as non-activating.

What the sweep does contribute is triage. Two families are **table-proven
non-mission content** rather than unrecovered narrative:

- **79 `radio_continue_*` keys.** `AudioRadioContinueTable` has 31 rows keyed by
  **speaker** (`aglina`, `antal`, `ardelia`, …), each holding
  `selfContinue`/`otherContinue` lists of `radio_continue_{self,other}_<speaker>_NN`.
  There is no mission, scene, or script field. These are per-speaker
  continuation voice lines, not narrative scenes, and no mission will ever own
  them.
- **84 `sns_topic_chr_*` keys.** `SNSDialogTopicTable` has 117 character-keyed
  topic rows carrying `topicId`, `sortId`, `topicName`, and
  `topicStartOptionDesc`, with `includeDialogIds` pointing at the topic content.
  Character SNS topics, likewise not mission narrative.

**Shipped.** `build_source_story_gap_queue.py` now reads both tables and closes
their keys as a fourth isolated-scene class,
`closedNonMissionContentIsolatedScenes` (recovery status
`closed_table_backed_non_mission_content`), alongside the existing exact-native,
runtime-config, and definition-only closures. Report schema is now
`sourceStoryGapQueue.v10`. The regenerated CN queue closes **233** rows — 154
from `SNSDialogTopicTable`, 79 from `AudioRadioContinueTable` — dropping
actionable core-isolated scenes from **2,691 to 2,458**. Every closed row is in
the `other` bucket, so no main-story, event, major, or character count moves;
the `other` bucket score falls from 12,167 to 11,002.

The Mission Pipeline builder carries the same classification
(`counts.nonMissionContentFiles`, `nonMissionContentKeys`, attachment status
`non_mission_content`), and both frontends render it: a corpus stat plus a
separate collapsed section on the pipeline page, and a
`storyTriggerNonMissionContent` category on the Storyline page. **That surface
is currently inert by design**: the pipeline's 5,273-file denominator never
included any `radio_continue_*` or `sns_topic_*` key, so it reports zero today.
It is kept so a future export that pulls those keys into the pipeline classifies
them instead of showing them as unassigned gaps.

Note the count is 233, not the 163 an earlier filename-pattern estimate
suggested, because the table admits rows such as `sns_topic_map01_lv001_4` whose
names do not match a `chr_` pattern. That gap is the argument for the table-only
rule: resist extending this with filename patterns. A `_map0N_lvNNN_` sweep would
claim another ~420 rows, but that is a **filename inference**, which this note
rejects as evidence. Only authored table contents may admit a key, and
`test_build_source_story_gap_queue.py` pins that with a look-alike key that is
absent from the tables and must stay actionable.

The other newly-examined tables are facility content with no mission carrier:
`SpaceshipSubCharGiftTable` (per-character `dlg_npc_*_spaceshipgift`),
`SpaceshipRoomLvTable`, `SpaceshipEmptyRoomTable`, `SNSDialogValidMapTable`, and
`SNSChatTable`.

### The cinematic queue: a deterministic cross-type order rule

The same lane exposes the runtime **sequencer** for Story playback, and it is
statically decidable. `LuaSystem/CinematicSystem.lua` subscribes
`ADD_CINEMATIC_ITEM_TO_QUEUE`, `END_CINEMATIC_QUEUE_ITEM`, and
`TOGGLE_IGNORE_CINEMATIC_QUEUE`. `AddCinematic2Queue` either plays immediately
when `data.playImmediately` is set or enqueues onto
`LuaSystemManager.mainHudActionQueue`, and `_DoAction` dispatches by
`data.queueItemType` back into the native
`GameAction.DoPlayDialogByHandle`, `DoPlayCutsceneByHandle`, `PlayCGByHandle`,
`StartRemoteCommByHandle`, `ShowNarrativeBlackScreenByHandle`,
`ShowUIReadingPopPanelByHandle`, and `DoPlayForceSNSByHandle`.
`Beyond.Gameplay.Core.CinematicQueueItemDataBase` carries `id`, **`cinematicId`**,
`playImmediately`, `ignoreCinematicQueue`, `overrideBeforeMask`, and
`overrideAfterMask`; the handle type is
`CinematicQueueManager+CinematicQueueItemHandle`.

The queue position comes from `CinematicUtils.TryGetCinematicPriority`, a C#
method at **`0x186db798c`** that Lua reaches through XLua (it has **zero** direct
callers in the binary). Its body is a **pure switch on `queueItemType` returning
hardcoded immediates** — no table lookup, no server state, no authored data:

| `CinematicQueueItemType` | returned order |
|---|---:|
| `Cutscene` (1), `FMV` (2) | `-75` |
| `Dialog` (3) | `-74` |
| `RemoteComm` (4), `ForceSNS` (5) | `-73` |
| `NarrativeBlackScreen` (6) | `-72` |
| `ReadingPop` (7) | `-65` |
| default / `None` | `-50` |
| guarded byte flag at `data+0x31` set | `-100` |

`MainHudActionQueueSystem.lua` shows the surrounding scale, with every config
expressed as `CINEMATIC_ORDER_FIRST - N` from `-40` up to `CINEMATIC_ORDER_FIRST`
itself for the `Cinematic` entry, then `BLOCKER_ORDER` and positive orders for
HUD panels. Because the switch's default branch returns `-50` and the `Cinematic`
config's base order is exactly `CINEMATIC_ORDER_FIRST`, that constant is
**inferred** to be `-50`; the relative spacing above is proven from the
immediates regardless.

This is a real, source-only, deterministic ordering rule, and it is the first one
recovered that applies **across** Story kinds rather than within one script. Its
scope must be stated precisely:

- It orders only items **pending in the queue at the same moment**. It says
  nothing about items triggered at different times, which is still the ordinary
  case.
- **Radio is not a `CinematicQueueItemType`.** This does not touch the
  within-phase radio interleaving that remains the main unrecovered order
  problem, including the `e0m0` q#11 cluster.
- `playImmediately` and `ignoreCinematicQueue` bypass the queue entirely, so a
  flagged item is not ordered by this rule at all.
- The native body is behind `IFix.WrappersManagerImpl::IsPatched(0xbdfd)`; a
  future IFix payload could replace it, so re-audit the patch set per build.

Treat it as a **tie-break rule for co-pending items**, not as a mission playback
order. It should be applied only where two Story items are independently shown to
be queued together; it must never be used to linearise a mission.

**It has no applicable case in the shipped data. Do not implement it.**
The only structurally co-pending population in the source graph is `Split`
divergence, which this note already leaves unordered. A corpus-wide measurement
over all 4,512 LevelScripts found **2,753** `Split` records with two or more
arms, and resolved each arm to its first playback action by breadth-first walk
over `nextId` plus nested `splitActionLocalIds`, `branchLocalRefs`,
`sequenceLocalRefs`, `gateLocalRefs`, and `IfElseAction` true/false ids
(bounded at 512 visited locals per arm, zero parse failures). Results:

- **2,547** Splits have no arm that reaches any playback action;
- **206** Splits resolve to exactly one cinematic type, where a type tie-break
  is meaningless;
- **0** Splits resolve to two or more different cinematic types.

Only 208 arms corpus-wide reach playback at all, so `Split` is overwhelmingly a
parallel-setup construct rather than a playback fork. The rule is therefore a
correct and interesting decode of the runtime sequencer with an **empty
applicable population**; it changes no edge and must not be wired into the
builder. Revisit only if a future export produces mixed-type Split playback, or
if some other construct is shown to enqueue two different cinematic types
together.

`SimpleConditionCheckMapVar` also surfaces a small evidence family this note had
never examined. `Data/Json/MapConfig` holds 168 files with 49 `stateName`
entries gated by 33 `SimpleConditionCheckQuestState`, 11
`SimpleConditionCheckMapVar`, nine `SimpleConditionCheckMissionState`, and two
`SimpleConditionCheckGlobalVar` conditions, so quest/mission identity and map
identity do co-occur there. But `stateName` values are world-state names such as
`Map02_lv005_fields_unrise`, not Story keys, so this family **adds no Story
ownership and no order edge**. It is recorded as a bounded negative, not a new
attachment source.

The node-level mission graph now consumes one exact cross-source join that was
previously audit-only. For a mission-shell Story row, the builder takes the
LevelScript ids that host its exact Story occurrence and admits the row when
typed quest-objective `_scriptId` operands name exactly one same-mission quest.
When several objectives name the same script, only an `exact_unique_getter`
that names one member of that objective-owner set on the exact serialized
playback path may disambiguate it. Script-wide quest strings and getters from
another script remain unusable. The current build publishes 36 context rows
covering 34 Story files on 22 quest nodes; nine otherwise matching rows remain
rejected. These are
`quest_objective_levelscript_scope_context` rows with
`playbackOwnership=false` and `orderEvidence=false`: the objective may read a
different property from the one that causes playback. The WebUI and source
graph expose the relation as shared quest scope, never as ownership,
completion, branch, or chronology evidence. Reproduce with
`build_node_attachment_coverage.py` or the normal Mission Pipeline build.

The one newly resolved competition is `radio_sm1l2m4_2`: both
`sm1l2m4_q#2` and `sm1l2m4_q#8` inspect script `200120007` property
`puzzleSolved`, but the exact custom-event playback path reaches an
`IfElseAction` whose uniquely decoded getter names `sm1l2m4_q#8`; the radio is
on that predicate-controlled path. This selects q#8 dependency scope without
claiming that q#8 owns or initiates playback. The remaining same-mission
competition, `cutscene_map01_lv003_downstair`, stays unresolved between
`sm1l3m3_q#7` and `q#7d1`: both inspect script `300010039` property `isDone`,
both carry the same tracking position, and the exact trigger-slot-80001
cutscene path contains no quest getter. The other eight rejected rows are
foreign-mission shell duplicates whose objective owner belongs to a different
mission variant; the same-mission gate correctly keeps them unplaced.
The production source-graph rebuild confirms 36 edges in each direction for
quest/Story and quest/LevelScript scope. `radio_sm1l2m4_2` has only the q#8
quest-scope pair, including the exact predicate evidence and explicit false
ownership/order flags; q#2 and `cutscene_map01_lv003_downstair` have no such
edges. SQLite `quick_check` passes.

## Current recovery queue

The gap score is a triage score, never chronology. It separates core Story
isolation from ambient `env` and standalone-video rows, scores a quest gap only
when diagnostic Story evidence exists without a strict attachment, and leaves
gameplay-only quests visible but unscored.

Current main-story priorities:

1. Resolve the mission/quest triggers for the 153 unassigned Story files that
   already have exact current-build native playback actions. All 153 are now
   organized by 158 exact runtime receivers across 182 receiver-to-Story
   placements, and zero lacks a decoded selector. All native event
   owners now have exact serialized control paths from the 230-entry
   ActionHeader union table, including paths through the current-build
   `SwitchInt` layout. BattleSignal, spawner begin/wave, ScriptActive,
   ScriptStageChanged, custom-event producers, teleport-finish ids, death-event
   targets, and server-registration identity domains now have exact negative or
   bounded results. The completed spawner and BattleSignal ownership passes
   recovered real script/ability dependencies but no additional typed
   MissionRuntime ownership. One SpawnerComplete/config route and one tracked
   SavePropertyChanged route were promoted as context. The exact NPC-proxy
   segment pass now contributes nine additional weak shell rows plus two
   DialogTree children. The PureGetter state census retains nine unique Story
   files across eleven non-owning dependency placements and promotes only one
   already-connected `Equal(Processing)` mission context. The typed
   RadioTriggerZone carrier adds four connected Story files across six
   mission-state placements. The exact same-entity ReadingPopUp narrative maps
   add `radio_c16m4_50` and `_51` for `c16m4d5`, bringing the combined
   dependency surface to 15 files across 19 placements without claiming quest
   ownership; FactoryBuildingPanelLock raises it to 16/21 and the four exact
   DialogTree quest-state gates raise it to 20/25. The exact AirWall carrier
   now adds 20 radio files across 61 record-level mission attachments (60
   unique mission/radio placements); these are wall-state-gated pushback
   contexts and remain non-owning. The next useful step is
   no longer another pass over listener names or payload fields: the exact
   interactive progress-lock join has already promoted every current row that
   passes its typed entity/config/quest gates, while the remaining
   entity/property, combat/encounter, and lifecycle/navigation audits produce
   zero safe promotions. Progress now requires an independently typed
   cross-system owner from MissionRuntime, LevelData parent/host registries, or
   the opaque server-state implementation, plus another typed bridge for
   server-placeholder rules. The
   current IFix payload is proven not to replace those methods; only a future
   patch update warrants repeating that audit. The placeholder
   packet shape itself is recovered and cannot bind Story because it lacks all
   LevelScript/Story identities. Do not add name guesses.
   The highest-value binary target remains a server-authored activation/config
   surface that co-carries mission/quest identity and LevelScript or scene/
   script identity. Client MissionRuntime and the recovered protocol schemas
   stop on opposite sides of that join, so more receiver decoding alone will
   organize evidence but cannot establish ownership. Message 125 closes one
   tempting branch, and its native path is now fully decoded rather than
   assumed: the handler interns `(missionId, eventName)` into a runtime
   `CombineKey` and raises it through
   `SendGlobal<Beyond.Gameplay.EventData>`. The complete AOT method-spec table
   contains zero instances of the required
   `BindGlobal<Beyond.EventData<Beyond.Gameplay.EventData>>` subscriber shape,
   so compiled managed indirect call forms no longer remain an open caveat.
   The same-namespace map-var subscriber reads
   `belongMapId`/`mapVarName` and is not a pair. Message 125 therefore supplies
   no LevelScript/Story identity to join. See the global event bus section
   above for the decode and its bounds; the former
   `MissionEvent_OnCustomEventForMission` consumer surface was a label, not a
   decoded target. Messages 126/316/317 remain present schemas but have no
   installed fallback handler/sender.
   Message 57 now has the corresponding context boundary decoded as well:
   `_Handle_SceneTriggerClientLevelScriptEvent` constructs the exact
   `LevelScriptPtr`, allocates `EventParams`, copies a non-empty protobuf
   `ctxToken` into the inherited parameter blackboard, and then calls
   `RaiseScriptEvent(eventName)`. The downstream chase is now complete for the
   exact static key slot: four direct RIP references resolve to the handler and
   `CallServer::Execute` only. CallServer reads the value as `netToken`, passes
   it through `GameAction::TriggerServerEvent` and
   `GameplayNetwork::TriggerLevelScriptServerEvent`, and writes it back to
   `CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER.CtxToken`. This is round-trip
   correlation context, not an independently typed mission/quest carrier, and
   it adds zero ownership or order edges. The current IFix target list does not
   replace any method on this chain. Separately constructed equal keys,
   reflection, native memory manipulation, future patches, and future builds
   remain outside this bounded closure.
   The current protobuf surface has now been exhaustively checked with the same
   fail-closed rule: recursive typed-field traversal across 983 enum-backed
   CS/SC message classes finds zero mission/quest + LevelScript/Story
   co-carriers. The three weaker mission/scene rows are message 317's inactive
   sender and the mission/quest state role snapshots. Native consumers close
   the latter as server position reconciliation through
   `CharacterPositionCorrection`, not authored scene ownership. Do not repeat
   this schema join until the binary, metadata, or IFix hash changes; search
   non-protobuf config/asset registries or independently typed server-state
   evidence instead. The AirWall result demonstrates the productive version of
   that search: prioritize typed config roots whose state predicate and Story
   consumer coexist in one validated object, then trace both the state listener
   and playback consumer before promotion.
   `MissionOptionData` is now closed under the same rule: its two identities
   select mutually exclusive native branches, its current authored-instance
   census is empty, and the installed IFix replaces none of the path. Do not
   revisit it until the binary, export, or patch hash changes.
   The nested `MissionRuntimeAsset.propertyDic -> ParamVariable.m_scriptPtr`
   shape is closed too. Current authored mission properties contain values but
   no script pointer, all three MissionSystem property handlers write the
   server-synchronized `MissionData.propertyDict` through `ToVariable`, and
   direct `m_scriptPtr` setters belong to LevelScript event registration.
   Reopen only when the binary, metadata, authored property shape, or IFix
   changes.
   The implicit action-context shortcut is closed as well:
   `ParamSource.CURRENT_MISSION_ID=1004` appears only in 18 MissionRuntime
   self-property checks across six missions and in zero of 4,512 LevelScript
   files / 74,839 UID records. It adds no Story or order edge. Do not revisit
   current-mission Param inheritance until authored data, metadata, binary, or
   IFix changes.
   The complete direct managed identity-carrier census is closed as well:
   ten exact candidate types, eight runtime/serialized object candidates, and
   zero unreviewed candidates. The only newly decoded pair is mission/scene
   tracking state, whose native consumers add and display HUD/map trackers and
   never call Story playback. Do not repeat direct managed field-pair searches
   until metadata, binary, authored tables, or IFix changes.
   The MetadataRegistration-backed nested census now closes the typed portion
   of that frontier to three custom-type hops as well: 25 candidates, 14
   nested-dependent, and zero unreviewed. Its last concrete candidate,
   `DialogManager.m_pendingItemSubmitter -> InventoryItemSubmitter.questId`,
   is actively produced by shipped `SubmitItemCtrl.lua` through XLua even
   though the native direct-call census is zero. Current DialogTrees expose 13
   typed SubmitItem terminals but only three stock placeholder parameter
   objects, ten empty parameter objects, and zero concrete quest ids. The
   fallback native/`PhaseDialog.lua` path forwards and decodes those params
   without quest substitution. Three exact MissionRuntime submission checks
   now recover quest-to-submission requirements; two have same-AND dialog
   co-gates, but those dialog ids overlap zero SubmitItem OpenUI terminals.
   The remaining authored shape is now explicit rather than left as an
   untyped condition-tree coincidence: `sm2l7m1_q#17` requires both the flute
   submission and stage-max for `map02_lv008/23100170008`. That script's exact
   dialog-exit path orders `dlg_sm2l7m1_17 -> dlg_sm2l7m1_9`, but it contains
   no submission id or SubmitItem OpenUI action. Its former `0x09b9/0x00`
   unknowns are now exactly normalized to ActionBase tag `0x00b9`/nine members,
   `ExitLevelCustomPerformance`; all three carry only the same unbound zero
   handle payload. The two playback branches are otherwise fully typed as
   dialog-and-teleport, clear-screen toggle off, main-character move to
   `walk_end_pos`, clear-screen toggle on, and custom-performance exit. Their
   former low-confidence `0x0e34/0x00` tails are now exact
   `CallServer` actions waiting for callback with an `event_args` pointer.
   Each event name is exactly `#` plus that action's own record UID, matching
   the complete current typed corpus. Treat these as local callback/correlation
   labels and diagnostic-only records, never hash-terminal Story nodes or
   mission/order evidence. Keep
   this as objective co-gating plus independently proved
   playback/presentation-cleanup context, not UI activation or a new
   quest-to-Story playback edge.
   Do not repeat this typed traversal until the binary, metadata, authored
   MissionRuntime/DialogTree/SubmitItem data, Lua, or patch changes. The next
   useful join must be another independently typed owner or newly changed
   authored/runtime surface; do not infer it from dialog filenames.
   The recovered LevelScript task packet family still sharpens the dynamic side
   of the target. Its concrete sender/handlers and decoded object offsets are
   mapped in `mission_runtime_trace_hooks.json`; the guarded message-815
   callback also recovers each condition id and its applied completion boolean.
   A future permitted runtime capture could join observed
   `(sceneNumId, scriptId, taskId, conditionId)` transitions to exact task maps
   and action paths, but the current protected game process denies both normal
   Frida writes and elevated target allocation (`WriteProcessMemory`/
   `VirtualAllocEx`, error 5) while `ACE-BASE.sys` is active. Treat live
   injection as unavailable in this environment; do not weaken or bypass the
   anti-cheat. If a supported capture environment becomes available, co-record
   mission/quest state, the LevelScript event/action chain, and final Story
   playback in one session. This can recover observed trigger order, forks, and
   convergence for a played route, but temporal overlap alone remains non-owning
   unless the runtime call chain or original data supplies the missing join.
   The bounded direct-call scan found no bridge between the two native lanes,
   and the current installed Lua chunk contains neither the then-182 audited
   playback ids nor their 106 listener/target script ids. Both results have now
   been re-run without their original blind spots and both survive: the lane scan
   was repeated in both directions with generic instantiations named over
   1,662,080 resolved calls, and the Lua surface was re-queried by global-event
   subscription name instead of by id. See the two sections above for the
   enumerated edges and the `MessageConst` vocabulary. Indirect dispatch and
   other shipped serialized consumer registries remain the original-data
   frontier; the negative result must not be filled with OCR or observed
   gameplay.
   The completed NpcProxy selector trace also closes a tempting false bridge:
   server resync/change supplies `activeCondIndex`, the client selects
   `exDatas[index-1].dialogId`, and that selector neither reads adjacent
   `missionId` nor calls MissionSystem. `missionId` is consumed separately only
   by the paused-mission deactivation guard. All 138 currently unlinked
   NpcProxyEx placements (126 Story files) have blank mission ids, so proxy
   tracking or server-selected row identity adds zero bindings.
   A separate exact `NpcProxyTable.lazyDestroyOverrideDialogId` carrier does
   add one bounded context edge. Only three current proxy rows configure that
   field; `lanshan_map02_v1d4d0_003` is the sole `lazyDestroy=true` row whose
   proxy is consumed by exactly one same-scene typed tracking record,
   `sm2l7m1_q#17`. It attaches `dlg_sm2l7m1_18` as non-owning quest navigation
   context. Native `NpcProxy.OnDeActive -> NpcProxyMgr.ApplyLazyDestroyData ->
   NpcManager.AddOverrideInteractDialogId` reads the field at runtime, while
   the upstream proxy state is server-pushed; there is no client request or
   expected reply and no proof that q17 causes deactivation or playback.
   The exhaustive unnamed-MonoBehaviour/PPtr follow-up scanned the 71 remaining
   Leader-family keys, expanded 352 initial file candidates to 381 exact CAB
   candidates, and decoded 15 reachable objects. It recovers one exact
   `cutscene_e11m1_dg011_2 -> _director -> PlayableDirector -> m_PlayableAsset`
   chain, but that complete component contains no typed mission/quest carrier;
   all 14 formerly unresolved nonzero PPtrs are `m_Script` and there are zero
   unresolved non-script PPtrs. Original CAB dependencies and a 1,018-row
   MonoScript registry now classify all 14 MonoBehaviours exactly: two in the
   loaded process and twelve by unique external CAB filename plus PathID. None
   carries a typed mission/quest identity, so this adds zero bindings. The CLI
   now has an opt-in compact object/schema/MonoScript JSONL writer and a
   deterministic cross-process merger. The maintained
   `build_animestudio_story_carrier_audit.py` consumer validates the published
   commit marker, stage signature, and hashes, then searches the actionable
   source-gap keys for exact typed Story-id fields co-carried with typed
   mission/quest or scene/script ids on one fully decoded object. It emits
   candidate rows only and cannot create ownership or order without a separate
   native consumer proof. Partial/truncated objects, unresolved scripts,
   untyped names, substrings, neighboring objects, filename/PathID proximity,
   OCR, and overrides fail closed. The last hash-validated installed-game
   census scanned 1,335,450 object rows for 2,691 actionable gap keys. It found
   190 objects with exact target values but zero typed
   same-object Story plus owner/runtime candidates. Exact
   `TimelineAsset.m_Name` and `CutsceneRootComponent._timelineName` occurrences
   remain rejected name/timeline clues, not ownership or order evidence. The
   historical result is preserved in
   `reports/story/recovery/animestudio_story_carrier_audit.{json,md}` and adds
   zero bindings or edges. A later Story carrier refresh ran without
   `--animestudio-object-index` and deliberately invalidated the published
   commit marker. Installed-data fingerprints still match that indexed run,
   but current AnimeStudio CLI provenance does not, so the maintained audit
   correctly refuses the leftover compressed index. Do not relabel its old
   zero-candidate result as current evidence or manually restore the marker.
   The next authorized offline refresh is:

   ```bat
   .\export.bat --export-from-game --animestudio-object-index --mission-pipeline-only
   python scripts\story_recovery\build_animestudio_story_carrier_audit.py
   python scripts\story_recovery\build_source_story_gap_queue.py --language CN
   ```

   A fresh hash-validated index can close or nominate serialized carrier
   candidates; even a positive same-object row still requires independently
   recovered native consumer semantics before ownership/playback promotion and
   a separate serialized control relation before any order edge.
   The generated coverage report now inventories 153 files across 25 decoded
   event families; the largest unique-file groups are Leader trigger volume
   (67), BattleSignal (16), Script custom event (13), and ScriptStageChanged
   (9).
   The source graph now mirrors all 158 exact runtime receiver nodes and 182
   receiver-to-Story placements. Every receiver retains its exact level,
   LevelScript, header id, selector, event family, native action, and source
   file while emitting zero mission/quest edges. This closes a queryability gap
   without changing the 153-file ownership frontier.
   The offline activation-frontier pass further divides the 93 hosting scripts
   into 10 exact SubGame activation scopes, 12 non-SubGame scripts with
   non-empty start shapes, 17 other non-null static start/task shapes, and 54
   Manual scripts with no decoded static shape/task/parent carrier. No receiver
   script is named by a typed MissionRuntime objective and no incoming literal
   cross-script manual control targets one. The 12 shaped scripts have zero
   complete exact same-level MissionArea shape matches; nearby centers with
   mismatched shape fields do not qualify. Across the 24 task-map scripts, the
   only serialized MissionRuntime-id constants are `a1m6d6`/`a1m6d7` in the
   already SubGame-scoped `22800950006`; all 83 non-SubGame receiver scripts
   have zero exact mission-id string tokens. This closes broad LevelData,
   start-type, start-shape, objective-operand, literal mission-id, and literal
   ManualStart searches as generic ownership routes. The task maps themselves
   are now completely decoded for all 24 affected scripts: 31 tasks carry 54
   exact conditions across 11 types, with no `CheckMissionState` condition.
   A complete 82-id task/condition census finds zero MissionRuntimeAsset use;
   the only foreign roots are 13 task-display rows and ten null-mission SubGame
   main-task bindings. The typed operand pass now resolves 53 exact source rows
   but finds zero MissionRuntime consumers, and the native callback pass finds
   zero exact `CheckLevelScriptTaskFinished` consumers for the 31 receiver
   tasks. These task-map ownership routes are closed on the current export;
   condition presence, source identity, same level, callback registration, and
   evaluation order remain non-owning.
   The exact Dungeon/SubGame scene join now adds context to `18` scripts and
   `14` Story files across `6` scenes (`40` placements), but only `7` are the
   actual bound script and `33` are siblings. The `cutscene_e9m3_2` /
   `e9m4_q#1` mismatch proves availability cannot stand in for ownership, so
   this lane is closed as a promotion source and remains debug context only.
   Nine of those sibling receivers also have a typed dungeon mission shell.
   The `c6m3`/`c6m1` and `c13m2d5`/`c13m2` mismatches reject even this stronger
   field as sibling-Story ownership; preserve it as runtime context only.
   All typed SubGame mission/logic whitelists are empty. The only proxy
   whitelist reaches two already-connected `f1m18d1` dialogs and no NpcProxyEx
   mission id, so the current whitelist surface is exhausted.
   The DungeonSubGame death-performance collection is universally empty, and
   its team-death hint is generic rather than a Story key. Do not revisit it
   for the 67 unassigned black scenes on this export.
   A diagnostic level intersection with the atmospheric switcher context finds
   89 receivers / 103 Story files on 13 shared levels. Four shared levels have
   only one atmospheric route mission, but their native Story families often
   name different missions (for example `map01_lv002` context is
   `sm1l2m2` while its receivers include `e1m7`/`e1m8` Story). Same-level
   atmospheric state is therefore useful only for capture-session triage; it
   remains non-owning and creates no receiver-to-context or mission edge.
   The exact WorldEntity bridge has removed three Leader-family files, two
   ScriptStageChanged files, and one InteractiveStateChanged file. Revisit remaining rows only
   when another typed MissionRuntime/LevelData bridge, shipped asset carrier, or
   changed installed binary/IFix payload becomes available.
   Use the report's exact key lists as the queue instead of filename sampling.
   Continue to require typed gates and unambiguous `ActionHeader.nextId`
   chains; do not reuse raw task-map proximity.
   The last validated merged object-index carrier census produced no typed
   carrier; refresh it after the exporter provenance changes before treating
   that negative as current. Apart from that refresh, the remaining concrete
   experiment is the first supported runtime capture rather than another
   receiver-name or loose-object pass. Start with `e11m1`: use the
   existing hash-locked recorder around
   `LevelScriptRuntime._RaiseOnScriptEvent` (current token `0x060121a3`, method
   index `74146`), propagate one unique chain id through ActionHeader/ActionBase
   dispatch and the mapped Story playback entry points, and snapshot
   MissionSystem mission/quest activity before the playback row is emitted.
   The action-backed final-key probes cover dialog/radio/remote communication/
   cutscene, the exact field-backed SNS UI probe covers `sns_*`, and its exact
   queue-item/handle/brain identity handoff preserves a dispatch chain across
   the asynchronous UI start when the accepted queue request still has one.
   Three queued dialog actions likewise emit only after the exact
   queue-item/handle path reaches `_PlayDialogInternal` beyond the native
   acceptance check. The action-backed mask decoder covers native black-screen
   lines. The Tick-based
   initial state snapshot now closes late attachment for structurally valid
   current MissionSystem dictionaries. Repeat the same route in more than one
   session and exercise alternate
   choices/conditions; one run recovers an observed path, while repeated
   differing successors are required to expose observed branches and repeated
   predecessors into one target expose merges. Resolve hooks again for every
   game build rather than carrying the current audited RVA forward. The
   importer and WebUI overlay are ready; no real capture has been ingested, and
   the current protected client blocks Frida injection. Do not weaken or bypass
   that protection; wait for a supported capture environment.
2. Continue original-data ownership recovery for the 67 unassigned black
   scenes. Six already have exact current-build LevelScript playback and
   event/control paths but no validated mission host. No wholly unlinked black
   file remains recoverable through an exact DialogTree parent; one connected
   file has a second unresolved parent use. The other 61 have
   no current-build original-game playback consumer. The next useful binary
   frontier is a serialized server/runtime activation registry that contains
   both LevelScript and MissionRuntime/quest identity. The current
   `TeleportParam` loading carrier is also closed: producers do not co-populate
   its mission/script fields and consumers never read `missionId`. Repeating
   current LevelScript, DialogTree, Timeline, PlayableDirector,
   MissionRuntime, or teleport-loading scans will not bind them unless the
   installed build/export or IFix payload changes; event
   names, slots, Story-name co-membership, and Common Mask visual PPtrs remain
   insufficient. The current installed Lua corpus contains no `black_*` Story
   id and therefore does not supply that missing consumer.
   Timeline containment itself is fully resolved for its current recovered
   clip set.
3. `e11m1` remains a high main-story source-link gap, but no longer appears to
   have a large LevelScript control-flow backlog. Of its 67 weak-only rows, 64
   have complete exact native event paths and three retain only non-ordering
   topology; zero remains an actionable control-flow decoder row. Its current
   queue has 30 actionable core-isolated source-link candidates after exact
   native and runtime-configuration closures. The full current-build
   custom-event producer scan
   finds only the already recovered `TigerStart` same-script producer/listener
   route. `TLCall_radio_e11m1_1`, `TLCall_PlayRadio`, and the six hashed
   Script CustomEvent listeners have no matching serialized
   `RaiseCustom*Event` producer route, so they remain unconnected. The native
   producer census above explains why and does not change the result: the
   remaining producers are shared runtime infrastructure and server message 57,
   neither of which selects a mission for these listeners.
   The apparent exact singleton is also a proved negative:
   `SimpleConditionCheckPlayerInLevel(indie_dg011)` selects
   only the current level, not its sole exported LevelScript `36900010001`.
   That inventory coincidence covers four residual Story files but is not an
   authored activation carrier. The activation-frontier audit now proves the
   stronger shared boundary for both e11m1 receiver scripts:
   `indie_dg011/36900010001` is the sole member-22 entry in generic
   `indie_dg011_lv_data_sub_01.json`, while
   `map02_lv007/10200260001` is the sole entry in generic
   `map02_lv007_lv_data_sub_MissionDefense.json`, not in the separate
   mission-named `map02_lv007_lv_data_sub_e11m1.json`. Both scripts serialize
   `startType=Manual`, null start shapes, null task maps, parent script `0`,
   zero typed MissionRuntime objective consumers, zero SubGame bind rows, and
   zero incoming literal cross-script ManualStart controls. Runtime/server
   state can still activate them through an unexported carrier, but the audited
   static LevelScript/LevelData fields do not contain it.
   The newly proved spawner wave-4 -> wave-5
   relation orders two typed radios but supplies no mission/quest identity.
   Pursue a typed scene/script owner rather than more header decoding, HP
   threshold assumptions, or level proximity.
4. The first static exact-carrier passes over `e10m4` and `e11m4` are closed.
   `e10m4` has 53 exact typed Story-bearing native records, but only
   three occur on isolated scene nodes: `radio_e10m4_39` and `_54` are
   independent same-numbered Leader trigger slots in different scripts, while
   `_64` is the only Story playback on a local scripted-character patrol
   callback keyed `levelseq`. The former `cutscene_e10m4_1` gap was a missing
   typed `Branch` traversal, not a free action root. Original file
   `24400020037` serializes `Branch` local 120 with `_idList=[143,121]`;
   `GameAssembly.dll` proves that list is ordered continuation. Following
   `Branch.sequence[1]` reconnects the cutscene through locals
   `121 -> 122 -> 123 -> 124 -> 125 -> 136` to `LevelEvent_OnCustomEvent`
   header 89 (`start_p2`). `radio_e10m4_69` is reached from the same header but
   diverges earlier at `Split` local 101 (`actions[3]` versus the cutscene's
   `actions[0]`), so the two remain unordered and no file-order edge is
   promoted. This closes e10m4's sole actionable weak-control row.
   The current `e11m4` queue score is 229: 49 core isolated scenes split into
   41 actionable rows, three exact-native closed rows, and five exact
   runtime-configuration closed dialogs. The latter are
   `dlg_e11m4_4`, `_9`, `_10`, `_11`, and `_12`. Their exact
   `NpcProxyExDataTable` rows name mission `e11m4`, map `map02_lv008`, and one
   proxy each. The installed native path
   `NpcInteractComponent._TryGetNpcProxyInteractDialogId` at
   `0x183564080` selects the server-supplied one-based active row and reads its
   `dialogId`; `NpcProxy._IsMissionConflict` at `0x18706ac74` consumes the
   adjacent `missionId` separately as a paused-mission deactivation guard.
   This closes missing source ownership for those five rows but adds no order
   edge. In particular, proxy suffixes and `NpcProxyEx` list/table order are
   not chronology.
   The third exact-native closure is `black_e11m4_1`. Its original
   `dlg_e11m4_14` DialogTree graph places its sole line after parent line
   `_006` and before `_007`. The parent dialog itself is reached by the exact
   `map02_lv008/23100090001` Leader-enter trigger-slot `80002` path ending at
   `StartDialogAction` local `22`. Because `dlg_e11m4_14` contains lines on
   both sides of the nested black-screen action, this recovers line placement
   but deliberately adds no scene-file edge. The other two exact-native
   isolated closures are playback nodes: `_15` listens for guide group
   `guide_group_miasma_ghost`, and `_16` listens for local custom event
   `#a6a41acb` behind `ifkilled`. The custom-event key occurs only in its
   listener script, and the exact guide-group id likewise has no serialized
   producer outside its completion listener; the distinct
   `guide_group_miasma_ghost_media` string is not treated as the same id. The
   nearby `e11m4_q#2` task-map/config record is not on the `_16` playback path.
   Separately, admitting only strict path-comparable cross-owner scenes recovers
   the original e11m4 Liexi chain
   `cutscene_map02_lv008_liexi_xs_m_02 ->
   cutscene_e11m2467_liexitexiao_02 -> dlg_e11m4_13`; it does not connect the
   isolated radio listeners.
   The remaining radio-heavy block is also bounded more tightly. Exact-string
   searches for `radio_e11m4_7`, `_8`, `_29..55`, and `_57..61` find those 34
   ids only in the original `RadioTable` definitions and `AudioDialog`
   membership among the authoritative MissionRuntime, LevelScript,
   GameplayConfig, and Table consumer families. Current binary metadata for
   `RadioData` exposes `continueAfterDialog`, `continueAfterRadio`, `priority`,
   `radioSingleDataList`, and `radioType`, but no next-radio or cross-radio id.
   A complete installed Lua VFS dump recovered 1,290 of 1,291 decoded entries;
   the one malformed base64 `.md` companion has a corresponding recovered
   60,071-byte `.lua` file. None of the 34 exact radio ids occurs in that Lua
   corpus. A whole-`GameAssembly.dll` direct-call census over 354,959 unique
   method pointers found 38 calls to the recovered radio playback entry points,
   confined to XLua wrappers, patrol/balloon/narrative helpers, air-wall/focus/
   radio-zone components, and serialized ActionBase playback. No new carrier
   for the 34 ids appears. This materially strengthens the negative boundary,
   but indirect/delegate/virtual/IFix dispatch remains a reason not to convert
   the rows into a universal no-consumer classification.
   This proves that RadioTable row order cannot order the files; it does not
   prove that every possible external system registry has been exhausted.
   Reused trigger-slot numbers, file position, and nearby task records do not
   order these scenes.
   The isolated `cutscene_e11m4_rift_camera_state1to2` is similarly bounded.
   Its numeric Timeline registry id is exactly `484`, between the e11m6/e11m2
   registry entries `483`/`485`, but exhaustive structured scalar searches
   find no consumer and no `InteractiveRiftComponent` field carries a
   cutscene id. The binary exposes only the generic cutscene-transition path
   and tag. A second whole-binary census finds 33 direct cutscene-entry calls,
   all in XLua wrappers, dialog/battle helpers, the GameAction chain,
   ChangePlayerGender, and typed Play/StartCutscene actions; decoded Lua and
   exported actions contain no exact e11 transition id. Registry position and
   code address therefore remain identity/cross-reference only, not playback
   or mission order.
   The mission evidence audit now enforces the same boundary for Reading/PRTS:
   exact `contentId` joins count as links, while five e11m4 same-number/suffix
   candidates are labeled cross-references only. In particular,
   `dlg_e11m4_3` is not owned by unrelated facility readings merely because
   their suffixes match.
   The two remaining exact dialog definitions also close the local
   DialogTree-internal frontier without adding ownership.
   `dlg_e11m4_3` is a registered root with the pure directed chain
   `_001 -> _002 -> ... -> _008 -> Finish`; `dlg_e11m4_15` is
   `_001 -> _002 -> Finish`. Their extra configs contain only `DialogTreeData`
   voice settings (plus one per-line 2D-sound flag for `_15`). Neither graph
   has a narrative/subtitle/OpenUI action, quest-state gate, nested dialog, or
   cross-Story trunk carrier. This proves their internal line order and
   definition identity, but the exact external activator remains absent, so
   both stay actionable source-ownership gaps.
   Further progress needs a genuinely new cross-system producer/owner
   registry or runtime capture, not another local carrier census. `e11m4`
   remains the highest-scoring main-story gap; its remaining work is source
   ownership, not the already-closed local playback, embedded placement, and
   runtime-configuration carriers.
5. `e7m3` no longer has an actionable LevelScript control-flow row: it has zero
   untyped multi-scene contexts and zero actionable weak-only scenes. The
   source-only queue now scores it 83 at main-story rank 12, with 58 scenes,
   23 strong/reduced edges, zero cycles, 19 isolated scenes, and nine
   actionable core-isolated source-link gaps. The installed DialogTree resolves
   `black_e7m3_1` to the exact `dlg_e7m3_14` playback context described above,
   while exact NpcProxyEx mission scope closes `dlg_e7m3_11` and `_12` without
   relative order. The remaining actionable keys are `dlg_e7m3_13..16`,
   `radio_e7m3_16`, `radio_e7m3_26`, and `text_e7m3_1..3`. The four dialog
   proxies have blank mission ids (and `_13` is attached only by a non-owning
   DialogTree quest-state dependency); the two radios are definition-only
   RadioTable rows with no recovered consumer; the three text files have exact
   ReadingPopUp/RichContent definitions but no activator. Continue only if a
   new typed original-game producer or mission/quest carrier appears. Proxy
   suffixes, table order, filename numbers, OCR, and manual overrides remain
   cross-reference only.
6. Keep the strict graph cycle-free from evidence rather than by deleting
   contradictory edges. If a future export produces a cycle, first audit
   occurrence reuse, action type, physical `ActionSerializedMap` list
   membership, and quest-instance projection before treating it as playback
   recurrence.
7. Keep the residual option frontier evidence-strict. Complete Runtime Jump
   paths are now reduced to their option-exclusive prefixes, with a
   no-exclusive-response arm represented as a direct jump to the shared
   continuation rather than rejected for lacking a fabricated response line.
   This recovers the exact asymmetry in `dlg_e3m6_101` (one arm skips `_019`
   and both resume at `_006`) and `dlg_e3m6_102` (one arm plays `_002`, the
   other resumes at `_003`). Exact per-option branch provenance is also carried
   from both direct DialogTree and DialogTreeFragment sources, and complete
   authored terminal/OpenUI/menu-loop outcomes are closed as non-line outcomes
   instead of being mislabeled missing line routes. The current generated
   partial-order frontier contains 368 strict groups / 767 option arms / 1,597
   branch lines. It retains 2,146 closed exclusions and 468 no-route groups,
   but 463 of those no-route groups are single-option prompts. Only five
   multi-choice groups remain globally, and the main-story option frontier is
   now zero.
   Pre-dialog Runtime Jump windows recover the exact `dlg_e11m3_16` split
   (`_001.._003` versus `_004.._006`). Zero-index Timeline trunks are also
   closed as shared continuation when only one or two local lines remain;
   groups whose same text-table option ids occur at distinct zero-index
   Timeline positions are sequential prompts rather than one fork; and an
   option slot after the final local Timeline line is recorded as having no
   intra-dialog line route without claiming that no external scene follows.
   `dlg_e2m6_11` is a separate exact definition-only closure: its local
   DialogTree launches `dlgtl_e2m6_11_sub_1`, but that Timeline consumes only
   the two `dlg_e2m6_19` option ids and maps them completely to finish numbers
   `0/1`; the same-text local option rows are not runtime consumers.
   Six more apparent incomplete non-line outcomes are also exact
   definition-only closures. In each case the recovered DialogTree option node
   explicitly names only option 1, while the same-prefix option 2 exists only
   in `DialogOptionTable` and is absent from every recovered DialogTree,
   scene-link, Timeline, and route consumer. The generated conversation keeps
   both text rows but marks the unused id as definition-only; the Mission
   Pipeline records the authored option 1 outcome without inventing an option
   2 branch.
   `dlg_c28m3_10` g1 is now an exact positive clip-index route rather than an
   inferred-following-lines risk. Its authored option indices are `1/2`; every
   response trunk clip matches those values, yielding option 1 ->
   `_023,_024` and option 2 -> `_025,_026`. The only in-window Runtime Jump is
   option-index 1, starts after `_024` ends, and lands exactly at the shared
   `_021` start, so it accelerates convergence past the inactive option-2 tail
   rather than contradicting the mapping.
   The remaining false gaps were closed by exact negative evidence rather than
   branch guesses. A scene absent from `DialogIdTable` is now closed only after
   the full route/outcome collector finds no authored consumer; this accounts
   for 180 source-less groups. One branch-line row belongs only to a proven
   definition-only option id. Eight DialogTree layout negatives are also
   closed: same-prefix ids on distinct option nodes are separate conditional
   prompts, while ids on a disconnected option node with no outgoing edge are
   orphan definitions. In the positive direction, an option route that reaches
   an actual `DialogTreeIfNode` retains all serialized conditional outcomes.
   The current corpus has 14 such option rows across eight scenes. The parser
   explicitly rejects following option/submenu nodes as conditional branches;
   that regression guard prevents hundreds of false outcomes and a spurious
   strong edge.

   The five surviving groups are `dlg_gm02m2_2` g1,
   `dlg_gm02m2_3` g2, and `dlg_gm02m3_{1,2,3}` g1. All five are exact
   `DialogIdTable` roots with complete option-id membership, but the registry
   has no line/trunk fields or `usedDialogTimelineIds` for them. The current
   export has no matching DialogTree, Timeline, MissionRuntimeAsset, or
   LevelScript source and the source graph finds no route consumer. A targeted
   local installed-VFS census matched zero `gm02m2`/`gm02m3` files across all
   936 chunks and every block family; a complete extraction of the 1,290
   readable Lua modules also contains no exact mission, scene, or option-id
   reference. No saved `export_1d2` tree is present to test an older build.
   Their option text suggests mission-state or return-location choices, but
   text semantics cannot establish the outcome graph. This is now a bounded
   unavailable-source frontier: further offline recovery requires an older or
   newer authored data archive containing those mission assets (or another
   exact consumer surface), not more inference over the current installation.
8. Keep unresolved narrative videos standalone until Timeline or another
   original-data source binding establishes placement; observed playback may
   cross-check but does not promote the connection.
9. The inter-mission graph is now recovered from cross-mission state
   conditions and is complete with respect to that evidence class: 153 edges,
   zero dangling targets, zero unclassified operands, and the one mission-level
   cycle explained by an acyclic quest graph. Do not re-derive it from
   filenames, chapter tables, or mission-id numbering. The next real
   improvement needs a *different* evidence class -- a server-authored
   activation surface co-carrying mission identity -- which is the same
   blocker recorded above for Story ownership.
10. envTalk consumers are enumerated and the 1,316 files with no consumer row
   are a measured negative, not an unexplored gap. The atmospheric cluster
   lead is closed: exact same-level full-NPC-set joins recover switcher
   mission/quest state context for 359 files, while preserving it as
   availability context rather than playback or ownership. Future work here
   needs a new source that directly proves ambient playback or trigger choice;
   looser entity overlap, filename mission fragments, and condition order are
   not such evidence.

The practical ceiling remains unchanged: original data can recover local
chains, partial mission graphs, quest forks/merges, verified dialog branches,
and authoritative media bindings. A complete mission-by-mission playback list
requires additional runtime/server-state evidence or an explicitly separate
manual/observed policy.
