#!/usr/bin/env python3
"""Audit the best recovered trigger evidence for each mission story entry.

This is intentionally evidence-first. It does not claim that unknown
LevelScript opcodes are decoded; instead it reports the script start mode, the
UID chain that contains the play record, nearby property/trigger-looking
strings, MissionRuntime property checks, and incoming script-pointer refs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402
from story_builder.level_bindings import (  # noqa: E402
    _build_uid_record_chains,
    _load_levelscript_binding_data,
    classify_levelscript_record,
)
from story_builder.levelscript_binary import (  # noqa: E402
    decode_levelscript_binary_file,
    decode_levelscript_record_payload,
    levelscript_action_map_membership,
)
from story_builder.mission_recovery import decode_mission_script_conditions  # noqa: E402


DATA_JSON_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json"
MISSION_RUNTIME_DIR = DATA_JSON_ROOT / "MissionRuntimeAsset"
STORY_ORDER_PATH = ROOT / "webui" / "data" / "assets" / "story_order.json"
DEFAULT_REPORT_DIR = ROOT / "reports" / "mission_order"

PLAY_CLASSES = {"play_cutscene", "play_radio", "play_dialog", "play_levelseq"}
NOISY_TEXT_PREFIXES = (
    "$",
    "#",
    "au_",
    "levelseq_",
    "cutscene_",
    "radio_",
    "dlg_",
    "guide_",
    "buff_",
    "chr_",
    "LD/",
)
NOISY_EXACT = {"event_args", "blackboard"}


def safe_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def parse_levelscript_source(source_file: str, source_script: str = "") -> tuple[str, str]:
    text = safe_text(source_file).replace("\\", "/")
    if "/LevelScriptData/" in text:
        tail = text.split("/LevelScriptData/", 1)[1]
        parts = [part for part in tail.split("/") if part]
        if len(parts) >= 2:
            return parts[0], Path(parts[-1]).stem
    return "", safe_text(source_script)


def source_path_for_entry(entry: dict[str, Any]) -> Path | None:
    source_file = safe_text(entry.get("sourceFile"))
    if not source_file:
        return None
    path = Path(source_file)
    if not path.is_absolute():
        path = ROOT / path
    return path


def binary_summary_for_entry(entry: dict[str, Any]) -> dict[str, Any]:
    path = source_path_for_entry(entry)
    script_id = safe_text(entry.get("sourceScript")) or (path.stem if path else "")
    if not path or not script_id:
        return {}
    return decode_levelscript_binary_file(path, script_id)


def entry_with_fresh_binary(entry: dict[str, Any]) -> dict[str, Any]:
    summary = binary_summary_for_entry(entry)
    if not summary:
        return dict(entry)
    out = dict(entry)
    out.update({
        "binaryMemberCount": summary.get("serializedMemberCount"),
        "binaryExpectedMemberCount": summary.get("expectedMemberCount"),
        "binaryActionMap": summary.get("actionMapStatus") or "",
        "binaryActionMapRecordCount": summary.get("actionMapRecordCount"),
        "binaryActionMapRecordStartOffset": summary.get("actionMapRecordStartOffsetHex") or "",
        "binaryScriptIdVerified": bool(summary.get("scriptIdVerified")),
        "binaryScriptIdOffset": summary.get("probableScriptIdOffsetHex") or "",
        "binaryScriptIdOccurrenceCount": summary.get("scriptIdOccurrenceCount"),
        "binaryStartShapeList": summary.get("startShapeListStatus") or "",
        "binaryStartShapeListCount": summary.get("startShapeListCount"),
        "binaryStartShapeListShapes": summary.get("startShapeListShapes") or [],
        "binaryStartType": summary.get("startTypeName") or "",
        "binaryStartTypeRaw": summary.get("startTypeRaw"),
        "binaryTaskMap": summary.get("taskMapStatus") or "",
        "binaryTaskMapCount": summary.get("taskMapCount"),
        "binaryTriggerVolumes": summary.get("triggerVolumesStatus") or "",
        "binaryTriggerVolumesCount": summary.get("triggerVolumesCount"),
        "binaryTriggerVolumeSlotIds": summary.get("triggerVolumeSlotIds") or [],
        "binaryTriggerVolumesDetails": summary.get("triggerVolumesDetails") or {},
        "binaryNote": summary.get("note") or "",
    })
    return out


def aliases_for_entry_key(key: str) -> set[str]:
    aliases = {key}
    if key.startswith("misc_"):
        aliases.add(key[5:])
    return {alias for alias in aliases if alias}


def record_texts(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for field in ("strings", "plainStrings"):
        for hit in record.get(field) or []:
            text = safe_text(hit.get("text") if isinstance(hit, dict) else hit)
            if text and text not in out:
                out.append(text)
    return out


def meaningful_trigger_texts(records: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for record in records:
        for text in record_texts(record):
            if text in NOISY_EXACT:
                continue
            if text.isdigit() or re.fullmatch(r"[0-9a-fA-F]{8}", text):
                continue
            if any(text.startswith(prefix) for prefix in NOISY_TEXT_PREFIXES):
                continue
            if len(text) > 80:
                continue
            if text not in out:
                out.append(text)
    return out[:12]


def format_vec(vec: dict[str, Any] | None) -> str:
    if not isinstance(vec, dict):
        return ""
    parts = []
    for key in ("x", "y", "z"):
        value = vec.get(key)
        if isinstance(value, (int, float)):
            parts.append(f"{value:.3f}".rstrip("0").rstrip("."))
    return "(" + ", ".join(parts) + ")" if len(parts) == 3 else ""


def format_levelscript_shape(shape: dict[str, Any]) -> str:
    shape_type = safe_text(shape.get("type"))
    position = format_vec(shape.get("position"))
    size = format_vec(shape.get("size"))
    radius = shape.get("radius")
    bits = [shape_type]
    if position:
        bits.append(f"pos {position}")
    if size and shape_type == "BOX":
        bits.append(f"size {size}")
    if isinstance(radius, (int, float)) and shape_type == "SPHERE":
        bits.append(f"r {radius:.3f}".rstrip("0").rstrip("."))
    return " ".join(bit for bit in bits if bit)


def format_start_shapes(shapes: list[dict[str, Any]]) -> str:
    parts = [format_levelscript_shape(shape) for shape in shapes[:4] if isinstance(shape, dict)]
    parts = [part for part in parts if part]
    if len(shapes) > len(parts):
        parts.append(f"+{len(shapes) - len(parts)} more")
    return "; ".join(parts)


def format_trigger_volume_shape(shape: dict[str, Any]) -> str:
    shape_type = safe_text(shape.get("shapeType"))
    position = format_vec(shape.get("position"))
    size = format_vec(shape.get("size"))
    radius = shape.get("radius")
    bits = [shape_type]
    if position:
        bits.append(f"pos {position}")
    if size and shape_type == "Box":
        bits.append(f"size {size}")
    if isinstance(radius, (int, float)) and shape_type == "Sphere":
        bits.append(f"r {radius:.3f}".rstrip("0").rstrip("."))
    return " ".join(bit for bit in bits if bit)


def format_trigger_volumes(details: dict[str, Any]) -> str:
    volumes = details.get("volumes") if isinstance(details, dict) else []
    if not isinstance(volumes, list):
        return ""
    parts: list[str] = []
    for volume in volumes[:6]:
        if not isinstance(volume, dict):
            continue
        slot_id = volume.get("slotId") or volume.get("keySlotId")
        shapes = ((volume.get("shapeList") or {}).get("shapes") or [])
        shape_text = ""
        if shapes and isinstance(shapes[0], dict):
            shape_text = format_trigger_volume_shape(shapes[0])
        bit = f"slot {slot_id}" if slot_id is not None else ""
        if shape_text:
            bit = f"{bit}: {shape_text}" if bit else shape_text
        if bit:
            parts.append(bit)
    if len(volumes) > len(parts):
        parts.append(f"+{len(volumes) - len(parts)} more")
    return "; ".join(parts)


def compact_record(
    record: dict[str, Any],
    data: bytes | None = None,
    next_start: int | None = None,
    action_map_index_by_start: dict[int, int] | None = None,
    action_map_role_by_start: dict[int, str] | None = None,
) -> dict[str, Any]:
    code = record.get("code")
    kind = record.get("kind")
    decoded = decode_levelscript_record_payload(data or b"", record, next_start=next_start) if data else {}
    start = int(record.get("start") or 0)
    action_map_text = ""
    if action_map_role_by_start is not None:
        action_map_text = action_map_role_by_start.get(start) or "outside"
    elif action_map_index_by_start is not None:
        action_map_text = "outside"
    return {
        "start": start,
        "payloadStart": int(record.get("payloadStart", record.get("start", 0)) or 0),
        "localId": record.get("localId"),
        "nextId": record.get("nextId"),
        "code": f"0x{int(code):04x}" if isinstance(code, int) else "",
        "kind": f"0x{int(kind):02x}" if isinstance(kind, int) else "",
        "class": classify_levelscript_record(record) or "",
        "actionMap": action_map_text,
        "hint": decoded.get("label") or "",
        "hintConfidence": decoded.get("confidence") or "",
        "decoded": {
            key: value
            for key, value in decoded.items()
            if key
            in {
                "seconds",
                "scriptPointer",
                "localRecordRefs",
                "branchLocalRefs",
                "branchRole",
                "guideId",
                "signalKeys",
                "triggerSlotIds",
                "triggerRole",
                "triggerEventKind",
                "propertyKeys",
                "propertyOutputRefs",
                "taggedFields",
                "note",
            }
            and value not in ("", None, [], {})
        },
        "strings": [
            safe_text(hit.get("text"))
            for hit in (record.get("strings") or [])[:6]
            if isinstance(hit, dict) and safe_text(hit.get("text"))
        ],
        "plainStrings": [
            safe_text(hit.get("text"))
            for hit in (record.get("plainStrings") or [])[:6]
            if isinstance(hit, dict) and safe_text(hit.get("text"))
        ],
    }


def chain_sort_key(chain: list[dict[str, Any]], aliases: set[str]) -> tuple[int, int, int]:
    match_index = 10**9
    play_match = 1
    play_any = 1
    for index, record in enumerate(chain):
        texts = set(record_texts(record))
        record_class = classify_levelscript_record(record) or ""
        if record_class in PLAY_CLASSES:
            play_any = 0
            if texts & aliases:
                play_match = 0
                match_index = min(match_index, index)
        elif texts & aliases:
            match_index = min(match_index, index)
    first_start = int(chain[0].get("start") or 0) if chain else 10**9
    return (play_match, play_any, match_index, first_start)


def action_map_record_metadata(
    data: bytes,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[int, int], dict[int, str]]:
    header, membership_by_start = levelscript_action_map_membership(data, records)
    return header, {}, membership_by_start


def find_matching_chain(level_id: str, script_id: str, key: str) -> dict[str, Any]:
    if not level_id or not script_id:
        return {}
    info = _load_levelscript_binding_data(level_id)
    file_info = next(
        (row for row in info.get("files") or [] if safe_text(row.get("fileStem")) == script_id),
        None,
    )
    if not file_info:
        return {}

    aliases = aliases_for_entry_key(key)
    matching: list[list[dict[str, Any]]] = []
    for chain in _build_uid_record_chains(file_info.get("records") or []):
        for record in chain:
            if set(record_texts(record)) & aliases:
                matching.append(chain)
                break
    if not matching:
        return {"file": file_info.get("file"), "chainsMatched": 0}

    data = b""
    next_start_by_record: dict[int, int | None] = {}
    file_path = Path(safe_text(file_info.get("file")))
    if not file_path.is_absolute():
        file_path = ROOT / file_path
    try:
        data = file_path.read_bytes()
    except OSError:
        data = b""
    sorted_records = sorted(file_info.get("records") or [], key=lambda row: int(row.get("start") or 0))
    for index, record in enumerate(sorted_records):
        next_start_by_record[int(record.get("start") or 0)] = (
            int(sorted_records[index + 1].get("start") or 0)
            if index + 1 < len(sorted_records)
            else None
        )
    action_map_header, action_map_index_by_start, action_map_role_by_start = action_map_record_metadata(
        data,
        sorted_records,
    )

    chain = min(matching, key=lambda row: chain_sort_key(row, aliases))
    compact_chain = [
        compact_record(
            record,
            data,
            next_start_by_record.get(int(record.get("start") or 0)),
            action_map_index_by_start,
            action_map_role_by_start,
        )
        for record in chain
    ]
    play_records = [
        compact_record(
            record,
            data,
            next_start_by_record.get(int(record.get("start") or 0)),
            action_map_index_by_start,
            action_map_role_by_start,
        )
        for record in chain
        if classify_levelscript_record(record) in PLAY_CLASSES
    ]
    matching_records = [
        compact_record(
            record,
            data,
            next_start_by_record.get(int(record.get("start") or 0)),
            action_map_index_by_start,
            action_map_role_by_start,
        )
        for record in chain
        if set(record_texts(record)) & aliases
    ]
    trigger_slot_records = [
        compact_record(
            record,
            data,
            next_start_by_record.get(int(record.get("start") or 0)),
            action_map_index_by_start,
            action_map_role_by_start,
        )
        for record in sorted_records
        if (decode_levelscript_record_payload(
            data,
            record,
            next_start=next_start_by_record.get(int(record.get("start") or 0)),
        ).get("triggerSlotIds") or [])
    ]
    head = compact_chain[0] if compact_chain else {}
    play_index = next(
        (
            index
            for index, record in enumerate(chain)
            if classify_levelscript_record(record) in PLAY_CLASSES
            and (set(record_texts(record)) & aliases or not matching_records)
        ),
        None,
    )
    return {
        "file": file_info.get("file"),
        "chainsMatched": len(matching),
        "chainLength": len(chain),
        "actionMap": {
            "status": action_map_header.get("status") or "",
            "recordCount": action_map_header.get("recordCount"),
            "listCounts": action_map_header.get("listCounts") or {},
            "recordStartOffset": action_map_header.get("recordStartOffsetHex") or "",
        },
        "chainHead": head,
        "playIndex": play_index,
        "playRecords": play_records,
        "matchingRecords": matching_records,
        "triggerSlotRecords": trigger_slot_records,
        "triggerTexts": meaningful_trigger_texts(chain),
        "chain": compact_chain,
    }


def load_story_entries(mission: str) -> list[dict[str, Any]]:
    payload = read_json(STORY_ORDER_PATH, {})
    mission_payload = ((payload.get("missions") or {}).get(mission) or {})
    entries = mission_payload.get("entries") or []
    return [row for row in entries if isinstance(row, dict)]


def load_runtime_conditions(mission: str) -> dict[tuple[str, str], list[dict[str, Any]]]:
    path = MISSION_RUNTIME_DIR / f"{mission}.json"
    raw = read_json(path, {})
    out: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for condition in decode_mission_script_conditions(raw if isinstance(raw, dict) else {}):
        map_id = safe_text(condition.get("mapId"))
        script_id = safe_text(condition.get("scriptId"))
        if not (map_id and script_id):
            continue
        out[(map_id, script_id)].append({
            "questId": safe_text(condition.get("questId")),
            "type": safe_text(condition.get("type")),
            "key": safe_text(condition.get("key")),
            "value": condition.get("value"),
        })
    return out


def incoming_ref_summary(entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ref in entry.get("binaryIncomingScriptRefs") or []:
        if not isinstance(ref, dict):
            continue
        row = {
            "sourceScript": safe_text(ref.get("sourceScript")),
            "targetScript": safe_text(ref.get("targetScript")),
            "record": safe_text(ref.get("record")),
            "class": safe_text(ref.get("class")),
            "relation": safe_text(ref.get("relation")),
            "pointerFlag": ref.get("pointerFlag"),
            "pointerPayloadShape": safe_text(ref.get("pointerPayloadShape")),
        }
        rows.append({key: value for key, value in row.items() if value not in ("", None, [], {})})
    return rows[:6]


def outgoing_ref_summary(entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ref in entry.get("binaryOutgoingScriptRefs") or []:
        if not isinstance(ref, dict):
            continue
        row = {
            "sourceScript": safe_text(ref.get("sourceScript")),
            "targetScript": safe_text(ref.get("targetScript")),
            "record": safe_text(ref.get("record")),
            "class": safe_text(ref.get("class")),
            "relation": safe_text(ref.get("relation")),
            "pointerFlag": ref.get("pointerFlag"),
            "pointerPayloadShape": safe_text(ref.get("pointerPayloadShape")),
        }
        rows.append({key: value for key, value in row.items() if value not in ("", None, [], {})})
    return rows[:6]


def trigger_slot_records_for_entry(
    chain_info: dict[str, Any],
    trigger_slots: list[Any],
) -> list[dict[str, Any]]:
    wanted = {int(slot) for slot in trigger_slots if isinstance(slot, int)}
    if not wanted:
        return []
    out: list[dict[str, Any]] = []
    for record in chain_info.get("triggerSlotRecords") or []:
        decoded = record.get("decoded") if isinstance(record, dict) else {}
        slots = decoded.get("triggerSlotIds") if isinstance(decoded, dict) else []
        if not isinstance(slots, list) or not (wanted & {slot for slot in slots if isinstance(slot, int)}):
            continue
        out.append(record)
    return out


def summarize_trigger_slot_records(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    counts = Counter(
        " ".join(
            part for part in (
                f"{record.get('code')}/{record.get('kind')}",
                safe_text((record.get("decoded") or {}).get("triggerEventKind") if isinstance(record.get("decoded"), dict) else ""),
            )
            if part
        )
        for record in records
        if record.get("code") or record.get("kind")
    )
    return ", ".join(f"{opcode} x{count}" for opcode, count in counts.most_common(4))


def describe_script_start(
    entry: dict[str, Any],
    incoming_refs: list[dict[str, Any]],
    trigger_slot_records: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    start_type = safe_text(entry.get("binaryStartType"))
    start_shape = safe_text(entry.get("binaryStartShapeList"))
    trigger_volumes = safe_text(entry.get("binaryTriggerVolumes"))
    trigger_count = entry.get("binaryTriggerVolumesCount")

    if start_type == "ByEnterStartShape":
        shape_summary = format_start_shapes(entry.get("binaryStartShapeListShapes") or [])
        suffix = f": {shape_summary}" if shape_summary else ""
        return "firm-start-shape", f"starts when player/entity enters startShapeList{suffix}"
    if start_type == "SameWithActive":
        return "candidate-same-with-active", "starts with parent/active LevelScript"
    if start_type == "Manual":
        pointer_refs = [
            ref for ref in incoming_refs
            if ref.get("pointerPayloadShape") or ref.get("record") in {"0x0455/0x0a", "0x045d/0x0a"}
        ]
        if pointer_refs:
            sources = ", ".join(sorted({safe_text(ref.get("sourceScript")) for ref in pointer_refs if ref.get("sourceScript")})[:4])
            return "candidate-manual-ref", f"manual script with incoming script-pointer ref(s) from {sources}"
        if trigger_volumes == "present" and isinstance(trigger_count, int) and trigger_count > 0:
            suffix = f":{trigger_count}" if trigger_count is not None else ""
            slots = entry.get("binaryTriggerVolumeSlotIds") or []
            slot_text = f" slots {', '.join(str(slot) for slot in slots[:6])}" if slots else ""
            record_text = summarize_trigger_slot_records(trigger_slot_records or [])
            record_suffix = f"; matching action records {record_text}" if record_text else ""
            return (
                "candidate-manual-trigger-volume",
                f"manual script with triggerVolumes{suffix}{slot_text}{record_suffix}; starter action not decoded",
            )
        return "candidate-manual", "manual script; starter action not decoded"
    if start_shape == "present":
        if trigger_volumes == "present":
            return "candidate-undecoded-shape", "startShapeList and triggerVolumes are present; non-null shape-list bytes not decoded"
        return "candidate-undecoded-shape", "startShapeList present; non-null shape-list bytes not decoded"
    return "unknown-start", "no decoded script start trigger"


def describe_record_trigger(chain_info: dict[str, Any]) -> str:
    if not chain_info:
        return "no LevelScript play chain recovered"
    chain = chain_info.get("chain") or []
    if not chain:
        return "source file decoded, but no matching UID chain"
    play_records = chain_info.get("playRecords") or []
    play_index = chain_info.get("playIndex")
    head = chain[0]
    head_label = " ".join(
        part for part in (
            safe_text(head.get("code")),
            safe_text(head.get("kind")),
            safe_text(head.get("class")),
            safe_text(head.get("hint")),
            ",".join(head.get("strings") or head.get("plainStrings") or []),
        )
        if part
    )
    trigger_texts = chain_info.get("triggerTexts") or []
    if not play_records:
        return f"matched UID chain has no named play opcode; matched head {head_label}"
    if isinstance(play_index, int) and play_index == 0:
        action_map = safe_text(head.get("actionMap"))
        if action_map and action_map != "outside":
            return (
                f"play record is actionMap {action_map}; "
                "it fires when the LevelScript is activated"
            )
        return "play record is chain head; trigger is script activation or an external caller"
    if trigger_texts:
        return f"chain head {head_label}; trigger-like keys: {', '.join(trigger_texts[:6])}"
    return f"chain head {head_label}; preceding opcode not named"


def build_audit(mission: str, language: str) -> dict[str, Any]:
    entries = load_story_entries(mission)
    runtime_by_script = load_runtime_conditions(mission)
    rows: list[dict[str, Any]] = []
    status_counts = Counter()
    source_count = 0
    chain_count = 0
    play_record_count = 0
    no_play_record_count = 0
    action_map_root_head_count = 0
    outside_head_count = 0
    terminal_branch_count = 0

    for index, raw_entry in enumerate(entries, start=1):
        entry = entry_with_fresh_binary(raw_entry)
        key = safe_text(entry.get("key"))
        level_id, script_id = parse_levelscript_source(
            safe_text(entry.get("sourceFile")),
            safe_text(entry.get("sourceScript")),
        )
        runtime_conditions = runtime_by_script.get((level_id, script_id), [])
        incoming_refs = incoming_ref_summary(entry)
        outgoing_refs = outgoing_ref_summary(entry)
        chain_info = find_matching_chain(level_id, script_id, key) if level_id and script_id else {}
        trigger_slot_records = trigger_slot_records_for_entry(
            chain_info,
            entry.get("binaryTriggerVolumeSlotIds") or [],
        )
        if level_id and script_id:
            source_count += 1
        terminal_branch_evidence = [
            row
            for row in entry.get("terminalBranchEvidence") or []
            if isinstance(row, dict)
        ]
        if terminal_branch_evidence:
            terminal_branch_count += 1
        if chain_info.get("chain"):
            chain_count += 1
            if chain_info.get("playRecords"):
                play_record_count += 1
            else:
                no_play_record_count += 1
            head_action_map = safe_text(((chain_info.get("chain") or [{}])[0] or {}).get("actionMap"))
            if head_action_map.endswith("root"):
                action_map_root_head_count += 1
            elif head_action_map == "outside":
                outside_head_count += 1

        trigger_status, script_start = describe_script_start(entry, incoming_refs, trigger_slot_records)
        record_trigger = describe_record_trigger(chain_info)
        status_counts[trigger_status] += 1

        row = {
            "index": index,
            "key": key,
            "levelId": level_id,
            "sourceScript": script_id,
            "orderEvidence": entry.get("evidence"),
            "orderRank": entry.get("rank"),
            "recordClass": entry.get("recordClass"),
            "scriptStartStatus": trigger_status,
            "scriptStart": script_start,
            "recordTrigger": record_trigger,
            "actionMap": entry.get("binaryActionMap") or "",
            "actionMapRecordCount": entry.get("binaryActionMapRecordCount"),
            "startType": entry.get("binaryStartType") or "",
            "startShapeList": entry.get("binaryStartShapeList") or "",
            "startShapeListCount": entry.get("binaryStartShapeListCount"),
            "startShapeListShapes": entry.get("binaryStartShapeListShapes") or [],
            "triggerVolumes": entry.get("binaryTriggerVolumes") or "",
            "triggerVolumesCount": entry.get("binaryTriggerVolumesCount"),
            "triggerVolumeSlotIds": entry.get("binaryTriggerVolumeSlotIds") or [],
            "triggerVolumesDetails": entry.get("binaryTriggerVolumesDetails") or {},
            "taskMap": entry.get("binaryTaskMap") or "",
            "taskMapCount": entry.get("binaryTaskMapCount"),
            "runtimeConditions": runtime_conditions,
            "terminalBranchEvidence": terminal_branch_evidence,
            "incomingScriptRefs": incoming_refs,
            "outgoingScriptRefs": outgoing_refs,
            "triggerSlotRecords": trigger_slot_records,
            "chain": chain_info,
        }
        rows.append({field: value for field, value in row.items() if value not in ("", None, [], {})})

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "mission": mission,
        "language": language,
        "summary": {
            "entries": len(entries),
            "sourceBackedEntries": source_count,
            "entriesWithUidChains": chain_count,
            "entriesWithPlayRecords": play_record_count,
            "entriesWithUidChainsWithoutPlayRecords": no_play_record_count,
            "entriesWithActionMapRootHeads": action_map_root_head_count,
            "entriesWithOutsideChainHeads": outside_head_count,
            "entriesWithTerminalBranchEvidence": terminal_branch_count,
            "fallbackEntries": len(entries) - source_count,
            "scriptStartStatusCounts": dict(status_counts),
        },
        "policy": {
            "firm": "Decoded ByEnterStartShape starts are treated as firm script-start trigger evidence.",
            "candidate": "Manual/SameWithActive starts, incoming script-pointer refs, triggerVolumes, and UID chains are reported as candidate trigger evidence until action opcodes are named.",
            "runtimeChecks": "MissionRuntime property checks are reported as quest-gate evidence, not as script-start triggers.",
            "unknown": "Entries without source LevelScript files have no trigger evidence in this audit.",
        },
        "entries": rows,
    }


def format_refs(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    parts = []
    for row in rows[:3]:
        source = safe_text(row.get("sourceScript"))
        record = safe_text(row.get("record"))
        flag = row.get("pointerFlag")
        bit = source
        if record:
            bit += f" {record}"
        if flag is not None:
            bit += f" flag={flag}"
        if bit:
            parts.append(bit)
    return "; ".join(parts)


def format_runtime(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in rows[:3]:
        quest = safe_text(row.get("questId"))
        key = safe_text(row.get("key"))
        if quest or key:
            parts.append(f"{quest}:{key}={row.get('value')!r}")
    return "; ".join(parts)


def format_terminal_branches(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in rows[:3]:
        props = ",".join(str(value) for value in (row.get("propertyKeys") or [])[:2])
        refs = ",".join(str(value) for value in (row.get("branchLocalRefs") or [])[:4])
        target = row.get("targetLocalId")
        quest = ",".join(str(value) for value in (row.get("questIds") or [])[:2])
        bit = ""
        if props:
            bit += props
        if refs:
            bit += f" branches={refs}"
        if target is not None:
            bit += f" -> {target}"
        if quest:
            bit += f" {quest}"
        if bit:
            parts.append(bit.strip())
    return "; ".join(parts)


def format_md(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        f"# {payload.get('mission')} Play Trigger Audit",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Summary",
        "",
        f"- Entries: `{summary.get('entries')}`",
        f"- Source-backed entries: `{summary.get('sourceBackedEntries')}`",
        f"- Entries with recovered UID chains: `{summary.get('entriesWithUidChains')}`",
        f"- Entries with named play records: `{summary.get('entriesWithPlayRecords')}`",
        f"- UID chains without named play records: `{summary.get('entriesWithUidChainsWithoutPlayRecords')}`",
        f"- Chain heads in action-list roots: `{summary.get('entriesWithActionMapRootHeads')}`",
        f"- Chain heads outside serialized action map: `{summary.get('entriesWithOutsideChainHeads')}`",
        f"- Entries with terminal-branch evidence: `{summary.get('entriesWithTerminalBranchEvidence')}`",
        f"- Fallback entries without trigger source: `{summary.get('fallbackEntries')}`",
        f"- Script start status: `{summary.get('scriptStartStatusCounts')}`",
        "",
        "## Interpretation",
        "",
        "- Firm script-start trigger evidence means the script has decoded `ByEnterStartShape` start mode.",
        "- MissionRuntime property checks are quest gates: they prove a quest waits on a LevelScript property, but they do not by themselves start that script.",
        "- Candidate trigger evidence means the script/record chain is real, but the exact starter/action opcode is still unnamed.",
        "- A play-chain trigger is local to the LevelScript body; a script-start trigger explains how that LevelScript becomes active.",
        "- `actionList#N root` means the record is a top-level action node; it is not itself a start trigger unless the script-start trigger is also known.",
        "",
        "## Entries",
        "",
        "| # | key | script | start trigger | play-chain trigger | runtime check | terminal branch | incoming refs |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload.get("entries") or []:
        script = ""
        if row.get("levelId") or row.get("sourceScript"):
            script = f"{row.get('levelId', '')}/{row.get('sourceScript', '')}".strip("/")
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("index") or ""),
                    f"`{md_escape(row.get('key'))}`",
                    f"`{md_escape(script)}`" if script else "",
                    f"{md_escape(row.get('scriptStartStatus'))}: {md_escape(row.get('scriptStart'))}",
                    md_escape(row.get("recordTrigger")),
                    md_escape(format_runtime(row.get("runtimeConditions") or [])),
                    md_escape(format_terminal_branches(row.get("terminalBranchEvidence") or [])),
                    md_escape(format_refs(row.get("incomingScriptRefs") or [])),
                ]
            )
            + " |"
        )

    lines.extend([
        "",
        "## Chain Details",
        "",
    ])
    for row in payload.get("entries") or []:
        chain = (row.get("chain") or {}).get("chain") or []
        lines.append(f"### {row.get('index')}. `{md_escape(row.get('key'))}`")
        if not chain:
            lines.append("")
            lines.append("_No source UID chain recovered._")
            lines.append("")
            continue
        lines.append("")
        lines.append(f"- Script: `{md_escape(row.get('levelId'))}/{md_escape(row.get('sourceScript'))}`")
        lines.append(f"- Start: `{md_escape(row.get('scriptStartStatus'))}` {md_escape(row.get('scriptStart'))}")
        shape_summary = format_start_shapes(row.get("startShapeListShapes") or [])
        if shape_summary:
            lines.append(f"- Start shape detail: {md_escape(shape_summary)}")
        volume_summary = format_trigger_volumes(row.get("triggerVolumesDetails") or {})
        if volume_summary:
            lines.append(f"- Trigger volume detail: {md_escape(volume_summary)}")
        slot_record_summary = summarize_trigger_slot_records(row.get("triggerSlotRecords") or [])
        if slot_record_summary:
            lines.append(f"- Trigger slot records: {md_escape(slot_record_summary)}")
        terminal_branch_summary = format_terminal_branches(row.get("terminalBranchEvidence") or [])
        if terminal_branch_summary:
            lines.append(f"- Terminal branch: {md_escape(terminal_branch_summary)}")
        action_map = ((row.get("chain") or {}).get("actionMap") or {})
        action_map_status = safe_text(action_map.get("status") or row.get("actionMap"))
        action_map_count = action_map.get("recordCount", row.get("actionMapRecordCount"))
        if action_map_status:
            bit = action_map_status
            if action_map_count is not None:
                bit += f", {action_map_count} serialized action-list records"
            lines.append(f"- ActionMap: {md_escape(bit)}")
        lines.append(f"- Record trigger: {md_escape(row.get('recordTrigger'))}")
        lines.append("")
        lines.append("| local -> next | offset | actionMap | opcode | class | hint | decoded | strings | plain strings |")
        lines.append("| --- | ---: | --- | --- | --- | --- | --- | --- | --- |")
        for record in chain:
            local_next = f"{record.get('localId')} -> {record.get('nextId')}"
            opcode = f"{record.get('code')}/{record.get('kind')}"
            decoded_bits: list[str] = []
            decoded = record.get("decoded") or {}
            if isinstance(decoded, dict):
                if decoded.get("seconds") is not None:
                    decoded_bits.append(f"seconds={decoded.get('seconds')}")
                if decoded.get("guideId"):
                    decoded_bits.append(f"guide={decoded.get('guideId')}")
                if decoded.get("localRecordRefs"):
                    decoded_bits.append(
                        "refs=" + ",".join(str(value) for value in (decoded.get("localRecordRefs") or [])[:6])
                    )
                if decoded.get("branchLocalRefs"):
                    decoded_bits.append(
                        "branches="
                        + ",".join(str(value) for value in (decoded.get("branchLocalRefs") or [])[:6])
                    )
                pointer = decoded.get("scriptPointer") if isinstance(decoded.get("scriptPointer"), dict) else {}
                if pointer:
                    target = pointer.get("pointerScript")
                    flag = pointer.get("pointerFlag")
                    bit = f"scriptPtr={target}" if target else ""
                    if flag is not None:
                        bit += f" flag={flag}"
                    if bit:
                        decoded_bits.append(bit)
                if decoded.get("signalKeys"):
                    decoded_bits.append("signals=" + ",".join(str(value) for value in decoded.get("signalKeys")[:3]))
                if decoded.get("triggerSlotIds"):
                    slot_text = "slots=" + ",".join(str(value) for value in decoded.get("triggerSlotIds")[:6])
                    if decoded.get("triggerEventKind"):
                        slot_text += f" {decoded.get('triggerEventKind')}"
                    decoded_bits.append(slot_text)
                if decoded.get("propertyKeys"):
                    decoded_bits.append("props=" + ",".join(str(value) for value in decoded.get("propertyKeys")[:4]))
                if decoded.get("propertyOutputRefs"):
                    decoded_bits.append(
                        "propRefs="
                        + ",".join(
                            str((value or {}).get("ref") or value)
                            for value in decoded.get("propertyOutputRefs")[:4]
                        )
                    )
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{md_escape(local_next)}`",
                        f"`0x{int(record.get('start') or 0):x}`",
                        md_escape(record.get("actionMap") or ""),
                        f"`{md_escape(opcode)}`",
                        md_escape(record.get("class") or ""),
                        md_escape(record.get("hint") or ""),
                        md_escape("; ".join(decoded_bits)),
                        md_escape(", ".join(record.get("strings") or [])),
                        md_escape(", ".join(record.get("plainStrings") or [])),
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit recovered LevelScript trigger evidence for mission story entries.")
    parser.add_argument("--mission", default="e0m0")
    parser.add_argument("--language", default="CN")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args(argv)

    payload = build_audit(args.mission, args.language)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.mission}_play_trigger_audit.json"
    md_path = args.output_dir / f"{args.mission}_play_trigger_audit.md"
    write_report_json(json_path, payload)
    write_text_if_changed(md_path, format_md(payload))
    print(f"Play trigger audit: {md_path}")
    print(f"Play trigger data:  {json_path}")
    summary = payload.get("summary") or {}
    print(
        f"{args.mission}: entries={summary.get('entries')} "
        f"source={summary.get('sourceBackedEntries')} "
        f"chains={summary.get('entriesWithUidChains')} "
        f"playRecords={summary.get('entriesWithPlayRecords')} "
        f"fallback={summary.get('fallbackEntries')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
