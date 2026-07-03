# System Jump Bind-System Source-Graph Recovery - 2026-07-03

## Scope

`SystemJumpTable.bindSystem` encodes the owning or unlocking game system for a
jump, using the same numeric values as `GameSystemConfigTable.unlockSystemType`.
The graph previously preserved `bindSystem` only in `system_jump` node data.
This pass added a lazy unlock-system lookup and explicit edges between jumps
and game-system config nodes.

## Added Semantics

- `system_jump_bound_to_game_system`
- `game_system_has_system_jump`

The edge evidence is `bindSystem`, with `{"bindSystem": ...}` preserved in edge
data.

## Validation

Focused temp graph:
`tmp/system_jump_bind_validate.sqlite`

The validation ingested both `ingest_settings_semantics()` and
`ingest_activity_achievement_semantics()` so `GameSystemConfigTable` and
`SystemJumpTable` were visible together.

Counts:

| Edge kind | Count |
| --- | ---: |
| `system_jump_bound_to_game_system` | 432 |
| `game_system_has_system_jump` | 432 |

Validated sample links:

| System jump | `bindSystem` | Game system |
| --- | ---: | --- |
| `item_obtain_activity_checkin_universe` | 1100 | `system_activity_center` |
| `item_obtain_adventurebook` | 652 | `system_adventure_book` |
| `jump_weapon` | 59 | `system_character` |
| `jump_wiki` | 55 | `system_wiki` |

CLI smoke checks:

- `python tools\endfield_source_graph.py query jump_wiki --kind system_jump --db tmp\system_jump_bind_validate.sqlite --limit 12`
  showed `system_jump_bound_to_game_system -> system_wiki`.
- `python tools\endfield_source_graph.py query system_wiki --kind game_system_config --db tmp\system_jump_bind_validate.sqlite --limit 12`
  showed wiki-related system jumps through `game_system_has_system_jump`.
- `python tools\endfield_source_graph.py query system_adventure_book --kind game_system_config --db tmp\system_jump_bind_validate.sqlite --limit 12`
  showed `item_obtain_adventurebook`, `jump_adventure_book`, and
  `jump_adventure_daily`.

`python -m py_compile tools\endfield_source_graph.py` passed.
