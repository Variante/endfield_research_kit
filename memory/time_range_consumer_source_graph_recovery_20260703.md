# Time Range Consumer Source Graph Recovery - 2026-07-03

## Context

`TimeRangeTable` already exposed authored time-range definitions, but most
consumer tables only preserved their `timeId`-style fields as payload values or
aliases. Starting from a known time range still did not reveal which activities,
stages, items, gacha pools, gifts, or achievements used it.

## Change

`tools/endfield_source_graph.py` now links authored time-range consumers to
`time_range` nodes with consumer-specific edges and a shared reverse edge:

- `activity_available_during`
- `activity_stage_available_during`
- `item_obtain_visibility_time`
- `gacha_pool_top_time`
- `gift_popularity_time`
- `achievement_display_time`
- `time_range_used_by`

The shared reverse edge preserves the original consumer edge kind in
`data.consumerEdge`, so a `time_range` query can show both the owner and the
relationship type.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\time_range_consumer_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,820,714 edges.
Validated edge counts:

- `defines_time_range`: 219
- `activity_available_during`: 64
- `activity_stage_available_during`: 115
- `item_obtain_visibility_time`: 31
- `gacha_pool_top_time`: 9
- `gift_popularity_time`: 7
- `achievement_display_time`: 4
- `time_range_used_by`: 230

The six forward consumer edge kinds total 230 edges, matching the 230 non-empty
source-table references found across `ActivityTable.timeId`,
activity-stage `timeId`, `ItemTable.notObtainShowTimeId`,
`GachaWeaponPoolTable.clientTopTimeId`, `GiftItemTable.finishPopularTimeId`,
and `AchievementTable.displayTimeId`. Those consumers reference 112 distinct
time-range ids, all present in `TimeRangeTable`.
