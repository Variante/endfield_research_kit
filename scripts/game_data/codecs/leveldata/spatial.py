"""Exact generated-wrapper codecs for LevelData spatial records."""

from __future__ import annotations

from typing import Any

from .memorypack import (
    read_bool,
    read_count,
    read_f32,
    read_i32,
    read_i64,
    read_string,
    read_u64,
)


def _read_vector(data: bytes, offset: int, size: int) -> tuple[list[float], int] | None:
    values: list[float] = []
    for _ in range(size):
        decoded = read_f32(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def _read_vector2_list(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, offset = decoded
    rows: list[list[float]] = []
    for _ in range(max(0, count)):
        vector = _read_vector(data, offset, 2)
        if vector is None:
            return None
        value, offset = vector
        rows.append(value)
    return {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else rows,
    }, offset


def _decode_current_polyline_shape(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    """Decode the current environment-volume polyline profile.

    The generated wrapper names all twelve members. Current records have empty
    BVH child/node and convex-polygon collections and a null tree. The reader
    stops if a future record authors one of those nested structures.
    """

    start = offset
    if offset >= len(data):
        return None
    marker = data[offset]
    offset += 1
    if marker == 0xFF:
        return {"startOffset": start, "endOffset": offset, "value": None}, offset
    if marker != 12:
        return None

    base_height = read_f32(data, offset)
    if base_height is None:
        return None
    base_height_offset, offset = base_height

    empty_lists: dict[str, dict[str, Any]] = {}
    for name in ("m_BVHNodeRightChildIndex", "m_BVHNodes"):
        list_start = offset
        decoded = read_count(data, offset, max_count=100_000)
        if decoded is None or decoded[0] not in (-1, 0):
            return None
        count, offset = decoded
        empty_lists[name] = {
            "startOffset": list_start,
            "endOffset": offset,
            "count": count,
            "value": None if count == -1 else [],
        }

    checked = read_bool(data, offset)
    if checked is None:
        return None
    checked_convex, offset = checked

    convex_start = offset
    convex_count_decoded = read_count(data, offset, max_count=100_000)
    if convex_count_decoded is None or convex_count_decoded[0] not in (-1, 0):
        return None
    convex_count, offset = convex_count_decoded
    convex_polygons = {
        "startOffset": convex_start,
        "endOffset": offset,
        "count": convex_count,
        "value": None if convex_count == -1 else [],
    }

    height_decoded = read_f32(data, offset)
    if height_decoded is None:
        return None
    height, offset = height_decoded
    clockwise_decoded = read_bool(data, offset)
    if clockwise_decoded is None:
        return None
    is_clockwise, offset = clockwise_decoded
    dirty_decoded = read_bool(data, offset)
    if dirty_decoded is None:
        return None
    is_dirty, offset = dirty_decoded
    position_decoded = _read_vector(data, offset, 3)
    if position_decoded is None:
        return None
    position, offset = position_decoded
    pos_list_decoded = _read_vector2_list(data, offset)
    if pos_list_decoded is None:
        return None
    pos_list, offset = pos_list_decoded
    rotation_decoded = _read_vector(data, offset, 3)
    if rotation_decoded is None:
        return None
    rotation, offset = rotation_decoded

    tree_start = offset
    if offset >= len(data) or data[offset] != 0xFF:
        return None
    offset += 1
    tree = {"startOffset": tree_start, "endOffset": offset, "value": None}
    return {
        "startOffset": start,
        "endOffset": offset,
        "memberCount": marker,
        "m_baseHeightOffset": base_height_offset,
        **empty_lists,
        "m_checkedConvex": checked_convex,
        "m_convexPolygons": convex_polygons,
        "m_height": height,
        "m_isClockWise": is_clockwise,
        "m_isDirty": is_dirty,
        "m_position": position,
        "m_posList": pos_list,
        "m_rotation": rotation,
        "m_tree": tree,
        "fieldOrderSource": "current generated BeyondPolyLineShapeForMemoryPack wrapper",
    }, offset


def decode_level_environment_volume_list(
    data: bytes,
    offset: int,
) -> dict[str, Any] | None:
    """Decode the current ``List<LevelEnvironmentVolume>`` profile."""

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None, "rows": []}

    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 12:
            return None
        cursor += 1
        blend_distance_decoded = read_f32(data, cursor)
        if blend_distance_decoded is None:
            return None
        blend_distance, cursor = blend_distance_decoded
        blend_mode_decoded = read_i32(data, cursor)
        if blend_mode_decoded is None:
            return None
        blend_mode, cursor = blend_mode_decoded
        path_decoded = read_string(data, cursor, max_length=4096)
        if path_decoded is None:
            return None
        env_phase_path, cursor = path_decoded
        fade_in_decoded = read_f32(data, cursor)
        if fade_in_decoded is None:
            return None
        fade_in_duration, cursor = fade_in_decoded
        fade_out_decoded = read_f32(data, cursor)
        if fade_out_decoded is None:
            return None
        fade_out_duration, cursor = fade_out_decoded
        polyline_decoded = _decode_current_polyline_shape(data, cursor)
        if polyline_decoded is None:
            return None
        polyline, cursor = polyline_decoded
        position_decoded = _read_vector(data, cursor, 3)
        if position_decoded is None:
            return None
        position, cursor = position_decoded
        priority_decoded = read_i32(data, cursor)
        if priority_decoded is None:
            return None
        priority, cursor = priority_decoded
        rotation_decoded = _read_vector(data, cursor, 3)
        if rotation_decoded is None:
            return None
        rotation, cursor = rotation_decoded
        scale_decoded = _read_vector(data, cursor, 3)
        if scale_decoded is None:
            return None
        scale, cursor = scale_decoded
        volume_id_decoded = read_u64(data, cursor)
        if volume_id_decoded is None:
            return None
        volume_id, cursor = volume_id_decoded
        volume_type_decoded = read_i32(data, cursor)
        if volume_type_decoded is None:
            return None
        volume_type, cursor = volume_type_decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 12,
            "blendDistance": blend_distance,
            "blendModeRaw": blend_mode,
            "envPhasePath": env_phase_path,
            "fadeInDuration": fade_in_duration,
            "fadeOutDuration": fade_out_duration,
            "polyLineShape": polyline,
            "position": position,
            "priorityRaw": priority,
            "rotation": rotation,
            "scale": scale,
            "volumeId": str(volume_id),
            "volumeTypeRaw": volume_type,
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "blendDistance", "blendMode", "envPhasePath", "fadeInDuration",
            "fadeOutDuration", "polyLineShape", "position", "priority",
            "rotation", "scale", "volumeId", "volumeType",
        ],
        "fieldOrderSource": "current generated LevelEnvironmentVolumeForMemoryPack wrapper",
    }


def decode_level_map_region_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelMapRegionData>`` including its authored shapes."""

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None, "rows": []}

    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 11:
            return None
        cursor += 1
        scalar_values: dict[str, Any] = {}
        for name in ("groupId", "hideByMistId"):
            decoded = read_i32(data, cursor)
            if decoded is None:
                return None
            scalar_values[name], cursor = decoded
        is_mist_decoded = read_bool(data, cursor)
        if is_mist_decoded is None:
            return None
        is_mist, cursor = is_mist_decoded
        level_id_decoded = read_string(data, cursor, max_length=4096)
        if level_id_decoded is None:
            return None
        level_id, cursor = level_id_decoded
        map_region_id_decoded = read_i32(data, cursor)
        if map_region_id_decoded is None:
            return None
        map_region_id, cursor = map_region_id_decoded
        name_decoded = read_string(data, cursor, max_length=4096)
        if name_decoded is None:
            return None
        map_region_id_name, cursor = name_decoded
        for name in ("mapRegionTypeRaw", "priority"):
            decoded = read_i32(data, cursor)
            if decoded is None:
                return None
            scalar_values[name], cursor = decoded

        shape_start = cursor
        shape_count_decoded = read_count(data, cursor, max_count=100_000)
        if shape_count_decoded is None:
            return None
        shape_count, cursor = shape_count_decoded
        shapes: list[dict[str, Any]] = []
        for shape_index in range(max(0, shape_count)):
            shape_row_start = cursor
            if cursor >= len(data) or data[cursor] != 7:
                return None
            cursor += 1
            polyline_center_decoded = _read_vector(data, cursor, 3)
            if polyline_center_decoded is None:
                return None
            polyline_center, cursor = polyline_center_decoded
            points_decoded = _read_vector2_list(data, cursor)
            if points_decoded is None:
                return None
            polyline_points, cursor = points_decoded
            position_decoded = _read_vector(data, cursor, 3)
            if position_decoded is None:
                return None
            position, cursor = position_decoded
            radius_decoded = read_f32(data, cursor)
            if radius_decoded is None:
                return None
            radius, cursor = radius_decoded
            rotation_decoded = _read_vector(data, cursor, 3)
            if rotation_decoded is None:
                return None
            rotation, cursor = rotation_decoded
            shape_type_decoded = read_i32(data, cursor)
            if shape_type_decoded is None:
                return None
            shape_type, cursor = shape_type_decoded
            size_decoded = _read_vector(data, cursor, 3)
            if size_decoded is None:
                return None
            size, cursor = size_decoded
            shapes.append({
                "indexInCollection": shape_index,
                "startOffset": shape_row_start,
                "endOffset": cursor,
                "memberCount": 7,
                "polyLineCenter": polyline_center,
                "polyLinePoints": polyline_points,
                "position": position,
                "radius": radius,
                "rotation": rotation,
                "shapeTypeRaw": shape_type,
                "size": size,
            })
        shape_list = {
            "startOffset": shape_start,
            "endOffset": cursor,
            "count": shape_count,
            "value": None if shape_count == -1 else shapes,
        }
        tier_index_decoded = read_i32(data, cursor)
        if tier_index_decoded is None:
            return None
        tier_index, cursor = tier_index_decoded
        tier_ids_start = cursor
        tier_count_decoded = read_count(data, cursor, max_count=100_000)
        if tier_count_decoded is None:
            return None
        tier_count, cursor = tier_count_decoded
        tier_ids: list[int] = []
        for _ in range(max(0, tier_count)):
            tier_id_decoded = read_i32(data, cursor)
            if tier_id_decoded is None:
                return None
            tier_id, cursor = tier_id_decoded
            tier_ids.append(tier_id)
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 11,
            **scalar_values,
            "isMist": is_mist,
            "levelId": level_id,
            "mapRegionId": map_region_id,
            "mapRegionIdName": map_region_id_name,
            "shapeList": shape_list,
            "tierIndex": tier_index,
            "tierMapRegionIds": {
                "startOffset": tier_ids_start,
                "endOffset": cursor,
                "count": tier_count,
                "value": None if tier_count == -1 else tier_ids,
            },
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "groupId", "hideByMistId", "isMist", "levelId", "mapRegionId",
            "mapRegionIdName", "mapRegionType", "priority", "shapeList",
            "tierIndex", "tierMapRegionIds",
        ],
        "fieldOrderSource": "current generated LevelMapRegionDataForMemoryPack wrapper",
    }


def decode_level_spline_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelSplineData>`` and Unity Splines Bezier knots."""

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None, "rows": []}

    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 7:
            return None
        cursor += 1
        closed_decoded = read_bool(data, cursor)
        if closed_decoded is None:
            return None
        closed, cursor = closed_decoded

        integer_lists: dict[str, dict[str, Any]] = {}
        key_start = cursor
        key_count_decoded = read_count(data, cursor, max_count=100_000)
        if key_count_decoded is None:
            return None
        key_count, cursor = key_count_decoded
        key_values: list[int] = []
        for _ in range(max(0, key_count)):
            value_decoded = read_i32(data, cursor)
            if value_decoded is None:
                return None
            value, cursor = value_decoded
            key_values.append(value)
        integer_lists["keyNodeIndexList"] = {
            "startOffset": key_start,
            "endOffset": cursor,
            "count": key_count,
            "value": None if key_count == -1 else key_values,
        }

        progress_start = cursor
        progress_count_decoded = read_count(data, cursor, max_count=100_000)
        if progress_count_decoded is None:
            return None
        progress_count, cursor = progress_count_decoded
        progresses: list[float] = []
        for _ in range(max(0, progress_count)):
            value_decoded = read_f32(data, cursor)
            if value_decoded is None:
                return None
            value, cursor = value_decoded
            progresses.append(value)

        knots_start = cursor
        knot_count_decoded = read_count(data, cursor, max_count=100_000)
        if knot_count_decoded is None:
            return None
        knot_count, cursor = knot_count_decoded
        knots: list[dict[str, Any]] = []
        for knot_index in range(max(0, knot_count)):
            knot_start = cursor
            components_decoded = _read_vector(data, cursor, 14)
            if components_decoded is None:
                return None
            components, cursor = components_decoded
            knots.append({
                "indexInCollection": knot_index,
                "startOffset": knot_start,
                "endOffset": cursor,
                "position": components[0:3],
                "tangentIn": components[3:6],
                "tangentOut": components[6:9],
                "rotation": components[9:13],
                "width": components[13],
            })
        position_decoded = _read_vector(data, cursor, 3)
        if position_decoded is None:
            return None
        position, cursor = position_decoded
        rotation_decoded = _read_vector(data, cursor, 3)
        if rotation_decoded is None:
            return None
        rotation, cursor = rotation_decoded
        spline_id_decoded = read_i32(data, cursor)
        if spline_id_decoded is None:
            return None
        spline_id, cursor = spline_id_decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 7,
            "closed": closed,
            **integer_lists,
            "knotProgresses": {
                "startOffset": progress_start,
                "endOffset": knots_start,
                "count": progress_count,
                "value": None if progress_count == -1 else progresses,
            },
            "knots": {
                "startOffset": knots_start,
                "endOffset": knots[-1]["endOffset"] if knots else knots_start + 4,
                "count": knot_count,
                "value": None if knot_count == -1 else knots,
                "structLayout": [
                    "Position.float3", "TangentIn.float3", "TangentOut.float3",
                    "Rotation.quaternion", "Width.float",
                ],
            },
            "position": position,
            "rotation": rotation,
            "splineId": spline_id,
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "closed", "keyNodeIndexList", "knotProgresses", "knots",
            "position", "rotation", "splineId",
        ],
        "fieldOrderSource": (
            "current generated LevelSplineDataForMemoryPack wrapper plus current "
            "Unity.Splines BezierKnot field layout"
        ),
    }


def decode_level_water_volume_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode the generated 26-field ``LevelWaterVolumeData`` records."""

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None, "rows": []}
    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 26:
            return None
        cursor += 1
        row: dict[str, Any] = {
            "indexInCollection": index,
            "startOffset": row_start,
            "memberCount": 26,
        }
        for name in ("amountCurrent", "amountMax", "fillEaseRaw"):
            decoded = read_i32(data, cursor)
            if decoded is None:
                return None
            row[name], cursor = decoded
        for name in ("fillSpeed", "flowDirection", "flowSpeed", "heightMax"):
            decoded = read_f32(data, cursor)
            if decoded is None:
                return None
            row[name], cursor = decoded
        id_decoded = read_u64(data, cursor)
        if id_decoded is None:
            return None
        volume_id, cursor = id_decoded
        row["id"] = str(volume_id)
        for name in (
            "intContainedWater", "isConnectNavMesh", "isInfinite",
            "isPrototype", "isUseLunaConfig",
        ):
            decoded = read_bool(data, cursor)
            if decoded is None:
                return None
            row[name], cursor = decoded
        for name in ("lunaConfigPathHash", "meshPathHash", "navMeshEntityId"):
            decoded = read_i64(data, cursor)
            if decoded is None:
                return None
            row[name], cursor = decoded
        for name, size in (("obbCenter", 3), ("obbRotation", 4), ("obbSize", 3)):
            decoded = _read_vector(data, cursor, size)
            if decoded is None:
                return None
            row[name], cursor = decoded
        parent_decoded = read_u64(data, cursor)
        if parent_decoded is None:
            return None
        parent_id, cursor = parent_decoded
        row["parentId"] = str(parent_id)
        pivot_decoded = _read_vector(data, cursor, 3)
        if pivot_decoded is None:
            return None
        row["pivot"], cursor = pivot_decoded
        points_start = cursor
        points_count_decoded = read_count(data, cursor, max_count=100_000)
        if points_count_decoded is None:
            return None
        points_count, cursor = points_count_decoded
        points: list[list[float]] = []
        for _ in range(max(0, points_count)):
            point_decoded = _read_vector(data, cursor, 3)
            if point_decoded is None:
                return None
            point, cursor = point_decoded
            points.append(point)
        row["points"] = {
            "startOffset": points_start,
            "endOffset": cursor,
            "count": points_count,
            "value": None if points_count == -1 else points,
        }
        item_type_decoded = read_string(data, cursor, max_length=4096)
        if item_type_decoded is None:
            return None
        row["waterItemType"], cursor = item_type_decoded
        lang_start = cursor
        if cursor >= len(data):
            return None
        lang_marker = data[cursor]
        cursor += 1
        if lang_marker == 0xFF:
            row["waterNameLangKey"] = {
                "startOffset": lang_start,
                "endOffset": cursor,
                "value": None,
            }
        elif lang_marker == 1:
            key_decoded = read_string(data, cursor, max_length=4096)
            if key_decoded is None:
                return None
            key, cursor = key_decoded
            row["waterNameLangKey"] = {
                "startOffset": lang_start,
                "endOffset": cursor,
                "memberCount": 1,
                "key": key,
            }
        else:
            return None
        for name in ("waterStartAudio", "waterStopAudio"):
            decoded = read_string(data, cursor, max_length=4096)
            if decoded is None:
                return None
            row[name], cursor = decoded
        row["endOffset"] = cursor
        rows.append(row)
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "amountCurrent", "amountMax", "fillEase", "fillSpeed", "flowDirection",
            "flowSpeed", "heightMax", "id", "intContainedWater", "isConnectNavMesh",
            "isInfinite", "isPrototype", "isUseLunaConfig", "lunaConfigPathHash",
            "meshPathHash", "navMeshEntityId", "obbCenter", "obbRotation", "obbSize",
            "parentId", "pivot", "points", "waterItemType", "waterNameLangKey",
            "waterStartAudio", "waterStopAudio",
        ],
        "fieldOrderSource": "current generated LevelWaterVolumeDataForMemoryPack wrapper",
    }


def decode_level_transform_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelTransformData>`` through all four fields."""

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None, "rows": []}
    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 4:
            return None
        cursor += 1
        key_decoded = read_string(data, cursor, max_length=4096)
        if key_decoded is None:
            return None
        key, cursor = key_decoded
        position_decoded = _read_vector(data, cursor, 3)
        if position_decoded is None:
            return None
        position, cursor = position_decoded
        rotation_decoded = _read_vector(data, cursor, 3)
        if rotation_decoded is None:
            return None
        rotation, cursor = rotation_decoded
        transform_id_decoded = read_i32(data, cursor)
        if transform_id_decoded is None:
            return None
        transform_id, cursor = transform_id_decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 4,
            "key": key,
            "position": position,
            "rotation": rotation,
            "transId": transform_id,
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": ["key", "position", "rotation", "transId"],
        "fieldOrderSource": "current generated LevelTransformDataForMemoryPack wrapper",
    }


def decode_u64_identity_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode a MemoryPack list whose elements are raw unsigned 64-bit IDs."""

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    values: list[str] = []
    for _ in range(max(0, count)):
        value_decoded = read_u64(data, cursor)
        if value_decoded is None:
            return None
        value, cursor = value_decoded
        values.append(str(value))
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "value": None if count == -1 else values,
    }


def decode_level_camera_pose_list(
    data: bytes,
    offset: int,
) -> dict[str, Any] | None:
    """Decode ``List<LevelCameraPoseData>`` from an exact starting cursor.

    The four-member order comes from the current generated
    ``LevelCameraPoseDataForMemoryPack`` wrapper.
    """

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    if count == -1:
        return {
            "startOffset": start,
            "endOffset": cursor,
            "count": count,
            "value": None,
            "rows": [],
        }

    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 4:
            return None
        cursor += 1
        camera_id_decoded = read_i32(data, cursor)
        if camera_id_decoded is None:
            return None
        camera_id, cursor = camera_id_decoded
        fov_decoded = read_f32(data, cursor)
        if fov_decoded is None:
            return None
        fov, cursor = fov_decoded

        vectors: dict[str, list[float]] = {}
        for name in ("position", "rotation"):
            values: list[float] = []
            for _ in range(3):
                component_decoded = read_f32(data, cursor)
                if component_decoded is None:
                    return None
                component, cursor = component_decoded
                values.append(component)
            vectors[name] = values
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 4,
            "cameraId": camera_id,
            "fov": fov,
            "position": vectors["position"],
            "rotation": vectors["rotation"],
        })

    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": ["cameraId", "fov", "position", "rotation"],
        "fieldOrderSource": "current generated LevelCameraPoseDataForMemoryPack wrapper",
    }
