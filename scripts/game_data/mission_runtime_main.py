"""Fail-closed named schema reader for main MissionRuntimeAsset JSON bodies."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.jsondata_named_schema import (
    load_schema_contract,
    make_fail,
    parse_utf8_json,
    validate_document,
)


class MissionRuntimeMainDecodeError(ValueError):
    pass


CONTRACT_PATH = CONTRACTS_DIR / "mission_runtime_main_schema.json"
CONTRACT_SHA256 = "B193E1C9B27D9A7190C008A65F24431DB260EB5D33238ED7CF7DB3DC80E0596E"
CONTRACT_SCHEMA = "endfield.mission-runtime-main-json-schema.v1"
_fail = make_fail(MissionRuntimeMainDecodeError)


def is_mission_runtime_main_path(relative: str) -> bool:
    path = PurePosixPath(relative.replace("\\", "/"))
    return (
        len(path.parts) == 2
        and path.parts[0] == "MissionRuntimeAsset"
        and path.suffix.casefold() == ".json"
        and not path.name.casefold().endswith("_meta.json")
    )


@lru_cache(maxsize=1)
def _load_contract() -> dict[str, Any]:
    return load_schema_contract(
        CONTRACT_PATH,
        sha256=CONTRACT_SHA256,
        schema=CONTRACT_SCHEMA,
        error=MissionRuntimeMainDecodeError,
    )


def _validate_relations(root: dict[str, Any], source: str) -> None:
    path = PurePosixPath(source.replace("\\", "/"))
    if is_mission_runtime_main_path(path.as_posix()):
        expected_mission_id = path.stem
        if root.get("missionId") != expected_mission_id:
            _fail(source + ".missionId", expected_mission_id, root.get("missionId"))

    id_to_key = root["propertyIdToKeyMap"]
    key_to_id = root["propertyKeyToIdMap"]
    if len(id_to_key) != len(key_to_id):
        _fail(source + ".propertyMaps.length", len(id_to_key), len(key_to_id))
    for property_id, key in id_to_key.items():
        if key_to_id.get(key) != int(property_id):
            _fail(source + ".propertyMaps.inverse", (key, int(property_id)), key_to_id.get(key))
    for key, property_id in key_to_id.items():
        if id_to_key.get(str(property_id)) != key:
            _fail(source + ".propertyMaps.inverse", (str(property_id), key), id_to_key.get(str(property_id)))

    action_keys = root["clientActionMapKey"]
    action_values = root["clientActionMapValue"]
    if len(action_keys) != len(action_values):
        _fail(source + ".clientActionMap.length", len(action_keys), len(action_values))


def decode_mission_runtime_main(
    data: bytes, *, source: str = "<bytes>"
) -> dict[str, Any]:
    root = parse_utf8_json(data, source=source, error=MissionRuntimeMainDecodeError)
    contract = _load_contract()
    counters = validate_document(root, contract, source=source, error=MissionRuntimeMainDecodeError)
    if not isinstance(root, dict):
        _fail(source, "mission root object", type(root).__name__)
    _validate_relations(root, source)
    return {
        "status": "named_exact",
        "schemaStatus": "named_exact",
        "missionId": root["missionId"],
        "questCount": len(root["questDic"]),
        "typedSchemaCount": len(contract["taggedObjects"]),
        "dynamicDictionaryCount": len(contract["dynamicDictionaries"]),
        **counters,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


__all__ = [
    "MissionRuntimeMainDecodeError",
    "decode_mission_runtime_main",
    "is_mission_runtime_main_path",
]
