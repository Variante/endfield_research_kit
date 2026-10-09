"""Reusable recursive action composition using reviewed typed child joins.

The caller must independently prove its parent map/sequence typed join. Positive
target recursion, selectors with unsupported processors/validators, inherited skill lists,
and unresolved EffectActionCfg terrain-effect arrays still refuse the action.
"""
from __future__ import annotations
import struct
from typing import Any
from scripts.game_data.memorypack import (
    buff_blackboard_double_child_receipt as blackboard,
    buff_create_buff_action_receipt as create,
    buff_create_icon_duration_child_receipt as icon_duration,
    buff_create_input_child_receipt as create_input,
    buff_direction_settings_child_receipt as direction,
    buff_selector_data_child_receipt as selector,
    buff_selector_finder_character_team as character_team,
    buff_target_settings_child_receipt as target,
    buff_effect_action_receipt as effect,
    buff_effect_vector_child_receipt as vector,
    buff_set_super_armor_action_receipt as armor,
    buff_super_armor_blackboard_child_receipt as armor_values,
    buff_finish_buff_advanced_action_receipt as finish,
    buff_find_settings_child_receipt as find,
    buff_direct_target_actions as direct_target_actions,
    buff_selector_finder_owner_spawned as owner_spawned,
    buff_selector_zero_finders as zero_finders,
)

from scripts.game_data.memorypack import buff_selector_shared_children as selector_children
from scripts.game_data.memorypack import buff_recursive_control_actions as control
from scripts.game_data.memorypack import buff_selector_geometry as geometry
from scripts.game_data.memorypack import buff_find_target_action as find_target
from scripts.game_data.memorypack import buff_selector_postprocessors as postprocessors
from scripts.game_data.memorypack import buff_direction_target_children as direction_children
from scripts.game_data.memorypack import buff_damage_action as damage
from scripts.game_data.memorypack import buff_aura_heal_actions as aura_heal
from scripts.game_data.memorypack import buff_skill_stack_interrupt_actions as skill_stack_interrupt
from scripts.game_data.memorypack import buff_vitals_actions as vitals
from scripts.game_data.memorypack import buff_data_transfer_actions as data_transfer
from scripts.game_data.memorypack import buff_probability_action as probability
from scripts.game_data.memorypack import buff_entity_count_action as entity_count
from scripts.game_data.memorypack import buff_notify_char_passive_ui_action as passive_ui
from scripts.game_data.memorypack import buff_cost_action as cost
from scripts.game_data.memorypack import buff_timed_marker_condition as timed_marker
from scripts.game_data.memorypack import buff_super_armor_condition as armor_condition
from scripts.game_data.memorypack import buff_debug_print_action as debug_print
from scripts.game_data.memorypack import animation_curve
from scripts.game_data.memorypack import buff_curve_actions as curve_actions
from scripts.game_data.memorypack import buff_marker_mask_actions as marker_mask_actions
from scripts.game_data.memorypack import buff_sequence
from scripts.game_data.memorypack import buff_tag_sequence_actions as tag_sequence_actions
from scripts.game_data.memorypack import buff_spawn_entity_action as spawn_entity
from scripts.game_data.memorypack import buff_camera_impulse_action as camera_impulse
from scripts.game_data.memorypack import buff_leaf_actions as leaf_actions
from scripts.game_data.memorypack import buff_keyword_actions as keyword_actions
from scripts.game_data.memorypack import buff_launch_projectile_action as launch_projectile
from scripts.game_data.memorypack import buff_ignite_text_action as ignite_text
from scripts.game_data.memorypack.buff_actions import SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack import buff_global_creation_action as global_creation
from scripts.game_data.memorypack import buff_finish_global_action as finish_global
from scripts.game_data.memorypack import buff_blow_off_character_action as blow_off
from scripts.game_data.memorypack import buff_cast_skill_action as cast_skill
from scripts.game_data.memorypack import buff_animator_param_action as animator_param
from scripts.game_data.memorypack import buff_camera_control_state_action as camera_control_state
from scripts.game_data.memorypack import buff_selector_fixed_point_finder as fixed_point
from scripts.game_data.memorypack import buff_switch_action as switch
from scripts.game_data.memorypack import buff_weapon_visual_action as weapon_visual
from scripts.game_data.memorypack import buff_selector_random_point_finder as random_point
from scripts.game_data.memorypack import buff_recover_poise_action as recover_poise
from scripts.game_data.memorypack import buff_spell_infliction_action as spell_infliction
from scripts.game_data.memorypack import buff_custom_ability_event_condition as custom_event
from scripts.game_data.memorypack import buff_animation_sequence_actions as animation_sequences
from scripts.game_data.memorypack import buff_check_distance_condition as check_distance
from scripts.game_data.memorypack import buff_selector_shape_finder as shape_finder
from scripts.game_data.memorypack import buff_collider_shape as collider_shape
from scripts.game_data.memorypack import buff_pick_target_action as pick_target
from scripts.game_data.memorypack import buff_effect_line_center_action as effect_line_center
from scripts.game_data.memorypack import buff_tick_interval_action as tick_interval

LABEL = "buffRecursiveActions"
SUPPORTED_TAGS = frozenset((create.TAG, effect.TAG, armor.TAG, finish.TAG, damage.TAG)) | direct_target_actions.supported_tags() | control.SUPPORTED_TAGS | find_target.supported_tags() | aura_heal.supported_tags() | skill_stack_interrupt.supported_tags() | vitals.supported_tags() | data_transfer.supported_tags() | probability.supported_tags() | entity_count.supported_tags() | passive_ui.supported_tags() | cost.supported_tags() | timed_marker.supported_tags() | armor_condition.supported_tags() | debug_print.supported_tags() | curve_actions.supported_tags() | marker_mask_actions.supported_tags() | tag_sequence_actions.supported_tags() | spawn_entity.supported_tags() | camera_impulse.supported_tags() | leaf_actions.supported_tags() | keyword_actions.supported_tags() | launch_projectile.supported_tags() | ignite_text.supported_tags() | global_creation.supported_tags() | switch.supported_tags() | weapon_visual.supported_tags()

SUPPORTED_TAGS |= recover_poise.supported_tags()
SUPPORTED_TAGS |= spell_infliction.supported_tags()
SUPPORTED_TAGS |= custom_event.supported_tags()
SUPPORTED_TAGS |= animation_sequences.supported_tags()
SUPPORTED_TAGS |= check_distance.supported_tags()
SUPPORTED_TAGS |= pick_target.supported_tags()
SUPPORTED_TAGS |= effect_line_center.supported_tags()
SUPPORTED_TAGS |= finish_global.supported_tags()
SUPPORTED_TAGS |= blow_off.supported_tags()
SUPPORTED_TAGS |= cast_skill.supported_tags()
SUPPORTED_TAGS |= animator_param.supported_tags()
SUPPORTED_TAGS |= camera_control_state.supported_tags()
SUPPORTED_TAGS |= tick_interval.supported_tags()

def validate_current_native_contract() -> dict[str, Any]:
    children = {"create": create.validate_current_native_contract(),
                "iconDuration": icon_duration.validate_current_native_contract(),
                "createInput": create_input.validate_current_native_contract(),
                "blackboard": blackboard.validate_current_native_contract(),
                "target": target.validate_current_native_contract(),
                "effect": effect.validate_current_native_contract(),
                "effectVectors": vector.validate_current_native_contract()}
    children["direction"] = direction.validate_current_native_contract(target_native=children["target"])
    children["selector"] = selector.validate_current_native_contract(target_native=children["target"])
    children["zeroFinders"] = zero_finders.validate_current_native_contract(selector_native=children["selector"])
    children["characterTeamFinder"] = character_team.validate_current_native_contract(selector_native=children["selector"])
    children["finish"] = children["target"]["parentNative"][finish.TAG]
    children["findSettings"] = find.validate_current_native_contract()
    children["armorValues"] = armor_values.validate_current_native_contract()
    children["armor"] = children["armorValues"]["parentNative"]
    children["directTargetActions"] = direct_target_actions.validate_current_native_contract()
    children["ownerSpawnedFinder"] = owner_spawned.validate_current_native_contract(selector_native=children["selector"])
    children["zeroValidators"] = selector_children.zero_owner.validate_current_native_contract(selector_native=children["selector"])
    children["tagQueryValidator"] = selector_children.tag_owner.validate_current_native_contract(selector_native=children["selector"])
    selector_children.query_parent_binding(children["tagQueryValidator"], children["findSettings"])
    children["ifElse"] = control.conditional.validate_current_native_contract()
    children["compare"] = control.compare.validate_current_native_contract()
    children["modify"] = children["blackboard"]["parentNative"][control.modify.TAG]
    children["checkStack"] = control.stack.validate_current_native_contract()
    children["buffIdActions"] = control.ids.validate_current_native_contract()
    children["blackboardString"] = control.strings.child.validate_current_native_contract()
    children["decorateMask"] = control.decorate.validate_current_native_contract()
    children["advancedBuffIds"] = control.advanced_ids.validate_current_native_contract(
        string_native=children["blackboardString"])
    children["selectorGeometry"] = geometry.validate_current_native_contract(
        selector_native=children["selector"], vector_native=children["effectVectors"])
    children["randomPointFinder"] = random_point.validate_current_native_contract(
        selector_native=children["selector"], vector_native=children["effectVectors"])
    children["colliderShape"] = collider_shape.validate_current_native_contract()
    children["shapeFinder"] = shape_finder.validate_current_native_contract(
        selector_native=children["selector"], collider_native=children["colliderShape"])
    children["fixedPointFinder"] = fixed_point.validate_current_native_contract(
        selector_native=children["selector"], vector_native=children["effectVectors"])
    children["selectorPostprocessors"] = postprocessors.validate_current_native_contract(children=children)
    children["directionTargets"] = direction_children.validate_current_native_contract(children=children)
    children["checkDistance"] = check_distance.validate_current_native_contract(children=children)
    children["distanceValidator"] = selector_children.distance_owner.validate_current_native_contract(children=children)
    children["damage"] = damage.validate_current_native_contract(
        vector_native=children["effectVectors"], target_native=children["target"])
    children["recoverPoise"] = recover_poise.validate_current_native_contract(children=children)
    children["spellInfliction"] = spell_infliction.validate_current_native_contract(children=children)
    children["customAbilityEvent"] = custom_event.validate_current_native_contract(children=children)
    children["auraHeal"] = aura_heal.validate_current_native_contract(children=children)
    children["skillStackInterrupt"] = skill_stack_interrupt.validate_current_native_contract(children=children)
    children["vitals"] = vitals.parent.validate_current_native_contract()
    children["dataTransfer"] = data_transfer.validate_current_native_contract(children=children)
    children["probability"] = probability.validate_current_native_contract(children=children)
    children["entityCount"] = entity_count.validate_current_native_contract(children=children)
    children["passiveUi"] = passive_ui.validate_current_native_contract(children=children)
    children["cost"] = cost.validate_current_native_contract(children=children)
    children["timedMarker"] = timed_marker.validate_current_native_contract(children=children)
    children["superArmorCondition"] = armor_condition.validate_current_native_contract(children=children)
    children["debugPrint"] = debug_print.validate_current_native_contract(children=children)
    children["animationCurve"] = animation_curve.validate_current_native_contract()
    children["cameraControlState"] = camera_control_state.validate_current_native_contract(children=children)
    children["curveActions"] = curve_actions.validate_current_native_contract(children=children)
    children["markerMaskActions"] = marker_mask_actions.validate_current_native_contract(children=children)
    children["sequence"] = buff_sequence.validate_current_native_contract()
    children["animationSequenceActions"] = animation_sequences.validate_current_native_contract(children=children)
    children["tagSequenceActions"] = tag_sequence_actions.validate_current_native_contract(children=children)
    children["spawnEntity"] = spawn_entity.validate_current_native_contract(children=children)
    children["cameraImpulse"] = camera_impulse.validate_current_native_contract(children=children)
    children["leafActions"] = leaf_actions.validate_current_native_contract()
    children["keywordActions"] = keyword_actions.validate_current_native_contract(children=children)
    children["launchProjectile"] = launch_projectile.validate_current_native_contract(children=children)
    children["igniteText"] = ignite_text.validate_current_native_contract(children=children)
    children["globalCreation"] = global_creation.validate_current_native_contract(children=children)
    children["finishGlobal"] = finish_global.validate_current_native_contract(children=children)
    children["blowOff"] = blow_off.validate_current_native_contract(children=children)
    children["castSkill"] = cast_skill.validate_current_native_contract(children=children)
    children["animatorParamAction"] = animator_param.validate_current_native_contract()
    children["switch"] = switch.validate_current_native_contract(children=children)
    children["weaponVisual"] = weapon_visual.validate_current_native_contract()
    children["pickTarget"] = pick_target.validate_current_native_contract(children=children)
    children["effectLineCenter"] = effect_line_center.validate_current_native_contract(children=children)
    children["tickInterval"] = tick_interval.composition.validate_current_native_contract()
    children["tickIntervalUnionRoute"] = tick_interval.unions.validate_current_native_contract()
    armor_target_binding(children["armor"], children["target"])
    finish_settings_binding(children["finish"], children["findSettings"])
    expected = children["create"]["nativeInputs"]
    for name, child in children.items():
        if (child.get("status") != "validated"
                or any(child.get("nativeInputs", {}).get(key) != expected.get(key)
                       for key in ("GameAssembly.dll", "global-metadata.dat"))):
            raise ValueError(f"{LABEL}.native:{name}-unvalidated-or-build-drift")
    return {"status": "validated", "nativeInputs": expected, "children": children}

def decode_create_action(
    data: bytes, source: str, digest: str, start: int, end: int,
    native: dict[str, Any],
) -> dict[str, Any]:
    children = native["children"]
    parent = create.decode_create_buff_action_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        native_validation=children["create"],
    )
    if (parent.get("wholeActionByteSpanExact") is not True
            or [field["fieldName"] for field in parent["namedFields"]]
            != ["isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
                "asChildBuff", "autoFinishByAction", "buffIconDurationSource",
                "buffs", "buffSource", "contextKey", "count",
                "finishWithNextSkillIfNotInherited", "inheritSkillIdList",
                "inheritSourceSkillCastId", "inheritSourceSkillCastInfo", "isExtra",
                "overrideBuffIconDuration", "passTargetGroupsToBuff", "targetSettings"]):
        raise ValueError(f"{LABEL}.action:parent-field-order")
    fields = {field["fieldName"]: field for field in parent["namedFields"]}
    icon_field = fields["buffIconDurationSource"]
    icon = icon_duration.decode_icon_duration_child(
        data, source=source, logical_sha256=digest,
        start=icon_field["start"], end=icon_field["end"],
        native_validation=children["iconDuration"],
    )
    input_field = fields["buffs"]
    inputs = create_input.decode_create_buff_input_list(
        data, source=source, logical_sha256=digest,
        start=input_field["start"], end=input_field["end"],
        native_validation=children["createInput"],
    )
    if (inputs.get("wholeStoredSpanExact") is not True
            or inputs.get("namedDirectMembersExact") is not True
            or inputs.get("start") != input_field["start"]
            or inputs.get("end") != input_field["end"]
            or len(inputs.get("inputs") or []) != max(0, inputs["count"])
            or any(item.get("status") not in ("named-five-member-exact-span", "exact-null-wrapper")
                   for item in inputs.get("inputs") or [])):
        raise ValueError(f"{LABEL}.action:input-list-not-exact")
    if (fields["inheritSkillIdList"]["end"] - fields["inheritSkillIdList"]["start"] != 4
            or struct.unpack_from("<i", data, fields["inheritSkillIdList"]["start"])[0] != 0):
        raise ValueError(f"{LABEL}.action:inherit-list-not-empty")
    blackboard_child = blackboard.decode_blackboard_double_action_child_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        tag=create.TAG, native_validation=children["blackboard"],
    )
    target_child = target.decode_target_settings_action_child_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        tag=create.TAG, native_validation=children["target"],
    )
    direction_child = direction.decode_direction_settings_action_child_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        tag=create.TAG, native_validation=children["direction"],
    )
    selector_child = selector.decode_selector_data_action_child_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        tag=create.TAG, native_validation=children["selector"],
    )
    if (blackboard_child.get("parentField") != "count"
            or blackboard_child.get("wholeProviderByteSpanExact") is not True
            or len(target_child.get("targetChildren") or []) != 1
            or len(direction_child.get("directionChildren") or []) != 1
            or len(selector_child.get("selectorChildren") or []) != 1):
        raise ValueError(f"{LABEL}.action:shared-child-cardinality")
    target_row = target_child["targetChildren"][0]
    direction_row = direction_child["directionChildren"][0]
    selector_row = selector_child["selectorChildren"][0]
    if (target_row.get("start") != fields["targetSettings"]["start"]
            or target_row.get("end") != fields["targetSettings"]["end"]
            or target_row.get("status") != "named-direct-members-exact-span"
            or direction_row.get("status") != "named-direct-members-exact-span"
            or selector_row.get("status") != "named-direct-members-exact-span"):
        raise ValueError(f"{LABEL}.action:target-child-span")
    target_members = {member["fieldName"]: member
                      for member in target_row["namedMembers"]}
    if (len(target_members) != 13
            or [direction_row["start"], direction_row["end"]]
            != [target_members["advancedDirection"]["start"],
                target_members["advancedDirection"]["end"]]
            or [selector_row["start"], selector_row["end"]]
            != [target_members["selectorData"]["start"],
                target_members["selectorData"]["end"]]
):
        raise ValueError(f"{LABEL}.action:direction-or-selector-join")
    recursive = recursive_target(data,source,digest,fields['targetSettings'],children)
    return {"parent": parent, "iconDuration": icon, "inputList": inputs,
            "blackboard": blackboard_child, "target": target_child,
            "direction": direction_child, "selector": selector_child,
            "finder": recursive['finder'], "validators": recursive['validators'],
            "postprocessors": recursive['postprocessors'], "recursiveTarget": recursive,
            "recursiveStoredSchemaExact": True}


def decode_effect_action(data: bytes, source: str, digest: str, start: int, end: int,
                         native: dict[str, Any]) -> dict[str, Any]:
    """Compose every reached EffectActionCfg and target child on exact joins."""
    children = native["children"]
    kw = dict(source=source, logical_sha256=digest, start=start, end=end)
    parent = effect.decode_effect_action_receipt(data, **kw, native_validation=children["effect"])
    if parent.get("wholeActionByteSpanExact") is not True:
        raise ValueError(f"{LABEL}.effect:parent-incomplete")
    fields = {row["fieldName"]: row for row in parent["namedFields"]}
    expected_targets = {name for name, row in fields.items() if row["kind"] == "target-profile"}
    vectors = vector.decode_effect_vector_child_receipt(
        data, **kw, native_validation=children["effectVectors"], action_native=children["effect"])
    targets = target.decode_target_settings_action_child_receipt(
        data, **kw, tag=effect.TAG, native_validation=children["target"])
    directions = direction.decode_direction_settings_action_child_receipt(
        data, **kw, tag=effect.TAG, native_validation=children["direction"])
    selectors = selector.decode_selector_data_action_child_receipt(
        data, **kw, tag=effect.TAG, native_validation=children["selector"])
    if (vectors.get("wholeConfigBlackboardChildrenExact") is not True
            or {row.get("parentField") for row in targets.get("targetChildren") or []} != expected_targets
            or len(targets.get("targetChildren") or []) != len(expected_targets)
            or len(directions.get("directionChildren") or []) != len(expected_targets)
            or len(selectors.get("selectorChildren") or []) != len(expected_targets)):
        raise ValueError(f"{LABEL}.effect:child-cardinality")
    finders = []
    validator_receipts = []
    recursive_targets = []
    for target_row in targets["targetChildren"]:
        parent_field = fields.get(target_row.get("parentField")) or {}
        if (target_row.get("status") != "named-direct-members-exact-span"
                or [target_row["start"], target_row["end"]]
                != [parent_field.get("start"), parent_field.get("end")]):
            raise ValueError(f"{LABEL}.effect:target-parent-join")
        members = {row["fieldName"]: row for row in target_row["namedMembers"]}
        ds = [row for row in directions["directionChildren"]
              if row.get("targetParentField") == target_row["parentField"]]
        ss = [row for row in selectors["selectorChildren"]
              if row.get("targetParentField") == target_row["parentField"]]
        if len(members) != 13 or len(ds) != 1 or len(ss) != 1:
            raise ValueError(f"{LABEL}.effect:target-child-join-cardinality")
        direction_row, selector_row = ds[0], ss[0]
        if (direction_row.get("status") != "named-direct-members-exact-span"
                or selector_row.get("status") != "named-direct-members-exact-span"
                or [direction_row["start"], direction_row["end"]]
                != [members["advancedDirection"]["start"], members["advancedDirection"]["end"]]
                or [selector_row["start"], selector_row["end"]]
                != [members["selectorData"]["start"], members["selectorData"]["end"]]
):
            raise ValueError(f"{LABEL}.effect:direction-or-selector-join")
        recursive=recursive_target(data,source,digest,parent_field,children)
        recursive_targets.append(recursive)
        if recursive['finder'] is not None:finders.append(recursive['finder'])
        if recursive['validators'] is not None:validator_receipts.append(recursive['validators'])
    return {"parent": parent, "configVectors": vectors, "target": targets,
            "direction": directions, "selector": selectors, "finders": finders, "recursiveTargets": recursive_targets,
            "recursiveStoredSchemaExact": True, **({'validators':validator_receipts} if validator_receipts else {})}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int,
                  tag: int, native_validation: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    if depth > SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f"{LABEL}.action:depth-limit")
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if tag in tick_interval.supported_tags():
        return tick_interval.decode_recursive_action(data, source=source, digest=digest, start=start, end=end,
            tag=tag, native_validation=native_validation, depth=depth)
    if tag in pick_target.supported_tags():
        return pick_target.decode_action(data, source=source, digest=digest, start=start, end=end,
            tag=tag, native_validation=native_validation, target_decoder=recursive_target, depth=depth)
    if tag in effect_line_center.supported_tags():
        return effect_line_center.decode_action(data, source=source, digest=digest, start=start, end=end,
            tag=tag, native_validation=native_validation, target_decoder=recursive_target, depth=depth)
    decoders = {create.TAG: decode_create_action, effect.TAG: decode_effect_action,
                armor.TAG: decode_armor_action, finish.TAG: decode_finish_action}
    if tag in weapon_visual.supported_tags():
        return weapon_visual.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation)
    if tag in recover_poise.supported_tags():
        return recover_poise.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in spell_infliction.supported_tags():
        return spell_infliction.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in animation_sequences.supported_tags():
        return animation_sequences.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, depth=depth)
    if tag in custom_event.supported_tags():
        return custom_event.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation)
    if tag in check_distance.supported_tags():
        return check_distance.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in global_creation.supported_tags():
        return global_creation.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in finish_global.supported_tags():
        return finish_global.decode_action(data, source=source, digest=digest, start=start, end=end,
            tag=tag, native_validation=native_validation)
    if tag in blow_off.supported_tags():
        return blow_off.decode_action(data, source=source, digest=digest, start=start, end=end,
            tag=tag, native_validation=native_validation, target_decoder=recursive_target)
    if tag in cast_skill.supported_tags():
        return cast_skill.decode_action(data, source=source, digest=digest, start=start, end=end,
            tag=tag, native_validation=native_validation, target_decoder=recursive_target)
    if tag in animator_param.supported_tags():
        return animator_param.decode_action(data, source=source, digest=digest, start=start, end=end,
            tag=tag, native_validation=native_validation)
    if tag in camera_control_state.supported_tags():
        return camera_control_state.decode_action(data, source=source, digest=digest, start=start, end=end,
            tag=tag, native_validation=native_validation)
    if tag in switch.supported_tags():
        return switch.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, depth=depth)
    if tag in direct_target_actions.supported_tags():
        return decode_direct_target_action(data, source, digest, start, end, tag, native_validation)
    if tag in find_target.supported_tags():
        return find_target.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag, native_validation=native_validation,target_decoder=recursive_target)
    if tag == damage.TAG:
        return damage.decode_action(data, source=source, digest=digest, start=start, end=end,
                                    native_validation=native_validation, target_decoder=recursive_target)
    if tag in aura_heal.supported_tags():
        return aura_heal.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target, depth=depth)
    if tag in skill_stack_interrupt.supported_tags():
        return skill_stack_interrupt.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in vitals.supported_tags():
        return vitals.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in data_transfer.supported_tags():
        return data_transfer.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in probability.supported_tags():
        return probability.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in cost.supported_tags():
        return cost.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in timed_marker.supported_tags():
        return timed_marker.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in armor_condition.supported_tags():
        return armor_condition.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in debug_print.supported_tags():
        return debug_print.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in curve_actions.supported_tags():
        return curve_actions.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in marker_mask_actions.supported_tags():
        return marker_mask_actions.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in tag_sequence_actions.supported_tags():
        return tag_sequence_actions.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target, depth=depth)
    if tag in spawn_entity.supported_tags():
        return spawn_entity.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in camera_impulse.supported_tags():
        return camera_impulse.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in leaf_actions.supported_tags():
        return leaf_actions.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation)
    if tag in ignite_text.supported_tags():
        return ignite_text.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
                                         native_validation=native_validation, target_decoder=recursive_target)
    if tag in launch_projectile.supported_tags():
        return launch_projectile.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
                                               native_validation=native_validation, target_decoder=recursive_target)
    if tag in keyword_actions.supported_tags():
        return keyword_actions.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag in passive_ui.supported_tags():
        return passive_ui.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
                                       native_validation=native_validation, target_decoder=recursive_target)
    if tag in entity_count.supported_tags():
        return entity_count.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag,
            native_validation=native_validation, target_decoder=recursive_target)
    if tag not in decoders:
        return control.decode_action(data, source=source, digest=digest, start=start, end=end,
                                     tag=tag, native_validation=native_validation, depth=depth)
    result = decoders[tag](data, source, digest, start, end, native_validation)
    return {"schema": "endfield.buff-recursive-action-receipt.v1", "tag": tag,
            "start": start, "end": end, **result}



def armor_target_binding(parent_native, target_native):
    """Join the already validated last source context to the named parent slot.

    armor.validate_current_native_contract independently compares the generated
    member declared types against [priority, impact, armor, target] contexts.
    This caller additionally binds the last source read to the child reader.
    No new destination or provider identity is inferred from a byte fit.
    """
    source, catalog = armor._contracts()
    contexts = source['nestedContexts']
    names, kinds = parent_native.get('memberNames', []), parent_native.get('readKinds', [])
    expected_inputs = catalog['nativeInputs']
    if (parent_native.get('status') != 'validated' or target_native.get('status') != 'validated'
            or parent_native.get('unionTag') != armor.TAG or len(names) != 7
            or kinds != source['anonymousReadOrder']['member7']
            or kinds[-1] != 'target-profile' or names[-1] != 'targetSettings'
            or contexts[-1]['typeName'] != 'Beyond.Gameplay.Core.TargetSettings'
            or [c['typeName'] for c in contexts[1:3]]
                != ['Beyond.Gameplay.Core.BlackboardImpactValue', 'Beyond.Gameplay.Core.BlackboardSuperArmorValue']
            or any(parent_native.get('nativeInputs', {}).get(k) != target_native.get('nativeInputs', {}).get(k)
                   for k in ('GameAssembly.dll', 'global-metadata.dat'))
            or parent_native['nativeInputs']['GameAssembly.dll'] != expected_inputs['gameAssemblySha256']
            or parent_native['nativeInputs']['global-metadata.dat'] != expected_inputs['metadataSha256']):
        raise ValueError('buffRecursiveActions.armor:typed-parent-target-join')
    return {'fieldName': names[-1], 'kind': kinds[-1], 'parentFieldIndex': 6,
            'declaredType': contexts[-1]['typeName'], 'sourceContext': contexts[-1]}


def finish_settings_binding(parent_native, child_native):
    """Bind the reviewed B4 source contexts to all generated object setters."""
    contract = finish._contract(); source, _catalog = finish._dependencies()
    setters = contract['wrapper']['inheritedSetterMethods'] + contract['wrapper']['setterMethods']
    kinds = contract['orderedReadKinds']
    nested = [(index, setter, kind) for index, (setter, kind) in enumerate(zip(setters, kinds, strict=True))
              if kind in ('target-profile', 'finder-profile', 'scalar-payload')]
    contexts = source['nestedContexts'][:len(nested)]
    if (parent_native.get('status') != 'validated' or child_native.get('status') != 'validated'
            or parent_native.get('nativeInputs') != contract['nativeInputs']
            or child_native.get('nativeInputs') != contract['nativeInputs']
            or parent_native.get('unionTag') != finish.TAG
            or parent_native.get('memberCount') != len(setters)
            or len(contexts) != len(nested)
            or [row[1][-1] for row in nested] != [row['typeName'] for row in contexts]):
        raise ValueError('buffRecursiveActions.finish:typed-parent-context-join')
    joined = [(index, setter, kind, context) for (index, setter, kind), context in zip(nested, contexts)
              if setter[1] == 'set___buffSettings__']
    if (len(joined) != 1 or joined[0][2] != 'finder-profile'
            or joined[0][1][-1] != 'Beyond.Gameplay.Core.BuffFindSettings'):
        raise ValueError('buffRecursiveActions.finish:typed-parent-settings-join')
    index, _setter, kind, context = joined[0]
    return {'fieldName': 'buffSettings', 'parentFieldIndex': index, 'kind': kind,
            'declaredType': context['typeName'], 'sourceContext': context}


def target_value(data, source, digest, field, native):
    """Use the factored existing loop; the caller still owns its typed join."""
    value = target.decode_target_settings_value(data, source=source, logical_sha256=digest,
        start=field['start'], end=field['end'], native_validation=native)
    if value['status'] != 'named-direct-members-exact-span':
        raise ValueError('buffRecursiveActions.target:null-target-not-admitted')
    return value


def recursive_target(data, source, digest, field, context, *, depth=0):
    if type(depth)is not int or not 0<=depth<=direction_children.DEPTH_LIMIT:
        raise ValueError('buffRecursiveActions.target:depth-limit')
    target_row = target_value(data, source, digest, field, context['target'])
    fields = {m['fieldName']: m for m in target_row['namedMembers']}
    d,s = fields['advancedDirection'],fields['selectorData']
    if not all(field['start']<m['start']<m['end']<=field['end'] for m in (d,s)):
        raise ValueError('buffRecursiveActions.target:strict-child-span')
    direction_row=direction_children.decode_direction(data,source=source,digest=digest,
        start=d['start'],end=d['end'],children=context,target_decoder=recursive_target,depth=depth)
    selected=find_target.decode_selector(data,source,digest,s['start'],s['end'],context,target_decoder=recursive_target,depth=depth)
    return {**target_row,'advancedDirection':direction_row,'selectorData':selected['selector'],
        'finder':selected['finder'],'validators':selected['validators'],'postprocessors':selected['postprocessors'],
        'recursiveStoredSchemaExact':True}


def decode_armor_action(data, source, digest, start, end, native):
    context = native["children"]
    binding = armor_target_binding(context['armor'], context['target'])
    args = dict(source=source, logical_sha256=digest, start=start, end=end)
    parent = armor.decode_set_super_armor_action_receipt(data, **args, native_validation=context['armor'])
    values = armor_values.decode_super_armor_blackboard_children(data, **args,
                                                               native_validation=context['armorValues'])
    field = parent['namedFields'][binding['parentFieldIndex']]
    if (field['fieldName'] != binding['fieldName'] or field['kind'] != binding['kind']
            or len(values['children']) != 2):
        raise ValueError('buffRecursiveActions.armor:children')
    for child, index in zip(values['children'], (4, 5)):
        expected = parent['namedFields'][index]
        if (child['parentFieldName'] != expected['fieldName']
                or child['parentFieldRange'] != [expected['start'], expected['end']]
                or child.get('wholeProviderByteSpanExact') is not True):
            raise ValueError('buffRecursiveActions.armor:blackboard-parent-join')
    target = recursive_target(data, source, digest, field, context)
    return {'schema': 'endfield.buff-recursive-action-receipt.v1', 'tag': armor.TAG,
            'start': start, 'end': end, 'parent': parent, 'blackboardValues': values,
            'target': target, 'recursiveStoredSchemaExact': True}


def decode_finish_action(data, source, digest, start, end, native):
    context = native["children"]
    settings_binding = finish_settings_binding(context['finish'], context['findSettings'])
    args = dict(source=source, logical_sha256=digest, start=start, end=end)
    parent = finish.decode_finish_buff_advanced_action_receipt(data, **args, native_validation=context['finish'])
    scalar = blackboard.decode_blackboard_double_action_child_receipt(data, **args,
        tag=finish.TAG, native_validation=context['blackboard'])
    fields = {m['fieldName']: m for m in parent['namedFields']}
    setters = finish._contract()['wrapper']['setterMethods']
    target_names = [m[1].removeprefix('set___').removesuffix('__') for m in setters
                    if m[-1] == 'Beyond.Gameplay.Core.TargetSettings']
    if set(target_names) != {m['fieldName'] for m in parent['namedFields'] if m['kind'] == 'target-profile'}:
        raise ValueError('buffRecursiveActions.finish:target-parent-join')
    targets = {name: recursive_target(data, source, digest, fields[name], context) for name in target_names}
    settings_field = parent['namedFields'][settings_binding['parentFieldIndex']]
    if (settings_field['fieldName'] != settings_binding['fieldName']
            or settings_field['kind'] != settings_binding['kind']):
        raise ValueError('buffRecursiveActions.finish:settings-parent-field')
    settings = find.decode_find_settings_child_receipt(data, source=source, logical_sha256=digest,
        start=settings_field['start'], end=settings_field['end'], native_validation=context['findSettings'])
    if (settings.get('wholeChildSpanExact') is not True or scalar.get('wholeProviderByteSpanExact') is not True
            or scalar['parentFieldRange'] != [fields['finishLayerCnt']['start'], fields['finishLayerCnt']['end']]):
        raise ValueError('buffRecursiveActions.finish:settings-or-scalar-parent-join')
    return {'schema': 'endfield.buff-recursive-action-receipt.v1', 'tag': finish.TAG,
            'start': start, 'end': end, 'parent': parent, 'blackboard': scalar,
            'targets': targets, 'buffSettings': settings, 'recursiveStoredSchemaExact': True}



def decode_direct_target_action(data, source, digest, start, end, tag, native_validation):
    context = native_validation["children"]
    native = context['directTargetActions']['routes'][tag]
    if (context['target'].get('status') != 'validated'
            or any(native['nativeInputs'][key] != context['target']['nativeInputs'][key]
           for key in ('GameAssembly.dll', 'global-metadata.dat'))):
        raise ValueError('buffRecursiveActions.directTarget:native-input-join')
    parent = direct_target_actions.decode_action(data, source=source, logical_sha256=digest,
        start=start, end=end, tag=tag, native_validation=native)
    if parent.get('isNull'):
        return {'schema':'endfield.buff-recursive-action-receipt.v1', 'tag':tag,
            'start':start, 'end':end, 'parent':parent, 'recursiveStoredSchemaExact':True}
    binding = native['targetBinding']; field = parent['namedFields'][binding['index']]
    if field['fieldName'] != binding['fieldName'] or field['kind'] != binding['kind']:
        raise ValueError('buffRecursiveActions.directTarget:target-parent-join')
    child = ({**field, 'status':'exact-null', 'recursiveStoredSchemaExact':True}
        if native.get('sourceRecord') and data[field['start']:field['end']] == b'\xff'
        else recursive_target(data, source, digest, field, context))
    if (child.get('recursiveStoredSchemaExact') is not True
            or [child.get('start'),child.get('end')] != [field['start'],field['end']]):
        raise ValueError('buffRecursiveActions.directTarget:target-child-span')
    return {'schema': 'endfield.buff-recursive-action-receipt.v1', 'tag': tag,
            'start': start, 'end': end, 'parent': parent, 'target': child, 'recursiveStoredSchemaExact': True}
