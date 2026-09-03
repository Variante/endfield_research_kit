"""Conservative parser for the observed Terrain TRET framing.

This module intentionally exposes byte ranges and integer encodings only.  The
six little-endian words after the version are not assigned semantic names.
Selected-build shapes may expose exact anonymous record ranges, while their
values and every unsupported body shape remain opaque.
"""

from dataclasses import dataclass

from scripts.game_data.inverted_lz4 import decompress_inverted_lz4


MAGIC = b"TRET"
FIXED_BODY_PREFIX_SIZE = 20
SUPPORTED_BODY_VERSION = 1

# Selected-build anonymous framing contracts.  The key is the four raw u16
# words at decoded offsets 8 through 14. Values are byte strides. Numeric words
# remain deliberately unnamed, and unobserved axis/count combinations fail
# closed rather than being generalized.
_OBSERVED_ANONYMOUS_LAYOUTS = {
    (34, 34, 1, 6): 2,
    (65, 65, 1, 6): 2,
    (132, 132, 1, 8): 4,
    (132, 132, 1, 100): 1,
    (132, 132, 1, 101): 1,
    (1024, 1024, 11, 5): 1,
}
# These two current shapes have a stable aggregate length, but candidate
# 16-byte-aligned splits leave non-zero bytes in would-be gaps and therefore do
# not certify those bytes as padding. Keep the complete body bounded and opaque.
_OBSERVED_BOUNDED_OPAQUE_LAYOUTS = {
    (1024, 1024, 11, 108): 1_398_128,
    (1024, 1024, 11, 109): 1_398_128,
}


@dataclass(frozen=True)
class TretAnonymousRecordRange:
    """One structurally tiled body range without a domain-field name."""

    index: int
    start_offset: int
    end_offset: int
    axis0_units: int
    axis1_units: int
    record_count: int
    record_stride: int


@dataclass(frozen=True)
class TretRecord:
    """Exact framing slices from one TRET-bearing record."""

    raw_length: int
    storage_mode: str
    declared_decoded_length: int | None
    encoded_prefix: bytes
    decoded_length: int
    body_fixed_prefix: bytes
    body_version_u32le: int
    body_u16le_offsets_8_18: tuple[int, int, int, int, int, int]
    body_payload_length_u32le: int
    anonymous_tiling_status: str
    anonymous_record_ranges: tuple[TretAnonymousRecordRange, ...]
    opaque_payload: bytes


def _frame_anonymous_record_ranges(
    body: bytes, words: tuple[int, int, int, int, int, int]
) -> tuple[str, tuple[TretAnonymousRecordRange, ...]]:
    """Tile the selected-build body using only anonymous header words."""

    axis0, axis1, range_count, _raw_layout_word = words[:4]
    if axis0 <= 0 or axis1 <= 0:
        raise ValueError(
            f"TRET anonymous axes must be positive: {axis0}, {axis1}"
        )
    layout_key = words[:4]
    opaque_length = _OBSERVED_BOUNDED_OPAQUE_LAYOUTS.get(layout_key)
    if opaque_length is not None:
        actual_length = len(body) - FIXED_BODY_PREFIX_SIZE
        if actual_length != opaque_length:
            raise ValueError(
                "TRET bounded opaque body length mismatch: "
                f"expected {opaque_length}, actual {actual_length}"
            )
        return "bounded_opaque_current_shape", ()
    try:
        record_stride = _OBSERVED_ANONYMOUS_LAYOUTS[layout_key]
    except KeyError as exc:
        raise ValueError(
            "unsupported TRET anonymous layout words: "
            f"words8_14={words[:4]}"
        ) from exc

    cursor = FIXED_BODY_PREFIX_SIZE
    ranges = []
    for index in range(range_count):
        current_axis0 = max(1, axis0 >> index)
        current_axis1 = max(1, axis1 >> index)
        record_count = current_axis0 * current_axis1
        data_length = record_count * record_stride
        end = cursor + data_length
        if end > len(body):
            raise ValueError(
                f"TRET anonymous range {index} exceeds decoded body: "
                f"end {end}, size {len(body)}"
            )
        ranges.append(
            TretAnonymousRecordRange(
                index=index,
                start_offset=cursor,
                end_offset=end,
                axis0_units=current_axis0,
                axis1_units=current_axis1,
                record_count=record_count,
                record_stride=record_stride,
            )
        )
        cursor = end
    if cursor != len(body):
        raise ValueError(
            f"TRET anonymous ranges end at {cursor}, decoded body ends at {len(body)}"
        )
    return "exact_anonymous_record_tiling", tuple(ranges)


def decode_terrain_envelope(raw: bytes) -> tuple[bytes, str, int | None]:
    """Decode raw TRET or a length-prefixed exact inverted-LZ4 envelope."""

    if raw.startswith(MAGIC):
        return raw, "raw", None
    if len(raw) < 5:
        raise ValueError("Terrain envelope lacks length and inverted-LZ4 body")
    expected = int.from_bytes(raw[:4], "little")
    decoded = decompress_inverted_lz4(raw[4:], expected)
    if not decoded.startswith(MAGIC):
        raise ValueError("decoded Terrain envelope does not begin with TRET")
    return decoded, "inverted_lz4", expected


def parse_tret_record(raw: bytes) -> TretRecord:
    """Parse only the validated TRET framing and return all remaining bytes opaque.

    The envelope is decoded before inspecting the TRET body.  The parser
    rejects missing magic and decoded bodies shorter than the observed fixed
    20-byte body prefix.  The final anonymous ``u32`` in that prefix must
    exactly equal the remaining body length, so truncation and trailing bytes
    cannot be hidden inside the opaque payload.
    """

    body, storage_mode, declared_length = decode_terrain_envelope(raw)
    if len(body) < FIXED_BODY_PREFIX_SIZE:
        raise ValueError(
            f"TRET body too short for fixed prefix: {len(body)} < {FIXED_BODY_PREFIX_SIZE}"
        )

    def u16(offset: int) -> int:
        return int.from_bytes(body[offset : offset + 2], "little")

    body_version = int.from_bytes(body[4:8], "little")
    if body_version != SUPPORTED_BODY_VERSION:
        raise ValueError(
            f"unsupported TRET body version: {body_version} != {SUPPORTED_BODY_VERSION}"
        )
    body_payload_length = int.from_bytes(body[16:20], "little")
    actual_body_payload_length = len(body) - FIXED_BODY_PREFIX_SIZE
    if body_payload_length != actual_body_payload_length:
        raise ValueError(
            "TRET body payload length mismatch: "
            f"declared {body_payload_length}, actual {actual_body_payload_length}"
        )

    words = tuple(u16(offset) for offset in range(8, 20, 2))
    anonymous_tiling_status, anonymous_record_ranges = _frame_anonymous_record_ranges(
        body, words
    )

    return TretRecord(
        raw_length=len(raw),
        storage_mode=storage_mode,
        declared_decoded_length=declared_length,
        encoded_prefix=raw[:4] if storage_mode == "inverted_lz4" else b"",
        decoded_length=len(body),
        body_fixed_prefix=body[:FIXED_BODY_PREFIX_SIZE],
        body_version_u32le=body_version,
        body_u16le_offsets_8_18=words,
        body_payload_length_u32le=body_payload_length,
        anonymous_tiling_status=anonymous_tiling_status,
        anonymous_record_ranges=anonymous_record_ranges,
        opaque_payload=body[FIXED_BODY_PREFIX_SIZE:],
    )
