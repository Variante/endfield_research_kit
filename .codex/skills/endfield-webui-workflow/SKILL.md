---
name: endfield-webui-workflow
description: "Use this skill for the static WebUI workflow: refresh/export, local serving, packaging, Updates tab checks, asset/index refresh, generated report and scratch/tmp organization, and Story/Text Tables frontend behavior such as inline SNS image rendering."
---

# Endfield WebUI Workflow

Use this skill when the task is about the static browser under `webui/`, the
export/build/package flow that feeds it, or frontend behavior visible in the
Story, Text Tables, Updates, or Assets tabs.

This is the first skill to open for requests such as:

- refresh the WebUI from local game data
- debug Story/Text Tables/Updates/Assets browser behavior
- verify packaging or local serving
- adjust inline image rendering, SNS media presentation, or preview behavior

## Core Commands

From the repo root:

```bat
notepad endfield_paths.bat
.\setup_first_time.bat
.\export.bat
.\export.bat --mission-pipeline-only
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
.\export.bat --with-assets
.\export.bat --full-source-graph
.\export.bat --export-from-game
.\build_updates.bat
.\build_updates.bat --init-build
.\build_updates_by_patch.bat --init-baseline
.\build_updates_by_patch.bat --check
.\build_updates_by_patch.bat
.\export_assets.bat
python serve.py
python serve.py 9000
python scripts\pack_webui.py
```

Use `setup_first_time.bat` as the user-facing all-in-one first-time setup path
from an installed game client. Edit `endfield_paths.bat` first for repeated
local paths. The setup initializes/builds AnimeStudio, verifies the integrated
AnimeStudio VFS/audio commands, runs the installed-game Story export, prints
optional Assets/media and Updates follow-up commands, then starts or reuses the
default WebUI server unless `--no-serve` is passed.

Use `export.bat` as the default Story/Text Tables rebuild path from an existing
`export_full/`. It verifies export freshness with a fast required-output
presence check, refreshes DialogIdTable, narrative video binding, and story
source-link evidence in parallel, rebuilds CN Story/Text Tables data, leaves the
user-managed Story order override untouched, and leaves decoded CN audio relinking
to `export_assets.bat` unless `--with-assets` is passed.
It skips installed-game export and AnimeStudio story extraction by default. Pass `--export-from-game` only when installed game
data should be refreshed and the story export tools should run. Pass
`--with-assets` when the same command should also rebuild asset indexes and
relink/decode CN audio; combining it with `--export-from-game` runs one
AnimeStudio Story+asset export.
The default graph stage keeps only exact original AssetMap rows needed by WebUI
material/shader/texture/FMV edges. Use `--full-source-graph` for exhaustive
Unity-object/PathID investigation. Use `--mission-pipeline-only` for recovery
iteration when Story evidence, CN Story/Text Tables, and Mission Pipeline are
the only requested outputs. Use `--mission-pipeline-data-only` when those Story
outputs are already current and only Mission Pipeline JSON/frontend work needs
refreshing; it skips freshness, evidence, Story, semantic-view, and source-graph
stages.
When Story relations changed but the recovered Timeline and exported Table
inputs did not, add `--reuse-timeline-orders --reuse-reference`. The latter
validates the current localized reference index and every indexed file before
preserving the existing Text Tables payload. Both reuse flags are rejected for
installed-game refreshes.
Use `build_updates.bat` as the standalone Updates feed comparison. It reads
previous/current export roots from `endfield_paths.bat` by default and tracks
WebUI-facing exported text JSON plus exported image/model/video assets and
decoded audio. Asset modifications use fast size fingerprints; pass
`--hash-asset-updates` when same-size binary modifications must be detected,
`--skip-audio-updates` to omit decoded audio while keeping other asset entries,
or `--skip-asset-updates` for a text-only feed. Preview previous-export pruning
with `--dry-run-prune-previous-export-untracked`; use
`--prune-previous-export-untracked` only when intentionally deleting old export
files outside the focused tracked scope. Use `export_assets.bat` for Assets tab
indexes and CN audio relinking when Story is already current; pass
`--export-from-game` to run the full WebUI-facing image/model asset export plus
`Material` JSON and decode CN audio. Prefer
`export.bat --export-from-game --with-assets` when Story and assets both need an
installed-game refresh. Pass `--webui-assets` when only WebUI-referenced
Texture2D media is needed, or `--debug-assets` for exhaustive AnimeStudio
conversion/JSON diagnostics. The exporter default is
`--animestudio-type-job-mode auto`: it merges map-filtered JSON, runs broad Story
JSON types sequentially in isolated processes, and leaves asset conversion
sharded.

For a one-off diff between two already extracted versions that should directly
generate the WebUI Updates page, run:

```bat
.\build_updates.bat --previous-export-root OLD --export-root NEW --refresh-previous-export-baseline
```

The command writes `webui/data/updates/latest.json` and the detailed reports
under `reports/updates/`. `build_updates_by_patch.bat --check` is detection-only;
the default patch mode invokes the feed builder after publishing archive/current.
Use `--full-export-scan` only for a broad audit, not for the normal WebUI-focused
feed.

Use `build_updates_by_patch.bat --init-baseline` to seed the separate
original-data VFS snapshot from only the current installed version and current
export. Default patch mode preserves published state for logical no-change,
VFS-version-only changes, and chunk-only repacks. Logical changes are built in a
complete sibling staging tree: changed Table/JsonData/Video/AuditVideo/Lua files
are dumped selectively, broad AnimeStudio/audio work runs only for affected
blocks, the installed snapshot is revalidated, then previous/current folders
are renamed on the same volume. WebUI data and the Updates feed are rebuilt
before the candidate baseline is accepted. Handled post-rotation failures
restore the prior export/WebUI data and retain the failed new tree for review.

When running `python scripts\story_builder\build.py` directly, use a
longer timeout. The default CN lean build currently takes about 3 minutes on
this checkout, while multi-language builds or forced timeline recovery can take
longer:

```text
timeout_ms >= 900000
```

## Report Organization

Keep `reports/` free of loose files. Use these topic roots:

- `reports/export/`: latest export summary, `runs/<timestamp>/` logs, and
  `benchmarks/`.
- `reports/story/build/`: normal Story build reports, including source links,
  narrative videos, mission timeline recovery, scene-order gaps, and inferred
  option anchors.
- `reports/story/recovery/`: manual Story recovery audits; option evidence
  belongs in `reports/story/recovery/options/`.
- `reports/updates/`: `game-data-change-summary.json/.md`.
- `reports/assets/`: hashes and asset diagnostics.
- `reports/source_graph/`, `reports/mission_order/`,
  `reports/playable_director/`, and `reports/gameplay_video_ocr/`: established
  graph and recovery topic roots.

Every `export.bat` run keeps the latest benchmark and up to ten historical
benchmark runs per label. Installed-game exporter runs keep five timestamped
run directories by default. `build_updates.bat --init-build` removes any stale
comparison summary because a baseline-only build intentionally has no change
report.

Treat canonical Story, mission-order, playable-director, OCR, option, and
source-graph reports as possible downstream inputs. Before deleting one, search
for readers in `scripts/` and `tools/endfield_source_graph.py`. Delete
superseded timestamp runs, scoped experiments, and temporary reports; move
durable conclusions to `memory/` and disposable work to `scratch/` or `tmp/`.
Never use `reports/` as an Updates comparison root.

Before rebuilding Story or report consumers from `export_full/`, run
`python scripts\verify_export_freshness.py`. If it reports stale installed-game
sources, refresh with `export.bat --export-from-game` first.

## Scratch And Temporary Work

Keep the roots of `scratch/` and `tmp/` free of loose entries. Put revisitable
experiments under `scratch/<topic>/<task>/` and disposable intermediates under
`tmp/<topic>/<task-or-run>/`. Prefer `webui`, `story`, `assets`, `animestudio`,
`source_graph`, `game_data`, `updates`, `ocr`, or `reverse_engineering` as the
topic; use `tests`, `tools`, or `misc` only when nothing else fits.

Delete completed `tmp/` runs after validation. Promote reusable helpers out of
`scratch/` into maintained code, move durable conclusions to `memory/`, and
delete superseded experiments. For a self-contained Unity/UE project, keep its
temporary work inside that project instead of the repo-root work directories.

## Recovery Investigation Commands

Use these for story recovery quality work before changing Story builder rules:

```bat
python tools\endfield_source_graph.py story dlg_c17m1_5 --limit-lines 8
python tools\endfield_source_graph.py issues --code inferredOptionResponse --limit 20
python scripts\story_recovery\build_runtime_jump_option_route_audit.py --language CN --story dlg_e1m1_5 --group 3
python scripts\story_recovery\build_option_playable_semantics_audit.py --language CN --only-interesting
python scripts\story_recovery\build_option_logic_id_audit.py --language CN
python scripts\story_recovery\build_dialog_tree_option_route_audit.py --language CN
python scripts\story_recovery\build_timeline_option_flow_audit.py --language CN
python scripts\story_recovery\build_timeline_binding_audit.py --language CN --only-interesting
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --cache-metadata
python tools\endfield-il2cpp\map_body_targets_to_gameassembly.py
python scripts\download_bilibili_video.py --dry-run
```

`build_option_playable_semantics_audit.py` checks remaining inferred option
responses against decoded `DialogOptionPlayableAsset` fields. The most useful
current queue is groups with non-default `logicId`; default-only rows and
clip-placement-only rows should be treated as lower-signal until new evidence
appears.

`build_option_logic_id_audit.py` checks whether those `logicId` values have
strong external references in mission/level-script sources. Same-mission
matches would be promising; table/config-only matches are weak unless another
source links them to the dialog.

`build_dialog_tree_option_route_audit.py` checks the unresolved option-response
queue against decoded AnimeStudio DialogTree routes, scene links, fragments,
and cinematic wrappers. Current CN results show most remaining cases are
cinematic-tree-to-Timeline only, so the next high-value work is Timeline/runtime
option target decoding rather than looser DialogTree promotion.

`build_timeline_option_flow_audit.py` checks unresolved option responses
against raw Timeline trunk clips. Current CN results show one promotable
`trunkClipOptionIndexRoute` case (`dlg_c28m3_10` group 1) and many default raw
`optionIndex=0` adjacent layouts that should not be promoted without new
runtime evidence. It resolves `misc_dlg_*` WebUI keys back to their underlying
`dlg_*` Timeline entries, so those scenes should not be treated as missing
Timeline data.

`build_timeline_binding_audit.py` checks the same queue against Timeline track
and binding layout. Current CN results show only one option-named track mapping
(`dlg_c28m3_10` group 1, candidates on `Option 1` / `Option 2` tracks), which
supports the existing raw trunk clip mapping. The rest are either a single
trunk track or option-clip tracks that do not match candidate response tracks,
so track layout should be treated as negative evidence unless this audit finds
new option-named or binding-split cases after future exports.

`catalog_option_flow_metadata.py` is the offline IL2CPP metadata pass for the
next backend-only recovery step. It validates/caches `global-metadata.dat` when
available, parses its tables instead of doing a raw string scan, then reports
option-flow fields and method-body targets. Current useful targets include
`DialogTimelineManager._SelectIndexInTimeline`,
`TryTriggerTrunkBindingOption`, `SetDialogOption`, `OnJumpForward`,
`DialogOptionBehaviour.InitDialogOptions`, `DialogTrunkBehaviour.InitDialogTrunk`,
and DialogTree `GetNextIndex` / `SelectIndex` methods.

`download_bilibili_video.py` is the optional intake helper for gameplay-video
OCR/audio story-order work. It writes flat `.mp4` files under `videos/` from
Bilibili BVIDs, uses browser-exported cookies, resumable parts, lock files,
and `ffmpeg`, and requires the external `requests` package. It is not part of
the stdlib-only export path.

## Frontend File Map

- `webui/index.html`: shell and tab containers
- `webui/style.css`: shared layout and inline media presentation
- `webui/app.js`: story/text-table data loading and conversation rendering
- `webui/app_tree.js`: filters, grouping, and sidebar tree rows
- `webui/app_labels.js`: labels and shared Story formatting helpers
- `webui/reference.js`: raw text-table browser
- `webui/updates.js`: installed-game update feed
- `webui/assets.js`: exported asset browser

## Runtime Overrides

Use runtime override files under `webui/overrides/` for user-edited Story
fixes that should be easy to maintain by hand. Scene order has a dedicated
full-list file that is maintained by the OCR story-order workflow.

Scene order lives in `webui/overrides/story_order.json`. Each mission has one
complete ordered file-key list:

```json
{
  "missions": {
    "e0m0": {
      "order": [
        "scene_key_1",
        "scene_key_2"
      ],
      "locked": true,
      "level": "level_id",
      "levels": ["level_id"]
    }
  }
}
```

Rules:

- `missions.<mission>.order` is the complete Story file order for that mission.
- `export.bat` does not regenerate this file; active Story sort is user-managed
  in this override.
- The old generated scene-order evidence asset is retired; the active override
  is the maintained Story order source, while OCR proposals are comparison
  evidence in `webui/data/story_order_ocr.json`.
- Gameplay OCR recovery writes proposed full mission lists for review, not to
  this override.
- Set `missions.<mission>.locked` to `true` to freeze that mission order;
  OCR proposal generation and browser-side merge/save logic must preserve the
  saved order exactly.
- The Story sidebar can save row moves from Story sort mode through `serve.py`.
  Mission-group lock/unlock buttons can toggle `locked` from the WebUI.
  These editing controls are visible behind `Show debug info`.
- Rows do not show a manual scene-order tag; the editable file is the order.

Option overrides live in `webui/overrides/options.json`. Option
position overrides use the same anchor idea, with dialog line ids as anchors and
option group numbers as moved values:

```json
{
  "scenes": {
    "dlg_example_1": {
      "positions": {
        "after": {
          "dlg_example_1_006": ["1"]
        },
        "pre": ["2"]
      },
      "responses": {
        "option_dlg_example_1_1_001": ["dlg_example_1_007"]
      },
      "notes": {
        "1": "Short factual note."
      }
    }
  }
}
```

For option overrides, `positions.after` moves option groups after a line anchor,
`positions.pre` renders groups before the scene, and `responses` maps option ids
directly to branch line ids. Moved/overridden option groups keep the visible
manual override tag.

Narrative video inline-attachment overrides live in
`webui/overrides/narrative_videos.json`. Use `attachInline` when a filename
stem is known to belong to a different story key, and use `suppressInline`
when a video should remain as a standalone `video_*` row but must not attach to
a resolved story key. Add `audioFrom` to an `attachInline` rule when the target
cutscene should inherit audio events from another cutscene during audio relink:

```json
{
  "attachInline": {
    "cutscene_example_2": {
      "stems": ["cs_video_other_name_1"],
      "audioFrom": ["cutscene_example_1"],
      "note": "Short factual reason."
    }
  },
  "suppressInline": {
    "cutscene_example_1": {
      "stems": ["cs_video_example_1"],
      "note": "Short factual reason."
    }
  }
}
```

These overrides are applied by the Story builder, so run `export.bat` or
`python scripts\story_builder\build.py --languages CN --default-language CN`
after editing them.

## Inline Image Rules

Current Story/Text Tables inline image behavior:

- SNS emoji images such as `sns_emoji_*` are treated as regular inline emoji.
  They render inline, do not open the modal preview, and do not show a hover
  popover.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and related
  `cg_image_*` assets render with normal image proportions instead of the small
  circular/emoji treatment.
- Preview popovers and the full-screen image modal must stay within the
  viewport and their visual frame.

When touching this area, keep the behavior documented above in sync across:

- `webui/app.js`
- `webui/style.css`
- `webui/README.md`
- `memory/webui_recovery.md`

## Verification

For WebUI-only frontend changes, prefer a quick local browser smoke test:

```bat
python serve.py
```

Then verify:

- Story tab still loads
- SNS emoji stays inline without popover/modal behavior
- SNS stickers and SNS images render with normal rectangular proportions
- preview popovers and the modal image do not overflow their border or the
  viewport

Useful built-in fixture conversations already generated in the CN data:

- `test_sns_emojicomment`
- `test_sns_sticker`
- `sns_topic_map02_lv005_12002`

When auditing Story frontend changes, check that recovery issue and method
filters remain visible in both normal and debug modes. `Show debug info` should
toggle line-order evidence, source/debug blocks, mission timeline recovery,
cutscene debug panels, and Story order editing controls without breaking normal
browsing.

## Scope Notes

- Keep root docs focused on active workflow, not investigation conclusions.
- Put durable conclusions in `memory/`, not `reports/`.
- Do not point Updates tracking at `webui/` or other generated repo folders;
  compare saved/current export roots instead.
- Treat ignored local vendor/tool caches under `tools/` as optional workflow
  dependencies; the tracked helper set is intentionally small.
