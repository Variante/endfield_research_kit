"""Publish graph-neutral Mission shells from validated source-order rows."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

if __package__ and __package__.startswith("scripts."):
    from scripts.common import sha256_file as _sha256_path
else:
    from common import sha256_file as _sha256_path

from . import story_order_projection


ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    path.write_text(encoded + "\n", encoding="utf-8", newline="\n")


def _repo_path(path: Path) -> str:
    path = path.resolve()
    return (
        path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else path.as_posix()
    )


def _natural_quest_key(value: str) -> tuple[str, int, str]:
    mission, marker, suffix = str(value).partition("_q#")
    try:
        number = int(suffix) if marker else 10**9
    except ValueError:
        number = 10**9
    return mission, number, suffix


def _resolve_report_source_path(source: str) -> Path:
    path = Path(source)
    return path if path.is_absolute() else ROOT / path


def _source_order_shell_related_files(
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
    additional_files: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Collect and hash original files for a strict source-order shell.

    The collector walks the generated evidence shape instead of naming a
    LevelScript class, mission, or action family.  Every listed original file
    must still exist and match its report hash before a shell is published.
    """
    validator = "source_story_order_shell"
    related: dict[tuple[str, str], dict[str, Any]] = {}
    resolved_hash_cache = hash_cache if hash_cache is not None else {}

    def add_file(raw: Any, *, fallback_kind: str, fallback_relationship: str) -> None:
        if isinstance(raw, str):
            raw = {"sourceFile": raw}
        if not isinstance(raw, dict):
            return
        source = str(raw.get("sourceFile") or "")
        if not source:
            return
        normalized_source = source.replace("\\", "/").casefold()
        if normalized_source.startswith((
            "installed persistent vfs/",
            "installed streamingassets vfs/",
        )):
            # Exact logical payloads inspected by targeted VFS dumps carry
            # their own content hash but are not standalone filesystem files.
            # Keep them on the branch record; do not misrepresent the VFS
            # label as a materialized source-order attachment.
            return
        path = _resolve_report_source_path(source)
        if not path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=relatedOriginalFile "
                f"mission={order_row.get('mission') or '-'} expected=file "
                f"actual=missing source={source}"
            )
        actual_hash = resolved_hash_cache.get(path)
        if actual_hash is None:
            actual_hash = _sha256_path(path)
            resolved_hash_cache[path] = actual_hash
        expected_hash = str(raw.get("sha256") or "")
        if expected_hash and expected_hash.casefold() != actual_hash.casefold():
            raise RuntimeError(
                f"validator={validator} gate=relatedOriginalFileHash "
                f"mission={order_row.get('mission') or '-'} "
                f"expected={expected_hash.upper()} actual={actual_hash.upper()} "
                f"source={source}"
            )
        normalized = dict(raw)
        normalized["sourceFile"] = _repo_path(path)
        normalized["sha256"] = actual_hash
        normalized.setdefault("kind", fallback_kind)
        normalized.setdefault("relationship", fallback_relationship)
        key = (
            str(normalized["sourceFile"]),
            str(normalized.get("relationship") or ""),
        )
        related[key] = normalized

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            rows = value.get("relatedOriginalFiles")
            if isinstance(rows, list):
                for row in rows:
                    add_file(
                        row,
                        fallback_kind="original_authored_source",
                        fallback_relationship="strict_source_story_order_context",
                    )
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    strong_edges = [
        edge
        for edge in order_row.get("directEdges") or []
        if isinstance(edge, dict) and str(edge.get("tier") or "") == "strong"
    ]
    for edge in strong_edges:
        for source in edge.get("sourceFiles") or []:
            source_text = str(source or "")
            normalized_source = source_text.replace("\\", "/")
            if "LevelScriptData/" in normalized_source:
                kind = "original_level_script"
            elif "MissionRuntimeAsset/" in normalized_source:
                kind = "original_mission_runtime"
            elif normalized_source.casefold().endswith("gameassembly.dll"):
                kind = "original_game_binary"
            elif normalized_source.casefold().endswith("global-metadata.dat"):
                kind = "original_game_metadata"
            else:
                kind = "original_authored_source"
            add_file(
                source_text,
                fallback_kind=kind,
                fallback_relationship="strict_source_story_order_edge",
            )
    for raw in additional_files or []:
        add_file(
            raw,
            fallback_kind="original_mission_runtime",
            fallback_relationship="source_order_mission_runtime_context",
        )
    walk(order_row.get("branches") or {})
    return sorted(
        related.values(),
        key=lambda row: (
            str(row.get("sourceFile") or ""),
            str(row.get("relationship") or ""),
        ),
    )


def _story_branch_related_original_files(
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
) -> list[dict[str, Any]]:
    """Hash exact original files cited by authored Story branch records.

    Dialog-line/Tree branch projections often cite the recovered TextAsset that
    contains the branch while having no LevelScript source-order edge.  Bounded
    DialogTree validation warnings also identify original files for malformed
    or non-promotable branch carriers.  Keep all of those files in a separate
    catalog: they are useful original-data context, but they are not chronology
    or mission-ownership evidence.  The walk is intentionally shape-driven and
    ignores generated WebUI paths.
    """
    validator = "story_branch_original_files"
    related: dict[str, dict[str, Any]] = {}
    resolved_hash_cache = hash_cache if hash_cache is not None else {}

    def classify(path: Path) -> str:
        normalized = path.as_posix().casefold()
        if "levelscriptdata/" in normalized:
            return "original_level_script"
        if "missionruntimeasset/" in normalized:
            return "original_mission_runtime"
        if normalized.endswith("gameassembly.dll"):
            return "original_game_binary"
        if normalized.endswith("global-metadata.dat"):
            return "original_game_metadata"
        if "/textasset/" in normalized or "json_by_type/textasset/" in normalized:
            return "original_dialog_tree_source"
        return "original_authored_source"

    def add_source(
        raw: Any,
        *,
        relationship: str = "authored_story_branch_source_file",
        expected_hash: str = "",
    ) -> None:
        source = str(raw or "")
        if not source:
            return
        normalized = source.replace("\\", "/").casefold()
        # Branch projections also carry generated conversation paths.  Only
        # original export/game paths are eligible for this hash-validated list.
        if normalized.startswith((
            "webui/",
            "reports/",
            "scratch/",
            "tmp/",
        )) or "/webui/data/" in normalized:
            return
        # The Story branch report may cite bytes that were inspected directly
        # in the installed VFS. Production WebUI dumps intentionally omit
        # patch-byte payloads, so this label is provenance rather than a local
        # filesystem path. Keep real missing paths fail-closed below.
        if normalized.startswith((
            "installed persistent vfs/",
            "installed streamingassets vfs/",
        )):
            return
        path = _resolve_report_source_path(source)
        if not path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=sourceFile "
                f"mission={order_row.get('mission') or '-'} expected=file "
                f"actual=missing source={source}"
            )
        actual_hash = resolved_hash_cache.get(path)
        if actual_hash is None:
            actual_hash = _sha256_path(path)
            resolved_hash_cache[path] = actual_hash
        if expected_hash and actual_hash.casefold() != expected_hash.casefold():
            raise RuntimeError(
                f"validator={validator} gate=sourceHash "
                f"mission={order_row.get('mission') or '-'} "
                f"expected={expected_hash!r} actual={actual_hash!r} "
                f"source={source}"
            )
        related.setdefault(_repo_path(path), {
            "kind": classify(path),
            "sourceFile": _repo_path(path),
            "sha256": actual_hash,
            "relationship": relationship,
        })

    def source_hashes(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        hashes: dict[str, str] = {}
        for raw_path, raw_hash in value.items():
            path_text = str(raw_path or "").replace("\\", "/")
            hash_text = str(raw_hash or "")
            if not path_text or not hash_text:
                continue
            hashes[path_text.casefold()] = hash_text
            hashes[Path(path_text).name.casefold()] = hash_text
        return hashes

    def source_values(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value if str(item or "")]
        return []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            # Branch projections may already carry a normalized
            # ``relatedOriginalFiles`` row (for example the exact
            # GameAssembly file used to validate a DialogTree selector).
            # Preserve that relationship and hash instead of requiring every
            # producer to duplicate it under ``sourceFiles``.  This remains
            # shape-driven: no mission, Story key, or concrete branch class is
            # special-cased here.
            related_rows = value.get("relatedOriginalFiles")
            if isinstance(related_rows, list):
                for row in related_rows:
                    if isinstance(row, dict):
                        add_source(
                            row.get("sourceFile"),
                            relationship=(
                                str(row.get("relationship") or "")
                                or "authored_story_branch_related_original_file"
                            ),
                            expected_hash=str(row.get("sha256") or ""),
                        )
                    elif isinstance(row, str):
                        add_source(row)
            for source in source_values(value.get("sourceFiles")):
                add_source(source)
            # Authored branch projections use both plural ``sourceFiles`` and
            # singular ``sourceFile`` fields.  Walk the singular shape as
            # well; this keeps the collector corpus-driven instead of
            # requiring each branch producer (dialog options, tree nodes,
            # native controls, and validation records) to be named here.
            singular_source = value.get("sourceFile")
            expected_singular_hash = str(
                value.get("sourceSha256") or value.get("sha256") or ""
            )
            for source in source_values(singular_source):
                add_source(
                    source,
                    expected_hash=expected_singular_hash,
                )
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(order_row.get("branches") or {})
    for warning in order_row.get("warnings") or []:
        if not isinstance(warning, dict):
            continue
        # Validation diagnostics are evidence-bearing only when they identify
        # their validator and an original source path.  This keeps unrelated
        # UI/report warnings out of the branch-file catalog without naming a
        # mission, scene, or concrete branch object.
        if not str(warning.get("validator") or ""):
            continue
        expected_hashes = source_hashes(warning.get("sourceSha256"))
        warning_sources = [
            *source_values(warning.get("sourcePaths")),
            *source_values(warning.get("sourceFiles")),
            *source_values(warning.get("sourceFile")),
        ]
        for source in warning_sources:
            normalized = source.replace("\\", "/").casefold()
            expected = expected_hashes.get(normalized)
            if not expected:
                expected = expected_hashes.get(Path(normalized).name.casefold(), "")
            add_source(
                source,
                relationship="authored_story_branch_validation_source_file",
                expected_hash=expected,
            )
    return sorted(related.values(), key=lambda row: str(row["sourceFile"]))


def _source_order_shell_candidate(
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
) -> bool:
    """Return whether a missing pipeline mission has strict source evidence."""
    if not str(order_row.get("mission") or ""):
        return False
    if not any(
        isinstance(edge, dict) and str(edge.get("tier") or "") == "strong"
        for edge in order_row.get("directEdges") or []
    ):
        return False
    mission_data = str(order_row.get("missionData") or "")
    if not mission_data or not _resolve_report_source_path(mission_data).is_file():
        return False
    return bool(_source_order_shell_related_files(order_row, hash_cache=hash_cache))


def _story_branch_shell_candidate(
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
) -> bool:
    """Return whether a missing pipeline mission has branch-source context."""
    if not str(order_row.get("mission") or ""):
        return False
    mission_data = str(order_row.get("missionData") or "")
    if not mission_data or not _resolve_report_source_path(mission_data).is_file():
        return False
    return bool(_story_branch_related_original_files(order_row, hash_cache=hash_cache))


def _create_story_branch_shell(
    index: dict[str, Any],
    output_root: Path,
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
    schema_version: str,
) -> dict[str, Any]:
    """Publish a graph-neutral shell for branch context without a mission owner."""
    mission_id = str(order_row.get("mission") or "")
    mission_data = str(order_row.get("missionData") or "")
    mission_data_path = _resolve_report_source_path(mission_data)
    branch_related_files = _story_branch_related_original_files(
        order_row,
        hash_cache=hash_cache,
    )
    if not mission_id or not mission_data_path.is_file() or not branch_related_files:
        raise RuntimeError(
            "validator=story_branch_shell gate=eligibleSourceMission "
            f"mission={mission_id or '-'} expected=localized-sidecar-and-branch-files "
            f"actual=missionData={mission_data or '-'} "
            f"branchFiles={len(branch_related_files)}"
        )
    level_ids = sorted({
        str(level_id)
        for edge in order_row.get("directEdges") or []
        if isinstance(edge, dict)
        for level_id in edge.get("levelIds") or []
        if level_id
    }, key=_natural_quest_key)
    boundary = (
        "These hash-validated original files are cited by authored Story branch "
        "or bounded branch-validation records. They provide branch-definition "
        "context only; they do not establish mission ownership, activation, or "
        "cross-file chronology."
    )
    story_order = copy.deepcopy(order_row)
    story_order["storyBranchShell"] = True
    story_order["storyBranchShellBoundary"] = (
        "This graph-neutral shell exposes authored Story branch and validation "
        "context for a Story namespace without a MissionRuntimeAsset owner. It "
        "does not establish mission ownership, activation, or Story-file order."
    )
    story_order["storyBranchRelatedOriginalFiles"] = copy.deepcopy(
        branch_related_files
    )
    story_order["storyBranchRelatedFilesBoundary"] = boundary
    payload = {
        "schemaVersion": schema_version,
        "mission": {
            "id": mission_id,
            "nameKey": "",
            "descriptionKey": "",
            "levelId": level_ids[0] if len(level_ids) == 1 else "",
            "missionType": None,
            "rewardId": "",
            "mainPath": [],
            "entryQuestIds": [],
            "nativeRuntimeBindings": [],
            "source": _repo_path(mission_data_path),
            "storyBranchShell": True,
            "storyBranchShellBoundary": story_order["storyBranchShellBoundary"],
            "storyBranchRelatedOriginalFiles": copy.deepcopy(branch_related_files),
            "storyBranchRelatedFilesBoundary": boundary,
            "relatedOriginalFiles": [],
            "sourceBoundary": (
                "No MissionRuntimeAsset payload exists for this Story namespace. "
                "The page exposes authored branch/validation context only; it is "
                "not a mission or quest owner and does not establish Story order."
            ),
        },
        "nodes": [],
        "edges": [],
        "caseStudy": None,
        "missionGraph": {"upstream": {}, "downstream": {}},
        "envTalkContext": [],
        "storyOrder": story_order,
    }
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    _write_json(mission_output / f"{mission_id}.json", payload)
    summary = {
        "id": mission_id,
        "nameKey": "",
        "levelId": payload["mission"]["levelId"],
        "questCount": 0,
        "mainPathCount": 0,
        "entryCount": 0,
        "fanoutCount": 0,
        "multiPrevJoinCount": 0,
        "activeJoinCount": 0,
        "exactFinishCount": 0,
        "serverPlaceholderCount": 0,
        "serverPlaceholderQuestCount": 0,
        "failureConditionCount": 0,
        "externalDependencyCount": 0,
        "submitItemConditionCount": 0,
        "submitItemQuestCount": 0,
        "submitItemDialogCoGateCount": 0,
        "submitItemLevelScriptCoGateCount": 0,
        "nativeRuntimeBindingCount": 0,
        "activityStageHostCount": 0,
        "activityStageHostedQuestCount": 0,
        "trackingInfoCount": 0,
        "trackingObjectiveCount": 0,
        "missionPropertyCount": 0,
        "conditionTypes": [],
        "caseStudy": False,
        "file": f"missions/{mission_id}.json",
        "storyBranchShell": True,
        "storyBranchRelatedFileCount": len(branch_related_files),
    }
    story_order_projection.update_story_order_summary(summary, story_order)
    index.setdefault("missions", []).append(summary)
    return summary


def _create_source_order_shell(
    index: dict[str, Any],
    output_root: Path,
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
    schema_version: str,
) -> dict[str, Any]:
    """Publish a graph-neutral shell for strict original-data Story order."""
    mission_id = str(order_row.get("mission") or "")
    mission_data = str(order_row.get("missionData") or "")
    mission_data_path = _resolve_report_source_path(mission_data)
    related_files = _source_order_shell_related_files(
        order_row,
        hash_cache=hash_cache,
    )
    branch_related_files = _story_branch_related_original_files(
        order_row,
        hash_cache=hash_cache,
    )
    if not mission_id or not mission_data_path.is_file() or not related_files:
        raise RuntimeError(
            "validator=source_story_order_shell gate=eligibleSourceMission "
            f"mission={mission_id or '-'} expected=localized-sidecar-and-original-files "
            f"actual=missionData={mission_data or '-'} relatedFiles={len(related_files)}"
        )
    level_ids = sorted({
        str(level_id)
        for edge in order_row.get("directEdges") or []
        if isinstance(edge, dict)
        for level_id in edge.get("levelIds") or []
        if level_id
    }, key=_natural_quest_key)
    story_order = copy.deepcopy(order_row)
    story_order["sourceOrderShell"] = True
    story_order["sourceOrderShellBoundary"] = (
        "This graph-neutral shell publishes strict original-data Story order and "
        "its hashed related files without claiming MissionRuntime, quest, playback "
        "ownership, activation, branch selection, or additional chronology."
    )
    story_order["sourceOrderRelatedOriginalFiles"] = copy.deepcopy(related_files)
    story_order["sourceOrderRelatedFilesBoundary"] = (
        "These original files are attached to the strict source-order report for "
        "auditability only. They do not establish mission ownership, activation, "
        "branch selection, or a total Story-file order."
    )
    story_order["storyBranchRelatedOriginalFiles"] = copy.deepcopy(
        branch_related_files
    )
    story_order["storyBranchRelatedFilesBoundary"] = (
        "These hash-validated original files are cited by authored Story branch "
        "or bounded branch-validation records. They provide branch-definition "
        "context only; they do not establish mission ownership, activation, or "
        "cross-file chronology."
    )
    payload = {
        "schemaVersion": schema_version,
        "mission": {
            "id": mission_id,
            "nameKey": "",
            "descriptionKey": "",
            "levelId": level_ids[0] if len(level_ids) == 1 else "",
            "missionType": None,
            "rewardId": "",
            "mainPath": [],
            "entryQuestIds": [],
            "nativeRuntimeBindings": [],
            "source": _repo_path(mission_data_path),
            "sourceOrderShell": True,
            "sourceOrderRelatedOriginalFiles": copy.deepcopy(related_files),
            "sourceOrderRelatedFilesBoundary": (
                "These original files are attached to the strict source-order "
                "report for auditability only. They do not establish mission "
                "ownership, activation, branch selection, or a total Story-file "
                "order."
            ),
            "storyBranchRelatedOriginalFiles": copy.deepcopy(
                branch_related_files
            ),
            "storyBranchRelatedFilesBoundary": (
                "These hash-validated original files are cited by authored Story "
                "branch or bounded branch-validation records. They provide "
                "branch-definition context only; they do not establish mission "
                "ownership, activation, or cross-file chronology."
            ),
            "relatedOriginalFiles": related_files,
            "sourceBoundary": (
                "No MissionRuntimeAsset payload exists for this Story namespace. "
                "The page exposes exact strict source-order evidence and hashed "
                "original files only; it is not a mission or quest owner."
            ),
        },
        "nodes": [],
        "edges": [],
        "caseStudy": None,
        "missionGraph": {"upstream": {}, "downstream": {}},
        "envTalkContext": [],
        "storyOrder": story_order,
    }
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    _write_json(mission_output / f"{mission_id}.json", payload)
    summary = {
        "id": mission_id,
        "nameKey": "",
        "levelId": payload["mission"]["levelId"],
        "questCount": 0,
        "mainPathCount": 0,
        "entryCount": 0,
        "fanoutCount": 0,
        "multiPrevJoinCount": 0,
        "activeJoinCount": 0,
        "exactFinishCount": 0,
        "serverPlaceholderCount": 0,
        "serverPlaceholderQuestCount": 0,
        "failureConditionCount": 0,
        "externalDependencyCount": 0,
        "submitItemConditionCount": 0,
        "submitItemQuestCount": 0,
        "submitItemDialogCoGateCount": 0,
        "submitItemLevelScriptCoGateCount": 0,
        "nativeRuntimeBindingCount": 0,
        "activityStageHostCount": 0,
        "activityStageHostedQuestCount": 0,
        "trackingInfoCount": 0,
        "trackingObjectiveCount": 0,
        "missionPropertyCount": 0,
        "conditionTypes": [],
        "caseStudy": False,
        "file": f"missions/{mission_id}.json",
        "sourceOrderShell": True,
        "sourceOrderRelatedFileCount": len(related_files),
        "storyBranchRelatedFileCount": len(branch_related_files),
    }
    story_order_projection.update_story_order_summary(summary, story_order)
    index.setdefault("missions", []).append(summary)
    return summary


def _create_story_variant_aggregate_shell(
    index: dict[str, Any],
    output_root: Path,
    order_row: dict[str, Any],
    *,
    schema_version: str,
) -> dict[str, Any]:
    """Create a non-owning shell from declared, validated Story variants.

    The rule is corpus-driven: a missing Story namespace is eligible only when
    its generated mission bundle declares variant mission bundles, every bundle
    identifies itself exactly, and every variant already has a Mission Pipeline
    payload backed by an original MissionRuntimeAsset.
    """
    mission_id = str(order_row.get("mission") or "")
    variant_sources = [
        str(value) for value in order_row.get("missionDataVariants") or [] if value
    ]
    validator = "source_story_order_publication"
    if not mission_id or not variant_sources:
        raise RuntimeError(
            f"validator={validator} gate=aggregateHasDeclaredVariants "
            f"mission={mission_id or '-'} expected=nonempty actual={variant_sources!r} "
            f"source={order_row.get('missionData') or '-'}"
        )
    summaries = {
        str(row.get("id") or ""): row
        for row in index.get("missions") or []
        if isinstance(row, dict) and row.get("id")
    }
    variant_ids: list[str] = []
    related_files: list[dict[str, Any]] = []
    level_ids: set[str] = set()
    for variant_source in variant_sources:
        generated_path = _resolve_report_source_path(variant_source)
        generated = _read_json(generated_path) if generated_path.is_file() else None
        variant_id = str((generated or {}).get("mission") or "")
        if not variant_id:
            raise RuntimeError(
                f"validator={validator} gate=variantBundleIdentifiesMission "
                f"mission={mission_id} expected=mission-id actual={variant_id or '-'} "
                f"source={generated_path}"
            )
        variant_summary = summaries.get(variant_id)
        if not variant_summary:
            raise RuntimeError(
                f"validator={validator} gate=declaredVariantHasPipelineMission "
                f"mission={mission_id} expected={variant_id!r} actual=missing "
                f"source={generated_path}"
            )
        pipeline_path = output_root / str(variant_summary.get("file") or "")
        pipeline_payload = _read_json(pipeline_path) if pipeline_path.is_file() else None
        original_source = str(((pipeline_payload or {}).get("mission") or {}).get("source") or "")
        original_path = _resolve_report_source_path(original_source) if original_source else Path()
        if not original_source or not original_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=variantHasOriginalMissionRuntime "
                f"mission={mission_id} variant={variant_id} expected=file actual={original_source or '-'} "
                f"source={pipeline_path}"
            )
        related_files.append({
            "kind": "original_mission_runtime",
            "sourceFile": _repo_path(original_path),
            "sha256": _sha256_path(original_path),
            "relationship": "declared_story_graph_variant_context",
            "variantMissionId": variant_id,
        })
        variant_ids.append(variant_id)
        if variant_summary.get("levelId"):
            level_ids.add(str(variant_summary["levelId"]))

    variant_ids = sorted(set(variant_ids), key=_natural_quest_key)
    related_files.sort(key=lambda row: (_natural_quest_key(row["variantMissionId"]), row["sourceFile"]))
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": schema_version,
        "mission": {
            "id": mission_id,
            "nameKey": "",
            "descriptionKey": "",
            "levelId": next(iter(level_ids)) if len(level_ids) == 1 else "",
            "missionType": None,
            "rewardId": "",
            "mainPath": [],
            "entryQuestIds": [],
            "nativeRuntimeBindings": [],
            "source": str(order_row.get("missionData") or ""),
            "storyAggregateShell": True,
            "variantMissionIds": variant_ids,
            "relatedOriginalFiles": related_files,
            "sourceBoundary": (
                "This Story namespace aggregates exact serialized Story and LevelScript "
                "evidence across its declared mission variants. It is not itself a "
                "MissionRuntimeAsset and does not prove mission ownership, quest ownership, "
                "branch selection, or chronology beyond the attached typed evidence."
            ),
        },
        "nodes": [],
        "edges": [],
        "caseStudy": None,
        "missionGraph": {"upstream": {}, "downstream": {}},
        "envTalkContext": [],
        "storyOrder": copy.deepcopy(order_row),
    }
    _write_json(mission_output / f"{mission_id}.json", payload)
    summary = {
        "id": mission_id,
        "nameKey": "",
        "levelId": payload["mission"]["levelId"],
        "questCount": 0,
        "mainPathCount": 0,
        "entryCount": 0,
        "fanoutCount": 0,
        "multiPrevJoinCount": 0,
        "activeJoinCount": 0,
        "exactFinishCount": 0,
        "serverPlaceholderCount": 0,
        "serverPlaceholderQuestCount": 0,
        "failureConditionCount": 0,
        "externalDependencyCount": 0,
        "submitItemConditionCount": 0,
        "submitItemQuestCount": 0,
        "submitItemDialogCoGateCount": 0,
        "submitItemLevelScriptCoGateCount": 0,
        "nativeRuntimeBindingCount": 0,
        "activityStageHostCount": 0,
        "activityStageHostedQuestCount": 0,
        "trackingInfoCount": 0,
        "trackingObjectiveCount": 0,
        "missionPropertyCount": 0,
        "conditionTypes": [],
        "caseStudy": False,
        "file": f"missions/{mission_id}.json",
        "storyAggregateShell": True,
        "storyAggregateVariantCount": len(variant_ids),
    }
    story_order_projection.update_story_order_summary(summary, order_row)
    index.setdefault("missions", []).append(summary)
    return summary
