"""Exact schema validation for current NPC ``PrefabInfo/npc_*.json`` files.

The JSON carries its field names directly.  This reader binds those names to
the current ``NPCPrefabInfo`` and nested wrapper shapes, validates every value,
and rejects extra, reordered, or unsupported fields instead of treating a
successful generic JSON parse as a schema claim.
"""

from __future__ import annotations

import json
import math
from pathlib import PurePosixPath
from typing import Any, Callable


class NpcPrefabInfoDecodeError(ValueError):
    """Raised when a selected PrefabInfo file differs from the reviewed schema."""


ROOT_FIELDS = (
    "partNameIdList", "avatarTempletName", "avatarMeshName",
    "cpuAnimationTempletName", "abilityTempletName", "sizeType",
    "templateType", "camp", "career", "gender", "id",
    "facialMorphAvatarName", "earMorphAvatarName", "useHighResShadow",
    "correspondingCharId", "lodNum", "renders", "materialCodes", "scale",
    "hasCloth", "needBattle", "battleData", "bornTag",
    "npcGamePlayDataList", "accessories", "bornEffectInfos",
    "waterInteractData", "aiCfg", "lookAt", "disableBlink",
    "enableBlurDetect", "enableMainCharCollisionDetect",
    "mainCharCollisionEnterDistance", "mainCharCollisionLeaveDistance",
    "mainCharCollisionReenterCd", "mainCharCollisionAction",
    "mainCharCollisionEffectKey", "mainCharCollisionEffectMountPoint",
    "blurPriority", "confrontAnims", "battleAnims", "idleBreakTags",
)

BATTLE_DATA_FIELDS = ("battleShapeData", "activeSkillId", "passiveSkillId", "blackboard")
BATTLE_SHAPE_FIELDS = (
    "_shape", "_rotationOffset", "_useExtentKey", "_extent",
    "_extentXKey", "_extentYKey", "_extentZKey", "_useCenterKey",
    "_center", "_centerXKey", "_centerYKey", "_centerZKey",
    "_heightKey", "_height", "_radiusKey", "_radius",
)
VECTOR3_FIELDS = ("x", "y", "z")
ACCESSORY_FIELDS = ("name", "mountPoint", "bIsHidden")
BORN_EFFECT_FIELDS = ("effectKey", "npcEffectType", "mountPoint")
WATER_FIELDS = ("effectKey", "rippleSize", "waterDepth")
ANIM_FIELDS = ("confrontAnim", "overrideConfrontRot", "needConfrontRot")
BATTLE_ANIM_FIELDS = ("battleAnim", "overrideBattleRot", "needBattleRot")
TAG_FIELDS = ("tagId",)


def is_npc_prefab_info_path(relative: str) -> bool:
    path = PurePosixPath(relative.replace("\\", "/"))
    return (
        len(path.parts) == 3
        and path.parts[:2] == ("NPC", "PrefabInfo")
        and path.name.casefold().startswith("npc_")
        and path.suffix.casefold() == ".json"
    )


def _fail(path: str, expected: Any, actual: Any) -> None:
    raise NpcPrefabInfoDecodeError(
        f"{path}: expected={expected!r} actual={actual!r}"
    )


def _object(value: Any, fields: tuple[str, ...], path: str, *, optional: str | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "object", type(value).__name__)
    keys = tuple(value)
    accepted = (fields, tuple(field for field in fields if field != optional)) if optional else (fields,)
    if keys not in accepted:
        _fail(path + ".fields", accepted, keys)
    return value


def _typed(value: Any, expected: type, path: str) -> Any:
    if type(value) is not expected:
        _fail(path, expected.__name__, type(value).__name__)
    if expected is float and not math.isfinite(value):
        _fail(path, "finite float", value)
    return value


def _list(value: Any, item: Callable[[Any, str], Any], path: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, "array", type(value).__name__)
    for index, member in enumerate(value):
        item(member, f"{path}[{index}]")
    return value


def _strings(value: Any, path: str) -> list[Any]:
    return _list(value, lambda member, item_path: _typed(member, str, item_path), path)


def _integers(value: Any, path: str) -> list[Any]:
    return _list(value, lambda member, item_path: _typed(member, int, item_path), path)


def _vector3(value: Any, path: str) -> None:
    row = _object(value, VECTOR3_FIELDS, path)
    for field in VECTOR3_FIELDS:
        _typed(row[field], float, f"{path}.{field}")


def _tag(value: Any, path: str) -> None:
    row = _object(value, TAG_FIELDS, path)
    _typed(row["tagId"], int, path + ".tagId")


def _anim(value: Any, path: str, *, battle: bool) -> None:
    fields = BATTLE_ANIM_FIELDS if battle else ANIM_FIELDS
    tag_field = "battleAnim" if battle else "confrontAnim"
    row = _object(value, fields, path)
    _tag(row[tag_field], path + "." + tag_field)
    _typed(row[fields[1]], bool, path + "." + fields[1])
    _typed(row[fields[2]], bool, path + "." + fields[2])


def decode_npc_prefab_info(data: bytes, *, source: str = "<bytes>") -> dict[str, Any]:
    try:
        root = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NpcPrefabInfoDecodeError(f"{source}: invalid UTF-8 JSON: {exc}") from exc
    root = _object(root, ROOT_FIELDS, source, optional="correspondingCharId")

    string_fields = (
        "avatarTempletName", "avatarMeshName", "cpuAnimationTempletName",
        "abilityTempletName", "camp", "career", "id",
        "facialMorphAvatarName", "earMorphAvatarName", "aiCfg",
        "mainCharCollisionEffectKey",
    )
    for field in string_fields:
        _typed(root[field], str, f"{source}.{field}")
    if "correspondingCharId" in root:
        _typed(root["correspondingCharId"], str, source + ".correspondingCharId")
    for field in ("sizeType", "templateType", "gender", "lodNum", "mainCharCollisionAction", "mainCharCollisionEffectMountPoint", "blurPriority"):
        _typed(root[field], int, f"{source}.{field}")
    for field in ("useHighResShadow", "hasCloth", "needBattle", "lookAt", "disableBlink", "enableBlurDetect", "enableMainCharCollisionDetect"):
        _typed(root[field], bool, f"{source}.{field}")
    for field in ("scale", "mainCharCollisionEnterDistance", "mainCharCollisionLeaveDistance", "mainCharCollisionReenterCd"):
        _typed(root[field], float, f"{source}.{field}")
    for field in ("partNameIdList", "renders", "bornTag", "npcGamePlayDataList"):
        _strings(root[field], f"{source}.{field}")
    _integers(root["materialCodes"], source + ".materialCodes")

    battle = _object(root["battleData"], BATTLE_DATA_FIELDS, source + ".battleData")
    shape = _object(battle["battleShapeData"], BATTLE_SHAPE_FIELDS, source + ".battleData.battleShapeData")
    _typed(shape["_shape"], int, source + ".battleData.battleShapeData._shape")
    for field in ("_rotationOffset", "_extent", "_center"):
        _vector3(shape[field], f"{source}.battleData.battleShapeData.{field}")
    for field in ("_useExtentKey", "_useCenterKey"):
        _typed(shape[field], bool, f"{source}.battleData.battleShapeData.{field}")
    for field in ("_extentXKey", "_extentYKey", "_extentZKey", "_centerXKey", "_centerYKey", "_centerZKey", "_heightKey", "_radiusKey"):
        _typed(shape[field], str, f"{source}.battleData.battleShapeData.{field}")
    for field in ("_height", "_radius"):
        _typed(shape[field], float, f"{source}.battleData.battleShapeData.{field}")
    _strings(battle["activeSkillId"], source + ".battleData.activeSkillId")
    _strings(battle["passiveSkillId"], source + ".battleData.passiveSkillId")
    if battle["blackboard"] != []:
        _fail(source + ".battleData.blackboard", "current empty SkillBBData list", battle["blackboard"])

    def accessory(value: Any, path: str) -> None:
        row = _object(value, ACCESSORY_FIELDS, path)
        _typed(row["name"], str, path + ".name")
        _typed(row["mountPoint"], int, path + ".mountPoint")
        _typed(row["bIsHidden"], bool, path + ".bIsHidden")

    def born_effect(value: Any, path: str) -> None:
        row = _object(value, BORN_EFFECT_FIELDS, path)
        _typed(row["effectKey"], str, path + ".effectKey")
        _typed(row["npcEffectType"], int, path + ".npcEffectType")
        _typed(row["mountPoint"], int, path + ".mountPoint")

    _list(root["accessories"], accessory, source + ".accessories")
    _list(root["bornEffectInfos"], born_effect, source + ".bornEffectInfos")
    water = _object(root["waterInteractData"], WATER_FIELDS, source + ".waterInteractData")
    _typed(water["effectKey"], str, source + ".waterInteractData.effectKey")
    _typed(water["rippleSize"], float, source + ".waterInteractData.rippleSize")
    _typed(water["waterDepth"], float, source + ".waterInteractData.waterDepth")
    _list(root["confrontAnims"], lambda value, path: _anim(value, path, battle=False), source + ".confrontAnims")
    _list(root["battleAnims"], lambda value, path: _anim(value, path, battle=True), source + ".battleAnims")
    _list(root["idleBreakTags"], _tag, source + ".idleBreakTags")

    return {
        "status": "named_exact",
        "schemaStatus": "named_exact",
        "fieldOrder": list(root),
        "fieldCount": len(root),
        "hasCorrespondingCharId": "correspondingCharId" in root,
        "accessoryCount": len(root["accessories"]),
        "bornEffectCount": len(root["bornEffectInfos"]),
        "confrontAnimCount": len(root["confrontAnims"]),
        "battleAnimCount": len(root["battleAnims"]),
        "evidenceBoundary": (
            "Every JSON key is stored explicitly. Current NPCPrefabInfo and nested "
            "wrapper field sets and scalar/container types are validated exactly; "
            "the currently empty SkillBBData list remains fail-closed on population."
        ),
    }
