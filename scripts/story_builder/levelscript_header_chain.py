#!/usr/bin/env python3
"""Audit LevelScript header events and the action chains they trigger.

The ActionSerializedMap recovery gives us three physical lists (their storage
layout is not a chronology):

    actionList -> getterList -> headerList

The current GameAssembly builds a last-serialized indexed runtime slot table
for each list. This report asks the next playback question: when an active
named headerList event has
a `nextId`, does it resolve to an actionList row, and does that action chain
contain a cutscene/radio/dialog/levelseq play action?

Output:

    reports/mission_order/levelscript_header_chain_audit.json
    reports/mission_order/levelscript_header_chain_audit.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402
from story_builder.context import LEVELSCRIPT_DIR  # noqa: E402
from story_builder.level_bindings import (  # noqa: E402
    LEVELSCRIPT_NATIVE_INDEXED_SLOT_MAPPING_ID,
    _prepare_levelscript_native_control_context,
    _levelscript_file_sort_key,
    _load_levelscript_binding_data,
    classify_levelscript_record,
)
from story_builder.levelscript_binary import (  # noqa: E402
    classify_local_trigger_volume_context,
    decode_levelscript_binary_summary,
    decode_levelscript_record_payload,
    levelscript_action_map_membership,
    LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
    LEVELSCRIPT_NATIVE_HEADER_NAMES,
)

REPORT_DIR = ROOT / "reports" / "mission_order"
DEFAULT_MAPPING = (
    ROOT / "reports" / "story" / "recovery" / "memorypack_union_formatter_tag_audit.json"
)
PLAY_CLASSES = {"play_cutscene", "play_radio", "play_dialog", "play_levelseq"}
SCENE_PREFIXES = ("cutscene_", "radio_", "dlg_", "misc_dlg_", "levelseq_", "video_cs_video_")


def safe_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


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


def record_start(record: dict[str, Any]) -> int:
    return int(record.get("start") or 0)


def record_texts(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for field in ("strings", "plainStrings"):
        for hit in record.get(field) or []:
            text = safe_text(hit.get("text") if isinstance(hit, dict) else hit)
            if text and text not in out:
                out.append(text)
    return out


def scene_texts(records: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for record in records:
        for text in record_texts(record):
            if text.startswith(SCENE_PREFIXES) and text not in out:
                out.append(text)
    return out


def load_header_mapping(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("derivedOpcodeMappings") or []:
        if not isinstance(row, dict):
            continue
        opcode = safe_text(row.get("opcode"))
        if not opcode:
            continue
        candidates[opcode].append(row)

    out: dict[str, dict[str, Any]] = {}
    for opcode, rows in candidates.items():
        rows.sort(
            key=lambda row: (
                not safe_text(row.get("band")).startswith("action-header-bank-"),
                -int(row.get("headerListCount") or 0),
                safe_text(row.get("band")),
            )
        )
        best = rows[0]
        out[opcode] = {
            "headerName": safe_text(best.get("headerName")),
            "headerBand": safe_text(best.get("band")),
            "headerTagHex": safe_text(best.get("headerTagHex")),
            "headerBaseCodeHex": safe_text(best.get("baseCodeHex")),
            "crossCheckBands": [
                safe_text(row.get("band"))
                for row in rows[1:]
                if safe_text(row.get("band"))
            ],
        }
    for (code, kind), header_name in LEVELSCRIPT_NATIVE_HEADER_NAMES.items():
        opcode = f"0x{code:04x}/0x{kind:02x}"
        out[opcode] = {
            "headerName": header_name,
            "headerBand": "current-native-actionheader",
            "headerTagHex": f"0x{code & 0xff:02x}",
            "headerBaseCodeHex": "",
            "crossCheckBands": [],
            "nativeMappingId": LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
        }
    return out


def next_start_by_record(records: list[dict[str, Any]], data_len: int) -> dict[int, int | None]:
    out: dict[int, int | None] = {}
    sorted_records = sorted(records, key=record_start)
    for index, record in enumerate(sorted_records):
        out[record_start(record)] = (
            record_start(sorted_records[index + 1])
            if index + 1 < len(sorted_records)
            else data_len
        )
    return out


def unique_by_local_id(records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        local_id = record.get("localId")
        if isinstance(local_id, int):
            buckets[local_id].append(record)
    return {
        local_id: bucket[0]
        for local_id, bucket in buckets.items()
        if len(bucket) == 1
    }


def records_by_local_id(records: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        local_id = record.get("localId")
        if isinstance(local_id, int):
            buckets[local_id].append(record)
    return dict(buckets)


def compact_record(
    record: dict[str, Any],
    *,
    data: bytes,
    next_starts: dict[int, int | None],
    membership: dict[int, str],
) -> dict[str, Any]:
    decoded = decode_levelscript_record_payload(
        data,
        record,
        next_start=next_starts.get(record_start(record)),
        action_map_role=safe_text(membership.get(record_start(record))),
    )
    row = {
        "localId": record.get("localId"),
        "recordNextId": record.get("nextId"),
        "offset": f"0x{record_start(record):x}",
        "opcode": opcode_key(record),
        "actionMap": membership.get(record_start(record), "outside"),
        "class": classify_levelscript_record(record),
        "hint": decoded.get("label") or "",
        "texts": record_texts(record)[:8],
    }
    action_header = decoded.get("actionHeader") if isinstance(decoded.get("actionHeader"), dict) else {}
    if action_header:
        row["actionHeaderNextId"] = action_header.get("nextId")
    return {key: value for key, value in row.items() if value not in ("", None, [], {})}


def follow_action_chain(
    start_record: dict[str, Any],
    *,
    action_by_local: dict[int, dict[str, Any]],
    max_steps: int = 32,
) -> tuple[list[dict[str, Any]], str]:
    chain: list[dict[str, Any]] = []
    seen: set[int] = set()
    current: dict[str, Any] | None = start_record
    status = "complete"
    while current is not None:
        local_id = current.get("localId")
        if not isinstance(local_id, int):
            status = "missing-local-id"
            break
        if local_id in seen:
            status = "loop"
            break
        seen.add(local_id)
        chain.append(current)
        if len(chain) >= max_steps:
            status = "truncated"
            break
        next_id = current.get("nextId")
        if not isinstance(next_id, int) or next_id < 0:
            break
        current = action_by_local.get(next_id)
        if current is None:
            status = "next-outside-action-list"
            break
    return chain, status


def iter_level_ids(selected: list[str]) -> list[str]:
    if selected:
        return list(dict.fromkeys(selected))
    if not LEVELSCRIPT_DIR.is_dir():
        return []
    return [
        path.name
        for path in sorted(LEVELSCRIPT_DIR.iterdir(), key=lambda p: p.name)
        if path.is_dir()
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    header_mapping = load_header_mapping(args.mapping)
    levels = iter_level_ids(args.level)
    event_rows: list[dict[str, Any]] = []
    stats = Counter()
    by_event: dict[str, Counter] = defaultdict(Counter)
    samples_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved_samples: list[dict[str, Any]] = []
    play_samples: list[dict[str, Any]] = []

    for level_id in levels:
        info = _load_levelscript_binding_data(level_id)
        files = sorted(
            info.get("files") or [],
            key=lambda row: _levelscript_file_sort_key(Path(safe_text(row.get("file")))),
        )
        for file_info in files:
            records = sorted(file_info.get("records") or [], key=record_start)
            if not records:
                continue
            rel_file = safe_text(file_info.get("file"))
            path = ROOT / rel_file
            try:
                data = path.read_bytes()
            except OSError:
                continue
            action_map, membership = levelscript_action_map_membership(data, records)
            if action_map.get("status") != "present":
                continue

            next_starts = next_start_by_record(records, len(data))
            action_records = [
                record for record in records
                if safe_text(membership.get(record_start(record))).startswith("actionList")
            ]
            runtime_context = _prepare_levelscript_native_control_context(
                data,
                records,
                membership,
            )
            action_by_local = runtime_context.get("actionByLocal") or {}
            action_buckets = runtime_context.get("actionBuckets") or {}
            all_buckets = records_by_local_id(records)
            all_by_local = unique_by_local_id(records)
            header_records = [
                record for record in records
                if safe_text(membership.get(record_start(record))).startswith("headerList")
            ]
            header_by_local = runtime_context.get("headerByLocal") or {}
            binary_summary: dict[str, Any] | None = None
            active_header_records = sorted(
                header_by_local.values(),
                key=record_start,
            )
            shadowed_actions = (
                runtime_context.get("runtimeShadowedRecordOffsets") or {}
            )
            shadowed_headers = (
                runtime_context.get("runtimeShadowedHeaderRecordOffsets") or {}
            )
            shadowed_getters = (
                runtime_context.get("runtimeShadowedGetterRecordOffsets") or {}
            )
            stats["filesWithActionMap"] += 1
            if header_records:
                stats["filesWithHeaderRows"] += 1
            stats["physicalHeaderRows"] += len(header_records)
            stats["shadowedActionRows"] += sum(
                len(offsets) for offsets in shadowed_actions.values()
            )
            stats["shadowedHeaderRows"] += sum(
                len(offsets) for offsets in shadowed_headers.values()
            )
            stats["shadowedGetterRows"] += sum(
                len(offsets) for offsets in shadowed_getters.values()
            )
            for header in active_header_records:
                stats["headerRows"] += 1
                opcode = opcode_key(header)
                mapping = header_mapping.get(opcode, {})
                header_name = safe_text(mapping.get("headerName"))
                if header_name:
                    stats["namedHeaderRows"] += 1
                decoded_header = decode_levelscript_record_payload(
                    data,
                    header,
                    next_start=next_starts.get(record_start(header)),
                    action_map_role=safe_text(membership.get(record_start(header))),
                )
                action_header = (
                    decoded_header.get("actionHeader")
                    if isinstance(decoded_header.get("actionHeader"), dict)
                    else {}
                )
                event_detail = (
                    decoded_header.get("nativeEventDetail")
                    if isinstance(decoded_header.get("nativeEventDetail"), dict)
                    else {}
                )
                local_trigger_context: dict[str, Any] = {}
                trigger_slot_id = event_detail.get("triggerSlotIdFilter")
                script_id = safe_text(file_info.get("fileStem"))
                if (
                    isinstance(trigger_slot_id, int)
                    and not isinstance(trigger_slot_id, bool)
                    and trigger_slot_id > 0
                    and script_id.isdigit()
                ):
                    if binary_summary is None:
                        binary_summary = decode_levelscript_binary_summary(
                            data, int(script_id)
                        )
                    local_trigger_context = classify_local_trigger_volume_context(
                        binary_summary,
                        [trigger_slot_id],
                    )
                if isinstance(action_header.get("priority"), int):
                    stats[f"priority:{action_header['priority']}"] += 1
                header_next_id = action_header.get("nextId")
                target_local_id = (
                    header_next_id
                    if isinstance(header_next_id, int)
                    else header.get("nextId")
                )
                target_source = "actionHeader.nextId" if isinstance(header_next_id, int) else "record.nextId"
                target = action_by_local.get(target_local_id) if isinstance(target_local_id, int) else None
                fallback_target = all_by_local.get(target_local_id) if isinstance(target_local_id, int) else None
                action_candidates = action_buckets.get(target_local_id, []) if isinstance(target_local_id, int) else []
                all_candidates = all_buckets.get(target_local_id, []) if isinstance(target_local_id, int) else []
                if target:
                    stats["headersTargetingActionList"] += 1
                    target_status = "action-list"
                elif fallback_target:
                    stats["headersTargetingNonActionList"] += 1
                    target_status = "non-action-list"
                elif len(all_candidates) > 1:
                    stats["headersTargetingAmbiguousNonActionList"] += 1
                    target_status = "ambiguous-non-action-list"
                elif isinstance(target_local_id, int) and target_local_id >= 0:
                    stats["headersWithMissingTarget"] += 1
                    target_status = "missing"
                else:
                    stats["headersWithoutNextTarget"] += 1
                    target_status = "no-next"

                chain: list[dict[str, Any]] = []
                chain_status = ""
                compact_chain: list[dict[str, Any]] = []
                play_records: list[dict[str, Any]] = []
                scenes: list[str] = []
                if target:
                    chain, chain_status = follow_action_chain(target, action_by_local=action_by_local)
                    compact_chain = [
                        compact_record(record, data=data, next_starts=next_starts, membership=membership)
                        for record in chain
                    ]
                    play_records = [
                        record for record in chain
                        if classify_levelscript_record(record) in PLAY_CLASSES
                    ]
                    scenes = scene_texts(chain)
                    if play_records:
                        stats["headersWithPlayActionInTargetChain"] += 1
                    if scenes:
                        stats["headersWithSceneTextInTargetChain"] += 1

                event_key = header_name or opcode
                by_event[event_key]["count"] += 1
                by_event[event_key]["named"] += 1 if header_name else 0
                by_event[event_key]["targetsActionList"] += 1 if target else 0
                by_event[event_key]["targetsAmbiguousActionList"] += 1 if target_status == "ambiguous-action-list" else 0
                by_event[event_key]["targetsNonActionList"] += 1 if target_status == "non-action-list" else 0
                by_event[event_key]["targetsAmbiguousNonActionList"] += 1 if target_status == "ambiguous-non-action-list" else 0
                by_event[event_key]["missingTarget"] += 1 if target_status == "missing" else 0
                by_event[event_key]["playChains"] += 1 if play_records else 0
                by_event[event_key]["sceneTextChains"] += 1 if scenes else 0

                row = {
                    "levelId": level_id,
                    "sourceScript": safe_text(file_info.get("fileStem")),
                    "file": rel_file,
                    "header": compact_record(header, data=data, next_starts=next_starts, membership=membership),
                    "headerName": header_name,
                    "headerBand": mapping.get("headerBand") or "",
                    "headerTagHex": mapping.get("headerTagHex") or "",
                    "crossCheckBands": mapping.get("crossCheckBands") or [],
                    "targetSource": target_source,
                    "targetLocalId": target_local_id,
                    "recordNextId": header.get("nextId"),
                    "actionHeader": action_header,
                    "eventDetail": event_detail,
                    "localTriggerVolumeContext": local_trigger_context,
                    "runtimeSlotStatus": "active-final-serialized-slot",
                    "runtimeShadowedHeaderRecordOffsets": (
                        shadowed_headers.get(header.get("localId")) or []
                    ),
                    "runtimeSlotMappingId": (
                        LEVELSCRIPT_NATIVE_INDEXED_SLOT_MAPPING_ID
                    ),
                    "targetStatus": target_status,
                    "targetAction": (
                        compact_record(target, data=data, next_starts=next_starts, membership=membership)
                        if target
                        else compact_record(fallback_target, data=data, next_starts=next_starts, membership=membership)
                        if fallback_target
                        else {}
                    ),
                    "targetCandidates": [
                        compact_record(candidate, data=data, next_starts=next_starts, membership=membership)
                        for candidate in action_candidates[:6]
                    ] if target_status == "ambiguous-action-list" else [],
                    "chainStatus": chain_status,
                    "chainLength": len(chain),
                    "playActions": [
                        compact_record(record, data=data, next_starts=next_starts, membership=membership)
                        for record in play_records
                    ],
                    "sceneTexts": scenes[:12],
                    "chain": compact_chain[: args.chain_preview],
                }
                row = {key: value for key, value in row.items() if value not in ("", None, [], {})}
                event_rows.append(row)

                if len(samples_by_event[event_key]) < args.samples_per_event:
                    samples_by_event[event_key].append(row)
                if play_records and len(play_samples) < args.play_samples:
                    play_samples.append(row)
                if (not target or not play_records) and len(unresolved_samples) < args.unresolved_samples:
                    unresolved_samples.append(row)

    event_summary = []
    for event_key, counter in by_event.items():
        sample = samples_by_event.get(event_key, [])
        event_summary.append(
            {
                "event": event_key,
                "count": counter.get("count", 0),
                "targetsActionList": counter.get("targetsActionList", 0),
                "targetsAmbiguousActionList": counter.get("targetsAmbiguousActionList", 0),
                "targetsNonActionList": counter.get("targetsNonActionList", 0),
                "targetsAmbiguousNonActionList": counter.get("targetsAmbiguousNonActionList", 0),
                "missingTarget": counter.get("missingTarget", 0),
                "playChains": counter.get("playChains", 0),
                "sceneTextChains": counter.get("sceneTextChains", 0),
                "samples": [
                    {
                        "levelId": row.get("levelId"),
                        "sourceScript": row.get("sourceScript"),
                        "file": row.get("file"),
                        "targetStatus": row.get("targetStatus"),
                        "sceneTexts": row.get("sceneTexts") or [],
                        "header": row.get("header") or {},
                        "targetAction": row.get("targetAction") or {},
                    }
                    for row in sample
                ],
            }
        )
    event_summary.sort(
        key=lambda row: (
            -int(row.get("playChains") or 0),
            -int(row.get("targetsActionList") or 0),
            -int(row.get("count") or 0),
            safe_text(row.get("event")),
        )
    )
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settings": {
            "levelFilter": levels if args.level else [],
            "mapping": repo_rel(args.mapping),
            "chainPreview": args.chain_preview,
        },
        "summary": {
            "levelsScanned": len(levels),
            "filesWithActionMap": stats.get("filesWithActionMap", 0),
            "filesWithHeaderRows": stats.get("filesWithHeaderRows", 0),
            "physicalHeaderRows": stats.get("physicalHeaderRows", 0),
            "headerRows": stats.get("headerRows", 0),
            "runtimeShadowedActionRows": stats.get("shadowedActionRows", 0),
            "runtimeShadowedHeaderRows": stats.get("shadowedHeaderRows", 0),
            "runtimeShadowedGetterRows": stats.get("shadowedGetterRows", 0),
            "eventPriorityCounts": {
                key.removeprefix("priority:"): value
                for key, value in sorted(stats.items())
                if key.startswith("priority:")
            },
            "runtimeSlotMappingId": LEVELSCRIPT_NATIVE_INDEXED_SLOT_MAPPING_ID,
            "namedHeaderRows": stats.get("namedHeaderRows", 0),
            "headersTargetingActionList": stats.get("headersTargetingActionList", 0),
            "headersTargetingAmbiguousActionList": stats.get("headersTargetingAmbiguousActionList", 0),
            "headersTargetingNonActionList": stats.get("headersTargetingNonActionList", 0),
            "headersTargetingAmbiguousNonActionList": stats.get("headersTargetingAmbiguousNonActionList", 0),
            "headersWithMissingTarget": stats.get("headersWithMissingTarget", 0),
            "headersWithoutNextTarget": stats.get("headersWithoutNextTarget", 0),
            "headersWithPlayActionInTargetChain": stats.get("headersWithPlayActionInTargetChain", 0),
            "headersWithSceneTextInTargetChain": stats.get("headersWithSceneTextInTargetChain", 0),
            "distinctHeaderEvents": len(event_summary),
        },
        "eventSummary": event_summary,
        "playSamples": play_samples,
        "unresolvedSamples": unresolved_samples,
        "headerRows": event_rows,
    }


def short_counts(row: dict[str, Any]) -> str:
    ambiguous = int(row.get("targetsAmbiguousActionList") or 0)
    ambiguous_text = f"; {ambiguous} ambiguous action targets" if ambiguous else ""
    return (
        f"{row.get('targetsActionList', 0)}/{row.get('count', 0)} target actionList{ambiguous_text}; "
        f"{row.get('playChains', 0)} play chains; "
        f"{row.get('sceneTextChains', 0)} scene-text chains"
    )


def format_compact_action(row: dict[str, Any]) -> str:
    if not row:
        return ""
    parts = [
        safe_text(row.get("actionMap")),
        safe_text(row.get("opcode")),
        safe_text(row.get("class")),
        safe_text(row.get("hint")),
    ]
    texts = row.get("texts") or []
    if texts:
        parts.append(", ".join(str(text) for text in texts[:3]))
    return " ".join(part for part in parts if part)


def format_sample_ref(row: dict[str, Any]) -> str:
    script = "/".join(part for part in (safe_text(row.get("levelId")), safe_text(row.get("sourceScript"))) if part)
    scenes = ", ".join(str(text) for text in (row.get("sceneTexts") or [])[:4])
    target = format_compact_action(row.get("targetAction") or {})
    if not target and row.get("targetCandidates"):
        target = "candidates: " + "; ".join(
            format_compact_action(candidate)
            for candidate in (row.get("targetCandidates") or [])[:3]
        )
    bits = [script, safe_text(row.get("targetStatus")), target]
    if scenes:
        bits.append(scenes)
    return "; ".join(bit for bit in bits if bit)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("summary") or {}
    lines = [
        "# LevelScript Header Chain Audit",
        "",
        "## Summary",
        "",
        f"- Levels scanned: `{summary.get('levelsScanned')}`",
        f"- Files with ActionSerializedMap: `{summary.get('filesWithActionMap')}`",
        f"- Files with header rows: `{summary.get('filesWithHeaderRows')}`",
        f"- Physical header rows: `{summary.get('physicalHeaderRows')}`",
        f"- Active indexed header slots: `{summary.get('headerRows')}`",
        f"- Runtime-shadowed rows (action/header/getter): `{summary.get('runtimeShadowedActionRows')}` / `{summary.get('runtimeShadowedHeaderRows')}` / `{summary.get('runtimeShadowedGetterRows')}`",
        f"- Authored event priority counts: `{json.dumps(summary.get('eventPriorityCounts') or {}, sort_keys=True)}`",
        f"- Header rows named by MemoryPack-derived mapping: `{summary.get('namedHeaderRows')}`",
        f"- Headers targeting actionList rows by `nextId`: `{summary.get('headersTargetingActionList')}`",
        f"- Headers targeting duplicate/ambiguous actionList local ids by `nextId`: `{summary.get('headersTargetingAmbiguousActionList')}`",
        f"- Headers targeting non-action rows by `nextId`: `{summary.get('headersTargetingNonActionList')}`",
        f"- Headers targeting duplicate/ambiguous non-action local ids by `nextId`: `{summary.get('headersTargetingAmbiguousNonActionList')}`",
        f"- Headers with missing/nonexistent positive `nextId`: `{summary.get('headersWithMissingTarget')}`",
        f"- Headers without a positive `nextId`: `{summary.get('headersWithoutNextTarget')}`",
        f"- Headers whose target chain contains a named play action: `{summary.get('headersWithPlayActionInTargetChain')}`",
        f"- Headers whose target chain carries scene-like text: `{summary.get('headersWithSceneTextInTargetChain')}`",
        f"- Distinct header events/opcodes: `{summary.get('distinctHeaderEvents')}`",
        "",
        "## Interpretation",
        "",
        "- `headerList`, `actionList`, and `getterList` share one current-binary runtime rule: each list is enumerated in serialized order into an array indexed by local ID, so the last serialized record owns a repeated slot.",
        "- Active `headerList` slots are independently invoked event/listener roots. Physical list order and authored `priority` values are listener metadata, not Story chronology.",
        "- A positive payload `ActionHeader.nextId` that resolves into the active `actionList` slot is a direct event-to-action edge.",
        "- A target chain with a named play action is the strongest recovered evidence for how a scene/radio/dialog/levelseq can be fired by original LevelScript data.",
        "- Rows without play actions still matter: they often gate state, properties, spawners, or scripted callbacks before another action path becomes active.",
        "",
        "## Event Summary",
        "",
        "| event/opcode | count | coverage | first samples |",
        "| --- | ---: | --- | --- |",
    ]
    for row in (payload.get("eventSummary") or [])[:80]:
        samples = "; ".join(format_sample_ref(sample) for sample in (row.get("samples") or [])[:3])
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{md_escape(row.get('event'))}`",
                    str(row.get("count") or 0),
                    md_escape(short_counts(row)),
                    md_escape(samples),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Play Samples", ""])
    play_samples = payload.get("playSamples") or []
    if play_samples:
        lines.append("| header | script | source | target | play actions | scene texts |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for row in play_samples:
            header = row.get("header") or {}
            script = "/".join(part for part in (safe_text(row.get("levelId")), safe_text(row.get("sourceScript"))) if part)
            play_actions = "; ".join(format_compact_action(action) for action in row.get("playActions") or [])
            scenes = ", ".join(str(text) for text in (row.get("sceneTexts") or [])[:6])
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_escape(row.get("headerName") or header.get("opcode") or ""),
                        f"`{md_escape(script)}`",
                        md_escape(row.get("targetSource") or ""),
                        md_escape(format_compact_action(row.get("targetAction") or {})),
                        md_escape(play_actions),
                        md_escape(scenes),
                    ]
                )
                + " |"
            )
    else:
        lines.append("- No header-triggered play samples were found.")

    lines.extend(["", "## Unresolved Samples", ""])
    unresolved = payload.get("unresolvedSamples") or []
    if unresolved:
        lines.append("| header | script | source | target status | target | chain status | scene texts |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in unresolved:
            header = row.get("header") or {}
            script = "/".join(part for part in (safe_text(row.get("levelId")), safe_text(row.get("sourceScript"))) if part)
            scenes = ", ".join(str(text) for text in (row.get("sceneTexts") or [])[:6])
            target_text = format_compact_action(row.get("targetAction") or {})
            if not target_text and row.get("targetCandidates"):
                target_text = "candidates: " + "; ".join(
                    format_compact_action(candidate)
                    for candidate in (row.get("targetCandidates") or [])[:3]
                )
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_escape(row.get("headerName") or header.get("opcode") or ""),
                        f"`{md_escape(script)}`",
                        md_escape(row.get("targetSource") or ""),
                        md_escape(row.get("targetStatus") or ""),
                        md_escape(target_text),
                        md_escape(row.get("chainStatus") or ""),
                        md_escape(scenes),
                    ]
                )
                + " |"
            )
    else:
        lines.append("- No unresolved samples captured.")
    write_text_if_changed(path, "\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit LevelScript headerList event edges into actionList chains.")
    parser.add_argument("--level", action="append", default=[], help="Limit to one LevelScript level id; can be repeated.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--chain-preview", type=int, default=10)
    parser.add_argument("--samples-per-event", type=int, default=3)
    parser.add_argument("--play-samples", type=int, default=40)
    parser.add_argument("--unresolved-samples", type=int, default=40)
    args = parser.parse_args(argv)

    payload = build_report(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "levelscript_header_chain_audit"
    if args.level:
        stem += "_" + "_".join(level.replace("/", "_").replace("\\", "_") for level in args.level)
    json_path = args.output_dir / f"{stem}.json"
    md_path = args.output_dir / f"{stem}.md"
    write_report_json(json_path, payload)
    write_markdown(md_path, payload)
    summary = payload.get("summary") or {}
    print(f"wrote {repo_rel(json_path)} and {repo_rel(md_path)}")
    print(
        "headerRows={headerRows} named={namedHeaderRows} "
        "targetAction={headersTargetingActionList} "
        "ambiguousAction={headersTargetingAmbiguousActionList} "
        "playChains={headersWithPlayActionInTargetChain}".format(**summary)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
