"""Current-build SkillData AddDynamicNavmeshObstacle action 0x0009 framing.

The reviewed Buff frontier-eight contract authenticates the selected union
route, six source reads, and the List<string>/TargetSettings nested contexts.
Keep this Skill-only reader finite and retain the shared TargetSettings stop.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "skillTimelineAddDynamicNavmeshObstacle"
TAG = 0x0009
SOURCE_CONTRACT = "buff_frontier8.json"
SOURCE_SCHEMA = "endfield.buff-frontier8-native-contract.v1"
TYPE_NAME = "Beyond.Gameplay.Core.AddDynamicNavmeshObstacle+Data"
READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "string-list", "target-settings",
)
NESTED_TYPES = (
    "System.Collections.Generic.List`1",
    "Beyond.Gameplay.Core.TargetSettings",
)


def _route() -> dict[str, Any]:
    source = buff_frontiers_native.reviewed_contract("frontier8")
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
    """Authenticate the existing frontier-eight route against selected binaries."""
    route = _route()
    rows, audit = buff_frontiers_native.load_rows("frontier8")
    if audit.get("status") != "validated" or rows.get(TAG) != route:
        raise ValueError(f"{LABEL}.native:{audit.get('status')}:{audit.get('validationFailures')}")
    return {
        "status": "validated",
        "sourceContract": SOURCE_CONTRACT,
        "sourceSchema": SOURCE_SCHEMA,
        "unionTag": TAG,
        "nativeInputs": buff_frontiers_native.reviewed_contract("frontier8")["nativeInputs"],
    }


def decode_add_dynamic_navmesh_obstacle_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one exact six-member action, with bounded child readers."""
    del depth
    _route()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_ORDER))
    reader.take(1, "AddDynamicNavmeshObstacle.anonymous-byte")
    for _ in range(3):
        reader.take(4, "AddDynamicNavmeshObstacle.anonymous-scalar32")
    count = reader.count(4, nullable=True)
    for _ in range(max(0, count)):
        reader.byte_payload()
    reader.target_profile()
