# Scripts

Active scripts in this directory support the WebUI export/package workflow.
Unity character recovery tools live under
`../unity_endfield_graph_shader_lab/tools`.

## Active Wrappers

From the repo root:

```bat
.\export.bat
.\package_webui.bat
```

`export.bat` is the normal WebUI refresh path. It runs:

- `scripts/export_full_from_game.py --skip-raw-vfs --skip-source-inventory`
- `scripts/verify_export_freshness.py`
- `scripts/story_builder/dialog_registry.py --quiet`
- `scripts/story_builder/video_bindings.py`
- `scripts/story_builder/source_links.py`
- `scripts/build_updates.py`
- `scripts/story_builder/build.py --languages CN --default-language CN`
- `scripts/build_assets.py`

Use `.\export.bat --init-build` for initial or baseline-only builds where the
Updates feed should be baselined instead of reporting changes.
Use `.\export.bat --fast-assets` for local refreshes that can reuse existing
asset indexes and skip demo bundle zip generation.
Use `.\export.bat --skip-export-full` to rebuild WebUI data from an existing
`export_full/` while still running the freshness guard before the builders.

`package_webui.bat` runs `scripts/package_webui.py` and creates split
shareable zips. The main story zip contains `serve.py`, `webui/`, generated
story/reference text data, WebUI code, and emoji images. The companion assets
zip contains the larger displayed image/video media resolved from
`export_full/`; extract the story zip first, then extract the assets zip into
the same directory when media is wanted. Packaging excludes 3D/model payloads
and does not include
`scratch/`, `reports/`, or `tmp/`.

## Folder Contract

The active WebUI export/package workflow should not require inputs from
`../scratch/`, `../reports/`, or `../tmp/`.

Expected active inputs and outputs:

- `../webui/`: static browser app plus generated WebUI data under
  `webui/data/`.
- `../export_full/`: generated export data used by Story, Reference, Assets,
  and package media resolution.
- `../.game-data-tracker/`: persistent state for original installed game-data
  update tracking.
- `../reports/`: durable generated reports and summaries written by exporters
  or builders. These are outputs, not package inputs, and should not contain
  agent investigation conclusions.
- `../memory/`: observations, conclusions, older exploration notes, status
  snapshots, and archived scripts.
- `../scratch/`: disposable probes, temporary prototypes, logs, generated
  previews, and experiment output that has not become part of a maintained
  workflow.
- `../tmp/`: disposable intermediate output and temporary files.
- `../tools/`: tracked lightweight helper scripts plus ignored local
  vendor/tool caches. If a workflow needs reusable helper data such as
  AnimeStudio DummyDlls, place it here or pass it explicitly rather than
  relying on `scratch/` or `tmp/`. New promoted tools need intentional
  tracking and documentation because this directory is ignored by default.

## WebUI

- `export_full_from_game.py`: export data from the installed Endfield client.
  The normal WebUI wrapper is `..\export.bat`, which skips raw VFS and source
  inventory. It writes generated summaries under `..\reports\` but does not
  require `reports`, `scratch`, or `tmp` as active inputs.
- `verify_export_freshness.py`: compares the latest export summary with
  the current installed `Endfield_Data` source fingerprints and verifies the
  WebUI-required export folders are present. `export.bat` runs it immediately
  after `export_full_from_game.py` so game updates do not silently reuse stale
  `export_full/` data.
- `track_export_changes.py`: generic file-tree tracker used by the WebUI
  Updates builder.
- `build_updates.py`: writes `webui/data/updates/latest.json` from the
  original installed game data only. Tracker state lives under
  `..\.game-data-tracker\`; generated summary reports live under
  `..\reports\`. Zero-change reruns preserve or restore the last non-empty
  feed from tracker history so accidental duplicate runs do not blank the
  Updates page. Non-empty feed snapshots are written as
  `..\.game-data-tracker\history\update-feed-*.json` so asset-level entries can
  be recovered with the game-data entries. Pass `--baseline-only` to update
  tracker state while writing an empty feed, or `--skip-asset-updates` to skip
  only the exported
  image/model/video asset diff.
- `story_builder/build.py`: builds CN story/reference data by default,
  with optional extra languages. The builder reads from `..\export_full\`, stamps dialog convs
  with DialogIdTable runtime registry evidence, links narrative
  Cutscene/RemoteComm video files to matching story entries, and writes
  generated WebUI data plus durable reports. The static frontend currently
  treats SNS emoji ids such as `sns_emoji_*` as inline emoji, while non-emoji
  SNS media such as `sns_image_*` and `sns_sticker_*` render as normal images.
- `build_assets.py`: builds the WebUI asset index, video index, story media
  index, and optional demo bundle zips from active WebUI export roots. Pass
  `--fast` to reuse existing indexes when present and skip demo bundle zip
  generation, or `--skip-bundles` to rebuild indexes without bundle zips.
- `asset_builder/`: shared asset-browser indexing, story-media selection, and
  demo bundle helpers used by `build_assets.py` and the Updates builder.
- `package_webui.py`: packages split shareable WebUI zips from
  `serve.py`, `..\webui\`, and displayed media files under `..\export_full\`.
  The primary zip is story/code/emoji only, including the full
  `envEmoji_common_*` prefab layer sprite set; the companion assets zip carries
  larger images and videos.
- `common.py`: small shared constants and JSON/path helpers for the
  WebUI builders.

## WebUI Story Helpers

These are kept because the WebUI story builders import or use them:

- `story_builder/timeline_recovery.py`: parses `dlgtl_*` Timeline MonoBehaviour
  data into authored line orders. Backs the `dialogTimeline` recovery mode,
  which corresponds to the runtime path
  `Beyond.Gameplay.Core.DialogTimelineManager.PlayDialogTimeline`.
- `story_builder/mission_recovery.py`: reconstructs mission-level quest/scene
  ordering evidence from `MissionRuntimeAsset`.
- `story_builder/dialog_registry.py`: extracts
  `Beyond.Gameplay.DialogIdTable` (the runtime's authoritative dialog
  registry) into a sceneKey index used by `scene_order_gap_shared.py` for
  evidence-grounded "registered vs cut content" classification. Runs as
  part of `export.bat` between the main export step and the build steps.
- `story_builder/source_links.py`: scans `MissionRuntimeAsset`,
  `LevelScriptData`, and `LevelScriptTemplateData` for `dlg_*`, `radio_*`,
  `sns_*`, `cutscene_*`, `remotecomm_*`, and reading-popup references. It
  writes `export_full/recovered/story_source_links.json`; the Story builder
  stamps matching conv files and index entries with source evidence and
  writes per-language coverage/orphan reports.
- `story_builder/video_bindings.py` builds the narrative video binding evidence used
  by the Story builder. Timeline-backed links are preserved into
  `webui/data/lang/<LANG>/narrative_video_evidence.json` so a WebUI video can
  be traced to the exact `BeyondFMVPlayableAsset` / Timeline source instead of
  relying on filename matching. Narrative videos that only match by name are
  emitted as standalone `video` story files grouped by mission, while stronger
  bindings remain attached to the proven dialog or cutscene.
- `story_builder/` also scans narrative video folders under
  `Data/Video/PC/Narrative/Cutscene` and `RemoteComm`, attaches matching
  `narrativeVideos` to dialog/cutscene/remotecomm conv JSON, and writes
  `reports/narrative_videos_<LANG>.json` / `.md`.

## Story Recovery Tools

These scripts are not part of `export.bat`; they live under
`scripts/story_recovery/` so the root export/package commands stay easy to
scan:

- `story_recovery/build_runtime_jump_option_route_audit.py`: audits remaining
  live `inferredOptionResponse` warning groups against nearby Runtime Jump
  Track clips, including forward skip ranges, reverse/directional ranges, and
  `needChangeOptionAfterJump` markers. It writes
  `reports/runtime_jump_option_route_audit_<LANG>.json` / `.md`. Use it
  before promoting any new automatic option-route rule. Pass
  `--include-promoted-risk-groups` only when you intentionally want to inspect
  already anchored diagnostic `optionBranchRisk` rows.
- `story_recovery/build_option_route_evidence_controls.py`: summarizes
  positive Runtime Jump route controls from `timeline_line_orders.json` beside
  the current negative-control `runtime_jump_option_route_audit` queue. It
  writes `reports/option_route_evidence_controls_<LANG>_priority.json` / `.md`
  and documents the evidence bar for promoting inferred option responses.
- `story_recovery/build_priority_story_order_audit.py`: summarizes the current
  main-story, event, major-mission, and character-story recovery surface from
  the built WebUI data. It writes `reports/priority_story_order_<LANG>.json` /
  `.md`, including ordered/unknown totals, remaining inferred responses,
  non-runtime option-layout rows, uncovered line warnings, and top unknown
  missions.
- `story_recovery/build_option_playable_semantics_audit.py`: audits remaining
  `inferredOptionResponse` groups against decoded
  `DialogOptionPlayableAsset` fields such as `logicId`, `trunkId`,
  `dialogId`, `conditionRid`, `changeFinishNum`, and `targetFinishNum`. Use
  `--only-interesting` to focus on groups where `logicId` is the only
  non-default semantic clue, or `--story <key> --group <n>` for a targeted
  scene check.
- `story_recovery/build_option_logic_id_audit.py`: follows up on the `logicId` queue by
  scanning structured tables, `MissionRuntimeAsset`, `LevelScriptData`,
  `LevelScriptTemplateData`, gameplay config, and Lua consumer terms for exact
  references to option `logicId` values. Same-mission mission/level-script
  matches would be high-value evidence; table/config-only matches are
  diagnostic unless another source links them to the dialog.
- `story_recovery/build_dialog_tree_option_route_audit.py`: audits remaining
  `inferredOptionResponse` groups against decoded AnimeStudio DialogTree
  routes, related scene links, target fragments, and cinematic wrappers. Use it
  after the option-playable and `logicId` audits to separate cases where
  the Story builder could promote authored tree evidence from the larger queue
  that needs deeper Timeline/runtime option-target decoding.
- `story_recovery/build_timeline_option_flow_audit.py`: audits remaining
  `inferredOptionResponse` groups against raw Timeline trunk clips. It reports
  whether candidate response clips carry useful non-default `optionIndex`
  values, resolves `misc_dlg_*` WebUI aliases to underlying `dlg_*` Timeline
  entries, and separates promotable `trunkClipOptionIndexRoute` cases from the
  common default `optionIndex=0` adjacent layouts that are diagnostic only.
- `story_recovery/build_timeline_binding_audit.py`: checks whether unresolved
  option responses separate cleanly by Timeline track, track binding, actor
  binding, or option-clip placement.
- `scene_order_gap_shared.py`: classifies each scene's line-order and
  option-layout recovery quality. Consumes the DialogIdTable registry above
  to upgrade `lineIdSuffix`-mode scenes to one of:
  - `unregisteredScene`: sceneKey is absent from `DialogIdTable`, so the
    runtime cannot load this scene at all (cut/dead content; the only order
    that exists is `DialogTextTable` layout).
  - `dialogTrunkRowIteration`: sceneKey IS registered but no Timeline or
    dialogTree source matched; `DialogTrunkBehaviour` would iterate
    `DialogTextTable` rows by sceneKey prefix, which produces the same
    sequence we already emit.
- `story_recovery/annotate_conv_with_registry.py`: standalone refresher for stamping each
  dialog conv JSON's `_debug` block with a `runtimeRegistry` evidence record
  (registered flag, trunk count, per-trunk line ids from `DialogIdTable`).
  The Story builder does this during normal exports; the refresher is useful
  when updating existing conv files without a full rebuild. Pure evidence
  surfacing; no inference.
- `story_recovery/rewrite_scene_order_warnings.py`: one-shot warning rebuild for conv
  JSONs without re-running the Story builder. Useful after tightening
  `scene_order_gap_shared.py` criteria.

### IL2CPP-derived evidence (out-of-band)

The C# class hierarchy backing the recovery modes was confirmed by scanning
`global-metadata.dat` from the game's IL2CPP runtime. The maintained helpers
under `tools/endfield-il2cpp/` validate/cache the metadata artifact, catalog
option-flow fields and method targets, and map focused body targets to
`GameAssembly.dll` addresses. They write drift/evidence reports outside the
normal WebUI build.
Relevant runtime types:

- `Beyond.Gameplay.Core.DialogManager` (partial across `.DialogTree.cs`,
  `.Level.cs`, `.LifeCycle.cs`, `.Timeline.cs`) -- routes every dialog load
- `Beyond.Gameplay.Core.DialogTrunkBehaviour` -- per-trunk playback driver
- `Beyond.Gameplay.Core.DialogTimelineManager` -- Timeline-driven path
- `Beyond.Gameplay.Core.DialogTreeController` -- tree/branch navigation
- `Beyond.Gameplay.Core.DialogOptionBehaviour` -- option/choice nodes
- `Beyond.Gameplay.DialogIdTable` -- runtime dialog registry (extracted by
  `story_builder/dialog_registry.py`)

There is **no** separate document / letter / memo / consent-form UI loader
class anywhere in the runtime. Every dialog scene -- including the "letter"
and "consent form" content -- goes through `DialogTrunkBehaviour
._TryInitDialogText`, with `DialogTimelineManager` and `DialogTreeController`
overlaid when applicable.

## Unity Character Recovery Lab

No active Unity character recovery scripts are present directly under this
`scripts/` directory in the current checkout. Unity recovery helpers should
live inside `../unity_endfield_graph_shader_lab/` unless they are promoted into
a shared WebUI/export workflow.

## Archived

The old archived-script bucket has been retired. UE5 pose-demo helpers live
with the UE project under `../ue5_zhuangfy_pose_demo 5.3/Scripts/`.
Put new experiments in `../scratch/` or `../tmp/`, and move observations or
conclusions to `../memory/` when they need to be kept.
