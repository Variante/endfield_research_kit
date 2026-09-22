"""Sequential prefix codec for the current 27-member ``LevelScriptData``.

The generated current wrapper fixes the member order.  This codec is narrow:
it starts immediately after a proved complete empty ``ActionMapAssetRaw`` and
advances through primitive members and null/empty collections only.  A positive
collection whose element codec is not owned here is returned as a named stop;
no later byte is scanned to guess its extent.
"""

from __future__ import annotations

import math
import struct
from typing import Any

from scripts.game_data.codecs.levelscript import (
    active_shapes,
    enemies,
    interactive_locks,
    interactives,
    modules,
)


class LevelScriptPrefixCodecError(ValueError):
    """Raised when the current wrapper grammar cannot advance exactly."""


END_TYPE_NAMES = {
    -1: "Auto",
    0: "ByExitStartShape",
    1: "Manual",
    2: "SameWithDeactive",
    3: "Never",
}

LEVEL_SCRIPT_TYPE_NAMES = {
    0: "World",
    1: "Mission",
    2: "Game",
    3: "Master",
    4: "SubLevelScript",
    5: "ControlledGame",
}

RESET_MODE_NAMES = {
    0: "None",
    1: "ResetAll",
    2: "ResetWithoutProperties",
    3: "ResetAllWhenNotDone",
}


def _require(data: bytes, cursor: int, size: int, field: str) -> None:
    if cursor < 0 or size < 0 or cursor + size > len(data):
        raise LevelScriptPrefixCodecError(
            f"truncated {field}: offset={cursor} size={size} length={len(data)}"
        )


def _i32(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    _require(data, cursor, 4, field)
    return struct.unpack_from("<i", data, cursor)[0], cursor + 4


def _u64(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    _require(data, cursor, 8, field)
    return struct.unpack_from("<Q", data, cursor)[0], cursor + 8


def _f32(data: bytes, cursor: int, field: str) -> tuple[float, int]:
    _require(data, cursor, 4, field)
    value = struct.unpack_from("<f", data, cursor)[0]
    if not math.isfinite(value):
        raise LevelScriptPrefixCodecError(
            f"non-finite {field}: offset={cursor} value={value!r}"
        )
    return value, cursor + 4


def _bool(data: bytes, cursor: int, field: str) -> tuple[bool, int]:
    _require(data, cursor, 1, field)
    raw = data[cursor]
    if raw not in (0, 1):
        raise LevelScriptPrefixCodecError(
            f"invalid bool {field}: offset={cursor} value={raw}"
        )
    return bool(raw), cursor + 1


def _string(data: bytes, cursor: int, field: str) -> tuple[str | None, int]:
    length, cursor = _i32(data, cursor, f"{field}.length")
    if length == -1:
        return None, cursor
    if length < 0:
        raise LevelScriptPrefixCodecError(
            f"invalid string length {field}: offset={cursor - 4} length={length}"
        )
    _require(data, cursor, length, field)
    raw = data[cursor : cursor + length]
    try:
        return raw.decode("utf-8"), cursor + length
    except UnicodeDecodeError as error:
        raise LevelScriptPrefixCodecError(
            f"invalid UTF-8 {field}: offset={cursor} length={length}"
        ) from error


def _empty_collection(
    data: bytes,
    cursor: int,
    field: str,
) -> tuple[dict[str, Any], int | None]:
    start = cursor
    count, cursor = _i32(data, cursor, f"{field}.count")
    if count == -1:
        return {
            "startOffset": start,
            "endOffset": cursor,
            "status": "null",
            "count": None,
        }, cursor
    if count == 0:
        return {
            "startOffset": start,
            "endOffset": cursor,
            "status": "present",
            "count": 0,
        }, cursor
    if count < -1:
        raise LevelScriptPrefixCodecError(
            f"invalid collection count {field}: offset={start} count={count}"
        )
    return {
        "startOffset": start,
        "endOffset": start,
        "status": "unsupported-positive",
        "count": count,
    }, None


def decode_empty_action_map_owner_prefix(
    data: bytes,
    offset: int = 20,
) -> dict[str, Any]:
    """Decode members 2..22 after a complete empty action-map asset.

    ``endOffset`` is always the next unread byte.  When ``stopField`` is set,
    its collection count has been validated but is deliberately not consumed,
    because this codec does not own that collection's element grammar.
    """
    cursor = offset
    fields: dict[str, Any] = {}
    ranges: dict[str, dict[str, Any]] = {}

    shape_start = cursor
    shape_list, shape_end = active_shapes.decode_shape_list(data, cursor)
    if (
        shape_end is None
        or shape_list.get("status") not in {"null", "present"}
        or (
            shape_list.get("status") == "present"
            and int(shape_list.get("count") or 0) > 0
            and (
                shape_list.get("parseStatus") != "decoded"
                or not all(
                    active_shapes._valid_active_shape(row)
                    for row in shape_list.get("shapes") or []
                )
            )
        )
    ):
        raise LevelScriptPrefixCodecError(
            f"invalid activeShapeList at offset={cursor}"
        )
    cursor = shape_end
    fields["activeShapeList"] = shape_list
    ranges["activeShapeList"] = {"startOffset": shape_start, "endOffset": cursor}

    for name in ("allowStartOnTravelPole", "allowTick", "enablePreload"):
        start = cursor
        fields[name], cursor = _bool(data, cursor, name)
        ranges[name] = {"startOffset": start, "endOffset": cursor}

    start = cursor
    end_type, cursor = _i32(data, cursor, "endType")
    if end_type not in END_TYPE_NAMES:
        raise LevelScriptPrefixCodecError(
            f"invalid endType: offset={start} value={end_type}"
        )
    fields["endType"] = {"raw": end_type, "name": END_TYPE_NAMES[end_type]}
    ranges["endType"] = {"startOffset": start, "endOffset": cursor}

    start = cursor
    try:
        enemy_rows, cursor = enemies.decode_enemy_dictionary(data, cursor)
    except enemies.LevelEnemyCodecError as error:
        raise LevelScriptPrefixCodecError(str(error)) from error
    if enemy_rows is None:
        count, _ = _i32(data, start, "enemies.count")
        return {
            "startOffset": offset,
            "endOffset": start,
            "fields": fields,
            "ranges": ranges,
            "stopField": "enemies",
            "stopDetail": {
                "startOffset": start,
                "endOffset": start,
                "status": "unsupported-positive",
                "count": count,
            },
        }
    fields["enemies"] = enemy_rows
    ranges["enemies"] = {"startOffset": start, "endOffset": cursor}

    start = cursor
    fields["exitBuffer"], cursor = _f32(data, cursor, "exitBuffer")
    ranges["exitBuffer"] = {"startOffset": start, "endOffset": cursor}
    start = cursor
    fields["exitBufferOverride"], cursor = _bool(
        data, cursor, "exitBufferOverride"
    )
    ranges["exitBufferOverride"] = {"startOffset": start, "endOffset": cursor}

    start = cursor
    try:
        lock_rows, cursor = interactive_locks.decode_interactive_lock_dictionary(
            data, cursor
        )
    except interactive_locks.InteractiveLockCodecError as error:
        raise LevelScriptPrefixCodecError(str(error)) from error
    if lock_rows is None:
        count, _ = _i32(data, start, "interactiveLocks.count")
        return {
            "startOffset": offset,
            "endOffset": start,
            "fields": fields,
            "ranges": ranges,
            "stopField": "interactiveLocks",
            "stopDetail": {
                "startOffset": start,
                "endOffset": start,
                "status": "unsupported-positive",
                "count": count,
            },
        }
    fields["interactiveLocks"] = lock_rows
    ranges["interactiveLocks"] = {"startOffset": start, "endOffset": cursor}

    start = cursor
    try:
        interactive_rows, cursor = interactives.decode_interactive_dictionary(
            data, cursor
        )
    except interactives.LevelInteractiveCodecError as error:
        raise LevelScriptPrefixCodecError(str(error)) from error
    fields["interactives"] = interactive_rows
    ranges["interactives"] = {"startOffset": start, "endOffset": cursor}

    start = cursor
    script_type, cursor = _i32(data, cursor, "levelScriptType")
    if script_type not in LEVEL_SCRIPT_TYPE_NAMES:
        raise LevelScriptPrefixCodecError(
            f"invalid levelScriptType: offset={start} value={script_type}"
        )
    fields["levelScriptType"] = {
        "raw": script_type,
        "name": LEVEL_SCRIPT_TYPE_NAMES[script_type],
    }
    ranges["levelScriptType"] = {"startOffset": start, "endOffset": cursor}

    start = cursor
    fields["lstTemplatePath"], cursor = _string(data, cursor, "lstTemplatePath")
    ranges["lstTemplatePath"] = {"startOffset": start, "endOffset": cursor}
    start = cursor
    fields["maxStage"], cursor = _i32(data, cursor, "maxStage")
    ranges["maxStage"] = {"startOffset": start, "endOffset": cursor}

    start = cursor
    try:
        module_rows, module_end = modules.decode_module_dictionary(data, cursor)
    except modules.LevelScriptModuleCodecError as error:
        raise LevelScriptPrefixCodecError(str(error)) from error
    if module_rows is None:
        count, _ = _i32(data, cursor, "modules.count")
        return {
            "startOffset": offset,
            "endOffset": cursor,
            "fields": fields,
            "ranges": ranges,
            "stopField": "modules",
            "stopDetail": {
                "startOffset": cursor,
                "endOffset": cursor,
                "status": "unsupported-positive",
                "count": count,
            },
        }
    fields["modules"] = module_rows
    ranges["modules"] = {"startOffset": start, "endOffset": module_end}
    cursor = module_end

    for name in ("npcs",):
        collection, next_cursor = _empty_collection(data, cursor, name)
        if next_cursor is None:
            return {
                "startOffset": offset,
                "endOffset": cursor,
                "fields": fields,
                "ranges": ranges,
                "stopField": name,
                "stopDetail": collection,
            }
        fields[name] = collection
        ranges[name] = {"startOffset": cursor, "endOffset": next_cursor}
        cursor = next_cursor

    start = cursor
    fields["parentLevelScriptId"], cursor = _u64(
        data, cursor, "parentLevelScriptId"
    )
    ranges["parentLevelScriptId"] = {"startOffset": start, "endOffset": cursor}

    for name in ("properties", "propertyIdToKeyMap", "refWorldEntityIdList"):
        collection, next_cursor = _empty_collection(data, cursor, name)
        if next_cursor is None:
            return {
                "startOffset": offset,
                "endOffset": cursor,
                "fields": fields,
                "ranges": ranges,
                "stopField": name,
                "stopDetail": collection,
            }
        fields[name] = collection
        ranges[name] = {"startOffset": cursor, "endOffset": next_cursor}
        cursor = next_cursor

    for name in ("resetModeWhenActive", "resetModeWhenEnd"):
        start = cursor
        raw, cursor = _i32(data, cursor, name)
        if raw not in RESET_MODE_NAMES:
            raise LevelScriptPrefixCodecError(
                f"invalid {name}: offset={start} value={raw}"
            )
        fields[name] = {"raw": raw, "name": RESET_MODE_NAMES[raw]}
        ranges[name] = {"startOffset": start, "endOffset": cursor}

    return {
        "startOffset": offset,
        "endOffset": cursor,
        "fields": fields,
        "ranges": ranges,
        "stopField": None,
    }
