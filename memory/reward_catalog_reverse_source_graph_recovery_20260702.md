# Reward Catalog Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for reward catalog side tables covering
gift items, check-in stages, daily activation rewards, money config/record
rows, money exchanges, important item show groups, and important reward item
configs.

New reverse edge families include:

- `tag_has_gift_prefer_config`
- `gift_config_for_item`
- `gift_prefer_tag_used_by_gift_item`
- `tag_used_by_gift_item`
- `checkin_config_for_activity`
- `checkin_stage_in_checkin`
- `reward_used_by_checkin_stage`
- `character_featured_by_checkin_stage`
- `weapon_featured_by_checkin_stage`
- `reward_used_by_daily_activation`
- `item_has_money_config`
- `item_has_money_record`
- `item_used_as_money_exchange_source`
- `item_received_from_money_exchange`
- `important_item_show_entry_in_group`
- `item_type_used_by_important_item_show`
- `item_has_important_reward_config`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\reward_catalog_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,010` nodes
- `3,177,389` edges
- `2,277,554` aliases

Parity checks:

- `gift_prefer_tag_resolves_to_tag`: `6`
- `tag_has_gift_prefer_config`: `6`
- `item_has_gift_config`: `14`
- `gift_config_for_item`: `14`
- `gift_item_prefer_tag`: `14`
- `gift_prefer_tag_used_by_gift_item`: `14`
- `gift_item_hobby_tag`: `28`
- `tag_used_by_gift_item`: `28`
- `activity_has_checkin_config`: `14`
- `checkin_config_for_activity`: `14`
- `checkin_has_stage`: `114`
- `checkin_stage_in_checkin`: `114`
- `checkin_stage_reward`: `114`
- `reward_used_by_checkin_stage`: `114`
- `checkin_stage_featured_character`: `1`
- `character_featured_by_checkin_stage`: `1`
- `checkin_stage_featured_weapon`: `1`
- `weapon_featured_by_checkin_stage`: `1`
- `daily_activation_reward_grants`: `5`
- `reward_used_by_daily_activation`: `5`
- `money_config_item`: `5`
- `item_has_money_config`: `5`
- `money_record_item`: `2`
- `item_has_money_record`: `2`
- `money_exchange_source_item`: `2`
- `item_used_as_money_exchange_source`: `2`
- `money_exchange_target_item`: `2`
- `item_received_from_money_exchange`: `2`
- `important_item_show_has_entry`: `4`
- `important_item_show_entry_in_group`: `4`
- `important_item_show_entry_item_type`: `4`
- `item_type_used_by_important_item_show`: `4`
- `important_reward_item_ref`: `12`
- `item_has_important_reward_config`: `12`

Sample evidence:

- `gift_item:item_gift_jinlong_1 -> item:item_gift_jinlong_1` as
  `gift_config_for_item`, source `GiftItemTable`, evidence `id`
- `reward:reward_activity_checkin_agline_1 -> checkin_stage:activity_checkin_agline:1`
  as `reward_used_by_checkin_stage`, source `CheckInRewardTable`, evidence
  `rewardId`
- `item:item_originium_recharge -> money_exchange:item_originium_to_item_diamond`
  as `item_used_as_money_exchange_source`, source `MoneyExchangeTable`,
  evidence `sourceMoneyId`
- `item_type:13 -> important_item_show_entry:1:13` as
  `item_type_used_by_important_item_show`, source `ImportantItemShowTable`,
  evidence `type`

## Notes

These edges improve numerical/economy recovery by making catalog lookups
bidirectional from items, rewards, tags, activities, characters, weapons, money
items, and item types back to the authored reward catalog tables that reference
them.
