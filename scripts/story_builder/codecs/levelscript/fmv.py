"""Exact current-build LevelScript FMV action field decoders."""

from __future__ import annotations

import struct
from typing import Any


LEVELSCRIPT_NATIVE_FMV_ACTION_MAPPING_ID = (
    "gameassembly-2026-07-11-memorypack-play-fmv-action-fields"
)


def _offset_hex(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def _decode_tagged_string_parameter_at(
    payload: bytes,
    offset: int,
) -> tuple[str, int] | None:
    """Decode one exact constant-string ActionParam at ``offset``.

    Current LevelScript ActionParam constants use a one-byte constant tag,
    UTF-8 byte length, payload, then the shared 12-byte reference/source tail.
    Returning the consumed end lets callers prove whether a field is the final
    serialized member instead of selecting an arbitrary printable token.
    """
    param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    if offset < 0 or offset + 5 > len(payload) or payload[offset] != 0x04:
        return None
    size = struct.unpack_from("<I", payload, offset + 1)[0]
    text_start = offset + 5
    text_end = text_start + size
    field_end = text_end + len(param_tail)
    if size <= 0 or field_end > len(payload):
        return None
    if payload[text_end:field_end] != param_tail:
        return None
    try:
        text = payload[text_start:text_end].decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text or any(ord(char) < 0x20 or ord(char) == 0x7F for char in text):
        return None
    return text, field_end


def decode_fmv_action(
    payload: bytes,
    payload_start: int,
    semantic_key: tuple[int, int],
    tagged_string_hits: list[dict[str, Any]],
) -> dict[str, Any]:
    """Decode exact authored FMV ids from the two current native actions.

    IL2CPP metadata and the generated MemoryPack setters prove that
    ``PlayFmvAction._moviePath`` is the first derived field, while
    ``StartFmvAndTeleportAction._fmvId`` is the final derived field. The union
    tag and member count in ``semantic_key`` are required together, so a tag
    collision or a future payload shape fails closed.
    """
    tagged_strings = sorted(
        (
            hit
            for hit in tagged_string_hits
            if isinstance(hit, dict)
            and isinstance(hit.get("offset"), int)
            and isinstance(hit.get("text"), str)
        ),
        key=lambda hit: int(hit["offset"]),
    )
    if semantic_key == (0x035E, 0x0E):
        if len(tagged_strings) != 1:
            return {}
        hit = tagged_strings[0]
        relative_offset = int(hit["offset"]) - payload_start
        if relative_offset != 0:
            return {}
        decoded = _decode_tagged_string_parameter_at(payload, relative_offset)
        if not decoded or decoded[0] != hit["text"]:
            return {}
        return {
            "action": "PlayFmvAction",
            "fmvId": decoded[0],
            "sourceField": "_moviePath",
            "fieldOffset": _offset_hex(int(hit["offset"])),
            "payloadShape": "play-fmv-movie-path-first-derived-field",
            "nativeMappingId": LEVELSCRIPT_NATIVE_FMV_ACTION_MAPPING_ID,
        }
    if semantic_key == (0x04A1, 0x10):
        if not tagged_strings:
            return {}
        hit = tagged_strings[-1]
        relative_offset = int(hit["offset"]) - payload_start
        decoded = _decode_tagged_string_parameter_at(payload, relative_offset)
        if (
            not decoded
            or decoded[0] != hit["text"]
            or decoded[1] != len(payload)
        ):
            return {}
        return {
            "action": "StartFmvAndTeleportAction",
            "fmvId": decoded[0],
            "sourceField": "_fmvId",
            "fieldOffset": _offset_hex(int(hit["offset"])),
            "payloadShape": "start-fmv-teleport-fmv-id-final-derived-field",
            "nativeMappingId": LEVELSCRIPT_NATIVE_FMV_ACTION_MAPPING_ID,
        }
    return {}
