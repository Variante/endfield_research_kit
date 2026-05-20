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

For focused e0m0 LevelScript ordering work, including the current
`lt:p` / `lt:mp` LevelTimeline marker plan, start with
`memory/e0m0_file_order_from_binary_scripts.md`.

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

Chunks now also carry diagnostic placement fields: `questIds`,
`questAttachSources`, `sourceScripts`, `sourceFileOrderHint`, and
`sourceFileOrderSpan`. The WebUI and audit can use the first LevelScript source
file as a display fallback when quest-DAG edges are absent, but this remains a
weak hint only. For `e0m0`, this lets us compare the file spans such as
`indie_dg002/8700040000..8700040001` with the one quest-attached chunk (`c4`)
without promoting filename/script-id order to chronology.

`questSpatialTrack` records quest-local map pins, resource references, script
condition refs, centroid movement, and attached chunks. This is shown as a
Quest Map Track in the WebUI and in mission-order audits. It is useful for
human inspection of e0m0's route through `indie_dg002`, but map position is
still diagnostic unless it is bridged by a quest/story or decoded trigger edge.

`levelscriptSpatialProximity` now extracts raw little-endian float32 triples
from LevelScriptData files and compares them with quest map pins in the same
map. Matches are capped to nearby vectors (`25m` x/z and `12m` y by default)
and are emitted only as weak diagnostics:

- scene placement rows get `spatialQuestCandidates` plus the
  `levelscriptSpatialProximity` evidence kind;
- chunks aggregate those candidates and may carry a weak `questOrderHint` used
  only as a display fallback when no quest-DAG chunk edges exist;
- `questSpatialTrack[*].spatialSourceMatches` shows which source scripts and
  chunks sit near each quest pin;
- `levelscriptSpatialProximity` is also emitted as a top-level per-mission
  list for audits.

Current CN run: `14,374` weak spatial matches across `175` missions, touching
`2,870` scene-placement rows. These matches do not write to `questIds`, do not
create `chunkOrder.edges`, and do not make a chunk strong.

Weak unattached chunks can now carry diagnostic `subchunks`. These are
contiguous runs inside one chunk, split by the best nearby quest pin from
`levelscriptSpatialProximity`; scenes without their own spatial match inherit
the neighboring run only for display. Subchunks never change the parent chunk's
strength or quest attachment. Current CN run: `349` subchunks inside `66` weak
chunks. For e0m0, c2 splits into `c2a` (zipline run near q#1 via
`8700010007`) and `c2b` (`cutscene_e0m0_3` plus the radio cluster near q#11
via `8700050001` / `8700020022`).

Quest-tree nodes now mirror these diagnostics as `sourceScriptHints`, so the
WebUI tree and the e0m0 audit can show weak file-to-quest candidates directly
on the quest node without promoting them to attachments. For e0m0 this exposes
`e0m0_q#1 <- c2a/cutscene_e0m0_1stZipline via indie_dg002/8700010007` and
`e0m0_q#11 <- c2b/cutscene_e0m0_3/4/5 plus radio cluster via
indie_dg002/8700050001`. These are source/spatial diagnostics only.

`cutscene_e0m0_1` remains unplaced. Exact searches in the original structured
game JSON do not find `cutscene_e0m0_1` as a LevelScript/MissionRuntime/LevelData
reference; only prefix-neighbor files such as `cutscene_e0m0_1stZipline`,
`cutscene_e0m0_10`, `cutscene_e0m0_11`, etc. appear. The recovered AnimeStudio
asset exists and carries one subtitle at `19.5s` ("管理员已进入任务待命位置"), the
path `Assets/Beyond/DynamicAssets/Gameplay/Cutscene/cutscene_e0m0_1/Prefab/cutscene_e0m0_1`,
and black-screen/elevator-selection metadata, so it is plausible mission-start
content by name and text. It is not currently evidence that the file is first
in the quest chronology: the rebuilt e0m0 scene graph keeps it
`orderStrength=unknown`, with no `scenePlacement`, no source-backed edge, and
no LevelScript spatial match.

`memory/quest_tree_source_connections.md` gives a useful strong-evidence
control: when a quest node truly owns a story file, the join usually appears
as a `MissionRuntimeAsset` field, `timelineRecovery.quests[*].storyRefs[]` or
`questSpatialTrack[*].resources[]`, `scenePlacement[storyKey].questIds`,
`conv/<storyKey>.json.sourceLinks[]`, and a source-graph
`references_story` / `source_references_story` edge. `cutscene_e7m4_1` has
that pattern through
`MissionRuntimeAsset/e7m4.json questDic.e7m4_q#13..._cutsceneId.constValue`.
The e0m0 suspects checked so far (`cutscene_e0m0_1`,
`cutscene_e0m0_1stZipline`, `cutscene_e0m0_3`, `cutscene_e0m0_13`) do not
have those direct source-link/source-graph edges; their usable clues are
LevelScript scene edges, script-condition attachment for `cutscene_e0m0_13`,
and weak spatial/file hints.

Mission-area metadata adds one more diagnostic but not a new e0m0 ordering
edge. `MissionAreaTable` entries now propagate `subDataParentId` /
`levelDataParentId` into quest pins and Quest Map Track display. In e0m0 all
mission-area pins `e0m1_001` through `e0m1_008` share parent `8700020000`,
including q#1 and q#11. That parent points at the shared mission-area host
neighborhood rather than a per-quest story trigger, so it should stay
diagnostic only; it does not attach `cutscene_e0m0_1`, and it does not replace
the stronger spatial candidates like q#1 via `8700010007` or q#11 via
`8700050001`.

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
or client-action `storyRefs`. Script-condition matches are now folded into
quest attachments only when exactly one mission owns the referenced
`(mapId, scriptId)`. For `e0m0`, this attaches `c4` to `e0m0_q#7`, but the
other six chunks remain unattached, so the mission still has `0` quest-DAG
chunk-order edges.

Evidence sources still on the queue for chunk-order recovery:

- `sourceBackedHashTerminals` prev/next hash chains crossing chunks.
- Story-call contexts with directional position info.
- Recovered questEdges from LevelScript property-setter flow — blocked until
  the compact property gate/terminal family is decoded. Low ActionBase setters
  are now named (`SetBool`, `SetInt`, `SetIntIncrease`), and the ScriptEvent
  high-code bands are named, but several MissionRuntime bridges still land on
  unresolved terminal records such as `0x0bed/0x00`.
  The property-flow audit explicitly marks the relation as not promotable, see
  [reports/mission_order/levelscript_property_flow_CN.md](../reports/mission_order/levelscript_property_flow_CN.md).
  The setter-candidate audit now separates exact UID key records from
  top-level/offset-only property data and distinguishes list-clear rows from
  terminal branch rows.
  Update: `0x0bed/0x00` is now structurally decoded as a local terminal
  branch carrier; the runtime class family is still unnamed, and the separate
  `0x0a03/0x00` gate family remains unresolved.

Explicitly rejected: filename/index order, scene-key numeric suffix, mission
bundle row order. The chunks themselves already include radio-continuation
edges in Phase 1, so radio continuation isn't a separate Phase 2 signal.

## Variant MissionRuntime + NPC Proxy Dialog Attachments

`attach_variant_mission_runtime_quests` and
`attach_npc_proxy_dialog_quests` mirror the script-condition attacher for
two additional decoded relationships in the WebUI scene graph:

- **Variant MissionRuntime** — when a mission borrows another mission's
  quest graph (`flow.sceneGraphVariantMissions`), edges in this mission's
  scene graph that carry the variant's `questIds` propagate those quest
  attachments onto both edge endpoints with `source: variantMissionRuntime`.
  `load_variant_quest_edges` then pulls the variant missions' MRA
  `prevQuestIdList` edges so `build_chunk_order` can use the variant DAG to
  order chunks that attach to variant quests.
- **NPC proxy dialog** — `flow.quests[*].proxyDialogs[*]` bind a dialog
  scene key to a quest via an NPC proxy. The attacher folds those quest
  ids into `scenePlacement[<sceneKey>].questIds` with
  `source: npcProxyDialog`.

Initial counts across the 418-mission run:

- variantMR: `304` attachment events across `13` missions; e10m4 alone
  contributes `126`.
- npcProxyDialog: `48` events across `35` missions.
- Combined chunk-order yield: 600 → `621` edges (+21), 156 → `158`
  missions ordered, 85 → `105` parallel pairs (most chunks touched by
  variantMR end up co-quest because they span many variant quests).
- e10m4's `c4` and `c5` now both anchor to multiple `e10m4d5_q#*` quests
  but share enough quests that they're marked parallel rather than ordered.
  Splitting overlapping-quest chunks into smaller chunks would let the
  strict-ordering policy bite, but that requires finer-grained scene-graph
  decoding (queued).

## Script-Condition Quest Attachment

`decode_mission_script_conditions` in
`scripts/story_builder/mission_recovery.py` walks every
MissionRuntimeAsset for `CheckLevelScriptProperty*` nodes, capturing
`(questId, mapId, scriptId, key)`. `build_script_condition_ownership` runs a
global pre-pass before per-mission recovery so the attacher can apply a
**scoped** policy: a quest attaches a scene only when the referenced
`(mapId, scriptId)` is referenced by exactly one mission (shared LevelScripts
don't fan out).

`attach_script_condition_quests` then folds matches into
`scenePlacement[<sceneKey>].questIds`, tags each attachment in
`questAttachSources` with `source: scriptCondition`, and marks the placement
row with the `scriptConditionQuestAttach` evidence kind. A diagnostic list
`scriptConditionAttachments: [...]` is emitted per mission for traceability.

Initial counts across the 418-mission run:

- `59` missions gain script-condition attachments.
- `928` attachment events recorded; `805` are new (not already covered by
  `storyRefs`).
- Chunk-order totals shift from the Phase 2 baseline to: 156 missions ordered
  (`+5`), `600` quest-DAG edges (`+56`), `85` parallel pairs (`+8`), `286`
  incomparable pairs (`+23`).
- Sample: `e0m0_q#7` now anchors chunk `c4` via the `indie_dg002/8700040000
  battle_field_clear` condition. e10m4 has no MissionRuntime script
  conditions, so its chunks remain unattached for quest-DAG ordering even
  after this promotion.

## Task Tree

`attach_chunks_to_quest_tree` annotates every quest-tree node with the
chunks attached to its quest. A chunk attaches to a quest when at least one
of its scenes lists that quest in `scenePlacement[<sceneKey>].questIds` (from
either storyRefs or scoped script conditions). Within a quest, chunks are
sorted by the Phase 2 chunk-order topological position when available,
otherwise by natural order.

Mission payload now carries `questTree.unattachedToQuestChunkIds` (chunks not
attached to any quest) and `questTree.chunkAttachmentSummary` with
`attachedChunkCount`, `unattachedChunkCount`, `questsWithChunkCount`.

The audit's `## Task Tree` section renders the quest tree with attached chunk
ids inline (e.g. `a1m3_q#SNS — c3 → a1m3_q#IntroDialog — c1 → ... → a1m3_q#FinalDialog — c2`).
The WebUI quest tree node attaches one `mission-timeline-chip-chunk` per
attached chunk id; an "unattached chunks" footer lists chunks with no quest
home.

## Useful Reports

Generate a mission evidence audit:

```bat
python scripts\story_recovery\build_mission_order_evidence_audit.py --language CN --mission e0m0
```

Current report families:

- `reports/mission_order/<mission>_evidence_audit.{json,md}`
- `reports/mission_order/levelscript_property_flow_CN.{json,md}`
- `reports/mission_order/levelscript_property_setter_candidates_CN.{json,md}`
- `reports/mission_order/levelscript_action_runtime_metadata.{json,md}`
- `reports/mission_order/levelscript_action_map_type_indices.{json,md}`
- `reports/mission_order/levelscript_action_map_list_audit.{json,md}`
- `reports/mission_order/levelscript_action_body_targets_gameassembly.{json,md}`
- `reports/mission_order/levelscript_actionbase_formatter_tags.{json,md}`
- `reports/mission_order/memorypack_union_formatter_tag_audit.{json,md}`
- `reports/mission_order/levelscript_header_chain_audit.{json,md}`
- `reports/mission_order/audio_dialog_custom_events_CN.{json,md}`
- `reports/playable_director/timeline_track_clips.{json,md}`

## Candidate Recovery Queue

1. Decode LevelScript setter/start opcodes for property-flow and manual-start
   bridges. The current audit found `60` confirmed bridges between
   `MissionRuntimeAsset` `CheckLevelScriptProperty*` conditions and owning
   LevelScript files. `build_memorypack_union_tag_audit.py` now derives `110`
   ActionHeader/header mappings from MemoryPack union formatter tables and the
   observed high-code banks, including low `0x0e**` / `0x0f**` ActionHeader
   banks plus `ScriptEvent_OnCustomEvent`, `ScriptEvent_OnLeaderEnterTriggerVolume`,
   `ScriptEvent_OnLeaderLeaveTriggerVolume`,
   `ScriptEvent_OnScriptStageChanged`, `LevelEvent_OnDialogEnter`,
   `LevelEvent_OnDialogExit`, `LevelEvent_OnQuestStateChanged`, and
   `LevelEvent_OnTrainLevelEvent`. These are listener or event registrations,
   not the setter that makes a quest edge promotable.
   The remaining missing pieces are the compact action record that mutates or
   completes the property (`0x0a03/0x00` / `0x0bed/0x00`) and the action record
   that calls `ManualStartLevelScript` / `ManualEndLevelScript`.
   `build_levelscript_opcode_shape_audit.py` now scans this globally:
   current run covers `59,763` records / `603` opcode pairs, finds no
   actionMap `levelId+scriptId` ManualStart-like rows, and narrows the
   property-key non-event candidate pool to clusters led by `0x0364/0x0b`,
   `0x03b8/0x0a`, `0x104e/0x00`, `0x1092/0x00`, `0x0176/0x08`,
   `0x03e7/0x0a`, `0x04bb/0x09`, and related opcodes.
   `build_levelscript_property_setter_candidate_audit.py` then focuses only
   the `60` confirmed MissionRuntime bridges: `41` rows have exact
   key-bearing UID records, `19` are offset-only/top-level property data, and
   only `5` candidate observations are story-adjacent. The best repeated
   focused clusters are `0x0a03/0x00` (`property-key-gate`), `0x0176/0x08`
   (`property-key-ref`), `0x0bed/0x00` (`property-key-terminal`), and the
   tiny story-adjacent `0x04b8/0x09`/`0x0000/0x00`/`0x0001/0x00` cases.
   `build_levelscript_action_metadata_audit.py` adds the class-level check:
   ManualStart/ManualEnd serialize `levelId + scriptId`, GetLevelScriptProperty
   families serialize `_target + _path`, and `OnPropertyChanged` is a
   listener. The current metadata pass also finds the real generic setter
   family: `Set<T>` / `SetList<T>` carry `_key + _value`, while concrete
   `SetBool`/`SetInt`/`SetPropertyPath`/`SetLevelScriptPtr` shells have no
   useful runtime fields. No metadata type name contains
   `UpdateLevelScriptProperty`, `OperateLevelScriptNumber`, or
   `SetLevelScriptDone`.
   `build_levelscript_action_body_audit.py` then maps the focused methods to
   GameAssembly: ManualStart/End call `TryGetLevelScript` then
   `LevelScriptRuntime.ManualStart`/`ManualEnd`; property getters call
   `TryGetLevelScript` and `LevelScriptRuntime.get_properties`;
   `OnPropertyChanged` registers listener paths; and runtime state updates call
   `ModuleResetUpdateProperty`, whose module body only toggles reset/update
   flags. The generic `Set<T>`/`SetList<T>` Execute pointers map to null in
   this IL2CPP table, but the concrete MemoryPack wrappers do prove serialized
   key/value order: `Deserialize` calls `set____key__` before
   `set____value__`, and the generic wrapper setters write key/value to the
   real instance at `+0xd0`/`+0xd8`. A new
   `build_levelscript_action_map_type_audit.py` pass resolves the previously
   opaque generic/list type indexes through `Il2CppMetadataRegistration`
   (`0x18a31fcd0`): `actionList` is `List<ActionBase>`, `getterList` is
   `List<PureGetter>`, and `headerList` is `List<ActionHeader>`; runtime
   arrays mirror those as `ActionBase[]`, `PureGetter[]`, and
   `ActionHeader[]`. The same body audit now includes
   `ActionSerializedMapForMemoryPack`: its `Deserialize` body calls
   `set___actionList__`, `set___getterList__`, and `set___headerList__` in
   that order, and the setter bodies write runtime fields at `+0x18`,
   `+0x20`, and `+0x10`.
   `build_levelscript_action_map_list_audit.py` keeps the physical list split
   honest against the opcode content: the second block is still best named
   `getterList` because its dominant named tags are `PureGetter` shapes such
   as `GetLevelScriptStage`, `IntEqual`, `GetMainCharacter`, and `IntCompare`,
   while the third block is header/event dominated. It also found and promotes
   the common two-block shape where an empty getter block is omitted and the
   final count is really `headerList` (`1,373` files). After that inference,
   the current scan keeps derived `ScriptEventHeader`-band rows out of
   `getterList`; `headerList` contains `5,703` such rows, including `3,309`
   `0x12a1/0x00` rows.
   `build_levelscript_actionbase_tag_audit.py` now extracts the generated
   `ActionBaseForMemoryPackFormatter..cctor` union table from GameAssembly.
   The table is contiguous from `0x0000` through `0x04dc` (`1,245` tags) and
   bridges raw action-map `code` values to formatter classes. This names
   common playback actions (`0x034a/0x0d` `PlayRadio`,
   `0x034b/0x0d` `PlayRadioAndWait`, `0x046c/0x0e` `StartDialogAction`,
   `0x046d/0x10` `StartDialogAndTeleportAction`) and confirms real setter
   action records (`0x03b8/0x0a` `SetBool`, `0x03e7/0x0a` `SetInt`,
   `0x03ea/0x0a` `SetIntIncrease`). It also reclassifies `0x0176/0x08` as
   `ListClear<float>`, not setter proof. The same audit checks
   `FinalActionBaseForMemoryPackFormatter` separately; it contains only two
   subgame final-action tags and does not explain the high records.

   `build_memorypack_union_tag_audit.py` then scans all generated MemoryPack
   union formatter cctors. It finds no raw union tag above `0x04dc`, so the
   high codes are not missing ActionBase-style formatter tags. Instead, the
   exact high opcode values are derived from ActionHeader banks over the
   extracted formatter tags: the current run derives `110` header/event
   mappings across `0x0exx` through `0x18xx` plus ScriptEvent runtime bands.
   `0x0a03/0x00` and `0x0bed/0x00` remain outside that mapping.

   Current implication: low ActionBase opcodes and ScriptEvent registrations
   are class-bridged; the serialized-map list boundaries are now mostly
   decoded. `levelscript_opcode_shape_audit` now reports `57,223` records
   inside `ActionSerializedMap` (`39,051` action, `8,087` getter, `10,085`
   header) out of `59,763` decoded UID records. The list audit puts
   `0x0a03/0x00` at `1` action, `212` getter, `0` header rows, and
   `0x0bed/0x00` at `1,529` action rows only. That moves `0x0a03/0x00`
   into the getter-list compact gate/read family and confirms `0x0bed/0x00`
   as an `actionList` terminal branch rather than an outside-map orphan. For e0m0
   specifically, `battle_field_clear` is still carried by `0x0bed/0x00`, so it
   remains a quest-to-script/property bridge rather than a decoded setter edge.
   The follow-up terminal-branch audit now decodes the `0x0bed/0x00` tail as
   local action refs and walks those refs through `nextId`, split lists, and
   nested terminal branches. Current CN run: `1,529` terminal rows, `6`
   MissionRuntime-bridged rows, `156` rows with story-key targets, and `154`
   rows with play-action targets. For e0m0, `battle_field_clear` branches to
   local refs `169, 189`; local `169` reaches `cutscene_e0m0_New14`,
   `radio_e0m0_8d8`, and nearby levelseq actions. This is a decoded terminal
   branch scene bridge, not generic setter proof.
   The body audit also proves the serialized `ActionHeader._nextID` setter
   writes the runtime field at `+0x60`; in compact LevelScript payloads this
   value appears at payload offset `+0x5`. `levelscript_binary.py` now exposes
   it as `payloadDecoded.actionHeader.nextId`, and
   `build_levelscript_header_chain_audit.py` uses it as the true
   `headerList` event-to-`actionList` edge. Current global run: `10,085`
   header rows, all `10,085` named by the derived mapping, `9,961` resolving
   to `actionList` rows, `1,647` target chains containing a named play action,
   and `1,791` target chains carrying scene-like text. The remaining edge
   residue is not missing data: `123` rows point at duplicate `actionList`
   local ids and are now reported as ambiguous action targets; only one row has
   no positive next edge.
   ManualStart/ManualEnd is also still missing from scanned action-map
   payloads: the global opcode audit found no action-map row with a true
   `levelId + scriptId` payload.
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

## Case Study: `e0m0` — Where the Quest/Scene Bridge Stops

Snapshot taken from the current `webui/data/lang/CN/mission/e0m0.json`. e0m0
is the prologue mission and a good probe because it shows almost every
class of evidence we have, while still bottoming out with most chunks
unattached.

Quest DAG (from `MissionRuntimeAsset.questDic[*].prevQuestIdList`) is a
clean linear chain `e0m0_q#1 → ... → e0m0_q#13`. All 11 leading quests
carry `MissionAreaTrackingInfo` or `PosTrackingInfo` in `indie_dg002`, so
quest order plus quest map-position is fully recovered (see
`flow.quests[*].tracking` and `flow.mapPins`).

Scene placement chunks vs quest attachment:

| chunk | scenes | attached quest | bridge |
|-------|--------|----------------|--------|
| c1 | cutscene_e0m0_6 / 7 / 8, item_mission_e0m0_hubkey, `#c5a02da1` | – | hub room script `indie_dg004/23900030000.json`; no MRA condition |
| c2 | 1stZipline, 2ndZiplineA/B/C, cs_3/4/5, radios 12-17/20/22/23 | – | spans `indie_dg002/87000{1,2,5}*.json`; no condition |
| c3 | cs_2, radio_e0m0_1 | – | Pei dialogue `8700020000/0001`; no condition |
| **c4** | cs_13, cs_New14, radios 1d5/8d4/8d8 | **e0m0_q#7** | `scriptConditionQuestAttach` on `indie_dg002/8700040000.json` |
| c5 | cs_lookingatpatriot, radios 8d9/9 | – | "Patriot" reveal transition |
| c6 | cs_tombstonecollapseCam, misc_dlg 0d5/0d7/0d8/0d9, radio_11 | – | tombstone-collapse cluster, `8700020017/18/19` |
| c7 | radio_2, radio_2d8 | – | `8700000004.json` only |

So 6 of 7 chunks land in `unattachedToQuestChunkIds` even though the
mission is fully quest-ordered. The only bridge that fired is the one
`CheckLevelScriptProperty*` condition on q#7 pointing at LevelScript
`8700040000`. No quest in this mission carries direct `storyRefs`, so
the `missionStoryRef` and `clientActionStoryRef` evidence kinds never
trigger.

Unused signals that could close the gap for e0m0-shaped missions:

1. **Quest tracking positions ↔ LevelScript embedded floats.** Implemented
   as weak `levelscriptSpatialProximity` diagnostics. The e0m0 probe confirms
   the expected raw vector family: `indie_dg002/8700020022.json` now produces
   q#11 candidates for c2 (including `cutscene_e0m0_3` and
   `radio_e0m0_12`), and a tighter neighbor in `8700050001` also sits near
   q#11. These are visible in both the WebUI chunk/Quest Map Track and
   `reports/mission_order/e0m0_evidence_audit.md`.
2. **LevelScript stem ordering inside a `(mapId)` directory.** The
   scene-graph already emits `levelscriptFileOrder` /
   `levelscriptCrossFileOrder` edges by numeric stem, but this only
   feeds scene→scene order, never chunk→quest attachment. If chunk X
   shares a `(mapId, *)` neighborhood with attached chunk Y, an
   `levelscriptStemNeighbor` attach could propagate Y's quest set to X
   with weak strength.
3. **`indie_dgXXX_lv_data_sub_mission_*` LevelData files.** These carry
   per-entity `(spawn_point, Lookat*)` positions tied to mission-area
   IDs that already appear in `quest.tracking[*].missionAreaId`. They
   are scanned today only for `storyRef` byte-context matching
   (`anime_assets._leveldata_quest_story_refs_by_mission`), not for
   positional anchoring.

None of the above is promotable to strong evidence; they are all weak
signals subject to false positives (e.g. a trigger volume positioned at
`(0, 0, 0)`, or a re-used `(mapId, scriptId)` across missions). If
promoted they belong in a new `evidenceKind` distinct from
`scriptConditionQuestAttach` so the WebUI can keep the attachment
hierarchy visible.

## 2026-05-19 Compact Gate And Setter Overlap Follow-up

`0x0a03/0x00` is now structurally decoded in
`scripts/story_builder/levelscript_binary.py` and audited by
`scripts/story_recovery/build_levelscript_gate_audit.py`.

Current CN result:

- `219` compact gate rows.
- `171` rows with a decoded property key.
- `41` rows with an optional tail local-action ref.
- `10` rows bridged from MissionRuntime property checks.
- Gate-ref walks reach story/play records only rarely (`5` story, `4` play),
  and the MissionRuntime-bridged rows mostly resolve to trigger/control setup
  or missing local ids rather than immediate scene playback.

The stable payload shape is:

```text
00 <null sentinel> 04 <first flag> ff ff ff ff
<type code> <len> <property key>
04 <post flag> <null sentinel> [optional i32 local ref]
```

There are also `local-ref` and rare `two-slot-key` variants. This makes
`0x0a03/0x00` a real gate/read clue, but not a promotable setter edge.

`scripts/story_recovery/build_levelscript_setter_overlap_audit.py` then
compares MissionRuntime `CheckLevelScriptProperty*` triples against the named
ActionBase setters from the formatter tag audit:

- `0x03b8/0x0a` = `SetBool`
- `0x03e7/0x0a` = `SetInt`
- `0x03ea/0x0a` = `SetIntIncrease`

The CN overlap result is `1,331` decoded setter-key rows and `0` exact
`(mapId, scriptId, key)` matches to the `164` distinct MissionRuntime
property-check triples. There is only `1` same-level/same-key fuzzy match, and
same-key-only matches are generic (`done`, `state`, `start`).

Implication: the normal ActionBase setters are real, but they do not explain
MissionRuntime script-property completion checks in this export. The strongest
recovered timeline signal remains the `0x0bed/0x00` terminal branch walk: for
e0m0 q#7, `battle_field_clear` branches through local `169` to concrete play
records (`cutscene_e0m0_New14`, `radio_e0m0_8d8`, and nearby levelseq nodes).
`0x0a03/0x00` stays diagnostic unless a future row has both a MissionRuntime
bridge and a gate-ref walk to concrete play/story actions.

## 2026-05-19 ManualStart/ManualEnd Follow-up

The missing ManualStart/ManualEnd clue is now partly decoded. The ActionBase
formatter tag table names:

- `0x02f1/0x0a` as `ManualStartLevelScript`.
- `0x02ec/0x0a` as `ManualEndLevelScript`.

`scripts/story_builder/levelscript_binary.py` now labels these rows, and
`scripts/story_recovery/build_levelscript_manual_control_audit.py` writes
`reports/mission_order/levelscript_manual_control_audit.{json,md}`.

Current global result:

- `84` manual control rows.
- `48` ManualStart rows and `36` ManualEnd rows.
- `74` rows are paired with the preceding trigger-volume ScriptEvent by local
  id (`0x12a1` enter -> ManualStart, `0x12a3` leave -> ManualEnd).
- `4` rows carry a literal script-id operand; the rest use the common
  default/parameterized operand payload.
- `0` rows carry a literal cross-script target; the literal script-id operands
  point back to the current script.
- `47` rows live in files that also contain story/playback text.

This is real script activation evidence. It is not, by itself, a cross-script
timeline edge: most rows do not serialize a literal `levelId + scriptId`
target, and the trigger-adjacent rows usually describe when the current
LevelScript activates/deactivates. For e0m0, locals `201 -> 202` and
`203 -> 204` confirm trigger-enter ManualStart and trigger-leave ManualEnd
around script `indie_dg002/8700040000`, while the direct scene-order recovery
still comes from the `0x0bed` `battle_field_clear` branch walk.

## 2026-05-19 Terminal Branch Tie-break And IL2CPP ActionMap Follow-up

The strict MissionRuntime bridge pass still yields only one terminal branch
that can move quest phase: `indie_dg002/8700040000` `battle_field_clear`
for `e0m0_q#7`, already used for `cutscene_e0m0_New14` and
`radio_e0m0_8d8`. The other bridged `0x0bed/0x00` rows are real property
bridges but their branch walks resolve to control/setup records rather than
concrete play/story actions:

- `c13m1` `isSuccceeded` rows in `map01_lv001/2100350001`,
  `2100350004`, and `2100350005`.
- `sm2l1m1` / `sm2l1m2` `start` rows in `map02_lv001/10100020011`
  and `10100020024`.

A narrower local-order promotion was added to
`scripts/story_recovery/build_story_order.py`: terminal branch evidence may
now break same-phase/same-rank ties only when both scenes are in the same
source script, the same `0x0bed` terminal record, the same nonzero branch
root, and each scene has a unique branch membership for that terminal. On the
current CN export this finds `8` safe nonzero path constraints, but they all
already agree with the existing order. The rows that would currently move are
blocked because they depend on branch-root `0` or on scenes reachable through
multiple alternative branches; those remain diagnostics until branch-root `0`
is proven to be a real local id rather than a sentinel in each context.

Implementation note: the terminal-branch tie grouping now handles valid
integer `targetOffset` rows. An earlier indentation bug populated groups only
for missing/non-integer target offsets, so the safe nonzero constraints were
computed by audits but not actually available to the story-order topological
tie pass.

The IL2CPP metadata path also narrowed the missing runtime layer. The
`LevelScriptData.actionMap` field is serialized as
`Beyond.Gameplay.Actions.ActionMapAssetRaw`, whose `dataMap` is
`Beyond.Gameplay.Actions.ActionSerializedMap`. Runtime fields are named
`headerList`, `actionList`, and `getterList`; GameAssembly body recovery
dispatches setters in `actionList`, `getterList`, then `headerList` order, and
the binary blobs carry the first count in the actionMap header and the later
two counts immediately before the next UID record. The action-map list audit
now cross-checks that order against content signatures: `getterList` has the
expected low PureGetter families, while `headerList` is strongly
ScriptEvent/header dominated. It also recognizes `1,373` two-block files
where the getter block is omitted/empty and
the final count is header-shaped. The normal
`ActionBase` union table explains the mid-range action codes, and the
`ScriptEventHeader` union table plus base offsets explains `0x12a*`/`0x13a*`.
No extracted MemoryPack union table names `0x0a03` or `0x0bed` directly. The
generic/list element type metadata is now resolved through
`levelscript_action_map_type_indices`: `actionList=List<ActionBase>`,
`getterList=List<PureGetter>`, and `headerList=List<ActionHeader>`. The
remaining clue is therefore any still-unnamed compact non-ActionBase runtime
family, not a missing ActionBase formatter tag, random outside-map record, or
unresolved generic list element.

## 2026-05-19 Header Event Chain Follow-up

The original game data now recovers a large class of scene starts directly:

```text
headerList event opcode/name
-> compact ActionHeader.nextId payload field
-> actionList local id
-> nextId / split-list / terminal-branch action walk
-> named play action or story-like text
```

The fixed UID record trailer `nextId` is usually `0` for header rows and is not
the event start edge. The start edge is the compact `ActionHeader` payload
field. GameAssembly body recovery pins the runtime setter sequence:
`ActionHeaderForMemoryPack.set____nextID__` writes the runtime field at
`+0x60`, with adjacent priority / trigger / filter fields at `+0x64` through
`+0x78`. In the compact LevelScript blobs, the same `nextId` value is the
little-endian i32 at payload offset `+0x5`.

`scripts/story_recovery/build_levelscript_header_chain_audit.py` uses this
field to audit every decoded LevelScript file. The latest follow-up extends
derived ActionHeader banks down to `0x0e00` and `0x0f00`, naming the remaining
low-bank headers such as `LevelEvent_OnSquadInFightChanged`,
`OnHitByLaser`, and `OnSettlementReadyPerformance`. Current global result:

- `10,085` header rows in `2,669` files.
- all `10,085` header rows named by MemoryPack-derived ActionHeader mapping.
- `9,961` header rows target an `actionList` row by payload
  `ActionHeader.nextId`.
- `123` rows target duplicate/ambiguous `actionList` local ids.
- `0` rows have a missing/nonexistent positive target id.
- `0` header rows target non-action records.
- `1,647` event target chains contain a named play action.
- `1,791` event target chains carry scene-like text.
- `1` row has no positive next edge.

This makes event-started dialog/radio/cutscene playback recoverable for many
mission scripts. For example, `ScriptEvent_OnLeaderEnterTriggerVolume` in
`base01_lv001/9800010002` jumps to an action chain that plays
`cutscene_e0m2_4`, then `dlg_e0m2_4`, then `radio_e0m2_1`.
`scripts/story_recovery/build_story_order.py` now surfaces this as
`headerEventEvidence` on generated `story_order.json` entries when a header
chain reaches a concrete play/story record. Current CN rebuild annotates
`1,351` entries across `179` missions; this is a trigger/event-path
diagnostic, not a standalone cross-scene chronology promotion.

The current `story_order.json` builder also promotes a narrower scene-order
case: same-script `levelscriptSceneChain` edges can keep weak
`content-suffix-fallback` groups together when all affected entries come from
the same source script and scene chunk. This promoted `74` weak fallback entries
across `31` missions in the latest rebuild. For e0m0 it fixes the hub-key
sequence from `indie_dg004/23900030000`, ordering
`cutscene_e0m0_6 -> cutscene_e0m0_7 -> cutscene_e0m0_8` as
`levelscript-scene-chain:c1` immediately after the q#7 branch. Explicit
AnimeStudio `timelinePlayable` video bindings remain standalone WebUI rows but
inherit adjacency from their bound story key; the only current example is
`video_cs_video_e0m0_3` after `cutscene_e0m0_3`.

Gameplay-observed calibration is now a separate, labelled layer. The only
current hint file is `scripts/story_recovery/manual_observed_order_hints.json`
for e0m0. Rows moved by this layer use
`observed-gameplay-calibration`, `observed-aligned:*`, or
`observed-compatible:*` evidence labels and preserve their previous
decoded/static evidence in `recovered*BeforeObserved` fields. Each observed
row also carries an `observedEvidenceAlignmentStatus`: `source-backed`,
`partial`, or `gap`. Do not count those observed hints as firm original-data
order when reporting evidence coverage; use them to find the next
activation/control-flow clues that the static recovery is still missing.

For the current e0m0 hint set, 45 observed rows are calibrated:
15 `source-backed`, 27 `partial`, and 3 `gap`. The added reading popup
`text_e0m0_1` is source-backed by `ShowUIReadingPopPanel` in
`8700020018`; the added tail has real support as two source clusters:
`8700050001` q#11 boss/final-area trigger-volume rows, and
`23900030000` hub-key scene-chain rows for `cutscene_e0m0_6 -> 7 -> 8`.
The exact boss-cluster radio/cutscene interleave, plus
`radio_e0m0_9d5`, `radio_e0m0_10`, and `radio_e0m0_21`, still needs local
branch/event-header/activation decoding; raw script offset order is not
enough.

Remaining limits: this is trigger/action evidence, not a total mission
timeline by itself. Runtime ordering among simultaneously active trigger
headers still depends on quest state, trigger volumes, properties, battle
signals, and other conditions. Non-play chains are still useful for state and
gate reconstruction but should not be promoted as scene chronology until their
downstream play/story edge is decoded.

## Case Study: Cutscene-Identification Metadata Already Available

`webui/data/lang/<lang>/conv/cutscene_*.json` already exposes rich
author-supplied identification for every cutscene, but the WebUI
mission-timeline chunk view renders only the bare `sceneKey` chip:

- `cutscene.tags` — author labels in mission language. e0m0 examples:
  `"indie, dg002, 巡野, 索道, 第一个"` (first zipline), `"迎战巨石"`
  (boulder fight), `"与配崩的对话"` (Pei dialogue), `"看爱国者"` (look
  at Patriot).
- `cutscene.paths` — distinguishes
  `Assets/.../Cutscene/...` vs `Assets/.../CutsceneTransition/...`, so
  cinematic vs gameplay transition is recoverable.
- `cutscene.metadata` — `isTransition`, `useBlackScreen`, `skipType`,
  `narrativeTypeTag` provide categorical info; the `summary[*].text`
  block already serializes a "Flags: transition, black-screen" line.
- `cutscene.audioEvents` — names like
  `au_music_cs_tundra_000_boss_intro` or
  `au_vo_cs_e0m0_3_f/m` are useful disambiguators when the bare key is
  opaque (`cutscene_e0m0_tombstonecollapseCam`).
- `lines[*]` length — zero-line cutscenes are almost always
  cinematics/transitions; multi-line cutscenes are dialog scenes.

The cutscene panel (`renderCutscenePlacementEdges` /
`renderConversation`) shows these when an entry is opened, but the
chunk view in `renderMissionTimelineSceneChunks` and the unconfirmed
order list in `renderMissionTimelineSceneOrder` do not. Surfacing a
one-line label per scene chip in those two views is a small, additive
WebUI change that does not require any new evidence extraction.
