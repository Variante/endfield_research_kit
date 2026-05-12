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
stale, build it. Use the quick build first for story/option/audio lookups:

```bat
python tools\endfield_source_graph.py build --skip-asset-maps --skip-reference-rows --skip-followups
```

Use the full build only when asset-map or generated follow-up reports matter:

```bat
python tools\endfield_source_graph.py build
```

Generated graph outputs live under `reports/source_graph/` and are ignored by
git. Do not confuse them with WebUI data; they are investigation artifacts.

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
- `AnimeStudio/maps`: Unity AssetMap entries; slow/full build only.

For user answers, report both the resolved relationship and its evidence source
when the distinction matters.
