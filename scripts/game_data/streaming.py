"""Strict framing checks for the Endfield block-15 Streaming family.

This module intentionally stops at the serialized envelope.  It does not
assign names or meanings to FlatBuffer fields.  The current build contains
two length-prefixed inverted-LZ4 families (``InitChunkData`` and
``StreamingChunkData``) and a raw ``StreamingChunkInfo`` family.  A small
DevOnly subset is raw despite sharing the first two path families, so the
decoder accepts raw only after independently validating the observed root
shape.
"""

from __future__ import annotations

import struct
from typing import Any

from scripts.game_data.inverted_lz4 import decompress_inverted_lz4


_COMPRESSED_ROOT = (8, 40, tuple(range(8)))
_INFO_ROOTS = {
    (4, 20, tuple(range(4))),
    # The sole DevOnly StreamingChunkInfo in the installed corpus uses the
    # older three-field table shape and is raw, not a malformed four-field
    # record.
    (3, 16, tuple(range(3))),
}


def _u16(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise ValueError(f"Streaming u16 outside payload at {offset}/{len(data)}")
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"Streaming u32 outside payload at {offset}/{len(data)}")
    return struct.unpack_from("<I", data, offset)[0]


def _i32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"Streaming i32 outside payload at {offset}/{len(data)}")
    return struct.unpack_from("<i", data, offset)[0]


def _root_layout(data: bytes) -> dict[str, Any]:
    if len(data) < 8:
        raise ValueError(f"Streaming payload is too short for a FlatBuffer root: {len(data)}")
    root = _u32(data, 0)
    if root < 4 or root + 4 > len(data):
        raise ValueError(f"Streaming root offset {root} outside payload {len(data)}")
    back = _i32(data, root)
    if back <= 0 or back > root:
        raise ValueError(f"Streaming root vtable back offset {back} at {root}")
    vtable = root - back
    if vtable + 4 > len(data):
        raise ValueError(f"Streaming vtable {vtable} outside payload {len(data)}")
    vtable_size = _u16(data, vtable)
    object_size = _u16(data, vtable + 2)
    if vtable_size < 4 or vtable_size % 2 or vtable + vtable_size > len(data):
        raise ValueError(f"Streaming vtable size {vtable_size} is invalid at {vtable}")
    if object_size < 4 or root + object_size > len(data):
        raise ValueError(f"Streaming object size {object_size} exceeds payload at {root}")
    field_count = (vtable_size - 4) // 2
    fields = [_u16(data, vtable + 4 + index * 2) for index in range(field_count)]
    if any(value and (value < 4 or value >= object_size) for value in fields):
        raise ValueError(f"Streaming field offset outside object: {fields}")
    return {
        "rootOffset": root,
        "vtableOffset": vtable,
        "vtableSize": vtable_size,
        "objectSize": object_size,
        "fieldCount": field_count,
        "presentFields": [index for index, value in enumerate(fields) if value],
        "opaqueTailBytes": len(data) - (root + object_size),
    }


def _check_root(kind: str, layout: dict[str, Any]) -> None:
    if kind == "info":
        if (
            layout["fieldCount"],
            layout["objectSize"],
            tuple(layout["presentFields"]),
        ) in _INFO_ROOTS:
            return
        expected = "(fieldCount, objectSize, presentFields) in {(4,20,[0..3]), (3,16,[0..2])}"
        actual = (layout["fieldCount"], layout["objectSize"], tuple(layout["presentFields"]))
        raise ValueError(
            f"Streaming {kind} root shape {actual}, expected {expected}"
        )
    expected_fields, expected_object_size, expected_present = _COMPRESSED_ROOT
    if layout["fieldCount"] != expected_fields:
        raise ValueError(
            f"Streaming {kind} root has {layout['fieldCount']} fields, "
            f"expected {expected_fields}"
        )
    if layout["objectSize"] != expected_object_size:
        raise ValueError(
            f"Streaming {kind} root object size {layout['objectSize']}, "
            f"expected {expected_object_size}"
        )
    if tuple(layout["presentFields"]) != expected_present:
        raise ValueError(
            f"Streaming {kind} root present fields {layout['presentFields']}, "
            f"expected {list(expected_present)}"
        )


def _decode_compressed(packed: bytes) -> bytes:
    if len(packed) < 5:
        raise ValueError("Streaming compressed payload lacks size prefix and body")
    expected = _u32(packed, 0)
    if expected <= 0:
        raise ValueError(f"Streaming decoded size is not positive: {expected}")
    return decompress_inverted_lz4(packed[4:], expected)


def parse_streaming_file(kind: str, packed: bytes, *, allow_raw: bool = False) -> dict[str, Any]:
    """Validate one block-15 file's observed envelope and root table.

    ``kind`` is a maintained path-family classification: ``init``,
    ``streaming``, or ``info``.  For the first two kinds compressed decoding
    is attempted first; raw is accepted only when its root has the exact same
    observed 8-field shape.  Raw data-family input is rejected unless the
    caller has independently established the raw exception (the installed
    corpus uses this only for DevOnly files).  The returned tail is
    explicitly opaque rather than being treated as consumed by the root
    table.
    """

    if kind not in {"init", "streaming", "info"}:
        raise ValueError(f"unknown Streaming family {kind!r}")
    if not packed:
        raise ValueError("Streaming payload is empty")

    if kind == "info":
        clear = packed
        encoding = "raw_flatbuffer"
        declared_decoded_size = None
    else:
        try:
            clear = _decode_compressed(packed)
            encoding = "inverted_lz4"
            declared_decoded_size = _u32(packed, 0)
        except ValueError as compressed_error:
            if not allow_raw:
                raise ValueError(
                    f"Streaming compressed envelope failed: {compressed_error}"
                ) from compressed_error
            # DevOnly fixtures in the installed build are raw.  Do not
            # accept arbitrary raw bytes: the exact root contract below is
            # the independent gate for this exception.
            clear = packed
            encoding = "raw_flatbuffer"
            declared_decoded_size = None
            try:
                raw_layout = _root_layout(clear)
                _check_root(kind, raw_layout)
            except ValueError as raw_error:
                raise ValueError(
                    f"Streaming compressed envelope failed ({compressed_error}); "
                    f"raw fallback failed ({raw_error})"
                ) from compressed_error

    layout = _root_layout(clear)
    _check_root(kind, layout)
    if encoding == "inverted_lz4" and len(clear) != declared_decoded_size:
        raise ValueError(
            f"Streaming decoded size mismatch: {len(clear)}/{declared_decoded_size}"
        )
    return {
        "kind": kind,
        "encoding": encoding,
        "sourceBytes": len(packed),
        "decodedBytes": len(clear),
        "declaredDecodedBytes": declared_decoded_size,
        "root": layout,
    }


__all__ = ["parse_streaming_file"]
