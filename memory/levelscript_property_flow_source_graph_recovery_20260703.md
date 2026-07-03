# LevelScript Property Flow Source Graph Recovery - 2026-07-03

## Summary

Promoted `reports/mission_order/levelscript_property_flow_CN.json` into the
source graph as queryable evidence.

The report bridges MissionRuntime `CheckLevelScriptProperty*` conditions to
decoded LevelScript files when the same `(mapId, scriptId, key)` appears in the
script bytes. This is useful runtime/control evidence, but the report itself is
explicitly not promotable to strong story order edges because setter/gate walks
still need independent proof.

The empty `levelscript_gate_audit_CN.json` was not ingested; it currently reports
0 gate rows and 0 target walks.

## Node And Edge Shapes

New node kinds:

- `level_script_property_flow`
- `level_script_property_record`
- `level_script_property_opcode`
- `level_script_property_bridge_status`

New edge kinds include:

- `levelscript_property_flow_audit_has_row`
- `level_script_property_flow_bridge_status`
- `level_script_property_flow_in_level`
- `level_script_property_flow_uses_script`
- `level_script_property_flow_for_property`
- `level_script_property_flow_checked_by_mission`
- `mission_checks_level_script_property_flow`
- `level_script_property_flow_checked_by_quest`
- `level_script_property_flow_checker_story_ref`
- `level_script_property_flow_has_record_hit`
- `level_script_property_record_opcode`
- `level_script_property_flow_nearby_story_ref`

The builder runs this pass after timeline option-flow and story-source-link
ingests, so existing story, mission, level, and LevelScript nodes can receive the
additional audit evidence.

## Validation

Static checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Focused temporary graph ingest called only
`ingest_levelscript_property_flow_audit()` against the current report.

Focused ingest counts:

| Item | Count |
| --- | ---: |
| `level_script_property_flow` nodes | 171 |
| `level_script_property_record` nodes | 61 |
| `level_script_property_opcode` nodes | 13 |
| `level_script_property_bridge_status` nodes | 3 |
| `level_script` nodes | 132 |
| `level_script_property` nodes | 171 |
| `level` nodes | 23 |
| `map` nodes | 2 |
| `mission` nodes | 68 |
| `quest_task` nodes | 163 |
| `story` nodes | 25 |
| `dataset` nodes | 1 |
| `file` nodes | 1 |
| `levelscript_property_flow_audit_has_row` edges | 171 |
| `level_script_property_flow_bridge_status` edges | 171 |
| `level_script_property_flow_in_level` edges | 171 |
| `level_script_property_flow_uses_script` edges | 171 |
| `level_script_property_flow_for_property` edges | 171 |
| `level_script_property_flow_checked_by_mission` edges | 171 |
| `mission_checks_level_script_property_flow` edges | 171 |
| `level_script_property_flow_checked_by_quest` edges | 200 |
| `level_script_property_flow_checker_story_ref` edges | 12 |
| `level_script_property_flow_has_record_hit` edges | 61 |
| `level_script_property_record_opcode` edges | 61 |
| `level_script_property_flow_nearby_story_ref` edges | 21 |
| `levelscript_property_flow_audit` file rows | 1 |

Bridge status split:

| Status | Rows |
| --- | ---: |
| `bridgeFound` | 63 |
| `bridgeMissing` | 105 |
| `bridgeSubstringOnly` | 3 |

## Notes

This closes a report-to-graph explainability gap for LevelScript property
conditions. It should be used to answer "which mission/quest checks this
LevelScript property and is the key visible in the script bytes?", not "what is
the final chronological story edge?".
