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
import math
import re
import struct
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if __package__ == "story_builder":
    from common import read_bytes_cached
elif __package__ == "scripts.story_builder":
    from ..common import read_bytes_cached
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("import this module as scripts.story_builder.mission_recovery")

from .mission_assets import select_complete_mission_runtime_root
from .story_keys import canonical_cutscene_key, line_stem, timeline_stem_to_dialog_key

EXPORT_ROOT = ROOT / "export_full"
DEFAULT_MRA_DIR = select_complete_mission_runtime_root(
    EXPORT_ROOT / "structured" / "StreamingAssets" / "Data" / "Json"
    / "MissionRuntimeAsset",
    EXPORT_ROOT / "structured" / "Persistent" / "Data" / "Json"
    / "MissionRuntimeAsset",
)
DEFAULT_TIMELINE_ORDERS = EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "timeline_line_orders.json"
DEFAULT_GENERATED_MISSION_DIR = ROOT / "webui" / "data" / "lang" / "CN" / "mission"
DEFAULT_OUT_JSON = ROOT / "reports" / "story" / "build" / "mission_timeline_recovery_CN.json"
DEFAULT_OUT_MD = ROOT / "reports" / "story" / "build" / "mission_timeline_recovery_CN.md"

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
    "levelscriptDialogExit",
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

LEVELSCRIPT_SPATIAL_XZ_THRESHOLD = 25.0
LEVELSCRIPT_SPATIAL_Y_THRESHOLD = 12.0
LEVELSCRIPT_SPATIAL_MAX_ABS = 200000.0
LEVELSCRIPT_SPATIAL_MAX_FILE_BYTES = 2_000_000
LEVELSCRIPT_SPATIAL_MAX_VECTORS = 25000

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
    "trackScriptEntity",
    "entityLogicId",
    "scriptId",
    "entitySlotId",
    "guidingArea",
    "shapeType",
    "radius",
    "routePointCount",
    "snsDialogId",
)

_ROOT_RESOLVED = ROOT.resolve()
_REL_PATH_CACHE: dict[str, str] = {}
_LEVELSCRIPT_VECTOR_CACHE: dict[str, list[dict]] = {}


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
    # This generated evidence payload is currently around 90 MB when pretty
    # printed. Its paired Markdown report is the human-readable view; compact
    # JSON preserves the exact data while avoiding tens of megabytes of
    # indentation and materially reducing every Story rebuild's write cost.
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


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
            row["multipleDescriptionKeys"] = unique_preserve(multiple_description)
            row["multipleDescriptionSources"] = [
                source_ref(source_path, f"{obj_field}.multipleDescription[{item_index}].key")
                for item_index, item in enumerate(obj.get("multipleDescription") or [])
                if isinstance(item, dict) and item.get("key")
            ]
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
        "dialogKey": entry.get("dialogKey") or timeline_stem_to_dialog_key(entry.get("timeline") or ""),
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
                timeline_stem_to_dialog_key(compact.get("timeline") or ""),
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


def attach_timeline_evidence(
    refs: list[dict],
    timeline_index: dict[str, list[dict]],
    dialog_tree_loader=None,
) -> tuple[dict[str, list[dict]], dict[str, dict], list[dict]]:
    if dialog_tree_loader is None:
        # Import after story_builder.context has finished initializing.  That
        # module imports mission_recovery while defining the shared AnimeStudio
        # roots, so a module-level import here would observe a partial context.
        from .anime_assets import recover_dialog_tree_definition_evidence

        dialog_tree_loader = recover_dialog_tree_definition_evidence
    evidence: dict[str, list[dict]] = {}
    dialog_tree_evidence: dict[str, dict] = {}
    unresolved: list[dict] = []
    for ref in refs:
        scene_key = ref.get("sceneKey") or ""
        kind = ref.get("kind") or ""
        if not scene_key:
            continue
        entries = timeline_index.get(scene_key, [])
        if entries:
            evidence.setdefault(scene_key, entries)
        if kind == "dlg":
            dialog_tree = dialog_tree_loader(scene_key)
            if isinstance(dialog_tree, dict):
                dialog_tree_evidence.setdefault(scene_key, dialog_tree)
            elif not entries:
                unresolved.append({
                    "kind": "missingDialogTimelineAndDialogTreeEvidence",
                    "sceneKey": scene_key,
                    "source": ref.get("source"),
                    "checkedSources": [
                        "recovered AnimeStudio timeline_line_orders.json",
                        "exact typed AnimeStudio TextAsset/DialogTree",
                    ],
                })
    return evidence, dialog_tree_evidence, unresolved


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


def is_call_server_self_uid_callback(node_key: str, step: dict | None) -> bool:
    """Return whether a hash-like payload is the owning CallServer record UID.

    Current-build ``CallServer`` rows serialize ``eventName`` as ``#`` plus
    their own eight-hex-digit action UID. That is an action-local callback /
    correlation label, not an independent Story node or mission-order edge.
    Require the exact typed opcode and source UID so unrelated hash-shaped
    payloads remain available for future recovery.
    """
    if not is_levelscript_hash_key(node_key) or not isinstance(step, dict):
        return False
    source = step.get("source")
    if not isinstance(source, dict):
        source = ((step.get("_debug") or {}).get("source") or {})
    if not isinstance(source, dict):
        return False
    code = source.get("code")
    kind = source.get("kind")
    try:
        code_value = int(str(code), 0) if not isinstance(code, int) else code
        kind_value = int(str(kind), 0) if not isinstance(kind, int) else kind
    except (TypeError, ValueError):
        return False
    uid = str(source.get("uid") or "").strip()
    return (
        code_value == 0x0E34
        and kind_value == 0x00
        and re.fullmatch(r"[0-9a-fA-F]{8}", uid) is not None
        and str(node_key).casefold() == f"#{uid}".casefold()
    )


def is_play_dialog_hide_non_identifier_payload(
    node_key: str,
    step: dict | None,
) -> bool:
    """Recognize action-local punctuation beside a real dialog id.

    Two current ``PlayDialogAndHideSceneObjectAction`` records serialize one
    punctuation character (``#`` or ``%``) beside their real dialog ids. With
    no identifier body these values cannot name Story/runtime nodes. Keep the
    guard tied to physical ActionSerializedMap membership, the exact typed
    action, and a co-record dialog payload so broader symbol recovery remains
    fail-closed.
    """
    value = str(node_key or "")
    if (
        len(value) != 1
        or not value.isascii()
        or value.isalnum()
        or value == "_"
        or not isinstance(step, dict)
    ):
        return False
    source = step.get("source")
    if not isinstance(source, dict):
        source = ((step.get("_debug") or {}).get("source") or {})
    if not isinstance(source, dict):
        return False
    if not str(source.get("actionMapRole") or "").startswith("actionList#"):
        return False
    code = source.get("code")
    kind = source.get("kind")
    try:
        code_value = int(str(code), 0) if not isinstance(code, int) else code
        kind_value = int(str(kind), 0) if not isinstance(kind, int) else kind
    except (TypeError, ValueError):
        return False
    if code_value != 0x035A or kind_value != 0x0F:
        return False
    return any(
        isinstance(payload, dict)
        and (
            str(payload.get("kind") or "") in {"dlg", "runtimeDialog"}
            or str(payload.get("sceneKey") or "").startswith(
                ("dlg_", "misc_dlg_")
            )
        )
        for payload in (step.get("payloads") or [])
    )


def typed_cutscene_single_char_parameter_action(
    node_key: str,
    step: dict | None,
) -> str:
    """Return the typed cutscene action for an action-local one-char value.

    Four current-build StartCutscene control/hide records expose a single
    alphabetic character beside the real cutscene id.  The concrete action
    schemas carry cutscene configuration/parameter fields, so that character
    is not a second runtime event or Story identity.  Keep this deliberately
    narrower than generic symbol filtering: require the exact typed action,
    the observed one-character shape, and a cutscene payload in the same
    serialized record.
    """
    value = str(node_key or "")
    if len(value) != 1 or not value.isascii() or not value.isalpha():
        return ""
    if not isinstance(step, dict):
        return ""
    source = step.get("source")
    if not isinstance(source, dict):
        source = ((step.get("_debug") or {}).get("source") or {})
    if not isinstance(source, dict):
        return ""
    if not str(source.get("actionMapRole") or "").startswith("actionList#"):
        return ""
    code = source.get("code")
    kind = source.get("kind")
    try:
        code_value = int(str(code), 0) if not isinstance(code, int) else code
        kind_value = int(str(kind), 0) if not isinstance(kind, int) else kind
    except (TypeError, ValueError):
        return ""
    action_name = {
        (0x049B, 0x13): "StartCutsceneAndControlSceneObjectAction",
        (0x049C, 0x12): "StartCutsceneAndHideSceneObjectAction",
    }.get((code_value, kind_value), "")
    if not action_name:
        return ""
    has_cutscene_payload = any(
        isinstance(payload, dict)
        and (
            payload.get("kind") == "cutscene"
            or str(payload.get("sceneKey") or "").startswith("cutscene_")
        )
        for payload in (step.get("payloads") or [])
    )
    return action_name if has_cutscene_payload else ""


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


def _logic_id_from_entity_ptr(value: Any) -> int | None:
    value = _unwrap_const(value)
    if not isinstance(value, dict) or value.get("useSlotId") is not False:
        return None
    logic_id = value.get("logicId")
    if (
        not isinstance(logic_id, int)
        or isinstance(logic_id, bool)
        or logic_id <= 0
        or logic_id > 0xFFFFFFFFFFFFFFFF
    ):
        return None
    return logic_id


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


def decode_mission_interactive_script_entity_conditions(raw: dict) -> list[dict]:
    """Decode exact ``InteractiveCheckInt`` script-entity candidates.

    ``InteractiveCheckInt._entityId`` is an ``EntityPtr``-like constant, not
    intrinsically a LevelScript reference.  This helper therefore preserves
    only the authored tuple and never promotes it by itself.  Callers must
    additionally prove that ``logicId`` is a current-build
    ``WorldEntityRegistry`` script id and that the matching LevelScript exists
    in the exact ``_levelId`` scene.

    Slot-backed pointers are deliberately excluded: their ``logicId`` member
    is not the selected identity when ``useSlotId`` is true.
    """
    out: list[dict] = []

    def walk(value: Any, quest_id: str = "") -> None:
        if isinstance(value, dict):
            next_quest_id = quest_id
            if isinstance(value.get("questId"), str):
                next_quest_id = value["questId"]
            type_name = _safe_key(value.get("$type"))
            short_name = type_name.split(",", 1)[0].rsplit(".", 1)[-1]
            if short_name == "InteractiveCheckInt":
                entity_value = _unwrap_const(value.get("_entityId"))
                level_id = _safe_key(
                    _unwrap_const(
                        value.get(
                            "_levelId",
                            value.get("levelId", value.get("_sceneId")),
                        )
                    )
                )
                if (
                    isinstance(entity_value, dict)
                    and entity_value.get("useSlotId") is False
                    and isinstance(entity_value.get("logicId"), int)
                    and not isinstance(entity_value.get("logicId"), bool)
                    and 0 < entity_value["logicId"] <= 0xFFFFFFFFFFFFFFFF
                    and level_id
                ):
                    out.append({
                        "questId": next_quest_id,
                        "type": type_name,
                        "mapId": level_id,
                        "logicId": entity_value["logicId"],
                        "useSlotId": False,
                        "slotId": entity_value.get("slotId"),
                        "key": _safe_key(_unwrap_const(value.get("_key"))),
                        "compareValue": _unwrap_const(value.get("_compareValue")),
                        "comparer": _unwrap_const(value.get("_comparer")),
                    })
            for child in value.values():
                walk(child, next_quest_id)
        elif isinstance(value, list):
            for child in value:
                walk(child, quest_id)

    walk(raw)
    return out


def decode_mission_world_entity_condition_refs(raw: dict) -> list[dict]:
    """Return exact logic-backed EntityPtr references from typed conditions.

    This is a corpus-uniqueness helper for foreign-key joins.  It retains
    direct ``_entityId`` and ``_enemyIds`` EntityPtr shapes only when the
    pointer is logic-backed and the containing typed node names a level.
    """
    out: list[dict] = []
    seen: set[tuple[str, str, str, int, str]] = set()

    def walk(value: Any, quest_id: str = "", path: str = "$") -> None:
        if isinstance(value, dict):
            next_quest_id = quest_id
            if isinstance(value.get("questId"), str):
                next_quest_id = value["questId"]
            type_name = _safe_key(value.get("$type"))
            short_name = type_name.split(",", 1)[0].rsplit(".", 1)[-1]
            map_id = _safe_key(
                _unwrap_const(
                    value.get(
                        "_levelId",
                        value.get(
                            "levelId",
                            value.get("_sceneId", value.get("sceneId")),
                        ),
                    )
                )
            )
            candidates: list[tuple[str, int]] = []
            direct_logic_id = _logic_id_from_entity_ptr(value.get("_entityId"))
            if direct_logic_id is not None:
                candidates.append(("_entityId", direct_logic_id))
            raw_enemy_ids = _unwrap_const(value.get("_enemyIds"))
            if isinstance(raw_enemy_ids, list):
                for index, raw_entity in enumerate(raw_enemy_ids):
                    logic_id = _logic_id_from_entity_ptr(raw_entity)
                    if logic_id is not None:
                        candidates.append((f"_enemyIds[{index}]", logic_id))
            if short_name and next_quest_id and map_id:
                for field_name, logic_id in candidates:
                    signature = (
                        next_quest_id,
                        short_name,
                        map_id,
                        logic_id,
                        field_name,
                    )
                    if signature in seen:
                        continue
                    seen.add(signature)
                    out.append({
                        "questId": next_quest_id,
                        "type": type_name,
                        "conditionType": short_name,
                        "mapId": map_id,
                        "logicId": logic_id,
                        "field": field_name,
                        "conditionPath": path,
                    })
            for key, child in value.items():
                walk(child, next_quest_id, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, quest_id, f"{path}[{index}]")

    walk(raw)
    return out


def decode_mission_world_entity_condition_groups(raw: dict) -> list[dict]:
    """Decode authored MissionRuntime condition groups of WorldEntity ids.

    The ids are preserved as foreign keys only.  They are not LevelScript ids
    and this helper never promotes them by itself.  Callers must prove, from a
    fully decoded current-build ``LevelScriptBriefData.refWorldEntity`` list,
    that every member of the group resolves uniquely to one exact script in
    the same level.

    Two current serialized shapes are accepted fail-closed:

    * ``CheckMonsterKilled._enemyIds``: one typed EntityPtr array;
    * a ``CombineCondition`` whose direct children are all
      ``InteractiveCheckInt`` records in one level.

    Slot-backed EntityPtrs, singleton groups, mixed direct children, and
    cross-level groups are deliberately rejected.
    """
    out: list[dict] = []
    seen: set[tuple[str, str, str, tuple[int, ...]]] = set()

    def emit(
        *,
        quest_id: str,
        group_type: str,
        map_id: str,
        entity_ids: list[int],
        condition_path: str,
        condition_types: list[str],
        condition_eval_string: str = "",
    ) -> None:
        entity_ids = list(dict.fromkeys(entity_ids))
        if not quest_id or not map_id or len(entity_ids) < 2:
            return
        signature = (quest_id, group_type, map_id, tuple(sorted(entity_ids)))
        if signature in seen:
            return
        seen.add(signature)
        row = {
            "questId": quest_id,
            "groupType": group_type,
            "mapId": map_id,
            "entityLogicIds": entity_ids,
            "conditionPath": condition_path,
            "conditionTypes": condition_types,
        }
        if condition_eval_string:
            row["conditionEvalString"] = condition_eval_string
        out.append(row)

    def walk(value: Any, quest_id: str = "", path: str = "$") -> None:
        if isinstance(value, dict):
            next_quest_id = quest_id
            if isinstance(value.get("questId"), str):
                next_quest_id = value["questId"]
            type_name = _safe_key(value.get("$type"))
            short_name = type_name.split(",", 1)[0].rsplit(".", 1)[-1]

            if short_name == "CheckMonsterKilled":
                map_id = _safe_key(
                    _unwrap_const(
                        value.get(
                            "_sceneId",
                            value.get("_levelId", value.get("levelId")),
                        )
                    )
                )
                raw_enemy_ids = _unwrap_const(value.get("_enemyIds"))
                entity_ids: list[int] = []
                valid = isinstance(raw_enemy_ids, list) and bool(raw_enemy_ids)
                if valid:
                    for raw_entity in raw_enemy_ids:
                        logic_id = _logic_id_from_entity_ptr(raw_entity)
                        if logic_id is None:
                            valid = False
                            break
                        entity_ids.append(logic_id)
                if valid:
                    emit(
                        quest_id=next_quest_id,
                        group_type="check_monster_killed_entity_set",
                        map_id=map_id,
                        entity_ids=entity_ids,
                        condition_path=path,
                        condition_types=["CheckMonsterKilled"],
                    )

            if short_name == "CombineCondition":
                direct_children = value.get("subConditions")
                if isinstance(direct_children, list) and len(direct_children) >= 2:
                    map_ids: list[str] = []
                    entity_ids = []
                    valid = True
                    for child in direct_children:
                        if not isinstance(child, dict):
                            valid = False
                            break
                        child_type = _safe_key(child.get("$type"))
                        child_short_name = child_type.split(",", 1)[0].rsplit(".", 1)[-1]
                        if child_short_name != "InteractiveCheckInt":
                            valid = False
                            break
                        map_id = _safe_key(
                            _unwrap_const(
                                child.get(
                                    "_levelId",
                                    child.get("levelId", child.get("_sceneId")),
                                )
                            )
                        )
                        logic_id = _logic_id_from_entity_ptr(child.get("_entityId"))
                        if not map_id or logic_id is None:
                            valid = False
                            break
                        map_ids.append(map_id)
                        entity_ids.append(logic_id)
                    if valid and len(set(map_ids)) == 1:
                        emit(
                            quest_id=next_quest_id,
                            group_type="combined_interactive_int_entity_set",
                            map_id=map_ids[0],
                            entity_ids=entity_ids,
                            condition_path=path,
                            condition_types=["InteractiveCheckInt"],
                            condition_eval_string=_safe_key(
                                value.get("conditionEvalString")
                            ),
                        )

            for key, child in value.items():
                walk(child, next_quest_id, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, quest_id, f"{path}[{index}]")

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
    """Reconstruct executable Story keys per LevelScript from strong edges.

    Weak file/byte/list ordering is deliberately excluded: those rows can span
    two LevelScript files and cannot prove that either endpoint executes in
    either file.  A strong edge is admitted only when it resolves to exactly
    one LevelScript source, preventing cross-file endpoint contamination.
    """
    out: dict[tuple[str, str], set[str]] = defaultdict(set)
    for edge in scene_edges or []:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("kind") or "") not in STRONG_ORDER_EDGE_KINDS:
            continue
        keys = [
            str(edge.get("from") or "").strip(),
            str(edge.get("to") or "").strip(),
        ]
        source_pairs = {
            (map_id, script_id)
            for source_file in edge.get("sourceFiles") or []
            if (map_id_script := levelscript_path_components(source_file))
            for map_id, script_id in [map_id_script]
            if map_id and script_id
        }
        if len(source_pairs) != 1:
            continue
        source_pair = next(iter(source_pairs))
        for key in keys:
            if key:
                out[source_pair].add(key)
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


def levelscript_source_sort_key(source_file: str) -> tuple:
    map_id, script_id = levelscript_path_components(source_file)
    script_num = int(script_id) if str(script_id).isdigit() else 10**18
    return (
        natural_key(map_id),
        script_num,
        natural_key(script_id),
        natural_key(str(source_file or "")),
    )


def script_ref_from_levelscript_source(source_file: str) -> dict:
    map_id, script_id = levelscript_path_components(source_file)
    if not (map_id and script_id):
        return {}
    row: dict[str, Any] = {
        "levelId": map_id,
        "mapId": map_id,
        "scriptId": script_id,
        "file": source_file,
    }
    if script_id.isdigit():
        row["scriptOrder"] = int(script_id)
    return row


def resolve_levelscript_source_path(source_file: str) -> Path | None:
    text = str(source_file or "").strip().replace("\\", "/")
    if not text:
        return None
    candidates: list[Path] = []
    raw_path = Path(text)
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append(ROOT / text)

    map_id, script_id = levelscript_path_components(text)
    if map_id and script_id:
        rel_tail = Path("Data") / "Json" / "LevelScriptData" / map_id / f"{script_id}.json"
        candidates.extend([
            EXPORT_ROOT / "structured" / "StreamingAssets" / rel_tail,
            EXPORT_ROOT / "structured" / "Persistent" / rel_tail,
            EXPORT_ROOT / "raw_vfs" / "StreamingAssets" / "files" / "775A31D1" / rel_tail,
            EXPORT_ROOT / "raw_vfs" / "Persistent" / "files" / "775A31D1" / rel_tail,
        ])

    seen: set[str] = set()
    for candidate in candidates:
        marker = str(candidate)
        if marker in seen:
            continue
        seen.add(marker)
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def extract_levelscript_float_vectors(source_file: str) -> list[dict]:
    """Extract plausible raw float32 xyz triples from one LevelScript file.

    LevelScript exports are binary-ish TextAssets with embedded strings and raw
    values. The useful trigger centers are not guaranteed to be 4-byte aligned,
    so this intentionally scans every byte offset and keeps only finite,
    world-scale triples. Callers still need a quest-pin proximity check before
    treating a vector as meaningful.
    """
    cache_key = str(source_file or "")
    if cache_key in _LEVELSCRIPT_VECTOR_CACHE:
        return _LEVELSCRIPT_VECTOR_CACHE[cache_key]

    path = resolve_levelscript_source_path(cache_key)
    if path is None:
        _LEVELSCRIPT_VECTOR_CACHE[cache_key] = []
        return []
    try:
        if path.stat().st_size > LEVELSCRIPT_SPATIAL_MAX_FILE_BYTES:
            _LEVELSCRIPT_VECTOR_CACHE[cache_key] = []
            return []
        data = read_bytes_cached(path)
    except OSError:
        _LEVELSCRIPT_VECTOR_CACHE[cache_key] = []
        return []

    vectors: list[dict] = []
    for offset in range(0, max(0, len(data) - 11)):
        x, y, z = struct.unpack_from("<fff", data, offset)
        values = (x, y, z)
        if not all(math.isfinite(value) for value in values):
            continue
        if any(abs(value) > LEVELSCRIPT_SPATIAL_MAX_ABS for value in values):
            continue
        if abs(x) < 0.0001 and abs(z) < 0.0001:
            continue
        vectors.append({
            "offset": offset,
            "position": {
                "x": round(float(x), 3),
                "y": round(float(y), 3),
                "z": round(float(z), 3),
            },
        })
        if len(vectors) >= LEVELSCRIPT_SPATIAL_MAX_VECTORS:
            break

    _LEVELSCRIPT_VECTOR_CACHE[cache_key] = vectors
    return vectors


def collect_quest_spatial_pin_targets(mission_flow: dict | None) -> list[dict]:
    if not isinstance(mission_flow, dict):
        return []
    targets: list[dict] = []
    seen: set[tuple] = set()
    for quest_index, quest in enumerate(mission_flow.get("quests") or []):
        if not isinstance(quest, dict):
            continue
        quest_id = str(quest.get("id") or "").strip()
        if not quest_id:
            continue
        flow_index = quest.get("flowIndex", quest_index)
        pin_sources = [
            pin for pin in quest.get("pins") or [] if isinstance(pin, dict)
        ]
        pin_sources.extend(
            pin for pin in quest.get("tracking") or [] if isinstance(pin, dict)
        )
        for pin in pin_sources:
            map_id = str(pin.get("scene") or "").strip()
            position = compact_position(pin.get("position") or pin.get("trackingPos"))
            if not (map_id and position):
                continue
            if abs(float(position.get("x", 0.0))) < 0.0001 and abs(float(position.get("z", 0.0))) < 0.0001:
                continue
            label = (
                str(pin.get("missionAreaId") or "").strip()
                or str(pin.get("npcProxyId") or "").strip()
                or str(pin.get("jumpId") or "").strip()
                or str(pin.get("trackingType") or pin.get("type") or "").strip()
                or map_id
            )
            marker = (
                quest_id,
                map_id,
                label,
                position.get("x"),
                position.get("y"),
                position.get("z"),
            )
            if marker in seen:
                continue
            seen.add(marker)
            row: dict[str, Any] = {
                "questId": quest_id,
                "flowIndex": flow_index,
                "questOrder": quest_index,
                "mapId": map_id,
                "levelId": map_id,
                "label": label,
                "position": position,
            }
            for key in ("missionAreaId", "npcProxyId", "jumpId", "trackingType", "sourceType", "subDataParentId", "levelDataParentId"):
                value = pin.get(key)
                if value not in (None, "", [], {}):
                    row[key] = value
            if "trackingType" not in row and pin.get("type"):
                row["trackingType"] = pin.get("type")
            targets.append(row)
    return targets


def spatial_distance(candidate: dict, pin: dict) -> tuple[float, float, float] | None:
    a = candidate.get("position") if isinstance(candidate, dict) else None
    b = pin.get("position") if isinstance(pin, dict) else None
    if not (isinstance(a, dict) and isinstance(b, dict)):
        return None
    try:
        dx = float(a.get("x", 0.0)) - float(b.get("x", 0.0))
        dy = float(a.get("y", 0.0)) - float(b.get("y", 0.0))
        dz = float(a.get("z", 0.0)) - float(b.get("z", 0.0))
    except (TypeError, ValueError):
        return None
    xz = (dx * dx + dz * dz) ** 0.5
    distance_3d = (dx * dx + dy * dy + dz * dz) ** 0.5
    return xz, abs(dy), distance_3d


def find_levelscript_spatial_matches(source_file: str, pins: list[dict]) -> list[dict]:
    if not pins:
        return []
    script_ref = script_ref_from_levelscript_source(source_file)
    if not script_ref:
        return []

    # A 25-unit X/Z threshold only needs the selected grid cell and its eight
    # neighbors. Preserve original pin order inside that exact candidate set so
    # equal-distance tie behavior remains identical to the former full scan.
    cell_size = LEVELSCRIPT_SPATIAL_XZ_THRESHOLD
    pins_by_cell: dict[tuple[int, int], list[tuple[int, dict]]] = defaultdict(list)
    for pin_index, pin in enumerate(pins):
        position = pin.get("position") if isinstance(pin, dict) else None
        if not isinstance(position, dict):
            continue
        try:
            x = float(position.get("x", 0.0))
            z = float(position.get("z", 0.0))
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(x) and math.isfinite(z)):
            continue
        pins_by_cell[(math.floor(x / cell_size), math.floor(z / cell_size))].append(
            (pin_index, pin)
        )

    best_by_quest: dict[str, dict] = {}
    for vector in extract_levelscript_float_vectors(source_file):
        position = vector.get("position") if isinstance(vector, dict) else None
        if not isinstance(position, dict):
            continue
        try:
            cell_x = math.floor(float(position.get("x", 0.0)) / cell_size)
            cell_z = math.floor(float(position.get("z", 0.0)) / cell_size)
        except (TypeError, ValueError):
            continue
        nearby_pins = sorted(
            (
                indexed_pin
                for dx in (-1, 0, 1)
                for dz in (-1, 0, 1)
                for indexed_pin in pins_by_cell.get((cell_x + dx, cell_z + dz), [])
            ),
            key=lambda item: item[0],
        )
        for _pin_index, pin in nearby_pins:
            distance = spatial_distance(vector, pin)
            if distance is None:
                continue
            distance_xz, delta_y, distance_3d = distance
            if distance_xz > LEVELSCRIPT_SPATIAL_XZ_THRESHOLD:
                continue
            if delta_y > LEVELSCRIPT_SPATIAL_Y_THRESHOLD:
                continue
            quest_id = str(pin.get("questId") or "").strip()
            if not quest_id:
                continue
            candidate = {
                "source": "levelscriptSpatialProximity",
                "strength": "weak",
                "questId": quest_id,
                "flowIndex": pin.get("flowIndex"),
                "questOrder": pin.get("questOrder"),
                "levelId": script_ref.get("levelId"),
                "mapId": script_ref.get("mapId"),
                "scriptId": script_ref.get("scriptId"),
                "file": source_file,
                "offset": vector.get("offset"),
                "distanceXZ": round(distance_xz, 3),
                "distance3d": round(distance_3d, 3),
                "yDelta": round(delta_y, 3),
                "position": vector.get("position"),
                "pin": {
                    key: pin.get(key)
                    for key in ("mapId", "label", "missionAreaId", "npcProxyId", "jumpId", "trackingType", "sourceType", "position")
                    if pin.get(key) not in (None, "", [], {})
                },
                "note": "Weak diagnostic only; LevelScript vector proximity is not promoted to quest chronology.",
            }
            previous = best_by_quest.get(quest_id)
            prev_key = (
                float(previous.get("distanceXZ", 10**9)),
                float(previous.get("yDelta", 10**9)),
                int(previous.get("offset") or 10**9),
            ) if previous else None
            next_key = (
                float(candidate.get("distanceXZ", 10**9)),
                float(candidate.get("yDelta", 10**9)),
                int(candidate.get("offset") or 10**9),
            )
            if previous is None or next_key < prev_key:
                best_by_quest[quest_id] = candidate
    return sorted(
        best_by_quest.values(),
        key=lambda item: (
            float(item.get("distanceXZ", 10**9)),
            float(item.get("yDelta", 10**9)),
            natural_key(str(item.get("questId") or "")),
        ),
    )


def spatial_candidate_key(candidate: dict) -> tuple:
    return (
        candidate.get("questId"),
        candidate.get("mapId"),
        candidate.get("scriptId"),
        candidate.get("offset"),
    )


def spatial_candidate_sort_key(candidate: dict) -> tuple:
    return (
        float(candidate.get("distanceXZ", 10**9)),
        float(candidate.get("yDelta", 10**9)),
        float(candidate.get("distance3d", 10**9)),
        natural_key(str(candidate.get("questId") or "")),
        candidate.get("questOrder") if isinstance(candidate.get("questOrder"), (int, float)) else 10**9,
        candidate.get("flowIndex") if isinstance(candidate.get("flowIndex"), (int, float)) else 10**9,
        natural_key(str(candidate.get("mapId") or "")),
        natural_key(str(candidate.get("levelId") or "")),
        natural_key(str(candidate.get("scriptId") or "")),
        int(candidate.get("offset") or 10**9),
        natural_key(str(candidate.get("file") or "")),
    )


def attach_levelscript_spatial_proximity(
    scene_placement: dict[str, dict],
    mission_flow: dict | None,
) -> list[dict]:
    """Attach weak LevelScript-vector-to-quest-pin diagnostics to scenes.

    This deliberately does not write to ``questIds``. It gives analysts and the
    WebUI a recoverable placement clue while keeping quest-DAG ordering clean.
    """
    pin_targets = collect_quest_spatial_pin_targets(mission_flow)
    if not pin_targets:
        return []
    pins_by_map: dict[str, list[dict]] = defaultdict(list)
    for pin in pin_targets:
        pins_by_map[str(pin.get("mapId") or "")].append(pin)

    attached: list[dict] = []
    matches_by_source_file: dict[str, list[dict]] = {}
    for scene_key, row in sorted(scene_placement.items(), key=lambda item: natural_key(item[0])):
        direct_source_files = sorted(
            scene_placement_source_files(row),
            key=levelscript_source_sort_key,
        )
        inherited_source_files = sorted(
            scene_placement_inherited_source_files(row),
            key=levelscript_source_sort_key,
        )
        if not direct_source_files and not inherited_source_files:
            continue

        def candidates_for(source_files: list[str], placement_evidence: str) -> list[dict]:
            candidates: list[dict] = []
            seen: set[tuple] = set()
            for source_file in source_files:
                map_id, _script_id = levelscript_path_components(source_file)
                pins = pins_by_map.get(map_id) or []
                if not pins:
                    continue
                if source_file not in matches_by_source_file:
                    matches_by_source_file[source_file] = find_levelscript_spatial_matches(
                        source_file,
                        pins,
                    )
                for raw_candidate in matches_by_source_file[source_file]:
                    marker = spatial_candidate_key(raw_candidate)
                    if marker in seen:
                        continue
                    seen.add(marker)
                    candidate = dict(raw_candidate)
                    candidate["placementEvidence"] = placement_evidence
                    candidate["displayOnSpatialMap"] = placement_evidence == "directLevelScriptSource"
                    candidates.append(candidate)
            candidates.sort(key=spatial_candidate_sort_key)
            return candidates

        direct_candidates = candidates_for(direct_source_files, "directLevelScriptSource")
        inherited_candidates = candidates_for(
            inherited_source_files,
            "inheritedCrossFileOrderSource",
        )
        if direct_candidates:
            row["spatialQuestCandidates"] = direct_candidates[:12]
            evidence_kinds = row.setdefault("evidenceKinds", [])
            if "levelscriptSpatialProximity" not in evidence_kinds:
                evidence_kinds.append("levelscriptSpatialProximity")
        if inherited_candidates:
            row["inheritedSpatialQuestCandidates"] = inherited_candidates[:12]
            evidence_kinds = row.setdefault("evidenceKinds", [])
            if "levelscriptSpatialInherited" not in evidence_kinds:
                evidence_kinds.append("levelscriptSpatialInherited")
        for candidate in [*direct_candidates, *inherited_candidates]:
            attached.append({
                "sceneKey": scene_key,
                **candidate,
            })
    return sorted(
        attached,
        key=lambda item: (
            natural_key(str(item.get("sceneKey") or "")),
            *spatial_candidate_sort_key(item),
        ),
    )


def append_source_file(files: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in files:
        files.append(text)


def scene_placement_source_file_groups(row: dict) -> tuple[list[str], list[str]]:
    """Return direct and cross-file-inherited LevelScript carriers.

    ``levelscriptCrossFileOrder`` joins two independently authored files. Its
    source list is useful order context, but neither endpoint proves that the
    other endpoint's Story node physically belongs to that file. Keep those
    files as inherited diagnostics unless another row field independently
    identifies the same file as a direct carrier.
    """
    direct_files: list[str] = []
    inherited_files: list[str] = []
    for edge in [
        *list(row.get("incomingEdges") or []),
        *list(row.get("outgoingEdges") or []),
    ]:
        if not isinstance(edge, dict):
            continue
        target = (
            inherited_files
            if edge.get("kind") == "levelscriptCrossFileOrder"
            else direct_files
        )
        for source_file in edge.get("sourceFiles") or []:
            append_source_file(target, source_file)
    for item in [
        *list(row.get("sequenceNeighbors") or []),
        *list(row.get("storyCallContexts") or []),
        *list(row.get("hashTerminals") or []),
    ]:
        if isinstance(item, dict):
            append_source_file(direct_files, item.get("sourceFile"))
    for item in row.get("timelineEvidence") or []:
        if isinstance(item, dict):
            append_source_file(direct_files, item.get("file"))
    for item in [
        *list(row.get("storyRefSources") or []),
        *list(row.get("clientActionSources") or []),
    ]:
        if isinstance(item, dict):
            append_source_file(direct_files, item.get("file"))
    direct_set = set(direct_files)
    inherited_files = [value for value in inherited_files if value not in direct_set]
    return direct_files, inherited_files


def scene_placement_source_files(row: dict) -> list[str]:
    direct_files, _inherited_files = scene_placement_source_file_groups(row)
    return direct_files


def scene_placement_inherited_source_files(row: dict) -> list[str]:
    _direct_files, inherited_files = scene_placement_source_file_groups(row)
    return inherited_files


def unique_dicts(rows: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for row in rows:
        key = tuple(row.get(field) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def compact_position(value: Any) -> dict | None:
    pos = vector3(value)
    if pos is None:
        return None
    return {
        axis: round(float(pos[axis]), 3)
        for axis in ("x", "y", "z")
    }


def compact_flow_pin(pin: dict) -> dict:
    row: dict[str, Any] = {}
    for key in (
        "scene",
        "trackingType",
        "sourceType",
        "missionAreaId",
        "npcProxyId",
        "jumpId",
        "radius",
        "subDataParentId",
        "levelDataParentId",
        "activeOnTravelLine",
        "needTrackingRoute",
        "routePointCount",
    ):
        value = pin.get(key)
        if value not in (None, "", [], {}):
            row[key] = value
    position = compact_position(pin.get("position") or pin.get("trackingPos"))
    if position is not None:
        row["position"] = position
    return row


def pins_centroid(pins: list[dict]) -> dict | None:
    positions = [
        pin.get("position")
        for pin in pins
        if isinstance(pin.get("position"), dict)
    ]
    if not positions:
        return None
    return {
        axis: round(
            sum(float(position.get(axis, 0.0)) for position in positions) / len(positions),
            3,
        )
        for axis in ("x", "y", "z")
    }


def xz_distance(a: dict | None, b: dict | None) -> float | None:
    if not (isinstance(a, dict) and isinstance(b, dict)):
        return None
    try:
        dx = float(a.get("x", 0.0)) - float(b.get("x", 0.0))
        dz = float(a.get("z", 0.0)) - float(b.get("z", 0.0))
    except (TypeError, ValueError):
        return None
    return round((dx * dx + dz * dz) ** 0.5, 3)


def compact_flow_resources(flow_quest: dict) -> list[dict]:
    resources: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: Any) -> None:
        key = str(value or "").strip()
        if not key:
            return
        marker = (kind, key)
        if marker in seen:
            return
        seen.add(marker)
        resources.append({"kind": kind, "key": key})

    for field_name, kind in (
        ("dialogs", "dlg"),
        ("cutscenes", "cutscene"),
        ("remotecomms", "remotecomm"),
        ("radios", "radio"),
        ("failStoryRefs", "storyRef"),
    ):
        for value in flow_quest.get(field_name) or []:
            add(kind, value)
    for anchor in flow_quest.get("objectiveAnchors") or []:
        if not isinstance(anchor, dict):
            continue
        for value in anchor.get("storyRefs") or []:
            add("objectiveStoryRef", value)
    for item in flow_quest.get("levelDataStoryRefs") or []:
        if isinstance(item, dict):
            add("levelDataStoryRef", item.get("storyRef"))
        else:
            add("levelDataStoryRef", item)
    for item in flow_quest.get("proxyDialogs") or []:
        if isinstance(item, dict):
            add("proxyDialog", item.get("dialogId"))
        else:
            add("proxyDialog", item)
    return resources


def compact_flow_script_refs(flow_quest: dict) -> list[dict]:
    refs: list[dict] = []
    for anchor in flow_quest.get("objectiveAnchors") or []:
        if not isinstance(anchor, dict):
            continue
        scene_ids = [
            str(value or "").strip()
            for value in anchor.get("sceneIds") or []
            if str(value or "").strip()
        ]
        for leaf in anchor.get("conditionLeaves") or []:
            if not isinstance(leaf, dict):
                continue
            leaf_scene_ids = [
                str(value or "").strip()
                for value in leaf.get("sceneIds") or []
                if str(value or "").strip()
            ] or scene_ids
            script_ids = [
                str(value or "").strip()
                for value in leaf.get("scriptIds") or []
                if str(value or "").strip()
            ]
            keys = [
                str(value or "").strip()
                for value in leaf.get("keys") or []
                if str(value or "").strip()
            ]
            for script_id in script_ids:
                row: dict[str, Any] = {
                    "type": leaf.get("type") or "",
                    "scriptId": script_id,
                }
                if leaf_scene_ids:
                    row["mapId"] = leaf_scene_ids[0]
                    row["levelId"] = leaf_scene_ids[0]
                if keys:
                    row["key"] = keys[0]
                refs.append({key: value for key, value in row.items() if value not in (None, "", [], {})})
    return unique_dicts(refs, ("type", "mapId", "scriptId", "key"))


def build_quest_spatial_track(
    mission_flow: dict | None,
    scene_placement: dict[str, dict],
) -> list[dict]:
    """Build quest-local map/resource diagnostics for visual placement.

    Pins, resource lists, condition metadata, and weak spatial matches help a
    human compare placed scenes with the quest route, but they are not treated
    as proof by themselves.
    """
    if not isinstance(mission_flow, dict):
        return []
    scenes_by_quest: dict[str, set[str]] = defaultdict(set)
    spatial_by_quest: dict[str, list[dict]] = defaultdict(list)
    inherited_spatial_by_quest: dict[str, list[dict]] = defaultdict(list)
    for scene_key, placement in sorted(scene_placement.items(), key=lambda item: natural_key(item[0])):
        for quest_id in placement.get("questIds") or []:
            quest_id = str(quest_id or "").strip()
            if not quest_id:
                continue
            scenes_by_quest[quest_id].add(scene_key)
        for placement_field, target in (
            ("spatialQuestCandidates", spatial_by_quest),
            ("inheritedSpatialQuestCandidates", inherited_spatial_by_quest),
        ):
            for candidate in placement.get(placement_field) or []:
                if not isinstance(candidate, dict):
                    continue
                quest_id = str(candidate.get("questId") or "").strip()
                if not quest_id:
                    continue
                match = {
                    key: candidate.get(key)
                    for key in (
                        "mapId",
                        "levelId",
                        "scriptId",
                        "distanceXZ",
                        "distance3d",
                        "yDelta",
                        "offset",
                        "placementEvidence",
                        "displayOnSpatialMap",
                    )
                    if candidate.get(key) not in (None, "", [], {})
                }
                match["sceneKey"] = scene_key
                if candidate.get("position"):
                    match["position"] = candidate.get("position")
                pin = candidate.get("pin") if isinstance(candidate.get("pin"), dict) else {}
                if pin:
                    match["pin"] = {
                        key: pin.get(key)
                        for key in ("label", "missionAreaId", "npcProxyId", "jumpId", "trackingType", "subDataParentId", "levelDataParentId", "position")
                        if pin.get(key) not in (None, "", [], {})
                    }
                target[quest_id].append(match)

    rows: list[dict] = []
    previous_centroid: dict | None = None
    for index, quest in enumerate(mission_flow.get("quests") or []):
        if not isinstance(quest, dict):
            continue
        quest_id = str(quest.get("id") or "").strip()
        if not quest_id:
            continue
        pins = [
            compact_flow_pin(pin)
            for pin in quest.get("pins") or []
            if isinstance(pin, dict)
        ]
        if not pins:
            pins = [
                compact_flow_pin(pin)
                for pin in quest.get("tracking") or []
                if isinstance(pin, dict)
                and compact_position(pin.get("position") or pin.get("trackingPos")) is not None
            ]
        centroid = pins_centroid(pins)
        distance = xz_distance(previous_centroid, centroid)
        if centroid is not None:
            previous_centroid = centroid

        row: dict[str, Any] = {
            "questId": quest_id,
            "flowIndex": quest.get("flowIndex", index),
            "questOrder": index,
            "prevQuestIds": [
                str(value)
                for value in quest.get("prev") or []
                if str(value or "")
            ],
            "scenes": [
                str(value)
                for value in quest.get("scenes") or []
                if str(value or "")
            ][:8],
            "note": "Map/resource metadata is a diagnostic placement hint, not standalone chronology evidence.",
        }
        if scenes_by_quest.get(quest_id):
            row["attachedSceneKeys"] = sorted(scenes_by_quest[quest_id], key=natural_key)[:16]
        if spatial_by_quest.get(quest_id):
            row["spatialSourceMatches"] = unique_dicts(
                sorted(
                    spatial_by_quest[quest_id],
                    key=lambda item: (
                        float(item.get("distanceXZ", 10**9)),
                        float(item.get("yDelta", 10**9)),
                        float(item.get("distance3d", 10**9)),
                        natural_key(str(item.get("sceneKey") or "")),
                        natural_key(str(item.get("mapId") or "")),
                        natural_key(str(item.get("levelId") or "")),
                        natural_key(str(item.get("scriptId") or "")),
                        int(item.get("offset") or 10**9),
                    ),
                ),
                ("sceneKey", "mapId", "scriptId", "offset"),
            )[:16]
        if inherited_spatial_by_quest.get(quest_id):
            row["inheritedSpatialSourceMatches"] = unique_dicts(
                sorted(
                    inherited_spatial_by_quest[quest_id],
                    key=lambda item: (
                        float(item.get("distanceXZ", 10**9)),
                        float(item.get("yDelta", 10**9)),
                        float(item.get("distance3d", 10**9)),
                        natural_key(str(item.get("sceneKey") or "")),
                        natural_key(str(item.get("mapId") or "")),
                        natural_key(str(item.get("levelId") or "")),
                        natural_key(str(item.get("scriptId") or "")),
                        int(item.get("offset") or 10**9),
                    ),
                ),
                ("sceneKey", "mapId", "scriptId", "offset"),
            )[:16]
        resources = compact_flow_resources(quest)
        if resources:
            row["resources"] = resources[:20]
            if len(resources) > 20:
                row["resourceCount"] = len(resources)
        script_refs = compact_flow_script_refs(quest)
        if script_refs:
            row["scriptRefs"] = script_refs[:12]
        condition_types = sorted({
            str(value)
            for anchor in quest.get("objectiveAnchors") or []
            if isinstance(anchor, dict)
            for value in (anchor.get("conditionTypes") or [])
            if str(value or "")
        })
        if condition_types:
            row["conditionTypes"] = condition_types
        descriptions = []
        objective_instructions = []
        for anchor in quest.get("objectiveAnchors") or []:
            if not isinstance(anchor, dict):
                continue
            if anchor.get("descriptionKey"):
                descriptions.append(str(anchor.get("descriptionKey") or ""))
            descriptions.extend(
                str(key)
                for key in (anchor.get("multipleDescriptionKeys") or [])
                if str(key or "")
            )
            for instruction in anchor.get("objectiveInstructions") or []:
                if isinstance(instruction, dict):
                    objective_instructions.append(instruction)
        if descriptions:
            row["descriptionKeys"] = unique_preserve(descriptions)[:8]
        if objective_instructions:
            row["objectiveInstructions"] = unique_dicts(
                objective_instructions,
                ("key", "text"),
            )[:12]
        if pins:
            row["pinCount"] = len(pins)
            row["pins"] = pins[:8]
        if centroid is not None:
            row["centroid"] = centroid
        if distance is not None:
            row["distanceFromPrevious"] = distance
        rows.append({
            key: value
            for key, value in row.items()
            if value not in (None, "", [], {})
            or key in {"questId", "flowIndex", "questOrder"}
        })
    return rows


# Scene kinds the WebUI treats as orderable story scenes. Mirrors
# ORDER_INCLUDE_KINDS in
# scratch/story/main_story_order_compare/recover_main_story_order_compare.py.
SCENE_ORDER_INCLUDE_KINDS = frozenset({
    "black",
    "cutscene",
    "dlg",
    "env",
    "radio",
    "remotecomm",
    "sns",
    "text",
    "video",
})


def scene_order_infer_kind(key: str, kind_hint: str = "") -> str:
    """Classify a scene key for sceneOrderInfo.

    Mirrors ``infer_kind`` in the scratch order-compare report: an explicit
    index ``d`` hint wins, otherwise the kind is read from the key prefix.
    """
    if kind_hint:
        return str(kind_hint)
    key = str(key or "")
    if key.startswith("misc_dlg_") or key.startswith("dlg_"):
        return "dlg"
    if key.startswith("env_"):
        return "env"
    return key.split("_", 1)[0] if "_" in key else "unknown"


def _scene_order_walk_values(node: Any) -> list[str]:
    out: list[str] = []
    if isinstance(node, dict):
        for value in node.values():
            out.extend(_scene_order_walk_values(value))
    elif isinstance(node, list):
        for value in node:
            out.extend(_scene_order_walk_values(value))
    elif isinstance(node, str):
        out.append(node)
    return out


def build_scene_order_candidate_kinds(
    index_entries: list[dict] | None,
    mission_id: str,
    override_keys: list[str] | None = None,
) -> dict[str, str]:
    """Build the {sceneKey: indexKindHint} candidate set for one mission.

    Mirrors the candidate-key selection in the scratch order-compare report:
    index entries whose inferred kind is an orderable story kind, plus every
    story-order override key (kept unfiltered), minus hash terminals.
    """
    mission_id = str(mission_id or "")
    candidate_kinds: dict[str, str] = {}
    for entry in index_entries or []:
        if not isinstance(entry, dict) or str(entry.get("m") or "") != mission_id:
            continue
        key = str(entry.get("k") or "")
        if not key or key.startswith("#"):
            continue
        hint = str(entry.get("d") or "")
        if scene_order_infer_kind(key, hint) in SCENE_ORDER_INCLUDE_KINDS:
            candidate_kinds[key] = hint
    for key in override_keys or []:
        key = str(key or "")
        if key and not key.startswith("#"):
            candidate_kinds.setdefault(key, "")
    return candidate_kinds


def build_scene_order_info(
    mission_flow: dict | None,
    quest_spatial_track: list[dict] | None,
    quests: list[dict] | None,
    scene_placement: dict[str, dict] | None,
    candidate_kinds: dict[str, str],
) -> dict[str, dict]:
    """Resolve additive per-scene static order CONFIDENCE + PHASE for the WebUI.

    Ports the per-key resolution from
    scratch/story/main_story_order_compare/recover_main_story_order_compare.py so the
    maintained builder emits the same questOrder / orderSource / confidence /
    evidenceKinds the scratch report's ``keyInfo`` carries. This is STATIC
    recovery only: confidence never folds in any OCR-derived signal. It adds no
    new ordering heuristic and does not change any existing field or sort.
    """
    flow = mission_flow if isinstance(mission_flow, dict) else {}
    quest_spatial_track = quest_spatial_track or []
    quests = quests or []
    scene_placement = scene_placement if isinstance(scene_placement, dict) else {}
    candidate_kinds = candidate_kinds or {}
    candidate_keys = {
        str(key)
        for key in candidate_kinds
        if str(key) and not str(key).startswith("#")
    }

    quest_order_by_id: dict[str, int] = {}
    flow_index_by_order: dict[int, Any] = {}
    for row in quest_spatial_track:
        if not isinstance(row, dict):
            continue
        quest_order = row.get("questOrder")
        quest_id = str(row.get("questId") or "")
        if quest_id and isinstance(quest_order, int):
            quest_order_by_id.setdefault(quest_id, int(quest_order))
        if isinstance(quest_order, int):
            flow_index_by_order.setdefault(int(quest_order), row.get("flowIndex"))
    for index, row in enumerate(quests):
        if not isinstance(row, dict):
            continue
        quest_id = str(row.get("questId") or "")
        if quest_id:
            quest_order_by_id.setdefault(quest_id, index)

    flow_attach: dict[str, list[int]] = defaultdict(list)
    for index, quest in enumerate(flow.get("quests") or []):
        if not isinstance(quest, dict):
            continue
        values = set(_scene_order_walk_values(quest))
        for key in candidate_keys:
            if key in values:
                flow_attach[key].append(index)

    quest_spatial_attach: dict[str, list[int]] = defaultdict(list)
    for row in quest_spatial_track:
        if not isinstance(row, dict) or not isinstance(row.get("questOrder"), int):
            continue
        quest_order = int(row["questOrder"])
        row_keys: set[str] = set()
        for key in row.get("attachedSceneKeys") or []:
            row_keys.add(str(key))
        for resource in row.get("resources") or []:
            if isinstance(resource, dict) and resource.get("key"):
                row_keys.add(str(resource["key"]))
        for match in row.get("spatialSourceMatches") or []:
            if isinstance(match, dict) and match.get("sceneKey"):
                row_keys.add(str(match["sceneKey"]))
        for key in candidate_keys & row_keys:
            quest_spatial_attach[key].append(quest_order)

    out: dict[str, dict] = {}
    for key in sorted(candidate_keys, key=natural_key):
        placement = scene_placement.get(key) if isinstance(scene_placement.get(key), dict) else {}
        candidates: list[tuple[int, int, str]] = []
        for order in flow_attach.get(key) or []:
            candidates.append((int(order), 0, "flowQuestAttachment"))
        for quest_id in placement.get("questIds") or []:
            if quest_id in quest_order_by_id:
                candidates.append((quest_order_by_id[quest_id], 1, "scenePlacementQuest"))
        for order in quest_spatial_attach.get(key) or []:
            candidates.append((int(order), 2, "questSpatialTrack"))
        for spatial in placement.get("spatialQuestCandidates") or []:
            if isinstance(spatial, dict) and isinstance(spatial.get("questOrder"), int):
                candidates.append((int(spatial["questOrder"]), 3, "levelscriptSpatialProximity"))

        if candidates:
            quest_order, source_priority, source = sorted(candidates)[0]
        else:
            quest_order, source_priority, source = 999999, 9, "numericFallback"
        evidence_kinds = sorted(str(value) for value in (placement.get("evidenceKinds") or []))
        if source_priority <= 1 or any(kind.startswith("sourceBacked") for kind in evidence_kinds):
            confidence = "source-backed"
        elif source_priority <= 3:
            confidence = "weak"
        else:
            confidence = "fallback"
        resolved_order = quest_order if quest_order != 999999 else None
        out[key] = {
            "questOrder": resolved_order,
            "flowIndex": flow_index_by_order.get(quest_order) if resolved_order is not None else None,
            "orderSource": source,
            "confidence": confidence,
            "kind": scene_order_infer_kind(key, candidate_kinds.get(key, "")),
            "evidenceKinds": evidence_kinds,
        }
    return out


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
        hash_step = terminal.get("hashStep") or {}
        if is_call_server_self_uid_callback(hash_key, hash_step):
            continue
        row = {
            "kind": terminal.get("kind") or "levelscriptHashTerminal",
            "sourceFile": terminal.get("file") or terminal.get("sourceFile") or "",
            "levelId": terminal.get("levelId") or "",
            "sceneKey": scene_key,
            "hash": hash_key,
            "direction": terminal.get("direction") or "",
            "sourceStep": terminal.get("sourceStep") or {},
            "hashStep": hash_step,
            "recoveredBy": "scripts/story_builder/build.py",
        }
        if source:
            bundle_source = dict(source)
            bundle_source["field"] = f"{bundle_source.get('field', 'flow.sceneGraph.levelscriptHashTerminals')}[{index}]"
            row["bundleSource"] = bundle_source
        out.append(row)
    return out


def source_backed_call_server_callbacks_from_scene_graph(
    scene_graph: dict | None,
    source: dict | None = None,
) -> list[dict]:
    """Load diagnostic-only self-UID CallServer callback labels."""
    callbacks = (scene_graph or {}).get("levelscriptCallServerCallbacks")
    if not isinstance(callbacks, list):
        return []

    out: list[dict] = []
    for index, callback in enumerate(callbacks):
        if not isinstance(callback, dict):
            continue
        label = str(callback.get("callbackLabel") or "").strip()
        source_step = callback.get("sourceStep") or {}
        if not is_call_server_self_uid_callback(label, source_step):
            continue
        row = {
            "kind": callback.get("kind") or "levelscriptCallServerSelfUidCallback",
            "sourceFile": callback.get("file") or callback.get("sourceFile") or "",
            "levelId": callback.get("levelId") or "",
            "precedingSceneKey": callback.get("precedingSceneKey") or "",
            "callbackLabel": label,
            "recordUid": callback.get("recordUid") or "",
            "identityRole": "self_uid_callback_label",
            "storyNode": False,
            "missionOwnershipEvidence": False,
            "orderEvidence": False,
            "sourceStep": source_step,
            "recoveredBy": "scripts/story_builder/build.py",
        }
        if source:
            bundle_source = dict(source)
            bundle_source["field"] = (
                f"{bundle_source.get('field', 'flow.sceneGraph.levelscriptCallServerCallbacks')}"
                f"[{index}]"
            )
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
                if is_call_server_self_uid_callback(hash_key, hash_step):
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


def load_mission_flow(mission_id: str, generated_mission_dir: Path | None) -> dict | None:
    """Load the WebUI builder's per-mission flow payload, if available."""
    if not generated_mission_dir:
        return None
    path = generated_mission_dir / f"{mission_id}.json"
    if not path.exists():
        return None
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError):
        return None
    flow = payload.get("flow")
    return flow if isinstance(flow, dict) else None


def attach_variant_mission_runtime_quests(
    scene_placement: dict[str, dict],
    mission_flow: dict | None,
) -> list[dict]:
    """Attach variant-mission quest ids based on the WebUI scene graph.

    Some missions reuse another mission's quest graph (the WebUI builder
    records the foreign mission ids in ``flow.sceneGraphVariantMissions``).
    Their decoded scene-graph edges carry ``questIds`` from those variant
    missions; both endpoints of such edges are reachable from the variant
    quest, so we attach the quest to the scene-placement entries.

    Returns a diagnostic list of attachments.
    """
    attached: list[dict] = []
    if not isinstance(mission_flow, dict):
        return attached
    variant_missions = {
        str(value).strip()
        for value in mission_flow.get("sceneGraphVariantMissions") or []
        if str(value or "").strip()
    }
    if not variant_missions:
        return attached
    scene_graph = mission_flow.get("sceneGraph") or {}
    for edge in scene_graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        edge_quest_ids = [
            str(quest_id).strip()
            for quest_id in edge.get("questIds") or []
            if str(quest_id or "").strip()
            and str(quest_id).split("_q#", 1)[0] in variant_missions
        ]
        if not edge_quest_ids:
            continue
        from_key = str(edge.get("from") or "").strip()
        to_key = str(edge.get("to") or "").strip()
        for scene_key in (from_key, to_key):
            row = scene_placement.get(scene_key)
            if row is None:
                continue
            quest_ids = row.setdefault("questIds", [])
            sources = row.setdefault("questAttachSources", [])
            for quest_id in edge_quest_ids:
                already = quest_id in quest_ids
                if not already:
                    quest_ids.append(quest_id)
                variant_mission = quest_id.split("_q#", 1)[0]
                source_record = {
                    "questId": quest_id,
                    "source": "variantMissionRuntime",
                    "variantMission": variant_mission,
                    "kind": edge.get("kind") or "",
                }
                if source_record not in sources:
                    sources.append(source_record)
                attached.append({
                    "sceneKey": scene_key,
                    "questId": quest_id,
                    "variantMission": variant_mission,
                    "edgeKind": edge.get("kind") or "",
                    "alreadyAttached": already,
                })
            kinds = row.setdefault("evidenceKinds", [])
            if "variantMissionRuntimeQuestAttach" not in kinds:
                kinds.append("variantMissionRuntimeQuestAttach")
    return attached


def attach_npc_proxy_dialog_quests(
    scene_placement: dict[str, dict],
    mission_flow: dict | None,
) -> list[dict]:
    """Attach quest ids based on NPC proxy dialog references.

    The WebUI builder collects ``flow.quests[*].proxyDialogs[*]`` records
    that bind an NPC proxy to a dialog scene key for a given quest. The
    attached scene gets the quest id so scene placement and the quest map
    track can use the relationship.
    """
    attached: list[dict] = []
    if not isinstance(mission_flow, dict):
        return attached
    for quest in mission_flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = str(quest.get("id") or "").strip()
        if not quest_id:
            continue
        for proxy_ref in quest.get("proxyDialogs") or []:
            if not isinstance(proxy_ref, dict):
                continue
            scene_key = str(proxy_ref.get("dialogId") or "").strip()
            row = scene_placement.get(scene_key)
            if row is None:
                misc_key = f"misc_{scene_key}" if scene_key.startswith("dlg_") else scene_key
                row = scene_placement.get(misc_key)
                if row is None:
                    continue
                scene_key = misc_key
            quest_ids = row.setdefault("questIds", [])
            sources = row.setdefault("questAttachSources", [])
            already = quest_id in quest_ids
            if not already:
                quest_ids.append(quest_id)
            source_record = {
                "questId": quest_id,
                "source": "npcProxyDialog",
                "npcProxyId": str(proxy_ref.get("npcProxyId") or ""),
                "dialogId": str(proxy_ref.get("dialogId") or ""),
            }
            if source_record not in sources:
                sources.append(source_record)
            attached.append({
                "sceneKey": scene_key,
                "questId": quest_id,
                "npcProxyId": str(proxy_ref.get("npcProxyId") or ""),
                "alreadyAttached": already,
            })
            kinds = row.setdefault("evidenceKinds", [])
            if "npcProxyDialogQuestAttach" not in kinds:
                kinds.append("npcProxyDialogQuestAttach")
    return attached


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


def load_source_backed_call_server_callbacks(
    mission_id: str,
    generated_mission_dir: Path | None,
) -> list[dict]:
    """Load non-Story CallServer callback-label diagnostics."""
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
    return source_backed_call_server_callbacks_from_scene_graph(
        scene_graph,
        source=source_ref(path, "flow.sceneGraph.levelscriptCallServerCallbacks"),
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

    Each attachment is recorded both on the placement row's ``questIds`` and
    on its ``questAttachSources`` diagnostic for traceability. Returns the
    list of attached records for auditing.
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
        for scene_key in sorted(story_keys, key=natural_key):
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
    return sorted(
        attached,
        key=lambda item: (
            natural_key(str(item.get("sceneKey") or "")),
            natural_key(str(item.get("questId") or "")),
            natural_key(str(item.get("mapId") or "")),
            natural_key(str(item.get("scriptId") or "")),
        ),
    )


def recover_mission(
    path: Path,
    timeline_index: dict[str, list[dict]],
    generated_mission_dir: Path | None,
    source_backed_scene_edges: list[dict] | None = None,
    source_backed_story_call_contexts: list[dict] | None = None,
    source_backed_hash_terminals: list[dict] | None = None,
    source_backed_call_server_callbacks: list[dict] | None = None,
    script_condition_ownership: dict[tuple[str, str], list[str]] | None = None,
    mission_flow: dict | None = None,
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
    (
        timeline_evidence,
        dialog_tree_evidence,
        timeline_unresolved,
    ) = attach_timeline_evidence(all_refs, timeline_index)
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
    call_server_callbacks = (
        source_backed_call_server_callbacks
        if source_backed_call_server_callbacks is not None
        else load_source_backed_call_server_callbacks(mission_id, generated_mission_dir)
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
    if mission_flow is None:
        mission_flow = load_mission_flow(mission_id, generated_mission_dir)
    variant_mr_attachments = attach_variant_mission_runtime_quests(
        scene_placement,
        mission_flow,
    )
    npc_proxy_attachments = attach_npc_proxy_dialog_quests(
        scene_placement,
        mission_flow,
    )
    levelscript_spatial_proximity = attach_levelscript_spatial_proximity(
        scene_placement,
        mission_flow,
    )
    quest_spatial_track = build_quest_spatial_track(mission_flow, scene_placement)
    payload = {
        "mission": mission_id,
        "metadata": metadata,
        "propertyModel": extract_properties(raw, path),
        "questLayers": build_quest_layers(quests),
        "entryQuestIds": entry_quests,
        "quests": quests,
        "questEdges": quest_edges,
        "branchPoints": build_branch_points(quest_edges, quests_by_id),
        "sourceBackedSceneEdges": scene_edges,
        "sourceBackedSceneSequences": scene_sequences,
        "sourceBackedStoryCallContexts": story_call_contexts,
        "sourceBackedHashTerminals": hash_terminals,
        "sourceBackedCallServerCallbacks": call_server_callbacks,
        "referencedScenes": referenced_scenes,
        "sceneTimelineEvidence": timeline_evidence,
        "sceneDialogTreeEvidence": dialog_tree_evidence,
        "scenePlacement": scene_placement,
        "questSpatialTrack": quest_spatial_track,
        "scriptConditionAttachments": script_condition_attachments,
        "variantMissionRuntimeAttachments": variant_mr_attachments,
        "npcProxyDialogAttachments": npc_proxy_attachments,
        "levelscriptSpatialProximity": levelscript_spatial_proximity,
        "unresolved": unresolved,
    }
    return payload


def enrich_source_backed_scene_edge_context(
    timeline_recovery: dict | None,
    scene_graph: dict | None,
) -> int:
    """Copy typed action/header context onto the WebUI timeline edge copy.

    Mission recovery and the localized scene graph preserve parallel copies of
    the same source-backed edges. The Story panel renders the former, while
    physical ActionSerializedMap membership is recovered while building the
    latter. Join only on the complete edge identity and copy diagnostic fields;
    this never changes edge kind, direction, ownership, or order strength.
    """
    if not isinstance(timeline_recovery, dict) or not isinstance(scene_graph, dict):
        return 0
    context_by_edge: dict[tuple[str, str, str], dict] = {}
    for edge in scene_graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        signature = (
            str(edge.get("from") or ""),
            str(edge.get("to") or ""),
            str(edge.get("kind") or ""),
        )
        if not all(signature):
            continue
        if edge.get("sourceActions") or edge.get("sourceEvents"):
            context_by_edge[signature] = edge

    enriched = 0
    for edge in timeline_recovery.get("sourceBackedSceneEdges") or []:
        if not isinstance(edge, dict):
            continue
        signature = (
            str(edge.get("from") or ""),
            str(edge.get("to") or ""),
            str(edge.get("kind") or ""),
        )
        context = context_by_edge.get(signature)
        if not context:
            continue
        changed = False
        for field in ("sourceActions", "sourceActionClasses", "sourceEvents"):
            values = [
                str(value)
                for value in context.get(field) or []
                if str(value)
            ]
            if values and edge.get(field) != values:
                edge[field] = values
                changed = True
        if changed:
            enriched += 1
    return enriched


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
    missions_with_dialog_tree_definitions = 0
    dialog_tree_definition_total = 0
    missions_with_scene_edges = 0
    missions_with_scene_sequences = 0
    missions_with_story_call_contexts = 0
    missions_with_hash_terminals = 0
    missions_with_call_server_callbacks = 0
    scene_edge_counter: Counter = Counter()
    scene_sequence_total = 0
    story_call_context_total = 0
    hash_terminal_total = 0
    call_server_callback_total = 0
    hash_terminal_catalog = build_hash_terminal_catalog(recovered)
    scene_placement_counter: Counter = Counter()
    scene_placement_total = 0
    missions_with_levelscript_spatial = 0
    levelscript_spatial_match_total = 0
    for mission in recovered:
        if mission.get("branchPoints"):
            missions_with_branches += 1
        if mission.get("sceneTimelineEvidence"):
            missions_with_timeline += 1
        if mission.get("sceneDialogTreeEvidence"):
            missions_with_dialog_tree_definitions += 1
            dialog_tree_definition_total += len(
                mission.get("sceneDialogTreeEvidence") or {}
            )
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
        if mission.get("sourceBackedCallServerCallbacks"):
            missions_with_call_server_callbacks += 1
            call_server_callback_total += len(
                mission.get("sourceBackedCallServerCallbacks") or []
            )
        for edge in mission.get("sourceBackedSceneEdges") or []:
            scene_edge_counter[edge.get("kind") or "edge"] += 1
        scene_placement_total += len(mission.get("scenePlacement") or {})
        for placement in (mission.get("scenePlacement") or {}).values():
            for kind in placement.get("evidenceKinds") or []:
                scene_placement_counter[kind] += 1
        spatial_matches = mission.get("levelscriptSpatialProximity") or []
        if spatial_matches:
            missions_with_levelscript_spatial += 1
            levelscript_spatial_match_total += len(spatial_matches)
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
        "missionsWithDialogTimelineEvidence": missions_with_timeline,
        "missionsWithDialogTreeDefinitionEvidence": (
            missions_with_dialog_tree_definitions
        ),
        "dialogTreeDefinitionEvidence": dialog_tree_definition_total,
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
        "missionsWithSourceBackedCallServerCallbacks": missions_with_call_server_callbacks,
        "sourceBackedCallServerCallbacks": call_server_callback_total,
        "scenePlacementEntries": scene_placement_total,
        "missionsWithLevelscriptSpatialProximity": missions_with_levelscript_spatial,
        "levelscriptSpatialProximityMatches": levelscript_spatial_match_total,
        "timelineEvidence": timeline_meta,
        "unresolvedByKind": dict(unresolved_counter.most_common()),
        "sourceBackedSceneEdgesByKind": dict(scene_edge_counter.most_common()),
        "scenePlacementEvidenceByKind": dict(scene_placement_counter.most_common()),
        "clientActionsByType": dict(action_counter.most_common()),
        "conditionTypes": dict(condition_counter.most_common()),
        "trackingTypes": dict(tracking_counter.most_common()),
    }


def build_mission_timeline_recovery_report(
    scene_graphs: dict[str, dict],
    mission_flows: dict[str, dict] | None = None,
    *,
    timeline_orders: Path = DEFAULT_TIMELINE_ORDERS,
    mission_runtime_root: Path = DEFAULT_MRA_DIR,
) -> dict:
    """Build the source-only mission timeline report used by Story output."""
    timeline_index, timeline_meta = load_timeline_index(timeline_orders)
    files = mission_files(mission_runtime_root, set()) if mission_runtime_root.is_dir() else []
    script_condition_ownership = build_script_condition_ownership(files)
    mission_flows = mission_flows or {}
    recovered = [
        recover_mission(
            path,
            timeline_index,
            None,
            source_backed_scene_edges_from_scene_graph(scene_graphs.get(path.stem)),
            source_backed_story_call_contexts_from_scene_graph(scene_graphs.get(path.stem)),
            source_backed_hash_terminals_from_scene_graph(scene_graphs.get(path.stem)),
            source_backed_call_server_callbacks_from_scene_graph(scene_graphs.get(path.stem)),
            script_condition_ownership=script_condition_ownership,
            mission_flow=mission_flows.get(path.stem),
        )
        for path in files
    ]
    return {
        "evidencePolicy": EVIDENCE_POLICY,
        "summary": summarize(
            recovered,
            timeline_meta,
            generated_by="scripts/story_builder/build.py",
        ),
        "missions": recovered,
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
        f"- missions with dialog timeline evidence: `{summary['missionsWithDialogTimelineEvidence']}`",
        (
            "- missions with exact DialogTree definition evidence: "
            f"`{summary.get('missionsWithDialogTreeDefinitionEvidence', 0)}`"
        ),
        (
            "- exact mission-referenced DialogTree definitions: "
            f"`{summary.get('dialogTreeDefinitionEvidence', 0)}`"
        ),
        f"- missions with source-backed scene edges: `{summary['missionsWithSourceBackedSceneEdges']}`",
        f"- missions with source-backed scene sequences: `{summary.get('missionsWithSourceBackedSceneSequences', 0)}`",
        f"- source-backed scene sequences: `{summary.get('sourceBackedSceneSequences', 0)}`",
        f"- missions with source-backed story-call context: `{summary.get('missionsWithSourceBackedStoryCallContexts', 0)}`",
        f"- source-backed story-call contexts: `{summary.get('sourceBackedStoryCallContexts', 0)}`",
        f"- missions with source-backed hash terminals: `{summary.get('missionsWithSourceBackedHashTerminals', 0)}`",
        f"- source-backed hash terminals: `{summary.get('sourceBackedHashTerminals', 0)}`",
        f"- unique source-backed terminal hashes: `{summary.get('sourceBackedHashTerminalUniqueHashes', 0)}`",
        f"- hash-terminal pattern exceptions: `{summary.get('sourceBackedHashTerminalExceptionCount', 0)}`",
        (
            "- missions with diagnostic CallServer self-UID callbacks: "
            f"`{summary.get('missionsWithSourceBackedCallServerCallbacks', 0)}`"
        ),
        (
            "- diagnostic CallServer self-UID callbacks (not Story/order evidence): "
            f"`{summary.get('sourceBackedCallServerCallbacks', 0)}`"
        ),
        f"- scene placement entries: `{summary.get('scenePlacementEntries', 0)}`",
        f"- LevelScript spatial proximity matches (weak): "
        f"`{summary.get('levelscriptSpatialProximityMatches', 0)}` "
        f"across `{summary.get('missionsWithLevelscriptSpatialProximity', 0)}` missions",
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
        "| Mission | Quests | Branches | Timeline Scenes | DialogTrees | Scene Edges | Scene Seq | Story Calls | Hash Terms | CallServer Callbacks | Scene Signals | Unresolved | Level |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    for mission in payload.get("missions") or []:
        metadata = mission.get("metadata") or {}
        lines.append(
            "| "
            f"`{mission.get('mission')}` | "
            f"{len(mission.get('quests') or [])} | "
            f"{len(mission.get('branchPoints') or [])} | "
            f"{len(mission.get('sceneTimelineEvidence') or {})} | "
            f"{len(mission.get('sceneDialogTreeEvidence') or {})} | "
            f"{len(mission.get('sourceBackedSceneEdges') or [])} | "
            f"{len(mission.get('sourceBackedSceneSequences') or [])} | "
            f"{len(mission.get('sourceBackedStoryCallContexts') or [])} | "
            f"{len(mission.get('sourceBackedHashTerminals') or [])} | "
            f"{len(mission.get('sourceBackedCallServerCallbacks') or [])} | "
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
    mra_dir = args.mra_dir or select_complete_mission_runtime_root(
        export_root / "structured" / "StreamingAssets" / "Data" / "Json"
        / "MissionRuntimeAsset",
        export_root / "structured" / "Persistent" / "Data" / "Json"
        / "MissionRuntimeAsset",
    )
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
