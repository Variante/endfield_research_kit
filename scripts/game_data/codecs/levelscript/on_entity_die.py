"""Selected stored ActionHeader cursor for OnEntityDie."""

from __future__ import annotations

from typing import Any
from scripts.game_data.memorypack.core import memorypack_union_header

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.EntityEvent.OnEntityDie"
_FIELDS = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["filterLevel", "int32"],
    ["filterMask", "int32"], ["filterMode", "bool"],
    ["nextID", "int32"], ["priority", "int32"],
    ["triggerActiveDuring", "int32"], ["validate", "Param<bool>"],
    ["targetEntity", "Param<EntityPtr>"],
    ["targetEntityList", "Param<List<EntityPtr>>"],
    ["targetEntityListOutput", "ParamOutput<EntityPtr>"],
    ["triggerTarget", "int32"],
]


def decode_on_entity_die_header(
    data: bytes, offset: int, route: dict[str, Any], *, game_root=None, strings: Any=None,
) -> tuple[dict[str, Any], int]:
    """Read one authenticated event header and its exact member order."""
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or type(route.get("tag")) is not int or not 0 <= route["tag"] <= 0xFFFF
        or route.get("serializedMemberCount") != 18
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("onEntityDie:invalid-route")
    header = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(header)] != header:
        raise ActionMapCodecError(f"onEntityDie:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + len(header), game_root=game_root, strings=strings)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in _FIELDS:
        start = cursor.offset
        values[name] = cursor.node_string(f"onEntityDie.{name}",{**route,"nativeGate":"levelscript_on_entity_die_native"},name) if kind=="string" else cursor.value(kind,f"onEntityDie.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset,
        "endOffset": cursor.offset,
        "unionTag": route["tag"],
        "memberCount": 18,
        "wrapperName": route["wrapperName"],
        "fields": values,
        "fieldSpans": spans,
    }, cursor.offset
