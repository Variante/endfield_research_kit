"""Conservative DynamicStreaming envelope and FlatBuffer framing helpers.

The shared codec lives under ``scripts.game_data``.  This module owns only the
DynamicStreaming-specific length prefix and the exact FlatBuffer table shapes
observed in the current build.  It deliberately does not assign meanings to
the 61 SingleGrid fields or to the DataMask.
"""

from __future__ import annotations

import struct
from collections import Counter
from typing import Any

from scripts.game_data.inverted_lz4 import decompress_inverted_lz4


OBSERVED_CHUNK_VERSION = 94
OBSERVED_STREAMING_VERSION = 47
SINGLE_GRID_FIELD_COUNT = 61
COMPRESSED_DYNAMIC_KINDS = frozenset(("init", "streaming"))
RAW_DYNAMIC_KINDS = frozenset(("main", "stream_area", "version"))
# These are deliberately layout contracts, not schema guesses.  The selected
# build has no generated FlatBuffer type for the three auxiliary roots, so
# their fields remain unnamed here.
OBSERVED_ROOT_SHAPES = {
    "init": (8, 40, tuple(range(8))),
    "streaming": (8, 40, tuple(range(8))),
    "main": (5, None, tuple(range(5))),
    "stream_area": (7, 52, tuple(range(7))),
    "version": (3, 16, tuple(range(3))),
}
REJECTED_DATA_MASK_PRESENCE_CANDIDATE = (
    "sum(1 << (fieldIndex - base)) for every nonempty vector field at or after base"
)


def _u16(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise ValueError(f"u16 outside payload at {offset}/{len(data)}")
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"u32 outside payload at {offset}/{len(data)}")
    return struct.unpack_from("<I", data, offset)[0]


def _i32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"i32 outside payload at {offset}/{len(data)}")
    return struct.unpack_from("<i", data, offset)[0]


def decode_length_prefixed_inverted_lz4(packed: bytes) -> bytes:
    """Decode an exact-consumption ``u32 length + inverted-LZ4`` envelope."""

    if len(packed) < 5:
        raise ValueError("length-prefixed inverted-LZ4 payload lacks size and body")
    expected = _u32(packed, 0)
    return decompress_inverted_lz4(packed[4:], expected)


def _table_layout(data: bytes, table: int) -> dict[str, Any]:
    back = _i32(data, table)
    if back == 0:
        raise ValueError(f"invalid table vtable back offset {back} at {table}")
    vtable = table - back
    if vtable < 0 or vtable + 4 > len(data):
        raise ValueError(f"table vtable target {vtable} outside payload")
    vtable_size = _u16(data, vtable)
    object_size = _u16(data, vtable + 2)
    if vtable_size < 4 or vtable_size % 2 or vtable + vtable_size > len(data):
        raise ValueError(f"invalid vtable size {vtable_size} at {vtable}")
    if object_size < 4 or table + object_size > len(data):
        raise ValueError(f"invalid object size {object_size} at {table}")
    fields = [_u16(data, vtable + 4 + index * 2) for index in range((vtable_size - 4) // 2)]
    if any(value and (value < 4 or value >= object_size) for value in fields):
        raise ValueError(f"table field offset outside object: {fields}")
    return {
        "tableOffset": table,
        "vtableOffset": vtable,
        "vtableSize": vtable_size,
        "objectSize": object_size,
        "fieldCount": len(fields),
        "presentFields": [index for index, value in enumerate(fields) if value],
    }


def _root_layout(data: bytes) -> dict[str, Any]:
    root = _u32(data, 0)
    if root < 4 or root + 4 > len(data):
        raise ValueError(f"root offset {root} outside payload {len(data)}")
    layout = _table_layout(data, root)
    layout["rootOffset"] = root
    return layout


def _field_address(data: bytes, layout: dict[str, Any], index: int) -> int | None:
    if index < 0 or index >= int(layout["fieldCount"]):
        return None
    relative = _u16(data, int(layout["vtableOffset"]) + 4 + index * 2)
    return int(layout["tableOffset"]) + relative if relative else None


def _field_span(data: bytes, layout: dict[str, Any], index: int, width: int) -> int | None:
    """Return a field address only when its complete scalar span is in-object."""

    if width < 0:
        raise ValueError(f"negative field width {width}")
    address = _field_address(data, layout, index)
    if address is None:
        return None
    object_end = int(layout["tableOffset"]) + int(layout["objectSize"])
    if address + width > object_end or address + width > len(data):
        raise ValueError(
            f"field {index} span {address}:{address + width} exceeds table/data bounds "
            f"({object_end}/{len(data)})"
        )
    return address


def _vector(data: bytes, layout: dict[str, Any], index: int) -> tuple[int, int]:
    address = _field_span(data, layout, index, 4)
    if address is None:
        return 0, 0
    relative = _u32(data, address)
    if relative == 0:
        raise ValueError(f"field {index} has a zero vector offset")
    target = address + relative
    if target <= address or target + 4 > len(data):
        raise ValueError(f"field {index} vector target {target} outside payload")
    count = _u32(data, target)
    end = target + 4 + count * 4
    if end > len(data):
        raise ValueError(f"field {index} vector end {end} outside payload")
    return target + 4, count


def _validate_string_vector(data: bytes, vector: int, count: int) -> None:
    """Validate every FlatBuffer string target, UTF-8 body, and terminator."""

    for index in range(count):
        slot = vector + index * 4
        relative = _u32(data, slot)
        if relative == 0:
            raise ValueError(f"TotalStr[{index}] has a zero string offset")
        target = slot + relative
        if target <= slot or target + 4 > len(data):
            raise ValueError(f"TotalStr[{index}] target {target} outside payload")
        length = _u32(data, target)
        start = target + 4
        end = start + length
        if end >= len(data):
            raise ValueError(
                f"TotalStr[{index}] range {start}:{end + 1} outside payload {len(data)}"
            )
        if data[end] != 0:
            raise ValueError(f"TotalStr[{index}] lacks FlatBuffer NUL terminator")
        try:
            data[start:end].decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError(f"TotalStr[{index}] is not strict UTF-8") from exc


def parse_dynamic_chunk_framing(data: bytes) -> dict[str, Any]:
    """Validate the observed five-field chunk root and 61-field grid tables.

    Returned values use generated accessor names for the three scalar root
    accessors.  Grid field contents and DataMask are intentionally not decoded.
    """

    root = _root_layout(data)
    if root["fieldCount"] != 5 or root["presentFields"] != [0, 1, 2, 3, 4]:
        raise ValueError(f"unexpected dynamic chunk root layout: {root}")

    scalar_specs = ((0, "<Q", "Version"), (1, "<i", "StreamingVersion"), (2, "<I", "UniqueId"))
    scalars: dict[str, int] = {}
    for index, fmt, name in scalar_specs:
        address = _field_span(data, root, index, struct.calcsize(fmt))
        if address is None:
            raise ValueError(f"dynamic chunk root field {name} is absent")
        scalars[name] = struct.unpack_from(fmt, data, address)[0]

    if scalars["Version"] != OBSERVED_CHUNK_VERSION:
        raise ValueError(
            f"unsupported dynamic chunk Version {scalars['Version']}; "
            f"expected {OBSERVED_CHUNK_VERSION}"
        )
    if scalars["StreamingVersion"] != OBSERVED_STREAMING_VERSION:
        raise ValueError(
            f"unsupported dynamic chunk StreamingVersion {scalars['StreamingVersion']}; "
            f"expected {OBSERVED_STREAMING_VERSION}"
        )

    grid_vector, grid_count = _vector(data, root, 3)
    shapes: Counter[tuple[int, int, tuple[int, ...]]] = Counter()
    for index in range(grid_count):
        slot = grid_vector + index * 4
        relative = _u32(data, slot)
        if relative == 0:
            raise ValueError(f"dynamic SingleGrid {index} has a zero table offset")
        table = slot + relative
        if table <= slot:
            raise ValueError(f"dynamic SingleGrid {index} table target is not forward")
        layout = _table_layout(data, table)
        if layout["fieldCount"] != SINGLE_GRID_FIELD_COUNT:
            raise ValueError(
                f"dynamic SingleGrid {index} has {layout['fieldCount']} fields, "
                f"expected {SINGLE_GRID_FIELD_COUNT}"
            )
        shapes[
            (
                int(layout["fieldCount"]),
                int(layout["objectSize"]),
                tuple(int(value) for value in layout["presentFields"]),
            )
        ] += 1
        # The selected-build metadata exposes a Length accessor for every
        # field 1..59.  Their element schemas are intentionally not decoded,
        # but each vector envelope must still be bounded exactly.  Field 0 is
        # the generated UInt32 UniqueId; field 60 is generated UInt64 DataMask.
        _field_span(data, layout, 0, 4)
        for field_index in range(1, SINGLE_GRID_FIELD_COUNT - 1):
            _vector(data, layout, field_index)
        _field_span(data, layout, SINGLE_GRID_FIELD_COUNT - 1, 8)

    strings_vector, strings_count = _vector(data, root, 4)
    _validate_string_vector(data, strings_vector, strings_count)
    return {
        **scalars,
        "GridsLength": grid_count,
        "TotalStrLength": strings_count,
        "SingleGridFieldCount": SINGLE_GRID_FIELD_COUNT,
        "SingleGridShapes": [
            {"fieldCount": key[0], "objectSize": key[1], "presentFields": list(key[2]), "count": count}
            for key, count in shapes.most_common()
        ],
        "DataMaskInference": {
            "status": "rejected",
            "candidate": REJECTED_DATA_MASK_PRESENCE_CANDIDATE,
            "reason": "full-corpus matches were 28 at base 1, 3682 at base 2, and zero at bases 3-5",
        },
    }


def decode_dynamic_payload(kind: str, packed: bytes) -> bytes:
    """Decode exactly the envelope used by one DynamicStreaming family.

    ``init`` and ``streaming`` have a little-endian decoded-size prefix and
    inverted-LZ4 body.  ``main``, ``stream_area``, and ``version`` are raw
    FlatBuffers in the observed dump; accepting a compressed envelope for
    those kinds would hide a caller/path classification error.
    """

    if kind in COMPRESSED_DYNAMIC_KINDS:
        return decode_length_prefixed_inverted_lz4(packed)
    if kind in RAW_DYNAMIC_KINDS:
        return packed
    raise ValueError(f"unknown DynamicStreaming family {kind!r}")


def _check_observed_root(kind: str, root: dict[str, Any]) -> None:
    try:
        expected_fields, expected_object_size, expected_present = OBSERVED_ROOT_SHAPES[kind]
    except KeyError as exc:
        raise ValueError(f"unknown DynamicStreaming family {kind!r}") from exc
    if int(root["fieldCount"]) != expected_fields:
        raise ValueError(
            f"{kind} root has {root['fieldCount']} fields, expected {expected_fields}"
        )
    if expected_object_size is not None and int(root["objectSize"]) != expected_object_size:
        raise ValueError(
            f"{kind} root object size {root['objectSize']}, expected {expected_object_size}"
        )
    if tuple(root["presentFields"]) != expected_present:
        raise ValueError(
            f"{kind} root present fields {root['presentFields']}, expected {list(expected_present)}"
        )


def parse_dynamic_file(kind: str, packed: bytes) -> dict[str, Any]:
    """Decode and frame any of the five observed DynamicStreaming roots.

    Only ``main`` has selected-build generated accessor names in the local
    metadata (``FBDynamicSceneChunkData`` and ``FBDynamicSceneSingleGrid``).
    The other roots are returned as exact unnamed table layouts.
    """

    clear = decode_dynamic_payload(kind, packed)
    if kind == "main":
        parsed = parse_dynamic_chunk_framing(clear)
    else:
        root = _root_layout(clear)
        _check_observed_root(kind, root)
        parsed = {"root": root}
    return {
        "kind": kind,
        "sourceBytes": len(packed),
        "decodedBytes": len(clear),
        "root": parsed.pop("root", _root_layout(clear)),
        **parsed,
    }
