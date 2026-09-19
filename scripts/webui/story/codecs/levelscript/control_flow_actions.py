"""Exact current-build local control-flow action decoders."""

from __future__ import annotations

import struct
from typing import Any

from .params import decode_bool_param


SPLIT = (0x0495, 0x09)
BRANCH_SEQUENCE = (0x002D, 0x09)
IF_ELSE = (0x00FF, 0x0B)
WHILE = (0x0501, 0x0A)


def decode_split_action_refs(payload: bytes) -> list[int]:
    """Decode the exact current-build ``Split.actions`` local-id list."""
    if len(payload) < 4:
        return []
    count = struct.unpack_from("<I", payload, 0)[0]
    if count > 64 or len(payload) != 4 + count * 4:
        return []
    refs = [
        struct.unpack_from("<i", payload, 4 + index * 4)[0]
        for index in range(count)
    ]
    if any(ref < 0 or ref > 0x10000 for ref in refs):
        return []
    return refs


def decode_branch_sequence_action_refs(payload: bytes) -> list[int]:
    """Decode the ordered ``Branch._idList`` continuation sequence."""
    refs = decode_split_action_refs(payload)
    if any(ref <= 0 for ref in refs):
        return []
    return refs


def decode_if_else_action_refs(payload: bytes) -> dict[str, Any]:
    """Decode exact ``IfElseAction`` condition and true/false action ids."""
    if len(payload) < 8:
        return {}
    false_id, true_id = struct.unpack_from("<ii", payload, len(payload) - 8)
    if any(ref < 0 or ref > 0x10000 for ref in (true_id, false_id)):
        return {}
    out = {
        "trueActionLocalId": true_id,
        "falseActionLocalId": false_id,
    }
    condition = payload[:-8]
    if (
        len(condition) == 14
        and condition[:2] == b"\x04\x01"
        and condition[6:] == b"\xff" * 8
    ):
        getter_id = struct.unpack_from("<i", condition, 2)[0]
        if 0 <= getter_id <= 0x10000:
            out["conditionGetterLocalId"] = getter_id
    else:
        inline_condition = decode_bool_param(condition, 0)
        if inline_condition is not None and inline_condition[1] == len(condition):
            out["conditionParam"] = inline_condition[0]
    return out


def decode_while_action(payload: bytes) -> dict[str, Any]:
    """Decode exact ``WhileAction`` condition and loop-body action id."""
    condition = decode_bool_param(payload, 0)
    condition_action_local_id: int | None = None
    if condition is not None:
        condition_detail, cursor = condition
    elif (
        len(payload) >= 14
        and payload[0] == 0x04
        and payload[1] in (0, 1)
        and payload[6:14] == b"\xff" * 8
    ):
        condition_action_local_id = struct.unpack_from("<i", payload, 2)[0]
        if condition_action_local_id <= 0 or condition_action_local_id > 0x10000:
            return {}
        condition_detail = {
            "value": bool(payload[1]),
            "idRef": condition_action_local_id,
            "paramSource": -1,
            "path": None,
        }
        cursor = 14
    else:
        return {}
    if cursor + 4 != len(payload):
        return {}
    do_action_local_id = struct.unpack_from("<i", payload, cursor)[0]
    if do_action_local_id <= 0 or do_action_local_id > 0x10000:
        return {}
    out = {
        "whileConditionParam": condition_detail,
        "whileDoActionLocalId": do_action_local_id,
    }
    if condition_action_local_id is not None:
        out["whileConditionActionLocalId"] = condition_action_local_id
    return out


def decode_control_flow_action(
    payload: bytes,
    semantic_key: tuple[int, int],
) -> dict[str, Any]:
    """Decode and label one exact local control-flow action schema."""
    if semantic_key == SPLIT:
        refs = decode_split_action_refs(payload)
        if not refs:
            return {}
        return {
            "splitActionLocalIds": refs,
            "branchLocalRefs": refs,
            "branchRole": "typed-split-action-list",
        }
    if semantic_key == BRANCH_SEQUENCE:
        refs = decode_branch_sequence_action_refs(payload)
        if not refs:
            return {}
        return {
            "branchSequenceActionLocalIds": refs,
            "sequenceLocalRefs": refs,
            "sequenceRole": "typed-branch-ordered-action-list",
        }
    if semantic_key == IF_ELSE:
        detail = decode_if_else_action_refs(payload)
        if not detail:
            return {}
        return {
            **detail,
            "branchLocalRefs": list(dict.fromkeys(
                ref
                for field in ("trueActionLocalId", "falseActionLocalId")
                for ref in [detail.get(field)]
                if isinstance(ref, int)
            )),
            "branchRole": "typed-if-else-actions",
        }
    if semantic_key == WHILE:
        detail = decode_while_action(payload)
        if not detail:
            return {}
        return {
            **detail,
            "branchLocalRefs": [detail["whileDoActionLocalId"]],
            "branchRole": "typed-while-action-body",
        }
    return {}
