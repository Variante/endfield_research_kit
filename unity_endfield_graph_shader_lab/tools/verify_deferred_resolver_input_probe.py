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
RESOURCE_RE = re.compile(
    r"Recovered deferred resolver target-resource snapshot:\s*"
    r"t0=(?P<t0>ready|absent),"
    r"t1=(?P<t1>ready|absent),"
    r"t5=(?P<t5>ready|absent),"
    r"t6=(?P<t6>ready|absent),"
    r"t7=(?P<t7>ready|absent),"
    r"t22=(?P<t22>allocated|absent),\s*"
    r"t1=(?P<t1shape>[^,]+),"
    r"t5=(?P<t5shape>[^,]+),"
    r"t6=(?P<t6shape>[^,]+),"
    r"t7=(?P<t7shape>[^,]+),"
    r"t22=(?P<t22shape>[^,]+),\s*"
    r"allPhysical=(?P<allphysical>true|false),\s*"
    r"screenContentValid=false\.",
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
    expect_resource_probe: bool = False,
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
    require(
        "g_buffer_aliases",
        G_BUFFER_TOKEN in text,
        not expect_fail_closed or expect_resource_probe,
    )
    require(
        "shadow_data_b34",
        SHADOW_DATA_TOKEN in text,
        not expect_fail_closed or expect_resource_probe,
    )

    active_matches = list(ACTIVE_RE.finditer(text))
    readback_matches = list(READBACK_RE.finditer(text))
    resource_matches = list(RESOURCE_RE.finditer(text))
    failed_closed = FAILURE_PREFIX in text
    require("fail_closed_record", failed_closed, expect_fail_closed)
    require("active_record_count", len(active_matches), 0 if expect_fail_closed else 1)
    require("readback_record_count", len(readback_matches), 0 if expect_fail_closed else 1)
    require(
        "resource_snapshot_count",
        len(resource_matches),
        0 if expect_fail_closed else 1,
    )

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

    resources: dict[str, object] = {}
    if resource_matches:
        match = resource_matches[-1]
        resources = {
            "t0": match["t0"],
            "t1": match["t1"],
            "t5": match["t5"],
            "t6": match["t6"],
            "t7": match["t7"],
            "t22": match["t22"],
            "shapes": {
                "t1": match["t1shape"],
                "t5": match["t5shape"],
                "t6": match["t6shape"],
                "t7": match["t7shape"],
                "t22": match["t22shape"],
            },
            "allPhysical": match["allphysical"].lower() == "true",
            "screenContentValid": False,
        }
        expected_resources = (
            {"t0": "ready", "t1": "ready", "t5": "ready", "t6": "ready", "t7": "ready", "t22": "allocated", "allPhysical": True}
            if expect_resource_probe
            else {"t0": "ready", "t1": "ready", "t5": "ready", "t6": "ready", "t7": "absent", "t22": "absent", "allPhysical": False}
        )
        for key, expected in expected_resources.items():
            require(f"resource_{key}", resources[key], expected)
        for key in ("t1", "t5", "t6", "t7", "t22"):
            require(f"resource_shape_{key}_present", resources["shapes"][key] != "none", expect_resource_probe or key in ("t1", "t5", "t6"))

    return {
        "schema": "endfield-recovered-deferred-resolver-input-validation-v2",
        "valid": not failures,
        "defaultOff": True,
        "expectedFailClosed": expect_fail_closed,
        "sameFramePublication": not expect_fail_closed,
        "active": active,
        "readback": readback,
        "resources": resources,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--expect-fail-closed", action="store_true")
    parser.add_argument("--expect-resource-probe", action="store_true")
    args = parser.parse_args()

    text = args.log.read_text(encoding="utf-8", errors="replace")
    report = validate_log(
        text,
        args.log,
        expect_fail_closed=args.expect_fail_closed,
        expect_resource_probe=args.expect_resource_probe,
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
