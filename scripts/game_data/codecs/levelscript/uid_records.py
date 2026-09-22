"""The ASCII/uid record scan that indexes a LevelScriptData blob.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import re
import struct

from scripts.game_data.codecs.levelscript.framing_common import _is_printable_ascii
from scripts.game_data.codecs.levelscript.framing_common import _record_start
from scripts.game_data.codecs.levelscript.primitives import i32 as _i32
from scripts.game_data.codecs.levelscript.primitives import u32 as _u32
from typing import Any

LEVELSCRIPT_HEX_UID_RE = re.compile(rb"[0-9a-f]{8}")


def _extract_levelscript_tagged_ascii_strings(
    data: bytes,
    tag: int = 0x04,
    *,
    max_len: int = 120,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    end = len(data) - 5
    i = 0
    while i < end:
        if data[i] != tag:
            i += 1
            continue
        size = struct.unpack_from("<I", data, i + 1)[0]
        if size <= 0 or size > max_len or i + 5 + size > len(data):
            i += 1
            continue
        raw = data[i + 5 : i + 5 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({"offset": i, "text": text})
        i += 5 + size
    return hits


def _extract_levelscript_plain_ascii_strings(
    data: bytes,
    *,
    min_len: int = 3,
    max_len: int = 120,
    tagged_offsets: set[int] | None = None,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    tagged_offsets = tagged_offsets or set()
    end = len(data) - 4
    i = 0
    while i < end:
        size = struct.unpack_from("<I", data, i)[0]
        if size < min_len or size > max_len or i + 4 + size > len(data):
            i += 1
            continue
        if i > 0 and data[i - 1] == 0x04 and (i - 1) in tagged_offsets:
            i += 4 + size
            continue
        raw = data[i + 4 : i + 4 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({"offset": i, "payloadOffset": i + 4, "text": text})
        i += 4 + size
    return hits


def _decode_levelscript_uid_record(data: bytes, uid_off: int, uid: str) -> dict[str, Any] | None:
    if uid_off >= 14:
        start = uid_off - 14
        if start + 32 <= len(data):
            if (
                data[start] == 0xFA
                and data[start + 4] in (0, 1)
                and data[start + 9] == 0
                and _u32(data, start + 10) == 8
            ):
                local_id = _u32(data, start + 5)
                if isinstance(local_id, int) and local_id <= 0x1000:
                    return {
                        "start": start,
                        "layout": "fa",
                        "code": struct.unpack_from("<H", data, start + 1)[0],
                        "kind": data[start + 3],
                        "unionTag": struct.unpack_from("<H", data, start + 1)[0],
                        "serializedMemberCount": data[start + 3],
                        "dontLog": bool(data[start + 4]),
                        "unionTagEncoding": "memorypack-fa-u16",
                        "localId": local_id,
                        "uid": uid,
                        "nextId": _i32(data, start + 28),
                        "payloadStart": start + 32,
                        "strings": [],
                        "plainStrings": [],
                    }

    if uid_off >= 12:
        start = uid_off - 12
        if start + 30 <= len(data):
            code = struct.unpack_from("<H", data, start)[0]
            kind = data[start + 2]
            local_id = _u32(data, start + 3)
            if (
                isinstance(local_id, int)
                and data[start] < 0xFA
                and data[start + 1] <= 0x40
                and kind in (0, 1)
                and local_id <= 0x1000
                and data[start + 7] == 0
                and _u32(data, start + 8) == 8
            ):
                return {
                    "start": start,
                    "layout": "plain",
                    "code": code,
                    "kind": kind,
                    "unionTag": data[start],
                    "serializedMemberCount": data[start + 1],
                    "dontLog": bool(data[start + 2]),
                    "unionTagEncoding": "memorypack-u8",
                    "localId": local_id,
                    "uid": uid,
                    "nextId": _i32(data, start + 26),
                    "payloadStart": start + 30,
                    "strings": [],
                    "plainStrings": [],
                }

    return None


def extract_levelscript_uid_records(
    data: bytes,
    tagged_strings: list[dict[str, Any]] | None = None,
    plain_strings: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_starts: set[int] = set()
    tagged_strings = sorted(tagged_strings or [], key=lambda hit: int(hit.get("offset") or 0))
    plain_strings = sorted(plain_strings or [], key=lambda hit: int(hit.get("offset") or 0))

    for match in LEVELSCRIPT_HEX_UID_RE.finditer(data):
        uid_off = match.start()
        uid = match.group().decode("ascii")
        record = _decode_levelscript_uid_record(data, uid_off, uid)
        if record is None or int(record["start"]) in seen_starts:
            continue
        seen_starts.add(int(record["start"]))
        records.append(record)

    records.sort(key=_record_start)
    if not records:
        return records

    tagged_index = 0
    plain_index = 0
    for index, record in enumerate(records):
        next_start = _record_start(records[index + 1]) if index + 1 < len(records) else len(data)
        payload_start = int(record.get("payloadStart") or 0)
        while tagged_index < len(tagged_strings) and int(tagged_strings[tagged_index].get("offset") or 0) < payload_start:
            tagged_index += 1
        scan_index = tagged_index
        while scan_index < len(tagged_strings) and int(tagged_strings[scan_index].get("offset") or 0) < next_start:
            record["strings"].append(tagged_strings[scan_index])
            scan_index += 1
        while plain_index < len(plain_strings) and int(plain_strings[plain_index].get("offset") or 0) < payload_start:
            plain_index += 1
        scan_index = plain_index
        while scan_index < len(plain_strings) and int(plain_strings[scan_index].get("offset") or 0) < next_start:
            record["plainStrings"].append(plain_strings[scan_index])
            scan_index += 1

    return records
