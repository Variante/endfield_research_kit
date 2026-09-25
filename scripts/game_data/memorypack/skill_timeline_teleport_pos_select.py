"""Current-build SkillData TeleportPosSelectAction 0x017D framing.

The Buff frontier-nine contract already authenticates this union route and its
ordered source reads.  Keep the Skill-only admission separate so an unsupported
Skill action still stops at its first byte.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "skillTimelineTeleportPosSelect"
TAG = 0x017D
SOURCE_CONTRACT = "buff_frontier9.json"
SOURCE_SCHEMA = "endfield.buff-frontier9-native-contract.v1"
TYPE_NAME = "Beyond.Gameplay.Core.TeleportPosSelectAction+Data"
READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "string",
    "teleport-fix-distance-data", "teleport-ranged-data",
    "target-settings", "enum32",
)
NESTED_TYPES = (
    "Beyond.Gameplay.Core.TeleportPosSelectAction+FixDistanceData",
    "Beyond.Gameplay.Core.TeleportPosSelectAction+RangedData",
    "Beyond.Gameplay.Core.TargetSettings",
)


def _route() -> dict[str, Any]:
    source = buff_frontiers_native.reviewed_contract("frontier9")
    matches = [row for row in source["actions"] if row.get("unionTag") == TAG]
    if (
        source.get("schema") != SOURCE_SCHEMA
        or len(matches) != 1
        or matches[0].get("actualTypeName") != TYPE_NAME
        or matches[0].get("serializedMemberCount") != len(READ_ORDER)
        or tuple(matches[0].get("readOrder", ())) != READ_ORDER
        or tuple(context.get("typeName") for context in matches[0].get("nestedContextUsage", ()))
        != NESTED_TYPES
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return matches[0]


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the existing frontier-nine route against selected binaries."""
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


def _fix_distance(reader: Reader) -> None:
    if reader.peek() == 0xFF:
        reader.take(1, "TeleportPosSelectAction.null-fix-distance")
        return
    reader.header(3)
    reader.scalar_payload()
    reader.take(1, "TeleportPosSelectAction.fix-distance.bool-byte")
    reader.take(1, "TeleportPosSelectAction.fix-distance.bool-byte")


def _ranged(reader: Reader) -> None:
    if reader.peek() == 0xFF:
        reader.take(1, "TeleportPosSelectAction.null-ranged")
        return
    reader.header(1)
    reader.scalar_payload()


def decode_teleport_pos_select_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one exact nine-member route, retaining nested parser stops."""
    del depth
    _route()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_ORDER))
    reader.take(1, "TeleportPosSelectAction.isEnable.bool-byte")
    for _ in range(3):
        reader.take(4, "TeleportPosSelectAction.scalar32")
    reader.byte_payload()
    _fix_distance(reader)
    _ranged(reader)
    reader.target_profile()
    reader.take(4, "TeleportPosSelectAction.teleportType.enum32")
