#!/usr/bin/env python3
"""Rank LevelScript property setter/gate candidates from bridge evidence.

`build_levelscript_property_flow_audit.py` proves that some
MissionRuntime property checks point at a concrete LevelScript file and that
the checked key is physically present in that file. This follow-up audit asks
the narrower question: when the key is inside a UID action record, what local
chain/opcode shape looks like the authored setter or gate?

The output is diagnostic only. It deliberately does not promote any scene
ordering edge until an opcode has repeated chain evidence and a decoded
runtime class.

Output:

    reports/mission_order/levelscript_property_setter_candidates_CN.json
    reports/mission_order/levelscript_property_setter_candidates_CN.md
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", _REPO_ROOT / "scripts" / "story_recovery"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402
from build_levelscript_property_flow_audit import build_audit as build_property_flow_audit  # noqa: E402
from story_builder.level_bindings import (  # noqa: E402
    _build_uid_record_chains,
    _levelscript_record_for_offset,
    _load_levelscript_binding_data,
    classify_levelscript_record,
)
from story_builder.levelscript_binary import (  # noqa: E402
    levelscript_action_map_membership,
    decode_levelscript_record_payload,
)

REPORT_DIR = ROOT / "reports" / "mission_order"
PROPERTY_FLOW_PATH = REPORT_DIR / "levelscript_property_flow_CN.json"

STORY_PREFIXES = (
    "dlg_",
    "misc_dlg_",
    "radio_",
    "cutscene_",
    "black_",
    "remotecomm_",
    "sns_",
    "video_cs_video_",
)
DONE_KEY_RE = re.compile(
    r"(?:done|finish|finished|succeed|succceed|clear|played|fixed|picked|looked|touched|triggered|solved|ok)$",
    re.IGNORECASE,
)
NOISY_TEXT_PREFIXES = ("$", "#", "LD/", "au_", "chr_", "guide_", "levelseq_")


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
    return ""


def record_texts(record: dict[str, Any], decoded: dict[str, Any] | None = None) -> list[str]:
    out: list[str] = []
    for field in (decoded or {}).get("taggedFields") or []:
        if isinstance(field, dict) and field.get("type") == "string":
            text = safe_text(field.get("value"))
            if text and text not in out:
                out.append(text)
    for field in ("strings", "plainStrings"):
        for hit in record.get(field) or []:
            text = safe_text(hit.get("text") if isinstance(hit, dict) else hit)
            if text and text not in out:
                out.append(text)
    return out


def story_refs(texts: list[str]) -> list[str]:
    out: list[str] = []
    for text in texts:
        if text.startswith(STORY_PREFIXES) and text not in out:
            out.append(text)
    return out


def meaningful_texts(texts: list[str]) -> list[str]:
    out: list[str] = []
    for text in texts:
        if not text or text.isdigit() or len(text) > 96:
            continue
        if any(text.startswith(prefix) for prefix in NOISY_TEXT_PREFIXES):
            continue
        if text not in out:
            out.append(text)
    return out[:12]


def next_start_by_record_start(records: list[dict[str, Any]], data_len: int) -> dict[int, int | None]:
    starts: dict[int, int | None] = {}
    sorted_records = sorted(records, key=lambda row: int(row.get("start") or 0))
    for index, record in enumerate(sorted_records):
        start = int(record.get("start") or 0)
        starts[start] = (
            int(sorted_records[index + 1].get("start") or data_len)
            if index + 1 < len(sorted_records)
            else None
        )
    return starts


def action_map_record_metadata(
    data: bytes,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[int, int], dict[int, str]]:
    header, membership_by_start = levelscript_action_map_membership(data, records)
    return header, {}, membership_by_start


def compact_record(
    record: dict[str, Any],
    *,
    data: bytes,
    next_start: int | None,
    action_index_by_start: dict[int, int],
    action_role_by_start: dict[int, str],
) -> dict[str, Any]:
    start = int(record.get("start") or 0)
    decoded = decode_levelscript_record_payload(data, record, next_start=next_start) if data else {}
    texts = record_texts(record, decoded)
    action_role = action_role_by_start.get(start)
    action_map = action_role or "outside"
    row = {
        "offset": f"0x{start:x}",
        "start": start,
        "uid": safe_text(record.get("uid")),
        "localId": record.get("localId"),
        "nextId": record.get("nextId"),
        "opcode": opcode_key(record),
        "class": classify_levelscript_record(record) or "",
        "actionMap": action_map,
        "hint": safe_text(decoded.get("label")),
        "confidence": safe_text(decoded.get("confidence")),
        "propertyRole": safe_text(decoded.get("propertyRole")),
        "propertyEventKind": safe_text(decoded.get("propertyEventKind")),
        "triggerEventKind": safe_text(decoded.get("triggerEventKind")),
        "propertyKeys": decoded.get("propertyKeys") or [],
        "propertyOutputs": decoded.get("propertyOutputRefs") or [],
        "triggerSlots": decoded.get("triggerSlotIds") or [],
        "branchLocalRefs": decoded.get("branchLocalRefs") or [],
        "storyRefs": story_refs(texts),
        "texts": meaningful_texts(texts),
        "decodedFields": (decoded.get("taggedFields") or [])[:6],
    }
    return {key: value for key, value in row.items() if value not in ("", None, [], {})}


def relation_to_story(record_index: int, story_indexes: list[int]) -> str:
    if not story_indexes:
        return "no-story-in-chain"
    if record_index in story_indexes:
        return "same-record-as-story"
    before = [idx for idx in story_indexes if idx < record_index]
    after = [idx for idx in story_indexes if idx > record_index]
    if before and after:
        return "between-story-records"
    if before:
        return "after-story"
    return "before-story"


def expected_values(row: dict[str, Any]) -> list[Any]:
    values: list[Any] = []
    for checker in row.get("checkers") or []:
        if not isinstance(checker, dict):
            continue
        value = checker.get("expectedValue")
        if value not in values:
            values.append(value)
    return values


def score_candidate(
    *,
    record: dict[str, Any],
    key: str,
    relation: str,
    expected: list[Any],
) -> tuple[int, list[str], str]:
    score = 0
    reasons: list[str] = []
    candidate_kind = "property-key-reference"
    if key in (record.get("texts") or []) or key in (record.get("propertyKeys") or []):
        score += 20
        reasons.append("record carries checked key")
    if record.get("propertyEventKind"):
        score -= 12
        reasons.append("property-change listener, not setter")
        candidate_kind = "listener"
    elif record.get("propertyRole"):
        role = str(record.get("propertyRole") or "")
        if role == "property-setter":
            score += 12
            reasons.append("decoded ActionBase property setter")
            candidate_kind = "decoded-property-setter"
        elif role == "property-list-clear":
            score += 2
            reasons.append("decoded list-clear target, not setter")
            candidate_kind = "property-list-clear"
        elif role == "property-key-terminal":
            score += 5
            reasons.append("decoded terminal/completion bridge")
            if record.get("branchLocalRefs"):
                score += 4
                reasons.append("carries local branch refs")
            candidate_kind = "terminal-bridge"
        else:
            score += 6
            reasons.append(f"decoded {role}")
            candidate_kind = "property-action"
    if record.get("class") == "set_state":
        score += 6
        reasons.append("known set_state class")
        candidate_kind = "state-action"
    if safe_text(record.get("actionMap")) != "outside":
        score += 4
        reasons.append("inside serialized action map")
    else:
        score -= 2
        reasons.append("outside serialized action map")
    if relation == "after-story":
        score += 8
        reasons.append("after story record in same chain")
        if candidate_kind not in {"listener", "property-list-clear"}:
            candidate_kind = "post-story-setter-candidate"
    elif relation == "same-record-as-story":
        score += 6
        reasons.append("same record as story text")
        if candidate_kind not in {"listener", "property-list-clear"}:
            candidate_kind = "story-adjacent-property-action"
    elif relation == "between-story-records":
        score += 5
        reasons.append("between story records")
        if candidate_kind not in {"listener", "property-list-clear"}:
            candidate_kind = "inter-story-property-action"
    elif relation == "before-story":
        score += 3
        reasons.append("before story record in same chain")
        if candidate_kind not in {"listener", "property-list-clear"}:
            candidate_kind = "pre-story-gate-candidate"
    if True in expected and DONE_KEY_RE.search(key):
        score += 3
        reasons.append("done/clear-style key checked for true")
    if record.get("propertyOutputs"):
        score -= 4
        reasons.append("has property output refs")
    if safe_text(record.get("actionMap")) == "outside":
        # Serialized tail objects can legitimately co-store property names and
        # Story ids, but they are not ActionSerializedMap records.  Keep the
        # occurrence visible for format research while failing closed against
        # presenting it as a setter/action candidate.
        score -= 20
        reasons.append("serialized tail co-occurrence is not executable action evidence")
        candidate_kind = "serialized-tail-cooccurrence"
    return score, reasons, candidate_kind


def find_file_info(level_id: str, script_id: str) -> dict[str, Any] | None:
    binding = _load_levelscript_binding_data(level_id)
    return next(
        (row for row in binding.get("files") or [] if safe_text(row.get("fileStem")) == script_id),
        None,
    )


def key_matches_record(record: dict[str, Any], key: str, decoded: dict[str, Any]) -> bool:
    texts = record_texts(record, decoded)
    if key in texts:
        return True
    return key in (decoded.get("propertyKeys") or [])


def record_window(
    records: list[dict[str, Any]],
    target_start: int,
    *,
    radius: int = 3,
) -> list[dict[str, Any]]:
    starts = [int(record.get("start") or 0) for record in records]
    try:
        index = starts.index(target_start)
    except ValueError:
        return []
    return records[max(0, index - radius) : min(len(records), index + radius + 1)]


def analyze_bridge_row(row: dict[str, Any]) -> dict[str, Any]:
    level_id = safe_text(row.get("mapId"))
    script_id = safe_text(row.get("scriptId"))
    key = safe_text(row.get("key"))
    file_info = find_file_info(level_id, script_id)
    base = {
        "mapId": level_id,
        "scriptId": script_id,
        "key": key,
        "checkerCount": row.get("checkerCount"),
        "checkerMissions": row.get("checkerMissions") or [],
        "checkerStoryRefs": row.get("checkerStoryRefs") or [],
        "expectedValues": expected_values(row),
        "bridgeStatus": row.get("bridgeStatus"),
    }
    if not file_info:
        return {**base, "status": "missing-levelscript-binding"}

    file_path = Path(safe_text(file_info.get("file")))
    if not file_path.is_absolute():
        file_path = ROOT / file_path
    try:
        data = file_path.read_bytes()
    except OSError:
        data = b""
    records = sorted(file_info.get("records") or [], key=lambda item: int(item.get("start") or 0))
    if not records or not data:
        return {
            **base,
            "status": "no-uid-records",
            "file": repo_rel(file_path),
            "firstKeyOffset": (row.get("lsDetect") or {}).get("firstLengthPrefixedOffset"),
        }

    next_by_start = next_start_by_record_start(records, len(data))
    action_header, action_index_by_start, action_role_by_start = action_map_record_metadata(data, records)
    chains = _build_uid_record_chains(records)
    chain_by_start: dict[int, tuple[int, int]] = {}
    for chain_index, chain in enumerate(chains):
        for record_index, record in enumerate(chain):
            chain_by_start[int(record.get("start") or 0)] = (chain_index, record_index)

    key_records: list[dict[str, Any]] = []
    for record in records:
        start = int(record.get("start") or 0)
        decoded = decode_levelscript_record_payload(data, record, next_start=next_by_start.get(start))
        if key_matches_record(record, key, decoded):
            key_records.append(record)

    first_key_offset = (row.get("lsDetect") or {}).get("firstLengthPrefixedOffset")
    outside_key_record: dict[str, Any] | None = None
    if not key_records and isinstance(first_key_offset, int):
        outside_key_record = _levelscript_record_for_offset(records, first_key_offset, len(data))

    candidate_rows: list[dict[str, Any]] = []
    chain_rows: list[dict[str, Any]] = []

    for key_record in key_records:
        key_start = int(key_record.get("start") or 0)
        chain_pos = chain_by_start.get(key_start)
        if chain_pos:
            chain_index, key_index = chain_pos
            chain = chains[chain_index]
            chain_records = chain
        else:
            chain_index, key_index = -1, -1
            chain_records = record_window(records, key_start)

        compact_chain = [
            compact_record(
                record,
                data=data,
                next_start=next_by_start.get(int(record.get("start") or 0)),
                action_index_by_start=action_index_by_start,
                action_role_by_start=action_role_by_start,
            )
            for record in chain_records
        ]
        story_indexes = [
            index
            for index, compact in enumerate(compact_chain)
            if compact.get("storyRefs")
        ]
        relation = relation_to_story(key_index if key_index >= 0 else 0, story_indexes)
        story_texts: list[str] = []
        for compact in compact_chain:
            for ref in compact.get("storyRefs") or []:
                if ref not in story_texts:
                    story_texts.append(ref)

        compact_key = compact_record(
            key_record,
            data=data,
            next_start=next_by_start.get(key_start),
            action_index_by_start=action_index_by_start,
            action_role_by_start=action_role_by_start,
        )
        score, reasons, candidate_kind = score_candidate(
            record=compact_key,
            key=key,
            relation=relation,
            expected=base["expectedValues"],
        )
        candidate = {
            "score": score,
            "candidateKind": candidate_kind,
            "relationToStory": relation,
            "reasons": reasons,
            "record": compact_key,
            "chainIndex": chain_index if chain_index >= 0 else None,
            "recordIndex": key_index if key_index >= 0 else None,
            "chainStoryRefs": story_texts[:12],
        }
        candidate_rows.append({key_: value for key_, value in candidate.items() if value not in (None, "", [], {})})
        chain_rows.append({
            "chainIndex": chain_index if chain_index >= 0 else None,
            "keyRecordOffset": compact_key.get("offset"),
            "relationToStory": relation,
            "storyRefs": story_texts[:12],
            "chain": compact_chain[:24],
        })

    candidate_rows.sort(key=lambda item: (-int(item.get("score") or 0), safe_text((item.get("record") or {}).get("offset"))))
    action_candidates = [
        item
        for item in candidate_rows
        if item.get("candidateKind") != "serialized-tail-cooccurrence"
    ]

    return {
        **base,
        "status": "analyzed",
        "file": repo_rel(file_path),
        "actionMap": {
            "status": action_header.get("status") or "",
            "recordCount": action_header.get("recordCount"),
            "listCounts": action_header.get("listCounts") or {},
        },
        "firstKeyOffset": first_key_offset,
        "exactKeyRecordCount": len(key_records),
        "offsetOnlyContainingRecord": (
            compact_record(
                outside_key_record,
                data=data,
                next_start=next_by_start.get(int(outside_key_record.get("start") or 0)),
                action_index_by_start=action_index_by_start,
                action_role_by_start=action_role_by_start,
            )
            if outside_key_record is not None
            else {}
        ),
        "candidateCount": len(action_candidates),
        "serializedTailObservationCount": len(candidate_rows) - len(action_candidates),
        "bestCandidate": action_candidates[0] if action_candidates else {},
        "candidates": candidate_rows,
        "chains": chain_rows[:8],
    }


def load_property_flow(language: str, *, refresh: bool) -> dict[str, Any]:
    path = REPORT_DIR / f"levelscript_property_flow_{language}.json"
    if not refresh:
        payload = read_json(path, {})
        if isinstance(payload, dict) and payload.get("rows"):
            return payload
        if language == "CN":
            payload = read_json(PROPERTY_FLOW_PATH, {})
            if isinstance(payload, dict) and payload.get("rows"):
                return payload
    return build_property_flow_audit()


def aggregate_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_opcode: dict[str, dict[str, Any]] = {}
    for row in rows:
        for candidate in row.get("candidates") or []:
            if candidate.get("candidateKind") == "serialized-tail-cooccurrence":
                continue
            record = candidate.get("record") or {}
            opcode = safe_text(record.get("opcode")) or "unknown"
            bucket = by_opcode.setdefault(
                opcode,
                {
                    "opcode": opcode,
                    "candidateCount": 0,
                    "bridgeTriples": set(),
                    "missions": set(),
                    "scoreTotal": 0,
                    "maxScore": None,
                    "candidateKinds": Counter(),
                    "relations": Counter(),
                    "classes": Counter(),
                    "hints": Counter(),
                    "propertyRoles": Counter(),
                    "actionMap": Counter(),
                    "storyAdjacent": 0,
                    "listenerCount": 0,
                    "examples": [],
                },
            )
            bucket["candidateCount"] += 1
            bucket["bridgeTriples"].add(f"{row.get('mapId')}/{row.get('scriptId')}/{row.get('key')}")
            for mission in row.get("checkerMissions") or []:
                bucket["missions"].add(mission)
            score = int(candidate.get("score") or 0)
            bucket["scoreTotal"] += score
            bucket["maxScore"] = score if bucket["maxScore"] is None else max(bucket["maxScore"], score)
            bucket["candidateKinds"][safe_text(candidate.get("candidateKind")) or "unknown"] += 1
            bucket["relations"][safe_text(candidate.get("relationToStory")) or "unknown"] += 1
            bucket["classes"][safe_text(record.get("class")) or "unknown"] += 1
            bucket["hints"][safe_text(record.get("hint")) or "unknown"] += 1
            bucket["propertyRoles"][safe_text(record.get("propertyRole")) or "unknown"] += 1
            bucket["actionMap"][safe_text(record.get("actionMap")) or ""] += 1
            if candidate.get("relationToStory") != "no-story-in-chain":
                bucket["storyAdjacent"] += 1
            if candidate.get("candidateKind") == "listener":
                bucket["listenerCount"] += 1
            if len(bucket["examples"]) < 8:
                bucket["examples"].append({
                    "mapId": row.get("mapId"),
                    "scriptId": row.get("scriptId"),
                    "key": row.get("key"),
                    "missions": row.get("checkerMissions") or [],
                    "score": score,
                    "relation": candidate.get("relationToStory"),
                    "offset": record.get("offset"),
                    "branchLocalRefs": record.get("branchLocalRefs") or [],
                    "storyRefs": candidate.get("chainStoryRefs") or [],
                })

    out: list[dict[str, Any]] = []
    for bucket in by_opcode.values():
        out.append({
            "opcode": bucket["opcode"],
            "candidateCount": bucket["candidateCount"],
            "bridgeTripleCount": len(bucket["bridgeTriples"]),
            "missionCount": len(bucket["missions"]),
            "scoreTotal": bucket["scoreTotal"],
            "maxScore": bucket["maxScore"],
            "storyAdjacent": bucket["storyAdjacent"],
            "listenerCount": bucket["listenerCount"],
            "candidateKinds": dict(bucket["candidateKinds"].most_common()),
            "relations": dict(bucket["relations"].most_common()),
            "classes": dict(bucket["classes"].most_common(6)),
            "hints": dict(bucket["hints"].most_common(6)),
            "propertyRoles": dict(bucket["propertyRoles"].most_common(6)),
            "actionMap": dict(bucket["actionMap"].most_common(6)),
            "examples": bucket["examples"],
        })
    out.sort(key=lambda item: (
        -int(item.get("storyAdjacent") or 0),
        -int(item.get("scoreTotal") or 0),
        -int(item.get("candidateCount") or 0),
        safe_text(item.get("opcode")),
    ))
    return out


def build_audit(*, language: str, refresh_property_flow: bool) -> dict[str, Any]:
    property_flow = load_property_flow(language, refresh=refresh_property_flow)
    source_rows = [
        row
        for row in property_flow.get("rows") or []
        if isinstance(row, dict) and row.get("bridgeStatus") == "bridgeFound"
    ]
    analyzed_rows = [analyze_bridge_row(row) for row in source_rows]
    aggregate_rows = aggregate_candidates(analyzed_rows)
    status_counts = Counter(safe_text(row.get("status")) for row in analyzed_rows)
    best_kind_counts = Counter(
        safe_text((row.get("bestCandidate") or {}).get("candidateKind")) or "none"
        for row in analyzed_rows
    )
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "propertyFlowReport": repo_rel(REPORT_DIR / f"levelscript_property_flow_{language}.json"),
            "propertyFlowGenerated": property_flow.get("generated") or "",
            "propertyFlowSummary": property_flow.get("summary") or {},
        },
        "summary": {
            "bridgeFoundTriples": len(source_rows),
            "analyzedRows": len(analyzed_rows),
            "statusCounts": dict(status_counts.most_common()),
            "rowsWithExactKeyRecords": sum(1 for row in analyzed_rows if row.get("exactKeyRecordCount")),
            "rowsWithOffsetOnlyContainingRecords": sum(
                1 for row in analyzed_rows if row.get("offsetOnlyContainingRecord")
            ),
            "candidateObservations": sum(int(row.get("candidateCount") or 0) for row in analyzed_rows),
            "storyAdjacentCandidateObservations": sum(
                1
                for row in analyzed_rows
                for candidate in row.get("candidates") or []
                if (
                    candidate.get("candidateKind") != "serialized-tail-cooccurrence"
                    and candidate.get("relationToStory") != "no-story-in-chain"
                )
            ),
            "serializedTailObservations": sum(
                int(row.get("serializedTailObservationCount") or 0)
                for row in analyzed_rows
            ),
            "bestCandidateKinds": dict(best_kind_counts.most_common()),
            "opcodeCandidateCount": len(aggregate_rows),
        },
        "evidenceClassification": {
            "isOrderingSource": True,
            "isPromotable": False,
            "reason": (
                "This audit ranks local property-key action records that are bridged from "
                "MissionRuntime property checks, but setter semantics are still inferred "
                "from chain position and payload shape. Promote only after a repeated "
                "opcode is matched to an IL2CPP action class or another independent "
                "runtime edge."
            ),
        },
        "opcodeCandidates": aggregate_rows,
        "rows": analyzed_rows,
    }


def short_counts(values: dict[str, Any], limit: int = 5) -> str:
    if not values:
        return ""
    return ", ".join(f"{key}:{value}" for key, value in list(values.items())[:limit])


def markdown_report(payload: dict[str, Any], *, top_rows: int) -> str:
    summary = payload.get("summary") or {}
    source = payload.get("source") or {}
    lines = [
        "# LevelScript Property Setter Candidate Audit",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Summary",
        "",
        f"- Source property-flow report: `{md_escape(source.get('propertyFlowReport'))}`",
        f"- Bridge-found triples analyzed: `{summary.get('bridgeFoundTriples')}`",
        f"- Rows with exact UID key records: `{summary.get('rowsWithExactKeyRecords')}`",
        f"- Rows with offset-only containing records: `{summary.get('rowsWithOffsetOnlyContainingRecords')}`",
        f"- Candidate observations: `{summary.get('candidateObservations')}`",
        f"- Story-adjacent candidate observations: `{summary.get('storyAdjacentCandidateObservations')}`",
        f"- Non-executable serialized-tail observations: `{summary.get('serializedTailObservations')}`",
        f"- Status counts: `{summary.get('statusCounts')}`",
        f"- Best candidate kinds: `{summary.get('bestCandidateKinds')}`",
        "",
        "## Evidence Classification",
        "",
        f"- `isOrderingSource`: `{payload['evidenceClassification']['isOrderingSource']}`",
        f"- `isPromotable`: `{payload['evidenceClassification']['isPromotable']}`",
        f"- Reason: {payload['evidenceClassification']['reason']}",
        "",
        "## Opcode Candidate Ranking",
        "",
        "| opcode | candidates | triples | story-adjacent | max score | kinds | relations | hints | examples |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    opcode_rows = payload.get("opcodeCandidates") or []
    if not opcode_rows:
        lines.append("| _(none)_ | 0 | 0 | 0 | 0 |  |  |  |  |")
    for row in opcode_rows:
        examples = "; ".join(
            f"{ex.get('mapId')}/{ex.get('scriptId')}:{ex.get('key')}@{ex.get('offset')}"
            for ex in (row.get("examples") or [])[:3]
        )
        lines.append(
            f"| `{md_escape(row.get('opcode'))}` "
            f"| {row.get('candidateCount')} "
            f"| {row.get('bridgeTripleCount')} "
            f"| {row.get('storyAdjacent')} "
            f"| {row.get('maxScore')} "
            f"| `{md_escape(short_counts(row.get('candidateKinds') or {}))}` "
            f"| `{md_escape(short_counts(row.get('relations') or {}))}` "
            f"| `{md_escape(short_counts(row.get('hints') or {}, 3))}` "
            f"| `{md_escape(examples)}` |"
        )

    lines.extend([
        "",
        "## Best Story-Adjacent Rows",
        "",
        "| score | map/script | key | missions | kind | relation | opcode | story refs | reasons |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    best_rows: list[dict[str, Any]] = []
    for row in payload.get("rows") or []:
        best = row.get("bestCandidate") or {}
        if not best or best.get("relationToStory") == "no-story-in-chain":
            continue
        record = best.get("record") or {}
        best_rows.append({
            "score": int(best.get("score") or 0),
            "mapScript": f"{row.get('mapId')}/{row.get('scriptId')}",
            "key": row.get("key"),
            "missions": ", ".join(row.get("checkerMissions") or []),
            "kind": best.get("candidateKind"),
            "relation": best.get("relationToStory"),
            "opcode": record.get("opcode"),
            "storyRefs": ", ".join((best.get("chainStoryRefs") or [])[:4]),
            "reasons": "; ".join(best.get("reasons") or []),
        })
    best_rows.sort(key=lambda item: (-item["score"], safe_text(item["mapScript"]), safe_text(item["key"])))
    if not best_rows:
        lines.append("| _(none)_ |  |  |  |  |  |  |  |  |")
    for row in best_rows[:top_rows]:
        lines.append(
            f"| {row['score']} "
            f"| `{md_escape(row['mapScript'])}` "
            f"| `{md_escape(row['key'])}` "
            f"| `{md_escape(row['missions'])}` "
            f"| `{md_escape(row['kind'])}` "
            f"| `{md_escape(row['relation'])}` "
            f"| `{md_escape(row['opcode'])}` "
            f"| `{md_escape(row['storyRefs'])}` "
            f"| {md_escape(row['reasons'])} |"
        )

    lines.extend([
        "",
        "## Interpretation Notes",
        "",
        "- `after-story` and `same-record-as-story` rows are the best completion/gate candidates, but still need class-level proof before promotion.",
        "- `before-story` rows are more likely gates/preconditions than completion setters.",
        "- `property-list-clear` rows are ActionBase list-clear targets, not setter proof.",
        "- `terminal-bridge` rows are high LevelScript terminal/completion candidates; use the terminal-branch audit for walked local-ref targets.",
        "- `listener` rows, especially property-change events, are useful trigger evidence but should not be treated as setters.",
        "- Rows with a bridge but no UID key record usually carry the key in top-level property/model data rather than an action record.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--reports-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--refresh-property-flow", action="store_true")
    parser.add_argument("--top-rows", type=int, default=40)
    args = parser.parse_args()

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    payload = build_audit(language=args.language, refresh_property_flow=args.refresh_property_flow)
    out_json = args.reports_dir / f"levelscript_property_setter_candidates_{args.language}.json"
    out_md = args.reports_dir / f"levelscript_property_setter_candidates_{args.language}.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload, top_rows=max(1, args.top_rows)))
    print(f"LevelScript property setter candidates: {out_json}")
    print(f"LevelScript property setter candidate report: {out_md}")
    summary = payload.get("summary") or {}
    print(
        f"bridgeFound={summary.get('bridgeFoundTriples')} "
        f"exactKeyRows={summary.get('rowsWithExactKeyRecords')} "
        f"storyAdjacent={summary.get('storyAdjacentCandidateObservations')} "
        f"opcodes={summary.get('opcodeCandidateCount')}"
    )


if __name__ == "__main__":
    main()
