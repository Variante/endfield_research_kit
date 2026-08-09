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
  one out-of-bounds authored route. The current corpus yields 35 exact
  option-to-objective dependencies across 17 missions, with 65 default-backed
  DialogTree producer rows and 101 exact consumers still unresolved. Option IDs
  are localization values, not global branch identities: `dlg_sm2l1m1_3`
  reuses two IDs under distinct option nodes reached through different IfNode
  arms, so producer agreement is scoped by original node and option slot.
  Duplicate Timeline clips must agree within their runtime option scope. These
  rows prove an objective dependency, not player selection, dialog activation,
  server successor choice, or total Story-file order.

## LevelScript and native conclusions

- Exact native playback actions, event headers, predicates, and local control
  graphs are decoded from original LevelScript data with hash-pinned binary
  contracts.
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
   receiver families.
2. Find any client-visible carrier for server-side mission/quest successor
   selection or LevelScript activation policy. Current state/update packets do
   not co-carry Story ownership.
3. Resolve source-bounded parent-dialog and Timeline placements only when a new
   exact producer/consumer or mission foreign key appears.
4. Improve within-mission order through strong relations. Do not turn the
   current sparse partial order into a total order by heuristic sorting.
5. Revisit option gaps only when new runtime route evidence appears; most
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
