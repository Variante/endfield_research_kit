# WebUI Notes

The `webui` frontend is intentionally small and static. It reads generated JSON
from `webui/data/`, serves exported media/audio from `export_full/`, and keeps
heavyweight recovery work in the Python builders.

## Browser Files

- `index.html` and `style.css`: shared shell, tabs, and layout.
- `src/core/`: small dependency-free browser utilities used by every tab.
- `src/ui/media_player.js`: shared audio/video control wrapper.
- `app_labels.js`: UI text, labels, and shared story formatting helpers.
- `app_tree.js`: story filters, grouping, sorting, and sidebar tree rows.
- `app.js`: story data loading and conversation rendering.
- `src/features/reference/`: raw localized text-table browser.
- `src/features/updates/`: focused exported text JSON and asset update browser.
- `src/features/game_data/`: local StreamingAssets/Data browser backed by `webui/data/game_data/` indexes.

- `assets.js`: exported asset browser and preview panel.

## Current Scope

- `Story`: language switch, search, foldable filters, a Storyline filter for
  mission/story buckets, Media chips for entries with videos, non-emoji images,
  SNS stickers, or emoji, recovered game-data story-order sorting with compact
  evidence badges in mission lists, conversation detail, summaries,
  option groups, line-order notes, raw source traces, and inline media
  rendering for SNS/content images. Recovery issue/method filters, raw
  source/debug blocks, mission timeline evidence, cutscene debug panels, and
  manual order-edit controls are gated behind the `Show debug info` toggle so
  normal browsing stays compact. Resetting filters returns to Story sort while
  preserving expanded mission groups, and gender variant selection is a header
  toggle. The current chrome uses a light neutral palette with muted teal and
  orange accents while keeping category badges softly color-coded. Narrative
  video blocks show the best
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
  `webui/overrides/options.json`; edit it and refresh the browser,
  no Story rebuild needed. Affected option groups or rows show a manual
  override tag. Mission Timeline Recovery shows the
  quest map track, LevelScript spatial candidates, source-script hints, and
  source-backed scene edges. Timeline action evidence from recovered
  AnimeStudio managed references appears behind `Show debug info` as compact
  line-order agreement, action-kind counts, and per-line staging chips. Cutscene chips now include compact identifying labels, and cutscene
  detail panels expose placement evidence plus variants, paths,
  metadata, videos, audio events, and actor labels to make individual
  cutscenes easier to identify. When `scripts/build_audio.py` has linked
  decoded audio, dialog/cutscene lines with `audioSrc` and recoverable
  cutscene audio events render WebUI audio controls with draggable seek bars;
  playable Story and Updates videos use the same draggable progress control.
- Narrative videos without a resolved story key are emitted as standalone
  `video` story files grouped by mission. Videos that resolve to dialog,
  cutscene, remotecomm, or another story file also attach to that file;
  standalone video rows sort beside the attached file. Timeline / playable
  evidence supplies authored inline placement when available. Manual
  attachments and false-attachment suppressions live in
  `webui/overrides/narrative_videos.json`; attach rules can set `audioFrom`
  to copy source cutscene audio events during audio relink. Videos stay
  available as standalone `video_*` rows after the Story builder is rerun.
- `Text`: raw localized rows from `data/lang/<code>/reference/`, with
  source/table filters and on-demand table loading.
- `Updates`: latest change summary from `data/updates/latest.json`, generated
  by comparing WebUI-facing exported text JSON and exported image/model/video
  assets between saved/current export roots, never generated WebUI files.
- `Data`: local-only browser for `export_full/structured/StreamingAssets/Data`, with lazy-loaded group shards, JSON groups folded by clear directory structure before filename prefixes, parsed text JSON previews, MemoryPack binary `.json` field summaries for known families, video previews for Data media files, PCK/audio package headers, raw bundle/streaming/extend-data headers, and binary header previews for other payloads. Very large raw Data indexes require choosing a group before entries are loaded.
- `Assets`: exported image/model/video/JSON file search, source tag filters,
  metadata, raw links, related files, and previews where the browser supports
  them.

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
- `export_full/recovered/AnimeStudio-cli/timeline_action_evidence.json`:
  builder-side dialog Timeline action evidence from AnimeStudio
  `$animestudio.recoveredManagedReferences.RefIds`. Conversation payloads only
  keep a compact debug slice under `_debug.timelineActions`; the full file is
  the audit source for action-flow line order agreement and per-line action
  class/layout counts.
- `export_full/structured/Audio/<code>/index.json`, shared decoded audio under
  `export_full/structured/Audio/shared/`, and language voice `.wav`/`.wem`
  files: optional audio generated by `scripts/build_audio.py`. Conversation
  payloads keep the per-line `audio` id and gain `audioSrc` only when a
  decoded file exists; cutscene `audioEvents` gain `audioFiles` only when Wwise
  bank metadata links the event to decoded media. Story rebuilds run a
  skip-decode audio relink automatically for languages with decoded audio
  already present.
- `overrides/story_order.json`: user-managed Story sort order. Each
  `missions.<mission>.order` array is the complete file order for that
  mission, and the WebUI treats this override as the only order source in
  `按剧情排序` mode. `export.bat` leaves the file untouched. The OCR pipeline
  writes its proposed order to `data/story_order_ocr.json`; it does not update
  this override. The Story sidebar can save row moves or toggle a mission lock.
  `missions.<mission>.locked: true` freezes a mission so
  OCR proposal generation and browser-side save logic preserve the saved list exactly.
- `data/lang/<code>/reference/`: Text table payloads; persistent rows may share
  streaming payloads or use small overlay files for changed rows.
- `data/game_data/index.json` and `data/game_data/groups/*.json`: ignored, local-only Data tab indexes generated by `scripts/build_data_index.py`. They summarize the moved StreamingAssets/Data tree and do not copy raw Data files.
- `data/assets/story_media.json`: compact Story inline image/video lookup using
  the same `entries` shape as the full asset indexes. The full
  `data/assets/index.json` remains for the Assets tab.

## Inline Media Rules

- SNS emoji assets such as `sns_emoji_*` are rendered as regular inline emoji.
  They stay inline and do not open hover popovers or the full-screen modal.
  Their resolver only uses exact or emoji-family sprite matches; if a matching
  emoji sprite is absent from `story_media.json`, the tag remains unresolved
  instead of borrowing numbered sticker or SNS decoration assets.
- EnvTalk emoji-only rows such as `envEmoji_common_*` render their line-level
  `emoji` fields from the Unity emoji prefab aliases and recovered
  RectTransform layer data in `story_media.json`. Recovered `AnimationClip`
  enter curves drive the initial alpha flicker and squash/stretch when the
  row scrolls into view, and replay on hover/focus. Standalone prefab variants
  are normalized to the same visual scale as the bubble-backed common emoji.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and matching
  `cg_image_*` assets should render with their normal image proportions rather
  than the compact emoji treatment. Exact non-emoji SNS media should not borrow
  numbered sticker, decoration, or emoji fallbacks.
- When a generated line has both an inline `<image=...>` tag and the matching
  `image`/`images` metadata, the inline render is the canonical display; the
  below-line media strip should not repeat the same asset, including when the
  inline tag display is switched to raw text.
- Inline image popovers and the modal preview should stay inside their visual
  border and the viewport.

## Explicit Non-Goals

- no runtime graph atlas or binding explorer in the frontend
- no mission-flow dashboard
- no broad frontend-side recovery workbench; the existing `Show debug info`
  toggle only exposes generated evidence/debug blocks needed to audit the
  current Story view

If one of those views becomes useful again, rebuild it intentionally instead of
letting the browser grow around recovery experiments.
