#!/usr/bin/env python3
"""Attach ambient ``env_*`` (envTalk) Story files to their authored consumers.

``env_*`` conversation files sit entirely outside the mission pipeline's
denominator, which counts only ``black``/``cutscene``/``dlg``/``radio``/
``remotecomm``/``sns``.  They are ambient world content, so they are not
mission-owned -- but they are not unattached either: the shipped data names an
exact consumer for a third of them.

Identity is exact, not inferred.  ``EnvTalkTable`` has one row per envTalk id
and the conversation corpus has exactly one ``env_<envTalkId>.json`` per row,
a verified bijection with no leftovers on either side.

Consumers, all read by exact field name:

* ``NpcProxyTable.dataTable[*].envTalkIds`` (and the nested
  ``lazyDestroyEnvTalkData.envTalkIds``) -- a placed NPC proxy, carrying
  ``levelId``;
* ``NpcProxyExDataTable`` -- the same shape on proxy variant rows;
* ``AtmosphericNpcClusterDataTable.dataTable[*].envTalkId`` -- an ambient NPC
  cluster, carrying ``levelId`` and its member ``npcIds``;
* ``NpcTable[*].envTalkIds`` -- a character-scoped ambient line set.

Quest context comes from one typed join and nothing else: a MissionRuntime
objective's ``trackingInfoList[*]`` entry of type ``NpcProxyTrackingInfo``
names an ``npcProxyId``; when that proxy row carries ``envTalkIds``, the quest
that tracks it is recorded as *navigation/configuration context*.

That relation is deliberately weak.  It means the quest steers the player to an
NPC that has ambient lines configured on it.  It does **not** mean the quest
plays, owns, starts, or completes those lines, and it creates no chronology and
no server exchange.  This mirrors the existing repo treatment of typed
``EntityTrackingInfo``: tracking establishes context, never playback ownership.

Everything else stays honestly unattached.  A proxy or cluster row supplies a
``levelId`` scope only; filename fragments that look like level or mission ids
(``envTalk_map01_lv001_env_12``) are never parsed into an attachment.
"""
from __future__ import annotations

import argparse
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


SCHEMA = "envTalkAttachment.v1"

DEFAULT_TABLE_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Table"
DEFAULT_GAMEPLAY_CONFIG_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json" / "GameplayConfig"
)
DEFAULT_MISSION_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset"
)
DEFAULT_REPORT_ROOT = ROOT / "reports" / "mission_graph"

STORY_KEY_PREFIX = "env_"

# Field names that hold an envTalk reference. Read by exact name so an
# unrelated string field can never be promoted into a binding.
ENV_TALK_LIST_FIELD = "envTalkIds"
ENV_TALK_SCALAR_FIELD = "envTalkId"

NPC_PROXY_TRACKING_TYPE = "NpcProxyTrackingInfo"
NPC_PROXY_ID_FIELD = "npcProxyId"

# Relation labels. Only ``questTrackedNpcProxy`` reaches a quest, and it is
# context, never ownership.
RELATION_QUEST_TRACKED_PROXY = "questTrackedNpcProxy"
RELATION_LEVEL_SCOPED = "levelScopedConsumer"
RELATION_CHARACTER_SCOPED = "characterScopedConsumer"
RELATION_NONE = "noAuthoredConsumer"

RELATION_ORDER = (
    RELATION_QUEST_TRACKED_PROXY,
    RELATION_LEVEL_SCOPED,
    RELATION_CHARACTER_SCOPED,
    RELATION_NONE,
)

RELATION_SUMMARY = {
    RELATION_QUEST_TRACKED_PROXY: (
        "a MissionRuntime objective tracks the NPC proxy that carries these lines; "
        "quest navigation/configuration context only, never playback ownership"
    ),
    RELATION_LEVEL_SCOPED: "consumer row supplies an exact levelId, but no quest tracks it",
    RELATION_CHARACTER_SCOPED: "configured on an NpcTable character with no level or quest scope",
    RELATION_NONE: "no row in any shipped consumer table references this envTalk id",
}


def iter_env_talk_ids(node: Any) -> Iterator[str]:
    """Yield every envTalk id reachable under exact field names."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == ENV_TALK_LIST_FIELD and isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item:
                        yield item
            elif key == ENV_TALK_SCALAR_FIELD and isinstance(value, str) and value:
                yield value
            else:
                yield from iter_env_talk_ids(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_env_talk_ids(value)


def data_table(payload: Any) -> dict[str, Any]:
    """Unwrap the ``dataTable`` envelope used by GameplayConfig tables."""
    if isinstance(payload, dict):
        inner = payload.get("dataTable")
        if isinstance(inner, dict):
            return inner
        return {k: v for k, v in payload.items() if not k.startswith("__")}
    return {}


def collect_consumers(
    table_root: Path, gameplay_root: Path
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, set[str]], Counter]:
    """Return envTalk id -> consumer rows, proxy id -> envTalk ids, and stats."""
    consumers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    proxy_env_talk: dict[str, set[str]] = defaultdict(set)
    stats: Counter = Counter()

    specs = (
        ("NpcProxyTable", gameplay_root / "NpcProxyTable.json", "npcProxy", True),
        ("NpcProxyExDataTable", gameplay_root / "NpcProxyExDataTable.json", "npcProxyEx", True),
        (
            "AtmosphericNpcClusterDataTable",
            gameplay_root / "AtmosphericNpcClusterDataTable.json",
            "atmosphericCluster",
            False,
        ),
        ("NpcTable", table_root / "NpcTable.json", "npc", False),
    )

    for table_name, path, consumer_kind, is_proxy in specs:
        rows = data_table(read_json(path))
        if not rows:
            stats[f"{table_name}Missing"] += 1
            continue
        stats[f"{table_name}Rows"] = len(rows)
        for row_key, row in rows.items():
            if not isinstance(row, dict):
                continue
            ids = sorted(set(iter_env_talk_ids(row)))
            if not ids:
                continue
            stats[f"{table_name}RowsWithEnvTalk"] += 1
            level_id = safe_key(row.get("levelId"))
            entry = {
                "table": table_name,
                "consumerKind": consumer_kind,
                "rowKey": row_key,
                "levelId": level_id,
                "sourceFile": rel_path(path),
            }
            if consumer_kind == "atmosphericCluster":
                npc_ids = [n for n in (row.get("npcIds") or []) if isinstance(n, str) and n]
                if npc_ids:
                    entry["npcIds"] = sorted(npc_ids)
            for env_talk_id in ids:
                consumers[env_talk_id].append(entry)
                if is_proxy:
                    proxy_env_talk[row_key].add(env_talk_id)

    return consumers, proxy_env_talk, stats


def collect_proxy_tracking(mission_root: Path) -> tuple[dict[str, list[dict[str, Any]]], Counter]:
    """Return proxy id -> typed tracking records that name it."""
    tracking: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stats: Counter = Counter()

    def walk(node: Any, mission_id: str, path: str) -> None:
        if isinstance(node, dict):
            raw_type = node.get("$type")
            # The node must declare the tracking type itself. Inheriting a type
            # from an enclosing record would let an untyped nested dict that
            # happens to carry the same field name become a binding.
            node_type = (
                raw_type.split(",", 1)[0].rsplit(".", 1)[-1]
                if isinstance(raw_type, str)
                else None
            )
            proxy_id = node.get(NPC_PROXY_ID_FIELD)
            # Accept the reference only from the typed tracking record, so an
            # incidental proxy-name string elsewhere never becomes a binding.
            if (
                node_type == NPC_PROXY_TRACKING_TYPE
                and isinstance(proxy_id, str)
                and proxy_id
            ):
                stats["trackingRows"] += 1
                tracking[proxy_id].append(
                    {
                        "missionId": mission_id,
                        "questId": quest_from_path(path),
                        "jsonPath": f"{path}.{NPC_PROXY_ID_FIELD}",
                        "trackingType": NPC_PROXY_TRACKING_TYPE,
                    }
                )
                return
            for key, value in node.items():
                walk(value, mission_id, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, mission_id, f"{path}[{index}]")

    mission_paths = sorted(
        path for path in mission_root.glob("*.json") if not path.name.endswith("_meta.json")
    )
    stats["missionsRead"] = len(mission_paths)
    for path in mission_paths:
        document = read_json(path)
        if document is None:
            continue
        walk(document, path.stem, "")
    return tracking, stats


def quest_from_path(json_path: str) -> str:
    import re

    match = re.match(r"^\.questDic\.(?P<quest>[^.\[]+)", json_path)
    return match.group("quest") if match else ""


def build_report(
    *, table_root: Path, gameplay_root: Path, mission_root: Path
) -> dict[str, Any]:
    definitions = read_json(table_root / "EnvTalkTable.json") or {}
    definition_ids = sorted(k for k in definitions if isinstance(k, str))

    consumers, proxy_env_talk, consumer_stats = collect_consumers(table_root, gameplay_root)
    tracking, tracking_stats = collect_proxy_tracking(mission_root)

    # A consumer may name an envTalk id that no EnvTalkTable row defines. Those
    # references are reported rather than dropped, and are never repaired by
    # trimming into an attachment: an exact-string lookup is what the runtime
    # does, so a whitespace-damaged id is a real defect, not a match.
    definition_set = set(definition_ids)
    dangling: list[dict[str, Any]] = []
    for env_talk_id in sorted(set(consumers) - definition_set):
        stripped = env_talk_id.strip()
        dangling.append(
            {
                "reference": env_talk_id,
                "hasSurroundingWhitespace": stripped != env_talk_id,
                "trimmedIdIsDefined": stripped in definition_set,
                "consumers": sorted(
                    (
                        {"table": row["table"], "rowKey": row["rowKey"], "levelId": row["levelId"]}
                        for row in consumers[env_talk_id]
                    ),
                    key=lambda item: (item["table"], item["rowKey"]),
                ),
            }
        )

    entries: list[dict[str, Any]] = []
    relation_counts: Counter = Counter()
    quest_context_missions: set[str] = set()
    quest_context_quests: set[str] = set()

    for env_talk_id in definition_ids:
        rows = consumers.get(env_talk_id) or []
        level_ids = sorted({r["levelId"] for r in rows if r["levelId"]})

        quest_contexts: list[dict[str, Any]] = []
        for row in rows:
            if row["consumerKind"] not in ("npcProxy", "npcProxyEx"):
                continue
            for record in tracking.get(row["rowKey"]) or []:
                quest_contexts.append(
                    {
                        "missionId": record["missionId"],
                        "questId": record["questId"],
                        "npcProxyId": row["rowKey"],
                        "levelId": row["levelId"],
                        "trackingType": record["trackingType"],
                        "jsonPath": record["jsonPath"],
                    }
                )
        quest_contexts.sort(key=lambda item: (item["missionId"], item["questId"], item["jsonPath"]))

        if quest_contexts:
            relation = RELATION_QUEST_TRACKED_PROXY
            quest_context_missions.update(item["missionId"] for item in quest_contexts)
            quest_context_quests.update(item["questId"] for item in quest_contexts if item["questId"])
        elif level_ids:
            relation = RELATION_LEVEL_SCOPED
        elif rows:
            relation = RELATION_CHARACTER_SCOPED
        else:
            relation = RELATION_NONE
        relation_counts[relation] += 1

        entries.append(
            {
                "envTalkId": env_talk_id,
                "storyKey": f"{STORY_KEY_PREFIX}{env_talk_id}",
                "relation": relation,
                "levelIds": level_ids,
                "consumerCount": len(rows),
                "consumers": sorted(
                    rows, key=lambda item: (item["table"], item["rowKey"])
                ),
                "questContexts": quest_contexts,
            }
        )

    by_relation: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        by_relation[entry["relation"]].append(entry["storyKey"])

    return {
        "schemaVersion": SCHEMA,
        "generated": int(datetime.now(timezone.utc).timestamp()),
        "sources": {
            "definitions": rel_path(table_root / "EnvTalkTable.json"),
            "gameplayConfigRoot": rel_path(gameplay_root),
            "missionRoot": rel_path(mission_root),
        },
        "evidencePolicy": {
            "identity": (
                "EnvTalkTable has one row per envTalk id and the conversation corpus "
                "has exactly one env_<envTalkId>.json per row; the mapping is a "
                "verified bijection, not a filename inference."
            ),
            "questRelation": (
                "A quest reaches an envTalk id only through a typed "
                "NpcProxyTrackingInfo.npcProxyId whose proxy row carries envTalkIds. "
                "This is navigation/configuration context: the quest steers the player "
                "to an NPC that has ambient lines configured. It is not playback "
                "ownership, chronology, a completion callback, or a server exchange."
            ),
            "rejected": [
                "Level or mission ids parsed out of envTalk filenames.",
                "Proximity between a proxy position and a mission area.",
                "Promoting a level-scoped consumer to a mission because only one "
                "mission uses that level.",
            ],
            "coverageBound": (
                "envTalk is ambient world content keyed by NPC, proxy, or cluster. "
                "No shipped table binds an envTalk id to a mission id, so the mission "
                "pipeline denominator legitimately excludes these files."
            ),
        },
        "relationSemantics": {relation: RELATION_SUMMARY[relation] for relation in RELATION_ORDER},
        "counts": {
            "definitions": len(definition_ids),
            "withAuthoredConsumer": len(definition_ids) - relation_counts[RELATION_NONE],
            "relationCounts": {relation: relation_counts[relation] for relation in RELATION_ORDER},
            "questContextMissions": len(quest_context_missions),
            "questContextQuests": len(quest_context_quests),
            "distinctLevelIds": len(
                {level for entry in entries for level in entry["levelIds"]}
            ),
            "proxyRowsWithEnvTalk": len(proxy_env_talk),
            "npcProxyTrackingRows": tracking_stats["trackingRows"],
            "missionsRead": tracking_stats["missionsRead"],
            "danglingConsumerReferences": len(dangling),
            "danglingWithSurroundingWhitespace": sum(
                1 for item in dangling if item["hasSurroundingWhitespace"]
            ),
            "danglingRepairableByTrim": sum(1 for item in dangling if item["trimmedIdIsDefined"]),
            **{key: value for key, value in consumer_stats.items()},
        },
        "danglingConsumerReferences": dangling,
        "storyKeysByRelation": {
            relation: sorted(by_relation.get(relation, [])) for relation in RELATION_ORDER
        },
        "entries": entries,
    }


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines: list[str] = []
    lines.append("# envTalk attachment")
    lines.append("")
    lines.append(f"- schema: `{report['schemaVersion']}`")
    lines.append(f"- definitions: {counts['definitions']}")
    lines.append(f"- with an authored consumer: {counts['withAuthoredConsumer']}")
    lines.append(
        f"- quest context: {counts['relationCounts'][RELATION_QUEST_TRACKED_PROXY]} files "
        f"across {counts['questContextQuests']} quests in {counts['questContextMissions']} missions"
    )
    lines.append(f"- distinct level ids: {counts['distinctLevelIds']}")
    lines.append("")
    lines.append("## Relations")
    lines.append("")
    lines.append("| relation | files | meaning |")
    lines.append("| --- | ---: | --- |")
    for relation in RELATION_ORDER:
        lines.append(
            f"| `{relation}` | {counts['relationCounts'][relation]} | "
            f"{md_escape(report['relationSemantics'][relation])} |"
        )
    lines.append("")
    lines.append("## Coverage bound")
    lines.append("")
    lines.append(md_escape(report["evidencePolicy"]["coverageBound"]))
    lines.append("")
    if report["danglingConsumerReferences"]:
        lines.append("## Dangling consumer references")
        lines.append("")
        lines.append(
            "Consumer rows naming an envTalk id that EnvTalkTable does not define. "
            "These are reported, never repaired: the runtime does an exact-string "
            "lookup, so a whitespace-damaged id does not resolve in the game either."
        )
        lines.append("")
        lines.append("| reference | whitespace | trimmed id defined | consumers |")
        lines.append("| --- | --- | --- | --- |")
        for item in report["danglingConsumerReferences"]:
            consumers = ", ".join(f"`{md_escape(c['rowKey'])}`" for c in item["consumers"][:3])
            if len(item["consumers"]) > 3:
                consumers += f" (+{len(item['consumers']) - 3})"
            lines.append(
                f"| `{md_escape(item['reference'])}` | "
                f"{'yes' if item['hasSurroundingWhitespace'] else 'no'} | "
                f"{'yes' if item['trimmedIdIsDefined'] else 'no'} | {consumers} |"
            )
        lines.append("")
    lines.append("## Quest-tracked proxy context")
    lines.append("")
    lines.append("| story key | mission | quest | npc proxy | level |")
    lines.append("| --- | --- | --- | --- | --- |")
    for entry in report["entries"]:
        for context in entry["questContexts"]:
            lines.append(
                f"| `{md_escape(entry['storyKey'])}` | `{md_escape(context['missionId'])}` | "
                f"`{md_escape(context['questId'])}` | `{md_escape(context['npcProxyId'])}` | "
                f"`{md_escape(context['levelId'])}` |"
            )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-root", type=Path, default=DEFAULT_TABLE_ROOT)
    parser.add_argument("--gameplay-config-root", type=Path, default=DEFAULT_GAMEPLAY_CONFIG_ROOT)
    parser.add_argument("--mission-root", type=Path, default=DEFAULT_MISSION_ROOT)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    args = parser.parse_args(argv)

    report = build_report(
        table_root=args.table_root,
        gameplay_root=args.gameplay_config_root,
        mission_root=args.mission_root,
    )

    json_path = args.report_root / "envtalk_attachment.json"
    md_path = args.report_root / "envtalk_attachment.md"
    write_report_json(json_path, report)
    write_text_if_changed(md_path, render_markdown(report))

    counts = report["counts"]
    print(
        f"definitions={counts['definitions']} "
        f"withConsumer={counts['withAuthoredConsumer']} "
        f"questContext={counts['relationCounts'][RELATION_QUEST_TRACKED_PROXY]} "
        f"levelScoped={counts['relationCounts'][RELATION_LEVEL_SCOPED]} "
        f"characterScoped={counts['relationCounts'][RELATION_CHARACTER_SCOPED]} "
        f"none={counts['relationCounts'][RELATION_NONE]}"
    )
    print(f"wrote {rel_path(json_path)}")
    print(f"wrote {rel_path(md_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
