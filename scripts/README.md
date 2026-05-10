# Scripts

Active scripts in this directory support the WebUI export/package workflow.
Unity shader-lab and character-recovery tools live under
`../unity_endfield_graph_shader_lab/tools`.

## Active Wrappers

From the repo root:

```bat
.\export.bat
.\package_webui.bat
```

`export.bat` is the normal WebUI refresh path. It runs:

- `scripts/export_full_from_game.py --skip-raw-vfs --skip-source-inventory`
- `scripts/webui/build_updates.py`
- `scripts/webui/build_story.py --languages CN --default-language CN`
- `scripts/webui/build_assets.py`

`package_webui.bat` runs `scripts/webui/package_webui.py` and creates a
shareable zip from `serve.py`, `webui/`, and displayed media resolved from
`export_full/`. It excludes 3D/model payloads and does not include
`scratch/`, `reports/`, or `tmp/`.

## Folder Contract

The active WebUI export/package workflow should not require inputs from
`../scratch/`, `../reports/`, or `../tmp/`.

Expected active inputs and outputs:

- `../webui/`: static browser app plus generated WebUI data under
  `webui/data/`.
- `../export_full/`: generated export data used by Story, Reference, Assets,
  and package media resolution.
- `../.game-data-tracker/`: persistent state for original installed game-data
  update tracking.
- `../reports/`: durable generated reports and summaries written by exporters
  or builders. These are outputs, not package inputs, and should not contain
  agent investigation conclusions.
- `../memory/`: observations, conclusions, older exploration notes, status
  snapshots, and archived scripts.
- `../scratch/`: disposable probes, temporary prototypes, logs, generated
  previews, and experiment output that has not become part of a maintained
  workflow.
- `../tmp/`: disposable intermediate output and temporary files.
- `../tools/`: durable shared tools. If a workflow needs reusable helper data
  such as AnimeStudio DummyDlls, place it here or pass it explicitly rather
  than relying on `scratch/` or `tmp/`.

## WebUI

- `export_full_from_game.py`: export data from the installed Endfield client.
  The normal WebUI wrapper is `..\export.bat`, which skips raw VFS and source
  inventory. It writes generated summaries under `..\reports\` but does not
  require `reports`, `scratch`, or `tmp` as active inputs.
- `track_export_changes.py`: generic file-tree tracker used by the WebUI
  Updates builder.
- `webui/build_updates.py`: writes `webui/data/updates/latest.json` from the
  original installed game data only. Tracker state lives under
  `..\.game-data-tracker\`; generated summary reports live under
  `..\reports\`.
- `webui/build_story.py`: builds CN story/reference data by default, with
  optional extra languages. It reads from `..\export_full\` and writes
  generated WebUI data plus durable reports.
- `webui/build_assets.py`: builds the WebUI asset index.
- `webui/package_webui.py`: packages a shareable WebUI build from `serve.py`,
  `..\webui\`, and displayed media files under `..\export_full\`.

## WebUI Story Helpers

These are kept because the WebUI story builders import or use them:

- `recover_timeline_line_orders.py`
- `recover_mission_timelines.py`
- `scene_order_gap_shared.py`

## Unity Shader Lab

No active shader-lab scripts are present directly under this `scripts/`
directory in the current checkout. Shader-lab helpers should live inside
`../unity_endfield_graph_shader_lab/` unless they are promoted into a shared
WebUI/export workflow.

## Archived

Older one-off recovery utilities live in `../memory/scripts_archive/`. UE5
pose-demo helpers now live with the UE project under
`../ue5_zhuangfy_pose_demo 5.3/Scripts/`. Put new experiments in `../scratch/`
and move observations or conclusions to `../memory/` when they need to be kept.
