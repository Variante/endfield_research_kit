"""Exact generated-wrapper codecs for LevelData factory records."""

from __future__ import annotations

from typing import Any

from .memorypack import read_bool, read_count, read_f32, read_i32, read_string, read_u64


def _read_vector(
    data: bytes, offset: int, width: int, reader
) -> tuple[list[int] | list[float], int] | None:
    values: list[int] | list[float] = []
    for _ in range(width):
        decoded = reader(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def _read_object_list(
    data: bytes, offset: int, decoder
) -> tuple[dict[str, Any], int] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, offset = decoded
    rows: list[dict[str, Any] | None] = []
    for index in range(max(0, count)):
        if offset >= len(data):
            return None
        row_start = offset
        if data[offset] == 0xFF:
            rows.append(None)
            offset += 1
            continue
        item = decoder(data, offset)
        if item is None:
            return None
        value, offset = item
        value["indexInCollection"] = index
        value["startOffset"] = row_start
        value["endOffset"] = offset
        rows.append(value)
    return {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else rows,
        "rows": rows,
    }, offset


def _read_member(data: bytes, offset: int, expected: int) -> int | None:
    if offset >= len(data) or data[offset] != expected:
        return None
    return offset + 1


def _decode_grid_transform(
    data: bytes, offset: int
) -> tuple[dict[str, Any], int] | None:
    start = offset
    offset = _read_member(data, offset, 3)
    if offset is None:
        return None
    face_decoded = read_i32(data, offset)
    if face_decoded is None:
        return None
    face, offset = face_decoded
    position_decoded = _read_vector(data, offset, 2, read_i32)
    if position_decoded is None:
        return None
    position, offset = position_decoded
    voxel_decoded = _read_vector(data, offset, 3, read_i32)
    if voxel_decoded is None:
        return None
    voxel_position, offset = voxel_decoded
    return {
        "memberCount": 3,
        "startOffset": start,
        "endOffset": offset,
        "face": face,
        "position": position,
        "voxelPosition": voxel_position,
    }, offset


def _decode_factory_mine(
    data: bytes, offset: int
) -> tuple[dict[str, Any], int] | None:
    start = offset
    offset = _read_member(data, offset, 7)
    if offset is None:
        return None
    density_decoded = _read_i32_list(data, offset)
    if density_decoded is None:
        return None
    density_level, offset = density_decoded
    item_decoded = read_string(data, offset, max_length=4096)
    if item_decoded is None:
        return None
    item_id, offset = item_decoded
    logic_decoded = read_u64(data, offset)
    if logic_decoded is None:
        return None
    logic_mine_data_id, offset = logic_decoded
    height_decoded = read_f32(data, offset)
    if height_decoded is None:
        return None
    mine_height, offset = height_decoded
    offset_decoded = read_f32(data, offset)
    if offset_decoded is None:
        return None
    mine_offset, offset = offset_decoded
    proto_decoded = read_string(data, offset, max_length=4096)
    if proto_decoded is None:
        return None
    proto_id, offset = proto_decoded
    transform_decoded = _decode_grid_transform(data, offset)
    if transform_decoded is None:
        return None
    transform, offset = transform_decoded
    return {
        "memberCount": 7,
        "startOffset": start,
        "endOffset": offset,
        "densityLevel": density_level,
        "itemId": item_id,
        "logicMineDataId": str(logic_mine_data_id),
        "mineHeight": mine_height,
        "offset": mine_offset,
        "protoId": proto_id,
        "trans": transform,
    }, offset


def decode_level_factory_mine_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelFactoryRegionMineInstanceData>`` exactly."""

    decoded = _read_object_list(data, offset, _decode_factory_mine)
    if decoded is None:
        return None
    value, _ = decoded
    value["itemFieldOrder"] = [
        "densityLevel", "itemId", "logicMineDataId", "mineHeight", "offset",
        "protoId", "trans",
    ]
    value["fieldOrderSource"] = (
        "current generated LevelFactoryRegionMineInstanceDataForMemoryPack wrapper"
    )
    return value


def _decode_area_bound(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 2)
    if offset is None:
        return None
    size_decoded = _read_vector(data, offset, 3, read_i32)
    if size_decoded is None:
        return None
    size, offset = size_decoded
    start_decoded = _read_vector(data, offset, 3, read_i32)
    if start_decoded is None:
        return None
    bound_start, offset = start_decoded
    return {"memberCount": 2, "size": size, "start": bound_start}, offset


def _decode_area_single_level(
    data: bytes, offset: int
) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 2)
    if offset is None:
        return None
    level_decoded = read_i32(data, offset)
    if level_decoded is None:
        return None
    level, offset = level_decoded
    bounds_decoded = _read_object_list(data, offset, _decode_area_bound)
    if bounds_decoded is None:
        return None
    level_bounds, offset = bounds_decoded
    return {
        "memberCount": 2, "level": level, "levelBounds": level_bounds
    }, offset


def _decode_area(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 6)
    if offset is None:
        return None
    fence_decoded = read_f32(data, offset)
    if fence_decoded is None:
        return None
    fence_height, offset = fence_decoded
    index_decoded = read_i32(data, offset)
    if index_decoded is None:
        return None
    index, offset = index_decoded
    main_decoded = read_bool(data, offset)
    if main_decoded is None:
        return None
    is_main, offset = main_decoded
    count_decoded = read_i32(data, offset)
    if count_decoded is None:
        return None
    level_count, offset = count_decoded
    levels_decoded = _read_object_list(data, offset, _decode_area_single_level)
    if levels_decoded is None:
        return None
    level_data, offset = levels_decoded
    max_decoded = read_i32(data, offset)
    if max_decoded is None:
        return None
    max_count, offset = max_decoded
    return {
        "memberCount": 6,
        "fenceHeight": fence_height,
        "index": index,
        "isMain": is_main,
        "levelCnt": level_count,
        "levelData": level_data,
        "maxCnt": max_count,
    }, offset


def _decode_mask_entry(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 2)
    if offset is None:
        return None
    point_decoded = _read_vector(data, offset, 2, read_i32)
    if point_decoded is None:
        return None
    point, offset = point_decoded
    value_decoded = read_i32(data, offset)
    if value_decoded is None:
        return None
    value, offset = value_decoded
    return {"memberCount": 2, "point": point, "val": value}, offset


def _decode_buildable_range(
    data: bytes, offset: int
) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 8)
    if offset is None:
        return None
    initial_decoded = read_i32(data, offset)
    if initial_decoded is None:
        return None
    initial_mask, offset = initial_decoded
    post_decoded = _read_object_list(data, offset, _decode_mask_entry)
    if post_decoded is None:
        return None
    post_masks, offset = post_decoded
    pre_decoded = _read_object_list(data, offset, _decode_mask_entry)
    if pre_decoded is None:
        return None
    pre_masks, offset = pre_decoded
    scalars: dict[str, int] = {}
    for name in ("rangeH", "rangeW", "rangeX", "rangeY", "regionLevel"):
        decoded = read_i32(data, offset)
        if decoded is None:
            return None
        scalars[name], offset = decoded
    return {
        "memberCount": 8,
        "initialMaskValue": initial_mask,
        "postMaks": post_masks,
        "preMasks": pre_masks,
        **scalars,
    }, offset


def _decode_bus(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 6)
    if offset is None:
        return None
    arc_decoded = _read_vector(data, offset, 3, read_f32)
    if arc_decoded is None:
        return None
    arc_position, offset = arc_decoded
    has_arc_decoded = read_bool(data, offset)
    if has_arc_decoded is None:
        return None
    has_arc, offset = has_arc_decoded
    inst_decoded = read_string(data, offset, max_length=4096)
    if inst_decoded is None:
        return None
    inst_key, offset = inst_decoded
    template_decoded = read_string(data, offset, max_length=4096)
    if template_decoded is None:
        return None
    template_id, offset = template_decoded
    position_decoded = _read_vector(data, offset, 3, read_f32)
    if position_decoded is None:
        return None
    world_position, offset = position_decoded
    rotation_decoded = _read_vector(data, offset, 3, read_f32)
    if rotation_decoded is None:
        return None
    world_rotation, offset = rotation_decoded
    return {
        "memberCount": 6,
        "arcPosition": arc_position,
        "hasArc": has_arc,
        "instKey": inst_key,
        "templateId": template_id,
        "worldPosition": world_position,
        "worldRotation": world_rotation,
    }, offset


def _decode_grid_path(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 3)
    if offset is None:
        return None
    face_decoded = read_i32(data, offset)
    if face_decoded is None:
        return None
    initial_face, offset = face_decoded
    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, offset = count_decoded
    segments: list[list[int]] = []
    for _ in range(max(0, count)):
        segment_decoded = _read_vector(data, offset, 2, read_i32)
        if segment_decoded is None:
            return None
        segment, offset = segment_decoded
        segments.append(segment)
    segment_list = {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else segments,
    }
    point_decoded = _read_vector(data, offset, 2, read_i32)
    if point_decoded is None:
        return None
    start_point, offset = point_decoded
    return {
        "memberCount": 3,
        "initialFace": initial_face,
        "segments": segment_list,
        "startPoint": start_point,
    }, offset


def _decode_initial_belt(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 2)
    if offset is None:
        return None
    belt_decoded = read_string(data, offset, max_length=4096)
    if belt_decoded is None:
        return None
    belt_id, offset = belt_decoded
    path_decoded = _decode_grid_path(data, offset)
    if path_decoded is None:
        return None
    grid_path, offset = path_decoded
    return {"memberCount": 2, "beltId": belt_id, "gridPath": grid_path}, offset


def _decode_item_bundle(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 4)
    if offset is None:
        return None
    count_decoded = read_i32(data, offset)
    if count_decoded is None:
        return None
    count, offset = count_decoded
    id_decoded = read_string(data, offset, max_length=4096)
    if id_decoded is None:
        return None
    item_id, offset = id_decoded
    if offset >= len(data) or data[offset] != 0xFF:
        return None
    inst_data = None
    offset += 1
    inst_decoded = read_u64(data, offset)
    if inst_decoded is None:
        return None
    inst_id, offset = inst_decoded
    return {
        "memberCount": 4,
        "count": count,
        "id": item_id,
        "instData": inst_data,
        "instId": str(inst_id),
    }, offset


def _decode_initial_building(
    data: bytes, offset: int
) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 4)
    if offset is None:
        return None
    broken_decoded = read_bool(data, offset)
    if broken_decoded is None:
        return None
    broken, offset = broken_decoded
    id_decoded = read_string(data, offset, max_length=4096)
    if id_decoded is None:
        return None
    building_id, offset = id_decoded
    repair_decoded = _read_object_list(data, offset, _decode_item_bundle)
    if repair_decoded is None:
        return None
    repair_items, offset = repair_decoded
    transform_decoded = _decode_grid_transform(data, offset)
    if transform_decoded is None:
        return None
    transform, offset = transform_decoded
    return {
        "memberCount": 4,
        "broken": broken,
        "buildingDataId": building_id,
        "repairRequireItems": repair_items,
        "trans": transform,
    }, offset


def _decode_settlement(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    offset = _read_member(data, offset, 2)
    if offset is None:
        return None
    id_decoded = read_string(data, offset, max_length=4096)
    if id_decoded is None:
        return None
    area_id, offset = id_decoded
    areas_decoded = _read_object_list(data, offset, _decode_area_bound)
    if areas_decoded is None:
        return None
    areas, offset = areas_decoded
    return {"memberCount": 2, "areaId": area_id, "areas": areas}, offset


def _decode_level_entity_base(
    data: bytes, offset: int
) -> tuple[dict[str, Any], int] | None:
    values: dict[str, Any] = {}
    for name, reader in (
        ("aoiRadiusTypeRaw", read_i32),
        ("belongLevelScriptId", read_u64),
        ("createStateRaw", read_i32),
        ("dependencyGroupId", read_u64),
    ):
        decoded = reader(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values[name] = str(value) if reader is read_u64 else value
    id_decoded = read_string(data, offset, max_length=4096)
    if id_decoded is None:
        return None
    values["entityDataIdKey"], offset = id_decoded
    type_decoded = read_i32(data, offset)
    if type_decoded is None:
        return None
    values["entityTypeRaw"], offset = type_decoded
    for name in ("forceLoad", "keepCrossMap"):
        decoded = read_bool(data, offset)
        if decoded is None:
            return None
        values[name], offset = decoded
    logic_decoded = read_u64(data, offset)
    if logic_decoded is None:
        return None
    logic_id, offset = logic_decoded
    values["levelLogicId"] = str(logic_id)
    override_decoded = read_bool(data, offset)
    if override_decoded is None:
        return None
    values["overrideSendDieEvent"], offset = override_decoded
    for name in ("position", "rotation", "scale"):
        decoded = _read_vector(data, offset, 3, read_f32)
        if decoded is None:
            return None
        values[name], offset = decoded
    send_decoded = read_bool(data, offset)
    if send_decoded is None:
        return None
    values["sendDieEvent"], offset = send_decoded
    return values, offset


def _decode_factory_region(
    data: bytes, offset: int
) -> tuple[dict[str, Any], int] | None:
    start = offset
    offset = _read_member(data, offset, 26)
    if offset is None:
        return None
    base_decoded = _decode_level_entity_base(data, offset)
    if base_decoded is None:
        return None
    base, offset = base_decoded
    members: dict[str, Any] = {}
    for name, decoder in (
        ("areas", _decode_area),
        ("buildableRange", _decode_buildable_range),
        ("buses", _decode_bus),
        ("cropPanels", _decode_area),
        ("initialBelts", _decode_initial_belt),
        ("initialBuildings", _decode_initial_building),
    ):
        decoded = _read_object_list(data, offset, decoder)
        if decoded is None:
            return None
        members[name], offset = decoded
    main_decoded = read_bool(data, offset)
    if main_decoded is None:
        return None
    members["isMainRegion"], offset = main_decoded
    mines_decoded = _read_object_list(data, offset, _decode_factory_mine)
    if mines_decoded is None:
        return None
    members["mines"], offset = mines_decoded
    power_decoded = read_i32(data, offset)
    if power_decoded is None:
        return None
    members["powerStorageCapacity"], offset = power_decoded
    region_decoded = read_string(data, offset, max_length=4096)
    if region_decoded is None:
        return None
    members["regionId"], offset = region_decoded
    roads_decoded = _read_object_list(data, offset, _decode_grid_path)
    if roads_decoded is None:
        return None
    members["roads"], offset = roads_decoded
    settlement_decoded = _read_object_list(data, offset, _decode_settlement)
    if settlement_decoded is None:
        return None
    members["settlementAreas"], offset = settlement_decoded
    return {
        "memberCount": 26,
        "startOffset": start,
        "endOffset": offset,
        **base,
        **members,
    }, offset


def decode_level_factory_region_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelFactoryRegionData>`` including nested factory records."""

    decoded = _read_object_list(data, offset, _decode_factory_region)
    if decoded is None:
        return None
    value, _ = decoded
    value["itemFieldOrder"] = [
        "aoiRadiusType", "belongLevelScriptId", "createState", "dependencyGroupId",
        "entityDataIdKey", "entityType", "forceLoad", "keepCrossMap",
        "levelLogicId", "overrideSendDieEvent", "position", "rotation", "scale",
        "sendDieEvent", "areas", "buildableRange", "buses", "cropPanels",
        "initialBelts", "initialBuildings", "isMainRegion", "mines",
        "powerStorageCapacity", "regionId", "roads", "settlementAreas",
    ]
    value["fieldOrderSource"] = (
        "current generated LevelEntityDataForMemoryPack and "
        "LevelFactoryRegionDataForMemoryPack wrappers"
    )
    return value


def _read_i32_list(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, offset = decoded
    values: list[int] = []
    for _ in range(max(0, count)):
        item = read_i32(data, offset)
        if item is None:
            return None
        value, offset = item
        values.append(value)
    return {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else values,
    }, offset


def decode_level_doodad_group_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelDoodadGroupData>`` through all nine members."""

    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None, "rows": []}
    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 9:
            return None
        cursor += 1
        center_id_decoded = read_u64(data, cursor)
        if center_id_decoded is None:
            return None
        center_id, cursor = center_id_decoded
        center_short_id_decoded = read_i32(data, cursor)
        if center_short_id_decoded is None:
            return None
        center_short_id, cursor = center_short_id_decoded
        factory_position: list[int] = []
        for _ in range(3):
            component_decoded = read_i32(data, cursor)
            if component_decoded is None:
                return None
            component, cursor = component_decoded
            factory_position.append(component)

        outer_start = cursor
        outer_count_decoded = read_count(data, cursor, max_count=100_000)
        if outer_count_decoded is None:
            return None
        outer_count, cursor = outer_count_decoded
        outer_ids: list[str] = []
        for _ in range(max(0, outer_count)):
            outer_id_decoded = read_u64(data, cursor)
            if outer_id_decoded is None:
                return None
            outer_id, cursor = outer_id_decoded
            outer_ids.append(str(outer_id))
        outer = {
            "startOffset": outer_start,
            "endOffset": cursor,
            "count": outer_count,
            "value": None if outer_count == -1 else outer_ids,
        }
        lists: dict[str, dict[str, Any]] = {}
        for name in (
            "outputSpeedPercentage", "refreshGroupNumLevel",
            "refreshGroupUpperLimitLevel", "upgradeSceneGrade",
        ):
            list_decoded = _read_i32_list(data, cursor)
            if list_decoded is None:
                return None
            lists[name], cursor = list_decoded
        source_decoded = read_i32(data, cursor)
        if source_decoded is None:
            return None
        upgrade_source, cursor = source_decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 9,
            "centerId": str(center_id),
            "centerShortId": center_short_id,
            "factoryPosition": factory_position,
            "outerId": outer,
            **lists,
            "upgradeSourceRaw": upgrade_source,
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "centerId", "centerShortId", "factoryPosition", "outerId",
            "outputSpeedPercentage", "refreshGroupNumLevel",
            "refreshGroupUpperLimitLevel", "upgradeSceneGrade", "upgradeSource",
        ],
        "fieldOrderSource": "current generated LevelDoodadGroupDataForMemoryPack wrapper",
    }
