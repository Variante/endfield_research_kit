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
.\export.bat --init-build
.\export.bat --fast-assets
python serve.py
python serve.py 9000
```

`export.bat` is the canonical WebUI refresh. It exports only data needed by the
browser, skips raw VFS and source inventory, builds the Updates feed, builds CN
story/reference data by default, and rebuilds the asset index. It also verifies
that `export_full/` matches the current installed `Endfield_Data` fingerprints
before the long WebUI builders run.
Use `--init-build` for first-time/baseline-only builds where the Updates feed
should be baselined instead of reporting changes.
Use `--fast-assets` for local refreshes that can reuse existing asset indexes
and skip demo bundle zip generation.

Useful direct commands:

```bat
python scripts\webui\build_updates.py
python scripts\webui\build_updates.py --baseline-only
python scripts\webui\build_updates.py --skip-asset-updates
python scripts\webui\build_updates.py --reset-baseline
python scripts\webui\verify_export_freshness.py
python scripts\webui\build_story_source_links.py
python scripts\webui\build_story.py --languages CN --default-language CN
python scripts\webui\build_story.py --languages CN EN JP --default-language CN
python scripts\webui\build_assets.py
python scripts\webui\build_assets.py --fast
python scripts\webui\package_webui.py
```

`scripts/webui/build_story.py` currently takes about 3 minutes for the default
CN lean build on this checkout. Multi-language builds or forced timeline
recovery can take longer; when Codex runs this command directly, use a longer
shell timeout, such as 10-15 minutes (`timeout_ms` of at least `900000`).

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
- detailed WebUI recovery notes: `memory/webui_recovery/`
- shader/animation recovery snapshots: dedicated files in `memory/`

## Project Local Skills

Project-only Codex skills live under `.codex/skills/`. When a task matches one
of these workflows, open the matching `SKILL.md` before acting:

- `.codex/skills/endfield-webui-workflow/`: WebUI refresh, serving, packaging,
  Updates tab, and static frontend scope, including current SNS inline-image
  behavior.
- `.codex/skills/endfield-source-graph/`: source graph build/query and
  graph-backed follow-up reports.

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

The WebUI Updates tab must report only original installed game-data changes.

`scripts/webui/build_updates.py` tracks:

```text
D:\Program Files\Endfield Game\Endfield_Data
```

by default and stores state under `.game-data-tracker/`. Do not point this
tracker at `webui/`, `export_full/`, `reports/`, `memory/`, or `scratch/`.
WebUI edits and generated output must not appear as game-data updates.
Local CrashSight telemetry files under
`Plugins/x86_64/wesight/crashsight_data/` are ignored as volatile local runtime
state, not installed content updates.

The builder may scan exported assets under `export_full/` to add image/model/video
asset-level entries to the Updates page, but it must only report those entries
when the original `Endfield_Data` tracker reports a real game-data change. When
there is no game-data change, exported asset differences should be treated as
local rebuild noise and baselined silently.

Zero-change reruns should not blank the Updates page. `build_updates.py`
preserves the existing non-empty feed, or restores the latest non-empty feed
snapshot from `.game-data-tracker/history/update-feed-*.json`. If no feed
snapshot exists, it can fall back to the latest non-empty raw tracker report,
which recovers game-data entries but not already-overwritten asset diffs. Use
`--baseline-only` or `--reset-baseline` only when an empty baseline is
intentional.

## Repo Rules

- Prefer the layout rooted at `serve.py`, `export.bat`, `webui/`,
  `scripts/webui/`, and `unity_endfield_graph_shader_lab/`.
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
- `scripts/recover_dialog_id_registry.py`
- `scripts/webui/verify_export_freshness.py`
- `scripts/webui/build_updates.py`
- `scripts/webui/build_story_source_links.py`
- `scripts/webui/build_story.py`
- `scripts/webui/build_assets.py`
- `scripts/webui/package_webui.py`
- supporting files in `scripts/webui/`

Story reconstruction helpers used by WebUI builders:

- `scripts/recover_timeline_line_orders.py`
- `scripts/recover_mission_timelines.py`
- `scripts/scene_order_gap_shared.py`

Unity character recovery lab:

- project-local scripts under `unity_endfield_graph_shader_lab/`

The old archived-script bucket has been retired. Do not recreate it; put
disposable scripts in `scratch/` or `tmp/`, and promote only maintained
workflow code.
