"""Project graph-neutral offline recovery rows onto the Story manifest."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import offline_shell_projection


ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _repo_path(path: Path) -> str:
    path = path.resolve()
    return (
        path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else path.as_posix()
    )


def publish_offline_story_recovery(
    story_trigger_manifest: dict[str, dict[str, Any]],
    gap_queue_path: Path | None,
    *,
    source_story_gap_queue_schema: str,
) -> dict[str, Any]:
    """Attach fail-closed offline recovery boundaries without adding routes.

    The source-story gap queue is a recovery worklist, not graph evidence.
    Only its exact current schema and active, graph-neutral evidence block are
    accepted. Published rows annotate existing manifest records. Story kinds
    outside the coverage denominator are emitted in a separate overlay with an
    explicit denominator-neutral status. Neither path changes an existing
    ``attachmentStatus`` nor adds trigger routes.
    """
    inactive = {
        "status": "unavailable",
        "schema": "",
        "mappingId": "",
        "graphEffect": "none",
        "publishedStoryKeys": 0,
        "publishedRuntimeContextStoryKeys": 0,
        "publishedProjectAuthoredStoryKeys": 0,
        "outsidePipelineCoverageStoryKeys": 0,
        "storyTriggerManifestOverlay": {},
        "questAttachmentDiagnosticStatus": "unavailable",
        "questAttachmentDiagnosticMappingId": "",
        "questAttachmentDiagnostics": {},
        "source": _repo_path(gap_queue_path) if gap_queue_path else "",
    }
    if gap_queue_path is None or not gap_queue_path.is_file():
        return inactive
    payload = _read_json(gap_queue_path)
    if not isinstance(payload, dict):
        return inactive
    schema = str(payload.get("_schema") or "")
    status = payload.get("offlineExhaustionEvidence")
    if (
        schema != source_story_gap_queue_schema
        or not isinstance(status, dict)
        or status.get("status") != "active"
        or status.get("graphEffect") != "none"
        or status.get("sourceHashMismatches")
    ):
        return {
            **inactive,
            "schema": schema,
            "status": "rejected_stale_or_incompatible",
        }

    published = 0
    published_keys: set[str] = set()
    published_partial_keys: set[str] = set()
    published_runtime_context_keys: set[str] = set()
    published_project_authored_keys: set[str] = set()
    manifest_overlay: dict[str, dict[str, Any]] = {}
    diagnostic_status = payload.get("questAttachmentDiagnosticEvidence")
    diagnostic_active = (
        isinstance(diagnostic_status, dict)
        and diagnostic_status.get("status") == "active"
        and diagnostic_status.get("graphEffect") == "none"
        and not diagnostic_status.get("sourceHashMismatches")
        and not diagnostic_status.get("validationFailures")
    )
    quest_attachment_diagnostics: dict[str, dict[str, Any]] = {}
    project_status = payload.get("projectAuthoredStoryEvidence")
    project_active = (
        isinstance(project_status, dict)
        and project_status.get("status") == "validated"
        and project_status.get("graphEffect") == "none"
        and not project_status.get("validationFailures")
    )
    for mission in payload.get("missions") or []:
        if not isinstance(mission, dict):
            continue
        if diagnostic_active:
            for row in mission.get("closedQuestAttachmentDiagnostics") or []:
                if not isinstance(row, dict) or row.get("graphEffect") != "none":
                    continue
                quest_id = str(row.get("questId") or "")
                if not quest_id:
                    continue
                quest_attachment_diagnostics[quest_id] = {
                    key: value
                    for key, value in row.items()
                    if key not in {"sourceHashes", "expectedSourceHashes"}
                }
        for row in mission.get("deferredOfflineExhaustedIsolatedScenes") or []:
            if not isinstance(row, dict) or row.get("graphEffect") != "none":
                continue
            story_key = str(row.get("sceneKey") or "")
            if not story_key:
                continue
            # Keep the exact negative-evidence boundary useful in the static UI
            # while dropping bulk source hashes and internal queue metrics.
            recovery = {
                key: value
                for key, value in row.items()
                if key not in {"sceneKey", "gameAssemblySha256"}
            }
            manifest_row = story_trigger_manifest.get(story_key)
            if isinstance(manifest_row, dict):
                manifest_row["offlineRecovery"] = recovery
                published += 1
                published_keys.add(story_key)
            else:
                manifest_overlay[story_key] = {
                    "key": story_key,
                    "kind": str(row.get("storyKind") or "")
                        or offline_shell_projection.offline_story_kind(story_key),
                    "nominalMissionId": str(row.get("missionId") or ""),
                    "attachmentStatus":
                        "offline_exhausted_outside_pipeline_coverage_denominator",
                    "routes": [],
                    "offlineRecovery": recovery,
                }

        for row in mission.get("partialRegisteredDialogTreeCarriers") or []:
            if (
                not isinstance(row, dict)
                or row.get("graphEffect") != "none"
                or row.get("recoveryStatus")
                != "actionable_partial_registered_dialog_tree_partition"
            ):
                continue
            story_key = str(row.get("sceneKey") or "")
            if not story_key:
                continue
            recovery = {
                key: value
                for key, value in row.items()
                if key not in {"sceneKey", "gameAssemblySha256"}
            }
            manifest_row = story_trigger_manifest.get(story_key)
            if isinstance(manifest_row, dict):
                manifest_row["partialRecovery"] = recovery
            else:
                overlay = manifest_overlay.setdefault(story_key, {
                    "key": story_key,
                    "kind": offline_shell_projection.offline_story_kind(story_key),
                    "nominalMissionId": str(row.get("missionId") or ""),
                    "attachmentStatus":
                        "partial_carrier_outside_pipeline_coverage_denominator",
                    "routes": [],
                })
                overlay["partialRecovery"] = recovery
            published_partial_keys.add(story_key)

        if project_active:
            for row in mission.get(
                "closedNonMissionContentIsolatedScenes"
            ) or []:
                if (
                    not isinstance(row, dict)
                    or row.get("evidenceKind")
                    != "project_authored_story_content"
                    or row.get("recoveryStatus")
                    != "excluded_project_authored_story_content"
                    or row.get("graphEffect") != "none"
                    or row.get("gameDataEvidence") is not False
                ):
                    continue
                story_key = str(row.get("sceneKey") or "")
                if not story_key:
                    continue
                recovery = {
                    key: value
                    for key, value in row.items()
                    if key != "sceneKey"
                }
                manifest_row = story_trigger_manifest.get(story_key)
                if isinstance(manifest_row, dict):
                    manifest_row["contentProvenance"] = recovery
                else:
                    overlay = manifest_overlay.setdefault(story_key, {
                        "key": story_key,
                        "kind": str(row.get("storyKind") or "")
                            or offline_shell_projection.offline_story_kind(story_key),
                        "nominalMissionId": str(mission.get("mission") or ""),
                        "attachmentStatus":
                            "project_authored_outside_game_coverage_denominator",
                        "routes": [],
                    })
                    overlay["contentProvenance"] = recovery
                published_project_authored_keys.add(story_key)

        approved_runtime_contexts = {
            (
                "objective_tracking_story_reference",
                "closed_exact_mission_tracking_context_no_relative_order",
            ),
            (
                "dialog_tree_prime_reachable_story_playback_dependency",
                "closed_exact_parent_dialog_dependency_no_relative_order",
            ),
            (
                "mission_accept_dialog",
                "closed_exact_mission_accept_dialog_no_relative_order",
            ),
            (
                "sns_authored_mission_link",
                "closed_exact_authored_sns_mission_link_no_relative_order",
            ),
            (
                "airwall_mission_state_radio_playback_context",
                "closed_exact_native_playback_context_no_relative_order",
            ),
            (
                "npc_proxy_tracking_dialog_navigation_context",
                "closed_exact_non_owning_dialog_context_no_relative_order",
            ),
            (
                "npc_proxy_lazy_destroy_dialog_context",
                "closed_exact_non_owning_dialog_context_no_relative_order",
            ),
            (
                "unique_mission_tracked_npc_proxy_dialog_context",
                "closed_exact_runtime_config_no_relative_order",
            ),
            (
                "unique_mission_tracked_npc_proxy_dialog_context",
                "closed_exact_cross_mission_runtime_config_no_relative_order",
            ),
            (
                "npc_proxy_ex_mission_context",
                "closed_exact_runtime_config_no_relative_order",
            ),
            (
                "npc_proxy_ex_mission_context",
                "closed_exact_cross_mission_runtime_config_no_relative_order",
            ),
            (
                "npc_proxy_ex_mission_context",
                "closed_exact_multi_mission_runtime_config_no_relative_order",
            ),
        }
        for row in mission.get(
            "closedExactRuntimeConfigIsolatedScenes"
        ) or []:
            if not isinstance(row, dict):
                continue
            if (
                str(row.get("relation") or ""),
                str(row.get("recoveryStatus") or ""),
            ) not in approved_runtime_contexts:
                continue
            story_key = str(row.get("sceneKey") or "")
            if not story_key:
                continue
            recovery = {
                key: value
                for key, value in row.items()
                if key != "sceneKey"
            }
            recovery["graphEffect"] = "none"
            manifest_row = story_trigger_manifest.get(story_key)
            if isinstance(manifest_row, dict):
                manifest_row["runtimeContextRecovery"] = recovery
                published_runtime_context_keys.add(story_key)
            else:
                overlay = manifest_overlay.setdefault(story_key, {
                    "key": story_key,
                    "kind": offline_shell_projection.offline_story_kind(story_key),
                    "nominalMissionId": str(
                        row.get("missionId")
                        or mission.get("mission")
                        or ""
                    ),
                    "attachmentStatus":
                        "runtime_context_outside_pipeline_coverage_denominator",
                    "routes": [],
                })
                overlay["runtimeContextRecovery"] = recovery
                published_runtime_context_keys.add(story_key)

        approved_native_contexts = {
            (
                "",
                "exact_current_build_interaction_trigger_recovered",
            ),
            (
                "authoritative_scope_leveldata_mission_context",
                "closed_exact_cross_mission_leveldata_shell_playback_context_no_relative_order",
            ),
            (
                "cutscene_root_playback_alias_composed",
                "closed_exact_composed_root_playback_context_no_relative_order",
            ),
            (
                "lua_controller_playback",
                "closed_exact_lua_controller_playback_no_mission_owner_or_relative_order",
            ),
            (
                "timeline_dialog_contains_black",
                "closed_exact_timeline_black_carrier_context_owner_or_order_unresolved",
            ),
            (
                "dialog_tree_narrative_action",
                "closed_exact_dialog_tree_black_carrier_context_no_file_order",
            ),
            (
                "leveldata_levelscript_mission_context",
                "closed_exact_cross_mission_leveldata_playback_context_no_relative_order",
            ),
            (
                "leveldata_levelscript_mission_context",
                "closed_exact_same_mission_leveldata_playback_context_no_relative_order",
            ),
            (
                "cross_owner_levelscript_quest_playback_context",
                "closed_exact_cross_mission_quest_playback_context_no_relative_order",
            ),
            (
                "dialog_tree_reachable_story_playback",
                "closed_exact_connected_dialog_tree_playback_context_no_relative_order",
            ),
            (
                "levelscript_quest_state_gate",
                "closed_exact_quest_state_gated_playback_context_no_relative_order",
            ),
        }
        for row in mission.get("closedExactNativeIsolatedScenes") or []:
            if not isinstance(row, dict):
                continue
            if (
                str(row.get("relation") or ""),
                str(row.get("recoveryStatus") or ""),
            ) not in approved_native_contexts:
                continue
            story_key = str(row.get("sceneKey") or "")
            if not story_key:
                continue
            recovery = {
                key: value
                for key, value in row.items()
                if key != "sceneKey"
            }
            recovery["graphEffect"] = "none"
            manifest_row = story_trigger_manifest.get(story_key)
            if isinstance(manifest_row, dict):
                manifest_row["runtimeContextRecovery"] = recovery
                published_runtime_context_keys.add(story_key)
            else:
                overlay = manifest_overlay.setdefault(story_key, {
                    "key": story_key,
                    "kind": offline_shell_projection.offline_story_kind(story_key),
                    "nominalMissionId": str(
                        row.get("nominalStoryMissionId")
                        or mission.get("mission")
                        or ""
                    ),
                    "attachmentStatus":
                        "runtime_context_outside_pipeline_coverage_denominator",
                    "routes": [],
                })
                overlay["runtimeContextRecovery"] = recovery
                published_runtime_context_keys.add(story_key)

    for story_key, entry in manifest_overlay.items():
        story_trigger_manifest.setdefault(story_key, entry)

    return {
        "status": "active",
        "schema": schema,
        "mappingId": str(status.get("mappingId") or ""),
        "graphEffect": "none",
        "publishedStoryKeys": len(published_keys),
        "publishedRows": published,
        "publishedPartialStoryKeys": len(published_partial_keys),
        "publishedRuntimeContextStoryKeys": len(
            published_runtime_context_keys
        ),
        "publishedProjectAuthoredStoryKeys": len(
            published_project_authored_keys
        ),
        "outsidePipelineCoverageStoryKeys": len(manifest_overlay),
        "storyTriggerManifestOverlay": manifest_overlay,
        "questAttachmentDiagnosticStatus": (
            "active" if diagnostic_active else "unavailable"
        ),
        "questAttachmentDiagnosticMappingId": (
            str(diagnostic_status.get("mappingId") or "")
            if diagnostic_active
            else ""
        ),
        "questAttachmentDiagnostics": quest_attachment_diagnostics,
        "source": _repo_path(gap_queue_path),
    }

