"""Current-build SkillData GetPatrolTeleportPos action 0x00C2 framing.

The reviewed Buff frontier-eight route pins the six ordered source reads.
This finite adapter consumes stored bytes without inferring teleport behavior.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "skillTimelineGetPatrolTeleportPos"
TAG = 0x00C2
SOURCE_CONTRACT = "buff_frontier8.json"
SOURCE_SCHEMA = "endfield.buff-frontier8-native-contract.v1"
TYPE_NAME = "Beyond.Gameplay.Core.GetPatrolTeleportPos+Data"
READ_ORDER = ("byte", "scalar32", "scalar32", "scalar32", "string", "float32")


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
        or tuple(matches[0].get("generatedOwnFields", ()))
        != ("teleportDis", "saveTo")
        or matches[0].get("nestedContextUsage") != []
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return matches[0]


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the already reviewed frontier-eight route on this build."""
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


def decode_get_patrol_teleport_pos_action(
    reader: Reader, depth: int, tag: int, width: int,
) -> None:
    """Consume one exact six-member selected action."""
    del depth
    _route()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_ORDER))
    reader.take(1, "GetPatrolTeleportPos.anonymous-byte")
    for _ in range(3):
        reader.take(4, "GetPatrolTeleportPos.anonymous-scalar32")
    reader.byte_payload()
    reader.take(4, "GetPatrolTeleportPos.float32-bits")
