"""Exact JSON schema for current UI level-map load configuration files."""

from __future__ import annotations

import json
import math
from pathlib import PurePosixPath
from typing import Any


class UiLevelMapLoadConfigDecodeError(ValueError):
    pass


ROOT_FIELDS = (
    "basic", "staticElements", "tierNames", "lowChunks", "mediumChunks",
    "highChunks", "gridInfos", "mistInfos", "tierInfos",
)
BASIC_FIELDS = (
    "worldRectLeftBottom", "worldRectRightTop", "minScale", "isSingleLevel",
    "needInverseXZ", "horizontalViewGridsCount", "verticalViewGridsCount",
    "horizontalMoveGridsValue", "verticalMoveGridsValue",
    "horizontalInitOffsetGridsValue", "verticalInitOffsetGridsValue",
    "horizontalAllInitOffsetGridsValue", "verticalAllInitOffsetGridsValue",
)
CHUNK_FIELDS = (
    "chunkId", "lodType", "x", "y", "worldCenter", "worldLeftBottom",
    "worldRightTop", "grids", "mists", "tiers",
)
GRID_FIELDS = ("gridId", "x", "y", "worldCenter", "worldLeftBottom", "worldRightTop")
MIST_FIELDS = ("mistLoadId", "mistId", "worldCenter", "worldLeftBottom", "worldRightTop")
TIER_FIELDS = ("tierLoadId", "tierId", "worldCenter", "worldLeftBottom", "worldRightTop")
STATIC_SHAPES = {
    ("id", "type", "position", "isPermanent", "loadDistance", "directionAngle", "textId", "regionPanelIndex", "rootLevel", "displayTierId", "defaultVisible", "defaultImgScale"),
    ("id", "type", "position", "isPermanent", "loadDistance", "targetLevelId", "directionAngle", "regionPanelIndex", "rootLevel", "displayTierId", "defaultVisible", "defaultImgScale"),
    ("id", "type", "position", "isPermanent", "loadDistance", "targetLevelId", "directionAngle", "targetLevelSpriteName", "regionPanelIndex", "rootLevel", "displayTierId", "defaultVisible", "defaultImgScale"),
    ("id", "type", "position", "isPermanent", "loadDistance", "directionAngle", "regionPanelIndex", "rootLevel", "displayTierId", "defaultVisible", "defaultImgPath", "defaultImgScale", "visibilityPhases"),
    ("id", "type", "position", "isPermanent", "loadDistance", "directionAngle", "regionPanelIndex", "settlementId", "rootLevel", "displayTierId", "defaultVisible", "defaultImgScale"),
    ("id", "type", "position", "isPermanent", "loadDistance", "directionAngle", "regionLevelId", "regionPanelIndex", "rootLevel", "displayTierId", "defaultVisible", "defaultImgScale"),
    ("id", "type", "position", "isPermanent", "loadDistance", "directionAngle", "regionPanelIndex", "rootLevel", "displayTierId", "defaultVisible", "defaultImgScale"),
    ("id", "type", "position", "isPermanent", "loadDistance", "directionAngle", "regionPanelIndex", "rootLevel", "displayTierId", "defaultVisible", "defaultImgPath", "defaultImgScale", "imagePhases"),
    ("id", "type", "position", "isPermanent", "loadDistance", "directionAngle", "regionPanelIndex", "rootLevel", "displayTierId", "defaultVisible", "defaultImgPath", "defaultImgScale", "visibilityPhases", "imagePhases"),
    ("id", "type", "position", "isPermanent", "loadDistance", "directionAngle", "textId", "textPhases", "regionPanelIndex", "rootLevel", "displayTierId", "defaultVisible", "defaultImgScale"),
}


def is_ui_level_map_load_config_path(relative: str) -> bool:
    path = PurePosixPath(relative.replace("\\", "/"))
    return len(path.parts) == 2 and path.parts[0] == "UILevelMapLoadConfig" and path.suffix.casefold() == ".json"


def _fail(path: str, expected: Any, actual: Any) -> None:
    raise UiLevelMapLoadConfigDecodeError(f"{path}: expected={expected!r} actual={actual!r}")


def _object(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "object", type(value).__name__)
    if tuple(value) != fields:
        _fail(path + ".fields", fields, tuple(value))
    return value


def _typed(value: Any, expected: type, path: str) -> Any:
    if type(value) is not expected:
        _fail(path, expected.__name__, type(value).__name__)
    return value


def _number(value: Any, path: str) -> float | int:
    if type(value) not in (int, float) or not math.isfinite(value):
        _fail(path, "finite JSON number", value)
    return value


def _vec(value: Any, fields: tuple[str, ...], path: str) -> None:
    row = _object(value, fields, path)
    for field in fields:
        _number(row[field], f"{path}.{field}")


def _strings(value: Any, path: str) -> None:
    if not isinstance(value, list):
        _fail(path, "array", type(value).__name__)
    for index, item in enumerate(value):
        _typed(item, str, f"{path}[{index}]")


def _string_map(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        _fail(path, "object<string,string>", type(value).__name__)
    for key, item in value.items():
        _typed(key, str, f"{path}.key")
        _typed(item, str, f"{path}[{key!r}]")


def _condition_expression(value: Any, path: str) -> None:
    expression = _object(value, ("groups",), path)
    groups = expression["groups"]
    if not isinstance(groups, list):
        _fail(path + ".groups", "array", type(groups).__name__)
    shapes = {
        ("conditionType", "questId", "expectedState", "expectedValue", "compare"): "questId",
        ("conditionType", "expectedState", "globalVarKey", "expectedValue", "compare"): "globalVarKey",
        ("conditionType", "missionId", "expectedState", "expectedValue", "compare"): "missionId",
    }
    for group_index, group_value in enumerate(groups):
        group_path = f"{path}.groups[{group_index}]"
        group = _object(group_value, ("conditions",), group_path)
        conditions = group["conditions"]
        if not isinstance(conditions, list):
            _fail(group_path + ".conditions", "array", type(conditions).__name__)
        for condition_index, condition_value in enumerate(conditions):
            condition_path = f"{group_path}.conditions[{condition_index}]"
            if not isinstance(condition_value, dict) or tuple(condition_value) not in shapes:
                _fail(condition_path + ".fields", tuple(shapes), tuple(condition_value) if isinstance(condition_value, dict) else type(condition_value).__name__)
            identity = shapes[tuple(condition_value)]
            _typed(condition_value[identity], str, f"{condition_path}.{identity}")
            for field in ("conditionType", "expectedState", "expectedValue", "compare"):
                _typed(condition_value[field], int, f"{condition_path}.{field}")


def _phases(value: Any, kind: str, path: str) -> None:
    if not isinstance(value, list):
        _fail(path, "array", type(value).__name__)
    fields = {
        "visibilityPhases": ("conditionExpression", "isVisible"),
        "imagePhases": ("conditionExpression", "imgPath", "imgScale"),
        "textPhases": ("conditionExpression", "textId"),
    }[kind]
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        row = _object(item, fields, item_path)
        _condition_expression(row["conditionExpression"], item_path + ".conditionExpression")
        if kind == "visibilityPhases":
            _typed(row["isVisible"], bool, item_path + ".isVisible")
        elif kind == "imagePhases":
            _typed(row["imgPath"], str, item_path + ".imgPath")
            _typed(row["imgScale"], float, item_path + ".imgScale")
        else:
            _typed(row["textId"], str, item_path + ".textId")


def _static_element(value: Any, key: str, path: str) -> None:
    if not isinstance(value, dict) or tuple(value) not in STATIC_SHAPES:
        _fail(path + ".fields", "supported exact static-element shape", tuple(value) if isinstance(value, dict) else type(value).__name__)
    if value["id"] != key:
        _fail(path + ".id", key, value["id"])
    for field in ("id", "targetLevelId", "targetLevelSpriteName", "textId", "defaultImgPath", "regionLevelId", "settlementId"):
        if field in value:
            _typed(value[field], str, f"{path}.{field}")
    for field in ("type", "regionPanelIndex", "rootLevel", "displayTierId"):
        _typed(value[field], int, f"{path}.{field}")
    for field in ("isPermanent", "defaultVisible"):
        _typed(value[field], bool, f"{path}.{field}")
    for field in ("loadDistance", "directionAngle", "defaultImgScale"):
        _typed(value[field], float, f"{path}.{field}")
    _vec(value["position"], ("x", "y", "z"), path + ".position")
    for kind in ("visibilityPhases", "imagePhases", "textPhases"):
        if kind in value:
            _phases(value[kind], kind, f"{path}.{kind}")


def decode_ui_level_map_load_config(data: bytes, *, source: str = "<bytes>") -> dict[str, Any]:
    try:
        root = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UiLevelMapLoadConfigDecodeError(f"{source}: invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(root, dict):
        _fail(source, "object", type(root).__name__)
    if tuple(root) == ("loadLevelList",):
        _strings(root["loadLevelList"], source + ".loadLevelList")
        return {"status": "named_exact", "schemaStatus": "named_exact", "kind": "load-list", "levelCount": len(root["loadLevelList"])}

    root = _object(root, ROOT_FIELDS, source)
    basic = _object(root["basic"], BASIC_FIELDS, source + ".basic")
    _vec(basic["worldRectLeftBottom"], ("x", "y"), source + ".basic.worldRectLeftBottom")
    _vec(basic["worldRectRightTop"], ("x", "y"), source + ".basic.worldRectRightTop")
    for field in ("minScale", "horizontalMoveGridsValue", "verticalMoveGridsValue", "horizontalInitOffsetGridsValue", "verticalInitOffsetGridsValue", "horizontalAllInitOffsetGridsValue", "verticalAllInitOffsetGridsValue"):
        _typed(basic[field], float, f"{source}.basic.{field}")
    for field in ("isSingleLevel", "needInverseXZ"):
        _typed(basic[field], bool, f"{source}.basic.{field}")
    for field in ("horizontalViewGridsCount", "verticalViewGridsCount"):
        _typed(basic[field], int, f"{source}.basic.{field}")

    for key, value in root["staticElements"].items():
        _static_element(value, key, f"{source}.staticElements[{key!r}]")
    _string_map(root["tierNames"], source + ".tierNames")
    for collection, lod_type in (("lowChunks", 0), ("mediumChunks", 1), ("highChunks", 2)):
        if not isinstance(root[collection], dict):
            _fail(source + "." + collection, "object", type(root[collection]).__name__)
        for key, value in root[collection].items():
            path = f"{source}.{collection}[{key!r}]"
            row = _object(value, CHUNK_FIELDS, path)
            if row["chunkId"] != key or row["lodType"] != lod_type:
                _fail(path + ".identity", (key, lod_type), (row["chunkId"], row["lodType"]))
            _typed(row["x"], int, path + ".x"); _typed(row["y"], int, path + ".y")
            for field in ("worldCenter", "worldLeftBottom", "worldRightTop"):
                _vec(row[field], ("x", "y"), path + "." + field)
            _strings(row["grids"], path + ".grids")
            _string_map(row["mists"], path + ".mists")
            _string_map(row["tiers"], path + ".tiers")

    specs = (("gridInfos", GRID_FIELDS, "gridId", None), ("mistInfos", MIST_FIELDS, "mistLoadId", "mistId"), ("tierInfos", TIER_FIELDS, "tierLoadId", "tierId"))
    for collection, fields, identity, numeric_id in specs:
        if not isinstance(root[collection], dict):
            _fail(source + "." + collection, "object", type(root[collection]).__name__)
        for key, value in root[collection].items():
            path = f"{source}.{collection}[{key!r}]"
            row = _object(value, fields, path)
            if row[identity] != key:
                _fail(path + "." + identity, key, row[identity])
            if collection == "gridInfos":
                _typed(row["x"], int, path + ".x"); _typed(row["y"], int, path + ".y")
            else:
                _typed(row[numeric_id], int, path + "." + str(numeric_id))
            for field in ("worldCenter", "worldLeftBottom", "worldRightTop"):
                _vec(row[field], ("x", "y"), path + "." + field)

    return {
        "status": "named_exact", "schemaStatus": "named_exact", "kind": "level-map",
        "staticElementCount": len(root["staticElements"]),
        "chunkCount": sum(len(root[name]) for name in ("lowChunks", "mediumChunks", "highChunks")),
        "gridCount": len(root["gridInfos"]), "mistCount": len(root["mistInfos"]), "tierCount": len(root["tierInfos"]),
        "evidenceBoundary": "Every current JSON key and scalar/container type is validated; dynamic dictionaries use exact named value schemas and identity joins. Unknown fields or nested variants fail closed.",
    }
