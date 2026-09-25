"""Exact named schema for current textual ``MapConfig`` JsonData rows."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any


class MapConfigDecodeError(ValueError):
    pass


ROOT_FIELDS = (
    "mapIdStr", "mapId", "isSeamless", "sideGridNum", "levelIds",
    "streamingMapConfigPath", "facSystemSkip", "sceneStateConditions",
    "levelStrIds", "domainName", "mapVarNumId2Name", "mapVarName2NumId",
    "mapVarClientDefaultValues",
)
ROOT_FIELDS_WITH_STATES = ROOT_FIELDS[:7] + ("sceneStates",) + ROOT_FIELDS[7:]
STATE_ROW_FIELDS = ("stateName", "condition")

CONDITION_FIELDS = {
    "Beyond.Gameplay.SimpleConditionCheckQuestState, Gameplay.Beyond":
        ("$type", "questId", "compareOperator", "compareTarget"),
    "Beyond.Gameplay.SimpleConditionCheckMissionState, Gameplay.Beyond":
        ("$type", "missionId", "compareOperator", "compareTarget"),
    "Beyond.Gameplay.SimpleConditionCheckMapVar, Gameplay.Beyond":
        ("$type", "belongMapId", "mapVarName", "compareOperator", "compareTarget"),
    "Beyond.Gameplay.SimpleConditionCheckGlobalVar, Gameplay.Beyond":
        ("$type", "globalVarName", "compareOperator", "compareTarget"),
    "Beyond.Gameplay.CombinedConditionRuntime, Gameplay.Beyond":
        ("$type", "conditionOperator", "reverse", "subConditions"),
}


def is_map_config_path(relative: str) -> bool:
    path = PurePosixPath(relative.replace("\\", "/"))
    return len(path.parts) == 2 and path.parts[0] == "MapConfig" and path.suffix.casefold() == ".json"


def _fail(path: str, expected: Any, actual: Any) -> None:
    raise MapConfigDecodeError(f"{path}: expected={expected!r} actual={actual!r}")


def _typed(value: Any, expected: type, path: str) -> Any:
    if type(value) is not expected:
        _fail(path, expected.__name__, type(value).__name__)
    return value


def _object(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "object", type(value).__name__)
    if tuple(value) != fields:
        _fail(path + ".fields", fields, tuple(value))
    return value


def _condition(
    value: Any, path: str, *, map_id: str, map_var_names: set[str], depth: int = 0,
) -> None:
    if depth > 16:
        _fail(path, "condition nesting <= 16", depth)
    if not isinstance(value, dict):
        _fail(path, "condition object", type(value).__name__)
    condition_type = value.get("$type")
    fields = CONDITION_FIELDS.get(condition_type)
    if fields is None:
        _fail(path + ".$type", tuple(CONDITION_FIELDS), condition_type)
    row = _object(value, fields, path)
    _typed(row["$type"], str, path + ".$type")
    if fields[-1] == "subConditions":
        _typed(row["conditionOperator"], int, path + ".conditionOperator")
        _typed(row["reverse"], bool, path + ".reverse")
        if not isinstance(row["subConditions"], list):
            _fail(path + ".subConditions", "array", type(row["subConditions"]).__name__)
        for index, child in enumerate(row["subConditions"]):
            _condition(
                child, f"{path}.subConditions[{index}]",
                map_id=map_id, map_var_names=map_var_names, depth=depth + 1,
            )
        return
    for field in fields[1:-2]:
        _typed(row[field], str, f"{path}.{field}")
    _typed(row["compareOperator"], int, path + ".compareOperator")
    _typed(row["compareTarget"], int, path + ".compareTarget")
    if condition_type == "Beyond.Gameplay.SimpleConditionCheckMapVar, Gameplay.Beyond":
        if row["belongMapId"] != map_id:
            _fail(path + ".belongMapId", map_id, row["belongMapId"])
        if row["mapVarName"] not in map_var_names:
            _fail(path + ".mapVarName", "mapVarName2NumId key", row["mapVarName"])


def decode_map_config(data: bytes, *, source: str = "<bytes>") -> dict[str, Any]:
    try:
        root = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MapConfigDecodeError(f"{source}: invalid UTF-8 JSON: {exc}") from exc
    keys = tuple(root) if isinstance(root, dict) else ()
    if keys == ROOT_FIELDS:
        root = _object(root, ROOT_FIELDS, source)
    elif keys == ROOT_FIELDS_WITH_STATES:
        root = _object(root, ROOT_FIELDS_WITH_STATES, source)
    else:
        _fail(source + ".fields", (ROOT_FIELDS, ROOT_FIELDS_WITH_STATES), keys)
    for field in ("mapIdStr", "streamingMapConfigPath", "domainName"):
        _typed(root[field], str, f"{source}.{field}")
    for field in ("mapId", "sideGridNum"):
        _typed(root[field], int, f"{source}.{field}")
    for field in ("isSeamless", "facSystemSkip"):
        _typed(root[field], bool, f"{source}.{field}")
    for field, item_type in (("levelIds", int), ("levelStrIds", str)):
        values = root[field]
        if not isinstance(values, list):
            _fail(f"{source}.{field}", "array", type(values).__name__)
        for index, value in enumerate(values):
            _typed(value, item_type, f"{source}.{field}[{index}]")
    scene_states = root.get("sceneStates", {})
    if not isinstance(scene_states, dict):
        _fail(source + ".sceneStates", "object", type(scene_states).__name__)
    state_indexes: set[int] = set()
    for key, value in scene_states.items():
        _typed(key, str, source + ".sceneStates.key")
        _typed(value, int, f"{source}.sceneStates[{key!r}]")
        if not key or not 0 <= value < 32 or value in state_indexes:
            _fail(f"{source}.sceneStates[{key!r}]", "unique name and UInt32 mask index 0..31", value)
        state_indexes.add(value)
    number_to_name = root["mapVarNumId2Name"]
    name_to_number = root["mapVarName2NumId"]
    if not isinstance(number_to_name, dict) or not isinstance(name_to_number, dict):
        _fail(source + ".mapVars", "two objects", (type(number_to_name).__name__, type(name_to_number).__name__))
    for key, value in number_to_name.items():
        if not key.isdecimal():
            _fail(source + ".mapVarNumId2Name.key", "decimal string", key)
        _typed(value, str, f"{source}.mapVarNumId2Name[{key!r}]")
        if name_to_number.get(value) != int(key):
            _fail(source + ".mapVarInverse", (value, int(key)), name_to_number.get(value))
    for key, value in name_to_number.items():
        _typed(key, str, source + ".mapVarName2NumId.key")
        _typed(value, int, f"{source}.mapVarName2NumId[{key!r}]")
        if number_to_name.get(str(value)) != key:
            _fail(source + ".mapVarInverse", (str(value), key), number_to_name.get(str(value)))
    state_rows = root["sceneStateConditions"]
    if not isinstance(state_rows, list):
        _fail(source + ".sceneStateConditions", "array", type(state_rows).__name__)
    condition_names: set[str] = set()
    map_var_names = set(name_to_number)
    for index, value in enumerate(state_rows):
        path = f"{source}.sceneStateConditions[{index}]"
        row = _object(value, STATE_ROW_FIELDS, path)
        name = _typed(row["stateName"], str, path + ".stateName")
        if name not in scene_states or name in condition_names:
            _fail(path + ".stateName", "unique sceneStates key", name)
        condition_names.add(name)
        _condition(
            row["condition"], path + ".condition",
            map_id=root["mapIdStr"], map_var_names=map_var_names,
        )
    if root["mapVarClientDefaultValues"] != {}:
        _fail(source + ".mapVarClientDefaultValues", "current empty object", root["mapVarClientDefaultValues"])
    return {
        "status": "named_exact",
        "schemaStatus": "named_exact",
        "fieldOrder": list(root),
        "levelCount": len(root["levelIds"]),
        "sceneStateCount": len(scene_states),
        "conditionCount": len(state_rows),
        "mapVariableCount": len(number_to_name),
        "evidenceBoundary": (
            "Every JSON key is stored explicitly. Both current root shapes, typed "
            "condition variants, unique scene-state mask indices, condition-name "
            "membership, map-variable condition ownership, and inverse map-variable "
            "dictionaries are validated exactly; client defaults remain fail-closed "
            "on the currently unobserved populated shape."
        ),
    }
