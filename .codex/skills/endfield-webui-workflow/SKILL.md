---
name: endfield-webui-workflow
description: Maintain Endfield's static WebUI and its generated data. Use for frontend behavior under webui/, Story/Text Tables/Characters/Gameplay/Assets/Updates/Mission Pipeline work, export and asset refreshes, local serving, packaging, update-feed comparisons, and WebUI report or scratch organization.
---

# Endfield WebUI Workflow

Work from the repository root. Read `AGENTS.md` first, then consult only the
active documentation needed for the task:

- `README.md` for user-facing commands and expected workflow.
- `scripts/README.md` for builder and wrapper contracts.
- `webui/README.md` for frontend scope, data layout, and behavior contracts.
- `memory/webui_recovery.md` for durable WebUI status and remaining gaps.

Use the source-graph or option-overrides skill as well when the task requires
graph evidence or edits to `webui/overrides/options.json`.

## Choose the Smallest Workflow

- First-time setup: `setup_first_time.bat`; add `--no-serve` to skip serving.
- Rebuild from an existing, current `export_full/`: `export.bat`.
- Refresh installed-game Story data: `export.bat --from-game`.
- Refresh installed-game Story and assets together:
  `export.bat --from-game --with-assets`.
- Rebuild asset indexes and relink CN audio from existing decoded assets:
  `export_assets.bat`.
- Refresh assets from the installed game when Story is already current:
  `export_assets.bat --from-game`.
- Rebuild only Story/Mission Pipeline during recovery:
  `export.bat --mission-pipeline-only`.
- Rebuild only Mission Pipeline JSON/frontend after generated Story and
  evidence are known current: `export.bat --mission-pipeline-data-only`.
- Build the Updates feed: `build_updates.bat`.
- Build an empty first-time Updates baseline: `build_updates.bat --first-time`.
- Compare named extracted trees: `build_updates.bat OLD NEW`.
- Detect an installed-game patch without publishing:
  `build_updates_by_patch.bat --check`.
- Package the static site: `python scripts\pack_webui.py`.

Use current flag names in docs and commands: `--from-game`, `--with-assets`,
`--focused-assets`, `--default-assets`, `--debug-assets`, `--asset-jobs N`, and
`--webui-jobs N`. Do not introduce retired aliases merely because wrappers
still accept them.

Before a builder reads an existing export, run
`python scripts\verify_export_freshness.py` when freshness is not already
established. If it reports stale installed-game inputs, refresh with
`export.bat --from-game`.

For direct `scripts\story_builder\build.py` runs, allow at least 15 minutes.
For repeated Mission Pipeline work with unchanged Timeline and Table inputs,
use `--reuse-timeline-orders --reuse-reference`; never combine reference reuse
with `--from-game`.

## Recovery Edit Loop

Batch Story recovery changes. Prefer focused tests, direct probes, or
`--mission-pipeline-data-only` during the batch. Run the canonical
`export.bat --mission-pipeline-only` after at least three independently
validated changes or at the end of a coherent 30-60 minute batch.

Run it earlier only for a cross-cutting parser/schema change that focused tests
cannot validate, changed installed-game inputs, known-stale generated inputs,
or an explicit user request. If a validator returns only a generic failure,
improve its deterministic diagnostics before rerunning the expensive pipeline.

## Serving and Browser Checks

Before starting a server, check `http://127.0.0.1:8765/`. Reuse it when it is
already running. Start `python serve.py` only when needed; use another port only
when the user explicitly requests a second server.

Verify behavior proportional to the change. For frontend work, smoke-test the
affected page and nearby navigation. For broad shell or routing changes, check:

- Story, Text Tables, Characters, Gameplay, Assets, and Updates load.
- Mission Pipeline is visible only with `Show debug info`; disabling debug
  while it is active returns to a visible page and normalized URL.
- Story recovery issue and method filters remain visible in normal and debug
  modes; source/evidence/order-edit controls remain debug-only.
- Story reset restores Story sort while preserving expanded mission groups.
- SNS `sns_emoji_*` media stays inline without hover or modal preview.
- Other SNS images and stickers keep normal proportions and bounded previews.

Useful generated fixtures are `test_sns_emojicomment`, `test_sns_sticker`, and
`sns_topic_map02_lv005_12002`.

## Active Frontend Surface

- `webui/index.html`: shell and page containers.
- `webui/style.css`: shared layout and media presentation.
- `webui/app.js`, `app_tree.js`, `app_labels.js`: Story/Text Tables rendering,
  filters, grouping, and labels.
- `webui/reference.js`: raw Text Tables browser.
- `webui/updates.js`: exported game-data change feed.
- `webui/assets.js`: exported asset browser.
- `webui/src/features/characters/`: character identity view and live overrides.
- `webui/src/features/gameplay/`: gameplay datasets and compact sound players.
- `webui/src/features/mission_pipeline/`: debug-only experimental view.

Do not restore retired Factory, World, Presentation, or standalone Combat &
Projectiles pages. Preserve useful projectile and sound information in
Gameplay.

## Overrides

- `webui/overrides/story_order.json` is user-managed and is not regenerated by
  `export.bat`. OCR output is proposal evidence in
  `webui/data/story_order_ocr.json`; locked mission order must remain exact.
- `webui/overrides/options.json` stores manual option positions and responses;
  use the option-overrides skill to edit or validate it.
- `webui/overrides/narrative_videos.json` controls inline attachment,
  suppression, and optional audio inheritance. Rebuild Story after edits.
- Character merge and name overrides are live inputs written through
  `serve.py`; they do not require a rebuild.

## Updates Contract

Build Updates only from the configured previous and current export roots. The
normal feed tracks WebUI-facing exported text plus exported image, model,
video, and decoded audio assets. Never compare `webui/`, `reports/`, `memory/`,
or `scratch/` as game-data roots.

Use `--text-only` for text-only output, `--no-audio` to omit audio while
retaining other assets, `--exact` for content hashing, and
`--full-export-scan` only for a broad audit. Treat pruning as destructive:
preview with `build_updates.bat --prune-old --dry-run` before intentionally
running `build_updates.bat --prune-old`.

## Outputs and Documentation

Keep generated reports in their established topic directories, especially
`reports/export/`, `reports/story/build/`, `reports/story/recovery/`,
`reports/updates/`, `reports/assets/`, and `reports/source_graph/`. Do not add
loose files at `reports/` root or use reports as narrative memory.

Put revisitable experiments under `scratch/<topic>/<task>/` and disposable
work under `tmp/<topic>/<task-or-run>/`; remove completed temporary runs. Fold
durable conclusions into the owning `memory/*.md` topic and keep active docs
concise. When changing stable frontend behavior, update `webui/README.md` and
`memory/webui_recovery.md` as appropriate.
