# Activity Jump Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for activity rewards, system jumps,
system-jump targets, activity tasks, milestones, stages, activity catalog games,
and adventure-book stage/task links.

New reverse edge families include:

- `system_jump_used_by_activity`
- `system_jump_used_by_activity_condition`
- `system_jump_used_by_activity_stage`
- `system_jump_used_by_activity_task`
- `system_jump_used_by_activity_banner`
- `system_jump_used_by_adventure_book_task`
- `system_jump_used_by_activity_benefit`
- `system_jump_used_by_activity_limited_formula_stage`
- `system_jump_used_by_activity_web_entry`
- `system_jump_used_by_activity_web_stage`
- `reward_used_by_activity`
- `reward_used_by_activity_milestone`
- `reward_used_by_activity_stage`
- `reward_used_by_activity_task`
- `reward_used_by_adventure_book_task`
- `reward_used_by_adventure_book_stage`
- `reward_used_by_activity_web_stage`
- target-node reverse edges such as `item_targeted_by_system_jump`,
  `shop_group_targeted_by_system_jump`, and `prts_entry_targeted_by_system_jump`
- `activity_task_in_activity`
- `activity_milestone_in_activity`
- `activity_stage_in_activity`
- `mission_used_by_activity_stage`
- `activity_catalog_game_in_entrance_series`
- `activity_catalog_game_in_high_difficulty_series`
- `dungeon_used_by_activity_catalog_game`
- `adventure_book_stage_has_task`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\activity_jump_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,010` nodes
- `3,181,019` edges
- `2,277,554` aliases

Selected parity checks:

- `activity_jumps_to`: `42`; `system_jump_used_by_activity`: `42`
- `activity_condition_jumps_to`: `33`; `system_jump_used_by_activity_condition`: `33`
- `stage_jumps_to`: `121`; `system_jump_used_by_activity_stage`: `121`
- `task_jumps_to`: `43`; `system_jump_used_by_activity_task`: `43`
- `banner_jumps_to`: `18`; `system_jump_used_by_activity_banner`: `18`
- `adventure_book_task_jump`: `70`; `system_jump_used_by_adventure_book_task`: `70`
- `activity_benefit_jump`: `8`; `system_jump_used_by_activity_benefit`: `8`
- `activity_limited_formula_stage_complete_jump`: `3`
- `activity_limited_formula_stage_incomplete_jump`: `3`
- `system_jump_used_by_activity_limited_formula_stage`: `6`
- `activity_rewards`: `40`; `reward_used_by_activity`: `40`
- `stage_rewards`: `332`; `reward_used_by_activity_stage`: `332`
- `task_rewards`: `16`; `reward_used_by_activity_task`: `16`
- `activity_has_task`: `276`; `activity_task_in_activity`: `276`
- `activity_has_stage`: `350`; `activity_stage_in_activity`: `350`
- `stage_uses_mission`: `50`; `mission_used_by_activity_stage`: `50`
- `activity_game_entrance_series_has_game`: `15`; `activity_catalog_game_in_entrance_series`: `15`
- `high_difficulty_series_has_game`: `30`; `activity_catalog_game_in_high_difficulty_series`: `30`
- `activity_catalog_game_dungeon_ref`: `45`; `dungeon_used_by_activity_catalog_game`: `45`
- `adventure_book_task_stage`: `157`; `adventure_book_stage_has_task`: `157`

System-jump target reverse checks:

- `system_jump_targets_activity`: `66`; `activity_targeted_by_system_jump`: `66`
- `system_jump_targets_snapshot_activity`: `20`; `snapshot_activity_targeted_by_system_jump`: `20`
- `system_jump_targets_factory_tech`: `13`; `factory_tech_targeted_by_system_jump`: `13`
- `system_jump_targets_manual_craft_unlock`: `50`; `item_targeted_by_manual_craft_system_jump`: `50`
- `system_jump_targets_item`: `56`; `item_targeted_by_system_jump`: `56`
- `system_jump_targets_dungeon`: `24`; `dungeon_targeted_by_system_jump`: `24`
- `system_jump_targets_shop`: `30`; `shop_targeted_by_system_jump`: `30`
- `system_jump_targets_shop_group`: `44`; `shop_group_targeted_by_system_jump`: `44`
- `system_jump_targets_prts_entry`: `25`; `prts_entry_targeted_by_system_jump`: `25`
- `system_jump_targets_prts_investigation`: `5`; `prts_investigation_targeted_by_system_jump`: `5`

## Notes

This improves activity and navigation semantics: queries can now start from a
reward, system jump, jump target, mission, dungeon, activity task/stage, or
adventure-book stage and traverse back to the activity catalog declaration that
uses it.
