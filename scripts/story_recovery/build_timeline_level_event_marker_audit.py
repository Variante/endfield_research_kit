#!/usr/bin/env python3
"""Join Timeline RaiseLevelEventMarker objects to LevelScript Story receivers."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX_ROOT = ROOT / "export_full" / "recovered" / "AnimeStudio-cli"
DEFAULT_PIPELINE = ROOT / "webui" / "data" / "mission_pipeline" / "index.json"
DEFAULT_JSON = ROOT / "reports" / "story" / "recovery" / "timeline_level_event_marker_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "story" / "recovery" / "timeline_level_event_marker_audit.md"

MARKER_SCRIPT = "Beyond.Gameplay.Core.RaiseLevelEventMarker"
TRACK_SCRIPT = "UnityEngine.Timeline.MarkerTrack"
TIMELINE_SCRIPT = "UnityEngine.Timeline.TimelineAsset"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        value = path.relative_to(ROOT)
    except ValueError:
        value = path
    return str(value).replace("\\", "/")


def identity(row: dict[str, Any]) -> tuple[str, int]:
    obj = row.get("object") or {}
    return str(obj.get("serializedFile") or ""), int(obj.get("pathId") or 0)


def target_identity(pptr: dict[str, Any]) -> tuple[str, int]:
    target = pptr.get("target") or {}
    expected = pptr.get("expected") or {}
    return (
        str(target.get("serializedFile") or expected.get("serializedFile") or ""),
        int(target.get("pathId") if target.get("pathId") is not None else pptr.get("pathId") or 0),
    )


def scalar_map(row: dict[str, Any]) -> dict[str, Any]:
    return {
        str(item[0]): item[2]
        for item in row.get("scalars") or []
        if isinstance(item, list) and len(item) >= 3
    }


def collect_object_roles(lines: Iterable[str]) -> tuple[dict, list, dict, int]:
    markers: dict[tuple[str, int], dict[str, Any]] = {}
    tracks: list[dict[str, Any]] = []
    timelines: dict[tuple[str, int], dict[str, Any]] = {}
    object_count = 0
    for line in lines:
        row = json.loads(line)
        if row.get("recordType") != "object":
            continue
        object_count += 1
        script = str((row.get("script") or {}).get("fullName") or "")
        if script == MARKER_SCRIPT:
            markers[identity(row)] = row
        elif script == TRACK_SCRIPT:
            tracks.append(row)
        elif script == TIMELINE_SCRIPT:
            timelines[identity(row)] = row
    return markers, tracks, timelines, object_count


def join_markers(markers: dict, tracks: list, timelines: dict, source: str) -> list[dict[str, Any]]:
    joined: list[dict[str, Any]] = []
    joined_marker_ids: set[tuple[str, int]] = set()
    for track in tracks:
        parent = None
        for pptr in track.get("pptrs") or []:
            if pptr.get("path") == "$.m_Parent":
                parent = timelines.get(target_identity(pptr))
                break
        for pptr in track.get("pptrs") or []:
            if not str(pptr.get("path") or "").startswith("$.m_Markers.m_Objects["):
                continue
            marker_id = target_identity(pptr)
            marker = markers.get(marker_id)
            if marker is None:
                continue
            joined_marker_ids.add(marker_id)
            scalars = scalar_map(marker)
            marker_obj = marker.get("object") or {}
            track_obj = track.get("object") or {}
            timeline_obj = (parent or {}).get("object") or {}
            joined.append(
                {
                    "source": source,
                    "eventName": str(scalars.get("$.eventName") or ""),
                    "parameters": [
                        {"path": path, "value": value}
                        for path, value in sorted(scalars.items())
                        if path.startswith("$.paramList")
                    ],
                    "marker": {
                        "serializedFile": marker_obj.get("serializedFile"),
                        "pathId": marker_obj.get("pathId"),
                        "name": marker.get("name"),
                    },
                    "markerTrack": {
                        "serializedFile": track_obj.get("serializedFile"),
                        "pathId": track_obj.get("pathId"),
                        "name": track.get("name"),
                    },
                    "timeline": {
                        "serializedFile": timeline_obj.get("serializedFile"),
                        "pathId": timeline_obj.get("pathId"),
                        "name": (parent or {}).get("name"),
                    },
                }
            )
    for marker_id, marker in markers.items():
        if marker_id in joined_marker_ids:
            continue
        scalars = scalar_map(marker)
        marker_obj = marker.get("object") or {}
        joined.append(
            {
                "source": source,
                "eventName": str(scalars.get("$.eventName") or ""),
                "parameters": [
                    {"path": path, "value": value}
                    for path, value in sorted(scalars.items())
                    if path.startswith("$.paramList")
                ],
                "marker": {
                    "serializedFile": marker_obj.get("serializedFile"),
                    "pathId": marker_obj.get("pathId"),
                    "name": marker.get("name"),
                },
                "markerTrack": None,
                "timeline": None,
            }
        )
    return joined


def enrich_marker_payload(row: dict[str, Any], index_root: Path) -> None:
    marker = row.get("marker") or {}
    name = str(marker.get("name") or "")
    path_id = int(marker.get("pathId") or 0)
    filename = f"{name}_p{path_id & ((1 << 64) - 1):016X}.json"
    object_path = (
        index_root
        / str(row.get("source") or "")
        / "json_by_type"
        / "MonoBehaviour"
        / filename
    )
    row["markerObjectJson"] = (
        display_path(object_path)
        if object_path.is_file()
        else None
    )
    row["timelineTimeSeconds"] = None
    row["retroactive"] = None
    row["emitOnce"] = None
    if not object_path.is_file():
        return
    payload = json.loads(object_path.read_text(encoding="utf-8"))
    row["timelineTimeSeconds"] = payload.get("m_Time")
    row["retroactive"] = payload.get("_Retroactive")
    row["emitOnce"] = payload.get("_EmitOnce")
    row["parameters"] = payload.get("paramList") or []


def collect_story_routes(pipeline: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_event: dict[str, list[dict[str, Any]]] = {}
    manifest = ((pipeline.get("storyCoverage") or {}).get("storyTriggerManifest") or {})
    for story_key, story in manifest.items():
        stack = list((story or {}).get("routes") or [])
        while stack:
            value = stack.pop()
            if isinstance(value, list):
                stack.extend(value)
                continue
            if not isinstance(value, dict):
                continue
            selector = value.get("selector") or {}
            event_key = str(selector.get("eventKey") or "")
            if event_key and value.get("sourceFile"):
                route = {
                    "storyKey": story_key,
                    "eventKey": event_key,
                    "levelId": value.get("levelId") or selector.get("levelId"),
                    "scriptId": value.get("scriptId") or selector.get("listenerScriptId"),
                    "listenerHeaderLocalId": selector.get("listenerHeaderLocalId") or value.get("headerLocalId"),
                    "sourceFile": value.get("sourceFile"),
                    "steps": value.get("steps") or [],
                }
                bucket = by_event.setdefault(event_key, [])
                signature = json.dumps(route, ensure_ascii=False, sort_keys=True)
                if all(json.dumps(item, ensure_ascii=False, sort_keys=True) != signature for item in bucket):
                    bucket.append(route)
            stack.extend(value.values())
    for routes in by_event.values():
        routes.sort(key=lambda row: (str(row.get("storyKey")), str(row.get("sourceFile"))))
    return by_event


def build_report(index_root: Path, pipeline_path: Path) -> dict[str, Any]:
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    story_routes = collect_story_routes(pipeline)
    rows: list[dict[str, Any]] = []
    sources = []
    total_objects = 0
    for source in ("Persistent", "StreamingAssets"):
        object_path = index_root / source / "object_index" / "objects.jsonl.gz"
        summary_path = index_root / source / "object_index" / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        with gzip.open(object_path, "rt", encoding="utf-8") as handle:
            markers, tracks, timelines, object_count = collect_object_roles(handle)
        total_objects += object_count
        source_rows = join_markers(markers, tracks, timelines, source)
        rows.extend(source_rows)
        sources.append(
            {
                "source": source,
                "objectIndex": str(object_path.relative_to(ROOT)).replace("\\", "/"),
                "summary": str(summary_path.relative_to(ROOT)).replace("\\", "/"),
                "summaryComplete": bool(summary.get("complete")),
                "summaryObjectCount": int((summary.get("counts") or {}).get("objects") or 0),
                "scannedObjectRecordCount": object_count,
                "objectsSha256": ((summary.get("outputs") or {}).get("objects") or {}).get("sha256"),
                "markerCount": len(markers),
                "markerTrackCount": len(tracks),
                "timelineAssetCount": len(timelines),
            }
        )
    for row in rows:
        enrich_marker_payload(row, index_root)
        row["storyRoutes"] = story_routes.get(row["eventName"], [])
    rows.sort(
        key=lambda row: (
            row["eventName"],
            str((row.get("timeline") or {}).get("name") or ""),
            str((row.get("marker") or {}).get("serializedFile") or ""),
            int((row.get("marker") or {}).get("pathId") or 0),
        )
    )
    event_counts = Counter(row["eventName"] or "<empty>" for row in rows)
    return {
        "schema": "timelineLevelEventMarkerAudit.v1",
        "status": "validated_complete_object_indexes",
        "sources": sources,
        "missionPipeline": {
            "path": str(pipeline_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(pipeline_path),
        },
        "summary": {
            "scannedObjectRecordCount": total_objects,
            "markerCount": len(rows),
            "markerWithTrackAndTimelineCount": sum(
                1 for row in rows if row.get("markerTrack") and row.get("timeline")
            ),
            "markerWithStoryRouteCount": sum(1 for row in rows if row["storyRoutes"]),
            "markerPayloadJsonResolvedCount": sum(
                1 for row in rows if row.get("markerObjectJson")
            ),
            "uniqueEventNameCount": len(event_counts),
            "eventNameCounts": dict(sorted(event_counts.items())),
        },
        "markers": rows,
        "evidenceBoundary": (
            "A marker-to-Timeline edge requires exact same-object-index PPtr identity; a Story route "
            "requires an exact eventName == LevelScript selector.eventKey join. This proves a serialized "
            "Timeline event can reach that receiver and its local Story action. It does not prove the "
            "Timeline was selected at runtime, a conditional branch ran, mission ownership, or order "
            "between unrelated Story files."
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Timeline level-event marker audit",
        "",
        f"Status: `{report['status']}`",
        "",
        f"- object records scanned: {summary['scannedObjectRecordCount']:,}",
        f"- `RaiseLevelEventMarker` objects: {summary['markerCount']:,}",
        f"- markers joined to MarkerTrack + TimelineAsset: {summary['markerWithTrackAndTimelineCount']:,}",
        f"- markers joined to an exact LevelScript Story route: {summary['markerWithStoryRouteCount']:,}",
        f"- marker payload JSON resolved for exact time: {summary['markerPayloadJsonResolvedCount']:,}",
        "",
        "## Story-bearing marker routes",
        "",
        "| Event | Timeline time | Timeline | Story | Receiver |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for row in report["markers"]:
        timeline = str((row.get("timeline") or {}).get("name") or "<unresolved>")
        for route in row["storyRoutes"]:
            receiver = (
                f"{route.get('levelId')}/{route.get('scriptId')} "
                f"header {route.get('listenerHeaderLocalId')}"
            )
            lines.append(
                f"| `{row['eventName'] or '<empty>'}` | "
                f"{row.get('timelineTimeSeconds') if row.get('timelineTimeSeconds') is not None else ''} | "
                f"`{timeline}` | "
                f"`{route['storyKey']}` | `{receiver}` |"
            )
    if not any(row["storyRoutes"] for row in report["markers"]):
        lines.append("| _none_ |  |  |  |  |")
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            report["evidenceBoundary"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-root", type=Path, default=DEFAULT_INDEX_ROOT)
    parser.add_argument("--mission-pipeline", type=Path, default=DEFAULT_PIPELINE)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.index_root, args.mission_pipeline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(
        f"timeline marker audit: {report['summary']['markerCount']} markers, "
        f"{report['summary']['markerWithStoryRouteCount']} with Story routes"
    )
    print(f"wrote {args.out}")
    print(f"wrote {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
