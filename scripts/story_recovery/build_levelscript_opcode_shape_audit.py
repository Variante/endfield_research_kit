#!/usr/bin/env python3
"""Group LevelScript action records by opcode/payload shape.

This is a diagnostic bridge between raw LevelScriptData bytes and IL2CPP
`Beyond.Gameplay.Actions.*` classes. It does not promote any ordering edge.
Instead it answers: which opcode/kind records look like trigger events,
property events, property setters/gates, compact script pointers, or true
ManualStart/ManualEnd-style `levelId + scriptId` payloads?

Output:

    reports/mission_order/levelscript_opcode_shape_audit.json
    reports/mission_order/levelscript_opcode_shape_audit.md
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", _REPO_ROOT / "scripts" / "story_recovery"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402
from story_builder.context import LEVELSCRIPT_DIR  # noqa: E402
from story_builder.level_bindings import (  # noqa: E402
    _load_levelscript_binding_data,
    classify_levelscript_record,
)
from story_builder.levelscript_binary import (  # noqa: E402
    levelscript_action_map_membership,
    decode_levelscript_record_payload,
    _looks_like_property_key,
)

OUTPUT_DIR = ROOT / "reports" / "mission_order"
STORY_KEY_RE = re.compile(
    r"^(?:dlg|radio|cutscene|black|env|sns|remotecomm|misc_dlg|video_cs_video)_[A-Za-z0-9_]+$"
)
LOCAL_OUTPUT_RE = re.compile(r"^\$\d+@_[A-Za-z0-9_]+$")
HEX_UID_RE = re.compile(r"^[0-9a-f]{8}$", re.IGNORECASE)


TARGET_PROFILES = [
    {
        "name": "ManualStartLevelScript / ManualEndLevelScript",
        "expectedShape": "levelId string + scriptId in one action payload",
        "status": (
            "ActionBase tags are present as 0x02f1/0x0a and 0x02ec/0x0a; "
            "observed payloads do not carry literal target levelId+scriptId values"
        ),
    },
    {
        "name": "UpdateLevelScriptProperty / OperateLevelScriptNumber / SetLevelScriptDone",
        "expectedShape": "property key/path plus value or operation fields",
        "status": "unproven; scan property-key non-event opcode clusters",
    },
    {
        "name": "ScriptEvent.OnLeaderEnterTriggerVolume / OnLeaderLeaveTriggerVolume",
        "expectedShape": "trigger slot filter/output fields",
        "status": "named by derived ScriptEventHeader mapping: 0x12a1/0x00 and 0x12a3/0x00",
    },
    {
        "name": "ScriptEvent.OnPropertyChanged",
        "expectedShape": "property key plus oldValue/value outputs",
        "status": "named by derived ScriptEventHeader mapping: 0x13a5/0x00",
    },
]


def safe_text(value: Any) -> str:
    return str(value or "")


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def opcode_key(record: dict[str, Any]) -> str:
    code = record.get("code")
    kind = record.get("kind")
    if isinstance(code, int) and isinstance(kind, int):
        return f"0x{code:04x}/0x{kind:02x}"
    return "unknown"


def record_texts(record: dict[str, Any], decoded: dict[str, Any] | None = None) -> list[str]:
    out: list[str] = []
    decoded = decoded or {}
    for field in decoded.get("taggedFields") or []:
        if isinstance(field, dict) and field.get("type") == "string":
            text = safe_text(field.get("value"))
            if text and text not in out:
                out.append(text)
    for field in ("strings", "plainStrings"):
        for hit in record.get(field) or []:
            text = hit.get("text") if isinstance(hit, dict) else hit
            if isinstance(text, str) and text and text not in out:
                out.append(text)
    return out


def decoded_field_texts(decoded: dict[str, Any] | None) -> list[str]:
    out: list[str] = []
    for field in (decoded or {}).get("taggedFields") or []:
        if isinstance(field, dict) and field.get("type") == "string":
            text = safe_text(field.get("value"))
            if text and text not in out:
                out.append(text)
    return out


def text_category(text: str, level_ids: set[str]) -> str:
    if text in level_ids:
        return "level-id"
    if STORY_KEY_RE.match(text):
        return "story-key"
    if text.startswith("levelseq_"):
        return "levelseq"
    if text.startswith("guide_"):
        return "guide"
    if LOCAL_OUTPUT_RE.match(text):
        return "local-output"
    if text.startswith("#") and HEX_UID_RE.match(text[1:]):
        return "event-uid"
    if HEX_UID_RE.match(text):
        return "uid"
    if _looks_like_property_key(text):
        return "property-key"
    return "other"


def field_signature(fields: list[dict[str, Any]], level_ids: set[str]) -> str:
    parts: list[str] = []
    for field in fields[:8]:
        if field.get("type") == "string":
            parts.append("str:" + text_category(safe_text(field.get("value")), level_ids))
        elif field.get("type") == "scalar":
            if "u32" in field and field.get("u32") in {0, 1, 2, 3, 4, 5}:
                parts.append(f"scalar:{field.get('u32')}")
            elif "float" in field and field.get("float") not in {0, 1}:
                parts.append("scalar:float")
            else:
                parts.append("scalar")
        else:
            parts.append(safe_text(field.get("type")) or "?")
    return ",".join(parts) or "-"


def payload_window(data: bytes, record: dict[str, Any], next_start: int | None) -> bytes:
    payload_start = int(record.get("payloadStart", record.get("start", 0)) or 0)
    if payload_start < 0 or payload_start >= len(data):
        return b""
    end = next_start if isinstance(next_start, int) and next_start > payload_start else len(data)
    return data[payload_start:end]


def prepare_level_script_id_bytes(level_ids: set[str]) -> dict[str, list[tuple[str, bytes, bytes]]]:
    out: dict[str, list[tuple[str, bytes, bytes]]] = {}
    for level_id in level_ids:
        level_dir = LEVELSCRIPT_DIR / level_id
        rows: list[tuple[str, bytes, bytes]] = []
        if level_dir.is_dir():
            for path in level_dir.glob("*.json"):
                if not path.stem.isdigit():
                    continue
                value = int(path.stem)
                rows.append((path.stem, struct.pack("<I", value & 0xFFFFFFFF), struct.pack("<Q", value)))
        out[level_id] = rows
    return out


def action_map_roles(data: bytes, records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[int, str]]:
    return levelscript_action_map_membership(data, records)


def compact_sample(
    *,
    level_id: str,
    file_stem: str,
    file_path: str,
    record: dict[str, Any],
    decoded: dict[str, Any],
    texts: list[str],
    action_role: str,
    manual_like: list[dict[str, Any]],
) -> dict[str, Any]:
    pointer = decoded.get("scriptPointer") if isinstance(decoded.get("scriptPointer"), dict) else {}
    row = {
        "levelId": level_id,
        "scriptId": file_stem,
        "file": file_path,
        "offset": f"0x{int(record.get('start') or 0):x}",
        "localId": record.get("localId"),
        "nextId": record.get("nextId"),
        "actionMap": action_role,
        "class": classify_levelscript_record(record) or "",
        "hint": decoded.get("label") or "",
        "confidence": decoded.get("confidence") or "",
        "texts": texts[:10],
        "propertyKeys": decoded.get("propertyKeys") or [],
        "propertyOutputs": decoded.get("propertyOutputRefs") or [],
        "triggerSlots": decoded.get("triggerSlotIds") or [],
        "gateLocalRefs": decoded.get("gateLocalRefs") or [],
        "compactGate": decoded.get("compactGate") or {},
        "branchLocalRefs": decoded.get("branchLocalRefs") or [],
        "levelScriptControlRole": decoded.get("levelScriptControlRole") or "",
        "manualControl": decoded.get("manualControl") or {},
        "triggerEventKind": decoded.get("triggerEventKind") or "",
        "propertyEventKind": decoded.get("propertyEventKind") or "",
        "scriptPointer": pointer,
        "manualLikeTargets": manual_like,
        "payloadHexPrefix": decoded.get("payloadHexPrefix") or "",
    }
    return {key: value for key, value in row.items() if value not in ("", None, [], {})}


def find_manual_like_targets(
    *,
    texts: list[str],
    payload: bytes,
    level_ids: set[str],
    script_id_bytes: dict[str, list[tuple[str, bytes, bytes]]],
) -> list[dict[str, Any]]:
    level_texts = [text for text in texts if text in level_ids]
    if not level_texts:
        return []
    search_payload = payload[:256]
    hits: list[dict[str, Any]] = []
    for level_id in level_texts:
        for script_id, raw_u32, raw_u64 in script_id_bytes.get(level_id, []):
            if script_id in texts or raw_u32 in search_payload or raw_u64 in search_payload:
                hits.append({"levelId": level_id, "scriptId": script_id})
                if len(hits) >= 12:
                    return hits
    return hits


def increment_values(counter: Counter[str], values: list[Any], *, limit: int = 20) -> None:
    for value in values[:limit]:
        text = safe_text(value)
        if text:
            counter[text] += 1


def build_audit(*, sample_limit: int, level_filter: str | None = None) -> dict[str, Any]:
    level_ids = {
        path.name
        for path in LEVELSCRIPT_DIR.iterdir()
        if path.is_dir() and (not level_filter or path.name == level_filter)
    }
    script_id_bytes = prepare_level_script_id_bytes(level_ids)

    opcode_stats: dict[str, dict[str, Any]] = {}
    totals = Counter()
    target_counters: dict[str, Counter[str]] = {
        "triggerEventOpcodes": Counter(),
        "propertyEventOpcodes": Counter(),
        "propertyKeyNonEventOpcodes": Counter(),
        "scriptPointerOpcodes": Counter(),
        "manualControlOpcodes": Counter(),
        "levelIdTextOpcodes": Counter(),
        "manualLikeOpcodes": Counter(),
        "outsideLevelIdScriptIdOpcodes": Counter(),
    }
    manual_like_rows: list[dict[str, Any]] = []
    outside_level_script_rows: list[dict[str, Any]] = []
    level_id_text_rows: list[dict[str, Any]] = []

    for level_id in sorted(level_ids):
        binding = _load_levelscript_binding_data(level_id)
        totals["levels"] += 1
        for file_info in binding.get("files") or []:
            file_path_text = safe_text(file_info.get("file"))
            file_path = Path(file_path_text)
            if not file_path.is_absolute():
                file_path = ROOT / file_path
            try:
                data = file_path.read_bytes()
            except OSError:
                data = b""
            records = sorted(file_info.get("records") or [], key=lambda row: int(row.get("start") or 0))
            if not records:
                continue
            totals["files"] += 1
            header, action_roles = action_map_roles(data, records)
            if header.get("status") == "present":
                totals["filesWithActionMap"] += 1
                if isinstance(header.get("recordCount"), int):
                    totals["actionMapRecordTotal"] += int(header.get("recordCount") or 0)
                for list_name, count in (header.get("listCounts") or {}).items():
                    if isinstance(count, int):
                        totals[f"{list_name}RecordTotal"] += count
                        totals["serializedActionMapRecordTotal"] += count
            starts = [int(record.get("start") or 0) for record in records]

            for index, record in enumerate(records):
                next_start = starts[index + 1] if index + 1 < len(starts) else None
                decoded = decode_levelscript_record_payload(data, record, next_start=next_start)
                texts = record_texts(record, decoded)
                field_texts = decoded_field_texts(decoded)
                key = opcode_key(record)
                payload = payload_window(data, record, next_start)
                level_id_texts = [text for text in texts if text in level_ids]
                manual_like = find_manual_like_targets(
                    texts=field_texts,
                    payload=payload,
                    level_ids=level_ids,
                    script_id_bytes=script_id_bytes,
                )
                action_role = action_roles.get(int(record.get("start") or 0), "outside")
                sample = compact_sample(
                    level_id=level_id,
                    file_stem=safe_text(Path(file_path_text).stem),
                    file_path=repo_rel(file_path),
                    record=record,
                    decoded=decoded,
                    texts=texts,
                    action_role=action_role,
                    manual_like=manual_like,
                )
                is_action_map_record = action_role.startswith("actionList#")

                stat = opcode_stats.setdefault(
                    key,
                    {
                        "opcode": key,
                        "count": 0,
                        "actionMapRoles": Counter(),
                        "classes": Counter(),
                        "hints": Counter(),
                        "confidences": Counter(),
                        "fieldSignatures": Counter(),
                        "textCategories": Counter(),
                        "propertyRoles": Counter(),
                        "triggerEventKinds": Counter(),
                        "propertyEventKinds": Counter(),
                        "propertyKeys": Counter(),
                        "triggerSlots": Counter(),
                        "scriptPointerTargets": Counter(),
                        "levelIdTexts": Counter(),
                        "manualLikeTargets": Counter(),
                        "payloadLengthMin": None,
                        "payloadLengthMax": 0,
                        "samples": [],
                    },
                )
                totals["records"] += 1
                stat["count"] += 1
                stat["actionMapRoles"][action_role] += 1
                record_class = classify_levelscript_record(record) or "unknown"
                stat["classes"][record_class] += 1
                hint = safe_text(decoded.get("label")) or "unknown"
                stat["hints"][hint] += 1
                confidence = safe_text(decoded.get("confidence")) or "unknown"
                stat["confidences"][confidence] += 1
                stat["fieldSignatures"][field_signature(decoded.get("taggedFields") or [], level_ids)] += 1
                for text in texts:
                    category = text_category(text, level_ids)
                    stat["textCategories"][category] += 1
                    if category == "level-id":
                        stat["levelIdTexts"][text] += 1
                if decoded.get("propertyRole"):
                    stat["propertyRoles"][safe_text(decoded.get("propertyRole"))] += 1
                if decoded.get("triggerEventKind"):
                    stat["triggerEventKinds"][safe_text(decoded.get("triggerEventKind"))] += 1
                    target_counters["triggerEventOpcodes"][key] += 1
                if decoded.get("propertyEventKind"):
                    stat["propertyEventKinds"][safe_text(decoded.get("propertyEventKind"))] += 1
                    target_counters["propertyEventOpcodes"][key] += 1
                if decoded.get("levelScriptControlRole"):
                    target_counters["manualControlOpcodes"][key] += 1
                property_texts = list(decoded.get("propertyKeys") or [])
                for text in texts:
                    if _looks_like_property_key(text) and text not in property_texts:
                        property_texts.append(text)
                increment_values(stat["propertyKeys"], property_texts)
                if property_texts and not decoded.get("propertyEventKind"):
                    target_counters["propertyKeyNonEventOpcodes"][key] += 1
                for value in decoded.get("triggerSlotIds") or []:
                    stat["triggerSlots"][str(value)] += 1
                pointer = decoded.get("scriptPointer") if isinstance(decoded.get("scriptPointer"), dict) else {}
                if pointer:
                    target = safe_text(pointer.get("pointerScript"))
                    if target:
                        stat["scriptPointerTargets"][target] += 1
                    target_counters["scriptPointerOpcodes"][key] += 1
                for target in manual_like:
                    target_text = f"{target.get('levelId')}/{target.get('scriptId')}"
                    stat["manualLikeTargets"][target_text] += 1
                if level_id_texts:
                    target_counters["levelIdTextOpcodes"][key] += 1
                if manual_like and is_action_map_record:
                    target_counters["manualLikeOpcodes"][key] += 1
                elif manual_like:
                    target_counters["outsideLevelIdScriptIdOpcodes"][key] += 1
                payload_len = len(payload)
                stat["payloadLengthMin"] = (
                    payload_len
                    if stat["payloadLengthMin"] is None
                    else min(int(stat["payloadLengthMin"]), payload_len)
                )
                stat["payloadLengthMax"] = max(int(stat["payloadLengthMax"]), payload_len)
                if len(stat["samples"]) < sample_limit:
                    stat["samples"].append(sample)
                if manual_like and is_action_map_record and len(manual_like_rows) < 100:
                    manual_like_rows.append({"opcode": key, **sample})
                elif manual_like and len(outside_level_script_rows) < 100:
                    outside_level_script_rows.append({"opcode": key, **sample})
                elif any(text in level_ids for text in texts) and len(level_id_text_rows) < 100:
                    level_id_text_rows.append({"opcode": key, **sample})

    rows: list[dict[str, Any]] = []
    for stat in opcode_stats.values():
        row = {
            "opcode": stat["opcode"],
            "count": stat["count"],
            "actionMapRoles": dict(stat["actionMapRoles"].most_common()),
            "classes": dict(stat["classes"].most_common(8)),
            "hints": dict(stat["hints"].most_common(8)),
            "confidences": dict(stat["confidences"].most_common(8)),
            "fieldSignatures": dict(stat["fieldSignatures"].most_common(10)),
            "textCategories": dict(stat["textCategories"].most_common(10)),
            "propertyRoles": dict(stat["propertyRoles"].most_common(8)),
            "triggerEventKinds": dict(stat["triggerEventKinds"].most_common(4)),
            "propertyEventKinds": dict(stat["propertyEventKinds"].most_common(4)),
            "propertyKeys": dict(stat["propertyKeys"].most_common(12)),
            "triggerSlots": dict(stat["triggerSlots"].most_common(12)),
            "scriptPointerTargets": dict(stat["scriptPointerTargets"].most_common(12)),
            "levelIdTexts": dict(stat["levelIdTexts"].most_common(8)),
            "manualLikeTargets": dict(stat["manualLikeTargets"].most_common(8)),
            "payloadLengthMin": stat["payloadLengthMin"],
            "payloadLengthMax": stat["payloadLengthMax"],
            "samples": stat["samples"],
        }
        rows.append({key: value for key, value in row.items() if value not in (None, "", [], {})})
    rows.sort(key=lambda row: (-int(row.get("count") or 0), safe_text(row.get("opcode"))))

    target_findings = {
        name: dict(counter.most_common(20))
        for name, counter in target_counters.items()
    }
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceRoot": repo_rel(LEVELSCRIPT_DIR),
        "targetProfiles": TARGET_PROFILES,
        "summary": {
            "levels": totals["levels"],
            "files": totals["files"],
            "filesWithActionMap": totals["filesWithActionMap"],
            "records": totals["records"],
            "distinctOpcodes": len(rows),
            "actionMapRecordTotal": totals["actionMapRecordTotal"],
            "serializedActionMapRecordTotal": totals["serializedActionMapRecordTotal"],
            "actionListRecordTotal": totals["actionListRecordTotal"],
            "getterListRecordTotal": totals["getterListRecordTotal"],
            "headerListRecordTotal": totals["headerListRecordTotal"],
            "manualLikeRows": len(manual_like_rows),
            "outsideLevelIdScriptIdRowsSampled": len(outside_level_script_rows),
            "levelIdTextRowsSampled": len(level_id_text_rows),
        },
        "targetFindings": target_findings,
        "manualLikeRows": manual_like_rows,
        "outsideLevelIdScriptIdRows": outside_level_script_rows,
        "levelIdTextRows": level_id_text_rows,
        "opcodeRows": rows,
    }


def short_counts(values: dict[str, Any], limit: int = 6) -> str:
    if not values:
        return ""
    return ", ".join(f"{key}:{value}" for key, value in list(values.items())[:limit])


def markdown_report(payload: dict[str, Any], *, top_opcodes: int) -> str:
    summary = payload.get("summary") or {}
    target_findings = payload.get("targetFindings") or {}
    lines = [
        "# LevelScript Opcode Shape Audit",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Summary",
        "",
        f"- Levels scanned: `{summary.get('levels')}`",
        f"- Files scanned: `{summary.get('files')}` (`{summary.get('filesWithActionMap')}` with decoded actionMap headers)",
        f"- Records scanned: `{summary.get('records')}`",
        f"- Distinct opcode/kind pairs: `{summary.get('distinctOpcodes')}`",
        (
            f"- Serialized action-map records: `{summary.get('serializedActionMapRecordTotal')}` "
            f"(action `{summary.get('actionListRecordTotal')}`, getter `{summary.get('getterListRecordTotal')}`, "
            f"header `{summary.get('headerListRecordTotal')}`)"
        ),
        f"- Action-list ManualStart-like `levelId+scriptId` rows found: `{summary.get('manualLikeRows')}`",
        f"- Residual outside-map `levelId+scriptId` rows sampled: `{summary.get('outsideLevelIdScriptIdRowsSampled')}`",
        "",
        "## Interpretation",
        "",
        "- This report groups raw LevelScript records by payload shape; it does not promote mission order edges.",
        "- The serialized `ActionSerializedMap` order is decoded as `actionList`, `getterList`, then `headerList` from GameAssembly setter dispatch, MetadataRegistration type resolution, and the dedicated action-map list audit. Two-block files can omit an empty getterList; header-shaped final blocks are inferred as `headerList`, keeping derived ScriptEventHeader-band rows out of `getterList` in the current scan.",
        "- `manualLikeRows=0` means no scanned action-list record carried both an exact level id and a target script id in the same payload.",
        "- Residual outside-map `levelId+scriptId` rows are retained as reference/data-shape diagnostics, not ManualStart candidates.",
        "- Property-key non-event rows are the next setter/gate candidate pool; property-change event rows are listeners, not setters.",
        "",
        "## Target Profiles",
        "",
        "| target | expected shape | current status |",
        "| --- | --- | --- |",
    ]
    for profile in payload.get("targetProfiles") or []:
        lines.append(
            f"| {md_escape(profile.get('name'))} "
            f"| {md_escape(profile.get('expectedShape'))} "
            f"| {md_escape(profile.get('status'))} |"
        )

    lines.extend([
        "",
        "## Target Findings",
        "",
        "| bucket | top opcode clusters |",
        "| --- | --- |",
    ])
    for key in (
        "triggerEventOpcodes",
        "propertyEventOpcodes",
        "propertyKeyNonEventOpcodes",
        "scriptPointerOpcodes",
        "manualControlOpcodes",
        "levelIdTextOpcodes",
        "manualLikeOpcodes",
        "outsideLevelIdScriptIdOpcodes",
    ):
        lines.append(f"| `{key}` | `{md_escape(short_counts(target_findings.get(key) or {}, 12))}` |")

    lines.extend([
        "",
        "## ManualStart-like ActionMap Rows",
        "",
    ])
    manual_like = payload.get("manualLikeRows") or []
    if manual_like:
        lines.extend([
            "| opcode | file | offset | class | hint | targets | texts |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ])
        for row in manual_like[:30]:
            targets = ", ".join(
                f"{target.get('levelId')}/{target.get('scriptId')}"
                for target in row.get("manualLikeTargets") or []
            )
            lines.append(
                f"| `{md_escape(row.get('opcode'))}` "
                f"| `{md_escape(row.get('file'))}` "
                f"| `{md_escape(row.get('offset'))}` "
                f"| {md_escape(row.get('class'))} "
                f"| {md_escape(row.get('hint'))} "
                f"| `{md_escape(targets)}` "
                f"| `{md_escape(', '.join(row.get('texts') or []))}` |"
            )
    else:
        lines.append("_No true `levelId+scriptId` action payloads found._")

    outside_rows = payload.get("outsideLevelIdScriptIdRows") or []
    lines.extend([
        "",
        "## Residual Outside-map LevelScript References",
        "",
    ])
    if outside_rows:
        lines.extend([
            "| opcode | file | offset | targets | texts |",
            "| --- | --- | ---: | --- | --- |",
        ])
        for row in outside_rows[:30]:
            targets = ", ".join(
                f"{target.get('levelId')}/{target.get('scriptId')}"
                for target in row.get("manualLikeTargets") or []
            )
            lines.append(
                f"| `{md_escape(row.get('opcode'))}` "
                f"| `{md_escape(row.get('file'))}` "
                f"| `{md_escape(row.get('offset'))}` "
                f"| `{md_escape(targets)}` "
                f"| `{md_escape(', '.join(row.get('texts') or []))}` |"
            )
    else:
        lines.append("_No residual outside-map `levelId+scriptId` payloads sampled._")

    lines.extend([
        "",
        "## Top Opcode Shapes",
        "",
        "| opcode | count | actionMap | classes | hints | fields | text cats | props/events | samples |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in (payload.get("opcodeRows") or [])[:top_opcodes]:
        prop_bits = []
        if row.get("propertyRoles"):
            prop_bits.append("roles " + short_counts(row.get("propertyRoles") or {}, 3))
        if row.get("propertyEventKinds"):
            prop_bits.append("propEvt " + short_counts(row.get("propertyEventKinds") or {}, 3))
        if row.get("triggerEventKinds"):
            prop_bits.append("trigEvt " + short_counts(row.get("triggerEventKinds") or {}, 3))
        if row.get("scriptPointerTargets"):
            prop_bits.append("ptr " + short_counts(row.get("scriptPointerTargets") or {}, 3))
        sample_text = "; ".join(
            f"{Path(safe_text(sample.get('file'))).name}@{sample.get('offset')}"
            for sample in (row.get("samples") or [])[:3]
        )
        lines.append(
            f"| `{md_escape(row.get('opcode'))}` "
            f"| {row.get('count')} "
            f"| `{md_escape(short_counts(row.get('actionMapRoles') or {}, 4))}` "
            f"| `{md_escape(short_counts(row.get('classes') or {}, 4))}` "
            f"| `{md_escape(short_counts(row.get('hints') or {}, 4))}` "
            f"| `{md_escape(short_counts(row.get('fieldSignatures') or {}, 3))}` "
            f"| `{md_escape(short_counts(row.get('textCategories') or {}, 5))}` "
            f"| `{md_escape('; '.join(prop_bits))}` "
            f"| `{md_escape(sample_text)}` |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", default=None, help="Optional LevelScriptData level id to scan.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--sample-limit", type=int, default=4)
    parser.add_argument("--top-opcodes", type=int, default=80)
    args = parser.parse_args()

    payload = build_audit(sample_limit=max(0, args.sample_limit), level_filter=args.level)
    suffix = f"_{args.level}" if args.level else ""
    json_path = args.output_dir / f"levelscript_opcode_shape_audit{suffix}.json"
    md_path = args.output_dir / f"levelscript_opcode_shape_audit{suffix}.md"
    write_report_json(json_path, payload)
    write_text_if_changed(md_path, markdown_report(payload, top_opcodes=max(1, args.top_opcodes)))
    print(f"LevelScript opcode shape audit: {json_path}")
    print(f"LevelScript opcode shape report: {md_path}")
    summary = payload.get("summary") or {}
    print(
        f"records={summary.get('records')} opcodes={summary.get('distinctOpcodes')} "
        f"manualLikeRows={summary.get('manualLikeRows')}"
    )


if __name__ == "__main__":
    main()
