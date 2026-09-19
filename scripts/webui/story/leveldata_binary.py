"""Strict partial framing for current-corpus ``LevelData`` payloads."""

from __future__ import annotations

from typing import Any

from .codecs.leveldata.memorypack import read_count, read_i32, read_string


class LevelDataTopLevelFramingError(ValueError):
    """Raised when an exact partial ``LevelData`` frame cannot be proved."""


def frame_leveldata_empty_tail(data: bytes) -> dict[str, Any]:
    """Frame one 43-member ``LevelData`` with the known empty tail at EOF.

    The current corpus contains a recurring tail made of a non-negative i32,
    fourteen empty collections, a one-member object envelope, a UTF-8 string,
    two empty collections, a null union tag, and three empty collections.
    This function proves that byte sequence with a strict cursor and exact EOF.
    It does not name the values or infer their member ordinals: the preceding
    bytes remain one explicit opaque range.
    """
    if not data:
        raise LevelDataTopLevelFramingError("truncated LevelData: empty payload")
    if data[0] != 43:
        raise LevelDataTopLevelFramingError(
            f"LevelData member count mismatch: expected=43 actual={data[0]}"
        )
    if len(data) < 91:
        raise LevelDataTopLevelFramingError(
            "truncated LevelData empty tail: expected at least 91 bytes"
        )

    # The only variable-width item in this tail is bounded to 256 bytes, so a
    # valid start must be within this bounded window before EOF.
    candidates: list[dict[str, Any]] = []
    for start in range(max(1, len(data) - 384), len(data)):
        scalar = read_i32(data, start)
        if scalar is None or scalar[0] < 0:
            continue
        scalar_value, cursor = scalar
        empty_collection_offsets: list[int] = []
        valid = True
        for _ in range(14):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            empty_collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or data[cursor : cursor + 5] != b"\x01\x00\x00\x00\x00":
            continue
        object_offset = cursor
        cursor += 5
        string_decoded = read_string(data, cursor, max_length=256)
        if string_decoded is None:
            continue
        string_value, cursor = string_decoded
        for _ in range(2):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            empty_collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or cursor >= len(data) or data[cursor] != 0xFF:
            continue
        null_union_offset = cursor
        cursor += 1
        for _ in range(3):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            empty_collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or cursor != len(data):
            continue
        candidates.append({
            "startOffset": start,
            "endOffset": cursor,
            "leadingScalar": scalar_value,
            "oneMemberObjectOffset": object_offset,
            "oneMemberObjectRawMarker": data[object_offset],
            "oneMemberObjectRawValue": int.from_bytes(
                data[object_offset + 1 : object_offset + 5],
                "little",
                signed=True,
            ),
            "stringValue": string_value,
            "emptyCollectionOffsets": empty_collection_offsets,
            "nullUnionOffset": null_union_offset,
            "nullUnionRawTag": data[null_union_offset],
        })

    if len(candidates) != 1:
        raise LevelDataTopLevelFramingError(
            "LevelData empty EOF tail is not unique and exact: "
            f"candidates={len(candidates)} length={len(data)}"
        )
    tail = candidates[0]
    return {
        "status": "exact_empty_tail_with_opaque_top_level_prefix",
        "schemaStatus": "partial",
        "serializedMemberCount": 43,
        "bytesConsumed": len(data),
        "ranges": {
            "memberCount": {"startOffset": 0, "endOffset": 1},
            "opaqueTopLevelPrefix": {
                "startOffset": 1,
                "endOffset": tail["startOffset"],
                "length": tail["startOffset"] - 1,
                "status": "opaque_unassigned_top_level_members",
            },
            "emptyTail": tail,
        },
        "evidenceBoundary": (
            "The tail cursor consumes exactly to EOF and preserves raw markers; "
            "the preceding bytes are not split into members or named."
        ),
    }
