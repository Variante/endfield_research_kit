"""Publish validated source Story order into Mission Pipeline payloads."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

if __package__ and __package__.startswith("scripts."):
    from scripts.common import write_report_json, write_text_if_changed
    from scripts.story_builder.source_story_partial_order import (
        build_report as build_source_story_partial_order_report,
        render_markdown as render_source_story_partial_order_markdown,
    )
    from scripts.story_builder.source_story_order_cross_reference import (
        build_report as build_source_story_order_cross_reference_report,
        render_markdown as render_source_story_order_cross_reference_markdown,
    )
else:
    from common import write_report_json, write_text_if_changed
    from story_builder.source_story_partial_order import (
        build_report as build_source_story_partial_order_report,
        render_markdown as render_source_story_partial_order_markdown,
    )
    from story_builder.source_story_order_cross_reference import (
        build_report as build_source_story_order_cross_reference_report,
        render_markdown as render_source_story_order_cross_reference_markdown,
    )

from . import story_order_projection
from . import source_order_shells


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


def _serialized_branch_story_keys(value: Any) -> set[str]:
    """Collect only Story keys carried by serialized Branch playback records.

    The native Branch inventory is deliberately a typed, corpus-wide census.  A
    mission projection may use it only when the exact Story key is present on a
    playback arm (including nested typed controls); arbitrary strings such as
    action names, level ids, and file paths are not candidates.
    """
    keys: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for field in ("playbackStoryKeys", "storyKeys"):
                values = node.get(field)
                if isinstance(values, str) and values:
                    keys.add(values)
                elif isinstance(values, list):
                    keys.update(
                        str(item) for item in values
                        if isinstance(item, str) and item
                    )
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return keys


def _serialized_branch_controls(value: Any) -> list[dict[str, Any]]:
    """Return nested typed controls without relying on a control-name allowlist."""
    controls: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if (
                isinstance(node.get("arms"), list)
                and ("controlKind" in node or "controlRuntimeMappingId" in node)
            ):
                controls.append(node)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return controls


def attach_serialized_branch_story_contexts(
    order_row: dict[str, Any],
    inventory_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Project exact serialized Branch/Story intersections into one mission row.

    This is intentionally a projection, not an ownership or chronology rule:
    the only admission gate is an exact Story key shared by the mission's
    serialized Story nodes and the original LevelScript Branch census.  The
    complete typed row and its original-file evidence remain attached so the
    WebUI can show the unresolved native context without inventing a route.
    """
    projected = copy.deepcopy(order_row)
    inventory_rows = [
        row for row in inventory_rows
        if isinstance(row, dict)
    ]
    if not inventory_rows:
        return projected
    mission_story_keys = {
        str(node if isinstance(node, str) else node.get("key") or "")
        for node in order_row.get("nodes") or []
        if (isinstance(node, str) and node) or (isinstance(node, dict) and node.get("key"))
    }
    contexts: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    context_story_keys: set[str] = set()
    related_source_files: set[str] = set()
    multi_playback_count = 0

    for source_row in inventory_rows:
        serialized_story_keys = _serialized_branch_story_keys(source_row)
        mission_keys = serialized_story_keys & mission_story_keys
        if not mission_keys:
            continue
        dedupe_hash = str(source_row.get("sha256") or "")
        if not dedupe_hash:
            dedupe_hash = "|".join(
                sorted(
                    str(value).replace("\\", "/")
                    for value in source_row.get("sourceFiles") or []
                    if value
                )
            )
        dedupe_key = (
            dedupe_hash,
            str(source_row.get("branchLocalId") or ""),
            tuple(sorted(mission_keys)),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        context = copy.deepcopy(source_row)
        context["relation"] = "serialized_branch_story_context"
        context["missionStoryKeys"] = sorted(mission_keys)
        context["externalStoryKeys"] = sorted(serialized_story_keys - mission_story_keys)
        context["ownership"] = False
        context["orderEvidence"] = False
        context["contextEvidenceBoundary"] = (
            "Exact serialized Branch playback keys intersect this mission's Story "
            "nodes. The original LevelScript, GameAssembly, and metadata files are "
            "attached for inspection; this context does not prove mission ownership, "
            "activation, arm exclusivity, or Story file order."
        )
        contexts.append(context)
        context_story_keys.update(mission_keys)
        related_source_files.update(
            str(related.get("sourceFile") or "")
            for related in source_row.get("relatedOriginalFiles") or []
            if isinstance(related, dict) and related.get("sourceFile")
        )
        multi_playback_count += int(
            int(source_row.get("playbackArmCount") or 0) > 1
        )
        multi_playback_count += sum(
            1
            for control in _serialized_branch_controls(source_row)
            if control.get("branchingStatus") == "multi_playback_arms"
        )

    contexts.sort(
        key=lambda row: (
            str(row.get("levelId") or ""),
            str(row.get("scriptId") or ""),
            str(row.get("branchLocalId") or ""),
            str(row.get("sha256") or ""),
            tuple(row.get("missionStoryKeys") or []),
        )
    )
    branches = projected.setdefault("branches", {})
    branches["nativeSerializedBranchContexts"] = contexts
    branches["nativeSerializedBranchContextEvidenceBoundary"] = (
        "These rows are exact serialized Branch playback contexts projected by Story "
        "key intersection. They retain original-file hashes but are not mission "
        "ownership, activation, arm exclusivity, or chronology evidence."
    )
    summary = projected.setdefault("summary", {})
    summary["nativeSerializedBranchContextCount"] = len(contexts)
    summary["nativeSerializedBranchContextStoryCount"] = len(context_story_keys)
    summary["nativeSerializedBranchContextMultiPlaybackCount"] = multi_playback_count
    summary["nativeSerializedBranchContextRelatedFileCount"] = len(related_source_files)
    return projected


def publish_source_story_partial_order(
    index: dict[str, Any],
    output_root: Path,
    story_data_root: Path,
    language: str,
    report_root: Path,
    *,
    schema_version: str,
    story_order_override_path: Path,
    story_order_ocr_path: Path,
    callserver_callback_audit: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Publish strict Story ordering evidence into lazy mission payloads."""
    story_index = story_data_root / language / "index.json"
    if not story_index.is_file():
        return None
    state_contract = (
        (index.get("runtimeContract") or {}).get("stateUpdateApplicationAudit")
        or {}
    )
    quest_succeed_contract = dict(
        state_contract.get("questSucceedActionApplication") or {}
    )
    quest_succeed_contract["relatedOriginalFiles"] = (
        state_contract.get("relatedOriginalFiles") or []
    )
    extra_thread_contract = (
        (index.get("runtimeContract") or {}).get(
            "actionExtraThreadSchedulerAudit"
        )
        or {}
    )
    report = build_source_story_partial_order_report(
        language,
        story_data_root=story_data_root,
        quest_succeed_lifecycle_contract=quest_succeed_contract,
        extra_thread_scheduler_contract=extra_thread_contract,
        callserver_callback_audit=callserver_callback_audit,
    )
    quest_start = state_contract.get("questStartApplication") or {}
    topology_consumers = state_contract.get("questTopologyFieldConsumers") or {}
    quest_fork_authority = {
        "classification": "server_selected_start_topology_only",
        "questInfoType": quest_start.get("questInfoType"),
        "questInfoFieldOffsets": quest_start.get("questInfoFieldOffsets") or {},
        "fieldReadCounts": quest_start.get("fieldReadCounts") or {},
        "topologyTraversalCalls": quest_start.get("topologyTraversalCalls") or [],
        "startQuest": quest_start.get("startQuest") or {},
        "sourceMessages": quest_start.get("sourceMessages") or [],
        "topologyFieldConsumers": topology_consumers,
        "finding": quest_start.get("finding") or "",
        "boundary": quest_start.get("boundary") or "",
        "relatedOriginalFiles": state_contract.get("relatedOriginalFiles") or [],
        "validation": quest_start.get("validation") or {},
    }
    semantic_forks_by_id: dict[str, dict[str, Any]] = {}
    for mission_summary in index.get("missions") or []:
        if not isinstance(mission_summary, dict):
            continue
        semantic_path = output_root / str(mission_summary.get("file") or "")
        semantic_payload = (
            _read_json(semantic_path) if semantic_path.is_file() else {}
        )
        for fork in (
            (semantic_payload.get("questTopology") or {}).get("forks") or []
        ):
            if not isinstance(fork, dict) or not fork.get("questId"):
                continue
            quest_id = str(fork["questId"])
            existing = semantic_forks_by_id.get(quest_id)
            if existing and existing != fork:
                raise RuntimeError(
                    "validator=quest_fork_semantics_publication "
                    "gate=globallyUniqueQuestForkId "
                    f"quest={quest_id} expected=unique actual=duplicate "
                    f"source={semantic_path}"
                )
            semantic_forks_by_id[quest_id] = fork
    for row in report.get("missions") or []:
        if not isinstance(row, dict):
            continue
        branches = row.get("branches") or {}
        if branches.get("questForks"):
            branches["questForkAuthority"] = quest_fork_authority
            missing_semantics = [
                str(fork.get("questId") or "")
                for fork in branches["questForks"]
                if isinstance(fork, dict)
                and str(fork.get("questId") or "") not in semantic_forks_by_id
            ]
            if missing_semantics:
                raise RuntimeError(
                    "validator=quest_fork_semantics_publication "
                    "gate=allStoryOrderForksHaveSemantics "
                    f"mission={row.get('mission') or '-'} "
                    "expected=[] "
                    f"actual={missing_semantics!r} "
                    f"source={output_root / 'missions'}"
                )
            branches["questForks"] = [
                semantic_forks_by_id[str(fork.get("questId") or "")]
                for fork in branches["questForks"]
                if isinstance(fork, dict)
            ]
    report_root.mkdir(parents=True, exist_ok=True)
    report_json = report_root / f"source_story_partial_order_{language}.json"
    report_markdown = report_root / f"source_story_partial_order_{language}.md"
    write_report_json(report_json, report)
    write_text_if_changed(
        report_markdown,
        render_source_story_partial_order_markdown(report),
    )

    order_cross_reference = build_source_story_order_cross_reference_report(
        report,
        _read_json(story_order_override_path)
        if story_order_override_path.is_file()
        else {},
        _read_json(story_order_ocr_path)
        if story_order_ocr_path.is_file()
        else {},
    )
    cross_reference_json = (
        report_root / f"source_story_order_cross_reference_{language}.json"
    )
    cross_reference_markdown = (
        report_root / f"source_story_order_cross_reference_{language}.md"
    )
    order_cross_reference["reportJson"] = _repo_path(cross_reference_json)
    order_cross_reference["reportMarkdown"] = _repo_path(cross_reference_markdown)
    write_report_json(cross_reference_json, order_cross_reference)
    write_text_if_changed(
        cross_reference_markdown,
        render_source_story_order_cross_reference_markdown(order_cross_reference),
    )

    publication = attach_source_story_partial_order(
        index,
        output_root,
        report,
        create_variant_aggregate_shells=False,
        require_complete_branch_publication=False,
        order_cross_reference=order_cross_reference,
        schema_version=schema_version,
    )

    order_summary = report.get("summary") or {}
    index["storyOrder"] = {
        "schema": report.get("_schema"),
        "language": language,
        "summary": order_summary,
        "nativeSerializedBranchInventory": copy.deepcopy(
            report.get("nativeSerializedBranchInventory") or {}
        ),
        "evidencePolicy": report.get("evidencePolicy") or {},
        "reportJson": _repo_path(report_json),
        "reportMarkdown": _repo_path(report_markdown),
        "publication": publication,
        "crossReference": (
            story_order_projection.compact_story_order_cross_reference_index(
                order_cross_reference
            )
        ),
    }
    _write_json(output_root / "index.json", index)
    return report


def _compact_source_story_gap_queue_row(
    row: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    """Publish review classifications without turning the queue into evidence."""
    scene_key_lists = (
        "coreIsolatedSceneKeys",
        "actionableCoreIsolatedSceneKeys",
        "actionableWeakOnlySceneKeys",
        "nonActionableWeakOnlySceneKeys",
    )
    closed_row_lists = (
        "closedExactNativeIsolatedScenes",
        "closedExactSystemSelectorIsolatedScenes",
        "closedExactRuntimeConfigIsolatedScenes",
        "closedDefinitionOnlyIsolatedScenes",
        "closedNonMissionContentIsolatedScenes",
        "deferredOfflineExhaustedIsolatedScenes",
    )
    compact: dict[str, Any] = {
        "mission": str(row.get("mission") or ""),
        "status": "recovery_queue_only",
        "graphEffect": "none",
        "source": source,
        "metrics": {
            key: value
            for key, value in (row.get("metrics") or {}).items()
            if key in {
                "sceneCount",
                "isolatedScenes",
                "coreIsolatedScenes",
                "actionableCoreIsolatedScenes",
                "weakOnlyScenes",
                "actionableWeakOnlyScenes",
            }
        },
        "evidenceBoundary": (
            "This compact row is a recovery-priority classification only. It "
            "does not add mission ownership, activation, playback, or Story-order "
            "edges."
        ),
    }
    for key in scene_key_lists:
        compact[key] = [str(value) for value in row.get(key) or [] if value]
    for key in closed_row_lists:
        compact[key] = [
            {
                field: value
                for field, value in item.items()
                if field in {
                    "sceneKey",
                    "recoveryStatus",
                    "relation",
                    "evidenceKind",
                }
            }
            for item in row.get(key) or []
            if isinstance(item, dict) and item.get("sceneKey")
        ]
    return compact


def attach_source_story_partial_order(
    index: dict[str, Any],
    output_root: Path,
    report: dict[str, Any],
    *,
    create_variant_aggregate_shells: bool,
    require_complete_branch_publication: bool,
    order_cross_reference: dict[str, Any] | None = None,
    source_gap_queue: dict[str, Any] | None = None,
    schema_version: str,
) -> dict[str, Any]:
    """Attach every recovered row that has a validated pipeline destination."""
    rows_by_mission = {
        str(row.get("mission") or ""): row
        for row in report.get("missions") or []
        if isinstance(row, dict) and row.get("mission")
    }
    existing_ids = {
        str(row.get("id") or "")
        for row in index.get("missions") or []
        if isinstance(row, dict)
    }
    aggregate_shells: list[str] = []
    published_source_order_shells: list[str] = []
    story_branch_shells: list[str] = []
    source_order_hash_cache: dict[Path, str] = {}
    if create_variant_aggregate_shells:
        for mission_id, order_row in sorted(rows_by_mission.items()):
            branch_count = len(
                ((order_row.get("branches") or {}).get("nativeControlBranches") or [])
            )
            if mission_id in existing_ids:
                continue
            if order_row.get("missionDataVariants") and branch_count:
                source_order_shells._create_story_variant_aggregate_shell(
                    index,
                    output_root,
                    order_row,
                    schema_version=schema_version,
                )
                existing_ids.add(mission_id)
                aggregate_shells.append(mission_id)
                continue
            if source_order_shells._source_order_shell_candidate(
                order_row,
                hash_cache=source_order_hash_cache,
            ):
                source_order_shells._create_source_order_shell(
                    index,
                    output_root,
                    order_row,
                    hash_cache=source_order_hash_cache,
                    schema_version=schema_version,
                )
                existing_ids.add(mission_id)
                published_source_order_shells.append(mission_id)
                continue
            if source_order_shells._story_branch_shell_candidate(
                order_row,
                hash_cache=source_order_hash_cache,
            ):
                source_order_shells._create_story_branch_shell(
                    index,
                    output_root,
                    order_row,
                    hash_cache=source_order_hash_cache,
                    schema_version=schema_version,
                )
                existing_ids.add(mission_id)
                story_branch_shells.append(mission_id)

    published_missions: list[str] = []
    published_branches = 0
    source_order_related_file_missions: list[str] = []
    source_order_related_file_rows = 0
    source_order_related_distinct_files: set[str] = set()
    story_branch_related_file_missions: list[str] = []
    story_branch_related_file_rows = 0
    story_branch_related_distinct_files: set[str] = set()
    cross_reference_by_mission = {
        str(row.get("mission") or ""): row
        for row in (order_cross_reference or {}).get("missions") or []
        if isinstance(row, dict) and row.get("mission")
    }
    source_gap_by_mission = {
        str(row.get("mission") or ""): row
        for row in (source_gap_queue or {}).get("missions") or []
        if isinstance(row, dict) and row.get("mission")
    }
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        order_row = rows_by_mission.get(mission_id)
        mission_path = output_root / str(summary.get("file") or "")
        if not order_row or not mission_path.is_file():
            continue
        payload = _read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        inventory_rows = (
            (report.get("nativeSerializedBranchInventory") or {}).get("rows") or []
        )
        published_order = attach_serialized_branch_story_contexts(
            order_row,
            inventory_rows,
        )
        previous_order = payload.get("storyOrder") or {}
        source_gap_row = source_gap_by_mission.get(mission_id)
        if source_gap_row:
            published_order["sourceGapQueue"] = (
                _compact_source_story_gap_queue_row(
                    source_gap_row,
                    str((source_gap_queue or {}).get("reportJson") or ""),
                )
            )
        elif previous_order.get("sourceGapQueue"):
            published_order["sourceGapQueue"] = previous_order["sourceGapQueue"]
        if previous_order.get("sourceOrderShell"):
            published_order["sourceOrderShell"] = True
            published_order["sourceOrderShellBoundary"] = str(
                previous_order.get("sourceOrderShellBoundary") or ""
            )
        if previous_order.get("storyBranchShell"):
            published_order["storyBranchShell"] = True
            published_order["storyBranchShellBoundary"] = str(
                previous_order.get("storyBranchShellBoundary") or ""
            )
        mission_source = str(
            (payload.get("mission") or {}).get("source") or ""
        )
        additional_source_files = (
            [mission_source]
            if "MissionRuntimeAsset/" in mission_source.replace("\\", "/")
            else []
        )
        related_files = source_order_shells._source_order_shell_related_files(
            order_row,
            hash_cache=source_order_hash_cache,
            additional_files=additional_source_files,
        )
        branch_related_files = source_order_shells._story_branch_related_original_files(
            order_row,
            hash_cache=source_order_hash_cache,
        )
        if related_files:
            related_boundary = (
                "These original files are attached to the strict source-order "
                "report for auditability only. They do not establish mission "
                "ownership, activation, branch selection, or a total Story-file "
                "order."
            )
            published_order["sourceOrderRelatedOriginalFiles"] = copy.deepcopy(
                related_files
            )
            published_order["sourceOrderRelatedFilesBoundary"] = related_boundary
            mission_data = payload.setdefault("mission", {})
            mission_data["sourceOrderRelatedOriginalFiles"] = copy.deepcopy(
                related_files
            )
            mission_data["sourceOrderRelatedFilesBoundary"] = related_boundary
            summary["sourceOrderRelatedFileCount"] = len(related_files)
            source_order_related_file_missions.append(mission_id)
            source_order_related_file_rows += len(related_files)
            source_order_related_distinct_files.update(
                str(row.get("sourceFile") or "")
                for row in related_files
                if row.get("sourceFile")
            )
        if branch_related_files:
            branch_related_boundary = (
                "These hash-validated original files are cited by authored Story "
                "branch or bounded branch-validation records. They provide "
                "branch-definition context only; they do not establish mission "
                "ownership, activation, or cross-file chronology."
            )
            published_order["storyBranchRelatedOriginalFiles"] = copy.deepcopy(
                branch_related_files
            )
            published_order["storyBranchRelatedFilesBoundary"] = (
                branch_related_boundary
            )
            mission_data = payload.setdefault("mission", {})
            mission_data["storyBranchRelatedOriginalFiles"] = copy.deepcopy(
                branch_related_files
            )
            mission_data["storyBranchRelatedFilesBoundary"] = (
                branch_related_boundary
            )
            summary["storyBranchRelatedFileCount"] = len(branch_related_files)
            story_branch_related_file_missions.append(mission_id)
            story_branch_related_file_rows += len(branch_related_files)
            story_branch_related_distinct_files.update(
                str(row.get("sourceFile") or "")
                for row in branch_related_files
                if row.get("sourceFile")
            )
        cross_reference_row = cross_reference_by_mission.get(mission_id)
        if cross_reference_row is not None:
            cross_reference_payload = (
                story_order_projection.compact_story_order_cross_reference(
                    cross_reference_row,
                    order_cross_reference or {},
                )
            )
            published_order["crossReference"] = cross_reference_payload
            order_summary = published_order.setdefault("summary", {})
            order_summary["crossReferenceStrictEdgeCount"] = int(
                cross_reference_payload.get("strictEdgeCount") or 0
            )
            order_summary["crossReferenceOverrideDisagreeCount"] = int(
                (cross_reference_payload.get("override") or {}).get(
                    "disagrees"
                )
                or 0
            )
            order_summary["crossReferenceOcrDisagreeCount"] = int(
                (cross_reference_payload.get("ocr") or {}).get("disagrees")
                or 0
            )
            order_summary["crossReferenceConflictCount"] = int(
                cross_reference_payload.get("conflictCount") or 0
            )
        elif isinstance(previous_order.get("crossReference"), dict):
            # The canonical builder publishes the order once before coverage
            # attachment and once after it. Preserve the full per-mission
            # diagnostic comparison on the second pass; it is deliberately
            # not reconstructed from the compact global index summary.
            published_order["crossReference"] = copy.deepcopy(
                previous_order["crossReference"]
            )
        payload["storyOrder"] = published_order
        _write_json(mission_path, payload)
        story_order_projection.update_story_order_summary(
            summary,
            published_order,
        )
        published_missions.append(mission_id)
        published_branches += len(
            ((order_row.get("branches") or {}).get("nativeControlBranches") or [])
        )

    expected_branches = sum(
        len(((row.get("branches") or {}).get("nativeControlBranches") or []))
        for row in rows_by_mission.values()
    )
    missing_branch_missions = [
        mission_id
        for mission_id, row in sorted(rows_by_mission.items())
        if ((row.get("branches") or {}).get("nativeControlBranches") or [])
        and mission_id not in published_missions
    ]
    publication = {
        "validator": "source_story_order_publication",
        "status": "validated" if not missing_branch_missions else "incomplete",
        "expectedNativeBranchPlacements": expected_branches,
        "publishedNativeBranchPlacements": published_branches,
        "unpublishedNativeBranchPlacements": expected_branches - published_branches,
        "publishedMissionRows": len(published_missions),
        "variantAggregateShells": aggregate_shells,
        "sourceOrderShells": published_source_order_shells,
        "storyBranchShells": story_branch_shells,
        "sourceOrderRelatedFileMissions": source_order_related_file_missions,
        "sourceOrderRelatedFileRows": source_order_related_file_rows,
        "sourceOrderRelatedDistinctFiles": len(source_order_related_distinct_files),
        "storyBranchRelatedFileMissions": story_branch_related_file_missions,
        "storyBranchRelatedFileRows": story_branch_related_file_rows,
        "storyBranchRelatedDistinctFiles": len(story_branch_related_distinct_files),
        "missingBranchMissions": missing_branch_missions,
    }
    index.setdefault("counts", {})["missions"] = len(index.get("missions") or [])
    index["counts"]["sourceOrderMissionShells"] = len(
        published_source_order_shells
    )
    index["counts"]["storyBranchMissionShells"] = len(story_branch_shells)
    index["counts"]["sourceOrderRelatedFileMissions"] = len(
        source_order_related_file_missions
    )
    index["counts"]["sourceOrderRelatedFileRows"] = source_order_related_file_rows
    index["counts"]["sourceOrderRelatedDistinctFiles"] = len(
        source_order_related_distinct_files
    )
    index["counts"]["storyBranchRelatedFileMissions"] = len(
        story_branch_related_file_missions
    )
    index["counts"]["storyBranchRelatedFileRows"] = story_branch_related_file_rows
    index["counts"]["storyBranchRelatedDistinctFiles"] = len(
        story_branch_related_distinct_files
    )
    index.setdefault("storyOrder", {})["publication"] = publication
    index.setdefault("counts", {})["storyVariantAggregateShells"] = len(
        [row for row in index.get("missions") or [] if row.get("storyAggregateShell")]
    )
    index["counts"]["missions"] = len(index.get("missions") or [])
    index["missions"].sort(key=lambda row: _natural_quest_key(str(row.get("id") or "")))
    if require_complete_branch_publication and missing_branch_missions:
        first = missing_branch_missions[0]
        row = rows_by_mission[first]
        actual = len(
            ((row.get("branches") or {}).get("nativeControlBranches") or [])
        )
        raise RuntimeError(
            "validator=source_story_order_publication "
            "gate=allRecoveredNativeBranchesPublished "
            f"mission={first} expected={actual} actual=0 "
            f"source={row.get('missionData') or '-'}"
        )
    _write_json(output_root / "index.json", index)
    return publication
