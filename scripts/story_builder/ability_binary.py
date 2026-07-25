"""Exact current-build AbilityActionData evidence used by Story recovery.

Only fully decoded, literal ``SendBattleSignalToLevel`` actions are joined to
LevelScript ``OnBattleSignal`` receivers.  The join proves local runtime
causality; it deliberately carries no mission or quest ownership.
"""

from __future__ import annotations

import math
import struct
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from .context import DATA_JSON_DIR, ROOT, read_bytes_cached, repo_rel
from .levelscript_binary import LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID


BATTLE_SIGNAL_ACTION_TAG = 0x0134
BATTLE_SIGNAL_ACTION_MEMBER_COUNT = 6
BATTLE_SIGNAL_ACTION_PREFIX = b"\xfa\x34\x01\x06"
BATTLE_SIGNAL_PRODUCER_MAPPING_ID = (
    "gameassembly-2026-07-22-ability-actiondata-0x0134"
)
BATTLE_SIGNAL_PAYLOAD_MAPPING_ID = (
    "gameassembly-2026-07-17-memorypack-native-event-fields"
)


def _read_bool(data: bytes, offset: int, field: str) -> tuple[bool, int]:
    if offset >= len(data) or data[offset] not in (0, 1):
        raise ValueError(f"{field}: invalid or truncated bool")
    return bool(data[offset]), offset + 1


def _read_i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field}: truncated i32")
    value = struct.unpack_from("<i", data, offset)[0]
    if abs(value) > 1_000_000:
        raise ValueError(f"{field}: implausible value {value}")
    return value, offset + 4


def _read_string(
    data: bytes,
    offset: int,
    field: str,
    *,
    max_length: int,
) -> tuple[str | None, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field}: truncated string length")
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length == 0xFFFFFFFF:
        return None, offset
    if length > max_length or offset + length > len(data):
        raise ValueError(f"{field}: invalid string length {length}")
    try:
        value = data[offset:offset + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{field}: invalid UTF-8") from exc
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{field}: control character")
    return value, offset + length


def _read_blackboard_float(
    data: bytes,
    offset: int,
    field: str,
) -> tuple[dict, int]:
    start = offset
    if offset >= len(data) or data[offset] != 3:
        raise ValueError(f"{field}: expected three members")
    offset += 1
    key, offset = _read_string(
        data,
        offset,
        f"{field}.blackboardKey",
        max_length=256,
    )
    use_key, offset = _read_bool(data, offset, f"{field}.useBlackboardKey")
    if offset + 4 > len(data):
        raise ValueError(f"{field}.value: truncated f32")
    raw_value = struct.unpack_from("<I", data, offset)[0]
    value = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    if not math.isfinite(value):
        raise ValueError(f"{field}.value: non-finite")
    return {
        "memberCount": 3,
        "offset": f"0x{start:x}",
        "blackboardKey": key or "",
        "useBlackboardKey": use_key,
        "serializedValueType": "System.Single",
        "rawValueU32": f"0x{raw_value:08x}",
        "value": round(value, 6),
    }, offset


def _read_blackboard_string(
    data: bytes,
    offset: int,
    field: str,
) -> tuple[dict, int]:
    start = offset
    if offset >= len(data) or data[offset] != 3:
        raise ValueError(f"{field}: expected three members")
    offset += 1
    key, offset = _read_string(
        data,
        offset,
        f"{field}.blackboardKey",
        max_length=256,
    )
    use_key, offset = _read_bool(data, offset, f"{field}.useBlackboardKey")
    value, offset = _read_string(
        data,
        offset,
        f"{field}.value",
        max_length=512,
    )
    return {
        "memberCount": 3,
        "offset": f"0x{start:x}",
        "blackboardKey": key or "",
        "useBlackboardKey": use_key,
        "value": value or "",
    }, offset


def decode_battle_signal_action(data: bytes, action_offset: int) -> dict:
    """Decode one exact 0x0134/six-member AbilityActionData union item."""
    if data[action_offset:action_offset + 4] != BATTLE_SIGNAL_ACTION_PREFIX:
        raise ValueError("sendBattleSignal: tag/member-count mismatch")
    offset = action_offset + 4
    is_enable, offset = _read_bool(data, offset, "prefix.isEnable")
    priority_level, offset = _read_i32(data, offset, "prefix.priorityLevel")
    priority_offset, offset = _read_i32(data, offset, "prefix.priorityOffset")
    server_action_index, offset = _read_i32(
        data,
        offset,
        "prefix.serverActionIndex",
    )
    double_value, offset = _read_blackboard_float(
        data,
        offset,
        "doubleValue",
    )
    signal_id, offset = _read_blackboard_string(data, offset, "signalId")
    return {
        "actionType": "Core_SendBattleSignalToLevel_Data",
        "actionUnionTag": "0x0134",
        "serializedMemberCount": BATTLE_SIGNAL_ACTION_MEMBER_COUNT,
        "actionOffset": f"0x{action_offset:x}",
        "actionByteLength": offset - action_offset,
        "producerMappingId": BATTLE_SIGNAL_PRODUCER_MAPPING_ID,
        "prefix": {
            "isEnable": is_enable,
            "priorityLevel": priority_level,
            "priorityOffset": priority_offset,
            "serverActionIndex": server_action_index,
        },
        "doubleValue": double_value,
        "signalId": signal_id,
    }


def _source_path(path: Path) -> str:
    try:
        return repo_rel(path)
    except ValueError:
        return path.as_posix()


@lru_cache(maxsize=4)
def build_battle_signal_producer_index(
    data_json_dir: Path = DATA_JSON_DIR,
) -> dict[str, list[dict]]:
    """Index fully decoded literal BattleSignal producers by signal id."""
    by_signal: dict[str, list[dict]] = defaultdict(list)
    for domain in ("SkillData", "BuffData"):
        source_dir = data_json_dir / domain
        if not source_dir.is_dir():
            continue
        for path in sorted(source_dir.glob("*.json"), key=lambda item: item.name):
            try:
                data = read_bytes_cached(path)
            except OSError:
                continue
            offset = 0
            while True:
                action_offset = data.find(BATTLE_SIGNAL_ACTION_PREFIX, offset)
                if action_offset < 0:
                    break
                offset = action_offset + 1
                try:
                    decoded = decode_battle_signal_action(data, action_offset)
                except (struct.error, UnicodeDecodeError, ValueError):
                    continue
                signal = decoded["signalId"]
                # A dynamic blackboard value cannot be equated to a literal
                # receiver selector from serialized data, so it remains out
                # of the exact producer-to-listener join.
                if (
                    decoded["prefix"]["isEnable"] is not True
                    or signal["useBlackboardKey"]
                    or not signal["value"]
                ):
                    continue
                by_signal[signal["value"]].append({
                    **decoded,
                    "relation": "ability_battle_signal_local_causality",
                    "producerDomain": domain,
                    "producerAssetId": path.stem,
                    "producerSourceFile": _source_path(path),
                    "executionSide": "client",
                    "transport": "local-level-runtime-event",
                    "serverExchange": False,
                    "clientRequest": False,
                    "expectedServerReturn": False,
                    "missionOwnerStatus": "unresolved",
                    "storyBinding": False,
                })
    return {
        signal: sorted(
            rows,
            key=lambda row: (
                row["producerDomain"],
                row["producerAssetId"],
                row["actionOffset"],
            ),
        )
        for signal, rows in sorted(by_signal.items())
    }


def match_battle_signal_story_producers(
    story_key: str,
    occurrences: list[dict],
    producer_index: dict[str, list[dict]],
) -> list[dict]:
    """Join exact literal producers to exact serialized Story receivers.

    The returned route stops at the Story playback.  It never supplies a
    mission/quest owner because ``OnBattleSignal`` has no serialized selector
    for the producer sender, entity, template, spawner, mission, or quest.
    """
    routes: list[dict] = []
    seen: set[tuple] = set()
    for occurrence in occurrences:
        for owner in occurrence.get("nativeEventOwners") or []:
            detail = owner.get("eventDetail") or {}
            if not (
                owner.get("status") == "exact_serialized_control_path"
                and owner.get("headerName") == "LevelEvent_OnBattleSignal"
                and owner.get("headerUnionTag") == "0x004c"
                and owner.get("headerSerializedMemberCount") == 16
                and owner.get("nativeHeaderMappingId")
                == LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID
                and detail.get("type") == "LevelEvent_OnBattleSignal"
                and detail.get("payloadSchemaStatus")
                == "exact_current_build_memorypack_fields"
                and detail.get("payloadSchemaMappingId")
                == BATTLE_SIGNAL_PAYLOAD_MAPPING_ID
            ):
                continue
            signal_id = str(detail.get("signalId") or "")
            if not signal_id:
                continue
            for producer in producer_index.get(signal_id) or []:
                signature = (
                    str(occurrence.get("sourceFile") or ""),
                    owner.get("headerLocalId"),
                    producer.get("producerSourceFile"),
                    producer.get("actionOffset"),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                routes.append({
                    **producer,
                    "storyKey": story_key,
                    "listenerLevelId": str(occurrence.get("levelId") or ""),
                    "listenerScriptId": str(occurrence.get("scriptId") or ""),
                    "listenerHeaderLocalId": owner.get("headerLocalId"),
                    "listenerSourceFile": str(
                        occurrence.get("sourceFile") or ""
                    ),
                    "listenerPlaybackAction": str(
                        occurrence.get("actionName") or ""
                    ),
                    "receiverSignalId": signal_id,
                    "receiverMappingId": str(
                        owner.get("nativeHeaderMappingId") or ""
                    ),
                    "receiverPayloadMappingId": str(
                        detail.get("payloadSchemaMappingId") or ""
                    ),
                    "source": (
                        "exact current-build 0x0134/six-member "
                        "SendBattleSignalToLevel action emits the literal signal "
                        "selected by this exact 0x004c/sixteen-member "
                        "OnBattleSignal receiver; local causality only, with no "
                        "mission/quest owner or server exchange"
                    ),
                })
    return sorted(
        routes,
        key=lambda row: (
            row["listenerLevelId"],
            row["listenerScriptId"],
            row.get("listenerHeaderLocalId") or -1,
            row["producerDomain"],
            row["producerAssetId"],
            row["actionOffset"],
        ),
    )
