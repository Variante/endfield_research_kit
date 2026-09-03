"""Strict framing checks for the Endfield block-15 Streaming family.

This module intentionally stops at the serialized envelope.  It does not
assign names or meanings to FlatBuffer fields.  The current build contains
two length-prefixed inverted-LZ4 families (``InitChunkData`` and
``StreamingChunkData``) and a raw ``StreamingChunkInfo`` family.  The latter's
selected-build table/vector graph is framed exactly while every field remains
anonymous. Both data families additionally expose one exact anonymous paired-
group subgraph; their other root fields remain opaque. A small DevOnly subset
is raw despite sharing the first two path families, so the decoder accepts raw
only after independently validating the observed root shape.
"""

from __future__ import annotations

import struct
from collections import Counter
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
_INFO_STANDARD_ROW = (2, 16, (0, 1))
_INFO_DEVONLY_ROW = (3, 20, (0, 1, 2))
_INIT_ID_WRAPPER = (1, 8, (0,))
_INIT_GROUP_ROWS = {
    (5, 56, tuple(range(5))),
    (5, 60, tuple(range(5))),
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
        "fields": fields,
        "presentFields": [index for index, value in enumerate(fields) if value],
        "opaqueTailBytes": len(data) - (root + object_size),
    }


def _table_layout(data: bytes, table: int) -> dict[str, Any]:
    """Frame a nested FlatBuffer table, including reused forward vtables."""

    back = _i32(data, table)
    if back == 0:
        raise ValueError(f"Streaming table has zero vtable displacement at {table}")
    vtable = table - back
    if vtable < 0 or vtable + 4 > len(data):
        raise ValueError(f"Streaming table vtable {vtable} outside payload {len(data)}")
    vtable_size = _u16(data, vtable)
    object_size = _u16(data, vtable + 2)
    if vtable_size < 4 or vtable_size % 2 or vtable + vtable_size > len(data):
        raise ValueError(f"Streaming table vtable size {vtable_size} is invalid at {vtable}")
    if object_size < 4 or table < 0 or table + object_size > len(data):
        raise ValueError(f"Streaming table object size {object_size} exceeds payload at {table}")
    fields = [
        _u16(data, vtable + 4 + index * 2)
        for index in range((vtable_size - 4) // 2)
    ]
    if any(value and (value < 4 or value >= object_size) for value in fields):
        raise ValueError(f"Streaming table field offset outside object: {fields}")
    return {
        "tableOffset": table,
        "vtableOffset": vtable,
        "vtableSize": vtable_size,
        "objectSize": object_size,
        "fieldCount": len(fields),
        "fields": fields,
        "presentFields": [index for index, value in enumerate(fields) if value],
    }


def _field_address(layout: dict[str, Any], index: int) -> int | None:
    fields = layout["fields"]
    if index < 0 or index >= len(fields) or not fields[index]:
        return None
    return int(layout["tableOffset"]) + int(fields[index])


def _bounded_vector(
    data: bytes,
    layout: dict[str, Any],
    index: int,
    element_width: int,
    label: str,
) -> tuple[int, int, int]:
    address = _field_address(layout, index)
    if address is None:
        raise ValueError(f"Streaming {label} is absent")
    if address + 4 > int(layout["tableOffset"]) + int(layout["objectSize"]):
        raise ValueError(f"Streaming {label} offset slot exceeds table object")
    relative = _u32(data, address)
    target = address + relative
    if relative == 0 or target <= address or target + 4 > len(data):
        raise ValueError(f"Streaming {label} vector target {target} outside payload")
    count = _u32(data, target)
    if element_width <= 0 or count > (len(data) - target - 4) // element_width:
        raise ValueError(
            f"Streaming {label} count {count} * width {element_width} exceeds payload"
        )
    end = target + 4 + count * element_width
    return target, count, end


def _parse_info_inner(data: bytes, root: dict[str, Any]) -> dict[str, Any]:
    """Exactly frame the selected-build anonymous StreamingChunkInfo graph."""

    ranges: list[tuple[int, int]] = [(0, 4)]
    shapes: Counter[tuple[int, int, tuple[int, ...]]] = Counter()
    row_count = 0

    def own_table(layout: dict[str, Any]) -> None:
        ranges.append(
            (
                int(layout["vtableOffset"]),
                int(layout["vtableOffset"]) + int(layout["vtableSize"]),
            )
        )
        ranges.append(
            (
                int(layout["tableOffset"]),
                int(layout["tableOffset"]) + int(layout["objectSize"]),
            )
        )

    def own_vector(
        layout: dict[str, Any], index: int, width: int, label: str
    ) -> tuple[int, int]:
        start, count, end = _bounded_vector(data, layout, index, width, label)
        ranges.append((start, end))
        return start + 4, count

    root_layout = {
        "tableOffset": root["rootOffset"],
        "vtableOffset": root["vtableOffset"],
        "vtableSize": root["vtableSize"],
        "objectSize": root["objectSize"],
        "fieldCount": root["fieldCount"],
        "fields": [
            _u16(data, root["vtableOffset"] + 4 + index * 2)
            for index in range(root["fieldCount"])
        ],
        "presentFields": root["presentFields"],
    }
    own_table(root_layout)
    root_shape = (
        root["fieldCount"],
        root["objectSize"],
        tuple(root["presentFields"]),
    )
    if root_shape == (4, 20, tuple(range(4))):
        own_vector(root_layout, 1, 4, "info field 1")
        own_vector(root_layout, 2, 4, "info field 2")
        body, count = own_vector(root_layout, 3, 4, "info field 3 table slots")
        expected_row = _INFO_STANDARD_ROW
        nested_vectors = ((1, 8),)
    elif root_shape == (3, 16, tuple(range(3))):
        own_vector(root_layout, 1, 12, "DevOnly info field 1")
        body, count = own_vector(root_layout, 2, 4, "DevOnly info field 2 table slots")
        expected_row = _INFO_DEVONLY_ROW
        nested_vectors = ((1, 4), (2, 4))
    else:  # Kept separate from the shallower root error for focused diagnostics.
        raise ValueError(f"Streaming info inner root shape {root_shape} is unsupported")

    for index in range(count):
        slot = body + index * 4
        relative = _u32(data, slot)
        target = slot + relative
        if relative == 0 or target <= slot:
            raise ValueError(f"Streaming info row {index} has invalid table target {target}")
        row = _table_layout(data, target)
        shape = (
            row["fieldCount"],
            row["objectSize"],
            tuple(row["presentFields"]),
        )
        if shape != expected_row:
            raise ValueError(
                f"Streaming info row {index} shape {shape}, expected {expected_row}"
            )
        shapes[shape] += 1
        own_table(row)
        for field_index, width in nested_vectors:
            own_vector(row, field_index, width, f"info row {index} field {field_index}")
        row_count += 1

    unique_ranges = sorted(set(ranges))
    for previous, current in zip(unique_ranges, unique_ranges[1:]):
        if current[0] < previous[1]:
            raise ValueError(
                "Streaming info structural ranges overlap: "
                f"{previous[0]}:{previous[1]} and {current[0]}:{current[1]}"
            )
    merged: list[list[int]] = []
    for start, end in unique_ranges:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    if not merged or merged[-1][1] != len(data):
        end = merged[-1][1] if merged else 0
        raise ValueError(f"Streaming info structural ranges end at {end}/{len(data)}")
    owned = sum(end - start for start, end in merged)
    gap_starts = (0, *(item[1] for item in merged))
    gap_ends = (*(item[0] for item in merged), len(data))
    for start, end in zip(gap_starts, gap_ends):
        if start < end and any(data[start:end]):
            raise ValueError(f"Streaming info nonzero byte outside structural ranges {start}:{end}")
    return {
        "status": "exact_anonymous",
        "rowCount": row_count,
        "rowShapes": [
            {
                "fieldCount": shape[0],
                "objectSize": shape[1],
                "presentFields": list(shape[2]),
                "count": count,
            }
            for shape, count in shapes.items()
        ],
        "ownedBytes": owned,
        "zeroAlignmentBytes": len(data) - owned,
        "structuralEnd": len(data),
    }


def _parse_paired_group_subgraph(
    data: bytes, root: dict[str, Any], family: str
) -> dict[str, Any]:
    """Frame one selected-build paired group subgraph without naming fields."""

    ranges: list[tuple[int, int, str, str]] = []
    shapes: Counter[tuple[int, int, tuple[int, ...]]] = Counter()
    descriptor_count = 0
    value_count = 0
    blob_bytes = 0

    def own(start: int, end: int, kind: str, label: str) -> None:
        if start < 0 or end < start or end > len(data):
            raise ValueError(
                f"Streaming {label} range {start}:{end} outside payload {len(data)}"
            )
        ranges.append((start, end, kind, label))

    def own_table(layout: dict[str, Any], label: str) -> None:
        own(
            int(layout["vtableOffset"]),
            int(layout["vtableOffset"]) + int(layout["vtableSize"]),
            "vtable",
            f"{label} vtable",
        )
        own(
            int(layout["tableOffset"]),
            int(layout["tableOffset"]) + int(layout["objectSize"]),
            "table",
            f"{label} table",
        )
        shape = (
            int(layout["fieldCount"]),
            int(layout["objectSize"]),
            tuple(int(value) for value in layout["presentFields"]),
        )
        shapes[shape] += 1

    root_layout = {
        "tableOffset": root["rootOffset"],
        "vtableOffset": root["vtableOffset"],
        "vtableSize": root["vtableSize"],
        "objectSize": root["objectSize"],
        "fieldCount": root["fieldCount"],
        "fields": root["fields"],
        "presentFields": root["presentFields"],
    }

    def table_vector(index: int, label: str) -> tuple[int, list[dict[str, Any]]]:
        start, count, end = _bounded_vector(data, root_layout, index, 4, label)
        own(start, end, "table-vector", label)
        body = start + 4
        tables = []
        for row_index in range(count):
            slot = body + row_index * 4
            relative = _u32(data, slot)
            target = slot + relative
            if relative == 0 or target <= slot:
                raise ValueError(
                    f"Streaming {label} row {row_index} has invalid table target {target}"
                )
            layout = _table_layout(data, target)
            own_table(layout, f"{label} row {row_index}")
            tables.append(layout)
        return count, tables

    id_group_count, id_wrappers = table_vector(
        6, f"{family} field 6 table slots"
    )
    data_group_count, data_groups = table_vector(
        7, f"{family} field 7 table slots"
    )
    if id_group_count != data_group_count:
        raise ValueError(
            f"Streaming {family} paired group count mismatch: "
            f"{id_group_count}/{data_group_count}"
        )

    for index, (id_wrapper, group) in enumerate(zip(id_wrappers, data_groups)):
        id_shape = (
            id_wrapper["fieldCount"],
            id_wrapper["objectSize"],
            tuple(id_wrapper["presentFields"]),
        )
        if id_shape != _INIT_ID_WRAPPER:
            raise ValueError(
                f"Streaming {family} field 6 row {index} shape {id_shape}, "
                f"expected {_INIT_ID_WRAPPER}"
            )
        ids_start, group_value_count, ids_end = _bounded_vector(
            data, id_wrapper, 0, 4, f"{family} field 6 row {index} values"
        )
        own(
            ids_start,
            ids_end,
            "u32-vector",
            f"{family} field 6 row {index} values",
        )

        group_shape = (
            group["fieldCount"],
            group["objectSize"],
            tuple(group["presentFields"]),
        )
        if group_shape not in _INIT_GROUP_ROWS:
            raise ValueError(
                f"Streaming {family} field 7 row {index} shape {group_shape}, "
                f"expected one of {sorted(_INIT_GROUP_ROWS)}"
            )
        count_address = _field_address(group, 1)
        if count_address is None:
            raise ValueError(
                f"Streaming {family} field 7 row {index} count is absent"
            )
        if count_address + 4 > int(group["tableOffset"]) + int(group["objectSize"]):
            raise ValueError(
                f"Streaming {family} field 7 row {index} count slot exceeds table object"
            )
        inline_count = _u32(data, count_address)
        if inline_count != group_value_count:
            raise ValueError(
                f"Streaming {family} row {index} value count mismatch: "
                f"{group_value_count}/{inline_count}"
            )

        descriptor_start, row_descriptor_count, descriptor_end = _bounded_vector(
            data, group, 3, 8, f"{family} field 7 row {index} descriptors"
        )
        own(
            descriptor_start,
            descriptor_end,
            "descriptor-vector",
            f"{family} field 7 row {index} descriptors",
        )
        descriptor_body = descriptor_start + 4
        expected_blob_bytes = 0
        for descriptor_index in range(row_descriptor_count):
            _anonymous_id, stride, reserved = struct.unpack_from(
                "<HHI", data, descriptor_body + descriptor_index * 8
            )
            if reserved:
                raise ValueError(
                    f"Streaming {family} row {index} descriptor {descriptor_index} "
                    f"reserved value {reserved}"
                )
            if stride == 0:
                raise ValueError(
                    f"Streaming {family} row {index} descriptor {descriptor_index} "
                    "has zero stride"
                )
            expected_blob_bytes += inline_count * stride

        wrapper_address = _field_address(group, 4)
        if wrapper_address is None:
            raise ValueError(
                f"Streaming {family} field 7 row {index} blob wrapper is absent"
            )
        if wrapper_address + 4 > int(group["tableOffset"]) + int(
            group["objectSize"]
        ):
            raise ValueError(
                f"Streaming {family} field 7 row {index} blob wrapper slot exceeds table object"
            )
        wrapper_relative = _u32(data, wrapper_address)
        wrapper_target = wrapper_address + wrapper_relative
        if wrapper_relative == 0 or wrapper_target <= wrapper_address:
            raise ValueError(
                f"Streaming {family} field 7 row {index} has invalid blob wrapper "
                f"target {wrapper_target}"
            )
        blob_wrapper = _table_layout(data, wrapper_target)
        own_table(blob_wrapper, f"{family} field 7 row {index} blob wrapper")
        blob_wrapper_shape = (
            blob_wrapper["fieldCount"],
            blob_wrapper["objectSize"],
            tuple(blob_wrapper["presentFields"]),
        )
        if blob_wrapper_shape != _INIT_ID_WRAPPER:
            raise ValueError(
                f"Streaming {family} field 7 row {index} blob wrapper shape "
                f"{blob_wrapper_shape}, expected {_INIT_ID_WRAPPER}"
            )
        blob_start, actual_blob_bytes, blob_end = _bounded_vector(
            data, blob_wrapper, 0, 1, f"{family} field 7 row {index} blob"
        )
        own(
            blob_start,
            blob_end,
            "byte-vector",
            f"{family} field 7 row {index} blob",
        )
        if actual_blob_bytes != expected_blob_bytes:
            raise ValueError(
                f"Streaming {family} row {index} blob length mismatch: "
                f"{actual_blob_bytes}/{expected_blob_bytes}"
            )
        descriptor_count += row_descriptor_count
        value_count += inline_count
        blob_bytes += actual_blob_bytes

    ordered = sorted(ranges)
    reused_vtables = 0
    for previous, current in zip(ordered, ordered[1:]):
        if current[0] >= previous[1]:
            continue
        same_vtable = (
            previous[:3] == current[:3]
            and previous[2] == "vtable"
        )
        if same_vtable:
            reused_vtables += 1
            continue
        raise ValueError(
            f"Streaming {family} subgraph structural ranges overlap: "
            f"{previous[3]}={previous[0]}:{previous[1]} and "
            f"{current[3]}={current[0]}:{current[1]}"
        )
    unique_ranges = {(start, end, kind) for start, end, kind, _label in ranges}
    return {
        "status": "exact_anonymous_subgraph",
        "pairedGroupCount": id_group_count,
        "valueCount": value_count,
        "descriptorCount": descriptor_count,
        "blobBytes": blob_bytes,
        "ownedBytes": sum(end - start for start, end, _kind in unique_ranges),
        "rangeCount": len(unique_ranges),
        "reusedVtableReferences": reused_vtables,
        "tableShapes": [
            {
                "fieldCount": shape[0],
                "objectSize": shape[1],
                "presentFields": list(shape[2]),
                "count": count,
            }
            for shape, count in shapes.items()
        ],
        "fieldStatus": "anonymous-structural-only",
        "wholeFileStatus": "partial",
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
    corpus uses this only for DevOnly files).  Init/Streaming bytes after the
    root table remain explicitly opaque.  Info files additionally return an
    exact anonymous inner table/vector framing.
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
    result = {
        "kind": kind,
        "encoding": encoding,
        "sourceBytes": len(packed),
        "decodedBytes": len(clear),
        "declaredDecodedBytes": declared_decoded_size,
        "root": layout,
    }
    if kind == "info":
        result["anonymousInner"] = _parse_info_inner(clear, layout)
    elif kind in {"init", "streaming"}:
        result["anonymousGroupSubgraph"] = _parse_paired_group_subgraph(
            clear, layout, kind
        )
    return result


__all__ = ["parse_streaming_file"]
