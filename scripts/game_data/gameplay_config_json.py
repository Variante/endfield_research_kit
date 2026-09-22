"""Exact named schemas for compact GameplayConfig JSON tables.

These tables are ordinary JSON, but JSON syntax alone does not prove their
field contracts.  This reader names the compact table families whose complete
current shapes and cross-index relationships are understood.
"""

from __future__ import annotations

import json
import math
from typing import Any, Callable


class GameplayConfigJsonDecodeError(ValueError):
    pass


PREFIX = "GameplayConfig/"


def is_compact_gameplay_config_json_path(relative: str) -> bool:
    name = relative.replace("\\", "/")
    return name.startswith(PREFIX) and name.removeprefix(PREFIX) in _DECODERS


def _fail(path: str, expected: Any, actual: Any) -> None:
    raise GameplayConfigJsonDecodeError(
        f"{path}: expected={expected!r} actual={actual!r}"
    )


def _obj(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or tuple(value) != fields:
        _fail(
            path + ".fields",
            fields,
            tuple(value) if isinstance(value, dict) else type(value).__name__,
        )
    return value


def _dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "object", type(value).__name__)
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, "array", type(value).__name__)
    return value


def _type(value: Any, expected: type, path: str) -> None:
    if type(value) is not expected:
        _fail(path, expected.__name__, type(value).__name__)


def _number(value: Any, path: str) -> None:
    # Json.NET writes infinite AnimationCurve tangents as +/-Infinity.  Python's
    # JSON reader accepts those tokens, and they are meaningful curve values.
    if type(value) not in (int, float) or (
        type(value) is float and math.isnan(value)
    ):
        _fail(path, "number (including infinite curve tangent)", value)


def _strings(value: Any, path: str) -> list[str]:
    values = _list(value, path)
    for index, item in enumerate(values):
        _type(item, str, f"{path}[{index}]")
    return values


def _ints(value: Any, path: str) -> list[int]:
    values = _list(value, path)
    for index, item in enumerate(values):
        _type(item, int, f"{path}[{index}]")
    return values


def _vector3(value: Any, path: str) -> None:
    value = _obj(value, ("x", "y", "z"), path)
    for field in value:
        _number(value[field], path + "." + field)


def _curve(value: Any, path: str) -> None:
    fields = (
        "time", "value", "inTangent", "outTangent", "inWeight",
        "outWeight", "weightedMode",
    )
    for index, keyframe in enumerate(_list(value, path)):
        keyframe = _obj(keyframe, fields, f"{path}[{index}]")
        for field in fields[:-1]:
            if field in ("inTangent", "outTangent") and keyframe[field] in (
                "Infinity", "-Infinity"
            ):
                continue
            _number(keyframe[field], f"{path}[{index}].{field}")
        _type(keyframe["weightedMode"], int, f"{path}[{index}].weightedMode")


def _auto_name_global(root: Any, source: str) -> dict[str, Any]:
    fields = (
        "globalVarAutoNameList", "globalVarIntKeyList",
        "globalVarDefaultValueList", "globalVarBelongEntityList",
        "globalVarToEntityPropList",
    )
    root = _obj(root, fields, source)
    validators = (_strings, _ints, _ints, _ints, _strings)
    lengths = []
    for field, validator in zip(fields, validators, strict=True):
        lengths.append(len(validator(root[field], source + "." + field)))
    if len(set(lengths)) != 1:
        _fail(source + ".parallelColumns", "equal lengths", lengths)
    return {"entryCount": lengths[0], "tableKind": "auto_name_global"}


def _auto_name_map(root: Any, source: str) -> dict[str, Any]:
    fields = (
        "mapVarAutoNameList", "mapVarIntKeyList", "mapVarDefaultValueList",
        "mapVarBelongEntityList", "mapVarToEntityPropList",
    )
    root = _obj(root, fields, source)
    columns = [_dict(root[field], source + "." + field) for field in fields]
    key_order = tuple(columns[0])
    for field, column in zip(fields[1:], columns[1:], strict=True):
        if tuple(column) != key_order:
            _fail(source + "." + field + ".keys", key_order, tuple(column))
    validators = (_strings, _ints, _ints, _ints, _strings)
    entries = 0
    for key in key_order:
        lengths = []
        for field, column, validator in zip(fields, columns, validators, strict=True):
            lengths.append(len(validator(column[key], f"{source}.{field}[{key!r}]")))
        if len(set(lengths)) != 1:
            _fail(f"{source}[{key!r}].parallelColumns", "equal lengths", lengths)
        if len(set(columns[1][key])) != len(columns[1][key]):
            _fail(f"{source}.mapVarIntKeyList[{key!r}]", "unique keys", columns[1][key])
        entries += lengths[0]
    return {"entryCount": entries, "mapCount": len(key_order), "tableKind": "auto_name_map"}


def _story_mode(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("forbidItemTypes", "forbidItems"), source)
    item_types = _ints(root["forbidItemTypes"], source + ".forbidItemTypes")
    items = _list(root["forbidItems"], source + ".forbidItems")
    for index, item in enumerate(items):
        item = _obj(item, ("forbidType",), f"{source}.forbidItems[{index}]")
        _type(item["forbidType"], int, f"{source}.forbidItems[{index}].forbidType")
    return {"entryCount": len(item_types) + len(items), "tableKind": "story_mode"}


def _subgame_misc(root: Any, source: str) -> dict[str, Any]:
    fields = (
        "simulationTrainingHotspotTemplateIds", "simulationTrainingLodCapThreshold",
        "worldChallengeEffectDowngradeGameIds",
    )
    root = _obj(root, fields, source)
    a = _strings(root[fields[0]], source + "." + fields[0])
    _type(root[fields[1]], int, source + "." + fields[1])
    b = _strings(root[fields[2]], source + "." + fields[2])
    return {"entryCount": len(a) + len(b), "tableKind": "subgame_misc"}


def _teleport_reason(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("reasonNeedMask",), source)
    rows = _list(root["reasonNeedMask"], source + ".reasonNeedMask")
    reasons: set[int] = set()
    for index, row in enumerate(rows):
        path = f"{source}.reasonNeedMask[{index}]"
        row = _obj(row, ("reason", "delayTime"), path)
        _type(row["reason"], int, path + ".reason")
        _number(row["delayTime"], path + ".delayTime")
        if row["reason"] in reasons:
            _fail(path + ".reason", "unique reason", row["reason"])
        reasons.add(row["reason"])
    return {"entryCount": len(rows), "tableKind": "teleport_reason_mask"}


def _teleport_perform(root: Any, source: str) -> dict[str, Any]:
    root = _dict(root, source)
    fields = ("$type", "performId", "vfxId", "startDuration", "endDuration")
    for key, row in root.items():
        path = f"{source}[{key!r}]"
        row = _obj(row, fields, path)
        if row["$type"] != "Beyond.Gameplay.FullScreenFxTeleportPerformCfg, Gameplay.Beyond":
            _fail(path + ".$type", "FullScreenFxTeleportPerformCfg identity", row["$type"])
        if row["performId"] != key:
            _fail(path + ".performId", key, row["performId"])
        _type(row["vfxId"], str, path + ".vfxId")
        _number(row["startDuration"], path + ".startDuration")
        _number(row["endDuration"], path + ".endDuration")
    return {"entryCount": len(root), "tableKind": "teleport_perform"}


def _condition(value: Any, path: str) -> None:
    value = _dict(value, path)
    identity = value.get("$type")
    if identity == "Beyond.Gameplay.CombinedConditionRuntime, Gameplay.Beyond":
        value = _obj(value, ("$type", "conditionOperator", "reverse", "subConditions"), path)
        _type(value["conditionOperator"], int, path + ".conditionOperator")
        _type(value["reverse"], bool, path + ".reverse")
        for index, child in enumerate(_list(value["subConditions"], path + ".subConditions")):
            _condition(child, f"{path}.subConditions[{index}]")
    elif identity == "Beyond.Gameplay.SimpleConditionCheckPlayerInLevel, Gameplay.Beyond":
        value = _obj(value, ("$type", "checkLevelId"), path)
        _type(value["checkLevelId"], str, path + ".checkLevelId")
    elif identity == "Beyond.Gameplay.SimpleConditionCheckPortableDeviceEquipped, Gameplay.Beyond":
        value = _obj(value, ("$type", "itemId"), path)
        _type(value["itemId"], str, path + ".itemId")
    elif identity == "Beyond.Gameplay.SimpleConditionCheckQuestState, Gameplay.Beyond":
        value = _obj(value, ("$type", "questId", "compareOperator", "compareTarget"), path)
        _type(value["questId"], str, path + ".questId")
        _type(value["compareOperator"], int, path + ".compareOperator")
        _type(value["compareTarget"], int, path + ".compareTarget")
    elif identity == "Beyond.Gameplay.SimpleConditionCheckMissionState, Gameplay.Beyond":
        value = _obj(value, ("$type", "missionId", "compareOperator", "compareTarget"), path)
        _type(value["missionId"], str, path + ".missionId")
        _type(value["compareOperator"], int, path + ".compareOperator")
        _type(value["compareTarget"], int, path + ".compareTarget")
    elif identity == "Beyond.Gameplay.SimpleConditionPlayerInsideFriendShip, Gameplay.Beyond":
        _obj(value, ("$type",), path)
    elif identity == "Beyond.Gameplay.SimpleConditionCheckGlobalVar, Gameplay.Beyond":
        value = _obj(value, ("$type", "globalVarName", "compareOperator", "compareTarget"), path)
        _type(value["globalVarName"], str, path + ".globalVarName")
        _type(value["compareOperator"], int, path + ".compareOperator")
        _type(value["compareTarget"], int, path + ".compareTarget")
    elif identity == "Beyond.Gameplay.SimpleConditionCheckMissionNotPaused, Gameplay.Beyond":
        value = _obj(value, ("$type", "missionId"), path)
        _type(value["missionId"], str, path + ".missionId")
    elif identity == "Beyond.Gameplay.SimpleConditionCheckMapVar, Gameplay.Beyond":
        value = _obj(value, ("$type", "belongMapId", "mapVarName", "compareOperator", "compareTarget"), path)
        _type(value["belongMapId"], str, path + ".belongMapId")
        _type(value["mapVarName"], str, path + ".mapVarName")
        _type(value["compareOperator"], int, path + ".compareOperator")
        _type(value["compareTarget"], int, path + ".compareTarget")
    else:
        _fail(path + ".$type", "known activation condition identity", identity)


def _temp_ability_conditions(root: Any, source: str) -> dict[str, Any]:
    root = _dict(root, source)
    for key, value in root.items():
        _type(key, str, source + ".key")
        _condition(value, f"{source}[{key!r}]")
    return {"entryCount": len(root), "tableKind": "temporary_ability_conditions"}


def _archery_affixes(root: Any, source: str) -> dict[str, Any]:
    root = _dict(root, source)
    rows = 0
    for key, values in root.items():
        _type(key, str, source + ".key")
        for index, row in enumerate(_list(values, f"{source}[{key!r}]")):
            path = f"{source}[{key!r}][{index}]"
            row = _obj(row, ("type", "param", "affectChipIds"), path)
            _type(row["type"], int, path + ".type")
            _number(row["param"], path + ".param")
            _strings(row["affectChipIds"], path + ".affectChipIds")
            rows += 1
    return {"entryCount": rows, "affixSetCount": len(root), "tableKind": "archery_affixes"}


def _mine_teams(root: Any, source: str, *, gas: bool) -> dict[str, Any]:
    root = _dict(root, source)
    fields = ("levelId", "instId", "doodadCoreIds") + (("isGas",) if gas else ())
    rows = 0
    ids: set[str] = set()
    for parent, values in root.items():
        if not parent.isdecimal():
            _fail(source + ".key", "decimal parent ID", parent)
        for index, row in enumerate(_list(values, f"{source}[{parent!r}]")):
            path = f"{source}[{parent!r}][{index}]"
            row = _obj(row, fields, path)
            _type(row["levelId"], str, path + ".levelId")
            _type(row["instId"], str, path + ".instId")
            _ints(row["doodadCoreIds"], path + ".doodadCoreIds")
            if row["instId"] in ids:
                _fail(path + ".instId", "globally unique", row["instId"])
            ids.add(row["instId"])
            if gas:
                _type(row["isGas"], bool, path + ".isGas")
            rows += 1
    return {"entryCount": rows, "parentCount": len(root), "tableKind": "gas_mine_teams" if gas else "mine_teams"}


def _level_short_ids(root: Any, source: str) -> dict[str, Any]:
    root = _dict(root, source)
    total = 0
    for scene, row in root.items():
        path = f"{source}[{scene!r}]"
        row = _obj(row, ("sceneName", "ids", "reverseIds"), path)
        if row["sceneName"] != scene:
            _fail(path + ".sceneName", scene, row["sceneName"])
        ids = _dict(row["ids"], path + ".ids")
        reverse = _dict(row["reverseIds"], path + ".reverseIds")
        for logic_id, short_id in ids.items():
            if not logic_id.isdecimal() or type(short_id) is not int:
                _fail(path + ".ids", "decimal logic ID -> int short ID", (logic_id, short_id))
            if reverse.get(str(short_id)) != int(logic_id):
                _fail(path + ".reverseIds", (str(short_id), int(logic_id)), reverse.get(str(short_id)))
        if len(ids) != len(reverse):
            _fail(path + ".inverseSize", len(ids), len(reverse))
        total += len(ids)
    return {"entryCount": total, "sceneCount": len(root), "tableKind": "level_short_ids"}


def _map_ids(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("mapIds", "mapIdStrToNum", "mapIdNumToStr"), source)
    names = _strings(root["mapIds"], source + ".mapIds")
    forward = _dict(root["mapIdStrToNum"], source + ".mapIdStrToNum")
    reverse = _dict(root["mapIdNumToStr"], source + ".mapIdNumToStr")
    if tuple(forward) != tuple(names):
        _fail(source + ".mapIdStrToNum.keys", tuple(names), tuple(forward))
    for name, number in forward.items():
        _type(number, int, source + f".mapIdStrToNum[{name!r}]")
        if reverse.get(str(number)) != name:
            _fail(source + ".mapIdNumToStr", (str(number), name), reverse.get(str(number)))
    if len(forward) != len(reverse):
        _fail(source + ".inverseSize", len(forward), len(reverse))
    return {"entryCount": len(names), "tableKind": "map_ids"}


def _level_basic_info(root: Any, source: str) -> dict[str, Any]:
    root = _dict(root, source)
    fields = ("id", "idNum", "levelType", "configPath", "mapUI", "regionUI", "facArea", "scope", "domainName")
    numeric_ids: set[int] = set()
    for key, row in root.items():
        path = f"{source}[{key!r}]"
        row = _obj(row, fields, path)
        if row["id"] != key:
            _fail(path + ".id", key, row["id"])
        for field in ("idNum", "levelType", "scope"):
            _type(row[field], int, path + "." + field)
        for field in ("configPath", "mapUI", "regionUI", "facArea", "domainName"):
            _type(row[field], str, path + "." + field)
        if row["idNum"] in numeric_ids:
            _fail(path + ".idNum", "unique", row["idNum"])
        numeric_ids.add(row["idNum"])
    return {"entryCount": len(root), "tableKind": "level_basic_info"}


def _interactive_curves(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("speedVariationCurveDict",), source)
    curves = _dict(root["speedVariationCurveDict"], source + ".speedVariationCurveDict")
    points = 0
    for key, value in curves.items():
        _type(key, str, source + ".speedVariationCurveDict.key")
        _curve(value, f"{source}.speedVariationCurveDict[{key!r}]")
        points += len(value)
    return {"entryCount": len(curves), "keyframeCount": points, "tableKind": "interactive_curves"}


def _model_radius(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("data",), source)
    rows = _dict(root["data"], source + ".data")
    fields = ("modelId", "enableModelBoxSqueeze", "radiusXZ", "modelBoxCenter", "modelBoxSize", "modelBoxYaw")
    for key, row in rows.items():
        path = f"{source}.data[{key!r}]"
        row = _obj(row, fields, path)
        if row["modelId"] != key:
            _fail(path + ".modelId", key, row["modelId"])
        _type(row["enableModelBoxSqueeze"], bool, path + ".enableModelBoxSqueeze")
        _number(row["radiusXZ"], path + ".radiusXZ")
        _vector3(row["modelBoxCenter"], path + ".modelBoxCenter")
        _vector3(row["modelBoxSize"], path + ".modelBoxSize")
        _number(row["modelBoxYaw"], path + ".modelBoxYaw")
    return {"entryCount": len(rows), "tableKind": "model_radius"}


def _air_wall(root: Any, source: str) -> dict[str, Any]:
    fields = ("airWallConfigs", "__AssemblyName__", "__TypeName__")
    root = _obj(root, fields, source)
    identity = (root["__AssemblyName__"], root["__TypeName__"])
    expected = ("Gameplay.Beyond", "Beyond.Gameplay.AirWallRuntimeConfig")
    if identity != expected:
        _fail(source + ".typeIdentity", expected, identity)
    configs = _dict(root["airWallConfigs"], source + ".airWallConfigs")
    for key, row in configs.items():
        row = _obj(row, ("defaultEffectId",), f"{source}.airWallConfigs[{key!r}]")
        _type(row["defaultEffectId"], str, f"{source}.airWallConfigs[{key!r}].defaultEffectId")
    return {"entryCount": len(configs), "tableKind": "air_wall_runtime"}


def _atmospheric_active_switchers(root: Any, source: str) -> dict[str, Any]:
    fields = ("dataTable", "levelId2SwitcherIds", "switchId2GroupIds", "groupId2AtmosphericNpcs", "__AssemblyName__", "__TypeName__")
    root = _obj(root, fields, source)
    identity = (root["__AssemblyName__"], root["__TypeName__"])
    expected = ("Gameplay.Beyond", "Beyond.Gameplay.NpcAtmosphericActiveSwitcherDataTable")
    if identity != expected:
        _fail(source + ".typeIdentity", expected, identity)
    for empty in fields[1:4]:
        value = _dict(root[empty], source + "." + empty)
        if value:
            _fail(source + "." + empty, "empty deferred index", len(value))
    rows = 0
    for level_id, values in _dict(root["dataTable"], source + ".dataTable").items():
        for index, row in enumerate(_list(values, f"{source}.dataTable[{level_id!r}]")):
            path = f"{source}.dataTable[{level_id!r}][{index}]"
            row = _obj(row, ("subDataParentId", "switcherId", "levelId", "groupIds", "groupId2AtmosphericNpcs"), path)
            _type(row["subDataParentId"], int, path + ".subDataParentId")
            _type(row["switcherId"], str, path + ".switcherId")
            if row["levelId"] != level_id:
                _fail(path + ".levelId", level_id, row["levelId"])
            groups = _strings(row["groupIds"], path + ".groupIds")
            mapping = _dict(row["groupId2AtmosphericNpcs"], path + ".groupId2AtmosphericNpcs")
            if len(set(groups)) != len(groups) or set(mapping) != set(groups):
                _fail(path + ".groupId2AtmosphericNpcs.keys", set(groups), set(mapping))
            for group_id, npc_ids in mapping.items():
                _strings(npc_ids, path + f".groupId2AtmosphericNpcs[{group_id!r}]")
            rows += 1
    return {"entryCount": rows, "levelCount": len(root["dataTable"]), "tableKind": "atmospheric_active_switchers"}


def _atmospheric_clusters(root: Any, source: str) -> dict[str, Any]:
    fields = ("dataTable", "npcId2ClusterId", "__AssemblyName__", "__TypeName__")
    root = _obj(root, fields, source)
    identity = (root["__AssemblyName__"], root["__TypeName__"])
    expected = ("Gameplay.Beyond", "Beyond.Gameplay.NpcAtmosphericClusterDataTable")
    if identity != expected:
        _fail(source + ".typeIdentity", expected, identity)
    if _dict(root["npcId2ClusterId"], source + ".npcId2ClusterId"):
        _fail(source + ".npcId2ClusterId", "empty deferred index", "nonempty")
    rows = _dict(root["dataTable"], source + ".dataTable")
    fields_row = ("subDataParentId", "clusterId", "envTalkId", "levelId", "envTalkTriggerDistance", "position", "forceSyncMontage", "npcIds")
    for key, row in rows.items():
        path = f"{source}.dataTable[{key!r}]"
        row = _obj(row, fields_row, path)
        _type(row["subDataParentId"], int, path + ".subDataParentId")
        if row["clusterId"] != key:
            _fail(path + ".clusterId", key, row["clusterId"])
        for field in ("envTalkId", "levelId"):
            _type(row[field], str, path + "." + field)
        _number(row["envTalkTriggerDistance"], path + ".envTalkTriggerDistance")
        _vector3(row["position"], path + ".position")
        _type(row["forceSyncMontage"], bool, path + ".forceSyncMontage")
        _strings(row["npcIds"], path + ".npcIds")
    return {"entryCount": len(rows), "tableKind": "atmospheric_clusters"}


def _atmospheric_switchers(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("level2SwitcherIds", "switcherId2GroupIds", "groupConfigs"), source)
    levels = _dict(root["level2SwitcherIds"], source + ".level2SwitcherIds")
    switchers = _dict(root["switcherId2GroupIds"], source + ".switcherId2GroupIds")
    groups = _dict(root["groupConfigs"], source + ".groupConfigs")
    level_for_switcher: dict[str, str] = {}
    for level_id, ids in levels.items():
        for switcher_id in _strings(ids, f"{source}.level2SwitcherIds[{level_id!r}]"):
            if switcher_id in level_for_switcher:
                _fail(source + ".level2SwitcherIds", "unique switcher ownership", switcher_id)
            level_for_switcher[switcher_id] = level_id
    if set(level_for_switcher) != set(switchers):
        _fail(source + ".switcherId2GroupIds.keys", set(level_for_switcher), set(switchers))
    fields = ("switcherId", "levelId", "mapId", "groupId", "switcherType", "condition")
    bound_fields = ("switcherId", "levelId", "mapId", "groupId", "bindMissionId", "switcherType", "condition")
    for switcher_id, group_ids in switchers.items():
        for group_id in _strings(group_ids, f"{source}.switcherId2GroupIds[{switcher_id!r}]"):
            row = groups.get(group_id)
            path = f"{source}.groupConfigs[{group_id!r}]"
            if not isinstance(row, dict) or tuple(row) not in (fields, bound_fields):
                _fail(path + ".fields", (fields, bound_fields), tuple(row) if isinstance(row, dict) else type(row).__name__)
            if row["switcherId"] != switcher_id or row["groupId"] != group_id:
                _fail(path + ".identity", (switcher_id, group_id), (row["switcherId"], row["groupId"]))
            if row["levelId"] != level_for_switcher[switcher_id]:
                _fail(path + ".levelId", level_for_switcher[switcher_id], row["levelId"])
            _type(row["mapId"], str, path + ".mapId")
            if "bindMissionId" in row:
                _type(row["bindMissionId"], str, path + ".bindMissionId")
            _type(row["switcherType"], int, path + ".switcherType")
            _condition(row["condition"], path + ".condition")
    referenced = {group for ids in switchers.values() for group in ids}
    if referenced != set(groups):
        _fail(source + ".groupConfigs.keys", referenced, set(groups))
    return {"entryCount": len(groups), "switcherCount": len(switchers), "levelCount": len(levels), "tableKind": "atmospheric_switchers"}


def _gameplay_tags(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("predefinedTags", "predefinedQuery", "tagName2Immune"), source)
    tags = _dict(root["predefinedTags"], source + ".predefinedTags")
    for name, row in tags.items():
        row = _obj(row, ("tagId",), f"{source}.predefinedTags[{name!r}]")
        _type(row["tagId"], int, f"{source}.predefinedTags[{name!r}].tagId")
    queries = _dict(root["predefinedQuery"], source + ".predefinedQuery")
    for name, row in queries.items():
        path = f"{source}.predefinedQuery[{name!r}]"
        row = _obj(row, ("queryType", "tags"), path)
        _type(row["queryType"], int, path + ".queryType")
        for index, tag in enumerate(_list(row["tags"], path + ".tags")):
            tag = _obj(tag, ("tagId",), f"{path}.tags[{index}]")
            _type(tag["tagId"], int, f"{path}.tags[{index}].tagId")
    immune = _dict(root["tagName2Immune"], source + ".tagName2Immune")
    for name, row in immune.items():
        path = f"{source}.tagName2Immune[{name!r}]"
        row = _obj(row, ("predefinedTag",), path)
        for index, tag in enumerate(_list(row["predefinedTag"], path + ".predefinedTag")):
            tag = _obj(tag, ("tagId",), f"{path}.predefinedTag[{index}]")
            _type(tag["tagId"], int, f"{path}.predefinedTag[{index}].tagId")
    return {"entryCount": len(tags) + len(queries) + len(immune), "tableKind": "gameplay_tags"}


def _levelscript_teleports(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("teleportValidationDatas",), source)
    rows = _dict(root["teleportValidationDatas"], source + ".teleportValidationDatas")
    fields = ("subDataParentId", "id", "teleportReason", "sceneId", "position", "rotationEuler", "uiTypeOut", "deviation", "keepAnim", "keepCam")
    for key, row in rows.items():
        path = f"{source}.teleportValidationDatas[{key!r}]"
        row = _obj(row, fields, path)
        if row["id"] != key:
            _fail(path + ".id", key, row["id"])
        for field in ("subDataParentId", "teleportReason", "uiTypeOut"):
            _type(row[field], int, path + "." + field)
        _type(row["sceneId"], str, path + ".sceneId")
        _vector3(row["position"], path + ".position")
        _vector3(row["rotationEuler"], path + ".rotationEuler")
        _number(row["deviation"], path + ".deviation")
        for field in ("keepAnim", "keepCam"):
            _type(row[field], bool, path + "." + field)
    return {"entryCount": len(rows), "tableKind": "levelscript_teleports"}


def _map_brief_info(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("mapTable",), source)
    maps = _dict(root["mapTable"], source + ".mapTable")
    sublevels = 0
    for map_id, map_row in maps.items():
        if not map_id.isdecimal():
            _fail(source + ".mapTable.key", "decimal map ID", map_id)
        map_row = _obj(map_row, ("subLevelTable",), f"{source}.mapTable[{map_id!r}]")
        for sub_id, row in _dict(map_row["subLevelTable"], source + f".mapTable[{map_id!r}].subLevelTable").items():
            path = f"{source}.mapTable[{map_id!r}].subLevelTable[{sub_id!r}]"
            row = _obj(row, ("subDataParentId", "enemyIdSet"), path)
            _type(row["subDataParentId"], int, path + ".subDataParentId")
            if str(row["subDataParentId"]) != sub_id:
                _fail(path + ".subDataParentId", int(sub_id), row["subDataParentId"])
            _strings(row["enemyIdSet"], path + ".enemyIdSet")
            sublevels += 1
    return {"entryCount": sublevels, "mapCount": len(maps), "tableKind": "map_brief_info"}


def _multi_trigger(root: Any, source: str) -> dict[str, Any]:
    root = _dict(root, source)
    trigger_fields = ("triggerId", "shape", "center", "radius", "size", "polyLineHeight", "isImportant", "interactiveDirectionCheck", "checkOffset", "checkRadius", "checkHeight", "checkAngle", "playerDirectionCheck", "inTriggerVolumePerformance")
    count = 0
    for parent, rows in root.items():
        if not parent.isdecimal():
            _fail(source + ".key", "decimal parent ID", parent)
        for index, row in enumerate(_list(rows, f"{source}[{parent!r}]")):
            path = f"{source}[{parent!r}][{index}]"
            row = _obj(row, ("serverId", "triggers"), path)
            _type(row["serverId"], int, path + ".serverId")
            for child_index, trigger in enumerate(_list(row["triggers"], path + ".triggers")):
                child = f"{path}.triggers[{child_index}]"
                trigger = _obj(trigger, trigger_fields, child)
                for field in ("triggerId", "shape"):
                    _type(trigger[field], int, child + "." + field)
                for field in ("center", "size", "checkOffset"):
                    _vector3(trigger[field], child + "." + field)
                for field in ("radius", "polyLineHeight", "checkRadius", "checkHeight", "checkAngle"):
                    _number(trigger[field], child + "." + field)
                for field in ("isImportant", "interactiveDirectionCheck", "playerDirectionCheck", "inTriggerVolumePerformance"):
                    _type(trigger[field], bool, child + "." + field)
                count += 1
    return {"entryCount": count, "parentCount": len(root), "tableKind": "multi_trigger"}


def _prts_bindings(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("entries", "__AssemblyName__", "__TypeName__"), source)
    identity = (root["__AssemblyName__"], root["__TypeName__"])
    expected = ("Gameplay.Beyond", "Beyond.Gameplay.PrtsLevelBindingTable")
    if identity != expected:
        _fail(source + ".typeIdentity", expected, identity)
    entries = _list(root["entries"], source + ".entries")
    ids: set[str] = set()
    for index, row in enumerate(entries):
        path = f"{source}.entries[{index}]"
        row = _obj(row, ("prtsId", "levelId"), path)
        for field in row:
            _type(row[field], str, path + "." + field)
        if row["prtsId"] in ids:
            _fail(path + ".prtsId", "unique", row["prtsId"])
        ids.add(row["prtsId"])
    return {"entryCount": len(entries), "tableKind": "prts_level_bindings"}


def _subgame_entity_overrides(root: Any, source: str) -> dict[str, Any]:
    root = _dict(root, source)
    fields = ("$type", "overrideAIConfig", "bornEffectKey", "bornDelay")
    for key, row in root.items():
        path = f"{source}[{key!r}]"
        row = _obj(row, fields, path)
        if row["$type"] != "Beyond.Gameplay.SubGameEnemyOverride, Gameplay.Beyond":
            _fail(path + ".$type", "SubGameEnemyOverride identity", row["$type"])
        for field in ("overrideAIConfig", "bornEffectKey"):
            _type(row[field], str, path + "." + field)
        _number(row["bornDelay"], path + ".bornDelay")
    return {"entryCount": len(root), "tableKind": "subgame_entity_overrides"}


def _tag(value: Any, path: str) -> None:
    value = _obj(value, ("tagId",), path)
    _type(value["tagId"], int, path + ".tagId")


def _localized_key(value: Any, path: str) -> None:
    value = _obj(value, ("key",), path)
    _type(value["key"], str, path + ".key")


def _model_table(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("data", "extraData_interactive"), source)
    rows = _dict(root["data"], source + ".data")
    base = ("modelId", "path", "type", "scaleFactor", "hasModelViewData", "usePersistentPool")
    ecs = ("modelId", "path", "type", "scaleFactor", "hasModelViewData", "ecsModelPath", "usePersistentPool")
    dependent = ("modelId", "path", "type", "scaleFactor", "hasModelViewData", "dependModelViewDataId", "usePersistentPool")
    for key, row in rows.items():
        path = f"{source}.data[{key!r}]"
        if not isinstance(row, dict) or tuple(row) not in (base, ecs, dependent):
            _fail(path + ".fields", (base, ecs, dependent), tuple(row) if isinstance(row, dict) else type(row).__name__)
        if row["modelId"] != key:
            _fail(path + ".modelId", key, row["modelId"])
        _type(row["path"], str, path + ".path")
        _type(row["type"], int, path + ".type")
        _number(row["scaleFactor"], path + ".scaleFactor")
        _type(row["hasModelViewData"], bool, path + ".hasModelViewData")
        _type(row["usePersistentPool"], bool, path + ".usePersistentPool")
        for field in ("ecsModelPath", "dependModelViewDataId"):
            if field in row:
                _type(row[field], str, path + "." + field)
    extras = _dict(root["extraData_interactive"], source + ".extraData_interactive")
    fields = ("shape", "center", "radius", "height", "size", "obstacleType", "hasMultiLevel", "dynamicUpdateRVO", "rvoConcernValue", "collisionShapeDatas", "collisionType", "gameplayLockViewConfig")
    for key, row in extras.items():
        path = f"{source}.extraData_interactive[{key!r}]"
        row = _obj(row, fields, path)
        for field in ("shape", "obstacleType", "rvoConcernValue", "collisionType"):
            _type(row[field], int, path + "." + field)
        for field in ("center", "size"):
            _vector3(row[field], path + "." + field)
        for field in ("radius", "height"):
            _number(row[field], path + "." + field)
        for field in ("hasMultiLevel", "dynamicUpdateRVO"):
            _type(row[field], bool, path + "." + field)
        collision_shapes = _list(row["collisionShapeDatas"], path + ".collisionShapeDatas")
        if collision_shapes:
            _fail(path + ".collisionShapeDatas", "empty current shape override list", len(collision_shapes))
        lock = _dict(row["gameplayLockViewConfig"], path + ".gameplayLockViewConfig")
        if lock:
            lock = _obj(lock, ("enemyLock",), path + ".gameplayLockViewConfig")
            enemy = _obj(lock["enemyLock"], ("modelNodeName", "mountOffset", "viewConfigId"), path + ".gameplayLockViewConfig.enemyLock")
            _type(enemy["modelNodeName"], str, path + ".gameplayLockViewConfig.enemyLock.modelNodeName")
            _vector3(enemy["mountOffset"], path + ".gameplayLockViewConfig.enemyLock.mountOffset")
            _type(enemy["viewConfigId"], str, path + ".gameplayLockViewConfig.enemyLock.viewConfigId")
    return {"entryCount": len(rows), "interactiveExtraCount": len(extras), "tableKind": "model_table"}


def _npc_proxy_extra(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("data", "proxyInfoData", "proxyNumId2Str", "npcId2EnitiyData"), source)
    data = _dict(root["data"], source + ".data")
    infos = _dict(root["proxyInfoData"], source + ".proxyInfoData")
    numbers = _dict(root["proxyNumId2Str"], source + ".proxyNumId2Str")
    entities = _dict(root["npcId2EnitiyData"], source + ".npcId2EnitiyData")
    if set(data) != set(infos):
        _fail(source + ".proxyInfoData.keys", set(data), set(infos))
    if set(numbers.values()) != set(data) or len(numbers) != len(data):
        _fail(source + ".proxyNumId2Str", "bijection onto proxy IDs", len(numbers))
    variants = 0
    for proxy_id, values in data.items():
        for index, row in enumerate(_list(values, f"{source}.data[{proxy_id!r}]")):
            path = f"{source}.data[{proxy_id!r}][{index}]"
            base = ("addDialogExOption", "envTalkData", "dialogExOptionData", "dialogId")
            with_mission = base + ("missionId",)
            if not isinstance(row, dict) or tuple(row) not in (base, with_mission):
                _fail(path + ".fields", (base, with_mission), tuple(row) if isinstance(row, dict) else type(row).__name__)
            _type(row["addDialogExOption"], bool, path + ".addDialogExOption")
            env = _dict(row["envTalkData"], path + ".envTalkData")
            if tuple(env) == ("envTalkOverrideNpc",):
                _type(env["envTalkOverrideNpc"], bool, path + ".envTalkData.envTalkOverrideNpc")
            else:
                env = _obj(env, ("envTalkIds", "envTalkOdd", "envTalkOverrideNpc"), path + ".envTalkData")
                ids = _strings(env["envTalkIds"], path + ".envTalkData.envTalkIds")
                odds = _ints(env["envTalkOdd"], path + ".envTalkData.envTalkOdd")
                if odds and len(ids) != len(odds):
                    _fail(path + ".envTalkData.parallelLists", "empty defaults or one weight per ID", (len(ids), len(odds)))
                _type(env["envTalkOverrideNpc"], bool, path + ".envTalkData.envTalkOverrideNpc")
            options = _list(row["dialogExOptionData"], path + ".dialogExOptionData")
            if options:
                _fail(path + ".dialogExOptionData", "empty current option list", len(options))
            _type(row["dialogId"], str, path + ".dialogId")
            if "missionId" in row:
                _type(row["missionId"], str, path + ".missionId")
            variants += 1
    for key, row in infos.items():
        path = f"{source}.proxyInfoData[{key!r}]"
        row = _obj(row, ("npcProxyType", "npcId", "npcNameId", "mapId"), path)
        _type(row["npcProxyType"], int, path + ".npcProxyType")
        for field in ("npcId", "npcNameId", "mapId"):
            _type(row[field], str, path + "." + field)
    for key, value in numbers.items():
        if not key.isdecimal() or type(value) is not str:
            _fail(source + ".proxyNumId2Str", "decimal ID -> proxy string", (key, value))
    fields = ("npcNameId", "npcEntityId", "headIcon", "interactRangeType", "enableMagicaCloth", "enableMorph")
    for key, row in entities.items():
        path = f"{source}.npcId2EnitiyData[{key!r}]"
        row = _obj(row, fields, path)
        if row["npcEntityId"] != key:
            _fail(path + ".npcEntityId", key, row["npcEntityId"])
        for field in ("npcNameId", "headIcon"):
            _type(row[field], str, path + "." + field)
        _type(row["interactRangeType"], int, path + ".interactRangeType")
        for field in ("enableMagicaCloth", "enableMorph"):
            _type(row[field], bool, path + "." + field)
    return {"entryCount": len(data), "variantCount": variants, "entityCount": len(entities), "tableKind": "npc_proxy_extra"}


_NPC_PROXY_FIELDS = (
    "subDataParentId", "levelLogicId", "entityType", "createState", "position", "rotation", "scale", "forceLoad", "aoiRadiusType", "overrideSendDieEvent", "sendDieEvent", "keepCrossMap", "npcGroupId", "type", "doPatrol", "defaultActivePatrol", "patrolCfgType", "initPatrolIndex", "patrolId_New", "defaultMontage", "overrideMontageState", "montageState", "autoPreloadMontages", "preloadMontages", "defaultMontageMaskType", "collisionEnable", "overrideInteractRange", "interactRangeType", "disableEmotion", "defaultEmotion", "defaultFacialAnim", "lookAt", "enableDialogLookAtCapability", "doStim", "stimulateKey", "atmosphereStimulateCanMove", "isOverriderBlur", "needBlurCheck", "blurPriority", "confrontAnim", "battleAnim", "idleBreakTags", "overrideConfrontRot", "needConfrontRot", "overrideBattleRot", "needBattleRot", "ignoreBattleReturn", "hideHeadLabel", "hideHeadName", "aiCfg", "belongStoryZoneId", "ifOverrideNpcName", "overrideNpcNameId", "ifOverrideTitle", "overrideNpcTitleId", "ifOverrideFaction", "overrideNpcFactionId", "envTalkIds", "envTalkOdd", "hitData", "notifyInteractEvent", "controlByLevelScript", "overrideDefaultInteractText", "overrideDefaultInteractIcon", "defaultInteractText", "interactionIcon", "envTalkTriggerDistance", "envTalkOverrideNpc", "disableDowngrade", "enableMorph", "enableCloth", "overrideSpIdleConfig", "enableDownGradeSpIdle", "normalIdle2SpidleTime", "spIdle2normalIdleTime", "spIdleRandomWaitTimeMin", "spIdleRandomWaitTimeMax", "npcPatrolGroupId", "battleDataOverride", "linkedChairId", "proxyId", "levelId", "overrideLabel", "hideBubble", "clusterId", "hidePopupExpression", "ifOverrideHeadIcon", "overrideHeadIcon", "needWayPoint", "overrideTemplateAI", "overrideAbilitySo", "lazyDestroy", "lazyDestroyEnvTalkData", "lazyDestroyOverrideDialogId", "lazyDestroyStartPatrol", "lazyDestroyPatrolId", "overrideTemplateAi", "overrideGamePlayData", "overrideAudio", "overrideInitAudioId",
)


def _npc_proxy_table(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("dataTable",), source)
    rows = _dict(root["dataTable"], source + ".dataTable")
    int_fields = {"subDataParentId", "levelLogicId", "entityType", "createState", "aoiRadiusType", "type", "patrolCfgType", "initPatrolIndex", "patrolId_New", "montageState", "defaultMontageMaskType", "interactRangeType", "blurPriority", "belongStoryZoneId", "npcPatrolGroupId", "linkedChairId", "lazyDestroyPatrolId"}
    float_fields = {"envTalkTriggerDistance", "normalIdle2SpidleTime", "spIdle2normalIdleTime", "spIdleRandomWaitTimeMin", "spIdleRandomWaitTimeMax"}
    str_fields = {"npcGroupId", "stimulateKey", "aiCfg", "interactionIcon", "proxyId", "levelId", "clusterId", "overrideHeadIcon", "overrideAbilitySo", "lazyDestroyOverrideDialogId"}
    structured = {"position", "rotation", "scale", "defaultMontage", "preloadMontages", "defaultEmotion", "defaultFacialAnim", "confrontAnim", "battleAnim", "idleBreakTags", "overrideNpcNameId", "overrideNpcTitleId", "overrideNpcFactionId", "envTalkIds", "envTalkOdd", "hitData", "defaultInteractText", "lazyDestroyEnvTalkData", "overrideInitAudioId"}
    bool_fields = set(_NPC_PROXY_FIELDS) - int_fields - float_fields - str_fields - structured
    for key, row in rows.items():
        path = f"{source}.dataTable[{key!r}]"
        row = _obj(row, _NPC_PROXY_FIELDS, path)
        if row["proxyId"] != key:
            _fail(path + ".proxyId", key, row["proxyId"])
        for field in int_fields:
            _type(row[field], int, path + "." + field)
        for field in float_fields:
            _number(row[field], path + "." + field)
        for field in str_fields:
            _type(row[field], str, path + "." + field)
        for field in bool_fields:
            _type(row[field], bool, path + "." + field)
        for field in ("position", "rotation", "scale"):
            _vector3(row[field], path + "." + field)
        for field in ("defaultMontage", "defaultEmotion", "defaultFacialAnim", "confrontAnim", "battleAnim"):
            _tag(row[field], path + "." + field)
        for index, tag in enumerate(_list(row["preloadMontages"], path + ".preloadMontages")):
            _tag(tag, f"{path}.preloadMontages[{index}]")
        if _list(row["idleBreakTags"], path + ".idleBreakTags"):
            _fail(path + ".idleBreakTags", "empty current tag list", row["idleBreakTags"])
        for field in ("overrideNpcNameId", "overrideNpcTitleId", "overrideNpcFactionId", "defaultInteractText"):
            _localized_key(row[field], path + "." + field)
        env_ids = _strings(row["envTalkIds"], path + ".envTalkIds")
        env_odds = _ints(row["envTalkOdd"], path + ".envTalkOdd")
        if len(env_ids) != len(env_odds):
            _fail(path + ".envTalkParallel", len(env_ids), len(env_odds))
        hit = _obj(row["hitData"], ("canBeHit", "shape", "center", "extent", "height", "direction", "radius", "hitEffect"), path + ".hitData")
        _type(hit["canBeHit"], bool, path + ".hitData.canBeHit")
        for field in ("shape", "direction"):
            _type(hit[field], int, path + ".hitData." + field)
        for field in ("center", "extent"):
            _vector3(hit[field], path + ".hitData." + field)
        for field in ("height", "radius"):
            _number(hit[field], path + ".hitData." + field)
        _type(hit["hitEffect"], str, path + ".hitData.hitEffect")
        lazy = _obj(row["lazyDestroyEnvTalkData"], ("envTalkIds", "envTalkOdd", "envTalkOverrideNpc"), path + ".lazyDestroyEnvTalkData")
        lazy_ids = _strings(lazy["envTalkIds"], path + ".lazyDestroyEnvTalkData.envTalkIds")
        lazy_odds = _ints(lazy["envTalkOdd"], path + ".lazyDestroyEnvTalkData.envTalkOdd")
        if len(lazy_ids) != len(lazy_odds):
            _fail(path + ".lazyDestroyEnvTalkData.parallel", len(lazy_ids), len(lazy_odds))
        _type(lazy["envTalkOverrideNpc"], bool, path + ".lazyDestroyEnvTalkData.envTalkOverrideNpc")
        audio = _obj(row["overrideInitAudioId"], ("_id",), path + ".overrideInitAudioId")
        _type(audio["_id"], int, path + ".overrideInitAudioId._id")
    return {"entryCount": len(rows), "tableKind": "npc_proxy_table"}


def _world_entity_brief(value: Any, path: str, *, detail_optional: bool) -> None:
    full = ("entityType", "detailId", "position", "rotation")
    short = ("entityType", "position", "rotation")
    if not isinstance(value, dict) or tuple(value) not in ((full, short) if detail_optional else (full,)):
        _fail(path + ".fields", (full, short) if detail_optional else full, tuple(value) if isinstance(value, dict) else type(value).__name__)
    _type(value["entityType"], int, path + ".entityType")
    if "detailId" in value:
        _type(value["detailId"], str, path + ".detailId")
    _vector3(value["position"], path + ".position")
    _vector3(value["rotation"], path + ".rotation")


def _world_entity_registry(root: Any, source: str) -> dict[str, Any]:
    fields = ("worldEntityBriefInfos", "m_scriptEntityIdList", "m_scriptEntityBriefInfo", "worldEntityConfigInfos", "m_npcIdToLogicIdLut", "npcProxyBriefInfos")
    root = _obj(root, fields, source)
    briefs = _dict(root["worldEntityBriefInfos"], source + ".worldEntityBriefInfos")
    for key, row in briefs.items():
        if not key.isdecimal():
            _fail(source + ".worldEntityBriefInfos.key", "decimal entity ID", key)
        _world_entity_brief(row, f"{source}.worldEntityBriefInfos[{key!r}]", detail_optional=True)
    ids = _list(root["m_scriptEntityIdList"], source + ".m_scriptEntityIdList")
    script_briefs = _list(root["m_scriptEntityBriefInfo"], source + ".m_scriptEntityBriefInfo")
    if len(ids) != len(script_briefs):
        _fail(source + ".scriptEntityParallel", len(ids), len(script_briefs))
    seen: set[tuple[int, int]] = set()
    for index, (identity, brief) in enumerate(zip(ids, script_briefs, strict=True)):
        path = f"{source}.m_scriptEntityIdList[{index}]"
        identity = _obj(identity, ("scriptIdGlobal", "slotId"), path)
        pair = (identity["scriptIdGlobal"], identity["slotId"])
        if type(pair[0]) is not int or type(pair[1]) is not int or pair in seen:
            _fail(path, "unique int script/slot pair", pair)
        seen.add(pair)
        _world_entity_brief(brief, f"{source}.m_scriptEntityBriefInfo[{index}]", detail_optional=False)
    configs = _dict(root["worldEntityConfigInfos"], source + ".worldEntityConfigInfos")
    if not set(configs).issubset(briefs):
        _fail(source + ".worldEntityConfigInfos.keys", "subset of world entities", sorted(set(configs) - set(briefs))[:5])
    for key, row in configs.items():
        path = f"{source}.worldEntityConfigInfos[{key!r}]"
        row = _obj(row, ("propertyList",), path)
        for index, prop in enumerate(_list(row["propertyList"], path + ".propertyList")):
            ppath = f"{path}.propertyList[{index}]"
            prop = _obj(prop, ("key", "value"), ppath)
            _type(prop["key"], str, ppath + ".key")
            value = _obj(prop["value"], ("type", "valueArray"), ppath + ".value")
            _type(value["type"], int, ppath + ".value.type")
            for bit_index, bit in enumerate(_list(value["valueArray"], ppath + ".value.valueArray")):
                bit = _obj(bit, ("valueBit64",), f"{ppath}.value.valueArray[{bit_index}]")
                _type(bit["valueBit64"], int, f"{ppath}.value.valueArray[{bit_index}].valueBit64")
    if _dict(root["m_npcIdToLogicIdLut"], source + ".m_npcIdToLogicIdLut"):
        _fail(source + ".m_npcIdToLogicIdLut", "empty deferred index", "nonempty")
    proxies = _dict(root["npcProxyBriefInfos"], source + ".npcProxyBriefInfos")
    for key, row in proxies.items():
        path = f"{source}.npcProxyBriefInfos[{key!r}]"
        row = _obj(row, ("proxyId", "segmentIdGlobal", "position"), path)
        _type(row["proxyId"], str, path + ".proxyId")
        _type(row["segmentIdGlobal"], int, path + ".segmentIdGlobal")
        if str(row["segmentIdGlobal"]) != key:
            _fail(path + ".segmentIdGlobal", int(key), row["segmentIdGlobal"])
        _vector3(row["position"], path + ".position")
    return {"entryCount": len(briefs), "scriptEntityCount": len(ids), "npcProxyCount": len(proxies), "tableKind": "world_entity_registry"}


def _focus_modes(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("dataTable",), source)
    rows = _dict(root["dataTable"], source + ".dataTable")
    shapes = (
        ("subDataParentId", "id", "missionId", "presetTeamId", "radioIdInteractLocked", "customEnterFocusModeFadeOut", "skipEnterConfirm", "enterFadeMaskType", "airWallList", "npcHideMask"),
        ("subDataParentId", "id", "missionId", "presetTeamId", "radioIdInteractLocked", "customEnterFocusModeFadeOut", "skipEnterConfirm", "enterFadeMaskType", "airWallList", "worldEntityWhitelist", "npcHideMask"),
        ("subDataParentId", "id", "missionId", "presetTeamId", "customEnterFocusModeFadeOut", "skipEnterConfirm", "enterFadeMaskType", "worldEntityWhitelist", "npcHideMask"),
    )
    for key, row in rows.items():
        path = f"{source}.dataTable[{key!r}]"
        if not isinstance(row, dict) or tuple(row) not in shapes:
            _fail(path + ".fields", shapes, tuple(row) if isinstance(row, dict) else type(row).__name__)
        if row["id"] != key:
            _fail(path + ".id", key, row["id"])
        for field in ("subDataParentId", "enterFadeMaskType", "npcHideMask"):
            _type(row[field], int, path + "." + field)
        for field in ("missionId", "presetTeamId", "radioIdInteractLocked"):
            if field in row:
                _type(row[field], str, path + "." + field)
        for field in ("customEnterFocusModeFadeOut", "skipEnterConfirm"):
            _type(row[field], bool, path + "." + field)
        for field in ("airWallList", "worldEntityWhitelist"):
            if field in row:
                _ints(row[field], path + "." + field)
    return {"entryCount": len(rows), "tableKind": "focus_modes"}


def _kickable_config(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("kickableConfigDict",), source)
    rows = _dict(root["kickableConfigDict"], source + ".kickableConfigDict")
    fields = ("baseKickForce", "kickPitchAngle", "kickCoolDown", "charSpeedToForceScale", "firstTouchDampingScale", "charSpeedToFacingScale", "kickHeightLimit", "wallCheckDistance", "dashTag", "dashForceScale", "dashFacingScale", "dashTouchDampingScale", "clickKickForce", "clickKickPitchAngle", "clickKickPitchAngleInsideSpawner", "enablePrediction", "predictionSegmentCount", "predictionLength", "predictionSmoothStartDistance", "predictionMinAngularSpeed", "predictionMaxAngularSpeed", "extraGravityScale", "speedToExitAudioList", "outOfRangeToast", "squadDitherRadius", "squadDitherAlpha", "pinnedDitherAlpha", "waterGunHitForce", "waterGunDistanceToForceScale", "useHitPoint", "bombHitForce", "damageBuffId", "damageBuffRadius", "damageBuffSpeedThreshold", "pipelineRotateSpeed", "ballDrag")
    structured = {"charSpeedToForceScale", "charSpeedToFacingScale", "dashTag", "speedToExitAudioList", "outOfRangeToast", "waterGunDistanceToForceScale"}
    ints = {"predictionSegmentCount", "predictionLength"}
    booleans = {"enablePrediction", "useHitPoint"}
    strings = {"damageBuffId"}
    numbers = set(fields) - structured - ints - booleans - strings
    for key, row in rows.items():
        path = f"{source}.kickableConfigDict[{key!r}]"
        row = _obj(row, fields, path)
        for field in numbers:
            _number(row[field], path + "." + field)
        for field in ints:
            _type(row[field], int, path + "." + field)
        for field in booleans:
            _type(row[field], bool, path + "." + field)
        _type(row["damageBuffId"], str, path + ".damageBuffId")
        for field in ("charSpeedToForceScale", "charSpeedToFacingScale", "waterGunDistanceToForceScale"):
            _curve(row[field], path + "." + field)
        _tag(row["dashTag"], path + ".dashTag")
        audio = _list(row["speedToExitAudioList"], path + ".speedToExitAudioList")
        for index, value in enumerate(audio):
            _number(value, f"{path}.speedToExitAudioList[{index}]")
        _localized_key(row["outOfRangeToast"], path + ".outOfRangeToast")
    return {"entryCount": len(rows), "tableKind": "kickable_config"}


def _region_shape(value: Any, path: str) -> None:
    value = _obj(value, ("position", "shapeType", "radius", "size", "rotation", "polyLinePoints", "polyLineCenter"), path)
    _vector3(value["position"], path + ".position")
    _type(value["shapeType"], int, path + ".shapeType")
    _number(value["radius"], path + ".radius")
    _vector3(value["size"], path + ".size")
    _vector3(value["rotation"], path + ".rotation")
    for index, point in enumerate(_list(value["polyLinePoints"], path + ".polyLinePoints")):
        point = _obj(point, ("x", "y"), f"{path}.polyLinePoints[{index}]")
        _number(point["x"], f"{path}.polyLinePoints[{index}].x")
        _number(point["y"], f"{path}.polyLinePoints[{index}].y")
    _vector3(value["polyLineCenter"], path + ".polyLineCenter")


def _map_regions(root: Any, source: str) -> dict[str, Any]:
    root = _dict(root, source)
    base = ("levelId", "mapRegionIdName", "mapRegionId", "isMist", "shapeList", "mapRegionType", "hideByMistId", "tierIndex", "groupId", "priority")
    tiered = base[:8] + ("tierMapRegionIds",) + base[8:]
    count = 0
    region_ids: set[tuple[str, int]] = set()
    for parent, values in root.items():
        if not parent.isdecimal():
            _fail(source + ".key", "decimal parent ID", parent)
        for index, row in enumerate(_list(values, f"{source}[{parent!r}]")):
            path = f"{source}[{parent!r}][{index}]"
            if not isinstance(row, dict) or tuple(row) not in (base, tiered):
                _fail(path + ".fields", (base, tiered), tuple(row) if isinstance(row, dict) else type(row).__name__)
            for field in ("levelId", "mapRegionIdName"):
                _type(row[field], str, path + "." + field)
            for field in ("mapRegionId", "mapRegionType", "hideByMistId", "tierIndex", "groupId", "priority"):
                _type(row[field], int, path + "." + field)
            _type(row["isMist"], bool, path + ".isMist")
            for shape_index, shape in enumerate(_list(row["shapeList"], path + ".shapeList")):
                _region_shape(shape, f"{path}.shapeList[{shape_index}]")
            if "tierMapRegionIds" in row:
                _ints(row["tierMapRegionIds"], path + ".tierMapRegionIds")
            identity = (row["levelId"], row["mapRegionId"])
            if identity in region_ids:
                _fail(path + ".mapRegionId", "unique within level", identity)
            region_ids.add(identity)
            count += 1
    return {"entryCount": count, "parentCount": len(root), "tableKind": "map_regions"}


def _bounding_box(value: Any, path: str) -> None:
    value = _obj(value, ("centerWorldPos", "extents", "eulerAngles"), path)
    for field in value:
        _vector3(value[field], path + "." + field)


def _mission_areas(root: Any, source: str) -> dict[str, Any]:
    root = _obj(root, ("m_areas",), source)
    maps = _dict(root["m_areas"], source + ".m_areas")
    count = 0
    base = ("subDataParentId", "missionAreaId", "activeOnTravelLine", "shape", "trackingOffset", "snapToGround", "needTrackingRoute")
    routed = base + ("trackingRouteInfo",)
    for map_id, areas in maps.items():
        if not map_id.isdecimal():
            _fail(source + ".m_areas.key", "decimal map ID", map_id)
        for area_id, row in _dict(areas, f"{source}.m_areas[{map_id!r}]").items():
            path = f"{source}.m_areas[{map_id!r}][{area_id!r}]"
            if not isinstance(row, dict) or tuple(row) not in (base, routed):
                _fail(path + ".fields", (base, routed), tuple(row) if isinstance(row, dict) else type(row).__name__)
            if row["missionAreaId"] != area_id:
                _fail(path + ".missionAreaId", area_id, row["missionAreaId"])
            _type(row["subDataParentId"], int, path + ".subDataParentId")
            for field in ("activeOnTravelLine", "snapToGround", "needTrackingRoute"):
                _type(row[field], bool, path + "." + field)
            shape = _obj(row["shape"], ("type", "position", "eulerAngles", "size", "radius"), path + ".shape")
            _type(shape["type"], int, path + ".shape.type")
            for field in ("position", "eulerAngles", "size"):
                _vector3(shape[field], path + ".shape." + field)
            _number(shape["radius"], path + ".shape.radius")
            _vector3(row["trackingOffset"], path + ".trackingOffset")
            if "trackingRouteInfo" in row:
                route = _obj(row["trackingRouteInfo"], ("ignoreYAxis", "points", "segmentPlaneList", "needBoundingBox", "trackingPointIdxOutOfBoundingBox", "needMultiBoundingBox", "boundingBox", "listOfBoundingBoxes"), path + ".trackingRouteInfo")
                for field in ("ignoreYAxis", "needBoundingBox", "needMultiBoundingBox"):
                    _type(route[field], bool, path + ".trackingRouteInfo." + field)
                _type(route["trackingPointIdxOutOfBoundingBox"], int, path + ".trackingRouteInfo.trackingPointIdxOutOfBoundingBox")
                for index, point in enumerate(_list(route["points"], path + ".trackingRouteInfo.points")):
                    point = _obj(point, ("worldPos", "matchMode"), f"{path}.trackingRouteInfo.points[{index}]")
                    _vector3(point["worldPos"], f"{path}.trackingRouteInfo.points[{index}].worldPos")
                    _type(point["matchMode"], int, f"{path}.trackingRouteInfo.points[{index}].matchMode")
                for index, plane in enumerate(_list(route["segmentPlaneList"], path + ".trackingRouteInfo.segmentPlaneList")):
                    plane = _obj(plane, ("xSize", "ySize", "worldPos", "eulerAngle"), f"{path}.trackingRouteInfo.segmentPlaneList[{index}]")
                    _number(plane["xSize"], f"{path}.trackingRouteInfo.segmentPlaneList[{index}].xSize")
                    _number(plane["ySize"], f"{path}.trackingRouteInfo.segmentPlaneList[{index}].ySize")
                    _vector3(plane["worldPos"], f"{path}.trackingRouteInfo.segmentPlaneList[{index}].worldPos")
                    _vector3(plane["eulerAngle"], f"{path}.trackingRouteInfo.segmentPlaneList[{index}].eulerAngle")
                _bounding_box(route["boundingBox"], path + ".trackingRouteInfo.boundingBox")
                for index, box in enumerate(_list(route["listOfBoundingBoxes"], path + ".trackingRouteInfo.listOfBoundingBoxes")):
                    _bounding_box(box, f"{path}.trackingRouteInfo.listOfBoundingBoxes[{index}]")
            count += 1
    return {"entryCount": count, "mapCount": len(maps), "tableKind": "mission_areas"}


def _mine(root: Any, source: str) -> dict[str, Any]:
    return _mine_teams(root, source, gas=False)


def _gas_mine(root: Any, source: str) -> dict[str, Any]:
    return _mine_teams(root, source, gas=True)


_DECODERS: dict[str, Callable[[Any, str], dict[str, Any]]] = {
    "AirWallRuntimeConfig.json": _air_wall,
    "AtmosphericNpcActiveSwitcherDataTable.json": _atmospheric_active_switchers,
    "AtmosphericNpcClusterDataTable.json": _atmospheric_clusters,
    "AtmosphericNpcSwitcherDataTable.json": _atmospheric_switchers,
    "AutoNameGlobalVarTable.json": _auto_name_global,
    "AutoNameMapVarTable.json": _auto_name_map,
    "GasMinePointTeamTable.json": _gas_mine,
    "GameplayTagPredefineTable.json": _gameplay_tags,
    "FocusModeInstanceTable.json": _focus_modes,
    "InteractiveCurveMoveConfigTable.json": _interactive_curves,
    "KickableGameplayConfigTable.json": _kickable_config,
    "LevelBasicInfoTable.json": _level_basic_info,
    "LevelScriptTeleportValidationDataTable.json": _levelscript_teleports,
    "LevelShortIdTable.json": _level_short_ids,
    "MapIdTable.json": _map_ids,
    "MapBriefInfoTable.json": _map_brief_info,
    "MapRegionTable.json": _map_regions,
    "MissionAreaTable.json": _mission_areas,
    "MinePointTeamTable.json": _mine,
    "ModelTable.json": _model_table,
    "ModelRadiusTable.json": _model_radius,
    "MultiTriggerTable.json": _multi_trigger,
    "PrtsLevelBindingTable.json": _prts_bindings,
    "NpcProxyExDataTable.json": _npc_proxy_extra,
    "NpcProxyTable.json": _npc_proxy_table,
    "StoryModeConfig.json": _story_mode,
    "SubGameMiscConfig.json": _subgame_misc,
    "SubGameEntityOverrideLibrary.json": _subgame_entity_overrides,
    "TeleportPerformTable.json": _teleport_perform,
    "TeleportReasonMaskConfig.json": _teleport_reason,
    "TempAbilityActivateConditionTable.json": _temp_ability_conditions,
    "TyphoeaArcheryAffixTableV2.json": _archery_affixes,
    "WorldEntityRegistry.json": _world_entity_registry,
}


def decode_compact_gameplay_config_json(
    data: bytes, *, source: str
) -> dict[str, Any]:
    normalized = source.replace("\\", "/")
    name = normalized.removeprefix(PREFIX)
    decoder = _DECODERS.get(name)
    if decoder is None or normalized != PREFIX + name:
        _fail(source, "supported compact GameplayConfig path", normalized)
    try:
        root = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GameplayConfigJsonDecodeError(
            f"{source}: invalid UTF-8 JSON: {exc}"
        ) from exc
    detail = decoder(root, source)
    return {
        "status": "named_exact",
        "schemaStatus": "named_exact",
        "wholeSchemaExact": True,
        "evidenceBoundary": "exact",
        **detail,
    }
