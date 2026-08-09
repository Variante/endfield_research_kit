#!/usr/bin/env python3
"""Validate b30 GPU readbacks and same-frame pipeline activation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BEAUTY = {
    "d3d11": "1753e0bd900dfc068e2604632122136a4abf047af0ef5ba9607f17abc8a27ec7",
    "d3d12": "59902c424de630a496364d57e404a5a72bcbcc42712bf7ef6935900d7500cac3",
}
EXPECTED_SELECTED_VECTORS = [
    0, 1, 2, 3,
    4, 5, 6, 7,
    24, 25, 26, 27,
    44,
]
ACTIVE_TOKEN = (
    "Recovered selected deferred _TransformVariables b30 reads are active "
    "for the physical CharInfo camera; pass0=disabled."
)
FAIL_CLOSED_TOKEN = (
    "Recovered selected deferred _TransformVariables failed closed: "
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


def require(
    source: Path,
    check: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        raise AssertionError(
            "Deferred TransformVariables validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def validate_gpu_report(
    report: dict[str, object],
    api: str,
    source: Path,
) -> None:
    require(
        source,
        f"gpu_report.{api}.schema",
        report["schema"],
        "endfield-recovered-deferred-transform-variables-validation-v1",
    )
    require(source, f"gpu_report.{api}.valid", report["valid"], True)
    require(
        source,
        f"gpu_report.{api}.identity",
        (
            report["graphicsApi"],
            report["defaultOff"],
            report["pass0ConsumerEnabled"],
            report["bufferBytes"],
            report["vectorCount"],
            report["d3d11SelectedBytes"],
        ),
        (api, True, False, 1312, 82, 720),
    )
    require(
        source,
        f"gpu_report.{api}.selected_vectors",
        report["selectedUsedVectors"],
        EXPECTED_SELECTED_VECTORS,
    )
    require(
        source,
        f"gpu_report.{api}.publication",
        (
            report["publicationReturnedReady"],
            report["readyObserved"],
            report["allPublishedWordsMatch"],
            report["selectedConsumerWordsMatch"],
            report["unresolvedRegistersZero"],
            report["viewInverseRoundTrip"],
            report["worldClipRoundTrip"],
        ),
        (True, True, True, True, True, True, True),
    )
    require(
        source,
        f"gpu_report.{api}.word_count",
        (len(report["expectedWords"]), len(report["actualWords"])),
        (328, 328),
    )
    require(
        source,
        f"gpu_report.{api}.words",
        report["actualWords"],
        report["expectedWords"],
    )
    require(
        source,
        f"gpu_report.{api}.fail_closed_gates",
        [
            (
                row["gate"],
                row["rejected"],
                row["diagnosticMatched"],
            )
            for row in report["failClosedGates"]
        ],
        [
            ("destination_size", True, True),
            ("nonfinite_camera", True, True),
            ("singular_view", True, True),
        ],
    )
    require(source, f"gpu_report.{api}.failures", report["failures"], [])


def validate_frame_log(
    text: str,
    api: str,
    source: Path,
    expect_fail_closed: bool,
) -> None:
    api_token = {
        "d3d11": "Forcing GfxDevice: Direct3D 11",
        "d3d12": "Forcing GfxDevice: Direct3D 12",
    }[api]
    require(source, f"frame.{api}.graphics_api", api_token in text, True)
    require(
        source,
        f"frame.{api}.batch_exit",
        "Exiting batchmode successfully now!" in text,
        True,
    )
    require(
        source,
        f"frame.{api}.shader_compile_errors",
        "Shader error in" in text,
        False,
    )
    require(
        source,
        f"frame.{api}.script_compile_errors",
        "error CS" in text,
        False,
    )
    require(
        source,
        f"frame.{api}.canonical_prerequisites",
        PREREQUISITE_TOKEN in text,
        not expect_fail_closed,
    )
    require(
        source,
        f"frame.{api}.activation",
        ACTIVE_TOKEN in text,
        not expect_fail_closed,
    )
    require(
        source,
        f"frame.{api}.fail_closed",
        FAIL_CLOSED_TOKEN in text,
        expect_fail_closed,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()

    reports: dict[str, dict[str, object]] = {}
    evidence: dict[str, object] = {}
    for api in ("d3d11", "d3d12"):
        report_path = root / f"gpu_validation_{api}.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        validate_gpu_report(report, api, report_path)
        reports[api] = report

        log_path = root / f"unity_frame_{api}.log"
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        validate_frame_log(log_text, api, log_path, False)

        beauty_path = root / f"wulfa_beauty_{api}.png"
        require(
            beauty_path,
            f"frame.{api}.beauty",
            sha256(beauty_path),
            EXPECTED_BEAUTY[api],
        )
        evidence[api] = {
            "gpuReport": {
                "path": report_path.relative_to(LAB_ROOT).as_posix(),
                "sha256": sha256(report_path),
            },
            "frameLog": {
                "path": log_path.relative_to(LAB_ROOT).as_posix(),
                "sha256": sha256(log_path),
            },
            "beauty": {
                "path": beauty_path.relative_to(LAB_ROOT).as_posix(),
                "sha256": sha256(beauty_path),
            },
        }

    require(
        root,
        "cross_api_words",
        reports["d3d11"]["actualWords"],
        reports["d3d12"]["actualWords"],
    )

    fail_log = root / "unity_fail_closed_d3d12.log"
    validate_frame_log(
        fail_log.read_text(encoding="utf-8", errors="replace"),
        "d3d12",
        fail_log,
        True,
    )
    fail_beauty = root / "wulfa_beauty_fail_closed_d3d12.png"
    require(
        fail_beauty,
        "frame.d3d12.fail_closed_beauty",
        sha256(fail_beauty),
        EXPECTED_BEAUTY["d3d12"],
    )
    evidence["failClosedD3D12"] = {
        "frameLog": {
            "path": fail_log.relative_to(LAB_ROOT).as_posix(),
            "sha256": sha256(fail_log),
        },
        "beauty": {
            "path": fail_beauty.relative_to(LAB_ROOT).as_posix(),
            "sha256": sha256(fail_beauty),
        },
    }

    source_paths = {
        "contract": (
            LAB_ROOT
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
            "EndfieldRecoveredDeferredTransformVariablesContract.cs"
        ),
        "owner": (
            LAB_ROOT
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
            "EndfieldRecoveredDeferredTransformVariables.cs"
        ),
        "pipeline": (
            LAB_ROOT
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
            "HGCompatRenderPipeline.cs"
        ),
        "probe": (
            LAB_ROOT
            / "Assets/EndfieldGraphShaderLab/Resources/"
            "EndfieldRecoveredDeferredTransformVariablesProbe.compute"
        ),
        "batchVerifier": (
            LAB_ROOT
            / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
            "EndfieldRecoveredDeferredTransformVariablesBatchVerifier.cs"
        ),
        "sourceAuditor": LAB_ROOT / "tools/audit_deferred_transform_variables.py",
        "validator": Path(__file__).resolve(),
        "wrapper": LAB_ROOT / "verify_recovered_deferred_transform_variables.bat",
    }
    output = {
        "schema": "endfield-recovered-deferred-transform-frame-validation-v1",
        "valid": True,
        "defaultOff": True,
        "pass0ConsumerEnabled": False,
        "selectedUsedVectors": EXPECTED_SELECTED_VECTORS,
        "crossApiWordsBitExact": True,
        "unresolvedRegistersZero": True,
        "beautyUnchanged": True,
        "failClosedWithoutCanonicalPrerequisites": True,
        "evidence": evidence,
        "sources": {
            name: {
                "path": path.relative_to(LAB_ROOT).as_posix(),
                "sha256": sha256(path),
            }
            for name, path in source_paths.items()
        },
    }
    output_path = root / "frame_validation.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(
        "Deferred TransformVariables validation passed: 328 words bit-exact "
        "across D3D11/D3D12, same-frame activation gated, pass0 disabled."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
