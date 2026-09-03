"""Strict decoder for the JsonData ``LipSync`` MemoryPack payload.

The current Endfield build stores ``LipSyncRawDataCriware`` as a fifteen
member object.  Every non-null member is a collection of six ``float32``
values.  The native ``LipSyncTrack._ConvertToAnimationCurve`` consumer uses
those values as a Unity ``Keyframe`` in the order documented by
``LIPSYNC_ROW_FIELDS``.

This module intentionally only decodes the proven wire contract.  It does
not guess a newer schema, accept a variable row width, or silently preserve
bytes after the final member.
"""

from __future__ import annotations

import math
import struct
from typing import TypeAlias

from .core import MEMORYPACK_NULL_COUNT


LIPSYNC_FIELD_NAMES = (
    "A",
    "E",
    "EyebrowRaise",
    "EyePitch",
    "EyeYaw",
    "HeadPitch",
    "HeadRoll",
    "HeadYaw",
    "Height",
    "I",
    "O",
    "Squint",
    "U",
    "WidthClose",
    "WidthOpen",
)

LIPSYNC_ROW_FIELDS = (
    "time",
    "value",
    "inTangent",
    "outTangent",
    "inWeight",
    "outWeight",
)

LIPSYNC_MEMBER_COUNT = len(LIPSYNC_FIELD_NAMES)
LIPSYNC_ROW_WIDTH = len(LIPSYNC_ROW_FIELDS)
LIPSYNC_MAX_ROWS_PER_CHANNEL = 1_000_000

LipSyncRows: TypeAlias = tuple[tuple[float, ...], ...]
LipSyncChannels: TypeAlias = dict[str, LipSyncRows | None]


class LipSyncDecodeError(ValueError):
    """Raised when a LipSync payload does not match the proven schema."""


def _require_bytes(data: bytes) -> None:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("lipsync:data-must-be-bytes")


def _read_u32(data: bytes | bytearray | memoryview, offset: int, label: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise LipSyncDecodeError(f"{label}:truncated-count")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def decode_lipsync_memorypack(data: bytes) -> LipSyncChannels:
    """Decode one exact ``JsonData/LipSync`` payload.

    The returned rows are immutable tuples and retain IEEE-754 float values
    exactly as decoded from the wire.  A null outer collection is represented
    by ``None``; an encoded empty collection is represented by ``()``.
    ``LipSyncDecodeError`` is raised for every structural or numeric mismatch.
    """

    _require_bytes(data)
    if not data:
        raise LipSyncDecodeError("lipsync:empty-payload")
    member_count = data[0]
    if member_count != LIPSYNC_MEMBER_COUNT:
        raise LipSyncDecodeError(
            f"lipsync:member-count={member_count};expected={LIPSYNC_MEMBER_COUNT}"
        )

    offset = 1
    channels: LipSyncChannels = {}
    for field_name in LIPSYNC_FIELD_NAMES:
        count, offset = _read_u32(data, offset, f"{field_name}.count")
        if count == MEMORYPACK_NULL_COUNT:
            channels[field_name] = None
            continue
        if count > LIPSYNC_MAX_ROWS_PER_CHANNEL:
            raise LipSyncDecodeError(
                f"{field_name}.count={count};max={LIPSYNC_MAX_ROWS_PER_CHANNEL}"
            )

        # Each item has a four-byte width followed by six float32 values.
        # This early bound rejects impossible counts before allocating a list.
        remaining = len(data) - offset
        if count > remaining // (4 + LIPSYNC_ROW_WIDTH * 4):
            raise LipSyncDecodeError(f"{field_name}.count={count};truncated-rows")

        rows: list[tuple[float, ...]] = []
        for row_index in range(count):
            width, offset = _read_u32(data, offset, f"{field_name}[{row_index}].width")
            if width != LIPSYNC_ROW_WIDTH:
                raise LipSyncDecodeError(
                    f"{field_name}[{row_index}].width={width};expected={LIPSYNC_ROW_WIDTH}"
                )
            byte_count = LIPSYNC_ROW_WIDTH * 4
            if offset + byte_count > len(data):
                raise LipSyncDecodeError(f"{field_name}[{row_index}]:truncated-row")
            values = struct.unpack_from("<6f", data, offset)
            offset += byte_count
            if not all(math.isfinite(value) for value in values):
                raise LipSyncDecodeError(f"{field_name}[{row_index}]:nonfinite-float")
            rows.append(values)
        channels[field_name] = tuple(rows)

    if offset != len(data):
        raise LipSyncDecodeError(f"lipsync:trailing-bytes={len(data) - offset}")
    return channels


def lip_sync_keyframes(channels: LipSyncChannels, field_name: str) -> tuple[dict[str, float], ...] | None:
    """Name the six values for one already-decoded channel.

    Naming is kept separate from wire decoding so callers cannot mistake the
    row labels for an independently proven serialized schema.  The labels are
    established by the exact native ``Keyframe`` constructor call.
    """

    if field_name not in LIPSYNC_FIELD_NAMES:
        raise KeyError(field_name)
    rows = channels[field_name]
    if rows is None:
        return None
    return tuple(dict(zip(LIPSYNC_ROW_FIELDS, row, strict=True)) for row in rows)


__all__ = [
    "LIPSYNC_FIELD_NAMES",
    "LIPSYNC_ROW_FIELDS",
    "LIPSYNC_MEMBER_COUNT",
    "LIPSYNC_ROW_WIDTH",
    "LipSyncDecodeError",
    "LipSyncChannels",
    "LipSyncRows",
    "decode_lipsync_memorypack",
    "lip_sync_keyframes",
]
