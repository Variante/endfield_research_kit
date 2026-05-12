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
- `scripts/webui/verify_export_freshness.py`
- `scripts/recover_dialog_id_registry.py --quiet`
- `scripts/webui/build_story_source_links.py`
- `scripts/webui/build_updates.py`
- `scripts/webui/build_story.py --languages CN --default-language CN`
- `scripts/webui/build_assets.py`

Use `.\export.bat --init-build` for initial or baseline-only builds where the
Updates feed should be baselined instead of reporting changes.
Use `.\export.bat --fast-assets` for local refreshes that can reuse existing
asset indexes and skip demo bundle zip generation.

`package_webui.bat` runs `scripts/webui/package_webui.py` and creates a
shareable zip from `serve.py`, `webui/`, and displayed media resolved from
`export_full/`. It excludes 3D/model payloads and does not include
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
- `../tools/`: durable shared tools. If a workflow needs reusable helper data
  such as AnimeStudio DummyDlls, place it here or pass it explicitly rather
  than relying on `scratch/` or `tmp/`.

## WebUI

- `export_full_from_game.py`: export data from the installed Endfield client.
  The normal WebUI wrapper is `..\export.bat`, which skips raw VFS and source
  inventory. It writes generated summaries under `..\reports\` but does not
  require `reports`, `scratch`, or `tmp` as active inputs.
- `webui/verify_export_freshness.py`: compares the latest export summary with
  the current installed `Endfield_Data` source fingerprints and verifies the
  WebUI-required export folders are present. `export.bat` runs it immediately
  after `export_full_from_game.py` so game updates do not silently reuse stale
  `export_full/` data.
- `track_export_changes.py`: generic file-tree tracker used by the WebUI
  Updates builder.
- `webui/build_updates.py`: writes `webui/data/updates/latest.json` from the
  original installed game data only. Tracker state lives under
  `..\.game-data-tracker\`; generated summary reports live under
  `..\reports\`. Pass `--baseline-only` to update tracker state while writing
  an empty feed, or `--skip-asset-updates` to skip only the exported
  image/model/video asset diff.
- `webui/build_story.py`: builds CN story/reference data by default, with
  optional extra languages. It reads from `..\export_full\`, stamps dialog
  convs with DialogIdTable runtime registry evidence, links narrative
  Cutscene/RemoteComm video files to matching story entries, and writes
  generated WebUI data plus durable reports. The static frontend currently
  treats SNS emoji ids such as `sns_emoji_*` as inline emoji, while non-emoji
  SNS media such as `sns_image_*` and `sns_sticker_*` render as normal images.
- `webui/build_assets.py`: builds the WebUI asset index. By default it scans
  only active WebUI export roots and skips legacy `inventory`, `raw_vfs`, and
  `unresolved` roots. Pass `--include-extra-roots` to include those, or
  `--fast` to reuse existing indexes when present and skip demo bundle zip
  generation, or `--skip-bundles` to rebuild indexes without bundle zips.
- `webui/package_webui.py`: packages a shareable WebUI build from `serve.py`,
  `..\webui\`, and displayed media files under `..\export_full\`.
- `webui/common.py`: small shared constants and JSON/path helpers for the
  WebUI builders.

## WebUI Story Helpers

These are kept because the WebUI story builders import or use them:

- `recover_timeline_line_orders.py`: parses `dlgtl_*` Timeline MonoBehaviour
  data into authored line orders. Backs the `dialogTimeline` recovery mode,
  which corresponds to the runtime path
  `Beyond.Gameplay.Core.DialogTimelineManager.PlayDialogTimeline`.
- `recover_mission_timelines.py`: reconstructs mission-level quest/scene
  ordering evidence from `MissionRuntimeAsset`.
- `recover_dialog_id_registry.py`: extracts
  `Beyond.Gameplay.DialogIdTable` (the runtime's authoritative dialog
  registry) into a sceneKey index used by `scene_order_gap_shared.py` for
  evidence-grounded "registered vs cut content" classification. Runs as
  part of `export.bat` between the main export step and the build steps.
- `webui/build_story_source_links.py`: scans `MissionRuntimeAsset`,
  `LevelScriptData`, and `LevelScriptTemplateData` for `dlg_*`, `radio_*`,
  `sns_*`, `cutscene_*`, `remotecomm_*`, and reading-popup references. It
  writes `export_full/recovered/story_source_links.json`; `build_story.py`
  stamps matching conv files and index entries with source evidence and
  writes per-language coverage/orphan reports.
- `webui/build_story.py` also scans narrative video folders under
  `Data/Video/PC/Narrative/Cutscene` and `RemoteComm`, attaches matching
  `narrativeVideos` to dialog/cutscene/remotecomm conv JSON, and writes
  `reports/narrative_videos_<LANG>.json` / `.md`.
- `webui/build_runtime_jump_option_route_audit.py`: audits remaining
  `inferredFollowingLines` option groups against nearby Runtime Jump Track
  clips and writes `reports/runtime_jump_option_route_audit_<LANG>.json` /
  `.md`. Use it before promoting any new automatic option-route rule.
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
- `annotate_conv_with_registry.py`: standalone refresher for stamping each
  dialog conv JSON's `_debug` block with a `runtimeRegistry` evidence record
  (registered flag, trunk count, per-trunk line ids from `DialogIdTable`).
  `build_story.py` does this during normal exports; the refresher is useful
  when updating existing conv files without a full rebuild. Pure evidence
  surfacing; no inference.
- `rewrite_scene_order_warnings.py`: one-shot warning rebuild for conv
  JSONs without re-running `build_story.py`. Useful after tightening
  `scene_order_gap_shared.py` criteria.

### IL2CPP-derived evidence (out-of-band)

The C# class hierarchy backing the recovery modes was confirmed by scanning
`global-metadata.dat` from the game's IL2CPP runtime. Relevant runtime types:

- `Beyond.Gameplay.Core.DialogManager` (partial across `.DialogTree.cs`,
  `.Level.cs`, `.LifeCycle.cs`, `.Timeline.cs`) -- routes every dialog load
- `Beyond.Gameplay.Core.DialogTrunkBehaviour` -- per-trunk playback driver
- `Beyond.Gameplay.Core.DialogTimelineManager` -- Timeline-driven path
- `Beyond.Gameplay.Core.DialogTreeController` -- tree/branch navigation
- `Beyond.Gameplay.Core.DialogOptionBehaviour` -- option/choice nodes
- `Beyond.Gameplay.DialogIdTable` -- runtime dialog registry (extracted by
  `recover_dialog_id_registry.py`)

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

Older one-off recovery utilities live in `../memory/scripts_archive/`. UE5
pose-demo helpers now live with the UE project under
`../ue5_zhuangfy_pose_demo 5.3/Scripts/`. Put new experiments in `../scratch/`
and move observations or conclusions to `../memory/` when they need to be kept.
