# WebUI Notes

The `webui` frontend is intentionally small and static. It reads generated JSON
from `webui/data/` and keeps heavyweight recovery work in the Python builders.

## Browser Files

- `index.html` and `style.css`: shared shell, tabs, and layout.
- `app_labels.js`: UI text, labels, and shared story formatting helpers.
- `app_tree.js`: story filters, grouping, sorting, and sidebar tree rows.
- `app.js`: story data loading and conversation rendering.
- `reference.js`: raw localized table/reference browser.
- `updates.js`: original game-data update browser.
- `assets.js`: exported asset browser and preview panel.

## Current Scope

- `Story`: language switch, search, filters, conversation detail, summaries,
  option groups, line-order notes, and raw source traces.
- `Reference`: raw localized rows from `data/lang/<code>/reference/`, with
  source/table filters and on-demand table loading.
- `Updates`: latest change summary from `data/updates/latest.json`, generated
  by tracking the installed `Endfield_Data` tree and derived exported
  image/model/video asset diffs, never generated WebUI files.
- `Assets`: exported file search, metadata, raw links, related files, and
  previews where the browser supports them.

## Explicit Non-Goals

- no runtime graph atlas or binding explorer in the frontend
- no mission-flow dashboard
- no frontend-side recovery debugging surface

If one of those views becomes useful again, rebuild it intentionally instead of
letting the browser grow around recovery experiments.
