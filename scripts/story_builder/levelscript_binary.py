from __future__ import annotations

import re
import struct
from collections import Counter
from pathlib import Path
from typing import Any


LEVELSCRIPT_START_TYPE_NAMES = {
    0: "ByEnterStartShape",
    1: "Manual",
    2: "SameWithActive",
    3: "Never",
}

LEVELSCRIPT_END_TYPE_NAMES = {
    0: "Auto",
    1: "ByExitStartShape",
    2: "Manual",
    3: "SameWithDeactive",
    4: "Never",
}

SCRIPT_POINTER_REF_RECORDS = {
    (0x0455, 0x0A),
    (0x045D, 0x0A),
}

LEVELSCRIPT_RECORD_HINTS = {
    (0x04BD, 0x09): {
        "label": "candidate-wait-seconds",
        "confidence": "medium",
        "note": "single float-shaped payload; matches WaitForSecondsForMemoryPack _seconds field shape",
    },
    (0x0455, 0x0A): {
        "label": "actionbase-show-scene-decoration-new",
        "confidence": "high",
        "note": (
            "ActionBase formatter tag maps the code to ShowSceneDecorationNew; "
            "some payloads still carry a plausible LevelScriptPtr-like value, "
            "but this is not ManualStart/ManualEnd because no levelId string is serialized"
        ),
    },
    (0x045D, 0x0A): {
        "label": "actionbase-show-ui-toast-dev-only",
        "confidence": "high",
        "note": (
            "ActionBase formatter tag maps the code to ShowUIToast_DevOnly; "
            "some payloads still carry a plausible LevelScriptPtr-like value, "
            "but this is not ManualStart/ManualEnd because no levelId string is serialized"
        ),
    },
    (0x0463, 0x09): {
        "label": "local-record-ref-list",
        "confidence": "medium",
        "note": "compact list of local record ids; likely control-flow/join wiring rather than a playback trigger",
    },
    (0x02EE, 0x09): {
        "label": "guide-prompt",
        "confidence": "medium",
        "note": "payload carries guide_* ids and usually precedes tutorial radio/dialog flow",
    },
    (0x0E34, 0x00): {
        "label": "event-args-continuation",
        "confidence": "low",
        "note": "payload carries event_args plus a UID-like token; exact ScriptEvent class is not proven",
    },
    (0x104A, 0x00): {
        "label": "float-property-signal",
        "confidence": "medium",
        "note": "payload carries a named signal plus an auto-named _floatValue property",
    },
    (0x03B8, 0x0A): {
        "label": "actionbase-set-bool",
        "confidence": "high",
        "note": (
            "ActionBase formatter tag maps the code to SetBool; payload carries "
            "a property key plus bool-shaped value fields"
        ),
        "propertyRole": "property-setter",
        "propertyValueType": "bool",
        "actionBaseAction": "SetBool",
    },
    (0x03E7, 0x0A): {
        "label": "actionbase-set-int",
        "confidence": "high",
        "note": (
            "ActionBase formatter tag maps the code to SetInt; payload carries "
            "a property key plus int-shaped value fields"
        ),
        "propertyRole": "property-setter",
        "propertyValueType": "int",
        "actionBaseAction": "SetInt",
    },
    (0x03EA, 0x0A): {
        "label": "actionbase-set-int-increase",
        "confidence": "high",
        "note": (
            "ActionBase formatter tag maps the code to SetIntIncrease; payload carries "
            "a property key plus increment-shaped value fields"
        ),
        "propertyRole": "property-setter",
        "propertyValueType": "int-increase",
        "actionBaseAction": "SetIntIncrease",
    },
    (0x0176, 0x08): {
        "label": "actionbase-list-clear-float",
        "confidence": "medium",
        "note": (
            "ActionBase formatter tag maps the code to ListClear<float>; payload carries "
            "a property key/list target, so this is not setter proof"
        ),
        "propertyRole": "property-list-clear",
        "propertyValueType": "float-list",
        "actionBaseAction": "ListClear<float>",
    },
    (0x02EC, 0x0A): {
        "label": "actionbase-manual-end-levelscript",
        "confidence": "high",
        "note": (
            "ActionBase formatter tag maps the code to ManualEndLevelScript; observed "
            "payloads carry default/parameterized operands, not literal levelId+scriptId "
            "targets, so use adjacent trigger-event structure as activation evidence"
        ),
        "levelScriptControlRole": "manual-end",
        "actionBaseAction": "ManualEndLevelScript",
    },
    (0x02F1, 0x0A): {
        "label": "actionbase-manual-start-levelscript",
        "confidence": "high",
        "note": (
            "ActionBase formatter tag maps the code to ManualStartLevelScript; observed "
            "payloads carry default/parameterized operands, not literal levelId+scriptId "
            "targets, so use adjacent trigger-event structure as activation evidence"
        ),
        "levelScriptControlRole": "manual-start",
        "actionBaseAction": "ManualStartLevelScript",
    },
    (0x0A03, 0x00): {
        "label": "property-key-gate",
        "confidence": "medium",
        "note": (
            "compact condition/gate payload carries a property key, type code, post flag, "
            "and sometimes a tail local action ref; this code is outside all extracted "
            "MemoryPack union formatter tag ranges, so treat it as a gate/read shape until "
            "its non-union runtime family is decoded"
        ),
        "propertyRole": "property-key-gate",
    },
    (0x0BED, 0x00): {
        "label": "property-key-terminal-branch",
        "confidence": "medium",
        "note": (
            "payload carries a bool/scalar-looking prefix and a property key on a terminal-looking "
            "record, with tail integers that resolve to local record ids in observed scripts; it is "
            "outside all extracted MemoryPack union formatter tag ranges, so it remains a compact "
            "terminal/completion branch bridge rather than generic Set<bool> proof"
        ),
        "propertyRole": "property-key-terminal",
    },
    (0x13A5, 0x00): {
        "label": "script-event-on-property-changed",
        "confidence": "high",
        "note": (
            "derived ScriptEventHeader mapping: 0x13a5 = 0x139e + tag 0x0007 "
            "ScriptEvent_OnPropertyChanged; payload carries a property key plus "
            "$local@_oldValue/$local@_value outputs, not a property setter"
        ),
        "propertyRole": "property-change-event",
        "propertyEventKind": "changed",
    },
    (0x094C, 0x00): {
        "label": "property-key-control",
        "confidence": "low",
        "note": "payload carries a property key near control records; exact role is not named",
        "propertyRole": "property-key-control",
    },
    (0x094D, 0x00): {
        "label": "property-key-control",
        "confidence": "low",
        "note": "payload carries a property key near control records; exact role is not named",
        "propertyRole": "property-key-control",
    },
    (0x12A0, 0x00): {
        "label": "script-event-on-custom-event",
        "confidence": "high",
        "note": (
            "derived ScriptEventHeader mapping: 0x12a0 = 0x129e + tag 0x0002 "
            "ScriptEvent_OnCustomEvent; payload often carries event uid or custom event key text"
        ),
    },
    (0x12A1, 0x00): {
        "label": "script-event-on-leader-enter-trigger-volume",
        "confidence": "high",
        "note": (
            "derived ScriptEventHeader mapping: 0x12a1 = 0x129e + tag 0x0003 "
            "ScriptEvent_OnLeaderEnterTriggerVolume; event wiring, not script-start proof by itself"
        ),
        "triggerRole": "trigger-volume-event",
        "triggerEventKind": "enter",
    },
    (0x12A3, 0x00): {
        "label": "script-event-on-leader-leave-trigger-volume",
        "confidence": "high",
        "note": (
            "derived ScriptEventHeader mapping: 0x12a3 = 0x129e + tag 0x0005 "
            "ScriptEvent_OnLeaderLeaveTriggerVolume; event wiring, not script-start proof by itself"
        ),
        "triggerRole": "trigger-volume-event",
        "triggerEventKind": "leave",
    },
    (0x12AC, 0x00): {
        "label": "script-event-on-script-stage-changed",
        "confidence": "high",
        "note": (
            "derived ScriptEventHeader mapping: 0x12ac = 0x129e + tag 0x000e "
            "ScriptEvent_OnScriptStageChanged"
        ),
    },
    (0x12AF, 0x00): {
        "label": "script-event-on-start-script-controlled-char-mode",
        "confidence": "high",
        "note": (
            "derived ScriptEventHeader mapping: 0x12af = 0x129e + tag 0x0011 "
            "ScriptEvent_OnStartScriptControlledCharMode"
        ),
    },
    (0x139F, 0x00): {
        "label": "script-event-on-bb-variable-changed",
        "confidence": "high",
        "note": (
            "derived ScriptEventHeader mapping: 0x139f = 0x139e + tag 0x0001 "
            "ScriptEvent_OnBBVariableChanged"
        ),
        "propertyRole": "property-change-event",
        "propertyEventKind": "blackboard-variable-changed",
    },
    (0x0A14, 0x00): {
        "label": "trigger-volume-slot-gate",
        "confidence": "low",
        "note": "payload carries trigger-volume slot ids in a scalar gate/control record",
    },
    (0x012F, 0x07): {
        "label": "trigger-volume-slot-control",
        "confidence": "low",
        "note": "payload carries trigger-volume slot ids near trigger-volume event/check records",
    },
    (0x09C5, 0x00): {
        "label": "trigger-volume-slot-control",
        "confidence": "low",
        "note": "payload carries trigger-volume slot ids near trigger-volume event/check records",
    },
    (0x1093, 0x00): {
        "label": "trigger-volume-entity-output",
        "confidence": "low",
        "note": "payload carries trigger-volume slot ids and entity/instance output refs in some scripts",
    },
    (0x107B, 0x00): {
        "label": "trigger-volume-related-control",
        "confidence": "low",
        "note": "payload may carry trigger-volume slot ids inside a larger control/event record",
    },
    (0x10A6, 0x00): {
        "label": "trigger-volume-related-control",
        "confidence": "low",
        "note": "payload appears near trigger-volume event records; exact role is not named",
    },
    (0x0362, 0x0A): {
        "label": "named-signal",
        "confidence": "low",
        "note": "payload carries authored signal/key text used around levelseq/cutscene control",
    },
    (0x092A, 0x00): {
        "label": "boolean-or-flag-check",
        "confidence": "low",
        "note": "single scalar/flag-shaped payload; exact condition class is not named",
    },
    (0x093E, 0x00): {
        "label": "boolean-or-flag-check",
        "confidence": "low",
        "note": "single scalar/flag-shaped payload; exact condition class is not named",
    },
    (0x0B20, 0x00): {
        "label": "multi-scalar-control",
        "confidence": "low",
        "note": "three scalar fields observed near play/control chains; exact class is not named",
    },
    (0x04B8, 0x09): {
        "label": "uid-keyed-control",
        "confidence": "low",
        "note": "payload carries a short uid/key string; exact class is not named",
    },
    (0x1280, 0x00): {
        "label": "branch-or-state-control",
        "confidence": "low",
        "note": "payload carries numeric state text and optional authored key; exact class is not named",
    },
}

PROPERTY_OUTPUT_RE = re.compile(r"^\$(?P<local>\d+)@_(?P<name>oldValue|value|result|floatValue|entityOutput|instKeyOutput)$")
NOISY_PROPERTY_PREFIXES = (
    "$",
    "#",
    "dlg_",
    "sns_",
    "cutscene_",
    "black_",
    "remotecomm_",
    "radio_",
    "misc_dlg_",
    "levelseq_",
    "guide_",
    "au_",
    "chr_",
    "skill_",
    "LD/",
)
NOISY_PROPERTY_TEXT = {
    "event_args",
    "blackboard",
    "PLAY_SEQ",
}
TRIGGER_VOLUME_RECORD_KEYS = {
    key
    for key, hint in LEVELSCRIPT_RECORD_HINTS.items()
    if str(hint.get("label") or "").startswith("trigger-volume")
    or str(hint.get("triggerRole") or "").startswith("trigger-volume")
}

COMPACT_NULL_SENTINEL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"

LEVELSCRIPT_SHAPE_TYPE_NAMES = {
    0: "None",
    1: "BOX",
    2: "SPHERE",
}

LEVELSCRIPT_TRIGGER_VOLUME_SHAPE_TYPE_NAMES = {
    0: "None",
    1: "Box",
    2: "Sphere",
    3: "PolyLine",
    4: "Infinite",
}

ACTION_SERIALIZED_MAP_LIST_ORDER = ("actionList", "getterList", "headerList")
ACTION_SERIALIZED_MAP_ORDER_EVIDENCE = (
    "GameAssembly ActionSerializedMapForMemoryPack.Deserialize dispatches "
    "set___actionList__, set___getterList__, then set___headerList__; the "
    "setter bodies write ActionSerializedMap fields at +0x18, +0x20, and "
    "+0x10, and MetadataRegistration resolves those fields as "
    "List<ActionBase>, List<PureGetter>, and List<ActionHeader>. The "
    "physical second/third UID-list blocks match getter/header content "
    "signatures; two-block maps can omit an empty getterList and go straight "
    "to a header-shaped final block, leaving ScriptEventHeader-band rows in "
    "headerList instead of getterList."
)


def _u32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def _i32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<i", data, offset)[0]


def _f32(data: bytes, offset: int) -> float | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<f", data, offset)[0]


def _u64_offsets(data: bytes, value: int) -> list[int]:
    needle = struct.pack("<Q", value)
    offsets: list[int] = []
    start = 0
    while True:
        offset = data.find(needle, start)
        if offset < 0:
            break
        offsets.append(offset)
        start = offset + 1
    return offsets


def _is_plausible_levelscript_id(value: int) -> bool:
    return 1_000_000 <= value <= 999_999_999_999


def _list_status(raw_count: int | None) -> tuple[str, int | None]:
    if raw_count is None:
        return "missing", None
    if raw_count == 0xFFFFFFFF:
        return "null", None
    if raw_count <= 64:
        return "present", raw_count
    return "unknown", raw_count


def _drop_empty(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value not in (None, "", [], {})}


def _offset_hex(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def _round_float(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)


def decode_levelscript_action_map_header(data: bytes) -> dict[str, Any]:
    """Decode the stable header of the top-level LevelScriptData actionMap.

    The first serialized member after the LevelScriptData member count is the
    actionMap. For the exported blobs seen so far, non-empty action maps start
    with `02 03 <u32 count>` followed immediately by that many `actionList`
    records. The remaining `ActionSerializedMap` list boundaries need the UID
    record index, so they are decoded by `decode_levelscript_action_map_lists`.
    """
    if not data:
        return {}
    out: dict[str, Any] = {
        "offset": "0x1",
        "serializedMemberCount": data[0],
    }
    if len(data) >= 7 and data[1] == 0x02 and data[2] == 0x03:
        count = _u32(data, 3)
        out.update({
            "status": "present",
            "recordCount": count,
            "recordStartOffset": 7,
            "recordStartOffsetHex": "0x7",
            "headerHex": data[:7].hex(" "),
        })
        return _drop_empty(out)
    if len(data) >= 3 and data[1] == 0xFF:
        out.update({
            "status": "absent-marker",
            "marker": f"0xff 0x{data[2]:02x}",
            "headerHex": data[:3].hex(" "),
        })
        return _drop_empty(out)
    out.update({
        "status": "unknown",
        "headerHex": data[: min(len(data), 8)].hex(" "),
    })
    return _drop_empty(out)


def _record_start(record: dict[str, Any]) -> int:
    try:
        return int(record.get("start") or 0)
    except (TypeError, ValueError):
        return 0


def _record_local_id(record: dict[str, Any]) -> int | None:
    value = record.get("localId")
    return value if isinstance(value, int) else None


def _small_uid_list_count(value: int | None, remaining_records: int) -> bool:
    return (
        isinstance(value, int)
        and value != 0xFFFFFFFF
        and 0 <= value <= 10_000
        and (remaining_records <= 0 or value <= remaining_records)
    )


def _levelscript_header_list_like_record(record: dict[str, Any]) -> bool:
    code = record.get("code")
    kind = record.get("kind")
    return (
        isinstance(code, int)
        and isinstance(kind, int)
        and kind == 0x00
        and 0x0E00 <= code <= 0x18FF
    )


def _levelscript_getter_list_like_record(record: dict[str, Any]) -> bool:
    code = record.get("code")
    kind = record.get("kind")
    if not isinstance(code, int) or not isinstance(kind, int):
        return False
    if (code, kind) == (0x0A03, 0x00):
        return True
    return kind in {0x07, 0x08, 0x09, 0x0A} and code <= 0x0446


def _block_looks_like_header_list(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    getter_like = sum(1 for record in records if _levelscript_getter_list_like_record(record))
    if getter_like:
        return False
    header_like = sum(1 for record in records if _levelscript_header_list_like_record(record))
    return header_like / len(records) >= 0.75


def _block_looks_like_levelscript_tail(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    outside_like = 0
    for record in records:
        code = record.get("code")
        kind = record.get("kind")
        if isinstance(code, int) and isinstance(kind, int) and (
            (code, kind) == (0x0000, 0x00) or code < 0x0100
        ):
            outside_like += 1
    return outside_like / len(records) >= 0.5


def _next_uid_block_relation(
    data: bytes,
    records: list[dict[str, Any]],
    index: int,
) -> str:
    record_count = len(records)
    if index >= record_count:
        return "none"
    marker_offset = _record_start(records[index]) - 4
    marker_value = _u32(data, marker_offset)
    remaining = record_count - index
    if not _small_uid_list_count(marker_value, remaining):
        return "invalid-marker"
    block = records[index : index + int(marker_value)]
    if _block_looks_like_header_list(block) or any(
        _levelscript_getter_list_like_record(record) for record in block
    ):
        return "action-map-like"
    if _block_looks_like_levelscript_tail(block):
        return "levelscript-tail-like"
    return "unknown-block"


def decode_levelscript_action_map_lists(
    data: bytes,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Decode the three `ActionSerializedMap` list boundaries.

    IL2CPP metadata names the runtime fields as `headerList`, `actionList`,
    and `getterList`. GameAssembly body recovery dispatches the generated
    wrapper setters as `actionList`, `getterList`, then `headerList`, and
    MetadataRegistration resolves those fields to `List<ActionBase>`,
    `List<PureGetter>`, and `List<ActionHeader>`. The compact LevelScript
    blobs follow the same physical order: the first count is in the actionMap
    header, and later counts sit immediately before the next UID record. Some
    two-block blobs omit an empty getter block and put a final header-shaped
    block after actionList; those are labeled as `headerList` by a conservative
    content check.
    """
    header = decode_levelscript_action_map_header(data)
    if not header:
        return {}
    out = dict(header)
    out["serializedListOrder"] = list(ACTION_SERIALIZED_MAP_LIST_ORDER)
    out["serializedListOrderEvidence"] = ACTION_SERIALIZED_MAP_ORDER_EVIDENCE
    if header.get("status") != "present":
        return _drop_empty(out)

    first_count = header.get("recordCount")
    if not isinstance(first_count, int) or first_count < 0:
        return _drop_empty(out)

    sorted_records = sorted(records or [], key=_record_start)
    record_count = len(sorted_records)
    lists: list[dict[str, Any]] = []

    def append_list(
        name: str,
        *,
        count: int | None,
        marker_offset: int | None,
        marker_value: int | None,
        start_index: int,
        source: str,
        status: str = "present",
    ) -> int:
        end_index = start_index
        if isinstance(count, int) and count >= 0:
            end_index = min(record_count, start_index + count)
        row: dict[str, Any] = {
            "name": name,
            "status": status,
            "count": count,
            "countOffset": _offset_hex(marker_offset),
            "countMarker": marker_value,
            "recordIndexStart": start_index,
            "recordIndexEnd": end_index,
            "decodedRecordCount": max(0, end_index - start_index),
            "source": source,
        }
        if isinstance(count, int) and record_count and start_index + count > record_count:
            row["status"] = "count-exceeds-decoded-records"
        lists.append(_drop_empty(row))
        return end_index

    index = append_list(
        "actionList",
        count=first_count,
        marker_offset=3,
        marker_value=first_count,
        start_index=0,
        source="actionMapHeader",
    )

    for name in ACTION_SERIALIZED_MAP_LIST_ORDER[1:]:
        if not sorted_records:
            lists.append({
                "name": name,
                "status": "records-not-provided",
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            continue
        if index >= record_count:
            lists.append({
                "name": name,
                "status": "no-decoded-records-after-previous-list",
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            continue
        marker_offset = _record_start(sorted_records[index]) - 4
        marker_value = _u32(data, marker_offset)
        remaining = record_count - index
        if marker_value == 0xFFFFFFFF:
            lists.append({
                "name": name,
                "status": "null-marker-or-unanchored",
                "countOffset": _offset_hex(marker_offset),
                "countMarker": marker_value,
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            break
        if not _small_uid_list_count(marker_value, remaining):
            lists.append({
                "name": name,
                "status": "unknown-marker",
                "countOffset": _offset_hex(marker_offset),
                "countMarker": marker_value,
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            break
        if (
            name == "getterList"
            and _block_looks_like_header_list(sorted_records[index : index + int(marker_value)])
            and _next_uid_block_relation(
                data,
                sorted_records,
                index + int(marker_value),
            )
            in {"none", "invalid-marker", "levelscript-tail-like"}
        ):
            lists.append({
                "name": "getterList",
                "status": "omitted-or-empty-before-headerList",
                "count": 0,
                "recordIndexStart": index,
                "recordIndexEnd": index,
                "decodedRecordCount": 0,
                "source": "inferredEmptyFromFinalHeaderLikeBlock",
            })
            index = append_list(
                "headerList",
                count=int(marker_value),
                marker_offset=marker_offset,
                marker_value=marker_value,
                start_index=index,
                source="uidBoundaryMarkerInferredHeaderList",
            )
            break
        index = append_list(
            name,
            count=int(marker_value),
            marker_offset=marker_offset,
            marker_value=marker_value,
            start_index=index,
            source="uidBoundaryMarker",
        )

    if record_count and index < record_count:
        lists.append({
            "name": "outsideSerializedActionMap",
            "status": "residual-uid-records",
            "count": record_count - index,
            "recordIndexStart": index,
            "recordIndexEnd": record_count,
        })

    out["serializedLists"] = lists
    out["listCounts"] = {
        str(row.get("name")): row.get("count")
        for row in lists
        if row.get("name") in ACTION_SERIALIZED_MAP_LIST_ORDER
    }
    return _drop_empty(out)


def levelscript_action_map_membership(
    data: bytes,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[int, str]]:
    """Return serialized action-map membership labels keyed by record start."""
    action_map = decode_levelscript_action_map_lists(data, records)
    sorted_records = sorted(records or [], key=_record_start)
    memberships: dict[int, str] = {}
    for list_info in action_map.get("serializedLists") or []:
        name = str(list_info.get("name") or "")
        if name not in ACTION_SERIALIZED_MAP_LIST_ORDER:
            continue
        start_index = int(list_info.get("recordIndexStart") or 0)
        end_index = int(list_info.get("recordIndexEnd") or start_index)
        list_records = sorted_records[start_index:end_index]
        linked_starts: set[int] = set()
        if name == "actionList":
            by_local_id: dict[int, list[dict[str, Any]]] = {}
            for record in list_records:
                local_id = _record_local_id(record)
                if local_id is not None:
                    by_local_id.setdefault(local_id, []).append(record)
            unique_targets = {
                local_id: bucket[0]
                for local_id, bucket in by_local_id.items()
                if len(bucket) == 1
            }
            linked_starts = {
                _record_start(target)
                for record in list_records
                if (target := unique_targets.get(record.get("nextId"))) is not None
            }
        for rel_index, record in enumerate(list_records, start=1):
            start = _record_start(record)
            label = f"{name}#{rel_index}"
            if name == "actionList":
                role = "linked" if start in linked_starts else "root"
                label = f"{label} {role}"
            memberships[start] = label
    return action_map, memberships


def _read_vector2(data: bytes, offset: int) -> tuple[dict[str, float] | None, int | None]:
    if offset < 0 or offset + 8 > len(data):
        return None, None
    return (
        {
            "x": _round_float(_f32(data, offset)),
            "y": _round_float(_f32(data, offset + 4)),
        },
        offset + 8,
    )


def _read_vector3(data: bytes, offset: int) -> tuple[dict[str, float] | None, int | None]:
    if offset < 0 or offset + 12 > len(data):
        return None, None
    return (
        {
            "x": _round_float(_f32(data, offset)),
            "y": _round_float(_f32(data, offset + 4)),
            "z": _round_float(_f32(data, offset + 8)),
        },
        offset + 12,
    )


def _decode_levelscript_shape(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int | None]:
    """Decode `Beyond.Gameplay.Core.LevelScriptShape`.

    The field order is verified from the MemoryPack setter order:
    eulerAngles, offset, radius, size, type. The object starts with a compact
    one-byte member count in these exported blobs.
    """
    if offset < 0 or offset + 45 > len(data):
        return None, None
    member_count = data[offset]
    cursor = offset + 1
    euler_angles, cursor = _read_vector3(data, cursor)
    if cursor is None:
        return None, None
    shape_offset, cursor = _read_vector3(data, cursor)
    if cursor is None:
        return None, None
    radius = _f32(data, cursor)
    cursor += 4
    size, cursor = _read_vector3(data, cursor)
    if cursor is None:
        return None, None
    shape_type_raw = _u32(data, cursor)
    cursor += 4
    return (
        _drop_empty(
            {
                "offset": _offset_hex(offset),
                "memberCount": member_count,
                "typeRaw": shape_type_raw,
                "type": LEVELSCRIPT_SHAPE_TYPE_NAMES.get(
                    shape_type_raw if shape_type_raw is not None else -1,
                    "",
                ),
                "position": shape_offset,
                "eulerAngles": euler_angles,
                "size": size,
                "radius": _round_float(radius),
            }
        ),
        cursor,
    )


def _decode_levelscript_shape_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 64,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None

    shapes: list[dict[str, Any]] = []
    for _ in range(count):
        shape, cursor = _decode_levelscript_shape(data, cursor)
        if shape is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["shapes"] = shapes
            return _drop_empty(out), None
        shapes.append(shape)
    out["parseStatus"] = "decoded"
    out["shapes"] = shapes
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _decode_vector2_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None

    points: list[dict[str, float]] = []
    for _ in range(count):
        point, cursor = _read_vector2(data, cursor)
        if point is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["points"] = points
            return _drop_empty(out), None
        points.append(point)
    out["parseStatus"] = "decoded"
    out["points"] = points
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _decode_vector3_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None

    points: list[dict[str, float]] = []
    for _ in range(count):
        point, cursor = _read_vector3(data, cursor)
        if point is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["points"] = points
            return _drop_empty(out), None
        points.append(point)
    out["parseStatus"] = "decoded"
    out["points"] = points
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _decode_trigger_volume_shape(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int | None]:
    """Decode `Beyond.Gameplay.LevelScriptTriggerVolumeShapeData`."""
    if offset < 0 or offset + 1 > len(data):
        return None, None
    member_count = data[offset]
    cursor = offset + 1
    poly_line_points, cursor = _decode_vector2_list(data, cursor)
    if cursor is None:
        return None, None
    position, cursor = _read_vector3(data, cursor)
    if position is None or cursor is None:
        return None, None
    radius = _f32(data, cursor)
    cursor += 4
    rotation, cursor = _read_vector3(data, cursor)
    if rotation is None or cursor is None:
        return None, None
    shape_type_raw = _u32(data, cursor)
    cursor += 4
    size, cursor = _read_vector3(data, cursor)
    if size is None or cursor is None:
        return None, None
    return (
        _drop_empty(
            {
                "offset": _offset_hex(offset),
                "memberCount": member_count,
                "shapeTypeRaw": shape_type_raw,
                "shapeType": LEVELSCRIPT_TRIGGER_VOLUME_SHAPE_TYPE_NAMES.get(
                    shape_type_raw if shape_type_raw is not None else -1,
                    "",
                ),
                "position": position,
                "radius": _round_float(radius),
                "rotation": rotation,
                "size": size,
                "polyLinePoints": poly_line_points,
            }
        ),
        cursor,
    )


def _decode_trigger_volume_shape_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None

    shapes: list[dict[str, Any]] = []
    for _ in range(count):
        shape, cursor = _decode_trigger_volume_shape(data, cursor)
        if shape is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["shapes"] = shapes
            return _drop_empty(out), None
        shapes.append(shape)
    out["parseStatus"] = "decoded"
    out["shapes"] = shapes
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _decode_trigger_volume_entry(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int | None]:
    """Decode one keyed `LevelScriptTriggerVolumeData` map entry."""
    if offset < 0 or offset + 5 > len(data):
        return None, None
    key_slot_id = _u32(data, offset)
    member_count = data[offset + 4]
    cursor = offset + 5
    if cursor + 6 > len(data):
        return None, None
    enter_check_on_ground = bool(data[cursor])
    cursor += 1
    exit_shape_start_index = _i32(data, cursor)
    cursor += 4
    is_important = bool(data[cursor])
    cursor += 1
    shape_list, cursor = _decode_trigger_volume_shape_list(data, cursor)
    if cursor is None or cursor + 10 > len(data):
        return None, None
    slot_id = _u32(data, cursor)
    cursor += 4
    trigger_count_limit = _i32(data, cursor)
    cursor += 4
    trigger_on_pole = bool(data[cursor])
    cursor += 1
    wait_srv_res = bool(data[cursor])
    cursor += 1
    return (
        _drop_empty(
            {
                "offset": _offset_hex(offset),
                "keySlotId": key_slot_id,
                "memberCount": member_count,
                "enterCheckOnGround": enter_check_on_ground,
                "exitShapeStartIndex": exit_shape_start_index,
                "isImportant": is_important,
                "shapeList": shape_list,
                "slotId": slot_id,
                "triggerCountLimit": trigger_count_limit,
                "triggerOnPole": trigger_on_pole,
                "waitSrvRes": wait_srv_res,
            }
        ),
        cursor,
    )



TRIGGER_VOLUME_WRAPPER_PROLOGUE = bytes.fromhex(
    "00 00 00 00 00 00 00 00 00 00 00 00 00 "
    "ff ff ff ff ea 03 00 00 ff ff ff ff "
    "01 00 00 00 00 00 00 00 00 00"
)


def _decode_trigger_volume_map(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    wrapper_end = offset + 4 + len(TRIGGER_VOLUME_WRAPPER_PROLOGUE)
    if (
        raw_count == 4
        and wrapper_end + 4 <= len(data)
        and data[offset + 4:wrapper_end] == TRIGGER_VOLUME_WRAPPER_PROLOGUE
    ):
        inner, inner_cursor = _decode_trigger_volume_map(data, wrapper_end, max_count=max_count)
        if inner_cursor == len(data) and inner.get("status") == "present":
            wrapped = dict(inner)
            wrapped.update({
                "offset": _offset_hex(offset),
                "encoding": "wrapped-trigger-volume-map",
                "wrapperOffset": _offset_hex(offset),
                "wrapperBytes": 4 + len(TRIGGER_VOLUME_WRAPPER_PROLOGUE),
                "wrapperOuterCount": raw_count,
                "wrapperPrologueBytes": len(TRIGGER_VOLUME_WRAPPER_PROLOGUE),
                "innerMapOffset": _offset_hex(wrapper_end),
                "endOffset": _offset_hex(inner_cursor),
            })
            wrapped.setdefault("parseStatus", "decoded")
            return _drop_empty(wrapped), inner_cursor

    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None
    min_entry_bytes = 25
    minimum_bytes_required = count * min_entry_bytes
    remaining_bytes = max(0, len(data) - cursor)
    if minimum_bytes_required > remaining_bytes:
        out["parseStatus"] = "count-exceeds-remaining"
        out["remainingBytes"] = remaining_bytes
        out["minimumBytesRequired"] = minimum_bytes_required
        return _drop_empty(out), None

    volumes: list[dict[str, Any]] = []
    for _ in range(count):
        volume, cursor = _decode_trigger_volume_entry(data, cursor)
        if volume is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["volumes"] = volumes
            return _drop_empty(out), None
        volumes.append(volume)
    out["parseStatus"] = "decoded"
    out["slotIds"] = [row.get("slotId") for row in volumes if row.get("slotId") is not None]
    out["volumes"] = volumes
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def decode_script_pointer_payload(
    data: bytes,
    record: dict[str, Any] | None,
    *,
    target_offset: int | None = None,
) -> dict[str, Any]:
    """Decode the compact script-pointer payload found in LevelScript records.

    This decodes bytes only. The flag byte is not yet mapped to start/end
    semantics, so callers must keep it diagnostic.
    """
    if not data or not record:
        return {}
    code = record.get("code")
    kind = record.get("kind")
    if not isinstance(code, int) or not isinstance(kind, int):
        return {}
    if (code, kind) not in SCRIPT_POINTER_REF_RECORDS:
        return {}
    payload_start = int(record.get("payloadStart", record.get("start", 0)) or 0)
    if payload_start < 0 or payload_start + 9 > len(data):
        return {}
    if data[payload_start] != 0x04:
        return {}

    pointer_script = struct.unpack_from("<Q", data, payload_start + 1)[0]
    if not _is_plausible_levelscript_id(pointer_script):
        return {}
    pointer_offset = payload_start + 1
    flag_offset: int | None = None
    pointer_flag: int | None = None
    if payload_start + 23 <= len(data) and data[payload_start + 21] == 0x04:
        raw_flag = data[payload_start + 22]
        if raw_flag in (0, 1):
            pointer_flag = raw_flag
            flag_offset = payload_start + 22

    sentinel_shape = False
    if payload_start + 35 <= len(data):
        sentinel_shape = (
            data[payload_start + 9 : payload_start + 21]
            == b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
            and data[payload_start + 23 : payload_start + 35]
            == b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        )

    return _drop_empty(
        {
            "pointerScript": str(pointer_script),
            "pointerScriptOffset": pointer_offset,
            "pointerPayloadStart": payload_start,
            "pointerTargetMatches": (
                target_offset is None or int(target_offset) == pointer_offset
            ),
            "pointerFlag": pointer_flag,
            "pointerFlagOffset": flag_offset,
            "pointerPayloadShape": (
                "tagged-u64+tagged-flag+sentinels"
                if sentinel_shape and pointer_flag is not None
                else "tagged-u64"
            ),
        }
    )


def _is_printable_ascii(blob: bytes) -> bool:
    return all(0x20 <= byte <= 0x7E for byte in blob)


LEVELSCRIPT_HEX_UID_RE = re.compile(rb"[0-9a-f]{8}")


def _extract_levelscript_tagged_ascii_strings(
    data: bytes,
    tag: int = 0x04,
    *,
    max_len: int = 120,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    end = len(data) - 5
    i = 0
    while i < end:
        if data[i] != tag:
            i += 1
            continue
        size = struct.unpack_from("<I", data, i + 1)[0]
        if size <= 0 or size > max_len or i + 5 + size > len(data):
            i += 1
            continue
        raw = data[i + 5 : i + 5 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({"offset": i, "text": text})
        i += 5 + size
    return hits


def _extract_levelscript_plain_ascii_strings(
    data: bytes,
    *,
    min_len: int = 3,
    max_len: int = 120,
    tagged_offsets: set[int] | None = None,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    tagged_offsets = tagged_offsets or set()
    end = len(data) - 4
    i = 0
    while i < end:
        size = struct.unpack_from("<I", data, i)[0]
        if size < min_len or size > max_len or i + 4 + size > len(data):
            i += 1
            continue
        if i > 0 and data[i - 1] == 0x04 and (i - 1) in tagged_offsets:
            i += 4 + size
            continue
        raw = data[i + 4 : i + 4 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({"offset": i, "payloadOffset": i + 4, "text": text})
        i += 4 + size
    return hits


def _decode_levelscript_uid_record(data: bytes, uid_off: int, uid: str) -> dict[str, Any] | None:
    if uid_off >= 14:
        start = uid_off - 14
        if start + 32 <= len(data):
            if (
                data[start] == 0xFA
                and data[start + 4] == 0
                and data[start + 9] == 0
                and _u32(data, start + 10) == 8
            ):
                local_id = _u32(data, start + 5)
                if isinstance(local_id, int) and local_id <= 0x1000:
                    return {
                        "start": start,
                        "layout": "fa",
                        "code": struct.unpack_from("<H", data, start + 1)[0],
                        "kind": data[start + 3],
                        "localId": local_id,
                        "uid": uid,
                        "nextId": _i32(data, start + 28),
                        "payloadStart": start + 32,
                        "strings": [],
                        "plainStrings": [],
                    }

    if uid_off >= 12:
        start = uid_off - 12
        if start + 30 <= len(data):
            code = struct.unpack_from("<H", data, start)[0]
            kind = data[start + 2]
            local_id = _u32(data, start + 3)
            if (
                isinstance(local_id, int)
                and code <= 0x1FFF
                and kind <= 0x10
                and local_id <= 0x1000
                and data[start + 7] == 0
                and _u32(data, start + 8) == 8
            ):
                return {
                    "start": start,
                    "layout": "plain",
                    "code": code,
                    "kind": kind,
                    "localId": local_id,
                    "uid": uid,
                    "nextId": _i32(data, start + 26),
                    "payloadStart": start + 30,
                    "strings": [],
                    "plainStrings": [],
                }

    return None


def extract_levelscript_uid_records(
    data: bytes,
    tagged_strings: list[dict[str, Any]] | None = None,
    plain_strings: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_starts: set[int] = set()
    tagged_strings = sorted(tagged_strings or [], key=lambda hit: int(hit.get("offset") or 0))
    plain_strings = sorted(plain_strings or [], key=lambda hit: int(hit.get("offset") or 0))

    for match in LEVELSCRIPT_HEX_UID_RE.finditer(data):
        uid_off = match.start()
        uid = match.group().decode("ascii")
        record = _decode_levelscript_uid_record(data, uid_off, uid)
        if record is None or int(record["start"]) in seen_starts:
            continue
        seen_starts.add(int(record["start"]))
        records.append(record)

    records.sort(key=_record_start)
    if not records:
        return records

    tagged_index = 0
    plain_index = 0
    for index, record in enumerate(records):
        next_start = _record_start(records[index + 1]) if index + 1 < len(records) else len(data)
        payload_start = int(record.get("payloadStart") or 0)
        while tagged_index < len(tagged_strings) and int(tagged_strings[tagged_index].get("offset") or 0) < payload_start:
            tagged_index += 1
        scan_index = tagged_index
        while scan_index < len(tagged_strings) and int(tagged_strings[scan_index].get("offset") or 0) < next_start:
            record["strings"].append(tagged_strings[scan_index])
            scan_index += 1
        while plain_index < len(plain_strings) and int(plain_strings[plain_index].get("offset") or 0) < payload_start:
            plain_index += 1
        scan_index = plain_index
        while scan_index < len(plain_strings) and int(plain_strings[scan_index].get("offset") or 0) < next_start:
            record["plainStrings"].append(plain_strings[scan_index])
            scan_index += 1

    return records


def decode_levelscript_action_map_details(
    data: bytes,
    *,
    sample_record_limit: int = 8,
    max_hint_records: int = 128,
) -> dict[str, Any]:
    tagged_strings = _extract_levelscript_tagged_ascii_strings(data)
    plain_strings = _extract_levelscript_plain_ascii_strings(
        data,
        tagged_offsets={int(hit.get("offset") or 0) for hit in tagged_strings},
    )
    records = extract_levelscript_uid_records(data, tagged_strings, plain_strings)
    action_map, memberships = levelscript_action_map_membership(data, records)
    list_status_counts: Counter[str] = Counter()
    for row in action_map.get("serializedLists") or []:
        name = str(row.get("name") or "")
        status = str(row.get("status") or "")
        if name or status:
            list_status_counts[f"{name}:{status}"] += 1

    membership_counts: Counter[str] = Counter()
    for label in memberships.values():
        label_text = str(label or "")
        if not label_text:
            continue
        list_name = label_text.split("#", 1)[0]
        if label_text.endswith(" root"):
            membership_counts[f"{list_name}:root"] += 1
        elif label_text.endswith(" linked"):
            membership_counts[f"{list_name}:linked"] += 1
        else:
            membership_counts[list_name] += 1

    record_code_counts: Counter[str] = Counter()
    hint_counts: Counter[str] = Counter()
    sample_rows: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        code = record.get("code")
        kind = record.get("kind")
        if isinstance(code, int) and isinstance(kind, int):
            record_code_counts[f"0x{code:04x}:0x{kind:02x}"] += 1
        next_start = _record_start(records[index + 1]) if index + 1 < len(records) else len(data)
        detail: dict[str, Any] = {}
        if index < max_hint_records:
            detail = decode_levelscript_record_payload(
                data,
                record,
                next_start=next_start,
                action_map_role=memberships.get(_record_start(record)),
            )
            label = (
                detail.get("label")
                or (detail.get("actionHeader") or {}).get("payloadShape")
                or detail.get("payloadShape")
                or ""
            )
            if label:
                hint_counts[str(label)] += 1
        if len(sample_rows) < sample_record_limit:
            sample: dict[str, Any] = {
                "offset": _offset_hex(_record_start(record)),
                "layout": record.get("layout"),
                "role": memberships.get(_record_start(record)) or "",
                "code": f"0x{code:04x}" if isinstance(code, int) else "",
                "kind": f"0x{kind:02x}" if isinstance(kind, int) else "",
                "localId": record.get("localId"),
                "nextId": record.get("nextId"),
                "uid": record.get("uid"),
                "strings": [str(hit.get("text") or "") for hit in (record.get("strings") or [])[:4]],
                "plainStrings": [str(hit.get("text") or "") for hit in (record.get("plainStrings") or [])[:4]],
            }
            label = (
                detail.get("label")
                or (detail.get("actionHeader") or {}).get("payloadShape")
                or detail.get("payloadShape")
                or ""
            )
            if label:
                sample["payloadHint"] = label
            sample_rows.append(_drop_empty(sample))

    return _drop_empty(
        {
            "actionMap": action_map,
            "uidRecordCount": len(records),
            "membershipCount": len(memberships),
            "taggedStringCount": len(tagged_strings),
            "plainStringCount": len(plain_strings),
            "listStatusCounts": dict(list_status_counts.most_common(12)),
            "membershipCounts": dict(membership_counts.most_common(12)),
            "recordCodeCounts": dict(record_code_counts.most_common(24)),
            "recordHintCounts": dict(hint_counts.most_common(24)),
            "recordHintSampledCount": min(len(records), max_hint_records),
            "sampleRecords": sample_rows,
        }
    )


def _payload_sentinel_size(data: bytes, offset: int) -> int:
    if offset + 12 <= len(data) and data[offset : offset + 12] == COMPACT_NULL_SENTINEL:
        return 12
    return 0


def _decode_tagged_payload_fields(payload: bytes, *, max_fields: int = 8) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(payload) and len(fields) < max_fields:
        if payload[cursor] != 0x04:
            cursor += 1
            continue
        if cursor + 5 > len(payload):
            break

        size = struct.unpack_from("<I", payload, cursor + 1)[0]
        if 0 < size <= 120 and cursor + 5 + size <= len(payload):
            raw = payload[cursor + 5 : cursor + 5 + size]
            if _is_printable_ascii(raw):
                text = raw.decode("ascii", errors="replace")
                end = cursor + 5 + size
                fields.append(
                    _drop_empty(
                        {
                            "offset": _offset_hex(cursor),
                            "type": "string",
                            "value": text,
                        }
                    )
                )
                cursor = end + _payload_sentinel_size(payload, end)
                continue

        raw4 = payload[cursor + 1 : cursor + 5]
        scalar_u32 = struct.unpack("<I", raw4)[0]
        scalar_i32 = struct.unpack("<i", raw4)[0]
        scalar_float = struct.unpack("<f", raw4)[0]
        field: dict[str, Any] = {
            "offset": _offset_hex(cursor),
            "type": "scalar",
        }
        if scalar_u32 <= 1_000_000:
            field["u32"] = scalar_u32
        if -1_000_000 <= scalar_i32 <= 1_000_000:
            field["i32"] = scalar_i32
        if -1_000_000.0 <= scalar_float <= 1_000_000.0:
            field["float"] = _round_float(scalar_float)
        if not any(key in field for key in ("u32", "i32", "float")):
            field["rawHex"] = raw4.hex(" ")
        fields.append(_drop_empty(field))
        end = cursor + 5
        cursor = end + _payload_sentinel_size(payload, end)
    return fields


def _record_text_values(record: dict[str, Any] | None, fields: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for field in fields:
        if field.get("type") == "string" and field.get("value") not in values:
            values.append(str(field.get("value")))
    for key in ("strings", "plainStrings"):
        for hit in (record or {}).get(key) or []:
            text = hit.get("text") if isinstance(hit, dict) else hit
            if isinstance(text, str) and text and text not in values:
                values.append(text)
    return values


def _looks_like_property_key(text: str) -> bool:
    if not text or len(text) > 80:
        return False
    if text in NOISY_PROPERTY_TEXT:
        return False
    if text.isdigit():
        return False
    if any(text.startswith(prefix) for prefix in NOISY_PROPERTY_PREFIXES):
        return False
    return any(ch.isalpha() for ch in text)


def _extract_property_output_refs(texts: list[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for text in texts:
        match = PROPERTY_OUTPUT_RE.match(text)
        if not match:
            continue
        refs.append({
            "localId": int(match.group("local")),
            "field": match.group("name"),
            "ref": text,
        })
    return refs


def _extract_trigger_slot_ids(payload: bytes) -> list[int]:
    slots: list[int] = []
    for offset in range(0, max(0, len(payload) - 3)):
        value = struct.unpack_from("<I", payload, offset)[0]
        if 80000 <= value <= 89999 and value not in slots:
            slots.append(value)
    return slots


def _extract_tail_local_refs(payload: bytes) -> list[int]:
    if len(payload) < 8:
        return []
    refs: list[int] = []
    for offset in (len(payload) - 8, len(payload) - 4):
        value = struct.unpack_from("<i", payload, offset)[0]
        if 0 <= value <= 0x1000 and value not in refs:
            refs.append(value)
    return refs


def _read_compact_string(payload: bytes, offset: int) -> tuple[str | None, int | None]:
    if offset < 0 or offset + 4 > len(payload):
        return None, None
    size = struct.unpack_from("<I", payload, offset)[0]
    if size > 120 or offset + 4 + size > len(payload):
        return None, None
    raw = payload[offset + 4 : offset + 4 + size]
    if not _is_printable_ascii(raw):
        return None, None
    return raw.decode("ascii", errors="replace"), offset + 4 + size


def _append_small_i32_tail(payload: bytes, cursor: int, out: dict[str, Any]) -> None:
    if cursor < 0 or cursor >= len(payload):
        return
    remaining = len(payload) - cursor
    if remaining != 4:
        if 0 < remaining <= 16:
            out["tailBytes"] = payload[cursor:].hex(" ")
        return
    value = struct.unpack_from("<i", payload, cursor)[0]
    out["tailLocalRef"] = value
    if 0 <= value <= 0x1000:
        out["gateLocalRefs"] = [value]


def _decode_post_flag_and_tail(payload: bytes, cursor: int, out: dict[str, Any]) -> None:
    if cursor + 14 > len(payload) or payload[cursor] != 0x04:
        _append_small_i32_tail(payload, cursor, out)
        return
    out["postFlag"] = payload[cursor + 1]
    out["postFlagOffset"] = _offset_hex(cursor + 1)
    out["postSentinel"] = payload[cursor + 2 : cursor + 14] == COMPACT_NULL_SENTINEL
    cursor += 14
    _append_small_i32_tail(payload, cursor, out)


def _decode_compact_property_gate(payload: bytes) -> dict[str, Any]:
    """Decode the compact 0x0a03 condition/gate payload shape.

    The runtime class is still unnamed. The stable exported shape is a
    sentinel-headed compact condition with one or two operand slots, an
    authored property/key string in many rows, a post-key 0/1 flag, and
    sometimes a trailing small int that resolves to a local action id.
    """
    if len(payload) < 15:
        return {}
    out: dict[str, Any] = {
        "payloadShape": "compact-condition-gate",
        "headByte": payload[0],
        "headSentinel": payload[1:13] == COMPACT_NULL_SENTINEL,
        "firstTag": payload[13],
        "firstFlag": payload[14],
    }
    if not out["headSentinel"] or payload[13] != 0x04:
        return _drop_empty(out)

    # Common key form:
    #   00 <sentinel> 04 00 ff ff ff ff <typeCode> <len> <key>
    if len(payload) >= 27 and payload[15:19] == b"\xff\xff\xff\xff":
        type_code = struct.unpack_from("<I", payload, 19)[0]
        key_text, cursor = _read_compact_string(payload, 23)
        if key_text is not None and cursor is not None:
            out.update(
                {
                    "schema": "single-key",
                    "typeCode": type_code,
                    "propertyKey": key_text,
                    "propertyKeyOffset": _offset_hex(27),
                }
            )
            _decode_post_flag_and_tail(payload, cursor, out)
            return _drop_empty(out)

    # Two-slot key form:
    #   00 <sentinel> 04 01 <sentinel> 04 00 ff ff ff ff <typeCode> <len> <key>
    if len(payload) >= 41 and payload[15:27] == COMPACT_NULL_SENTINEL and payload[27] == 0x04:
        type_code = struct.unpack_from("<I", payload, 33)[0]
        key_text, cursor = _read_compact_string(payload, 37)
        if key_text is not None and cursor is not None:
            out.update(
                {
                    "schema": "two-slot-key",
                    "secondTag": payload[27],
                    "secondFlag": payload[28],
                    "typeCode": type_code,
                    "propertyKey": key_text,
                    "propertyKeyOffset": _offset_hex(41),
                }
            )
            _decode_post_flag_and_tail(payload, cursor, out)
            return _drop_empty(out)

    # No-key local-ref form. These rows compare a local/scalar slot and do not
    # carry a property name in the action payload.
    if len(payload) >= 41 and payload[19:27] == b"\xff\xff\xff\xff\xff\xff\xff\xff" and payload[27] == 0x04:
        out.update(
            {
                "schema": "local-ref",
                "firstLocalRef": struct.unpack_from("<i", payload, 15)[0],
                "secondTag": payload[27],
                "secondFlag": payload[28],
                "secondSentinel": payload[29:41] == COMPACT_NULL_SENTINEL,
            }
        )
        _append_small_i32_tail(payload, 41, out)
        return _drop_empty(out)

    return _drop_empty(out)


def _decode_manual_levelscript_control(payload: bytes, role: str) -> dict[str, Any]:
    """Decode stable diagnostics for ManualStart/ManualEnd action payloads."""
    if len(payload) < 46:
        return {}
    script_id_candidate: int | None = None
    if payload[17] == 0x04 and len(payload) >= 26:
        raw_script_id = struct.unpack_from("<Q", payload, 18)[0]
        if _is_plausible_levelscript_id(raw_script_id):
            script_id_candidate = raw_script_id
    marker_values: list[int] = []
    for offset in range(0, len(payload) - 3):
        value = struct.unpack_from("<I", payload, offset)[0]
        if 900 <= value <= 1100 and value not in marker_values:
            marker_values.append(value)
    canonical_prefix = (
        payload[0] == 0x04
        and payload[1:9] == b"\xff" * 8
        and payload[13:17] == b"\xff" * 4
        and payload[17] == 0x04
        and payload[18:34] == b"\x00" * 16
        and payload[34:38] == b"\xff" * 4
        and payload[42:46] == b"\xff" * 4
    )
    out = {
        "action": "ManualStartLevelScript" if role == "manual-start" else "ManualEndLevelScript",
        "role": role,
        "payloadShape": "manual-levelscript-default-operands" if canonical_prefix else "manual-levelscript-unknown",
        "memberCountByte": payload[0],
        "markerU32s": marker_values,
        "hasLiteralLevelId": False,
        "hasLiteralScriptId": script_id_candidate is not None,
        "scriptIdCandidate": str(script_id_candidate) if script_id_candidate is not None else "",
        "constantTargetStatus": "script-id-only" if script_id_candidate is not None else "absent",
    }
    if script_id_candidate is not None:
        out["payloadShape"] = "manual-levelscript-script-id-operand"
    if len(payload) > 46 and canonical_prefix:
        out["trailingBytesAfterCanonicalPrefix"] = payload[46:].hex(" ")
    return _drop_empty(out)


def _decode_action_header_prefix(payload: bytes) -> dict[str, Any]:
    """Decode the compact common ActionHeader prefix.

    GameAssembly body recovery shows the MemoryPack wrapper setters store
    ActionHeader fields at runtime offsets: nextID +0x60, priority +0x64,
    triggerActiveDuring +0x68, filterMode +0x6c, filterLevel +0x70,
    filterMask +0x74, and validate +0x78.

    In the exported LevelScript blobs observed so far, high ActionHeader rows
    carry a compact 17-byte prefix. The useful playback edge is `_nextID`,
    serialized as a u32 at payload offset +5. The fixed record trailer also
    has a `nextId`-looking integer, but for headerList rows that value often
    points nowhere useful and is not the event-to-action edge.
    """
    if len(payload) < 17:
        return {}
    filter_level = struct.unpack_from("<i", payload, 0)[0]
    filter_mode = payload[4]
    next_id = struct.unpack_from("<i", payload, 5)[0]
    priority = struct.unpack_from("<i", payload, 9)[0]
    trigger_active_during = struct.unpack_from("<i", payload, 13)[0]
    if filter_mode > 8:
        return {}
    if not (-1 <= next_id <= 0x10000):
        return {}
    if not (-1000 <= filter_level <= 100000):
        return {}
    if not (-1000 <= priority <= 100000):
        return {}
    if not (-1000 <= trigger_active_during <= 100000):
        return {}
    return _drop_empty(
        {
            "payloadShape": "action-header-prefix",
            "filterLevel": filter_level,
            "filterMode": filter_mode,
            "nextId": next_id,
            "priority": priority,
            "triggerActiveDuring": trigger_active_during,
            "nextIdOffset": "0x5",
        }
    )


def _record_payload_window(
    data: bytes,
    record: dict[str, Any] | None,
    next_start: int | None,
) -> tuple[int, bytes]:
    if not data or not record:
        return 0, b""
    payload_start = int(record.get("payloadStart", record.get("start", 0)) or 0)
    if payload_start < 0 or payload_start >= len(data):
        return payload_start, b""
    if next_start is None or next_start <= payload_start or next_start > len(data):
        next_start = min(len(data), payload_start + 160)
    return payload_start, data[payload_start:next_start]


def decode_levelscript_record_payload(
    data: bytes,
    record: dict[str, Any] | None,
    *,
    next_start: int | None = None,
    action_map_role: str | None = None,
) -> dict[str, Any]:
    """Decode small, diagnostic LevelScript action-record payload hints.

    This deliberately stays conservative: labels are shape hints, not a full
    opcode table. ManualStart/ManualEnd are named only where ActionBase
    formatter tags prove the class; observed rows still do not serialize
    literal levelId + scriptId targets in the action payload.
    """
    if not data or not record:
        return {}
    code = record.get("code")
    kind = record.get("kind")
    if not isinstance(code, int) or not isinstance(kind, int):
        return {}
    key = (code, kind)
    payload_start, payload = _record_payload_window(data, record, next_start)
    if not payload:
        return {}

    hint = dict(LEVELSCRIPT_RECORD_HINTS.get(key) or {})
    fields = _decode_tagged_payload_fields(payload)
    texts = _record_text_values(record, fields)
    property_outputs = _extract_property_output_refs(texts)
    property_keys = [
        text
        for text in texts
        if _looks_like_property_key(text) and not PROPERTY_OUTPUT_RE.match(text)
    ]
    trigger_slot_ids = _extract_trigger_slot_ids(payload) if key in TRIGGER_VOLUME_RECORD_KEYS else []
    out: dict[str, Any] = {
        "payloadStart": _offset_hex(payload_start),
        "payloadLength": len(payload),
        "payloadHexPrefix": payload[:48].hex(" "),
        "taggedFields": fields,
    }
    out.update(hint)
    action_map_role_text = str(action_map_role or "")
    header_role = action_map_role_text.startswith("headerList")
    action_header_code = (
        kind == 0x00
        and (
            0x1000 <= code <= 0x18FF
            or (header_role and 0x0E00 <= code <= 0x18FF)
        )
    )
    if action_header_code:
        action_header = _decode_action_header_prefix(payload)
        if action_header:
            out["actionHeader"] = action_header
    if property_outputs:
        out["propertyOutputRefs"] = property_outputs
    if property_keys and (
        "propertyRole" in hint
        or key in {
            (0x04B8, 0x09),
            (0x104A, 0x00),
        }
    ):
        out["propertyKeys"] = property_keys[:8]
    if trigger_slot_ids:
        out["triggerSlotIds"] = trigger_slot_ids
    if key == (0x0A03, 0x00):
        gate = _decode_compact_property_gate(payload)
        if gate:
            out["compactGate"] = gate
            gate_key = gate.get("propertyKey")
            if isinstance(gate_key, str) and gate_key and not gate_key.startswith("$"):
                property_keys = list(out.get("propertyKeys") or [])
                if gate_key not in property_keys:
                    property_keys.append(gate_key)
                out["propertyKeys"] = property_keys[:8]
            gate_refs = gate.get("gateLocalRefs") or []
            if gate_refs:
                out["gateLocalRefs"] = gate_refs
                out["gateRole"] = "conditional-local-ref"
    if key == (0x0BED, 0x00):
        branch_refs = _extract_tail_local_refs(payload)
        if branch_refs:
            out["branchLocalRefs"] = branch_refs
            out["branchRole"] = "conditional-terminal-local-refs"
    if key in {(0x02F1, 0x0A), (0x02EC, 0x0A)}:
        role = str(hint.get("levelScriptControlRole") or "")
        manual_control = _decode_manual_levelscript_control(payload, role)
        if manual_control:
            out["manualControl"] = manual_control

    if key == (0x04BD, 0x09) and payload[:1] == b"\x04" and len(payload) >= 5:
        out["seconds"] = _round_float(struct.unpack_from("<f", payload, 1)[0])
    elif key in SCRIPT_POINTER_REF_RECORDS:
        pointer = decode_script_pointer_payload(data, record)
        if pointer:
            out.setdefault("label", "script-ptr-scalar-ref")
            out.setdefault("confidence", "medium")
            out.setdefault("note", (
                "LevelScriptPtr plus scalar parameter; matches trigger-volume predicate/action field shape, "
                "not ManualStart/ManualEnd because no levelId string is serialized"
            ))
            out["scriptPointer"] = pointer
        else:
            out.setdefault("label", "scalar-control")
            out.setdefault("confidence", "low")
            out.setdefault("note", (
                "same opcode family as script-pointer refs, but this payload does not contain "
                "a plausible LevelScript id"
            ))
    elif key == (0x0463, 0x09) and len(payload) >= 4:
        count = struct.unpack_from("<I", payload, 0)[0]
        if count <= 64 and 4 + count * 4 <= len(payload):
            out["localRecordRefs"] = [
                struct.unpack_from("<I", payload, 4 + index * 4)[0]
                for index in range(count)
            ]
    elif key == (0x02EE, 0x09):
        for field in fields:
            if field.get("type") == "string" and str(field.get("value") or "").startswith("guide_"):
                out["guideId"] = field.get("value")
                break
    elif key == (0x104A, 0x00):
        texts = [
            str(hit.get("text") or "")
            for hit in (record.get("strings") or []) + (record.get("plainStrings") or [])
            if isinstance(hit, dict) and hit.get("text")
        ]
        if texts:
            out["signalKeys"] = texts[:4]
    return _drop_empty(out)


def _tail_candidate(data: bytes, offset: int) -> dict[str, Any]:
    start_shape_offset = offset + 8
    start_shape, start_shape_end = _decode_levelscript_shape_list(data, start_shape_offset)
    start_shape_status = str(start_shape.get("status") or "missing")
    start_shape_count = start_shape.get("count")
    start_type_offset: int | None = None
    if start_shape_status in {"null", "present"} and start_shape_end is not None:
        start_type_offset = start_shape_end

    start_type_raw = _u32(data, start_type_offset) if start_type_offset is not None else None
    start_type_valid = start_type_raw in LEVELSCRIPT_START_TYPE_NAMES
    task_map_offset = start_type_offset + 4 if start_type_valid and start_type_offset is not None else None
    task_map_raw = _u32(data, task_map_offset) if task_map_offset is not None else None
    task_map_status, task_map_count = _list_status(task_map_raw)
    task_map_end: int | None = None
    if task_map_offset is not None and task_map_status == "null":
        task_map_end = task_map_offset + 4
    trigger_volume_offset = task_map_end
    trigger_volume: dict[str, Any] = {}
    if trigger_volume_offset is not None:
        trigger_volume, _trigger_volume_end = _decode_trigger_volume_map(data, trigger_volume_offset)
    trigger_volume_status = str(trigger_volume.get("status") or "missing")
    trigger_volume_count = trigger_volume.get("count")

    score = offset
    if start_type_valid:
        score += 1_000_000
    if start_shape_status == "null":
        score += 100_000
    elif start_shape_count == 0:
        score += 50_000
    if task_map_status in {"null", "present"}:
        score += 10_000

    return {
        "scriptIdOffset": offset,
        "scriptIdOffsetHex": f"0x{offset:x}",
        "startShapeListOffset": start_shape_offset,
        "startShapeListStatus": start_shape_status,
        "startShapeListCount": start_shape_count,
        "startShapeList": start_shape,
        "startTypeOffset": start_type_offset,
        "startTypeOffsetHex": _offset_hex(start_type_offset),
        "startTypeRaw": start_type_raw if start_type_valid else None,
        "startTypeName": LEVELSCRIPT_START_TYPE_NAMES.get(
            start_type_raw if start_type_raw is not None else -1,
            "",
        ),
        "taskMapOffset": task_map_offset,
        "taskMapOffsetHex": _offset_hex(task_map_offset),
        "taskMapStatus": task_map_status,
        "taskMapCount": task_map_count,
        "triggerVolumesOffset": trigger_volume_offset,
        "triggerVolumesOffsetHex": _offset_hex(trigger_volume_offset),
        "triggerVolumesStatus": trigger_volume_status,
        "triggerVolumesCount": trigger_volume_count,
        "triggerVolumes": trigger_volume,
        "score": score,
    }


def decode_levelscript_binary_summary(data: bytes, script_id: int) -> dict[str, Any]:
    """Decode stable top-level LevelScriptData facts from a raw blob.

    This intentionally handles only fields whose byte positions can be verified
    cheaply from the IL2CPP MemoryPack setter order. It does not parse action
    records or promote start/end semantics into order edges.
    """
    if not data or script_id <= 0:
        return {}
    action_map = decode_levelscript_action_map_header(data)
    offsets = _u64_offsets(data, script_id)
    candidates = [_tail_candidate(data, offset) for offset in offsets]
    best = max(candidates, key=lambda item: int(item.get("score") or 0), default={})
    return {
        "serializedMemberCount": data[0],
        "expectedMemberCount": 26,
        "actionMapStatus": action_map.get("status") or "",
        "actionMapRecordCount": action_map.get("recordCount"),
        "actionMapRecordStartOffsetHex": action_map.get("recordStartOffsetHex") or "",
        "actionMapHeader": action_map,
        "scriptId": str(script_id),
        "scriptIdOffsets": [f"0x{offset:x}" for offset in offsets],
        "scriptIdOccurrenceCount": len(offsets),
        "scriptIdVerified": bool(offsets),
        "probableScriptIdOffset": best.get("scriptIdOffset"),
        "probableScriptIdOffsetHex": best.get("scriptIdOffsetHex") or "",
        "startShapeListStatus": best.get("startShapeListStatus") or "",
        "startShapeListCount": best.get("startShapeListCount"),
        "startShapeListDetails": best.get("startShapeList") or {},
        "startShapeListShapes": (best.get("startShapeList") or {}).get("shapes") or [],
        "startTypeOffset": best.get("startTypeOffset"),
        "startTypeOffsetHex": best.get("startTypeOffsetHex") or "",
        "startTypeRaw": best.get("startTypeRaw"),
        "startTypeName": best.get("startTypeName") or "",
        "taskMapOffsetHex": best.get("taskMapOffsetHex") or "",
        "taskMapStatus": best.get("taskMapStatus") or "",
        "taskMapCount": best.get("taskMapCount"),
        "triggerVolumesOffsetHex": best.get("triggerVolumesOffsetHex") or "",
        "triggerVolumesStatus": best.get("triggerVolumesStatus") or "",
        "triggerVolumesCount": best.get("triggerVolumesCount"),
        "triggerVolumesDetails": best.get("triggerVolumes") or {},
        "triggerVolumeSlotIds": (best.get("triggerVolumes") or {}).get("slotIds") or [],
        "note": (
            "actionMap header plus scriptId/startType/shape-list trigger fields decoded from the top-level MemoryPack; "
            "action start/end opcodes are still not decoded"
        ),
    }


def decode_levelscript_binary_file(path: Path, script_id: int | str) -> dict[str, Any]:
    try:
        numeric_script_id = int(script_id)
    except (TypeError, ValueError):
        return {}
    try:
        data = path.read_bytes()
    except OSError:
        return {}
    return decode_levelscript_binary_summary(data, numeric_script_id)
