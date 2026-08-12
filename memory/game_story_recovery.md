# Game Story recovery

## Current status

The Story builder reconstructs dialog, radio, SNS, cutscenes, options, inline
media, localized reference links, mission grouping, and an evidence-typed
partial order. The browser is useful for research, but it does not claim a
complete canonical playthrough.

Current CN headline coverage from the maintained reports:

- 487 source-order missions and 5,563 unique Story files;
- 4,236 connected files (76.1%);
- 4,457 files with at least one normalized trigger/context route (80.1%);
- 1,327 unlinked files, including 156 with exact native playback but no
  mission/quest activation bridge;
- 1,529 strong source-only edges across 8,877 candidate scene placements;
- 0 cyclic components;
- 3,850 of 249,695 possible within-mission pairs proven comparable (1.54%).

Counts are volatile. Use the generated coverage, partial-order, and gap-queue
reports for the current inventory rather than copying detailed counts here.

## Stable recovery model

Story evidence is layered and kept visibly typed:

1. **Authored Story structure:** DialogIdTable, DialogTree, Timeline,
   conversation tables, option definitions, and narrative media rows.
2. **Mission structure:** MissionRuntime quests, predecessors, objective and
   failure conditions, typed client actions, and related source files.
3. **Runtime configuration:** LevelScript, LevelData, SubGame, spawners,
   interactive records, and shipped Lua consumers.
4. **Installed-binary contracts:** hash-pinned IL2CPP/metadata evidence for
   action types, branch polarity, state application, scheduling, and playback
   calls.
5. **Cross-reference only:** OCR proposals, manual Story order, filenames,
   source proximity, and gameplay observation.

The first four layers can contribute a connection or order edge only through a
validated typed relation. Cross-reference material can guide investigation but
never promotes an edge.

## Recovered Story structure

- DialogTree and Timeline data recover most line order and explicit option
  routes. Strict intra-dialog option routes currently cover 799 options in 383
  groups and 1,666 branch lines.
- Narrative videos, inline images, SNS media, and playable audio are linked
  without treating media definitions as playback or mission ownership.
- Character Wiki voice rows are not a complete substitute for gameplay voice
  catalogs. ResponsiveDialog retains trigger/response relations and additional
  exploration lines; `greetEnvTalk` is only partly duplicated by profile
  voices, while `radio_continue_self_*` remains distinct. Duplicate text/audio
  may be folded in presentation, but the authored trigger records stay intact.
- Exact DialogTree conditionals, branch nodes, and IfNodes retain all decoded
  arms and polarity. They describe local selection unless a typed cross-Story
  continuation is independently proven.
- Multi-output DialogTree controls use one schema-driven native decoder for
  managed enum/static-port families. For OpenUI nodes it derives the installed
  `Dictionary<DialogOpenUIType,List<string>>`, selector-to-string getter,
  explicit continuation-index path, and current IFix exclusion from original
  binary inputs. A second schema-driven pass target-dumps all 1,290 installed
  Lua files and fails closed over the shared phase router, default table, every
  override-message occurrence, and every direct native `Next` call. The current
  86 controls / 172 arms divide into 123 arms with a bounded shipped producer,
  35 with a dynamic producer whose exact index is not statically bounded, and
  14 with no producer in the current shipped Lua corpus; validation failures
  are zero. Named ports remain exact authored alternatives and absent map rows
  remain ordinal-only. Producer presence is not an observed choice, activation,
  mission owner, or cross-file order; producer absence is not permanent
  unreachability. Anonymous zero-edge controls remain detached definitions.
- Timeline option-index and track evidence remains selection/placement
  evidence, not mission ownership or cross-file chronology.
- Manual option fixes live in `webui/overrides/options.json`; manual mission
  order lives in `webui/overrides/story_order.json`. Builders do not replace
  the latter with OCR output.

## Mission and quest conclusions

- MissionRuntime predecessors, exact typed Story actions, and objective
  relations form a source-only mission graph.
- Quest forks are authored topology. Main/auxiliary labels, guards,
  `questType`, `showMode`, and reconvergence describe configuration and
  presentation; they do not prove which successor the server selected.
- Fork-arm source attachment is corpus-driven. Each sibling-exclusive corridor
  identity must exist in the exact original MissionRuntime `questDic`; a shared
  recursive walker then admits only records carrying both `sourceFile` and a
  byte hash. The current corpus publishes 3,337 authored quest-source placements
  and at least one original file on all 740 arms, including 395 arms with no
  Story placement. Twenty-three arms immediately enter a shared merge and are
  labeled direct-successor boundaries instead of being called exclusive. The
  walker has no mission, quest, action, or object allowlist and never reads OCR
  or manual order.
- The installed client applies server-supplied mission/quest identities and
  states one at a time. Current validated handlers do not expose a client-side
  successor selector.
- Binary-proven quest success can order a matching objective Story before a
  same-quest succeed action. It does not prove success occurred or select a
  later fork arm.
- Authored start actions remain definition evidence where the installed AOT
  dispatcher has no validated start producer.
- Server-placeholder conditions expose an explicit evidence boundary rather
  than being guessed from neighboring client data.
- Exact option-outcome dependencies are recovered generically by joining an
  authored DialogTree finish node or Timeline finish-number override to a
  nonnegative MissionRuntime `CheckTalkOptionFinish` operand. The installed
  binary and metadata are hash/body-pinned for import, FullSerializer reflected
  deserialization, producer, recorder, and consumer methods. FullSerializer
  creates reflected objects uninitialized and assigns only JSON-present fields,
  so an omitted `Int32 finishId` is admitted as runtime-default zero; malformed
  explicit values still fail closed. The installed selection path also proves
  that `NormalOptionData.index` is passed unchanged through the option handler
  and controller to `DialogTree.Continue`, where it selects the physical
  outgoing connection. `DialogTreeExOptionNode` edges remain in that physical
  list, so normal-option list ordinal and option/connection-count equality are
  not route evidence. The shared decoder uses only the serialized index (or
  binary-validated omitted-`Int32` zero), and never filename, suffix, layout,
  OCR, or override signals. `DialogManager.ShowOptions` also sets the
  hash-validated `DialogTreeOptionBase.doNext` field before selection, so an
  absent physical edge is not a terminal-choice signal. Across all 2,579
  original DialogTrees, 2,682 authored option nodes contain 4,403 normal
  options: 4,383 routes validate while 20 fail closed. Those 20 are now fully
  partitioned by original graph structure: seven options are unreferenced
  definitions without serialized graph identity, eight belong to five linked
  nodes with no outgoing edge, and five carry an out-of-bounds index on a
  partially connected node. Sixty-seven extra-option nodes validate the binary
  pattern; 77 unequal-count nodes are retained rather than categorically rejected.
  The mission-observed subset validates 1,199 routes in 434 files and rejects
  one out-of-bounds authored route. The installed `Graph.get_primeNode` returns
  the first serialized node and `DialogTree.OnGraphStarted` enters it when a
  current node is absent. A shared structural walker therefore validates exact
  connection identities and admits only finish nodes reachable from that prime
  node; it never reads dialog names, filename suffixes, editor layout, OCR, or
  overrides. Across the full typed corpus, 3,121 finish endpoints validate and
  69 fail closed. The mission-linked subset validates 622 endpoints and rejects
  15 across 478 original files. Timeline and DialogTree evidence are retained
  independently, so a Timeline no longer suppresses the corresponding original
  DialogTree definition. All 136 exact nonnegative MissionRuntime consumers are
  now covered: 35 have an exact option-to-objective route across 17 missions,
  while 101 are endpoint-only dependencies across 57 missions and do not claim
  a route or player choice. No exact consumer remains unresolved. Option IDs
  are localization values, not global branch identities: `dlg_sm2l1m1_3`
  reuses two IDs under distinct option nodes reached through different IfNode
  arms, so producer agreement is scoped by original node and option slot.
  Duplicate Timeline clips must agree within their runtime option scope. These
  rows prove an objective dependency, not player selection, dialog activation,
  server successor choice, or total Story-file order.
- Registered DialogTree and NpcProxy-consumer recovery is corpus-driven: core
  isolated Story targets join mechanically through `misc_dlg_` aliases, the
  current DialogId registry, exact hash-validated TextAssets, authored option
  routes and finish endpoints, exact `NpcProxyEx`/`NpcProxy` rows, typed
  LevelScript/native/object carrier censuses, and the installed binaries. The
  current definition path ignores the copied per-object definition fields for
  72 of 102 maintained rows. The NpcProxy pattern independently validates 54
  DialogTrees and 60 selected rows, including aliases and multi-proxy cases;
  all 44 formerly copied consumer declarations (48 rows) match it exactly and
  have been removed. Mission tracking is also corpus-driven: the complete
  active MissionRuntime root currently has 490 mission payloads and 839 typed
  `NpcProxyTrackingInfo` rows; 781 exact unfiltered rows qualify, while 58
  filtered rows stay outside this relation. The same proxy/level join recovers
  tracking context for 26 maintained dialog definitions without any copied
  tracking declaration. The broader Story builder qualifies 146 proxy contexts
  covering 210 configured dialogs in 82 missions. Each context carries its
  exact original source file and hash; 13 former per-dialog tracking blocks and
  the former one-proxy publication allowlist have been removed. This family
  is now classified by one general quest-graph rule rather than mission/proxy
  cases. Across the current 146 contexts it validates every candidate identity,
  predecessor, cycle boundary, MissionRuntime hash, and installed
  `GameAssembly.dll` hash; 13 contexts span sibling-exclusive fork arms or
  touch/feed an authored merge. The binary keeps `activeCondIndex` proxy-row
  selection separate from server-supplied quest-state identity, so the
  classifier exposes candidate chains, antichains, partial orders, forks, and
  merges without assigning a configured dialog to a quest or adding a branch
  selection/Story-order edge. Twenty registered configured dialog ids lack an
  exported Story definition; the mission-scope topology inventory retains them
  explicitly rather than dropping them from the Story manifest. This family
  retains 312 authored lines, 90
  validated option routes, and 68 prime-reachable
  finish endpoints; three unresolved option-node identities remain visibly fail
  closed. One transient row without a current
  `NpcProxyTable` identity fails closed with a bounded diagnostic. Internal
  DialogTree routes remain local structure and NpcProxy active-row selection
  remains a consumer relation; neither creates mission activation or
  cross-file order.

## LevelScript and native conclusions

- Exact native playback actions, event headers, predicates, and local control
  graphs are decoded from original LevelScript data with hash-pinned binary
  contracts.
- Teleport-completion correlation is now a corpus rule rather than a
  receiver-specific guess. Across all 4,512 current original StreamingAssets
  LevelScripts, 117 typed `LevelEvent_OnTeleportFinish` listeners carry 116
  distinct `actionId` filters. Exact action UID/text and raw-byte correlation
  finds no serialized producer for any filter; the one filter that also equals
  its own header UID is explicitly accounted as listener-owned, not a producer.
  The installed binary proves `OnTeleportFinish.Process` compares the authored
  filter with `TeleportParam.actionId` at runtime. This adds exact unresolved
  context for `radio_c13m2_10` and `radio_e1m8_1`, but no activation, ownership,
  branch, or order edge. Future candidates are discovered by the same typed
  event/filter scan, with no Story, mission, script, or filter allowlist.
  Producer recovery is now equally general: the installed-binary value-carrier
  audit derives a requested managed type's runtime layout, signature methods,
  inherited container paths, direct callsites, focused accesses, and stack-local
  initializers without content identities. For `TeleportParam` it finds nine
  fields, 15 signature methods, ten container paths, 13 direct callsites, and 23
  focused accesses. Each extended identity field has one exact zero-origin write
  plus one carrier-copy write; six direct local arguments are zeroed, three are
  forwarding/copy lanes, and the sole unknown local is a `PerformerFactory`
  consumer copy. `LoadFinishStep` reads `levelScriptId` and `actionId` but not
  `missionId`. No nonzero direct AOT originator is present; indirect/interface,
  reflection, XLua, and live-server production remain outside this bound.
- The active LevelScript overlay (`Persistent` over the matching
  `StreamingAssets` path) contains 230 validated `CheckTalkOptionFinish`
  consumers: 42 exact nonnegative finish ids and 188 any-finish checks. All 230
  now resolve through complete task maps, yielding 227 exact task identities
  with no bounded fragment remaining. The decoder does not add a payload branch
  per condition class: the current binary's root `GameCondition` formatter
  supplies union identity and member count, then one reusable backtracking
  decoder proves a unique sequence of self-delimiting `Param<T>` wire shapes
  against the condition dictionary key, objective envelope, and complete task
  map. Scalar interpretations with the same boundary remain opaque. A reusable
  string-collection Param shape covers collection-valued fields. All 227 tasks
  are authored type `None`, untracked, and automatic-check; 214 contain one
  condition and 13 retain multi-condition structure. The current binary
  validates the general lifecycle without object-specific ids: the typed
  server state is forwarded through LevelScriptManager, LevelScriptRuntime,
  and ScriptTaskRuntime; Processing walks the task conditions, installs the
  result-change delegate, activates/binds each GameCondition, and reports the
  exact level/script/task/condition identity. This proves reusable runtime
  semantics after server selection, not which task the server selected in a
  session. All 42 exact consumers join to a prime-reachable authored DialogTree
  finish endpoint; none lacks an original endpoint. Exact
  MissionRuntime finish matches publish 15 objective placements across 14 task
  rows and 13 missions, all from complete maps. Five
  any-finish objective placements across four missions accept an exact task
  outcome under the hash-locked native predicate, while 17 objective placements
  across five missions reference the same active LevelScript as eight task
  consumers. These remain context-only. One row, `c28m3`, also has an exact
  same-mission SubGame task carrier. A general minimal-object field-shape census
  over all 85,405 active structured files outside LevelScript definition
  families independently finds that same `c28m3` script/task/mission carrier
  and no typed-JSON carrier for the other 39 exact-finish task identities. The
  maintained prefix gate counts serialized files without reading them as JSON.
  A generic serialized-object pass now validates all 40 exact task identities
  (42 finish-condition rows) across 27 LevelData files: the complete member-22
  dictionary must place paired `lt:p`/`lt:mp` properties inside the exact
  script's `LevelScriptBriefData` entry. Independent whole-shell references
  resolve 20 task identities to one mission shell, retain 11 as shared, and
  leave nine shell identities unresolved. This attaches 21 authored consumer
  rows through LevelData plus the existing SubGame-owned row to 17 Mission
  Pipeline missions. The LevelData carrier proves persistent task-condition
  placement and shell context, not activation, quest ownership, or Story order.
  A third corpus-wide join now reads all 849 typed `NpcProxyTrackingInfo` rows
  across 588 proxies directly from the active original MissionRuntime overlay,
  then requires the same proxy's authored `NpcProxyEx` mission and a
  `WorldEntityRegistry.segmentIdGlobal` identical to the exact LevelScript id.
  It finds seven task-script contexts: six unique and one shared. Seven task
  consumer rows use the unique script-local shell tier; six corroborate the
  existing unique LevelData result, while `map01_lv002/200080000/f69e4698`
  refines the shared `sm1l2m2`/`sm1l2m3` whole shell to `sm1l2m3`. The shared
  `map02_lv002/22800280001` context remains ambiguous between `f1m20` and
  `sm2l6m1`. Mission Pipeline now attaches 23 authored consumer rows to 18
  missions. This segment join remains mission-shell context, not NPC or task
  activation, quest ownership, or Story order.
  The other 28 endpoint-to-task
  dependencies lack an exact MissionRuntime finish match; this is no longer an
  endpoint gap, but server selection and mission/task ownership remain
  unresolved. Every
  mission-to-script placement hash-matches the active `Persistent`-over-
  `StreamingAssets` source before publication. None of these tiers proves
  player choice, server successor selection, or Story order.
- Split/fan-out scheduling preserves sibling actions as parallel or unordered.
  Array/list position is never chronology.
- Parent-dialog activation uses the same corpus-wide typed control-path walker,
  including non-linear edges rather than a dialog-specific chain. The current
  audit validates 13 of 14 parent dialogs (15 of 16 embedded Story keys) across
  nine mission shells: four routes cross an unordered `Split` fan-out and one
  crosses a conditional `SwitchInt` case whose runtime selection is unobserved.
  The remaining `dlg_c13m3_7` has no native playback action. Its exact
  `NpcProxyEx` row instead co-identifies mission `c13m3`, the parent dialog, and
  proxy `andrew_map01_c13m3Safe`; that same proxy has one typed MissionRuntime
  tracking consumer in `c13m3_q#4`. This is mission configuration plus quest
  navigation context, not parent playback, activation, branch selection, or
  Story order.
- The NPC configuration join is corpus-wide and patch-sensitive. Installed
  metadata must expose the mission/dialog carrier, and mapped native bodies
  must prove the one-based active-row conversion, dialog output flow, and
  mission-conflict lookup before any row is published. No mission, quest,
  proxy, dialog, token, address, OCR, or override allowlist participates.
- The same 13-route audit now resolves every typed MissionRuntime tracking row
  through the maintained original MissionArea/NPC-proxy tables and tests its
  point against the exact event-selected serialized trigger shape. The general
  box/sphere rule yields 24 contained tracking rows on nine routes (23 distinct
  quest IDs). These are quest spatial candidates only: containment does not
  prove entry, activation, ownership, branch selection, or Story-file order;
  unsupported or multiply matching shapes fail closed.
- Four activation routes have no contained tracking point. Three have no
  MissionRuntime reference to their playback LevelScript; `e5m1_q#6` observes
  script `10100060000` reaching stage 1, but the trigger/dialog arm ends in an
  opaque server handoff and does not prove which server transition advances
  that stage. They remain activation-with-mission-shell evidence, not quest
  activation.
- Branch, IfElse, Switch, loop, and wait/outcome families retain active,
  inactive, non-Story, and playback-bearing arms separately. A branch only
  creates order when its runtime semantics and the relevant source-to-target
  path are both proven.
- Runtime-shadowed duplicate local ids use the validated active mapping while
  retaining the physical records as debug evidence.
- Post-playback `CallServer`, variable setters, and callback graphs are local
  control evidence. Parameters or callback labels do not supply a mission
  owner without a typed carrier.
- Exact receiver playback can be joined to its LevelScript, LevelData host,
  activation geometry, local gate, task protocol, and server-applied script
  state. Those facts still do not reveal the server-side reason for activation
  or a mission/quest owner.
- A corpus-wide typed shell join follows MissionRuntime
  `MissionAreaTrackingInfo.(sceneId, missionAreaId)` through
  `LevelBasicInfoTable.idNum` and the exact level-specific
  `MissionAreaTable.subDataParentId` to a root in the same validated LevelData
  member-22 dictionary as an unresolved receiver. Level scoping is mandatory:
  `c13_002` exists in both `map01_lv007` and `dung01_rdg002`, so an area-id-only
  join incorrectly attached the main `c13m2` mission to the dungeon shell.
  Across 95 receiver scripts the corrected join finds five unique contexts:
  `map01_lv007/2800100000` maps to `e3m6`, and four
  `dung01_rdg002` scripts map to `c13m2d5`; `c13m2` is excluded by its authored
  `map01_lv007` scene. Mission Pipeline publishes five shell placements with
  hashes for MissionRuntime, LevelBasicInfo, MissionArea, LevelData,
  LevelScript, installed binary, and metadata. This creates no ownership,
  activation, branch, or order edge; Story-name disagreements remain visible
  cross-context evidence rather than identity.
- `SameWithActive`, current-context ManualStart, SubGame interaction starts,
  active-phase receiver availability, and client active/start request paths
  are recovered as corpus-wide contracts rather than per-scene exceptions.
- Mission-name tokens, receiver registration, spatial proximity, and
  source-file co-membership remain non-owning context.

## Other accepted and bounded sources

- Shipped Lua can prove an exact playback call and, only when the same original
  row carries a mission/quest identity, an attachment. Case-only similarity is
  rejected.
- SubGame rows can provide exact interaction and bound-LevelScript context.
- Spawner and task topology can prove local progression only through typed
  authored relations.
- Narrative definitions, ReadingPopUp/RichContent rows, and black-screen audio
  metadata remain definition-only until an exact consumer is recovered. A
  `ShowUIReadingPopPanel` action carries its direct `_readingPopId`; it does not
  require a LevelData BriefData property host.
- The focused `e0m0` unresolved set is now source-bounded rather than attached
  by filename or position. `text_e0m0_1` has an exact
  `WorldEntityRegistry 8700020018/40001 -> int_mission_beacon` map interaction
  at `(278.377, 55.920, 651.378)`. Its complete embedded
  `LevelInteractiveData/25` record raises `readepitaph`, and the same script's
  exact `LevelEvent_OnCustomEvent(readepitaph) -> ShowUIReadingPopPanel`
  receiver carries direct id `text_e0m0_1`. This recovers the interaction
  trigger and playback route without a broad map re-export; no exact
  MissionRuntime/quest owner or mission-step order is yet proven. The trigger
  is 0.343 m in 3D from the `e0m0_q#10` tracking centroid (`进入过去`), while
  q9 and q11 are about 98 m and 143 m away. This is high-signal spatial
  context for q10, not a quest-ownership or Story-order edge.
  The targeted runtime-map layer now also aligns exact WorldEntityRegistry
  positions for the three active second-zipline transition producers:
  `cutscene_e0m0_2ndZiplineA` at
  `(-70.600, 60.492, -42.800)`, `B` at
  `(-21.070, 36.417, -17.940)`, and `CCamOnly` at
  `(-17.730, 66.267, 43.690)`. Their matching stage tags and retained-camera
  paths explain the relationship to legacy `_10`, `_11`, and `_12`, but do
  not make those legacy roots playback aliases or prove that they trigger.
  `cutscene_e0m0_1` has only a case-mismatched
  shipped-Lua call rejected by the case-sensitive native lookup;
  `cutscene_e0m0_10` through `_12` are legacy zipline definitions parallel to
  active transition assets without a recovered consumer, and `_11111` likewise
  has no current exact activator. Field observation confirms that radios
  `_9d5`, `_10`, and `_21` do play, and all of their decoded media exists
  (`_10`/`_21` use protagonist-gender `_f/_m` variants), so they are no longer
  treated as unused definitions. Their exact offline trigger carrier remains
  unrecovered: focused nearby Audio Timeline exports resolve only unrelated
  scene SFX. Current native recovery proves the general non-LevelScript
  `RadioTriggerZoneHandler.OnEnter -> mission gates/once flag ->
  GameAction.PlayRadio` route, but no authored zone instance has yet joined
  that route to these three ids. The complete current LevelScript Radio surface
  excludes all three. Its sole dynamic radio-id binding is
  `map01_lv006/3500060003: PlayRadio`; the exact getter chain resolves as
  `ListGetValueString(RandomLines)` against the matching `LevelScriptBriefData`
  to `radio_e2m7_9`, `_10`, `_11`, and `_16`. Which list index is chosen at
  runtime remains unobserved, but the bounded candidate set excludes every
  `e0m0` target. Streaming/DynamicStreaming/ExtendData contain no
  target-id occurrence; JsonData/Lua/Table occurrences are limited to
  RadioTable and AudioDialog definitions. The working
  `9 -> 9d5 -> 10 -> 21 -> tombstone` placement already matches
  `story_order.json`; it is not promoted to a strict serialized edge.
- The focused `e0m0` flow is now consolidated in
  `reports/story/recovery/e0m0_mission_flow.md`. The exact mission backbone is
  the unbranched `e0m0_q#1 -> ... -> e0m0_q#13` chain, while the apparent
  53-item Story order contains only 49 WebUI Story roots:
  `cutscene_e0m0_2ndZiplineC` is a LevelSequence display alias and
  `radio_e0m0_16_1/_2/_3` are battle-signal ids that play
  `radio_e0m0_16/_22/_23`. Boss dialogue is event-conditioned partial order,
  not a fixed sequence. Strong local ordering is currently limited to exact
  serialized paths such as `cutscene_e0m0_2 -> radio_e0m0_1`,
  `cutscene_e0m0_New14 -> radio_e0m0_8d8`, and the newly recovered
  `cutscene_e0m0_13 @ 7.75s -> TLCall_Summon_Cannon_1_Step_01 ->
  indie_dg002/8700040000 header 4 -> StopLevelSequenceAction ->
  radio_e0m0_8d4`; ending cutscenes 6/7/8 have exact
  individual playback paths but their cross-event 6 -> 7 -> 8 progression is
  still a working sequence, not one serialized control chain. The report lists
  every displayed key, trigger carrier, preload-only case, and definition with
  no current consumer.
- The current-CLI Story object-index join for the unresolved `e0m0` radios is
  complete. Hash-validated StreamingAssets and Persistent indexes cover
  1,394,047 object rows and retain exact component GameObject/Transform scene
  context plus boolean state fields. Exact scans found zero serialized scalar
  matches for `radio_e0m0_9d5`, `_10`, or `_21`; a second bounded scan also
  found zero matches across the three roots, eight line ids, their
  `au_radio_*` overrides, and `_f/_m` variants (35 exact values total).
  `RadioTable` still proves each row-to-`audioOverride` binding, and gameplay
  proves playback, but neither the complete Unity object surface nor the
  previously audited LevelScript/native constant surface identifies the
  producer. Keep the working sequence
  `radio_e0m0_9 -> radio_e0m0_9d5 -> radio_e0m0_10 -> radio_e0m0_21 ->
  cutscene_e0m0_tombstonecollapseCam`; its middle four relative edges remain
  manual observations, not serialized strict order.
- The installed Radio receiver is now decoded end to end. The shipped
  `Lua/Data/LuaScripts/LuaSystem/RadioSystem.lua` registers
  `MessageConst.SHOW_RADIO`, accepts a
  `GameAction.RadioRuntimeData`, looks up its `radioId` in `RadioTable`, and
  plays `radioSingleDataList` in authored list order; normal voiced rows submit
  each row's `audioOverride` to `VoiceManager.SpeakNarrative`. This proves the
  root -> line -> audio execution mechanism and explains why a Radio definition
  is not itself a trigger. It does not provide the missing root producer.
  `radio_e0m0_9d5`, `_10`, and `_21` all have equal priority 3 and both
  continuation flags false; none occurs in `AudioRadioContinueTable`. The
  receiver therefore cannot turn one of these roots into the next. Hearing all
  three requires three externally supplied `RadioRuntimeData` values (or an
  independently proven direct-audio bypass), and does not promote their
  observed order to a serialized edge.
- The current indirect playback surface is narrower. The installed XLua
  `BeyondGameplayActionsGameActionWrap._m_PlayRadio_xlua_st_` reads the Lua
  string argument and has four decoded direct call paths to the static
  `GameAction.PlayRadio`; `PlayRadioAndWait`, `PlayRadioOnEntity`, and
  `FlushAndPlayRadio` wrappers are likewise mapped. The complete 1,290-module
  shipped Lua corpus contains no target root id and no direct `GameAction`
  Radio playback call. Its only Lua `SHOW_RADIO` producers use a dynamic
  factory-interaction `forbidReason.radioId`, with no target literal. The
  complete current `GameAssembly.dll` direct-call census found exactly seven
  calls to `RadioRuntimeData..ctor`: the four `GameAction` Radio helpers,
  `Play3DRadio.GenRadioRuntimeData`, and two `FactoryUtil` building-lock
  checks. The two factory checks pass the lock-check output string as
  `radioId`, are gated by `needRadioNotify`, and close the same dynamic factory
  path seen in Lua; no mission, task, level, or `e0m0` constructor caller was
  found. This census covered 6,425,224 executable-section `E8` candidates. The
  same global scan over the five static `GameAction` Radio entry families found
  35 direct calls across 22 callers. The reproducible closure audit in
  `reports/story/recovery/radio_producer_closure_audit.md` classifies five XLua
  wrappers, five typed Action `Execute` methods, four NPC patrol callers, two
  interactive-narrative callers, one `RadioTriggerZoneHandler`, and five other
  native systems. Every direct caller now has a bounded current authored/runtime
  carrier, and none supplies the three target ids. `NarrativeComponent` obtains
  its content id from an interactive ParamBlackboard; the maintained LevelInteractiveData /
  ReadingPopUp join already covers that authored carrier, and none of the three
  target roots occurs in `ReadingPopUpTable`. Across current structured tables,
  the targets occur only in `RadioTable` and `AudioDialog`. They are also absent
  from both `StrIdNumTable.radio_id` and `real_radio_id_fixed`, closing the
  numeric Radio-id mapping as a hidden selector for these rows. A direct-field
  census of all 3,743 current `Proto.*` types found zero `radioId`, `timelineId`,
  or `storyId` fields, so normal typed protobuf delivery does not carry these
  roots; opaque bytes, dynamic maps, and native-private packets remain outside
  that bound. The 12 CN target voice variants have no Wwise Event bindings
  (`eventCount=0`), and their signed/unsigned `AudioDialog` integer keys have
  zero exact retained-scalar matches across the same 1,394,047 Unity objects.
  Those 12 int32 keys also have zero exact constant hits in the current
  `GameAssembly.dll` executable sections.
  The two shipped Lua `SHOW_RADIO` producers are now closed as current offline
  value sources rather than left as an unspecified `forbidReason` boundary.
  `Utils.isForbiddenWithReason` returns the base `ForbidParams`; the only
  subtype with a `radioId` is `ForbidParamsWithRadioReason`, whose current
  layout is `radioId:string` at `+0x18`. Metadata fixes
  `ForbidInteractFacBuilding=25`. The subtype string constructor has exactly
  one direct AOT caller, `ForbidParams.CreateForbidParams`, and its value-25
  branch passes a null string; the serialized LevelScript `SetForbid` action
  likewise passes null `forbidParams` to `ForbidSystem.AddForbid`. The complete
  indexes contain two serialized subtype instances, both in
  `ForbidByGameplayTagConfig` and both with an empty four-byte string payload;
  shipped Lua has two readers and zero subtype constructors. None of the 30
  active Gameplay IFix replacements touches Radio, Forbid, EventManager, or
  `SendGlobal`. This closes the current direct/native-default, serialized,
  shipped-Lua, and active-IFix form of that path; indirect runtime mutation or
  server-provided generic script data remains outside the bound.
  A normal Timeline/PostEvent bypass and a retained Unity identifier-key
  carrier are therefore also closed. The direct raw-voice surface is now
  bounded separately: the full AOT scan finds eight business calls to the two
  public `VoiceManager.SpeakNarrative` overloads, while all 1,290 shipped Lua
  modules contain ten calls across six modules. Exact scans of the three roots,
  eight line/base-audio ids, and 12 resolved voice variants still reach only
  `RadioTable` and `AudioDialog`. The six Reading/PRTS tables expose 1,628
  `overrideRadioId` fields but only three non-empty values, all unrelated to
  `e0m0`; the three native getter stubs have no direct AOT callers. The PRTS
  uses are Lua UI playback, and `RadioSystem` reaches target audio only after a
  Radio root was already supplied. The same complete Lua corpus has no dynamic
  `GameAction[...]`, managed reflection, `GetMethod`, `InvokeMember`,
  `DynamicInvoke`, or managed `Activator` call pattern. The metadata type
  `GameActionEnumInvokeMethod` has zero fields and only the standard delegate
  `.ctor`/`Invoke`/`BeginInvoke`/`EndInvoke` shape, so it is not a method-name
  dispatcher or authored Radio registry. The current installed
  `Gameplay.Beyond.patch.bytes` fixes 30 methods but none of the Radio receiver,
  wrapper, or playback methods. `GameAction.PlayRadio` is
  static, so there is no interface/virtual slot for this exact entry. The
  by-value `RadioRuntimeData` surface is now closed independently of its
  constructor: exact metadata has no other persistent carrier field, four
  parameter methods and two return methods, including three IFix wrappers.
  Their direct-E8 census has nine calls from seven callers. The concrete
  `EventManager.SendGlobal<RadioRuntimeData>` body is reached through one
  validated 0x38-byte ABI thunk; all eight thunk calls come from the four
  static GameAction playback helpers and the two Factory building-lock checks.
  The call sites read `Beyond.PredefinedEventKeys.SHOW_RADIO` at the exact
  registered field offset `+0x4a4`, closing the native-to-Lua event bridge.
  `FactoryBuildingPanelLock` has only `radio_e1m2_3d5`, `radio_e1m3_6`, and
  `radio_e5m2_3d2`, so that second producer family excludes the e0m0 targets.
  XLua and the current IFix payload are therefore available mechanisms, not
  producers of these three values; reflection/dynamic construction, a runtime
  patch or indirect call, server-origin `forbidReason.radioId`, and an
  indirect/non-indexed raw-audio path remain outside the closed corpus. Exact
  source-graph queries add only definition, line/audio,
  mission-grouping, actor, and manual/fallback-order relations for the three
  targets; they add no trigger or producer edge and therefore do not alter
  `story_order.json`.
- The maintained Timeline marker audit now scans both complete AnimeStudio
  object indexes: 1,394,047 objects contain 91 `RaiseLevelEventMarker`
  objects, 74 exact MarkerTrack/Timeline owners, and six exact event-name joins
  to LevelScript Story receivers. Exact `m_Time` values come from each marker
  object, not object order. Two `TLCall_PlayRadio` markers at 21.7333 seconds
  belong to `f_cutscene_e11m1_fire_end_Actor` and
  `m_cutscene_e11m1_fire_end_Actor`; both reach the same
  `radio_e11m1_22` receiver. This proves one reason a Story file appears many
  times in spatial/source views: distinct gender or authored Timeline variants
  can converge on one event receiver, and every occurrence is retained as
  provenance. It is not evidence that playback repeats. The e0m0 route above
  is the only current marker-to-Story join in `cutscene_e0m0_13`; Step02-06 and
  FreeRoam retain their exact 8.15-12.5167 second order but have no Story join.
  See `reports/story/recovery/timeline_level_event_marker_audit.md`.
- Project-authored WebUI fixtures are labeled and excluded from original-game
  chronology recovery.

The C35/Liino audio pass provides a useful trigger boundary. For
`dlg_c35m1_10`, `DialogTrunkPlayableAsset._trunkId` and the recovered
`dlgtl_c35m1_10_sub_1` Timeline establish an authored voice carrier and exact
line order; the same Timeline's Audio tracks separately establish authored SFX
placements. `RadioTable` similarly establishes Radio row -> line ->
`audioOverride` identity, and LevelScript decodes the generic `PlayRadio*`
action families. These are strong content/ownership relations, not proof that
the game reached the Director or executed the action. In particular,
`mission:c35m1 -> story:dlg_c35m1_10` is a WebUI grouping edge: the raw
`MissionRuntimeAsset/c35m1.json` has no direct dialog finish or LevelScript
binding for this scene.

The active Persistent-over-Streaming LevelScript overlay adds a separate C35
carrier, but not the missing Timeline activation. Four exact files,
`Persistent/Data/Json/LevelScriptData/map01_lv001/2100710037.json` through
`2100710040.json`, are each 843 bytes with a two-record control surface. Their
`actionList#1` root is a current-build `StartDialogAction` (`0x049e`, 15
serialized members, local id 3) carrying the tagged id `dlg_c35m1_dungeon`.
Their `headerList#1` is `LevelEvent_OnCustomEvent` (`0x1052`/tag `0x0052`)
with `nextId=3` and event keys `Enter_c35m1`, `Enter_c35m2`, `Enter_c35m3`,
and `Enter_c35m4` respectively. This proves the authored local event ->
StartDialogAction -> dialog-id edge. It does not prove that any of those
events fired, and an exhaustive structured-export string scan finds no second
serialized producer for the four `Enter_*` keys. The quest's
`EntityTrackingInfo.scriptId=710037, entitySlotId=40001` is a useful lead:
`2100710037 % 100000000 == 710037`, but the current WorldEntityRegistry has no
matching row, so the maintained resolver cannot yet prove that tracking target
owns this LevelScript.

The matching Persistent LevelData asset,
`map01_lv001/map01_lv001_lv_data_sub_c35_1d4.json`, contains one validated
`LevelScriptBriefData` dictionary covering global ids `2100710037` through
`2100710041`. The `2100710037` row has `levelScriptType=1`, `maxStage=1`, no
properties, and no world-entity references; the container has no mission,
Story, dialog, or Timeline identity. The target LevelScript itself decodes
`startType=Manual` with zero serialized trigger-volume rows. These fields
explain why the exported bytes do not yield a player-entered spatial producer:
they are authored activation configuration, not proof that the runtime invoked
the script.

No `dlg_c35m1_10` or `dlgtl_c35m1_10_sub_1` identity occurs in these
LevelScript action fields. Until a `map01_lv001`/LevelScript action, event
producer, or another native receiver is joined to the Timeline, C35 remains
`mission-associated/runtime-activation-unresolved`; the four
`Enter_* -> dlg_c35m1_dungeon` rows should be retained as a distinct
custom-event dialog route rather than conflated with scene 10. The existing
dialog index also keeps the distinction explicit: `dlg_c35m1_dungeon` has no
recovered lines or Timeline, while `dlg_c35m1_10` owns
`dlgtl_c35m1_10_sub_1`. The existing e11m3 `mission_story_context` chain is
the comparator for the stronger evidence that is still missing here.

The generated CN audio trigger shard now projects the scene-10 DialogTrunk
schedule as 19 `dialogTimeline` rows. Each row preserves the exact line id,
actor, timeline id, start/duration, and existing playable `au_dlg_c35m1_10_*`
FLAC; all 19 resolve to media, but all remain
`dialogTimelineRuntimeExecutionNotObserved`. This establishes the authored
voice placement and media meaning without changing the unresolved mission or
Timeline activation boundary above.

The same `dlgtl_c35m1_10_sub_1_Audio` asset has six serialized Audio tracks
with 21 exact clip placements and 18 unique SFX keys. The CN semantic surface
now exposes each placement's start/duration and the raw `AudioDlgEventPlayable`
controls; all 18 keys are absent from the current Wwise/Event and media
indexes, so their rows intentionally have no playable `src`. Their authored
names describe create/fall/landing, shimmer/wink, flight/whoosh, grass
footsteps, Liino fly/pat-head/surprise, NPC fear/shake, Endmin landing, and
lens-zoom light. `au_sfx_dlg_foley_c35m1_10_liino_pathead` is the only
scene-10 placement marked `isCue=1`; that still does not resolve its cue or
prove Timeline/Director execution.

The playable-type audit keeps this SFX lane separate from voice: 20 of the 21
clips use `AudioDlgEventPlayable` and `wink_02` uses `AudioEventPlayable`.
Both carry `_audioEventKey`-style SFX fields and neither carries a dialog
`_trunkId` or `playVoice` flag. The voice lane is instead
`Actor -> Common -> Dialog Trunk`, with 19 `_trunkId` line placements and two
`DialogLipSyncPlayableAsset` tracks using `playVoice=1`; the serialized Dialog
Voice Audio Track has no clips. `DialogAudioEventPlayableAsset` found in a
different timeline extract uses an `audioEvent._id` shape and is not evidence
for C35. Thus a matching `au_sfx_*` name is a Timeline SFX identity, not a
voice trigger or a lifecycle hook.

An exact-key audit across the comparable CN Wwise indexes in
`export_full_1d3d2`, `export_full_1d4`, and the current `export_full` finds
none of the 18 C35 scene-10 SFX keys. Those historical indexes do contain
other `au_sfx_dlg_*` names, so this is a C35-key absence rather than a claim
that the whole dialog-SFX namespace was never exported. The current semantic
shard therefore keeps these keys as authored Timeline requests with no
decoded Wwise media, and records the two static playable contract ids
(`timelineStringEventKey.audioDlg` / `timelineStringEventKey.audioEvent`) for
the 20/1 carrier split. The remaining missing link is still the runtime
Timeline evaluation and Wwise request, not a justified synthetic media join.

The C35 scene root also explains how this child audio Timeline is intended to
enter playback. The root `CutsceneRootComponent` stores
`_timelineName=dlgtl_c35m1_10_sub_1` and `_director` resolves to root
PlayableDirector PathID `63140722070379897`, whose TimelineAsset is the root
Story asset PathID `-2466791841398753755`. Its `Audio` ControlTrack has one
`ControlPlayableAsset` clip (`0.0s`, `180.583333s`) with
`autoBindingPath=Audio`, `updateDirector=1`, and `active=1`; this binds the
child `Audio` GameObject and PlayableDirector PathID `79300700487540089` to
the SFX TimelineAsset PathID `6744480576528724800`. The root-to-child
relation is exact serialized composition, while root activation, child
Director evaluation, and Wwise posting remain unobserved.

The matching current-build native audit now gives the child Timeline a typed
evaluation contract. For the 20 `AudioDlgEventPlayable` clips,
`ProcessFrame` calls `ShouldPlay`, `_DoPlayEvent`, and the conditional
`_TrySeek`/`_TryStop` paths; manual pause calls `_DoPlayStopEvent`, and graph
stop calls `_TryStop`. The one `AudioEventPlayable` clip has the parallel
`OnBehaviourPlay -> ShouldPlay` path and graph-stop cleanup including
`_TryPostExitEvent`. This explains when an already-evaluated clip can request,
seek, or stop its authored key, but it does not establish root activation,
Director evaluation, the actual Wwise `PostEvent`, or audible output for C35.
In the current native body, `_DoPlayEvent` stops at `_GetAudioObjId`, callback
construction, and IFix/indirect targets rather than a direct `PostEvent` edge;
`_TryStop` likewise has no direct `StopPlayingID` edge. The remaining cut is
therefore specifically the IFix/indirect runtime target and live execution, not
the serialized carrier or the managed Timeline lifecycle.
The bounded native evidence is recorded in
`reports/story/recovery/audio/timeline_audio_runtime_gameassembly.md`.

The same scene now has two additional, separate dialog-lifecycle hooks from
`AudioDialogCustomEventTable`: `dlg_c35m1_10.postEnterEvents[0]` is the exact
uint32 Event `0x4cd598ce` (authored signed value `1289066702`) and
`preExitEvents[0]` is `0xcd4ea851` (authored signed value `-850483119`). The
static `AudioGameplayStatusSystem` metadata connects these fields to
`_OnPostEnterDialog` and `_OnPreExitDialog`, with pending/preload scheduling
methods visible in the same type. Both current Wwise Event objects have no
decoded media leaf, so these hooks do not explain the 18 Timeline SFX keys or
prove that scene 10 dispatched either lifecycle event during play.

## Evidence rules

Accepted chronology requires a typed authored or validated runtime relation,
for example:

- quest predecessor or same-quest succeed lifecycle;
- exact DialogTree continuation or decoded option route;
- exact LevelScript playback control path with validated scheduling semantics;
- proven spawner/wave progression.

Keep as non-ordering context:

- mission-state dependencies without a playback/ownership join;
- source co-membership and related original files;
- registration, preload/remove/override actions, or callback labels;
- receiver/level scope without a mission bridge;
- definition-only media or text.

Reject as proof:

- filename or numeric suffix order;
- file, list, registration, or code-address order;
- OCR or manual order;
- spatial proximity;
- gameplay observation without an original-data carrier.

## Highest-value remaining gaps

1. Continue the three unresolved `e0m0` radios only through an exact producer
   of the `RadioRuntimeData.radioId` entering `MessageConst.SHOW_RADIO`, or a
   direct audio submission path. The receiver, complete Unity object index,
   4,581 active-overlay LevelScripts (including the resolved sole dynamic Radio
   candidate set), targeted VFS bytes, direct native constants, shipped Lua
   callers, all 22 direct static-entry callers, all direct AOT
   `RadioRuntimeData` constructor callers, all six by-value carrier methods,
   the validated `SendGlobal<RadioRuntimeData>` ABI thunk and its eight calls,
   the exact `SHOW_RADIO +0x4a4` event-key load, the eight native plus ten shipped-Lua
   direct `SpeakNarrative` calls, all Reading/PRTS override fields, and the
   current IFix fixed-method set, and the exact
   `ForbidInteractFacBuilding -> ForbidParamsWithRadioReason.radioId` native,
   serialized, Lua, and active-IFix value path are closed for all three
   root/line/audio identifiers. Continue only through a dynamically
   constructed/reflected value outside shipped Lua, indirect/native runtime
   mutation or server-provided generic script data outside the reviewed typed
   surfaces, or an indirect/non-indexed raw AudioDialog/media submission path.
   Do not
   repeat static string, AssetMap, spatial,
   interface-slot, XLua-registration, current-IFix, direct-constructor,
   direct-static-entry, fixed-numeric-id, typed-protobuf-radio-id,
   Unity-object-AudioDialog-key, direct-SpeakNarrative, Reading/PRTS-override,
   or code-address scans unless the original corpus changes.
2. Recover a typed mission/quest owner for the 156 unlinked Story files that
   already have exact native playback, especially repeated LevelScript
   receiver families. Five receiver scripts now have exact level-scoped typed
   mission-shell context and all five unions are unique, but none supplies the
   missing activation or Story-ownership selector.
3. Resolve the remaining ambiguous LevelData mission shells with an independent
   typed server-selection or mission-owner carrier. The LevelData census still
   retains 11 shared and nine unresolved identities, but the NpcProxy segment
   tier now refines one shared task script to `sm1l2m3`; ten shared identities
   therefore remain unresolved at the task-owner tier. The exact
   member-22 task-progress boundary is complete for all 40 task identities, but
   28 authored endpoint-to-task dependencies still lack an exact
   MissionRuntime finish match. Complete task maps, client lifecycle, authored
   DialogTree endpoints, and original LevelData carrier files are recovered.
4. Find any client-visible carrier for server-side mission/quest successor
   selection or LevelScript activation policy. Current state/update packets do
   not co-carry Story ownership. Do not repeat LevelScript UID/name searches for
   teleport-finish filters unless the original corpus changes: all 116 current
   filters are listener-owned only. The remaining useful boundary is the
   runtime producer of `TeleportParam.actionId` is now closed across the direct
   AOT carrier/callsite surface. Continue only through an exact indirect,
   interface, reflection, XLua, live-server, or different typed selector path
   that co-carries mission/quest identity; do not add object-specific producer
   exceptions.
5. Continue external-result recovery only through exact typed producer data.
   The shared phase router, defaults, nine override sites, nine direct native
   calls, and current arm coverage are complete for all 1,290 shipped Lua
   files. The next useful evidence is a bounded value source for the 35 dynamic
   indexes or an exact indirect/interface/reflection/XLua/native producer for
   the 14 arms with no current shipped producer. Do not infer those arm values
   from target shapes, authoring proximity, OCR, or per-panel exceptions.
6. Improve within-mission order through strong relations. Do not turn the
   current sparse partial order into a total order by heuristic sorting.
7. Revisit option gaps only when new runtime route evidence appears; most
   no-route rows are single-option acknowledgements or already bounded
   cosmetic/shared definitions. The 20 corpus-level rejected normal-option
   routes are structurally classified; revisit them only if a new original
   connection or native fallback appears. Do not repair them with positional
   replication or object-specific exceptions.
The current source-only gap queue ranks actionable isolated scenes by mission.
Use it as a work queue, not as a proposed Story order.

## Maintained commands

```bat
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\story_recovery\build_source_story_gap_queue.py --language CN
python scripts\story_recovery\build_timeline_embedded_story_runtime_audit.py
python scripts\story_recovery\build_timeline_level_event_marker_audit.py
python scripts\story_recovery\build_radio_forbid_producer_audit.py
python scripts\story_recovery\build_dialog_finish_branch_audit.py --publish
python tools\endfield_source_graph.py story STORY_KEY
python tools\endfield_source_graph.py issues --limit 20
```

Batch recovery edits and use focused tests/probes during the batch. Run the
canonical pipeline at the batch boundary before publishing generated data or
declaring counts final.

## Maintained reports

```text
reports/story/build/mission_pipeline_story_binding_coverage_CN.md
reports/story/build/mission_timeline_recovery_CN.md
reports/story/build/narrative_videos_CN.md
reports/mission_order/source_story_partial_order_CN.md
reports/mission_order/source_story_order_cross_reference_CN.md
reports/mission_order/source_story_gap_queue_CN.md
reports/story/recovery/native_receiver_activation_frontier.md
reports/story/recovery/dialog_finish_branch_audit.md
reports/story/recovery/protocol_registry_audit.md
reports/story/recovery/timeline_embedded_story_runtime_audit.md
reports/story/recovery/timeline_level_event_marker_audit.md
reports/story/recovery/radio_forbid_producer_audit.md
```

Generated reports are the current inventory and hash record. This memory topic
keeps only stable conclusions, evidence boundaries, commands, and the
highest-value queue.
