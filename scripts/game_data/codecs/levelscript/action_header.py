"""Exact codec for the action header prefix and its CallServer contract.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import struct

from scripts.game_data.codecs.levelscript.framing_common import _drop_empty
from typing import Any

CALLSERVER_SERIALIZED_CONTRACT_FIELDS = (
    "payloadShape",
    "callClientOutputUIDs",
    "eventArgsPtr",
    "eventName",
    "eventNameIdentity",
    "callbackCorrelationLabel",
    "useCustomEvent",
    "waitForCallback",
    "withEventArgs",
    "consumedBytes",
    "trailingBytes",
)


def compact_callserver_serialized_contract(
    call_server: dict[str, Any],
) -> dict[str, Any]:
    """Project decoded bytes without derived graph/evidence annotations."""
    if not isinstance(call_server, dict):
        return {}
    return {
        key: call_server[key]
        for key in CALLSERVER_SERIALIZED_CONTRACT_FIELDS
        if key in call_server
    }


def _decode_action_header_prefix(payload: bytes) -> dict[str, Any]:
    """Decode the compact common ActionHeader prefix.

    GameAssembly body recovery shows the MemoryPack wrapper setters store
    ActionHeader fields at runtime offsets include nextID, priority,
    triggerActiveDuring, filterMode, filterLevel, filterMask, and validate.

    In the exported LevelScript blobs observed so far, high ActionHeader rows
    carry a compact 17-byte prefix. The useful playback edge is `_nextID`,
    serialized as a u32 at payload offset +5. The fixed record trailer also
    has a `nextId`-looking integer, but for headerList rows that value often
    points nowhere useful and is not the event-to-action edge.
    """
    if len(payload) < 17:
        return {}
    filter_mask = struct.unpack_from("<i", payload, 0)[0]
    filter_mode = payload[4]
    next_id = struct.unpack_from("<i", payload, 5)[0]
    priority = struct.unpack_from("<i", payload, 9)[0]
    trigger_active_during = struct.unpack_from("<i", payload, 13)[0]
    if filter_mode > 8:
        return {}
    if not (-1 <= next_id <= 0x10000):
        return {}
    if not (-1000 <= filter_mask <= 100000):
        return {}
    if not (-1000 <= priority <= 100000):
        return {}
    if not (-1000 <= trigger_active_during <= 100000):
        return {}
    validate_param: dict[str, Any] = {}
    if len(payload) >= 31 and payload[17] == 0x04 and payload[18] in (0, 1):
        id_ref = struct.unpack_from("<i", payload, 19)[0]
        param_source = struct.unpack_from("<i", payload, 23)[0]
        path_size = struct.unpack_from("<i", payload, 27)[0]
        if path_size == -1 and (
            (id_ref == -1 and param_source == 0)
            or (0 < id_ref <= 0x10000 and param_source == -1)
        ):
            validate_param = {
                "value": bool(payload[18]),
                "idRef": id_ref,
                "paramSource": param_source,
                "path": None,
                "payloadOffset": "0x11",
                "payloadShape": (
                    "action-header-validate-constant"
                    if id_ref == -1
                    else "action-header-validate-local-getter"
                ),
            }
    detail = {
            "payloadShape": "action-header-prefix",
            "filterMask": filter_mask,
            "filterMode": filter_mode,
            "nextId": next_id,
            "priority": priority,
            "triggerActiveDuring": trigger_active_during,
            "nextIdOffset": "0x5",
    }
    if validate_param:
        detail["validateParam"] = validate_param
        if validate_param["payloadShape"] == "action-header-validate-local-getter":
            detail["validateGetterLocalId"] = validate_param["idRef"]
    return _drop_empty(detail)


LEVELSCRIPT_EXACT_GETTER_FIELDS = (
    "booleanCompare",
    "boolGetterAnd",
    "boolGetterInvert",
    "boolGetterMultiAnd",
    "boolGetterOr",
    "checkLevelScriptStage",
    "checkMissionOrQuestIsComplete",
    "compareMissionState",
    "getConditionResult",
    "floatNewCompare",
    "getLevelScriptPropertyGenericBool",
    "getLevelScriptStage",
    "getMissionState",
    "getLsmIsCompleted",
    "getterBool",
    "getterInt",
    "getterString",
    "intCompare",
    "intEqual",
    "intRandom",
    "interactiveCheckState",
    "isEndminGender",
)


def _predicate_local_getter_refs(
    value: Any,
    path: str = "",
) -> list[dict[str, Any]]:
    """Collect explicitly typed local-getter references from exact fields."""
    refs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if (
                isinstance(child, int)
                and (
                    key == "getterLocalId"
                    or key.endswith("GetterLocalId")
                )
            ):
                shorthand_base = key[: -len("GetterLocalId")]
                canonical_operand = value.get(shorthand_base)
                if (
                    shorthand_base
                    and isinstance(canonical_operand, dict)
                    and canonical_operand.get("getterLocalId") == child
                ):
                    continue
                refs.append({"path": child_path, "getterLocalId": child})
            else:
                refs.extend(_predicate_local_getter_refs(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            refs.extend(_predicate_local_getter_refs(child, child_path))
    return refs
