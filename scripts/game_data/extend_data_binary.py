"""Conservative readers for the exact-build ExtendData binary payloads.

The readers in this module intentionally describe framing and bounds only.  In
particular, the hash fields and the first StringPathHash bucket word are kept
as raw values, and FacBoneTRS's 64-byte values are not assigned a managed type.
They are useful for audit reports and tests; they are not game-runtime
reimplementations.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


INIT_STRING_PATH = "Data/ExtendData/Initial/InitStringPathHash.bin"
FAC_BONE_TRS_PATH = "Data/ExtendData/Main/FacBone/FacBoneTRS.bin"
STRING_PATH_HASH_PATH = "Data/ExtendData/Main/StringPathHash.bin"
OUTER_LEDGER_SCHEMA_VERSION = 1


class BinaryFormatError(ValueError):
    """Raised when a payload cannot be consumed using its observed framing."""


def _need(data: bytes, offset: int, size: int, label: str) -> None:
    if offset < 0 or size < 0 or offset > len(data) or size > len(data) - offset:
        raise BinaryFormatError(
            f"{label} range [{offset}, {offset + size}) is outside "
            f"source length {len(data)}"
        )


def _union(ranges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    ordered = sorted((start, end) for start, end in ranges if end > start)
    result: list[tuple[int, int]] = []
    for start, end in ordered:
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result


def _complement(length: int, ranges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    cursor = 0
    for start, end in _union(ranges):
        if start > cursor:
            result.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < length:
        result.append((cursor, length))
    return result


@dataclass(frozen=True)
class StringPathHashSummary:
    source_length: int
    str_data_offset: int
    count: int
    slot_count: int
    nonempty_slot_count: int
    bucket_count: int
    distinct_bucket_count: int
    string_count: int
    referenced_string_count: int
    raw_key_offset_nonzero_count: int
    bucket_ranges: tuple[tuple[int, int], ...]
    unaccounted_pre_string_ranges: tuple[tuple[int, int], ...]
    consumed_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_length": self.source_length,
            "str_data_offset": self.str_data_offset,
            "count": self.count,
            "slot_count": self.slot_count,
            "nonempty_slot_count": self.nonempty_slot_count,
            "bucket_count": self.bucket_count,
            "distinct_bucket_count": self.distinct_bucket_count,
            "string_count": self.string_count,
            "referenced_string_count": self.referenced_string_count,
            "raw_key_offset_nonzero_count": self.raw_key_offset_nonzero_count,
            "bucket_ranges": [list(item) for item in self.bucket_ranges],
            "unaccounted_pre_string_ranges": [
                list(item) for item in self.unaccounted_pre_string_ranges
            ],
            "consumed_bytes": self.consumed_bytes,
        }


def parse_string_path_hash(data: bytes, *, source: str = "<memory>") -> StringPathHashSummary:
    """Parse StringPathHash.bin or InitStringPathHash.bin.

    The observed header is ``<uint32 strDataOffset, uint32 count>``.  Each
    slot is ``<uint32 offset, uint32 bucketsSize>`` and each bucket is
    ``<uint32 rawKeyOrValueOffset, uint64 hash, uint32 pathOffset>``.  The
    string region contains exactly ``count`` length-prefixed UTF-16LE strings.
    ``pathOffset`` is validated as a relative string-record start.
    """

    if len(data) < 8:
        raise BinaryFormatError(f"{source}: missing 8-byte header")
    str_data_offset, count = struct.unpack_from("<II", data, 0)
    if str_data_offset != 8 + count * 24:
        raise BinaryFormatError(
            f"{source}: strDataOffset {str_data_offset} != 8 + count*24 "
            f"({8 + count * 24})"
        )
    _need(data, 8, count * 8, f"{source} slot table")
    if str_data_offset > len(data):
        raise BinaryFormatError(f"{source}: string region starts past source")

    slots_end = 8 + count * 8
    slots: list[tuple[int, int]] = []
    nonempty = 0
    bucket_ranges: list[tuple[int, int]] = []
    bucket_starts: list[int] = []
    bucket_count = 0
    raw_nonzero = 0
    path_offsets: list[int] = []
    for index in range(count):
        offset, bucket_size = struct.unpack_from("<II", data, 8 + index * 8)
        slots.append((offset, bucket_size))
        if bucket_size == 0:
            if offset != 0:
                raise BinaryFormatError(
                    f"{source}: empty slot {index} has nonzero offset {offset}"
                )
            continue
        nonempty += 1
        if offset < slots_end - 4:
            raise BinaryFormatError(
                f"{source}: slot {index} bucket offset {offset} precedes "
                f"allowed bucket boundary {slots_end - 4}"
            )
        byte_size = bucket_size * 16
        _need(data, offset, byte_size, f"{source} slot {index} buckets")
        if offset + byte_size > str_data_offset:
            raise BinaryFormatError(
                f"{source}: slot {index} buckets overlap string region "
                f"at {str_data_offset}"
            )
        bucket_ranges.append((offset, offset + byte_size))
        for bucket_index in range(bucket_size):
            bucket_offset = offset + bucket_index * 16
            raw_key_offset, _hash_value, path_offset = struct.unpack_from(
                "<IQI", data, bucket_offset
            )
            raw_nonzero += raw_key_offset != 0
            bucket_starts.append(bucket_offset)
            path_offsets.append(path_offset)
            bucket_count += 1

    distinct_bucket_count = len(set(bucket_starts))
    if distinct_bucket_count != bucket_count:
        raise BinaryFormatError(
            f"{source}: bucket records alias ({bucket_count - distinct_bucket_count} duplicate starts)"
        )
    ordered_bucket_ranges = sorted(bucket_ranges)
    for previous, current in zip(ordered_bucket_ranges, ordered_bucket_ranges[1:]):
        if current[0] < previous[1]:
            raise BinaryFormatError(
                f"{source}: bucket ranges overlap at "
                f"[{current[0]}, {current[1]}) and "
                f"[{previous[0]}, {previous[1]})"
            )

    # Parse every string record and retain only record starts.  Strict decoding
    # is deliberate: a malformed UTF-16 payload is not silently classified as
    # an unknown string.
    string_starts: set[int] = set()
    cursor = str_data_offset
    for string_index in range(count):
        string_starts.add(cursor - str_data_offset)
        _need(data, cursor, 4, f"{source} string {string_index} length")
        byte_length = struct.unpack_from("<I", data, cursor)[0]
        cursor += 4
        if byte_length & 1:
            raise BinaryFormatError(
                f"{source}: string {string_index} has odd UTF-16 byte length {byte_length}"
            )
        _need(data, cursor, byte_length + 2, f"{source} string {string_index} payload")
        try:
            data[cursor : cursor + byte_length].decode("utf-16-le", errors="strict")
        except UnicodeDecodeError as exc:
            raise BinaryFormatError(
                f"{source}: string {string_index} is not valid UTF-16LE: {exc}"
            ) from exc
        if data[cursor + byte_length : cursor + byte_length + 2] != b"\0\0":
            raise BinaryFormatError(
                f"{source}: string {string_index} is missing its UTF-16 terminator"
            )
        cursor += byte_length + 2
    if cursor != len(data):
        raise BinaryFormatError(
            f"{source}: string region consumed through {cursor}, source ends at {len(data)}"
        )
    missing = sorted(set(path_offsets) - string_starts)
    if missing:
        preview = ", ".join(str(value) for value in missing[:4])
        raise BinaryFormatError(
            f"{source}: {len(missing)} pathOffset values do not name string records "
            f"(first: {preview})"
        )

    return StringPathHashSummary(
        source_length=len(data),
        str_data_offset=str_data_offset,
        count=count,
        slot_count=count,
        nonempty_slot_count=nonempty,
        bucket_count=bucket_count,
        distinct_bucket_count=distinct_bucket_count,
        string_count=count,
        referenced_string_count=len(set(path_offsets)),
        raw_key_offset_nonzero_count=raw_nonzero,
        bucket_ranges=tuple(_union(bucket_ranges)),
        unaccounted_pre_string_ranges=tuple(
            _complement(str_data_offset, [(0, slots_end), *bucket_ranges])
        ),
        consumed_bytes=cursor,
    )


@dataclass(frozen=True)
class FacBoneTRSSummary:
    source_length: int
    lookup_end_offset: int
    lookup_slot_count: int
    nonempty_lookup_slot_count: int
    lookup_bucket_count: int
    lookup_bucket_ranges: tuple[tuple[int, int], ...]
    unit_table_start: int
    unit_table_end: int
    unit_record_count: int
    bone_count: int
    bone_pool_start: int
    bone_pool_end: int
    trs_range_count: int
    trs_element_stride: int
    trs_bytes: int
    max_trs_end: int
    unit_bone_ranges: tuple[tuple[int, int], ...]
    trs_ranges: tuple[tuple[int, int], ...]
    unaccounted_ranges: tuple[tuple[int, int], ...]
    consumed_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_length": self.source_length,
            "lookup_end_offset": self.lookup_end_offset,
            "lookup_slot_count": self.lookup_slot_count,
            "nonempty_lookup_slot_count": self.nonempty_lookup_slot_count,
            "lookup_bucket_count": self.lookup_bucket_count,
            "lookup_bucket_ranges": [list(item) for item in self.lookup_bucket_ranges],
            "unit_table_start": self.unit_table_start,
            "unit_table_end": self.unit_table_end,
            "unit_record_count": self.unit_record_count,
            "bone_count": self.bone_count,
            "bone_pool_start": self.bone_pool_start,
            "bone_pool_end": self.bone_pool_end,
            "trs_range_count": self.trs_range_count,
            "trs_element_stride": self.trs_element_stride,
            "trs_bytes": self.trs_bytes,
            "max_trs_end": self.max_trs_end,
            "unit_bone_ranges": [list(item) for item in self.unit_bone_ranges],
            "trs_ranges": [list(item) for item in self.trs_ranges],
            "unaccounted_ranges": [list(item) for item in self.unaccounted_ranges],
            "consumed_bytes": self.consumed_bytes,
        }


def parse_fac_bone_trs(
    data: bytes,
    *,
    source: str = "<memory>",
) -> FacBoneTRSSummary:
    """Parse the self-bounded FacBoneTRS lookup, unit, bone, and TRS pools.

    The first two words provide the lookup-bucket end and entry count.  That
    count bounds both the eight-byte slot table and the aligned 16-byte unit
    table.  The current layout has observed overlaps between adjacent structural
    views: the lookup bucket pool starts four bytes before the slot table ends,
    and the first bone record starts eight bytes before the unit table ends.
    Acceptance requires the complete lookup pool, unit records, bone lists,
    and 64-byte value ranges to satisfy the observed gap-free framing through
    physical EOF. Hashes and 64-byte values remain semantically unnamed.
    """

    if len(data) < 8:
        raise BinaryFormatError(f"{source}: missing 8-byte FacBoneTRS header")
    lookup_end_offset, unit_record_count = struct.unpack_from("<II", data, 0)
    if unit_record_count == 0:
        raise BinaryFormatError(f"{source}: unit record count must be positive")
    slot_table_end = 8 + unit_record_count * 8
    _need(data, 8, unit_record_count * 8, f"{source} lookup slot table")
    unit_table_start = (slot_table_end + 15) & ~15
    unit_table_end = unit_table_start + unit_record_count * 16
    _need(
        data,
        unit_table_start,
        unit_record_count * 16,
        f"{source} unit table",
    )
    expected_lookup_end = unit_table_end - 12
    if lookup_end_offset != expected_lookup_end:
        raise BinaryFormatError(
            f"{source}: lookup end {lookup_end_offset} != aligned unit-table "
            f"end minus 12 ({expected_lookup_end})"
        )

    lookup_bucket_ranges: list[tuple[int, int]] = []
    lookup_bucket_starts: list[int] = []
    nonempty_lookup_slots = 0
    lookup_bucket_count = 0
    for index in range(unit_record_count):
        bucket_offset, bucket_count = struct.unpack_from("<II", data, 8 + index * 8)
        if bucket_count == 0:
            if bucket_offset != 0:
                raise BinaryFormatError(
                    f"{source}: empty lookup slot {index} has nonzero offset "
                    f"{bucket_offset}"
                )
            continue
        nonempty_lookup_slots += 1
        if bucket_offset < slot_table_end - 4:
            raise BinaryFormatError(
                f"{source}: lookup slot {index} bucket offset {bucket_offset} "
                f"precedes allowed overlap boundary {slot_table_end - 4}"
            )
        byte_size = bucket_count * 16
        _need(data, bucket_offset, byte_size, f"{source} lookup slot {index} buckets")
        if bucket_offset + byte_size > lookup_end_offset:
            raise BinaryFormatError(
                f"{source}: lookup slot {index} buckets end past declared lookup "
                f"boundary {lookup_end_offset}"
            )
        lookup_bucket_ranges.append((bucket_offset, bucket_offset + byte_size))
        lookup_bucket_starts.extend(
            bucket_offset + bucket_index * 16 for bucket_index in range(bucket_count)
        )
        lookup_bucket_count += bucket_count
    if lookup_bucket_count != unit_record_count:
        raise BinaryFormatError(
            f"{source}: lookup bucket count {lookup_bucket_count} != unit record "
            f"count {unit_record_count}"
        )
    if len(set(lookup_bucket_starts)) != lookup_bucket_count:
        raise BinaryFormatError(f"{source}: lookup bucket records alias")
    ordered_lookup_ranges = sorted(lookup_bucket_ranges)
    for previous, current in zip(ordered_lookup_ranges, ordered_lookup_ranges[1:]):
        if current[0] < previous[1]:
            raise BinaryFormatError(
                f"{source}: lookup bucket ranges overlap at "
                f"[{current[0]}, {current[1]}) and "
                f"[{previous[0]}, {previous[1]})"
            )
    merged_lookup_buckets = _union(lookup_bucket_ranges)
    expected_lookup_range = [(slot_table_end - 4, lookup_end_offset)]
    if merged_lookup_buckets != expected_lookup_range:
        raise BinaryFormatError(
            f"{source}: lookup buckets do not exactly tile "
            f"[{slot_table_end - 4}, {lookup_end_offset})"
        )

    units: list[tuple[int, int, int]] = []
    for index in range(unit_record_count):
        row_offset = unit_table_start + index * 16
        bone_count, bones_offset, hash_key = struct.unpack_from("<IIQ", data, row_offset)
        units.append((bone_count, bones_offset, hash_key))
        if bone_count == 0:
            raise BinaryFormatError(
                f"{source}: unit {index} has zero bone-record count"
            )
        if bones_offset < unit_table_end - 8:
            raise BinaryFormatError(
                f"{source}: unit {index} bone list starts before allowed "
                f"eight-byte overlap boundary {unit_table_end - 8}"
            )
        _need(
            data,
            bones_offset,
            bone_count * 16,
            f"{source} unit {index} bone list",
        )

    unit_bone_ranges = [
        (bones_offset, bones_offset + bone_count * 16)
        for bone_count, bones_offset, _hash_key in units
    ]
    # Unit lists are independently addressed source ranges.  Aliasing would
    # make exact record accounting ambiguous, so reject it.
    previous_end = -1
    for start, end in sorted(unit_bone_ranges):
        if start < previous_end:
            raise BinaryFormatError(f"{source}: unit bone-list ranges overlap")
        previous_end = end

    merged_bone_ranges = _union(unit_bone_ranges)
    if len(merged_bone_ranges) != 1:
        raise BinaryFormatError(f"{source}: unit bone-list ranges contain gaps")
    bone_pool_start, bone_pool_end = merged_bone_ranges[0]
    if bone_pool_start != unit_table_end - 8:
        raise BinaryFormatError(
            f"{source}: bone pool starts at {bone_pool_start}, expected "
            f"unit-table end minus 8 ({unit_table_end - 8})"
        )

    trs_ranges: list[tuple[int, int]] = []
    total_bones = 0
    for unit_index, (bone_count, bones_offset, _hash_key) in enumerate(units):
        for bone_index in range(bone_count):
            row_offset = bones_offset + bone_index * 16
            bone_name_hash, trs_count, trs_offset = struct.unpack_from("<QII", data, row_offset)
            if trs_count <= 0:
                raise BinaryFormatError(
                    f"{source}: unit {unit_index} bone {bone_index} has zero TRS count"
                )
            byte_size = trs_count * 64
            if trs_offset < bone_pool_end:
                raise BinaryFormatError(
                    f"{source}: unit {unit_index} bone {bone_index} TRS starts "
                    f"before bone-pool end {bone_pool_end}"
                )
            _need(data, trs_offset, byte_size, f"{source} unit {unit_index} bone {bone_index} TRS")
            trs_ranges.append((trs_offset, trs_offset + byte_size))
            total_bones += 1

    ordered_trs = sorted(trs_ranges)
    for previous, current in zip(ordered_trs, ordered_trs[1:]):
        if current[0] < previous[1]:
            raise BinaryFormatError(
                f"{source}: TRS ranges overlap at "
                f"[{current[0]}, {current[1]}) and "
                f"[{previous[0]}, {previous[1]})"
            )
    merged_trs = _union(ordered_trs)
    if len(merged_trs) != 1:
        raise BinaryFormatError(f"{source}: TRS ranges contain gaps")
    if merged_trs[0][0] != bone_pool_end:
        raise BinaryFormatError(
            f"{source}: TRS pool starts at {merged_trs[0][0]}, bone pool ends "
            f"at {bone_pool_end}"
        )
    max_trs_end = max(end for _start, end in merged_trs)
    if max_trs_end != len(data):
        raise BinaryFormatError(
            f"{source}: final TRS range ends at {max_trs_end}, source ends at {len(data)}"
        )
    return FacBoneTRSSummary(
        source_length=len(data),
        lookup_end_offset=lookup_end_offset,
        lookup_slot_count=unit_record_count,
        nonempty_lookup_slot_count=nonempty_lookup_slots,
        lookup_bucket_count=lookup_bucket_count,
        lookup_bucket_ranges=tuple(merged_lookup_buckets),
        unit_table_start=unit_table_start,
        unit_table_end=unit_table_end,
        unit_record_count=unit_record_count,
        bone_count=total_bones,
        bone_pool_start=bone_pool_start,
        bone_pool_end=bone_pool_end,
        trs_range_count=len(trs_ranges),
        trs_element_stride=64,
        trs_bytes=sum(end - start for start, end in trs_ranges),
        max_trs_end=max_trs_end,
        unit_bone_ranges=tuple(_union(unit_bone_ranges)),
        trs_ranges=tuple(merged_trs),
        unaccounted_ranges=tuple(
            _complement(
                len(data),
                [
                    (0, slot_table_end),
                    *lookup_bucket_ranges,
                    (unit_table_start, unit_table_end),
                    *unit_bone_ranges,
                    *trs_ranges,
                ],
            )
        ),
        consumed_bytes=len(data),
    )


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return _bytes_digest(data) | {"path": str(path)}


def _bytes_digest(data: bytes) -> dict[str, Any]:
    return {
        "length": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data).hexdigest(),
    }


def _join_outer_ledger(
    ledger_path: Path,
    input_set_sha256: str,
    expectations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Fail closed unless every logical payload joins one certified ledger row."""
    expected_input_set = input_set_sha256.upper()
    rows: dict[str, dict[str, Any]] = {}
    audit_headers: list[dict[str, Any]] = []
    opener = gzip.open if ledger_path.suffix.casefold() == ".gz" else open
    with opener(ledger_path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BinaryFormatError(
                    f"{ledger_path}: malformed JSONL row {line_number}: {exc}"
                ) from exc
            record_type = row.get("recordType")
            if record_type == "audit_header":
                audit_headers.append(row)
                continue
            virtual_path = row.get("virtualPath")
            if virtual_path not in expectations:
                continue
            if record_type != "file":
                raise BinaryFormatError(
                    f"{ledger_path}: target {virtual_path} has recordType "
                    f"{record_type!r}, expected 'file'"
                )
            if virtual_path in rows:
                raise BinaryFormatError(
                    f"{ledger_path}: duplicate outer-ledger row for {virtual_path}"
                )
            rows[virtual_path] = row

    if len(audit_headers) != 1:
        raise BinaryFormatError(
            f"{ledger_path}: expected exactly one audit_header, found "
            f"{len(audit_headers)}"
        )
    audit_header = audit_headers[0]
    if audit_header.get("schemaVersion") != OUTER_LEDGER_SCHEMA_VERSION:
        raise BinaryFormatError(
            f"{ledger_path}: unsupported audit_header schemaVersion "
            f"{audit_header.get('schemaVersion')!r}; expected "
            f"{OUTER_LEDGER_SCHEMA_VERSION}"
        )
    header_input_set = str(audit_header.get("inputSetSha256", "")).upper()
    if header_input_set != expected_input_set:
        raise BinaryFormatError(
            f"{ledger_path}: audit_header input-set SHA-256 mismatch "
            f"expected={expected_input_set} actual={header_input_set or '<missing>'}"
        )

    missing = sorted(set(expectations) - set(rows))
    if missing:
        raise BinaryFormatError(
            f"{ledger_path}: missing outer-ledger rows: {missing}"
        )

    joined_rows = []
    for virtual_path, expected in expectations.items():
        row = rows[virtual_path]
        if str(row.get("inputSetSha256", "")).upper() != expected_input_set:
            raise BinaryFormatError(
                f"{virtual_path}: input-set SHA-256 mismatch"
            )
        if row.get("status") != "verified" or row.get("boundaryStatus") != "boundary_verified":
            raise BinaryFormatError(
                f"{virtual_path}: outer ledger is not boundary-verified"
            )
        for field in ("offset", "length"):
            if row.get(field) != expected[field]:
                raise BinaryFormatError(
                    f"{virtual_path}: outer-ledger {field} mismatch "
                    f"expected={expected[field]} actual={row.get(field)!r}"
                )
        if row.get("actualBytesRead") != expected["length"]:
            raise BinaryFormatError(
                f"{virtual_path}: outer-ledger actualBytesRead mismatch"
            )
        actual_md5 = str(row.get("recomputedFileDataMd5", "")).casefold()
        if actual_md5 != expected["md5"].casefold():
            raise BinaryFormatError(
                f"{virtual_path}: outer-ledger MD5 mismatch "
                f"expected={expected['md5']} actual={actual_md5 or '<missing>'}"
            )
        ledger_physical = Path(str(row.get("physicalChunkPath", ""))).resolve()
        expected_physical = Path(expected["physical_chunk_path"]).resolve()
        if ledger_physical != expected_physical:
            raise BinaryFormatError(
                f"{virtual_path}: physical chunk mismatch "
                f"expected={expected_physical} actual={ledger_physical}"
            )
        joined_rows.append({
            "virtualPath": virtual_path,
            "offset": expected["offset"],
            "length": expected["length"],
            "md5": expected["md5"],
            "physicalChunkPath": str(expected_physical),
            "status": "boundary_verified_exact_identity_join",
        })
    return {
        "outerLedger": str(ledger_path),
        "schemaVersion": OUTER_LEDGER_SCHEMA_VERSION,
        "inputSetSha256": expected_input_set,
        "rows": joined_rows,
        "complete": True,
    }


def build_current_report(
    *,
    init_path: Path,
    chunk_path: Path,
    fac_offset: int,
    fac_length: int,
    main_offset: int,
    main_length: int,
    outer_ledger_path: Path,
    input_set_sha256: str,
) -> dict[str, Any]:
    chunk = chunk_path.read_bytes()
    _need(chunk, fac_offset, fac_length, "FacBoneTRS chunk slice")
    _need(chunk, main_offset, main_length, "StringPathHash chunk slice")
    init = init_path.read_bytes()
    fac_data = chunk[fac_offset : fac_offset + fac_length]
    main_data = chunk[main_offset : main_offset + main_length]
    init_identity = _bytes_digest(init)
    fac_identity = _bytes_digest(fac_data)
    main_identity = _bytes_digest(main_data)
    outer_ledger_join = _join_outer_ledger(
        outer_ledger_path,
        input_set_sha256,
        {
            INIT_STRING_PATH: {
                **init_identity,
                "offset": 0,
                "physical_chunk_path": init_path,
            },
            FAC_BONE_TRS_PATH: {
                **fac_identity,
                "offset": fac_offset,
                "physical_chunk_path": chunk_path,
            },
            STRING_PATH_HASH_PATH: {
                **main_identity,
                "offset": main_offset,
                "physical_chunk_path": chunk_path,
            },
        },
    )
    return {
        "format": "endfield-extend-data-inner-v2",
        "evidence_boundary": (
            "All reported ranges are bounded and exactly consumed. Hash/key roles "
            "and the semantic type of each 64-byte FacBoneTRS value remain unnamed."
        ),
        "source": {
            "init_string_path_hash": _file_digest(init_path),
            "chunk": _file_digest(chunk_path),
        },
        "provenance": outer_ledger_join,
        "payloads": {
            "InitStringPathHash.bin": {
                "file": str(init_path),
                "summary": parse_string_path_hash(init, source=str(init_path)).to_dict(),
            },
            "FacBoneTRS.bin": {
                "chunk_offset": fac_offset,
                "chunk_length": fac_length,
                "identity": fac_identity,
                "summary": parse_fac_bone_trs(
                    fac_data,
                    source=f"{chunk_path}@{fac_offset}+{fac_length}",
                ).to_dict(),
            },
            "StringPathHash.bin": {
                "chunk_offset": main_offset,
                "chunk_length": main_length,
                "identity": main_identity,
                "summary": parse_string_path_hash(
                    main_data,
                    source=f"{chunk_path}@{main_offset}+{main_length}",
                ).to_dict(),
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init", required=True, type=Path)
    parser.add_argument("--chunk", required=True, type=Path)
    parser.add_argument("--fac-offset", required=True, type=int)
    parser.add_argument("--fac-length", required=True, type=int)
    parser.add_argument("--main-offset", required=True, type=int)
    parser.add_argument("--main-length", required=True, type=int)
    parser.add_argument("--outer-ledger", required=True, type=Path)
    parser.add_argument("--input-set-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_current_report(
        init_path=args.init,
        chunk_path=args.chunk,
        fac_offset=args.fac_offset,
        fac_length=args.fac_length,
        main_offset=args.main_offset,
        main_length=args.main_length,
        outer_ledger_path=args.outer_ledger,
        input_set_sha256=args.input_set_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
