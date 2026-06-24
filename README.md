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

## First-Time Setup

For a fresh checkout, install Git, Python 3, Rust/Cargo, and a legally obtained
Endfield client first. Then clone the project:

```bat
git clone https://github.com/Variante/endfield_research_kit.git
cd endfield_research_kit
```

Run the all-in-one setup script from the repository root. If Endfield is in the
default location, use:

```bat
.\setup_first_time.bat
```

If your installed game is somewhere else, pass the installed `Endfield_Data`
folder:

```bat
.\setup_first_time.bat --game-root "E:\Games\Endfield Game\Endfield_Data"
```

The script initializes the AnimeStudio submodule, builds AnimeStudio, downloads
and builds the patched `fluffy-dumper`, exports Story/Reference/audio data,
exports Assets tab media, creates the first Updates baseline, and starts or
reuses the WebUI server at `http://127.0.0.1:8765/`.

Keep that terminal window open while browsing the WebUI. To build everything
without starting the server, add `--no-serve`:

```bat
.\setup_first_time.bat --game-root "E:\Games\Endfield Game\Endfield_Data" --no-serve
```

Useful setup options:

- `--skip-assets`: build Story/Reference/audio first and skip the heavier
  Assets tab media export.
- `--refresh-fluffy-src`: download and overlay the hosted patched
  `fluffy-dumper` source before building it.
- `--help`: show the script help and examples.

<details>
<summary>What the setup script does</summary>

The setup script is just the first-time workflow below bundled into one command.
These details are useful when troubleshooting a failed step or when you want to
understand what is being built.

1. It can initialize the AnimeStudio submodule.

```bat
git submodule update --init tools/AnimeStudio
```

2. It verifies Python 3 is on `PATH`.

```bat
python --version
```

3. It chooses the installed `Endfield_Data` folder.

The default path is:

```text
D:\Program Files\Endfield Game\Endfield_Data
```

If your install is somewhere else, the setup script accepts
`--game-root "...\Endfield_Data"`. The export wrappers also accept
`--game-root`, and command-line `--game-root` takes precedence over
`ENDFIELD_GAME_ROOT`.

In `cmd.exe`, an environment fallback looks like:

```bat
set "ENDFIELD_GAME_ROOT=E:\Games\Endfield Game\Endfield_Data"
```

In PowerShell:

```powershell
$env:ENDFIELD_GAME_ROOT = "E:\Games\Endfield Game\Endfield_Data"
```

4. It builds the AnimeStudio CLI submodule.

The installed-game export path uses the AnimeStudio fork at
`tools\AnimeStudio`. The setup script runs:

```bat
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI
```

The expected executable is:

```text
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
```

After the first restore, this faster rebuild is usually enough:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

5. It makes sure `fluffy-dumper.exe` is available for the full story/audio
export.

`.\export.bat --export-from-game` uses `fluffy-dumper` for structured data and
CN audio decoding. The wrapper expects:

```text
tools\fluffy-dumper-src\target\release\fluffy-dumper.exe
```

This tool is a local vendor checkout, not a tracked submodule here. The setup
script downloads this project's patched source zip and builds it locally.

The manual commands are:

```powershell
New-Item -ItemType Directory -Force tools | Out-Null
$fluffyUrl = 'https://drive.google.com/file/d/1WqShlYyM_QpEqzM_myRkdpTGifYOuVHg/view?usp=sharing'
if ($fluffyUrl -match 'drive\.google\.com/file/d/([^/]+)/') {
  $fluffyUrl = 'https://drive.google.com/uc?export=download&id=' + $Matches[1]
}
Invoke-WebRequest -Uri $fluffyUrl -OutFile fluffy-dumper.zip
New-Item -ItemType Directory -Force tools\fluffy-dumper-src | Out-Null
Expand-Archive -Force fluffy-dumper.zip tools\fluffy-dumper-src
```

```bat
cargo build --release --manifest-path tools\fluffy-dumper-src\Cargo.toml
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe --help
```

The help text for both `dump` and `audio` should include
`--fallback-assets <FALLBACK_ASSETS>`. That option is required by the WebUI
export wrappers when one exported source root needs chunks from another source
root.

`export_assets.bat --export-from-game` does not need `fluffy-dumper` because it
passes `--skip-structured`.

6. It runs the first full Story/Reference export from the installed game.

```bat
.\export.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
```

This creates or refreshes `export_full/`, runs the story AnimeStudio export,
decodes CN audio, builds CN Story/Reference data, and links playable
`audioSrc` values into the generated conversations.

7. It builds the Assets tab data when images, models, videos, and compact Story
media lookup are needed.

```bat
.\export_assets.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
```

Installed-game AnimeStudio refreshes accept `--animestudio-jobs N` through both
wrappers. The default is `1` to keep peak RAM low. On the current 64 GiB test
machine, `--animestudio-jobs 2` was the best measured setting: the Story JSON
slice was about 21% faster than one worker and the full asset refresh peaked at
about 27 GiB observed process-tree working set. Avoid `3` workers unless the
machine has substantially more free RAM, because `AnimationClip` and
`Texture2D` are long, high-memory workers.

For better story MonoBehaviour decoding, pass a usable IL2CPP DummyDll folder
through the wrappers:

```bat
.\export.bat --export-from-game --animestudio-dummy-dlls "D:\path\to\DummyDll"
```

The explicit flag takes precedence over the `ANIMESTUDIO_DUMMY_DLLS`
environment variable. If neither is set, the wrapper only passes
AnimeStudio's `--dummy_dlls` option when it finds a directory containing `.dll`
files under the known game/tool locations such as `tools\DummyDll`.

After an installed-game refresh, check `reports/export_full_summary.md` for
stage return codes and log issues. A nonzero AnimeStudio subprocess now makes
the wrapper fail. Metadata-only MonoBehaviour JSON means the guarded reader
found impossible schema fields and preserved object metadata instead of
allocating huge buffers. Per-asset `Export ... error` entries mean individual
converted assets were skipped even though the broader type pass may have
completed.

8. It creates an initial Updates baseline after the first export.

```bat
.\build_updates.bat --init-build
```

9. It starts or reuses the default WebUI server.

```bat
python serve.py
```

Then open `http://127.0.0.1:8765/`.

The local server sends no-store headers, and the Story browser revalidates
generated JSON when loading or reselecting conversations, so a browser reload
after a rebuild should show refreshed data without changing ports.

</details>

## Routine Commands

After `export_full/` already exists and still matches the installed game, use
the faster rebuild commands:

```bat
.\export.bat
.\export_assets.bat
.\build_updates.bat
python serve.py
```

Use `.\export.bat --export-from-game` again after the installed game updates,
after `scripts\verify_export_freshness.py` reports stale source roots, or when
you intentionally want to refresh `export_full/` and decode CN audio from the
installed client.

`export.bat` without `--export-from-game` rebuilds Story/Reference browser data
from an existing `export_full/`. It runs:

- `scripts/verify_export_freshness.py`
- `scripts/story_builder/dialog_registry.py --quiet`
- `scripts/story_builder/video_bindings.py`
- `scripts/story_builder/source_links.py`
- `scripts/story_builder/build.py --languages CN --default-language CN`
- `scripts/build_audio.py --skip-decode`

It intentionally skips installed-game export, Updates diffing, fluffy-dumper
structured export, AnimeStudio story extraction, and 2D/3D asset/animation
decoding by default. It also leaves the editable Story sort order in
`webui/overrides/story_order.json` alone; that file is maintained by the OCR
story-order workflow. Without `--export-from-game`, the final audio pass reuses
existing decoded files under `export_full/structured/Audio/CN/`.

Run `python scripts\build_audio.py --language EN --skip-decode` after building
other WebUI language folders if those languages already have decoded audio.

CN is rebuilt by default. To build more languages after the rebuild:

```bat
python scripts\story_builder\build.py --languages CN EN JP --default-language CN
```

Package a shareable browser build with:

```bat
.\package_webui.bat
```

or:

```bat
python scripts\package_webui.py
```

Packaging writes three zips by default: a story zip with the WebUI,
story/reference text data, and emoji images; a companion assets zip with larger
story images and videos; and a standalone audio zip with decoded story audio.
Extract the story zip first, then extract the assets and audio zips into the
same directory when those media or audio files are needed.

## Browser Notes

The current Story/Reference inline media behavior treats SNS emoji images such
as `sns_emoji_*` as regular inline emoji with no popup/modal preview, while
non-emoji SNS media such as `sns_image_*` and `sns_sticker_*` render at normal
image proportions with bounded hover/modal previews.

The Story sidebar keeps routine browsing quiet by default: recovery issue
filters, source/debug blocks, mission timeline evidence, cutscene debug panels,
and manual order-edit controls are available from the `Show debug info` toggle.
The reset button returns filters to the Story sort while preserving expanded
mission groups.

## Update Tracking

The Updates tab is built by:

```bat
.\build_updates.bat
```

It compares the WebUI-facing exported text JSON plus exported image/model/video
assets and decoded audio in two exported game-data trees. By default the
previous tree is:

```text
export_1d2
```

and the current tree is:

```text
export_full
```

Use `--previous-export-root PATH` when comparing against a different saved
export, and `--export-root PATH` when the current export is not `export_full/`.
These options choose the exported game-data trees that are compared:

```bat
.\build_updates.bat --previous-export-root D:\exports\export_1d2
.\build_updates.bat --export-root D:\exports\export_full --previous-export-root D:\exports\export_1d2
```

Most Updates runs do not need `--game-root`. Pass
`--game-root "...\Endfield_Data"` only when the optional decoded-impact mapping
should read a non-default installed game root; it does not replace
`--export-root` or `--previous-export-root`.

The builder does not scan `webui/`, `memory/`, or other generated repo files,
so WebUI edits do not appear as upstream data changes. Scanner cache and feed
history live in `.game-data-tracker/`; the cached baseline is built from the
previous export folder, then the current export is scanned against it with the
same focused roots. Use `--full-export-scan` only when a broad all-files export
audit is intentional.

Media asset changes, including decoded audio under
`export_full/structured/Audio/`, are included by default using fast size
fingerprints. Pass
`--hash-asset-updates` when same-size binary asset modifications must be
detected, or `--skip-asset-updates` when the feed should only compare
WebUI-facing text JSON.

To shrink the saved previous export after confirming the focused Updates scope,
preview the old files that are outside the tracked text/assets surfaces:

```bat
.\build_updates.bat --dry-run-prune-previous-export-untracked
```

Then delete those untracked files from the previous export root intentionally:

```bat
.\build_updates.bat --prune-previous-export-untracked
```

The prune flag refuses to run when the previous export root is the current
`export_full/` or the repository root.

Non-empty feed snapshots are kept in `.game-data-tracker/history/` as
`update-feed-*.json`.

Write an empty baseline feed for a first-time or baseline-only build:

```bat
.\build_updates.bat --init-build
```

If you want text JSON changes but not the exported asset diff, use:

```bat
.\build_updates.bat --skip-asset-updates
```

Rebuild the cached scanner baseline after replacing the previous export folder:

```bat
.\build_updates.bat --refresh-previous-export-baseline
```

The WebUI feed is written to `webui/data/updates/latest.json`.

## Export Freshness

`export.bat` verifies that `export_full/` still matches the installed
`Endfield_Data` source fingerprints before running the long WebUI builders. To
check that guard directly:

```bat
python scripts\verify_export_freshness.py
```

Pass `--game-root "...\Endfield_Data"` here too when checking a non-default
install root.

If it reports stale source roots, rerun `.\export.bat --export-from-game` so
future game-data changes are re-extracted before the Story builder or asset
indexing reads `export_full/`.

Plain `.\export.bat` uses this same guard before it rebuilds the WebUI from
existing `export_full/` data.

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

The normal reuse path uses the WebUI scripts and an existing `export_full/`.
Installed-game refreshes also use the tracked AnimeStudio submodule and a local
`fluffy-dumper` executable.

The tracked tool surface is intentionally small:

- `tools/AnimeStudio/`: submodule pinned to
  `https://github.com/Variante/AnimeStudio.git`. Build the CLI with
  `scripts\animestudio\rebuild.bat -Target CLI` before
  `export.bat --export-from-game` or `export_assets.bat --export-from-game`.
- `tools/endfield_source_graph.py`: local SQLite source-graph builder for
  evidence lookup across generated WebUI story/reference data, selected tables,
  audio, videos, assets, material links, and optional AnimeStudio asset maps.
  Outputs are written under `reports/source_graph/`. Use
  `python tools\endfield_source_graph.py build --skip-asset-maps` for quick
  iteration, `python tools\endfield_source_graph.py build` for the full graph,
  and `python tools\endfield_source_graph.py query zhuangfy --limit 20` for a
  simple search. Its old standalone follow-up helper scripts have been folded
  into this tool's built-in follow-up index generation.
- `tools/endfield-il2cpp/`: tracked offline IL2CPP metadata helpers used by
  optional story-recovery audits. They are diagnostics, not normal
  `export.bat`, Updates, packaging, or WebUI serving steps.

Optional local tool/vendor directories may also exist under ignored `tools/`,
including `fluffy-dumper-src`, Ruri.ShaderDecompiler, FractalMiner, TypeTree,
TypeTreeDumps, ACL helpers, and other dumping support. Keep their generated
outputs local. Standalone downloaders, report experiments, and other non-WebUI
helpers should stay in `scratch/`, `tmp/`, or ignored local `tools/` entries
unless they are deliberately promoted with docs.

The maintained gameplay-video OCR workflow can use
`scripts/download_bilibili_video.py` as an optional intake helper for public
Bilibili sources. It writes flat `.mp4` files under `videos/` for the Story
order OCR/audio matcher and requires `requests`, `ffmpeg`, and a
browser-exported cookie JSON.

Use `scripts/README.md` for the maintained script map. Keep new throwaway
experiments in `scratch/`, and promote reusable shared helpers only with
matching docs and intentional tracking.

## Active Layout

- `webui/`: static app and generated browser data.
- `scripts/`: WebUI builders, packaging tools, and export helpers.
- `tools/AnimeStudio/`: tracked AnimeStudio fork submodule used for
  installed-game story and asset exports.
- `unity_endfield_graph_shader_lab/`: Unity character recovery lab project.
- `export_full/`: generated data exported from the installed client.
- `reports/`: durable WebUI/export summaries.
- `videos/`: local gameplay captures used by optional Story order OCR/audio
  recovery tools.
- `scratch/`: disposable local outputs.
- `memory/`: durable notes, conclusions, and recovery snapshots.

## Script Notes

`scripts/README.md` lists the active script groups. New one-off exploration
scripts should start in `scratch/` or `tmp/`; durable conclusions belong in
`memory/`, and reusable helpers should move into a maintained workflow only
when they are promoted.

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
