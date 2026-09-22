"""Helpers and constants shared by every LevelScript payload codec.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import struct

from typing import Any

class LevelScriptTopLevelFramingError(ValueError):
    """Raised when a strict partial top-level frame cannot be proved."""


def _u64_offsets(data: bytes, value: int) -> list[int]:
    needle = struct.pack("<Q", value)
    offsets: list[int] = []
    start = 0
    while True:
        offset = data.find(needle, start)
        if offset < 0:
            break
        offsets.append(offset)
        start = offset + 1
    return offsets


def _is_plausible_levelscript_id(value: int) -> bool:
    return 1_000_000 <= value <= 999_999_999_999


def _drop_empty(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value not in (None, "", [], {})}


def _offset_hex(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def _round_float(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)


def _record_start(record: dict[str, Any]) -> int:
    try:
        return int(record.get("start") or 0)
    except (TypeError, ValueError):
        return 0


def _is_printable_ascii(blob: bytes) -> bool:
    return all(0x20 <= byte <= 0x7E for byte in blob)


def _read_compact_string(payload: bytes, offset: int) -> tuple[str | None, int | None]:
    """Read a compact ASCII string shared by task-map schemas."""
    if offset < 0 or offset + 4 > len(payload):
        return None, None
    size = struct.unpack_from("<I", payload, offset)[0]
    if size > 120 or offset + 4 + size > len(payload):
        return None, None
    raw = payload[offset + 4 : offset + 4 + size]
    if not _is_printable_ascii(raw):
        return None, None
    return raw.decode("ascii", errors="replace"), offset + 4 + size


def _record_payload_window(
    data: bytes,
    record: dict[str, Any] | None,
    next_start: int | None,
) -> tuple[int, bytes]:
    if not data or not record:
        return 0, b""
    payload_start = int(record.get("payloadStart", record.get("start", 0)) or 0)
    if payload_start < 0 or payload_start >= len(data):
        return payload_start, b""
    if next_start is None or next_start <= payload_start or next_start > len(data):
        next_start = min(len(data), payload_start + 160)
    return payload_start, data[payload_start:next_start]


COMPACT_NULL_SENTINEL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


ACTION_SERIALIZED_MAP_LIST_ORDER = ("actionList", "getterList", "headerList")


ACTION_SERIALIZED_MAP_ORDER_EVIDENCE = (
    "GameAssembly ActionSerializedMapForMemoryPack.Deserialize dispatches "
    "set___actionList__, set___getterList__, then set___headerList__; the "
    "setter bodies write ActionSerializedMap fields at +0x18, +0x20, and "
    "+0x10, and MetadataRegistration resolves those fields as "
    "List<ActionBase>, List<PureGetter>, and List<ActionHeader>. The "
    "physical second/third UID-list blocks match getter/header content "
    "signatures; two-block maps can omit an empty getterList and go straight "
    "to a header-shaped final block, leaving ScriptEventHeader-band rows in "
    "headerList instead of getterList."
)


SCRIPT_POINTER_REF_RECORDS = {
    (0x045D, 0x0A),
}


NOISY_PROPERTY_PREFIXES = (
    "$",
    "#",
    "dlg_",
    "sns_",
    "cutscene_",
    "black_",
    "remotecomm_",
    "radio_",
    "misc_dlg_",
    "levelseq_",
    "guide_",
    "au_",
    "chr_",
    "skill_",
    "LD/",
)


NOISY_PROPERTY_TEXT = {
    "event_args",
    "blackboard",
    "PLAY_SEQ",
}
