#!/usr/bin/env python3
"""Audit exact GameObject component hierarchies for actionable Story carriers.

The compact AnimeStudio object index intentionally contains the Story-facing
JSON types, not every GameObject. This audit:

1. validates and scans the published object indexes;
2. selects exact actionable Story values whose object has a resolved
   ``m_GameObject`` PPtr;
3. maps each original chunk offset back to its logical AssetBundle;
4. extracts only those bundles and exports their GameObjects; and
5. resolves sibling and descendant components back through the typed object
   index.

GameObject co-membership and Transform parent/child links are exact serialized
relations, but this report still emits candidates only. Native consumer
semantics are required before any ownership, playback, or order edge can be
promoted.
"""

from __future__ import annotations

import argparse
import json
import mmap
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import resolve_installed_game_data_root  # noqa: E402

import build_animestudio_story_carrier_audit as carrier  # noqa: E402

SCHEMA = "animestudioStoryGameObjectAudit.v3"
DEFAULT_OUTPUT_ROOT = ROOT / "export_full"
DEFAULT_GAP_QUEUE = (
    ROOT / "reports" / "mission_order" / "source_story_gap_queue_CN.json"
)
DEFAULT_REPORT_ROOT = ROOT / "reports" / "story" / "recovery"
DEFAULT_CLI = (
    ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
SOURCES = ("StreamingAssets", "Persistent")
TARGETED_DUMP_BATCH_SIZE = 64


class AuditError(RuntimeError):
    """Raised when exact provenance or targeted extraction cannot be trusted."""


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def resolved_game_object_ptrs(row: dict[str, Any]) -> list[dict[str, Any]]:
    pointers: list[dict[str, Any]] = []
    for pptr in row.get("pptrs") or []:
        if not isinstance(pptr, dict) or pptr.get("path") != "$.m_GameObject":
            continue
        path_id = pptr.get("pathId")
        if not isinstance(path_id, int) or path_id == 0:
            continue
        if not str(pptr.get("status") or "").startswith("resolved"):
            continue
        pointers.append(pptr)
    return pointers


def collect_story_game_objects(
    rows: Iterable[dict[str, Any]],
    target_missions: dict[str, set[str]],
    source: str,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    found: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for row in rows:
        if row.get("recordType") != "object":
            continue
        counts["objectsScanned"] += 1
        matches = sorted({
            story_key
            for field in carrier.scalar_rows(row)
            if (
                story_key := carrier.canonical_target_story_key(
                    field["value"],
                    target_missions,
                )
            )
        })
        if not matches:
            continue
        counts["objectsWithExactTargetValue"] += 1
        pointers = resolved_game_object_ptrs(row)
        if not pointers:
            continue
        counts["objectsWithResolvedGameObject"] += 1
        identity = row.get("object") or {}
        type_identity = carrier.object_type_identity(row)
        found.append({
            "storyKeys": matches,
            "expectedGapMissions": sorted({
                mission
                for story_key in matches
                for mission in target_missions[story_key]
            }),
            "source": source,
            "object": dict(identity),
            "type": type_identity,
            "gameObjectPathIds": sorted({
                int(pptr["pathId"]) for pptr in pointers
            }),
        })
    found.sort(key=lambda row: (
        row["source"],
        str(row["object"].get("serializedFile") or ""),
        int(row["object"].get("sourceOffset") or 0),
        int(row["object"].get("pathId") or 0),
    ))
    return found, counts


def _find_enclosing_object(
    mapped: mmap.mmap,
    position: int,
) -> dict[str, Any] | None:
    start = mapped.rfind(b"{", 0, position)
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for cursor in range(start, len(mapped)):
        value = mapped[cursor]
        if in_string:
            if escaped:
                escaped = False
            elif value == 0x5C:
                escaped = True
            elif value == 0x22:
                in_string = False
            continue
        if value == 0x22:
            in_string = True
        elif value == 0x7B:
            depth += 1
        elif value == 0x7D:
            depth -= 1
            if depth == 0:
                try:
                    payload = json.loads(mapped[start:cursor + 1])
                except json.JSONDecodeError:
                    return None
                return payload if isinstance(payload, dict) else None
    return None


def load_chunk_record(index_path: Path, chunk_file: str) -> dict[str, Any]:
    if not index_path.is_file():
        raise AuditError(f"missing VFS index: {index_path}")
    needle = json.dumps(f"{chunk_file}", ensure_ascii=True).encode("utf-8")
    with index_path.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as mapped:
        position = 0
        while True:
            position = mapped.find(needle, position)
            if position < 0:
                break
            payload = _find_enclosing_object(mapped, position)
            if (
                payload
                and payload.get("fileName") == chunk_file
                and isinstance(payload.get("files"), list)
            ):
                return payload
            position += len(needle)
    raise AuditError(f"{index_path}: chunk record not found for {chunk_file}")


def logical_bundle_for_offset(
    chunk: dict[str, Any],
    source_offset: int,
) -> dict[str, Any]:
    matches = []
    for row in chunk.get("files") or []:
        if not isinstance(row, dict):
            continue
        offset = row.get("offset")
        length = row.get("length")
        if (
            isinstance(offset, int)
            and isinstance(length, int)
            and offset <= source_offset < offset + length
        ):
            matches.append(row)
    if len(matches) != 1:
        raise AuditError(
            f"chunk {chunk.get('fileName')}: source offset {source_offset} "
            f"mapped to {len(matches)} logical files"
        )
    row = matches[0]
    if row.get("blockType") != "Bundle":
        raise AuditError(
            f"source offset {source_offset} is not in a Bundle logical file"
        )
    name = str(row.get("name") or "")
    if not name.lower().endswith(".ab"):
        raise AuditError(f"unexpected logical bundle name: {name!r}")
    return {
        "name": name,
        "offset": int(row["offset"]),
        "length": int(row["length"]),
        "dataMd5": str(row.get("dataMd5") or ""),
        "chunkFile": str(chunk.get("fileName") or ""),
        "chunkContentMd5": str(chunk.get("contentMd5") or ""),
    }


def map_logical_bundles(
    output_root: Path,
    roots: list[dict[str, Any]],
) -> dict[str, list[str]]:
    chunk_cache: dict[tuple[str, str], dict[str, Any]] = {}
    logical_by_source: dict[str, set[str]] = defaultdict(set)
    for row in roots:
        source = str(row["source"])
        identity = row["object"]
        source_path = str(identity.get("source") or "").replace("\\", "/")
        chunk_file = Path(source_path).name
        if not chunk_file.lower().endswith(".chk"):
            raise AuditError(f"unexpected indexed source path: {source_path!r}")
        cache_key = (source, chunk_file)
        if cache_key not in chunk_cache:
            index_path = (
                output_root
                / "recovered"
                / "AnimeStudio-cli"
                / source
                / "vfs_index"
                / "bundle_vfs_index.json"
            )
            chunk_cache[cache_key] = load_chunk_record(index_path, chunk_file)
        logical = logical_bundle_for_offset(
            chunk_cache[cache_key],
            int(identity.get("sourceOffset") or 0),
        )
        row["logicalBundle"] = logical
        logical_by_source[source].add(logical["name"])
    return {
        source: sorted(names)
        for source, names in sorted(logical_by_source.items())
    }


def run_checked(command: list[str], *, label: str) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise AuditError(
            f"{label} failed with return code {result.returncode}\n"
            f"stdout:\n{result.stdout[-4000:]}\n"
            f"stderr:\n{result.stderr[-4000:]}"
        )


def batched_logical_names(
    logical_names: list[str],
    batch_size: int = TARGETED_DUMP_BATCH_SIZE,
) -> list[list[str]]:
    """Keep repeated ``--file-regex`` arguments below Windows CLI limits."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    return [
        logical_names[index:index + batch_size]
        for index in range(0, len(logical_names), batch_size)
    ]


def extract_game_objects(
    cli: Path,
    game_root: Path,
    logical_by_source: dict[str, list[str]],
    work_root: Path,
) -> dict[str, Path]:
    game_object_roots: dict[str, Path] = {}
    for source, logical_names in logical_by_source.items():
        if not logical_names:
            continue
        source_root = game_root / source
        if not source_root.is_dir():
            raise AuditError(f"missing installed-game source: {source_root}")
        raw_root = work_root / source / "raw"
        json_root = work_root / source / "json"
        raw_root.mkdir(parents=True, exist_ok=True)
        json_root.mkdir(parents=True, exist_ok=True)
        for batch_index, logical_batch in enumerate(
            batched_logical_names(logical_names),
            start=1,
        ):
            dump_command = [
                str(cli),
                "dump",
                "--streaming-assets",
                str(source_root),
                "--output",
                str(raw_root),
                "--block-type",
                "bundle",
            ]
            for logical_name in logical_batch:
                dump_command.extend([
                    "--file-regex",
                    re.escape(logical_name) + "$",
                ])
            run_checked(
                dump_command,
                label=(
                    f"{source} targeted VFS dump batch "
                    f"{batch_index}"
                ),
            )
        extracted = list(raw_root.rglob("*.ab"))
        if len(extracted) != len(logical_names):
            raise AuditError(
                f"{source}: extracted {len(extracted)} bundles, expected "
                f"{len(logical_names)}"
            )
        run_checked(
            [
                str(cli),
                str(raw_root),
                str(json_root),
                "--game",
                "ArknightsEndfield",
                "--logger_flags",
                "Warning",
                "Error",
                "--group_assets",
                "ByType",
                "--export_type",
                "JSON",
                "--types",
                "GameObject:Both",
            ],
            label=f"{source} targeted GameObject export",
        )
        game_object_roots[source] = json_root / "GameObject"
    return game_object_roots


def game_object_components(
    game_object_root: Path,
) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    if not game_object_root.is_dir():
        return result
    for path in sorted(game_object_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuditError(f"cannot read GameObject JSON {path}: {exc}") from exc
        transform = payload.get("m_Transform") or {}
        game_object = transform.get("m_GameObject") or {}
        path_id = game_object.get("m_PathID")
        if not isinstance(path_id, int) or path_id == 0:
            raise AuditError(f"{path}: cannot resolve GameObject PathID")
        components = []
        for item in payload.get("m_Components") or []:
            component_id = item.get("m_PathID") if isinstance(item, dict) else None
            if isinstance(component_id, int) and component_id:
                components.append(component_id)
        if path_id in result:
            raise AuditError(
                f"duplicate GameObject PathID {path_id} under {game_object_root}"
            )
        father = transform.get("m_Father") or {}
        child_transform_path_ids = []
        for item in transform.get("m_Children") or []:
            child_id = item.get("m_PathID") if isinstance(item, dict) else None
            if isinstance(child_id, int) and child_id:
                child_transform_path_ids.append(child_id)
        result[path_id] = {
            "name": str(payload.get("m_Name") or payload.get("Name") or ""),
            "componentPathIds": components,
            "transformComponentPathId": (
                components[0] if components and transform else 0
            ),
            "parentTransformPathId": int(father.get("m_PathID") or 0),
            "childTransformPathIds": child_transform_path_ids,
            "sourceJson": str(path),
        }
    return result


def descendant_game_objects(
    game_objects: dict[int, dict[str, Any]],
    root_path_id: int,
) -> tuple[list[dict[str, Any]], list[int]]:
    """Resolve an exact Transform child tree beneath one exported GameObject."""
    root = game_objects.get(root_path_id)
    if root is None:
        raise AuditError(f"GameObject PathID {root_path_id} was not exported")
    transform_to_game_object: dict[int, int] = {}
    children_by_parent: dict[int, set[int]] = defaultdict(set)
    for game_object_path_id, row in game_objects.items():
        transform_path_id = int(row.get("transformComponentPathId") or 0)
        if transform_path_id:
            previous = transform_to_game_object.setdefault(
                transform_path_id, game_object_path_id
            )
            if previous != game_object_path_id:
                raise AuditError(
                    f"duplicate Transform PathID {transform_path_id}"
                )
        parent_transform_path_id = int(
            row.get("parentTransformPathId") or 0
        )
        if parent_transform_path_id:
            children_by_parent[parent_transform_path_id].add(
                game_object_path_id
            )

    descendants: list[dict[str, Any]] = []
    unresolved_child_transforms: set[int] = set()
    visited = {root_path_id}
    pending = [(root_path_id, 0)]
    while pending:
        parent_path_id, parent_depth = pending.pop()
        parent = game_objects[parent_path_id]
        parent_transform_path_id = int(
            parent.get("transformComponentPathId") or 0
        )
        declared_child_transforms = {
            int(value)
            for value in parent.get("childTransformPathIds") or []
            if isinstance(value, int) and value
        }
        declared_child_game_objects = set()
        for transform_path_id in declared_child_transforms:
            child_path_id = transform_to_game_object.get(transform_path_id)
            if child_path_id is None:
                unresolved_child_transforms.add(transform_path_id)
                continue
            declared_child_game_objects.add(child_path_id)
        parent_link_children = children_by_parent.get(
            parent_transform_path_id, set()
        )
        if declared_child_game_objects != parent_link_children:
            raise AuditError(
                f"GameObject PathID {parent_path_id}: Transform child/father "
                "relations disagree"
            )
        for child_path_id in sorted(parent_link_children, reverse=True):
            if child_path_id in visited:
                raise AuditError(
                    f"GameObject hierarchy cycle or repeated child "
                    f"{child_path_id}"
                )
            visited.add(child_path_id)
            child = game_objects[child_path_id]
            depth = parent_depth + 1
            descendants.append({
                "pathId": child_path_id,
                "name": child["name"],
                "depth": depth,
                "parentGameObjectPathId": parent_path_id,
                "parentTransformPathId": child["parentTransformPathId"],
                "transformComponentPathId":
                    child["transformComponentPathId"],
                "childTransformPathIds":
                    child.get("childTransformPathIds") or [],
                "componentPathIds": child["componentPathIds"],
            })
            pending.append((child_path_id, depth))
    if unresolved_child_transforms:
        sample = ", ".join(
            str(value) for value in sorted(unresolved_child_transforms)[:5]
        )
        raise AuditError(
            f"GameObject PathID {root_path_id}: unresolved child Transform "
            f"PathIDs ({sample})"
        )
    descendants.sort(key=lambda row: (
        row["depth"],
        row["parentGameObjectPathId"],
        row["pathId"],
    ))
    return descendants, sorted(unresolved_child_transforms)


def collect_component_rows(
    output_root: Path,
    wanted: dict[str, set[tuple[str, int]]],
) -> dict[tuple[str, str, int], dict[str, Any]]:
    result: dict[tuple[str, str, int], dict[str, Any]] = {}
    for source, identities in wanted.items():
        if not identities:
            continue
        summary = carrier.load_animestudio_object_index_summary(
            output_root, source
        )
        if summary is None or summary.get("complete") is not True:
            raise AuditError(f"{source}: published object index is not complete")
        index_dir = carrier.animestudio_object_index_dir(output_root, source)
        object_path = index_dir / summary["outputs"]["objects"]["path"]
        for row in carrier.iter_gzip_jsonl(object_path):
            if row.get("recordType") != "object":
                continue
            identity = row.get("object") or {}
            key = (
                str(identity.get("serializedFile") or ""),
                int(identity.get("pathId") or 0),
            )
            if key in identities:
                result[(source, key[0], key[1])] = row
    return result


def compact_component(row: dict[str, Any]) -> dict[str, Any]:
    identity = row.get("object") or {}
    scalars = carrier.scalar_rows(row)
    return {
        "pathId": int(identity.get("pathId") or 0),
        "type": carrier.object_type_identity(row),
        "ownerFields": [
            field for field in scalars
            if field["fieldClass"] == "owner_identifier"
            and carrier.meaningful_identifier_value(field["value"])
        ],
        "runtimeFields": [
            field for field in scalars
            if field["fieldClass"] == "runtime_identifier"
            and carrier.meaningful_identifier_value(field["value"])
        ],
        "storyFields": [
            field for field in scalars
            if field["fieldClass"] == "story_identifier"
            and carrier.meaningful_identifier_value(field["value"])
        ],
    }


def analyze_roots(
    roots: list[dict[str, Any]],
    game_objects_by_source: dict[str, dict[int, dict[str, Any]]],
    component_rows: dict[tuple[str, str, int], dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    analyzed: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for root in roots:
        source = str(root["source"])
        identity = root["object"]
        serialized_file = str(identity.get("serializedFile") or "")
        story_path_id = int(identity.get("pathId") or 0)
        for game_object_path_id in root["gameObjectPathIds"]:
            game_object = game_objects_by_source.get(source, {}).get(
                game_object_path_id
            )
            if game_object is None:
                raise AuditError(
                    f"{source}/{serialized_file}: GameObject PathID "
                    f"{game_object_path_id} was not exported"
                )
            siblings = []
            unresolved_component_path_ids = []
            for component_path_id in game_object["componentPathIds"]:
                if component_path_id in {
                    story_path_id,
                    game_object["transformComponentPathId"],
                }:
                    continue
                component = component_rows.get((
                    source,
                    serialized_file,
                    component_path_id,
                ))
                if component is None:
                    unresolved_component_path_ids.append(component_path_id)
                    continue
                siblings.append(compact_component(component))
            descendants, unresolved_child_transform_path_ids = (
                descendant_game_objects(
                    game_objects_by_source.get(source, {}),
                    game_object_path_id,
                )
            )
            descendant_rows = []
            descendant_candidates = []
            for descendant in descendants:
                typed_components = []
                unresolved_descendant_component_path_ids = []
                for component_path_id in descendant["componentPathIds"]:
                    if component_path_id == (
                        descendant["transformComponentPathId"]
                    ):
                        continue
                    component = component_rows.get((
                        source,
                        serialized_file,
                        component_path_id,
                    ))
                    if component is None:
                        unresolved_descendant_component_path_ids.append(
                            component_path_id
                        )
                        continue
                    typed_components.append(compact_component(component))
                candidates_for_descendant = [
                    row for row in typed_components
                    if row["ownerFields"] or row["runtimeFields"]
                ]
                descendant_candidates.extend(candidates_for_descendant)
                descendant_rows.append({
                    **descendant,
                    "typedComponents": typed_components,
                    "unindexedComponentPathIds":
                        unresolved_descendant_component_path_ids,
                    "candidateComponents": candidates_for_descendant,
                })
            candidates = [
                row for row in siblings
                if row["ownerFields"] or row["runtimeFields"]
            ]
            counts["gameObjectsAudited"] += 1
            counts["typedSiblingComponents"] += len(siblings)
            counts["candidateSiblingComponents"] += len(candidates)
            counts["descendantGameObjectsAudited"] += len(descendant_rows)
            counts["typedDescendantComponents"] += sum(
                len(row["typedComponents"]) for row in descendant_rows
            )
            counts["candidateDescendantComponents"] += len(
                descendant_candidates
            )
            if candidates:
                counts["gameObjectsWithCandidateSibling"] += 1
            if descendant_candidates:
                counts["gameObjectsWithCandidateDescendant"] += 1
            analyzed.append({
                **root,
                "gameObject": {
                    "pathId": game_object_path_id,
                    "name": game_object["name"],
                    "parentTransformPathId":
                        game_object["parentTransformPathId"],
                    "transformComponentPathId":
                        game_object["transformComponentPathId"],
                    "childTransformPathIds":
                        game_object.get("childTransformPathIds") or [],
                    "componentPathIds": game_object["componentPathIds"],
                },
                "typedSiblingComponents": siblings,
                "unindexedComponentPathIds":
                    unresolved_component_path_ids,
                "candidateSiblingComponents": candidates,
                "descendantGameObjects": descendant_rows,
                "unresolvedChildTransformPathIds":
                    unresolved_child_transform_path_ids,
                "candidateDescendantComponents": descendant_candidates,
                "candidateStatus": (
                    "exact_hierarchy_typed_owner_or_runtime_candidate"
                    if candidates or descendant_candidates
                    else "no_typed_owner_or_runtime_sibling_or_descendant"
                ),
                "edgeStatus": "no_edge_candidate_only",
            })
    analyzed.sort(key=lambda row: (
        row["storyKeys"],
        row["source"],
        row["object"]["serializedFile"],
        row["gameObject"]["pathId"],
    ))
    return analyzed, counts


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# AnimeStudio Story GameObject Audit",
        "",
        f"- Core-isolated Story keys: `{report['targetStoryKeys']}`",
        f"- Object rows scanned: `{summary['objectsScanned']}`",
        "- Exact Story-value objects with resolved GameObject: "
        f"`{summary['objectsWithResolvedGameObject']}`",
        f"- Exact GameObjects audited: `{summary['gameObjectsAudited']}`",
        "- GameObjects with a typed owner/runtime sibling candidate: "
        f"`{summary['gameObjectsWithCandidateSibling']}`",
        f"- Exact descendant GameObjects audited: "
        f"`{summary['descendantGameObjectsAudited']}`",
        "- Roots with a typed owner/runtime descendant candidate: "
        f"`{summary['gameObjectsWithCandidateDescendant']}`",
        "",
        "This is a candidate audit, not an ownership or ordering graph. "
        "Exact GameObject component membership does not prove which component "
        "activates Story playback.",
        "",
        "## Descendant typed-component census",
        "",
    ]
    component_type_counts = report.get("descendantComponentTypeCounts") or []
    if not component_type_counts:
        lines.append("_No typed descendant components._")
    else:
        lines.extend([
            "| component type | count |",
            "| --- | ---: |",
        ])
        for row in component_type_counts[:20]:
            lines.append(f"| `{row['type']}` | {row['count']} |")
    lines.extend([
        "",
        "## Candidate sibling components",
        "",
    ])
    candidate_roots = [
        row for row in report["gameObjects"]
        if row["candidateSiblingComponents"]
    ]
    if not candidate_roots:
        lines.append("_No typed owner/runtime sibling candidates._")
    else:
        lines.extend([
            "| Story keys | source object | GameObject | sibling type | "
            "owner/runtime fields |",
            "| --- | --- | --- | --- | --- |",
        ])
        for row in candidate_roots:
            for sibling in row["candidateSiblingComponents"]:
                type_row = sibling["type"]
                type_name = (
                    type_row.get("scriptFullName")
                    or type_row.get("objectType")
                    or "unknown"
                )
                fields = sibling["ownerFields"] + sibling["runtimeFields"]
                field_text = ", ".join(
                    f"`{field['path']}={field['value']}`" for field in fields
                )
                lines.append(
                    f"| {', '.join(f'`{key}`' for key in row['storyKeys'])} | "
                    f"`{row['object']['serializedFile']}` / "
                    f"`{row['object']['pathId']}` | "
                    f"`{row['gameObject']['pathId']}` | `{type_name}` | "
                    f"{field_text} |"
                )
    lines.extend([
        "",
        "## Candidate descendant components",
        "",
    ])
    candidate_descendant_roots = [
        row for row in report["gameObjects"]
        if row["candidateDescendantComponents"]
    ]
    if not candidate_descendant_roots:
        lines.append("_No typed owner/runtime descendant candidates._")
    else:
        lines.extend([
            "| Story keys | source object | descendant | depth | "
            "component type | owner/runtime fields |",
            "| --- | --- | --- | ---: | --- | --- |",
        ])
        for row in candidate_descendant_roots:
            for descendant in row["descendantGameObjects"]:
                for component in descendant["candidateComponents"]:
                    type_row = component["type"]
                    type_name = (
                        type_row.get("scriptFullName")
                        or type_row.get("objectType")
                        or "unknown"
                    )
                    fields = (
                        component["ownerFields"]
                        + component["runtimeFields"]
                    )
                    field_text = ", ".join(
                        f"`{field['path']}={field['value']}`"
                        for field in fields
                    )
                    lines.append(
                        f"| {', '.join(f'`{key}`' for key in row['storyKeys'])} "
                        f"| `{row['object']['serializedFile']}` / "
                        f"`{row['object']['pathId']}` | "
                        f"`{descendant['name']}` / "
                        f"`{descendant['pathId']}` | "
                        f"{descendant['depth']} | `{type_name}` | "
                        f"{field_text} |"
                    )
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        "- Accepted: exact actionable Story value, complete published object "
        "index provenance, resolved `m_GameObject` PPtr, targeted extraction "
        "of the exact original logical bundle, exact GameObject component "
        "PathIDs, and mutually consistent Transform `m_Children` / `m_Father` "
        "links for descendants.",
        "- Rejected: neighboring unrelated GameObjects, bundle proximity, "
        "filenames, untyped scalar names, unresolved PPtrs, and incomplete or "
        "inconsistent Transform hierarchies.",
        "- Promotion: a candidate sibling or descendant still needs "
        "independently recovered native consumer semantics before ownership/"
        "playback promotion and a separate control relation before any order "
        "edge.",
        "",
    ])
    return "\n".join(lines)


def build_report(
    *,
    output_root: Path,
    gap_queue: Path,
    game_root: Path,
    cli: Path,
    work_parent: Path,
) -> dict[str, Any]:
    if not cli.is_file():
        raise AuditError(f"AnimeStudio CLI not found: {cli}")
    target_missions = carrier.load_gap_targets(gap_queue)
    roots: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    source_indexes = []
    for source in SOURCES:
        summary = carrier.load_animestudio_object_index_summary(
            output_root, source
        )
        if summary is None or summary.get("complete") is not True:
            raise AuditError(f"{source}: published object index is not complete")
        index_dir = carrier.animestudio_object_index_dir(output_root, source)
        object_path = index_dir / summary["outputs"]["objects"]["path"]
        found, counts = collect_story_game_objects(
            carrier.iter_gzip_jsonl(object_path),
            target_missions,
            source,
        )
        expected_objects = int((summary.get("counts") or {}).get("objects") or 0)
        if counts["objectsScanned"] != expected_objects:
            raise AuditError(
                f"{source}: merged object count mismatch: "
                f"{counts['objectsScanned']} parsed, {expected_objects} "
                "published"
            )
        roots.extend(found)
        totals.update(counts)
        source_indexes.append({
            "source": source,
            "summary": str(index_dir / "summary.json"),
            "objects": str(object_path),
            "mergeContract": summary.get("mergeContract"),
            "stageSignatureSha256": (
                (summary.get("stageSignature") or {}).get("sha256")
            ),
        })
    logical_by_source = map_logical_bundles(output_root, roots)
    work_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="animestudio_story_gameobject_",
        dir=work_parent,
    ) as temp_name:
        game_object_roots = extract_game_objects(
            cli,
            game_root,
            logical_by_source,
            Path(temp_name),
        )
        game_objects_by_source = {
            source: game_object_components(path)
            for source, path in game_object_roots.items()
        }
        wanted: dict[str, set[tuple[str, int]]] = defaultdict(set)
        for root in roots:
            source = root["source"]
            serialized_file = root["object"]["serializedFile"]
            for game_object_path_id in root["gameObjectPathIds"]:
                game_object = game_objects_by_source.get(source, {}).get(
                    game_object_path_id
                )
                if game_object is None:
                    raise AuditError(
                        f"{source}/{serialized_file}: missing GameObject "
                        f"{game_object_path_id}"
                    )
                for component_path_id in game_object["componentPathIds"]:
                    wanted[source].add(
                        (serialized_file, component_path_id)
                    )
                descendants, _ = descendant_game_objects(
                    game_objects_by_source[source],
                    game_object_path_id,
                )
                for descendant in descendants:
                    for component_path_id in descendant["componentPathIds"]:
                        wanted[source].add(
                            (serialized_file, component_path_id)
                        )
        component_rows = collect_component_rows(output_root, wanted)
        analyzed, analysis_counts = analyze_roots(
            roots,
            game_objects_by_source,
            component_rows,
        )
        descendant_component_types: Counter[str] = Counter()
        for root in analyzed:
            for descendant in root["descendantGameObjects"]:
                for component in descendant["typedComponents"]:
                    type_row = component["type"]
                    type_name = str(
                        type_row.get("scriptFullName")
                        or type_row.get("objectType")
                        or "unknown"
                    )
                    descendant_component_types[type_name] += 1
    totals.update(analysis_counts)
    for key in (
        "objectsScanned",
        "objectsWithExactTargetValue",
        "objectsWithResolvedGameObject",
        "gameObjectsAudited",
        "typedSiblingComponents",
        "candidateSiblingComponents",
        "gameObjectsWithCandidateSibling",
        "descendantGameObjectsAudited",
        "typedDescendantComponents",
        "candidateDescendantComponents",
        "gameObjectsWithCandidateDescendant",
    ):
        totals.setdefault(key, 0)
    return {
        "_schema": SCHEMA,
        "gapQueue": str(gap_queue),
        "targetStoryKeys": len(target_missions),
        "sources": source_indexes,
        "logicalBundles": logical_by_source,
        "summary": dict(sorted(totals.items())),
        "descendantComponentTypeCounts": [
            {"type": type_name, "count": count}
            for type_name, count in sorted(
                descendant_component_types.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "gameObjects": analyzed,
        "evidencePolicy": {
            "accepted": (
                "exact Story value plus resolved m_GameObject PPtr, exact "
                "component membership, and consistent Transform child/father "
                "relations from the targeted original AssetBundle"
            ),
            "candidateOnly": (
                "native consumer semantics are required before ownership or "
                "playback promotion; serialized control is required for order"
            ),
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--gap-queue", type=Path, default=DEFAULT_GAP_QUEUE)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--animestudio-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument(
        "--work-parent",
        type=Path,
        default=ROOT / "tmp" / "story",
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=DEFAULT_REPORT_ROOT,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(
            output_root=args.output_root.resolve(),
            gap_queue=args.gap_queue.resolve(),
            game_root=args.game_root.resolve(),
            cli=args.animestudio_cli.resolve(),
            work_parent=args.work_parent.resolve(),
        )
    except (AuditError, carrier.AuditError) as exc:
        raise SystemExit(
            f"AnimeStudio Story GameObject audit failed: {exc}"
        ) from exc
    json_path = args.report_root / "animestudio_story_gameobject_audit.json"
    markdown_path = args.report_root / "animestudio_story_gameobject_audit.md"
    write_json(json_path, report)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        "AnimeStudio Story GameObject audit: "
        f"{markdown_path.relative_to(ROOT)}"
    )
    print(
        "AnimeStudio Story GameObject data: "
        f"{json_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
