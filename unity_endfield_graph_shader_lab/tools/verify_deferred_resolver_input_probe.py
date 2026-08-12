#!/usr/bin/env python3
"""Validate the default-off same-frame deferred resolver input probe log."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ACTIVE_RE = re.compile(
    r"Recovered deferred resolver input consumer probe active:\s*"
    r"camera=(?P<camera>[^,]+),\s*"
    r"size=(?P<width>\d+)x(?P<height>\d+),\s*"
    r"publicationSerial=(?P<serial>\d+),\s*"
    r"sourceIdentifiers=(?P<source_ids>t23:_62,t24:_61,t25:_60),\s*"
    r"registerBridges=(?P<bridges>b0\.\.b8),\s*"
    r"b6=(?P<b6>[^,]+),\s*"
    r"presented=(?P<presented>true|false),\s*"
    r"retailPass0=(?P<pass0>true|false)\.",
    re.IGNORECASE,
)
READBACK_RE = re.compile(
    r"Recovered deferred resolver input probe readback:\s*"
    r"camera=(?P<camera>[^,]+),\s*"
    r"size=(?P<width>\d+)x(?P<height>\d+),\s*"
    r"bytes=(?P<bytes>\d+),\s*"
    r"nonzeroBytes=(?P<nonzero>\d+)\.",
    re.IGNORECASE,
)
G_BUFFER_TOKEN = (
    "resolverGBufferBindings=t23:C,t24:B,t25:A, "
    "resolverSourceIdentifiers=t23:_62,t24:_61,t25:_60"
)
SHADOW_DATA_TOKEN = (
    "Recovered selected deferred ShadowData b34 punctual section and "
    "matching D16 atlas are active"
)
FAILURE_PREFIX = "Recovered deferred resolver input probe failed closed:"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_log(
    text: str,
    source: Path,
    *,
    expect_fail_closed: bool = False,
) -> dict[str, object]:
    failures: list[str] = []

    def require(check: str, actual: object, expected: object) -> None:
        if actual != expected:
            failures.append(
                "Deferred resolver input validator failed: "
                f"check={check}; source={source}; "
                f"expected={expected!r}; actual={actual!r}"
            )

    require("batch_exit", "Exiting batchmode successfully now!" in text, True)
    require("script_compile_errors", "error CS" in text, False)
    require("shader_compile_errors", "Shader error in" in text, False)
    require("g_buffer_aliases", G_BUFFER_TOKEN in text, not expect_fail_closed)
    require("shadow_data_b34", SHADOW_DATA_TOKEN in text, not expect_fail_closed)

    active_matches = list(ACTIVE_RE.finditer(text))
    readback_matches = list(READBACK_RE.finditer(text))
    failed_closed = FAILURE_PREFIX in text
    require("fail_closed_record", failed_closed, expect_fail_closed)
    require("active_record_count", len(active_matches), 0 if expect_fail_closed else 1)
    require("readback_record_count", len(readback_matches), 0 if expect_fail_closed else 1)

    active: dict[str, object] = {}
    if active_matches:
        match = active_matches[-1]
        active = {
            "camera": match["camera"],
            "width": int(match["width"]),
            "height": int(match["height"]),
            "publicationSerial": int(match["serial"]),
            "sourceIdentifiers": match["source_ids"],
            "registerBridges": match["bridges"],
            "b6": match["b6"],
            "presented": match["presented"].lower() == "true",
            "retailPass0": match["pass0"].lower() == "true",
        }
        require("camera", active["camera"], "MainCamera")
        require("extent", (active["width"], active["height"]), (640, 720))
        require("publication_serial", active["publicationSerial"] > 0, True)
        require("source_identifiers", active["sourceIdentifiers"], "t23:_62,t24:_61,t25:_60")
        require("register_bridges", active["registerBridges"], "b0..b8")
        require("b6_fallback", active["b6"], "zero-fallback")
        require("presented", active["presented"], False)
        require("retail_pass0", active["retailPass0"], False)

    readback: dict[str, object] = {}
    if readback_matches:
        match = readback_matches[-1]
        readback = {
            "camera": match["camera"],
            "width": int(match["width"]),
            "height": int(match["height"]),
            "bytes": int(match["bytes"]),
            "nonzeroBytes": int(match["nonzero"]),
        }
        require("readback_camera", readback["camera"], "MainCamera")
        require("readback_extent", (readback["width"], readback["height"]), (640, 720))
        require("readback_bytes", readback["bytes"], 640 * 720 * 16)
        require("readback_nonzero", readback["nonzeroBytes"] > 0, True)

    return {
        "schema": "endfield-recovered-deferred-resolver-input-validation-v1",
        "valid": not failures,
        "defaultOff": True,
        "expectedFailClosed": expect_fail_closed,
        "sameFramePublication": not expect_fail_closed,
        "active": active,
        "readback": readback,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--expect-fail-closed", action="store_true")
    args = parser.parse_args()

    text = args.log.read_text(encoding="utf-8", errors="replace")
    report = validate_log(
        text,
        args.log,
        expect_fail_closed=args.expect_fail_closed,
    )
    report["sources"] = {
        "log": {"path": str(args.log), "sha256": sha256(args.log)},
        "producer": {
            "path": "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredDeferredGBufferFrame.cs",
        },
        "probe": {
            "path": "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredDeferredResolverInputProbe.cs",
        },
        "pipeline": {
            "path": "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs",
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if report["valid"]:
        print("VALID: same-frame deferred resolver input probe")
        return 0
    for failure in report["failures"]:
        print(failure)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
