#!/usr/bin/env python3
"""Audit real FindTargetAction selector/TargetSettings boundary evidence.

The IL2CPP body audit proves setter order and field offsets, but the WebUI
index builder still needs sample-byte proof before it can consume
FindTargetAction chains. This script scans exported BuffData files through the
existing `build_data_index.py` decoder and records the real opaque
FindTargetAction middle bytes that still block promotion.

Output:

    reports/mission_order/findtarget_selector_boundary_audit.json
    reports/mission_order/findtarget_selector_boundary_audit.md
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

BUILD_DATA_INDEX = ROOT / "scripts" / "build_data_index.py"
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
REPORT_DIR = ROOT / "reports" / "mission_order"
DEFAULT_JSON = REPORT_DIR / "findtarget_selector_boundary_audit.json"
DEFAULT_MD = REPORT_DIR / "findtarget_selector_boundary_audit.md"
FIND_TARGET_TAG_HEX = "0x009f"


def load_build_data_index() -> Any:
    spec = importlib.util.spec_from_file_location("endfield_build_data_index", BUILD_DATA_INDEX)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {BUILD_DATA_INDEX}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path)


def parse_offset(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value or "0")
    return int(text, 16 if text.lower().startswith("0x") else 10)


def buffdata_files(export_root: Path) -> list[Path]:
    structured = export_root / "structured"
    return sorted(structured.glob("**/Data/Json/BuffData/*.json"))


def scan_target_settings_candidates(
    helper: Any,
    data: bytes,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    candidates = []
    for offset in range(start, end):
        try:
            decoded, candidate_end = helper.read_buff_target_settings_envelope_partial(
                data,
                offset,
                end,
                "findTargetAction.bodyMiddle.targetSettingsCandidate",
            )
        except (ValueError, IndexError, struct.error, UnicodeDecodeError, TypeError, AttributeError):
            continue
        candidates.append(
            {
                "offset": helper.format_offset(offset),
                "relativeOffset": helper.format_offset(offset - start),
                "end": helper.format_offset(candidate_end),
                "relativeEnd": helper.format_offset(candidate_end - start),
                "bytes": decoded.get("bytes"),
                "shape": decoded.get("shape"),
                "stringSlotValue": decoded.get("stringSlotValue"),
                "tailU32Candidate": decoded.get("tailU32Candidate"),
            }
        )
    return candidates


def selector_tag_byte_stats(raw: bytes) -> dict[str, Any]:
    # This is deliberately weak evidence: byte hits can only prioritize manual
    # inspection. Selector tags are one-byte union tags, but without a proven
    # enclosing reader state they are not boundaries.
    ranges = {
        "finder": range(0x00, 0x14),
        "validator": range(0x00, 0x0B),
        "postProcessor": range(0x00, 0x09),
    }
    member3_offsets = [index for index, value in enumerate(raw) if value == 3]
    return {
        "memberCount3Offsets": [f"0x{offset:x}" for offset in member3_offsets[:24]],
        "memberCount3Count": len(member3_offsets),
        "zeroByteCount": raw.count(0),
        "nonZeroTagByteCounts": {
            name: sum(1 for byte in raw if byte != 0 and byte in values)
            for name, values in ranges.items()
        },
    }


def iter_findtarget_items(post_id_prefix: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decoded_items = []
    ambiguous_records = []
    for record in post_id_prefix.get("timelineActionRecords") or []:
        sequence = record.get("sequenceActionData") or {}
        items = sequence.get("actionDataItems") or []
        for item in items:
            if item.get("tag") == FIND_TARGET_TAG_HEX or "FindTargetAction" in str(item.get("name") or ""):
                decoded_items.append({"record": record, "sequence": sequence, "item": item})
        if (
            sequence.get("firstActionTag") == FIND_TARGET_TAG_HEX
            and sequence.get("actionDataSplit") == "ambiguous-union-tag-boundaries"
        ):
            ambiguous_records.append({"record": record, "sequence": sequence})
    return decoded_items, ambiguous_records


def sample_row(
    *,
    helper: Any,
    path: Path,
    data: bytes,
    record: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, Any]:
    decoded = item.get("decoded") or {}
    middle = decoded.get("bodyMiddleOpaque") or {}
    start = parse_offset(middle.get("offset"))
    byte_count = int(middle.get("bytes") or 0)
    end = start + byte_count
    raw = data[start:end]
    sha = hashlib.sha256(raw).hexdigest()
    candidates = scan_target_settings_candidates(helper, data, start, end)
    return {
        "path": repo_rel(path),
        "recordIndex": record.get("index"),
        "recordOffset": record.get("offset"),
        "itemIndex": item.get("index"),
        "itemOffset": item.get("offset"),
        "itemBytes": item.get("bytes"),
        "bodyMiddleOffset": middle.get("offset"),
        "bodyMiddleBytes": byte_count,
        "bodyMiddleSha256": sha,
        "targetSettingsCandidateCount": len(candidates),
        "targetSettingsCandidates": candidates,
        "selectorTagByteStats": selector_tag_byte_stats(raw),
        "targetGroupKey": decoded.get("targetGroupKey"),
        "selectorOwner": decoded.get("selectorOwner"),
        "selectorOwnerContextKey": decoded.get("selectorOwnerContextKey"),
        "target": decoded.get("target"),
        "useAdvancedDirectionSetting": decoded.get("useAdvancedDirectionSetting"),
        "useCenterEntityMountPoint": decoded.get("useCenterEntityMountPoint"),
        "tailFieldOffsets": decoded.get("tailFieldOffsets") or {},
        "stringHits": middle.get("stringHits") or [],
        "prefixHex": middle.get("prefixHex"),
        "tailHex": middle.get("tailHex"),
    }


def ambiguous_row(path: Path, record: dict[str, Any], sequence: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": repo_rel(path),
        "recordIndex": record.get("index"),
        "recordOffset": record.get("offset"),
        "recordBytes": record.get("bytes"),
        "actionDataOffset": sequence.get("actionDataOffset"),
        "actionDataBytes": sequence.get("actionDataBytes"),
        "actionDataCount": sequence.get("actionDataCount"),
        "firstActionName": sequence.get("firstActionName"),
        "firstActionTag": sequence.get("firstActionTag"),
        "splitStatus": sequence.get("actionDataSplit"),
        "stringHits": sequence.get("stringHits") or [],
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    helper = load_build_data_index()
    files = buffdata_files(args.export_root)
    samples: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    errors = []

    for path in files:
        try:
            data = path.read_bytes()
            decoded = helper.decode_buff_memorypack(path, data, len(data))
        except Exception as exc:  # keep the audit diagnostic, not build-blocking
            errors.append({"path": repo_rel(path), "error": f"{type(exc).__name__}: {str(exc)[:180]}"})
            continue
        post_id_prefix = ((decoded or {}).get("decoded") or {}).get("postIdPrefix") or {}
        item_refs, ambiguous_refs = iter_findtarget_items(post_id_prefix)
        for ref in item_refs:
            samples.append(
                sample_row(
                    helper=helper,
                    path=path,
                    data=data,
                    record=ref["record"],
                    item=ref["item"],
                )
            )
        for ref in ambiguous_refs:
            ambiguous.append(ambiguous_row(path, ref["record"], ref["sequence"]))

    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        by_sha[str(row.get("bodyMiddleSha256"))].append(row)
    unique_shapes = []
    for sha, rows in sorted(by_sha.items(), key=lambda item: (-len(item[1]), item[0])):
        first = rows[0]
        unique_shapes.append(
            {
                "bodyMiddleSha256": sha,
                "sampleCount": len(rows),
                "bodyMiddleBytes": first.get("bodyMiddleBytes"),
                "targetSettingsCandidateCount": first.get("targetSettingsCandidateCount"),
                "targetGroupKeys": sorted({str(row.get("targetGroupKey") or "") for row in rows}),
                "examplePath": first.get("path"),
                "exampleRecordIndex": first.get("recordIndex"),
                "exampleItemOffset": first.get("itemOffset"),
                "prefixHex": first.get("prefixHex"),
                "tailHex": first.get("tailHex"),
                "stringHits": first.get("stringHits") or [],
                "selectorTagByteStats": first.get("selectorTagByteStats") or {},
            }
        )

    return {
        "metadata": {
            "exportRoot": repo_rel(args.export_root),
            "fileCount": len(files),
            "helper": repo_rel(BUILD_DATA_INDEX),
        },
        "settings": {
            "maxSamplesMarkdown": args.markdown_samples,
            "maxAmbiguousMarkdown": args.markdown_ambiguous,
        },
        "summary": {
            "buffDataFileCount": len(files),
            "decodedFindTargetItemCount": len(samples),
            "uniqueBodyMiddleShapeCount": len(unique_shapes),
            "ambiguousFirstFindTargetRecordCount": len(ambiguous),
            "targetSettingsCandidateTotal": sum(int(row.get("targetSettingsCandidateCount") or 0) for row in samples),
            "targetSettingsCandidateShapeCount": sum(
                1 for row in unique_shapes if int(row.get("targetSettingsCandidateCount") or 0) > 0
            ),
            "decodeErrorCount": len(errors),
            "bodyMiddleSizeCounts": dict(Counter(int(row.get("bodyMiddleBytes") or 0) for row in samples).most_common()),
        },
        "interpretation": [
            "Current TargetSettings envelope parser accepts zero candidates inside decoded FindTargetAction body-middle bytes when targetSettingsCandidateTotal is 0.",
            "Selector tag byte hits are prioritization hints only; they are not boundaries until a reader state and exact end offset are proven.",
            "Ambiguous first-FindTarget records remain unsplit because header-only union scanning is not safe enough for chain consumption.",
        ],
        "uniqueBodyMiddleShapes": unique_shapes,
        "samples": samples,
        "ambiguousFirstFindTargetRecords": ambiguous,
        "decodeErrors": errors[:100],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    settings = payload.get("settings") or {}
    lines = [
        "# FindTarget Selector Boundary Audit",
        "",
        f"- BuffData files scanned: `{summary.get('buffDataFileCount')}`",
        f"- decoded FindTarget items: `{summary.get('decodedFindTargetItemCount')}`",
        f"- unique body-middle shapes: `{summary.get('uniqueBodyMiddleShapeCount')}`",
        f"- ambiguous first-FindTarget records: `{summary.get('ambiguousFirstFindTargetRecordCount')}`",
        f"- TargetSettings candidates inside body-middle: `{summary.get('targetSettingsCandidateTotal')}`",
        f"- decode errors: `{summary.get('decodeErrorCount')}`",
        "",
        "## Interpretation",
        "",
    ]
    for item in payload.get("interpretation") or []:
        lines.append(f"- {md_escape(item)}")

    lines.extend(["", "## Unique Body-Middle Shapes", ""])
    for row in (payload.get("uniqueBodyMiddleShapes") or [])[: int(settings.get("maxSamplesMarkdown") or 20)]:
        keys = ", ".join(row.get("targetGroupKeys") or [])
        string_hits = ", ".join(str(hit.get("value") or "") for hit in (row.get("stringHits") or [])[:4])
        lines.append(
            f"- `{row.get('bodyMiddleSha256')}` count=`{row.get('sampleCount')}` "
            f"bytes=`{row.get('bodyMiddleBytes')}` targetGroups=`{md_escape(keys)}` "
            f"targetSettingsCandidates=`{row.get('targetSettingsCandidateCount')}`"
        )
        lines.append(
            f"  - example: `{md_escape(row.get('examplePath', ''))}` "
            f"record=`{row.get('exampleRecordIndex')}` itemOffset=`{row.get('exampleItemOffset')}`"
        )
        if string_hits:
            lines.append(f"  - strings: `{md_escape(string_hits)}`")
        stats = row.get("selectorTagByteStats") or {}
        lines.append(
            "  - selector byte hints: "
            f"memberCount3=`{stats.get('memberCount3Count')}` "
            f"nonZeroTagBytes=`{md_escape(json.dumps(stats.get('nonZeroTagByteCounts') or {}, sort_keys=True))}`"
        )

    lines.extend(["", "## Ambiguous First-FindTarget Records", ""])
    ambiguous = payload.get("ambiguousFirstFindTargetRecords") or []
    if not ambiguous:
        lines.append("- None.")
    for row in ambiguous[: int(settings.get("maxAmbiguousMarkdown") or 30)]:
        strings = ", ".join(str(hit.get("value") or "") for hit in (row.get("stringHits") or [])[:4])
        lines.append(
            f"- `{md_escape(row.get('path', ''))}` record=`{row.get('recordIndex')}` "
            f"actionDataCount=`{row.get('actionDataCount')}` bytes=`{row.get('actionDataBytes')}` "
            f"split=`{md_escape(row.get('splitStatus', ''))}`"
        )
        if strings:
            lines.append(f"  - strings: `{md_escape(strings)}`")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--markdown-samples", type=int, default=24)
    parser.add_argument("--markdown-ambiguous", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, render_markdown(payload))
    summary = payload["summary"]
    print(f"FindTarget selector boundary audit: {args.json}")
    print(f"FindTarget selector boundary report: {args.markdown}")
    print(
        "decodedFindTarget="
        f"{summary['decodedFindTargetItemCount']} "
        f"uniqueShapes={summary['uniqueBodyMiddleShapeCount']} "
        f"targetSettingsCandidates={summary['targetSettingsCandidateTotal']} "
        f"ambiguousFirstFindTarget={summary['ambiguousFirstFindTargetRecordCount']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
