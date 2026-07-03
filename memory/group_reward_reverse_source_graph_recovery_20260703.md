# Group Reward Reverse Source Graph Recovery - 2026-07-03

## Context

Two group-level reward references already had forward source-graph edges but no
central reverse mapping from reward nodes back to their group owners:

- `factory_tech_group_rewards`
- `game_mechanic_group_first_pass_reward`

This left reward-centered queries unable to directly answer which factory tech
group or game-mechanic group used a reward.

## Implementation

`tools/endfield_source_graph.py` now maps those edge kinds in
`add_reward_ref_edge`:

- `reward_used_by_factory_tech_group`
- `reward_used_by_game_mechanic_group_first_pass`

No table-specific ingestion changes were needed.

## Validation

Focused validation graph:

```text
factory_tech_group_rewards 2 reward_used_by_factory_tech_group 2
game_mechanic_group_first_pass_reward 9 reward_used_by_game_mechanic_group_first_pass 9
```

Sample reverse evidence:

```text
reward:reward_blackbox_common_1
  reward_used_by_factory_tech_group -> factory_tech_group:tech_group_tundra

reward:reward_world_energy_point01
  reward_used_by_game_mechanic_group_first_pass -> game_mechanic_group:world_energy_point_group01
```

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query reward_blackbox_common_1 --kind reward --db tmp\group_reward_reverse_validation.sqlite --limit 12
python tools\endfield_source_graph.py query reward_world_energy_point01 --kind reward --db tmp\group_reward_reverse_validation.sqlite --limit 12
```

Both queries showed the original forward reward edges and the new reverse
reward-to-group edges.
