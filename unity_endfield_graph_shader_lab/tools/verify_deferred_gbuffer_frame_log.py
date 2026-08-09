#!/usr/bin/env python3
"""Validate the same-camera SphereOutside five-MRT HGBuffer sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
EXPECTED_PNG_SHA256 = {
    "d3d11": "1753e0bd900dfc068e2604632122136a4abf047af0ef5ba9607f17abc8a27ec7",
    "d3d12": "59902c424de630a496364d57e404a5a72bcbcc42712bf7ef6935900d7500cac3",
}
EXPECTED_READBACKS = {
    "SceneColor": {
        "format": "B10G11R11_UFloatPack32",
        "nonzeroBytes": 0,
        "sha256": "8df6d450b5a7cb358b9e8373af9fd9304e5912389c644f6c4bc66068380e88a3",
    },
    "SceneMV": {
        "format": "A2B10G10R10_UNormPack32",
        "nonzeroBytes": 1_382_400,
        "sha256": "bd540907f59ca28745feaa98ab9685611b2f39af8965bfa06c2e39f4565c2bd0",
    },
    "GBufferA": {
        "format": "A2B10G10R10_UNormPack32",
        "nonzeroBytes": 1_382_400,
        "sha256": "3bdc871afc50d227293199b9126e69a2f7e9337ab4550cc6a39f8135651c9683",
    },
    "GBufferB": {
        "format": "A2B10G10R10_UNormPack32",
        "nonzeroBytes": 1_842_098,
        "sha256": "18e66cdee5523d33c9629a61436a3c2feee97fc2321efc67f922265505094125",
    },
    "GBufferC": {
        "format": "R8G8B8A8_SRGB",
        "nonzeroBytes": 1_382_400,
        "sha256": "b6ffa8536d9c20724bbd90c514cde0a80e0cb3e95911bd5a3293b8d320bbfa56",
    },
}

ACTIVE_RE = re.compile(
    r"Recovered SphereOutside same-frame HGBuffer sidecar active: "
    r"camera=(?P<camera>[^,]+), size=(?P<width>\d+)x(?P<height>\d+), "
    r"attachments=(?P<attachments>[^,]+), "
    r"sourceRendererDisabled=(?P<disabled>True|False), "
    r"pass0ConsumerEnabled=(?P<pass0>true|false)\."
)
READBACK_RE = re.compile(
    r"Recovered deferred HGBuffer GPU readback: role=(?P<role>\w+), "
    r"camera=(?P<camera>[^,]+), size=(?P<width>\d+)x(?P<height>\d+), "
    r"format=(?P<format>\w+), bytes=(?P<bytes>\d+), "
    r"nonzeroBytes=(?P<nonzero>\d+), sha256=(?P<sha>[0-9a-f]{64})\."
)
FAIL_CLOSED_TOKEN = (
    "Recovered SphereOutside same-frame HGBuffer sidecar failed closed: "
    "canonical binning/reflection/VisibilitySHConstData prerequisites are not ready."
)
PREREQUISITE_TOKEN = (
    "Recovered canonical CharInfo binning + reflection oct/global + exact "
    "VisibilitySHConstData frame resources are active"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_log(
    text: str,
    api: str,
    source: Path,
    expect_fail_closed: bool = False,
) -> dict[str, object]:
    failures: list[str] = []

    def require(check: str, actual: object, expected: object) -> None:
        if actual != expected:
            failures.append(
                "Deferred HGBuffer frame validator failed: "
                f"check={check}; source={source}; "
                f"expected={expected!r}; actual={actual!r}"
            )

    api_token = {
        "d3d11": "Forcing GfxDevice: Direct3D 11",
        "d3d12": "Forcing GfxDevice: Direct3D 12",
    }[api]
    require("graphics_api", api_token in text, True)
    require("batch_exit", "Exiting batchmode successfully now!" in text, True)
    require("shader_compile_errors", "Shader error in" in text, False)
    require("script_compile_errors", "error CS" in text, False)
    require(
        "canonical_prerequisites",
        PREREQUISITE_TOKEN in text,
        not expect_fail_closed,
    )

    active_match = ACTIVE_RE.search(text)
    readback_matches = list(READBACK_RE.finditer(text))
    fail_closed_present = FAIL_CLOSED_TOKEN in text
    require("fail_closed_record", fail_closed_present, expect_fail_closed)
    require("active_record", active_match is not None, not expect_fail_closed)
    require("readback_count", len(readback_matches), 0 if expect_fail_closed else 5)

    active: dict[str, object] = {}
    readbacks: dict[str, dict[str, object]] = {}
    if active_match:
        active = {
            "camera": active_match["camera"],
            "width": int(active_match["width"]),
            "height": int(active_match["height"]),
            "attachments": active_match["attachments"],
            "sourceRendererDisabled": active_match["disabled"] == "True",
            "pass0ConsumerEnabled": active_match["pass0"] == "true",
        }
        require("active_camera", active["camera"], "MainCamera")
        require("active_extent", (active["width"], active["height"]), (640, 720))
        require(
            "active_attachments",
            active["attachments"],
            (
                "B10G11R11/A2B10G10R10/A2B10G10R10/"
                "A2B10G10R10/R8G8B8A8_SRGB+D32S8"
            ),
        )
        require("source_renderer_disabled", active["sourceRendererDisabled"], True)
        require("pass0_consumer_disabled", active["pass0ConsumerEnabled"], False)

    for match in readback_matches:
        role = match["role"]
        record = {
            "camera": match["camera"],
            "width": int(match["width"]),
            "height": int(match["height"]),
            "format": match["format"],
            "byteCount": int(match["bytes"]),
            "nonzeroBytes": int(match["nonzero"]),
            "sha256": match["sha"],
        }
        if role in readbacks:
            failures.append(
                "Deferred HGBuffer frame validator failed: "
                f"check=duplicate_readback_role; source={source}; role={role}"
            )
            continue
        readbacks[role] = record

    if not expect_fail_closed:
        require("readback_roles", set(readbacks), set(EXPECTED_READBACKS))
        for role, expected in EXPECTED_READBACKS.items():
            if role not in readbacks:
                continue
            actual = readbacks[role]
            require(f"{role}.camera", actual["camera"], "MainCamera")
            require(f"{role}.extent", (actual["width"], actual["height"]), (640, 720))
            require(f"{role}.byte_count", actual["byteCount"], 640 * 720 * 4)
            require(f"{role}.format", actual["format"], expected["format"])
            require(
                f"{role}.nonzero_bytes",
                actual["nonzeroBytes"],
                expected["nonzeroBytes"],
            )
            require(f"{role}.sha256", actual["sha256"], expected["sha256"])

    return {
        "schema": "endfield-recovered-deferred-gbuffer-frame-validation-v1",
        "valid": not failures,
        "graphicsApi": api,
        "defaultOff": True,
        "expectedFailClosed": expect_fail_closed,
        "canonicalPublication": False,
        "pass0ConsumerEnabled": False,
        "activeFrame": active,
        "gpuReadbacks": readbacks,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True, choices=("d3d11", "d3d12"))
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--beauty", required=True, type=Path)
    parser.add_argument("--expect-fail-closed", action="store_true")
    args = parser.parse_args()

    text = args.log.read_text(encoding="utf-8", errors="replace")
    report = validate_log(
        text,
        args.api,
        args.log,
        args.expect_fail_closed,
    )
    report["sources"] = {
        "log": {"path": str(args.log), "sha256": sha256(args.log)},
        "producer": {
            "path": "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredDeferredGBufferFrame.cs",
            "sha256": sha256(
                LAB_ROOT
                / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredDeferredGBufferFrame.cs"
            ),
        },
        "shader": {
            "path": "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldCharInfoHGRPLitUnavailable.shader",
            "sha256": sha256(
                LAB_ROOT
                / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldCharInfoHGRPLitUnavailable.shader"
            ),
        },
        "pipeline": {
            "path": "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs",
            "sha256": sha256(
                LAB_ROOT
                / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
            ),
        },
        "materialSource": {
            "path": "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/Materials/M_CharInfo_outside.raw.json",
            "sha256": sha256(
                LAB_ROOT
                / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/Materials/M_CharInfo_outside.raw.json"
            ),
        },
    }
    expected_png = EXPECTED_PNG_SHA256[args.api]
    actual_png = sha256(args.beauty) if args.beauty.is_file() else ""
    report["beautyFrame"] = {
        "path": str(args.beauty),
        "sha256": actual_png,
        "expectedSha256": expected_png,
        "unchanged": actual_png == expected_png,
    }
    if actual_png != expected_png:
        report["failures"].append(
            "Deferred HGBuffer frame validator failed: "
            f"check=beauty_frame; source={args.beauty}; "
            f"expected={expected_png!r}; actual={actual_png!r}"
        )
        report["valid"] = False

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["valid"]:
        for failure in report["failures"]:
            print(failure)
        return 1
    if args.expect_fail_closed:
        print(
            "Deferred HGBuffer frame fail-closed validation passed: "
            f"api={args.api}, readbacks=0, pass0ConsumerEnabled=false."
        )
    else:
        print(
            "Deferred HGBuffer frame validation passed: "
            f"api={args.api}, readbacks=5, extent=640x720, "
            "pass0ConsumerEnabled=false."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
