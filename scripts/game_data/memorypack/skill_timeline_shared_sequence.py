"""Authenticated exact SkillData timeline records using current action readers.

This is deliberately narrower than the general BuffData action reader. It
admits only reached routes in its reviewed composite contract, including
timeline actions and passive action maps. Every absent child route still fails
closed at its first byte.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.buff_actions import (
    IF_ELSE_ACTION_MEMBER_COUNT,
    IF_ELSE_ACTION_READ_KINDS,
    IF_ELSE_ACTION_TAG,
    SEQUENCE_RECURSION_LIMIT,
    Reader,
)
from scripts.game_data.memorypack.skill_allow_next_skill import (
    decode_allow_next_skill_action,
    validate_current_native_contract as validate_allow_next_skill_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_add_camera_control_state import (
    decode_add_camera_control_state_action,
    validate_current_native_contract as validate_add_camera_control_state_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_fixed_four import (
    decode_fixed_four_action,
    validate_current_native_contract as validate_fixed_four_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_save_two_direction_angle import (
    decode_save_two_direction_angle_action,
    validate_current_native_contract as validate_save_two_direction_angle_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_push_back import (
    decode_push_back_action,
    validate_current_native_contract as validate_push_back_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_add_dynamic_navmesh_obstacle import (
    decode_add_dynamic_navmesh_obstacle_action,
    validate_current_native_contract as validate_add_dynamic_navmesh_obstacle_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_tick_interval import (
    decode_tick_interval_action,
    validate_current_native_contract as validate_tick_interval_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_camera_rotate import (
    decode_camera_rotate_action,
    validate_current_native_contract as validate_camera_rotate_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_gain_breaking_attack_atb import (
    decode_gain_breaking_attack_atb_action,
    validate_current_native_contract as validate_gain_breaking_attack_atb_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_override_camera_follow import (
    decode_override_camera_follow_action,
    validate_current_native_contract as validate_override_camera_follow_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_curve_evaluate_float import (
    decode_curve_evaluate_float_action,
    validate_current_native_contract as validate_curve_evaluate_float_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_command_to_characters import (
    decode_command_to_characters_action,
    validate_current_native_contract as validate_command_to_characters_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_receive_move_input import (
    decode_receive_move_input_action,
    validate_current_native_contract as validate_receive_move_input_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_combo_skill_camera_alpha import (
    decode_check_combo_skill_camera_alpha_action,
    validate_current_native_contract as validate_check_combo_skill_camera_alpha_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_temporary_unlock import (
    decode_temporary_unlock_action,
    validate_current_native_contract as validate_temporary_unlock_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_has_move_input import (
    decode_check_has_move_input_action,
    validate_current_native_contract as validate_check_has_move_input_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_togglable import (
    decode_togglable_action,
    validate_current_native_contract as validate_togglable_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_squad_in_fight import (
    decode_check_squad_in_fight_action,
    validate_current_native_contract as validate_check_squad_in_fight_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_break_interactive import (
    decode_break_interactive_action,
    validate_current_native_contract as validate_break_interactive_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_inherit_buff import (
    decode_inherit_buff_action,
    validate_current_native_contract as validate_inherit_buff_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_animated_camera import (
    decode_animated_camera_action,
    validate_current_native_contract as validate_animated_camera_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_hide_ui import (
    decode_hide_ui_action,
    validate_current_native_contract as validate_hide_ui_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_move_to_location import (
    decode_move_to_location_action,
    validate_current_native_contract as validate_move_to_location_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_ultimate_time import (
    decode_ultimate_time_action,
    validate_current_native_contract as validate_ultimate_time_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_ultimate_show import (
    decode_ultimate_show_action,
    validate_current_native_contract as validate_ultimate_show_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_channeling_casting import (
    decode_channeling_casting_action,
    validate_current_native_contract as validate_channeling_casting_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_modify_weapon_mount_point import (
    decode_modify_weapon_mount_point_action,
    validate_current_native_contract as validate_modify_weapon_mount_point_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_raycast_effect import (
    decode_raycast_effect_action,
    validate_current_native_contract as validate_raycast_effect_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_pick_target import (
    decode_pick_target_action,
    validate_current_native_contract as validate_pick_target_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_do_once import (
    decode_do_once_action,
    validate_current_native_contract as validate_do_once_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_skill_camera_motion_free import (
    decode_check_skill_camera_motion_free_action,
    validate_current_native_contract as validate_check_skill_camera_motion_free_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_target_angle import (
    decode_check_target_angle_action,
    validate_current_native_contract as validate_check_target_angle_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_move_to_target import (
    decode_move_to_target_action,
    validate_current_native_contract as validate_move_to_target_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_jump_to_target import (
    decode_jump_to_target_action,
    validate_current_native_contract as validate_jump_to_target_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_elite_back_swing_be_hit import (
    decode_elite_back_swing_be_hit_action,
    validate_current_native_contract as validate_elite_back_swing_be_hit_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_get_target_buff_bb_advanced import (
    decode_get_target_buff_bb_advanced_action,
    validate_current_native_contract as validate_get_target_buff_bb_advanced_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_target_contains import (
    decode_check_target_contains_action,
    validate_current_native_contract as validate_check_target_contains_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_physics_cast import (
    decode_physics_cast_action,
    validate_current_native_contract as validate_physics_cast_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_launch_upward import (
    decode_launch_upward_action,
    validate_current_native_contract as validate_launch_upward_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_change_skill import (
    decode_change_skill_action,
    validate_current_native_contract as validate_change_skill_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_buff_id_context_advanced import (
    decode_check_buff_id_context_advanced_action,
    validate_current_native_contract as validate_check_buff_id_context_advanced_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_combo_action import (
    decode_combo_action,
    validate_current_native_contract as validate_combo_action_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_store_cur_skill_execute_frame import (
    decode_store_cur_skill_execute_frame_action,
    validate_current_native_contract as validate_store_cur_skill_execute_frame_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_skill_ai_move import (
    decode_skill_ai_move_action,
    validate_current_native_contract as validate_skill_ai_move_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_bone_attach import (
    decode_bone_attach_action,
    validate_current_native_contract as validate_bone_attach_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_ignore_model_interval_check import (
    decode_ignore_model_interval_check_action,
    validate_current_native_contract as validate_ignore_model_interval_check_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_knock_down import (
    decode_knock_down_action,
    validate_current_native_contract as validate_knock_down_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_target_postprocessor import (
    decode_target_postprocessor_action,
    validate_current_native_contract as validate_target_postprocessor_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_remove_ai_marker import (
    decode_remove_ai_marker_action,
    validate_current_native_contract as validate_remove_ai_marker_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_typhoea_archery_chip import (
    decode_typhoea_archery_chip_action,
    validate_current_native_contract as validate_typhoea_archery_chip_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_tick_interval_v2 import (
    decode_tick_interval_v2_action,
    validate_current_native_contract as validate_tick_interval_v2_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_origin_skill_type import (
    decode_check_origin_skill_type_action,
    validate_current_native_contract as validate_check_origin_skill_type_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_save_move_axis_angle import (
    decode_save_move_axis_angle_action,
    validate_current_native_contract as validate_save_move_axis_angle_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_move_to_direction import (
    decode_move_to_direction_action,
    validate_current_native_contract as validate_move_to_direction_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_crush import (
    READ_ORDER as CRUSH_READ_ORDER,
    decode_crush_action,
    validate_current_native_contract as validate_crush_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_spell_infliction_type import (
    decode_check_spell_infliction_type_action,
    validate_current_native_contract as validate_check_spell_infliction_type_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_heal_tag import (
    decode_check_heal_tag_action,
    validate_current_native_contract as validate_check_heal_tag_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_consume_buff_layer import (
    decode_check_consume_buff_layer_action,
    validate_current_native_contract as validate_check_consume_buff_layer_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_obtain_atb_type import (
    decode_check_obtain_atb_type_action,
    validate_current_native_contract as validate_check_obtain_atb_type_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_global_cd_timer import (
    decode_check_global_cd_timer_action,
    validate_current_native_contract as validate_check_global_cd_timer_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_add_global_cd_timer import (
    decode_add_global_cd_timer_action,
    validate_current_native_contract as validate_add_global_cd_timer_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_play_animation_step import (
    decode_play_animation_step_action,
    validate_current_native_contract as validate_play_animation_step_shared_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_blow_off_enemy import (
    READ_ORDER as BLOW_OFF_ENEMY_READ_ORDER,
    decode_blow_off_enemy_action,
    validate_current_native_contract as validate_blow_off_enemy_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_physical_infliction_type import (
    decode_check_physical_infliction_type_action,
    validate_current_native_contract as validate_check_physical_infliction_type_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_create_buff_attaching_skill import (
    decode_create_buff_attaching_skill_action,
    validate_current_native_contract as validate_create_buff_attaching_skill_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_inherit_ccs import (
    decode_inherit_ccs_action,
    validate_current_native_contract as validate_inherit_ccs_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_channeling_damage import (
    decode_channeling_damage_action,
    validate_current_native_contract as validate_channeling_damage_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_hit_collider_options import (
    decode_check_hit_collider_options_action,
    validate_current_native_contract as validate_check_hit_collider_options_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_compare_deck_attr import (
    decode_compare_deck_attr_action,
    validate_current_native_contract as validate_compare_deck_attr_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_check_buff_stack_num_by_tag import (
    decode_check_buff_stack_num_by_tag_action,
    validate_current_native_contract as validate_check_buff_stack_num_by_tag_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_force_spell_status import (
    decode_force_spell_status_action,
    validate_current_native_contract as validate_force_spell_status_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_modify_camera_lock_point import (
    decode_modify_camera_lock_point_action,
    validate_current_native_contract as validate_modify_camera_lock_point_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_apply_armor import (
    decode_apply_armor_action,
    validate_current_native_contract as validate_apply_armor_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_blight_miasma_tolerance_zero import (
    decode_blight_miasma_tolerance_zero_action,
    validate_current_native_contract as validate_blight_miasma_tolerance_zero_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_block_move_interrupt_skill import (
    decode_block_move_interrupt_skill_action,
    validate_current_native_contract as validate_block_move_interrupt_skill_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_channeling_v2 import (
    decode_channeling_v2_action,
    validate_current_native_contract as validate_channeling_v2_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_char_follow_action import (
    decode_char_follow_action,
    validate_current_native_contract as validate_char_follow_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_finish_buff_by_tag import (
    decode_finish_buff_by_tag_action,
    validate_current_native_contract as validate_finish_buff_by_tag_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_extend_buff import (
    decode_extend_buff_action,
    validate_current_native_contract as validate_extend_buff_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_get_patrol_teleport_pos import (
    decode_get_patrol_teleport_pos_action,
    validate_current_native_contract as validate_get_patrol_teleport_pos_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_override_born_position import (
    decode_override_born_position_action,
    validate_current_native_contract as validate_override_born_position_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_refresh_head_bar_show_hide import (
    decode_refresh_head_bar_show_hide_action,
    validate_current_native_contract as validate_refresh_head_bar_show_hide_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_force_hide_head_bar import (
    decode_force_hide_head_bar_action,
    validate_current_native_contract as validate_force_hide_head_bar_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_additional_battle_shape import (
    decode_additional_battle_shape_action,
    validate_current_native_contract as validate_additional_battle_shape_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_throw_pickup_item import (
    decode_throw_pickup_item_action,
    validate_current_native_contract as validate_throw_pickup_item_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_throw_pickup_item_start import (
    decode_throw_pickup_item_start_action,
    validate_current_native_contract as validate_throw_pickup_item_start_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_take_down import (
    decode_take_down_action,
    validate_current_native_contract as validate_take_down_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_obtain_usp_normal import (
    READ_ORDER as OBTAIN_USP_NORMAL_READ_ORDER,
    decode_obtain_usp_normal_action,
    validate_current_native_contract as validate_obtain_usp_normal_native_contract,
)
from scripts.game_data.memorypack.skill_selector_finder_typhoea import (
    decode_typhoea_selected_finder,
    validate_current_native_contract as validate_typhoea_selected_finder_native_contract,
)
from scripts.game_data.memorypack.skill_selector_validator_in_screen import (
    decode_in_screen_validator,
    validate_current_native_contract as validate_in_screen_validator_native_contract,
)
from scripts.game_data.memorypack.skill_nested_interactive_key_validator import (
    decode_nested_interactive_key_validator,
    validate_current_native_contract as validate_nested_interactive_key_validator_native_contract,
)
from scripts.game_data.memorypack.skill_custom_root_motion import (
    decode_custom_root_motion_action,
    validate_current_native_contract as validate_custom_root_motion_native_contract,
)
from scripts.game_data.memorypack.skill_snap_to_target_with_range import (
    decode_snap_to_target_with_range_action,
    validate_current_native_contract as validate_snap_to_target_with_range_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_enemy_warning import (
    decode_enemy_warning_action,
    validate_current_native_contract as validate_enemy_warning_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_finish_angry import (
    decode_finish_angry_action,
    validate_current_native_contract as validate_finish_angry_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_teleport_pos_select import (
    decode_teleport_pos_select_action,
    validate_current_native_contract as validate_teleport_pos_select_native_contract,
)


CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_shared_sequence_native.json"
LABEL = "skillTimelineSharedSequence"
JUMP_TO_ACTION_TAG = 0x00D9
JUMP_TO_ACTION_MEMBER_COUNT = 6
JUMP_TO_ACTION_READ_KINDS = (
    "anonymous-nonzero-byte",
    "anonymous-scalar32",
    "anonymous-scalar32",
    "anonymous-scalar32",
    "SequenceActionData",
    "int32",
)
SET_ABILITY_ENTITY_TARGET_TAG = 0x0147
SET_ABILITY_ENTITY_TARGET_MEMBER_COUNT = 5
SET_ABILITY_ENTITY_TARGET_READ_KINDS = (
    "anonymous-nonzero-byte",
    "anonymous-scalar32",
    "anonymous-scalar32",
    "anonymous-scalar32",
    "TargetSettings",
)
PLAY_PERFECT_DODGE_ANIM_TAG = 0x0118
PLAY_PERFECT_DODGE_ANIM_MEMBER_COUNT = 6
PLAY_PERFECT_DODGE_ANIM_READ_KINDS = (
    "bool-byte",
    "enum-int32",
    "int32",
    "int32",
    "bool-byte",
    "float32-bits",
)
FIRST_DAMAGE_UNIT_COST_LIST_MEMBER_INDEX = 5
FIRST_DAMAGE_UNIT_COST_LIST_METHOD_SPEC = 610882
COST_DATA_MEMBER_COUNT = 3
COST_DATA_READ_KINDS = (
    "anonymous-raw4",
    "anonymous-scalar32",
    "anonymous-raw4",
)
BROADCAST_ALERT_MEMBER_READ_KINDS = (
    "byte", "scalar32", "scalar32", "scalar32", "skill-alert-profile",
    "scalar32", "scalar32", "byte-payload", "scalar32", "raw4",
    "target-profile",
)
SET_SUPER_ARMOR_MEMBER_READ_KINDS = (
    "byte", "scalar32", "scalar32", "scalar32",
    "scalar-flag-payload", "scalar-flag-payload", "target-profile",
)
SAVE_VALUE_FROM_AI_BLACKBOARD_READ_KINDS = (
    "byte", "scalar32", "scalar32", "scalar32", "byte-payload",
    "target-profile", "byte-payload", "byte-payload", "byte-payload",
    "byte-payload", "scalar32",
)
PASSIVE_CONDITION_ROUTES = (
    (
        "0x0056", "Beyond.Gameplay.Core.Conditions.CheckBuffIdInContext+Data",
        "buff_56_native.json", "member8",
        ("byte", "scalar32", "scalar32", "scalar32", "byte-payload",
         "counted-member1-payloads", "scalar32", "query-profile"),
    ),
    (
        "0x005B", "Beyond.Gameplay.Core.Conditions.CheckDamageDecorateMask+Data",
        "buff_5b_native.json", "member6",
        ("byte", "scalar32", "scalar32", "scalar32", "scalar32", "scalar64"),
    ),
    (
        "0x0078", "Beyond.Gameplay.Core.Conditions.CheckSkillType+Data",
        "buff_78_native.json", "member9",
        ("byte", "scalar32", "scalar32", "scalar32", "scalar32", "byte",
         "byte", "target-profile", "counted-scalar32"),
    ),
)
TIMELINE_SOURCE_ROUTES = (
    (
        "0x0157", "Beyond.Gameplay.Core.SetSkillCdAtOnce+Data",
        "buff_157_native.json", "member11",
        ("byte", "scalar32", "scalar32", "scalar32", "scalar32", "byte",
         "byte-payload", "scalar32", "target-profile", "byte", "scalar-payload"),
    ),
    (
        "0x015B", "Beyond.Gameplay.Core.SetWeaknessAction+Data",
        "buff_15b_native.json", "member11",
        ("byte", "scalar32", "scalar32", "scalar32", "scalar-payload",
         "scalar-payload", "byte", "sequence", "scalar-payload", "byte",
         "scalar-payload"),
    ),
    (
        "0x017C", "Beyond.Gameplay.Core.TeleportAction+Data",
        "buff_17c_native.json", "member14",
        ("byte", "scalar32", "scalar32", "scalar32", "sequence", "byte",
         "byte", "byte", "byte", "raw4", "scalar-payload", "byte",
         "target", "byte"),
    ),
)
FAC_BUILDING_PLAY_ANIMATION_TAG = 0x00B0
CHECK_TWO_DIRECTION_ANGLE_TAG = 0x0082
CHECK_TWO_DIRECTION_ANGLE_READ_KINDS = (
    "byte", "scalar32", "scalar32", "scalar32", "enum32", "enum32",
    "target-settings", "target-settings", "enum32", "target-settings",
    "target-settings", "blackboard-double",
)
COMBO_CACHE_READ_KINDS = (
    "byte", "scalar32", "scalar32", "scalar32",
    "counted-combo-cache-mappings",
)
ADD_AI_MARKER_READ_KINDS = (
    "byte", "scalar32", "scalar32", "scalar32",
    "scalar-payload", "scalar32", "target", "byte",
)
FAC_BUILDING_PLAY_ANIMATION_MEMBER_COUNT = 6
FAC_BUILDING_PLAY_ANIMATION_PLAN = (
    ("fixed", 1, "bool"),
    ("fixed", 4, "scalar32"),
    ("fixed", 4, "scalar32"),
    ("fixed", 4, "scalar32"),
    ("string", None, None),
    ("fixed", 1, "bool"),
)


class SharedSequenceReader(Reader):
    """Skill-only extensions to the shared finite action grammar."""

    def selector_finder_profile(self) -> None:
        if self.peek() == 0x17:
            decode_typhoea_selected_finder(self)
            return
        super().selector_finder_profile()

    def selector_validator_profile(self) -> None:
        if self.peek() == 0x07:
            decode_in_screen_validator(self)
            return
        if self.peek() == 0x08:
            decode_nested_interactive_key_validator(self)
            return
        super().selector_validator_profile()

    def damage_unit_profile(self) -> None:
        """Select the Skill-authenticated CostData list at member five.

        The shared Buff reader deliberately leaves every positive first/third
        DamageUnit list closed.  SkillData has an additional composite
        contract for member five only, so keep the selection local to this
        subclass and retain the shared fail-closed behavior for member ten and
        the EffectActionCfg array.
        """
        stack = getattr(self, "_skill_damage_unit_list_indices", None)
        if stack is None:
            stack = []
            self._skill_damage_unit_list_indices = stack
        stack.append(0)
        try:
            super().damage_unit_profile()
        finally:
            stack.pop()

    def empty_damage_collection(self, kind: str) -> int | None:
        stack = getattr(self, "_skill_damage_unit_list_indices", None)
        if kind == "damage unit list" and stack:
            list_index = stack[-1]
            stack[-1] += 1
            if list_index == 0:
                start = self.pos
                count = self.count(1, nullable=True)
                for _ in range(max(0, count)):
                    self.cost_profile()
                self.records.append({
                    "start": start,
                    "end": self.pos,
                    "kind": "skill-damage-unit-cost-data-list",
                    "count": count,
                    "damageUnitMemberIndex": FIRST_DAMAGE_UNIT_COST_LIST_MEMBER_INDEX,
                })
                return count
        return super().empty_damage_collection(kind)

    def _action(self, depth: int, tag: int, width: int) -> None:
        if tag == 0x0116:
            decode_play_animation_step_action(self, depth, tag, width)
            return
        if tag == 0x001D:
            decode_blow_off_enemy_action(self, depth, tag, width)
            return
        if tag == 0x006D:
            decode_check_physical_infliction_type_action(self, depth, tag, width)
            return
        if tag == 0x0093:
            decode_create_buff_attaching_skill_action(self, depth, tag, width)
            return
        if tag == 0x00D3:
            decode_inherit_ccs_action(self, depth, tag, width)
            return
        if tag == 0x0032:
            decode_channeling_damage_action(self, depth, tag, width)
            return
        if tag == 0x0064:
            decode_check_hit_collider_options_action(self, depth, tag, width)
            return
        if tag == 0x0085:
            decode_compare_deck_attr_action(self, depth, tag, width)
            return
        if tag == 0x0059:
            decode_check_buff_stack_num_by_tag_action(self, depth, tag, width)
            return
        if tag == 0x00BA:
            decode_force_spell_status_action(self, depth, tag, width)
            return
        if tag == 0x00EB:
            decode_modify_camera_lock_point_action(self, depth, tag, width)
            return
        if tag == 0x0013:
            decode_apply_armor_action(self, depth, tag, width)
            return
        if tag == 0x0019:
            decode_blight_miasma_tolerance_zero_action(self, depth, tag, width)
            return
        if tag == 0x001A:
            decode_block_move_interrupt_skill_action(self, depth, tag, width)
            return
        if tag == 0x0030:
            decode_channeling_v2_action(self, depth, tag, width)
            return
        if tag == 0x0034:
            decode_char_follow_action(self, depth, tag, width)
            return
        if tag == 0x00B5:
            decode_finish_buff_by_tag_action(self, depth, tag, width)
            return
        if tag == 0x00AF:
            decode_extend_buff_action(self, depth, tag, width)
            return
        if tag == 0x00C2:
            decode_get_patrol_teleport_pos_action(self, depth, tag, width)
            return
        if tag == 0x0103:
            decode_override_born_position_action(self, depth, tag, width)
            return
        if tag == 0x012C:
            decode_refresh_head_bar_show_hide_action(self, depth, tag, width)
            return
        if tag == 0x00B9:
            decode_force_hide_head_bar_action(self, depth, tag, width)
            return
        if tag == 0x0091:
            decode_additional_battle_shape_action(self, depth, tag, width)
            return
        if tag == 0x017F:
            decode_throw_pickup_item_action(self, depth, tag, width)
            return
        if tag == 0x0180:
            decode_throw_pickup_item_start_action(self, depth, tag, width)
            return
        if tag == 0x017A:
            decode_take_down_action(self, depth, tag, width)
            return
        if tag == 0x00FF and width == 3:
            decode_obtain_usp_normal_action(self, depth, tag, width)
            return
        if tag == 0x000A:
            decode_add_global_cd_timer_action(self, depth, tag, width)
            return
        if tag == 0x0044:
            decode_check_global_cd_timer_action(self, depth, tag, width)
            return
        if tag == 0x006A:
            decode_check_obtain_atb_type_action(self, depth, tag, width)
            return
        if tag == 0x003F:
            decode_check_consume_buff_layer_action(self, depth, tag, width)
            return
        if tag == 0x0063:
            decode_check_heal_tag_action(self, depth, tag, width)
            return
        if tag == 0x007A:
            decode_check_spell_infliction_type_action(self, depth, tag, width)
            return
        if tag == 0x0097:
            decode_crush_action(self, depth, tag, width)
            return
        if tag == 0x0048:
            decode_check_origin_skill_type_action(self, depth, tag, width)
            return
        if tag == 0x013D:
            decode_save_move_axis_angle_action(self, depth, tag, width)
            return
        if tag == 0x00F7:
            decode_move_to_direction_action(self, depth, tag, width)
            return
        if tag == 0x0182:
            decode_tick_interval_v2_action(self, depth, tag, width)
            return
        if tag == 0x012D:
            decode_remove_ai_marker_action(self, depth, tag, width)
            return
        if tag == 0x018E:
            decode_typhoea_archery_chip_action(self, depth, tag, width)
            return
        if tag == 0x017B:
            decode_target_postprocessor_action(self, depth, tag, width)
            return
        if tag == 0x00DD:
            decode_knock_down_action(self, depth, tag, width)
            return
        if tag == 0x00D0:
            decode_ignore_model_interval_check_action(self, depth, tag, width)
            return
        if tag == 0x0000:
            decode_bone_attach_action(self, depth, tag, width)
            return
        if tag == 0x0165:
            decode_skill_ai_move_action(self, depth, tag, width)
            return
        if tag == 0x0173:
            decode_store_cur_skill_execute_frame_action(self, depth, tag, width)
            return
        if tag == 0x004D:
            decode_combo_action(self, depth, tag, width)
            return
        if tag == 0x0057:
            decode_check_buff_id_context_advanced_action(self, depth, tag, width)
            return
        if tag == 0x002C:
            decode_change_skill_action(self, depth, tag, width)
            return
        if tag == 0x007E:
            decode_check_target_contains_action(self, depth, tag, width)
            return
        if tag == 0x0113:
            decode_physics_cast_action(self, depth, tag, width)
            return
        if tag == 0x00DF:
            decode_launch_upward_action(self, depth, tag, width)
            return
        if tag == 0x00C4:
            decode_get_target_buff_bb_advanced_action(self, depth, tag, width)
            return
        if tag == 0x00A5:
            decode_elite_back_swing_be_hit_action(self, depth, tag, width)
            return
        if tag == 0x00DA:
            decode_jump_to_target_action(self, depth, tag, width)
            return
        if tag == 0x00FB:
            decode_move_to_target_action(self, depth, tag, width)
            return
        if tag == 0x007D:
            decode_check_target_angle_action(self, depth, tag, width)
            return
        if tag == 0x0072:
            decode_check_skill_camera_motion_free_action(self, depth, tag, width)
            return
        if tag == 0x0121:
            decode_raycast_effect_action(self, depth, tag, width)
            return
        if tag == 0x0114:
            decode_pick_target_action(self, depth, tag, width)
            return
        if tag == 0x00A0:
            decode_do_once_action(self, depth, tag, width)
            return
        if tag == 0x00F3:
            decode_modify_weapon_mount_point_action(self, depth, tag, width)
            return
        if tag == 0x0031:
            decode_channeling_casting_action(self, depth, tag, width)
            return
        if tag == 0x0193:
            decode_ultimate_show_action(self, depth, tag, width)
            return
        if tag == 0x0194:
            decode_ultimate_time_action(self, depth, tag, width)
            return
        if tag == 0x00F8:
            decode_move_to_location_action(self, depth, tag, width)
            return
        if tag == 0x00C6:
            decode_hide_ui_action(self, depth, tag, width)
            return
        if tag == 0x0010:
            decode_animated_camera_action(self, depth, tag, width)
            return
        if tag == 0x00D2:
            decode_inherit_buff_action(self, depth, tag, width)
            return
        if tag == 0x0001:
            decode_break_interactive_action(self, depth, tag, width)
            return
        if tag == 0x0052:
            decode_check_squad_in_fight_action(self, depth, tag, width)
            return
        if tag == 0x0184:
            decode_togglable_action(self, depth, tag, width)
            return
        if tag == 0x0045:
            decode_check_has_move_input_action(self, depth, tag, width)
            return
        if tag == 0x003D:
            decode_check_combo_skill_camera_alpha_action(self, depth, tag, width)
            return
        if tag == 0x017E:
            decode_temporary_unlock_action(self, depth, tag, width)
            return
        if tag == 0x004F:
            decode_command_to_characters_action(self, depth, tag, width)
            return
        if tag == 0x0123:
            decode_receive_move_input_action(self, depth, tag, width)
            return
        if tag == 0x0025:
            decode_camera_rotate_action(self, depth, tag, width)
            return
        if tag == 0x00BF:
            decode_gain_breaking_attack_atb_action(self, depth, tag, width)
            return
        if tag == 0x0104:
            decode_override_camera_follow_action(self, depth, tag, width)
            return
        if tag == 0x0098:
            decode_curve_evaluate_float_action(self, depth, tag, width)
            return
        if tag == 0x0009:
            decode_add_dynamic_navmesh_obstacle_action(self, depth, tag, width)
            return
        if tag == 0x011E:
            decode_push_back_action(self, depth, tag, width)
            return
        if tag == 0x0141:
            decode_save_two_direction_angle_action(self, depth, tag, width)
            return
        if tag == 0x0181:
            decode_tick_interval_action(self, depth, tag, width)
            return
        if tag == 0x019E:
            decode_add_camera_control_state_action(self, depth, tag, width)
            return
        if tag in (0x009E, 0x00E8):
            decode_fixed_four_action(self, depth, tag, width)
            return
        if tag == 0x000E:
            decode_allow_next_skill_action(self, depth, tag, width)
            return
        if tag == 0x0168:
            decode_snap_to_target_with_range_action(self, depth, tag, width)
            return
        if tag == 0x017D:
            decode_teleport_pos_select_action(self, depth, tag, width)
            return
        if tag == CHECK_TWO_DIRECTION_ANGLE_TAG:
            if width != 1:
                raise ValueError("skillTimelineSharedSequence.checkTwoDirectionAngle:tag-width")
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(len(CHECK_TWO_DIRECTION_ANGLE_READ_KINDS))
            self.take(1, "anonymous-nonzero-byte")
            for _ in range(5):
                self.take(4, "anonymous-scalar32")
            self.target_profile()
            self.target_profile()
            self.take(4, "anonymous-enum32")
            self.target_profile()
            self.target_profile()
            self.scalar_payload()
            return
        if tag == 0x00B3:
            decode_finish_angry_action(self, depth, tag, width)
            return
        if tag == 0x00AA:
            decode_enemy_warning_action(self, depth, tag, width)
            return
        if tag == FAC_BUILDING_PLAY_ANIMATION_TAG:
            if width != 1:
                raise ValueError("skillTimelineSharedSequence.facBuildingPlayAnimation:tag-width")
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(FAC_BUILDING_PLAY_ANIMATION_MEMBER_COUNT)
            self.take(1, "anonymous-bool-byte")
            for _ in range(3):
                self.take(4, "anonymous-scalar32")
            self.byte_payload()
            self.take(1, "anonymous-bool-byte")
            return
        if tag == 0x0099:
            decode_custom_root_motion_action(self, depth, tag, width)
            return
        if tag == JUMP_TO_ACTION_TAG:
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(JUMP_TO_ACTION_MEMBER_COUNT)
            self.take(1, "anonymous-nonzero-byte")
            for _ in range(3):
                self.take(4, "anonymous-scalar32")
            self.sequence(depth)
            self.take(4, "anonymous-scalar32")
            return
        if tag == SET_ABILITY_ENTITY_TARGET_TAG:
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(SET_ABILITY_ENTITY_TARGET_MEMBER_COUNT)
            self.take(1, "anonymous-nonzero-byte")
            for _ in range(3):
                self.take(4, "anonymous-scalar32")
            self.target_profile()
            return
        if tag == PLAY_PERFECT_DODGE_ANIM_TAG:
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(PLAY_PERFECT_DODGE_ANIM_MEMBER_COUNT)
            self.take(1, PLAY_PERFECT_DODGE_ANIM_READ_KINDS[0])
            for kind in PLAY_PERFECT_DODGE_ANIM_READ_KINDS[1:4]:
                self.take(4, kind)
            self.take(1, PLAY_PERFECT_DODGE_ANIM_READ_KINDS[4])
            self.take(4, PLAY_PERFECT_DODGE_ANIM_READ_KINDS[5])
            return
        super()._action(depth, tag, width)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    raw = CONTRACT_PATH.read_bytes()
    value = json.loads(raw)
    if value.get("schema") != "endfield.skill-timeline-shared-sequence-native-contract.v2":
        raise ValueError("skillTimelineSharedSequence.contract:unsupported-schema")
    dependency_values: dict[str, dict[str, Any]] = {}
    for dependency in value.get("dependencies", []):
        path = CONTRACT_PATH.parent / dependency["path"]
        if path.suffix == ".json":
            dependency_values[dependency["path"]] = json.loads(path.read_bytes())
    routes = value.get("allowedReachedRoutes")
    if not isinstance(routes, list):
        raise ValueError("skillTimelineSharedSequence.contract:routes")
    for route in routes:
        provider_ref = route.get("providerRef")
        if provider_ref is None:
            continue
        provider = value.get(provider_ref)
        if not isinstance(provider, dict):
            raise ValueError(
                f"skillTimelineSharedSequence.contract:provider-missing:{provider_ref}"
            )
        if (
            provider.get("physicalTag") != route.get("tag")
            or provider.get("serializedMemberCount") != route.get("memberCount")
            or provider.get("status")
            != "authenticated-static-provider-chain-with-exact-corpus-cursor"
        ):
            raise ValueError(
                f"skillTimelineSharedSequence.contract:provider-route-drift:{provider_ref}"
            )
        reads = provider.get("orderedSourceReads")
        read_kinds = tuple(row.get("kind") for row in reads) if isinstance(reads, list) else ()
        provider_kind = provider.get("providerKind")
        expected = {
            None: (IF_ELSE_ACTION_TAG, IF_ELSE_ACTION_MEMBER_COUNT, IF_ELSE_ACTION_READ_KINDS),
            "nested-sequence-action": (
                JUMP_TO_ACTION_TAG,
                JUMP_TO_ACTION_MEMBER_COUNT,
                JUMP_TO_ACTION_READ_KINDS,
            ),
            "target-settings-action": (
                SET_ABILITY_ENTITY_TARGET_TAG,
                SET_ABILITY_ENTITY_TARGET_MEMBER_COUNT,
                SET_ABILITY_ENTITY_TARGET_READ_KINDS,
            ),
            "simple-action": (
                PLAY_PERFECT_DODGE_ANIM_TAG,
                PLAY_PERFECT_DODGE_ANIM_MEMBER_COUNT,
                PLAY_PERFECT_DODGE_ANIM_READ_KINDS,
            ),
        }.get(provider_kind)
        if (
            expected is None
            or int(route["tag"], 16) != expected[0]
            or route["memberCount"] != expected[1]
            or [row.get("memberIndex") for row in reads or []]
            != list(range(route["memberCount"]))
            or read_kinds != expected[2]
            or (provider_kind is None and provider.get("recursionLimit") != SEQUENCE_RECURSION_LIMIT)
        ):
            raise ValueError(
                f"skillTimelineSharedSequence.contract:provider-read-order:{provider_ref}"
            )
        method_spec = provider.get("nestedMethodSpec")
        expected_type = {
            None: "Beyond.Gameplay.Core.SequenceActionData",
            "nested-sequence-action": "Beyond.Gameplay.Core.SequenceActionData",
            "target-settings-action": "Beyond.Gameplay.Core.TargetSettings",
            "simple-action": None,
        }[provider_kind]
        if expected_type is not None and (
            not isinstance(method_spec, dict)
            or method_spec.get("typeName") != expected_type
        ):
            raise ValueError(
                f"skillTimelineSharedSequence.contract:provider-type:{provider_ref}"
            )
        if expected_type is None and method_spec is not None:
            raise ValueError(
                f"skillTimelineSharedSequence.contract:unexpected-provider-type:{provider_ref}"
            )
    cost_provider = value.get("positiveFirstDamageUnitCostListProvider")
    if not isinstance(cost_provider, dict):
        raise ValueError("skillTimelineSharedSequence.contract:cost-list-provider")
    element_reads = cost_provider.get("orderedElementReads")
    if (
        cost_provider.get("status")
        != "authenticated-static-provider-chain-with-exact-corpus-cursor"
        or cost_provider.get("damageUnitMemberIndex")
        != FIRST_DAMAGE_UNIT_COST_LIST_MEMBER_INDEX
        or cost_provider.get("listMethodSpecIndex")
        != FIRST_DAMAGE_UNIT_COST_LIST_METHOD_SPEC
        or cost_provider.get("elementTypeName")
        != "Beyond.Gameplay.Core.CastData+CostData"
        or cost_provider.get("elementTypeDefinition") != 9061
        or cost_provider.get("elementMemberCount") != COST_DATA_MEMBER_COUNT
        or [row.get("memberIndex") for row in element_reads or []]
        != list(range(COST_DATA_MEMBER_COUNT))
        or tuple(row.get("kind") for row in element_reads or [])
        != COST_DATA_READ_KINDS
    ):
        raise ValueError("skillTimelineSharedSequence.contract:cost-list-provider-drift")
    damage_contract = dependency_values.get("buff_9a_native.json", {})
    damage_context = next(
        (
            row
            for row in damage_contract.get("nestedContexts", [])
            if row.get("instructionRva") == cost_provider.get("listCallsiteRva")
        ),
        None,
    )
    cost_contract = dependency_values.get("buff_c0_native.json", {})
    cost_methods = cost_contract.get("methods", [])
    if (
        not isinstance(damage_context, dict)
        or damage_context.get("methodSpecIndex") != FIRST_DAMAGE_UNIT_COST_LIST_METHOD_SPEC
        or damage_context.get("typeName") != "System.Collections.Generic.List`1"
        or damage_context.get("generic", {}).get("elementInstantiationIndex") != 17015
        or damage_context.get("generic", {}).get("elementArguments")
        != [cost_provider.get("elementArgumentRawHex")]
        or cost_contract.get("anonymousReadOrder", {}).get("costMember3")
        != ["raw4", "scalar32", "raw4"]
        or not any(
            row[1]
            == "Beyond.MemoryPack.Beyond_Gameplay_Core_CastData_CostDataForMemoryPack"
            and row[2] == "Deserialize"
            for row in cost_methods
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:cost-list-source-drift")
    alert_route = next(
        (row for row in routes if row.get("tag") == "0x0023"), None
    )
    alert_ref = alert_route.get("sourceContract") if isinstance(alert_route, dict) else None
    alert_contract = dependency_values.get("buff_23_native.json", {})
    if (
        not isinstance(alert_route, dict)
        or alert_route.get("typeName") != "BroadcastAlertToCharactersAction"
        or alert_route.get("memberCount") != len(BROADCAST_ALERT_MEMBER_READ_KINDS)
        or alert_ref != {
            "path": "buff_23_native.json",
            "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member11",
        }
        or alert_contract.get("schemaVersion") != 1
        or tuple(alert_contract.get("anonymousReadOrder", {}).get("member11", ()))
        != BROADCAST_ALERT_MEMBER_READ_KINDS
        or not any(
            row[2] == "Deserialize"
            and "BroadcastAlertToCharactersActionDataForMemoryPack" in row[1]
            for row in alert_contract.get("methods", [])
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:alert-route-source-drift")
    motion_route = next((row for row in routes if row.get("tag") == "0x0099"), None)
    motion_contract = dependency_values.get("skill_custom_root_motion_native.json", {})
    motion_reads = motion_contract.get("orderedSourceReads")
    if (
        not isinstance(motion_route, dict)
        or motion_route.get("typeName") != "Beyond.Gameplay.Core.CustomRootMotionAction+Data"
        or motion_route.get("memberCount") != 24
        or motion_route.get("sourceContract") != {
            "path": "skill_custom_root_motion_native.json",
            "schema": "endfield.skill-custom-root-motion-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or motion_contract.get("schema") != "endfield.skill-custom-root-motion-native-contract.v1"
        or motion_contract.get("status") != "exact-current-build"
        or motion_contract.get("dispatcher", {}).get("unionTag") != 0x0099
        or motion_contract.get("serializedMemberCount") != 24
        or not isinstance(motion_reads, list)
        or len(motion_reads) != 24
    ):
        raise ValueError("skillTimelineSharedSequence.contract:custom-root-motion-source-drift")
    building_route = next(
        (row for row in routes if row.get("tag") == "0x00B0"), None
    )
    if (
        not isinstance(building_route, dict)
        or building_route.get("typeName")
        != "Beyond.Gameplay.Core.FacBuildingPlayAnimationAction+Data"
        or building_route.get("memberCount")
        != FAC_BUILDING_PLAY_ANIMATION_MEMBER_COUNT
        or building_route.get("evidence") != "derivedPlanCorpusVerified"
    ):
        raise ValueError("skillTimelineSharedSequence.contract:fac-building-route-drift")
    armor_route = next((row for row in routes if row.get("tag") == "0x0159"), None)
    armor_contract = dependency_values.get("buff_159_native.json", {})
    if (
        not isinstance(armor_route, dict)
        or armor_route.get("typeName") != "Beyond.Gameplay.Core.SetSuperArmorAction+Data"
        or armor_route.get("memberCount") != len(SET_SUPER_ARMOR_MEMBER_READ_KINDS)
        or armor_route.get("sourceContract") != {
            "path": "buff_159_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member7",
        }
        or armor_contract.get("schemaVersion") != 1
        or tuple(armor_contract.get("anonymousReadOrder", {}).get("member7", ()))
        != SET_SUPER_ARMOR_MEMBER_READ_KINDS
        or not any(
            row[2] == "Deserialize" and "SetSuperArmorAction" in row[1]
            for row in armor_contract.get("methods", [])
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:set-super-armor-source-drift")
    blackboard_route = next((row for row in routes if row.get("tag") == "0x0142"), None)
    blackboard_contract = dependency_values.get("buff_142_native.json", {})
    if (
        not isinstance(blackboard_route, dict)
        or blackboard_route.get("typeName")
        != "Beyond.Gameplay.Core.SaveValueFromAIBlackboard+Data"
        or blackboard_route.get("memberCount")
        != len(SAVE_VALUE_FROM_AI_BLACKBOARD_READ_KINDS)
        or blackboard_route.get("sourceContract") != {
            "path": "buff_142_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member11",
        }
        or blackboard_contract.get("schemaVersion") != 1
        or tuple(blackboard_contract.get("anonymousReadOrder", {}).get("member11", ()))
        != SAVE_VALUE_FROM_AI_BLACKBOARD_READ_KINDS
        or not any(
            row[2] == "Deserialize" and "SaveValueFromAIBlackboard" in row[1]
            for row in blackboard_contract.get("methods", [])
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:ai-blackboard-source-drift")
    for tag, type_name, path, read_key, read_kinds in (
        *PASSIVE_CONDITION_ROUTES, *TIMELINE_SOURCE_ROUTES
    ):
        route = next((row for row in routes if row.get("tag") == tag), None)
        source = dependency_values.get(path, {})
        if (
            not isinstance(route, dict)
            or route.get("typeName") != type_name
            or route.get("memberCount") != len(read_kinds)
            or route.get("sourceContract") != {
                "path": path, "schemaVersion": 1,
                "orderedReadRef": f"anonymousReadOrder.{read_key}",
            }
            or source.get("schemaVersion") != 1
            or tuple(source.get("anonymousReadOrder", {}).get(read_key, ())) != read_kinds
            or not any(
                row[2] == "Deserialize" and type_name.split(".")[-1].split("+")[0] in row[1]
                for row in source.get("methods", [])
            )
        ):
            raise ValueError(f"skillTimelineSharedSequence.contract:action-source-drift:{tag}")
    camera_route = next((row for row in routes if row.get("tag") == "0x00E0"), None)
    camera_contract = dependency_values.get("buff_e0_native.json", {})
    camera_reads = camera_contract.get("anonymousReadOrder", {}).get("memberSourceCalls")
    if (
        not isinstance(camera_route, dict)
        or camera_route.get("typeName")
        != "Beyond.Gameplay.Core.LockCameraAimAction+LockCameraAimActionData"
        or camera_route.get("memberCount") != 54
        or camera_route.get("sourceContract") != {
            "path": "buff_e0_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.memberSourceCalls",
        }
        or camera_contract.get("schemaVersion") != 1
        or camera_contract.get("anonymousReadOrder", {}).get("memberCount") != 54
        or not isinstance(camera_reads, list)
        or [row.get("memberIndex") for row in camera_reads] != list(range(1, 55))
        or not any(
            row[2] == "Deserialize" and "LockCameraAimAction" in row[1]
            for row in camera_contract.get("methods", [])
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:lock-camera-source-drift")
    action_map_contract = dependency_values.get("buff_ad_native.json", {})
    if (
        action_map_contract.get("schemaVersion") != 1
        or action_map_contract.get("anonymousReadOrder", {}).get("mapMember2")
        != ["scalar32", "nullable-sequence-array"]
        or not any(
            row[2] == "Deserialize" and "AbilityActionMapForMemoryPack" in row[1]
            for row in action_map_contract.get("methods", [])
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:ability-action-map-source-drift")
    direction_route = next(
        (row for row in routes if row.get("tag") == "0x0082"), None
    )
    frontier = dependency_values.get("buff_frontier9.json", {})
    direction_source = next(
        (row for row in frontier.get("actions", []) if row.get("unionTag") == 0x0082), None
    )
    if (
        not isinstance(direction_route, dict)
        or direction_route.get("typeName")
        != "Beyond.Gameplay.Core.Conditions.CheckTwoDirectionAngle+Data"
        or direction_route.get("memberCount") != len(CHECK_TWO_DIRECTION_ANGLE_READ_KINDS)
        or direction_route.get("sourceContract") != {
            "path": "buff_frontier9.json",
            "schema": "endfield.buff-frontier9-native-contract.v1",
            "orderedReadRef": "actions[unionTag=130].readOrder",
        }
        or frontier.get("schema") != "endfield.buff-frontier9-native-contract.v1"
        or frontier.get("status") != "exact-current-build"
        or not isinstance(direction_source, dict)
        or direction_source.get("serializedMemberCount")
        != len(CHECK_TWO_DIRECTION_ANGLE_READ_KINDS)
        or direction_source.get("actualTypeName") != direction_route["typeName"]
        or tuple(direction_source.get("readOrder", ()))
        != CHECK_TWO_DIRECTION_ANGLE_READ_KINDS
    ):
        raise ValueError("skillTimelineSharedSequence.contract:two-direction-source-drift")
    step_route = next((row for row in routes if row.get("tag") == "0x0116"), None)
    step_source = dependency_values.get("skill_timeline_play_animation_step_native.json", {})
    step_wrapper = step_source.get("wrapper", {})
    if (
        not isinstance(step_route, dict)
        or step_route.get("typeName")
        != "Beyond.Gameplay.Core.PlayAnimationWithStep+PlayAnimationWithStepData"
        or step_route.get("memberCount") != 30
        or step_route.get("sourceContract") != {
            "path": "skill_timeline_play_animation_step_native.json",
            "schema": "endfield.skill-timeline-play-animation-step-native-contract.v1",
            "orderedReadRef": "wrapper.selectedReadOrder",
        }
        or step_source.get("schema")
        != "endfield.skill-timeline-play-animation-step-native-contract.v1"
        or step_source.get("status") != "exact-current-build"
        or step_source.get("dispatcher", {}).get("unionTag") != 0x0116
        or step_wrapper.get("serializedMemberCount") != 30
        or step_wrapper.get("typeName")
        != step_source["dispatcher"].get("wrapperName")
        or len(step_wrapper.get("selectedReadOrder", ())) != 14
        or step_source.get("dependencies") != [
            {"path": "skill_timeline_play_animation_native.json", "role": "inherited PlayAnimationActionData member16 source reads and shared TimelineActionData framing"}
        ]
    ):
        raise ValueError("skillTimelineSharedSequence.contract:play-animation-step-source-drift")
    crush_route = next((row for row in routes if row.get("tag") == "0x0097"), None)
    crush_source = next(
        (row for row in frontier.get("actions", []) if row.get("unionTag") == 0x0097), None
    )
    if (
        not isinstance(crush_route, dict)
        or crush_route.get("typeName") != "Beyond.Gameplay.Core.CrushAction+Data"
        or crush_route.get("memberCount") != len(CRUSH_READ_ORDER)
        or crush_route.get("sourceContract") != {
            "path": "buff_frontier9.json",
            "schema": "endfield.buff-frontier9-native-contract.v1",
            "orderedReadRef": "actions[unionTag=151].readOrder",
        }
        or frontier.get("schema") != "endfield.buff-frontier9-native-contract.v1"
        or frontier.get("status") != "exact-current-build"
        or not isinstance(crush_source, dict)
        or crush_source.get("actualTypeName") != crush_route["typeName"]
        or crush_source.get("serializedMemberCount") != len(CRUSH_READ_ORDER)
        or tuple(crush_source.get("readOrder", ())) != CRUSH_READ_ORDER
    ):
        raise ValueError("skillTimelineSharedSequence.contract:crush-source-drift")
    blow_route = next((row for row in routes if row.get("tag") == "0x001D"), None)
    blow_source = next(
        (row for row in frontier.get("actions", []) if row.get("unionTag") == 0x001D), None
    )
    if (
        not isinstance(blow_route, dict)
        or blow_route.get("typeName") != "Beyond.Gameplay.Core.BlowOffEnemyAction+Data"
        or blow_route.get("memberCount") != len(BLOW_OFF_ENEMY_READ_ORDER)
        or blow_route.get("sourceContract") != {
            "path": "buff_frontier9.json",
            "schema": "endfield.buff-frontier9-native-contract.v1",
            "orderedReadRef": "actions[unionTag=29].readOrder",
        }
        or frontier.get("schema") != "endfield.buff-frontier9-native-contract.v1"
        or frontier.get("status") != "exact-current-build"
        or not isinstance(blow_source, dict)
        or blow_source.get("actualTypeName") != blow_route["typeName"]
        or blow_source.get("serializedMemberCount") != len(BLOW_OFF_ENEMY_READ_ORDER)
        or tuple(blow_source.get("readOrder", ())) != BLOW_OFF_ENEMY_READ_ORDER
    ):
        raise ValueError("skillTimelineSharedSequence.contract:blow-off-enemy-source-drift")
    for tag, type_name, path, schema, count, read_ref in (
        (
            "0x006D", "Beyond.Gameplay.Core.Conditions.CheckPhysicalInflictionType+Data",
            "skill_timeline_check_physical_infliction_type_native.json",
            "endfield.skill-timeline-check-physical-infliction-type-native-contract.v1",
            6, "orderedSourceReads",
        ),
        (
            "0x0093", "Beyond.Gameplay.Core.CreateBuffAttachingSkill+Data",
            "skill_timeline_create_buff_attaching_skill_native.json",
            "endfield.skill-timeline-create-buff-attaching-skill-native-contract.v1",
            19, "inheritedFieldContract.wrapper.selectedReadOrder",
        ),
        (
            "0x00D3", "Beyond.Gameplay.Core.InheritCCSAction+Data",
            "skill_timeline_inherit_ccs_native.json",
            "endfield.skill-timeline-inherit-ccs-native-contract.v1",
            8, "orderedSourceReads",
        ),
        (
            "0x0032", "Beyond.Gameplay.Core.ChannelingDamageAction+Data",
            "skill_timeline_channeling_damage_native.json",
            "endfield.skill-timeline-channeling-damage-native-contract.v1",
            12, "orderedSourceReads",
        ),
        (
            "0x0064", "Beyond.Gameplay.Core.Conditions.CheckHitColliderOptions+Data",
            "skill_timeline_check_hit_collider_options_native.json",
            "endfield.skill-timeline-check-hit-collider-options-native-contract.v1",
            6, "orderedSourceReads",
        ),
        (
            "0x0085", "Beyond.Gameplay.Core.Conditions.CompareDeckAttr+Data",
            "skill_timeline_compare_deck_attr_native.json",
            "endfield.skill-timeline-compare-deck-attr-native-contract.v1",
            10, "orderedSourceReads",
        ),
        (
            "0x0059", "Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag+Data",
            "skill_timeline_check_buff_stack_num_by_tag_native.json",
            "endfield.skill-timeline-check-buff-stack-num-by-tag-native-contract.v1",
            9, "orderedSourceReads",
        ),
        (
            "0x00BA", "Beyond.Gameplay.Core.ForceSpellStatusAction+Data",
            "skill_timeline_force_spell_status_native.json",
            "endfield.skill-timeline-force-spell-status-native-contract.v1",
            11, "orderedSourceReads",
        ),
        (
            "0x00EB", "Beyond.Gameplay.Core.ModifyCameraLockPointAction+Data",
            "skill_timeline_modify_camera_lock_point_native.json",
            "endfield.skill-timeline-modify-camera-lock-point-native-contract.v1",
            6, "orderedSourceReads",
        ),
        (
            "0x0013", "Beyond.Gameplay.Core.ApplyArmor+Data",
            "skill_timeline_apply_armor_native.json",
            "endfield.skill-timeline-apply-armor-native-contract.v1",
            5, "orderedSourceReads",
        ),
        (
            "0x0019", "Beyond.Gameplay.Core.BlightMiasmaToleranceZero+Data",
            "skill_timeline_blight_miasma_tolerance_zero_native.json",
            "endfield.skill-timeline-blight-miasma-tolerance-zero-native-contract.v1",
            4, "orderedSourceReads",
        ),
        (
            "0x001A", "Beyond.Gameplay.Core.BlockMoveInterruptSkill+Data",
            "skill_timeline_block_move_interrupt_skill_native.json",
            "endfield.skill-timeline-block-move-interrupt-skill-native-contract.v1",
            4, "orderedSourceReads",
        ),
        (
            "0x0030", "Beyond.Gameplay.Core.ChannelingActionV2+Data",
            "skill_timeline_channeling_v2_native.json",
            "endfield.skill-timeline-channeling-v2-native-contract.v1",
            10, "orderedSourceReads",
        ),
        (
            "0x0034", "Beyond.Gameplay.Core.CharFollowAction+CharFollowActionData",
            "skill_timeline_char_follow_action_native.json",
            "endfield.skill-timeline-char-follow-action-native-contract.v1",
            4, "orderedSourceReads",
        ),
        (
            "0x0103", "Beyond.Gameplay.Core.OverrideBornPosition+Data",
            "skill_timeline_override_born_position_native.json",
            "endfield.skill-timeline-override-born-position-native-contract.v1",
            5, "orderedSourceReads",
        ),
        (
            "0x012C", "Beyond.Gameplay.Core.RefreshHeadBarShowHideAction+Data",
            "skill_timeline_refresh_head_bar_show_hide_native.json",
            "endfield.skill-timeline-refresh-head-bar-show-hide-native-contract.v1",
            4, "orderedSourceReads",
        ),
        (
            "0x00B9", "Beyond.Gameplay.Core.ForceHideHeadBarAction+Data",
            "skill_timeline_force_hide_head_bar_native.json",
            "endfield.skill-timeline-force-hide-head-bar-native-contract.v1",
            6, "orderedSourceReads",
        ),
        (
            "0x0091", "Beyond.Gameplay.Core.CreateAdditionalBattleShape+Data",
            "skill_timeline_additional_battle_shape_native.json",
            "endfield.skill-timeline-additional-battle-shape-native-contract.v1",
            10, "orderedSourceReads",
        ),
        (
            "0x017F", "Beyond.Gameplay.Core.ThrowPickupItemAction+Data",
            "skill_timeline_throw_pickup_item_native.json",
            "endfield.skill-timeline-throw-pickup-item-native-contract.v1",
            4, "orderedSourceReads",
        ),
        (
            "0x017A", "Beyond.Gameplay.Core.TakeDownAction+Data",
            "skill_timeline_take_down_native.json",
            "endfield.skill-timeline-take-down-native-contract.v1",
            12, "orderedSourceReads",
        ),
        (
            "0x0180", "Beyond.Gameplay.Core.ThrowPickupItemStartAction+Data",
            "skill_timeline_throw_pickup_item_start_native.json",
            "endfield.skill-timeline-throw-pickup-item-start-native-contract.v1",
            4, "orderedSourceReads",
        ),
        (
            "0x00B5", "Beyond.Gameplay.Core.FinishBuffByTag+Data",
            "skill_timeline_finish_buff_by_tag_native.json",
            "endfield.skill-timeline-finish-buff-by-tag-native-contract.v1",
            12, "orderedSourceReads",
        ),
    ):
        route = next((row for row in routes if row.get("tag") == tag), None)
        source = dependency_values.get(path, {})
        if (
            not isinstance(route, dict)
            or route.get("typeName") != type_name
            or route.get("memberCount") != count
            or route.get("sourceContract") != {
                "path": path, "schema": schema, "orderedReadRef": read_ref,
            }
            or source.get("schema") != schema
            or source.get("status") != "exact-current-build"
            or (source.get("dispatcher") or {}).get("unionTag", source.get("unionTag")) != int(tag, 16)
            or source.get("serializedMemberCount") != count
            or (
                tag in (
                    "0x006D", "0x00D3", "0x0032", "0x0064", "0x0085",
                    "0x0059", "0x00BA", "0x00EB",
                    "0x0013", "0x0019", "0x001A",
                    "0x0030", "0x0034", "0x00B5",
                    "0x0103", "0x012C", "0x00B9", "0x0091",
                    "0x017F", "0x0180", "0x017A",
                )
                and len(source.get("orderedSourceReads", ())) != count
            )
            or (
                tag == "0x0093"
                and source.get("inheritedFieldContract")
                != "skill_timeline_create_buff_native.json"
            )
        ):
            raise ValueError(f"skillTimelineSharedSequence.contract:action-source-drift:{tag}")
    for tag, path, schema, family, count in (
        (0x17, "skill_selector_finder_typhoea_native.json",
         "endfield.skill-selector-finder-typhoea-native-contract.v1", "SelectorFinder", 0),
        (0x07, "skill_selector_validator_in_screen_native.json",
         "endfield.skill-selector-validator-in-screen-native-contract.v1", "SelectorValidator", 0),
        (0x08, "skill_nested_interactive_key_validator_native.json",
         "endfield.skill-nested-interactive-key-validator-native-contract.v1", "SelectorValidator", 1),
    ):
        source = dependency_values.get(path, {})
        catalog = dependency_values.get("levelscript_union_tags.json", {})
        catalog_route = catalog.get("families", {}).get(family, [])[tag]
        if (
            source.get("schema") != schema
            or source.get("status") != "exact-current-build"
            or source.get("serializedMemberCount") != count
            or source.get("dispatcher", {}).get("unionTag") != tag
            or not isinstance(catalog_route, dict)
            or catalog_route.get("wrapperName")
            != source.get("dispatcher", {}).get("wrapperName")
            or catalog_route.get("memberCount") != count
        ):
            raise ValueError(f"skillTimelineSharedSequence.contract:nested-source-drift:{family}:{tag:#x}")
    usp_route = next((row for row in routes if row.get("tag") == "0x00FF"), None)
    usp_frontier = dependency_values.get("buff_frontier7.json", {})
    usp_source = next(
        (row for row in usp_frontier.get("actions", ()) if row.get("unionTag") == 0x00FF), None
    )
    if (
        not isinstance(usp_route, dict)
        or usp_route.get("typeName") != "Beyond.Gameplay.Core.ObtainUspInNormalSkill+Data"
        or usp_route.get("memberCount") != len(OBTAIN_USP_NORMAL_READ_ORDER)
        or usp_route.get("sourceContract") != {
            "path": "buff_frontier7.json",
            "schema": "endfield.buff-frontier7-native-contract.v1",
            "orderedReadRef": "actions[unionTag=255].readOrder",
        }
        or usp_frontier.get("schema") != "endfield.buff-frontier7-native-contract.v1"
        or usp_frontier.get("status") != "exact-current-build"
        or not isinstance(usp_source, dict)
        or usp_source.get("actualTypeName") != usp_route["typeName"]
        or usp_source.get("serializedMemberCount") != len(OBTAIN_USP_NORMAL_READ_ORDER)
        or tuple(usp_source.get("readOrder", ())) != OBTAIN_USP_NORMAL_READ_ORDER
    ):
        raise ValueError("skillTimelineSharedSequence.contract:obtain-usp-source-drift")
    combo_route = next((row for row in routes if row.get("tag") == "0x004E"), None)
    combo_contract = dependency_values.get("buff_4e_native.json", {})
    if (
        not isinstance(combo_route, dict)
        or combo_route.get("typeName") != "Beyond.Gameplay.Core.ComboCacheAction+Data"
        or combo_route.get("memberCount") != len(COMBO_CACHE_READ_KINDS)
        or combo_route.get("sourceContract") != {
            "path": "buff_4e_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member5",
        }
        or combo_contract.get("schemaVersion") != 1
        or tuple(combo_contract.get("anonymousReadOrder", {}).get("member5", ()))
        != COMBO_CACHE_READ_KINDS
        or not any(
            row[2] == "Deserialize" and "ComboCacheAction" in row[1]
            for row in combo_contract.get("methods", [])
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:combo-cache-source-drift")
    marker_route = next((row for row in routes if row.get("tag") == "0x0007"), None)
    marker_contract = dependency_values.get("buff_07_native.json", {})
    if (
        not isinstance(marker_route, dict)
        or marker_route.get("typeName") != "Beyond.Gameplay.Core.AddAIMarkerAction+Data"
        or marker_route.get("memberCount") != len(ADD_AI_MARKER_READ_KINDS)
        or marker_route.get("sourceContract") != {
            "path": "buff_07_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member8",
        }
        or marker_contract.get("schemaVersion") != 1
        or tuple(marker_contract.get("anonymousReadOrder", {}).get("member8", ()))
        != ADD_AI_MARKER_READ_KINDS
        or not any(
            row[2] == "Deserialize" and "AddAIMarkerAction" in row[1]
            for row in marker_contract.get("methods", [])
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:add-ai-marker-source-drift")
    allow_route = next((row for row in routes if row.get("tag") == "0x000E"), None)
    if (
        not isinstance(allow_route, dict)
        or allow_route.get("typeName")
        != "Beyond.Gameplay.Core.AllowNextSkillAction+Data"
        or allow_route.get("memberCount") != 5
        or allow_route.get("evidence") != "selectedDerivedPlanCorpusVerified"
    ):
        raise ValueError("skillTimelineSharedSequence.contract:allow-next-skill-route-drift")
    for tag, type_name in (
        ("0x009E", "Beyond.Gameplay.Core.DisableRootMotionAction+Data"),
        ("0x00E8", "Beyond.Gameplay.Core.MarkCanInterrupt+Data"),
    ):
        route = next((row for row in routes if row.get("tag") == tag), None)
        if (
            not isinstance(route, dict)
            or route.get("typeName") != type_name
            or route.get("memberCount") != 4
            or route.get("evidence") != "selectedDerivedPlanCorpusVerified"
        ):
            raise ValueError(f"skillTimelineSharedSequence.contract:fixed-four-route-drift:{tag}")
    teleport_route = next(
        (row for row in routes if row.get("tag") == "0x017D"), None
    )
    teleport_source = next(
        (row for row in frontier.get("actions", []) if row.get("unionTag") == 0x017D), None
    )
    if (
        not isinstance(teleport_route, dict)
        or teleport_route.get("typeName")
        != "Beyond.Gameplay.Core.TeleportPosSelectAction+Data"
        or teleport_route.get("memberCount") != 9
        or teleport_route.get("sourceContract") != {
            "path": "buff_frontier9.json",
            "schema": "endfield.buff-frontier9-native-contract.v1",
            "orderedReadRef": "actions[unionTag=381].readOrder",
        }
        or not isinstance(teleport_source, dict)
        or teleport_source.get("serializedMemberCount") != 9
        or teleport_source.get("actualTypeName") != teleport_route["typeName"]
        or tuple(teleport_source.get("readOrder", ())) != (
            "byte", "scalar32", "scalar32", "scalar32", "string",
            "teleport-fix-distance-data", "teleport-ranged-data",
            "target-settings", "enum32",
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:teleport-pos-select-source-drift")
    save_angle_route = next(
        (row for row in routes if row.get("tag") == "0x0141"), None
    )
    save_angle_source = next(
        (row for row in frontier.get("actions", []) if row.get("unionTag") == 0x0141), None
    )
    if (
        not isinstance(save_angle_route, dict)
        or save_angle_route.get("typeName")
        != "Beyond.Gameplay.Core.SaveTwoDirectionAngle+Data"
        or save_angle_route.get("memberCount") != 11
        or save_angle_route.get("sourceContract") != {
            "path": "buff_frontier9.json",
            "schema": "endfield.buff-frontier9-native-contract.v1",
            "orderedReadRef": "actions[unionTag=321].readOrder",
        }
        or not isinstance(save_angle_source, dict)
        or save_angle_source.get("actualTypeName") != save_angle_route["typeName"]
        or save_angle_source.get("serializedMemberCount") != 11
        or tuple(save_angle_source.get("readOrder", ())) != (
            "byte", "scalar32", "scalar32", "scalar32", "enum32",
            "target-settings", "target-settings", "enum32",
            "target-settings", "target-settings", "string",
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:save-two-direction-source-drift")
    navmesh_route = next((row for row in routes if row.get("tag") == "0x0009"), None)
    frontier8 = dependency_values.get("buff_frontier8.json", {})
    navmesh_source = next(
        (row for row in frontier8.get("actions", []) if row.get("unionTag") == 0x0009), None
    )
    if (
        not isinstance(navmesh_route, dict)
        or navmesh_route.get("typeName")
        != "Beyond.Gameplay.Core.AddDynamicNavmeshObstacle+Data"
        or navmesh_route.get("memberCount") != 6
        or navmesh_route.get("sourceContract") != {
            "path": "buff_frontier8.json",
            "schema": "endfield.buff-frontier8-native-contract.v1",
            "orderedReadRef": "actions[unionTag=9].readOrder",
        }
        or frontier8.get("schema") != "endfield.buff-frontier8-native-contract.v1"
        or not isinstance(navmesh_source, dict)
        or navmesh_source.get("actualTypeName") != navmesh_route["typeName"]
        or navmesh_source.get("serializedMemberCount") != 6
        or tuple(navmesh_source.get("readOrder", ())) != (
            "byte", "scalar32", "scalar32", "scalar32",
            "string-list", "target-settings",
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:navmesh-obstacle-source-drift")
    extend_buff_route = next((row for row in routes if row.get("tag") == "0x00AF"), None)
    extend_buff_source = next(
        (row for row in frontier8.get("actions", []) if row.get("unionTag") == 0x00AF), None
    )
    if (
        not isinstance(extend_buff_route, dict)
        or extend_buff_route.get("typeName") != "Beyond.Gameplay.Core.ExtendBuffAction+Data"
        or extend_buff_route.get("memberCount") != 6
        or extend_buff_route.get("sourceContract") != {
            "path": "buff_frontier8.json",
            "schema": "endfield.buff-frontier8-native-contract.v1",
            "orderedReadRef": "actions[unionTag=175].readOrder",
        }
        or not isinstance(extend_buff_source, dict)
        or extend_buff_source.get("actualTypeName") != extend_buff_route["typeName"]
        or extend_buff_source.get("serializedMemberCount") != 6
        or tuple(extend_buff_source.get("readOrder", ())) != (
            "byte", "scalar32", "scalar32", "scalar32",
            "target-settings", "buff-find-settings",
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:extend-buff-source-drift")
    patrol_route = next((row for row in routes if row.get("tag") == "0x00C2"), None)
    patrol_source = next(
        (row for row in frontier8.get("actions", []) if row.get("unionTag") == 0x00C2), None
    )
    if (
        not isinstance(patrol_route, dict)
        or patrol_route.get("typeName") != "Beyond.Gameplay.Core.GetPatrolTeleportPos+Data"
        or patrol_route.get("memberCount") != 6
        or patrol_route.get("sourceContract") != {
            "path": "buff_frontier8.json",
            "schema": "endfield.buff-frontier8-native-contract.v1",
            "orderedReadRef": "actions[unionTag=194].readOrder",
        }
        or not isinstance(patrol_source, dict)
        or patrol_source.get("actualTypeName") != patrol_route["typeName"]
        or patrol_source.get("serializedMemberCount") != 6
        or tuple(patrol_source.get("readOrder", ())) != (
            "byte", "scalar32", "scalar32", "scalar32", "string", "float32",
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:patrol-teleport-source-drift")
    for tag, name, source_path, read_order in (
        (
            "0x000C", "Beyond.Gameplay.Core.AddTagToEntities+Data",
            "buff_0c_native.json",
            ("byte", "scalar32", "scalar32", "scalar32", "paired-payload", "target", "tag-elements", "byte"),
        ),
        (
            "0x0065", "Beyond.Gameplay.Core.Conditions.CheckHp+Data",
            "buff_65_native.json",
            ("byte", "scalar32", "scalar32", "scalar32", "scalar32", "target-profile", "byte", "scalar-payload"),
        ),
        (
            "0x006E", "Beyond.Gameplay.Core.Conditions.CheckPoiseValue+Data",
            "buff_6e_native.json",
            ("byte", "scalar32", "scalar32", "scalar32", "scalar32", "target-profile", "byte", "scalar-payload"),
        ),
    ):
        route = next((row for row in routes if row.get("tag") == tag), None)
        source = dependency_values.get(source_path, {})
        if (
            not isinstance(route, dict)
            or route.get("typeName") != name
            or route.get("memberCount") != 8
            or route.get("sourceContract") != {
                "path": source_path,
                "schemaVersion": 1,
                "orderedReadRef": "anonymousReadOrder.member8",
            }
            or source.get("schemaVersion") != 1
            or tuple(source.get("anonymousReadOrder", {}).get("member8", ())) != read_order
        ):
            raise ValueError(f"skillTimelineSharedSequence.contract:buff-reuse-source-drift:{tag}")
    snap_route = next((row for row in routes if row.get("tag") == "0x0168"), None)
    snap_contract = dependency_values.get("skill_snap_to_target_with_range_native.json", {})
    snap_reads = snap_contract.get("orderedSourceReads")
    if (
        not isinstance(snap_route, dict)
        or snap_route.get("typeName")
        != "Beyond.Gameplay.Core.SnapToTargetWithRangeAction+Data"
        or snap_route.get("memberCount") != 18
        or snap_route.get("sourceContract") != {
            "path": "skill_snap_to_target_with_range_native.json",
            "schema": "endfield.skill-snap-to-target-with-range-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or snap_contract.get("schema")
        != "endfield.skill-snap-to-target-with-range-native-contract.v1"
        or snap_contract.get("status") != "exact-current-build"
        or snap_contract.get("dispatcher", {}).get("unionTag") != 0x0168
        or snap_contract.get("serializedMemberCount") != 18
        or not isinstance(snap_reads, list)
        or len(snap_reads) != 18
    ):
        raise ValueError("skillTimelineSharedSequence.contract:snap-to-target-source-drift")
    push_route = next((row for row in routes if row.get("tag") == "0x011E"), None)
    push_contract = dependency_values.get("skill_timeline_push_back_native.json", {})
    push_reads = push_contract.get("orderedSourceReads")
    if (
        not isinstance(push_route, dict)
        or push_route.get("typeName") != "Beyond.Gameplay.Core.PushBackAction+Data"
        or push_route.get("memberCount") != 20
        or push_route.get("sourceContract") != {
            "path": "skill_timeline_push_back_native.json",
            "schema": "endfield.skill-timeline-push-back-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or push_contract.get("schema")
        != "endfield.skill-timeline-push-back-native-contract.v1"
        or push_contract.get("status") != "exact-current-build"
        or push_contract.get("dispatcher", {}).get("unionTag") != 0x011E
        or push_contract.get("serializedMemberCount") != 20
        or not isinstance(push_reads, list)
        or len(push_reads) != 20
    ):
        raise ValueError("skillTimelineSharedSequence.contract:push-back-source-drift")
    tick_route = next((row for row in routes if row.get("tag") == "0x0181"), None)
    tick_contract = dependency_values.get("skill_timeline_tick_interval_native.json", {})
    tick_reads = tick_contract.get("orderedSourceReads")
    if (
        not isinstance(tick_route, dict)
        or tick_route.get("typeName") != "Beyond.Gameplay.Core.TickIntervalAction+Data"
        or tick_route.get("memberCount") != 9
        or tick_route.get("sourceContract") != {
            "path": "skill_timeline_tick_interval_native.json",
            "schema": "endfield.skill-timeline-tick-interval-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or tick_contract.get("schema")
        != "endfield.skill-timeline-tick-interval-native-contract.v1"
        or tick_contract.get("status") != "exact-current-build"
        or tick_contract.get("dispatcher", {}).get("unionTag") != 0x0181
        or not isinstance(tick_reads, list)
        or len(tick_reads) != 9
    ):
        raise ValueError("skillTimelineSharedSequence.contract:tick-interval-source-drift")
    for tag, type_name, count, path, schema in (
        (
            "0x0025", "Beyond.Gameplay.Core.CameraRotateAction+CameraRotationActionData",
            10, "skill_timeline_camera_rotate_native.json",
            "endfield.skill-timeline-camera-rotate-native-contract.v1",
        ),
        (
            "0x00BF", "Beyond.Gameplay.Core.GainBreakingAttackAtb+Data",
            7, "skill_timeline_gain_breaking_attack_atb_native.json",
            "endfield.skill-timeline-gain-breaking-attack-atb-native-contract.v1",
        ),
    ):
        route = next((row for row in routes if row.get("tag") == tag), None)
        source = dependency_values.get(path, {})
        if (
            not isinstance(route, dict)
            or route.get("typeName") != type_name
            or route.get("memberCount") != count
            or route.get("sourceContract") != {
                "path": path, "schema": schema, "orderedReadRef": "orderedSourceReads",
            }
            or source.get("schema") != schema
            or source.get("status") != "exact-current-build"
            or source.get("dispatcher", {}).get("unionTag") != int(tag, 16)
            or source.get("serializedMemberCount") != count
            or len(source.get("orderedSourceReads", ())) != count
        ):
            raise ValueError(f"skillTimelineSharedSequence.contract:standalone-source-drift:{tag}")
    override_route = next((row for row in routes if row.get("tag") == "0x0104"), None)
    override_source = next(
        (row for row in frontier.get("actions", []) if row.get("unionTag") == 0x0104), None
    )
    if (
        not isinstance(override_route, dict)
        or override_route.get("typeName")
        != "Beyond.Gameplay.Core.OverrideCameraFollowAction+OverrideCameraFollowActionData"
        or override_route.get("memberCount") != 12
        or override_route.get("sourceContract") != {
            "path": "buff_frontier9.json",
            "schema": "endfield.buff-frontier9-native-contract.v1",
            "orderedReadRef": "actions[unionTag=260].readOrder",
        }
        or not isinstance(override_source, dict)
        or override_source.get("actualTypeName") != override_route["typeName"]
        or override_source.get("serializedMemberCount") != 12
        or len(override_source.get("readOrder", ())) != 12
    ):
        raise ValueError("skillTimelineSharedSequence.contract:override-camera-follow-source-drift")
    not_next_route = next((row for row in routes if row.get("tag") == "0x00FD"), None)
    not_next_source = dependency_values.get("buff_fd_native.json", {})
    if (
        not isinstance(not_next_route, dict)
        or not_next_route.get("typeName") != "Beyond.Gameplay.Core.NotNextCheckAction+Data"
        or not_next_route.get("memberCount") != 4
        or not_next_route.get("sourceContract") != {
            "path": "buff_fd_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member4",
        }
        or not_next_source.get("schemaVersion") != 1
        or tuple(not_next_source.get("anonymousReadOrder", {}).get("member4", ()))
        != ("byte", "scalar32", "scalar32", "scalar32")
    ):
        raise ValueError("skillTimelineSharedSequence.contract:not-next-check-source-drift")
    curve_route = next((row for row in routes if row.get("tag") == "0x0098"), None)
    curve_source = dependency_values.get("buff_98_native.json", {})
    curve_selected = dependency_values.get("skill_timeline_curve_evaluate_float_native.json", {})
    curve_reads = (
        "byte", "scalar32", "scalar32", "scalar32", "byte-payload",
        "curve", "scalar-payload", "byte-payload", "byte",
    )
    if (
        not isinstance(curve_route, dict)
        or curve_route.get("typeName") != "Beyond.Gameplay.Core.CurveEvaluateFloat+Data"
        or curve_route.get("memberCount") != 9
        or curve_route.get("sourceContract") != {
            "path": "buff_98_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member9",
        }
        or curve_source.get("schemaVersion") != 1
        or tuple(curve_source.get("anonymousReadOrder", {}).get("member9", ())) != curve_reads
        or curve_selected.get("schema")
        != "endfield.skill-timeline-curve-evaluate-float-native-contract.v1"
        or curve_selected.get("status") != "exact-current-build"
        or curve_selected.get("dispatcher", {}).get("unionTag") != 0x0098
        or curve_selected.get("serializedMemberCount") != 9
    ):
        raise ValueError("skillTimelineSharedSequence.contract:curve-evaluate-float-source-drift")
    command_route = next((row for row in routes if row.get("tag") == "0x004F"), None)
    command_source = dependency_values.get("skill_timeline_command_to_characters_native.json", {})
    if (
        not isinstance(command_route, dict)
        or command_route.get("typeName")
        != "Beyond.Gameplay.Core.CommandToCharactersAction+CommandToCharactersActionData"
        or command_route.get("memberCount") != 14
        or command_route.get("sourceContract") != {
            "path": "skill_timeline_command_to_characters_native.json",
            "schema": "endfield.skill-timeline-command-to-characters-native-contract.v1",
        }
        or command_source.get("schema")
        != "endfield.skill-timeline-command-to-characters-native-contract.v1"
        or command_source.get("status") != "exact-current-build"
        or command_source.get("dispatcher", {}).get("unionTag") != 0x004F
        or command_source.get("serializedMemberCount") != 14
        or len(command_source.get("orderedSourceReads", ())) != 14
    ):
        raise ValueError("skillTimelineSharedSequence.contract:command-to-characters-source-drift")
    move_route = next((row for row in routes if row.get("tag") == "0x0123"), None)
    move_source = dependency_values.get("skill_timeline_receive_move_input_native.json", {})
    if (
        not isinstance(move_route, dict)
        or move_route.get("typeName") != "Beyond.Gameplay.Core.ReceiveMoveInputAction+Data"
        or move_route.get("memberCount") != 20
        or move_route.get("sourceContract") != {
            "path": "skill_timeline_receive_move_input_native.json",
            "schema": "endfield.skill-timeline-receive-move-input-native-contract.v1",
        }
        or move_source.get("schema")
        != "endfield.skill-timeline-receive-move-input-native-contract.v1"
        or move_source.get("status") != "exact-current-build"
        or move_source.get("dispatcher", {}).get("unionTag") != 0x0123
        or move_source.get("outer", {}).get("serializedMemberCount") != 20
        or len(move_source.get("outer", {}).get("orderedSourceReads", ())) != 20
        or move_source.get("moveParam", {}).get("serializedMemberCount") != 9
        or len(move_source.get("moveParam", {}).get("orderedSourceReads", ())) != 9
    ):
        raise ValueError("skillTimelineSharedSequence.contract:receive-move-input-source-drift")
    combo_alpha_route = next((row for row in routes if row.get("tag") == "0x003D"), None)
    combo_alpha_source = dependency_values.get(
        "skill_timeline_check_combo_skill_camera_alpha_native.json", {}
    )
    if (
        not isinstance(combo_alpha_route, dict)
        or combo_alpha_route.get("typeName")
        != "Beyond.Gameplay.Core.CheckComboSkillCameraAlphaSetting+Data"
        or combo_alpha_route.get("memberCount") != 5
        or combo_alpha_route.get("sourceContract") != {
            "path": "skill_timeline_check_combo_skill_camera_alpha_native.json",
            "schema": "endfield.skill-timeline-check-combo-skill-camera-alpha-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or combo_alpha_source.get("schema")
        != "endfield.skill-timeline-check-combo-skill-camera-alpha-native-contract.v1"
        or combo_alpha_source.get("status") != "exact-current-build"
        or combo_alpha_source.get("dispatcher", {}).get("unionTag") != 0x003D
        or combo_alpha_source.get("serializedMemberCount") != 5
        or len(combo_alpha_source.get("orderedSourceReads", ())) != 5
    ):
        raise ValueError("skillTimelineSharedSequence.contract:combo-skill-camera-alpha-source-drift")
    unlock_route = next((row for row in routes if row.get("tag") == "0x017E"), None)
    unlock_source = next(
        (row for row in frontier.get("actions", ()) if row.get("unionTag") == 0x017E), None
    )
    if (
        not isinstance(unlock_route, dict)
        or unlock_route.get("typeName") != "Beyond.Gameplay.Core.TemporaryUnlockAction+Data"
        or unlock_route.get("memberCount") != 8
        or unlock_route.get("sourceContract") != {
            "path": "buff_frontier9.json",
            "schema": "endfield.buff-frontier9-native-contract.v1",
            "orderedReadRef": "actions[unionTag=382].readOrder",
        }
        or not isinstance(unlock_source, dict)
        or unlock_source.get("actualTypeName") != unlock_route["typeName"]
        or unlock_source.get("serializedMemberCount") != 8
        or len(unlock_source.get("readOrder", ())) != 8
    ):
        raise ValueError("skillTimelineSharedSequence.contract:temporary-unlock-source-drift")
    move_check_route = next((row for row in routes if row.get("tag") == "0x0045"), None)
    move_check_source = dependency_values.get("skill_timeline_check_has_move_input_native.json", {})
    if (
        not isinstance(move_check_route, dict)
        or move_check_route.get("typeName") != "Beyond.Gameplay.Core.CheckHasMoveInput+Data"
        or move_check_route.get("memberCount") != 4
        or move_check_route.get("sourceContract") != {
            "path": "skill_timeline_check_has_move_input_native.json",
            "schema": "endfield.skill-timeline-check-has-move-input-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or move_check_source.get("schema")
        != "endfield.skill-timeline-check-has-move-input-native-contract.v1"
        or move_check_source.get("status") != "exact-current-build"
        or move_check_source.get("dispatcher", {}).get("unionTag") != 0x0045
        or len(move_check_source.get("orderedSourceReads", ())) != 4
        or move_check_source.get("setterMethods") != []
    ):
        raise ValueError("skillTimelineSharedSequence.contract:check-has-move-input-source-drift")
    togglable_route = next((row for row in routes if row.get("tag") == "0x0184"), None)
    togglable_source = dependency_values.get("buff_184_native.json", {})
    togglable_catalog = dependency_values.get("levelscript_union_tags.json", {})
    togglable_actions = togglable_catalog.get("families", {}).get("AbilityActionData")
    togglable_entry = (
        togglable_actions[0x0184]
        if isinstance(togglable_actions, list) and len(togglable_actions) > 0x0184 else None
    )
    if (
        not isinstance(togglable_route, dict)
        or togglable_route.get("typeName") != "Beyond.Gameplay.Core.TogglableAction+Data"
        or togglable_route.get("memberCount") != 6
        or togglable_route.get("sourceContract") != {
            "path": "buff_184_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member6",
        }
        or togglable_source.get("schemaVersion") != 1
        or tuple(togglable_source.get("anonymousReadOrder", {}).get("member6", ()))
        != ("byte", "scalar32", "scalar32", "scalar32", "sequence", "sequence")
        or togglable_catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or not isinstance(togglable_entry, dict)
        or togglable_entry.get("tag") != 0x0184
        or togglable_entry.get("wrappedType") != togglable_route["typeName"]
        or togglable_entry.get("memberCount") != 6
    ):
        raise ValueError("skillTimelineSharedSequence.contract:togglable-source-drift")
    squad_route = next((row for row in routes if row.get("tag") == "0x0052"), None)
    squad_source = dependency_values.get("buff_52_native.json", {})
    squad_entry = (
        togglable_actions[0x0052]
        if isinstance(togglable_actions, list) and len(togglable_actions) > 0x0052 else None
    )
    if (
        not isinstance(squad_route, dict)
        or squad_route.get("typeName") != "Beyond.Gameplay.Core.Condition.CheckSquadInFight+Data"
        or squad_route.get("memberCount") != 5
        or squad_route.get("sourceContract") != {
            "path": "buff_52_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member5",
        }
        or squad_source.get("schemaVersion") != 1
        or tuple(squad_source.get("anonymousReadOrder", {}).get("member5", ()))
        != ("byte", "scalar32", "scalar32", "scalar32", "byte")
        or not isinstance(squad_entry, dict)
        or squad_entry.get("tag") != 0x0052
        or squad_entry.get("wrappedType") != squad_route["typeName"]
        or squad_entry.get("memberCount") != 5
    ):
        raise ValueError("skillTimelineSharedSequence.contract:check-squad-in-fight-source-drift")
    break_route = next((row for row in routes if row.get("tag") == "0x0001"), None)
    break_source = dependency_values.get("skill_timeline_break_interactive_native.json", {})
    if (
        not isinstance(break_route, dict)
        or break_route.get("typeName")
        != "Beyond.Gameplay.Core.AbilityActions.BreakInteractiveAction+Data"
        or break_route.get("memberCount") != 9
        or break_route.get("sourceContract") != {
            "path": "skill_timeline_break_interactive_native.json",
            "schema": "endfield.skill-timeline-break-interactive-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or break_source.get("schema")
        != "endfield.skill-timeline-break-interactive-native-contract.v1"
        or break_source.get("status") != "exact-current-build"
        or break_source.get("dispatcher", {}).get("unionTag") != 0x0001
        or break_source.get("serializedMemberCount") != 9
        or len(break_source.get("orderedSourceReads", ())) != 9
        or break_source.get("finder9", {}).get("serializedMemberCount") != 12
        or len(break_source.get("finder9", {}).get("orderedSourceReads", ())) != 12
    ):
        raise ValueError("skillTimelineSharedSequence.contract:break-interactive-source-drift")
    inherit_route = next((row for row in routes if row.get("tag") == "0x00D2"), None)
    inherit_source = dependency_values.get("skill_timeline_inherit_buff_native.json", {})
    if (
        not isinstance(inherit_route, dict)
        or inherit_route.get("typeName") != "Beyond.Gameplay.Core.InheritBuffAction+Data"
        or inherit_route.get("memberCount") != 9
        or inherit_route.get("sourceContract") != {
            "path": "skill_timeline_inherit_buff_native.json",
            "schema": "endfield.skill-timeline-inherit-buff-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or inherit_source.get("schema")
        != "endfield.skill-timeline-inherit-buff-native-contract.v1"
        or inherit_source.get("status") != "exact-current-build"
        or inherit_source.get("dispatcher", {}).get("unionTag") != 0x00D2
        or inherit_source.get("serializedMemberCount") != 9
        or len(inherit_source.get("orderedSourceReads", ())) != 9
    ):
        raise ValueError("skillTimelineSharedSequence.contract:inherit-buff-source-drift")
    animated_route = next((row for row in routes if row.get("tag") == "0x0010"), None)
    animated_source = dependency_values.get("skill_timeline_animated_camera_native.json", {})
    if (
        not isinstance(animated_route, dict)
        or animated_route.get("typeName")
        != "Beyond.Gameplay.Core.AnimatedCameraAction+AnimatedCameraActionData"
        or animated_route.get("memberCount") != 24
        or animated_route.get("sourceContract") != {
            "path": "skill_timeline_animated_camera_native.json",
            "schema": "endfield.skill-timeline-animated-camera-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or animated_source.get("schema")
        != "endfield.skill-timeline-animated-camera-native-contract.v1"
        or animated_source.get("status") != "exact-current-build"
        or animated_source.get("dispatcher", {}).get("unionTag") != 0x0010
        or animated_source.get("serializedMemberCount") != 24
        or len(animated_source.get("orderedSourceReads", ())) != 24
    ):
        raise ValueError("skillTimelineSharedSequence.contract:animated-camera-source-drift")
    hide_route = next((row for row in routes if row.get("tag") == "0x00C6"), None)
    hide_source = dependency_values.get("skill_timeline_hide_ui_native.json", {})
    if (
        not isinstance(hide_route, dict)
        or hide_route.get("typeName") != "Beyond.Gameplay.Core.HideUIAction+Data"
        or hide_route.get("memberCount") != 5
        or hide_route.get("sourceContract") != {
            "path": "skill_timeline_hide_ui_native.json",
            "schema": "endfield.skill-timeline-hide-ui-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or hide_source.get("schema") != "endfield.skill-timeline-hide-ui-native-contract.v1"
        or hide_source.get("status") != "exact-current-build"
        or hide_source.get("dispatcher", {}).get("unionTag") != 0x00C6
        or hide_source.get("serializedMemberCount") != 5
        or len(hide_source.get("orderedSourceReads", ())) != 5
    ):
        raise ValueError("skillTimelineSharedSequence.contract:hide-ui-source-drift")
    move_route = next((row for row in routes if row.get("tag") == "0x00F8"), None)
    move_source = dependency_values.get("skill_timeline_move_to_location_native.json", {})
    if (
        not isinstance(move_route, dict)
        or move_route.get("typeName") != "Beyond.Gameplay.Core.MoveToLocationAction+Data"
        or move_route.get("memberCount") != 23
        or move_route.get("sourceContract") != {
            "path": "skill_timeline_move_to_location_native.json",
            "schema": "endfield.skill-timeline-move-to-location-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or move_source.get("schema")
        != "endfield.skill-timeline-move-to-location-native-contract.v1"
        or move_source.get("status") != "exact-current-build"
        or move_source.get("dispatcher", {}).get("unionTag") != 0x00F8
        or move_source.get("serializedMemberCount") != 23
        or len(move_source.get("orderedSourceReads", ())) != 23
    ):
        raise ValueError("skillTimelineSharedSequence.contract:move-to-location-source-drift")
    ultimate_route = next((row for row in routes if row.get("tag") == "0x0194"), None)
    ultimate_source = dependency_values.get("skill_timeline_ultimate_time_native.json", {})
    if (
        not isinstance(ultimate_route, dict)
        or ultimate_route.get("typeName") != "Beyond.Gameplay.Core.UltimateTimeAction+Data"
        or ultimate_route.get("memberCount") != 7
        or ultimate_route.get("sourceContract") != {
            "path": "skill_timeline_ultimate_time_native.json",
            "schema": "endfield.skill-timeline-ultimate-time-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or ultimate_source.get("schema")
        != "endfield.skill-timeline-ultimate-time-native-contract.v1"
        or ultimate_source.get("status") != "exact-current-build"
        or ultimate_source.get("dispatcher", {}).get("unionTag") != 0x0194
        or ultimate_source.get("serializedMemberCount") != 7
        or len(ultimate_source.get("orderedSourceReads", ())) != 7
    ):
        raise ValueError("skillTimelineSharedSequence.contract:ultimate-time-source-drift")
    show_route = next((row for row in routes if row.get("tag") == "0x0193"), None)
    show_source = dependency_values.get("skill_timeline_ultimate_show_native.json", {})
    if (
        not isinstance(show_route, dict)
        or show_route.get("typeName") != "Beyond.Gameplay.Core.UltimateShowAction+Data"
        or show_route.get("memberCount") != 4
        or show_route.get("sourceContract") != {
            "path": "skill_timeline_ultimate_show_native.json",
            "schema": "endfield.skill-timeline-ultimate-show-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or show_source.get("schema")
        != "endfield.skill-timeline-ultimate-show-native-contract.v1"
        or show_source.get("status") != "exact-current-build"
        or show_source.get("dispatcher", {}).get("unionTag") != 0x0193
        or show_source.get("serializedMemberCount") != 4
        or len(show_source.get("orderedSourceReads", ())) != 4
    ):
        raise ValueError("skillTimelineSharedSequence.contract:ultimate-show-source-drift")
    channeling_route = next((row for row in routes if row.get("tag") == "0x0031"), None)
    channeling_source = dependency_values.get("skill_timeline_channeling_casting_native.json", {})
    if (
        not isinstance(channeling_route, dict)
        or channeling_route.get("typeName") != "Beyond.Gameplay.Core.ChannelingCastingAction+Data"
        or channeling_route.get("memberCount") != 8
        or channeling_route.get("sourceContract") != {
            "path": "skill_timeline_channeling_casting_native.json",
            "schema": "endfield.skill-timeline-channeling-casting-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or channeling_source.get("schema")
        != "endfield.skill-timeline-channeling-casting-native-contract.v1"
        or channeling_source.get("status") != "exact-current-build"
        or channeling_source.get("dispatcher", {}).get("unionTag") != 0x0031
        or channeling_source.get("serializedMemberCount") != 8
        or len(channeling_source.get("orderedSourceReads", ())) != 8
    ):
        raise ValueError("skillTimelineSharedSequence.contract:channeling-casting-source-drift")
    mount_route = next((row for row in routes if row.get("tag") == "0x00F3"), None)
    mount_source = dependency_values.get("skill_timeline_modify_weapon_mount_point_native.json", {})
    if (
        not isinstance(mount_route, dict)
        or mount_route.get("typeName") != "Beyond.Gameplay.Core.ModifyWeaponMountPoint+Data"
        or mount_route.get("memberCount") != 9
        or mount_route.get("sourceContract") != {
            "path": "skill_timeline_modify_weapon_mount_point_native.json",
            "schema": "endfield.skill-timeline-modify-weapon-mount-point-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or mount_source.get("schema")
        != "endfield.skill-timeline-modify-weapon-mount-point-native-contract.v1"
        or mount_source.get("status") != "exact-current-build"
        or mount_source.get("dispatcher", {}).get("unionTag") != 0x00F3
        or mount_source.get("serializedMemberCount") != 9
        or len(mount_source.get("orderedSourceReads", ())) != 9
    ):
        raise ValueError("skillTimelineSharedSequence.contract:modify-mount-source-drift")
    for tag, type_name, path, schema, count, read_ref in (
        (
            "0x0121", "Beyond.Gameplay.Core.RayCastEffectAction+RayCastEffectActionData",
            "skill_timeline_raycast_effect_native.json",
            "endfield.skill-timeline-raycast-effect-native-contract.v1", 33,
            "sections.action.orderedSourceReads",
        ),
        (
            "0x0114", "Beyond.Gameplay.Core.PickTargetAction+Data",
            "skill_timeline_pick_target_native.json",
            "endfield.skill-timeline-pick-target-native-contract.v1", 7,
            "orderedSourceReads",
        ),
        (
            "0x00A0", "Beyond.Gameplay.Core.DoOnceAction+Data",
            "skill_timeline_do_once_native.json",
            "endfield.skill-timeline-do-once-native-contract.v1", 5,
            "orderedSourceReads",
        ),
        (
            "0x0072", "Beyond.Gameplay.Core.Conditions.CheckSkillCameraMotionFree+Data",
            "skill_timeline_check_skill_camera_motion_free_native.json",
            "endfield.skill-timeline-check-skill-camera-motion-free-native-contract.v1", 6,
            "orderedSourceReads",
        ),
        (
            "0x007D", "Beyond.Gameplay.Core.Conditions.CheckTargetAngle+Data",
            "skill_timeline_check_target_angle_native.json",
            "endfield.skill-timeline-check-target-angle-native-contract.v1", 8,
            "orderedSourceReads",
        ),
        (
            "0x00FB", "Beyond.Gameplay.Core.MoveToTargetAction+Data",
            "skill_timeline_move_to_target_native.json",
            "endfield.skill-timeline-move-to-target-native-contract.v1", 17,
            "orderedSourceReads",
        ),
        (
            "0x00DA", "Beyond.Gameplay.Core.JumpToTargetAction+Data",
            "skill_timeline_jump_to_target_native.json",
            "endfield.skill-timeline-jump-to-target-native-contract.v1", 11,
            "orderedSourceReads",
        ),
        (
            "0x00A5", "Beyond.Gameplay.Core.EliteBackSwingBeHit+Data",
            "skill_timeline_elite_back_swing_be_hit_native.json",
            "endfield.skill-timeline-elite-back-swing-be-hit-native-contract.v1", 7,
            "orderedSourceReads",
        ),
        (
            "0x00C4", "Beyond.Gameplay.Core.GetTargetBuffBBAdvanced+Data",
            "skill_timeline_get_target_buff_bb_advanced_native.json",
            "endfield.skill-timeline-get-target-buff-bb-advanced-native-contract.v1", 8,
            "orderedSourceReads",
        ),
        (
            "0x007E", "Beyond.Gameplay.Core.Conditions.CheckTargetContains+Data",
            "skill_timeline_check_target_contains_native.json",
            "endfield.skill-timeline-check-target-contains-native-contract.v1", 6,
            "orderedSourceReads",
        ),
        (
            "0x0113", "Beyond.Gameplay.Core.PhysicsCastAction+PhysicsCastActionData",
            "skill_timeline_physics_cast_native.json",
            "endfield.skill-timeline-physics-cast-native-contract.v1", 20,
            "sections.action.orderedSourceReads",
        ),
        (
            "0x00DF", "Beyond.Gameplay.Core.LaunchUpwardAction+Data",
            "skill_timeline_launch_upward_native.json",
            "endfield.skill-timeline-launch-upward-native-contract.v1", 15,
            "orderedSourceReads",
        ),
        (
            "0x002C", "Beyond.Gameplay.Core.ChangeSkillAction+Data",
            "skill_timeline_change_skill_native.json",
            "endfield.skill-timeline-change-skill-native-contract.v1", 14,
            "orderedSourceReads",
        ),
        (
            "0x0057", "Beyond.Gameplay.Core.Conditions.CheckBuffIdInContextAdvanced+Data",
            "skill_timeline_check_buff_id_context_advanced_native.json",
            "endfield.skill-timeline-check-buff-id-context-advanced-native-contract.v1", 8,
            "orderedSourceReads",
        ),
        (
            "0x004D", "Beyond.Gameplay.Core.ComboAction+Data",
            "skill_timeline_combo_action_native.json",
            "endfield.skill-timeline-combo-action-native-contract.v1", 7,
            "orderedSourceReads",
        ),
        (
            "0x0173", "Beyond.Gameplay.Core.StoreCurSkillExecuteFrame+Data",
            "skill_timeline_store_cur_skill_execute_frame_native.json",
            "endfield.skill-timeline-store-cur-skill-execute-frame-native-contract.v1", 6,
            "orderedSourceReads",
        ),
        (
            "0x0165", "Beyond.Gameplay.Core.SkillAIMoveAction+Data",
            "skill_timeline_skill_ai_move_native.json",
            "endfield.skill-timeline-skill-ai-move-native-contract.v1", 16,
            "sections.action.orderedSourceReads",
        ),
        (
            "0x0000", "Beyond.Gameplay.BoneAttachAction+Data",
            "skill_timeline_bone_attach_native.json",
            "endfield.skill-timeline-bone-attach-native-contract.v1", 13,
            "orderedSourceReads",
        ),
        (
            "0x00D0", "Beyond.Gameplay.Core.IgnoreModelIntervalCheck+Data",
            "skill_timeline_ignore_model_interval_check_native.json",
            "endfield.skill-timeline-ignore-model-interval-check-native-contract.v1", 4,
            "orderedSourceReads",
        ),
        (
            "0x00DD", "Beyond.Gameplay.Core.KnockDownAction+Data",
            "skill_timeline_knock_down_native.json",
            "endfield.skill-timeline-knock-down-native-contract.v1", 13,
            "orderedSourceReads",
        ),
        (
            "0x017B", "Beyond.Gameplay.Core.TargetPostProcessorAction+Data",
            "skill_timeline_target_postprocessor_native.json",
            "endfield.skill-timeline-target-postprocessor-native-contract.v1", 11,
            "orderedSourceReads",
        ),
        (
            "0x012D", "Beyond.Gameplay.Core.RemoveAIMarkerAction+Data",
            "skill_timeline_remove_ai_marker_native.json",
            "endfield.skill-timeline-remove-ai-marker-native-contract.v1", 6,
            "orderedSourceReads",
        ),
        (
            "0x018E", "Beyond.Gameplay.Core.TyphoeaArcheryChipDataAction+Data",
            "skill_timeline_typhoea_archery_chip_native.json",
            "endfield.skill-timeline-typhoea-archery-chip-native-contract.v1", 18,
            "orderedSourceReads",
        ),
        (
            "0x0182", "Beyond.Gameplay.Core.TickIntervalActionV2+Data",
            "skill_timeline_tick_interval_v2_native.json",
            "endfield.skill-timeline-tick-interval-v2-native-contract.v1", 10,
            "orderedSourceReads",
        ),
        (
            "0x0048", "Beyond.Gameplay.Core.CheckOriginSkillType+Data",
            "skill_timeline_check_origin_skill_type_native.json",
            "endfield.skill-timeline-check-origin-skill-type-native-contract.v1", 6,
            "orderedSourceReads",
        ),
        (
            "0x013D", "Beyond.Gameplay.Core.SaveMoveAxisAngle+Data",
            "skill_timeline_save_move_axis_angle_native.json",
            "endfield.skill-timeline-save-move-axis-angle-native-contract.v1", 5,
            "orderedSourceReads",
        ),
        (
            "0x00F7", "Beyond.Gameplay.Core.MoveToDirectionAction+Data",
            "skill_timeline_move_to_direction_native.json",
            "endfield.skill-timeline-move-to-direction-native-contract.v1", 19,
            "orderedSourceReads",
        ),
        (
            "0x007A", "Beyond.Gameplay.Core.Conditions.CheckSpellInflictionType+Data",
            "skill_timeline_check_spell_infliction_type_native.json",
            "endfield.skill-timeline-check-spell-infliction-type-native-contract.v1", 6,
            "orderedSourceReads",
        ),
        (
            "0x0063", "Beyond.Gameplay.Core.Conditions.CheckHealTag+Data",
            "skill_timeline_check_heal_tag_native.json",
            "endfield.skill-timeline-check-heal-tag-native-contract.v1", 5,
            "orderedSourceReads",
        ),
        (
            "0x003F", "Beyond.Gameplay.Core.CheckConsumeBuffLayer+Data",
            "skill_timeline_check_consume_buff_layer_native.json",
            "endfield.skill-timeline-check-consume-buff-layer-native-contract.v1", 7,
            "orderedSourceReads",
        ),
        (
            "0x006A", "Beyond.Gameplay.Core.Conditions.CheckObtainAtbType+Data",
            "skill_timeline_check_obtain_atb_type_native.json",
            "endfield.skill-timeline-check-obtain-atb-type-native-contract.v1", 8,
            "orderedSourceReads",
        ),
        (
            "0x0044", "Beyond.Gameplay.Core.CheckGlobalCDTimerAction+Data",
            "skill_timeline_check_global_cd_timer_native.json",
            "endfield.skill-timeline-check-global-cd-timer-native-contract.v1", 6,
            "orderedSourceReads",
        ),
        (
            "0x000A", "Beyond.Gameplay.Core.AddGlobalCDTimer+Data",
            "skill_timeline_add_global_cd_timer_native.json",
            "endfield.skill-timeline-add-global-cd-timer-native-contract.v1", 7,
            "orderedSourceReads",
        ),
    ):
        route = next((row for row in routes if row.get("tag") == tag), None)
        source = dependency_values.get(path, {})
        action = source.get("sections", {}).get("action", {}) if tag in ("0x0121", "0x0113", "0x0165") else source
        if (
            not isinstance(route, dict)
            or route.get("typeName") != type_name
            or route.get("memberCount") != count
            or route.get("sourceContract") != {
                "path": path, "schema": schema, "orderedReadRef": read_ref,
            }
            or source.get("schema") != schema
            or source.get("status") != "exact-current-build"
            or source.get("dispatcher", {}).get("unionTag") != int(tag, 16)
            or action.get("serializedMemberCount") != count
            or len(action.get("orderedSourceReads", ())) != count
        ):
            raise ValueError(f"skillTimelineSharedSequence.contract:source-drift:{tag}")
        if tag == "0x00A0" and (
            len(source.get("nestedContexts", ())) != 1
            or source["nestedContexts"][0].get("typeName")
            != "Beyond.Gameplay.Core.SequenceActionData"
        ):
            raise ValueError("skillTimelineSharedSequence.contract:do-once-child-drift")
        if tag == "0x0057" and source.get("nestedSourceContract") != "buff_57_native.json":
            raise ValueError("skillTimelineSharedSequence.contract:check-buff-child-drift")
        if tag == "0x0173" and source.get("dependencies") != [
            {"path": "buff_ec_native.json", "role": "reviewed finite TargetSettings profile"}
        ]:
            raise ValueError("skillTimelineSharedSequence.contract:store-frame-child-drift")
        if tag == "0x0165" and source.get("dependencies") != [
            {"path": "buff_ec_native.json", "role": "reviewed finite TargetSettings profile"}
        ]:
            raise ValueError("skillTimelineSharedSequence.contract:skill-ai-move-child-drift")
        if tag == "0x0000" and source.get("dependencies") != [
            {"path": "buff_16a_native.json", "role": "reviewed raw12 Vector3 source helper"},
            {"path": "buff_ec_native.json", "role": "reviewed finite TargetSettings source profile"},
        ]:
            raise ValueError("skillTimelineSharedSequence.contract:bone-attach-child-drift")
        if tag == "0x00DD" and source.get("dependencies") != [
            {"path": "buff_ec_native.json", "role": "reviewed finite BlackboardDouble and TargetSettings child profiles"},
            {"path": "buff_b2_native.json", "role": "reviewed finite DirectionSettings child profile"},
        ]:
            raise ValueError("skillTimelineSharedSequence.contract:knock-down-child-drift")
        if tag == "0x017B" and source.get("dependencies") != [
            {"path": "buff_b2_native.json", "role": "reviewed finite nested selector profile"},
            {"path": "buff_ec_native.json", "role": "reviewed finite nested selector profile"},
        ]:
            raise ValueError("skillTimelineSharedSequence.contract:target-postprocessor-child-drift")
        if tag == "0x012D" and source.get("dependencies") != [
            {"path": "buff_fe_native.json", "role": "raw GameplayTag DWORD source helper"},
            {"path": "buff_ec_native.json", "role": "finite TargetSettings child reader"},
        ]:
            raise ValueError("skillTimelineSharedSequence.contract:remove-ai-marker-child-drift")
        if tag == "0x0182" and source.get("dependencies") != [
            {"path": "skill_timeline_tick_interval_native.json", "role": "selected SequenceActionData context and finite sequence reader"},
            {"path": "buff_16b_native.json", "role": "concrete BlackboardInt header-three reader"},
            {"path": "buff_ec_native.json", "role": "concrete BlackboardDouble header-three reader"},
        ]:
            raise ValueError("skillTimelineSharedSequence.contract:tick-interval-v2-child-drift")
        if tag == "0x0048" and (
            source.get("sourceContract") != "buff_48_native.json"
            or source.get("listElementContract") != "buff_78_native.json"
            or source.get("catalogContract") != "levelscript_union_tags.json"
        ):
            raise ValueError("skillTimelineSharedSequence.contract:check-origin-skill-type-child-drift")
        if tag == "0x007A" and (
            source.get("sourceContract") != "buff_7a_native.json"
            or source.get("catalogContract") != "levelscript_union_tags.json"
        ):
            raise ValueError("skillTimelineSharedSequence.contract:check-spell-infliction-child-drift")
        if tag == "0x0063" and (
            source.get("sourceContract") != "buff_63_native.json"
            or source.get("queryProfileContract") != "buff_b4_native.json"
            or source.get("catalogContract") != "levelscript_union_tags.json"
        ):
            raise ValueError("skillTimelineSharedSequence.contract:check-heal-tag-child-drift")
        if tag == "0x003F" and (
            source.get("sourceContract") != "buff_3f_native.json"
            or source.get("scalarPayloadContract") != "buff_16b_native.json"
            or source.get("catalogContract") != "levelscript_union_tags.json"
        ):
            raise ValueError("skillTimelineSharedSequence.contract:check-consume-buff-layer-child-drift")
        if tag == "0x006A" and (
            source.get("sourceContract") != "buff_6a_native.json"
            or source.get("catalogContract") != "levelscript_union_tags.json"
        ):
            raise ValueError("skillTimelineSharedSequence.contract:check-obtain-atb-type-child-drift")
        if tag == "0x0044" and (
            source.get("sourceContract") != "buff_44_native.json"
            or source.get("targetProfileContract") != "buff_ec_native.json"
            or source.get("catalogContract") != "levelscript_union_tags.json"
        ):
            raise ValueError("skillTimelineSharedSequence.contract:check-global-cd-timer-child-drift")
        if tag == "0x000A" and (
            source.get("sourceContract") != "buff_0a_native.json"
            or source.get("nestedProfileContract") != "buff_ec_native.json"
            or source.get("catalogContract") != "levelscript_union_tags.json"
        ):
            raise ValueError("skillTimelineSharedSequence.contract:add-global-cd-timer-child-drift")
        if tag == "0x00F7" and source.get("dependencies") != [
            {"path": "buff_1f_native.json", "role": "reviewed LayerMask raw4 source shape"},
            {"path": "buff_ec_native.json", "role": "reviewed TargetSettings finite profile"},
            {"path": "buff_98_native.json", "role": "reviewed AnimationCurve finite profile"},
        ]:
            raise ValueError("skillTimelineSharedSequence.contract:move-to-direction-child-drift")
    for tag, type_name, source_path, member_count, read_order in (
        (
            "0x007B", "Beyond.Gameplay.Core.Conditions.CheckSuperArmor+Data",
            "buff_7b_native.json", 7,
            ("byte", "scalar32", "scalar32", "scalar32", "target-profile", "scalar32", "scalar-payload"),
        ),
        (
            "0x0080", "Beyond.Gameplay.Core.Conditions.CheckTargetsEqual+Data",
            "buff_80_native.json", 6,
            ("byte", "scalar32", "scalar32", "scalar32", "target-profile", "target-profile"),
        ),
        (
            "0x00A7", "Beyond.Gameplay.Core.EnablePartsAction+Data",
            "buff_a7_native.json", 11,
            ("byte", "scalar32", "scalar32", "scalar32", "byte", "byte-profile",
             "scalar-pair-flags-profile", "query-profile", "byte-profile",
             "scalar-pair-flags-profile", "byte"),
        ),
        (
            "0x0036", "Beyond.Gameplay.Core.CharWeaponAnimationAction+CharWeaponAnimationActionData",
            "buff_36_native.json", 12,
            ("byte", "scalar32", "scalar32", "scalar32", "byte", "byte",
             "animator-param-profile", "animator-param-profile", "raw4", "byte",
             "animator-param-profile", "scalar32"),
        ),
        (
            "0x0178", "Beyond.Gameplay.Core.SwitchModeAction+Data",
            "buff_178_native.json", 8,
            ("byte", "scalar32", "scalar32", "scalar32", "byte", "byte",
             "byte-payload", "byte"),
        ),
        (
            "0x004C", "Beyond.Gameplay.Core.ClearProjectileAction+Data",
            "buff_4c_native.json", 12,
            ("byte", "scalar32", "scalar32", "scalar32", "scalar-payload-profile",
             "target-profile", "byte", "byte", "scalar32", "byte",
             "nullable-byte-payload-list", "target-profile"),
        ),
    ):
        route = next((row for row in routes if row.get("tag") == tag), None)
        source = dependency_values.get(source_path, {})
        if (
            not isinstance(route, dict)
            or route.get("typeName") != type_name
            or route.get("memberCount") != member_count
            or route.get("sourceContract") != {
                "path": source_path, "schemaVersion": 1,
                "orderedReadRef": f"anonymousReadOrder.member{member_count}",
            }
            or source.get("schemaVersion") != 1
            or tuple(source.get("anonymousReadOrder", {}).get(f"member{member_count}", ()))
            != read_order
            or not source.get("methods")
            or not source.get("codeWindows")
        ):
            raise ValueError(f"skillTimelineSharedSequence.contract:reused-buff-source-drift:{tag}")
    camera_state_route = next(
        (row for row in routes if row.get("tag") == "0x019E"), None
    )
    camera_state_contract = dependency_values.get("buff_19e_native.json", {})
    if (
        not isinstance(camera_state_route, dict)
        or camera_state_route.get("typeName")
        != "Beyond.Gameplay.View.AddCameraControlStateAction+AddCameraControlStateActionData"
        or camera_state_route.get("memberCount") != 23
        or camera_state_route.get("sourceContract") != {
            "path": "buff_19e_native.json", "schemaVersion": 1,
            "orderedReadRef": "anonymousReadOrder.member23",
        }
        or camera_state_contract.get("schemaVersion") != 1
        or not isinstance(camera_state_contract.get("anonymousReadOrder", {}).get("member23"), list)
        or len(camera_state_contract["anonymousReadOrder"]["member23"]) != 23
    ):
        raise ValueError("skillTimelineSharedSequence.contract:camera-control-state-source-drift")
    warning_route = next((row for row in routes if row.get("tag") == "0x00AA"), None)
    warning_contract = dependency_values.get("skill_timeline_enemy_warning_native.json", {})
    if (
        not isinstance(warning_route, dict)
        or warning_route.get("typeName")
        != "Beyond.Gameplay.Core.EnemyWarningAction+EnemyWarningActionData"
        or warning_route.get("memberCount") != 18
        or warning_route.get("sourceContract") != {
            "path": "skill_timeline_enemy_warning_native.json",
            "schema": "endfield.skill-timeline-enemy-warning-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or warning_contract.get("schema")
        != "endfield.skill-timeline-enemy-warning-native-contract.v1"
        or warning_contract.get("status") != "exact-current-build"
        or warning_contract.get("dispatcher", {}).get("unionTag") != 0x00AA
        or not isinstance(warning_contract.get("orderedSourceReads"), list)
        or len(warning_contract["orderedSourceReads"]) != 18
    ):
        raise ValueError("skillTimelineSharedSequence.contract:enemy-warning-source-drift")
    angry_route = next((row for row in routes if row.get("tag") == "0x00B3"), None)
    angry_contract = dependency_values.get("skill_timeline_finish_angry_native.json", {})
    if (
        not isinstance(angry_route, dict)
        or angry_route.get("typeName") != "Beyond.Gameplay.Core.FinishAngryOnEnd+Data"
        or angry_route.get("memberCount") != 4
        or angry_route.get("sourceContract") != {
            "path": "skill_timeline_finish_angry_native.json",
            "schema": "endfield.skill-timeline-finish-angry-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or angry_contract.get("schema")
        != "endfield.skill-timeline-finish-angry-native-contract.v1"
        or angry_contract.get("status") != "exact-current-build"
        or angry_contract.get("dispatcher", {}).get("unionTag") != 0x00B3
        or not isinstance(angry_contract.get("orderedSourceReads"), list)
        or len(angry_contract["orderedSourceReads"]) != 4
    ):
        raise ValueError("skillTimelineSharedSequence.contract:finish-angry-source-drift")
    return value


def validate_current_native_contract() -> dict[str, Any]:
    contract = _contract()
    frontier_rows, frontier_audit = buff_frontiers_native.load_rows("frontier9")
    if frontier_audit.get("status") != "validated" or 0x0082 not in frontier_rows:
        raise ValueError(
            f"skillTimelineSharedSequence.native:two-direction-frontier:{frontier_audit.get('status')}"
        )
    teleport_validation = validate_teleport_pos_select_native_contract()
    snap_validation = validate_snap_to_target_with_range_native_contract()
    allow_validation = validate_allow_next_skill_native_contract()
    fixed_four_validation = validate_fixed_four_native_contract()
    camera_state_validation = validate_add_camera_control_state_native_contract()
    save_angle_validation = validate_save_two_direction_angle_native_contract()
    push_validation = validate_push_back_native_contract()
    navmesh_validation = validate_add_dynamic_navmesh_obstacle_native_contract()
    tick_validation = validate_tick_interval_native_contract()
    camera_rotate_validation = validate_camera_rotate_native_contract()
    gain_breaking_attack_validation = validate_gain_breaking_attack_atb_native_contract()
    override_camera_follow_validation = validate_override_camera_follow_native_contract()
    curve_evaluate_float_validation = validate_curve_evaluate_float_native_contract()
    command_to_characters_validation = validate_command_to_characters_native_contract()
    receive_move_input_validation = validate_receive_move_input_native_contract()
    check_combo_skill_camera_alpha_validation = validate_check_combo_skill_camera_alpha_native_contract()
    temporary_unlock_validation = validate_temporary_unlock_native_contract()
    check_has_move_input_validation = validate_check_has_move_input_native_contract()
    togglable_validation = validate_togglable_native_contract()
    check_squad_in_fight_validation = validate_check_squad_in_fight_native_contract()
    break_interactive_validation = validate_break_interactive_native_contract()
    inherit_buff_validation = validate_inherit_buff_native_contract()
    animated_camera_validation = validate_animated_camera_native_contract()
    hide_ui_validation = validate_hide_ui_native_contract()
    move_to_location_validation = validate_move_to_location_native_contract()
    ultimate_time_validation = validate_ultimate_time_native_contract()
    ultimate_show_validation = validate_ultimate_show_native_contract()
    channeling_casting_validation = validate_channeling_casting_native_contract()
    modify_weapon_mount_point_validation = validate_modify_weapon_mount_point_native_contract()
    raycast_effect_validation = validate_raycast_effect_native_contract()
    pick_target_validation = validate_pick_target_native_contract()
    do_once_validation = validate_do_once_native_contract()
    check_skill_camera_motion_free_validation = validate_check_skill_camera_motion_free_native_contract()
    check_target_angle_validation = validate_check_target_angle_native_contract()
    move_to_target_validation = validate_move_to_target_native_contract()
    jump_to_target_validation = validate_jump_to_target_native_contract()
    elite_back_swing_be_hit_validation = validate_elite_back_swing_be_hit_native_contract()
    get_target_buff_bb_advanced_validation = validate_get_target_buff_bb_advanced_native_contract()
    check_target_contains_validation = validate_check_target_contains_native_contract()
    physics_cast_validation = validate_physics_cast_native_contract()
    launch_upward_validation = validate_launch_upward_native_contract()
    change_skill_validation = validate_change_skill_native_contract()
    check_buff_id_context_advanced_validation = validate_check_buff_id_context_advanced_native_contract()
    combo_action_validation = validate_combo_action_native_contract()
    store_cur_skill_execute_frame_validation = validate_store_cur_skill_execute_frame_native_contract()
    skill_ai_move_validation = validate_skill_ai_move_native_contract()
    bone_attach_validation = validate_bone_attach_native_contract()
    ignore_model_interval_check_validation = validate_ignore_model_interval_check_native_contract()
    knock_down_validation = validate_knock_down_native_contract()
    target_postprocessor_validation = validate_target_postprocessor_native_contract()
    remove_ai_marker_validation = validate_remove_ai_marker_native_contract()
    typhoea_archery_chip_validation = validate_typhoea_archery_chip_native_contract()
    tick_interval_v2_validation = validate_tick_interval_v2_native_contract()
    check_origin_skill_type_validation = validate_check_origin_skill_type_native_contract()
    save_move_axis_angle_validation = validate_save_move_axis_angle_native_contract()
    move_to_direction_validation = validate_move_to_direction_native_contract()
    crush_validation = validate_crush_native_contract()
    check_spell_infliction_type_validation = validate_check_spell_infliction_type_native_contract()
    check_heal_tag_validation = validate_check_heal_tag_native_contract()
    check_consume_buff_layer_validation = validate_check_consume_buff_layer_native_contract()
    check_obtain_atb_type_validation = validate_check_obtain_atb_type_native_contract()
    check_global_cd_timer_validation = validate_check_global_cd_timer_native_contract()
    add_global_cd_timer_validation = validate_add_global_cd_timer_native_contract()
    play_animation_step_shared_validation = validate_play_animation_step_shared_native_contract()
    blow_off_enemy_validation = validate_blow_off_enemy_native_contract()
    check_physical_infliction_type_validation = validate_check_physical_infliction_type_native_contract()
    create_buff_attaching_skill_validation = validate_create_buff_attaching_skill_native_contract()
    inherit_ccs_validation = validate_inherit_ccs_native_contract()
    channeling_damage_validation = validate_channeling_damage_native_contract()
    check_hit_collider_options_validation = validate_check_hit_collider_options_native_contract()
    compare_deck_attr_validation = validate_compare_deck_attr_native_contract()
    check_buff_stack_num_by_tag_validation = validate_check_buff_stack_num_by_tag_native_contract()
    force_spell_status_validation = validate_force_spell_status_native_contract()
    modify_camera_lock_point_validation = validate_modify_camera_lock_point_native_contract()
    apply_armor_validation = validate_apply_armor_native_contract()
    blight_miasma_tolerance_zero_validation = validate_blight_miasma_tolerance_zero_native_contract()
    block_move_interrupt_skill_validation = validate_block_move_interrupt_skill_native_contract()
    channeling_v2_validation = validate_channeling_v2_native_contract()
    char_follow_validation = validate_char_follow_native_contract()
    finish_buff_by_tag_validation = validate_finish_buff_by_tag_native_contract()
    extend_buff_validation = validate_extend_buff_native_contract()
    get_patrol_teleport_pos_validation = validate_get_patrol_teleport_pos_native_contract()
    override_born_position_validation = validate_override_born_position_native_contract()
    refresh_head_bar_show_hide_validation = validate_refresh_head_bar_show_hide_native_contract()
    force_hide_head_bar_validation = validate_force_hide_head_bar_native_contract()
    additional_battle_shape_validation = validate_additional_battle_shape_native_contract()
    throw_pickup_item_validation = validate_throw_pickup_item_native_contract()
    throw_pickup_item_start_validation = validate_throw_pickup_item_start_native_contract()
    take_down_validation = validate_take_down_native_contract()
    obtain_usp_normal_validation = validate_obtain_usp_normal_native_contract()
    typhoea_selected_finder_validation = validate_typhoea_selected_finder_native_contract()
    in_screen_validator_validation = validate_in_screen_validator_native_contract()
    nested_interactive_key_validator_validation = validate_nested_interactive_key_validator_native_contract()
    motion_validation = validate_custom_root_motion_native_contract()
    warning_validation = validate_enemy_warning_native_contract()
    angry_validation = validate_finish_angry_native_contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["gameassemblySha256"], expected["globalMetadataSha256"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(
            f"skillTimelineSharedSequence.native:{gate.status}:{gate.detail}"
        )
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unityplayer.is_file():
        raise ValueError("skillTimelineSharedSequence.native:UnityPlayer.dll:missing")
    if hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected["unityplayerSha256"]:
        raise ValueError("skillTimelineSharedSequence.native:UnityPlayer.dll:sha256-mismatch")
    from scripts.game_data.memorypack.derived_schema import resolve_routes

    derived_routes, resolver, derived_audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata
    )
    building_route = derived_routes.get(FAC_BUILDING_PLAY_ANIMATION_TAG, {})
    building_definition = building_route.get("wrapperTypeDefinition")
    building_plan = (
        resolver.plans.get(building_definition)
        if resolver is not None and building_definition is not None else None
    )
    if (
        derived_audit.get("status") != "validated"
        or building_route.get("status") != "determined"
        or building_route.get("wrapperName")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_FacBuildingPlayAnimationAction_DataForMemoryPack"
        or building_route.get("evidenceTier") != "direct"
        or not isinstance(building_plan, tuple)
        or tuple((member.kind, member.width, member.scalar) for member in building_plan)
        != FAC_BUILDING_PLAY_ANIMATION_PLAN
    ):
        raise ValueError("skillTimelineSharedSequence.native:fac-building-plan-drift")
    for tag, wrapper in (
        (0x007B, "Beyond.MemoryPack.Beyond_Gameplay_Core_Conditions_CheckSuperArmor_DataForMemoryPack"),
        (0x0080, "Beyond.MemoryPack.Beyond_Gameplay_Core_Conditions_CheckTargetsEqual_DataForMemoryPack"),
        (0x00A7, "Beyond.MemoryPack.Beyond_Gameplay_Core_EnablePartsAction_DataForMemoryPack"),
        (0x0036, "Beyond.MemoryPack.Beyond_Gameplay_Core_CharWeaponAnimationAction_CharWeaponAnimationActionDataForMemoryPack"),
        (0x0178, "Beyond.MemoryPack.Beyond_Gameplay_Core_SwitchModeAction_DataForMemoryPack"),
        (0x004C, "Beyond.MemoryPack.Beyond_Gameplay_Core_ClearProjectileAction_DataForMemoryPack"),
    ):
        selected = derived_routes.get(tag, {})
        if selected.get("status") not in ("determined", "open") or selected.get("wrapperName") != wrapper:
            raise ValueError(f"skillTimelineSharedSequence.native:reused-buff-route-drift:{tag:#x}")
    from scripts.game_data.il2cpp.native_image import open_native_image

    image = open_native_image(gate.gameassembly, gate.metadata)
    source_window_dependencies = sorted({
        ref["path"]
        for route in contract["allowedReachedRoutes"]
        if isinstance(ref := route.get("sourceContract"), dict)
        and isinstance(ref.get("path"), str)
        and ref["path"].startswith("buff_")
        and ref["path"].endswith("_native.json")
    })
    for name in source_window_dependencies:
        path = (CONTRACT_PATH.parent / name).resolve()
        if not path.is_relative_to(CONTRACT_PATH.parent.resolve()):
            raise ValueError(f"skillTimelineSharedSequence.native:source-path:{name}")
        source = json.loads(path.read_bytes())
        for method in source["methods"]:
            image.validate_method_row(method, label=f"{LABEL}.{name}")
        image.check_windows(source["codeWindows"], label=f"{LABEL}.{name}")
    return {
        "status": "validated",
        "nativeInputs": expected,
        "contractSha256": hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest().upper(),
        "dependencyCount": len(contract["dependencies"]),
        "facBuildingPlanValidation": "validated",
        "sourceWindowValidation": source_window_dependencies,
        "twoDirectionFrontierValidation": frontier_audit["status"],
        "teleportPosSelectNativeValidation": teleport_validation,
        "snapToTargetWithRangeNativeValidation": snap_validation,
        "allowNextSkillNativeValidation": allow_validation,
        "fixedFourNativeValidation": fixed_four_validation,
        "addCameraControlStateNativeValidation": camera_state_validation,
        "saveTwoDirectionAngleNativeValidation": save_angle_validation,
        "pushBackNativeValidation": push_validation,
        "addDynamicNavmeshObstacleNativeValidation": navmesh_validation,
        "tickIntervalNativeValidation": tick_validation,
        "cameraRotateNativeValidation": camera_rotate_validation,
        "gainBreakingAttackAtbNativeValidation": gain_breaking_attack_validation,
        "overrideCameraFollowNativeValidation": override_camera_follow_validation,
        "curveEvaluateFloatNativeValidation": curve_evaluate_float_validation,
        "commandToCharactersNativeValidation": command_to_characters_validation,
        "receiveMoveInputNativeValidation": receive_move_input_validation,
        "checkComboSkillCameraAlphaNativeValidation": check_combo_skill_camera_alpha_validation,
        "temporaryUnlockNativeValidation": temporary_unlock_validation,
        "checkHasMoveInputNativeValidation": check_has_move_input_validation,
        "togglableNativeValidation": togglable_validation,
        "checkSquadInFightNativeValidation": check_squad_in_fight_validation,
        "breakInteractiveNativeValidation": break_interactive_validation,
        "inheritBuffNativeValidation": inherit_buff_validation,
        "animatedCameraNativeValidation": animated_camera_validation,
        "hideUiNativeValidation": hide_ui_validation,
        "moveToLocationNativeValidation": move_to_location_validation,
        "ultimateTimeNativeValidation": ultimate_time_validation,
        "ultimateShowNativeValidation": ultimate_show_validation,
        "channelingCastingNativeValidation": channeling_casting_validation,
        "modifyWeaponMountPointNativeValidation": modify_weapon_mount_point_validation,
        "raycastEffectNativeValidation": raycast_effect_validation,
        "pickTargetNativeValidation": pick_target_validation,
        "doOnceNativeValidation": do_once_validation,
        "checkSkillCameraMotionFreeNativeValidation": check_skill_camera_motion_free_validation,
        "checkTargetAngleNativeValidation": check_target_angle_validation,
        "moveToTargetNativeValidation": move_to_target_validation,
        "jumpToTargetNativeValidation": jump_to_target_validation,
        "eliteBackSwingBeHitNativeValidation": elite_back_swing_be_hit_validation,
        "getTargetBuffBBAdvancedNativeValidation": get_target_buff_bb_advanced_validation,
        "checkTargetContainsNativeValidation": check_target_contains_validation,
        "physicsCastNativeValidation": physics_cast_validation,
        "launchUpwardNativeValidation": launch_upward_validation,
        "changeSkillNativeValidation": change_skill_validation,
        "checkBuffIdContextAdvancedNativeValidation": check_buff_id_context_advanced_validation,
        "comboActionNativeValidation": combo_action_validation,
        "storeCurSkillExecuteFrameNativeValidation": store_cur_skill_execute_frame_validation,
        "skillAiMoveNativeValidation": skill_ai_move_validation,
        "boneAttachNativeValidation": bone_attach_validation,
        "ignoreModelIntervalCheckNativeValidation": ignore_model_interval_check_validation,
        "knockDownNativeValidation": knock_down_validation,
        "targetPostprocessorNativeValidation": target_postprocessor_validation,
        "removeAiMarkerNativeValidation": remove_ai_marker_validation,
        "typhoeaArcheryChipNativeValidation": typhoea_archery_chip_validation,
        "tickIntervalV2NativeValidation": tick_interval_v2_validation,
        "checkOriginSkillTypeNativeValidation": check_origin_skill_type_validation,
        "saveMoveAxisAngleNativeValidation": save_move_axis_angle_validation,
        "moveToDirectionNativeValidation": move_to_direction_validation,
        "crushNativeValidation": crush_validation,
        "checkSpellInflictionTypeNativeValidation": check_spell_infliction_type_validation,
        "checkHealTagNativeValidation": check_heal_tag_validation,
        "checkConsumeBuffLayerNativeValidation": check_consume_buff_layer_validation,
        "checkObtainAtbTypeNativeValidation": check_obtain_atb_type_validation,
        "checkGlobalCdTimerNativeValidation": check_global_cd_timer_validation,
        "addGlobalCdTimerNativeValidation": add_global_cd_timer_validation,
        "playAnimationStepSharedNativeValidation": play_animation_step_shared_validation,
        "blowOffEnemyNativeValidation": blow_off_enemy_validation,
        "checkPhysicalInflictionTypeNativeValidation": check_physical_infliction_type_validation,
        "createBuffAttachingSkillNativeValidation": create_buff_attaching_skill_validation,
        "inheritCcsNativeValidation": inherit_ccs_validation,
        "channelingDamageNativeValidation": channeling_damage_validation,
        "checkHitColliderOptionsNativeValidation": check_hit_collider_options_validation,
        "compareDeckAttrNativeValidation": compare_deck_attr_validation,
        "checkBuffStackNumByTagNativeValidation": check_buff_stack_num_by_tag_validation,
        "forceSpellStatusNativeValidation": force_spell_status_validation,
        "modifyCameraLockPointNativeValidation": modify_camera_lock_point_validation,
        "applyArmorNativeValidation": apply_armor_validation,
        "blightMiasmaToleranceZeroNativeValidation": blight_miasma_tolerance_zero_validation,
        "blockMoveInterruptSkillNativeValidation": block_move_interrupt_skill_validation,
        "channelingV2NativeValidation": channeling_v2_validation,
        "charFollowNativeValidation": char_follow_validation,
        "finishBuffByTagNativeValidation": finish_buff_by_tag_validation,
        "extendBuffNativeValidation": extend_buff_validation,
        "getPatrolTeleportPosNativeValidation": get_patrol_teleport_pos_validation,
        "overrideBornPositionNativeValidation": override_born_position_validation,
        "refreshHeadBarShowHideNativeValidation": refresh_head_bar_show_hide_validation,
        "forceHideHeadBarNativeValidation": force_hide_head_bar_validation,
        "additionalBattleShapeNativeValidation": additional_battle_shape_validation,
        "throwPickupItemNativeValidation": throw_pickup_item_validation,
        "throwPickupItemStartNativeValidation": throw_pickup_item_start_validation,
        "takeDownNativeValidation": take_down_validation,
        "obtainUspNormalNativeValidation": obtain_usp_normal_validation,
        "typhoeaSelectedFinderNativeValidation": typhoea_selected_finder_validation,
        "inScreenValidatorNativeValidation": in_screen_validator_validation,
        "nestedInteractiveKeyValidatorNativeValidation": nested_interactive_key_validator_validation,
        "customRootMotionNativeValidation": motion_validation,
        "enemyWarningNativeValidation": warning_validation,
        "finishAngryNativeValidation": angry_validation,
    }


def _tag_at(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    if offset >= limit:
        raise ValueError("skillTimelineSharedSequence.unionTag:truncated")
    lead = data[offset]
    if lead == 0xFA:
        if offset + 3 > limit:
            raise ValueError("skillTimelineSharedSequence.unionTag:truncated-extended")
        return struct.unpack_from("<H", data, offset + 1)[0], 3
    return lead, 1


def _is_null_action_record(data: bytes, record: dict[str, Any]) -> bool:
    """Only one-byte FF is null; FA FF 00 is physical action tag 0x00FF."""
    return record["tag"] == 0xFF and data[record["start"]] == 0xFF


def _route_table() -> dict[int, dict[str, Any]]:
    return {
        int(row["tag"], 16): row for row in _contract()["allowedReachedRoutes"]
    }


def _named_ranges(reader: Reader) -> list[dict[str, Any]]:
    ranges = [
        {"name": "skillData.memberCount", "start": 0, "end": 1, "kind": "SkillData.member-count"},
        {"name": "skillData.actionGroupData.memberCount", "start": 1, "end": 2, "kind": "ActionGroupData.member-count"},
        {"name": "skillData.actionGroupData.passiveEventActions.count", "start": 2, "end": 6, "kind": "nullable-list-count-i32"},
        {"name": "skillData.actionGroupData.timelineActions.count", "start": 6, "end": 10, "kind": "nullable-list-count-i32"},
    ]
    for index, span in enumerate(reader.ranges):
        ranges.append({
            "name": f"timeline.sharedSequence.range[{index}]",
            "start": span["start"],
            "end": span["end"],
            "kind": span["kind"],
        })
    cursor = 0
    for span in ranges:
        if span["start"] != cursor or span["end"] <= span["start"]:
            raise ValueError(
                f"skillTimelineSharedSequence.ranges:not-contiguous:{cursor}:{span}"
            )
        cursor = span["end"]
    if cursor != reader.pos:
        raise ValueError(
            f"skillTimelineSharedSequence.ranges:end={cursor}:cursor={reader.pos}"
        )
    return ranges


def decode_first_timeline_shared_sequence(
    data: bytes,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Close one first TimelineActionData using only contracted action routes."""
    contract = _contract()
    hard_limit = len(data) if limit is None else limit
    if hard_limit > len(data) or hard_limit < 22:
        raise ValueError("skillTimelineSharedSequence.limit")
    if data[0] != 48 or data[1] != 2:
        raise ValueError("skillTimelineSharedSequence.envelope")
    passive_count = struct.unpack_from("<i", data, 2)[0]
    timeline_count = struct.unpack_from("<i", data, 6)[0]
    if passive_count != 0 or timeline_count <= 0:
        raise ValueError("skillTimelineSharedSequence.actionGroup")
    if data[10] != 4 or data[15] != 3:
        raise ValueError("skillTimelineSharedSequence.timelineHeader")
    action_count = struct.unpack_from("<i", data, 16)[0]
    if action_count <= 0:
        raise ValueError("skillTimelineSharedSequence.actionCount")
    first_tag, _ = _tag_at(data, 20, hard_limit)
    roots = {int(tag, 16) for tag in contract["rootTags"]}
    create_buff_root = int(contract["createBuffMultiActionRoot"], 16)
    if first_tag == create_buff_root:
        if action_count <= 1:
            raise ValueError("skillTimelineSharedSequence.createBuff:requires-multiple-actions")
    elif first_tag not in roots:
        raise ValueError(f"skillTimelineSharedSequence.firstTag=0x{first_tag:04X}")

    reader = SharedSequenceReader(data, "SkillData.SharedTimelineSequence", hard_limit)
    reader.pos = 10
    timeline_start = reader.pos
    reader.header(4)
    reader.take(4, "TimelineActionData.endFrame.int32")
    reader.sequence()
    sequence_end = reader.pos
    reader.take(4, "TimelineActionData.startFrame.int32")
    reader.header(4)
    reader.take(1, "ForceSyncAnimData.forceSync.bool-byte")
    reader.byte_payload()
    reader.take(4, "ForceSyncAnimData.playbackSpeed.float32-bits")
    reader.take(4, "ForceSyncAnimData.targetFrame.int32")

    route_table = _route_table()
    actions = []
    for record in reader.records:
        if record.get("kind") != "union":
            continue
        tag = record["tag"]
        if _is_null_action_record(data, record):
            actions.append({
                "tag": tag,
                "tagHex": "0x00FF",
                "typeName": "null",
                "memberCount": None,
                "start": record["start"],
                "end": record["end"],
                "structurallyExact": True,
            })
            continue
        route = route_table.get(tag)
        if route is None:
            raise ValueError(f"skillTimelineSharedSequence.route=0x{tag:04X}:not-contracted")
        _tag, width = _tag_at(data, record["start"], record["end"])
        if _tag != tag:
            raise ValueError("skillTimelineSharedSequence.route:tag-drift")
        member_offset = record["start"] + width
        if member_offset >= record["end"] or data[member_offset] != route["memberCount"]:
            raise ValueError(
                f"skillTimelineSharedSequence.route=0x{tag:04X}:member-count"
            )
        actions.append({
            "tag": tag,
            "tagHex": f"0x{tag:04X}",
            "typeName": route["typeName"],
            "memberCount": route["memberCount"],
            "start": record["start"],
            "end": record["end"],
            "structurallyExact": True,
        })
    top_level_actions = [row for row in actions if row["start"] < sequence_end]
    if len(top_level_actions) < action_count:
        raise ValueError(
            f"skillTimelineSharedSequence.topLevelActions={len(top_level_actions)} expected>={action_count}"
        )
    # Nested sequences can contribute union records. The root sequence's first
    # action count is independently retained, while all reached unions must be
    # contracted and exact.
    return {
        "status": "exact-first-timeline-shared-sequence-record",
        "parserCursor": reader.pos,
        "hardLimit": hard_limit,
        "timelineActionsCount": timeline_count,
        "firstSequenceActionDataCount": action_count,
        "firstActionTag": first_tag,
        "firstTimelineAction": {
            "start": timeline_start,
            "end": reader.pos,
            "sequenceEnd": sequence_end,
            "actionData": actions,
            "wholeRecordExact": True,
        },
        "namedRanges": _named_ranges(reader),
        "wholeFirstTimelineActionExact": True,
        "wholeTimelineListExact": timeline_count == 1,
        "wholeActionGroupDataExact": timeline_count == 1,
        "wholeSkillDataExact": False,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_timeline_shared_sequence(
    data: bytes,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Close every supported timeline record, retaining the exact first prefix on a stop."""
    first = decode_first_timeline_shared_sequence(data, limit=limit)
    timeline_count = first["timelineActionsCount"]
    if timeline_count == 1:
        return first

    hard_limit = first["hardLimit"]
    reader = SharedSequenceReader(data, "SkillData.SharedTimelineSequence", hard_limit)
    reader.pos = first["parserCursor"]
    routes = _route_table()
    later_records = []
    try:
        for index in range(1, timeline_count):
            start = reader.pos
            record_start = len(reader.records)
            reader.header(4)
            reader.take(4, "TimelineActionData.endFrame.int32")
            if reader.peek() != 3 or reader.pos + 5 > hard_limit:
                raise ValueError(f"skillTimelineSharedSequence.timeline[{index}]:sequence-header")
            action_count = struct.unpack_from("<i", data, reader.pos + 1)[0]
            reader.sequence()
            sequence_end = reader.pos
            reader.take(4, "TimelineActionData.startFrame.int32")
            reader.header(4)
            reader.take(1, "ForceSyncAnimData.forceSync.bool-byte")
            reader.byte_payload()
            reader.take(4, "ForceSyncAnimData.playbackSpeed.float32-bits")
            reader.take(4, "ForceSyncAnimData.targetFrame.int32")

            actions = []
            for record in reader.records[record_start:]:
                if record.get("kind") != "union":
                    continue
                tag = record["tag"]
                if _is_null_action_record(data, record):
                    actions.append({
                        "tag": tag, "tagHex": "0x00FF", "typeName": "null",
                        "memberCount": None, "start": record["start"],
                        "end": record["end"], "structurallyExact": True,
                    })
                    continue
                route = routes.get(tag)
                if route is None:
                    raise ValueError(
                        f"skillTimelineSharedSequence.timeline[{index}]:route=0x{tag:04X}:not-contracted"
                    )
                actual_tag, width = _tag_at(data, record["start"], record["end"])
                member_offset = record["start"] + width
                if (
                    actual_tag != tag
                    or member_offset >= record["end"]
                    or data[member_offset] != route["memberCount"]
                ):
                    raise ValueError(
                        f"skillTimelineSharedSequence.timeline[{index}]:route=0x{tag:04X}:member-count"
                    )
                actions.append({
                    "tag": tag, "tagHex": f"0x{tag:04X}",
                    "typeName": route["typeName"],
                    "memberCount": route["memberCount"],
                    "start": record["start"], "end": record["end"],
                    "structurallyExact": True,
                })
            if action_count < 0 or sum(
                action["start"] < sequence_end for action in actions
            ) < action_count:
                raise ValueError(
                    f"skillTimelineSharedSequence.timeline[{index}]:action-count"
                )
            later_records.append({
                "index": index, "start": start, "end": reader.pos,
                "sequenceEnd": sequence_end,
                "sequenceActionDataCount": action_count,
                "actionData": actions, "wholeRecordExact": True,
            })
    except ValueError as exc:
        return {**first, "laterStopReason": str(exc)}

    ranges = list(first["namedRanges"])
    cursor = first["parserCursor"]
    for index, span in enumerate(reader.ranges):
        if span["start"] != cursor or span["end"] <= cursor:
            raise ValueError(
                f"skillTimelineSharedSequence.laterRanges:not-contiguous:{cursor}:{span}"
            )
        ranges.append({
            "name": f"timeline.sharedSequence.laterRange[{index}]",
            "start": span["start"], "end": span["end"], "kind": span["kind"],
        })
        cursor = span["end"]
    if cursor != reader.pos:
        raise ValueError("skillTimelineSharedSequence.laterRanges:end-drift")
    return {
        **first,
        "parserCursor": reader.pos,
        "laterTimelineActions": later_records,
        "namedRanges": ranges,
        "wholeTimelineListExact": True,
        "wholeActionGroupDataExact": True,
    }


def decode_passive_shared_sequence(
    data: bytes,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Close a positive passive map list followed by an empty timeline list.

    The map and nested sequences use the selected AbilityActionMap grammar.
    Every reached action must also have a reviewed route and matching payload
    header before the enclosing ActionGroupData is marked exact.
    """
    contract = _contract()
    hard_limit = len(data) if limit is None else limit
    if hard_limit > len(data) or hard_limit < 10:
        raise ValueError("skillPassiveSharedSequence.limit")
    if data[0] != 48 or data[1] != 2:
        raise ValueError("skillPassiveSharedSequence.envelope")
    passive_count = struct.unpack_from("<i", data, 2)[0]
    if passive_count <= 0:
        raise ValueError("skillPassiveSharedSequence.passive-count")
    reader = SharedSequenceReader(data, "SkillData.SharedPassiveSequence", hard_limit)
    reader.pos = 2
    reader.ability_action_map_collection_profile(0)
    timeline_count_start = reader.pos
    if reader.count(1, nullable=True) != 0:
        raise ValueError("skillPassiveSharedSequence.nonempty-timeline-list")
    routes = _route_table()
    actions = []
    for record in reader.records:
        if record.get("kind") != "union":
            continue
        tag = record["tag"]
        if _is_null_action_record(data, record):
            actions.append({
                "tag": tag, "tagHex": "0x00FF", "typeName": "null",
                "memberCount": None, "start": record["start"], "end": record["end"],
                "structurallyExact": True,
            })
            continue
        route = routes.get(tag)
        if route is None:
            raise ValueError(f"skillPassiveSharedSequence.route=0x{tag:04X}:not-contracted")
        actual_tag, width = _tag_at(data, record["start"], record["end"])
        member_offset = record["start"] + width
        if (
            actual_tag != tag or member_offset >= record["end"]
            or data[member_offset] != route["memberCount"]
        ):
            raise ValueError(f"skillPassiveSharedSequence.route=0x{tag:04X}:member-count")
        actions.append({
            "tag": tag, "tagHex": f"0x{tag:04X}", "typeName": route["typeName"],
            "memberCount": route["memberCount"], "start": record["start"],
            "end": record["end"], "structurallyExact": True,
        })
    ranges = [
        {"name": "skillData.memberCount", "start": 0, "end": 1, "kind": "SkillData.member-count"},
        {"name": "skillData.actionGroupData.memberCount", "start": 1, "end": 2,
         "kind": "ActionGroupData.member-count"},
    ]
    for index, span in enumerate(reader.ranges):
        ranges.append({
            "name": (
                "skillData.actionGroupData.timelineActions.count"
                if span["start"] == timeline_count_start
                else f"passive.sharedSequence.range[{index}]"
            ),
            "start": span["start"], "end": span["end"], "kind": span["kind"],
        })
    cursor = 0
    for span in ranges:
        if span["start"] != cursor or span["end"] <= span["start"]:
            raise ValueError("skillPassiveSharedSequence.ranges:not-contiguous")
        cursor = span["end"]
    if cursor != reader.pos:
        raise ValueError("skillPassiveSharedSequence.ranges:end-drift")
    return {
        "status": "exact-passive-shared-sequence-list",
        "parserCursor": reader.pos,
        "hardLimit": hard_limit,
        "passiveEventActionsCount": passive_count,
        "timelineActionsCount": 0,
        "actionData": actions,
        "namedRanges": ranges,
        "wholeActionGroupDataExact": True,
        "wholeSkillDataExact": False,
        "evidenceBoundary": contract["evidenceBoundary"],
    }
