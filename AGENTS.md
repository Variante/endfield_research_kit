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
python serve.py
python serve.py 9000
```

`export.bat` is the canonical WebUI refresh. It exports only data needed by the
browser, skips raw VFS and source inventory, builds the Updates feed, builds CN
story/reference data by default, and rebuilds the asset index.

Useful direct commands:

```bat
python scripts\webui\build_updates.py
python scripts\webui\build_updates.py --reset-baseline
python scripts\webui\build_story_source_links.py
python scripts\webui\build_story.py --languages CN --default-language CN
python scripts\webui\build_story.py --languages CN EN JP --default-language CN
python scripts\webui\build_assets.py
python scripts\webui\package_webui.py
```

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
  Updates tab, and static frontend scope.
- `.codex/skills/endfield-story-recovery/`: DialogIdTable registry,
  story-source links, Timeline/mission recovery, and scene-order warnings.
- `.codex/skills/endfield-source-graph/`: source graph build/query and
  graph-backed follow-up reports.
- `.codex/skills/endfield-character-recovery-lab/`: Unity character recovery
  viewer, shader tuning, generated manifests, previews, and ACL sampling.

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

The builder may scan exported assets under `export_full/` to add image/model/video
asset-level entries to the Updates page, but it must only report those entries
when the original `Endfield_Data` tracker reports a real game-data change. When
there is no game-data change, exported asset differences should be treated as
local rebuild noise and baselined silently.

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
- Put durable shared tools under `tools/`. Existing tools there may be used and
  patched as needed.
- For `tools/Ruri.ShaderDecompiler`, regularly pull upstream before rebuild or
  recovery work: `git -C tools\Ruri.ShaderDecompiler pull --ff-only`.
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

Archived exploration scripts live under `memory/scripts_archive/`.
