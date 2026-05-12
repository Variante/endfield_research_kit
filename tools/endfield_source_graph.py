#!/usr/bin/env python3
"""Build and query a local Endfield source graph database.

The graph is intentionally evidence-first. It connects recovered WebUI story
data, source-link evidence, exported assets, AnimeStudio asset maps, material
texture references, character recovery manifests, selected structured tables,
and a few derived follow-up indexes into one SQLite database.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT / "export_full"
WEBUI_DATA = ROOT / "webui" / "data"
UNITY_CHARACTER_ROOT = (
    ROOT
    / "unity_endfield_graph_shader_lab"
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
)
GRAPH_DIR = ROOT / "reports" / "source_graph"
DEFAULT_DB = GRAPH_DIR / "endfield_source_graph.sqlite"
DEFAULT_SUMMARY_JSON = GRAPH_DIR / "summary.json"
DEFAULT_SUMMARY_MD = GRAPH_DIR / "summary.md"

ASSET_MAPS = {
    "StreamingAssets": (
        EXPORT_ROOT
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "maps"
        / "endfield_streamingassets_assets.json"
    ),
    "Persistent": (
        EXPORT_ROOT
        / "recovered"
        / "AnimeStudio-cli"
        / "Persistent"
        / "maps"
        / "endfield_persistent_assets.json"
    ),
}

STORY_KEY_RE = re.compile(
    r"\b(?:dlg|radio|sns|cutscene|remotecomm|black|timeline|envtalk|responsive|prts|reading)_[A-Za-z0-9_]{2,160}"
)
ASSET_ACTOR_RE = re.compile(r"(?:^|[/\\])(?:S|T|M|A|AC)_actor_([A-Za-z0-9]+)", re.IGNORECASE)
LINE_AUDIO_RE = re.compile(r"\bau_[A-Za-z0-9_]{2,160}\b")

SELECTED_STRUCTURED_TABLES = (
    "AudioDialog.json",
    "AudioSequenceDialog.json",
    "CharacterTable.json",
    "DialogSummaryMapTable.json",
    "DialogSummaryTable.json",
    "InteractiveMissionDataTable.json",
    "LevelDescTable.json",
    "MapIdTable.json",
    "MapMarkInsTable.json",
    "MissionExtraInfoTable.json",
    "SceneAreaTable.json",
    "SpecialLevelToMapTable.json",
)


def slash(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compact_text(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def compact_payload(value: Any, *, depth: int = 2, list_limit: int = 12) -> Any:
    """Keep node payloads useful without ballooning the graph."""
    if depth <= 0:
        if isinstance(value, dict):
            return f"dict[{len(value)}]"
        if isinstance(value, list):
            return f"list[{len(value)}]"
        return value
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= list_limit:
                out["..."] = f"{len(value) - list_limit} more"
                break
            out[str(key)] = compact_payload(item, depth=depth - 1, list_limit=list_limit)
        return out
    if isinstance(value, list):
        out = [compact_payload(item, depth=depth - 1, list_limit=list_limit) for item in value[:list_limit]]
        if len(value) > list_limit:
            out.append(f"... {len(value) - list_limit} more")
        return out
    if isinstance(value, str):
        return compact_text(value, 500)
    return value


def safe_key(value: Any) -> str:
    return str(value if value is not None else "").strip()


def normalize_abs_path(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    try:
        return slash(path)
    except (OSError, ValueError):
        return path_text.replace("\\", "/")


def iter_asset_entries(path: Path) -> Iterable[dict[str, Any]]:
    """Stream entries from AnimeStudio's large AssetMap JSON."""
    inside_entries = False
    buffer: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not inside_entries:
                if stripped == '"AssetEntries": [':
                    inside_entries = True
                continue

            if stripped == "]":
                break

            if not buffer:
                if stripped.startswith("{"):
                    buffer.append(line)
                continue

            buffer.append(line)
            if stripped.startswith("}") or stripped.startswith("},"):
                text = "".join(buffer).rstrip().rstrip(",")
                buffer = []
                try:
                    yield json.loads(text)
                except json.JSONDecodeError:
                    continue


class SourceGraphBuilder:
    def __init__(
        self,
        *,
        db_path: Path,
        root: Path = ROOT,
        export_root: Path = EXPORT_ROOT,
        language: str = "CN",
        include_asset_maps: bool = True,
        include_reference_rows: bool = True,
        include_all_material_json: bool = False,
        emit_followups: bool = True,
    ) -> None:
        self.root = root
        self.export_root = export_root
        self.language = language
        self.db_path = db_path
        self.include_asset_maps = include_asset_maps
        self.include_reference_rows = include_reference_rows
        self.include_all_material_json = include_all_material_json
        self.emit_followups = emit_followups
        self.conn: sqlite3.Connection | None = None
        self.node_counts: Counter[str] = Counter()
        self.edge_counts: Counter[str] = Counter()
        self.file_counts: Counter[str] = Counter()
        self.ingest_counts: Counter[str] = Counter()
        self.asset_by_stem: dict[str, list[str]] = defaultdict(list)
        self.asset_by_name: dict[str, list[str]] = defaultdict(list)
        self.alias_count = 0

    @property
    def db(self) -> sqlite3.Connection:
        if self.conn is None:
            raise RuntimeError("database is not open")
        return self.conn

    def open(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists():
            self.db_path.unlink()
        self.conn = sqlite3.connect(self.db_path)
        self.db.execute("PRAGMA journal_mode=OFF")
        self.db.execute("PRAGMA synchronous=OFF")
        self.db.execute("PRAGMA temp_store=MEMORY")
        self.db.execute("PRAGMA cache_size=-200000")
        self.create_schema()

    def close(self) -> None:
        if self.conn is not None:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    def create_schema(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                name TEXT,
                source TEXT,
                path TEXT,
                data TEXT
            );
            CREATE TABLE edges (
                id INTEGER PRIMARY KEY,
                src TEXT NOT NULL,
                dst TEXT NOT NULL,
                kind TEXT NOT NULL,
                source TEXT,
                evidence TEXT,
                data TEXT,
                UNIQUE(src, dst, kind, source, evidence)
            );
            CREATE TABLE aliases (
                alias TEXT NOT NULL,
                node_id TEXT NOT NULL,
                kind TEXT,
                source TEXT,
                UNIQUE(alias, node_id, kind, source)
            );
            CREATE TABLE files (
                path TEXT PRIMARY KEY,
                kind TEXT,
                source TEXT,
                size INTEGER,
                data TEXT
            );
            CREATE TABLE meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE INDEX idx_nodes_kind ON nodes(kind);
            CREATE INDEX idx_nodes_name ON nodes(name);
            CREATE INDEX idx_edges_src ON edges(src);
            CREATE INDEX idx_edges_dst ON edges(dst);
            CREATE INDEX idx_edges_kind ON edges(kind);
            CREATE INDEX idx_aliases_alias ON aliases(alias);
            CREATE INDEX idx_files_kind ON files(kind);
            """
        )

    def node_id(self, kind: str, key: Any) -> str:
        return f"{kind}:{safe_key(key)}"

    def add_node(
        self,
        kind: str,
        key: Any,
        *,
        name: Any = None,
        source: Any = None,
        path: Any = None,
        data: Any = None,
    ) -> str:
        key_text = safe_key(key)
        node_id = self.node_id(kind, key_text)
        payload = dump_json(data) if data is not None else None
        cur = self.db.execute(
            """
            INSERT OR IGNORE INTO nodes(id, kind, name, source, path, data)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                kind,
                compact_text(name or key_text, 300),
                safe_key(source) or None,
                safe_key(path) or None,
                payload,
            ),
        )
        if cur.rowcount:
            self.node_counts[kind] += 1
        return node_id

    def add_alias(self, alias: Any, node_id: str, *, kind: str = "", source: str = "") -> None:
        alias_text = safe_key(alias)
        if not alias_text:
            return
        cur = self.db.execute(
            "INSERT OR IGNORE INTO aliases(alias, node_id, kind, source) VALUES (?, ?, ?, ?)",
            (alias_text, node_id, kind or None, source or None),
        )
        if cur.rowcount:
            self.alias_count += 1

    def add_edge(
        self,
        src: str,
        dst: str,
        kind: str,
        *,
        source: str = "",
        evidence: str = "",
        data: Any = None,
    ) -> None:
        if not src or not dst:
            return
        payload = dump_json(data) if data is not None else None
        cur = self.db.execute(
            """
            INSERT OR IGNORE INTO edges(src, dst, kind, source, evidence, data)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (src, dst, kind, source or None, evidence or None, payload),
        )
        if cur.rowcount:
            self.edge_counts[kind] += 1

    def add_file(
        self,
        path: Any,
        *,
        kind: str = "",
        source: str = "",
        size: int | None = None,
        data: Any = None,
    ) -> str:
        path_text = safe_key(path).replace("\\", "/")
        node_id = self.add_node("file", path_text, name=Path(path_text).name, source=source, path=path_text, data=data)
        self.db.execute(
            """
            INSERT OR IGNORE INTO files(path, kind, source, size, data)
            VALUES (?, ?, ?, ?, ?)
            """,
            (path_text, kind or None, source or None, size, dump_json(data) if data is not None else None),
        )
        if kind:
            self.file_counts[kind] += 1
        return node_id

    def commit_step(self, label: str) -> None:
        self.db.commit()
        self.ingest_counts[f"{label}.nodes"] = sum(self.node_counts.values())
        self.ingest_counts[f"{label}.edges"] = sum(self.edge_counts.values())

    def build(self) -> dict[str, Any]:
        started = time.time()
        self.open()
        try:
            self.db.execute("INSERT INTO meta(key, value) VALUES (?, ?)", ("generated", str(int(started))))
            self.db.execute("INSERT INTO meta(key, value) VALUES (?, ?)", ("language", self.language))
            self.ingest_assets()
            self.commit_step("assets")
            self.ingest_videos()
            self.commit_step("videos")
            self.ingest_webui_story()
            self.commit_step("story")
            self.ingest_story_source_links()
            self.commit_step("storySourceLinks")
            self.ingest_materials()
            self.commit_step("materials")
            self.ingest_character_manifests()
            self.commit_step("characterManifests")
            self.ingest_selected_structured_tables()
            self.commit_step("structuredTables")
            if self.include_reference_rows:
                self.ingest_reference_tables()
                self.commit_step("reference")
            if self.include_asset_maps:
                self.ingest_asset_maps()
                self.commit_step("assetMaps")
            self.finalize_indices()
            summary = self.summary(started)
            write_summary(summary)
            if self.emit_followups:
                emit_followup_indexes(self.db_path, summary)
            return summary
        finally:
            self.close()

    def finalize_indices(self) -> None:
        self.db.execute("ANALYZE")

    def ingest_assets(self) -> None:
        path = WEBUI_DATA / "assets" / "index.json"
        payload = read_json(path, {})
        root_node = self.add_node("dataset", "webui_assets", name="WebUI asset index", path=slash(path))
        for entry in payload.get("entries") or []:
            rel = safe_key(entry.get("r"))
            if not rel:
                continue
            kind = safe_key(entry.get("k")) or "asset"
            size = entry.get("s")
            node = self.add_node(
                "asset",
                rel,
                name=Path(rel).name,
                source=rel.split("/", 1)[0],
                path=rel,
                data={"type": kind, "size": size, "preview": entry.get("p")},
            )
            self.add_edge(root_node, node, "indexes_asset", source="webui/assets")
            self.add_file(rel, kind=kind, source=rel.split("/", 1)[0], size=size)
            stem = Path(rel).stem.lower()
            self.asset_by_stem[stem].append(rel)
            self.asset_by_name[Path(rel).name.lower()].append(rel)
            self.add_alias(stem, node, kind="asset_stem", source="webui/assets")
            self.add_alias(Path(rel).name.lower(), node, kind="asset_name", source="webui/assets")
            if entry.get("p"):
                preview = self.add_node("asset", entry["p"], name=Path(entry["p"]).name, path=entry["p"])
                self.add_edge(node, preview, "previewed_by", source="webui/assets")

    def ingest_videos(self) -> None:
        path = WEBUI_DATA / "assets" / "videos.json"
        payload = read_json(path, {})
        root_node = self.add_node("dataset", "webui_videos", name="WebUI video index", path=slash(path))
        for entry in payload.get("entries") or []:
            rel = safe_key(entry.get("r"))
            if not rel:
                continue
            node = self.add_node(
                "video",
                rel,
                name=Path(rel).name,
                source=rel.split("/", 1)[0],
                path=rel,
                data={"type": entry.get("k"), "size": entry.get("s")},
            )
            self.add_edge(root_node, node, "indexes_video", source="webui/videos")
            self.add_file(rel, kind="video", source=rel.split("/", 1)[0], size=entry.get("s"))
            self.add_alias(Path(rel).stem.lower(), node, kind="video_stem", source="webui/videos")

    def ingest_webui_story(self) -> None:
        lang_root = WEBUI_DATA / "lang" / self.language
        index_path = lang_root / "index.json"
        index = read_json(index_path, {})
        lang_node = self.add_node("language", self.language, name=self.language, path=slash(index_path))

        for actor_id, names in (index.get("actorNames") or {}).items():
            name = names[0] if isinstance(names, list) and names else actor_id
            actor_node = self.add_node("actor", actor_id, name=name, source="webui/story")
            self.add_edge(lang_node, actor_node, "has_actor_name", source="webui/story")
            for actor_name in names if isinstance(names, list) else []:
                self.add_alias(actor_name, actor_node, kind="actor_name", source=self.language)

        for mission_id, names in (index.get("missionNames") or {}).items():
            name = names[0] if isinstance(names, list) and names else mission_id
            mission_node = self.add_node("mission", mission_id, name=name, source="webui/story")
            self.add_edge(lang_node, mission_node, "has_mission_name", source="webui/story")

        for entry in index.get("entries") or []:
            story_key = safe_key(entry.get("k"))
            if not story_key:
                continue
            story_node = self.add_story_node(story_key, entry)
            self.add_edge(lang_node, story_node, "has_story_entry", source="webui/story")
            mission = safe_key(entry.get("m"))
            if mission:
                mission_node = self.add_node("mission", mission, source="webui/story")
                self.add_edge(mission_node, story_node, "has_story", source="webui/story")
            for actor_id in entry.get("c") or []:
                actor_node = self.add_node("actor", actor_id, source="webui/story")
                self.add_edge(story_node, actor_node, "mentions_actor", source="webui/story")

        conv_root = lang_root / "conv"
        for conv_path in sorted(conv_root.glob("*.json")):
            conv = read_json(conv_path, {})
            story_key = safe_key(conv.get("key") or conv_path.stem)
            story_node = self.add_story_node(story_key, conv, path=slash(conv_path))
            self.add_file(slash(conv_path), kind="story_conv", source=self.language)
            self.add_lines_and_options(conv, story_node)
            self.add_narrative_videos(conv, story_node)
            self.add_scene_graph_edges(conv, story_node)

    def add_story_node(self, story_key: str, data: dict[str, Any], *, path: str = "") -> str:
        summary = data.get("summary")
        if isinstance(summary, dict):
            preview = summary.get("text")
        elif isinstance(summary, list) and summary:
            first_summary = summary[0]
            preview = first_summary.get("text") if isinstance(first_summary, dict) else first_summary
        else:
            preview = None
        node = self.add_node(
            "story",
            story_key,
            name=story_key,
            source="webui/story",
            path=path,
            data={
                "kind": data.get("kind") or data.get("d"),
                "mission": data.get("mission") or data.get("m"),
                "scene": data.get("scene") or data.get("s"),
                "tags": data.get("tags"),
                "lineCount": len(data.get("lines") or []) if isinstance(data.get("lines"), list) else data.get("n"),
                "preview": data.get("p") or preview,
            },
        )
        self.add_alias(story_key, node, kind="story_key", source="webui/story")
        return node

    def add_lines_and_options(self, conv: dict[str, Any], story_node: str) -> None:
        for index, line in enumerate(conv.get("lines") or []):
            line_id = safe_key(line.get("id") or f"{conv.get('key')}#{index}")
            line_node = self.add_node(
                "line",
                line_id,
                name=line_id,
                source="webui/story",
                data={
                    "actor": line.get("actor"),
                    "actorId": line.get("aid"),
                    "audio": line.get("audio"),
                    "text": compact_text(line.get("text"), 500),
                    "timestamp": line.get("ts"),
                    "duration": line.get("dur"),
                },
            )
            self.add_edge(story_node, line_node, "has_line", source="webui/story", evidence=str(index))
            actor_id = safe_key(line.get("aid"))
            if actor_id:
                actor_node = self.add_node("actor", actor_id, name=line.get("actor"), source="webui/story")
                self.add_edge(line_node, actor_node, "spoken_by", source="webui/story")
            audio_id = safe_key(line.get("audio"))
            if audio_id:
                audio_node = self.add_node("audio", audio_id, name=audio_id, source="dialog_line")
                self.add_edge(line_node, audio_node, "uses_audio", source="webui/story")

        for group in conv.get("optionGroups") or []:
            branch_risk = group.get("optionBranchRisk") or {}
            group_key = f"{conv.get('key')}#optionGroup:{group.get('g', len(group))}"
            group_node = self.add_node(
                "option_group",
                group_key,
                name=group_key,
                source="webui/story",
                data={
                    "after": group.get("after"),
                    "risk": branch_risk.get("code"),
                    "reason": branch_risk.get("reason"),
                    "riskDetail": branch_risk.get("detail"),
                    "riskSource": branch_risk.get("source"),
                    "candidateLineIds": branch_risk.get("candidateLineIds"),
                    "commonContinuationLineId": branch_risk.get("commonContinuationLineId"),
                    "branchLineIdsByOption": branch_risk.get("branchLineIdsByOption"),
                    "skippedLineIdsByOption": branch_risk.get("skippedLineIdsByOption"),
                    "continuationOptionIds": branch_risk.get("continuationOptionIds"),
                },
            )
            self.add_edge(story_node, group_node, "has_option_group", source="webui/story")
            if group.get("after"):
                after_node = self.add_node("line", group["after"], source="webui/story")
                self.add_edge(group_node, after_node, "anchored_after_line", source="webui/story")
            options = group.get("options") or []
            branch_option_ids = [safe_key(value) for value in branch_risk.get("optionIds") or [] if safe_key(value)]
            if not branch_option_ids:
                branch_option_ids = [safe_key(option.get("id")) for option in options if safe_key(option.get("id"))]
            candidate_line_ids = [safe_key(value) for value in branch_risk.get("candidateLineIds") or [] if safe_key(value)]
            common_line_id = safe_key(branch_risk.get("commonContinuationLineId"))
            raw_branch_lines_by_option = branch_risk.get("branchLineIdsByOption") or {}
            branch_lines_by_option = {
                safe_key(option_id): [safe_key(line_id) for line_id in line_ids or [] if safe_key(line_id)]
                for option_id, line_ids in raw_branch_lines_by_option.items()
                if safe_key(option_id) and isinstance(line_ids, list)
            } if isinstance(raw_branch_lines_by_option, dict) else {}
            raw_skipped_lines_by_option = branch_risk.get("skippedLineIdsByOption") or {}
            skipped_lines_by_option = {
                safe_key(option_id): [safe_key(line_id) for line_id in line_ids or [] if safe_key(line_id)]
                for option_id, line_ids in raw_skipped_lines_by_option.items()
                if safe_key(option_id) and isinstance(line_ids, list)
            } if isinstance(raw_skipped_lines_by_option, dict) else {}
            continuation_option_ids = [
                safe_key(value)
                for value in branch_risk.get("continuationOptionIds") or []
                if safe_key(value)
            ]
            option_branch_hints: dict[str, dict[str, Any]] = {}
            if branch_risk and branch_option_ids:
                for index, option_id in enumerate(branch_option_ids):
                    hint: dict[str, Any] = {
                        "code": branch_risk.get("code"),
                        "reason": branch_risk.get("reason"),
                        "source": branch_risk.get("source"),
                    }
                    if option_id in branch_lines_by_option:
                        hint["branchLineIds"] = branch_lines_by_option[option_id]
                    if option_id in skipped_lines_by_option:
                        hint["skippedLineIds"] = skipped_lines_by_option[option_id]
                    if continuation_option_ids:
                        hint["continuationOptionIds"] = continuation_option_ids
                    if index < len(candidate_line_ids):
                        hint["candidateLineId"] = candidate_line_ids[index]
                    if common_line_id:
                        hint["commonContinuationLineId"] = common_line_id
                    option_branch_hints[option_id] = hint

            for option in options:
                option_id = safe_key(option.get("id"))
                if not option_id:
                    continue
                option_node = self.add_node(
                    "option",
                    option_id,
                    name=compact_text(option.get("text") or option_id, 160),
                    source="webui/story",
                    data={"text": option.get("text"), "icon": option.get("icon"), "index": option.get("i")},
                )
                self.add_edge(group_node, option_node, "has_option", source="webui/story")
                hint = option_branch_hints.get(option_id)
                if not hint:
                    continue
                evidence = ":".join(str(value) for value in (hint.get("code"), hint.get("reason"), hint.get("source")) if value)
                edge_source = "timeline_route_branch" if hint.get("code") == "timelineRouteBranches" else "option_branch_risk"
                branch_line_ids = [
                    safe_key(line_id)
                    for line_id in hint.get("branchLineIds") or []
                    if safe_key(line_id)
                ]
                first_line_id = branch_line_ids[0] if branch_line_ids else hint.get("candidateLineId") or hint.get("commonContinuationLineId")
                if first_line_id:
                    first_line_node = self.add_node("line", first_line_id, source="webui/optionBranchRisk")
                    self.add_edge(option_node, first_line_node, "option_first_line", source=edge_source, evidence=evidence, data=hint)
                    if not branch_line_ids:
                        self.add_edge(option_node, first_line_node, "option_path_line", source=edge_source, evidence=evidence, data=hint)
                for line_id in branch_line_ids:
                    branch_line_node = self.add_node("line", line_id, source="webui/optionBranchRisk")
                    self.add_edge(option_node, branch_line_node, "option_path_line", source=edge_source, evidence=evidence, data=hint)
                if hint.get("commonContinuationLineId") and hint.get("commonContinuationLineId") != first_line_id:
                    common_line_node = self.add_node("line", hint["commonContinuationLineId"], source="webui/optionBranchRisk")
                    self.add_edge(option_node, common_line_node, "option_path_line", source=edge_source, evidence=evidence, data=hint)
                    self.add_edge(option_node, common_line_node, "option_merge_line", source=edge_source, evidence=evidence, data=hint)
                self.add_edge(option_node, story_node, "option_path_story", source=edge_source, evidence=evidence, data=hint)
                self.add_edge(option_node, story_node, "option_enters_story", source=edge_source, evidence=evidence, data=hint)

    def add_narrative_videos(self, conv: dict[str, Any], story_node: str) -> None:
        for video in conv.get("narrativeVideos") or []:
            rel = safe_key(video.get("rel"))
            if not rel:
                continue
            video_node = self.add_node(
                "video",
                rel,
                name=video.get("name") or Path(rel).name,
                source=video.get("source"),
                path=rel,
                data={"format": video.get("format"), "kind": video.get("kind"), "size": video.get("size")},
            )
            self.add_edge(story_node, video_node, "has_narrative_video", source="webui/story")

    def add_scene_graph_edges(self, conv: dict[str, Any], story_node: str) -> None:
        for fragment in conv.get("graphFragments") or []:
            source_key = safe_key(fragment.get("sourceKey"))
            if source_key:
                source_node = self.add_node("story_graph_source", source_key, source="AnimeStudio/TextAsset")
                self.add_edge(source_node, story_node, "graph_fragment_targets_story", source="webui/story")
            if fragment.get("file"):
                file_node = self.add_file(fragment["file"], kind="text_asset_json", source="AnimeStudio/TextAsset")
                self.add_edge(story_node, file_node, "has_graph_source_file", source="webui/story")
            for option_group in fragment.get("optionGroups") or []:
                after = option_group.get("after")
                branches = option_group.get("branches") or {}
                merges = option_group.get("merge") or {}
                for option_id in option_group.get("optionIds") or []:
                    option_node = self.add_node("option", option_id, source="webui/story")
                    if after:
                        self.add_edge(option_node, self.add_node("line", after), "option_anchor_after", source="scene_graph")
                    for line_id in branches.get(option_id) or []:
                        self.add_edge(option_node, self.add_node("line", line_id), "option_branch_line", source="scene_graph")
                    if merges.get(option_id):
                        self.add_edge(option_node, self.add_node("line", merges[option_id]), "option_merge_line", source="scene_graph")

        for link in conv.get("sceneGraphLinks") or []:
            for option in link.get("options") or []:
                option_id = safe_key(option.get("optionId"))
                if not option_id:
                    continue
                option_node = self.add_node("option", option_id, source="webui/story")
                if option.get("firstLineId"):
                    self.add_edge(option_node, self.add_node("line", option["firstLineId"]), "option_first_line", source="scene_graph")
                if option.get("firstSceneKey"):
                    self.add_edge(option_node, self.add_node("story", option["firstSceneKey"]), "option_enters_story", source="scene_graph")
                for line_id in option.get("pathLineIds") or []:
                    self.add_edge(option_node, self.add_node("line", line_id), "option_path_line", source="scene_graph")
                for scene_key in option.get("sceneKeys") or []:
                    self.add_edge(option_node, self.add_node("story", scene_key), "option_path_story", source="scene_graph")

    def ingest_story_source_links(self) -> None:
        path = EXPORT_ROOT / "recovered" / "story_source_links.json"
        payload = read_json(path, {})
        dataset = self.add_node("dataset", "story_source_links", path=slash(path), data=payload.get("summary"))
        for story_key, rows in (payload.get("links") or {}).items():
            story_node = self.add_node("story", story_key, source="story_source_links")
            self.add_edge(dataset, story_node, "has_story_source_link", source="story_source_links")
            for row in rows:
                file_rel = safe_key(row.get("file"))
                if file_rel:
                    file_node = self.add_file(file_rel, kind="source_json", source=row.get("source"))
                    self.add_edge(file_node, story_node, "references_story", source=row.get("source") or "story_source_links", evidence=row.get("path") or "")
                mission = safe_key(row.get("mission"))
                if mission:
                    mission_node = self.add_node("mission", mission, source=row.get("source"))
                    self.add_edge(mission_node, story_node, "source_references_story", source=row.get("source") or "story_source_links")

    def ingest_materials(self) -> None:
        for source in ("StreamingAssets", "Persistent"):
            root = EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / source / "json_by_type" / "Material"
            if not root.is_dir():
                continue
            if self.include_all_material_json:
                material_paths = root.glob("*.json")
            else:
                material_paths = root.glob("M_actor*.json")
            for path in sorted(material_paths):
                payload = read_json(path, {})
                name = safe_key(payload.get("m_Name") or payload.get("Name") or path.stem)
                material_node = self.add_node(
                    "material",
                    f"{source}:{name}",
                    name=name,
                    source=source,
                    path=slash(path),
                    data={"shader": payload.get("m_Shader"), "json": slash(path)},
                )
                self.add_file(slash(path), kind="material_json", source=source)
                self.add_alias(name.lower(), material_node, kind="material_name", source=source)
                shader = payload.get("m_Shader") or {}
                if shader.get("m_PathID"):
                    shader_node = self.add_node("unity_pathid", shader["m_PathID"], name=f"pathid:{shader['m_PathID']}", source=source)
                    self.add_edge(material_node, shader_node, "uses_shader_pathid", source="material_json")
                tex_envs = ((payload.get("m_SavedProperties") or {}).get("m_TexEnvs") or {})
                for slot, tex_env in tex_envs.items():
                    texture = (tex_env or {}).get("m_Texture") or {}
                    if texture.get("IsNull") or not texture.get("m_PathID"):
                        continue
                    tex_node = self.add_node("unity_pathid", texture["m_PathID"], name=f"pathid:{texture['m_PathID']}", source=source)
                    self.add_edge(
                        material_node,
                        tex_node,
                        "uses_texture_pathid",
                        source="material_json",
                        evidence=slot,
                        data={"slot": slot, "fileId": texture.get("m_FileID")},
                    )

    def ingest_character_manifests(self) -> None:
        if not UNITY_CHARACTER_ROOT.exists():
            return
        dataset = self.add_node("dataset", "unity_character_recovery_manifests", path=slash(UNITY_CHARACTER_ROOT))
        for path in sorted(UNITY_CHARACTER_ROOT.rglob("*_recovery_manifest.json")):
            payload = read_json(path, {})
            actor = safe_key(payload.get("model") or path.stem.removesuffix("_recovery_manifest"))
            actor_node = self.add_node("actor", actor, name=actor, source="unity_character_lab", path=slash(path))
            manifest_node = self.add_node("character_manifest", actor, name=actor, source="unity_character_lab", path=slash(path))
            self.add_edge(dataset, manifest_node, "has_character_manifest", source="unity_character_lab")
            self.add_edge(actor_node, manifest_node, "has_recovery_manifest", source="unity_character_lab")
            self.add_file(slash(path), kind="character_manifest", source="unity_character_lab")

            for mesh in payload.get("meshes") or []:
                mesh_name = safe_key(mesh.get("name") or mesh.get("path"))
                if not mesh_name:
                    continue
                mesh_node = self.add_node(
                    "mesh",
                    mesh_name,
                    name=mesh_name,
                    source="unity_character_lab",
                    data={
                        "path": mesh.get("path"),
                        "container": mesh.get("mesh_container"),
                        "pathId": mesh.get("mesh_path_id"),
                        "materials": mesh.get("material_names"),
                    },
                )
                self.add_edge(manifest_node, mesh_node, "has_mesh", source="unity_character_lab")
                for material_name in mesh.get("material_names") or []:
                    mat_node = self.add_node("material", material_name, name=material_name, source="unity_character_lab")
                    self.add_edge(mesh_node, mat_node, "uses_material", source="unity_character_lab")

            for material_key, material in (payload.get("materials") or {}).items():
                material_name = safe_key(material.get("name") or material_key)
                mat_node = self.add_node(
                    "material",
                    material_name,
                    name=material_name,
                    source="unity_character_lab",
                    data={
                        "shader": material.get("shader_name"),
                        "container": material.get("container"),
                        "pathId": material.get("path_id"),
                        "assetRoot": material.get("asset_root"),
                    },
                )
                self.add_edge(manifest_node, mat_node, "has_material", source="unity_character_lab")
                if material.get("shader_name"):
                    shader_node = self.add_node("shader", material["shader_name"], name=material["shader_name"])
                    self.add_edge(mat_node, shader_node, "uses_shader", source="unity_character_lab")
                for slot, texture in (material.get("textures") or {}).items():
                    texture_name = safe_key(texture.get("name") or texture.get("file"))
                    tex_node = self.add_node(
                        "texture",
                        texture_name,
                        name=texture_name,
                        source=texture.get("asset_root"),
                        path=normalize_abs_path(texture.get("file") or ""),
                        data={"slot": slot, "pathId": texture.get("path_id"), "container": texture.get("container")},
                    )
                    self.add_edge(mat_node, tex_node, "uses_texture", source="unity_character_lab", evidence=slot)
                    if texture.get("file"):
                        rel = normalize_abs_path(texture["file"])
                        file_node = self.add_file(rel, kind="image", source=texture.get("asset_root"))
                        self.add_edge(tex_node, file_node, "exported_file", source="unity_character_lab")

            for clip in payload.get("clips") or []:
                clip_name = safe_key(clip.get("name"))
                if not clip_name:
                    continue
                clip_node = self.add_node(
                    "animation_clip",
                    clip_name,
                    name=clip_name,
                    source=clip.get("sample_source"),
                    path=normalize_abs_path(clip.get("sample_json") or ""),
                    data={
                        "class": clip.get("clip_class"),
                        "category": clip.get("clip_category"),
                        "duration": clip.get("duration"),
                        "sampleRate": clip.get("sample_rate"),
                        "trackCount": clip.get("output_track_count"),
                        "bindingEvidence": clip.get("binding_evidence"),
                    },
                )
                self.add_edge(manifest_node, clip_node, "has_animation_clip", source="unity_character_lab")

    def ingest_selected_structured_tables(self) -> None:
        table_root = EXPORT_ROOT / "structured" / "StreamingAssets" / "Table"
        dataset = self.add_node("dataset", "structured_tables_selected", path=slash(table_root))
        for table_name in SELECTED_STRUCTURED_TABLES:
            path = table_root / table_name
            payload = read_json(path, None)
            if payload is None:
                continue
            table_key = Path(table_name).stem
            table_node = self.add_node("table", table_key, name=table_key, source="StreamingAssets/Table", path=slash(path))
            self.add_edge(dataset, table_node, "has_table", source="structured")
            self.add_file(slash(path), kind="structured_table", source="StreamingAssets/Table")
            if not isinstance(payload, dict):
                continue
            for row_key, row in payload.items():
                row_node = self.add_node(
                    "table_row",
                    f"{table_key}:{row_key}",
                    name=str(row_key),
                    source=table_key,
                    data=compact_payload(row, depth=2),
                )
                self.add_edge(table_node, row_node, "has_row", source="structured")
                self.add_structured_row_edges(table_key, row_key, row, row_node)

    def add_structured_row_edges(self, table: str, row_key: str, row: Any, row_node: str) -> None:
        if table == "AudioDialog" and isinstance(row, dict):
            path = safe_key(row.get("path"))
            audio_key = Path(path).stem if path else row_key
            audio_node = self.add_node(
                "audio",
                audio_key,
                name=audio_key,
                source="AudioDialog",
                path=path,
                data={
                    "id": row_key,
                    "speaker": row.get("speakerChannel"),
                    "duration": row.get("wavDuration"),
                    "path": path,
                    "voType": row.get("voType"),
                    "codec": row.get("codec"),
                },
            )
            self.add_edge(row_node, audio_node, "defines_audio", source="AudioDialog")
            if row.get("speakerChannel"):
                actor_node = self.add_node("actor", row["speakerChannel"], source="AudioDialog")
                self.add_edge(audio_node, actor_node, "speaker_channel", source="AudioDialog")
            if path:
                file_node = self.add_file(path, kind="wem_path", source="AudioDialog")
                self.add_edge(audio_node, file_node, "audio_path", source="AudioDialog")
        elif table == "CharacterTable" and isinstance(row, dict):
            char_id = safe_key(row.get("charId") or row_key)
            char_node = self.add_node(
                "character",
                char_id,
                name=row.get("engName") or char_id,
                source="CharacterTable",
                data={"rarity": row.get("rarity"), "weaponType": row.get("weaponType"), "department": row.get("department")},
            )
            self.add_edge(row_node, char_node, "defines_character", source="CharacterTable")
            actor_hint = char_id.replace("chr_", "")
            self.add_alias(actor_hint, char_node, kind="character_alias", source="CharacterTable")
            for voice in row.get("profileVoice") or []:
                vo_id = safe_key(voice.get("voId"))
                if not vo_id:
                    continue
                audio_node = self.add_node("audio", vo_id, name=vo_id, source="CharacterTable")
                self.add_edge(char_node, audio_node, "has_profile_voice", source="CharacterTable", evidence=str(voice.get("voiceIndex") or ""))
        elif table == "MapMarkInsTable" and isinstance(row, dict):
            level = safe_key(row.get("levelId"))
            mark = safe_key(row.get("markInsId") or row_key)
            mark_node = self.add_node(
                "map_mark",
                mark,
                name=mark,
                source="MapMarkInsTable",
                data={"levelId": level, "markInfoId": row.get("markInfoId"), "pos": row.get("pos")},
            )
            self.add_edge(row_node, mark_node, "defines_map_mark", source="MapMarkInsTable")
            if level:
                level_node = self.add_node("level", level, name=level, source="MapMarkInsTable")
                self.add_edge(level_node, mark_node, "has_map_mark", source="MapMarkInsTable")
        elif table == "AudioSequenceDialog" and isinstance(row, dict):
            for sequence_key, sequence in row.items():
                seq_node = self.add_node("audio_sequence", sequence_key, name=sequence_key, source="AudioSequenceDialog")
                self.add_edge(row_node, seq_node, "has_audio_sequence", source="AudioSequenceDialog")
                if isinstance(sequence, dict):
                    for speaker in sequence.get("involvedSpeakers") or []:
                        char_node = self.add_node("character", speaker, name=speaker, source="AudioSequenceDialog")
                        self.add_edge(seq_node, char_node, "involves_speaker", source="AudioSequenceDialog")
                    for audio_id in sequence.get("sequence") or []:
                        audio_node = self.add_node("audio", str(audio_id), name=str(audio_id), source="AudioSequenceDialog")
                        self.add_edge(seq_node, audio_node, "sequence_audio_id", source="AudioSequenceDialog")

    def ingest_reference_tables(self) -> None:
        ref_root = WEBUI_DATA / "lang" / self.language / "reference"
        index = read_json(ref_root / "index.json", {})
        dataset = self.add_node("dataset", f"reference_{self.language}", name=f"Reference {self.language}", path=slash(ref_root))
        for table in index.get("tables") or []:
            table_name = safe_key(table.get("table"))
            table_key = f"{table.get('source')}:{table_name.removesuffix('.json')}"
            table_node = self.add_node(
                "reference_table",
                table_key,
                name=table.get("label") or table_name,
                source=table.get("source"),
                path=(ref_root / table.get("file", "")).as_posix(),
                data={"rows": table.get("rows"), "texts": table.get("texts")},
            )
            self.add_edge(dataset, table_node, "has_reference_table", source="webui/reference")
            table_path = ref_root / safe_key(table.get("file"))
            payload = read_json(table_path, {})
            for row in payload.get("rows") or []:
                row_id = safe_key(row.get("id"))
                if not row_id:
                    continue
                row_node = self.add_node(
                    "reference_row",
                    f"{table_key}:{row_id}",
                    name=row_id,
                    source=table_key,
                    data={
                        "title": row.get("title"),
                        "bucket": row.get("bucket"),
                        "texts": compact_payload(row.get("texts") or [], depth=2, list_limit=6),
                    },
                )
                self.add_edge(table_node, row_node, "has_reference_row", source="webui/reference")
                for text in row.get("texts") or []:
                    i18n_id = safe_key(text.get("i18nId"))
                    if i18n_id:
                        text_node = self.add_node(
                            "i18n_text",
                            f"{self.language}:{i18n_id}",
                            name=compact_text(text.get("text"), 160),
                            source=self.language,
                            data={"field": text.get("field"), "text": text.get("text")},
                        )
                        self.add_edge(row_node, text_node, "has_i18n_text", source="webui/reference", evidence=text.get("field") or "")

    def ingest_asset_maps(self) -> None:
        dataset = self.add_node("dataset", "animestudio_asset_maps", name="AnimeStudio asset maps")
        batch = 0
        for source, path in ASSET_MAPS.items():
            if not path.exists():
                continue
            source_node = self.add_node("asset_map", source, name=f"{source} AssetMap", source=source, path=slash(path))
            self.add_edge(dataset, source_node, "has_asset_map", source="AnimeStudio/maps")
            for entry in iter_asset_entries(path):
                path_id = entry.get("PathID")
                name = safe_key(entry.get("Name")) or f"pathid_{path_id}"
                key = f"{source}:{path_id}" if path_id is not None else f"{source}:{name}:{entry.get('Offset')}"
                node = self.add_node(
                    "unity_asset",
                    key,
                    name=name,
                    source=source,
                    path=safe_key(entry.get("Container")),
                    data={
                        "type": entry.get("Type"),
                        "container": entry.get("Container"),
                        "source": normalize_abs_path(entry.get("Source") or ""),
                        "pathId": path_id,
                        "hash": entry.get("Hash"),
                    },
                )
                self.add_edge(source_node, node, "indexes_unity_asset", source="AnimeStudio/maps")
                self.add_alias(name.lower(), node, kind="unity_asset_name", source=source)
                if path_id is not None:
                    self.add_alias(f"pathid:{path_id}", node, kind="unity_pathid", source=source)
                    pathid_node = self.add_node("unity_pathid", path_id, name=f"pathid:{path_id}", source=source)
                    self.add_edge(pathid_node, node, "resolves_to_unity_asset", source="AnimeStudio/maps")
                container = safe_key(entry.get("Container"))
                if container:
                    container_node = self.add_node("asset_container", container, name=Path(container).name, source=source, path=container)
                    self.add_edge(container_node, node, "contains_unity_asset", source="AnimeStudio/maps")
                for rel in self.asset_by_stem.get(name.lower(), []):
                    self.add_edge(node, self.add_node("asset", rel), "exported_as", source="AnimeStudio/maps")
                batch += 1
                if batch % 25000 == 0:
                    self.db.commit()

    def summary(self, started: float) -> dict[str, Any]:
        node_total = self.db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_total = self.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        alias_total = self.db.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
        file_total = self.db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        nodes_by_kind = dict(self.db.execute("SELECT kind, COUNT(*) FROM nodes GROUP BY kind ORDER BY kind").fetchall())
        edges_by_kind = dict(self.db.execute("SELECT kind, COUNT(*) FROM edges GROUP BY kind ORDER BY kind").fetchall())
        files_by_kind = dict(
            self.db.execute("SELECT COALESCE(kind, ''), COUNT(*) FROM files GROUP BY kind ORDER BY kind").fetchall()
        )
        return {
            "generated": int(time.time()),
            "durationSeconds": round(time.time() - started, 3),
            "database": slash(self.db_path),
            "language": self.language,
            "totals": {
                "nodes": node_total,
                "edges": edge_total,
                "aliases": alias_total,
                "files": file_total,
            },
            "nodesByKind": nodes_by_kind,
            "edgesByKind": edges_by_kind,
            "filesByKind": files_by_kind,
            "options": {
                "includeAssetMaps": self.include_asset_maps,
                "includeReferenceRows": self.include_reference_rows,
                "includeAllMaterialJson": self.include_all_material_json,
                "emitFollowups": self.emit_followups,
            },
        }


def write_summary(summary: dict[str, Any]) -> None:
    DEFAULT_SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Endfield Source Graph",
        "",
        f"- Database: `{summary['database']}`",
        f"- Language: `{summary['language']}`",
        f"- Build time: `{summary['durationSeconds']}` seconds",
        f"- Nodes: `{summary['totals']['nodes']}`",
        f"- Edges: `{summary['totals']['edges']}`",
        f"- Aliases: `{summary['totals']['aliases']}`",
        f"- Files: `{summary['totals']['files']}`",
        "",
        "## Nodes By Kind",
        "",
    ]
    for key, count in summary.get("nodesByKind", {}).items():
        lines.append(f"- `{key}`: `{count}`")
    lines.extend(["", "## Edges By Kind", ""])
    for key, count in summary.get("edgesByKind", {}).items():
        lines.append(f"- `{key}`: `{count}`")
    lines.append("")
    DEFAULT_SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def emit_followup_indexes(db_path: Path, summary: dict[str, Any]) -> None:
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        emit_voice_audio_links(conn)
        emit_character_recovery_candidates(conn)
        emit_option_branch_gaps(conn)
        emit_map_level_index(conn)
        emit_semantic_update_summary(conn)


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def parse_node_data(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    data = row["data"] if isinstance(row, sqlite3.Row) else row.get("data")
    if not data:
        return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {}


def parse_json_text(data: Any) -> dict[str, Any]:
    if not data:
        return {}
    try:
        return json.loads(data)
    except (TypeError, json.JSONDecodeError):
        return {}


def emit_voice_audio_links(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT
            line.id AS lineNode,
            line.name AS lineId,
            line.data AS lineData,
            audio.id AS audioNode,
            audio.name AS audioId,
            audio.path AS audioPath,
            audio.data AS audioData
        FROM edges e
        JOIN nodes line ON line.id = e.src
        JOIN nodes audio ON audio.id = e.dst
        WHERE e.kind = 'uses_audio'
        ORDER BY line.name
        """
    ).fetchall()
    linked = []
    unresolved = []
    for row in rows:
        line_data = parse_json_text(row["lineData"])
        audio_data = parse_json_text(row["audioData"])
        record = {
            "lineId": row["lineId"],
            "audioId": row["audioId"],
            "actorId": line_data.get("actorId"),
            "actor": line_data.get("actor"),
            "text": line_data.get("text"),
            "audioPath": audio_data.get("path") or row["audioPath"],
            "duration": audio_data.get("duration"),
            "speaker": audio_data.get("speaker"),
        }
        if record["audioPath"]:
            linked.append(record)
        else:
            unresolved.append(record)
    payload = {
        "generated": int(time.time()),
        "linked": len(linked),
        "unresolved": len(unresolved),
        "links": linked[:5000],
        "unresolvedExamples": unresolved[:500],
    }
    (GRAPH_DIR / "voice_audio_links.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def emit_character_recovery_candidates(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT id, kind, name, path, source, data
        FROM nodes
        WHERE kind IN ('asset', 'unity_asset', 'material', 'mesh', 'texture', 'animation_clip')
        """
    ).fetchall()
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        haystack = " ".join(str(row[key] or "") for key in ("id", "name", "path", "source"))
        match = ASSET_ACTOR_RE.search(haystack)
        if not match:
            continue
        actor = match.group(1).lower()
        grouped[actor][row["kind"]] += 1
        bucket = examples[actor][row["kind"]]
        if len(bucket) < 8:
            bucket.append(row["name"] or row["id"])
    candidates = []
    for actor, counts in sorted(grouped.items()):
        score = (
            counts.get("mesh", 0) * 4
            + counts.get("material", 0) * 3
            + counts.get("texture", 0) * 2
            + counts.get("animation_clip", 0) * 2
            + counts.get("asset", 0)
            + counts.get("unity_asset", 0)
        )
        candidates.append({
            "actor": actor,
            "score": score,
            "counts": dict(counts),
            "examples": {key: value for key, value in examples[actor].items()},
        })
    candidates.sort(key=lambda row: (-row["score"], row["actor"]))
    payload = {
        "generated": int(time.time()),
        "candidates": candidates,
    }
    (GRAPH_DIR / "character_recovery_candidates.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def emit_option_branch_gaps(conn: sqlite3.Connection) -> None:
    report_path = ROOT / "reports" / f"inferred_option_anchors_{conn.execute('SELECT value FROM meta WHERE key=?', ('language',)).fetchone()[0]}.json"
    report = read_json(report_path, {})
    scenes = report.get("scenes") or report.get("entries") or []
    if not scenes and isinstance(report, dict):
        for key in ("items", "rows"):
            if isinstance(report.get(key), list):
                scenes = report[key]
                break
    story_rows = conn.execute(
        """
        SELECT story.name AS storyKey, COUNT(e.id) AS graphEdges
        FROM nodes story
        LEFT JOIN edges e ON e.src = story.id AND e.kind LIKE 'option_%'
        WHERE story.kind = 'story'
        GROUP BY story.id
        """
    ).fetchall()
    edge_counts = {row["storyKey"]: row["graphEdges"] for row in story_rows}
    output_scenes = []
    if isinstance(scenes, list):
        for scene in scenes:
            key = scene.get("scene") or scene.get("key") or scene.get("storyKey")
            if not key:
                continue
            scene = dict(scene)
            scene["graphOptionEdges"] = edge_counts.get(key, 0)
            output_scenes.append(scene)
    payload = {
        "generated": int(time.time()),
        "sourceReport": slash(report_path),
        "scenes": output_scenes,
        "count": len(output_scenes),
    }
    (GRAPH_DIR / "option_branch_gaps.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def emit_map_level_index(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT level.name AS levelId, mark.name AS markId, mark.data AS markData
        FROM edges e
        JOIN nodes level ON level.id = e.src
        JOIN nodes mark ON mark.id = e.dst
        WHERE e.kind = 'has_map_mark'
        ORDER BY level.name, mark.name
        """
    ).fetchall()
    levels: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        data = parse_json_text(row["markData"])
        levels[row["levelId"]].append({
            "markId": row["markId"],
            "markInfoId": data.get("markInfoId"),
            "pos": data.get("pos"),
        })
    payload = {
        "generated": int(time.time()),
        "levels": [{"levelId": level, "marks": marks} for level, marks in sorted(levels.items())],
    }
    (GRAPH_DIR / "map_level_index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def emit_semantic_update_summary(conn: sqlite3.Connection) -> None:
    updates_path = WEBUI_DATA / "updates" / "latest.json"
    updates = read_json(updates_path, {})
    categories: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in updates.get("entries") or []:
        path = safe_key(entry.get("path") or entry.get("rel") or entry.get("file"))
        category = classify_update_path(path)
        categories[category] += 1
        if len(examples[category]) < 12:
            examples[category].append(compact_payload(entry, depth=2))
    payload = {
        "generated": int(time.time()),
        "source": slash(updates_path),
        "sourceTotals": updates.get("totals"),
        "categories": dict(sorted(categories.items())),
        "examples": dict(sorted(examples.items())),
    }
    (GRAPH_DIR / "semantic_update_summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def classify_update_path(path: str) -> str:
    lower = path.lower()
    if "/table/" in lower or "\\table\\" in lower:
        return "table"
    if "/lua/" in lower or "\\lua\\" in lower:
        return "lua"
    if "/video/" in lower or lower.endswith((".usm", ".mp4")):
        return "video"
    if "/audio/" in lower or lower.endswith((".wem", ".pck", ".bnk")):
        return "audio"
    if any(token in lower for token in ("texture", "/sprite/", "\\sprite\\")):
        return "image"
    if any(token in lower for token in ("mesh", "postmodel", "prefab")):
        return "model_or_prefab"
    if "material" in lower or lower.endswith(".mat"):
        return "material"
    if "animation" in lower or "animator" in lower:
        return "animation"
    return "other"


QUERY_KIND_PRIORITY = {
    "story": 0,
    "option_group": 1,
    "option": 2,
    "line": 3,
    "mission": 4,
    "actor": 5,
    "audio": 6,
    "file": 7,
}

NODE_ID_PREFIXES = (
    "story",
    "option_group",
    "option",
    "line",
    "mission",
    "actor",
    "audio",
    "video",
    "file",
    "table_row",
)

OPTION_BRANCH_EDGE_KINDS = (
    "option_anchor_after",
    "option_first_line",
    "option_branch_line",
    "option_path_line",
    "option_path_story",
    "option_merge_line",
    "option_enters_story",
)


def exact_node_candidates(term: str) -> list[str]:
    candidates = [term]
    if ":" not in term:
        candidates.extend(f"{prefix}:{term}" for prefix in NODE_ID_PREFIXES)
    return candidates


def node_sort_key(row: dict[str, Any], term: str, exact_ids: set[str]) -> tuple[int, int, str]:
    term_lower = term.lower()
    row_id = safe_key(row.get("id")).lower()
    row_name = safe_key(row.get("name")).lower()
    row_path = safe_key(row.get("path")).lower()
    if row_id in exact_ids:
        match_rank = 0
    elif row_name == term_lower:
        match_rank = 1
    elif row_path == term_lower:
        match_rank = 2
    else:
        match_rank = 3
    kind_rank = QUERY_KIND_PRIORITY.get(safe_key(row.get("kind")), 99)
    return (match_rank, kind_rank, safe_key(row.get("name") or row.get("id")))


def resolve_seed_node(conn: sqlite3.Connection, term: str, nodes: list[dict[str, Any]], *, kind: str = "") -> str:
    exact_alias = conn.execute(
        """
        SELECT aliases.node_id
        FROM aliases
        JOIN nodes ON nodes.id = aliases.node_id
        WHERE LOWER(aliases.alias) = LOWER(?)
          AND (? = '' OR nodes.kind = ?)
        ORDER BY
          CASE aliases.kind
            WHEN 'story_key' THEN 0
            WHEN 'line_id' THEN 1
            ELSE 2
          END,
          CASE nodes.kind
            WHEN 'story' THEN 0
            WHEN 'option' THEN 1
            WHEN 'line' THEN 2
            ELSE 3
          END
        LIMIT 1
        """,
        (term, kind, kind),
    ).fetchone()
    if exact_alias:
        return exact_alias["node_id"]
    if nodes:
        return nodes[0]["id"]
    return ""


def query_graph(db_path: Path, term: str, *, limit: int = 40, kind: str = "") -> dict[str, Any]:
    like = f"%{term}%"
    exact_candidates = exact_node_candidates(term)
    exact_placeholders = ",".join("?" for _ in exact_candidates)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        exact_nodes = rows_to_dicts(
            conn.execute(
                f"""
                SELECT id, kind, name, source, path
                FROM nodes
                WHERE (id IN ({exact_placeholders}) OR LOWER(name) = LOWER(?) OR LOWER(path) = LOWER(?))
                  AND (? = '' OR kind = ?)
                ORDER BY kind, name
                LIMIT ?
                """,
                (*exact_candidates, term, term, kind, kind, limit),
            ).fetchall()
        )
        exact_ids = {row["id"].lower() for row in exact_nodes}
        fuzzy_limit = max(limit - len(exact_nodes), 0)
        fuzzy_nodes: list[dict[str, Any]] = []
        if fuzzy_limit:
            fuzzy_nodes = rows_to_dicts(
                conn.execute(
                    f"""
                    SELECT id, kind, name, source, path
                    FROM nodes
                    WHERE (id LIKE ? OR name LIKE ? OR path LIKE ?)
                      AND id NOT IN ({exact_placeholders})
                      AND (? = '' OR kind = ?)
                    ORDER BY kind, name
                    LIMIT ?
                    """,
                    (like, like, like, *exact_candidates, kind, kind, fuzzy_limit),
                ).fetchall()
            )
        nodes = [*exact_nodes, *fuzzy_nodes]
        nodes.sort(key=lambda row: node_sort_key(row, term, exact_ids))
        nodes = nodes[:limit]
        aliases = rows_to_dicts(
            conn.execute(
                """
                SELECT alias, node_id, kind, source
                FROM aliases
                WHERE alias LIKE ?
                ORDER BY alias
                LIMIT ?
                """,
                (like, limit),
            ).fetchall()
        )
        related: list[dict[str, Any]] = []
        seed = resolve_seed_node(conn, term, nodes, kind=kind)
        if seed:
            related = rows_to_dicts(
                conn.execute(
                    """
                    SELECT e.kind AS edge, e.source, e.evidence,
                           src.kind AS srcKind, src.name AS srcName,
                           dst.kind AS dstKind, dst.name AS dstName, dst.path AS dstPath
                    FROM edges e
                    JOIN nodes src ON src.id = e.src
                    JOIN nodes dst ON dst.id = e.dst
                    WHERE e.src = ? OR e.dst = ?
                    ORDER BY e.kind, dst.kind, dst.name
                    LIMIT ?
                    """,
                    (seed, seed, limit),
                ).fetchall()
            )
        return {"seedNode": seed, "nodes": nodes, "aliases": aliases, "relatedToFirstNode": related}


def compact_node_ref(row: sqlite3.Row, edge_row: sqlite3.Row | None = None) -> dict[str, Any]:
    data = parse_json_text(row["data"])
    ref: dict[str, Any] = {
        "id": row["id"],
        "key": node_key(row["id"]),
        "kind": row["kind"],
        "name": row["name"],
    }
    if row["path"]:
        ref["path"] = row["path"]
    if isinstance(data, dict):
        for key in ("actor", "actorId", "audio", "text", "timestamp", "duration"):
            value = data.get(key)
            if value not in (None, "", [], {}):
                ref[key] = value
    if edge_row is not None:
        if edge_row["source"]:
            ref["source"] = edge_row["source"]
        if edge_row["evidence"]:
            ref["evidence"] = edge_row["evidence"]
        edge_data = parse_json_text(edge_row["data"])
        if edge_data:
            ref["edgeData"] = edge_data
    return ref


def node_key(node_id: str) -> str:
    return node_id.split(":", 1)[1] if ":" in node_id else node_id


def option_group_sort_key(group: dict[str, Any]) -> tuple[int, str]:
    data = group.get("data") or {}
    index = data.get("index") or data.get("g")
    if isinstance(index, int):
        return (index, group["key"])
    if isinstance(index, str) and index.isdigit():
        return (int(index), group["key"])
    match = re.search(r"#optionGroup:(\d+)", group["key"])
    if match:
        return (int(match.group(1)), group["key"])
    return (999999, group["key"])


def option_sort_key(option: dict[str, Any]) -> tuple[int, str]:
    data = option.get("data") or {}
    index = data.get("index")
    if isinstance(index, int):
        return (index, option["key"])
    if isinstance(index, str) and index.isdigit():
        return (int(index), option["key"])
    match = re.search(r"_(\d+)$", option["key"])
    if match:
        return (int(match.group(1)), option["key"])
    return (999999, option["key"])


def story_arrangement(db_path: Path, story_key: str, *, limit_lines: int = 0) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        seed_nodes = rows_to_dicts(
            conn.execute(
                """
                SELECT id, kind, name, source, path
                FROM nodes
                WHERE kind = 'story'
                  AND (LOWER(name) = LOWER(?) OR LOWER(id) = LOWER(?) OR LOWER(id) = LOWER(?))
                LIMIT 1
                """,
                (story_key, story_key, f"story:{story_key}"),
            ).fetchall()
        )
        seed = resolve_seed_node(conn, story_key, seed_nodes, kind="story")
        if not seed:
            raise ValueError(f"story not found: {story_key}")

        story_row = conn.execute("SELECT id, kind, name, source, path, data FROM nodes WHERE id = ?", (seed,)).fetchone()
        story_data = parse_json_text(story_row["data"])

        line_rows = conn.execute(
            """
            SELECT edge.evidence, edge.source, edge.data AS edgeData,
                   line.id, line.kind, line.name, line.source AS nodeSource, line.path, line.data
            FROM edges edge
            JOIN nodes line ON line.id = edge.dst
            WHERE edge.src = ? AND edge.kind = 'has_line'
            ORDER BY CAST(edge.evidence AS INTEGER), edge.id
            """,
            (seed,),
        ).fetchall()
        lines = []
        for row in line_rows:
            line_ref = compact_node_ref(row)
            line_ref["order"] = int(row["evidence"]) if safe_key(row["evidence"]).isdigit() else len(lines)
            lines.append(line_ref)
        if limit_lines > 0:
            lines = lines[:limit_lines]

        group_rows = conn.execute(
            """
            SELECT group_node.id, group_node.kind, group_node.name, group_node.source, group_node.path, group_node.data
            FROM edges edge
            JOIN nodes group_node ON group_node.id = edge.dst
            WHERE edge.src = ? AND edge.kind = 'has_option_group'
            ORDER BY group_node.name
            """,
            (seed,),
        ).fetchall()

        groups = []
        for group_row in group_rows:
            group_data = parse_json_text(group_row["data"])
            group = {
                "id": group_row["id"],
                "key": node_key(group_row["id"]),
                "after": group_data.get("after"),
                "risk": group_data.get("risk"),
                "reason": group_data.get("reason"),
                "riskSource": group_data.get("riskSource"),
                "data": group_data,
                "options": [],
            }
            option_rows = conn.execute(
                """
                SELECT option_node.id, option_node.kind, option_node.name, option_node.source, option_node.path, option_node.data
                FROM edges edge
                JOIN nodes option_node ON option_node.id = edge.dst
                WHERE edge.src = ? AND edge.kind = 'has_option'
                ORDER BY edge.id
                """,
                (group_row["id"],),
            ).fetchall()
            for option_row in option_rows:
                option_data = parse_json_text(option_row["data"])
                option = {
                    "id": option_row["id"],
                    "key": node_key(option_row["id"]),
                    "text": option_data.get("text") or option_row["name"],
                    "icon": option_data.get("icon"),
                    "data": option_data,
                    "branches": {},
                }
                branch_rows = conn.execute(
                    f"""
                    SELECT edge.kind AS edgeKind, edge.source, edge.evidence, edge.data,
                           target.id, target.kind, target.name, target.source AS nodeSource, target.path, target.data AS targetData
                    FROM edges edge
                    JOIN nodes target ON target.id = edge.dst
                    WHERE edge.src = ?
                      AND edge.kind IN ({','.join('?' for _ in OPTION_BRANCH_EDGE_KINDS)})
                    ORDER BY edge.kind, edge.id
                    """,
                    (option_row["id"], *OPTION_BRANCH_EDGE_KINDS),
                ).fetchall()
                for branch_row in branch_rows:
                    target_row = {
                        "id": branch_row["id"],
                        "kind": branch_row["kind"],
                        "name": branch_row["name"],
                        "path": branch_row["path"],
                        "data": branch_row["targetData"],
                    }
                    option["branches"].setdefault(branch_row["edgeKind"], []).append(
                        compact_node_ref(target_row, branch_row)
                    )
                group["options"].append(option)
            group["options"].sort(key=option_sort_key)
            groups.append(group)
        groups.sort(key=option_group_sort_key)

        return {
            "story": {
                "id": story_row["id"],
                "key": story_row["name"],
                "path": story_row["path"],
                "kind": story_data.get("kind"),
                "mission": story_data.get("mission"),
                "scene": story_data.get("scene"),
                "lineCount": story_data.get("lineCount"),
                "preview": story_data.get("preview"),
            },
            "lines": lines,
            "optionGroups": groups,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    build = sub.add_parser("build", help="Build the SQLite source graph")
    build.add_argument("--db", type=Path, default=DEFAULT_DB)
    build.add_argument("--language", default="CN")
    build.add_argument("--skip-asset-maps", action="store_true")
    build.add_argument("--skip-reference-rows", action="store_true")
    build.add_argument("--include-all-material-json", action="store_true")
    build.add_argument("--skip-followups", action="store_true")

    query = sub.add_parser("query", help="Search graph nodes and show first-node neighbors")
    query.add_argument("term")
    query.add_argument("--db", type=Path, default=DEFAULT_DB)
    query.add_argument("--limit", type=int, default=40)
    query.add_argument("--kind", default="", help="Optional node kind filter, such as story, option, line, or audio.")

    story = sub.add_parser("story", help="Show recovered line order and option branch evidence for one story key")
    story.add_argument("story_key")
    story.add_argument("--db", type=Path, default=DEFAULT_DB)
    story.add_argument("--limit-lines", type=int, default=0, help="Only include the first N ordered lines; 0 includes all.")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command in (None, "build"):
        builder = SourceGraphBuilder(
            db_path=args.db if hasattr(args, "db") else DEFAULT_DB,
            language=getattr(args, "language", "CN"),
            include_asset_maps=not getattr(args, "skip_asset_maps", False),
            include_reference_rows=not getattr(args, "skip_reference_rows", False),
            include_all_material_json=getattr(args, "include_all_material_json", False),
            emit_followups=not getattr(args, "skip_followups", False),
        )
        summary = builder.build()
        print(
            "Source graph: "
            f"{summary['totals']['nodes']} nodes, "
            f"{summary['totals']['edges']} edges, "
            f"{summary['totals']['aliases']} aliases"
        )
        print(f"Wrote {summary['database']}")
        print(f"Wrote {slash(DEFAULT_SUMMARY_JSON)}")
        if summary["options"]["emitFollowups"]:
            print(f"Wrote follow-up indexes under {slash(GRAPH_DIR)}")
        return 0
    if args.command == "query":
        result = query_graph(args.db, args.term, limit=args.limit, kind=args.kind)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "story":
        result = story_arrangement(args.db, args.story_key, limit_lines=args.limit_lines)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
