# Endfield Research Kit

Endfield Research Kit is a local research workspace maintained around two active
surfaces:

- `webui/`: a static browser for story, reference text, exported assets, and
  source-data update diffs.
- `unity_endfield_graph_shader_lab/`: the Unity 2022.3 Endfield Character
  Recovery Lab for recovered character shaders, render checks, meshes, and
  animation playback.

This repository is for research and study purposes only. It is intended for
local inspection of data from a legally obtained installation, with generated
outputs kept narrow and reproducible. Do not use it to redistribute proprietary
game content or bypass the rights of the original creators.

Most notes, recovery logic, and generated outputs here were produced with LLM
assistance, so treat them as working research artifacts rather than authoritative
facts. Expect mistakes and verify conclusions against the original data.

Older exploration notes, demo status snapshots, and one-off recovery utilities
belong under `memory/` so the repo root stays focused.

## Community Resources

Special thanks to these LLM-driven community wiki projects. They are not
affiliated with this project, but they are excellent resources and well worth
checking out:

- [AIC | Endfield Industrial Terminal](https://endfield.prts.chat/) is an
  AI-assisted Endfield wiki/reference project for checking public game
  knowledge and browsing organized Endfield material.
- [PRTS | Rhodes Island Terminal](https://prts.chat/) is an AI-assisted
  Arknights wiki/reference project for checking public game knowledge across
  the broader Arknights setting.

If you are looking for conversational public wiki/reference material rather
than this local research workspace, start with those sites and still verify
important details against primary sources.

## Quick WebUI Refresh

From the repo root:

```bat
.\export.bat
python serve.py
```

Then open `http://127.0.0.1:8765/`.

The local server sends no-store headers, and the Story browser revalidates
generated JSON when loading or reselecting conversations, so a browser reload
after `export.bat` should show the refreshed data without changing ports.

The current Story/Reference inline media behavior treats SNS emoji images such
as `sns_emoji_*` as regular inline emoji with no popup/modal preview, while
non-emoji SNS media such as `sns_image_*` and `sns_sticker_*` render at normal
image proportions with bounded hover/modal previews.

`export.bat` is the normal browser-data refresh. It runs:

- `scripts/export_full_from_game.py --skip-raw-vfs --skip-source-inventory`
- `scripts/verify_export_freshness.py`
- `scripts/story_builder/dialog_registry.py --quiet`
- `scripts/story_builder/video_bindings.py`
- `scripts/story_builder/source_links.py`
- `scripts/build_updates.py`
- `scripts/story_builder/build.py --languages CN --default-language CN`
- `scripts/build_assets.py`

For an initial build where there is no useful update history yet:

```bat
.\export.bat --init-build
```

For faster local refreshes that can reuse the existing asset search indexes and
skip demo bundle zip generation:

```bat
.\export.bat --fast-assets
```

For a WebUI rebuild from an existing export, skip the main extraction step while
still checking that `export_full/` matches the installed game data:

```bat
.\export.bat --skip-export-full
```

CN is exported by default. To build more languages after the export:

```bat
python scripts\story_builder\build.py --languages CN EN JP --default-language CN
```

Package a shareable browser build with:

```bat
python scripts\package_webui.py
```

or:

```bat
.\package_webui.bat
```

Packaging writes two zips by default: a smaller story zip with the WebUI,
story/reference text data, and emoji images, plus a companion assets zip with
larger story images and videos. Extract the story zip first, then extract the
assets zip into the same directory when those media files are needed.

## Update Tracking

The Updates tab is built by:

```bat
python scripts\build_updates.py
```

It tracks only the original installed data tree, defaulting to:

```text
D:\Program Files\Endfield Game\Endfield_Data
```

It does not scan `webui/`, `memory/`, or other generated repo files, so WebUI
edits do not appear as upstream data changes. Tracker state lives in
`.game-data-tracker/`. The first scan initializes the baseline and writes an
empty update feed; later scans show only changes from the original source tree.
Local CrashSight telemetry files under `Plugins/x86_64/wesight/crashsight_data/`
are ignored because they churn during normal local runs and are not installed
content updates.

The same builder also diffs exported image/model/video assets from
`export_full/` and adds those asset-level changes to the Updates page. Those
asset diffs are only reported when the `Endfield_Data` tracker sees a real
source-data change; export or WebUI rebuild noise without a source-data change
is silently absorbed into the asset baseline.

If the tracker is run again after a game update has already been recorded,
`build_updates.py` preserves the last non-empty feed instead of overwriting the
Updates page with a zero-change report. It can also restore that feed from
`.game-data-tracker/history/` if the current `latest.json` was already blanked.
Full non-empty feed snapshots are also kept there as `update-feed-*.json`, so
future recovery keeps asset-level entries as well as game-data entries.

Write an empty baseline feed for a first-time or baseline-only build:

```bat
python scripts\build_updates.py --baseline-only
```

If you still want game-data changes but not the exported asset diff, use
`--skip-asset-updates`.

Reset the baseline only when you intentionally want to treat the current
installed game files as the new "no changes yet" state:

```bat
python scripts\build_updates.py --reset-baseline
```

The WebUI feed is written to `webui/data/updates/latest.json`.

## Export Freshness

`export.bat` verifies that `export_full/` still matches the installed
`Endfield_Data` source fingerprints before running the long WebUI builders. To
check that guard directly:

```bat
python scripts\verify_export_freshness.py
```

If it reports stale source roots, rerun `.\export.bat` so future game-data
changes are re-extracted before the Story builder or asset indexing reads
`export_full/`.

`.\export.bat --skip-export-full` uses this same guard before it rebuilds the
WebUI from existing `export_full/` data.

## What The Browser Reads

The active WebUI builders use:

- `export_full/structured/StreamingAssets/Table/*.json`
- recovered AnimeStudio text and metadata under `export_full/recovered/`
- exported image/model/material outputs under
  `export_full/recovered/AnimeStudio-cli/<source>/`
- generated WebUI data under `webui/data/`

The current `export.bat` skips raw VFS output and source inventory because the
browser does not need them.

Generated WebUI outputs include:

- `webui/data/manifest.json`
- `webui/data/lang/<code>/index.json`
- `webui/data/lang/<code>/conv/*.json`
- `webui/data/lang/<code>/mission/*.json`
- `webui/data/lang/<code>/reference/**`
- `webui/data/assets/index.json`
- `webui/data/updates/latest.json`

Asset indexing scans only the active WebUI export roots.

## Unity Character Recovery Lab

The Unity project lives in `unity_endfield_graph_shader_lab/`.

Common commands:

```bat
cd unity_endfield_graph_shader_lab
.\open_character_recovery_lab.bat
.\build_all_character_recovery.bat
```

See `unity_endfield_graph_shader_lab/README.md` for the full character recovery
workflow. In this checkout, Unity recovery helpers are project-local under
`unity_endfield_graph_shader_lab/` rather than active files under `scripts/`.

## Tool Pointers

The active workflows use Python stdlib scripts plus a small tracked helper set
under `tools/`. The `tools/` directory is ignored by default, so large vendor
checkouts and generated tool caches can exist locally without becoming part of
the maintained repo surface.

Tracked helpers:

- `tools/endfield_asset_map_filter.py`: local helper maintained in this repo
  for asset-map filtering experiments.
- `tools/endfield_source_graph.py`: local SQLite source-graph builder that
  connects story, reference text, tables, audio, videos, assets, character
  recovery manifests, material links, and optional AnimeStudio asset maps.
  Outputs are written under `reports/source_graph/`. Use
  `python tools\endfield_source_graph.py build --skip-asset-maps` for quick
  iteration, `python tools\endfield_source_graph.py build` for the full graph,
  and `python tools\endfield_source_graph.py query zhuangfy --limit 20` for a
  simple search.
- Source-graph follow-up tools: `tools/endfield_voice_audio_linker.py`,
  `tools/endfield_story_branch_resolver.py`,
  `tools/endfield_map_level_indexer.py`, and
  `tools/endfield_semantic_update_classifier.py` build richer reports under
  `reports/source_graph/`.
- `tools/endfield-il2cpp/`: tracked offline IL2CPP metadata helpers. The
  catalog validates/caches `global-metadata.dat`, the mapper links focused
  method targets to `GameAssembly.dll` addresses, and both write option-flow
  evidence reports. These are out-of-band diagnostics, not normal
  `export.bat` steps.

Optional local tool/vendor directories may also exist under ignored `tools/`,
including AnimeStudio, Ruri.ShaderDecompiler, FractalMiner, TypeTree,
TypeTreeDumps, ACL helpers, and dumping support. Keep their generated outputs
local; document only the workflow contract that depends on them.

Use `scripts/README.md` for the maintained script map. Keep new throwaway
experiments in `scratch/`, and promote reusable shared helpers only with
matching docs and intentional tracking.

## Active Layout

- `webui/`: static app and generated browser data.
- `scripts/`: WebUI builders and packaging tools.
- `scripts/`: WebUI/export helpers.
- `unity_endfield_graph_shader_lab/`: Unity character recovery lab project.
- `export_full/`: generated data exported from the installed client.
- `reports/`: durable WebUI/export summaries.
- `scratch/`: disposable local outputs.
- `memory/`: durable notes, conclusions, and recovery snapshots.

## Script Notes

`scripts/README.md` lists the active script groups. New one-off exploration
scripts should start in `scratch/` or `tmp/`; durable conclusions belong in
`memory/`, and reusable helpers should move into a maintained workflow only
when they are promoted.
