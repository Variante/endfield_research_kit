#!/usr/bin/env python3
"""Validate cross-API ShaderVariablesGlobal GPU and same-frame reports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_SH_WORDS = [
    "0xbbf76c60",
    "0x3ef1c917",
    "0x3c476813",
    "0x3f8c53be",
]
ACTIVATION_TOKEN = (
    "Recovered selected ShaderVariablesGlobal b35 / EndfieldCB1 reads are active; "
    "pass0=disabled."
)
FAIL_CLOSED_TOKEN = (
    "Recovered selected ShaderVariablesGlobal failed closed: canonical "
    "binning/reflection/VisibilitySHConstData prerequisites are not ready."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(check: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(
            "ShaderVariablesGlobal verification failed: "
            f"check={check}; expected={expected!r}; actual={actual!r}"
        )


def read_log(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\x00", "")


def verify(root: Path) -> dict[str, object]:
    reports: dict[str, dict[str, object]] = {}
    for api in ("d3d11", "d3d12"):
        path = root / f"gpu_validation_{api}.json"
        require(f"{api}_report_exists", path.is_file(), True)
        report = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "valid",
            "defaultOff",
            "sourceAuditHashMatches",
            "publicationReturnedReady",
            "readyObserved",
            "canonicalWordsMatch",
            "d3d11BridgeWordsMatch",
            "selectedConsumerWordsMatch",
            "unresolvedRegistersZero",
        ):
            require(f"{api}_{key}", report[key], True)
        require(f"{api}_pass0", report["pass0ConsumerEnabled"], False)
        require(f"{api}_buffer_bytes", report["bufferBytes"], 3200)
        require(f"{api}_vector_count", report["vectorCount"], 200)
        require(f"{api}_bridge_bytes", report["d3d11SelectedBytes"], 2512)
        require(f"{api}_selected_vectors", report["selectedVectorCount"], 32)
        require(
            f"{api}_selected_default_sh",
            report["selectedDefaultSHWords"],
            EXPECTED_SH_WORDS,
        )
        require(f"{api}_fail_closed_gate_count", len(report["failClosedGates"]), 6)
        for index, gate in enumerate(report["failClosedGates"]):
            require(f"{api}_gate_{index}_rejected", gate["rejected"], True)
            require(f"{api}_gate_{index}_diagnostic", gate["diagnosticMatched"], True)
        require(f"{api}_failures", report["failures"], [])
        reports[api] = report

        frame_log = read_log(root / f"unity_frame_{api}.log")
        require(f"{api}_frame_activation", ACTIVATION_TOKEN in frame_log, True)
        require(
            f"{api}_frame_no_fail_closed",
            "Recovered selected ShaderVariablesGlobal failed closed:" in frame_log,
            False,
        )

    fail_closed_log = read_log(root / "unity_fail_closed_d3d12.log")
    require("fail_closed_token", FAIL_CLOSED_TOKEN in fail_closed_log, True)
    require("fail_closed_no_activation", ACTIVATION_TOKEN in fail_closed_log, False)

    beauty_paths = {
        "d3d11": root / "wulfa_beauty_d3d11.png",
        "d3d12": root / "wulfa_beauty_d3d12.png",
        "fail_closed_d3d12": root / "wulfa_beauty_fail_closed_d3d12.png",
    }
    beauty_hashes = {name: sha256(path) for name, path in beauty_paths.items()}
    require(
        "d3d12_fail_closed_beauty",
        beauty_hashes["fail_closed_d3d12"],
        beauty_hashes["d3d12"],
    )

    return {
        "schema": "endfield-recovered-shader-variables-global-summary-v1",
        "valid": True,
        "canonicalWordsBitExact": True,
        "d3d11BridgeWordsBitExact": True,
        "crossApi": True,
        "selectedVectorCount": 32,
        "unresolvedRegistersZero": True,
        "sameFrameActivation": True,
        "failClosedWithoutCanonicalPrerequisites": True,
        "d3d12FailClosedBeautyUnchanged": True,
        "pass0ConsumerEnabled": False,
        "beautySha256": beauty_hashes,
        "sourceAuditSha256": reports["d3d11"]["sourceAuditSha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    summary = verify(args.root)
    output = args.root / "validation_summary.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        "ShaderVariablesGlobal verification passed: canonical 800 and "
        "EndfieldCB1 628 words exact on D3D11/D3D12; same-frame and "
        "D3D12 fail-closed beauty is unchanged."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
