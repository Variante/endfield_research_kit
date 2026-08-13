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


SCHEMA = "nodeAttachmentCoverage.v4"

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


def playback_path_getter_evidence(
    row: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Return exact quest getters serialized on this Story playback path.

    The Story builder records a branch predicate only when the getter is
    uniquely decoded from the current-build action payload. Keeping the result
    keyed by the occurrence's LevelScript id prevents a predicate from one
    script from selecting an objective owner of another script on a multi-
    occurrence shell row.
    """
    by_script: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occurrence_index, occurrence in enumerate(row.get("levelScriptOccurrences") or []):
        if not isinstance(occurrence, dict):
            continue
        script_id = safe_key(occurrence.get("scriptId"))
        if not script_id:
            continue
        for owner_index, owner in enumerate(occurrence.get("nativeEventOwners") or []):
            if not isinstance(owner, dict):
                continue
            path = owner.get("path") or []
            for path_index, step in enumerate(path):
                if not isinstance(step, dict):
                    continue
                predicate = step.get("branchPredicate")
                if (
                    not isinstance(predicate, dict)
                    or safe_key(predicate.get("status")) != "exact_unique_getter"
                ):
                    continue
                for quest_id_raw in predicate.get("getterTexts") or []:
                    quest_id = safe_key(quest_id_raw)
                    if not quest_id:
                        continue
                    by_script[script_id].append({
                        "questId": quest_id,
                        "scriptId": script_id,
                        "occurrenceIndex": occurrence_index,
                        "eventOwnerIndex": owner_index,
                        "pathIndex": path_index,
                        "pathEdge": safe_key(step.get("edge")),
                        "selectedBranchEdge": (
                            safe_key(path[path_index + 1].get("edge"))
                            if path_index + 1 < len(path)
                            and isinstance(path[path_index + 1], dict)
                            else ""
                        ),
                        "branchLocalId": step.get("localId"),
                        "getterLocalId": predicate.get("getterLocalId"),
                    })
    return by_script


def script_scoped_quest_placements(
    shell_rows: list[dict[str, Any]],
    script_owners: dict[str, set[tuple[str, str]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Shell rows whose hosting LevelScript is named by exactly one quest.

    Both halves of the join are already-accepted evidence: the row's
    ``scriptIds`` are the scripts that contain the Story occurrence, and
    ``script_owners`` are quest objective conditions naming a script. The
    placement is admitted when the union of owners across the row's scripts is
    a single quest in the row's mission. When several objectives name the same
    script, one additional discriminator is allowed: an exact uniquely-decoded
    quest getter on the serialized playback path may select that same quest
    from the objective-owner set. Script-wide strings and unrelated paths are
    never selectors.

    The resulting relation is quest-level context. The objective may read a
    different property of that script than the one that plays the Story, so
    this proves shared quest scope, not playback ownership.
    """
    placements: list[dict[str, Any]] = []
    ambiguities: list[dict[str, Any]] = []
    for row in shell_rows:
        script_ids = [safe_key(value) for value in row.get("scriptIds") or []]
        owners: set[tuple[str, str]] = set()
        owners_by_script: dict[str, set[tuple[str, str]]] = {}
        matched = False
        for script_id in script_ids:
            if script_id in script_owners:
                matched = True
                owners_by_script[script_id] = set(script_owners[script_id])
                owners |= owners_by_script[script_id]
        if not matched:
            continue

        owner: tuple[str, str] | None = None
        discriminator = ""
        predicate_evidence: list[dict[str, Any]] = []
        if len(owners) == 1:
            candidate = next(iter(owners))
            if candidate[0] == row["missionId"]:
                owner = candidate
                discriminator = "globally_unique_objective_script_owner"
        else:
            predicates_by_script = playback_path_getter_evidence(row)
            discriminated: set[tuple[str, str]] = set()
            for script_id, evidence_rows in predicates_by_script.items():
                script_owner_rows = owners_by_script.get(script_id, set())
                predicate_quest_ids = {
                    safe_key(evidence.get("questId")) for evidence in evidence_rows
                }
                for candidate in script_owner_rows:
                    if (
                        candidate[0] == row["missionId"]
                        and candidate[1] in predicate_quest_ids
                    ):
                        discriminated.add(candidate)
            if len(discriminated) == 1:
                owner = next(iter(discriminated))
                discriminator = "exact_playback_path_quest_predicate"
                for script_id, evidence_rows in predicates_by_script.items():
                    if owner not in owners_by_script.get(script_id, set()):
                        continue
                    predicate_evidence.extend(
                        evidence
                        for evidence in evidence_rows
                        if safe_key(evidence.get("questId")) == owner[1]
                    )

        if owner is None:
            same_mission_owners = sorted(
                quest_id
                for mission_id, quest_id in owners
                if mission_id == row["missionId"]
            )
            foreign_owners = [
                {"missionId": mission_id, "questId": quest_id}
                for mission_id, quest_id in sorted(owners)
                if mission_id != row["missionId"]
            ]
            predicates_by_script = playback_path_getter_evidence(row)
            path_predicates = sorted(
                {
                    (script_id, safe_key(evidence.get("questId")))
                    for script_id, evidence_rows in predicates_by_script.items()
                    for evidence in evidence_rows
                    if any(
                        owner_quest == safe_key(evidence.get("questId"))
                        for _owner_mission, owner_quest in owners_by_script.get(
                            script_id, set()
                        )
                    )
                }
            )
            if same_mission_owners:
                reason = "multiple_or_unresolved_same_mission_objective_owners"
            else:
                reason = "objective_owner_mission_mismatch"
            ambiguities.append({
                "missionId": row["missionId"],
                "storyKey": row["key"],
                "kind": safe_key(row.get("kind")),
                "sourceRelation": safe_key(row.get("relation")),
                "scriptIds": script_ids,
                "reason": reason,
                "sameMissionOwnerQuestIds": same_mission_owners,
                "foreignOwners": foreign_owners,
                "playbackPathOwnerQuestPredicates": [
                    {"scriptId": script_id, "questId": quest_id}
                    for script_id, quest_id in path_predicates
                ],
            })
            continue

        owner_mission, owner_quest = owner
        placements.append({
            "missionId": row["missionId"],
            "questId": owner_quest,
            "storyKey": row["key"],
            "kind": safe_key(row.get("kind")),
            "sourceRelation": safe_key(row.get("relation")),
            "scriptIds": script_ids,
            "questTriggerStatus": safe_key(row.get("questTriggerStatus")),
            "scopeDiscriminator": discriminator,
            "questPredicateEvidence": predicate_evidence,
        })
    placements.sort(key=lambda item: (item["missionId"], item["questId"], item["storyKey"]))
    ambiguities.sort(
        key=lambda item: (item["missionId"], item["storyKey"], item["sourceRelation"])
    )
    return placements, ambiguities


def exact_quest_condition_scope_placements(
    mission_id: str,
    flow: dict[str, Any],
) -> list[dict[str, Any]]:
    """Publish exact per-quest script observations already present in the flow.

    A ``levelscript_condition_scope`` quest row alone is diagnostic. It becomes
    publishable only when the same flow also has a complete
    ``levelscript_mission_context`` row whose exact native playback occurrence
    names the same Story key and carries a MissionRuntime condition for that
    quest and script.
    """
    exact_scopes: set[tuple[str, str, str, str]] = set()
    for row in flow.get("missionStoryConnections") or []:
        if (
            not isinstance(row, dict)
            or safe_key(row.get("relation")) != "levelscript_mission_context"
            or safe_key(row.get("confidence")) != "scoped_script"
            or row.get("hasUnscopedOrOtherMissionOccurrences") is not False
            or "mission_condition_checks_script"
            not in {
                safe_key(value) for value in row.get("scopeEvidenceKinds") or []
            }
        ):
            continue
        story_key = safe_key(row.get("key"))
        occurrences = [
            occurrence
            for occurrence in row.get("levelScriptOccurrences") or []
            if isinstance(occurrence, dict)
        ]
        if (
            not story_key
            or not occurrences
            or row.get("occurrenceCount") != len(occurrences)
            or row.get("allOccurrenceCount") != len(occurrences)
        ):
            continue
        for occurrence in occurrences:
            map_id = safe_key(occurrence.get("levelId"))
            script_id = safe_key(occurrence.get("scriptId"))
            if (
                not map_id
                or not script_id
                or not safe_key(occurrence.get("actionMapRole")).startswith(
                    "actionList#"
                )
                or not safe_key(occurrence.get("recordClass")).startswith("play_")
                or story_key not in {
                    safe_key(value)
                    for value in occurrence.get("allStoryKeysInRecord") or []
                }
                or "mission_condition_checks_script"
                not in {
                    safe_key(value)
                    for value in occurrence.get("scopeEvidenceKinds") or []
                }
            ):
                continue
            for condition in occurrence.get("missionConditions") or []:
                if not isinstance(condition, dict):
                    continue
                quest_id = safe_key(condition.get("questId"))
                if (
                    safe_key(condition.get("missionId")) == mission_id
                    and quest_id
                ):
                    exact_scopes.add((story_key, map_id, script_id, quest_id))

    placements: list[dict[str, Any]] = []
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id") or quest.get("questId"))
        if not quest_id:
            continue
        for row in quest.get("storyConnections") or []:
            if (
                not isinstance(row, dict)
                or safe_key(row.get("relation")) != "levelscript_condition_scope"
                or safe_key(row.get("direction")) != "context"
                or safe_key(row.get("confidence")) != "scoped_script"
            ):
                continue
            story_key = safe_key(row.get("key"))
            map_id = safe_key(row.get("mapId"))
            script_id = safe_key(row.get("scriptId"))
            if (story_key, map_id, script_id, quest_id) not in exact_scopes:
                continue
            placements.append({
                "missionId": mission_id,
                "questId": quest_id,
                "storyKey": story_key,
                "kind": safe_key(row.get("kind")),
                "sourceRelation": "levelscript_condition_scope",
                "scriptIds": [script_id],
                "mapIds": [map_id],
                "questTriggerStatus": "",
                "scopeDiscriminator":
                    "exact_quest_condition_and_complete_native_playback_scope",
                "questPredicateEvidence": [],
            })
    return sorted(
        placements,
        key=lambda item: (
            item["missionId"],
            item["questId"],
            item["storyKey"],
            item["scriptIds"],
        ),
    )


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
    exact_condition_placements: list[dict[str, Any]] = []
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
        exact_condition_placements.extend(
            exact_quest_condition_scope_placements(mission_id, flow)
        )

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
    script_placements, script_ambiguities = script_scoped_quest_placements(
        shell_only_rows, script_owners
    )
    script_placements.extend(exact_condition_placements)
    script_placements.sort(
        key=lambda item: (
            item["missionId"],
            item["questId"],
            item["storyKey"],
            item["scopeDiscriminator"],
        )
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
                "A shell-only row whose hosting LevelScript is named by one or more "
                "quest objective conditions (typed _scriptId). A globally unique "
                "same-mission owner is admitted directly. If several quests name the "
                "same script, only an exact uniquely-decoded quest getter on that "
                "Story occurrence's serialized playback path may select one of those "
                "objective owners. An existing per-quest "
                "`levelscript_condition_scope` row is also published when a complete "
                "same-key native playback occurrence independently carries that exact "
                "quest condition. This establishes shared quest dependency scope, "
                "but does not prove the quest plays, owns, or completes the Story."
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
            "scriptScopedQuestPlacementAmbiguous": len(script_ambiguities),
        },
        "scriptScopedQuestPlacements": script_placements,
        "scriptScopedQuestAmbiguities": script_ambiguities,
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
        lines.append("| story key | mission | quest | discriminator | source relation |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in report["scriptScopedQuestPlacements"]:
            lines.append(
                f"| `{md_escape(row['storyKey'])}` | `{md_escape(row['missionId'])}` | "
                f"`{md_escape(row['questId'])}` | "
                f"`{md_escape(row.get('scopeDiscriminator'))}` | "
                f"`{md_escape(row['sourceRelation'])}` |"
            )
        lines.append("")
    if report["scriptScopedQuestAmbiguities"]:
        lines.append("### Rejected objective/LevelScript joins")
        lines.append("")
        lines.append("| story key | shell mission | reason | same-mission owners | foreign owners |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in report["scriptScopedQuestAmbiguities"]:
            same_mission = ", ".join(
                f"`{md_escape(value)}`"
                for value in row.get("sameMissionOwnerQuestIds") or []
            )
            foreign = ", ".join(
                f"`{md_escape(owner.get('missionId'))}:{md_escape(owner.get('questId'))}`"
                for owner in row.get("foreignOwners") or []
            )
            lines.append(
                f"| `{md_escape(row['storyKey'])}` | `{md_escape(row['missionId'])}` | "
                f"`{md_escape(row['reason'])}` | {same_mission} | {foreign} |"
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
