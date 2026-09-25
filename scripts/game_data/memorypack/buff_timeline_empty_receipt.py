"""Audit null/empty BuffData timeline lists against native ownership and bytes.

This reads the separately authenticated compact-branch corpus receipt, then
rechecks its report hash, exported logical bytes and exact following tail.  A
positive timeline list remains a structural endpoint and is never promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack.buff_timeline_empty_native import (
    CONTRACT_PATH,
    decode_empty_timeline_suffix,
    validate_current_native_contract,
)


PREFIX = "Data/Json/BuffData/"
COMPACT_SCHEMA = "endfield.buff-stacking-compact-corpus-receipt.v1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def audit_empty_timeline(
    compact_report: Path, buff_report: Path, export_root: Path,
    *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    expected = expected_input_set_sha256.upper()
    native = validate_current_native_contract()
    if native.get("status") != "validated":
        raise ValueError(f"buff-timeline-empty:native={native.get('status')} {native.get('detail', '')}")
    compact = json.loads(compact_report.read_text(encoding="utf-8"))
    if (compact.get("schema") != COMPACT_SCHEMA
            or compact.get("status") != "complete"
            or compact.get("publicationEligible") is not True
            or compact.get("inputSetSha256") != expected):
        raise ValueError("buff-timeline-empty:compact-report-gate")
    buff_digest = _sha256_file(buff_report)
    if compact.get("sourceReport", {}).get("sha256") != buff_digest:
        raise ValueError("buff-timeline-empty:source-report-sha")
    rows = compact.get("rows")
    if (not isinstance(rows, list) or not rows
            or compact.get("counts", {}).get("files") != len(rows)):
        raise ValueError("buff-timeline-empty:compact-row-count")
    sources = [row.get("source") for row in rows]
    if (any(not isinstance(source, str) or not source.startswith(PREFIX)
            or "/" in source[len(PREFIX):] for source in sources)
            or len(set(sources)) != len(sources)):
        raise ValueError("buff-timeline-empty:source-identity")
    export_sources = {PREFIX + path.name for path in export_root.glob("*.json")}
    if set(sources) != export_sources:
        raise ValueError(f"buff-timeline-empty:export-set added={len(export_sources-set(sources))} "
                         f"missing={len(set(sources)-export_sources)}")

    counts: Counter[str] = Counter()
    exact_rows = []
    for row in sorted(rows, key=lambda value: value["source"]):
        source = row["source"]
        data = (export_root / source[len(PREFIX):]).read_bytes()
        digest = hashlib.sha256(data).hexdigest().upper()
        if len(data) != row.get("physicalEof") or digest != row.get("logicalSha256"):
            raise ValueError(f"buff-timeline-empty:logical-source={source}")
        count = row.get("timelineCount")
        count_start = row.get("tagRange", [None, None])[1]
        if type(count) is not int or type(count_start) is not int:
            raise ValueError(f"buff-timeline-empty:missing-timeline-range={source}")
        counts["files"] += 1
        if count > 0:
            if row.get("timelineBodyStatus") != "opaque-structural-endpoint":
                raise ValueError(f"buff-timeline-empty:positive-status={source}")
            counts["positiveUnresolved"] += 1
            continue
        if count not in (-1, 0) or row.get("timelineBodyStatus") != "empty-or-null":
            raise ValueError(f"buff-timeline-empty:invalid-empty-branch={source}")
        decoded = decode_empty_timeline_suffix(
            data, count_start, native_validation=native,
        )
        if (decoded["count"] != count
                or decoded["followingStart"] != row.get("triggerIntervalOffset")
                or decoded["followingEnd"] != len(data)):
            raise ValueError(f"buff-timeline-empty:following-tail-join={source}")
        counts[decoded["representation"]] += 1
        exact_rows.append({
            "source": source, "logicalSha256": digest,
            "physicalEof": len(data), "acceptedAnchor": row["acceptedAnchor"],
            "timelineList": {
                "startOffset": count_start,
                "consumedEnd": decoded["consumedEnd"],
                "count": count, "representation": decoded["representation"],
                "wholeTimelineListExact": True,
            },
            "followingTriggerTail": {
                "startOffset": decoded["followingStart"],
                "consumedEnd": decoded["followingEnd"],
            },
        })
    if counts["files"] != counts["null"] + counts["empty"] + counts["positiveUnresolved"]:
        raise ValueError("buff-timeline-empty:count-accounting")
    return {
        "schema": "endfield.buff-timeline-empty-corpus-receipt.v1",
        "status": "complete", "publicationEligible": True,
        "inputSetSha256": expected,
        "compactReport": {"path": str(compact_report),
                          "sha256": _sha256_file(compact_report)},
        "sourceReport": {"path": str(buff_report), "sha256": buff_digest},
        "nativeContract": {"path": str(CONTRACT_PATH), "status": native["status"]},
        "counts": dict(sorted(counts.items())),
        "rows": exact_rows,
        "wholeBuffSchemaExact": False,
        "evidenceBoundary": {
            "direct": "Selected native BuffData source context reads List<TimelineActionData> and stores it in timelineActions before reading triggerInterval.",
            "conditional": "For each verified null or zero count, four count bytes immediately rejoin the separately parsed triggerInterval and two flags at physical EOF.",
            "structuralOnly": "Positive timeline lists still use a structural endpoint and retain their nested payload ownership gap.",
            "unresolved": "Live list formatter selection, positive timeline element parity, and whole BuffData recursive naming remain open.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compact-report", type=Path, required=True)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit_empty_timeline(
        args.compact_report, args.buff_report, args.export_root,
        expected_input_set_sha256=args.expected_input_set_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "counts": result["counts"],
                      "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
