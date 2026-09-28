"""Byte-pinned named schemas for the remaining textual JsonData tables.

The reviewed ``jsondata_text_schema.json`` contract (walked by
``schemas.named_schema``) closes the AI global settings and enemy-template
path summary, the root-level NPC-proxy and script-task tables, interactive
collection counts, doodad groups, factory regions and spaceship cabin spawn
data.  ``_relations`` adds the cross-field checks the node walk cannot
express: enemy-template paths end in ``data_<id>.asset``, the two root tables
carry their ``Gameplay.Beyond`` type identities, collection rows hold exactly
33 integer counts, and doodad group ids are globally unique.  The
``LevelMountPoint`` files use the recursive reader in
``schemas.level_mount_point`` instead.

``exact`` stored structure for reconstruction placement, navigation,
attachment and idle-behavior work; it does not show which runtime object
consumes a row.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.schemas.named_schema import (
    load_schema_contract,
    make_fail,
    parse_utf8_json,
    section_counts,
    validate_document,
)


class JsonDataTextSchemaDecodeError(ValueError):
    pass


CONTRACT_PATH = CONTRACTS_DIR / "jsondata_text_schema.json"
CONTRACT_SCHEMA = "endfield.jsondata-text-schema.v1"
SUPPORTED = frozenset({
    "AIConfig/AIGlobalSetting.json",
    "AIConfig/EnemyTemplateDataSummary.json",
    "GameplayConfigNpcProxyTable.json",
    "GameplayConfigScriptTaskExtraInfoTable.json",
    "InteractiveData/Collections.json",
    "LevelGenForRuntime/DoodadGroupTable.json",
    "LevelGenForRuntime/TotalFactoryRegions.json",
    "SpaceshipCabinData.json",
})
_fail = make_fail(JsonDataTextSchemaDecodeError)


def is_named_jsondata_text_path(relative: str) -> bool:
    return relative.replace("\\", "/") in SUPPORTED


@lru_cache(maxsize=1)
def _load_contract() -> dict[str, Any]:
    return load_schema_contract(
        CONTRACT_PATH,
        schema=CONTRACT_SCHEMA,
        error=JsonDataTextSchemaDecodeError,
        tables=SUPPORTED,
    )


def _relations(root: Any, relative: str, source: str) -> None:
    if relative == "AIConfig/EnemyTemplateDataSummary.json":
        for enemy_id, path in root["preloadEnemyTemplateId2Path"].items():
            if not path.endswith(f"/data_{enemy_id}.asset"):
                _fail(f"{source}.preloadEnemyTemplateId2Path[{enemy_id!r}]", f"*/data_{enemy_id}.asset", path)
    elif relative == "GameplayConfigNpcProxyTable.json":
        expected = ("Gameplay.Beyond", "Beyond.Gameplay.NpcRuntimeProxyDataTable")
        actual = (root["__AssemblyName__"], root["__TypeName__"])
        if actual != expected:
            _fail(source + ".typeIdentity", expected, actual)
    elif relative == "GameplayConfigScriptTaskExtraInfoTable.json":
        expected = ("Gameplay.Beyond", "Beyond.Gameplay.LevelScriptTaskExtraInfoTable")
        actual = (root["__AssemblyName__"], root["__TypeName__"])
        if actual != expected:
            _fail(source + ".typeIdentity", expected, actual)
    elif relative == "InteractiveData/Collections.json":
        for key, row in root.items():
            if len(row["totalCnt"]) != 33 or any(type(x) is not int for x in row["totalCnt"]):
                _fail(f"{source}[{key!r}].totalCnt", "33 integer collection counts", row["totalCnt"])
    elif relative == "LevelGenForRuntime/DoodadGroupTable.json":
        ids: set[int] = set()
        for rows in root.values():
            for row in rows:
                group_id = row["doodadGroupId"]
                if group_id in ids:
                    _fail(source + ".doodadGroupId", "globally unique", group_id)
                ids.add(group_id)
    elif relative == "LevelGenForRuntime/TotalFactoryRegions.json":
        ids = [row["regionId"] for row in root["regions"]]
        if len(ids) != len(set(ids)):
            _fail(source + ".regions.regionId", "unique", ids)


def decode_named_jsondata_text(data: bytes, *, source: str) -> dict[str, Any]:
    relative = source.replace("\\", "/")
    if relative not in SUPPORTED:
        _fail(source, "supported named text-table path", relative)
    root = parse_utf8_json(data, source=source, error=JsonDataTextSchemaDecodeError)
    table = _load_contract()["tables"][relative]
    counters = validate_document(root, table, source=source, error=JsonDataTextSchemaDecodeError)
    _relations(root, relative, source)
    return {
        "status": "named_exact",
        "schemaStatus": "named_exact",
        "wholeSchemaExact": True,
        "evidenceBoundary": "exact",
        **section_counts(table),
        **counters,
    }


__all__ = ["JsonDataTextSchemaDecodeError", "decode_named_jsondata_text", "is_named_jsondata_text_path"]
