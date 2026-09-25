"""Selected-build named wrapper receipt for BuffData CreateBuff actions.

The Buff corpus frames ``abilityEventAction`` without assigning names to its
interior.  This adapter reuses the independently reviewed SkillData member-19
reader for physical tag ``0x0092``.  Its receipt names the wrapper fields and
checks the exact action span, but keeps nested provider and whole-BuffData
ownership separate.
"""
from __future__ import annotations

import hashlib
from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.skill_timeline_create_buff import (
    _contract as _create_buff_contract,
    _decode_create_buff_action,
    validate_current_native_contract,
)


TAG = 0x0092
SCHEMA = "endfield.buff-create-buff-action-receipt.v1"
_INHERITED_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
)


def decode_create_buff_action_receipt(
    data: bytes,
    *,
    source: str,
    logical_sha256: str,
    start: int,
    end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name one framed action after a VFS hash join and selected native gate.

    ``logical_sha256`` must come from the verified VFS identity for ``source``;
    the adapter checks that these are the exact logical bytes before reading.
    The caller should run ``validate_current_native_contract`` once per batch
    and pass its result for every reached physical ``0x0092`` action.
    """
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("unionTag") != TAG
        or native_validation.get("nativeInputs")
        != _create_buff_contract()["nativeInputs"]
    ):
        raise ValueError("buffCreateBuffActionReceipt:native-not-validated")
    if (
        not isinstance(logical_sha256, str)
        or len(logical_sha256) != 64
        or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
    ):
        raise ValueError("buffCreateBuffActionReceipt:logical-sha256-mismatch")
    if not source or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError("buffCreateBuffActionReceipt:invalid-action-range")

    reader = Reader(data, source, end)
    reader.pos = start
    ranges: list[dict[str, Any]] = []
    action = _decode_create_buff_action(reader, ranges)
    if action["end"] != end:
        raise ValueError(
            f"buffCreateBuffActionReceipt:action-end={action['end']}; expected={end}"
        )
    fields = action["fields"]
    direct_names = tuple(
        row[1].removeprefix("set___").removesuffix("__")
        for row in _create_buff_contract()["wrapper"]["setterMethods"]
    )
    if (
        len(fields) != 19
        or tuple(field["fieldName"] for field in fields)
        != _INHERITED_NAMES + direct_names
        or fields[0]["start"] != start + 2
        or fields[-1]["end"] != end
        or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))
    ):
        raise ValueError("buffCreateBuffActionReceipt:field-order-or-range-drift")
    return {
        "schema": SCHEMA,
        "source": source,
        "logicalSha256": logical_sha256.upper(),
        "status": "named-wrapper-exact-span",
        "tag": TAG,
        "typeName": action["typeName"],
        "memberCount": 19,
        "start": start,
        "end": end,
        "namedFields": fields,
        "wholeActionByteSpanExact": True,
        "recursiveNamedSchemaExact": False,
        "wholeBuffDataExact": False,
        "nestedStructuralFields": [
            "buffIconDurationSource", "buffs", "count", "targetSettings"
        ],
        "evidenceBoundary": (
            "The selected native dispatcher and generated setter order name the "
            "19 CreateBuff wrapper fields, and the authenticated logical bytes "
            "close this one physical action span. Nested providers and values "
            "remain structural only; other action unions and the enclosing "
            "BuffData schema are not promoted."
        ),
    }
