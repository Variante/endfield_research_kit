# Endfield Research Kit

Endfield Research Kit turns a local Windows version Endfield install into an
offline research browser. Its main surface is a static `webui/` app for
browsing recovered story text, curated gameplay records, exported media/assets,
raw text tables, playable audio/video, and focused update diffs between
game-data exports.

The project is built around reproducible local exports:

- `Story` reconstructs dialog, cutscenes, branches, inline media, audio links,
  story order, and recovery evidence from generated game-data JSON.
- `Gameplay` surfaces curated weapon, character, skill, talent, progression,
  and numeric table records from structured game-data tables.
- `Mission Pipeline` is an experimental debug-only quest DAG with explicit
  client-to-server objective/dialog messages, server-to-client state updates,
  and visibly unknown server successor policy.
- `Progression` traverses direct authored links across character and weapon
  upgrades, equipment stages, item costs/use/obtain paths, reward bundles, and
  drop pools while retaining table/row/path provenance.
- `Projectiles` inspects byte-complete authored projectile payloads, including
  collision, movement, effects, alerts, and sound references with semantic
  confidence labels.
- `Combat` browses evidence-labelled relationships between characters,
  enemies, abilities, exact AbilityEntity inherited-prefix/component records,
  exact 92-byte surrounding configurations, reachable TargetSettings/selectors,
  buffs, projectiles, effects, audio, and assets.
- `Factory` covers recipes, machines, technology, logistics, utilities, shops,
  rewards, and activities from static authored configuration.
- `World` browses deduplicated authored placements, interactives, NPC proxies,
  spawners, enemies, levels, scripts, models, and audio references without
  claiming live world state or simulation.
- `Presentation` follows curated model, prefab, controller, material, shader,
  animation, effect, and representative exported-asset evidence while keeping
  inferred name matches separate from direct source references.
- `Assets` indexes exported images, models, videos, materials, metadata, and
  related files.
- `Text Tables` exposes localized table rows and source data in a searchable
  browser.
- `Updates` compares a saved previous export against the current export so the
  WebUI reports game-data changes without treating local WebUI edits as
  upstream changes.

<p>
  <img src="res/story_screenshot.png" alt="Story browser with mission list, reconstructed dialog, filters, and debug controls" height="150">
  <img src="res/story_screenshot2.png" alt="Story browser showing recovered dialog detail with media and evidence panels" height="150">
  <img src="res/story_screenshot4.png" alt="Asset browser showing exported OBJ models" height="150">
  <img src="res/story_screenshot3.png" alt="Text Tables browser with searchable localized table rows" height="150">
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

Durable recovery conclusions are maintained as a small set of living topic
documents under `memory/`; generated reports and one-off experiments stay out
of those documents so the repo root and research guidance remain focused.

中文: [b站专栏](https://www.bilibili.com/opus/1212936027582234627)，[百度盘](http://pan.baidu.com/s/1nLaAc6-AdZAbZb6jGObtmA?pwd=94p7)

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
AnimeStudio's integrated VFS/audio commands, exports Story/Gameplay/Text Tables
plus Mission Pipeline/Progression/Projectile/Combat/Factory/World/Presentation data
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
Story/Gameplay/Text Tables and the related semantic views can take a while; the optional installed-game asset/media and
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
- `--no-serve`: build the static WebUI data without starting the WebUI server.
- `--help`: show the script help and examples.

For troubleshooting and implementation details behind the wrappers, see
`AGENTS.md` and `scripts/README.md`.

## Routine Commands

After `export_full/` already exists and still matches the installed game, use
the faster rebuild commands:

```bat
.\export.bat
.\export.bat --with-assets
.\export_assets.bat
.\build_updates.bat
python serve.py
```

Plain `export.bat` rebuilds Story, Gameplay, Mission Pipeline, Progression, Projectiles, Combat, Factory, World, Presentation, and
Text Tables browser data from
the existing `export_full/` and verifies freshness first. It rebuilds the local
source graph after the authored semantic views (and optional assets/audio), then
builds Presentation and Combat only from that fresh graph; stale graph evidence degrades visibly
instead of being emitted as direct. Use `export.bat --with-assets`
when you want Story plus asset indexes and CN audio relinking in one local
rebuild. Use `export.bat --export-from-game` after the installed game updates,
after `scripts\verify_export_freshness.py` reports stale source roots, or
whenever you intentionally want to refresh `export_full/` from the installed
client. Add `--with-assets` when media or audio should refresh too; that path
runs one combined AnimeStudio Story+asset export instead of running
`export.bat` and `export_assets.bat` separately.

`export_assets.bat` without `--export-from-game` remains the asset/audio-only
path. It reuses existing decoded assets, rebuilds the Assets tab index and
compact Story media lookup, then relinks existing CN audio. Pass
`--export-from-game` when you want to refresh only media or audio from the
installed client after Story is already current.

Installed-game asset refreshes have three modes:

- `--full-assets`: default; exports the WebUI-facing image/model set plus
  `Material` JSON, builds the full Assets browser index, and decodes CN audio.
- `--webui-assets`: lean mode for WebUI-referenced `Texture2D` media when you
  want a faster media refresh with less output.
- `--debug-assets`: exhaustive AnimeStudio conversion/JSON diagnostics, then a
  full Assets browser index from whatever browser-visible files were exported.

AnimeStudio refreshes also accept worker and shard controls:

```bat
.\export.bat --export-from-game --with-assets --full-assets --animestudio-jobs 2 --animestudio-shards 16
```

`--animestudio-jobs` is the number of concurrent AnimeStudio worker processes;
the default is `8`, but use `1`, `2`, or `4` when RAM is tight. `--animestudio-shards`
is the number of deterministic asset slices, defaulting to `16`; it tunes
per-process asset batch size and does not by itself increase concurrency.
Non-sharded JSON type jobs are merged by default with
`--animestudio-type-job-mode auto`, so AnimeStudio can load matching bundles once
for multiple JSON types. Pass `--animestudio-type-job-mode parallel` to restore
the older one-process-per-type behavior. `export.bat --export-from-game`
accepts `--animestudio-jobs` for Story export work too, and
`export.bat --export-from-game --with-assets` accepts the same asset mode,
worker, shard, and type-job controls as `export_assets.bat --export-from-game`.
Every `export.bat` run also writes a wall-time and process-tree RAM benchmark
under `reports/export/benchmarks/` and updates `reports/export/export_benchmark_latest.md`.

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
story, gameplay, text-table data, and emoji images; a companion assets zip with
larger story images and videos; and a standalone audio zip with decoded story
audio.
Extract the story zip first, then extract the assets and audio zips into the
same directory when those media or audio files are needed.
Pass `--skip-audio` to omit the standalone audio zip.

## Generated Reports

Generated reports are ignored by git and grouped by topic; do not create loose
files directly under `reports/`.

- `reports/export/`: latest exporter summary, timestamped run logs, and export
  benchmarks. The exporter retains five runs, and benchmark history retains ten
  runs per label by default.
- `reports/story/build/`: reports refreshed by the normal Story build.
- `reports/story/recovery/`: manual Story recovery and option audits.
- `reports/updates/`: the current exported game-data comparison summary.
- `reports/assets/`: asset hashes and diagnostics.
- `reports/source_graph/`, `reports/mission_order/`,
  `reports/playable_director/`, and `reports/gameplay_video_ocr/`: current graph
  and recovery evidence.

Some Story, mission-order, OCR, and option reports are inputs to later audit or
graph builds, so do not delete a current canonical report solely because it is
generated. Remove superseded run histories, scoped experiments, and temporary
outputs; put durable conclusions in `memory/` and disposable work in `scratch/`
or `tmp/`.

Keep `scratch/` and `tmp/` organized by topic too; do not create loose files or
one-off run directories at either root. Use
`scratch/<topic>/<task>/` for experiments or prototypes that may be revisited,
and `tmp/<topic>/<task-or-run>/` for disposable intermediates. Reuse the active
topic names (`webui`, `story`, `assets`, `animestudio`, `source_graph`,
`character_recovery`, `game_data`, `updates`, `ocr`, and
`reverse_engineering`) and use `tests`, `tools`, or `misc` only when no active
topic fits. Delete completed `tmp/` runs; promote reusable helpers to
`scripts/` and durable conclusions to `memory/`.

## Game Update Tracking

Use the command that matches the job:

| Job | Command | Changes the WebUI Updates page? |
| --- | --- | --- |
| Create an empty Updates page for the first export | `.\build_updates.bat --init-build` | Yes |
| Detect, patch-export, archive, and build after a game update | `.\build_updates_by_patch.bat` | Yes, only on logical change |
| Compare the configured previous/current extracted exports | `.\build_updates.bat` | Yes |
| Compare any two extracted export folders | `.\build_updates.bat --previous-export-root OLD --export-root NEW --refresh-previous-export-baseline` | Yes |
| Detect whether original VFS data changed without applying it | `.\build_updates_by_patch.bat --check` | No |

`build_updates.bat` is the Updates-page builder. It compares two extracted
game-data trees and writes `webui/data/updates/latest.json`, which the static
WebUI reads directly. The normal focused comparison includes Story/Text Tables
source JSON, exported image/model/video assets, and decoded audio. It ignores
local WebUI code, reports, memory, scratch, and other repository changes.

`build_updates_by_patch.bat` owns the installed-game update path. With no
arguments it compares original VFS logical-file hashes against the source
baseline. Logical no-change, VFS-version-only changes, and chunk repacks leave
the baseline, exports, archives, and feed untouched. A logical change is built
in a sibling staging tree: directly dumpable changed VFS files are exported
selectively, broader AnimeStudio or audio scopes run only when their source
blocks changed, and unchanged exported outputs are copied forward from the
previous complete export. After validation it archives the old export,
publishes the staged tree as the latest `export_full`, rebuilds WebUI data,
generates the Updates feed, and advances the source baseline.

### First export: create an empty Updates page

For a first-time export, there is no older game export to compare against yet.
After `setup_first_time.bat` or the first `export.bat` run finishes, create an
empty Updates page:

```bat
.\build_updates.bat --init-build
```

This writes a baseline-only `webui/data/updates/latest.json`; it does not report
the entire first export as newly added. To separately seed the original VFS
detector from only the currently installed version, run:

```bat
.\build_updates_by_patch.bat --init-baseline
```

The VFS baseline is optional and is not required by `build_updates.bat`.

### Normal game-update workflow

After the installed game updates, run one command:

```bat
.\build_updates_by_patch.bat
```

The configured `ENDFIELD_PREVIOUS_EXPORT_ROOT` is the preferred archive name.
If it already exists, the workflow creates a snapshot-suffixed sibling instead
of overwriting it. The current export and preferred archive must be on the same
volume so folder publication uses renames. Changed direct structured files are
exported individually; asset-affecting blocks trigger the configured
AnimeStudio asset scope, and audio-affecting blocks trigger CN audio refresh.

Use detection-only mode when you want to inspect the change plan without
building or rotating anything:

```bat
.\build_updates_by_patch.bat --check
```

The baseline is copied into the staged new export only after the patch export
is stable. It becomes active only after the WebUI rebuild and Updates comparison
succeed. A failed post-rotation build restores the previous `export_full` and
WebUI data; the failed staged export is retained under
`.game-data-tracker/original-data/failed/` for inspection.

### Compare two already extracted versions

This is the direct one-off command for any two extracted folders:

```bat
.\build_updates.bat --previous-export-root "D:\exports\Endfield_old" --export-root "D:\exports\Endfield_new" --refresh-previous-export-baseline
```

The old folder is always `--previous-export-root`; the new folder is always
`--export-root`. Both should be complete extraction roots containing
`structured/` and/or `recovered/`, not `webui/` or the installed
`Endfield_Data` directory.

Useful comparison modes:

```bat
:: Text JSON only
.\build_updates.bat --previous-export-root OLD --export-root NEW --refresh-previous-export-baseline --skip-asset-updates

:: Text, images, models, and videos, but no decoded audio
.\build_updates.bat --previous-export-root OLD --export-root NEW --refresh-previous-export-baseline --skip-audio-updates

:: Hash binary assets too, detecting same-size binary modifications
.\build_updates.bat --previous-export-root OLD --export-root NEW --refresh-previous-export-baseline --hash-asset-updates

:: Broad audit of every file under both export roots; not the normal WebUI scope
.\build_updates.bat --previous-export-root OLD --export-root NEW --refresh-previous-export-baseline --full-export-scan
```

The builder writes:

- `webui/data/updates/latest.json`: data displayed by the Updates tab.
- `reports/updates/game-data-change-summary.json`: machine-readable detailed report.
- `reports/updates/game-data-change-summary.md`: readable detailed report.
- `.game-data-tracker/`: cached previous-export baseline and feed history.

After the command succeeds, reuse an existing `http://127.0.0.1:8765/` server
or run `python serve.py`, then refresh the Updates tab. Re-running
`build_updates.bat` safely replaces the generated latest feed.

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
- `reports/`: generated outputs grouped by topic; see Generated Reports above.
- `videos/`: local gameplay captures used by optional Story order OCR/audio
  recovery tools.
- `scratch/`: topic-grouped experiments and prototypes that may be revisited.
- `tmp/`: topic-grouped disposable intermediates and per-run output.
- `memory/`: consolidated, living recovery conclusions by topic; see
  `memory/README.md` for the index and writing rules.

## Research Memory

The research memory is intentionally concise and topic-based. Update these
documents in place instead of adding dated investigation snapshots:

- [`memory/webui_recovery.md`](memory/webui_recovery.md): WebUI export,
  updates, serving, packaging, media, and performance behavior.
- [`memory/game_story_recovery.md`](memory/game_story_recovery.md): Story
  ordering evidence, quests, dialog/options, and narrative video.
- [`memory/game_data_recovery.md`](memory/game_data_recovery.md): VFS and data
  formats, gameplay payloads, MonoBehaviour semantics, and source graph.
- [`memory/asset_recovery.md`](memory/asset_recovery.md): models, entities,
  materials, textures, media, placement, and asset aliases.
- [`memory/animestudio_recovery.md`](memory/animestudio_recovery.md): exporter
  architecture, conversion status, parsers, diagnostics, and memory behavior.
- [`memory/character_render_and_animation_recovery.md`](memory/character_render_and_animation_recovery.md):
  Unity character rendering, CharInfo/HGRP recovery, roster, and animation.

Changing inventories and exhaustive audits belong under the matching topic in
`reports/`; temporary probes belong under `scratch/` or `tmp/`. The full
maintenance contract is in [`memory/README.md`](memory/README.md) and
`AGENTS.md`.

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
