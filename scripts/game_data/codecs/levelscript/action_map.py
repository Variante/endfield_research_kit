"""Sequential, fail-closed ActionSerializedMap reader for reviewed layouts.

The adjacent reviewed contract owns selected-build union identities and
typed field order. This reader never searches for UIDs or guesses a body end.
It establishes stored data, not that an action or event executes at runtime.

Wire shape. An `ActionSerializedMap` is a member-count byte (3, or `0xFF`
for null) followed by three int32-counted lists: ActionBase, PureGetter
(`GetterBase` here) and ActionHeader. Each element is a union: one tag byte,
where `0xFA` introduces a little-endian uint16 wide tag and other bytes at or
above `0xFA` are refused, then a member-count byte, then the row's fields in
generated setter order. `GameCondition` unions nested inside a
`WaitForCondition` or task map use the separate `conditionLayouts` table.
The four dispatcher domains stay separate: identical scalar layouts never
merge a header, getter, action or condition row, and an outer wrapper never
licenses parsing past a nested polymorphic member it does not own.

Tiers. Reviewed rows in `action_map_layouts.json` are `exact`: each carries
its `nativeIdentity` (dispatcher switch target, registered type usage,
generated setter order). Every reviewed row, through any entry point, is
refused on a build whose native inputs differ from the contract's
`nativeInputs` (tags renumber per build, so the same pair could name another
type there); `decode_reviewed_node` also accepts an explicit game root, and
`python -m scripts.game_data.levelscript_route_deserialize_native` re-checks
the rows' Deserialize order on a selected build. A caller that passes the
derived `Declarations` from `scripts.game_data.levelscript_union_layouts`
reads at the `direct` tier and must say so.

Native gates. `_required_native_gates` reads the route identity of every
per-route contract listed there (the integrated gate list). A layout row for
one of those routes must name the matching `nativeGate`, and
`_require_selected_native` refuses the row unless that validator returns
`validated` with the same wrapper and field list; build or body drift makes
the route unavailable instead of plausible. A route with a tracked contract
and validator that is absent from that list and from the layout rows is
isolated and stops the reader at its first byte.

Promotion. A route moves in three steps, never skipped: an isolated contract,
validator and focused tests; then a layout row, a gate-list entry,
production source replay and a clean union derivation; then whole-owner
closure, which only the full authenticated JsonData gate
(`scripts.game_data.jsondata_corpus`) decides at physical EOF. Advancing a
cursor to a later union promotes nothing, and a projection made between the
second and third step is provisional. Template and Interactive owners reuse
this reader, but reuse never bypasses their own dispatcher or EOF gate.

Shapes worth knowing, beyond what the rows state:

* Action-level `Param<GameplayTag>` is a raw int32; it lacks the standalone
  GameplayTag reader's nested one-member header.
* `LevelScriptPtr` has no decimal-magnitude framing rule: a short local ID is
  a valid uint64 with the same zero reserved word and Param tail as a long
  one.
* `Param<SpawnerPtr>` is a four-member Param whose constant is one unmanaged
  uint64 ID. Some reached getters store ID zero and bind the value through
  source `200` properties instead; others store nonzero constants.
* The `FinishBuff` `Param<BuffPtr>` value follows the generated 4/1/2 member
  chain, a cached unsigned identity and a null object marker before the
  ordinary Param tail.
* `PlayFmvAction` stores `moviePath`, a `CommonMaskBlendData` `param`,
  `shouldWaitForFinish`, the `afterMask` mask, then `beforeMask` and
  `overrideAfterMaskConfig` as booleans. Field names do not decide wire
  types; the generated setters do.
* `PlayDialogAndHideSceneObjectAction` inherits the
  `StartCinematicAndHideSceneObject` fields (interactive and scene-object
  hide lists, two override booleans, after/before masks) and adds its own
  `dialogId` last.
* `ScriptEvent_OnCustomEvent` follows the inherited script-event fields with
  `eventArgsPtr` as `ParamOutput<EventArgsPtr>` and `eventKey` as
  `Param<string>`; it closes the `LST_Sdg_*` progression templates.
* Enum backings differ by route: the two `AudioBlackScreenBehaviour` enums
  of `BlackScreenFadeInAndOut` are byte-backed, `PostAudioCue` uses the
  generated default Int32, `ShowUIToast` keeps an Int32-backed alias, and
  several others are signed-int aliases. The width comes from the enum
  alias table in `_Cursor.value`, never from the enum's name.
* Positive `Param<List<PosRot>>` and `Param<List<GameplayTag>>` elements and
  non-null `CameraControllerBase` constants remain unsupported and fail
  closed (see the contract's `supportedBoundary`).
"""

from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from . import params
from . import send_lua_event


CONTRACT_PATH = Path(__file__).with_name("action_map_layouts.json")


class ActionMapCodecError(ValueError):
    """The next declared field has no proven exact cursor."""


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_bytes())
    if contract.get("schema") != "endfield.action-map-layouts.v3":
        raise ActionMapCodecError("actionMap.layoutContract:unsupported-schema")
    return contract


@lru_cache(maxsize=1)
def _layouts() -> dict[tuple[str, int], dict[str, Any]]:
    return {(row["family"], row["tag"]): row for row in _contract()["layouts"]}


@lru_cache(maxsize=1)
def _condition_layouts() -> dict[int, dict[str, Any]]:
    return {row["tag"]: row for row in _contract().get("conditionLayouts", [])}


@lru_cache(maxsize=1)
def _layout_build_status() -> tuple[str, str]:
    """The installed build against the layout contract, checked once per process."""
    inputs = _contract()["nativeInputs"]
    native = check_installed_native_inputs(
        inputs["gameAssembly"]["sha256"], inputs["metadata"]["sha256"],
    )
    return native.status, native.detail


def _require_layout_build() -> None:
    """Refuse every reviewed row on a build other than the contract's.

    A union tag is its type's rank among the family's wrappers, so a client
    update renumbers it: on another build a reviewed `(tag, memberCount)` pair
    can name a different type and would decode plausibly. Rows with their own
    `nativeGate` are re-proved per route; this gate covers every other row.
    """
    status, detail = _layout_build_status()
    if status != "validated":
        raise ActionMapCodecError(
            f"actionMap.installed_native_inputs: expected=validated, "
            f"actual={status}, detail={detail}"
        )


@lru_cache(maxsize=1)
def _finish_scene_effect_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_finish_scene_effect_native import (
        validate_finish_scene_effect_native_contract,
    )

    return validate_finish_scene_effect_native_contract()


@lru_cache(maxsize=1)
def _npc_proxy_patrol_stop_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_proxy_patrol_stop_native import (
        validate_npc_proxy_patrol_stop_native_contract,
    )

    return validate_npc_proxy_patrol_stop_native_contract()


@lru_cache(maxsize=1)
def _post_audio_status_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_post_audio_status_native import (
        validate_post_audio_status_native_contract,
    )

    return validate_post_audio_status_native_contract()


@lru_cache(maxsize=1)
def _entities_visibility_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entities_visibility_native import (
        validate_entities_visibility_native_contract,
    )

    return validate_entities_visibility_native_contract()


@lru_cache(maxsize=1)
def _track_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_track_camera_native import (
        validate_track_camera_native_contract,
    )

    return validate_track_camera_native_contract()


@lru_cache(maxsize=1)
def _enemy_patrol_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_enemy_patrol_start_native import (
        validate_enemy_patrol_start_native_contract,
    )

    return validate_enemy_patrol_start_native_contract()


@lru_cache(maxsize=1)
def _archery_stage_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_archery_stage_native import (
        validate_archery_stage_native_contract,
    )

    return validate_archery_stage_native_contract()


@lru_cache(maxsize=1)
def _typhoea_chip_id_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_typhoea_chip_id_native import (
        validate_typhoea_chip_id_native_contract,
    )

    return validate_typhoea_chip_id_native_contract()


@lru_cache(maxsize=1)
def _finish_buffs_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_finish_buffs_native import (
        validate_finish_buffs_native_contract,
    )

    return validate_finish_buffs_native_contract()


@lru_cache(maxsize=1)
def _mark_task_condition_failed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_mark_task_condition_failed_native import (
        validate_levelscript_mark_task_condition_failed_native_contract,
    )

    return validate_levelscript_mark_task_condition_failed_native_contract()


@lru_cache(maxsize=1)
def _archery_advanced_headers_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_archery_advanced_headers_native import (
        validate_levelscript_archery_advanced_headers_native_contract,
    )

    return validate_levelscript_archery_advanced_headers_native_contract()


@lru_cache(maxsize=1)
def _on_train_level_event_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_train_level_event_native import (
        validate_levelscript_on_train_level_event_native_contract,
    )

    return validate_levelscript_on_train_level_event_native_contract()


@lru_cache(maxsize=1)
def _on_map_var_changed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_map_var_changed_native import (
        validate_levelscript_on_map_var_changed_native_contract,
    )

    return validate_levelscript_on_map_var_changed_native_contract()


@lru_cache(maxsize=1)
def _on_enemy_in_fight_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_enemy_in_fight_native import (
        validate_levelscript_on_enemy_in_fight_native_contract,
    )

    return validate_levelscript_on_enemy_in_fight_native_contract()


@lru_cache(maxsize=1)
def _on_enemy_take_last_attack_damage_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_enemy_take_last_attack_damage_native import (
        validate_levelscript_on_enemy_take_last_attack_damage_native_contract,
    )

    return validate_levelscript_on_enemy_take_last_attack_damage_native_contract()


@lru_cache(maxsize=1)
def _on_spell_infliction_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spell_infliction_native import (
        validate_levelscript_on_spell_infliction_native_contract,
    )

    return validate_levelscript_on_spell_infliction_native_contract()


@lru_cache(maxsize=1)
def _on_spawner_entity_spawn_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_entity_spawn_native import (
        validate_levelscript_on_spawner_entity_spawn_native_contract,
    )

    return validate_levelscript_on_spawner_entity_spawn_native_contract()


@lru_cache(maxsize=1)
def _on_spawner_group_begin_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_group_begin_native import (
        validate_levelscript_on_spawner_group_begin_native_contract,
    )

    return validate_levelscript_on_spawner_group_begin_native_contract()


@lru_cache(maxsize=1)
def _on_spawner_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_start_native import (
        validate_levelscript_on_spawner_start_native_contract,
    )

    return validate_levelscript_on_spawner_start_native_contract()


@lru_cache(maxsize=1)
def _on_spell_abnormal_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spell_abnormal_start_native import (
        validate_levelscript_on_spell_abnormal_start_native_contract,
    )

    return validate_levelscript_on_spell_abnormal_start_native_contract()


@lru_cache(maxsize=1)
def _on_physical_infliction_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_physical_infliction_native import (
        validate_levelscript_on_physical_infliction_native_contract,
    )

    return validate_levelscript_on_physical_infliction_native_contract()


@lru_cache(maxsize=1)
def _on_bb_variable_changed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_bb_variable_changed_native import (
        validate_levelscript_on_bb_variable_changed_native_contract,
    )

    return validate_levelscript_on_bb_variable_changed_native_contract()


@lru_cache(maxsize=1)
def _on_physical_no_guard_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_physical_no_guard_native import (
        validate_levelscript_on_physical_no_guard_native_contract,
    )

    return validate_levelscript_on_physical_no_guard_native_contract()


@lru_cache(maxsize=1)
def _on_spawner_wave_begin_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_wave_begin_native import (
        validate_levelscript_on_spawner_wave_begin_native_contract,
    )

    return validate_levelscript_on_spawner_wave_begin_native_contract()


@lru_cache(maxsize=1)
def _on_spawner_entity_die_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_entity_die_native import (
        validate_levelscript_on_spawner_entity_die_native_contract,
    )

    return validate_levelscript_on_spawner_entity_die_native_contract()


@lru_cache(maxsize=1)
def _on_encounter_activated_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_encounter_activated_native import (
        validate_levelscript_on_encounter_activated_native_contract,
    )

    return validate_levelscript_on_encounter_activated_native_contract()


@lru_cache(maxsize=1)
def _on_encounter_battle_part_begin_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_encounter_battle_part_begin_native import (
        validate_levelscript_on_encounter_battle_part_begin_native_contract,
    )

    return validate_levelscript_on_encounter_battle_part_begin_native_contract()


@lru_cache(maxsize=1)
def _on_encounter_battle_part_end_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_encounter_battle_part_end_native import (
        validate_levelscript_on_encounter_battle_part_end_native_contract,
    )

    return validate_levelscript_on_encounter_battle_part_end_native_contract()


@lru_cache(maxsize=1)
def _on_entity_cast_skill_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_entity_cast_skill_native import (
        validate_levelscript_on_entity_cast_skill_native_contract,
    )

    return validate_levelscript_on_entity_cast_skill_native_contract()


@lru_cache(maxsize=1)
def _on_leader_enter_trigger_volume_list_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_leader_enter_trigger_volume_list_native import (
        validate_levelscript_on_leader_enter_trigger_volume_list_native_contract,
    )

    return validate_levelscript_on_leader_enter_trigger_volume_list_native_contract()


@lru_cache(maxsize=1)
def _list_add_value_entity_ptr_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_list_add_value_entity_ptr_native import (
        validate_levelscript_list_add_value_entity_ptr_native_contract,
    )

    return validate_levelscript_list_add_value_entity_ptr_native_contract()


@lru_cache(maxsize=1)
def _add_tracking_point_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_add_tracking_point_native import (
        validate_levelscript_add_tracking_point_native_contract,
    )

    return validate_levelscript_add_tracking_point_native_contract()


@lru_cache(maxsize=1)
def _set_forbid_map_teleport_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_forbid_map_teleport_native import (
        validate_levelscript_set_forbid_map_teleport_native_contract,
    )

    return validate_levelscript_set_forbid_map_teleport_native_contract()


@lru_cache(maxsize=1)
def _resume_spawner_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_resume_spawner_native import (
        validate_levelscript_resume_spawner_native_contract,
    )

    return validate_levelscript_resume_spawner_native_contract()


@lru_cache(maxsize=1)
def _start_seq_loop_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_seq_loop_native import (
        validate_start_seq_loop_native_contract,
    )

    return validate_start_seq_loop_native_contract()


@lru_cache(maxsize=1)
def _entity_scanned_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entity_scanned_native import (
        validate_entity_scanned_native_contract,
    )

    return validate_entity_scanned_native_contract()


@lru_cache(maxsize=1)
def _squad_fight_header_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_squad_fight_header_native import (
        validate_squad_fight_header_native_contract,
    )

    return validate_squad_fight_header_native_contract()


@lru_cache(maxsize=1)
def _leader_enter_trigger_volume_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_leader_enter_trigger_volume_native import (
        validate_leader_enter_trigger_volume_native_contract,
    )

    return validate_leader_enter_trigger_volume_native_contract()


@lru_cache(maxsize=1)
def _squad_all_die_header_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_squad_all_die_header_native import (
        validate_squad_all_die_header_native_contract,
    )

    return validate_squad_all_die_header_native_contract()


@lru_cache(maxsize=1)
def _tracking_point_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_tracking_point_native import (
        validate_tracking_point_native_contract,
    )

    return validate_tracking_point_native_contract()


@lru_cache(maxsize=1)
def _mission_changed_header_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_mission_changed_header_native import (
        validate_mission_changed_header_native_contract,
    )

    return validate_mission_changed_header_native_contract()


@lru_cache(maxsize=1)
def _cutscene_teleport_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_cutscene_teleport_native import (
        validate_cutscene_teleport_native_contract,
    )

    return validate_cutscene_teleport_native_contract()


@lru_cache(maxsize=1)
def _manually_stop_guide_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_manually_stop_guide_native import (
        validate_manually_stop_guide_native_contract,
    )

    return validate_manually_stop_guide_native_contract()


@lru_cache(maxsize=1)
def _remove_tracking_point_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_remove_tracking_point_native import (
        validate_remove_tracking_point_native_contract,
    )

    return validate_remove_tracking_point_native_contract()


@lru_cache(maxsize=1)
def _get_is_leader_in_trigger_volume_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_is_leader_in_trigger_volume_native import (
        validate_get_is_leader_in_trigger_volume_native_contract,
    )

    return validate_get_is_leader_in_trigger_volume_native_contract()


@lru_cache(maxsize=1)
def _send_lua_event1_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_send_lua_event1_native import (
        validate_send_lua_event1_native_contract,
    )

    return validate_send_lua_event1_native_contract()


@lru_cache(maxsize=1)
def _start_subgame_countdown_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_subgame_countdown_native import (
        validate_start_subgame_countdown_native_contract,
    )

    return validate_start_subgame_countdown_native_contract()


@lru_cache(maxsize=1)
def _show_start_toast_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_show_start_toast_native import (
        validate_show_start_toast_native_contract,
    )

    return validate_show_start_toast_native_contract()


@lru_cache(maxsize=1)
def _show_finish_toast_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_show_finish_toast_native import (
        validate_show_finish_toast_native_contract,
    )

    return validate_show_finish_toast_native_contract()


@lru_cache(maxsize=1)
def _toggle_main_hud_ignore_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_toggle_main_hud_ignore_native import (
        validate_toggle_main_hud_ignore_native_contract,
    )

    return validate_toggle_main_hud_ignore_native_contract()


@lru_cache(maxsize=1)
def _show_chapter_panel_direct_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_show_chapter_panel_direct_native import (
        validate_show_chapter_panel_direct_native_contract,
    )

    return validate_show_chapter_panel_direct_native_contract()


@lru_cache(maxsize=1)
def _show_chapter_completed_panel_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_show_chapter_completed_panel_native import (
        validate_show_chapter_completed_panel_native_contract,
    )

    return validate_show_chapter_completed_panel_native_contract()


@lru_cache(maxsize=1)
def _switch_to_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_switch_to_camera_native import (
        validate_switch_to_camera_native_contract,
    )

    return validate_switch_to_camera_native_contract()


@lru_cache(maxsize=1)
def _start_track_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_track_camera_native import (
        validate_start_track_camera_native_contract,
    )

    return validate_start_track_camera_native_contract()


@lru_cache(maxsize=1)
def _exit_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_exit_camera_native import (
        validate_exit_camera_native_contract,
    )

    return validate_exit_camera_native_contract()


@lru_cache(maxsize=1)
def _reset_follow_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_reset_follow_camera_native import (
        validate_reset_follow_camera_native_contract,
    )

    return validate_reset_follow_camera_native_contract()


@lru_cache(maxsize=1)
def _fac_set_interact_locked_state_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_set_interact_locked_state_native import (
        validate_fac_set_interact_locked_state_native_contract,
    )

    return validate_fac_set_interact_locked_state_native_contract()


@lru_cache(maxsize=1)
def _toggle_clear_screen_but_radio_v2_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_toggle_clear_screen_but_radio_v2_native import (
        validate_toggle_clear_screen_but_radio_v2_native_contract,
    )

    return validate_toggle_clear_screen_but_radio_v2_native_contract()


@lru_cache(maxsize=1)
def _remove_npc_dialog_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_remove_npc_dialog_native import (
        validate_remove_npc_dialog_native_contract,
    )

    return validate_remove_npc_dialog_native_contract()


@lru_cache(maxsize=1)
def _stop_subgame_countdown_by_handle_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_stop_subgame_countdown_by_handle_native import (
        validate_stop_subgame_countdown_by_handle_native_contract,
    )

    return validate_stop_subgame_countdown_by_handle_native_contract()


@lru_cache(maxsize=1)
def _require_settlement_show_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_require_settlement_show_native import (
        validate_require_settlement_show_native_contract,
    )

    return validate_require_settlement_show_native_contract()


@lru_cache(maxsize=1)
def _settlement_followon_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_settlement_followon_native import (
        validate_settlement_followon_native_contract,
    )

    return validate_settlement_followon_native_contract()


@lru_cache(maxsize=1)
def _bool_compare_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_bool_compare_native import (
        validate_bool_compare_native_contract,
    )

    return validate_bool_compare_native_contract()


@lru_cache(maxsize=1)
def _fac_top_view_range_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_top_view_range_native import (
        validate_fac_top_view_range_native_contract,
    )

    return validate_fac_top_view_range_native_contract()


@lru_cache(maxsize=1)
def _fac_build_effect_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_build_effect_native import (
        validate_fac_build_effect_native_contract,
    )

    return validate_fac_build_effect_native_contract()


@lru_cache(maxsize=1)
def _fac_change_building_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_change_building_native import (
        validate_fac_change_building_native_contract,
    )

    return validate_fac_change_building_native_contract()


@lru_cache(maxsize=1)
def _npc_proxy_effect_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_proxy_effect_native import (
        validate_npc_proxy_effect_native_contract,
    )

    return validate_npc_proxy_effect_native_contract()


@lru_cache(maxsize=1)
def _npc_effect_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_effect_native import (
        validate_npc_effect_native_contract,
    )

    return validate_npc_effect_native_contract()


@lru_cache(maxsize=1)
def _block_battle_music_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_block_battle_music_native import (
        validate_block_battle_music_native_contract,
    )

    return validate_block_battle_music_native_contract()


@lru_cache(maxsize=1)
def _block_auto_music_change_cancel_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_block_auto_music_change_cancel_native import (
        validate_block_auto_music_change_cancel_native_contract,
    )

    return validate_block_auto_music_change_cancel_native_contract()


@lru_cache(maxsize=1)
def _fac_get_building_position_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_get_building_position_native import (
        validate_fac_get_building_position_native_contract,
    )

    return validate_fac_get_building_position_native_contract()


@lru_cache(maxsize=1)
def _entity_hp_changed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entity_hp_changed_native import (
        validate_entity_hp_changed_native_contract,
    )

    return validate_entity_hp_changed_native_contract()


@lru_cache(maxsize=1)
def _settlement_upgrade_show_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_settlement_upgrade_show_native import (
        validate_settlement_upgrade_show_native_contract,
    )

    return validate_settlement_upgrade_show_native_contract()


@lru_cache(maxsize=1)
def _check_performance_ready_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_check_performance_ready_native import (
        validate_check_performance_ready_native_contract,
    )

    return validate_check_performance_ready_native_contract()


@lru_cache(maxsize=1)
def _environment_enable_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_environment_enable_native import (
        validate_environment_enable_native_contract,
    )

    return validate_environment_enable_native_contract()


@lru_cache(maxsize=1)
def _settlement_ready_performance_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_settlement_ready_performance_native import (
        validate_settlement_ready_performance_native_contract,
    )

    return validate_settlement_ready_performance_native_contract()


@lru_cache(maxsize=1)
def _add_buffs_to_target_selves_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_add_buffs_to_target_selves_native import (
        validate_add_buffs_to_target_selves_native_contract,
    )

    return validate_add_buffs_to_target_selves_native_contract()


@lru_cache(maxsize=1)
def _set_squad_special_idle_enable_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_squad_special_idle_enable_native import (
        validate_set_squad_special_idle_enable_native_contract,
    )

    return validate_set_squad_special_idle_enable_native_contract()


@lru_cache(maxsize=1)
def _list_make_entity_ptr_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_list_make_entity_ptr_native import (
        validate_list_make_entity_ptr_native_contract,
    )

    return validate_list_make_entity_ptr_native_contract()


@lru_cache(maxsize=1)
def _getter_entity_ptr_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_getter_entity_ptr_native import (
        validate_getter_entity_ptr_native_contract,
    )

    return validate_getter_entity_ptr_native_contract()


@lru_cache(maxsize=1)
def _getter_levelscript_ptr_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_getter_levelscript_ptr_native import (
        validate_getter_levelscript_ptr_native_contract,
    )

    return validate_getter_levelscript_ptr_native_contract()


@lru_cache(maxsize=1)
def _set_enemy_ui_show_range_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_enemy_ui_show_range_native import (
        validate_set_enemy_ui_show_range_native_contract,
    )

    return validate_set_enemy_ui_show_range_native_contract()


@lru_cache(maxsize=1)
def _set_list_buff_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_list_buff_native import (
        validate_set_list_buff_native_contract,
    )

    return validate_set_list_buff_native_contract()


@lru_cache(maxsize=1)
def _entity_to_string_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entity_to_string_native import (
        validate_entity_to_string_native_contract,
    )

    return validate_entity_to_string_native_contract()


@lru_cache(maxsize=1)
def _is_look_at_point_in_screen_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_is_look_at_point_in_screen_native import (
        validate_is_look_at_point_in_screen_native_contract,
    )

    return validate_is_look_at_point_in_screen_native_contract()


@lru_cache(maxsize=1)
def _getter_list_buff_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_getter_list_buff_native import (
        validate_getter_list_buff_native_contract,
    )

    return validate_getter_list_buff_native_contract()


@lru_cache(maxsize=1)
def _get_cur_squad_all_dead_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_cur_squad_all_dead_native import (
        validate_get_cur_squad_all_dead_native_contract,
    )

    return validate_get_cur_squad_all_dead_native_contract()


@lru_cache(maxsize=1)
def _get_character_template_id_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_character_template_id_native import (
        validate_get_character_template_id_native_contract,
    )

    return validate_get_character_template_id_native_contract()


@lru_cache(maxsize=1)
def _float_getter_int_to_float_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_float_getter_int_to_float_native import (
        validate_float_getter_int_to_float_native_contract,
    )

    return validate_float_getter_int_to_float_native_contract()


@lru_cache(maxsize=1)
def _float_getter_plus_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_float_getter_plus_native import (
        validate_float_getter_plus_native_contract,
    )

    return validate_float_getter_plus_native_contract()


@lru_cache(maxsize=1)
def _bool_getter_mult_or_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_bool_getter_mult_or_native import (
        validate_bool_getter_mult_or_native_contract,
    )

    return validate_bool_getter_mult_or_native_contract()


@lru_cache(maxsize=1)
def _play_voice_narrative_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_play_voice_narrative_native import (
        validate_play_voice_narrative_native_contract,
    )

    return validate_play_voice_narrative_native_contract()


@lru_cache(maxsize=1)
def _scripted_char_teleport_to_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_scripted_char_teleport_to_native import (
        validate_scripted_char_teleport_to_native_contract,
    )

    return validate_scripted_char_teleport_to_native_contract()


@lru_cache(maxsize=1)
def _scripted_char_patrol_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_scripted_char_patrol_start_native import (
        validate_scripted_char_patrol_start_native_contract,
    )

    return validate_scripted_char_patrol_start_native_contract()


@lru_cache(maxsize=1)
def _stop_char_scripted_mode_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_stop_char_scripted_mode_native import (
        validate_stop_char_scripted_mode_native_contract,
    )

    return validate_stop_char_scripted_mode_native_contract()


@lru_cache(maxsize=1)
def _on_any_entity_die_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_any_entity_die_native import (
        validate_on_any_entity_die_native_contract,
    )

    return validate_on_any_entity_die_native_contract()


@lru_cache(maxsize=1)
def _on_start_script_controlled_char_mode_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_start_script_controlled_char_mode_native import (
        validate_on_start_script_controlled_char_mode_native_contract,
    )

    return validate_on_start_script_controlled_char_mode_native_contract()


@lru_cache(maxsize=1)
def _on_spawner_pause_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_pause_native import (
        validate_on_spawner_pause_native_contract,
    )

    return validate_on_spawner_pause_native_contract()


@lru_cache(maxsize=1)
def _building_pos_hint_show_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_building_pos_hint_show_native import (
        validate_building_pos_hint_show_native_contract,
    )

    return validate_building_pos_hint_show_native_contract()


@lru_cache(maxsize=1)
def _building_pos_hint_hide_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_building_pos_hint_hide_native import (
        validate_building_pos_hint_hide_native_contract,
    )

    return validate_building_pos_hint_hide_native_contract()


@lru_cache(maxsize=1)
def _fac_guide_hint_enable_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_guide_hint_enable_native import (
        validate_fac_guide_hint_enable_native_contract,
    )

    return validate_fac_guide_hint_enable_native_contract()


@lru_cache(maxsize=1)
def _npc_get_pack_anim_has_clean_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_get_pack_anim_has_clean_native import (
        validate_npc_get_pack_anim_has_clean_native_contract,
    )

    return validate_npc_get_pack_anim_has_clean_native_contract()


@lru_cache(maxsize=1)
def _on_encounter_intro_part_end_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_encounter_intro_part_end_native import (
        validate_levelscript_on_encounter_intro_part_end_native_contract,
    )

    return validate_levelscript_on_encounter_intro_part_end_native_contract()


@lru_cache(maxsize=1)
def _on_npc_dirty_block_cleaned_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_npc_dirty_block_cleaned_native import (
        validate_levelscript_on_npc_dirty_block_cleaned_native_contract,
    )

    return validate_levelscript_on_npc_dirty_block_cleaned_native_contract()


@lru_cache(maxsize=1)
def _on_server_dialog_exit_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_server_dialog_exit_native import (
        validate_levelscript_on_server_dialog_exit_native_contract,
    )

    return validate_levelscript_on_server_dialog_exit_native_contract()


@lru_cache(maxsize=1)
def _on_level_reset_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_level_reset_native import (
        validate_levelscript_on_level_reset_native_contract,
    )

    return validate_levelscript_on_level_reset_native_contract()


@lru_cache(maxsize=1)
def _on_specific_entity_die_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_specific_entity_die_native import (
        validate_levelscript_on_specific_entity_die_native_contract,
    )

    return validate_levelscript_on_specific_entity_die_native_contract()


@lru_cache(maxsize=1)
def _on_sub_game_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_sub_game_start_native import (
        validate_levelscript_on_sub_game_start_native_contract,
    )

    return validate_levelscript_on_sub_game_start_native_contract()


@lru_cache(maxsize=1)
def _on_npc_patrol_checkpoint_reach_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_npc_patrol_checkpoint_reach_native import (
        validate_levelscript_on_npc_patrol_checkpoint_reach_native_contract,
    )

    return validate_levelscript_on_npc_patrol_checkpoint_reach_native_contract()


@lru_cache(maxsize=1)
def _on_spawner_group_complete_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_group_complete_native import (
        validate_levelscript_on_spawner_group_complete_native_contract,
    )

    return validate_levelscript_on_spawner_group_complete_native_contract()


@lru_cache(maxsize=1)
def _set_decoration_animator_int_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_decoration_animator_int_native import (
        validate_set_decoration_animator_int_native_contract,
    )

    return validate_set_decoration_animator_int_native_contract()


@lru_cache(maxsize=1)
def _set_decoration_view_state_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_decoration_view_state_native import (
        validate_set_decoration_view_state_native_contract,
    )

    return validate_set_decoration_view_state_native_contract()


@lru_cache(maxsize=1)
def _entity_move_to_with_speed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entity_move_to_with_speed_native import (
        validate_entity_move_to_with_speed_native_contract,
    )

    return validate_entity_move_to_with_speed_native_contract()


@lru_cache(maxsize=1)
def _start_fmv_and_teleport_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_fmv_and_teleport_native import (
        validate_start_fmv_and_teleport_native_contract,
    )

    return validate_start_fmv_and_teleport_native_contract()


@lru_cache(maxsize=1)
def _disable_hud_fade_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_disable_hud_fade_native import (
        validate_disable_hud_fade_native_contract,
    )

    return validate_disable_hud_fade_native_contract()


@lru_cache(maxsize=1)
def _stop_effect_on_npc_proxy_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_stop_effect_on_npc_proxy_native import (
        validate_stop_effect_on_npc_proxy_native_contract,
    )

    return validate_stop_effect_on_npc_proxy_native_contract()


@lru_cache(maxsize=1)
def _npc_stop_cur_montage_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_stop_cur_montage_native import (
        validate_npc_stop_cur_montage_native_contract,
    )

    return validate_npc_stop_cur_montage_native_contract()


@lru_cache(maxsize=1)
def _set_main_char_hp_bar_active_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_main_char_hp_bar_active_native import (
        validate_set_main_char_hp_bar_active_native_contract,
    )

    return validate_set_main_char_hp_bar_active_native_contract()


@lru_cache(maxsize=1)
def _destroy_ability_entity_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_destroy_ability_entity_native import (
        validate_destroy_ability_entity_native_contract,
    )

    return validate_destroy_ability_entity_native_contract()


@lru_cache(maxsize=1)
def _move_bamboo_last_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_move_bamboo_last_native import (
        validate_move_bamboo_last_native_contract,
    )

    return validate_move_bamboo_last_native_contract()


@lru_cache(maxsize=1)
def _is_endmin_gender_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_is_endmin_gender_native import (
        validate_is_endmin_gender_native_contract,
    )

    return validate_is_endmin_gender_native_contract()


@lru_cache(maxsize=1)
def _teleport_gameplay_npc_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_teleport_gameplay_npc_native import (
        validate_levelscript_teleport_gameplay_npc_native_contract,
    )

    return validate_levelscript_teleport_gameplay_npc_native_contract()


@lru_cache(maxsize=1)
def _apply_movement_setting_modifier_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_apply_movement_setting_modifier_native import (
        validate_apply_movement_setting_modifier_native_contract,
    )

    return validate_apply_movement_setting_modifier_native_contract()


@lru_cache(maxsize=1)
def _toggle_ui_dev_only_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_toggle_ui_dev_only_native import (
        validate_toggle_ui_dev_only_native_contract,
    )

    return validate_toggle_ui_dev_only_native_contract()


@lru_cache(maxsize=1)
def _start_cutscene_hide_scene_object_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_cutscene_hide_scene_object_native import (
        validate_start_cutscene_hide_scene_object_native_contract,
    )

    return validate_start_cutscene_hide_scene_object_native_contract()


@lru_cache(maxsize=1)
def _start_cutscene_control_scene_object_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_cutscene_control_scene_object_native import (
        validate_start_cutscene_control_scene_object_native_contract,
    )

    return validate_start_cutscene_control_scene_object_native_contract()


@lru_cache(maxsize=1)
def _set_squad_icon_active_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_squad_icon_active_native import (
        validate_set_squad_icon_active_native_contract,
    )

    return validate_set_squad_icon_active_native_contract()


@lru_cache(maxsize=1)
def _skip_entity_die_display_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_skip_entity_die_display_native import (
        validate_skip_entity_die_display_native_contract,
    )

    return validate_skip_entity_die_display_native_contract()


@lru_cache(maxsize=1)
def _get_script_task_objective_is_completed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_script_task_objective_is_completed_native import (
        validate_get_script_task_objective_is_completed_native_contract,
    )

    return validate_get_script_task_objective_is_completed_native_contract()


@lru_cache(maxsize=1)
def _on_any_enemy_poise_zero_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_any_enemy_poise_zero_native import (
        validate_on_any_enemy_poise_zero_native_contract,
    )

    return validate_on_any_enemy_poise_zero_native_contract()


@lru_cache(maxsize=1)
def _on_any_enemy_poise_knot_break_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_any_enemy_poise_knot_break_native import (
        validate_on_any_enemy_poise_knot_break_native_contract,
    )

    return validate_on_any_enemy_poise_knot_break_native_contract()


@lru_cache(maxsize=1)
def _on_aether_lock_endpoint_scanned_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_aether_lock_endpoint_scanned_native import (
        validate_levelscript_on_aether_lock_endpoint_scanned_native_contract,
    )

    return validate_levelscript_on_aether_lock_endpoint_scanned_native_contract()


@lru_cache(maxsize=1)
def _on_cutscene_exit_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_cutscene_exit_native import (
        validate_levelscript_on_cutscene_exit_native_contract,
    )

    return validate_levelscript_on_cutscene_exit_native_contract()


@lru_cache(maxsize=1)
def _on_entity_die_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_entity_die_native import (
        validate_levelscript_on_entity_die_native_contract,
    )

    return validate_levelscript_on_entity_die_native_contract()


@lru_cache(maxsize=1)
def _on_blight_miasma_weak_guide_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_blight_miasma_weak_guide_native import (
        validate_levelscript_on_blight_miasma_weak_guide_native_contract,
    )

    return validate_levelscript_on_blight_miasma_weak_guide_native_contract()


@lru_cache(maxsize=1)
def _event_args_float_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_event_args_float_native import (
        validate_event_args_float_native_contract,
    )

    return validate_event_args_float_native_contract()


@lru_cache(maxsize=1)
def _audio_cue_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_audio_cue_native import (
        validate_audio_cue_native_contract,
    )

    return validate_audio_cue_native_contract()


@lru_cache(maxsize=1)
def _override_npc_dialog_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_override_npc_dialog_native import (
        validate_override_npc_dialog_native_contract,
    )

    return validate_override_npc_dialog_native_contract()


@lru_cache(maxsize=1)
def _getter_compare_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_getter_compare_native import (
        validate_getter_compare_native_contract,
    )

    return validate_getter_compare_native_contract()


@lru_cache(maxsize=1)
def _get_mission_state_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_mission_state_native import (
        validate_get_mission_state_native_contract,
    )

    return validate_get_mission_state_native_contract()


@lru_cache(maxsize=1)
def _water_height_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_water_height_native import (
        validate_water_height_native_contract,
    )

    return validate_water_height_native_contract()


@lru_cache(maxsize=1)
def _set_fac_mode_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_fac_mode_native import (
        validate_set_fac_mode_native_contract,
    )

    return validate_set_fac_mode_native_contract()


@lru_cache(maxsize=1)
def _required_native_gates() -> dict[tuple[str, int], str]:
    """Read selected route identities from their reviewed contracts."""
    required: dict[tuple[str, int], str] = {}
    for filename, schema, gate in (
        ("levelscript_header_native.json", "endfield.levelscript-header-native-contract.v1", "levelscript_header_native"),
        ("levelscript_finish_scene_effect_native.json", "endfield.levelscript-finish-scene-effect-native-contract.v1", "levelscript_finish_scene_effect_native"),
        ("levelscript_getter_int_native.json", "endfield.levelscript-getter-int-native-contract.v1", "levelscript_getter_int_native"),
        ("levelscript_getter_compare_native.json", "endfield.levelscript-getter-compare-native-contract.v1", "levelscript_getter_compare_native"),
        ("levelscript_get_mission_state_native.json", "endfield.levelscript-get-mission-state-native-contract.v1", "levelscript_get_mission_state_native"),
        ("levelscript_water_height_native.json", "endfield.levelscript-water-height-native-contract.v1", "levelscript_water_height_native"),
        ("levelscript_set_fac_mode_native.json", "endfield.levelscript-set-fac-mode-native-contract.v1", "levelscript_set_fac_mode_native"),
        ("levelscript_npc_proxy_patrol_stop_native.json", "endfield.levelscript-npc-proxy-patrol-stop-native-contract.v1", "levelscript_npc_proxy_patrol_stop_native"),
        ("levelscript_post_audio_status_native.json", "endfield.levelscript-post-audio-status-native-contract.v1", "levelscript_post_audio_status_native"),
        ("levelscript_entities_visibility_native.json", "endfield.levelscript-entities-visibility-native-contract.v1", "levelscript_entities_visibility_native"),
        ("levelscript_track_camera_native.json", "endfield.levelscript-track-camera-native-contract.v1", "levelscript_track_camera_native"),
        ("levelscript_enemy_patrol_start_native.json", "endfield.levelscript-enemy-patrol-start-native-contract.v1", "levelscript_enemy_patrol_start_native"),
        ("levelscript_archery_stage_native.json", "endfield.levelscript-enable-typhoea-archery-stage-native-contract.v1", "levelscript_archery_stage_native"),
        ("levelscript_typhoea_chip_id_native.json", "endfield.levelscript-typhoea-chip-id-native-contract.v1", "levelscript_typhoea_chip_id_native"),
        ("levelscript_finish_buffs_native.json", "endfield.levelscript-finish-buffs-native-contract.v1", "levelscript_finish_buffs_native"),
        ("levelscript_mark_task_condition_failed_native.json", "endfield.levelscript-mark-task-condition-failed-native.v1", "levelscript_mark_task_condition_failed_native"),
        ("levelscript_archery_advanced_headers_native.json", "endfield.levelscript-archery-advanced-headers-native.v1", "levelscript_archery_advanced_headers_native"),
        ("levelscript_on_train_level_event_native.json", "endfield.levelscript-on-train-level-event-native.v1", "levelscript_on_train_level_event_native"),
        ("levelscript_on_map_var_changed_native.json", "endfield.levelscript-on-map-var-changed-native.v1", "levelscript_on_map_var_changed_native"),
        ("levelscript_on_enemy_in_fight_native.json", "endfield.levelscript-on-enemy-in-fight-native.v1", "levelscript_on_enemy_in_fight_native"),
        ("levelscript_on_enemy_take_last_attack_damage_native.json", "endfield.levelscript-on-enemy-take-last-attack-damage-native.v1", "levelscript_on_enemy_take_last_attack_damage_native"),
        ("levelscript_on_spell_infliction_native.json", "endfield.levelscript-on-spell-infliction-native.v1", "levelscript_on_spell_infliction_native"),
        ("levelscript_on_spawner_entity_spawn_native.json", "endfield.levelscript-on-spawner-entity-spawn-native.v1", "levelscript_on_spawner_entity_spawn_native"),
        ("levelscript_on_spawner_group_begin_native.json", "endfield.levelscript-on-spawner-group-begin-native.v1", "levelscript_on_spawner_group_begin_native"),
        ("levelscript_on_spawner_start_native.json", "endfield.levelscript-on-spawner-start-native.v1", "levelscript_on_spawner_start_native"),
        ("levelscript_on_spell_abnormal_start_native.json", "endfield.levelscript-on-spell-abnormal-start-native.v1", "levelscript_on_spell_abnormal_start_native"),
        ("levelscript_on_physical_infliction_native.json", "endfield.levelscript-on-physical-infliction-native.v1", "levelscript_on_physical_infliction_native"),
        ("levelscript_on_bb_variable_changed_native.json", "endfield.levelscript-on-bb-variable-changed-native.v1", "levelscript_on_bb_variable_changed_native"),
        ("levelscript_on_physical_no_guard_native.json", "endfield.levelscript-on-physical-no-guard-native.v1", "levelscript_on_physical_no_guard_native"),
        ("levelscript_on_spawner_wave_begin_native.json", "endfield.levelscript-on-spawner-wave-begin-native.v1", "levelscript_on_spawner_wave_begin_native"),
        ("levelscript_on_spawner_entity_die_native.json", "endfield.levelscript-on-spawner-entity-die-native.v1", "levelscript_on_spawner_entity_die_native"),
        ("levelscript_on_encounter_activated_native.json", "endfield.levelscript-on-encounter-activated-native.v1", "levelscript_on_encounter_activated_native"),
        ("levelscript_on_encounter_battle_part_begin_native.json", "endfield.levelscript-on-encounter-battle-part-begin-native.v1", "levelscript_on_encounter_battle_part_begin_native"),
        ("levelscript_on_encounter_battle_part_end_native.json", "endfield.levelscript-on-encounter-battle-part-end-native.v1", "levelscript_on_encounter_battle_part_end_native"),
        ("levelscript_on_entity_cast_skill_native.json", "endfield.levelscript-on-entity-cast-skill-native.v1", "levelscript_on_entity_cast_skill_native"),
        ("levelscript_on_leader_enter_trigger_volume_list_native.json", "endfield.levelscript-on-leader-enter-trigger-volume-list-native.v1", "levelscript_on_leader_enter_trigger_volume_list_native"),
        ("levelscript_list_add_value_entity_ptr_native.json", "endfield.levelscript-list-add-value-entity-ptr-native.v1", "levelscript_list_add_value_entity_ptr_native"),
        ("levelscript_add_tracking_point_native.json", "endfield.levelscript-add-tracking-point-native.v1", "levelscript_add_tracking_point_native"),
        ("levelscript_set_forbid_map_teleport_native.json", "endfield.levelscript-set-forbid-map-teleport-native.v1", "levelscript_set_forbid_map_teleport_native"),
        ("levelscript_resume_spawner_native.json", "endfield.levelscript-resume-spawner-native.v1", "levelscript_resume_spawner_native"),
        ("levelscript_start_seq_loop_native.json", "endfield.levelscript-start-level-seq-loop-segment-native-contract.v1", "levelscript_start_seq_loop_native"),
        ("levelscript_entity_scanned_native.json", "endfield.levelscript-entity-scanned-native-contract.v1", "levelscript_entity_scanned_native"),
        ("levelscript_squad_fight_header_native.json", "endfield.levelscript-squad-fight-header-native-contract.v1", "levelscript_squad_fight_header_native"),
        ("levelscript_leader_enter_trigger_volume_native.json", "endfield.levelscript-leader-enter-trigger-volume-native-contract.v1", "levelscript_leader_enter_trigger_volume_native"),
        ("levelscript_squad_all_die_header_native.json", "endfield.levelscript-squad-all-die-header-native-contract.v1", "levelscript_squad_all_die_header_native"),
        ("levelscript_tracking_point_native.json", "endfield.levelscript-tracking-point-native-contract.v1", "levelscript_tracking_point_native"),
        ("levelscript_mission_changed_header_native.json", "endfield.levelscript-mission-changed-header-native-contract.v1", "levelscript_mission_changed_header_native"),
        ("levelscript_cutscene_teleport_native.json", "endfield.levelscript-cutscene-teleport-native-contract.v1", "levelscript_cutscene_teleport_native"),
        ("levelscript_manually_stop_guide_native.json", "endfield.levelscript-manually-stop-guide-native-contract.v1", "levelscript_manually_stop_guide_native"),
        ("levelscript_remove_tracking_point_native.json", "endfield.levelscript-remove-tracking-point-native-contract.v1", "levelscript_remove_tracking_point_native"),
        ("levelscript_get_is_leader_in_trigger_volume_native.json", "endfield.levelscript-get-is-leader-in-trigger-volume-native-contract.v1", "levelscript_get_is_leader_in_trigger_volume_native"),
        ("levelscript_send_lua_event1_native.json", "endfield.levelscript-send-lua-event1-native-contract.v1", "levelscript_send_lua_event1_native"),
        ("levelscript_start_subgame_countdown_native.json", "endfield.levelscript-start-subgame-countdown-native-contract.v1", "levelscript_start_subgame_countdown_native"),
        ("levelscript_show_start_toast_native.json", "endfield.levelscript-show-start-toast-native-contract.v1", "levelscript_show_start_toast_native"),
        ("levelscript_show_finish_toast_native.json", "endfield.levelscript-show-finish-toast-native-contract.v1", "levelscript_show_finish_toast_native"),
        ("levelscript_toggle_main_hud_ignore_native.json", "endfield.levelscript-toggle-main-hud-ignore-native-contract.v1", "levelscript_toggle_main_hud_ignore_native"),
        ("levelscript_show_chapter_panel_direct_native.json", "endfield.levelscript-show-chapter-panel-direct-native-contract.v1", "levelscript_show_chapter_panel_direct_native"),
        ("levelscript_show_chapter_completed_panel_native.json", "endfield.levelscript-show-chapter-completed-panel-native-contract.v1", "levelscript_show_chapter_completed_panel_native"),
        ("levelscript_switch_to_camera_native.json", "endfield.levelscript-switch-to-camera-native-contract.v1", "levelscript_switch_to_camera_native"),
        ("levelscript_start_track_camera_native.json", "endfield.levelscript-start-track-camera-native-contract.v1", "levelscript_start_track_camera_native"),
        ("levelscript_exit_camera_native.json", "endfield.levelscript-exit-camera-native-contract.v1", "levelscript_exit_camera_native"),
        ("levelscript_reset_follow_camera_native.json", "endfield.levelscript-reset-follow-camera-native-contract.v1", "levelscript_reset_follow_camera_native"),
        ("levelscript_fac_set_interact_locked_state_native.json", "endfield.levelscript-fac-set-interact-locked-state-native-contract.v1", "levelscript_fac_set_interact_locked_state_native"),
        ("levelscript_toggle_clear_screen_but_radio_v2_native.json", "endfield.levelscript-toggle-clear-screen-but-radio-v2-native-contract.v1", "levelscript_toggle_clear_screen_but_radio_v2_native"),
        ("levelscript_remove_npc_dialog_native.json", "endfield.levelscript-remove-npc-dialog-native-contract.v1", "levelscript_remove_npc_dialog_native"),
        ("levelscript_stop_subgame_countdown_by_handle_native.json", "endfield.levelscript-stop-subgame-countdown-by-handle-native-contract.v1", "levelscript_stop_subgame_countdown_by_handle_native"),
        ("levelscript_require_settlement_show_native.json", "endfield.levelscript-require-settlement-show-native-contract.v1", "levelscript_require_settlement_show_native"),
        ("levelscript_settlement_followon_native.json", "endfield.levelscript-settlement-followon-native-contract.v1", "levelscript_settlement_followon_native"),
        ("levelscript_bool_compare_native.json", "endfield.levelscript-bool-compare-native-contract.v1", "levelscript_bool_compare_native"),
        ("levelscript_fac_top_view_range_native.json", "endfield.levelscript-fac-top-view-range-native-contract.v1", "levelscript_fac_top_view_range_native"),
        ("levelscript_fac_build_effect_native.json", "endfield.levelscript-fac-build-effect-native-contract.v1", "levelscript_fac_build_effect_native"),
        ("levelscript_fac_change_building_native.json", "endfield.levelscript-fac-change-building-native-contract.v1", "levelscript_fac_change_building_native"),
        ("levelscript_npc_proxy_effect_native.json", "endfield.levelscript-npc-proxy-effect-native-contract.v1", "levelscript_npc_proxy_effect_native"),
        ("levelscript_npc_effect_native.json", "endfield.levelscript-npc-effect-native-contract.v1", "levelscript_npc_effect_native"),
        ("levelscript_block_battle_music_native.json", "endfield.levelscript-block-battle-music-native-contract.v1", "levelscript_block_battle_music_native"),
        ("levelscript_block_auto_music_change_cancel_native.json", "endfield.levelscript-block-auto-music-change-cancel-native-contract.v1", "levelscript_block_auto_music_change_cancel_native"),
        ("levelscript_fac_get_building_position_native.json", "endfield.levelscript-fac-get-building-position-native-contract.v1", "levelscript_fac_get_building_position_native"),
        ("levelscript_entity_hp_changed_native.json", "endfield.levelscript-entity-hp-changed-native-contract.v1", "levelscript_entity_hp_changed_native"),
        ("levelscript_settlement_upgrade_show_native.json", "endfield.levelscript-settlement-upgrade-show-native-contract.v1", "levelscript_settlement_upgrade_show_native"),
        ("levelscript_check_performance_ready_native.json", "endfield.levelscript-check-performance-ready-native-contract.v1", "levelscript_check_performance_ready_native"),
        ("levelscript_environment_enable_native.json", "endfield.levelscript-environment-enable-native-contract.v1", "levelscript_environment_enable_native"),
        ("levelscript_settlement_ready_performance_native.json", "endfield.levelscript-settlement-ready-performance-native-contract.v1", "levelscript_settlement_ready_performance_native"),
        ("levelscript_add_buffs_to_target_selves_native.json", "endfield.levelscript-add-buffs-to-target-selves-native-contract.v1", "levelscript_add_buffs_to_target_selves_native"),
        ("levelscript_set_squad_special_idle_enable_native.json", "endfield.levelscript-set-squad-special-idle-enable-native-contract.v1", "levelscript_set_squad_special_idle_enable_native"),
        ("levelscript_list_make_entity_ptr_native.json", "endfield.levelscript-list-make-entity-ptr-native-contract.v1", "levelscript_list_make_entity_ptr_native"),
        ("levelscript_getter_entity_ptr_native.json", "endfield.levelscript-getter-entity-ptr-native-contract.v1", "levelscript_getter_entity_ptr_native"),
        ("levelscript_getter_levelscript_ptr_native.json", "endfield.levelscript-getter-levelscript-ptr-native-contract.v1", "levelscript_getter_levelscript_ptr_native"),
        ("levelscript_set_enemy_ui_show_range_native.json", "endfield.levelscript-set-enemy-ui-show-range-native-contract.v1", "levelscript_set_enemy_ui_show_range_native"),
        ("levelscript_set_list_buff_native.json", "endfield.levelscript-set-list-buff-native-contract.v1", "levelscript_set_list_buff_native"),
        ("levelscript_entity_to_string_native.json", "endfield.levelscript-entity-to-string-native-contract.v1", "levelscript_entity_to_string_native"),
        ("levelscript_is_look_at_point_in_screen_native.json", "endfield.levelscript-is-look-at-point-in-screen-native-contract.v1", "levelscript_is_look_at_point_in_screen_native"),
        ("levelscript_getter_list_buff_native.json", "endfield.levelscript-getter-list-buff-native-contract.v1", "levelscript_getter_list_buff_native"),
        ("levelscript_get_cur_squad_all_dead_native.json", "endfield.levelscript-get-cur-squad-all-dead-native-contract.v1", "levelscript_get_cur_squad_all_dead_native"),
        ("levelscript_get_character_template_id_native.json", "endfield.levelscript-get-character-template-id-native-contract.v1", "levelscript_get_character_template_id_native"),
        ("levelscript_float_getter_int_to_float_native.json", "endfield.levelscript-float-getter-int-to-float-native-contract.v1", "levelscript_float_getter_int_to_float_native"),
        ("levelscript_float_getter_plus_native.json", "endfield.levelscript-float-getter-plus-native-contract.v1", "levelscript_float_getter_plus_native"),
        ("levelscript_bool_getter_mult_or_native.json", "endfield.levelscript-bool-getter-mult-or-native.v1", "levelscript_bool_getter_mult_or_native"),
        ("levelscript_play_voice_narrative_native.json", "endfield.levelscript-play-voice-narrative-native-contract.v1", "levelscript_play_voice_narrative_native"),
        ("levelscript_scripted_char_teleport_to_native.json", "endfield.levelscript-scripted-char-teleport-to-native-contract.v1", "levelscript_scripted_char_teleport_to_native"),
        ("levelscript_scripted_char_patrol_start_native.json", "endfield.levelscript-scripted-char-patrol-start-native-contract.v1", "levelscript_scripted_char_patrol_start_native"),
        ("levelscript_stop_char_scripted_mode_native.json", "endfield.levelscript-stop-char-scripted-mode-native-contract.v1", "levelscript_stop_char_scripted_mode_native"),
        ("levelscript_on_any_entity_die_native.json", "endfield.levelscript-on-any-entity-die-native-contract.v1", "levelscript_on_any_entity_die_native"),
        ("levelscript_on_start_script_controlled_char_mode_native.json", "endfield.levelscript-on-start-script-controlled-char-mode-native-contract.v1", "levelscript_on_start_script_controlled_char_mode_native"),
        ("levelscript_on_spawner_pause_native.json", "endfield.levelscript-on-spawner-pause-native-contract.v1", "levelscript_on_spawner_pause_native"),
        ("levelscript_building_pos_hint_show_native.json", "endfield.levelscript-building-pos-hint-show-native-contract.v1", "levelscript_building_pos_hint_show_native"),
        ("levelscript_building_pos_hint_hide_native.json", "endfield.levelscript-building-pos-hint-hide-native-contract.v1", "levelscript_building_pos_hint_hide_native"),
        ("levelscript_fac_guide_hint_enable_native.json", "endfield.levelscript-fac-guide-hint-enable-native-contract.v1", "levelscript_fac_guide_hint_enable_native"),
        ("levelscript_npc_get_pack_anim_has_clean_native.json", "endfield.levelscript-npc-get-pack-anim-has-clean-native-contract.v1", "levelscript_npc_get_pack_anim_has_clean_native"),
        ("levelscript_on_encounter_intro_part_end_native.json", "endfield.levelscript-on-encounter-intro-part-end-native.v1", "levelscript_on_encounter_intro_part_end_native"),
        ("levelscript_on_npc_dirty_block_cleaned_native.json", "endfield.levelscript-on-npc-dirty-block-cleaned-native.v1", "levelscript_on_npc_dirty_block_cleaned_native"),
        ("levelscript_on_server_dialog_exit_native.json", "endfield.levelscript-on-server-dialog-exit-native.v1", "levelscript_on_server_dialog_exit_native"),
        ("levelscript_on_level_reset_native.json", "endfield.levelscript-on-level-reset-native.v1", "levelscript_on_level_reset_native"),
        ("levelscript_on_specific_entity_die_native.json", "endfield.levelscript-on-specific-entity-die-native.v1", "levelscript_on_specific_entity_die_native"),
        ("levelscript_on_sub_game_start_native.json", "endfield.levelscript-on-sub-game-start-native.v1", "levelscript_on_sub_game_start_native"),
        ("levelscript_on_npc_patrol_checkpoint_reach_native.json", "endfield.levelscript-on-npc-patrol-checkpoint-reach-native.v1", "levelscript_on_npc_patrol_checkpoint_reach_native"),
        ("levelscript_on_spawner_group_complete_native.json", "endfield.levelscript-on-spawner-group-complete-native.v1", "levelscript_on_spawner_group_complete_native"),
        ("levelscript_set_decoration_animator_int_native.json", "endfield.levelscript-set-decoration-animator-int-native-contract.v1", "levelscript_set_decoration_animator_int_native"),
        ("levelscript_set_decoration_view_state_native.json", "endfield.levelscript-set-decoration-view-state-native-contract.v1", "levelscript_set_decoration_view_state_native"),
        ("levelscript_entity_move_to_with_speed_native.json", "endfield.levelscript-entity-move-to-with-speed-native-contract.v1", "levelscript_entity_move_to_with_speed_native"),
        ("levelscript_start_fmv_and_teleport_native.json", "endfield.levelscript-start-fmv-and-teleport-native-contract.v1", "levelscript_start_fmv_and_teleport_native"),
        ("levelscript_disable_hud_fade_native.json", "endfield.levelscript-disable-hud-fade-native-contract.v1", "levelscript_disable_hud_fade_native"),
        ("levelscript_stop_effect_on_npc_proxy_native.json", "endfield.levelscript-stop-effect-on-npc-proxy-native.v1", "levelscript_stop_effect_on_npc_proxy_native"),
        ("levelscript_npc_stop_cur_montage_native.json", "endfield.levelscript-npc-stop-cur-montage-native-contract.v1", "levelscript_npc_stop_cur_montage_native"),
        ("levelscript_set_main_char_hp_bar_active_native.json", "endfield.levelscript-set-main-char-hp-bar-active-native.v1", "levelscript_set_main_char_hp_bar_active_native"),
        ("levelscript_destroy_ability_entity_native.json", "endfield.levelscript-destroy-ability-entity-native-contract.v1", "levelscript_destroy_ability_entity_native"),
        ("levelscript_move_bamboo_last_native.json", "endfield.levelscript-move-bamboo-last-native-contract.v1", "levelscript_move_bamboo_last_native"),
        ("levelscript_is_endmin_gender_native.json", "endfield.levelscript-is-endmin-gender-native.v1", "levelscript_is_endmin_gender_native"),
        ("levelscript_teleport_gameplay_npc_native.json", "endfield.levelscript-teleport-gameplay-npc-native.v1", "levelscript_teleport_gameplay_npc_native"),
        ("levelscript_apply_movement_setting_modifier_native.json", "endfield.levelscript-apply-movement-setting-modifier-native.v1", "levelscript_apply_movement_setting_modifier_native"),
        ("levelscript_toggle_ui_dev_only_native.json", "endfield.levelscript-toggle-ui-dev-only-native.v1", "levelscript_toggle_ui_dev_only_native"),
        ("levelscript_start_cutscene_hide_scene_object_native.json", "endfield.levelscript-start-cutscene-hide-scene-object-native.v1", "levelscript_start_cutscene_hide_scene_object_native"),
        ("levelscript_start_cutscene_control_scene_object_native.json", "endfield.levelscript-start-cutscene-control-scene-object-native.v1", "levelscript_start_cutscene_control_scene_object_native"),
        ("levelscript_set_squad_icon_active_native.json", "endfield.levelscript-set-squad-icon-active-native-contract.v1", "levelscript_set_squad_icon_active_native"),
        ("levelscript_skip_entity_die_display_native.json", "endfield.levelscript-skip-entity-die-display-native-contract.v1", "levelscript_skip_entity_die_display_native"),
        ("levelscript_get_script_task_objective_is_completed_native.json", "endfield.levelscript-get-script-task-objective-is-completed-native.v1", "levelscript_get_script_task_objective_is_completed_native"),
        ("levelscript_on_any_enemy_poise_zero_native.json", "endfield.levelscript-on-any-enemy-poise-zero-native-contract.v1", "levelscript_on_any_enemy_poise_zero_native"),
        ("levelscript_on_any_enemy_poise_knot_break_native.json", "endfield.levelscript-on-any-enemy-poise-knot-break-native-contract.v1", "levelscript_on_any_enemy_poise_knot_break_native"),
        ("levelscript_on_aether_lock_endpoint_scanned_native.json", "endfield.levelscript-on-aether-lock-endpoint-scanned-native.v1", "levelscript_on_aether_lock_endpoint_scanned_native"),
        ("levelscript_on_cutscene_exit_native.json", "endfield.levelscript-on-cutscene-exit-native.v1", "levelscript_on_cutscene_exit_native"),
        ("levelscript_on_entity_die_native.json", "endfield.levelscript-on-entity-die-native.v1", "levelscript_on_entity_die_native"),
        ("levelscript_on_blight_miasma_weak_guide_native.json", "endfield.levelscript-on-blight-miasma-weak-guide-native.v1", "levelscript_on_blight_miasma_weak_guide_native"),
        ("levelscript_event_args_float_native.json", "endfield.levelscript-event-args-float-native-contract.v1", "levelscript_event_args_float_native"),
        ("levelscript_audio_cue_native.json", "endfield.levelscript-audio-cue-native-contract.v1", "levelscript_audio_cue_native"),
        ("levelscript_override_npc_dialog_native.json", "endfield.levelscript-override-npc-dialog-native-contract.v1", "levelscript_override_npc_dialog_native"),
    ):
        contract = json.loads((CONTRACTS_DIR / filename).read_bytes())
        if contract.get("schema") != schema or contract.get("status") != "exact-current-build":
            raise ActionMapCodecError(f"actionMap.nativeGate:contract-status={filename}")
        routes = contract.get("routes", [contract.get("route")])
        for route in routes:
            if not isinstance(route, dict):
                raise ActionMapCodecError(f"actionMap.nativeGate:contract-route={filename}")
            key = (route.get("codecFamily", route.get("family")), route.get("tag"))
            if key in required or not isinstance(key[0], str) or not isinstance(key[1], int):
                raise ActionMapCodecError(f"actionMap.nativeGate:contract-identity={filename}")
            required[key] = gate
    return required


def _require_selected_native(family: str, tag: int, layout: dict[str, Any]) -> None:
    """Keep selected native routes unavailable on build or body drift."""
    reviewed = _layouts().get((family, tag))
    if reviewed is None:
        return
    native_gate = reviewed.get("nativeGate")
    required = _required_native_gates().get((family, tag))
    if required is not None and native_gate != required:
        raise ActionMapCodecError(
            f"actionMap.nativeGate:missing-gate={family}:0x{tag:04x},required={required}"
        )
    if native_gate is None:
        return
    if native_gate == "levelscript_entity_scanned_native":
        audit = _entity_scanned_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.entityScannedNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_squad_fight_header_native":
        audit = _squad_fight_header_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.squadFightHeaderNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_leader_enter_trigger_volume_native":
        audit = _leader_enter_trigger_volume_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.leaderEnterTriggerVolumeNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_squad_all_die_header_native":
        audit = _squad_all_die_header_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.squadAllDieHeaderNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_tracking_point_native":
        audit = _tracking_point_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.trackingPointNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_mission_changed_header_native":
        audit = _mission_changed_header_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.missionChangedHeaderNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_cutscene_teleport_native":
        audit = _cutscene_teleport_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.cutsceneTeleportNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_manually_stop_guide_native":
        audit = _manually_stop_guide_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.manuallyStopGuideNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_remove_tracking_point_native":
        audit = _remove_tracking_point_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.removeTrackingPointNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_get_is_leader_in_trigger_volume_native":
        audit = _get_is_leader_in_trigger_volume_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.getIsLeaderInTriggerVolumeNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_send_lua_event1_native":
        audit = _send_lua_event1_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.sendLuaEvent1Native: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_start_subgame_countdown_native":
        audit = _start_subgame_countdown_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.startSubGameCountDownNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate in (
        "levelscript_show_start_toast_native",
        "levelscript_show_finish_toast_native",
        "levelscript_toggle_main_hud_ignore_native",
        "levelscript_show_chapter_panel_direct_native",
        "levelscript_show_chapter_completed_panel_native",
        "levelscript_switch_to_camera_native",
        "levelscript_start_track_camera_native",
        "levelscript_exit_camera_native",
        "levelscript_reset_follow_camera_native",
        "levelscript_fac_set_interact_locked_state_native",
        "levelscript_toggle_clear_screen_but_radio_v2_native",
        "levelscript_remove_npc_dialog_native",
        "levelscript_stop_subgame_countdown_by_handle_native",
    ):
        audit = (
            _show_start_toast_native_audit() if native_gate == "levelscript_show_start_toast_native"
            else _show_finish_toast_native_audit() if native_gate == "levelscript_show_finish_toast_native"
            else _toggle_main_hud_ignore_native_audit() if native_gate == "levelscript_toggle_main_hud_ignore_native"
            else _show_chapter_panel_direct_native_audit() if native_gate == "levelscript_show_chapter_panel_direct_native"
            else _show_chapter_completed_panel_native_audit() if native_gate == "levelscript_show_chapter_completed_panel_native"
            else _switch_to_camera_native_audit() if native_gate == "levelscript_switch_to_camera_native"
            else _start_track_camera_native_audit() if native_gate == "levelscript_start_track_camera_native"
            else _exit_camera_native_audit() if native_gate == "levelscript_exit_camera_native"
            else _reset_follow_camera_native_audit() if native_gate == "levelscript_reset_follow_camera_native"
            else _fac_set_interact_locked_state_native_audit() if native_gate == "levelscript_fac_set_interact_locked_state_native"
            else _toggle_clear_screen_but_radio_v2_native_audit() if native_gate == "levelscript_toggle_clear_screen_but_radio_v2_native"
            else _remove_npc_dialog_native_audit() if native_gate == "levelscript_remove_npc_dialog_native"
            else _stop_subgame_countdown_by_handle_native_audit()
        )
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                f"actionMap.{native_gate}: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_require_settlement_show_native":
        audit = _require_settlement_show_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.requireSettlementShowNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_settlement_followon_native":
        audit = _settlement_followon_native_audit()
        selected = next(
            (row for row in audit.get("routes", [])
             if row.get("family") == family and row.get("tag") == tag), None,
        )
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.settlementFollowonNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_bool_compare_native":
        audit = _bool_compare_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.boolCompareNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_fac_top_view_range_native":
        audit = _fac_top_view_range_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.facTopViewRangeNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_fac_build_effect_native":
        audit = _fac_build_effect_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.facBuildEffectNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_fac_change_building_native":
        audit = _fac_change_building_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.facChangeBuildingNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_npc_proxy_effect_native":
        audit = _npc_proxy_effect_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.npcProxyEffectNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate in {
        "levelscript_npc_effect_native",
        "levelscript_block_battle_music_native",
        "levelscript_block_auto_music_change_cancel_native",
        "levelscript_fac_get_building_position_native",
        "levelscript_entity_hp_changed_native",
        "levelscript_settlement_upgrade_show_native",
        "levelscript_check_performance_ready_native",
        "levelscript_environment_enable_native",
        "levelscript_settlement_ready_performance_native",
        "levelscript_add_buffs_to_target_selves_native",
        "levelscript_set_squad_special_idle_enable_native",
        "levelscript_list_make_entity_ptr_native",
        "levelscript_getter_entity_ptr_native",
        "levelscript_getter_levelscript_ptr_native",
        "levelscript_set_enemy_ui_show_range_native",
        "levelscript_set_list_buff_native",
        "levelscript_entity_to_string_native",
        "levelscript_is_look_at_point_in_screen_native",
        "levelscript_getter_list_buff_native",
        "levelscript_get_cur_squad_all_dead_native",
        "levelscript_get_character_template_id_native",
        "levelscript_float_getter_int_to_float_native",
        "levelscript_float_getter_plus_native",
        "levelscript_bool_getter_mult_or_native",
        "levelscript_play_voice_narrative_native",
        "levelscript_scripted_char_teleport_to_native",
        "levelscript_scripted_char_patrol_start_native",
        "levelscript_stop_char_scripted_mode_native",
        "levelscript_on_any_entity_die_native",
        "levelscript_on_start_script_controlled_char_mode_native",
        "levelscript_on_spawner_pause_native",
        "levelscript_building_pos_hint_show_native",
        "levelscript_building_pos_hint_hide_native",
        "levelscript_fac_guide_hint_enable_native",
        "levelscript_get_script_task_objective_is_completed_native",
        "levelscript_set_decoration_animator_int_native",
        "levelscript_set_decoration_view_state_native",
        "levelscript_entity_move_to_with_speed_native",
        "levelscript_start_fmv_and_teleport_native",
        "levelscript_disable_hud_fade_native",
        "levelscript_stop_effect_on_npc_proxy_native",
        "levelscript_npc_stop_cur_montage_native",
        "levelscript_set_main_char_hp_bar_active_native",
        "levelscript_destroy_ability_entity_native",
        "levelscript_move_bamboo_last_native",
        "levelscript_is_endmin_gender_native",
        "levelscript_apply_movement_setting_modifier_native",
        "levelscript_toggle_ui_dev_only_native",
        "levelscript_start_cutscene_hide_scene_object_native",
        "levelscript_start_cutscene_control_scene_object_native",
        "levelscript_set_squad_icon_active_native",
        "levelscript_skip_entity_die_display_native",
        "levelscript_npc_get_pack_anim_has_clean_native",
        "levelscript_on_any_enemy_poise_zero_native",
        "levelscript_on_any_enemy_poise_knot_break_native",
    }:
        validators = {
            "levelscript_npc_effect_native": _npc_effect_native_audit,
            "levelscript_block_battle_music_native": _block_battle_music_native_audit,
            "levelscript_block_auto_music_change_cancel_native": _block_auto_music_change_cancel_native_audit,
            "levelscript_fac_get_building_position_native": _fac_get_building_position_native_audit,
            "levelscript_entity_hp_changed_native": _entity_hp_changed_native_audit,
            "levelscript_settlement_upgrade_show_native": _settlement_upgrade_show_native_audit,
            "levelscript_check_performance_ready_native": _check_performance_ready_native_audit,
            "levelscript_environment_enable_native": _environment_enable_native_audit,
            "levelscript_settlement_ready_performance_native": _settlement_ready_performance_native_audit,
            "levelscript_add_buffs_to_target_selves_native": _add_buffs_to_target_selves_native_audit,
            "levelscript_set_squad_special_idle_enable_native": _set_squad_special_idle_enable_native_audit,
            "levelscript_list_make_entity_ptr_native": _list_make_entity_ptr_native_audit,
            "levelscript_getter_entity_ptr_native": _getter_entity_ptr_native_audit,
            "levelscript_getter_levelscript_ptr_native": _getter_levelscript_ptr_native_audit,
            "levelscript_set_enemy_ui_show_range_native": _set_enemy_ui_show_range_native_audit,
            "levelscript_set_list_buff_native": _set_list_buff_native_audit,
            "levelscript_entity_to_string_native": _entity_to_string_native_audit,
            "levelscript_is_look_at_point_in_screen_native": _is_look_at_point_in_screen_native_audit,
            "levelscript_getter_list_buff_native": _getter_list_buff_native_audit,
            "levelscript_get_cur_squad_all_dead_native": _get_cur_squad_all_dead_native_audit,
            "levelscript_get_character_template_id_native": _get_character_template_id_native_audit,
            "levelscript_float_getter_int_to_float_native": _float_getter_int_to_float_native_audit,
            "levelscript_float_getter_plus_native": _float_getter_plus_native_audit,
            "levelscript_bool_getter_mult_or_native": _bool_getter_mult_or_native_audit,
            "levelscript_play_voice_narrative_native": _play_voice_narrative_native_audit,
            "levelscript_scripted_char_teleport_to_native": _scripted_char_teleport_to_native_audit,
            "levelscript_scripted_char_patrol_start_native": _scripted_char_patrol_start_native_audit,
            "levelscript_stop_char_scripted_mode_native": _stop_char_scripted_mode_native_audit,
            "levelscript_on_any_entity_die_native": _on_any_entity_die_native_audit,
            "levelscript_on_start_script_controlled_char_mode_native": _on_start_script_controlled_char_mode_native_audit,
            "levelscript_on_spawner_pause_native": _on_spawner_pause_native_audit,
            "levelscript_building_pos_hint_show_native": _building_pos_hint_show_native_audit,
            "levelscript_building_pos_hint_hide_native": _building_pos_hint_hide_native_audit,
            "levelscript_fac_guide_hint_enable_native": _fac_guide_hint_enable_native_audit,
            "levelscript_get_script_task_objective_is_completed_native": _get_script_task_objective_is_completed_native_audit,
            "levelscript_set_decoration_animator_int_native": _set_decoration_animator_int_native_audit,
            "levelscript_set_decoration_view_state_native": _set_decoration_view_state_native_audit,
            "levelscript_entity_move_to_with_speed_native": _entity_move_to_with_speed_native_audit,
            "levelscript_start_fmv_and_teleport_native": _start_fmv_and_teleport_native_audit,
            "levelscript_disable_hud_fade_native": _disable_hud_fade_native_audit,
            "levelscript_stop_effect_on_npc_proxy_native": _stop_effect_on_npc_proxy_native_audit,
            "levelscript_npc_stop_cur_montage_native": _npc_stop_cur_montage_native_audit,
            "levelscript_set_main_char_hp_bar_active_native": _set_main_char_hp_bar_active_native_audit,
            "levelscript_destroy_ability_entity_native": _destroy_ability_entity_native_audit,
            "levelscript_move_bamboo_last_native": _move_bamboo_last_native_audit,
            "levelscript_is_endmin_gender_native": _is_endmin_gender_native_audit,
            "levelscript_apply_movement_setting_modifier_native": _apply_movement_setting_modifier_native_audit,
            "levelscript_toggle_ui_dev_only_native": _toggle_ui_dev_only_native_audit,
            "levelscript_start_cutscene_hide_scene_object_native": _start_cutscene_hide_scene_object_native_audit,
            "levelscript_start_cutscene_control_scene_object_native": _start_cutscene_control_scene_object_native_audit,
            "levelscript_set_squad_icon_active_native": _set_squad_icon_active_native_audit,
            "levelscript_skip_entity_die_display_native": _skip_entity_die_display_native_audit,
            "levelscript_npc_get_pack_anim_has_clean_native": _npc_get_pack_anim_has_clean_native_audit,
            "levelscript_on_any_enemy_poise_zero_native": _on_any_enemy_poise_zero_native_audit,
            "levelscript_on_any_enemy_poise_knot_break_native": _on_any_enemy_poise_knot_break_native_audit,
        }
        audit = validators[native_gate]()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                f"actionMap.selectedNative: family={family},tag=0x{tag:04x},"
                f"gate={native_gate},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_event_args_float_native":
        audit = _event_args_float_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.eventArgsFloatNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_audio_cue_native":
        audit = _audio_cue_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.audioCueNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_override_npc_dialog_native":
        audit = _override_npc_dialog_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.overrideNpcDialogNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_finish_scene_effect_native":
        audit = _finish_scene_effect_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.finishSceneNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_npc_proxy_patrol_stop_native":
        audit = _npc_proxy_patrol_stop_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.npcPatrolNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_post_audio_status_native":
        audit = _post_audio_status_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.postAudioStatusNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_entities_visibility_native":
        audit = _entities_visibility_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.entitiesVisibilityNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_track_camera_native":
        audit = _track_camera_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.trackCameraNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_enemy_patrol_start_native":
        audit = _enemy_patrol_start_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.enemyPatrolStartNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_archery_stage_native":
        audit = _archery_stage_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.archeryStageNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_typhoea_chip_id_native":
        audit = _typhoea_chip_id_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.typhoeaChipIdNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_finish_buffs_native":
        audit = _finish_buffs_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.finishBuffsNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_mark_task_condition_failed_native":
        audit = _mark_task_condition_failed_native_audit()
        selected = audit.get("route")
        selected_fields = (
            [[name, "int32" if kind == "enum32" else kind] for name, kind in selected["fields"]]
            if isinstance(selected, dict) else None
        )
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected_fields != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.markTaskConditionFailedNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_archery_advanced_headers_native":
        audit = _archery_advanced_headers_native_audit()
        selected = next(
            (route for route in audit.get("routes", [])
             if route.get("family") == family and route.get("tag") == tag),
            None,
        )
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.archeryAdvancedHeadersNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_on_train_level_event_native":
        audit = _on_train_level_event_native_audit()
        selected = next(
            (route for route in audit.get("routes", [])
             if route.get("family") == family and route.get("tag") == tag),
            None,
        )
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.onTrainLevelEventNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate in {
        "levelscript_on_map_var_changed_native",
        "levelscript_on_enemy_in_fight_native",
        "levelscript_on_enemy_take_last_attack_damage_native",
        "levelscript_on_spell_infliction_native",
        "levelscript_on_spawner_entity_spawn_native",
        "levelscript_on_spawner_group_begin_native",
        "levelscript_on_spawner_start_native",
        "levelscript_on_spell_abnormal_start_native",
        "levelscript_on_physical_infliction_native",
        "levelscript_on_bb_variable_changed_native",
        "levelscript_on_aether_lock_endpoint_scanned_native",
        "levelscript_on_cutscene_exit_native",
        "levelscript_on_encounter_intro_part_end_native",
        "levelscript_on_npc_dirty_block_cleaned_native",
        "levelscript_on_server_dialog_exit_native",
        "levelscript_on_level_reset_native",
        "levelscript_on_specific_entity_die_native",
        "levelscript_on_sub_game_start_native",
        "levelscript_on_npc_patrol_checkpoint_reach_native",
        "levelscript_on_spawner_group_complete_native",
        "levelscript_teleport_gameplay_npc_native",
        "levelscript_on_entity_die_native",
        "levelscript_on_blight_miasma_weak_guide_native",
        "levelscript_on_physical_no_guard_native",
        "levelscript_on_spawner_wave_begin_native",
        "levelscript_on_spawner_entity_die_native",
        "levelscript_on_encounter_activated_native",
        "levelscript_on_encounter_battle_part_begin_native",
        "levelscript_on_encounter_battle_part_end_native",
        "levelscript_on_entity_cast_skill_native",
        "levelscript_on_leader_enter_trigger_volume_list_native",
        "levelscript_add_tracking_point_native",
        "levelscript_set_forbid_map_teleport_native",
        "levelscript_resume_spawner_native",
    }:
        audit = {
            "levelscript_on_map_var_changed_native": _on_map_var_changed_native_audit,
            "levelscript_on_enemy_in_fight_native": _on_enemy_in_fight_native_audit,
            "levelscript_on_enemy_take_last_attack_damage_native": _on_enemy_take_last_attack_damage_native_audit,
            "levelscript_on_spell_infliction_native": _on_spell_infliction_native_audit,
            "levelscript_on_spawner_entity_spawn_native": _on_spawner_entity_spawn_native_audit,
            "levelscript_on_spawner_group_begin_native": _on_spawner_group_begin_native_audit,
            "levelscript_on_spawner_start_native": _on_spawner_start_native_audit,
            "levelscript_on_spell_abnormal_start_native": _on_spell_abnormal_start_native_audit,
            "levelscript_on_physical_infliction_native": _on_physical_infliction_native_audit,
            "levelscript_on_bb_variable_changed_native": _on_bb_variable_changed_native_audit,
            "levelscript_on_aether_lock_endpoint_scanned_native": _on_aether_lock_endpoint_scanned_native_audit,
            "levelscript_on_cutscene_exit_native": _on_cutscene_exit_native_audit,
            "levelscript_on_encounter_intro_part_end_native": _on_encounter_intro_part_end_native_audit,
            "levelscript_on_npc_dirty_block_cleaned_native": _on_npc_dirty_block_cleaned_native_audit,
            "levelscript_on_server_dialog_exit_native": _on_server_dialog_exit_native_audit,
            "levelscript_on_level_reset_native": _on_level_reset_native_audit,
            "levelscript_on_specific_entity_die_native": _on_specific_entity_die_native_audit,
            "levelscript_on_sub_game_start_native": _on_sub_game_start_native_audit,
            "levelscript_on_npc_patrol_checkpoint_reach_native": _on_npc_patrol_checkpoint_reach_native_audit,
            "levelscript_on_spawner_group_complete_native": _on_spawner_group_complete_native_audit,
            "levelscript_teleport_gameplay_npc_native": _teleport_gameplay_npc_native_audit,
            "levelscript_on_entity_die_native": _on_entity_die_native_audit,
            "levelscript_on_blight_miasma_weak_guide_native": _on_blight_miasma_weak_guide_native_audit,
            "levelscript_on_physical_no_guard_native": _on_physical_no_guard_native_audit,
            "levelscript_on_spawner_wave_begin_native": _on_spawner_wave_begin_native_audit,
            "levelscript_on_spawner_entity_die_native": _on_spawner_entity_die_native_audit,
            "levelscript_on_encounter_activated_native": _on_encounter_activated_native_audit,
            "levelscript_on_encounter_battle_part_begin_native": _on_encounter_battle_part_begin_native_audit,
            "levelscript_on_encounter_battle_part_end_native": _on_encounter_battle_part_end_native_audit,
            "levelscript_on_entity_cast_skill_native": _on_entity_cast_skill_native_audit,
            "levelscript_on_leader_enter_trigger_volume_list_native": _on_leader_enter_trigger_volume_list_native_audit,
            "levelscript_add_tracking_point_native": _add_tracking_point_native_audit,
            "levelscript_set_forbid_map_teleport_native": _set_forbid_map_teleport_native_audit,
            "levelscript_resume_spawner_native": _resume_spawner_native_audit,
        }[native_gate]()
        selected = next(
            (route for route in audit.get("routes", [])
             if route.get("family") == family and route.get("tag") == tag),
            None,
        )
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.selectedLevelEventNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_list_add_value_entity_ptr_native":
        audit = _list_add_value_entity_ptr_native_audit()
        selected = next(
            (route for route in audit.get("routes", [])
             if route.get("family") == family and route.get("tag") == tag),
            None,
        )
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.listAddValueEntityPtrNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_start_seq_loop_native":
        audit = _start_seq_loop_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.startSeqLoopNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_getter_int_native":
        from scripts.game_data.levelscript_getter_int_native import (
            load_current_getter_int_native,
        )

        selected, audit = load_current_getter_int_native()
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("codecFamily") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.getterIntNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_getter_compare_native":
        audit = _getter_compare_native_audit()
        selected = next(
            (route for route in audit.get("routes", [])
             if route.get("family") == family and route.get("tag") == tag),
            None,
        )
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.getterCompareNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_get_mission_state_native":
        audit = _get_mission_state_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.getMissionStateNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_water_height_native":
        audit = _water_height_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.waterHeightNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate == "levelscript_set_fac_mode_native":
        audit = _set_fac_mode_native_audit()
        selected = audit.get("route")
        if (
            audit.get("status") != "validated"
            or selected is None
            or selected.get("family") != family
            or selected.get("tag") != tag
            or selected.get("wrapperName") != reviewed.get("wrapperName")
            or selected.get("fields") != reviewed.get("fields")
            or layout.get("wrapperName") != reviewed.get("wrapperName")
            or layout.get("fields") != reviewed.get("fields")
        ):
            raise ActionMapCodecError(
                "actionMap.setFacModeNative: "
                f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
                f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
        return
    if native_gate != "levelscript_header_native":
        raise ActionMapCodecError(
            f"actionMap.headerNative:unsupported-gate={native_gate}"
        )
    from scripts.game_data.levelscript_header_native import load_current_header_native

    routes, audit = load_current_header_native()
    selected = routes.get(tag) if routes is not None else None
    if (
        audit.get("status") != "validated"
        or selected is None
        or selected.get("wrapperName") != reviewed.get("wrapperName")
        or selected.get("fields") != reviewed.get("fields")
        or layout.get("wrapperName") != reviewed.get("wrapperName")
        or layout.get("fields") != reviewed.get("fields")
    ):
        raise ActionMapCodecError(
            "actionMap.headerNative: "
            f"family={family},tag=0x{tag:04x},status={audit.get('status')},"
            f"check={audit.get('failedCheck')},detail={audit.get('detail')}"
        )


#: Fixed-width primitives a derived declaration can name directly.  These are
#: written raw, with no member-count header, exactly as the reviewed rows read
#: `int32` and `float32`.
_DERIVED_SCALARS = {
    "int8": "<b", "uint8": "<B", "byte": "<B", "sbyte": "<b",
    "int16": "<h", "uint16": "<H", "short": "<h", "ushort": "<H",
    "int": "<i", "uint": "<I", "long": "<q", "ulong": "<Q",
    "int64": "<q", "uint64": "<Q", "uint32": "<I",
    "float32": "<f", "float": "<f", "double": "<d", "char": "<H",
    # A stepped Unity keyframe tangent is +/-Infinity, so this width is read
    # without the finiteness check the ordinary float carries.
    "floatAllowInfinite": "<f",
}


#: Unity math types are plain unmanaged structs written as raw floats.
_UNITY_VECTORS = {
    "Quaternion": ("<ffff", ("x", "y", "z", "w")),
    "Vector4": ("<ffff", ("x", "y", "z", "w")),
    "Vector2Int": ("<ii", ("x", "y")),
    "Vector3Int": ("<iii", ("x", "y", "z")),
    "Color": ("<ffff", ("r", "g", "b", "a")),
    "Color32": ("<BBBB", ("r", "g", "b", "a")),
}


def _align_up(offset: int, alignment: int) -> int:
    """Round `offset` up to a multiple of `alignment`, as .NET lays out fields."""

    if alignment <= 1:
        return offset
    remainder = offset % alignment
    return offset if remainder == 0 else offset + (alignment - remainder)


class _NotDeclared:
    """Sentinel: no derived declaration covers this kind.

    A distinct object rather than `None`, because `None` is a real decoded
    value here -- a null struct or a null list.
    """

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return "<not-declared>"


_NOT_DECLARED = _NotDeclared()


def _split_generic_arguments(text: str) -> list[str]:
    """Split `a,b` at depth zero, so a nested `List<x,y>` stays one argument."""

    parts: list[str] = []
    depth = 0
    current = ""
    for char in text:
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
            continue
        current += char
    if current:
        parts.append(current)
    return parts


#: `Beyond.SerializeFieldDictionary<K,V>` and its `Paired`/`Sorted` siblings
#: each have a registered `MemoryPackFormatter`, so their wire form is not the
#: bare counted map that `Dictionary<K,V>` writes: the formatter emits the
#: one-member object header first, and its null is the one-byte `0xff` marker
#: rather than a four-byte `ff ff ff ff` count. `_Cursor.declared_inner` owns
#: that header; these heads are still listed as counted containers so they
#: route there instead of through the generic null marker, which would
#: misread a legitimate count byte.
SERIALIZE_FIELD_DICTIONARY_HEADS = (
    "SerializeFieldDictionary",
    "SerializeFieldDictionaryPaired",
    "SerializeFieldDictionarySorted",
)


def _serialize_field_dictionary_arguments(kind: str) -> list[str] | None:
    """The `K, V` of a `SerializeFieldDictionary`-family kind, or None."""

    for head in SERIALIZE_FIELD_DICTIONARY_HEADS:
        pair = _generic_argument(kind, head)
        if pair is None:
            continue
        arguments = _split_generic_arguments(pair)
        return arguments if len(arguments) == 2 else None
    return None


def _is_counted_container(kind: str) -> bool:
    """Whether a kind is routed to the declared container reader.

    `List<T>`, `T[]` and `Dictionary<K,V>` are written as a nullable count and
    then their elements. The `SerializeFieldDictionary` family carries a
    one-member object header before that count; it is routed here too so the
    generic null marker never sees it.
    """

    if kind.endswith("[]"):
        return True
    if _generic_argument(kind, "Nullable") is not None:
        return False
    return any(
        _generic_argument(kind, head) is not None
        for head in ("List", "Dictionary", *SERIALIZE_FIELD_DICTIONARY_HEADS)
    )


def _generic_argument(kind: str, head: str) -> str | None:
    """The single argument of `head<...>`, or None if `kind` is not that."""

    prefix = head + "<"
    if not kind.startswith(prefix) or not kind.endswith(">"):
        return None
    return kind[len(prefix) : -1]


class Declarations:
    """Derived declarations a caller opts into, at the `direct` tier.

    `scripts.game_data.levelscript_union_layouts` derives the full union table
    plus the structs and enums it refers to from the build's managed image.
    Those rows are corroborated on every reviewed row but are not read from
    the native dispatcher, so they never load by default: a caller passes them
    in, and by doing so accepts that its result is `direct` rather than
    `exact`. Passing nothing leaves this codec byte-identical to the reviewed
    contract alone.
    """

    def __init__(
        self,
        layouts: dict[tuple[str, int], dict[str, Any]],
        structs: dict[str, dict[str, Any]],
        enums: dict[str, str],
    ) -> None:
        self.layouts = layouts
        self.structs = structs
        self.enums = enums

    @classmethod
    def from_report(cls, report: dict[str, Any]) -> "Declarations":
        """Build from a `levelscript_union_layouts` report."""

        if report.get("evidenceBoundary") != "direct":
            raise ActionMapCodecError(
                "actionMap.declarations:unexpected-evidence-boundary="
                f"{report.get('evidenceBoundary')}"
            )
        layouts = {
            (family, row["tag"]): row
            for family, rows in (report.get("families") or {}).items()
            for row in rows
        }
        return cls(layouts, report.get("structs") or {}, report.get("enums") or {})


class _Cursor:
    def __init__(
        self,
        data: bytes,
        offset: int,
        declarations: Declarations | None = None,
    ):
        self.data = data
        self.offset = offset
        self.declarations = declarations

    def need(self, size: int, field: str) -> None:
        if self.offset < 0 or size < 0 or self.offset + size > len(self.data):
            raise ActionMapCodecError(f"{field}:truncated,offset={self.offset},size={size}")

    def byte(self, field: str) -> int:
        self.need(1, field)
        value = self.data[self.offset]
        self.offset += 1
        return value

    def i32(self, field: str) -> int:
        self.need(4, field)
        value = struct.unpack_from("<i", self.data, self.offset)[0]
        self.offset += 4
        return value

    def string(self, field: str) -> str | None:
        size = self.i32(field + ".length")
        if size == -1:
            return None
        if not 0 <= size <= 1 << 20:
            raise ActionMapCodecError(f"{field}:unsupported-length={size}")
        self.need(size, field)
        try:
            value = self.data[self.offset:self.offset + size].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ActionMapCodecError(f"{field}:invalid-utf8,offset={self.offset}") from exc
        self.offset += size
        return value

    def value(self, kind: str, field: str) -> Any:
        if kind == "Param<Deco_MountPoint>":
            audit = _set_decoration_view_state_native_audit()
            allowed = audit.get("enumValues", {}).get("Deco_MountPoint")
            if audit.get("status") != "validated" or not isinstance(allowed, list) or not allowed:
                raise ActionMapCodecError(f"{field}:decoration-mount-point-native={audit.get('status')}")
            result = self.value("Param<byte>", field)
            if result is not None and result["value"] not in allowed:
                raise ActionMapCodecError(f"{field}:unsupported-decoration-mount-point={result['value']}")
            return result
        if kind == "Param<BuildingPosHintShow.EBuildingRot>":
            audit = _building_pos_hint_show_native_audit()
            allowed = audit.get("enumValues", {}).get("BuildingPosHintShow.EBuildingRot")
            if audit.get("status") != "validated" or not isinstance(allowed, list) or not allowed:
                raise ActionMapCodecError(f"{field}:building-rotation-enum-native={audit.get('status')}")
            result = self.value("Param<int>", field)
            if result is not None and result["value"] not in allowed:
                raise ActionMapCodecError(f"{field}:unsupported-building-rotation={result['value']}")
            return result
        if kind == "Param<TaskObjectiveEnum>":
            return self.value("Param<int>", field)
        if kind == "Param<EnergyShardType>":
            return self.value("Param<int>", field)
        if kind == "Param<OnSpawnerEntitySpawn.FilterType>":
            return self.value("Param<int>", field)
        if kind == "Param<OnSpawnerEntityDie.FilterType>":
            return self.value("Param<int>", field)
        if kind == "Param<SkillTypeMask>":
            return self.value("Param<int>", field)
        if kind == "Param<EntityPtr>[]":
            decoded = params.decode_entity_ptr_getter_ref_array(self.data, self.offset)
            if decoded is None:
                raise ActionMapCodecError(f"{field}:unsupported-entity-ptr-array,offset={self.offset}")
            value, self.offset = decoded
            return value
        if kind == "Param<ScriptTaskPtr>":
            from .mark_task_condition_failed import decode_script_task_ptr_param

            detail, self.offset = decode_script_task_ptr_param(self.data, self.offset)
            return detail
        if kind == "GameCondition":
            return self.condition(field)
        if kind == "List<GameCondition>":
            count = self.i32(field + ".count")
            if count == -1:
                return None
            if not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            return [self.condition(f"{field}[{index}]") for index in range(count)]
        if kind == "int32":
            return self.i32(field)
        if kind == "string":
            return self.string(field)
        if kind == "bool":
            value = self.byte(field)
            if value not in (0, 1):
                raise ActionMapCodecError(f"{field}:invalid-bool={value}")
            return bool(value)
        if kind == "Vector3":
            self.need(12, field)
            values = struct.unpack_from("<fff", self.data, self.offset)
            self.offset += 12
            if not all(math.isfinite(value) for value in values):
                raise ActionMapCodecError(f"{field}:non-finite")
            return dict(zip(("x", "y", "z"), values))
        if kind == "Vector2":
            self.need(8, field)
            values = struct.unpack_from("<ff", self.data, self.offset)
            self.offset += 8
            if not all(math.isfinite(value) for value in values):
                raise ActionMapCodecError(f"{field}:non-finite")
            return dict(zip(("x", "y"), values))
        if kind == "float32":
            self.need(4, field)
            value = struct.unpack_from("<f", self.data, self.offset)[0]
            self.offset += 4
            if not math.isfinite(value):
                raise ActionMapCodecError(f"{field}:non-finite")
            return value
        if kind == "GameplayTag":
            self.need(4, field)
            value = struct.unpack_from("<I", self.data, self.offset)[0]
            self.offset += 4
            return {"raw": f"0x{value:08x}", "signed": struct.unpack("<i", struct.pack("<I", value))[0]}
        # Derived scalars and counted containers must resolve here, above the
        # generic null marker below. Both start with bytes that marker would
        # misread: an unmanaged byte can legitimately be 0xff, and a null
        # count is 0xff_ff_ff_ff, of which it would swallow exactly one byte.
        if self.declarations is not None:
            scalar = kind
            if scalar in self.declarations.enums:
                scalar = self.declarations.enums[scalar]
            if scalar in _DERIVED_SCALARS:
                return self.scalar(
                    _DERIVED_SCALARS[scalar], field,
                    allow_infinite=scalar == "floatAllowInfinite",
                )
            if _is_counted_container(kind):
                return self.declared_inner(kind, field)
        if kind == "Param<bool>[]":
            count = self.i32(field + ".count")
            if count == -1:
                return None
            if not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            return [self.value("Param<bool>", f"{field}[{index}]") for index in range(count)]
        if kind in ("List<int>", "List<ulong>", "List<string>", "List<Vector3>", "List<float>"):
            count = self.i32(field + ".count")
            if count == -1:
                return None
            if not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            if kind == "List<int>":
                reader = self.i32
            elif kind == "List<ulong>":
                def reader(name: str) -> int:
                    self.need(8, name)
                    value = struct.unpack_from("<Q", self.data, self.offset)[0]
                    self.offset += 8
                    return value
            elif kind == "List<string>":
                reader = self.string
            else:
                reader = lambda name: self.value(
                    "Vector3" if kind == "List<Vector3>" else "float32", name
                )
            return [reader(f"{field}[{index}]") for index in range(count)]
        if kind == "Param<NodeLookAtType>":
            audit = _is_look_at_point_in_screen_native_audit()
            if audit.get("status") != "validated":
                raise ActionMapCodecError(
                    "actionMap.isLookAtPointInScreenEnumNative: "
                    f"status={audit.get('status')},detail={audit.get('detail')}"
                )
            # The selected wrapper proves this enum is Int32-backed.
            return self.value("Param<int>", field)
        self.need(1, field)
        if self.data[self.offset] == 0xFF:
            self.offset += 1
            return None
        if kind == "Param<EnvironmentVolumePtr>":
            from .environment_volume_ptr import decode_environment_volume_ptr_param

            decoded = decode_environment_volume_ptr_param(self.data, self.offset)
            if decoded is None:
                raise ActionMapCodecError(f"{field}:invalid-environment-volume-ptr,offset={self.offset}")
            value, self.offset = decoded
            return value
        if kind == "Param<EnterDollyTrackCamera.TrackCameraMoveState>":
            from .track_camera import decode_move_state_param

            audit = _track_camera_native_audit()
            if audit.get("status") != "validated":
                raise ActionMapCodecError(
                    "actionMap.trackCameraEnumNative: "
                    f"status={audit.get('status')},detail={audit.get('detail')}"
                )
            enum_values = {value: name for name, value in audit["enumMembers"]}
            decoded, self.offset = decode_move_state_param(
                self.data, self.offset, enum_values,
            )
            return decoded
        if kind == "Param<ModelVisibleType>":
            from .visibility_action import decode_visible_source_param

            audit = _entities_visibility_native_audit()
            if audit.get("status") != "validated":
                raise ActionMapCodecError(
                    "actionMap.entitiesVisibilityEnumNative: "
                    f"status={audit.get('status')},detail={audit.get('detail')}"
                )
            enum_values = {value: name for name, value in audit["enumMembers"]}
            decoded, self.offset = decode_visible_source_param(
                self.data, self.offset, enum_values,
            )
            return decoded
        if kind in ("Param<List<PosRot>>", "Param<List<GameplayTag>>"):
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                return self.param_tail(None, field)
            if count == 0:
                return self.param_tail([], field)
            if kind == "Param<List<GameplayTag>>":
                # This element layout is still unreviewed; only PosRot is read.
                raise ActionMapCodecError(f"{field}:unsupported-GameplayTag-count={count}")
            if not 0 < count <= 4096:
                raise ActionMapCodecError(f"{field}:unsupported-PosRot-count={count}")
            return self.param_tail(self.pos_rot_list(count, field), field)
        if kind == "Param<CameraControllerBase>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 0xFF:
                raise ActionMapCodecError(
                    f"{field}:unsupported-camera-constant-members={marker}/{value_marker}"
                )
            return self.param_tail(None, field)
        if kind == "Param<CameraBlendCurveKey>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 1:
                raise ActionMapCodecError(
                    f"{field}:unsupported-curve-key-members={marker}/{value_marker}"
                )
            return self.param_tail({"key": self.string(field + ".value.key")}, field)
        if kind == "Param<CameraControlState>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 0xFF:
                raise ActionMapCodecError(
                    f"{field}:unsupported-camera-state-members={marker}/{value_marker}"
                )
            return self.param_tail(None, field)
        if kind == "Param<List<BlackboardKVPair>>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                values = None
            elif not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            else:
                values = []
                for index in range(count):
                    item = f"{field}.value[{index}]"
                    members = self.byte(item + ".memberCount")
                    if members != 4:
                        raise ActionMapCodecError(
                            f"{item}:unsupported-member-count={members}"
                        )
                    values.append({
                        "key": self.string(item + ".key"),
                        "useString": self.value("bool", item + ".useString"),
                        "valueFloat": self.value("float32", item + ".valueFloat"),
                        "valueString": self.string(item + ".valueString"),
                    })
            return self.param_tail(values, field)
        if kind == "Param<List<uint>>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                values = None
            elif not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            else:
                self.need(count * 4, field + ".value")
                values = list(struct.unpack_from(f"<{count}I", self.data, self.offset))
                self.offset += count * 4
            return self.param_tail(values, field)
        if kind in (
            "Param<List<int>>", "Param<List<ulong>>", "Param<List<string>>",
            "Param<List<Vector3>>", "Param<List<float>>",
        ):
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            value = self.value(kind[6:-1], field + ".value")
            return self.param_tail(value, field)
        if kind == "Param<List<LangKey>>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                value = None
            elif not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            else:
                value = []
                for index in range(count):
                    item = f"{field}.value[{index}]"
                    item_marker = self.byte(item + ".memberCount")
                    if item_marker != 1:
                        raise ActionMapCodecError(
                            f"{item}:unsupported-member-count={item_marker}"
                        )
                    value.append({"key": self.string(item + ".key")})
            return self.param_tail(value, field)
        if kind == "Param<GameplayTag>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(
                    f"{field}:unsupported-gameplay-tag-param-members={marker}"
                )
            return self.param_tail(
                {"tagId": self.i32(field + ".value.tagId")}, field
            )
        if kind in (
            "Param<CommonTrackingPointStyleType>",
            "Param<CommonTrackingType>",
        ):
            audit = _tracking_point_native_audit()
            allowed = audit.get("enumValues", {}).get(kind) if audit.get("status") == "validated" else None
            if not isinstance(allowed, list) or not allowed:
                raise ActionMapCodecError(f"{field}:tracking-point-enum-native={audit.get('status')}")
            result = self.value("Param<int>", field)
            if result["value"] not in allowed:
                raise ActionMapCodecError(f"{field}:unsupported-tracking-point-enum={result['value']}")
            return result
        if kind == "Param<OnMissionStateChanged.FilterMissionStateEnum>":
            audit = _mission_changed_header_native_audit()
            allowed = audit.get("enumValues", {}).get(kind) if audit.get("status") == "validated" else None
            if not isinstance(allowed, list) or not allowed:
                raise ActionMapCodecError(f"{field}:mission-filter-enum-native={audit.get('status')}")
            result = self.value("Param<int>", field)
            if result["value"] not in allowed:
                raise ActionMapCodecError(f"{field}:unsupported-mission-filter-enum={result['value']}")
            return result
        if kind == "Param<TeleportUIType>":
            audit = _cutscene_teleport_native_audit()
            allowed = audit.get("enumValues", {}).get(kind) if audit.get("status") == "validated" else None
            if not isinstance(allowed, list) or not allowed:
                raise ActionMapCodecError(f"{field}:teleport-ui-enum-native={audit.get('status')}")
            result = self.value("Param<int>", field)
            if result["value"] not in allowed:
                raise ActionMapCodecError(f"{field}:unsupported-teleport-ui-enum={result['value']}")
            return result
        if kind == "Param<ChapterEffectType>":
            # Both selected chapter-panel readers authenticate this same enum.
            audit = _show_chapter_panel_direct_native_audit()
            if audit.get("status") != "validated":
                audit = _show_chapter_completed_panel_native_audit()
            allowed = audit.get("enumValues", {}).get(kind) if audit.get("status") == "validated" else None
            if not isinstance(allowed, list) or not allowed:
                raise ActionMapCodecError(f"{field}:chapter-effect-enum-native={audit.get('status')}")
            result = self.value("Param<int>", field)
            if result["value"] not in allowed:
                raise ActionMapCodecError(f"{field}:unsupported-chapter-effect-enum={result['value']}")
            return result
        if kind in ("Param<EAudioVarScope>", "Param<EAudioCueVarType>"):
            audit = _audio_cue_native_audit()
            allowed = audit.get("enumValues", {}).get(kind) if audit.get("status") == "validated" else None
            if not isinstance(allowed, list) or not allowed:
                raise ActionMapCodecError(f"{field}:audio-cue-enum-native={audit.get('status')}")
            result = self.value("Param<int>", field)
            if result["value"] not in allowed:
                raise ActionMapCodecError(f"{field}:unsupported-audio-cue-enum={result['value']}")
            return result
        # These enums have signed Int32 underlying types in the reviewed
        # wrappers. Their raw values do not select another wire layout.
        if kind in (
            "Param<BoolComparer>", "Param<NumberComparer>",
            "Param<MissionSystem.MissionState>", "Param<EntityPtrComparer>",
            "Param<SP_INTERACTIVE_OP_TYPE>",
            "Param<InteractiveAudioComponent.EAudioTriggerState>",
            "Param<TweenManager.TweenEase>",
            "Param<FacBuildingState>",
            "Param<FCNodeMode>",
            "Param<CinemachineBlendDefinition.Style>",
            "Param<CommonBlendCamResetType>",
            "Param<AudioCueSystem.EBehaviourType>",
            "Param<AudioPlaceholderMusicUtil.EPlaceholderMusicFadeInType>",
            "Param<RadioVoiceAttenuationType>",
            "Param<AudioMusicSystem.EMusicEventPreAction>",
            "Param<LimitedGuideIconType>",
            "Param<LimitedGuideType>",
            "Param<OnQuestStateChanged.FilterQuestStateEnum>",
            "Param<MovementComponent.GroundedMoveGait>",
            "Param<MountPoint>",
            "Param<NpcEffectType>",
            "Param<PlayerController.InputActionType>",
            "Param<EnemyAIModeType>",
            "Param<ENPCAnimationAvatarMaskType>",
            "Param<NPCMontageAnim.EMontageStateType>",
            "Param<MissionSystem.QuestState>",
            "Param<SetCharSkillButtonActive.CharSkillTypeMask>",
            "Param<CharacterAIModeType>",
            "Param<GameAction.EAudioMusicBaseState>",
            "Param<GameAction.EAudioBattleMusicIntensityState>",
            "Param<GameAction.EAudioBattleMusicState>",
            "Param<CompareOperator>",
            "Param<ECharTutorialStepState>",
            "Param<ShowUIToast.ShowToastType>",
            "Param<ForbidType>",
            "Param<GeneralAbilityType>",
            "Param<GeneralAbilitySystem.TempAbilityActiveState>",
            "Param<CastTargetType>",
            "Param<PlayerController.InputActionType>",
            "Param<ScriptEndReason>",
            "Param<Gender>",
        ):
            kind = "Param<int>"
        # Both AudioBlackScreenBehaviour enums explicitly use Byte as their
        # underlying type in the selected generated wrapper.
        if kind in (
            "Param<AudioBlackScreenBehaviour.ERetainFlag>",
            "Param<AudioBlackScreenBehaviour.EPresetBehaviour>",
        ):
            kind = "Param<byte>"
        if kind in (
            "Param<byte>", "Param<uint>", "Param<ulong>",
            "Param<float>", "Param<Vector2>", "Param<Vector3>",
        ):
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            if kind in ("Param<Vector2>", "Param<Vector3>"):
                return self.param_tail(
                    self.value(kind[6:-1], field + ".value"), field
                )
            fmt = {
                "Param<byte>": "<B", "Param<uint>": "<I",
                "Param<ulong>": "<Q", "Param<float>": "<f",
            }[kind]
            size = struct.calcsize(fmt)
            self.need(size, field + ".value")
            values = struct.unpack_from(fmt, self.data, self.offset)
            self.offset += size
            if not all(math.isfinite(value) for value in values):
                raise ActionMapCodecError(f"{field}:non-finite")
            return self.param_tail(values[0], field)
        if kind in ("Param<LsmPtr>", "Param<FunctionAreaPtr>", "Param<SpawnerPtr>", "Param<WaterVolumePtr>"):
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(
                    f"{field}:unsupported-member-count={marker}"
                )
            self.need(8, field + ".value.id")
            value = struct.unpack_from("<Q", self.data, self.offset)[0]
            self.offset += 8
            return self.param_tail({"id": value}, field)
        if kind in ("Param<EventArgsPtr>", "Param<LangKey>", "Param<CameraShakeConfigPtr>"):
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 1:
                raise ActionMapCodecError(
                    f"{field}:unsupported-wrapped-string-members={marker}/{value_marker}"
                )
            return self.param_tail({"key": self.string(field + ".value.key")}, field)
        if kind == "Param<GlobalBuffId>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 1:
                raise ActionMapCodecError(
                    f"{field}:unsupported-global-buff-id-members={marker}/{value_marker}"
                )
            return self.param_tail({"id": self.string(field + ".value.id")}, field)
        if kind == "Param<ObjectPtr<GlobalBuff>>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 2:
                raise ActionMapCodecError(
                    f"{field}:unsupported-global-buff-pointer-members="
                    f"{marker}/{value_marker}"
                )
            self.need(4, field + ".value.cachedUid")
            cached_uid = struct.unpack_from("<I", self.data, self.offset)[0]
            self.offset += 4
            obj_marker = self.byte(field + ".value.obj")
            if obj_marker != 0xFF:
                raise ActionMapCodecError(
                    f"{field}:unsupported-nonnull-global-buff=0x{obj_marker:02x}"
                )
            return self.param_tail({"cachedUid": cached_uid, "obj": None}, field)
        if kind == "Param<BuffPtr>":
            marker = self.byte(field + ".memberCount")
            buff_ptr_marker = self.byte(field + ".value.memberCount")
            object_ptr_marker = self.byte(field + ".value.ptr.memberCount")
            if (marker, buff_ptr_marker, object_ptr_marker) != (4, 1, 2):
                raise ActionMapCodecError(
                    f"{field}:unsupported-buff-pointer-members="
                    f"{marker}/{buff_ptr_marker}/{object_ptr_marker}"
                )
            self.need(4, field + ".value.ptr.cachedUid")
            cached_uid = struct.unpack_from("<I", self.data, self.offset)[0]
            self.offset += 4
            obj_marker = self.byte(field + ".value.ptr.obj")
            if obj_marker != 0xFF:
                raise ActionMapCodecError(
                    f"{field}:unsupported-nonnull-buff=0x{obj_marker:02x}"
                )
            return self.param_tail(
                {"ptr": {"cachedUid": cached_uid, "obj": None}}, field
            )
        if kind == "Param<List<BuffPtr>>":
            from .finish_buffs import decode_null_buff_list_param

            detail, self.offset = decode_null_buff_list_param(self.data, self.offset)
            return detail
        if kind == "Param<List<EntityPtr>>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                value = None
            elif not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-entity-list-count={count}")
            else:
                value = []
                for index in range(count):
                    item = f"{field}.value[{index}]"
                    item_marker = self.byte(item + ".memberCount")
                    if item_marker != 3:
                        raise ActionMapCodecError(
                            f"{item}:unsupported-member-count={item_marker}"
                        )
                    self.need(13, item)
                    logic_id, slot_id, use_slot_id = struct.unpack_from(
                        "<QIB", self.data, self.offset
                    )
                    self.offset += 13
                    if use_slot_id not in (0, 1):
                        raise ActionMapCodecError(
                            f"{item}:invalid-use-slot-id={use_slot_id}"
                        )
                    value.append({
                        "logicId": logic_id,
                        "slotId": slot_id,
                        "useSlotId": bool(use_slot_id),
                    })
            tail = params.decode_param_tail(self.data, self.offset)
            if tail is None:
                raise ActionMapCodecError(f"{field}:invalid-param-tail,offset={self.offset}")
            detail, self.offset = tail
            return {"value": value, **detail}
        if kind == "Param<List<NpcProxyOverrideEnvTalk.EnvTalkStruct>>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                value = None
            elif not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            else:
                value = []
                for index in range(count):
                    item = f"{field}.value[{index}]"
                    members = self.byte(item + ".memberCount")
                    if members != 2:
                        raise ActionMapCodecError(
                            f"{item}:unsupported-member-count={members}"
                        )
                    value.append({
                        "envTalkId": self.string(item + ".envTalkId"),
                        "odds": self.i32(item + ".odds"),
                    })
            return self.param_tail(value, field)
        if kind == "Param<CommonMaskBlendData>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            value_marker = self.byte(field + ".value.memberCount")
            if value_marker == 0xFF:
                return self.param_tail(None, field)
            if value_marker != 6:
                raise ActionMapCodecError(
                    f"{field}:unsupported-value-member-count={value_marker}"
                )
            self.need(16, field + ".value.audioBlackScreenBehaviour")
            audio = self.data[self.offset:self.offset + 16]
            self.offset += 16
            preset, retain_flags = audio[0], audio[1]
            fade_in_override, fade_out_override = audio[2], audio[8]
            override_in = struct.unpack_from("<f", audio, 4)[0]
            override_out = struct.unpack_from("<f", audio, 12)[0]
            if (
                preset not in (0, 1, 2, 64, 65, 128)
                or retain_flags > 0x1F
                or fade_in_override not in (0, 1)
                or fade_out_override not in (0, 1)
                or audio[3] != 0
                or audio[9:12] != b"\x00\x00\x00"
                or not math.isfinite(override_in)
                or not math.isfinite(override_out)
            ):
                raise ActionMapCodecError(
                    f"{field}:unsupported-audio-black-screen-behaviour"
                )
            curve_marker = self.byte(field + ".value.curve.memberCount")
            if curve_marker == 0xFF:
                curve = None
            elif curve_marker == 3:
                post_wrap = self.i32(field + ".value.curve.postWrapMode")
                pre_wrap = self.i32(field + ".value.curve.preWrapMode")
                key_count = self.i32(field + ".value.curve.keys.count")
                if key_count != 0:
                    raise ActionMapCodecError(
                        f"{field}:unsupported-curve-key-count={key_count}"
                    )
                curve = {"postWrapMode": post_wrap, "preWrapMode": pre_wrap, "keys": []}
            else:
                raise ActionMapCodecError(
                    f"{field}:unsupported-curve-member-count={curve_marker}"
                )
            fade_in = self.value("float32", field + ".value.fadeInDuration")
            fade_out = self.value("float32", field + ".value.fadeOutDuration")
            mask_type = self.i32(field + ".value.maskType")
            use_curve = self.byte(field + ".value.useCurve")
            if mask_type not in (0, 1, 2, 3) or use_curve not in (0, 1):
                raise ActionMapCodecError(
                    f"{field}:unsupported-mask={mask_type},useCurve={use_curve}"
                )
            return self.param_tail({
                "audioBlackScreenBehaviour": {
                    "presetBehaviour": preset,
                    "customRetainFlags": retain_flags,
                    "isOverrideFadeInTime": bool(fade_in_override),
                    "overrideFadeInTimeSeconds": override_in,
                    "isOverrideFadeOutTime": bool(fade_out_override),
                    "overrideFadeOutTimeSeconds": override_out,
                },
                "curve": curve,
                "fadeInDuration": fade_in,
                "fadeOutDuration": fade_out,
                "maskType": mask_type,
                "useCurve": bool(use_curve),
            }, field)
        if kind == "SendLuaEvent1" and field.endswith(".manualValue"):
            try:
                value, self.offset = send_lua_event.decode_nested_send_lua_event(
                    self.data, self.offset, field, 1,
                )
            except send_lua_event.SendLuaEventDecodeError as exc:
                raise ActionMapCodecError(str(exc)) from exc
            return value
        decoder = (
            params.decode_param_output if kind.startswith("ParamOutput<") else {
                "Param<string>": params.decode_string_param,
                "Param<bool>": params.decode_bool_param,
                "Param<int>": params.decode_i32_param,
                "Param<EntityPtr>": params.decode_constant_entity_ptr_param,
                "Param<LevelScriptPtr>": params.decode_levelscript_ptr_param,
            }.get(kind)
        )
        if decoder is None:
            declared = self.declared_value(kind, field)
            if declared is not _NOT_DECLARED:
                return declared
            raise ActionMapCodecError(f"{field}:unsupported-field-type={kind}")
        result = decoder(self.data, self.offset)
        if result is None:
            raise ActionMapCodecError(f"{field}:invalid-{kind},offset={self.offset}")
        detail, self.offset = result
        return detail

    # -- derived-tier decoding ------------------------------------------
    #
    # Everything below reads a shape stated by a derived declaration rather
    # than by the reviewed contract.  It is reached only when a caller passed
    # `Declarations`, and only after the reviewed vocabulary has declined the
    # kind, so the reviewed path's behaviour is unchanged.

    def scalar(self, fmt: str, field: str, *, allow_infinite: bool = False) -> Any:
        size = struct.calcsize(fmt)
        self.need(size, field)
        value = struct.unpack_from(fmt, self.data, self.offset)[0]
        self.offset += size
        if fmt in ("<f", "<d") and not allow_infinite and not math.isfinite(value):
            raise ActionMapCodecError(f"{field}:non-finite")
        return value

    def raw_struct(self, name: str, declared: dict[str, Any], field: str) -> Any:
        """A struct written as raw memory, read at its declared offsets.

        The bytes are the type's memory image, so members sit at the offsets
        its real field order and alignment put them at -- not in serialized
        order, and with padding in between. Padding must be zero: the reviewed
        `Param<LevelScriptPtr>` decoder already requires that of the same eight
        bytes, which is what keeps a mis-sized read from sliding silently.
        """

        layout = declared.get("rawLayout")
        if layout is None:
            raise ActionMapCodecError(
                f"{field}:unresolved-unmanaged-struct-layout={name}"
            )
        base = self.offset
        self.need(layout["size"], field)
        value: dict[str, Any] = {}
        covered = []
        for member, kind, offset, size in layout["fields"]:
            self.offset = base + offset
            value[member] = self.declared_member(kind, f"{field}.{member}")
            if self.offset != base + offset + size:
                raise ActionMapCodecError(
                    f"{field}.{member}:declared-size-mismatch={self.offset - base - offset},"
                    f"expected={size}"
                )
            covered.append((offset, offset + size))
        cursor = 0
        for start, end in sorted(covered):
            if any(self.data[base + cursor : base + start]):
                raise ActionMapCodecError(
                    f"{field}:non-zero-struct-padding,offset={base + cursor}"
                )
            cursor = max(cursor, end)
        if any(self.data[base + cursor : base + layout["size"]]):
            raise ActionMapCodecError(
                f"{field}:non-zero-struct-padding,offset={base + cursor}"
            )
        self.offset = base + layout["size"]
        return value

    def declared_struct(self, name: str, field: str, *, allow_raw: bool = False) -> Any:
        """One declared struct, framed the way its real type requires.

        MemoryPack frames a value holding any reference as an object: a null
        marker or a member count, then the members in declared order. A struct
        holding no reference is written as raw bytes instead, with no marker
        and no count. The reviewed contract already encodes both by hand --
        `Param<EventArgsPtr>` reads a header then a string, `Param<LsmPtr>`
        reads a bare uint64 -- so the framing is a per-type fact, and
        `containsReferences` is where the derivation records it.

        The raw case is only decodable when the struct has a single member.
        With more than one, the bytes are the type's in-memory layout, with
        whatever ordering and padding the runtime chose, and that is not
        something the declaration states. `AirWallPtr` is the live example:
        three unmanaged members whose serialized order is not their field
        order. Those fail closed rather than being read in member order.
        """

        declared = self.declarations.structs[name]
        # A type with no MemoryPack wrapper has no generated object formatter,
        # so the unmanaged formatter writes it raw wherever it appears --
        # collection elements included. `StringPathHash` is one bare int64 and
        # never carries a header.
        always_raw = declared.get("wrapperName") is None
        if (allow_raw or always_raw) and not declared.get("containsReferences", True):
            return self.raw_struct(name, declared, field)
        self.need(1, field)
        if self.data[self.offset] == 0xFF:
            self.offset += 1
            return None
        # A SendLuaEvent's nested `manualValue` is the action written by its own
        # formatter, not by the wrapper whose property type the derivation
        # recorded, so the declared member count describes the wrong object.
        # `send_lua_event` owns that shape and why it cannot be derived.
        if send_lua_event.is_send_lua_event(name) and field.endswith(".manualValue"):
            try:
                value, self.offset = send_lua_event.decode_nested_send_lua_event(
                    self.data,
                    self.offset,
                    field,
                    send_lua_event.json_param_count(declared),
                )
            except send_lua_event.SendLuaEventDecodeError as exc:
                raise ActionMapCodecError(str(exc)) from exc
            return value
        members = self.byte(field + ".memberCount")
        if members != declared["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-declared-member-count={members},"
                f"expected={declared['memberCount']}"
            )
        value = {
            member: self.declared_member(kind, f"{field}.{member}")
            for member, kind in declared["fields"]
        }
        if declared.get("provenBoundary") == "empty-collection-only":
            # The declaration's evidence covers only the empty shape. A
            # populated one is a different, unestablished layout, so say so
            # here rather than let a wrong length surface as a desync four
            # members later.
            for member, decoded in value.items():
                if isinstance(decoded, list) and decoded:
                    raise ActionMapCodecError(
                        f"{field}.{member}:unproven-populated-collection="
                        f"{name},count={len(decoded)}"
                    )
        return value

    def declared_member(self, kind: str, field: str) -> Any:
        """One member of an enclosing object, which may be raw.

        A generated formatter writes each member with the writer's own value
        call, so an unmanaged member goes out as raw bytes. A collection
        element takes the element formatter instead, which writes the object
        header -- that is the whole of the difference.
        """

        if self.declarations is not None and kind in self.declarations.structs:
            decoded = self.declared_inner(kind, field, allow_raw=True)
            if decoded is not _NOT_DECLARED:
                return decoded
        return self.value(kind, field)

    def declared_value(self, kind: str, field: str) -> Any:
        """Decode `kind` from a derived declaration, or return the sentinel.

        The cursor has already consumed a leading null marker for the object
        shapes that carry one, so a `Param<...>` here starts at its member
        count. Anything this method does not recognise is handed back, so the
        caller still raises `unsupported-field-type` rather than guessing.
        """

        if self.declarations is None:
            return _NOT_DECLARED
        inner = _generic_argument(kind, "Param")
        if inner is not None:
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            value = self.declared_inner(inner, field + ".value", allow_raw=True)
            if value is _NOT_DECLARED:
                raise ActionMapCodecError(f"{field}:unsupported-field-type={kind}")
            return self.param_tail(value, field)
        return self.declared_inner(kind, field)

    def declared_inner(self, kind: str, field: str, *, allow_raw: bool = False) -> Any:
        """The value side of a declared type, with no Param envelope.

        `allow_raw` says whether an unmanaged struct here is written as raw
        memory. It is true only directly inside a `Param<T>`: the reviewed
        decoders show `Param<LsmPtr>` reading a bare uint64 and
        `Param<LevelScriptPtr>` reading sixteen raw bytes, while the reviewed
        shape decoder reads a member-count header for every
        `List<LevelScriptShape>` element -- and `LevelScriptShape` is just as
        unmanaged as those. So the framing is decided by where the value sits,
        not by the type alone.
        """

        if kind in self.declarations.enums:
            kind = self.declarations.enums[kind]
        if kind in _DERIVED_SCALARS:
            return self.scalar(
                _DERIVED_SCALARS[kind], field,
                allow_infinite=kind == "floatAllowInfinite",
            )
        if kind in ("bool", "string", "int32", "float32", "Vector2", "Vector3"):
            return self.value(kind, field)
        if kind in _UNITY_VECTORS:
            fmt, names = _UNITY_VECTORS[kind]
            size = struct.calcsize(fmt)
            self.need(size, field)
            values = struct.unpack_from(fmt, self.data, self.offset)
            self.offset += size
            if fmt[-1] == "f" and not all(math.isfinite(v) for v in values):
                raise ActionMapCodecError(f"{field}:non-finite")
            return dict(zip(names, values))
        inner = _generic_argument(kind, "Nullable")
        if inner is not None:
            return self.declared_nullable(inner, field)
        element = _generic_argument(kind, "List")
        if element is not None:
            return self.counted_declared(element, field)
        if kind.endswith("[]"):
            # An array of an unmanaged element takes MemoryPack's unmanaged
            # array path: a count, then the elements as raw memory with no
            # per-element header. `List<T>` does not -- it writes each element
            # through T's own formatter -- so the two are not interchangeable.
            return self.counted_declared(kind[:-2], field, allow_raw=True)
        if any(
            _generic_argument(kind, head) is not None
            for head in SERIALIZE_FIELD_DICTIONARY_HEADS
        ):
            arguments = _serialize_field_dictionary_arguments(kind)
            if arguments is None:
                return _NOT_DECLARED
            return self.serialize_field_dictionary(
                arguments[0], arguments[1], field
            )
        pair = _generic_argument(kind, "Dictionary")
        if pair is not None:
            arguments = _split_generic_arguments(pair)
            if len(arguments) != 2:
                return _NOT_DECLARED
            return self.declared_dictionary(arguments[0], arguments[1], field)
        declared = self.declarations.structs.get(kind)
        if declared is None:
            return _NOT_DECLARED
        if declared.get("isUnionBase"):
            return self.declared_union(kind, field)
        return self.declared_struct(kind, field, allow_raw=allow_raw)

    def pos_rot_list(self, count: int, field: str) -> list[dict[str, Any]]:
        """`List<PosRot>` elements, each written by PosRot's own formatter.

        `List<T>` writes every element through T's formatter rather than as raw
        memory, so each carries its own two-member header before the two
        `Vector3`s -- twenty-five bytes per element, not twenty-four.

        **The two vectors are written eulerAngles first.** `PosRot` declares
        `position` then `eulerAngles`, but `Beyond_PosRotForMemoryPack`'s
        setters are `set___eulerAngles__` then `set___position__`, and the
        generated formatter follows its own member order. The payload agrees:
        read this way the second vector is a map02 world position and the first
        a yaw/pitch/roll, while the declared order gives eulers past 1300
        degrees. Declaration order is not wire order here, the same lesson
        `RunePuzzleData` taught.
        """

        poses: list[dict[str, Any]] = []
        for index in range(count):
            item = f"{field}.value[{index}]"
            members = self.byte(item + ".memberCount")
            if members != 2:
                raise ActionMapCodecError(
                    f"{item}:unsupported-member-count={members}"
                )
            self.need(24, item)
            values = struct.unpack_from("<6f", self.data, self.offset)
            if not all(math.isfinite(value) for value in values):
                raise ActionMapCodecError(f"{item}:non-finite")
            self.offset += 24
            poses.append({
                "eulerAngles": {"x": values[0], "y": values[1], "z": values[2]},
                "position": {"x": values[3], "y": values[4], "z": values[5]},
            })
        return poses

    def declared_nullable(self, inner: str, field: str) -> Any:
        """`T?` for an unmanaged T, written as its raw memory image.

        .NET lays `Nullable<T>` out as a `hasValue` flag followed by the value
        at T's alignment, so a `float?` is eight bytes: the flag, three bytes
        of padding, then the float. The padding must be zero for the same
        reason it must in any other raw struct.
        """

        if inner in self.declarations.enums:
            inner = self.declarations.enums[inner]
        fmt = _DERIVED_SCALARS.get(inner)
        if fmt is None:
            return _NOT_DECLARED
        width = struct.calcsize(fmt)
        self.need(width * 2 if width > 1 else 2, field)
        base = self.offset
        has_value = self.data[base]
        if has_value not in (0, 1):
            raise ActionMapCodecError(f"{field}:invalid-has-value={has_value}")
        if any(self.data[base + 1 : base + width]):
            raise ActionMapCodecError(
                f"{field}:non-zero-nullable-padding,offset={base + 1}"
            )
        self.offset = base + max(width, 1)
        value = self.scalar(fmt, field + ".value")
        return value if has_value else None

    def serialize_field_dictionary(self, key: str, value: str, field: str) -> Any:
        """`Beyond.SerializeFieldDictionary<K,V>`: an object, then a map.

        The type is serialized by a registered `MemoryPackFormatter`, not by a
        generated one, so its member list does not describe the wire. What the
        formatter writes is the ordinary one-member object framing -- a null
        marker or a member count of one -- followed by the same counted map a
        `Dictionary<K,V>` member writes. The reviewed CharInteractPerform
        reader reads exactly that shape and reaches EOF on all 202 current
        owners; reading the header as the map's own count instead consumes
        four bytes where one belongs and desynchronises the rest of the file.
        """

        self.need(1, field)
        if self.data[self.offset] == 0xFF:
            self.offset += 1
            return None
        members = self.byte(field + ".memberCount")
        if members != 1:
            raise ActionMapCodecError(
                f"{field}:unsupported-serialize-field-dictionary-member-count="
                f"{members}"
            )
        return self.declared_dictionary(key, value, field)

    def unmanaged_width(self, kind: str) -> int | None:
        """The raw width of an unmanaged kind, or None if it is not one.

        An enum is written as its storage type, so it resolves to that width
        rather than being treated as unknown.
        """

        if self.declarations is not None and kind in self.declarations.enums:
            kind = self.declarations.enums[kind]
        if kind == "bool":
            return 1
        fmt = _DERIVED_SCALARS.get(kind)
        return struct.calcsize(fmt) if fmt else None

    def declared_dictionary(self, key: str, value: str, field: str) -> Any:
        """A counted map: a nullable count, then that many key/value pairs.

        When both sides are unmanaged the pair is a `KeyValuePair<K,V>` struct
        written as raw memory, so it carries .NET's layout padding and not just
        the two values back to back. `Dictionary<ulong,int>` is the case the
        corpus proves: the key is eight bytes, the value four, and the pair is
        sixteen, so every entry ends with four bytes the two fields do not
        account for. Reading them back to back desynchronises by four bytes per
        entry, which is how `RunePuzzleData` surfaced -- its first field after
        the map read a count out of the drifted cursor.

        This is the same shape `SerializeFieldDictionary` already cost four
        bytes per value for, so it is a property of the unmanaged pair rather
        than of one dictionary. The padding must be zero, which keeps the rule
        self-checking: a wrong layout shows up as a refusal rather than as
        plausible values.
        """

        count = self.i32(field + ".count")
        if count == -1:
            return None
        if not 0 <= count <= 100_000:
            raise ActionMapCodecError(f"{field}:unsupported-count={count}")

        key_width = self.unmanaged_width(key)
        value_width = self.unmanaged_width(value)
        value_offset = 0
        pair_size = 0
        if key_width and value_width:
            alignment = max(key_width, value_width)
            value_offset = _align_up(key_width, value_width)
            pair_size = _align_up(value_offset + value_width, alignment)

        entries = []
        for index in range(count):
            item = f"{field}[{index}]"
            start = self.offset
            if pair_size:
                # The whole pair must be present before any of it is read, so
                # the bound is taken from the pair's start rather than from a
                # cursor the key has already moved.
                self.need(pair_size, item)
            decoded_key = self.declared_inner(key, item + ".key")
            if pair_size:
                self._require_zero_padding(start + key_width, start + value_offset, item)
                self.offset = start + value_offset
            decoded_value = self.declared_inner(value, item + ".value")
            if decoded_key is _NOT_DECLARED or decoded_value is _NOT_DECLARED:
                missing = key if decoded_key is _NOT_DECLARED else value
                raise ActionMapCodecError(
                    f"{item}:unsupported-field-type={missing}"
                )
            if pair_size:
                self._require_zero_padding(self.offset, start + pair_size, item)
                self.offset = start + pair_size
            entries.append({"key": decoded_key, "value": decoded_value})
        return entries

    def _require_zero_padding(self, start: int, end: int, field: str) -> None:
        if end > start and any(self.data[start:end]):
            raise ActionMapCodecError(
                f"{field}:non-zero-pair-padding,offset={start}"
            )

    def declared_union(self, family: str, field: str) -> Any:
        """A member declared as a union base: null, or a tag and its members.

        The base type names the family; the tag selects which subtype's
        declaration applies. `LevelScriptTriggerVolumeData` is the reviewed
        example, where tag 1 is the Leader subtype that adds no fields.
        """

        self.need(1, field)
        if self.data[self.offset] == 0xFF:
            self.offset += 1
            return None
        tag = self.byte(field + ".tag")
        if tag == 0xFA:
            self.need(2, field + ".wideTag")
            tag = struct.unpack_from("<H", self.data, self.offset)[0]
            self.offset += 2
        elif tag >= 0xFA:
            raise ActionMapCodecError(
                f"{field}:unsupported-union-marker=0x{tag:02x}"
            )
        members = self.byte(field + ".memberCount")
        layout = self.declarations.layouts.get((family, tag))
        if layout is None or members != layout["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-declared-union={family}#0x{tag:04x},"
                f"memberCount={members}"
            )
        _require_selected_native(family, tag, layout)
        return {
            "unionTag": tag,
            "wrapperName": layout["wrapperName"],
            "fields": {
                member: self.declared_member(kind, f"{field}.{member}")
                for member, kind in layout["fields"]
            },
        }

    def counted_declared(
        self, element: str, field: str, *, allow_raw: bool = False
    ) -> list[Any] | None:
        count = self.i32(field + ".count")
        if count == -1:
            return None
        if not 0 <= count <= 10_000:
            raise ActionMapCodecError(f"{field}:unsupported-count={count}")
        values = []
        for index in range(count):
            item = f"{field}[{index}]"
            if _generic_argument(element, "Param") is not None:
                # A Param element carries its own envelope, so it goes through
                # the ordinary value path and picks up the reviewed decoders.
                values.append(self.value(element, item))
                continue
            decoded = self.declared_inner(element, item, allow_raw=allow_raw)
            if decoded is _NOT_DECLARED:
                raise ActionMapCodecError(
                    f"{item}:unsupported-field-type={element}"
                )
            values.append(decoded)
        return values

    def param_tail(self, value: Any, field: str) -> dict[str, Any]:
        result = params.decode_param_tail(self.data, self.offset)
        if result is None:
            raise ActionMapCodecError(f"{field}:invalid-param-tail,offset={self.offset}")
        detail, self.offset = result
        return {"value": value, **detail}

    def node(self, family: str, field: str) -> dict[str, Any]:
        start = self.offset
        tag = self.byte(field + ".tag")
        if tag == 0xFA:
            self.need(2, field + ".wideTag")
            tag = struct.unpack_from("<H", self.data, self.offset)[0]
            self.offset += 2
        elif tag >= 0xFA:
            raise ActionMapCodecError(f"{field}:unsupported-union-marker=0x{tag:02x}")
        members = self.byte(field + ".memberCount")
        layout = _layouts().get((family, tag))
        if layout is not None:
            _require_layout_build()
        elif self.declarations is not None:
            layout = self.declarations.layouts.get((family, tag))
        if layout is None or members != layout["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-union=0x{tag:04x},memberCount={members},offset={start}"
            )
        _require_selected_native(family, tag, layout)
        if layout.get("nativeGate") == "levelscript_on_spell_abnormal_start_native":
            from .on_spell_abnormal_start import decode_on_spell_abnormal_start_header

            audit = _on_spell_abnormal_start_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onSpellAbnormalStartNative:missing-route")
            decoded, self.offset = decode_on_spell_abnormal_start_header(
                self.data, start, route,
                enum_values=audit.get("enumValues", {}).get("Param<SpellAbnormalType>"),
            )
            return decoded
        if layout.get("nativeGate") == "levelscript_on_physical_infliction_native":
            from .on_physical_infliction import decode_on_physical_infliction_header

            audit = _on_physical_infliction_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onPhysicalInflictionNative:missing-route")
            decoded, self.offset = decode_on_physical_infliction_header(
                self.data, start, route,
                enum_values=audit.get("enumValues", {}).get("Param<PhysicalInflictionType>"),
            )
            return decoded
        if layout.get("nativeGate") == "levelscript_on_bb_variable_changed_native":
            from .on_bb_variable_changed import decode_on_bb_variable_changed_header

            audit = _on_bb_variable_changed_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onBBVariableChangedNative:missing-route")
            decoded, self.offset = decode_on_bb_variable_changed_header(
                self.data, start, route,
            )
            return decoded
        if layout.get("nativeGate") == "levelscript_on_entity_die_native":
            from .on_entity_die import decode_on_entity_die_header

            audit = _on_entity_die_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onEntityDieNative:missing-route")
            decoded, self.offset = decode_on_entity_die_header(
                self.data, start, route,
            )
            return decoded
        if layout.get("nativeGate") == "levelscript_on_encounter_intro_part_end_native":
            from .on_encounter_intro_part_end import decode_on_encounter_intro_part_end_header

            audit = _on_encounter_intro_part_end_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onEncounterIntroPartEndNative:missing-route")
            decoded, self.offset = decode_on_encounter_intro_part_end_header(
                self.data, start, route,
            )
            return decoded
        values = {name: self.value(kind, field + "." + name) for name, kind in layout["fields"]}
        return {
            "sourceOffset": start, "endOffset": self.offset,
            "unionTag": tag, "memberCount": members,
            "wrapperName": layout["wrapperName"], "fields": values,
        }

    def condition(self, field: str) -> dict[str, Any]:
        start = self.offset
        tag = self.byte(field + ".tag")
        if tag == 0xFA:
            self.need(2, field + ".wideTag")
            tag = struct.unpack_from("<H", self.data, self.offset)[0]
            self.offset += 2
        elif tag >= 0xFA:
            raise ActionMapCodecError(
                f"{field}:unsupported-condition-union-marker=0x{tag:02x}"
            )
        members = self.byte(field + ".memberCount")
        layout = _condition_layouts().get(tag)
        if layout is not None:
            _require_layout_build()
        elif self.declarations is not None:
            layout = self.declarations.layouts.get(("GameCondition", tag))
        if layout is None or members != layout["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-condition-union=0x{tag:04x},"
                f"memberCount={members},offset={start}"
            )
        values = {
            name: self.value(kind, field + "." + name)
            for name, kind in layout["fields"]
        }
        return {
            "sourceOffset": start,
            "endOffset": self.offset,
            "unionTag": tag,
            "memberCount": members,
            "wrapperName": layout["wrapperName"],
            "fields": values,
        }


def decode_action_serialized_map(
    data: bytes, offset: int, *, declarations: Declarations | None = None,
) -> tuple[dict[str, Any] | None, int]:
    """Consume a null map or three declared lists.

    With no `declarations` this uses only reviewed codecs and the reviewed
    layout contract, which is the `exact` tier every production consumer
    publishes at. Passing `declarations` additionally admits the derived
    union, struct and enum table; the result is then `direct`, and the caller
    owns saying so.
    """
    cursor = _Cursor(data, offset, declarations)
    marker = cursor.byte("interactiveTemplate.dataMap.memberCount")
    if marker == 0xFF:
        return None, cursor.offset
    if marker != 3:
        raise ActionMapCodecError(f"interactiveTemplate.dataMap.memberCount={marker},expected=3-or-null")
    counts = []
    lists = []
    for index, family in enumerate(("ActionBase", "GetterBase", "ActionHeader")):
        field = f"interactiveTemplate.dataMap.lists[{index}]"
        count_offset = cursor.offset
        count = cursor.i32(field + ".count")
        if not 0 <= count <= 10_000:
            raise ActionMapCodecError(
                f"{field}:unsupported-count={count},countOffset={count_offset},"
                f"payloadOffset={cursor.offset}"
            )
        counts.append(count)
        lists.append([cursor.node(family, f"{field}[{i}]") for i in range(count)])
    result: dict[str, Any] = {"memberCount": 3, "rawListCounts": counts, "empty": not any(counts)}
    if any(counts):
        result.update({"sourceOffset": offset, "endOffset": cursor.offset,
                       "actions": lists[0], "getters": lists[1], "headers": lists[2]})
    return result, cursor.offset


def decode_declared_root(
    data: bytes,
    offset: int,
    root: str,
    declarations: Declarations,
) -> tuple[dict[str, Any], int]:
    """Decode a whole serialized root from its derived declaration.

    `LevelScriptData` is a twenty-seven member MemoryPack type whose members
    are declared in the same place its unions are. Two independently recovered
    framings corroborate the order: the prefix framing proved member zero is
    `actionMap`, and the terminal framing proved the file ends with `scriptId`,
    `startShapeList`, `startType`, `taskMap`, `triggerVolumes` -- which is
    exactly the head and tail of the declared list.

    `ActionSerializedMap` is the one member that routes back to the reviewed
    reader rather than the generic one, because its three declared lists are
    what `decode_action_serialized_map` already owns.
    """

    declared = declarations.structs.get(root)
    if declared is None:
        raise ActionMapCodecError(f"declaredRoot:unknown-type={root}")
    cursor = _Cursor(data, offset, declarations)
    members = cursor.byte(f"{root}.memberCount")
    if members != declared["memberCount"]:
        raise ActionMapCodecError(
            f"{root}:unsupported-member-count={members},"
            f"expected={declared['memberCount']}"
        )
    values: dict[str, Any] = {}
    for member, kind in declared["fields"]:
        field = f"{root}.{member}"
        if kind == "ActionSerializedMap":
            values[member], cursor.offset = decode_action_serialized_map(
                data, cursor.offset, declarations=declarations
            )
            continue
        values[member] = cursor.declared_member(kind, field)
    return {"root": root, "memberCount": members, "fields": values}, cursor.offset


def decode_reviewed_node(
    data: bytes, offset: int, family: str, *, game_root: Path | None = None,
) -> tuple[dict[str, Any], int]:
    """Decode one reviewed union at a declared cursor, with a selected-build gate."""
    inputs = _contract()["nativeInputs"]
    native = check_installed_native_inputs(
        inputs["gameAssembly"]["sha256"], inputs["metadata"]["sha256"],
        gameassembly=game_root.parent / "GameAssembly.dll" if game_root else None,
        metadata=game_root / "il2cpp_data/Metadata/global-metadata.dat" if game_root else None,
    )
    if native.status != "validated":
        raise ActionMapCodecError(
            f"actionMap.installed_native_inputs: expected=validated, "
            f"actual={native.status}, detail={native.detail}"
        )
    if family not in ("ActionBase", "GetterBase", "ActionHeader"):
        raise ActionMapCodecError(f"actionMap:unsupported-family={family}")
    cursor = _Cursor(data, offset)
    result = cursor.node(family, f"actionMap.{family}")
    return result, cursor.offset
