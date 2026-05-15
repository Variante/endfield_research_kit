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
   - weak: LevelScript file-offset order.
   - unknown: fallback/numeric order only. Keep these after strong/weak ordered
     files in the sidebar, sorted by the numeric index recovered from the file
     key tail (`1`, `1d5`, `New14`, etc.).

## Avoid

- Do not sort scene files only by filename suffix.
- Do not use extracted filesystem order or VFS chunk order as narrative order.
- Do not flatten quest branches unless an original source edge proves a merge or
  predecessor relation.
- Do not use generated WebUI rank/order as evidence for this recovery pass.
- Do not promote LevelScript file-offset order to strong evidence until record
  types, trigger ownership, or UID/control-flow relationships are decoded.
