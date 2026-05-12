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

Current CN gains from this pass, after the 2026-05-12 directional Runtime Jump
extension:

- `timeline_line_orders.json`: 27 Timeline entries with route evidence,
  containing 61 option routes.
- WebUI CN conv output: 16 scenes and 18 option groups now have
  `timelineRouteBranches` evidence.
- Those route-backed groups account for 100 branch-line assignments that no
  longer need `inferredFollowingLines` risk tags.
- Strict recovery report improvement: flagged scenes dropped from 98 to 92,
  and inferred option-response scenes dropped from 65 to 59.

On 2026-05-12 `tools/endfield_source_graph.py` was updated to ingest the raw
Timeline recovery file directly. This does not change WebUI conv output by
itself, but it improves recovery investigation quality: source graph `story`
and `query` commands can now show raw Timeline line clip order, option clip
anchors, Runtime Jump route path lines, skipped lines, continuation options,
runtime jump clip nodes, and the extracted JSON files behind each clip.
Use this to audit examples before promoting another automatic WebUI rule.
The graph also ingests WebUI recovery warnings, so unresolved queues can be
listed with nearby evidence:

```bat
python tools\endfield_source_graph.py issues --code inferredOptionResponse --limit 20
```

That command is the fastest next-entry point for separating cases with only
Timeline clip placement from cases that have stronger route/skip evidence.

After widening `DialogOptionPlayableAsset` extraction, a quick graph aggregate
over `inferredOptionResponse` warnings found:

- `63` warning records have raw `timeline_option_clip` evidence.
- `19` warning records also have `timeline_option_anchor_line` evidence.
- `0` warning records have `has_timeline_route`,
  `timeline_route_skips_line`, or `timeline_route_runtime_jump` evidence.

So the current unresolved option-response queue is not secretly backed by
Runtime Jump routes. The next likely recovery source is deeper interpretation
of option clip fields (`logicId`, finish-number fields, condition references,
or linked dialog tree/cinematic state), not looser skip-window promotion.

`scripts/webui/build_option_playable_semantics_audit.py` was added as the
follow-up audit for that queue:

```bat
python scripts\webui\build_option_playable_semantics_audit.py --language CN
python scripts\webui\build_option_playable_semantics_audit.py --language CN --only-interesting
python scripts\webui\build_option_playable_semantics_audit.py --language CN --story dlg_c17m1_5 --group 3
```

Current CN result:

- `107` remaining inferred response groups audited.
- `0` decoded option rows expose explicit `trunkId` or `dialogId` target
  fields.
- `targetFinishNum` only appears as default-like `-1` or `0`, with
  `changeFinishNum=0`, so it is not branch-target evidence yet.
- `conditionRid` is `-2` in all decoded rows.
- `77` groups have nonzero `logicId` values and are the only currently
  interesting semantic queue. Across those groups, `157` best option rows have
  nonzero `logicId` values.
- `30` groups have only decoded default fields.
- `0` groups have Timeline clip placement only after `misc_dlg_*` aliases are
  resolved to the underlying `dlg_*` Timeline entries.
- `46` of the `77` `logicId` groups use contiguous nonzero values, which makes
  `logicId` look more like option-state numbering than a target line id.
- Only `2` nonzero best-row `logicId` values equal the candidate line suffix.
- `9` same-story `logicId` values repeat with different candidate lines
  (`dlg_e1m10_5`, `dlg_e6m1_10`, `dlg_e6m1_12`, `dlg_e6m3_10`, and
  `dlg_f1m9d4_1`), which is strong negative evidence against treating
  `logicId` as a direct branch target.

Recovery gain: this pass does not promote more line order automatically, but it
removes two tempting false leads (`trunkId`/`dialogId` target fields and
finish-number fields). It also shows that `logicId` is probably not a direct
line target. The next high-value search is where `logicId` is consumed as
option state, completion, or UI gating, and whether that state can explain
repeat option prompts rather than branch entry lines.

`scripts/webui/build_option_logic_id_audit.py` was then added to scan those
`logicId` values against non-Timeline game-data sources:

```bat
python scripts\webui\build_option_logic_id_audit.py --language CN
python scripts\webui\build_option_logic_id_audit.py --language CN --story dlg_c17m1_5 --group 3
python scripts\webui\build_option_logic_id_audit.py --language CN --story dlg_c28m3_23 --group 1
```

Current CN result:

- `77` logic-bearing inferred response groups.
- `157` logic-bearing option rows.
- `117` unique nonzero option `logicId` values.
- `1,464` JSON files parsed from structured tables, `MissionRuntimeAsset`,
  `LevelScriptData`, `LevelScriptTemplateData`, and gameplay config.
- `0` same-mission exact matches in `MissionRuntimeAsset`, `LevelScriptData`,
  or `LevelScriptTemplateData`.
- `7` exact external matches total, all weak table/config matches:
  `logicId` `2`/`3` in `ScriptTaskExtraInfoTable` tracking entities and
  `31`/`147` in `MapMarkInsTable` camp map marks.
- Dialog Lua has `0` `logicId` consumer hits. It exposes option UI fields such
  as `optionId`, text/icon data, and `setGreyed`, but not the Timeline option
  `logicId`.

Recovery gain: the `logicId` branch-target hypothesis is now very unlikely for
the unresolved option-response queue. Future recovery work should prioritize
new source families that can expose authored branch links directly: dialog tree
asset extraction, PlayableDirector track binding semantics, or runtime method
body recovery for option selection flow.

`scripts/webui/build_dialog_tree_option_route_audit.py` was added to answer
the next branch-source question: do remaining inferred option responses already
have authored DialogTree route evidence that `build_story.py` failed to
promote?

```bat
python scripts\webui\build_dialog_tree_option_route_audit.py --language CN
python scripts\webui\build_dialog_tree_option_route_audit.py --language CN --story dlg_c17m1_5 --group 3
python scripts\webui\build_dialog_tree_option_route_audit.py --language CN --story dlg_e3m6_11 --group 4
```

Current CN result:

- `107` remaining inferred response groups audited.
- `0` groups have clean per-option authored DialogTree routes to promote.
- `98` groups are `cinematicTreeTimelineOnly`: the DialogTree source exists,
  but it is a cinematic wrapper that launches a `dlgtl_*` Timeline; option
  route information must come from Timeline/runtime selection flow.
- `6` groups have no matching DialogTree source (`sourceMissing`), currently
  all in `misc_dlg_*` scenes.
- `1` group (`dlg_e2m5_3` group 1) has tree files but no decoded option route
  signal, so it is the only current DialogTree-decoder follow-up.
- `2` groups (`dlg_e3m6_11` group 4 and `dlg_e6m2_7` group 1) have authored
  shared-route evidence. Both options route into the same authored path, so
  they should not be treated as confirmed per-option branches.

Recovery gain: this closes the obvious AnimeStudio DialogTree promotion path
for the unresolved queue. The biggest remaining quality lever is deeper
Timeline/runtime option-target decoding, not broader DialogTree inference.

AnimeStudio CLI was also patched so future MonoBehaviour JSON exports include
resolved MonoScript metadata under `$animestudio` (`scriptFullName`,
`scriptAssemblyName`, and script PPtr ids when resolvable). This is an export
quality improvement for future audits: it makes Timeline assets easier to map
back to runtime classes, but it does not change current WebUI recovery until
the local game data is re-exported.

`scripts/webui/build_timeline_option_flow_audit.py` was then added for the
remaining Timeline-only option response queue:

```bat
python scripts\webui\build_timeline_option_flow_audit.py --language CN
python scripts\webui\build_timeline_option_flow_audit.py --language CN --story dlg_c28m3_10 --group 1
```

Current CN result:

- `107` remaining inferred response groups audited.
- `106` groups have adjacent candidate response clips whose raw trunk
  `optionIndex` is only `0`; these are default clip values, not route evidence.
- `0` groups remain Timeline-layout unresolved after the audit was patched to
  resolve `misc_dlg_*` WebUI story keys to their underlying `dlg_*` Timeline
  entries.
- `1` group has a promotable raw trunk clip mapping:
  `dlg_c28m3_10` group 1. The Timeline order is `_025`, then `_023`, but the
  candidate clips carry raw `clipOptionIndex` values `2`, then `1`, matching
  option indices `1` and `2` after reordering.

Recovery gain: `scripts/recover_timeline_line_orders.py` now preserves line
clip `clipOptionIndex`, and `scripts/webui/build_story.py` uses it only when
the candidate line indices are complete, distinct, and exactly match the
group's option indices. After the CN rebuild, `dlg_c28m3_10` group 1 maps:

- `option_dlg_c28m3_10_1_001` -> `dlg_c28m3_10_023`
- `option_dlg_c28m3_10_1_002` -> `dlg_c28m3_10_025`

The same audit is also negative evidence: most remaining inferred option
responses do not expose useful per-option target data through raw trunk clip
`optionIndex`, so future work should focus on PlayableDirector binding
semantics or runtime option-selection method bodies.

The option-playable semantics audit now uses the same `misc_dlg_*` to `dlg_*`
Timeline aliasing. That changes the decoded-field totals to `77`
`logicIdOnly` groups and `30` `defaultOptionFieldsOnly` groups; explicit
target fields remain at `0`. The source graph was refreshed with this rebuilt
WebUI data, and option branch-risk edges now preserve `candidateMapping` plus
`candidateLineClipOptionIndex` evidence, so `dlg_c28m3_10` graph queries show
why option `_001` maps to line `_023` and option `_002` maps to `_025`.

Example: `dlg_e1m1_5` group 1 is no longer an inferred option response.
Runtime Jump Track skip windows recover:

- `option_dlg_e1m1_5_1_001` -> `dlg_e1m1_5_002`, `dlg_e1m1_5_003`
- `option_dlg_e1m1_5_1_002` -> `dlg_e1m1_5_004`, `dlg_e1m1_5_005`,
  `dlg_e1m1_5_006`
- both branches continue to `option_dlg_e1m1_5_2_001`

`dlg_e1m1_5` group 3 remains inferred because the current Timeline/DLL dump
does not expose matching runtime-jump route evidence for that later option
group.

A second, narrower Runtime Jump rule was added for one shape exposed by
`reports/runtime_jump_option_route_audit_CN.json`: a multi-option group whose
next authored slot is a single-option boundary sitting on one branch line. The
rule still requires complete forward jump coverage and distinct non-empty
paths for every option. It recovers `dlg_c28m3_23` group 2:

- `option_dlg_c28m3_23_2_001` -> `dlg_c28m3_23_014`
- `option_dlg_c28m3_23_2_002` -> `dlg_c28m3_23_015`

On 2026-05-12 a directional Runtime Jump rule resolved the `dlg_c13m2_12`
group 1 contradiction. The key evidence is that the reverse clip for option 2
starts at the option prompt and covers `dlg_c13m2_12_027`, while the forward
clip for option 1 skips that same line. The recovered routes are:

- `option_dlg_c13m2_12_1_001` -> `dlg_c13m2_12_003`,
  `dlg_c13m2_12_004`, `dlg_c13m2_12_005`
- `option_dlg_c13m2_12_1_002` -> `dlg_c13m2_12_027`,
  `dlg_c13m2_12_003`, `dlg_c13m2_12_004`, `dlg_c13m2_12_005`

That changed `dlg_c13m2_12` group 1 from `inferredFollowingLines` into
`timelineRouteBranches`, with both the forward skip track and the reverse
range track preserved in the WebUI evidence payload. After that promotion, the
audit has 106 remaining inferred groups; 10 have nearby Runtime Jump clips,
and 0 pass the strict promotion checks. The nearby cases are therefore
diagnostic only for now.

On 2026-05-12 `scripts/webui/build_runtime_jump_option_route_audit.py` gained
targeted filters so these diagnostics can be checked without a full global
scan:

```bat
python scripts\webui\build_runtime_jump_option_route_audit.py --language CN --story dlg_e1m1_5 --group 3
python scripts\webui\build_runtime_jump_option_route_audit.py --language CN --story dlg_c28m3_23 --group 1
python scripts\webui\build_runtime_jump_option_route_audit.py --language CN --story dlg_c13m2_12 --group 1
```

Current spot checks after the directional-rule promotion still do not justify
another automatic route rule:

- `dlg_e1m1_5` group 3 has no nearby Runtime Jump clips.
- `dlg_c28m3_23` group 1 has nearby forward jumps, but they belong to option
  indices 3 and 4 rather than the inferred group's option indices 1 and 2.
- The remaining nearby Runtime Jump cases either contradict the current
  inferred first line or lack complete option coverage.

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
