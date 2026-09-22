"""Tagged-payload field scanning shared by the record dispatcher.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import struct

from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript.framing_common import COMPACT_NULL_SENTINEL
from scripts.game_data.codecs.levelscript.framing_common import NOISY_PROPERTY_PREFIXES
from scripts.game_data.codecs.levelscript.framing_common import NOISY_PROPERTY_TEXT
from scripts.game_data.codecs.levelscript.framing_common import _drop_empty
from scripts.game_data.codecs.levelscript.framing_common import _is_printable_ascii
from scripts.game_data.codecs.levelscript.framing_common import _offset_hex
from scripts.game_data.codecs.levelscript.framing_common import _round_float
from typing import Any

def _payload_sentinel_size(data: bytes, offset: int) -> int:
    if offset + 12 <= len(data) and data[offset : offset + 12] == COMPACT_NULL_SENTINEL:
        return 12
    return 0


def _decode_tagged_payload_fields(payload: bytes, *, max_fields: int = 8) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(payload) and len(fields) < max_fields:
        if payload[cursor] != 0x04:
            cursor += 1
            continue
        if cursor + 5 > len(payload):
            break

        size = struct.unpack_from("<I", payload, cursor + 1)[0]
        if 0 < size <= 120 and cursor + 5 + size <= len(payload):
            raw = payload[cursor + 5 : cursor + 5 + size]
            if _is_printable_ascii(raw):
                text = raw.decode("ascii", errors="replace")
                end = cursor + 5 + size
                fields.append(
                    _drop_empty(
                        {
                            "offset": _offset_hex(cursor),
                            "type": "string",
                            "value": text,
                        }
                    )
                )
                cursor = end + _payload_sentinel_size(payload, end)
                continue

        raw4 = payload[cursor + 1 : cursor + 5]
        scalar_u32 = struct.unpack("<I", raw4)[0]
        scalar_i32 = struct.unpack("<i", raw4)[0]
        scalar_float = struct.unpack("<f", raw4)[0]
        field: dict[str, Any] = {
            "offset": _offset_hex(cursor),
            "type": "scalar",
        }
        if scalar_u32 <= 1_000_000:
            field["u32"] = scalar_u32
        if -1_000_000 <= scalar_i32 <= 1_000_000:
            field["i32"] = scalar_i32
        if -1_000_000.0 <= scalar_float <= 1_000_000.0:
            field["float"] = _round_float(scalar_float)
        if not any(key in field for key in ("u32", "i32", "float")):
            field["rawHex"] = raw4.hex(" ")
        fields.append(_drop_empty(field))
        end = cursor + 5
        cursor = end + _payload_sentinel_size(payload, end)
    return fields


def _record_text_values(record: dict[str, Any] | None, fields: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for field in fields:
        if field.get("type") == "string" and field.get("value") not in values:
            values.append(str(field.get("value")))
    for key in ("strings", "plainStrings"):
        for hit in (record or {}).get(key) or []:
            text = hit.get("text") if isinstance(hit, dict) else hit
            if isinstance(text, str) and text and text not in values:
                values.append(text)
    return values


def _looks_like_property_key(text: str) -> bool:
    if not text or len(text) > 80:
        return False
    if text in NOISY_PROPERTY_TEXT:
        return False
    if text.isdigit():
        return False
    if any(text.startswith(prefix) for prefix in NOISY_PROPERTY_PREFIXES):
        return False
    return any(ch.isalpha() for ch in text)


def _extract_property_output_refs(texts: list[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for text in texts:
        match = levelscript_params.PROPERTY_OUTPUT_PATH_RE.match(text)
        if not match:
            continue
        refs.append({
            "localId": int(match.group("local")),
            "field": match.group("name"),
            "ref": text,
        })
    return refs


def _extract_trigger_slot_ids(payload: bytes) -> list[int]:
    slots: list[int] = []
    for offset in range(0, max(0, len(payload) - 3)):
        value = struct.unpack_from("<I", payload, offset)[0]
        if 80000 <= value <= 89999 and value not in slots:
            slots.append(value)
    return slots
