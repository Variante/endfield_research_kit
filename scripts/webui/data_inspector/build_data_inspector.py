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
import struct
from typing import Any, Callable, Iterable

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.webui.data_inspector.build_data_inspector"
    )

from scripts.common import OUT_DIR, ROOT, check_installed_native_inputs, require_export_layout
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
from scripts.game_data.leveldata_binary import (
    LevelDataTopLevelFramingError,
    frame_leveldata_named_prefix,
)
from scripts.game_data.matrix_shockwave_binary import (
    MatrixShockWaveDecodeError,
    decode_matrix_shockwave_table,
)
from scripts.game_data.memorypack.npc_montage import (
    NpcMontageFramingError,
    frame_npc_montage,
)
from scripts.game_data.memorypack.buff_actions import Unsupported
from scripts.game_data.memorypack.derived_plans import SKILLDATA_TYPE, load_registry
from scripts.game_data.memorypack.derived_values import decode_file, find_identifier
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
    decode_teleport_validation_json_table,
    decode_teleport_validation_table,
)
from scripts.game_data.unity_store import UnityObjectStore, open_store, open_store_if_present, split_logical_ref
from scripts.source_paths import EXPORT_LAYOUT_SCHEMA, ExportLayout, configured_export_root
from scripts.webui.data_inspector.contract import (
    json_safe,
    publish_dataset,
    publish_root_index,
    source_descriptor,
)
from scripts.webui.data_inspector.buff_action_receipts import load_receipt_records


DATASET_IDS = (
    "animation-config",
    "npc-montage",
    "animator-controller",
    "animator-override-controller",
    "level-config",
    "level-data",
    "skill-data",
    "buff-action-receipts",
    "char-interact-perform",
    "navmesh",
    "level-mount-point",
    "config-table",
)
PUBLISHER_REVISION = 9
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
    parser.add_argument(
        "--buff-action-receipts-report", type=Path,
        default=ROOT / "reports/animestudio/buff_action_receipts_current_latest.json",
    )
    parser.add_argument(
        "--buff-corpus-report", type=Path,
        default=ROOT / "reports/animestudio/buffdata_current_latest.json",
    )
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


def _level_data_record(path: Path, export_root: Path) -> dict[str, Any]:
    """Publish the maintained LevelData reader's exact or bounded result.

    A decoded spline is stored geometry. Its presence does not establish a
    movement route, scene instance, or runtime traversal.
    """
    relative = path.relative_to(export_root).as_posix()
    tags = ["level", "leveldata", "memorypack"]
    try:
        decoded = frame_leveldata_named_prefix(path.read_bytes())
    except (OSError, LevelDataTopLevelFramingError, ValueError) as exc:
        return _error_record(path, export_root, "application/octet-stream", tags, exc)

    status = _reader_status(decoded, "bounded_partial")
    fields = decoded.get("fields") if isinstance(decoded.get("fields"), dict) else {}
    splines = fields.get("splines") if isinstance(fields.get("splines"), dict) else {}
    open_field = decoded.get("openField") if isinstance(decoded.get("openField"), dict) else {}
    spline_count = splines.get("count") if isinstance(splines.get("count"), int) else None
    spline_rows = splines.get("rows") if isinstance(splines.get("rows"), list) else None
    knot_counts = [
        row.get("knots", {}).get("count") if isinstance(row, dict)
        and isinstance(row.get("knots"), dict) else None
        for row in spline_rows or []
    ]
    knot_count = sum(knot_counts) if (
        spline_count is not None and spline_count >= 0
        and spline_rows is not None and len(spline_rows) == spline_count
        and all(type(count) is int and count >= 0 for count in knot_counts)
    ) else None
    facts = {
        "level": path.parent.name,
        "closedFieldCount": len(decoded.get("closedFields") or []),
        "serializedMemberCount": decoded.get("serializedMemberCount"),
        "openField": open_field.get("name"),
        "bytesConsumed": decoded.get("bytesConsumed"),
    }
    if spline_count is not None:
        facts["splineCount"] = spline_count
    if knot_count is not None:
        facts["knotCount"] = knot_count
    return {
        "id": relative,
        "title": f"{path.parent.name} / {path.stem}",
        "status": status,
        "summary": _summary_text((
            f"fields={facts['closedFieldCount']}/{facts['serializedMemberCount']}",
            f"splines={spline_count}" if spline_count is not None else "",
            f"knots={knot_count}" if knot_count is not None and spline_count else "",
            f"open={facts['openField']}" if facts["openField"] else "",
        )),
        "tags": [
            *tags, status,
            *(["has-splines"] if spline_count and spline_count > 0 else []),
            *(["has-knots"] if knot_count and knot_count > 0 else []),
        ],
        "source": _source(path, export_root, "application/octet-stream"),
        "facts": facts,
        "payload": decoded,
        "payloadKind": "reader",
    }


def _skill_data_reference_targets(paths: Iterable[Path], export_root: Path) -> dict[str, list[str]]:
    """Index exact filename stems; duplicates stay ambiguous, never guessed."""
    targets: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        targets[path.stem].append(path.relative_to(export_root).as_posix())
    return dict(targets)


def _skill_data_stored_references(
    value: dict[str, Any], targets: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Walk nested actions once, projecting only exact-tag/type authored IDs."""
    max_depth = 64
    max_nodes = 250_000
    references: list[dict[str, Any]] = []
    stack: list[tuple[Any, str, int, bool]] = [(value, "", 0, False)]
    nodes = 0
    while stack:
        node, path, depth, skip_projected_ids = stack.pop()
        nodes += 1
        if nodes > max_nodes or depth > max_depth:
            raise ValueError(
                f"SkillData stored-reference traversal limit at {path or '<root>'}: "
                f"nodes={nodes}/{max_nodes}, depth={depth}/{max_depth}"
            )
        if isinstance(node, dict):
            exact_action = node.get("$tag") == 0x000E and (
                node.get("$type") == "Beyond.Gameplay.Core.AllowNextSkillAction+Data"
            )
            data = node.get("$value") if exact_action else None
            allowed = data.get("allowedSkillIdList") if isinstance(data, dict) else None
            if isinstance(allowed, list):
                for id_index, stored_id in enumerate(allowed):
                    if not isinstance(stored_id, str) or not stored_id:
                        continue
                    matches = targets.get(stored_id, [])
                    references.append({
                        "kind": "storedAllowedSkillId",
                        "sourcePath": f"{path}.$value.allowedSkillIdList[{id_index}]",
                        "storedId": stored_id,
                        "targetDatasetId": "skill-data",
                        "targetRecordId": matches[0] if len(matches) == 1 else None,
                        "targetState": (
                            "present" if len(matches) == 1 else
                            "ambiguous" if matches else "absent"
                        ),
                    })
            for key, child in reversed(list(node.items())):
                if skip_projected_ids and key == "allowedSkillIdList":
                    continue
                child_path = f"{path}.{key}" if path else str(key)
                stack.append((child, child_path, depth + 1, exact_action and key == "$value"))
        elif isinstance(node, list):
            for index in range(len(node) - 1, -1, -1):
                stack.append((node[index], f"{path}[{index}]", depth + 1, False))
    return references


def _skill_data_direct_action_types(value: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Count direct stored action unions without assigning runtime behavior.

    Nested branch actions remain in the reader payload, but are outside this
    inventory. An unfamiliar container shape withholds the whole projection.
    """
    group = value.get("actionGroupData")
    if not isinstance(group, dict):
        return None
    timeline = group.get("timelineActions")
    passive = group.get("passiveEventActions")
    if not isinstance(timeline, list) or not isinstance(passive, list):
        return None
    counts: dict[tuple[int, str], list[int]] = defaultdict(lambda: [0, 0])

    def add_actions(actions: Any, lane: int) -> bool:
        if not isinstance(actions, list):
            return False
        for action in actions:
            if not isinstance(action, dict):
                return False
            tag, name = action.get("$tag"), action.get("$type")
            if type(tag) is not int or not isinstance(name, str) or not name:
                return False
            counts[(tag, name)][lane] += 1
        return True

    for slot in timeline:
        sequence = slot.get("_sequenceActionData") if isinstance(slot, dict) else None
        if not isinstance(sequence, dict) or not add_actions(sequence.get("actionData"), 0):
            return None
    for event in passive:
        groups = event.get("actions") if isinstance(event, dict) else None
        if not isinstance(groups, list):
            return None
        for action_group in groups:
            if not isinstance(action_group, dict) or not add_actions(action_group.get("actionData"), 1):
                return None
    return [
        {
            "tag": tag,
            "type": name,
            "timelineOccurrences": lanes[0],
            "passiveEventOccurrences": lanes[1],
        }
        for (tag, name), lanes in sorted(counts.items(), key=lambda item: (item[0][1], item[0][0]))
    ]


def _skill_data_record(
    path: Path, export_root: Path, *, registry: Any, definition: int,
    reference_targets: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Publish stored SkillData values only after whole-file and id agreement.

    The selected generated wrapper supplies member names and scalar types. A
    stored action, tag, or field name does not establish its runtime execution.
    """
    relative = path.relative_to(export_root).as_posix()
    tags = ["gameplay", "skilldata", "memorypack"]
    try:
        raw = path.read_bytes()
        value, reached = decode_file(raw, definition, registry, source=path.name)
        if reached != len(raw):
            raise ValueError(f"whole-file cursor {reached}/{len(raw)}")
        if find_identifier(value) != path.stem:
            raise ValueError(
                f"stored identifier does not match exported filename {path.stem!r}"
            )
        if not isinstance(value, dict):
            raise ValueError("SkillData root is not a named record")
        group = value.get("actionGroupData")
        group = group if isinstance(group, dict) else {}
        timeline = group.get("timelineActions")
        passive = group.get("passiveEventActions")
        timeline_count = len(timeline) if isinstance(timeline, list) else None
        passive_count = len(passive) if isinstance(passive, list) else None
        direct_actions = _skill_data_direct_action_types(value)
        facts = {
            "skillId": value["skillId"],
            "storedMemberCount": len(value),
            "wholeFileCursorExact": True,
            "identifierMatchesFilename": True,
            "bytesConsumed": reached,
            "timelineActionCount": timeline_count,
            "passiveEventActionCount": passive_count,
            "directStoredActionInventoryAvailable": direct_actions is not None,
            "evidenceBoundary": (
                "structuralOnly: selected native generated-wrapper member values "
                "and nested union assignments; exact whole-file cursor and "
                "exported-filename identifier; stored data only"
            ),
        }
        if direct_actions is not None:
            facts["directStoredActionOccurrenceCount"] = sum(
                row["timelineOccurrences"] + row["passiveEventOccurrences"]
                for row in direct_actions
            )
            facts["directStoredActionTypes"] = direct_actions
        references = _skill_data_stored_references(value, reference_targets or {})
        record = {
            "id": relative,
            "title": path.stem,
            "status": "structural_only",
            "summary": _summary_text((
                f"members={len(value)}",
                f"timeline actions={timeline_count}" if timeline_count is not None else "",
                f"passive events={passive_count}" if passive_count is not None else "",
            )),
            "tags": [
                *tags, "structural_only",
                *(["has-timeline-actions"] if timeline_count else []),
                *(["has-passive-events"] if passive_count else []),
            ],
            "source": _source(path, export_root, "application/octet-stream"),
            "facts": facts,
            "payload": value,
            "payloadKind": "reader",
        }
        if direct_actions is not None:
            record["searchTerms"] = sorted({row["type"] for row in direct_actions})
        if references:
            record["references"] = {
                "evidenceBoundary": (
                    "Stored AllowNextSkillAction.allowedSkillIdList strings from the "
                    "selected native generated-wrapper value decode. A target is linked "
                    "only by exact SkillData filename-stem match in this export; "
                    "no runtime skill transition is observed."
                ),
                "items": references,
            }
        return record
    except (OSError, Unsupported, ValueError, IndexError, struct.error,
            UnicodeDecodeError, KeyError, TypeError) as exc:
        return _error_record(path, export_root, "application/octet-stream", tags, exc)


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


def _teleport_validation_json(data: bytes) -> Any:
    return decode_teleport_validation_json_table(data)


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
        _teleport_validation_json, "teleport-validation", "gameplay"),
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

# Config tables the client ships as plaintext UTF-8 JSON rather than as a
# serialized payload. Their bytes are the readable source, so the record must
# say so instead of presenting the file as an opaque binary blob.
JSON_TEXT_CONFIG_TABLES = frozenset({
    "GameplayConfig/LevelScriptTeleportValidationDataTable.json",
})


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
    json_text = json_relative in JSON_TEXT_CONFIG_TABLES
    media_type = "application/json" if json_text else "application/octet-stream"
    tags = ["config-table", kind, lane]
    if json_text:
        tags.append("json-text")
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
            "source": _source(path, export_root, media_type),
            "facts": facts,
            "payload": decoded,
            "payloadKind": "reader",
        }
    except _TABLE_ERRORS as exc:
        return _error_record(path, export_root, media_type, tags, exc)


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


#: Datasets whose documents are Unity objects: rows of game/Unity.sqlite, not
#: loose files. Their records keep the logical game/Unity/<Type>/<name> path.
UNITY_DATASET_TYPES = {
    "animator-controller": "AnimatorController",
    "animator-override-controller": "AnimatorOverrideController",
}


def _unity_document(path: Path, export_root: Path) -> bytes:
    """The exact bytes behind a logical ``game/Unity/<Type>/<name>`` path."""

    parts = split_logical_ref(path)
    if parts is None:
        raise OSError(f"not a Unity object document path: {path}")
    try:
        return open_store(export_root).read_bytes(*parts)
    except KeyError as exc:
        raise OSError(f"no Unity object document {parts[0]}/{parts[1]} in the export store") from exc


def _unity_source(path: Path, export_root: Path, size: int, media_type: str) -> dict[str, Any]:
    """``source_descriptor`` for a store row: the same logical path, the row's size."""

    relative = path.relative_to(export_root).as_posix()
    return {
        "path": relative,
        "href": f"/export_full/{relative}",
        "bytes": size,
        "mediaType": media_type,
    }


def _unity_selector(type_name: str, export_root: Path) -> Callable[[Path], list[Path]]:
    """Selector over one Unity type's JSON documents in the export store."""

    def select(root: Path) -> list[Path]:
        store = open_store_if_present(export_root)
        if store is None:
            return []
        return sorted(root / name for name in store.names(type_name, "*.json"))

    return select


def _unity_input_signature(store: UnityObjectStore | None, type_name: str) -> dict[str, Any]:
    """Reuse key for a store-backed dataset: document names, sizes and SHA256s."""

    digest = hashlib.sha256()
    count = 0
    total_bytes = 0
    rows = sorted(store.rows(type_name, "*.json"), key=lambda row: row.name.lower()) if store is not None else []
    for row in rows:
        digest.update(row.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(row.size).encode("ascii"))
        digest.update(b"\0")
        digest.update(row.sha256.lower().encode("ascii"))
        digest.update(b"\n")
        count += 1
        total_bytes += row.size
    return {
        "algorithm": "unity-store-name-size-sha256",
        "sha256": digest.hexdigest(),
        "files": count,
        "bytes": total_bytes,
    }


def _animator_controller_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    size = 0
    try:
        data = _unity_document(path, export_root)
        size = len(data)
        payload = json.loads(data.decode("utf-8-sig"))
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
            "source": _unity_source(path, export_root, size, "application/json"),
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
            "source": _unity_source(path, export_root, size, "application/json"),
            "diagnostic": str(exc),
        }


def _animator_override_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    size = 0
    try:
        data = _unity_document(path, export_root)
        size = len(data)
        payload = json.loads(data.decode("utf-8-sig"))
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
            "source": _unity_source(path, export_root, size, "application/json"),
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
            "source": _unity_source(path, export_root, size, "application/json"),
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


def _skill_data_plan() -> tuple[Any | None, int | None, dict[str, str], str]:
    """Resolve the selected native plan before publishing or reusing SkillData."""
    gate = check_installed_native_inputs()
    signature = {
        "gameAssemblySha256": gate.gameassembly_sha256,
        "metadataSha256": gate.metadata_sha256,
        "nativeStatus": gate.status,
    }
    if not gate.validated:
        return None, None, signature, gate.detail or gate.status
    try:
        registry, audit = load_registry(
            gameassembly=gate.gameassembly, metadata=gate.metadata,
        )
        signature["planStatus"] = str(audit.get("status") or "unavailable")
        if audit.get("status") != "validated":
            return None, None, signature, f"selected SkillData plan {signature['planStatus']}"
        definition = registry.named_roots.get(SKILLDATA_TYPE)
        if definition is None:
            return None, None, signature, "selected SkillData root plan missing"
        return registry, definition, signature, ""
    except (OSError, ValueError, RuntimeError, KeyError, IndexError,
            TypeError, struct.error) as exc:
        signature["planStatus"] = "unavailable"
        return None, None, signature, f"selected SkillData plan: {type(exc).__name__}: {exc}"


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
            _unity_selector("AnimatorController", args.export_root),
        ),
        "animator-override-controller": (
            "Animator override controllers",
            "Controller and clip override references with raw exported JSON.",
            layout.unity_type_dir("AnimatorOverrideController"),
            _animator_override_record,
            _unity_selector("AnimatorOverrideController", args.export_root),
        ),
        "level-config": (
            "Level configs",
            "Complete LevelConfig schema: level identity, map id, seamless and dimension flags, "
            "level-data path hashes, and level grids.",
            layout.json_dir / "LevelConfig",
            _level_config_record,
            _all_json,
        ),
        "level-data": (
            "Level data",
            "Exact and bounded LevelData fields, including stored spline geometry when reached; "
            "no runtime traversal is implied.",
            layout.json_dir / "LevelData",
            _level_data_record,
            _all_json,
        ),
        "skill-data": (
            "Skill data",
            "Selected-native SkillData member values, shown only after an exact whole-file "
            "decode and stored-id match; no runtime action is implied.",
            layout.json_dir / "SkillData",
            _skill_data_record,
            _all_json,
        ),
        "buff-action-receipts": (
            "Buff action receipts",
            "Authenticated CreateBuff and FinishBuffAdvanced action spans and wrapper fields; "
            "the enclosing BuffData schema remains partial.",
            layout.json_dir / "BuffData",
            None,
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
        unity_type = UNITY_DATASET_TYPES.get(dataset_id)
        if unity_type is not None:
            unity_store = open_store_if_present(args.export_root)
            available = unity_store is not None
            diagnostic = "" if available else f"missing Unity object store: {layout.unity_store_path}"
            input_signature = _unity_input_signature(unity_store, unity_type)
        else:
            available = root.is_dir()
            diagnostic = "" if available else f"missing source directory: {root}"
            input_signature = _input_signature(root, selector)
        skill_registry = None
        skill_definition = None
        buff_receipt_records = None
        if dataset_id == "skill-data" and available:
            skill_registry, skill_definition, native_signature, native_diagnostic = _skill_data_plan()
            input_signature["selectedNative"] = native_signature
            if skill_definition is None:
                available = False
                diagnostic = native_diagnostic
        if dataset_id == "buff-action-receipts" and available:
            try:
                buff_receipt_records, receipt_signature = load_receipt_records(
                    args.buff_action_receipts_report, args.buff_corpus_report,
                    args.export_root,
                )
                input_signature["authenticatedReceipts"] = receipt_signature
            except (OSError, ValueError, KeyError, TypeError,
                    json.JSONDecodeError) as exc:
                available = False
                diagnostic = f"Buff action receipts unavailable: {type(exc).__name__}: {exc}"
        descriptor = None if args.force or not available else _reusable_descriptor(
            args.out_dir, dataset_id, input_signature, args.shard_size
        )
        if descriptor is not None:
            descriptors.append(descriptor)
            print(f"{dataset_id}: reused {descriptor['recordCount']} unchanged records")
            continue
        if available and dataset_id == "skill-data":
            skill_paths = list(selector(root))
            reference_targets = _skill_data_reference_targets(skill_paths, args.export_root)
            records = [
                _skill_data_record(
                    path, args.export_root,
                    registry=skill_registry, definition=skill_definition,
                    reference_targets=reference_targets,
                )
                for path in skill_paths
            ]
        elif available and dataset_id == "buff-action-receipts":
            records = buff_receipt_records
        else:
            records = (
                [reader(path, args.export_root) for path in selector(root)]
                if available and unity_type is not None else
                _build_records(root, args.export_root, reader, selector) if available else []
            )
        descriptor = publish_dataset(
            args.out_dir,
            dataset_id=dataset_id,
            title=title,
            description=description,
            records=records,
            provenance={
                "exportLayout": EXPORT_LAYOUT_SCHEMA,
                "sourceRoot": root.relative_to(args.export_root).as_posix(),
                "reader": (
                    "scripts.game_data.memorypack.derived_values.decode_file"
                    if dataset_id == "skill-data" else
                    "scripts.game_data.memorypack.buff_action_receipt_corpus"
                    if dataset_id == "buff-action-receipts" else
                    f"{reader.__module__}.{reader.__name__}"
                ),
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
