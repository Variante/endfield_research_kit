# Map Level Usage Source Graph Recovery - 2026-07-06

## Summary

Added a focused `map-usage` query shortcut to `tools/endfield_source_graph.py`
for reviewing map, level, sublevel, spawner, and enemy placement relations from
the source graph. `level-usage` is accepted as an alias.

This is a diagnostic source-graph improvement only. It does not change WebUI
output, map recovery, spawner decoding, enemy decoding, or generated reports.

## Current Evidence

The current SQLite graph has:

- 144 `map` nodes.
- 514 `level` nodes.
- 810 `level_data` nodes.
- 211 `map_sublevel_brief` nodes.
- 436 `spawner_config` nodes.
- 1,057 `spawner_enemy_entry` nodes.
- 289 `enemy` nodes.

Important existing edges include:

- `map_has_level` / `level_belongs_to_map`: 1,010 each.
- `level_has_level_data`: 810.
- `map_has_sublevel_brief` / `map_sublevel_brief_in_map`: 211 each.
- `map_sublevel_brief_has_enemy` / `enemy_used_by_map_sublevel_brief`: 1,009
  each.
- `defines_spawner_config`: 849.
- `spawner_config_has_enemy`: 1,057.
- `spawner_enemy_uses_enemy` / `enemy_used_by_spawner_entry`: 1,057 each.
- `spawner_enemy_starts_with_buff`: 1,599.
- `spawner_enemy_prewarn_audio`: 864.
- `spawner_enemy_prewarn_effect`: 980.
- `spawner_buff_uses_blackboard_key`: 677.

`reports/source_graph/map_level_index.json` currently exists but has an empty
`levels` list, so this query reads SQLite graph nodes and edges directly.

## New Query Surface

Use:

```bat
python tools\endfield_source_graph.py map-usage map01 --kind map --limit 5
python tools\endfield_source_graph.py map-usage map02 --kind map --limit 5
python tools\endfield_source_graph.py map-usage sc_base01_dg001_9900010011 --kind spawner_config --limit 5
python tools\endfield_source_graph.py map-usage eny_0007_mimicw_hdg005 --kind enemy --limit 5
python tools\endfield_source_graph.py level-usage 101 --kind level --limit 5
```

The command resolves the term as a `map`, `level`, `map_sublevel_brief`,
`level_data`, `spawner_config`, `spawner_enemy_entry`, or `enemy`, then emits
the seed node, aliases, direct edge counts, and compact relation samples.

It intentionally reports already-ingested graph evidence. It does not infer a
new level-to-spawner binding when the graph only has spawner config path and
enemy-library evidence.

## Validation

Validated with:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py map-usage map01 --kind map --limit 5
python tools\endfield_source_graph.py map-usage map02 --kind map --limit 5
python tools\endfield_source_graph.py map-usage sc_base01_dg001_9900010011 --kind spawner_config --limit 5
python tools\endfield_source_graph.py map-usage eny_0007_mimicw_hdg005 --kind enemy --limit 5
python tools\endfield_source_graph.py level-usage 101 --kind level --limit 3
```

Observed `map01` with 256 `map_has_level` edges and 55
`map_has_sublevel_brief` edges, and `map02` with 262 `map_has_level` edges and
59 `map_has_sublevel_brief` edges.

Observed `sc_base01_dg001_9900010011` resolving to a spawner config with two
enemy entries, including enemy levels and `forceToBattle` flags. Observed
`eny_0007_mimicw_hdg005` resolving to one map-sublevel use and three spawner
enemy entries with level/force evidence.

Observed `level-usage 101 --kind level` resolving through the numeric-level
alias to `level:map02_lv001`, with map, level-data, level-script, mission
runtime, map-mark, atmospheric NPC, and interactive-collection edge counts.
