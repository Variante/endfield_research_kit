"""Audit physically isolated Marker15 targets in selected Streaming scenes.

This gate reopens authenticated StreamingChunkData files, uses the maintained
FlatBuffer framing to find certified ranges and nested target pointers, and
reports where one Marker15 pointer is alone in a 16-byte complement. It does
not name or claim ownership of those bytes or infer a general record width.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.corpus_common import atomic_write_text, validate_provenance
from scripts.game_data.streaming import framing
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.streaming-marker15-gap-corpus.v1"
BLOCK_TYPE = 15


class Marker15GapError(ValueError):
    """The selected audit or a structural pointer/certified range was invalid."""


def _load_rows(summary_path: Path, ledger_path: Path, expected_input_set: str,
               scenes: tuple[str, ...]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = json.loads(summary_path.read_text(encoding="utf8"))
    headers: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    prefixes = tuple(f"/PC/{scene}/Streaming/StreamingChunkData_" for scene in scenes)
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if row.get("recordType") == "audit_header":
                headers.append(row)
                continue
            if row.get("recordType") != "file" or row.get("blockTypeValue") != BLOCK_TYPE:
                continue
            name = row.get("fileName")
            if not isinstance(name, str) or not any(prefix in name for prefix in prefixes):
                continue
            if (row.get("boundaryStatus") != "boundary_verified"
                    or str(row.get("inputSetSha256", "")).upper() != expected_input_set.upper()
                    or row.get("encrypted") is not False):
                raise Marker15GapError(f"ledger line {line_number}: unverified source {name}")
            rows.append(row)
    if len(headers) != 1:
        raise Marker15GapError(f"expected one outer ledger header; actual {len(headers)}")
    failures, provenance = validate_provenance(summary, headers[0], ledger_path, expected_input_set)
    if failures:
        raise Marker15GapError(f"outer audit provenance mismatch: {failures[:4]}")
    if not rows:
        raise Marker15GapError(f"no StreamingChunkData files under selected scenes {scenes}")
    found = {scene for scene in scenes if any(f"/PC/{scene}/Streaming/StreamingChunkData_" in row["fileName"] for row in rows)}
    if found != set(scenes):
        raise Marker15GapError(f"selected scenes absent from current ledger: {sorted(set(scenes)-found)}")
    provenance["framingReaderSha256"] = hashlib.sha256(Path(framing.__file__).read_bytes()).hexdigest().upper()
    provenance["corpusGateSha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
    return provenance, rows


def _targets(clear: bytes, root: dict[str, Any]) -> list[dict[str, int]]:
    """Rewalk only the already proven row/nested-vector grammar."""
    result: list[dict[str, int]] = []
    start, count, _ = framing._bounded_vector(clear, root, 5, 4, "root5")
    for row_index in range(count):
        row_slot = start + 4 + row_index * 4
        row = framing._table_layout(clear, framing._bounded_anonymous_target(clear, row_slot, "row"))
        field3 = framing._field_address(row, 3)
        if field3 is None or framing._field_address(row, 5) is None:
            continue
        nested = framing._table_layout(clear, framing._bounded_anonymous_target(clear, field3, "nested"))
        keys, n, _ = framing._bounded_vector(clear, nested, 3, 4, "nested keys")
        markers, nm, _ = framing._bounded_vector(clear, nested, 4, 1, "nested markers")
        slots, nt, _ = framing._bounded_vector(clear, nested, 5, 4, "nested slots")
        if n != nm or n != nt:
            raise Marker15GapError(f"nested vector count mismatch at row {row_index}")
        for index in range(n):
            slot = slots + 4 + index * 4
            result.append({
                "row": row_index,
                "index": index,
                "key": framing._u32(clear, keys + 4 + index * 4),
                "marker": clear[markers + 4 + index],
                "slot": slot,
                "target": framing._bounded_anonymous_target(clear, slot, "nested target"),
            })
    return result


def _one_file(row: dict[str, Any]) -> dict[str, Any]:
    path = Path(row["physicalChunkPath"])
    with path.open("rb") as stream:
        stream.seek(row["offset"])
        packed = stream.read(row["length"])
    if len(packed) != row["length"]:
        raise Marker15GapError(f"short source read {row['fileName']}")
    md5 = hashlib.md5(packed).hexdigest().upper()
    if md5 != str(row["recomputedFileDataMd5"]).upper():
        raise Marker15GapError(f"source MD5 mismatch {row['fileName']}: expected {row['recomputedFileDataMd5']}, actual {md5}")
    parsed = framing.parse_streaming_file("streaming", packed, allow_raw="DevOnly" in row["fileName"],
                                          include_certified_ranges=True)
    clear = packed if parsed["encoding"] == "raw_flatbuffer" else framing._decode_compressed(packed)
    root = framing._root_layout(clear)
    root["tableOffset"] = root["rootOffset"]
    targets = _targets(clear, root)
    marker15 = [item for item in targets if item["marker"] == 15]
    recorded = parsed["anonymousParallelSubgraph"]["nestedMarker15References"]["count"]
    if len(marker15) != recorded:
        raise Marker15GapError(f"reader Marker15 count mismatch {row['fileName']}: {len(marker15)} vs {recorded}")
    certified = sorted((start, end) for start, end, _ in parsed["decodedCertifiedRanges"])
    witnesses: list[dict[str, Any]] = []
    for item in marker15:
        target = item["target"]
        if any(start <= target < end for start, end in certified):
            continue
        left = max((end for start, end in certified if end <= target), default=0)
        right = min((start for start, end in certified if start >= target), default=len(clear))
        if target != left or right != target + 16:
            continue
        occupants = [other for other in targets if left <= other["target"] < right]
        if len(occupants) != 1 or occupants[0] is not item:
            continue
        witnesses.append({"row": item["row"], "index": item["index"],
                          "key": f"{item['key']:08X}", "slot": item["slot"],
                          "target": target, "gapStart": left, "gapEnd": right,
                          "raw16Hex": clear[target:right].hex().upper()})
    return {"virtualPath": row["fileName"], "packedMd5": md5,
            "packedSha256": hashlib.sha256(packed).hexdigest().upper(),
            "decodedLength": len(clear), "marker15ReferenceCount": len(marker15),
            "exclusive16Witnesses": witnesses}


def sweep(summary_path: Path, ledger_path: Path, expected_input_set: str,
          scenes: tuple[str, ...]) -> dict[str, Any]:
    """Inspect all StreamingChunkData files in each selected scene."""
    if not scenes or any(not scene or "/" in scene or "\\" in scene for scene in scenes):
        raise Marker15GapError("--scene must name one or more plain scene directory names")
    provenance, rows = _load_rows(summary_path, ledger_path, expected_input_set, scenes)
    files = [_one_file(row) for row in sorted(rows, key=lambda row: row["fileName"])]
    witnesses = [w for file in files for w in file["exclusive16Witnesses"]]
    return {
        "schema": SCHEMA,
        "status": "validated",
        "evidenceBoundary": "exact physical 16-byte complement to certified ranges for selected files only; no producer, native selector, general record width, or semantic field ownership",
        "source": provenance,
        "selection": {"scenes": list(scenes), "family": "StreamingChunkData", "allMatchingFiles": True},
        "summary": {"files": len(files), "marker15References": sum(f["marker15ReferenceCount"] for f in files),
                    "exclusive16Witnesses": len(witnesses),
                    "witnessKeys": dict(sorted(Counter(w["key"] for w in witnesses).items()))},
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", action="append", required=True, help="scene directory name under Data/Streaming/PC")
    parser.add_argument("--outer-summary", type=Path, default=REPO_ROOT / "reports/animestudio/vfs_understanding_latest.json")
    parser.add_argument("--outer-ledger", type=Path, default=REPO_ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz")
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports/animestudio/streaming_marker15_gap_latest.json")
    args = parser.parse_args()
    try:
        report = sweep(args.outer_summary, args.outer_ledger, args.expected_input_set_sha256, tuple(args.scene))
    except Exception as exc:
        print(f"marker15 gap audit failed: {type(exc).__name__}: {exc}")
        return 2
    atomic_write_text(args.output, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"marker15 gap audit validated: {report['summary']}; report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
