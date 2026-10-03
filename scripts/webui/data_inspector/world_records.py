"""Data-page records from maintained SpawnerConfig and atmospheric NPC readers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from scripts.game_data.atmospheric_npc_binary import frame_atmospheric_npc_table
from scripts.game_data.spawner_binary import frame_spawner_named
from scripts.game_data.schemas.map_config import decode_map_config
from scripts.webui.data_inspector.contract import source_descriptor


def _record(
    path: Path, export_root: Path, *, reader: Callable[[bytes], dict[str, Any]],
    family: str, fact_keys: tuple[str, ...], media_type: str = "application/octet-stream",
) -> dict[str, Any]:
    base = {
        "id": path.relative_to(export_root).as_posix(), "title": path.stem,
        "source": source_descriptor(path, export_root=export_root, media_type=media_type),
        "tags": ["world", family, "memorypack"],
    }
    try:
        decoded = reader(path.read_bytes())
    except (OSError, ValueError) as exc:
        return {
            **base, "status": "decode_error", "summary": str(exc)[:1200],
            "tags": [*base["tags"], "decode_error"], "diagnostic": str(exc)[:1200],
        }
    status = str(decoded.get("schemaStatus") or decoded.get("status") or "bounded_partial")
    facts = {key: decoded[key] for key in fact_keys if key in decoded}
    open_field = decoded.get("openField")
    if isinstance(open_field, dict):
        facts["openField"] = open_field.get("name")
    return {
        **base, "status": status,
        "summary": ", ".join(f"{key}={value}" for key, value in facts.items()),
        "tags": [*base["tags"], status], "facts": facts,
        "diagnostic": decoded.get("diagnostic"),
        "payload": decoded, "payloadKind": "reader",
    }


def spawner_record(path: Path, export_root: Path) -> dict[str, Any]:
    return _record(
        path, export_root, reader=frame_spawner_named, family="spawner",
        fact_keys=("configId", "enemyLibraryCount", "routeMapCount", "waveCount", "bytesConsumed"),
    )


def atmospheric_npc_record(path: Path, export_root: Path) -> dict[str, Any]:
    return _record(
        path, export_root, reader=frame_atmospheric_npc_table, family="atmospheric-npc",
        fact_keys=("entryCount", "namedNpcRuntimeProxyCount", "namedLevelEntityPrefixCount", "bytesConsumed"),
    )


def map_config_record(path: Path, export_root: Path) -> dict[str, Any]:
    return _record(
        path, export_root, reader=lambda raw: decode_map_config(raw, source=path.name), family="map-config",
        fact_keys=("levelCount", "sceneStateCount", "conditionCount", "mapVariableCount"),
        media_type="application/json",
    )
