# Story Runtime Extraction Audit

Date: 2026-05-11

## Summary

Yes: the repo can use the IL2CPP tooling and the already-exported game data
to recover more story-adjacent information. For this game, `Il2CppDumper` is
not the best first step for normal WebUI enrichment because HGP relocates
`MetadataRegistration`, but `global-metadata.dat` is still very useful as an
offline runtime-vocabulary source. The actual story payload is mostly in the
structured tables, mission/runtime JSON, Lua UI scripts, and recovered
AnimeStudio/Unity asset map.

## Verified This Pass

- `tools/endfield-il2cpp/verify_dialog_class_hierarchy.py` passes against:
  `D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat`
  - metadata size: 57,526,184 bytes
  - version: 29
  - dialog runtime hierarchy is unchanged from the May 2026 baseline.
- `tools/endfield-il2cpp/catalog_dialog_classes.py` now also buckets
  Cutscene, SNS, EnvTalk, Interact, and Reading runtime vocabulary.
- Full runtime vocabulary report:
  `reports/story_runtime_catalog_2026-05-11.json`

Useful catalog counts from this pass:

- Dialog: 327 identifiers
- Trunk: 78
- Timeline: 73
- Tree: 56
- Option: 26
- Cutscene: 322
- Mission: 109
- Scene: 142
- Radio: 26
- SNS: 74
- EnvTalk/AIBark/Responsive: 278
- LevelScript: 657
- Interact: 2,065
- Reading/PRTS/RemoteComm: 286
- Strict specialized document/memo/letter loader canary: 0

The strict `DocOrMemo` canary staying at zero supports the existing
conclusion: document-style dialog content is not handled by a separate
runtime UI loader.

## Existing Extracted Payload Sources

High-signal structured tables already available under
`export_full/structured/StreamingAssets/Table/`:

- `DialogTextTable.json`: 16,659 dialog rows
- `DialogOptionTable.json`: 4,102 option-text/icon rows
- `DialogSummaryTable.json`: 954 summary rows
- `DialogSummaryMapTable.json`: 888 dialog-to-summary links
- `RadioTable.json`: 2,192 radio conversations
- `SNSDialogTable.json`: 272 SNS conversations
- `SNSDialogOptionTable.json`: 1,227 SNS option rows
- `EnvTalkTable.json`: 1,630 ambient-talk groups
- `ResponsiveDialog.json`: 6 responsive dialog groups
- `ReadingPopUpTable.json`: 546 reading popup entries
- `PrtsDocument.json`: 61 document entries
- `PrtsNote.json`: 27 note entries
- `PrtsRecord.json`: 316 record entries

Mission and level-script JSON already contain direct story references:

- dialog references: 480 refs across 168 files
- radio references: 339 refs across 136 files
- SNS references: 98 refs across 90 files
- direct cutscene references: 3 refs across 3 mission files

Current CN WebUI story index already includes:

- total entries: 8,525
- dialog: 2,343
- radio: 2,192
- env talk: 1,555
- wiki/reference-style story content: 1,071
- PRTS: 399
- SNS: 272
- cutscene: 214
- blackbox/timeline: 143
- remote comm: 28
- responsive: 27

## Remaining Recovery Issues

After the 2026-05-11 CN rebuild, the WebUI recovery filter no longer treats
partial/fallback line ordering as a missing line-order block. It does treat
Timeline-inferred option replies (`inferredOptionResponse`, shown in the UI as
`推测回应`) as recovery issues, because the option metadata does not name an
explicit target trunk line. The strict recovery report has:

- Flagged scenes: 93
- Missing line-order blocks: 0
- Partial authored line order: 11 scenes
- Fallback line order: 3 scenes
- Scenes with uncovered lines: 14
- Inferred option placement: 20 scenes
- Inferred option responses: 60 scenes
- Duplicate timestamps: 0 scenes

Runtime Jump Track option-route recovery, added later on 2026-05-11, explains
some option replies that were previously only inferred from adjacent Timeline
lines. The Timeline parser now treats forward `Runtime Jump Track` clips as
per-option skip windows: for a selected `optionIndex`, lines inside that skip
window are skipped and the remaining lines before the next option group become
that option's branch path.

Current CN gains from this pass:

- `timeline_line_orders.json`: 25 Timeline entries with route evidence,
  containing 57 option routes.
- WebUI CN conv output: 14 scenes and 16 option groups now have
  `timelineRouteBranches` evidence.
- Those route-backed groups account for 91 branch-line assignments that no
  longer need `inferredFollowingLines` risk tags.
- Strict recovery report improvement: flagged scenes dropped from 98 to 93,
  and inferred option-response scenes dropped from 65 to 60.

Example: `dlg_e1m1_5` group 1 is no longer an inferred option response.
Runtime Jump Track skip windows recover:

- `option_dlg_e1m1_5_1_001` -> `dlg_e1m1_5_002`, `dlg_e1m1_5_003`
- `option_dlg_e1m1_5_1_002` -> `dlg_e1m1_5_004`, `dlg_e1m1_5_005`,
  `dlg_e1m1_5_006`
- both branches continue to `option_dlg_e1m1_5_2_001`

`dlg_e1m1_5` group 3 remains inferred because the current Timeline/DLL dump
does not expose matching runtime-jump route evidence for that later option
group.

`dlg_e0m2_1` is now resolved by the `dialogTreeCinematicTimeline` stitch:
`dlgtl_e0m2_1_sub_1` inserts line 005 after trunk line 004, and
`dlgtl_e0m2_1_sub_2` inserts lines 009-010 after trunk line 008. Duplicate
timestamp diagnostics are scoped per Timeline segment, so separate sub-timelines
can both start at 0.0 seconds without creating a false recovery issue.

The broader inferred-option-anchor diagnostic remains useful context for option
placement work: 98 scenes and 183 inferred groups, mostly `lineNumber`
placements. Source/video side queues also remain: 18 source-link keys are
referenced by extracted source data but missing from WebUI entries, and 33
narrative video refs are unresolved.

## Runtime/Lua Hooks Worth Mining

Lua confirms useful UI/runtime semantics without requiring full C#
decompilation:

- `PhaseCinematic.lua` starts cutscenes through `ON_PLAY_CUTSCENE` and
  forwards `ON_LOAD_NEW_CUTSCENE`.
- `CinematicCtrl.lua` exposes `cutsceneName`, subtitle binding, left-subtitle
  binding, masks, skip checks, and `loadedPanelFmv` panel video nodes.
- `PhaseDialogTimeline.lua` and `DialogTimelineCtrl.lua` expose timeline
  dialog options, subtitles, FMV nodes, skip summaries, logs, auto mode, and
  trunk start/stop events.
- `DialogCtrlBase.lua` shows option runtime data fields surfaced to UI:
  `optionId`, option text, `iconType`, option icon, optional color, and
  greyed/selected state.
- `DialogCtrl.lua` shows direct dialog trunk UI fields: background sprites,
  center-image/full-bg actions, radio styling, left subtitles, skip summaries,
  and open/close UI actions such as `ReadingPopUp`.

## Recommended Extraction Work

1. Add a mission/source-link extractor for `MissionRuntimeAsset`,
   `LevelScriptData`, and `LevelScriptTemplateData`. **Implemented
   2026-05-11** as `scripts/webui/build_story_source_links.py`.
   - Output: `export_full/recovered/story_source_links.json`, plus
     `reports/story_source_links.json` / `.md`.
   - `build_story.py` now stamps matching conv JSON files with
     `sourceLinks`, adds compact `src` evidence to index entries, and writes
     per-language coverage/orphan reports such as
     `reports/story_source_links_CN.json`.
   - Value: makes dialog/radio/SNS/cutscene ordering evidence more explicit
     in the WebUI.

2. Add a cutscene/detail video miner. **Partially implemented 2026-05-11**
   in `scripts/webui/build_story.py`.
   - Inputs: exported narrative videos under
     `Data/Video/PC/Narrative/Cutscene` and `RemoteComm`, plus current WebUI
     story keys.
   - Output: `narrativeVideos` on matching dialog/cutscene/remotecomm conv
     JSON, compact `vid` summaries and `narrativeVideo` tags in the story
     index, WebUI video previews, and
     `reports/narrative_videos_CN.json` / `.md`.
   - Current CN result: 235 narrative video files scanned, 202 refs attached
     to 42 story keys (20 cutscenes, 17 dialogs, 5 remote comms), with 33
     unresolved refs left for future source-graph work.
   - Remaining work: mine additional AnimeStudio/Timeline fields beyond the
     existing actor/audio/effect groups and video refs, especially subtitle
     binding details, panel FMV metadata, and skip/transition state.

3. Enrich dialog option recovery.
   - Existing `DialogOptionTable` gives text/icon rows, and Lua shows runtime
     option data fields.
   - IL2CPP metadata exposes `DialogTimelineOptionData`, `DialogOptionBehaviour`,
     `centerPanelId`, `popUpPanelId`, and `ApplyPanelId`.
   - **Partially implemented 2026-05-11** with Runtime Jump Track route
     recovery in `scripts/recover_timeline_line_orders.py` and
     `scripts/webui/build_story.py`.
   - Remaining target: find the concrete asset/table or runtime state that
     stores explicit option target indices for groups that do not have
     Runtime Jump Track skip-window evidence.

4. Bring Reading/PRTS/RemoteComm into the same source graph.
   - Tables already exist for reading popups, PRTS documents/notes/records,
     rich content, and remote comm.
   - Useful next step: cross-link `Dialog OpenUI` actions and mission actions
     to these entries.

5. Keep live IL2CPP dumping as a last-resort path.
   - Use only when method bodies are needed, not for routine data extraction.
   - Requires the game running and elevated tooling (`pe-sieve`, `procdump`,
     reflection dump, then `Il2CppDumper` manual addresses).
   - Current offline metadata and structured exports are enough for the next
     story-recovery improvements above.
