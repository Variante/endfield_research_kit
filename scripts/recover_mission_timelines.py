#!/usr/bin/env python3
"""Recover evidence-only mission timelines.

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


ROOT = Path(__file__).resolve().parent.parent
EXPORT_ROOT = ROOT / "export_full"
DEFAULT_MRA_DIR = EXPORT_ROOT / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset"
DEFAULT_TIMELINE_ORDERS = EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "timeline_line_orders.json"
DEFAULT_GENERATED_MISSION_DIR = ROOT / "webui" / "data" / "lang" / "CN" / "mission"
DEFAULT_OUT_JSON = ROOT / "reports" / "mission_timeline_recovery_CN.json"
DEFAULT_OUT_MD = ROOT / "reports" / "mission_timeline_recovery_CN.md"

EVIDENCE_POLICY = {
    "uses": [
        "MissionRuntimeAsset explicit fields",
        "MissionRuntimeAsset client action maps",
        "recovered AnimeStudio timeline clip records",
        "source-backed LevelScriptData and AnimeStudio edges recovered by build_story.py",
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
            "recoveredBy": "scripts/webui/build_story.py",
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
    """Load supplemental scene edges recovered by build_story.py.

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


def recover_mission(
    path: Path,
    timeline_index: dict[str, list[dict]],
    generated_mission_dir: Path | None,
    source_backed_scene_edges: list[dict] | None = None,
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
    payload = {
        "mission": mission_id,
        "metadata": metadata,
        "propertyModel": extract_properties(raw, path),
        "questLayers": build_quest_layers(quests),
        "entryQuestIds": entry_quests,
        "quests": quests,
        "questEdges": quest_edges,
        "questTree": build_quest_tree(quests, quest_edges),
        "branchPoints": build_branch_points(quest_edges, quests_by_id),
        "sourceBackedSceneEdges": (
            source_backed_scene_edges
            if source_backed_scene_edges is not None
            else load_source_backed_scene_edges(mission_id, generated_mission_dir)
        ),
        "referencedScenes": referenced_scenes,
        "sceneTimelineEvidence": timeline_evidence,
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


def summarize(
    recovered: list[dict],
    timeline_meta: dict,
    generated_by: str = "scripts/recover_mission_timelines.py",
) -> dict:
    unresolved_counter: Counter = Counter()
    action_counter: Counter = Counter()
    condition_counter: Counter = Counter()
    tracking_counter: Counter = Counter()
    missions_with_branches = 0
    missions_with_timeline = 0
    missions_with_scene_edges = 0
    missions_with_quest_loops = 0
    quest_loop_count = 0
    scene_edge_counter: Counter = Counter()
    for mission in recovered:
        if mission.get("branchPoints"):
            missions_with_branches += 1
        if mission.get("sceneTimelineEvidence"):
            missions_with_timeline += 1
        if mission.get("sourceBackedSceneEdges"):
            missions_with_scene_edges += 1
        loops = ((mission.get("questTree") or {}).get("loops") or [])
        if loops:
            missions_with_quest_loops += 1
            quest_loop_count += len(loops)
        for edge in mission.get("sourceBackedSceneEdges") or []:
            scene_edge_counter[edge.get("kind") or "edge"] += 1
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
        "timelineEvidence": timeline_meta,
        "unresolvedByKind": dict(unresolved_counter.most_common()),
        "sourceBackedSceneEdgesByKind": dict(scene_edge_counter.most_common()),
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
        "| Mission | Quests | Branches | Timeline Scenes | Scene Edges | Unresolved | Level |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
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

    recovered = [recover_mission(path, timeline_index, generated_mission_dir) for path in files]
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
