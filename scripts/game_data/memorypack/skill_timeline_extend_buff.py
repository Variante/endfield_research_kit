"""Current-build SkillData ExtendBuffAction 0x00AF storage framing.

The reviewed frontier-eight route fixes six source reads and the nested
TargetSettings/BuffFindSettings types.  Values remain stored-data evidence;
this reader makes no runtime buff-extension claim.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.buff import read_buff_find_settings_exact
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "skillTimelineExtendBuff"
TAG = 0x00AF
SOURCE_CONTRACT = "buff_frontier8.json"
SOURCE_SCHEMA = "endfield.buff-frontier8-native-contract.v1"
TYPE_NAME = "Beyond.Gameplay.Core.ExtendBuffAction+Data"
READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32",
    "target-settings", "buff-find-settings",
)
NESTED_TYPES = (
    "Beyond.Gameplay.Core.TargetSettings",
    "Beyond.Gameplay.Core.BuffFindSettings",
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
    """Authenticate the selected route against installed native inputs."""
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


def decode_extend_buff_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite six-member action and its bounded children."""
    del depth
    _route()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_ORDER))
    reader.take(1, "ExtendBuffAction.anonymous-byte")
    for _ in range(3):
        reader.take(4, "ExtendBuffAction.anonymous-scalar32")
    reader.target_profile()
    start = reader.pos
    _decoded, end = read_buff_find_settings_exact(
        reader.data, start, reader.limit, "ExtendBuffAction.buffSettings",
    )
    reader.take(end - start, "ExtendBuffAction.BuffFindSettings")
