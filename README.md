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
- `scripts/webui/verify_export_freshness.py`
- `scripts/recover_dialog_id_registry.py --quiet`
- `scripts/webui/build_story_source_links.py`
- `scripts/webui/build_updates.py`
- `scripts/webui/build_story.py --languages CN --default-language CN`
- `scripts/webui/build_assets.py`

For an initial build where there is no useful update history yet:

```bat
.\export.bat --init-build
```

For faster local refreshes that can reuse the existing asset search indexes and
skip demo bundle zip generation:

```bat
.\export.bat --fast-assets
```

CN is exported by default. To build more languages after the export:

```bat
python scripts\webui\build_story.py --languages CN EN JP --default-language CN
```

Package a shareable browser build with:

```bat
python scripts\webui\package_webui.py
```

or:

```bat
.\package_webui.bat
```

## Update Tracking

The Updates tab is built by:

```bat
python scripts\webui\build_updates.py
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

Write an empty baseline feed for a first-time or baseline-only build:

```bat
python scripts\webui\build_updates.py --baseline-only
```

If you still want game-data changes but not the exported asset diff, use
`--skip-asset-updates`.

Reset the baseline only when you intentionally want to treat the current
installed game files as the new "no changes yet" state:

```bat
python scripts\webui\build_updates.py --reset-baseline
```

The WebUI feed is written to `webui/data/updates/latest.json`.

## Export Freshness

`export.bat` verifies that `export_full/` still matches the installed
`Endfield_Data` source fingerprints before running the long WebUI builders. To
check that guard directly:

```bat
python scripts\webui\verify_export_freshness.py
```

If it reports stale source roots, rerun `.\export.bat` so future game-data
changes are re-extracted before `build_story.py` or asset indexing reads
`export_full/`.

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

The normal workflows use Python stdlib scripts plus local helper tools already
kept under `tools/`:

- `tools/AnimeStudio/`: AnimeStudio extraction/recovery helpers used by the
  exported story and media data. Upstream:
  <https://github.com/Escartem/AnimeStudio>
- `tools/endfield-il2cpp/`: local offline IL2CPP metadata catalog helper.
  It validates/caches `global-metadata.dat` when available and writes
  option-flow runtime evidence reports; it is not part of the normal
  `export.bat` WebUI refresh.
- `tools/TypeTree/`: optional Unity type-tree reference tooling for decoding
  serialized asset schemas when AnimeStudio/AssetStudio-style output is missing
  fields. Upstream: <https://github.com/FractalTools/TypeTree>
- `tools/TypeTreeDumps/`: optional Unity type-tree dump references used as
  schema lookups for Unity class layouts. They are not part of normal
  `export.bat` refreshes. Upstream:
  <https://github.com/AssetRipper/TypeTreeDumps>
- `tools/Ruri.ShaderDecompiler/`: shader decompiler used around the Unity lab.
  Upstream: <https://github.com/ShiyumeMeguri/Ruri.ShaderDecompiler>
- `tools/FractalMiner/`: Unity asset and shader-analysis helper. Upstream:
  <https://github.com/ShiyumeMeguri/FractalMiner>
- `tools/AllShader_1.2.4-Assets/`: shader reference assets from FractalMiner's
  EndField project assets:
  <https://github.com/ShiyumeMeguri/FractalMiner/tree/main/Assets/Project/EndField>
- `tools/acl-upstream/`: Animation Compression Library reference source.
  Upstream: <https://github.com/nfrechette/acl>
- `tools/endfield_acl_sampler/`: local ACL sampling helper for actor animation
  recovery; it is maintained in this repo and built against `tools/acl-upstream/`.
- `tools/fluffy-dumper-src/`: maintained dumping support kept as source for
  inspection and patching. Upstream mirror:
  <https://git.nekolab.app/fluffield/fluffy-dumper>
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
  `tools/endfield_character_recovery_planner.py`,
  `tools/endfield_story_branch_resolver.py`,
  `tools/endfield_map_level_indexer.py`, and
  `tools/endfield_semantic_update_classifier.py` build richer reports under
  `reports/source_graph/`.

Use `scripts/README.md` for the maintained script map. Keep new throwaway
experiments in `scratch/`, and promote only reusable shared helpers to `tools/`.

## Active Layout

- `webui/`: static app and generated browser data.
- `scripts/webui/`: WebUI builders and packaging tools.
- `scripts/`: WebUI/export helpers.
- `unity_endfield_graph_shader_lab/`: Unity character recovery lab project.
- `export_full/`: generated data exported from the installed client.
- `reports/`: durable WebUI/export summaries.
- `scratch/`: disposable local outputs.
- `memory/`: archived exploration notes and one-off utilities.

## Script Notes

`scripts/README.md` lists the active script groups. New one-off exploration
scripts should start in `memory/` or `scratch/` and only move into a maintained
workflow once they are promoted.
