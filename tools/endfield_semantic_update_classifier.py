#!/usr/bin/env python3
"""Classify Endfield update-feed entries by semantic area.

The tool reads the WebUI update feed plus the local source graph SQLite
database, then emits a compact JSON/Markdown report. It intentionally stays
stdlib-only so it can run in the same environment as the existing recovery
tools.
"""

from __future__ import annotations

import argparse
import datetime as dt
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
DEFAULT_UPDATES = ROOT / "webui" / "data" / "updates" / "latest.json"
DEFAULT_OUT_DIR = GRAPH_DIR / "update_classification"

BUCKETS = (
    "story/dialog",
    "audio",
    "character",
    "map/level",
    "asset/image/model/material",
    "shader",
    "video",
    "table/reference",
    "unknown",
)

STORY_KEY_RE = re.compile(
    r"\b(?:dlg|radio|sns|cutscene|remotecomm|black|timeline|envtalk|responsive|prts|reading)_[A-Za-z0-9_]{2,160}",
    re.IGNORECASE,
)
MISSION_RE = re.compile(r"\b(?:main|sub|act|mission|quest|level|map|stage|zone)[_-]?[A-Za-z0-9]{2,80}", re.IGNORECASE)
AUDIO_ID_RE = re.compile(r"\bau_[A-Za-z0-9_]{2,160}\b", re.IGNORECASE)
ACTOR_ASSET_RE = re.compile(r"(?:^|[/\\])(?:S|T|M|A|AC)_actor_([A-Za-z0-9]+)", re.IGNORECASE)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".dds", ".tga", ".tif", ".tiff", ".ktx", ".exr", ".bmp"}
MODEL_EXTENSIONS = {".fbx", ".obj", ".glb", ".gltf", ".mesh", ".prefab", ".asset", ".anim", ".controller"}
MATERIAL_EXTENSIONS = {".mat", ".material"}
VIDEO_EXTENSIONS = {".usm", ".mp4", ".webm", ".mov", ".avi", ".mkv"}
AUDIO_EXTENSIONS = {".wem", ".pck", ".bnk", ".wav", ".ogg", ".mp3", ".flac"}
SHADER_EXTENSIONS = {".shader", ".glsl", ".glslfx", ".hlsl", ".cginc", ".compute"}

KIND_BUCKET = {
    "story": "story/dialog",
    "line": "story/dialog",
    "option": "story/dialog",
    "option_group": "story/dialog",
    "story_graph_source": "story/dialog",
    "audio": "audio",
    "audio_sequence": "audio",
    "actor": "character",
    "character": "character",
    "character_manifest": "character",
    "animation_clip": "character",
    "mission": "map/level",
    "level": "map/level",
    "map_mark": "map/level",
    "asset": "asset/image/model/material",
    "asset_container": "asset/image/model/material",
    "material": "asset/image/model/material",
    "mesh": "asset/image/model/material",
    "texture": "asset/image/model/material",
    "unity_asset": "asset/image/model/material",
    "unity_pathid": "asset/image/model/material",
    "shader": "shader",
    "video": "video",
    "dataset": "table/reference",
    "i18n_text": "table/reference",
    "language": "table/reference",
    "reference_row": "table/reference",
    "reference_table": "table/reference",
    "table": "table/reference",
    "table_row": "table/reference",
}

FILE_KIND_BUCKET = {
    "story_conv": "story/dialog",
    "source_json": "story/dialog",
    "text_asset_json": "story/dialog",
    "wem_path": "audio",
    "character_manifest": "character",
    "image": "asset/image/model/material",
    "material_json": "asset/image/model/material",
    "model": "asset/image/model/material",
    "video": "video",
    "structured_table": "table/reference",
}

ALIAS_KIND_BUCKET = {
    "story_key": "story/dialog",
    "actor_name": "character",
    "character_alias": "character",
    "asset_name": "asset/image/model/material",
    "asset_stem": "asset/image/model/material",
    "material_name": "asset/image/model/material",
    "unity_asset_name": "asset/image/model/material",
    "unity_pathid": "asset/image/model/material",
    "video_stem": "video",
}

EDGE_BUCKET = {
    "anchored_after_line": "story/dialog",
    "graph_fragment_targets_story": "story/dialog",
    "has_graph_source_file": "story/dialog",
    "has_line": "story/dialog",
    "has_narrative_video": "story/dialog",
    "has_option": "story/dialog",
    "has_option_group": "story/dialog",
    "has_story": "story/dialog",
    "has_story_entry": "story/dialog",
    "has_story_source_link": "story/dialog",
    "mentions_actor": "story/dialog",
    "option_anchor_after": "story/dialog",
    "option_branch_line": "story/dialog",
    "option_enters_story": "story/dialog",
    "option_first_line": "story/dialog",
    "option_merge_line": "story/dialog",
    "option_path_line": "story/dialog",
    "option_path_story": "story/dialog",
    "references_story": "story/dialog",
    "source_references_story": "story/dialog",
    "uses_audio": "audio",
    "audio_path": "audio",
    "defines_audio": "audio",
    "has_audio_sequence": "audio",
    "has_profile_voice": "audio",
    "speaker_channel": "audio",
    "spoken_by": "audio",
    "defines_character": "character",
    "has_actor_name": "character",
    "has_animation_clip": "character",
    "has_character_manifest": "character",
    "has_recovery_manifest": "character",
    "defines_map_mark": "map/level",
    "has_map_mark": "map/level",
    "has_mission_name": "map/level",
    "contains_unity_asset": "asset/image/model/material",
    "exported_as": "asset/image/model/material",
    "exported_file": "asset/image/model/material",
    "has_material": "asset/image/model/material",
    "indexes_asset": "asset/image/model/material",
    "indexes_unity_asset": "asset/image/model/material",
    "resolves_to_unity_asset": "asset/image/model/material",
    "uses_material": "asset/image/model/material",
    "uses_texture": "asset/image/model/material",
    "uses_texture_pathid": "asset/image/model/material",
    "uses_shader": "shader",
    "uses_shader_pathid": "shader",
    "indexes_video": "video",
    "has_i18n_text": "table/reference",
    "has_reference_row": "table/reference",
    "has_reference_table": "table/reference",
    "has_row": "table/reference",
    "has_table": "table/reference",
}


def slash(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def normalize_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compact_text(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def compact_value(value: Any, *, depth: int = 2, list_limit: int = 8) -> Any:
    if depth <= 0:
        if isinstance(value, dict):
            return f"dict[{len(value)}]"
        if isinstance(value, list):
            return f"list[{len(value)}]"
        return compact_text(value, 120) if isinstance(value, str) else value
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= list_limit:
                out["..."] = f"{len(value) - list_limit} more"
                break
            out[str(key)] = compact_value(item, depth=depth - 1, list_limit=list_limit)
        return out
    if isinstance(value, list):
        out = [compact_value(item, depth=depth - 1, list_limit=list_limit) for item in value[:list_limit]]
        if len(value) > list_limit:
            out.append(f"... {len(value) - list_limit} more")
        return out
    if isinstance(value, str):
        return compact_text(value)
    return value


def add_score(
    scores: Counter[str],
    evidence: list[dict[str, Any]],
    bucket: str,
    weight: float,
    reason: str,
    detail: Any,
) -> None:
    if bucket not in BUCKETS or bucket == "unknown":
        return
    scores[bucket] += weight
    evidence.append(
        {
            "bucket": bucket,
            "weight": round(weight, 3),
            "reason": reason,
            "detail": compact_value(detail, depth=1),
        }
    )


def path_candidates(entry: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for key in ("path", "asset_rel", "rel", "file", "sourcePath", "source", "dst", "name", "id"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(normalize_path(value))
    path = normalize_path(entry.get("path") or entry.get("asset_rel") or "")
    if path:
        candidates.append(path.strip("/"))
        parts = path.split("/")
        if len(parts) >= 3 and parts[1].lower() == "vfs":
            candidates.append("/".join(("raw_vfs", parts[0], "files", *parts[2:])))
        name = Path(path).name
        stem = Path(path).stem
        if name:
            candidates.append(name)
            candidates.append(name.lower())
        if stem:
            candidates.append(stem)
            candidates.append(stem.lower())
    out: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out


def semantic_tokens(entry: dict[str, Any]) -> set[str]:
    text = " ".join(str(value) for value in entry.values() if isinstance(value, (str, int, float)))
    tokens = set()
    for pattern in (STORY_KEY_RE, AUDIO_ID_RE, MISSION_RE):
        tokens.update(match.group(0) for match in pattern.finditer(text))
    actor_match = ACTOR_ASSET_RE.search(text)
    if actor_match:
        tokens.add(actor_match.group(1))
        tokens.add(f"actor_{actor_match.group(1)}")
    for token in re.split(r"[^A-Za-z0-9_:-]+", text):
        if 3 <= len(token) <= 120:
            lower = token.lower()
            if lower.startswith(("dlg_", "au_", "cs_", "m_actor", "s_actor", "t_actor")):
                tokens.add(token)
                tokens.add(lower)
    return tokens


def path_heuristics(entry: dict[str, Any], scores: Counter[str], evidence: list[dict[str, Any]]) -> None:
    path = normalize_path(entry.get("path") or entry.get("asset_rel") or entry.get("file") or "")
    lower = path.lower()
    suffix = Path(lower).suffix
    category = str(entry.get("category") or "").lower()
    domain = str(entry.get("domain") or "").lower()
    asset_kind = str(entry.get("asset_kind") or "").lower()

    if domain == "asset":
        add_score(scores, evidence, "asset/image/model/material", 0.35, "entry domain", {"domain": domain})
    if "story" in category or "dialog" in category:
        add_score(scores, evidence, "story/dialog", 0.45, "entry category", {"category": category})
    if "audio" in category or asset_kind == "audio":
        add_score(scores, evidence, "audio", 0.45, "entry category", {"category": category, "asset_kind": asset_kind})
    if "video" in category or asset_kind == "video":
        add_score(scores, evidence, "video", 0.55, "entry category", {"category": category, "asset_kind": asset_kind})
    if asset_kind in {"image", "model", "material", "asset"}:
        add_score(scores, evidence, "asset/image/model/material", 0.45, "asset kind", asset_kind)

    if suffix in AUDIO_EXTENSIONS or "/audio/" in lower or lower.startswith("audio/"):
        add_score(scores, evidence, "audio", 0.75, "path/extension", path)
    if suffix in VIDEO_EXTENSIONS or "/video/" in lower or lower.startswith("video/"):
        add_score(scores, evidence, "video", 0.75, "path/extension", path)
    if suffix in SHADER_EXTENSIONS or "shader" in lower:
        add_score(scores, evidence, "shader", 0.8, "path/extension", path)
    if suffix in IMAGE_EXTENSIONS or any(token in lower for token in ("texture", "/tex/", "/sprite/", "/icon/")):
        add_score(scores, evidence, "asset/image/model/material", 0.65, "path/extension", path)
    if suffix in MODEL_EXTENSIONS or any(token in lower for token in ("mesh", "model", "prefab", "animator", "animation")):
        add_score(scores, evidence, "asset/image/model/material", 0.6, "path/extension", path)
    if suffix in MATERIAL_EXTENSIONS or "material" in lower or "/mat/" in lower:
        add_score(scores, evidence, "asset/image/model/material", 0.65, "path/extension", path)
    if "/table/" in lower or "table" in category or "reference" in lower or "i18n" in lower:
        add_score(scores, evidence, "table/reference", 0.65, "path/category", {"path": path, "category": category})
    if STORY_KEY_RE.search(path) or any(token in lower for token in ("/story/", "/dialog/", "/dialogue/", "/narrative/")):
        add_score(scores, evidence, "story/dialog", 0.7, "story/dialog path token", path)
    if AUDIO_ID_RE.search(path):
        add_score(scores, evidence, "audio", 0.65, "audio id token", path)
    if ACTOR_ASSET_RE.search(path) or any(token in lower for token in ("/character/", "/characters/", "/actor/", "/avatar/")):
        add_score(scores, evidence, "character", 0.65, "character path token", path)
    if any(token in lower for token in ("/map/", "/level/", "/scene/", "/stage/", "/terrain/", "mapmark", "mission")):
        add_score(scores, evidence, "map/level", 0.55, "map/level path token", path)


def placeholders(count: int) -> str:
    return ",".join("?" for _ in range(count))


def fetch_graph_matches(conn: sqlite3.Connection | None, entry: dict[str, Any], limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if conn is None:
        return [], []

    candidates = path_candidates(entry)
    candidates.extend(semantic_tokens(entry))
    lower_candidates = [candidate.lower() for candidate in candidates]
    candidates.extend(lower_candidates)
    candidates = list(dict.fromkeys(candidate for candidate in candidates if candidate))

    node_ids: list[str] = []
    for candidate in candidates:
        normalized = normalize_path(candidate)
        if normalized:
            for prefix in ("file", "asset", "video", "story", "audio", "character", "mission", "level", "map_mark"):
                node_ids.append(f"{prefix}:{normalized}")

    aliases: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []

    if candidates:
        for chunk in chunked(candidates, 200):
            rows = conn.execute(
                f"""
                SELECT a.alias, a.kind AS aliasKind, a.source AS aliasSource,
                       n.id, n.kind, n.name, n.source, n.path
                FROM aliases a
                JOIN nodes n ON n.id = a.node_id
                WHERE a.alias IN ({placeholders(len(chunk))})
                ORDER BY a.kind, n.kind, n.name
                LIMIT ?
                """,
                (*chunk, limit),
            ).fetchall()
            aliases.extend(dict(row) for row in rows)
            if len(aliases) >= limit:
                break

        path_like_candidates = [candidate for candidate in candidates if "/" in candidate]
        for chunk in chunked(path_like_candidates, 200):
            rows = conn.execute(
                f"""
                SELECT path, kind, source, size
                FROM files
                WHERE path IN ({placeholders(len(chunk))})
                ORDER BY kind, path
                LIMIT ?
                """,
                (*chunk, limit),
            ).fetchall()
            files.extend(dict(row) for row in rows)
            if len(files) >= limit:
                break

    if node_ids:
        for chunk in chunked(list(dict.fromkeys(node_ids)), 200):
            rows = conn.execute(
                f"""
                SELECT id, kind, name, source, path
                FROM nodes
                WHERE id IN ({placeholders(len(chunk))})
                ORDER BY kind, name
                LIMIT ?
                """,
                (*chunk, limit),
            ).fetchall()
            nodes.extend(dict(row) for row in rows)
            if len(nodes) >= limit:
                break

    match_map: dict[str, dict[str, Any]] = {}
    for row in aliases:
        row["matchType"] = "alias"
        match_map[row["id"]] = row
    for row in files:
        node_id = f"file:{row['path']}"
        match_map[node_id] = {
            "matchType": "file",
            "id": node_id,
            "kind": "file",
            "fileKind": row.get("kind"),
            "name": Path(row["path"]).name,
            "source": row.get("source"),
            "path": row.get("path"),
        }
    for row in nodes:
        row["matchType"] = "node"
        match_map[row["id"]] = row

    matches = list(match_map.values())[:limit]
    node_match_ids = [match["id"] for match in matches if match.get("id")]
    edges: list[dict[str, Any]] = []
    if node_match_ids:
        for chunk in chunked(node_match_ids, 100):
            rows = conn.execute(
                f"""
                SELECT e.kind, e.source, e.evidence, e.src, e.dst,
                       src.kind AS srcKind, src.name AS srcName,
                       dst.kind AS dstKind, dst.name AS dstName, dst.path AS dstPath
                FROM edges e
                JOIN nodes src ON src.id = e.src
                JOIN nodes dst ON dst.id = e.dst
                WHERE e.src IN ({placeholders(len(chunk))})
                   OR e.dst IN ({placeholders(len(chunk))})
                ORDER BY e.kind, e.source
                LIMIT ?
                """,
                (*chunk, *chunk, limit),
            ).fetchall()
            edges.extend(dict(row) for row in rows)
            if len(edges) >= limit:
                break

    return matches, edges[:limit]


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def graph_heuristics(
    matches: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    scores: Counter[str],
    evidence: list[dict[str, Any]],
) -> None:
    for match in matches:
        kind = str(match.get("kind") or "")
        file_kind = str(match.get("fileKind") or "")
        alias_kind = str(match.get("aliasKind") or "")
        bucket = FILE_KIND_BUCKET.get(file_kind) or KIND_BUCKET.get(kind) or ALIAS_KIND_BUCKET.get(alias_kind)
        if bucket:
            add_score(
                scores,
                evidence,
                bucket,
                0.9 if match.get("matchType") in {"file", "node"} else 0.75,
                f"graph {match.get('matchType')}",
                {
                    "id": match.get("id"),
                    "kind": kind,
                    "fileKind": file_kind or None,
                    "aliasKind": alias_kind or None,
                    "name": match.get("name"),
                    "path": match.get("path"),
                },
            )
        lower_text = " ".join(
            str(match.get(key) or "").lower() for key in ("id", "name", "path", "source", "alias", "aliasKind")
        )
        if "shader" in lower_text:
            add_score(scores, evidence, "shader", 0.55, "graph text token", lower_text)
        if "video" in lower_text:
            add_score(scores, evidence, "video", 0.45, "graph text token", lower_text)
        if "audio" in lower_text or "wem" in lower_text:
            add_score(scores, evidence, "audio", 0.45, "graph text token", lower_text)

    seen_edge_kinds: set[str] = set()
    for edge in edges:
        edge_kind = str(edge.get("kind") or "")
        bucket = EDGE_BUCKET.get(edge_kind)
        if not bucket:
            continue
        key = f"{edge_kind}:{bucket}"
        if key in seen_edge_kinds:
            continue
        seen_edge_kinds.add(key)
        add_score(
            scores,
            evidence,
            bucket,
            0.3,
            "neighbor edge",
            {
                "edge": edge_kind,
                "source": edge.get("source"),
                "evidence": edge.get("evidence"),
                "srcKind": edge.get("srcKind"),
                "srcName": edge.get("srcName"),
                "dstKind": edge.get("dstKind"),
                "dstName": edge.get("dstName"),
                "dstPath": edge.get("dstPath"),
            },
        )


def choose_bucket(scores: Counter[str]) -> tuple[str, float, dict[str, float]]:
    if not scores:
        return "unknown", 0.0, {}
    ranked = scores.most_common()
    bucket, score = ranked[0]
    if score <= 0:
        return "unknown", 0.0, dict(scores)
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = max(0.0, score - runner_up)
    confidence = min(0.99, 0.35 + (score / (score + 1.2)) * 0.5 + min(margin, 1.0) * 0.14)
    return bucket, round(confidence, 3), {key: round(value, 3) for key, value in scores.items()}


def classify_entry(
    conn: sqlite3.Connection | None,
    entry: dict[str, Any],
    *,
    index: int,
    graph_limit: int,
) -> dict[str, Any]:
    scores: Counter[str] = Counter()
    evidence: list[dict[str, Any]] = []
    path_heuristics(entry, scores, evidence)
    matches, edges = fetch_graph_matches(conn, entry, graph_limit)
    graph_heuristics(matches, edges, scores, evidence)
    bucket, confidence, bucket_scores = choose_bucket(scores)
    return {
        "index": index,
        "status": entry.get("status"),
        "domain": entry.get("domain"),
        "category": entry.get("category"),
        "path": normalize_path(entry.get("path") or entry.get("asset_rel") or entry.get("file") or ""),
        "bucket": bucket,
        "confidence": confidence,
        "scores": bucket_scores,
        "evidence": sorted(evidence, key=lambda item: item.get("weight", 0), reverse=True)[:16],
        "graphMatches": [compact_value(match, depth=1) for match in matches[:12]],
        "graphEdges": [compact_value(edge, depth=1) for edge in edges[:12]],
        "entry": compact_value(entry, depth=2),
    }


def load_entries(updates: Any, limit: int | None) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    if not isinstance(updates, dict):
        return [], ["update feed is not a JSON object"]
    if updates.get("_error"):
        warnings.append(f"could not read update feed: {updates['_error']}")
    raw_entries = updates.get("entries") or []
    if not isinstance(raw_entries, list):
        return [], warnings + ["update feed entries field is not a list"]
    entries = [entry for entry in raw_entries if isinstance(entry, dict)]
    skipped = len(raw_entries) - len(entries)
    if skipped:
        warnings.append(f"skipped {skipped} non-object update entries")
    if limit is not None:
        entries = entries[: max(0, limit)]
    return entries, warnings


def classify_updates(db_path: Path, updates_path: Path, out_dir: Path, *, limit: int | None) -> dict[str, Any]:
    updates = read_json(updates_path)
    entries, warnings = load_entries(updates, limit)
    conn: sqlite3.Connection | None = None
    db_available = db_path.exists()
    if db_available:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    else:
        warnings.append(f"source graph database not found: {db_path}")

    started = time.time()
    try:
        classified = [
            classify_entry(conn, entry, index=index, graph_limit=36)
            for index, entry in enumerate(entries)
        ]
    finally:
        if conn is not None:
            conn.close()

    bucket_counts = Counter(item["bucket"] for item in classified)
    status_counts = Counter(str(item.get("status") or "unknown") for item in classified)
    domain_counts = Counter(str(item.get("domain") or "unknown") for item in classified)
    category_counts = Counter(str(item.get("category") or "unknown") for item in classified)
    total_confidence = sum(float(item.get("confidence") or 0.0) for item in classified)
    generated_at = dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
    payload = {
        "schemaVersion": 1,
        "generated": int(time.time()),
        "generatedAt": generated_at,
        "generatedBy": "tools/endfield_semantic_update_classifier.py",
        "durationSeconds": round(time.time() - started, 3),
        "source": slash(updates_path),
        "database": slash(db_path),
        "databaseAvailable": db_available,
        "limit": limit,
        "sourceTotals": updates.get("totals") if isinstance(updates, dict) else None,
        "sourceGeneratedAt": updates.get("generatedAt") if isinstance(updates, dict) else None,
        "sourceRoot": updates.get("sourceRoot") if isinstance(updates, dict) else None,
        "totalEntries": len(classified),
        "empty": len(classified) == 0,
        "warnings": warnings,
        "summary": {
            "byBucket": {bucket: bucket_counts.get(bucket, 0) for bucket in BUCKETS},
            "byStatus": dict(status_counts.most_common()),
            "byDomain": dict(domain_counts.most_common()),
            "byCategory": dict(category_counts.most_common()),
            "averageConfidence": round(total_confidence / len(classified), 3) if classified else 0.0,
        },
        "entries": classified,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "classified_updates.json", payload)
    (out_dir / "summary.md").write_text(render_markdown(payload), encoding="utf-8")
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Semantic Update Classification",
        "",
        f"- Generated: `{payload.get('generatedAt')}`",
        f"- Source feed: `{payload.get('source')}`",
        f"- Source graph DB: `{payload.get('database')}`",
        f"- DB available: `{payload.get('databaseAvailable')}`",
        f"- Classified entries: `{payload.get('totalEntries')}`",
        f"- Average confidence: `{payload.get('summary', {}).get('averageConfidence')}`",
        "",
    ]
    source_totals = payload.get("sourceTotals")
    if source_totals:
        lines.extend(["## Source Totals", ""])
        for key in ("added", "modified", "deleted", "changed"):
            if key in source_totals:
                lines.append(f"- {key}: `{source_totals.get(key)}`")
        lines.append("")

    warnings = payload.get("warnings") or []
    if warnings:
        lines.extend(["## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.extend(["## Buckets", ""])
    for bucket, count in (payload.get("summary", {}).get("byBucket") or {}).items():
        lines.append(f"- {bucket}: `{count}`")
    lines.append("")

    if payload.get("empty"):
        lines.extend(
            [
                "## Entries",
                "",
                "No update entries were present in the feed. The report is intentionally empty so downstream automation can still consume a stable shape.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(["## Examples", ""])
    examples_by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in payload.get("entries") or []:
        bucket = str(item.get("bucket") or "unknown")
        if len(examples_by_bucket[bucket]) < 5:
            examples_by_bucket[bucket].append(item)
    for bucket in BUCKETS:
        examples = examples_by_bucket.get(bucket) or []
        if not examples:
            continue
        lines.append(f"### {bucket}")
        lines.append("")
        for item in examples:
            lines.append(
                f"- `{item.get('status') or 'unknown'}` `{item.get('path') or '[no path]'}` "
                f"confidence `{item.get('confidence')}`"
            )
            for ev in (item.get("evidence") or [])[:3]:
                lines.append(
                    f"  - {ev.get('reason')}: `{ev.get('bucket')}` "
                    f"weight `{ev.get('weight')}`"
                )
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Source graph SQLite database.")
    parser.add_argument("--updates", type=Path, default=DEFAULT_UPDATES, help="WebUI update feed JSON.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Report output directory.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum update entries to classify.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = classify_updates(args.db, args.updates, args.out_dir, limit=args.limit)
    print(
        "Classified "
        f"{payload['totalEntries']} update entries into "
        f"{args.out_dir / 'classified_updates.json'}"
    )
    if payload.get("empty"):
        print("Update feed is empty; emitted an empty report with source totals and bucket schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
