# Memory Notes

This directory holds durable conclusions, investigation summaries, and status
snapshots that should not live in the root README or generated reports.

Keep this directory flat. Use one Markdown file per durable topic, with the
current conclusion first and old session history folded into concise evidence
notes. Generated JSON/Markdown reports belong under `reports/`; disposable
experiments belong under `scratch/` or `tmp/`.

## Current Files

- `webui_recovery.md`: static WebUI recovery pipeline, page data contracts,
  update tracking, packaging, serving, inline media, OCR intake, and current
  performance guidance.
- `game_story_recovery.md`: single source of truth for Story reconstruction,
  source-only mission/scene partial order, quest attachment, LevelScript
  control flow, dialog branches, option-route controls, e0m0 calibration,
  narrative-video placement, graph queries, and the current recovery queue.
- `game_data_recovery.md`: single source of truth for installed-data/VFS
  extraction, structured and binary config formats, MonoBehaviour gameplay
  payloads, source-graph semantics, evidence boundaries, and the current
  non-Story game-data recovery queue.
- `asset_recovery.md`: semantic asset catalog, model/prefab/entity bindings,
  materials, textures, shaders, animation/effect/audio/video usage, alias
  evidence, placement, and unresolved binding strategy.
- `animestudio_recovery.md`: local exporter architecture, AB/status semantics,
  selection and dependency lessons, conversion/parser recovery, managed
  references, shader bytecode, diagnostics, memory, and performance.
- `character_render_and_animation_recovery.md`: Unity character viewer,
  CharacterNPR/HGRP frame recovery, CharInfo presentation, roster and UI
  animation scope, validation, limitations, and next work.

## Writing Rules

- Start with the current conclusion, then the evidence that matters.
- Prefer links to generated reports over copying their full contents.
- Keep commands that are still useful for future work.
- Remove or fold chronological logs once their conclusions are captured.
- Do not recreate nested README-shaped archive folders.
- Put each active priority in its owning topic instead of maintaining a second
  cross-topic improvement-plan snapshot.
