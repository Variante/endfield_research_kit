"""Publish non-owning quest scope inferred by the node-attachment audit."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ == "scripts.mission_pipeline":
    from ..common import (
        compact_dict,
        write_report_json,
        write_text_if_changed,
    )
    from ..story_builder.node_attachment import (
        build_report as build_node_attachment_report,
        render_markdown as render_node_attachment_markdown,
    )
elif __package__ == "mission_pipeline":
    from common import compact_dict, write_report_json, write_text_if_changed
    from story_builder.node_attachment import (
        build_report as build_node_attachment_report,
        render_markdown as render_node_attachment_markdown,
    )
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("import this module as scripts.mission_pipeline.quest_scope_projection")


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_ROOT = ROOT / "reports" / "mission_graph"


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


def publish_quest_objective_story_scope(
    index: dict[str, Any],
    output_root: Path,
    story_data_root: Path,
    language: str,
    coverage_report: Path,
    report_root: Path = DEFAULT_REPORT_ROOT,
) -> dict[str, Any] | None:
    """Publish exact objective-to-LevelScript joins as non-owning quest context.

    The node-attachment audit admits a Story row when its hosting LevelScript is
    named by exactly one same-mission quest objective in the generated pipeline.
    When several objectives name the same script, an exact uniquely-decoded
    quest getter on that Story occurrence's serialized playback path may select
    one member of that owner set. These rows are deliberately dependency
    context, never playback ownership or ordering.
    """
    flow_root = story_data_root / language / "mission"
    mission_root = output_root / "missions"
    if (
        not flow_root.is_dir()
        or not mission_root.is_dir()
        or not coverage_report.is_file()
    ):
        return None

    report = build_node_attachment_report(
        flow_root,
        coverage_report,
        mission_root,
    )
    report_root.mkdir(parents=True, exist_ok=True)
    report_json = report_root / "node_attachment_coverage.json"
    report_markdown = report_root / "node_attachment_coverage.md"
    write_report_json(report_json, report)
    write_text_if_changed(report_markdown, render_node_attachment_markdown(report))

    placements_by_mission: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for placement in report.get("scriptScopedQuestPlacements") or []:
        if not isinstance(placement, dict):
            continue
        mission_id = str(placement.get("missionId") or "")
        quest_id = str(placement.get("questId") or "")
        story_key = str(placement.get("storyKey") or "")
        if not mission_id or not quest_id or not story_key:
            continue
        script_ids = sorted(
            {
                str(value)
                for value in placement.get("scriptIds") or []
                if str(value)
            }
        )
        discriminator = str(placement.get("scopeDiscriminator") or "")
        predicate_evidence = [
            row
            for row in placement.get("questPredicateEvidence") or []
            if isinstance(row, dict)
        ]
        if discriminator == "exact_playback_path_quest_predicate":
            evidence_text = (
                "quest objective names the hosting LevelScript and an exact "
                "uniquely-decoded quest getter gates this Story playback path"
            )
            confidence = "derived_exact_quest_scope_path_predicate"
        elif (
            discriminator
            == "exact_quest_condition_and_complete_native_playback_scope"
        ):
            evidence_text = (
                "quest condition names this LevelScript and the complete exact "
                "native Story occurrence carries that same quest condition"
            )
            confidence = "derived_exact_quest_condition_scope"
        else:
            evidence_text = (
                "quest objective names the unique LevelScript that hosts "
                "this Story occurrence"
            )
            confidence = "derived_exact_quest_scope"
        placements_by_mission[mission_id][quest_id].append(
            compact_dict(
                {
                    "key": story_key,
                    "kind": placement.get("kind") or "",
                    "relation": "quest_objective_levelscript_scope_context",
                    "sourceRelation": placement.get("sourceRelation") or "",
                    "direction": "context",
                    "phase": "objective_scope",
                    "confidence": confidence,
                    "scriptIds": script_ids,
                    "scopeDiscriminator": discriminator,
                    "questPredicateEvidence": predicate_evidence,
                    "questTriggerStatus": placement.get("questTriggerStatus") or "",
                    "ownershipStatus": "non_owning_context",
                    "playbackOwnership": False,
                    "orderEvidence": False,
                    "source": _repo_path(report_json),
                    "evidence": evidence_text,
                }
            )
        )

    published_rows = 0
    published_keys: set[str] = set()
    published_quests = 0
    published_missions = 0
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        mission_path = output_root / str(summary.get("file") or "")
        if not mission_path.is_file():
            continue
        payload = _read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        mission_rows = 0
        mission_quests = 0
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            node.pop("storyScopeContexts", None)
            quest_id = str(node.get("id") or "")
            rows = placements_by_mission.get(mission_id, {}).get(quest_id, [])
            if not rows:
                continue
            deduplicated = {
                (
                    str(row.get("key") or ""),
                    str(row.get("sourceRelation") or ""),
                    str(row.get("scopeDiscriminator") or ""),
                    tuple(row.get("scriptIds") or []),
                ): row
                for row in rows
            }
            node["storyScopeContexts"] = sorted(
                deduplicated.values(),
                key=lambda row: (
                    str(row.get("key") or ""),
                    str(row.get("sourceRelation") or ""),
                    str(row.get("scopeDiscriminator") or ""),
                    tuple(row.get("scriptIds") or []),
                ),
            )
            mission_quests += 1
            mission_rows += len(node["storyScopeContexts"])
            published_keys.update(
                str(row.get("key") or "")
                for row in node["storyScopeContexts"]
            )
        summary["storyScopeContextCount"] = mission_rows
        summary["storyScopeContextQuestCount"] = mission_quests
        if mission_rows:
            published_missions += 1
            published_quests += mission_quests
            published_rows += mission_rows
        _write_json(mission_path, payload)

    counts = report.get("counts") or {}
    index["nodeAttachmentCoverage"] = {
        "schema": report.get("schemaVersion"),
        "language": language,
        "counts": counts,
        "evidencePolicy": {
            "classification": "derived_exact_quest_scope",
            "ownershipPromotion": False,
            "orderPromotion": False,
            "boundary": (
                "A unique objective owner, or an exact playback-path quest predicate "
                "selecting one member of the objective-owner set, proves shared quest "
                "dependency scope only; it does not prove playback ownership or "
                "chronology."
            ),
        },
        "published": {
            "missions": published_missions,
            "quests": published_quests,
            "rows": published_rows,
            "uniqueStoryKeys": len(published_keys),
        },
        "reportJson": _repo_path(report_json),
        "reportMarkdown": _repo_path(report_markdown),
    }
    return report
