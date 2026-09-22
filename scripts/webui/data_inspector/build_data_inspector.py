#!/usr/bin/env python3
"""Build lazy decoded-data datasets for the WebUI inspector.

The builder reuses maintained data-side readers. It publishes decoded records
and bounded summaries, while large exported Unity JSON stays in ``export_full``
and is fetched only when a user asks to inspect its raw source.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Iterable

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.webui.data_inspector.build_data_inspector"
    )

from scripts.common import OUT_DIR, require_export_layout
from scripts.game_data.animation_config_binary import (
    AnimationConfigFramingError,
    frame_animation_config,
)
from scripts.game_data.aether_energy_lock_binary import (
    AetherEnergyLockDecodeError,
    decode_aether_energy_lock_table,
)
from scripts.game_data.char_interact_perform_binary import (
    CharInteractPerformDecodeError,
    decode_char_interact_complete_frame,
    frame_char_interact_prefix,
)
from scripts.game_data.gameplay_compact_binary import (
    GameplayCompactDecodeError,
    decode_mission_area_table,
    frame_subgame_table,
    frame_world_entity_registry,
)
from scripts.game_data.schemas.gold_coin_config import (
    GoldCoinConfigDecodeError,
    decode_gold_coin_config,
)
from scripts.game_data.interactive_binary import (
    InteractiveBinaryDecodeError,
    decode_interactive_table,
)
from scripts.game_data.schemas.level_mount_point import (
    LevelMountPointJsonDecodeError,
    decode_level_mount_points,
)
from scripts.game_data.levelconfig_binary import (
    LevelConfigDecodeError,
    decode_level_config,
)
from scripts.game_data.matrix_shockwave_binary import (
    MatrixShockWaveDecodeError,
    decode_matrix_shockwave_table,
)
from scripts.game_data.memorypack.npc_montage import (
    NpcMontageFramingError,
    frame_npc_montage,
)
from scripts.game_data.memorypack.tables import (
    BAMBOO_RAFT_TASK_TABLE_REL,
    DIALOG_ID_TABLE_REL,
    decode_bamboo_raft_task_table_memorypack,
    decode_dialog_id_table_memorypack,
)
from scripts.game_data.navmesh_binary import (
    NavMeshDecodeError,
    decode_luna_area,
    decode_navmesh_state_container,
)
from scripts.game_data.teleport_validation_binary import (
    TeleportValidationDecodeError,
    decode_teleport_validation_table,
)
from scripts.source_paths import ExportLayout, configured_export_root
from scripts.webui.data_inspector.contract import (
    json_safe,
    publish_dataset,
    publish_root_index,
    source_descriptor,
)


DATASET_IDS = (
    "animation-config",
    "npc-montage",
    "animator-controller",
    "animator-override-controller",
    "level-config",
    "char-interact-perform",
    "navmesh",
    "level-mount-point",
    "config-table",
)
PUBLISHER_REVISION = 5
_HASH_KEY = re.compile(r"(?:hash|id)$", re.IGNORECASE)
_SKIP_HASH_KEYS = {"m_pathid", "m_fileid", "pathid", "fileid"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=configured_export_root())
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR / "data_inspector")
    parser.add_argument(
        "--dataset",
        action="append",
        choices=DATASET_IDS,
        help="Publish only this dataset; repeat for more than one (default: all).",
    )
    parser.add_argument("--shard-size", type=int, default=20)
    parser.add_argument("--force", action="store_true", help="Rebuild unchanged datasets.")
    return parser.parse_args(argv)


def _source(path: Path, export_root: Path, media_type: str) -> dict[str, Any]:
    return source_descriptor(path, export_root=export_root, media_type=media_type)


def _summary_text(parts: Iterable[Any]) -> str:
    return "; ".join(str(value) for value in parts if value not in (None, "", [], {}))


def _scalar_values(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): child
        for key, child in value.items()
        if child is None or isinstance(child, (str, int, float, bool))
    }


def _named_row_keys(value: Any) -> list[Any]:
    if not isinstance(value, dict) or not isinstance(value.get("rows"), list):
        return []
    return [
        row.get("key")
        for row in value["rows"]
        if isinstance(row, dict) and row.get("key") is not None
    ]


def _animation_config_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    try:
        decoded = frame_animation_config(path.read_bytes())
        fields = decoded.get("fields") if isinstance(decoded.get("fields"), dict) else {}
        extra_header = decoded.get("extraData") if isinstance(decoded.get("extraData"), dict) else {}
        extra = fields.get("extraData") if isinstance(fields.get("extraData"), dict) else {}
        montage = fields.get("montages") if isinstance(fields.get("montages"), dict) else {}
        sync_curves = fields.get("syncGroupCurves") if isinstance(fields.get("syncGroupCurves"), dict) else {}
        time_curves = fields.get("timeRefCurves") if isinstance(fields.get("timeRefCurves"), dict) else {}
        status = str(decoded.get("schemaStatus") or "partial")
        facts = {
            "controllerPath": fields.get("controllerPath"),
            "optControllerPath": fields.get("optControllerPath"),
            "retargetAnimConfigPath": fields.get("retargetAnimConfigPath"),
            "extraDataType": extra_header.get("subtype"),
            "extraDataFields": sorted(extra),
            "extraDataValues": _scalar_values(extra),
            "montageCount": montage.get("count", len(montage.get("rows") or [])),
            "montageNames": _named_row_keys(montage),
            "npcMontageCount": len(fields.get("npcMontages") or []),
            "syncGroupCurveCount": sync_curves.get("count"),
            "syncGroupCurveNames": _named_row_keys(sync_curves),
            "timeRefCurveCount": time_curves.get("count"),
            "timeRefCurveNames": _named_row_keys(time_curves),
        }
        tags = ["animation", "memorypack", status]
        if facts["extraDataType"]:
            tags.append(str(facts["extraDataType"]))
        return {
            "id": relative,
            "title": path.stem,
            "status": status,
            "summary": _summary_text((
                facts.get("extraDataType") or "no extra data",
                f"montages={facts['montageCount'] or 0}",
                f"curves={(facts['syncGroupCurveCount'] or 0) + (facts['timeRefCurveCount'] or 0)}",
            )),
            "tags": tags,
            "source": _source(path, export_root, "application/octet-stream"),
            "facts": facts,
            "payload": decoded,
            "payloadKind": "reader",
        }
    except (OSError, AnimationConfigFramingError, ValueError) as exc:
        return {
            "id": relative,
            "title": path.stem,
            "status": "decode_error",
            "summary": str(exc),
            "tags": ["animation", "memorypack", "decode_error"],
            "source": _source(path, export_root, "application/octet-stream"),
            "diagnostic": str(exc),
        }


def _npc_montage_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    try:
        decoded = frame_npc_montage(path.read_bytes())
        clip = decoded.get("clipInfo") if isinstance(decoded.get("clipInfo"), dict) else {}
        facts = {
            "clipName": clip.get("name"),
            "duration": clip.get("duration"),
            "animType": decoded.get("animType"),
            "tag": decoded.get("tag"),
            "dynamicEntityCount": decoded.get("dynamicEntityCount"),
            "transitionOverrideCount": decoded.get("transitionOverrideCount"),
            "frameRate": decoded.get("frameRate"),
        }
        status = str(decoded.get("schemaStatus") or decoded.get("status") or "decoded")
        return {
            "id": relative,
            "title": str(clip.get("name") or path.stem),
            "status": status,
            "summary": _summary_text((
                f"animType={facts['animType']}",
                f"tag={facts['tag']}",
                f"duration={facts['duration']}" if facts["duration"] is not None else "",
            )),
            "tags": ["animation", "montage", "memorypack", status],
            "source": _source(path, export_root, "application/octet-stream"),
            "facts": facts,
            "payload": decoded,
            "payloadKind": "reader",
        }
    except (OSError, NpcMontageFramingError, ValueError) as exc:
        return {
            "id": relative,
            "title": path.stem,
            "status": "decode_error",
            "summary": str(exc),
            "tags": ["animation", "montage", "memorypack", "decode_error"],
            "source": _source(path, export_root, "application/octet-stream"),
            "diagnostic": str(exc),
        }


# ---- exact single-schema families -------------------------------------------
#
# Each adapter below hands the file to the maintained reader that
# ``scripts.game_data.jsondata_corpus`` routes it to, and publishes that
# reader's own result unchanged as ``payload``. Status comes from the reader's
# reported framing, never from the adapter: a reader that fails closed on an
# unsupported variant produces a visible ``decode_error`` row rather than a
# missing one.


def _reader_status(decoded: dict[str, Any], default: str = "named_exact") -> str:
    return str(decoded.get("schemaStatus") or decoded.get("status") or default)


def _error_record(
    path: Path,
    export_root: Path,
    media_type: str,
    tags: list[str],
    exc: BaseException,
) -> dict[str, Any]:
    return {
        "id": path.relative_to(export_root).as_posix(),
        "title": path.stem,
        "status": "decode_error",
        "summary": str(exc),
        "tags": [*tags, "decode_error"],
        "source": _source(path, export_root, media_type),
        "diagnostic": str(exc),
    }


def _level_config_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    try:
        decoded = decode_level_config(path.read_bytes())
        status = _reader_status(decoded)
        facts = {
            "id": decoded.get("id"),
            "idNum": decoded.get("idNum"),
            "mapIdStr": decoded.get("mapIdStr"),
            "defaultState": decoded.get("defaultState"),
            "isSeamless": decoded.get("isSeamless"),
            "isDimensionLevel": decoded.get("isDimensionLevel"),
            "dimensionSourceLevelId": decoded.get("dimensionSourceLevelId"),
            "levelDataPathHashCount": len(decoded.get("levelDataPathHashes") or []),
            "levelGridCount": len(decoded.get("levelGrids") or []),
            "bytesConsumed": decoded.get("bytesConsumed"),
        }
        return {
            "id": relative,
            "title": str(decoded.get("id") or path.stem),
            "status": status,
            "summary": _summary_text((
                f"idNum={facts['idNum']}",
                f"map={facts['mapIdStr']}" if facts["mapIdStr"] else "",
                f"grids={facts['levelGridCount']}",
                f"levelData={facts['levelDataPathHashCount']}",
            )),
            "tags": ["level", "levelconfig", status],
            "source": _source(path, export_root, "application/octet-stream"),
            "facts": facts,
            "payload": decoded,
            "payloadKind": "reader",
        }
    except (OSError, LevelConfigDecodeError, ValueError) as exc:
        return _error_record(
            path, export_root, "application/octet-stream", ["level", "levelconfig"], exc
        )


def _char_interact_perform_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    tags = ["npc", "char-interact", "memorypack"]
    try:
        data = path.read_bytes()
    except OSError as exc:
        return _error_record(path, export_root, "application/octet-stream", tags, exc)
    try:
        decoded = decode_char_interact_complete_frame(data)
        bounded = False
    except (CharInteractPerformDecodeError, ValueError) as complete_exc:
        # The complete frame is the claim; the named prefix is the honest
        # fallback, and it is published as a bounded row rather than dropped.
        try:
            decoded = frame_char_interact_prefix(data)
            bounded = True
        except (CharInteractPerformDecodeError, ValueError):
            return _error_record(
                path, export_root, "application/octet-stream", tags, complete_exc
            )
    status = _reader_status(decoded, "bounded_partial" if bounded else "named_exact")
    facts = {
        "actionCount": decoded.get("actionCount"),
        "actionTypeCounts": decoded.get("actionTypeCounts"),
        "audioActionCount": decoded.get("audioActionCount"),
        "wholeSchemaExact": decoded.get("wholeSchemaExact"),
        "schemaMappingId": decoded.get("schemaMappingId"),
        "unionMappingId": decoded.get("unionMappingId"),
        "bytesConsumed": decoded.get("bytesConsumed"),
    }
    return {
        "id": relative,
        "title": path.stem,
        "status": status,
        "summary": _summary_text((
            f"actions={facts['actionCount']}" if facts["actionCount"] is not None else "",
            f"audio={facts['audioActionCount']}" if facts["audioActionCount"] is not None else "",
            "named prefix only" if bounded else "",
        )),
        "tags": [*tags, status],
        "source": _source(path, export_root, "application/octet-stream"),
        "facts": facts,
        "payload": decoded,
        "payloadKind": "reader",
    }


_NAVMESH_READERS = {
    "LunaArea.json": (decode_luna_area, "luna-area"),
    "NavMeshStateContainer.json": (decode_navmesh_state_container, "state-container"),
}


def _navmesh_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    entry = _NAVMESH_READERS.get(path.name)
    if entry is None:
        return {
            "id": relative,
            "title": f"{path.parent.name} / {path.stem}",
            "status": "unsupported",
            "summary": "no maintained NavMesh reader routes this filename",
            "tags": ["world", "navmesh", "unsupported"],
            "source": _source(path, export_root, "application/octet-stream"),
        }
    reader, kind = entry
    try:
        decoded = reader(path.read_bytes())
        status = _reader_status(decoded)
        facts = {
            "level": path.parent.name,
            "areaCount": decoded.get("areaCount"),
            "counts": decoded.get("counts"),
            "bytesConsumed": decoded.get("bytesConsumed"),
        }
        return {
            "id": relative,
            "title": f"{path.parent.name} / {path.stem}",
            "status": status,
            "summary": _summary_text((
                path.parent.name,
                f"areas={facts['areaCount']}" if facts["areaCount"] is not None else "",
            )),
            "tags": ["world", "navmesh", kind, status],
            "source": _source(path, export_root, "application/octet-stream"),
            "facts": facts,
            "payload": decoded,
            "payloadKind": "reader",
        }
    except (OSError, NavMeshDecodeError, ValueError) as exc:
        return _error_record(
            path, export_root, "application/octet-stream", ["world", "navmesh", kind], exc
        )


def _level_mount_point_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    # The reader authenticates the family from its own Json-relative path.
    source = f"LevelMountPoint/{path.name}"
    try:
        decoded = decode_level_mount_points(path.read_bytes(), source=source)
        status = _reader_status(decoded)
        return {
            "id": relative,
            "title": path.stem,
            "status": status,
            "summary": _summary_text((
                f"roots={decoded.get('rootTypeCount')}",
                f"mountPoints={decoded.get('mountPointCount')}",
                f"teleports={decoded.get('teleportCount')}",
            )),
            "tags": ["level", "mount-point", status],
            "source": _source(path, export_root, "application/json"),
            "facts": {
                key: value
                for key, value in decoded.items()
                if key not in {"status", "schemaStatus"}
            },
            "payload": decoded,
            "payloadKind": "reader",
        }
    except (OSError, LevelMountPointJsonDecodeError, ValueError) as exc:
        return _error_record(
            path, export_root, "application/json", ["level", "mount-point"], exc
        )


def _teleport_validation(data: bytes) -> Any:
    return decode_teleport_validation_table(data)


def _dialog_id_table(data: bytes) -> Any:
    return decode_dialog_id_table_memorypack(DIALOG_ID_TABLE_REL, data, len(data))


def _bamboo_raft_table(data: bytes) -> Any:
    return decode_bamboo_raft_task_table_memorypack(
        BAMBOO_RAFT_TASK_TABLE_REL, data, len(data)
    )


# Single-instance config tables, each with its own exact reader. The key is the
# path relative to the export's Json root, which is also what routes the reader
# in ``scripts.game_data.jsondata_corpus``.
CONFIG_TABLE_READERS: dict[str, tuple[Callable[[bytes], Any], str, str]] = {
    "GameplayConfig/CinematicTeleportValidationDataTable.json": (
        _teleport_validation, "teleport-validation", "gameplay"),
    "GameplayConfig/CommonSysTeleportValidationDataTable.json": (
        _teleport_validation, "teleport-validation", "gameplay"),
    "GameplayConfig/GuideTeleportValidationDataTable.json": (
        _teleport_validation, "teleport-validation", "gameplay"),
    "GameplayConfig/LevelScriptTeleportValidationDataTable.json": (
        _teleport_validation, "teleport-validation", "gameplay"),
    "GameplayConfig/MapTeleportValidationDataTable.json": (
        _teleport_validation, "teleport-validation", "gameplay"),
    "GameplayConfig/AetherEnergyLockConfigTable.json": (
        decode_aether_energy_lock_table, "aether-energy-lock", "gameplay"),
    "GameplayConfig/DialogIdTable.json": (_dialog_id_table, "dialog-id", "story"),
    "NonGeneratedConfigs/MatrixShockWaveBeatConfigTable.json": (
        decode_matrix_shockwave_table, "matrix-shockwave", "gameplay"),
    "NonGeneratedConfigs/BambooRaftTaskTable.json": (
        _bamboo_raft_table, "bamboo-raft", "gameplay"),
    "NonGeneratedConfigs/GoldCoinConfigTable.json": (
        decode_gold_coin_config, "gold-coin", "gameplay"),
    "GameplayConfigMissionAreaTable.json": (
        decode_mission_area_table, "mission-area", "gameplay"),
    "GameplayConfigSubGameInstanceDataTable.json": (
        frame_subgame_table, "subgame-instance", "gameplay"),
    "GameplayConfigWorldEntityRegistry.json": (
        frame_world_entity_registry, "world-entity-registry", "gameplay"),
    "Interactive/InteractiveTable.json": (
        decode_interactive_table, "interactive-table", "gameplay"),
}

_TABLE_ERRORS = (
    OSError,
    AetherEnergyLockDecodeError,
    GameplayCompactDecodeError,
    GoldCoinConfigDecodeError,
    InteractiveBinaryDecodeError,
    MatrixShockWaveDecodeError,
    TeleportValidationDecodeError,
    TypeError,
    ValueError,
)


def _config_table_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    json_relative = relative.split("game/Json/", 1)[-1]
    entry = CONFIG_TABLE_READERS.get(json_relative)
    if entry is None:
        return {
            "id": relative,
            "title": path.stem,
            "status": "unsupported",
            "summary": "no maintained exact reader routes this table",
            "tags": ["config-table", "unsupported"],
            "source": _source(path, export_root, "application/octet-stream"),
        }
    reader, kind, lane = entry
    tags = ["config-table", kind, lane]
    try:
        decoded = reader(path.read_bytes())
        if decoded is None:
            raise ValueError("current exact table reader rejected payload")
        # The MemoryPack table readers report exactness under `decoded`, while
        # the binary table readers report it as their own framing status.
        nested = decoded.get("decoded") if isinstance(decoded.get("decoded"), dict) else {}
        if nested:
            status = "named_exact" if nested.get("exactLength") is True else "bounded_partial"
        else:
            status = _reader_status(decoded)
        facts = {
            key: value
            for key, value in decoded.items()
            if key not in {"status", "schemaStatus", "decoded", "rows", "sample", "keys"}
        }
        rows = decoded.get("rows")
        if isinstance(rows, int):
            facts["rows"] = rows
        elif isinstance(rows, list):
            facts["rowCount"] = len(rows)
        return {
            "id": relative,
            "title": path.stem,
            "status": status,
            "summary": _summary_text((
                str(decoded.get("summary") or "")[:160],
                f"rows={decoded.get('rowCount')}" if decoded.get("rowCount") is not None else "",
                f"entries={decoded.get('entryCount')}" if decoded.get("entryCount") is not None else "",
            )) or kind,
            "tags": [*tags, status],
            "source": _source(path, export_root, "application/octet-stream"),
            "facts": facts,
            "payload": decoded,
            "payloadKind": "reader",
        }
    except _TABLE_ERRORS as exc:
        return _error_record(path, export_root, "application/octet-stream", tags, exc)


def _walk(value: Any, path: str = "") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if child_path == "$animestudio.typeTreeFieldPaths":
                continue
            yield child_path, str(key), child
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _controller_facts(payload: dict[str, Any]) -> dict[str, Any]:
    controller = payload.get("m_Controller") if isinstance(payload.get("m_Controller"), dict) else {}
    string_table = [str(value) for value in payload.get("m_TOSData") or [] if str(value)]
    hashes: dict[str, set[Any]] = defaultdict(set)
    hash_occurrences = 0
    conditions: Counter[tuple[Any, Any, Any, Any]] = Counter()
    curve_scalar_values: dict[str, set[Any]] = defaultdict(set)
    curve_collection_sizes: dict[str, Counter[int]] = defaultdict(Counter)
    state_count = transition_count = 0
    for path, key, value in _walk(controller, "m_Controller"):
        folded = key.casefold()
        if (
            isinstance(value, (int, float, str))
            and folded not in _SKIP_HASH_KEYS
            and _HASH_KEY.search(key)
        ):
            hashes[key].add(value)
            hash_occurrences += 1
        if key == "m_StateConstantArray" and isinstance(value, list):
            state_count += len(value)
        elif key in {"m_TransitionConstantArray", "m_AnyStateTransitionConstantArray"} and isinstance(value, list):
            transition_count += len(value)
        if isinstance(value, dict) and {"m_ConditionMode", "m_EventID"}.issubset(value):
            conditions[(
                value.get("m_ConditionMode"),
                value.get("m_EventID"),
                value.get("m_EventThreshold"),
                value.get("m_ExitTime"),
            )] += 1
        if "curve" in folded:
            if isinstance(value, (list, dict)):
                curve_collection_sizes[key][len(value)] += 1
            elif isinstance(value, (int, float, str, bool)) or value is None:
                curve_scalar_values[key].add(value)
    condition_rows = [
        {
            "mode": key[0],
            "eventId": key[1],
            "threshold": key[2],
            "exitTime": key[3],
            "occurrences": count,
        }
        for key, count in sorted(conditions.items(), key=lambda item: tuple(str(value) for value in item[0]))
    ]
    curve_fields: dict[str, dict[str, Any]] = {}
    for key in sorted({*curve_scalar_values, *curve_collection_sizes}):
        row: dict[str, Any] = {}
        values = curve_scalar_values.get(key)
        if values:
            row["values"] = sorted(values, key=lambda value: str(value))
        sizes = curve_collection_sizes.get(key)
        if sizes:
            row["collectionSizeHistogram"] = {
                str(size): count for size, count in sorted(sizes.items())
            }
        curve_fields[key] = row
    unique_strings = list(dict.fromkeys(string_table))
    return {
        "controllerSize": payload.get("m_ControllerSize"),
        "layerCount": len(controller.get("m_LayerArray") or []),
        "stateMachineCount": len(controller.get("m_StateMachineArray") or []),
        "stateCount": state_count,
        "transitionCount": transition_count,
        "conditionCount": sum(conditions.values()),
        "distinctConditionCount": len(conditions),
        "clipReferenceCount": len(payload.get("m_AnimationClips") or []),
        "hashCount": sum(len(values) for values in hashes.values()),
        "hashOccurrenceCount": hash_occurrences,
        "hashesByField": {
            key: sorted(values, key=lambda value: str(value))
            for key, values in sorted(hashes.items())
        },
        "conditions": condition_rows,
        "stringTable": unique_strings,
        "idleNames": [value for value in unique_strings if "idle" in value.casefold()],
        "curveFields": curve_fields,
    }


def _animator_controller_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("controller JSON root is not an object")
        facts = _controller_facts(payload)
        metadata = payload.get("$animestudio") if isinstance(payload.get("$animestudio"), dict) else {}
        compact_metadata = {
            key: metadata.get(key)
            for key in (
                "pathId", "type", "classId", "name", "sourceFile", "sourceOffset",
                "byteSize", "rawDataLength", "rawDataSha256", "typeTreeSource",
                "typeTreeNodeCount",
            )
            if key in metadata
        }
        return {
            "id": relative,
            "title": str(payload.get("m_Name") or path.stem),
            "status": "decoded_unity_json",
            "summary": _summary_text((
                f"layers={facts['layerCount']}",
                f"states={facts['stateCount']}",
                f"conditions={facts['conditionCount']}",
                f"hashes={facts['hashCount']}",
            )),
            "tags": ["animation", "controller", "unity-json"],
            "source": _source(path, export_root, "application/json"),
            "facts": facts,
            "payload": {
                "animestudio": compact_metadata,
                "name": payload.get("m_Name"),
                "multiThreadedStateMachine": payload.get("m_MultiThreadedStateMachine"),
                "clothCalculatorType": payload.get("m_ClothCalculatorType"),
                "enableOptClipBindings": payload.get("m_EnableOptClipBindings"),
            },
            "payloadKind": "projection",
        }
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "id": relative,
            "title": path.stem,
            "status": "decode_error",
            "summary": str(exc),
            "tags": ["animation", "controller", "decode_error"],
            "source": _source(path, export_root, "application/json"),
            "diagnostic": str(exc),
        }


def _animator_override_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("override-controller JSON root is not an object")
        overrides = payload.get("m_Clips") if isinstance(payload.get("m_Clips"), list) else []
        controller = payload.get("m_Controller") if isinstance(payload.get("m_Controller"), dict) else {}
        facts = {
            "controller": controller,
            "overrideCount": len(overrides),
            "nullOverrideCount": sum(
                1 for row in overrides
                if isinstance(row, dict)
                and isinstance(row.get("m_OverrideClip"), dict)
                and row["m_OverrideClip"].get("IsNull") is True
            ),
        }
        return {
            "id": relative,
            "title": str(payload.get("m_Name") or path.stem),
            "status": "decoded_unity_json",
            "summary": f"overrides={facts['overrideCount']}; null={facts['nullOverrideCount']}",
            "tags": ["animation", "controller-override", "unity-json"],
            "source": _source(path, export_root, "application/json"),
            "facts": facts,
            "payload": {
                "animestudio": payload.get("$animestudio"),
                "name": payload.get("m_Name"),
                "controller": controller,
                "clips": overrides,
            },
            "payloadKind": "projection",
        }
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "id": relative,
            "title": path.stem,
            "status": "decode_error",
            "summary": str(exc),
            "tags": ["animation", "controller-override", "decode_error"],
            "source": _source(path, export_root, "application/json"),
            "diagnostic": str(exc),
        }


def _all_json(root: Path) -> list[Path]:
    """Default selector: every JSON file under a family's own directory."""

    return sorted(root.rglob("*.json"))


def _named_files(names: Iterable[str]) -> Callable[[Path], list[Path]]:
    """Selector for a fixed set of root-relative files, skipping absent ones.

    A dataset built from single-instance tables must not silently change shape
    when the client drops or renames one, so the caller's order is preserved and
    a missing file is simply absent rather than an error here; the dataset's own
    record count and the input signature both move when that happens.
    """

    def select(root: Path) -> list[Path]:
        return [path for path in (root / name for name in names) if path.is_file()]

    return select


def _build_records(
    root: Path,
    export_root: Path,
    reader: Callable[[Path, Path], dict[str, Any]],
    selector: Callable[[Path], list[Path]],
) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    return [reader(path, export_root) for path in selector(root)]


def _input_signature(root: Path, selector: Callable[[Path], list[Path]]) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = 0
    total_bytes = 0
    latest_mtime_ns = 0
    if root.is_dir():
        for path in selector(root):
            stat = path.stat()
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(b"\0")
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
            digest.update(b"\n")
            count += 1
            total_bytes += stat.st_size
            latest_mtime_ns = max(latest_mtime_ns, stat.st_mtime_ns)
    return {
        "algorithm": "relative-path-size-mtime-ns-sha256",
        "sha256": digest.hexdigest(),
        "files": count,
        "bytes": total_bytes,
        "latestMtimeNs": latest_mtime_ns,
    }


def _reusable_descriptor(
    out_dir: Path,
    dataset_id: str,
    input_signature: dict[str, Any],
    shard_size: int,
) -> dict[str, Any] | None:
    path = out_dir / "datasets" / dataset_id / "index.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    provenance = manifest.get("provenance") if isinstance(manifest.get("provenance"), dict) else {}
    # Compare against the signature as it was written: publication rewrites an
    # integer outside JavaScript's exact range as a decimal string, and
    # `latestMtimeNs` is always outside it, so an unnormalized comparison never
    # matches and the cache silently rebuilds every dataset on every run.
    if (
        provenance.get("inputSignature") != json_safe(input_signature)
        or provenance.get("publisherRevision") != PUBLISHER_REVISION
        or manifest.get("shardSize") != shard_size
    ):
        return None
    for shard in manifest.get("shards") or []:
        if not (path.parent / str(shard.get("path") or "")).is_file():
            return None
    return _descriptor_from_manifest(dataset_id, manifest)


def _existing_descriptor(out_dir: Path, dataset_id: str) -> dict[str, Any] | None:
    path = out_dir / "datasets" / dataset_id / "index.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    for shard in manifest.get("shards") or []:
        if not (path.parent / str(shard.get("path") or "")).is_file():
            return None
    return _descriptor_from_manifest(dataset_id, manifest)


def _descriptor_from_manifest(dataset_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": manifest.get("id"),
        "title": manifest.get("title"),
        "description": manifest.get("description"),
        "available": manifest.get("available") is True,
        "diagnostic": str(manifest.get("diagnostic") or ""),
        "recordCount": int(manifest.get("recordCount") or 0),
        "statusCounts": manifest.get("statusCounts") or {},
        "path": f"datasets/{dataset_id}/index.json",
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_export_layout(args.export_root)
    layout = ExportLayout(args.export_root)
    selected = set(args.dataset or DATASET_IDS)
    specs = {
        "animation-config": (
            "Animation configs",
            "Decoded AnimationConfig records: controller hashes, extra-data type, montages, and curves.",
            layout.json_dir / "AnimationConfig",
            _animation_config_record,
            _all_json,
        ),
        "npc-montage": (
            "NPC montages",
            "Decoded NPC montage records with clip, transition, entity, and framing evidence.",
            layout.json_dir / "NPC" / "MontageJson" / "MontageNew",
            _npc_montage_record,
            _all_json,
        ),
        "animator-controller": (
            "Animator controllers",
            "Controller layers, states, conditions, hashes, string tables, and raw exported JSON.",
            layout.unity_type_dir("AnimatorController"),
            _animator_controller_record,
            _all_json,
        ),
        "animator-override-controller": (
            "Animator override controllers",
            "Controller and clip override references with raw exported JSON.",
            layout.unity_type_dir("AnimatorOverrideController"),
            _animator_override_record,
            _all_json,
        ),
        "level-config": (
            "Level configs",
            "Complete LevelConfig schema: level identity, map id, seamless and dimension flags, "
            "level-data path hashes, and level grids.",
            layout.json_dir / "LevelConfig",
            _level_config_record,
            _all_json,
        ),
        "char-interact-perform": (
            "Character interact performances",
            "Complete CharInteractPerform frames: the typed action union, per-type counts, "
            "audio actions, and the contract that names them.",
            layout.json_dir / "CharInteractPerformCfgs",
            _char_interact_perform_record,
            _all_json,
        ),
        "navmesh": (
            "NavMesh areas and states",
            "Per-level LunaArea containers and NavMeshStateContainer fields, framed to EOF.",
            layout.json_dir / "NavMesh",
            _navmesh_record,
            _all_json,
        ),
        "level-mount-point": (
            "Level mount points",
            "Validated LevelMountPoint trees: sub-root types, node and mount-point counts, "
            "teleports, and tree depth.",
            layout.json_dir / "LevelMountPoint",
            _level_mount_point_record,
            _all_json,
        ),
        "config-table": (
            "Exact config tables",
            "Single-instance config tables with their own exact readers: teleport validation, "
            "dialog ids, aether-energy locks, mission areas, the world-entity registry, and more.",
            layout.json_dir,
            _config_table_record,
            _named_files(CONFIG_TABLE_READERS),
        ),
    }

    descriptors: list[dict[str, Any]] = []
    for dataset_id in DATASET_IDS:
        if dataset_id not in selected:
            descriptor = _existing_descriptor(args.out_dir, dataset_id)
            if descriptor is not None:
                descriptors.append(descriptor)
            continue
        title, description, root, reader, selector = specs[dataset_id]
        available = root.is_dir()
        diagnostic = "" if available else f"missing source directory: {root}"
        input_signature = _input_signature(root, selector)
        descriptor = None if args.force else _reusable_descriptor(
            args.out_dir, dataset_id, input_signature, args.shard_size
        )
        if descriptor is not None:
            descriptors.append(descriptor)
            print(f"{dataset_id}: reused {descriptor['recordCount']} unchanged records")
            continue
        records = _build_records(root, args.export_root, reader, selector) if available else []
        descriptor = publish_dataset(
            args.out_dir,
            dataset_id=dataset_id,
            title=title,
            description=description,
            records=records,
            provenance={
                "exportLayout": "endfield.export-layout.v2",
                "sourceRoot": root.relative_to(args.export_root).as_posix(),
                "reader": f"{reader.__module__}.{reader.__name__}",
                "publisherRevision": PUBLISHER_REVISION,
                "inputSignature": input_signature,
            },
            shard_size=args.shard_size,
            available=available,
            diagnostic=diagnostic,
        )
        descriptors.append(descriptor)
        print(
            f"{dataset_id}: {descriptor['recordCount']} records "
            f"({', '.join(f'{key}={value}' for key, value in descriptor['statusCounts'].items())})"
        )
    path = publish_root_index(args.out_dir, descriptors)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
