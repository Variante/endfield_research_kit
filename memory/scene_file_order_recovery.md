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

5. **LevelScript file-offset order**
   - Source:
     `export_full/structured/StreamingAssets/Data/Json/LevelScriptData/<level>/*.json`
   - Ordering signal: tagged story/cutscene/radio strings encountered in byte
     offset order within one LevelScript file.
   - This is useful as a weak hint for files that are not connected by UID
     `nextId` chains, especially boss/script clusters with parallel event
     records. It is not a strong chronology source by itself and should be
     marked separately from quest-DAG, authored scene-link, and UID-chain order.

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

`e0m0` current mission-order status:

```text
strong: radio_e0m0_8d4 -> cutscene_e0m0_New14 -> radio_e0m0_8d8 -> cutscene_e0m0_13
strong: cutscene_e0m0_6 -> cutscene_e0m0_7 -> cutscene_e0m0_8
weak:   misc_dlg_e0m0_0d5 -> misc_dlg_e0m0_0d7 -> misc_dlg_e0m0_0d8 -> misc_dlg_e0m0_0d9
weak:   cutscene_e0m0_2 -> radio_e0m0_1
weak:   cutscene_e0m0_2ndZiplineA -> cutscene_e0m0_2ndZiplineB -> cutscene_e0m0_2ndZiplineCCamOnly
weak:   radio_e0m0_2 -> radio_e0m0_2d8
weak:   cutscene_e0m0_4 -> cutscene_e0m0_5 -> radio_e0m0_13 -> radio_e0m0_14 -> radio_e0m0_15 -> radio_e0m0_16 -> radio_e0m0_17 -> radio_e0m0_20 -> cutscene_e0m0_3 -> radio_e0m0_22 -> radio_e0m0_23
weak:   radio_e0m0_8d9 -> cutscene_e0m0_lookingatpatriot -> radio_e0m0_9
weak:   cutscene_e0m0_3 -> radio_e0m0_12
unknown: cutscene_e0m0_tombstonecollapseCam, cutscene_e0m0_1, cutscene_e0m0_1stZipline, radio_e0m0_1d5, radio_e0m0_3d2, radio_e0m0_5d6, radio_e0m0_9d5, cutscene_e0m0_10, radio_e0m0_10, cutscene_e0m0_11, radio_e0m0_11, cutscene_e0m0_12, radio_e0m0_21, cutscene_e0m0_11111
```

Conclusion: `e0m0` is only partially confirmed. The first four-entry quest
sequence and the `cutscene_e0m0_6/7/8` UID chain are strong. Most of the long
radio/cutscene ordering is still file-offset order only, and several exported
files have no mission-order clue yet.

Generated follow-up audit:

- `reports/mission_order/e0m0_evidence_audit.json`
- `reports/mission_order/e0m0_evidence_audit.md`

Regenerate with:

```bat
python scripts\story_recovery\build_mission_order_evidence_audit.py --language CN --mission e0m0
```

Audit checkpoint, 2026-05-14:

- `e0m0` currently has 48 mission entries in the CN WebUI index: 7 strong, 26
  weak, and 15 unknown.
- LevelScript evidence was found under both `indie_dg002` and `indie_dg004`.
  The direct mission runtime `levelId` is `indie_dg002`, while
  `LevelData/indie_dg004/indie_dg004_lv_data_sub_mission_e0m0.json` also
  points to mission-specific data for this mission.
- The strongest mission-to-LevelScript bridge is quest `e0m0_q#7`: its
  objective waits on map `indie_dg002`, script `8700040000`, key
  `battle_field_clear`. That LevelScript file contains the strong sequence
  `radio_e0m0_8d4 -> cutscene_e0m0_New14 -> radio_e0m0_8d8 ->
  cutscene_e0m0_13`.
- Unknown entries with no MissionRuntime or LevelScript placement hit in the
  audit were: `cutscene_e0m0_1`, `video_cs_video_e0m0_3`,
  `radio_e0m0_9d5`, `cutscene_e0m0_10`, `radio_e0m0_10`,
  `cutscene_e0m0_11`, `cutscene_e0m0_12`, `radio_e0m0_21`, and
  `cutscene_e0m0_11111`.
- LevelData byte-string scanning found trigger/state context in
  `indie_dg002_lv_data_sub_03.json` for the long radio cluster and in
  `indie_dg002_lv_data_sub_mission_e0m1.json` for
  `dlg_e0m0_0d5/0d7/0d8/0d9`. This did not reduce the orphan list above,
  because LevelData string hits are still trigger/spatial context rather than
  chronology until the blobs are decoded into explicit ownership.
- Unknown entries that do have LevelScript hits but still lack decoded order
  semantics were: `cutscene_e0m0_1stZipline`, `radio_e0m0_1d5`,
  `radio_e0m0_3d2`, `radio_e0m0_5d6`, `radio_e0m0_11`, and
  `cutscene_e0m0_tombstonecollapseCam`.
- `RadioTable`, `AudioDialog`, and AssetMap hits validate many file families,
  but they still do not prove inter-file mission chronology without a quest,
  LevelScript control-flow, or trigger ownership bridge.

Promising LevelScript opcode/kind clusters seen in e0m0:

```text
0x033e kind 0x13: cutscene play-like records
0x033f kind 0x13: zipline cutscene variant records
0x034a kind 0x0d: radio records
0x034b kind 0x0d: alternate radio records
0x046c kind 0x0e: dialog records
0x035b/0x035d/0x0347/0x047e/0x047f/0x02e6: levelseq/cutscene-control records
0x104a kind 0x00: radio state or played-style records
```

These opcode labels are working hypotheses until validated against runtime
metadata or repeated cross-mission behavior. They are the next best route for
promoting some weak LevelScript file-offset edges into stronger typed
control-flow evidence.

## Ongoing Recovery Plan

Keep improving mission file-order recovery in small, commit-sized passes:

1. Preserve the current evidence classes in the WebUI: strong, weak, and
   unknown.
2. For each mission under active review, generate or update an evidence audit
   that lists every weak/unknown file and all original-data hits behind it.
3. Promote an order edge to strong only when original data proves a quest DAG,
   authored scene transition, UID/control-flow chain, or typed trigger/action
   relation.
4. Keep filename index order as a display fallback only. Unknown files should
   remain after strong/weak placed files until better evidence is recovered.
5. Update this `memory/` note with durable conclusions after each pass. Put
   generated machine-readable audit output under `reports/` and disposable
   prototypes under `scratch/` or `tmp/`.
6. Make regular scoped commits for completed slices, without sweeping unrelated
   local edits into the recovery commits.

## Candidate Metadata Queue

High-value sources to test next:

- Typed `LevelScriptData` records: identify action/condition opcodes behind
  play-cutscene, play-radio, set property, wait condition, quest advance,
  battle clear, black fade, camera, and related mission triggers.
- `MissionRuntimeAsset` nested action and condition fields: inspect
  `failedCondition`, `finishCondition`, client actions, tracking targets, and
  `CheckFMVFinish`-style dependencies for phase anchors.
- LevelScript property ownership: pair condition checks such as
  `CheckLevelScriptPropertyBool` with the script records that set the same
  key, then use that relation to place nearby story files.
- Timeline/prefab component graphs: recover `PlayableDirector`, audio/control
  tracks, activation tracks, camera bindings, and cutscene prefab references
  for files that currently appear only in asset paths.
- Radio/audio metadata: use `RadioTable` continuation fields, priority, type,
  per-line index, and `AudioDialog.path` as validation and weak tie-break
  evidence unless another source connects the radio to a quest phase.
- Map/route metadata: use mission track points, links, pins, areas,
  interactives, NPCs, and spawners to explain spatial progression, but avoid
  promoting spatial order to strong chronology without an explicit mission
  reference.
- Registry tables: use `StrIdNumTable` / `NumIdStrTable` as key-existence
  validation only until runtime semantics prove those ids imply chronology.

## Expanded Clue Inventory (2026-05-14)

Additional original-data sources worth probing for scene-file ordering. These
are working hypotheses; promote to strong only if a concrete mission/scene
chronology link is recovered.

### Tier A: direct ordering signals not yet exploited

- `AudioRadioContinueTable.json`: name suggests explicit radio-to-radio
  continuation chains. If schema confirms (`prevRadio`/`nextRadio` style
  fields), this is direct strong evidence for radio file order without needing
  LevelScript control flow.
- `AudioSequenceDialog.json`: "sequence dialog" naming implies an ordered
  list/chain. Verify whether entries are per-conversation playlists or just
  per-line voice clips.
- `AudioDialogConfigs.json`: may carry per-conversation chunk ordering and
  audio routing flags beyond what `AudioDialog.json` records.
- `LevelScriptTemplateData/`: templated record skeletons keyed by record type.
  If templates name opcode purpose (e.g. `PlayCutscene`, `WaitProperty`,
  `Branch`), they can validate the working opcode labels in the parent
  memory file (`0x033e`, `0x033f`, `0x034a`, `0x046c`, ...).
- `MissionExtraInfoTable.json` / `MissionTypeInfoTable.json`: per-mission
  metadata that may include phase labels, parent/child mission links, or
  recommended order; not yet inspected.
- `InteractiveMissionDataTable.json`: interactives tied to specific mission
  steps. Where an interactive triggers a dialog/cutscene, its mission-step
  field is a quest-phase anchor.

### Tier B: state-machine and condition graph evidence

- `ConditionTable.json` + `GlobalVarTable.json`: shared global flag and
  condition definitions. Pair `setVar` actions in LevelScript with
  `checkVar` conditions to derive "scene X happens before scene Y because
  scene Y waits on a flag scene X sets". This is the same pattern as the
  LevelScript-property recipe but at the global scope.
- `MissionRuntimeAsset[*].questDic[*]._failedCondition` /
  `_finishCondition` / `_trackingCondition`: already cited, but each nested
  `LevelScript*Condition` carries `mapId`, `scriptId`, `key`, `value`,
  `comparer` triples that, combined with the LevelScript property writers,
  produce a directed phase graph. Build a per-mission property-flow graph.
- `ResponsiveTriggers.json` / `ResponsiveDialog.json`: trigger-driven dialog
  events. The trigger table maps a runtime event id to a dialog/cutscene
  key. Cross-referencing trigger emit sites in LevelScript yields ordering
  for triggered files.

### Tier C: progression-side validation

- `AchievementTable.json` / `AchievementStatisticTable.json`: achievements
  with mission-completion conditions provide a coarse chronology between
  missions (and sometimes between named scene steps within a mission when
  achievements name a step).
- `PrtsRecord.json` / `PrtsInvestigate.json` / `PrtsDocument.json` /
  `PrtsReading.json` / `PrtsMultimedia.json`: the in-game archive system.
  Entries that unlock on completing a specific scene/quest give a chronology
  link from the unlocked entry back to the source scene.
- `MailSenderTable.json` / `MailTemplateTable.json`: in-game mail is often
  triggered post-quest. If a mail template references a quest finish or
  story flag, that yields a "scene → mail" anchor without scanning bytes.
- `WikiEntryTable.json` / `WikiEntryDataTable.json`: codex/wiki entries.
  Similar unlock-condition logic to the Prts archive.
- `AdventureTaskTable.json` / `AdventureLevelTable.json`: side-quest /
  adventure progression. If these reference main-line missions as
  prerequisites, they validate mission ordering between scene files.
- `LoadingTipsTable.json`: loading tip unlock keys can implicitly imply a
  mission has been reached.
- `IntroTable.json`: opening/intro sequence ordering — first-mission anchor.
- `GameMechanicConditionTable.json` / `GameMechanicTable.json`: feature
  unlocks frequently gate on quest finish, giving anchor points.

### Tier D: spatial/contextual evidence

- `MapMarkInsTable.json` / `MapMarkTempTable.json` /
  `TrackMapPointTable.json` / `TrackMapLinkTable.json`: map markers and
  track-point graphs. Use as weak spatial ordering only.
- `SpawnerConfig/`: NPC/encounter spawn entries can tie spawn enable/disable
  to mission steps.
- `NpcInfoTable.json` / `NpcGroupTable.json` /
  `AtmosphereNpcTable.json` / `GameplayAndEnvironmentalNpc.json`: NPC phase
  data — appearance states tied to mission progression.
- `CharInteractPerformCfgs/`: character interaction performance configs
  that may bind cutscenes to characters at specific story stages.
- `LipSync/`: per-line lip sync data; lip-sync clip names usually carry the
  same dialog-line ids and can validate which lines belong to which scene
  when other tables disagree.
- `AnimationConfig/`: animation configuration data; cross-validates
  Timeline clip ordering for cutscenes.

### Tier E: cross-cutting metadata

- `TextVoIdTable.json`: text-id to voice-id mapping. Voice ids that share a
  scene prefix confirm scene membership; can also validate that two
  separately-keyed files belong to the same recording session.
- `VoiceIdConflictTable.json`: voice-id conflicts may flag which lines are
  alternates of the same anchor — useful for option-anchor validation.
- `AudioVoiceExtraData.json`: extra voice metadata — speaker, emotion,
  recording session tags can indicate co-authored line clusters.
- `EmotionVoiceConfig.json`: emotion configs per voice clip; emotion-state
  changes can hint at narrative beats.
- `SettlementLevelPOIMapTable.json` / `SettlementBasicDataTable.json`:
  settlement/POI progression that may unlock with story.
- `CinematicConst.json`: cinematic constants; may include default playable
  director chains for prologue/epilogue clusters.

### Anti-clues (do not use as ordering evidence)

- Filename suffix numeric / `dXX` / `New14` style indices — already an
  established fallback only.
- Asset bundle on-disk byte offsets — packaging order is not authoring or
  narrative order.
- WebUI generated rank/order fields — circular.
- Plain string co-occurrence in `LevelData/*` without a decoded record kind.

### Search workflow per candidate source

For each candidate above:

1. Read a small sample (1–3 entries) to confirm schema before any wide scan.
2. Look for fields that reference `dlg_*`, `sns_*`, `cutscene_*`, `radio_*`,
   `dlgtl_*`, mission ids, quest ids, level/script ids, or property keys.
3. Decide whether the reference is *causal* (X depends on Y, X completes
   after Y) or *correlational* (X mentions Y).
4. Only causal references promote a weak edge to strong. Correlational
   references stay as validation/weak.
5. Land each finding as a small audit script under
   `scripts/story_recovery/` plus a generated report under
   `reports/mission_order/` (or a similarly scoped subdirectory). Add a
   one-line summary under this section pointing at the audit.
6. Commit per-source slices, do not bundle.

### Reminder loop

The recovery work should run as small, commit-sized passes. After each pass:

- Update this section with the source(s) confirmed or rejected.
- Update `Audit checkpoint, YYYY-MM-DD` notes in the parent section.
- Regenerate the relevant evidence audit JSON/MD under `reports/`.
- Avoid promoting filename-suffix order to strong.

### 2026-05-14 Probe Results

First reconnaissance pass over the candidate sources. Each entry records the
shape, the *unique* ordering signal (if any), and whether the field is
*currently exploited* by `scripts/`.

- `AudioRadioContinueTable.json` (map of speaker → `selfContinue[]` /
  `otherContinue[]` arrays of `radio_continue_self_*` and
  `radio_continue_other_*` ids). The arrays are an authored sequence, but
  the referenced ids are **ambient banter pool ids**, not the mission-tied
  `radio_<scene>_*` files in the Story view. Use as banter-pool ordering only.
  Currently not consumed by `scripts/`.
- `AudioSequenceDialog.json` (only two top-level entries, `"1"` and `"2"`,
  for the two protagonist gender variants; nested `sequence` maps hash ids
  to ambient banter triplets with `cdTime`, `involvedSpeakers`, `sequence`).
  Banter pool selector by gender, **not mission ordering**. Reject.
- `AudioDialog.json` / `AudioDialogConfigs.json`: pure audio bank routing
  metadata; no ordering signal. Continue treating as validation only.
- `RadioTable.json`: 2192 entries; 1325 scene-keyed (`radio_<scene>_*`).
  `continueAfterDialog` is `true` on 1051 of them, `continueAfterRadio` on
  292; both true on 188. These are **flags, not pointers** — they assert "this
  radio is a continuation of the immediately preceding dialog/radio in the
  same trigger context" but do not name the predecessor. Combined with
  LevelScript trigger-proximity ordering, they can promote a weak file-offset
  pair to strong when the offset pair already places a `dlg_*` immediately
  before a `radio_<scene>_*` flagged `continueAfterDialog=true`. The current
  audit captures the flags as descriptive fields only
  ([build_mission_order_evidence_audit.py#L347-L349](scripts/story_recovery/build_mission_order_evidence_audit.py#L347-L349));
  the LevelScript-proximity-driven promotion rule is **not yet implemented**.
- `AudioDialogCustomEventTable.json`: 41 entries, each keyed by a `dlg_*`
  id with `preEnterEvents` / `preExitEvents` / `preloadEvents` arrays of
  integer event ids. Not currently consumed by any script. If the event ids
  match Wwise event ids referenced by LevelScript audio records, this
  bridges specific dialog files to the LevelScript record that fired their
  enter event — a strong direct ownership signal. **Next: map event ids
  through `AudioDialog.json`/`AudioCueTable.json` to confirm.**
- `DomainDepotDeliverTargetDialogTable.json`: 15 NPC depot entries with
  `initialDialogId` + `repeatDialogId`. Authored *initial-before-repeat*
  pairs (e.g. `dlg_f1m33_5 → dlg_f1m33_6`). Weak ordering signal scoped to
  the depot interactive; currently not consumed.
- `ConditionTable.json`: 19 entries, top-level condition graph with
  `subConditionIds` chains referencing `questms_*` quest-state-machine ids
  and `kernel_*` system flags. Not scene-keyed; useful for quest-level DAG
  validation, not scene-file ordering.
- `GlobalVarTable.json`: contains mission-scoped state flags like
  `c13m1_delivery_state_01`, `c28m1_door`, `e4m1_all_erosion_unlock`,
  `e5m1_adaxier_zhufa_state`. If paired with the LevelScript records that
  set vs. check these vars, the resulting setter→checker edges become
  strong ordering signals for the scene files those records belong to.
  Already referenced in `scripts/scene_order_gap_shared.py`; verify which
  setter/checker pairs are exploited and which remain idle.
- `MissionExtraInfoTable.json`: 19 entries; only `extraInfoDesc` text and
  `extraInfoType`. **No ordering signal.** Reject.
- `MissionTypeInfoTable.json`: 6 entries; UI display metadata only.
  Reject.
- `InteractiveMissionDataTable.json`: 7 entries; `missionUseType` enum is a
  global tag, no step granularity. Reject for file-order.
- `SNSDialogTable.json`: `linkMissionId` plus `preContentId` /
  `nextContentId` / `isEnd` flow. Already exploited by
  `scripts/story_builder/language_bundle.py` (intra-conversation order plus
  `linkMission` passthrough). No new evidence here.
- `PrtsRecord.json`: 316 entries, mostly keyed by `nar_*` archive ids;
  only 5 follow the `nar_<scene>_n` pattern. Each entry carries
  `firstLvId` ("first-level id") and `contentId` pointing at the in-game
  archive text. Not a chronology source — at best a 5-row anchor set.
- `AchievementTable.json`: 101 entries with nested `levelInfos[*].conditions`
  referencing `conditionId` values whose definitions live in a separate
  condition store, not in scene files. No direct scene anchors.
- `LoadingTipsTable.json`: 142 tips; 98 have an `unlockMissionId`,
  covering 15 unique missions (`e1m1`, `e1m10`, `e1m2`, ..., `f1m3d1`).
  Cross-mission anchor at coarse "mission-completed" granularity only.
- `AdventureWorldLevelTable.json`: 7 entries; `missionId` is non-empty on
  only 4 rows (`m0m2`, `m0m3`, `m0m4`, `m0m5`). Marginal anchor set.
- `LevelScriptTemplateData/*.json`: 28+ template files, but the `.json`
  extension is misleading — payload is Unity serialized binary, not
  human-readable JSON. Templates carry no opcode→typename mapping. The
  existing decoder at
  [level_bindings.py#L194-L243](scripts/story_builder/level_bindings.py#L194-L243)
  extracts `code` / `kind` / `localId` / `nextId` from real records but
  has no semantic dictionary for those values. The opcode hypotheses in
  the parent section remain unvalidated. Reject the template directory as a
  dictionary source; pursue cross-mission opcode-frequency statistics
  instead.

Concrete next slices implied by the probe:

1. Implement the LevelScript-proximity + `continueAfterDialog/Radio` rule
   that promotes a weak `dlg → radio` adjacency to strong when the radio
   flag is set.
2. Build an `AudioDialogCustomEventTable` event-id resolver that walks
   `AudioDialog.json` and `AudioCueTable.json` to identify the LevelScript
   record firing the dialog enter/exit events.
3. Inventory `GlobalVarTable` setters vs. checkers across all LevelScript
   files for every mission-scoped var; emit a per-mission var-flow audit.
4. Stop probing `MissionExtraInfoTable`, `MissionTypeInfoTable`,
   `InteractiveMissionDataTable`, `AudioRadioContinueTable`,
   `AudioSequenceDialog`, `AudioDialog`, `AudioDialogConfigs`. They are
   confirmed dead ends for scene-file ordering.

### 2026-05-14 Opcode Validation (cross-mission sample)

Sampled three LevelScript directories (`indie_dg002`, `indie_dg004`,
`indie_dg005`) using `_load_levelscript_binding_data` from
[level_bindings.py#L194-L243](scripts/story_builder/level_bindings.py#L194-L243).
Each working hypothesis now has supporting payload evidence:

- `0x033e kind 0x13` — cutscene play: payloads include
  `cutscene_e0m0_lookingatpatriot`, `cutscene_e0m0_tombstonecollapseCam`,
  `cutscene_e0m0_6/7/8` (across two levels). **Confirmed.**
- `0x033f kind 0x13` — zipline cutscene variant: payloads include
  `cutscene_e0m0_1stZipline`, `cutscene_e0m0_2ndZipline*`. **Confirmed.**
- `0x034a kind 0x0d` — radio: payloads `radio_e0m0_1/8d4/8d8`,
  `radio_e4m1d5_2`, `radio_e6m1_22/23/24`. **Confirmed.**
- `0x034b kind 0x0d` — alternate radio: payloads `radio_e0m0_5d6/9/20`.
  **Confirmed.**
- `0x046c kind 0x0e` — dialog: payloads `dlg_e0m0_0d5/0d7/0d8/0d9`,
  `dlg_e4m1d5_3/7`, `dlg_e6m1_5/7/9`. **Confirmed.**
- `0x035b kind 0x0c` / `0x035d kind 0x0a` — cutscene control: payloads
  again carry `cutscene_*` ids; consistent with control/seq variant.
  **Confirmed.**
- `0x0347 kind 0x0d` / `0x047e kind 0x0c` / `0x047f kind 0x09` /
  `0x02e6 kind 0x09` — opaque control records; no in-band story payloads,
  so they sit between cutscene plays. Likely audio/camera/trigger control
  rather than story callsites. **Partial — hypothesis stands, but no
  payload anchor.**
- `0x104a kind 0x00` — radio state/played: 28 records in `indie_dg002`
  carry `radio_e0m0_14/16_2/16_3` payloads. **Confirmed radio-adjacent;
  state-vs-played distinction unresolved.**

Implication: the play-* opcodes (`0x033e/033f`, `0x034a/034b`, `0x046c`)
are reliable typed markers. A chain of consecutive *typed* play records
within one LevelScript file is now stronger than raw file-offset order
alone, because the typed sequence excludes opaque control records that
could have hidden ownership boundaries.

### 2026-05-14 Proximity-Rule Prototype

[scratch/probe_radio_continuation_promotions.py](scratch/probe_radio_continuation_promotions.py)
walks each mission audit's `levelScriptFiles[*].matchedSequence` and
emits a promotion candidate whenever a `radio_<scene>_*` flagged
`continueAfterDialog` follows a `dlg_*` (or `misc_dlg_*`) earlier in the
same script file, and similarly for `continueAfterRadio`. Initial output
on `e0m0` / `e1m1` / `c17m3`:

```text
missions audited: 3; promotion candidates: 11
by match kind: {'after-dialog': 10, 'after-radio': 1, 'mismatched': 0}
```

Concrete `c17m3` candidates worth promoting once the rule moves out of
scratch:

- `dlg_c17m3_2  -> radio_c17m3_42` @ map01_lv005/3400320003
- `dlg_c17m3_13 -> radio_c17m3_40` @ dung01_rdg005/24300010006
- `dlg_c17m3_15 -> radio_c17m3_25` @ dung01_rdg005/24300010007
- `dlg_c17m3_10 -> radio_c17m3_8`  @ dung01_rdg005/24300010009
- `dlg_c17m3_12 -> radio_c17m3_22` @ dung01_rdg005/24300010011
- `dlg_c17m3_25 -> radio_c17m3_58` @ dung01_rdg005/24300010024
- `radio_c17m3_51 -> radio_c17m3_41` @ dung01_rdg005/24300010012 (after-radio)

`e0m0` produces zero candidates because all 23 of its scene-keyed radios
have both flags `false`. That confirms `e0m0` is the worst case for this
rule and validates why the long radio cluster there remains weak.

Concrete `e1m1` candidates:

- `dlg_e1m1_1   -> radio_e1m1_1d5` @ map01_lv001/2100050039
- `dlg_e1m1_4d2 -> radio_e1m1_5d3` @ map01_lv001/2100050029
- `dlg_e1m1_6d3 -> radio_e1m1_13`  @ map01_lv001/2100050071

Cross-mission radio coverage of this signal (top missions by flagged
scene-keyed radio count):

```text
e10m4  59/59 cAD, 2 cAR
c17m3  45/45 cAD, 2 cAR
c28m3  38/38 cAD, 7 cAR
e5m1   37/38 cAD, 7 cAR
e9m2   36/36 cAD, 4 cAR     # also an inferredOptionResponse mission
e9m3   31/31 cAD, 0 cAR
e8m3   29/29 cAD, 9 cAR
```

Across the full table 1051/1325 scene-keyed radios have
`continueAfterDialog=true` and 292/1325 have `continueAfterRadio=true`
(some have both). Promotion via this rule should land hundreds of new
strong edges once the prototype is folded into
`scripts/story_recovery/` and the WebUI builder picks up the resulting
strong-edge records.

Next promotions of this slice:

1. Promote the prototype out of `scratch/` into a `scripts/story_recovery/`
   audit named e.g. `build_radio_continuation_audit.py` and write a
   `reports/mission_order/radio_continuation_*.{json,md}` artifact.
2. Decide whether the WebUI builder should consume the new strong edges
   directly (via `scripts/scene_order_gap_shared.py` or a new evidence
   class) or stay diagnostic until validated on more missions.
3. Re-run mission audits and compare strong/weak/unknown counts to
   measure how many entries the rule actually promotes.

### 2026-05-14 Tool-Side Extraction Inventory

What we extract from the original game today via the in-repo tools, and where
the next data classes can come from. The decoder budget is intentionally
small; each new class needs a clear story-recovery payoff.

#### Extracted today

- `tools/AnimeStudio/` (C# Unity asset extractor) — invoked via
  [export_full_from_game.py#L32-L61](scripts/export_full_from_game.py#L32-L61):
  - Convert pass: `GameObject`, `Texture2D`, `AudioClip`, `Shader`,
    `TextAsset`, `Font`, `Mesh`, `VideoClip`, `MovieTexture`, `Sprite`,
    `Animator`, `AnimationClip`, `MiHoYoBinData`.
  - JSON pass: `TextAsset`, `MonoBehaviour`, `Material`, `AssetBundle`,
    `IndexObject`, `AnimatorController`, `AnimatorOverrideController`,
    `MonoScript`, `PlayerSettings`, `PlayableDirector`, `ResourceManager`,
    `SpriteAtlas`, `NapAssetBundleIndexAsset`.
  - Timeline-focused pass via
    [timeline_recovery.py#L404-L412](scripts/story_builder/timeline_recovery.py#L404-L412):
    `MonoBehaviour:Both`, `PlayableDirector:Both`, `TextAsset:Both`.
  - Confirmed on disk: `export_full/recovered/AnimeStudio-cli/{Streaming
    Assets,Persistent,timeline_extract/*}/json_by_type/PlayableDirector/`.
- `tools/endfield-il2cpp/` (Python) — parses `global-metadata.dat` offline
  via `catalog_option_flow_metadata.py` and resolves body-target methods to
  `GameAssembly.dll` via `map_body_targets_to_gameassembly.py`. Reports under
  `reports/option_flow_*` and `reports/option_flow_body_targets_*`.
- `tools/endfield_acl_sampler/` (C++/Python) — samples ACL-compressed
  animations for specific actors (`export_actor_samples.py`,
  `export_funnel_samples.py`, `export_zhuangfy_samples.py`).
- `tools/fluffy-dumper-src/` (Rust workspace) — VFS decryptor for
  StreamingAssets bundles. Modules: `chacha20`, `vfs`, `usm`, `vgmstream`,
  `xxhash3`, `xxtea`, `sparkbuffer`.
- `tools/Ruri.ShaderDecompiler/` — local checkout of Ruri's shader bytecode
  decompiler; CLAUDE.md tells us to pull upstream regularly. **No script in
  `scripts/` currently invokes it.**
- `tools/TypeTreeDumps/` — Unity TypeTree dumps across versions for the
  generic JSON fallback to handle classes without a dedicated parser.
- `tools/endfield_source_graph.py` produces
  `reports/source_graph/endfield_source_graph.sqlite` (385K files + 343K
  assets + 36K lines + 32K audio + 26K table rows + 8.6K stories + 4K
  options + 1.5K actors + 1088 story_graph_sources + 912 videos + 807
  animation_clips + 625 missions + 273 timelines + 124 textures + 7
  shaders). Edges already cover `has_line`, `audio_path`, `defines_audio`,
  `speaker_channel`, `uses_audio`, `spoken_by`, `option_path_line`,
  `has_story`, `mentions_actor`, `option_enters_story`,
  `has_timeline_line`, `option_anchor_after`, etc.

#### Untapped Unity classes (no parser, would use TypeTree fallback)

These are present in `ClassIDType.cs` but not in either AnimeStudio export
pass. Adding `<name>:Both` to `ANIMESTUDIO_JSON_TYPES` or `App.config types`
enables them without writing a new C# class because
[AssetsManager.cs#L681](tools/AnimeStudio/AnimeStudio/AssetsManager.cs#L681)
falls back to `new Object(objectReader)` which uses the serialized TypeTree.

- `PreloadData` (ClassID 150): per-bundle list of `m_Assets` PPtrs and
  `m_Dependencies` strings. Reveals which assets load together with a
  cutscene/scene. **Cohort signal: if cutscene C's bundle preloads
  `dlg_X` and `radio_Y`, those three files share a runtime cohort.**
- `AvatarMask` (319): body-part transform masks per animation. Validates
  which character body parts move during each cutscene; useful for the
  Unity character recovery lab.
- `NavMeshData` (238): navigation surface data per scene. Could correlate
  spatial progression with mission step, but high volume + low ordering
  payoff. Skip unless mapping work specifically calls for it.
- `ParticleSystem` (198) + `ParticleSystemRenderer` (199): VFX parameters.
  Low story-recovery payoff. Skip.
- `Cubemap` / `CubemapArray` / `RenderTexture` / `CustomRenderTexture`:
  environment maps. Skip.
- `GraphicsSettings` (30) / `LightmapSettings` (157): scene-wide lighting
  refs. Refs may be very large; skip unless needed.
- `StreamingController` (1542919678 custom): named in ClassIDType.cs;
  unclear payload without sampling. **Worth one probe.**

The 2026-05-14 patch enables `PreloadData:Both` and `AvatarMask:Both` in
both [export_full_from_game.py#L62-L66](scripts/export_full_from_game.py#L62-L66)
and the App.config defaults at
[App.config#L29](tools/AnimeStudio/AnimeStudio.CLI/App.config#L29). The
PlayableDirector entry was also added to App.config so default invocations
match the pipeline. The next `export.bat --skip-export-full` rebuild will
produce `json_by_type/PreloadData/` and `json_by_type/AvatarMask/` outputs.

#### Underused data already on disk

- **PlayableDirector container paths**: each
  `json_by_type/PlayableDirector/PlayableDirector#*.json` includes a
  `container` field naming the cutscene prefab (e.g.
  `assets/beyond/dynamicassets/gameplay/cutscenetransition/cutscene_map02_lv004_jinianguan_1/prefab/...`).
  Parsing that container path yields the mission/scene context for every
  PlayableDirector without any new tool invocation.
- **PlayableDirector m_SceneBindings**: maps Timeline track PPtrs to scene
  GameObject PPtrs. Combined with the GameObject `container` paths, this
  resolves "which NPC/prop plays in which Timeline track" — a direct
  bridge from cutscene Timeline to cutscene contents.
- **PlayableDirector m_ExposedReferences**: named exposed-reference table
  (string → PPtr). Designers often name these with the role they play
  ("MainCharacter", "VoiceTrack1"), giving a free vocabulary for what each
  binding does.
- **AssetBundle m_Dependencies**: cross-bundle dependency graph. Source
  graph already indexes some of this; verify coverage and emit a
  dependency-cohort report per cutscene bundle.
- **MonoBehaviour MarkerTrack in TimelineAsset**: Unity Timelines can carry
  named markers at specific time positions. The MonoBehaviour JSONs likely
  include any markers; verify by sampling a `dlgtl_*` TimelineAsset.
- **Material `m_TexEnvs` and `m_SavedProperties`**: each Material JSON
  exposes shader properties. Cutscene-specific materials often embed
  scene/character keywords in their property names.

#### Tools that need writing / extending

1. **PreloadData consumer** (Python): after the next export with the new
   types enabled, write a `scripts/story_recovery/build_preload_cohorts.py`
   that walks `json_by_type/PreloadData/*.json`, resolves each `m_Assets`
   PPtr to its asset stem via the asset map, and emits per-cutscene-bundle
   cohort manifests. New `reports/mission_order/preload_cohorts_*.md`.
2. **PlayableDirector context bridge** (Python): walk
   `json_by_type/PlayableDirector/*.json`, parse each `container` path,
   resolve `m_PlayableAsset` PPtr to the Timeline MonoBehaviour, and emit a
   mapping of (cutscene_id → PlayableDirector path → Timeline path → scene
   GameObject names → exposed references). This is the missing bridge
   from `PlayableDirector#*.json` to the cutscene story file. No tool
   patch needed; pure consumer.
3. **Ruri.ShaderDecompiler harness**: add `scripts/decompile_shaders.py`
   to iterate `Shader/*.shader` outputs, feed each through Ruri to recover
   readable source, and grep for embedded story keywords (mission ids,
   scene names) and TextAsset-style strings.
4. **fluffy-dumper USM subtitle extractor**: USM containers carry one or
   more `@SBT` / `@ALP` subchannels alongside `@SFV` video / `@SFA` audio.
   The `tools/fluffy-dumper-src/usm/` crate can already index the
   substream tags. Add a `--dump-subtitles` mode that emits per-USM
   `subtitles.json` with timing entries; the WebUI then has line-level
   timing for FMV cutscenes that lack a Timeline.
5. **endfield-il2cpp class catalog expansion**: extend
   `catalog_option_flow_metadata.py` to also catalog
   `Beyond.Gameplay.LevelScript.*` types (record kinds, opcode names if
   present) and `Beyond.Gameplay.Mission.*` types. This validates the
   working opcode hypotheses against the actual C# class names.
6. **endfield_acl_sampler extension**: add `export_levelscript_samples.py`
   that samples the ACL clips referenced from LevelScript records to
   confirm which cutscene the LevelScript intended to play.

### 2026-05-15 PlayableDirector Story-Context Bridge

Promoted the bridge consumer from scratch to
[scripts/story_recovery/build_playable_director_bridge.py](scripts/story_recovery/build_playable_director_bridge.py).
The script walks every `PlayableDirector#*.json` under
`export_full/recovered/AnimeStudio-cli/**/json_by_type/PlayableDirector/`,
parses the container path (e.g.
`assets/beyond/dynamicassets/gameplay/cutscenetransition/cutscene_map02_lv004_jinianguan_1/prefab/...`),
matches story prefixes `cutscene`, `cutscenetransition`, `cs`, `dlgtl`,
`dlg`, `levelseq`, `lvlseq`, `fmv`, `sns`, and emits one record per
PlayableDirector. Reports land at
`reports/playable_director/playable_director_bridge.{json,md}`.

First full run, 2026-05-15:

- PlayableDirector JSONs scanned: 12,237
- Distinct story names resolved: 539 (was 93 before the prefix widening)
- Distinct missions inferred: 85
- Kind breakdown: `dlgtl=3398`, `cutscene=2174`, `levelseq=1144`
- Without story name in container: 5,521 (likely UI/factory/effects)

Track-type histogram (top 10): `Animation Track`=35480,
`Activation Track`=16353, `Dialog Skeletal Morph Track`=3456,
`Dialog Mute Auto Blink Track`=2880, `Dialog Trunk Track`=2672,
`Additive Anim Track`=2128, `Entity VFX Playable Track`=1187,
`Cinemachine Track`=1080, `Common Mask Track`=734, `Audio Track`=640.

Notable lower-frequency tracks worth surfacing later: `Subtitle Track`=71
(authored subtitle timing for cutscenes that have no separate USM subtitle
stream), `Beyond FMV Track`=63 (FMV playback timing bound to the
PlayableDirector), `Dialog Use Emotion Lip Sync Track`=208,
`LipSyncTrack`=72, `小队控制1`=124 (squad-control track named in Chinese).

Top missions by PlayableDirector story count: `e0m0`=48 (matches its 48
WebUI entries — every entry is a separate PlayableDirector),
`map02_lv002`=31, `map02_lv004`=27, `map02_lv005`=16, `c27m4`=16,
`e2m6`=15, `f1m9`=13, `e9m2`=12, `e6m4`=12, `c17m3`=11.

Implication: every story-named PlayableDirector now carries a free
mission anchor through its container path. The WebUI builder could
consume this report to add a "PlayableDirector container" evidence row
to mission-order audits, giving anchor data for cutscene/dlgtl/levelseq
files whose ownership is otherwise weak.

### 2026-05-15 Radio Continuation Audit Promotion

Promoted the radio-continuation probe from scratch to
[scripts/story_recovery/build_radio_continuation_audit.py](scripts/story_recovery/build_radio_continuation_audit.py).
The audit walks every `<mission>_evidence_audit.json` already on disk,
pairs each `radio_<scene>_*` flagged `continueAfterDialog` (or
`continueAfterRadio`) with its nearest preceding `dlg_*`/`radio_*` in
the same LevelScript file, and emits
`reports/mission_order/radio_continuation_CN.{json,md}`.

Run against six missions (`e0m0`, `e1m1`, `c17m3`, `e10m4`, `c28m3`,
`e9m2`) on 2026-05-15:

```text
missions audited: 6; promotion candidates: 34; by kind: after-dialog=30, after-radio=4

per-mission:
  e9m2  : 17 candidates (15 after-dialog, 2 after-radio)
  c17m3 : 8 candidates (7 after-dialog, 1 after-radio)
  e10m4 : 4 candidates (4 after-dialog)
  e1m1  : 3 candidates (3 after-dialog)
  c28m3 : 2 candidates (1 after-dialog, 1 after-radio)
  e0m0  : 0 candidates (all 23 radios have both flags false — tutorial anomaly)
```

`e9m2` is significant — it sits on the inferredOptionResponse no-source
list, and the 17 candidates now give us 17 directly authored
`dlg → radio` adjacencies. Worth folding into the WebUI strong-edge set
in the next builder pass.

### 2026-05-15 Bridge Cross-Link to Mission Audits

The bridge consumer now supports `--cross-link`, which compares its
stories against every `<mission>_evidence_audit.json` on disk
(case-insensitive, stripping `misc_` prefix) and emits
`reports/playable_director/playable_director_bridge_cross_link.json`.

First run, six missions:

| mission | weak/unknown → anchored | already strong | total entries |
| --- | ---: | ---: | ---: |
| `e0m0` | **15** | 5 | 48 |
| `e1m1` | 6 | 1 | 48 |
| `e10m4` | 2 | 0 | 81 |
| `c17m3` | 1 | 0 | 76 |
| `c28m3` | 0 | 1 | 59 |
| `e9m2` | 0 | 1 | 58 |

`e0m0` is the highlight: **15 newly anchored entries** out of 41
weak+unknown. Every previously-unknown `cutscene_e0m0_*` finds a
PlayableDirector match, including `cutscene_e0m0_1`, `_1stZipline`,
`_10`, `_11`, `_12`, `_11111`, and `_tombstonecollapseCam`. The
anchor data exposes director counts (e.g. `cutscene_e0m0_2` has
**22 directors**, `_3/_4/_5` have 11 each), which gives a richness
signal in addition to the existence anchor.

Combined with the earlier per-mission status counts, the cumulative
2026-05-15 evidence position for `e0m0`:

```text
strong          7  (unchanged)
weak           26 of which  8 now also have a PlayableDirector anchor
unknown        15 of which  7 now also have a PlayableDirector anchor
total          48; 22 entries gain new evidence from the bridge alone
```

The radio-continuation audit and the PlayableDirector bridge are
complementary: the former addresses `radio_*` adjacency, the latter
addresses `cutscene_*/dlgtl_*/levelseq_*` ownership. Together they
cover most non-`dlg_` story file kinds.

### 2026-05-15 Next Slice

After the next `export.bat --skip-export-full` run produces
`json_by_type/PreloadData/` (enabled by the 2026-05-14 patch), write a
`scripts/story_recovery/build_preload_cohorts.py` consumer that walks
the new PreloadData JSONs, resolves each `m_Assets` PPtr to its asset
stem via the asset map, and emits per-cutscene-bundle cohort manifests
under `reports/mission_order/preload_cohorts_*.{json,md}`. Cross-check
the cohorts against the PlayableDirector bridge to confirm "cutscene C
loads dialog files D1/D2 and radio R1" is consistent with the
PlayableDirector's container path and Timeline track set.

Additional slices ready to land:

1. ~~Fold the bridge's `newAnchors` records back into
   `build_mission_order_evidence_audit.py`~~ — landed 2026-05-15. See
   below.
2. Pipe the radio-continuation candidates into
   `scripts/scene_order_gap_shared.py` as a new evidence class
   (`radio_continuation`) so the WebUI gets the promotion edges. Gate
   on the candidate set growing beyond the current 34, since each new
   edge needs to be source-explainable.

### 2026-05-15 Audit Folds in PlayableDirector + RadioContinuation Evidence

`build_mission_order_evidence_audit.py` now reads two prebuilt reports
when present and folds their findings as per-entry evidence:

- `reports/playable_director/playable_director_bridge.json` → adds
  `hits.playableDirector` with director count, total bindings,
  Timeline names, and track-type histogram. Restricted to the audit's
  mission (case-insensitive match, stripping `misc_`).
- `reports/mission_order/radio_continuation_CN.json` → adds
  `hits.radioContinuation` with the predecessor `dlg_*`/`radio_*`
  identified by the `continueAfterDialog`/`continueAfterRadio` rule,
  plus the LevelScript file/level pair the adjacency was observed in.

The markdown report gains two columns: `PlayDir` (`dN/bM` director
count / total bindings) and `RadioCont` (match kind + predecessor).
The summary block reports four new fields:
`playableDirectorAnchoredCount`, `weakOrUnknownGainingPlayableDirectorAnchor`,
`radioContinuationAnchoredCount`, `weakOrUnknownGainingRadioContinuationAnchor`.

Net effect across the ten 2026-05-15 audits (after replacing the empty
`f1m9` with `f1m9d3` once the regex fix landed):

| mission | entries | strong | weak | unknown | pd_anc | w/u_pd | rcont_anc | w/u_rcont | unique_w/u_promotions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `e0m0`   | 48 |  7 | 26 | 15 | **20** | **15** |  0 |  0 | **15** |
| `e1m1`   | 48 | 10 | 18 | 20 |  7 |  6 |  3 |  3 |  9 |
| `c17m3`  | 76 |  3 |  3 | 70 |  1 |  1 |  8 |  8 | **9** |
| `c28m3`  | 59 |  9 | 18 | 32 |  1 |  0 |  2 |  2 |  2 |
| `e9m2`   | 58 | 26 | 15 | 17 |  1 |  0 | 15 |  7 |  7 |
| `e10m4`  | 81 |  0 |  0 | 81 |  2 |  2 |  4 |  4 |  6 |
| `c27m4`  | 45 |  2 | 22 | 21 |  3 |  3 |  7 |  5 |  8 |
| `e2m6`   | 48 | 25 | 11 | 12 |  7 |  2 |  5 |  3 |  5 |
| `f1m9d3` | 22 |  8 |  2 | 12 |  3 |  3 |  0 |  0 |  3 |
| `e6m4`   | 58 | 20 | 17 | 21 |  3 |  3 |  0 |  0 |  3 |
| **total** | **543** | **110** | **132** | **301** | **48** | **35** | **44** | **32** | **67** |

Two signals are complementary: `PlayableDirector` covers
`cutscene_*`/`dlgtl_*`/`levelseq_*` files (Timeline-driven), and
`RadioContinuation` covers `radio_*` files (LevelScript-driven).
Together they promote 67 unique weak/unknown entries — **15%** of the
433 weak+unknown entries across these missions — in one pass without
running anything beyond `--skip-asset-map`.

### 2026-05-15 RadioContinuation Edges Land in the WebUI Builder

Promoted `radioContinuation` from a diagnostic-only signal to a real
WebUI evidence class. `scripts/story_builder/language_bundle.py` now:

- Loads `reports/mission_order/radio_continuation_CN.json` via a
  cached `_load_radio_continuation_candidates_by_mission` helper that
  returns an empty dict when the audit report is missing (silent
  no-op).
- Inside `build_mission_scene_graph`, after the `levelscriptFileOrder`
  edges are added, walks the mission's candidates and emits one
  `radioContinuation` edge per `(predecessor, radio)` pair when both
  keys are in `available`. Edges carry `sourceFiles`, `levelIds`, and
  `continuationKinds` for provenance.
- Adds `"radioContinuation"` to `strong_order_edge_kinds`. The
  authored `continueAfterDialog`/`continueAfterRadio` flag combined
  with a LevelScript file-offset adjacency is stronger than file-order
  alone because the flag asserts the radio is meant to follow the
  preceding dialog/radio.

Full CN rebuild (`build.py --languages CN --default-language CN`)
completes in 220.1s with no errors. After regenerating audits against
the new index, the cumulative position across the same 10 missions
shifts as follows:

| mission   | strong before | weak before | unk before | strong after | weak after | unk after | Δstrong |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `c17m3`   |  3 |  3 | 70 | **18** |  2 | 56 | **+15** |
| `e9m2`    | 26 | 15 | 17 | **37** |  4 | 17 | **+11** |
| `c27m4`   |  2 | 22 | 21 | **11** | 13 | 21 |  **+9** |
| `e1m1`    | 10 | 18 | 20 | **16** | 12 | 20 |  **+6** |
| `e10m4`   |  0 |  0 | 81 |  **6** |  0 | 75 |  **+6** |
| `e2m6`    | 25 | 11 | 12 | **30** |  6 | 12 |  **+5** |
| `c28m3`   |  9 | 18 | 32 | **12** | 15 | 32 |  **+3** |
| `e0m0`    |  7 | 26 | 15 |  7 | 26 | 15 |  +0 (anomaly) |
| `f1m9d3`  |  8 |  2 | 12 |  8 |  2 | 12 |  +0 |
| `e6m4`    | 20 | 17 | 21 | 20 | 17 | 21 |  +0 |
| **total** | **110** | **132** | **301** | **165** | **97** | **281** | **+55** |

Net: **+55 strong, -35 weak, -20 unknown** across 543 entries in 10
missions. The cascading effect (where adding a single radio edge
propagates ordering to other nodes via the scene-graph) shows up in
e10m4 most cleanly: 4 radio-continuation candidates land 6 strong
promotions because the radios pull two more file-order chains into a
strong ordered region.

`e0m0` stays at +0 because all 23 of its scene-keyed radios have both
`continueAfterDialog` and `continueAfterRadio` false (the tutorial
anomaly already noted). `f1m9d3` and `e6m4` stay at +0 because
neither had any RadioCont candidates.

The earlier `f1m9` anomaly turned out to be a regex bug — the bridge's
`MISSION_FROM_SCENE_RE` stopped at `f1m9` and discarded the `d3`/`d4`
sub-mission suffix even though the WebUI treats `f1m9d1`, `f1m9d2`,
`f1m9d3`, `f1m9d4` as distinct missions. Fixed by moving the
`(?:d\d+)?` segment **inside** the mission capture group, so
`cutscene_f1m9d3_1` now resolves mission=`f1m9d3` instead of `f1m9`.
After the fix the bridge resolves **97** distinct missions (up from
85) and a fresh audit of `f1m9d3` adds 3 PlayDir anchors (3
weak/unknown promoted). Edge-case verified: `e0m0_8d4` still resolves
to `e0m0` because the `d4` is separated by an underscore.

Radio-continuation audit also re-ran across the same 10 audits and
landed **48 promotion candidates** (41 after-dialog, 7 after-radio) —
up from 34 in the prior six-mission run.

Remaining un-anchored e0m0 entries (`radio_e0m0_1d5`, `_3d2`, `_5d6`,
`_9d5`, `_10`, `_11`, `_21`, plus `video_cs_video_e0m0_3`) are radio
files (no PlayableDirector by design — radios are LevelScript records,
not Timeline-driven) and one FMV. The radio-continuation rule already
addresses `radio_<scene>_*` flagged `continueAfter*`; the remaining
e0m0 anomaly stands because every e0m0 radio has both flags false.

### 2026-05-15 RadioContinuation Expansion Batch

Followed the low-risk path of auditing more PlayableDirector-bridge missions
now that `radioContinuation` is a real WebUI strong edge.

Added 20 mission-order audits for the highest-count unaudited bridge missions:
`map02_lv002`, `map02_lv004`, `map02_lv005`, `e0m2`, `e7m3`, `e6m3`,
`c16m4`, `c6m1`, `e8m5`, `e6m1`, `e3m4`, `e9m4`, `e5m1`, `c17m2`,
`c16m1`, `map02_lv001`, `e7m4`, `e8m1`, `map01_lv003`, and `f1m9d4`.

Baseline before refreshing radio continuation:

| metric | before |
| --- | ---: |
| strong | 159 |
| weak | 156 |
| unknown | 371 |

Rebuilt `reports/mission_order/radio_continuation_CN.{json,md}` across all
32 mission audits on disk. Candidate count rose from 48 to **128**:
104 `after-dialog`, 24 `after-radio`. After rebuilding the CN WebUI story
bundle and re-running the same 20 audits, the batch moved:

| metric | before | after | delta |
| --- | ---: | ---: | ---: |
| strong | 159 | 224 | +65 |
| weak | 156 | 91 | -65 |
| unknown | 371 | 371 | 0 |

Top promotions in this batch:

| mission | strong delta | radio-continuation candidates |
| --- | ---: | ---: |
| `c17m2` | +12 | 16 |
| `e6m1` | +12 | 9 |
| `e7m3` | +10 | 19 |
| `c16m4` | +10 | 7 |
| `e5m1` | +9 | 8 |
| `c16m1` | +4 | 2 |
| `c6m1` | +3 | 2 |
| `e9m4` | +2 | 2 |
| `e6m3` | +2 | 1 |
| `e7m4` | +1 | 10 |

The map-scoped bridge missions (`map02_lv002`, `map02_lv004`,
`map02_lv005`, `map02_lv001`, `map01_lv003`) stayed at zero radio candidates
and remain entirely unknown in this audit shape. They likely need a different
ordering source than `RadioTable.continueAfter*`.

Ran a second non-map expansion batch for:
`e10m2`, `e2m5`, `c16m3`, `e8m3`, `e8m2`, `e1m4`, `e4m1`, `c13m2`,
`e10m1`, `gm02m4`, `e2m2`, `e3m3`, `f1m4d1`, `e1m2`, `c27m5`,
`c28m2`, `c27m2`, `e10m3`, `c13m3`, and `e4m1d5`.

That raised the radio-continuation report to **146** candidates across
52 mission audits: 120 `after-dialog`, 26 `after-radio`. After another CN
WebUI rebuild and audit pass, the second batch moved:

| metric | before | after | delta |
| --- | ---: | ---: | ---: |
| strong | 133 | 158 | +25 |
| weak | 101 | 76 | -25 |
| unknown | 218 | 218 | 0 |

Second-batch promotions were smaller but still useful:

| mission | strong delta | radio-continuation candidates |
| --- | ---: | ---: |
| `c16m3` | +4 | 2 |
| `e3m3` | +4 | 2 |
| `e8m2` | +3 | 3 |
| `e1m4` | +3 | 2 |
| `e8m3` | +3 | 2 |
| `e10m1` | +2 | 2 |
| `e2m2` | +2 | 2 |
| `e4m1` | +2 | 2 |
| `e1m2` | +2 | 1 |

Total measured radio-continuation WebUI impact so far across the original 10
missions plus both 20-mission expansion batches: **+145 strong**,
**-125 weak**, **-20 unknown**. The expansion batches converted only weak
rows, while the original batch had the useful unknown-to-strong movement in
`c17m3` and `e10m4`. Next best target is no longer more blind
radio-continuation batching; it is either a map-scoped ordering source for the
all-unknown `map*_lv*` rows, or the deeper PlayableDirector timeline-order
edge derivation.

### 2026-05-15 Map-Scoped LevelScript File-Order Seed

The first map-scoped ordering gap was a WebUI builder omission, not missing
evidence. Mission-order audits for `map02_lv002`, `map02_lv004`, and
`map01_lv003` were already seeing LevelScript `matchedSequence` chains, but
`build_mission_scene_graph` did not seed the map id itself into
`flow_level_ids` when the mission key was already a `map##_lv###` level id.
That meant `_build_levelscript_file_order_scene_sequences` never ran for these
map missions during WebUI generation.

Patched `scripts/story_builder/language_bundle.py` to add the mission id to
`flow_level_ids` when it matches `^map\d+_lv\d+$`. This preserves the existing
weak-only semantics of `levelscriptFileOrder`; it just lets map-scoped missions
participate in the same file-order scan as normal missions with known levels.

After a CN rebuild and re-running the five map-scoped audits:

| mission | weak before | weak after | unknown before | unknown after |
| --- | ---: | ---: | ---: | ---: |
| `map02_lv002` | 0 | 8 | 52 | 44 |
| `map02_lv004` | 0 | 8 | 22 | 14 |
| `map01_lv003` | 0 | 9 | 46 | 37 |
| `map02_lv005` | 0 | 0 | 12 | 12 |
| `map02_lv001` | 0 | 0 | 14 | 14 |
| **total** | **0** | **25** | **146** | **121** |

Net: **+25 weak**, **-25 unknown**. `map02_lv005` and `map02_lv001`
still have no WebUI-relevant LevelScript sequences in the audit output; they
only expose LevelData/table/audio-style validation hits, so they need a
different source before promotion.

Follow-up checks:

- `map02_lv005` LevelData contains the remaining `dlg_map02_lv005_1200*`
  references, but the byte/entity order is `12001`, `12003`, `12004`,
  `12002`, `12007`, `12005`, `12006`. That is useful placement/trigger
  validation, not a safe chronology signal.
- `map02_lv001` has PlayableDirector anchors for six cutscenes, but the bridge
  records are per-cutscene prefab/timeline containers. They prove the cutscene
  asset family exists; they do not yet expose a shared parent timeline with
  inter-cutscene `m_Start` order.
- The current PlayableDirector bridge is therefore still anchor-only. Promoting
  it to ordering evidence needs a new source: a parent timeline, sequencer, or
  control-flow edge that references multiple story keys with authored order.

Added a LevelData interaction-order diagnostic to
`scripts/story_recovery/build_mission_order_evidence_audit.py` so future map
passes show the exact LevelData story-ref sequence plus nearby entity, quest,
ReadingPopUp, and PRTS ids when present. This is deliberately report-only:
LevelData interaction order is not a WebUI edge kind yet.

The rerun confirms why this stays diagnostic:

| mission | LevelData adjacent pairs | observed sequence |
| --- | ---: | --- |
| `map02_lv001` | 6 | `radio_map02_lv001_1` -> `dlg_map02_lv001_1` -> `dlg_map02_lv001_2` -> `dlg_map02_lv001_3` -> `dlg_map02_lv001_5` -> `dlg_map02_lv001_6` -> `dlg_map02_lv001_7` |
| `map02_lv005` | 6 | `dlg_map02_lv005_12001` -> `dlg_map02_lv005_12003` -> `dlg_map02_lv005_12004` -> `dlg_map02_lv005_12002` -> `dlg_map02_lv005_12007` -> `dlg_map02_lv005_12005` -> `dlg_map02_lv005_12006` |

`map02_lv001` happens to mostly look numeric after the opening radio, but
`map02_lv005` is visibly placement/entity order. That makes the signal useful
for finding trigger records and quest ids, but too weak to promote rows out of
`unknown` by itself.

Reran the same diagnostic on the three map missions that already gained weak
LevelScript edges. Their LevelData sequences are also mixed placement order:

| mission | LevelData adjacent pairs | note |
| --- | ---: | --- |
| `map02_lv002` | 28 | includes jumps such as `2` -> `3` -> `5` -> `26` -> `7` and a separate `12001`-family run |
| `map02_lv004` | 9 | main run is `3` -> `4` -> `5` -> `6` -> `7` -> `8` -> `9` -> `1` -> `10` -> `2` |
| `map01_lv003` | 8 | multiple short runs, including `1` -> `19` -> `2` -> `20` and a radio-led interaction run |

So LevelData order should stay an audit column / diagnostic section. It is
good at exposing which interaction records contain story keys, but not at
recovering chronology without another authored edge.

Extended that diagnostic with LevelData quest-owner lookup. When a nearby
quest-like id such as `e5m1_q#4` appears in the LevelData context, the audit now
resolves it back to its owning `MissionRuntimeAsset`, predecessor list, child
quests, level, flow index, and any story refs on that exact quest.

Results on the map batch:

| map audit | LevelData quest owner | owner mission | owner level | outcome |
| --- | --- | --- | --- | --- |
| `map02_lv001` | `e5m1_q#4` | `e5m1` | `map02_lv001` | real quest node, but no story refs on the owned row; neighboring script-stage refs belong to `e5m1` stories such as `dlg_e5m1_5` / `radio_e5m1_30`, not the `map02_lv001_*` map-scoped rows |
| `map02_lv002` | `e5m3_q#3` | `e5m3` | `map02_lv001` | real quest node, but no story refs on the owned row; nearby script evidence resolves to `e5m3` story refs such as `radio_e5m3_0d8` |
| `map02_lv005` | none | - | - | no quest owner signal |
| `map02_lv004` | none | - | - | no quest owner signal |
| `map01_lv003` | none | - | - | no quest owner signal |

So LevelData quest ownership is a useful provenance clue, but still not a
promotable order edge for the map-scoped rows. It shows that some map
interactions participate in regular mission quest graphs; it does not order the
standalone `map##_lv###` story files.

### 2026-05-15 PRTS Collection-Order Weak Edges

The `rp_*` / `nar_*` trace produced one conservative promotable signal:
`PrtsAllItem` rows have `firstLvId` + `order`, which is authored page order
inside a single PRTS reading/collection item. This is not mission chronology,
but it is a legitimate local sequence for multi-page documents. The builder now
emits weak `prtsCollectionOrder` edges only when:

- the row is `type=text` via `contentId=text_*`;
- multiple rows share the same `firstLvId`;
- each adjacent `order` slot maps to exactly one available story key;
- ambiguous duplicate slots, such as `black_*` + `dlg_*` sharing the same text
  content, are skipped.

After rebuilding CN and rerunning the map audits:

| mission | weak before | weak after | unknown before | unknown after | PRTS edges |
| --- | ---: | ---: | ---: | ---: | ---: |
| `map02_lv001` | 0 | 3 | 14 | 11 | 2 |
| `map02_lv002` | 8 | 21 | 44 | 31 | 9 |
| `map02_lv005` | 0 | 0 | 12 | 12 | 0 |
| `map02_lv004` | 8 | 8 | 14 | 14 | 0 |
| `map01_lv003` | 9 | 9 | 37 | 37 | 0 |
| **total** | **25** | **41** | **121** | **105** | **11** |

Net from PRTS collection order on this map batch: **+16 weak**, **-16
unknown**. Examples:

- `map02_lv001`: `dlg_map02_lv001_3` -> `dlg_map02_lv001_4` ->
  `dlg_map02_lv001_5` from `paper_map02_3` orders 1/2/3.
- `map02_lv002`: `paper_map02_39` orders `dlg_map02_lv002_16` ->
  `17` -> `18` -> `19`, and `paper_map02_42` orders `22` -> `23` -> `24`.

Keep this edge weak. Some collections order pages within a document, not
world-story beats, and groups like `paper_map02_25` can jump from
`dlg_map02_lv002_3` to `dlg_map02_lv002_12` to `dlg_map02_lv002_26`.

### 2026-05-15 Option Position / Inferred Response Status

The option-placement warning queue had a large false-positive component:
table-only scenes where the option group number exactly matches an existing
dialog line suffix (`group 1` -> line `_001`, etc.). The builder now treats
that as a source-keyed option anchor instead of a warning-only fallback, while
leaving `sparseGap`, `lastLine`, and sibling-timeline placement flagged.

After CN rebuilds:

- `reports/inferred_option_anchors_CN.md` dropped from 97 scenes / 182 groups
  to **2 scenes / 2 groups**.
- In the priority story buckets (`e`, `a`, `gm`, `c`), only
  `dlg_gm01m25_5` (`sparseGap`) still needed runtime-registration triage.
- `dlg_e2m6_11` no longer warns: the local Timeline/sibling placement is now
  source-backed by `dlg_e2m6_19`, whose authored SceneGraph option branches
  exactly match the local post-choice response text (`007`/`008` for option 1,
  `009` for option 2).
- The other remaining global layout warning is `dlg_map02_lv001_env_8`, which
  is outside the current priority story buckets.
- Empty one-choice rows such as `dlg_gm01m5_1` no longer emit raw
  option-layout warnings, matching the scene-order analyzer's "no meaningful
  options" behavior.

The remaining inferred-response queue still has strong negative evidence. The
current `reports/timeline_option_flow_audit_CN.json` summary shows:

- `20` inferred response groups remain.
- all `20` classify as `rawTrunkClipOptionIndexDefaultAdjacent`.
- all `20` have runtime-gate verdict
  `strictOptionRowsButAllZeroCandidateRuntimeField`.
- candidate raw clip `optionIndex` counts are all `0`; no candidate group maps
  back to nonzero option rows.

This means option row positions are known for these groups, but the suspected
response clips are not runtime-active branch clips. The one visible nonzero
window case, `dlg_c28m3_23` group 1, has its nonzero field on the common
continuation / later option region, not on the candidate response rows. Keep
these groups blocked until a Runtime Jump Track route, explicit DialogTree
edge, sibling SceneGraph text match, or another authored route source appears.

Refreshed `reports/source_graph/endfield_source_graph.sqlite` after the option
placement fixes to remove stale issue output. The refreshed graph now reports
the same live queue: **15 scenes / 20 groups** with
`inferredOptionResponse`.

Rerunning the response-route audits after the graph refresh closed the obvious
promotion paths:

- `build_dialog_tree_option_route_audit.py`: 20 groups audited, 0 authored
  route candidate hits, 0 explicit per-option routes.
- `build_timeline_option_flow_audit.py`: 20 groups audited, 0 nonzero
  candidate trunk/raw `optionIndex`; all candidate runtime fields are zero.
- `build_timeline_binding_audit.py`: 20 groups audited, 0 option-named track
  mappings.
- `build_option_playable_semantics_audit.py --only-interesting`: 14 groups
  with decoded option rows, 0 explicit target fields.
- `build_option_logic_id_audit.py`: 31 logic-bearing option rows, 0
  same-mission exact references; the two external `logicId=3` hits are unrelated
  GameplayConfig rows.

The remaining plausible response-route direction is therefore not a loose
promotion rule. It is runtime Timeline semantics: understand how selected
`DialogOptionPlayableAsset` rows drive active clip/time-range selection. Current
IL2CPP facts show `_SelectIndexInTimeline` passes the selected option object's
`+0x98` into `DialogChooseOption`, then active branch clips require a positive
runtime `+0x18` option field. All current candidate response clips have zero in
that runtime field, so adjacency to option clips is negative evidence until the
active-clip/range mechanism is decoded more precisely.

Refined the Runtime Jump follow-up audit so its default scope matches the live
`inferredOptionResponse` warning queue instead of every retained diagnostic
`optionBranchRisk` row. This excludes already anchored raw trunk
`clipOptionIndex` cases such as `dlg_c28m3_10` from the unresolved queue while
keeping them inspectable with `--include-promoted-risk-groups`.

Current strict Runtime Jump response-route check:

- `reports/runtime_jump_option_route_audit_CN.md`: 20 live inferred groups,
  3 with nearby Runtime Jump clips, 0 strict promotions.
- `dlg_c28m3_23` group 1 has nearby jump clips, but they belong to optionIndex
  3/4 while the unresolved group has optionIndex 1/2.
- `dlg_e6m1_10` group 4 and `dlg_e6m4_14` group 2 have nearby jump clips, but
  the recovered runtime path either contradicts the inferred first line or
  resets option state to default. Do not promote them.
- `reports/runtime_jump_option_route_audit_CN_nearby_promoted.md` keeps the
  promoted diagnostic comparison; `dlg_c28m3_10` remains a raw
  `clipOptionIndex` positive case, not a live unresolved warning.

Added a positive/negative control report at
`reports/option_route_evidence_controls_CN_priority.md`. In priority buckets,
the positive Runtime Jump route shape has **30 groups / 63 route entries**:
all 30 groups have distinct per-option paths and skip/reverse range evidence
for every option. The 20 live unresolved groups have no such complete shape and
0 strict passes. This is the current evidence standard for promoting inferred
responses from Runtime Jump data.

The focused priority report is now generated by
`scripts/story_recovery/build_priority_story_order_audit.py` at
`reports/priority_story_order_CN.md`.

Added a WebUI `LevelData` host scan for parent-variant LevelScript levels.
Files such as `*_sub_e10m4d5.json` and `*_sub_c17m3d5.json` now seed their
host levels into parent missions `e10m4` and `c17m3`, letting the existing
weak `levelscriptFileOrder` edge run for priority missions that previously had
matching audit evidence but no WebUI level seed.

Measured priority impact after rebuild:

| bucket | before weak | after weak | before unknown | after unknown | delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| main | 280 | 308 | 914 | 886 | +28 weak / -28 unknown |
| character | 100 | 123 | 445 | 422 | +23 weak / -23 unknown |
| event | 8 | 8 | 61 | 61 | 0 |
| major | 38 | 38 | 331 | 331 | 0 |
| **total** | **426** | **477** | **1751** | **1700** | **+51 weak / -51 unknown** |

Strong rows are unchanged at `938`; this edge remains weak. The visible wins
are `e10m4` unknowns dropping from 85 to **57** and `c17m3` dropping from 58
to **35**.

Expanded the mission-order audit coverage to every missing priority mission
(`e`, `a`, `gm`, `c`) with the heavy AssetMap pass disabled. That raised the
radio-continuation report from the earlier 44 candidates to **204** candidates
across **145** audited missions (`after-dialog=155`, `after-radio=49`).

After refreshing `reports/mission_order/radio_continuation_CN.json` and
rebuilding CN, the extra radio edges promoted weak entries to strong entries:

| bucket | strong before | strong after | weak before | weak after | unknown before | unknown after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| main | 538 | 576 | 308 | 270 | 886 | 886 |
| event | 62 | 62 | 8 | 8 | 61 | 61 |
| major | 122 | 122 | 38 | 38 | 331 | 331 |
| character | 216 | 224 | 123 | 115 | 422 | 422 |
| **total** | **938** | **984** | **477** | **431** | **1700** | **1700** |

At that point priority-bucket totals were `3115` entries: `984` strong,
`431` weak, `1700` unknown. The radio batch did not reduce unknown rows because
the new candidates mostly overlapped rows already recovered weakly by
LevelScript file-order evidence, but it still made those rows strong in the
WebUI ordering graph.

The biggest remaining unknown mission queues were `e10m4` (57), `c16m4` (53),
`c6m1` (44), `e1m1` (43), `c28m3` (41), `e9m3` (39), `e0m2` (38), `e1m2`
(38), `e1m3` (37), and `c17m3` (35).

The `e9m3` hole turned out to be a mission-discovery bug in the WebUI builder,
not missing source data. `e9m3` is mostly radio/cutscene content, so it was not
in `known_missions` when `language_bundle.py` scanned LevelData host filenames
like `dung02_dg003_lv_data_sub_e9m3.json`. Adding `RadioTable` and
`RemoteCommonTable` ids to that early known-mission seed lets the existing
LevelData-host scan include `dung02_dg003`, and the already-authored
LevelScript file-order / UID-chain logic then recovers the mission:

| mission | before strong | before weak | before unknown | after strong | after weak | after unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `e9m3` | 0 | 0 | 39 | 2 | 26 | 11 |

Evidence source:
`export_full/structured/StreamingAssets/Data/Json/LevelData/dung02_dg003/dung02_dg003_lv_data_sub_e9m3.json`
links the mission to the dungeon host, then
`LevelScriptData/dung02_dg003/29800030000.json`, `29800030003.json`, and
`29800030004.json` provide the recovered sequence. The regenerated
`reports/mission_order/e9m3_evidence_audit.md` now reports status
`strong=2`, `weak=26`, `unknown=11`.

Current priority totals after this fix are `3115` entries: `986` strong,
`457` weak, `1672` unknown. This is a net **+2 strong / +26 weak /
-28 unknown** in the priority scope, entirely from original game-data host and
LevelScript evidence.

The next recovery came from parent/variant MissionRuntime evidence. Some
playable variants, such as `e10m4d5` and `c16m4d5`, own quest DAGs and
client-action/script-condition story refs whose story keys are parent mission
keys (`radio_e10m4_*`, `dlg_c16m4_*`, etc.). The WebUI story entries live under
the parent mission, so `language_bundle.py` now folds matching `*d#`
MissionRuntimeAsset quests into the **scene graph ordering pass only** when
their story refs resolve to actual parent WebUI nodes. The visible mission flow
payload stays parent-scoped.

After rebuilding CN:

| bucket | before strong | before weak | before unknown | after strong | after weak | after unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| main | 578 | 296 | 858 | 611 | 272 | 849 |
| character | 224 | 115 | 422 | 247 | 109 | 405 |
| event | 62 | 8 | 61 | 62 | 8 | 61 |
| major | 122 | 38 | 331 | 122 | 38 | 331 |
| **total** | **986** | **457** | **1672** | **1042** | **427** | **1646** |

Net from variant MissionRuntime scene-graph evidence: **+56 strong**,
**-30 weak**, **-26 unknown**.

Largest mission impacts:

| mission | variant source | before | after |
| --- | --- | --- | --- |
| `e10m4` | `MissionRuntimeAsset/e10m4d5.json` plus referenced `LevelScriptData/dung02_rdg002` scripts | 6 strong / 28 weak / 57 unknown | 28 strong / 8 weak / 55 unknown |
| `c16m4` | `MissionRuntimeAsset/c16m4d5.json` quest refs and client actions | 10 strong / 8 weak / 53 unknown | 21 strong / 4 weak / 46 unknown |

`reports/mission_order/e10m4_evidence_audit.md` and
`reports/mission_order/c16m4_evidence_audit.md` now include a `VariantMR`
column so the provenance is visible in the generated audit rather than implied
by the final strong/weak status.

The next promotable source is NPC proxy dialog evidence. `MissionRuntimeAsset`
quest objectives often track an NPC proxy without directly naming the dialog,
while `GameplayConfig/NpcProxyExDataTable.json` assigns the active dialog to
that proxy. The builder now records a `proxyDialogs` ref only when the tracked
proxy is unique to one quest in the mission and the proxy table has exactly one
usable dialog row for that mission. This avoids the noisy shared-proxy cases
seen in several `gm*` missions.

After rebuilding CN, priority-bucket totals moved from `1042` strong,
`427` weak, `1646` unknown to `1075` strong, `421` weak, `1619` unknown:
**+33 strong / -6 weak / -27 unknown**.

Representative promotions:

| mission | evidence | result |
| --- | --- | --- |
| `c6m1` | `c6m1_q#9` tracks `c6m1Unionminer2_map01_001`, whose `NpcProxyExDataTable` row assigns `dlg_c6m1_33`; `c6m1_q#talkStartDgn` tracks `wolfgd_map01_002`, which assigns `dlg_c6m1_20` | `11/4/43` -> `13/3/42` in the mission audit |
| `e10m4` | `e10m4_q#2` tracks `zhuangfy_indie_dg005_e10m4opendoor`, which assigns `dlg_e10m4_10` | `28` -> `29` strong |
| `c16m4` | `c16m4_q#1` tracks `pelica_base01_lv001_c16m4`, which assigns `dlg_c16m4_1` | `21` -> `22` strong |
| `c27m4` | `c27m4_q#2` tracks `tangtang_map02_c27m3fuben`, which assigns `dlg_c27m4_14` | `12` -> `13` strong |

`scripts/story_recovery/build_mission_order_evidence_audit.py` now reports a
`ProxyDlg` column so these rows show the exact `npcProxyId <- questId`
provenance instead of appearing as unexplained strong rows with
`MissionRuntime=0`.

Retired four priority line-order warnings with a narrow
`numericBoundaryStitch` source. This only covers rows whose numeric suffix sits
outside the authored DialogTree/Timeline span, such as an intro line before the
first Timeline clip or a terminal line after the last DialogTree trunk. In-range
holes are still flagged.

The remaining priority line-order warnings are therefore small
partial-coverage cases, not broad missing-order buckets:

| bucket | scene | uncovered lines |
| --- | --- | --- |
| event | `dlg_a1m4_1` | `016`, `017` |
| character | `dlg_c17m2_10` | `002` |
| major | `dlg_gm02m13_3` | `003` |
| major | `dlg_gm02m13_4` | `003` |

These are next in line if we want to reduce priority warnings further. They
look like in-range DialogTree/Timeline coverage holes where the builder has a
final placement, but the uncovered lines are not directly named by the authored
source used for that scene. Source-graph checks for the four uncovered line
nodes only found generated `webui/story` membership, speaker, and audio edges,
not a DialogTree/Timeline/mission-source ordering edge, so they should stay
warning-backed until another original source appears.

Added two more MissionRuntime-only recovery passes for the priority buckets:

- Scene-ref aliasing now treats `dlg_*` / `misc_dlg_*` as aliases in the shared
  source-ref resolver, and `build_mission_scene_graph` resolves normal quest
  `dialogs`, `cutscenes`, `remotecomms`, and `radios` through that resolver
  instead of raw string membership. This promotes quest-authored d-variant
  dialog refs such as `dlg_e2m5_2d7` to the actual WebUI node
  `misc_dlg_e2m5_2d7`.
- Client action extraction now follows explicit `actionMapRaw` `_nextID`
  chains from each `clientActionMapValue` root. This attaches chained
  `PlayRadio` refs to the same quest only when the original MissionRuntime
  action graph says the action follows the root.

Measured CN priority impact:

| pass | strong | weak | unknown | delta |
| --- | ---: | ---: | ---: | --- |
| after NPC proxy / variant-gate consistency | 1087 | 412 | 1616 | - |
| after `dlg` -> `misc_dlg` quest aliasing | 1099 | 408 | 1608 | +12 strong / -4 weak / -8 unknown |
| after `_nextID` client-action chains | 1104 | 408 | 1603 | +5 strong / -5 unknown |

Representative alias promotions:

| mission | promoted rows | evidence |
| --- | --- | --- |
| `e2m5` | `misc_dlg_e2m5_2d7`, `misc_dlg_e2m5_3d5` | `MissionRuntimeAsset/e2m5.json` quest `dialogs` / `CheckTalkOptionFinish` refs use the raw `dlg_*d*` ids |
| `e7m2` | `misc_dlg_e7m2_3d5` | quest `e7m2_q#15` names `dlg_e7m2_3d5` |
| `gm01m6` | `misc_dlg_gm01m6_3d5` | quest `gm01m6_q#3` names `dlg_gm01m6_3d5` |

Representative `_nextID` promotions:

| mission | promoted rows | evidence |
| --- | --- | --- |
| `e6m4` | `radio_e6m4_20`, `radio_e6m4_32` | `clientActionMapValue` roots action `27`; action `27 -> 28 -> 29` via `_nextID`, and actions `28` / `29` are `PlayRadio` |
| `c28m1` | `radio_c28m1_6` | chained `PlayRadio` under quest `c28m1_q#10` |
| `c28m2` | `radio_c28m2_20` | chained `PlayRadio` under quest `c28m2_q#10` |
| `gm01m22` | `radio_gm01m22_2d7` | chained `PlayRadio` under quest `gm01m22_q#4` |

Tightened `build_mission_order_evidence_audit.py` string matching so diagnostic
MissionRuntime hits no longer count `dlg_c6m1_1` inside distinct ids like
`dlg_c6m1_17`. The audit still allows line/audio suffixes such as
`dlg_x_1_001`, but rejects alphanumeric continuations.

Follow-up evidence checks kept the same boundary:

- `dlg_gm01m25_5` is now separated as `nonRuntimeOptionLayout` in
  `reports/priority_story_order_CN.md`. Its scene key is absent from
  `Beyond.Gameplay.DialogIdTable`, so the runtime `DialogManager` has no
  gameplay entry point for it. The option rows still exist in
  `DialogOptionTable` / `DialogTextTable`, but without a runtime registry row
  this looks like cut or unreferenced content, not an active option-location
  bug.
- The remaining uncovered line ids (`dlg_a1m4_1_016`, `dlg_a1m4_1_017`,
  `dlg_c17m2_10_002`, `dlg_gm02m13_3_003`, and `dlg_gm02m13_4_003`) were
  checked against source graph edges, decoded related DialogTree JSON and
  extra-config files, `DialogIdTable`, `MissionRuntimeAsset`, `LevelScriptData`,
  `AudioDialog`, and structured table hits. The exact line ids are absent from
  the original DialogTree/timeline/mission ordering sources; they only have
  table/audio-style presence evidence. Keep them warning-backed rather than
  promoting a placement from numeric fallback.

Added another original-data extractor fix for MissionRuntime objective script
anchors:

- Objective leaf extraction now reads both underscored and non-underscored
  LevelScript fields: `_scriptId` / `scriptId`, `_levelId` / `levelId`,
  `_mapId` / `mapId`, and scene-id variants. Several conditions use
  `CheckLevelScriptStage*` with `levelId.constValue` and
  `scriptId.constValue.scriptId`; before this pass, the audit could see those
  script ids diagnostically, but the WebUI scene graph could not bind them back
  to their LevelScript story refs.
- The mission-order audit now reports `levelId`/`mapId` for these script
  conditions so the evidence column names the original file pair instead of
  leaving the map column blank.

Measured CN priority impact:

| pass | strong | weak | unknown | delta |
| --- | ---: | ---: | ---: | --- |
| after `_nextID` client-action chains | 1104 | 408 | 1603 | - |
| after objective `scriptId` / `levelId` aliases | 1142 | 388 | 1585 | +38 strong / -20 weak / -18 unknown |

Representative objective-script promotions:

| mission | promoted rows | evidence |
| --- | --- | --- |
| `e2m5` | `misc_dlg_e2m5_2d8`, `misc_dlg_e2m5_2d9`, `dlg_e2m5_3` | `MissionRuntimeAsset/e2m5.json` quest `e2m5_q#23` / `e2m5_q#32` checks `map01_lv005` scripts `3400060028`, `3400060029`, and `3400060027`; those LevelScript files name the promoted scenes |
| `e6m4` | `radio_e6m4_19`, `cutscene_e6m4_transition_1`, `dlg_e6m4_5`, `radio_e6m4_4`, `dlg_e6m4_8` | quests `e6m4_q#8`, `#11`, `#9`, and `#41` check `map02_lv002` scripts `22800110036`, `22800110006`, `22800110003`, and `22800110032` |
| `e1m2` | `radio_e1m2_3`, `dlg_e1m2_1`, `radio_e1m2_4`, `dlg_e1m2_2`, `dlg_e1m2_3`, `radio_e1m2_6` | quest `e1m2_q#3` checks `map01_lv001` scripts `2100060024`, `2100060025`, and `2100060026` |

The option-location / inferred-response boundary is unchanged after this pass:
remaining inferred responses still fail the runtime-jump positive-control rule,
and priority option-layout warnings are down to the single unregistered
`dlg_gm01m25_5` non-runtime case.

Added two small original-data order lanes after the objective-script pass:

1. Mission area ids that embed story keys are now treated as real quest anchors.
   The scanner reads `_areaId` / `areaId` / `missionAreaId` from
   `MissionRuntimeAsset` objective conditions and tracking hints. This is a
   narrow source because the original quest data literally names the story key
   inside an area id, e.g. `e1m1_radio_e1m1_3d2`.
   - CN priority impact: `radio_e1m1_3d2` moved from unknown to strong.
   - Totals after this pass: `3115` priority entries; `1143` strong, `388`
     weak, `1584` unknown.
   - Example edge: `radio_e1m1_3 -> radio_e1m1_3d2 -> radio_e1m1_4d5`, sourced
     from the `e1m1_q#62` quest/area anchor and normal quest predecessor edges.

2. LevelData quest/story co-location is now a weak WebUI evidence class.
   The scanner searches original `LevelData/*.json` byte-string context for a
   nearby quest id and story id, requires the story mission to match the quest
   mission or its parent variant, then attaches compact `levelDataStoryRefs` to
   the matching mission-flow quest. `language_bundle.py` emits
   `levelDataQuestRef` edges as weak only. This deliberately does not upgrade
   to strong because LevelData proves a quest-gated host/trigger relationship,
   not strict playback chronology.
   - CN priority impact: strong unchanged at `1143`; weak `388 -> 401`;
     unknown `1584 -> 1571`.
   - New weak anchors include `radio_c16m4_2d6`, `radio_c28m3_33`,
     `radio_e1m7_3d4`, `radio_e1m7_8`, `radio_gm01m11_3`,
     `radio_gm01m11_4`, `radio_e10m3_9`, `radio_e5m2_18`,
     `radio_e7m1_18`, `radio_c17m2_25`, `radio_c17m2_26`,
     `radio_c28m1_16`, and `radio_e2m5d5_4`.
   - Representative original-data edges:
     - `c16m4`: `radio_c16m4_2d5 -> radio_c16m4_2d6`, quest
       `c16m4d5_q#11`, file
       `LevelData/dung01_rdg003/dung01_rdg003_lv_data_sub_c16m4.json`, entity
       `int_narrative_common_empty`.
     - `c28m3`: `dlg_c28m3_19 -> radio_c28m3_33`, quest `c28m3_q#19`, file
       `LevelData/dung01_rdg007/dung01_rdg007_lv_data_sub_c28m3.json`.
     - `gm01m11`: `dlg_gm01m11_2 -> radio_gm01m11_3 ->
       radio_gm01m11_4`, quests `gm01m11_q#5` / `gm01m11_q#6`, fields
       `radio_await_start`, `radio_escape_start`, and `require_quest`.

The option-location / inferred-response boundary is still unchanged: the
remaining inferred responses have no positive runtime jump / option target
evidence, and `dlg_gm01m25_5` remains the only priority option-layout warning,
classified as non-runtime/unregistered content.

#### Anti-targets (not worth the decoder budget)

- Patching AnimeStudio to add a dedicated `PlayableDirector` C# class —
  the generic TypeTree fallback already exposes every field we care about.
- Patching AnimeStudio to add `LightmapSettings` / `Cubemap` — large
  outputs, no story payoff.
- Writing a custom GameAssembly.dll decompiler — HGP relocates
  MetadataRegistration; the metadata.dat string-scan approach already in
  `tools/endfield-il2cpp/` is the deterministic path.
- Extending fluffy-dumper to handle previously-unsupported encryption — the
  current chacha20/xxtea path already cracks the StreamingAssets VFS.

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

9. Surface mission-order confidence separately in UI:
   - strong: quest DAG, authored scene link, or UID-linked LevelScript scene
     chain.
   - weak: LevelScript file-offset order, or LevelData quest/story co-location
     where the original level data proves a quest-gated host/trigger but not
     strict playback chronology.
   - unknown: fallback/numeric order only. Keep these after strong/weak ordered
     files in the sidebar, sorted by the numeric index recovered from the file
     key tail (`1`, `1d5`, `New14`, etc.).

### 2026-05-16 Timeline Track Clip Consumer

New consumer for the PlayableDirector bridge histogram's
high-value track types:
[scripts/story_recovery/build_timeline_track_clip_consumer.py](scripts/story_recovery/build_timeline_track_clip_consumer.py).

The script walks
`export_full/recovered/AnimeStudio-cli/timeline_extract/<bundle>/MonoBehaviour/`
for the three target track types and emits per-clip detail with
authored `m_Start` / `m_Duration`:

- **Beyond FMV Track** (21 clips, 20 distinct `fmvId`s): each clip's
  `m_Asset` PPtr resolves to a sibling `BeyondFMVPlayableAsset` whose
  `fmvId` is the `cs_video_*` story key. Provides authored cutscene
  FMV timing inside a parent Timeline. Examples:
  `cs_video_dlg_e6m1_9 start=4.4 dur=14.68`, `cs_video_e6m3_2
  start=114.77 dur=130.5`, `cs_video_dlg_e2m6_14 start=119.45 dur=31.68`.
- **Subtitle Track** (3 instances, all empty): the track exists and
  auto-binds to `CinematicPanel/SubtitlePanel`, but every
  `m_Clips` array is empty in the export. Subtitle text lives on
  the Dialog Trunk Track or on FMV-prefab markers, not on this
  track. Recorded as a presence flag only.
- **Dialog Trunk Track** (8,824 clips across 8 folders): already
  fully covered by `timeline_recovery.py` ->
  `timeline_line_orders.json`. Re-summarized here for cross-validation.

Output:
`reports/playable_director/timeline_track_clips.{json,md}`.

Direct use: the FMV clip table is a strong cross-reference for FMV
ordering. Two FMV ids are gender-variant pairs sharing the same
timeline start (`f_cs_video_dlg_e0m2_5` + `m_cs_video_dlg_e0m2_5`
both at start=124.38), and four `cs_video_dlg_e9m4_19a/b/c` clips
share a parent Timeline with monotonic start times — authored play
order is preserved in the clip layout.

Subtitle Track is a confirmed dead end for line-level timing
extraction; do not pursue it further unless the runtime starts
populating its clips.

### 2026-05-16 FMV Clip Meta in Conv Payload

Wired the existing `timeline_track_clips` Beyond FMV evidence into
the WebUI conv payloads. A new precompute step writes
`reports/playable_director/fmv_clip_by_webui_key.json` keyed by
WebUI story key with the per-clip `fmvId`, `clipStart`,
`clipDuration`, `assetClipDuration`. The language bundle loads the
mapping and attaches `payload.fmvClips` on both the `dlg_*` and
`cutscene_*` write paths; the WebUI conv-meta line surfaces the
clip info as `fmv=<fmvId>@<start>s+<dur>s, ...`.

Coverage: 18 WebUI keys carry one or more FMV clips:

```text
dlg_e6m1_9, dlg_e2m6_14, dlg_e9m2_18, dlg_e10m1_1, dlg_e10m2_5,
dlg_e10m3_7a, dlg_e10m3_7b, dlg_e10m3_7c, dlg_e3m6_11,
dlg_sm2l5m1_10, dlg_e0m2_5 (gender-pair), dlg_e6m1_7 (gender-pair),
dlg_e9m4_19a, dlg_e9m4_19b, dlg_e9m4_19c, dlg_e9m4_19d,
cutscene_e6m2_2, cutscene_e6m3_2
```

No new scene-order edges. The visible value is per-conv FMV timing
in the WebUI meta line. This converts existing audit evidence into
visible UI without further decode work.

### 2026-05-16 Source-Graph Cross-Reference Audit (no gain)

Inspected `reports/source_graph/endfield_source_graph.sqlite` (611k
edges across 75 kinds) for unused ordering evidence. The
ordering-relevant kinds (`graph_fragment_targets_story` 62,
`option_anchor_after` 37, `option_enters_story` 2711,
`anchored_after_line` 2683, `references_story` 873) are already
consumed by the WebUI builder through `sceneGraphLinks` ->
`authoredDirect` / `authoredMenu` strong edges, or are leaf
data (audio path / file references / texture pathids). No unused
ordering source found. Verified on `a1m10` and `a1m3`: all
mission-internal dialog nodes are already strong.

### 2026-05-16 LevelScript Property Setter Opcode Candidates

Scanned the 60 bridgeFound property-flow triples to find which LS
opcode/kind carries the property key string. Results:

```text
code=0x0000 kind=0x00: 7 (likely padding / data segment, not a real opcode)
code=0x13a5 kind=0x00: 5  <-- candidate property setter
code=0x07fa kind=0x01: 3
code=0x084d kind=0x00: 2
code=0x04b8 kind=0x09: 2
code=0x0001 kind=0x00: 1
```

`0x13a5/0x00` appears in five property-setter contexts
(`fightFinished` in c16m1d5, `isSuccceeded` x3 in c13m1, `puzzle` in
e5m2). The records carry only the property-key string and no adjacent
story refs in their immediate +-3 record neighborhood, so this opcode
alone does not produce a promotable edge.

Promotion would need control-flow traversal: identify 0x13a5 records
as candidate property setters, follow each script's `nextId` chains
or surrounding play-* opcode records, and connect the setter to its
authored predecessor / successor story refs. That is deeper graph
analysis than this slice budget can deliver and remains queued.

Not landing as a WebUI rule. Recording the opcode candidate for the
next session.

### 2026-05-16 LevelScript Cross-File Order Weak Edge

New `levelscriptCrossFileOrder` weak edge kind in the WebUI builder.
For each LevelScript level the mission touches, the builder now pairs
*consecutive numeric LS files* (`<id>.json` followed by `<id+1>.json`)
and connects the last story key in file N to the first story key in
file N+1.

Motivation: e10m4's `dlg_e10m4_1` and `dlg_e10m4_2` were stuck unknown
because each lived alone in its `dung02_rdg002/24400020002.json` and
`/24400020003.json` LS file. The existing `levelscriptFileOrder` rule
only emits edges when a single LS file holds two or more story keys,
so singleton files never produced cross-mission ordering hints. The
new rule complements it.

Conservative gate: only pairs files whose numeric stem deltas are
exactly 1, so unrelated parallel-event files in the same level can't
be flattened into one chain by accident.

Measured impact on CN priority buckets (single rebuild):

```text
              before                after                delta
main          670 / 253 / 809      670 / 427 / 635      +0 / +174 / -174
event         71  / 6   / 54        71 / 10  / 50       +0 / +4   / -4
major         125 / 40  / 326      125 / 78  / 288      +0 / +38  / -38
character     277 / 102 / 382      277 / 187 / 297      +0 / +85  / -85
TOTAL         1143 / 401 / 1571    1143 / 702 / 1270    +0 / +301 / -301
```

Net: **+301 weak / -301 unknown** across priority buckets in one
pass. Strong rows are unchanged at 1143 (consistent with the
edge-kind classification: cross-file order is weak only).

Spot-check on e10m4: `dlg_e10m4_1` and `dlg_e10m4_2` are now weak
(promoted from unknown) via cross-file edges between
`dung02_rdg002/24400020002.json` -> `24400020003.json` and
`24400020001.json` -> `24400020002.json`. e10m4 overall moved from
`29/8/54` to `29/17/45`.

The rule is **conservative** by design (delta-1 stems only) and does
not produce any strong promotions. It is a discovery rule for the
unknown queue.

### 2026-05-16 +0x18 Interpretation Correction

The prior session's analysis named `+0x18` as a runtime `activeClipGate`
field whose writer needs disassembling. That framing is **wrong**.

Cross-checking the IL2CPP option type fields against the serialized
JSON form of `DialogOptionPlayableAsset.options[*]`:

```text
JSON field order: trunkId, dialogId, setGreyed, selectedFlag, ...
IL2CPP layout:    +0x10 trunkId (string ptr)
                  +0x18 dialogId (string ptr)
                  +0x20 setGreyed (int)
                  ...
```

So `cmp [rax+0x18], 0x0` inside `TryTriggerTrunkBindingOption` is
checking `if dialogId != null`. The memory note for the story page
already records this exact condition: the 20 live
`inferredOptionResponse` groups all have **blank `trunkId`/`dialogId`**
on their `DialogOptionPlayableAsset` rows
([memory/webui_recovery/story_page.md:218-220](memory/webui_recovery/story_page.md)).

Implications:

- The "20 inferredOptionResponse groups need IL2CPP +0x18 writer
  decoded" framing is incorrect. They're stuck because the source
  data does not author `dialogId`/`trunkId` for those option clips,
  combined with no Runtime Jump Track route and a `logicId` that
  resolves nowhere in the export.
- No disassembler will unblock them; the data just lacks the routing.
- The follow-up slice "Decode the +0x18 writer in `GameAssembly.dll`"
  in the 2026-05-16 session checkpoint is **retracted**.

What actually IS a runtime field worth decoding from disassembly:

- `+0x98 selectedOptionIndex` (on the manager-side option object that
  `_SelectIndexInTimeline` reads). This one is read but its writer
  is not in the existing 96-byte windows.
- `+0x200 selectedIndexStore` writer.

Neither of those gates the 20 unresolved groups; they would help
with skip/resume scenarios, not response routing.

### 2026-05-16 IL2CPP Option Runtime Field Analysis

Built an interpretation layer over the existing IL2CPP body-target
mapper output. New script:
[scripts/story_recovery/build_option_runtime_field_analysis.py](scripts/story_recovery/build_option_runtime_field_analysis.py).

It reads `reports/option_flow_body_targets_gameassembly.json` (already
produced by `tools/endfield-il2cpp/map_body_targets_to_gameassembly.py`)
and extracts every `[reg+offset]` memory access in the disassembly
window of the 14 catalog-target direct call edges, then annotates the
named offsets that the disassembly proves matter for option flow.

Confirmed runtime field semantics on the option object:

- `+0x18 activeClipGate` (5 uses across `TryTriggerTrunkBindingOption`
  and `_TryDoNext`): read as `cmp [rax+0x18], 0` before
  `SetDialogOption(this, optionData)`. Options with this offset zero
  are filtered out — this is the runtime gate that keeps the 20 live
  `inferredOptionResponse` candidate clips inactive in the WebUI
  builder, because their authored serialized fields all read 0.
- `+0x98 selectedOptionIndex` (3 uses in `_SelectIndexInTimeline`,
  `SkipToNextShowNode`): read as
  `mov ebx, [rax+0x98]; mov edx, ebx; call DialogChooseOption`. The
  optionIndex passed to `DialogChooseOption` is literally
  `selectedOption.+0x98`.
- `+0x200 selectedIndexStore` (1 use in `SelectIndex`): written as
  `mov [rax+0x200], ecx` (ecx <- `this.+0xa0`) before
  `ResetDialogOption()`. Persistent store of the selected option index
  for the active dialog timeline.
- `+0xa0 managerCurrentIndex` (1 use in `SelectIndex`): the
  `DialogTimelineManager`-side index source that feeds `+0x200`.
- `+0x28 playableOptionsList` (3 uses in `GenPlayable`,
  `TryTriggerTrunkBindingOption`): the serialized `options` list on
  the playable asset.

18 distinct offsets appear in the 14 direct-call windows; 5 have
named semantics, 13 remain `unknown` for now.

Output: `reports/option_flow_active_clip_field_analysis.{json,md}`.

Next decoding target: identify the PRODUCER/INITIALIZER of `+0x18` on
the runtime option object. `TryTriggerTrunkBindingOption` reads it
but does not write it; the likely writers are
`DialogTimelineManager.SetDialogOption` or the
`DialogOptionPlayableAsset` post-bind path. Once the writer is
identified and the conditions under which it sets non-zero are known,
the WebUI builder can promote authored +0x18 evidence into a real
option-response edge. This is the key unblocker for the 20 live
`inferredOptionResponse` groups.

### 2026-05-16 Option Response Audio / Timeline Evidence

Ran a per-group AudioDialog + Timeline + speaker evidence audit on the
20 live `inferredOptionResponse` groups across 15 scenes. New audit:
[scripts/story_recovery/build_option_response_audio_evidence.py](scripts/story_recovery/build_option_response_audio_evidence.py)
emitting `reports/option_response_audio_evidence_CN.{json,md}`.

For each candidate line the audit captures:

- `DialogTextTable` speaker id and display name
- `AudioDialog.path`, `speakerChannel`, integer dialog key (audio
  recording session order), `wavDuration`
- `DialogTrunkPlayableAsset` Timeline name + `start` + `duration`
- whether all candidates fall after the anchor on the same Timeline
- whether the candidate set is monotonic by Timeline start time
- whether AudioDialog keys are monotonic across the candidate set
- whether the speakers are consistent (single responder) across
  candidates, and whether the anchor's speaker differs from them

Results (CN, 2026-05-16):

```text
groups audited:                     20
monotonic by Timeline start:        19 / 20
monotonic by AudioDialog key:       15 / 20
candidates all after anchor:        19 / 20  (matches Timeline monotonicity)
consistent candidate speaker:       13 / 20
anchor speaker different from cand: 13 / 20  (matches)
candidates share anchor's Timeline: 19 / 20
```

The single non-monotonic group is `misc_dlg_e5m3_0d5` g2 which has
no Timeline data — a table-only scene.

The 7 multi-speaker groups (`dlg_e1m10_7 g5`, `dlg_e4m1_4 g3`,
`dlg_e6m1_10 g4`, `dlg_e6m3_14 g2`, `dlg_e6m4_14 g2/g3`,
`misc_dlg_e5m3_0d5 g2`) carry an additional signal: each option may
trigger a different NPC to respond, so the speaker pattern itself
maps to the option index. Example: `dlg_e6m1_10 g4` candidates are
`_016 (pelica)` and `_003 (zhuangfy)` — two-option group where the
two response speakers are distinct characters.

Classification:

- Necessary signal: candidates form a coherent authored cohort
  (same Timeline, after the anchor, monotonic start times).
- **Not sufficient for promotion**: candidate monotonicity is
  consistent with the option-index mapping but does not bind a
  specific candidate to a specific option index. The
  `DialogOptionPlayableAsset +0x18` runtime field would do that
  binding; until it is decoded, this audit stays diagnostic.

This audit is the right evidence packet to attach to each of the 20
groups when reviewing future promotion rules. Do not land an
automatic Timeline-monotonic option-response edge yet — the negative
control in `build_option_route_evidence_controls.py` still demands
authored Runtime Jump skip/reverse range evidence for every option,
which these groups lack.

### 2026-05-16 LevelScript Property-Flow Audit

Audited the LevelScript-property-condition / setter bridge described in
the candidate metadata queue. New audit script:
[scripts/story_recovery/build_levelscript_property_flow_audit.py](scripts/story_recovery/build_levelscript_property_flow_audit.py).

The audit:

1. Walks every `MissionRuntimeAsset/*.json`, extracts each
   `CheckLevelScriptPropertyBool` / `CheckLevelScriptPropertyInt`
   triple `(mapId, scriptId, key)`, the checker mission/quest, and any
   story refs on that quest.
2. Locates the target LevelScript file at
   `LevelScriptData/<mapId>/<scriptId>.json`.
3. Tests whether the property key appears as a Unity-style length-
   prefixed UTF-8 string (4-byte LE length followed by ASCII bytes) in
   the LS binary.
4. Decodes the LS file via `_load_levelscript_binding_data` and finds
   records that carry both the property key AND adjacent story refs.

Results (CN export, 2026-05-16):

```text
missions with property checks: 64
property-typed conditions:     193
distinct (mapId, scriptId, key) triples: 164
bridge status:                 bridgeFound=60, bridgeSubstringOnly=3, bridgeMissing=101
records-with-neighbor-story-refs: 18 of 60 bridgeFound rows
```

Notable bridgeFound triples:

- `map01_lv006/3500150002 key=dlg_sm1l6m1_4_Done` —
  property name literally encodes a dialog completion flag. The setter
  must be the script record that finishes `dlg_sm1l6m1_4`.
- `map01_lv006/3500150004 key=radio_sm1l6m1_3_Done`,
  `radio_sm1l6m1_4_Done` — same pattern for radios.
- `map01_lv001/2100130002 key=comm_fixed` (e1m3) — descriptive event.
- `indie_dg002/8700040000 key=battle_field_clear` (e0m0) — matches the
  known strong sequence `radio_e0m0_8d4 -> cutscene_e0m0_New14 ...`.
- `map01_lv001/2100370011 key=isFinished` (c13m3) — record `0/0` at
  delta=0 carries `dlg_c13m3_7`.

Classification:

- `isOrderingSource = True`: the bridge is real and per-mission.
- `isPromotable = False`: the audit identifies WHICH scripts own the
  property but does not yet decode the SETTER opcode/kind. Promotion
  to strong scene-order edges in the WebUI builder needs that decoder
  pass.

bridgeMissing rows are mostly runtime-system property names
(`isFinished`, `isSucceeded`, `puzzleSolved`, `int_sum`,
`Check_HasPower`, etc.) that the LS script exposes implicitly without
storing the name as a literal string.

Output: `reports/mission_order/levelscript_property_flow_CN.{json,md}`.

This is a foundation for follow-up scene-order promotion. Do not
promote rows out of this audit into the WebUI yet.

### 2026-05-15 AudioDialogCustomEventTable Probe

Audited `Table/AudioDialogCustomEventTable.json` against
[scripts/story_recovery/build_audio_dialog_custom_events.py](scripts/story_recovery/build_audio_dialog_custom_events.py)
to test the tier-A hypothesis "dialog enter/exit event IDs bridge specific
`dlg_*` files to LevelScript audio records".

The table holds **41 dialogs / 73 distinct event IDs** (35 unique
signatures, 2 shared groupings). Per-mission distribution: `e8m1=10`,
`e8m3=8`, `e10m4=5`, `e8m2=5`, `e8m5=5`, `e8m4=3`, `e10m2=2`, `e9m2=1` —
clustered on the e8 chapter and a few e10 entries.

Probes that rejected this as an ordering source:

- The 73 integer event IDs do not appear (as text or as little-endian
  int32 bytes) in any other `Table/*.json`, in any LevelScript binary
  payload under `LevelScriptData/`, or in any recovered AnimeStudio
  `json_by_type/MonoBehaviour/*` dialog/timeline JSON.
- Wwise-style hashes (`FNV-1`, `FNV-1A`, `CRC32`, `Murmur3` seeds 0/1/42,
  `djb2`, `sdbm`) of every `au_*` token extracted from
  `global-metadata.dat` (167 candidates, including the only two
  dialog-relevant strings `au_global_contr_narrat_dialog_in` and
  `au_global_contr_narrat_dialog_out`) produce zero matches against the
  73 target IDs. The hash function is therefore not any of those — it
  is either a Wwise-internal variant baked into `GameAssembly.dll`, or
  the event names live in compiled-only string pools that
  `metadata.dat` does not expose.

What remains usable from this table:

- A **per-dialog presence flag** identifying which dialogs carry custom
  Wwise audio enter/exit hooks (mostly e8 chapter cinematic dialogs).
- A **shared-signature group**: 6 dialogs
  (`dlg_e10m2_1/2`, `dlg_e10m4_15/4`, `dlg_sm2l5m1_4/6`) share
  `preEnter=-1326707401`, `preExit=-1281540150`. This is a likely
  "generic dialog audio profile" group — useful as a co-authored cohort
  marker but not as a chronology edge.
- A second pair shared signature for `dlg_e8m5_2` + `dlg_e8m5_5`
  including a non-zero `preloadEvents=1936686820`.

Output: `reports/mission_order/audio_dialog_custom_events_CN.{json,md}`.

Reject this table as a scene-ordering source. Treat as a validation /
metadata tag only. Next promising direction for option response remains
the IL2CPP-side decoding of `DialogChooseOption` and the `+0x18`
runtime active-clip field on `DialogOptionPlayableAsset`.

### 2026-05-16 Session Checkpoint

Summary of evidence-source audits added this pass (after the
2026-05-15 batch of WebUI strong-edge promotions). Each is in
`scripts/story_recovery/` and emits to `reports/`. None of them
modify WebUI builder output yet; they are foundations for follow-up
promotion slices once the runtime fields they hint at are decoded.

| audit | source | classification | output |
| --- | --- | --- | --- |
| `build_audio_dialog_custom_events.py` | `AudioDialogCustomEventTable.json` | Tag only — not an ordering source | `reports/mission_order/audio_dialog_custom_events_CN.{json,md}` |
| `build_levelscript_property_flow_audit.py` | `MissionRuntimeAsset/*` `CheckLevelScriptProperty*` + `LevelScriptData/<mapId>/<scriptId>.json` binary key probe | Ordering source, not yet promotable | `reports/mission_order/levelscript_property_flow_CN.{json,md}` |
| `build_option_response_audio_evidence.py` | `AudioDialog.json` + Timeline `start/duration` + `DialogTextTable` speaker | Diagnostic for the 20 live `inferredOptionResponse` groups | `reports/option_response_audio_evidence_CN.{json,md}` |
| `build_option_runtime_field_analysis.py` | `option_flow_body_targets_gameassembly.json` disassembly windows | Names runtime field offsets `+0x18` / `+0x98` / `+0xa0` / `+0x200` | `reports/option_flow_active_clip_field_analysis.{json,md}` |
| `build_timeline_track_clip_consumer.py` | Timeline `MonoBehaviour` `Beyond FMV Track` / `Subtitle Track` / `Dialog Trunk Track` JSONs | FMV-clip evidence (21 clips / 20 ids); Subtitle dead-end confirmed | `reports/playable_director/timeline_track_clips.{json,md}` |

Key new findings this session:

1. **`+0x18 activeClipGate`** is the runtime field on the option
   object that `TryTriggerTrunkBindingOption` checks before calling
   `SetDialogOption`. Options with `[rax+0x18] == 0` get filtered
   out. All 20 live `inferredOptionResponse` candidate clips read 0
   in their authored serialized fields, which is why they stay
   inferred today.
2. **`+0x98 selectedOptionIndex`** is the runtime field that
   `_SelectIndexInTimeline` reads and passes as `optionIndex` into
   `DialogChooseOption`. The selected option binds to a clip via
   this offset.
3. **Identifying the writer of `+0x18`** is the single next decoding
   target that would unblock all 20 inferred groups. The writer is
   likely in `DialogTimelineManager.SetDialogOption` or
   `DialogOptionPlayableAsset` post-bind initialization. Once
   identified, the WebUI builder can promote authored `+0x18`
   evidence into a real option-response edge.
4. **LevelScript property flow** has 60 confirmed bridges between
   MRA checker conditions and owning LS scripts. Setters are not yet
   decoded by opcode; this is the next scene-order slice that could
   land strong edges once the setter opcode is identified.
5. **Beyond FMV Track** provides authored cutscene timing through
   `BeyondFMVPlayableAsset.fmvId`. 20 distinct `cs_video_*` story
   keys with clip start/duration. Gender variants
   (`f_cs_video_*` + `m_cs_video_*`) share Timeline start; sequential
   variant suffixes (`a/b/c/d`) chain monotonically.
6. **`AudioDialogCustomEventTable`** is confirmed not a scene-order
   source; reject this candidate.
7. **`AudioDialog` + Timeline** monotonicity holds for 19 of 20
   live inferred-response groups — necessary but not sufficient for
   promotion. The 7 multi-speaker groups carry an additional
   per-option NPC-response signal worth surfacing in the WebUI.

The follow-up slice queue, in priority order:

1. **Decode the `+0x18` writer in `GameAssembly.dll`.** Use a real
   disassembler (Cpp2IL, Ghidra, or a focused x86_64 decoder) to
   trace `DialogTimelineManager.SetDialogOption` and
   `DialogOptionPlayableAsset` post-bind to find where `+0x18` gets
   set to non-zero. Once known, promote authored evidence into the
   WebUI builder.
2. **Setter-opcode identification for LevelScript property flow.**
   Decode which LS record opcode/kind writes property values. With
   that, the 60 bridgeFound triples can promote scene-order edges.
3. **Per-option NPC response speaker mapping.** For the 7
   multi-speaker `inferredOptionResponse` groups, the responder
   speaker per option might be authored in the
   `DialogOptionTable.options[*].actorId` field. Worth checking.
4. **Connect FMV clip evidence to the WebUI builder.** The 20
   `cs_video_*` clips with start/duration are already enough to
   add an `fmvClipOrder` weak edge for the parent cutscene.

### 2026-05-16 e10m4 Deep Dive

Audited `reports/mission_order/e10m4_evidence_audit.md` as the
highest-unknown priority mission. Current regenerated status is
`strong=29`, `weak=8`, `unknown=44` across 81 entries.

No new strong/weak promotions landed from this pass. The useful finding was a
false-positive diagnostic source in the audit itself: raw LevelData byte scans
were matching short story ids inside longer ids. Examples:

- `dlg_e10m4_1` was counted inside `dlg_e10m4_19` and `dlg_e10m4_18`.
- `dlg_e10m4_2` was counted inside `dlg_e10m4_22` and `dlg_e10m4_20`.
- `radio_e10m4_2` was counted inside repeated `radio_e10m4_25` payloads.

Fixed `scripts/story_recovery/build_mission_order_evidence_audit.py` so
LevelData byte hits require story-id boundaries. After regeneration,
`e10m4` LevelData adjacent story pairs dropped from 6 to 2:

- `dlg_e10m4_19 -> dlg_e10m4_18` in
  `LevelData/indie_dg005/indie_dg005_lv_data_sub_e10m1.json`
- `radio_e10m4_25 -> radio_e10m4_61` in
  `LevelData/dung02_rdg002/dung02_rdg002_lv_data.json`

Both remaining pairs are exact-id diagnostics only. They lack a decoded quest
owner or trigger-control edge, so they should stay weak context rather than
promotion evidence.

### 2026-05-16 Priority Audit Sweep

Regenerated the other top-unknown priority audits after the LevelData
story-id boundary fix:

| mission | strong | weak | unknown | LevelData adjacent pairs | weak/unknown with no MR/proxy/variant/LS |
| --- | ---: | ---: | ---: | ---: | ---: |
| `e10m4` | 29 | 8 | 44 | 2 | 31 |
| `c16m4` | 22 | 5 | 31 | 0 | 19 |
| `c6m1` | 13 | 3 | 42 | 0 | 29 |
| `e1m1` | 17 | 12 | 19 | 0 | 8 |
| `c28m3` | 12 | 16 | 31 | 0 | 13 |

`c16m4` deep dive did not reveal a safe new promotion. Its useful authored
evidence is already represented by:

- variant MissionRuntime scene-graph evidence from `c16m4d5` for 10 entries
- NPC proxy dialog ownership for `dlg_c16m4_1`
- radio-continuation edges for 7 radios
- weak LevelScript file-order edges for the `dlg_c16m4_8` /
  `misc_dlg_c16m4_7d7` / `dlg_c16m4_7` cluster

The remaining `levelscriptChain` edges are placement/ownership anchors from
script/control nodes to story keys or terminals. They should not be promoted as
inter-story chronology by themselves. The consecutive `dung01_rdg003`
LevelScript script ids around `misc_dlg_c16m4_7d5`, `7d8`, `7d7`, and
`dlg_c16m4_7` are still filename/script-id proximity only unless a decoded
trigger owner or MissionRuntime objective maps those script ids into a real
quest edge.

## Avoid

- Do not sort scene files only by filename suffix.
- Do not use extracted filesystem order or VFS chunk order as narrative order.
- Do not flatten quest branches unless an original source edge proves a merge or
  predecessor relation.
- Do not use generated WebUI rank/order as evidence for this recovery pass.
- Do not promote LevelScript file-offset order to strong evidence until record
  types, trigger ownership, or UID/control-flow relationships are decoded.
