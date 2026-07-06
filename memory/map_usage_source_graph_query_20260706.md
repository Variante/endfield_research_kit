# Map Usage Source-Graph Query - 2026-07-06

## Scope

Improved `python tools/endfield_source_graph.py map-usage` and its
`level-usage` alias so one lookup can explain more of the authored map, level,
sublevel, spawner, enemy, map-mark, level-data, and level-script evidence already
present in the source graph.

This advances the world/asset-placement gap from the original understanding
report: the graph cannot simulate runtime streaming, but it can now show the
static authored references that connect a map or level to its visible data
surface.

## Evidence Covered

The command now resolves seeds across:

- `map`, `map_config`, `level`, `level_config`, `level_basic_info`, and
  `level_short_id_scene`
- `map_sublevel_brief` and `map_brief_info`
- `map_scene_state`, `map_variable`, `map_mark`, and `map_mark_template`
- `level_data`, `level_script`, `spawner_config`, `spawner_enemy_entry`, and
  `enemy`

It includes direct edge families for:

- map config definitions, domain/streaming asset refs, level ids, scene states,
  map variables, and scene-state condition refs
- level basic info, level config, level short ids, level data, and level script
  definitions
- map/sublevel/enemy brief rows
- map marks and map-mark templates
- mission/story/effect/buff/audio/asset references found in level data
- spawner enemy entries, spawn buffs, prewarn audio, and prewarn effects
- atmospheric NPC and interactive collection placement links

## Output Shape

`map-usage` still returns `edgeCounts` and raw `relations`, and now adds
`mapSummary`, grouped by:

- `mapConfig`
- `levelConfig`
- `mapLevels`
- `sceneStateConditions`
- `mapMarks`
- `levelScripts`
- `missionStory`
- `spawnersEnemies`
- `worldObjects`
- `gameplayRefs`
- `assets`

Useful examples:

```bat
python tools\endfield_source_graph.py map-usage map01 --kind map
python tools\endfield_source_graph.py level-usage map01_lv001 --kind level
python tools\endfield_source_graph.py map-usage sc_BattleGym_36800000002 --kind spawner_config
```

## Validation

Smoke checks verified:

- `map01` resolves as `map:map01` and exposes map config plus map/level edges.
- `map01_lv001` resolves as `level:map01_lv001` and exposes level basic/config,
  level data/script, mission runtime, map mark, atmospheric NPC, and interactive
  collection edge counts.
- `sc_BattleGym_36800000002` resolves as a `spawner_config` with authored enemy
  entries.

## Caveats

This is authored static table and decoded-config reference evidence. Some
level-to-map edges are explicit while others are prefix inferred; inspect each
relation's `evidence` field before treating it as a hard authored reference.
The query does not prove runtime streaming visibility, spawn activation,
quest-dependent world state, or player-position-dependent behavior.

## Next Story Target

A parallel subagent triage found the smallest decisive story-control-flow gap is
the audit-backed option-route conflict set:

```bat
python tools\endfield_source_graph.py option-gaps --audit-only --limit 10
python tools\endfield_source_graph.py story dlg_e6m1_10
python tools\endfield_source_graph.py story dlg_e6m4_14
```

That should be a good next increment after this world/map lookup cleanup.
