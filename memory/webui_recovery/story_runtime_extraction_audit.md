# Story Runtime Extraction Audit

Date: 2026-05-11

## Summary

Yes: the repo can use offline IL2CPP metadata and the already-exported game
data to recover more story-adjacent information. `global-metadata.dat` is useful
as a runtime-vocabulary source, but the actual story payload is mostly in the
structured tables, mission/runtime JSON, Lua UI scripts, and recovered
AnimeStudio/Unity asset map.

## Verified This Pass

- `tools/endfield-il2cpp/catalog_option_flow_metadata.py` parses:
  `D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat`
  - metadata size: 57,526,184 bytes
  - version: 29
  - dialog option/timeline/trunk focus fields are cataloged for drift checks.
- Historical broader runtime vocabulary report:
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

Current CN result after the 2026-05-12 DialogIdTable evidence pass:

- `106` remaining inferred response groups audited.
- `0` groups have clean per-option authored DialogTree routes to promote.
- `97` groups are `cinematicTreeTimelineOnly`: the DialogTree source exists,
  but it is a cinematic wrapper that launches a `dlgtl_*` Timeline; option
  route information must come from Timeline/runtime selection flow.
- `6` groups are `timelineOnlyNoTree`, currently all scenes whose WebUI key
  had to be resolved back to an underlying `dlg_*` Timeline source.
- `1` group (`dlg_e2m5_3` group 1) is
  `treePresentRuntimeTrunkOnly`: DialogTree covers a later option group, while
  `DialogIdTable` exposes runtime trunk refs for the earlier group
  (`trunk 1: dlg_e2m5_3_1_001, dlg_e2m5_3_1_002`). The next action is
  `decodeRuntimeTrunkOptionMapping`, not a looser DialogTree promotion.
- `2` groups (`dlg_e3m6_11` group 4 and `dlg_e6m2_7` group 1) have authored
  shared-route evidence. Both options route into the same authored path, so
  they should not be treated as confirmed per-option branches.
- All `106` audited rows now carry DialogIdTable trunk line refs in the JSON
  and Markdown reports.
- After `scripts/recover_dialog_id_registry.py` was widened to extract
  `option_dlg_*` tokens from the same binary table, all `106` audited rows
  also have DialogIdTable option refs for the current group, and all current
  WebUI option IDs are present in those refs. The current registry extraction
  finds `3,725` runtime option IDs across `1,185` scenes.
- A spot byte check around `dlg_e2m5_3` option IDs shows multiple duplicate
  option-id blocks with nearby dense little-endian integers such as `489`,
  `490`, and `491`. They do not match Timeline `logicId` values (`2` and `4`)
  and should be treated as registry/string ordinals until a fuller
  MemoryPack decoder proves otherwise.

Recovery gain: this closes the obvious AnimeStudio DialogTree promotion path
for the unresolved queue and adds a runtime grouping lens. DialogIdTable now
confirms that the unresolved option IDs are real runtime options, not WebUI
inventions or missing table joins. Its trunk refs explain which original trunk
rows the runtime knows about, but they are not branch targets by themselves.
The biggest remaining quality lever is decoding how option selection maps to
those runtime trunk refs or to Timeline target state, not broader DialogTree
inference.

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

The WebUI now renders these route-backed groups as option-specific prefixes
plus one shared suffix. For `dlg_c13m2_12`, that means option 2 shows
`dlg_c13m2_12_027` and a reverse-route loop marker, `dlg_c13m2_12_003` through
`dlg_c13m2_12_005` render once as the shared continuation, and the next
single-option group stays anchored after `dlg_c13m2_12_006`. In the current CN
bundle, 6 of the 18 `timelineRouteBranches` groups have this shared-suffix
shape, and 10 carry anchored continuation option evidence that should render
at the recovered line instead of being pulled up under the previous menu.

The renderer now treats branch path lines as single-owner lines rather than
using numeric suffix order to decide trunk visibility. This fixes cases where
Timeline order places a lower-suffix line after a higher-suffix option anchor,
such as `dlg_e6m1_10_012` after `dlg_e6m1_10_020`. A live WebUI audit over
the 1,272 current CN dialog-kind conversations with option groups found no
duplicate rendered `data-line-id` values after this change.

The follow-up renderer was flattened for branch-owned option anchors. Branch
path lines no longer mount child option groups inside `.branch-line`; instead,
groups anchored to lines owned by a branch route render as flat siblings in
the owning branch chain. Single-option groups render only the option prompt,
then their recovered path lines render as flat line siblings beside the option
prompt in that same chain; inside branch columns they use compact regular-line
styling, matching direct branch dialog lines. For
`option_dlg_gm01m8_3_11`, the scene graph evidence says option 1 reaches
`dlg_gm01m8_3_012`, then group 12 reaches regular line `dlg_gm01m8_3_013`;
option 2 reaches `dlg_gm01m8_3_014` through `dlg_gm01m8_3_016`, then group 16
joins the same continuation at `dlg_gm01m8_3_017`. The WebUI now renders group
12 and `dlg_gm01m8_3_013` at the same level inside the option-1 column, renders
group 16 inside the option-2 column, then resumes `dlg_gm01m8_3_017` once as
the common continuation below both columns. A live browser audit over the same
1,272 CN dialog-kind conversations found no duplicate rendered line ids, no
`.branch-line .opt-group` nests, no single-option groups containing rendered
line rows, and no legacy `.opt-block-branch-inline` blocks.

The branch-anchor rule is general, not keyed to `dlg_gm01m8_3`. A CN data scan
over 1,272 dialog conversations with options found 276 multi-option branch
parents, 65 branch-local child groups that should stay in the owning option
column, and 20 cases where a child group is anchored to a branch line but the
outcome evidence proves it is shared by every option. The WebUI gives the
shared-continuation evidence priority in those conflicts, so cases such as
`dlg_e10m1_3` render group 3 once below the two group-2 columns instead of
claiming it under only the `dlg_e10m1_3_007` column.

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

`scripts/webui/build_timeline_binding_audit.py` was added to test one more
backend-only branch hypothesis: whether unresolved option responses separate
cleanly by Timeline track, actor binding, or option-clip track placement.

Current CN result:

- `106` inferred response groups audited.
- `106` groups have option Timeline clip rows.
- `40` groups are `singleTrunkTrackOnly`.
- `65` groups are `optionClipTrackDifferentFromCandidates`, meaning the option
  clip track does not explain the response target lines.
- `1` group has an option-named track mapping:
  `dlg_c28m3_10` group 1 has candidate lines on `Option 1` and `Option 2`
  tracks, supporting the existing raw trunk `clipOptionIndex` mapping.
- `0` groups have candidate actor/binding splits.

Recovery gain: this adds a useful negative/confirmation audit. It does not
unlock a new broad automatic recovery rule, but it confirms that Timeline
track layout supports the already-promoted `dlg_c28m3_10` mapping and warns
against using option-clip track ids as branch targets for the remaining queue.
If future game exports add more `Option N` tracks or binding-split candidates,
this report will surface them quickly.

`tools/endfield-il2cpp/catalog_option_flow_metadata.py` was then added as the
next backend-only runtime evidence pass. It parses `global-metadata.dat` tables
directly instead of scanning identifier strings, including type, field, method,
parameter, image, and nested-type tables. The parser handles Endfield's local
v29 layout (`92` byte type records with start-index fields before flags).

Current output:

- `reports/option_flow_runtime_metadata.json`
- `reports/option_flow_runtime_metadata.md`
- metadata version `29`, `60,261` type definitions, `461,579` methods,
  `278,566` fields.
- `4,549` Beyond-assembly option/timeline/trunk-related matched types.
- `9` focus types and `54` likely method-body targets.

Important recovered runtime shape:

- `DialogTimelineOptionData` fields are exactly `optionIndex`,
  `changeFinishNum`, and `targetFinishNum`.
- `DialogOptionPlayableAsset` owns `options` and builds runtime playables via
  `GenPlayable`.
- `DialogOptionBehaviour` owns `m_options` and initializes them via
  `InitDialogOptions`.
- `DialogTrunkBehaviour` owns `m_trunkId` and initializes trunk playback via
  `InitDialogTrunk`.
- `DialogTimelineManager` owns `m_preTriggeredOptionAsset` and `m_options`;
  the most relevant selection-flow methods are `_SelectIndexInTimeline`,
  `TryTriggerTrunkBindingOption`, `SetDialogOption`, `ResetDialogOption`,
  `_TryDoNext`, `OnJumpForward`, and `SelectIndex`.
- DialogTree flow remains targetable through `DialogTreeController.SelectIndex`,
  `DialogTreeController.Next`, `DialogTreeOptionNode.GetNextIndex`,
  `DialogTreeOptionNode.GetChatOptionData`, and
  `DialogTreeExOptionNode.GetNextIndex`.

Recovery gain: this confirms that the explicit branch target is not simply a
hidden extra field on `DialogTimelineOptionData`; the runtime fields match the
decoded AnimeStudio option data we already audited. It also gives stable
method indices/tokens for future targeted backend audits, so we can focus on a
short option-selection call chain instead of searching the whole binary.

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

5. Keep IL2CPP work offline unless a concrete method-body target appears.
   - Use `catalog_option_flow_metadata.py` to cache/catalog metadata and watch
     focus-type drift after updates.
   - Current offline metadata and structured exports are enough for the next
     story-recovery improvements above.

## 2026-05-13 Audit Tool Signal Pass

`scripts/webui/build_dialog_tree_option_route_audit.py` and
`scripts/webui/build_timeline_option_flow_audit.py` were expanded to expose
more branch-recovery evidence before promoting more WebUI story routes.

New DialogTree audit signal:

- compact AnimeStudio action asset, cinematic timeline anchor, and cinematic
  finish-group summaries are included in JSON and Markdown rows.
- option field matrices now show `logicId`, `conditionRid`,
  `changeFinishNum`, and `targetFinishNum` across candidate option rows.
- summary counters now distinguish cinematic timeline anchors, cinematic
  finish groups, option finish-number fields, and finish-number matches.

Current CN results:

- `106` inferred response groups audited.
- `100` groups have cinematic timeline anchors.
- `0` groups have cinematic finish-number branches.
- `0` groups have option finish-number fields.
- `0` groups have finish-number fields matching cinematic finish groups.
- `2` groups remain shared authored routes: `dlg_e3m6_11` group `4` and
  `dlg_e6m2_7` group `1`.
- `dlg_e2m5_3` group `1` remains the main runtime-trunk-only target.

New Timeline option-flow audit signal:

- each group now includes a compact candidate window summary showing whether
  candidate trunk lines are contiguous, whether they start the audited window,
  candidate offset patterns, raw trunk clip `optionIndex` mappings,
  option/clip row indices, logic-id contiguity, and source track names.
- summary counters now track contiguous candidate windows, candidates at the
  window start, raw option-index mapping matches, nonzero raw option-index
  matches, and contiguous `logicId` groups.

Current CN results:

- `105` of `106` groups have contiguous candidate lines at the start of the
  audited window, but these are all default-adjacent windows with raw
  `optionIndex = 0`.
- `31` groups have raw option-index sets matching option rows, but almost all
  are all-zero default matches and should not be promoted as branch evidence.
- `1` group has a nonzero raw option-index mapping: `dlg_c28m3_10` group `1`,
  with `Option 1` / `Option 2` tracks mapping to trunk raw indices `1` / `2`.
- `45` groups have contiguous best-row `logicId` values, supporting the
  conclusion that `logicId` is usually sequential option/state numbering
  rather than an explicit branch target.

Recovery gain: the added diagnostics narrow the queue instead of broadening
automatic promotion. Current decoded data does not expose a finish-number
branch path, and most remaining inferred groups look like adjacent timeline
windows without explicit route evidence. The next useful implementation work is
to special-case or re-check `dlg_c28m3_10`, collapse the two shared-route cases
where appropriate, and target runtime trunk decoding for `dlg_e2m5_3`.

Follow-up implementation: `dlg_c28m3_10` group `1` was promoted from first-line
raw-index mapping to multi-line same-index branch runs. A scan across current
`timeline_line_orders.json` found three strict raw `clipOptionIndex` / option
`optionIndex` matches:

- `dlg_c28m1_2` group `4`: already covered by scene-graph branch evidence,
  with single-line raw-index starts.
- `dlg_c28m3_23` group `2`: already covered by Runtime Jump route evidence,
  with single-line raw-index starts.
- `dlg_c28m3_10` group `1`: the only extended same-index run. The recovered
  inferred branch evidence is now
  `option_dlg_c28m3_10_1_001 -> dlg_c28m3_10_023, dlg_c28m3_10_024` and
  `option_dlg_c28m3_10_1_002 -> dlg_c28m3_10_025, dlg_c28m3_10_026`, with
  `dlg_c28m3_10_021` as the merge/common continuation.

The rule remains conservative: it still requires the first candidate response
clips after the option anchor to contain a complete, distinct, nonzero raw
`clipOptionIndex` set matching the group's option indices before collecting
additional same-index branch lines.
Because this is stronger than adjacent-order inference, the WebUI keeps the
structured branch evidence and renders a distinct per-option `index matched`
chip for that strong raw-index sample instead of the weaker inferred-reply
chip. It is also removed from the unresolved `inferredOptionResponse` issue
queue while remaining visible through the Story recovery-method filter as
`optionBranch:rawIndexMatched`.

## 2026-05-13 Runtime Selection Body Mapping

`tools/endfield-il2cpp/catalog_option_flow_metadata.py` was widened to include
the `DialogUtils` option/timeline helpers in the compact focus pass:
`DialogChooseOption`, `DialogTimelineDoNext`,
`DialogTimelineGetAllActiveClips`, and `DialogTimelineDisableLoopInRange`.

`tools/endfield-il2cpp/map_body_targets_to_gameassembly.py` now maps those
focused metadata methods to `GameAssembly.dll` method pointers through
`CodeRegistration`, scans direct `call rel32` edges, and records a small
pre-call argument context. The decoder tracks the normal Windows x64 argument
registers plus common XMM moves used by timeline start/end float arguments,
and clears stale argument writes after intervening calls.

Current focused output:

- `reports/option_flow_runtime_metadata_focus.json` / `.md`
- `reports/option_flow_body_targets_gameassembly.json` / `.md`
- `29 / 29` focused body targets mapped.
- `205` resolved direct calls.
- `63` dialog-related direct calls.
- `12` direct calls to catalog targets.
- `14` important direct-call edges.

Strong selection-flow evidence from the GameAssembly report:

- `DialogTimelineManager.SelectIndex(index)` calls
  `_SelectIndexInTimeline(index)` with `rdx=esi`.
- `_SelectIndexInTimeline(index)` calls
  `DialogUtils.DialogChooseOption(timelineRoot, optionIndex)` with
  `rdx=ebx`, then calls `_TryDoNext(fromSelectOption)` with `rdx=1`.
- `_TryDoNext(fromSelectOption)` can call
  `TryTriggerTrunkBindingOption()` and later
  `DialogUtils.DialogTimelineDoNext(timelineRoot, startTime, endTime)`;
  the report now shows the timeline-root register and XMM start/end argument
  setup for those calls.

Recovery gain: this confirms the runtime chain that consumes the selected
option index and then advances the dialog timeline, but it still does not
expose per-option target trunk rows for the unresolved no-runtime-jump groups.
For WebUI promotion, the current safe evidence remains explicit DialogTree
branches, Runtime Jump route windows, or raw nonzero `clipOptionIndex` runs.
The remaining branch-target problem likely requires decoding local state inside
`DialogChooseOption`, `TryTriggerTrunkBindingOption`, or
`DialogTimelineDoNext`, not another serialized field search.

Follow-up body-summary pass: the GameAssembly mapper now also emits compact
method-body summaries for the focused selection methods. The important local
state shape is:

- `DialogTimelineManager.SetDialogOption(options)` treats manager field
  `this+0x1e0` as the active option list and compares list counts through
  `+0x18`.
- `_SelectIndexInTimeline(index)` uses the selected UI index to fetch an
  option row from `this+0x1e0`, then reads that option row's raw
  `optionIndex` from offset `+0x98`.
- `DialogChooseOption(timelineRoot, optionIndex)` writes that raw optionIndex
  into a timeline/playable object field at `+0x18` and passes the same value
  into the hotfix wrapper path.

Recovery gain: this explains why nonzero raw `clipOptionIndex` mappings are
strong branch evidence, and why all-zero option groups should not be rendered
as separate inferred per-option replies. `scripts/webui/build_story.py` now
classifies groups where all option rows and adjacent candidate trunk clips have
raw `optionIndex = 0` as `sharedTimelineContinuation` with a shared jump to
the first continuation line. This removes the weak inferred-reply chips while
leaving the normal following lines below the option box.

Current CN rebuild result after that rule:

- flagged scenes: `79`
- inferred option-response scenes: `46`
- `29` option groups now use `sharedTimelineContinuation`
- `dlg_e2m5_3` group `1` is now shared continuation:
  common line `dlg_e2m5_3_003`, option indices `[0, 0]`.
- Under this earlier all-option-index-zero-only rule, `dlg_e1m1_5` group `3`
  remained unresolved because its best option rows have raw option indices
  `[0, 1]`. The broader default trunk clip rule below supersedes that status.

## 2026-05-13 Default Trunk Clip Continuation

`scripts/webui/build_timeline_option_flow_audit.py` now buckets unresolved
Timeline option groups by raw option-index pattern and by candidate/window
trunk `clipOptionIndex` pattern. It also emits per-line raw clip indices,
recovered line `clipOptionIndex` values, nonzero-coverage booleans, and any
recovered Runtime Jump routes adjacent to the option group.

The audit before promotion found:

- `73` unresolved inferred response groups.
- `52` had mixed option-row `optionIndex` values such as `[0, 1]`.
- `21` had strict nonzero option-row `optionIndex` values.
- `73 / 73` candidate response windows had candidate trunk
  `clipOptionIndex = 0` only.
- `0 / 52` mixed groups had nonzero candidate/window clip coverage.
- `0 / 52` mixed groups had recovered Runtime Jump routes.

A broader scan across all recovered AnimeStudio timeline option groups found
`149` mixed `[0, nonzero]` groups and no counterexample with a nonzero
candidate/window clip or Runtime Jump route. That made the safer promotion
broader than the earlier all-option-index-zero rule: when the adjacent
candidate response window itself is all `clipOptionIndex = 0`, and no Runtime
Jump route branch was recovered, the WebUI now treats the window as shared
Timeline continuation starting at the first candidate line. It does not invent
per-option branch targets.

Initial CN rebuild result after this rule was too aggressive:

- flagged scenes: `33`
- inferred option-response scenes: `0`
- `103` option groups used `sharedTimelineContinuation`
  - `30` retained reason `rawOptionIndexConverges`
  - `73` used reason `defaultTrunkClipContinuation`

User review found the false positive: `dlg_e2m5_2` group `3` has strict
nonzero option indices `[1, 2, 3]`, and the candidate lines are semantically
the three option replies:

- `option_dlg_e2m5_2_3_001` ("是我。") -> `dlg_e2m5_2_023`
- `option_dlg_e2m5_2_3_002` ("是佩丽卡。") -> `dlg_e2m5_2_024`
- `option_dlg_e2m5_2_3_003` ("是这位陈千语。") -> `dlg_e2m5_2_025`
- merge/common continuation: `dlg_e2m5_2_026`

The correction keeps `sharedTimelineContinuation` for all-zero and mixed
`[0, nonzero]` option-row patterns, but no longer promotes strict-nonzero
groups when the only evidence is an all-zero candidate trunk clip window.
Strict nonzero groups return to `inferredFollowingLines` unless Runtime Jump
routes or raw nonzero same-index trunk clips provide stronger evidence.

Corrected CN rebuild result:

- flagged scenes: `48`
- inferred option-response scenes: `15`
- timeline option-flow audit unresolved groups: `21`
- all `21` unresolved audit groups are strict-nonzero option-index groups with
  all-zero candidate trunk clips and no recovered Runtime Jump routes.
- `82` option groups use `sharedTimelineContinuation`
  - `30` retain reason `rawOptionIndexConverges`
  - `52` use reason `defaultTrunkClipContinuation`

Sample outcomes:

- `dlg_e1m1_5` group `3` is now shared continuation:
  `optionIndex [0, 1]`, candidate clip indices `[0, 0]`, common continuation
  `dlg_e1m1_5_036`, with `dlg_e1m1_5_036` and `dlg_e1m1_5_037` left as normal
  following lines below the option box.
- `dlg_c28m3_23` group `1` is no longer shared continuation after the
  strict-nonzero correction. It remains in the audit queue with candidates
  `dlg_c28m3_23_009, dlg_c28m3_23_010` and common continuation
  `dlg_c28m3_23_014`.
- `dlg_c28m3_10` group `1` remains the one strong raw-index branch mapping:
  option `1` maps to `dlg_c28m3_10_023, dlg_c28m3_10_024`; option `2` maps to
  `dlg_c28m3_10_025, dlg_c28m3_10_026`.

## 2026-05-13 IL2CPP Value-Flow Windows And E2M6 Clues

`tools/endfield-il2cpp/map_body_targets_to_gameassembly.py` now emits compact
field/value-flow decision windows in addition to direct call edges. This makes
the option-selection evidence easier to audit without opening a disassembler.
The regenerated reports are:

- `reports/option_flow_body_targets_gameassembly.json`
- `reports/option_flow_body_targets_gameassembly.md`

New high-signal windows:

- `_SelectIndexInTimeline(index)` fetches `this+0x1e0[index]`, then reads
  `[selectedOption+0x98]` and passes that value as `rdx` to
  `DialogChooseOption`.
- `DialogChooseOption(timelineRoot, optionIndex)` writes the selected raw
  `optionIndex` into `[rax+0x18]` and passes the same value into the wrapper
  path.
- `TryTriggerTrunkBindingOption()` gets active clips, checks `[rax+0x18]`,
  calls `SetDialogOption`, and then calls `DialogTimelineDisableLoopInRange`
  with the selected time range.

Interpretation: IL2CPP confirms that runtime option selection is driven by the
raw per-option value at the selected option object's `+0x98`, then stored into
a timeline/playable object field at `+0x18`. This strengthens the existing raw
`clipOptionIndex` promotion rule, but it still does not by itself identify
branch target rows when all adjacent trunk clips carry default
`clipOptionIndex = 0`.

The mapper was then deepened to separate register reads from register writes,
decode more short conditional branches and scalar SSE operations, include the
`DialogTimelineGetAllActiveClips` and `DialogTimelineDisableLoopInRange`
bodies, and emit explicit `optionFlowFacts`. The regenerated
`reports/option_flow_body_targets_gameassembly.*` report extracts `6` facts:

- `_SelectIndexInTimeline`: UI `index` is used to look up a selected Timeline
  option object, then that object's `+0x98` value is passed to
  `DialogChooseOption`.
- `DialogChooseOption`: the selected option index is written into a runtime
  option/playable object's `+0x18` field.
- `_TryDoNext`: checks the manager's current option `+0x18` before entering
  trunk-binding option handling.
- `TryTriggerTrunkBindingOption`: only calls `SetDialogOption` for an active
  clip whose runtime `+0x18` option field is positive.
- `SetDialogOption`: compares the manager current option `+0x18` against the
  candidate option `+0x18`, and treats zero as the default/non-branch case.
- `TryTriggerTrunkBindingOption`: after selecting an active option clip, passes
  clip time fields into `DialogTimelineDisableLoopInRange`
  (`[rsi+0x18]` as start, `[rbx+0x18]` minus a small scalar constant as end).

This corrected one earlier over-broad-looking trace: after
`mov ebx, [rax+0x98]`, the register is no longer considered `param:index`.
The useful conclusion stays the same but is sharper: runtime branch selection
depends on nonzero runtime option fields, and all-zero adjacent trunk clip
windows remain insufficient evidence for per-option branch recovery without
another way to map active runtime clips back to authored Timeline rows.

For `dlg_e2m6_11`, there is a strong non-IL2CPP placement clue:

- Current WebUI data places group 1 after `dlg_e2m6_11_006` only by
  `siblingTimelinePosition`, and records `branchHint.scenes = [dlg_e2m6_19]`
  on shared timeline `dlgtl_e2m6_11_sub_1`.
- `dlg_e2m6_19` has authored `scene_graph` branches for the same option prompt
  shape:
  - option 1 reaches `dlg_e2m6_19_002`, `dlg_e2m6_19_003`;
  - option 2 reaches `dlg_e2m6_19_004`.
- Those branch line texts exactly match `dlg_e2m6_11_007`,
  `dlg_e2m6_11_008`, and `dlg_e2m6_11_009`.

So the likely transplanted mapping for `dlg_e2m6_11` is:

- `option_dlg_e2m6_11_1_001` -> `dlg_e2m6_11_007`,
  `dlg_e2m6_11_008`
- `option_dlg_e2m6_11_1_002` -> `dlg_e2m6_11_009`

A guarded sibling-scene text transplant rule was added to `build_story.py` for
this case. It only runs when the option anchor itself is a fallback
`siblingTimelinePosition`, the sibling scene has authored SceneGraph branches
for a compatible option sequence, and each sibling branch line text maps to a
unique local line after the fallback anchor. The CN rebuild found exactly one
generated group with `optionBranchRisk.code = siblingSceneTextBranches`:
`dlg_e2m6_11` group 1. The generated mapping is:

- `option_dlg_e2m6_11_1_001` -> `dlg_e2m6_11_007`,
  `dlg_e2m6_11_008`
- `option_dlg_e2m6_11_1_002` -> `dlg_e2m6_11_009`

The broader quality counts are unchanged after this patch: `48` flagged
scenes, `19` scenes with inferred option layout, and `15` scenes with inferred
option response. `dlg_e2m6_11` still keeps `inferredOptionLayout` because its
option box position is inferred from the sibling timeline, but the option
response rows are now recovered from sibling SceneGraph text evidence.

For `dlg_e2m6_18`, the evidence remains weak:

- The scene is absent from `DialogIdTable`, so runtime DialogManager has no
  entry point for it.
- There is no recovered Timeline, no DialogTree option branch, no related
  sibling scene, and source-graph option queries only show `has_option`.
- The current placement after `dlg_e2m6_18_001` is therefore a line-number
  fallback plus natural reading order, not confirmed runtime or authored route
  evidence.

## 2026-05-13 Runtime-Gate Audit Surface

`scripts/webui/build_timeline_option_flow_audit.py` now imports the compact
`optionFlowFacts` from `reports/option_flow_body_targets_gameassembly.json`
and adds a `runtimeGate` block to each audited Timeline option group. That
block translates the IL2CPP finding into per-line evidence: selected option
rows feed runtime `+0x18`, and active branch clips require a positive runtime
option field, so candidate trunk clips whose raw/runtime option field is `0`
do not satisfy the branch gate.

Current CN audit result after the patch:

- `21` inferred response groups remain in the Timeline audit queue.
- all `21` have verdict
  `strictOptionRowsButAllZeroCandidateRuntimeField`.
- `0` groups have candidate runtime fields mapping back to option indices.
- `1` group has a nonzero runtime field elsewhere in the audited window:
  `dlg_c28m3_23` group `1`, where candidates `dlg_c28m3_23_009` and
  `dlg_c28m3_23_010` are still `0`, while common continuation
  `dlg_c28m3_23_014` carries runtime field `3`.

Recovery implication: this makes the negative evidence easier to inspect
without changing WebUI output. It also keeps the `dlg_e2m5_2` group `3` false
positive safely blocked: its three candidate response rows are adjacent and
semantically branch-like, but the candidate runtime fields are still all zero,
so the audit does not promote a shared continuation or a raw-index route.

AnimeStudio exporter check: the current exported MonoBehaviour JSON already
contains the option playable rows, raw trunk clip fields, track/file
provenance, type-tree field paths, and resolved script metadata needed by this
audit. There is no clear C# exporter gap for these option groups yet. The next
AnimeStudio patch should wait for a specific missing serialized signal, such
as stronger PlayableDirector binding detail or an unresolved PPtr relation
that is not already present in `$animestudio`.

## 2026-05-13 Active Clip Slice Pass

`tools/endfield-il2cpp/map_body_targets_to_gameassembly.py` was patched again
to emit backward register slices for the hot `TryTriggerTrunkBindingOption`
path. The regenerated `reports/option_flow_body_targets_gameassembly.*` report
now shows where the active option object and loop-disable range arguments come
from instead of only showing the final calls.

New concrete shape in `TryTriggerTrunkBindingOption`:

- `DialogTimelineGetAllActiveClips(timelineRoot, outClips)` is called at
  `+0x25b`.
- The candidate object passed into `SetDialogOption` is loaded from
  `[rbx+0x28]`, checked at `[rax+0x18] > 0`, and then passed as
  `rdx = rax` at `+0x3f1`.
- The loop-disable start time is loaded from `[rsi+0x18]` into `xmm7`.
- The loop-disable end time is loaded from `[rbx+0x18]` into `xmm6`, adjusted
  by a small constant, and passed as `xmm2`.
- After `DialogTimelineDisableLoopInRange`, the same `rbx` is stored to
  manager field `[r14+0x1a8]`.

Interpretation: `rbx` is now a stronger candidate for the active clip/list
node or end-boundary node, while `rax = [rbx+0x28]` is the option object whose
runtime option field gates `SetDialogOption`. `rsi` appears to hold the
start-boundary node used for the disable range. The next useful mapper patch
is to decode the list/enumerator calls between `DialogTimelineGetAllActiveClips`
and the `rbx`/`rsi` assignments so the report can name whether these are
current/previous/next active clips and map the start/end time range back to
Timeline clip windows.

Follow-up AnimeStudio log audit:

- Current summary reports pointed at cached AnimeStudio stdout logs under
  `reports/20260421_041136`, `reports/20260424_142747`, and
  `reports/20260511_181106`.
- JSON-by-type logs do contain MonoBehaviour export errors:
  - StreamingAssets: `29` `Unable to read beyond the end of the stream`
    MonoBehaviour failures.
  - Persistent: `19` equivalent MonoBehaviour failures.
  - `0` of those JSON export failures have story-like names (`dlg`,
    `dlgtl`, `dialog`, `timeline`, `cutscene`, `option`, `trunk`,
    `playable`).
- Convert-by-type logs are noisier. The 2026-05-11 Persistent convert log has
  many GameObject/AnimationClip export errors; `140` broadly match story-like
  keywords, including `dlgtl_*` actor/light/effect objects and cutscene
  lighting/camera objects. These affect model/FBX conversion visibility, not
  the JSON Timeline/MonoBehaviour data path used by story line-order recovery.

Two patches came out of this:

- `scripts/export_full_from_game.py` now scans AnimeStudio stdout/stderr logs
  and records log issue counts plus export-error samples in
  `export_full_summary.json` / `.md`, so future summaries no longer hide
  AnimeStudio errors behind `failed_to_decode.txt = 0`.
- AnimeStudio CLI `ExportMonoBehaviour` now writes a metadata-only JSON
  fallback when normal type-tree decoding fails. The fallback preserves
  `$animestudio`, raw data hash/optional sidecar, script metadata, path id,
  and `decodeError` instead of letting those MonoBehaviours disappear. The CLI
  rebuild passed after the patch.

Recovery implication: we did miss AnimeStudio log issues operationally, but
the current missed JSON MonoBehaviours do not explain unresolved option
branches. The convert-stage story-like failures may matter for future visual
cutscene/lighting recovery, but they are not evidence for changing
`build_story.py` option routing rules.

## 2026-05-13 AnimeStudio Log Recheck And Active Traversal Fact

The first post-patch AnimeStudio summary was misleading because
`scripts/export_full_from_game.py` kept the cached stage stdout/stderr paths
when a fresh AnimeStudio command result existed. That made the summary scan old
April/May logs even though the new run had already succeeded. The exporter
summary now replaces stage log paths with the current `CommandResult` paths and
classifies metadata-only MonoBehaviour JSON fallbacks separately from real
export errors.

Fresh evidence after the fix:

- `reports/20260513_032741/*_animestudio_json_by_type.stdout.log` contains
  metadata-only fallback warnings, not `[Error] Export ... error` rows.
- A narrow Persistent refresh at `reports/20260513_034816` ran only
  `MonoBehaviour` for `json_by_type` in `9.161s`.
- Persistent JSON summary now reports `export_error_count = 0`,
  `story_like_export_error_count = 0`, and `metadata_only_json_count = 18`.
- The fallback rows are enemy/npc behavior MonoBehaviours such as
  `BB_eny_0057_dog`, `BB_eny_0055_hscrane_hard`, and
  `BB_eny_scripted_move_base`; none are dialog/timeline/option-looking names.

So the AnimeStudio patch did recover otherwise-missing JSON placeholders and
made the logs auditable, but it still does not reveal a missing serialized
story route signal.

The IL2CPP mapper was then deepened around the active clip traversal window.
`reports/option_flow_body_targets_gameassembly.*` now includes a seventh
`optionFlowFacts` entry, `activeClipTraversalWindow`, for
`TryTriggerTrunkBindingOption`:

- after `DialogTimelineGetAllActiveClips` at `+0x25b`, the method makes three
  unresolved iterator/setup calls at `+0x28a`, `+0x2c1`, and `+0x2e5`;
- then it makes seven lookup/equality calls through the candidate scan window,
  including `PlayableDirectorUtility.GetTimelinePlayable` at `+0x346` and
  `Object.op_Equality` at `+0x3c1`;
- recovered state loads show `rsi = [rsp+0x30]`, `r13 = rax`, and repeated
  `rbx = rax` assignments;
- candidate checks show the payload load `rax = [rbx+0x28]`, followed by
  `cmp [rax+0x18], 0x0` before `SetDialogOption`.

Interpretation: `rbx` is the selected active clip/list node, `[rbx+0x28]` is
the option payload object whose runtime `+0x18` gates branch selection, and
`rsi` is the paired start-boundary node later used for the
`DialogTimelineDisableLoopInRange` start time. This strengthens the runtime
model for active clip selection, but it still does not map all-zero candidate
Timeline rows back to per-option branches.

The regenerated CN Timeline option-flow audit now sees `7` IL2CPP facts and
still reports the same recovery verdicts:

- `21` inferred-response groups remain audited.
- all `21` candidates have all-zero runtime fields.
- `0` groups have candidate runtime fields that map back to option indices.
- `1` group (`dlg_c28m3_23` group `1`) has a nonzero runtime field elsewhere
  in the window, outside the candidate response rows.

Recovery implication: do not relax the WebUI branch-promotion rule based only
on active clip traversal. The next useful IL2CPP step is naming the three
unresolved iterator/setup helpers or finding a way to join the active
clip/list nodes back to authored Timeline clip rows.

Follow-up decode of those traversal helper targets improved the names by
instruction shape:

- `+0x28a -> 0x182b37b40` is `listEnumeratorCtorLike`: it stores the active
  clip list into the stack enumerator struct and clears enumerator state.
- `+0x2c1 -> 0x1827201e0` is `listEnumeratorMoveNextLike`: it reads list size
  and version fields, advances the index, and stores the current item at
  `[rcx+0x10]`.
- `+0x2e5 -> 0x180425e00` remains an unclassified
  virtual/generic invoker-like call that jumps through a vtable/generic slot.
- `+0x33c -> 0x185b36e94` is `unityObjectFieldGetterLike`; in this call site it
  feeds `PlayableDirectorUtility.GetTimelinePlayable`.
- `+0x368`, `+0x387`, and `+0x3a5` all target `0x183151c50`, classified as
  `genericLookupHelperLike`, and use `[rsi+0x48]` plus candidate indexes
  (`[rax+0x1c]`, `[r13+0x20]`, and `-1`) to materialize candidate active clip
  nodes.

This means the runtime path is now clearer: it enumerates active clips, obtains
the current playable, then uses generic lookups to produce candidate clip nodes
before applying the positive `+0x18` option gate. It still does not expose a
serialized or runtime field that maps an all-zero candidate response row to a
specific selected option.

The mapper now also emits `activeClipsFromTimelinePlayableClipLists` from
`DialogTimelineGetAllActiveClips` itself. This is the first strong bridge from
runtime active clips back toward authored Timeline rows:

- `DialogTimelineGetAllActiveClips` calls
  `DialogTimelineGetAllTimelinePlayable` at `+0x189`.
- It enumerates the resulting Timeline playable list with
  `listEnumeratorCtorWrapperLike` and `listEnumeratorMoveNextLike` helpers.
- For each playable, it loads `rdx = [rax+0x40]`, then enumerates that clip
  list with `listEnumeratorCtorLike` and `listEnumeratorMoveNextLike`.
- Each candidate clip is passed through `unityObjectAliveFilterLike`, then
  appended to `outClips` through a `listAddLike` helper.

This answers one prior unknown: the active clip nodes consumed by
`TryTriggerTrunkBindingOption` come from per-playable clip lists, not from a
separate branch table. The regenerated audit now sees `8` IL2CPP facts. Its
verdict remains unchanged because the candidate rows in the unresolved queue
still carry all-zero runtime option fields.

`DialogTimelineGetAllTimelinePlayable` has now been promoted into the IL2CPP
body-target set and emits `timelinePlayableListFromTimelineRoot`. The recovered
shape is:

- the method creates/reuses a result list through helper calls at `+0xf6` and
  `+0x111`;
- it derives a Timeline-root collection through calls at `+0x119` and
  `+0x134`;
- it loops over the collection using a `listGetItemLike` helper at `+0x14c`;
- each item is resolved through `PlayableDirectorUtility.GetTimelinePlayable`
  at `+0x156`;
- non-null playables are appended to the result list through `listAddLike` at
  `+0x193`;
- the result list is stored/read through a global/static handle path ending in
  `+0x98`.

Together with `activeClipsFromTimelinePlayableClipLists`, the runtime chain is
now:

`timelineRoot -> Timeline playable list -> playable +0x40 clip list -> active
clip node -> [clip+0x28] option payload -> payload +0x18 branch gate`.

The CN Timeline option-flow audit now sees `9` IL2CPP facts. The verdict is
still unchanged: all `21` unresolved inferred-response groups have all-zero
candidate runtime fields and no candidate runtime-field mapping back to option
indices. This completes the currently useful IL2CPP structure pass without
creating a new WebUI promotion rule.

## 2026-05-13 Scene Placement Signals And Timeline DoNext

`scripts/recover_mission_timelines.py` now emits a compact `scenePlacement`
index for each recovered mission. It stays evidence-only and records, per
scene key, which signals exist:

- `missionStoryRef`: direct MissionRuntimeAsset story references, with quest ids
  and source fields.
- `clientActionStoryRef`: client-action references such as radio/menu actions.
- `sourceBackedSceneEdge`: source-backed LevelScript/AnimeStudio scene graph
  edges.
- `timelineEvidence`: recovered AnimeStudio Timeline entries.

The regenerated CN mission timeline report now has:

- `3,357` scene placement entries.
- `2,591` scenes with source-backed scene-edge signals.
- `512` scenes with MissionRuntimeAsset story refs.
- `322` scenes with client-action story refs.
- `40` scenes with timeline evidence.

`reports/scene_order_gap_report_CN.*` now joins those placement signals onto the
remaining flagged dialog scenes. Current flagged-scene coverage:

- `7` flagged scenes have mission/story-ref placement evidence.
- `18` flagged scenes have source-backed scene-edge evidence.
- `2` flagged scenes have timeline evidence.

The `e2m6` clue is now explicit in generated data:

- `dlg_e2m6_11` has a source-backed LevelScript outgoing edge from
  `export_full/structured/StreamingAssets/Data/Json/LevelScriptData/map01_lv006/3500010031.json`.
- `dlg_e2m6_19` has MissionRuntimeAsset evidence from
  `questDic.e2m6_q#10.objectiveList[0].condition.subConditions[1]._dialogId.constValue`
  and shares Timeline `dlgtl_e2m6_11_sub_1`.
- `dlg_e2m6_18` still has no mission placement signal and remains marked
  unregistered/cut by the scene-order gap report.

The IL2CPP mapper also gained a tenth fact,
`timelineDoNextActiveClipQueries`, for `DialogUtils.DialogTimelineDoNext`.
It shows runtime advancement resolving playable graph roots and calling:

- `TimelinePlayable.GetActiveClipsAtGivenTime` at `+0x844`;
- `TimelinePlayable.UpdateIntervalTree` at `+0xcb9`;
- `TimelinePlayable.GetActiveClipsAtGivenTimeRange` at `+0xf5d`;
- `TimelineRuntimeUtils.SetNewTimeForCutsceneRoot` at `+0x11da`.

Interpretation: runtime dialog/cutscene advancement is driven by Timeline
active-clip time windows, which strengthens intra-Timeline line/cutscene order
evidence. It still does not create a branch-target promotion rule for all-zero
candidate option rows. The refreshed CN Timeline option-flow audit now sees
`10` IL2CPP facts and keeps the same verdict: `21` inferred-response groups,
all `21` candidate sets have all-zero runtime fields, and `0` groups are
promotable by the runtime gate.
