# Game Mechanic Condition Mission Parameter Source-Graph Recovery - 2026-07-03

## Scope

`GameMechanicConditionTable` condition parameters include mission and quest-task
IDs used as unlock/progress gates for dungeons, simulation training, world
energy points, and level checks. These strings previously fell through to
generic `game_mechanic` references, which created misleading nodes such as
`game_mechanic:a1m2_q#3`.

This pass classifies mission-shaped parameters before the generic fallback.

## Added Semantics

- `game_mechanic_condition_param_quest_task`
- `quest_task_used_by_game_mechanic_condition_param`
- `game_mechanic_condition_param_mission`
- `mission_used_by_game_mechanic_condition_param`

Quest-task IDs match mission prefixes plus `_q#N`; mission IDs match the same
prefix without the quest suffix.

## Validation

Focused temp graph:
`tmp/game_mechanic_mission_condition_validate.sqlite`

Counts from `ingest_game_mechanic_semantics()`:

| Edge kind | Count |
| --- | ---: |
| `game_mechanic_condition_param_quest_task` | 14 |
| `quest_task_used_by_game_mechanic_condition_param` | 14 |
| `game_mechanic_condition_param_mission` | 30 |
| `mission_used_by_game_mechanic_condition_param` | 30 |
| `game_mechanic_condition_param_mechanic` | 252 |
| `game_mechanic_condition_param_level` | 13 |
| `game_mechanic_condition_param_character` | 22 |

The 44 mission-like parameters formerly counted as generic mechanic refs, so
`game_mechanic_condition_param_mechanic` dropped from the prior 296 to 252.
The current export has 14 quest-task parameters and 30 mission parameters.

CLI smoke checks:

- `python tools\endfield_source_graph.py query dung01_actmonster01_cond_1 --kind game_mechanic_condition --db tmp\game_mechanic_mission_condition_validate.sqlite --limit 12`
  showed `a1m2_q#3` as `game_mechanic_condition_param_quest_task`.
- `python tools\endfield_source_graph.py query e1m8_q#4 --kind quest_task --db tmp\game_mechanic_mission_condition_validate.sqlite --limit 12`
  showed `quest_task_used_by_game_mechanic_condition_param` from
  `dung01_bossrush01_01_cond_1`.
- `python tools\endfield_source_graph.py query f1m5_q#21 --kind quest_task --db tmp\game_mechanic_mission_condition_validate.sqlite --limit 12`
  showed the simulation training gate from `stm_tundra_1_2_normal_cond2`.
- `python tools\endfield_source_graph.py query e2m5 --kind mission --db tmp\game_mechanic_mission_condition_validate.sqlite --limit 12`
  showed world energy point conditions using mission `e2m5`.
- `python tools\endfield_source_graph.py query m0m2 --kind mission --db tmp\game_mechanic_mission_condition_validate.sqlite --limit 12`
  showed `indie_levelcheck002_condition_2` using mission `m0m2`.

`python -m py_compile tools\endfield_source_graph.py` passed.
