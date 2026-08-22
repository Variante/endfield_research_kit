"""Stable audio identifier codecs shared by index and semantic builders."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


METADATA_MAGIC = 0xFAB11BAF

# ``vo_`` is a shipped Event namespace alongside ``au_``/``bark_``/``radio_``.
# The prefix set stays closed on purpose: an unprefixed sweep of the literal
# blob resolves only generic English words such as ``Stop`` whose hash happens
# to collide with an Event id, which is a coincidence rather than a name.
MANAGED_AUDIO_LITERAL_RE = re.compile(
    r"^(?:au|bark|radio|vo)_[A-Za-z0-9_./+:-]+$",
    re.IGNORECASE,
)


def collect_metadata_audio_literals(metadata_path: Path | None) -> list[str]:
    """Recover complete audio-like managed string literals from IL2CPP v29+.

    ``stringLiteral`` rows are exact ``<byteLength, dataIndex>`` pairs and the
    referenced UTF-8 bytes live in ``stringLiteralData``.  These strings prove
    that managed code shipped the identifier, not that the corresponding
    event was posted at runtime.  A later exact FNV-1/type-4 HIRC join upgrades
    the row to a named Wwise Event object.
    """

    if metadata_path is None or not metadata_path.is_file():
        return []
    data = metadata_path.read_bytes()
    if len(data) < 24:
        return []
    magic = int.from_bytes(data[0:4], "little")
    version = int.from_bytes(data[4:8], "little")
    if magic != METADATA_MAGIC or version < 29:
        return []
    literal_offset = int.from_bytes(data[8:12], "little")
    literal_size = int.from_bytes(data[12:16], "little", signed=True)
    literal_data_offset = int.from_bytes(data[16:20], "little")
    literal_data_size = int.from_bytes(data[20:24], "little", signed=True)
    if (
        literal_size < 0
        or literal_data_size < 0
        or literal_size % 8
        or literal_offset + literal_size > len(data)
        or literal_data_offset + literal_data_size > len(data)
    ):
        return []

    names: dict[str, str] = {}
    literal_data_end = literal_data_offset + literal_data_size
    for pos in range(literal_offset, literal_offset + literal_size, 8):
        byte_length = int.from_bytes(data[pos : pos + 4], "little")
        data_index = int.from_bytes(data[pos + 4 : pos + 8], "little")
        start = literal_data_offset + data_index
        end = start + byte_length
        if start < literal_data_offset or end > literal_data_end:
            continue
        try:
            value = data[start:end].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if MANAGED_AUDIO_LITERAL_RE.fullmatch(value):
            names.setdefault(value.lower(), value)
    return [names[key] for key in sorted(names)]


def audio_hash_generator_compute(value: str) -> int:
    """Mirror ``Beyond.Audio.AudioHashGenerator.Compute(string)`` exactly.

    The shipped implementation applies FNV-1 to managed UTF-16 code units,
    folding only ASCII ``A``-``Z`` before each XOR.  Whitespace is significant.
    """

    hash_value = 0x811C9DC5
    encoded = value.encode("utf-16-le", errors="surrogatepass")
    for offset in range(0, len(encoded), 2):
        code_unit = encoded[offset] | (encoded[offset + 1] << 8)
        if 0x41 <= code_unit <= 0x5A:
            code_unit += 0x20
        hash_value = (hash_value * 0x01000193) & 0xFFFFFFFF
        hash_value ^= code_unit
    return hash_value


def hashed_event_key(event_hash: int) -> str:
    return f"hashed-event:0x{event_hash & 0xFFFFFFFF:08x}"


def event_hash_context_key(event_hash: int) -> str:
    return f"#0x{event_hash & 0xFFFFFFFF:08x}"


def is_rtpc_parameter_name(value: Any) -> bool:
    return str(value or "").strip().lower().startswith("au_rtpc_")
