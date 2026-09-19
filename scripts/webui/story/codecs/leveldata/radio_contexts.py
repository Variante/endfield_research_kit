from __future__ import annotations

from .memorypack import (
    read_bool,
    read_count,
    read_i32,
    read_string,
    read_u32,
    read_u64,
    skip_bytes,
    skip_string,
)


def parse_airwall_groups(data: bytes) -> list[dict]:
    """Decode exact ``LevelData.airWalls`` MemoryPack rows."""
    if not data or data[0] != 43:
        return []
    count_decoded = read_count(data, 1, max_count=4096)
    if count_decoded is None or count_decoded[0] < 0:
        return []
    group_count, cursor = count_decoded

    def object_header(offset: int, expected: int) -> int | None:
        if offset >= len(data) or data[offset] != expected:
            return None
        return offset + 1

    def skip_three_dim_range(offset: int) -> int | None:
        if offset < len(data) and data[offset] == 0xFF:
            return offset + 1
        offset = object_header(offset, 2)
        return None if offset is None else skip_bytes(data, offset, 24)

    def parse_mission_check(offset: int) -> tuple[dict, int] | None:
        start = offset
        offset = object_header(offset, 4)
        if offset is None:
            return None
        detail_decoded = read_i32(data, offset)
        if detail_decoded is None:
            return None
        detail_state, offset = detail_decoded
        id_decoded = read_string(data, offset)
        if id_decoded is None:
            return None
        check_id, offset = id_decoded
        quest_decoded = read_bool(data, offset)
        if quest_decoded is None:
            return None
        is_quest, offset = quest_decoded
        same_decoded = read_bool(data, offset)
        if same_decoded is None:
            return None
        is_same, offset = same_decoded
        return {
            "id": check_id,
            "isQuest": is_quest,
            "detailState": detail_state,
            "isSame": is_same,
            "recordOffset": start,
            "recordEndOffset": offset,
        }, offset

    def parse_mission_check_list(offset: int) -> tuple[list[dict], int] | None:
        decoded = read_count(data, offset, max_count=4096)
        if decoded is None:
            return None
        count, offset = decoded
        if count == -1:
            return [], offset
        rows: list[dict] = []
        for _index in range(count):
            parsed = parse_mission_check(offset)
            if parsed is None:
                return None
            row, offset = parsed
            rows.append(row)
        return rows, offset

    def parse_mission_total(offset: int) -> tuple[dict | None, int] | None:
        if offset < len(data) and data[offset] == 0xFF:
            return None, offset + 1
        offset = object_header(offset, 4)
        if offset is None:
            return None
        down_decoded = parse_mission_check_list(offset)
        if down_decoded is None:
            return None
        down_reason, offset = down_decoded
        down_any_decoded = read_bool(data, offset)
        if down_any_decoded is None:
            return None
        is_down_any, offset = down_any_decoded
        rise_any_decoded = read_bool(data, offset)
        if rise_any_decoded is None:
            return None
        is_rise_any, offset = rise_any_decoded
        rise_decoded = parse_mission_check_list(offset)
        if rise_decoded is None:
            return None
        rise_reason, offset = rise_decoded
        return {
            "downReason": down_reason,
            "isDownAny": is_down_any,
            "isRiseAny": is_rise_any,
            "riseReason": rise_reason,
        }, offset

    def parse_airwall_check(offset: int) -> tuple[dict | None, int] | None:
        if offset < len(data) and data[offset] == 0xFF:
            return None, offset + 1
        offset = object_header(offset, 2)
        if offset is None:
            return None
        type_decoded = read_i32(data, offset)
        if type_decoded is None:
            return None
        check_type, offset = type_decoded
        total_decoded = parse_mission_total(offset)
        if total_decoded is None:
            return None
        mission_data, offset = total_decoded
        return {"checkType": check_type, "missionData": mission_data}, offset

    def skip_poly_line_wall(offset: int) -> int | None:
        offset = object_header(offset, 10)
        if offset is None:
            return None
        offset = skip_three_dim_range(offset)
        if offset is None:
            return None
        for _field in ("disableDefaultEffect", "enableNavObstacle"):
            decoded = read_bool(data, offset)
            if decoded is None:
                return None
            _value, offset = decoded
        offset = skip_bytes(data, offset, 8)
        if offset is None:
            return None
        offset = skip_string(data, offset)
        if offset is None:
            return None
        positions_decoded = read_count(data, offset, max_count=65536)
        if positions_decoded is None:
            return None
        position_count, offset = positions_decoded
        if position_count >= 0:
            offset = skip_bytes(data, offset, position_count * 8)
            if offset is None:
                return None
        return skip_bytes(data, offset, 20)

    def skip_poly_line_wall_list(offset: int) -> int | None:
        decoded = read_count(data, offset, max_count=65536)
        if decoded is None:
            return None
        count, offset = decoded
        if count == -1:
            return offset
        for _index in range(count):
            offset = skip_poly_line_wall(offset)
            if offset is None:
                return None
        return offset

    rows: list[dict] = []
    for _index in range(group_count):
        record_offset = cursor
        cursor = object_header(cursor, 8)
        if cursor is None:
            return []
        cursor = skip_three_dim_range(cursor)
        if cursor is None:
            return []
        check_decoded = parse_airwall_check(cursor)
        if check_decoded is None:
            return []
        check_data, cursor = check_decoded
        default_decoded = read_bool(data, cursor)
        if default_decoded is None:
            return []
        default_on, cursor = default_decoded
        group_decoded = read_u64(data, cursor)
        if group_decoded is None:
            return []
        group_id, cursor = group_decoded
        cursor = skip_poly_line_wall_list(cursor)
        if cursor is None:
            return []
        radio_decoded = read_string(data, cursor)
        if radio_decoded is None:
            return []
        pushback_radio_id, cursor = radio_decoded
        script_decoded = read_u64(data, cursor)
        if script_decoded is None:
            return []
        script_id, cursor = script_decoded
        slot_decoded = read_u32(data, cursor)
        if slot_decoded is None:
            return []
        slot_id, cursor = slot_decoded
        rows.append({
            "recordOffset": record_offset,
            "recordEndOffset": cursor,
            "serializedMemberCount": 8,
            "defaultOn": default_on,
            "groupId": str(group_id),
            "scriptId": str(script_id),
            "slotId": slot_id,
            "checkData": check_data,
            "pushBackRadioId": pushback_radio_id,
        })
    return rows


def parse_function_area_radio_trigger(data: bytes, offset: int) -> dict | None:
    """Parse one exact LevelFunctionArea RadioTriggerZoneData union row."""
    if (
        offset < 4
        or data[offset : offset + 2] != b"\x09\x07"
        or int.from_bytes(data[offset - 4 : offset], "little", signed=True) != 1
    ):
        return None
    cursor = offset + 2
    values: list[str] = []
    for _ in range(5):
        decoded = read_string(data, cursor)
        if decoded is None:
            return None
        value, cursor = decoded
        values.append(value)
    trigger_decoded = read_u64(data, cursor)
    if trigger_decoded is None:
        return None
    trigger_id, cursor = trigger_decoded
    if trigger_id <= 0 or cursor >= len(data) or data[cursor] not in (0, 1):
        return None
    use_once = bool(data[cursor])
    cursor += 1
    (
        hide_after_mission_id,
        hide_before_mission_id,
        hide_complete_mission_id,
        prts_id,
        radio_id,
    ) = values
    if not radio_id.startswith("radio_"):
        return None
    return {
        "recordOffset": offset,
        "recordEndOffset": cursor,
        "unionTag": 9,
        "serializedMemberCount": 7,
        "specificDataListCount": 1,
        "hideAfterMissionId": hide_after_mission_id,
        "hideBeforeMissionId": hide_before_mission_id,
        "hideCompleteMissionId": hide_complete_mission_id,
        "prtsId": prts_id,
        "radioId": radio_id,
        "triggerId": str(trigger_id),
        "useRadioTriggerOnce": use_once,
    }
