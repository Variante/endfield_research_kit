"""The nested ``manualValue`` of a ``SendLuaEvent`` action, read from bytes.

The derived declaration cannot describe this one, and the reason is worth
keeping because it is a derivation artifact rather than a schema. A
``SendLuaEvent1`` wrapper exposes two properties, ``set___instance`` and
``set___manualValue__``, and both take ``SendLuaEvent1``. The layout derivation
reads the property's parameter type, so it records ``manualValue`` as being of
the *enclosing* type and the reader then expects the wrapper's nine members
where the wire holds seven.

What is actually written there is the action serialized by its own formatter
rather than by the wrapper, and its members are a different set. Read from the
payload, the shape is::

    memberCount = 7
    int32           _ID              observed 41
    string          _uid             observed "21afb3dd"
    byte            bool
    int32                            observed -1
    byte            bool
    Param<string>   _eventName       observed "ON_RACING_DUNGEON_SELECT_ROOM"
    string          _param1          a JSON-encoded Param descriptor

Two of those names are supported by more than position. ``_eventName`` is the
only ``Param<string>`` the class declares, and its value is a Lua event name.
``_param1`` is declared ``Param<object>``, which MemoryPack cannot serialize
generically, and the bytes hold JSON of the form
``{"paramSource":200,"path":"RoomID"}`` -- a param descriptor written as text.
The two booleans and the second ``int32`` are read at their proven widths and
reported under neutral keys, because the base chain declares more candidate
bools than the wire carries and nothing here says which were dropped.

**The evidence is whole-file framing, not a plausible parse.**
``frame_levelscript_declared_root`` refuses any file whose cursor does not land
on physical EOF, and this layout closes all fifteen files that carry the action,
taking LevelScriptData from 5,006 to 5,021 of 5,030.

``SendLuaEvent2`` declares a second ``Param<object>`` and so should write eight
members. **No file in the corpus contains one**, so that count is a prediction
and not a measurement; it is computed from the declaration and checked, so an
unexpected count fails closed instead of being read as if proven.
"""

from __future__ import annotations

import struct
from typing import Any, Callable

from . import params


#: Members every SendLuaEvent nested value writes before its Param fields.
FIXED_MEMBER_COUNT = 6

#: The action classes whose nested value this module owns.
SEND_LUA_EVENT_TYPES = ("SendLuaEvent1", "SendLuaEvent2")

#: MemoryPack writes a present Param behind this member-count marker.
PARAM_MARKER = 0x04


class SendLuaEventDecodeError(ValueError):
    """The nested value does not match the proven wire shape."""


def is_send_lua_event(name: str) -> bool:
    return name in SEND_LUA_EVENT_TYPES


def json_param_count(declared: dict[str, Any]) -> int:
    """How many ``Param<object>`` members the class declares.

    Derived rather than hard-coded, so ``SendLuaEvent2`` is handled by the
    same rule that ``SendLuaEvent1`` was measured against instead of by a
    second special case.
    """

    fields = declared.get("fields") or []
    declared_params = sum(1 for _, kind in fields if kind == "Param<object>")
    # The derivation records the wrapper's members, not the instance's, so a
    # class whose own Param<object> fields it did not record still reads as
    # the single-param shape that the corpus proves.
    return declared_params or 1


def decode_nested_send_lua_event(
    data: bytes,
    offset: int,
    field: str,
    json_params: int,
) -> tuple[dict[str, Any], int]:
    """Read one nested ``manualValue`` and return it with the new cursor."""

    expected = FIXED_MEMBER_COUNT + json_params
    if offset < 0 or offset >= len(data):
        raise SendLuaEventDecodeError(f"{field}:truncated at {offset}")
    members = data[offset]
    cursor = offset + 1
    if members != expected:
        raise SendLuaEventDecodeError(
            f"{field}:nested-member-count={members},expected={expected}"
        )

    def need(size: int, label: str) -> None:
        if cursor + size > len(data):
            raise SendLuaEventDecodeError(f"{field}.{label}:truncated at {cursor}")

    def read_i32(label: str) -> int:
        nonlocal cursor
        need(4, label)
        value = struct.unpack_from("<i", data, cursor)[0]
        cursor += 4
        return value

    def read_bool(label: str) -> bool:
        nonlocal cursor
        need(1, label)
        value = data[cursor]
        if value not in (0, 1):
            raise SendLuaEventDecodeError(f"{field}.{label}:invalid-bool={value}")
        cursor += 1
        return bool(value)

    def read_string(label: str) -> str | None:
        nonlocal cursor
        size = read_i32(f"{label}.size")
        if size == -1:
            return None
        if size < 0 or cursor + size > len(data):
            raise SendLuaEventDecodeError(f"{field}.{label}:invalid-size={size}")
        raw = data[cursor:cursor + size]
        cursor += size
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SendLuaEventDecodeError(f"{field}.{label}:not-utf8") from exc

    def read_param_string(label: str) -> dict[str, Any]:
        nonlocal cursor
        need(1, label)
        marker = data[cursor]
        if marker != PARAM_MARKER:
            raise SendLuaEventDecodeError(
                f"{field}.{label}:unsupported-member-count={marker}"
            )
        cursor += 1
        value = read_string(label)
        tail = params.decode_param_tail(data, cursor)
        if tail is None:
            raise SendLuaEventDecodeError(f"{field}.{label}:invalid-param-tail")
        detail, cursor = tail
        return {"value": value, **detail}

    value: dict[str, Any] = {
        "ID": read_i32("ID"),
        "uid": read_string("uid"),
        # The base chain declares more bools than the wire carries, so these
        # two keep neutral names rather than being assigned a declared field.
        "flag0": read_bool("flag0"),
        "int1": read_i32("int1"),
        "flag1": read_bool("flag1"),
        "eventName": read_param_string("eventName"),
    }
    for index in range(json_params):
        value[f"param{index + 1}Json"] = read_string(f"param{index + 1}Json")
    return value, cursor
