"""Byte-pinned named schemas for polymorphic GameplayConfig JSON tables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.jsondata_named_schema import (
    load_schema_contract,
    make_fail,
    parse_utf8_json,
    section_counts,
    validate_document,
)


class GameplayConfigPolymorphicDecodeError(ValueError):
    pass


CONTRACT_PATH = Path(__file__).with_name("gameplay_config_polymorphic_schema.json")
CONTRACT_SHA256 = "20383F5EFBD4B6D19F14174D555933C447EC03960985FB2B729A974A4A4F6453"
CONTRACT_SCHEMA = "endfield.gameplay-config-polymorphic-json-schema.v1"
PREFIX = "GameplayConfig/"
SUPPORTED = frozenset({
    "ForbidByGameplayTagTable.json",
    "GameModeTable.json",
    "LevelMapMark.json",
    "ScriptTaskExtraInfoTable.json",
    "SubGameInstanceDataTable.json",
})
_fail = make_fail(GameplayConfigPolymorphicDecodeError)


def is_polymorphic_gameplay_config_path(relative: str) -> bool:
    path = PurePosixPath(relative.replace("\\", "/"))
    return len(path.parts) == 2 and path.parts[0] == "GameplayConfig" and path.name in SUPPORTED


@lru_cache(maxsize=1)
def _load_contract() -> dict[str, Any]:
    return load_schema_contract(
        CONTRACT_PATH,
        sha256=CONTRACT_SHA256,
        schema=CONTRACT_SCHEMA,
        error=GameplayConfigPolymorphicDecodeError,
        tables=SUPPORTED,
    )


def _validate_relations(root: Any, name: str, source: str) -> None:
    if name == "GameModeTable.json":
        if not isinstance(root, dict):
            _fail(source, "game-mode dictionary", type(root).__name__)
        for key, row in root.items():
            if not isinstance(row, dict) or row.get("modeId") != key:
                _fail(f"{source}[{key!r}].modeId", key, row.get("modeId") if isinstance(row, dict) else type(row).__name__)


def decode_polymorphic_gameplay_config(
    data: bytes, *, source: str
) -> dict[str, Any]:
    normalized = source.replace("\\", "/")
    if not is_polymorphic_gameplay_config_path(normalized):
        _fail(source, "supported polymorphic GameplayConfig path", normalized)
    name = PurePosixPath(normalized).name
    root = parse_utf8_json(data, source=source, error=GameplayConfigPolymorphicDecodeError)
    table = _load_contract()["tables"][name]
    counters = validate_document(root, table, source=source, error=GameplayConfigPolymorphicDecodeError)
    _validate_relations(root, name, source)
    return {
        "status": "named_exact",
        "schemaStatus": "named_exact",
        "wholeSchemaExact": True,
        "evidenceBoundary": "exact",
        "tableKind": name.removesuffix(".json"),
        **section_counts(table),
        **counters,
    }


__all__ = [
    "GameplayConfigPolymorphicDecodeError",
    "decode_polymorphic_gameplay_config",
    "is_polymorphic_gameplay_config_path",
]
