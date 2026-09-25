"""Check native main-path selection against authenticated FlatBuffer root IDs.

The selected GetPath body extracts a high nibble and two bytes from a packed
grid value. This audit rechecks its named native claims, then tests that every
current fb_main filename carries the same packed value as its root UniqueId.
It does not observe a live grid request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.dynamic_main_native import _checked_dump_path
from scripts.game_data.dynamic_streaming import _field_span, _root_layout
from scripts.game_data.dynamic_streaming_config_join import _selected_runtime_report
from scripts.game_data.dynamic_visibility_state_join import _selected_inputs
from scripts.repo_paths import REPO_ROOT


FORMAT = "endfield.dynamic-main-path-join.v1"
DEFAULT_MAIN_REPORT = REPO_ROOT / "reports/animestudio/dynamic_root_comp_native_latest.json"
DEFAULT_RUNTIME_REPORT = REPO_ROOT / "reports/animestudio/dynamic_visibility_runtime_claims_latest.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/dynamic_main_path_join_latest.json"
MAIN_NAME = re.compile(r"fb_main_([0-9a-fA-F])_(\d{4})_(\d{4})\.bytes$")
PATH_METHOD = "DynamicSceneFbDataLoader.GetPath"


class DynamicMainPathJoinError(ValueError):
    """Selected evidence or an authored filename/root identity differs."""


def _filename_unique_id(source: str) -> tuple[int, int, int, int]:
    name = source.replace("\\", "/").rsplit("/", 1)[-1]
    match = MAIN_NAME.fullmatch(name)
    if match is None:
        raise DynamicMainPathJoinError(f"unexpected main filename: {source}")
    bit = int(match.group(1), 16)
    x = int(match.group(2))
    z = int(match.group(3))
    if not 0 <= x <= 255 or not 0 <= z <= 255:
        raise DynamicMainPathJoinError(f"main filename coordinate exceeds packed byte: {source}")
    return (bit << 16) | (z << 8) | x, bit, x, z


def _root_unique_id(data: bytes, source: str) -> int:
    layout = _root_layout(data)
    if layout["fieldCount"] != 5 or layout["presentFields"] != [0, 1, 2, 3, 4]:
        raise DynamicMainPathJoinError(f"{source}: main root layout differs")
    at = _field_span(data, layout, 2, 4)
    if at is None:
        raise DynamicMainPathJoinError(f"{source}: main root UniqueId absent")
    return struct.unpack_from("<I", data, at)[0]


def _file_rows(main: dict[str, Any], input_root: Path) -> tuple[list[dict[str, Any]], Counter[str]]:
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    seen: set[str] = set()
    for entry in main["files"]:
        source = entry["path"]
        if source.casefold() in seen:
            raise DynamicMainPathJoinError(f"duplicate current main file: {source}")
        seen.add(source.casefold())
        data = _checked_dump_path(input_root, source).read_bytes()
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if actual_md5 != entry["fileDataMd5"].upper():
            raise DynamicMainPathJoinError(
                f"{source}: dump differs from authenticated RootComp row "
                f"expectedMd5={entry['fileDataMd5']} actualMd5={actual_md5}"
            )
        from_name, bit, x, z = _filename_unique_id(source)
        from_root = _root_unique_id(data, source)
        if from_name != from_root:
            raise DynamicMainPathJoinError(
                f"{source}: filename/root UniqueId differs "
                f"filename={from_name} root={from_root}"
            )
        counts["files"] += 1
        counts[f"bit_{bit:x}"] += 1
        rows.append({
            "path": source,
            "fileDataMd5": actual_md5,
            "rootUniqueId": from_root,
            "bit": bit,
            "x": x,
            "z": z,
        })
    return rows, counts


def audit(
    *, gameassembly: Path, metadata: Path, main_report: Path,
    runtime_report: Path, input_root: Path, expected_input_set_sha256: str,
) -> dict[str, Any]:
    main_raw = main_report.read_bytes()
    main = json.loads(main_raw)
    _layout, receipt, _digest = _selected_inputs(
        main, gameassembly=gameassembly, metadata=metadata,
        expected_input_set_sha256=expected_input_set_sha256,
    )
    runtime_raw = runtime_report.read_bytes()
    runtime = json.loads(runtime_raw)
    _selected_runtime_report(runtime, receipt)
    method = next((row for row in runtime["methods"] if row["symbol"] == PATH_METHOD), None)
    if method is None:
        raise DynamicMainPathJoinError(f"runtime report lacks {PATH_METHOD}")
    rows, counts = _file_rows(main, input_root)
    if counts["files"] != main["corpus"]["files"]:
        raise DynamicMainPathJoinError("main file census differs from selected native report")
    return {
        "format": FORMAT,
        "status": "validated",
        "inputSetSha256": expected_input_set_sha256.upper(),
        "nativeInputs": receipt,
        "sourceReports": {
            "mainSha256": hashlib.sha256(main_raw).hexdigest().upper(),
            "runtimeSha256": hashlib.sha256(runtime_raw).hexdigest().upper(),
            "getPathBodySha256": method["bodySha256"],
        },
        "counts": dict(counts),
        "files": rows,
        "evidenceBoundary": {
            "direct": "The selected GetPath body shifts and masks a packed grid value before replacing indexed main-filename characters; its named claims and body hash are rechecked.",
            "exact": "Every current dump matches its authenticated VFS MD5 and its fb_main filename encodes the same UInt32 as the FlatBuffer root UniqueId.",
            "unresolved": "The selected live grid, timing of file requests, and success of runtime reads are not observed.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--main-input-root", type=Path, required=True)
    parser.add_argument("--main-report", type=Path, default=DEFAULT_MAIN_REPORT)
    parser.add_argument("--runtime-report", type=Path, default=DEFAULT_RUNTIME_REPORT)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = audit(
            gameassembly=args.gameassembly, metadata=args.metadata,
            main_report=args.main_report, runtime_report=args.runtime_report,
            input_root=args.main_input_root,
            expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as exc:
        print(f"dynamic-main-path-join: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DynamicStreaming main path join passed: files={report['counts']['files']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
