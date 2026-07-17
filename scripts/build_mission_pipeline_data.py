"""Build the experimental Mission Pipeline graph payload for the static WebUI.

The payload keeps authored MissionRuntimeAsset structure separate from native
runtime conclusions.  Predecessor edges are prerequisites visible in exported
data; they are never promoted to proof that the client chooses a successor.

Run from the repository root:
    python scripts/build_mission_pipeline_data.py
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MISSION_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset"
)
DEFAULT_OUTPUT_ROOT = ROOT / "webui" / "data" / "mission_pipeline"
SCHEMA_VERSION = 1


RUNTIME_CONTRACT = {
    "authority": {
        "owner": "server",
        "summary": (
            "The examined client applies synchronized quest states. It does not use "
            "prevQuestIdList or flowIndex to choose the next quest."
        ),
        "boundary": (
            "Predecessor and condition edges explain prerequisites visible to the client, "
            "not the server's complete authored successor policy."
        ),
    },
    "inbound": [
        {
            "id": "full-mission-sync",
            "direction": "server_to_client",
            "message": "SC_SYNC_ALL_MISSION",
            "handler": "MissionSystem.Handle_SyncAllMission",
            "address": "0x1833784e0",
            "fields": ["trackMissionId", "missions", "curQuests", "dailyMissionId", "curMainMissionId"],
            "effect": "Rebuild mission and current-quest state during initial/full synchronization.",
            "confidence": "native_proven",
        },
        {
            "id": "full-dialog-sync",
            "direction": "server_to_client",
            "message": "SC_SYNC_ALL_DIALOG",
            "handler": "CinematicSystem._Handle_SyncAllDialog",
            "address": "0x1837a2530",
            "fields": ["dialogs[].dialogId", "optionIds[]", "finishNums[]"],
            "effect": "Rebuild the dialog history that exact-finish mission conditions query.",
            "confidence": "native_proven",
        },
        {
            "id": "mission-state",
            "direction": "server_to_client",
            "message": "SC_MISSION_STATE_UPDATE",
            "handler": "MissionSystem.Handle_MissionStateUpdate",
            "address": "0x1873be300",
            "fields": ["missionId", "missionState", "succeedId", "properties", "acceptTime"],
            "effect": "Dispatch to AvailableMission, StartMission, or CompleteMission.",
            "confidence": "native_proven",
        },
        {
            "id": "quest-start",
            "direction": "server_to_client",
            "message": "SC_QUEST_STATE_UPDATE { questId, questState = 2, bRollback, roleBaseInfo }",
            "handler": "MissionSystem.Handle_QuestStateUpdate -> MissionRuntime.StartQuest",
            "address": "0x1873bf0a0 -> 0x183a885d0",
            "effect": "Create/bind the active client quest and its objective callbacks.",
            "confidence": "native_proven",
        },
        {
            "id": "quest-succeed",
            "direction": "server_to_client",
            "message": "SC_QUEST_STATE_UPDATE { questId, questState = 3, bRollback, roleBaseInfo }",
            "handler": "MissionSystem.Handle_QuestStateUpdate -> MissionRuntime.SucceedQuest",
            "address": "0x1873bf0a0 -> 0x1873c32ac",
            "effect": "Mark the quest completed on the client.",
            "confidence": "native_proven",
        },
        {
            "id": "quest-objectives",
            "direction": "server_to_client",
            "message": "SC_QUEST_OBJECTIVES_UPDATE",
            "handler": "MissionSystem.Handle_QuestObjectiveUpdate",
            "address": "0x183a882e0",
            "fields": ["questId", "questObjectives[].conditionId", "values", "isComplete", "descriptionIndex"],
            "effect": "Refresh objective progress and HUD state; completion still arrives as a separate quest-state update.",
            "confidence": "native_proven",
        },
        {
            "id": "quest-fail",
            "direction": "server_to_client",
            "message": "SC_QUEST_FAILED",
            "handler": "Handle_QuestFailed -> MissionRuntime.FailQuest",
            "address": "0x1873bef80 -> 0x1873bac84",
            "effect": "Mark the quest failed on the client.",
            "confidence": "native_proven",
        },
        {
            "id": "dialog-finish-echo",
            "direction": "server_to_client",
            "message": "SC_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
            "handler": "CinematicSystem._Handle_FinishDialog",
            "address": "0x1872f1758",
            "effect": "CheckTalkOptionFinish can test any finish or an exact finish id.",
            "confidence": "native_proven",
        },
        {
            "id": "level-script-event-ack",
            "direction": "server_to_client",
            "message": "SC_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER { }",
            "handler": "empty protocol acknowledgement",
            "effect": "Acknowledge the LevelScript event request; quest progression still arrives through objective or state updates.",
            "confidence": "native_proven",
        },
    ],
    "outbound": [
        {
            "id": "accept-mission",
            "direction": "client_to_server",
            "message": "CS_ACCEPT_MISSION { missionId }",
            "handler": "MissionSystem.AcceptMission -> BasePlayerManager.SendMsg",
            "address": "0x1873b7b48",
            "effect": "Request mission acceptance; await an asynchronous mission-state update rather than a paired accept response.",
            "confidence": "native_proven",
        },
        {
            "id": "objective-progress",
            "direction": "client_to_server",
            "message": "CS_UPDATE_QUEST_OBJECTIVE",
            "handler": "MissionSystem.OnSubConditionProgressChanged -> BasePlayerManager.SendMsg",
            "address": "0x183a6fc20",
            "fields": ["questId", "objectiveValueOps[].conditionId", "value", "isAdd=false"],
            "effect": "Report an absolute value when a bound client-side subcondition callback changes.",
            "confidence": "native_proven",
        },
        {
            "id": "dialog-finish",
            "direction": "client_to_server",
            "message": "CS_FINISH_DIALOG",
            "handler": "DialogManager.FinishDialog -> _SendServer -> CinematicSystem.SendFinishDialog",
            "address": "0x186e0f2d4 -> 0x186e2d2c0 -> 0x1872f0d88",
            "fields": ["dialogId", "optionIds[]", "finishNums[]", "dialogExtraInfoType", "submitInfo?"],
            "effect": "Submit the stable selected option ids and resolved dialog finish.",
            "confidence": "native_proven",
        },
        {
            "id": "level-script-event",
            "direction": "client_to_server",
            "message": "CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER",
            "handler": "GameplayNetwork.TriggerLevelScriptServerEvent[WithProperties]",
            "address": "0x1845f6710 / 0x187383640",
            "fields": ["sceneNumId", "scriptId", "eventName", "properties", "ctxToken"],
            "effect": "Trigger a server LevelScript event and await an empty acknowledgement; this does not itself prove quest completion.",
            "confidence": "native_proven",
        },
    ],
    "nativeEvidence": [
        {
            "symbol": "MissionRuntime.StartQuest",
            "address": "0x183a885d0",
            "finding": "Binds local quest/objective callbacks; no successor traversal was found.",
            "confidence": "native_proven",
        },
        {
            "symbol": "MissionSystem.OnSubConditionProgressChanged",
            "address": "0x183a6fc20",
            "finding": "Sends an absolute CS_UPDATE_QUEST_OBJECTIVE operation for the changed condition id.",
            "confidence": "native_proven",
        },
        {
            "symbol": "DialogTreeController.SelectIndex -> DialogTree.Continue",
            "finding": "The resolved option index selects an outgoing DialogTree connection.",
            "confidence": "native_proven",
        },
        {
            "symbol": "DialogTreeFinishNode.DoExecute -> DialogManager.FinishDialog",
            "finding": "The finish node supplies the finish id sent and synchronized later.",
            "confidence": "native_proven",
        },
        {
            "symbol": "CheckTalkOptionFinish.Check",
            "finding": (
                "Negative finish id means any recorded finish; a nonnegative id requires "
                "exact membership in dialogFinishInfos."
            ),
            "confidence": "native_proven",
        },
    ],
}


CASE_STUDIES: dict[str, dict[str, Any]] = {
    "e7m3": {
        "title": "Parallel fork and AND join",
        "summary": (
            "q16 activates two dialog objectives. LevelScript evidence and observed playback "
            "show both must finish before q29 advances; flowIndex does not make them exclusive."
        ),
        "nodes": {
            "e7m3_q#16": "fanout",
            "e7m3_q#17": "parallel objective",
            "e7m3_q#18": "parallel objective",
            "e7m3_q#29": "AND join",
        },
        "confidence": "asset_native_playback",
    },
    "c16m3": {
        "title": "Condition-driven AND join",
        "summary": (
            "q21 has one predecessor but actively ANDs Completed-state checks for q2, q3, and q4. "
            "Joins are not encoded only by multiple prevQuestIdList entries."
        ),
        "nodes": {
            "c16m3_q#2": "monitored completion",
            "c16m3_q#3": "monitored completion",
            "c16m3_q#4": "monitored completion",
            "c16m3_q#21": "active AND monitor",
        },
        "confidence": "asset_proven",
    },
    "e2m5": {
        "title": "Repeatable outcomes, not an exclusive route",
        "summary": (
            "q24 and q27 listen for finishes 1 and 2 of the same dialog. Playback shows the "
            "interaction repeats until both outcomes are recorded (0/2 -> 1/2 -> 2/2)."
        ),
        "nodes": {
            "e2m5_q#12": "fanout",
            "e2m5_q#23": "requires both result properties",
            "e2m5_q#24": "dialog finish 1 flag",
            "e2m5_q#27": "dialog finish 2 flag",
        },
        "confidence": "asset_playback",
    },
    "e7m4": {
        "title": "Persisted cinematic timeline result",
        "summary": (
            "Timeline finish routing maps 'confront Ruan Yi' to finish 0/q9 and 'prepare longer' "
            "to finish 1/q2. Only q2 is referenced by later LevelScript 23300030006; the exact "
            "high-level gated action remains unresolved."
        ),
        "nodes": {
            "e7m4_q#9": "timeline result 2 -> finish 0",
            "e7m4_q#2": "timeline result 1 -> finish 1; consumed later",
        },
        "confidence": "asset_native_playback",
    },
}


SERVER_CONDITION_TYPES = {"GameConditionServerPlaceHolder"}
SYNC_HISTORY_TYPES = {"CheckTalkOptionFinish"}
SYNC_STATE_TYPES = {
    "CheckQuestState",
    "SimpleConditionCheckQuestState",
    "CheckMissionSucceedId",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission-root", type=Path, default=DEFAULT_MISSION_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(encoded + "\n", encoding="utf-8", newline="\n")


def type_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.split(",", 1)[0].rsplit(".", 1)[-1]


def const_value(value: Any) -> Any:
    if isinstance(value, dict) and "constValue" in value:
        return value.get("constValue")
    return value


def iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def natural_quest_key(value: str) -> tuple[str, int, str]:
    mission, marker, suffix = str(value).partition("_q#")
    try:
        number = int(suffix) if marker else 10**9
    except ValueError:
        number = 10**9
    return mission, number, suffix


def compact_scalar(value: Any) -> Any:
    value = const_value(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        scalars = [compact_scalar(item) for item in value[:12]]
        return [item for item in scalars if item is not None]
    if isinstance(value, dict):
        kept: dict[str, Any] = {}
        for key in sorted(value):
            item = compact_scalar(value[key])
            if item not in (None, "", [], {}):
                kept[str(key)] = item
            if len(kept) >= 12:
                break
        return kept
    return str(value)


FACT_KEYS = (
    "conditionEvalString",
    "_dialogId",
    "_finishId",
    "_questId",
    "questId",
    "_targetQuestId",
    "_targetQuestState",
    "targetQuestState",
    "compareTarget",
    "_sceneId",
    "sceneId",
    "_scriptId",
    "scriptId",
    "_propertyKey",
    "_key",
    "_areaId",
    "_mapId",
    "needAllKill",
)


def condition_tree(condition: Any) -> dict[str, Any] | None:
    if not isinstance(condition, dict):
        return None
    name = type_name(condition.get("$type")) or "UnknownCondition"
    facts = {
        key.lstrip("_"): compact_scalar(condition.get(key))
        for key in FACT_KEYS
        if condition.get(key) not in (None, "", [], {})
    }
    children: list[dict[str, Any]] = []
    for key in ("subConditions", "conditions", "conditionList"):
        for child in condition.get(key) or []:
            normalized = condition_tree(child)
            if normalized:
                children.append(normalized)
    row: dict[str, Any] = {"type": name}
    if facts:
        row["facts"] = facts
    if children:
        row["children"] = children
    return row


def condition_objects(condition: Any) -> list[dict[str, Any]]:
    if not isinstance(condition, dict):
        return []
    return [row for row in iter_dicts(condition) if isinstance(row.get("$type"), str)]


def quest_condition_objects(quest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for objective in quest.get("objectiveList") or []:
        if isinstance(objective, dict):
            rows.extend(condition_objects(objective.get("condition")))
    rows.extend(condition_objects(quest.get("failedCondition")))
    return rows


def classify_authority(condition_types: Iterable[str]) -> str:
    values = set(condition_types)
    classes: set[str] = set()
    if values & SERVER_CONDITION_TYPES:
        classes.add("server")
    if values & SYNC_HISTORY_TYPES:
        classes.add("synchronized_history")
    if values & SYNC_STATE_TYPES:
        classes.add("synchronized_state")
    if values - SERVER_CONDITION_TYPES - SYNC_HISTORY_TYPES - SYNC_STATE_TYPES:
        classes.add("client_observed")
    if not classes:
        return "unknown"
    if len(classes) == 1:
        return next(iter(classes))
    return "mixed"


def get_const(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return const_value(row.get(key))
    return None


def objective_row(objective: dict[str, Any], index: int) -> dict[str, Any]:
    condition = objective.get("condition")
    objects = condition_objects(condition)
    types = sorted({type_name(row.get("$type")) for row in objects if type_name(row.get("$type"))})
    dialog_finishes: list[dict[str, Any]] = []
    quest_state_refs: list[dict[str, Any]] = []
    level_scripts: set[str] = set()
    properties: set[str] = set()
    for row in objects:
        name = type_name(row.get("$type"))
        if name == "CheckTalkOptionFinish":
            dialog = get_const(row, "_dialogId", "dialogId")
            finish = get_const(row, "_finishId", "finishId")
            if isinstance(dialog, str):
                dialog_finishes.append({"dialogId": dialog, "finishId": finish})
        if name in {"CheckQuestState", "SimpleConditionCheckQuestState"}:
            quest_id = get_const(row, "_questId", "questId", "_targetQuestId", "targetQuestId")
            state = get_const(row, "_targetQuestState", "targetQuestState", "compareTarget")
            if isinstance(quest_id, str):
                quest_state_refs.append({"questId": quest_id, "state": state})
        script = get_const(row, "_scriptId", "scriptId")
        if isinstance(script, dict):
            script = script.get("scriptId")
        if isinstance(script, (str, int)):
            level_scripts.add(str(script))
        prop = get_const(row, "_propertyKey", "propertyKey", "_key", "key")
        if isinstance(prop, str):
            properties.add(prop)
    description = objective.get("description") or {}
    return {
        "index": index,
        "conditionId": condition.get("uniqueId") if isinstance(condition, dict) else "",
        "descriptionKey": description.get("key") if isinstance(description, dict) else "",
        "multiple": bool(objective.get("multiple")),
        "condition": condition_tree(condition),
        "conditionTypes": types,
        "authority": classify_authority(types),
        "dialogFinishes": dialog_finishes,
        "questStateRefs": quest_state_refs,
        "levelScriptIds": sorted(level_scripts),
        "propertyKeys": sorted(properties),
    }


def action_rows(mission: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    action_by_id: dict[Any, dict[str, Any]] = {}
    data_map = ((mission.get("actionMapRaw") or {}).get("dataMap") or {})
    for action in data_map.get("actionList") or []:
        if not isinstance(action, dict):
            continue
        action_id = action.get("_ID")
        facts = {
            key.lstrip("_"): compact_scalar(value)
            for key, value in action.items()
            if key not in {"$type", "_ID", "_uid"} and value not in (None, "", [], {})
        }
        action_by_id[action_id] = {
            "id": action_id,
            "type": type_name(action.get("$type")) or "UnknownAction",
            "facts": facts,
        }
    keys = mission.get("clientActionMapKey") or []
    values = mission.get("clientActionMapValue") or []
    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, key in enumerate(keys):
        if not isinstance(key, dict):
            continue
        quest_id = key.get("questId")
        if not isinstance(quest_id, str):
            continue
        action_id = values[index] if index < len(values) else None
        action = dict(action_by_id.get(action_id) or {"id": action_id, "type": "UnknownAction"})
        action["trigger"] = key.get("action")
        output[quest_id].append(action)
    return dict(output)


def build_mission(mission: dict[str, Any], source_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    mission_id = str(mission.get("missionId") or source_path.stem)
    quest_map = mission.get("questDic") or {}
    main_path = [str(value) for value in mission.get("mainPathQuests") or []]
    main_index = {quest_id: index for index, quest_id in enumerate(main_path)}
    actions = action_rows(mission)
    successors: dict[str, list[str]] = defaultdict(list)
    for raw in quest_map.values():
        if not isinstance(raw, dict):
            continue
        quest_id = str(raw.get("questId") or "")
        for parent in raw.get("prevQuestIdList") or []:
            if isinstance(parent, str) and quest_id:
                successors[parent].append(quest_id)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    condition_counts: Counter[str] = Counter()
    exact_finish_count = 0
    server_placeholder_count = 0
    active_join_count = 0
    failure_count = 0
    external_dependency_count = 0
    annotations = (CASE_STUDIES.get(mission_id) or {}).get("nodes") or {}

    ordered_quests = sorted(
        (row for row in quest_map.values() if isinstance(row, dict)),
        key=lambda row: (
            main_index.get(str(row.get("questId") or ""), 10**6),
            int(row.get("flowIndex") or 0),
            natural_quest_key(str(row.get("questId") or "")),
        ),
    )
    for raw in ordered_quests:
        quest_id = str(raw.get("questId") or "")
        objectives = [
            objective_row(objective, index + 1)
            for index, objective in enumerate(raw.get("objectiveList") or [])
            if isinstance(objective, dict)
        ]
        condition_types = sorted({item for objective in objectives for item in objective["conditionTypes"]})
        condition_counts.update(condition_types)
        dialog_finishes = [item for objective in objectives for item in objective["dialogFinishes"]]
        exact_finish_count += sum(1 for item in dialog_finishes if isinstance(item.get("finishId"), int) and item["finishId"] >= 0)
        if "GameConditionServerPlaceHolder" in condition_types:
            server_placeholder_count += 1
        quest_state_refs = [item for objective in objectives for item in objective["questStateRefs"]]
        if len({item["questId"] for item in quest_state_refs}) >= 2:
            active_join_count += 1
        failed_condition = condition_tree(raw.get("failedCondition"))
        if failed_condition:
            failure_count += 1
        prev = [str(value) for value in raw.get("prevQuestIdList") or [] if isinstance(value, str)]
        authority = classify_authority(condition_types)
        node = {
            "id": quest_id,
            "flowIndex": raw.get("flowIndex", 0),
            "showMode": raw.get("showMode"),
            "questType": raw.get("questType"),
            "mainPath": quest_id in main_index,
            "mainPathOrder": main_index.get(quest_id),
            "prev": prev,
            "successors": sorted(successors.get(quest_id, []), key=natural_quest_key),
            "objectives": objectives,
            "conditionTypes": condition_types,
            "authority": authority,
            "clientActions": actions.get(quest_id, []),
            "failedCondition": failed_condition,
            "network": {
                "outbound": "dialog_finish" if dialog_finishes else (
                    "server_owned" if authority == "server" else (
                        "objective_progress" if objectives else "unresolved"
                    )
                ),
                "inbound": ["quest_start", "quest_succeed"] + (["quest_fail"] if failed_condition else []),
            },
        }
        if quest_id in annotations:
            node["annotation"] = annotations[quest_id]
        nodes.append(node)
        for parent in prev:
            edges.append({
                "source": parent,
                "target": quest_id,
                "type": "predecessor",
                "confidence": "asset_direct",
                "serverDecision": True,
            })
        for objective_index, objective in enumerate(objectives, 1):
            for ref in objective["questStateRefs"]:
                external_source = ref["questId"] not in quest_map
                if external_source:
                    external_dependency_count += 1
                edge = {
                    "source": ref["questId"],
                    "target": quest_id,
                    "type": "condition_dependency",
                    "targetState": ref.get("state"),
                    "objectiveIndex": objective_index,
                    "confidence": "asset_direct",
                }
                if external_source:
                    edge["externalSource"] = True
                edges.append(edge)

    roots = [node["id"] for node in nodes if not node["prev"]]
    fanouts = [node["id"] for node in nodes if len(node["successors"]) > 1]
    multi_prev = [node["id"] for node in nodes if len(node["prev"]) > 1]
    mission_name = mission.get("missionName") or {}
    mission_desc = mission.get("missionDescription") or {}
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "mission": {
            "id": mission_id,
            "nameKey": mission_name.get("key") if isinstance(mission_name, dict) else "",
            "descriptionKey": mission_desc.get("key") if isinstance(mission_desc, dict) else "",
            "levelId": mission.get("levelId") or "",
            "missionType": mission.get("missionType"),
            "rewardId": mission.get("rewardId") or "",
            "mainPath": main_path,
            "entryQuestIds": roots,
            "onMissionAcceptId": mission.get("onMissionAcceptId"),
            "onMissionCompletedId": mission.get("onMissionCompletedId"),
            "onMissionFailedId": mission.get("onMissionFailedId"),
            "source": source_path.relative_to(ROOT).as_posix() if source_path.is_relative_to(ROOT) else source_path.as_posix(),
        },
        "nodes": nodes,
        "edges": sorted(edges, key=lambda row: (row["type"], natural_quest_key(row["source"]), natural_quest_key(row["target"]))),
        "caseStudy": CASE_STUDIES.get(mission_id),
    }
    summary = {
        "id": mission_id,
        "nameKey": payload["mission"]["nameKey"],
        "levelId": payload["mission"]["levelId"],
        "questCount": len(nodes),
        "mainPathCount": len(main_path),
        "entryCount": len(roots),
        "fanoutCount": len(fanouts),
        "multiPrevJoinCount": len(multi_prev),
        "activeJoinCount": active_join_count,
        "exactFinishCount": exact_finish_count,
        "serverPlaceholderCount": server_placeholder_count,
        "failureConditionCount": failure_count,
        "externalDependencyCount": external_dependency_count,
        "conditionTypes": sorted(condition_counts),
        "caseStudy": mission_id in CASE_STUDIES,
        "file": f"missions/{mission_id}.json",
    }
    return payload, summary


def build_all(mission_root: Path, output_root: Path) -> dict[str, Any]:
    if not mission_root.is_dir():
        raise FileNotFoundError(f"MissionRuntimeAsset root not found: {mission_root}")
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    produced: set[str] = set()
    condition_counts: Counter[str] = Counter()
    quest_count = 0
    for path in sorted(mission_root.glob("*.json")):
        if path.name.endswith("_meta.json"):
            continue
        mission = read_json(path)
        if not isinstance(mission, dict) or not isinstance(mission.get("questDic"), dict):
            continue
        payload, summary = build_mission(mission, path)
        target = mission_output / f"{summary['id']}.json"
        write_json(target, payload)
        produced.add(target.name)
        summaries.append(summary)
        quest_count += summary["questCount"]
        condition_counts.update(summary["conditionTypes"])
    for stale in mission_output.glob("*.json"):
        if stale.name not in produced:
            stale.unlink()
    summaries.sort(key=lambda row: natural_quest_key(row["id"]))
    index = {
        "schemaVersion": SCHEMA_VERSION,
        "generated": int(time.time()),
        "source": mission_root.relative_to(ROOT).as_posix() if mission_root.is_relative_to(ROOT) else mission_root.as_posix(),
        "counts": {
            "missions": len(summaries),
            "quests": quest_count,
            "caseStudies": sum(1 for row in summaries if row["caseStudy"]),
        },
        "conditionTypeMissionCounts": dict(sorted(condition_counts.items())),
        "runtimeContract": RUNTIME_CONTRACT,
        "missions": summaries,
    }
    write_json(output_root / "index.json", index)
    return index


def main() -> int:
    args = parse_args()
    index = build_all(args.mission_root.resolve(), args.output_root.resolve())
    print(
        f"Mission pipeline: {index['counts']['missions']} missions, "
        f"{index['counts']['quests']} quests -> {args.output_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
