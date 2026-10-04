"""Project authored observation-station task text into Story document cards.

Ownership comes only from KiteStationEntrustTasksTable.missionId. These cards
are task definitions, not dialogue, playback evidence, or mission scene order.
The existing mission-flow reader supplies objective keys; localization and
publication remain owned by the language bundle.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from scripts.webui.story.bundle_primitives import brace_text, pick_fields, source_ref
from scripts.webui.story.bundle_support import parse_mission


def project_kite_station_tasks(
    table: dict,
    *,
    translate: Callable[[object], str],
    text_trace: Callable[..., dict],
    named_text_trace: Callable[[str], dict | None],
    mission_name: Callable[[str], str],
    mission_flow: Callable[[str], dict | None],
) -> Iterator[dict]:
    """Yield keyword arguments for the bundle's reference-document writer."""
    table_name = "KiteStationEntrustTasksTable"
    kind = "table_kitestationentrusttaskstable"
    for station_id, station in sorted(table.items()):
        tasks = station.get("list") if isinstance(station, dict) else None
        if not isinstance(tasks, dict):
            continue
        for task_id, row in sorted(tasks.items()):
            if not isinstance(row, dict):
                continue
            mission_id = str(row.get("missionId") or "").strip()
            if not mission_id:
                continue
            field_prefix = f"list.{task_id}"
            source = source_ref(
                table_name, station_id,
                pick_fields(row, "missionId", "entrustIdx", "snapshotId", "isGuideMission", "isRepeatable"),
                field=field_prefix,
                evidenceBoundary="direct",
            )
            lines: list[dict] = []

            def table_text(field: str) -> str:
                value = row.get(field)
                return translate(value.get("id")) if isinstance(value, dict) else ""

            def append_table_line(field: str) -> None:
                text = table_text(field)
                if text:
                    lines.append({
                        "id": f"{station_id}.{field_prefix}.{field}",
                        "text": text,
                        "_debug": {
                            **source,
                            "fields": {"text": text_trace(table_name, station_id, f"{field_prefix}.{field}", row.get(field))},
                        },
                    })

            title = mission_name(mission_id) or brace_text(table_text("shotTargetName")) or brace_text(table_text("name")) or mission_id
            # Keep the entrust name when the mission title is a longer instruction.
            if table_text("name") and brace_text(table_text("name")) != title:
                append_table_line("name")
            append_table_line("desc")
            flow = mission_flow(mission_id) or {}
            if not table_text("desc"):
                description = named_text_trace(str(flow.get("missionDescriptionKey") or ""))
                if description and description.get("value"):
                    lines.append({"id": description["rowId"], "text": description["value"], "_debug": description})
            seen_objectives: set[str] = set()
            for quest in flow.get("quests") or []:
                for anchor in quest.get("objectiveAnchors") or []:
                    keys = [anchor.get("descriptionKey"), *(anchor.get("multipleDescriptionKeys") or [])]
                    for key in keys:
                        if not key or key in seen_objectives:
                            continue
                        seen_objectives.add(key)
                        trace = named_text_trace(str(key))
                        if not trace or not trace.get("value"):
                            continue
                        lines.append({
                            "id": str(key),
                            "text": trace["value"],
                            "_debug": {
                                **trace,
                                "missionId": mission_id,
                                "questId": quest.get("id"),
                                "objectiveIndex": anchor.get("index"),
                            },
                        })
            if not seen_objectives or not any(line["id"] in seen_objectives for line in lines):
                append_table_line("shotTargetName")
            append_table_line("completeDesc")
            type_key, _act = parse_mission(mission_id)
            yield {
                "out_key": f"task_{station_id}_{task_id}",
                "mission_id": mission_id,
                "scene": 0,
                "title": title,
                "lines": lines,
                "kind": kind,
                "type_key": type_key,
                "source_debug": source,
                "tags": ["task", kind],
                "search_parts": [station_id, str(task_id), mission_id, title],
            }
