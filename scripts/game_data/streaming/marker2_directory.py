"""Structural directory for nested marker-2 target references.

The caller owns VFS identity, decompression and the root parser gate.  This
module replays only the already-authenticated anonymous parallel graph.  A
target uoffset establishes one byte of addressability, not a record width.
"""
from __future__ import annotations

import bisect
import collections
import hashlib
import struct
from typing import Any, Iterable

from scripts.game_data.streaming import framing as fmt


# These representations are already bounded by the maintained root parser:
# marker17 as wrapper framing, marker13/15 as anonymous forward targets.  This
# directory adds marker2.  No other marker byte makes its slot word a uoffset.
KNOWN_TARGET_MARKERS = frozenset((2, 13, 15, 17))


def _need_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected mapping, actual {type(value).__name__}")
    return value


def _ranges(
    data: bytes, supplied: Iterable[dict[str, Any] | tuple[int, int, str]], source: str,
) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    for index, item in enumerate(supplied):
        if isinstance(item, dict):
            start, end, kind = item.get("start"), item.get("end"), item.get("kind")
        else:
            try:
                start, end, kind = item
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{source}: certified range {index}: expected triple") from exc
        if type(start) is not int or type(end) is not int:
            raise ValueError(
                f"{source}: certified range {index}: expected integer bounds, actual {start!r}:{end!r}"
            )
        if not isinstance(kind, str) or not kind:
            raise ValueError(f"{source}: certified range {index}: expected nonempty kind")
        if start < 0 or end <= start or end > len(data):
            raise ValueError(
                f"{source}: certified range {index}: expected 0 <= start < end <= {len(data)}, "
                f"actual {start}:{end}"
            )
        rows.append((start, end, kind))
    expected = sorted(set(rows))
    if rows != expected:
        raise ValueError(f"{source}: certified ranges: expected sorted duplicate-free input")
    for left, right in zip(rows, rows[1:]):
        if right[0] < left[1]:
            raise ValueError(f"{source}: certified ranges overlap: {left!r} / {right!r}")
    return rows


def _selector(
    data: bytes, outer: dict[str, Any], root_marker: int, source: str, ordinal: int,
) -> tuple[int | None, int | None, str]:
    """Decode field2 only for the independently selected root-marker-2 shape."""
    if root_marker != 2:
        return None, None, "not-decoded-for-non-marker2-outer-shape"
    slot = fmt._field_address(outer, 2)
    if slot is None:
        return None, None, "serialized-field2-absent"
    addresses = sorted(
        int(address)
        for field in outer["presentFields"]
        if (address := fmt._field_address(outer, int(field))) is not None
    )
    position = addresses.index(slot)
    end = addresses[position + 1] if position + 1 < len(addresses) else int(outer["tableOffset"]) + int(outer["objectSize"])
    if end - slot < 4:
        raise ValueError(
            f"{source}: outer row {ordinal} selector slot {slot}: expected at least 4 bytes, actual {end-slot}"
        )
    return fmt._u32(data, slot), slot, "serialized-field2-present-u32"


def _parallel_vectors(
    data: bytes, table: dict[str, Any], source: str, label: str,
) -> tuple[dict[int, tuple[int, int, int]], int]:
    vectors = {
        field: fmt._bounded_vector(data, table, field, width, f"{source} {label} field{field}")
        for field, width in ((3, 4), (4, 1), (5, 4))
    }
    counts = {field: value[1] for field, value in vectors.items()}
    if len(set(counts.values())) != 1:
        raise ValueError(f"{source}: {label} parallel counts differ: {counts!r}")
    return vectors, vectors[3][1]


def collect_marker2_directory(
    data: bytes, *, source: str, family: str, parsed: dict[str, Any],
    certified_ranges: Iterable[dict[str, Any] | tuple[int, int, str]] | None = None,
) -> dict[str, Any]:
    """Return all marker-2 rows plus every target occupying their opaque gaps.

    Unknown nested marker bytes retain raw slots and make occupancy incomplete.  No target
    byte is read and no target width, ownership, EOF, union tag or semantic
    meaning is assigned.
    """
    if not isinstance(data, bytes):
        raise ValueError(f"{source}: decoded payload: expected bytes, actual {type(data).__name__}")
    if family not in {"init", "streaming"}:
        raise ValueError(f"{source}: family: expected init/streaming, actual {family!r}")
    document = _need_mapping(parsed, f"{source}: parsed document")
    decoded_bytes = document.get("decodedBytes")
    if type(decoded_bytes) is not int or decoded_bytes != len(data):
        raise ValueError(
            f"{source}: decoded length: expected parser integer {decoded_bytes!r}, actual {len(data)}"
        )
    graph = _need_mapping(document.get("anonymousParallelSubgraph"), f"{source}: parallel graph")
    if graph.get("status") != "exact_anonymous_subgraph":
        raise ValueError(
            f"{source}: parallel graph status: expected exact_anonymous_subgraph, actual {graph.get('status')!r}"
        )
    witness = _need_mapping(graph.get("orderedRootWitness"), f"{source}: ordered root witness")
    ranges = _ranges(
        data,
        document.get("decodedCertifiedRanges") if certified_ranges is None else certified_ranges,
        source,
    )

    root = fmt._table_layout(data, fmt._u32(data, 0))
    root_vectors, outer_count = _parallel_vectors(data, root, source, "root")
    witnessed_rows = witness.get("rowCount")
    if type(witnessed_rows) is not int or witnessed_rows != outer_count:
        raise ValueError(
            f"{source}: root row count: expected parser integer {witnessed_rows!r}, actual {outer_count}"
        )

    all_references: list[dict[str, Any]] = []
    marker_counts: collections.Counter[int] = collections.Counter()
    nested_table_count = 0
    for outer_index in range(outer_count):
        root_marker_offset = root_vectors[4][0] + 4 + outer_index
        root_marker = data[root_marker_offset]
        outer_slot = root_vectors[5][0] + 4 + outer_index * 4
        outer_offset = fmt._bounded_anonymous_target(
            data, outer_slot, f"{source} outer row {outer_index}",
        )
        outer = fmt._table_layout(data, outer_offset)
        field5_slot = fmt._field_address(outer, 5)
        if field5_slot is None:
            continue
        field3_slot = fmt._field_address(outer, 3)
        if field3_slot is None:
            raise ValueError(f"{source}: outer row {outer_index}: field5 present but field3 absent")
        _unused_start, unused_count, _unused_end = fmt._bounded_vector(
            data, outer, 5, 1, f"{source} outer row {outer_index} field5",
        )
        if unused_count != 0:
            raise ValueError(
                f"{source}: outer row {outer_index} field5: expected parser-authenticated empty count 0, "
                f"actual {unused_count}"
            )
        nested_offset = fmt._bounded_anonymous_target(
            data, field3_slot, f"{source} outer row {outer_index} nested table",
        )
        nested = fmt._table_layout(data, nested_offset)
        nested_vectors, nested_count = _parallel_vectors(
            data, nested, source, f"outer row {outer_index} nested",
        )
        nested_table_count += 1
        selector, selector_offset, selector_status = _selector(
            data, outer, root_marker, source, outer_index,
        )
        keys = [
            fmt._u32(data, nested_vectors[3][0] + 4 + index * 4)
            for index in range(nested_count)
        ]
        key_counts = collections.Counter(keys)
        for element_index, key in enumerate(keys):
            marker_offset = nested_vectors[4][0] + 4 + element_index
            marker = data[marker_offset]
            target_slot = nested_vectors[5][0] + 4 + element_index * 4
            raw_target_word = fmt._u32(data, target_slot)
            target = (
                fmt._bounded_anonymous_target(
                    data, target_slot,
                    f"{source} outer row {outer_index} nested element {element_index} marker {marker}",
                )
                if marker in KNOWN_TARGET_MARKERS else None
            )
            marker_counts[marker] += 1
            all_references.append({
                "outerRowIndex": outer_index,
                "outerRowOffset": outer_offset,
                "outerRowVectorSlotOffset": outer_slot,
                "rootMarker": root_marker,
                "rootMarkerOffset": root_marker_offset,
                "rowSelectorU32": selector,
                "rowSelectorLowByte": selector & 0xFF if selector is not None else None,
                "rowSelectorOffset": selector_offset,
                "rowSelectorStatus": selector_status,
                "nestedTableOffset": nested_offset,
                "nestedElementCount": nested_count,
                "elementIndex": element_index,
                "key": key,
                "keyHex": f"{key:08X}",
                "keyOffset": nested_vectors[3][0] + 4 + element_index * 4,
                "keyOccurrenceCountInTable": key_counts[key],
                "keyStatus": "unique" if key_counts[key] == 1 else "ambiguous",
                "marker": marker,
                "markerOffset": marker_offset,
                "targetSlotOffset": target_slot,
                "rawTargetSlotWordU32": raw_target_word,
                "targetStart": target,
                "targetResolutionStatus": (
                    "bounded-anonymous-forward-target"
                    if target is not None else "unknown-marker-representation-unresolved"
                ),
            })

    expected_counts = {}
    for key, value in _need_mapping(
        graph.get("nestedElementMarkerCounts"), f"{source}: parser marker counts",
    ).items():
        if type(key) is not int or not 0 <= key <= 255:
            raise ValueError(f"{source}: parser marker key: expected byte integer, actual {key!r}")
        if type(value) is not int or value < 0:
            raise ValueError(f"{source}: parser marker {key} count: expected nonnegative integer, actual {value!r}")
        expected_counts[key] = value
    if dict(sorted(marker_counts.items())) != dict(sorted(expected_counts.items())):
        raise ValueError(
            f"{source}: nested marker counts: expected parser {expected_counts!r}, "
            f"actual {dict(marker_counts)!r}"
        )
    expected_nested_tables = graph.get("field5Field3NestedTableCount")
    if type(expected_nested_tables) is not int or expected_nested_tables != nested_table_count:
        raise ValueError(
            f"{source}: nested table count: expected parser integer {expected_nested_tables!r}, "
            f"actual {nested_table_count}"
        )

    by_target: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    ordered_digest = hashlib.sha256()
    for row in all_references:
        if row["targetStart"] is not None:
            by_target[row["targetStart"]].append(row)
        ordered_digest.update(struct.pack(
            "<QQQBIIQ", row["outerRowIndex"], row["elementIndex"], row["targetSlotOffset"],
            row["marker"], row["key"], row["rawTargetSlotWordU32"],
            0 if row["targetStart"] is None else row["targetStart"] + 1,
        ))
    target_starts = sorted(by_target)
    unresolved_marker_rows = [row for row in all_references if row["targetStart"] is None]
    occupancy_complete = not unresolved_marker_rows
    certified_starts = [item[0] for item in ranges]
    certified_ends = [item[1] for item in ranges]
    marker2_rows = []
    for row in all_references:
        if row["marker"] != 2:
            continue
        target = row["targetStart"]
        containing_index = bisect.bisect_right(certified_starts, target) - 1
        containing = (
            [ranges[containing_index]]
            if containing_index >= 0 and target < ranges[containing_index][1] else []
        )
        prior_index = bisect.bisect_right(certified_ends, target) - 1
        next_index = bisect.bisect_right(certified_starts, target)
        previous = ranges[prior_index] if prior_index >= 0 else None
        following = ranges[next_index] if next_index < len(ranges) else None
        gap_start = previous[1] if previous is not None else 0
        gap_end = following[0] if following is not None else len(data)
        occupants = []
        if not containing and gap_start <= target < gap_end:
            for occupied_target in target_starts[
                bisect.bisect_left(target_starts, gap_start):bisect.bisect_left(target_starts, gap_end)
            ]:
                for occupant in by_target[occupied_target]:
                    occupants.append({
                        name: occupant[name] for name in (
                            "targetStart", "targetSlotOffset", "outerRowIndex", "elementIndex",
                            "marker", "markerOffset", "key", "keyOffset",
                            "keyOccurrenceCountInTable", "rawTargetSlotWordU32",
                        )
                    })
        marker2_rows.append({
            **row,
            "targetReferenceCountInFile": len(by_target[target]),
            "targetStatus": "inside-certified-range" if containing else "anonymous-uncertified-target",
            "containingCertifiedRanges": [
                {"start": start, "end": end, "kind": kind} for start, end, kind in containing
            ],
            "previousCertifiedRange": (
                {"start": previous[0], "end": previous[1], "kind": previous[2]}
                if previous is not None else None
            ),
            "nextCertifiedRange": (
                {"start": following[0], "end": following[1], "kind": following[2]}
                if following is not None else None
            ),
            "candidateOpaqueGap": (
                {"start": gap_start, "end": gap_end, "length": gap_end-gap_start}
                if not containing and gap_start <= target < gap_end else None
            ),
            "gapTargetReferences": occupants,
            "targetOccupancyComplete": occupancy_complete,
            "unresolvedMarkerReferenceCountInFile": len(unresolved_marker_rows),
            "targetOwnedBytes": 0,
            "targetWidthStatus": "unresolved",
        })

    return {
        "status": (
            "exact-structural-marker2-reference-directory"
            if occupancy_complete else
            "exact-marker2-directory-with-incomplete-unknown-marker-occupancy"
        ),
        "evidenceLevel": "structural-only",
        "source": source,
        "family": family,
        "rows": marker2_rows,
        "counts": {
            "outerRows": outer_count,
            "nestedTables": nested_table_count,
            "allNestedTargetReferences": len(all_references),
            "uniqueNestedTargetStarts": len(by_target),
            "unresolvedMarkerRepresentations": len(unresolved_marker_rows),
            "marker2References": len(marker2_rows),
        },
        "nestedMarkerCounts": dict(sorted(marker_counts.items())),
        "allNestedTargetOrderedSha256": ordered_digest.hexdigest().upper(),
        "unresolvedMarkerRows": [
            {name: row[name] for name in (
                "outerRowIndex", "outerRowOffset", "rootMarker", "rootMarkerOffset",
                "nestedTableOffset", "elementIndex", "key", "keyOffset",
                "keyOccurrenceCountInTable", "marker", "markerOffset",
                "targetSlotOffset", "rawTargetSlotWordU32", "targetResolutionStatus",
            )}
            for row in unresolved_marker_rows
        ],
        "targetOwnedBytes": 0,
        "targetWidthStatus": "unresolved",
        "unknownMarkerDisposition": (
            "raw marker/key/slot word retained; target representation unresolved; occupancy incomplete"
        ),
        "semanticsStatus": "unresolved",
    }
