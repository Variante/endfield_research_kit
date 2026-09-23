"""Exact codec for the LevelScript task map and its condition unions.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import re
import struct

from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript import top_level_tail as levelscript_top_level_tail
from scripts.game_data.codecs.levelscript.condition_params import _decode_entity_ptr_list_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_levelscript_ptr_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_levelscript_task_ptr_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_nullable_string_value
from scripts.game_data.codecs.levelscript.condition_params import _decode_string_collection_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_string_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_u32_collection_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_u64_param
from scripts.game_data.codecs.levelscript.framing_common import LevelScriptTopLevelFramingError
from scripts.game_data.codecs.levelscript.framing_common import _offset_hex
from scripts.game_data.codecs.levelscript.framing_common import _read_compact_string
from scripts.game_data.codecs.levelscript.framing_common import _u64_offsets
from scripts.game_data.codecs.levelscript.params import decode_bool_param as _decode_bool_param
from scripts.game_data.codecs.levelscript.params import decode_constant_string_param as _decode_constant_string_param
from scripts.game_data.codecs.levelscript.params import decode_i32_param as _decode_i32_param
from scripts.game_data.codecs.levelscript.params import decode_param_tail as _decode_param_tail
from scripts.game_data import levelscript_union_tags as union_tags
from scripts.game_data.levelscript_task_condition_native import load_levelscript_task_condition_rows
from typing import Any

LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID = (
    "gameassembly-2026-07-22-levelscript-task-check-mission-state-0x67"
)


LEVELSCRIPT_TASK_CONDITION_MAPPING_ID = (
    "gameassembly-2026-09-20-levelscript-task-root-gamecondition-tags-v4"
)


def _task_condition_tag(name: str) -> Any:
    """The current GameCondition tag of ``name``, resolved by type name.

    A tag is the type's rank in the union and renumbers when a condition is
    added, so it is never written down. Names outside the ``Conditions``
    namespace are recorded bare and looked up both ways; exactly one must
    exist. Without the recorded build the key is a placeholder no byte equals.
    """
    candidates = [
        found for found in (
            union_tags.pair("GameCondition", name.replace(".", "_")),
            union_tags.pair("GameCondition", "Conditions_" + name),
        )
        if isinstance(found[0], int)
    ]
    if len(candidates) != 1:
        return ("unresolved", "GameCondition", name)
    return candidates[0][0]


# Reviewed condition payload layouts: the type name and the member count its
# codec reads. A current wrapper with another member count fails closed.
LEVELSCRIPT_TASK_CONDITION_TAGS = {
    _task_condition_tag(name): (name, member_count)
    for name, member_count in (
        ("CheckBuildingConnected", 8),
        ("CheckBuildingConnectedAsMA2SB", 8),
        ("CheckBuildingConnectedExist", 8),
        ("CheckBuildingConnectedSpecify", 9),
        ("CheckBuildingStateInArea", 9),
        ("CheckClientGlobalVar", 7),
        ("CheckCutsceneFinish", 5),
        ("CheckDomainShopChannelLevel", 7),
        ("CheckFacBuildingState", 8),
        ("CheckFactoryBlackBoxState", 7),
        ("CheckFluidVolume", 9),
        ("CheckFMVFinish", 5),
        ("CheckGuideGroupComplete", 6),
        ("CheckInteractiveDestroyed", 6),
        ("CheckInteractiveLock", 7),
        ("CheckLevelScriptPropertyBool", 9),
        ("CheckLevelScriptPropertyInt", 9),
        ("CheckLevelScriptStage", 8),
        ("CheckLevelScriptStageReachMax", 6),
        ("CheckLsmEncounterCompleted", 7),
        ("CheckMissionState", 7),
        ("CheckMonsterKilled", 9),
        ("CheckMonsterSpawnerComplete", 6),
        ("CheckPerfectlyPassDungeonId", 5),
        ("CheckPlayerInMap", 5),
        ("CheckPRTSUnlocked", 5),
        ("CheckQuestState", 7),
        ("CheckRepairBuilding", 6),
        ("CheckRepeatableTalkFinish", 6),
        ("CheckRichContentReadingDone", 5),
        ("CheckScanInteractive", 6),
        ("CheckScriptTaskStateEqual", 9),
        ("CheckScriptMonsterKilled", 10),
        ("CheckServerGlobalVar", 7),
        ("CheckSewageTreatPlantLevel", 7),
        ("CheckSpaceshipRoomBuilt", 7),
        ("CheckTalkOptionFinish", 6),
        ("CheckTerminalReadingDone", 5),
        ("CombineCondition", 6),
        ("Conditions.CheckCurrentDungeonBoth", 5),
        ("OnBuildingPanelOpen", 6),
        ("DepotHasItem", 7),
        ("FacBattleBuildingCurEnergy", 8),
        ("FacBuildingCountInScene", 8),
        ("FacBuildingFluidContainerHasItem", 9),
        ("FacBuildingProducingCountInScene", 8),
        ("FacProducePowerReach", 6),
        ("FacProducingFormulaCountInScene", 8),
        ("FacStatisticItemGen", 8),
        ("FacStatisticItemGenRate", 8),
        ("HasItemCount", 7),
        ("InteractiveCheckBool", 8),
        ("InteractiveCheckInt", 9),
        ("PlayerHasItem", 8),
        ("PlayerHasItemInItemBag", 8),
        ("TaskReachDestination", 6),
        ("SystemPoiLevel", 8),
    )
}


_MISSION_STATE_NAMES = {
    0: "None",
    1: "Available",
    2: "Processing",
    3: "Completed",
    4: "Failed",
    5: "Disabled",
}


_QUEST_STATE_NAMES = {
    0: "None",
    2: "Processing",
    3: "Completed",
    4: "Failed",
    5: "Disabled",
}


_MISSION_STATE_COMPARER_NAMES = {
    0: "Equal",
    1: "NotEqual",
}


_NUMBER_COMPARER_NAMES = {
    0: "Equal",
    1: "NotEqual",
    2: "GreaterThan",
    3: "GreaterEqual",
    4: "LessThan",
    5: "LessEqual",
}


_FACTORY_BLACK_BOX_STATE_NAMES = {
    0: "Inactive",
    1: "Active",
    2: "PassMainTask",
    3: "PassAllTask",
}


_SPACESHIP_ROOM_TYPE_NAMES = {
    0: "ControlCenter",
    1: "ManufacturingStation",
    2: "GrowCabin",
    3: "GuestRoom",
    4: "CommandCenter",
    5: "GuestRoomClueExtension",
    999996: "Any",
    999997: "FlexibleTypeB",
    999998: "FlexibleTypeA",
    999999: "Invalid",
}


_DOMAIN_POI_TYPE_NAMES = {
    0: "None",
    1: "Settlement",
    2: "DomainShop",
    3: "DomainDepot",
    4: "KiteStation",
    5: "RecycleBin",
    120: "SewageTreatPlant",
    130: "SimulationTraining",
    150: "TyphoeaArchery",
}


def _decode_task_condition_union_header(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[int, int, str, int] | None:
    if offset + 2 > limit:
        return None
    if data[offset] < 0xFA:
        return data[offset], data[offset + 1], "memorypack-u8", offset + 2
    if data[offset] == 0xFA and offset + 4 <= limit:
        return (
            struct.unpack_from("<H", data, offset + 1)[0],
            data[offset + 3],
            "memorypack-fa-u16",
            offset + 4,
        )
    return None


def _decode_task_condition_common(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[dict[str, Any], int] | None:
    if offset + 4 > limit:
        return None
    scope_mask = struct.unpack_from("<i", data, offset)[0]
    unique_id, cursor = _read_compact_string(data, offset + 4)
    if (
        unique_id is None
        or cursor is None
        or cursor + 2 > limit
        or not re.fullmatch(r"[0-9a-f]{8}", unique_id)
        or data[cursor] not in (0, 1)
        or data[cursor + 1] not in (0, 1)
        or scope_mask < 0
        or scope_mask > 0xFFFF
    ):
        return None
    return {
        "scopeMask": scope_mask,
        "uniqueId": unique_id,
        "useCurrentScope": bool(data[cursor]),
        "useGraphScope": bool(data[cursor + 1]),
    }, cursor + 2


def _condition_param(
    decoder: Any,
    data: bytes,
    cursor: int,
    limit: int,
) -> tuple[Any, int] | None:
    decoded = decoder(data, cursor)
    if decoded is None or decoded[1] > limit:
        return None
    return decoded


def _decode_nullable_param(
    decoder: Any,
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode a nullable generated ``Param<T>`` wrapper exactly."""
    if cursor < len(data) and data[cursor] == 0xFF:
        return {"status": "null", "value": None}, cursor + 1
    return decoder(data, cursor)


def _decode_generic_task_condition_fields(
    data: bytes,
    offset: int,
    limit: int,
    *,
    field_count: int,
) -> tuple[list[dict[str, Any]], int] | None:
    """Recover a unique authored ``Param`` sequence without per-type code.

    Current ``GameConditionForMemoryPack`` payloads share four base members;
    the union member count therefore bounds the number of concrete fields.
    Generated condition formatters serialize those fields as self-delimiting
    ``Param<T>`` values.  Try the reusable Param shapes, retain only endpoints
    followed by the exact task-objective envelope, and fail closed unless one
    field-boundary sequence survives.  Equal-size scalar interpretations are
    deliberately kept opaque instead of guessing an enum/int/float meaning.
    """
    if field_count < 0 or field_count > 32:
        return None

    def scalar4_param(cursor: int) -> tuple[dict[str, Any], int] | None:
        if cursor + 5 > limit or data[cursor] != 0x04:
            return None
        tail = _decode_param_tail(data, cursor + 5)
        if tail is None or tail[1] > limit:
            return None
        raw = data[cursor + 1 : cursor + 5]
        detail, end = tail
        return {
            "shape": "param-scalar4",
            "rawHex": raw.hex(),
            "int32Value": struct.unpack_from("<i", raw)[0],
            "uint32Value": struct.unpack_from("<I", raw)[0],
            **detail,
        }, end

    def wrap(
        shape: str,
        decoder: Any,
        cursor: int,
    ) -> tuple[dict[str, Any], int] | None:
        decoded = decoder(data, cursor)
        if decoded is None or decoded[1] > limit:
            return None
        value, end = decoded
        return {"shape": shape, **value}, end

    decoders = (
        ("param-string", _decode_string_param),
        ("param-string-collection", _decode_string_collection_param),
        ("param-bool", _decode_bool_param),
        ("param-entity-ptr", levelscript_params.decode_constant_entity_ptr_param),
        ("param-entity-ptr-list", _decode_entity_ptr_list_param),
        ("param-levelscript-ptr", _decode_levelscript_ptr_param),
        ("param-levelscript-task-ptr", _decode_levelscript_task_ptr_param),
        ("param-u64", _decode_u64_param),
    )
    memo: dict[tuple[int, int], list[tuple[list[dict[str, Any]], int]]] = {}

    def visit(
        cursor: int,
        remaining: int,
    ) -> list[tuple[list[dict[str, Any]], int]]:
        memo_key = (cursor, remaining)
        cached = memo.get(memo_key)
        if cached is not None:
            return cached
        if remaining == 0:
            if cursor + 5 > limit or data[cursor] not in (0, 1):
                memo[memo_key] = []
                return []
            objective_enum = struct.unpack_from("<i", data, cursor + 1)[0]
            memo[memo_key] = (
                [([], cursor)] if 0 <= objective_enum <= 0x100 else []
            )
            return memo[memo_key]

        candidates: dict[int, list[dict[str, Any]]] = {}
        scalar = scalar4_param(cursor)
        if scalar is not None:
            candidates[scalar[1]] = [scalar[0]]
        for shape, decoder in decoders:
            decoded = wrap(shape, decoder, cursor)
            if decoded is None:
                continue
            field, end = decoded
            same_end = candidates.setdefault(end, [])
            if not any(row.get("shape") == shape for row in same_end):
                same_end.append(field)

        rows: list[tuple[list[dict[str, Any]], int]] = []
        for end, same_end_fields in sorted(candidates.items()):
            if len(same_end_fields) == 1:
                field = same_end_fields[0]
            else:
                field = {
                    "shape": "ambiguous-same-boundary",
                    "candidateShapes": [
                        row.get("shape") for row in same_end_fields
                    ],
                    "candidates": same_end_fields,
                }
            for tail_fields, final_end in visit(end, remaining - 1):
                rows.append(([field, *tail_fields], final_end))
                if len(rows) > 128:
                    memo[memo_key] = []
                    return []
        memo[memo_key] = rows
        return rows

    parses = visit(offset, field_count)
    boundary_sequences = {
        (
            end,
            tuple(
                (
                    str(field.get("shape") or ""),
                    tuple(
                        str(value)
                        for value in field.get("candidateShapes") or []
                    ),
                )
                for field in fields
            ),
        ): (fields, end)
        for fields, end in parses
    }
    if len(boundary_sequences) != 1:
        return None
    return next(iter(boundary_sequences.values()))


def _decode_levelscript_task_condition(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one supported root ``GameCondition`` task payload exactly."""
    start = offset
    header = _decode_task_condition_union_header(data, offset, limit)
    if header is None:
        return None
    union_tag, member_count, tag_encoding, cursor = header
    identity = LEVELSCRIPT_TASK_CONDITION_TAGS.get(union_tag)
    native_mapping_id = LEVELSCRIPT_TASK_CONDITION_MAPPING_ID
    if identity is None:
        supplemental_rows, supplemental_audit = load_levelscript_task_condition_rows()
        supplemental = supplemental_rows.get((union_tag, member_count))
        if supplemental is not None:
            identity = (supplemental["conditionType"], supplemental["memberCount"])
            native_mapping_id = (
                "endfield.levelscript-task-condition-native.v1:"
                + supplemental_audit["contractSha256"]
            )
    if identity is None or identity[1] != member_count:
        return None
    condition_type = identity[0]
    common_decoded = _decode_task_condition_common(data, cursor, limit)
    if common_decoded is None:
        return None
    common, cursor = common_decoded
    fields: dict[str, Any] = {}

    def read_param(name: str, decoder: Any) -> bool:
        nonlocal cursor
        decoded = _condition_param(decoder, data, cursor, limit)
        if decoded is None:
            return False
        fields[name], cursor = decoded
        return True

    def read_nullable_param(name: str, decoder: Any) -> bool:
        nonlocal cursor
        decoded = _condition_param(
            lambda payload, start: _decode_nullable_param(
                decoder,
                payload,
                start,
            ),
            data,
            cursor,
            limit,
        )
        if decoded is None:
            return False
        fields[name], cursor = decoded
        return True

    if condition_type == "CheckMissionState":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("missionId", _decode_string_param)
            and read_param("targetMissionState", _decode_i32_param)
        ):
            return None
        comparer_raw = fields["comparer"]["value"]
        target_raw = fields["targetMissionState"]["value"]
        if (
            comparer_raw not in _MISSION_STATE_COMPARER_NAMES
            or target_raw not in _MISSION_STATE_NAMES
        ):
            return None
        fields["comparerName"] = _MISSION_STATE_COMPARER_NAMES[comparer_raw]
        fields["targetMissionStateName"] = _MISSION_STATE_NAMES[target_raw]
    elif condition_type == "CheckQuestState":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("questId", _decode_string_param)
            and read_param("targetQuestState", _decode_i32_param)
        ):
            return None
        comparer_raw = fields["comparer"]["value"]
        target_raw = fields["targetQuestState"]["value"]
        if (
            comparer_raw not in _MISSION_STATE_COMPARER_NAMES
            or target_raw not in _QUEST_STATE_NAMES
        ):
            return None
        fields["comparerName"] = _MISSION_STATE_COMPARER_NAMES[comparer_raw]
        fields["targetQuestStateName"] = _QUEST_STATE_NAMES[target_raw]
    elif condition_type == "CheckFMVFinish":
        if not read_param("fmvId", _decode_string_param):
            return None
    elif condition_type in ("CheckClientGlobalVar", "CheckServerGlobalVar"):
        key_decoder = (
            _decode_string_param
            if condition_type == "CheckClientGlobalVar"
            else _decode_i32_param
        )
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("key", key_decoder)
            and read_param("targetValue", _decode_u64_param)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type in (
        "CheckBuildingConnected",
        "CheckBuildingConnectedAsMA2SB",
    ):
        if not (
            read_param("facBuildingIdA", _decode_string_param)
            and read_param("facBuildingIdB", _decode_string_param)
            and read_param("targetCount", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckBuildingConnectedExist":
        if not (
            read_param("buildingIdEnd", _decode_string_param)
            and read_param("buildingIdStart", _decode_string_param)
            and read_param("exist", _decode_bool_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckBuildingConnectedSpecify":
        if not (
            read_param("connected", _decode_bool_param)
            and read_param("conveyorType", _decode_i32_param)
            and read_param("instKeyA", _decode_string_param)
            and read_param("instKeyB", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckBuildingStateInArea":
        if not (
            read_param("facBuildingId", _decode_string_param)
            and read_param("facStateType", _decode_i32_param)
            and read_param("targetAreaId", _decode_string_param)
            and read_param("targetCount", _decode_i32_param)
            and read_param("targetMapId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckFluidVolume":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("targetVolume", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
            and read_param("volumeId", _decode_u64_param)
            and read_param("waterType", _decode_string_param)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type == "CheckFacBuildingState":
        if not (
            read_param("facStateId", _decode_i32_param)
            and read_param("instKey", _decode_string_param)
            and read_param("isInState", _decode_bool_param)
            and read_param("sceneName", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckFactoryBlackBoxState":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("dungeonId", _decode_string_param)
            and read_param("state", _decode_i32_param)
        ):
            return None
        comparer_raw = fields["comparer"]["value"]
        state_raw = fields["state"]["value"]
        if (
            comparer_raw not in _NUMBER_COMPARER_NAMES
            or state_raw not in _FACTORY_BLACK_BOX_STATE_NAMES
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES[comparer_raw]
        fields["stateName"] = _FACTORY_BLACK_BOX_STATE_NAMES[state_raw]
    elif condition_type == "CheckRepairBuilding":
        if not (
            read_param("repairId", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckScriptTaskStateEqual":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
            and read_param("scriptId", _decode_levelscript_ptr_param)
            and read_param("targetValue", _decode_i32_param)
            and read_param("taskKey", _decode_levelscript_task_ptr_param)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type == "OnBuildingPanelOpen":
        if not (
            read_param("buildingId", _decode_string_param)
            and read_param("needWaitAnimation", _decode_bool_param)
        ):
            return None
    elif condition_type == "FacProducePowerReach":
        if not (
            read_param("power", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "FacProducingFormulaCountInScene":
        if not (
            read_param("compareOperator", _decode_i32_param)
            and read_param("progressToCompare", _decode_i32_param)
            and read_param("facFormulaId", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type == "DepotHasItem":
        if not (
            read_param("compareOperator", _decode_i32_param)
            and read_param("itemId", _decode_string_param)
            and read_param("targetItemCount", _decode_i32_param)
        ):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type in (
        "FacBattleBuildingCurEnergy",
        "FacBuildingCountInScene",
        "FacBuildingFluidContainerHasItem",
        "FacBuildingProducingCountInScene",
        "FacStatisticItemGen",
        "FacStatisticItemGenRate",
        "HasItemCount",
    ):
        if not (
            read_param("compareOperator", _decode_i32_param)
            and read_param("progressToCompare", _decode_i32_param)
        ):
            return None
        if condition_type == "FacBattleBuildingCurEnergy":
            if not (
                read_param("instKey", _decode_string_param)
                and read_param("levelId", _decode_string_param)
            ):
                return None
        elif condition_type in (
            "FacBuildingCountInScene",
            "FacBuildingProducingCountInScene",
        ):
            if not (
                read_param("facBuildingId", _decode_string_param)
                and read_param("levelId", _decode_string_param)
            ):
                return None
        elif condition_type in (
            "FacStatisticItemGen",
            "FacStatisticItemGenRate",
        ):
            if not (
                read_param("itemId", _decode_string_param)
                and read_param("levelId", _decode_string_param)
            ):
                return None
        elif condition_type == "FacBuildingFluidContainerHasItem":
            if not (
                read_param("instKey", _decode_string_param)
                and read_param("itemId", _decode_string_param)
                and read_param("levelId", _decode_string_param)
            ):
                return None
        elif not read_param("itemId", _decode_string_param):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type in ("PlayerHasItem", "PlayerHasItemInItemBag"):
        if not (
            read_param("displayInfoBox", _decode_nullable_string_value)
            and read_param("compareOperator", _decode_i32_param)
            and read_param("itemId", _decode_string_param)
            and read_param("targetItemCount", _decode_i32_param)
        ):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type == "CheckInteractiveDestroyed":
        if not (
            read_param("entity", levelscript_params.decode_constant_entity_ptr_param)
            and read_param("mapId", _decode_string_param)
        ):
            return None
    elif condition_type in (
        "CheckLevelScriptPropertyBool",
        "CheckLevelScriptPropertyInt",
    ):
        value_decoder = (
            _decode_bool_param
            if condition_type.endswith("Bool")
            else _decode_i32_param
        )
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("key", _decode_string_param)
            and read_param("mapId", _decode_string_param)
            and read_param("scriptId", _decode_levelscript_ptr_param)
            and read_param("value", value_decoder)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type == "CheckLevelScriptStage":
        if not (
            read_param("compareOperator", _decode_i32_param)
            and read_param("progressToCompare", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
            and read_param("scriptId", _decode_levelscript_ptr_param)
        ):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type == "CheckLevelScriptStageReachMax":
        if not (
            read_param("levelId", _decode_string_param)
            and read_param("scriptId", _decode_levelscript_ptr_param)
        ):
            return None
    elif condition_type == "CheckScanInteractive":
        if not (
            read_param(
                "entity",
                levelscript_params.decode_constant_entity_ptr_param,
            )
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckTerminalReadingDone":
        if not read_param("terminalUniqId", _decode_string_param):
            return None
    elif condition_type == "Conditions.CheckCurrentDungeonBoth":
        if not read_param("dungeonId", _decode_string_param):
            return None
    elif condition_type == "CheckMonsterKilled":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("enemyIds", _decode_entity_ptr_list_param)
            and read_param("sceneId", _decode_string_param)
            and read_param("targetValue", _decode_u64_param)
            and cursor < limit
            and data[cursor] in (0, 1)
        ):
            return None
        fields["needKillAll"] = bool(data[cursor])
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
        cursor += 1
    elif condition_type == "CheckMonsterSpawnerComplete":
        if not (
            read_param("levelId", _decode_string_param)
            and read_param("spawnerId", _decode_u64_param)
        ):
            return None
    elif condition_type in (
        "CheckRepeatableTalkFinish",
        "CheckTalkOptionFinish",
    ):
        if not (
            read_param("dialogId", _decode_string_param)
            and read_param("finishId", _decode_i32_param)
        ):
            return None
    elif condition_type == "CheckScriptMonsterKilled":
        if not (
            read_nullable_param("compareOperator", _decode_i32_param)
            and read_nullable_param("progressToCompare", _decode_i32_param)
            and read_param("sceneId", _decode_string_param)
            and read_param("scriptId", _decode_levelscript_ptr_param)
            and read_param("slotIds", _decode_u32_collection_param)
            and cursor < limit
            and data[cursor] in (0, 1)
        ):
            return None
        comparer_raw = fields["compareOperator"]["value"]
        if (
            comparer_raw is not None
            and comparer_raw not in _NUMBER_COMPARER_NAMES
        ):
            return None
        fields["compareOperatorName"] = (
            _NUMBER_COMPARER_NAMES[comparer_raw]
            if comparer_raw is not None else None
        )
        fields["needAllKill"] = bool(data[cursor])
        cursor += 1
    elif condition_type == "CheckSpaceshipRoomBuilt":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("progressToCompare", _decode_i32_param)
            and read_param("roomType", _decode_i32_param)
        ):
            return None
        comparer_raw = fields["comparer"]["value"]
        room_type_raw = fields["roomType"]["value"]
        if (
            comparer_raw not in _NUMBER_COMPARER_NAMES
            or room_type_raw not in _SPACESHIP_ROOM_TYPE_NAMES
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES[comparer_raw]
        fields["roomTypeName"] = _SPACESHIP_ROOM_TYPE_NAMES[room_type_raw]
    elif condition_type == "CheckPRTSUnlocked":
        if not read_param("prtsIds", _decode_string_collection_param):
            return None
    elif condition_type == "SystemPoiLevel":
        if not (
            read_param("compareLevel", _decode_i32_param)
            and read_param("comparer", _decode_i32_param)
            and read_param("instId", _decode_string_param)
            and read_param("poiType", _decode_i32_param)
        ):
            return None
        comparer_raw = fields["comparer"]["value"]
        poi_type_raw = fields["poiType"]["value"]
        if (
            comparer_raw not in _NUMBER_COMPARER_NAMES
            or poi_type_raw not in _DOMAIN_POI_TYPE_NAMES
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES[comparer_raw]
        fields["poiTypeName"] = _DOMAIN_POI_TYPE_NAMES[poi_type_raw]
    elif condition_type == "InteractiveCheckBool":
        if not (
            read_param("compareValue", _decode_bool_param)
            and read_param(
                "entityId",
                levelscript_params.decode_constant_entity_ptr_param,
            )
            and read_param("key", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "InteractiveCheckInt":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("compareValue", _decode_i32_param)
            and read_param(
                "entityId",
                levelscript_params.decode_constant_entity_ptr_param,
            )
            and read_param("key", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type == "TaskReachDestination":
        if not (
            read_param("areaId", _decode_string_param)
            and read_param("mapId", _decode_string_param)
        ):
            return None
    elif condition_type == "CombineCondition":
        if cursor + 4 > limit:
            return None
        size = struct.unpack_from("<i", data, cursor)[0]
        cursor += 4
        if size < 0 or size > 1024 or cursor + size + 4 > limit:
            return None
        try:
            expression = data[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += size
        subcondition_count = struct.unpack_from("<I", data, cursor)[0]
        cursor += 4
        # Current receiver task maps use only the exact empty serialized list.
        # A non-empty list has no element lengths and needs its own recursive
        # boundary proof before it can be accepted.
        if subcondition_count != 0:
            return None
        fields["conditionEvalString"] = expression
        fields["subConditionCount"] = 0
    else:
        generic = _decode_generic_task_condition_fields(
            data,
            cursor,
            limit,
            field_count=member_count - 4,
        )
        if generic is None:
            return None
        serialized_fields, cursor = generic
        fields["serializedFields"] = serialized_fields
        fields["payloadShape"] = (
            "unique-memorypack-param-boundary-sequence"
        )
        fields["fieldSemanticsStatus"] = (
            "opaque_formatter_fields_no_semantic_name_in_decoder"
        )

    return {
        "type": condition_type,
        "conditionUnionTag": f"0x{union_tag:04x}",
        "conditionUnionTagEncoding": tag_encoding,
        "serializedMemberCount": member_count,
        "conditionOffset": start,
        "conditionOffsetHex": _offset_hex(start),
        "conditionEndOffset": cursor,
        "conditionEndOffsetHex": _offset_hex(cursor),
        **common,
        **fields,
        "nativeMappingId": native_mapping_id,
    }, cursor


def _decode_levelscript_check_mission_state_condition(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one exact GameCondition tag 0x67 / seven-member payload."""
    start = offset
    if offset + 2 > limit or data[offset : offset + 2] != b"\x67\x07":
        return None
    cursor = offset + 2
    if cursor + 4 > limit:
        return None
    scope_mask = struct.unpack_from("<i", data, cursor)[0]
    cursor += 4
    unique_id, next_cursor = _read_compact_string(data, cursor)
    if (
        unique_id is None
        or next_cursor is None
        or next_cursor > limit
        or not re.fullmatch(r"[0-9a-f]{8}", unique_id)
    ):
        return None
    cursor = next_cursor
    if (
        cursor + 2 > limit
        or data[cursor] not in (0, 1)
        or data[cursor + 1] not in (0, 1)
    ):
        return None
    use_current_scope = bool(data[cursor])
    use_graph_scope = bool(data[cursor + 1])
    cursor += 2
    comparer = levelscript_params.decode_constant_i32_param(data, cursor)
    if comparer is None or comparer[1] > limit:
        return None
    comparer_raw, cursor = comparer
    mission = _decode_constant_string_param(data, cursor)
    if mission is None or mission[1] > limit:
        return None
    mission_id, cursor = mission
    target_state = levelscript_params.decode_constant_i32_param(data, cursor)
    if target_state is None or target_state[1] > limit:
        return None
    target_state_raw, cursor = target_state
    if (
        scope_mask < 0
        or scope_mask > 0xFFFF
        or comparer_raw not in _MISSION_STATE_COMPARER_NAMES
        or target_state_raw not in _MISSION_STATE_NAMES
        or not mission_id
        or not re.fullmatch(r"[A-Za-z0-9_#-]+", mission_id)
    ):
        return None
    return {
        "type": "CheckMissionState",
        "conditionUnionTag": "0x0067",
        "serializedMemberCount": 7,
        "conditionOffset": start,
        "conditionOffsetHex": _offset_hex(start),
        "conditionEndOffset": cursor,
        "conditionEndOffsetHex": _offset_hex(cursor),
        "scopeMask": scope_mask,
        "uniqueId": unique_id,
        "useCurrentScope": use_current_scope,
        "useGraphScope": use_graph_scope,
        "comparerRaw": comparer_raw,
        "comparerName": _MISSION_STATE_COMPARER_NAMES[comparer_raw],
        "missionId": mission_id,
        "targetMissionStateRaw": target_state_raw,
        "targetMissionStateName": _MISSION_STATE_NAMES[target_state_raw],
        "nativeMappingId": LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID,
    }, cursor


def _decode_levelscript_single_condition_task_mission_state(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one complete LevelScriptTaskData with one mission condition."""
    start = offset
    task_key, cursor = _read_compact_string(data, offset)
    if (
        task_key is None
        or cursor is None
        or cursor > limit
        or not re.fullmatch(r"[0-9a-f]{8}", task_key)
        or cursor + 6 > limit
        or data[cursor] != 4
        or data[cursor + 1] not in (0, 1)
    ):
        return None
    task_data_member_count = data[cursor]
    can_be_tracked = bool(data[cursor + 1])
    cursor += 2
    condition_count = struct.unpack_from("<I", data, cursor)[0]
    cursor += 4
    if condition_count != 1:
        return None
    condition_key, next_cursor = _read_compact_string(data, cursor)
    if (
        condition_key is None
        or next_cursor is None
        or next_cursor > limit
        or not re.fullmatch(r"[0-9a-f]{8}", condition_key)
    ):
        return None
    cursor = next_cursor
    if cursor >= limit or data[cursor] != 3:
        return None
    task_condition_member_count = data[cursor]
    cursor += 1
    condition_decoded = _decode_levelscript_check_mission_state_condition(
        data,
        cursor,
        limit,
    )
    if condition_decoded is None:
        return None
    condition, cursor = condition_decoded
    if condition["uniqueId"] != condition_key or cursor + 10 > limit:
        return None
    if data[cursor] not in (0, 1):
        return None
    is_main_objective = bool(data[cursor])
    objective_enum = struct.unpack_from("<i", data, cursor + 1)[0]
    cursor += 5
    if data[cursor] not in (0, 1):
        return None
    need_manual_check = bool(data[cursor])
    task_type = struct.unpack_from("<i", data, cursor + 1)[0]
    cursor += 5
    if not (0 <= objective_enum <= 0x100 and 0 <= task_type <= 0x100):
        return None
    return {
        "taskKey": task_key,
        "taskEntryOffset": start,
        "taskEntryOffsetHex": _offset_hex(start),
        "taskEntryEndOffset": cursor,
        "taskEntryEndOffsetHex": _offset_hex(cursor),
        "taskDataMemberCount": task_data_member_count,
        "canBeTracked": can_be_tracked,
        "conditionDictCount": condition_count,
        "conditionKey": condition_key,
        "taskConditionMemberCount": task_condition_member_count,
        "condition": condition,
        "isMainObjective": is_main_objective,
        "objectiveEnum": objective_enum,
        "needManualCheck": need_manual_check,
        "taskType": task_type,
    }, cursor


def _looks_like_levelscript_task_entry_prefix(
    data: bytes,
    offset: int,
    limit: int,
) -> bool:
    task_key, cursor = _read_compact_string(data, offset)
    return bool(
        task_key
        and cursor is not None
        and cursor + 6 <= limit
        and re.fullmatch(r"[0-9a-f]{8}", task_key)
        and data[cursor] == 4
        and data[cursor + 1] in (0, 1)
        and struct.unpack_from("<I", data, cursor + 2)[0] <= 128
    )


def _decode_levelscript_task_entry(
    data: bytes,
    offset: int,
    limit: int,
    diagnostics: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], int] | None:
    """Decode one complete current-build ``LevelScriptTaskData`` envelope."""
    start = offset
    task_key, cursor = _read_compact_string(data, offset)
    if (
        task_key is None
        or cursor is None
        or cursor + 6 > limit
        or not re.fullmatch(r"[0-9a-f]{8}", task_key)
        or data[cursor] != 4
        or data[cursor + 1] not in (0, 1)
    ):
        if diagnostics is not None and not diagnostics:
            diagnostics.append({
                "gate": "taskEntryEnvelope",
                "taskEntryOffset": offset,
                "taskEntryOffsetHex": _offset_hex(offset),
                "limitOffset": limit,
                "limitOffsetHex": _offset_hex(limit),
            })
        return None
    task_data_member_count = data[cursor]
    can_be_tracked = bool(data[cursor + 1])
    condition_count = struct.unpack_from("<I", data, cursor + 2)[0]
    cursor += 6
    if condition_count > 128:
        return None

    conditions: list[dict[str, Any]] = []
    for _ in range(condition_count):
        condition_entry_start = cursor
        condition_key, next_cursor = _read_compact_string(data, cursor)
        if (
            condition_key is None
            or next_cursor is None
            or next_cursor >= limit
            or not re.fullmatch(r"[0-9a-f]{8}", condition_key)
            or data[next_cursor] != 3
        ):
            if diagnostics is not None and not diagnostics:
                diagnostics.append({
                    "gate": "taskConditionEnvelope",
                    "taskKey": task_key,
                    "conditionIndex": len(conditions),
                    "conditionEntryOffset": condition_entry_start,
                    "conditionEntryOffsetHex": _offset_hex(
                        condition_entry_start
                    ),
                })
            return None
        cursor = next_cursor + 1
        if cursor < limit and data[cursor] == 0xFF:
            condition_decoded = ({
                "type": "NullGameCondition",
                "conditionUnionTag": None,
                "conditionUnionTagEncoding": "memorypack-null",
                "serializedMemberCount": None,
                "conditionOffset": cursor,
                "conditionOffsetHex": _offset_hex(cursor),
                "conditionEndOffset": cursor + 1,
                "conditionEndOffsetHex": _offset_hex(cursor + 1),
                "nativeMappingId": LEVELSCRIPT_TASK_CONDITION_MAPPING_ID,
            }, cursor + 1)
        else:
            condition_decoded = _decode_levelscript_task_condition(
                data,
                cursor,
                limit,
            )
        if condition_decoded is None:
            if diagnostics is not None and not diagnostics:
                header = _decode_task_condition_union_header(
                    data,
                    cursor,
                    limit,
                )
                union_tag = header[0] if header is not None else None
                member_count = header[1] if header is not None else None
                expected = (
                    LEVELSCRIPT_TASK_CONDITION_TAGS.get(union_tag)
                    if isinstance(union_tag, int)
                    else None
                )
                diagnostics.append({
                    "gate": (
                        "supportedConditionPayloadLayout"
                        if expected is not None
                        else "supportedConditionUnionTag"
                    ),
                    "taskKey": task_key,
                    "conditionKey": condition_key,
                    "conditionIndex": len(conditions),
                    "conditionOffset": cursor,
                    "conditionOffsetHex": _offset_hex(cursor),
                    "conditionUnionTag": (
                        f"0x{union_tag:04x}"
                        if isinstance(union_tag, int) else None
                    ),
                    "serializedMemberCount": member_count,
                    "expectedConditionType": (
                        expected[0] if expected is not None else None
                    ),
                    "expectedSerializedMemberCount": (
                        expected[1] if expected is not None else None
                    ),
                    "payloadHexPrefix": data[cursor : cursor + 48].hex(" "),
                    "nativeMappingId": LEVELSCRIPT_TASK_CONDITION_MAPPING_ID,
                })
            return None
        condition, cursor = condition_decoded
        if (
            (
                condition.get("type") != "NullGameCondition"
                and condition.get("uniqueId") != condition_key
            )
            or cursor + 5 > limit
            or data[cursor] not in (0, 1)
        ):
            return None
        is_main_objective = bool(data[cursor])
        objective_enum = struct.unpack_from("<i", data, cursor + 1)[0]
        cursor += 5
        if objective_enum < 0 or objective_enum > 0x100:
            return None
        conditions.append({
            "conditionKey": condition_key,
            "conditionEntryOffset": condition_entry_start,
            "conditionEntryOffsetHex": _offset_hex(condition_entry_start),
            "taskConditionMemberCount": 3,
            "isMainObjective": is_main_objective,
            "objectiveEnum": objective_enum,
            "condition": condition,
        })

    if cursor + 5 > limit or data[cursor] not in (0, 1):
        return None
    need_manual_check = bool(data[cursor])
    task_type = struct.unpack_from("<i", data, cursor + 1)[0]
    cursor += 5
    if task_type < 0 or task_type > 0x100:
        return None
    return {
        "taskKey": task_key,
        "taskEntryOffset": start,
        "taskEntryOffsetHex": _offset_hex(start),
        "taskEntryEndOffset": cursor,
        "taskEntryEndOffsetHex": _offset_hex(cursor),
        "taskDataMemberCount": task_data_member_count,
        "canBeTracked": can_be_tracked,
        "conditionDictCount": condition_count,
        "conditions": conditions,
        "needManualCheck": need_manual_check,
        "taskType": task_type,
    }, cursor


def decode_levelscript_task_map_exact(
    data: bytes,
    offset: int,
    count: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """Decode a counted task-map body that must end at an exact owner boundary."""

    if count < 0 or count > 128 or offset < 0 or limit < offset or limit > len(data):
        raise LevelScriptTopLevelFramingError(
            f"invalid task-map bounds: offset={offset} count={count} limit={limit} length={len(data)}"
        )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    cursor = offset
    for index in range(count):
        diagnostics: list[dict[str, Any]] = []
        decoded = _decode_levelscript_task_entry(data, cursor, limit, diagnostics)
        if decoded is None:
            diagnostic = diagnostics[0] if diagnostics else {"gate": "taskEntry"}
            raise LevelScriptTopLevelFramingError(
                f"taskMap[{index}] failed at offset={cursor}: {diagnostic}"
            )
        row, cursor = decoded
        task_key = str(row["taskKey"])
        if task_key in seen:
            raise LevelScriptTopLevelFramingError(
                f"taskMap[{index}] duplicate key {task_key!r}"
            )
        seen.add(task_key)
        rows.append(row)
    if cursor != limit:
        raise LevelScriptTopLevelFramingError(
            f"taskMap did not reach owner boundary: cursor={cursor} limit={limit}"
        )
    return rows, cursor


def decode_levelscript_task_conditions(
    data: bytes,
    script_id: int | str,
    *,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Recover only completely bounded LevelScript task-condition maps.

    The task dictionary begins at an exact validated top-level tail candidate.
    Every declared task and condition must decode in sequence, including its
    IDs and trailing fields.  When a trigger-volume dictionary follows, its
    exact offset is also required to equal the parsed task-map end.  Missing
    later top-level members are allowed only after the declared task count has
    parsed completely.  Results are dependency/evaluation evidence, never
    mission ownership or Story order.
    """
    try:
        numeric_script_id = int(script_id)
    except (TypeError, ValueError):
        return []
    if not data or data[0] not in (26, 27) or len(data) < 8:
        return []

    parsed_hosts: list[dict[str, Any]] = []
    for script_id_offset in _u64_offsets(data, numeric_script_id):
        host = levelscript_top_level_tail.decode_tail_candidate(data, script_id_offset)
        task_count = host.get("taskMapCount")
        task_map_offset = host.get("taskMapOffset")
        if (
            not host.get("startTypeName")
            or host.get("taskMapStatus") != "present"
            or not isinstance(task_count, int)
            or not isinstance(task_map_offset, int)
            or task_count <= 0
            or task_count > 128
        ):
            continue
        cursor = task_map_offset + 4
        trigger_offset = host.get("triggerVolumesOffset")
        limit = (
            int(trigger_offset)
            if isinstance(trigger_offset, int) and trigger_offset > cursor
            else len(data)
        )
        tasks: list[dict[str, Any]] = []
        valid = True
        for _ in range(task_count):
            decoded = _decode_levelscript_task_entry(
                data,
                cursor,
                limit,
                diagnostics,
            )
            if decoded is None:
                valid = False
                break
            task, cursor = decoded
            tasks.append(task)
        if not valid:
            continue
        if isinstance(trigger_offset, int) and cursor != trigger_offset:
            continue
        parsed_hosts.append({
            "scriptId": str(numeric_script_id),
            "levelScriptSerializedMemberCount": data[0],
            "scriptIdOffset": script_id_offset,
            "scriptIdOffsetHex": _offset_hex(script_id_offset),
            "startType": str(host.get("startTypeName") or ""),
            "taskMapOffset": task_map_offset,
            "taskMapOffsetHex": _offset_hex(task_map_offset),
            "taskMapCount": task_count,
            "taskMapEndOffset": cursor,
            "taskMapEndOffsetHex": _offset_hex(cursor),
            "taskMapBoundaryStatus": (
                "exact_trigger_volumes_offset"
                if isinstance(trigger_offset, int)
                else "exact_declared_task_count"
            ),
            "triggerVolumesStatus": str(
                host.get("triggerVolumesStatus") or "missing"
            ),
            "triggerVolumesOffset": trigger_offset,
            "triggerVolumesOffsetHex": _offset_hex(trigger_offset),
            "tasks": tasks,
            "payloadShape": (
                "validated-top-level-task-map-complete-supported-"
                "gameconditions"
            ),
        })

    signatures: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in parsed_hosts:
        signature = (
            row["scriptIdOffset"],
            row["taskMapOffset"],
            row["taskMapEndOffset"],
            tuple(
                (
                    task["taskKey"],
                    tuple(
                        (
                            condition["conditionKey"],
                            condition["condition"]["conditionUnionTag"],
                            condition["condition"]["conditionEndOffset"],
                        )
                        for condition in task["conditions"]
                    ),
                )
                for task in row["tasks"]
            ),
        )
        signatures.setdefault(signature, row)
    return list(signatures.values()) if len(signatures) == 1 else []


def scan_levelscript_task_condition_fragments(
    data: bytes,
    script_id: int | str,
    *,
    condition_types: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Recover individually bounded task conditions from mixed task maps.

    A complete task map cannot be decoded when even one neighboring condition
    uses an unsupported union tag.  This scanner keeps the admission rule
    structural instead of adding per-file exceptions: a supported condition
    must sit inside one uniquely identified top-level task-map interval, have
    an immediately preceding ``TaskCondition`` dictionary key equal to the
    condition's serialized ``uniqueId``, consume its complete typed payload,
    and have the exact trailing objective fields.

    The surrounding task id is deliberately left unresolved because proving
    it would require walking every preceding condition.  These fragments are
    exact condition-consumer evidence, but never task ownership, mission
    ownership, activation, or Story order.
    """
    try:
        numeric_script_id = int(script_id)
    except (TypeError, ValueError):
        return []
    if not data or data[0] not in (26, 27) or len(data) < 8:
        return []

    hosts: dict[tuple[int, int, int], dict[str, Any]] = {}
    for script_id_offset in _u64_offsets(data, numeric_script_id):
        host = levelscript_top_level_tail.decode_tail_candidate(data, script_id_offset)
        task_count = host.get("taskMapCount")
        task_map_offset = host.get("taskMapOffset")
        if (
            not host.get("startTypeName")
            or host.get("taskMapStatus") != "present"
            or not isinstance(task_count, int)
            or not isinstance(task_map_offset, int)
            or task_count <= 0
            or task_count > 128
        ):
            continue
        start = task_map_offset + 4
        trigger_offset = host.get("triggerVolumesOffset")
        end = (
            int(trigger_offset)
            if isinstance(trigger_offset, int) and trigger_offset > start
            else len(data)
        )
        if start >= end:
            continue
        hosts.setdefault((task_map_offset, end, task_count), host)
    if len(hosts) != 1:
        return []

    (task_map_offset, limit, task_count), host = next(iter(hosts.items()))
    fragments: dict[tuple[int, int, str], dict[str, Any]] = {}
    cursor = task_map_offset + 4
    while cursor < limit:
        decoded = _decode_levelscript_task_condition(data, cursor, limit)
        if decoded is None:
            cursor += 1
            continue
        condition, condition_end = decoded
        condition_type = str(condition.get("type") or "")
        condition_key = str(condition.get("uniqueId") or "")
        if (
            (condition_types is not None and condition_type not in condition_types)
            or not re.fullmatch(r"[0-9a-f]{8}", condition_key)
        ):
            cursor += 1
            continue

        key_bytes = condition_key.encode("ascii")
        condition_entry_offset = cursor - 4 - len(key_bytes) - 1
        envelope_valid = (
            condition_entry_offset >= task_map_offset + 4
            and struct.unpack_from("<I", data, condition_entry_offset)[0]
            == len(key_bytes)
            and data[
                condition_entry_offset + 4 : condition_entry_offset + 4 + len(key_bytes)
            ]
            == key_bytes
            and data[cursor - 1] == 3
        )
        if not envelope_valid or condition_end + 5 > limit:
            cursor += 1
            continue
        is_main_objective = data[condition_end]
        objective_enum = struct.unpack_from("<i", data, condition_end + 1)[0]
        if is_main_objective not in (0, 1) or not 0 <= objective_enum <= 0x100:
            cursor += 1
            continue

        signature = (cursor, condition_end, condition_key)
        fragments[signature] = {
            "scriptId": str(numeric_script_id),
            "levelScriptSerializedMemberCount": data[0],
            "startType": str(host.get("startTypeName") or ""),
            "taskMapOffset": task_map_offset,
            "taskMapOffsetHex": _offset_hex(task_map_offset),
            "taskMapCount": task_count,
            "taskMapEndOffset": limit,
            "taskMapEndOffsetHex": _offset_hex(limit),
            "taskMapBoundaryStatus": (
                "exact_trigger_volumes_offset"
                if isinstance(host.get("triggerVolumesOffset"), int)
                else "exact_file_boundary"
            ),
            "taskIdentityStatus": "unresolved_in_mixed_task_map",
            "conditionKey": condition_key,
            "conditionEntryOffset": condition_entry_offset,
            "conditionEntryOffsetHex": _offset_hex(condition_entry_offset),
            "taskConditionMemberCount": 3,
            "isMainObjective": bool(is_main_objective),
            "objectiveEnum": objective_enum,
            "condition": condition,
            "payloadShape": (
                "validated-task-condition-fragment-inside-unique-top-level-task-map"
            ),
        }
        cursor = condition_end + 5
    return sorted(fragments.values(), key=lambda row: row["conditionEntryOffset"])


def decode_levelscript_task_mission_state_dependencies(
    data: bytes,
    script_id: int | str,
) -> list[dict[str, Any]]:
    """Recover structurally complete task-map mission-state conditions.

    This first narrow implementation supports the current-build top-level
    layout whose task map is followed by a null trigger-volume dictionary at
    EOF.  It scans only the uniquely validated task-map interval and accepts
    only complete one-condition task envelopes.  The result is dependency
    evidence, never a Story control path or mission owner.
    """
    try:
        numeric_script_id = int(script_id)
    except (TypeError, ValueError):
        return []
    if (
        not data
        or data[0] not in (26, 27)
        or len(data) < 8
        or data[-4:] != b"\x00\x00\x00\x00"
    ):
        return []
    tail_candidates = [
        levelscript_top_level_tail.decode_tail_candidate(data, offset)
        for offset in _u64_offsets(data, numeric_script_id)
    ]
    task_hosts = [
        candidate
        for candidate in tail_candidates
        if candidate.get("startTypeName")
        and candidate.get("taskMapStatus") == "present"
        and isinstance(candidate.get("taskMapOffset"), int)
        and isinstance(candidate.get("taskMapCount"), int)
        and 0 < int(candidate["taskMapCount"]) <= 128
    ]
    if len(task_hosts) != 1:
        return []
    host = task_hosts[0]
    task_map_offset = int(host["taskMapOffset"])
    task_map_count = int(host["taskMapCount"])
    task_map_start = task_map_offset + 4
    task_map_end = len(data) - 4
    if task_map_start >= task_map_end:
        return []

    candidates: list[dict[str, Any]] = []
    for offset in range(task_map_start, task_map_end):
        decoded = _decode_levelscript_single_condition_task_mission_state(
            data,
            offset,
            task_map_end,
        )
        if decoded is None:
            continue
        row, cursor = decoded
        if cursor != task_map_end and not _looks_like_levelscript_task_entry_prefix(
            data,
            cursor,
            task_map_end,
        ):
            continue
        candidates.append({
            **row,
            "scriptId": str(numeric_script_id),
            "levelScriptSerializedMemberCount": data[0],
            "startType": str(host.get("startTypeName") or ""),
            "taskMapOffset": task_map_offset,
            "taskMapOffsetHex": _offset_hex(task_map_offset),
            "taskMapCount": task_map_count,
            "taskMapEndOffset": task_map_end,
            "taskMapEndOffsetHex": _offset_hex(task_map_end),
            "triggerVolumesStatus": "empty",
            "triggerVolumesOffset": task_map_end,
            "triggerVolumesOffsetHex": _offset_hex(task_map_end),
            "payloadShape": (
                "validated-top-level-task-map-single-check-mission-state-"
                "task-and-null-trigger-volumes-eof"
            ),
        })
    signatures = [
        (
            row["taskKey"],
            row["conditionKey"],
            row["taskEntryOffset"],
        )
        for row in candidates
    ]
    if len(signatures) != len(set(signatures)):
        return []
    return sorted(candidates, key=lambda row: row["taskEntryOffset"])
