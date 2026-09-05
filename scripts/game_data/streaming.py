"""Strict framing checks for the Endfield block-15 Streaming family.

This module separates byte framing from field semantics. It does not
assign names or meanings to FlatBuffer fields.  The current build contains
two length-prefixed inverted-LZ4 families (``InitChunkData`` and
``StreamingChunkData``) and a raw ``StreamingChunkInfo`` family.  The latter's
selected-build table/vector graph is framed exactly while every field remains
anonymous. Both data families additionally expose three exact anonymous
subgraphs: the paired groups under root fields 6/7, the parallel first-level
vectors/rows under root fields 3/4/5, and the root-field-2 vector, its direct
tables/vtables, and the anonymous width-4 vectors reached through row field 5.
For parallel rows that expose field 5, only its empty count prefix is framed;
the element width remains unresolved. Field 3 reaches a nested table with
equal-count width-4/1/4 vectors. Marker 17 elements frame two anonymous
wrappers and a counted byte range; their byte contents and all other element
targets remain opaque. The marker association is not a proven union registry.
Marker 15 slots additionally require nonzero forward offsets to readable
payload positions. This authenticates reference bounds only: no target bytes
are claimed as owned and no element width or object type is selected.
For the selected build, hash-gated native accessors and consumers establish row
fields 0--2 as single 32-bit loads, field 3 as two signed 32-bit loads, field 4
as six 32-bit floating-point loads, and every field-5 vector element as a
32-bit hash-table lookup key. The values and names remain anonymous. A
small DevOnly subset is raw despite sharing the first two path families, so the
decoder accepts raw only after independently validating the observed root
shape.
"""

from __future__ import annotations

import hashlib
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
_FIELD2_STREAMING_ROWS = {
    (6, 40, (3, 4, 5)): (0, 0, 0, 4, 12, 36),
    (6, 44, (0, 3, 4, 5)): (4, 0, 0, 8, 16, 40),
    (6, 48, (0, 1, 3, 4, 5)): (4, 8, 0, 12, 20, 44),
    (6, 44, (1, 3, 4, 5)): (0, 4, 0, 8, 16, 40),
    (6, 44, (2, 3, 4, 5)): (0, 0, 4, 8, 16, 40),
    (6, 48, (0, 2, 3, 4, 5)): (4, 0, 8, 12, 20, 44),
    (6, 52, (0, 1, 2, 3, 4, 5)): (4, 8, 12, 16, 24, 48),
}
_FIELD2_STREAMING_SLOT_SPANS = (4, 4, 4, 8, 24, 4)


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


def _info_slot_partition(layout, widths, label):
    """Partition object slots by physical boundaries, not declaration order."""
    fields = layout['fields']
    if len(fields) != len(widths) or len(set(fields)) != len(fields) or min(fields, default=0) != 4:
        raise ValueError(f'Streaming {label} at {layout["tableOffset"]}: expected unique fields partitioning object from +4, actual {fields}')
    spans = []
    for index, start in enumerate(fields):
        end = min([value for value in fields if value > start] + [layout['objectSize']])
        if end-start != widths[index]:
            raise ValueError(f'Streaming {label} field {index} at {layout["tableOffset"]+start}: expected slot width {widths[index]}, actual {end-start}')
        spans.append(dict(fieldIndex=index, start=layout['tableOffset']+start, end=layout['tableOffset']+end))
    return spans


def _parse_info_inner(data: bytes, root: dict[str, Any]) -> dict[str, Any]:
    """Exactly frame the selected-build anonymous StreamingChunkInfo graph."""

    ranges: list[tuple[int, int]] = [(0, 4)]
    shapes: Counter[tuple[int, int, tuple[int, ...]]] = Counter()
    row_count = 0
    catalog_rows = []
    slot_rows = []

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
    root_slots = _info_slot_partition(root_layout, (4,) * root["fieldCount"], "info root")
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
        slots = _info_slot_partition(row, (8,) + (4,) * (row["fieldCount"]-1), f"info row {index}")
        vectors = []
        for field_index, width in nested_vectors:
            vector_body, vector_count = own_vector(row, field_index, width, f"info row {index} field {field_index}")
            vectors.append(dict(fieldIndex=field_index, start=vector_body-4,
                                end=vector_body+vector_count*width, count=vector_count, elementWidth=width))
            if expected_row == _INFO_STANDARD_ROW:
                field0 = slots[0]['start']
                for element in range(vector_count):
                    address = vector_body + element*8
                    offsets = [field0, field0+4, address, address+4]
                    catalog_rows.append(dict(rowIndex=index, elementIndex=element,
                                             rowOffset=target, offsets=offsets,
                                             values=[_i32(data, offset) for offset in offsets]))
        slot_rows.append(dict(rowIndex=index, rowOffset=target, slots=slots, vectors=vectors))
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
        "catalogProjection": {
            "status": "standard-four-word-projection" if expected_row == _INFO_STANDARD_ROW else "unsupported-legacy-three-field-root",
            "rows": catalog_rows,
            "slotPartitions": {"root": root_slots, "rows": slot_rows},
            "evidenceLevel": "structural-only",
            "boundary": "Four anonymous int32 words from one bounded row-field0 pair and one bounded width8 vector element. No names, spatial meaning, runtime selection or legacy Cartesian product is inferred.",
        },
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


def _bounded_anonymous_target(data: bytes, slot: int, label: str) -> int:
    """Bound an anonymous uoffset without assuming its target representation."""
    relative = _u32(data, slot)
    target = slot + relative
    if relative == 0 or target >= len(data):
        raise ValueError(
            f"Streaming {label} at slot {slot}: expected nonzero forward "
            f"target below EOF {len(data)}, actual relative {relative}, target {target}"
        )
    return target


def _nested_reference_ranges(
    data: bytes, slot: int, marker: int, label: str
) -> tuple[list[tuple[int, int, str, str]], int]:
    """Observed marker-17 framing only; not a proven union/type registry.

    17 has two wrappers and an opaque counted byte range. Other marker
    values must be left opaque by the caller, not searched for plausible tables.
    """
    if marker != 17:
        raise ValueError(f"Streaming {label}: unsupported marker {marker}")
    ranges = []
    for depth in range(2):
        relative = _u32(data, slot)
        target = slot + relative
        if relative == 0 or target + 4 > len(data):
            raise ValueError(
                f"Streaming {label} wrapper {depth} at slot {slot}: expected "
                f"forward bounded target, actual {target}, EOF {len(data)}"
            )
        table = _table_layout(data, target)
        actual = (table["fieldCount"], table["objectSize"], table["fields"])
        if actual not in ((1, 8, [4]), (1, 10, [4])):
            raise ValueError(
                f"Streaming {label} wrapper {depth} at {target}: expected "
                f"single field at +4, object size 8 or 10, actual {actual}"
            )
        ranges.extend([
            (table["vtableOffset"], table["vtableOffset"] + table["vtableSize"], "vtable", label),
            (target, target + table["objectSize"], "table", label),
        ])
        slot = target + 4
    try:
        start, count, end = _bounded_vector(data, table, 0, 1, label)
    except ValueError as exc:
        raise ValueError(f"{exc}; reference slot {slot}, actual EOF {len(data)}") from exc
    ranges.append((start, end, "length-prefixed-byte-range", label))
    return ranges, count


def _selector5_key_ranges(
    data: bytes, starts: dict[int, int], count: int, label: str,
) -> dict[str, Any]:
    """Join one table's unique keys to bounded candidate read spans.

    This is not native execution or a record-width claim. In particular the
    runtime dispatch marker and later row pointer originate in different
    roots. Reject duplicates as ambiguous even though native insertion keeps
    the first index; our evidence contract requires a unique serialized join.
    """
    for field, width in ((3, 4), (4, 1), (5, 4)):
        start = starts[field]
        actual = _u32(data, start)
        if actual != count or count > (len(data) - start - 4) // width:
            raise ValueError(f"Streaming {label} field {field} at {start}: expected bounded count {count}, actual {actual}, EOF {len(data)}")
    indices = {}
    for index in range(count):
        offset = starts[3] + 4 + index * 4
        key = _u32(data, offset)
        if key in indices:
            raise ValueError(f"Streaming {label} key at {offset}: expected unique key, actual ambiguous {key:#010x} at indices {indices[key]}/{index}")
        indices[key] = index

    def resolve(key: int, marker: int, width: int) -> dict[str, int]:
        if key not in indices:
            raise ValueError(f"Streaming {label} keys at {starts[3]}: expected key {key:#010x}, actual missing")
        index = indices[key]
        marker_offset = starts[4] + 4 + index
        actual = data[marker_offset]
        if actual != marker:
            raise ValueError(f"Streaming {label} marker at {marker_offset}: expected {marker} for key {key:#010x}, actual {actual}")
        slot = starts[5] + 4 + index * 4
        target = _bounded_anonymous_target(data, slot, label)
        if width > len(data) - target:
            raise ValueError(f"Streaming {label} target at {target}: expected {width} readable bytes, actual {len(data)-target}")
        return dict(key=key, index=index, slot=slot, start=target, end=target+width)

    if 0x05020000 not in indices:
        return dict(status='unresolved-missing-count-key', countValue=None,
                    countRange=None, elementRanges=[])
    scalar = resolve(0x05020000, 2, 4)
    value = _i32(data, scalar['start'])
    # The selected unique-key profile supports at most one 16-bit index lane.
    # Native OR packing outside that lane is not a one-to-one key encoding.
    if value < 0 or value > min(count, 65536):
        raise ValueError(f"Streaming {label} count at {scalar['start']}: expected 0..{min(count, 65536)}, actual {value}")
    elements = [resolve(0x05010000 | index, 15, 16) for index in range(value)]
    return dict(status='exact-unique-key-candidate-read-ranges',
                countValue=value, countRange=scalar, elementRanges=elements)


def _parse_parallel_root_subgraph(
    data: bytes, root: dict[str, Any], family: str
) -> dict[str, Any]:
    """Frame root fields 3/4/5 without interpreting their values or children.

    The selected corpus proves three equal-length first-level vectors. Field 5
    contains table offsets; each row's field 0 reaches a length-prefixed byte
    range followed by zero. Rows with field 5 also carry an empty counted
    vector and field 3 reaches a nested table whose fields 3/4/5 are equal-
    count width-4/width-1/width-4 vectors. Nested marker 17 additionally
    bounds two-wrapper byte ranges; other element targets remain opaque.
    This marker association is structural, not an independently proven union.
    Field 0's physical
    representation is compatible with both a FlatBuffer string and a byte
    vector followed by alignment, so this parser deliberately keeps the
    serialized type ambiguous.
    """

    ranges: list[tuple[int, int, str, str]] = []
    shapes: Counter[tuple[int, int, tuple[int, ...]]] = Counter()
    byte_values: Counter[int] = Counter()
    marker_shapes: Counter[tuple[int, int, int, tuple[int, ...]]] = Counter()
    referenced_bytes = 0
    outer_field5_vectors = 0
    outer_field5_values = 0
    nested_tables = 0
    nested_shapes: Counter[tuple[int, int, tuple[int, ...]]] = Counter()
    nested_parallel_rows = 0
    nested_field3_values = 0
    nested_field4_values = 0
    nested_field5_values = 0
    nested_markers: Counter[int] = Counter()
    nested_framed: Counter[int] = Counter()
    nested_bytes: Counter[int] = Counter()
    marker15_references = 0
    marker15_targets_digest = hashlib.sha256()
    marker15_prefix_fits: Counter[int] = Counter()
    # These are probes, not an exhaustive registry or selectable layouts.
    marker15_probe_widths = (1, 2, 4, 8, 12, 16, 20, 24, 32, 48, 64)
    selector5_rows = []
    marker17_rows = []
    selector5_ranges = []
    row_field0_digest = hashlib.sha256()

    def own(start: int, end: int, kind: str, label: str) -> None:
        if start < 0 or end < start or end > len(data):
            raise ValueError(
                f"Streaming {label} range {start}:{end} outside payload {len(data)}"
            )
        ranges.append((start, end, kind, label))

    root_layout = {
        "tableOffset": root["rootOffset"],
        "vtableOffset": root["vtableOffset"],
        "vtableSize": root["vtableSize"],
        "objectSize": root["objectSize"],
        "fieldCount": root["fieldCount"],
        "fields": root["fields"],
        "presentFields": root["presentFields"],
    }

    field3_start, field3_count, field3_end = _bounded_vector(
        data, root_layout, 3, 4, f"{family} field 3"
    )
    own(field3_start, field3_end, "width-4-vector", f"{family} field 3")
    field4_start, field4_count, field4_end = _bounded_vector(
        data, root_layout, 4, 1, f"{family} field 4"
    )
    own(field4_start, field4_end, "byte-vector", f"{family} field 4")
    byte_values.update(data[field4_start + 4 : field4_end])
    field5_start, field5_count, field5_end = _bounded_vector(
        data, root_layout, 5, 4, f"{family} field 5 table slots"
    )
    own(
        field5_start,
        field5_end,
        "table-vector",
        f"{family} field 5 table slots",
    )
    if (field3_count, field4_count, field5_count) != (
        field3_count,
        field3_count,
        field3_count,
    ):
        raise ValueError(
            f"Streaming {family} parallel root count mismatch: "
            f"field 3={field3_count}, field 4={field4_count}, "
            f"field 5={field5_count}"
        )

    field5_body = field5_start + 4
    for index in range(field5_count):
        slot = field5_body + index * 4
        relative = _u32(data, slot)
        target = slot + relative
        if relative == 0 or target <= slot:
            raise ValueError(
                f"Streaming {family} field 5 row {index} has invalid table "
                f"target {target} at slot {slot}"
            )
        row = _table_layout(data, target)
        own(
            int(row["vtableOffset"]),
            int(row["vtableOffset"]) + int(row["vtableSize"]),
            "vtable",
            f"{family} field 5 row {index} vtable",
        )
        own(
            int(row["tableOffset"]),
            int(row["tableOffset"]) + int(row["objectSize"]),
            "table",
            f"{family} field 5 row {index} table",
        )
        shape = (
            int(row["fieldCount"]),
            int(row["objectSize"]),
            tuple(int(value) for value in row["presentFields"]),
        )
        shapes[shape] += 1

        # Join by the exact vector index, never by equal marginal counts.
        marker_shapes[(data[field4_start + 4 + index], *shape)] += 1
        field0 = _field_address(row, 0)
        if field0 is None:
            raise ValueError(
                f"Streaming {family} field 5 row {index} field 0 is absent"
            )
        if field0 + 4 > int(row["tableOffset"]) + int(row["objectSize"]):
            raise ValueError(
                f"Streaming {family} field 5 row {index} field 0 slot "
                "exceeds table object"
            )
        value_relative = _u32(data, field0)
        value_target = field0 + value_relative
        if (
            value_relative == 0
            or value_target <= field0
            or value_target + 4 > len(data)
        ):
            raise ValueError(
                f"Streaming {family} field 5 row {index} field 0 target "
                f"{value_target} from slot {field0} outside payload {len(data)}"
            )
        value_length = _u32(data, value_target)
        value_end = value_target + 4 + value_length
        if value_end >= len(data):
            raise ValueError(
                f"Streaming {family} field 5 row {index} field 0 length "
                f"{value_length} ends at {value_end}, actual EOF {len(data)}"
            )
        if data[value_end] != 0:
            raise ValueError(
                f"Streaming {family} field 5 row {index} field 0 expected "
                f"following zero at offset {value_end}, actual {data[value_end]}"
            )
        try:
            data[value_target + 4 : value_end].decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"Streaming {family} field 5 row {index} field 0 is not "
                f"UTF-8-compatible at offset {value_target + 4}"
            ) from exc
        own(
            value_target,
            value_end,
            "length-prefixed-byte-range",
            f"{family} field 5 row {index} field 0",
        )
        referenced_bytes += value_length
        # Include each length before its bytes so concatenation cannot erase
        # row boundaries. These are ordered anonymous values, not name ids.
        row_field0_digest.update(data[value_target:value_end])

        # Six-field rows expose two additional references. The selected
        # corpus closes the immediate ranges without assigning a union or
        # element type: row field 5 has only an empty count prefix in the
        # corpus, while row field 3 reaches a nested table with three equal-
        # count parallel vectors.
        row_field5 = _field_address(row, 5)
        if row_field5 is not None:
            ordered_addresses = sorted(
                int(address)
                for field_index in row["presentFields"]
                if (address := _field_address(row, int(field_index))) is not None
            )
            slot_spans = {
                address: (
                    ordered_addresses[position + 1]
                    if position + 1 < len(ordered_addresses)
                    else int(row["tableOffset"]) + int(row["objectSize"])
                )
                - address
                for position, address in enumerate(ordered_addresses)
            }
            row_field3 = _field_address(row, 3)
            if row_field3 is None:
                raise ValueError(
                    f"Streaming {family} field 5 row {index} has field 5 "
                    "without field 3"
                )
            for field_index, address in ((3, row_field3), (5, row_field5)):
                if slot_spans.get(int(address)) != 4:
                    raise ValueError(
                        f"Streaming {family} field 5 row {index} field "
                        f"{field_index} expected 4-byte reference slot, actual "
                        f"{slot_spans.get(int(address))}"
                    )

            field5_vector, field5_value_count, field5_vector_end = _bounded_vector(
                data,
                row,
                5,
                1,  # Lower bound only; a nonzero count is rejected below.
                f"{family} field 5 row {index} field 5",
            )
            if field5_value_count != 0:
                raise ValueError(
                    f"Streaming {family} field 5 row {index} field 5 at "
                    f"{field5_vector}: expected empty count 0 (element width "
                    f"unresolved), actual {field5_value_count}"
                )
            own(
                field5_vector,
                field5_vector_end,
                "empty-count-prefix",
                f"{family} field 5 row {index} field 5",
            )
            outer_field5_vectors += 1
            outer_field5_values += field5_value_count

            nested_relative = _u32(data, row_field3)
            nested_target = row_field3 + nested_relative
            if (
                nested_relative == 0
                or nested_target <= row_field3
                or nested_target + 4 > len(data)
            ):
                raise ValueError(
                    f"Streaming {family} field 5 row {index} field 3 table "
                    f"target {nested_target} outside payload {len(data)}"
                )
            nested = _table_layout(data, nested_target)
            own(
                int(nested["vtableOffset"]),
                int(nested["vtableOffset"]) + int(nested["vtableSize"]),
                "vtable",
                f"{family} field 5 row {index} field 3 vtable",
            )
            own(
                int(nested["tableOffset"]),
                int(nested["tableOffset"]) + int(nested["objectSize"]),
                "table",
                f"{family} field 5 row {index} field 3 table",
            )
            nested_shape = (
                int(nested["fieldCount"]),
                int(nested["objectSize"]),
                tuple(int(value) for value in nested["presentFields"]),
            )
            nested_shapes[nested_shape] += 1
            nested_vectors = []
            nested_starts = {}
            for nested_field, width in ((3, 4), (4, 1), (5, 4)):
                vector_start, vector_count, vector_end = _bounded_vector(
                    data,
                    nested,
                    nested_field,
                    width,
                    (
                        f"{family} field 5 row {index} field 3 nested "
                        f"field {nested_field}"
                    ),
                )
                own(
                    vector_start,
                    vector_end,
                    f"width-{width}-vector",
                    (
                        f"{family} field 5 row {index} field 3 nested "
                        f"field {nested_field}"
                    ),
                )
                nested_vectors.append((nested_field, vector_count))
                nested_starts[nested_field] = vector_start
            nested_counts = tuple(count for _field, count in nested_vectors)
            if len(set(nested_counts)) != 1:
                raise ValueError(
                    f"Streaming {family} field 5 row {index} field 3 nested "
                    f"parallel count mismatch: field 3={nested_counts[0]}, "
                    f"field 4={nested_counts[1]}, field 5={nested_counts[2]}"
                )
            nested_tables += 1
            nested_parallel_rows += nested_counts[0]
            nested_field3_values += nested_counts[0]
            nested_field4_values += nested_counts[1]
            nested_field5_values += nested_counts[2]
            selector_slot = _field_address(row, 2)
            if (data[field4_start + 4 + index] == 2 and selector_slot is not None
                    and slot_spans.get(selector_slot, 0) < 4):
                raise ValueError(
                    f"Streaming {family} selector field2 at {selector_slot}: "
                    f"expected at least 4 slot bytes, actual {slot_spans.get(selector_slot, 0)}"
                )
            if (data[field4_start + 4 + index] == 2 and selector_slot is not None
                    and _u32(data, selector_slot) & 255 == 5):
                joined = _selector5_key_ranges(
                    data, nested_starts, nested_counts[0],
                    f"{family} selector5 row {index}",
                )
                joined.update(rowIndex=index, rowOffset=int(row['tableOffset']),
                              nestedTableOffset=nested_target)
                selector5_rows.append(joined)
                if joined['countRange'] is not None:
                    selector5_ranges.extend((r['start'], r['end'], 'candidate-read-span')
                                            for r in [joined['countRange'], *joined['elementRanges']])
            key_counts = None
            for element_index in range(nested_counts[0]):
                marker = data[nested_starts[4] + 4 + element_index]
                nested_markers[marker] += 1
                if marker == 15:
                    slot = nested_starts[5] + 4 + element_index * 4
                    target = _bounded_anonymous_target(
                        data, slot,
                        f"{family} field 5 row {index} nested element {element_index} marker 15",
                    )
                    marker15_references += 1
                    marker15_targets_digest.update(struct.pack('<QQ', slot, target))
                    for width in marker15_probe_widths:
                        if width <= len(data) - target:
                            marker15_prefix_fits[width] += 1
                    continue
                if marker != 17:
                    continue
                label = (
                    f"{family} field 5 row {index} nested element {element_index} "
                    f"marker {marker}"
                )
                child_ranges, byte_count = _nested_reference_ranges(
                    data, nested_starts[5] + 4 + element_index * 4, marker, label
                )
                for child_range in child_ranges:
                    own(*child_range)
                # Record identity in the same bounded directory traversal. A
                # duplicate key is ambiguous even if its other marker differs.
                if key_counts is None:
                    key_counts = Counter(
                        _u32(data, nested_starts[3] + 4 + ordinal * 4)
                        for ordinal in range(nested_counts[0])
                    )
                key_offset = nested_starts[3] + 4 + element_index * 4
                key = _u32(data, key_offset)
                root_marker = data[field4_start + 4 + index]
                selector = (_u32(data, selector_slot)
                            if root_marker == 2 and selector_slot is not None else None)
                marker17_rows.append({
                    "outerRowIndex": index, "outerRowOffset": int(row["tableOffset"]),
                    "rootMarker": root_marker,
                    "rowSelectorU32": selector,
                    "rowSelectorLowByte": selector & 255 if selector is not None else None,
                    "nestedTableOffset": nested_target,
                    "nestedElementCount": nested_counts[0], "elementIndex": element_index,
                    "key": key, "keyHex": f"{key:08X}", "keyOffset": key_offset,
                    "keyOccurrenceCountInTable": key_counts[key],
                    "keyStatus": "unique" if key_counts[key] == 1 else "ambiguous",
                    "marker": marker, "markerOffset": nested_starts[4] + 4 + element_index,
                    "targetSlotOffset": nested_starts[5] + 4 + element_index * 4,
                    "byteCount": byte_count,
                    "wrapperAndByteRanges": [
                        {"start": start, "end": end, "kind": kind}
                        for start, end, kind, _label in child_ranges
                    ],
                })
                nested_framed[marker] += 1
                nested_bytes[marker] += byte_count

    # FlatBuffers may reuse vtables and referenced objects. Exact duplicate
    # ranges are references, not overlaps; every non-identical overlap fails.
    unique_ranges = sorted(
        {(start, end, kind) for start, end, kind, _label in ranges}
    )
    # Candidate reads may not collide with authenticated structure. They stay
    # separate from owned bytes: a native load width is not object extent.
    checked_ranges = sorted(set(unique_ranges + selector5_ranges)) if selector5_ranges else []
    for previous, current in zip(checked_ranges, checked_ranges[1:]):
        if current[0] < previous[1]:
            raise ValueError(f"Streaming {family} selector5 range at {current[0]}: expected no overlap, actual {previous} / {current}")
    reused_references = len(ranges) - len(unique_ranges)
    for previous, current in zip(unique_ranges, unique_ranges[1:]):
        if current[0] < previous[1]:
            raise ValueError(
                f"Streaming {family} parallel subgraph structural ranges "
                f"overlap: {previous[0]}:{previous[1]} ({previous[2]}) and "
                f"{current[0]}:{current[1]} ({current[2]})"
            )
    return {
        "status": "exact_anonymous_subgraph",
        "parallelCount": field3_count,
        "orderedRootWitness": {
            "rowCount": field3_count,
            "field3VectorSha256": hashlib.sha256(data[field3_start:field3_end]).hexdigest().upper(),
            "field4VectorSha256": hashlib.sha256(data[field4_start:field4_end]).hexdigest().upper(),
            "rowField0ValuesSha256": row_field0_digest.hexdigest().upper(),
            "field3DuplicateCount": field3_count - len({
                _u32(data, field3_start + 4 + index * 4) for index in range(field3_count)
            }),
            "encoding": "vectors include u32 count; row-field0 digest concatenates u32 length and exact bytes in row order",
        },
        "marker17KeyDirectory": {
            "status": "exact-structural-directory",
            "evidenceLevel": "structural-only", "rows": marker17_rows,
            "targetOwnedBytes": 0,
            "scope": "table-local keys; offsets in decoded logical-file bytes; byte range includes u32 count prefix",
            "bodyStatus": "opaque", "runtimeSelectionStatus": "unresolved",
        },
        "selector5KeyRangeJoin": {
            "status": "exact-unique-key-candidate-read-ranges",
            "evidenceLevel": "structural-only",
            "scope": "same-file root marker 2 and row.field2 low byte 5; not cross-root runtime dispatch",
            "rows": selector5_rows,
            "targetOwnedBytes": 0,
            "recordExtentStatus": "unresolved",
        },
        "fieldWidths": {"3": 4, "4": 1, "5": 4},
        "field4ByteValueCounts": dict(sorted(byte_values.items())),
        "field4ByteToRowShapes": [
            {"marker": key[0], "fieldCount": key[1], "objectSize": key[2],
             "presentFields": list(key[3]), "count": count}
            for key, count in sorted(marker_shapes.items())
        ],
        "field5RowCount": field5_count,
        "field5RowShapes": [
            {
                "fieldCount": shape[0],
                "objectSize": shape[1],
                "presentFields": list(shape[2]),
                "count": count,
            }
            for shape, count in shapes.items()
        ],
        "field5Field0ReferenceCount": field5_count,
        "field5Field0ReferencedBytes": referenced_bytes,
        "field5Field0Representation": "ambiguous",
        "field5Field0RepresentationCandidates": [
            "flatbuffer-string",
            "byte-vector-with-following-zero",
        ],
        "field5Field5VectorCount": outer_field5_vectors,
        "field5Field5ValueCount": outer_field5_values,
        "field5Field5Representation": "empty-count-prefix-element-width-unresolved",
        "field5Field3NestedTableCount": nested_tables,
        "field5Field3NestedTableShapes": [
            {
                "fieldCount": shape[0],
                "objectSize": shape[1],
                "presentFields": list(shape[2]),
                "count": count,
            }
            for shape, count in nested_shapes.items()
        ],
        "field5Field3NestedParallelWidths": {"3": 4, "4": 1, "5": 4},
        "field5Field3NestedParallelCount": nested_parallel_rows,
        "field5Field3NestedFieldValueCounts": {
            "3": nested_field3_values,
            "4": nested_field4_values,
            "5": nested_field5_values,
        },
        "field5Field3NestedElementStatus": "partial-marker17-anonymous-framing",
        "nestedElementMarkerCounts": dict(sorted(nested_markers.items())),
        "nestedElementFramedCounts": dict(sorted(nested_framed.items())),
        "nestedElementByteCounts": dict(sorted(nested_bytes.items())),
        "nestedElementOpaqueCount": sum(nested_markers.values()) - sum(nested_framed.values()),
        "nestedMarker17Representation": "two-wrappers-to-opaque-counted-bytes",
        "nestedMarker15References": {
            "status": "bounded-anonymous-forward-uoffset-targets",
            "evidenceLevel": "structural-only",
            "count": marker15_references,
            "orderedSlotTargetSha256": marker15_targets_digest.hexdigest().upper(),
            "widthStatus": "unresolved",
            "probeWidthFitCounts": dict(sorted(marker15_prefix_fits.items())),
            "probeWidths": list(marker15_probe_widths),
            "probeMeaning": "available-file-bytes-only-not-layout-candidates-or-ownership",
            "targetOwnedBytes": 0,
            "nativeWidthJoin": "unresolved-context-table-and-marker-join",
        },
        "nestedMarkerMeaning": "unresolved-not-a-proven-union-registry",
        "ownedBytes": sum(end - start for start, end, _kind in unique_ranges),
        "rangeCount": len(unique_ranges),
        "reusedReferences": reused_references,
        "fieldStatus": "anonymous-structural-only",
        "wholeFileStatus": "partial",
    }


def _parse_field2_terminal_subgraph(
    data: bytes,
    root: dict[str, Any],
    family: str,
    *,
    native_layout_validated: bool,
) -> dict[str, Any]:
    """Frame the selected-build root-field-2 terminal subgraph to EOF.

    Row field 5 is an exact count-prefixed vector reference with anonymous
    width-4 elements. Selected-build native accessors and consumers establish
    the stored representations of row fields 0--5, but their names, signedness,
    key namespace, and meanings remain unresolved. The current-corpus gate
    independently revalidates that native contract before publishing these
    representations as current evidence.
    """

    root_layout = {
        "tableOffset": root["rootOffset"],
        "vtableOffset": root["vtableOffset"],
        "vtableSize": root["vtableSize"],
        "objectSize": root["objectSize"],
        "fieldCount": root["fieldCount"],
        "fields": root["fields"],
        "presentFields": root["presentFields"],
    }
    vector_start, row_count, vector_end = _bounded_vector(
        data, root_layout, 2, 4, f"{family} field 2 table slots"
    )
    ranges: list[tuple[int, int, str, str]] = [
        (vector_start, vector_end, "table-vector", f"{family} field 2 table slots")
    ]
    layouts: Counter[
        tuple[int, int, tuple[int, ...], tuple[int, ...]]
    ] = Counter()
    child_vector_count = 0
    child_value_count = 0
    child_ranges: list[tuple[int, int, str]] = []
    slot_presence: Counter[int] = Counter()
    slot_span_bytes: Counter[int] = Counter()
    row_value_records: list[dict[str, Any]] = []

    body = vector_start + 4
    for index in range(row_count):
        slot = body + index * 4
        relative = _u32(data, slot)
        target = slot + relative
        if relative == 0 or target <= slot or target + 4 > len(data):
            raise ValueError(
                f"Streaming {family} field 2 row {index} table target "
                f"{target} from slot {slot} outside payload {len(data)}"
            )
        row = _table_layout(data, target)
        shape = (
            int(row["fieldCount"]),
            int(row["objectSize"]),
            tuple(int(value) for value in row["presentFields"]),
        )
        fields = tuple(int(value) for value in row["fields"])
        expected_fields = _FIELD2_STREAMING_ROWS.get(shape)
        if family == "init":
            raise ValueError(
                f"Streaming init field 2 expected 0 rows, actual at least {index + 1}"
            )
        if expected_fields is None:
            raise ValueError(
                f"Streaming {family} field 2 row {index} shape {shape} is unsupported"
            )
        if fields != expected_fields:
            raise ValueError(
                f"Streaming {family} field 2 row {index} field offsets {fields}, "
                f"expected {expected_fields} for shape {shape}"
            )
        layouts[(shape[0], shape[1], shape[2], fields)] += 1
        present_fields = shape[2]
        if not present_fields or fields[present_fields[0]] != 4:
            raise ValueError(
                f"Streaming {family} field 2 row {index} first slot starts at "
                f"{fields[present_fields[0]] if present_fields else 'absent'}, "
                "expected object offset 4"
            )
        for position, field_index in enumerate(present_fields):
            start = fields[field_index]
            end = (
                fields[present_fields[position + 1]]
                if position + 1 < len(present_fields)
                else int(row["objectSize"])
            )
            span = end - start
            expected_span = _FIELD2_STREAMING_SLOT_SPANS[field_index]
            if span != expected_span:
                raise ValueError(
                    f"Streaming {family} field 2 row {index} field {field_index} "
                    f"slot-to-next-boundary span {span}, expected {expected_span}"
                )
            slot_presence[field_index] += 1
            slot_span_bytes[field_index] += span
        row_values: dict[str, Any] | None = None
        if native_layout_validated:
            row_values = {"rowIndex": index}
            for field_index in range(3):
                offset = fields[field_index]
                row_values[f"field{field_index}Scalar32Bits"] = (
                    _u32(data, target + offset) if offset else None
                )
            field3_offset = fields[3]
            field4_offset = fields[4]
            if not field3_offset or not field4_offset:
                raise ValueError(
                    f"Streaming {family} field 2 row {index} native-consumed "
                    "fields 3 and 4 must both be present"
                )
            row_values["field3Int32Lanes"] = list(
                struct.unpack_from("<2i", data, target + field3_offset)
            )
            row_values["field4Float32Bits"] = list(
                struct.unpack_from("<6I", data, target + field4_offset)
            )
        ranges.append(
            (
                int(row["vtableOffset"]),
                int(row["vtableOffset"]) + int(row["vtableSize"]),
                "vtable",
                f"{family} field 2 row {index} vtable",
            )
        )
        ranges.append(
            (
                int(row["tableOffset"]),
                int(row["tableOffset"]) + int(row["objectSize"]),
                "table",
                f"{family} field 2 row {index} table",
            )
        )
        table_end = int(row["tableOffset"]) + int(row["objectSize"])
        child_start, child_count, child_end = _bounded_vector(
            data,
            row,
            5,
            4,
            f"{family} field 2 row {index} field 5",
        )
        if child_start != table_end:
            raise ValueError(
                f"Streaming {family} field 2 row {index} field 5 vector "
                f"target {child_start}, expected table end {table_end}"
            )
        child_range = (child_start, child_end, "anonymous-width4-vector")
        ranges.append(
            (*child_range, f"{family} field 2 row {index} field 5")
        )
        child_ranges.append(child_range)
        child_vector_count += 1
        child_value_count += child_count
        if row_values is not None:
            row_values["field5Scalar32Bits"] = [
                _u32(data, child_start + 4 + value_index * 4)
                for value_index in range(child_count)
            ]
            row_value_records.append(row_values)

    if family == "init":
        if row_count != 0:
            raise ValueError(
                f"Streaming init field 2 expected 0 rows, actual {row_count}"
            )
        if vector_end != len(data):
            raise ValueError(
                f"Streaming init field 2 empty vector expected EOF {vector_end}, "
                f"actual {len(data)}"
            )

    # Exact duplicate ranges of the same structural kind are shared
    # references. Any other overlap is malformed. The selected-build terminal
    # subgraph is continuous from the root-field-2 vector through decoded EOF.
    unique_ranges = sorted(
        {(start, end, kind) for start, end, kind, _label in ranges}
    )
    unique_child_ranges = sorted(set(child_ranges))
    unique_direct_ranges = [
        item for item in unique_ranges if item[2] != "anonymous-width4-vector"
    ]
    reused_references = len(ranges) - len(unique_ranges)
    if unique_ranges[0][0] != vector_start:
        raise ValueError(
            f"Streaming {family} field 2 terminal structural ranges start at "
            f"{unique_ranges[0][0]}, expected vector start {vector_start}"
        )
    for previous, current in zip(unique_ranges, unique_ranges[1:]):
        if current[0] < previous[1]:
            raise ValueError(
                f"Streaming {family} field 2 terminal structural ranges overlap: "
                f"{previous[0]}:{previous[1]} ({previous[2]}) and "
                f"{current[0]}:{current[1]} ({current[2]})"
            )
        if current[0] > previous[1]:
            raise ValueError(
                f"Streaming {family} field 2 terminal structural gap "
                f"{previous[1]}:{current[0]} before {current[2]}"
            )
    if unique_ranges[-1][1] != len(data):
        raise ValueError(
            f"Streaming {family} field 2 terminal structural ranges end at "
            f"{unique_ranges[-1][1]}, expected EOF {len(data)}"
        )

    return {
        "status": "exact_anonymous_eof_subgraph",
        "rowCount": row_count,
        "vectorRange": [vector_start, vector_end],
        "vectorEndsAtEof": vector_end == len(data),
        "rowLayouts": [
            {
                "fieldCount": layout[0],
                "objectSize": layout[1],
                "presentFields": list(layout[2]),
                "fieldOffsets": list(layout[3]),
                "count": count,
            }
            for layout, count in layouts.items()
        ],
        "ownedBytes": sum(end - start for start, end, _kind in unique_ranges),
        "rangeCount": len(unique_ranges),
        "reusedReferences": reused_references,
        "directOwnedBytes": sum(
            end - start for start, end, _kind in unique_direct_ranges
        ),
        "directRangeCount": len(unique_direct_ranges),
        "directReusedReferences": (
            len(ranges) - len(child_ranges) - len(unique_direct_ranges)
        ),
        "structuralRange": [vector_start, len(data)],
        "field5VectorCount": child_vector_count,
        "field5ElementWidth": 4,
        "field5ValueCount": child_value_count,
        "field5ReferencedBytes": sum(end - start for start, end, _kind in child_ranges),
        "field5OwnedBytes": sum(
            end - start for start, end, _kind in unique_child_ranges
        ),
        "field5RangeCount": len(unique_child_ranges),
        "field5ReusedReferences": len(child_ranges) - len(unique_child_ranges),
        "field5Status": (
            "exact-anonymous-native-consumed-scalar32-vector"
            if native_layout_validated
            else "exact-anonymous-vector"
        ),
        "rowObjectPartitionStatus": "exact-anonymous-slot-spans",
        "rowObjectPrefixBytes": row_count * 4,
        "rowSlotSpans": [
            {
                "fieldIndex": field_index,
                "slotToNextBoundaryBytes": span,
                "presentCount": slot_presence[field_index],
                "absentCount": row_count - slot_presence[field_index],
                "totalSpanBytes": slot_span_bytes[field_index],
                "status": (
                    "exact-vector-uoffset-slot"
                    if field_index == 5
                    else (
                        "exact-native-consumed-representation"
                        if native_layout_validated
                        else "exact-anonymous-span-only"
                    )
                ),
            }
            for field_index, span in enumerate(_FIELD2_STREAMING_SLOT_SPANS)
        ],
        "rowFields0To4Status": (
            "exact-anonymous-native-consumed-layout"
            if native_layout_validated
            else "exact-anonymous-slot-spans"
        ),
        "rowFields0To4RepresentationStatus": (
            "exact-selected-build-native-loads"
            if native_layout_validated
            else "unvalidated-native-contract"
        ),
        "rowFields0To5Status": (
            "exact-anonymous-native-consumed-layout"
            if native_layout_validated
            else "exact-anonymous-slot-spans"
        ),
        "rowFields0To5RepresentationStatus": (
            "exact-selected-build-native-loads"
            if native_layout_validated
            else "unvalidated-native-contract"
        ),
        "rowFieldRepresentations": ([
            {
                "fieldIndex": field_index,
                "representation": representation,
                "evidence": "selected-build-native-accessor-and-consumer",
                "semanticStatus": "unresolved",
            }
            for field_index, representation in enumerate(
                (
                    "little-endian-scalar32",
                    "little-endian-scalar32",
                    "little-endian-scalar32",
                    "little-endian-int32[2]",
                    "little-endian-float32[6]",
                    "count-prefixed-little-endian-scalar32[]",
                )
            )
        ] if native_layout_validated else []),
        "rowValueRecords": row_value_records,
        "rowSlotSpansMayContainPadding": (
            [] if native_layout_validated else [0, 1, 2, 3, 4]
        ),
        "field5ValuesStatus": (
            "exact-anonymous-selected-build-native-scalar32-keys"
            if native_layout_validated
            else "unvalidated-native-contract"
        ),
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


def parse_streaming_file(
    kind: str,
    packed: bytes,
    *,
    allow_raw: bool = False,
    native_layout_validated: bool = False,
) -> dict[str, Any]:
    """Validate one block-15 file's observed envelope and root table.

    ``kind`` is a maintained path-family classification: ``init``,
    ``streaming``, or ``info``.  For the first two kinds compressed decoding
    is attempted first; raw is accepted only when its root has the exact same
    observed 8-field shape.  Raw data-family input is rejected unless the
    caller has independently established the raw exception (the installed
    corpus uses this only for DevOnly files). Init/Streaming bytes outside the
    certified subgraphs remain explicitly opaque. Info files additionally
    return an exact anonymous inner table/vector framing. Field-2 typed loads
    are published only when the caller has separately revalidated the selected-
    build native contract and passes ``native_layout_validated=True``.
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
        result["anonymousParallelSubgraph"] = _parse_parallel_root_subgraph(
            clear, layout, kind
        )
        result["anonymousGroupSubgraph"] = _parse_paired_group_subgraph(
            clear, layout, kind
        )
        result["anonymousField2TerminalSubgraph"] = _parse_field2_terminal_subgraph(
            clear,
            layout,
            kind,
            native_layout_validated=native_layout_validated,
        )
    return result


__all__ = ["parse_streaming_file"]
