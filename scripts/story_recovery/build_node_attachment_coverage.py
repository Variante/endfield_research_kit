#!/usr/bin/env python3
"""Measure how far Story files actually reach into the mission *node* graph.

The Story binding coverage report answers "does this file reach a mission?".
That is not the same question as "does this file reach a node?".  A mission is
a shell; the nodes a reader navigates are quests.  A file attached only to the
mission shell is connected in the coverage sense while still being unplaced in
the graph sense.

This audit splits the corpus three ways:

* ``quest`` -- the file appears on at least one quest node, through the
  localized flow's ``quests[*].storyFiles`` or ``quests[*].storyConnections``;
* ``missionShell`` -- the file appears only in ``missionStoryConnections``;
* ``unlinked`` -- the file reaches no mission at all.

It then separates the mission-shell rows that already *name* a quest through
``candidateQuestIds`` from those that name none.  A named candidate is not an
automatic promotion: several relations deliberately stop at the shell
regardless of candidate count, most notably spatial
``pos_tracking_trigger_center_story_context`` rows, which the evidence policy
keeps diagnostic and never turns into an attachment.  The audit therefore
reports candidates by relation and by candidate count, and marks which
relations are policy-blocked, instead of proposing a bulk promotion.

The report itself creates no ownership or order edge. Mission Pipeline may
publish the uniquely joined LevelScript rows as explicit non-owning quest scope;
that consumer must preserve the boundary described below.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from common import (  # noqa: E402
    md_escape,
    read_json,
    rel_path,
    safe_key,
    write_report_json,
    write_text_if_changed,
)


SCHEMA = "nodeAttachmentCoverage.v2"

DEFAULT_FLOW_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "mission"
DEFAULT_COVERAGE_REPORT = (
    ROOT / "reports" / "story" / "build" / "mission_pipeline_story_binding_coverage_CN.json"
)
DEFAULT_PIPELINE_MISSION_ROOT = ROOT / "webui" / "data" / "mission_pipeline" / "missions"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "mission_graph"

QUEST_STORY_FIELDS = ("storyFiles", "storyConnections")

# Relations whose rows must stay at the mission shell even when they name a
# single candidate quest. Spatial proximity is diagnostic under the evidence
# policy and is never promoted to a Story attachment.
POLICY_BLOCKED_RELATIONS = frozenset({
    "pos_tracking_trigger_center_story_context",
})


def quest_attached_keys(flow: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        for field in QUEST_STORY_FIELDS:
            for row in quest.get(field) or []:
                key = row.get("key") if isinstance(row, dict) else row
                if isinstance(key, str) and key:
                    keys.add(key)
    return keys


def quest_objective_script_owners(
    pipeline_mission_root: Path,
) -> dict[str, set[tuple[str, str]]]:
    """Map each LevelScript id to the quests whose objectives name it.

    ``objectives[*].levelScriptIds`` is collected from typed ``_scriptId`` /
    ``scriptId`` operands on quest objective conditions, so a hit means the
    quest objective itself reads that script -- exact original data, not a
    filename or proximity guess.
    """
    owners: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for path in sorted(pipeline_mission_root.glob("*.json")):
        payload = read_json(path) or {}
        mission_id = safe_key((payload.get("mission") or {}).get("id")) or path.stem
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            quest_id = safe_key(node.get("id"))
            for objective in node.get("objectives") or []:
                if not isinstance(objective, dict):
                    continue
                for script_id in objective.get("levelScriptIds") or []:
                    key = safe_key(script_id)
                    if key and quest_id:
                        owners[key].add((mission_id, quest_id))
    return owners


def script_scoped_quest_placements(
    shell_rows: list[dict[str, Any]],
    script_owners: dict[str, set[tuple[str, str]]],
) -> tuple[list[dict[str, Any]], int]:
    """Shell rows whose hosting LevelScript is named by exactly one quest.

    Both halves of the join are already-accepted evidence: the row's
    ``scriptIds`` are the scripts that contain the Story occurrence, and
    ``script_owners`` are quest objective conditions naming a script. The
    placement is admitted only when the union of owners across the row's
    scripts is a single quest *and* that quest belongs to the row's own
    mission, so a script shared by several quests never selects one.

    The resulting relation is quest-level context. The objective may read a
    different property of that script than the one that plays the Story, so
    this proves shared quest scope, not playback ownership.
    """
    placements: list[dict[str, Any]] = []
    ambiguous = 0
    for row in shell_rows:
        script_ids = [safe_key(value) for value in row.get("scriptIds") or []]
        owners: set[tuple[str, str]] = set()
        matched = False
        for script_id in script_ids:
            if script_id in script_owners:
                matched = True
                owners |= script_owners[script_id]
        if not matched:
            continue
        if len(owners) != 1:
            ambiguous += 1
            continue
        owner_mission, owner_quest = next(iter(owners))
        if owner_mission != row["missionId"]:
            ambiguous += 1
            continue
        placements.append({
            "missionId": row["missionId"],
            "questId": owner_quest,
            "storyKey": row["key"],
            "kind": safe_key(row.get("kind")),
            "sourceRelation": safe_key(row.get("relation")),
            "scriptIds": script_ids,
            "questTriggerStatus": safe_key(row.get("questTriggerStatus")),
        })
    placements.sort(key=lambda item: (item["missionId"], item["questId"], item["storyKey"]))
    return placements, ambiguous


def build_report(
    flow_root: Path,
    coverage_report: Path,
    pipeline_mission_root: Path | None = None,
) -> dict[str, Any]:
    coverage = read_json(coverage_report) or {}
    unlinked_keys = {
        safe_key(row.get("key") if isinstance(row, dict) else row)
        for row in coverage.get("unlinked") or []
    }
    unlinked_keys.discard("")

    quest_keys: set[str] = set()
    shell_rows: list[dict[str, Any]] = []
    per_mission: dict[str, dict[str, Any]] = {}
    quest_node_total = 0
    quest_nodes_with_files = 0

    flow_paths = sorted(flow_root.glob("*.json"))
    for path in flow_paths:
        document = read_json(path) or {}
        flow = document.get("flow") or {}
        if not flow:
            continue
        mission_id = path.stem
        attached = quest_attached_keys(flow)
        quest_keys |= attached

        for quest in flow.get("quests") or []:
            if not isinstance(quest, dict):
                continue
            quest_node_total += 1
            if any(quest.get(field) for field in QUEST_STORY_FIELDS):
                quest_nodes_with_files += 1

        mission_rows = [
            row
            for row in flow.get("missionStoryConnections") or []
            if isinstance(row, dict) and row.get("key")
        ]
        for row in mission_rows:
            shell_rows.append({"missionId": mission_id, **row})

        per_mission[mission_id] = {
            "questNodeCount": len(flow.get("quests") or []),
            "questAttachedKeys": len(attached),
            "missionRowCount": len(mission_rows),
        }

    # A key counts as shell-only when no quest node anywhere carries it.
    shell_only_rows = [row for row in shell_rows if row["key"] not in quest_keys]
    shell_only_keys = {row["key"] for row in shell_only_rows}

    candidate_rows = [row for row in shell_only_rows if row.get("candidateQuestIds")]
    single_candidate_rows = [
        row for row in candidate_rows if len(row["candidateQuestIds"]) == 1
    ]
    promotable_rows = [
        row
        for row in single_candidate_rows
        if row.get("relation") not in POLICY_BLOCKED_RELATIONS
    ]
    blocked_rows = [
        row
        for row in single_candidate_rows
        if row.get("relation") in POLICY_BLOCKED_RELATIONS
    ]

    def relation_breakdown(rows: list[dict[str, Any]]) -> dict[str, int]:
        return dict(sorted(Counter(safe_key(row.get("relation")) for row in rows).items()))

    script_owners = (
        quest_objective_script_owners(pipeline_mission_root)
        if pipeline_mission_root and pipeline_mission_root.is_dir()
        else {}
    )
    script_placements, script_ambiguous = script_scoped_quest_placements(
        shell_only_rows, script_owners
    )

    by_relation_status: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"rows": 0, "keys": set(), "questTriggerStatuses": Counter()}
    )
    for row in promotable_rows:
        slot = by_relation_status[safe_key(row.get("relation"))]
        slot["rows"] += 1
        slot["keys"].add(row["key"])
        slot["questTriggerStatuses"][safe_key(row.get("questTriggerStatus"))] += 1

    return {
        "schemaVersion": SCHEMA,
        "generated": int(datetime.now(timezone.utc).timestamp()),
        "sources": {
            "flowRoot": rel_path(flow_root),
            "coverageReport": rel_path(coverage_report),
            "pipelineMissionRoot": (
                rel_path(pipeline_mission_root) if pipeline_mission_root else None
            ),
        },
        "evidencePolicy": {
            "question": (
                "Story binding coverage answers 'does this file reach a mission'. "
                "This audit answers 'does this file reach a quest node', which is "
                "the unit the pipeline graph actually draws."
            ),
            "noPromotion": (
                "A named candidate quest is a measurement of what the existing "
                "evidence already says and creates no attachment; it is not a "
                "proposal to attach."
            ),
            "policyBlockedRelations": sorted(POLICY_BLOCKED_RELATIONS),
            "policyBlockedReason": (
                "Spatial proximity between a tracked trigger centre and a scene is "
                "diagnostic only and is never promoted to a Story attachment, "
                "regardless of how many quests it names."
            ),
            "scriptScopedQuestPlacement": (
                "A shell-only row whose hosting LevelScript is named by exactly one "
                "quest objective condition (typed _scriptId), globally unique and in "
                "the row's own mission. This establishes shared quest scope: the "
                "objective reads the same script that hosts the Story. It does not "
                "prove the quest plays, owns, or completes the Story, because the "
                "objective may read a different property of that script."
            ),
            "publicationBoundary": (
                "Mission Pipeline may expose scriptScopedQuestPlacements on the "
                "matching quest as derived exact scope context. Such rows must remain "
                "non-owning and must not create playback, completion, branch, or order "
                "edges."
            ),
        },
        "counts": {
            "missionsRead": len(flow_paths),
            "questNodes": quest_node_total,
            "questNodesWithStoryFiles": quest_nodes_with_files,
            "questNodeAttachmentRate": (
                round(quest_nodes_with_files / quest_node_total, 4)
                if quest_node_total
                else 0.0
            ),
            "keysOnQuestNodes": len(quest_keys),
            "keysOnMissionShellOnly": len(shell_only_keys),
            "keysUnlinked": len(unlinked_keys),
            "missionShellOnlyRows": len(shell_only_rows),
            "missionShellRowsNamingACandidateQuest": len(candidate_rows),
            "missionShellRowsNamingExactlyOneQuest": len(single_candidate_rows),
            "singleCandidateRowsPolicyBlocked": len(blocked_rows),
            "singleCandidateRowsNotPolicyBlocked": len(promotable_rows),
            "singleCandidateKeysNotPolicyBlocked": len(
                {row["key"] for row in promotable_rows}
            ),
            "candidateCountHistogram": dict(
                sorted(Counter(len(row["candidateQuestIds"]) for row in candidate_rows).items())
            ),
            "questObjectiveScriptIds": len(script_owners),
            "questObjectiveScriptIdsUniqueToOneQuest": sum(
                1 for owners in script_owners.values() if len(owners) == 1
            ),
            "scriptScopedQuestPlacementRows": len(script_placements),
            "scriptScopedQuestPlacementKeys": len(
                {row["storyKey"] for row in script_placements}
            ),
            "scriptScopedQuestPlacementAmbiguous": script_ambiguous,
        },
        "scriptScopedQuestPlacements": script_placements,
        "shellOnlyRelationBreakdown": relation_breakdown(shell_only_rows),
        "singleCandidateRelationBreakdown": relation_breakdown(single_candidate_rows),
        "singleCandidateNotBlocked": {
            relation: {
                "rows": slot["rows"],
                "keys": len(slot["keys"]),
                "questTriggerStatuses": dict(sorted(slot["questTriggerStatuses"].items())),
                "storyKeys": sorted(slot["keys"]),
            }
            for relation, slot in sorted(by_relation_status.items())
        },
        "perMission": dict(sorted(per_mission.items())),
    }


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines: list[str] = []
    lines.append("# Node attachment coverage")
    lines.append("")
    lines.append(f"- schema: `{report['schemaVersion']}`")
    lines.append(
        f"- quest nodes: {counts['questNodes']}, with at least one Story file: "
        f"{counts['questNodesWithStoryFiles']} "
        f"({counts['questNodeAttachmentRate'] * 100:.1f}%)"
    )
    lines.append(f"- Story keys reaching a quest node: {counts['keysOnQuestNodes']}")
    lines.append(f"- Story keys on the mission shell only: {counts['keysOnMissionShellOnly']}")
    lines.append(f"- Story keys reaching no mission: {counts['keysUnlinked']}")
    lines.append("")
    lines.append("## Mission-shell rows that already name a quest")
    lines.append("")
    lines.append(
        f"- rows naming at least one candidate quest: "
        f"{counts['missionShellRowsNamingACandidateQuest']}"
    )
    lines.append(
        f"- rows naming exactly one: {counts['missionShellRowsNamingExactlyOneQuest']} "
        f"({counts['singleCandidateRowsPolicyBlocked']} policy-blocked, "
        f"{counts['singleCandidateRowsNotPolicyBlocked']} not blocked, covering "
        f"{counts['singleCandidateKeysNotPolicyBlocked']} Story files)"
    )
    lines.append("")
    lines.append(md_escape(report["evidencePolicy"]["noPromotion"]))
    lines.append("")
    lines.append("### Not policy-blocked, by relation")
    lines.append("")
    lines.append("| relation | rows | files | quest trigger statuses |")
    lines.append("| --- | ---: | ---: | --- |")
    for relation, slot in report["singleCandidateNotBlocked"].items():
        statuses = ", ".join(
            f"`{md_escape(name)}` ({count})" for name, count in slot["questTriggerStatuses"].items()
        )
        lines.append(
            f"| `{md_escape(relation)}` | {slot['rows']} | {slot['keys']} | {statuses} |"
        )
    lines.append("")
    lines.append("## LevelScript-scoped quest placements")
    lines.append("")
    lines.append(md_escape(report["evidencePolicy"]["scriptScopedQuestPlacement"]))
    lines.append("")
    lines.append(md_escape(report["evidencePolicy"]["publicationBoundary"]))
    lines.append("")
    lines.append(
        f"- quest objective LevelScript ids: {counts['questObjectiveScriptIds']} "
        f"({counts['questObjectiveScriptIdsUniqueToOneQuest']} unique to one quest)"
    )
    lines.append(
        f"- shell rows placed: {counts['scriptScopedQuestPlacementRows']} "
        f"covering {counts['scriptScopedQuestPlacementKeys']} Story files "
        f"({counts['scriptScopedQuestPlacementAmbiguous']} rejected as ambiguous)"
    )
    lines.append("")
    if report["scriptScopedQuestPlacements"]:
        lines.append("| story key | mission | quest | source relation |")
        lines.append("| --- | --- | --- | --- |")
        for row in report["scriptScopedQuestPlacements"]:
            lines.append(
                f"| `{md_escape(row['storyKey'])}` | `{md_escape(row['missionId'])}` | "
                f"`{md_escape(row['questId'])}` | `{md_escape(row['sourceRelation'])}` |"
            )
        lines.append("")
    lines.append("## All mission-shell-only rows, by relation")
    lines.append("")
    lines.append("| relation | rows |")
    lines.append("| --- | ---: |")
    for relation, count in sorted(
        report["shellOnlyRelationBreakdown"].items(), key=lambda item: -item[1]
    ):
        lines.append(f"| `{md_escape(relation)}` | {count} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow-root", type=Path, default=DEFAULT_FLOW_ROOT)
    parser.add_argument("--coverage-report", type=Path, default=DEFAULT_COVERAGE_REPORT)
    parser.add_argument(
        "--pipeline-mission-root", type=Path, default=DEFAULT_PIPELINE_MISSION_ROOT
    )
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    args = parser.parse_args(argv)

    if not args.flow_root.is_dir():
        raise FileNotFoundError(f"localized mission flow root not found: {args.flow_root}")

    report = build_report(
        args.flow_root, args.coverage_report, args.pipeline_mission_root
    )

    json_path = args.report_root / "node_attachment_coverage.json"
    md_path = args.report_root / "node_attachment_coverage.md"
    write_report_json(json_path, report)
    write_text_if_changed(md_path, render_markdown(report))

    counts = report["counts"]
    print(
        f"questNodes={counts['questNodes']} "
        f"withFiles={counts['questNodesWithStoryFiles']} "
        f"onQuest={counts['keysOnQuestNodes']} "
        f"shellOnly={counts['keysOnMissionShellOnly']} "
        f"unlinked={counts['keysUnlinked']} "
        f"singleCandidateNotBlocked={counts['singleCandidateKeysNotPolicyBlocked']} "
        f"scriptScopedPlaceable={counts['scriptScopedQuestPlacementKeys']}"
    )
    print(f"wrote {rel_path(json_path)}")
    print(f"wrote {rel_path(md_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
