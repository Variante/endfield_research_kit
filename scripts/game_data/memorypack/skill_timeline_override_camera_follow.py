"""Selected-build SkillData OverrideCameraFollowAction 0x0104 framing.

The reviewed Buff frontier-nine route authenticates all twelve ordered reads,
including BlackboardDouble and TargetSettings generic contexts. Keep this
Skill-only reader finite; whole-file status is established by the caller.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "skillTimelineOverrideCameraFollow"
TAG = 0x0104
SOURCE_CONTRACT = "buff_frontier9.json"
SOURCE_SCHEMA = "endfield.buff-frontier9-native-contract.v1"
TYPE_NAME = "Beyond.Gameplay.Core.OverrideCameraFollowAction+OverrideCameraFollowActionData"
READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "enum32", "blackboard-double",
    "enum32", "blackboard-double", "blackboard-double", "blackboard-double",
    "target-settings", "target-settings",
)
NESTED_TYPES = (
    "Beyond.Blackboard+BlackboardDouble",
    "Beyond.Blackboard+BlackboardDouble",
    "Beyond.Blackboard+BlackboardDouble",
    "Beyond.Blackboard+BlackboardDouble",
    "Beyond.Gameplay.Core.TargetSettings",
    "Beyond.Gameplay.Core.TargetSettings",
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
        != NESTED_TYPES
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return matches[0]


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the existing frontier-nine route on the installed binaries."""
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


def decode_override_camera_follow_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one twelve-member action using separately bounded profiles."""
    del depth
    _route()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_ORDER))
    reader.take(1, "OverrideCameraFollow.anonymous-byte")
    for _ in range(3):
        reader.take(4, "OverrideCameraFollow.anonymous-scalar32")
    reader.take(4, "OverrideCameraFollow.anonymous-enum32")
    reader.scalar_payload()
    reader.take(4, "OverrideCameraFollow.anonymous-enum32")
    for _ in range(3):
        reader.scalar_payload()
    reader.target_profile()
    reader.target_profile()
