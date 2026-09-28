"""Read the selected chained CheckInteractiveSubmitSuccess stored payload."""

from __future__ import annotations

from typing import Any

from scripts.game_data.codecs.levelscript.condition_params import _decode_string_param
from scripts.game_data.codecs.levelscript.framing_common import _offset_hex
from scripts.game_data.codecs.levelscript.params import decode_bool_param, decode_constant_entity_ptr_param
from scripts.game_data.codecs.levelscript.task_conditions import (
    _decode_task_condition_common, _decode_task_condition_union_header,
)
from scripts.game_data.levelscript_taskmap_submit_native import SCHEMA, validated_taskmap_submit_route


_PARAM_READERS = {
    "Param<EntityPtr>": decode_constant_entity_ptr_param,
    "Param<bool>": decode_bool_param,
    "Param<string>": _decode_string_param,
}


def decode_taskmap_submit_condition(
    data: bytes, offset: int, limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Return one exact selected payload, or no route after native/source drift."""
    if not 0 <= offset < limit <= len(data):
        return None
    header = _decode_task_condition_union_header(data,offset,limit)
    if header is None:
        return None
    tag,count,encoding,cursor = header
    route = validated_taskmap_submit_route()
    if route is None or (tag,count) != (route["tag"],route["serializedMemberCount"]):
        return None
    common = _decode_task_condition_common(data,cursor,limit)
    if common is None:
        return None
    base_fields,cursor = common
    values: dict[str,Any] = {}
    for name,kind in route["fields"][4:]:
        decoder = _PARAM_READERS.get(kind)
        if decoder is None:
            return None
        decoded = decoder(data,cursor)
        if decoded is None or decoded[1] > limit:
            return None
        values[name],cursor = decoded
    return {
        "type": route["typeName"].removeprefix("Beyond.Gameplay."),
        "conditionUnionTag": f"0x{tag:04x}",
        "conditionUnionTagEncoding": encoding,
        "serializedMemberCount": count,
        "conditionOffset": offset,
        "conditionOffsetHex": _offset_hex(offset),
        "conditionEndOffset": cursor,
        "conditionEndOffsetHex": _offset_hex(cursor),
        **base_fields, **values,
        "nativeMappingId": SCHEMA,
    },cursor
