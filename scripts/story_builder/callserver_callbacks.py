#!/usr/bin/env python3
"""Parse and validate serialized CallServer callback relations.

The stable parsing, validation, report, and command APIs live together here so
production consumers do not depend on the recovery package.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


if __package__ == "story_builder":
    from common import (
        STORY_RECOVERY_REPORTS_DIR,
        md_escape,
        read_bytes_cached,
        rel_path,
        write_report_json,
        write_text_if_changed,
    )
elif __package__ == "scripts.story_builder":
    from scripts.common import (
        STORY_RECOVERY_REPORTS_DIR,
        md_escape,
        read_bytes_cached,
        rel_path,
        write_report_json,
        write_text_if_changed,
    )
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("run this module with python -m scripts.story_builder.callserver_callbacks")
from .context import LEVELSCRIPT_DIR
from .level_bindings import (
    CALLSERVER_CALLBACK_CONTRACT_AUDIT,
    _levelscript_native_action_successors,
    _levelscript_native_callserver_callback_successors,
    _prepare_levelscript_native_control_context,
    build_levelscript_action_story_occurrences,
    levelscript_native_action_name,
    levelscript_record_semantic_key,
)
from .levelscript_binary import (
    compact_callserver_serialized_contract,
    decode_levelscript_record_payload,
    extract_levelscript_uid_records,
    levelscript_action_map_membership,
)


SCHEMA = "levelScriptCallServerCallbackAudit.v2"
CALLSERVER_PAIR = (0x0034, 14)
HEX_UID_RE = re.compile(r"[0-9a-fA-F]{8}")
DEFAULT_JSON = STORY_RECOVERY_REPORTS_DIR / "levelscript_callserver_callback_audit.json"
DEFAULT_MARKDOWN = STORY_RECOVERY_REPORTS_DIR / "levelscript_callserver_callback_audit.md"


def _story_occurrences_by_record(
    level_script_root: Path,
) -> dict[tuple[str, int], list[str]]:
    by_record: dict[tuple[str, int], set[str]] = defaultdict(set)
    for story_key, occurrences in build_levelscript_action_story_occurrences(
        level_script_root
    ).items():
        for occurrence in occurrences:
            source_file = str(occurrence.get("sourceFile") or "").replace("\\", "/")
            record_offset = occurrence.get("recordOffset")
            if source_file and isinstance(record_offset, int):
                by_record[(source_file, record_offset)].add(story_key)
    return {
        key: sorted(values)
        for key, values in by_record.items()
    }


def _callback_control_graph(
    *,
    source_file: str,
    start_local_id: int,
    data: bytes,
    membership: dict[int, str],
    context: dict[str, Any],
    story_by_record: dict[tuple[str, int], list[str]],
) -> dict[str, Any]:
    action_by_local = context.get("actionByLocal") or {}
    ordered = context.get("ordered") or []
    records_by_uid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in ordered:
        uid = str(record.get("uid") or "").casefold()
        if uid:
            records_by_uid[uid].append(record)
    decoded_cache = context.get("decodedByStart") or {}
    next_starts = context.get("nextStarts") or {}

    def detail(record: dict[str, Any]) -> dict[str, Any]:
        start = int(record.get("start") or 0)
        if start not in decoded_cache:
            decoded_cache[start] = decode_levelscript_record_payload(
                data,
                record,
                next_start=next_starts.get(start),
                action_map_role=str(membership.get(start) or ""),
            )
        return decoded_cache[start]

    nodes: dict[int, dict[str, Any]] = {}
    edges: set[tuple[int, int, str]] = set()
    story_keys: set[str] = set()
    queue: deque[tuple[int, tuple[int, ...]]] = deque([(start_local_id, tuple())])
    cycle_count = 0
    while queue and len(nodes) < 512:
        local_id, path = queue.popleft()
        if local_id in path:
            cycle_count += 1
            continue
        record = action_by_local.get(local_id)
        if record is None:
            continue
        start = int(record.get("start") or 0)
        record_story_keys = story_by_record.get((source_file, start), [])
        story_keys.update(record_story_keys)
        node = {
            "localId": local_id,
            "uid": str(record.get("uid") or ""),
            "actionName": levelscript_native_action_name(record),
            "storyKeys": record_story_keys,
        }
        nodes[local_id] = node
        record_detail = detail(record)
        successors = list(dict.fromkeys([
            *_levelscript_native_action_successors(record, record_detail),
            *_levelscript_native_callserver_callback_successors(
                record,
                record_detail,
                records_by_uid=records_by_uid,
                membership=membership,
                decode_record=detail,
            ),
        ]))
        for edge_name, next_local_id in successors:
            edges.add((local_id, next_local_id, edge_name))
            queue.append((next_local_id, path + (local_id,)))
    branch_points = len({
        source
        for source, _target, _edge in edges
        if sum(1 for row in edges if row[0] == source) > 1
    })
    return {
        "startActionLocalId": start_local_id,
        "actionCount": len(nodes),
        "edgeCount": len(edges),
        "branchPointCount": branch_points,
        "cycleCount": cycle_count,
        "storyKeys": sorted(story_keys),
        "actions": [nodes[key] for key in sorted(nodes)],
        "edges": [
            {
                "sourceLocalId": source,
                "targetLocalId": target,
                "edge": edge,
            }
            for source, target, edge in sorted(edges)
        ],
        "truncated": bool(queue),
    }


def validate_callserver_serialized_contract(
    call_server: dict[str, Any],
    *,
    source_file: str,
    local_id: Any,
    uid: Any,
) -> list[dict[str, Any]]:
    """Fail closed when any of the six decoded CallServer fields is incomplete.

    This validates the reusable serialized action shape, not any particular
    LevelScript object or event value. Value distributions are reported by the
    corpus audit instead of being promoted into mission/order evidence.
    """
    failures: list[dict[str, Any]] = []
    common = {
        "source": source_file,
        "localId": local_id,
        "uid": uid,
    }
    expected_fields = {
        "callClientOutputUIDs",
        "eventArgsPtr",
        "eventName",
        "useCustomEvent",
        "waitForCallback",
        "withEventArgs",
        "consumedBytes",
        "trailingBytes",
    }
    missing = sorted(expected_fields - set(call_server))
    if missing:
        failures.append({
            "gate": "callserver_serialized_fields_present",
            **common,
            "expected": sorted(expected_fields),
            "actualMissing": missing,
        })
        return failures
    output_uids = call_server.get("callClientOutputUIDs")
    if output_uids is not None and not isinstance(output_uids, list):
        failures.append({
            "gate": "callserver_output_list_type",
            **common,
            "expected": "null-or-list",
            "actual": type(output_uids).__name__,
        })
    event_args = call_server.get("eventArgsPtr")
    if not isinstance(event_args, dict) or not isinstance(
        event_args.get("pathValue") if isinstance(event_args, dict) else None,
        str,
    ):
        failures.append({
            "gate": "callserver_event_args_param_shape",
            **common,
            "expected": "object-with-string-pathValue",
            "actual": event_args,
        })
    if not isinstance(call_server.get("eventName"), str):
        failures.append({
            "gate": "callserver_event_name_type",
            **common,
            "expected": "string",
            "actual": type(call_server.get("eventName")).__name__,
        })
    for field in ("useCustomEvent", "waitForCallback", "withEventArgs"):
        if not isinstance(call_server.get(field), bool):
            failures.append({
                "gate": f"callserver_{field}_type",
                **common,
                "expected": "bool",
                "actual": type(call_server.get(field)).__name__,
            })
    for field in ("consumedBytes", "trailingBytes"):
        value = call_server.get(field)
        if not isinstance(value, int) or value < 0:
            failures.append({
                "gate": f"callserver_{field}_range",
                **common,
                "expected": "non-negative-int",
                "actual": value,
            })
    return failures


def build_report(
    *,
    level_script_root: Path = LEVELSCRIPT_DIR,
) -> dict[str, Any]:
    contract_audit = CALLSERVER_CALLBACK_CONTRACT_AUDIT
    native_contract = dict(contract_audit.get("nativeContract") or {})
    native_contract.setdefault("schema", contract_audit.get("schema", ""))
    native_contract.setdefault("status", contract_audit.get("status", ""))
    native_contract.update({
        "source": contract_audit.get("sourceFile", ""),
        "sourceSha256": contract_audit.get("sourceSha256", ""),
    })
    level_script_root = level_script_root.resolve()
    story_by_record = _story_occurrences_by_record(level_script_root)
    rows: list[dict[str, Any]] = []
    unresolved_outputs: list[dict[str, Any]] = []
    validation_failures: list[dict[str, Any]] = list(
        contract_audit.get("validationFailures") or []
    )
    counts: Counter[str] = Counter()
    output_count_distribution: Counter[str] = Counter()
    callback_event_types: Counter[str] = Counter()
    downstream_action_names: Counter[str] = Counter()
    event_name_identity_distribution: Counter[str] = Counter()
    event_args_path_value_distribution: Counter[str] = Counter()
    event_args_param_source_distribution: Counter[str] = Counter()
    event_args_param_path_distribution: Counter[str] = Counter()
    flag_distribution: Counter[str] = Counter()
    trailing_bytes_distribution: Counter[str] = Counter()

    files = sorted(level_script_root.rglob("*.json"))
    for path in files:
        source_file = rel_path(path)
        normalized_source = source_file.replace("\\", "/")
        try:
            data = read_bytes_cached(path)
        except OSError as exc:
            validation_failures.append({
                "gate": "read_levelscript",
                "source": source_file,
                "actual": str(exc),
            })
            continue
        records = extract_levelscript_uid_records(data)
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
        call_server_records = [
            record
            for record in records
            if levelscript_record_semantic_key(record) == CALLSERVER_PAIR
            and str(membership.get(int(record.get("start") or 0)) or "").startswith(
                "actionList#"
            )
        ]
        if not call_server_records:
            continue
        context = _prepare_levelscript_native_control_context(
            data,
            records,
            membership,
        )
        records_by_uid: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            uid = str(record.get("uid") or "").casefold()
            if uid:
                records_by_uid[uid].append(record)

        for record in call_server_records:
            counts["callServerActions"] += 1
            start = int(record.get("start") or 0)
            detail = decode_levelscript_record_payload(
                data,
                record,
                next_start=next_starts.get(start),
                action_map_role=str(membership.get(start) or ""),
            )
            call_server = detail.get("callServer") or {}
            if not call_server:
                validation_failures.append({
                    "gate": "decode_callserver_generated_fields",
                    "source": source_file,
                    "localId": record.get("localId"),
                    "uid": record.get("uid"),
                    "payloadHexPrefix": detail.get("payloadHexPrefix") or "",
                })
                continue
            counts["decodedCallServerActions"] += 1
            contract_failures = validate_callserver_serialized_contract(
                call_server,
                source_file=source_file,
                local_id=record.get("localId"),
                uid=record.get("uid"),
            )
            if contract_failures:
                validation_failures.extend(contract_failures)
                continue
            event_args = call_server["eventArgsPtr"]
            event_name_identity_distribution[
                str(call_server.get("eventNameIdentity") or "other")
            ] += 1
            event_args_path_value_distribution[
                str(event_args.get("pathValue") or "<empty>")
            ] += 1
            event_args_param_source_distribution[
                str(event_args.get("paramSource"))
            ] += 1
            event_args_param_path_distribution[
                str(event_args.get("path") or "<null>")
            ] += 1
            flag_distribution[
                "custom={custom},wait={wait},args={args}".format(
                    custom=int(call_server["useCustomEvent"]),
                    wait=int(call_server["waitForCallback"]),
                    args=int(call_server["withEventArgs"]),
                )
            ] += 1
            trailing_bytes_distribution[str(call_server["trailingBytes"])] += 1
            output_uids = call_server.get("callClientOutputUIDs")
            if output_uids is None:
                counts["nullOutputLists"] += 1
                output_count_distribution["null"] += 1
                callback_output_uids: list[Any] = []
            else:
                counts["nonNullOutputLists"] += 1
                output_count_distribution[str(len(output_uids))] += 1
                if output_uids:
                    counts["callServerActionsWithOutputs"] += 1
                callback_output_uids = output_uids
            callback_rows: list[dict[str, Any]] = []
            for index, output_uid in enumerate(callback_output_uids):
                counts["callbackOutputUids"] += 1
                callback: dict[str, Any] = {
                    "index": index,
                    "headerUid": output_uid,
                }
                if not isinstance(output_uid, str) or not HEX_UID_RE.fullmatch(
                    output_uid
                ):
                    callback["status"] = "invalid_header_uid_shape"
                    unresolved_outputs.append({
                        "sourceFile": source_file,
                        "callServerLocalId": record.get("localId"),
                        **callback,
                    })
                    callback_rows.append(callback)
                    continue
                candidates = records_by_uid.get(output_uid.casefold(), [])
                if len(candidates) != 1:
                    callback["status"] = (
                        "missing_header_uid"
                        if not candidates
                        else "ambiguous_header_uid"
                    )
                    callback["candidateCount"] = len(candidates)
                    unresolved_outputs.append({
                        "sourceFile": source_file,
                        "callServerLocalId": record.get("localId"),
                        **callback,
                    })
                    callback_rows.append(callback)
                    continue
                header = candidates[0]
                header_start = int(header.get("start") or 0)
                header_role = str(membership.get(header_start) or "")
                header_detail = decode_levelscript_record_payload(
                    data,
                    header,
                    next_start=next_starts.get(header_start),
                    action_map_role=header_role,
                )
                event = header_detail.get("nativeEventDetail") or {}
                event_type = str(event.get("type") or header_detail.get("label") or "")
                event_key = str(event.get("eventKey") or "")
                next_action_id = (header_detail.get("actionHeader") or {}).get(
                    "nextId"
                )
                if (
                    not header_role.startswith("headerList#")
                    or event_type != "ScriptEvent_OnCustomEvent"
                    or event_key.casefold() != f"#{output_uid}".casefold()
                    or not isinstance(next_action_id, int)
                    or next_action_id <= 0
                ):
                    validation_failures.append({
                        "gate": "callback_uid_header_contract",
                        "source": source_file,
                        "callServerLocalId": record.get("localId"),
                        "headerUid": output_uid,
                        "headerRole": header_role,
                        "eventType": event_type,
                        "eventKey": event_key,
                        "nextActionLocalId": next_action_id,
                    })
                    callback["status"] = "header_contract_mismatch"
                    callback_rows.append(callback)
                    continue
                graph = _callback_control_graph(
                    source_file=normalized_source,
                    start_local_id=next_action_id,
                    data=data,
                    membership=membership,
                    context=context,
                    story_by_record=story_by_record,
                )
                callback_event_types[event_type] += 1
                counts["exactCallbackHeaders"] += 1
                counts["callbackControlActions"] += graph["actionCount"]
                counts["callbackControlEdges"] += graph["edgeCount"]
                counts["callbackBranchPoints"] += graph["branchPointCount"]
                if graph["storyKeys"]:
                    counts["callbackHeadersReachingStory"] += 1
                    counts["callbackStoryTargets"] += len(graph["storyKeys"])
                for action in graph["actions"]:
                    action_name = str(action.get("actionName") or "")
                    if action_name:
                        downstream_action_names[action_name] += 1
                callback.update({
                    "status": "exact_callback_header_control_path",
                    "headerLocalId": header.get("localId"),
                    "headerRole": header_role,
                    "eventType": event_type,
                    "eventKey": event_key,
                    "controlGraph": graph,
                })
                callback_rows.append(callback)
            rows.append({
                "levelId": path.parent.name,
                "scriptId": path.stem,
                "sourceFile": source_file,
                "callServerLocalId": record.get("localId"),
                "callServerUid": record.get("uid"),
                "serializedContract": compact_callserver_serialized_contract(
                    call_server
                ),
                "eventName": call_server.get("eventName"),
                "waitForCallback": bool(call_server.get("waitForCallback")),
                "callbackOutputs": callback_rows,
            })

    counts["levelScriptFilesScanned"] = len(files)
    counts["unresolvedCallbackOutputs"] = len(unresolved_outputs)
    counts["validationFailures"] = len(validation_failures)
    status = (
        "validated_complete_corpus"
        if not validation_failures
        and counts["decodedCallServerActions"] == counts["callServerActions"]
        else "validation_failed"
    )
    return {
        "schema": SCHEMA,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "sources": {
            "levelScriptRoot": rel_path(level_script_root),
            "nativeContract": native_contract,
        },
        "summary": {
            **dict(sorted(counts.items())),
            "outputCountDistribution": dict(sorted(output_count_distribution.items())),
            "callbackEventTypes": dict(sorted(callback_event_types.items())),
            "eventNameIdentityDistribution": dict(
                sorted(event_name_identity_distribution.items())
            ),
            "eventArgsPathValueDistribution": dict(
                sorted(event_args_path_value_distribution.items())
            ),
            "eventArgsParamSourceDistribution": dict(
                sorted(event_args_param_source_distribution.items())
            ),
            "eventArgsParamPathDistribution": dict(
                sorted(event_args_param_path_distribution.items())
            ),
            "flagDistribution": dict(sorted(flag_distribution.items())),
            "trailingBytesDistribution": dict(
                sorted(trailing_bytes_distribution.items(), key=lambda row: int(row[0]))
            ),
            "downstreamActionNames": dict(
                sorted(downstream_action_names.items(), key=lambda row: (-row[1], row[0]))
            ),
        },
        "rows": rows,
        "unresolvedCallbackOutputs": unresolved_outputs,
        "validationFailures": validation_failures,
        "missionOwnershipEvidence": False,
        "evidenceBoundary": (
            "The installed binary makes each non-empty callClientOutputUIDs value a "
            "possible sub-executor header UID. Exact UID/event/header/action links prove "
            "conditional callback topology inside one LevelScript. Missing UIDs remain "
            "dangling, and neither a callback nor its local actions identify a mission "
            "owner. Ten exact callback headers do reach Story playback actions, but "
            "none of their CallServer actions are themselves downstream of an earlier "
            "Story playback in the local typed graph, so they do not create a recovered "
            "Story-to-Story order edge. The audit retains all six serialized "
            "CallServer fields for every decoded action; their exact values are "
            "runtime handoff parameters, not mission identity unless an independent "
            "original-data contract proves that interpretation."
        ),
        "usesOcrOrManualOrder": False,
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# LevelScript CallServer Callback Audit",
        "",
        f"- status: `{report.get('status')}`",
        f"- LevelScript files scanned: `{summary.get('levelScriptFilesScanned', 0)}`",
        f"- CallServer actions decoded: `{summary.get('decodedCallServerActions', 0)}` / `{summary.get('callServerActions', 0)}`",
        f"- actions with callback outputs: `{summary.get('callServerActionsWithOutputs', 0)}`",
        f"- callback output UIDs: `{summary.get('callbackOutputUids', 0)}`",
        f"- exact callback headers: `{summary.get('exactCallbackHeaders', 0)}`",
        f"- unresolved callback outputs: `{summary.get('unresolvedCallbackOutputs', 0)}`",
        f"- callback headers reaching Story playback: `{summary.get('callbackHeadersReachingStory', 0)}`",
        f"- validation failures: `{summary.get('validationFailures', 0)}`",
        f"- event-name identities: `{json.dumps(summary.get('eventNameIdentityDistribution', {}), sort_keys=True)}`",
        f"- event argument path values: `{json.dumps(summary.get('eventArgsPathValueDistribution', {}), sort_keys=True)}`",
        f"- flag combinations: `{json.dumps(summary.get('flagDistribution', {}), sort_keys=True)}`",
        f"- trailing-byte lengths: `{json.dumps(summary.get('trailingBytesDistribution', {}), sort_keys=True)}`",
        "",
        "## Evidence boundary",
        "",
        str(report.get("evidenceBoundary") or ""),
    ]
    unresolved = report.get("unresolvedCallbackOutputs") or []
    if unresolved:
        lines.extend([
            "",
            "## Unresolved callback outputs",
            "",
            "| Source | CallServer local id | Header UID | Status |",
            "|---|---:|---|---|",
        ])
        for row in unresolved:
            lines.append(
                f"| `{md_escape(row.get('sourceFile', ''))}` | "
                f"`{row.get('callServerLocalId', '')}` | "
                f"`{md_escape(row.get('headerUid', ''))}` | "
                f"`{md_escape(row.get('status', ''))}` |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level-script-root", type=Path, default=LEVELSCRIPT_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    report = build_report(
        level_script_root=args.level_script_root,
    )
    write_report_json(args.out, report)
    write_text_if_changed(args.markdown, markdown_report(report))
    summary = report["summary"]
    print(
        "CallServer callback audit: "
        f"{summary['decodedCallServerActions']}/{summary['callServerActions']} actions, "
        f"{summary['exactCallbackHeaders']}/{summary['callbackOutputUids']} exact headers, "
        f"{summary['callbackHeadersReachingStory']} Story callbacks, "
        f"{summary['validationFailures']} validation failures"
    )
    return 0 if report["status"] == "validated_complete_corpus" else 1


if __name__ == "__main__":
    raise SystemExit(main())
