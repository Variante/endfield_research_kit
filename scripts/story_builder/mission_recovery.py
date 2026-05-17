#!/usr/bin/env python3
"""Recover evidence-only mission timelines for the WebUI Story builder.

This script builds a mission-level timeline graph from source data only:

- MissionRuntimeAsset quest flow, properties, objective conditions, tracking,
  failed-condition guards, and client action maps.
- recovered AnimeStudio timeline line-order evidence from
  export_full/recovered/AnimeStudio-cli/timeline_line_orders.json.

It intentionally does not use filename order, numeric suffix fallback, generated
UI rank, or any other guessed ordering as timeline evidence. When the source only
proves that events belong to the same quest/layer, the output keeps them grouped
instead of flattening them into a made-up sequence.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = ROOT / "export_full"
DEFAULT_MRA_DIR = EXPORT_ROOT / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset"
DEFAULT_TIMELINE_ORDERS = EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "timeline_line_orders.json"
DEFAULT_GENERATED_MISSION_DIR = ROOT / "webui" / "data" / "lang" / "CN" / "mission"
DEFAULT_OUT_JSON = ROOT / "reports" / "mission_timeline_recovery_CN.json"
DEFAULT_OUT_MD = ROOT / "reports" / "mission_timeline_recovery_CN.md"

# Mission ID prefixes the WebUI builders treat as authored story missions.
# Tutorial / debug buckets (db, dm, hidden, map*) are excluded.
TARGET_MISSION_PREFIXES = ("e", "a", "gm", "c", "sm", "f", "m")

# Edge-kind strength classification, mirroring scripts/story_builder/language_bundle.py.
# Strong: authored/decoded chronological evidence.
# Weak: file/byte-offset proximity, table-collection order, or share-only hints.
STRONG_ORDER_EDGE_KINDS = frozenset({
    "questSequence",
    "questPrev",
    "questFailGuard",
    "authoredDirect",
    "authoredMenu",
    "levelscriptSceneChain",
    "radioContinuation",
})
WEAK_ORDER_EDGE_KINDS = frozenset({
    "levelscriptChain",
    "levelscriptFileOrder",
    "levelscriptCrossFileOrder",
    "levelDataQuestRef",
    "prtsCollectionOrder",
    "timelineShare",
})

EVIDENCE_POLICY = {
    "uses": [
        "MissionRuntimeAsset explicit fields",
        "MissionRuntimeAsset client action maps",
        "recovered AnimeStudio timeline clip records",
        "source-backed LevelScriptData and AnimeStudio edges recovered by scripts/story_builder/build.py",
    ],
    "rejects": [
        "filename order",
        "numeric suffix fallback",
        "generated UI rank",
        "raw table row order as chronology",
    ],
}

DIALOG_REF_FIELDS = ("_dialogId", "snsDialogId")
CUTSCENE_REF_FIELDS = ("_cutsceneId",)
REMOTECOMM_REF_FIELDS = ("_remoteCommId",)
RADIO_REF_FIELDS = ("_radioId",)
STORY_REF_FIELDS = DIALOG_REF_FIELDS + CUTSCENE_REF_FIELDS + REMOTECOMM_REF_FIELDS + RADIO_REF_FIELDS

CUTSCENE_HASH_SUFFIX_RE = re.compile(r"_p[0-9A-Fa-f]{8,16}$")
CUTSCENE_COMPONENT_SUFFIX_RE = re.compile(
    r"_(?:Actor|Audio|Effect|Light|Others)(?:_(?:cam_\d+|AU|CHI|CN|EN|ENG|JP|KO|KR|ENV))*$",
    re.IGNORECASE,
)
CUTSCENE_LOCALE_SUFFIX_RE = re.compile(r"_(?:CHI|CN|EN|ENG|JP|KO|KR|ENV)$", re.IGNORECASE)

OBJECTIVE_FLAG_FIELDS = (
    "multiple",
    "useMultipleDescription",
    "muteTrack",
    "mapSubCondition",
    "mapTrackingToMultiDesc",
    "isObjectiveWrapper",
    "isBlockObjective",
)

CONDITION_FIELD_GROUPS = {
    "storyRefs": STORY_REF_FIELDS,
    "questRefs": ("_questId",),
    "missionRefs": ("_missionId",),
    "sceneRefs": ("_sceneId", "_levelId"),
    "itemRefs": ("_itemId", "itemId", "_itemIds", "itemIds", "needItemIds"),
    "propertyKeys": ("_key",),
    "compareValues": ("_compareValue", "_progressToCompare"),
    "comparers": ("_comparer",),
    "finishIds": ("_finishId",),
    "scriptIds": ("_scriptId",),
    "logicIds": ("_entityId",),
    "triggerSlotIds": ("_triggerSlotIdOutput",),
    "succeedIds": ("_succeedId",),
    "newStates": ("_newState",),
    "oldStates": ("_oldState",),
    "eventTriggerIds": ("level_event_id_trigger",),
}

TRACKING_COPY_FIELDS = (
    "sceneId",
    "npcProxyId",
    "missionAreaId",
    "jumpId",
    "guidingArea",
    "shapeType",
    "radius",
    "routePointCount",
    "snsDialogId",
)

_ROOT_RESOLVED = ROOT.resolve()
_REL_PATH_CACHE: dict[str, str] = {}


def rel_path(path: Path) -> str:
    cache_key = str(path)
    if cache_key in _REL_PATH_CACHE:
        return _REL_PATH_CACHE[cache_key]
    try:
        result = path.relative_to(ROOT).as_posix()
    except ValueError:
        try:
            result = path.resolve().relative_to(_ROOT_RESOLVED).as_posix()
        except (OSError, ValueError):
            result = path.as_posix()
    _REL_PATH_CACHE[cache_key] = result
    return result


def source_ref(path: Path, field: str) -> dict:
    return {"file": rel_path(path), "field": field}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def short_type(value: str) -> str:
    return str(value or "").split(",", 1)[0].rsplit(".", 1)[-1]


def natural_key(value: str) -> tuple:
    parts = re.split(r"(\d+)", str(value or ""))
    return tuple(int(part) if part.isdigit() else part for part in parts)


def unique_preserve(values: list[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def const_value(value: Any) -> Any:
    if isinstance(value, dict) and "constValue" in value:
        return value.get("constValue")
    return value


def is_empty_value(value: Any) -> bool:
    return value in (None, "", [], {}, False)


def walk_field_values(node: Any, field_name: str, path: str = "$"):
    if isinstance(node, dict):
        for key, value in node.items():
            child_path = f"{path}.{key}"
            if key == field_name:
                if isinstance(value, dict) and "constValue" in value:
                    yield value.get("constValue"), f"{child_path}.constValue"
                else:
                    yield value, child_path
            else:
                yield from walk_field_values(value, field_name, child_path)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from walk_field_values(item, field_name, f"{path}[{index}]")


def walk_typed_nodes(node: Any, path: str = "$"):
    if isinstance(node, dict):
        if node.get("$type"):
            yield node, path
        for key, value in node.items():
            yield from walk_typed_nodes(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from walk_typed_nodes(item, f"{path}[{index}]")


def flatten_primitives(node: Any, path: str = "$", *, max_items: int = 80) -> list[dict]:
    out: list[dict] = []

    def visit(value: Any, value_path: str) -> None:
        if len(out) >= max_items:
            return
        if isinstance(value, dict):
            if "constValue" in value and len(value) <= 2:
                out.append({"field": value_path, "value": value.get("constValue")})
                return
            for key, child in value.items():
                if key == "$type":
                    continue
                visit(child, f"{value_path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{value_path}[{index}]")
        elif not is_empty_value(value):
            out.append({"field": value_path, "value": value})

    visit(node, path)
    return out


def canonical_cutscene_key(value: str) -> str:
    if not isinstance(value, str):
        return ""
    key = value.strip()
    if key.startswith("cutscene_"):
        pass
    elif match := re.match(r"^(?:f|m|fm)_(cutscene_.+)$", key, re.IGNORECASE):
        key = match.group(1)
    else:
        return ""
    key = "cutscene_" + key[len("cutscene_"):]
    key = CUTSCENE_HASH_SUFFIX_RE.sub("", key)
    key = CUTSCENE_COMPONENT_SUFFIX_RE.sub("", key)
    key = CUTSCENE_LOCALE_SUFFIX_RE.sub("", key)
    return key if key != "cutscene" else ""


def classify_story_ref(field_name: str, raw_value: str) -> tuple[str, str]:
    value = str(raw_value or "").strip()
    if not value:
        return "", ""
    if field_name == "snsDialogId" or value.startswith("sns_"):
        return "sns", value
    if field_name == "_dialogId" or value.startswith("dlg_"):
        return "dlg", value
    if field_name == "_cutsceneId":
        return "cutscene", canonical_cutscene_key(value) or value
    if field_name == "_remoteCommId" or value.startswith("remotecomm_"):
        return "remotecomm", value
    if field_name == "_radioId" or value.startswith("radio_"):
        return "radio", value
    return "storyRef", value


def extract_story_refs(node: Any, source_path: Path, root_field: str) -> list[dict]:
    refs: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for field_name in STORY_REF_FIELDS:
        for value, field_path in walk_field_values(node, field_name, root_field):
            if not isinstance(value, str) or not value:
                continue
            kind, scene_key = classify_story_ref(field_name, value)
            key = (field_name, value, scene_key)
            if key in seen:
                continue
            seen.add(key)
            refs.append({
                "kind": kind,
                "rawId": value,
                "sceneKey": scene_key,
                "source": source_ref(source_path, field_path),
            })
    return refs


def extract_condition_leaves(cond: Any, source_path: Path, root_field: str) -> list[dict]:
    leaves: list[dict] = []
    if not isinstance(cond, dict):
        return leaves
    for node, node_path in walk_typed_nodes(cond, root_field):
        typ = short_type(node.get("$type", ""))
        if typ == "CombineCondition":
            continue
        leaf: dict[str, Any] = {
            "type": typ or "Unknown",
            "source": source_ref(source_path, node_path),
        }
        for group_name, field_names in CONDITION_FIELD_GROUPS.items():
            rows: list[dict] = []
            for field_name in field_names:
                for value, value_path in walk_field_values(node, field_name, node_path):
                    value = const_value(value)
                    if is_empty_value(value):
                        continue
                    rows.append({
                        "field": value_path,
                        "value": value,
                    })
            if rows:
                leaf[group_name] = unique_preserve(rows)
        leaves.append(leaf)
    return leaves


def condition_eval_strings(cond: Any) -> list[dict]:
    out: list[dict] = []
    if not isinstance(cond, dict):
        return out
    for node, node_path in walk_typed_nodes(cond):
        if short_type(node.get("$type", "")) != "CombineCondition":
            continue
        eval_string = node.get("conditionEvalString")
        if isinstance(eval_string, str) and eval_string:
            out.append({"field": node_path + ".conditionEvalString", "value": eval_string})
    return out


def vector3(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    try:
        return {
            "x": float(value.get("x", 0.0)),
            "y": float(value.get("y", 0.0)),
            "z": float(value.get("z", 0.0)),
        }
    except (TypeError, ValueError):
        return None


def extract_tracking_rows(obj: dict, source_path: Path, obj_field: str) -> list[dict]:
    rows: list[dict] = []
    for index, info in enumerate(obj.get("trackingInfoList") or []):
        if not isinstance(info, dict):
            continue
        row: dict[str, Any] = {
            "type": short_type(info.get("$type", "")) or "TrackingInfo",
            "source": source_ref(source_path, f"{obj_field}.trackingInfoList[{index}]"),
        }
        for field_name in TRACKING_COPY_FIELDS:
            value = info.get(field_name)
            if not is_empty_value(value):
                key = "scene" if field_name == "sceneId" else field_name
                row[key] = value
        for field_name in ("trackingPos", "position", "rotation"):
            vec = vector3(info.get(field_name))
            if vec is not None:
                row[field_name] = vec
        rows.append(row)
    return rows


def extract_objectives(quest: dict, source_path: Path, quest_field: str) -> list[dict]:
    out: list[dict] = []
    for index, obj in enumerate(quest.get("objectiveList") or []):
        if not isinstance(obj, dict):
            continue
        obj_field = f"{quest_field}.objectiveList[{index}]"
        row: dict[str, Any] = {
            "index": index + 1,
            "source": source_ref(source_path, obj_field),
        }
        description = obj.get("description")
        if isinstance(description, dict) and description.get("key"):
            row["descriptionKey"] = description["key"]
            row["descriptionSource"] = source_ref(source_path, f"{obj_field}.description.key")
        multiple_description = [
            item.get("key")
            for item in (obj.get("multipleDescription") or [])
            if isinstance(item, dict) and item.get("key")
        ]
        if multiple_description:
            row["multipleDescriptionKeys"] = multiple_description
        flags = {
            field_name: obj.get(field_name)
            for field_name in OBJECTIVE_FLAG_FIELDS
            if obj.get(field_name)
        }
        if flags:
            row["flags"] = flags
        if obj.get("showProgressMethod") not in (None, 0):
            row["showProgressMethod"] = obj.get("showProgressMethod")
        if obj.get("wrapperSystemType") not in (None, 0):
            row["wrapperSystemType"] = obj.get("wrapperSystemType")
        if obj.get("objectiveWrapperStep") not in (None, 0):
            row["objectiveWrapperStep"] = obj.get("objectiveWrapperStep")
        tracking = extract_tracking_rows(obj, source_path, obj_field)
        if tracking:
            row["tracking"] = tracking
        leaves = extract_condition_leaves(obj.get("condition"), source_path, f"{obj_field}.condition")
        if leaves:
            row["conditionLeaves"] = leaves
            row["conditionTypes"] = unique_preserve([leaf["type"] for leaf in leaves if leaf.get("type")])
        evals = condition_eval_strings(obj.get("condition"))
        if evals:
            row["conditionEvalStrings"] = [
                {**item, "source": source_ref(source_path, item["field"])}
                for item in evals
            ]
        if len(row) > 2:
            out.append(row)
    return out


def extract_failed_condition(quest: dict, source_path: Path, quest_field: str) -> dict | None:
    failed = quest.get("failedCondition")
    if not isinstance(failed, dict):
        return None
    payload: dict[str, Any] = {
        "source": source_ref(source_path, f"{quest_field}.failedCondition"),
        "conditionLeaves": extract_condition_leaves(failed, source_path, f"{quest_field}.failedCondition"),
    }
    evals = condition_eval_strings(failed)
    if evals:
        payload["conditionEvalStrings"] = [
            {**item, "source": source_ref(source_path, item["field"])}
            for item in evals
        ]
    return payload if payload.get("conditionLeaves") or payload.get("conditionEvalStrings") else None


def simplify_property_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    value_array = value.get("valueArray")
    if isinstance(value_array, list):
        simplified = []
        for item in value_array:
            if not isinstance(item, dict):
                simplified.append(item)
                continue
            if item.get("valueString"):
                simplified.append(item.get("valueString"))
            elif "valueBit64" in item:
                simplified.append(item.get("valueBit64"))
            else:
                simplified.append(item)
        return {
            "type": value.get("type"),
            "values": simplified,
        }
    return value


def extract_properties(raw: dict, source_path: Path) -> dict:
    properties = []
    for index, item in enumerate(raw.get("properties") or []):
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        if not key:
            continue
        properties.append({
            "key": key,
            "value": simplify_property_value(item.get("value")),
            "source": source_ref(source_path, f"properties[{index}]"),
        })
    payload: dict[str, Any] = {}
    if properties:
        payload["properties"] = properties
    if raw.get("propertyIdToKeyMap"):
        payload["propertyIdToKeyMap"] = raw["propertyIdToKeyMap"]
        payload["propertyIdToKeyMapSource"] = source_ref(source_path, "propertyIdToKeyMap")
    if raw.get("propertyKeyToIdMap"):
        payload["propertyKeyToIdMap"] = raw["propertyKeyToIdMap"]
        payload["propertyKeyToIdMapSource"] = source_ref(source_path, "propertyKeyToIdMap")
    return payload


def extract_client_actions(raw: dict, source_path: Path) -> list[dict]:
    action_list = (((raw.get("actionMapRaw") or {}).get("dataMap") or {}).get("actionList") or [])
    actions_by_id: dict[int, dict] = {}
    for index, action in enumerate(action_list):
        if not isinstance(action, dict):
            continue
        action_id = action.get("_ID")
        if not isinstance(action_id, int):
            continue
        action_field = f"actionMapRaw.dataMap.actionList[{index}]"
        refs = extract_story_refs(action, source_path, action_field)
        actions_by_id[action_id] = {
            "actionId": action_id,
            "actionType": short_type(action.get("$type", "")) or "ClientAction",
            "source": source_ref(source_path, action_field),
            "storyRefs": refs,
            "fields": flatten_primitives(action, action_field),
        }

    out: list[dict] = []
    keys = raw.get("clientActionMapKey") or []
    values = raw.get("clientActionMapValue") or []
    for index, (key_row, action_id) in enumerate(zip(keys, values)):
        if not isinstance(key_row, dict) or not isinstance(action_id, int):
            continue
        action = actions_by_id.get(action_id)
        if not action:
            continue
        row = {
            "questId": key_row.get("questId") or "",
            "actionSlot": key_row.get("action"),
            "actionId": action_id,
            "actionType": action.get("actionType"),
            "source": source_ref(source_path, f"clientActionMapKey[{index}]"),
            "valueSource": source_ref(source_path, f"clientActionMapValue[{index}]"),
            "actionSource": action.get("source"),
        }
        if action.get("storyRefs"):
            row["storyRefs"] = action["storyRefs"]
        if action.get("fields"):
            row["fields"] = action["fields"]
        out.append(row)
    return out


def quest_tail_number(quest_id: str) -> int:
    match = re.search(r"#(\d+)$", str(quest_id or ""))
    return int(match.group(1)) if match else 10**9


def build_quest_layers(quests: list[dict]) -> list[dict]:
    grouped: dict[Any, list[dict]] = defaultdict(list)
    for quest in quests:
        grouped[quest.get("flowIndex")].append(quest)
    layers = []
    for flow_index, bucket in sorted(grouped.items(), key=lambda item: (item[0] if isinstance(item[0], (int, float)) else 10**9, str(item[0]))):
        layers.append({
            "flowIndex": flow_index,
            "questIds": [
                quest["questId"]
                for quest in sorted(bucket, key=lambda item: (quest_tail_number(item["questId"]), item["questId"]))
            ],
            "source": "MissionRuntimeAsset.questDic[*].flowIndex",
            "note": "Members share an authored flowIndex; order inside the layer is not promoted unless prevQuestIdList edges prove it.",
        })
    return layers


def build_quest_edges(quests: list[dict], source_path: Path) -> tuple[list[dict], list[dict]]:
    quest_ids = {quest["questId"] for quest in quests}
    edges: list[dict] = []
    unresolved: list[dict] = []
    for quest in quests:
        for prev_id in quest.get("prevQuestIds") or []:
            if prev_id not in quest_ids:
                unresolved.append({
                    "kind": "missingPrevQuest",
                    "questId": quest["questId"],
                    "prevQuestId": prev_id,
                    "source": source_ref(source_path, f"questDic.{quest['questId']}.prevQuestIdList"),
                })
                continue
            edge = {
                "from": prev_id,
                "to": quest["questId"],
                "kind": "questPrev",
                "source": source_ref(source_path, f"questDic.{quest['questId']}.prevQuestIdList"),
            }
            if quest.get("failedCondition"):
                edge["guardSource"] = quest["failedCondition"]["source"]
                edge["guard"] = quest["failedCondition"]
            edges.append(edge)
    return edges, unresolved


def build_quest_tree(quests: list[dict], edges: list[dict]) -> dict:
    """Build an explicit prevQuestIdList tree without inventing chronology."""
    quest_ids = {quest["questId"] for quest in quests if quest.get("questId")}
    quest_order = [quest["questId"] for quest in quests if quest.get("questId")]
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    edge_source_by_pair: dict[tuple[str, str], dict] = {}
    for edge in edges:
        if edge.get("kind") != "questPrev":
            continue
        parent = edge.get("from") or ""
        child = edge.get("to") or ""
        if parent not in quest_ids or child not in quest_ids:
            continue
        children_by_parent[parent].append(child)
        if edge.get("source"):
            edge_source_by_pair[(parent, child)] = edge["source"]

    for parent, children in children_by_parent.items():
        children_by_parent[parent] = sorted(unique_preserve(children), key=natural_key)

    root_ids = [
        quest["questId"]
        for quest in quests
        if quest.get("questId") and not quest.get("prevQuestIds")
    ]
    roots_seen = set(root_ids)
    root_ids = [quest_id for quest_id in quest_order if quest_id in roots_seen]
    expanded: set[str] = set()
    loops: list[dict] = []
    loop_keys: set[tuple[str, ...]] = set()

    def walk(quest_id: str, path: list[str]) -> dict:
        if quest_id in path:
            loop_start = path.index(quest_id)
            loop_path = path[loop_start:] + [quest_id]
            loop_key = tuple(loop_path)
            source = edge_source_by_pair.get((path[-1], quest_id)) if path else None
            if loop_key not in loop_keys:
                loop_keys.add(loop_key)
                row = {
                    "from": path[-1] if path else "",
                    "to": quest_id,
                    "questIds": loop_path,
                    "source": source,
                }
                loops.append({key: value for key, value in row.items() if value})
            node = {
                "questId": quest_id,
                "loop": True,
                "loopPath": loop_path,
            }
            if source:
                node["source"] = source
            return node

        node: dict[str, Any] = {"questId": quest_id}
        children = children_by_parent.get(quest_id) or []
        if quest_id in expanded:
            node["reused"] = True
            return node
        expanded.add(quest_id)
        if children:
            node["children"] = [walk(child, [*path, quest_id]) for child in children]
        return node

    root_nodes = [walk(root_id, []) for root_id in root_ids]
    unrooted_ids = [quest_id for quest_id in quest_order if quest_id not in expanded]
    unrooted_nodes = [walk(quest_id, []) for quest_id in unrooted_ids]

    return {
        "source": "MissionRuntimeAsset.questDic[*].prevQuestIdList",
        "rootSource": "quests with empty prevQuestIdList",
        "rootQuestIds": root_ids,
        "roots": root_nodes,
        "unrootedQuestIds": unrooted_ids,
        "unrootedRoots": unrooted_nodes,
        "loops": loops,
        "note": "Unrooted roots are coverage anchors for components without an explicit empty-prevQuestIdList entry; they are not promoted to chronology.",
    }


def build_branch_points(edges: list[dict], quests_by_id: dict[str, dict]) -> list[dict]:
    succ: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.get("kind") == "questPrev":
            succ[edge["from"]].append(edge["to"])
    branches: list[dict] = []
    for quest_id, children in sorted(succ.items(), key=lambda item: natural_key(item[0])):
        if len(children) < 2:
            continue
        row = {
            "questId": quest_id,
            "successorQuestIds": sorted(children, key=natural_key),
            "source": "MissionRuntimeAsset.questDic[*].prevQuestIdList",
        }
        guarded = [
            {
                "questId": child,
                "failedCondition": quests_by_id[child].get("failedCondition"),
            }
            for child in children
            if quests_by_id.get(child, {}).get("failedCondition")
        ]
        if guarded:
            row["guardedSuccessors"] = guarded
        branches.append(row)
    return branches


def timeline_to_dialog_key(timeline: str) -> str:
    value = str(timeline or "")
    for prefix in ("f_dlgtl_", "m_dlgtl_", "dlgtl_"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    value = re.sub(r"_sub_\d+$", "", value)
    return f"dlg_{value}" if value else ""


def line_stem(line_id: str) -> str:
    value = str(line_id or "")
    if value.startswith("dlg_"):
        return re.sub(r"_\d+$", "", value)
    if re.search(r"_\d+_\d+$", value):
        return re.sub(r"_\d+_\d+$", "", value)
    return re.sub(r"_\d+$", "", value) if re.search(r"_\d+$", value) else ""


def option_scene_key(option_id: str) -> str:
    value = str(option_id or "")
    if not value.startswith("option_dlg_"):
        return ""
    parts = value.rsplit("_", 2)
    if len(parts) != 3:
        return ""
    return parts[0][len("option_"):]


def timeline_entry_variants(entry: dict) -> list[dict]:
    variants = entry.get("variants")
    if isinstance(variants, list) and variants:
        return [item for item in variants if isinstance(item, dict)]
    return [entry]


def compact_timeline_entry(entry: dict, source_key: str, timeline_orders_path: Path) -> dict:
    line_timings = []
    for line in entry.get("lines") or []:
        if not isinstance(line, dict):
            continue
        row = {
            "id": line.get("id") or "",
            "start": line.get("start"),
            "duration": line.get("duration"),
        }
        for field_name in ("actor", "binding", "track", "trackName", "sourceFile"):
            if line.get(field_name):
                row[field_name] = line[field_name]
        line_timings.append(row)
    payload = {
        "sourceKey": source_key,
        "timeline": entry.get("timeline") or "",
        "dialogKey": entry.get("dialogKey") or timeline_to_dialog_key(entry.get("timeline") or ""),
        "lineIds": [str(line_id) for line_id in (entry.get("lineIds") or []) if str(line_id)],
        "lineTimings": line_timings,
        "source": source_ref(timeline_orders_path, source_key),
    }
    for field_name in ("source", "sourceRoots", "trackCount", "duplicateClipCount", "optionIds", "optionAnchors", "optionGroups", "optionPositions"):
        if entry.get(field_name):
            payload[field_name] = entry[field_name]
    return payload


def load_timeline_index(path: Path) -> tuple[dict[str, list[dict]], dict]:
    if not path.exists():
        return {}, {"missing": True, "path": rel_path(path)}
    payload = load_json(path)
    if not isinstance(payload, dict):
        return {}, {"invalid": True, "path": rel_path(path)}
    index: dict[str, list[dict]] = defaultdict(list)
    meta = dict(payload.get("_meta") or {})
    meta["path"] = rel_path(path)
    for key, entry in payload.items():
        if str(key).startswith("_") or not isinstance(entry, dict):
            continue
        for variant in timeline_entry_variants(entry):
            compact = compact_timeline_entry(variant, str(key), path)
            aliases = {
                str(key),
                compact.get("dialogKey") or "",
                timeline_to_dialog_key(compact.get("timeline") or ""),
            }
            for line_id in compact.get("lineIds") or []:
                aliases.add(line_stem(line_id))
            for option_id in compact.get("optionIds") or []:
                aliases.add(option_scene_key(option_id))
            for alias in aliases:
                if alias:
                    bucket = index.setdefault(alias, [])
                    identity = (
                        compact.get("timeline"),
                        tuple(compact.get("lineIds") or []),
                        json.dumps(compact.get("optionAnchors") or {}, sort_keys=True, ensure_ascii=False),
                    )
                    if not any(
                        (
                            item.get("timeline"),
                            tuple(item.get("lineIds") or []),
                            json.dumps(item.get("optionAnchors") or {}, sort_keys=True, ensure_ascii=False),
                        )
                        == identity
                        for item in bucket
                    ):
                        bucket.append(compact)
    for entries in index.values():
        entries.sort(key=lambda item: (-len(item.get("lineIds") or []), item.get("timeline") or ""))
    meta["indexedAliases"] = len(index)
    return dict(index), meta


def attach_timeline_evidence(refs: list[dict], timeline_index: dict[str, list[dict]]) -> tuple[dict[str, list[dict]], list[dict]]:
    evidence: dict[str, list[dict]] = {}
    unresolved: list[dict] = []
    for ref in refs:
        scene_key = ref.get("sceneKey") or ""
        kind = ref.get("kind") or ""
        if not scene_key:
            continue
        entries = timeline_index.get(scene_key, [])
        if entries:
            evidence.setdefault(scene_key, entries)
        elif kind == "dlg":
            unresolved.append({
                "kind": "missingDialogTimelineEvidence",
                "sceneKey": scene_key,
                "source": ref.get("source"),
            })
    return evidence, unresolved


def unique_append(bucket: list, value: Any) -> None:
    if value in (None, "", [], {}):
        return
    if value not in bucket:
        bucket.append(value)


def story_scene_kind(scene_key: str) -> str:
    if scene_key.startswith("dlg_"):
        return "dlg"
    if scene_key.startswith("black_"):
        return "black"
    if scene_key.startswith("cutscene_"):
        return "cutscene"
    if scene_key.startswith("remotecomm_"):
        return "remotecomm"
    if scene_key.startswith("radio_"):
        return "radio"
    if scene_key.startswith("sns_"):
        return "sns"
    return "storyRef"


def compact_source(source: Any) -> dict:
    if not isinstance(source, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("file", "field"):
        value = source.get(key)
        if value not in (None, "", [], {}):
            out[key] = value
    return out


def compact_edge_for_scene(edge: dict, scene_key: str, direction: str) -> dict:
    other_key = edge.get("from") if direction == "incoming" else edge.get("to")
    row = {
        "direction": direction,
        "neighbor": other_key or "",
        "kind": edge.get("kind") or "",
    }
    for key in ("sourceFiles", "sourceKeys", "questIds", "levelIds", "optionIds", "positions"):
        values = edge.get(key)
        if isinstance(values, list) and values:
            row[key] = values[:6]
    if edge.get("bundleSource"):
        row["bundleSource"] = compact_source(edge.get("bundleSource"))
    return row


def compact_sequence_for_scene(sequence: dict, index: int) -> dict:
    scene_keys = [
        str(value)
        for value in (sequence.get("sceneKeys") or [])
        if str(value or "")
    ]
    start = max(0, index - 2)
    end = min(len(scene_keys), index + 3)
    row = {
        "kind": sequence.get("kind") or "",
        "sourceFile": sequence.get("sourceFile") or "",
        "levelId": sequence.get("levelId") or "",
        "index": index,
        "previous": scene_keys[index - 1] if index > 0 else "",
        "next": scene_keys[index + 1] if index + 1 < len(scene_keys) else "",
        "window": scene_keys[start:end],
    }
    positions = sequence.get("positions")
    if isinstance(positions, list) and positions:
        row["positions"] = positions[:10]
    edge_count = sequence.get("edgeCount")
    if isinstance(edge_count, int) and edge_count:
        row["edgeCount"] = edge_count
    return {
        key: value
        for key, value in row.items()
        if value not in (None, "", [], {}, 0)
        or key in {"kind", "index", "window"}
    }


def compact_levelscript_step(step: Any) -> dict:
    if not isinstance(step, dict):
        return {}
    row: dict[str, Any] = {}
    for key in ("nodeKey", "payloadText", "localId", "nextId"):
        value = step.get(key)
        if value not in (None, "", [], {}):
            row[key] = value
    source = step.get("source")
    if isinstance(source, dict):
        compact_source = {
            key: source.get(key)
            for key in ("layout", "code", "kind", "uid", "start")
            if source.get(key) not in (None, "", [], {})
        }
        if compact_source:
            row["source"] = compact_source
    return row


def compact_hash_terminal(terminal: dict) -> dict:
    row = {
        "direction": terminal.get("direction") or "",
        "hash": terminal.get("hash") or "",
        "sourceFile": terminal.get("sourceFile") or "",
        "levelId": terminal.get("levelId") or "",
    }
    source_step = compact_levelscript_step(terminal.get("sourceStep"))
    hash_step = compact_levelscript_step(terminal.get("hashStep"))
    if source_step:
        row["sourceStep"] = source_step
    if hash_step:
        row["hashStep"] = hash_step
    return {
        key: value
        for key, value in row.items()
        if value not in (None, "", [], {})
    }


def compact_scene_timeline_entry(entry: dict) -> dict:
    row: dict[str, Any] = {}
    for key in ("sourceKey", "timeline", "dialogKey", "file"):
        value = entry.get(key)
        if value not in (None, "", [], {}):
            row[key] = value
    line_ids = entry.get("lineIds") or []
    if isinstance(line_ids, list):
        row["lineCount"] = len(line_ids)
    option_anchors = entry.get("optionAnchors") or {}
    if isinstance(option_anchors, dict):
        row["optionAnchorCount"] = len(option_anchors)
    option_routes = entry.get("optionRoutes") or {}
    if isinstance(option_routes, dict):
        row["optionRouteCount"] = len(option_routes)
    return row


def build_scene_placement_index(
    quests: list[dict],
    client_actions: list[dict],
    timeline_evidence: dict[str, list[dict]],
    source_backed_scene_edges: list[dict],
    source_backed_scene_sequences: list[dict] | None = None,
    source_backed_story_call_contexts: list[dict] | None = None,
    source_backed_hash_terminals: list[dict] | None = None,
) -> dict[str, dict]:
    """Build compact, evidence-only scene placement signals for one mission."""
    rows: dict[str, dict] = {}

    def ensure(scene_key: str) -> dict:
        scene_key = str(scene_key or "").strip()
        row = rows.get(scene_key)
        if row is None:
            row = {
                "sceneKey": scene_key,
                "kind": story_scene_kind(scene_key),
                "evidenceKinds": [],
                "questIds": [],
                "storyRefKinds": [],
                "storyRefCount": 0,
                "storyRefSources": [],
                "clientActionTypes": [],
                "clientActionCount": 0,
                "clientActionSources": [],
                "sourceBackedEdgeCount": 0,
                "incomingEdgeCount": 0,
                "outgoingEdgeCount": 0,
                "incomingEdges": [],
                "outgoingEdges": [],
                "sourceBackedSequenceCount": 0,
                "sequenceNeighborCount": 0,
                "sequenceNeighbors": [],
                "sourceBackedStoryCallContextCount": 0,
                "storyCallContexts": [],
                "sourceBackedHashTerminalCount": 0,
                "hashTerminals": [],
                "timelineEvidenceCount": 0,
                "timelines": [],
                "timelineEvidence": [],
            }
            rows[scene_key] = row
        return row

    for quest in quests:
        quest_id = str(quest.get("questId") or "")
        for ref in quest.get("storyRefs") or []:
            if not isinstance(ref, dict):
                continue
            scene_key = str(ref.get("sceneKey") or "").strip()
            if not scene_key:
                continue
            row = ensure(scene_key)
            row["storyRefCount"] += 1
            unique_append(row["questIds"], quest_id)
            unique_append(row["storyRefKinds"], ref.get("kind"))
            source = compact_source(ref.get("source"))
            if source and len(row["storyRefSources"]) < 8:
                row["storyRefSources"].append(source)

    for action in client_actions:
        quest_id = str(action.get("questId") or "")
        action_type = str(action.get("actionType") or "")
        for ref in action.get("storyRefs") or []:
            if not isinstance(ref, dict):
                continue
            scene_key = str(ref.get("sceneKey") or "").strip()
            if not scene_key:
                continue
            row = ensure(scene_key)
            row["clientActionCount"] += 1
            unique_append(row["questIds"], quest_id)
            unique_append(row["storyRefKinds"], ref.get("kind"))
            unique_append(row["clientActionTypes"], action_type)
            source = compact_source(ref.get("source"))
            if source and len(row["clientActionSources"]) < 8:
                row["clientActionSources"].append(source)

    for scene_key, entries in timeline_evidence.items():
        row = ensure(scene_key)
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            row["timelineEvidenceCount"] += 1
            unique_append(row["timelines"], entry.get("timeline") or entry.get("sourceKey"))
            if len(row["timelineEvidence"]) < 8:
                row["timelineEvidence"].append(compact_scene_timeline_entry(entry))

    for edge in source_backed_scene_edges:
        if not isinstance(edge, dict):
            continue
        from_key = str(edge.get("from") or "").strip()
        to_key = str(edge.get("to") or "").strip()
        if from_key:
            row = ensure(from_key)
            row["sourceBackedEdgeCount"] += 1
            row["outgoingEdgeCount"] += 1
            if len(row["outgoingEdges"]) < 10:
                row["outgoingEdges"].append(compact_edge_for_scene(edge, from_key, "outgoing"))
        if to_key:
            row = ensure(to_key)
            row["sourceBackedEdgeCount"] += 1
            row["incomingEdgeCount"] += 1
            if len(row["incomingEdges"]) < 10:
                row["incomingEdges"].append(compact_edge_for_scene(edge, to_key, "incoming"))

    for sequence in source_backed_scene_sequences or []:
        if not isinstance(sequence, dict):
            continue
        scene_keys = [
            str(scene_key).strip()
            for scene_key in (sequence.get("sceneKeys") or [])
            if str(scene_key or "").strip()
        ]
        for index, scene_key in enumerate(scene_keys):
            row = ensure(scene_key)
            row["sourceBackedSequenceCount"] += 1
            row["sequenceNeighborCount"] += 1
            if len(row["sequenceNeighbors"]) < 8:
                row["sequenceNeighbors"].append(
                    compact_sequence_for_scene(sequence, index)
                )

    for context in source_backed_story_call_contexts or []:
        if not isinstance(context, dict):
            continue
        scene_keys = [
            str(scene_key).strip()
            for scene_key in (context.get("sceneKeys") or [])
            if str(scene_key or "").strip()
        ]
        for index, scene_key in enumerate(scene_keys):
            row = ensure(scene_key)
            row["sourceBackedStoryCallContextCount"] += 1
            if len(row["storyCallContexts"]) < 8:
                row["storyCallContexts"].append(
                    compact_sequence_for_scene(context, index)
                )

    for terminal in source_backed_hash_terminals or []:
        if not isinstance(terminal, dict):
            continue
        scene_key = str(terminal.get("sceneKey") or "").strip()
        if not scene_key:
            continue
        row = ensure(scene_key)
        row["sourceBackedHashTerminalCount"] += 1
        if len(row["hashTerminals"]) < 8:
            row["hashTerminals"].append(compact_hash_terminal(terminal))

    compact_rows: dict[str, dict] = {}
    for scene_key, row in sorted(rows.items(), key=lambda item: natural_key(item[0])):
        if row["storyRefCount"]:
            unique_append(row["evidenceKinds"], "missionStoryRef")
        if row["clientActionCount"]:
            unique_append(row["evidenceKinds"], "clientActionStoryRef")
        if row["sourceBackedEdgeCount"]:
            unique_append(row["evidenceKinds"], "sourceBackedSceneEdge")
        if row["sourceBackedSequenceCount"]:
            unique_append(row["evidenceKinds"], "sourceBackedSceneSequence")
        if row["sourceBackedStoryCallContextCount"]:
            unique_append(row["evidenceKinds"], "sourceBackedStoryCallContext")
        if row["sourceBackedHashTerminalCount"]:
            unique_append(row["evidenceKinds"], "sourceBackedHashTerminal")
        if row["timelineEvidenceCount"]:
            unique_append(row["evidenceKinds"], "timelineEvidence")
        row["questIds"].sort(key=natural_key)
        row["storyRefKinds"].sort()
        row["clientActionTypes"].sort()
        row["timelines"].sort(key=natural_key)
        compact_rows[scene_key] = {
            key: value
            for key, value in row.items()
            if value not in (None, "", [], {}, 0)
            or key in {"sceneKey", "kind", "evidenceKinds"}
        }
    return compact_rows


SEQUENCE_SCENE_KINDS = {"dlg", "black", "cutscene", "remotecomm", "radio", "sns"}


def is_sequence_scene_key(scene_key: str) -> bool:
    return story_scene_kind(str(scene_key or "")) in SEQUENCE_SCENE_KINDS


def is_levelscript_hash_key(node_key: str) -> bool:
    return re.match(r"^#[0-9a-fA-F]{8}$", str(node_key or "")) is not None


def first_string(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def first_position(edge: dict) -> int:
    positions = edge.get("positions")
    if not isinstance(positions, list):
        return 10**9
    numeric_positions = [
        int(value)
        for value in positions
        if isinstance(value, (int, float))
    ]
    return min(numeric_positions) if numeric_positions else 10**9


def build_source_backed_scene_sequences(source_backed_scene_edges: list[dict]) -> list[dict]:
    """Group levelscript scene-chain edges into source-local scene sequences."""
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for edge in source_backed_scene_edges:
        if not isinstance(edge, dict) or edge.get("kind") != "levelscriptSceneChain":
            continue
        from_key = str(edge.get("from") or "").strip()
        to_key = str(edge.get("to") or "").strip()
        if not (is_sequence_scene_key(from_key) or is_sequence_scene_key(to_key)):
            continue
        source_file = first_string(edge.get("sourceFiles"))
        if not source_file:
            continue
        level_id = first_string(edge.get("levelIds"))
        grouped[(source_file, level_id)].append(edge)

    sequences: list[dict] = []

    def append_scene(scene_keys: list[str], scene_key: str) -> None:
        scene_key = str(scene_key or "").strip()
        if not scene_key or not is_sequence_scene_key(scene_key):
            return
        if not scene_keys or scene_keys[-1] != scene_key:
            scene_keys.append(scene_key)

    for (source_file, level_id), edges in sorted(
        grouped.items(),
        key=lambda item: natural_key("|".join(item[0])),
    ):
        scene_keys: list[str] = []
        positions: list[int] = []
        edge_count = 0

        def flush() -> None:
            nonlocal scene_keys, positions, edge_count
            if len(scene_keys) >= 2:
                sequences.append({
                    "kind": "levelscriptSceneChain",
                    "sourceFile": source_file,
                    "levelId": level_id,
                    "sceneKeys": scene_keys,
                    "positions": positions,
                    "edgeCount": edge_count,
                })
            scene_keys = []
            positions = []
            edge_count = 0

        for edge in sorted(
            edges,
            key=lambda item: (
                first_position(item),
                natural_key(str(item.get("from") or "")),
                natural_key(str(item.get("to") or "")),
            ),
        ):
            from_key = str(edge.get("from") or "").strip()
            to_key = str(edge.get("to") or "").strip()
            if scene_keys and is_sequence_scene_key(from_key) and scene_keys[-1] != from_key:
                flush()
            append_scene(scene_keys, from_key)
            append_scene(scene_keys, to_key)
            position = first_position(edge)
            if position != 10**9:
                positions.append(position)
            edge_count += 1
        flush()
    return sequences


def _unwrap_const(value: Any) -> Any:
    if isinstance(value, dict) and "constValue" in value:
        return value.get("constValue")
    return value


def _safe_key(value: Any) -> str:
    return str(value if value is not None else "").strip()


def decode_mission_script_conditions(raw: dict) -> list[dict]:
    """Decode MissionRuntime ``CheckLevelScriptProperty*`` conditions.

    Walks the MissionRuntimeAsset tree, latching the enclosing ``questId`` as
    it descends, and produces one record per node that carries a script id
    (i.e. references a specific LevelScript file). Mirrors the audit's
    ``collect_mission_runtime_script_conditions`` exactly so the two stay in
    sync.
    """
    out: list[dict] = []

    def walk(value: Any, quest_id: str = "") -> None:
        if isinstance(value, dict):
            next_quest_id = quest_id
            if isinstance(value.get("questId"), str):
                next_quest_id = value["questId"]
            type_name = _safe_key(value.get("$type"))
            has_script_id = "_scriptId" in value or "scriptId" in value
            if "LevelScript" in type_name or has_script_id:
                script_value = _unwrap_const(value.get("_scriptId", value.get("scriptId")))
                if isinstance(script_value, dict):
                    script_id = script_value.get("scriptId")
                else:
                    script_id = script_value
                map_id = _unwrap_const(
                    value.get(
                        "_mapId",
                        value.get(
                            "mapId",
                            value.get(
                                "_levelId",
                                value.get(
                                    "levelId",
                                    value.get("_sceneId", value.get("sceneId")),
                                ),
                            ),
                        ),
                    )
                )
                map_id_str = _safe_key(map_id)
                script_id_str = _safe_key(script_id)
                if map_id_str and script_id_str:
                    out.append({
                        "questId": next_quest_id,
                        "type": type_name,
                        "mapId": map_id_str,
                        "scriptId": script_id_str,
                        "key": _safe_key(_unwrap_const(value.get("_key", value.get("key")))),
                        "value": _unwrap_const(value.get("_value", value.get("value"))),
                    })
            for child in value.values():
                walk(child, next_quest_id)
        elif isinstance(value, list):
            for child in value:
                walk(child, quest_id)

    walk(raw)
    return out


def build_script_condition_ownership(mra_files: list[Path]) -> dict[tuple[str, str], list[str]]:
    """Pre-pass: map every (mapId, scriptId) to the missions whose quests
    reference it via a CheckLevelScriptProperty condition.

    Used by ``recover_mission`` to gate script-condition quest attachments —
    we only attach when exactly one mission owns the referenced LevelScript,
    so a shared script doesn't fan out to claim the same scene from multiple
    missions.
    """
    ownership: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path in mra_files:
        try:
            raw = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        mission_id = raw.get("missionId") or path.stem
        for condition in decode_mission_script_conditions(raw):
            ownership[(condition["mapId"], condition["scriptId"])].add(mission_id)
    return {key: sorted(values, key=natural_key) for key, values in ownership.items()}


def levelscript_path_components(source_file: str) -> tuple[str, str]:
    """Return ``(mapId, scriptId)`` parsed from a LevelScriptData JSON path.

    Returns ``("", "")`` when the path is not a LevelScriptData file. The path
    layout is ``.../LevelScriptData/<mapId>/<scriptId>.json``.
    """
    text = str(source_file or "").replace("\\", "/")
    if "/LevelScriptData/" not in text:
        return ("", "")
    tail = text.split("/LevelScriptData/", 1)[1]
    parts = tail.split("/")
    if len(parts) < 2:
        return ("", "")
    map_id = parts[0]
    script_stem = Path(parts[-1]).stem
    return (map_id, script_stem)


def build_levelscript_story_keys_map(
    scene_edges: list[dict],
) -> dict[tuple[str, str], set[str]]:
    """Reconstruct the story keys present in each LevelScript file from the
    mission's source-backed scene edges.

    Every edge carries the LevelScriptData JSON path it was decoded from in
    ``sourceFiles``. Both endpoints are story keys (or hash terminals) that
    appear in that file.
    """
    out: dict[tuple[str, str], set[str]] = defaultdict(set)
    for edge in scene_edges or []:
        if not isinstance(edge, dict):
            continue
        keys = [
            str(edge.get("from") or "").strip(),
            str(edge.get("to") or "").strip(),
        ]
        for source_file in edge.get("sourceFiles") or []:
            map_id, script_id = levelscript_path_components(source_file)
            if not (map_id and script_id):
                continue
            for key in keys:
                if key:
                    out[(map_id, script_id)].add(key)
    return out


def mission_id_matches_target_prefix(mission_id: str) -> bool:
    """Return True when mission_id starts with one of TARGET_MISSION_PREFIXES.

    The prefix list is the WebUI's authored-story-mission set. Longer prefixes
    (gm, sm) are checked before single-letter ones so `gm0m0` is not classified
    as starting with `g` (which isn't in the set anyway).
    """
    text = str(mission_id or "")
    if not text:
        return False
    for prefix in sorted(TARGET_MISSION_PREFIXES, key=len, reverse=True):
        if text.startswith(prefix):
            tail = text[len(prefix) :]
            if tail and (tail[0].isdigit() or tail[0] == "_"):
                return True
    return False


def build_scene_chunks(
    scene_placement: dict[str, dict],
    source_backed_scene_edges: list[dict],
    source_backed_scene_sequences: list[dict] | None,
    scene_timeline_evidence: dict[str, list[dict]] | None,
) -> tuple[list[dict], dict[str, str]]:
    """Group placed scenes into connected components by source-backed evidence.

    Edges (undirected, for connected-component grouping):

    - `sourceBackedSceneEdge` / decoded edge.kind: any (from, to) pair in
      `source_backed_scene_edges` (UID chains, quest-attach, DialogTree, etc.).
    - `levelscriptSceneChain` (sequence): consecutive pairs inside any
      `source_backed_scene_sequences[*].sceneKeys` chain.
    - `timelineShare`: scene keys that share a Timeline asset id
      (`scene_timeline_evidence[scene][*].timeline` or `sourceKey`).

    Chunks are numbered `c1`, `c2`, ... by natural order of each component's
    lexicographically-first scene key, so IDs are stable across reruns when the
    membership is stable. Isolated scenes (no joining edges) get their own
    singleton chunk.

    Returns (chunks, chunk_by_scene_key).
    """
    nodes: set[str] = {
        str(scene_key)
        for scene_key in (scene_placement or {}).keys()
        if str(scene_key)
    }
    if not nodes:
        return [], {}

    parent: dict[str, str] = {n: n for n in nodes}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        if a == b:
            return
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return
        if natural_key(root_a) <= natural_key(root_b):
            parent[root_b] = root_a
        else:
            parent[root_a] = root_b

    edge_records: list[tuple[str, str, str]] = []

    for edge in source_backed_scene_edges or []:
        if not isinstance(edge, dict):
            continue
        from_key = str(edge.get("from") or "").strip()
        to_key = str(edge.get("to") or "").strip()
        if not (from_key and to_key) or from_key == to_key:
            continue
        if from_key not in nodes or to_key not in nodes:
            continue
        kind = str(edge.get("kind") or "sourceBackedSceneEdge")
        edge_records.append((from_key, to_key, kind))

    for sequence in source_backed_scene_sequences or []:
        if not isinstance(sequence, dict):
            continue
        sequence_kind = str(sequence.get("kind") or "levelscriptSceneChain")
        scene_keys = [
            str(scene_key).strip()
            for scene_key in (sequence.get("sceneKeys") or [])
            if str(scene_key or "").strip()
        ]
        for a, b in zip(scene_keys, scene_keys[1:]):
            if a == b or a not in nodes or b not in nodes:
                continue
            edge_records.append((a, b, sequence_kind))

    if scene_timeline_evidence:
        timeline_to_scenes: dict[str, list[str]] = defaultdict(list)
        for scene_key, entries in scene_timeline_evidence.items():
            if scene_key not in nodes:
                continue
            for entry in entries or []:
                if not isinstance(entry, dict):
                    continue
                timeline_id = str(
                    entry.get("timeline") or entry.get("sourceKey") or ""
                ).strip()
                if not timeline_id:
                    continue
                timeline_to_scenes[timeline_id].append(scene_key)
        for timeline_id, scene_keys in timeline_to_scenes.items():
            unique_scene_keys = list(dict.fromkeys(scene_keys))
            if len(unique_scene_keys) < 2:
                continue
            anchor = unique_scene_keys[0]
            for other in unique_scene_keys[1:]:
                edge_records.append((anchor, other, "timelineShare"))

    for a, b, _kind in edge_records:
        union(a, b)

    component_members: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        component_members[find(node)].append(node)

    chunk_edge_kinds: dict[str, set[str]] = defaultdict(set)
    chunk_internal_edge_count: dict[str, int] = defaultdict(int)
    for a, _b, kind in edge_records:
        root = find(a)
        chunk_edge_kinds[root].add(kind)
        chunk_internal_edge_count[root] += 1

    sorted_roots = sorted(component_members.keys(), key=natural_key)
    chunks: list[dict] = []
    chunk_by_scene_key: dict[str, str] = {}
    for index, root in enumerate(sorted_roots, start=1):
        chunk_id = f"c{index}"
        members = sorted(component_members[root], key=natural_key)
        edge_kinds_set = chunk_edge_kinds.get(root, set())
        edge_kinds = sorted(edge_kinds_set)
        scene_kinds = sorted(
            {kind for kind in (story_scene_kind(scene_key) for scene_key in members) if kind}
        )
        if edge_kinds_set & STRONG_ORDER_EDGE_KINDS:
            strength = "strong"
        elif edge_kinds_set:
            strength = "weak"
        else:
            strength = "unanchored"
        chunks.append({
            "id": chunk_id,
            "sceneKeys": members,
            "sceneCount": len(members),
            "sceneKinds": scene_kinds,
            "edgeKinds": edge_kinds,
            "internalEdgeCount": chunk_internal_edge_count.get(root, 0),
            "strength": strength,
            "isolated": len(members) == 1 and not edge_kinds_set,
        })
        for scene_key in members:
            chunk_by_scene_key[scene_key] = chunk_id
    return chunks, chunk_by_scene_key


def attach_chunks_to_quest_tree(
    quest_tree: dict,
    chunks: list[dict],
    scene_placement: dict[str, dict],
    chunk_order: dict | None = None,
) -> dict:
    """Annotate every quest-tree node with the chunks attached to its quest.

    A chunk attaches to a quest when at least one of the chunk's scenes lists
    that quest in ``scenePlacement[<sceneKey>].questIds``. The ordering of
    chunks within a quest follows the chunk-order topological order when
    available (Phase 2 quest-DAG resolver), otherwise natural order.

    Also returns the set of chunks not attached to any quest as
    ``unattachedToQuestChunkIds`` on the returned tree dict.
    """
    chunks_by_quest: dict[str, set[str]] = defaultdict(set)
    quests_by_chunk: dict[str, set[str]] = defaultdict(set)
    for chunk in chunks or []:
        chunk_id = str(chunk.get("id") or "")
        if not chunk_id:
            continue
        for scene_key in chunk.get("sceneKeys") or []:
            for quest_id in (scene_placement.get(scene_key) or {}).get("questIds") or []:
                quest_id_str = str(quest_id or "").strip()
                if quest_id_str:
                    chunks_by_quest[quest_id_str].add(chunk_id)
                    quests_by_chunk[chunk_id].add(quest_id_str)

    chunk_order_index: dict[str, int] = {}
    for index, edge in enumerate((chunk_order or {}).get("edges") or []):
        chunk_order_index.setdefault(str(edge.get("from") or ""), index)
        chunk_order_index.setdefault(str(edge.get("to") or ""), index + 0.5)

    def sort_chunk_ids(chunk_ids: list[str]) -> list[str]:
        return sorted(
            chunk_ids,
            key=lambda cid: (
                chunk_order_index.get(cid, float("inf")),
                natural_key(cid),
            ),
        )

    def walk(node: dict) -> None:
        if not isinstance(node, dict):
            return
        quest_id = str(node.get("questId") or "")
        attached = sorted(chunks_by_quest.get(quest_id, set()), key=natural_key)
        if attached:
            node["attachedChunkIds"] = sort_chunk_ids(attached)
        for child in node.get("children") or []:
            walk(child)

    for root in quest_tree.get("roots") or []:
        walk(root)
    for root in quest_tree.get("unrootedRoots") or []:
        walk(root)

    attached_chunk_ids = set(quests_by_chunk.keys())
    all_chunk_ids = [str(chunk.get("id") or "") for chunk in chunks or [] if chunk.get("id")]
    unattached = [cid for cid in all_chunk_ids if cid not in attached_chunk_ids]
    quest_tree["unattachedToQuestChunkIds"] = sort_chunk_ids(unattached)
    quest_tree["chunkAttachmentSummary"] = {
        "attachedChunkCount": len(attached_chunk_ids),
        "unattachedChunkCount": len(unattached),
        "questsWithChunkCount": len(chunks_by_quest),
    }
    return quest_tree


def _quest_descendants(quest_edges: list[dict]) -> dict[str, set[str]]:
    """Return quest_id -> set of quest_ids reachable as later quests in the DAG.

    Quest edges use kind='questPrev' with from=predecessor, to=successor — the
    same direction as chronology. Reachability is exclusive of the source
    quest itself; cycles (very rare but they exist) terminate via the visited
    set.
    """
    succ: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set()
    for edge in quest_edges or []:
        if not isinstance(edge, dict):
            continue
        if edge.get("kind") != "questPrev":
            continue
        from_id = str(edge.get("from") or "").strip()
        to_id = str(edge.get("to") or "").strip()
        if not from_id or not to_id:
            continue
        succ[from_id].add(to_id)
        nodes.add(from_id)
        nodes.add(to_id)

    descendants: dict[str, set[str]] = {}

    def visit(start: str) -> set[str]:
        if start in descendants:
            return descendants[start]
        seen: set[str] = set()
        stack = [start]
        while stack:
            current = stack.pop()
            for child in succ.get(current, ()):
                if child in seen or child == start:
                    continue
                seen.add(child)
                stack.append(child)
        descendants[start] = seen
        return seen

    for node in nodes:
        visit(node)
    return descendants


def build_chunk_order(
    chunks: list[dict],
    scene_placement: dict[str, dict],
    quest_edges: list[dict],
) -> dict:
    """Recover directed cross-chunk order from quest-DAG attachments.

    Scene-to-quest attachments come from `scenePlacement[<sceneKey>].questIds`,
    which is populated by `build_scene_placement_index` from
    MissionRuntimeAsset quest `storyRefs` and client-action `storyRefs`. A
    chunk's `attachedQuests` is the union of its scenes' quest attachments.

    Emit X → Y when:

    1. Both X and Y have non-empty quest attachments.
    2. Their quest sets are disjoint.
    3. Every quest qY in Y is a strict descendant of every quest qX in X in
       the quest DAG (built from `questEdges` of kind ``questPrev``).

    After collecting all such pairs, run transitive reduction so the output
    is minimal (X→Y is dropped when there exists Z with X→Z and Z→Y in the
    edge set).

    Pairs that share a quest go under ``parallel`` (co-quest, not orderable
    by this signal). Pairs with disjoint quests but no provable ordering go
    under ``incomparable`` — typical of quest branches or scenes attached to
    different branches of a fork.

    Returns a dict with keys:
        edges: list of {from, to, kind, fromQuests, toQuests, transitiveOnly}
        parallel: list of [chunkA, chunkB]  # share ≥ 1 quest
        incomparable: list of [chunkA, chunkB]  # disjoint, no order
        unattachedChunkIds: list of chunk ids with no quest attachments
        attachedQuestsByChunk: dict chunkId -> sorted quest_id list
    """
    descendants = _quest_descendants(quest_edges)
    chunk_quests: dict[str, set[str]] = {}
    for chunk in chunks:
        chunk_id = str(chunk.get("id") or "")
        attached: set[str] = set()
        for scene_key in chunk.get("sceneKeys") or []:
            for quest_id in (scene_placement.get(scene_key) or {}).get("questIds") or []:
                quest_id_str = str(quest_id or "").strip()
                if quest_id_str:
                    attached.add(quest_id_str)
        chunk_quests[chunk_id] = attached

    attached_ids = [cid for cid, quests in chunk_quests.items() if quests]
    unattached_ids = [cid for cid, quests in chunk_quests.items() if not quests]

    parallel_pairs: list[tuple[str, str]] = []
    incomparable_pairs: list[tuple[str, str]] = []
    raw_edges: dict[tuple[str, str], dict] = {}

    def chunk_descendants(quests: set[str]) -> set[str]:
        result: set[str] = set()
        for q in quests:
            result |= descendants.get(q, set())
        return result

    for i, chunk_a in enumerate(attached_ids):
        quests_a = chunk_quests[chunk_a]
        desc_a = chunk_descendants(quests_a)
        for chunk_b in attached_ids[i + 1 :]:
            quests_b = chunk_quests[chunk_b]
            if quests_a & quests_b:
                parallel_pairs.append((chunk_a, chunk_b))
                continue
            desc_b = chunk_descendants(quests_b)
            # X strictly precedes Y when every quest in Y is reachable from
            # every quest in X via questPrev edges.
            a_precedes_b = all(quest in desc_a for quest in quests_b)
            b_precedes_a = all(quest in desc_b for quest in quests_a)
            if a_precedes_b and not b_precedes_a:
                raw_edges[(chunk_a, chunk_b)] = {
                    "from": chunk_a,
                    "to": chunk_b,
                    "kind": "questDag",
                    "fromQuests": sorted(quests_a, key=natural_key),
                    "toQuests": sorted(quests_b, key=natural_key),
                }
            elif b_precedes_a and not a_precedes_b:
                raw_edges[(chunk_b, chunk_a)] = {
                    "from": chunk_b,
                    "to": chunk_a,
                    "kind": "questDag",
                    "fromQuests": sorted(quests_b, key=natural_key),
                    "toQuests": sorted(quests_a, key=natural_key),
                }
            else:
                incomparable_pairs.append((chunk_a, chunk_b))

    # Transitive reduction. We only know edges between attached chunks, all
    # marked as questDag. Drop X→Y when X→Z and Z→Y are both present.
    successors_by_chunk: dict[str, set[str]] = defaultdict(set)
    for (src, dst) in raw_edges:
        successors_by_chunk[src].add(dst)
    transitive_to_drop: set[tuple[str, str]] = set()
    for (src, dst) in raw_edges:
        for mid in successors_by_chunk[src]:
            if mid == dst:
                continue
            if dst in successors_by_chunk[mid]:
                transitive_to_drop.add((src, dst))
                break

    final_edges: list[dict] = []
    for key, edge in raw_edges.items():
        if key in transitive_to_drop:
            continue
        final_edges.append(edge)
    final_edges.sort(key=lambda item: (natural_key(item["from"]), natural_key(item["to"])))

    parallel_pairs = [tuple(sorted(pair, key=natural_key)) for pair in parallel_pairs]
    incomparable_pairs = [tuple(sorted(pair, key=natural_key)) for pair in incomparable_pairs]
    parallel_pairs = sorted(set(parallel_pairs))
    incomparable_pairs = sorted(set(incomparable_pairs))

    return {
        "edges": final_edges,
        "parallel": [list(pair) for pair in parallel_pairs],
        "incomparable": [list(pair) for pair in incomparable_pairs],
        "unattachedChunkIds": sorted(unattached_ids, key=natural_key),
        "attachedQuestsByChunk": {
            cid: sorted(quests, key=natural_key)
            for cid, quests in chunk_quests.items()
            if quests
        },
        "evidencePolicy": "questDag-only; chunks with no MissionRuntime storyRefs are unattached",
    }


def source_backed_story_call_contexts_from_scene_graph(
    scene_graph: dict | None,
    source: dict | None = None,
) -> list[dict]:
    contexts = (scene_graph or {}).get("levelscriptStoryCallContexts")
    if not isinstance(contexts, list):
        return []

    out: list[dict] = []
    for index, context in enumerate(contexts):
        if not isinstance(context, dict):
            continue
        scene_keys: list[str] = []
        for scene_key in context.get("sequence") or context.get("sceneKeys") or []:
            scene_key = str(scene_key or "").strip()
            if not scene_key or not is_sequence_scene_key(scene_key):
                continue
            if not scene_keys or scene_keys[-1] != scene_key:
                scene_keys.append(scene_key)
        if not scene_keys:
            continue
        row = {
            "kind": context.get("kind") or "levelscriptFileStoryCallOrder",
            "sourceFile": context.get("file") or context.get("sourceFile") or "",
            "levelId": context.get("levelId") or "",
            "sceneKeys": scene_keys,
            "recoveredBy": "scripts/story_builder/build.py",
        }
        if source:
            bundle_source = dict(source)
            bundle_source["field"] = f"{bundle_source.get('field', 'flow.sceneGraph.levelscriptStoryCallContexts')}[{index}]"
            row["bundleSource"] = bundle_source
        out.append(row)
    return out


def source_backed_hash_terminals_from_scene_graph(
    scene_graph: dict | None,
    source: dict | None = None,
) -> list[dict]:
    terminals = (scene_graph or {}).get("levelscriptHashTerminals")
    if not isinstance(terminals, list):
        return []

    out: list[dict] = []
    for index, terminal in enumerate(terminals):
        if not isinstance(terminal, dict):
            continue
        scene_key = str(terminal.get("sceneKey") or "").strip()
        hash_key = str(terminal.get("hash") or "").strip()
        if not scene_key or not is_sequence_scene_key(scene_key) or not is_levelscript_hash_key(hash_key):
            continue
        row = {
            "kind": terminal.get("kind") or "levelscriptHashTerminal",
            "sourceFile": terminal.get("file") or terminal.get("sourceFile") or "",
            "levelId": terminal.get("levelId") or "",
            "sceneKey": scene_key,
            "hash": hash_key,
            "direction": terminal.get("direction") or "",
            "sourceStep": terminal.get("sourceStep") or {},
            "hashStep": terminal.get("hashStep") or {},
            "recoveredBy": "scripts/story_builder/build.py",
        }
        if source:
            bundle_source = dict(source)
            bundle_source["field"] = f"{bundle_source.get('field', 'flow.sceneGraph.levelscriptHashTerminals')}[{index}]"
            row["bundleSource"] = bundle_source
        out.append(row)
    return out


def source_backed_story_call_contexts_from_scene_bindings(
    scene_bindings: dict | None,
    source: dict | None = None,
) -> list[dict]:
    if not isinstance(scene_bindings, dict):
        return []

    by_file: dict[tuple[str, str], list[tuple[int, int, str]]] = defaultdict(list)
    seen: set[tuple[str, str, int, int, str]] = set()
    for binding in scene_bindings.values():
        if not isinstance(binding, dict):
            continue
        for chain in binding.get("chains") or []:
            if not isinstance(chain, dict):
                continue
            source_file = str(chain.get("file") or "").strip()
            if not source_file:
                continue
            level_id = str(chain.get("levelId") or "").strip()
            for step in chain.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                step_source = ((step.get("_debug") or {}).get("source") or {})
                start = step_source.get("start")
                if not isinstance(start, int):
                    start = 10**9
                for payload_index, payload in enumerate(step.get("payloads") or []):
                    if not isinstance(payload, dict):
                        continue
                    scene_key = str(payload.get("sceneKey") or payload.get("nodeKey") or "").strip()
                    if not scene_key or not is_sequence_scene_key(scene_key):
                        continue
                    signature = (source_file, level_id, start, payload_index, scene_key)
                    if signature in seen:
                        continue
                    seen.add(signature)
                    by_file[(source_file, level_id)].append((start, payload_index, scene_key))

    out: list[dict] = []
    for index, ((source_file, level_id), items) in enumerate(
        sorted(by_file.items(), key=lambda item: natural_key("|".join(item[0])))
    ):
        scene_keys: list[str] = []
        for _, __, scene_key in sorted(items):
            if not scene_keys or scene_keys[-1] != scene_key:
                scene_keys.append(scene_key)
        if not scene_keys:
            continue
        row = {
            "kind": "levelscriptFileStoryCallOrder",
            "sourceFile": source_file,
            "levelId": level_id,
            "sceneKeys": scene_keys,
            "recoveredBy": "scripts/story_builder/build.py",
        }
        if source:
            bundle_source = dict(source)
            bundle_source["field"] = f"{bundle_source.get('field', 'extras.sceneBindings')}#{index}"
            row["bundleSource"] = bundle_source
        out.append(row)
    return out


def source_backed_hash_terminals_from_scene_bindings(
    scene_bindings: dict | None,
    source: dict | None = None,
) -> list[dict]:
    if not isinstance(scene_bindings, dict):
        return []

    out: list[dict] = []
    seen: set[tuple] = set()
    for binding in scene_bindings.values():
        if not isinstance(binding, dict):
            continue
        for chain in binding.get("chains") or []:
            if not isinstance(chain, dict):
                continue
            source_file = str(chain.get("file") or "").strip()
            level_id = str(chain.get("levelId") or "").strip()
            nodes: list[tuple[str, dict]] = []
            for step in chain.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                for payload in step.get("payloads") or []:
                    if not isinstance(payload, dict):
                        continue
                    node_key = str(payload.get("sceneKey") or payload.get("nodeKey") or "").strip()
                    if not node_key:
                        continue
                    step_source = ((step.get("_debug") or {}).get("source") or {})
                    compact_step = {
                        "nodeKey": node_key,
                        "payloadText": payload.get("text") or "",
                        "localId": step.get("localId"),
                        "nextId": step.get("nextId"),
                        "source": {
                            key: step_source.get(key)
                            for key in ("layout", "code", "kind", "uid", "start")
                            if step_source.get(key) not in (None, "", [], {})
                        },
                    }
                    if not compact_step["source"]:
                        compact_step.pop("source", None)
                    if not nodes or nodes[-1][0] != node_key:
                        nodes.append((node_key, compact_step))
            for pos, ((src, source_step), (dst, hash_step)) in enumerate(zip(nodes, nodes[1:])):
                if is_levelscript_hash_key(src) and is_sequence_scene_key(dst):
                    scene_key = dst
                    hash_key = src
                    direction = "hash->story"
                elif is_sequence_scene_key(src) and is_levelscript_hash_key(dst):
                    scene_key = src
                    hash_key = dst
                    direction = "story->hash"
                else:
                    continue
                signature = (source_file, level_id, scene_key, hash_key, direction, pos)
                if signature in seen:
                    continue
                seen.add(signature)
                row = {
                    "kind": "levelscriptHashTerminal",
                    "sourceFile": source_file,
                    "levelId": level_id,
                    "sceneKey": scene_key,
                    "hash": hash_key,
                    "direction": direction,
                    "sourceStep": source_step,
                    "hashStep": hash_step,
                    "recoveredBy": "scripts/story_builder/build.py",
                }
                if source:
                    bundle_source = dict(source)
                    bundle_source["field"] = f"{bundle_source.get('field', 'extras.sceneBindings')}#{len(out)}"
                    row["bundleSource"] = bundle_source
                out.append(row)
    return out


def source_backed_scene_edges_from_scene_graph(scene_graph: dict | None, source: dict | None = None) -> list[dict]:
    edges = (scene_graph or {}).get("edges")
    if not isinstance(edges, list):
        return []

    out: list[dict] = []
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            continue
        source_files = [
            str(file_ref)
            for file_ref in (edge.get("sourceFiles") or [])
            if str(file_ref)
        ]
        source_keys = [
            str(source_key)
            for source_key in (edge.get("sourceKeys") or [])
            if str(source_key)
        ]
        quest_ids = [
            str(quest_id)
            for quest_id in (edge.get("questIds") or [])
            if str(quest_id)
        ]
        # Quest-only edges are already represented by MissionRuntimeAsset
        # questEdges. Keep them here only when another recovered source backs
        # the edge.
        if not source_files and not source_keys:
            continue
        row = {
            "from": edge.get("from") or "",
            "to": edge.get("to") or "",
            "kind": edge.get("kind") or "",
            "recoveredBy": "scripts/story_builder/build.py",
        }
        if source:
            bundle_source = dict(source)
            bundle_source["field"] = f"{bundle_source.get('field', 'flow.sceneGraph.edges')}[{index}]"
            row["bundleSource"] = bundle_source
        if source_files:
            row["sourceFiles"] = source_files
        if source_keys:
            row["sourceKeys"] = source_keys
        if quest_ids:
            row["questIds"] = quest_ids
        if edge.get("levelIds"):
            row["levelIds"] = edge["levelIds"]
        if edge.get("optionIds"):
            row["optionIds"] = edge["optionIds"]
        if edge.get("positions"):
            row["positions"] = edge["positions"]
        out.append(row)
    return out


def load_source_backed_scene_edges(mission_id: str, generated_mission_dir: Path | None) -> list[dict]:
    """Load supplemental scene edges recovered by story_builder/build.py.

    The generated mission bundle can contain UI ordering/rank fields. This
    helper intentionally ignores those and keeps only edge records that carry
    source-backed LevelScriptData files, AnimeStudio source keys, or quest ids.
    """
    if not generated_mission_dir:
        return []
    path = generated_mission_dir / f"{mission_id}.json"
    if not path.exists():
        return []
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError):
        return []
    scene_graph = ((payload.get("flow") or {}).get("sceneGraph") or {})
    return source_backed_scene_edges_from_scene_graph(
        scene_graph,
        source=source_ref(path, "flow.sceneGraph.edges"),
    )


def load_source_backed_story_call_contexts(mission_id: str, generated_mission_dir: Path | None) -> list[dict]:
    """Load file-local LevelScript story-call context from generated mission bundles."""
    if not generated_mission_dir:
        return []
    path = generated_mission_dir / f"{mission_id}.json"
    if not path.exists():
        return []
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError):
        return []
    scene_graph = ((payload.get("flow") or {}).get("sceneGraph") or {})
    contexts = source_backed_story_call_contexts_from_scene_graph(
        scene_graph,
        source=source_ref(path, "flow.sceneGraph.levelscriptStoryCallContexts"),
    )
    if contexts:
        return contexts
    return source_backed_story_call_contexts_from_scene_bindings(
        ((payload.get("extras") or {}).get("sceneBindings") or {}),
        source=source_ref(path, "extras.sceneBindings"),
    )


def load_source_backed_hash_terminals(mission_id: str, generated_mission_dir: Path | None) -> list[dict]:
    """Load source-backed story/hash terminal diagnostics from generated mission bundles."""
    if not generated_mission_dir:
        return []
    path = generated_mission_dir / f"{mission_id}.json"
    if not path.exists():
        return []
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError):
        return []
    scene_graph = ((payload.get("flow") or {}).get("sceneGraph") or {})
    terminals = source_backed_hash_terminals_from_scene_graph(
        scene_graph,
        source=source_ref(path, "flow.sceneGraph.levelscriptHashTerminals"),
    )
    if terminals:
        return terminals
    return source_backed_hash_terminals_from_scene_bindings(
        ((payload.get("extras") or {}).get("sceneBindings") or {}),
        source=source_ref(path, "extras.sceneBindings"),
    )


def extract_quest(raw_quest: dict, source_path: Path, quest_field: str) -> dict:
    quest_id = raw_quest.get("questId") or ""
    quest = {
        "questId": quest_id,
        "questType": raw_quest.get("questType"),
        "flowIndex": raw_quest.get("flowIndex", 0),
        "prevQuestIds": list(raw_quest.get("prevQuestIdList") or []),
        "source": source_ref(source_path, quest_field),
        "flowIndexSource": source_ref(source_path, f"{quest_field}.flowIndex"),
        "prevSource": source_ref(source_path, f"{quest_field}.prevQuestIdList"),
    }
    for field_name in ("objectiveConditionNum", "showMode", "forceShowHudAnim", "ignoreNewQuestAnim", "ignoreQuestCompleteAnim", "blockQuestSkipToast", "needHudUpdateTag"):
        if raw_quest.get(field_name) not in (None, "", [], {}):
            quest[field_name] = raw_quest.get(field_name)
    if raw_quest.get("rewardId"):
        quest["rewardId"] = raw_quest["rewardId"]
        quest["rewardSource"] = source_ref(source_path, f"{quest_field}.rewardId")
    if raw_quest.get("needItemIds"):
        quest["needItemIds"] = raw_quest["needItemIds"]
        quest["needItemIdsSource"] = source_ref(source_path, f"{quest_field}.needItemIds")
    if raw_quest.get("overrideMissionDesc"):
        quest["overrideMissionDesc"] = True
    if raw_quest.get("descriptionOverride"):
        quest["descriptionOverride"] = raw_quest["descriptionOverride"]
        quest["descriptionOverrideSource"] = source_ref(source_path, f"{quest_field}.descriptionOverride")

    refs = extract_story_refs(raw_quest, source_path, quest_field)
    if refs:
        quest["storyRefs"] = refs
    objectives = extract_objectives(raw_quest, source_path, quest_field)
    if objectives:
        quest["objectives"] = objectives
    failed = extract_failed_condition(raw_quest, source_path, quest_field)
    if failed:
        quest["failedCondition"] = failed
    return quest


def attach_script_condition_quests(
    scene_placement: dict[str, dict],
    conditions: list[dict],
    story_keys_map: dict[tuple[str, str], set[str]],
    ownership: dict[tuple[str, str], list[str]] | None,
    mission_id: str,
) -> list[dict]:
    """Attach quest ids to scene_placement entries based on script conditions.

    For each (questId, mapId, scriptId) condition, look up the story keys that
    appear in that LevelScript via the per-mission story_keys_map. When
    ``ownership`` is supplied, only attach when exactly one mission owns the
    referenced LevelScript and that mission matches ``mission_id`` — the
    "scoped" attach policy that avoids letting shared LevelScripts pull a
    scene into multiple missions' quest hierarchies.

    Each attachment is recorded both on the placement row's ``questIds`` (so
    Phase 2 chunk-order recovery sees it) and on its ``questAttachSources``
    diagnostic for traceability. Returns the list of attached records for
    auditing.
    """
    attached: list[dict] = []
    if not conditions or not story_keys_map:
        return attached
    for condition in conditions:
        quest_id = str(condition.get("questId") or "").strip()
        map_id = str(condition.get("mapId") or "").strip()
        script_id = str(condition.get("scriptId") or "").strip()
        if not (quest_id and map_id and script_id):
            continue
        if ownership is not None:
            owners = ownership.get((map_id, script_id)) or []
            if len(owners) != 1 or owners[0] != mission_id:
                continue
        story_keys = story_keys_map.get((map_id, script_id)) or set()
        if not story_keys:
            continue
        for scene_key in story_keys:
            row = scene_placement.get(scene_key)
            if row is None:
                continue
            quest_ids = row.setdefault("questIds", [])
            already = quest_id in quest_ids
            if not already:
                quest_ids.append(quest_id)
            sources = row.setdefault("questAttachSources", [])
            source_record = {
                "questId": quest_id,
                "source": "scriptCondition",
                "mapId": map_id,
                "scriptId": script_id,
                "key": condition.get("key") or "",
            }
            if source_record not in sources:
                sources.append(source_record)
            attached.append({
                "sceneKey": scene_key,
                "questId": quest_id,
                "mapId": map_id,
                "scriptId": script_id,
                "alreadyAttached": already,
            })
            if "scriptConditionQuestAttach" not in (row.get("evidenceKinds") or []):
                row.setdefault("evidenceKinds", []).append("scriptConditionQuestAttach")
    return attached


def recover_mission(
    path: Path,
    timeline_index: dict[str, list[dict]],
    generated_mission_dir: Path | None,
    source_backed_scene_edges: list[dict] | None = None,
    source_backed_story_call_contexts: list[dict] | None = None,
    source_backed_hash_terminals: list[dict] | None = None,
    script_condition_ownership: dict[tuple[str, str], list[str]] | None = None,
) -> dict:
    raw = load_json(path)
    mission_id = raw.get("missionId") or path.stem
    metadata = {
        "missionId": mission_id,
        "source": source_ref(path, "$"),
    }
    for field_name in ("missionName", "missionDescription", "rewardId", "missionType", "missionImportance", "sortId", "charId", "levelId", "scope", "skipMissionAcceptAnim", "skipMissionCompleteAnim", "isWrapperMission", "useRewardWrapper", "useLevelIdWrapper"):
        value = raw.get(field_name)
        if not is_empty_value(value):
            metadata[field_name] = value
            metadata[f"{field_name}Source"] = source_ref(path, field_name)
    for field_name in ("onMissionAcceptId", "onMissionCompletedId", "onMissionFailedId"):
        value = raw.get(field_name)
        if value not in (None, -1):
            metadata[field_name] = value
            metadata[f"{field_name}Source"] = source_ref(path, field_name)
    if isinstance(raw.get("externalInfo"), dict):
        metadata["externalInfo"] = {
            "type": short_type(raw["externalInfo"].get("$type", "")),
            "source": source_ref(path, "externalInfo"),
            "fields": flatten_primitives(raw["externalInfo"], "externalInfo"),
        }

    quests: list[dict] = []
    quest_dic = raw.get("questDic") or {}
    for key, raw_quest in sorted(quest_dic.items(), key=lambda item: natural_key(item[0])):
        if not isinstance(raw_quest, dict):
            continue
        quests.append(extract_quest(raw_quest, path, f"questDic.{key}"))
    quests.sort(key=lambda item: (
        item.get("flowIndex") if isinstance(item.get("flowIndex"), (int, float)) else 10**9,
        quest_tail_number(item.get("questId") or ""),
        item.get("questId") or "",
    ))

    client_actions = extract_client_actions(raw, path)
    actions_by_quest: dict[str, list[dict]] = defaultdict(list)
    for action in client_actions:
        if action.get("questId"):
            actions_by_quest[action["questId"]].append(action)
    for quest in quests:
        if actions_by_quest.get(quest["questId"]):
            quest["clientActions"] = actions_by_quest[quest["questId"]]

    all_refs = [
        ref
        for quest in quests
        for ref in (quest.get("storyRefs") or [])
    ]
    for action in client_actions:
        all_refs.extend(action.get("storyRefs") or [])
    timeline_evidence, timeline_unresolved = attach_timeline_evidence(all_refs, timeline_index)
    quest_edges, edge_unresolved = build_quest_edges(quests, path)
    quests_by_id = {quest["questId"]: quest for quest in quests}

    unresolved = edge_unresolved + timeline_unresolved
    referenced_scenes = sorted({ref.get("sceneKey") or "" for ref in all_refs if ref.get("sceneKey")})
    entry_quests = [
        quest["questId"]
        for quest in quests
        if not quest.get("prevQuestIds")
    ]
    scene_edges = (
        source_backed_scene_edges
        if source_backed_scene_edges is not None
        else load_source_backed_scene_edges(mission_id, generated_mission_dir)
    )
    scene_sequences = build_source_backed_scene_sequences(scene_edges)
    story_call_contexts = (
        source_backed_story_call_contexts
        if source_backed_story_call_contexts is not None
        else load_source_backed_story_call_contexts(mission_id, generated_mission_dir)
    )
    hash_terminals = (
        source_backed_hash_terminals
        if source_backed_hash_terminals is not None
        else load_source_backed_hash_terminals(mission_id, generated_mission_dir)
    )
    scene_placement = build_scene_placement_index(
        quests,
        client_actions,
        timeline_evidence,
        scene_edges,
        scene_sequences,
        story_call_contexts,
        hash_terminals,
    )
    script_conditions = decode_mission_script_conditions(raw)
    story_keys_by_script = build_levelscript_story_keys_map(scene_edges)
    script_condition_attachments = attach_script_condition_quests(
        scene_placement,
        script_conditions,
        story_keys_by_script,
        script_condition_ownership,
        mission_id,
    )
    chunks, chunk_by_scene_key = build_scene_chunks(
        scene_placement,
        scene_edges,
        scene_sequences,
        timeline_evidence,
    )
    for scene_key, chunk_id in chunk_by_scene_key.items():
        placement_row = scene_placement.get(scene_key)
        if placement_row is not None:
            placement_row["chunkId"] = chunk_id
    chunk_order = build_chunk_order(chunks, scene_placement, quest_edges)
    quest_tree = build_quest_tree(quests, quest_edges)
    attach_chunks_to_quest_tree(quest_tree, chunks, scene_placement, chunk_order)
    payload = {
        "mission": mission_id,
        "metadata": metadata,
        "propertyModel": extract_properties(raw, path),
        "questLayers": build_quest_layers(quests),
        "entryQuestIds": entry_quests,
        "quests": quests,
        "questEdges": quest_edges,
        "questTree": quest_tree,
        "branchPoints": build_branch_points(quest_edges, quests_by_id),
        "sourceBackedSceneEdges": scene_edges,
        "sourceBackedSceneSequences": scene_sequences,
        "sourceBackedStoryCallContexts": story_call_contexts,
        "sourceBackedHashTerminals": hash_terminals,
        "referencedScenes": referenced_scenes,
        "sceneTimelineEvidence": timeline_evidence,
        "scenePlacement": scene_placement,
        "chunks": chunks,
        "chunkOrder": chunk_order,
        "scriptConditionAttachments": script_condition_attachments,
        "unresolved": unresolved,
    }
    return payload


def mission_files(mra_dir: Path, selected: set[str]) -> list[Path]:
    files = [
        path
        for path in mra_dir.glob("*.json")
        if not path.name.endswith("_meta.json")
    ]
    if selected:
        files = [path for path in files if path.stem in selected]
    return sorted(files, key=lambda path: natural_key(path.stem))


EXPECTED_HASH_TERMINAL_PATTERN = {
    "direction": "story->hash",
    "layout": "plain",
    "code": "0x0e34",
    "kind": "0x00",
    "nextId": -1,
}


def _terminal_hash_step(terminal: dict) -> dict:
    hash_step = terminal.get("hashStep")
    return hash_step if isinstance(hash_step, dict) else {}


def _terminal_hash_source(terminal: dict) -> dict:
    source = _terminal_hash_step(terminal).get("source")
    return source if isinstance(source, dict) else {}


def _terminal_pattern(terminal: dict) -> dict:
    hash_step = _terminal_hash_step(terminal)
    source = _terminal_hash_source(terminal)
    return {
        "direction": terminal.get("direction") or "",
        "layout": source.get("layout") or "",
        "code": source.get("code") or "",
        "kind": source.get("kind") or "",
        "nextId": hash_step.get("nextId"),
    }


def _pattern_counter_key(pattern: dict) -> tuple:
    return (
        pattern.get("direction") or "",
        pattern.get("layout") or "",
        pattern.get("code") or "",
        pattern.get("kind") or "",
        pattern.get("nextId"),
    )


def _terminal_matches_expected_pattern(pattern: dict) -> bool:
    return all(
        pattern.get(key) == expected
        for key, expected in EXPECTED_HASH_TERMINAL_PATTERN.items()
    )


def _hash_terminal_catalog_sample(mission_id: str, terminal: dict) -> dict:
    pattern = _terminal_pattern(terminal)
    sample = {
        "mission": mission_id,
        "sceneKey": terminal.get("sceneKey") or "",
        "hash": terminal.get("hash") or "",
        "sourceFile": terminal.get("sourceFile") or "",
        **pattern,
    }
    return {
        key: value
        for key, value in sample.items()
        if value not in (None, "", [], {})
    }


def build_hash_terminal_catalog(recovered: list[dict]) -> dict:
    pattern_counter: Counter = Counter()
    hash_counter: Counter = Counter()
    missions_by_hash: dict[str, set[str]] = defaultdict(set)
    scenes_by_hash: dict[str, set[str]] = defaultdict(set)
    files_by_hash: dict[str, set[str]] = defaultdict(set)
    samples_by_hash: dict[str, list[dict]] = defaultdict(list)
    sample_signatures_by_hash: dict[str, set[str]] = defaultdict(set)
    exceptions: list[dict] = []
    exception_count = 0

    for mission in recovered:
        mission_id = str(mission.get("mission") or "")
        for terminal in mission.get("sourceBackedHashTerminals") or []:
            if not isinstance(terminal, dict):
                continue
            hash_key = str(terminal.get("hash") or "").strip()
            if not hash_key:
                continue
            pattern = _terminal_pattern(terminal)
            pattern_counter[_pattern_counter_key(pattern)] += 1
            hash_counter[hash_key] += 1
            if mission_id:
                missions_by_hash[hash_key].add(mission_id)
            scene_key = str(terminal.get("sceneKey") or "").strip()
            if scene_key:
                scenes_by_hash[hash_key].add(scene_key)
            source_file = str(terminal.get("sourceFile") or "").strip()
            if source_file:
                files_by_hash[hash_key].add(source_file)

            sample = _hash_terminal_catalog_sample(mission_id, terminal)
            sample_signature = json.dumps(sample, ensure_ascii=False, sort_keys=True)
            if (
                sample_signature not in sample_signatures_by_hash[hash_key]
                and len(samples_by_hash[hash_key]) < 5
            ):
                sample_signatures_by_hash[hash_key].add(sample_signature)
                samples_by_hash[hash_key].append(sample)

            if not _terminal_matches_expected_pattern(pattern):
                exception_count += 1
                if len(exceptions) < 50:
                    exceptions.append(sample)

    pattern_counts = []
    for key, count in pattern_counter.most_common():
        direction, layout, code, kind, next_id = key
        pattern_counts.append({
            "count": count,
            "direction": direction,
            "layout": layout,
            "code": code,
            "kind": kind,
            "nextId": next_id,
        })

    top_hashes = []
    for hash_key, count in hash_counter.most_common(20):
        top_hashes.append({
            "hash": hash_key,
            "count": count,
            "missionCount": len(missions_by_hash.get(hash_key) or []),
            "sceneCount": len(scenes_by_hash.get(hash_key) or []),
            "sourceFileCount": len(files_by_hash.get(hash_key) or []),
            "missions": sorted(missions_by_hash.get(hash_key) or [], key=natural_key)[:10],
            "scenes": sorted(scenes_by_hash.get(hash_key) or [], key=natural_key)[:12],
            "sourceFiles": sorted(files_by_hash.get(hash_key) or [], key=natural_key)[:5],
            "samples": samples_by_hash.get(hash_key) or [],
        })

    return {
        "expectedTerminalPattern": EXPECTED_HASH_TERMINAL_PATTERN,
        "uniqueHashes": len(hash_counter),
        "patternCounts": pattern_counts,
        "topHashes": top_hashes,
        "exceptionCount": exception_count,
        "exceptions": exceptions,
        "allMatchExpectedTerminalPattern": exception_count == 0,
    }


def summarize(
    recovered: list[dict],
    timeline_meta: dict,
    generated_by: str = "scripts/story_builder/mission_recovery.py",
) -> dict:
    unresolved_counter: Counter = Counter()
    action_counter: Counter = Counter()
    condition_counter: Counter = Counter()
    tracking_counter: Counter = Counter()
    missions_with_branches = 0
    missions_with_timeline = 0
    missions_with_scene_edges = 0
    missions_with_scene_sequences = 0
    missions_with_story_call_contexts = 0
    missions_with_hash_terminals = 0
    missions_with_quest_loops = 0
    quest_loop_count = 0
    scene_edge_counter: Counter = Counter()
    scene_sequence_total = 0
    story_call_context_total = 0
    hash_terminal_total = 0
    hash_terminal_catalog = build_hash_terminal_catalog(recovered)
    scene_placement_counter: Counter = Counter()
    scene_placement_total = 0
    chunk_total = 0
    chunk_singleton_total = 0
    chunk_isolated_total = 0
    chunk_size_max = 0
    chunk_edge_kind_counter: Counter = Counter()
    chunk_strength_counter: Counter = Counter()
    missions_with_chunks = 0
    missions_with_multichunk = 0
    chunk_order_edge_total = 0
    chunk_order_parallel_total = 0
    chunk_order_incomparable_total = 0
    missions_with_chunk_order = 0
    missions_fully_ordered_attached = 0
    missions_partially_ordered_attached = 0
    for mission in recovered:
        if mission.get("branchPoints"):
            missions_with_branches += 1
        if mission.get("sceneTimelineEvidence"):
            missions_with_timeline += 1
        if mission.get("sourceBackedSceneEdges"):
            missions_with_scene_edges += 1
        if mission.get("sourceBackedSceneSequences"):
            missions_with_scene_sequences += 1
            scene_sequence_total += len(mission.get("sourceBackedSceneSequences") or [])
        if mission.get("sourceBackedStoryCallContexts"):
            missions_with_story_call_contexts += 1
            story_call_context_total += len(mission.get("sourceBackedStoryCallContexts") or [])
        if mission.get("sourceBackedHashTerminals"):
            missions_with_hash_terminals += 1
            hash_terminal_total += len(mission.get("sourceBackedHashTerminals") or [])
        loops = ((mission.get("questTree") or {}).get("loops") or [])
        if loops:
            missions_with_quest_loops += 1
            quest_loop_count += len(loops)
        for edge in mission.get("sourceBackedSceneEdges") or []:
            scene_edge_counter[edge.get("kind") or "edge"] += 1
        scene_placement_total += len(mission.get("scenePlacement") or {})
        for placement in (mission.get("scenePlacement") or {}).values():
            for kind in placement.get("evidenceKinds") or []:
                scene_placement_counter[kind] += 1
        mission_chunks = mission.get("chunks") or []
        if mission_chunks:
            missions_with_chunks += 1
            chunk_total += len(mission_chunks)
            multichunk = [chunk for chunk in mission_chunks if chunk.get("sceneCount", 0) >= 2]
            if len(multichunk) >= 2 or (len(multichunk) >= 1 and len(mission_chunks) > 1):
                missions_with_multichunk += 1
            for chunk in mission_chunks:
                size = int(chunk.get("sceneCount") or 0)
                if size > chunk_size_max:
                    chunk_size_max = size
                if size <= 1:
                    chunk_singleton_total += 1
                if chunk.get("isolated"):
                    chunk_isolated_total += 1
                chunk_strength_counter[str(chunk.get("strength") or "unanchored")] += 1
                for kind in chunk.get("edgeKinds") or []:
                    chunk_edge_kind_counter[kind] += 1
        chunk_order = mission.get("chunkOrder") or {}
        edges = chunk_order.get("edges") or []
        attached_chunks = chunk_order.get("attachedQuestsByChunk") or {}
        if edges:
            chunk_order_edge_total += len(edges)
            missions_with_chunk_order += 1
        chunk_order_parallel_total += len(chunk_order.get("parallel") or [])
        chunk_order_incomparable_total += len(chunk_order.get("incomparable") or [])
        if attached_chunks and not (chunk_order.get("incomparable") or []) and not (chunk_order.get("parallel") or []):
            missions_fully_ordered_attached += 1
        elif edges:
            missions_partially_ordered_attached += 1
        for item in mission.get("unresolved") or []:
            unresolved_counter[item.get("kind") or "unknown"] += 1
        for quest in mission.get("quests") or []:
            for action in quest.get("clientActions") or []:
                action_counter[action.get("actionType") or "ClientAction"] += 1
            for objective in quest.get("objectives") or []:
                for typ in objective.get("conditionTypes") or []:
                    condition_counter[typ] += 1
                for tracking in objective.get("tracking") or []:
                    tracking_counter[tracking.get("type") or "TrackingInfo"] += 1
    return {
        "generatedBy": generated_by,
        "generatedAt": int(time.time()),
        "missionCount": len(recovered),
        "questCount": sum(len(mission.get("quests") or []) for mission in recovered),
        "missionWithBranchPoints": missions_with_branches,
        "missionsWithQuestTreeLoops": missions_with_quest_loops,
        "questTreeLoops": quest_loop_count,
        "missionsWithDialogTimelineEvidence": missions_with_timeline,
        "missionsWithSourceBackedSceneEdges": missions_with_scene_edges,
        "missionsWithSourceBackedSceneSequences": missions_with_scene_sequences,
        "sourceBackedSceneSequences": scene_sequence_total,
        "missionsWithSourceBackedStoryCallContexts": missions_with_story_call_contexts,
        "sourceBackedStoryCallContexts": story_call_context_total,
        "missionsWithSourceBackedHashTerminals": missions_with_hash_terminals,
        "sourceBackedHashTerminals": hash_terminal_total,
        "sourceBackedHashTerminalUniqueHashes": hash_terminal_catalog.get("uniqueHashes", 0),
        "sourceBackedHashTerminalExceptionCount": hash_terminal_catalog.get("exceptionCount", 0),
        "hashTerminalCatalog": hash_terminal_catalog,
        "scenePlacementEntries": scene_placement_total,
        "missionsWithChunks": missions_with_chunks,
        "missionsWithMultiChunkLayout": missions_with_multichunk,
        "chunkCount": chunk_total,
        "chunkSingletonCount": chunk_singleton_total,
        "chunkIsolatedCount": chunk_isolated_total,
        "chunkMaxSceneCount": chunk_size_max,
        "chunkEdgeKindCounts": dict(chunk_edge_kind_counter.most_common()),
        "chunkStrengthCounts": dict(chunk_strength_counter.most_common()),
        "missionsWithChunkOrder": missions_with_chunk_order,
        "missionsFullyOrderedByQuestAttach": missions_fully_ordered_attached,
        "missionsPartiallyOrderedByQuestAttach": missions_partially_ordered_attached,
        "chunkOrderEdges": chunk_order_edge_total,
        "chunkOrderParallelPairs": chunk_order_parallel_total,
        "chunkOrderIncomparablePairs": chunk_order_incomparable_total,
        "timelineEvidence": timeline_meta,
        "unresolvedByKind": dict(unresolved_counter.most_common()),
        "sourceBackedSceneEdgesByKind": dict(scene_edge_counter.most_common()),
        "scenePlacementEvidenceByKind": dict(scene_placement_counter.most_common()),
        "clientActionsByType": dict(action_counter.most_common()),
        "conditionTypes": dict(condition_counter.most_common()),
        "trackingTypes": dict(tracking_counter.most_common()),
    }


def render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Mission Timeline Recovery",
        "",
        "Evidence policy: source-backed records only. Filename order, numeric suffix fallback, generated UI rank, and raw table row order are not used as chronology.",
        "",
        "## Summary",
        "",
        f"- missions: `{summary['missionCount']}`",
        f"- quests: `{summary['questCount']}`",
        f"- missions with branch points: `{summary['missionWithBranchPoints']}`",
        f"- missions with quest-tree loops: `{summary.get('missionsWithQuestTreeLoops', 0)}`",
        f"- missions with dialog timeline evidence: `{summary['missionsWithDialogTimelineEvidence']}`",
        f"- missions with source-backed scene edges: `{summary['missionsWithSourceBackedSceneEdges']}`",
        f"- missions with source-backed scene sequences: `{summary.get('missionsWithSourceBackedSceneSequences', 0)}`",
        f"- source-backed scene sequences: `{summary.get('sourceBackedSceneSequences', 0)}`",
        f"- missions with source-backed story-call context: `{summary.get('missionsWithSourceBackedStoryCallContexts', 0)}`",
        f"- source-backed story-call contexts: `{summary.get('sourceBackedStoryCallContexts', 0)}`",
        f"- missions with source-backed hash terminals: `{summary.get('missionsWithSourceBackedHashTerminals', 0)}`",
        f"- source-backed hash terminals: `{summary.get('sourceBackedHashTerminals', 0)}`",
        f"- unique source-backed terminal hashes: `{summary.get('sourceBackedHashTerminalUniqueHashes', 0)}`",
        f"- hash-terminal pattern exceptions: `{summary.get('sourceBackedHashTerminalExceptionCount', 0)}`",
        f"- scene placement entries: `{summary.get('scenePlacementEntries', 0)}`",
        f"- missions with chunks: `{summary.get('missionsWithChunks', 0)}`",
        f"- missions with multi-chunk layout: `{summary.get('missionsWithMultiChunkLayout', 0)}`",
        f"- chunks total: `{summary.get('chunkCount', 0)}` "
        f"(singletons `{summary.get('chunkSingletonCount', 0)}`, "
        f"isolated `{summary.get('chunkIsolatedCount', 0)}`, "
        f"max scenes/chunk `{summary.get('chunkMaxSceneCount', 0)}`)",
        f"- chunk-order edges (questDag): `{summary.get('chunkOrderEdges', 0)}` "
        f"across `{summary.get('missionsWithChunkOrder', 0)}` missions; "
        f"parallel pairs `{summary.get('chunkOrderParallelPairs', 0)}`, "
        f"incomparable pairs `{summary.get('chunkOrderIncomparablePairs', 0)}`",
        f"- timeline evidence file: `{summary['timelineEvidence'].get('path', '')}`",
        "",
        "## Unresolved Evidence",
        "",
    ]
    if summary.get("unresolvedByKind"):
        for key, count in summary["unresolvedByKind"].items():
            lines.append(f"- `{key}`: `{count}`")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Source-Backed Scene Edges",
        "",
    ])
    if summary.get("sourceBackedSceneEdgesByKind"):
        for key, count in summary["sourceBackedSceneEdgesByKind"].items():
            lines.append(f"- `{key}`: `{count}`")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Scene Placement Signals",
        "",
    ])
    if summary.get("scenePlacementEvidenceByKind"):
        for key, count in summary["scenePlacementEvidenceByKind"].items():
            lines.append(f"- `{key}`: `{count}`")
    else:
        lines.append("- none")
    catalog = summary.get("hashTerminalCatalog") or {}
    lines.extend([
        "",
        "## Hash Terminal Catalog",
        "",
    ])
    if catalog:
        expected = catalog.get("expectedTerminalPattern") or {}
        lines.append(f"- unique hashes: `{catalog.get('uniqueHashes', 0)}`")
        lines.append(
            f"- all match expected terminal pattern: "
            f"`{'yes' if catalog.get('allMatchExpectedTerminalPattern') else 'no'}`"
        )
        if expected:
            lines.append(
                "- expected terminal pattern: "
                f"`{expected.get('direction', '')}` "
                f"`{expected.get('layout', '')}` "
                f"`{expected.get('code', '')}` "
                f"`{expected.get('kind', '')}` "
                f"`nextId={expected.get('nextId')}`"
            )
        pattern_counts = catalog.get("patternCounts") or []
        if pattern_counts:
            lines.extend(["", "### Terminal Patterns", ""])
            for pattern in pattern_counts[:12]:
                lines.append(
                    "- "
                    f"`{pattern.get('direction', '')}` "
                    f"`{pattern.get('layout', '')}` "
                    f"`{pattern.get('code', '')}` "
                    f"`{pattern.get('kind', '')}` "
                    f"`nextId={pattern.get('nextId')}`: "
                    f"`{pattern.get('count', 0)}`"
                )
        top_hashes = catalog.get("topHashes") or []
        if top_hashes:
            lines.extend(["", "### Top Hashes", ""])
            for item in top_hashes[:10]:
                scene_samples = (item.get("scenes") or [])[:6]
                scenes = ", ".join(f"`{scene}`" for scene in scene_samples)
                remaining_scenes = int(item.get("sceneCount") or 0) - len(scene_samples)
                if remaining_scenes > 0:
                    scenes += f", +{remaining_scenes}"
                mission_samples = (item.get("missions") or [])[:6]
                missions = ", ".join(f"`{mission}`" for mission in mission_samples)
                remaining_missions = int(item.get("missionCount") or 0) - len(mission_samples)
                if remaining_missions > 0:
                    missions += f", +{remaining_missions}"
                lines.append(
                    "- "
                    f"`{item.get('hash', '')}`: "
                    f"count=`{item.get('count', 0)}`, "
                    f"missions=`{item.get('missionCount', 0)}`, "
                    f"scenes=`{item.get('sceneCount', 0)}`"
                    + (f"; mission samples: {missions}" if missions else "")
                    + (f"; scene samples: {scenes}" if scenes else "")
                )
        exceptions = catalog.get("exceptions") or []
        lines.extend(["", "### Pattern Exceptions", ""])
        if exceptions:
            for item in exceptions[:20]:
                lines.append(
                    "- "
                    f"`{item.get('mission', '')}` "
                    f"`{item.get('sceneKey', '')}` -> "
                    f"`{item.get('hash', '')}` "
                    f"`{item.get('direction', '')}` "
                    f"`{item.get('layout', '')}` "
                    f"`{item.get('code', '')}` "
                    f"`{item.get('kind', '')}` "
                    f"`nextId={item.get('nextId')}`"
                )
        else:
            lines.append("- none")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Client Actions",
        "",
    ])
    if summary.get("clientActionsByType"):
        for key, count in summary["clientActionsByType"].items():
            lines.append(f"- `{key}`: `{count}`")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Mission Index",
        "",
        "| Mission | Quests | Branches | Timeline Scenes | Scene Edges | Scene Seq | Story Calls | Hash Terms | Scene Signals | Unresolved | Level |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    for mission in payload.get("missions") or []:
        metadata = mission.get("metadata") or {}
        lines.append(
            "| "
            f"`{mission.get('mission')}` | "
            f"{len(mission.get('quests') or [])} | "
            f"{len(mission.get('branchPoints') or [])} | "
            f"{len(mission.get('sceneTimelineEvidence') or {})} | "
            f"{len(mission.get('sourceBackedSceneEdges') or [])} | "
            f"{len(mission.get('sourceBackedSceneSequences') or [])} | "
            f"{len(mission.get('sourceBackedStoryCallContexts') or [])} | "
            f"{len(mission.get('sourceBackedHashTerminals') or [])} | "
            f"{len(mission.get('scenePlacement') or {})} | "
            f"{len(mission.get('unresolved') or [])} | "
            f"`{metadata.get('levelId', '')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--mra-dir", type=Path, help="MissionRuntimeAsset directory. Defaults under --export-root.")
    parser.add_argument("--timeline-orders", type=Path, help="Recovered AnimeStudio timeline_line_orders.json.")
    parser.add_argument(
        "--generated-mission-dir",
        type=Path,
        default=DEFAULT_GENERATED_MISSION_DIR,
        help="Generated mission bundle directory used only for source-backed scene edges.",
    )
    parser.add_argument(
        "--no-generated-mission-edges",
        action="store_true",
        help="Do not import source-backed scene edges from generated mission bundles.",
    )
    parser.add_argument("--mission", action="append", default=[], help="Recover only this mission id. May be repeated.")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    export_root = args.export_root if args.export_root.is_absolute() else ROOT / args.export_root
    mra_dir = args.mra_dir or export_root / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset"
    mra_dir = mra_dir if mra_dir.is_absolute() else ROOT / mra_dir
    timeline_orders = args.timeline_orders or export_root / "recovered" / "AnimeStudio-cli" / "timeline_line_orders.json"
    timeline_orders = timeline_orders if timeline_orders.is_absolute() else ROOT / timeline_orders
    generated_mission_dir = None
    if not args.no_generated_mission_edges:
        generated_mission_dir = args.generated_mission_dir if args.generated_mission_dir.is_absolute() else ROOT / args.generated_mission_dir
    out_json = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_md = args.out_md if args.out_md.is_absolute() else ROOT / args.out_md

    if not mra_dir.is_dir():
        raise SystemExit(f"MissionRuntimeAsset directory not found: {mra_dir}")
    timeline_index, timeline_meta = load_timeline_index(timeline_orders)
    selected = set(args.mission or [])
    files = mission_files(mra_dir, selected)
    if selected and len(files) != len(selected):
        found = {path.stem for path in files}
        missing = sorted(selected - found)
        raise SystemExit(f"MissionRuntimeAsset missing for: {', '.join(missing)}")

    all_files = mission_files(mra_dir, set())
    script_condition_ownership = build_script_condition_ownership(all_files)
    recovered = [
        recover_mission(
            path,
            timeline_index,
            generated_mission_dir,
            script_condition_ownership=script_condition_ownership,
        )
        for path in files
    ]
    payload = {
        "evidencePolicy": EVIDENCE_POLICY,
        "summary": summarize(recovered, timeline_meta),
        "missions": recovered,
    }
    write_json(out_json, payload)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(payload), encoding="utf-8")
    print(f"wrote {rel_path(out_json)}")
    print(f"wrote {rel_path(out_md)}")
    print(f"missions={payload['summary']['missionCount']} quests={payload['summary']['questCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
