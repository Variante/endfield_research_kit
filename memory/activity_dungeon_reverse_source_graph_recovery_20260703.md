# Activity Dungeon Reverse Source-Graph Recovery - 2026-07-03

## Scope

This pass added direct reverse lookup edges for activity dungeon state and
fighting-stage table links already emitted by `tools/endfield_source_graph.py`.

The new edges are field-level inverses only. They do not infer activity
availability, runtime quest flow, or stage completion order beyond the source
table fields.

## Added Edges

- `level_has_activity_dungeon_state`
- `activity_stage_has_activity_dungeon_state`
- `activity_dungeon_show_state_has_activity_dungeon_state`
- `level_has_activity_dungeon_fighting_stage`
- `quest_task_used_by_activity_stage`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:

- `tmp/activity_dungeon_reverse_validate.sqlite`

The validation seeded `ingest_factory_interaction_lookup_semantics()`.

| Edge | Count |
| --- | ---: |
| `activity_dungeon_state_level` | 8 |
| `level_has_activity_dungeon_state` | 8 |
| `activity_dungeon_state_stage` | 8 |
| `activity_stage_has_activity_dungeon_state` | 8 |
| `activity_dungeon_state_show_state` | 8 |
| `activity_dungeon_show_state_has_activity_dungeon_state` | 8 |
| `activity_stage_level` | 8 |
| `level_has_activity_dungeon_fighting_stage` | 8 |
| `activity_stage_quest` | 8 |
| `quest_task_used_by_activity_stage` | 8 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `activity_dungeon_state` | 8 |
| `activity_dungeon_show_state` | 3 |
| `activity_stage` | 8 |
| `level` | 8 |
| `quest_task` | 7 |
