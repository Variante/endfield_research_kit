#!/usr/bin/env python3
"""Validate b34 GPU transport and same-frame isolated-shadow publication."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BEAUTY = {
    "d3d11": "5af932a9d9a6a21e846aea6daa027f5412450357445e06f12c10baf7b0ed0402",
    "d3d12": "3c223fb0311ff677a80079c72adfacea724e4d568be596b72824a78acac65527",
}
EXPECTED_ZHUANGFY_BEAUTY_D3D12 = (
    "c9fceb48173ea16d032d64f18a2ceec3c9c0e0352674c28bb06713c4ce6d0796"
)
PRODUCER_TOKEN = (
    "Recovered isolated punctual soft-shadow producer active: wulfa: row 4, "
    "packed light 5, slots 40..40, B=1024, atlas=6144x4096, D16, casters=12."
)
ZHUANGFY_PRODUCER_TOKEN = (
    "Recovered isolated punctual soft-shadow producer active: zhuangfy: row 4, "
    "packed light 0, slots 40..45, B=1024, atlas=6144x4096, D16, casters=6."
)
LIGHT_DATA_TOKEN = (
    "Recovered selected deferred _LightDataBuffer b31 reads are active for "
    "the source-closed Wulfa/Zhuangfy CharInfo fixture; pass0=disabled."
)
ACTIVE_TOKEN = (
    "Recovered selected deferred ShadowData b34 punctual section and matching "
    "D16 atlas are active for the isolated Wulfa/Zhuangfy fixture; pass0=disabled."
)
FAIL_CLOSED_TOKEN = (
    "Recovered selected deferred ShadowData failed closed: isolated "
    "punctual-shadow producer prerequisite is not ready."
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
            "Deferred ShadowData validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def validate_gpu(report: dict[str, object], api: str, source: Path) -> None:
    require(
        source,
        f"gpu.{api}.schema",
        report["schema"],
        "endfield-recovered-deferred-shadow-data-validation-v1",
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
            report["d3d11SelectedBytes"],
            report["d3d11SelectedVectors"],
        ),
        (api, True, False, 11440, 715, 6416, 401),
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
            report["namedBridgePrefixExact"],
            report["unownedSectionsZero"],
            report["expectedNonzeroWords"],
            report["namedNonzeroWords"],
        ),
        (True, True, True, True, True, True, True, 23, 23),
    )
    require(
        source,
        f"gpu.{api}.word_hash",
        report["namedWordsSha256"],
        report["expectedWordsSha256"],
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
            ("array_size", True, True),
            ("tile_resolution", True, True),
            ("face_count", True, True),
            ("inactive_slot", True, True),
            ("active_rect", True, True),
        ],
    )
    require(source, f"gpu.{api}.failures", report["failures"], [])


def validate_log(
    source: Path,
    api: str,
    mode: str,
) -> None:
    text = source.read_text(encoding="utf-8", errors="replace")
    require(
        source,
        f"{mode}.{api}.graphics_api",
        f"Forcing GfxDevice: Direct3D {api[-2:]}" in text,
        True,
    )
    require(
        source,
        f"{mode}.{api}.batch_exit",
        "Exiting batchmode successfully now!" in text,
        True,
    )
    require(source, f"{mode}.{api}.script_errors", "error CS" in text, False)
    require(source, f"{mode}.{api}.shader_errors", "Shader error in" in text, False)
    if mode == "active":
        require(source, f"{mode}.{api}.producer", PRODUCER_TOKEN in text, True)
        require(source, f"{mode}.{api}.b31", LIGHT_DATA_TOKEN in text, True)
        require(source, f"{mode}.{api}.b34", ACTIVE_TOKEN in text, True)
        require(source, f"{mode}.{api}.fail_closed", FAIL_CLOSED_TOKEN in text, False)
    elif mode == "control":
        require(source, f"{mode}.{api}.producer", PRODUCER_TOKEN in text, True)
        require(source, f"{mode}.{api}.b34", ACTIVE_TOKEN in text, False)
        require(source, f"{mode}.{api}.fail_closed", FAIL_CLOSED_TOKEN in text, False)
    else:
        require(source, f"{mode}.{api}.b31", LIGHT_DATA_TOKEN in text, True)
        require(source, f"{mode}.{api}.b34", ACTIVE_TOKEN in text, False)
        require(source, f"{mode}.{api}.fail_closed", FAIL_CLOSED_TOKEN in text, True)


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

        active_log = root / f"unity_frame_{api}.log"
        control_log = root / f"unity_control_{api}.log"
        validate_log(active_log, api, "active")
        validate_log(control_log, api, "control")
        active_beauty = root / f"wulfa_beauty_{api}.png"
        control_beauty = root / f"wulfa_beauty_control_{api}.png"
        require(
            active_beauty,
            f"active.{api}.beauty",
            sha256(active_beauty),
            EXPECTED_BEAUTY[api],
        )
        require(
            control_beauty,
            f"control.{api}.beauty",
            sha256(control_beauty),
            EXPECTED_BEAUTY[api],
        )
        evidence[api] = {
            "gpuReport": sha256(report_path),
            "activeLog": sha256(active_log),
            "controlLog": sha256(control_log),
            "activeBeauty": sha256(active_beauty),
            "controlBeauty": sha256(control_beauty),
        }

    require(
        root,
        "cross_api_named_words",
        reports["d3d11"]["namedWordsSha256"],
        reports["d3d12"]["namedWordsSha256"],
    )
    require(
        root,
        "cross_api_bridge_words",
        reports["d3d11"]["bridgeWordsSha256"],
        reports["d3d12"]["bridgeWordsSha256"],
    )

    fail_log = root / "unity_fail_closed_d3d12.log"
    validate_log(fail_log, "d3d12", "fail_closed")
    evidence["failClosedD3D12"] = {"log": sha256(fail_log)}

    zhuangfy_log = root / "unity_zhuangfy_d3d12.log"
    zhuangfy_text = zhuangfy_log.read_text(encoding="utf-8", errors="replace")
    require(
        zhuangfy_log,
        "zhuangfy.d3d12.graphics_api",
        "Forcing GfxDevice: Direct3D 12" in zhuangfy_text,
        True,
    )
    require(
        zhuangfy_log,
        "zhuangfy.d3d12.batch_exit",
        "Exiting batchmode successfully now!" in zhuangfy_text,
        True,
    )
    require(
        zhuangfy_log,
        "zhuangfy.d3d12.point_shadow_producer",
        ZHUANGFY_PRODUCER_TOKEN in zhuangfy_text,
        True,
    )
    require(
        zhuangfy_log,
        "zhuangfy.d3d12.b31",
        LIGHT_DATA_TOKEN in zhuangfy_text,
        True,
    )
    require(
        zhuangfy_log,
        "zhuangfy.d3d12.b34",
        ACTIVE_TOKEN in zhuangfy_text,
        True,
    )
    require(zhuangfy_log, "zhuangfy.d3d12.script_errors", "error CS" in zhuangfy_text, False)
    require(zhuangfy_log, "zhuangfy.d3d12.shader_errors", "Shader error in" in zhuangfy_text, False)
    zhuangfy_beauty = root / "zhuangfy_beauty_d3d12.png"
    require(
        zhuangfy_beauty,
        "zhuangfy.d3d12.beauty",
        sha256(zhuangfy_beauty),
        EXPECTED_ZHUANGFY_BEAUTY_D3D12,
    )
    evidence["zhuangfyD3D12"] = {
        "log": sha256(zhuangfy_log),
        "beauty": sha256(zhuangfy_beauty),
    }

    sources = {
        "contract": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredDeferredShadowDataContract.cs",
        "owner": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredDeferredShadowData.cs",
        "punctualProducer": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredPunctualShadowProducer.cs",
        "lightDataOwner": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredDeferredLightData.cs",
        "pipeline": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs",
        "probe": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Resources/EndfieldRecoveredDeferredShadowDataProbe.compute",
        "batchVerifier": LAB_ROOT / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldRecoveredDeferredShadowDataBatchVerifier.cs",
        "sourceAuditor": LAB_ROOT / "tools/audit_deferred_shadow_data.py",
        "validator": Path(__file__).resolve(),
        "wrapper": LAB_ROOT / "verify_recovered_deferred_shadow_data.bat",
    }
    output = {
        "schema": "endfield-recovered-deferred-shadow-data-frame-validation-v1",
        "valid": True,
        "defaultOff": True,
        "pass0ConsumerEnabled": False,
        "fullNamedAndD3D11BridgeBitExact": True,
        "unownedSectionsZero": True,
        "sameFrameProducerSnapshot": True,
        "matchingD16Atlas": True,
        "wulfaSpotAndZhuangfyPointRowsValidated": True,
        "activeControlBeautyBitExact": True,
        "failClosedWithoutPunctualProducer": True,
        "generalSceneShadowDataRecovered": False,
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
        "Deferred ShadowData validation passed: full b34 and CB5 exact on "
        "D3D11/D3D12, same-frame punctual producer gated, pass0 disabled."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
