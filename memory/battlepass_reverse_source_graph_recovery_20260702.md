# BattlePass Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for BattlePass seasons, level groups,
level rewards, task groups, task conditions, task jumps, reward previews,
banners, labels, tracks, and WeekRaid battle-pass mirror nodes.

New reverse edge families include:

- `reward_used_by_battlepass_level_free`
- `reward_used_by_battlepass_level_originium`
- `reward_used_by_battlepass_level_pay`
- `reward_used_by_battlepass_season_originium_hint`
- `reward_used_by_battlepass_season_pay_hint`
- `system_jump_used_by_battlepass_task`
- `battlepass_preview_entry_in_group`
- `item_used_by_battlepass_preview`
- `battlepass_banner_entry_in_banner`
- `battlepass_track_used_by_banner_entry`
- `item_used_by_battlepass_banner_entry`
- `battlepass_level_group_used_by_season`
- `battlepass_override_level_group_used_by_season`
- `battlepass_banner_used_by_season`
- `battlepass_preview_group_used_by_season`
- `item_used_as_battlepass_weapon_box`
- `ui_label_used_by_battlepass_task_group`
- `battlepass_task_in_group`
- `battlepass_condition_used_by_task`
- `battlepass_forecast_tip_used_by_task`
- `battlepass_level_in_group`
- `battlepass_track_has_type`
- `battlepass_label_has_parent`
- `dungeon_used_by_weekraid_battlepass_node`
- `reward_used_by_weekraid_battlepass_node`
- `item_used_by_weekraid_battlepass_node`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\battlepass_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,010` nodes
- `3,182,797` edges
- `2,277,554` aliases

Compile and diff checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Both passed.

Populated parity checks:

- `battlepass_level_free_reward`: `160`
- `reward_used_by_battlepass_level_free`: `160`
- `battlepass_level_originium_reward`: `162`
- `reward_used_by_battlepass_level_originium`: `162`
- `battlepass_level_pay_reward`: `162`
- `reward_used_by_battlepass_level_pay`: `162`
- `battlepass_season_originium_hint_reward`: `4`
- `reward_used_by_battlepass_season_originium_hint`: `4`
- `battlepass_season_pay_hint_reward`: `4`
- `reward_used_by_battlepass_season_pay_hint`: `4`
- `battlepass_task_jump`: `167`
- `system_jump_used_by_battlepass_task`: `167`
- `battlepass_preview_group_has_entry`: `44`
- `battlepass_preview_entry_in_group`: `44`
- `battlepass_preview_item`: `44`
- `item_used_by_battlepass_preview`: `44`
- `battlepass_banner_has_entry`: `16`
- `battlepass_banner_entry_in_banner`: `16`
- `battlepass_banner_entry_track`: `16`
- `battlepass_track_used_by_banner_entry`: `16`
- `battlepass_banner_entry_item`: `8`
- `item_used_by_battlepass_banner_entry`: `8`
- `battlepass_season_level_group`: `4`
- `battlepass_level_group_used_by_season`: `4`
- `battlepass_season_override_level_group`: `4`
- `battlepass_override_level_group_used_by_season`: `4`
- `battlepass_season_banner`: `4`
- `battlepass_banner_used_by_season`: `4`
- `battlepass_season_originium_preview`: `4`
- `battlepass_season_pay_preview`: `4`
- `battlepass_preview_group_used_by_season`: `8`
- `battlepass_season_weapon_box`: `4`
- `item_used_as_battlepass_weapon_box`: `4`
- `battlepass_task_group_label`: `45`
- `ui_label_used_by_battlepass_task_group`: `45`
- `battlepass_group_has_task`: `306`
- `battlepass_task_in_group`: `306`
- `battlepass_task_has_condition`: `322`
- `battlepass_condition_used_by_task`: `322`
- `battlepass_task_forecast_tip`: `23`
- `battlepass_forecast_tip_used_by_task`: `23`
- `battlepass_group_has_level`: `162`
- `battlepass_level_in_group`: `162`
- `battlepass_track_type_resolves`: `3`
- `battlepass_track_has_type`: `3`
- `battlepass_label_has_sublabel`: `46`
- `battlepass_label_has_parent`: `46`
- `weekraid_battlepass_game`: `20`
- `dungeon_used_by_weekraid_battlepass_node`: `20`
- `weekraid_battlepass_reward`: `20`
- `reward_used_by_weekraid_battlepass_node`: `20`
- `weekraid_battlepass_reward_item`: `20`
- `item_used_by_weekraid_battlepass_node`: `20`

Sample evidence:

- `reward:reward_bp_01_free_01` ->
  `battlepass_level:bp_lv_group_default:1` as
  `reward_used_by_battlepass_level_free`, source `BattlePassLevelTable`,
  evidence `freeRewardId`.
- `system_jump:jump_battle_train` ->
  `battlepass_task:bp_01_task_once_12` as
  `system_jump_used_by_battlepass_task`, source `BattlePassTaskTable`,
  evidence `jumpId`.
- `battlepass_task:bp_01_task_activity_1` ->
  `battlepass_task_group:bp_01_taskgroup_activity_1` as
  `battlepass_task_in_group`, source `BattlePassTaskTable`, evidence
  `groupId`.
- `battlepass_condition:bp_02_condition_activity_1_1` ->
  `battlepass_task:bp_02_task_activity_1_1` as
  `battlepass_condition_used_by_task`, source `BattlePassTaskTable`, evidence
  `conditionIds[0]`.
- `item:business_card_topic_bp_1_0` ->
  `battlepass_reward_preview:preset_purchase_1_pay:3` as
  `item_used_by_battlepass_preview`, source `BattlePassRewardPreviewTable`,
  evidence `itemId`.
- `dungeon:dung01_wrdg001` -> `weekraid_battlepass_node:1` as
  `dungeon_used_by_weekraid_battlepass_node`, source
  `WeekRaidBattlePassTable`, evidence `gameId`.

## Notes

BattlePass queries can now start from rewards, items, SystemJump ids,
conditions, labels, levels, tracks, preview groups, banners, dungeons, or
WeekRaid battle-pass mirror nodes and traverse back to the BattlePass records
that reference them.
