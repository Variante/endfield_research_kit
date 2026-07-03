# Activity Achievement Reverse Source Graph Recovery - 2026-07-03

## Context

Activity, stage, task, and achievement tables already emitted useful forward
edges for authored conditions, achievements, groups, levels, and statistic
rows. Reverse lookup from a known condition, achievement, group, level, or
statistic still required manual SQL, which made activity and achievement
investigation less direct than neighboring catalog families.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for existing
activity/achievement relationships:

- `activity_condition_used_by_stage`
- `activity_condition_unlocks_stage`
- `activity_condition_completes_stage`
- `activity_condition_used_by_achievement_plate`
- `activity_condition_used_by_adventure_book_task`
- `activity_condition_used_by_adventure_task`
- `activity_condition_used_by_benefit`
- `activity_condition_completes_task`
- `activity_condition_used_by_push`
- `achievement_used_by_activity`
- `achievement_group_in_category`
- `achievement_in_group`
- `achievement_level_for_achievement`
- `achievement_condition_for_level`
- `achievement_tracked_by_statistic`

The reverse edges preserve the same table source, evidence path, and any
payload data as the forward relationship. Some generic reverse edge kinds are
currently zero-count in this export but are emitted by shared helpers when
matching future rows appear.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\activity_achievement_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,820,254 edges.
Forward/reverse counts matched:

- `stage_has_condition`: 41 / `activity_condition_used_by_stage`: 41
- `stage_has_unlock_condition`: 41 / `activity_condition_unlocks_stage`: 41
- `stage_has_complete_condition`: 139 / `activity_condition_completes_stage`: 139
- `achievement_has_plate_condition`: 62 / `activity_condition_used_by_achievement_plate`: 62
- `adventure_book_task_condition`: 86 / `activity_condition_used_by_adventure_book_task`: 86
- `adventure_task_condition`: 0 / `activity_condition_used_by_adventure_task`: 0
- `activity_benefit_condition`: 0 / `activity_condition_used_by_benefit`: 0
- `task_has_complete_condition`: 16 / `activity_condition_completes_task`: 16
- `push_has_condition`: 0 / `activity_condition_used_by_push`: 0
- `activity_has_achievement`: 2 / `achievement_used_by_activity`: 2
- `achievement_category_has_group`: 12 / `achievement_group_in_category`: 12
- `achievement_group_has_achievement`: 114 / `achievement_in_group`: 114
- `achievement_has_level`: 156 / `achievement_level_for_achievement`: 156
- `achievement_level_has_condition`: 200 / `achievement_condition_for_level`: 200
- `achievement_statistic_tracks`: 3 / `achievement_tracked_by_statistic`: 3
