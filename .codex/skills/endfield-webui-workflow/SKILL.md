---
name: endfield-webui-workflow
description: Use this skill for the static WebUI workflow: refresh/export, local serving, packaging, Updates tab checks, asset/index refresh, and Story/Reference frontend behavior such as inline SNS image rendering.
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
.\export.bat --init-build
.\export.bat --fast-assets
python serve.py
python serve.py 9000
python scripts\webui\package_webui.py
```

Use `export.bat` as the default browser-data refresh path. It exports only the
active WebUI inputs, verifies export freshness, rebuilds the Updates feed,
rebuilds CN story/reference data by default, and refreshes the asset index.

When running `python scripts\webui\build_story.py` directly, use a long timeout
because it commonly takes about 30 minutes:

```text
timeout_ms >= 2700000
```

## Frontend File Map

- `webui/index.html`: shell and tab containers
- `webui/style.css`: shared layout and inline media presentation
- `webui/app.js`: story/reference data loading and conversation rendering
- `webui/app_tree.js`: filters, grouping, and sidebar tree rows
- `webui/app_labels.js`: labels and shared Story formatting helpers
- `webui/reference.js`: raw table/reference browser
- `webui/updates.js`: installed-game update feed
- `webui/assets.js`: exported asset browser

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
- `memory/webui_recovery/story_page.md`

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

## Scope Notes

- Keep root docs focused on active workflow, not investigation conclusions.
- Put durable conclusions in `memory/`, not `reports/`.
- Do not point Updates tracking at `webui/` or other generated repo folders.
