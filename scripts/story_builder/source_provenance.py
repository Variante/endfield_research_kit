"""Generic original-file provenance for generated Story connections.

Story recovery produces many connection families, each with a ``sourceFiles``
list.  The list is useful for navigation but historically did not prove that
the referenced bytes still exist in the current export.  This module resolves
the whole connection corpus by shape, attaches SHA-256 records for files that
are actually present, and keeps unresolved references visible without turning
them into evidence.

The collector deliberately does not inspect relation names, mission ids, Story
suffixes, OCR proposals, or manual overrides.  It only accepts original game
data roots (or the installed original binary/metadata) and therefore remains a
generic provenance pass rather than an object-specific recovery rule.
"""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_ORIGINAL_BINARY_NAMES = {"GameAssembly.dll", "global-metadata.dat"}
_SOURCE_REFERENCE_PREFIXES = (
    "export_full/",
    "Data/",
    "StreamingAssets/",
    "Persistent/",
)
_FILE_SUFFIXES = {
    ".asset",
    ".bin",
    ".bytes",
    ".bundle",
    ".csv",
    ".dat",
    ".dll",
    ".json",
    ".mp4",
    ".pck",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
_HASH_CACHE: dict[Path, str] = {}
_BASENAME_INDEX_CACHE: dict[Path, dict[str, tuple[Path, ...]]] = {}


def _normalise_reference(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/")


def _is_path_reference(reference: str) -> bool:
    """Return whether a source token is intended to name a file path.

    Asset ids (for example ``CAB-...``) and bare serialized object names are
    intentionally not treated as missing files.  Export-relative paths,
    file-like basenames, and absolute original-binary paths are the only
    references that can be validated here.
    """

    if not reference:
        return False
    path = Path(reference)
    return (
        path.is_absolute()
        or "/" in reference
        or reference.startswith(_SOURCE_REFERENCE_PREFIXES)
        or path.suffix.lower() in _FILE_SUFFIXES
    )


def _basename_index(root: Path) -> dict[str, tuple[Path, ...]]:
    root_resolved = root.resolve()
    cached = _BASENAME_INDEX_CACHE.get(root_resolved)
    if cached is not None:
        return cached
    index: dict[str, list[Path]] = defaultdict(list)
    structured_root = root_resolved / "export_full" / "structured"
    for data_root in (
        structured_root / "StreamingAssets",
        structured_root / "Persistent",
    ):
        if not data_root.is_dir():
            continue
        for candidate in data_root.rglob("*"):
            if candidate.is_file():
                index[candidate.name.lower()].append(candidate.resolve())
    frozen = {
        name: tuple(sorted(paths, key=lambda path: path.as_posix()))
        for name, paths in index.items()
    }
    _BASENAME_INDEX_CACHE[root_resolved] = frozen
    return frozen


def _candidate_paths(reference: str, root: Path) -> list[Path]:
    path = Path(reference)
    if path.is_absolute():
        return [path]
    candidates: list[Path] = []
    if reference.startswith("export_full/"):
        candidates.append(root / Path(reference))
    else:
        candidates.extend((
            root / Path(reference),
            root / "export_full" / "structured" / "StreamingAssets" / Path(reference),
            root / "export_full" / "structured" / "Persistent" / Path(reference),
        ))
        if reference.startswith("StreamingAssets/"):
            candidates.append(
                root / "export_full" / "structured" / Path(reference)
            )
        if reference.startswith("Persistent/"):
            candidates.append(
                root / "export_full" / "structured" / Path(reference)
            )
        if "/" not in reference:
            candidates.extend(_basename_index(root).get(reference.lower(), ()))
    out: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        out.append(resolved)
    return out


def _is_original_game_file(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    export_root = (root / "export_full").resolve()
    if resolved.is_relative_to(export_root):
        return True
    return resolved.name in _ORIGINAL_BINARY_NAMES and resolved.is_file()


def _kind_for_path(path: Path) -> str:
    text = path.as_posix()
    if "/LevelScriptData/" in text:
        return "level_script"
    if "/MissionRuntimeAsset/" in text:
        return "mission_runtime"
    if "/LevelData/" in text:
        return "level_data"
    if "/Table/" in text:
        return "original_table"
    if path.name == "GameAssembly.dll":
        return "original_game_binary"
    if path.name == "global-metadata.dat":
        return "original_game_metadata"
    if "/recovered/" in text:
        return "recovered_game_asset"
    return "original_game_file"


def _sha256(path: Path) -> str:
    resolved = path.resolve()
    cached = _HASH_CACHE.get(resolved)
    if cached:
        return cached
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    _HASH_CACHE[resolved] = value
    return value


def _related_file(path: Path, *, reference: str, relation: str) -> dict[str, Any]:
    return {
        "kind": _kind_for_path(path),
        "sourceFile": reference,
        "sha256": _sha256(path),
        "relationship": f"story_connection:{relation}",
    }


def enrich_story_connection_original_files(
    mission_flows_payload: dict[str, dict[str, Any]],
    *,
    root: Path,
) -> dict[str, Any]:
    """Attach validated original-file records to every relation row.

    The input is the complete generated mission-flow corpus.  Any dictionary
    with a relation and a ``sourceFiles`` list is eligible, including nested
    quest connections and dependency rows.  Existing related-file records are
    retained; duplicate paths are collapsed by hash and source path.
    """

    totals = Counter()
    relation_counts: Counter[str] = Counter()
    mission_summaries: dict[str, dict[str, Any]] = {}

    for mission_id, flow_payload in sorted(mission_flows_payload.items()):
        mission_stats = Counter()
        unresolved_by_relation: dict[str, list[str]] = defaultdict(list)

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                relation = str(value.get("relation") or "")
                raw_sources = value.get("sourceFiles")
                if relation and isinstance(raw_sources, list):
                    relation_counts[relation] += 1
                    mission_stats["relationRows"] += 1
                    related: list[dict[str, Any]] = [
                        row
                        for row in value.get("relatedOriginalFiles") or []
                        if isinstance(row, dict) and row.get("sourceFile")
                    ]
                    seen_related = {
                        (
                            str(row.get("sourceFile") or ""),
                            str(row.get("sha256") or ""),
                        )
                        for row in related
                    }
                    considered = 0
                    unresolved: list[str] = []
                    non_path_references: list[str] = []
                    for raw in raw_sources:
                        reference = _normalise_reference(raw)
                        if not _is_path_reference(reference):
                            if reference:
                                non_path_references.append(reference)
                            continue
                        considered += 1
                        candidates = [
                            path
                            for path in _candidate_paths(reference, root)
                            if _is_original_game_file(path, root)
                        ]
                        if not candidates:
                            unresolved.append(reference)
                            continue
                        for candidate in candidates:
                            # Use the export-relative path when a generic
                            # ``Data/...`` reference resolves to both roots.
                            source_reference = reference
                            if len(candidates) > 1:
                                try:
                                    source_reference = candidate.relative_to(root).as_posix()
                                except ValueError:
                                    source_reference = candidate.as_posix()
                            row = _related_file(
                                candidate,
                                reference=source_reference,
                                relation=relation,
                            )
                            signature = (
                                str(row.get("sourceFile") or ""),
                                str(row.get("sha256") or ""),
                            )
                            if signature not in seen_related:
                                seen_related.add(signature)
                                related.append(row)
                    if related:
                        value["relatedOriginalFiles"] = sorted(
                            related,
                            key=lambda row: (
                                str(row.get("sourceFile") or ""),
                                str(row.get("sha256") or ""),
                            ),
                        )
                    validation_status = (
                        "validated"
                        if not unresolved
                        else "partial_unresolved_source_references"
                    )
                    value["relatedOriginalFilesValidation"] = {
                        "status": validation_status,
                        "sourceReferencesConsidered": considered,
                        "attachedOriginalFiles": len(related),
                        "unresolvedSourceReferences": sorted(set(unresolved)),
                        "nonPathSourceReferences": sorted(set(non_path_references)),
                        "usesOcrOrManualOrder": False,
                    }
                    mission_stats["sourceReferencesConsidered"] += considered
                    mission_stats["attachedOriginalFiles"] += len(related)
                    mission_stats["unresolvedSourceReferences"] += len(
                        set(unresolved)
                    )
                    mission_stats["nonPathSourceReferences"] += len(
                        set(non_path_references)
                    )
                    totals["relationRows"] += 1
                    totals["sourceReferencesConsidered"] += considered
                    totals["attachedOriginalFiles"] += len(related)
                    totals["unresolvedSourceReferences"] += len(set(unresolved))
                    totals["nonPathSourceReferences"] += len(
                        set(non_path_references)
                    )
                    if unresolved:
                        unresolved_by_relation[relation].extend(unresolved)
                for key, child in value.items():
                    if key in {"relatedOriginalFiles", "relatedOriginalFilesValidation"}:
                        continue
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(flow_payload)
        mission_summaries[mission_id] = {
            "relationRows": mission_stats["relationRows"],
            "sourceReferencesConsidered": mission_stats["sourceReferencesConsidered"],
            "attachedOriginalFiles": mission_stats["attachedOriginalFiles"],
            "unresolvedSourceReferences": mission_stats["unresolvedSourceReferences"],
            "nonPathSourceReferences": mission_stats["nonPathSourceReferences"],
            "unresolvedByRelation": {
                relation: sorted(set(values))
                for relation, values in sorted(unresolved_by_relation.items())
            },
            "status": (
                "validated"
                if not mission_stats["unresolvedSourceReferences"]
                else "partial_unresolved_source_references"
            ),
        }
        flow_payload["storyConnectionOriginalFileSummary"] = {
            key: value
            for key, value in mission_summaries[mission_id].items()
            if key != "unresolvedByRelation"
        }

    return {
        "schema": "storyConnectionOriginalFiles.v1",
        "root": root.resolve().as_posix(),
        "summary": {
            **dict(totals),
            "missionCount": len(mission_summaries),
            "relationCounts": dict(sorted(relation_counts.items())),
            "validatedMissionCount": sum(
                row["status"] == "validated" for row in mission_summaries.values()
            ),
            "partialMissionCount": sum(
                row["status"] != "validated" for row in mission_summaries.values()
            ),
        },
        "missions": mission_summaries,
        "evidenceBoundary": (
            "SHA-256 records prove that an accepted Story connection cites the "
            "current original exported file bytes. They do not add mission "
            "ownership, activation, branch selection, or Story chronology; "
            "unresolved source references and non-path tokens remain diagnostic "
            "only."
        ),
        "usesOcrOrManualOrder": False,
    }


def render_story_connection_original_files_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Story connection original-file provenance",
        "",
        f"- Missions scanned: `{summary.get('missionCount', 0)}`",
        f"- Relation rows scanned: `{summary.get('relationRows', 0)}`",
        f"- Source references considered: `{summary.get('sourceReferencesConsidered', 0)}`",
        f"- Hash-validated original files attached: `{summary.get('attachedOriginalFiles', 0)}`",
        f"- Unresolved path references: `{summary.get('unresolvedSourceReferences', 0)}`",
        f"- Non-path source tokens retained as diagnostics: `{summary.get('nonPathSourceReferences', 0)}`",
        f"- Fully validated mission flows: `{summary.get('validatedMissionCount', 0)}`",
        f"- Partially unresolved mission flows: `{summary.get('partialMissionCount', 0)}`",
        "",
        "This is provenance context only. It does not create ownership, activation, branch-selection, or Story-order evidence.",
        "",
        "## Relation rows",
        "",
        "| relation | rows |",
        "| --- | ---: |",
    ]
    for relation, count in sorted((summary.get("relationCounts") or {}).items()):
        lines.append(f"| `{relation}` | {count} |")
    return "\n".join(lines) + "\n"
