# Map Level Index Source Graph Report Recovery - 2026-07-06

## Summary

Fixed `emit_map_level_index()` in `tools/endfield_source_graph.py` so the
generated source-graph follow-up report `reports/source_graph/map_level_index.json`
reflects the actual map, level, map-mark, sublevel, and sublevel-enemy graph.

This is a source-graph report improvement only. It does not change WebUI
output, game-data decoding, map recovery, spawner recovery, or any authored
override data.

## Problem

`reports/source_graph/map_level_index.json` existed but contained an empty
`levels` list even though the SQLite graph already had rich map/level evidence.

The cause was a stale edge-kind lookup in `emit_map_level_index()`: it queried
`has_map_mark`, but current graph ingestion writes `level_has_map_mark` and
`map_mark_in_level`.

## Current Report Shape

The refreshed report now contains:

- `summary`: aggregate map/level/mark/sublevel counts.
- `maps`: map entries with unique levels plus sublevel summaries and enemy
  references.
- `levels`: level entries with unique maps, mark counts and mark records,
  level-data records, plus level-script and mission-runtime counts.

The report intentionally uses existing SQLite graph edges only. It does not
infer missing direct level-to-spawner bindings; spawner evidence remains
available through `map-usage` / `level-usage` and spawner config nodes.

## Validation

Validated the emitter against the current graph database and refreshed the
ignored generated report.

Observed summary:

```json
{
  "mapCount": 142,
  "levelCount": 432,
  "mapLevelPairCount": 486,
  "mapMarkCount": 1877,
  "sublevelCount": 211,
  "sublevelEnemyRefCount": 1009,
  "levelDataCount": 810,
  "levelScriptCount": 3756,
  "missionRuntimeCount": 813
}
```

Additional checks:

- `map01` reports 66 unique levels, 55 sublevels, and 310 sublevel enemy
  references in the refreshed report.
- 16 level entries currently have map marks.
- The refreshed report carries 810 `levelData` records on level entries.
- `python -m py_compile tools\endfield_source_graph.py` passes.
