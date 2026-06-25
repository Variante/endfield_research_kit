# Endfield Research Kit

Endfield Research Kit turns a local, legally obtained Endfield install into an
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
  <img src="res/story_screenshot.png" alt="Story browser with mission list, reconstructed dialog, filters, and debug controls" height="160">
  <img src="res/story_screenshot2.png" alt="Story browser showing recovered dialog detail with media and evidence panels" height="160">
  <img src="res/story_screenshot3.png" alt="Text Tables browser with searchable localized table rows" height="160">
  <img src="res/story_screenshot4.png" alt="Additional Endfield Research Kit WebUI screenshot" height="160">
</p>

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

For a fresh checkout, install Git, Python 3, and a legally obtained
Endfield client first. Then clone the project:

```bat
git clone https://github.com/Variante/endfield_research_kit.git
cd endfield_research_kit
```

Run the all-in-one setup script from the repository root. Pass the installed
`Endfield_Data` folder:

```bat
.\setup_first_time.bat --game-root "E:\Games\Endfield Game\Endfield_Data"
```

The script initializes the AnimeStudio submodule, builds AnimeStudio, verifies
AnimeStudio's integrated VFS/audio commands, exports Story/Text Tables data,
exports Assets tab media and CN audio into repo-local output folders, creates
the first Updates baseline, and starts or reuses the WebUI server at
`http://127.0.0.1:8765/`.

The local `tools/AnimeStudio` fork includes custom Endfield VFS/export work
informed by [fluffy-dumper](https://git.nekolab.app/fluffield/fluffy-dumper)
and [EIHRTeam/EndfieldStudio](https://github.com/EIHRTeam/EndfieldStudio).
Many thanks to those projects and their maintainers for the groundwork.

First-time setup is intentionally heavy. The Story/Text Tables rebuild is much
faster once `export_full/` exists, but the installed-game export plus full
Assets tab media and CN audio refresh can take several hours. The full asset
path has been observed around 27 GiB of process-tree RAM on a 64 GiB workstation;
use `--skip-assets` for a lighter first pass on lower-RAM systems, then run
`export_assets.bat --export-from-game --animestudio-jobs 1` later when you are
ready for the media/audio pass. Keep generous free disk space for `export_full/`,
decoded audio, reports, and optional packages; 100 GB free is a sensible
starting point, and debug/full media workflows can need more.

Keep that terminal window open while browsing the WebUI. To build everything
without starting the server, add `--no-serve`:

```bat
.\setup_first_time.bat --game-root "E:\Games\Endfield Game\Endfield_Data" --no-serve
```

Useful setup options:

- `--skip-assets`: build Story/Text Tables first and skip the heavier Assets tab
  media and CN audio export.
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

Use `.\export.bat --export-from-game` again after the installed game updates,
after `scripts\verify_export_freshness.py` reports stale source roots, or when
you intentionally want to refresh `export_full/` from the installed client. Run
`.\export_assets.bat --export-from-game` when you also want to refresh decoded
media and CN audio from the installed client.

Plain `.\export.bat` rebuilds Story/Text Tables browser data from an existing
`export_full/` and verifies freshness first. `export_assets.bat` rebuilds the
Assets tab index, compact Story media lookup, and CN audio links. For command
internals and direct script entry points, see `scripts/README.md`.

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
story and text-table data, and emoji images; a companion assets zip with larger
story images and videos; and a standalone audio zip with decoded story audio.
Extract the story zip first, then extract the assets and audio zips into the
same directory when those media or audio files are needed.

## Update Tracking

Build the Updates tab with:

```bat
.\build_updates.bat
```

By default this compares the saved previous export in `export_1d2/` against
the current export in `export_full/`, then writes
`webui/data/updates/latest.json`. Use `--previous-export-root PATH` or
`--export-root PATH` when comparing different export trees.

Write an empty first-time baseline with:

```bat
.\build_updates.bat --init-build
```

More specific update-tracking flags, pruning safeguards, and scanner-cache
details are documented in `AGENTS.md` and `scripts/README.md`.

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
