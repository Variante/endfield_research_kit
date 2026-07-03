# Week Raid Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for week raid games, items, tech, delegates,
refresh levels, battlepass tiers, missions, rewards, dungeons, and currencies.

New reverse edge families include:

- `week_raid_game_has_tech`
- `week_raid_game_has_delegate`
- `week_raid_game_has_battlepass_tier`
- `dungeon_used_by_week_raid_game`
- `week_raid_domain_has_item`
- `week_raid_item_reverse_converted`
- `item_used_as_week_raid_currency`
- `mission_unlocks_week_raid_random_stage`
- `item_converted_from_week_raid_item`
- `currency_converted_from_week_raid_item`
- `item_unlocks_week_raid_tech`
- `week_raid_tech_type_has_tech`
- `week_raid_buff_tech_type_has_tech`
- `reward_used_by_week_raid_delegate`
- `mission_has_week_raid_delegate`
- `mission_required_by_week_raid_delegate`
- `item_used_as_week_raid_refresh_currency`
- `week_raid_refresh_level_for_game`
- `reward_used_by_week_raid_battlepass_tier`
- `item_used_by_week_raid_battlepass_tier`
- `week_raid_tech_required_by_battlepass_tier`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\week_raid_reverse_source_graph_2.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,010` nodes
- `3,178,878` edges
- `2,277,554` aliases

Populated parity checks:

- `week_raid_tech_game`: `31`
- `week_raid_game_has_tech`: `31`
- `week_raid_delegate_game`: `66`
- `week_raid_game_has_delegate`: `66`
- `week_raid_battlepass_tier_game`: `20`
- `week_raid_game_has_battlepass_tier`: `20`
- `week_raid_game_dungeon_ref`: `5`
- `dungeon_used_by_week_raid_game`: `5`
- `week_raid_item_domain`: `68`
- `week_raid_domain_has_item`: `68`
- `week_raid_item_reverse_original`: `34`
- `week_raid_item_reverse_converted`: `34`
- `week_raid_currency`: `2`
- `item_used_as_week_raid_currency`: `2`
- `week_raid_unlock_random_stage_mission`: `1`
- `mission_unlocks_week_raid_random_stage`: `1`
- `week_raid_item_converts_to_item`: `34`
- `item_converted_from_week_raid_item`: `34`
- `week_raid_item_converts_to_currency`: `21`
- `currency_converted_from_week_raid_item`: `21`
- `week_raid_tech_item`: `31`
- `item_unlocks_week_raid_tech`: `31`
- `week_raid_tech_type`: `31`
- `week_raid_tech_type_has_tech`: `31`
- `week_raid_tech_buff_type`: `7`
- `week_raid_buff_tech_type_has_tech`: `7`
- `week_raid_delegate_reward`: `66`
- `reward_used_by_week_raid_delegate`: `66`
- `week_raid_delegate_mission`: `66`
- `mission_has_week_raid_delegate`: `66`
- `week_raid_refresh_currency`: `1`
- `item_used_as_week_raid_refresh_currency`: `1`
- `week_raid_has_refresh_level`: `9`
- `week_raid_refresh_level_for_game`: `9`
- `week_raid_battlepass_tier_reward`: `20`
- `reward_used_by_week_raid_battlepass_tier`: `20`
- `week_raid_battlepass_reward_item`: `20`
- `item_used_by_week_raid_battlepass_tier`: `20`

Empty in this dataset:

- `week_raid_delegate_dependent_mission` / `mission_required_by_week_raid_delegate`
- `week_raid_battlepass_condition_tech` / `week_raid_tech_required_by_battlepass_tier`

## Notes

Week raid queries can now start from items, currencies, domains, missions,
rewards, dungeons, tech types, or battlepass tiers and traverse back to the
week raid game/delegate/tech/tier records that reference them.
