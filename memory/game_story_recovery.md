# Game Story recovery

## Current status

The client supports a useful evidence-backed partial order, not one complete
canonical scene list.

Latest CN reports:

| Metric | Current |
| --- | ---: |
| Pipeline missions | 490 |
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

The current main-story isolated-scene queue is source-bounded: all 588 core
isolated rows are now either closed by exact native/runtime/definition evidence
or deferred after current-build offline carrier exhaustion; none remain broadly
actionable. The latest eight-row batch covered `black_e7m1_3`, `sns_e1m9_1`,
four radio definitions, `text_e8m4_1`, and `dlg_e5m0d5_1`. Exact current-game
carriers are attached in Mission Pipeline. For `dlg_e5m0d5_1`, the registered
DialogTree owns internal Timeline `dlgtl_e5m0d5_1_sub_1` and its 14-line order,
but no mission activator or mission-relative order was found. For
`radio_e1m5_3d5`, exact LevelData proximity to `e1m5_q#8` remains explicitly
non-owning and non-ordering.

Manual order, OCR, filenames, table order, numeric suffixes, and gameplay
observation are comparison evidence only. They never promote an original-data
ownership or chronology edge.

## Remaining gaps

1. **Mission ownership:** 155 Story files have exact native playback but lack a
   mission/quest activation bridge. The unresolved surface is organized under
   161 runtime receiver nodes and 185 receiver-to-Story placements.
2. **Black screens:** 65 remain unassigned. Most are definition-only or lack a
   current-build playback consumer; five have playback but no static owner.
3. **Main story:** no core-isolated scene remains actionable. Two strict
   quest-attachment gaps remain: `e10m3d5_q#7` and `e2m8_q#5`.
4. **Option routes:** five multi-choice groups lack any current installed
   DialogTree, Timeline, MissionRuntime, LevelScript, VFS, or Lua consumer.
5. **Narrative video:** three placement groups remain unresolved:
   `cs_video_e1m3_3`, `remotecomm_e1m2_2`, and `remotecomm_e1m2_3`.
6. **Total ordering:** most scene pairs are unknowable from current static
   evidence. A display order must remain separate from source proof.

The highest-value missing source is a serialized server/runtime registry that
contains both LevelScript and mission/quest identity. Repeating existing
LevelScript, DialogTree, Timeline, teleport, proxy, or local carrier scans is
unlikely to close the remaining ownership gap without changed inputs.

Next work should trace the two remaining main-story quest gaps through exact
MissionRuntime conditions, native receivers, and any changed installed-game
registries, then continue the same binary-first audit into the highest-ranked
event and major-mission isolated scenes. Reopen a deferred row only when a new
typed producer/consumer or changed source hash supplies an ownership or order
edge.

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
