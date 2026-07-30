from __future__ import annotations

from .context import *
from .anime_assets import *
from .level_bindings import *
from .level_bindings import _load_levelscript_binding_data
from .levelscript_binary import (
    decode_levelscript_record_payload,
    levelscript_action_map_membership,
)


def _mission_text_key(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("key") or "").strip()
    return ""


_STORY_CONNECTION_FIELDS = (
    *((field, "dialog") for field in _DIALOG_REF_FIELDS),
    *((field, "cutscene") for field in _CUTSCENE_REF_FIELDS),
    *((field, "remotecomm") for field in _REMOTECOMM_REF_FIELDS),
    *((field, "radio") for field in _RADIO_REF_FIELDS),
)

_QUEST_ACTION_CONNECTIONS = {
    1: ("client_action_start", "start"),
    2: ("client_action_succeed", "succeed"),
    4: ("client_action_failed", "failed"),
}

# Current installed MemoryPack formatter evidence maps the compact ActionHeader
# tag 0x85 with 0x13 subtype members to LevelEvent_OnQuestStateChanged. Only
# exact header-list membership is accepted below.
_LEVELSCRIPT_QUEST_STATE_CHANGED_TAG = (0x0085, 0x13)
_LEVELSCRIPT_QUEST_STATE_CHANGED_CONNECTIONS_CACHE: dict[str, list[dict]] | None = None
_LEVELSCRIPT_LEADER_ENTER_TRIGGER_TAG = (0x00BE, 0x12)
_LEVELSCRIPT_WAIT_FOR_CONDITION_OPCODE = (0x04F0, 0x09)
_LEVELSCRIPT_CHECK_QUEST_STATE_TAG = 0x7E
_LEVELSCRIPT_QUEST_STATE_GATE_CONNECTIONS_CACHE: dict[str, list[dict]] | None = None
_LEVELSCRIPT_STORY_PAYLOAD_PREFIXES = (
    "dlg_",
    "misc_dlg_",
    "sns_",
    "cutscene_",
    "black_",
    "remotecomm_",
    "radio_",
)
_LEVELSCRIPT_QUEST_ID_RE = re.compile(r"^[A-Za-z0-9_]+_q#[A-Za-z0-9_#]+$")
_LEVELSCRIPT_STORY_PLAY_CLASSES = {
    "play_cutscene",
    "play_dialog",
    "play_levelseq",
    "play_radio",
}


def _story_ref_kind(key: str) -> str:
    value = str(key or "")
    if value.startswith(("dlg_", "misc_dlg_")):
        return "dialog"
    for prefix, kind in (
        ("sns_", "sns"),
        ("cutscene_", "cutscene"),
        ("black_", "black"),
        ("remotecomm_", "remotecomm"),
        ("radio_", "radio"),
    ):
        if value.startswith(prefix):
            return kind
    return "story"


def _append_story_connection(rows: list[dict], row: dict) -> None:
    key = str(row.get("key") or "").strip()
    if not key:
        return
    row["key"] = key
    signature = (
        key,
        row.get("relation"),
        row.get("phase"),
        row.get("actionSlot"),
        row.get("objectiveIndex"),
        row.get("source"),
    )
    for existing in rows:
        if (
            existing.get("key"),
            existing.get("relation"),
            existing.get("phase"),
            existing.get("actionSlot"),
            existing.get("objectiveIndex"),
            existing.get("source"),
        ) == signature:
            return
    rows.append(row)


def _levelscript_record_texts(record: dict) -> list[str]:
    texts: list[str] = []
    for field_name in ("strings", "plainStrings"):
        for value in record.get(field_name) or []:
            text = str(value.get("text") if isinstance(value, dict) else value).strip()
            if text and text not in texts:
                texts.append(text)
    return texts


def _levelscript_quest_state_changed_event_state(decoded: dict) -> int | None:
    """Return the serialized OnQuestStateChanged filter-state value.

    The generated MemoryPack wrapper deserializes ``_filtedNewState`` before
    ``_filtedQuestId``. In current LevelScript payloads the enum scalar is the
    tagged field at offset 0x1f; current authored playback rows use value 2
    for Processing and value 3 for Completed.
    """
    for field in decoded.get("taggedFields") or []:
        if field.get("offset") == "0x1f" and isinstance(field.get("i32"), int):
            return field["i32"]
    return None


def _unique_levelscript_action_chain(
    action_buckets: dict[int, list[dict]],
    target_id: object,
) -> list[dict]:
    if not isinstance(target_id, int):
        return []
    chain: list[dict] = []
    seen_ids: set[int] = set()
    current_id = target_id
    while len(chain) < 64:
        bucket = action_buckets.get(current_id) or []
        if len(bucket) != 1:
            return []
        record = bucket[0]
        local_id = record.get("localId")
        if not isinstance(local_id, int) or local_id in seen_ids:
            return []
        seen_ids.add(local_id)
        chain.append(record)
        next_id = record.get("nextId")
        if not isinstance(next_id, int):
            return []
        if next_id < 0:
            return chain
        current_id = next_id
    return []


def _levelscript_quest_state_changed_connections_from_file(
    data: bytes,
    records: list[dict],
    *,
    level_id: str,
    script_id: str,
    source_file: str,
) -> dict[str, list[dict]]:
    """Decode exact quest-state event headers and their action chains."""
    out: dict[str, list[dict]] = defaultdict(list)
    if not data or not records:
        return {}
    _action_map, membership = levelscript_action_map_membership(data, records)
    ordered = sorted(records, key=lambda row: int(row.get("start") or 0))
    next_starts = {
        int(record.get("start") or 0): (
            int(ordered[index + 1].get("start") or len(data))
            if index + 1 < len(ordered)
            else len(data)
        )
        for index, record in enumerate(ordered)
    }
    action_buckets: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        local_id = record.get("localId")
        role = str(membership.get(int(record.get("start") or 0)) or "")
        if isinstance(local_id, int) and role.startswith("actionList#"):
            action_buckets[local_id].append(record)

    for header in records:
        if levelscript_record_semantic_key(header) != _LEVELSCRIPT_QUEST_STATE_CHANGED_TAG:
            continue
        start = int(header.get("start") or 0)
        header_role = str(membership.get(start) or "")
        if not header_role.startswith("headerList#"):
            continue
        decoded = decode_levelscript_record_payload(
            data,
            header,
            next_start=next_starts.get(start),
            action_map_role=header_role,
        )
        quest_state = _levelscript_quest_state_changed_event_state(decoded)
        state_semantics = {
            2: ("levelscript_quest_processing_action", "start", "Processing"),
            3: ("levelscript_quest_completed_action", "succeed", "Completed"),
        }.get(quest_state)
        if state_semantics is None:
            continue
        relation, phase, quest_state_name = state_semantics
        quest_ids = [
            text
            for text in _levelscript_record_texts(header)
            if _LEVELSCRIPT_QUEST_ID_RE.fullmatch(text)
        ]
        if len(quest_ids) != 1:
            continue
        action_header = decoded.get("actionHeader") or {}
        chain = _unique_levelscript_action_chain(
            action_buckets,
            action_header.get("nextId"),
        )
        if not chain:
            continue
        quest_id = quest_ids[0]
        action_path_local_ids = [
            int(action["localId"])
            for action in chain
            if isinstance(action.get("localId"), int)
        ]
        for action_path_index, action in enumerate(chain):
            action_class = classify_levelscript_record(action)
            action_name = levelscript_native_action_name(action)
            if action_class not in _LEVELSCRIPT_STORY_PLAY_CLASSES or not action_name:
                continue
            story_keys = _unique_preserve([
                str(hit.get("text") or "").strip()
                for hit in action.get("strings") or []
                if isinstance(hit, dict)
                and str(hit.get("text") or "").strip().startswith(
                    _LEVELSCRIPT_STORY_PAYLOAD_PREFIXES
                )
            ])
            for story_key in story_keys:
                action_local_id = action.get("localId")
                action_code = f"0x{int(action.get('code') or 0):04x}"
                action_kind = f"0x{int(action.get('kind') or 0):02x}"
                _append_story_connection(out[quest_id], {
                    "key": story_key,
                    "kind": _story_ref_kind(story_key),
                    "relation": relation,
                    "direction": "quest_to_story",
                    "phase": phase,
                    "confidence": "native_typed_direct",
                    "source": (
                        f"{source_file} {header_role} LevelEvent_OnQuestStateChanged"
                        f"({quest_state_name}) -> actionList localId {action_local_id}"
                    ),
                    "event": "LevelEvent_OnQuestStateChanged",
                    "questState": quest_state,
                    "questStateName": quest_state_name,
                    "levelId": level_id,
                    "scriptId": script_id,
                    "sourceFile": source_file,
                    "headerLocalId": header.get("localId"),
                    "actionLocalId": action_local_id,
                    "actionPathIndex": action_path_index,
                    "actionPathLocalIds": action_path_local_ids,
                    "actionCode": action_code,
                    "actionKind": action_kind,
                    "actionName": action_name,
                    "nativeMappingId": LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
                })
    return dict(out)


def _levelscript_quest_state_changed_story_connections() -> dict[str, list[dict]]:
    """Build the version-gated quest-state action index once per build."""
    global _LEVELSCRIPT_QUEST_STATE_CHANGED_CONNECTIONS_CACHE
    if _LEVELSCRIPT_QUEST_STATE_CHANGED_CONNECTIONS_CACHE is not None:
        return _LEVELSCRIPT_QUEST_STATE_CHANGED_CONNECTIONS_CACHE
    out: dict[str, list[dict]] = defaultdict(list)
    if LEVELSCRIPT_DIR.is_dir():
        for level_dir in sorted(path for path in LEVELSCRIPT_DIR.iterdir() if path.is_dir()):
            info = _load_levelscript_binding_data(level_dir.name)
            for file_info in info.get("files") or []:
                source_file = str(file_info.get("file") or "")
                records = list(file_info.get("records") or [])
                if not source_file or not any(
                levelscript_record_semantic_key(record)
                    == _LEVELSCRIPT_QUEST_STATE_CHANGED_TAG
                    for record in records
                ):
                    continue
                try:
                    data = read_bytes_cached(ROOT / source_file)
                except OSError:
                    continue
                rows_by_quest = _levelscript_quest_state_changed_connections_from_file(
                    data,
                    records,
                    level_id=level_dir.name,
                    script_id=str(file_info.get("fileStem") or ""),
                    source_file=source_file,
                )
                for quest_id, rows in rows_by_quest.items():
                    for row in rows:
                        _append_story_connection(out[quest_id], row)
    _LEVELSCRIPT_QUEST_STATE_CHANGED_CONNECTIONS_CACHE = dict(out)
    return _LEVELSCRIPT_QUEST_STATE_CHANGED_CONNECTIONS_CACHE


def _levelscript_quest_state_gate_connections_from_file(
    data: bytes,
    records: list[dict],
    *,
    level_id: str,
    script_id: str,
    source_file: str,
) -> dict[str, list[dict]]:
    """Recover trigger -> CheckQuestState(Processing) -> playback gates."""
    out: dict[str, list[dict]] = defaultdict(list)
    if not data or not records:
        return {}
    _action_map, membership = levelscript_action_map_membership(data, records)
    ordered = sorted(records, key=lambda row: int(row.get("start") or 0))
    next_starts = {
        int(record.get("start") or 0): (
            int(ordered[index + 1].get("start") or len(data))
            if index + 1 < len(ordered)
            else len(data)
        )
        for index, record in enumerate(ordered)
    }
    action_buckets: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        local_id = record.get("localId")
        role = str(membership.get(int(record.get("start") or 0)) or "")
        if isinstance(local_id, int) and role.startswith("actionList#"):
            action_buckets[local_id].append(record)

    for header in records:
        if levelscript_record_semantic_key(header) != _LEVELSCRIPT_LEADER_ENTER_TRIGGER_TAG:
            continue
        header_start = int(header.get("start") or 0)
        header_role = str(membership.get(header_start) or "")
        if not header_role.startswith("headerList#"):
            continue
        header_decoded = decode_levelscript_record_payload(
            data,
            header,
            next_start=next_starts.get(header_start),
            action_map_role=header_role,
        )
        chain = _unique_levelscript_action_chain(
            action_buckets,
            (header_decoded.get("actionHeader") or {}).get("nextId"),
        )
        if not chain:
            continue
        for gate_index, gate in enumerate(chain):
            if (gate.get("code"), gate.get("kind")) != _LEVELSCRIPT_WAIT_FOR_CONDITION_OPCODE:
                continue
            gate_start = int(gate.get("start") or 0)
            gate_payload_start = int(gate.get("payloadStart", gate_start) or gate_start)
            gate_next_start = next_starts.get(gate_start)
            if not isinstance(gate_next_start, int) or gate_next_start <= gate_payload_start:
                continue
            gate_payload = data[gate_payload_start:gate_next_start]
            if len(gate_payload) < 2 or gate_payload[0] != _LEVELSCRIPT_CHECK_QUEST_STATE_TAG:
                continue
            gate_role = str(membership.get(gate_start) or "")
            gate_decoded = decode_levelscript_record_payload(
                data,
                gate,
                next_start=gate_next_start,
                action_map_role=gate_role,
            )
            quest_ids = [
                text
                for text in _levelscript_record_texts(gate)
                if _LEVELSCRIPT_QUEST_ID_RE.fullmatch(text)
            ]
            if len(quest_ids) != 1:
                continue
            tagged_fields = list(gate_decoded.get("taggedFields") or [])
            string_positions = [
                index
                for index, field in enumerate(tagged_fields)
                if field.get("type") == "string" and field.get("value") == quest_ids[0]
            ]
            if len(string_positions) != 1:
                continue
            string_position = string_positions[0]
            before_values = [
                field.get("i32")
                for field in tagged_fields[:string_position]
                if isinstance(field.get("i32"), int)
            ]
            after_values = [
                field.get("i32")
                for field in tagged_fields[string_position + 1:]
                if isinstance(field.get("i32"), int)
            ]
            # GameCondition tag 0x7e is CheckQuestState. Comparer 0 is Equal;
            # QuestState 2 is Processing. This is a gate, not a completion
            # callback or a server response.
            if before_values != [0] or after_values != [2]:
                continue
            quest_id = quest_ids[0]
            for action in chain[gate_index + 1:]:
                action_class = classify_levelscript_record(action)
                action_name = levelscript_native_action_name(action)
                if action_class not in _LEVELSCRIPT_STORY_PLAY_CLASSES or not action_name:
                    continue
                story_keys = _unique_preserve([
                    str(hit.get("text") or "").strip()
                    for hit in action.get("strings") or []
                    if isinstance(hit, dict)
                    and str(hit.get("text") or "").strip().startswith(
                        _LEVELSCRIPT_STORY_PAYLOAD_PREFIXES
                    )
                ])
                for story_key in story_keys:
                    _append_story_connection(out[quest_id], {
                        "key": story_key,
                        "kind": _story_ref_kind(story_key),
                        "relation": "levelscript_quest_state_gate",
                        "direction": "context",
                        "phase": "processing_gate",
                        "confidence": "native_typed_gate",
                        "source": (
                            f"{source_file} {header_role} LeaderEnterTriggerVolume -> "
                            f"WaitForCondition CheckQuestState({quest_id} == Processing) -> "
                            f"actionList localId {action.get('localId')}"
                        ),
                        "event": "ScriptEvent_OnLeaderEnterTriggerVolume",
                        "levelId": level_id,
                        "scriptId": script_id,
                        "headerLocalId": header.get("localId"),
                        "gateActionLocalId": gate.get("localId"),
                        "conditionType": "CheckQuestState",
                        "conditionComparer": "Equal",
                        "conditionQuestState": 2,
                        "actionLocalId": action.get("localId"),
                        "actionCode": f"0x{int(action.get('code') or 0):04x}",
                        "actionKind": f"0x{int(action.get('kind') or 0):02x}",
                        "actionName": action_name,
                        "nativeMappingId": LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
                    })
    return dict(out)


def _levelscript_quest_state_gate_story_connections() -> dict[str, list[dict]]:
    global _LEVELSCRIPT_QUEST_STATE_GATE_CONNECTIONS_CACHE
    if _LEVELSCRIPT_QUEST_STATE_GATE_CONNECTIONS_CACHE is not None:
        return _LEVELSCRIPT_QUEST_STATE_GATE_CONNECTIONS_CACHE
    out: dict[str, list[dict]] = defaultdict(list)
    if LEVELSCRIPT_DIR.is_dir():
        for level_dir in sorted(path for path in LEVELSCRIPT_DIR.iterdir() if path.is_dir()):
            info = _load_levelscript_binding_data(level_dir.name)
            for file_info in info.get("files") or []:
                source_file = str(file_info.get("file") or "")
                records = list(file_info.get("records") or [])
                if not source_file or not any(
                levelscript_record_semantic_key(record)
                    == _LEVELSCRIPT_LEADER_ENTER_TRIGGER_TAG
                    for record in records
                ):
                    continue
                try:
                    data = read_bytes_cached(ROOT / source_file)
                except OSError:
                    continue
                for quest_id, rows in _levelscript_quest_state_gate_connections_from_file(
                    data,
                    records,
                    level_id=level_dir.name,
                    script_id=str(file_info.get("fileStem") or ""),
                    source_file=source_file,
                ).items():
                    for row in rows:
                        _append_story_connection(out[quest_id], row)
    _LEVELSCRIPT_QUEST_STATE_GATE_CONNECTIONS_CACHE = dict(out)
    return _LEVELSCRIPT_QUEST_STATE_GATE_CONNECTIONS_CACHE


def _runtime_story_connections(
    node: object,
    *,
    relation: str,
    phase: str,
    source: str,
    objective_index: int | None = None,
) -> list[dict]:
    rows: list[dict] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            condition_type = _condition_short_type(str(value.get("$type") or ""))
            for field_name, kind in _STORY_CONNECTION_FIELDS:
                if field_name not in value:
                    continue
                field_node = {field_name: value.get(field_name)}
                for raw_ref in _extract_ref_strings(field_node, (field_name,)):
                    story_key = (
                        _canonical_cutscene_key(raw_ref) or raw_ref
                        if kind == "cutscene"
                        else raw_ref
                    )
                    row = {
                        "key": story_key,
                        "kind": kind,
                        "relation": relation,
                        "direction": "story_to_quest",
                        "phase": phase,
                        "confidence": "direct",
                        "source": f"{source}.{field_name}",
                    }
                    if objective_index is not None:
                        row["objectiveIndex"] = objective_index
                    if condition_type:
                        row["conditionType"] = condition_type
                    if condition_type == "CheckTalkOptionFinish":
                        finish_ids = list(_walk_field_values(value, "_finishId"))
                        if finish_ids:
                            row["finishId"] = finish_ids[0]
                    _append_story_connection(rows, row)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(node)
    return rows


def _client_action_story_connections(raw: dict) -> dict[str, list[dict]]:
    action_list = (((raw.get("actionMapRaw") or {}).get("dataMap") or {}).get("actionList") or [])
    actions_by_id = {
        action.get("_ID"): action
        for action in action_list
        if isinstance(action, dict) and isinstance(action.get("_ID"), int)
    }
    out: dict[str, list[dict]] = defaultdict(list)
    for index, (key_row, action_id) in enumerate(zip(
        raw.get("clientActionMapKey") or [],
        raw.get("clientActionMapValue") or [],
    )):
        if not isinstance(key_row, dict) or not isinstance(action_id, int):
            continue
        quest_id = str(key_row.get("questId") or "")
        action_slot = key_row.get("action")
        if not quest_id:
            continue
        relation, phase = _QUEST_ACTION_CONNECTIONS.get(
            action_slot,
            ("client_action", "unknown"),
        )
        seen_action_ids: set[int] = set()
        current_id = action_id
        while isinstance(current_id, int) and current_id not in seen_action_ids:
            seen_action_ids.add(current_id)
            action = actions_by_id.get(current_id)
            if not action:
                break
            action_type = _condition_short_type(str(action.get("$type") or "")) or "ClientAction"
            for field_name, kind in _STORY_CONNECTION_FIELDS:
                if field_name not in action:
                    continue
                field_node = {field_name: action.get(field_name)}
                for raw_ref in _extract_ref_strings(field_node, (field_name,)):
                    story_key = (
                        _canonical_cutscene_key(raw_ref) or raw_ref
                        if kind == "cutscene"
                        else raw_ref
                    )
                    _append_story_connection(out[quest_id], {
                        "key": story_key,
                        "kind": kind,
                        "relation": relation,
                        "direction": "quest_to_story",
                        "phase": phase,
                        "confidence": "native_typed_direct",
                        "source": (
                            f"MissionRuntimeAsset.clientActionMapKey[{index}]"
                            f" -> actionMapRaw.actionList[{current_id}].{field_name}"
                        ),
                        "actionSlot": action_slot,
                        "actionId": current_id,
                        "actionType": action_type,
                    })
            next_id = action.get("_nextID")
            if not isinstance(next_id, int) or next_id < 0:
                break
            current_id = next_id
    return dict(out)


def _objective_area_story_connections(objective_anchors: list[dict]) -> list[dict]:
    """Keep exact Story ids embedded in authored mission-area identifiers.

    This is a contextual ownership link, not a claim that entering the area
    directly plays the referenced Story file. The serialized identifier itself
    contains the complete Story key (for example
    ``e1m1_radio_e1m1_3d2``), which is stronger than spatial proximity.
    """
    rows: list[dict] = []
    for anchor in objective_anchors:
        if not isinstance(anchor, dict):
            continue
        objective_index = anchor.get("index")
        mission_area_ids = _unique_preserve([
            str(value)
            for value in anchor.get("missionAreaIds") or []
            if value
        ])
        condition_types = _unique_preserve([
            str(value)
            for value in anchor.get("conditionTypes") or []
            if value
        ])
        for story_key in anchor.get("areaStoryRefs") or []:
            row = {
                "key": str(story_key or ""),
                "kind": _story_ref_kind(str(story_key or "")),
                "relation": "mission_area_story_reference",
                "direction": "context",
                "phase": "progress",
                "confidence": "direct_embedded",
                "source": (
                    "MissionRuntimeAsset.questDic[*].objectiveList"
                    f"[{int(objective_index or 1) - 1}] mission-area identifier"
                ),
            }
            if objective_index is not None:
                row["objectiveIndex"] = objective_index
            if mission_area_ids:
                row["missionAreaIds"] = mission_area_ids
            if condition_types:
                row["conditionTypes"] = condition_types
            _append_story_connection(rows, row)
    return rows


def _objective_tracking_story_connections(
    tracking_hints: list[dict],
) -> list[dict]:
    """Keep exact Story ids authored on typed objective tracking rows.

    ``SnsTrackingInfo.snsDialogId`` binds an SNS conversation to the quest
    objective's tracking configuration. ``SnsTrackingInfo.Execute`` updates
    mission HUD tracking; it is not the SNS playback entry point. This
    relation therefore proves attachment only, with no playback, ownership,
    activation, or ordering claim.
    """
    rows: list[dict] = []
    for hint in tracking_hints:
        if not isinstance(hint, dict):
            continue
        tracking_type = str(hint.get("type") or "")
        story_key = str(hint.get("snsDialogId") or "").strip()
        objective_index = hint.get("objectiveIndex")
        tracking_index = hint.get("trackingIndex")
        if (
            tracking_type != "SnsTrackingInfo"
            or not story_key
            or not isinstance(objective_index, int)
            or isinstance(objective_index, bool)
            or objective_index <= 0
            or not isinstance(tracking_index, int)
            or isinstance(tracking_index, bool)
            or tracking_index < 0
        ):
            continue
        _append_story_connection(rows, {
            "key": story_key,
            "kind": "sns",
            "relation": "objective_tracking_story_reference",
            "direction": "context",
            "phase": "tracking",
            "confidence": "native_typed_context",
            "source": (
                "MissionRuntimeAsset.questDic[*].objectiveList"
                f"[{objective_index - 1}].trackingInfoList"
                f"[{tracking_index}].snsDialogId"
            ),
            "objectiveIndex": objective_index,
            "trackingIndex": tracking_index,
            "trackingType": tracking_type,
            "playback": False,
            "attachmentBoundary": (
                "authored objective tracking attachment only; "
                "SnsTrackingInfo.Execute is not SNS playback"
            ),
            "orderBoundary": (
                "tracking configuration establishes no activation time or "
                "relative Story order"
            ),
        })
    return rows


def _mission_proxy_dialog_ids(mission_id: str, proxy_id: str) -> list[str]:
    if not mission_id or not proxy_id:
        return []
    rows = (_load_npc_proxy_ex().get("data") or {}).get(proxy_id) or []
    dialog_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_mission = str(row.get("missionId") or "")
        # Blank mission ids describe reusable/default proxy rows and do not
        # prove that their dialog belongs to this mission. Quest attachment
        # requires the authored mission id to match exactly.
        if row_mission != mission_id:
            continue
        dialog_id = str(row.get("dialogId") or "")
        if dialog_id and dialog_id not in dialog_ids:
            dialog_ids.append(dialog_id)
    return dialog_ids


def _attach_unique_proxy_dialog_refs(mission_id: str, quests_out: list[dict]) -> None:
    proxy_quest_ids: dict[str, set[str]] = defaultdict(set)
    for quest in quests_out:
        quest_id = quest.get("id") or ""
        for proxy_id in quest.get("proxies") or []:
            if proxy_id and quest_id:
                proxy_quest_ids[proxy_id].add(quest_id)

    for quest in quests_out:
        proxy_dialogs: list[dict] = []
        seen_dialogs = set(quest.get("dialogs") or [])
        for proxy_id in quest.get("proxies") or []:
            if not proxy_id or len(proxy_quest_ids.get(proxy_id) or ()) != 1:
                continue
            dialog_ids = _mission_proxy_dialog_ids(mission_id, proxy_id)
            for dialog_id in dialog_ids:
                if dialog_id in seen_dialogs:
                    continue
                seen_dialogs.add(dialog_id)
                proxy_dialogs.append({
                    "dialogId": dialog_id,
                    "npcProxyId": proxy_id,
                    "missionId": mission_id,
                    "source": "NpcProxyExDataTable.data[*].dialogId",
                })
                connections = quest.setdefault("storyConnections", [])
                _append_story_connection(connections, {
                    "key": dialog_id,
                    "kind": "dialog",
                    "relation": "npc_proxy_ex_attachment",
                    "direction": "context",
                    "phase": "context",
                    "confidence": "scoped_unique",
                    "source": (
                        "NpcProxyExDataTable.data[*] exact missionId + "
                        "unique quest tracking proxy"
                    ),
                    "npcProxyId": proxy_id,
                    "npcProxyMissionId": mission_id,
                })
        if proxy_dialogs:
            quest["proxyDialogs"] = proxy_dialogs


def _mission_accept_story_connections(mission_id: str) -> list[dict]:
    """Recover Story shown by the mission acceptance lifecycle itself."""
    meta_path = MRA_DIR / f"{mission_id}_meta.json"
    if not meta_path.exists():
        return []
    try:
        with meta_path.open(encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    accept_mode = meta.get("acceptMode") or {}
    mode_info = accept_mode.get("modeInfo") or {}
    if not isinstance(mode_info, dict):
        return []
    mode_info_type = _condition_short_type(str(mode_info.get("$type") or ""))
    if accept_mode.get("mode") != 3 or not mode_info_type.endswith("+NPCInfo"):
        return []
    dialog_id = str(mode_info.get("dialogId") or "").strip()
    if not dialog_id:
        return []
    row = {
        "key": dialog_id,
        "kind": "dialog",
        "relation": "mission_accept_dialog",
        "direction": "story_to_mission",
        "phase": "accept",
        "confidence": "native_typed_direct",
        "source": (
            f"MissionRuntimeAsset/{mission_id}_meta.json."
            "acceptMode.modeInfo.dialogId"
        ),
        "acceptMode": accept_mode.get("mode"),
        "acceptModeType": mode_info_type,
    }
    for output_name, source_name in (
        ("npcProxyId", "npcProxyId"),
        ("levelId", "levelId"),
        ("finishId", "finishId"),
    ):
        value = mode_info.get(source_name)
        if value not in (None, ""):
            row[output_name] = value
    return [row]


def load_mission_flow(mission_id: str) -> dict | None:
    """Parse MissionRuntimeAsset/<mission>.json into a compact flow payload.

    Returns None when the asset is missing. Cached — the flow data is
    language-independent, so one parse serves every language bundle.
    """
    if mission_id in _MISSION_FLOW_CACHE:
        return _MISSION_FLOW_CACHE[mission_id]
    path = MRA_DIR / f"{mission_id}.json"
    if not path.exists():
        _MISSION_FLOW_CACHE[mission_id] = None
        return None
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _MISSION_FLOW_CACHE[mission_id] = None
        return None

    quests_out: list[dict] = []
    quest_entries_by_id: dict[str, dict] = {}
    for quest in (raw.get("questDic") or {}).values():
        qid = quest.get("questId")
        if not qid:
            continue
        entry: dict = {
            "id": qid,
            "flowIndex": quest.get("flowIndex", 0),
            "prev": list(quest.get("prevQuestIdList") or []),
        }
        story_connections: list[dict] = []
        for objective_index, objective in enumerate(quest.get("objectiveList") or [], 1):
            if not isinstance(objective, dict):
                continue
            for row in _runtime_story_connections(
                objective.get("condition"),
                relation="objective_condition",
                phase="progress",
                source=f"MissionRuntimeAsset.questDic[*].objectiveList[{objective_index - 1}].condition",
                objective_index=objective_index,
            ):
                _append_story_connection(story_connections, row)
        for row in _runtime_story_connections(
            quest.get("failedCondition"),
            relation="failure_condition",
            phase="failed",
            source="MissionRuntimeAsset.questDic[*].failedCondition",
        ):
            _append_story_connection(story_connections, row)
        if story_connections:
            entry["storyConnections"] = story_connections
        if quest.get("overrideMissionDesc"):
            entry["overrideMissionDescription"] = True
        description_override_key = _mission_text_key(quest.get("descriptionOverride"))
        if description_override_key:
            entry["descriptionOverrideKey"] = description_override_key
        quest_story_node = dict(quest)
        quest_story_node.pop("failedCondition", None)
        dialogs = _extract_ref_strings(quest_story_node, _DIALOG_REF_FIELDS)
        if dialogs:
            entry["dialogs"] = dialogs
        cutscenes = [
            canonical
            for cutscene_id in _extract_ref_strings(quest_story_node, _CUTSCENE_REF_FIELDS)
            if (canonical := _canonical_cutscene_key(cutscene_id))
        ]
        if cutscenes:
            entry["cutscenes"] = _unique_preserve(cutscenes)
        remotecomms = _extract_ref_strings(quest_story_node, _REMOTECOMM_REF_FIELDS)
        if remotecomms:
            entry["remotecomms"] = _unique_preserve(remotecomms)
        radios = _extract_ref_strings(quest_story_node, _RADIO_REF_FIELDS)
        if radios:
            entry["radios"] = _unique_preserve(radios)
        tracking = _extract_tracking_hints(quest)
        if tracking:
            resolved_tracking = [_resolve_tracking_hint(hint) for hint in tracking]
            entry["tracking"] = resolved_tracking
            connections = entry.setdefault("storyConnections", [])
            for row in _objective_tracking_story_connections(resolved_tracking):
                _append_story_connection(connections, row)
            scenes = _unique_preserve(
                [hint["scene"] for hint in resolved_tracking if hint.get("scene")]
            )
            proxies = _unique_preserve(
                [hint["npcProxyId"] for hint in resolved_tracking if hint.get("npcProxyId")]
            )
            if scenes:
                entry["scenes"] = scenes
            if proxies:
                entry["proxies"] = proxies
            pins: list[dict] = []
            seen_pins: set[tuple] = set()
            for hint in resolved_tracking:
                pin = _tracking_hint_pin(hint)
                if not pin:
                    continue
                key = (
                    pin.get("scene", ""),
                    pin.get("sourceType", ""),
                    pin.get("trackingType", ""),
                    pin.get("missionAreaId", ""),
                    pin.get("npcProxyId", ""),
                    round(float(pin["position"]["x"]), 3),
                    round(float(pin["position"]["y"]), 3),
                    round(float(pin["position"]["z"]), 3),
                )
                if key in seen_pins:
                    continue
                seen_pins.add(key)
                pins.append(pin)
            if pins:
                entry["pins"] = pins
        objective_anchors = _extract_objective_anchors(quest)
        if objective_anchors:
            entry["objectiveAnchors"] = objective_anchors
            connections = entry.setdefault("storyConnections", [])
            for row in _objective_area_story_connections(objective_anchors):
                _append_story_connection(connections, row)
        fc = quest.get("failedCondition")
        if fc:
            flags = _extract_branch_flags(fc)
            eval_str = _combine_eval_string(fc)
            fail_story_refs: list[str] = []
            for field_name in (*_DIALOG_REF_FIELDS, *_CUTSCENE_REF_FIELDS, *_REMOTECOMM_REF_FIELDS, *_RADIO_REF_FIELDS):
                for value in _walk_field_values(fc, field_name):
                    if not isinstance(value, str) or not value:
                        continue
                    if field_name in _CUTSCENE_REF_FIELDS:
                        value = _canonical_cutscene_key(value) or value
                    if value not in fail_story_refs:
                        fail_story_refs.append(value)
            if fail_story_refs:
                entry["failStoryRefs"] = fail_story_refs
            if flags or eval_str or fail_story_refs:
                fail_entry: dict = {"flags": flags}
                if eval_str:
                    fail_entry["eval"] = eval_str
                if fail_story_refs:
                    fail_entry["storyRefs"] = fail_story_refs
                entry["fail"] = fail_entry
        quests_out.append(entry)
        quest_entries_by_id[qid] = entry

    radio_actions_by_quest = _extract_client_action_refs(raw, _RADIO_REF_FIELDS)
    for quest_id, radio_ids in radio_actions_by_quest.items():
        entry = quest_entries_by_id.get(quest_id)
        if not entry:
            continue
        entry["radios"] = _unique_preserve([
            *(entry.get("radios") or []),
            *radio_ids,
        ])

    for quest_id, rows in _client_action_story_connections(raw).items():
        entry = quest_entries_by_id.get(quest_id)
        if not entry:
            continue
        connections = entry.setdefault("storyConnections", [])
        for row in rows:
            _append_story_connection(connections, row)

    for quest_id, rows in _levelscript_quest_state_changed_story_connections().items():
        entry = quest_entries_by_id.get(quest_id)
        if not entry:
            continue
        connections = entry.setdefault("storyConnections", [])
        for row in rows:
            _append_story_connection(connections, row)

    for quest_id, rows in _levelscript_quest_state_gate_story_connections().items():
        entry = quest_entries_by_id.get(quest_id)
        if not entry:
            continue
        connections = entry.setdefault("storyConnections", [])
        for row in rows:
            _append_story_connection(connections, row)

    for quest_id, rows in _leveldata_quest_story_refs_for_mission(mission_id).items():
        entry = quest_entries_by_id.get(quest_id)
        if not entry:
            continue
        refs = _unique_preserve(
            str(row.get("storyRef") or "")
            for row in rows
            if row.get("storyRef")
        )
        if not refs:
            continue
        entry["levelDataStoryRefs"] = [
            {
                key: value
                for key, value in row.items()
                if key in (
                    "storyRef",
                    "levelId",
                    "file",
                    "distance",
                    "entity",
                    "fields",
                    "source",
                )
                and value not in (None, "", [], {})
            }
            for row in rows
        ]
        connections = entry.setdefault("storyConnections", [])
        for row in entry["levelDataStoryRefs"]:
            _append_story_connection(connections, {
                "key": row.get("storyRef") or "",
                "kind": "level_data",
                "relation": "leveldata_quest_reference",
                "direction": "context",
                "phase": "context",
                "confidence": "direct",
                "source": row.get("source") or "LevelData quest reference",
                **({"levelId": row["levelId"]} if row.get("levelId") else {}),
                **({"entity": row["entity"]} if row.get("entity") else {}),
                **({"file": row["file"]} if row.get("file") else {}),
            })

    _attach_unique_proxy_dialog_refs(mission_id, quests_out)

    quests_out = _topo_sort_quests(quests_out)

    payload = {
        "level": raw.get("levelId", ""),
        "quests": quests_out,
    }
    mission_story_connections = _mission_accept_story_connections(mission_id)
    if mission_story_connections:
        payload["missionStoryConnections"] = mission_story_connections
    mission_description_key = _mission_text_key(raw.get("missionDescription"))
    if mission_description_key:
        payload["missionDescriptionKey"] = mission_description_key
    _MISSION_FLOW_CACHE[mission_id] = payload
    return payload


__all__ = [name for name in globals() if not name.startswith("__")]
