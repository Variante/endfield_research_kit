# e0m0 — full file happen-order from original game data

Goes beyond the JSON quest DAG by decoding the binary `LevelScriptData/indie_dg002/*.json`
opcode records. Sources used (all under `export_full/structured/`):

- `StreamingAssets/Data/Json/MissionRuntimeAsset/e0m0.json`, `e0m0_meta.json`
- `StreamingAssets/Data/Json/LevelScriptData/indie_dg002/87000*.json` (binary blobs)
- `StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json`
- `Persistent/Table/AudioDialog.json` (Wwise paths)
- `Persistent/Table/DialogTextTable.json` (line counts)
- `Persistent/Table/TextTable.json` and `I18nTextTable_CN.json`
- AnimeStudio asset map at `recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json`

## 2026-05-18 correction

- `cutscene_e0m0_3` is not evidence-bound to `cs_video_e0m0_3`. The cutscene
  has its own TextTable rows, PlayableDirector/AnimeStudio `f_/m_cutscene_*`
  assets, and LevelScript play-cutscene occurrences. The
  `video_cs_video_e0m0_3` WebUI row is a standalone narrative video row with
  no non-name binding to that cutscene.
- `cutscene_e0m0_3` as the first story entry is supported by decoded story
  text, not by the video filename: `TextTable[cutscene_e0m0_3_01]` resolves
  through `I18nTextTable_CN` to a title card containing `00:00:00`.
- The gap between `radio_e0m0_1d5` and `radio_e0m0_2` is supported by
  `levelseq_e0m0_001` in `8700020001`, where `cutscene_e0m0_2` appears near
  that level sequence.
- The `radio_e0m0_2d8` to `radio_e0m0_3d2` gap is partly supported:
  `cutscene_e0m0_1stZipline` is directly anchored to `levelseq_e0m0_003` in
  `8700020023`; `radio_e0m0_3d2` still only has weak suffix/file evidence.
- Follow-up audit found that `story_order.json` must scan secondary mission
  level refs too. `webui/data/lang/CN/mission/e0m0.json` points at
  `LevelData/indie_dg004/indie_dg004_lv_data_sub_mission_e0m0.json`, whose
  `LevelScriptData/indie_dg004/23900030000.json` plays
  `cutscene_e0m0_6`, `cutscene_e0m0_7`, and `cutscene_e0m0_8`; these should not
  remain pure WebUI fallbacks.
- `cutscene_e0m0_2ndZipline*` has original LevelScript evidence in
  `indie_dg002/8700010008.json` but no numeric `levelseq_e0m0_00N` anchor.
  The current WebUI order keeps it near `cutscene_e0m0_1stZipline` using the
  authored ordinal names `1stZipline` / `2ndZipline`; this is weaker than a
  quest/property or numeric levelseq anchor and is labelled as such.

## 2026-05-18 runtime playback check

Freshness check: `scripts/verify_export_freshness.py` reports the WebUI export
matches the installed `StreamingAssets` and `Persistent` roots. `il2cpp_data`,
`Plugins`, and `Resources` are not exported by the WebUI source set, so IL2CPP
metadata is read from the installed game/cache separately.

IL2CPP metadata does not contain an authored e0m0 playlist. What it confirms is
the runtime path used by the serialized files:

- `Beyond.Gameplay.LevelScriptData` serializes `scriptId`, `startType`,
  `endType`, `activeShapeList`, `startShapeList`, `actionMap`, `taskMap`,
  `modules`, `properties`, and `propertyIdToKeyMap`.
- `Beyond.Gameplay.Core.LevelScriptContainer.LoadFromLevelData` loads those
  scripts into `allLevelScriptDict`, `activeLevelScriptDict`,
  `enabledLevelScriptDict`, `m_waitingActiveList`, and `m_waitingStartList`.
- `Beyond.Gameplay.Core.LevelScriptRuntime` runs the lifecycle:
  `OnScriptActive`, `OnScriptStart`, `ManualStart`, `ManualEnd`, `Tick`,
  `ServerSyncProperties`, and property/task/timer runtime state.
- `Beyond.Gameplay.CheckLevelScriptPropertyBool/Int/String` stores `_mapId`,
  `_scriptId`, `_key`, `_value`, and `_comparer`, then resolves the runtime
  `m_levelScriptPtr`/`m_propertyPath`.
- `Beyond.Gameplay.Actions.ManualStartLevelScript` and
  `ManualEndLevelScript` serialize `levelId` + `scriptId`, confirming that
  scripts can be explicitly started/ended by action nodes.

So the source-backed order evidence remains the serialized LevelScriptData and
MissionRuntimeAsset data, not IL2CPP method names by themselves. IL2CPP is
useful for proving that the fields we decode (`scriptId`, action maps, start
shapes, property checks, manual starts) are real runtime concepts.

## 2026-05-18 LevelData control layer

There is a higher layer than raw LevelScript play-record byte order, but it is
not a flat authored playlist. IL2CPP metadata confirms the runtime hierarchy:

- `Beyond.Gameplay.LevelData` owns `levelScripts`,
  `levelScriptDataPathDict`, and `levelScriptBriefDataDict`.
- `Beyond.Gameplay.LevelScriptBriefData` stores `scriptId`, `dataPath`,
  `levelScriptType`, `parentLevelScriptId`, `maxStage`, `properties`, and
  `propertyIdToKeyMap`.
- `Beyond.Gameplay.LevelScriptData` stores the executable script body plus
  `startType`, `endType`, `activeShapeList`, `startShapeList`, `actionMap`,
  `taskMap`, `modules`, `properties`, `triggerVolumes`, and
  `propertyIdToKeyMap`.
- `Beyond.Gameplay.Core.LevelScriptContainer.LoadFromLevelData` loads the
  `LevelData` catalog into runtime script dictionaries, while
  `LevelScriptRuntime` runs `OnScriptActive`, `OnScriptStart`, `ManualStart`,
  `ManualEnd`, `Tick`, state/stage changes, and property sync.
- `LevelScriptStartType` is `ByEnterStartShape`, `Manual`,
  `SameWithActive`, or `Never`; `LevelScriptEndType` is `Auto`,
  `ByExitStartShape`, `Manual`, `SameWithDeactive`, or `Never`.

For e0m0, the LevelData layer gives controller/ownership evidence:

- `indie_dg002_lv_data.json` references the master/controller script
  `8700000016` and early script `8700000004`.
- `indie_dg002_lv_data_sub_mission_e0m1.json` references
  `8700020000`, `8700020001`, `8700020010`, `8700020017`,
  `8700020018`, `8700020019`, `8700020022`, `8700020023`, and
  `8700020026`, with nearby authored property names such as
  `isFinished`, `haveCrossedDebris`, `radioplayed`, `isPlayCS`,
  `pelica_played`, `finishi_final_dialog`, and LevelTimeline markers
  like `lt:p:*` / `lt:mp:*`.
- `indie_dg002_lv_data_sub_levelseq.json` references `8700010001` and
  `8700010008`, with nearby `seqPlayed`, `played`, and `preloaded`
  properties. This is better grouping evidence for the zipline/levelseq
  scripts than filename suffixes alone.
- `indie_dg002_lv_data_sub_01.json` references `8700030000` with
  `telePos3`, `teleRot3`, `ReloadPos`, and `ReloadRot`, supporting it as
  a controlled tutorial/teleport/reload script for `radio_e0m0_3d2`.
- `indie_dg002_lv_data_sub_02.json` references `8700040000` and
  `8700040001`, with `tag_list`, `bomb_postion*`, `pole01`, `pole02`,
  `PlayerPos`, and `PlayerRot`; MissionRuntime q#7 also directly checks
  `8700040000.battle_field_clear`.
- `indie_dg002_lv_data_sub_03.json` references `8700050001`, with
  `FightPos`, `squadPos*`, and `PlayerRotPhase2`, matching the boss-fight
  cluster.
- `indie_dg004_lv_data_sub_mission_e0m0.json` references `23900030000`,
  with `spawn_point`, `spawn_rot`, `Lookat1`, `Lookat2`,
  `HavePickedUp`, `HaveInteracted`, and `teleportcompleted`; this is the
  higher-level source for the `cutscene_e0m0_6/7/8` hub-key sequence.

Cross-script `uint64` references add relationship evidence, but direction is
not yet decoded:

- `8700020000 -> 8700000016` ties the opening script to the master
  controller.
- `8700000016 -> 8700000004` and `8700000016 -> 8700040000` show the
  master referencing the early radio script and the q#7 battlefield script.
- `8700040000 -> 8700040001`, then `8700040001 -> 8700000004`, ties the
  `radio_e0m0_1d5` / `radio_e0m0_2` / battlefield cluster together, but
  does not by itself prove a total order.
- `8700020019 -> 8700020022`, `8700020022 -> 8700020026`, and
  `8700020020 -> 8700030000` are useful graph edges for nearby systems,
  but currently remain undirected evidence.

The next real upgrade is to decode the MemoryPack bodies far enough to expose
`LevelScriptBriefData.startType/endType`, shape lists, trigger volumes, and
action node type IDs. That should identify whether a script is started by
entering a shape, by same-as-active, or by an explicit
`ManualStartLevelScript` action, which is the missing "who starts whom" layer.

Focused e0m0 playback records from `LevelScriptData/indie_dg002`:

```
8700020000:
  0x0054 code=0335 kind=0b au_special_cs_e0m0_1_mask_amb
  0x0640 code=033e kind=13 play_cutscene cutscene_e0m0_2
  0x086f code=034a kind=0d play_radio radio_e0m0_1

8700040001:
  0x0449 code=034a kind=0d play_radio radio_e0m0_1d5

8700020001:
  0x003b/0x00be/0x0180 play_levelseq levelseq_e0m0_001
  0x0207/0x04ae cutscene_e0m0_2 payloads with currently unclassified wrappers

8700000004:
  0x0038 code=034a kind=0d play_radio radio_e0m0_2
  0x083d code=034a kind=0d play_radio radio_e0m0_2d8

8700020023:
  0x0007/0x008a play_levelseq levelseq_e0m0_003
  0x014c code=035b kind=0c play_cutscene cutscene_e0m0_1stZipline

8700030000:
  0x0eb2 code=034a kind=0d play_radio radio_e0m0_3d2

8700020022:
  0x05c7 code=035b kind=0c play_cutscene cutscene_e0m0_3
  0x0820 code=034b kind=0d play_radio radio_e0m0_12

8700020028:
  0x0033 code=035b kind=0c play_cutscene cutscene_e0m0_3
  0x0e7d code=02e6 kind=09 play_levelseq levelseq_e0m0_tombstonecollapse

8700050001:
  0x2b51 code=033e kind=13 play_cutscene cutscene_e0m0_3
```

The direct MissionRuntime script/property links for e0m0 are only:

```
e0m0_q#2: EntityTrackingInfo scene=indie_dg002 scriptId=40001 slot=40010
          (not a LevelScriptData/indie_dg002/40001.json file)
e0m0_q#7: CheckLevelScriptPropertyBool mapId=indie_dg002
          scriptId=8700040000 key=battle_field_clear value=true
```

This means `8700040000` is directly quest-gated by q#7, but the early
`8700000004`, `8700020001`, `8700020023`, `8700030000`, and `8700040001`
placements still need non-property evidence such as levelseq anchors,
same-script offset order, spatial/quest proximity, or content suffixes.

The binary decoder is `scripts/story_builder/level_bindings._load_levelscript_binding_data`,
which walks the record layout (`0xFA`-tagged 32-byte header or plain 30-byte header,
`code`/`kind`/`localId`/`nextId`/`payloadStart`) and pairs records to tagged ASCII
strings (`0x04 <le32 len> <ascii>`) in the same file.

## Four ordering signals in the original data

1. **Quest DAG** in `MissionRuntimeAsset/e0m0.json questDic`, linear chain:
   `q#1 → q#2 → q#3 → q#4 → q#5 → q#6 → q#7 → q#8 → q#9 → q#10 → q#11 → q#12 → q#13`.
   Each quest carries its own area / pos / property gate (see §A).

2. **Numbered levelseq names** `levelseq_e0m0_001 .. _012`, monotonic in
   the binary script string tables. This is the story-beat backbone the
   designers actually wrote into the data (§B).

3. **Per-script binary offset** order within each `LevelScriptData/indie_dg002/<id>.json`
   blob. SerializeReference layout preserves authoring order, so the byte
   offsets of `0x04`-tagged strings inside one script are an honest
   "what fires next in this script" order (§C).

4. **Decoded title-card time text** from `TextTable` + `I18nTextTable_CN`.
   This is the source for placing `cutscene_e0m0_3` first; it is independent
   of `cs_video_e0m0_3`.

## §A — Quest DAG with tracked gates

```
[0]  e0m0_q#1   prev=[]          area=e0m1_001 → e0m1_002  (split by haveCrossedDebris)
[1]  e0m0_q#2   prev=[q#1]       follow scriptEntity scriptId=40001 slot=40010
[2]  e0m0_q#3   prev=[q#2]       pos=(-109,56,-65) → pos=(-82,61,-54)  (CombatTutorDone)
[3]  e0m0_q#4   prev=[q#3]       area=e0m1_003
[4]  e0m0_q#5   prev=[q#4]       pos=(1,59,137) → pos=(16,59,173)      (beforetowerTracker)
[5]  e0m0_q#6   prev=[q#5]       area=e0m1_004
[6]  e0m0_q#7   prev=[q#6]       property=8700040000.battle_field_clear
                                  + pos=(90,71,295) → pos=(168,59,388) (EnterBattlleField)
[7]  e0m0_q#8   prev=[q#7]       area=e0m1_008
[8]  e0m0_q#9   prev=[q#8]       area=e0m1_005
[9]  e0m0_q#10  prev=[q#9]       area=e0m1_006
[10] e0m0_q#11  prev=[q#10]      area=e0m1_007
[11] e0m0_q#12  prev=[q#11]      (no track — server placeholder)
[12] e0m0_q#13  prev=[q#12]      (no track — server placeholder)
```

## §B — levelseq backbone (monotonic story beats)

| seq | script that plays it (binary blob `indie_dg002/<id>.json`) |
|-----|------------------------------------------------------------|
| 001 | `8700020001` (also fires `cutscene_e0m0_2`)                |
| 002 | `8700020002`                                               |
| 003 | `8700020023` (also fires `cutscene_e0m0_1stZipline`)       |
| 004 | `8700020004`                                               |
| 005 | `8700020009`, `8700020010` (also fires `radio_e0m0_5d6`)    |
| 006 | `8700020013`                                               |
| 007 | `8700020026` (also fires `levelseq_e0m0_giganticmonsterinthebackground`, `radio_e0m0_8d9`, `cutscene_e0m0_lookingatpatriot`, `levelseq_e0m0_patriotstatuefalling`) |
| 008 | `8700020017` (also fires `levelseq_e0m0_tombstonecollapse`, `cutscene_e0m0_tombstonecollapseCam`) |
| 009 | `8700020018` (also fires the 4 dialog chunks — see §C)     |
| 010 | `8700020018`, `8700020019`                                 |
| 011 | `8700020019`                                               |
| 012 | `8700020019` (also fires `radio_e0m0_11`)                  |

The numeric levelseq suffix is an authored monotonic index — directly an
ordering signal in the original data. Script IDs (`87000200xx`) do not
match the seq order (e.g. seq `003` lives in `8700020023`, seq `007` in
`8700020026`) because script IDs are assigned in authoring order, not
story order; the seq number is the canonical story index.

## §C — Per-script content, binary-offset order

Only e0m0 content shown. Offsets are byte positions inside the binary blob.

```
8700000004
  @0x0093  radio_e0m0_2
  @0x0898  radio_e0m0_2d8

8700000016  (mission master — quest state transitions)
  @0xfa6   e0m0_q#2     @0xfe7   e0m0_q#6     @0x105e  e0m0_q#7
  @0x1111  e0m0_q#3     @0x1152  e0m0_q#4     @0x1193  e0m0_q#5
  @0x11d4  e0m0_q#6     @0x1215  e0m0_q#7     @0x1256  e0m0_q#8
  @0x1297  e0m0_q#3     @0x12d8  e0m0_q#4     @0x1319  e0m0_q#5
  @0x135a  e0m0_q#6     @0x139b  e0m0_q#7     @0x13dc  e0m0_q#8
  @0x141d  e0m0_q#8     @0x145e  e0m0_q#11    @0x14a0  e0m0_q#7
  @0x14e1  e0m0_q#12    @0x1564  e0m0_q#10
  @0x1675  e0m0_q#1     @0x16e0  e0m0_q#1     @0x1a0b  e0m0_q#1

8700010000
  @0x005a  levelseq_e0m0_giganticmonsterinthebackground

8700010001  (Patriot statue moment)
  @0x0234  cutscene_e0m0_lookingatpatriot
  @0x0404  levelseq_e0m0_patriotstatuefalling
  @0x079c  radio_e0m0_9
  @0x0a3d  levelseq_e0m0_patriotstatuefalling

8700010002
  @0x009e  levelseq_e0m0_watchtowerhitandfall      (×3 in script)

8700010004:  levelseq_e0m0_meteorfalling
8700010005:  levelseq_e0m0_meteorfalling2

8700010007  (zipline 1)
  @0x0027  cutscene_e0m0_1stZipline
  @0x0130  cutscene_e0m0_1stZipline

8700010008  (zipline 2 — A → cam_effect → B → C-CamOnly → C)
  @0x005a  levelseq_e0m0_2ndZiplineEffectsAllinOne
  @0x00ec  cutscene_e0m0_2ndZiplineA
  @0x02a4  levelseq_e0m0_2ndZiplineA_cam_effect
  @0x0349  cutscene_e0m0_2ndZiplineB
  @0x04df  cutscene_e0m0_2ndZiplineCCamOnly
  @0x0674  levelseq_e0m0_2ndZiplineC
  @0x08ad  levelseq_e0m0_2ndZiplineA_02

8700020000  (opening cinematic)
  @0x0090  au_special_cs_e0m0_1_mask_amb        (audio mask for cs_e0m0_1)
  @0x0660  cutscene_e0m0_2
  @0x08ca  radio_e0m0_1
  @0x0cfc  cutscene_e0m0_2

8700020001
  @0x008e  levelseq_e0m0_001  (×3)
  @0x0235  cutscene_e0m0_2    (×2)

8700020002: levelseq_e0m0_002 (×3)
8700020004: levelseq_e0m0_004 (×2)
8700020009: levelseq_e0m0_005
8700020010: levelseq_e0m0_005 (×2); @0x0fe1 radio_e0m0_5d6
8700020013: levelseq_e0m0_006 (×3)
8700020016: cutscene_e0m0_tombstonecollapseCam

8700020017  (tombstone collapse)
  @0x0027  levelseq_e0m0_008
  @0x0552  levelseq_e0m0_tombstonecollapse
  @0x05b0  cutscene_e0m0_tombstonecollapseCam
  @0x0b70  levelseq_e0m0_tombstonecollapse2ndPart
  @0x0c01  cutscene_e0m0_tombstonecollapseCam

8700020018  (4 dialogs gated to seq 009 / 010 boundary)
  @0x0027  levelseq_e0m0_009
  @0x00ff  levelseq_e0m0_010
  @0x020e  levelseq_e0m0_009
  @0x02f5  dlg_e0m0_0d5
  @0x035e  dlg_e0m0_0d7
  @0x03c7  dlg_e0m0_0d8
  @0x0430  dlg_e0m0_0d9

8700020019  (closes 010, plays 011, 012, radio_11)
  @0x0027  levelseq_e0m0_010
  @0x017a  levelseq_e0m0_011 (×2)
  @0x031d  levelseq_e0m0_012 (×2)
  @0x0708  radio_e0m0_11

8700020022
  @0x05e7  cutscene_e0m0_3
  @0x087b  radio_e0m0_12

8700020023  (zipline 1 entry, plays seq 003)
  @0x005a  levelseq_e0m0_003 (×2)
  @0x016c  cutscene_e0m0_1stZipline

8700020026  (Patriot moment, plays seq 007)
  @0x0027  levelseq_e0m0_007
  @0x008e  levelseq_e0m0_giganticmonsterinthebackground
  @0x0126  radio_e0m0_8d9
  @0x01f3  levelseq_e0m0_007
  @0x0243  cutscene_e0m0_lookingatpatriot
  @0x02af  levelseq_e0m0_patriotstatuefalling

8700020028
  @0x0053  cutscene_e0m0_3
  @0x0e9d  levelseq_e0m0_tombstonecollapse
  @0x1991  e0m0_q#10   (this script gates / advances q#10)

8700030000:  radio_e0m0_3d2

8700040000  (battle-field script; q#7 reads property `battle_field_clear` on this scriptId)
  @0x0105  radio_e0m0_8d4
  @0x14f3  cutscene_e0m0_New14
  @0x162a  levelseq_e0m0_14_light
  @0x1701  radio_e0m0_8d8
  @0x2312  cutscene_e0m0_13

8700040001:  radio_e0m0_1d5
8700040004:  levelseq_e0m0_14_light

8700050001  (boss fight + countdown; ~50 entries)
  bossfightrockfall, bossfightrockfall_left, cutscene_e0m0_4,
  levelseq_e0m0_countdown (×8), cutscene_e0m0_5,
  radio 13, 14, 15, 16 (and 16_1/16_2/16_3), 17, 20, 22, 23,
  cutscene_e0m0_3 (replayed)
```

## §D — Reconstructed happen-order

Combining the three signals:

```
PROLOGUE (before q#1 fires)
  cutscene_e0m0_3                                   [TextTable cutscene_e0m0_3_01 time-zero title card]
  cs_e0m0_1   (opening cinematic, 22 sub-clips cs_e0m0_1_001..022)
                                                    [script 8700020000 + au_special_cs_e0m0_1_mask_amb]
  cutscene_e0m0_2                                   [script 8700020000]
  radio_e0m0_1                                       [script 8700020000]

q#1   (enter e0m1_001 → e0m1_002, crossing debris)
  radio_e0m0_1d5                                    [script 8700040001]

q#2   (follow guide scriptEntity 40001)
  levelseq_e0m0_001                                  [script 8700020001]
  cutscene_e0m0_2 (reuse)                            [script 8700020001]
  radio_e0m0_2                                       [script 8700000004]
  radio_e0m0_2d8                                     [script 8700000004]

q#3   (pos near combat-tutor; CombatTutorDone)
  levelseq_e0m0_002                                  [script 8700020002]
  levelseq_e0m0_003                                  [script 8700020023]
  cutscene_e0m0_1stZipline                           [scripts 8700010007, 8700020023]
  radio_e0m0_3d2                                     [script 8700030000; weak suffix placement]
  levelseq_e0m0_2ndZiplineEffectsAllinOne            [script 8700010008]
  cutscene_e0m0_2ndZiplineA                          [script 8700010008]
  levelseq_e0m0_2ndZiplineA_cam_effect               [script 8700010008]
  cutscene_e0m0_2ndZiplineB                          [script 8700010008]
  cutscene_e0m0_2ndZiplineCCamOnly                   [script 8700010008]
  levelseq_e0m0_2ndZiplineC                          [script 8700010008]
  levelseq_e0m0_2ndZiplineA_02                       [script 8700010008]

q#4   (enter e0m1_003)
  levelseq_e0m0_004                                  [script 8700020004]
  levelseq_e0m0_005                                  [scripts 8700020009, 8700020010]
  radio_e0m0_5d6                                     [script 8700020010]

q#5   (pos before tower; beforetowerTracker)
  levelseq_e0m0_006                                  [script 8700020013]
  levelseq_e0m0_007                                  [script 8700020026]
  levelseq_e0m0_giganticmonsterinthebackground       [scripts 8700010000, 8700020026]
  radio_e0m0_8d9                                     [script 8700020026]
  cutscene_e0m0_lookingatpatriot                     [scripts 8700010001, 8700020026]
  levelseq_e0m0_patriotstatuefalling                 [scripts 8700010001, 8700020026]
  radio_e0m0_9                                       [script 8700010001]
  levelseq_e0m0_watchtowerhitandfall                 [script 8700010002]
  levelseq_e0m0_meteorfalling                        [script 8700010004]
  levelseq_e0m0_meteorfalling2                       [script 8700010005]

q#6   (enter e0m1_004)
  radio_e0m0_8d4                                     [script 8700040000]

q#7   (battle_field_clear == true on 8700040000)
  cutscene_e0m0_New14                                [script 8700040000]
  levelseq_e0m0_14_light                             [scripts 8700040000, 8700040004]
  radio_e0m0_8d8                                     [script 8700040000]
  cutscene_e0m0_13                                   [script 8700040000]

q#8   (enter e0m1_008)
  levelseq_e0m0_008                                  [script 8700020017]
  levelseq_e0m0_tombstonecollapse                    [scripts 8700020017, 8700020028]
  cutscene_e0m0_tombstonecollapseCam                 [scripts 8700020016, 8700020017]
  levelseq_e0m0_tombstonecollapse2ndPart             [script 8700020017]

q#9   (enter e0m1_005)
  levelseq_e0m0_009                                  [script 8700020018]
  dlg_e0m0_0d5                                       [script 8700020018]
  dlg_e0m0_0d7                                       [script 8700020018]
  dlg_e0m0_0d8                                       [script 8700020018]
  dlg_e0m0_0d9                                       [script 8700020018]

q#10  (enter e0m1_006)
  levelseq_e0m0_010                                  [scripts 8700020018, 8700020019]
  levelseq_e0m0_011                                  [script 8700020019]
  radio_e0m0_11                                      [script 8700020019]
  cutscene_e0m0_3 (replay/use-site)                  [scripts 8700020022, 8700020028,
                                                       8700050001; late LevelScript replays]
  radio_e0m0_12                                      [script 8700020022]

q#11  (enter e0m1_007)
  levelseq_e0m0_012                                  [script 8700020019]
  (boss fight begins — script 8700050001)
  levelseq_e0m0_bossfightrockfall                    [script 8700050001]
  levelseq_e0m0_bossfightrockfall_left               [script 8700050001]
  cutscene_e0m0_4                                    [script 8700050001]
  levelseq_e0m0_countdown                            [script 8700050001, ×8 instances]
  cutscene_e0m0_5                                    [script 8700050001]
  radio_e0m0_13                                      [script 8700050001]
  radio_e0m0_14                                      [script 8700050001]
  radio_e0m0_15                                      [script 8700050001]
  radio_e0m0_16 (also 16_1, 16_2, 16_3 variants)     [script 8700050001]
  radio_e0m0_17                                      [script 8700050001]
  radio_e0m0_20                                      [script 8700050001]
  radio_e0m0_22                                      [script 8700050001]
  radio_e0m0_23                                      [script 8700050001]

q#12, q#13   (mission completion placeholders, server-driven)
```

## §E — What is direct vs inferred

| Order claim                              | Evidence type        |
|------------------------------------------|----------------------|
| q#N → q#N+1                              | direct `prevQuestIdList` |
| `levelseq_e0m0_001 < 002 < … < 012`      | direct (monotonic suffix in original strings) |
| dlg_0d5 / 0d7 / 0d8 / 0d9 within 8700020018 | direct (binary offsets 0x2f5/0x35e/0x3c7/0x430, uniform 105-byte stride) |
| cs_e0m0_1 sub-clips 001..022             | direct (AnimeStudio asset map enumerates them in numeric order) |
| `q#7` ↔ script `8700040000`              | direct (`CheckLevelScriptPropertyBool._scriptId.constValue.scriptId = 8700040000` in `e0m0.json`) |
| `q#10` ↔ script `8700020028`             | direct (e0m0_q#10 string at offset 0x1991 inside 8700020028.json) |
| Other script ↔ quest bindings (§D rows)   | **inferred** from semantic clustering (e.g. zipline scripts before tower, battle-field scripts at q#7, boss-fight 8700050001 at q#11–13). The scripts themselves do not embed a quest gate that the current decoder can read. |
| radio numeric suffix order = play order  | **inferred** (consistent with how the rest of the file IDs work, but not gated). The d-suffix inserts (`1d5`, `2d8`, `5d6`, `8d4/8d8/8d9`) suggest later authoring inserts between integer points. |

To turn the inferred bindings into direct ones, the next step is to decode
the `kind` / `code` fields of the records that wrap each `levelseq_*` /
`cutscene_*` string and follow their `nextId` link to a quest-property
condition record. The decoder already pulls out the record headers
(`scripts/story_builder/level_bindings.py` lines 194–243); what is missing
is a table from opcode → semantic ("CheckMissionProperty", "PlayDirector",
"SetMissionVariable", etc.). With that table, every row in §D would
upgrade from `inferred` to `direct`.

## 2026-05-18 LevelScript control audit follow-up

The diagnostic tool `scripts/story_recovery/build_levelscript_control_audit.py`
now writes `reports/mission_order/e0m0_levelscript_control_audit.json` and
`.md`. It combines MissionRuntime quest conditions, LevelData script ownership,
decoded LevelScript story/levelseq payloads, cross-script numeric references,
and IL2CPP metadata field names.

For e0m0 the current audit finds:

- 37 relevant LevelScriptData files across `indie_dg002` and `indie_dg004`.
- 106 LevelData script-id references and 46 cross-script numeric references.
- Exactly one direct MissionRuntime LevelScript condition:
  `e0m0_q#7 -> indie_dg002/8700040000.battle_field_clear == true`.
- `radio_e0m0_1d5` is in `8700040001`, with tower/pole/cannon context.
- `radio_e0m0_2` and `radio_e0m0_2d8` are in `8700000004`, with early quest
  and teleport context.
- `radio_e0m0_3d2` is in `8700030000`, with tutorial/teleport/enemy context.
- `cutscene_e0m0_2ndZiplineA/B/CCamOnly/C` are in `8700010008`, with
  `preloaded` / `played` LevelData context.
- `cutscene_e0m0_6/7/8` are in `indie_dg004/23900030000`, with
  `spawn_point`, `spawn_rot`, `Lookat1/2`, `HavePickedUp`,
  `HaveInteracted`, and `teleportcompleted` context.

This improves the evidence surface but does not yet prove a total play order.
The remaining promotion target is to decode `LevelScriptData.startType`,
`endType`, shape lists, and action nodes such as `ManualStartLevelScript` /
`ManualEndLevelScript`, especially the repeated `0x0455/0x0a` records around
script-id references. Until those action opcodes are named, cross-script refs
remain control evidence, not directed order edges.
