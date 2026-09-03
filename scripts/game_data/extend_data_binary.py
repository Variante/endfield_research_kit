"""Conservative readers for the exact-build ExtendData binary payloads.

The readers in this module intentionally describe framing and bounds only.  In
particular, the hash fields and the first StringPathHash bucket word are kept
as raw values, and FacBoneTRS's 64-byte values are not assigned a managed type.
They are useful for audit reports and tests; they are not game-runtime
reimplementations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


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
    header_size: int
    unit_record_count: int
    valid_unit_count: int
    sentinel_count: int
    bone_count: int
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
            "header_size": self.header_size,
            "unit_record_count": self.unit_record_count,
            "valid_unit_count": self.valid_unit_count,
            "sentinel_count": self.sentinel_count,
            "bone_count": self.bone_count,
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
    unit_record_count: int,
    source: str = "<memory>",
    allow_final_sentinel: bool = True,
) -> FacBoneTRSSummary:
    """Parse the observed FacBoneTRS table and bounded 64-byte TRS ranges.

    ``unit_record_count`` is explicit because the file's preceding 768 bytes
    have not been assigned a count meaning.  A final invalid unit row may be a
    sentinel in the current file; earlier invalid rows are always rejected.
    """

    header_size = 768
    if unit_record_count <= 0:
        raise BinaryFormatError(f"{source}: unit_record_count must be positive")
    _need(data, 0, header_size + unit_record_count * 16, f"{source} header/unit table")
    unit_table_end = header_size + unit_record_count * 16
    units: list[tuple[int, int, int]] = []
    valid_units: list[tuple[int, int, int]] = []
    sentinel_count = 0
    for index in range(unit_record_count):
        row_offset = header_size + index * 16
        bone_count, bones_offset, hash_key = struct.unpack_from("<IIQ", data, row_offset)
        units.append((bone_count, bones_offset, hash_key))
        valid = bone_count > 0 and bones_offset >= unit_table_end
        if valid:
            valid = bones_offset + bone_count * 16 <= len(data)
        # The current file's final row points at the beginning of the TRS
        # pool and is in-bounds as a byte range, but does not decode as a bone
        # list.  Probe its entries before classifying it as a real unit.
        if valid:
            for bone_index in range(bone_count):
                bone_row = bones_offset + bone_index * 16
                _bone_hash, trs_count, trs_offset = struct.unpack_from(
                    "<QII", data, bone_row
                )
                if (
                    trs_count == 0
                    or trs_offset < unit_table_end
                    or trs_offset + trs_count * 64 > len(data)
                ):
                    valid = False
                    break
        if not valid:
            if allow_final_sentinel and index == unit_record_count - 1:
                sentinel_count += 1
                continue
            raise BinaryFormatError(
                f"{source}: unit {index} bone range "
                f"[{bones_offset}, {bones_offset + bone_count * 16}) is invalid"
            )
        valid_units.append((bone_count, bones_offset, hash_key))

    if not valid_units:
        raise BinaryFormatError(f"{source}: no valid FacBoneTRS units")

    unit_bone_ranges = [
        (bones_offset, bones_offset + bone_count * 16)
        for bone_count, bones_offset, _hash_key in valid_units
    ]
    # Unit lists are independently addressed source ranges.  Aliasing would
    # make exact record accounting ambiguous, so reject it.
    previous_end = -1
    for start, end in sorted(unit_bone_ranges):
        if start < previous_end:
            raise BinaryFormatError(f"{source}: unit bone-list ranges overlap")
        previous_end = end

    trs_ranges: list[tuple[int, int]] = []
    total_bones = 0
    for unit_index, (bone_count, bones_offset, _hash_key) in enumerate(valid_units):
        for bone_index in range(bone_count):
            row_offset = bones_offset + bone_index * 16
            bone_name_hash, trs_count, trs_offset = struct.unpack_from("<QII", data, row_offset)
            if trs_count <= 0:
                raise BinaryFormatError(
                    f"{source}: unit {unit_index} bone {bone_index} has zero TRS count"
                )
            byte_size = trs_count * 64
            if trs_offset < unit_table_end:
                raise BinaryFormatError(
                    f"{source}: unit {unit_index} bone {bone_index} TRS starts in table"
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
    max_trs_end = max(end for _start, end in merged_trs)
    if max_trs_end != len(data):
        raise BinaryFormatError(
            f"{source}: final TRS range ends at {max_trs_end}, source ends at {len(data)}"
        )
    return FacBoneTRSSummary(
        source_length=len(data),
        header_size=header_size,
        unit_record_count=unit_record_count,
        valid_unit_count=len(valid_units),
        sentinel_count=sentinel_count,
        bone_count=total_bones,
        trs_range_count=len(trs_ranges),
        trs_element_stride=64,
        trs_bytes=sum(end - start for start, end in trs_ranges),
        max_trs_end=max_trs_end,
        unit_bone_ranges=tuple(_union(unit_bone_ranges)),
        trs_ranges=tuple(merged_trs),
        unaccounted_ranges=tuple(
            _complement(
                len(data),
                [(0, header_size), (header_size, unit_table_end), *unit_bone_ranges, *trs_ranges],
            )
        ),
        consumed_bytes=len(data),
    )


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "length": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data).hexdigest(),
    }


def build_current_report(
    *,
    init_path: Path,
    chunk_path: Path,
    fac_offset: int,
    fac_length: int,
    main_offset: int,
    main_length: int,
    unit_record_count: int,
) -> dict[str, Any]:
    chunk = chunk_path.read_bytes()
    _need(chunk, fac_offset, fac_length, "FacBoneTRS chunk slice")
    _need(chunk, main_offset, main_length, "StringPathHash chunk slice")
    init = init_path.read_bytes()
    return {
        "format": "endfield-extend-data-inner-v1",
        "source": {
            "init_string_path_hash": _file_digest(init_path),
            "chunk": _file_digest(chunk_path),
        },
        "payloads": {
            "InitStringPathHash.bin": {
                "file": str(init_path),
                "summary": parse_string_path_hash(init, source=str(init_path)).to_dict(),
            },
            "FacBoneTRS.bin": {
                "chunk_offset": fac_offset,
                "chunk_length": fac_length,
                "summary": parse_fac_bone_trs(
                    chunk[fac_offset : fac_offset + fac_length],
                    unit_record_count=unit_record_count,
                    source=f"{chunk_path}@{fac_offset}+{fac_length}",
                ).to_dict(),
            },
            "StringPathHash.bin": {
                "chunk_offset": main_offset,
                "chunk_length": main_length,
                "summary": parse_string_path_hash(
                    chunk[main_offset : main_offset + main_length],
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
    parser.add_argument("--unit-record-count", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_current_report(
        init_path=args.init,
        chunk_path=args.chunk,
        fac_offset=args.fac_offset,
        fac_length=args.fac_length,
        main_offset=args.main_offset,
        main_length=args.main_length,
        unit_record_count=args.unit_record_count,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
