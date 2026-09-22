"""Exact JSON schemas for the two current NPC catalog files."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any


class NpcCatalogDecodeError(ValueError):
    pass


MONTAGE_HASH_PATH = "NPC/MontageJson/hashMapPath.Json"
PREFAB_MANIFEST_PATH = "NPC/PrefabInfo/manifest.json"


def is_npc_catalog_path(relative: str) -> bool:
    normalized = PurePosixPath(relative.replace("\\", "/")).as_posix()
    return normalized.casefold() in {MONTAGE_HASH_PATH.casefold(), PREFAB_MANIFEST_PATH.casefold()}


def _fail(path: str, expected: Any, actual: Any) -> None:
    raise NpcCatalogDecodeError(f"{path}: expected={expected!r} actual={actual!r}")


def decode_npc_catalog(data: bytes, *, source: str) -> dict[str, Any]:
    try:
        root = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NpcCatalogDecodeError(f"{source}: invalid UTF-8 JSON: {exc}") from exc
    normalized = PurePosixPath(source.replace("\\", "/")).as_posix().casefold()
    if normalized == PREFAB_MANIFEST_PATH.casefold():
        if not isinstance(root, dict) or tuple(root) != ("files",):
            _fail(source + ".fields", ("files",), tuple(root) if isinstance(root, dict) else type(root).__name__)
        files = root["files"]
        if not isinstance(files, list):
            _fail(source + ".files", "array", type(files).__name__)
        seen: set[str] = set()
        for index, value in enumerate(files):
            if type(value) is not str or not value.startswith("npc_") or not value.endswith(".json"):
                _fail(f"{source}.files[{index}]", "npc_*.json string", value)
            folded = value.casefold()
            if folded in seen:
                _fail(f"{source}.files[{index}]", "case-insensitive unique path", value)
            seen.add(folded)
        return {"status": "named_exact", "schemaStatus": "named_exact", "kind": "prefab-manifest", "fileCount": len(files)}
    if normalized != MONTAGE_HASH_PATH.casefold():
        _fail(source, (MONTAGE_HASH_PATH, PREFAB_MANIFEST_PATH), source)
    if not isinstance(root, dict) or tuple(root) != ("array",):
        _fail(source + ".fields", ("array",), tuple(root) if isinstance(root, dict) else type(root).__name__)
    rows = root["array"]
    if not isinstance(rows, list):
        _fail(source + ".array", "array", type(rows).__name__)
    hash_paths: dict[int, str] = {}
    duplicate_rows = 0
    for index, value in enumerate(rows):
        path = f"{source}.array[{index}]"
        if not isinstance(value, dict) or tuple(value) != ("hash", "path"):
            _fail(path + ".fields", ("hash", "path"), tuple(value) if isinstance(value, dict) else type(value).__name__)
        if type(value["hash"]) is not int or value["hash"] < 0:
            _fail(path + ".hash", "nonnegative integer", value["hash"])
        if type(value["path"]) is not str or not value["path"]:
            _fail(path + ".path", "nonempty string", value["path"])
        previous = hash_paths.get(value["hash"])
        if previous is not None and previous != value["path"]:
            _fail(path, "one path per hash", (previous, value["path"]))
        if previous is not None:
            duplicate_rows += 1
        hash_paths[value["hash"]] = value["path"]
    return {
        "status": "named_exact", "schemaStatus": "named_exact",
        "kind": "montage-hash-path", "entryCount": len(rows),
        "uniqueHashCount": len(hash_paths), "duplicateRowCount": duplicate_rows,
    }
