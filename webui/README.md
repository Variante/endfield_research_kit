# WebUI Notes

The `webui` frontend is intentionally small and static. It reads generated JSON
from `webui/data/` and keeps heavyweight recovery work in the Python builders.

## Browser Files

- `index.html` and `style.css`: shared shell, tabs, and layout.
- `shared.js`: small dependency-free browser utilities used by the static
  views.
- `app_labels.js`: UI text, labels, and shared story formatting helpers.
- `app_tree.js`: story filters, grouping, sorting, and sidebar tree rows.
- `app.js`: story data loading and conversation rendering.
- `reference.js`: raw localized table/reference browser.
- `updates.js`: original game-data update browser.
- `assets.js`: exported asset browser and preview panel.

## Current Scope

- `Story`: language switch, search, filters, conversation detail, summaries,
  option groups, line-order notes, raw source traces, and inline media
  rendering for SNS/content images.
- `Reference`: raw localized rows from `data/lang/<code>/reference/`, with
  source/table filters and on-demand table loading.
- `Updates`: latest change summary from `data/updates/latest.json`, generated
  by tracking the installed `Endfield_Data` tree and derived exported
  image/model/video asset diffs, never generated WebUI files.
- `Assets`: exported file search, metadata, raw links, related files, and
  previews where the browser supports them.

## Inline Media Rules

- SNS emoji assets such as `sns_emoji_*` are rendered as regular inline emoji.
  They stay inline and do not open hover popovers or the full-screen modal.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and matching
  `cg_image_*` assets should render with their normal image proportions rather
  than the compact emoji treatment.
- Inline image popovers and the modal preview should stay inside their visual
  border and the viewport.

## Explicit Non-Goals

- no runtime graph atlas or binding explorer in the frontend
- no mission-flow dashboard
- no frontend-side recovery debugging surface

If one of those views becomes useful again, rebuild it intentionally instead of
letting the browser grow around recovery experiments.
