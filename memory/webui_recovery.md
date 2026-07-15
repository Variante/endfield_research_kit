# WebUI Recovery

The static WebUI is recovered from an installed Endfield client through the
repo's active export/build pipeline. This note keeps the durable recovery
conclusions in one flat file; user-facing usage stays in `README.md`, script
contracts in `scripts/README.md`, and frontend scope in `webui/README.md`.

## Canonical Refresh

From the repo root:

```bat
.\export.bat
python serve.py
```

`export.bat` currently:

1. reuses the existing `export_full/` by default;
2. verifies `export_full/` freshness against the installed game data;
3. rebuilds `export_full/recovered/dialog_id_table_index.json`;
4. rebuilds narrative video/source-link evidence;
5. builds CN Story and Reference data;
6. leaves the OCR-managed Story order override untouched; and
7. leaves asset indexes and CN audio relinking to `export_assets.bat` unless
   `--with-assets` is passed.

Use `--export-from-game` only when refreshing `export_full/` from the installed
game data. Add `--with-assets` when the same command should also run a combined
Story+asset AnimeStudio export, rebuild asset indexes, and decode/relink CN
audio. Without `--export-from-game`, `--with-assets` reuses existing decoded
assets and relinks audio after the Story rebuild. Run `.\build_updates.bat`
separately for the Updates feed. Use `.\export_assets.bat` separately when only
asset indexes or audio need maintenance.

The game does not need to be running. If it is open, close it before export so
files are not locked.

## Generated Data

Expected browser data:

```text
webui/data/
  manifest.json
  index.json
  actors.json
  lang/CN/index.json
  lang/CN/actors.json
  lang/CN/conv/*.json
  lang/CN/mission/*.json
  lang/CN/reference/index.json
  lang/CN/reference/<source>/<table>.json
  updates/latest.json
  assets/index.json
  assets/story_media.json
  assets/videos.json
  assets/bundles/index.json
```

Generated diagnostics and summaries are outputs, not active WebUI inputs.
Keep them under `reports/`.

## Page Contracts

Story:

- Built by `python scripts\story_builder\build.py --languages CN --default-language CN`.
- Uses structured dialog/SNS/radio/remote/env talk tables, recovered
  AnimeStudio/Timeline data, `dialog_id_table_index.json`, and
  `story_source_links.json`.
- Conversation JSON is lazy-loaded from `webui/data/lang/<code>/conv/`.
- Recovery uncertainty should stay visible through warnings. Detailed issue
  filters, source/debug blocks, mission timeline evidence, cutscene debug
  panels, and manual order-edit controls are available from the Story
  `Show debug info` toggle.
- Timeline-inferred option responses are promoted only when source evidence
  binds each option index to a distinct candidate response. The known
  source-backed strict `trunkClipOptionIndex` case is `dlg_c28m3_10` group 1;
  the remaining unresolved groups stay inferred.

Reference:

- Built by the Story builder.
- Keeps rows close to exported structured tables and resolves localized display
  text where possible.
- Avoid story-specific interpretation; tables that should not become Story
  conversations can remain Reference-only.

Updates:

- Built by `.\build_updates.bat` or `python scripts\build_updates.py`.
- Reads the saved previous and current export roots from `endfield_paths.bat`;
  the underlying script falls back to `export_1d2/` and `export_full/` when no
  wrapper configuration or explicit paths are supplied.
- Stores scanner cache and feed history under `.game-data-tracker/`.
- Never point the comparison at `webui/`, `reports/`, `memory/`, `scratch/`, or
  `tmp/`.
- Tracks WebUI-facing exported JSON plus exported image/model/video assets and
  decoded audio by default. Use `--skip-audio-updates` to omit audio while
  retaining other assets, or `--skip-asset-updates` for a text-only feed.
- Use `--baseline-only` only when an intentionally empty first/baseline feed is
  desired. Refresh the cached previous baseline after replacing that folder.

Assets:

- Built by `python scripts\build_assets.py`.
- Indexes exported images, models, materials, videos, story media, related
  files, browser previews, and optional demo bundles.
- Keep heavyweight recovery/debugger views out of the static frontend unless a
  new recovery view is intentionally designed.

Serving and packaging:

- Serve locally with `python serve.py` at `http://127.0.0.1:8765/`, or pass a
  port such as `python serve.py 9000`.
- Before starting a default server, check whether `127.0.0.1:8765` is already
  running and reuse it.
- Package with `python scripts\pack_webui.py` or `.\pack_webui.bat`.
- Package inputs are `serve.py`, `webui/`, and selected media from
  `export_full/`. `reports/`, `scratch/`, and `tmp/` are not package inputs.

## Inline Media Rules

- `sns_emoji_*` assets render as inline emoji. They do not open hover popovers
  or the full-screen modal. Their resolver only uses exact or emoji-family
  sprite matches; missing emoji sprites stay unresolved instead of falling back
  to numbered sticker or SNS decoration assets.
- `envEmoji_common_*` rows render line-level `emoji` fields using recovered
  Unity prefab aliases, RectTransform layer data, and enter animation curves in
  `story_media.json`.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and related
  `cg_image_*` assets keep normal image proportions. Exact non-emoji SNS media
  does not borrow numbered sticker, decoration, or emoji fallbacks.
- When a line has both an inline `<image=...>` token and matching line-level
  `image`/`images` metadata, the inline token owns the visible display and the
  media strip dedupes it.
- Popovers and the modal preview must stay inside their visual frame and the
  viewport.

Regenerate envEmoji prefab data with:

```bat
python scripts\recover_envemoji_prefabs.py
```

## DialogIdTable Registry

The Story builder uses Endfield's runtime dialog registry,
`Beyond.Gameplay.DialogIdTable`, as offline evidence. The source file is
exported to:

```text
export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json
```

The extractor does not fully parse MemoryPack records. It extracts ASCII dialog
and option identifiers, which is enough to build:

```text
export_full/recovered/dialog_id_table_index.json
```

Current baseline:

- `4,496` registered scenes.
- `1,058` scenes with trunk/line decomposition.
- `485` multi-trunk scenes.
- `1,185` scenes with option registrations.
- `3,725` option IDs.
- `0` radio entries; radio remains sourced from `RadioTable.json`.

Registry-backed reason codes:

- `unregisteredScene`: scene key absent from `DialogIdTable`; the runtime has
  no standard dialog entry point for it.
- `dialogTrunkRowIteration`: scene key present, but no Timeline/DialogTree
  source was recovered; row iteration by scene key prefix is the supported
  direct fallback.

Each conversation payload can include `_debug.runtimeRegistry` so downstream
tools can inspect registration, trunk counts, option IDs, and line-count deltas.

If a future update makes the registry extractor report near-zero scenes, inspect
whether `DialogIdTable.json` still contains ASCII `dlg_*` strings. If not, the
table format or encryption changed and needs a targeted offline decoder.

## Game Update Playbook

Most game updates need only:

```bat
.\export.bat --export-from-game
```

Then, if `global-metadata.dat` exists, refresh the IL2CPP metadata canary:

```bat
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --cache-metadata
```

Inspect these drift reports only when the metadata canary changes:

- `reports/option_flow_runtime_metadata_diff.md`
- `reports/option_flow_runtime_metadata_focus_diff.md`
- `reports/option_flow_runtime_metadata_focus.md`
- `reports/option_flow_runtime_metadata.md`

Important interpretation:

- `global-metadata.dat` is useful for runtime vocabulary and method/field drift,
  but it is not the authored story payload.
- A hash-only metadata change with no focus/body-target drift is usually
  harmless.
- A new serialized field on dialog option/tree/timeline focus types is a strong
  candidate for new recovery evidence.
- `DialogTimelineOptionData` still having only `optionIndex`,
  `changeFinishNum`, and `targetFinishNum` means unresolved option targets are
  a runtime method problem, not a hidden serialized field problem.

## Benchmarks

Every `export.bat` run writes a wall-time and process-tree RAM benchmark under
`reports/export_benchmarks/` and updates
`reports/export_benchmark_latest.{md,json}`. Use those files as current truth.
The maintained direct CN Story build is presently on the order of minutes, so
direct runs should have a 10-15 minute shell timeout.

Historical profiling found the main Story-builder costs in repeated file
opens, per-scene regex compilation, mission/LevelScript spatial comparisons,
DialogTree source loading, raw Reference generation, and reopening freshly
written conversation JSON. Prefix/path indexes delivered a large early gain;
future optimization should re-profile before acting because the recovery
surface has since expanded.

A historical EndfieldStudio comparison showed it could rapidly cross-check the
structured Table/Lua/JsonData surface and extract a classified non-material
image subset, but it did not add Story data and omitted material textures,
meshes, AnimationClips, Material JSON, bundle JSON, and AnimeStudio
relationship metadata. It remains a cross-check or preview candidate, not a
replacement for the canonical AnimeStudio export.

## Verification

After a refresh, check:

- Story tab loads and conversation detail lazy-loads.
- SNS emoji stays inline without modal/popover behavior.
- SNS stickers/photos render with normal proportions.
- EnvTalk emoji rows render with recovered prefab layers and replayable enter
  motion.
- Reference tab loads table counts and lazy-loads rows.
- Updates payload tracks the installed `Endfield_Data` root, not generated repo
  folders.
- Assets tab loads counts and can preview images/videos where supported.
- Package dry-run reports expected story media and excludes 3D/model payloads
  by default.

## Story browsing and debug surface

- The Story view now defaults to a quieter browsing surface. The `Show debug
  info` toggle exposes recovery issue/method filters, line-order evidence,
  source/debug panels, mission timeline recovery, cutscene debug detail, and
  manual Story order editing controls.
- Resetting Story filters returns to Story sort and clears chips/search without
  collapsing already-expanded mission groups.
- The WebUI chrome moved to a light neutral palette with muted teal and orange
  accents; kind/category badges remain softly color-coded for scanning.
- The gameplay video story-order matcher now combines OCR segments with
  decoded Story audio-template matches. Audio fingerprints are cached under
  `tmp/ocr/gameplay_video_ocr/audio/`; `au_music*` templates are ignored by default,
  and locked missions are used as threshold controls before applying proposed
  order changes.
- `scripts/download_bilibili_video.py` is the maintained optional intake helper
  for public Bilibili gameplay sources. It writes complete muxed `.mp4` files
  into `videos/`; the OCR worker continues to skip partial `.m4s` and `.lock`
  files.

## Narrative video attachment policy

- Story builder now embeds every resolved narrative-video mapping into its
  resolved conversation, replacing the old dialog plus one-cutscene exception.
  This
  covers cutscene, remotecomm, and any other resolved story file; non-name
  evidence such as `timelinePlayable` supplies authored inline timing when
  available.
- Standalone `video_*` rows are still emitted for direct browsing, but they
  carry `attachTo` for the resolved story key. Story sort uses that attachment
  so the standalone video row stays beside the file where the video is inserted.
- Manual rules in `webui/overrides/narrative_videos.json` cover both known
  filename mismatches and false attachments. `attachInline` manually embeds a
  matching video stem into a target story key, and can set `audioFrom` to copy
  source cutscene audio events into that target during audio relink.
  `suppressInline` keeps known false inline attachments standalone-only.
  `cutscene_e1m3_1` is suppressed for `cs_video_e1m3_1` because the filename
  match should not attach that video to the black-screen cutscene.

## Archive duplicate identity

- `radio_e1m1_2d7` and `nar_media_map01_128_1` have the same localized audio
  transcript. Keep `radio_e1m1_2d7` as the mission `e1m1` row; keep
  `nar_media_map01_128_1` available only from Archive/media grouping and from
  the bidirectional file-page link.
