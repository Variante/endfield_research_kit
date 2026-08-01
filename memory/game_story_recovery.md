# Game Story recovery

## Current status

The client supports a useful evidence-backed partial order, not one complete
canonical scene list.

Latest CN reports:

| Metric | Current |
| --- | ---: |
| Pipeline missions | 493 (490 MissionRuntime + 3 Story-only recovery shells) |
| Unique Story files | 5,282 |
| Connected files | 4,174 (79.0%) |
| Files with a normalized trigger/context route | 4,395 (83.2%) |
| Unlinked files | 1,108 |
| Unlinked files with exact native playback | 155 |
| Ordered mission graphs | 487 |
| Candidate scene placements | 8,876 |
| Strong / supported / weak edges | 1,480 / 834 / 2,630 |
| Source-comparable scene pairs | 3,762 / 249,651 (1.51%) |
| Cyclic components | 0 |
| Exact nested DialogTree containments | 30 across 29 child files |

Persistent `MissionRuntimeAsset` is the effective authored corpus only when it
contains the complete StreamingAssets filename set; otherwise builders use the
whole StreamingAssets corpus. The current roots share 980 filenames and differ
in five payloads.

## What is recovered

- Mission and quest graphs, predecessor relations, forks, and merges.
- Story cards for dialog, radio, SNS, cutscenes, black screens, and remote
  communication.
- Typed LevelScript, DialogTree, Timeline, FMV, quest-state, interactive, and
  selected runtime receiver evidence.
- Exact native control paths for Split, If/Else, Switch, Branch, playback, and
  many event families.
- 296 native branch groups and four native convergences, kept as a partial
  graph instead of flattened into a guessed file list.
- 368 strict option-route groups covering 767 option arms and 1,597 branch
  lines.
- Source-only graph generation with zero cycles and explicit unknown pairs.
- 180 of 188 narrative-video references attached across 53 Story keys.

The current main-story isolated-scene queue is source-bounded: all 586 core
isolated rows are now either closed by exact native/runtime/definition evidence
or deferred after current-build offline carrier exhaustion; none remain broadly
actionable. The latest batch closed the last two broad main-story quest
co-memberships as explicitly non-owning diagnostics and exhausted all eight
`a1m5` definition/branch rows. `e10m3d5_q#7` tracks the exact doctor proxy and
its mission-bound `dlg_e10m3_2` row, but its server placeholder exposes no
playback or completion carrier. `e2m8_q#5` reads `CarParked` from exact
`getterList#2`; the three Story calls in that LevelScript are separate action
records. Neither case creates a quest-to-Story or order edge.

`dlg_a1m5_5` is exact authored branch context rather than dead standalone text:
registered `dlg_a1m5_2` contains its two trunks behind a no-bypass seven-way OR
over completed quests `q#4`, `q#5`, `q#8`, `q#10`, `q#12`, `q#14`, and `q#16`.
Mission Pipeline attaches that source file and branch context, while retaining
the boundary that it does not identify one unique trigger or mission-relative
chronology. The seven `text_a1m5_*` files remain exact ReadingPopUp/RichContent
definitions with no recovered activator.

The seven `text_a1m9_*` judge-note files are now closed to the same strict
boundary. Original `ReadingPopUpTable` rows `rp_text_a1m9_1` through
`rp_text_a1m9_7` each target one exact RichContent payload, but exact searches
of MissionRuntime, typed LevelScript/LevelData interactive carriers, and both
current object indexes find no activator. The current structured export has no
Lua corpus, so Lua is a reopen condition rather than claimed negative evidence.
This removes seven rows from the event queue without adding ownership or order
edges.

The next binary-first event batch closes five more actionable rows without
inventing chronology. `radio_a1m6d1_1` plays on the exact local
leader-enter-trigger path in LevelScript `22800970016`; typed MissionRuntime,
NpcProxyEx, and WorldEntityRegistry joins place that authored segment shell in
mission `a1m6d4`, not the nominal `a1m6d1`, and do not select one quest or
relative order. `dlg_a1m6d5_8` is the exact `type_id` of the interactive tracked
by `a1m6d5_q#4`; this proves a client navigation target, not playback.
`text_a1m6d5_1` is an exact ReadingPopUp/RichContent definition without a
recovered activator. `dlg_a1m7_2` and `dlg_a1m7_12` have exact DialogText rows,
no DialogId/DialogTree/Timeline/audio consumer, and no recovered carrier;
`dlg_a1m7_2` has three exact DialogOption definitions, but no original route
graph. Mission Pipeline exposes these files and boundaries.

The remaining nine event rows are now source-bounded too. Exact typed
MissionRuntime tracking attaches `sns_a1m1_1` and `sns_a1m13_1` to `q#1` in
their nominal missions, but `SnsTrackingInfo` is navigation context rather
than playback. The registered `dlg_a1m4_1` DialogTree's exact prime-node paths
reach both `dlg_a1m4_2` trunks; the quest observes only parent-dialog
completion, so activation and inter-file chronology remain unresolved.
`radio_a1m6d1_2`, `radio_a1m6d2_1`, and `radio_a1m6d3_1` are exact one-line
RadioTable definitions whose audio ids are absent from current AudioDialog and
whose audited native/original-data surfaces expose no activator. `dlg_a1m2_4`
is registered and selectable through an empty-mission NpcProxyEx row;
`dlg_a1m11_3` is text/option-definition only. `sns_a1m8d1_1` has a complete
20-node internal content graph and six exact option routes, but no recovered
mission activator. These closures create no guessed ownership or order edge.
Both main-story and event core-isolated queues now have zero actionable rows.

The four-file `a1m8d3` event frontier is closed without using OCR or manual
order as evidence. Original `dlg_a1m8d3_2` DialogTree connections place
`black_a1m8d3_1_001` exactly after `dlg_a1m8d3_2_009` and before `_010`; this
is line-level containment, not a complete file-order edge. Original LevelScript
segment `10100620005` reaches `black_a1m8d3_2` through an exact
leader-enter-trigger to `NarrativeBlackScreenAction` path and is the exact
global segment of tracked proxy `liaowuhen_map02_v1d2d0_005`, proving only
mission-shell playback context. `dlg_a1m8d3_2` and `radio_a1m8d3_1` remain
hash-locked runtime definitions without recovered activators; their current
audio ids are absent from `AudioDialog`. Mission Pipeline exposes all four
boundaries and keeps the mission score at zero.

The 13-file `gm02m2` major-mission frontier is now source-bounded as well.
Exact original tables retain four DialogId-registered roots with 16
DialogText lines and nine DialogOption definitions, plus nine RadioTable roots
with 15 lines. None has current AudioDialog membership. The four dialogs have
no DialogTree TextAsset, Timeline membership, NpcProxyEx consumer, typed
MissionRuntime/LevelScript carrier, exact GameAssembly root token, or typed
object-index carrier; all 13 keys are in the current hash-locked no-candidate
carrier audit. The two multi-choice groups remain visible with their exact
option ids, but their destinations and file chronology are unresolved and no
longer scored as an unsearched runtime-route surface. Because `gm02m2` has no
MissionRuntimeAsset, Mission Pipeline now publishes an explicit zero-node,
zero-edge Story-only recovery shell (also used for `e5m4` and `e5m5`) instead
of hiding the attachments in a global overlay. This lowers major actionable
core-isolated rows from 213 to 200 without creating ownership or order edges.

The 12-file actionable `gm01m22` frontier is now fully source-bounded, reducing
major-mission actionable core-isolated rows to 179. Exact MissionRuntime meta
attaches `dlg_gm01m22_1` to the mission-accept interaction at
`jite_map01_005`; this proves mission ownership and accept-phase placement, not
a relative file edge. The registered parent `dlg_gm01m22_hapo` has exact
prime-reachable typed carriers for `dlg_gm01m22_6` and `_8`, while quest 27
observes completion of the parent; the parent activator remains unknown.
Original DialogTree connections recover `_6` option group 3 as a three-way
split, `_8` group 6 as a two-option convergence on line `_019`, and `_8` group
9 as a three-way split. Seven other dialogs/radios, `sns_gm01m22_2`, and
`text_gm01m22_5` remain exact current-build definitions without a recovered
activator; exact UTF-8/UTF-16 root tokens are absent from the current
GameAssembly. Mission Pipeline displays all eleven definition boundaries,
the internal routes, the accept attachment, and both parent-carrier contexts.

Manual order, OCR, filenames, table order, numeric suffixes, and gameplay
observation are comparison evidence only. They never promote an original-data
ownership or chronology edge.

## Remaining gaps

1. **Mission ownership:** 155 Story files have exact native playback but lack a
   mission/quest activation bridge. The unresolved surface is organized under
   161 runtime receiver nodes and 185 receiver-to-Story placements.
2. **Black screens:** 65 remain unassigned. Most are definition-only or lack a
   current-build playback consumer; five have playback but no static owner.
3. **Main/event story:** no core-isolated scene or strict quest-attachment gap
   remains actionable in either current source-bounded queue; seven broad
   main-story co-memberships remain visible as non-owning diagnostics.
4. **Option routes:** three actionable multi-choice groups lack any current installed
   DialogTree, Timeline, MissionRuntime, LevelScript, VFS, or Lua consumer.
5. **Narrative video:** three placement groups remain unresolved:
   `cs_video_e1m3_3`, `remotecomm_e1m2_2`, and `remotecomm_e1m2_3`.
6. **Total ordering:** most scene pairs are unknowable from current static
   evidence. A display order must remain separate from source proof.

The highest-value missing source is a serialized server/runtime registry that
contains both LevelScript and mission/quest identity. Repeating existing
LevelScript, DialogTree, Timeline, teleport, proxy, or local carrier scans is
unlikely to close the remaining ownership gap without changed inputs.

Next work should continue the same binary-first audit with the highest-ranked
real major-mission frontier (`gm02m3`, 10 actionable core-isolated files), then
the five character-mission quest-attachment gaps. Reopen a
deferred row only when a new typed producer/consumer or changed source hash
supplies an ownership or order edge.

## Evidence rules

Accepted chronology requires a typed authored relation such as quest
predecessors, exact DialogTree continuation, decoded option routes, exact
LevelScript playback control paths, or proven spawner progression.

Keep as non-ordering context:

- source co-membership;
- native registration;
- mission-state dependencies;
- preload/remove/override actions;
- definition-only media;
- receiver or level scope without a mission bridge.

Reject as proof:

- filename and suffix order;
- file/list/code-address order;
- OCR or manual order;
- spatial proximity;
- observed gameplay without an original-data carrier.

## Maintained reports

```text
reports/story/build/mission_pipeline_story_binding_coverage_CN.md
reports/mission_order/source_story_partial_order_CN.md
reports/mission_order/source_story_gap_queue_CN.md
reports/story/recovery/native_receiver_activation_frontier.md
reports/story/build/narrative_videos_CN.md
```

Useful commands:

```bat
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
python tools\endfield_source_graph.py story STORY_KEY
python scripts\story_recovery\build_source_story_gap_queue.py --language CN
```

Treat report counts as current truth; this note records only the stable
interpretation and highest-value gaps.
