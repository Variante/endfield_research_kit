"""Strict framing for current Endfield IrradianceVolume files.

This module intentionally stops at proven framing.  The 16-byte region records
are retained as opaque bytes: their internal fields and ordering have not been
established by this parser.  It also validates the independently proven
filename table in v3/legacy ``index.bytes`` files.

For numeric index magic ``0x03000002``, and for single-filename
``0x03000003`` indexes, the current format has one referenced payload and an
exact index-resident byte-range directory. The directory records remain eight
or nine opaque little-endian words. Words 2 and 3 are exposed as a byte
interval only because the complete record sequence tiles the separately read
payload from offset zero through EOF without gaps or overlaps; no
renderer/coefficient meaning is assigned to any word.
"""

from __future__ import annotations

import io
import math
import re
import struct
from dataclasses import dataclass
from typing import BinaryIO, Mapping


REGION_HEADER_SIZE = 44
REGION_RECORD_SIZE = 16
REGION_HEADER_WORD0 = 4096
MAX_DIMENSION = 1_000_000
INDEX_HEADER_SIZE = 4
INDEX_MAGIC_V3_SCENE = 0x03000003
INDEX_MAGIC_V3_GACHA = 0x03000002
INDEX_MAGIC_LEGACY_GACHA = 0x01000043
INDEX_MAGICS = frozenset(
    (INDEX_MAGIC_V3_SCENE, INDEX_MAGIC_V3_GACHA, INDEX_MAGIC_LEGACY_GACHA)
)
MAX_INDEX_SIZE = 64 * 1024 * 1024
MAX_INDEX_FILENAME_COUNT = 1_000_000
MAX_INDEX_FILENAME_BYTES = 4096
INDEXED_PAYLOAD_SCHEMA_VERSION = 1
INDEXED_PAYLOAD_OPAQUE_PREFIX_SIZE = 184
INDEXED_PAYLOAD_RECORD_SIZE = 32
INDEXED_PAYLOAD_SCENE_RECORD_SIZE = 36
MAX_INDEXED_PAYLOAD_RECORDS = 1_000_000
_INDEX_FILENAME_RE = re.compile(r"iv_[0-9]+(?:_[0-9]+){1,2}\.bytes\Z")


class IrradianceFormatError(ValueError):
    """Raised when a region envelope is malformed or not fully consumed."""


@dataclass(frozen=True)
class RegionIvHeader:
    header_word0: int
    header_size: int
    header_floats: tuple[float, float, float, float, float, float]
    shape: tuple[int, int, int]

    @property
    def record_count(self) -> int:
        return self.shape[0] * self.shape[1] * self.shape[2]

    @property
    def record_bytes(self) -> int:
        return self.record_count * REGION_RECORD_SIZE


@dataclass(frozen=True)
class IrradianceIndex:
    """The proven outer/index filename framing only.

    ``opaque_remainder_length`` deliberately records a length rather than
    retaining or interpreting the remainder.  ``magic`` is the original
    numeric little-endian value so the v3 scene, v3 Gacha, and legacy Gacha
    identities cannot be folded together.
    """

    magic: int
    table_offset: int
    filename_count: int
    filenames: tuple[str, ...]
    table_end: int
    opaque_remainder_length: int


@dataclass(frozen=True)
class IndexedPayloadRange:
    """One opaque index record plus its proven byte interval."""

    words: tuple[int, ...]

    @property
    def offset(self) -> int:
        return self.words[2]

    @property
    def length(self) -> int:
        return self.words[3]

    @property
    def end(self) -> int:
        return self.offset + self.length


@dataclass(frozen=True)
class IndexedPayloadFraming:
    """Versioned structural framing for one index-directed payload.

    ``opaque_prefix_*`` bounds bytes that are deliberately not interpreted.
    ``records`` retain all eight numeric words so unproven field names are not
    introduced by the parser.
    """

    schema_version: int
    magic: int
    payload_filename: str
    filename_table_end: int
    opaque_prefix_start: int
    opaque_prefix_end: int
    opaque_suffix_start: int
    opaque_suffix_end: int
    directory_offset: int
    record_count: int
    record_size: int
    records: tuple[IndexedPayloadRange, ...]
    directory_end: int
    payload_length: int


@dataclass(frozen=True)
class IndexedPayloadGroup:
    """One filename-bound group whose records independently tile its payload."""

    payload_filename: str
    first_record_index: int
    records: tuple[IndexedPayloadRange, ...]
    payload_length: int


@dataclass(frozen=True)
class GroupedIndexedPayloadFraming:
    """Exact multi-filename directory framing for numeric magic 0x03000003."""

    schema_version: int
    magic: int
    payload_filenames: tuple[str, ...]
    filename_table_end: int
    opaque_prefix_start: int
    opaque_prefix_end: int
    opaque_suffix_start: int
    opaque_suffix_end: int
    directory_offset: int
    directory_end: int
    record_count: int
    record_size: int
    groups: tuple[IndexedPayloadGroup, ...]


def _read_exact(stream: BinaryIO, count: int, field: str) -> bytes:
    if count < 0:
        raise IrradianceFormatError(f"{field}: negative read length {count}")
    data = stream.read(count)
    if data is None or len(data) != count:
        actual = 0 if data is None else len(data)
        raise IrradianceFormatError(
            f"{field}: short read expected {count}, actual {actual}"
        )
    return data


def _checked_record_bytes(shape: tuple[int, int, int]) -> int:
    count = 1
    for axis, value in zip(("x", "y", "z"), shape):
        if value <= 0:
            raise IrradianceFormatError(f"shape.{axis}: expected positive value, got {value}")
        if value > MAX_DIMENSION:
            raise IrradianceFormatError(
                f"shape.{axis}: value {value} exceeds bound {MAX_DIMENSION}"
            )
        if count > (2**63 - 1) // value:
            raise IrradianceFormatError("shape product overflows signed 64-bit range")
        count *= value
    if count > (2**63 - 1) // REGION_RECORD_SIZE:
        raise IrradianceFormatError("record byte count overflows signed 64-bit range")
    return count * REGION_RECORD_SIZE


def read_region_header(stream: BinaryIO) -> RegionIvHeader:
    raw = _read_exact(stream, REGION_HEADER_SIZE, "region header")
    header_word0, header_size = struct.unpack_from("<II", raw, 0)
    floats = struct.unpack_from("<6f", raw, 8)
    shape = struct.unpack_from("<3I", raw, 32)
    if header_word0 != REGION_HEADER_WORD0:
        raise IrradianceFormatError(
            f"header_word0 mismatch expected {REGION_HEADER_WORD0}, actual {header_word0}"
        )
    if header_size != REGION_HEADER_SIZE:
        raise IrradianceFormatError(
            f"header_size mismatch expected {REGION_HEADER_SIZE}, actual {header_size}"
        )
    if not all(math.isfinite(value) for value in floats):
        raise IrradianceFormatError("header floats contain non-finite value")
    _checked_record_bytes(shape)
    return RegionIvHeader(header_word0, header_size, tuple(floats), tuple(shape))


def validate_region_stream(stream: BinaryIO) -> RegionIvHeader:
    """Validate a complete region file without retaining its record payload."""

    header = read_region_header(stream)
    expected = header.record_bytes
    remaining = expected
    while remaining:
        chunk = stream.read(min(1024 * 1024, remaining))
        if not chunk:
            raise IrradianceFormatError(
                f"region records: short read expected {expected}, actual {expected - remaining}"
            )
        remaining -= len(chunk)
    extra = stream.read(1)
    if extra:
        raise IrradianceFormatError(
            f"region records: trailing bytes after expected {expected}: actual at least {expected + 1}"
        )
    return header


def parse_region_bytes(data: bytes) -> RegionIvHeader:
    """Validate fixture-sized bytes with the same exact-consumption rules."""

    return validate_region_stream(io.BytesIO(data))


def _index_filename_candidate(
    data: bytes, table_offset: int
) -> tuple[IrradianceIndex | None, str | None]:
    """Try one even-aligned count offset without guessing other fields."""

    if table_offset + 4 > len(data):
        return None, "count truncated"
    count = struct.unpack_from("<I", data, table_offset)[0]
    if count > MAX_INDEX_FILENAME_COUNT:
        return None, f"count overflow {count} > {MAX_INDEX_FILENAME_COUNT}"
    if count == 0:
        return None, None

    cursor = table_offset + 4
    names: list[str] = []
    for index in range(count):
        if cursor + 4 > len(data):
            return None, f"entry {index}: length truncated"
        length = struct.unpack_from("<I", data, cursor)[0]
        if length == 0 or length % 2:
            return None, f"entry {index}: invalid UTF-16LE byte length {length}"
        if length > MAX_INDEX_FILENAME_BYTES:
            return None, (
                f"entry {index}: filename length {length} exceeds bound "
                f"{MAX_INDEX_FILENAME_BYTES}"
            )
        string_offset = cursor + 4
        string_end = string_offset + length
        if string_end > len(data):
            return None, f"entry {index}: string truncated"
        try:
            name = data[string_offset:string_end].decode("utf-16le", "strict")
        except UnicodeDecodeError as exc:
            return None, f"entry {index}: invalid UTF-16LE ({exc.reason})"
        if not _INDEX_FILENAME_RE.fullmatch(name):
            return None, f"entry {index}: invalid filename {name!r}"
        names.append(name)
        cursor = string_end

    if len(set(names)) != len(names):
        return None, "duplicate filename in table"
    return (
        IrradianceIndex(
            magic=struct.unpack_from("<I", data, 0)[0],
            table_offset=table_offset,
            filename_count=count,
            filenames=tuple(names),
            table_end=cursor,
            opaque_remainder_length=len(data) - cursor,
        ),
        None,
    )


def parse_index_bytes(data: bytes) -> IrradianceIndex:
    """Validate the proven index filename table and retain the tail as opaque.

    The table start is not fixed across current files, so every even byte
    offset after the magic is considered.  A candidate is valid only when its
    explicit count and all length-prefixed strings form the complete current
    ``iv_*.bytes`` filename convention.  Exactly one candidate is required;
    this makes table-boundary ambiguity fail closed.  Bytes after the table
    are intentionally not parsed.
    """

    if len(data) < INDEX_HEADER_SIZE:
        raise IrradianceFormatError(
            f"index header: short read expected {INDEX_HEADER_SIZE}, actual {len(data)}"
        )
    if len(data) > MAX_INDEX_SIZE:
        raise IrradianceFormatError(
            f"index size {len(data)} exceeds bound {MAX_INDEX_SIZE}"
        )
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic not in INDEX_MAGICS:
        raise IrradianceFormatError(f"index magic unsupported: 0x{magic:08x}")

    candidates: list[IrradianceIndex] = []
    diagnostics: list[str] = []
    for table_offset in range(INDEX_HEADER_SIZE, len(data) - 3, 2):
        candidate, diagnostic = _index_filename_candidate(data, table_offset)
        if candidate is not None:
            candidates.append(candidate)
        elif diagnostic is not None and len(diagnostics) < 8:
            diagnostics.append(f"offset {table_offset}: {diagnostic}")

    if len(candidates) != 1:
        if len(candidates) > 1:
            offsets = ", ".join(str(item.table_offset) for item in candidates[:8])
            raise IrradianceFormatError(
                f"index filename table boundary ambiguous: "
                f"{len(candidates)} candidates ({offsets})"
            )
        detail = "; ".join(diagnostics) if diagnostics else "no candidate"
        raise IrradianceFormatError(f"index filename table not found: {detail}")
    return candidates[0]


def parse_indexed_payload_framing(
    data: bytes, payload_length: int | None = None
) -> IndexedPayloadFraming:
    """Parse an exact index-to-payload byte-range directory.

    Numeric magic ``0x03000002`` has a fixed directory position and a 32-byte
    record width.  Numeric magic ``0x03000003`` with exactly one filename uses
    36-byte records; its directory is accepted only when exactly one aligned
    candidate tiles the independently supplied payload length.  Bytes before
    and after either directory are explicitly opaque.
    """

    index = parse_index_bytes(data)
    if index.magic not in (INDEX_MAGIC_V3_GACHA, INDEX_MAGIC_V3_SCENE):
        raise IrradianceFormatError(
            f"indexed payload framing unsupported for numeric magic "
            f"0x{index.magic:08x}"
        )
    if index.filename_count != 1:
        raise IrradianceFormatError(
            f"indexed payload framing requires exactly one filename, "
            f"actual {index.filename_count}"
        )

    def read_candidate(
        directory_offset: int, record_size: int, require_index_eof: bool
    ) -> tuple[int, int, tuple[IndexedPayloadRange, ...], int]:
        if directory_offset + 4 > len(data):
            raise IrradianceFormatError(
                f"indexed payload directory count: short read expected end "
                f"{directory_offset + 4}, actual {len(data)}"
            )
        count = struct.unpack_from("<I", data, directory_offset)[0]
        if count == 0:
            raise IrradianceFormatError("indexed payload directory count is zero")
        if count > MAX_INDEXED_PAYLOAD_RECORDS:
            raise IrradianceFormatError(
                f"indexed payload directory count {count} exceeds bound "
                f"{MAX_INDEXED_PAYLOAD_RECORDS}"
            )
        if count > (2**63 - 1 - directory_offset - 4) // record_size:
            raise IrradianceFormatError("indexed payload directory byte count overflows")
        directory_end = directory_offset + 4 + count * record_size
        if directory_end > len(data) or (require_index_eof and directory_end != len(data)):
            relation = "truncated" if directory_end > len(data) else "trailing bytes"
            raise IrradianceFormatError(
                f"indexed payload directory {relation}: expected EOF {directory_end}, "
                f"actual {len(data)}"
            )

        records: list[IndexedPayloadRange] = []
        expected_offset = 0
        cursor = directory_offset + 4
        for record_index in range(count):
            words = struct.unpack_from(f"<{record_size // 4}I", data, cursor)
            record = IndexedPayloadRange(tuple(words))
            if record.length == 0:
                raise IrradianceFormatError(
                    f"indexed payload record {record_index}: zero byte length"
                )
            if record.offset != expected_offset:
                relation = "overlap" if record.offset < expected_offset else "gap"
                raise IrradianceFormatError(
                    f"indexed payload record {record_index}: {relation}; expected "
                    f"offset {expected_offset}, actual {record.offset}"
                )
            if record.end > 0xFFFFFFFF:
                raise IrradianceFormatError(
                    f"indexed payload record {record_index}: interval end "
                    f"{record.end} exceeds uint32 range"
                )
            records.append(record)
            expected_offset = record.end
            cursor += record_size
        return count, directory_end, tuple(records), expected_offset

    if index.magic == INDEX_MAGIC_V3_GACHA:
        opaque_start = index.table_end
        directory_offset = opaque_start + INDEXED_PAYLOAD_OPAQUE_PREFIX_SIZE
        record_size = INDEXED_PAYLOAD_RECORD_SIZE
        count, directory_end, records, expected_offset = read_candidate(
            directory_offset, record_size, True
        )
        if payload_length is not None and expected_offset != payload_length:
            raise IrradianceFormatError(
                f"indexed payload length mismatch: expected {expected_offset}, "
                f"actual {payload_length}"
            )
    else:
        if payload_length is None:
            raise IrradianceFormatError(
                "numeric magic 0x03000003 requires an authenticated payload length"
            )
        record_size = INDEXED_PAYLOAD_SCENE_RECORD_SIZE
        candidates = []
        first_aligned_offset = (index.table_end + 3) & ~3
        for directory_offset in range(first_aligned_offset, len(data) - 3, 4):
            try:
                candidate = read_candidate(directory_offset, record_size, False)
            except IrradianceFormatError:
                continue
            if candidate[3] == payload_length:
                candidates.append((directory_offset, candidate))
        if len(candidates) != 1:
            offsets = ", ".join(str(offset) for offset, _ in candidates[:8])
            detail = f" ({offsets})" if offsets else ""
            raise IrradianceFormatError(
                f"indexed payload directory boundary ambiguous for numeric magic "
                f"0x03000003: {len(candidates)} candidates{detail}"
            )
        directory_offset, candidate = candidates[0]
        count, directory_end, records, expected_offset = candidate
        opaque_start = index.table_end

    return IndexedPayloadFraming(
        schema_version=INDEXED_PAYLOAD_SCHEMA_VERSION,
        magic=index.magic,
        payload_filename=index.filenames[0],
        filename_table_end=index.table_end,
        opaque_prefix_start=opaque_start,
        opaque_prefix_end=directory_offset,
        opaque_suffix_start=directory_end,
        opaque_suffix_end=len(data),
        directory_offset=directory_offset,
        record_count=count,
        record_size=record_size,
        records=records,
        directory_end=directory_end,
        payload_length=expected_offset,
    )


def parse_grouped_indexed_payload_framing(
    data: bytes, payload_lengths: Mapping[str, int]
) -> GroupedIndexedPayloadFraming:
    """Parse a unique multi-filename scene-v3 byte-range directory.

    The authenticated lengths must name exactly the filename-table entries.
    Directory records are grouped in filename-table order.  Every group must
    restart at offset zero and tile its own payload through EOF without gaps or
    overlaps.  All other index bytes remain explicitly opaque.
    """

    index = parse_index_bytes(data)
    if index.magic != INDEX_MAGIC_V3_SCENE:
        raise IrradianceFormatError(
            f"grouped indexed payload framing unsupported for numeric magic "
            f"0x{index.magic:08x}"
        )
    if index.filename_count < 2:
        raise IrradianceFormatError(
            f"grouped indexed payload framing requires at least two filenames, "
            f"actual {index.filename_count}"
        )
    expected_names = set(index.filenames)
    actual_names = set(payload_lengths)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise IrradianceFormatError(
            f"grouped indexed payload filenames mismatch: missing={missing[:8]}, "
            f"extra={extra[:8]}"
        )
    ordered_lengths = []
    for filename in index.filenames:
        length = payload_lengths[filename]
        if not isinstance(length, int) or isinstance(length, bool) or length <= 0:
            raise IrradianceFormatError(
                f"grouped indexed payload {filename!r}: invalid length {length!r}"
            )
        if length > 0xFFFFFFFF:
            raise IrradianceFormatError(
                f"grouped indexed payload {filename!r}: length {length} exceeds "
                f"uint32 range"
            )
        ordered_lengths.append(length)

    candidates = []
    record_size = INDEXED_PAYLOAD_SCENE_RECORD_SIZE
    first_aligned_offset = (index.table_end + 3) & ~3
    for directory_offset in range(first_aligned_offset, len(data) - 3, 4):
        count = struct.unpack_from("<I", data, directory_offset)[0]
        if count == 0 or count > MAX_INDEXED_PAYLOAD_RECORDS:
            continue
        if count > (len(data) - directory_offset - 4) // record_size:
            continue
        directory_end = directory_offset + 4 + count * record_size
        cursor = directory_offset + 4
        group_index = 0
        group_start_record = 0
        expected_offset = 0
        group_records: list[IndexedPayloadRange] = []
        groups: list[IndexedPayloadGroup] = []
        valid = True
        for record_index in range(count):
            words = struct.unpack_from("<9I", data, cursor)
            record = IndexedPayloadRange(tuple(words))
            if record.length == 0 or record.end > 0xFFFFFFFF:
                valid = False
                break
            target_length = ordered_lengths[group_index]
            if expected_offset == target_length:
                groups.append(
                    IndexedPayloadGroup(
                        payload_filename=index.filenames[group_index],
                        first_record_index=group_start_record,
                        records=tuple(group_records),
                        payload_length=target_length,
                    )
                )
                group_index += 1
                if group_index >= len(ordered_lengths):
                    valid = False
                    break
                group_start_record = record_index
                group_records = []
                expected_offset = 0
                target_length = ordered_lengths[group_index]
            if record.offset != expected_offset or record.end > target_length:
                valid = False
                break
            group_records.append(record)
            expected_offset = record.end
            cursor += record_size
        if not valid or group_index != len(ordered_lengths) - 1:
            continue
        if expected_offset != ordered_lengths[group_index]:
            continue
        groups.append(
            IndexedPayloadGroup(
                payload_filename=index.filenames[group_index],
                first_record_index=group_start_record,
                records=tuple(group_records),
                payload_length=ordered_lengths[group_index],
            )
        )
        candidates.append((directory_offset, directory_end, tuple(groups)))

    if len(candidates) != 1:
        offsets = ", ".join(str(item[0]) for item in candidates[:8])
        detail = f" ({offsets})" if offsets else ""
        raise IrradianceFormatError(
            f"grouped indexed payload directory boundary ambiguous for numeric magic "
            f"0x03000003: {len(candidates)} candidates{detail}"
        )
    directory_offset, directory_end, groups = candidates[0]
    return GroupedIndexedPayloadFraming(
        schema_version=INDEXED_PAYLOAD_SCHEMA_VERSION,
        magic=index.magic,
        payload_filenames=index.filenames,
        filename_table_end=index.table_end,
        opaque_prefix_start=index.table_end,
        opaque_prefix_end=directory_offset,
        opaque_suffix_start=directory_end,
        opaque_suffix_end=len(data),
        directory_offset=directory_offset,
        directory_end=directory_end,
        record_count=sum(len(group.records) for group in groups),
        record_size=record_size,
        groups=groups,
    )


def validate_grouped_indexed_payload_streams(
    index_data: bytes,
    payload_streams: Mapping[str, BinaryIO],
    payload_lengths: Mapping[str, int],
) -> GroupedIndexedPayloadFraming:
    """Validate complete bounded payload streams against grouped index ranges."""

    framing = parse_grouped_indexed_payload_framing(index_data, payload_lengths)
    if set(payload_streams) != set(framing.payload_filenames):
        missing = sorted(set(framing.payload_filenames) - set(payload_streams))
        extra = sorted(set(payload_streams) - set(framing.payload_filenames))
        raise IrradianceFormatError(
            f"grouped indexed payload streams mismatch: missing={missing[:8]}, "
            f"extra={extra[:8]}"
        )
    for group in framing.groups:
        stream = payload_streams[group.payload_filename]
        actual = 0
        for record_index, record in enumerate(group.records):
            remaining = record.length
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise IrradianceFormatError(
                        f"grouped indexed payload {group.payload_filename!r} record "
                        f"{record_index}: short read expected {record.length}, actual "
                        f"{record.length - remaining}; payload total expected "
                        f"{group.payload_length}, actual {actual}"
                    )
                remaining -= len(chunk)
                actual += len(chunk)
        if stream.read(1):
            raise IrradianceFormatError(
                f"grouped indexed payload {group.payload_filename!r}: trailing bytes "
                f"after expected {group.payload_length}: actual at least "
                f"{group.payload_length + 1}"
            )
    return framing


def parse_grouped_indexed_payload_bytes(
    index_data: bytes, payloads: Mapping[str, bytes]
) -> GroupedIndexedPayloadFraming:
    """Fixture-sized convenience wrapper for grouped payload framing."""

    return validate_grouped_indexed_payload_streams(
        index_data,
        {filename: io.BytesIO(data) for filename, data in payloads.items()},
        {filename: len(data) for filename, data in payloads.items()},
    )


def validate_indexed_payload_stream(
    index_data: bytes, payload_stream: BinaryIO, payload_length: int | None = None
) -> IndexedPayloadFraming:
    """Validate a complete bounded payload stream against its index ranges."""

    index = parse_index_bytes(index_data)
    framing = parse_indexed_payload_framing(
        index_data,
        payload_length if index.magic == INDEX_MAGIC_V3_SCENE else None,
    )
    actual = 0
    for record_index, record in enumerate(framing.records):
        remaining = record.length
        while remaining:
            chunk = payload_stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise IrradianceFormatError(
                    f"indexed payload record {record_index}: short read expected "
                    f"{record.length}, actual {record.length - remaining}; "
                    f"payload total expected {framing.payload_length}, actual {actual}"
                )
            remaining -= len(chunk)
            actual += len(chunk)
    extra = payload_stream.read(1)
    if extra:
        raise IrradianceFormatError(
            f"indexed payload: trailing bytes after expected {framing.payload_length}: "
            f"actual at least {framing.payload_length + 1}"
        )
    return framing


def parse_indexed_payload_bytes(
    index_data: bytes, payload_data: bytes
) -> IndexedPayloadFraming:
    """Fixture-sized convenience wrapper for exact indexed payload framing."""

    return validate_indexed_payload_stream(
        index_data, io.BytesIO(payload_data), len(payload_data)
    )
