# Item Submission Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for item submission, bottle/liquid,
food-submit stage, AP recovery, valuable depot, collection, and recycle-bin
relationships.

New reverse edge families include:

- `item_required_by_submit_item`
- `item_has_full_bottle_config`
- `item_used_as_full_bottle_container`
- `item_liquid_used_by_full_bottle`
- `item_has_empty_bottle_config`
- `item_accepted_by_empty_bottle`
- `item_full_variant_of_empty_bottle`
- `activity_has_food_submit_stage`
- `activity_stage_has_food_submit_overlay`
- `reward_used_by_food_submit_stage`
- `system_jump_used_by_food_submit_stage`
- `ap_recovery_config_for_item`
- `item_type_allowed_by_valuable_depot`
- `item_used_by_collection_entry`
- `item_used_as_collection_bandwidth`
- `collection_entry_merged_from`
- `domain_has_recycle_bin`
- `level_has_recycle_bin_config`
- `recycle_bin_level_in_bin`
- `reward_used_by_recycle_bin_level`
- `recycle_bin_listed_for_level`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\item_submission_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,010` nodes
- `3,178,345` edges
- `2,277,554` aliases

Parity checks:

- `submit_item_requires_item`: `308`
- `item_required_by_submit_item`: `308`
- `full_bottle_item_ref`: `67`
- `item_has_full_bottle_config`: `67`
- `full_bottle_empty_container`: `67`
- `item_used_as_full_bottle_container`: `67`
- `full_bottle_contains_liquid`: `67`
- `item_liquid_used_by_full_bottle`: `67`
- `empty_bottle_item_ref`: `7`
- `item_has_empty_bottle_config`: `7`
- `empty_bottle_accepts_liquid`: `67`
- `item_accepted_by_empty_bottle`: `67`
- `empty_bottle_full_variant`: `67`
- `item_full_variant_of_empty_bottle`: `67`
- `food_submit_stage_activity`: `16`
- `activity_has_food_submit_stage`: `16`
- `food_submit_stage_id_overlay`: `16`
- `activity_stage_has_food_submit_overlay`: `16`
- `food_submit_stage_reward`: `14`
- `reward_used_by_food_submit_stage`: `14`
- `food_submit_stage_jump`: `0`
- `system_jump_used_by_food_submit_stage`: `0`
- `item_has_ap_recovery`: `18`
- `ap_recovery_config_for_item`: `18`
- `valuable_depot_allows_item_type`: `42`
- `item_type_allowed_by_valuable_depot`: `42`
- `collection_entry_item`: `4`
- `item_used_by_collection_entry`: `4`
- `collection_entry_bandwidth_item`: `1`
- `item_used_as_collection_bandwidth`: `1`
- `collection_entry_merges_to`: `19`
- `collection_entry_merged_from`: `19`
- `recycle_bin_domain`: `16`
- `domain_has_recycle_bin`: `16`
- `recycle_bin_level`: `16`
- `level_has_recycle_bin_config`: `16`
- `recycle_bin_has_level`: `64`
- `recycle_bin_level_in_bin`: `64`
- `recycle_bin_level_reward`: `64`
- `reward_used_by_recycle_bin_level`: `64`
- `level_has_recycle_bin`: `16`
- `recycle_bin_listed_for_level`: `16`

Sample evidence:

- `item:item_003_chips_1 -> activity_submit_item:submit_003_chips` as
  `item_required_by_submit_item`, source `SubmitItem`, evidence
  `paramData[0].paramList[0].valueStringList[0]`
- `item:item_liquid_acid -> full_bottle_item:item_fbottle_copper_acid` as
  `item_liquid_used_by_full_bottle`, source `FullBottleTable`, evidence
  `liquidId`
- `collection_entry:int_blackbox_entry -> collection_entry:int_blackbox_entry_hard`
  as `collection_entry_merged_from`, source `CollectionTable`, evidence
  `mergeId`
- `reward:reward_recycle_1 -> recycle_bin_level:recycle_bin_1_001_1:1` as
  `reward_used_by_recycle_bin_level`, source `RecycleBinTable`, evidence
  `levelData.1.rewardId`

## Notes

This closes the item-submission inbound lookup gap for required items,
bottle/liquid transforms, collection merge targets, AP recovery configs,
valuable depot item types, and recycle-bin level rewards. Queries can now start
from item, reward, level, domain, activity, activity-stage, item-type, or
collection nodes and traverse back to the exact item-submission declarations
that reference them.
