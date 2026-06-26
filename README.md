# Endfield Research Kit

Endfield Research Kit turns a local Windows version Endfield install into an
offline research browser. Its main surface is a static `webui/` app for
browsing recovered story text, raw text tables, exported media/assets, playable
audio/video, and focused update diffs between game-data exports.

The project is built around reproducible local exports:

- `Story` reconstructs dialog, cutscenes, branches, inline media, audio links,
  story order, and recovery evidence from generated game-data JSON.
- `Text Tables` exposes localized table rows and source data in a searchable
  browser.
- `Assets` indexes exported images, models, videos, materials, metadata, and
  related files.
- `Updates` compares a saved previous export against the current export so the
  WebUI reports game-data changes without treating local WebUI edits as
  upstream changes.

<p>
  <img src="res/story_screenshot.png" alt="Story browser with mission list, reconstructed dialog, filters, and debug controls" height="150">
  <img src="res/story_screenshot2.png" alt="Story browser showing recovered dialog detail with media and evidence panels" height="150">
  <img src="res/story_screenshot3.png" alt="Text Tables browser with searchable localized table rows" height="150">
  <img src="res/story_screenshot4.png" alt="Asset browser showing exported OBJ models" height="150">
</p>

## Disclaimer

This repository is for research and study purposes only. It is intended for
local inspection of data from a legally obtained installation, with generated
outputs kept narrow and reproducible. Do not use it to redistribute proprietary
game content or bypass the rights of the original creators.

Most notes, recovery logic, generated outputs, and documentation in this
workspace were produced with LLM assistance. Treat them as working research
artifacts, not authoritative facts. Expect mistakes, inspect the source data,
and verify important conclusions yourself.

The exported tables, story files, audio, videos, images, and update diffs can
include unreleased or not-yet-seen game content. Browsing them may spoil story,
characters, maps, events, mechanics, or other discoveries. If you care about a
blind playthrough, be careful about what you export and open.

Older exploration notes, demo status snapshots, and one-off recovery utilities
belong under `memory/` so the repo root stays focused.

## First-Time Setup

For a fresh checkout, install Git, Python 3, and a legally obtained
Endfield client first. Then clone the project:

```bat
git clone https://github.com/Variante/endfield_research_kit.git
cd endfield_research_kit
```

Edit the repo-root path config once, then run the all-in-one setup script from
the repository root:

```bat
notepad endfield_paths.bat
.\setup_first_time.bat
```

Set `ENDFIELD_GAME_ROOT` to the installed `Endfield_Data` folder. The same file
also stores the saved previous export folder used by Updates tracking.

The script initializes the AnimeStudio submodule, builds AnimeStudio, verifies
AnimeStudio's integrated VFS/audio commands, exports Story/Text Tables data
into `export_full/` and `webui/data/`, then starts or reuses the WebUI server
at `http://127.0.0.1:8765/`.

It intentionally skips the heavier optional passes. Run `export_assets.bat`
later when you want Assets tab media and playable CN audio, and run
`build_updates.bat --init-build` when you want to initialize the Updates tab
baseline.

The local `tools/AnimeStudio` fork includes custom Endfield VFS/export work
informed by [fluffy-dumper](https://git.nekolab.app/fluffield/fluffy-dumper)
and [EIHRTeam/EndfieldStudio](https://github.com/EIHRTeam/EndfieldStudio).
Many thanks to those projects and their maintainers for the groundwork.

First-time setup still does real work. Building AnimeStudio and exporting
Story/Text Tables can take a while; the optional installed-game asset/media and
CN audio refresh can take several hours. The full asset path has been observed
around 27 GiB of process-tree RAM on a 64 GiB workstation, so 64 GiB system RAM
is the comfortable target for full media refreshes. On lower-RAM systems, start
with the base setup, then run the optional asset pass later with
`--webui-assets` or `--animestudio-jobs 1`.

Keep plenty of free disk space for `export_full/`, decoded audio, reports, and
optional packages. Around 325 GB free is a practical starting point if you want
debug-level asset diagnostics and broad media outputs.

Keep that terminal window open while browsing the WebUI. To build everything
without starting the server, add `--no-serve`:

```bat
.\setup_first_time.bat --no-serve
```

Useful setup options:

- `--game-root PATH`: one-off override for `ENDFIELD_GAME_ROOT` in `endfield_paths.bat`.
- `--no-serve`: build Story/Text Tables without starting the WebUI server.
- `--help`: show the script help and examples.

For troubleshooting and implementation details behind the wrappers, see
`AGENTS.md` and `scripts/README.md`.

## Routine Commands

After `export_full/` already exists and still matches the installed game, use
the faster rebuild commands:

```bat
.\export.bat
.\export_assets.bat
.\build_updates.bat
python serve.py
```

Plain `export.bat` rebuilds Story/Text Tables browser data from the existing
`export_full/` and verifies freshness first. Use `export.bat --export-from-game`
after the installed game updates, after `scripts\verify_export_freshness.py`
reports stale source roots, or whenever you intentionally want to refresh
`export_full/` from the installed client.

`export_assets.bat` without `--export-from-game` reuses existing decoded assets,
rebuilds the Assets tab index and compact Story media lookup, then relinks
existing CN audio. Pass `--export-from-game` when you want to refresh media or
audio from the installed client.

Installed-game asset refreshes have three modes:

- `--full-assets`: default; exports the WebUI-facing image/model set plus
  `Material` JSON, builds the full Assets browser index, and decodes CN audio.
- `--webui-assets`: lean mode for WebUI-referenced `Texture2D` media when you
  want a faster media refresh with less output.
- `--debug-assets`: exhaustive AnimeStudio conversion/JSON diagnostics, then a
  full Assets browser index from whatever browser-visible files were exported.

AnimeStudio refreshes also accept worker and shard controls:

```bat
.\export_assets.bat --export-from-game --full-assets --animestudio-jobs 2 --animestudio-shards 16
```

`--animestudio-jobs` is the number of concurrent AnimeStudio worker processes;
the default is `4`, but use `1` or `2` when RAM is tight. `--animestudio-shards`
is the number of deterministic asset slices, defaulting to `16`; it tunes
per-process asset batch size and does not by itself increase concurrency.
`export.bat --export-from-game` accepts `--animestudio-jobs` for Story export
work too.

CN is rebuilt by default. To build more languages after the rebuild:

```bat
python scripts\story_builder\build.py --languages CN EN JP --default-language CN
```

Package a shareable browser build with:

```bat
.\pack_webui.bat
```

or:

```bat
python scripts\pack_webui.py
```

Packaging writes three zips by default: a story zip with the WebUI,
story and text-table data, and emoji images; a companion assets zip with larger
story images and videos; and a standalone audio zip with decoded story audio.
Extract the story zip first, then extract the assets and audio zips into the
same directory when those media or audio files are needed.

## Game Update Tracking

The Updates tab needs two game-data exports: a saved previous export and the
current export. That comparison lets the WebUI show what changed in the game
while ignoring local WebUI edits, regenerated reports, scratch files, and other
research workspace noise.

For a first-time export, there is no older game export to compare against yet.
After `setup_first_time.bat` finishes, optionally initialize an empty baseline:

```bat
.\build_updates.bat --init-build
```

When the game updates:

1. Rename the old `export_full/` to the folder configured as
   `ENDFIELD_PREVIOUS_EXPORT_ROOT` in `endfield_paths.bat`.

2. Refresh the current export from the installed client:

```bat
.\export.bat --export-from-game
```

3. Build the Updates feed:

```bat
.\build_updates.bat
```

If the saved previous export keeps accumulating files that also exist unchanged
in the refreshed export, `build_updates.bat` can help prune those old duplicate
copies. Preview the cleanup first, then run the prune only when the target is
the saved previous export you intend to trim:

```bat
.\build_updates.bat --dry-run-prune-previous-export-untracked
.\build_updates.bat --prune-previous-export-untracked
```

Do not point update tracking at `webui/`, `reports/`, `memory/`, or `scratch/`.
It is meant to compare exported game-data roots only. One-off path flags still
override `endfield_paths.bat` when needed. More specific flags, pruning
safeguards, and scanner-cache details are documented in `AGENTS.md` and
`scripts/README.md`.

## Active Layout

- `webui/`: static app and generated browser data.
- `scripts/`: WebUI builders, packaging tools, and export helpers.
- `tools/AnimeStudio/`: tracked AnimeStudio fork submodule used for
  installed-game story and asset exports.
- `export_full/`: generated data exported from the installed client.
- `res/`: README screenshots and other small documentation media.
- `reports/`: durable WebUI/export summaries.
- `videos/`: local gameplay captures used by optional Story order OCR/audio
  recovery tools.
- `scratch/`: disposable local outputs.
- `memory/`: durable notes, conclusions, and recovery snapshots.

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
