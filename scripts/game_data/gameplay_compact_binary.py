"""Readers for compact root-level GameplayConfig MemoryPack payloads."""

from __future__ import annotations

import re
import struct
from typing import Any


class GameplayCompactDecodeError(ValueError):
    pass


_KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _need(data: bytes, offset: int, size: int, field: str) -> None:
    if offset + size > len(data):
        raise GameplayCompactDecodeError(f"{field}: truncated")


def _u32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    _need(data, offset, 4, field)
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _string(data: bytes, offset: int, field: str) -> tuple[str | None, int]:
    length, offset = _u32(data, offset, f"{field}.length")
    if length == 0xFFFFFFFF:
        return None, offset
    if length > 16_384:
        raise GameplayCompactDecodeError(f"{field}: invalid length {length}")
    _need(data, offset, length, field)
    try:
        return data[offset:offset + length].decode("utf-8"), offset + length
    except UnicodeDecodeError as exc:
        raise GameplayCompactDecodeError(f"{field}: invalid UTF-8") from exc


def _count(data: bytes, offset: int, field: str, limit: int = 100_000) -> tuple[int, int]:
    count, offset = _u32(data, offset, field)
    if count > limit:
        raise GameplayCompactDecodeError(f"{field}: invalid count {count}")
    return count, offset


def _tracking_bounds(data: bytes, offset: int, field: str) -> int:
    _need(data, offset, 37, field)
    if data[offset] != 3:
        raise GameplayCompactDecodeError(f"{field}: member count is not 3")
    return offset + 37


def _tracking_route(data: bytes, offset: int, field: str) -> int:
    if data[offset] == 0xFF:
        return offset + 1
    if data[offset] != 8:
        raise GameplayCompactDecodeError(f"{field}: member count is not 8/null")
    offset += 1
    offset = _tracking_bounds(data, offset, f"{field}.boundingBox")
    if data[offset] not in (0, 1):
        raise GameplayCompactDecodeError(f"{field}.ignoreYAxis: invalid bool")
    offset += 1
    count, offset = _count(data, offset, f"{field}.listOfBoundingBoxes")
    for index in range(count):
        offset = _tracking_bounds(data, offset, f"{field}.listOfBoundingBoxes[{index}]")
    _need(data, offset, 2, field)
    if data[offset] not in (0, 1) or data[offset + 1] not in (0, 1):
        raise GameplayCompactDecodeError(f"{field}: invalid bounding booleans")
    offset += 2
    count, offset = _count(data, offset, f"{field}.points")
    for index in range(count):
        _need(data, offset, 17, f"{field}.points[{index}]")
        if data[offset] != 2:
            raise GameplayCompactDecodeError(f"{field}.points[{index}]: member count is not 2")
        offset += 17
    count, offset = _count(data, offset, f"{field}.segmentPlaneList")
    for index in range(count):
        _need(data, offset, 33, f"{field}.segmentPlaneList[{index}]")
        if data[offset] != 4:
            raise GameplayCompactDecodeError(f"{field}.segmentPlaneList[{index}]: member count is not 4")
        offset += 33
    _need(data, offset, 4, f"{field}.trackingPointIdxOutOfBoundingBox")
    return offset + 4


def decode_mission_area_table(data: bytes) -> dict[str, Any]:
    if not data or data[0] != 1:
        raise GameplayCompactDecodeError("MissionAreaTable root member count is not 1")
    level_count, offset = _count(data, 1, "m_areas")
    area_count = route_count = 0
    for level_index in range(level_count):
        _need(data, offset, 4, f"m_areas[{level_index}].key")
        level_id = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        count, offset = _count(data, offset, f"m_areas[{level_id}]")
        for area_index in range(count):
            field = f"m_areas[{level_id}][{area_index}]"
            key, offset = _string(data, offset, f"{field}.key")
            if data[offset] != 8:
                raise GameplayCompactDecodeError(f"{field}: member count is not 8")
            offset += 1
            if data[offset] not in (0, 1):
                raise GameplayCompactDecodeError(f"{field}.activeOnTravelLine: invalid bool")
            offset += 1
            mission_id, offset = _string(data, offset, f"{field}.missionAreaId")
            if not key or mission_id != key:
                raise GameplayCompactDecodeError(f"{field}: key/id mismatch")
            if data[offset] not in (0, 1):
                raise GameplayCompactDecodeError(f"{field}.needTrackingRoute: invalid bool")
            offset += 1
            # TriggerShapeData is a raw 44-byte unmanaged value in declaration order.
            _need(data, offset, 44, f"{field}.shape")
            offset += 44
            if data[offset] not in (0, 1):
                raise GameplayCompactDecodeError(f"{field}.snapToGround: invalid bool")
            offset += 1
            _need(data, offset, 20, f"{field}.subDataParentId/trackingOffset")
            offset += 20
            if data[offset] != 0xFF:
                route_count += 1
            offset = _tracking_route(data, offset, f"{field}.trackingRouteInfo")
            area_count += 1
    if offset != len(data):
        raise GameplayCompactDecodeError(f"MissionAreaTable trailing bytes: {len(data) - offset}")
    return {
        "status": "exact",
        "schemaStatus": "named_exact",
        "bytesConsumed": offset,
        "levelCount": level_count,
        "entryCount": area_count,
        "trackingRouteCount": route_count,
    }


def frame_subgame_table(data: bytes) -> dict[str, Any]:
    if not data or data[0] != 1:
        raise GameplayCompactDecodeError("SubGame table root member count is not 1")
    count, offset = _count(data, 1, "dataTable")

    def boolean(cursor: int, field: str) -> int:
        _need(data, cursor, 1, field)
        if data[cursor] not in (0, 1):
            raise GameplayCompactDecodeError(f"{field}: invalid bool")
        return cursor + 1

    def nullable_list(cursor: int, field: str, item) -> tuple[int, int]:
        raw_count, cursor = _u32(data, cursor, f"{field}.count")
        if raw_count == 0xFFFFFFFF:
            return 0, cursor
        if raw_count > 4096:
            raise GameplayCompactDecodeError(f"{field}: invalid count {raw_count}")
        for item_index in range(raw_count):
            cursor = item(cursor, f"{field}[{item_index}]")
        return raw_count, cursor

    def string_item(cursor: int, field: str) -> int:
        _, cursor = _string(data, cursor, field)
        return cursor

    def u64_item(cursor: int, field: str) -> int:
        _need(data, cursor, 8, field)
        return cursor + 8

    def task_item(cursor: int, field: str) -> int:
        if data[cursor] != 1:
            raise GameplayCompactDecodeError(f"{field}: member count is not 1")
        _, cursor = _string(data, cursor + 1, f"{field}.taskId")
        return cursor

    def lang_key(cursor: int, field: str) -> int:
        marker = data[cursor]
        if marker == 0xFF:
            return cursor + 1
        if marker != 1:
            raise GameplayCompactDecodeError(f"{field}: member count is not 1/null")
        _, cursor = _string(data, cursor + 1, f"{field}.key")
        return cursor

    rows: list[dict[str, Any]] = []
    task_total = 0
    for row_index in range(count):
        start = offset
        key, offset = _string(data, offset, f"dataTable[{row_index}].key")
        if not key or not _KEY_RE.fullmatch(key):
            raise GameplayCompactDecodeError(f"dataTable[{row_index}]: invalid key")
        _need(data, offset, 2, f"dataTable[{row_index}].union")
        if (data[offset], data[offset + 1]) != (7, 35):
            raise GameplayCompactDecodeError(f"dataTable[{row_index}]: expected union 7/member 35")
        offset += 2
        _need(data, offset, 8, "bindScriptId"); offset += 8
        offset = boolean(offset, "canQuit")
        _need(data, offset, 8, "countDownType/countingType"); offset += 8
        offset = boolean(offset, "disableTracking")
        _, offset = _string(data, offset, "dungeonMissionId")
        _, offset = nullable_list(offset, "extraTasks", task_item)
        offset = lang_key(offset, "failInfo")
        tasks, offset = nullable_list(offset, "failTasks", task_item); task_total += tasks
        _need(data, offset, 4, "gameMechanicsType"); offset += 4
        offset = boolean(boolean(boolean(offset, "hasTimeLimit"), "hasTimer"), "hideStageProgress")
        row_id, offset = _string(data, offset, "id")
        if row_id != key:
            raise GameplayCompactDecodeError(f"dataTable[{row_index}]: key/id mismatch")
        offset = boolean(offset, "ignoreFinishToast")
        _, offset = nullable_list(offset, "logicIdWhitelist", u64_item)
        tasks, offset = nullable_list(offset, "mainTasks", task_item); task_total += tasks
        offset = boolean(boolean(offset, "manualStartBanner"), "manualSyncTrackingStage")
        _, offset = _string(data, offset, "modeId")
        _need(data, offset, 4, "modeType"); offset += 4
        offset = boolean(offset, "noFailOnTeamAllDie")
        _, offset = _string(data, offset, "preparePhaseUIType")
        _, offset = nullable_list(offset, "proxyWhitelist", string_item)
        offset = lang_key(offset, "resetBtnName")
        offset = boolean(offset, "showDesc")
        _need(data, offset, 8, "subDataParentId"); offset += 8
        offset = lang_key(offset, "successInfo")
        _, offset = _string(data, offset, "taskGoalIconName")
        _need(data, offset, 4, "taskGoalStyle"); offset += 4
        _, offset = _string(data, offset, "teamConfigId")
        _, offset = nullable_list(offset, "teamConfigIds", string_item)
        offset = boolean(boolean(offset, "ignoreFailToastBeforeStart"), "showTimeInfoOnFinishToast")
        spawners, offset = nullable_list(offset, "spawnerIds", u64_item)
        rows.append({
            "startOffset": start,
            "endOffset": offset,
            "key": key,
            "unionTag": 7,
            "memberCount": 35,
            "spawnerIdCount": spawners,
        })
    if offset != len(data):
        raise GameplayCompactDecodeError(f"SubGame table trailing bytes: {len(data) - offset}")
    return {
        "status": "exact",
        "schemaStatus": "named_exact",
        "bytesConsumed": offset,
        "entryCount": count,
        "taskCount": task_total,
        "rows": rows,
    }


def frame_world_entity_registry(data: bytes) -> dict[str, Any]:
    """Decode the first three named dictionaries and bound the fourth to EOF."""
    if not data or data[0] != 4:
        raise GameplayCompactDecodeError("WorldEntityRegistry root member count is not 4")
    offset = 1
    lut_count, offset = _count(data, offset, "m_npcIdToLogicIdLut")
    for index in range(lut_count):
        _, offset = _string(data, offset, f"m_npcIdToLogicIdLut[{index}].key")
        _need(data, offset, 8, "m_npcIdToLogicIdLut.value")
        offset += 8
    npc_count, offset = _count(data, offset, "npcProxyBriefInfos")
    for index in range(npc_count):
        _need(data, offset, 9, f"npcProxyBriefInfos[{index}]")
        offset += 8
        if data[offset] != 4:
            raise GameplayCompactDecodeError(f"npcProxyBriefInfos[{index}]: member count is not 4")
        offset += 1
        _, offset = _string(data, offset, f"npcProxyBriefInfos[{index}].proxyId")
        _need(data, offset, 20, f"npcProxyBriefInfos[{index}].position/segmentIdGlobal")
        offset += 20
    world_count, offset = _count(data, offset, "worldEntityBriefInfos")
    for index in range(world_count):
        _need(data, offset, 9, f"worldEntityBriefInfos[{index}]")
        offset += 8
        if data[offset] != 4:
            raise GameplayCompactDecodeError(f"worldEntityBriefInfos[{index}]: member count is not 4")
        offset += 1
        _need(data, offset, 4, f"worldEntityBriefInfos[{index}].detailId")
        if struct.unpack_from("<I", data, offset)[0] == 0xFFFFFFFF:
            offset += 4
        else:
            _, offset = _string(data, offset, f"worldEntityBriefInfos[{index}].detailId")
        _need(data, offset, 28, f"worldEntityBriefInfos[{index}].type/transform")
        offset += 28
    detailed_count, offset = _count(data, offset, "worldEntityConfigInfos")
    property_count = atom_count = 0
    for detail_index in range(detailed_count):
        _need(data, offset, 9, f"worldEntityConfigInfos[{detail_index}]")
        offset += 8
        if data[offset] != 1:
            raise GameplayCompactDecodeError(
                f"worldEntityConfigInfos[{detail_index}]: member count is not 1"
            )
        offset += 1
        count, offset = _count(data, offset, f"worldEntityConfigInfos[{detail_index}].propertyList")
        property_count += count
        for property_index in range(count):
            field = f"worldEntityConfigInfos[{detail_index}].propertyList[{property_index}]"
            if data[offset] != 2:
                raise GameplayCompactDecodeError(f"{field}: member count is not 2")
            _, offset = _string(data, offset + 1, f"{field}.key")
            if data[offset] != 2:
                raise GameplayCompactDecodeError(f"{field}.value: member count is not 2")
            offset += 1
            _need(data, offset, 4, f"{field}.value.type")
            offset += 4
            atoms, offset = _count(data, offset, f"{field}.value.valueArray")
            atom_count += atoms
            for atom_index in range(atoms):
                atom = f"{field}.value.valueArray[{atom_index}]"
                if data[offset] != 2:
                    raise GameplayCompactDecodeError(f"{atom}: member count is not 2")
                offset += 1
                _need(data, offset, 8, f"{atom}.valueBit64")
                offset += 8
                _, offset = _string(data, offset, f"{atom}.valueString")
    if offset != len(data):
        raise GameplayCompactDecodeError(f"WorldEntityRegistry trailing bytes: {len(data) - offset}")
    return {
        "status": "exact",
        "schemaStatus": "named_exact",
        "bytesConsumed": offset,
        "npcIdLutCount": lut_count,
        "npcProxyCount": npc_count,
        "worldEntityBriefCount": world_count,
        "worldEntityConfigCount": detailed_count,
        "propertyCount": property_count,
        "atomCount": atom_count,
    }
