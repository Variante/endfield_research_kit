"""Shared bounded node helpers; positive maps use the reviewed sequential reader."""

from __future__ import annotations

import struct

from scripts.game_data import levelscript_union_tags as union_tags
from scripts.game_data.codecs.levelscript.framing_common import LevelScriptTopLevelFramingError
from scripts.game_data.codecs.levelscript.primitives import i32 as _i32
from scripts.game_data.codecs.levelscript.primitives import u32 as _u32
from typing import Any

# The record types these lanes select, with the member count each reads.
_LEADER_ENTER_HEADER = ("ActionHeader", "ScriptEvent_OnLeaderEnterTriggerVolume", 0x12)


def _leader_enter_header_route() -> tuple[int, int]:
    """The current plain ``(tag, member count)`` of the leader-enter header.

    Raises the framing error when no route resolves, so a caller with a
    reviewed fallback can take it.
    """
    route = union_tags.plain_route(*_LEADER_ENTER_HEADER)
    if route is None:
        raise LevelScriptTopLevelFramingError(
            "ScriptEvent_OnLeaderEnterTriggerVolume has no current plain-tag route"
            f"{union_tags.unavailable_note()}"
        )
    return route


def _read_anonymous_nullable_utf8(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    start = cursor
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated anonymous UTF-8 length at offset={cursor}"
        )
    length = struct.unpack_from("<i", data, cursor)[0]
    cursor += 4
    if length == -1:
        return {"startOffset": start, "endOffset": cursor, "value": None}, cursor
    if length < 0 or length > len(data) - cursor:
        raise LevelScriptTopLevelFramingError(
            "invalid anonymous UTF-8 length: "
            f"offset={start} length={length} remaining={len(data) - cursor}"
        )
    raw = data[cursor : cursor + length]
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LevelScriptTopLevelFramingError(
            f"invalid anonymous UTF-8 payload at offset={cursor} length={length}"
        ) from error
    cursor += length
    return {
        "startOffset": start,
        "endOffset": cursor,
        "value": value,
    }, cursor


def _read_anonymous_i32_string_collection(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    start = cursor
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated anonymous collection count at offset={cursor}"
        )
    count = struct.unpack_from("<i", data, cursor)[0]
    cursor += 4
    if count == -1:
        return {
            "startOffset": start,
            "endOffset": cursor,
            "rawCount": count,
            "values": None,
        }, cursor
    if count < 0 or count > (len(data) - cursor) // 4:
        raise LevelScriptTopLevelFramingError(
            "invalid anonymous collection count: "
            f"offset={start} count={count} remaining={len(data) - cursor}"
        )
    values = []
    for _ in range(count):
        value, cursor = _read_anonymous_nullable_utf8(data, cursor)
        values.append(value["value"])
    return {
        "startOffset": start,
        "endOffset": cursor,
        "rawCount": count,
        "values": values,
    }, cursor


def _read_anonymous_param_tail(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    start = cursor
    if cursor + 8 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated anonymous fixed-width tail at offset={cursor}"
        )
    raw_i32 = list(struct.unpack_from("<ii", data, cursor))
    cursor += 8
    trailing, cursor = _read_anonymous_nullable_utf8(data, cursor)
    return {
        "startOffset": start,
        "endOffset": cursor,
        "rawI32": raw_i32,
        "trailingNullableUtf8": trailing["value"],
    }, cursor


def _read_nullable_levelscript_param(
    data: bytes,
    cursor: int,
    decoder: Any,
    label: str,
) -> tuple[dict[str, Any], int]:
    """Read a nullable generated ``Param`` member without guessing its end."""
    if cursor >= len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated {label} at offset={cursor}"
        )
    if data[cursor] == 0xFF:
        return {"value": None, "startOffset": cursor, "endOffset": cursor + 1}, cursor + 1
    decoded = decoder(data, cursor)
    if decoded is None:
        raise LevelScriptTopLevelFramingError(
            f"unsupported {label} encoding at offset={cursor}"
        )
    value, end = decoded
    return {
        "value": value,
        "startOffset": cursor,
        "endOffset": end,
    }, end


def _read_levelscript_node_envelope(
    data: bytes,
    cursor: int,
    *,
    union_tag: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    """Read the seven generated ``NodeBase`` fields of a plain-tag record."""
    start = cursor
    if cursor + 26 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated NodeBase envelope at offset={cursor}"
        )
    if data[cursor] != union_tag or data[cursor + 1] != member_count:
        raise LevelScriptTopLevelFramingError(
            "polymorphic record mismatch: "
            f"expected={union_tag:02x} {member_count:02x} "
            f"actual={data[cursor:cursor + 2].hex(' ')}"
        )
    dont_log = data[cursor + 2]
    release = data[cursor + 7]
    use_current = data[cursor + 24]
    use_graph = data[cursor + 25]
    if any(value not in (0, 1) for value in (dont_log, release, use_current, use_graph)):
        raise LevelScriptTopLevelFramingError(
            f"invalid NodeBase boolean at offset={cursor}"
        )
    uid_size = _u32(data, cursor + 8)
    if uid_size != 8:
        raise LevelScriptTopLevelFramingError(
            f"NodeBase uid length mismatch at offset={cursor + 8}: actual={uid_size}"
        )
    raw_uid = data[cursor + 12 : cursor + 20]
    if not all(
        ord("0") <= value <= ord("9") or ord("a") <= value <= ord("f")
        for value in raw_uid
    ):
        raise LevelScriptTopLevelFramingError(
            f"invalid NodeBase uid at offset={cursor + 12}"
        )
    end = cursor + 26
    return {
        "startOffset": start,
        "endOffset": end,
        "unionTag": union_tag,
        "serializedMemberCount": member_count,
        "dontLogWarning": bool(dont_log),
        "id": _u32(data, cursor + 3),
        "releaseWhenExecutionFinished": bool(release),
        "uid": raw_uid.decode("ascii"),
        "scopeMask": _i32(data, cursor + 20),
        "useCurrentScope": bool(use_current),
        "useGraphScope": bool(use_graph),
    }, end
