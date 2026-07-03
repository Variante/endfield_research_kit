# Activity SystemJump Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for Activity, SystemJump, Adventure Book,
and activity-catalog relationships.

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
- `activity_targeted_by_system_jump`
- `dungeon_targeted_by_system_jump`
- `reward_targeted_by_system_jump`
- `item_targeted_by_system_jump`
- `mission_targeted_by_system_jump`
- `shop_targeted_by_system_jump`
- `activity_task_in_activity`
- `activity_milestone_in_activity`
- `activity_stage_in_activity`
- `mission_used_by_activity_stage`
- `dungeon_used_by_activity_catalog_game`
- `activity_catalog_game_in_entrance_series`
- `activity_catalog_game_in_high_difficulty_series`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\activity_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,010` nodes
- `3,181,019` edges
- `2,277,554` aliases

Compile and diff checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Both passed.

Populated parity checks:

- `activity_has_stage`: `350`
- `activity_stage_in_activity`: `350`
- `stage_rewards`: `332`
- `reward_used_by_activity_stage`: `332`
- `stage_jumps_to`: `121`
- `system_jump_used_by_activity_stage`: `121`
- `stage_uses_mission`: `50`
- `mission_used_by_activity_stage`: `50`
- `activity_has_task`: `276`
- `activity_task_in_activity`: `276`
- `task_rewards`: `16`
- `reward_used_by_activity_task`: `16`
- `task_jumps_to`: `43`
- `system_jump_used_by_activity_task`: `43`
- `activity_has_milestone`: `5`
- `activity_milestone_in_activity`: `5`
- `activity_milestone_rewards`: `5`
- `reward_used_by_activity_milestone`: `5`
- `activity_jumps_to`: `42`
- `system_jump_used_by_activity`: `42`
- `system_jump_targets_activity`: `66`
- `activity_targeted_by_system_jump`: `66`
- `system_jump_targets_dungeon`: `24`
- `dungeon_targeted_by_system_jump`: `24`
- `system_jump_targets_reward`: `5`
- `reward_targeted_by_system_jump`: `5`
- `system_jump_targets_item`: `56`
- `item_targeted_by_system_jump`: `56`
- `adventure_book_task_reward`: `85`
- `reward_used_by_adventure_book_task`: `85`
- `adventure_book_task_jump`: `70`
- `system_jump_used_by_adventure_book_task`: `70`
- `adventure_book_task_stage`: `157`
- `adventure_book_stage_has_task`: `157`
- `adventure_book_stage_reward`: `12`
- `reward_used_by_adventure_book_stage`: `12`
- `activity_catalog_game_dungeon_ref`: `45`
- `dungeon_used_by_activity_catalog_game`: `45`
- `activity_game_entrance_series_has_game`: `15`
- `activity_catalog_game_in_entrance_series`: `15`
- `high_difficulty_series_has_game`: `30`
- `activity_catalog_game_in_high_difficulty_series`: `30`
- `activity_benefit_jump`: `8`
- `system_jump_used_by_activity_benefit`: `8`
- `activity_web_entry_jump`: `3`
- `system_jump_used_by_activity_web_entry`: `3`
- `activity_web_stage_reward`: `2`
- `reward_used_by_activity_web_stage`: `2`

Sample evidence:

- `reward:reward_activity_gacha_beginner_1` ->
  `activity_stage:1` as `reward_used_by_activity_stage`, source
  `ActivityLevelRewardsTable`, evidence `rewardId`.
- `system_jump:jump_activity_cleaning_stage_6` ->
  `activity_stage:cleaning_test_6` as
  `system_jump_used_by_activity_stage`, source
  `ActivityConditionalMultiStageTable`, evidence `jumpId`.
- `mission:a1m10` -> `activity_stage:activity_phototaking_universe_stage_1`
  as `mission_used_by_activity_stage`, source
  `ActivityConditionalMultiStageTable`, evidence `missionId`.
- `activity:CharacterGuide_aglina` ->
  `system_jump:jump_center_activity_char_guide_2` as
  `activity_targeted_by_system_jump`, source `SystemJumpTable`, evidence
  `phaseArgs.activityId`.
- `dungeon:dung01_puzzle01` -> `activity_catalog_game:dung01_puzzle01`
  as `dungeon_used_by_activity_catalog_game`, source
  `ActivityGameEntranceGameTable`, evidence `gameList[0]`.
- `reward:reward_adventure_book_10_1` ->
  `adventure_book_task:ab_10_01` as
  `reward_used_by_adventure_book_task`, source `AdventureTaskTable`, evidence
  `rewardId`.

## Notes

This closes the broad activity-navigation inbound lookup gap. Queries can now
start from rewards, SystemJump ids, missions, dungeons, items, activities,
stages, tasks, and catalog games and traverse back to the activity records that
reference them.
