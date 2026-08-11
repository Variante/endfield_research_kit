---
name: endfield-source-graph
description: Query and rebuild Endfield's local SQLite evidence graph with tools/endfield_source_graph.py. Use for story keys, dialog lines, options and routes, actors, audio, videos, assets, materials, map or level rows, structured-table references, and explaining why generated WebUI entities are linked.
---

# Endfield Source Graph

Use the graph for evidence lookup, not as authority to change recovery logic.
When the task is primarily a WebUI refresh or frontend change, use the
`endfield-webui-workflow` skill and treat this skill as supporting evidence.

## Query First

Prefer graph queries over broad text searches for known identifiers:

```bat
python tools\endfield_source_graph.py query dlg_c28m3_23
python tools\endfield_source_graph.py query option_dlg_c28m3_23_2_001
python tools\endfield_source_graph.py query au_dlg_e1m1_5_001
python tools\endfield_source_graph.py query radio_sm2l6m1_29 --kind story
python tools\endfield_source_graph.py story dlg_e1m1_5 --limit-lines 8
```

Use `--kind story`, `--kind option`, or `--kind line` to disambiguate. Use the
`story` view for compact recovered order, option anchors/routes, merge lines,
and edge provenance. If built-in output is insufficient, inspect SQLite tables
`nodes`, `edges`, `aliases`, and `files` directly with a parameterized query.

Report the resolved relationship and its evidence source when provenance
affects confidence. Do not turn availability, registration, proximity, or code
address order into ownership, playback, or mission order.

## Build or Refresh

The canonical database is
`reports/source_graph/endfield_source_graph.sqlite`. If it is missing or stale,
first run:

```bat
python scripts\verify_export_freshness.py
```

Refresh stale installed-game inputs with `export.bat --from-game`. Then prefer
the WebUI-relevant graph:

```bat
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

This retains only exact AssetMap source/PathID rows consumed by relevant WebUI
material, shader, texture, and FMV edges. Use a full build only when exhaustive
Unity-object/PathID investigation or generated follow-up reports are required:

```bat
python tools\endfield_source_graph.py build
```

The graph consumes generated WebUI data and canonical evidence reports. Before
deleting a report, search for graph readers or regenerate it before the next
build. Keep graph outputs under `reports/source_graph/`, revisitable probes
under `scratch/source_graph/<task>/`, and disposable copies under
`tmp/source_graph/<task-or-run>/`.

## Evidence Boundaries

- `webui/story`: generated Story, line, actor, audio, option, and video data.
- `scene_graph`: direct DialogTree or scene-link branch evidence.
- `option_branch_risk`: inferred hints, not direct branch proof.
- `timeline_route_branch`: recovered Runtime Jump Track option routes.
- `story_source_links`: mission/runtime references to Story keys.
- Mission Pipeline environment context: non-owning availability evidence.
- Native runtime receivers: playback control flow with unresolved mission
  ownership; never a mission edge or Story ordering source.
- `AnimeStudio/maps`: exact relevant consumers in focused mode and all map rows
  only in exhaustive mode.
