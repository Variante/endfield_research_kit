Agent notes for this repo. User-facing usage belongs in `README.md`.

## Active Scope

Keep root-level docs and workflow guidance focused on:

- the static WebUI in `webui/`
- the Unity character recovery lab in `unity_endfield_graph_shader_lab/`

Move observations, conclusions, older exploration notes, and status snapshots to
`memory/`. Do not use `reports/` for investigation conclusions.

## Commands

```bat
.\export.bat
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

`export.bat` is the canonical story/reference WebUI rebuild from an existing
`export_full/`. It verifies that `export_full/` matches the current installed
`Endfield_Data` fingerprints before the long WebUI builders run, then builds CN
story/reference data by default. It does not export from installed game data by
default. Pass `--export-from-game` only when the user explicitly asks to refresh
`export_full/`, run the story export tools, and decode CN audio. `export.bat`
always finishes by running the audio builder so generated CN conversations have
playable `audioSrc` links when decoded audio is available.
Use `build_updates.bat` for the standalone Updates feed comparison. Use
`build_updates.bat --init-build` for first-time/baseline-only builds where the
Updates feed should be baselined instead of reporting changes. The wrapper
passes `--skip-asset-updates` by default so stale decoded asset outputs do not
appear in story-only refreshes.
Use `export_assets.bat` for WebUI Assets tab indexes and compact Story media
lookup from existing decoded assets. Pass `--export-from-game` only when the
user explicitly asks to run the heavier AnimeStudio image/model/animation
decode from installed game data first.
Use direct `scripts/build_audio.py` runs for non-CN languages or audio-only
maintenance. The audio builder writes `export_full/structured/Audio/<LANG>/`,
parses Wwise bank event-to-media links, and post-processes generated
conversation JSON with playable `audioSrc` links.

Useful direct commands:

```bat
python scripts\build_updates.py
python scripts\build_updates.py --baseline-only
python scripts\build_updates.py --skip-asset-updates
python scripts\build_updates.py --refresh-previous-export-baseline
python scripts\verify_export_freshness.py
python scripts\story_builder\source_links.py
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\story_builder\build.py --languages CN EN JP --default-language CN
python scripts\build_assets.py
python scripts\build_audio.py
python scripts\package_webui.py
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
saved previous export and the current export.

`scripts/build_updates.py` compares:

```text
export_122
export_full
```

by default. Pass `--previous-export-root PATH` for a different saved previous
export. Scanner cache and feed history live under `.game-data-tracker/`; the
cached baseline is built from the previous export folder, then `export_full/`
is scanned against it. Do not point this comparison at `webui/`, `reports/`,
`memory/`, or `scratch/`. WebUI edits and generated output outside the export
roots must not appear as game-data updates.

The builder may scan exported assets in the same two export folders to add
image/model/video asset-level entries to the Updates page. The standalone
`build_updates.bat` wrapper passes `--skip-asset-updates` by default; include
asset updates only after the asset workflow refreshes heavy outputs
intentionally.

Use `--baseline-only` only when an empty feed is intentional. Use
`--refresh-previous-export-baseline` after replacing the saved previous export
folder so the cached scanner baseline is rebuilt.

## Repo Rules

- Prefer the layout rooted at `serve.py`, `export.bat`, `webui/`,
  `scripts/`, and `unity_endfield_graph_shader_lab/`.
- Keep `README.md` focused on active WebUI and Unity character recovery usage.
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
- `scripts/build_updates.py`
- `scripts/story_builder/source_links.py`
- `scripts/story_builder/build.py`
- `scripts/build_assets.py`
- `scripts/build_audio.py`
- `scripts/package_webui.py`
- supporting files in `scripts/` and `scripts/asset_builder/`

Story reconstruction helpers used by WebUI builders:

- `scripts/story_builder/timeline_recovery.py`
- `scripts/story_builder/mission_recovery.py`
- `scripts/scene_order_gap_shared.py`

Story recovery audit/refresh tools, not run by `export.bat`:

- `scripts/story_recovery/`

Unity character recovery lab:

- project-local scripts under `unity_endfield_graph_shader_lab/`

The old archived-script bucket has been retired. Do not recreate it; put
disposable scripts in `scratch/` or `tmp/`, and promote only maintained
workflow code.
