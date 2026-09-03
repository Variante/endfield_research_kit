"""Conservative parser for the observed Terrain TRET framing.

This module intentionally exposes byte ranges and integer encodings only.  The
six little-endian words after the version are not assigned semantic names; the
decoded payload remains opaque.
"""

from dataclasses import dataclass

from scripts.game_data.inverted_lz4 import decompress_inverted_lz4


MAGIC = b"TRET"
FIXED_BODY_PREFIX_SIZE = 20
SUPPORTED_BODY_VERSION = 1


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
    opaque_payload: bytes


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

    return TretRecord(
        raw_length=len(raw),
        storage_mode=storage_mode,
        declared_decoded_length=declared_length,
        encoded_prefix=raw[:4] if storage_mode == "inverted_lz4" else b"",
        decoded_length=len(body),
        body_fixed_prefix=body[:FIXED_BODY_PREFIX_SIZE],
        body_version_u32le=body_version,
        body_u16le_offsets_8_18=tuple(u16(offset) for offset in range(8, 20, 2)),
        body_payload_length_u32le=body_payload_length,
        opaque_payload=body[FIXED_BODY_PREFIX_SIZE:],
    )
