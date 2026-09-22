"""Exact recursive schema for LevelMountPoint JSON trees."""

from __future__ import annotations

import json
import math
from pathlib import PurePosixPath
from typing import Any


class LevelMountPointJsonDecodeError(ValueError):
    pass


def is_level_mount_point_path(relative: str) -> bool:
    path = PurePosixPath(relative.replace("\\", "/"))
    return len(path.parts) == 2 and path.parts[0] == "LevelMountPoint" and path.suffix.casefold() == ".json"


def _fail(path: str, expected: Any, actual: Any) -> None:
    raise LevelMountPointJsonDecodeError(
        f"{path}: expected={expected!r} actual={actual!r}"
    )


def _obj(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or tuple(value) != fields:
        _fail(path + ".fields", fields, tuple(value) if isinstance(value, dict) else type(value).__name__)
    return value


def _vector3(value: Any, path: str) -> None:
    value = _obj(value, ("x", "y", "z"), path)
    for field, number in value.items():
        if type(number) not in (int, float) or (type(number) is float and not math.isfinite(number)):
            _fail(path + "." + field, "finite number", number)


def _node(value: Any, path: str, counters: dict[str, int], depth: int) -> None:
    if depth > 32:
        _fail(path, "depth <= 32", depth)
    branch = ("nodeName", "children")
    leaf = ("nodeName", "mountPoint")
    teleport = ("nodeName", "mountPoint", "extraData")
    if not isinstance(value, dict) or tuple(value) not in (branch, leaf, teleport):
        _fail(path + ".fields", (branch, leaf, teleport), tuple(value) if isinstance(value, dict) else type(value).__name__)
    if type(value["nodeName"]) is not str:
        _fail(path + ".nodeName", "string", type(value["nodeName"]).__name__)
    counters["nodeCount"] += 1
    counters["maxDepth"] = max(counters["maxDepth"], depth)
    if "children" in value:
        children = value["children"]
        if not isinstance(children, dict):
            _fail(path + ".children", "object", type(children).__name__)
        for key, child in children.items():
            if type(key) is not str or not key:
                _fail(path + ".children.key", "nonempty string", key)
            _node(child, f"{path}.children[{key!r}]", counters, depth + 1)
        return
    mount = _obj(value["mountPoint"], ("position", "rotation"), path + ".mountPoint")
    _vector3(mount["position"], path + ".mountPoint.position")
    _vector3(mount["rotation"], path + ".mountPoint.rotation")
    counters["mountPointCount"] += 1
    if "extraData" in value:
        extra = _obj(value["extraData"], ("$type", "tpUniqueId"), path + ".extraData")
        identity = "Beyond.Gameplay.LevelTpMountPointExtraData, Gameplay.Beyond"
        if extra["$type"] != identity:
            _fail(path + ".extraData.$type", identity, extra["$type"])
        if type(extra["tpUniqueId"]) is not str or not extra["tpUniqueId"]:
            _fail(path + ".extraData.tpUniqueId", "nonempty string", extra["tpUniqueId"])
        counters["teleportCount"] += 1


def decode_level_mount_points(data: bytes, *, source: str) -> dict[str, Any]:
    if not is_level_mount_point_path(source):
        _fail(source, "LevelMountPoint/<level>.json", source)
    try:
        root = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LevelMountPointJsonDecodeError(f"{source}: invalid UTF-8 JSON: {exc}") from exc
    root = _obj(root, ("subRootByType",), source)
    roots = root["subRootByType"]
    if not isinstance(roots, dict):
        _fail(source + ".subRootByType", "object", type(roots).__name__)
    counters = {"nodeCount": 0, "mountPointCount": 0, "teleportCount": 0, "maxDepth": 0}
    for key, value in roots.items():
        if type(key) is not str or not key:
            _fail(source + ".subRootByType.key", "nonempty string", key)
        _node(value, f"{source}.subRootByType[{key!r}]", counters, 0)
    return {
        "status": "named_exact",
        "schemaStatus": "named_exact",
        "wholeSchemaExact": True,
        "evidenceBoundary": "exact",
        "rootTypeCount": len(roots),
        **counters,
    }


__all__ = ["LevelMountPointJsonDecodeError", "decode_level_mount_points", "is_level_mount_point_path"]
