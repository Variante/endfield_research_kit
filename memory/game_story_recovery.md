# Game Story recovery

## Current status

The Story builder reconstructs dialog, radio, SNS, cutscenes, options, inline
media, localized reference links, mission grouping, and an evidence-typed
partial order. The browser is useful for research, but it does not claim a
complete canonical playthrough.

Current CN headline coverage from the maintained reports:

- 490 pipeline missions and 5,563 unique Story files;
- 4,236 connected files (76.1%);
- 4,457 files with at least one normalized trigger/context route (80.1%);
- 1,327 unlinked files, including 156 with exact native playback but no
  mission/quest activation bridge;
- 1,524 strong source-only edges across 8,877 candidate scene placements;
- 0 cyclic components;
- 3,845 of 249,695 possible within-mission pairs proven comparable (1.54%).

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
- Exact DialogTree conditionals, branch nodes, and IfNodes retain all decoded
  arms and polarity. They describe local selection unless a typed cross-Story
  continuation is independently proven.
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
  metadata remain definition-only until an exact consumer is recovered.
- Project-authored WebUI fixtures are labeled and excluded from original-game
  chronology recovery.

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

1. Recover a typed mission/quest owner for the 156 unlinked Story files that
   already have exact native playback, especially repeated LevelScript
   receiver families. Five receiver scripts now have exact level-scoped typed
   mission-shell context and all five unions are unique, but none supplies the
   missing activation or Story-ownership selector.
2. Resolve the remaining ambiguous LevelData mission shells with an independent
   typed server-selection or mission-owner carrier. The LevelData census still
   retains 11 shared and nine unresolved identities, but the NpcProxy segment
   tier now refines one shared task script to `sm1l2m3`; ten shared identities
   therefore remain unresolved at the task-owner tier. The exact
   member-22 task-progress boundary is complete for all 40 task identities, but
   28 authored endpoint-to-task dependencies still lack an exact
   MissionRuntime finish match. Complete task maps, client lifecycle, authored
   DialogTree endpoints, and original LevelData carrier files are recovered.
3. Find any client-visible carrier for server-side mission/quest successor
   selection or LevelScript activation policy. Current state/update packets do
   not co-carry Story ownership. Do not repeat LevelScript UID/name searches for
   teleport-finish filters unless the original corpus changes: all 116 current
   filters are listener-owned only. The remaining useful boundary is the
   runtime producer of `TeleportParam.actionId` (or another typed selector that
   co-carries mission/quest identity).
4. Resolve source-bounded parent-dialog and Timeline placements only when a new
   exact producer/consumer or mission foreign key appears.
5. Improve within-mission order through strong relations. Do not turn the
   current sparse partial order into a total order by heuristic sorting.
6. Revisit option gaps only when new runtime route evidence appears; most
   no-route rows are single-option acknowledgements or already bounded
   cosmetic/shared definitions. The 20 corpus-level rejected normal-option
   routes are structurally classified; revisit them only if a new original
   connection or native fallback appears. Do not repair them with positional
   replication or object-specific exceptions.
7. Republish the StreamingAssets object-index commit marker only through a
   current-CLI Story carrier refresh. The surviving merged outputs and worker
   parts still hash-match their last valid report and the installed-data
   fingerprint is unchanged, but the current AnimeStudio implementation hashes
   differ from that producer; copying the old marker would violate provenance.

The current source-only gap queue ranks actionable isolated scenes by mission.
Use it as a work queue, not as a proposed Story order.

## Maintained commands

```bat
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\story_recovery\build_source_story_gap_queue.py --language CN
python scripts\story_recovery\build_timeline_embedded_story_runtime_audit.py
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
```

Generated reports are the current inventory and hash record. This memory topic
keeps only stable conclusions, evidence boundaries, commands, and the
highest-value queue.
