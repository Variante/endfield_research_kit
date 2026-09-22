"""Fail-closed outer framing for ``NpcAtmosphericDataTable`` payloads."""

from __future__ import annotations

import re
import math
import struct
from typing import Any


ROOT_MEMBER_COUNT = 1
PROXY_MEMBER_COUNT = 118
MAX_ENTRY_COUNT = 100_000
MAX_KEY_BYTES = 512
KEY_RE = re.compile(r"[A-Za-z0-9_]+\Z")
LEVEL_ENTITY_FIELD_ORDER = (
    "aoiRadiusType",
    "belongLevelScriptId",
    "createState",
    "dependencyGroupId",
    "entityDataIdKey",
    "entityType",
    "forceLoad",
    "keepCrossMap",
    "levelLogicId",
    "overrideSendDieEvent",
    "position",
    "rotation",
    "scale",
    "sendDieEvent",
)


class AtmosphericNpcFramingError(ValueError):
    """Raised when the current table envelope cannot be framed uniquely."""


def _read_i32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise AtmosphericNpcFramingError(f"truncated int32 at {offset}")
    return struct.unpack_from("<i", data, offset)[0]


def decode_level_entity_data(data: bytes, start: int, end: int) -> dict[str, Any]:
    """Decode the inherited 14-field ``LevelEntityData`` prefix."""
    cursor = start

    def require(size: int, field: str) -> int:
        nonlocal cursor
        field_start = cursor
        cursor += size
        if size < 0 or cursor > end:
            raise AtmosphericNpcFramingError(
                f"{field}:truncated offset={field_start} need={size} end={end}"
            )
        return field_start

    def i32(field: str) -> int:
        return struct.unpack_from("<i", data, require(4, field))[0]

    def i64(field: str) -> int:
        return struct.unpack_from("<q", data, require(8, field))[0]

    def boolean(field: str) -> bool:
        value = data[require(1, field)]
        if value not in (0, 1):
            raise AtmosphericNpcFramingError(f"{field}:invalid-bool={value}")
        return bool(value)

    def string(field: str) -> str | None:
        length = i32(f"{field}.length")
        if length == -1:
            return None
        if length < 0 or length > MAX_KEY_BYTES:
            raise AtmosphericNpcFramingError(f"{field}:invalid-length={length}")
        value_start = require(length, f"{field}.bytes")
        try:
            return data[value_start:cursor].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AtmosphericNpcFramingError(f"{field}:invalid-utf8") from exc

    def vector3(field: str) -> dict[str, float]:
        values = struct.unpack_from("<fff", data, require(12, field))
        if not all(math.isfinite(value) for value in values):
            raise AtmosphericNpcFramingError(f"{field}:non-finite")
        return {"x": values[0], "y": values[1], "z": values[2]}

    prefix_start = cursor
    fields = {
        "aoiRadiusType": i32("aoiRadiusType"),
        "belongLevelScriptId": i64("belongLevelScriptId"),
        "createState": i32("createState"),
        "dependencyGroupId": i64("dependencyGroupId"),
        "entityDataIdKey": string("entityDataIdKey"),
        "entityType": i32("entityType"),
        "forceLoad": boolean("forceLoad"),
        "keepCrossMap": boolean("keepCrossMap"),
        "levelLogicId": i64("levelLogicId"),
        "overrideSendDieEvent": boolean("overrideSendDieEvent"),
        "position": vector3("position"),
        "rotation": vector3("rotation"),
        "scale": vector3("scale"),
        "sendDieEvent": boolean("sendDieEvent"),
    }
    return {
        "startOffset": prefix_start,
        "endOffset": cursor,
        "fieldOrder": list(LEVEL_ENTITY_FIELD_ORDER),
        "fields": fields,
    }


def frame_atmospheric_npc_table(data: bytes) -> dict[str, Any]:
    """Decode the counted string/proxy dictionary through physical EOF."""
    if not data or data[0] != ROOT_MEMBER_COUNT:
        actual = data[0] if data else None
        raise AtmosphericNpcFramingError(
            f"table member count mismatch: expected={ROOT_MEMBER_COUNT} actual={actual}"
        )
    count = _read_i32(data, 1)
    if count < 0 or count > MAX_ENTRY_COUNT:
        raise AtmosphericNpcFramingError(f"invalid dictionary count {count}")
    if count == 0:
        if len(data) != 5:
            raise AtmosphericNpcFramingError(
                f"empty dictionary has trailing bytes: length={len(data)}"
            )
        return {
            "status": "exact_empty_table",
            "schemaStatus": "exact",
            "serializedMemberCount": ROOT_MEMBER_COUNT,
            "entryCount": 0,
            "bytesConsumed": len(data),
            "entries": [],
            "evidenceBoundary": "The one-member root and empty dictionary count close at physical EOF.",
        }

    anchors: list[dict[str, Any]] = []
    for key_offset in range(5, max(5, len(data) - 5)):
        length = _read_i32(data, key_offset)
        if length <= 0 or length > MAX_KEY_BYTES:
            continue
        key_start = key_offset + 4
        value_offset = key_start + length
        if value_offset >= len(data) or data[value_offset] != PROXY_MEMBER_COUNT:
            continue
        try:
            key = data[key_start:value_offset].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if KEY_RE.fullmatch(key) is None:
            continue
        anchors.append({
            "key": key,
            "keyOffset": key_offset,
            "keyEndOffset": value_offset,
            "valueOffset": value_offset,
        })
    if len(anchors) != count or not anchors or anchors[0]["keyOffset"] != 5:
        raise AtmosphericNpcFramingError(
            "dictionary key/value anchors do not match the declared count: "
            f"declared={count} anchors={len(anchors)} first={anchors[0]['keyOffset'] if anchors else None}"
        )
    keys = [row["key"] for row in anchors]
    if len(set(keys)) != len(keys):
        raise AtmosphericNpcFramingError("dictionary keys are not unique")

    entries: list[dict[str, Any]] = []
    named_rows = 0
    for index, anchor in enumerate(anchors):
        value_end = anchors[index + 1]["keyOffset"] if index + 1 < count else len(data)
        value_offset = int(anchor["valueOffset"])
        if value_end <= value_offset + 1:
            raise AtmosphericNpcFramingError(f"entry {index} has an empty proxy body")
        entry = {
            **anchor,
            "index": index,
            "valueEndOffset": value_end,
            "valueByteLength": value_end - value_offset,
            "proxyMemberCount": data[value_offset],
            "proxyBodyStatus": "opaque_bounded_by_next_entry_or_eof",
        }
        try:
            level_entity = decode_level_entity_data(
                data, value_offset + 1, value_end
            )
        except AtmosphericNpcFramingError as exc:
            entry["levelEntityPrefixDiagnostic"] = str(exc)
        else:
            entry["levelEntityData"] = level_entity
            entry["proxyBodyStatus"] = (
                "named_level_entity_prefix_with_opaque_derived_members"
            )
        try:
            # Lazy import avoids the codec's deliberate reuse of the inherited
            # LevelEntityData primitive from this module at import time.
            from scripts.game_data.codecs.leveldata.npc_runtime import (
                LevelNpcCodecError,
                decode_npc_runtime_proxy_row,
            )

            decoded_proxy = decode_npc_runtime_proxy_row(
                data[value_offset:value_end]
            )
        except (LevelNpcCodecError, AtmosphericNpcFramingError) as exc:
            entry["npcRuntimeProxyDiagnostic"] = str(exc)
        else:
            entry["npcRuntimeProxyData"] = decoded_proxy
            entry["proxyBodyStatus"] = "named_exact_npc_runtime_proxy"
            named_rows += 1
        entries.append(entry)
    named_prefixes = sum("levelEntityData" in entry for entry in entries)
    if named_rows == count:
        schema_status = "named_exact"
        status = "exact_named_npc_runtime_proxy_table"
    elif named_prefixes == count:
        schema_status = "named_exact_frame"
        status = "exact_dictionary_entry_ranges_with_partial_named_proxy_bodies"
    else:
        schema_status = "anonymous_exact_frame"
        status = "exact_dictionary_entry_ranges_with_opaque_proxy_bodies"
    return {
        "status": status,
        "schemaStatus": schema_status,
        "serializedMemberCount": ROOT_MEMBER_COUNT,
        "entryCount": count,
        "bytesConsumed": len(data),
        "entries": entries,
        "namedLevelEntityPrefixCount": named_prefixes,
        "namedNpcRuntimeProxyCount": named_rows,
        "evidenceBoundary": (
            "The declared dictionary count, UTF-8 keys, repeated 118-member proxy markers, "
            "next-entry boundaries, and physical EOF frame every entry. A populated row is "
            "named exact only when the shared 14 + 77 + 27 member NpcRuntimeProxyData codec "
            "advances through its complete bounded value; unsupported nested variants remain "
            "fail-closed at framed or prefix-named evidence."
        ),
    }
