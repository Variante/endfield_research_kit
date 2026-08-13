"""Project one validated MissionRuntime payload into WebUI mission data."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _natural_quest_key(value: str) -> tuple[str, int, str]:
    mission, marker, suffix = str(value).partition("_q#")
    try:
        number = int(suffix) if marker else 10**9
    except ValueError:
        number = 10**9
    return mission, number, suffix


def build_mission(
    mission: dict[str, Any],
    source_path: Path,
    native_runtime_bindings: list[dict[str, Any]] | None = None,
    activity_quest_level_hosts: dict[str, list[dict[str, Any]]] | None = None,
    mission_graph_entry: dict[str, Any] | None = None,
    env_talk_contexts: list[dict[str, Any]] | None = None,
    *,
    schema_version: str,
    repo_root: Path,
    case_studies: dict[str, Any],
    action_projector: Any,
    objective_projector: Any,
    task_dependency_validator: Any,
    condition_projector: Any,
    authority_classifier: Any,
    quest_fork_builder: Any,
    mission_property_projector: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mission_id = str(mission.get("missionId") or source_path.stem)
    quest_map = mission.get("questDic") or {}
    main_path = [str(value) for value in mission.get("mainPathQuests") or []]
    main_index = {quest_id: index for index, quest_id in enumerate(main_path)}
    actions = action_projector(mission)
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
    server_placeholder_quest_count = 0
    active_join_count = 0
    failure_count = 0
    external_dependency_count = 0
    submit_item_count = 0
    submit_item_quest_count = 0
    submit_item_dialog_co_gate_count = 0
    submit_item_level_script_co_gate_count = 0
    level_script_task_dependency_count = 0
    annotations = (case_studies.get(mission_id) or {}).get("nodes") or {}

    ordered_quests = sorted(
        (row for row in quest_map.values() if isinstance(row, dict)),
        key=lambda row: (
            main_index.get(str(row.get("questId") or ""), 10**6),
            int(row.get("flowIndex") or 0),
            _natural_quest_key(str(row.get("questId") or "")),
        ),
    )
    for raw in ordered_quests:
        quest_id = str(raw.get("questId") or "")
        objectives = [
            objective_projector(objective, index + 1)
            for index, objective in enumerate(raw.get("objectiveList") or [])
            if isinstance(objective, dict)
        ]
        condition_types = sorted({item for objective in objectives for item in objective["conditionTypes"]})
        condition_counts.update(condition_types)
        dialog_finishes = [item for objective in objectives for item in objective["dialogFinishes"]]
        submission_checks = [
            item
            for objective in objectives
            for item in objective["submissionChecks"]
        ]
        for objective in objectives:
            objective["levelScriptTaskDependencies"] = [
                task_dependency_validator(
                    dependency,
                    mission_id=mission_id,
                    quest_id=quest_id,
                    mission_source=source_path,
                )
                for dependency in objective.get("levelScriptTaskDependencies") or []
            ]
        level_script_task_dependencies_for_quest = [
            dependency
            for objective in objectives
            for dependency in objective.get("levelScriptTaskDependencies") or []
        ]
        level_script_task_dependency_count += len(
            level_script_task_dependencies_for_quest
        )
        submission_dialog_co_gates = [
            item
            for objective in objectives
            for item in objective["submissionDialogCoGates"]
        ]
        submission_level_script_co_gates = [
            item
            for objective in objectives
            for item in objective["submissionLevelScriptCoGates"]
        ]
        submit_item_count += len(submission_checks)
        if submission_checks:
            submit_item_quest_count += 1
        submit_item_dialog_co_gate_count += len(submission_dialog_co_gates)
        submit_item_level_script_co_gate_count += len(
            submission_level_script_co_gates
        )
        exact_finish_count += sum(1 for item in dialog_finishes if isinstance(item.get("finishId"), int) and item["finishId"] >= 0)
        placeholder_condition_ids = [
            condition_id
            for objective in objectives
            for condition_id in objective["serverPlaceholderConditionIds"]
        ]
        server_placeholder_count += len(placeholder_condition_ids)
        if placeholder_condition_ids:
            server_placeholder_quest_count += 1
        quest_state_refs = [item for objective in objectives for item in objective["questStateRefs"]]
        if len({item["questId"] for item in quest_state_refs}) >= 2:
            active_join_count += 1
        failed_condition = condition_projector(raw.get("failedCondition"))
        if failed_condition:
            failure_count += 1
        prev = [str(value) for value in raw.get("prevQuestIdList") or [] if isinstance(value, str)]
        authority = authority_classifier(condition_types)
        node = {
            "id": quest_id,
            "flowIndex": raw.get("flowIndex", 0),
            "showMode": raw.get("showMode"),
            "questType": raw.get("questType"),
            "mainPath": quest_id in main_index,
            "mainPathOrder": main_index.get(quest_id),
            "prev": prev,
            "successors": sorted(successors.get(quest_id, []), key=_natural_quest_key),
            "objectives": objectives,
            "submissionChecks": submission_checks,
            "submissionDialogCoGates": submission_dialog_co_gates,
            "submissionLevelScriptCoGates": submission_level_script_co_gates,
            "levelScriptTaskDependencies": level_script_task_dependencies_for_quest,
            "serverPlaceholderKeys": [
                {"questId": quest_id, "conditionId": condition_id}
                for condition_id in placeholder_condition_ids
            ],
            "conditionTypes": condition_types,
            "authority": authority,
            "clientActions": actions.get(quest_id, []),
            "activityStageHosts": list(
                (activity_quest_level_hosts or {}).get(quest_id, [])
            ),
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

    quest_topology = quest_fork_builder(nodes, source_path)
    if quest_topology["validation"]["status"] != "validated":
        first = quest_topology["validation"]["failures"][0]
        raise RuntimeError(
            "validator=quest_fork_semantics "
            f"gate={first['gate']} mission={first['mission']} "
            f"quest={first.get('questId') or '-'} "
            f"expected={first['expected']!r} actual={first['actual']!r} "
            f"source={first['sourceFile']} "
            f"sourceHashes={first['sourceHashes']!r}"
        )
    roots = [node["id"] for node in nodes if not node["prev"]]
    fanouts = [node["id"] for node in nodes if len(node["successors"]) > 1]
    multi_prev = [node["id"] for node in nodes if len(node["prev"]) > 1]
    mission_name = mission.get("missionName") or {}
    mission_desc = mission.get("missionDescription") or {}
    mission_task_dependencies = [
        {**dependency, "questId": node["id"], "objectiveIndex": objective["index"]}
        for node in nodes
        for objective in node.get("objectives") or []
        for dependency in objective.get("levelScriptTaskDependencies") or []
    ]
    payload = {
        "schemaVersion": schema_version,
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
            "nativeRuntimeBindings": list(native_runtime_bindings or []),
            "levelScriptTaskDependencies": mission_task_dependencies,
            "source": source_path.relative_to(repo_root).as_posix() if source_path.is_relative_to(repo_root) else source_path.as_posix(),
        },
        "nodes": nodes,
        "edges": sorted(edges, key=lambda row: (row["type"], _natural_quest_key(row["source"]), _natural_quest_key(row["target"]))),
        "caseStudy": case_studies.get(mission_id),
        # Cross-mission relations recovered from authored mission/quest state
        # conditions. Only ``requiresCompleted`` carries precedence; the other
        # relations are co-active or mutually exclusive and must not be read as
        # ordering. See story_builder/mission_dependency_graph.py.
        "missionGraph": mission_graph_entry or {"upstream": {}, "downstream": {}},
        "questTopology": quest_topology,
        # Ambient envTalk lines configured on an NPC proxy that a quest of this
        # mission tracks. Navigation/configuration context only -- never
        # playback ownership. See story_builder/envtalk_attachment.py.
        "envTalkContext": sorted(
            env_talk_contexts or [],
            key=lambda row: (_natural_quest_key(row.get("questId") or ""), row.get("storyKey") or ""),
        ),
    }
    properties = mission_property_projector(mission)
    if properties:
        payload["mission"]["properties"] = properties
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
        "serverPlaceholderQuestCount": server_placeholder_quest_count,
        "failureConditionCount": failure_count,
        "questForkSemanticCount": quest_topology["counts"]["forks"],
        "questForkGuardedCount": quest_topology["counts"]["guardedForks"],
        "questForkStructureCounts": quest_topology["counts"]["structures"],
        "questForkOutcomeCounts": quest_topology["counts"]["outcomes"],
        "externalDependencyCount": external_dependency_count,
        "submitItemConditionCount": submit_item_count,
        "submitItemQuestCount": submit_item_quest_count,
        "submitItemDialogCoGateCount": submit_item_dialog_co_gate_count,
        "submitItemLevelScriptCoGateCount": (
            submit_item_level_script_co_gate_count
        ),
        "levelScriptTaskDependencyCount": level_script_task_dependency_count,
        "nativeRuntimeBindingCount": len(native_runtime_bindings or []),
        "activityStageHostCount": sum(
            len(node.get("activityStageHosts") or []) for node in nodes
        ),
        "activityStageHostedQuestCount": sum(
            1 for node in nodes if node.get("activityStageHosts")
        ),
        "trackingInfoCount": sum(
            len(objective.get("tracking") or [])
            for node in nodes
            for objective in node.get("objectives") or []
        ),
        "trackingObjectiveCount": sum(
            1
            for node in nodes
            for objective in node.get("objectives") or []
            if objective.get("tracking")
        ),
        "missionPropertyCount": len(properties),
        "conditionTypes": sorted(condition_counts),
        "caseStudy": mission_id in case_studies,
        "file": f"missions/{mission_id}.json",
    }
    return payload, summary
