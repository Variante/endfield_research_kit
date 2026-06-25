# Endfield Research Kit

Endfield Research Kit is a local research workspace maintained around the
`webui/` static browser for story, reference text, exported assets, and
source-data update diffs.

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
and builds the patched `fluffy-dumper`, exports Story/Reference data, exports
Assets tab media and CN audio, creates the first Updates baseline, and starts
or reuses the WebUI server at `http://127.0.0.1:8765/`.

Keep that terminal window open while browsing the WebUI. To build everything
without starting the server, add `--no-serve`:

```bat
.\setup_first_time.bat --game-root "E:\Games\Endfield Game\Endfield_Data" --no-serve
```

Useful setup options:

- `--skip-assets`: build Story/Reference first and skip the heavier Assets tab
  media and CN audio export.
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

5. It makes sure `fluffy-dumper.exe` is available for structured story data
and CN audio export.

`.\export.bat --export-from-game` uses `fluffy-dumper` for structured data.
`.\export_assets.bat --export-from-game` uses it for a lightweight VFS bundle
metadata index and CN audio decoding. The wrappers expect:

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

`export_assets.bat --export-from-game` does not run the full structured dump
because it passes `--skip-structured`; it still runs `fluffy-dumper vfs-index`
to cache VFS file/chunk metadata for asset exports, and its audio step uses the
patched `fluffy-dumper audio` command.

6. It runs the first full Story/Reference export from the installed game.

```bat
.\export.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
```

This creates or refreshes `export_full/`, runs the story AnimeStudio export,
and builds CN Story/Reference data.

7. It builds full Assets tab data and CN audio when images, models, videos,
compact Story media lookup, and playable audio links are needed.

```bat
.\export_assets.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
```

Installed-game AnimeStudio refreshes accept `--animestudio-jobs N` through both
wrappers. The default is now `4` so balanced asset shards and per-type exports
run in parallel; lower it to `1` or `2` if peak AnimeStudio memory is too high.
Earlier testing on the 64 GiB machine found `--animestudio-jobs 2` made the Story
JSON slice about 21% faster than one worker and the old full asset refresh peaked
at about 27 GiB observed process-tree working set. The default
`export_assets.bat --export-from-game` path runs the full WebUI-facing
image/model asset export, `Material` JSON, and full Assets browser index. Pass
`--webui-assets` when only WebUI-referenced Texture2D media is needed, or
`--debug-assets` for exhaustive AnimeStudio conversion/JSON diagnostics.

For better story MonoBehaviour decoding, give AnimeStudio a usable IL2CPP
DummyDll folder. The preferred repo-local root is `tools\DummyDll`; when that
directory contains `.dll` files, the wrappers auto-detect it and pass
AnimeStudio's `--dummy_dlls` option.

To reproduce the current local DummyDll root from an installed Endfield build,
generate stub assemblies from `GameAssembly.dll` and
`Endfield_Data\il2cpp_data\Metadata\global-metadata.dat`, then copy the
resulting DLLs into `tools\DummyDll`:

```powershell
git clone --depth 1 --branch 2022.0.7 https://github.com/SamboyCoding/Cpp2IL.git tools\Cpp2IL-src-2022.0.7
dotnet build tools\Cpp2IL-src-2022.0.7\Cpp2IL\Cpp2IL.csproj -c Release

# The current local Endfield build needs manual MetadataRegistration.
# Replace this value after a game update if Cpp2IL reports a different one.
"18c439d80`n" | tools\Cpp2IL-src-2022.0.7\Cpp2IL\bin\Release\net6.0\Cpp2IL.exe --game-path "D:\Program Files\Endfield Game" --exe-name Endfield --output-root tools\Cpp2IL-endfield-dummy --skip-analysis --skip-metadata-txts --suppress-attributes

New-Item -ItemType Directory -Force tools\DummyDll | Out-Null
Copy-Item tools\Cpp2IL-endfield-dummy\*.dll tools\DummyDll\
```

If stock Cpp2IL aborts on the current metadata before saving assemblies, use a
local patched Cpp2IL build or another IL2CPP dumper that can still emit stub
DLLs. The local patched path used here suppresses Cpp2IL-injected attributes,
skips malformed image/type rows instead of aborting, and skips attribute
restoration when `--suppress-attributes` is set. The generated `tools\DummyDll`
folder is a local tool cache and should be refreshed after game updates.

You can also pass a one-off DummyDll folder through the wrappers:

```bat
.\export.bat --export-from-game --animestudio-dummy-dlls "D:\path\to\DummyDll"
```

The explicit flag takes precedence over the `ANIMESTUDIO_DUMMY_DLLS`
environment variable. If neither is set, the wrapper tries known local
locations, including `tools\DummyDll`, and otherwise leaves AnimeStudio's
`--dummy_dlls` option unset.

For targeted MonoBehaviour schema experiments, add
`--animestudio-mono-behaviour-type-tree-priority script-first` to try the
DummyDll script-derived TypeTree before Unity's embedded serialized TypeTree.
The default is `serialized-first`. Script-first helps only when AnimeStudio can
also load the external `MonoScript` dependency for the MonoBehaviour and the
DummyDll set contains a usable script type with real field nodes; otherwise the
output records the unresolved or unusable script-derived status and falls back
to the serialized TypeTree.

AnimeStudio now keeps partial MonoBehaviour JSON when a serialized TypeTree
fails partway through a managed-reference field. Instead of writing only
metadata, it preserves successfully decoded fields such as `m_Name`,
`actionsData`, and `$animestudio.recoveredManagedReferences.RefIds` headers with
each managed reference `rid`, type name, payload offset, payload length, and
validated inferred `DialogMainFlowData` `leadRid`/`linkedRids` when that layout
matches exactly. It also names validated string fields for common dialog
actions, including `lineId`, `animationPath`, `facialMorphPath`, and
`poseControlNames`, records inferred transform-like fields for validated
`DialogTeleportEntityActionData` payloads, names small validated empty-tail and
flag/index-like dialog actions, records validated motion/camera/post-process
scalar blocks for action payloads such as `DialogMoveToActData`,
`DialogLookAtActData`, `DialogTurnToActData`, `DialogCamDOFActionData`,
`DialogMaskActionData`, `DialogCamPPActionData`, and the common
`DialogCamActData` layout, and records a conservative `inferredActionTimingPrefix`
for dialog action payloads (`value0Seconds`, `value1Seconds`, and `actionCode`).
Still-unparsed payloads may include
`heuristicStringHints` and `heuristicRidLinks`; those fields are intentionally
advisory clues, not a full managed-reference schema decode.
The Story builder turns decoded dialog action flows into
`timeline_action_evidence.json` and shows compact line-order/action evidence in
the WebUI when `Show debug info` is enabled.
DummyDlls add extra value on top of that when `m_Script` resolves: the JSON
records the script class/namespace/assembly and whether a script-derived
TypeTree was usable. Some Endfield timeline classes, for example
`Beyond.Gameplay.DialogSlateTimelineData`, are not present in the current Cpp2IL
DummyDll set, so those objects still rely on the embedded serialized TypeTree
plus partial managed-reference recovery.

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
you intentionally want to refresh `export_full/` and Story export data from the
installed client. Run `.\export_assets.bat --export-from-game` when you also
want to refresh decoded media and CN audio from the installed client.

`export.bat` without `--export-from-game` rebuilds Story/Reference browser data
from an existing `export_full/`. It runs:

- `scripts/verify_export_freshness.py`
- `scripts/story_builder/refresh_evidence.py`
- `scripts/story_builder/build.py --languages CN --default-language CN --skip-audio-link`

The evidence refresh step runs the DialogIdTable registry, narrative video
bindings, and story source-link refresh in parallel. The freshness verifier uses
a fast non-empty check for required generated output folders; run
`python scripts\verify_export_freshness.py --full-output-counts` only when an
exact audit count is needed.

It intentionally skips installed-game export, Updates diffing, fluffy-dumper
structured export, AnimeStudio story extraction, 2D/3D asset/animation
decoding, and audio relinking by default. It also leaves the editable Story sort
order in `webui/overrides/story_order.json` alone; that file is maintained by
the OCR story-order workflow.

`export_assets.bat` rebuilds the Assets tab index and compact Story media
lookup, then runs `scripts/build_audio.py --skip-decode` to relink existing CN
audio under `export_full/structured/Audio/CN/`. With `--export-from-game`, it
refreshes decoded media and decodes CN audio before the relink pass.

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

To shrink the saved previous export after confirming the Updates comparison,
preview old files that already exist byte-identically in the current export:

```bat
.\build_updates.bat --dry-run-prune-previous-export-untracked
```

Then delete those old duplicate copies from the previous export root
intentionally:

```bat
.\build_updates.bat --prune-previous-export-untracked
```

The prune flag refuses to run when the previous export root is the current
`export_full/` or the repository root. It deletes only previous-export files
that exist byte-identically at the same relative path in the current
`export_full/`; cached tracker and asset baselines keep future update
comparisons from treating those pruned files as newly added.

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

## Tool Pointers

The normal reuse path uses the WebUI scripts and an existing `export_full/`.
Installed-game refreshes also use the tracked AnimeStudio submodule and a local
`fluffy-dumper` executable.

Future export work may be able to use
[EIHRTeam/EndfieldStudio](https://github.com/EIHRTeam/EndfieldStudio) as a
replacement for the current patched `fluffy-dumper` plus AnimeStudio pipeline,
once its coverage matches the Story/Reference, Assets, and audio surfaces this
workspace depends on.

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
