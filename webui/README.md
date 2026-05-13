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

- `Story`: language switch, search, foldable media/recovery issue/method
  filters, a Storyline filter for mission/story buckets, and Media chips for
  entries with videos, non-emoji images, SNS stickers, or emoji,
  conversation detail, summaries,
  option groups, line-order notes, raw source traces, and inline media
  rendering for SNS/content images. Narrative video blocks show the best
  playable active-gender/source variant for each distinct video, without
  counting hidden duplicate format/source variants as extra videos. Story
  search includes option ids as well as line ids/text. Option
  groups recovered from Runtime Jump route tracks preserve option-specific
  route lines, merge shared suffix lines once, and render branch-owned
  follow-up option groups as flat siblings in the owning branch chain instead
  of nesting them inside compact branch rows. Timeline-inferred groups with
  strict `trunkClipOptionIndex` evidence render their per-option candidate
  lines below each option prompt in the same branch-column flow, outside the
  option prompt shell. Single-option follow-ups render
  their recovered next lines as flat line siblings beside the option prompt in
  that same chain, using compact regular-line styling inside branch columns and
  full regular-line styling after the branches merge. When route outcomes prove a
  follow-up group is shared by every option, that shared-continuation evidence
  takes precedence over a single `after` anchor and the group resumes once
  below the option columns. Shared continuation lines resume once after
  branch-local prompts. Branch-owned dialog lines render once in the option path
  and are removed from the trunk even when
  recovered Timeline order disagrees with numeric line suffix order. DialogIdTable
  recovery chips expose runtime trunk line refs and runtime option refs in
  their tooltip when that evidence is available.
- `Reference`: raw localized rows from `data/lang/<code>/reference/`, with
  source/table filters and on-demand table loading.
- `Updates`: latest change summary from `data/updates/latest.json`, generated
  by tracking the installed `Endfield_Data` tree and derived exported
  image/model/video asset diffs, never generated WebUI files.
- `Assets`: exported file search, metadata, raw links, related files, and
  previews where the browser supports them.

## Data Layout

- `data/manifest.json`: language list and build stats.
- `data/lang/<code>/index.json`: lightweight story tree entries only.
- `data/lang/<code>/actors.json`, `missions.json`, and `search.json`: lazy
  sidecars for display names and full-text search.
- `data/lang/<code>/conv/` and `mission/`: conversation and mission payloads
  loaded on demand.
- `data/lang/<code>/reference/`: Reference tables; persistent rows may share
  streaming payloads or use small overlay files for changed rows.
- `data/assets/story_media.json`: compact Story inline image/video lookup using
  the same `entries` shape as the full asset indexes. The full
  `data/assets/index.json` remains for the Assets tab.

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
