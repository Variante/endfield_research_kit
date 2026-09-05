"""Fail-closed parser for the bounded marker13 selector9 physical gap.

This parser derives each selected physical gap only from independently
certified neighbouring ranges;
native load width and the ordering of other anonymous targets are not extent
evidence.
"""
from __future__ import annotations

import bisect
import hashlib
import struct
from typing import Any, Iterable


PROFILE = {
    "family": "streaming",
    "rootMarker": 2,
    "rowSelectorU32": 9,
    "key": 0xFF000000,
    "marker": 13,
    "readWidth": 16,
    "physicalGapLengths": (16, 18),
}


def parse_marker13_selector9_gaps(
    data: bytes, *, source: str, family: str, rows: Iterable[dict[str, Any]],
    certified_ranges: Iterable[dict[str, Any] | tuple[int, int, str]],
    native_layout_validated: bool = False,
) -> dict[str, Any]:
    """Parse reference projections against independently certified neighbours.

    The caller supplies a source-authenticated structural directory and ranges;
    this helper rechecks referenced bytes, but does not authenticate a VFS root.
    All bytes outside the returned physical gaps remain owned by the original
    parser or opaque. A gap end is not a serialized sizeof or whole-file EOF.
    """
    try:
        return _parse_marker13_selector9_gaps(
            data, source=source, family=family, rows=rows,
            certified_ranges=certified_ranges,
            native_layout_validated=native_layout_validated,
        )
    except ValueError as exc:
        raise ValueError(f"{source}: {exc}") from exc


def _need_offset(data: bytes, value: Any, width: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label}: expected integer offset, actual {value!r}")
    if value < 0 or value > len(data) - width:
        raise ValueError(
            f"{label} at {value}: expected {width} readable bytes within payload "
            f"{len(data)}, actual {max(0, len(data) - value) if value >= 0 else 0}"
        )
    return value


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _normalize_ranges(
    data: bytes, ranges: Iterable[dict[str, Any] | tuple[int, int, str]]
) -> list[tuple[int, int, str]]:
    result: list[tuple[int, int, str]] = []
    for index, item in enumerate(ranges):
        if isinstance(item, dict):
            start, end, kind = item.get("start"), item.get("end"), item.get("kind")
        else:
            try:
                start, end, kind = item
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"certified range {index}: expected start/end/kind triple, actual {item!r}"
                ) from exc
        if not isinstance(start, int) or isinstance(start, bool):
            raise ValueError(f"certified range {index} start: expected integer, actual {start!r}")
        if not isinstance(end, int) or isinstance(end, bool):
            raise ValueError(f"certified range {index} end: expected integer, actual {end!r}")
        if not isinstance(kind, str) or not kind:
            raise ValueError(f"certified range {index} kind: expected nonempty string, actual {kind!r}")
        if start < 0 or end <= start or end > len(data):
            raise ValueError(
                f"certified range {index} {start}:{end}: expected 0 <= start < end <= "
                f"{len(data)}, actual {start}:{end}"
            )
        result.append((start, end, kind))
    if result != sorted(result):
        raise ValueError("certified ranges: expected sorted start/end/kind order, actual unsorted")
    for previous, current in zip(result, result[1:]):
        if current[0] < previous[1] and current != previous:
            raise ValueError(
                "certified ranges: expected no non-identical overlap, actual "
                f"{previous} and {current}"
            )
    return sorted(set(result))


def _validate_row_values(data: bytes, row: dict[str, Any], row_index: int) -> dict[str, Any]:
    label = f"marker13 row {row_index}"
    for name in ("rootMarkerOffset", "keyOffset", "markerOffset", "targetSlotOffset"):
        if name not in row:
            raise ValueError(f"{label}: expected {name}, actual absent")
    root_offset = _need_offset(data, row["rootMarkerOffset"], 1, f"{label} root marker")
    key_offset = _need_offset(data, row["keyOffset"], 4, f"{label} key")
    marker_offset = _need_offset(data, row["markerOffset"], 1, f"{label} marker")
    target_slot = _need_offset(data, row["targetSlotOffset"], 4, f"{label} target slot")
    actual_root = data[root_offset]
    actual_key = _u32(data, key_offset)
    actual_marker = data[marker_offset]
    relative = _u32(data, target_slot)
    actual_target = target_slot + relative
    if actual_target <= target_slot or actual_target >= len(data):
        raise ValueError(
            f"{label} target slot at {target_slot}: expected positive in-bounds uoffset, "
            f"actual relative {relative} -> {actual_target} for payload {len(data)}"
        )
    checks = (
        ("rootMarker", actual_root),
        ("key", actual_key),
        ("marker", actual_marker),
        ("targetStart", actual_target),
    )
    for name, actual in checks:
        expected = row.get(name)
        if expected != actual:
            raise ValueError(f"{label} {name}: expected directory {expected!r}, actual bytes {actual!r}")

    selector = row.get("rowSelectorU32")
    selector_offset = row.get("rowSelectorOffset")
    if selector is None:
        if selector_offset is not None:
            raise ValueError(
                f"{label} selector: expected absent offset for absent value, actual {selector_offset!r}"
            )
        actual_selector = None
    else:
        selector_offset = _need_offset(data, selector_offset, 4, f"{label} selector")
        actual_selector = _u32(data, selector_offset)
        if selector != actual_selector:
            raise ValueError(
                f"{label} rowSelectorU32: expected directory {selector!r}, actual bytes {actual_selector!r}"
            )
    expected_low = None if actual_selector is None else actual_selector & 0xFF
    if row.get("rowSelectorLowByte") != expected_low:
        raise ValueError(
            f"{label} rowSelectorLowByte: expected {expected_low!r} from raw selector, "
            f"actual {row.get('rowSelectorLowByte')!r}"
        )
    return {
        "rootMarker": actual_root,
        "rowSelectorU32": actual_selector,
        "rowSelectorLowByte": expected_low,
        "key": actual_key,
        "marker": actual_marker,
        "targetStart": actual_target,
    }


def _context_status(family: str, actual: dict[str, Any]) -> tuple[str, str | None]:
    if family != PROFILE["family"]:
        return "unsupported-context", f"family {family!r} is not selected family 'streaming'"
    if actual["rootMarker"] != PROFILE["rootMarker"]:
        return "unsupported-context", f"root marker {actual['rootMarker']} is not selected marker 2"
    if actual["rowSelectorU32"] != PROFILE["rowSelectorU32"]:
        return "unsupported-context", (
            f"raw row selector {actual['rowSelectorU32']!r} is not selected raw selector 9"
        )
    if actual["key"] != PROFILE["key"]:
        return "unsupported-context", f"full key {actual['key']:#010x} is not selected key 0xff000000"
    return "selected", None


def _parse_marker13_selector9_gaps(
    data: bytes,
    *,
    source: str,
    family: str,
    rows: Iterable[dict[str, Any]],
    certified_ranges: Iterable[dict[str, Any] | tuple[int, int, str]],
    native_layout_validated: bool,
) -> dict[str, Any]:
    """Project 16 readable bytes within a certified 16- or 18-byte gap.

    Unsupported contexts remain explicit and own no bytes.  A duplicate table
    key is reported as ambiguous and likewise does not select an extent.
    Structural inconsistencies in a selected context fail closed.
    """
    if native_layout_validated is not True:
        raise ValueError(
            "marker13 selector9 native layout gate: expected exact boolean True, "
            f"actual {native_layout_validated!r}"
        )
    if not isinstance(data, bytes):
        raise ValueError(f"marker13 decoded payload: expected bytes, actual {type(data).__name__}")
    if family != PROFILE["family"]:
        raise ValueError(
            f"marker13 family: expected selected family 'streaming', actual {family!r}"
        )
    certified = _normalize_ranges(data, certified_ranges)
    certified_starts = [item[0] for item in certified]
    certified_ends = [item[1] for item in certified]
    output_rows = []
    exact_count = ambiguous_count = unsupported_count = 0
    partitioned_bytes = 0
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"marker13 row {row_index}: expected mapping, actual {type(row).__name__}")
        actual = _validate_row_values(data, row, row_index)
        status, reason = _context_status(family, actual)
        evidence = {
            "source": source,
            "family": family,
            "outerRowIndex": row.get("outerRowIndex"),
            "outerRowOffset": row.get("outerRowOffset"),
            "rootMarker": actual["rootMarker"],
            "rootMarkerOffset": row["rootMarkerOffset"],
            "rowSelectorU32": actual["rowSelectorU32"],
            "rowSelectorLowByte": actual["rowSelectorLowByte"],
            "rowSelectorOffset": row.get("rowSelectorOffset"),
            "nestedTableOffset": row.get("nestedTableOffset"),
            "nestedElementCount": row.get("nestedElementCount"),
            "elementIndex": row.get("elementIndex"),
            "key": actual["key"],
            "keyHex": f"{actual['key']:08X}",
            "keyOffset": row["keyOffset"],
            "keyOccurrenceCountInTable": row.get("keyOccurrenceCountInTable"),
            "marker": actual["marker"],
            "markerOffset": row["markerOffset"],
            "targetSlotOffset": row["targetSlotOffset"],
            "targetStart": actual["targetStart"],
        }
        if status == "unsupported-context":
            output_rows.append({**evidence, "status": status, "reason": reason,
                                "partitionedBytes": 0})
            unsupported_count += 1
            continue
        if actual["marker"] != PROFILE["marker"]:
            raise ValueError(
                f"marker13 row {row_index} marker at {row['markerOffset']}: expected 13, "
                f"actual {actual['marker']}"
            )
        occurrence_count = row.get("keyOccurrenceCountInTable")
        if (not isinstance(occurrence_count, int) or isinstance(occurrence_count, bool)
                or occurrence_count <= 0):
            raise ValueError(
                f"marker13 row {row_index} keyOccurrenceCountInTable: expected positive "
                f"integer, actual {occurrence_count!r}"
            )
        if occurrence_count > 1:
            output_rows.append({
                **evidence, "status": "ambiguous",
                "reason": "selected full key is not unique in its nested table",
                "partitionedBytes": 0,
            })
            ambiguous_count += 1
            continue

        target = actual["targetStart"]
        if target > len(data) - PROFILE["readWidth"]:
            raise ValueError(
                f"marker13 row {row_index} target at {target}: expected 16 readable bytes, "
                f"actual {max(0, len(data) - target)}"
            )
        # The ranges are sorted, unique and non-overlapping, so only the two
        # neighbours around the insertion point can intersect the gap.
        insertion = bisect.bisect_right(certified_starts, target)
        neighbor_indices = range(max(0, insertion - 1), min(len(certified), insertion + 1))
        overlapping = [
            certified[index] for index in neighbor_indices
            if certified[index][0] < target + 16 and target < certified[index][1]
        ]
        if overlapping:
            raise ValueError(
                f"marker13 row {row_index} target range {target}:{target+16}: expected no "
                f"certified overlap, actual {overlapping[0]}"
            )
        prior_index = bisect.bisect_right(certified_ends, target) - 1
        following_index = bisect.bisect_left(certified_starts, target)
        if prior_index < 0:
            raise ValueError(
                f"marker13 row {row_index} target at {target}: expected preceding certified end "
                "at target, actual none"
            )
        previous_end = certified[prior_index][1]
        previous = [certified[prior_index]]
        if previous_end != target:
            raise ValueError(
                f"marker13 row {row_index} target at {target}: expected preceding certified end "
                f"{target}, actual {previous_end}"
            )
        if following_index >= len(certified):
            raise ValueError(
                f"marker13 row {row_index} target at {target}: expected following certified "
                f"start {target+16}, actual none before EOF {len(data)}"
            )
        next_start = certified[following_index][0]
        following_at_start = [certified[following_index]]
        if next_start - target not in PROFILE["physicalGapLengths"]:
            relation = "short/overlapping" if next_start < target + 16 else "extra/long"
            raise ValueError(
                f"marker13 row {row_index} target at {target}: expected following certified "
                f"start in {[target + length for length in PROFILE['physicalGapLengths']]}, "
                f"actual {next_start} ({relation} gap {next_start-target})"
            )
        raw = data[target:target + 16]
        lanes = [
            {"index": index, "offset": target + index * 4, "anonymousU32": _u32(raw, index * 4)}
            for index in range(4)
        ]
        output_rows.append({
            **evidence,
            "status": "exact-anonymous-physical-gap",
            "evidenceLevel": "structural-only",
            "physicalGapRange": {"start": target, "end": next_start, "length": next_start - target},
            "nativeReadWindowRange": {"start": target, "end": target + 16, "length": 16},
            "residualOpaqueRange": (
                {"start": target + 16, "end": next_start, "length": next_start - target - 16}
                if next_start > target + 16 else None
            ),
            "previousCertifiedRanges": [
                {"start": start, "end": end, "kind": kind} for start, end, kind in previous
            ],
            "nextCertifiedRanges": [
                {"start": start, "end": end, "kind": kind}
                for start, end, kind in following_at_start
            ],
            "anonymousScalar32Projection": lanes,
            "rawHex": raw.hex().upper(),
            "rawSha256": hashlib.sha256(raw).hexdigest().upper(),
            "partitionedBytes": 16,
            "serializedSizeStatus": "unknown",
            "nativeFinalCursorStatus": "unknown",
            "semanticsStatus": "unresolved",
        })
        exact_count += 1
        partitioned_bytes += 16

    status = (
        "ambiguous" if ambiguous_count else
        "exact-anonymous-physical-gaps" if exact_count else
        "unsupported-context-only"
    )
    return {
        "status": status,
        "evidenceLevel": "structural-only",
        "profile": dict(PROFILE),
        "source": source,
        "rows": output_rows,
        "counts": {
            "exact": exact_count,
            "ambiguous": ambiguous_count,
            "unsupportedContext": unsupported_count,
        },
        "partitionedBytes": partitioned_bytes,
        "targetOwnedBytes": 0,
        "serializedSizeStatus": "unknown",
        "nativeFinalCursorStatus": "unknown",
        "semanticsStatus": "unresolved",
    }
