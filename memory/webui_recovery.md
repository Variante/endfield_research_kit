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

1. exports browser-needed game data with `scripts/export_full_from_game.py`;
2. verifies `export_full/` freshness against the installed game data;
3. rebuilds `export_full/recovered/dialog_id_table_index.json`;
4. rebuilds story source links;
5. rebuilds the installed-game Updates feed;
6. builds CN Story and Reference data;
7. rebuilds the asset indexes.

Use `--init-build` for an intentional first/baseline build, `--fast-assets`
when existing asset indexes can be reused, and `--skip-export-full` when
rebuilding from an existing fresh `export_full/`.

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
- Recovery uncertainty should stay visible through warnings, issue filters,
  and source/debug blocks.
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

- Built by `python scripts\build_updates.py`.
- Tracks only the installed game data root:
  `D:\Program Files\Endfield Game\Endfield_Data`.
- Stores state under `.game-data-tracker/`.
- Never point the tracker at `webui/`, `export_full/`, `reports/`, `memory/`,
  `scratch/`, or `tmp/`.
- Asset-level entries derived from `export_full/` are reported only when the
  original game-data tracker reports a real installed-data change.
- Zero-change reruns preserve or restore the latest non-empty feed snapshot.

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
- Package with `python scripts\package_webui.py` or `.\package_webui.bat`.
- Package inputs are `serve.py`, `webui/`, and selected media from
  `export_full/`. `reports/`, `scratch/`, and `tmp/` are not package inputs.

## Inline Media Rules

- `sns_emoji_*` assets render as inline emoji. They do not open hover popovers
  or the full-screen modal.
- `envEmoji_common_*` rows render line-level `emoji` fields using recovered
  Unity prefab aliases, RectTransform layer data, and enter animation curves in
  `story_media.json`.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and related
  `cg_image_*` assets keep normal image proportions.
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
.\export.bat
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

Useful current measurements:

- `.\export.bat --fast-assets` with no content update took about `41.1`
  minutes on 2026-05-12. The two structured dumps cost about `17.1` minutes.
- Before the Story builder speed pass, a CN build took about `807` seconds.
- Prefix-index lookup and path-rendering caches reduced the CN build to about
  `74` seconds on the same machine.

Likely remaining speed targets:

- structured-dump caching or skip logic in `export_full_from_game.py`;
- AnimeStudio MonoBehaviour file discovery;
- raw Reference bundle generation across hundreds of tables;
- mission timeline recovery.

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
