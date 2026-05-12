#!/usr/bin/env python3
"""Emit richer Endfield voice/audio recovery reports from the source graph.

This tool is intentionally standalone and stdlib-only. It reads the SQLite
graph produced by tools/endfield_source_graph.py and writes focused voice/audio
reports without mutating the graph.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "reports" / "source_graph"
DEFAULT_DB = GRAPH_DIR / "endfield_source_graph.sqlite"
DEFAULT_OUT_DIR = GRAPH_DIR / "voice_audio"

AUDIO_HINT_RE = re.compile(r"\bau_[A-Za-z0-9_]{2,160}\b")


def parse_json_text(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def compact_text(value: Any, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def edge_payload(row: sqlite3.Row, prefix: str) -> dict[str, Any]:
    edge_id = row[f"{prefix}_edge_id"]
    if edge_id is None:
        return {}
    return {
        "id": edge_id,
        "kind": row[f"{prefix}_kind"],
        "source": row[f"{prefix}_source"],
        "evidence": row[f"{prefix}_evidence"],
        "data": parse_json_text(row[f"{prefix}_data"]),
    }


def node_payload(row: sqlite3.Row, prefix: str) -> dict[str, Any]:
    node_id = row[f"{prefix}_node"]
    if node_id is None:
        return {}
    return {
        "node": node_id,
        "id": row[f"{prefix}_name"],
        "source": row[f"{prefix}_source"],
        "path": row[f"{prefix}_path"],
        "data": parse_json_text(row[f"{prefix}_data"]),
    }


def audio_hints(*values: Any) -> list[str]:
    hints: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
        for match in AUDIO_HINT_RE.findall(text):
            key = match.lower()
            if key not in seen:
                seen.add(key)
                hints.append(match)
    return hints


def limit_items(items: list[Any], limit: int) -> list[Any]:
    if limit <= 0:
        return items
    return items[:limit]


def story_where_clause(story_filters: list[str], alias: str = "story") -> tuple[str, list[str]]:
    if not story_filters:
        return "", []
    clauses = []
    params: list[str] = []
    for story_filter in story_filters:
        needle = f"%{story_filter}%"
        clauses.append(f"({alias}.id LIKE ? OR {alias}.name LIKE ? OR {alias}.path LIKE ?)")
        params.extend([needle, needle, needle])
    return " AND (" + " OR ".join(clauses) + ")", params


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"Graph database not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_audio_paths(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    rows = conn.execute(
        """
        SELECT
            e.id AS audio_path_edge_id,
            e.kind AS audio_path_kind,
            e.source AS audio_path_source,
            e.evidence AS audio_path_evidence,
            e.data AS audio_path_data,
            audio.id AS audio_node,
            file.id AS file_node,
            file.name AS file_name,
            file.source AS file_source,
            file.path AS file_path,
            file.data AS file_data
        FROM edges e
        JOIN nodes audio ON audio.id = e.src
        JOIN nodes file ON file.id = e.dst
        WHERE e.kind = 'audio_path'
        ORDER BY audio.name, file.path
        """
    ).fetchall()
    by_audio: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_audio[row["audio_node"]].append(
            {
                "edge": edge_payload(row, "audio_path"),
                "file": {
                    "node": row["file_node"],
                    "name": row["file_name"],
                    "source": row["file_source"],
                    "path": row["file_path"],
                    "data": parse_json_text(row["file_data"]),
                },
            }
        )
    return by_audio


def fetch_audio_definitions(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    rows = conn.execute(
        """
        SELECT
            e.id AS defines_audio_edge_id,
            e.kind AS defines_audio_kind,
            e.source AS defines_audio_source,
            e.evidence AS defines_audio_evidence,
            e.data AS defines_audio_data,
            audio.id AS audio_node,
            row.id AS row_node,
            row.name AS row_name,
            row.source AS row_source,
            row.path AS row_path,
            row.data AS row_data
        FROM edges e
        JOIN nodes row ON row.id = e.src
        JOIN nodes audio ON audio.id = e.dst
        WHERE e.kind = 'defines_audio'
        ORDER BY audio.name, row.name
        """
    ).fetchall()
    by_audio: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        data = parse_json_text(row["row_data"])
        by_audio[row["audio_node"]].append(
            {
                "edge": edge_payload(row, "defines_audio"),
                "row": {
                    "node": row["row_node"],
                    "id": row["row_name"],
                    "source": row["row_source"],
                    "path": row["row_path"],
                    "data": data,
                },
            }
        )
    return by_audio


def fetch_audio_speaker_channels(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    rows = conn.execute(
        """
        SELECT
            e.id AS speaker_edge_id,
            e.kind AS speaker_kind,
            e.source AS speaker_source,
            e.evidence AS speaker_evidence,
            e.data AS speaker_data,
            audio.id AS audio_node,
            actor.id AS actor_node,
            actor.name AS actor_name,
            actor.source AS actor_source,
            actor.path AS actor_path,
            actor.data AS actor_data
        FROM edges e
        JOIN nodes audio ON audio.id = e.src
        JOIN nodes actor ON actor.id = e.dst
        WHERE e.kind = 'speaker_channel'
        ORDER BY audio.name, actor.name
        """
    ).fetchall()
    by_audio: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_audio[row["audio_node"]].append(
            {
                "edge": edge_payload(row, "speaker"),
                "actor": {
                    "node": row["actor_node"],
                    "id": row["actor_name"],
                    "source": row["actor_source"],
                    "path": row["actor_path"],
                    "data": parse_json_text(row["actor_data"]),
                },
            }
        )
    return by_audio


def fetch_line_audio_rows(conn: sqlite3.Connection, story_filters: list[str]) -> list[sqlite3.Row]:
    where, params = story_where_clause(story_filters)
    return conn.execute(
        f"""
        SELECT
            has_line.id AS has_line_edge_id,
            has_line.kind AS has_line_kind,
            has_line.source AS has_line_source,
            has_line.evidence AS has_line_evidence,
            has_line.data AS has_line_data,
            uses_audio.id AS uses_audio_edge_id,
            uses_audio.kind AS uses_audio_kind,
            uses_audio.source AS uses_audio_source,
            uses_audio.evidence AS uses_audio_evidence,
            uses_audio.data AS uses_audio_data,
            spoken_by.id AS spoken_by_edge_id,
            spoken_by.kind AS spoken_by_kind,
            spoken_by.source AS spoken_by_source,
            spoken_by.evidence AS spoken_by_evidence,
            spoken_by.data AS spoken_by_data,
            story.id AS story_node,
            story.name AS story_name,
            story.source AS story_source,
            story.path AS story_path,
            story.data AS story_data,
            line.id AS line_node,
            line.name AS line_name,
            line.source AS line_source,
            line.path AS line_path,
            line.data AS line_data,
            audio.id AS audio_node,
            audio.name AS audio_name,
            audio.source AS audio_source,
            audio.path AS audio_path,
            audio.data AS audio_data,
            actor.id AS actor_node,
            actor.name AS actor_name,
            actor.source AS actor_source,
            actor.path AS actor_path,
            actor.data AS actor_data
        FROM edges has_line
        JOIN nodes story ON story.id = has_line.src AND story.kind = 'story'
        JOIN nodes line ON line.id = has_line.dst AND line.kind = 'line'
        JOIN edges uses_audio ON uses_audio.src = line.id AND uses_audio.kind = 'uses_audio'
        JOIN nodes audio ON audio.id = uses_audio.dst AND audio.kind = 'audio'
        LEFT JOIN edges spoken_by ON spoken_by.src = line.id AND spoken_by.kind = 'spoken_by'
        LEFT JOIN nodes actor ON actor.id = spoken_by.dst
        WHERE has_line.kind = 'has_line'{where}
        ORDER BY story.name, has_line.evidence, line.name, audio.name
        """,
        params,
    ).fetchall()


def first_audio_definition_value(definitions: list[dict[str, Any]], *keys: str) -> Any:
    for definition in definitions:
        data = definition.get("row", {}).get("data", {})
        for key in keys:
            if key in data and data[key] not in ("", None):
                return data[key]
    return None


def make_relationship_record(
    row: sqlite3.Row,
    audio_paths: dict[str, list[dict[str, Any]]],
    audio_definitions: dict[str, list[dict[str, Any]]],
    audio_speakers: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    line = node_payload(row, "line")
    story = node_payload(row, "story")
    audio = node_payload(row, "audio")
    actor = node_payload(row, "actor")
    line_data = line.get("data", {})
    audio_data = audio.get("data", {})
    definitions = audio_definitions.get(row["audio_node"], [])
    paths = audio_paths.get(row["audio_node"], [])
    speaker_channels = audio_speakers.get(row["audio_node"], [])

    audio_path = None
    if paths:
        audio_path = paths[0].get("file", {}).get("path")
    if not audio_path:
        audio_path = audio_data.get("path") or audio.get("path")
    if not audio_path:
        audio_path = first_audio_definition_value(definitions, "path")

    speaker_id = (
        line_data.get("actorId")
        or (actor.get("id") if actor else None)
        or first_audio_definition_value(definitions, "speaker", "speakerChannel")
        or (speaker_channels[0]["actor"]["id"] if speaker_channels else None)
        or ""
    )
    speaker_name = line_data.get("actor") or (actor.get("id") if actor else None) or speaker_id

    audio["path"] = audio_path
    audio["duration"] = audio_data.get("duration") or first_audio_definition_value(definitions, "duration", "wavDuration")
    audio["speakerChannel"] = audio_data.get("speaker") or first_audio_definition_value(definitions, "speaker", "speakerChannel")
    audio["voType"] = audio_data.get("voType") or first_audio_definition_value(definitions, "voType")
    audio["codec"] = audio_data.get("codec") or first_audio_definition_value(definitions, "codec")
    audio["definitions"] = definitions
    audio["paths"] = paths
    audio["speakerChannels"] = speaker_channels

    return {
        "story": {
            "node": story.get("node"),
            "id": story.get("id"),
            "source": story.get("source"),
            "path": story.get("path"),
            "data": story.get("data", {}),
        },
        "line": {
            "node": line.get("node"),
            "id": line.get("id"),
            "source": line.get("source"),
            "path": line.get("path"),
            "actor": line_data.get("actor"),
            "actorId": line_data.get("actorId"),
            "audioField": line_data.get("audio"),
            "text": line_data.get("text"),
            "timestamp": line_data.get("timestamp"),
            "duration": line_data.get("duration"),
        },
        "speaker": {
            "id": speaker_id,
            "name": speaker_name,
            "spokenByActor": actor,
        },
        "audio": audio,
        "edges": {
            "hasLine": edge_payload(row, "has_line"),
            "usesAudio": edge_payload(row, "uses_audio"),
            "spokenBy": edge_payload(row, "spoken_by"),
            "definesAudio": [definition["edge"] for definition in definitions],
            "audioPath": [path["edge"] for path in paths],
        },
    }


def story_key(record: dict[str, Any]) -> str:
    return record.get("story", {}).get("id") or record.get("story", {}).get("node") or "(unknown-story)"


def speaker_key(record: dict[str, Any]) -> str:
    speaker = record.get("speaker", {})
    return speaker.get("id") or speaker.get("name") or "(unknown-speaker)"


def build_groups(records: list[dict[str, Any]], limit: int) -> tuple[dict[str, Any], dict[str, Any]]:
    by_story: dict[str, dict[str, Any]] = {}
    by_speaker: dict[str, dict[str, Any]] = {}
    for record in records:
        story_id = story_key(record)
        speaker_id = speaker_key(record)
        audio_id = record.get("audio", {}).get("id")
        missing_path = not bool(record.get("audio", {}).get("path"))

        story_group = by_story.setdefault(
            story_id,
            {
                "story": record.get("story"),
                "lineCount": 0,
                "audioCount": 0,
                "missingAudioPathCount": 0,
                "speakers": Counter(),
                "examples": [],
            },
        )
        story_group["lineCount"] += 1
        story_group["audioCount"] += 1 if audio_id else 0
        story_group["missingAudioPathCount"] += 1 if missing_path else 0
        story_group["speakers"][speaker_id] += 1
        if limit <= 0 or len(story_group["examples"]) < min(limit, 20):
            story_group["examples"].append(record)

        speaker_group = by_speaker.setdefault(
            speaker_id,
            {
                "speaker": record.get("speaker"),
                "lineCount": 0,
                "audioCount": 0,
                "missingAudioPathCount": 0,
                "stories": Counter(),
                "examples": [],
            },
        )
        speaker_group["lineCount"] += 1
        speaker_group["audioCount"] += 1 if audio_id else 0
        speaker_group["missingAudioPathCount"] += 1 if missing_path else 0
        speaker_group["stories"][story_id] += 1
        if limit <= 0 or len(speaker_group["examples"]) < min(limit, 20):
            speaker_group["examples"].append(record)

    for group in by_story.values():
        group["speakers"] = dict(group["speakers"].most_common())
    for group in by_speaker.values():
        group["stories"] = dict(group["stories"].most_common())

    by_story = dict(sorted(by_story.items(), key=lambda item: (-item[1]["lineCount"], item[0])))
    by_speaker = dict(sorted(by_speaker.items(), key=lambda item: (-item[1]["lineCount"], item[0])))
    return by_story, by_speaker


def fetch_unresolved_line_mentions(conn: sqlite3.Connection, story_filters: list[str], limit: int) -> list[dict[str, Any]]:
    where, params = story_where_clause(story_filters)
    line_limit = "" if limit <= 0 else " LIMIT ?"
    line_params: list[Any] = list(params)
    if limit > 0:
        line_params.append(limit)
    rows = conn.execute(
        f"""
        SELECT
            has_line.id AS has_line_edge_id,
            has_line.kind AS has_line_kind,
            has_line.source AS has_line_source,
            has_line.evidence AS has_line_evidence,
            has_line.data AS has_line_data,
            story.id AS story_node,
            story.name AS story_name,
            story.source AS story_source,
            story.path AS story_path,
            story.data AS story_data,
            line.id AS line_node,
            line.name AS line_name,
            line.source AS line_source,
            line.path AS line_path,
            line.data AS line_data
        FROM edges has_line
        JOIN nodes story ON story.id = has_line.src AND story.kind = 'story'
        JOIN nodes line ON line.id = has_line.dst AND line.kind = 'line'
        WHERE has_line.kind = 'has_line'
          AND NOT EXISTS (
              SELECT 1 FROM edges uses_audio
              WHERE uses_audio.src = line.id AND uses_audio.kind = 'uses_audio'
          )
          AND (line.id LIKE '%au_%' OR line.name LIKE '%au_%' OR line.data LIKE '%au_%')
          {where}
        ORDER BY story.name, has_line.evidence, line.name
        {line_limit}
        """,
        line_params,
    ).fetchall()

    candidates: list[dict[str, Any]] = []
    seen_lines: set[str] = set()
    for row in rows:
        line = node_payload(row, "line")
        story = node_payload(row, "story")
        hints = audio_hints(line.get("node"), line.get("id"), line.get("data", {}))
        if not hints:
            continue
        seen_lines.add(line["node"])
        candidates.append(
            {
                "story": story,
                "line": {
                    "node": line.get("node"),
                    "id": line.get("id"),
                    "source": line.get("source"),
                    "path": line.get("path"),
                    "actor": line.get("data", {}).get("actor"),
                    "actorId": line.get("data", {}).get("actorId"),
                    "text": line.get("data", {}).get("text"),
                },
                "audioHints": hints,
                "source": "line",
                "edges": {"hasLine": edge_payload(row, "has_line")},
            }
        )

    alias_limit = limit if limit > 0 else 5000
    if len(candidates) < alias_limit:
        alias_rows = conn.execute(
            """
            SELECT alias, node_id
            FROM aliases
            WHERE alias LIKE '%au_%'
            LIMIT ?
            """,
            (max(alias_limit * 20, 1000),),
        ).fetchall()
        for alias_row in alias_rows:
            line_node = alias_row["node_id"]
            if line_node in seen_lines or not str(line_node).startswith("line:"):
                continue
            link = conn.execute(
                f"""
                SELECT
                    has_line.id AS has_line_edge_id,
                    has_line.kind AS has_line_kind,
                    has_line.source AS has_line_source,
                    has_line.evidence AS has_line_evidence,
                    has_line.data AS has_line_data,
                    story.id AS story_node,
                    story.name AS story_name,
                    story.source AS story_source,
                    story.path AS story_path,
                    story.data AS story_data,
                    line.id AS line_node,
                    line.name AS line_name,
                    line.source AS line_source,
                    line.path AS line_path,
                    line.data AS line_data
                FROM nodes line
                JOIN edges has_line ON has_line.dst = line.id AND has_line.kind = 'has_line'
                JOIN nodes story ON story.id = has_line.src AND story.kind = 'story'
                WHERE line.id = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM edges uses_audio
                      WHERE uses_audio.src = line.id AND uses_audio.kind = 'uses_audio'
                  )
                  {where}
                LIMIT 1
                """,
                [line_node] + params,
            ).fetchone()
            if not link:
                continue
            line = node_payload(link, "line")
            story = node_payload(link, "story")
            seen_lines.add(line_node)
            candidates.append(
                {
                    "story": story,
                    "line": {
                        "node": line.get("node"),
                        "id": line.get("id"),
                        "source": line.get("source"),
                        "path": line.get("path"),
                        "actor": line.get("data", {}).get("actor"),
                        "actorId": line.get("data", {}).get("actorId"),
                        "text": line.get("data", {}).get("text"),
                    },
                    "audioHints": audio_hints(alias_row["alias"]),
                    "source": "alias",
                    "alias": alias_row["alias"],
                    "edges": {"hasLine": edge_payload(link, "has_line")},
                }
            )
            if limit > 0 and len(candidates) >= limit:
                break
    return candidates


def fetch_orphan_audio_definitions(
    conn: sqlite3.Connection,
    audio_paths: dict[str, list[dict[str, Any]]],
    audio_definitions: dict[str, list[dict[str, Any]]],
    limit: int,
) -> list[dict[str, Any]]:
    sql_limit = "" if limit <= 0 else " LIMIT ?"
    params: list[Any] = [] if limit <= 0 else [limit]
    rows = conn.execute(
        f"""
        SELECT audio.id AS audio_node, audio.name AS audio_name, audio.source AS audio_source,
               audio.path AS audio_path, audio.data AS audio_data
        FROM nodes audio
        WHERE audio.kind = 'audio'
          AND EXISTS (
              SELECT 1 FROM edges defines_audio
              WHERE defines_audio.dst = audio.id AND defines_audio.kind = 'defines_audio'
          )
          AND NOT EXISTS (
              SELECT 1 FROM edges uses_audio
              WHERE uses_audio.dst = audio.id AND uses_audio.kind = 'uses_audio'
          )
        ORDER BY audio.name
        {sql_limit}
        """,
        params,
    ).fetchall()
    orphans: list[dict[str, Any]] = []
    for row in rows:
        node = {
            "node": row["audio_node"],
            "id": row["audio_name"],
            "source": row["audio_source"],
            "path": row["audio_path"],
            "data": parse_json_text(row["audio_data"]),
        }
        orphans.append(
            {
                "audio": node,
                "definitions": audio_definitions.get(row["audio_node"], []),
                "paths": audio_paths.get(row["audio_node"], []),
            }
        )
    return orphans


def build_report(conn: sqlite3.Connection, story_filters: list[str], limit: int, term: str = "") -> dict[str, Any]:
    started = time.time()
    audio_paths = fetch_audio_paths(conn)
    audio_definitions = fetch_audio_definitions(conn)
    audio_speakers = fetch_audio_speaker_channels(conn)

    rows = fetch_line_audio_rows(conn, story_filters)
    records = [make_relationship_record(row, audio_paths, audio_definitions, audio_speakers) for row in rows]
    if term:
        lowered = term.lower()
        records = [
            record
            for record in records
            if lowered
            in json.dumps(
                {
                    "story": record.get("story", {}).get("id"),
                    "line": record.get("line", {}).get("id"),
                    "text": record.get("line", {}).get("text"),
                    "speaker": record.get("speaker", {}),
                    "audio": {
                        "id": record.get("audio", {}).get("id"),
                        "path": record.get("audio", {}).get("path"),
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
            ).lower()
        ]

    missing_audio_paths = [record for record in records if not record.get("audio", {}).get("path")]
    by_story, by_speaker = build_groups(records, limit)
    unresolved_candidates = fetch_unresolved_line_mentions(conn, story_filters, limit)
    orphan_audio = fetch_orphan_audio_definitions(conn, audio_paths, audio_definitions, limit)

    story_counts = Counter(story_key(record) for record in records)
    speaker_counts = Counter(speaker_key(record) for record in records)
    audio_ids = {record.get("audio", {}).get("node") for record in records if record.get("audio", {}).get("node")}
    path_count = sum(1 for record in records if record.get("audio", {}).get("path"))

    return {
        "generated": int(time.time()),
        "durationSeconds": round(time.time() - started, 3),
        "storyFilters": story_filters,
        "inspectTerm": term,
        "limit": limit,
        "summary": {
            "lineAudioRelationships": len(records),
            "stories": len(story_counts),
            "speakers": len(speaker_counts),
            "audioNodes": len(audio_ids),
            "relationshipsWithAudioPath": path_count,
            "relationshipsMissingAudioPath": len(missing_audio_paths),
            "unresolvedMentionCandidatesSampled": len(unresolved_candidates),
            "orphanAudioDefinitionsSampled": len(orphan_audio),
        },
        "topStories": [{"story": key, "relationships": count} for key, count in story_counts.most_common(25)],
        "topSpeakers": [{"speaker": key, "relationships": count} for key, count in speaker_counts.most_common(25)],
        "relationships": limit_items(records, limit),
        "missingAudioPaths": limit_items(missing_audio_paths, limit),
        "unresolvedMentionCandidates": unresolved_candidates,
        "orphanAudioDefinitions": orphan_audio,
        "byStory": by_story,
        "bySpeaker": by_speaker,
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def group_summary(groups: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    rows = []
    for key, group in list(groups.items())[:limit]:
        rows.append(
            {
                "id": key,
                "lineCount": group.get("lineCount"),
                "audioCount": group.get("audioCount"),
                "missingAudioPathCount": group.get("missingAudioPathCount"),
                "speakers": group.get("speakers"),
                "stories": group.get("stories"),
            }
        )
    return rows


def write_reports(report: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "report": out_dir / "voice_audio_report.json",
        "by_story": out_dir / "by_story.json",
        "by_speaker": out_dir / "by_speaker.json",
        "missing_audio_paths": out_dir / "missing_audio_paths.json",
        "unresolved_candidates": out_dir / "unresolved_candidates.json",
        "orphan_audio_definitions": out_dir / "orphan_audio_definitions.json",
        "summary": out_dir / "summary.md",
    }
    write_json(paths["report"], report)
    write_json(paths["by_story"], report["byStory"])
    write_json(paths["by_speaker"], report["bySpeaker"])
    write_json(paths["missing_audio_paths"], report["missingAudioPaths"])
    write_json(paths["unresolved_candidates"], report["unresolvedMentionCandidates"])
    write_json(paths["orphan_audio_definitions"], report["orphanAudioDefinitions"])
    paths["summary"].write_text(render_summary_markdown(report, paths), encoding="utf-8")
    return paths


def render_summary_markdown(report: dict[str, Any], paths: dict[str, Path]) -> str:
    summary = report["summary"]
    filters = ", ".join(report.get("storyFilters") or []) or "(none)"
    lines = [
        "# Voice/Audio Recovery Summary",
        "",
        f"- Generated: `{report['generated']}`",
        f"- Duration: `{report['durationSeconds']}` seconds",
        f"- Story filters: `{filters}`",
        f"- Detail limit: `{report['limit']}` (`0` means all records)",
        "",
        "## Totals",
        "",
        f"- Line/audio relationships: `{summary['lineAudioRelationships']}`",
        f"- Stories: `{summary['stories']}`",
        f"- Speakers: `{summary['speakers']}`",
        f"- Audio nodes used by story lines: `{summary['audioNodes']}`",
        f"- Relationships with audio paths: `{summary['relationshipsWithAudioPath']}`",
        f"- Relationships missing audio paths: `{summary['relationshipsMissingAudioPath']}`",
        f"- Unresolved line/alias `au_...` candidates sampled: `{summary['unresolvedMentionCandidatesSampled']}`",
        f"- AudioDialog definitions not used by story lines sampled: `{summary['orphanAudioDefinitionsSampled']}`",
        "",
        "## Output Files",
        "",
    ]
    for label, path in paths.items():
        lines.append(f"- `{label}`: `{path.as_posix()}`")

    lines.extend(["", "## Top Stories", "", "| Story | Relationships |", "| --- | ---: |"])
    for item in report.get("topStories", [])[:15]:
        lines.append(f"| `{item['story']}` | {item['relationships']} |")

    lines.extend(["", "## Top Speakers", "", "| Speaker | Relationships |", "| --- | ---: |"])
    for item in report.get("topSpeakers", [])[:15]:
        lines.append(f"| `{item['speaker']}` | {item['relationships']} |")

    missing = report.get("missingAudioPaths", [])[:10]
    if missing:
        lines.extend(["", "## Missing Audio Path Examples", "", "| Story | Line | Audio | Speaker |", "| --- | --- | --- | --- |"])
        for record in missing:
            lines.append(
                "| `{story}` | `{line}` | `{audio}` | `{speaker}` |".format(
                    story=record.get("story", {}).get("id"),
                    line=record.get("line", {}).get("id"),
                    audio=record.get("audio", {}).get("id"),
                    speaker=record.get("speaker", {}).get("id") or "",
                )
            )

    unresolved = report.get("unresolvedMentionCandidates", [])[:10]
    if unresolved:
        lines.extend(["", "## Unresolved Mention Examples", "", "| Story | Line | Hints | Source |", "| --- | --- | --- | --- |"])
        for record in unresolved:
            hints = ", ".join(f"`{hint}`" for hint in record.get("audioHints", []))
            lines.append(
                "| `{story}` | `{line}` | {hints} | `{source}` |".format(
                    story=record.get("story", {}).get("id"),
                    line=record.get("line", {}).get("id"),
                    hints=hints or "",
                    source=record.get("source"),
                )
            )
    lines.append("")
    return "\n".join(lines)


def run_build(args: argparse.Namespace) -> int:
    with connect(args.db) as conn:
        report = build_report(conn, args.story or [], args.limit)
    paths = write_reports(report, args.out_dir)
    print(f"Wrote voice/audio report: {paths['summary']}")
    print(
        "relationships={lineAudioRelationships} missing_paths={relationshipsMissingAudioPath} "
        "unresolved_candidates={unresolvedMentionCandidatesSampled}".format(**report["summary"])
    )
    return 0


def run_inspect(args: argparse.Namespace) -> int:
    with connect(args.db) as conn:
        report = build_report(conn, args.story or [], args.limit, term=args.term)
    slim = {
        "summary": report["summary"],
        "topStories": report["topStories"][:10],
        "topSpeakers": report["topSpeakers"][:10],
        "relationships": report["relationships"],
        "missingAudioPaths": report["missingAudioPaths"],
        "unresolvedMentionCandidates": report["unresolvedMentionCandidates"],
    }
    print(json.dumps(slim, ensure_ascii=False, indent=2))
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"SQLite graph path (default: {DEFAULT_DB})")
    parser.add_argument("--limit", type=int, default=2000, help="Maximum detailed records per report section; 0 means all")
    parser.add_argument("--story", action="append", default=[], help="Filter story id/name/path by substring; may repeat")


def parse_args(argv: list[str]) -> argparse.Namespace:
    if argv and argv[0] in {"inspect", "query"}:
        parser = argparse.ArgumentParser(description="Inspect matching voice/audio graph relationships")
        parser.add_argument("command", choices=("inspect", "query"))
        parser.add_argument("term", help="Substring to match against story, line, speaker, audio id, or audio path")
        add_common_args(parser)
        return parser.parse_args(argv)

    parser = argparse.ArgumentParser(description="Build voice/audio recovery reports from the Endfield source graph")
    add_common_args(parser)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory for JSON and Markdown reports (default: {DEFAULT_OUT_DIR})",
    )
    args = parser.parse_args(argv)
    args.command = "build"
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.limit < 0:
        raise SystemExit("--limit must be 0 or greater")
    if getattr(args, "command", "build") in {"inspect", "query"}:
        return run_inspect(args)
    return run_build(args)


if __name__ == "__main__":
    raise SystemExit(main())
