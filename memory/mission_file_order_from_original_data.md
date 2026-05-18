# Correct happen-order of files within a mission — evidence from original game data

Fresh extraction starting from `export_full/structured/` (raw exported game tables) only.
Existing recovery code and prior investigation memory are ignored on purpose.

## "Files within a mission" — what they actually are

For a mission `<missionId>` (e.g. `a1m2`, `e1m1`), the per-mission asset files
referenced by the game are:

- `MissionRuntimeAsset/<missionId>.json` — the canonical mission file (quests, DAG).
- `MissionRuntimeAsset/<missionId>_meta.json` — small mission meta (acceptMode, level).
- `LipSync/<Lang>/au_dlg_<missionId>_<chunk>_<line>.json` — per-line lipsync.
- `LevelScriptData/<levelId>/<numericScriptId>.json` — binary level scripts that
  trigger a single dialog chunk; each script references at most one `dlg_<missionId>_<chunk>`.
- Persistent tables that list per-mission rows: `DialogIdTable`, `DialogTextTable`,
  `DialogOptionTable`, `NpcProxyExDataTable`, `AudioDialog` (`.wem` paths),
  `MissionExtraInfoTable`.

The unit the question is about is the **dialog/scene chunk**:
`dlg_<missionId>_<chunk>` (e.g. `dlg_a1m2_1` ... `dlg_a1m2_4`). The lipsync files
share that chunk number as their middle component.

## The ordering signal in original game data

The only original-data structure that explicitly encodes runtime ordering of
chunks within a mission is the **quest DAG** in
`MissionRuntimeAsset/<missionId>.json`:

- Each entry in `questDic` has `prevQuestIdList: [<questId>...]`.
- Those edges define a partial order (DAG) over quests. The quest at the head of
  this DAG (the one with `prevQuestIdList: []`) is the entry quest.
- Each quest references the chunk it triggers via, in decreasing strength:
  1. `objectiveList[].condition._dialogId.constValue = "dlg_<missionId>_<n>"`
     — the quest is *gated* by that chunk finishing.
  2. `objectiveList[].trackingInfoList[].npcProxyId = "<proxy>"` — the quest is
     tracked on an NPC proxy; the proxy → dialog mapping is in
     `GameplayConfig/NpcProxyExDataTable.json` (`<proxy>.dialogId`).
  3. `objectiveList[].trackingInfoList[].snsDialogId` / `jumpId` — non-chunk
     content (SNS or activity gameplay), still ordered by the same DAG.
- Quests not referencing any chunk are still ordered by the DAG and act as
  spacing/gating between dialog phases.

Anything that joins to a quest in the DAG inherits the quest's DAG position.
The chunk numeric suffix (`_1`, `_2`, ...) is a designer convention only and is
not always monotonic with the DAG (see e1m1 below); rely on the DAG.

Chunks with `missionId=""` in `NpcProxyExDataTable` are environmental/standalone
NPC dialogs, not part of the mission's gated chain.

## Worked example — `a1m2`

Sources, raw:
- `export_full/structured/StreamingAssets/Data/Json/MissionRuntimeAsset/a1m2.json`
- `export_full/structured/Persistent/Data/Json/GameplayConfig/NpcProxyExDataTable.json`
- `export_full/structured/Persistent/Table/DialogTextTable.json` (presence-only)

Chunks present in `DialogTextTable` for `a1m2`: `dlg_a1m2_1`, `dlg_a1m2_2`,
`dlg_a1m2_3`, `dlg_a1m2_4`.

Quest DAG from `prevQuestIdList` (root has empty prev):

```
a1m2_q#3 (root)
 -> a1m2_q#4
 -> a1m2_q#Day1
 -> a1m2_q#6
 -> a1m2_q#Day2
 -> a1m2_q#7
 -> a1m2_q#Day3
 -> a1m2_q#9
 -> a1m2_q#Day4
 -> a1m2_q#11
 -> a1m2_q#Day5
 -> a1m2_q#13
 -> a1m2_q#Day6
 -> a1m2_q#15
 -> a1m2_q#Day7
 -> a1m2_q#5
 -> a1m2_q#18
```

Chunk bindings, all from the same files:
- `q#3` tracks `npcProxyId = kelala_map01_v1d1d0_002`
  -> `NpcProxyExDataTable["kelala_map01_v1d1d0_002"].dialogId = dlg_a1m2_1`,
     `missionId = a1m2`.
- `q#4` condition `_dialogId.constValue = "dlg_a1m2_1"` (gating chunk 1).
- `q#Day1..Day7` (with `q#6/7/9/11/13/15` as `dungeon_fighting_<n>` gates):
  `trackingInfoList[].jumpId = jump_dungeon_activity_monster_1` —
  combat-stage phase, no story chunk.
- `q#5` tracks `npcProxyId = kelala_map01_v1d1d0_004`
  -> `dlg_a1m2_3`, `missionId = a1m2`.
- `q#18` condition `_dialogId.constValue = "dlg_a1m2_3"` (gating chunk 3).

`NpcProxyExDataTable.json` also has:
- `kelala_map01_v1d1d0_003.dialogId = dlg_a1m2_2`, `missionId = a1m2`
  — not gated by any quest in `a1m2.questDic`; it is a mission-tagged NPC
  dialog that is reachable while the mission is active.
- `kelala_map01_v1d1d0_005.dialogId = dlg_a1m2_4`, `missionId = ""`
  — generic NPC dialog, not gated to `a1m2` at all.

**Resulting order for `a1m2`** (gated chunks only, from original data):
```
dlg_a1m2_1   (gated by q#3/q#4, root of DAG)
dlg_a1m2_3   (gated by q#5/q#18, terminal quest in DAG)
```
Combat/SNS spacing between them is the `Day1..Day7` block with
`jump_dungeon_activity_monster_1`.

Ungated chunks for `a1m2`:
```
dlg_a1m2_2   (mission-tagged NPC dialog, proxy _003; reachable during mission,
              no quest gate -> position only constrained by proxy id ordering
              002/003/004/005)
dlg_a1m2_4   (proxy _005, missionId="" -> not part of a1m2's gated chain)
```

## Worked example — `e1m1` (where the numeric suffix is misleading)

Sources, raw:
- `export_full/structured/StreamingAssets/Data/Json/MissionRuntimeAsset/e1m1.json`
- `export_full/structured/StreamingAssets/Data/Json/LevelScriptData/map01_lv001/{2100050029,2100050039,2100050066,2100050067,2100050068,2100050069,2100050070,2100050071,2100660001}.json`
- `NpcProxyExDataTable.json`

`e1m1.questDic` uses only non-dialog conditions
(`GameConditionServerPlaceHolder`, `CheckGuideGroupComplete`,
`CheckScriptMonsterKilled`, `PlayerHasItem`, `ReachDestination`), so chunks
are not gated by `_dialogId` here.

DAG root is `e1m1_q#Deco_showLandslide` (`prevQuestIdList: []`). Following the
edges and noting each quest's `objectiveList[].description.key`
(`objective_e1m1_<phase>_001`), the linear chain of phases encountered is:

```
2, 1, 1, 2, 1, 3, 4, 4, 5, 13, 5, 13, 5, 1, 5, 5, 6, 7, 7, 8, 8, 8, 8, 8, 8,
15, 15, 16, 16, 17, 17, 7, 17, 9, 9, 19, 13, 21, 10, 11, 11, 11, 12, 12, 12,
18, 18, 18, 18, 18
```

Collapsed first-occurrence order of the description phase:
```
2 -> 1 -> 3 -> 4 -> 5 -> 13 -> 6 -> 7 -> 8 -> 15 -> 16 -> 17 -> 9 -> 19 -> 21
  -> 10 -> 11 -> 12 -> 18
```

So the `objective_e1m1_<N>_001` numbering is **not** monotonic along the DAG;
the chunk's literal numeric suffix in the filename is a designer index, not the
play order. The reliable ordering signal here is still the DAG, joined to
chunks via NPC proxies and dedicated LevelScript binaries:

- `andrew_map01_e1m1Basement2 -> dlg_e1m1_7`
- `chen_map01_e1m1Basement1 -> dlg_e1m1_6`
- `qinjc_map01_e1m1Frontline1 -> dlg_e1m1_3`
- LevelScript binaries each trigger one chunk:
  `2100050039 -> dlg_e1m1_1`,
  `2100050066 -> dlg_e1m1_2`,
  `2100050068 -> dlg_e1m1_4`,
  `2100050069 -> dlg_e1m1_5`,
  `2100050070 -> dlg_e1m1_6{d1,d2}`,
  `2100050071 -> dlg_e1m1_6d3`,
  `2100050029 -> dlg_e1m1_4d2`,
  `2100050067 -> dlg_e1m1_4d3`,
  `2100660001 -> dlg_e1m1_1`.

A LevelScript fires when its in-script condition is satisfied, which in turn
references one of the `e1m1_q#NN` quest states (e.g. `2100660001` references
`e1m1_q#07`, `e1m1_q#53`, `e1m1_q#54`). So each chunk's actual position is
ultimately given by the quest-DAG position of the script's gating quest.

## Method summary (so the same extraction can be repeated)

For any mission `<missionId>`:

1. Read `MissionRuntimeAsset/<missionId>.json`. Build the quest DAG from
   `questDic[*].prevQuestIdList`. The root(s) are quests with empty prev.
2. For each quest, collect chunk bindings:
   - `objectiveList[*].condition._dialogId.constValue` (direct gate).
   - `objectiveList[*].trackingInfoList[*].npcProxyId`, then join to
     `NpcProxyExDataTable.json[<proxy>][*].dialogId` (with `missionId == <missionId>`).
   - `objectiveList[*].trackingInfoList[*].snsDialogId` / `jumpId` for SNS /
     activity spacing.
3. For chunks not gated by any quest above, also scan
   `LevelScriptData/<levelId>/*.json` for `dlg_<missionId>_<chunk>` and for
   `<missionId>_q#<id>` references. Each script's gating quest gives its DAG
   position.
4. Topologically sort the quests. Chunks inherit the position of their gating
   quest. Chunks bound to NPC proxies whose row has `missionId == ""` are
   generic NPC dialogs and not part of the gated chain.

This procedure uses only `export_full/structured/...` JSON data — no recovered
timelines, no inferred ordering, no prior investigation memory.
