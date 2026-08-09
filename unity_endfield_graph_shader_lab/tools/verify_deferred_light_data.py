#!/usr/bin/env python3
"""Validate b31 GPU readbacks and same-frame pipeline activation."""

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
ACTIVE_TOKEN = (
    "Recovered selected deferred _LightDataBuffer b31 reads are active for "
    "the source-closed Wulfa/Zhuangfy CharInfo fixture; pass0=disabled."
)
FAIL_CLOSED_TOKEN = (
    "Recovered selected deferred _LightDataBuffer failed closed: canonical "
    "binning/reflection/VisibilitySHConstData prerequisites are not ready."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(source: Path, check: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(
            "Deferred LightData validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def validate_gpu(report: dict[str, object], api: str, source: Path) -> None:
    require(
        source,
        f"gpu.{api}.schema",
        report["schema"],
        "endfield-recovered-deferred-light-data-validation-v1",
    )
    require(source, f"gpu.{api}.valid", report["valid"], True)
    require(
        source,
        f"gpu.{api}.identity",
        (
            report["graphicsApi"],
            report["defaultOff"],
            report["pass0ConsumerEnabled"],
            report["bufferBytes"],
            report["vectorCount"],
            report["headerVectors"],
            report["maxPunctualLights"],
            report["vectorsPerPunctualLight"],
        ),
        (api, True, False, 32864, 2054, 6, 256, 8),
    )
    require(
        source,
        f"gpu.{api}.transport",
        (
            report["sourceAuditHashMatches"],
            report["namedReadyObserved"],
            report["bridgeReadyObserved"],
            report["namedWordsExact"],
            report["bridgeWordsExact"],
            report["namedBridgeWordsExact"],
            report["unresolvedWordsZero"],
            report["expectedNonzeroWords"],
            report["actualNonzeroWords"],
        ),
        (True, True, True, True, True, True, True, 17, 17),
    )
    require(
        source,
        f"gpu.{api}.fail_closed_gates",
        [
            (row["gate"], row["rejected"], row["diagnosticMatched"])
            for row in report["failClosedGates"]
        ],
        [
            ("destination_size", True, True),
            ("punctual_count", True, True),
            ("directional_source", True, True),
            ("nonfinite_color", True, True),
        ],
    )
    require(source, f"gpu.{api}.failures", report["failures"], [])


def validate_frame(source: Path, api: str, fail_closed: bool) -> None:
    text = source.read_text(encoding="utf-8", errors="replace")
    require(
        source,
        f"frame.{api}.graphics_api",
        f"Forcing GfxDevice: Direct3D {api[-2:]}" in text,
        True,
    )
    require(
        source,
        f"frame.{api}.batch_exit",
        "Exiting batchmode successfully now!" in text,
        True,
    )
    require(source, f"frame.{api}.script_errors", "error CS" in text, False)
    require(source, f"frame.{api}.shader_errors", "Shader error in" in text, False)
    require(source, f"frame.{api}.activation", ACTIVE_TOKEN in text, not fail_closed)
    require(source, f"frame.{api}.fail_closed", FAIL_CLOSED_TOKEN in text, fail_closed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()

    evidence: dict[str, object] = {}
    reports: dict[str, dict[str, object]] = {}
    for api in ("d3d11", "d3d12"):
        report_path = root / f"gpu_validation_{api}.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        validate_gpu(report, api, report_path)
        reports[api] = report

        frame_log = root / f"unity_frame_{api}.log"
        validate_frame(frame_log, api, False)
        beauty = root / f"wulfa_beauty_{api}.png"
        require(beauty, f"frame.{api}.beauty", sha256(beauty), EXPECTED_BEAUTY[api])
        evidence[api] = {
            "gpuReport": sha256(report_path),
            "frameLog": sha256(frame_log),
            "beauty": sha256(beauty),
        }

    require(
        root,
        "cross_api_nonzero_words",
        reports["d3d11"]["actualNonzeroWords"],
        reports["d3d12"]["actualNonzeroWords"],
    )
    fail_log = root / "unity_fail_closed_d3d12.log"
    validate_frame(fail_log, "d3d12", True)
    fail_beauty = root / "wulfa_beauty_fail_closed_d3d12.png"
    require(
        fail_beauty,
        "frame.d3d12.fail_closed_beauty",
        sha256(fail_beauty),
        EXPECTED_BEAUTY["d3d12"],
    )
    evidence["failClosedD3D12"] = {
        "frameLog": sha256(fail_log),
        "beauty": sha256(fail_beauty),
    }

    sources = {
        "contract": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredDeferredLightDataContract.cs",
        "owner": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredDeferredLightData.cs",
        "pipeline": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs",
        "probe": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Resources/EndfieldRecoveredDeferredLightDataProbe.compute",
        "batchVerifier": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldRecoveredDeferredLightDataBatchVerifier.cs",
        "sourceAuditor": LAB_ROOT / "tools/audit_deferred_light_data.py",
        "validator": Path(__file__).resolve(),
        "wrapper": LAB_ROOT / "verify_recovered_deferred_light_data.bat",
    }
    output = {
        "schema": "endfield-recovered-deferred-light-data-frame-validation-v1",
        "valid": True,
        "defaultOff": True,
        "pass0ConsumerEnabled": False,
        "layout": "6 header + 256 * 8 punctual float4",
        "namedAndD3D11BridgeBitExact": True,
        "unresolvedWordsZero": True,
        "sameFrameActivation": True,
        "beautyUnchanged": True,
        "failClosedWithoutCanonicalPrerequisites": True,
        "generalScenePunctualPayloadRecovered": False,
        "evidence": evidence,
        "sources": {
            name: {
                "path": path.relative_to(LAB_ROOT).as_posix(),
                "sha256": sha256(path),
            }
            for name, path in sources.items()
        },
    }
    output_path = root / "frame_validation.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(
        "Deferred LightData validation passed: 8216 words exact on "
        "D3D11/D3D12 named+CB4 paths, same-frame activation gated, pass0 disabled."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
