#!/usr/bin/env python3
"""Emit map/level reconstruction indexes from the Endfield source graph."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "reports" / "source_graph"
DEFAULT_DB = GRAPH_DIR / "endfield_source_graph.sqlite"
DEFAULT_OUT_DIR = GRAPH_DIR / "map_levels"

RELATED_NODE_KINDS = ("asset", "video", "unity_asset")
SELECTED_TABLES = (
    "AudioDialog",
    "AudioSequenceDialog",
    "CharacterTable",
    "DialogSummaryMapTable",
    "DialogSummaryTable",
    "InteractiveMissionDataTable",
    "LevelDescTable",
    "MapIdTable",
    "MapMarkInsTable",
    "MissionExtraInfoTable",
    "SceneAreaTable",
    "SpecialLevelToMapTable",
)
MAP_TABLES = {"MapIdTable", "MapMarkInsTable"}
LABEL_KEYS = (
    "label",
    "displayName",
    "showName",
    "name",
    "title",
    "markName",
    "description",
    "desc",
    "text",
)
LEVEL_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]+\d+_(?:lv|fc)\d+)(?=$|[^A-Za-z0-9])", re.IGNORECASE)
MAP_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])(?:map|base)\d+(?=$|[^A-Za-z0-9])", re.IGNORECASE)


def parse_json_text(text: Any, default: Any = None) -> Any:
    if text is None:
        return default
    if not isinstance(text, str):
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def slash(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def safe_filename(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return clean.strip("._") or "unnamed"


def compact_text(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def compact_value(value: Any, depth: int = 3, list_limit: int = 12) -> Any:
    if depth <= 0:
        if isinstance(value, dict):
            return f"dict[{len(value)}]"
        if isinstance(value, list):
            return f"list[{len(value)}]"
        if isinstance(value, str):
            return compact_text(value)
        return value
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= list_limit:
                out["..."] = f"{len(value) - list_limit} more"
                break
            out[str(key)] = compact_value(item, depth - 1, list_limit)
        return out
    if isinstance(value, list):
        out = [compact_value(item, depth - 1, list_limit) for item in value[:list_limit]]
        if len(value) > list_limit:
            out.append(f"... {len(value) - list_limit} more")
        return out
    if isinstance(value, str):
        return compact_text(value, 500)
    return value


def value_texts(value: Any) -> list[str]:
    texts: list[str] = []
    stack = [value]
    while stack:
        item = stack.pop()
        if item is None:
            continue
        if isinstance(item, str):
            texts.append(item)
        elif isinstance(item, (int, float)):
            texts.append(str(item))
        elif isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return texts


def extract_label(value: Any) -> str | None:
    if isinstance(value, str):
        text = compact_text(value)
        return text or None
    if not isinstance(value, dict):
        return None
    for key in LABEL_KEYS:
        if key not in value:
            continue
        candidate = value.get(key)
        if isinstance(candidate, dict):
            nested = extract_label(candidate)
            if nested:
                return nested
        elif isinstance(candidate, str):
            text = compact_text(candidate)
            if text:
                return text
    return None


def extract_pos(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    candidate = value.get("pos") or value.get("position") or value.get("coord") or value.get("coordinates")
    if not isinstance(candidate, dict):
        return None
    out: dict[str, Any] = {}
    for axis in ("x", "y", "z"):
        if axis in candidate:
            out[axis] = candidate[axis]
    return out or None


def derive_map_id(level_id: str | None) -> str | None:
    if not level_id:
        return None
    text = str(level_id).strip()
    match = re.match(r"^([A-Za-z]+\d+)(?:_|$)", text)
    if match:
        return match.group(1)
    if "_" in text:
        return text.split("_", 1)[0]
    return text or None


def node_summary(row: sqlite3.Row | dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = parse_json_text(row["data"], None)
    summary: dict[str, Any] = {
        "nodeId": row["id"],
        "kind": row["kind"],
        "name": row["name"],
        "source": row["source"],
    }
    if row["path"]:
        summary["path"] = row["path"]
    label = extract_label(data)
    if label:
        summary["label"] = label
    if data not in (None, {}, []):
        summary["data"] = compact_value(data)
    return {key: value for key, value in summary.items() if value is not None}


def add_unique_record(items: list[dict[str, Any]], record: dict[str, Any], key: str = "nodeId") -> None:
    record_key = record.get(key)
    if record_key is None:
        record_key = json.dumps(record, sort_keys=True, ensure_ascii=False)
    if any(item.get(key) == record_key for item in items):
        return
    items.append(record)


class MapLevelIndexer:
    def __init__(self, *, db_path: Path, out_dir: Path, level_filters: list[str], limit: int) -> None:
        self.db_path = db_path
        self.out_dir = out_dir
        self.level_filters = {item.lower() for item in level_filters if item}
        self.limit = max(0, limit)
        self.conn: sqlite3.Connection | None = None
        self.levels: dict[str, dict[str, Any]] = {}
        self.map_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.unresolved: dict[str, list[dict[str, Any]]] = {
            "marksWithoutLevel": [],
            "tableRowsWithoutLevel": [],
        }
        self.unresolved_counts: Counter[str] = Counter()
        self.unresolved_seen: dict[str, set[str]] = defaultdict(set)
        self.table_counts: Counter[str] = Counter()
        self.mark_row_node_ids: set[str] = set()

    @property
    def db(self) -> sqlite3.Connection:
        if self.conn is None:
            raise RuntimeError("database is not open")
        return self.conn

    def open(self) -> None:
        if not self.db_path.exists():
            raise FileNotFoundError(f"source graph database not found: {self.db_path}")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def build(self) -> dict[str, Any]:
        self.open()
        try:
            self.load_levels()
            self.load_map_id_rows()
            self.load_marks()
            self.load_relevant_table_rows()
            selected_levels = self.selected_level_records()
            maps = self.build_maps(selected_levels)
            self.attach_related_media(selected_levels, maps)
            payload = self.payload(selected_levels, maps)
            self.write_outputs(payload, selected_levels)
            return payload
        finally:
            self.close()

    def load_levels(self) -> None:
        rows = self.db.execute(
            """
            SELECT id, kind, name, source, path, data
            FROM nodes
            WHERE kind = 'level'
            ORDER BY name
            """
        ).fetchall()
        for row in rows:
            level_id = row["name"] or row["id"].split(":", 1)[-1]
            self.ensure_level(level_id, node=row)

    def ensure_level(self, level_id: str, node: sqlite3.Row | None = None) -> dict[str, Any]:
        map_id = derive_map_id(level_id)
        if level_id not in self.levels:
            self.levels[level_id] = {
                "levelId": level_id,
                "mapId": map_id,
                "node": node_summary(node),
                "aliases": [],
                "marks": [],
                "tableRows": [],
                "assets": [],
                "videos": [],
                "unityAssets": [],
                "evidence": {
                    "hasLevelNode": node is not None,
                    "markCount": 0,
                    "tableRowCount": 0,
                },
            }
        elif node is not None and not self.levels[level_id].get("node"):
            self.levels[level_id]["node"] = node_summary(node)
            self.levels[level_id]["evidence"]["hasLevelNode"] = True
        return self.levels[level_id]

    def load_map_id_rows(self) -> None:
        for row in self.fetch_table_rows(["MapIdTable"]):
            record = self.table_row_record(row)
            row_key = record.get("key") or row["name"]
            data = parse_json_text(row["data"], {})
            map_id = derive_map_id(str(row_key)) if "_" in str(row_key) else str(row_key)
            if isinstance(data, dict):
                map_id = data.get("mapId") or data.get("id") or map_id
            if not map_id:
                continue
            record["mapId"] = map_id
            self.map_rows[map_id].append(record)

    def load_marks(self) -> None:
        rows = self.db.execute(
            """
            SELECT
                mark.id AS markNodeId,
                mark.kind AS markKind,
                mark.name AS markName,
                mark.source AS markSource,
                mark.path AS markPath,
                mark.data AS markData,
                level.id AS levelNodeId,
                level.name AS edgeLevelId,
                row.id AS rowNodeId,
                row.kind AS rowKind,
                row.name AS rowName,
                row.source AS rowSource,
                row.path AS rowPath,
                row.data AS rowData
            FROM nodes mark
            LEFT JOIN edges level_edge
                ON level_edge.dst = mark.id AND level_edge.kind = 'has_map_mark'
            LEFT JOIN nodes level
                ON level.id = level_edge.src
            LEFT JOIN edges row_edge
                ON row_edge.dst = mark.id AND row_edge.kind = 'defines_map_mark'
            LEFT JOIN nodes row
                ON row.id = row_edge.src
            WHERE mark.kind = 'map_mark'
            ORDER BY edgeLevelId, mark.name
            """
        ).fetchall()
        for row in rows:
            mark_data = parse_json_text(row["markData"], {}) or {}
            row_data = parse_json_text(row["rowData"], {}) or {}
            level_id = row["edgeLevelId"] or mark_data.get("levelId") or row_data.get("levelId")
            mark_id = row["markName"] or row["markNodeId"].split(":", 1)[-1]
            mark_info_id = mark_data.get("markInfoId") or row_data.get("markInfoId")
            mark_record = {
                "nodeId": row["markNodeId"],
                "markId": mark_id,
                "levelId": level_id,
                "mapId": derive_map_id(level_id),
                "markInfoId": mark_info_id,
                "pos": extract_pos(mark_data) or extract_pos(row_data),
                "label": extract_label(mark_data) or extract_label(row_data),
                "source": row["markSource"],
                "levelLink": {
                    "viaEdge": bool(row["levelNodeId"]),
                    "levelNodeId": row["levelNodeId"],
                },
            }
            mark_record = {key: value for key, value in mark_record.items() if value not in (None, [], {})}
            if row["rowNodeId"]:
                table_row = self.table_row_record(
                    {
                        "id": row["rowNodeId"],
                        "kind": row["rowKind"],
                        "name": row["rowName"],
                        "source": row["rowSource"],
                        "path": row["rowPath"],
                        "data": row["rowData"],
                    }
                )
                mark_record["tableRow"] = table_row
                self.mark_row_node_ids.add(row["rowNodeId"])

            if level_id:
                level = self.ensure_level(str(level_id))
                add_unique_record(level["marks"], mark_record)
                if row["rowNodeId"]:
                    add_unique_record(level["tableRows"], mark_record["tableRow"])
            else:
                self.add_unresolved("marksWithoutLevel", mark_record)

    def load_relevant_table_rows(self) -> None:
        known_levels = set(self.levels)
        known_maps = {derive_map_id(level_id) for level_id in known_levels}
        known_maps.update(self.map_rows)
        known_maps.discard(None)

        for row in self.fetch_table_rows(SELECTED_TABLES):
            self.table_counts[row["source"]] += 1
            if row["id"] in self.mark_row_node_ids or row["source"] == "MapIdTable":
                continue
            record = self.table_row_record(row)
            data = parse_json_text(row["data"], {})
            level_ids, map_ids = self.extract_row_ids(record, data, known_levels, known_maps)
            linked = False
            for level_id in sorted(level_ids):
                level = self.ensure_level(level_id)
                add_unique_record(level["tableRows"], record)
                linked = True
            if not linked and map_ids:
                record["mapOnlyLink"] = True
                record["candidateMapIds"] = sorted(map_ids)
                for map_id in sorted(map_ids):
                    add_unique_record(self.map_rows[map_id], record)
                linked = True
            if not linked and self.is_unresolved_table_candidate(record, data, level_ids, map_ids):
                record["candidateLevelIds"] = sorted(level_ids)
                record["candidateMapIds"] = sorted(map_ids)
                self.add_unresolved("tableRowsWithoutLevel", record)

    def selected_level_records(self) -> list[dict[str, Any]]:
        selected = []
        for level_id in sorted(self.levels):
            level = self.levels[level_id]
            level["marks"].sort(key=lambda item: item.get("markId") or "")
            level["tableRows"].sort(key=lambda item: (item.get("table") or "", item.get("key") or ""))
            level["evidence"]["markCount"] = len(level["marks"])
            level["evidence"]["tableRowCount"] = len(level["tableRows"])
            if self.include_level(level):
                selected.append(level)
        return selected

    def build_maps(self, selected_levels: list[dict[str, Any]]) -> list[dict[str, Any]]:
        maps: dict[str, dict[str, Any]] = {}

        def ensure_map(map_id: str) -> dict[str, Any]:
            if map_id not in maps:
                maps[map_id] = {
                    "mapId": map_id,
                    "tableRows": list(self.map_rows.get(map_id, [])),
                    "levels": [],
                    "assets": [],
                    "videos": [],
                    "unityAssets": [],
                    "markCount": 0,
                }
            return maps[map_id]

        for level in selected_levels:
            map_id = level.get("mapId") or derive_map_id(level["levelId"]) or "unknown"
            map_record = ensure_map(map_id)
            map_record["levels"].append(
                {
                    "levelId": level["levelId"],
                    "markCount": len(level["marks"]),
                    "tableRowCount": len(level["tableRows"]),
                    "assetCount": 0,
                    "videoCount": 0,
                    "unityAssetCount": 0,
                    "outputFile": f"levels/{safe_filename(level['levelId'])}.json",
                }
            )
            map_record["markCount"] += len(level["marks"])

        for map_id, rows in self.map_rows.items():
            if self.include_map(map_id) and map_id not in maps:
                maps[map_id] = {
                    "mapId": map_id,
                    "tableRows": rows,
                    "levels": [],
                    "assets": [],
                    "videos": [],
                    "unityAssets": [],
                    "markCount": 0,
                }

        for map_record in maps.values():
            map_record["levels"].sort(key=lambda item: item["levelId"])
            map_record["tableRows"].sort(key=lambda item: (item.get("table") or "", item.get("key") or ""))
        return [maps[map_id] for map_id in sorted(maps)]

    def attach_related_media(self, selected_levels: list[dict[str, Any]], maps: list[dict[str, Any]]) -> None:
        if self.limit == 0:
            return
        map_lookup = {item["mapId"]: item for item in maps}
        for level in selected_levels:
            terms = self.level_terms(level)
            direct = self.direct_related_nodes(self.level_node_ids(level), self.limit)
            alias = self.alias_related_nodes(terms, self.limit)
            self.assign_related(level, direct + alias)

        for map_record in maps:
            terms = [map_record["mapId"]]
            terms.extend(str(row.get("key")) for row in map_record.get("tableRows") or [] if row.get("key"))
            self.assign_related(map_record, self.alias_related_nodes(terms, self.limit))

        for level in selected_levels:
            map_id = level.get("mapId")
            if map_id in map_lookup:
                for kind_key in ("assets", "videos", "unityAssets"):
                    for record in level.get(kind_key) or []:
                        add_unique_record(map_lookup[map_id][kind_key], record)

        for map_record in maps:
            level_counts = {item["levelId"]: item for item in map_record["levels"]}
            for level in selected_levels:
                if level.get("mapId") != map_record["mapId"]:
                    continue
                summary = level_counts.get(level["levelId"])
                if summary:
                    summary["assetCount"] = len(level.get("assets") or [])
                    summary["videoCount"] = len(level.get("videos") or [])
                    summary["unityAssetCount"] = len(level.get("unityAssets") or [])

    def payload(self, selected_levels: list[dict[str, Any]], maps: list[dict[str, Any]]) -> dict[str, Any]:
        selected_marks = sum(len(level["marks"]) for level in selected_levels)
        selected_rows = sum(len(level["tableRows"]) for level in selected_levels)
        unresolved = {
            key: value[: self.limit or None]
            for key, value in self.unresolved.items()
        }
        totals = {
            "maps": len(maps),
            "levels": len(selected_levels),
            "marks": selected_marks,
            "linkedTableRows": selected_rows,
            "linkedMapTableRows": sum(len(item.get("tableRows") or []) for item in maps),
            "unresolvedMarks": self.unresolved_counts["marksWithoutLevel"],
            "unresolvedTableRows": self.unresolved_counts["tableRowsWithoutLevel"],
            "relatedAssets": sum(len(item.get("assets") or []) for item in selected_levels),
            "relatedVideos": sum(len(item.get("videos") or []) for item in selected_levels),
            "relatedUnityAssets": sum(len(item.get("unityAssets") or []) for item in selected_levels),
        }
        return {
            "generated": int(time.time()),
            "sourceDatabase": slash(self.db_path),
            "filters": {
                "level": sorted(self.level_filters),
                "limit": self.limit,
            },
            "totals": totals,
            "selectedTableRows": dict(sorted(self.table_counts.items())),
            "maps": maps,
            "levels": selected_levels,
            "unresolved": unresolved,
            "unresolvedRetainedCounts": {key: len(value) for key, value in unresolved.items()},
        }

    def write_outputs(self, payload: dict[str, Any], selected_levels: list[dict[str, Any]]) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        dump_json(self.out_dir / "map_level_index.json", payload)
        levels_dir = self.out_dir / "levels"
        for level in selected_levels:
            dump_json(levels_dir / f"{safe_filename(level['levelId'])}.json", level)
        (self.out_dir / "summary.md").write_text(self.summary_markdown(payload, selected_levels), encoding="utf-8")

    def summary_markdown(self, payload: dict[str, Any], selected_levels: list[dict[str, Any]]) -> str:
        totals = payload["totals"]
        lines = [
            "# Map/Level Reconstruction Index",
            "",
            f"- Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Source database: `{payload['sourceDatabase']}`",
            f"- Output directory: `{slash(self.out_dir)}`",
            f"- Maps: {totals['maps']}",
            f"- Levels: {totals['levels']}",
            f"- Marks: {totals['marks']}",
            f"- Linked table rows: {totals['linkedTableRows']}",
            f"- Linked map-only table rows: {totals['linkedMapTableRows']}",
            f"- Unresolved marks: {totals['unresolvedMarks']}",
            f"- Unresolved table rows: {totals['unresolvedTableRows']}",
            "",
            "## Maps",
            "",
            "| Map | Levels | Marks | Assets | Videos | Unity assets |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for item in payload["maps"]:
            lines.append(
                f"| `{item['mapId']}` | {len(item.get('levels') or [])} | {item.get('markCount', 0)} | "
                f"{len(item.get('assets') or [])} | {len(item.get('videos') or [])} | {len(item.get('unityAssets') or [])} |"
            )
        lines.extend(["", "## Levels", "", "| Level | Map | Marks | Table rows | Assets | Videos |", "| --- | --- | ---: | ---: | ---: | ---: |"])
        for level in selected_levels:
            lines.append(
                f"| `{level['levelId']}` | `{level.get('mapId') or ''}` | {len(level.get('marks') or [])} | "
                f"{len(level.get('tableRows') or [])} | {len(level.get('assets') or [])} | {len(level.get('videos') or [])} |"
            )
        if payload["unresolved"]["marksWithoutLevel"] or payload["unresolved"]["tableRowsWithoutLevel"]:
            lines.extend(["", "## Unresolved", ""])
            lines.append(f"- Marks without level linkage: {totals['unresolvedMarks']}")
            lines.append(f"- Table rows without level linkage: {totals['unresolvedTableRows']}")
        lines.append("")
        return "\n".join(lines)

    def fetch_table_rows(self, sources: list[str] | tuple[str, ...]) -> list[sqlite3.Row]:
        placeholders = ",".join("?" for _ in sources)
        return self.db.execute(
            f"""
            SELECT id, kind, name, source, path, data
            FROM nodes
            WHERE kind = 'table_row' AND source IN ({placeholders})
            ORDER BY source, name
            """,
            tuple(sources),
        ).fetchall()

    def table_row_record(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        data = parse_json_text(row["data"], None)
        record = {
            "nodeId": row["id"],
            "table": row["source"],
            "key": row["name"],
            "label": extract_label(data),
            "pos": extract_pos(data),
        }
        if data not in (None, {}, []):
            record["data"] = compact_value(data)
        return {key: value for key, value in record.items() if value not in (None, [], {})}

    def extract_row_ids(
        self,
        record: dict[str, Any],
        data: Any,
        known_levels: set[str],
        known_maps: set[str | None],
    ) -> tuple[set[str], set[str]]:
        texts = [str(record.get("key") or ""), str(record.get("nodeId") or "")]
        texts.extend(value_texts(data))
        haystack = "\n".join(texts).lower()
        level_ids: set[str] = {level_id for level_id in known_levels if level_id.lower() in haystack}
        map_ids: set[str] = {map_id for map_id in known_maps if map_id and map_id.lower() in haystack}
        if isinstance(data, dict):
            direct_level = data.get("levelId")
            if direct_level:
                level_ids.add(str(direct_level))
                map_id = derive_map_id(str(direct_level))
                if map_id:
                    map_ids.add(map_id)
            direct_map = data.get("mapId")
            if direct_map:
                map_ids.add(str(direct_map))
        level_ids.update(match.group(0) for match in LEVEL_TOKEN_RE.finditer(haystack))
        for match in MAP_TOKEN_RE.finditer(haystack):
            candidate = match.group(0)
            if candidate in known_maps:
                map_ids.add(candidate)
        return level_ids, {item for item in map_ids if item}

    def is_unresolved_table_candidate(
        self,
        record: dict[str, Any],
        data: Any,
        level_ids: set[str],
        map_ids: set[str],
    ) -> bool:
        table = record.get("table")
        if table in MAP_TABLES:
            return True
        if level_ids or map_ids:
            return True
        key = str(record.get("key") or "")
        if LEVEL_TOKEN_RE.search(key):
            return True
        if isinstance(data, dict) and ("levelId" in data or "mapId" in data):
            return True
        return False

    def add_unresolved(self, bucket: str, record: dict[str, Any]) -> None:
        if not self.include_unresolved_record(record):
            return
        record_key = str(record.get("nodeId") or json.dumps(record, sort_keys=True, ensure_ascii=False))
        if record_key in self.unresolved_seen[bucket]:
            return
        self.unresolved_seen[bucket].add(record_key)
        self.unresolved_counts[bucket] += 1
        if self.limit and len(self.unresolved[bucket]) >= self.limit:
            return
        self.unresolved[bucket].append(record)

    def include_unresolved_record(self, record: dict[str, Any]) -> bool:
        if not self.level_filters:
            return True
        values = {
            str(record.get("levelId") or "").lower(),
            str(record.get("mapId") or "").lower(),
            str(record.get("key") or "").lower(),
        }
        values.update(str(item).lower() for item in record.get("candidateLevelIds") or [])
        values.update(str(item).lower() for item in record.get("candidateMapIds") or [])
        return bool(values & self.level_filters)

    def include_level(self, level: dict[str, Any]) -> bool:
        if not self.level_filters:
            return True
        level_id = str(level.get("levelId") or "").lower()
        map_id = str(level.get("mapId") or "").lower()
        return level_id in self.level_filters or map_id in self.level_filters

    def include_map(self, map_id: str) -> bool:
        if not self.level_filters:
            return True
        return map_id.lower() in self.level_filters

    def aliases_for_node(self, node_id: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """
            SELECT alias, kind, source
            FROM aliases
            WHERE node_id = ?
            ORDER BY kind, alias
            LIMIT ?
            """,
            (node_id, limit),
        ).fetchall()
        return [
            {key: value for key, value in {"alias": row["alias"], "kind": row["kind"], "source": row["source"]}.items() if value}
            for row in rows
        ]

    def level_terms(self, level: dict[str, Any]) -> list[str]:
        terms = [level["levelId"]]
        if level.get("mapId"):
            terms.append(level["mapId"])
        for mark in level.get("marks") or []:
            value = mark.get("markInfoId")
            if value:
                terms.append(str(value))
        seen: set[str] = set()
        out: list[str] = []
        for term in terms:
            term = str(term).strip()
            if len(term) < 4:
                continue
            lowered = term.lower()
            if lowered not in seen:
                seen.add(lowered)
                out.append(term)
        return out[:12]

    def level_node_ids(self, level: dict[str, Any]) -> list[str]:
        node_ids = []
        if level.get("node"):
            node_ids.append(level["node"]["nodeId"])
        for mark in level.get("marks") or []:
            if mark.get("nodeId"):
                node_ids.append(mark["nodeId"])
            table_row = mark.get("tableRow")
            if table_row and table_row.get("nodeId"):
                node_ids.append(table_row["nodeId"])
        for row in level.get("tableRows") or []:
            if row.get("nodeId"):
                node_ids.append(row["nodeId"])
        seen: set[str] = set()
        out = []
        for node_id in node_ids:
            if node_id not in seen:
                seen.add(node_id)
                out.append(node_id)
        return out[:100]

    def alias_related_nodes(self, terms: list[str], limit: int) -> list[dict[str, Any]]:
        if not terms or limit <= 0:
            return []
        related: list[dict[str, Any]] = []
        seen: set[str] = set()
        for term in terms:
            if len(related) >= limit:
                break
            rows = self.db.execute(
                """
                SELECT
                    a.alias AS alias,
                    a.kind AS aliasKind,
                    a.source AS aliasSource,
                    n.id AS nodeId,
                    n.kind AS nodeKind,
                    n.name AS nodeName,
                    n.source AS nodeSource,
                    n.path AS nodePath,
                    n.data AS nodeData
                FROM aliases a
                JOIN nodes n ON n.id = a.node_id
                WHERE lower(a.alias) LIKE ?
                    AND n.kind IN ('asset', 'video', 'unity_asset')
                LIMIT ?
                """,
                (f"%{term}%", max(limit - len(related), 1)),
            ).fetchall()
            for row in rows:
                key = row["nodeId"]
                if key in seen:
                    continue
                seen.add(key)
                related.append(self.related_record(row, relation="alias", matched_term=term))
                if len(related) >= limit:
                    break
        return related

    def direct_related_nodes(self, node_ids: list[str], limit: int) -> list[dict[str, Any]]:
        if not node_ids or limit <= 0:
            return []
        related: list[dict[str, Any]] = []
        seen: set[str] = set()
        for node_id in node_ids:
            if len(related) >= limit:
                break
            for sql, direction in (
                (
                    """
                    SELECT
                        e.kind AS edgeKind,
                        e.source AS edgeSource,
                        e.evidence AS edgeEvidence,
                        n.id AS nodeId,
                        n.kind AS nodeKind,
                        n.name AS nodeName,
                        n.source AS nodeSource,
                        n.path AS nodePath,
                        n.data AS nodeData
                    FROM edges e
                    JOIN nodes n ON n.id = e.dst
                    WHERE e.src = ? AND n.kind IN ('asset', 'video', 'unity_asset')
                    LIMIT ?
                    """,
                    "out",
                ),
                (
                    """
                    SELECT
                        e.kind AS edgeKind,
                        e.source AS edgeSource,
                        e.evidence AS edgeEvidence,
                        n.id AS nodeId,
                        n.kind AS nodeKind,
                        n.name AS nodeName,
                        n.source AS nodeSource,
                        n.path AS nodePath,
                        n.data AS nodeData
                    FROM edges e
                    JOIN nodes n ON n.id = e.src
                    WHERE e.dst = ? AND n.kind IN ('asset', 'video', 'unity_asset')
                    LIMIT ?
                    """,
                    "in",
                ),
            ):
                rows = self.db.execute(sql, (node_id, max(limit - len(related), 1))).fetchall()
                for row in rows:
                    key = row["nodeId"]
                    if key in seen:
                        continue
                    seen.add(key)
                    record = self.related_record(row, relation=f"edge:{direction}")
                    record["edge"] = {
                        "kind": row["edgeKind"],
                        "source": row["edgeSource"],
                        "evidence": row["edgeEvidence"],
                    }
                    related.append(record)
                    if len(related) >= limit:
                        break
                if len(related) >= limit:
                    break
        return related

    def related_record(
        self,
        row: sqlite3.Row,
        *,
        relation: str,
        matched_term: str | None = None,
    ) -> dict[str, Any]:
        data = parse_json_text(row["nodeData"], None)
        record = {
            "nodeId": row["nodeId"],
            "kind": row["nodeKind"],
            "name": row["nodeName"],
            "path": row["nodePath"],
            "source": row["nodeSource"],
            "relation": relation,
            "matchedTerm": matched_term,
            "label": extract_label(data),
        }
        if "alias" in row.keys():
            record["alias"] = row["alias"]
            record["aliasKind"] = row["aliasKind"]
            record["aliasSource"] = row["aliasSource"]
        return {key: value for key, value in record.items() if value not in (None, "", [], {})}

    def assign_related(self, target: dict[str, Any], related: list[dict[str, Any]]) -> None:
        for record in related:
            node_kind = record.get("kind")
            if node_kind == "video":
                bucket = "videos"
            elif node_kind == "unity_asset":
                bucket = "unityAssets"
            else:
                bucket = "assets"
            if self.limit and len(target[bucket]) >= self.limit:
                continue
            add_unique_record(target[bucket], record)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build map/level reconstruction indexes from endfield_source_graph.sqlite."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"source graph database (default: {DEFAULT_DB})")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help=f"output directory (default: {DEFAULT_OUT_DIR})")
    parser.add_argument(
        "--level",
        action="append",
        default=[],
        help="level id or map id to include; can be passed more than once",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="maximum related assets/videos and unresolved examples to keep per bucket (0 disables media lookup)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    indexer = MapLevelIndexer(
        db_path=args.db,
        out_dir=args.out_dir,
        level_filters=args.level,
        limit=args.limit,
    )
    payload = indexer.build()
    totals = payload["totals"]
    print(
        "Wrote map/level indexes to "
        f"{args.out_dir} ({totals['maps']} maps, {totals['levels']} levels, {totals['marks']} marks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
