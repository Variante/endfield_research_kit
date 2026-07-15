# Original-game Story order recovery (2026-07-10)

## Outcome

The installed game data supports a useful **partial** reconstruction of Story
scene order and mission branches, but it does not support a defensible global
total order. The strict CN audit recovered 1,710 order-bearing scene edges and
1,077 reduced component edges across 434 missions. Only 4,878 of 202,621
within-mission scene pairs (2.41%) are comparable from accepted source evidence.
Unknown order must therefore remain explicit rather than being filled from
filenames, generated rank, OCR, or manual overrides.

The maintained audit is
`scripts/story_recovery/build_source_story_partial_order.py`. It writes:

- `reports/mission_order/source_story_partial_order_CN.json`
- `reports/mission_order/source_story_partial_order_CN.md`

It does not modify or consume the user-managed
`webui/overrides/story_order.json`.

## Availability assessment

The original data provides different evidence strengths at different levels:

- Intra-conversation line order is generally strong where decoded DialogTree,
  DialogTreeFragment, or dialog Timeline structure exists.
- Intra-conversation option routing is recoverable only when a DialogTree path
  directly names the branch lines or decoded Runtime Jump Tracks provide the
  exact route mapping. The audit accepts 300 groups / 613 option routes / 1,349
  branch lines: 284 groups from DialogTree paths and 16 from Runtime Jump
  Tracks.
- Mission quest topology is useful but partial: 207 quest forks and 40 quest
  merges survive as explicit branch structures. Authored cross-scene option
  links add 59 source groups.
- Scene-to-scene chronology is sparse. Of 7,618 candidate scenes, 4,530 are
  isolated and 1,603 have only weak evidence. Only 1,337 scenes participate in
  an acyclic strong relation; 148 scenes occur in source-edge cycles.
- 250 of 434 missions have no source-comparable scene pair. Only four missions
  are fully comparable, and all four contain just two scenes. Exact mission
  playback order is therefore unavailable for most missions in static data.

The audit also records 259 rejected option-evidence groups (529 options) and
2,144 groups (2,967 options) with no explicit route. Rejected or missing routes
are not silently converted into branches.

## Evidence policy

Order-bearing evidence:

- `questSequence`, `questPrev`, and `questFailGuard` relations decoded from
  MissionRuntimeAsset quest structures;
- `authoredDirect` and `authoredMenu` links decoded from DialogTree structures;
- typed `levelscriptSceneChain` relations;
- direct DialogTree/DialogTreeFragment option paths verified against emitted
  `branchLines`;
- Runtime Jump option mappings only when their provenance is exactly
  `timelineRouteBranches` / `runtimeJumpTrack` / `dialogTimeline`.

Retained but non-ordering evidence includes LevelScript file and cross-file
order, untyped LevelScript chains, LevelData quest references, PRTS collection
order, and `radioContinuation` pending evidence-policy reconciliation.

The strict result rejects:

- `webui/overrides/story_order.json` and option overrides;
- `webui/data/story_order_ocr.json`, gameplay video, and OCR evidence;
- `sceneOrderInfo.questOrder`, `flowIndex`, SceneGraph node `order`, and UI rank;
- numeric filename suffixes, filesystem order, and VFS order;
- inferred-following-line, shared/default-continuation, risk-tagged, and manual
  option mappings.

Strong edges are collapsed into strongly connected components. The resulting
component DAG is transitively reduced. The 39 cyclic components across 30
missions are preserved as unordered cycles; they are not broken by a numeric
or file-order tie-breaker.

## Source controls

Representative checks against exported original data:

- `e1m10`: `dlg_e1m10_6 -> cutscene_e1m10_2 -> dlg_e1m10_7` is recovered as a
  typed `levelscriptSceneChain` from
  `LevelScriptData/base01_lv001/9800020005.json`.
- `c16m3`: the quest chain reaches `q#22`, which forks to `q#2`, `q#3`, `q#4`,
  and `q#21`. The sibling branches remain unordered. Scene attachments include
  `dlg_c16m3_8`, `_9`, and `_10` on the corresponding successor paths.
- `dlg_a1m3_1`: option group 1 maps to lines `_002` / `_003`, and group 4 maps
  to `_009` / `_010`, directly from
  `dlg_a1m3_1_p6505FAD8DEE14CD2.json` DialogTree paths.
- `dlg_c13m2_12`: Runtime Jump group 1 maps option 1 to `_003,_004,_005` while
  skipping `_027`, and option 2 to `_027`.
- `dlg_e6m1_10`: Runtime Jump group 3 maps to `_012` / `_013`. The nearby group
  4 candidates `_016` / `_003` are inferred-following-line diagnostics and are
  present only in the rejected-evidence bucket; `_003` is not promoted.
- `dlg_gm01m25_5`: no explicit source route exists, so its option group remains
  unknown even though a manual display route may exist elsewhere.
- `e0m0` quest 11 cluster: the LevelScript file sequence is retained as weak
  evidence and creates no order. `radio_e0m0_21` remains isolated.

Eleven focused unit tests cover transitive reduction, partial forks, SCC cycles,
weak-evidence non-promotion, candidate filtering, quest branches/merges, direct
DialogTree routes, exact Runtime Jump routes, inferred-route rejection, and
no-route/manual-evidence groups.

## Export and graph snapshot

The source was refreshed with `export.bat --export-from-game` in run
`reports/20260709_194500`. All structured and AnimeStudio stages returned zero,
with no failed decode entries and no missing manifest references. The run took
1h 12m 44.9s and peaked at 12.74 GiB sampled process-tree working set.

After the export, the source graph was rebuilt from the refreshed data with
asset maps, reference rows, and follow-up reports skipped. It contains
1,867,736 nodes, 4,753,140 edges, and 2,433,413 aliases. These counts match the
previous graph snapshot, so the installed patch did not change the modeled
Story topology.

`verify_export_freshness.py` currently reports the broad `Persistent` root as
stale after the successful export. This is a launcher/runtime false positive:
the export snapshot briefly included one extra `Persistent/HGDownload` payload
(141 files / 2,100,688,684 bytes), while the current root has 140 files /
1,959,082,428 bytes. The actual `Persistent/VFS` source remains stable at 135
files / 1,958,855,696 bytes, and the exported Persistent VFS index contains 33
chunks and 261,685 virtual files with zero missing chunks. Do not use the
transient broad-root mismatch as evidence that the Story VFS export failed.

## Practical ceiling

The original data is sufficient to present a source-backed graph, local chains,
quest forks/merges, and verified option arms. It is not sufficient to reconstruct
one authoritative scene list for every mission. Any UI total order beyond the
accepted partial graph necessarily adds a policy choice or external evidence and
must remain separate from this source-only result.
