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
WEBUI_OPTION_OVERRIDES = ROOT / "webui" / "overrides" / "options.json"
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
TIMELINE_LINE_ORDERS_REL = Path("recovered") / "AnimeStudio-cli" / "timeline_line_orders.json"
TIMELINE_LINE_ORDERS_PATH = EXPORT_ROOT / TIMELINE_LINE_ORDERS_REL

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
PATH_ID_EXPORT_STEM_RE = re.compile(r"^(?P<base>.+)_p(?P<path_id>[0-9A-Fa-f]{16})$")
ASSET_SINGLE_PREFIX_RE = re.compile(r"^[A-Za-z]_")
ASSET_LOD_SUFFIX_RE = re.compile(r"(?:[_-])lod\d+$", re.IGNORECASE)
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


def path_id_export_base_stem(value: Any) -> str:
    match = PATH_ID_EXPORT_STEM_RE.match(str(value or ""))
    return match.group("base") if match else ""


def normalized_model_entity_base(stem: str) -> str:
    logical_stem = path_id_export_base_stem(stem) or stem
    stripped = ASSET_SINGLE_PREFIX_RE.sub("", logical_stem, count=1)
    return ASSET_LOD_SUFFIX_RE.sub("", stripped).lower()


def lod_model_entity_base(rel: str) -> str:
    stem = Path(rel).stem
    logical_stem = path_id_export_base_stem(stem) or stem
    stripped = ASSET_SINGLE_PREFIX_RE.sub("", logical_stem, count=1)
    if not ASSET_LOD_SUFFIX_RE.search(stripped):
        return ""
    return normalized_model_entity_base(stem)


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


def _unique_preserve(values: Iterable[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


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
        include_gameplay: bool = True,
        include_asset_maps: bool = True,
        include_reference_rows: bool = True,
        include_all_material_json: bool = False,
        emit_followups: bool = True,
    ) -> None:
        self.root = root
        self.export_root = export_root
        self.language = language
        self.include_gameplay = include_gameplay
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
        self.asset_entities_by_base: dict[str, list[str]] = defaultdict(list)
        self.asset_paths: list[str] = []
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
            self.ingest_option_overrides()
            self.commit_step("optionOverrides")
            if self.include_gameplay:
                self.ingest_gameplay()
                self.commit_step("gameplay")
            self.ingest_timeline_line_orders()
            self.commit_step("timelineLineOrders")
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
        asset_nodes_by_rel: dict[str, str] = {}
        asset_entity_key_by_model_rel: dict[str, tuple[str, str]] = {}
        asset_entity_groups: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {"source": "", "base": "", "models": {}, "materials": {}, "textures": {}}
        )

        def asset_node_for_rel(rel_value: Any) -> str:
            rel_text = safe_key(rel_value)
            if not rel_text:
                return ""
            node = asset_nodes_by_rel.get(rel_text)
            if node:
                return node
            return self.add_node(
                "asset",
                rel_text,
                name=Path(rel_text).name,
                source=rel_text.split("/", 1)[0],
                path=rel_text,
            )

        def add_pid_aliases(pid_value: Any, node_id: str) -> None:
            raw = safe_key(pid_value).upper()
            if raw.startswith("PID:"):
                raw = raw[4:]
            if raw.startswith("0X"):
                raw = raw[2:]
            if not re.fullmatch(r"[0-9A-F]{1,16}", raw):
                return
            number = int(raw, 16)
            pid = f"{number:016X}"
            self.add_alias(f"pid:{pid}", node_id, kind="asset_pid", source="webui/assets")
            signed_path_id = number - (1 << 64) if number & (1 << 63) else number
            self.add_alias(f"pathid:{signed_path_id}", node_id, kind="asset_pathid", source="webui/assets")

        def relation_data(item: dict[str, Any]) -> dict[str, Any]:
            return {
                key: item.get(key)
                for key in ("slot", "name", "pid", "rel")
                if item.get(key) not in (None, "")
            }

        def relation_evidence(item: dict[str, Any]) -> str:
            slot = safe_key(item.get("slot"))
            name = safe_key(item.get("name"))
            pid = safe_key(item.get("pid"))
            return " ".join(part for part in (slot, name or pid) if part)

        for entry in payload.get("entries") or []:
            rel = safe_key(entry.get("r"))
            if not rel:
                continue
            kind = safe_key(entry.get("k")) or "asset"
            size = entry.get("s")
            pid = safe_key(entry.get("pid")).upper()
            data = {
                key: value
                for key, value in {
                    "type": kind,
                    "size": size,
                    "preview": entry.get("p"),
                    "pid": pid,
                    "category": entry.get("ic"),
                    "materialLike": bool(entry.get("mt")) if entry.get("mt") else None,
                }.items()
                if value not in (None, "")
            }
            node = self.add_node(
                "asset",
                rel,
                name=Path(rel).name,
                source=rel.split("/", 1)[0],
                path=rel,
                data=data,
            )
            asset_nodes_by_rel[rel] = node
            self.add_edge(root_node, node, "indexes_asset", source="webui/assets")
            self.add_file(rel, kind=kind, source=rel.split("/", 1)[0], size=size)
            stem = Path(rel).stem.lower()
            self.asset_by_stem[stem].append(rel)
            self.asset_by_name[Path(rel).name.lower()].append(rel)
            self.asset_paths.append(rel)
            self.add_alias(stem, node, kind="asset_stem", source="webui/assets")
            self.add_alias(Path(rel).name.lower(), node, kind="asset_name", source="webui/assets")
            if pid:
                add_pid_aliases(pid, node)
            if kind == "model":
                model_base = lod_model_entity_base(rel)
                if model_base:
                    source = rel.split("/", 1)[0]
                    entity_key = (source, model_base)
                    asset_entity_key_by_model_rel[rel] = entity_key
                    group = asset_entity_groups[entity_key]
                    group["source"] = source
                    group["base"] = model_base
                    group["models"][rel] = {"pid": pid} if pid else {}
            if entry.get("p"):
                preview = asset_node_for_rel(entry["p"])
                self.add_edge(node, preview, "previewed_by", source="webui/assets")

        relations = payload.get("relations") or {}
        if isinstance(relations, dict):
            for rel, relation in sorted(relations.items()):
                if not isinstance(relation, dict):
                    continue
                src_node = asset_node_for_rel(rel)
                if not src_node:
                    continue
                entity_key = asset_entity_key_by_model_rel.get(rel)
                entity_group = asset_entity_groups.get(entity_key) if entity_key else None

                for item in relation.get("materials") or []:
                    if not isinstance(item, dict):
                        continue
                    dst_rel = safe_key(item.get("rel"))
                    if not dst_rel:
                        continue
                    dst_node = asset_node_for_rel(dst_rel)
                    material_evidence = safe_key(item.get("name")) or Path(dst_rel).stem
                    material_data = relation_data(item)
                    self.add_edge(
                        src_node,
                        dst_node,
                        "uses_material",
                        source="webui/assets",
                        evidence=material_evidence,
                        data=material_data,
                    )
                    if entity_group is not None:
                        entity_group["materials"].setdefault(
                            dst_rel,
                            {"evidence": material_evidence, "data": material_data},
                        )

                for item in relation.get("textures") or []:
                    if not isinstance(item, dict):
                        continue
                    dst_rel = safe_key(item.get("rel"))
                    if not dst_rel:
                        continue
                    dst_node = asset_node_for_rel(dst_rel)
                    texture_evidence = relation_evidence(item)
                    texture_data = relation_data(item)
                    self.add_edge(
                        src_node,
                        dst_node,
                        "uses_texture",
                        source="webui/assets",
                        evidence=texture_evidence,
                        data=texture_data,
                    )
                    if entity_group is not None:
                        entity_group["textures"].setdefault(
                            dst_rel,
                            {"evidence": texture_evidence, "data": texture_data},
                        )

                for item in relation.get("referencedByMaterials") or []:
                    if not isinstance(item, dict):
                        continue
                    dst_rel = safe_key(item.get("rel"))
                    if not dst_rel:
                        continue
                    dst_node = asset_node_for_rel(dst_rel)
                    self.add_edge(
                        src_node,
                        dst_node,
                        "referenced_by_material",
                        source="webui/assets",
                        evidence=relation_evidence(item),
                        data=relation_data(item),
                    )

                for item in relation.get("referencedByModels") or []:
                    if not isinstance(item, dict):
                        continue
                    dst_rel = safe_key(item.get("rel"))
                    if not dst_rel:
                        continue
                    dst_node = asset_node_for_rel(dst_rel)
                    self.add_edge(
                        src_node,
                        dst_node,
                        "referenced_by_model",
                        source="webui/assets",
                        evidence=safe_key(item.get("name")) or Path(dst_rel).stem,
                        data=relation_data(item),
                    )

        relation_lookup = relations if isinstance(relations, dict) else {}
        for (_source, _model_base), group in sorted(asset_entity_groups.items()):
            source = safe_key(group.get("source"))
            model_base = safe_key(group.get("base"))
            if not source or not model_base:
                continue
            for material_rel, material_info in sorted(group["materials"].items()):
                material_relation = relation_lookup.get(material_rel) or {}
                if not isinstance(material_relation, dict):
                    continue
                for item in material_relation.get("textures") or []:
                    if not isinstance(item, dict):
                        continue
                    dst_rel = safe_key(item.get("rel"))
                    if not dst_rel:
                        continue
                    texture_data = relation_data(item)
                    texture_data["viaMaterial"] = material_rel
                    texture_evidence = relation_evidence(item) or Path(dst_rel).stem
                    group["textures"].setdefault(
                        dst_rel,
                        {
                            "evidence": texture_evidence,
                            "data": texture_data,
                        },
                    )

            entity_node = self.add_node(
                "asset_entity",
                f"{source}/{model_base}",
                name=model_base,
                source=source,
                data={
                    "source": source,
                    "modelBase": model_base,
                    "lodModelCount": len(group["models"]),
                    "materialCount": len(group["materials"]),
                    "textureCount": len(group["textures"]),
                },
            )
            self.add_alias(model_base, entity_node, kind="asset_entity_id", source="webui/assets")
            self.add_alias(f"{source}/{model_base}", entity_node, kind="asset_entity_id", source="webui/assets")
            self.asset_entities_by_base[model_base].append(entity_node)
            for model_rel, model_info in sorted(group["models"].items()):
                model_node = asset_node_for_rel(model_rel)
                model_data = {"rel": model_rel}
                if isinstance(model_info, dict) and model_info.get("pid"):
                    model_data["pid"] = model_info["pid"]
                self.add_edge(
                    entity_node,
                    model_node,
                    "entity_has_lod_model",
                    source="webui/assets",
                    evidence=Path(model_rel).stem,
                    data=model_data,
                )
            for material_rel, material_info in sorted(group["materials"].items()):
                material_node = asset_node_for_rel(material_rel)
                material_data = dict(material_info.get("data") or {}) if isinstance(material_info, dict) else {}
                material_data.setdefault("rel", material_rel)
                self.add_edge(
                    entity_node,
                    material_node,
                    "entity_uses_material",
                    source="webui/assets",
                    evidence=safe_key(material_info.get("evidence")) if isinstance(material_info, dict) else Path(material_rel).stem,
                    data=material_data,
                )
            for texture_rel, texture_info in sorted(group["textures"].items()):
                texture_node = asset_node_for_rel(texture_rel)
                texture_data = dict(texture_info.get("data") or {}) if isinstance(texture_info, dict) else {}
                texture_data.setdefault("rel", texture_rel)
                self.add_edge(
                    entity_node,
                    texture_node,
                    "entity_uses_texture",
                    source="webui/assets",
                    evidence=safe_key(texture_info.get("evidence")) if isinstance(texture_info, dict) else Path(texture_rel).stem,
                    data=texture_data,
                )

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
            self.add_recovery_warnings(conv, story_node)

    def ingest_option_overrides(self) -> None:
        payload = read_json(WEBUI_OPTION_OVERRIDES, {})
        scenes = payload.get("scenes") if isinstance(payload, dict) else {}
        if not isinstance(scenes, dict) or not scenes:
            return
        file_rel = slash(WEBUI_OPTION_OVERRIDES)
        file_node = self.add_file(
            file_rel,
            kind="option_override",
            source="webui/option_override",
            data={"sceneCount": len(scenes)},
        )

        def group_id_text(value: Any) -> str:
            text = safe_key(value)
            if not text:
                return ""
            try:
                return str(int(text))
            except ValueError:
                return text

        def override_key(story_key: str, group_id: str) -> str:
            return f"{story_key}#optionGroup:{group_id}"

        def note_for(scene_override: dict[str, Any], group_id: str) -> str:
            notes = scene_override.get("notes") if isinstance(scene_override, dict) else {}
            if not isinstance(notes, dict):
                return ""
            return safe_key(notes.get(group_id))

        def response_group_id(story_key: str, option_id: str) -> str:
            prefix = f"option_{story_key}_"
            if option_id.startswith(prefix):
                return group_id_text(option_id[len(prefix):].split("_", 1)[0])
            match = re.search(r"_(\d+)_\d+$", option_id)
            return group_id_text(match.group(1)) if match else ""

        def ensure_override_node(story_key: str, group_id: str, scene_override: dict[str, Any]) -> str:
            key = override_key(story_key, group_id)
            note = note_for(scene_override, group_id)
            node = self.add_node(
                "option_override",
                key,
                name=key,
                source="webui/option_override",
                path=file_rel,
                data={"story": story_key, "group": group_id, "note": note, "webuiOnly": True},
            )
            story_node = self.add_node("story", story_key, source="webui/option_override")
            group_node = self.add_node("option_group", key, source="webui/option_override")
            self.add_edge(story_node, node, "has_option_override", source="webui/option_override", evidence=group_id)
            self.add_edge(file_node, node, "defines_option_override", source="webui/option_override", evidence=story_key)
            self.add_edge(node, group_node, "overrides_option_group", source="webui/option_override", evidence=group_id)
            self.add_alias(f"manual-option:{story_key}:{group_id}", node, kind="option_override", source="webui/option_override")
            self.add_alias(f"option-override:{story_key}:{group_id}", node, kind="option_override", source="webui/option_override")
            return node

        for story_key_raw, scene_override in sorted(scenes.items()):
            story_key = safe_key(story_key_raw)
            if not story_key or not isinstance(scene_override, dict):
                continue
            positions = scene_override.get("positions") if isinstance(scene_override.get("positions"), dict) else {}
            positions_after = positions.get("after") if isinstance(positions.get("after"), dict) else {}
            positions_pre = positions.get("pre") if isinstance(positions.get("pre"), list) else []
            responses = scene_override.get("responses") if isinstance(scene_override.get("responses"), dict) else {}
            story_node = self.add_node("story", story_key, source="webui/option_override")

            for group_raw in positions_pre:
                group_id = group_id_text(group_raw)
                if not group_id:
                    continue
                override_node = ensure_override_node(story_key, group_id, scene_override)
                group_node = self.add_node("option_group", override_key(story_key, group_id), source="webui/option_override")
                data = {"story": story_key, "group": group_id, "position": "pre", "note": note_for(scene_override, group_id), "webuiOnly": True}
                self.add_edge(group_node, story_node, "manual_position_pre", source="webui/option_override", evidence=group_id, data=data)
                self.add_edge(override_node, group_node, "manual_position_pre", source="webui/option_override", evidence=group_id, data=data)

            for anchor_line, groups in sorted(positions_after.items()):
                if not isinstance(groups, list):
                    continue
                anchor_id = safe_key(anchor_line)
                if not anchor_id:
                    continue
                anchor_node = self.add_node("line", anchor_id, source="webui/option_override")
                for group_raw in groups:
                    group_id = group_id_text(group_raw)
                    if not group_id:
                        continue
                    override_node = ensure_override_node(story_key, group_id, scene_override)
                    group_node = self.add_node("option_group", override_key(story_key, group_id), source="webui/option_override")
                    data = {"story": story_key, "group": group_id, "position": "after", "anchor": anchor_id, "note": note_for(scene_override, group_id), "webuiOnly": True}
                    self.add_edge(group_node, anchor_node, "anchored_after_line", source="webui/option_override", evidence=group_id, data=data)
                    self.add_edge(override_node, anchor_node, "manual_position_after", source="webui/option_override", evidence=group_id, data=data)

            for option_id_raw, targets_raw in sorted(responses.items()):
                option_id = safe_key(option_id_raw)
                targets = [safe_key(target) for target in targets_raw or [] if safe_key(target)] if isinstance(targets_raw, list) else []
                if not option_id or not targets:
                    continue
                group_id = response_group_id(story_key, option_id)
                if not group_id:
                    continue
                override_node = ensure_override_node(story_key, group_id, scene_override)
                option_node = self.add_node("option", option_id, source="webui/option_override")
                self.add_edge(override_node, option_node, "overrides_option", source="webui/option_override", evidence=group_id)
                data = {"story": story_key, "group": group_id, "targets": targets, "note": note_for(scene_override, group_id), "webuiOnly": True}
                first_line_node = self.add_node("line", targets[0], source="webui/option_override")
                self.add_edge(option_node, first_line_node, "option_first_line", source="webui/option_override", evidence=group_id, data=data)
                for target in targets:
                    target_node = self.add_node("line", target, source="webui/option_override")
                    self.add_edge(option_node, target_node, "option_path_line", source="webui/option_override", evidence=group_id, data=data)
                self.add_edge(option_node, story_node, "option_path_story", source="webui/option_override", evidence=group_id, data=data)
                self.add_edge(option_node, story_node, "option_enters_story", source="webui/option_override", evidence=group_id, data=data)

    def ingest_gameplay(self) -> None:
        path = WEBUI_DATA / "lang" / self.language / "gameplay" / "index.json"
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            return
        entries = [entry for entry in payload.get("entries") or [] if isinstance(entry, dict)]
        if not entries:
            return
        dataset = self.add_node(
            "dataset",
            f"gameplay_{self.language}",
            name=f"Gameplay {self.language}",
            source="webui/gameplay",
            path=slash(path),
            data={"counts": payload.get("counts"), "entryCount": len(entries)},
        )
        language_node = self.add_node("language", self.language, name=self.language)
        self.add_edge(language_node, dataset, "has_gameplay_dataset", source="webui/gameplay")
        self.add_file(slash(path), kind="gameplay_index", source=self.language)
        for entry in entries:
            self.add_gameplay_entry(dataset, entry)

    def add_gameplay_entry(self, dataset_node: str, entry: dict[str, Any]) -> None:
        entry_id = safe_key(entry.get("id"))
        if not entry_id:
            return
        kind = safe_key(entry.get("kind")) or "entry"
        node_kind = {"weapon": "weapon", "equipment": "equipment", "character": "character"}.get(kind, "gameplay_entry")
        stats = entry.get("stats") if isinstance(entry.get("stats"), dict) else {}
        formula = entry.get("formula") if isinstance(entry.get("formula"), dict) else {}
        node = self.add_node(
            node_kind,
            entry_id,
            name=entry.get("title") or entry_id,
            source="webui/gameplay",
            data={
                "kind": kind,
                "title": entry.get("title"),
                "subtitle": entry.get("subtitle"),
                "group": entry.get("group"),
                "rarity": entry.get("rarity"),
                "weaponType": entry.get("weaponType"),
                "weaponTypeLabel": entry.get("weaponTypeLabel"),
                "element": entry.get("element"),
                "elementLabel": entry.get("elementLabel"),
                "profession": entry.get("profession"),
                "professionLabel": entry.get("professionLabel"),
                "partType": entry.get("partType"),
                "partTypeLabel": entry.get("partTypeLabel"),
                "showingType": entry.get("showingType"),
                "showingTypeLabel": entry.get("showingTypeLabel"),
                "domainId": entry.get("domainId"),
                "domainName": entry.get("domainName"),
                "suitId": entry.get("suitId"),
                "formulaId": formula.get("formulaId"),
                "formulaName": formula.get("formulaName") or formula.get("name"),
                "source": entry.get("source"),
                "stats": self.gameplay_progression_summary(stats),
            },
        )
        self.add_edge(dataset_node, node, "has_gameplay_entry", source="webui/gameplay", evidence=kind)
        for alias, alias_kind in (
            (entry_id, f"{node_kind}_id"),
            (entry.get("title"), f"{node_kind}_name"),
            (entry.get("subtitle"), f"{node_kind}_alias"),
            (entry.get("internalName"), f"{node_kind}_alias"),
            (entry.get("engName"), f"{node_kind}_alias"),
            (entry.get("fileName"), "model_name"),
            (entry.get("modelPath"), "model_path"),
            (entry.get("iconId"), "icon_id"),
        ):
            self.add_alias(alias, node, kind=alias_kind, source="webui/gameplay")
        self.add_gameplay_source_edges(node, entry.get("source"))
        self.add_gameplay_asset_edges(node, entry)
        self.add_gameplay_asset_entity_edges(node, entry)

        default_weapon_id = safe_key(entry.get("defaultWeaponId"))
        if default_weapon_id:
            weapon_node = self.add_node("weapon", default_weapon_id, name=entry.get("defaultWeaponName") or default_weapon_id, source="webui/gameplay")
            self.add_edge(node, weapon_node, "default_weapon", source="webui/gameplay")

        for label in ("stats", "upgrade", "breakthrough", "levelCurve", "breakthroughs", "potentials", "formula", "suit"):
            self.add_gameplay_progression_node(node, entry_id, label, entry.get(label))
        if kind == "equipment":
            self.add_gameplay_equipment_semantics(node, entry_id, entry)

        for index, skill in enumerate(entry.get("skills") or []):
            if isinstance(skill, dict):
                self.add_gameplay_skill(node, skill, edge_kind="has_weapon_skill", owner_key=entry_id, index=index)

        for index, group in enumerate(entry.get("skillGroups") or []):
            if not isinstance(group, dict):
                continue
            group_id = safe_key(group.get("id") or f"group_{index}")
            group_node = self.add_node(
                "gameplay_skill_group",
                f"{entry_id}:{group_id}",
                name=group.get("name") or group_id,
                source="webui/gameplay",
                data={
                    "id": group.get("id"),
                    "type": group.get("type"),
                    "typeLabel": group.get("typeLabel"),
                    "name": group.get("name"),
                    "description": compact_text(group.get("description"), 500),
                    "actionSkillIds": group.get("actionSkillIds"),
                    "levelUp": self.gameplay_progression_summary(group.get("levelUp")),
                },
            )
            self.add_edge(node, group_node, "has_skill_group", source="webui/gameplay")
            self.add_alias(group.get("id"), group_node, kind="gameplay_skill_group_id", source="webui/gameplay")
            self.add_alias(group.get("name"), group_node, kind="gameplay_skill_group_name", source="webui/gameplay")
            self.add_gameplay_required_items(group_node, group.get("levelUp"), evidence="skillGroup.levelUp")
            for skill_index, skill in enumerate(group.get("skills") or []):
                if isinstance(skill, dict):
                    self.add_gameplay_skill(group_node, skill, edge_kind="has_action_skill", owner_key=f"{entry_id}:{group_id}", index=skill_index)

        for index, group in enumerate(entry.get("talentGroups") or []):
            if isinstance(group, dict):
                self.add_gameplay_talent_group(node, entry_id, group, index)
        if not entry.get("talentGroups"):
            for index, talent in enumerate(entry.get("talents") or []):
                if isinstance(talent, dict):
                    self.add_gameplay_talent(node, f"{entry_id}:talents", talent, index)

    def add_gameplay_equipment_semantics(self, equipment_node: str, equipment_id: str, entry: dict[str, Any]) -> None:
        domain = entry.get("domain") if isinstance(entry.get("domain"), dict) else {}
        domain_id = safe_key(entry.get("domainId") or domain.get("id"))
        if domain_id:
            domain_node = self.add_node(
                "gameplay_domain",
                domain_id,
                name=entry.get("domainName") or domain.get("name") or domain_id,
                source="webui/gameplay",
                data={
                    "id": domain_id,
                    "name": entry.get("domainName") or domain.get("name"),
                    "storageName": domain.get("storageName"),
                    "equipmentCountEvidence": "edge_count",
                },
            )
            self.add_edge(equipment_node, domain_node, "uses_gameplay_domain", source="webui/gameplay", evidence="domainId")
            self.add_alias(domain_id, domain_node, kind="gameplay_domain_id", source="webui/gameplay")
            self.add_alias(entry.get("domainName") or domain.get("name"), domain_node, kind="gameplay_domain_name", source="webui/gameplay")
            self.add_gameplay_source_edges(domain_node, {"table": "DomainDataTable.json", "id": domain_id})

        suit = entry.get("suit") if isinstance(entry.get("suit"), dict) else {}
        suit_id = safe_key(entry.get("suitId") or suit.get("id"))
        if suit_id:
            suit_node = self.add_node(
                "equipment_suit",
                suit_id,
                name=suit.get("name") or suit_id,
                source="webui/gameplay",
                data={
                    "id": suit_id,
                    "name": suit.get("name"),
                    "effectCount": len(suit.get("effects") or []),
                },
            )
            self.add_edge(equipment_node, suit_node, "has_equipment_suit", source="webui/gameplay", evidence="suitId")
            self.add_alias(suit_id, suit_node, kind="equipment_suit_id", source="webui/gameplay")
            self.add_alias(suit.get("name"), suit_node, kind="equipment_suit_name", source="webui/gameplay")
            self.add_gameplay_source_edges(suit_node, {"table": "EquipSuitTable.json", "id": suit_id})

        formula = entry.get("formula") if isinstance(entry.get("formula"), dict) else {}
        formula_id = safe_key(formula.get("formulaId"))
        if formula_id:
            formula_node = self.add_node(
                "equipment_formula",
                formula_id,
                name=formula.get("formulaName") or formula.get("name") or formula_id,
                source="webui/gameplay",
                data={
                    "id": formula_id,
                    "name": formula.get("formulaName") or formula.get("name"),
                    "outcomeEquipId": formula.get("outcomeEquipId"),
                    "outcomeEquipName": formula.get("outcomeEquipName"),
                    "packId": formula.get("packId"),
                    "packName": formula.get("packName"),
                    "unlockType": formula.get("unlockType"),
                    "unlockKey": formula.get("unlockKey"),
                    "unlockName": formula.get("unlockName"),
                    "costCount": len(formula.get("costs") or []),
                },
            )
            self.add_edge(equipment_node, formula_node, "crafted_by_formula", source="webui/gameplay", evidence="formulaId")
            self.add_edge(formula_node, equipment_node, "formula_outputs_equipment", source="webui/gameplay", evidence="outcomeEquipId")
            self.add_alias(formula_id, formula_node, kind="equipment_formula_id", source="webui/gameplay")
            self.add_alias(formula.get("formulaName") or formula.get("name"), formula_node, kind="equipment_formula_name", source="webui/gameplay")
            self.add_alias(formula.get("outcomeEquipId"), formula_node, kind="equipment_formula_outcome_id", source="webui/gameplay")
            self.add_gameplay_source_edges(formula_node, {"table": "EquipFormulaTable.json", "id": formula_id})
            self.add_gameplay_required_items(formula_node, formula, evidence="equipmentFormula")

            pack_id = safe_key(formula.get("packId"))
            if pack_id:
                pack_node = self.add_node(
                    "equipment_formula_pack",
                    pack_id,
                    name=formula.get("packName") or pack_id,
                    source="webui/gameplay",
                    data={"id": pack_id, "name": formula.get("packName")},
                )
                self.add_edge(formula_node, pack_node, "belongs_to_formula_pack", source="webui/gameplay", evidence="packId")
                self.add_alias(pack_id, pack_node, kind="equipment_formula_pack_id", source="webui/gameplay")
                self.add_alias(formula.get("packName"), pack_node, kind="equipment_formula_pack_name", source="webui/gameplay")
                self.add_gameplay_source_edges(pack_node, {"table": "EquipPackTable.json", "id": pack_id})

            unlock_key = safe_key(formula.get("unlockKey"))
            if unlock_key:
                unlock_node = self.add_node(
                    "gameplay_unlock",
                    unlock_key,
                    name=formula.get("unlockName") or unlock_key,
                    source="webui/gameplay",
                    data={
                        "id": unlock_key,
                        "name": formula.get("unlockName"),
                        "unlockType": formula.get("unlockType"),
                        "unlockValue": formula.get("unlockValue"),
                    },
                )
                self.add_edge(formula_node, unlock_node, "unlocked_by", source="webui/gameplay", evidence="unlockKey")
                self.add_alias(unlock_key, unlock_node, kind="gameplay_unlock_id", source="webui/gameplay")
                self.add_alias(formula.get("unlockName"), unlock_node, kind="gameplay_unlock_name", source="webui/gameplay")

        stats = entry.get("stats") if isinstance(entry.get("stats"), dict) else {}
        for index, curve in enumerate(stats.get("propertyCurves") or []):
            if isinstance(curve, dict):
                self.add_gameplay_property_curve(equipment_node, equipment_id, curve, index)

    def add_gameplay_property_curve(self, equipment_node: str, equipment_id: str, curve: dict[str, Any], index: int) -> str:
        attr_index = safe_key(curve.get("attrIndex"))
        key = safe_key(curve.get("key") or curve.get("compositeAttr") or attr_index or f"property_{index}")
        curve_key = f"{equipment_id}:{attr_index or index}:{key}"
        node = self.add_node(
            "gameplay_property_curve",
            curve_key,
            name=curve.get("label") or key,
            source="webui/gameplay",
            data={
                "equipmentId": equipment_id,
                "attrIndex": curve.get("attrIndex"),
                "key": curve.get("key"),
                "label": curve.get("label"),
                "iconName": curve.get("iconName"),
                "compositeAttr": curve.get("compositeAttr"),
                "rowCount": curve.get("rowCount"),
                "maxLevel": curve.get("maxLevel"),
            },
        )
        self.add_edge(equipment_node, node, "has_equipment_property_curve", source="webui/gameplay", evidence=attr_index or str(index))
        self.add_alias(key, node, kind="gameplay_property_curve_key", source="webui/gameplay")
        self.add_alias(curve.get("label"), node, kind="gameplay_property_curve_label", source="webui/gameplay")

        stat_node = self.add_node(
            "gameplay_stat_property",
            key,
            name=curve.get("label") or key,
            source="webui/gameplay",
            data={"key": key, "label": curve.get("label"), "iconName": curve.get("iconName"), "compositeAttr": curve.get("compositeAttr")},
        )
        self.add_edge(node, stat_node, "scales_stat_property", source="webui/gameplay", evidence=key)
        self.add_alias(key, stat_node, kind="gameplay_stat_property_key", source="webui/gameplay")
        self.add_alias(curve.get("label"), stat_node, kind="gameplay_stat_property_name", source="webui/gameplay")
        return node

    def add_gameplay_asset_entity_edges(self, owner_node: str, entry: dict[str, Any]) -> None:
        if safe_key(entry.get("kind")) != "weapon":
            return
        model_path = safe_key(entry.get("modelPath"))
        if not model_path:
            return
        model_stem = Path(model_path).stem.lower()
        if not model_stem:
            return
        seen_entities: set[str] = set()
        for model_base, entity_nodes in sorted(self.asset_entities_by_base.items()):
            if model_base != model_stem and not model_base.startswith(f"{model_stem}_"):
                continue
            for entity_node in entity_nodes:
                if entity_node in seen_entities:
                    continue
                seen_entities.add(entity_node)
                self.add_edge(
                    owner_node,
                    entity_node,
                    "has_gameplay_asset_entity",
                    source="webui/gameplay",
                    evidence="modelPath",
                    data={
                        "modelPath": model_path,
                        "token": model_stem,
                        "modelBase": model_base,
                        "assetEntity": node_key(entity_node),
                    },
                )

    def add_gameplay_asset_edges(self, owner_node: str, entry: dict[str, Any]) -> None:
        tokens: list[tuple[str, str]] = []
        entry_id = safe_key(entry.get("id"))
        kind = safe_key(entry.get("kind"))
        if kind in {"weapon", "character"} and entry_id:
            tokens.append(("id", entry_id))
        icon_id = safe_key(entry.get("iconId"))
        if icon_id:
            tokens.append(("iconId", icon_id))
        model_path = safe_key(entry.get("modelPath"))
        if model_path:
            model_stem = Path(model_path).stem
            if model_stem:
                tokens.append(("modelPath", model_stem))

        seen_tokens: set[str] = set()
        for field, token in tokens:
            token_lower = token.lower()
            if not token_lower or token_lower in seen_tokens:
                continue
            seen_tokens.add(token_lower)
            for rel in self.asset_paths:
                if token_lower not in rel.lower():
                    continue
                asset_node = self.add_node("asset", rel, name=Path(rel).name, path=rel)
                self.add_edge(
                    owner_node,
                    asset_node,
                    "has_gameplay_asset",
                    source="webui/gameplay",
                    evidence=field,
                    data={"token": token},
                )

    def add_gameplay_source_edges(self, owner_node: str, source: Any, *, edge_kind: str = "defined_by_row") -> None:
        if not isinstance(source, dict):
            return
        row_id = safe_key(source.get("id"))
        if not row_id:
            return
        for key, kind in (("table", edge_kind), ("nameTable", "named_by_row")):
            table_name = safe_key(source.get(key))
            if not table_name:
                continue
            table_key = Path(table_name).stem
            table_node = self.add_node("table", table_key, name=table_key, source="webui/gameplay")
            row_node = self.add_node("table_row", f"{table_key}:{row_id}", name=row_id, source=table_key)
            self.add_edge(table_node, row_node, "has_row", source="webui/gameplay")
            self.add_edge(owner_node, row_node, kind, source="webui/gameplay", evidence=table_name)

    def gameplay_progression_summary(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            out = {
                key: payload.get(key)
                for key in (
                    "source",
                    "templateId",
                    "rowCount",
                    "rawRowCount",
                    "maxLevel",
                    "rawMaxLevel",
                    "playableMaxLevel",
                    "extraRowsBeyondPlayable",
                )
                if payload.get(key) not in (None, "", [], {})
            }
            for key in ("rows", "checkpoints", "levels", "costs", "requiredItem", "displayAttrs", "propertyCurves"):
                if isinstance(payload.get(key), list):
                    out[f"{key}Count"] = len(payload[key])
            return out
        if isinstance(payload, list):
            return {"count": len(payload), "preview": compact_payload(payload[:2], depth=2, list_limit=4)}
        return {}

    def add_gameplay_progression_node(self, owner_node: str, owner_key: str, label: str, payload: Any) -> str:
        if payload in (None, "", [], {}):
            return ""
        data = self.gameplay_progression_summary(payload)
        if not data:
            data = compact_payload(payload, depth=2, list_limit=6)
        node = self.add_node(
            "gameplay_progression",
            f"{owner_key}:{label}",
            name=f"{owner_key} {label}",
            source="webui/gameplay",
            data=data,
        )
        self.add_edge(owner_node, node, "has_gameplay_progression", source="webui/gameplay", evidence=label)
        self.add_gameplay_required_items(node, payload, evidence=label)
        return node

    def add_gameplay_skill(self, owner_node: str, skill: dict[str, Any], *, edge_kind: str, owner_key: str, index: int) -> str:
        skill_id = safe_key(skill.get("id") or f"skill_{index}")
        node = self.add_node(
            "gameplay_skill",
            skill_id,
            name=skill.get("name") or skill_id,
            source="webui/gameplay",
            data={
                "id": skill.get("id"),
                "name": skill.get("name"),
                "description": compact_text(skill.get("description"), 500),
                "maxDescription": compact_text(skill.get("maxDescription"), 500),
                "levelCount": skill.get("levelCount"),
                "source": skill.get("source"),
            },
        )
        self.add_edge(owner_node, node, edge_kind, source="webui/gameplay", evidence=str(index))
        self.add_alias(skill.get("id"), node, kind="gameplay_skill_id", source="webui/gameplay")
        self.add_alias(skill.get("name"), node, kind="gameplay_skill_name", source="webui/gameplay")
        self.add_gameplay_source_edges(node, skill.get("source"))
        self.add_gameplay_required_items(node, skill, evidence="skill")
        return node

    def add_gameplay_talent_group(self, owner_node: str, owner_key: str, group: dict[str, Any], index: int) -> str:
        group_id = safe_key(group.get("id") or f"talent_group_{index}")
        node = self.add_node(
            "gameplay_talent_group",
            f"{owner_key}:{group_id}",
            name=group.get("title") or group_id,
            source="webui/gameplay",
            data={
                "id": group.get("id"),
                "kind": group.get("kind"),
                "kindLabel": group.get("kindLabel"),
                "rank": group.get("rank"),
                "rankIndex": group.get("rankIndex"),
                "title": group.get("title"),
                "levelCount": len(group.get("levels") or []),
            },
        )
        self.add_edge(owner_node, node, "has_talent_group", source="webui/gameplay", evidence=str(index))
        self.add_alias(group.get("id"), node, kind="gameplay_talent_group_id", source="webui/gameplay")
        self.add_alias(group.get("title"), node, kind="gameplay_talent_group_name", source="webui/gameplay")
        for level_index, level in enumerate(group.get("levels") or []):
            if isinstance(level, dict):
                self.add_gameplay_talent(node, f"{owner_key}:{group_id}", level, level_index)
        return node

    def add_gameplay_talent(self, owner_node: str, owner_key: str, talent: dict[str, Any], index: int) -> str:
        talent_id = safe_key(talent.get("id") or f"talent_{index}")
        node = self.add_node(
            "gameplay_talent",
            f"{owner_key}:{talent_id}:{index}",
            name=talent.get("title") or talent_id,
            source="webui/gameplay",
            data={
                "id": talent.get("id"),
                "nodeType": talent.get("nodeType"),
                "typeLabel": talent.get("typeLabel"),
                "kind": talent.get("kind"),
                "kindLabel": talent.get("kindLabel"),
                "title": talent.get("title"),
                "description": compact_text(talent.get("description"), 500),
                "level": talent.get("level"),
                "rank": talent.get("rank"),
                "breakStage": talent.get("breakStage"),
                "source": talent.get("source"),
            },
        )
        self.add_edge(owner_node, node, "has_talent", source="webui/gameplay", evidence=str(index))
        self.add_alias(talent.get("id"), node, kind="gameplay_talent_id", source="webui/gameplay")
        self.add_alias(talent.get("title"), node, kind="gameplay_talent_name", source="webui/gameplay")
        self.add_gameplay_source_edges(node, talent.get("source"))
        self.add_gameplay_required_items(node, talent, evidence="talent")
        return node

    def add_gameplay_required_items(self, owner_node: str, payload: Any, *, evidence: str, depth: int = 4) -> None:
        if depth <= 0 or payload in (None, "", [], {}):
            return
        if isinstance(payload, dict):
            for key in ("costs", "requiredItem", "requiredItems", "itemBundle", "items"):
                self.add_gameplay_item_edges(owner_node, payload.get(key), evidence=f"{evidence}.{key}")
            self.add_gameplay_gold_edge(owner_node, payload.get("goldCost"), evidence=f"{evidence}.goldCost")
            for key in ("rows", "checkpoints", "levels", "potentials", "breakthroughs", "formula", "suit", "propertyCurves"):
                self.add_gameplay_required_items(owner_node, payload.get(key), evidence=f"{evidence}.{key}", depth=depth - 1)
        elif isinstance(payload, list):
            for item in payload:
                self.add_gameplay_required_items(owner_node, item, evidence=evidence, depth=depth - 1)

    def add_gameplay_gold_edge(self, owner_node: str, value: Any, *, evidence: str) -> None:
        if not isinstance(value, (int, float)) or value <= 0:
            return
        item_node = self.add_node(
            "item",
            "item_gold",
            name="item_gold",
            source="webui/gameplay",
            data={"id": "item_gold", "name": "item_gold"},
        )
        self.add_edge(owner_node, item_node, "requires_item", source="webui/gameplay", evidence=evidence, data={"count": value})
        self.add_alias("item_gold", item_node, kind="item_id", source="webui/gameplay")

    def add_gameplay_item_edges(self, owner_node: str, items: Any, *, evidence: str) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = safe_key(item.get("id") or item.get("itemId"))
            if not item_id:
                continue
            count = item.get("count")
            if isinstance(count, (int, float)) and count <= 0:
                continue
            item_node = self.add_node(
                "item",
                item_id,
                name=item.get("name") or item_id,
                source="webui/gameplay",
                data={"id": item_id, "name": item.get("name"), "count": count},
            )
            self.add_edge(owner_node, item_node, "requires_item", source="webui/gameplay", evidence=evidence, data={"count": count})
            self.add_alias(item_id, item_node, kind="item_id", source="webui/gameplay")
            self.add_alias(item.get("name"), item_node, kind="item_name", source="webui/gameplay")

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
                    "candidateLineIdsByOption": branch_risk.get("candidateLineIdsByOption"),
                    "candidateMapping": branch_risk.get("candidateMapping"),
                    "candidateLineClipOptionIndex": branch_risk.get("candidateLineClipOptionIndex"),
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
            raw_candidate_lines_by_option = branch_risk.get("candidateLineIdsByOption") or {}

            def normalize_candidate_line_ids(value: Any) -> list[str]:
                if isinstance(value, list):
                    return [safe_key(line_id) for line_id in value if safe_key(line_id)]
                line_id = safe_key(value)
                return [line_id] if line_id else []

            candidate_lines_by_option = {
                safe_key(option_id): normalize_candidate_line_ids(line_ids)
                for option_id, line_ids in raw_candidate_lines_by_option.items()
                if safe_key(option_id) and normalize_candidate_line_ids(line_ids)
            } if isinstance(raw_candidate_lines_by_option, dict) else {}
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
                        "candidateMapping": branch_risk.get("candidateMapping"),
                        "candidateLineClipOptionIndex": branch_risk.get("candidateLineClipOptionIndex"),
                    }
                    if option_id in branch_lines_by_option:
                        hint["branchLineIds"] = branch_lines_by_option[option_id]
                    if option_id in skipped_lines_by_option:
                        hint["skippedLineIds"] = skipped_lines_by_option[option_id]
                    if continuation_option_ids:
                        hint["continuationOptionIds"] = continuation_option_ids
                    if option_id in candidate_lines_by_option:
                        hint["candidateLineIds"] = candidate_lines_by_option[option_id]
                        hint["candidateLineId"] = candidate_lines_by_option[option_id][0]
                        if option_id not in branch_lines_by_option and len(candidate_lines_by_option[option_id]) > 1:
                            hint["branchLineIds"] = candidate_lines_by_option[option_id]
                    elif index < len(candidate_line_ids):
                        hint["candidateLineId"] = candidate_line_ids[index]
                    if common_line_id:
                        hint["commonContinuationLineId"] = common_line_id
                    hint = {key: value for key, value in hint.items() if value not in (None, "", [], {})}
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

    def add_recovery_warnings(self, conv: dict[str, Any], story_node: str) -> None:
        story_key = safe_key(conv.get("key"))
        if not story_key:
            return
        for warning_index, warning in enumerate(conv.get("warnings") or []):
            if not isinstance(warning, dict):
                continue
            code = safe_key(warning.get("code")) or "warning"
            warning_node = self.add_node(
                "story_recovery_warning",
                f"{story_key}:{warning_index}:{code}",
                name=code,
                source="webui/recovery",
                data=compact_payload(warning, depth=5, list_limit=80),
            )
            self.add_edge(story_node, warning_node, "has_recovery_warning", source="webui/recovery", evidence=code)

            for group_warning in warning.get("groups") or []:
                if not isinstance(group_warning, dict):
                    continue
                group_key = safe_key(group_warning.get("group"))
                if group_key:
                    group_node = self.add_node(
                        "option_group",
                        self.timeline_group_key(story_key, group_key),
                        source="webui/recovery",
                    )
                    self.add_edge(
                        warning_node,
                        group_node,
                        "warning_option_group",
                        source="webui/recovery",
                        evidence=group_key,
                        data=compact_payload(group_warning, depth=2, list_limit=12),
                    )
                for option_id in group_warning.get("optionIds") or []:
                    option_key = safe_key(option_id)
                    if option_key:
                        option_node = self.add_node("option", option_key, source="webui/recovery")
                        self.add_edge(warning_node, option_node, "warning_option", source="webui/recovery", evidence=code)
                for line_id in group_warning.get("candidateLineIds") or []:
                    line_key = safe_key(line_id)
                    if line_key:
                        line_node = self.add_node("line", line_key, source="webui/recovery")
                        self.add_edge(warning_node, line_node, "warning_candidate_line", source="webui/recovery", evidence=code)
                common_line_id = safe_key(group_warning.get("commonContinuationLineId"))
                if common_line_id:
                    line_node = self.add_node("line", common_line_id, source="webui/recovery")
                    self.add_edge(warning_node, line_node, "warning_continuation_line", source="webui/recovery", evidence=code)
                for asset_track in group_warning.get("assetTracks") or []:
                    asset_track_key = safe_key(asset_track)
                    if asset_track_key:
                        file_node = self.add_file(asset_track_key, kind="recovery_warning_source", source="webui/recovery")
                        self.add_edge(warning_node, file_node, "warning_source_file", source="webui/recovery", evidence=code)

            for option_id in warning.get("optionIds") or []:
                option_key = safe_key(option_id)
                if option_key:
                    option_node = self.add_node("option", option_key, source="webui/recovery")
                    self.add_edge(warning_node, option_node, "warning_option", source="webui/recovery", evidence=code)
            for line_id in warning.get("lineIds") or []:
                line_key = safe_key(line_id)
                if line_key:
                    line_node = self.add_node("line", line_key, source="webui/recovery")
                    self.add_edge(warning_node, line_node, "warning_candidate_line", source="webui/recovery", evidence=code)

    def ingest_timeline_line_orders(self) -> None:
        path = self.export_root / TIMELINE_LINE_ORDERS_REL
        payload = read_json(path, {})
        if not isinstance(payload, dict) or not payload:
            return
        meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
        dataset = self.add_node(
            "dataset",
            "timeline_line_orders",
            name="Timeline line/order recovery",
            source="AnimeStudio/timeline",
            path=slash(path),
            data=meta,
        )
        self.add_file(slash(path), kind="timeline_line_orders", source="AnimeStudio/timeline", data=meta)

        for raw_key, entry in payload.items():
            if raw_key.startswith("_") or not isinstance(entry, dict):
                continue
            story_key = safe_key(entry.get("dialogKey") or raw_key)
            if not story_key:
                continue
            story_node = self.add_node("story", story_key, source="timeline_line_orders")
            timeline_key = safe_key(entry.get("timeline") or f"{story_key}:timeline")
            timeline_node = self.add_node(
                "timeline",
                timeline_key,
                name=timeline_key,
                source="timeline_line_orders",
                path=safe_key(entry.get("source")),
                data={
                    "dialogKey": story_key,
                    "lineCount": len(entry.get("lines") or entry.get("lineIds") or []),
                    "optionCount": len(entry.get("options") or entry.get("optionIds") or []),
                    "optionRouteCount": len(entry.get("optionRoutes") or {}),
                    "trackCount": entry.get("trackCount"),
                    "duplicateClipCount": entry.get("duplicateClipCount"),
                    "duplicateOptionClipCount": entry.get("duplicateOptionClipCount"),
                    "source": entry.get("source"),
                    "sourceRoots": compact_payload(entry.get("sourceRoots") or [], depth=1, list_limit=6),
                },
            )
            self.add_alias(timeline_key.lower(), timeline_node, kind="timeline_name", source="timeline_line_orders")
            self.add_edge(dataset, timeline_node, "has_timeline", source="timeline_line_orders")
            self.add_edge(story_node, timeline_node, "has_timeline_recovery", source="timeline_line_orders")
            self.add_edge(timeline_node, story_node, "timeline_targets_story", source="timeline_line_orders")
            for source_root in entry.get("sourceRoots") or []:
                file_node = self.add_file(source_root, kind="timeline_source_json", source="timeline_line_orders")
                self.add_edge(timeline_node, file_node, "timeline_source_file", source="timeline_line_orders")

            for line_index, line in enumerate(entry.get("lines") or []):
                if not isinstance(line, dict):
                    continue
                line_id = safe_key(line.get("id"))
                if not line_id:
                    continue
                line_node = self.add_node(
                    "line",
                    line_id,
                    name=line_id,
                    source="timeline_line_orders",
                    data=self.timeline_clip_payload(line, story_key, line_index),
                )
                clip_data = self.timeline_clip_payload(line, story_key, line_index)
                self.add_edge(
                    timeline_node,
                    line_node,
                    "timeline_line_clip",
                    source="timeline_line_orders",
                    evidence=str(line_index),
                    data=clip_data,
                )
                self.add_edge(
                    story_node,
                    line_node,
                    "has_timeline_line",
                    source="timeline_line_orders",
                    evidence=str(line_index),
                    data=clip_data,
                )
                self.add_timeline_clip_files(line_node, line, prefix="timeline_line")

            for option_index, option in enumerate(entry.get("options") or []):
                if not isinstance(option, dict):
                    continue
                self.ingest_timeline_option_clip(
                    story_node=story_node,
                    timeline_node=timeline_node,
                    story_key=story_key,
                    option=option,
                    option_index=option_index,
                )

            option_routes = entry.get("optionRoutes") or {}
            if isinstance(option_routes, dict):
                for option_id, route in option_routes.items():
                    if isinstance(route, dict):
                        self.ingest_timeline_option_route(
                            timeline_node=timeline_node,
                            story_key=story_key,
                            option_id=safe_key(option_id),
                            route=route,
                        )

    def timeline_clip_payload(self, clip: dict[str, Any], story_key: str, index: int) -> dict[str, Any]:
        data = {
            "dialogKey": story_key,
            "index": index,
            "timeline": clip.get("timeline"),
            "start": clip.get("start"),
            "duration": clip.get("duration"),
            "trackName": clip.get("trackName"),
            "trackPathId": clip.get("trackPathId"),
            "track": clip.get("track"),
            "sourceFile": clip.get("sourceFile"),
            "lineIdSource": clip.get("lineIdSource"),
            "assetName": clip.get("assetName"),
            "assetPathId": clip.get("assetPathId"),
            "assetTrack": clip.get("assetTrack"),
            "groupKey": clip.get("groupKey"),
            "optionIndex": clip.get("optionIndex"),
            "clipOptionIndex": clip.get("clipOptionIndex"),
            "anchorMode": clip.get("anchorMode"),
            "anchorLineId": clip.get("anchorLineId"),
            "trunkId": clip.get("trunkId"),
            "dialogId": clip.get("dialogId"),
            "logicId": clip.get("logicId"),
            "selectedFlag": clip.get("selectedFlag"),
            "setGreyed": clip.get("setGreyed"),
            "main": clip.get("main"),
            "isChat": clip.get("isChat"),
            "changeFinishNum": clip.get("changeFinishNum"),
            "targetFinishNum": clip.get("targetFinishNum"),
            "useExOptionColor": clip.get("useExOptionColor"),
            "overrideOptionIcon": clip.get("overrideOptionIcon"),
            "overrideOptionIconType": clip.get("overrideOptionIconType"),
            "conditionRid": clip.get("conditionRid"),
        }
        return {key: value for key, value in data.items() if value not in (None, "", [], {})}

    def add_timeline_clip_files(self, owner_node: str, clip: dict[str, Any], *, prefix: str) -> None:
        track = safe_key(clip.get("track"))
        if track:
            track_file = self.add_file(
                track,
                kind=f"{prefix}_track_json",
                source="timeline_line_orders",
                data={"trackName": clip.get("trackName"), "trackPathId": clip.get("trackPathId")},
            )
            self.add_edge(
                owner_node,
                track_file,
                f"{prefix}_track_file",
                source="timeline_line_orders",
                evidence=safe_key(clip.get("trackName")),
            )
        asset_track = safe_key(clip.get("assetTrack"))
        if asset_track:
            asset_file = self.add_file(
                asset_track,
                kind=f"{prefix}_asset_json",
                source="timeline_line_orders",
                data={"assetName": clip.get("assetName"), "assetPathId": clip.get("assetPathId")},
            )
            self.add_edge(
                owner_node,
                asset_file,
                f"{prefix}_asset_file",
                source="timeline_line_orders",
                evidence=safe_key(clip.get("assetName")),
            )

    def timeline_group_key(self, story_key: str, group_key: Any) -> str:
        return f"{story_key}#optionGroup:{safe_key(group_key)}"

    def timeline_group_index(self, group_key: Any) -> Any:
        group_text = safe_key(group_key)
        return int(group_text) if group_text.isdigit() else group_text

    def ingest_timeline_option_clip(
        self,
        *,
        story_node: str,
        timeline_node: str,
        story_key: str,
        option: dict[str, Any],
        option_index: int,
    ) -> None:
        option_id = safe_key(option.get("id"))
        if not option_id:
            return
        clip_data = self.timeline_clip_payload(option, story_key, option_index)
        option_node = self.add_node(
            "option",
            option_id,
            name=option_id,
            source="timeline_line_orders",
            data={"index": option.get("optionIndex"), "groupKey": option.get("groupKey"), "timeline": option.get("timeline")},
        )
        self.add_edge(
            timeline_node,
            option_node,
            "timeline_option_clip",
            source="timeline_line_orders",
            evidence=str(option_index),
            data=clip_data,
        )
        group_key = safe_key(option.get("groupKey"))
        if group_key:
            group_node = self.add_node(
                "option_group",
                self.timeline_group_key(story_key, group_key),
                source="timeline_line_orders",
                data={"g": group_key, "index": self.timeline_group_index(group_key), "after": option.get("anchorLineId")},
            )
            self.add_edge(story_node, group_node, "has_option_group", source="timeline_line_orders", evidence=group_key)
            self.add_edge(timeline_node, group_node, "timeline_has_option_group", source="timeline_line_orders", evidence=group_key)
            self.add_edge(
                group_node,
                option_node,
                "has_option",
                source="timeline_line_orders",
                evidence=safe_key(option.get("optionIndex") if option.get("optionIndex") is not None else option_index),
            )
        anchor_line_id = safe_key(option.get("anchorLineId"))
        if anchor_line_id:
            line_node = self.add_node("line", anchor_line_id, source="timeline_line_orders")
            self.add_edge(
                option_node,
                line_node,
                "timeline_option_anchor_line",
                source="timeline_line_orders",
                evidence=safe_key(option.get("anchorMode")),
                data=clip_data,
            )
            if group_key:
                self.add_edge(group_node, line_node, "anchored_after_line", source="timeline_line_orders", data=clip_data)
        self.add_timeline_clip_files(option_node, option, prefix="timeline_option")

    def timeline_route_payload(self, story_key: str, option_id: str, route: dict[str, Any]) -> dict[str, Any]:
        return {
            "dialogKey": story_key,
            "optionId": option_id,
            "source": route.get("source"),
            "groupKey": route.get("groupKey"),
            "optionIndex": route.get("optionIndex"),
            "start": route.get("start"),
            "end": route.get("end"),
            "pathLineIds": route.get("pathLineIds") or [],
            "skippedLineIds": route.get("skippedLineIds") or [],
            "skipRangeCount": len(route.get("skipRanges") or []),
            "continuationGroupKey": route.get("continuationGroupKey"),
            "continuationOptionIds": route.get("continuationOptionIds") or [],
        }

    def ingest_timeline_option_route(
        self,
        *,
        timeline_node: str,
        story_key: str,
        option_id: str,
        route: dict[str, Any],
    ) -> None:
        if not option_id:
            return
        option_node = self.add_node("option", option_id, name=option_id, source="timeline_line_orders")
        route_key = f"{story_key}:{option_id}"
        route_data = self.timeline_route_payload(story_key, option_id, route)
        route_node = self.add_node(
            "timeline_option_route",
            route_key,
            name=option_id,
            source="timeline_line_orders",
            data=route_data,
        )
        evidence = ":".join(
            safe_key(value)
            for value in (route.get("source"), route.get("groupKey"), route.get("optionIndex"))
            if safe_key(value)
        )
        self.add_edge(option_node, route_node, "has_timeline_route", source="timeline_line_orders", evidence=evidence, data=route_data)
        self.add_edge(timeline_node, route_node, "timeline_has_option_route", source="timeline_line_orders", evidence=option_id)

        for line_index, line_id in enumerate(route.get("pathLineIds") or []):
            line_key = safe_key(line_id)
            if not line_key:
                continue
            line_node = self.add_node("line", line_key, source="timeline_line_orders")
            edge_data = {
                "dialogKey": story_key,
                "optionId": option_id,
                "routeSource": route.get("source"),
                "groupKey": route.get("groupKey"),
                "optionIndex": route.get("optionIndex"),
                "order": line_index,
                "start": route.get("start"),
                "end": route.get("end"),
            }
            self.add_edge(route_node, line_node, "timeline_route_path_line", source="timeline_line_orders", evidence=str(line_index), data=edge_data)
            self.add_edge(option_node, line_node, "timeline_route_path_line", source="timeline_line_orders", evidence=str(line_index), data=edge_data)
            if line_index == 0:
                self.add_edge(option_node, line_node, "timeline_route_first_line", source="timeline_line_orders", evidence=evidence, data=edge_data)

        for line_index, line_id in enumerate(route.get("skippedLineIds") or []):
            line_key = safe_key(line_id)
            if not line_key:
                continue
            line_node = self.add_node("line", line_key, source="timeline_line_orders")
            edge_data = {
                "dialogKey": story_key,
                "optionId": option_id,
                "routeSource": route.get("source"),
                "groupKey": route.get("groupKey"),
                "optionIndex": route.get("optionIndex"),
                "skippedOrder": line_index,
                "start": route.get("start"),
                "end": route.get("end"),
            }
            self.add_edge(route_node, line_node, "timeline_route_skips_line", source="timeline_line_orders", evidence=str(line_index), data=edge_data)
            self.add_edge(option_node, line_node, "timeline_route_skips_line", source="timeline_line_orders", evidence=str(line_index), data=edge_data)

        for continuation_index, continuation_id in enumerate(route.get("continuationOptionIds") or []):
            continuation_key = safe_key(continuation_id)
            if not continuation_key:
                continue
            continuation_node = self.add_node("option", continuation_key, source="timeline_line_orders")
            edge_data = {
                "dialogKey": story_key,
                "optionId": option_id,
                "continuationGroupKey": route.get("continuationGroupKey"),
                "order": continuation_index,
            }
            self.add_edge(
                route_node,
                continuation_node,
                "timeline_route_continues_to_option",
                source="timeline_line_orders",
                evidence=str(continuation_index),
                data=edge_data,
            )
            self.add_edge(
                option_node,
                continuation_node,
                "timeline_route_continues_to_option",
                source="timeline_line_orders",
                evidence=str(continuation_index),
                data=edge_data,
            )

        for jump_index, jump in enumerate(route.get("skipRanges") or []):
            if isinstance(jump, dict):
                self.ingest_runtime_jump_clip(
                    option_node=option_node,
                    route_node=route_node,
                    story_key=story_key,
                    option_id=option_id,
                    route=route,
                    jump=jump,
                    jump_index=jump_index,
                )

    def ingest_runtime_jump_clip(
        self,
        *,
        option_node: str,
        route_node: str,
        story_key: str,
        option_id: str,
        route: dict[str, Any],
        jump: dict[str, Any],
        jump_index: int,
    ) -> None:
        jump_key = safe_key(jump.get("assetTrack") or jump.get("track"))
        if not jump_key:
            jump_key = f"{story_key}:{option_id}:runtimeJump:{jump_index}:{jump.get('start')}:{jump.get('end')}"
        jump_data = {
            "dialogKey": story_key,
            "optionId": option_id,
            "routeSource": route.get("source"),
            "groupKey": route.get("groupKey"),
            "optionIndex": route.get("optionIndex"),
            "start": jump.get("start"),
            "end": jump.get("end"),
            "duration": jump.get("duration"),
            "trackName": jump.get("trackName"),
            "displayName": jump.get("displayName"),
            "track": jump.get("track"),
            "assetTrack": jump.get("assetTrack"),
        }
        jump_node = self.add_node(
            "runtime_jump_clip",
            jump_key,
            name=Path(jump_key).stem,
            source="timeline_line_orders",
            path=safe_key(jump.get("assetTrack") or jump.get("track")),
            data=jump_data,
        )
        self.add_edge(route_node, jump_node, "route_uses_runtime_jump", source="timeline_line_orders", evidence=str(jump_index), data=jump_data)
        self.add_edge(option_node, jump_node, "timeline_route_runtime_jump", source="timeline_line_orders", evidence=str(jump_index), data=jump_data)
        self.add_timeline_clip_files(jump_node, jump, prefix="runtime_jump")

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
        dataset = self.add_node("dataset", f"reference_{self.language}", name=f"Text Tables {self.language}", path=slash(ref_root))
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
                "includeGameplay": self.include_gameplay,
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
    "option_override": 3,
    "line": 4,
    "timeline": 5,
    "timeline_option_route": 6,
    "runtime_jump_clip": 7,
    "mission": 8,
    "character": 9,
    "weapon": 10,
    "equipment": 11,
    "equipment_formula": 12,
    "equipment_formula_pack": 13,
    "equipment_suit": 14,
    "gameplay_domain": 15,
    "gameplay_property_curve": 16,
    "gameplay_stat_property": 17,
    "gameplay_unlock": 18,
    "item": 19,
    "gameplay_skill_group": 20,
    "gameplay_skill": 21,
    "gameplay_talent_group": 22,
    "gameplay_talent": 23,
    "gameplay_progression": 24,
    "asset_entity": 25,
    "asset": 26,
    "actor": 27,
    "audio": 28,
    "file": 29,
}

NODE_ID_PREFIXES = (
    "story",
    "option_group",
    "option",
    "option_override",
    "line",
    "mission",
    "character",
    "weapon",
    "equipment",
    "equipment_formula",
    "equipment_formula_pack",
    "equipment_suit",
    "gameplay_domain",
    "gameplay_property_curve",
    "gameplay_stat_property",
    "gameplay_unlock",
    "item",
    "gameplay_skill_group",
    "gameplay_skill",
    "gameplay_talent_group",
    "gameplay_talent",
    "gameplay_progression",
    "asset_entity",
    "asset",
    "actor",
    "audio",
    "video",
    "timeline",
    "timeline_option_route",
    "runtime_jump_clip",
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
    "has_timeline_route",
    "timeline_option_anchor_line",
    "timeline_route_first_line",
    "timeline_route_path_line",
    "timeline_route_skips_line",
    "timeline_route_continues_to_option",
    "timeline_route_runtime_jump",
)

ISSUE_EVIDENCE_EDGE_KINDS = (
    "option_first_line",
    "option_path_line",
    "option_merge_line",
    "has_timeline_route",
    "timeline_option_anchor_line",
    "timeline_option_clip",
    "timeline_route_first_line",
    "timeline_route_path_line",
    "timeline_route_skips_line",
    "timeline_route_continues_to_option",
    "timeline_route_runtime_jump",
)
ASSET_USED_BY_INCOMING_EDGE_KINDS = (
    "has_gameplay_asset",
    "has_gameplay_asset_entity",
    "previewed_by",
    "uses_material",
    "uses_texture_pathid",
    "entity_has_lod_model",
    "entity_uses_material",
    "entity_uses_texture",
)
ASSET_USED_BY_OUTGOING_EDGE_KINDS = (
    "referenced_by_material",
    "referenced_by_model",
)
ASSET_USES_EDGE_KINDS = (
    "has_gameplay_asset_entity",
    "previewed_by",
    "uses_material",
    "uses_texture",
    "uses_texture_pathid",
    "entity_has_lod_model",
    "entity_uses_material",
    "entity_uses_texture",
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
            WHEN 'character_id' THEN 2
            WHEN 'weapon_id' THEN 3
            WHEN 'equipment_id' THEN 4
            WHEN 'equipment_formula_id' THEN 5
            WHEN 'equipment_suit_id' THEN 6
            WHEN 'gameplay_domain_id' THEN 7
            WHEN 'gameplay_stat_property_key' THEN 8
            WHEN 'item_id' THEN 9
            WHEN 'gameplay_skill_id' THEN 10
            WHEN 'asset_entity_id' THEN 11
            ELSE 19
          END,
          CASE nodes.kind
            WHEN 'story' THEN 0
            WHEN 'option' THEN 1
            WHEN 'line' THEN 2
            WHEN 'character' THEN 3
            WHEN 'weapon' THEN 4
            WHEN 'equipment' THEN 5
            WHEN 'equipment_formula' THEN 6
            WHEN 'equipment_suit' THEN 7
            WHEN 'gameplay_domain' THEN 8
            WHEN 'gameplay_stat_property' THEN 9
            WHEN 'item' THEN 10
            WHEN 'asset_entity' THEN 11
            WHEN 'asset' THEN 12
            ELSE 19
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


def usage_node_ref(row: sqlite3.Row, side: str) -> dict[str, Any]:
    data = parse_json_text(row[f"{side}Data"])
    ref: dict[str, Any] = {
        "id": row[f"{side}Id"],
        "key": node_key(row[f"{side}Id"]),
        "kind": row[f"{side}Kind"],
        "name": row[f"{side}Name"],
    }
    if row[f"{side}Path"]:
        ref["path"] = row[f"{side}Path"]
    if isinstance(data, dict):
        for key in (
            "type",
            "size",
            "preview",
            "pid",
            "category",
            "materialLike",
            "modelBase",
            "lodModelCount",
            "materialCount",
            "textureCount",
        ):
            value = data.get(key)
            if value not in (None, "", [], {}):
                ref[key] = value
    return ref


def usage_edge_ref(row: sqlite3.Row, actor_side: str, seed: str) -> dict[str, Any]:
    ref = usage_node_ref(row, actor_side)
    ref["edge"] = row["edge"]
    ref["direction"] = "incoming" if row["dstId"] == seed else "outgoing"
    if row["source"]:
        ref["source"] = row["source"]
    if row["evidence"]:
        ref["evidence"] = row["evidence"]
    edge_data = parse_json_text(row["edgeData"])
    if edge_data:
        ref["edgeData"] = edge_data
    return ref


def asset_usage(db_path: Path, term: str, *, limit: int = 40, kind: str = "asset") -> dict[str, Any]:
    lookup = query_graph(db_path, term, limit=min(max(limit, 1), 20), kind=kind)
    seed = safe_key(lookup.get("seedNode"))
    if not seed:
        return {"term": term, "seedNode": "", "matches": lookup.get("nodes") or [], "usedBy": [], "uses": []}

    incoming_placeholders = ",".join("?" for _ in ASSET_USED_BY_INCOMING_EDGE_KINDS)
    outgoing_placeholders = ",".join("?" for _ in ASSET_USED_BY_OUTGOING_EDGE_KINDS)
    uses_placeholders = ",".join("?" for _ in ASSET_USES_EDGE_KINDS)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        seed_row = conn.execute(
            "SELECT id, kind, name, source, path, data FROM nodes WHERE id = ?",
            (seed,),
        ).fetchone()
        used_by_rows = conn.execute(
            f"""
            SELECT e.kind AS edge, e.source, e.evidence, e.data AS edgeData,
                   src.id AS srcId, src.kind AS srcKind, src.name AS srcName, src.path AS srcPath, src.data AS srcData,
                   dst.id AS dstId, dst.kind AS dstKind, dst.name AS dstName, dst.path AS dstPath, dst.data AS dstData
            FROM edges e
            JOIN nodes src ON src.id = e.src
            JOIN nodes dst ON dst.id = e.dst
            WHERE (e.kind IN ({incoming_placeholders}) AND e.dst = ?)
               OR (e.kind IN ({outgoing_placeholders}) AND e.src = ?)
            ORDER BY e.kind, src.kind, src.name, dst.kind, dst.name, e.evidence
            LIMIT ?
            """,
            (*ASSET_USED_BY_INCOMING_EDGE_KINDS, seed, *ASSET_USED_BY_OUTGOING_EDGE_KINDS, seed, limit),
        ).fetchall()
        uses_rows = conn.execute(
            f"""
            SELECT e.kind AS edge, e.source, e.evidence, e.data AS edgeData,
                   src.id AS srcId, src.kind AS srcKind, src.name AS srcName, src.path AS srcPath, src.data AS srcData,
                   dst.id AS dstId, dst.kind AS dstKind, dst.name AS dstName, dst.path AS dstPath, dst.data AS dstData
            FROM edges e
            JOIN nodes src ON src.id = e.src
            JOIN nodes dst ON dst.id = e.dst
            WHERE e.kind IN ({uses_placeholders})
              AND e.src = ?
            ORDER BY e.kind, dst.kind, dst.name, e.evidence
            LIMIT ?
            """,
            (*ASSET_USES_EDGE_KINDS, seed, limit),
        ).fetchall()

    return {
        "term": term,
        "seedNode": seed,
        "seed": compact_node_ref(seed_row) if seed_row else {"id": seed, "key": node_key(seed)},
        "aliases": lookup.get("aliases") or [],
        "usedBy": [
            usage_edge_ref(row, "src" if row["dstId"] == seed else "dst", seed)
            for row in used_by_rows
        ],
        "uses": [usage_edge_ref(row, "dst", seed) for row in uses_rows],
    }


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
        for key in (
            "actor",
            "actorId",
            "audio",
            "text",
            "timestamp",
            "duration",
            "modelBase",
            "lodModelCount",
            "materialCount",
            "textureCount",
        ):
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


def annotate_option_branch_precedence(branches: dict[str, list[dict[str, Any]]]) -> None:
    manual_first_lines = {
        safe_key(ref.get("key"))
        for ref in branches.get("option_first_line", [])
        if ref.get("source") == "webui/option_override" and safe_key(ref.get("key"))
    }
    inferred_first_lines = {
        safe_key(ref.get("key"))
        for ref in branches.get("option_first_line", [])
        if ref.get("source") != "webui/option_override" and safe_key(ref.get("key"))
    }
    for edge_kind, refs in branches.items():
        for ref in refs:
            source = safe_key(ref.get("source"))
            if source == "webui/option_override":
                ref["precedence"] = "manual_authoritative"
                ref["webuiOnly"] = True
                if edge_kind == "option_first_line":
                    if not inferred_first_lines:
                        ref["classification"] = "manual_only"
                    elif safe_key(ref.get("key")) in inferred_first_lines:
                        ref["classification"] = "manual_matches_inference"
                    else:
                        ref["classification"] = "manual_conflicts_inference"
                        ref["inferredFirstLineIds"] = sorted(inferred_first_lines)
            elif edge_kind.startswith("option_") or edge_kind.startswith("timeline_"):
                if source == "timeline_route_branch":
                    ref["precedence"] = "runtime_route_evidence"
                    match_label = "runtime_route_matches_manual"
                    conflict_label = "runtime_route_conflicts_manual"
                elif source == "timeline_line_orders":
                    ref["precedence"] = "runtime_timeline_evidence"
                    match_label = "runtime_timeline_matches_manual"
                    conflict_label = "runtime_timeline_conflicts_manual"
                else:
                    ref["precedence"] = "diagnostic_inference"
                    match_label = "inference_matches_manual"
                    conflict_label = "inference_conflicts_manual"
                if edge_kind == "option_first_line" and manual_first_lines:
                    if safe_key(ref.get("key")) in manual_first_lines:
                        ref["classification"] = match_label
                    else:
                        ref["classification"] = conflict_label
                        ref["manualFirstLineIds"] = sorted(manual_first_lines)

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

        warning_rows = conn.execute(
            """
            SELECT edge.evidence, edge.source, edge.data AS edgeData,
                   warning.id, warning.kind, warning.name, warning.source AS nodeSource, warning.path, warning.data
            FROM edges edge
            JOIN nodes warning ON warning.id = edge.dst
            WHERE edge.src = ? AND edge.kind = 'has_recovery_warning'
            ORDER BY edge.id
            """,
            (seed,),
        ).fetchall()
        warnings = []
        for row in warning_rows:
            warning_data = parse_json_text(row["data"])
            warnings.append({
                "id": row["id"],
                "key": node_key(row["id"]),
                "code": warning_data.get("code") or row["name"],
                "reason": warning_data.get("reason"),
                "detail": warning_data.get("detail"),
                "groups": warning_data.get("groups") or [],
                "optionIds": warning_data.get("optionIds") or [],
                "lineIds": warning_data.get("lineIds") or [],
                "source": row["source"],
            })

        timeline_rows = conn.execute(
            """
            SELECT edge.source AS edgeSource, edge.evidence, edge.data AS edgeData,
                   timeline.id, timeline.kind, timeline.name, timeline.source AS nodeSource, timeline.path, timeline.data AS timelineData
            FROM edges edge
            JOIN nodes timeline ON timeline.id = edge.dst
            WHERE edge.src = ? AND edge.kind = 'has_timeline_recovery'
            ORDER BY timeline.name
            """,
            (seed,),
        ).fetchall()
        timeline_refs = []
        timeline_lines = []
        for timeline_row in timeline_rows:
            timeline_ref = compact_node_ref(
                {
                    "id": timeline_row["id"],
                    "kind": timeline_row["kind"],
                    "name": timeline_row["name"],
                    "path": timeline_row["path"],
                    "data": timeline_row["timelineData"],
                }
            )
            if timeline_row["edgeSource"]:
                timeline_ref["source"] = timeline_row["edgeSource"]
            timeline_refs.append(timeline_ref)

            clip_rows = conn.execute(
                """
                SELECT edge.evidence, edge.source, edge.data,
                       line.id, line.kind, line.name, line.source AS nodeSource, line.path, line.data AS lineData
                FROM edges edge
                JOIN nodes line ON line.id = edge.dst
                WHERE edge.src = ? AND edge.kind = 'timeline_line_clip'
                ORDER BY CAST(edge.evidence AS INTEGER), edge.id
                """,
                (timeline_row["id"],),
            ).fetchall()
            for clip_row in clip_rows:
                line_ref = compact_node_ref(
                    {
                        "id": clip_row["id"],
                        "kind": clip_row["kind"],
                        "name": clip_row["name"],
                        "path": clip_row["path"],
                        "data": clip_row["lineData"],
                    },
                    clip_row,
                )
                line_ref["timeline"] = timeline_row["name"]
                line_ref["order"] = int(clip_row["evidence"]) if safe_key(clip_row["evidence"]).isdigit() else len(timeline_lines)
                timeline_lines.append(line_ref)
        if limit_lines > 0:
            timeline_lines = timeline_lines[:limit_lines]

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
            SELECT group_node.id, group_node.kind, group_node.name, group_node.source, group_node.path, group_node.data,
                   MIN(edge.id) AS firstEdgeId
            FROM edges edge
            JOIN nodes group_node ON group_node.id = edge.dst
            WHERE edge.src = ? AND edge.kind = 'has_option_group'
            GROUP BY group_node.id, group_node.kind, group_node.name, group_node.source, group_node.path, group_node.data
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
                SELECT option_node.id, option_node.kind, option_node.name, option_node.source, option_node.path, option_node.data,
                       MIN(edge.id) AS firstEdgeId
                FROM edges edge
                JOIN nodes option_node ON option_node.id = edge.dst
                WHERE edge.src = ? AND edge.kind = 'has_option'
                GROUP BY option_node.id, option_node.kind, option_node.name, option_node.source, option_node.path, option_node.data
                ORDER BY firstEdgeId
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
                annotate_option_branch_precedence(option["branches"])
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
            "warnings": warnings,
            "timelineRecovery": {
                "timelines": timeline_refs,
                "lines": timeline_lines,
            },
            "optionGroups": groups,
        }


def recovery_issues(db_path: Path, *, code: str = "", limit: int = 40) -> dict[str, Any]:
    edge_placeholders = ",".join("?" for _ in ISSUE_EVIDENCE_EDGE_KINDS)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        total_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM edges edge
            JOIN nodes warning ON warning.id = edge.dst
            WHERE edge.kind = 'has_recovery_warning'
              AND (? = '' OR warning.name = ?)
            """,
            (code, code),
        ).fetchone()[0]
        rows = conn.execute(
            """
            SELECT story.id AS storyNode, story.name AS storyKey, story.data AS storyData,
                   warning.id AS warningNode, warning.name AS warningCode, warning.data AS warningData
            FROM edges edge
            JOIN nodes story ON story.id = edge.src
            JOIN nodes warning ON warning.id = edge.dst
            WHERE edge.kind = 'has_recovery_warning'
              AND (? = '' OR warning.name = ?)
            ORDER BY story.name, warning.name
            LIMIT ?
            """,
            (code, code, limit),
        ).fetchall()
        issues = []
        for row in rows:
            story_data = parse_json_text(row["storyData"])
            warning_data = parse_json_text(row["warningData"])
            option_ids = _unique_preserve([
                safe_key(option_id)
                for option_id in warning_data.get("optionIds") or []
                if safe_key(option_id)
            ])
            line_ids = _unique_preserve([
                safe_key(line_id)
                for line_id in warning_data.get("lineIds") or []
                if safe_key(line_id)
            ])
            group_ids: list[Any] = []
            for group in warning_data.get("groups") or []:
                if not isinstance(group, dict):
                    continue
                group_ids.append(group.get("group"))
                for option_id in group.get("optionIds") or []:
                    option_key = safe_key(option_id)
                    if option_key and option_key not in option_ids:
                        option_ids.append(option_key)
                for line_id in group.get("candidateLineIds") or []:
                    line_key = safe_key(line_id)
                    if line_key and line_key not in line_ids:
                        line_ids.append(line_key)
                common_line = safe_key(group.get("commonContinuationLineId"))
                if common_line and common_line not in line_ids:
                    line_ids.append(common_line)

            evidence_counts: Counter[str] = Counter()
            evidence_samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for option_id in option_ids:
                option_node = f"option:{option_id}"
                evidence_rows = conn.execute(
                    f"""
                    SELECT edge.kind, edge.source, edge.evidence,
                           src.id AS srcId, src.kind AS srcKind, src.name AS srcName,
                           dst.id AS dstId, dst.kind AS dstKind, dst.name AS dstName
                    FROM edges edge
                    JOIN nodes src ON src.id = edge.src
                    JOIN nodes dst ON dst.id = edge.dst
                    WHERE (edge.src = ? OR edge.dst = ?)
                      AND edge.kind IN ({edge_placeholders})
                    ORDER BY edge.kind, edge.id
                    """,
                    (option_node, option_node, *ISSUE_EVIDENCE_EDGE_KINDS),
                ).fetchall()
                for evidence_row in evidence_rows:
                    edge_kind = evidence_row["kind"]
                    evidence_counts[edge_kind] += 1
                    samples = evidence_samples[edge_kind]
                    if len(samples) < 5:
                        if evidence_row["srcId"] == option_node:
                            target_id = evidence_row["dstId"]
                            target_kind = evidence_row["dstKind"]
                        else:
                            target_id = evidence_row["srcId"]
                            target_kind = evidence_row["srcKind"]
                        samples.append({
                            "optionId": option_id,
                            "target": node_key(target_id),
                            "targetKind": target_kind,
                            "source": evidence_row["source"],
                            "evidence": evidence_row["evidence"],
                        })

            timeline_count = conn.execute(
                "SELECT COUNT(*) FROM edges WHERE src = ? AND kind = 'has_timeline_recovery'",
                (row["storyNode"],),
            ).fetchone()[0]
            issues.append({
                "storyKey": row["storyKey"],
                "mission": story_data.get("mission"),
                "kind": story_data.get("kind"),
                "warning": warning_data.get("code") or row["warningCode"],
                "reason": warning_data.get("reason"),
                "groupIds": group_ids,
                "optionIds": option_ids,
                "lineIds": line_ids,
                "timelineRecoveryCount": timeline_count,
                "evidenceCounts": dict(evidence_counts),
                "evidenceSamples": dict(evidence_samples),
            })
        return {
            "code": code,
            "totalCount": total_count,
            "returned": len(issues),
            "issues": issues,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    build = sub.add_parser("build", help="Build the SQLite source graph")
    build.add_argument("--db", type=Path, default=DEFAULT_DB)
    build.add_argument("--language", default="CN")
    build.add_argument("--skip-gameplay", action="store_true")
    build.add_argument("--skip-asset-maps", action="store_true")
    build.add_argument("--skip-reference-rows", action="store_true")
    build.add_argument("--include-all-material-json", action="store_true")
    build.add_argument("--skip-followups", action="store_true")

    query = sub.add_parser("query", help="Search graph nodes and show first-node neighbors")
    query.add_argument("term")
    query.add_argument("--db", type=Path, default=DEFAULT_DB)
    query.add_argument("--limit", type=int, default=40)
    query.add_argument("--kind", default="", help="Optional node kind filter, such as story, option, line, or audio.")

    used_by = sub.add_parser("used-by", help="Show what uses an asset/pathid plus direct asset dependencies")
    used_by.add_argument("term")
    used_by.add_argument("--db", type=Path, default=DEFAULT_DB)
    used_by.add_argument("--limit", type=int, default=40)
    used_by.add_argument("--kind", default="asset", help="Node kind to resolve before usage lookup; defaults to asset.")

    story = sub.add_parser("story", help="Show recovered line order and option branch evidence for one story key")
    story.add_argument("story_key")
    story.add_argument("--db", type=Path, default=DEFAULT_DB)
    story.add_argument("--limit-lines", type=int, default=0, help="Only include the first N ordered lines; 0 includes all.")

    issues = sub.add_parser("issues", help="List WebUI recovery warnings with nearby graph evidence")
    issues.add_argument("--db", type=Path, default=DEFAULT_DB)
    issues.add_argument("--code", default="", help="Optional warning code filter, such as inferredOptionResponse.")
    issues.add_argument("--limit", type=int, default=40)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command in (None, "build"):
        builder = SourceGraphBuilder(
            db_path=args.db if hasattr(args, "db") else DEFAULT_DB,
            language=getattr(args, "language", "CN"),
            include_gameplay=not getattr(args, "skip_gameplay", False),
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
    if args.command == "used-by":
        result = asset_usage(args.db, args.term, limit=args.limit, kind=args.kind)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "story":
        result = story_arrangement(args.db, args.story_key, limit_lines=args.limit_lines)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "issues":
        result = recovery_issues(args.db, code=args.code, limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
