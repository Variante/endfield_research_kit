# Memory Notes

This directory holds durable conclusions, investigation summaries, and status
snapshots that should not live in the root README or generated reports.

Keep this directory flat. Use one Markdown file per durable topic, with the
current conclusion first and old session history folded into concise evidence
notes. Generated JSON/Markdown reports belong under `reports/`; disposable
experiments belong under `scratch/` or `tmp/`.

## Current Files

- `webui_recovery.md`: static WebUI recovery pipeline, page data contracts,
  DialogIdTable registry behavior, update tracking, packaging, serving, and
  export benchmark notes.
- `character_unity_export_workflow.md`: character recovery path for exporting
  Endfield model, texture, material, animation, shader-reference, and static
  prop resources into the Unity viewer project.
- `game_story_recovery.md`: single source of truth for Story reconstruction,
  source-only mission/scene partial order, quest attachment, LevelScript
  control flow, dialog branches, option-route controls, e0m0 calibration,
  narrative-video placement, graph queries, and the current recovery queue.
- `source_graph_database.md`: local SQLite source graph build/query workflow,
  output shape, source coverage, and current limitations.

## Writing Rules

- Start with the current conclusion, then the evidence that matters.
- Prefer links to generated reports over copying their full contents.
- Keep commands that are still useful for future work.
- Remove or fold chronological logs once their conclusions are captured.
- Do not recreate nested README-shaped archive folders.
