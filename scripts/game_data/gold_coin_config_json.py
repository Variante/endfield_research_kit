"""Exact JSON schema for the current GoldCoinConfigTable."""

from __future__ import annotations

import json
import math
from typing import Any


class GoldCoinConfigDecodeError(ValueError):
    pass


RELATIVE_PATH = "NonGeneratedConfigs/GoldCoinConfigTable.json"
ROOT_FIELDS = ("data", "__AssemblyName__", "__TypeName__")
ROW_FIELDS = (
    "source", "scatterAlgorithm", "collisionRadius", "pickupDistance",
    "pickupSpeed", "pickupDelay", "coinLifetime", "fadeOutRemainingTime",
    "unpickableRemainingTime", "raycastDir", "previewPickupAcceleration",
    "previewPickupHeightFactor", "previewGroundYOffset", "sinArcLegacy",
    "physicalBouncePipeline",
)
SIN_FIELDS = ("scatterRadius", "expectedGravity", "minJumpHeight", "maxJumpHeight", "minJumpDuration", "maxJumpDuration")
PIPELINE_FIELDS = ("scatterArcDivisions", "scatterRadialJitter", "motion")
MOTION_FIELDS = (
    "scatterRadius", "bounciness", "bouncinessDecay", "airDrag", "gravity",
    "rotationFactor", "arcApexHeight", "collisionRadius",
    "velocityThresholdIdle", "horizontalFrictionOnGround", "angularAirDecayPerTick",
)


def is_gold_coin_config_path(relative: str) -> bool:
    return relative.replace("\\", "/").casefold() == RELATIVE_PATH.casefold()


def _fail(path: str, expected: Any, actual: Any) -> None:
    raise GoldCoinConfigDecodeError(f"{path}: expected={expected!r} actual={actual!r}")


def _obj(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or tuple(value) != fields:
        _fail(path + ".fields", fields, tuple(value) if isinstance(value, dict) else type(value).__name__)
    return value


def _float(value: Any, path: str) -> None:
    if type(value) is not float or not math.isfinite(value):
        _fail(path, "finite float", value)


def decode_gold_coin_config(data: bytes, *, source: str = RELATIVE_PATH) -> dict[str, Any]:
    try:
        root = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GoldCoinConfigDecodeError(f"{source}: invalid UTF-8 JSON: {exc}") from exc
    root = _obj(root, ROOT_FIELDS, source)
    if root["__AssemblyName__"] != "Gameplay.Beyond" or root["__TypeName__"] != "Beyond.Gameplay.GoldCoinConfigTable":
        _fail(source + ".typeIdentity", ("Gameplay.Beyond", "Beyond.Gameplay.GoldCoinConfigTable"), (root["__AssemblyName__"], root["__TypeName__"]))
    if not isinstance(root["data"], dict):
        _fail(source + ".data", "object", type(root["data"]).__name__)
    sources: set[int] = set()
    for key, value in root["data"].items():
        if type(key) is not str or not key:
            _fail(source + ".data.key", "nonempty string", key)
        path = f"{source}.data[{key!r}]"
        row = _obj(value, ROW_FIELDS, path)
        for field in ("source", "scatterAlgorithm"):
            if type(row[field]) is not int:
                _fail(path + "." + field, "int", type(row[field]).__name__)
        if row["source"] in sources:
            _fail(path + ".source", "unique enum value", row["source"])
        sources.add(row["source"])
        for field in ROW_FIELDS[2:9] + ROW_FIELDS[10:13]:
            _float(row[field], path + "." + field)
        ray = _obj(row["raycastDir"], ("x", "y", "z"), path + ".raycastDir")
        for field in ray:
            _float(ray[field], path + ".raycastDir." + field)
        sin = _obj(row["sinArcLegacy"], SIN_FIELDS, path + ".sinArcLegacy")
        for field in sin:
            _float(sin[field], path + ".sinArcLegacy." + field)
        pipeline = _obj(row["physicalBouncePipeline"], PIPELINE_FIELDS, path + ".physicalBouncePipeline")
        if type(pipeline["scatterArcDivisions"]) is not int:
            _fail(path + ".physicalBouncePipeline.scatterArcDivisions", "int", type(pipeline["scatterArcDivisions"]).__name__)
        _float(pipeline["scatterRadialJitter"], path + ".physicalBouncePipeline.scatterRadialJitter")
        motion = _obj(pipeline["motion"], MOTION_FIELDS, path + ".physicalBouncePipeline.motion")
        for field in motion:
            _float(motion[field], path + ".physicalBouncePipeline.motion." + field)
    return {"status": "named_exact", "schemaStatus": "named_exact", "entryCount": len(root["data"]), "sourceCount": len(sources)}
