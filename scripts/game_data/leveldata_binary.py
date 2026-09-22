"""Strict partial framing for current-corpus ``LevelData`` payloads."""

from __future__ import annotations

import re
from typing import Any

from scripts.game_data.codecs.leveldata.memorypack import (
    read_bool,
    read_count,
    read_f32,
    read_i32,
    read_string,
    read_u64,
)
from scripts.game_data.codecs.leveldata.levelscript_brief import (
    decode_levelscript_brief_dictionary_at,
)
from scripts.game_data.codecs.leveldata.spatial import (
    decode_level_camera_pose_list,
    decode_level_environment_volume_list,
    decode_level_map_region_list,
    decode_level_spline_list,
    decode_level_transform_list,
    decode_level_water_volume_list,
    decode_u64_identity_list,
)
from scripts.game_data.codecs.leveldata import interactive_layout
from scripts.game_data.codecs.leveldata.factory import (
    decode_level_doodad_group_list,
    decode_level_factory_mine_list,
    decode_level_factory_region_list,
)
from scripts.game_data.codecs.leveldata.ui import decode_level_ui_list
from scripts.game_data.codecs.leveldata.combat import decode_level_enemy_group_list
from scripts.game_data.codecs.leveldata.spawners import decode_level_spawner_list
from scripts.game_data.codecs.leveldata.npc import (
    decode_npc_attract_point_list,
    decode_world_waypoint_list,
)
from scripts.game_data.codecs.leveldata.npc_runtime import (
    LevelNpcCodecError,
    decode_npc_runtime_proxy_list,
)
from scripts.game_data.codecs.leveldata.patrol import decode_npc_patrol_list, decode_patrol_list
from scripts.game_data.codecs.leveldata.enemy_patrol import decode_enemy_patrol_list
from scripts.game_data.codecs.leveldata.guide_hints import decode_level_guide_hint_list
from scripts.game_data.codecs.leveldata.predefined_params import (
    decode_level_factory_predefined_param_list,
)
from scripts.game_data.codecs.leveldata.char_patrol import decode_character_patrol_list
from scripts.game_data.codecs.leveldata.dynamic_occlusion import decode_dynamic_occlude_area_list
from scripts.game_data.codecs.leveldata.sludge import decode_erosion_sludge_list
from scripts.game_data.codecs.leveldata.specific import decode_level_specific_data
from scripts.game_data.codecs.leveldata.levelwide import decode_level_wide_configs
from scripts.game_data.codecs.leveldata.radio_contexts import parse_airwall_groups
from scripts.game_data.codecs.leveldata.blackbox import (
    LevelDataBlackboxCodecError,
    decode_leveldata_blackbox,
)
from scripts.game_data.codecs.leveldata.function_area import (
    LevelFunctionAreaCodecError,
    decode_condition_runtime,
    decode_function_area_condition_list,
    decode_function_area_specific_data_list,
)
from scripts.game_data.codecs.levelscript.interactives import (
    LevelInteractiveCodecError,
    decode_interactive_list,
)
from scripts.game_data.codecs.levelscript.enemies import (
    LevelEnemyCodecError,
    decode_enemy_list,
)
from scripts.game_data.codecs.levelscript.interactive_locks import (
    InteractiveLockCodecError,
    decode_interactive_lock_list,
)


class LevelDataTopLevelFramingError(ValueError):
    """Raised when an exact partial ``LevelData`` frame cannot be proved."""


LEVELDATA_FIELDS = (
    "airWalls", "aiTransData", "autoSpawnedInteractives", "blackbox",
    "buildableCondition", "cameraPoses", "charPatrol", "doodadGroup",
    "dynamicOccludeAreas", "enemies", "enemyGroup", "enemyPatrol",
    "environmentVolumes", "factoryMines", "factoryPredefineData",
    "factoryRegions", "functionArea", "guideHints", "interactiveLockData",
    "interactives", "levelIdNum", "levelScriptBriefDataDict",
    "levelScriptDataPathDict", "levelUIs", "levelWideConfigs",
    "mapVolumeDatas", "missionAreas", "npcAttractPointData", "npcClusters",
    "npcGroup", "npcPatrol", "npcs", "patrols", "predefinedParams",
    "riftVolumes", "safeZone", "sceneId", "sludgeDatas", "spawners",
    "specificData", "splines", "waterVolumes", "worldWayPointData",
)

LEVELDATA_TERMINAL_FIELDS = LEVELDATA_FIELDS[35:]
LEVELDATA_EMPTY_TAIL_FIELDS = LEVELDATA_FIELDS[20:]

_LEVELDATA_NULLABLE_OBJECT_FIELDS = {
    "blackbox",
    "buildableCondition",
    "specificData",
}
_LEVELDATA_COLLECTION_FIELDS = set(LEVELDATA_FIELDS) - {
    "airWalls",
    "blackbox",
    "buildableCondition",
    "factoryPredefineData",
    "functionArea",
    "levelIdNum",
    "levelScriptBriefDataDict",
    "safeZone",
    "sceneId",
    "specificData",
}


def _decode_function_area_base_data_list(
    data: bytes,
    offset: int,
) -> dict[str, Any] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None}
    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data):
            return None
        if data[cursor] == 0xFF:
            rows.append({
                "indexInCollection": index,
                "startOffset": row_start,
                "endOffset": row_start + 1,
                "value": None,
            })
            cursor += 1
            continue
        if data[cursor] != 13:
            return None
        cursor += 1

        buffer_distance_decoded = read_f32(data, cursor)
        if buffer_distance_decoded is None:
            return None
        buffer_distance, cursor = buffer_distance_decoded
        default_off_decoded = read_bool(data, cursor)
        if default_off_decoded is None:
            return None
        default_off, cursor = default_off_decoded

        vectors: dict[str, list[float]] = {}
        for vector_name in ("euler",):
            values: list[float] = []
            for _ in range(3):
                value_decoded = read_f32(data, cursor)
                if value_decoded is None:
                    return None
                value, cursor = value_decoded
                values.append(value)
            vectors[vector_name] = values

        function_type_decoded = read_i32(data, cursor)
        if function_type_decoded is None:
            return None
        function_type, cursor = function_type_decoded
        has_condition_decoded = read_bool(data, cursor)
        if has_condition_decoded is None:
            return None
        has_condition, cursor = has_condition_decoded
        index_decoded = read_i32(data, cursor)
        if index_decoded is None:
            return None
        row_index, cursor = index_decoded

        for vector_name in ("offset",):
            values = []
            for _ in range(3):
                value_decoded = read_f32(data, cursor)
                if value_decoded is None:
                    return None
                value, cursor = value_decoded
                values.append(value)
            vectors[vector_name] = values

        pos_count_decoded = read_count(data, cursor, max_count=100_000)
        if pos_count_decoded is None:
            return None
        pos_count, cursor = pos_count_decoded
        positions: list[list[float]] | None = None if pos_count == -1 else []
        for _ in range(max(0, pos_count)):
            position: list[float] = []
            # Generated ``FunctionAreaBaseData.posList`` is ``List<Vector2>``.
            for _ in range(2):
                value_decoded = read_f32(data, cursor)
                if value_decoded is None:
                    return None
                value, cursor = value_decoded
                position.append(value)
            assert positions is not None
            positions.append(position)

        for vector_name in ("postion",):
            values = []
            for _ in range(3):
                value_decoded = read_f32(data, cursor)
                if value_decoded is None:
                    return None
                value, cursor = value_decoded
                values.append(value)
            vectors[vector_name] = values

        radius_decoded = read_f32(data, cursor)
        shape_type_decoded = read_i32(data, radius_decoded[1]) if radius_decoded else None
        if radius_decoded is None or shape_type_decoded is None:
            return None
        radius, _ = radius_decoded
        shape_type, cursor = shape_type_decoded

        size: list[float] = []
        for _ in range(3):
            value_decoded = read_f32(data, cursor)
            if value_decoded is None:
                return None
            value, cursor = value_decoded
            size.append(value)
        unique_id_decoded = read_u64(data, cursor)
        if unique_id_decoded is None:
            return None
        unique_id, cursor = unique_id_decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 13,
            "bufferDistance": buffer_distance,
            "defaultOff": default_off,
            "euler": vectors["euler"],
            "functionType": function_type,
            "hasCondition": has_condition,
            "index": row_index,
            "offset": vectors["offset"],
            "posList": positions,
            "postion": vectors["postion"],
            "radius": radius,
            "shapeType": shape_type,
            "size": size,
            "uniqueId": str(unique_id),
        })
    return {"startOffset": start, "endOffset": cursor, "count": count, "rows": rows}


def _decode_three_dim_range_list(data: bytes, offset: int) -> dict[str, Any] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None}
    rows: list[dict[str, Any] | None] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data):
            return None
        if data[cursor] == 0xFF:
            rows.append(None)
            cursor += 1
            continue
        if data[cursor] != 2:
            return None
        cursor += 1
        values: list[float] = []
        for _ in range(6):
            value_decoded = read_f32(data, cursor)
            if value_decoded is None:
                return None
            value, cursor = value_decoded
            values.append(value)
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 2,
            "center": values[:3],
            "size": values[3:],
        })
    return {"startOffset": start, "endOffset": cursor, "count": count, "rows": rows}


def frame_leveldata_airwalls_prefix(data: bytes) -> dict[str, Any]:
    """Decode the exact named ``airWalls`` first member and stop its cursor."""
    if not data or data[0] != 43:
        actual = data[0] if data else None
        raise LevelDataTopLevelFramingError(
            f"LevelData member count mismatch: expected=43 actual={actual}"
        )
    decoded = read_count(data, 1, max_count=4096)
    if decoded is None or decoded[0] < 0:
        raise LevelDataTopLevelFramingError("invalid airWalls collection count")
    count, count_end = decoded
    rows = parse_airwall_groups(data)
    if len(rows) != count:
        raise LevelDataTopLevelFramingError(
            f"airWalls record count mismatch: declared={count} decoded={len(rows)}"
        )
    end_offset = count_end if count == 0 else rows[-1].get("recordEndOffset")
    if not isinstance(end_offset, int) or not count_end <= end_offset <= len(data):
        raise LevelDataTopLevelFramingError("airWalls cursor is invalid")
    return {
        "status": "exact_named_airwalls_prefix_with_opaque_remainder",
        "schemaStatus": "partial",
        "serializedMemberCount": 43,
        "bytesConsumed": end_offset,
        "airWalls": {
            "startOffset": 1,
            "endOffset": end_offset,
            "count": count,
            "records": rows,
        },
        "opaqueRemainder": {
            "startOffset": end_offset,
            "endOffset": len(data),
            "length": len(data) - end_offset,
        },
        "evidenceBoundary": (
            "The named first-member airWalls list advances an exact cursor through every "
            "declared record. All later LevelData members remain one opaque remainder."
        ),
    }


def frame_leveldata_named_prefix(data: bytes) -> dict[str, Any]:
    """Advance the generated 43-field order through current simple shapes.

    Collection fields close only when null or empty. For a nonempty collection,
    the count header is still named but its records and every later field remain
    opaque. Nullable objects close only on ``0xff``; a present object's member
    marker is retained as the exact stop. The current empty
    ``LevelFactoryPredefineData`` and ``LevelFunctionAreaData`` wrappers are
    also closed from their generated one- and four-list layouts.
    """
    airwalls = frame_leveldata_airwalls_prefix(data)
    cursor = int(airwalls["bytesConsumed"])
    fields: dict[str, Any] = {"airWalls": airwalls["airWalls"]}
    closed_fields = ["airWalls"]
    open_field: dict[str, Any] | None = None
    has_opaque_nested_records = False

    def read_simple_collection(field: str) -> bool:
        nonlocal cursor, open_field
        start = cursor
        decoded = read_count(data, cursor, max_count=100_000)
        if decoded is None:
            raise LevelDataTopLevelFramingError(
                f"{field}: invalid or truncated collection count at {cursor}"
            )
        count, cursor = decoded
        fields[field] = {
            "startOffset": start,
            "countHeaderEndOffset": cursor,
            "count": count,
            "value": None if count == -1 else [],
        }
        if count in (-1, 0):
            fields[field]["endOffset"] = cursor
            closed_fields.append(field)
            return True
        open_field = {
            "name": field,
            "startOffset": start,
            "countHeaderEndOffset": cursor,
            "count": count,
            "status": "nonempty_collection_records_opaque",
        }
        return False

    for field in LEVELDATA_FIELDS[1:]:
        # Assigned only by exact-range structural closures whose nested record
        # fields are intentionally not decoded.
        if field == "levelScriptBriefDataDict":
            decoded = decode_levelscript_brief_dictionary_at(data, cursor)
            if decoded is None:
                raise LevelDataTopLevelFramingError(
                    f"{field}: exact dictionary codec rejected payload at {cursor}"
                )
            cursor = int(decoded["endOffset"])
            fields[field] = decoded
            closed_fields.append(field)
            continue
        if field in _LEVELDATA_COLLECTION_FIELDS:
            if field == "aiTransData":
                decoded = decode_level_transform_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "autoSpawnedInteractives":
                decoded = decode_u64_identity_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "enemies":
                try:
                    decoded_enemies, enemy_end = decode_enemy_list(data, cursor)
                except LevelEnemyCodecError:
                    decoded_enemies = None
                    enemy_end = cursor
                if decoded_enemies is not None:
                    cursor = enemy_end
                    fields[field] = decoded_enemies
                    closed_fields.append(field)
                    continue
            if field == "enemyGroup":
                decoded = decode_level_enemy_group_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "enemyPatrol":
                decoded = decode_enemy_patrol_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "guideHints":
                decoded = decode_level_guide_hint_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "charPatrol":
                decoded = decode_character_patrol_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "dynamicOccludeAreas":
                decoded = decode_dynamic_occlude_area_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "sludgeDatas":
                decoded = decode_erosion_sludge_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "levelUIs":
                decoded = decode_level_ui_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "npcAttractPointData":
                decoded = decode_npc_attract_point_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "npcPatrol":
                decoded = decode_npc_patrol_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "npcs":
                try:
                    decoded = decode_npc_runtime_proxy_list(data, cursor)
                except LevelNpcCodecError:
                    decoded = None
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "patrols":
                decoded = decode_patrol_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "predefinedParams":
                decoded = decode_level_factory_predefined_param_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "levelWideConfigs":
                decoded = decode_level_wide_configs(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "worldWayPointData":
                decoded = decode_world_waypoint_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "spawners":
                decoded = decode_level_spawner_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "doodadGroup":
                decoded = decode_level_doodad_group_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "factoryMines":
                decoded = decode_level_factory_mine_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "factoryRegions":
                decoded = decode_level_factory_region_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "cameraPoses":
                decoded = decode_level_camera_pose_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "environmentVolumes":
                decoded = decode_level_environment_volume_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "mapVolumeDatas":
                decoded = decode_level_map_region_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "splines":
                decoded = decode_level_spline_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field in {"riftVolumes", "waterVolumes"}:
                decoded = decode_level_water_volume_list(data, cursor)
                if decoded is not None:
                    cursor = int(decoded["endOffset"])
                    fields[field] = decoded
                    closed_fields.append(field)
                    continue
            if field == "interactives":
                try:
                    decoded_interactives, interactive_end = (
                        decode_interactive_list(data, cursor)
                    )
                except LevelInteractiveCodecError:
                    decoded_interactives = None
                    interactive_end = cursor
                if decoded_interactives is not None:
                    cursor = interactive_end
                    fields[field] = decoded_interactives
                    closed_fields.append(field)
                    continue
                count_decoded = read_count(data, cursor, max_count=100_000)
                if count_decoded is None:
                    raise LevelDataTopLevelFramingError(
                        "interactives: invalid collection count"
                    )
                interactive_count, count_end = count_decoded
                if interactive_count > 0:
                    try:
                        terminal = frame_leveldata_empty_tail(data)
                    except LevelDataTopLevelFramingError:
                        terminal = None
                    if terminal is not None:
                        member21_offset = int(
                            terminal["ranges"]["emptyTail"]["startOffset"]
                        )
                        matches = [
                            frame
                            for frame in interactive_layout.level_interactive_data_list_frames(
                                data,
                                final_record_end_offset=member21_offset,
                            )
                            if frame.get("listCountOffset") == cursor
                            and frame.get("listCount") == interactive_count
                            and len(frame.get("records") or []) == interactive_count
                        ]
                        if len(matches) == 1:
                            fields[field] = {
                                "startOffset": cursor,
                                "endOffset": member21_offset,
                                "count": interactive_count,
                                "records": matches[0]["records"],
                                "recordSchemaStatus": "opaque_exact_ranges",
                            }
                            cursor = member21_offset
                            closed_fields.append(field)
                            has_opaque_nested_records = True
                            continue
            if field == "interactiveLockData":
                try:
                    decoded_locks, lock_end = decode_interactive_lock_list(
                        data, cursor
                    )
                except InteractiveLockCodecError:
                    decoded_locks = None
                    lock_end = cursor
                if decoded_locks is not None:
                    cursor = lock_end
                    fields[field] = decoded_locks
                    closed_fields.append(field)
                    continue
            if not read_simple_collection(field):
                break
            continue

        if field == "blackbox":
            start = cursor
            if cursor >= len(data):
                raise LevelDataTopLevelFramingError("blackbox: truncated object marker")
            if data[cursor] == 0xFF:
                fields[field] = {
                    "startOffset": start, "endOffset": start + 1, "value": None
                }
                cursor += 1
                closed_fields.append(field)
                continue
            try:
                decoded_blackbox, cursor = decode_leveldata_blackbox(data, cursor)
            except LevelDataBlackboxCodecError as exc:
                diagnostic = str(exc)
                offset_match = re.search(r"\boffset=(\d+)\b", diagnostic)
                stop_offset = int(offset_match.group(1)) if offset_match else start + 1
                nested_name = diagnostic.split(":", 1)[0]
                open_field = {
                    "name": nested_name if nested_name.startswith("blackbox.") else "blackbox",
                    "startOffset": start,
                    "memberCount": data[start],
                    "headerEndOffset": start + 1,
                    "status": "unsupported_blackbox_shape",
                    "diagnostic": diagnostic,
                    "exactStopOffset": stop_offset,
                }
                fields[field] = dict(open_field)
                cursor = stop_offset
                break
            fields[field] = decoded_blackbox
            closed_fields.append(field)
            continue

        if field == "buildableCondition":
            start = cursor
            if cursor >= len(data):
                raise LevelDataTopLevelFramingError(
                    "buildableCondition: truncated union marker"
                )
            if data[cursor] == 0xFF:
                fields[field] = {"startOffset": start, "endOffset": start + 1,
                                 "value": None}
                cursor += 1
                closed_fields.append(field)
                continue
            try:
                condition, cursor = decode_condition_runtime(
                    data, cursor, "buildableCondition"
                )
            except LevelFunctionAreaCodecError as exc:
                open_field = {
                    "name": field,
                    "startOffset": start,
                    "status": "unsupported_condition_runtime",
                    "diagnostic": str(exc),
                }
                break
            fields[field] = condition
            closed_fields.append(field)
            continue

        if field == "specificData":
            decoded = decode_level_specific_data(data, cursor)
            if decoded is not None:
                cursor = int(decoded["endOffset"])
                fields[field] = decoded
                closed_fields.append(field)
                continue

        if field in _LEVELDATA_NULLABLE_OBJECT_FIELDS:
            start = cursor
            if cursor >= len(data):
                raise LevelDataTopLevelFramingError(f"{field}: truncated object marker")
            marker = data[cursor]
            cursor += 1
            fields[field] = {
                "startOffset": start,
                "memberCount": None if marker == 0xFF else marker,
                "value": None if marker == 0xFF else "present_opaque",
            }
            if marker == 0xFF:
                fields[field]["endOffset"] = cursor
                closed_fields.append(field)
                continue
            open_field = {
                "name": field,
                "startOffset": start,
                "memberCount": marker,
                "headerEndOffset": cursor,
                "status": "present_object_body_opaque",
            }
            break

        if field in {"factoryPredefineData", "functionArea"}:
            start = cursor
            if cursor >= len(data):
                raise LevelDataTopLevelFramingError(f"{field}: truncated object marker")
            marker = data[cursor]
            cursor += 1
            expected = 1 if field == "factoryPredefineData" else 4
            if marker == 0xFF:
                fields[field] = {
                    "startOffset": start, "endOffset": cursor, "value": None
                }
                closed_fields.append(field)
                continue
            if marker != expected:
                open_field = {
                    "name": field,
                    "startOffset": start,
                    "memberCount": marker,
                    "headerEndOffset": cursor,
                    "status": "unsupported_object_member_count",
                }
                fields[field] = dict(open_field)
                break
            member_names = (
                ["powerGates"]
                if field == "factoryPredefineData"
                else ["baseData", "functionAreaConditions", "ranges", "specificDatas"]
            )
            members: dict[str, Any] = {}
            complete = True
            for member_name in member_names:
                member_start = cursor
                if field == "functionArea" and member_name == "baseData":
                    base_data = _decode_function_area_base_data_list(data, cursor)
                    if base_data is None:
                        count_decoded = read_count(data, cursor, max_count=100_000)
                        if count_decoded is None:
                            raise LevelDataTopLevelFramingError(
                                "functionArea.baseData: invalid collection count"
                            )
                        count, cursor = count_decoded
                        members[member_name] = {
                            "startOffset": member_start,
                            "countHeaderEndOffset": cursor,
                            "count": count,
                        }
                        open_field = {
                            "name": "functionArea.baseData",
                            "startOffset": member_start,
                            "countHeaderEndOffset": cursor,
                            "count": count,
                            "status": "unsupported_base_data_record_shape",
                        }
                        complete = False
                        break
                    members[member_name] = base_data
                    cursor = int(base_data["endOffset"])
                    continue
                if field == "functionArea" and member_name == "ranges":
                    ranges = _decode_three_dim_range_list(data, cursor)
                    if ranges is None:
                        count_decoded = read_count(data, cursor, max_count=100_000)
                        if count_decoded is None:
                            raise LevelDataTopLevelFramingError(
                                "functionArea.ranges: invalid collection count"
                            )
                        count, cursor = count_decoded
                        members[member_name] = {
                            "startOffset": member_start,
                            "countHeaderEndOffset": cursor,
                            "count": count,
                        }
                        open_field = {
                            "name": "functionArea.ranges",
                            "startOffset": member_start,
                            "countHeaderEndOffset": cursor,
                            "count": count,
                            "status": "unsupported_range_record_shape",
                        }
                        complete = False
                        break
                    members[member_name] = ranges
                    cursor = int(ranges["endOffset"])
                    continue
                if field == "functionArea" and member_name in {
                    "functionAreaConditions",
                    "specificDatas",
                }:
                    decoder = (
                        decode_function_area_condition_list
                        if member_name == "functionAreaConditions"
                        else decode_function_area_specific_data_list
                    )
                    try:
                        nested = decoder(data, cursor)
                    except LevelFunctionAreaCodecError as exc:
                        nested = None
                        nested_diagnostic = str(exc)
                    if nested is not None:
                        members[member_name] = nested
                        cursor = int(nested["endOffset"])
                        continue
                    decoded = read_count(data, cursor, max_count=100_000)
                    if decoded is None:
                        base_data = members.get("baseData")
                        if isinstance(base_data, dict) and int(base_data.get("count") or 0) > 0:
                            base_start = int(base_data["startOffset"])
                            base_count = int(base_data["count"])
                            cursor = base_start + 4
                            members["baseData"] = {
                                "startOffset": base_start,
                                "countHeaderEndOffset": cursor,
                                "count": base_count,
                            }
                            open_field = {
                                "name": "functionArea.baseData",
                                "startOffset": base_start,
                                "countHeaderEndOffset": cursor,
                                "count": base_count,
                                "status": "unsupported_base_data_record_shape",
                            }
                            complete = False
                            break
                        raise LevelDataTopLevelFramingError(
                            f"functionArea.{member_name}: invalid collection count"
                        )
                    count, cursor = decoded
                    members[member_name] = {
                        "startOffset": member_start,
                        "countHeaderEndOffset": cursor,
                        "count": count,
                    }
                    open_field = {
                        "name": f"functionArea.{member_name}",
                        "startOffset": member_start,
                        "countHeaderEndOffset": cursor,
                        "count": count,
                        "status": "unsupported_nested_record_shape",
                        "diagnostic": nested_diagnostic,
                    }
                    complete = False
                    break
                decoded = read_count(data, cursor, max_count=100_000)
                if decoded is None:
                    base_data = members.get("baseData") if field == "functionArea" else None
                    if isinstance(base_data, dict) and int(base_data.get("count") or 0) > 0:
                        base_start = int(base_data["startOffset"])
                        base_count = int(base_data["count"])
                        cursor = base_start + 4
                        members["baseData"] = {
                            "startOffset": base_start,
                            "countHeaderEndOffset": cursor,
                            "count": base_count,
                        }
                        open_field = {
                            "name": "functionArea.baseData",
                            "startOffset": base_start,
                            "countHeaderEndOffset": cursor,
                            "count": base_count,
                            "status": "unsupported_base_data_record_shape",
                        }
                        complete = False
                        break
                    raise LevelDataTopLevelFramingError(
                        f"{field}.{member_name}: invalid collection count"
                    )
                count, cursor = decoded
                members[member_name] = {
                    "startOffset": member_start,
                    "countHeaderEndOffset": cursor,
                    "count": count,
                    "value": None if count == -1 else [],
                }
                if count not in (-1, 0):
                    open_field = {
                        "name": f"{field}.{member_name}",
                        "startOffset": member_start,
                        "countHeaderEndOffset": cursor,
                        "count": count,
                        "status": "nonempty_collection_records_opaque",
                    }
                    complete = False
                    break
                members[member_name]["endOffset"] = cursor
            fields[field] = {
                "startOffset": start,
                "memberCount": marker,
                "members": members,
            }
            if not complete:
                break
            fields[field]["endOffset"] = cursor
            closed_fields.append(field)
            continue

        if field == "levelIdNum":
            start = cursor
            decoded = read_i32(data, cursor)
            if decoded is None:
                raise LevelDataTopLevelFramingError("levelIdNum: truncated int32")
            value, cursor = decoded
            fields[field] = {"startOffset": start, "endOffset": cursor, "value": value}
            closed_fields.append(field)
            continue

        if field == "safeZone":
            start = cursor
            if cursor >= len(data):
                raise LevelDataTopLevelFramingError("safeZone: truncated object marker")
            marker = data[cursor]
            cursor += 1
            if marker == 0xFF:
                fields[field] = {"startOffset": start, "endOffset": cursor, "value": None}
                closed_fields.append(field)
                continue
            if marker != 1:
                open_field = {
                    "name": field, "startOffset": start, "memberCount": marker,
                    "headerEndOffset": cursor, "status": "unsupported_object_member_count",
                }
                fields[field] = dict(open_field)
                break
            decoded = read_i32(data, cursor)
            if decoded is None:
                raise LevelDataTopLevelFramingError("safeZone: truncated value")
            value, cursor = decoded
            fields[field] = {
                "startOffset": start, "endOffset": cursor,
                "memberCount": 1, "value": value,
            }
            closed_fields.append(field)
            continue

        if field == "sceneId":
            start = cursor
            decoded = read_string(data, cursor, max_length=1024)
            if decoded is None:
                raise LevelDataTopLevelFramingError("sceneId: invalid UTF-8 string")
            value, cursor = decoded
            fields[field] = {"startOffset": start, "endOffset": cursor, "value": value}
            closed_fields.append(field)
            continue

        raise AssertionError(f"unhandled LevelData field {field}")

    exact = open_field is None and len(closed_fields) == len(LEVELDATA_FIELDS)
    if exact and cursor != len(data):
        raise LevelDataTopLevelFramingError(
            f"LevelData trailing bytes: cursor={cursor} length={len(data)}"
        )
    result: dict[str, Any] = {
        "status": (
            "exact_named_outer_frame"
            if exact and has_opaque_nested_records
            else "exact_named_schema" if exact
            else "exact_named_prefix_with_opaque_remainder"
        ),
        "schemaStatus": (
            "named_exact_frame"
            if exact and has_opaque_nested_records
            else "named_exact" if exact
            else "partial"
        ),
        "serializedMemberCount": 43,
        "bytesConsumed": cursor,
        "fieldOrder": list(LEVELDATA_FIELDS),
        "closedFields": closed_fields,
        "fields": fields,
        "openField": open_field,
        "hasOpaqueNestedRecords": has_opaque_nested_records,
        "opaqueRemainder": None if exact else {
            "startOffset": cursor,
            "endOffset": len(data),
            "length": len(data) - cursor,
        },
        "evidenceBoundary": (
            "Generated wrapper order and strict current simple-shape readers close all "
            "43 fields through EOF."
            if exact else
            "Generated wrapper order closes each listed field sequentially and stops "
            "at the first nonempty or unsupported nested body."
        ),
    }
    if not exact:
        for terminal_reader in (frame_leveldata_empty_tail, frame_leveldata_terminal_suffix):
            try:
                result["independentTerminalFrame"] = terminal_reader(data)
                break
            except LevelDataTopLevelFramingError:
                continue
    return result


def frame_leveldata_terminal_suffix(data: bytes) -> dict[str, Any]:
    """Frame the named final eight members of a 43-member LevelData.

    This is intentionally weaker than :func:`frame_leveldata_empty_tail`: it
    Generated wrapper order assigns this suffix to ``safeZone`` through
    ``worldWayPointData``. Every earlier byte remains opaque. The object
    marker/value, string, two empty collections, null union, and three final
    empty collections must close at physical EOF, with exactly one candidate.
    """
    if not data:
        raise LevelDataTopLevelFramingError("truncated LevelData: empty payload")
    if data[0] != 43:
        raise LevelDataTopLevelFramingError(
            f"LevelData member count mismatch: expected=43 actual={data[0]}"
        )
    if len(data) < 34:
        raise LevelDataTopLevelFramingError(
            "truncated LevelData terminal suffix: expected at least 34 bytes"
        )

    candidates: list[dict[str, Any]] = []
    for start in range(max(1, len(data) - 384), len(data)):
        if data[start : start + 5] != b"\x01\x00\x00\x00\x00":
            continue
        cursor = start + 5
        string_decoded = read_string(data, cursor, max_length=256)
        if string_decoded is None:
            continue
        string_value, cursor = string_decoded
        empty_collection_offsets: list[int] = []
        valid = True
        for _ in range(2):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            empty_collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or cursor >= len(data) or data[cursor] != 0xFF:
            continue
        null_union_offset = cursor
        cursor += 1
        for _ in range(3):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            empty_collection_offsets.append(cursor)
            _, cursor = decoded
        if valid and cursor == len(data):
            candidates.append({
                "startOffset": start,
                "endOffset": cursor,
                "fieldOrder": list(LEVELDATA_TERMINAL_FIELDS),
                "safeZone": {
                    "memberCount": data[start],
                    "rawValue": int.from_bytes(
                        data[start + 1 : start + 5], "little", signed=True
                    ),
                },
                "sceneId": string_value,
                "sludgeDatasCount": 0,
                "spawnersCount": 0,
                "specificData": None,
                "splinesCount": 0,
                "waterVolumesCount": 0,
                "worldWayPointDataCount": 0,
                "emptyCollectionOffsets": empty_collection_offsets,
                "nullUnionOffset": null_union_offset,
                "nullUnionRawTag": data[null_union_offset],
            })
    if len(candidates) != 1:
        raise LevelDataTopLevelFramingError(
            "LevelData terminal EOF suffix is not unique and exact: "
            f"candidates={len(candidates)} length={len(data)}"
        )
    suffix = candidates[0]
    return {
        "status": "exact_named_terminal_suffix_with_opaque_top_level_prefix",
        "schemaStatus": "partial",
        "serializedMemberCount": 43,
        "bytesConsumed": len(data),
        "ranges": {
            "memberCount": {"startOffset": 0, "endOffset": 1},
            "opaqueTopLevelPrefix": {
                "startOffset": 1,
                "endOffset": suffix["startOffset"],
                "length": suffix["startOffset"] - 1,
                "status": "opaque_unassigned_top_level_members",
            },
            "terminalSuffix": suffix,
        },
        "evidenceBoundary": (
            "Generated wrapper order names the final eight members, and their cursor "
            "consumes exactly to EOF. Every preceding top-level byte remains unresolved."
        ),
    }


def frame_leveldata_empty_tail(data: bytes) -> dict[str, Any]:
    """Frame named members 21 through 43 in the known empty-tail shape.

    The current corpus contains a recurring tail made of a non-negative i32,
    fourteen empty collections, a one-member object envelope, a UTF-8 string,
    two empty collections, a null union tag, and three empty collections.
    Generated wrapper order assigns the scalar to ``levelIdNum``, the next
    fourteen collections through ``riftVolumes``, and the common final suffix
    to ``safeZone`` through ``worldWayPointData``. The preceding bytes remain
    one explicit opaque range.
    """
    if not data:
        raise LevelDataTopLevelFramingError("truncated LevelData: empty payload")
    if data[0] != 43:
        raise LevelDataTopLevelFramingError(
            f"LevelData member count mismatch: expected=43 actual={data[0]}"
        )
    if len(data) < 91:
        raise LevelDataTopLevelFramingError(
            "truncated LevelData empty tail: expected at least 91 bytes"
        )

    # The only variable-width item in this tail is bounded to 256 bytes, so a
    # valid start must be within this bounded window before EOF.
    candidates: list[dict[str, Any]] = []
    for start in range(max(1, len(data) - 384), len(data)):
        scalar = read_i32(data, start)
        if scalar is None or scalar[0] < 0:
            continue
        scalar_value, cursor = scalar
        empty_collection_offsets: list[int] = []
        valid = True
        for _ in range(14):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            empty_collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or data[cursor : cursor + 5] != b"\x01\x00\x00\x00\x00":
            continue
        object_offset = cursor
        cursor += 5
        string_decoded = read_string(data, cursor, max_length=256)
        if string_decoded is None:
            continue
        string_value, cursor = string_decoded
        for _ in range(2):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            empty_collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or cursor >= len(data) or data[cursor] != 0xFF:
            continue
        null_union_offset = cursor
        cursor += 1
        for _ in range(3):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            empty_collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or cursor != len(data):
            continue
        candidates.append({
            "startOffset": start,
            "endOffset": cursor,
            "fieldOrder": list(LEVELDATA_EMPTY_TAIL_FIELDS),
            "levelIdNum": scalar_value,
            "emptyFieldsBeforeSafeZone": list(LEVELDATA_FIELDS[21:35]),
            "oneMemberObjectOffset": object_offset,
            "safeZone": {
                "memberCount": data[object_offset],
                "rawValue": int.from_bytes(
                    data[object_offset + 1 : object_offset + 5],
                    "little",
                    signed=True,
                ),
            },
            "sceneId": string_value,
            "sludgeDatasCount": 0,
            "spawnersCount": 0,
            "specificData": None,
            "splinesCount": 0,
            "waterVolumesCount": 0,
            "worldWayPointDataCount": 0,
            "emptyCollectionOffsets": empty_collection_offsets,
            "nullUnionOffset": null_union_offset,
            "nullUnionRawTag": data[null_union_offset],
        })

    if len(candidates) != 1:
        raise LevelDataTopLevelFramingError(
            "LevelData empty EOF tail is not unique and exact: "
            f"candidates={len(candidates)} length={len(data)}"
        )
    tail = candidates[0]
    return {
        "status": "exact_named_empty_tail_with_opaque_top_level_prefix",
        "schemaStatus": "partial",
        "serializedMemberCount": 43,
        "bytesConsumed": len(data),
        "ranges": {
            "memberCount": {"startOffset": 0, "endOffset": 1},
            "opaqueTopLevelPrefix": {
                "startOffset": 1,
                "endOffset": tail["startOffset"],
                "length": tail["startOffset"] - 1,
                "status": "opaque_unassigned_top_level_members",
            },
            "emptyTail": tail,
        },
        "evidenceBoundary": (
            "Generated wrapper order names members 21 through 43 and their cursor "
            "consumes exactly to EOF; members 1 through 20 remain an opaque prefix."
        ),
    }
