"""Fail-closed framing for current ``NPC/MontageJson/MontageNew`` payloads.

The selected build uses a compact MemoryPack object with three top-level
members and a 24-member montage record. Both observed variable collections are
count-framed. Nested values remain anonymous: metadata names alone do not
establish their serialized field order.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Any

from .core import MEMORYPACK_NULL_COUNT, format_offset


NPC_MONTAGE_ROOT_MEMBER_COUNT = 3
NPC_MONTAGE_DATA_MEMBER_COUNT = 24
NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT = 7
NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT = 12
NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT = 3
NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT = 4
NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT = 5
NPC_MONTAGE_RELATIVE_PREFIX = "Data/Json/NPC/MontageJson/MontageNew/"

_GUID_PROXY_SIZE = 16
_ASYNC_CLIP_INFO_SIZE = 36
_TRANSITION_INFO_SIZE = 32
_MEMBER3_RECORD_FIXED_PREFIX_SIZE = 10
_MEMBER3_NESTED_OBJECT_BODY_SIZE = 9
_MEMBER3_INNER_RECORD_FIXED_SIZE = 20
_MEMBER3_RECORD_FIXED_SUFFIX_SIZE = 38
_MEMBER3_MIN_RECORD_SIZE = 71
_MEMBER3_MIN_INNER_RECORD_SIZE = 33
_POST_MEMBER3_MIN_SUFFIX_SIZE = 231
_MEMBER18_RECORD_BODY_SIZE = 20
_MEMBER18_RECORD_SIZE = 21
_POST_MEMBER18_SUFFIX_SIZE = 72
_MAX_ANONYMOUS_UTF8_BYTES = 512


class NpcMontageFramingError(ValueError):
    """Raised when a payload is truncated, changed, or outside this exact frame."""


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def require(self, size: int, field: str) -> int:
        start = self.offset
        end = start + size
        if size < 0 or end > len(self.data):
            raise NpcMontageFramingError(
                f"{field}:truncated offset={format_offset(start)} "
                f"need={size} remaining={len(self.data) - start}"
            )
        self.offset = end
        return start

    def u8(self, field: str) -> int:
        return self.data[self.require(1, field)]

    def i32(self, field: str) -> int:
        return struct.unpack_from("<i", self.data, self.require(4, field))[0]

    def u32(self, field: str) -> int:
        return struct.unpack_from("<I", self.data, self.require(4, field))[0]

    def f32(self, field: str) -> float:
        value = struct.unpack_from("<f", self.data, self.require(4, field))[0]
        if not math.isfinite(value):
            raise NpcMontageFramingError(f"{field}:non-finite")
        return value

    def skip(self, size: int, field: str) -> dict[str, int]:
        start = self.require(size, field)
        return {"startOffset": start, "endOffset": self.offset, "length": size}

    def boolean(self, field: str) -> bool:
        value = self.u8(field)
        if value not in (0, 1):
            raise NpcMontageFramingError(f"{field}:invalid-bool={value}")
        return bool(value)


def is_npc_montage_memorypack_path(path: str | Path) -> bool:
    """Return whether ``path`` routes to the generated NPC montage family."""
    normalized = str(path).replace("\\", "/")
    folded = normalized.casefold()
    marker = NPC_MONTAGE_RELATIVE_PREFIX.casefold()
    marker_offset = folded.find(marker)
    return (
        marker_offset >= 0
        and (marker_offset == 0 or folded[marker_offset - 1] == "/")
        and folded.endswith(".json")
    )


def _read_clip_info(reader: _Reader) -> dict[str, Any]:
    start = reader.offset
    member_count = reader.u8("data.member2.memberCount")
    if member_count == 0xFF:
        return {
            "isNull": True,
            "memberCount": None,
            "startOffset": start,
            "endOffset": reader.offset,
            "anonymousUtf8": None,
        }
    if member_count != NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT:
        raise NpcMontageFramingError(
            "data.member2.memberCount:"
            f"expected={NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT} actual={member_count}"
        )

    # The seven-member record has an exact current-corpus frame. Metadata
    # suggests that its UTF-8 value may be a clip name, but setter order alone
    # does not establish the serialized cursor. Keep the value anonymous while
    # retaining the current corpus's non-empty A_* prefix as a fail-closed gate.
    reader.f32("data.member2.member0")
    reader.i32("data.member2.member1")
    reader.skip(8, "data.member2.member2")
    reader.skip(_GUID_PROXY_SIZE, "data.member2.member3")
    string_offset = reader.offset
    length = reader.u32("data.member2.anonymousUtf8.length")
    anonymous_utf8: str | None
    if length == MEMORYPACK_NULL_COUNT:
        anonymous_utf8 = None
    else:
        if length > _MAX_ANONYMOUS_UTF8_BYTES:
            raise NpcMontageFramingError(
                f"data.member2.anonymousUtf8:invalid-length={length}"
            )
        raw_offset = reader.require(length, "data.member2.anonymousUtf8.bytes")
        try:
            anonymous_utf8 = reader.data[raw_offset:reader.offset].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise NpcMontageFramingError(
                "data.member2.anonymousUtf8:invalid-utf8 "
                f"offset={format_offset(raw_offset)}"
            ) from exc
        if anonymous_utf8 and not anonymous_utf8.startswith("A_"):
            raise NpcMontageFramingError(
                "data.member2.anonymousUtf8:unexpected-current-prefix="
                f"{anonymous_utf8[:32]!r}"
            )
    reader.f32("data.member2.member5")
    reader.f32("data.member2.member6")
    return {
        "isNull": False,
        "memberCount": member_count,
        "startOffset": start,
        "endOffset": reader.offset,
        "anonymousUtf8Offset": string_offset,
        "anonymousUtf8": anonymous_utf8,
    }


def _read_member18_records(reader: _Reader, count: int) -> list[dict[str, Any]]:
    remaining = len(reader.data) - reader.offset
    required = count * _MEMBER18_RECORD_SIZE + _POST_MEMBER18_SUFFIX_SIZE
    if required > remaining:
        raise NpcMontageFramingError(
            "data.member18:truncated-count-envelope "
            f"count={count} need={required} remaining={remaining}"
        )
    records: list[dict[str, Any]] = []
    for index in range(count):
        start = reader.offset
        member_count = reader.u8(f"data.member18[{index}].memberCount")
        if member_count != NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT:
            raise NpcMontageFramingError(
                f"data.member18[{index}].memberCount:"
                f"expected={NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT} "
                f"actual={member_count}"
            )
        body_range = reader.skip(
            _MEMBER18_RECORD_BODY_SIZE,
            f"data.member18[{index}].anonymousBody",
        )
        records.append(
            {
                "memberCount": member_count,
                "startOffset": start,
                "endOffset": reader.offset,
                "anonymousBodyRange": body_range,
            }
        )
    return records


def _read_anonymous_utf8(reader: _Reader, field: str) -> dict[str, Any]:
    start = reader.offset
    length = reader.u32(f"{field}.length")
    if length == MEMORYPACK_NULL_COUNT:
        return {
            "startOffset": start,
            "endOffset": reader.offset,
            "byteLength": None,
            "isNull": True,
        }
    if length > _MAX_ANONYMOUS_UTF8_BYTES:
        raise NpcMontageFramingError(f"{field}:invalid-length={length}")
    raw_offset = reader.require(length, f"{field}.bytes")
    try:
        reader.data[raw_offset:reader.offset].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise NpcMontageFramingError(
            f"{field}:invalid-utf8 offset={format_offset(raw_offset)}"
        ) from exc
    return {
        "startOffset": start,
        "endOffset": reader.offset,
        "byteLength": length,
        "isNull": False,
    }


def _read_member3_records(reader: _Reader, count: int) -> list[dict[str, Any]]:
    remaining = len(reader.data) - reader.offset
    required = count * _MEMBER3_MIN_RECORD_SIZE + _POST_MEMBER3_MIN_SUFFIX_SIZE
    if required > remaining:
        raise NpcMontageFramingError(
            "data.member3:truncated-count-envelope "
            f"count={count} need-at-least={required} remaining={remaining}"
        )

    records: list[dict[str, Any]] = []
    for index in range(count):
        start = reader.offset
        member_count = reader.u8(f"data.member3[{index}].memberCount")
        if member_count != NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT:
            raise NpcMontageFramingError(
                f"data.member3[{index}].memberCount:"
                f"expected={NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT} "
                f"actual={member_count}"
            )
        anonymous_utf8_a = _read_anonymous_utf8(
            reader, f"data.member3[{index}].anonymousUtf8A"
        )
        fixed_prefix = reader.skip(
            _MEMBER3_RECORD_FIXED_PREFIX_SIZE,
            f"data.member3[{index}].anonymousFixedPrefix",
        )
        nested_member_count = reader.u8(
            f"data.member3[{index}].nestedObject.memberCount"
        )
        if nested_member_count != NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT:
            raise NpcMontageFramingError(
                f"data.member3[{index}].nestedObject.memberCount:"
                f"expected={NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT} "
                f"actual={nested_member_count}"
            )
        nested_body = reader.skip(
            _MEMBER3_NESTED_OBJECT_BODY_SIZE,
            f"data.member3[{index}].nestedObject.anonymousBody",
        )
        anonymous_utf8_b = _read_anonymous_utf8(
            reader, f"data.member3[{index}].anonymousUtf8B"
        )
        inner_count_offset = reader.offset
        inner_count = reader.u32(f"data.member3[{index}].inner.count")
        if inner_count > (
            len(reader.data) - reader.offset
        ) // _MEMBER3_MIN_INNER_RECORD_SIZE:
            raise NpcMontageFramingError(
                f"data.member3[{index}].inner:count-overrun "
                f"count={inner_count} remaining={len(reader.data) - reader.offset}"
            )
        inner_records: list[dict[str, Any]] = []
        for inner_index in range(inner_count):
            inner_start = reader.offset
            inner_member_count = reader.u8(
                f"data.member3[{index}].inner[{inner_index}].memberCount"
            )
            if inner_member_count != NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT:
                raise NpcMontageFramingError(
                    f"data.member3[{index}].inner[{inner_index}].memberCount:"
                    f"expected={NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT} "
                    f"actual={inner_member_count}"
                )
            inner_utf8_a = _read_anonymous_utf8(
                reader,
                f"data.member3[{index}].inner[{inner_index}].anonymousUtf8A",
            )
            inner_fixed = reader.skip(
                _MEMBER3_INNER_RECORD_FIXED_SIZE,
                f"data.member3[{index}].inner[{inner_index}].anonymousFixed",
            )
            inner_utf8_b = _read_anonymous_utf8(
                reader,
                f"data.member3[{index}].inner[{inner_index}].anonymousUtf8B",
            )
            inner_utf8_c = _read_anonymous_utf8(
                reader,
                f"data.member3[{index}].inner[{inner_index}].anonymousUtf8C",
            )
            inner_records.append(
                {
                    "memberCount": inner_member_count,
                    "startOffset": inner_start,
                    "endOffset": reader.offset,
                    "anonymousUtf8Ranges": [
                        inner_utf8_a,
                        inner_utf8_b,
                        inner_utf8_c,
                    ],
                    "anonymousFixedRange": inner_fixed,
                }
            )
        fixed_suffix = reader.skip(
            _MEMBER3_RECORD_FIXED_SUFFIX_SIZE,
            f"data.member3[{index}].anonymousFixedSuffix",
        )
        records.append(
            {
                "memberCount": member_count,
                "startOffset": start,
                "endOffset": reader.offset,
                "nestedObjectMemberCount": nested_member_count,
                "anonymousUtf8Ranges": [anonymous_utf8_a, anonymous_utf8_b],
                "anonymousFixedRanges": [fixed_prefix, nested_body, fixed_suffix],
                "innerCountOffset": inner_count_offset,
                "innerRecords": inner_records,
            }
        )
    return records


def frame_npc_montage(data: bytes) -> dict[str, Any]:
    """Frame one supported current-build NPC montage through physical EOF.

    Both variable collections are consumed only through explicit counts,
    length-prefixed values, fixed anonymous extents, and per-record member-count
    markers. No suffix scanning is used.
    """
    reader = _Reader(data)
    root_count = reader.u8("root.memberCount")
    if root_count != NPC_MONTAGE_ROOT_MEMBER_COUNT:
        raise NpcMontageFramingError(
            f"root.memberCount:expected={NPC_MONTAGE_ROOT_MEMBER_COUNT} actual={root_count}"
        )

    root_member0 = reader.i32("root.member0")
    data_count = reader.u8("root.member1.memberCount")
    if data_count != NPC_MONTAGE_DATA_MEMBER_COUNT:
        raise NpcMontageFramingError(
            f"root.member1.memberCount:expected={NPC_MONTAGE_DATA_MEMBER_COUNT} "
            f"actual={data_count}"
        )

    reader.boolean("data.member0")
    reader.boolean("data.member1")
    clip_info = _read_clip_info(reader)

    dynamic_count_offset = reader.offset
    dynamic_count = reader.u32("data.member3.count")
    member3_records = _read_member3_records(reader, dynamic_count)
    reader.boolean("data.member4")
    reader.boolean("data.member5")
    anonymous_ranges = [
        reader.skip(_ASYNC_CLIP_INFO_SIZE, "data.member6"),
    ]
    reader.boolean("data.member7")
    reader.f32("data.member8")
    reader.f32("data.member9")
    reader.i32("data.member10")
    reader.i32("data.member11")
    anonymous_ranges.extend([
        reader.skip(8, "data.member12"),
        reader.skip(_GUID_PROXY_SIZE, "data.member13"),
    ])
    reader.f32("data.member14")
    anonymous_ranges.append(
        reader.skip(_ASYNC_CLIP_INFO_SIZE, "data.member15")
    )
    reader.i32("data.member16")
    anonymous_ranges.append(
        reader.skip(_TRANSITION_INFO_SIZE, "data.member17")
    )

    override_count_offset = reader.offset
    override_count = reader.u32("data.member18.count")
    member18_records = _read_member18_records(reader, override_count)
    reader.i32("data.member19")
    reader.f32("data.member20")
    anonymous_ranges.append(
        reader.skip(_ASYNC_CLIP_INFO_SIZE, "data.member21")
    )
    anonymous_ranges.extend([
        reader.skip(_GUID_PROXY_SIZE, "data.member22"),
        reader.skip(8, "data.member23"),
    ])

    root_member2_offset = reader.offset
    root_member2 = reader.i32("root.member2")
    if reader.offset != len(data):
        raise NpcMontageFramingError(
            f"trailing-bytes offset={format_offset(reader.offset)} "
            f"count={len(data) - reader.offset}"
        )

    return {
        "status": (
            "exact_current_npc_montage_member3_counted_frame"
            if dynamic_count
            else (
                "exact_current_npc_montage_empty_collection_frame"
                if override_count == 0
                else "exact_current_npc_montage_member18_counted_frame"
            )
        ),
        "schemaStatus": "anonymous_exact_frame",
        "serializedMemberCount": root_count,
        "nestedDataMemberCount": data_count,
        "bytesConsumed": reader.offset,
        "clipInfo": clip_info,
        "collectionCountOffsets": [dynamic_count_offset, override_count_offset],
        "emptyCollectionOffsets": [
            *([dynamic_count_offset] if dynamic_count == 0 else []),
            *([override_count_offset] if override_count == 0 else []),
        ],
        "member3Records": member3_records,
        "member18Records": member18_records,
        "rootRawMembers": [
            {"index": 0, "offset": 1, "value": root_member0},
            {"index": 2, "offset": root_member2_offset, "value": root_member2},
        ],
        "anonymousFixedRanges": anonymous_ranges,
        "evidenceBoundary": (
            "The complete supported shape is consumed through physical EOF. "
            "The nested UTF-8 value and all scalar/fixed-size records stay "
            "anonymous; non-empty strings are gated to the observed A_* shape. "
            "Member3 and member18 records are bounded by explicit collection "
            "counts and nested member-count markers; their values remain "
            "anonymous."
        ),
    }


def decode_npc_montage_memorypack(
    path: str | Path,
    data: bytes,
    size: int | None = None,
) -> dict[str, Any] | None:
    """Route and summarize a supported NPC montage payload."""
    if not is_npc_montage_memorypack_path(path):
        return None
    if size is not None and size != len(data):
        raise NpcMontageFramingError(
            f"outer-size-mismatch declared={size} actual={len(data)}"
        )
    framed = frame_npc_montage(data)
    anonymous_utf8 = framed["clipInfo"].get("anonymousUtf8")
    return {
        "kind": "memorypack-json",
        "subtype": "NPCMontageJson",
        "summary": (
            "MemoryPack NPCMontageJson; 3-member root; 24-member montage; "
            "count-framed anonymous records; exact length"
        ),
        "rows": 1,
        "keys": ["anonymousUtf8"],
        "sample": (
            f"anonymousUtf8={anonymous_utf8}"
            if anonymous_utf8
            else "anonymousUtf8=<null-or-empty>"
        ),
        "decoded": framed,
    }
