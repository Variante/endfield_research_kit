"""Public in-process API for building the source-only Story gap queue."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.webui.story.mission_recovery import natural_key
from scripts.webui.story.source_story_partial_order import (
    build_report as build_partial_order_report,
    _NativeProofScope,
    load_mission_payload_with_variants,
)
from scripts.webui.story.source_gap.attachment_evidence import (
    build_general_quest_attachment_boundary_index,
    build_quest_attachment_diagnostic_index,
    load_story_trigger_manifest_evidence,
)
from scripts.webui.story.source_gap.content_evidence import project_authored_story_content_keys
from scripts.webui.story.source_gap.foundation import read_json, safe_key
from scripts.webui.story.source_gap.model import build_gap_report
from scripts.webui.story.source_gap.offline_evidence import build_offline_exhaustion_index
from scripts.webui.story.source_gap.report import GapReportPaths, publish_gap_report
from scripts.webui.story.level_bindings import (
    build_levelscript_action_story_occurrences,
    build_levelscript_native_story_playback_index,
)


from scripts.repo_paths import REPO_ROOT
from scripts.common import EXPORT_LAYOUT, rel_path as export_rel_path

ROOT = REPO_ROOT


@dataclass(frozen=True)
class SourceGapBuildResult:
    report: dict[str, Any]
    paths: GapReportPaths


def _build_source_gap_report(
    language: str = "CN",
    *,
    table_root: Path | None = None,
    game_assembly: Path | None = None,
    native_scope=None,
) -> dict[str, Any]:
    """Construct the queue under its caller-owned native proof scope."""
    language = str(language or "CN").upper()
    table_root = table_root or (ROOT / export_rel_path(EXPORT_LAYOUT.table_dir))

    partial_report = build_partial_order_report(language)
    action_story_occurrences = build_levelscript_action_story_occurrences()
    native_playback_index = build_levelscript_native_story_playback_index()
    mission_dir = ROOT / "webui" / "data" / "lang" / language / "mission"
    language_dir = mission_dir.parent
    mission_payloads: dict[str, dict[str, Any]] = {}
    mission_bundle_presence: set[str] = set()
    for partial_row in partial_report.get("missions") or []:
        mission = safe_key(partial_row.get("mission"))
        path = mission_dir / f"{mission}.json"
        if not path.is_file():
            continue
        mission_payloads[mission] = load_mission_payload_with_variants(
            mission_dir,
            mission,
        )
        mission_bundle_presence.add(mission)
    for path in sorted(mission_dir.glob("*.json")):
        mission = path.stem
        if mission in mission_payloads:
            continue
        payload = read_json(path, {})
        if isinstance(payload, dict):
            mission_payloads[mission] = payload

    project_authored_content, project_authored_status = (
        project_authored_story_content_keys(
            read_json(language_dir / "index.json", {}),
            language_dir / "conv",
        )
    )
    coverage_path = (
        ROOT
        / "reports"
        / "story"
        / "build"
        / f"mission_pipeline_story_binding_coverage_{language}.json"
    )
    story_trigger_manifest, story_trigger_manifest_status = (
        load_story_trigger_manifest_evidence(coverage_path, language)
    )
    offline_exhaustion_index, offline_exhaustion_status = (
        build_offline_exhaustion_index(
            partial_report,
            table_root,
            game_assembly_path=game_assembly,
            native_playback_index=native_playback_index,
            action_story_occurrences=action_story_occurrences,
            native_scope=native_scope,
        )
    )
    quest_index, quest_status = build_quest_attachment_diagnostic_index(
        mission_payloads
    )
    # Receipt for the actual source-bound rows, before independently validated
    # generic boundaries are merged. A stale source contract contributes none.
    offline_exhaustion_status["sourceBoundEvidenceRowCount"] = len(
        offline_exhaustion_index
    )
    quest_status["sourceBoundEvidenceRowCount"] = len(quest_index)
    general_index, general_status = (
        build_general_quest_attachment_boundary_index(
            partial_report,
            mission_payloads,
            native_playback_index,
        )
    )
    quest_index.update(general_index)
    quest_status["genericQuestAttachmentBoundaries"] = general_status
    quest_status["validatedQuestIds"] = sorted(
        quest_index,
        key=natural_key,
    )
    general_failures = general_status.get("validationFailures") or []
    if general_failures:
        quest_status.setdefault("validationFailureDetails", []).extend(
            general_failures
        )
        quest_status["status"] = "inactive_generated_shape_validation_failed"

    report = build_gap_report(
        partial_report,
        mission_payloads,
        mission_bundle_presence,
        native_playback_index,
        action_story_occurrences,
        table_root=table_root,
        offline_exhaustion_index=offline_exhaustion_index,
        offline_exhaustion_status=offline_exhaustion_status,
        quest_attachment_diagnostic_index=quest_index,
        quest_attachment_diagnostic_status=quest_status,
        story_trigger_manifest=story_trigger_manifest,
        story_trigger_manifest_status=story_trigger_manifest_status,
        project_authored_content=project_authored_content,
        project_authored_status=project_authored_status,
        native_scope=native_scope,
    )
    return report


def build_source_gap_queue(language="CN", *, reports_dir=None, table_root=None, game_assembly=None):
    """Build one source gap report; recheck native evidence before publication."""
    language = str(language or "CN").upper()
    reports_dir = reports_dir or ROOT / "reports" / "mission_order"
    scope = _NativeProofScope()
    try:
        report = _build_source_gap_report(language, table_root=table_root,
            game_assembly=game_assembly, native_scope=scope)
        scope.finish()
    finally:
        scope._closed = True
    return SourceGapBuildResult(report, publish_gap_report(report, reports_dir, language))
