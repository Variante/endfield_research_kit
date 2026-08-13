"""Public in-process API for building the source-only Story gap queue."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import core
from .foundation import read_json, safe_key
from .report import GapReportPaths, publish_gap_report
from ..level_bindings import (
    build_levelscript_action_story_occurrences,
    build_levelscript_native_story_playback_index,
)


ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class SourceGapBuildResult:
    report: dict[str, Any]
    paths: GapReportPaths


def build_source_gap_queue(
    language: str = "CN",
    *,
    reports_dir: Path | None = None,
    table_root: Path | None = None,
    game_assembly: Path | None = None,
) -> SourceGapBuildResult:
    """Build and publish the canonical queue without spawning another Python."""
    language = str(language or "CN").upper()
    reports_dir = reports_dir or ROOT / "reports" / "mission_order"
    table_root = table_root or (
        ROOT / "export_full" / "structured" / "StreamingAssets" / "Table"
    )

    partial_report = core.build_partial_order_report(language)
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
        mission_payloads[mission] = core.load_mission_payload_with_variants(
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
        core.project_authored_story_content_keys(
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
        core.load_story_trigger_manifest_evidence(coverage_path, language)
    )
    offline_exhaustion_index, offline_exhaustion_status = (
        core.build_offline_exhaustion_index(
            partial_report,
            table_root,
            game_assembly_path=game_assembly,
            native_playback_index=native_playback_index,
            action_story_occurrences=action_story_occurrences,
        )
    )
    quest_index, quest_status = core.build_quest_attachment_diagnostic_index(
        mission_payloads
    )
    general_index, general_status = (
        core.build_general_quest_attachment_boundary_index(
            partial_report,
            mission_payloads,
            native_playback_index,
        )
    )
    quest_index.update(general_index)
    quest_status["genericQuestAttachmentBoundaries"] = general_status
    quest_status["validatedQuestIds"] = sorted(
        quest_index,
        key=core.natural_key,
    )
    general_failures = general_status.get("validationFailures") or []
    if general_failures:
        quest_status.setdefault("validationFailureDetails", []).extend(
            general_failures
        )
        quest_status["status"] = "inactive_generated_shape_validation_failed"

    report = core.build_gap_report(
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
    )
    return SourceGapBuildResult(
        report=report,
        paths=publish_gap_report(report, reports_dir, language),
    )
