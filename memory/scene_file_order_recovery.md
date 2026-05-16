# Scene File Order Recovery

This note records the current evidence rules for ordering story, dialog,
radio, cutscene, and mission files from original game data. Existing WebUI
order is not evidence by itself.

## Evidence Stack

Strong evidence:

1. `MissionRuntimeAsset` quest DAG edges, especially
   `questDic[*].prevQuestIdList` plus quest-local story refs such as
   `_dialogId`, `snsDialogId`, `_cutsceneId`, `_remoteCommId`, and `_radioId`.
2. DialogTree edges decoded from `dlg_*` TextAssets:
   `connections[*]._sourceNode.$ref -> connections[*]._targetNode.$ref`.
3. Timeline clip order for cinematic dialog from
   `timeline_line_orders.json` and source Timeline `MonoBehaviour` JSON.
4. Typed UID/control-flow or trigger/action relations decoded from
   LevelScript data.

Weak evidence:

- LevelScript byte-offset order inside one file.
- filename/script-id proximity.
- radio continuation or audio metadata without a quest/control-flow bridge.
- table membership, summaries, or registry presence without a chronological
  edge.

Not evidence:

- generated WebUI rank/order;
- filesystem or VFS chunk order;
- filename suffix order except as a display fallback;
- branch flattening when the quest DAG does not prove a merge or predecessor.

## Current Coverage

Recent scans found:

- `418` mission runtime assets.
- `3,736` quest nodes.
- `185` missions with story file references.
- `548` total quest-local story refs across dialog, SNS, cutscene, remote
  comm, and radio fields.
- `4,223` decoded DialogTree graphs.
- `290` recovered dialog Timeline assets covering `273` dialog keys.
- `66` option route records in the Timeline catalog.

Timeline order proves suffix order is only a fallback. For example,
`dlg_c28m3_23` has authored clip times for `_001`, `_003`, `_004`, `_005`,
and `_007`, skipping numeric suffixes.

## Current Audit Conclusions

`e0m0` is partially confirmed. The first four-entry quest sequence and the
`cutscene_e0m0_6 -> cutscene_e0m0_7 -> cutscene_e0m0_8` UID chain are strong.
Most long radio/cutscene clusters remain weak LevelScript file-offset order,
and several exported files still have no mission-order clue.

`e10m4`, `c16m4`, `c6m1`, `e1m1`, and `c28m3` remain the highest-priority
unknown-heavy missions. After fixing short-id false positives in LevelData byte
scans, recent audit status was:

| mission | strong | weak | unknown | LevelData adjacent pairs |
| --- | ---: | ---: | ---: | ---: |
| `e10m4` | 29 | 8 | 44 | 2 |
| `c16m4` | 22 | 5 | 31 | 0 |
| `c6m1` | 13 | 3 | 42 | 0 |
| `e1m1` | 17 | 12 | 19 | 0 |
| `c28m3` | 12 | 16 | 31 | 0 |

Remaining `levelscriptChain` entries are placement/ownership anchors from
script/control nodes to story keys or terminals. Do not promote them as
inter-story chronology unless a decoded trigger owner, quest edge, UID chain,
or typed setter/action relation proves the relation.

## Scene Chunks

`scripts/story_builder/mission_recovery.py` now groups every placed scene into
a connected-component chunk. Chunks are written to
`reports/mission_timeline_recovery_CN.json` as a top-level `chunks: [...]` list
per mission, and each `scenePlacement[<sceneKey>].chunkId` references its
chunk (`c1`, `c2`, ...).

Joining edges (undirected, for component grouping):

- `sourceBackedSceneEdges` of any kind in the source-backed scene graph
  (questAttach, levelscriptSceneChain, levelscriptChain, levelscriptFileOrder,
  levelscriptCrossFileOrder, radioContinuation, authoredDirect, authoredMenu).
- Consecutive `sourceBackedSceneSequences[*].sceneKeys` pairs.
- `sceneTimelineEvidence` scenes that share the same Timeline asset id.

A chunk's `strength` is `strong` if any internal edge kind is in
`STRONG_ORDER_EDGE_KINDS` (the same set the WebUI builder treats as authored
chronology), otherwise `weak`, or `unanchored` when the chunk is a singleton
with no joining edges. Chunk IDs are stable: components are numbered by the
natural-key order of their lexicographically-first scene key.

Initial counts across all 418 missions (`reports/mission_timeline_recovery_CN.json`):

- `245` missions have at least one chunk.
- `175` missions land in a multi-chunk layout.
- `1,167` chunks total — `135` strong, `320` weak, `712` unanchored singletons.
- Largest chunk holds `69` scenes.
- Per-edge tally: `levelscriptChain` 345, `levelscriptFileOrder` 282,
  `levelscriptCrossFileOrder` 236, `levelscriptSceneChain` 99,
  `radioContinuation` 68, `levelDataQuestRef` 11, `authoredMenu` 4,
  `authoredDirect` 3, `timelineShare` 1.

Snapshot of the unknown-heavy missions from `## Current Audit Conclusions`:

| mission | chunks | strong | weak | isolated | max scenes/chunk |
| --- | ---: | ---: | ---: | ---: | ---: |
| `e0m0` | 7 | 1 | 6 | 0 | 16 |
| `e10m4` | 7 | 2 | 5 | 0 | 16 |
| `c28m3` | 9 | 1 | 5 | 3 | 39 |
| `c6m1` | 10 | 1 | 6 | 3 | 14 |

Chunk membership for `e0m0` agrees with the prior audit narrative: the
`cutscene_e0m0_6 -> _7 -> _8` UID-mediated chain plus a couple of related
quest/hash nodes form the one strong chunk; the remaining six chunks are
LevelScript file-offset groups not yet promoted to strong evidence. A scene
with `status=strong` in the per-entry audit can still belong to a `weak` chunk
when its strength comes from a non-chunk source (MissionRuntime conditioning,
PlayableDirector anchor, etc.).

The audit (`reports/mission_order/<mission>_evidence_audit.md`) now includes a
`chunk` column in the Entry Evidence table and a `## Scene Chunks` section
listing every chunk with its strength, edge kinds, and scene keys. To
regenerate for every authored-story mission prefix
(`e/a/gm/c/sm/f/m`, excludes `db/dm/hidden/map*`):

```bat
python scripts\story_builder\mission_recovery.py
python scripts\story_recovery\build_mission_order_evidence_audit.py --all-target-prefixes --skip-asset-map
```

## Chunk Order

Per mission, `build_chunk_order` in `scripts/story_builder/mission_recovery.py`
recovers directed cross-chunk edges from the quest DAG. The output is on each
mission's payload as `chunkOrder: {edges, parallel, incomparable, unattachedChunkIds, attachedQuestsByChunk}`
and surfaces in both `reports/mission_order/<mission>_evidence_audit.md`
("Chunk Order (questDag)" section) and the WebUI mission-timeline box (chunks
are sorted in topological order with quest-DAG arrows where evidence exists).

Algorithm: each chunk's `attachedQuests` is the union of
`scenePlacement[*].questIds` over its member scenes. Quest ancestry comes from
`questEdges` of kind `questPrev`. Emit X → Y iff X and Y have non-empty,
disjoint quest sets and every quest in Y is a strict descendant of every
quest in X. Transitive reduction drops redundant edges. Parallel pairs share a
quest. Incomparable pairs have disjoint quests but no provable order — these
mark quest-fork siblings.

Initial counts across all 418 missions:

- `151` missions gain at least one chunk-order edge (`544` edges total).
- `166` missions are fully ordered by quest attach (no parallels or
  incomparable pairs in the attached set).
- `54` missions are partially ordered (some edges plus parallels or
  incomparable pairs).
- `77` parallel chunk pairs (co-quest).
- `263` incomparable chunk pairs (typical of branching quests).

Important caveat: many e-prefix missions store scene attachments only via
LevelScript script-condition references rather than MissionRuntime `storyRefs`
or client-action `storyRefs`. Those scenes therefore land in
`attachedQuestsByChunk = {}` and stay unattached for chunk-order recovery.
`e0m0` and `e10m4` both fall in this bucket — 0 quest-DAG edges despite the
audit's `missionRuntimeScriptConditions` block pinning specific quests to
specific story-key sequences. Folding script-condition matches into quest
attachments is a candidate follow-up.

Evidence sources still on the queue for chunk-order recovery:

- Script-condition matched story keys (`missionRuntimeScriptConditions`)
  promoted to quest attachments.
- `sourceBackedHashTerminals` prev/next hash chains crossing chunks.
- Story-call contexts with directional position info.

Explicitly rejected: filename/index order, scene-key numeric suffix, mission
bundle row order. The chunks themselves already include radio-continuation
edges in Phase 1, so radio continuation isn't a separate Phase 2 signal.

## Useful Reports

Generate a mission evidence audit:

```bat
python scripts\story_recovery\build_mission_order_evidence_audit.py --language CN --mission e0m0
```

Current report families:

- `reports/mission_order/<mission>_evidence_audit.{json,md}`
- `reports/mission_order/levelscript_property_flow_CN.{json,md}`
- `reports/mission_order/audio_dialog_custom_events_CN.{json,md}`
- `reports/playable_director/timeline_track_clips.{json,md}`

## Candidate Recovery Queue

1. Decode LevelScript setter opcodes for property-flow bridges. The current
   audit found `60` confirmed bridges between `MissionRuntimeAsset`
   `CheckLevelScriptProperty*` conditions and owning LevelScript files, but
   they are not promotable until the setter record type is identified.
2. Trace `DialogOptionPlayableAsset` runtime field `+0x18`, the active clip
   gate checked before `SetDialogOption`, to unblock source-backed option
   response mapping.
3. Map per-option NPC response speakers for the multi-speaker inferred option
   response groups, likely via `DialogOptionTable.options[*].actorId`.
4. Connect `BeyondFMVPlayableAsset.fmvId` Timeline clip evidence to the WebUI
   builder as weak FMV/cutscene ordering evidence.
5. Keep rejecting `AudioDialogCustomEventTable` as a scene-ordering source. It
   is useful only as a per-dialog audio profile/tag.

## Rules For Future Promotions

- Promote to strong only from quest DAGs, authored scene transitions,
  UID/control-flow chains, or decoded typed trigger/action relations.
- Keep weak edges visibly separate from strong edges.
- Preserve unknown entries rather than inventing total order.
- Put generated audits under `reports/`, disposable prototypes under
  `scratch/` or `tmp/`, and durable conclusions in this file.
