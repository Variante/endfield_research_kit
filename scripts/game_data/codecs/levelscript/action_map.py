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

Tiers. Reviewed rows in `action_map_layouts.json`
(`endfield.action-map-layouts.v5`) are `exact` layouts keyed by
`wrapperName`: reviewed `memberCount` and typed `fields` (generated setter
order), no per-build tag and no `nativeInputs`. A union tag is the type's
rank among its family's wrappers and renumbers per build, so `_resolved`
attaches the current tag at load from
`scripts.game_data.contracts/levelscript_union_tags.json` through
`scripts.game_data.levelscript_union_tags` (`GetterBase` rows resolve in the
`PureGetter` family, conditions in `GameCondition`, short name from the
wrapper). The whole table fails closed (no row, `actionMap.unionTags` error)
unless that contract validates the installed build; a row whose wrapper is
missing or whose current member count differs is dropped and listed by
`layout_resolution_audit()`. `decode_reviewed_node` also accepts an explicit
game root, checked against the union-tags contract's build, and
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
* `Param<LevelScriptPtr>` stores raw16: UInt64 script ID, signed Int32 level
  ID and four preserved bytes, then a pooled Param tail. Zero or an empty path
  does not imply a current-script mode.
* `Param<SpawnerPtr>` is a four-member Param whose constant is one unmanaged
  uint64 ID. Some reached getters store ID zero and bind the value through
  source `200` properties instead; others store nonzero constants.
* The `FinishBuff` `Param<BuffPtr>` value follows the generated 4/1/2 member
  chain, a cached unsigned identity and a null object marker before the
  pooled Param tail. Its hidden sixteen-byte value has an independent native
  gate; positive nested Buff objects remain refused. CameraShake's managed
  eight-byte value has its own pooled key/source and owned-transfer proof.
* Int32/UInt32 list Params require their independent current collection and
  parent-source proof before consuming even a null marker. Their codecs
  preserve signed binding words and pooled paths without assigning gameplay
  meaning. Float lists receive no grammar from these component proofs.
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
* Enum backings differ by route. A Param needs its own selected wrapper,
  source and store proof before decoding; backing width alone does not
  select a primitive formatter.
* `Param<List<GameplayTag>>` has its own pooled parent and generated MC1/FF
  element source; its positive elements do not reuse raw4 tag-array framing.
  Non-null `CameraControllerBase` constants remain unsupported and fail closed.
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
from scripts.game_data.memorypack.operation_native_validation import validate_native as _validate_native
from . import params
from . import send_lua_event
from .pos_rot import decode_pos_rot_param


CONTRACT_PATH = Path(__file__).with_name("action_map_layouts.json")


class ActionMapCodecError(ValueError):
    """The next declared field has no proven exact cursor."""


LAYOUT_SCHEMA = "endfield.action-map-layouts.v5"
# The layout contract names the PureGetter dispatcher's members `GetterBase`;
# the union-tags contract keeps the dispatcher's own family name.
_UNION_TAG_FAMILY = {"GetterBase": "PureGetter"}


def _contract() -> dict[str, Any]:
    return _decoded_contract(CONTRACT_PATH.read_bytes())


@lru_cache(maxsize=2)
def _decoded_contract(raw: bytes) -> dict[str, Any]:
    contract = json.loads(raw)
    if contract.get("schema") != LAYOUT_SCHEMA:
        raise ActionMapCodecError("actionMap.layoutContract:unsupported-schema")
    return contract


def _union_tags():
    from scripts.game_data import levelscript_union_tags

    return levelscript_union_tags


def _resolve_rows(rows: list[dict[str, Any]], default_family: str | None,
                  unresolved: list[str], families: dict, wrappers: dict) -> list[dict[str, Any]]:
    """Attach the installed build's tag to each reviewed row, by wrapper name.

    A row whose wrapper is absent from the current union, or whose current
    member count differs from the reviewed one, is left out and named in
    `unresolved`: its reviewed field order does not describe this build.
    """
    tags = _union_tags()
    resolved = []
    for row in rows:
        family = row.get("family") or default_family
        name = tags.short_name(str(row.get("wrapperName") or ""))
        union_family=_UNION_TAG_FAMILY.get(family, family)
        current = families.get(union_family,{}).get(name,('unavailable',family,name))
        if not isinstance(current[0], int):
            unresolved.append(f"{family}:{name}:unknown")
            continue
        if current[1] != row.get("memberCount"):
            unresolved.append(f"{family}:{name}:memberCount={current[1]}!={row.get('memberCount')}")
            continue
        if wrappers.get(union_family,{}).get(name,'') not in ("", row.get("wrapperName")):
            unresolved.append(f"{family}:{name}:wrapper")
            continue
        resolved.append({**row, "family": family, "tag": current[0]})
    return resolved


_RESOLVED: list[Any] = [None,None,None,None]


def _resolved() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Reviewed rows with current tags, plus the audit of that resolution.

    Fails closed as a whole: unless the union-tags contract validates the
    installed build, no row resolves and the audit carries its status.
    """
    tags=_union_tags();families,audit=tags._load()
    if audit.get("status") != "validated":
        return [], [], {"status": audit.get("status") or "unavailable",
                        "detail": f"levelscript_union_tags: {str(audit.get('detail') or '')[:300]}",
                        "unresolved": []}
    contract = _contract()
    wrappers=tags._wrappers()
    if all(previous is selected for previous,selected in zip(_RESOLVED[:3],(contract,families,wrappers))):return _RESOLVED[3]
    unresolved: list[str] = []
    layouts = _resolve_rows(contract["layouts"], None, unresolved,families,wrappers)
    conditions = _resolve_rows(contract.get("conditionLayouts", []), "GameCondition", unresolved,families,wrappers)
    result=layouts, conditions, {"status": "validated", "detail": "", "unresolved": unresolved}
    _RESOLVED[:]=[contract,families,wrappers,result]
    return result


def layout_resolution_audit() -> dict[str, Any]:
    """Union-tag gate status and the reviewed rows that did not resolve."""
    return dict(_resolved()[2])


def _layouts() -> dict[tuple[str, int], dict[str, Any]]:
    return {(row["family"], row["tag"]): row for row in _resolved()[0]}


def _condition_layouts() -> dict[int, dict[str, Any]]:
    return {row["tag"]: row for row in _resolved()[1]}


def _layout_build_status() -> tuple[str, str]:
    """The union-tag gate that resolved the reviewed rows' current tags."""
    audit = _resolved()[2]
    return audit["status"], audit["detail"]


def _require_layout_build() -> None:
    """Refuse every reviewed row unless its tag was resolved on this build.

    A union tag is its type's rank among the family's wrappers, so a client
    update renumbers it; rows therefore carry no tag and are resolved by
    wrapper name through the build-gated union-tags contract. Rows with their
    own `nativeGate` are re-proved per route; this gate covers every row.
    """
    status, detail = _layout_build_status()
    if status != "validated":
        raise ActionMapCodecError(
            f"actionMap.unionTags: expected=validated, actual={status}, detail={detail}"
        )


def _finish_scene_effect_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_finish_scene_effect_native import (
        validate_finish_scene_effect_native_contract,
    )

    return validate_finish_scene_effect_native_contract()


def _npc_proxy_patrol_stop_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_proxy_patrol_stop_native import (
        validate_npc_proxy_patrol_stop_native_contract,
    )

    return validate_npc_proxy_patrol_stop_native_contract()


def _post_audio_status_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_post_audio_status_native import (
        validate_post_audio_status_native_contract,
    )

    return validate_post_audio_status_native_contract()


def _entities_visibility_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entities_visibility_native import (
        validate_entities_visibility_native_contract,
    )

    return validate_entities_visibility_native_contract()


def _track_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_track_camera_native import (
        validate_track_camera_native_contract,
    )

    return validate_track_camera_native_contract()


def _enemy_patrol_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_enemy_patrol_start_native import (
        validate_enemy_patrol_start_native_contract,
    )

    return validate_enemy_patrol_start_native_contract()


def _archery_stage_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_archery_stage_native import (
        validate_archery_stage_native_contract,
    )

    return validate_archery_stage_native_contract()


def _typhoea_chip_id_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_typhoea_chip_id_native import (
        validate_typhoea_chip_id_native_contract,
    )

    return validate_typhoea_chip_id_native_contract()


def _finish_buffs_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_finish_buffs_native import (
        validate_finish_buffs_native_contract,
    )

    return validate_finish_buffs_native_contract()


def _mark_task_condition_failed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_mark_task_condition_failed_native import (
        validate_levelscript_mark_task_condition_failed_native_contract,
    )

    return validate_levelscript_mark_task_condition_failed_native_contract()


def _archery_advanced_headers_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_archery_advanced_headers_native import (
        validate_levelscript_archery_advanced_headers_native_contract,
    )

    return validate_levelscript_archery_advanced_headers_native_contract()


def _on_train_level_event_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_train_level_event_native import (
        validate_levelscript_on_train_level_event_native_contract,
    )

    return validate_levelscript_on_train_level_event_native_contract()


def _on_map_var_changed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_map_var_changed_native import (
        validate_levelscript_on_map_var_changed_native_contract,
    )

    return validate_levelscript_on_map_var_changed_native_contract()


def _on_enemy_in_fight_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_enemy_in_fight_native import (
        validate_levelscript_on_enemy_in_fight_native_contract,
    )

    return validate_levelscript_on_enemy_in_fight_native_contract()


def _on_enemy_take_last_attack_damage_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_enemy_take_last_attack_damage_native import (
        validate_levelscript_on_enemy_take_last_attack_damage_native_contract,
    )

    return validate_levelscript_on_enemy_take_last_attack_damage_native_contract()


def _on_spell_infliction_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spell_infliction_native import (
        validate_levelscript_on_spell_infliction_native_contract,
    )

    return validate_levelscript_on_spell_infliction_native_contract()


def _on_spawner_entity_spawn_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_entity_spawn_native import (
        validate_levelscript_on_spawner_entity_spawn_native_contract,
    )

    return validate_levelscript_on_spawner_entity_spawn_native_contract()


def _on_spawner_group_begin_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_group_begin_native import (
        validate_levelscript_on_spawner_group_begin_native_contract,
    )

    return validate_levelscript_on_spawner_group_begin_native_contract()


def _on_spawner_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_start_native import (
        validate_levelscript_on_spawner_start_native_contract,
    )

    return validate_levelscript_on_spawner_start_native_contract()


def _on_spell_abnormal_start_native_audit(*, game_root: Path | None = None) -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spell_abnormal_start_native import (
        validate_levelscript_on_spell_abnormal_start_native_contract,
    )

    if game_root is None:return validate_levelscript_on_spell_abnormal_start_native_contract()
    return _validate_native(validate_levelscript_on_spell_abnormal_start_native_contract,game_root=game_root)


def _on_physical_infliction_native_audit(*, game_root: Path | None = None) -> dict[str, Any]:
    from scripts.game_data.levelscript_on_physical_infliction_native import (
        validate_levelscript_on_physical_infliction_native_contract,
    )

    if game_root is None:return validate_levelscript_on_physical_infliction_native_contract()
    return _validate_native(validate_levelscript_on_physical_infliction_native_contract,game_root=game_root)


def _on_bb_variable_changed_native_audit(*, game_root: Path | None = None) -> dict[str, Any]:
    from scripts.game_data.levelscript_on_bb_variable_changed_native import (
        validate_levelscript_on_bb_variable_changed_native_contract,
    )

    if game_root is None:return validate_levelscript_on_bb_variable_changed_native_contract()
    return _validate_native(validate_levelscript_on_bb_variable_changed_native_contract,game_root=game_root)


def _on_physical_no_guard_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_physical_no_guard_native import (
        validate_levelscript_on_physical_no_guard_native_contract,
    )

    return validate_levelscript_on_physical_no_guard_native_contract()


def _on_spawner_wave_begin_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_wave_begin_native import (
        validate_levelscript_on_spawner_wave_begin_native_contract,
    )

    return validate_levelscript_on_spawner_wave_begin_native_contract()


def _on_spawner_entity_die_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_entity_die_native import (
        validate_levelscript_on_spawner_entity_die_native_contract,
    )

    return validate_levelscript_on_spawner_entity_die_native_contract()


def _on_encounter_activated_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_encounter_activated_native import (
        validate_levelscript_on_encounter_activated_native_contract,
    )

    return validate_levelscript_on_encounter_activated_native_contract()


def _on_encounter_battle_part_begin_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_encounter_battle_part_begin_native import (
        validate_levelscript_on_encounter_battle_part_begin_native_contract,
    )

    return validate_levelscript_on_encounter_battle_part_begin_native_contract()


def _on_encounter_battle_part_end_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_encounter_battle_part_end_native import (
        validate_levelscript_on_encounter_battle_part_end_native_contract,
    )

    return validate_levelscript_on_encounter_battle_part_end_native_contract()


def _on_entity_cast_skill_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_entity_cast_skill_native import (
        validate_levelscript_on_entity_cast_skill_native_contract,
    )

    return validate_levelscript_on_entity_cast_skill_native_contract()


def _on_leader_enter_trigger_volume_list_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_leader_enter_trigger_volume_list_native import (
        validate_levelscript_on_leader_enter_trigger_volume_list_native_contract,
    )

    return validate_levelscript_on_leader_enter_trigger_volume_list_native_contract()


def _list_add_value_entity_ptr_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_list_add_value_entity_ptr_native import (
        validate_levelscript_list_add_value_entity_ptr_native_contract,
    )

    return validate_levelscript_list_add_value_entity_ptr_native_contract()


def _add_tracking_point_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_add_tracking_point_native import (
        validate_levelscript_add_tracking_point_native_contract,
    )

    return validate_levelscript_add_tracking_point_native_contract()


def _set_forbid_map_teleport_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_forbid_map_teleport_native import (
        validate_levelscript_set_forbid_map_teleport_native_contract,
    )

    return validate_levelscript_set_forbid_map_teleport_native_contract()


def _resume_spawner_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_resume_spawner_native import (
        validate_levelscript_resume_spawner_native_contract,
    )

    return validate_levelscript_resume_spawner_native_contract()


def _start_seq_loop_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_seq_loop_native import (
        validate_start_seq_loop_native_contract,
    )

    return validate_start_seq_loop_native_contract()


def _entity_scanned_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entity_scanned_native import (
        validate_entity_scanned_native_contract,
    )

    return validate_entity_scanned_native_contract()


def _squad_fight_header_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_squad_fight_header_native import (
        validate_squad_fight_header_native_contract,
    )

    return validate_squad_fight_header_native_contract()


def _leader_enter_trigger_volume_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_leader_enter_trigger_volume_native import (
        validate_leader_enter_trigger_volume_native_contract,
    )

    return validate_leader_enter_trigger_volume_native_contract()


def _squad_all_die_header_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_squad_all_die_header_native import (
        validate_squad_all_die_header_native_contract,
    )

    return validate_squad_all_die_header_native_contract()


def _tracking_point_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_tracking_point_native import (
        validate_tracking_point_native_contract,
    )

    return validate_tracking_point_native_contract()


def _mission_changed_header_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_mission_changed_header_native import (
        validate_mission_changed_header_native_contract,
    )

    return validate_mission_changed_header_native_contract()


def _cutscene_teleport_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_cutscene_teleport_native import (
        validate_cutscene_teleport_native_contract,
    )

    return validate_cutscene_teleport_native_contract()


def _manually_stop_guide_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_manually_stop_guide_native import (
        validate_manually_stop_guide_native_contract,
    )

    return validate_manually_stop_guide_native_contract()


def _remove_tracking_point_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_remove_tracking_point_native import (
        validate_remove_tracking_point_native_contract,
    )

    return validate_remove_tracking_point_native_contract()


def _get_is_leader_in_trigger_volume_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_is_leader_in_trigger_volume_native import (
        validate_get_is_leader_in_trigger_volume_native_contract,
    )

    return validate_get_is_leader_in_trigger_volume_native_contract()


def _send_lua_event1_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_send_lua_event1_native import (
        validate_send_lua_event1_native_contract,
    )

    return validate_send_lua_event1_native_contract()


def _start_subgame_countdown_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_subgame_countdown_native import (
        validate_start_subgame_countdown_native_contract,
    )

    return validate_start_subgame_countdown_native_contract()


def _show_start_toast_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_show_start_toast_native import (
        validate_show_start_toast_native_contract,
    )

    return validate_show_start_toast_native_contract()


def _show_finish_toast_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_show_finish_toast_native import (
        validate_show_finish_toast_native_contract,
    )

    return validate_show_finish_toast_native_contract()


def _toggle_main_hud_ignore_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_toggle_main_hud_ignore_native import (
        validate_toggle_main_hud_ignore_native_contract,
    )

    return validate_toggle_main_hud_ignore_native_contract()


def _show_chapter_panel_direct_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_show_chapter_panel_direct_native import (
        validate_show_chapter_panel_direct_native_contract,
    )

    return validate_show_chapter_panel_direct_native_contract()


def _show_chapter_completed_panel_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_show_chapter_completed_panel_native import (
        validate_show_chapter_completed_panel_native_contract,
    )

    return validate_show_chapter_completed_panel_native_contract()


def _switch_to_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_switch_to_camera_native import (
        validate_switch_to_camera_native_contract,
    )

    return validate_switch_to_camera_native_contract()


def _start_track_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_track_camera_native import (
        validate_start_track_camera_native_contract,
    )

    return validate_start_track_camera_native_contract()


def _exit_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_exit_camera_native import (
        validate_exit_camera_native_contract,
    )

    return validate_exit_camera_native_contract()


def _reset_follow_camera_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_reset_follow_camera_native import (
        validate_reset_follow_camera_native_contract,
    )

    return validate_reset_follow_camera_native_contract()


def _fac_set_interact_locked_state_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_set_interact_locked_state_native import (
        validate_fac_set_interact_locked_state_native_contract,
    )

    return validate_fac_set_interact_locked_state_native_contract()


def _toggle_clear_screen_but_radio_v2_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_toggle_clear_screen_but_radio_v2_native import (
        validate_toggle_clear_screen_but_radio_v2_native_contract,
    )

    return validate_toggle_clear_screen_but_radio_v2_native_contract()


def _remove_npc_dialog_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_remove_npc_dialog_native import (
        validate_remove_npc_dialog_native_contract,
    )

    return validate_remove_npc_dialog_native_contract()


def _stop_subgame_countdown_by_handle_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_stop_subgame_countdown_by_handle_native import (
        validate_stop_subgame_countdown_by_handle_native_contract,
    )

    return validate_stop_subgame_countdown_by_handle_native_contract()


def _require_settlement_show_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_require_settlement_show_native import (
        validate_require_settlement_show_native_contract,
    )

    return validate_require_settlement_show_native_contract()


def _settlement_followon_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_settlement_followon_native import (
        validate_settlement_followon_native_contract,
    )

    return validate_settlement_followon_native_contract()


def _bool_compare_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_bool_compare_native import (
        validate_bool_compare_native_contract,
    )

    return validate_bool_compare_native_contract()


def _fac_top_view_range_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_top_view_range_native import (
        validate_fac_top_view_range_native_contract,
    )

    return validate_fac_top_view_range_native_contract()


def _fac_build_effect_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_build_effect_native import (
        validate_fac_build_effect_native_contract,
    )

    return validate_fac_build_effect_native_contract()


def _fac_change_building_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_change_building_native import (
        validate_fac_change_building_native_contract,
    )

    return validate_fac_change_building_native_contract()


def _npc_proxy_effect_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_proxy_effect_native import (
        validate_npc_proxy_effect_native_contract,
    )

    return validate_npc_proxy_effect_native_contract()


def _npc_effect_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_effect_native import (
        validate_npc_effect_native_contract,
    )

    return validate_npc_effect_native_contract()


def _block_battle_music_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_block_battle_music_native import (
        validate_block_battle_music_native_contract,
    )

    return validate_block_battle_music_native_contract()


def _block_auto_music_change_cancel_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_block_auto_music_change_cancel_native import (
        validate_block_auto_music_change_cancel_native_contract,
    )

    return validate_block_auto_music_change_cancel_native_contract()


def _fac_get_building_position_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_get_building_position_native import (
        validate_fac_get_building_position_native_contract,
    )

    return validate_fac_get_building_position_native_contract()


def _entity_hp_changed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entity_hp_changed_native import (
        validate_entity_hp_changed_native_contract,
    )

    return validate_entity_hp_changed_native_contract()


def _settlement_upgrade_show_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_settlement_upgrade_show_native import (
        validate_settlement_upgrade_show_native_contract,
    )

    return validate_settlement_upgrade_show_native_contract()


def _check_performance_ready_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_check_performance_ready_native import (
        validate_check_performance_ready_native_contract,
    )

    return validate_check_performance_ready_native_contract()


def _environment_enable_native_audit(*, game_root: Path | None = None) -> dict[str, Any]:
    from scripts.game_data.levelscript_environment_enable_native import (
        validate_environment_enable_native_contract,
    )

    return validate_environment_enable_native_contract(game_root=game_root)


def _settlement_ready_performance_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_settlement_ready_performance_native import (
        validate_settlement_ready_performance_native_contract,
    )

    return validate_settlement_ready_performance_native_contract()


def _add_buffs_to_target_selves_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_add_buffs_to_target_selves_native import (
        validate_add_buffs_to_target_selves_native_contract,
    )

    return validate_add_buffs_to_target_selves_native_contract()


def _set_squad_special_idle_enable_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_squad_special_idle_enable_native import (
        validate_set_squad_special_idle_enable_native_contract,
    )

    return validate_set_squad_special_idle_enable_native_contract()


def _list_make_entity_ptr_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_list_make_entity_ptr_native import (
        validate_list_make_entity_ptr_native_contract,
    )

    return validate_list_make_entity_ptr_native_contract()


def _getter_entity_ptr_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_getter_entity_ptr_native import (
        validate_getter_entity_ptr_native_contract,
    )

    return validate_getter_entity_ptr_native_contract()


def _getter_levelscript_ptr_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_getter_levelscript_ptr_native import (
        validate_getter_levelscript_ptr_native_contract,
    )

    return validate_getter_levelscript_ptr_native_contract()


def _set_enemy_ui_show_range_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_enemy_ui_show_range_native import (
        validate_set_enemy_ui_show_range_native_contract,
    )

    return validate_set_enemy_ui_show_range_native_contract()


def _set_list_buff_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_list_buff_native import (
        validate_set_list_buff_native_contract,
    )

    return validate_set_list_buff_native_contract()


def _entity_to_string_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entity_to_string_native import (
        validate_entity_to_string_native_contract,
    )

    return validate_entity_to_string_native_contract()


def _is_look_at_point_in_screen_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_is_look_at_point_in_screen_native import (
        validate_is_look_at_point_in_screen_native_contract,
    )

    return validate_is_look_at_point_in_screen_native_contract()


def _getter_list_buff_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_getter_list_buff_native import (
        validate_getter_list_buff_native_contract,
    )

    return validate_getter_list_buff_native_contract()


def _get_cur_squad_all_dead_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_cur_squad_all_dead_native import (
        validate_get_cur_squad_all_dead_native_contract,
    )

    return validate_get_cur_squad_all_dead_native_contract()


def _get_character_template_id_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_character_template_id_native import (
        validate_get_character_template_id_native_contract,
    )

    return validate_get_character_template_id_native_contract()


def _float_getter_int_to_float_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_float_getter_int_to_float_native import (
        validate_float_getter_int_to_float_native_contract,
    )

    return validate_float_getter_int_to_float_native_contract()


def _float_getter_plus_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_float_getter_plus_native import (
        validate_float_getter_plus_native_contract,
    )

    return validate_float_getter_plus_native_contract()


def _get_interactive_property_int_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_interactive_property_int_native import (
        validate_get_interactive_property_int_native_contract,
    )

    return validate_get_interactive_property_int_native_contract()


def _get_mission_save_property_int_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_mission_save_property_int_native import (
        validate_get_mission_save_property_int_native_contract,
    )

    return validate_get_mission_save_property_int_native_contract()


def _start_narrative_black_screen_teleport_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_narrative_black_screen_teleport_native import (
        validate_start_narrative_black_screen_teleport_native_contract,
    )

    return validate_start_narrative_black_screen_teleport_native_contract()


def _set_squad_enable_relax_idle_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_squad_enable_relax_idle_native import (
        validate_set_squad_enable_relax_idle_native_contract,
    )

    return validate_set_squad_enable_relax_idle_native_contract()


def _character_play_montage_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_character_play_montage_native import (
        validate_character_play_montage_native_contract,
    )

    return validate_character_play_montage_native_contract()


def _on_script_pre_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_script_pre_start_native import (
        validate_on_script_pre_start_native_contract,
    )

    return validate_on_script_pre_start_native_contract()


def _bool_getter_mult_or_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_bool_getter_mult_or_native import (
        validate_bool_getter_mult_or_native_contract,
    )

    return validate_bool_getter_mult_or_native_contract()


def _play_voice_narrative_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_play_voice_narrative_native import (
        validate_play_voice_narrative_native_contract,
    )

    return validate_play_voice_narrative_native_contract()


def _scripted_char_teleport_to_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_scripted_char_teleport_to_native import (
        validate_scripted_char_teleport_to_native_contract,
    )

    return validate_scripted_char_teleport_to_native_contract()


def _scripted_char_patrol_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_scripted_char_patrol_start_native import (
        validate_scripted_char_patrol_start_native_contract,
    )

    return validate_scripted_char_patrol_start_native_contract()


def _stop_char_scripted_mode_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_stop_char_scripted_mode_native import (
        validate_stop_char_scripted_mode_native_contract,
    )

    return validate_stop_char_scripted_mode_native_contract()


def _on_any_entity_die_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_any_entity_die_native import (
        validate_on_any_entity_die_native_contract,
    )

    return validate_on_any_entity_die_native_contract()


def _on_client_global_var_changed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_client_global_var_changed_native import (
        validate_on_client_global_var_changed_native_contract,
    )

    return validate_on_client_global_var_changed_native_contract()


def _on_specific_entity_list_die_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_specific_entity_list_die_native import (
        validate_on_specific_entity_list_die_native_contract,
    )

    return validate_on_specific_entity_list_die_native_contract()


def _on_start_script_controlled_char_mode_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_start_script_controlled_char_mode_native import (
        validate_on_start_script_controlled_char_mode_native_contract,
    )

    return validate_on_start_script_controlled_char_mode_native_contract()


def _on_spawner_pause_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_pause_native import (
        validate_on_spawner_pause_native_contract,
    )

    return validate_on_spawner_pause_native_contract()


def _building_pos_hint_show_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_building_pos_hint_show_native import (
        validate_building_pos_hint_show_native_contract,
    )

    return validate_building_pos_hint_show_native_contract()


def _building_pos_hint_hide_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_building_pos_hint_hide_native import (
        validate_building_pos_hint_hide_native_contract,
    )

    return validate_building_pos_hint_hide_native_contract()


def _fac_guide_hint_enable_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_fac_guide_hint_enable_native import (
        validate_fac_guide_hint_enable_native_contract,
    )

    return validate_fac_guide_hint_enable_native_contract()


def _npc_get_pack_anim_has_clean_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_get_pack_anim_has_clean_native import (
        validate_npc_get_pack_anim_has_clean_native_contract,
    )

    return validate_npc_get_pack_anim_has_clean_native_contract()


def _on_encounter_intro_part_end_native_audit(*, game_root: Path | None = None) -> dict[str, Any]:
    from scripts.game_data.levelscript_on_encounter_intro_part_end_native import (
        validate_levelscript_on_encounter_intro_part_end_native_contract,
    )

    if game_root is None:return validate_levelscript_on_encounter_intro_part_end_native_contract()
    return _validate_native(validate_levelscript_on_encounter_intro_part_end_native_contract,game_root=game_root)


def _on_npc_dirty_block_cleaned_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_npc_dirty_block_cleaned_native import (
        validate_levelscript_on_npc_dirty_block_cleaned_native_contract,
    )

    return validate_levelscript_on_npc_dirty_block_cleaned_native_contract()


def _on_server_dialog_exit_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_server_dialog_exit_native import (
        validate_levelscript_on_server_dialog_exit_native_contract,
    )

    return validate_levelscript_on_server_dialog_exit_native_contract()


def _on_level_reset_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_level_reset_native import (
        validate_levelscript_on_level_reset_native_contract,
    )

    return validate_levelscript_on_level_reset_native_contract()


def _on_specific_entity_die_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_specific_entity_die_native import (
        validate_levelscript_on_specific_entity_die_native_contract,
    )

    return validate_levelscript_on_specific_entity_die_native_contract()


def _on_sub_game_start_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_sub_game_start_native import (
        validate_levelscript_on_sub_game_start_native_contract,
    )

    return validate_levelscript_on_sub_game_start_native_contract()


def _on_npc_patrol_checkpoint_reach_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_npc_patrol_checkpoint_reach_native import (
        validate_levelscript_on_npc_patrol_checkpoint_reach_native_contract,
    )

    return validate_levelscript_on_npc_patrol_checkpoint_reach_native_contract()


def _on_spawner_group_complete_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_spawner_group_complete_native import (
        validate_levelscript_on_spawner_group_complete_native_contract,
    )

    return validate_levelscript_on_spawner_group_complete_native_contract()


def _set_decoration_animator_int_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_decoration_animator_int_native import (
        validate_set_decoration_animator_int_native_contract,
    )

    return validate_set_decoration_animator_int_native_contract()


def _set_decoration_view_state_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_decoration_view_state_native import (
        validate_set_decoration_view_state_native_contract,
    )

    return validate_set_decoration_view_state_native_contract()


def _entity_move_to_with_speed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_entity_move_to_with_speed_native import (
        validate_entity_move_to_with_speed_native_contract,
    )

    return validate_entity_move_to_with_speed_native_contract()


def _start_fmv_and_teleport_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_fmv_and_teleport_native import (
        validate_start_fmv_and_teleport_native_contract,
    )

    return validate_start_fmv_and_teleport_native_contract()


def _disable_hud_fade_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_disable_hud_fade_native import (
        validate_disable_hud_fade_native_contract,
    )

    return validate_disable_hud_fade_native_contract()


def _stop_effect_on_npc_proxy_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_stop_effect_on_npc_proxy_native import (
        validate_stop_effect_on_npc_proxy_native_contract,
    )

    return validate_stop_effect_on_npc_proxy_native_contract()


def _npc_stop_cur_montage_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_npc_stop_cur_montage_native import (
        validate_npc_stop_cur_montage_native_contract,
    )

    return validate_npc_stop_cur_montage_native_contract()


def _set_main_char_hp_bar_active_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_main_char_hp_bar_active_native import (
        validate_set_main_char_hp_bar_active_native_contract,
    )

    return validate_set_main_char_hp_bar_active_native_contract()


def _destroy_ability_entity_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_destroy_ability_entity_native import (
        validate_destroy_ability_entity_native_contract,
    )

    return validate_destroy_ability_entity_native_contract()


def _move_bamboo_last_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_move_bamboo_last_native import (
        validate_move_bamboo_last_native_contract,
    )

    return validate_move_bamboo_last_native_contract()


def _stop_radio_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_stop_radio_native import (
        validate_stop_radio_native_contract,
    )

    return validate_stop_radio_native_contract()


def _set_bamboo_pos_index_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_bamboo_pos_index_native import (
        validate_set_bamboo_pos_index_native_contract,
    )

    return validate_set_bamboo_pos_index_native_contract()


def _is_endmin_gender_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_is_endmin_gender_native import (
        validate_is_endmin_gender_native_contract,
    )

    return validate_is_endmin_gender_native_contract()


def _teleport_gameplay_npc_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_teleport_gameplay_npc_native import (
        validate_levelscript_teleport_gameplay_npc_native_contract,
    )

    return validate_levelscript_teleport_gameplay_npc_native_contract()


def _apply_movement_setting_modifier_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_apply_movement_setting_modifier_native import (
        validate_apply_movement_setting_modifier_native_contract,
    )

    return validate_apply_movement_setting_modifier_native_contract()


def _toggle_ui_dev_only_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_toggle_ui_dev_only_native import (
        validate_toggle_ui_dev_only_native_contract,
    )

    return validate_toggle_ui_dev_only_native_contract()


def _start_cutscene_hide_scene_object_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_cutscene_hide_scene_object_native import (
        validate_start_cutscene_hide_scene_object_native_contract,
    )

    return validate_start_cutscene_hide_scene_object_native_contract()


def _start_cutscene_control_scene_object_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_start_cutscene_control_scene_object_native import (
        validate_start_cutscene_control_scene_object_native_contract,
    )

    return validate_start_cutscene_control_scene_object_native_contract()


def _set_squad_icon_active_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_squad_icon_active_native import (
        validate_set_squad_icon_active_native_contract,
    )

    return validate_set_squad_icon_active_native_contract()


def _skip_entity_die_display_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_skip_entity_die_display_native import (
        validate_skip_entity_die_display_native_contract,
    )

    return validate_skip_entity_die_display_native_contract()


def _get_script_task_objective_is_completed_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_script_task_objective_is_completed_native import (
        validate_get_script_task_objective_is_completed_native_contract,
    )

    return validate_get_script_task_objective_is_completed_native_contract()


def _on_any_enemy_poise_zero_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_any_enemy_poise_zero_native import (
        validate_on_any_enemy_poise_zero_native_contract,
    )

    return validate_on_any_enemy_poise_zero_native_contract()


def _on_any_enemy_poise_knot_break_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_any_enemy_poise_knot_break_native import (
        validate_on_any_enemy_poise_knot_break_native_contract,
    )

    return validate_on_any_enemy_poise_knot_break_native_contract()


def _on_aether_lock_endpoint_scanned_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_aether_lock_endpoint_scanned_native import (
        validate_levelscript_on_aether_lock_endpoint_scanned_native_contract,
    )

    return validate_levelscript_on_aether_lock_endpoint_scanned_native_contract()


def _on_cutscene_exit_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_cutscene_exit_native import (
        validate_levelscript_on_cutscene_exit_native_contract,
    )

    return validate_levelscript_on_cutscene_exit_native_contract()


def _on_entity_die_native_audit(*, game_root: Path | None = None) -> dict[str, Any]:
    from scripts.game_data.levelscript_on_entity_die_native import (
        validate_levelscript_on_entity_die_native_contract,
    )

    if game_root is None:return validate_levelscript_on_entity_die_native_contract()
    return _validate_native(validate_levelscript_on_entity_die_native_contract,game_root=game_root)


def _on_blight_miasma_weak_guide_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_on_blight_miasma_weak_guide_native import (
        validate_levelscript_on_blight_miasma_weak_guide_native_contract,
    )

    return validate_levelscript_on_blight_miasma_weak_guide_native_contract()


def _event_args_float_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_event_args_float_native import (
        validate_event_args_float_native_contract,
    )

    return validate_event_args_float_native_contract()


def _audio_cue_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_audio_cue_native import (
        validate_audio_cue_native_contract,
    )

    return validate_audio_cue_native_contract()


def _override_npc_dialog_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_override_npc_dialog_native import (
        validate_override_npc_dialog_native_contract,
    )

    return validate_override_npc_dialog_native_contract()


def _getter_compare_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_getter_compare_native import (
        validate_getter_compare_native_contract,
    )

    return validate_getter_compare_native_contract()


def _get_mission_state_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_get_mission_state_native import (
        validate_get_mission_state_native_contract,
    )

    return validate_get_mission_state_native_contract()


def _water_height_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_water_height_native import (
        validate_water_height_native_contract,
    )

    return validate_water_height_native_contract()


def _set_fac_mode_native_audit() -> dict[str, Any]:
    from scripts.game_data.levelscript_set_fac_mode_native import (
        validate_set_fac_mode_native_contract,
    )

    return validate_set_fac_mode_native_contract()


_NATIVE_GATE_CONTRACTS = (
    ("levelscript_set_spawner_ptr_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_set_spawner_ptr_native"),
    ("levelscript_airwall_enable_fields_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_airwall_enable_fields_native"),
    ("levelscript_entity_list_take_damage_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_entity_list_take_damage_native"),
    ("levelscript_blackboard_fields_native.json", "endfield.levelscript-route-deserialize-native.v4", "levelscript_blackboard_fields_native"),
    ("levelscript_stored_routes_current_native.json", "endfield.levelscript-route-deserialize-native.v4", "levelscript_stored_routes_current_native"),
    ("levelscript_black_screen_fades_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_black_screen_fades_native"),
    ("levelscript_preload_controls_native.json", "endfield.levelscript-route-deserialize-native.v5", "levelscript_preload_controls_native"),
    ("levelscript_on_squad_member_usp_fields_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_on_squad_member_usp_fields_native"),
    ("levelscript_blend_camera_transform_fields_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_blend_camera_transform_fields_native"),
    ("levelscript_npc_proxy_envtalk_fields_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_npc_proxy_envtalk_fields_native"),
    ("levelscript_play_fmv_fields_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_play_fmv_fields_native"),
    ("levelscript_entity_attach_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_entity_attach_native"),
    ("levelscript_spawner_camera_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_spawner_camera_native"),
    ("levelscript_route_deserialize_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_route_deserialize_native"),
    ("levelscript_stored_routes_native.json", "endfield.levelscript-route-deserialize-native.v6", "levelscript_stored_routes_native"),
    ("levelscript_remove_camera_control_state_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_remove_camera_control_state_native"),
    ("levelscript_camera_look_at_fields_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_camera_look_at_fields_native"),
    ("levelscript_residual_routes_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_residual_routes_native"),
    ("levelscript_check_is_squad_in_fight_native.json", "endfield.levelscript-route-deserialize-native.v4", "levelscript_check_is_squad_in_fight_native"),
    ("levelscript_get_client_map_var_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_get_client_map_var_native"),
    ("levelscript_get_squad_in_fight_native.json", "endfield.levelscript-route-deserialize-native.v2", "levelscript_get_squad_in_fight_native"),
    ("levelscript_header_native.json", "endfield.levelscript-header-native-contract.v1", "levelscript_header_native"),
    ("levelscript_finish_scene_effect_native.json", "endfield.levelscript-finish-scene-effect-native-contract.v2", "levelscript_finish_scene_effect_native"),
    ("levelscript_getter_int_native.json", "endfield.levelscript-getter-int-native-contract.v1", "levelscript_getter_int_native"),
    ("levelscript_getter_compare_native.json", "endfield.levelscript-getter-compare-native-contract.v1", "levelscript_getter_compare_native"),
    ("levelscript_get_mission_state_native.json", "endfield.levelscript-get-mission-state-native-contract.v1", "levelscript_get_mission_state_native"),
    ("levelscript_water_height_native.json", "endfield.levelscript-water-height-native-contract.v1", "levelscript_water_height_native"),
    ("levelscript_set_fac_mode_native.json", "endfield.levelscript-set-fac-mode-native-contract.v1", "levelscript_set_fac_mode_native"),
    ("levelscript_npc_proxy_patrol_stop_native.json", "endfield.levelscript-npc-proxy-patrol-stop-native-contract.v2", "levelscript_npc_proxy_patrol_stop_native"),
    ("levelscript_post_audio_status_native.json", "endfield.levelscript-post-audio-status-native-contract.v1", "levelscript_post_audio_status_native"),
    ("levelscript_entities_visibility_native.json", "endfield.levelscript-entities-visibility-native-contract.v1", "levelscript_entities_visibility_native"),
    ("levelscript_track_camera_native.json", "endfield.levelscript-track-camera-native-contract.v2", "levelscript_track_camera_native"),
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
    ("levelscript_start_seq_loop_native.json", "endfield.levelscript-start-level-seq-loop-segment-native-contract.v2", "levelscript_start_seq_loop_native"),
    ("levelscript_entity_scanned_native.json", "endfield.levelscript-entity-scanned-native-contract.v1", "levelscript_entity_scanned_native"),
    ("levelscript_squad_fight_header_native.json", "endfield.levelscript-squad-fight-header-native-contract.v1", "levelscript_squad_fight_header_native"),
    ("levelscript_leader_enter_trigger_volume_native.json", "endfield.levelscript-leader-enter-trigger-volume-native-contract.v1", "levelscript_leader_enter_trigger_volume_native"),
    ("levelscript_squad_all_die_header_native.json", "endfield.levelscript-squad-all-die-header-native-contract.v1", "levelscript_squad_all_die_header_native"),
    ("levelscript_tracking_point_native.json", "endfield.levelscript-tracking-point-native-contract.v1", "levelscript_tracking_point_native"),
    ("levelscript_mission_changed_header_native.json", "endfield.levelscript-mission-changed-header-native-contract.v1", "levelscript_mission_changed_header_native"),
    ("levelscript_cutscene_teleport_native.json", "endfield.levelscript-cutscene-teleport-native-contract.v2", "levelscript_cutscene_teleport_native"),
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
    ("levelscript_get_interactive_property_int_native.json", "endfield.levelscript-get-interactive-property-int-native-contract.v1", "levelscript_get_interactive_property_int_native"),
    ("levelscript_get_mission_save_property_int_native.json", "endfield.levelscript-get-mission-save-property-int-native-contract.v1", "levelscript_get_mission_save_property_int_native"),
    ("levelscript_start_narrative_black_screen_teleport_native.json", "endfield.levelscript-start-narrative-black-screen-teleport-native-contract.v1", "levelscript_start_narrative_black_screen_teleport_native"),
    ("levelscript_set_squad_enable_relax_idle_native.json", "endfield.levelscript-set-squad-enable-relax-idle-native-contract.v1", "levelscript_set_squad_enable_relax_idle_native"),
    ("levelscript_character_play_montage_native.json", "endfield.levelscript-character-play-montage-native-contract.v1", "levelscript_character_play_montage_native"),
    ("levelscript_on_script_pre_start_native.json", "endfield.levelscript-on-script-pre-start-native-contract.v1", "levelscript_on_script_pre_start_native"),
    ("levelscript_bool_getter_mult_or_native.json", "endfield.levelscript-bool-getter-mult-or-native.v1", "levelscript_bool_getter_mult_or_native"),
    ("levelscript_play_voice_narrative_native.json", "endfield.levelscript-play-voice-narrative-native-contract.v1", "levelscript_play_voice_narrative_native"),
    ("levelscript_scripted_char_teleport_to_native.json", "endfield.levelscript-scripted-char-teleport-to-native-contract.v1", "levelscript_scripted_char_teleport_to_native"),
    ("levelscript_scripted_char_patrol_start_native.json", "endfield.levelscript-scripted-char-patrol-start-native-contract.v1", "levelscript_scripted_char_patrol_start_native"),
    ("levelscript_stop_char_scripted_mode_native.json", "endfield.levelscript-stop-char-scripted-mode-native-contract.v1", "levelscript_stop_char_scripted_mode_native"),
    ("levelscript_on_any_entity_die_native.json", "endfield.levelscript-on-any-entity-die-native-contract.v1", "levelscript_on_any_entity_die_native"),
    ("levelscript_on_client_global_var_changed_native.json", "endfield.levelscript-on-client-global-var-changed-native-contract.v1", "levelscript_on_client_global_var_changed_native"),
    ("levelscript_on_specific_entity_list_die_native.json", "endfield.levelscript-on-specific-entity-list-die-native-contract.v1", "levelscript_on_specific_entity_list_die_native"),
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
    ("levelscript_stop_radio_native.json", "endfield.levelscript-stop-radio-native-contract.v1", "levelscript_stop_radio_native"),
    ("levelscript_set_bamboo_pos_index_native.json", "endfield.levelscript-set-bamboo-pos-index-native-contract.v1", "levelscript_set_bamboo_pos_index_native"),
    ("levelscript_is_endmin_gender_native.json", "endfield.levelscript-is-endmin-gender-native.v1", "levelscript_is_endmin_gender_native"),
    ("levelscript_teleport_gameplay_npc_native.json", "endfield.levelscript-teleport-gameplay-npc-native.v1", "levelscript_teleport_gameplay_npc_native"),
    ("levelscript_apply_movement_setting_modifier_native.json", "endfield.levelscript-apply-movement-setting-modifier-native.v1", "levelscript_apply_movement_setting_modifier_native"),
    ("levelscript_toggle_ui_dev_only_native.json", "endfield.levelscript-toggle-ui-dev-only-native.v1", "levelscript_toggle_ui_dev_only_native"),
    ("levelscript_start_cutscene_hide_scene_object_native.json", "endfield.levelscript-start-cutscene-hide-scene-object-native.v2", "levelscript_start_cutscene_hide_scene_object_native"),
    ("levelscript_start_cutscene_control_scene_object_native.json", "endfield.levelscript-start-cutscene-control-scene-object-native.v2", "levelscript_start_cutscene_control_scene_object_native"),
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
)


def _required_native_gates() -> dict[tuple[str, int], str]:
    families,audit=_union_tags()._load()
    if audit.get('status')!='validated':return {}
    signatures=[]
    for filename,schema,gate in _NATIVE_GATE_CONTRACTS:
        stat=(CONTRACTS_DIR/filename).stat()
        signatures.append((filename,schema,gate,stat.st_mtime_ns,stat.st_size))
    tag_rows=tuple((family,tuple(sorted(rows.items()))) for family,rows in sorted(families.items()))
    return _required_native_gates_cached(tuple(signatures),tag_rows)


@lru_cache(maxsize=2)
def _required_native_gates_cached(signatures: tuple, tag_rows: tuple) -> dict[tuple[str, int], str]:
    """Read selected route identities from their reviewed contracts."""
    required: dict[tuple[str, int], str] = {}
    families={family:dict(rows) for family,rows in tag_rows}
    for filename, schema, gate, *_ in signatures:
        contract = json.loads((CONTRACTS_DIR / filename).read_bytes())
        if contract.get("schema") != schema or contract.get("status") != "exact-current-build":
            raise ActionMapCodecError(f"actionMap.nativeGate:contract-status={filename}")
        routes = contract.get("routes", [contract.get("route")])
        for route in routes:
            if not isinstance(route, dict):
                raise ActionMapCodecError(f"actionMap.nativeGate:contract-route={filename}")
            family = route.get("codecFamily", route.get("family"))
            wrapper = route.get("wrapperName")
            if not isinstance(family, str) or not isinstance(wrapper, str):
                raise ActionMapCodecError(f"actionMap.nativeGate:contract-identity={filename}")
            # The route's recorded tag pins the build it was proved on; key it
            # by name at the installed build's tag so a renumbered union can
            # never attach this gate to a different type.  An unresolved name
            # adds no requirement: the route's own audit still fails closed.
            tags = _union_tags()
            current = families.get(_UNION_TAG_FAMILY.get(family, family),{}).get(tags.short_name(wrapper),('unavailable',))
            if not isinstance(current[0], int):
                continue
            key = (family, current[0])
            if key in required:
                raise ActionMapCodecError(f"actionMap.nativeGate:contract-identity={filename}")
            required[key] = gate
    return required


def _require_selected_native(family: str, tag: int, layout: dict[str, Any], *, game_root: Path | None = None) -> None:
    """Keep selected native routes unavailable on build or body drift."""
    reviewed = (_condition_layouts().get(tag) if family == 'GameCondition'
                else _layouts().get((family, tag)))
    if reviewed is None:
        if family == 'GameCondition' and _required_native_gates().get((family, tag)) is not None:
            raise ActionMapCodecError(f'actionMap.nativeContract:missing-reviewed-condition-layout=0x{tag:04x}')
        return
    native_gate = reviewed.get("nativeGate")
    required = _required_native_gates().get((family, tag))
    if required is not None and native_gate != required:
        raise ActionMapCodecError(
            f"actionMap.nativeGate:missing-gate={family}:0x{tag:04x},required={required}"
        )
    if native_gate is None:
        return
    route_audits = {
        "levelscript_set_spawner_ptr_native": (None,"actionMap.setSpawnerPtrNative"),
        "levelscript_airwall_enable_fields_native": (None,"actionMap.airWallEnableFieldsNative"),
        "levelscript_entity_list_take_damage_native": (None,"actionMap.entityListTakeDamageNative"),
        "levelscript_blackboard_fields_native": (None,"actionMap.blackboardFieldsNative"),
        "levelscript_stored_routes_current_native": (None,"actionMap.storedRoutesCurrentNative"),
        "levelscript_black_screen_fades_native": (None,"actionMap.blackScreenFadesNative"),
        "levelscript_preload_controls_native": (None,"actionMap.preloadControlsNative"),
        "levelscript_on_squad_member_usp_fields_native": (None,"actionMap.squadMemberUspFieldsNative"),
        "levelscript_blend_camera_transform_fields_native": (None,"actionMap.blendCameraTransformFieldsNative"),
        "levelscript_npc_proxy_envtalk_fields_native": (None,"actionMap.npcProxyEnvTalkFieldsNative"),
        "levelscript_play_fmv_fields_native": (None,"actionMap.playFmvFieldsNative"),
        "levelscript_entity_attach_native": (None,"actionMap.entityAttachNative"),
        "levelscript_spawner_camera_native": (None,"actionMap.spawnerCameraNative"),
        "levelscript_route_deserialize_native": (None,"actionMap.routeDeserializeNative"),
        "levelscript_stored_routes_native": (None, "actionMap.storedRoutesNative"),
        "levelscript_remove_camera_control_state_native": (None,"actionMap.removeCameraControlStateNative"),
        "levelscript_camera_look_at_fields_native": (None,"actionMap.cameraLookAtFieldsNative"),
        "levelscript_residual_routes_native": (None,"actionMap.residualRoutesNative"),
        "levelscript_check_is_squad_in_fight_native": (None,"actionMap.checkIsSquadInFightNative"),
        "levelscript_get_client_map_var_native": (None, "actionMap.getClientMapVarNative"),
        "levelscript_get_squad_in_fight_native": (None, "actionMap.getSquadInFightNative"),
    }
    if native_gate in route_audits:
        reader, label = route_audits[native_gate]
        if reader is None:
            from scripts.game_data.levelscript_route_deserialize_native import validate
            root = Path(game_root) if game_root is not None else None
            audit = _validate_native(validate,contract_path=CONTRACTS_DIR/(native_gate+'.json'),
                selected_route=(family,tag),
                gameassembly=root.parent/'GameAssembly.dll' if root else None,
                metadata=root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        else:audit = reader()
        selected = next((row for row in audit.get("validatedRows", [])
                         if (row.get("family"), row.get("tag")) == (family, tag)), None)
        if (audit.get("status") != "validated" or selected is None
                or selected.get("wrapperName") != reviewed.get("wrapperName")
                or (family == 'GameCondition' and selected.get('memberCount') != reviewed.get('memberCount'))
                or selected.get("fields") != reviewed.get("fields")
                or layout.get("wrapperName") != reviewed.get("wrapperName")
                or layout.get("fields") != reviewed.get("fields")):
            raise ActionMapCodecError(
                f"{label}:unavailable={family}:0x{tag:04x},"
                f"status={audit.get('status')},check={audit.get('failedCheck')},detail={audit.get('detail')}"
            )
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
        "levelscript_get_interactive_property_int_native",
        "levelscript_get_mission_save_property_int_native",
        "levelscript_start_narrative_black_screen_teleport_native",
        "levelscript_set_squad_enable_relax_idle_native",
        "levelscript_character_play_montage_native",
        "levelscript_on_script_pre_start_native",
        "levelscript_bool_getter_mult_or_native",
        "levelscript_play_voice_narrative_native",
        "levelscript_scripted_char_teleport_to_native",
        "levelscript_scripted_char_patrol_start_native",
        "levelscript_stop_char_scripted_mode_native",
        "levelscript_on_any_entity_die_native",
        "levelscript_on_client_global_var_changed_native",
        "levelscript_on_specific_entity_list_die_native",
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
        "levelscript_stop_radio_native",
        "levelscript_set_bamboo_pos_index_native",
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
            "levelscript_get_interactive_property_int_native": _get_interactive_property_int_native_audit,
            "levelscript_get_mission_save_property_int_native": _get_mission_save_property_int_native_audit,
            "levelscript_start_narrative_black_screen_teleport_native": _start_narrative_black_screen_teleport_native_audit,
            "levelscript_set_squad_enable_relax_idle_native": _set_squad_enable_relax_idle_native_audit,
            "levelscript_character_play_montage_native": _character_play_montage_native_audit,
            "levelscript_on_script_pre_start_native": _on_script_pre_start_native_audit,
            "levelscript_bool_getter_mult_or_native": _bool_getter_mult_or_native_audit,
            "levelscript_play_voice_narrative_native": _play_voice_narrative_native_audit,
            "levelscript_scripted_char_teleport_to_native": _scripted_char_teleport_to_native_audit,
            "levelscript_scripted_char_patrol_start_native": _scripted_char_patrol_start_native_audit,
            "levelscript_stop_char_scripted_mode_native": _stop_char_scripted_mode_native_audit,
            "levelscript_on_any_entity_die_native": _on_any_entity_die_native_audit,
            "levelscript_on_client_global_var_changed_native": _on_client_global_var_changed_native_audit,
            "levelscript_on_specific_entity_list_die_native": _on_specific_entity_list_die_native_audit,
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
            "levelscript_stop_radio_native": _stop_radio_native_audit,
            "levelscript_set_bamboo_pos_index_native": _set_bamboo_pos_index_native_audit,
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
        audit = validators[native_gate](game_root=game_root) if native_gate == 'levelscript_environment_enable_native' else validators[native_gate]()
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
        audit_reader = {
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
        }[native_gate]
        audit = (audit_reader(game_root=game_root) if game_root is not None and native_gate in {
            "levelscript_on_spell_abnormal_start_native", "levelscript_on_physical_infliction_native",
            "levelscript_on_bb_variable_changed_native", "levelscript_on_entity_die_native",
            "levelscript_on_encounter_intro_part_end_native",
        } else audit_reader())
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
        *,
        game_root: Path | None = None,
        strings: Any = None,
        route: dict[str, Any] | None = None,
        null_list_params: Any = None,
        numeric_list_params: Any = None, camera_shake_params: Any = None, buff_ptr_params: Any = None, entity_list_params: Any = None,
        current_owner: Any = None,
    ):
        self.data = data
        self.offset = offset
        self.declarations = declarations
        self.game_root = game_root
        self.strings = strings
        self.null_list_params = null_list_params
        self.numeric_list_params = numeric_list_params
        self.camera_shake_params = camera_shake_params
        self.buff_ptr_params = buff_ptr_params
        self.entity_list_params = entity_list_params
        self.current_owner = current_owner
        self.route = {**route, 'fields': [field[:2] for field in route['fields']], 'nativeGate': _required_native_gates().get((route.get('family'), route.get('tag')))} if route is not None else None

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
        raise ActionMapCodecError(f"{field}:current-pooled-child-source-unproved,offset={self.offset}")

    def node_string(self, field: str, layout: dict[str, Any], member: str) -> str | None:
        if layout.get('family') == 'GameCondition' and self.current_owner is not None:
            from .current_actionmap_children import decode_game_condition_string
            try:
                value, end = decode_game_condition_string(self.data, self.offset, layout,
                    field=member, current_owner=self.current_owner, strings=self.strings)
            except (OSError, KeyError, TypeError, ValueError) as error:
                raise ActionMapCodecError(f'{field}:{error}') from error
            self.offset = end
            return value
        from .node_strings import decode_node_string
        try:
            value,end=decode_node_string(self.data,self.offset,layout,_NATIVE_GATE_CONTRACTS,field=member,game_root=self.game_root,strings=self.strings)
        except (OSError,KeyError,TypeError,ValueError) as error:raise ActionMapCodecError(f'{field}:{error}') from error
        self.offset=end
        return value

    def require_scalar_param(self, kind: str, field: str) -> None:
        component={
            'Param<long>':('long_param',8,{'primitiveType':'long'}),
            'Param<SplinePtr>':('spline_ptr',4,{'fieldType':'int'}),
            'Param<GameplayTag>':('gameplay_tag_param',4,{}),
            'Param<WaterVolumePtr>':('water_volume_ptr_param',8,{}),
            'Param<EnvironmentVolumePtr>':('environment_volume_ptr_param',8,{}),
        }.get(kind)
        if component is None:return
        from importlib import import_module
        owner,width,extra=component
        module=import_module('scripts.game_data.levelscript_'+owner+'_native')
        audit=_validate_native(getattr(module,'validate_'+owner+'_native_contract'),game_root=self.game_root)
        expected={'status':'validated','codecKind':kind,'rawSize':width,'pathEncoding':'int32-pool-index',**extra}
        if any(audit.get(k)!=v for k,v in expected.items()):
            raise ActionMapCodecError(f"{field}.nativeContract:owner=levelscript_{owner}_native,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")

    def value(self, kind: str, field: str, *, parent_layout=None, member=None) -> Any:
        if kind in ('Param<List<BuffPtr>>', 'Param<ModelVisibleType>', 'Param<CommonMaskBlendData>',
                'Param<EntityPtr>[]', 'Param<ObjectPtr<GlobalBuff>>',
                'Param<Vector3>[]', 'Param<List<GameplayTag>>'):
            from .current_action_params import decode
            try:
                value, self.offset = decode(self.data, self.offset, codec_kind=kind,
                    strings=self.strings, game_root=self.game_root)
            except (OSError, KeyError, TypeError, ValueError) as error:
                raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind in ('Param<CameraShakeConfigPtr>', 'Param<BuffPtr>'):
            from importlib import import_module
            owner = 'camera_shake' if kind == 'Param<CameraShakeConfigPtr>' else 'buff_ptr'
            component = import_module('scripts.game_data.codecs.levelscript.' + owner + '_param')
            operation = self.camera_shake_params if owner == 'camera_shake' else self.buff_ptr_params
            try:
                decoded = getattr(component, 'decode_' + owner + '_param')(
                    self.data, self.offset, strings=self.strings,
                    game_root=self.game_root, operation=operation)
                if decoded is None:
                    raise ValueError('invalid-' + owner + '-param')
                value, self.offset = decoded
                return value
            except (ValueError, TypeError, KeyError, OSError) as error:
                raise ActionMapCodecError(f'{field}:{error},offset={self.offset}') from error
        if kind in ('Param<List<int>>', 'Param<List<uint>>', 'Param<List<float>>'):
            from scripts.game_data.levelscript_numeric_list_param_native import (
                validate_numeric_list_param_native_contract, prepared_numeric_list_audit,
            )
            from .numeric_list_param import decode_numeric_list_param
            try:
                audit = (_validate_native(validate_numeric_list_param_native_contract,codec_kind=kind, game_root=self.game_root)
                         if self.numeric_list_params is None else
                         prepared_numeric_list_audit(self.numeric_list_params, codec_kind=kind,
                                                     game_root=self.game_root, strings=self.strings))
                expected = dict(status='validated', codecKinds=[kind], memberCount=4, rawSize=8,
                    pathEncoding='int32-pool-index', collectionCountEncoding='int32', constantNullCount=-1,
                    elementEncodings={kind: {'Param<List<int>>': 'int32', 'Param<List<uint>>': 'uint32',
                                             'Param<List<float>>': 'float32-bits'}[kind]},
                    wholeParamNullAdmitted=True, positiveConstantsAdmitted=True)
                if any(audit.get(key) != value for key, value in expected.items()):
                    raise ValueError('numeric-list-native-unavailable:status=' + str(audit.get('status'))
                                     + ',detail=' + str(audit.get('detail', ''))[:500])
                decoded = decode_numeric_list_param(self.data, self.offset, kind=kind, strings=self.strings)
                if decoded is None:
                    raise ValueError('invalid-numeric-list-param')
                value, self.offset = decoded
                return value
            except (ValueError, TypeError, KeyError, OSError) as error:
                raise ActionMapCodecError(f'{field}:{error},offset={self.offset}') from error
        if kind == 'List<string>':
            from .positive_string_list import decode_literal
            try:value,self.offset=decode_literal(self.data,self.offset,strings=self.strings,game_root=self.game_root)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind == 'Param<List<LangKey>>':
            from .positive_lang_key_list import decode_param
            try:value,self.offset=decode_param(self.data,self.offset,strings=self.strings,game_root=self.game_root)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind == 'Param<List<string>>':
            from .positive_string_list import decode_param
            try:value,self.offset=decode_param(self.data,self.offset,strings=self.strings,game_root=self.game_root)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind == 'Param<List<Vector3>>':
            from .positive_vector3_list import decode_param
            try:value,self.offset=decode_param(self.data,self.offset,strings=self.strings,game_root=self.game_root)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind == 'Param<List<ulong>>':
            from .positive_ulong_list import decode_param
            try:value,self.offset=decode_param(self.data,self.offset,strings=self.strings,game_root=self.game_root)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind in('Param<LangKey>','Param<GlobalBuffId>'):
            from .nominal_key import decode_nominal_key_param
            try:value,self.offset=decode_nominal_key_param(self.data,self.offset,kind=kind,strings=self.strings,game_root=self.game_root)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind == 'Param<List<BlackboardKVPair>>':
            from .blackboard import decode_blackboard_param
            try:value,self.offset=decode_blackboard_param(self.data,self.offset,strings=self.strings,game_root=self.game_root)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind == 'Param<List<PosRot>>':
            try:value,self.offset=decode_pos_rot_param(self.data,self.offset,strings=self.strings,game_root=self.game_root)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind in ('Param<List<NpcAtmosphericOverrideEnvTalk.EnvTalkStruct>>','Param<List<NpcOverrideEnvTalk.EnvTalkStruct>>','Param<List<NpcProxyOverrideEnvTalk.EnvTalkStruct>>'):
            from scripts.game_data.levelscript_envtalk_native import validate as validate_envtalk
            from .envtalk import decode_envtalk_param
            audit=_validate_native(validate_envtalk,game_root=self.game_root)
            if audit.get('status')!='validated' or kind not in audit.get('codecKinds',[]):
                raise ActionMapCodecError(f"{field}:validator=levelscriptEnvTalkNative,check=selected-stored-grammar,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:parsed=decode_envtalk_param(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if parsed is None:raise ActionMapCodecError(f'{field}:invalid-{kind},offset={self.offset}')
            value,self.offset=parsed
            return value
        if kind == 'Param<List<EntityPtr>>' and (self.entity_list_params is not None or
                self.offset + 5 <= len(self.data) and self.data[self.offset] == 4 and
                struct.unpack_from('<i', self.data, self.offset + 1)[0] > 0):
            from .entity_list_param import decode_entity_list_param
            try:
                decoded = decode_entity_list_param(self.data, self.offset, strings=self.strings,
                    game_root=self.game_root, operation=self.entity_list_params)
                if decoded is None:
                    raise ValueError('invalid-entity-list-param')
                value, self.offset = decoded
                return value
            except (ValueError, TypeError, KeyError, OSError) as error:
                raise ActionMapCodecError(f'{field}:{error},offset={self.offset}') from error
        if kind == 'Param<List<EntityPtr>>':
            from scripts.game_data.levelscript_null_list_param_native import validate_null_list_param_native_contract,prepared_null_list_audit
            from .null_list_param import decode_null_list_param
            audit=(_validate_native(validate_null_list_param_native_contract,codec_kind=kind,game_root=self.game_root) if self.null_list_params is None else prepared_null_list_audit(self.null_list_params,codec_kind=kind,game_root=self.game_root,strings=self.strings))
            counts=[-1,0]
            expected=dict(status='validated',codecKinds=[kind],memberCount=4,rawSize=8,pathEncoding='int32-pool-index',collectionCounts={kind:counts})
            if any(audit.get(k)!=v for k,v in expected.items()):
                raise ActionMapCodecError(f"{field}:null-list-composition-unproved,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:decoded=decode_null_list_param(self.data,self.offset,strings=self.strings,collection_counts=audit['collectionCounts'][kind])
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if decoded is None:
                actual=struct.unpack_from('<i',self.data,self.offset+1)[0] if self.offset+5<=len(self.data) else None
                raise ActionMapCodecError(f'{field}:list-count-or-framing-unproved,offset={self.offset+1},expected={counts},actual={actual}')
            value,self.offset=decoded
            return value
        if kind == 'Param<AirWallPtr>':
            from scripts.game_data.levelscript_airwall_ptr_param_native import validate as validate_airwall
            from .airwall_ptr_param import decode_airwall_ptr_param
            audit=_validate_native(validate_airwall,game_root=self.game_root)
            expected=dict(status='validated',codecKind=kind,memberCount=4,rawSize=24,pathEncoding='int32-pool-index')
            if any(audit.get(k)!=v for k,v in expected.items()):
                raise ActionMapCodecError(f"{field}:airwall-ptr-composition-unproved,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:parsed=decode_airwall_ptr_param(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if parsed is None:raise ActionMapCodecError(f'{field}:invalid-{kind},offset={self.offset}')
            value,self.offset=parsed
            return value
        if kind == 'Param<EntityPtr>':
            from scripts.game_data.levelscript_entity_ptr_param_native import validate_entity_ptr_param_native_contract
            from .entity_ptr_param import decode_entity_ptr_param
            audit=_validate_native(validate_entity_ptr_param_native_contract,game_root=self.game_root)
            expected=dict(status='validated',codecKind=kind,memberCount=4,rawSize=40,pathEncoding='int32-pool-index')
            if any(audit.get(k)!=v for k,v in expected.items()):
                raise ActionMapCodecError(f"{field}:entity-ptr-composition-unproved,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:decoded=decode_entity_ptr_param(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if decoded is None:raise ActionMapCodecError(f'{field}:invalid-or-unproved-{kind},offset={self.offset}')
            value,self.offset=decoded
            return value
        if kind == 'Param<EventArgsPtr>':
            from scripts.game_data.levelscript_event_args_param_native import validate_event_args_param_native_contract
            from .event_args_param import decode_event_args_param
            audit=_validate_native(validate_event_args_param_native_contract,game_root=self.game_root)
            expected=dict(status='validated',codecKind=kind,memberCount=4,rawSize=8,pathEncoding='int32-pool-index')
            if any(audit.get(k)!=v for k,v in expected.items()):
                raise ActionMapCodecError(f"{field}:event-args-composition-unproved,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:decoded=decode_event_args_param(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if decoded is None:raise ActionMapCodecError(f'{field}:invalid-or-unproved-{kind},offset={self.offset}')
            value,self.offset=decoded
            return value
        if kind == 'Param<CameraControlState>':
            from scripts.game_data.levelscript_camera_state_param_native import validate_camera_state_param_native_contract
            from .camera_state_param import decode_camera_state_param
            audit=_validate_native(validate_camera_state_param_native_contract,game_root=self.game_root)
            expected=dict(status='validated',codecKind=kind,memberCount=4,rawSize=8,pathEncoding='int32-pool-index',constantNullMarker=255,constantWireBytes=1,positiveConstantAdmitted=False)
            if any(audit.get(k)!=v for k,v in expected.items()):
                raise ActionMapCodecError(f"{field}:camera-state-param-composition-unproved,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:decoded=decode_camera_state_param(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if decoded is None:raise ActionMapCodecError(f'{field}:invalid-or-positive-{kind},offset={self.offset}')
            value,self.offset=decoded
            return value
        if kind == 'Param<CameraControlStateInitialParam>':
            from scripts.game_data.levelscript_camera_initial_param_native import validate_camera_initial_param_native_contract
            from .camera_initial_param import decode_camera_initial_param
            audit=_validate_native(validate_camera_initial_param_native_contract,game_root=self.game_root)
            expected=dict(status='validated',codecKind=kind,memberCount=4,rawSize=24,pathEncoding='int32-pool-index')
            if any(audit.get(k)!=v for k,v in expected.items()) or not audit.get('fields'):
                raise ActionMapCodecError(f"{field}:camera-initial-param-composition-unproved,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:decoded=decode_camera_initial_param(self.data,self.offset,audit['fields'],strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if decoded is None:raise ActionMapCodecError(f'{field}:invalid-{kind},offset={self.offset}')
            value,self.offset=decoded
            return value
        if kind == 'Param<CameraBlendCurveKey>':
            from .curve_key_param import decode_curve_key_param
            try:value,self.offset=decode_curve_key_param(self.data,self.offset,strings=self.strings,game_root=self.game_root)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            return value
        if kind=='Param<ETrackCameraTargetType>':
            from scripts.game_data.levelscript_camera_target_param_native import validate_camera_target_param_native_contract
            from scripts.game_data.codecs.levelscript.int_param import decode_int_param
            audit=_validate_native(validate_camera_target_param_native_contract,game_root=self.game_root)
            expected=dict(status='validated',codecKind=kind,memberCount=4,rawSize=4,pathEncoding='int32-pool-index')
            if any(audit.get(k)!=v for k,v in expected.items()):
                raise ActionMapCodecError(f"{field}:camera-target-param-composition-unproved,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:decoded=decode_int_param(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if decoded is None:raise ActionMapCodecError(f'{field}:invalid-{kind},offset={self.offset}')
            value,self.offset=decoded
            return value
        if kind=='Param<EnterDollyTrackCamera.TrackCameraMoveState>':
            from scripts.game_data.levelscript_enum_param_native import validate_enum_param_native_contract
            from scripts.game_data.codecs.levelscript.track_camera import decode_move_state_param
            audit=_validate_native(validate_enum_param_native_contract,codec_kind=kind,game_root=self.game_root)
            expected=dict(status='validated',codecKinds=[kind],memberCount=4,rawSize=4,pathEncoding='int32-pool-index')
            if any(audit.get(k)!=v for k,v in expected.items()):
                raise ActionMapCodecError(f"{field}:enum-param-composition-unproved={kind},status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            camera=_track_camera_native_audit()
            if camera.get('status')!='validated':
                raise ActionMapCodecError(f"{field}:trackCameraEnumNative:status={camera.get('status')},detail={str(camera.get('detail',''))[:500]}")
            value,end=decode_move_state_param(self.data,self.offset,{value:name for name,value in camera['enumMembers']},strings=self.strings)
            self.offset=end
            return value
        if kind in ('Param<LsmPtr>','Param<SpawnerPtr>','Param<FunctionAreaPtr>'):
            from scripts.game_data.levelscript_pod_id_param_native import validate
            from .pod_id_param import decode_pod_id_param
            audit=_validate_native(validate,kind,game_root=self.game_root)
            if any(audit.get(k)!=v for k,v in dict(status='validated',codecKind=kind,memberCount=4,rawSize=8,pathEncoding='int32-pool-index').items()):
                raise ActionMapCodecError(f"{field}:{kind}-pointer-param-unproved,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            parsed=decode_pod_id_param(self.data,self.offset,strings=self.strings)
            if parsed is None:raise ActionMapCodecError(f'{field}:invalid-{kind},offset={self.offset}')
            value,self.offset=parsed
            return value
        if kind=='Param<LevelScriptPtr>':
            from scripts.game_data.levelscript_script_ptr_param_native import validate_script_ptr_param_native_contract
            from .levelscript_ptr_param import decode_levelscript_ptr_param
            audit=_validate_native(validate_script_ptr_param_native_contract,game_root=self.game_root)
            expected=dict(status='validated',codecKind=kind,memberCount=4,rawSize=16,pathEncoding='int32-pool-index')
            if any(audit.get(k)!=v for k,v in expected.items()):
                raise ActionMapCodecError(f"{field}:script-pointer-param-unproved,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:parsed=decode_levelscript_ptr_param(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if parsed is None:raise ActionMapCodecError(f'{field}:invalid-{kind},offset={self.offset}')
            value,self.offset=parsed
            return value
        if kind=='Param<byte>':
            raise ActionMapCodecError(f'{field}:param-component-unproved={kind}')
        if kind in ('Param<AudioBlackScreenBehaviour.ERetainFlag>','Param<AudioBlackScreenBehaviour.EPresetBehaviour>','Param<Deco_MountPoint>'):
            from scripts.game_data.levelscript_byte_enum_param_native import validate_byte_enum_param_native_contract
            from .byte_enum_param import decode_byte_enum_param
            audit=_validate_native(validate_byte_enum_param_native_contract,codec_kind=kind,game_root=self.game_root)
            if any(audit.get(k)!=v for k,v in dict(status='validated',codecKinds=[kind],memberCount=4,rawSize=1,pathEncoding='int32-pool-index',valueEncoding='uint8').items()):
                raise ActionMapCodecError(f"{field}:byte-enum-param-composition-unproved={kind},status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:decoded=decode_byte_enum_param(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if decoded is None:raise ActionMapCodecError(f'{field}:invalid-{kind},offset={self.offset}')
            value,self.offset=decoded
            return value
        # An enum backing type does not prove its selected Param formatter.
        if kind in (
            'Param<BuildingPosHintShow.EBuildingRot>',
            'Param<SpellAbnormalType>',
            'Param<PhysicalInflictionType>',
            'Param<TaskObjectiveEnum>',
            'Param<EnergyShardType>',
            'Param<OnSpawnerEntitySpawn.FilterType>',
            'Param<OnSpawnerEntityDie.FilterType>',
            'Param<SkillTypeMask>',
            'Param<NodeLookAtType>',
            'Param<CommonTrackingPointStyleType>',
            'Param<CommonTrackingType>',
            'Param<OnMissionStateChanged.FilterMissionStateEnum>',
            'Param<TeleportUIType>',
            'Param<ChapterEffectType>',
            'Param<EAudioVarScope>',
            'Param<EAudioCueVarType>',
            'Param<BoolComparer>',
            'Param<NumberComparer>',
            'Param<MissionSystem.MissionState>',
            'Param<EntityPtrComparer>',
            'Param<SP_INTERACTIVE_OP_TYPE>',
            'Param<InteractiveAudioComponent.EAudioTriggerState>',
            'Param<TweenManager.TweenEase>',
            'Param<FacBuildingState>',
            'Param<FCNodeMode>',
            'Param<CinemachineBlendDefinition.Style>',
            'Param<CommonBlendCamResetType>',
            'Param<AudioCueSystem.EBehaviourType>',
            'Param<AudioPlaceholderMusicUtil.EPlaceholderMusicFadeInType>',
            'Param<RadioVoiceAttenuationType>',
            'Param<AudioMusicSystem.EMusicEventPreAction>',
            'Param<LimitedGuideIconType>',
            'Param<LimitedGuideType>',
            'Param<OnQuestStateChanged.FilterQuestStateEnum>',
            'Param<MovementComponent.GroundedMoveGait>',
            'Param<MountPoint>',
            'Param<NpcEffectType>',
            'Param<PlayerController.InputActionType>',
            'Param<EnemyAIModeType>',
            'Param<ENPCAnimationAvatarMaskType>',
            'Param<NPCMontageAnim.EMontageStateType>',
            'Param<MissionSystem.QuestState>',
            'Param<SetCharSkillButtonActive.CharSkillTypeMask>',
            'Param<CharacterAIModeType>',
            'Param<GameAction.EAudioMusicBaseState>',
            'Param<GameAction.EAudioBattleMusicIntensityState>',
            'Param<GameAction.EAudioBattleMusicState>',
            'Param<CompareOperator>',
            'Param<ServerGameVarEnum>',
            'Param<MovementSettingName>',
            'Param<ECharTutorialStepState>',
            'Param<ShowUIToast.ShowToastType>',
            'Param<ForbidType>',
            'Param<GeneralAbilityType>',
            'Param<UnlockSystemType>',
            'Param<GeneralAbilitySystem.TempAbilityActiveState>',
            'Param<CastTargetType>',
            'Param<ScriptEndReason>',
            'Param<Gender>',
            'Param<RollingStoneController.ManipulateLauncherOp>',
            'Param<CinematicOptionBrain.EOperation>',
        ):
            from scripts.game_data.levelscript_enum_param_native import validate_enum_param_native_contract
            from .int_param import decode_int_param
            audit=_validate_native(validate_enum_param_native_contract,codec_kind=kind,game_root=self.game_root)
            if ((audit.get('status'),audit.get('codecKinds'),audit.get('memberCount'),audit.get('rawSize'),audit.get('pathEncoding'))
                    !=('validated',[kind],4,4,'int32-pool-index')):
                raise ActionMapCodecError(f"{field}:enum-param-composition-unproved={kind},status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:decoded=decode_int_param(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if decoded is None:raise ActionMapCodecError(f'{field}:invalid-{kind},offset={self.offset}')
            value,end=decoded;self.offset=end
            if isinstance(value,dict) and value.get('paramSource')==0:
                # The formatter proves an Int32 read, not an enum whitelist.
                # Preserve unnamed constants and label only unique declarations.
                names=[r['name'] for r in audit.get('enumValues',[]) if r['id']==value['value']]
                if len(names)==1:value['enumName']=names[0]
            return value
        if kind == "Param<ScriptTaskPtr>":
            if self.current_owner is not None:
                from .current_actionmap_children import decode_script_task_ptr_param
                try:
                    detail, self.offset = decode_script_task_ptr_param(self.data, self.offset,
                        field=field, current_owner=self.current_owner, strings=self.strings)
                except (OSError, KeyError, TypeError, ValueError) as error:
                    raise ActionMapCodecError(f'{field}:{error}') from error
                return detail
            from .mark_task_condition_failed import decode_script_task_ptr_param

            detail, self.offset = decode_script_task_ptr_param(self.data, self.offset)
            return detail
        if kind == "GameCondition":
            if self.current_owner is not None and parent_layout is not None:
                from .current_actionmap_condition_gateway import decode_condition
                try:
                    value, self.offset = decode_condition(self.data, self.offset, field=field,
                        parent_layout=parent_layout, member=member,
                        current_owner=self.current_owner, strings=self.strings)
                except (OSError, KeyError, TypeError, ValueError) as error:
                    raise ActionMapCodecError(f'{field}:{error}') from error
                return value
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
            if self.route is not None:return self.node_string(field,self.route,field.rsplit(".",1)[-1])
            if field.rsplit(".",1)[-1]=="uid":raise ActionMapCodecError(f"{field}:node-string-source-binding-required")
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
        if kind.startswith('ParamOutput<'):
            from scripts.game_data.levelscript_param_output_native import validate_param_output_native_contract
            from .param_output import decode_param_output
            audit=_validate_native(validate_param_output_native_contract,codec_kind=kind,game_root=self.game_root)
            if ((audit.get('status'),audit.get('codecKinds'),audit.get('memberCount'),audit.get('integerField'),audit.get('pathEncoding'))
                    !=('validated',[kind],2,'paramTarget','int32-pool-index')):
                raise ActionMapCodecError(f"{field}.nativeContract:owner=levelscript_param_output_native,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            try:decoded=decode_param_output(self.data,self.offset,strings=self.strings)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if decoded is None:raise ActionMapCodecError(f'{field}:unsupported-param-output,offset={self.offset}')
            value,end=decoded;self.offset=end
            return value
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
        if kind in ("List<int>", "List<ulong>", "List<Vector3>", "List<float>"):
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
            else:
                reader = lambda name: self.value(
                    "Vector3" if kind == "List<Vector3>" else "float32", name
                )
            return [reader(f"{field}[{index}]") for index in range(count)]
        if kind in ('Param<bool>','Param<int>','Param<string>','Param<float>','Param<uint>','Param<ulong>','Param<Vector2>','Param<Vector3>'):
            from scripts.game_data.levelscript_bool_param_native import validate_bool_param_native_contract
            from scripts.game_data.levelscript_int_param_native import validate_int_param_native_contract
            from scripts.game_data.levelscript_string_param_native import validate_string_param_native_contract
            from scripts.game_data.levelscript_float_param_native import validate_float_param_native_contract
            from scripts.game_data.levelscript_uint_param_native import validate_uint_param_native_contract
            from scripts.game_data.levelscript_ulong_param_native import validate_ulong_param_native_contract
            from scripts.game_data.levelscript_vector3_param_native import validate_vector3_param_native_contract
            from scripts.game_data.levelscript_vector2_param_native import validate_vector2_param_native_contract
            from .boolean_param import decode_bool_param
            from .int_param import decode_int_param
            from .string_param import decode_string_param
            from .float_param import decode_float_param
            from .vector_param import decode_vector_param
            owner='vector'+kind[-2] if kind in ('Param<Vector2>','Param<Vector3>') else kind[6:-1]
            validate,decode,width={'bool':(validate_bool_param_native_contract,decode_bool_param,1),
                'int':(validate_int_param_native_contract,decode_int_param,4),'string':(validate_string_param_native_contract,decode_string_param,8),
                'float':(validate_float_param_native_contract,decode_float_param,4),'uint':(validate_uint_param_native_contract,decode_int_param,4),
                'ulong':(validate_ulong_param_native_contract,decode_int_param,8),'vector3':(validate_vector3_param_native_contract,decode_vector_param,12),
                'vector2':(validate_vector2_param_native_contract,decode_vector_param,8)}[owner]
            audit=_validate_native(validate,game_root=self.game_root)
            if ((audit.get('status'),audit.get('codecKind'),audit.get('rawSize'),audit.get('pathEncoding'))!=('validated',kind,width,'int32-pool-index')
                    or (owner=='string' and audit.get('valueEncoding')!='int32-pool-index')):
                raise ActionMapCodecError(f"{field}.nativeContract:owner=levelscript_{owner}_param_native,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]}")
            options={'unsigned':True,'width':width} if owner in ('uint','ulong') else {'dimension':int(owner[-1])} if owner in ('vector2','vector3') else {}
            try:parsed=decode(self.data,self.offset,strings=self.strings,**options)
            except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
            if parsed is None:raise ActionMapCodecError(f'{field}:invalid-{kind},offset={self.offset}')
            result,self.offset=parsed
            return result
        if kind == "Param<CameraControllerBase>":
            if self.strings is None:
                raise ActionMapCodecError(f"{field}:matching-StringPool-required,offset={self.offset}")
            from scripts.game_data.levelscript_camera_controller_param_native import validate
            audit = _validate_native(validate,game_root=self.game_root)
            if audit.get("status") != "validated" or (audit.get("layout") or {}).get("codecKind") != kind:
                raise ActionMapCodecError(f"{field}:camera-controller-param-native-unavailable,status={audit.get('status')},detail={str(audit.get('detail',''))[:500]},offset={self.offset}")
            if self.data[self.offset:self.offset+2] != b"\x04\xff":
                raise ActionMapCodecError(f"{field}:only-null-camera-constant-proved,offset={self.offset}")
            self.offset += 2
            return self.param_tail(None, field, pooled=True)
        self.require_scalar_param(kind,field)
        self.need(1, field)
        if self.data[self.offset] == 0xFF and (_generic_argument(kind,"Param") is not None or kind in ("GetterBase","ActionBase","ActionHeader")):
            self.offset += 1
            return None
        if kind == "Param<EnvironmentVolumePtr>":
            from .environment_volume_ptr import decode_environment_volume_ptr_param
            decoded = decode_environment_volume_ptr_param(self.data, self.offset, strings=self.strings)
            if decoded is None:
                raise ActionMapCodecError(f"{field}:invalid-environment-volume-ptr,offset={self.offset}")
            value, self.offset = decoded
            return value
        if kind == "Param<GameplayTag>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(
                    f"{field}:unsupported-gameplay-tag-param-members={marker}"
                )
            return self.param_tail(
                {"tagId": self.i32(field + ".value.tagId")}, field, pooled=True
            )
        if kind == "Param<long>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            fmt = '<q'
            size = struct.calcsize(fmt)
            self.need(size, field + ".value")
            values = struct.unpack_from(fmt, self.data, self.offset)
            self.offset += size
            if not all(math.isfinite(value) for value in values):
                raise ActionMapCodecError(f"{field}:non-finite")
            return self.param_tail(values[0], field, pooled=kind=='Param<long>')
        if kind == "Param<SplinePtr>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            self.need(4, field + ".value.id")
            value = struct.unpack_from("<i", self.data, self.offset)[0]
            self.offset += 4
            return self.param_tail({"id": value}, field, pooled=True)
        if kind == "Param<WaterVolumePtr>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(
                    f"{field}:unsupported-member-count={marker}"
                )
            self.need(8, field + ".value.id")
            value = struct.unpack_from("<Q", self.data, self.offset)[0]
            self.offset += 8
            return self.param_tail({"id": value}, field,pooled=kind=='Param<WaterVolumePtr>')
        if kind == "SendLuaEvent1" and field.endswith(".manualValue"):
            try:
                value, self.offset = send_lua_event.decode_nested_send_lua_event(
                    self.data, self.offset, field, 1,
                    strings=self.strings, game_root=self.game_root,
                )
            except send_lua_event.SendLuaEventDecodeError as exc:
                raise ActionMapCodecError(str(exc)) from exc
            return value
        declared = self.declared_value(kind, field)
        if declared is not _NOT_DECLARED:
            return declared
        raise ActionMapCodecError(f"{field}:unsupported-field-type={kind}")

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
        order, and with padding in between. This bounded reader requires zero
        padding; an unproved value or enclosing Param remains refused.
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
                    strings=self.strings,
                    game_root=self.game_root,
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
        memory. The enclosing reader must prove that selection: a Param's raw
        constant and a list element can use different framing for the same
        unmanaged type.
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
        _require_selected_native(family, tag, layout, game_root=self.game_root)
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

    def param_tail(self, value: Any, field: str, *, pooled: bool = False) -> dict[str, Any]:
        if not pooled:
            raise ActionMapCodecError(f"{field}:current-pooled-param-source-unproved,offset={self.offset}")
        try:
            result = params.decode_pooled_param_tail(self.data,self.offset,strings=self.strings)
        except ValueError as error:raise ActionMapCodecError(f'{field}:{error}') from error
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
        if family == "ActionBase" and _union_tags().type_name_for_tag(family, tag) == "PreloadCutsceneAction":
            from .current_action_sequence import _preload_cutscene_layout

            try:
                _preload_cutscene_layout(members)
            except ValueError as error:
                refusal = ActionMapCodecError(str(error))
                refusal.diagnostics = error.diagnostics
                raise refusal from error
        layout = _layouts().get((family, tag))
        if layout is not None:
            _require_layout_build()
        elif self.declarations is not None:
            layout = self.declarations.layouts.get((family, tag))
        else:
            # No reviewed row: name the union-tag gate when it emptied them.
            _require_layout_build()
        # Restored legacy residual rows retain their standalone gate. An
        # active Current/Existing operation keeps the generated source bridge
        # used before those independent legacy rows were restored.
        legacy_residual = (layout is not None and
            layout.get("nativeGate") == "levelscript_residual_routes_native")
        if self.current_owner is not None and (layout is None or legacy_residual):
            from .current_actionmap_route_gateway import decode
            try:
                decoded, self.offset = decode(self.data, start, family=family, tag=tag,
                    field=field, current_owner=self.current_owner, strings=self.strings)
            except (OSError, KeyError, TypeError, ValueError) as error:
                raise ActionMapCodecError(f'{field}:{error}') from error
            return decoded
        if layout is None or members != layout["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-union=0x{tag:04x},memberCount={members},offset={start}"
            )
        _require_selected_native(family, tag, layout, game_root=self.game_root)
        if layout.get("nativeGate") == "levelscript_on_spell_abnormal_start_native":
            from .on_spell_abnormal_start import decode_on_spell_abnormal_start_header

            audit = _on_spell_abnormal_start_native_audit(game_root=self.game_root) if self.game_root is not None else _on_spell_abnormal_start_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onSpellAbnormalStartNative:missing-route")
            decoded, self.offset = decode_on_spell_abnormal_start_header(
                self.data, start, route, game_root=self.game_root, strings=self.strings,
                enum_values=audit.get("enumValues", {}).get("Param<SpellAbnormalType>"),
            )
            decoded['fieldTypes'] = dict(layout['fields'])
            return decoded
        if layout.get("nativeGate") == "levelscript_on_physical_infliction_native":
            from .on_physical_infliction import decode_on_physical_infliction_header

            audit = _on_physical_infliction_native_audit(game_root=self.game_root) if self.game_root is not None else _on_physical_infliction_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onPhysicalInflictionNative:missing-route")
            decoded, self.offset = decode_on_physical_infliction_header(
                self.data, start, route, game_root=self.game_root, strings=self.strings,
                enum_values=audit.get("enumValues", {}).get("Param<PhysicalInflictionType>"),
            )
            decoded['fieldTypes'] = dict(layout['fields'])
            return decoded
        if layout.get("nativeGate") == "levelscript_on_bb_variable_changed_native":
            from .on_bb_variable_changed import decode_on_bb_variable_changed_header

            audit = _on_bb_variable_changed_native_audit(game_root=self.game_root) if self.game_root is not None else _on_bb_variable_changed_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onBBVariableChangedNative:missing-route")
            decoded, self.offset = decode_on_bb_variable_changed_header(
                self.data, start, route, game_root=self.game_root, strings=self.strings,
            )
            decoded['fieldTypes'] = dict(layout['fields'])
            return decoded
        if layout.get("nativeGate") == "levelscript_on_entity_die_native":
            from .on_entity_die import decode_on_entity_die_header

            audit = _on_entity_die_native_audit(game_root=self.game_root) if self.game_root is not None else _on_entity_die_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onEntityDieNative:missing-route")
            decoded, self.offset = decode_on_entity_die_header(
                self.data, start, route, game_root=self.game_root, strings=self.strings,
            )
            decoded['fieldTypes'] = dict(layout['fields'])
            return decoded
        if layout.get("nativeGate") == "levelscript_on_encounter_intro_part_end_native":
            from .on_encounter_intro_part_end import decode_on_encounter_intro_part_end_header

            audit = _on_encounter_intro_part_end_native_audit(game_root=self.game_root) if self.game_root is not None else _on_encounter_intro_part_end_native_audit()
            route = next(
                (row for row in audit.get("routes", [])
                 if row.get("family") == family and row.get("tag") == tag),
                None,
            )
            if route is None:
                raise ActionMapCodecError("actionMap.onEncounterIntroPartEndNative:missing-route")
            decoded, self.offset = decode_on_encounter_intro_part_end_header(
                self.data, start, route, game_root=self.game_root, strings=self.strings,
            )
            decoded['fieldTypes'] = dict(layout['fields'])
            return decoded
        values = {}; ranges = {}
        for name, kind in layout['fields']:
            at = self.offset
            values[name] = self.node_string(field+'.'+name,layout,name) if kind=='string' else self.value(
                kind,field+'.'+name,parent_layout=layout,member=name)
            ranges[name] = [at,self.offset]
        return {
            "sourceOffset": start, "endOffset": self.offset,
            "unionTag": tag, "memberCount": members,
            "wrapperName": layout["wrapperName"], "fields": values, "fieldRanges": ranges, "fieldTypes": dict(layout["fields"]),
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
        else:
            _require_layout_build()
        if layout is None or members != layout["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-condition-union=0x{tag:04x},"
                f"memberCount={members},offset={start}"
            )
        _require_selected_native('GameCondition', tag, layout, game_root=self.game_root)
        values = {
            name: self.node_string(field+'.'+name,layout,name) if kind=='string' else self.value(kind, field + "." + name)
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
    data: bytes, offset: int, family: str, *, game_root: Path | None = None, strings: Any = None, null_list_params: Any = None, numeric_list_params: Any = None, camera_shake_params: Any = None, buff_ptr_params: Any = None, entity_list_params: Any = None,
    current_owner: Any = None,
) -> tuple[dict[str, Any], int]:
    """Decode one reviewed union at a declared cursor, with a selected-build gate."""
    if game_root is not None:
        inputs = _union_tags().contract_native_inputs()
        native = check_installed_native_inputs(
            inputs["gameAssemblySha256"], inputs["metadataSha256"],
            gameassembly=game_root.parent / "GameAssembly.dll",
            metadata=game_root / "il2cpp_data/Metadata/global-metadata.dat",
        )
        if native.status != "validated":
            raise ActionMapCodecError(
                f"actionMap.installed_native_inputs: expected=validated, "
                f"actual={native.status}, detail={native.detail}"
            )
    _require_layout_build()
    if family not in ("ActionBase", "GetterBase", "ActionHeader"):
        raise ActionMapCodecError(f"actionMap:unsupported-family={family}")
    cursor = _Cursor(data, offset, game_root=game_root, strings=strings, null_list_params=null_list_params, numeric_list_params=numeric_list_params,camera_shake_params=camera_shake_params,buff_ptr_params=buff_ptr_params,entity_list_params=entity_list_params,current_owner=current_owner)
    result = cursor.node(family, f"actionMap.{family}")
    return result, cursor.offset
