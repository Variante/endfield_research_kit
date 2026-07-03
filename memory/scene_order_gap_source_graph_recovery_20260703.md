# Scene Order Gap Source Graph Recovery - 2026-07-03

## Summary

Promoted `reports/scene_order_gap_report_CN.json` into the source graph as a
queryable story-recovery hotlist.

The report is the current 35-scene CN gap inventory called out by the original
game-data understanding report. The graph now exposes each flagged scene, its
line-order status/reason/pattern, option-layout status/reason/pattern, warning
codes, scene-placement evidence kinds, ordered/uncovered lines, option-group
diagnostics, placement quests, neighboring story evidence, source files, and
timeline evidence.

This does not alter Story output or promote any inferred option placements. It
only makes the existing gap report easier to query and cross-reference.

## Node And Edge Shapes

New node kinds:

- `scene_order_gap`
- `scene_order_gap_warning`
- `scene_order_line_status`
- `scene_order_line_reason`
- `scene_order_line_pattern`
- `scene_order_option_layout_status`
- `scene_order_option_layout_reason`
- `scene_order_option_position_pattern`
- `scene_order_option_group_status`
- `scene_placement_evidence_kind`
- `scene_order_line_source`

New edge kinds include:

- `scene_order_gap_report_has_scene`
- `story_has_scene_order_gap`
- `scene_order_gap_for_story`
- `scene_order_gap_in_mission`
- `mission_has_scene_order_gap`
- `scene_order_gap_has_warning`
- `scene_order_gap_ordered_line`
- `scene_order_gap_uncovered_line`
- `scene_order_gap_line_source`
- `scene_order_gap_option_group`
- `scene_order_gap_option_group_has_option`
- `scene_order_gap_unauthored_option`
- `scene_order_gap_placement_quest`
- `scene_order_gap_placement_neighbor`
- `scene_order_gap_placement_source_file`
- `scene_order_gap_placement_timeline`

The builder runs this pass after the main-story order comparison and before the
LevelScript property-flow report, keeping it with the story-order evidence
cluster.

## Validation

Static checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Focused temporary graph ingest called only `ingest_scene_order_gap_report()`
against the current CN report.

Focused ingest counts:

| Item | Count |
| --- | ---: |
| `scene_order_gap` nodes | 35 |
| `scene_order_gap_warning` nodes | 3 |
| `scene_order_line_status` nodes | 2 |
| `scene_order_line_reason` nodes | 5 |
| `scene_order_line_pattern` nodes | 2 |
| `scene_order_option_layout_status` nodes | 3 |
| `scene_order_option_layout_reason` nodes | 4 |
| `scene_order_option_position_pattern` nodes | 4 |
| `scene_order_option_group_status` nodes | 2 |
| `scene_placement_evidence_kind` nodes | 8 |
| `scene_order_line_source` nodes | 34 |
| `story` nodes | 77 |
| `mission` nodes | 27 |
| `line` nodes | 430 |
| `option_group` nodes | 19 |
| `option` nodes | 33 |
| `quest_task` nodes | 13 |
| `timeline_asset` nodes | 2 |
| `file` nodes | 43 |
| `dataset` nodes | 1 |
| `scene_order_gap_report_has_scene` edges | 35 |
| `story_has_scene_order_gap` edges | 35 |
| `scene_order_gap_for_story` edges | 35 |
| `scene_order_gap_in_mission` edges | 35 |
| `mission_has_scene_order_gap` edges | 35 |
| `scene_order_gap_has_warning` edges | 50 |
| `scene_order_gap_has_placement_evidence` edges | 66 |
| `scene_order_gap_ordered_line` edges | 430 |
| `scene_order_gap_uncovered_line` edges | 7 |
| `scene_order_gap_line_source` edges | 34 |
| `defines_scene_order_line_source` edges | 22 |
| `scene_order_gap_option_group` edges | 19 |
| `scene_order_gap_option_group_status` edges | 19 |
| `scene_order_gap_option_group_after_line` edges | 19 |
| `scene_order_gap_option_group_fallback_anchor` edges | 19 |
| `scene_order_gap_option_group_has_option` edges | 33 |
| `scene_order_gap_unauthored_option` edges | 33 |
| `scene_order_gap_placement_quest` edges | 17 |
| `scene_order_gap_placement_neighbor` edges | 53 |
| `scene_order_gap_placement_source_file` edges | 68 |
| `scene_order_gap_placement_timeline` edges | 2 |
| `scene_order_gap_report` file rows | 1 |

Warning split:

| Warning | Scenes |
| --- | ---: |
| `inferredOptionLayout` | 15 |
| `inferredOptionResponse` | 14 |
| `sceneOrderDisorder` | 21 |

## Notes

This turns the remaining scene-order work into graph-addressable follow-up
tasks. Queries can now start from a story key or mission and see whether the
remaining issue is line coverage, option placement, option response inference,
or runtime placement evidence. The graph intentionally preserves uncertainty:
inferred option layouts and responses remain diagnostics, not promoted branch
truth.
