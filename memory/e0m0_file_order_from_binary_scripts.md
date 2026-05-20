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

- `cs_video_e0m0_3` is evidence-bound to the cutscene asset, but the evidence
  comes from AnimeStudio's serialized Timeline objects, not from the video
  filename. `BeyondFMVPlayableAsset_p41331C7714F6805F.json` has
  `fmvId=m_cs_video_e0m0_3` and AssetMap container
  `assets/beyond/dynamicassets/gameplay/cutscene/m_cutscene_e0m0_3/playable/m_cutscene_e0m0_3_actor.playable`;
  `BeyondFMVPlayableAsset_p676DAEAABCD83E74.json` does the same for
  `f_cs_video_e0m0_3` in `f_cutscene_e0m0_3_actor.playable`. Both FMV Track
  clips start at `0.0` and last about `59.75s`.
- The USM/VFS side is identity evidence only. The original video block gives
  chunk indices, hashes, and CRI header strings such as
  `c:\Beyond_Video\MultiPlatform\PC\Narrative\Cutscene\v0d8\m_cs_video_e0m0_3.usm`,
  but no mission/order/quest placement. `fluffy-dumper` also demuxes USM to
  MP4 without preserving any extra placement metadata.
- `cutscene_e0m0_3` should not be placed first from text alone. Its
  `TextTable[cutscene_e0m0_3_01]` row contains a `00:00:00` title-card/slate
  string, but that is identification metadata rather than mission-order proof.
  The stronger placement evidence is the original LevelScript/runtime data:
  `cutscene_e0m0_3` appears in late `indie_dg002` scripts near the q#11
  final-area/boss cluster. The FMV Track binding is identity/asset evidence for
  `cs_video_e0m0_3`, not a reason to force the video row beside the earliest
  `cutscene_e0m0_3` placement.
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
- Current builder behavior: the same-script `levelscriptSceneChain` for
  `indie_dg004/23900030000` now promotes that weak suffix-only hub-key island
  into a contiguous sequence:
  `cutscene_e0m0_6 -> cutscene_e0m0_7 -> cutscene_e0m0_8`, with evidence
  `levelscript-scene-chain:c1` and phases `6.00`, `6.01`, `6.02`.
- `cutscene_e0m0_2ndZipline*` has original LevelScript evidence in
  `indie_dg002/8700010008.json` but no numeric `levelseq_e0m0_00N` anchor.
  The current WebUI order keeps it near `cutscene_e0m0_1stZipline` using the
  authored ordinal names `1stZipline` / `2ndZipline`; this is weaker than a
  quest/property or numeric levelseq anchor and is labelled as such.

## 2026-05-19 gameplay-observed calibration

The user supplied a partial e0m0 playthrough order that differs from the
static-data recovery in important places, especially the opening three
cutscenes, the zipline/radio interleave, and `video_cs_video_e0m0_3` after
`radio_e0m0_12`.

`scripts/story_recovery/manual_observed_order_hints.json` now records that
partial order. `build_story_order.py` applies it as a calibration layer for
the listed e0m0 rows, but keeps the previous static-data result in
`recoveredEvidenceBeforeObserved`, `recoveredPhaseBeforeObserved`, and
`recoveredRankBeforeObserved`. This is for the WebUI and for follow-up
investigation; it is not counted as firm original-data proof.

The calibration now also carries per-row evidence alignment:

- `source-backed`: the row already had direct decoded evidence compatible with
  the observed entry, such as LevelTimeline markers, levelseq anchors,
  property gates, or terminal branches.
- `partial`: original data supports identity, location, or source cluster, but
  not the complete observed relative order.
- `gap`: no decoded source support yet.

Current e0m0 rebuild has `45` observed rows: `15` marked `source-backed`,
`27` marked `partial`, and `3` marked `gap`. The new source-backed row is
`text_e0m0_1`: ReadingPopUp/RichContent define the tombstone epitaph text, and
`8700020018` routes custom event `readepitaph` to `0x045b/0x09`
`ShowUIReadingPopPanel` before the `misc_dlg_e0m0_0d5-0d9` sequence. The big
partial alignments are:
`cutscene_e0m0_3` as a title-card plus FMV prologue clue,
`cutscene_e0m0_1` as the black-screen elevator/selection transition, the first
zipline as levelseq plus q#1 spatial clue, `video_cs_video_e0m0_3` as the late
q#11 video/cutscene cluster, the `8700050001` q#11 boss trigger cluster, and
the `indie_dg004/23900030000` hub-key scene chain for
`cutscene_e0m0_6 -> 7 -> 8`.

After rebuilding `webui/data/assets/story_order.json`, the first 45 generated
e0m0 entries match the observed list from `cutscene_e0m0_1` through
`cutscene_e0m0_8`. Unlisted rows still follow the previous recovered order.
This removes the missing reading-popup display gap. The remaining observed raw
gaps are `radio_e0m0_9d5`, `radio_e0m0_10`, and `radio_e0m0_21`; the runtime
activation/start graph still needs to explain those rows, why the prologue
asset path and later `cutscene_e0m0_3`/video cluster split the way the
playthrough shows, and the exact q#11 boss-cluster radio/cutscene interleave.

Post-calibration source checks did not uncover a missing direct source edge:
the source graph finds only WebUI story/line/video membership for
`cutscene_e0m0_1`, only line plus narrative-video asset edges for
`cutscene_e0m0_3`, and no `video_cs_video_e0m0_3` story node. Exact structured
JSON searches find `cutscene_e0m0_1` only in string/text id tables and find
`cs_video_e0m0_3` only in string/text id tables, not in MissionRuntime,
LevelData, or LevelScript trigger records. So the next clue probably is not a
plain text reference; it has to come from decoded activation state, start
shape/trigger flow, or a runtime table that is not currently indexed as a
story source.

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

The focused setter-candidate audit now confirms the q#7 bridge reaches an
exact UID action record: `indie_dg002/8700040000` carries
`battle_field_clear` in `0x0bed/0x00` at offset `0x1339`, actionMap `#61`
root, now decoded as a medium-confidence `property-key-terminal-branch`.
The payload tail resolves to local action refs `169` and `189`. Branch `169`
walks through a split record into play records `177` (`cutscene_e0m0_New14`),
`178` (`radio_e0m0_8d8`), and levelseq actions `179`/`183`; branch `189` is
the other event-args side. This is no longer just a quest-to-script ownership
clue: it is a direct q#7 property terminal -> local scene-action bridge inside
`8700040000`. The exact runtime class family for `0x0bed/0x00` is still
unnamed, so treat the edge as a decoded terminal-branch walk rather than a
generic setter proof.

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

4. **Decoded terminal branch refs** in compact `0x0bed/0x00` records. These
   tail local ids are stronger than raw offset order when they lead through
   split/next chains to concrete play actions, as with q#7
   `battle_field_clear -> 169 -> cutscene_e0m0_New14/radio_e0m0_8d8`.

TextTable and AnimeStudio metadata can identify a cutscene, its subtitles,
flags, and FMV playable, but they are no longer treated as standalone
mission-order evidence. In particular, a `00:00:00` slate in
`cutscene_e0m0_3_01` does not override the LevelScript placement evidence.

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

Combining the four signals:

```
PROLOGUE (before q#1 fires)
  cutscene_e0m0_2                                   [script 8700020000]
  radio_e0m0_1                                       [script 8700020000]
  (diagnostic only) au_special_cs_e0m0_1_mask_amb     [audio mask; not promoted to cutscene_e0m0_1]

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
  cutscene_e0m0_New14                                [script 8700040000; 0x0bed branch 168->169->177]
  levelseq_e0m0_14_light                             [scripts 8700040000, 8700040004; branch 168->169->183]
  radio_e0m0_8d8                                     [script 8700040000; branch 168->169->178]
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

## 2026-05-18 LevelData grouping surfaced in WebUI

After `export_full/` was restored, the e0m0 control audit was regenerated from
the recovered files and now reports 7 decoded LevelData script sequences. The
Story WebUI `story_order.json` builder also attaches the first decoded
LevelData file/offset plus neighboring script ids to each ordered entry where a
source script is known. These fields are diagnostic only and are explicitly not
promoted as playback edges.

Concrete e0m0 checks:

- `radio_e0m0_1d5` is sourced from `8700040001` and carries LevelData grouping
  `indie_dg002_lv_data_sub_02.json @0x1418`, with previous script
  `8700040000` and next scripts `8700040002`, `8700040004`. This supports
  non-story interstitial LevelScripts around the tower/pole/cannon section.
- `radio_e0m0_2` and `radio_e0m0_2d8` are both sourced from `8700000004`,
  grouped in `indie_dg002_lv_data.json @0x89`. Their order is direct within
  the same LevelScript payload offsets, but the bridge from this script to
  `radio_e0m0_3d2` is still not a directed game-data edge.
- `cutscene_e0m0_1stZipline` is still the only user-facing cutscene currently
  shown between `radio_e0m0_2d8` and `radio_e0m0_3d2`; its strongest order
  evidence is `levelseq_e0m0_003`. LevelData places its script near
  `8700020022` and `8700020026`, but that sequence is interleaved and not a
  strict playback chain.
- `radio_e0m0_3d2` is sourced from `8700030000`, grouped in
  `indie_dg002_lv_data_sub_01.json @0x81`, with previous script `8700030001`.
  Its current `story_order.json` phase remains `content-suffix-fallback`, so
  this is still inference rather than direct order proof.

The audit now also records the IL2CPP/GameAssembly body facts that were
verified with the local body-target mapper: `LevelScriptData.actionMapRaw` is
at runtime field offset `0x68`, `startType` at `0x38`, and `endType` at
`0x3c`; `ManualStartLevelScript.Execute` and
`ManualEndLevelScript.Execute` both resolve `levelId`/`scriptId` through
`LevelScriptManager.TryGetLevelScript` before calling
`LevelScriptRuntime.ManualStart` / `ManualEnd`. This proves the higher control
path but still does not identify `0x0455/0x0a` as a directed start/end action.

## 2026-05-18 Binary LevelScriptData tail decode

`scripts/story_builder/levelscript_binary.py` now decodes stable top-level
MemoryPack facts from raw LevelScriptData blobs. The GameAssembly
`Beyond_Gameplay_LevelScriptDataForMemoryPack.Deserialize` body confirms
`memberCount=26` and this field order:

```text
actionMap, activeShapeList, allowStartOnTravelPole, allowTick, endType,
enemies, exitBuffer, exitBufferOverride, interactiveLocks, interactives,
levelScriptType, lstTemplatePath, maxStage, modules, npcs,
parentLevelScriptId, properties, propertyIdToKeyMap, refWorldEntityIdList,
resetModeWhenActive, resetModeWhenEnd, scriptId, startShapeList, startType,
taskMap, triggerVolumes
```

The control audit now verifies all 37 relevant e0m0 LevelScriptData files have
a serialized script id matching their filename, and decodes `startType` for 25
of them where `startShapeList` is null or empty. The WebUI story-order tooltip
shows these binary fields for source-backed rows.

Targeted checks:

- `radio_e0m0_1d5`: source script `8700040001`, binary member count `26/26`,
  top-level scriptId at `0x1f94`, `startType=Manual`, `startShapeList=null`.
  The same script has a `0x0455/0x0a` script-id pointer to `8700000004`, but
  the opcode is still not proven as start/end.
- `radio_e0m0_2` / `radio_e0m0_2d8`: source script `8700000004`, top-level
  scriptId at `0x14d6`, `startType=SameWithActive`.
- `cutscene_e0m0_1stZipline`: source script `8700020023`, top-level scriptId
  at `0x3ee`, `startType=Manual`; its ordering remains strongest through
  `levelseq_e0m0_003`.
- `radio_e0m0_3d2`: source script `8700030000`, top-level scriptId at
  `0x245d`, `startType=Manual`; this verifies the source binary but does not
  upgrade the current `content-suffix-fallback` story-order placement.

## 2026-05-18 Cross-script byte-window audit

`scripts/story_recovery/build_levelscript_control_audit.py` now emits raw
cross-script reference bytes for each numeric script-id hit: record start,
payload start, whether the target sits in the payload or pre-payload header,
the little-endian target id, the record header bytes, decoded script-pointer
payload/flag bytes for `0x0455/0x0a` and `0x045d/0x0a`, and a byte window
around the target. This makes the weak `x -> y` relations auditable without
naming the opcode prematurely.

`webui/data/assets/story_order.json` also carries compact, deduplicated
incoming/outgoing refs for source-backed story rows, including the decoded raw
flag byte when the target sits inside one of those script-pointer payloads.
The WebUI tooltip and conversation metadata display them as control
diagnostics only; sorting still uses the existing quest/property, levelseq,
timeline/spatial, and weak suffix evidence. Title-card/slate text is
identification metadata only, not a mission-order anchor.

Targeted e0m0 observations:

- `8700040001 -> 8700000004` is a real binary reference at `0xf86` inside
  record `0x0455/0x0a`, payload relation `payload`. The target little-endian
  bytes are `04 77 8f 06 02 00 00 00`; the decoded payload flag byte is `1`.
  The row is still classified only as `script-id-pointer-ref`.
- `8700040000 -> 8700040001` appears twice at `0xcfa` and `0xd3d`, also in
  `0x0455/0x0a` records. `8700040004 -> 8700040001` appears at `0x470` in the
  same record class. Some follow-up `0x045d/0x0a` records share the same
  tagged script-pointer shape. These confirm a cluster around the tower/pole
  scripts, not a directed start/end edge yet.
- `8700030000 -> 8700030001` now resolves to record `0x0415/0x08` at
  `0x191d`, with relation `pre-payload`. This is useful evidence that the
  source script contains a pointer to the neighboring tutorial script, but it
  is weaker than the `0x0455/0x0a` payload refs and is not playback proof.
- The focused IL2CPP body probe confirms `ManualStartLevelScriptForMemoryPack`
  and `ManualEndLevelScriptForMemoryPack` deserialize setters in
  `levelId -> scriptId` order, write the runtime instance fields at `0xd0` and
  `0xd8`, and that `LevelScriptPtrForMemoryPack` serializes one member,
  `scriptId`, stored at offset `0x10`. This explains why script-id pointer
  records matter, but still does not identify any observed opcode as
  ManualStart or ManualEnd.

## 2026-05-18 map-position proximity diagnostics

`mission_recovery.py` already decodes LevelScript vector literals and compares
them with quest/map pins. `story_order.json` now exposes those
candidate matches per story row as diagnostic fields, and
`build_levelscript_control_audit.py` writes a `Map Position Candidates` section.
The data includes the source script id, LevelScript vector position, quest pin
position, XZ/3D distance, and pin label/source. This evidence supports
spatial/quest vicinity only by itself; it is not a standalone playback edge.
The builder has one narrow promotion path: if direct same-script spatial
candidates agree on one quest cluster and content suffixes would place a
raw-ordered source-script cluster several phases too early, the builder ignores
the suffixes and keeps that script's raw payload order at the shared spatial
cluster. A second narrow path handles numeric levelseq over-anchoring: if a
scene has an incoming cross-file LevelScript edge and the predecessor script's
spatial candidate agrees on an earlier quest cluster, that can override the
later numeric levelseq phase for the target row. The same payload also exposes compact mission timeline scene edges, including same-script
`levelscriptFileOrder` edges, so the Story tooltip can show local source-order
evidence without opening the full mission bundle. Direct same-script
`levelscriptFileOrder` edges are now also applied as stable local ordering
constraints.

Focused e0m0 observations from the rebuilt audit:

- `radio_e0m0_1d5` on script `8700040001` has same-script map-position
  candidates near `e0m0_q#1` and `e0m0_q#3`: q#1 is `1.828m` XZ from mission
  area pin `e0m1_002` (`pos=-233.39,85.806,-71.016`,
  `pin=-231.85,86.76,-72.0`), and q#3 is `4.379m` XZ from a `PosTrackingInfo`
  pin (`pos=-104.9,53.607,-63.3`, `pin=-108.854,56.478,-65.182`). The current
  builder keeps these coordinates visible but no longer lets the q#1 proximity place
  `radio_e0m0_1d5` before direct `levelseq_e0m0_001` evidence.
- `radio_e0m0_2` and `radio_e0m0_2d8` on script `8700000004` have a
  same-script q#3 candidate at `6.681m` XZ from the same `PosTrackingInfo` pin.
- `cutscene_e0m0_1stZipline` still uses `levelseq_e0m0_003` as its selected
  order evidence, but related scripts carry spatial candidates: `8700010007`
  is `1.481m` XZ from `e0m1_002`, while `8700020022` is `15.409m` XZ from
  `e0m1_007`.
- `cutscene_e0m0_2`, `radio_e0m0_1`, and `radio_e0m0_3d2` currently have no
  direct map-position candidate in `story_order.json`. For `cutscene_e0m0_2`
  and `radio_e0m0_1`, the stronger game-data evidence is still the
  same-script `8700020000` byte order, which places `cutscene_e0m0_2` before
  `radio_e0m0_1`. The exported scene-edge diagnostics now show
  `cutscene_e0m0_2 -> radio_e0m0_1` as `levelscriptFileOrder` via
  `8700020000`; the current builder applies that edge after duplicate
  occurrence selection so the displayed order no longer places
  `radio_e0m0_1` before `cutscene_e0m0_2`.
- `radio_e0m0_11` on script `8700020019` is no longer anchored to the late
  `levelseq_e0m0_012` phase. The source-backed scene diagnostics contain
  `misc_dlg_e0m0_0d9 -> radio_e0m0_11` as a `levelscriptCrossFileOrder` edge
  across `8700020018` and `8700020019`, and the predecessor script
  `8700020018` has a q#10 spatial candidate `0.315m` XZ from mission area
  `e0m1_006`. `story_order.json` therefore places `radio_e0m0_11` after
  `misc_dlg_e0m0_0d9` with evidence
  `crossfile-spatial-order:e0m0_q#10`.
- `video_cs_video_e0m0_3` is a separate WebUI video row, but its original-data
  evidence is only an AnimeStudio binding to `cutscene_e0m0_3`. The improved
  `video_bindings.json` scan finds the full `BeyondFMVPlayableAsset` records
  in `json_by_type/MonoBehaviour` and binds `f/m_cs_video_e0m0_3` to the
  `f/m_cutscene_e0m0_3_actor.playable` FMV Track at start `0.0`. The
  standalone USM files, subtitle timeline assets,
  `fmv_id.dic[cs_video_e0m0_3] = 17`, and empty `TextTable` rows identify the
  asset, not its mission-order
  placement. Before gameplay-observed calibration, the source order rejected
  the old time-zero title-card promotion and kept `cutscene_e0m0_3` in the
  late LevelScript cluster: one occurrence sits with
  `levelseq_e0m0_tombstonecollapse` in `8700020028`, and related/replay
  occurrences sit near the q#11 spatial cluster in `8700020022` and
  `8700050001`. The observed calibration now moves the standalone video row
  after `radio_e0m0_12`, preserving
  `timeline-video-binding:cutscene_e0m0_3` as the previous evidence.
- `cutscene_e0m0_4`, `cutscene_e0m0_5`, `radio_e0m0_13`,
  `radio_e0m0_14`, `radio_e0m0_15`, `radio_e0m0_16`,
  `radio_e0m0_16_1`, `radio_e0m0_16_2`, `radio_e0m0_16_3`,
  `radio_e0m0_17`, `radio_e0m0_20`, `radio_e0m0_22`, and
  `radio_e0m0_23` now share `script-spatial-raw-order:e0m0_q#11` evidence.
  They all come from `indie_dg002/8700050001`, whose direct same-script
  spatial candidates agree on the q#11 boss/final-area cluster. Their content
  suffixes are now ignored for placement, and the displayed order follows the
  raw LevelScript payload offsets from that source script.

## 2026-05-19 actionMap and play-trigger audit

`scripts/story_recovery/build_levelscript_play_trigger_audit.py` now writes
per-entry trigger evidence to
`reports/mission_order/e0m0_play_trigger_audit.md` and `.json`. The audit
separates two layers:

- script-start trigger: how the whole LevelScript becomes active
  (`ByEnterStartShape`, manual/incoming ref, SameWithActive, or still unknown);
- play-chain trigger: the local action-chain head that leads to the cutscene,
  radio, dialog, or levelseq play record.

The new `actionMap` header decode is useful but deliberately narrow. For the
current exported LevelScriptData blobs, the first serialized member starts as
`02 03 <u32 count>`, followed by that many top-level action records. Marking
records as `actionMap #N root/linked` proves whether a play chain is a root
inside that script; it does not by itself prove the external script-start
trigger.

Current e0m0 counts before the gameplay-observed calibration layer:

- 51 displayed entries.
- 43 source-backed entries with recovered UID chains.
- 40 entries with named play records.
- 3 source-backed UID chains without a named play opcode:
  `radio_e0m0_16_1`, `radio_e0m0_16_2`, and `radio_e0m0_16_3`. These resolve
  to `0x104a/0x00` float-property signal records carrying the matching key and
  `$<localId>@_floatValue`, not to `play_radio`.
- 8 non-popup entries still have no decoded LevelScript source:
  `cutscene_e0m0_1`, `cutscene_e0m0_10`, `cutscene_e0m0_11`,
  `cutscene_e0m0_11111`, `cutscene_e0m0_12`, `radio_e0m0_10`,
  `radio_e0m0_21`, and `radio_e0m0_9d5`. `text_e0m0_1` has now moved out of
  this class: it is a `ShowUIReadingPopPanel` action in `8700020018`.
  Exact source-graph checks for these keys only find generated WebUI/story
  nodes (and line/audio children for the radio rows), not MissionRuntime or
  LevelScript source edges.

After the observed calibration rebuild, `story_order.json` has 53 e0m0 rows:
45 in the observed prefix and 8 still using the recovered static evidence
directly. Among the observed rows, the builder reports 15 `source-backed`
alignments, 27 `partial` alignments, and 3 raw evidence gaps
(`radio_e0m0_9d5`, `radio_e0m0_10`, `radio_e0m0_21`).

The best next recovery path is a per-script action/control-flow walk for
`indie_dg002/8700050001`. Simple byte order gives
`cutscene_4 -> cutscene_5 -> radio_13 -> radio_14 -> radio_15 -> radio_16 ->
radio_17 -> radio_20 -> ... -> radio_22 -> radio_23`, while the observed tail
is `radio_13 -> radio_14 -> radio_16 -> radio_22 -> radio_23 -> radio_17 ->
radio_15 -> cutscene_4 -> radio_20 -> cutscene_5`. Since all of those rows are
real actionList roots in the same manual trigger-volume script, the missing
ordering signal is probably branch predicates, local event headers, or
state/property gates inside `8700050001`, not another plain story-string
reference.

Important action-record conclusions:

- `0x04bd/0x09` is a candidate wait/delay record; its payload decodes as a
  single float-shaped seconds value, e.g. `radio_e0m0_1` waits `2.5` seconds
  and `radio_e0m0_1d5` waits `1.5` seconds before the play record.
- `0x0455/0x0a` and some `0x045d/0x0a` records carry a compact
  `LevelScriptPtr` plus a small scalar/flag. The IL2CPP MemoryPack evidence
  says `ManualStartLevelScript` and `ManualEndLevelScript` serialize
  `levelId -> scriptId`, so these compact records should not be promoted to
  ManualStart/ManualEnd.
- `0x045d/0x0a` is not uniformly a script-pointer record. Some cutscene chains
  have the same opcode with no plausible LevelScript id, so the report labels
  those as scalar-control instead.
- Manual scripts with triggerVolumes remain candidate start triggers only.
  The actionMap often shows the clip play record as a top-level root, which
  means the clip fires when the script is activated; the data still does not
  name the external starter for those manual scripts.

## 2026-05-19 cs_video_e0m0_3 standalone video bundle

Re-audited the `cs_video_e0m0_3` → `cutscene_e0m0_3` combination because the
WebUI cutscene bundle was missing the FMV's dialogue. Findings:

- Typed binding evidence: `BeyondFMVPlayableAsset` records
  `p41331C7714F6805F` (fmvId `m_cs_video_e0m0_3`) and `p676DAEAABCD83E74`
  (fmvId `f_cs_video_e0m0_3`) live inside
  `assets/beyond/dynamicassets/gameplay/cutscene/{m,f}_cutscene_e0m0_3/playable/{m,f}_cutscene_e0m0_3_actor.playable`,
  each with a `Beyond FMV Track` clip at `m_Start=0.0`,
  `m_Duration≈59.75s`. The cutscene's TextAsset manifest
  (`m_cutscene_e0m0_3.json`) ships only the `sc029_star/loop` clips in its
  own `animClipData`; the pre-rendered FMV plays in-line for the sc023-sc028
  range, then the engine takes over with sc029. Cutscene `audioEvents` are
  `au_music_cs_tundra_000_boss_intro`, `au_sfx_cs_e0m0_3`,
  `au_vo_cs_e0m0_3_m` (boss intro music + cs sfx + voiceover).
- Corroborating evidence: `I18N_FMVSubtitleConfig.fmvId2Config` lists both
  `f_cs_video_e0m0_3` (rid `1540790041066340414`) and `m_cs_video_e0m0_3`
  (rid `1540790087718011755`) as `I18NSubtitleAudioBean` references, so the
  game's own FMV subsystem treats `cs_video_e0m0_3` as a subtitled FMV.
- No LevelScript binary blob contains the string `cs_video_e0m0_3`, and no
  MissionRuntime `CheckFMVFinish` references it. The only runtime trigger is
  the Beyond FMV Track inside the cutscene timeline.
- Per-user rule [[feedback-video-attachment-rules]]: the WebUI does NOT inline
  the FMV into the cutscene bundle. Instead, every FMV gets a standalone
  `video_cs_video_*` conv bundle. Dialog/remotecomm bindings keep inline AND
  emit standalone; cutscene bindings are standalone-only.
- After applying that rule the four UI-overlay rows
  (`cutscene_e0m0_3_01..04`: date slate, depth readout, hash placeholder,
  "北极点 远征尽头") stay in `cutscene_e0m0_3.json`, while
  `webui/data/lang/CN/conv/video_cs_video_e0m0_3.json` carries the 4 mp4
  refs and explicitly lists `cs_video_e0m0_3_01/02` as name-matched
  `videoTextCandidates`. The standalone summary reads "timeline-bound to
  cutscene `cutscene_e0m0_3`; kept standalone in WebUI" and warns that the
  candidate rows are not tied by a decoded subtitle track.
- The two `cs_video_e0m0_3_01/02` TextTable rows are still NOT promoted to
  playable video lines. They are name-only matches; the FMV's actual
  subtitles — if any — would have to come from an `I18NSubtitleAudioBean`
  payload (data fields are empty in the export) or a SubtitleTrack inside the
  FMV playable (none found in the relevant containers). See
  [[feedback-video-attachment-rules]] for the rule.
- Code touchpoints (`scripts/story_builder/language_bundle.py`):
  `entry_kind_by_key` precomputed inside `attach_narrative_videos_to_outputs`
  classifies the resolved key; cutscene-bound refs skip `resolved_videos`;
  `emit_standalone_video_outputs` writes `lines: []` and surfaces matching
  `cs_video_*` TextTable rows only under `videoTextCandidates`.
- Source-data placement of `cutscene_e0m0_3` before observed calibration is
  unchanged: boss intro transition (`phase=8.0`, evidence `levelseq-alias`,
  source `indie_dg002/8700020028.json @0x33`) with q#11 spatial candidates
  9.8 m and 15.4 m from `e0m1_007`. The standalone
  `video_cs_video_e0m0_3` row is kind `video`, mission `e0m0`; its current
  WebUI position after `radio_e0m0_12` comes from the explicit gameplay
  observation hint, not from a decoded video trigger.

## 2026-05-19 ordering-evidence inventory and next-step plan

Stocktaking of every ordering signal in the e0m0 data, sorted by what the
current builders actually consume vs. what is already in the export but
unused vs. what still needs decoding.

### A. Signals already consumed (with strength label)

| Evidence | Source | Strength | Coverage |
| --- | --- | --- | --- |
| Quest DAG `prevQuestIdList` | `MissionRuntimeAsset/e0m0.json questDic` | direct | 13/13 quests, linear |
| Quest area / pos tracking | `objectiveList.trackingInfoList` (Area/Pos/Entity) | direct | 11/13 quests |
| Quest property gate | `CheckLevelScriptPropertyBool/Int/String` in MRA | direct, rare | 1 row: q#7 `8700040000.battle_field_clear==true` |
| Numbered `levelseq_e0m0_001..012` | binary string table in LevelScriptData | direct (monotonic) | 12 anchors |
| Per-script byte offset of `0x04`-tagged strings | LevelScriptData record decoder | direct intra-script | 37/46 scripts in audit |
| LevelData parent grouping (`indie_dg002_lv_data_sub_*`) | LevelData binary strings | diagnostic | 7 sub-files |
| Cross-script `uint64` refs (`0x0455/0x0a`, `0x045d/0x0a`) | LevelScriptData record decoder | inferred (opcode unproven) | 46 edges |
| Map-position proximity (LevelScript Vec3 vs quest pin) | spatial nearest-neighbour | weak (correlative) | 51 entries |
| Content-suffix fallback (`radio_e0m0_1d5` → q#1.5) | naming heuristic | weak | 3 entries |
| AnimeStudio FMV binding | asset map + `BeyondFMVPlayableAsset` | direct for video↔scene container | 1 e0m0 binding |
| IL2CPP MemoryPack offsets | GameAssembly body probe | direct for field layout | confirms scriptId/startType/etc. |

### B. Fields already in the export the builder ignores

1. `objectiveList[].trackingInfoList[].filterCondition`
   (`SimpleConditionCheckMissionVariableInt missionVarName=haveCrossedDebris`).
   q#1 splits into two sub-areas by that variable — direct ordering inside
   one quest.
2. `multipleDescription` keys (`objective_e0m0_1_001`, `_3_001`, `_4_001` etc.)
   — authored objective phases per quest with TextTable bodies.
3. `flowIndex` per quest (currently `0` for all q#1-13, used elsewhere as
   tiebreaker but not here).
4. `onMissionAcceptId` / `onMissionCompletedId` — `-1` for e0m0 but populated
   for other missions and would feed a mission-level event hook.
5. `actionMapRaw.dataMap.{headerList,actionList,getterList}` — empty for e0m0,
   non-empty elsewhere; same shape as LevelScript actionMap.
6. `indie_dg002_lv_data.json` master list explicitly names quests
   `q#1, q#5, q#3, q#6, q#7, q#10` as the master's gated quests. Other quests
   live in sub-LevelData files. Direct ownership evidence we don't use.
7. `indie_dg002_lv_data_sub_03.json` (boss-fight LevelData) carries named
   properties `radio_e0m0_13Played..23Played` in authoring order:
   first pass `13, 14, 15, 16_1, 17, 20, 16_2, 16_3` (then a second pass with
   slightly different order). The current `script-spatial-raw-order:e0m0_q#11`
   placement misses this signal; using LevelData property order would likely
   correct `radio_e0m0_16_1/16_2/16_3` placement.
8. `indie_dg002_lv_data_sub_mission_e0m1.json` has named-property story beats:
   `DoOnce1`, `DoOnce2`, `waveAttack`/`2`/`3`/`4`,
   `LookAtPelica`→`PelicaLookAT`→`PelicaGone`,
   `pelica1gone`/`2gone`/`3gone`, `have_left`, `have_zoomed`, `hascrossedarm`,
   `finish_graveyard_dialog`, `finishi_final_dialog`, `played10`,
   `radioplayed`, `isPlayCS`. The order they appear in the LevelData blob is
   authoring order.
9. Per-script `propertyIdToKeyMap` is decoded already, but
   `collect_property_hits` only retains keys that appear in MRA
   `CheckLevelScript*` conditions
   (`scripts/story_recovery/build_levelscript_control_audit.py` line ~510).
   Properties like `radio_*Played`, `pelica*gone`, `wave*` are dropped.
10. `triggerVolumes` / `startShapeList` presence is decoded, but the
    AABB/sphere coordinates are not. Combined with quest pin coords we
    could compute a player-traversal order through trigger shapes.
11. Cutscene `audioEvents` (decoded into bundle but unused for ordering).
    `au_music_cs_tundra_000_boss_intro` alone places `cutscene_e0m0_3` at
    the boss intro.
12. Cutscene `animClipData[].clipInfo.length` + AnimeStudio AnimationClip
    durations give a wall-clock length per cutscene/sub-cut. We pin no
    minimum elapsed time between adjacent rows today.

### C. New evidence found in this pass

**`lt:p:<hash1>:<hash2>` LevelTimeline markers** in
`indie_dg002_lv_data_sub_mission_e0m1.json`. Each pair maps directly to two
`0x04`-tagged UIDs inside a single LevelScript:

```
lt:p:3bb8122f:b8b3f31a → both in 8700020000.json  (prologue)
lt:p:c5eaf64e:2aacba33 → both in 8700020000.json
lt:p:c5eaf64e:92b927b3 → both in 8700020000.json
lt:p:5f89a8fe:5ae800d5 → both in 8700020001.json  (q#2)
lt:p:cf8a9047:54c7b76a → both in 8700020019.json  (q#11)
lt:p:311a0a75:1919fce5 → both in 8700020020.json  (q#11 follower)
lt:p:311a0a75:5a92827a → both in 8700020020.json
```

Each `lt:p:` has a partner `lt:mp:` ("mapped property"). These ARE the
missing piece between "LevelData says this narrative beat exists" and
"LevelScript record X is that beat":

- Direct edges from the mission's authored narrative outline to specific
  UIDs inside scripts.
- The order they appear in the LevelData blob is the authored beat order
  (independent of LevelScript byte offset).
- A shared first hash inside one script (e.g. `c5eaf64e:*`) reveals start/end
  pairing inside that script.

`8700020020.json` ships story-relevant UIDs but is **not yet in the audit's
37-script set** for e0m0. The other 9 indie_dg002 scripts the audit misses
are `8700000001`, `_010`, `_015`, `_018`, `8700020003`, `_007`, `_008`,
`_012`, `_021`, `8700040013` — worth a one-pass scan to confirm they have no
e0m0 strings before excluding them.

### D. Three extractions, ordered by yield

The current order has 8 entries with no LevelScript source at all
(`cutscene_e0m0_1`, `_10`, `_11`, `_11111`, `_12`, `radio_e0m0_10`, `_21`,
`_9d5`) and ~20 placed by inference (spatial proximity + content suffix).

1. **Decode `lt:p:` / `lt:mp:` markers in every LevelData file for the
   mission.** Build a `marker_id → (scriptFile, recordOffset, sourceUid,
   targetUid)` map and surface it as a directed ordering signal — both
   intra-script (sourceUid → targetUid) and across the markers' appearance
   order in LevelData. Self-contained: string-table scan plus in-script UID
   lookup. Highest yield per line of code.
2. **Generalise `propertyHits` to scan ALL LevelData/LevelScript property
   names, not just MRA-referenced ones.** Then attach property semantics
   (`radio_e0m0_13Played` → fires `radio_e0m0_13`, `pelica1gone` → after
   Pelica leaves stage 1) to story rows. The `_sub_03.json` radio play list
   becomes a direct ordering signal that today's solution misses.
3. **Pair action-record decoding with IL2CPP `Beyond.Gameplay.Actions.*`
   classes.** We already have MemoryPack field offsets for
   `ManualStartLevelScript`/`ManualEndLevelScript`. Enumerate every
   `Beyond.Gameplay.Actions.*` MemoryPack record, derive its (memberCount,
   serialized-field order, primitive sizes), match against our recurring
   opcodes (`0x0455/0x0a`, `0x045d/0x0a`, `0x04bd/0x09`, `0x033e`, `0x034a`,
   `0x035b`, `0x02e6`, `0x1041`, `0x104a`). Each confirmed match converts an
   inferred edge into a directed start/end action edge between scripts. Once
   `0x0455/0x0a` is proven we have the full cross-script playback DAG and
   can stop relying on spatial proximity for q#11.

Current spatial/suffix fallbacks should remain as tie-breakers but their
evidence rank should drop below any of these three. (1) and (2) together
should promote 10–15 e0m0 rows from inferred to direct. (3) closes the
cross-script DAG.

Starting with (1) next.

## 2026-05-19 LevelTimeline marker implementation

Step 1 is now implemented in the maintained WebUI recovery path:

- `scripts/story_builder/level_bindings.py` keeps every marker-bearing
  LevelData named-entry table, resolves raw LevelScript UID occurrences, and
  labels marker pairs as `same-record`, `same-script`, `cross-script`,
  `partial`, or `unresolved`.
- `scripts/story_recovery/build_story_order.py` consumes resolved `lt:p`
  markers as direct LevelData-to-LevelScript UID evidence. Secondary levels
  are restricted to explicit mission LevelData refs, so unrelated markers on
  shared levels do not leak into e0m0 diagnostics.
- `scripts/story_recovery/build_levelscript_control_audit.py` now reports a
  LevelTimeline marker section and summary counts. `lt:mp` rows are retained
  as paired metadata only.

Fresh e0m0 verification after rebuilding `story_order.json`:

- `reports/mission_order/e0m0_levelscript_control_audit.json` finds 14
  LevelTimeline rows in the e0m0 source surface: 7 `lt:p`, 7 `lt:mp`, all
  resolving to `same-record` UID evidence.
- `webui/data/assets/story_order.json` promotes the selected
  `cutscene_e0m0_2` prologue occurrence from `mission-start` to
  `leveltimeline-marker:lt:p:3bb8122f:b8b3f31a`.
- `cutscene_e0m0_6`, `cutscene_e0m0_7`, and `cutscene_e0m0_8` are no longer
  split by unrelated phase-7/phase-8 beats. Their shared
  `indie_dg004/23900030000` `levelscriptSceneChain` promotes only the weak
  suffix fallback group, placing the hub-key cluster immediately after the
  q#7 battlefield branch and before the q#8 Patriot reveal.
- `video_cs_video_e0m0_3` stays a standalone WebUI video row, but its explicit
  AnimeStudio `timelinePlayable` binding now orders it directly after
  `cutscene_e0m0_3` with evidence
  `timeline-video-binding:cutscene_e0m0_3` instead of leaving it as a late
  `webui-conv-fallback`.
- The other resolved e0m0 markers currently attach to property/control records
  (`teamSet`, `radioplayed`, or plain UID partner fields) rather than directly
  to displayed story rows. They are visible in the audit and should feed the
  next property-semantics extraction instead of being silently promoted.

## 2026-05-19 `cs_video_e0m0_3` FMV subtitle raw-audit

Re-exported the relevant `76ED1BDFAEF49881D09BFFEF1D829D7A.chk` MonoBehaviour
records into `tmp/e0m0_fmv_subtitle_raw/` with
`ANIMESTUDIO_EXPORT_JSON_RAW=1` to test whether AnimeStudio's JSON export was
dropping FMV subtitle payload data.

Findings:

- `I18N_FMVSubtitleConfig_pAD5AD045DD96065E.raw.bin` matches the existing
  JSON metadata hash (`a6752e0953fe2219f067c8c44415aaf9837139ef82042a8b7937d0ebbff43b94`)
  and does contain non-empty managed-reference payloads for
  `f_cs_video_e0m0_3` and `m_cs_video_e0m0_3`. The JSON `data: {}` is
  therefore lossy.
- The recovered payloads are not subtitle row payloads. They decode as AU
  timeline mappings:
  - `f_cs_video_e0m0_3`: primary `f_cs_video_e0m0_3_Others_AU_CN`, plus CN,
    EN, JP, KR entries.
  - `m_cs_video_e0m0_3`: primary `m_cs_video_e0m0_3_Others_AU_CN`, plus CN,
    EN, JP, KR entries.
- The raw FMV config contains the strings `f_cs_video_e0m0_3` and
  `m_cs_video_e0m0_3`, but it contains no `cs_video_e0m0_3_01/02`,
  no `cutscene_e0m0_3_01..04`, and none of the corresponding TextTable row
  ids as little-endian int64 values.
- The raw cutscene subtitle config likewise contains no
  `cutscene_e0m0_3`/`cs_video_e0m0_3` row keys or row ids.
- The eight resolved `*_cs_video_e0m0_3_Others_AU_*` timelines have only
  `sfx`, `bgm`, and `vo` tracks; no subtitle/text tracks or row-key strings
  were found.

Conclusion: the exporter is losing managed-reference detail for
`I18NSubtitleAudioBean`, but the missing detail here points to localized audio
timeline refs, not subtitle text refs. Keep `cs_video_e0m0_3_01/02` unbound as
subtitle evidence unless a different runtime source proves they are used; the
WebUI may still surface them as explicit name-matched video-text candidates.

## 2026-05-19 cutscene text/video alignment review

Latest review outcome:

- `cutscene_e0m0_3`: the cutscene bundle is timeline-bound to the FMV/audio
  cluster, but its own `cutscene_e0m0_3_01..04` TextTable rows are title-card
  or slate text. They remain in the cutscene bundle with an explicit warning:
  no decoded subtitle track ties those rows to the FMV timeline.
- `video_cs_video_e0m0_3`: `cs_video_e0m0_3_01/02` now appear as
  `videoTextCandidates` with the text "不要忘记我们的约定....." and
  "我在北方等你". They are not promoted to `lines` because the raw FMV audit
  still found no subtitle-track/text-id binding.
- `cutscene_e0m0_2`: CN playback aligns better to the untagged
  `f/m_cutscene_e0m0_2_Others` subtitle tracks than to the
  `*_AU_CHI_ENV_CHI` tracks. The WebUI CN scene now uses that observed track
  family, including the leading-zero `cutscene_e0m0_02_03..07` and
  `cutscene_e0m0_02_10` rows. The summary exposes both text groups so the
  mixed family is visible instead of silently flattened.

## 2026-05-20 e0m0 video/cutscene timeline alignment

`cutscene_e0m0_3` now carries the bound `cs_video_e0m0_3` FMV refs directly in
its generated WebUI payload (`narrativeVideos` and `cutscene.videoRefs`) while
`video_cs_video_e0m0_3` remains as a standalone media/search row. This is a
targeted exception for the confirmed e0m0_3 timelinePlayable binding, not a
general rule that filename-matched videos should merge into cutscenes.

Recovered timing is:

- `f_cs_video_e0m0_3`: bound to `cutscene_e0m0_3`, start `0.0`, duration
  `59.75`.
- `m_cs_video_e0m0_3`: bound to `cutscene_e0m0_3`, start `0.0`, duration
  about `59.75`.

Story order now records `video_cs_video_e0m0_3` as `timelineAlignedWith:
cutscene_e0m0_3`, with `videoBindingClips`, `timelineStart`, and
`timelineDuration`. The video row's adjacency to `cutscene_e0m0_3` is therefore
source-backed by AnimeStudio timelinePlayable data. The broader late placement
of the `cutscene_e0m0_3` cluster in e0m0 is still only partial/static evidence,
because no decoded edge yet proves the exact post-`radio_e0m0_12` trigger.

## 2026-05-19 LevelScript trigger/property opcode refinement

The focused trigger/property pass narrowed three recurring action-record
families without over-promoting them into mission-order edges:

- `0x12a1/0x00` matches the `ScriptEvent.OnLeaderEnterTriggerVolume` field
  shape: trigger slot filter plus trigger slot output. In e0m0 it explains the
  repeated slot records beside Manual scripts with `triggerVolumes`.
- `0x12a3/0x00` matches the paired
  `ScriptEvent.OnLeaderLeaveTriggerVolume` field shape.
- `0x13a5/0x00` matches `ScriptEvent.OnPropertyChanged`: property key plus
  `$local@_oldValue` and `$local@_value` outputs. This is a property-change
  event/listener candidate, not proof of the action that sets the property.

Regenerated reports:

- `reports/mission_order/e0m0_play_trigger_audit.md`
- `reports/mission_order/levelscript_property_flow_CN.md`

Current implication: the original game data can recover a partial
mission-play graph with firm start-shape scripts, trigger-volume event
records, cross-script pointer refs, UID play chains, and MissionRuntime
property gates. A complete quest-to-scene timeline still needs the setter
opcode for LevelScript properties and the typed manual start/end action node.

Follow-up global check: among action-map records whose decoded text contains
an exact known LevelScript level id, no payload also carried a target script id
from that level as text, `u32`, or `u64`. That keeps
`ManualStartLevelScript` / `ManualEndLevelScript` unassigned in the binary
record table. The compact cross-script records remain best described as
`LevelScriptPtr` references plus scalar flags until a real `levelId+scriptId`
payload is found.

`scripts/story_recovery/build_levelscript_opcode_shape_audit.py` now preserves
this check as a reusable report. The current global run scanned `59,763`
records across `2,853` LevelScriptData files and found `0` actionMap
ManualStart-like rows. It also confirmed the already-named event clusters:
`0x12a1/0x00` enter trigger volume (`3,350` records),
`0x12a3/0x00` leave trigger volume (`335` records), and `0x13a5/0x00`
property changed (`90` records). The next setter hunt should start with the
property-key non-event opcode clusters surfaced in
`reports/mission_order/levelscript_opcode_shape_audit.md`.

## 2026-05-19 focused property setter candidate audit

`scripts/story_recovery/build_levelscript_property_setter_candidate_audit.py`
now starts from the confirmed MissionRuntime property bridges and walks the
target LevelScript UID records. It keeps exact key-bearing UID action records
separate from offset-only/top-level property data so property models do not
pollute the opcode ranking.

Current CN result:

- `60` confirmed property bridges from the property-flow report.
- `41` rows have exact key-bearing UID records.
- `19` rows are only offset-containing/top-level data.
- `59` candidate observations across `14` opcode/kind clusters.
- Only `5` observations are story-adjacent.

For e0m0 specifically, q#7's `battle_field_clear` condition resolves to
`indie_dg002/8700040000`, record `0x0bed/0x00` at offset `0x1339`,
actionMap `#61 root`, local id `168`, no `nextId`, with decoded role
`property-key-terminal`. This is a strong quest-to-script/property bridge and
a plausible completion/gate action shape, but it has no story ref in the same
UID chain. Do not promote it into a scene-to-scene edge until `0x0bed/0x00`
or a neighboring action class is identified from IL2CPP/runtime evidence. The
ActionBase formatter tag audit below later proves `0x0bed/0x00` is outside the
normal ActionBase union table, so this is specifically a high
event/gate/terminal-family problem now.

## 2026-05-19 focused LevelScript action metadata audit

`scripts/story_recovery/build_levelscript_action_metadata_audit.py` now keeps a
small IL2CPP metadata report beside the opcode/property audits. The current
report confirms that `ManualStartLevelScript` and `ManualEndLevelScript`
serialize `levelId + scriptId`, while `GetLevelScriptProperty*` actions
serialize `_target + _path` and `ScriptEvent.OnPropertyChanged` is a listener
shape. The expanded pass now also captures the actual generic setter family:
`Beyond.Gameplay.Actions.Set<T>` and `SetList<T>` have `_key + _value` fields,
while the concrete `SetBool`/`SetInt`/`SetPropertyPath`/`SetLevelScriptPtr`
runtime shells have no useful fields of their own. It still finds no metadata
type names for `UpdateLevelScriptProperty`, `OperateLevelScriptNumber`, or
`SetLevelScriptDone`.

Current implication: metadata alone still does not name raw opcodes, but it
sets the test for the next pass. Property-key records such as `0x0a03/0x00`
and `0x0bed/0x00` should stay as gate/completion candidates until they are
tied to a runtime class. For e0m0, `battle_field_clear` remains a strong
quest-to-script/property bridge, but the missing piece is still the runtime
action family that makes that property true.

## 2026-05-19 focused LevelScript GameAssembly body audit

`scripts/story_recovery/build_levelscript_action_body_audit.py` now maps the
focused LevelScript metadata targets to `GameAssembly.dll` and writes
`reports/mission_order/levelscript_action_body_targets_gameassembly.md`.

Current body result:

- `675` focused body targets, `649` mapped; `185` direct calls to focused
  targets were resolved.
- Manual start/end is confirmed as
  `ManualStartLevelScript.Execute` / `ManualEndLevelScript.Execute` ->
  `LevelScriptManager.TryGetLevelScript` ->
  `LevelScriptRuntime.ManualStart` / `ManualEnd`.
- `GetLevelScriptPropertyBool/Int.GetResult` calls
  `LevelScriptManager.TryGetLevelScript` and then
  `LevelScriptRuntime.get_properties`, so these shapes are reads/gates.
- `ScriptEvent.OnPropertyChanged` registers through
  `LevelScriptModule`/`LevelEventManager` and reads `ParamBlackboard`
  variables during `Process`, so it remains listener evidence.
- `LevelScriptRuntime.UpdateRuntimeState` calls
  `ModuleResetUpdateProperty`, which calls
  `LevelScriptModule.ResetUpdateProperty`; that module body only toggles small
  reset/update flags in the recovered body.
- Generic `Set<T>` / `SetList<T>` carry `_key + _value` fields, but their
  generic `CollectParams` / `Execute` body pointers are null in this IL2CPP
  body table.
- Concrete MemoryPack wrappers do prove the setter serialization/storage
  shape: `SetBoolForMemoryPack.Deserialize` calls
  `Set_bool_ForMemoryPack.set____key__` before `set____value__`, and the
  generic wrapper setters store key/value at the real instance offsets
  `+0xd0` / `+0xd8`. The same pattern appears for `Set<int>`,
  `Set<PropertyPath>`, and `Set<LevelScriptPtr>`.
- `ParamVariable._RaiseOnPropertyChangedEvent` can call
  `ParamBlackboard.SetVariableValue`, so listener/writeback paths can mutate
  blackboard variables; this still does not identify an authored LevelScript
  setter opcode.

Current implication: the missing e0m0 `battle_field_clear` mutation is not
explained by the named `SetPropertyPath`/`SetLevelScriptPtr` shells or by
`OnPropertyChanged`. The e0m0 `0x0bed/0x00` payload starts with a
bool/scalar-looking prefix and then carries the plain `battle_field_clear` key;
that is still only a completion bridge shape, not enough to promote a
scene-to-scene edge.

## 2026-05-19 ActionBase formatter tag audit

`scripts/story_recovery/build_levelscript_actionbase_tag_audit.py` now extracts
the generated `ActionBaseForMemoryPackFormatter..cctor` union registration
table from `GameAssembly.dll`, checks the tiny `FinalActionBase` formatter,
decodes the runtime-metadata type slots through `global-metadata.dat`, and
cross-references the global opcode-shape audit.

Current tag result:

- `1,245` contiguous ActionBase tags, `0x0000..0x04dc`, no duplicates and no
  missing values inside the range.
- `326` observed opcode/kind rows in the global `LevelScriptData` audit match
  an ActionBase tag, covering `33,250` records.
- Playback classes are now directly named: `0x034a/0x0d` is `PlayRadio`,
  `0x034b/0x0d` is `PlayRadioAndWait`, `0x0347/0x0d` is
  `PlayLevelSequenceAction`, `0x046c/0x0e` is `StartDialogAction`, and
  `0x046d/0x10` is `StartDialogAndTeleportAction`.
- Real setter action records are also named: `0x03b8/0x0a` is `SetBool`
  (`925` records), `0x03e7/0x0a` is `SetInt` (`340` records), and
  `0x03ea/0x0a` is `SetIntIncrease` (`71` records).
- `0x0176/0x08` is `ListClear<float>`, so its property-key payload is a list
  target, not setter proof.
- `0x0a03/0x00`, `0x0bed/0x00`, `0x12a1/0x00`, `0x12a3/0x00`, and
  `0x13a5/0x00` are outside the ActionBase tag range. `FinalActionBase` only
  contains two subgame final-action tags, so it does not explain them either.

Current implication: part of the original missing bridge is solved. Low
action-map `code` values can now be mapped to action classes, including
generic property setters. The remaining blocker for e0m0 is narrower:
`battle_field_clear` is carried by the high `0x0bed/0x00` terminal record, not
by one of the now-named `SetBool`/`SetInt` ActionBase records. That keeps q#7
as a quest-to-script/property attachment rather than a scene-to-scene timeline
edge until the compact terminal family is decoded.

## 2026-05-19 MemoryPack union and ScriptEventHeader scan

`scripts/story_recovery/build_memorypack_union_tag_audit.py` now scans all
generated MemoryPack formatter `.cctor` union registrations, not just
ActionBase. It writes:

- `reports/mission_order/memorypack_union_formatter_tag_audit.{json,md}`
- `reports/mission_order/memorypack_union_formatter_tag_audit_all_images.{json,md}`

Current result:

- `845` formatter cctors scanned; no extracted raw union tag exceeds
  `0x04dc`.
- The selected high records are absent as raw union tags, but seven observed
  high opcode rows derive from `ScriptEventHeader` with fixed bases:
  `0x12a0/0x00` custom event, `0x12a1/0x00` leader-enter trigger,
  `0x12a3/0x00` leader-leave trigger, `0x12ac/0x00` script-stage changed,
  `0x12af/0x00` start script-controlled-char mode, `0x139f/0x00`
  BB-variable changed, and `0x13a5/0x00` property changed.
- These are event/listener registrations. They do not set
  `battle_field_clear` and should not become e0m0 scene-order edges by
  themselves.

Current implication: the high ScriptEvent side is now named, and the e0m0
`0x0bed/0x00` row is structurally decoded as a terminal branch carrier:
`battle_field_clear` -> local refs `169, 189`, with ref `169` reaching
`cutscene_e0m0_New14`, `radio_e0m0_8d8`, and nearby levelseq actions. The
remaining unsolved piece is the exact non-union runtime class family for
`0x0bed/0x00` and the separate compact gate family that includes
`0x0a03/0x00`. ManualStart/ManualEnd is still not observed as a true
`levelId + scriptId` action-map payload.

## 2026-05-19 terminal branch walk

`scripts/story_recovery/build_levelscript_terminal_branch_audit.py` follows
the decoded `0x0bed/0x00` tail refs through `nextId`, split lists
(`0x0463/0x09`), and nested terminal branches. It writes:

- `reports/mission_order/levelscript_terminal_branch_audit_CN.{json,md}`
- focused variants such as
  `reports/mission_order/levelscript_terminal_branch_audit_CN_indie_dg002_8700040000.{json,md}`

Current CN result:

- `1,529` terminal branch rows.
- `6` rows bridge to MissionRuntime property checks.
- `156` rows have story-key targets after the branch walk.
- `154` rows have play-action targets after the branch walk.
- The e0m0 q#7 bridge is now explicit:
  `indie_dg002/8700040000` local `168`
  `battle_field_clear` branches to `169, 189`; local `169` splits to
  `170, 175`, then through local `176` to play records:
  `177` `play_cutscene cutscene_e0m0_New14`,
  `178` `play_radio radio_e0m0_8d8`,
  `179` and `183` `play_levelseq`.

This means timeline recovery from original game data is possible for more
than quest-local refs: compact LevelScript terminal branches can now recover
authored local scene actions when their branch refs lead to play records.

## 2026-05-19 compact gate and setter overlap follow-up

`0x0a03/0x00` is now structurally decoded as a compact condition/gate shape
with a property key, type code, post flag, and optional tail local-action ref.
The global gate audit (`reports/mission_order/levelscript_gate_audit_CN.md`)
finds `219` rows, `171` decoded property-key rows, `41` tail local refs, and
`10` MissionRuntime-bridged rows. It is real gate evidence, but much weaker
for timeline promotion than `0x0bed`: the bridged rows mostly resolve to
trigger/control setup or missing local ids, not immediate scene play records.

The named low ActionBase setters were also checked against MissionRuntime
script-property checks:

- `0x03b8/0x0a` = `SetBool`
- `0x03e7/0x0a` = `SetInt`
- `0x03ea/0x0a` = `SetIntIncrease`

`reports/mission_order/levelscript_setter_overlap_CN.md` finds `1,331`
setter-key rows but `0` exact `(mapId, scriptId, key)` matches against the
`164` distinct MissionRuntime property-check triples. For e0m0 specifically,
that reinforces the current model: q#7's `battle_field_clear` is a
script-property terminal branch (`0x0bed`) rather than a normal ActionBase
`SetBool` write. The direct recoverable timeline edge is therefore the branch
walk from `battle_field_clear` to local `169`, not a setter-to-checker edge.

## 2026-05-19 ManualStart/ManualEnd activation follow-up

ManualStart/ManualEnd is no longer completely missing. The ActionBase union
table names:

- `0x02f1/0x0a` as `ManualStartLevelScript`.
- `0x02ec/0x0a` as `ManualEndLevelScript`.

`scripts/story_recovery/build_levelscript_manual_control_audit.py` now scans
these records globally. It finds `84` manual control rows, including `74`
trigger-adjacent activation pairs and only `4` rows with literal script-id
operands. Those `4` literal operands are self-targets; the current scan finds
`0` literal cross-script targets.

For e0m0 script `indie_dg002/8700040000`, the relevant local-id pattern is:

- `201` `0x12a1/0x00` `ScriptEvent_OnLeaderEnterTriggerVolume`
- `202` `0x02f1/0x0a` `ManualStartLevelScript`
- `203` `0x12a3/0x00` `ScriptEvent_OnLeaderLeaveTriggerVolume`
- `204` `0x02ec/0x0a` `ManualEndLevelScript`

This confirms the script activation/deactivation surface for the e0m0
LevelScript. It still does not produce a direct scene timeline edge because
the manual control payloads do not carry a literal cross-script `levelId` /
`scriptId` target. The promotable e0m0 scene edge remains the original-data
branch from q#7 `battle_field_clear` through `0x0bed` local `168` to local
`169`, which reaches `cutscene_e0m0_New14`, `radio_e0m0_8d8`, and nearby
levelseq actions.
