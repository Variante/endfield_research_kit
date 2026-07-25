"""Build a bounded presentation/asset relationship graph for the static WebUI.

The source graph contains millions of low-level Unity records.  This builder
intentionally selects only authored presentation roots and useful exported
assets reachable through maintained source-graph edges.  It never traverses
generic ``unity_asset`` nodes.

Run from the repository root:
    python scripts/build_presentation_data.py
    python scripts/build_presentation_data.py --languages CN EN JP
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = ROOT / "webui" / "data" / "lang"
DEFAULT_GRAPH = ROOT / "reports" / "source_graph" / "endfield_source_graph.sqlite"
SCHEMA_VERSION = 1

INFERRED_EDGE_KINDS = {
    "effect_name_matches_export_base_asset",
    "model_config_asset_entity",
    "model_view_state_controller_asset_entity",
}

# Model rows are already compacted on their nodes. Repeating the same row on
# up to four source-variant edges adds megabytes without improving provenance.
EDGE_KINDS_WITH_NODE_REDUNDANT_RAW = {"model_config_has_model"}

ANIMATION_EDGE_CAPS = {
    "animation_config_references_state": 64,
    "animation_config_references_actor_animation": 32,
    "animation_config_references_facial_morph": 12,
    "animation_config_references_montage": 12,
    "animation_config_references_cutscene": 12,
    "animation_config_references_path": 12,
}
CONTROLLER_EDGE_CAPS = {
    "model_view_state_controller_uses_model": 1,
    "model_view_state_controller_asset_entity": 4,
    "model_view_state_controller_has_clip_asset": 16,
    "model_view_state_controller_animator_references_clip": 16,
    "model_view_state_controller_references_effect": 16,
    "model_view_state_controller_animator_references_effect": 16,
}
ENTITY_EDGE_CAPS = {
    "entity_has_lod_model": 3,
    "entity_uses_material": 8,
    "entity_uses_texture": 8,
}
MATERIAL_EDGE_CAPS = {
    "material_uses_shader_program": 2,
    "material_texture_pathid_exports_asset": 12,
    "uses_shader": 2,
    "uses_texture": 12,
}
MATERIAL_ASSET_EDGE_CAPS = {"uses_texture": 12}
EFFECT_EDGE_CAPS = {"effect_name_matches_export_base_asset": 4}
SHADER_PROGRAM_EDGE_CAPS = {"shader_program_named_shader": 1}

DISPLAY_KINDS = {
    "actor_animation_ref": "animation_clip_ref",
    "model_view_clip_ref": "animation_clip_ref",
    "level_script_montage": "animation_montage_ref",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--languages", nargs="+", default=["CN"])
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--max-model-assets", type=int, default=3)
    parser.add_argument("--max-materials", type=int, default=8)
    parser.add_argument("--max-textures", type=int, default=8)
    parser.add_argument("--max-material-textures", type=int, default=12)
    parser.add_argument("--max-effect-assets", type=int, default=4)
    return parser.parse_args()


def graph_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def compact(value: Any, *, depth: int = 3, width: int = 24) -> Any:
    """Keep useful evidence while preventing large raw records in the payload."""
    if depth <= 0:
        if isinstance(value, (dict, list)):
            return f"<{type(value).__name__}>"
        return value
    if isinstance(value, dict):
        keys = sorted(value, key=str)
        kept = {
            str(key): compact(value[key], depth=depth - 1, width=width)
            for key in keys[:width]
            if value[key] not in (None, "", [], {})
        }
        if len(keys) > width:
            kept["..."] = f"{len(keys) - width} more"
        return kept
    if isinstance(value, list):
        kept = [compact(item, depth=depth - 1, width=width) for item in value[:width]]
        if len(value) > width:
            kept.append(f"... {len(value) - width} more")
        return kept
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(encoded + "\n", encoding="utf-8", newline="\n")


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def asset_display_kind(path: str, data: Any) -> str:
    lowered = path.lower()
    suffix = Path(path).suffix.lower()
    if "/material/" in lowered and suffix == ".json":
        return "material_asset"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".tga", ".dds"}:
        return "texture_asset"
    if suffix in {".fbx", ".obj", ".gltf", ".glb"}:
        return "model_asset"
    if isinstance(data, dict):
        asset_type = str(data.get("type") or "").lower()
        if asset_type == "image":
            return "texture_asset"
        if asset_type == "model":
            return "model_asset"
    return "browser_asset"


def edge_sort_key(edge: dict[str, Any]) -> tuple[str, str, str, str, str]:
    evidence = edge.get("evidence") or {}
    return (
        str(edge.get("source", "")),
        str(edge.get("type", "")),
        str(edge.get("target", "")),
        str(evidence.get("source", "")),
        str(evidence.get("path", "")),
    )


class PresentationBuilder:
    def __init__(self, connection: sqlite3.Connection, language: str, caps: dict[str, int]) -> None:
        self.db = connection
        self.language = language
        self.caps = caps
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        self.roots: set[str] = set()
        self.omissions: dict[str, int] = defaultdict(int)
        self.omission_sources: dict[str, int] = defaultdict(int)

    def add_node(self, node_id: str) -> bool:
        if node_id in self.nodes:
            return True
        row = self.db.execute(
            "SELECT id, kind, name, source, path, data FROM nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        if row is None or row[1] in {"unity_asset", "unity_pathid"}:
            return False
        raw = graph_json(row[5])
        graph_kind = str(row[1])
        path = str(row[4] or "")
        display_kind = DISPLAY_KINDS.get(graph_kind, graph_kind)
        if graph_kind == "asset":
            display_kind = asset_display_kind(path, raw)
        node: dict[str, Any] = {
            "id": str(row[0]),
            "kind": display_kind,
            "label": str(row[2] or str(row[0]).split(":", 1)[-1]),
            "graphKind": graph_kind,
        }
        if row[3]:
            node["source"] = str(row[3])
        if path:
            node["path"] = path
        if graph_kind == "asset":
            node["browserAsset"] = True
            node["assetRel"] = path
            node["previewable"] = display_kind in {"texture_asset", "model_asset"}
        if raw not in (None, "", [], {}):
            node["raw"] = compact(raw)
        self.nodes[node_id] = node
        return True

    def add_edge_row(self, row: tuple[Any, ...]) -> bool:
        source, target, kind, evidence_source, evidence_path, raw_json = row
        source = str(source)
        target = str(target)
        kind = str(kind)
        if not self.add_node(source) or not self.add_node(target):
            return False
        evidence: dict[str, Any] = {"source": str(evidence_source or "source_graph")}
        if evidence_path:
            evidence["path"] = str(evidence_path)
        raw = graph_json(raw_json)
        if kind not in EDGE_KINDS_WITH_NODE_REDUNDANT_RAW and raw not in (None, "", [], {}):
            evidence["raw"] = compact(raw, depth=3)
        edge = {
            "source": source,
            "target": target,
            "type": kind,
            "confidence": "inferred" if kind in INFERRED_EDGE_KINDS else "direct",
            "evidence": evidence,
        }
        key = (source, target, kind, evidence["source"], str(evidence.get("path") or ""))
        self.edges[key] = edge
        return True

    def node_ids(self, kind: str, *, where: str = "", params: tuple[Any, ...] = ()) -> list[str]:
        query = "SELECT id FROM nodes WHERE kind = ?"
        if where:
            query += f" AND ({where})"
        query += " ORDER BY id"
        return [str(row[0]) for row in self.db.execute(query, (kind, *params))]

    def edge_rows(self, source: str, kind: str) -> list[tuple[Any, ...]]:
        return list(
            self.db.execute(
                "SELECT src, dst, kind, source, evidence, data FROM edges "
                "WHERE src = ? AND kind = ? ORDER BY dst, source, evidence",
                (source, kind),
            )
        )

    def add_capped_edges(self, sources: Iterable[str], edge_caps: dict[str, int]) -> set[str]:
        added_targets: set[str] = set()
        for source in sorted(set(sources)):
            for kind, configured_cap in edge_caps.items():
                cap = max(0, int(configured_cap))
                rows = self.edge_rows(source, kind)
                selected = rows[:cap]
                omitted = max(0, len(rows) - len(selected))
                if omitted:
                    self.omissions[kind] += omitted
                    self.omission_sources[kind] += 1
                for row in selected:
                    if self.add_edge_row(row):
                        added_targets.add(str(row[1]))
        return added_targets

    def add_all_edges(self, sources: Iterable[str], kinds: Iterable[str]) -> set[str]:
        return self.add_capped_edges(sources, {kind: 1_000_000 for kind in kinds})

    def build(self) -> dict[str, Any]:
        # Authored model/config roots.  Four source variants may define the same
        # model; retaining each direct edge exposes that provenance explicitly.
        model_configs = self.node_ids("model_config")
        model_models = self.node_ids("model_config_model")
        for node_id in [*model_configs, *model_models]:
            self.add_node(node_id)
        self.roots.update(model_models)
        self.add_all_edges(model_configs, ["model_config_has_model"])
        model_targets = self.add_all_edges(
            model_models,
            [
                "model_config_uses_prefab",
                "model_config_asset_entity",
                "model_config_used_by_model_view_state_controller",
            ],
        )

        controllers = self.node_ids("model_view_state_controller")
        for node_id in controllers:
            self.add_node(node_id)
        self.roots.update(controllers)
        controller_caps = dict(CONTROLLER_EDGE_CAPS)
        controller_caps["model_view_state_controller_asset_entity"] = self.caps["materials"]
        controller_targets = self.add_capped_edges(controllers, controller_caps)

        animation_configs = self.node_ids("animation_config")
        for node_id in animation_configs:
            self.add_node(node_id)
        self.roots.update(animation_configs)
        self.add_capped_edges(animation_configs, ANIMATION_EDGE_CAPS)

        # Only shader-backed semantic materials are useful presentation roots.
        material_roots = [
            str(row[0])
            for row in self.db.execute(
                "SELECT DISTINCT src FROM edges WHERE kind = 'material_uses_shader_program' ORDER BY src"
            )
        ]
        for node_id in material_roots:
            self.add_node(node_id)
        self.roots.update(material_roots)
        material_caps = dict(MATERIAL_EDGE_CAPS)
        material_caps["material_texture_pathid_exports_asset"] = self.caps["materialTextures"]
        material_targets = self.add_capped_edges(material_roots, material_caps)

        asset_entities = {
            node_id
            for node_id in model_targets | controller_targets
            if node_id.startswith("asset_entity:")
        }
        entity_caps = dict(ENTITY_EDGE_CAPS)
        entity_caps["entity_has_lod_model"] = self.caps["modelAssets"]
        entity_caps["entity_uses_material"] = self.caps["materials"]
        entity_caps["entity_uses_texture"] = self.caps["textures"]
        entity_targets = self.add_capped_edges(asset_entities, entity_caps)

        material_assets = {
            node_id
            for node_id in entity_targets | material_targets
            if self.nodes.get(node_id, {}).get("kind") == "material_asset"
        }
        material_asset_caps = dict(MATERIAL_ASSET_EDGE_CAPS)
        material_asset_caps["uses_texture"] = self.caps["materialTextures"]
        self.add_capped_edges(material_assets, material_asset_caps)

        # Effects are included only when a controller directly references them
        # or an exact normalized export basename provides a useful asset match.
        controller_effects = {
            node_id
            for node_id in controller_targets
            if node_id.startswith("gameplay_effect:")
        }
        matched_effects = [
            str(row[0])
            for row in self.db.execute(
                "SELECT DISTINCT src FROM edges WHERE kind = 'effect_name_matches_export_base_asset' ORDER BY src"
            )
        ]
        effects = sorted(controller_effects | set(matched_effects))
        for node_id in effects:
            self.add_node(node_id)
        self.roots.update(effects)
        effect_caps = dict(EFFECT_EDGE_CAPS)
        effect_caps["effect_name_matches_export_base_asset"] = self.caps["effectAssets"]
        self.add_capped_edges(effects, effect_caps)

        shader_programs = {
            node_id
            for node_id in material_targets
            if node_id.startswith("shader_program:")
        }
        self.add_capped_edges(shader_programs, SHADER_PROGRAM_EDGE_CAPS)

        nodes = sorted(self.nodes.values(), key=lambda node: (str(node["kind"]), str(node["id"])))
        edges = sorted(self.edges.values(), key=edge_sort_key)
        node_ids = {str(node["id"]) for node in nodes}
        roots = sorted(root for root in self.roots if root in node_ids)
        kind_counts: dict[str, int] = defaultdict(int)
        confidence_counts: dict[str, int] = defaultdict(int)
        edge_kind_counts: dict[str, int] = defaultdict(int)
        for node in nodes:
            kind_counts[str(node["kind"])] += 1
        for edge in edges:
            confidence_counts[str(edge["confidence"])] += 1
            edge_kind_counts[str(edge["type"])] += 1
        return {
            "schemaVersion": SCHEMA_VERSION,
            "language": self.language,
            "scope": {
                "staticDataOnly": True,
                "runtimePresentationClaimed": False,
                "rootKinds": [
                    "model_config_model",
                    "model_view_state_controller",
                    "animation_config",
                    "material",
                    "gameplay_effect",
                ],
                "excludedGraphKinds": ["unity_asset", "unity_pathid"],
                "note": "Authored configuration and exported-asset evidence only; runtime renderer selection, animation transitions, effect timing, and shader behavior are not reconstructed.",
            },
            "caps": dict(sorted(self.caps.items())),
            "omissions": {
                kind: {
                    "edges": count,
                    "sourcesAffected": self.omission_sources[kind],
                    "reason": "per-source display cap",
                }
                for kind, count in sorted(self.omissions.items())
            },
            "counts": {
                "roots": len(roots),
                "nodes": len(nodes),
                "edges": len(edges),
                "nodeKinds": dict(sorted(kind_counts.items())),
                "edgeKinds": dict(sorted(edge_kind_counts.items())),
                "confidence": dict(sorted(confidence_counts.items())),
            },
            "roots": roots,
            "nodes": nodes,
            "edges": edges,
            "rootEdges": self.build_root_index(roots, edges),
        }

    @staticmethod
    def build_root_index(roots: list[str], edges: list[dict[str, Any]]) -> dict[str, list[int]]:
        outgoing: dict[str, list[int]] = defaultdict(list)
        incoming: dict[str, list[int]] = defaultdict(list)
        for index, edge in enumerate(edges):
            outgoing[str(edge["source"])].append(index)
            incoming[str(edge["target"])].append(index)
        result: dict[str, list[int]] = {}
        for root in roots:
            queue: deque[tuple[str, int]] = deque([(root, 0)])
            seen = {root}
            # Incoming edges describe who uses or declares the selected root.
            # Keep them as leaves: traversing backwards through shared config or
            # shader hubs would make one detail payload absorb unrelated roots.
            selected: set[int] = set(incoming.get(root, []))
            while queue:
                current, depth = queue.popleft()
                if depth >= 4:
                    continue
                for edge_index in outgoing.get(current, []):
                    selected.add(edge_index)
                    target = str(edges[edge_index]["target"])
                    if target not in seen:
                        seen.add(target)
                        queue.append((target, depth + 1))
            result[root] = sorted(selected)
        return result


def graph_freshness_reason(graph: Path) -> str:
    if not graph.is_file():
        return f"source graph not found: {relative(graph)}"
    inputs = [
        ROOT / "webui" / "data" / "assets" / "index.json",
        ROOT / "webui" / "data" / "game_data" / "index.json",
    ]
    existing = [path for path in inputs if path.is_file()]
    if existing:
        newest = max(existing, key=lambda path: path.stat().st_mtime_ns)
        if newest.stat().st_mtime_ns > graph.stat().st_mtime_ns:
            return (
                f"source graph predates {relative(newest)}; rebuild "
                "tools/endfield_source_graph.py before using presentation edges"
            )
    try:
        connection = sqlite3.connect(f"file:{graph.as_posix()}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT value FROM meta WHERE key = 'asset_map_scope'"
            ).fetchone()
            unity_asset_count = int(connection.execute(
                "SELECT COUNT(*) FROM nodes WHERE kind = 'unity_asset'"
            ).fetchone()[0])
            required_row = connection.execute(
                "SELECT value FROM meta WHERE key = 'asset_map_required_path_ids'"
            ).fetchone()
            matched_row = connection.execute(
                "SELECT value FROM meta WHERE key = 'asset_map_matched_path_ids'"
            ).fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        return f"source graph metadata could not be read: {exc}"
    # Graphs built before asset-map scope metadata was introduced were always
    # exhaustive. New no-map graphs must not masquerade as complete merely
    # because their timestamp is fresh.
    asset_map_scope = str(row[0] or "") if row else ("full" if unity_asset_count else "none")
    if asset_map_scope not in {"full", "relevant"}:
        return (
            f"source graph asset-map scope is {asset_map_scope or 'unknown'}; "
            "rebuild with --relevant-asset-maps or the default full maps before "
            "using presentation edges"
        )
    if not unity_asset_count:
        return "source graph contains no original Unity AssetMap rows"
    if asset_map_scope == "relevant":
        if not required_row or not matched_row:
            return "source graph relevant AssetMap scope has no completed coverage metadata"
        try:
            required = int(required_row[0] or 0)
            matched = int(matched_row[0] or 0)
        except (TypeError, ValueError):
            return "source graph relevant AssetMap coverage metadata is invalid"
        if matched < required:
            return (
                f"source graph relevant AssetMap scope matched {matched} of {required} "
                "required source/PathID identities"
            )
    return ""


def empty_payload(language: str, graph: Path, stale_reason: str, caps: dict[str, int]) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "language": language,
        "scope": {
            "staticDataOnly": True,
            "runtimePresentationClaimed": False,
            "rootKinds": [],
            "excludedGraphKinds": ["unity_asset", "unity_pathid"],
            "note": "Presentation relationships are unavailable until the local source graph is current.",
        },
        "graph": {
            "available": False,
            "source": relative(graph),
            "degradedMode": True,
            "stale": graph.is_file(),
            "staleReason": stale_reason or None,
        },
        "caps": dict(sorted(caps.items())),
        "omissions": {},
        "counts": {"roots": 0, "nodes": 0, "edges": 0, "nodeKinds": {}, "edgeKinds": {}, "confidence": {}},
        "roots": [],
        "nodes": [],
        "edges": [],
        "rootEdges": {},
    }


def build_language(args: argparse.Namespace, language: str) -> tuple[Path, dict[str, Any]]:
    language = language.upper()
    caps = {
        "modelAssetsPerEntity": max(0, args.max_model_assets),
        "materialsPerEntity": max(0, args.max_materials),
        "texturesPerEntity": max(0, args.max_textures),
        "texturesPerMaterial": max(0, args.max_material_textures),
        "effectAssetsPerEffect": max(0, args.max_effect_assets),
    }
    internal_caps = {
        "modelAssets": caps["modelAssetsPerEntity"],
        "materials": caps["materialsPerEntity"],
        "textures": caps["texturesPerEntity"],
        "materialTextures": caps["texturesPerMaterial"],
        "effectAssets": caps["effectAssetsPerEffect"],
    }
    stale_reason = graph_freshness_reason(args.graph)
    payload: dict[str, Any]
    if stale_reason:
        payload = empty_payload(language, args.graph, stale_reason, caps)
    else:
        try:
            connection = sqlite3.connect(f"file:{args.graph.as_posix()}?mode=ro", uri=True)
            connection.execute("SELECT 1 FROM nodes LIMIT 1").fetchone()
            builder = PresentationBuilder(connection, language, internal_caps)
            payload = builder.build()
            connection.close()
            payload["caps"] = dict(sorted(caps.items()))
            payload["graph"] = {
                "available": True,
                "source": relative(args.graph),
                "degradedMode": False,
                "stale": False,
                "staleReason": None,
            }
        except sqlite3.Error as exc:
            payload = empty_payload(language, args.graph, f"source graph could not be read: {exc}", caps)
    output = args.data_root / language / "presentation" / "index.json"
    write_json(output, payload)
    return output, payload


def validate_payload(payload: dict[str, Any]) -> None:
    nodes = payload.get("nodes") or []
    edges = payload.get("edges") or []
    node_ids = [str(node.get("id") or "") for node in nodes]
    if not all(node_ids) or len(node_ids) != len(set(node_ids)):
        raise ValueError("presentation payload contains missing or duplicate node ids")
    known = set(node_ids)
    roots = [str(root) for root in payload.get("roots") or []]
    if len(roots) != len(set(roots)) or any(root not in known for root in roots):
        raise ValueError("presentation payload contains duplicate or unknown roots")
    dangling = [edge for edge in edges if edge.get("source") not in known or edge.get("target") not in known]
    if dangling:
        raise ValueError(f"presentation payload contains {len(dangling)} dangling edges")
    edge_keys = [
        (
            edge.get("source"),
            edge.get("target"),
            edge.get("type"),
            (edge.get("evidence") or {}).get("source"),
            (edge.get("evidence") or {}).get("path"),
        )
        for edge in edges
    ]
    if len(edge_keys) != len(set(edge_keys)):
        raise ValueError("presentation payload contains duplicate edges")
    if any(str(node.get("graphKind")) in {"unity_asset", "unity_pathid"} for node in nodes):
        raise ValueError("presentation payload unexpectedly contains generic Unity nodes")
    counts = payload.get("counts") or {}
    if counts.get("roots") != len(roots) or counts.get("nodes") != len(nodes) or counts.get("edges") != len(edges):
        raise ValueError("presentation payload counts do not match its arrays")
    root_edges = payload.get("rootEdges") or {}
    if set(root_edges) != set(roots):
        raise ValueError("presentation root edge index does not match roots")
    for root, indices in root_edges.items():
        if len(indices) != len(set(indices)) or any(not isinstance(index, int) or index < 0 or index >= len(edges) for index in indices):
            raise ValueError(f"presentation root {root} has an invalid edge index")


def main() -> int:
    args = parse_args()
    for language in args.languages:
        output, payload = build_language(args, language)
        validate_payload(payload)
        graph_mode = "source graph" if payload["graph"]["available"] else "degraded"
        print(
            f"{language.upper()}: {payload['counts']['roots']} roots, "
            f"{payload['counts']['nodes']} nodes, {payload['counts']['edges']} edges, "
            f"{graph_mode} -> {relative(output)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
