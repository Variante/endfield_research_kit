"""Publish observed runtime traces without changing Mission Pipeline evidence."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


SCHEMA = "missionRuntimeTrace.v1"
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


def _compact_runtime_observation(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "sessionId",
        "seq",
        "monotonicMs",
        "storyKey",
        "playbackType",
        "chainId",
        "triggerStatus",
        "ownershipStatus",
        "levelId",
        "scriptId",
        "headerLocalId",
        "actionLocalId",
        "actionType",
        "route",
    )
    return {key: row[key] for key in keys if key in row}


def publish_mission_runtime_trace(
    index: dict[str, Any],
    output_root: Path,
    trace_bundle_path: Path,
) -> dict[str, Any]:
    """Publish an observed-only runtime overlay without promoting ownership/order."""
    if not trace_bundle_path.is_file():
        raise FileNotFoundError(
            f"Mission runtime trace bundle not found: {trace_bundle_path}"
        )
    bundle = _read_json(trace_bundle_path)
    if not isinstance(bundle, dict) or bundle.get("_schema") != SCHEMA:
        raise ValueError(
            f"Mission runtime trace must use {SCHEMA}: {trace_bundle_path}"
        )
    observations = bundle.get("storyObservations")
    if not isinstance(observations, dict):
        raise ValueError("Mission runtime trace storyObservations must be an object")

    observations_by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for story_key, raw_rows in observations.items():
        if not isinstance(story_key, str) or not isinstance(raw_rows, list):
            raise ValueError("Mission runtime trace observations have an invalid shape")
        for row in raw_rows:
            if not isinstance(row, dict) or str(row.get("storyKey") or "") != story_key:
                raise ValueError(
                    f"Mission runtime trace observation mismatch for {story_key}"
                )
            mission_ids = {
                str(item.get("missionId") or "")
                for item in [
                    *(row.get("activeMissions") or []),
                    *(row.get("activeQuests") or []),
                ]
                if isinstance(item, dict) and item.get("missionId")
            }
            for mission_id in sorted(mission_ids):
                observations_by_mission[mission_id].append(row)

    edges_by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in bundle.get("observedEdges") or []:
        if not isinstance(edge, dict):
            continue
        for mission_id in edge.get("sharedMissionIds") or []:
            if isinstance(mission_id, str) and mission_id:
                edges_by_mission[mission_id].append(edge)
        for quest in edge.get("sharedQuests") or []:
            if isinstance(quest, dict) and quest.get("missionId"):
                mission_id = str(quest["missionId"])
                if edge not in edges_by_mission[mission_id]:
                    edges_by_mission[mission_id].append(edge)

    published_missions = 0
    quest_placements = 0
    mission_context_only = 0
    unmatched_mission_ids = sorted(
        set(observations_by_mission)
        - {
            str(summary.get("id") or "")
            for summary in index.get("missions") or []
            if isinstance(summary, dict)
        }
    )
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        mission_rows = observations_by_mission.get(mission_id) or []
        if not mission_rows:
            continue
        mission_path = output_root / str(summary.get("file") or "")
        if not mission_path.is_file():
            continue
        payload = _read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        nodes = {
            str(node.get("id") or ""): node
            for node in payload.get("nodes") or []
            if isinstance(node, dict) and node.get("id")
        }
        context_only_rows = []
        unique_rows: dict[tuple[str, int, str], dict[str, Any]] = {}
        for row in mission_rows:
            compact = _compact_runtime_observation(row)
            signature = (
                str(compact.get("sessionId") or ""),
                int(compact.get("seq") or 0),
                str(compact.get("storyKey") or ""),
            )
            unique_rows[signature] = compact
            quest_ids = sorted({
                str(item.get("questId") or "")
                for item in row.get("activeQuests") or []
                if isinstance(item, dict)
                and str(item.get("missionId") or "") == mission_id
                and item.get("questId")
            })
            attached = False
            for quest_id in quest_ids:
                node = nodes.get(quest_id)
                if node is None:
                    continue
                node.setdefault("runtimeStoryObservations", []).append(compact)
                quest_placements += 1
                attached = True
            if not attached:
                context_only_rows.append(compact)
                mission_context_only += 1
        for node in nodes.values():
            if node.get("runtimeStoryObservations"):
                node["runtimeStoryObservations"].sort(
                    key=lambda row: (
                        str(row.get("sessionId") or ""),
                        int(row.get("seq") or 0),
                        str(row.get("storyKey") or ""),
                    )
                )
        payload["runtimeTrace"] = {
            "schema": SCHEMA,
            "evidenceClassification": "observed_runtime",
            "ownershipPromotion": False,
            "orderPromotion": False,
            "storyObservationCount": len(unique_rows),
            "questObservationPlacements": sum(
                len(node.get("runtimeStoryObservations") or [])
                for node in nodes.values()
            ),
            "missionContextOnly": context_only_rows,
            "observedEdges": edges_by_mission.get(mission_id, []),
        }
        summary["runtimeStoryObservationCount"] = len(unique_rows)
        summary["runtimeQuestObservationPlacementCount"] = payload[
            "runtimeTrace"
        ]["questObservationPlacements"]
        _write_json(mission_path, payload)
        published_missions += 1

    bundle_summary = bundle.get("summary") or {}
    index["runtimeTrace"] = {
        "schema": SCHEMA,
        "source": _repo_path(trace_bundle_path),
        "evidenceClassification": "observed_runtime",
        "ownershipPromotion": False,
        "orderPromotion": False,
        "evidencePolicy": bundle.get("evidencePolicy") or {},
        "summary": bundle_summary,
        "sessions": bundle.get("sessions") or [],
        "published": {
            "missions": published_missions,
            "questObservationPlacements": quest_placements,
            "missionContextOnlyObservations": mission_context_only,
            "unmatchedMissionIds": unmatched_mission_ids,
        },
        "observedForks": bundle.get("observedForks") or [],
        "observedMerges": bundle.get("observedMerges") or [],
    }
    _write_json(output_root / "index.json", index)
    return bundle
