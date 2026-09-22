"""Exact current ``Dictionary<uint, InteractiveLockData>`` codec."""

from __future__ import annotations

from typing import Any

from scripts.game_data.codecs.levelscript import interactives as primitive


class InteractiveLockCodecError(ValueError):
    """Raised when a declared lock value cannot advance exactly."""


_UNLOCK_TYPES = {
    0: "None",
    1: "ScriptLock",
    2: "MiniGame",
    3: "Submit",
    4: "Quest",
    5: "Sludge",
}


def _call(function, data: bytes, cursor: int, field: str):
    try:
        return function(data, cursor, field)
    except primitive.LevelInteractiveCodecError as error:
        raise InteractiveLockCodecError(str(error)) from error


def _count(data: bytes, cursor: int, field: str):
    return _call(primitive._count, data, cursor, field)


def _i32(data: bytes, cursor: int, field: str):
    return _call(primitive._i32, data, cursor, field)


def _u32(data: bytes, cursor: int, field: str):
    return _call(primitive._u32, data, cursor, field)


def _u64(data: bytes, cursor: int, field: str):
    return _call(primitive._u64, data, cursor, field)


def _bool(data: bytes, cursor: int, field: str):
    return _call(primitive._bool, data, cursor, field)


def _string(data: bytes, cursor: int, field: str):
    return _call(primitive._string, data, cursor, field)


def _member(data: bytes, cursor: int, expected: int, field: str) -> int:
    if cursor >= len(data):
        raise InteractiveLockCodecError(f"truncated {field}.memberCount: offset={cursor}")
    actual = data[cursor]
    if actual != expected:
        raise InteractiveLockCodecError(
            f"invalid {field} member count: offset={cursor} value={actual} expected={expected}"
        )
    return cursor + 1


def _lang_key(data: bytes, cursor: int, field: str) -> tuple[Any, int]:
    if cursor >= len(data):
        raise InteractiveLockCodecError(f"truncated {field}: offset={cursor}")
    if data[cursor] == 0xFF:
        return None, cursor + 1
    cursor = _member(data, cursor, 1, field)
    key, cursor = _string(data, cursor, f"{field}.key")
    return {"key": key}, cursor


def _string_list(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    count, cursor = _count(data, cursor, field)
    if count is None:
        return {"status": "null", "count": None, "values": None}, cursor
    values = []
    for index in range(count):
        value, cursor = _string(data, cursor, f"{field}[{index}]")
        values.append(value)
    return {"status": "present", "count": count, "values": values}, cursor


def _single_lock(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    cursor = _member(data, cursor, 18, field)
    value: dict[str, Any] = {}
    value["interactiveId"], cursor = _u64(data, cursor, f"{field}.interactiveId")
    value["miniGameIds"], cursor = _string_list(data, cursor, f"{field}.miniGameIds")
    value["optionUnlock"], cursor = _lang_key(data, cursor, f"{field}.optionUnlock")
    value["overrideViewConfigHash"], cursor = _string(
        data, cursor, f"{field}.overrideViewConfigHash"
    )
    for name in ("panelBtnTxt", "panelDecoTxt", "panelDesc", "panelDescTitle"):
        value[name], cursor = _lang_key(data, cursor, f"{field}.{name}")
    value["panelIconSpritePath"], cursor = _string(
        data, cursor, f"{field}.panelIconSpritePath"
    )
    value["panelTextConfigured"], cursor = _bool(
        data, cursor, f"{field}.panelTextConfigured"
    )
    value["panelTitle"], cursor = _lang_key(data, cursor, f"{field}.panelTitle")
    value["questId"], cursor = _string(data, cursor, f"{field}.questId")
    value["seamlessBlendToPerf"], cursor = _bool(
        data, cursor, f"{field}.seamlessBlendToPerf"
    )
    value["skipSubmitBoard"], cursor = _bool(data, cursor, f"{field}.skipSubmitBoard")
    value["submitId"], cursor = _string(data, cursor, f"{field}.submitId")
    value["toastFailed"], cursor = _lang_key(data, cursor, f"{field}.toastFailed")
    value["toastSuccess"], cursor = _lang_key(data, cursor, f"{field}.toastSuccess")
    raw, cursor = _i32(data, cursor, f"{field}.unlockType")
    if raw not in _UNLOCK_TYPES:
        raise InteractiveLockCodecError(f"invalid {field}.unlockType: value={raw}")
    value["unlockType"] = {"raw": raw, "name": _UNLOCK_TYPES[raw]}
    return value, cursor


def _lock_value(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    cursor = _member(data, cursor, 2, field)
    count, cursor = _count(data, cursor, f"{field}.locks")
    locks = None
    if count is not None:
        locks = []
        for index in range(count):
            value, cursor = _single_lock(data, cursor, f"{field}.locks[{index}]")
            locks.append(value)
    logic_id, cursor = _u64(data, cursor, f"{field}.logicIdGlobal")
    return {"locks": {"count": count, "values": locks}, "logicIdGlobal": logic_id}, cursor


def decode_interactive_lock_dictionary(
    data: bytes, cursor: int
) -> tuple[dict[str, Any] | None, int]:
    """Decode the current lock dictionary and return its exact next cursor."""
    start = cursor
    count, cursor = _count(data, cursor, "interactiveLocks")
    if count is None:
        return {"status": "null", "count": None, "entries": None}, cursor
    if count and (cursor + 5 > len(data) or data[cursor + 4] != 2):
        return None, start
    entries = []
    seen: set[int] = set()
    for index in range(count):
        key, cursor = _u32(data, cursor, f"interactiveLocks[{index}].key")
        if key in seen:
            raise InteractiveLockCodecError(f"duplicate interactiveLocks key: {key}")
        seen.add(key)
        value, cursor = _lock_value(data, cursor, f"interactiveLocks[{key}]")
        entries.append({"key": key, "value": value})
    return {
        "status": "present",
        "count": count,
        "entries": entries,
        "startOffset": start,
        "endOffset": cursor,
    }, cursor


def decode_interactive_lock_list(
    data: bytes, cursor: int
) -> tuple[dict[str, Any] | None, int]:
    """Decode LevelData's direct ``List<InteractiveLockData>`` owner."""
    start = cursor
    count, cursor = _count(data, cursor, "interactiveLockData")
    if count is None:
        return {"status": "null", "count": None, "values": None,
                "startOffset": start, "endOffset": cursor}, cursor
    values: list[dict[str, Any] | None] = []
    lock_count = 0
    for index in range(count):
        if cursor >= len(data):
            raise InteractiveLockCodecError(
                f"truncated interactiveLockData[{index}]: offset={cursor}"
            )
        if data[cursor] == 0xFF:
            values.append(None)
            cursor += 1
            continue
        value, cursor = _lock_value(
            data, cursor, f"interactiveLockData[{index}]"
        )
        values.append(value)
        lock_count += len(value["locks"]["values"] or [])
    return {
        "status": "present",
        "count": count,
        "values": values,
        "lockCount": lock_count,
        "startOffset": start,
        "endOffset": cursor,
        "itemFieldOrder": ["locks", "logicIdGlobal"],
        "fieldOrderSource": "current generated InteractiveLockData wrapper",
    }, cursor
