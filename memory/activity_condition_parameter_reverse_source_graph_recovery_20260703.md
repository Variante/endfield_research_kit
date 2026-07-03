# Activity Condition Parameter Reverse Source-Graph Recovery - 2026-07-03

## Scope

Activity condition parameter parsing already emitted typed forward references
from `activity_condition` nodes to system jumps, rewards, items, characters,
achievements, stages, activities, dungeons, and missions. This pass added
reverse edges so those target nodes can recover which activity conditions
reference them.

## Added Reverse Edges

- `system_jump_used_by_activity_condition_param`
- `reward_used_by_activity_condition_param`
- `item_used_by_activity_condition_param`
- `character_used_by_activity_condition_param`
- `achievement_used_by_activity_condition_param`
- `activity_stage_used_by_activity_condition_param`
- `activity_used_by_activity_condition_param`
- `dungeon_used_by_activity_condition_param`
- `mission_used_by_activity_condition_param`

The direct `stageId` condition field now also emits
`activity_stage_used_by_activity_condition_param`.

## Validation

Focused temp graph:
`tmp/activity_condition_param_reverse_validate.sqlite`

Counts from `ingest_activity_achievement_semantics()` plus
`ingest_activity_catalog_semantics()`:

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `activity_condition_refs_system_jump` | 0 | `system_jump_used_by_activity_condition_param` | 0 |
| `activity_condition_refs_reward` | 0 | `reward_used_by_activity_condition_param` | 0 |
| `activity_condition_refs_item` | 4 | `item_used_by_activity_condition_param` | 4 |
| `activity_condition_refs_character` | 0 | `character_used_by_activity_condition_param` | 0 |
| `activity_condition_refs_achievement` | 0 | `achievement_used_by_activity_condition_param` | 0 |
| `activity_condition_refs_stage` | 210 | `activity_stage_used_by_activity_condition_param` | 210 |
| `activity_condition_refs_activity` | 0 | `activity_used_by_activity_condition_param` | 0 |
| `activity_condition_refs_dungeon` | 31 | `dungeon_used_by_activity_condition_param` | 31 |
| `activity_condition_refs_mission` | 70 | `mission_used_by_activity_condition_param` | 70 |

CLI smoke checks:

- `python tools\endfield_source_graph.py query activity_conditional_multistage_1_stage_1 --kind activity_stage --db tmp\activity_condition_param_reverse_validate.sqlite --limit 12`
  showed reverse condition-parameter links from the stage.
- `python tools\endfield_source_graph.py query e1m1 --kind mission --db tmp\activity_condition_param_reverse_validate.sqlite --limit 12`
  showed `mission_used_by_activity_condition_param`.

SQL samples confirmed:

- `dungeon:dung01_actmonster01` -> `activity_condition:dungeon_fighting_stage_1_complete_condition_1`
- `item:item_domain_jinlong_coupon` -> `activity_condition:SimulationTraining_task12_condition`

`python -m py_compile tools\endfield_source_graph.py` passed.
