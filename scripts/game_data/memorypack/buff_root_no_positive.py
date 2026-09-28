"""Forward, selected-build BuffData reader for bounded recursive-list branches.

Every accepted record starts at the root header and ends at physical EOF. The
native contract authenticates root source order; child validators authenticate
the nested records decoded here. The positive damage branch requires separately
checked condition and processor children. Other positive recursive collections
remain refused.

This is the only route that makes a whole BuffData root a named schema. It
admits a unique outer-frame cohort (``is_no_positive_candidate``,
``is_positive_damage_candidate``) whose child layouts are independently
validated (``CHILD_VALIDATORS``): the null/empty recursive-list branch, a
positive ``blackboard`` DataPair list (``buff_datapair_native``) plus
``globalModifier`` list, and one positive ``damageModifier`` whose sole
nested blocker is that list. The damage branch composes the
``buff_damage_modifier_receipt`` item partition with the selected condition
receipts (``buff_damage_*_condition_receipt``) and processor receipts
(``buff_damage_*_processor_*receipt``); a condition or processor without its
own receipt refuses the file. The narrow sole-CreateBuffAction branch lives
in ``buff_create_action_root_receipt``.

Each admitted file is reread from byte zero through 30 contiguous named
fields on the original logical bytes, checks the stored ``id`` against its
source stem and ends at physical EOF. The caller authenticates the stream
against the VFS ledger length and MD5 and records its logical SHA;
``scripts.game_data.jsondata_corpus`` revalidates the native inputs and
replays the exported bytes against the entire receipt before classifying a
row as schema decoded.

Refused: nonzero condition actions or processors without a selected receipt,
positive heal and other action lists, ``stackEffects`` and timeline
interiors -- each keeps its own named-ownership blocker. Evidence tier:
``exact`` stored layout for the selected rows; live formatter-provider
choice and gameplay behavior stay open.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import PurePosixPath
from typing import Any

from scripts.game_data.memorypack import (
    buff_adding_cooldown,
    buff_damage_check_decorate_mask_condition_receipt,
    buff_damage_check_type_condition_receipt,
    buff_damage_check_type_mask_condition_receipt,
    buff_damage_check_tag_match_condition_receipt,
    buff_damage_check_main_character_condition_receipt,
    buff_damage_check_buff_stack_condition_receipt,
    buff_damage_check_vitals_condition_receipt,
    buff_damage_origin_or_condition_receipt,
    buff_damage_known_compound_condition_receipt,
    buff_damage_if_else_condition_receipt,
    buff_damage_not_next_main_condition_receipt,
    buff_damage_two_direction_angle_condition_receipt,
    buff_damage_modifier_receipt,
    buff_damage_modify_calc_result_processor_child_receipt,
    buff_damage_instant_modify_attribute_processor_receipt,
    buff_damage_scalar_processor_child_receipt,
    buff_damage_scale_processor_child_receipt,
    buff_damage_sequence_action_condition_receipt,
    buff_damage_text_processor_child_receipt,
    buff_damage_two_action_condition_receipt,
    buff_datapair_native,
    buff_dispel_config,
    buff_global_modifier_receipt,
    buff_icon_config,
    buff_stacking_compact_native,
    buff_timeline_empty_native,
)
from scripts.game_data.memorypack.buff import (
    read_buff_blackboard_float_raw_field_bounded,
    read_buff_blackboard_int_field,
    read_buff_bool_field,
    read_buff_memorypack_utf8_string_strict_bounded,
)
from scripts.game_data.memorypack.buff_actions import event_prefix, root_continuation
from scripts.game_data.memorypack.buff_residual_actions import _ResidualReader
from scripts.game_data.memorypack.buff_root_no_positive_native import (
    _contract as _native_contract,
    validate_current_native_contract as validate_root_native,
)


CHILD_VALIDATORS = {
    "addingCooldown": buff_adding_cooldown.validate_current_native_contract,
    "dispelConfig": buff_dispel_config.validate_current_native_contract,
    "iconConfig": buff_icon_config.validate_current_native_contract,
    "stackingSettings": buff_stacking_compact_native.validate_current_native_contract,
    "timelineActions": buff_timeline_empty_native.validate_current_native_contract,
    "blackboardDataPairs": buff_datapair_native.validate_current_native_contract,
    "globalModifier": buff_global_modifier_receipt.validate_current_native_contract,
}


def is_no_positive_candidate(framed: dict[str, Any], *, length: int) -> bool:
    """Select only the legacy first-stop cohort the forward reader can prove."""
    if (framed.get("coverageStatus") != "unique"
            or framed.get("candidateCount") != 1
            or framed.get("eventPrefixStatus") != "success"
            or framed.get("rootContinuationStatus") != "success"
            or framed.get("namedOuterFrameStatus") not in ("named_exact_frame", "named_exact_full")):
        return False
    candidates = framed.get("candidates") or []
    if len(candidates) != 1:
        return False
    candidate = candidates[0]
    legacy = candidate.get("namedSchemaReceipt") or {}
    fields = legacy.get("forwardNamedFields") or []
    if (legacy.get("physicalEof") != length
            or legacy.get("actionUnionCount") != 0
            or legacy.get("hasConservativeSuffixFrontier") is not False
            or legacy.get("composedOpaqueBytes") != 0
            or not _allowed_blockers(legacy.get("blockers"))
            or len(fields) != 15
            or [field.get("index") for field in fields] != list(range(15))):
        return False
    lengths = {0: 4, 3: 6, 5: 4, 6: 4, 13: 4}
    if any(fields[index].get("end", -1) - fields[index].get("start", 0) != size
           for index, size in lengths.items()):
        return False
    suffix = candidate.get("currentNamedSuffix") or {}
    stacking = suffix.get("stackingSettingsNativeChild") or {}
    timeline = suffix.get("timelineEmptyNativeChild") or {}
    blackboard = fields[4]
    global_modifier = fields[10]
    return (
        (candidate.get("currentNamedMiddle") or {}).get("iconConfigStatus") == "exact"
        and suffix.get("status") == "named-exact-to-eof"
        and suffix.get("endOffset") == length
        and stacking.get("status") == "exact-child-cursor"
        and stacking.get("stackEffectsCount") == 0
        and timeline.get("status") == "exact-null-or-empty-list-to-eof"
        and timeline.get("count") in (-1, 0)
        and _field4_exact(blackboard)
        and _field10_exact(global_modifier)
        # The reviewed promotion is the nine-row globalModifier cohort. A
        # positive blackboard list alone remains a partial root frontier.
        and ((blackboard.get("nestedProfile") or {}).get("count", 0) <= 0
             or global_modifier.get("count") == 1)
    )


def is_positive_damage_candidate(framed: dict[str, Any], *, length: int) -> bool:
    """Select one exact outer frame whose sole nested blocker is damage."""
    if (framed.get("coverageStatus") != "unique"
            or framed.get("candidateCount") != 1
            or framed.get("eventPrefixStatus") != "success"
            or framed.get("rootContinuationStatus") != "success"
            or framed.get("namedOuterFrameStatus") not in ("named_exact_frame", "named_exact_full")):
        return False
    candidates = framed.get("candidates") or []
    if len(candidates) != 1:
        return False
    candidate = candidates[0]
    legacy = candidate.get("namedSchemaReceipt") or {}
    fields = legacy.get("forwardNamedFields") or []
    blockers = legacy.get("blockers") or []
    if (legacy.get("physicalEof") != length
            or legacy.get("actionUnionCount") != 0
            or legacy.get("hasConservativeSuffixFrontier") is not False
            or legacy.get("composedOpaqueBytes") != 0
            or len(blockers) != 2
            or blockers[1] != {"field": "root", "category": "recursive-name-authentication-incomplete",
                               "start": None, "end": None}
            or len(fields) != 15
            or [field.get("index") for field in fields] != list(range(15))):
        return False
    damage = blockers[0]
    if (damage.get("field") != "damageModifier"
            or damage.get("category") != "positive-modifier-recursive-proof"
            or type(damage.get("start")) is not int
            or type(damage.get("end")) is not int
            or [damage["start"], damage["end"]] != [fields[6].get("start"), fields[6].get("end")]
            or not damage["start"] < damage["end"]
            or fields[6].get("count") != 1):
        return False
    lengths = {0: 4, 3: 6, 5: 4, 13: 4}
    if any(fields[index].get("end", -1) - fields[index].get("start", 0) != size
           for index, size in lengths.items()):
        return False
    suffix = candidate.get("currentNamedSuffix") or {}
    stacking = suffix.get("stackingSettingsNativeChild") or {}
    timeline = suffix.get("timelineEmptyNativeChild") or {}
    blackboard = fields[4]
    blackboard_child = blackboard.get("nestedProfile") or {}
    global_modifier = fields[10]
    return (
        (candidate.get("currentNamedMiddle") or {}).get("iconConfigStatus") == "exact"
        and suffix.get("status") == "named-exact-to-eof"
        and suffix.get("endOffset") == length
        and stacking.get("status") == "exact-child-cursor"
        and stacking.get("stackEffectsCount") == 0
        and timeline.get("status") == "exact-null-or-empty-list-to-eof"
        and timeline.get("count") in (-1, 0)
        and blackboard_child.get("status") == "exact-datapair-list"
        and blackboard_child.get("wholeListExact") is True
        and blackboard_child.get("startOffset") == blackboard.get("start")
        and blackboard_child.get("consumedEnd") == blackboard.get("end")
        and type(blackboard_child.get("count")) is int
        and -1 <= blackboard_child["count"] <= 256
        and global_modifier.get("count") in (-1, 0)
        and global_modifier.get("end", -1) - global_modifier.get("start", 0) == 4
    )


def _allowed_blockers(blockers: Any) -> bool:
    if not isinstance(blockers, list):
        return False
    expected_root = {"field": "root", "category": "recursive-name-authentication-incomplete",
                     "start": None, "end": None}
    if expected_root not in blockers:
        return False
    rest = [row for row in blockers if row != expected_root]
    return len(rest) == 0 or (
        len(rest) == 1
        and rest[0].get("field") == "globalModifier"
        and rest[0].get("category") == "positive-modifier-recursive-proof"
        and type(rest[0].get("start")) is int
        and type(rest[0].get("end")) is int
        and rest[0]["start"] < rest[0]["end"]
    )


def _field4_exact(field: dict[str, Any]) -> bool:
    child = field.get("nestedProfile") or {}
    return (
        child.get("status") == "exact-datapair-list"
        and child.get("wholeListExact") is True
        and child.get("startOffset") == field.get("start")
        and child.get("consumedEnd") == field.get("end")
        and child.get("count") in (-1, 0, 1)
    )


def _field10_exact(field: dict[str, Any]) -> bool:
    if field.get("count") in (-1, 0):
        return field.get("end", -1) - field.get("start", 0) == 4
    child = field.get("nestedProfile") or {}
    return (
        field.get("count", 0) == 1
        and child.get("status") == "exact"
        and child.get("wholeValueExact") is True
        and child.get("startOffset") == field.get("start")
        and child.get("consumedEnd") == field.get("end")
        and child.get("count") == 1
    )


def validate_current_native_contract() -> dict[str, Any]:
    """Gate the root and all separately reviewed child read orders."""
    root = validate_root_native()
    if root.get("status") != "validated":
        return {"status": root.get("status", "failed"), "root": root}
    children: dict[str, dict[str, Any]] = {}
    for name, validate in CHILD_VALIDATORS.items():
        audit = validate()
        children[name] = audit
        if audit.get("status") != "validated":
            return {"status": audit.get("status", "failed"), "root": root,
                    "children": children, "failedChild": name}
    return {"status": "validated", "root": root, "children": children,
            "nativeInputs": root["nativeInputs"]}


def validate_positive_damage_native_contract(
    *, root_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Gate every selected reader used by the positive damage composition."""
    root = root_validation if root_validation is not None else validate_current_native_contract()
    if root.get("status") != "validated":
        return {"status": root.get("status", "failed"), "root": root}
    modifier = buff_damage_modifier_receipt.validate_current_native_contract()
    if modifier.get("status") != "validated":
        return {"status": modifier.get("status", "failed"), "root": root,
                "damageModifier": modifier}
    processor = buff_damage_scale_processor_child_receipt.validate_current_native_contract(
        modifier_native=modifier,
    )
    if processor.get("status") != "validated":
        return {"status": processor.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor}
    modify_calc = (
        buff_damage_modify_calc_result_processor_child_receipt.validate_current_native_contract(
            modifier_native=modifier,
        )
    )
    if modify_calc.get("status") != "validated":
        return {"status": modify_calc.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc}
    instant_modify = (
        buff_damage_instant_modify_attribute_processor_receipt.validate_current_native_contract(
            modifier_native=modifier,
        )
    )
    if instant_modify.get("status") != "validated":
        return {"status": instant_modify.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc,
                "processorInstantModifyAttribute": instant_modify}
    scalar = buff_damage_scalar_processor_child_receipt.validate_current_native_contract(
        modifier_native=modifier,
    )
    if scalar.get("status") != "validated":
        return {"status": scalar.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc, "processorScalar": scalar}
    processor_text = buff_damage_text_processor_child_receipt.validate_current_native_contract(
        modifier_native=modifier,
    )
    if processor_text.get("status") != "validated":
        return {"status": processor_text.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc, "processorScalar": scalar,
                "processorText": processor_text}
    condition = buff_damage_sequence_action_condition_receipt.validate_current_native_contract()
    if condition.get("status") != "validated":
        return {"status": condition.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc,
                "condition": condition}
    check_mask = buff_damage_check_decorate_mask_condition_receipt.validate_current_native_contract()
    if check_mask.get("status") != "validated":
        return {"status": check_mask.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc,
                "condition": condition, "checkDecorateMaskCondition": check_mask}
    check_type = buff_damage_check_type_condition_receipt.validate_current_native_contract()
    if check_type.get("status") != "validated":
        return {"status": check_type.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc,
                "condition": condition, "checkDecorateMaskCondition": check_mask,
                "checkDamageTypeCondition": check_type}
    check_type_mask = buff_damage_check_type_mask_condition_receipt.validate_current_native_contract()
    if check_type_mask.get("status") != "validated":
        return {"status": check_type_mask.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc,
                "condition": condition, "checkDecorateMaskCondition": check_mask,
                "checkDamageTypeCondition": check_type,
                "checkDamageTypeMaskCondition": check_type_mask}
    check_tag_match = buff_damage_check_tag_match_condition_receipt.validate_current_native_contract()
    if check_tag_match.get("status") != "validated":
        return {"status": check_tag_match.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc,
                "condition": condition, "checkDecorateMaskCondition": check_mask,
                "checkDamageTypeCondition": check_type,
                "checkDamageTypeMaskCondition": check_type_mask,
                "checkTagMatchCondition": check_tag_match}
    check_main_character = (
        buff_damage_check_main_character_condition_receipt.validate_current_native_contract()
    )
    if check_main_character.get("status") != "validated":
        return {"status": check_main_character.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc, "processorScalar": scalar,
                "processorText": processor_text,
                "condition": condition, "checkDecorateMaskCondition": check_mask,
                "checkDamageTypeCondition": check_type,
                "checkDamageTypeMaskCondition": check_type_mask,
                "checkTagMatchCondition": check_tag_match,
                "checkMainCharacterCondition": check_main_character}
    check_buff_stack = (
        buff_damage_check_buff_stack_condition_receipt.validate_current_native_contract()
    )
    if check_buff_stack.get("status") != "validated":
        return {"status": check_buff_stack.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc,
                "processorInstantModifyAttribute": instant_modify,
                "processorScalar": scalar, "processorText": processor_text,
                "condition": condition, "checkDecorateMaskCondition": check_mask,
                "checkDamageTypeCondition": check_type,
                "checkDamageTypeMaskCondition": check_type_mask,
                "checkTagMatchCondition": check_tag_match,
                "checkMainCharacterCondition": check_main_character,
                "checkBuffStackCondition": check_buff_stack}
    check_vitals = (
        buff_damage_check_vitals_condition_receipt.validate_current_native_contract()
    )
    if check_vitals.get("status") != "validated":
        return {"status": check_vitals.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc,
                "processorInstantModifyAttribute": instant_modify,
                "processorScalar": scalar, "processorText": processor_text,
                "condition": condition, "checkDecorateMaskCondition": check_mask,
                "checkDamageTypeCondition": check_type,
                "checkDamageTypeMaskCondition": check_type_mask,
                "checkTagMatchCondition": check_tag_match,
                "checkMainCharacterCondition": check_main_character,
                "checkBuffStackCondition": check_buff_stack,
                "checkVitalsCondition": check_vitals}
    two_action = buff_damage_two_action_condition_receipt.validate_current_native_contract()
    if two_action.get("status") != "validated":
        return {"status": two_action.get("status", "failed"), "root": root,
                "damageModifier": modifier, "processor": processor,
                "processorModifyCalc": modify_calc, "processorScalar": scalar,
                "processorInstantModifyAttribute": instant_modify,
                "processorText": processor_text,
                "condition": condition, "checkDecorateMaskCondition": check_mask,
                "checkDamageTypeCondition": check_type,
                "checkDamageTypeMaskCondition": check_type_mask,
                "checkTagMatchCondition": check_tag_match,
                "checkMainCharacterCondition": check_main_character,
                "checkBuffStackCondition": check_buff_stack,
                "checkVitalsCondition": check_vitals,
                "twoActionCondition": two_action}
    origin_or = buff_damage_origin_or_condition_receipt.validate_current_native_contract()
    if origin_or.get("status") != "validated":
        return {"status": origin_or.get("status", "failed"), "root": root,
                "originOrCondition": origin_or}
    known_compound = (
        buff_damage_known_compound_condition_receipt.validate_current_native_contract()
    )
    if known_compound.get("status") != "validated":
        return {"status": known_compound.get("status", "failed"), "root": root,
                "originOrCondition": origin_or,
                "knownCompoundCondition": known_compound}
    if_else = buff_damage_if_else_condition_receipt.validate_current_native_contract(
        main_character_native=check_main_character, sequence_native=condition,
    )
    if if_else.get("status") != "validated":
        return {"status": if_else.get("status", "failed"), "root": root,
                "ifElseCondition": if_else}
    not_next = buff_damage_not_next_main_condition_receipt.validate_current_native_contract(
        main_character_native=check_main_character, sequence_native=condition,
    )
    if not_next.get("status") != "validated":
        return {"status": not_next.get("status", "failed"), "root": root,
                "notNextMainCondition": not_next}
    two_direction_angle = (
        buff_damage_two_direction_angle_condition_receipt.validate_current_native_contract()
    )
    if two_direction_angle.get("status") != "validated":
        return {"status": two_direction_angle.get("status", "failed"), "root": root,
                "twoDirectionAngleCondition": two_direction_angle}
    return {"status": "validated", "root": root, "damageModifier": modifier,
            "processor": processor, "processorModifyCalc": modify_calc,
            "processorInstantModifyAttribute": instant_modify,
            "processorScalar": scalar, "processorText": processor_text,
            "condition": condition,
            "checkDecorateMaskCondition": check_mask,
            "checkDamageTypeCondition": check_type,
            "checkDamageTypeMaskCondition": check_type_mask,
            "checkTagMatchCondition": check_tag_match,
            "checkMainCharacterCondition": check_main_character,
            "checkBuffStackCondition": check_buff_stack,
            "checkVitalsCondition": check_vitals,
            "twoActionCondition": two_action,
            "originOrCondition": origin_or,
            "knownCompoundCondition": known_compound,
            "ifElseCondition": if_else,
            "notNextMainCondition": not_next,
            "twoDirectionAngleCondition": two_direction_angle,
            "nativeInputs": root["nativeInputs"]}


def decode_no_positive_buff(
    data: bytes, *, source: str, expected_sha256: str,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Decode the established null/empty and DataPair/GlobalModifier cohort."""
    return _decode_buff(
        data, source=source, expected_sha256=expected_sha256,
        native_validation=native_validation, positive_damage_validation=None,
    )


def decode_positive_damage_buff(
    data: bytes, *, source: str, expected_sha256: str,
    native_validation: dict[str, Any],
    positive_damage_validation: dict[str, Any],
) -> dict[str, Any]:
    """Decode selected conditions and processors in exact damage child roots."""
    return _decode_buff(
        data, source=source, expected_sha256=expected_sha256,
        native_validation=native_validation,
        positive_damage_validation=positive_damage_validation,
    )


def _decode_buff(
    data: bytes, *, source: str, expected_sha256: str,
    native_validation: dict[str, Any],
    positive_damage_validation: dict[str, Any] | None,
) -> dict[str, Any]:
    """Walk the original logical bytes through all thirty named root fields."""
    positive_damage = positive_damage_validation is not None
    if native_validation.get("status") != "validated":
        raise ValueError("buffRootNoPositive.native:unvalidated")
    if positive_damage and (
        positive_damage_validation.get("status") != "validated"
        or positive_damage_validation.get("root") != native_validation
        or any(positive_damage_validation.get(name, {}).get("status") != "validated"
               for name in ("damageModifier", "processor", "processorModifyCalc",
            "processorScalar", "processorText", "processorInstantModifyAttribute", "condition",
                            "checkDecorateMaskCondition", "checkDamageTypeCondition",
                            "checkDamageTypeMaskCondition", "checkTagMatchCondition",
                            "checkMainCharacterCondition",
                            "checkBuffStackCondition",
                            "checkVitalsCondition",
                            "twoActionCondition",
                            "originOrCondition",
                            "knownCompoundCondition",
                            "ifElseCondition",
                            "notNextMainCondition",
                            "twoDirectionAngleCondition"))
    ):
        raise ValueError("buffRootPositiveDamage.native:unvalidated")
    if not isinstance(data, bytes) or not data:
        raise ValueError("buffRootNoPositive.input:empty-or-nonbytes")
    if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
            or any(ch not in "0123456789ABCDEFabcdef" for ch in expected_sha256)):
        raise ValueError("buffRootNoPositive.source:invalid-sha256")
    actual_sha256 = hashlib.sha256(data).hexdigest().upper()
    if actual_sha256 != expected_sha256.upper():
        raise ValueError("buffRootNoPositive.source:sha256-mismatch")
    if (not isinstance(source, str)
            or source.split("/")[:3] != ["Data", "Json", "BuffData"]
            or len(source.split("/")) != 4
            or not source.endswith(".json")
            or PurePosixPath(source).name in ("", ".", "..")):
        raise ValueError("buffRootNoPositive.source:invalid-path")
    contract = _native_contract()
    contract_fields = contract["fields"]
    if positive_damage and contract_fields[6]["name"] != "damageModifier":
        raise ValueError("buffRootPositiveDamage.contract:member-six")
    if data[0] != contract["rootMemberCount"]:
        raise ValueError(f"buffRootNoPositive.header:expected=30 actual={data[0]}")

    fields: list[dict[str, Any]] = []

    def add(index: int, start: int, end: int, **detail: Any) -> None:
        if (len(fields) != index or type(start) is not int or type(end) is not int
                or start != (1 if index == 0 else fields[-1]["end"])
                or not start < end <= len(data)):
            raise ValueError(f"buffRootNoPositive.field[{index}]:noncontiguous")
        fields.append({"index": index, "name": contract_fields[index]["name"],
                       "declaredType": contract_fields[index]["declaredType"],
                       "start": start, "end": end, "boundaryClass": "exact-cursor",
                       **detail})

    def count_null_or_empty(start: int, index: int) -> int:
        if start + 4 > len(data):
            raise ValueError(f"buffRootNoPositive.field[{index}]:truncated-count")
        count = struct.unpack_from("<i", data, start)[0]
        if count not in (-1, 0):
            raise ValueError(f"buffRootNoPositive.field[{index}]:positive-or-invalid={count}")
        add(index, start, start + 4, count=count,
            representation="null" if count == -1 else "empty")
        return start + 4

    first = event_prefix(data, source=source, limit=len(data))
    if first["status"] != "supported-prefix" or len(first["namedFields"]) != 1:
        raise ValueError(f"buffRootNoPositive.abilityEventAction:{first['diagnostic']}")
    if first["consumedEnd"] != 5 or struct.unpack_from("<i", data, 1)[0] != 0:
        raise ValueError("buffRootNoPositive.abilityEventAction:not-empty")
    add(0, 1, first["consumedEnd"], count=0, representation="empty")
    continuation = root_continuation(
        data, source=source, start=first["consumedEnd"], limit=len(data),
    )
    if (continuation["status"] != "supported-prefix"
            or len(continuation["namedFields"]) != 5):
        raise ValueError(f"buffRootNoPositive.rootContinuation:{continuation['diagnostic']}")
    for row in continuation["namedFields"]:
        index = row["index"]
        if row["name"] != contract_fields[index]["name"]:
            raise ValueError(f"buffRootNoPositive.field[{index}]:contract-name")
        start, end = row["start"], row["end"]
        if index == 1:
            child = buff_adding_cooldown.decode_adding_cooldown(
                data, start, end,
                native_validation=native_validation["children"]["addingCooldown"],
            )
            add(index, start, end, child=child)
        elif index == 2:
            if end - start < 4:
                raise ValueError("buffRootNoPositive.applyTags:truncated")
            count = struct.unpack_from("<i", data, start)[0]
            if count < -1 or count > 4096 or end - start != 4 + max(0, count) * 4:
                raise ValueError(f"buffRootNoPositive.applyTags:count={count}")
            add(index, start, end, count=count,
                representation="null" if count == -1 else "raw-u32-array")
        elif index == 3:
            if end - start != 6 or data[start] != 2:
                raise ValueError("buffRootNoPositive.attributeModifier:not-empty")
            count = struct.unpack_from("<i", data, start + 1)[0]
            if count not in (-1, 0):
                raise ValueError("buffRootNoPositive.attributeModifier:positive")
            add(index, start, end, memberCount=2, arrayCount=count,
                terminalRaw=data[end - 1])
        else:
            if index == 4:
                if (native_validation["children"]["blackboardDataPairs"].get("status")
                        != "validated"):
                    raise ValueError("buffRootNoPositive.blackboard:native-unvalidated")
                child = buff_datapair_native.decode_datapair_list(
                    data, start, end,
                    native_validation=native_validation["children"]["blackboardDataPairs"],
                    require_end=False,
                )
                if child["consumedEnd"] != end:
                    raise ValueError(
                        f"buffRootNoPositive.blackboard:endpoint={child['consumedEnd']} expected={end}"
                    )
                add(index, start, end, count=child["count"], child=child)
                continue
            if index == 10:
                if (native_validation["children"]["globalModifier"].get("status")
                        != "validated"):
                    raise ValueError("buffRootNoPositive.globalModifier:native-unvalidated")
                child = buff_global_modifier_receipt.decode_global_modifier_collection(
                    data, start, end, source=source,
                    native_validation=native_validation["children"]["globalModifier"],
                    blackboard_native_validation=native_validation["children"]["addingCooldown"],
                )
                if child.get("count") != 1:
                    raise ValueError("buffRootNoPositive.globalModifier:positive-count")
                add(index, start, end, count=child["count"], child=child)
                continue
            if end - start != 4:
                raise ValueError(f"buffRootNoPositive.field[{index}]:not-empty")
            count = struct.unpack_from("<i", data, start)[0]
            if count not in (-1, 0):
                raise ValueError(f"buffRootNoPositive.field[{index}]:positive")
            add(index, start, end, count=count,
                representation="null" if count == -1 else "empty")
    cursor = continuation["consumedEnd"]

    if positive_damage:
        start = cursor
        reader = _ResidualReader(data, source, len(data))
        reader.pos = start
        count = reader.damage_modifier_collection_profile()
        cursor = reader.pos
        if count != 1:
            raise ValueError(f"buffRootPositiveDamage.damageModifier:count={count}")
        child = buff_damage_modifier_receipt.decode_damage_modifier_collection(
            data, start, cursor, source=source,
            native_validation=positive_damage_validation["damageModifier"],
            processor_native_validation=positive_damage_validation["processor"],
        )
        elements = child.get("elements") or []
        if (child.get("count") != 1 or len(elements) != 1
                or child.get("startOffset") != start
                or child.get("consumedEnd") != cursor
                or elements[0].get("status") != "named-direct-child-spans"):
            raise ValueError("buffRootPositiveDamage.damageModifier:child-shape")
        element = elements[0]
        nested = element.get("fields") or []
        if ([row.get("name") for row in nested]
                != ["condition", "damageProcessors", "enableSide"]
                or element.get("start") != start + 4
                or element.get("end") != cursor
                or element.get("headerRange") != [start + 4, start + 5]
                or nested[0].get("start") != start + 5
                or nested[0].get("end") != nested[1].get("start")
                or nested[1].get("end") != nested[2].get("start")
                or nested[2].get("end") != cursor
                or nested[2]["end"] - nested[2]["start"] != 4):
            raise ValueError("buffRootPositiveDamage.damageModifier:field-tiling")
        condition_tags = nested[0].get("actionTags")
        if nested[0].get("actionUnionCount") == 0 and condition_tags == []:
            condition = buff_damage_sequence_action_condition_receipt.decode_zero_action_condition(
                data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                logical_sha256=actual_sha256,
                native_validation=positive_damage_validation["condition"],
            )
            condition_exact = (
                condition.get("status") == "exact-empty-sequence"
                and condition.get("actionCount") == 0
                and len(condition.get("terminal") or []) == 2
                and condition.get("wholeStoredSpanExact") is True
            )
        elif (nested[0].get("actionUnionCount") == 1
              and condition_tags == [positive_damage_validation["checkDecorateMaskCondition"]["unionTag"]]):
            condition = (
                buff_damage_check_decorate_mask_condition_receipt.decode_check_decorate_mask_condition(
                    data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                    logical_sha256=actual_sha256,
                    native_validation=positive_damage_validation["checkDecorateMaskCondition"],
                )
            )
            condition_exact = (
                condition.get("status") == "exact-one-action-sequence"
                and condition.get("actionCount") == 1
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and (condition.get("action") or {}).get("tag") == condition_tags[0]
            )
        elif (nested[0].get("actionUnionCount") == 1
              and condition_tags == [positive_damage_validation["checkDamageTypeCondition"]["unionTag"]]):
            condition = buff_damage_check_type_condition_receipt.decode_check_damage_type_condition(
                data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                logical_sha256=actual_sha256,
                native_validation=positive_damage_validation["checkDamageTypeCondition"],
            )
            condition_exact = (
                condition.get("status") == "exact-one-action-sequence"
                and condition.get("actionCount") == 1
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and (condition.get("action") or {}).get("tag") == condition_tags[0]
            )
        elif (nested[0].get("actionUnionCount") == 1
              and condition_tags == [positive_damage_validation["checkDamageTypeMaskCondition"]["unionTag"]]):
            condition = (
                buff_damage_check_type_mask_condition_receipt.decode_check_damage_type_mask_condition(
                    data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                    logical_sha256=actual_sha256,
                    native_validation=positive_damage_validation["checkDamageTypeMaskCondition"],
                )
            )
            condition_exact = (
                condition.get("status") == "exact-one-action-sequence"
                and condition.get("actionCount") == 1
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and (condition.get("action") or {}).get("tag") == condition_tags[0]
            )
        elif (nested[0].get("actionUnionCount") == 1
              and condition_tags == [positive_damage_validation["checkTagMatchCondition"]["unionTag"]]):
            condition = buff_damage_check_tag_match_condition_receipt.decode_check_tag_match_condition(
                data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                logical_sha256=actual_sha256,
                native_validation=positive_damage_validation["checkTagMatchCondition"],
            )
            condition_exact = (
                condition.get("status") == "exact-one-action-sequence"
                and condition.get("actionCount") == 1
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and (condition.get("action") or {}).get("tag") == condition_tags[0]
            )
        elif (nested[0].get("actionUnionCount") == 1
              and condition_tags == [positive_damage_validation["checkMainCharacterCondition"]["unionTag"]]):
            condition = (
                buff_damage_check_main_character_condition_receipt.decode_check_main_character_condition(
                    data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                    logical_sha256=actual_sha256,
                    native_validation=positive_damage_validation["checkMainCharacterCondition"],
                )
            )
            condition_exact = (
                condition.get("status") == "exact-one-action-sequence"
                and condition.get("actionCount") == 1
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and (condition.get("action") or {}).get("tag") == condition_tags[0]
            )
        elif (nested[0].get("actionUnionCount") == 1
              and condition_tags == [positive_damage_validation["checkBuffStackCondition"]["unionTag"]]):
            condition = (
                buff_damage_check_buff_stack_condition_receipt.decode_check_buff_stack_condition(
                    data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                    logical_sha256=actual_sha256,
                    native_validation=positive_damage_validation["checkBuffStackCondition"],
                )
            )
            condition_exact = (
                condition.get("status") == "exact-one-action-sequence"
                and condition.get("actionCount") == 1
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and (condition.get("action") or {}).get("tag") == condition_tags[0]
            )
        elif (nested[0].get("actionUnionCount") == 1
              and len(condition_tags or []) == 1
              and condition_tags[0] in [route["unionTag"] for route in
                                        positive_damage_validation["checkVitalsCondition"]["routes"]]):
            condition = (
                buff_damage_check_vitals_condition_receipt.decode_check_vitals_condition(
                    data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                    logical_sha256=actual_sha256,
                    native_validation=positive_damage_validation["checkVitalsCondition"],
                )
            )
            condition_exact = (
                condition.get("status") == "exact-one-action-sequence"
                and condition.get("actionCount") == 1
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and (condition.get("action") or {}).get("tag") == condition_tags[0]
            )
        elif (nested[0].get("actionUnionCount") == 2
              and condition_tags == positive_damage_validation["twoActionCondition"]["selectedActionTags"]):
            condition = buff_damage_two_action_condition_receipt.decode_two_action_condition(
                data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                logical_sha256=actual_sha256,
                native_validation=positive_damage_validation["twoActionCondition"],
            )
            condition_exact = (
                condition.get("status") == "exact-two-action-sequence"
                and condition.get("actionCount") == 2
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and [action.get("tag") for action in condition.get("actions") or []]
                    == condition_tags
                and all(action.get("recursiveNamedSchemaExact") is True
                        for action in condition.get("actions") or [])
            )
        elif (condition_tags in (
                  positive_damage_validation["originOrCondition"]["simpleActionTags"],
                  [positive_damage_validation["originOrCondition"]["originUnionTag"]]
                  + [tags[0] for tags in positive_damage_validation[
                      "originOrCondition"]["orNestedSequenceTags"]]
                  + [positive_damage_validation["originOrCondition"]["orUnionTag"]],
              )
              and nested[0].get("actionUnionCount") == len(condition_tags)):
            condition = buff_damage_origin_or_condition_receipt.decode_origin_or_condition(
                data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                logical_sha256=actual_sha256,
                native_validation=positive_damage_validation["originOrCondition"],
            )
            origin_native = positive_damage_validation["originOrCondition"]
            selected_branch = (
                "origin-poise" if condition_tags == origin_native["simpleActionTags"]
                else "origin-or"
            )
            expected_top = (
                origin_native["simpleActionTags"] if selected_branch == "origin-poise"
                else origin_native["nestedActionTags"]
            )
            actions = condition.get("actions") or []
            or_fields = ((actions[1].get("namedFields") or []) if len(actions) == 2 else [])
            nested_sequences = (
                (or_fields[4].get("namedChildren") or [])
                if len(or_fields) == 5 and selected_branch == "origin-or" else []
            )
            condition_exact = (
                condition.get("status") == "exact-two-action-sequence"
                and condition.get("branch") == selected_branch
                and condition.get("actionCount") == 2
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and [action.get("tag") for action in actions] == expected_top
                and all(action.get("recursiveNamedSchemaExact") is True for action in actions)
                and (selected_branch != "origin-or"
                     or [[item.get("tag") for item in child.get("actions") or []]
                         for child in nested_sequences]
                     == origin_native["orNestedSequenceTags"])
            )
        elif (condition_tags in positive_damage_validation["knownCompoundCondition"]["selectedActionPatterns"]
              and nested[0].get("actionUnionCount") == len(condition_tags)):
            condition = (
                buff_damage_known_compound_condition_receipt.decode_known_compound_condition(
                    data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                    logical_sha256=actual_sha256,
                    native_validation=positive_damage_validation["knownCompoundCondition"],
                )
            )
            actions = condition.get("actions") or []
            condition_exact = (
                condition.get("status") == "exact-selected-compound-sequence"
                and condition.get("actionCount") == len(condition_tags)
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and [action.get("tag") for action in actions] == condition_tags
                and all(action.get("recursiveNamedSchemaExact") is True for action in actions)
            )
        elif (condition_tags in ([104, 304, 201], [104, 304, 201, 91])
              and nested[0].get("actionUnionCount") == len(condition_tags)):
            condition = (
                buff_damage_if_else_condition_receipt.decode_if_else_condition(
                    data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                    logical_sha256=actual_sha256,
                    native_validation=positive_damage_validation["ifElseCondition"],
                )
            )
            actions = condition.get("actions") or []
            if_else_fields = actions[0].get("namedFields") or [] if actions else []
            nested_children = (
                [if_else_fields[index].get("namedChild") or {} for index in (5, 6, 7)]
                if len(if_else_fields) == 8 else []
            )
            condition_exact = (
                condition.get("status") == "exact-selected-if-else-sequence"
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and condition.get("actionCount") in (1, 2)
                and len(actions) == condition["actionCount"]
                and [action.get("tag") for action in actions]
                    == positive_damage_validation["ifElseCondition"]["selectedTopActionPatterns"][
                        condition["actionCount"] - 1]
                and all(action.get("recursiveNamedSchemaExact") is True for action in actions)
                and [child.get("actionCount") for child in nested_children] == [1, 0, 1]
                and (nested_children[0].get("action") or {}).get("tag") == 104
                and (nested_children[2].get("action") or {}).get("tag") == 304
            )
        elif (condition_tags == positive_damage_validation["notNextMainCondition"]["selectedActionTags"]
              and nested[0].get("actionUnionCount") == 2):
            condition = (
                buff_damage_not_next_main_condition_receipt.decode_not_next_main_condition(
                    data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                    logical_sha256=actual_sha256,
                    native_validation=positive_damage_validation["notNextMainCondition"],
                )
            )
            actions = condition.get("actions") or []
            condition_exact = (
                condition.get("status") == "exact-two-action-sequence"
                and condition.get("actionCount") == 2
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and [action.get("tag") for action in actions] == condition_tags
                and all(action.get("recursiveNamedSchemaExact") is True for action in actions)
            )
        elif (condition_tags == positive_damage_validation["twoDirectionAngleCondition"]["selectedActionTags"]
              and nested[0].get("actionUnionCount") == 2):
            condition = (
                buff_damage_two_direction_angle_condition_receipt.decode_two_direction_angle_condition(
                    data, source=source, start=nested[0]["start"], end=nested[0]["end"],
                    logical_sha256=actual_sha256,
                    native_validation=positive_damage_validation["twoDirectionAngleCondition"],
                )
            )
            actions = condition.get("actions") or []
            plan = positive_damage_validation["twoDirectionAngleCondition"]["fieldPlan"]
            target_names = positive_damage_validation["twoDirectionAngleCondition"]["selectedTargetMemberNames"]
            blackboard_name = positive_damage_validation["twoDirectionAngleCondition"]["selectedBlackboardMemberName"]
            condition_exact = (
                condition.get("status") == "exact-two-action-sequence"
                and condition.get("actionCount") == 2
                and condition.get("wholeStoredSpanExact") is True
                and condition.get("recursiveNamedSchemaExact") is True
                and condition.get("terminalRawHex")
                    == positive_damage_validation["twoDirectionAngleCondition"]["selectedTerminalRawHex"]
                and len(actions) == 2
                and [action.get("tag") for action in actions] == condition_tags
                and all(
                    action.get("recursiveNamedSchemaExact") is True
                    and [field.get("name") for field in action.get("namedFields") or []]
                        == [field["name"] for field in plan]
                    and all(
                        (field.get("namedChild") or {}).get("status") == "exact-simple-target"
                        and (field.get("namedChild") or {}).get("end") == field.get("end")
                        for field in action.get("namedFields") or []
                        if field.get("name") in target_names
                    )
                    and any(
                        field.get("name") == blackboard_name
                        and (field.get("namedChild") or {}).get("wholeValueExact") is True
                        and (field.get("namedChild") or {}).get("consumedEnd") == field.get("end")
                        for field in action.get("namedFields") or []
                    )
                    for action in actions
                )
            )
        else:
            raise ValueError("buffRootPositiveDamage.damageModifier:unsupported-condition-actions")
        processors = nested[1].get("processors") or []
        processor_count = nested[1].get("count")
        selected_two_direction_angle = (
            condition.get("actionCount") == 2
            and condition.get("status") == "exact-two-action-sequence"
            and condition_tags
                == positive_damage_validation["twoDirectionAngleCondition"]["selectedActionTags"]
        )
        if (not condition_exact
                or processor_count not in (1, 2)
                or len(processors) != processor_count
                or processors[0].get("start") != nested[1]["start"] + 4
                or (processor_count == 1
                    and processors[0].get("end") != nested[1]["end"])
                or (processor_count == 2
                    and (condition.get("actionCount") != 0 and not selected_two_direction_angle
                         or [row.get("tag") for row in processors] != [5, 6]
                         or processors[0].get("end") != processors[1].get("start")
                         or processors[1].get("end") != nested[1]["end"]))):
            raise ValueError("buffRootPositiveDamage.damageModifier:condition-or-processor")
        processor_tag = processors[0].get("tag")
        if selected_two_direction_angle and processor_count != 2:
            raise ValueError("buffRootPositiveDamage.damageModifier:two-angle-processor-pair")
        if condition.get("actionCount") == 2 and not selected_two_direction_angle and (
            processor_count != 1 or not (
                processor_tag == 5
                or (processor_tag == 4
                    and condition.get("status") == "exact-two-action-sequence"
                    and [action.get("tag") for action in condition.get("actions") or []]
                        == positive_damage_validation["notNextMainCondition"]["selectedActionTags"])
            )
        ):
            raise ValueError("buffRootPositiveDamage.damageModifier:two-action-processor")
        if processor_tag == positive_damage_validation["processor"]["unionTag"]:
            processor = processors[0].get("namedChild") or {}
            plan = positive_damage_validation["processor"]["fieldPlan"]
        elif processor_tag == positive_damage_validation["processorModifyCalc"]["unionTag"]:
            if (condition.get("actionCount") != 1
                    or (condition.get("action") or {}).get("tag") not in (
                        positive_damage_validation["checkDecorateMaskCondition"]["unionTag"],
                        positive_damage_validation["checkDamageTypeCondition"]["unionTag"],
                    )):
                raise ValueError("buffRootPositiveDamage.damageModifier:tag-ten-condition")
            processor = (
                buff_damage_modify_calc_result_processor_child_receipt.decode_modify_calc_result_processor_span(
                    data, source=source, logical_sha256=actual_sha256,
                    start=processors[0]["start"], end=processors[0]["end"],
                    native_validation=positive_damage_validation["processorModifyCalc"],
                )
            )
            plan = positive_damage_validation["processorModifyCalc"]["fieldPlan"]
            named = processor.get("namedFields") or []
            if (len(named) != 3
                    or any((named[index].get("namedChild") or {}).get("wholeValueExact") is not True
                           or (named[index]["namedChild"]).get("startOffset") != named[index].get("start")
                           or (named[index]["namedChild"]).get("consumedEnd") != named[index].get("end")
                           for index in (0, 2))):
                raise ValueError("buffRootPositiveDamage.damageModifier:tag-ten-blackboard-children")
        elif processor_tag in (0, 2, 3, 4):
            if (processor_tag == 4
                    and (condition.get("actionCount") != 2
                         or [action.get("tag") for action in condition.get("actions") or []]
                             != positive_damage_validation["notNextMainCondition"]["selectedActionTags"])):
                raise ValueError("buffRootPositiveDamage.damageModifier:tag-four-condition")
            if (processor_tag != 4 and (condition.get("actionCount") != 1
                    or (processor_tag == 2 and (condition.get("action") or {}).get("tag")
                        != positive_damage_validation["checkDecorateMaskCondition"]["unionTag"])
                    or (processor_tag in (0, 3)
                        and (condition.get("action") or {}).get("tag") not in (
                            positive_damage_validation["checkDecorateMaskCondition"]["unionTag"],
                            positive_damage_validation["checkTagMatchCondition"]["unionTag"],
                        )))):
                raise ValueError("buffRootPositiveDamage.damageModifier:scalar-condition")
            processor = buff_damage_scalar_processor_child_receipt.decode_scalar_processor_span(
                data, source=source, logical_sha256=actual_sha256,
                start=processors[0]["start"], end=processors[0]["end"],
                native_validation=positive_damage_validation["processorScalar"],
            )
            route = next(
                (route for route in positive_damage_validation["processorScalar"]["routes"]
                 if route["unionTag"] == processor_tag), None,
            )
            if route is None:
                raise ValueError("buffRootPositiveDamage.damageModifier:scalar-route")
            plan = route["fieldPlan"]
            named = processor.get("namedFields") or []
            if (len(named) != 1
                    or (named[0].get("namedChild") or {}).get("wholeValueExact") is not True
                    or named[0]["namedChild"].get("startOffset") != named[0].get("start")
                    or named[0]["namedChild"].get("consumedEnd") != named[0].get("end")):
                raise ValueError("buffRootPositiveDamage.damageModifier:scalar-blackboard-child")
        elif processor_tag == positive_damage_validation["processorInstantModifyAttribute"]["unionTag"]:
            if (condition.get("actionCount") != 1
                    or (condition.get("action") or {}).get("tag")
                    != positive_damage_validation["checkBuffStackCondition"]["unionTag"]):
                raise ValueError("buffRootPositiveDamage.damageModifier:tag-nine-condition")
            processor = (
                buff_damage_instant_modify_attribute_processor_receipt.decode_instant_modify_attribute_processor_span(
                    data, source=source, logical_sha256=actual_sha256,
                    start=processors[0]["start"], end=processors[0]["end"],
                    native_validation=positive_damage_validation["processorInstantModifyAttribute"],
                )
            )
            plan = positive_damage_validation["processorInstantModifyAttribute"]["fieldPlan"]
            named = processor.get("namedFields") or []
            inner = ((named[0].get("namedChild") or {}).get("namedFields") or []) if named else []
            if (len(named) != 2 or len(inner) != 4
                    or named[0].get("end") != named[1].get("start")
                    or [row.get("name") for row in inner]
                    != [row["name"] for row in positive_damage_validation[
                        "processorInstantModifyAttribute"]["modifierFieldPlan"]]
                    or (inner[3].get("namedChild") or {}).get("wholeValueExact") is not True
                    or inner[3]["namedChild"].get("startOffset") != inner[3].get("start")
                    or inner[3]["namedChild"].get("consumedEnd") != inner[3].get("end")):
                raise ValueError("buffRootPositiveDamage.damageModifier:tag-nine-modifier-child")
        else:
            raise ValueError("buffRootPositiveDamage.damageModifier:unsupported-processor-tag")
        if (processor.get("status") != "named-direct-members-exact-span"
                or processor.get("wholeStoredSpanExact") is not True
                or processor.get("recursiveNamedSchemaExact") is not True
                or processor.get("start") != processors[0]["start"]
                or processor.get("end") != processors[0]["end"]
                or processor.get("unionTag") != processor_tag
                or [row.get("name") for row in processor.get("namedFields") or []]
                   != [row["name"] for row in plan]):
            raise ValueError("buffRootPositiveDamage.damageModifier:processor-child")
        processor_children = [processor]
        if processor_count == 2:
            second = buff_damage_text_processor_child_receipt.decode_damage_text_processor_span(
                data, source=source, logical_sha256=actual_sha256,
                start=processors[1]["start"], end=processors[1]["end"],
                native_validation=positive_damage_validation["processorText"],
            )
            if (second.get("status") != "named-direct-members-exact-span"
                    or second.get("wholeStoredSpanExact") is not True
                    or second.get("recursiveNamedSchemaExact") is not True
                    or second.get("start") != processors[1]["start"]
                    or second.get("end") != processors[1]["end"]
                    or second.get("unionTag") != positive_damage_validation["processorText"]["unionTag"]
                    or [row.get("name") for row in second.get("namedFields") or []]
                       != [row["name"] for row in positive_damage_validation["processorText"]["fieldPlan"]]):
                raise ValueError("buffRootPositiveDamage.damageModifier:text-processor-child")
            processor_children.append(second)
        composed = {
            "status": "exact-composed-damage-list", "startOffset": start,
            "consumedEnd": cursor, "count": 1, "wholeListExact": True,
            "parent": child, "conditionChild": condition,
            "processorChild": processor,
            "processorChildren": processor_children,
            "evidenceBoundary": (
                "Selected root list and child read/store order, exact selected condition, "
                "selected processor list and named child spans through the original "
                "logical bytes. Stored values do not establish runtime effects."
            ),
        }
        add(6, start, cursor, count=1, child=composed)
    else:
        cursor = count_null_or_empty(cursor, 6)
    start = cursor
    if start + 8 > len(data):
        raise ValueError("buffRootNoPositive.dispelConfig:truncated")
    child = buff_dispel_config.decode_dispel_config(
        data, start, start + 8,
        native_validation=native_validation["children"]["dispelConfig"],
    )
    cursor = start + 8
    add(7, start, cursor, child=child)

    for index in (8,):
        start = cursor
        value, cursor = read_buff_blackboard_float_raw_field_bounded(
            data, start, len(data), contract_fields[index]["name"],
        )
        child = buff_adding_cooldown.decode_adding_cooldown(
            data, start, cursor,
            native_validation=native_validation["children"]["addingCooldown"],
        )
        add(index, start, cursor, value=value, child=child)
    start = cursor
    value, cursor = read_buff_bool_field(data, start, contract_fields[9]["name"])
    add(9, start, cursor, value=value)
    start = cursor
    if start + 4 > len(data):
        raise ValueError("buffRootNoPositive.globalModifier:truncated-count")
    global_count = struct.unpack_from("<i", data, start)[0]
    if global_count in (-1, 0):
        cursor = start + 4
        add(10, start, cursor, count=global_count,
            representation="null" if global_count == -1 else "empty")
    else:
        child = buff_global_modifier_receipt.decode_global_modifier_collection(
            data, start, len(data), source=source,
            native_validation=native_validation["children"]["globalModifier"],
            blackboard_native_validation=native_validation["children"]["addingCooldown"],
            require_end=False,
        )
        if child.get("count") != 1:
            raise ValueError(f"buffRootNoPositive.globalModifier:count={child.get('count')}")
        cursor = child["consumedEnd"]
        add(10, start, cursor, count=child["count"], child=child)
    for index in (11, 12):
        start = cursor
        value, cursor = read_buff_bool_field(data, start, contract_fields[index]["name"])
        add(index, start, cursor, value=value)
    cursor = count_null_or_empty(cursor, 13)
    start = cursor
    child = buff_icon_config.decode_icon_config(data, start, len(data), require_limit_end=False)
    cursor = child["consumedEnd"]
    add(14, start, cursor, child=child)

    start = cursor
    buff_id, cursor = read_buff_memorypack_utf8_string_strict_bounded(
        data, start, len(data), "id", max_length=512,
    )
    expected_id = PurePosixPath(source).stem
    if buff_id != expected_id:
        raise ValueError(f"buffRootNoPositive.id:expected={expected_id!r} actual={buff_id!r}")
    add(15, start, cursor, value=buff_id)
    cursor = count_null_or_empty(cursor, 16)
    for index in (17, 18):
        start = cursor
        value, cursor = read_buff_bool_field(data, start, contract_fields[index]["name"])
        add(index, start, cursor, value=value)
    start = cursor
    if cursor >= len(data):
        raise ValueError("buffRootNoPositive.lifeType:truncated")
    cursor += 1
    add(19, start, cursor, rawByte=data[start])
    start = cursor
    value, cursor = read_buff_blackboard_int_field(
        data, start, contract_fields[20]["name"],
    )
    add(20, start, cursor, value=value)
    start = cursor
    value, cursor = read_buff_bool_field(data, start, contract_fields[21]["name"])
    add(21, start, cursor, value=value)
    cursor = count_null_or_empty(cursor, 22)
    cursor = count_null_or_empty(cursor, 23)
    start = cursor
    child = buff_stacking_compact_native.decode_stacking_settings_compact(
        data, start,
        native_validation=native_validation["children"]["stackingSettings"],
    )
    if child["stackEffectsCount"] != 0:
        raise ValueError("buffRootNoPositive.stackingSettings:positive-stack-effects")
    cursor = child["consumedEnd"]
    add(24, start, cursor, child=child)
    start = cursor
    if start + 4 > len(data):
        raise ValueError("buffRootNoPositive.tagsAfterTriggerExtendBuffAction:truncated-count")
    count = struct.unpack_from("<i", data, start)[0]
    if count < -1 or count > 4096 or start + 4 + max(0, count) * 4 > len(data):
        raise ValueError(f"buffRootNoPositive.tagsAfterTriggerExtendBuffAction:count={count}")
    cursor = start + 4 + max(0, count) * 4
    add(25, start, cursor, count=count,
        representation="null" if count == -1 else "raw-u32-array")
    start = cursor
    child = buff_timeline_empty_native.decode_empty_timeline_suffix(
        data, start,
        native_validation=native_validation["children"]["timelineActions"],
    )
    cursor = child["consumedEnd"]
    add(26, start, cursor, child=child)
    start = cursor
    value, cursor = read_buff_blackboard_float_raw_field_bounded(
        data, start, len(data), contract_fields[27]["name"],
    )
    named_child = buff_adding_cooldown.decode_adding_cooldown(
        data, start, cursor,
        native_validation=native_validation["children"]["addingCooldown"],
    )
    add(27, start, cursor, value=value, child=named_child)
    for index in (28, 29):
        start = cursor
        value, cursor = read_buff_bool_field(data, start, contract_fields[index]["name"])
        add(index, start, cursor, value=value)
    if cursor != len(data) or cursor != child["followingEnd"]:
        raise ValueError(f"buffRootNoPositive.eof:cursor={cursor} length={len(data)}")
    if len(fields) != 30 or fields[-1]["end"] != len(data):
        raise ValueError("buffRootNoPositive.fields:incomplete")
    return {
        "schema": (
            "endfield.buff-root-positive-damage-receipt.v12" if positive_damage
            else "endfield.buff-root-no-positive-receipt.v1"
        ),
        "source": source,
        "logicalSha256": actual_sha256,
        "status": "named-exact-full",
        "wholeSchemaExact": True,
        "namedOuterFrameStatus": "named_exact_full",
        "rootMemberCount": 30,
        "headerRange": [0, 1],
        "fields": fields,
        "bytesConsumed": len(data),
        "physicalEof": len(data),
        "nativeStatus": "validated",
        "evidenceBoundary": (
            "Selected native source/read/store order and child layouts, supplied "
            "SHA256 checked against logical bytes, "
            + ("single positive damage child and otherwise exact recursive-list branches, "
               if positive_damage else "null/empty recursive-list branches, ")
            +
            "30 contiguous field spans, id equality, and physical EOF. "
            "The caller owns independent source authentication; live formatter-provider "
            "selection and gameplay meaning are unresolved."
        ),
    }
