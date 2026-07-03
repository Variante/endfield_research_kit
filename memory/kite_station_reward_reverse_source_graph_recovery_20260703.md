# Kite Station Reward Reverse Source Graph Recovery - 2026-07-03

## Context

Kite Station photo-chain tables already emitted forward reward edges:

- `kite_station_task_reward_by_level`
- `kite_station_milestone_reward`

Those links let a task or milestone reach its reward id, but reward-centered
queries did not directly show which Kite Station task level or milestone used a
given reward.

## Implementation

`tools/endfield_source_graph.py` now maps those reward edge kinds to reverse
edges in `add_reward_ref_edge`:

- `reward_used_by_kite_station_task_level`
- `reward_used_by_kite_station_milestone`

No table-specific ingestion changes were needed.

## Validation

Focused validation graph:

```text
kite_station_task_reward_by_level 112 reward_used_by_kite_station_task_level 112
kite_station_milestone_reward 9 reward_used_by_kite_station_milestone 9
```

Sample reverse evidence:

```text
reward:reward_kitestation_milestone_jinlong_002_1
  reward_used_by_kite_station_milestone -> kite_station_milestone_reward:kitestation_002_1:1

reward:reward_kitestation_mission_jinlong_002_0
  reward_used_by_kite_station_task_level -> kite_station_entrust_task:kitestation_002_1:1
```

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query reward_kitestation_milestone_jinlong_002_1 --kind reward --db tmp\kite_station_reward_reverse_validation.sqlite --limit 12
python tools\endfield_source_graph.py query reward_kitestation_mission_jinlong_002_0 --kind reward --db tmp\kite_station_reward_reverse_validation.sqlite --limit 12
```

Both queries showed the original forward reward edge and the new reverse edge
from the reward node.
