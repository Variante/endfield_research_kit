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

Mission/quest context comes from two typed, exact joins:

* a MissionRuntime objective's ``trackingInfoList[*]`` entry of type
  ``NpcProxyTrackingInfo`` names an ``npcProxyId``; when that proxy row carries
  ``envTalkIds``, the quest that tracks it is recorded as navigation context;
* an atmospheric cluster's complete, non-empty ``npcIds`` set is contained by
  exactly one active switcher group on the same exact ``levelId``. The matching
  ``AtmosphericNpcSwitcherGroupConfig.condition`` supplies exact mission/quest
  state dependencies for the cluster's envTalk.

Both relations are deliberately weak. They explain navigation or world-state
availability, not playback. They do **not** mean a mission plays, owns, starts,
or completes the lines, and they create no chronology or server exchange.

Everything else stays honestly unattached.  A proxy or cluster row supplies a
``levelId`` scope only; filename fragments that look like level or mission ids
(``envTalk_map01_lv001_env_12``) are never parsed into an attachment.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[2]
try:
    from common import (
        md_escape,
        read_json,
        rel_path,
        safe_key,
        write_report_json,
        write_text_if_changed,
    )
except ModuleNotFoundError:
    from scripts.common import (
        md_escape,
        read_json,
        rel_path,
        safe_key,
        write_report_json,
        write_text_if_changed,
    )
from .mission_assets import select_complete_mission_runtime_root


SCHEMA = "envTalkAttachment.v2"

DEFAULT_TABLE_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Table"
DEFAULT_GAMEPLAY_CONFIG_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json" / "GameplayConfig"
)
DEFAULT_MISSION_ROOT = select_complete_mission_runtime_root(
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data"
    / "Json" / "MissionRuntimeAsset",
    ROOT / "export_full" / "structured" / "Persistent" / "Data" / "Json"
    / "MissionRuntimeAsset",
)
DEFAULT_REPORT_ROOT = ROOT / "reports" / "mission_graph"

STORY_KEY_PREFIX = "env_"

# Field names that hold an envTalk reference. Read by exact name so an
# unrelated string field can never be promoted into a binding.
ENV_TALK_LIST_FIELD = "envTalkIds"
ENV_TALK_SCALAR_FIELD = "envTalkId"

NPC_PROXY_TRACKING_TYPE = "NpcProxyTrackingInfo"
NPC_PROXY_ID_FIELD = "npcProxyId"
STATE_CONTEXT_RELATION = "atmosphericSwitcherStateContext"

ACTIVE_SWITCHER_TABLE = "AtmosphericNpcActiveSwitcherDataTable"
SWITCHER_CONFIG_TABLE = "AtmosphericNpcSwitcherDataTable"
CLUSTER_TABLE = "AtmosphericNpcClusterDataTable"

# Primary consumer labels stay independent of atmospheric state context. Both
# quest-tracked proxy and switcher-state joins are context, never ownership.
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


def collect_proxy_tracking(
    mission_root: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str], set[str], Counter]:
    """Return typed proxy tracking plus exact mission and quest registries."""
    tracking: dict[str, list[dict[str, Any]]] = defaultdict(list)
    quest_owners: dict[str, str] = {}
    mission_ids: set[str] = set()
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
        if not isinstance(document, dict):
            continue
        mission_id = safe_key(document.get("missionId")) or path.stem
        mission_ids.add(mission_id)
        quests = document.get("questDic")
        if isinstance(quests, dict):
            for quest_id in quests:
                if not isinstance(quest_id, str) or not quest_id:
                    continue
                prior = quest_owners.setdefault(quest_id, mission_id)
                if prior != mission_id:
                    stats["questOwnerConflicts"] += 1
        walk(document, mission_id, "")
    stats["missionIds"] = len(mission_ids)
    stats["questIds"] = len(quest_owners)
    return tracking, quest_owners, mission_ids, stats


def collect_condition_references(node: Any, path: str = ".condition") -> list[dict[str, Any]]:
    """Collect exact mission/quest fields from one authored condition tree."""
    references: list[dict[str, Any]] = []
    if isinstance(node, dict):
        condition_type = safe_key(node.get("$type"))
        common = {
            "conditionType": condition_type,
            "compareOperator": node.get("compareOperator"),
            "compareTarget": node.get("compareTarget"),
            "reverse": node.get("reverse"),
        }
        for field, kind in (("missionId", "mission"), ("questId", "quest")):
            reference_id = safe_key(node.get(field))
            if reference_id:
                references.append(
                    {
                        "kind": kind,
                        "id": reference_id,
                        "jsonPath": f"{path}.{field}",
                        **common,
                    }
                )
        for key, value in node.items():
            collect_path = f"{path}.{key}"
            references.extend(collect_condition_references(value, collect_path))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            references.extend(collect_condition_references(value, f"{path}[{index}]"))
    return references


def collect_atmospheric_state_contexts(
    gameplay_root: Path,
    quest_owners: dict[str, str],
    mission_ids: set[str],
) -> tuple[dict[str, list[dict[str, Any]]], Counter]:
    """Join atmospheric clusters to switcher conditions, failing closed.

    A cluster is accepted only when its complete, non-empty NPC set is a subset
    of exactly one active switcher group on the same exact level. Partial
    overlaps, cross-level matches, ambiguous groups, and missing configs are
    counted but never promoted.
    """
    cluster_path = gameplay_root / f"{CLUSTER_TABLE}.json"
    active_path = gameplay_root / f"{ACTIVE_SWITCHER_TABLE}.json"
    config_path = gameplay_root / f"{SWITCHER_CONFIG_TABLE}.json"
    clusters = data_table(read_json(cluster_path))
    active_by_level = data_table(read_json(active_path))
    config_payload = read_json(config_path) or {}
    configs = (
        config_payload.get("groupConfigs")
        if isinstance(config_payload, dict)
        else {}
    )
    if not isinstance(configs, dict):
        configs = {}

    stats: Counter = Counter()
    for key in (
        "clustersWithoutJoinIdentity",
        "ambiguousClusterMatches",
        "partialOnlyClusterMatches",
        "crossLevelClusterMatches",
        "missingClusterMatches",
        "clustersWithUniqueSwitcherGroup",
        "matchedGroupsWithoutConfig",
        "matchedConfigIdentityMismatch",
        "clustersWithoutStateReference",
        "stateContextClusters",
    ):
        stats[key] = 0
    stats["atmosphericClusters"] = len(clusters)
    stats["switcherGroupConfigs"] = len(configs)
    active_groups: list[dict[str, Any]] = []
    active_group_ids: list[str] = []
    empty_active_groups = 0
    for level_key, switchers in active_by_level.items():
        if not isinstance(switchers, list):
            continue
        for switcher in switchers:
            if not isinstance(switcher, dict):
                continue
            level_id = safe_key(switcher.get("levelId")) or safe_key(level_key)
            switcher_id = safe_key(switcher.get("switcherId"))
            group_npcs = switcher.get("groupId2AtmosphericNpcs")
            if not isinstance(group_npcs, dict):
                continue
            for group_id, npc_ids in group_npcs.items():
                normalized_group_id = safe_key(group_id)
                active_group_ids.append(normalized_group_id)
                npc_set = {
                    value for value in (npc_ids or [])
                    if isinstance(value, str) and value
                }
                if not npc_set:
                    empty_active_groups += 1
                    continue
                active_groups.append(
                    {
                        "groupId": normalized_group_id,
                        "switcherId": switcher_id,
                        "levelId": level_id,
                        "npcIds": npc_set,
                    }
                )
    stats["activeSwitcherGroupRows"] = len(active_group_ids)
    stats["activeSwitcherGroupIds"] = len(set(active_group_ids))
    stats["activeSwitcherDuplicateGroupRows"] = (
        len(active_group_ids) - len(set(active_group_ids))
    )
    stats["activeSwitcherEmptyGroups"] = empty_active_groups
    stats["activeSwitcherGroupsWithNpcs"] = len(active_groups)

    by_env_talk: dict[str, list[dict[str, Any]]] = defaultdict(list)
    state_files: set[str] = set()
    state_missions: set[str] = set()
    state_quests: set[str] = set()
    for cluster_key, cluster in clusters.items():
        if not isinstance(cluster, dict):
            continue
        env_talk_id = safe_key(cluster.get("envTalkId"))
        cluster_id = safe_key(cluster.get("clusterId")) or safe_key(cluster_key)
        level_id = safe_key(cluster.get("levelId"))
        cluster_npcs = {
            value for value in (cluster.get("npcIds") or [])
            if isinstance(value, str) and value
        }
        if not env_talk_id or not level_id or not cluster_npcs:
            stats["clustersWithoutJoinIdentity"] += 1
            continue

        same_level = [group for group in active_groups if group["levelId"] == level_id]
        matches = [
            group for group in same_level
            if cluster_npcs.issubset(group["npcIds"])
        ]
        if len(matches) != 1:
            if len(matches) > 1:
                stats["ambiguousClusterMatches"] += 1
            elif any(cluster_npcs & group["npcIds"] for group in same_level):
                stats["partialOnlyClusterMatches"] += 1
            elif any(
                cluster_npcs.issubset(group["npcIds"])
                for group in active_groups
                if group["levelId"] != level_id
            ):
                stats["crossLevelClusterMatches"] += 1
            else:
                stats["missingClusterMatches"] += 1
            continue
        stats["clustersWithUniqueSwitcherGroup"] += 1
        group = matches[0]
        config = configs.get(group["groupId"])
        if not isinstance(config, dict):
            stats["matchedGroupsWithoutConfig"] += 1
            continue
        config_level = safe_key(config.get("levelId"))
        config_switcher = safe_key(config.get("switcherId"))
        if config_level != level_id or config_switcher != group["switcherId"]:
            stats["matchedConfigIdentityMismatch"] += 1
            continue

        condition_references = collect_condition_references(config.get("condition"))
        condition_missions = sorted({
            row["id"] for row in condition_references if row["kind"] == "mission"
        })
        condition_quests = sorted({
            row["id"] for row in condition_references if row["kind"] == "quest"
        })
        bind_mission_id = safe_key(config.get("bindMissionId"))
        referenced_missions = set(condition_missions)
        if bind_mission_id:
            referenced_missions.add(bind_mission_id)
        resolved_missions = {value for value in referenced_missions if value in mission_ids}
        unresolved_missions = referenced_missions - resolved_missions
        unresolved_quests: list[str] = []
        resolved_quest_owners: dict[str, str] = {}
        for quest_id in condition_quests:
            owner = quest_owners.get(quest_id)
            if owner:
                resolved_missions.add(owner)
                resolved_quest_owners[quest_id] = owner
            else:
                unresolved_quests.append(quest_id)

        if not condition_references and not bind_mission_id:
            stats["clustersWithoutStateReference"] += 1
            continue
        context = {
            "relation": STATE_CONTEXT_RELATION,
            "clusterId": cluster_id,
            "switcherId": group["switcherId"],
            "switcherGroupId": group["groupId"],
            "levelId": level_id,
            "npcIds": sorted(cluster_npcs),
            "bindMissionId": bind_mission_id,
            "missionIds": sorted(resolved_missions),
            "conditionMissionIds": condition_missions,
            "questIds": condition_quests,
            "questOwners": resolved_quest_owners,
            "unresolvedMissionIds": sorted(unresolved_missions),
            "unresolvedQuestIds": sorted(unresolved_quests),
            "conditionReferences": condition_references,
            "sourceFiles": {
                "cluster": rel_path(cluster_path),
                "activeSwitcher": rel_path(active_path),
                "switcherConfig": rel_path(config_path),
            },
        }
        by_env_talk[env_talk_id].append(context)
        stats["stateContextClusters"] += 1
        state_files.add(env_talk_id)
        state_missions.update(resolved_missions)
        state_quests.update(condition_quests)

    stats["stateContextFiles"] = len(state_files)
    stats["stateContextMissions"] = len(state_missions)
    stats["stateContextQuests"] = len(state_quests)
    return by_env_talk, stats


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
    tracking, quest_owners, mission_ids, tracking_stats = collect_proxy_tracking(mission_root)
    state_contexts_by_env_talk, state_stats = collect_atmospheric_state_contexts(
        gameplay_root,
        quest_owners,
        mission_ids,
    )

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
        state_contexts = sorted(
            state_contexts_by_env_talk.get(env_talk_id) or [],
            key=lambda item: (item["levelId"], item["switcherGroupId"], item["clusterId"]),
        )

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
                "stateContexts": state_contexts,
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
            "atmosphericStateRelation": (
                "An atmospheric cluster reaches a switcher condition only when its "
                "complete non-empty npcIds set is contained by exactly one active "
                "switcher group on the same exact levelId, and that group's config "
                "identity agrees. Exact missionId/questId fields under condition and "
                "bindMissionId provide world-state availability context. They do not "
                "prove envTalk playback, mission ownership, chronology, completion, "
                "or a server exchange."
            ),
            "rejected": [
                "Level or mission ids parsed out of envTalk filenames.",
                "Proximity between a proxy position and a mission area.",
                "Promoting a level-scoped consumer to a mission because only one "
                "mission uses that level.",
                "Partial NPC overlap, a cross-level NPC-set match, or more than one "
                "full switcher-group match.",
            ],
            "coverageBound": (
                "envTalk is ambient world content keyed by NPC, proxy, or cluster. "
                "The recovered mission/quest relations explain navigation or NPC-group "
                "availability; no shipped row makes a mission the playback owner of an "
                "envTalk id, so the mission Story denominator still excludes these files."
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
            "missionIdsRead": tracking_stats["missionIds"],
            "questIdsRead": tracking_stats["questIds"],
            "questOwnerConflicts": tracking_stats["questOwnerConflicts"],
            "danglingConsumerReferences": len(dangling),
            "danglingWithSurroundingWhitespace": sum(
                1 for item in dangling if item["hasSurroundingWhitespace"]
            ),
            "danglingRepairableByTrim": sum(1 for item in dangling if item["trimmedIdIsDefined"]),
            **{key: value for key, value in state_stats.items()},
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
    lines.append(
        f"- atmospheric switcher state context: {counts['stateContextFiles']} files / "
        f"{counts['stateContextClusters']} clusters across "
        f"{counts['stateContextQuests']} quests in {counts['stateContextMissions']} missions"
    )
    lines.append(
        f"- exact cluster/group joins: {counts['clustersWithUniqueSwitcherGroup']} / "
        f"{counts['atmosphericClusters']} "
        f"(ambiguous {counts['ambiguousClusterMatches']}, "
        f"partial-only {counts['partialOnlyClusterMatches']}, "
        f"cross-level {counts['crossLevelClusterMatches']}, "
        f"missing {counts['missingClusterMatches']})"
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
    lines.append("## Atmospheric switcher state context")
    lines.append("")
    lines.append(
        "These rows are exact NPC-group availability dependencies, not envTalk "
        "playback or mission ownership."
    )
    lines.append("")
    lines.append("| story key | missions | quests | switcher group | cluster | level |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for entry in report["entries"]:
        for context in entry["stateContexts"]:
            missions = ", ".join(f"`{md_escape(value)}`" for value in context["missionIds"])
            quests = ", ".join(f"`{md_escape(value)}`" for value in context["questIds"])
            lines.append(
                f"| `{md_escape(entry['storyKey'])}` | {missions} | {quests} | "
                f"`{md_escape(context['switcherGroupId'])}` | "
                f"`{md_escape(context['clusterId'])}` | "
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
        f"stateContext={counts['stateContextFiles']} "
        f"levelScoped={counts['relationCounts'][RELATION_LEVEL_SCOPED]} "
        f"characterScoped={counts['relationCounts'][RELATION_CHARACTER_SCOPED]} "
        f"none={counts['relationCounts'][RELATION_NONE]}"
    )
    print(f"wrote {rel_path(json_path)}")
    print(f"wrote {rel_path(md_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
