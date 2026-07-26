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
from story_builder.context import LEVELDATA_DIR, LEVELSCRIPT_DIR  # noqa: E402
from story_builder.level_bindings import (  # noqa: E402
    _parse_leveldata_mission_host_name,
    parse_leveldata_levelscript_brief_dictionary,
)
from story_builder.levelscript_binary import (  # noqa: E402
    decode_levelscript_binary_file,
)


SCHEMA = "nativeReceiverActivationFrontier.v1"
DEFAULT_PIPELINE_INDEX = ROOT / "webui" / "data" / "mission_pipeline" / "index.json"
DEFAULT_PIPELINE_MISSION_ROOT = (
    ROOT / "webui" / "data" / "mission_pipeline" / "missions"
)
DEFAULT_MANUAL_CONTROL_AUDIT = (
    ROOT / "reports" / "mission_order" / "levelscript_manual_control_audit.json"
)
DEFAULT_JSON = STORY_RECOVERY_REPORTS_DIR / "native_receiver_activation_frontier.json"
DEFAULT_MARKDOWN = STORY_RECOVERY_REPORTS_DIR / "native_receiver_activation_frontier.md"


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
) -> dict[str, Any]:
    mission_ids = {
        safe_text(row.get("id"))
        for row in index_payload.get("missions") or []
        if isinstance(row, dict) and safe_text(row.get("id"))
    }
    incoming_by_target = manual_control_targets(manual_control_payload)
    subgames_by_script = subgame_script_bindings(index_payload)
    consumers_by_script = mission_runtime_script_consumers(mission_root)
    rows: list[dict[str, Any]] = []
    classes: Counter[str] = Counter()
    start_types: Counter[str] = Counter()
    host_shapes: Counter[str] = Counter()

    for receiver in receiver_script_rows(index_payload):
        level_id = receiver["levelId"]
        script_id = receiver["scriptId"]
        script_path = levelscript_root / level_id / f"{script_id}.json"
        levelscript = decode_levelscript_binary_file(script_path, script_id)
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
