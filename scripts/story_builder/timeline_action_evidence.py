"""Recover compact dialog Timeline action evidence for WebUI debug views.

This consumes AnimeStudio MonoBehaviour JSON with
`$animestudio.recoveredManagedReferences.RefIds`, follows
`DialogMainFlowData` RID links to trunk line actions, and compares the recovered
action-flow line sequence with the existing Timeline clip order.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import fast_glob_files

EXPORT_ROOT = ROOT / "export_full"
DEFAULT_RECOVERY_ROOT = EXPORT_ROOT / "recovered" / "AnimeStudio-cli"
DEFAULT_OUT = DEFAULT_RECOVERY_ROOT / "timeline_action_evidence.json"
DEFAULT_LINE_ORDERS = DEFAULT_RECOVERY_ROOT / "timeline_line_orders.json"

ACTION_DISPLAY_LIMIT_PER_LINE = 8
DETAIL_TIMELINE_LIMIT = 5

ACTION_KIND_BY_CLASS = {
    "DialogAnimActData": "anim",
    "DialogCamActData": "camera",
    "DialogCamDOFActionData": "dof",
    "DialogCamPPActionData": "postfx",
    "DialogEmotionActData": "face",
    "DialogEmotionPoseActData": "pose",
    "DialogLookAtActData": "lookAt",
    "DialogMaskActionData": "mask",
    "DialogMFTransitionActionData": "transition",
    "DialogMFTrunkActionData": "line",
    "DialogMorphAnimActData": "morphAnim",
    "DialogMoveToActData": "move",
    "DialogMuteAutoBlinkActData": "blink",
    "DialogSetDisableClickActionData": "click",
    "DialogShowOrHideSingleActorActionData": "actor",
    "DialogSummaryActData": "summary",
    "DialogTeleportEntityActionData": "teleport",
    "DialogTurnToActData": "turn",
}

LABEL_FIELDS = (
    "lineId",
    "animationPath",
    "facialMorphPath",
    "morphAnimPath",
    "poseControlNames",
    "controlNames",
    "summaryId",
)

ORDER_STATUS_RANK = {
    "agrees": 0,
    "partialAgree": 1,
    "missingTimeline": 2,
    "conflict": 3,
}
ACTION_TIMELINE_FILENAME_RE = re.compile(r"^(?:[fm]_)?dlg_.*timeline.*\.json$", re.IGNORECASE)

_ACTION_EVIDENCE_CACHE: dict[str, list[dict]] | None = None
_ACTION_EVIDENCE_CACHE_PATH: Path | None = None


def rel_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def log(message: str) -> None:
    print(f"[timeline-action-evidence] {message}")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def rounded_seconds(value: Any) -> float | None:
    number = as_float(value)
    if number is None:
        return None
    return round(number, 3)


def node_value(node: Any) -> Any:
    if isinstance(node, dict) and "value" in node:
        return node.get("value")
    return node


def node_rid(node: Any) -> int | None:
    if isinstance(node, dict):
        return as_int(node.get("rid"))
    return as_int(node)


def action_class(ref: dict) -> str:
    type_info = ref.get("type") if isinstance(ref.get("type"), dict) else {}
    return str(type_info.get("class") or "")


def action_data(ref: dict) -> dict:
    data = ref.get("data")
    return data if isinstance(data, dict) else {}


def action_layout(ref: dict) -> str:
    return str(action_data(ref).get("layout") or "")


def action_timing(data: dict) -> dict:
    prefix = data.get("inferredActionTimingPrefix")
    if not isinstance(prefix, dict):
        return {}
    out: dict[str, Any] = {}
    value0 = rounded_seconds(node_value(prefix.get("value0Seconds")))
    value1 = rounded_seconds(node_value(prefix.get("value1Seconds")))
    action_code = as_int(node_value(prefix.get("actionCode")))
    if value0 is not None:
        out["time0"] = value0
    if value1 is not None:
        out["time1"] = value1
    if action_code is not None:
        out["actionCode"] = action_code
    return out


def compact_value(value: Any) -> Any:
    value = node_value(value)
    if isinstance(value, dict):
        if "values" in value:
            value = value.get("values")
        elif "items" in value:
            value = value.get("items")
    if isinstance(value, list):
        out = []
        for item in value:
            item_value = node_value(item)
            if isinstance(item_value, (str, int, float)) and str(item_value):
                out.append(item_value)
        return out
    if isinstance(value, (str, int, float)) and str(value):
        return value
    return None


def action_label(data: dict) -> str:
    for field in LABEL_FIELDS:
        if field not in data:
            continue
        value = compact_value(data.get(field))
        if isinstance(value, list):
            return ", ".join(str(item) for item in value[:4])
        if value is not None:
            return str(value)
    return ""


def line_id_from_ref(ref: dict) -> str:
    value = compact_value(action_data(ref).get("lineId"))
    return str(value or "").strip()


def dialog_key_from_line_id(line_id: str) -> str:
    value = str(line_id or "").strip()
    if not value.startswith("dlg_"):
        return ""
    return re.sub(r"_\d+$", "", value)


def dialog_key_from_timeline_name(name: str) -> str:
    value = str(name or "").strip()
    if value.startswith("dlg_") and value.endswith("_timeline"):
        return value[: -len("_timeline")]
    for prefix in ("f_dlgtl_", "m_dlgtl_", "dlgtl_"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    value = re.sub(r"_sub_\d+$", "", value)
    return f"dlg_{value}" if value else ""


def compact_action(ref: dict) -> dict:
    data = action_data(ref)
    class_name = action_class(ref)
    layout = action_layout(ref)
    out: dict[str, Any] = {
        "rid": as_int(ref.get("rid")),
        "class": class_name,
        "kind": ACTION_KIND_BY_CLASS.get(class_name, class_name.removeprefix("Dialog").removesuffix("ActionData")),
    }
    if layout:
        out["layout"] = layout
    label = action_label(data)
    if label:
        out["label"] = label
    timing = action_timing(data)
    if timing:
        out.update(timing)
    if data.get("$decoded") is True:
        out["decode"] = "full"
    elif data.get("$partialDecoded") is True:
        out["decode"] = "partial"
    elif data:
        out["decode"] = "raw"
    else:
        out["decode"] = "missing"
    return {key: value for key, value in out.items() if value not in (None, "")}


def iter_default_mono_roots(recovery_root: Path = DEFAULT_RECOVERY_ROOT) -> list[Path]:
    return [
        recovery_root / "StreamingAssets" / "json_by_type" / "MonoBehaviour",
        recovery_root / "Persistent" / "json_by_type" / "MonoBehaviour",
    ]


def iter_mono_dirs(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for raw_root in roots:
        root = raw_root if raw_root.is_absolute() else ROOT / raw_root
        candidates: list[Path] = []
        if root.is_dir() and root.name == "MonoBehaviour":
            candidates.append(root)
        elif (root / "MonoBehaviour").is_dir():
            candidates.append(root / "MonoBehaviour")
        elif root.is_dir():
            candidates.extend(sorted(path for path in root.rglob("MonoBehaviour") if path.is_dir()))
        for candidate in candidates:
            key = str(candidate.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(candidate)
    return out


def iter_action_candidate_files(mono_dir: Path) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for pattern in ("dlg_*timeline*.json", "f_dlg_*timeline*.json", "m_dlg_*timeline*.json"):
        for path in fast_glob_files(mono_dir, pattern):
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
    return paths


def load_timeline_order_index(path: Path) -> dict[str, list[dict]]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    def variants(entry: Any) -> list[dict]:
        if not isinstance(entry, dict):
            return []
        raw_variants = entry.get("variants")
        if isinstance(raw_variants, list) and raw_variants:
            return [item for item in raw_variants if isinstance(item, dict)]
        return [entry]

    index: dict[str, list[dict]] = defaultdict(list)
    by_dialog = payload.get("byDialogKey")
    if isinstance(by_dialog, dict):
        sources = by_dialog.items()
    else:
        sources = (
            (key, value)
            for key, value in payload.items()
            if not str(key).startswith("_") and key != "byDialogKey"
        )
    for raw_key, raw_entry in sources:
        for entry in variants(raw_entry):
            line_ids = [str(line_id) for line_id in (entry.get("lineIds") or []) if str(line_id)]
            if not line_ids:
                line_ids = [
                    str(item.get("id") or "")
                    for item in (entry.get("lineTimings") or entry.get("lines") or [])
                    if isinstance(item, dict) and str(item.get("id") or "")
                ]
            dialog_keys = {str(raw_key)}
            dialog_keys.update(dialog_key_from_line_id(line_id) for line_id in line_ids)
            compact = {
                "sourceKey": str(raw_key),
                "timeline": str(entry.get("timeline") or entry.get("sourceKey") or ""),
                "file": str(entry.get("file") or ""),
                "lineIds": line_ids,
            }
            for key in sorted(key for key in dialog_keys if key.startswith("dlg_")):
                index[key].append(compact)
    return dict(index)


def compare_line_orders(action_line_ids: list[str], timeline_line_ids: list[str]) -> dict:
    action = [line_id for line_id in action_line_ids if line_id]
    timeline = [line_id for line_id in timeline_line_ids if line_id]
    if not action:
        return {"status": "missingAction", "commonLineCount": 0}
    if not timeline:
        return {
            "status": "missingTimeline",
            "commonLineCount": 0,
            "actionLineIds": action,
            "timelineLineIds": [],
        }
    action_set = set(action)
    timeline_set = set(timeline)
    common_action = [line_id for line_id in action if line_id in timeline_set]
    common_timeline = [line_id for line_id in timeline if line_id in action_set]
    status = "agrees" if common_action == common_timeline else "conflict"
    if status == "agrees" and (len(common_action) < len(action) or len(common_timeline) < len(timeline)):
        status = "partialAgree"
    out: dict[str, Any] = {
        "status": status,
        "commonLineCount": len(common_action),
    }
    if status != "agrees":
        out["actionLineIds"] = action[:20]
        out["timelineLineIds"] = timeline[:20]
        action_only = [line_id for line_id in action if line_id not in timeline_set]
        timeline_only = [line_id for line_id in timeline if line_id not in action_set]
        if action_only:
            out["actionOnlyLineIds"] = action_only[:20]
        if timeline_only:
            out["timelineOnlyLineIds"] = timeline_only[:20]
        if status == "conflict":
            for idx, (left, right) in enumerate(zip(common_action, common_timeline)):
                if left != right:
                    out["firstConflict"] = {
                        "index": idx,
                        "actionLineId": left,
                        "timelineLineId": right,
                    }
                    break
    return out


def best_timeline_comparison(action_line_ids: list[str], timeline_entries: list[dict]) -> dict:
    best: dict | None = None
    for entry in timeline_entries:
        comparison = compare_line_orders(action_line_ids, entry.get("lineIds") or [])
        comparison["timeline"] = entry.get("timeline") or entry.get("sourceKey") or ""
        if entry.get("file"):
            comparison["file"] = entry.get("file")
        if best is None:
            best = comparison
            continue
        current_rank = ORDER_STATUS_RANK.get(str(comparison.get("status") or ""), 9)
        best_rank = ORDER_STATUS_RANK.get(str(best.get("status") or ""), 9)
        if (current_rank, -comparison.get("commonLineCount", 0)) < (best_rank, -best.get("commonLineCount", 0)):
            best = comparison
    if best is not None:
        return best
    return compare_line_orders(action_line_ids, [])


def build_action_flows(path: Path, payload: dict) -> list[dict]:
    meta = payload.get("$animestudio") if isinstance(payload.get("$animestudio"), dict) else {}
    refs_root = meta.get("recoveredManagedReferences")
    if not isinstance(refs_root, dict):
        refs_root = payload.get("recoveredManagedReferences")
    if not isinstance(refs_root, dict):
        return []
    refs = refs_root.get("RefIds")
    if not isinstance(refs, list):
        return []

    refs_by_rid = {
        rid: ref
        for ref in refs
        if isinstance(ref, dict)
        for rid in [as_int(ref.get("rid"))]
        if rid is not None
    }
    flows: list[dict] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict) or action_class(ref) != "DialogMainFlowData":
            continue
        data = action_data(ref)
        if action_layout(ref) != "DialogMainFlowDataRidArray":
            continue
        rid_nodes = [data.get("leadRid")]
        linked = data.get("linkedRids")
        if isinstance(linked, list):
            rid_nodes.extend(linked)
        linked_rids = [rid for rid in (node_rid(node) for node in rid_nodes) if rid is not None]
        action_refs = [refs_by_rid[rid] for rid in linked_rids if rid in refs_by_rid]
        line_ref = next((candidate for candidate in action_refs if line_id_from_ref(candidate)), None)
        line_id = line_id_from_ref(line_ref or {}) if line_ref else ""
        if not line_id:
            continue
        line_timing = action_timing(action_data(line_ref)) if line_ref else {}
        compact_actions = [
            compact_action(candidate)
            for candidate in action_refs
            if candidate is not line_ref
        ]
        decoded_count = sum(1 for action in compact_actions if action.get("decode") in {"full", "partial"})
        flows.append({
            "sequence": index,
            "rid": as_int(ref.get("rid")),
            "lineId": line_id,
            "dialogKey": dialog_key_from_line_id(line_id),
            "timing": line_timing,
            "linkedRids": linked_rids,
            "actions": compact_actions,
            "linkedActionCount": len(compact_actions),
            "decodedActionCount": decoded_count,
            "unparsedActionCount": len(compact_actions) - decoded_count,
        })
    return flows


def compact_line_flow(flow: dict) -> dict:
    actions = flow.get("actions") or []
    out: dict[str, Any] = {
        "lineId": flow.get("lineId") or "",
        "flowRid": flow.get("rid"),
        "actionCount": len(actions),
        "actions": actions[:ACTION_DISPLAY_LIMIT_PER_LINE],
    }
    timing = flow.get("timing") if isinstance(flow.get("timing"), dict) else {}
    if timing:
        out["timing"] = timing
    omitted = len(actions) - ACTION_DISPLAY_LIMIT_PER_LINE
    if omitted > 0:
        out["omittedActions"] = omitted
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def build_entry_from_flows(path: Path, payload: dict, dialog_key: str, flows: list[dict]) -> dict:
    meta = payload.get("$animestudio") if isinstance(payload.get("$animestudio"), dict) else {}
    name = str(meta.get("name") or path.stem)
    timeline = name or dialog_key_from_timeline_name(path.stem)
    layout_counts: Counter = Counter()
    kind_counts: Counter = Counter()
    line_ids: list[str] = []
    line_flows: list[dict] = []
    linked_action_count = 0
    decoded_action_count = 0
    unparsed_action_count = 0
    for flow in flows:
        line_id = str(flow.get("lineId") or "")
        if line_id and line_id not in line_ids:
            line_ids.append(line_id)
        linked_action_count += int(flow.get("linkedActionCount") or 0)
        decoded_action_count += int(flow.get("decodedActionCount") or 0)
        unparsed_action_count += int(flow.get("unparsedActionCount") or 0)
        for action in flow.get("actions") or []:
            if action.get("layout"):
                layout_counts[str(action["layout"])] += 1
            if action.get("kind"):
                kind_counts[str(action["kind"])] += 1
        line_flows.append(compact_line_flow(flow))
    out: dict[str, Any] = {
        "timeline": timeline,
        "dialogKey": dialog_key,
        "file": rel_path(path),
        "pathId": meta.get("pathId"),
        "sourceFile": meta.get("sourceFile") or "",
        "sourceOriginalPath": meta.get("sourceOriginalPath") or "",
        "typeTreeSource": meta.get("typeTreeSource") or "",
        "partialTypeTreeDecode": bool(meta.get("partialTypeTreeDecode")),
        "lineIds": line_ids,
        "flowCount": len(line_flows),
        "linkedActionCount": linked_action_count,
        "decodedActionCount": decoded_action_count,
        "unparsedActionCount": unparsed_action_count,
        "layoutCounts": dict(sorted(layout_counts.items())),
        "actionKindCounts": dict(sorted(kind_counts.items())),
        "lineFlows": line_flows,
    }
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def scan_action_entries(mono_roots: list[Path]) -> tuple[dict[str, list[dict]], dict]:
    mono_dirs = iter_mono_dirs(mono_roots)
    by_dialog: dict[str, list[dict]] = defaultdict(list)
    file_count = 0
    candidate_file_count = 0
    files_with_refs = 0
    ref_count = 0
    main_flow_count = 0
    seen_files: set[str] = set()
    for mono_dir in mono_dirs:
        for path in iter_action_candidate_files(mono_dir):
            resolved = str(path.resolve()).lower()
            if resolved in seen_files:
                continue
            seen_files.add(resolved)
            file_count += 1
            if not ACTION_TIMELINE_FILENAME_RE.search(path.name):
                continue
            candidate_file_count += 1
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            if "recoveredManagedReferences" not in text or "DialogMainFlowData" not in text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            meta = payload.get("$animestudio") if isinstance(payload.get("$animestudio"), dict) else {}
            refs_root = meta.get("recoveredManagedReferences")
            if not isinstance(refs_root, dict):
                refs_root = payload.get("recoveredManagedReferences")
            refs = refs_root.get("RefIds") if isinstance(refs_root, dict) else []
            if isinstance(refs, list):
                ref_count += len(refs)
            flows = build_action_flows(path, payload)
            if not flows:
                continue
            files_with_refs += 1
            main_flow_count += len(flows)
            flows_by_dialog: dict[str, list[dict]] = defaultdict(list)
            fallback_dialog_key = dialog_key_from_timeline_name(str(meta.get("name") or path.stem))
            for flow in flows:
                dialog_key = str(flow.get("dialogKey") or fallback_dialog_key)
                if dialog_key:
                    flows_by_dialog[dialog_key].append(flow)
            for dialog_key, group_flows in flows_by_dialog.items():
                by_dialog[dialog_key].append(build_entry_from_flows(path, payload, dialog_key, group_flows))
    meta = {
        "monoDirCount": len(mono_dirs),
        "monoFileCount": file_count,
        "candidateMonoFileCount": candidate_file_count,
        "filesWithActionEvidence": files_with_refs,
        "managedReferenceCount": ref_count,
        "mainFlowCount": main_flow_count,
    }
    return dict(by_dialog), meta


def attach_line_order_comparisons(by_dialog: dict[str, list[dict]], line_orders_path: Path) -> dict:
    timeline_index = load_timeline_order_index(line_orders_path)
    status_counts: Counter = Counter()
    for dialog_key, entries in by_dialog.items():
        timeline_entries = timeline_index.get(dialog_key, [])
        for entry in entries:
            comparison = best_timeline_comparison(entry.get("lineIds") or [], timeline_entries)
            entry["lineOrderComparison"] = comparison
            status_counts[str(comparison.get("status") or "unknown")] += 1
    return dict(sorted(status_counts.items()))


def build_timeline_action_evidence(
    *,
    mono_roots: list[Path] | None = None,
    line_orders_path: Path = DEFAULT_LINE_ORDERS,
    out_path: Path = DEFAULT_OUT,
    write: bool = True,
) -> dict:
    roots = mono_roots or iter_default_mono_roots(out_path.parents[0] if out_path.name else DEFAULT_RECOVERY_ROOT)
    t0 = time.time()
    by_dialog, scan_meta = scan_action_entries(roots)
    comparison_counts = attach_line_order_comparisons(by_dialog, line_orders_path)
    by_dialog = {
        key: sorted(entries, key=lambda item: (item.get("timeline") or "", item.get("file") or ""))
        for key, entries in sorted(by_dialog.items())
    }
    payload = {
        "_meta": {
            "generatedBy": "scripts/story_builder/timeline_action_evidence.py",
            "generated": int(time.time()),
            "elapsedSeconds": round(time.time() - t0, 3),
            "lineOrders": rel_path(line_orders_path),
            "dialogKeyCount": len(by_dialog),
            "timelineEntryCount": sum(len(entries) for entries in by_dialog.values()),
            "lineOrderComparisonCounts": comparison_counts,
            **scan_meta,
        },
        "byDialogKey": by_dialog,
    }
    if write:
        write_json(out_path, payload)
        log(
            f"wrote {rel_path(out_path)} "
            f"({payload['_meta']['dialogKeyCount']} dialog key(s), "
            f"{payload['_meta']['mainFlowCount']} action flow(s))"
        )
    return payload


def default_evidence_out(export_root: Path = EXPORT_ROOT) -> Path:
    return export_root / "recovered" / "AnimeStudio-cli" / "timeline_action_evidence.json"


def build_timeline_action_evidence_for_build(export_root: Path = EXPORT_ROOT) -> dict:
    recovery_root = export_root / "recovered" / "AnimeStudio-cli"
    return build_timeline_action_evidence(
        mono_roots=iter_default_mono_roots(recovery_root),
        line_orders_path=recovery_root / "timeline_line_orders.json",
        out_path=recovery_root / "timeline_action_evidence.json",
        write=True,
    )


def load_timeline_action_evidence_index(path: Path = DEFAULT_OUT) -> dict[str, list[dict]]:
    global _ACTION_EVIDENCE_CACHE, _ACTION_EVIDENCE_CACHE_PATH
    path = path if path.is_absolute() else ROOT / path
    if _ACTION_EVIDENCE_CACHE is not None and _ACTION_EVIDENCE_CACHE_PATH == path:
        return _ACTION_EVIDENCE_CACHE
    if not path.exists():
        _ACTION_EVIDENCE_CACHE = {}
        _ACTION_EVIDENCE_CACHE_PATH = path
        return _ACTION_EVIDENCE_CACHE
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        payload = {}
    by_dialog = payload.get("byDialogKey") if isinstance(payload, dict) else {}
    if not isinstance(by_dialog, dict):
        by_dialog = {}
    _ACTION_EVIDENCE_CACHE = {
        str(key): [entry for entry in entries if isinstance(entry, dict)]
        for key, entries in by_dialog.items()
        if isinstance(entries, list)
    }
    _ACTION_EVIDENCE_CACHE_PATH = path
    return _ACTION_EVIDENCE_CACHE


def _merge_counts(entries: list[dict], field: str) -> dict[str, int]:
    counts: Counter = Counter()
    for entry in entries:
        raw_counts = entry.get(field)
        if not isinstance(raw_counts, dict):
            continue
        for key, value in raw_counts.items():
            number = as_int(value)
            if key and number:
                counts[str(key)] += number
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return "missing"
    return max(statuses, key=lambda status: ORDER_STATUS_RANK.get(status, 9))


def build_conversation_action_debug(
    conv_key: str,
    original_line_ids: list[str],
    ordered_line_ids: list[str] | None = None,
    *,
    evidence_path: Path = DEFAULT_OUT,
) -> dict | None:
    entries = load_timeline_action_evidence_index(evidence_path).get(conv_key, [])
    if not entries:
        return None
    action_line_ids: list[str] = []
    line_flow_rows: dict[str, dict] = {}
    for entry in entries:
        for line_id in entry.get("lineIds") or []:
            line_id = str(line_id)
            if line_id and line_id not in action_line_ids:
                action_line_ids.append(line_id)
        for flow in entry.get("lineFlows") or []:
            if not isinstance(flow, dict):
                continue
            line_id = str(flow.get("lineId") or "")
            if not line_id:
                continue
            row = line_flow_rows.setdefault(line_id, {
                "lineId": line_id,
                "flowCount": 0,
                "actionCount": 0,
                "actions": [],
            })
            row["flowCount"] += 1
            row["actionCount"] += int(flow.get("actionCount") or len(flow.get("actions") or []))
            for action in flow.get("actions") or []:
                if len(row["actions"]) < ACTION_DISPLAY_LIMIT_PER_LINE:
                    row["actions"].append(action)
            row["omittedActions"] = max(
                0,
                int(row.get("actionCount") or 0) - len(row.get("actions") or []),
            )

    current_order = [str(line_id) for line_id in (ordered_line_ids or original_line_ids) if str(line_id)]
    comparison = compare_line_orders(action_line_ids, current_order)
    comparison["comparedTo"] = "webuiCurrentOrder"

    timeline_statuses = [
        str((entry.get("lineOrderComparison") or {}).get("status") or "")
        for entry in entries
        if isinstance(entry.get("lineOrderComparison"), dict)
    ]
    timeline_entries = []
    for entry in entries[:DETAIL_TIMELINE_LIMIT]:
        compact = {
            "timeline": entry.get("timeline") or "",
            "file": entry.get("file") or "",
            "lineIds": entry.get("lineIds") or [],
            "flowCount": entry.get("flowCount") or 0,
            "linkedActionCount": entry.get("linkedActionCount") or 0,
            "comparison": entry.get("lineOrderComparison") or {},
        }
        timeline_entries.append({key: value for key, value in compact.items() if value not in (None, "", [], {})})

    line_actions = [
        row
        for _line_id, row in sorted(
            line_flow_rows.items(),
            key=lambda item: current_order.index(item[0]) if item[0] in current_order else len(current_order),
        )
    ]
    out = {
        "source": {
            "file": rel_path(evidence_path),
            "key": conv_key,
            "entries": len(entries),
        },
        "status": comparison.get("status") or "missing",
        "timelineStatus": _aggregate_status(timeline_statuses),
        "flowCount": sum(int(entry.get("flowCount") or 0) for entry in entries),
        "lineCount": len(action_line_ids),
        "linkedActionCount": sum(int(entry.get("linkedActionCount") or 0) for entry in entries),
        "decodedActionCount": sum(int(entry.get("decodedActionCount") or 0) for entry in entries),
        "unparsedActionCount": sum(int(entry.get("unparsedActionCount") or 0) for entry in entries),
        "actionKindCounts": _merge_counts(entries, "actionKindCounts"),
        "layoutCounts": _merge_counts(entries, "layoutCounts"),
        "comparison": comparison,
        "lineActions": line_actions,
        "timelineEntries": timeline_entries,
    }
    if len(entries) > DETAIL_TIMELINE_LIMIT:
        out["omittedTimelineEntries"] = len(entries) - DETAIL_TIMELINE_LIMIT
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--mono-root", action="append", type=Path, help="MonoBehaviour directory or parent root to scan. May be repeated.")
    parser.add_argument("--line-orders", type=Path, help="timeline_line_orders.json path.")
    parser.add_argument("--out", type=Path, help="Output timeline_action_evidence.json path.")
    args = parser.parse_args(argv)

    export_root = args.export_root if args.export_root.is_absolute() else ROOT / args.export_root
    recovery_root = export_root / "recovered" / "AnimeStudio-cli"
    mono_roots = args.mono_root or iter_default_mono_roots(recovery_root)
    line_orders = args.line_orders or recovery_root / "timeline_line_orders.json"
    out_path = args.out or recovery_root / "timeline_action_evidence.json"
    line_orders = line_orders if line_orders.is_absolute() else ROOT / line_orders
    out_path = out_path if out_path.is_absolute() else ROOT / out_path
    build_timeline_action_evidence(
        mono_roots=mono_roots,
        line_orders_path=line_orders,
        out_path=out_path,
        write=True,
    )


if __name__ == "__main__":
    main()
