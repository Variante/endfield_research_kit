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

- 434 missions and 7,618 candidate Story scenes;
- 1,716 accepted strong scene edges;
- 1,083 transitively reduced component edges;
- 4,903 comparable pairs out of 202,621 within-mission pairs (2.4198%);
- 4,529 isolated scenes and 1,595 scenes with weak evidence only;
- 39 cyclic strongly connected components across 30 missions;
- 207 explicit quest forks, 40 quest merges, and 59 authored cross-scene
  option groups.

Unknown relationships must stay unknown. Filename suffixes, file order,
generated rank, OCR, gameplay calibration, and manual WebUI overrides can be
useful display or investigation inputs, but they are not original-data proof.

The maintained source-only audits are:

```bat
python scripts\story_recovery\build_source_story_partial_order.py --language CN
python scripts\story_recovery\build_source_story_gap_queue.py --language CN
```

They write:

- `reports/mission_order/source_story_partial_order_CN.{json,md}`
- `reports/mission_order/source_story_gap_queue_CN.{json,md}`

Neither audit reads or writes `webui/overrides/story_order.json` or
`webui/data/story_order_ocr.json`.

## Evidence policy

### Accepted ordering evidence

- `MissionRuntimeAsset` quest relations: `questSequence`, `questPrev`, and
  `questFailGuard`.
- Direct quest-local Story references such as `_dialogId`, `snsDialogId`,
  `_cutsceneId`, `_remoteCommId`, and `_radioId`.
- DialogTree `authoredDirect` and `authoredMenu` connections.
- Typed LevelScript `levelscriptSceneChain` relations.
- LevelScript `LevelEvent_OnDialogExit` action chains that pass the strict
  ambiguity controls described below.
- Direct DialogTree/DialogTreeFragment option-to-line paths.
- Runtime Jump option routes only when the generated provenance is exactly
  `timelineRouteBranches` / `runtimeJumpTrack` / `dialogTimeline`.
- Timeline clip order for lines within one decoded dialog or cutscene asset.

### Retained but non-ordering evidence

- LevelScript byte/file order and cross-file numeric proximity.
- Untyped LevelScript membership, Story-call contexts, and hash terminals that
  do not establish direction.
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
- `LevelData` for script ownership, parent/control grouping, properties, and
  `lt:p` / `lt:mp` marker references;
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

High compact record families are structurally useful but require care:

- `0x0bed/0x00` carries terminal branches that can lead through local refs to
  concrete play actions;
- `0x0a03/0x00` is a compact property gate and is generally weaker;
- `0x12a1/0x00` and `0x12a3/0x00` are leader enter/leave trigger-volume
  events;
- property-changed and blackboard-change events are listeners, not proof of
  the writer sequence;
- static ActionBase setters do not cover many gameplay/server-owned property
  writes.

### `LevelEvent_OnDialogExit`

The July 11 installed client uses CodeRegistration `0x18b9217d0` and
MetadataRegistration `0x18b921c30`. Recovered
MemoryPack formatter mappings identify `0x1250/0x00` as
`LevelEvent_OnDialogExit`.

An exit chain is promoted only when:

1. the event header resolves to exactly one same-mission Story scene;
2. `ActionHeader.nextId` resolves unambiguously into `actionList`;
3. each linked action record resolves to zero or one Story scene;
4. record `nextId` links establish the action sequence;
5. self-only references and ambiguous records are discarded.

This produced exactly six new strong edges:

- `misc_dlg_c16m4_2d5 -> radio_c16m4_33`
- `misc_dlg_e3m1_1d5 -> radio_e3m1_1d5`
- `dlg_e3m6_105 -> dlg_e3m6_11`
- `dlg_e7m3_3 -> radio_e7m3_6`
- `dlg_sm2l2m7_8 -> black_sm2l2m7_1`
- `black_sm2l2m7_1 -> dlg_sm2l2m7_9`

They raised the strict graph from 1,710 to 1,716 strong edges and from 4,878
to 4,903 comparable scene pairs without creating a cycle.

## Dialog lines and option branches

Intra-conversation line order is usually strong when a DialogTree or Timeline
exists. Numeric line suffixes remain fallback identity only; authored clip
times can skip or reorder suffixes.

The strict audit currently accepts 300 option groups, 613 routes, and 1,349
branch lines:

- 284 groups come from direct DialogTree/DialogTreeFragment paths;
- 16 groups come from exact Runtime Jump Track routes.

It retains 259 rejected evidence groups (529 options) and 2,144 groups (2,967
options) with no explicit route. Missing routes are not silently converted to
branches.

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

The source graph is an evidence index, not runtime simulation. After the latest
CN rebuild it contains 5,345,967 nodes, 11,182,819 edges, and 5,489,598
aliases. Story-recovery queries include:

```bat
python tools\endfield_source_graph.py story dlg_e7m3_3
python tools\endfield_source_graph.py mission-flow e7m3 --limit 40
python tools\endfield_source_graph.py scene-gaps --warning sceneOrderDisorder
python tools\endfield_source_graph.py option-gaps --audit-only
python tools\endfield_source_graph.py option-route-audit --conflicts
```

The graph exposes Story/line/option reverse links, MissionRuntime actions and
conditions, quest narrative refs, LevelScript refs and property-flow audits,
scene-order gaps, option conflict evidence, FMV/video bindings, and comparison
reports. These links improve explainability; they do not promote chronology by
themselves.

Useful generated report families:

- `reports/mission_order/source_story_partial_order_CN.{json,md}`
- `reports/mission_order/source_story_gap_queue_CN.{json,md}`
- `reports/mission_order/<mission>_evidence_audit.{json,md}`
- `reports/mission_order/levelscript_*`
- `reports/scene_order_gap_report_CN.{json,md}`
- `reports/runtime_jump_option_route_audit_CN*.{json,md}`
- `reports/option_response_audio_evidence_CN.{json,md}`
- `reports/narrative_video_override_audit_CN.{json,md}`
- `reports/source_graph/option_branch_gaps.{json,md}`
- `reports/source_graph/unresolved_narrative_video_candidates.{json,md}`

## Current recovery queue

The gap score is a triage score, never chronology. It separates core Story
isolation from ambient `env` and standalone-video rows, scores a quest gap only
when diagnostic Story evidence exists without a strict attachment, and leaves
gameplay-only quests visible but unscored.

Current main-story priorities:

1. `e10m4`: highest total main-story score, driven by 39 core isolated scenes;
   find original source links for its radio/dialog/text rows.
2. `e7m3`: highest-ranked main mission whose primary frontier is LevelScript
   control flow; eight untyped multi-scene contexts remain after the recovered
   dialog-exit edge.
3. Audit other named LevelScript event types only when their semantics create
   a directional Story relation, with global ambiguity, reverse-path, and
   cycle controls.
4. Review the 39 cyclic components without numeric/file-order tie-breakers.
5. Expand exact Runtime Jump routes and keep the known conflict groups
   diagnostic until runtime option-index/post-jump semantics are proven.
6. Keep unresolved narrative videos standalone until Timeline, source-link, or
   observed playback evidence establishes placement.

The practical ceiling remains unchanged: original data can recover local
chains, partial mission graphs, quest forks/merges, verified dialog branches,
and authoritative media bindings. A complete mission-by-mission playback list
requires additional runtime/server-state evidence or an explicitly separate
manual/observed policy.
