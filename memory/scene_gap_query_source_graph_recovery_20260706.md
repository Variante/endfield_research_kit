# Scene Gap Query Source Graph Recovery - 2026-07-06

## Summary

Added a focused `scene-gaps` query shortcut to `tools/endfield_source_graph.py`
for reviewing the current scene-order gap hotlist from the source graph.

This is a diagnostic source-graph improvement only. It does not change Story
builder recovery logic, WebUI output, option overrides, or generated
conversation data.

## Current Evidence

Primary input remains `reports/scene_order_gap_report_CN.json`, which the graph
already ingests through `ingest_scene_order_gap_report()`.

The existing graph currently exposes:

- 35 `scene_order_gap` nodes.
- 21 `sceneOrderDisorder` warning edges.
- 15 `inferredOptionLayout` warning edges.
- 14 `inferredOptionResponse` warning edges.
- 29 direct line-order scenes and 6 partial line-order scenes.
- 18 authored option-layout scenes, 15 inferred option-layout scenes, and 2
  not-needed option-layout scenes.
- Placement evidence counts include 16 `sourceBackedSceneEdge`, 16
  `sourceBackedStoryCallContext`, 15 `levelscriptSpatialProximity`, 6
  `missionStoryRef`, 6 `sourceBackedHashTerminal`, 4
  `sourceBackedSceneSequence`, 2 `timelineEvidence`, and 1
  `scriptConditionQuestAttach`.

## New Query Surface

Use:

```bat
python tools\endfield_source_graph.py scene-gaps --limit 5
python tools\endfield_source_graph.py scene-gaps --warning inferredOptionResponse --limit 5
python tools\endfield_source_graph.py scene-gaps --warning sceneOrderDisorder --mission a1m4
python tools\endfield_source_graph.py scene-gaps --line-status partial
python tools\endfield_source_graph.py scene-gaps --option-status inferred
python tools\endfield_source_graph.py scene-gaps --placement timelineEvidence
python tools\endfield_source_graph.py scene-gaps --term dlg_a1m7_2
```

The command reads existing SQLite `scene_order_gap` nodes and edges, then emits
compact JSON with story key, mission, title, warning codes, line-order status
and reason, option-layout status and reason, inferred-option flags, placement
evidence kinds, line and option edge counts, source path, and aggregate
warning/status/evidence counts.

The command falls back to graph edge counts when the node payload was built
before newer report count fields were added.

## Validation

Validated with:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py scene-gaps --term dlg_a1m7_2 --limit 1
python tools\endfield_source_graph.py scene-gaps --warning sceneOrderDisorder --mission a1m4 --limit 5
python tools\endfield_source_graph.py scene-gaps --line-status partial --limit 2
python tools\endfield_source_graph.py scene-gaps --placement timelineEvidence --limit 5
```

Observed output matched the current 35-scene hotlist counts and returned expected
filtered records such as `dlg_a1m7_2`, `dlg_a1m4_1`, `dlg_e4m1_4`, and
`dlg_e9m2_14`.
