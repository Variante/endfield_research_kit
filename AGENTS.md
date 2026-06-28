Agent notes for this repo. User-facing usage belongs in `README.md`.

## Active Scope

Keep root-level docs and workflow guidance focused on:

- the static WebUI in `webui/`

Move observations, conclusions, older exploration notes, and status snapshots to
`memory/`. Do not use `reports/` for investigation conclusions.

## Commands

```bat
.\setup_first_time.bat
.\export.bat
.\export.bat --with-assets
.\export.bat --export-from-game
.\build_updates.bat
.\build_updates.bat --init-build
.\export_assets.bat
python serve.py
python serve.py 9000
```

Before starting a WebUI server, check whether the default
`http://127.0.0.1:8765/` server is already running. Reuse the existing default
server instead of starting another `serve.py` process on `8765` or a custom
port, unless the user explicitly asks for a second server.

Root wrapper scripts load `endfield_paths.bat` before parsing arguments. That
file sets the repeated local defaults for `ENDFIELD_GAME_ROOT`,
`ENDFIELD_PREVIOUS_EXPORT_ROOT`, and `ENDFIELD_EXPORT_ROOT`; explicit path
flags still override it for one-off commands.

`setup_first_time.bat` is the user-facing all-in-one first-time setup path. It
initializes `tools/AnimeStudio`, builds the AnimeStudio CLI, verifies the
integrated AnimeStudio VFS/audio commands, runs `export.bat --export-from-game`,
prints optional `export_assets.bat --export-from-game` and
`build_updates.bat --init-build` follow-up commands, then starts or reuses the
default WebUI server. Pass `--no-serve` when setup should finish without
starting `serve.py`.

`export.bat` is the canonical Story/Text Tables WebUI rebuild from an existing
`export_full/`. It verifies that `export_full/` matches the current installed
`Endfield_Data` fingerprints before the long WebUI builders run, then builds CN
Story/Text Tables data by default. It does not export from installed game data by
default. Pass `--export-from-game` only when the user explicitly asks to refresh
`export_full/` and run the story export tools. Pass `--with-assets` to also
rebuild asset indexes and relink/decode CN audio after generated conversations
are rebuilt. Combining `--export-from-game --with-assets` runs one AnimeStudio
Story+asset export instead of separate Story and asset exporter invocations.
`export.bat` does not refresh `webui/overrides/story_order.json`; Story order is
maintained by the OCR workflow. Every `export.bat` run writes a wall-time and
process-tree RAM benchmark under `reports/export_benchmarks/` and updates
`reports/export_benchmark_latest.md/json`.
Use `build_updates.bat` for the standalone Updates feed comparison. Use
`build_updates.bat --init-build` for first-time/baseline-only builds where the
Updates feed should be baselined instead of reporting changes. It reads the
previous/current export roots from `endfield_paths.bat` by default, tracks
WebUI-facing exported text JSON plus exported image/model/video assets and
decoded audio, and accepts explicit root flags for one-off comparisons. Pass
`--skip-audio-updates` to omit decoded audio while keeping other asset entries.
Pass `--skip-asset-updates` only for a text-only update feed.
Use `export_assets.bat` for WebUI Assets tab indexes, compact Story media
lookup, and CN audio relinking from existing decoded assets when Story is
already current. Pass `--export-from-game` only when the user explicitly asks to
run the default full AnimeStudio image/model decode, `Material` JSON, and CN
audio decode from installed game data first. Prefer
`export.bat --export-from-game --with-assets` when Story and assets both need an
installed-game refresh. Pass `--webui-assets` for the lean WebUI-referenced
Texture2D mode, or `--debug-assets` for exhaustive AnimeStudio diagnostics.
Use direct `scripts/build_audio.py` runs for non-CN languages or audio-only
maintenance. The audio builder writes shared SFX/music once under
`export_full/structured/Audio/shared/` and language voice under
`export_full/structured/Audio/<LANG>/`, parses Wwise bank event-to-media links, and post-processes generated
conversation JSON with playable `audioSrc` links. The default exporter mode is
`--animestudio-type-job-mode auto`: it merges non-sharded JSON type jobs inside
one AnimeStudio process while keeping map-filtered asset conversion sharded;
use `parallel` only when comparing against the older one-process-per-type path.

Useful direct commands:

```bat
python scripts\build_updates.py
python scripts\build_updates.py --baseline-only
python scripts\build_updates.py --skip-asset-updates
python scripts\build_updates.py --skip-audio-updates
python scripts\build_updates.py --refresh-previous-export-baseline
python scripts\verify_export_freshness.py
python scripts\story_builder\refresh_evidence.py
python scripts\story_builder\source_links.py
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\story_builder\build.py --languages CN EN JP --default-language CN
python scripts\build_assets.py
python scripts\build_audio.py
python scripts\download_bilibili_video.py --dry-run
python scripts\pack_webui.py
```

`scripts/story_builder/build.py` currently takes about 3 minutes for the
default CN lean build on this checkout. Multi-language builds or forced
timeline recovery can take longer; when Codex runs this command directly, use a
longer shell timeout, such as 10-15 minutes (`timeout_ms` of at least
`900000`).

Unity character recovery lab:

```bat
cd unity_endfield_graph_shader_lab
.\open_character_recovery_lab.bat
.\build_all_character_recovery.bat
```

The Python tooling is intended to stay stdlib-only unless a task explicitly
requires otherwise.

## WebUI Technical Notes

Keep detailed browser/export mechanics here, in project skills, or in
`scripts/README.md`; keep the root `README.md` short and user-facing.

Browser behavior:

- Story/Text Tables inline media treats `sns_emoji_*` as regular inline emoji
  with no popup/modal preview.
- Non-emoji SNS media such as `sns_image_*` and `sns_sticker_*` render at
  normal image proportions with bounded hover/modal previews.
- Story recovery issue filters, source/debug blocks, mission timeline evidence,
  cutscene debug panels, and manual order-edit controls are behind
  `Show debug info`.
- The Story reset button returns filters to Story sort while preserving
  expanded mission groups.

Export freshness:

- `export.bat` runs `scripts/verify_export_freshness.py` before rebuilding
  from an existing `export_full/`.
- Run `python scripts\verify_export_freshness.py` directly when checking the
  guard, and pass `--game-root "...\Endfield_Data"` for non-default installs.
- If freshness reports stale source roots, rerun
  `.\export.bat --export-from-game` before Story or asset builders read
  `export_full/`.

Setup and export internals:

- The expected AnimeStudio CLI path is
  `tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe`.
- The AnimeStudio CLI provides the WebUI VFS commands `dump`, `audio`, `stream`,
  `vfs-index`, and `list`; `dump`, `audio`, `stream`, and `vfs-index` help should include
  `--fallback-assets <FALLBACK_ASSETS>`. `dump`, `stream`, and `vfs-index` accept repeated
  `--block-type` flags plus repeated `--file-regex` filters; `stream` exposes the
  same targeted VFS filtering for JSONL byte streaming.
- Installed-game Story exports use `--structured-dump-mode webui` by default:
  they dump only WebUI-consumed VFS blocks (`table`, `json-data`, and video)
  and skip raw asset bundles, audio PCK/media files, world-streaming bytes,
  irradiance volumes, extend-data bins, patch bytes, and Lua. `build_audio.py`
  streams Wwise bank metadata directly from VFS when relinking audio events.
  `--structured-dump-mode full` keeps the same production skip rules; use
  `--structured-dump-mode debug` only for broad VFS diagnostics.
- `export_assets.bat --export-from-game` passes `--skip-structured`, writes a
  lightweight VFS metadata index, runs WebUI-facing image/model/Material
  export, and decodes CN audio before relinking.
- `export.bat --export-from-game --with-assets` keeps the structured Story
  refresh and folds the asset export into the same AnimeStudio run.
- `tools\DummyDll` is the preferred repo-local IL2CPP DummyDll root when
  optional script-schema recovery is wanted. Wrapper flags or
  `ANIMESTUDIO_DUMMY_DLLS` can supply it, but missing or stale DummyDll paths
  must warn and continue without failing normal exports.
- `--animestudio-mono-behaviour-type-tree-priority script-first` is for
  targeted MonoBehaviour schema experiments; the default is `serialized-first`.
  Script-first must fall back cleanly when no usable DummyDlls are available.
- After installed-game refreshes, check `reports/export_full_summary.md` for
  stage return codes and AnimeStudio export errors.

Browser data inputs and outputs:

- Active inputs include `export_full/structured/StreamingAssets/Table/*.json`,
  recovered AnimeStudio text/metadata under `export_full/recovered/`,
  exported image/model/material outputs under
  `export_full/recovered/AnimeStudio-cli/<source>/`, and generated data under
  `webui/data/`.
- Generated browser outputs include `webui/data/manifest.json`,
  `webui/data/lang/<code>/index.json`, `conv/*.json`, `mission/*.json`,
  `reference/**`, `webui/data/assets/index.json`, and
  `webui/data/updates/latest.json`.
- The current `export.bat` skips raw VFS output and source inventory because
  the browser does not need them.

Tool pointers:

- `tools/AnimeStudio/` is the tracked AnimeStudio fork submodule used by
  installed-game Story and asset export paths.
- `tools/endfield_source_graph.py` builds/query local SQLite evidence across
  generated WebUI story/text-table data, selected tables, audio, videos,
  assets, material links, and optional AnimeStudio asset maps.
- `tools/endfield-il2cpp/` contains offline IL2CPP metadata diagnostics. It is
  not part of normal export, Updates, packaging, or serving flows.
- Optional local vendor/tool caches may live under ignored `tools/`; keep their
  generated outputs local.

Script notes:

- `scripts/README.md` lists the maintained script map and workflow contracts.
- New one-off exploration scripts should start in `scratch/` or `tmp/`.
- Durable conclusions belong in `memory/`; reusable helpers should move into
  maintained workflow code only with matching docs and intentional tracking.

## Current Guidance Locations

Older `memory/` exploration archives have been retired into the active docs.
Do not recreate duplicate README-shaped snapshots in `memory/`; update the
current source of truth instead:

- user-facing active workflow: `README.md`
- agent-facing repo rules: `AGENTS.md`
- script/workflow contract: `scripts/README.md`
- WebUI frontend scope: `webui/README.md`
- detailed WebUI recovery notes: `memory/webui_recovery.md`
- shader/animation recovery snapshots: dedicated files in `memory/`

## Project Local Skills

Project-only Codex skills live under `.codex/skills/`. When a task matches one
of these workflows, open the matching `SKILL.md` before acting:

- `.codex/skills/endfield-webui-workflow/`: WebUI refresh, serving, packaging,
  Updates tab, and static frontend scope, including current SNS inline-image
  behavior.
- `.codex/skills/endfield-source-graph/`: source graph build/query and
  graph-backed follow-up reports.
- `.codex/skills/endfield-option-overrides/`: editing and validating
  WebUI-only manual option recovery overrides in
  `webui/overrides/options.json`.
- `.codex/skills/animestudio-workflow/`: building, running, patching, and
  debugging the local `tools/AnimeStudio` exporter and its WebUI wrappers.

The current checkout does not ship separate `endfield-story-recovery` or
`endfield-character-recovery-lab` skill folders. For those workflows, use the
active docs (`README.md`, `scripts/README.md`, `webui/README.md`, and
`unity_endfield_graph_shader_lab/README.md`) plus the existing source-graph
skill when graph evidence is relevant.

The retired exploration snapshots were collapsed because they mixed active
workflow guidance with stale conclusions, obsolete package behavior based on
`reports/`, and Blender/actor recovery detail outside the root active scope.
Keep generated reports in `reports/`, durable conclusions in `memory/`, and
disposable experiments in `scratch/` or `tmp/`.

## Update Tracking Rule

The WebUI Updates tab must report only exported game-data changes between a
saved previous export and the current export. By default it tracks the
exported JSON roots that feed Story/Text Tables display plus exported
image/model/video assets plus decoded audio. Use `--full-export-scan` only for
a broad audit of all files under the two export roots.

`build_updates.bat` reads the saved previous export and current export roots
from `endfield_paths.bat` (`ENDFIELD_PREVIOUS_EXPORT_ROOT` and
`ENDFIELD_EXPORT_ROOT`). The underlying `scripts/build_updates.py` defaults to
comparing:

```text
export_1d2
export_full
```

when no wrapper config or explicit flags are supplied. Pass
`--previous-export-root PATH` for a one-off different saved previous export.
Scanner cache and feed history live under `.game-data-tracker/`; the cached
baseline is built from the previous export folder, then the current export root
is scanned against it using the same focused roots. Do not point this
comparison at `webui/`, `reports/`, `memory/`, or `scratch/`. WebUI edits and
generated output outside the export roots must not appear as game-data updates.

The builder scans exported assets in the same two export folders by default to
add image/model/video/audio asset-level entries to the Updates page. Asset
modifications use fast size fingerprints by default; pass
`--hash-asset-updates` only when same-size binary modifications must be
detected. Use `--skip-audio-updates` when decoded audio entries should be
omitted while image/model/video entries remain enabled. Use
`--skip-asset-updates` only when all asset entries should be omitted.
Use `--dry-run-prune-previous-export-untracked` to preview previous-export
files that exist byte-identically at the same relative paths in the current
export, and `--prune-previous-export-untracked` only when intentionally
deleting those old duplicate copies from the previous export folder. This
pruning must never target `export_full/` or the repo root.

Use `--baseline-only` only when an empty feed is intentional. Use
`--refresh-previous-export-baseline` after replacing the saved previous export
folder so the cached scanner baseline is rebuilt.

## Repo Rules

- Prefer the layout rooted at `serve.py`, `export.bat`, `webui/`,
  `scripts/`, and `unity_endfield_graph_shader_lab/`.
- Keep `README.md` focused on active WebUI user-facing usage.
- Keep observations, conclusions, investigation notes, and status snapshots in
  `memory/`.
- Keep `reports/` for durable generated reports only, not agent conclusions or
  narrative writeups.
- Use `scratch/` for attempts, tool prototypes, generated previews, and tools
  written during exploration before they are promoted.
- Use `tmp/` for temporary results, intermediate output, and disposable files.
- Put durable shared helper code under the maintained script/tool surface.
  `tools/` is ignored by default except for already tracked helper scripts, so
  new promoted tools need intentional tracking and documentation.
- Local vendor/tool caches may live under ignored `tools/`. If
  `tools/Ruri.ShaderDecompiler` is present, regularly pull upstream before
  rebuild or recovery work: `git -C tools\Ruri.ShaderDecompiler pull --ff-only`.
- Keep `ue5_*` and `unity_*` directories self-contained. Code, assets, generated
  files, and helpers related to those projects should live inside the matching
  project folder.
- Preserve narrow, surgical changes when adjusting exporters or builders.
- Do not promote an ad-hoc script into `scripts/` unless it supports WebUI or
  `unity_endfield_graph_shader_lab`.

## Active Script Groups

WebUI:

- `scripts/export_full_from_game.py`
- `scripts/track_export_changes.py`
- `scripts/story_builder/dialog_registry.py`
- `scripts/story_builder/video_bindings.py`
- `scripts/verify_export_freshness.py`
- `scripts/story_builder/refresh_evidence.py`
- `scripts/build_updates.py`
- `scripts/story_builder/source_links.py`
- `scripts/story_builder/build.py`
- `scripts/story_builder/timeline_action_evidence.py`
- `scripts/build_assets.py`
- `scripts/build_audio.py`
- `scripts/pack_webui.py`
- supporting files in `scripts/` and `scripts/asset_builder/`

Story reconstruction helpers used by WebUI builders:

- `scripts/story_builder/timeline_recovery.py`
- `scripts/story_builder/timeline_action_evidence.py`
- `scripts/story_builder/mission_recovery.py`
- `scripts/scene_order_gap_shared.py`

Story recovery audit/refresh tools, not run by `export.bat`:

- `scripts/story_recovery/`
- `scripts/download_bilibili_video.py` is an optional gameplay-video intake
  helper for the OCR/audio story-order workflow. It requires `requests`,
  `ffmpeg`, and browser-exported Bilibili cookies, writes complete `.mp4` files
  under `videos/`, and is not part of the stdlib-only export path.

Unity character recovery lab:

- project-local scripts under `unity_endfield_graph_shader_lab/`

The old archived-script bucket has been retired. Do not recreate it; put
disposable scripts in `scratch/` or `tmp/`, and promote only maintained
workflow code.
