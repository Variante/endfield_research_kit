# Reward Reference Reverse Source Graph Recovery - 2026-07-03

## Context

Reward bundle contents already support item-first lookup, but several
reward-id reference edges were still easier to traverse from the consuming
system to the reward. Reward-centered queries could not directly enumerate all
mission runtime, dungeon, and game-mechanic consumers.

## Finding

`tools/endfield_source_graph.py` now emits reverse reward-reference edges for:

- `reward_used_by_mission_runtime`
- `reward_used_by_dungeon`
- `reward_used_by_dungeon_first_pass`
- `reward_used_by_dungeon_extra`
- `reward_used_by_dungeon_hunter`
- `reward_used_by_dungeon_custom`
- `reward_used_by_game_mechanic`
- `reward_used_by_game_mechanic_first_pass`
- `reward_used_by_game_mechanic_extra`
- `reward_used_by_game_mechanic_hunter`
- `reward_used_by_world_game_mechanic_first_pass`

Most of these use the shared `add_reward_ref_edge()` reverse map. Mission
runtime rewards are emitted directly next to `mission_runtime_rewards` because
that decoded-config path does not use the helper.

## Validation

Focused temporary graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DB: `tmp/reward_ref_reverse.sqlite`

Forward/reverse counts matched:

- `mission_runtime_rewards`: 494 / reverse 494
- `dungeon_reward`: 30 / reverse 30
- `dungeon_first_pass_reward`: 147 / reverse 147
- `dungeon_extra_reward`: 39 / reverse 39
- `dungeon_hunter_reward`: 10 / reverse 10
- `dungeon_custom_reward`: 12 / reverse 12
- `game_mechanic_reward`: 88 / reverse 88
- `game_mechanic_first_pass_reward`: 152 / reverse 152
- `game_mechanic_extra_reward`: 39 / reverse 39
- `game_mechanic_hunter_reward`: 10 / reverse 10
- `world_game_mechanic_first_pass_reward`: 5 / reverse 5

Sample reverse edges showed first-pass reward ids such as
`reward:reward_blackbox_basic_1` pointing back to their `dungeon:*` consumers
with the original `firstPassRewardId` evidence.
