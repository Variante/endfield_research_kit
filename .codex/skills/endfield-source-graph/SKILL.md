---
name: endfield-source-graph
description: Quickly look up Endfield repo evidence with tools/endfield_source_graph.py. Use when Codex needs to answer questions about story keys, dialog lines, options, option routes/branch evidence, actors, audio ids, narrative videos, assets, materials, map/level rows, structured table references, or "why do we think X links to Y?" from the local SQLite source graph.
---

# Endfield Source Graph

Use this skill for fast evidence lookup, not for changing WebUI recovery logic.
If the task is primarily about WebUI refresh, frontend behavior, inline SNS
images, or browser packaging/serving, open
`.codex/skills/endfield-webui-workflow/SKILL.md` first and use this graph skill
only as supporting evidence.
The graph is a local SQLite database built from WebUI data, source links,
selected tables, assets, materials, character manifests, and optional
AnimeStudio maps.

## Quick Lookup

Prefer the graph before wide text search when the user asks to look up a known
story key, option id, actor, asset, audio id, map/level id, or evidence link.

```bat
python tools\endfield_source_graph.py query dlg_c28m3_23
python tools\endfield_source_graph.py query option_dlg_c28m3_23_2_001
python tools\endfield_source_graph.py query au_dlg_e1m1_5_001
python tools\endfield_source_graph.py query radio_sm2l6m1_29 --kind story
python tools\endfield_source_graph.py story dlg_e1m1_5 --limit-lines 8
```

The query command returns matching nodes/aliases plus neighbors of the first
match. Exact aliases and typed node ids are preferred over fuzzy matches, and
`--kind story`, `--kind option`, or `--kind line` can narrow a noisy query.

The story command returns a compact per-story arrangement: recovered line order,
option groups, anchors, option first/path/merge lines, and the evidence source
for each branch edge. Use it when a WebUI recovery issue needs a quick
line-order or option-route explanation.

## Build Or Refresh

If `reports/source_graph/endfield_source_graph.sqlite` is missing or clearly
stale, first verify that its exported inputs are current:

```bat
python scripts\verify_export_freshness.py
```

If the guard reports stale installed-game sources, refresh with
`export.bat --export-from-game` before rebuilding the graph. Then use the
WebUI-relevant build first for story/option/audio and Presentation/Combat work:

```bat
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

This still scans original AssetMaps but inserts only exact material, shader,
texture, and FMV source/PathID consumers. Use the full build only when generic
Unity-object/PathID lookup or generated follow-up reports matter:

```bat
python tools\endfield_source_graph.py build
```

Generated graph outputs live under `reports/source_graph/` and are ignored by
git. Do not confuse them with WebUI data; they are investigation artifacts.

The graph also reads canonical generated evidence from
`reports/story/build/`, `reports/story/recovery/options/`, and
`reports/mission_order/`. Treat those files as report-to-report inputs: do not
remove them during cleanup unless their consumer is retired or they will be
regenerated before the next graph build. Keep graph outputs inside the existing
`reports/source_graph/` topic root, never loose at `reports/`.

Put revisitable graph experiments under `scratch/source_graph/<task>/` and
disposable databases or query exports under `tmp/source_graph/<task-or-run>/`.
Do not create loose SQLite files at the root of `scratch/` or `tmp/`, and delete
temporary graph copies after the result is validated.

## Exact Evidence Queries

When the built-in query is too broad, query SQLite directly. Useful tables:
`nodes(id, kind, name, source, path, data)`, `edges(src, dst, kind, source,
evidence, data)`, `aliases(alias, node_id, kind, source)`, `files(...)`.

Examples:

```bat
python -c "import sqlite3; c=sqlite3.connect('reports/source_graph/endfield_source_graph.sqlite'); print(c.execute(\"SELECT dst,kind,source,evidence FROM edges WHERE src=? ORDER BY kind,dst\", ('option:option_dlg_c28m3_23_2_001',)).fetchall())"
```

```bat
python -c "import sqlite3; c=sqlite3.connect('reports/source_graph/endfield_source_graph.sqlite'); print(c.execute(\"SELECT src,dst,kind,source,evidence FROM edges WHERE source='timeline_route_branch' AND (src LIKE '%c28m3_23%' OR dst LIKE '%c28m3_23%') ORDER BY src,dst\").fetchall())"
```

## Interpreting Sources

- `webui/story`: generated story, line, actor, audio, option, video data.
- `scene_graph`: direct dialog-tree or sceneGraphLinks branch evidence.
- `option_branch_risk`: inferred option branch hints from WebUI recovery.
- `timeline_route_branch`: Runtime Jump Track recovered option routes.
- `story_source_links`: mission/runtime source references to story keys.
- `webui/mission_pipeline/env_talk_context`: exact same-level,
  complete-NPC-set atmospheric switcher state context. It is non-owning
  availability evidence, never playback or order evidence.
- `webui/mission_pipeline/native_runtime_receivers`: exact current-build
  receiver-to-Story playback control flow with unresolved mission ownership.
  It never supplies a mission/quest edge or Story order.
- `AnimeStudio/maps`: Unity AssetMap entries; exact WebUI consumers in relevant
  mode and all entries in exhaustive mode.

For user answers, report both the resolved relationship and its evidence source
when the distinction matters.
