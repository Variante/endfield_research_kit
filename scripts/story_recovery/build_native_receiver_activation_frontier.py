#!/usr/bin/env python3
"""Audit the static activation frontier of unresolved native Story receivers.

Mission Pipeline already preserves exact native event receivers that lead to
Story playback while refusing to invent a mission owner.  This audit asks the
next narrower question for each hosting LevelScript:

* how the LevelScript says it starts;
* which validated LevelData member-22 dictionary contains it;
* whether that container names a MissionRuntime id;
* whether any decoded ManualStartLevelScript row literally targets it.

The result is a triage surface, not an attachment source.  A generic LevelData
container, Manual start type, or incoming manual-control edge does not by
itself identify a mission, quest, playback order, or server-state producer.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
for search_path in (ROOT / "scripts", ROOT / "scripts" / "story_recovery"):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from common import (  # noqa: E402
    STORY_RECOVERY_REPORTS_DIR,
    md_escape,
    read_bytes_cached,
    read_json,
    rel_path,
    write_report_json,
    write_text_if_changed,
)
from story_builder.context import (  # noqa: E402
    GAMEPLAY_CONFIG_DIR,
    LEVELDATA_DIR,
    LEVELSCRIPT_DIR,
    MRA_DIR,
    SPAWNER_CONFIG_DIR,
)
from story_builder.level_bindings import (  # noqa: E402
    _native_vector_close,
    _parse_leveldata_mission_host_name,
    parse_leveldata_levelscript_brief_dictionary,
)
from story_builder.levelscript_binary import (  # noqa: E402
    decode_levelscript_task_conditions,
    decode_levelscript_binary_file,
)
from story_builder.mission_recovery import (  # noqa: E402
    decode_mission_script_conditions,
    decode_mission_world_entity_condition_refs,
)


SCHEMA = "nativeReceiverActivationFrontier.v5"
DEFAULT_PIPELINE_INDEX = ROOT / "webui" / "data" / "mission_pipeline" / "index.json"
DEFAULT_PIPELINE_MISSION_ROOT = (
    ROOT / "webui" / "data" / "mission_pipeline" / "missions"
)
DEFAULT_MANUAL_CONTROL_AUDIT = (
    ROOT / "reports" / "mission_order" / "levelscript_manual_control_audit.json"
)
DEFAULT_JSON = STORY_RECOVERY_REPORTS_DIR / "native_receiver_activation_frontier.json"
DEFAULT_MARKDOWN = STORY_RECOVERY_REPORTS_DIR / "native_receiver_activation_frontier.md"
DEFAULT_MISSION_AREA_TABLE = GAMEPLAY_CONFIG_DIR / "MissionAreaTable.json"
DEFAULT_LEVEL_BASIC_INFO_TABLE = GAMEPLAY_CONFIG_DIR / "LevelBasicInfoTable.json"
DEFAULT_SCRIPT_TASK_EXTRA_INFO_TABLE = (
    GAMEPLAY_CONFIG_DIR / "ScriptTaskExtraInfoTable.json"
)
DEFAULT_WORLD_ENTITY_REGISTRY = GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"


def safe_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def receiver_script_rows(index_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Collapse exact receiver nodes to one row per hosting LevelScript."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    nodes = (
        (index_payload.get("storyCoverage") or {}).get(
            "missionlessNativeRuntimeNodes"
        )
        or []
    )
    for node in nodes:
        if not isinstance(node, dict):
            continue
        selector = node.get("selector") or {}
        level_id = safe_text(selector.get("levelId"))
        script_id = safe_text(selector.get("listenerScriptId"))
        if not level_id or not script_id.isdigit():
            continue
        key = (level_id, script_id)
        slot = grouped.setdefault(
            key,
            {
                "levelId": level_id,
                "scriptId": script_id,
                "receiverNodeCount": 0,
                "receiverToStoryPlacementCount": 0,
                "eventNames": set(),
                "storyKeys": set(),
                "storyKinds": set(),
                "sourceFiles": set(),
            },
        )
        slot["receiverNodeCount"] += 1
        event_name = safe_text(node.get("eventName"))
        if event_name:
            slot["eventNames"].add(event_name)
        for story_file in node.get("storyFiles") or []:
            if not isinstance(story_file, dict):
                continue
            slot["receiverToStoryPlacementCount"] += 1
            story_key = safe_text(story_file.get("key"))
            story_kind = safe_text(story_file.get("kind"))
            if story_key:
                slot["storyKeys"].add(story_key)
            if story_kind:
                slot["storyKinds"].add(story_kind)
            for source_file in story_file.get("sourceFiles") or []:
                if safe_text(source_file):
                    slot["sourceFiles"].add(safe_text(source_file))

    rows: list[dict[str, Any]] = []
    for slot in grouped.values():
        rows.append(
            {
                **slot,
                "eventNames": sorted(slot["eventNames"]),
                "storyKeys": sorted(slot["storyKeys"]),
                "storyKinds": sorted(slot["storyKinds"]),
                "sourceFiles": sorted(slot["sourceFiles"]),
            }
        )
    rows.sort(key=lambda row: (row["levelId"], int(row["scriptId"])))
    return rows


def manual_control_targets(
    payload: dict[str, Any],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Index literal manual-control targets without treating defaults as edges."""
    targets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        source_level = safe_text(row.get("levelId"))
        source_script = safe_text(row.get("scriptId"))
        for target in row.get("literalTargets") or []:
            if not isinstance(target, dict):
                continue
            level_id = safe_text(target.get("levelId"))
            script_id = safe_text(target.get("scriptId"))
            if not level_id or not script_id:
                continue
            targets[(level_id, script_id)].append(
                {
                    "sourceLevelId": source_level,
                    "sourceScriptId": source_script,
                    "localId": row.get("localId"),
                    "action": safe_text(row.get("action")),
                    "selfTarget": (
                        source_level == level_id and source_script == script_id
                    ),
                    "sourceFile": safe_text(row.get("file")),
                }
            )
    return targets


def subgame_script_bindings(
    index_payload: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Index exact SubGame bindScriptId rows already preserved by the pipeline."""
    bindings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows = (
        (index_payload.get("storyCoverage") or {}).get(
            "missionlessSubGamePlaybackNodes"
        )
        or []
    )
    for row in rows:
        if not isinstance(row, dict):
            continue
        script_id = safe_text(row.get("bindScriptId"))
        if not script_id:
            continue
        bindings[script_id].append(
            {
                "subGameId": safe_text(row.get("subGameId")),
                "modeId": safe_text(row.get("modeId")),
                "runtimeType": safe_text(row.get("runtimeType")),
                "mainTaskIds": sorted(
                    safe_text(value)
                    for value in row.get("mainTaskIds") or []
                    if safe_text(value)
                ),
                "subDataParentId": safe_text(row.get("subDataParentId")),
                "sourceFile": safe_text(row.get("source")),
                "missionOwnerStatus": safe_text(
                    row.get("missionOwnerStatus")
                ),
                "associations": row.get("associations") or [],
            }
        )
    return bindings


def script_task_extra_info_rows(
    payload: dict[str, Any],
    *,
    source_file: str = "",
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Index exact level/script/task display metadata without inferring owners."""
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    data_table = payload.get("dataTable") or {}
    if not isinstance(data_table, dict):
        return indexed
    for level_id_raw, scripts in data_table.items():
        level_id = safe_text(level_id_raw)
        if not level_id or not isinstance(scripts, dict):
            continue
        for script_id_raw, tasks in scripts.items():
            script_id = safe_text(script_id_raw)
            if not script_id.isdigit() or not isinstance(tasks, dict):
                continue
            for task_id_raw, info in tasks.items():
                task_id = safe_text(task_id_raw)
                if not task_id or not isinstance(info, dict):
                    continue
                tracking_info = info.get("trackingInfoDict")
                if not isinstance(tracking_info, dict):
                    tracking_info = {}
                objectives = []
                for objective_id_raw, objective in tracking_info.items():
                    if not isinstance(objective, dict):
                        continue
                    description = objective.get("description")
                    if not isinstance(description, dict):
                        description = {}
                    objectives.append({
                        "objectiveId": safe_text(objective_id_raw),
                        "descriptionKey": safe_text(
                            description.get("key")
                        ),
                        "needFormatProgress": objective.get(
                            "needFormatProgress"
                        ),
                        "progressDisplayMode": objective.get(
                            "progressDisplayMode"
                        ),
                    })
                task_title = info.get("taskTitle")
                if not isinstance(task_title, dict):
                    task_title = {}
                indexed[(level_id, script_id, task_id)] = {
                    "taskTitleKey": safe_text(task_title.get("key")),
                    "objectiveCount": info.get("objectiveCount"),
                    "singleDescriptionFormatProgress": info.get(
                        "singleDescriptionFormatProgress"
                    ),
                    "objectives": objectives,
                    "sourceFile": source_file,
                    "evidenceBoundary": (
                        "Exact task display/tracking metadata only; it carries "
                        "no mission or quest owner."
                    ),
                }
    return indexed


def annotate_task_sources(
    decoded_task_map: dict[str, Any] | None,
    *,
    level_id: str,
    script_id: str,
    subgames: list[dict[str, Any]],
    extra_info: dict[tuple[str, str, str], dict[str, Any]],
) -> None:
    """Attach exact task-table/SubGame cross-references in place."""
    for task in (decoded_task_map or {}).get("tasks") or []:
        task_id = safe_text(task.get("taskKey"))
        if not task_id:
            continue
        detail = extra_info.get((level_id, script_id, task_id))
        if detail:
            task["taskExtraInfo"] = detail
        bindings = []
        for subgame in subgames:
            if task_id not in set(subgame.get("mainTaskIds") or []):
                continue
            bindings.append({
                "subGameId": safe_text(subgame.get("subGameId")),
                "modeId": safe_text(subgame.get("modeId")),
                "runtimeType": safe_text(subgame.get("runtimeType")),
                "missionOwnerStatus": safe_text(
                    subgame.get("missionOwnerStatus")
                ),
                "sourceFile": safe_text(subgame.get("sourceFile")),
            })
        if bindings:
            task["subGameMainTaskBindings"] = bindings


def _unwrap_const(value: Any) -> Any:
    if isinstance(value, dict) and "constValue" in value:
        return value.get("constValue")
    return value


def _short_type_name(value: Any) -> str:
    return safe_text(value).split(",", 1)[0].rsplit(".", 1)[-1]


def _typed_nodes(
    value: Any,
    quest_id: str = "",
) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        next_quest_id = safe_text(value.get("questId")) or quest_id
        if safe_text(value.get("$type")):
            rows.append((next_quest_id, value))
        for child in value.values():
            rows.extend(_typed_nodes(child, next_quest_id))
    elif isinstance(value, list):
        for child in value:
            rows.extend(_typed_nodes(child, quest_id))
    return rows


def mission_runtime_operand_consumers_from_payloads(
    payloads: list[tuple[str, dict[str, Any], str]],
) -> dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]]:
    """Index typed MissionRuntime condition operands by exact authored key."""
    indexes: dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]] = {
        kind: defaultdict(list)
        for kind in ("dialog", "area", "spawner", "script", "entity", "task")
    }
    for mission_id, raw, source_file in payloads:
        for row in decode_mission_script_conditions(raw):
            level_id = safe_text(row.get("mapId"))
            script_id = safe_text(row.get("scriptId"))
            if level_id and script_id:
                indexes["script"][(level_id, script_id)].append({
                    "missionId": mission_id,
                    "questId": safe_text(row.get("questId")),
                    "conditionType": _short_type_name(row.get("type")),
                    "sourceFile": source_file,
                })
        for row in decode_mission_world_entity_condition_refs(raw):
            level_id = safe_text(row.get("mapId"))
            logic_id = row.get("logicId")
            if (
                level_id
                and isinstance(logic_id, int)
                and not isinstance(logic_id, bool)
                and logic_id > 0
            ):
                indexes["entity"][(level_id, logic_id)].append({
                    "missionId": mission_id,
                    "questId": safe_text(row.get("questId")),
                    "conditionType": safe_text(row.get("conditionType")),
                    "conditionPath": safe_text(row.get("conditionPath")),
                    "sourceFile": source_file,
                })
        for quest_id, node in _typed_nodes(raw):
            condition_type = _short_type_name(node.get("$type"))
            if condition_type == "CheckTalkOptionFinish":
                dialog_id = _unwrap_const(
                    node.get("_dialogId", node.get("dialogId"))
                )
                finish_id = _unwrap_const(
                    node.get("_finishId", node.get("finishId"))
                )
                if isinstance(dialog_id, str) and isinstance(finish_id, int):
                    indexes["dialog"][(dialog_id, finish_id)].append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "conditionType": condition_type,
                        "sourceFile": source_file,
                    })
            elif condition_type in {"ReachDestination", "TaskReachDestination"}:
                area_id = _unwrap_const(node.get("_areaId", node.get("areaId")))
                level_id = _unwrap_const(
                    node.get(
                        "_mapId",
                        node.get(
                            "mapId",
                            node.get("_levelId", node.get("levelId")),
                        ),
                    )
                )
                if isinstance(area_id, str) and isinstance(level_id, str):
                    indexes["area"][(level_id, area_id)].append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "conditionType": condition_type,
                        "sourceFile": source_file,
                    })
            elif condition_type == "CheckMonsterSpawnerComplete":
                spawner_id = _unwrap_const(
                    node.get("_spawnerId", node.get("spawnerId"))
                )
                level_id = _unwrap_const(
                    node.get(
                        "_levelId",
                        node.get(
                            "levelId",
                            node.get("_mapId", node.get("mapId")),
                        ),
                    )
                )
                if (
                    isinstance(spawner_id, int)
                    and not isinstance(spawner_id, bool)
                    and isinstance(level_id, str)
                ):
                    indexes["spawner"][(level_id, str(spawner_id))].append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "conditionType": condition_type,
                        "sourceFile": source_file,
                    })
            elif condition_type == "CheckLevelScriptTaskFinished":
                level_id = _unwrap_const(
                    node.get(
                        "_sceneId",
                        node.get(
                            "sceneId",
                            node.get("_levelId", node.get("levelId")),
                        ),
                    )
                )
                script_value = _unwrap_const(
                    node.get("_scriptId", node.get("scriptId"))
                )
                if isinstance(script_value, dict):
                    script_value = script_value.get("scriptId")
                task_id = _unwrap_const(
                    node.get("_taskId", node.get("taskId"))
                )
                level_text = safe_text(level_id)
                script_text = safe_text(script_value)
                task_text = safe_text(task_id)
                if level_text and script_text and task_text:
                    indexes["task"][
                        (level_text, script_text, task_text)
                    ].append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "conditionType": condition_type,
                        "sourceFile": source_file,
                    })
    return {kind: dict(rows) for kind, rows in indexes.items()}


def mission_runtime_operand_consumers(
    mission_runtime_root: Path = MRA_DIR,
) -> dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]]:
    payloads = []
    if mission_runtime_root.is_dir():
        for path in sorted(mission_runtime_root.glob("*.json")):
            if path.stem.endswith("_meta"):
                continue
            raw = read_json(path) or {}
            mission_id = safe_text(raw.get("missionId")) or path.stem
            payloads.append((mission_id, raw, rel_path(path)))
    return mission_runtime_operand_consumers_from_payloads(payloads)


def world_entity_operand_sources(
    payload: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, int], dict[str, Any]]]:
    """Build exact logic-id and current-script/slot WorldEntity indexes."""
    raw_logic_rows = payload.get("worldEntityBriefInfos") or {}
    if not isinstance(raw_logic_rows, dict):
        raw_logic_rows = {}
    logic_rows = {
        safe_text(logic_id): dict(brief)
        for logic_id, brief in raw_logic_rows.items()
        if safe_text(logic_id) and isinstance(brief, dict)
    }
    id_rows = payload.get("m_scriptEntityIdList") or []
    brief_rows = payload.get("m_scriptEntityBriefInfo") or []
    slot_rows: dict[tuple[str, int], dict[str, Any]] = {}
    if (
        isinstance(id_rows, list)
        and isinstance(brief_rows, list)
        and len(id_rows) == len(brief_rows)
    ):
        candidates: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        for index, (identity, brief) in enumerate(zip(id_rows, brief_rows)):
            if not isinstance(identity, dict) or not isinstance(brief, dict):
                continue
            script_id = safe_text(identity.get("scriptIdGlobal"))
            slot_id = identity.get("slotId")
            if (
                not script_id.isdigit()
                or not isinstance(slot_id, int)
                or isinstance(slot_id, bool)
            ):
                continue
            candidates[(script_id, slot_id)].append({
                "registryIndex": index,
                "scriptIdGlobal": script_id,
                "slotId": slot_id,
                "entityType": brief.get("entityType"),
                "entityDetailId": safe_text(brief.get("detailId")),
                "position": brief.get("position"),
            })
        slot_rows = {
            key: rows[0]
            for key, rows in candidates.items()
            if len(rows) == 1
        }
    return logic_rows, slot_rows


def annotate_task_condition_operands(
    decoded_task_map: dict[str, Any] | None,
    *,
    level_id: str,
    script_id: str,
    story_keys: list[str],
    mission_areas: list[dict[str, Any]],
    logic_entities: dict[str, dict[str, Any]],
    slot_entities: dict[tuple[str, int], dict[str, Any]],
    mission_consumers: dict[
        str,
        dict[tuple[Any, ...], list[dict[str, Any]]],
    ],
    levelscript_root: Path,
    spawner_root: Path,
) -> None:
    """Resolve exact condition operands while preserving non-owning status."""
    area_by_id = {
        safe_text(area.get("missionAreaId")): area
        for area in mission_areas
        if isinstance(area, dict) and safe_text(area.get("missionAreaId"))
    }
    story_key_set = set(story_keys)
    for task in (decoded_task_map or {}).get("tasks") or []:
        task_consumers = mission_consumers["task"].get(
            (level_id, script_id, safe_text(task.get("taskKey"))),
            [],
        )
        if task_consumers:
            task["missionRuntimeTaskConsumers"] = task_consumers
        for condition_row in task.get("conditions") or []:
            condition = condition_row.get("condition") or {}
            sources = []
            consumers = []

            dialog_id = (condition.get("dialogId") or {}).get("value")
            finish_id = (condition.get("finishId") or {}).get("value")
            if isinstance(dialog_id, str):
                if dialog_id in story_key_set:
                    sources.append({
                        "kind": "same_receiver_story",
                        "storyKey": dialog_id,
                    })
                if isinstance(finish_id, int):
                    consumers.extend(
                        mission_consumers["dialog"].get(
                            (dialog_id, finish_id),
                            [],
                        )
                    )

            area_id = (condition.get("areaId") or {}).get("value")
            if isinstance(area_id, str) and area_id in area_by_id:
                area = area_by_id[area_id]
                sources.append({
                    "kind": "same_level_mission_area",
                    "missionAreaId": area_id,
                    "subDataParentId": area.get("subDataParentId"),
                    "shape": area.get("shape"),
                })
                consumers.extend(
                    mission_consumers["area"].get((level_id, area_id), [])
                )

            spawner_id = (condition.get("spawnerId") or {}).get("value")
            if isinstance(spawner_id, str):
                spawner_path = (
                    spawner_root
                    / level_id
                    / f"sc_{level_id}_{spawner_id}.json"
                )
                if spawner_path.is_file():
                    sources.append({
                        "kind": "same_level_spawner_config",
                        "spawnerId": spawner_id,
                        "sourceFile": rel_path(spawner_path),
                    })
                consumers.extend(
                    mission_consumers["spawner"].get(
                        (level_id, spawner_id),
                        [],
                    )
                )

            script_ptr = condition.get("scriptId") or {}
            target_script = (
                script_id
                if script_ptr.get("mode") == "current_script"
                else safe_text(script_ptr.get("scriptId"))
            )
            if target_script:
                target_path = (
                    levelscript_root / level_id / f"{target_script}.json"
                )
                if target_path.is_file():
                    sources.append({
                        "kind": "same_level_levelscript",
                        "scriptId": target_script,
                        "sourceFile": rel_path(target_path),
                    })
                consumers.extend(
                    mission_consumers["script"].get(
                        (level_id, target_script),
                        [],
                    )
                )

            pointers = []
            for field in ("entity", "entityId"):
                if isinstance(condition.get(field), dict):
                    pointers.append((field, condition[field]))
            for index, pointer in enumerate(
                (condition.get("enemyIds") or {}).get("values") or []
            ):
                if isinstance(pointer, dict):
                    pointers.append((f"enemyIds[{index}]", pointer))
            for field, pointer in pointers:
                if pointer.get("useSlotId") is True:
                    slot_id = pointer.get("slotId")
                    if isinstance(slot_id, int):
                        source = slot_entities.get((script_id, slot_id))
                        if source:
                            sources.append({
                                "kind": "current_script_slot_entity",
                                "field": field,
                                **source,
                            })
                elif pointer.get("useSlotId") is False:
                    logic_text = safe_text(pointer.get("logicId"))
                    if logic_text.isdigit() and int(logic_text) > 0:
                        logic_id = int(logic_text)
                        source = logic_entities.get(logic_text)
                        if source:
                            sources.append({
                                "kind": "world_entity_logic_id",
                                "field": field,
                                "logicId": logic_text,
                                "entityType": source.get("entityType"),
                                "entityDetailId": safe_text(
                                    source.get("detailId")
                                ),
                                "position": source.get("position"),
                            })
                        consumers.extend(
                            mission_consumers["entity"].get(
                                (level_id, logic_id),
                                [],
                            )
                        )
            if sources:
                condition_row["operandSources"] = sources
            if consumers:
                unique_consumers = {
                    (
                        safe_text(row.get("missionId")),
                        safe_text(row.get("questId")),
                        safe_text(row.get("conditionType")),
                        safe_text(row.get("sourceFile")),
                    ): row
                    for row in consumers
                }
                condition_row["missionRuntimeOperandConsumers"] = list(
                    unique_consumers.values()
                )


def mission_runtime_script_consumers(
    mission_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Index typed objective operands that name a LevelScript id."""
    consumers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not mission_root.is_dir():
        return consumers
    for path in sorted(mission_root.glob("*.json")):
        payload = read_json(path) or {}
        mission = payload.get("mission") or {}
        mission_id = safe_text(mission.get("id")) or path.stem
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            quest_id = safe_text(node.get("id"))
            for objective in node.get("objectives") or []:
                if not isinstance(objective, dict):
                    continue
                for script_id_raw in objective.get("levelScriptIds") or []:
                    script_id = safe_text(script_id_raw)
                    if not script_id:
                        continue
                    consumers[script_id].append(
                        {
                            "missionId": mission_id,
                            "questId": quest_id,
                            "objectiveIndex": objective.get("index"),
                            "conditionTypes": objective.get("conditionTypes") or [],
                            "sourceFile": rel_path(path),
                        }
                    )
    return consumers


def mission_areas_by_level(
    mission_area_path: Path = DEFAULT_MISSION_AREA_TABLE,
    level_basic_info_path: Path = DEFAULT_LEVEL_BASIC_INFO_TABLE,
) -> dict[str, list[dict[str, Any]]]:
    """Resolve authored MissionArea rows to their exact LevelBasicInfo level."""
    mission_area_payload = read_json(mission_area_path) or {}
    level_rows = read_json(level_basic_info_path) or {}
    area_groups = (
        mission_area_payload.get("m_areas")
        if isinstance(mission_area_payload, dict)
        else None
    )
    if not isinstance(area_groups, dict) or not isinstance(level_rows, dict):
        return {}

    out: dict[str, list[dict[str, Any]]] = {}
    for level_id, level_row in level_rows.items():
        if not isinstance(level_row, dict):
            continue
        level_num = safe_text(level_row.get("idNum"))
        group = area_groups.get(level_num)
        if not isinstance(group, dict):
            continue
        out[safe_text(level_id)] = [
            {
                "missionAreaId": safe_text(area_id),
                **area,
            }
            for area_id, area in sorted(group.items())
            if isinstance(area, dict)
        ]
    return out


def exact_start_shape_mission_area_matches(
    shapes: list[dict[str, Any]],
    mission_areas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Match complete authored shapes; proximity and names are never enough."""
    matches: list[dict[str, Any]] = []
    for shape_index, shape in enumerate(shapes):
        if not isinstance(shape, dict):
            continue
        try:
            shape_type = int(shape.get("typeRaw"))
        except (TypeError, ValueError):
            continue
        for area in mission_areas:
            area_shape = area.get("shape") if isinstance(area, dict) else None
            if not isinstance(area_shape, dict):
                continue
            try:
                area_type = int(area_shape.get("type"))
            except (TypeError, ValueError):
                continue
            if shape_type != area_type or not _native_vector_close(
                shape.get("position"),
                area_shape.get("position"),
            ):
                continue
            if shape_type == 1 and (
                not _native_vector_close(shape.get("size"), area_shape.get("size"))
                or not _native_vector_close(
                    shape.get("eulerAngles"),
                    area_shape.get("eulerAngles"),
                    angular=True,
                )
            ):
                continue
            if shape_type == 2:
                try:
                    radius_delta = abs(
                        float(shape.get("radius") or 0.0)
                        - float(area_shape.get("radius") or 0.0)
                    )
                except (TypeError, ValueError):
                    continue
                if radius_delta > 0.001:
                    continue
            matches.append(
                {
                    "startShapeIndex": shape_index,
                    "startShapeOffset": safe_text(shape.get("offset")),
                    "missionAreaId": safe_text(area.get("missionAreaId")),
                    "subDataParentId": area.get("subDataParentId"),
                    "shape": area_shape,
                    "status": "exact_complete_authored_shape_match",
                }
            )
    return matches


def exact_memorypack_string_tokens(
    data: bytes,
    values: set[str],
) -> list[str]:
    """Return exact positive-length MemoryPack string constants in one blob."""
    hits: list[str] = []
    for value in sorted(values):
        encoded = value.encode("utf-8")
        if not encoded:
            continue
        token = len(encoded).to_bytes(4, "little", signed=True) + encoded
        if token in data:
            hits.append(value)
    return hits


def validated_leveldata_hosts(
    level_id: str,
    target_script_id: str,
    mission_ids: set[str],
    *,
    leveldata_root: Path,
    levelscript_root: Path,
) -> list[dict[str, Any]]:
    """Return containers whose complete member-22 dictionary validates."""
    leveldata_dir = leveldata_root / level_id
    levelscript_dir = levelscript_root / level_id
    if not leveldata_dir.is_dir() or not levelscript_dir.is_dir():
        return []
    candidate_script_ids = {
        int(path.stem)
        for path in levelscript_dir.glob("*.json")
        if path.stem.isdigit()
    }
    numeric_target = int(target_script_id)
    if numeric_target not in candidate_script_ids:
        return []

    hosts: list[dict[str, Any]] = []
    for path in sorted(leveldata_dir.glob("*.json")):
        try:
            data = read_bytes_cached(path)
        except OSError:
            continue
        dictionary = parse_leveldata_levelscript_brief_dictionary(
            data,
            candidate_script_ids,
        )
        brief = dictionary.get(numeric_target)
        if not brief:
            continue
        mission_id = _parse_leveldata_mission_host_name(
            path.name,
            level_id,
            mission_ids,
        )
        hosts.append(
            {
                "sourceFile": rel_path(path),
                "fileName": path.name,
                "dictionaryEntryCount": len(dictionary),
                "missionNamedHost": bool(mission_id),
                "hostMissionId": mission_id or None,
                "briefData": {
                    "dataPathHash": safe_text(brief.get("dataPathHash")),
                    "levelScriptType": brief.get("levelScriptType"),
                    "maxStage": brief.get("maxStage"),
                    "parentLevelScriptId": safe_text(
                        brief.get("parentLevelScriptId")
                    ),
                    "propertyCount": brief.get("propertyCount"),
                    "propertyNames": [
                        safe_text(item.get("name"))
                        for item in brief.get("properties") or []
                        if isinstance(item, dict) and safe_text(item.get("name"))
                    ],
                    "refWorldEntityCount": brief.get("refWorldEntityCount"),
                    "refWorldEntityIds": brief.get("refWorldEntityIds") or [],
                },
            }
        )
    return hosts


def activation_class(
    levelscript: dict[str, Any],
    hosts: list[dict[str, Any]],
    incoming_manual_controls: list[dict[str, Any]],
    subgame_bindings: list[dict[str, Any]] | None = None,
) -> str:
    """Classify only the static carriers that the audit actually decodes."""
    if subgame_bindings:
        return "subgame_bind_script_activation_scope"
    if not levelscript:
        return "levelscript_missing_or_undecoded"
    start_type = safe_text(levelscript.get("startTypeName"))
    if not start_type:
        return "start_type_unresolved"
    cross_targets = [
        row for row in incoming_manual_controls if not row.get("selfTarget")
    ]
    if cross_targets:
        return "literal_cross_script_manual_control"
    if start_type != "Manual":
        if (levelscript.get("startShapeListCount") or 0) > 0:
            return "nonmanual_start_with_shapes"
        return "nonmanual_start_static_carrier_unresolved"

    parent_ids = {
        safe_text((host.get("briefData") or {}).get("parentLevelScriptId"))
        for host in hosts
    }
    parent_ids.discard("")
    no_parent = bool(hosts) and parent_ids == {"0"}
    no_shapes = (
        safe_text(levelscript.get("startShapeListStatus")) == "null"
        and (levelscript.get("startShapeListCount") or 0) == 0
    )
    no_task_map = (
        safe_text(levelscript.get("taskMapStatus")) == "null"
        and (levelscript.get("taskMapCount") or 0) == 0
    )
    if no_parent and no_shapes and no_task_map:
        return "manual_start_no_static_activation_carrier"
    return "manual_start_static_carrier_unresolved"


def build_report(
    index_payload: dict[str, Any],
    manual_control_payload: dict[str, Any],
    *,
    leveldata_root: Path = LEVELDATA_DIR,
    levelscript_root: Path = LEVELSCRIPT_DIR,
    mission_root: Path = DEFAULT_PIPELINE_MISSION_ROOT,
    mission_runtime_root: Path = MRA_DIR,
    spawner_root: Path = SPAWNER_CONFIG_DIR,
    script_task_extra_info_path: Path = DEFAULT_SCRIPT_TASK_EXTRA_INFO_TABLE,
    world_entity_registry_path: Path = DEFAULT_WORLD_ENTITY_REGISTRY,
) -> dict[str, Any]:
    mission_ids = {
        safe_text(row.get("id"))
        for row in index_payload.get("missions") or []
        if isinstance(row, dict) and safe_text(row.get("id"))
    }
    incoming_by_target = manual_control_targets(manual_control_payload)
    subgames_by_script = subgame_script_bindings(index_payload)
    consumers_by_script = mission_runtime_script_consumers(mission_root)
    task_extra_info = script_task_extra_info_rows(
        read_json(script_task_extra_info_path) or {},
        source_file=rel_path(script_task_extra_info_path),
    )
    mission_areas = mission_areas_by_level()
    mission_operand_consumers = mission_runtime_operand_consumers(
        mission_runtime_root
    )
    logic_entities, slot_entities = world_entity_operand_sources(
        read_json(world_entity_registry_path) or {}
    )
    rows: list[dict[str, Any]] = []
    classes: Counter[str] = Counter()
    start_types: Counter[str] = Counter()
    host_shapes: Counter[str] = Counter()
    task_condition_types: Counter[str] = Counter()
    task_operand_source_types: Counter[str] = Counter()
    task_mission_consumer_types: Counter[str] = Counter()
    task_conditions_with_operand_sources = 0
    task_conditions_with_mission_consumers = 0
    tasks_with_mission_consumers = 0

    for receiver in receiver_script_rows(index_payload):
        level_id = receiver["levelId"]
        script_id = receiver["scriptId"]
        script_path = levelscript_root / level_id / f"{script_id}.json"
        levelscript = decode_levelscript_binary_file(script_path, script_id)
        try:
            script_data = read_bytes_cached(script_path)
        except OSError:
            script_data = b""
        hosts = validated_leveldata_hosts(
            level_id,
            script_id,
            mission_ids,
            leveldata_root=leveldata_root,
            levelscript_root=levelscript_root,
        )
        incoming = incoming_by_target.get((level_id, script_id), [])
        subgames = subgames_by_script.get(script_id, [])
        consumers = consumers_by_script.get(script_id, [])
        start_shape_area_matches = exact_start_shape_mission_area_matches(
            levelscript.get("startShapeListShapes") or [],
            mission_areas.get(level_id, []),
        )
        serialized_mission_ids = exact_memorypack_string_tokens(
            script_data,
            mission_ids,
        )
        decoded_task_maps = decode_levelscript_task_conditions(
            script_data,
            script_id,
        )
        decoded_task_map = (
            decoded_task_maps[0] if len(decoded_task_maps) == 1 else None
        )
        annotate_task_sources(
            decoded_task_map,
            level_id=level_id,
            script_id=script_id,
            subgames=subgames,
            extra_info=task_extra_info,
        )
        annotate_task_condition_operands(
            decoded_task_map,
            level_id=level_id,
            script_id=script_id,
            story_keys=receiver["storyKeys"],
            mission_areas=mission_areas.get(level_id, []),
            logic_entities=logic_entities,
            slot_entities=slot_entities,
            mission_consumers=mission_operand_consumers,
            levelscript_root=levelscript_root,
            spawner_root=spawner_root,
        )
        for task in (decoded_task_map or {}).get("tasks") or []:
            tasks_with_mission_consumers += bool(
                task.get("missionRuntimeTaskConsumers")
            )
            for condition_row in task.get("conditions") or []:
                condition = condition_row.get("condition") or {}
                condition_type = safe_text(condition.get("type"))
                if condition_type:
                    task_condition_types[condition_type] += 1
                operand_sources = condition_row.get("operandSources") or []
                mission_consumers = (
                    condition_row.get("missionRuntimeOperandConsumers") or []
                )
                task_conditions_with_operand_sources += bool(operand_sources)
                task_conditions_with_mission_consumers += bool(
                    mission_consumers
                )
                for source in operand_sources:
                    source_type = safe_text(source.get("kind"))
                    if source_type:
                        task_operand_source_types[source_type] += 1
                for consumer in mission_consumers:
                    consumer_type = safe_text(consumer.get("conditionType"))
                    if consumer_type:
                        task_mission_consumer_types[consumer_type] += 1
        classification = activation_class(
            levelscript,
            hosts,
            incoming,
            subgames,
        )
        classes[classification] += 1
        start_types[safe_text(levelscript.get("startTypeName")) or "[unresolved]"] += 1
        if not hosts:
            host_shapes["no_validated_host"] += 1
        elif all(host.get("dictionaryEntryCount") == 1 for host in hosts):
            host_shapes["singleton_only"] += 1
        else:
            host_shapes["includes_multi_script_host"] += 1

        rows.append(
            {
                **receiver,
                "levelScript": {
                    "sourceFile": rel_path(script_path),
                    "scriptIdVerified": bool(levelscript.get("scriptIdVerified")),
                    "serializedMemberCount": levelscript.get(
                        "serializedMemberCount"
                    ),
                    "actionMapRecordCount": levelscript.get(
                        "actionMapRecordCount"
                    ),
                    "startTypeRaw": levelscript.get("startTypeRaw"),
                    "startTypeName": safe_text(levelscript.get("startTypeName")),
                    "startShapeListStatus": safe_text(
                        levelscript.get("startShapeListStatus")
                    ),
                    "startShapeListCount": levelscript.get("startShapeListCount"),
                    "startShapeListShapes": levelscript.get(
                        "startShapeListShapes"
                    )
                    or [],
                    "taskMapStatus": safe_text(levelscript.get("taskMapStatus")),
                    "taskMapCount": levelscript.get("taskMapCount"),
                    "triggerVolumesStatus": safe_text(
                        levelscript.get("triggerVolumesStatus")
                    ),
                    "triggerVolumesCount": levelscript.get("triggerVolumesCount"),
                    "triggerVolumeSlotIds": levelscript.get(
                        "triggerVolumeSlotIds"
                    )
                    or [],
                },
                "levelDataHosts": hosts,
                "incomingLiteralManualControls": incoming,
                "subGameBindings": subgames,
                "missionRuntimeScriptConsumers": consumers,
                "startShapeMissionAreaMatches": start_shape_area_matches,
                "serializedMissionRuntimeIdTokens": serialized_mission_ids,
                "decodedTaskMap": decoded_task_map,
                "activationClass": classification,
                "missionOwnerStatus": "unresolved",
                "evidenceBoundary": (
                    "Static start/container/control fields narrow the missing "
                    "activation carrier but do not identify a mission, quest, "
                    "server-state producer, playback owner, or order."
                ),
            }
        )

    return {
        "schemaVersion": SCHEMA,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "missionPipelineIndex": rel_path(DEFAULT_PIPELINE_INDEX),
            "manualControlAudit": rel_path(DEFAULT_MANUAL_CONTROL_AUDIT),
            "levelDataRoot": rel_path(leveldata_root),
            "levelScriptRoot": rel_path(levelscript_root),
            "missionPipelineMissionRoot": rel_path(mission_root),
            "missionRuntimeRoot": rel_path(mission_runtime_root),
            "spawnerRoot": rel_path(spawner_root),
            "scriptTaskExtraInfo": rel_path(script_task_extra_info_path),
            "worldEntityRegistry": rel_path(world_entity_registry_path),
        },
        "evidencePolicy": {
            "purpose": (
                "Locate the next static activation carrier for exact unresolved "
                "native Story receiver scripts."
            ),
            "noPromotion": (
                "This audit creates no mission/quest ownership, playback, branch, "
                "completion, or order edge."
            ),
            "manualBoundary": (
                "Manual start means the script does not use a decoded automatic "
                "start shape. Runtime/server state may still activate it through "
                "a carrier not serialized in the audited fields."
            ),
            "containerBoundary": (
                "A validated LevelData member-22 host proves loading/registration "
                "scope only. Even a mission-named host is context, not playback "
                "ownership."
            ),
            "subGameBoundary": (
                "SubGame bindScriptId proves the runtime system that activates "
                "the script shell, but a SubGame row without dungeonMissionId "
                "does not identify a mission or quest owner."
            ),
            "literalMissionIdBoundary": (
                "An exact MemoryPack string token proves only that the literal "
                "mission id exists somewhere in the LevelScript blob. Absence "
                "closes literal-constant carriers, not dynamic, indirect, or "
                "server-authored activation."
            ),
            "taskConditionBoundary": (
                "A completely decoded task map proves authored task evaluation "
                "requirements inside this LevelScript. Entity, spawner, dialog, "
                "area, property, stage, and mission operands are dependencies "
                "or completion gates, not mission ownership, activation order, "
                "or proof that the task executes."
            ),
            "taskOperandBoundary": (
                "Exact operand-source resolution identifies the authored object "
                "evaluated by a task condition. Only an exact typed "
                "MissionRuntime objective consuming the same operand could add "
                "a mission-side cross-reference; source identity alone proves "
                "no mission ownership or execution order."
            ),
            "taskConsumerBoundary": (
                "An exact CheckLevelScriptTaskFinished tuple would prove that "
                "one MissionRuntime objective waits on this task. It would be a "
                "mission-side completion dependency, not proof that the task "
                "activates or owns any Story playback in the receiver script."
            ),
        },
        "counts": {
            "receiverNodes": sum(row["receiverNodeCount"] for row in rows),
            "receiverScripts": len(rows),
            "receiverToStoryPlacements": sum(
                row["receiverToStoryPlacementCount"] for row in rows
            ),
            "storyKeys": len(
                {story_key for row in rows for story_key in row["storyKeys"]}
            ),
            "activationClasses": dict(sorted(classes.items())),
            "startTypes": dict(sorted(start_types.items())),
            "levelDataHostShapes": dict(sorted(host_shapes.items())),
            "scriptsWithMissionNamedHost": sum(
                any(host.get("missionNamedHost") for host in row["levelDataHosts"])
                for row in rows
            ),
            "scriptsWithIncomingLiteralCrossControl": sum(
                any(
                    not control.get("selfTarget")
                    for control in row["incomingLiteralManualControls"]
                )
                for row in rows
            ),
            "scriptsWithSubGameBinding": sum(
                bool(row["subGameBindings"]) for row in rows
            ),
            "scriptsWithMissionRuntimeObjectiveConsumer": sum(
                bool(row["missionRuntimeScriptConsumers"]) for row in rows
            ),
            "scriptsWithStartShapes": sum(
                bool((row.get("levelScript") or {}).get("startShapeListShapes"))
                for row in rows
            ),
            "scriptsWithExactStartShapeMissionAreaMatch": sum(
                bool(row["startShapeMissionAreaMatches"]) for row in rows
            ),
            "scriptsWithTaskMap": sum(
                safe_text((row.get("levelScript") or {}).get("taskMapStatus"))
                == "present"
                for row in rows
            ),
            "scriptsWithFullyDecodedTaskMap": sum(
                bool(row.get("decodedTaskMap")) for row in rows
            ),
            "decodedTaskCount": sum(
                len((row.get("decodedTaskMap") or {}).get("tasks") or [])
                for row in rows
            ),
            "decodedTaskConditionCount": sum(task_condition_types.values()),
            "decodedTaskConditionTypes": dict(
                sorted(task_condition_types.items())
            ),
            "decodedTaskConditionsWithExactOperandSource": (
                task_conditions_with_operand_sources
            ),
            "decodedTaskOperandSourceTypes": dict(
                sorted(task_operand_source_types.items())
            ),
            "decodedTaskConditionsWithMissionRuntimeOperandConsumer": (
                task_conditions_with_mission_consumers
            ),
            "decodedTaskMissionRuntimeOperandConsumerTypes": dict(
                sorted(task_mission_consumer_types.items())
            ),
            "decodedTasksWithMissionRuntimeTaskConsumer": (
                tasks_with_mission_consumers
            ),
            "decodedTasksWithExtraInfo": sum(
                bool(task.get("taskExtraInfo"))
                for row in rows
                for task in (row.get("decodedTaskMap") or {}).get("tasks") or []
            ),
            "decodedTasksWithSubGameMainTaskBinding": sum(
                bool(task.get("subGameMainTaskBindings"))
                for row in rows
                for task in (row.get("decodedTaskMap") or {}).get("tasks") or []
            ),
            "scriptsWithSerializedMissionRuntimeIdToken": sum(
                bool(row["serializedMissionRuntimeIdTokens"]) for row in rows
            ),
            "nonSubGameScriptsWithSerializedMissionRuntimeIdToken": sum(
                bool(row["serializedMissionRuntimeIdTokens"])
                and not row["subGameBindings"]
                for row in rows
            ),
            "nonSubGameTaskMapScriptsWithSerializedMissionRuntimeIdToken": sum(
                bool(row["serializedMissionRuntimeIdTokens"])
                and not row["subGameBindings"]
                and safe_text(
                    (row.get("levelScript") or {}).get("taskMapStatus")
                )
                == "present"
                for row in rows
            ),
        },
        "manualControlAuditSummary": manual_control_payload.get("summary") or {},
        "rows": rows,
    }


def publish_to_pipeline_index(
    index_payload: dict[str, Any],
    report: dict[str, Any],
) -> int:
    """Publish compact debug annotations without adding graph edges."""
    coverage = index_payload.get("storyCoverage")
    if not isinstance(coverage, dict):
        return 0
    row_index = {
        (safe_text(row.get("levelId")), safe_text(row.get("scriptId"))): row
        for row in report.get("rows") or []
        if isinstance(row, dict)
    }
    annotated = 0
    for node in coverage.get("missionlessNativeRuntimeNodes") or []:
        if not isinstance(node, dict):
            continue
        selector = node.get("selector") or {}
        row = row_index.get(
            (
                safe_text(selector.get("levelId")),
                safe_text(selector.get("listenerScriptId")),
            )
        )
        if not row:
            continue
        levelscript = row.get("levelScript") or {}
        node["activationFrontier"] = {
            "activationClass": safe_text(row.get("activationClass")),
            "startTypeName": safe_text(levelscript.get("startTypeName")),
            "startShapeListStatus": safe_text(
                levelscript.get("startShapeListStatus")
            ),
            "startShapeListCount": levelscript.get("startShapeListCount"),
            "taskMapStatus": safe_text(levelscript.get("taskMapStatus")),
            "taskMapCount": levelscript.get("taskMapCount"),
            "levelDataHosts": [
                {
                    "fileName": safe_text(host.get("fileName")),
                    "dictionaryEntryCount": host.get("dictionaryEntryCount"),
                    "hostMissionId": host.get("hostMissionId"),
                }
                for host in row.get("levelDataHosts") or []
                if isinstance(host, dict)
            ],
            "subGameIds": [
                safe_text(binding.get("subGameId"))
                for binding in row.get("subGameBindings") or []
                if isinstance(binding, dict) and safe_text(binding.get("subGameId"))
            ],
            "incomingLiteralCrossControlCount": sum(
                not control.get("selfTarget")
                for control in row.get("incomingLiteralManualControls") or []
                if isinstance(control, dict)
            ),
            "missionRuntimeObjectiveConsumerCount": len(
                row.get("missionRuntimeScriptConsumers") or []
            ),
            "exactStartShapeMissionAreaMatchCount": len(
                row.get("startShapeMissionAreaMatches") or []
            ),
            "serializedMissionRuntimeIdTokens": (
                row.get("serializedMissionRuntimeIdTokens") or []
            ),
            "decodedTaskMap": row.get("decodedTaskMap"),
        }
        annotated += 1

    coverage["nativeReceiverActivationFrontier"] = {
        "schemaVersion": report.get("schemaVersion"),
        "generated": report.get("generated"),
        "counts": report.get("counts") or {},
        "evidencePolicy": report.get("evidencePolicy") or {},
        "reportJson": rel_path(DEFAULT_JSON),
        "reportMarkdown": rel_path(DEFAULT_MARKDOWN),
        "annotatedReceiverNodes": annotated,
    }
    return annotated


def markdown_report(payload: dict[str, Any]) -> str:
    counts = payload.get("counts") or {}
    lines = [
        "# Native Receiver Activation Frontier",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Result",
        "",
        f"- Exact unresolved receiver nodes: `{counts.get('receiverNodes')}`",
        f"- Hosting LevelScripts: `{counts.get('receiverScripts')}`",
        (
            "- Receiver-to-Story placements: "
            f"`{counts.get('receiverToStoryPlacements')}`"
        ),
        f"- Unique Story keys: `{counts.get('storyKeys')}`",
        f"- Start types: `{counts.get('startTypes')}`",
        f"- Activation classes: `{counts.get('activationClasses')}`",
        f"- LevelData host shapes: `{counts.get('levelDataHostShapes')}`",
        (
            "- Scripts in a validated mission-named LevelData host: "
            f"`{counts.get('scriptsWithMissionNamedHost')}`"
        ),
        (
            "- Scripts with an incoming literal cross-script manual control: "
            f"`{counts.get('scriptsWithIncomingLiteralCrossControl')}`"
        ),
        (
            "- Scripts with an exact SubGame `bindScriptId` carrier: "
            f"`{counts.get('scriptsWithSubGameBinding')}`"
        ),
        (
            "- Scripts named by a typed MissionRuntime objective operand: "
            f"`{counts.get('scriptsWithMissionRuntimeObjectiveConsumer')}`"
        ),
        (
            "- Scripts with authored start shapes / exact complete MissionArea "
            f"shape matches: `{counts.get('scriptsWithStartShapes')}` / "
            f"`{counts.get('scriptsWithExactStartShapeMissionAreaMatch')}`"
        ),
        (
            "- Scripts with task maps / exact serialized MissionRuntime-id "
            f"tokens: `{counts.get('scriptsWithTaskMap')}` / "
            f"`{counts.get('scriptsWithSerializedMissionRuntimeIdToken')}`"
        ),
        (
            "- Fully decoded task-map scripts / tasks / conditions: "
            f"`{counts.get('scriptsWithFullyDecodedTaskMap')}` / "
            f"`{counts.get('decodedTaskCount')}` / "
            f"`{counts.get('decodedTaskConditionCount')}`"
        ),
        (
            "- Decoded task condition types: "
            f"`{counts.get('decodedTaskConditionTypes')}`"
        ),
        (
            "- Conditions with exact authored operand sources / source types: "
            f"`{counts.get('decodedTaskConditionsWithExactOperandSource')}` / "
            f"`{counts.get('decodedTaskOperandSourceTypes')}`"
        ),
        (
            "- Conditions with an exact typed MissionRuntime operand consumer: "
            f"`{counts.get('decodedTaskConditionsWithMissionRuntimeOperandConsumer')}`"
        ),
        (
            "- Tasks with an exact `CheckLevelScriptTaskFinished` consumer: "
            f"`{counts.get('decodedTasksWithMissionRuntimeTaskConsumer')}`"
        ),
        (
            "- Tasks with exact ScriptTaskExtraInfo / SubGame main-task rows: "
            f"`{counts.get('decodedTasksWithExtraInfo')}` / "
            f"`{counts.get('decodedTasksWithSubGameMainTaskBinding')}`"
        ),
        (
            "- Non-SubGame task-map scripts with a serialized MissionRuntime-id "
            "token: "
            f"`{counts.get('nonSubGameTaskMapScriptsWithSerializedMissionRuntimeIdToken')}`"
        ),
        "",
        "The report is fail-closed: these fields narrow the missing activation "
        "carrier but create no mission, quest, playback, branch, completion, or "
        "order edge.",
        "",
        "## Receiver scripts",
        "",
        "| LevelScript | receivers | Story keys | start | LevelData host | class |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for row in payload.get("rows") or []:
        levelscript = row.get("levelScript") or {}
        hosts = row.get("levelDataHosts") or []
        host_text = ", ".join(
            (
                f"{host.get('fileName')} "
                f"({host.get('dictionaryEntryCount')} scripts"
                + (
                    f", mission {host.get('hostMissionId')}"
                    if host.get("missionNamedHost")
                    else ", generic"
                )
                + ")"
            )
            for host in hosts
        ) or "[no validated host]"
        lines.append(
            "| "
            + " | ".join(
                md_escape(value)
                for value in (
                    f"{row.get('levelId')}/{row.get('scriptId')}",
                    row.get("receiverNodeCount"),
                    ", ".join(row.get("storyKeys") or []),
                    (
                        f"{levelscript.get('startTypeName') or '[unresolved]'}; "
                        f"shapes={levelscript.get('startShapeListStatus')}/"
                        f"{levelscript.get('startShapeListCount')}; "
                        f"taskMap={levelscript.get('taskMapStatus')}/"
                        f"{levelscript.get('taskMapCount')}"
                    ),
                    host_text,
                    row.get("activationClass"),
                )
            )
            + " |"
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-index", type=Path, default=DEFAULT_PIPELINE_INDEX)
    parser.add_argument(
        "--manual-control-audit",
        type=Path,
        default=DEFAULT_MANUAL_CONTROL_AUDIT,
    )
    parser.add_argument(
        "--mission-root",
        type=Path,
        default=DEFAULT_PIPELINE_MISSION_ROOT,
    )
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_report(
        read_json(args.pipeline_index) or {},
        read_json(args.manual_control_audit) or {},
        mission_root=args.mission_root,
    )
    payload["sources"]["missionPipelineIndex"] = rel_path(args.pipeline_index)
    payload["sources"]["manualControlAudit"] = rel_path(args.manual_control_audit)
    payload["sources"]["missionPipelineMissionRoot"] = rel_path(args.mission_root)
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, markdown_report(payload))
    counts = payload["counts"]
    print(
        f"wrote {rel_path(args.json)} and {rel_path(args.markdown)} "
        f"(scripts={counts['receiverScripts']}, "
        f"classes={counts['activationClasses']})"
    )


if __name__ == "__main__":
    main()
