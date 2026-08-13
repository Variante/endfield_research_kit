"""Publish graph-neutral Mission Pipeline shells from offline recovery rows."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    path.write_text(encoded + "\n", encoding="utf-8", newline="\n")


def _repo_path(path: Path) -> str:
    path = path.resolve()
    return (
        path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else path.as_posix()
    )


def _natural_quest_key(value: str) -> tuple[str, int, str]:
    mission, marker, suffix = str(value).partition("_q#")
    try:
        number = int(suffix) if marker else 10**9
    except ValueError:
        number = 10**9
    return mission, number, suffix


def offline_story_kind(story_key: str) -> str:
    """Preserve the Story kind for denominator-neutral recovery overlays."""
    if story_key.startswith("radio_"):
        return "radio"
    if story_key.startswith("cutscene_"):
        return "cutscene"
    if story_key.startswith("sns_"):
        return "sns"
    if story_key.startswith("black_"):
        return "black"
    if story_key.startswith(("dlg_", "misc_dlg_")):
        return "dlg"
    return "text"


def publish_offline_recovery_mission_shells(
    index: dict[str, Any],
    output_root: Path,
    offline_recovery: dict[str, Any],
    gap_queue_path: Path,
    *,
    schema_version: str,
) -> list[str]:
    """Publish navigable graph-neutral shells for exhausted non-runtime missions.

    A Story mission can exist in authored tables without a MissionRuntimeAsset.
    Its exact-build recovery boundary still belongs in Mission Pipeline, but a
    shell must never imply quests, ownership, playback, or order edges.
    """
    if offline_recovery.get("status") != "active":
        return []
    queue = _read_json(gap_queue_path)
    if not isinstance(queue, dict):
        return []
    queue_rows = {
        str(row.get("mission") or ""): row
        for row in queue.get("missions") or []
        if isinstance(row, dict) and row.get("mission")
    }
    existing = {
        str(row.get("id") or "")
        for row in index.get("missions") or []
        if isinstance(row, dict) and row.get("id")
    }
    overlay = offline_recovery.get("storyTriggerManifestOverlay") or {}
    keys_by_mission: dict[str, list[str]] = defaultdict(list)
    kind_by_key: dict[str, str] = {}
    for story_key, entry in overlay.items():
        recovery = (
            entry.get("offlineRecovery") or entry.get("contentProvenance")
        ) if isinstance(entry, dict) else None
        mission_id = str(
            (recovery or {}).get("missionId")
            or (entry or {}).get("nominalMissionId")
            or ""
        )
        if mission_id and mission_id not in existing:
            keys_by_mission[mission_id].append(str(story_key))
            kind_by_key[str(story_key)] = str(entry.get("kind") or "")

    published: list[str] = []
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    for mission_id in sorted(keys_by_mission, key=_natural_quest_key):
        order_row = queue_rows.get(mission_id)
        if not isinstance(order_row, dict):
            continue
        story_keys = sorted(keys_by_mission[mission_id], key=_natural_quest_key)
        metrics = order_row.get("metrics") or {}
        components = [
            {
                "id": f"p{index}",
                "sceneKeys": [story_key],
                "cyclic": False,
                "internalEdgeIndexes": [],
            }
            for index, story_key in enumerate(story_keys, start=1)
        ]
        story_order = {
            "mission": mission_id,
            "summary": {
                "sceneCount": int(metrics.get("sceneCount") or len(story_keys)),
                "strongEdgeCount": 0,
                "weakEdgeCount": 0,
                "cycleCount": 0,
                "unorderedScenePairs": int(metrics.get("totalScenePairs") or 0),
                "isolatedSceneCount": int(
                    metrics.get("isolatedScenes") or len(story_keys)
                ),
                "weakOnlySceneCount": 0,
            },
            "nodes": [
                {
                    "key": story_key,
                    "kind": kind_by_key.get(story_key)
                        or offline_story_kind(story_key),
                    "membership": "index",
                    "component": component["id"],
                    "relationStatus": "isolated",
                }
                for story_key, component in zip(story_keys, components)
            ],
            "components": components,
            "componentEdges": [],
            "reducedComponentEdges": [],
            "topologicalLayers": [[row["id"] for row in components]],
            "directEdges": [],
            "containments": [],
            "cycles": [],
            "branches": {
                "sceneGraphOptions": [],
                "nativeControlBranches": [],
                "nativeControlMerges": [],
                "nativeOrderedSequences": [],
                "nativeRelatedActionTopologies": [],
                "dialogLineOptions": [],
                "questForks": [],
                "questMerges": [],
            },
            "isolatedSceneKeys": story_keys,
            "weakOnlySceneKeys": [],
            "unknownSceneKeys": story_keys,
            "unresolvedSourceNodes": [],
            "sourceGapQueue": order_row,
        }
        payload = {
            "schemaVersion": schema_version,
            "mission": {
                "id": mission_id,
                "nameKey": "",
                "descriptionKey": "",
                "levelId": "",
                "missionType": None,
                "rewardId": "",
                "mainPath": [],
                "entryQuestIds": [],
                "nativeRuntimeBindings": [],
                "source": _repo_path(gap_queue_path),
                "offlineRecoveryShell": True,
                "sourceBoundary": (
                    "No MissionRuntimeAsset exists in the current export; this "
                    "shell exposes exact graph-neutral Story recovery only."
                ),
            },
            "nodes": [],
            "edges": [],
            "caseStudy": None,
            "missionGraph": {"upstream": {}, "downstream": {}},
            "envTalkContext": [],
            "storyOrder": story_order,
        }
        _write_json(mission_output / f"{mission_id}.json", payload)
        summary = {
            "id": mission_id,
            "nameKey": "",
            "levelId": "",
            "questCount": 0,
            "mainPathCount": 0,
            "entryCount": 0,
            "fanoutCount": 0,
            "multiPrevJoinCount": 0,
            "activeJoinCount": 0,
            "exactFinishCount": 0,
            "serverPlaceholderCount": 0,
            "serverPlaceholderQuestCount": 0,
            "failureConditionCount": 0,
            "externalDependencyCount": 0,
            "submitItemConditionCount": 0,
            "submitItemQuestCount": 0,
            "submitItemDialogCoGateCount": 0,
            "submitItemLevelScriptCoGateCount": 0,
            "nativeRuntimeBindingCount": 0,
            "activityStageHostCount": 0,
            "activityStageHostedQuestCount": 0,
            "trackingInfoCount": 0,
            "trackingObjectiveCount": 0,
            "missionPropertyCount": 0,
            "conditionTypes": [],
            "caseStudy": False,
            "file": f"missions/{mission_id}.json",
            "offlineRecoveryShell": True,
            "offlineRecoveryStoryCount": len(story_keys),
            "storyOrderSceneCount": int(metrics.get("sceneCount") or 0),
            "storyOrderStrongEdgeCount": int(
                metrics.get("strongEdgeCount") or 0
            ),
            "storyOrderCycleCount": int(metrics.get("sourceCycles") or 0),
        }
        index.setdefault("missions", []).append(summary)
        published.append(mission_id)
        existing.add(mission_id)
    index["missions"].sort(key=lambda row: _natural_quest_key(row["id"]))
    index.setdefault("counts", {})["missions"] = len(index["missions"])
    index["counts"]["offlineRecoveryMissionShells"] = len(published)
    return published
