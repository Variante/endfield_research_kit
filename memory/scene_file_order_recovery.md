# Scene File Order Recovery From Original Game Data

Investigation date: 2026-05-14

This pass intentionally treats existing WebUI/story outputs as non-authoritative.
The goal is to identify original-game-data evidence for ordering story/dialog
files that belong to one scene or mission.

## Best Evidence Stack

1. **MissionRuntimeAsset quest graph**
   - Source: `export_full/structured/StreamingAssets/Data/Json/MissionRuntimeAsset/*.json`
   - Ordering signal: `questDic[*].prevQuestIdList` plus quest-local story
     references such as `_dialogId`, `snsDialogId`, `_cutsceneId`,
     `_remoteCommId`, and `_radioId`.
   - This is the best source for ordering separate files inside one mission
     scene because the game runtime must satisfy quest predecessor edges before
     later quest nodes.
   - Treat it as a DAG/partial order. Do not force branches with the same
     predecessor into one invented sequence.

2. **DialogTree graph inside each `dlg_*` TextAsset**
   - Source:
     `export_full/recovered/AnimeStudio-cli/*/json_by_type/TextAsset/dlg_*.json`
   - The `m_Script` field is base64 JSON. Decoding exposes
     `Beyond.Gameplay.DialogTree` with `nodes`, `connections`, and `_position`.
   - Ordering signal: `connections[*]._sourceNode.$ref ->
     connections[*]._targetNode.$ref`. `_position.x/y` is useful as layout
     evidence and tie-break/debug evidence, not as the primary runtime edge.
   - This orders trunks/options within a single dialog file, not separate
     mission-scene files.

3. **Timeline clip windows for cinematic dialog**
   - Source:
     `export_full/recovered/AnimeStudio-cli/timeline_extract/**/MonoBehaviour/*.json`
     and the derived compact catalog
     `export_full/recovered/AnimeStudio-cli/timeline_line_orders.json`.
   - Ordering signal: `DialogTrunkPlayableAsset` clip `start`/`duration`, track,
     binding, and `assetTrunkId`/line ids.
   - This is strongest for `dlgtl_*` cinematic/timeline-backed scenes and for
     cases where line suffix order disagrees with authored Timeline time.

4. **Runtime registry and summary tables**
   - Sources:
     `export_full/recovered/dialog_id_table_index.json`,
     `export_full/structured/StreamingAssets/Table/DialogSummaryMapTable.json`,
     `DialogTextTable.json`, `DialogOptionTable.json`.
   - These prove registration, line membership, option membership, and summary
     presence. They do not by themselves prove chronological order between
     separate scene files.

## Fresh Coverage Checks

Quick scan of `MissionRuntimeAsset` found:

- `418` mission runtime assets.
- `3,736` quest nodes.
- `185` missions contain story file references.
- `504` quest nodes contain story references.
- `548` total story refs across `_dialogId`, `snsDialogId`, `_cutsceneId`,
  `_remoteCommId`, and `_radioId`.

Quick scan of decoded `dlg_*` TextAssets found:

- `4,223` decoded DialogTree graphs.
- `52,194` graph nodes.
- `49,413` graph edges.
- `3,598` graphs with a single root node.
- `2,423` graphs with branch nodes.

Timeline catalog evidence currently covers:

- `290` recovered dialog Timeline assets.
- `273` dialog keys.
- `200` option Timelines.
- `781` option clips.
- `816` option anchors.
- `66` option route records.

## Example Evidence

`c17m3` mission graph order:

```text
c17m3_q#0d5  prev=[]              -> _dialogId=dlg_c17m3_1
c17m3_q#2    prev=[c17m3_q#1]     -> _dialogId=dlg_c17m3_2
c17m3_q#5    prev=[c17m3_q#4]     -> _dialogId=dlg_c17m3_8
```

`a1m10` mission graph order:

```text
a1m10_q#1    prev=[]              -> snsDialogId=sns_a1m10_1
a1m10_q#2    prev=[a1m10_q#1]     -> _dialogId=dlg_a1m10_1
a1m10_q#6    prev=[a1m10_q#5]     -> _dialogId=dlg_a1m10_2
```

Decoded `dlg_a1m8d1_1` DialogTree begins with explicit edges:

```text
0 -> 1
0 -> 22
1 -> 2
2 -> 3
3 -> 4
4 -> 5
5 -> 6
```

Its node layout also moves left-to-right:

```text
node 0 x=200 y=200
node 1 x=600 y=200
node 2 x=1000 y=200
node 3 x=1400 y=200
```

Timeline example `dlg_c28m3_23` has authored clip time order that skips numeric
suffixes:

```text
dlg_c28m3_23_001  start=0.1833
dlg_c28m3_23_003  start=7.0167
dlg_c28m3_23_004  start=14.65
dlg_c28m3_23_005  start=18.4833
dlg_c28m3_23_007  start=40.55
```

That proves numeric suffix order is at best a fallback, not the primary
ordering source.

## Recommended Recovery Algorithm

For ordering files within a mission/scene:

1. Load the relevant `MissionRuntimeAsset/<mission>.json`.
2. Build a quest DAG from `questDic[*].prevQuestIdList`.
3. Extract story refs from each quest node, including nested objective
   conditions and client action maps.
4. Emit ordered groups by DAG layer:
   - If A is an ancestor of B, A's story refs precede B's refs.
   - If two quest nodes are siblings under the same predecessor and no edge
     connects them, keep them as parallel alternatives instead of imposing an
     arbitrary order.
5. Within a single quest node, preserve local list order for refs from the same
   array/object path, but mark it as local-authoring order rather than global
   chronology.
6. For each referenced `dlg_*` file, decode the DialogTree and use its explicit
   node connections for intra-file trunk/option flow.
7. For any referenced `dlgtl_*` or Timeline-backed dialog, use Timeline clip
   `start` time as stronger intra-file line order.
8. Attach registry/summary/table evidence only as validation:
   registered/unregistered, line membership, option membership, summary
   presence, text availability.

## Avoid

- Do not sort scene files only by filename suffix.
- Do not use extracted filesystem order or VFS chunk order as narrative order.
- Do not flatten quest branches unless an original source edge proves a merge or
  predecessor relation.
- Do not use generated WebUI rank/order as evidence for this recovery pass.

