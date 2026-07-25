#!/usr/bin/env python3
"""Recover the inter-mission dependency graph from authored MissionRuntime data.

MissionRuntimeAsset carries no mission-to-mission ordering field: the accept
sidecar has only ``acceptMode``/``missionType``/``rewardId``, and mission
unlocking is server-authored.  The one place the shipped client data *does*
state a relation between two different missions is a quest condition that reads
another mission's or another mission's quest's state.

This builder extracts exactly those conditions:

* ``CheckMissionState`` / ``SimpleConditionCheckMissionState`` -- reads
  ``_missionId`` directly;
* ``CheckQuestState`` / ``SimpleConditionCheckQuestState`` -- reads
  ``_questId``, whose owning mission is the literal ``<mission>_q#<n>`` prefix.

A row becomes a graph edge only when the referenced mission differs from the
mission that declares the condition.  Same-mission reads are intra-mission
quest flow and are already covered by ``prevQuestIdList`` in the pipeline
payload, so they are counted and dropped here.

Edge semantics follow the condition's own operands and are never collapsed
into one "precedes" relation:

* ``requiresCompleted``  -- objective waits for ``Equal Completed``; the target
  mission finishes before the declaring quest can advance.  This is the only
  class that carries authored precedence.
* ``requiresProcessing`` -- objective waits for ``Equal Processing``; the
  target must be *in progress*, which is a co-active window, not precedence.
* ``abortsOnCompleted``  -- the reference sits in ``failedCondition``: the
  declaring quest fails when the target completes.  This is mutual exclusion
  and is the opposite of precedence.

The comparer/state numerals are the installed build's enums, already pinned
elsewhere in this repo by the native ``CheckMissionState`` union tag ``0x67``
whose decoded predicate reads ``e7m4 Equal Completed`` (comparer ``0`` =
``Equal``, state ``3`` = ``Completed``, state ``2`` = ``Processing``).  Any
unrecognized comparer/state pair is retained verbatim under ``unclassified``
rather than being guessed into a relation.

What these edges are NOT: they are not a full mission unlock tree.  Only the
missions that happen to gate on another mission's state appear here.  Absence
of an edge is not evidence that two missions are unordered -- the authoritative
unlock order lives on the server.

Granularity matters.  ``CheckQuestState`` names an exact quest, so the same
evidence also yields a quest-level graph.  Combined with the intra-mission
``prevQuestIdList`` chains, that quest graph is acyclic.  The mission-level
projection is not: two missions can hand control back and forth, which collapses
into a mission-level cycle that no reordering can remove.  Such a pair is
reported as an *interleaving* rather than as a contradiction, and only after the
underlying quest graph is confirmed acyclic.  A mission-level cycle whose quest
graph is *also* cyclic would be a real defect and is reported separately.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


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


SCHEMA = "missionDependencyGraph.v1"

DEFAULT_MISSION_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset"
)
DEFAULT_REPORT_ROOT = ROOT / "reports" / "mission_graph"

# Condition ``$type`` short names that name another mission, and the field that
# carries the reference. Both the full gameplay condition and its "Simple"
# counterpart serialize the same operand names.
MISSION_STATE_TYPES = ("CheckMissionState", "SimpleConditionCheckMissionState")
QUEST_STATE_TYPES = ("CheckQuestState", "SimpleConditionCheckQuestState")

MISSION_ID_FIELDS = ("_missionId", "missionId")
QUEST_ID_FIELDS = ("_questId", "questId")
COMPARER_FIELDS = ("_comparer", "comparer")
MISSION_STATE_FIELDS = ("_targetMissionState", "targetMissionState")
QUEST_STATE_FIELDS = ("_targetQuestState", "targetQuestState")

COMPARER_EQUAL = 0
STATE_PROCESSING = 2
STATE_COMPLETED = 3

COMPARER_NAMES = {COMPARER_EQUAL: "Equal"}
STATE_NAMES = {STATE_PROCESSING: "Processing", STATE_COMPLETED: "Completed"}

RELATION_REQUIRES_COMPLETED = "requiresCompleted"
RELATION_REQUIRES_PROCESSING = "requiresProcessing"
RELATION_ABORTS_ON_COMPLETED = "abortsOnCompleted"
RELATION_UNCLASSIFIED = "unclassified"

# Only ``requiresCompleted`` states that the target finishes first. The other
# classes are deliberately excluded from any ordering consumer.
PRECEDENCE_RELATIONS = frozenset({RELATION_REQUIRES_COMPLETED})

RELATION_ORDER = (
    RELATION_REQUIRES_COMPLETED,
    RELATION_REQUIRES_PROCESSING,
    RELATION_ABORTS_ON_COMPLETED,
    RELATION_UNCLASSIFIED,
)

RELATION_SUMMARY = {
    RELATION_REQUIRES_COMPLETED: "target mission completes before the declaring quest advances",
    RELATION_REQUIRES_PROCESSING: "target mission must be in progress; co-active window, not precedence",
    RELATION_ABORTS_ON_COMPLETED: "declaring quest fails when the target completes; mutual exclusion",
    RELATION_UNCLASSIFIED: "comparer/state pair not pinned by the installed build; retained verbatim",
}

QUEST_ID_PATTERN = re.compile(r"^(?P<mission>.+?)_q#")

# ``failedCondition`` inverts the meaning of whatever it contains, so the
# declaring path decides the relation before the operands do.
FAILED_CONDITION_SEGMENT = "failedCondition"


def quest_owner_mission(quest_id: str) -> str | None:
    """Return the mission that owns ``quest_id``, or None if it is not a quest id."""
    match = QUEST_ID_PATTERN.match(safe_key(quest_id))
    return match.group("mission") if match else None


def const_value(node: Any, fields: tuple[str, ...]) -> Any:
    """Read the first present field, unwrapping the authored ``constValue`` box."""
    if not isinstance(node, dict):
        return None
    for field in fields:
        if field not in node:
            continue
        value = node[field]
        if isinstance(value, dict):
            return value.get("constValue")
        return value
    return None


def type_short_name(node: Any) -> str | None:
    if not isinstance(node, dict):
        return None
    raw = node.get("$type")
    if not isinstance(raw, str):
        return None
    return raw.split(",", 1)[0].rsplit(".", 1)[-1]


def iter_state_conditions(node: Any, path: str = "") -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Yield ``(kind, json_path, condition)`` for every mission/quest state read.

    ``kind`` is ``"mission"`` or ``"quest"``. Nested conditions inside
    ``CombineCondition.subConditions`` are reached by the ordinary walk, so a
    reference stays visible no matter how deep the authored boolean tree is.
    """
    if isinstance(node, dict):
        short = type_short_name(node)
        if short in MISSION_STATE_TYPES:
            yield "mission", path, node
            return
        if short in QUEST_STATE_TYPES:
            yield "quest", path, node
            return
        for key, value in node.items():
            yield from iter_state_conditions(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_state_conditions(value, f"{path}[{index}]")


def declaring_quest_id(json_path: str) -> str:
    """Recover the quest that declares a condition from its authored JSON path."""
    match = re.match(r"^\.questDic\.(?P<quest>[^.\[]+)", json_path)
    return match.group("quest") if match else ""


def classify_relation(*, json_path: str, comparer: Any, state: Any) -> str:
    if FAILED_CONDITION_SEGMENT in json_path:
        # A failure clause reverses the sense of its operands. Only an
        # Equal/Completed failure clause has a pinned meaning.
        if comparer == COMPARER_EQUAL and state == STATE_COMPLETED:
            return RELATION_ABORTS_ON_COMPLETED
        return RELATION_UNCLASSIFIED
    if comparer != COMPARER_EQUAL:
        return RELATION_UNCLASSIFIED
    if state == STATE_COMPLETED:
        return RELATION_REQUIRES_COMPLETED
    if state == STATE_PROCESSING:
        return RELATION_REQUIRES_PROCESSING
    return RELATION_UNCLASSIFIED


def find_cycles(adjacency: dict[str, set[str]]) -> list[list[str]]:
    """Return distinct simple cycles reachable by DFS over ``adjacency``."""
    cycles: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    color: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        color[node] = 1
        stack.append(node)
        for neighbour in sorted(adjacency.get(node, ())):
            state = color.get(neighbour, 0)
            if state == 1:
                cycle = stack[stack.index(neighbour):]
                rotation = min(range(len(cycle)), key=lambda i: cycle[i])
                normalized = tuple(cycle[rotation:] + cycle[:rotation])
                if normalized not in seen:
                    seen.add(normalized)
                    cycles.append(list(normalized))
            elif state == 0:
                visit(neighbour)
        stack.pop()
        color[node] = 2

    for node in sorted(adjacency):
        if color.get(node, 0) == 0:
            visit(node)
    return cycles


def collect_quest_edges(
    mission_root: Path, rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build the quest-granularity graph that the mission projection collapses.

    Two edge sources are combined: authored ``prevQuestIdList`` chains inside a
    mission, and the cross-mission ``CheckQuestState`` precedence rows, which
    are the only cross-mission references that name an exact quest.
    """
    adjacency: dict[str, set[str]] = defaultdict(set)
    intra_count = 0
    for path in sorted(mission_root.glob("*.json")):
        if path.name.endswith("_meta.json"):
            continue
        document = read_json(path)
        quest_dic = (document or {}).get("questDic") or {}
        if not isinstance(quest_dic, dict):
            continue
        for quest_id, quest in quest_dic.items():
            if not isinstance(quest, dict):
                continue
            for previous in quest.get("prevQuestIdList") or []:
                if isinstance(previous, str) and previous:
                    adjacency[previous].add(quest_id)
                    intra_count += 1

    cross_edges: list[dict[str, Any]] = []
    for row in rows:
        if row["referenceKind"] != "quest" or row["relation"] not in PRECEDENCE_RELATIONS:
            continue
        declaring = row["declaringQuestId"]
        if not declaring or not row["reference"]:
            continue
        adjacency[row["reference"]].add(declaring)
        cross_edges.append(
            {
                "from": row["reference"],
                "to": declaring,
                "fromMission": row["targetMission"],
                "toMission": row["sourceMission"],
                "relation": row["relation"],
                "conditionType": row["conditionType"],
                "conditionUniqueId": row["conditionUniqueId"],
                "jsonPath": row["jsonPath"],
                "sourceFile": row["sourceFile"],
            }
        )

    cross_edges.sort(key=lambda edge: (edge["from"], edge["to"]))
    cycles = find_cycles(adjacency)
    return cross_edges, {
        "intraMissionEdges": intra_count,
        "crossMissionEdges": len(cross_edges),
        "nodes": len(adjacency),
        "cycles": cycles,
    }


def collect_rows(mission_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read every MissionRuntimeAsset and return raw cross-mission reference rows."""
    mission_paths = sorted(
        path
        for path in mission_root.glob("*.json")
        if not path.name.endswith("_meta.json")
    )
    known_missions = {path.stem for path in mission_paths}
    rows: list[dict[str, Any]] = []
    stats = Counter()
    stats["missionsRead"] = len(mission_paths)

    for path in mission_paths:
        mission_id = path.stem
        document = read_json(path)
        if document is None:
            stats["missionsUnreadable"] += 1
            continue
        for kind, json_path, condition in iter_state_conditions(document):
            stats["stateConditionRows"] += 1
            if kind == "mission":
                reference = const_value(condition, MISSION_ID_FIELDS)
                target = safe_key(reference)
                state = const_value(condition, MISSION_STATE_FIELDS)
            else:
                reference = const_value(condition, QUEST_ID_FIELDS)
                target = safe_key(quest_owner_mission(reference) or "")
                state = const_value(condition, QUEST_STATE_FIELDS)
            comparer = const_value(condition, COMPARER_FIELDS)

            if not target:
                # A quest id that does not parse, or a blank mission operand.
                stats["unresolvedReference"] += 1
                continue
            if target == mission_id:
                stats["sameMissionRows"] += 1
                continue

            rows.append(
                {
                    "sourceMission": mission_id,
                    "targetMission": target,
                    "referenceKind": kind,
                    "reference": safe_key(reference),
                    "declaringQuestId": declaring_quest_id(json_path),
                    "conditionType": type_short_name(condition) or "",
                    "conditionUniqueId": safe_key(condition.get("uniqueId")),
                    "comparer": comparer,
                    "comparerName": COMPARER_NAMES.get(comparer, ""),
                    "targetState": state,
                    "targetStateName": STATE_NAMES.get(state, ""),
                    "relation": classify_relation(
                        json_path=json_path, comparer=comparer, state=state
                    ),
                    "jsonPath": json_path,
                    "sourceFile": rel_path(path),
                }
            )

    stats["crossMissionRows"] = len(rows)
    stats["targetMissionsMissingFromCorpus"] = len(
        {row["targetMission"] for row in rows} - known_missions
    )
    return rows, {"knownMissions": known_missions, "stats": stats}


def build_edges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group reference rows into one edge per (target, source, relation)."""
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["targetMission"], row["sourceMission"], row["relation"])].append(row)

    edges: list[dict[str, Any]] = []
    for (target, source, relation), members in sorted(grouped.items()):
        edges.append(
            {
                "from": target,
                "to": source,
                "relation": relation,
                "precedence": relation in PRECEDENCE_RELATIONS,
                "referenceCount": len(members),
                "declaringQuestIds": sorted({m["declaringQuestId"] for m in members if m["declaringQuestId"]}),
                "referenceKinds": sorted({m["referenceKind"] for m in members}),
                "evidence": sorted(
                    (
                        {
                            "conditionType": m["conditionType"],
                            "conditionUniqueId": m["conditionUniqueId"],
                            "reference": m["reference"],
                            "comparerName": m["comparerName"],
                            "targetStateName": m["targetStateName"],
                            "jsonPath": m["jsonPath"],
                            "sourceFile": m["sourceFile"],
                        }
                        for m in members
                    ),
                    key=lambda item: item["jsonPath"],
                ),
            }
        )
    return edges


def find_precedence_cycles(edges: list[dict[str, Any]]) -> list[list[str]]:
    """Return simple cycles over mission-level precedence edges only."""
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge["precedence"]:
            adjacency[edge["from"]].add(edge["to"])
    return find_cycles(adjacency)


def build_mission_index(edges: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-mission upstream/downstream view, split by relation."""
    index: dict[str, dict[str, Any]] = {}

    def slot(mission: str) -> dict[str, Any]:
        return index.setdefault(
            mission,
            {"upstream": defaultdict(list), "downstream": defaultdict(list)},
        )

    for edge in edges:
        slot(edge["to"])["upstream"][edge["relation"]].append(edge["from"])
        slot(edge["from"])["downstream"][edge["relation"]].append(edge["to"])

    return {
        mission: {
            "upstream": {rel: sorted(set(v)) for rel, v in sorted(value["upstream"].items())},
            "downstream": {rel: sorted(set(v)) for rel, v in sorted(value["downstream"].items())},
        }
        for mission, value in sorted(index.items())
    }


def build_report(mission_root: Path) -> dict[str, Any]:
    rows, context = collect_rows(mission_root)
    stats = context["stats"]
    edges = build_edges(rows)
    cycles = find_precedence_cycles(edges)
    mission_index = build_mission_index(edges)
    quest_edges, quest_stats = collect_quest_edges(mission_root, rows)

    relation_counts = Counter(edge["relation"] for edge in edges)
    precedence_edges = [edge for edge in edges if edge["precedence"]]

    # A mission-level cycle is only an interleaving if the quest graph that it
    # projects from is itself acyclic. Otherwise it is a real defect and must
    # not be explained away.
    quest_graph_acyclic = not quest_stats["cycles"]
    interleavings = [
        {
            "missions": cycle,
            "questGraphAcyclic": True,
            "explanation": (
                "These missions hand control back and forth at quest granularity; "
                "the quest-level precedence graph is acyclic, so no mission-level "
                "ordering exists between them."
            ),
        }
        for cycle in cycles
    ] if quest_graph_acyclic else []
    unexplained_cycles = [] if quest_graph_acyclic else cycles

    return {
        "schemaVersion": SCHEMA,
        "generated": int(datetime.now(timezone.utc).timestamp()),
        "source": rel_path(mission_root),
        "evidencePolicy": {
            "acceptedRelation": (
                "A quest condition in mission A that reads mission B's state, or a "
                "quest of mission B's state, where B != A."
            ),
            "enumProvenance": (
                "comparer 0 = Equal, mission/quest state 3 = Completed, 2 = Processing; "
                "pinned by the installed-build CheckMissionState union tag 0x67 whose "
                "decoded predicate reads 'e7m4 Equal Completed'."
            ),
            "precedenceRelations": sorted(PRECEDENCE_RELATIONS),
            "notPrecedence": [
                RELATION_REQUIRES_PROCESSING,
                RELATION_ABORTS_ON_COMPLETED,
                RELATION_UNCLASSIFIED,
            ],
            "coverageBound": (
                "Only missions that gate on another mission's state appear. Mission "
                "unlock order is server-authored and is not recoverable from the "
                "shipped client data, so a missing edge is not evidence that two "
                "missions are unordered."
            ),
            "rejected": [
                "MissionRuntimeAsset *_meta.json carries no prerequisite field "
                "(acceptMode/missionType/missionImportance/rewardId only).",
                "ChapterMissionChapterTable/MissionSelectChapterTable map chapter ids "
                "to UI select chapters and carry no mission ordering.",
                "Filename or numeric mission-id similarity is never an edge.",
            ],
        },
        "relationSemantics": {
            relation: RELATION_SUMMARY[relation] for relation in RELATION_ORDER
        },
        "counts": {
            "missionsRead": stats["missionsRead"],
            "missionsUnreadable": stats["missionsUnreadable"],
            "stateConditionRows": stats["stateConditionRows"],
            "sameMissionRows": stats["sameMissionRows"],
            "unresolvedReference": stats["unresolvedReference"],
            "crossMissionRows": stats["crossMissionRows"],
            "targetMissionsMissingFromCorpus": stats["targetMissionsMissingFromCorpus"],
            "edges": len(edges),
            "precedenceEdges": len(precedence_edges),
            "missionsInGraph": len(mission_index),
            "precedenceCycles": len(cycles),
            "missionInterleavings": len(interleavings),
            "unexplainedPrecedenceCycles": len(unexplained_cycles),
            "questGraphNodes": quest_stats["nodes"],
            "questGraphIntraMissionEdges": quest_stats["intraMissionEdges"],
            "questGraphCrossMissionEdges": quest_stats["crossMissionEdges"],
            "questGraphCycles": len(quest_stats["cycles"]),
            "relationEdgeCounts": {rel: relation_counts.get(rel, 0) for rel in RELATION_ORDER},
        },
        "edges": edges,
        "missions": mission_index,
        "precedenceCycles": cycles,
        "missionInterleavings": interleavings,
        "unexplainedPrecedenceCycles": unexplained_cycles,
        "questGraph": {
            "acyclic": quest_graph_acyclic,
            "nodes": quest_stats["nodes"],
            "intraMissionEdges": quest_stats["intraMissionEdges"],
            "crossMissionEdges": quest_edges,
            "cycles": quest_stats["cycles"],
            "sources": [
                "MissionRuntimeAsset.questDic[*].prevQuestIdList (intra-mission)",
                "CheckQuestState / SimpleConditionCheckQuestState Equal Completed (cross-mission)",
            ],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines: list[str] = []
    lines.append("# Mission dependency graph")
    lines.append("")
    lines.append(f"- schema: `{report['schemaVersion']}`")
    lines.append(f"- source: `{report['source']}`")
    lines.append(f"- missions read: {counts['missionsRead']}")
    lines.append(
        f"- cross-mission reference rows: {counts['crossMissionRows']} "
        f"(same-mission rows dropped: {counts['sameMissionRows']})"
    )
    lines.append(
        f"- edges: {counts['edges']} across {counts['missionsInGraph']} missions "
        f"({counts['precedenceEdges']} precedence)"
    )
    lines.append(
        f"- mission-level precedence cycles: {counts['precedenceCycles']} "
        f"({counts['missionInterleavings']} explained as interleaving, "
        f"{counts['unexplainedPrecedenceCycles']} unexplained)"
    )
    lines.append(
        f"- quest graph: {counts['questGraphNodes']} nodes, "
        f"{counts['questGraphIntraMissionEdges']} intra-mission + "
        f"{counts['questGraphCrossMissionEdges']} cross-mission edges, "
        f"{counts['questGraphCycles']} cycles"
    )
    lines.append(
        f"- target missions missing from corpus: {counts['targetMissionsMissingFromCorpus']}"
    )
    lines.append("")
    lines.append("## Relation semantics")
    lines.append("")
    lines.append("| relation | edges | precedence | meaning |")
    lines.append("| --- | ---: | --- | --- |")
    for relation in RELATION_ORDER:
        lines.append(
            f"| `{relation}` | {counts['relationEdgeCounts'][relation]} | "
            f"{'yes' if relation in PRECEDENCE_RELATIONS else 'no'} | "
            f"{md_escape(report['relationSemantics'][relation])} |"
        )
    lines.append("")
    lines.append("## Coverage bound")
    lines.append("")
    lines.append(md_escape(report["evidencePolicy"]["coverageBound"]))
    lines.append("")
    lines.append("## Edges")
    lines.append("")
    lines.append("| from | to | relation | refs | declaring quests |")
    lines.append("| --- | --- | --- | ---: | --- |")
    for edge in report["edges"]:
        quests = ", ".join(f"`{md_escape(q)}`" for q in edge["declaringQuestIds"][:4])
        if len(edge["declaringQuestIds"]) > 4:
            quests += f" (+{len(edge['declaringQuestIds']) - 4})"
        lines.append(
            f"| `{md_escape(edge['from'])}` | `{md_escape(edge['to'])}` | "
            f"`{edge['relation']}` | {edge['referenceCount']} | {quests} |"
        )
    lines.append("")
    if report["missionInterleavings"]:
        lines.append("## Mission interleavings")
        lines.append("")
        lines.append(
            "Mission-level cycles whose underlying quest graph is acyclic. These "
            "missions exchange control at quest granularity, so no mission-level "
            "ordering between them exists to recover."
        )
        lines.append("")
        for item in report["missionInterleavings"]:
            missions = item["missions"]
            lines.append("- " + " -> ".join(f"`{md_escape(m)}`" for m in missions + missions[:1]))
        lines.append("")
    if report["unexplainedPrecedenceCycles"]:
        lines.append("## Unexplained precedence cycles")
        lines.append("")
        lines.append(
            "The quest graph is also cyclic here, so the relation classification "
            "is wrong or the authored data is inconsistent. Investigate before use."
        )
        lines.append("")
        for cycle in report["unexplainedPrecedenceCycles"]:
            lines.append("- " + " -> ".join(f"`{md_escape(m)}`" for m in cycle + cycle[:1]))
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission-root", type=Path, default=DEFAULT_MISSION_ROOT)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    args = parser.parse_args(argv)

    if not args.mission_root.is_dir():
        raise FileNotFoundError(f"MissionRuntimeAsset root not found: {args.mission_root}")

    report = build_report(args.mission_root)

    json_path = args.report_root / "mission_dependency_graph.json"
    md_path = args.report_root / "mission_dependency_graph.md"
    write_report_json(json_path, report)
    write_text_if_changed(md_path, render_markdown(report))

    counts = report["counts"]
    print(
        f"missions={counts['missionsRead']} "
        f"crossRows={counts['crossMissionRows']} "
        f"edges={counts['edges']} "
        f"precedence={counts['precedenceEdges']} "
        f"interleavings={counts['missionInterleavings']} "
        f"unexplainedCycles={counts['unexplainedPrecedenceCycles']} "
        f"questGraphCycles={counts['questGraphCycles']}"
    )
    print(f"wrote {rel_path(json_path)}")
    print(f"wrote {rel_path(md_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
