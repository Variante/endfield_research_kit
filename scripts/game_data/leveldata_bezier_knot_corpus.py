"""Sweep exported LevelData spline knots against the selected native layout."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import EXPORT_ROOT, NATIVE_EVIDENCE_VALIDATED, write_report_json
from scripts.game_data.leveldata_bezier_knot_native import validate_bezier_knot_native
from scripts.game_data.leveldata_binary import frame_leveldata_named_prefix
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.leveldata-bezier-knot-corpus.v1"
DEFAULT_REPORT = REPO_ROOT / "reports/game_data/leveldata_bezier_knot_corpus.json"


def check_spline_knots(data: bytes, spline: dict[str, Any], *, stride: int) -> tuple[int, int]:
    """Verify list boundaries and each knot's five named 14-float partitions."""

    spline_rows = spline["rows"]
    knot_rows = 0
    for row in spline_rows:
        collection = row["knots"]
        count = collection["count"]
        start = collection["startOffset"]
        if struct.unpack_from("<i", data, start)[0] != count:
            raise ValueError(f"knot-count-offset={start}")
        values = collection["value"] or []
        if count != -1 and len(values) != count:
            raise ValueError(f"knot-count={count} rows={len(values)}")
        expected_end = start + 4 + len(values) * stride
        if collection["endOffset"] != expected_end:
            raise ValueError(f"knot-end={collection['endOffset']} expected={expected_end}")
        for index, knot in enumerate(values):
            knot_start = start + 4 + index * stride
            if knot["startOffset"] != knot_start or knot["endOffset"] != knot_start + stride:
                raise ValueError(f"knot-boundary={knot_start}")
            fields = [*knot["position"], *knot["tangentIn"], *knot["tangentOut"],
                      *knot["rotation"], knot["width"]]
            if len(fields) != 14 or struct.pack("<14f", *fields) != data[knot_start:knot_start + stride]:
                raise ValueError(f"knot-values={knot_start}")
        knot_rows += len(values)
    return len(spline_rows), knot_rows


def audit_bezier_knot_corpus(
    export_root: Path = EXPORT_ROOT, *, game_root: Path | None = None,
    native_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    native = native_report if native_report is not None else validate_bezier_knot_native(game_root=game_root)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": native["status"],
        "exportRoot": str(Path(export_root).resolve()),
        "native": native,
        "inputSetSha256": None,
        "files": 0,
        "exactNamedFiles": 0,
        "splineRows": 0,
        "knotRows": 0,
        "failures": [],
        "evidenceBoundary": (
            "Native formatter fast-path stride and native field offsets are gated separately; "
            "the selected exported LevelData files must close all 43 fields through EOF, "
            "and every spline knot must occupy that stride with the named float partitions."
        ),
    }
    if native["status"] != NATIVE_EVIDENCE_VALIDATED:
        return report
    stride = native["wireStride"]
    if stride != struct.calcsize("<14f"):
        report["status"] = "validation_failed"
        report["failures"].append({"gate": "codec_native_stride", "native": stride,
                                   "codec": struct.calcsize("<14f")})
        return report
    directory = Path(export_root) / "game/Json/LevelData"
    paths = sorted(directory.rglob("*.json")) if directory.is_dir() else []
    if not paths:
        report["status"] = "validation_failed"
        report["failures"].append({"gate": "source_files", "path": str(directory)})
        return report
    digest = hashlib.sha256()
    for path in paths:
        source = path.relative_to(export_root).as_posix()
        data = path.read_bytes()
        digest.update(source.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
        report["files"] += 1
        try:
            decoded = frame_leveldata_named_prefix(data)
            if decoded["status"] != "exact_named_schema" or decoded["bytesConsumed"] != len(data):
                raise ValueError(f"frame={decoded['status']} cursor={decoded['bytesConsumed']} length={len(data)}")
            report["exactNamedFiles"] += 1
            spline = decoded["fields"]["splines"]
            rows, knots = check_spline_knots(data, spline, stride=stride)
            report["splineRows"] += rows
            report["knotRows"] += knots
        except (KeyError, ValueError, struct.error, TypeError) as exc:
            report["failures"].append({"source": source, "detail": str(exc)[:400]})
    report["inputSetSha256"] = digest.hexdigest().upper()
    report["status"] = (
        NATIVE_EVIDENCE_VALIDATED
        if not report["failures"] and report["knotRows"] > 0 else "validation_failed"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    report = audit_bezier_knot_corpus(args.export_root, game_root=args.game_root)
    write_report_json(args.report, report)
    print(json.dumps({key: report[key] for key in (
        "status", "files", "exactNamedFiles", "splineRows", "knotRows", "failures",
    )}, ensure_ascii=False))
    return 0 if report["status"] == NATIVE_EVIDENCE_VALIDATED else 1


if __name__ == "__main__":
    raise SystemExit(main())
