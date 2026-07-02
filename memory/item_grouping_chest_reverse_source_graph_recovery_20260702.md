# Item Grouping And Chest Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for item grouping, usable chest, and
limited-time alias relationships.

New reverse edges:

- `item -> item_type` as `item_listed_by_item_type`
- `item -> item_showing_type` as `item_listed_by_showing_type`
- `usable_item_chest -> item` as `usable_chest_config_for_item`
- `item -> usable_item_chest` as `item_random_in_usable_chest`
- `reward -> usable_item_chest` as `reward_used_by_usable_chest`
- `item -> limited_time_item_alias` as `item_has_limited_time_alias`
- `item_type -> item_type` as `item_type_used_by_limited_time_type`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\item_grouping_chest_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,009` nodes
- `3,150,669` edges
- `2,277,554` aliases

Parity checks:

- `item_type_lists_item`: `1,946`
- `item_listed_by_item_type`: `1,946`
- `item_showing_type_lists_item`: `1,946`
- `item_listed_by_showing_type`: `1,946`
- `item_uses_chest_config`: `36`
- `usable_chest_config_for_item`: `36`
- `usable_chest_random_item`: `5`
- `item_random_in_usable_chest`: `5`
- `usable_chest_reward`: `154`
- `reward_used_by_usable_chest`: `154`
- `limited_time_alias_resolves_item`: `28`
- `item_has_limited_time_alias`: `28`
- `limited_time_item_type_preset`: `5`
- `item_type_used_by_limited_time_type`: `5`

Sample evidence:

- `item:achv_item_test_1 -> item_type:100` as
  `item_listed_by_item_type`, source `ItemListByTypeTable`, evidence
  `list[0]`
- `item:achv_item_test_1 -> item_showing_type:0` as
  `item_listed_by_showing_type`, source `ItemListByShowingTypeTable`,
  evidence `list[1173]`
- `reward:reward_case_bp_random_1 -> usable_item_chest:item_case_bp_random_1`
  as `reward_used_by_usable_chest`, source `UsableItemChestTable`, evidence
  `rewardIdList[0]`

## Notes

This closes another inbound-query gap for item/economy recovery. Queries can
now start from an item, reward, or type bucket and follow authored grouping,
chest, and limited-time alias relationships without manual inbound edge scans.
The separate `memory/item_outcome_reverse_source_graph_recovery_20260702.md`
checkpoint records the `ItemTable.outcomeItemIds` reverse edge from the same
source-graph slice.
