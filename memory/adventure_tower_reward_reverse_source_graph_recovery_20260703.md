# Adventure and Tower Reward Reverse Source Graph Recovery - 2026-07-03

## Context

`AdventureLevelTable` and `TowerDefenseTable` already emitted forward reward
edges into the source graph:

- `adventure_level_reward`
- `tower_defense_stage_reward`

Those edges made it possible to start from an adventure level or tower-defense
stage and reach its reward id, but reward-centered queries did not show where
those rewards were used.

## Implementation

`tools/endfield_source_graph.py` now adds reverse reward edges for those two
existing forward edge kinds through `add_reward_ref_edge`:

- `reward_used_by_adventure_level`
- `reward_used_by_tower_defense_stage`

No new table ingestion path was needed; the change only completes reverse
semantics for already-ingested `rewardId` fields.

## Validation

Focused validation graph:

```text
adventure_level_reward 59 reward_used_by_adventure_level 59
tower_defense_stage_reward 22 reward_used_by_tower_defense_stage 22
```

Sample reverse evidence:

```text
reward:reward_adventure_levelup_10
  reward_used_by_adventure_level -> adventure_level:10 (rewardId)

reward:reward_stm_hongs_1_1_auto
  reward_used_by_tower_defense_stage -> tower_defense_stage:stm_hongs_1_1_auto (rewardId)
```

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query reward_adventure_levelup_10 --kind reward --db tmp\adventure_tower_reward_reverse_validation.sqlite --limit 20
python tools\endfield_source_graph.py query reward_stm_hongs_1_1_auto --kind reward --db tmp\adventure_tower_reward_reverse_validation.sqlite --limit 20
```

Both queries showed the original forward edge and the new reverse edge from the
reward node.
