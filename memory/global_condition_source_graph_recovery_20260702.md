# Global Condition Source Graph Recovery - 2026-07-02

A focused source-graph pass now ingests the shared condition/gating tables from
`export_full/structured/StreamingAssets/Table/`:

- `ConditionTable.json`
- `GlobalVarTable.json`
- `TimeRangeTable.json`

This closes a small but important semantic gap from the original game data
understanding report: table rows can now resolve global condition IDs into
first-class graph nodes instead of leaving unlock/gate semantics only as opaque
row payloads.

Validation build:

```bat
python tools\endfield_source_graph.py build --db tmp\condition_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- Nodes: 1,583,396
- Edges: 2,956,731
- Aliases: 2,149,169

New/updated condition-layer node counts in the validation DB:

- `condition`: 19
- `condition_type`: 8
- `condition_parameter`: 13
- `condition_parameter_literal`: 1
- `compare_operator`: 2
- `global_variable`: 131
- `time_range`: 219

New direct `ConditionTable` relationships include:

- `defines_condition`
- `condition_has_type`
- `condition_compare_operator`
- `condition_has_subcondition`
- `condition_has_parameter`
- `condition_parameter_item`
- `condition_parameter_quest`
- `condition_parameter_value`

The pass intentionally keeps parameter interpretation conservative. String
parameters are linked to obvious item, quest, mission, activity, character, and
time-range nodes by ID prefix; unclassified values remain
`condition_parameter_literal` nodes with raw value metadata. This avoids
claiming runtime formula semantics that are not proven yet.

The local validation also required a small uncommitted compatibility fix in the
currently dirty `scripts/build_data_index.py`: the dirty working tree had added
a damage-action decoder reference without the corresponding consume-style
wrapper. That file contains pre-existing unrelated edits, so it was not staged
with this source-graph recovery commit.
