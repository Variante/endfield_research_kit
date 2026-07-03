# Mission Runtime Quest Reverse Links Source Graph Recovery - 2026-07-03

## Scope

Mission runtime quest narrative references now use target-side reverse edge
names keyed to `mission_runtime_quest`. This is a small follow-up to the
mission-runtime reverse-link pass: quest-owned `quest_references_narrative`
edges no longer fall back to reverse names derived from the raw forward edge.

## Graph Adjustment

The shared mission runtime narrative helper now maps `quest_task` owners to
`mission_runtime_quest`, producing typed reverse edges such as:

- `story_used_by_mission_runtime_quest`
- `radio_used_by_mission_runtime_quest`
- `sns_dialog_used_by_mission_runtime_quest`
- `remote_common_used_by_mission_runtime_quest`

## Validation

Static check:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Focused temp graph using only `ingest_decoded_config_semantics()`:

- `quest_references_narrative`: 579
- `story_used_by_mission_runtime_quest`: 462
- `radio_used_by_mission_runtime_quest`: 4
- `sns_dialog_used_by_mission_runtime_quest`: 108
- `remote_common_used_by_mission_runtime_quest`: 5

Sample evidence:

- `radio_sm1l1m9_1d2_Done` -> `sm1l1m9_q#29`
- `remotecomm_c16m3_1` -> `c16m3_q#22`
- `sns_a1m10_1` -> `a1m10_q#1`

## Interpretation

This does not add new quest parsing. It makes existing quest-local story,
radio, SNS, and remote-common references easier to query from the target side
and keeps them distinct from action, action-map, and condition reverse links.
