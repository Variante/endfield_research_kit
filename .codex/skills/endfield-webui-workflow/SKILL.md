---
name: endfield-webui-workflow
description: "Use this skill for the static WebUI workflow: refresh/export, local serving, packaging, Updates tab checks, asset/index refresh, and Story/Reference frontend behavior such as inline SNS image rendering."
---

# Endfield WebUI Workflow

Use this skill when the task is about the static browser under `webui/`, the
export/build/package flow that feeds it, or frontend behavior visible in the
Story, Reference, Updates, or Assets tabs.

This is the first skill to open for requests such as:

- refresh the WebUI from local game data
- debug Story/Reference/Updates/Assets browser behavior
- verify packaging or local serving
- adjust inline image rendering, SNS media presentation, or preview behavior

## Core Commands

From the repo root:

```bat
.\export.bat
.\export.bat --export-from-game
.\build_updates.bat
.\build_updates.bat --init-build
.\export_assets.bat
python serve.py
python serve.py 9000
python scripts\package_webui.py
```

Use `export.bat` as the default story/reference rebuild path from an existing
`export_full/`. It verifies export freshness, rebuilds DialogIdTable and story
source-link evidence, rebuilds CN story/reference data, leaves the
OCR-managed Story order override untouched, and finishes by linking decoded CN
audio by default.
It skips installed-game export, fluffy-dumper structured export, and AnimeStudio
story extraction by default. Pass `--export-from-game` only when installed game
data should be refreshed, the story export tools should run, and CN audio
should be decoded before the final link pass.
Use `build_updates.bat` as the standalone Updates feed comparison. It skips
asset-level update entries by default; pass `--include-asset-updates` only
after refreshing heavy assets. Use `export_assets.bat` for Assets tab indexes;
pass `--export-from-game` to run the heavier image/model/animation decode.

When running `python scripts\story_builder\build.py` directly, use a
longer timeout. The default CN lean build currently takes about 3 minutes on
this checkout, while multi-language builds or forced timeline recovery can take
longer:

```text
timeout_ms >= 900000
```

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
- `webui/app.js`: story/reference data loading and conversation rendering
- `webui/app_tree.js`: filters, grouping, and sidebar tree rows
- `webui/app_labels.js`: labels and shared Story formatting helpers
- `webui/reference.js`: raw table/reference browser
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
- `export.bat` does not regenerate this file; OCR recovery is the source of
  truth for Story sort updates.
- The old generated scene-order evidence asset is retired; the OCR override is
  the only maintained Story order source.
- Gameplay OCR recovery updates the same full mission lists when applied.
- Set `missions.<mission>.locked` to `true` to freeze that mission order;
  OCR recovery and browser-side merge/save logic must preserve the saved order
  exactly.
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
a resolved story key:

```json
{
  "attachInline": {
    "cutscene_example_2": {
      "stems": ["cs_video_other_name_1"],
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

Current Story/Reference inline image behavior:

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

When auditing Story frontend changes, also check that `Show debug info` toggles
line-order evidence, source/debug blocks, mission timeline recovery, cutscene
debug panels, recovery filters, and Story order editing controls without
breaking normal browsing.

## Scope Notes

- Keep root docs focused on active workflow, not investigation conclusions.
- Put durable conclusions in `memory/`, not `reports/`.
- Do not point Updates tracking at `webui/` or other generated repo folders.
- Treat ignored local vendor/tool caches under `tools/` as optional workflow
  dependencies; the tracked helper set is intentionally small.
