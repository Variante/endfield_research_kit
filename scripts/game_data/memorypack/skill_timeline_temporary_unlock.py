"""Current-build SkillData TemporaryUnlockAction 0x017E framing.

The reviewed Buff frontier-nine contract pins the eight ordered source reads
and the nested TargetSettings context. This reader consumes only stored bytes.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "skillTimelineTemporaryUnlock"
TAG = 0x017E
SOURCE_CONTRACT = "buff_frontier9.json"
SOURCE_SCHEMA = "endfield.buff-frontier9-native-contract.v1"
TYPE_NAME = "Beyond.Gameplay.Core.TemporaryUnlockAction+Data"
READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "bool", "bool", "float32",
    "target-settings",
)


def _route() -> dict[str, Any]:
    source = buff_frontiers_native.reviewed_contract("frontier9")
    matches = [row for row in source["actions"] if row.get("unionTag") == TAG]
    if (
        source.get("schema") != SOURCE_SCHEMA
        or source.get("status") != "exact-current-build"
        or len(matches) != 1
        or matches[0].get("actualTypeName") != TYPE_NAME
        or matches[0].get("serializedMemberCount") != len(READ_ORDER)
        or tuple(matches[0].get("readOrder", ())) != READ_ORDER
        or tuple(context.get("typeName") for context in matches[0].get("nestedContextUsage", ()))
        != ("Beyond.Gameplay.Core.TargetSettings",)
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return matches[0]


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the frontier-nine route against selected installed binaries."""
    route = _route()
    rows, audit = buff_frontiers_native.load_rows("frontier9")
    if audit.get("status") != "validated" or rows.get(TAG) != route:
        raise ValueError(f"{LABEL}.native:{audit.get('status')}:{audit.get('validationFailures')}")
    return {
        "status": "validated",
        "sourceContract": SOURCE_CONTRACT,
        "sourceSchema": SOURCE_SCHEMA,
        "unionTag": TAG,
        "nativeInputs": buff_frontiers_native.reviewed_contract("frontier9")["nativeInputs"],
    }


def decode_temporary_unlock_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one eight-member action with a bounded TargetSettings child."""
    del depth
    _route()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_ORDER))
    reader.take(1, "TemporaryUnlockAction.anonymous-byte")
    for _ in range(3):
        reader.take(4, "TemporaryUnlockAction.anonymous-scalar32")
    reader.take(1, "TemporaryUnlockAction.bool-byte")
    reader.take(1, "TemporaryUnlockAction.bool-byte")
    reader.take(4, "TemporaryUnlockAction.float32-bits")
    reader.target_profile()
