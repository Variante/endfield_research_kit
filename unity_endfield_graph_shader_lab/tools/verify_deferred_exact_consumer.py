#!/usr/bin/env python3
"""Validate the opt-in exact deferred-resolver DXBC frame consumer log."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SUBMITTED_RE = re.compile(
    r"Recovered exact deferred resolver consumer submitted:\s*"
    r"camera=(?P<camera>[^,]+),\s*"
    r"size=(?P<width>\d+)x(?P<height>\d+),\s*"
    r"publicationSerial=(?P<serial>\d+),\s*"
    r"exactBound=(?P<bound>\d+),\s*"
    r"resourceMask=0x(?P<mask>[0-9a-f]+),\s*"
    r"resourceFailureMask=0x(?P<resource_failures>[0-9a-f]+),\s*"
    r"resourceFailureResults=(?P<resource_results>[^,]+),\s*"
    r"constantBufferMask=0x(?P<cb_mask>[0-9a-f]+),\s*"
    r"failureCount=(?P<failures>\d+),\s*"
    r"presented=(?P<presented>true|false),\s*"
    r"retailPass0=(?P<pass0>true|false),\s*"
    r"screenContentValid=(?P<screen>false|true)\.",
    re.IGNORECASE,
)
READBACK_RE = re.compile(
    r"Recovered exact deferred resolver consumer readback:\s*"
    r"camera=(?P<camera>[^,]+),\s*"
    r"size=(?P<width>\d+)x(?P<height>\d+),\s*"
    r"bytes=(?P<bytes>\d+),\s*"
    r"nonzeroBytes=(?P<nonzero>\d+),\s*"
    r"exactBound=(?P<bound>\d+),\s*"
    r"resourceMask=0x(?P<mask>[0-9a-f]+),\s*"
    r"resourceFailureMask=0x(?P<resource_failures>[0-9a-f]+),\s*"
    r"resourceFailureResults=(?P<resource_results>[^,]+),\s*"
    r"constantBufferMask=0x(?P<cb_mask>[0-9a-f]+),\s*"
    r"rgbaFloatSha256=(?P<sha>[0-9a-f]{64}),\s*"
    r"finiteFloats=(?P<finite>\d+),\s*"
    r"nonFiniteFloats=(?P<nonfinite>\d+),\s*"
    r"min=(?P<minimum>[^,]+),\s*"
    r"max=(?P<maximum>[^,]+),\s*"
    r"failureCount=(?P<failures>\d+),\s*"
    r"presented=(?P<presented>true|false),\s*"
    r"retailPass0=(?P<pass0>true|false)\.",
    re.IGNORECASE,
)
HLSL_COMPARISON_RE = re.compile(
    r"Recovered deferred pass-0 HLSL vs exact DXBC comparison:\s*"
    r"camera=(?P<camera>[^,]+),\s*size=(?P<width>\d+)x(?P<height>\d+),\s*"
    r"floatCount=(?P<count>\d+),\s*maxAbs=(?P<max_abs>[^,]+),\s*"
    r"rmse=(?P<rmse>[^,]+),\s*over1e-6=(?P<over_1e6>\d+),\s*"
    r"over1e-4=(?P<over_1e4>\d+),\s*over1e-3=(?P<over_1e3>\d+),\s*"
    r"presented=(?P<presented>true|false)\.",
    re.IGNORECASE,
)
EXPECTED_RESOURCE_MASK = (1 << 26) - 1


def validate_log(text: str, source: Path) -> dict[str, object]:
    failures: list[str] = []

    def require(check: str, actual: object, expected: object) -> None:
        if actual != expected:
            failures.append(
                "Deferred exact-consumer validator failed: "
                f"check={check}; source={source}; "
                f"expected={expected!r}; actual={actual!r}"
            )

    require("batch_exit", "Exiting batchmode successfully now!" in text, True)
    require("script_compile_errors", "error CS" in text, False)
    require("shader_compile_errors", "Shader error in" in text, False)
    submitted_matches = list(SUBMITTED_RE.finditer(text))
    readback_matches = list(READBACK_RE.finditer(text))
    comparison_matches = list(HLSL_COMPARISON_RE.finditer(text))
    require("submitted_record_count", len(submitted_matches) > 0, True)
    require("readback_record_count", len(readback_matches) > 0, True)
    require("hlsl_comparison_record_count", len(comparison_matches) > 0, True)

    submitted: dict[str, object] = {}
    submitted_main_matches = [
        match for match in submitted_matches
        if int(match["width"]) == 640 and int(match["height"]) == 720
    ]
    if submitted_main_matches:
        match = submitted_main_matches[-1]
        submitted = {
            "camera": match["camera"],
            "width": int(match["width"]),
            "height": int(match["height"]),
            "publicationSerial": int(match["serial"]),
            "exactBound": int(match["bound"]),
            "resourceMask": int(match["mask"], 16),
            "resourceFailureMask": int(match["resource_failures"], 16),
            "resourceFailureResults": match["resource_results"],
            "constantBufferMask": int(match["cb_mask"], 16),
            "failureCount": int(match["failures"]),
            "presented": match["presented"].lower() == "true",
            "retailPass0": match["pass0"].lower() == "true",
            "screenContentValid": match["screen"].lower() == "true",
        }
        require("camera", submitted["camera"], "MainCamera")
        require("extent", (submitted["width"], submitted["height"]), (640, 720))
        require("publication_serial", submitted["publicationSerial"] > 0, True)
        # The submission log is emitted immediately after ExecuteCommandBuffer;
        # exactBound/masks are authoritative only in the later GPU readback
        # callback, after the native render event has run.
        require("native_submit_failures", submitted["failureCount"], 0)
        require("presented", submitted["presented"], False)
        require("retail_pass0", submitted["retailPass0"], False)
        require("screen_content_valid", submitted["screenContentValid"], False)

    readback: dict[str, object] = {}
    readback_main_matches = [
        match for match in readback_matches
        if int(match["width"]) == 640 and int(match["height"]) == 720
    ]
    require("main_camera_readback_count", len(readback_main_matches) > 0, True)
    if readback_main_matches:
        match = readback_main_matches[-1]
        readback = {
            "camera": match["camera"],
            "width": int(match["width"]),
            "height": int(match["height"]),
            "bytes": int(match["bytes"]),
            "nonzeroBytes": int(match["nonzero"]),
            "exactBound": int(match["bound"]),
            "resourceMask": int(match["mask"], 16),
            "resourceFailureMask": int(match["resource_failures"], 16),
            "resourceFailureResults": match["resource_results"],
            "constantBufferMask": int(match["cb_mask"], 16),
            "rgbaFloatSha256": match["sha"],
            "finiteFloats": int(match["finite"]),
            "nonFiniteFloats": int(match["nonfinite"]),
            "min": match["minimum"],
            "max": match["maximum"],
            "failureCount": int(match["failures"]),
            "presented": match["presented"].lower() == "true",
            "retailPass0": match["pass0"].lower() == "true",
        }
        require("readback_camera", readback["camera"], "MainCamera")
        require("readback_extent", (readback["width"], readback["height"]), (640, 720))
        require("readback_bytes", readback["bytes"], 640 * 720 * 16)
        require("readback_nonzero", readback["nonzeroBytes"] > 0, True)
        require("readback_exact_shader_bound", readback["exactBound"], 1)
        require(
            "readback_resource_mask_all_t0_t25",
            readback["resourceMask"],
            EXPECTED_RESOURCE_MASK,
        )
        require("readback_resource_failure_mask", readback["resourceFailureMask"], 0)
        require("readback_resource_failure_results", readback["resourceFailureResults"], "none")
        require("readback_constant_buffer_mask_all_b0_b8", readback["constantBufferMask"], 0x1FF)
        require("readback_finite_float_count", readback["finiteFloats"], 640 * 720 * 4)
        require("readback_nonfinite_float_count", readback["nonFiniteFloats"], 0)
        require("readback_native_failures", readback["failureCount"], 0)
        require("readback_presented", readback["presented"], False)
        require("readback_retail_pass0", readback["retailPass0"], False)

    comparison: dict[str, object] = {}
    comparison_main_matches = [
        match for match in comparison_matches
        if int(match["width"]) == 640 and int(match["height"]) == 720
    ]
    require("main_camera_hlsl_comparison_count", len(comparison_main_matches) > 0, True)
    if comparison_main_matches:
        match = comparison_main_matches[-1]
        comparison = {
            "camera": match["camera"],
            "width": int(match["width"]),
            "height": int(match["height"]),
            "floatCount": int(match["count"]),
            "maxAbs": float(match["max_abs"]),
            "rmse": float(match["rmse"]),
            "over1e-6": int(match["over_1e6"]),
            "over1e-4": int(match["over_1e4"]),
            "over1e-3": int(match["over_1e3"]),
            "presented": match["presented"].lower() == "true",
        }
        require("hlsl_comparison_camera", comparison["camera"], "MainCamera")
        require("hlsl_comparison_float_count", comparison["floatCount"], 640 * 720 * 4)
        require("hlsl_comparison_max_abs_within_one_ulp", comparison["maxAbs"] <= 1.1920929e-7, True)
        require("hlsl_comparison_over_1e6", comparison["over1e-6"], 0)
        require("hlsl_comparison_presented", comparison["presented"], False)

    return {
        "schema": "endfield-recovered-deferred-exact-consumer-validation-v1",
        "valid": not failures,
        "defaultOff": True,
        "submitted": submitted,
        "readback": readback,
        "hlslComparison": comparison,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    report = validate_log(text, args.log)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if report["valid"]:
        print("VALID: exact deferred resolver consumer")
        return 0
    for failure in report["failures"]:
        print(failure)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
