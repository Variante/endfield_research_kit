# Item Submission Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for item submission, bottle, food-submit,
AP recovery, depot, collection, and recycle-bin metadata.

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
python tools\endfield_source_graph.py build --db tmp\item_submission_reverse_source_graph_2.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,010` nodes
- `3,178,345` edges
- `2,277,554` aliases

Populated parity checks:

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

Empty in this dataset:

- `food_submit_stage_jump` / `system_jump_used_by_food_submit_stage`

## Notes

These edges make item-submission and depot-like metadata queryable from the
items, rewards, activities, levels, domains, item types, and collection entries
that participate in them, rather than requiring manual inbound scans.
