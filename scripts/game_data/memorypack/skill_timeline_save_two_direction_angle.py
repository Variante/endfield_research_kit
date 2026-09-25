"""Current-build SkillData SaveTwoDirectionAngle action 0x0141 framing.

The Buff frontier-nine contract authenticates the physical union route,
ordered source reads, and four nested TargetSettings contexts.  SkillData
admits that route through this finite reader, without assigning gameplay
meaning to anonymous stored values.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "skillTimelineSaveTwoDirectionAngle"
TAG = 0x0141
SOURCE_CONTRACT = "buff_frontier9.json"
SOURCE_SCHEMA = "endfield.buff-frontier9-native-contract.v1"
TYPE_NAME = "Beyond.Gameplay.Core.SaveTwoDirectionAngle+Data"
READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "enum32",
    "target-settings", "target-settings", "enum32",
    "target-settings", "target-settings", "string",
)
NESTED_TYPE = "Beyond.Gameplay.Core.TargetSettings"


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
        != (NESTED_TYPE,) * 4
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return matches[0]


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected frontier-nine route against native inputs."""
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


def decode_save_two_direction_angle_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume the exact eleven-member 0x0141 route with bounded children."""
    del depth
    _route()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_ORDER))
    reader.take(1, "SaveTwoDirectionAngle.anonymous-byte")
    for _ in range(3):
        reader.take(4, "SaveTwoDirectionAngle.anonymous-scalar32")
    reader.take(4, "SaveTwoDirectionAngle.anonymous-enum32")
    reader.target_profile()
    reader.target_profile()
    reader.take(4, "SaveTwoDirectionAngle.anonymous-enum32")
    reader.target_profile()
    reader.target_profile()
    reader.byte_payload()
