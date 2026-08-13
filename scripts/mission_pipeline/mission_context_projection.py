"""Project typed activity and SubGame tables into Mission context registries."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _repo_path(path: Path) -> str:
    path = path.resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def load_activity_quest_level_hosts(
    table_paths: Iterable[Path | None],
    *,
    activity_quest_level_hosts_contract: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Load typed activity-stage ``questId -> levelId`` host rows.

    These rows enrich a quest's authored level context.  They deliberately do
    not create a Story edge: neither table contains a Story or LevelScript
    identity.
    """
    rows_by_quest: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sources: list[str] = []
    seen: set[tuple[str, str, str, str]] = set()
    for path in table_paths:
        if path is None or not path.is_file():
            continue
        source = _repo_path(path)
        sources.append(source)
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        table_name = path.stem
        for stage_id, raw in sorted(payload.items()):
            if not isinstance(raw, dict):
                continue
            quest_id = str(raw.get("questId") or "").strip()
            level_id = str(raw.get("levelId") or "").strip()
            if not quest_id or not level_id:
                continue
            signature = (table_name, str(stage_id), quest_id, level_id)
            if signature in seen:
                continue
            seen.add(signature)
            rows_by_quest[quest_id].append({
                "relation": "activity_stage_quest_level_host",
                "table": table_name,
                "stageId": str(stage_id),
                "questId": quest_id,
                "levelId": level_id,
                "storyBinding": False,
                "source": source,
                "confidence": "typed_original_data_and_native_accessors",
            })
    for rows in rows_by_quest.values():
        rows.sort(key=lambda row: (row["table"], row["stageId"], row["levelId"]))
    return dict(rows_by_quest), {
        "sources": sorted(set(sources)),
        "rowCount": sum(len(rows) for rows in rows_by_quest.values()),
        "questCount": len(rows_by_quest),
        "distinctLevelCount": len({
            row["levelId"]
            for rows in rows_by_quest.values()
            for row in rows
        }),
        "storyBindingsAdded": 0,
        "evidence": activity_quest_level_hosts_contract,
    }


def load_subgame_mission_bindings(
    table_path: Path | None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Load exact mission/script identities co-authored in typed SubGame rows.

    The relation is deliberately mission-shell context. Authored task lanes are
    retained so later generic recovery can require an exact script/task carrier.
    It never attaches a quest or Story file merely because the script is bound.
    """
    if table_path is None or not table_path.is_file():
        return {}, {
            "available": False,
            "source": _repo_path(table_path) if table_path is not None else "",
            "rowCount": 0,
            "rowsWithBindScriptId": 0,
            "rowsWithDungeonMissionId": 0,
            "missionBindingCount": 0,
            "boundMissionCount": 0,
            "distinctScriptCount": 0,
            "storyBindingsAdded": 0,
        }
    payload = _read_json(table_path)
    data_table = payload.get("dataTable") if isinstance(payload, dict) else None
    if not isinstance(data_table, dict):
        raise ValueError(f"SubGameInstanceData table has no dataTable map: {table_path}")
    bindings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, int]] = set()
    rows_with_bind_script_id = 0
    rows_with_dungeon_mission_id = 0
    for subgame_id, raw in sorted(data_table.items()):
        if not isinstance(raw, dict):
            continue
        mission_id = raw.get("dungeonMissionId")
        script_id = raw.get("bindScriptId")
        if isinstance(script_id, int) and script_id > 0:
            rows_with_bind_script_id += 1
        if isinstance(mission_id, str) and mission_id:
            rows_with_dungeon_mission_id += 1
        if not isinstance(mission_id, str) or not mission_id or not isinstance(script_id, int) or script_id <= 0:
            continue
        identity = (mission_id, str(subgame_id), script_id)
        if identity in seen:
            continue
        seen.add(identity)
        runtime_type = str(raw.get("$type") or "")
        if "," in runtime_type:
            runtime_type = runtime_type.split(",", 1)[0]
        task_lanes: dict[str, list[dict[str, Any]]] = {}
        for source_field, lane in (
            ("mainTasks", "main"),
            ("extraTasks", "extra"),
            ("failTasks", "fail"),
        ):
            values = raw.get(source_field)
            if not isinstance(values, list):
                raise ValueError(
                    "SubGame task lane is not an array: "
                    f"source={table_path} subGameId={subgame_id} "
                    f"lane={source_field} actual={type(values).__name__}"
                )
            task_lanes[lane] = [
                {
                    key: value
                    for key, value in task.items()
                    if key in {"taskId", "levelScriptId", "failInfo"}
                }
                for task in values
                if isinstance(task, dict) and str(task.get("taskId") or "")
            ]
        bindings[mission_id].append({
            "subGameId": str(subgame_id),
            "bindScriptId": str(script_id),
            "dungeonMissionId": mission_id,
            "subDataParentId": str(raw.get("subDataParentId") or ""),
            "runtimeType": runtime_type,
            "modeId": str(raw.get("modeId") or ""),
            "modeType": raw.get("modeType"),
            "gameMechanicsType": raw.get("gameMechanicsType"),
            "relation": "subgame_bind_script_runtime",
            "confidence": "typed_original_data",
            "source": _repo_path(table_path),
            "storyBinding": False,
            "taskLanes": task_lanes,
            "networkIdentity": {
                "authoredKeyField": "gameId",
                "authoredKeyValue": str(subgame_id),
                "startRequest": "CS_GAME_MECHANICS_REQ_START",
                "enterPush": "SC_GAME_MECHANICS_SYNC_ENTER_GAME_INST",
                "challengeStartPush": "SC_GAME_MECHANICS_SYNC_CHALLENGE_START",
                "challengeCompletePush": "SC_GAME_MECHANICS_SYNC_CHALLENGE_COMPLETE",
                "completionRewardPush": "SC_GAME_MECHANICS_SYNC_COMPLETION_REWARD",
                "stopRequest": "CS_GAME_MECHANICS_REQ_STOP",
                "leavePush": "SC_GAME_MECHANICS_SYNC_LEAVE_GAME_INST",
            },
        })
    for rows in bindings.values():
        rows.sort(key=lambda row: (row["subGameId"], row["bindScriptId"]))
    return dict(bindings), {
        "available": True,
        "source": _repo_path(table_path),
        "rowCount": len(data_table),
        "rowsWithBindScriptId": rows_with_bind_script_id,
        "rowsWithDungeonMissionId": rows_with_dungeon_mission_id,
        "missionBindingCount": len(seen),
        "boundMissionCount": len(bindings),
        "distinctScriptCount": len({script_id for _, _, script_id in seen}),
        "storyBindingsAdded": 0,
        "packetIdentity": {
            "authoredRowKey": "gameId",
            "runtimeOnlyFields": ["gameInstId", "gameUniqueId", "isReenter"],
            "missingOwnershipFields": ["missionId", "questId", "sceneNumId", "bindScriptId"],
        },
        "bindScriptNativeEvidence": {
            "serializedFieldOffset": "0x50",
            "startConsumer": "InteractiveLogicChallengeStartPoint._OnInteract",
            "startConsumerToken": "0x0600231a",
            "startConsumerAddress": "0x18713e548",
            "startEffect": (
                "SubGame table lookup -> bindScriptId read -> "
                "LevelScriptManager.TryGetLevelScript -> LevelScriptRuntime.ManualStart"
            ),
            "stopConsumer": "WorldChallengeGame.SendQuit",
            "stopConsumerAddress": "0x186f60cc8",
            "stopEffect": (
                "LevelScriptManager.TryGetLevelScript -> "
                "LevelScriptRuntime.ManualEnd -> send stop request"
            ),
            "auditedOnStartConsumerFound": True,
        },
        "evidenceBoundary": (
            "Exact typed mission-to-SubGame-to-LevelScript shell and authored task "
            "lanes only; the binary proves the generic interaction ManualStart "
            "carrier but not that it fired. No quest or Story attachment is inferred "
            "from co-membership. OCR, manual, and gameplay cross-references cannot "
            "promote this relation."
        ),
    }

