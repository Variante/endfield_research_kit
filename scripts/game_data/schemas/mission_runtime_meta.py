"""Exact named schema for current MissionRuntimeAsset ``*_meta.json`` rows."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any


class MissionRuntimeMetaDecodeError(ValueError):
    pass


ROOT_FIELDS = ("missionId", "acceptMode", "missionType", "missionImportance", "rewardId")
ACCEPT_FIELDS = ("mode", "levelId", "missionType")
ACCEPT_INFO_FIELDS = ("mode", "modeInfo", "levelId", "missionType")
NPC_INFO_FIELDS = ("$type", "npcProxyId", "dialogId", "finishId", "levelId")
AREA_INFO_FIELDS = ("$type", "useMultiArea", "levelId", "missionAreaId", "areas")
AREA_FIELDS = ("levelId", "missionAreaId")
NPC_INFO_TYPE = "Beyond.Gameplay.MissionAcceptMode+NPCInfo, Gameplay.Beyond"
AREA_INFO_TYPE = "Beyond.Gameplay.MissionAcceptMode+EnterAreaInfo, Gameplay.Beyond"


def is_mission_runtime_meta_path(relative: str) -> bool:
    path = PurePosixPath(relative.replace("\\", "/"))
    return (
        len(path.parts) == 2
        and path.parts[0] == "MissionRuntimeAsset"
        and path.name.casefold().endswith("_meta.json")
    )


def _fail(path: str, expected: Any, actual: Any) -> None:
    raise MissionRuntimeMetaDecodeError(
        f"{path}: expected={expected!r} actual={actual!r}"
    )


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


def decode_mission_runtime_meta(data: bytes, *, source: str = "<bytes>") -> dict[str, Any]:
    try:
        root = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionRuntimeMetaDecodeError(f"{source}: invalid UTF-8 JSON: {exc}") from exc
    root = _object(root, ROOT_FIELDS, source)
    _typed(root["missionId"], str, source + ".missionId")
    _typed(root["missionType"], int, source + ".missionType")
    _typed(root["missionImportance"], int, source + ".missionImportance")
    _typed(root["rewardId"], str, source + ".rewardId")

    accept = root["acceptMode"]
    keys = tuple(accept) if isinstance(accept, dict) else ()
    if keys == ACCEPT_FIELDS:
        accept = _object(accept, ACCEPT_FIELDS, source + ".acceptMode")
        mode_info_type = None
        area_count = 0
    elif keys == ACCEPT_INFO_FIELDS:
        accept = _object(accept, ACCEPT_INFO_FIELDS, source + ".acceptMode")
        info = accept["modeInfo"]
        info_keys = tuple(info) if isinstance(info, dict) else ()
        if info_keys == NPC_INFO_FIELDS:
            info = _object(info, NPC_INFO_FIELDS, source + ".acceptMode.modeInfo")
            if info["$type"] != NPC_INFO_TYPE:
                _fail(source + ".acceptMode.modeInfo.$type", NPC_INFO_TYPE, info["$type"])
            for field in ("npcProxyId", "dialogId", "levelId"):
                _typed(info[field], str, f"{source}.acceptMode.modeInfo.{field}")
            _typed(info["finishId"], int, source + ".acceptMode.modeInfo.finishId")
            mode_info_type = "NPCInfo"
            area_count = 0
        elif info_keys == AREA_INFO_FIELDS:
            info = _object(info, AREA_INFO_FIELDS, source + ".acceptMode.modeInfo")
            if info["$type"] != AREA_INFO_TYPE:
                _fail(source + ".acceptMode.modeInfo.$type", AREA_INFO_TYPE, info["$type"])
            _typed(info["useMultiArea"], bool, source + ".acceptMode.modeInfo.useMultiArea")
            _typed(info["levelId"], str, source + ".acceptMode.modeInfo.levelId")
            _typed(info["missionAreaId"], str, source + ".acceptMode.modeInfo.missionAreaId")
            if not isinstance(info["areas"], list):
                _fail(source + ".acceptMode.modeInfo.areas", "array", type(info["areas"]).__name__)
            for index, value in enumerate(info["areas"]):
                area = _object(value, AREA_FIELDS, f"{source}.acceptMode.modeInfo.areas[{index}]")
                _typed(area["levelId"], str, f"{source}.acceptMode.modeInfo.areas[{index}].levelId")
                _typed(area["missionAreaId"], str, f"{source}.acceptMode.modeInfo.areas[{index}].missionAreaId")
            mode_info_type = "EnterAreaInfo"
            area_count = len(info["areas"])
        else:
            _fail(source + ".acceptMode.modeInfo.fields", (NPC_INFO_FIELDS, AREA_INFO_FIELDS), info_keys)
    else:
        _fail(source + ".acceptMode.fields", (ACCEPT_FIELDS, ACCEPT_INFO_FIELDS), keys)

    _typed(accept["mode"], int, source + ".acceptMode.mode")
    _typed(accept["levelId"], str, source + ".acceptMode.levelId")
    _typed(accept["missionType"], int, source + ".acceptMode.missionType")
    return {
        "status": "named_exact",
        "schemaStatus": "named_exact",
        "fieldOrder": list(ROOT_FIELDS),
        "modeInfoType": mode_info_type,
        "areaCount": area_count,
        "evidenceBoundary": (
            "Every JSON key is stored explicitly. The current mission meta root, "
            "accept-mode wrapper, and the two observed typed mode-info variants "
            "are validated exactly; new fields or variants fail closed."
        ),
    }
