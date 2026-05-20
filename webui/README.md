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
  filters, a Storyline filter for mission/story buckets, Media chips for
  entries with videos, non-emoji images, SNS stickers, or emoji, recovered
  game-data story-order sorting with compact evidence badges in mission lists,
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
  their tooltip when that evidence is available. Known option placement or
  inferred-response gaps can be covered for WebUI display only through
  `scripts/story_builder/manual_option_overrides.json`; affected option groups
  or rows show a manual override tag. Mission Timeline Recovery shows the
  quest tree, quest map track, scene chunks, diagnostic weak subchunks,
  LevelScript spatial candidates, source-script hints, and source-backed scene
  edges. Cutscene chips now include compact identifying labels, and cutscene
  detail panels expose placement/chunk/subchunk evidence plus variants, paths,
  metadata, videos, audio events, and actor labels to make individual
  cutscenes easier to identify.
- Narrative videos without non-name binding evidence are emitted as standalone
  `video` story files grouped by mission. Videos with recovered Timeline /
  playable evidence stay attached to their proven dialog or cutscene.
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
- `data/lang/<code>/narrative_video_evidence.json`: timeline-backed video to
  WebUI conversation evidence. These rows require recovered
  `BeyondFMVPlayableAsset` / Timeline sources, including gameplay cutscene
  playables from AnimeStudio `json_by_type/MonoBehaviour`; heuristic filename
  matches are not recorded as proof.
- `data/assets/story_order.json`: recovered mission entry order from
  original/decodeable game data. Strong rows carry MissionRuntime/property,
  LevelScript record, or levelseq evidence; weaker rows are kept as
  fallbacks and marked in the UI tooltip. Entries can also expose decoded
  LevelData file/offset and neighboring script ids as grouping diagnostics;
  those fields are not treated as playback-order proof. When a source
  LevelScript is known, entries also show raw binary LevelScriptData checks
  such as serialized member count, verified scriptId offset, and decoded
  top-level startType where the tail layout is currently understood. Compact
  incoming/outgoing cross-script references are shown as control diagnostics
  only, not as ordering edges. When the binary record is a decoded
  script-pointer payload, the compact ref label also shows the raw flag byte;
  the flag is diagnostic until the action opcode is named. Map-position
  diagnostics from decoded LevelScript vectors matched against quest pins are
  also exposed for source-backed rows; these support spatial/quest vicinity
  and are not standalone chronological proof. A narrow builder rule can use
  coherent direct same-script candidates to override weak suffix fallback for a
  raw-ordered source-script cluster, and another constrained rule can correct
  numeric levelseq over-anchoring when an incoming cross-file edge and
  predecessor-script spatial candidate agree. Compact
  mission timeline scene edges are exposed beside entries so same-script
  file-order evidence can be checked from the Story tooltip; direct same-script
  edges are also applied as local ordering constraints.
- `data/lang/<code>/reference/`: Reference tables; persistent rows may share
  streaming payloads or use small overlay files for changed rows.
- `data/assets/story_media.json`: compact Story inline image/video lookup using
  the same `entries` shape as the full asset indexes. The full
  `data/assets/index.json` remains for the Assets tab.

## Inline Media Rules

- SNS emoji assets such as `sns_emoji_*` are rendered as regular inline emoji.
  They stay inline and do not open hover popovers or the full-screen modal.
- EnvTalk emoji-only rows such as `envEmoji_common_*` render their line-level
  `emoji` fields from the Unity emoji prefab aliases and recovered
  RectTransform layer data in `story_media.json`. Recovered `AnimationClip`
  enter curves drive the initial alpha flicker and squash/stretch when the
  row scrolls into view, and replay on hover/focus. Standalone prefab variants
  are normalized to the same visual scale as the bubble-backed common emoji.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and matching
  `cg_image_*` assets should render with their normal image proportions rather
  than the compact emoji treatment.
- When a generated line has both an inline `<image=...>` tag and the matching
  `image`/`images` metadata, the inline render is the canonical display; the
  below-line media strip should not repeat the same asset, including when the
  inline tag display is switched to raw text.
- Inline image popovers and the modal preview should stay inside their visual
  border and the viewport.

## Explicit Non-Goals

- no runtime graph atlas or binding explorer in the frontend
- no mission-flow dashboard
- no frontend-side recovery debugging surface

If one of those views becomes useful again, rebuild it intentionally instead of
letting the browser grow around recovery experiments.
