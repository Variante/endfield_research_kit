#!/usr/bin/env python3
"""Check that the recovered HGRP/Lit HGBuffer producer has not drifted.

This is a source-contract gate, not a retail-parity claim.  It checks the
selected fragment's five original MRT lanes against the source-shaped Unity
sidecar and records the deliberately open runtime boundary (neutral motion,
neutral packed flags, and no pass-0 presentation).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


LAB_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = (
    LAB_ROOT
    / "scratch/character_recovery/charinfo_outside_lit/hgbuffer_fragment.hlsl"
)
SIDECAR_PATH = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/"
    "EndfieldCharInfoHGRPLitUnavailable.shader"
)
RUNTIME_PATH = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredDeferredGBufferFrame.cs"
)
MATERIAL_PATH = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/CharInfoPresentation/"
    "Materials/M_CharInfo_outside.mat"
)


def _check_tokens(
    checks: list[dict[str, object]],
    failures: list[dict[str, object]],
    *,
    name: str,
    source: Path,
    text: str,
    tokens: Iterable[str],
) -> None:
    expected = list(tokens)
    missing = [token for token in expected if token not in text]
    result: dict[str, object] = {
        "check": name,
        "source": source.as_posix(),
        "expected": expected,
        "actual": {"missing": missing},
        "status": "pass" if not missing else "failed",
    }
    checks.append(result)
    if missing:
        failures.append(
            {
                "check": name,
                "source": source.as_posix(),
                "expected": f"all {len(expected)} tokens present",
                "actual": f"missing {missing!r}",
            }
        )


def _check_count(
    checks: list[dict[str, object]],
    failures: list[dict[str, object]],
    *,
    name: str,
    source: Path,
    text: str,
    token: str,
    minimum: int,
) -> None:
    actual = text.count(token)
    result: dict[str, object] = {
        "check": name,
        "source": source.as_posix(),
        "expected": {"token": token, "minimum": minimum},
        "actual": actual,
        "status": "pass" if actual >= minimum else "failed",
    }
    checks.append(result)
    if actual < minimum:
        failures.append(
            {
                "check": name,
                "source": source.as_posix(),
                "expected": f"{token!r} count >= {minimum}",
                "actual": actual,
            }
        )


def validate_payload_contract(
    *,
    source_text: str,
    sidecar_text: str,
    runtime_text: str,
    material_text: str,
    source_path: Path = SOURCE_PATH,
    sidecar_path: Path = SIDECAR_PATH,
    runtime_path: Path = RUNTIME_PATH,
    material_path: Path = MATERIAL_PATH,
) -> dict[str, object]:
    """Return structured checks and bounded diagnostics for the payload gate."""

    checks: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    _check_tokens(
        checks,
        failures,
        name="source.target0_fixed_payload",
        source=source_path,
        text=source_text,
        tokens=(
            "SV_Target.x = 0.0f;",
            "SV_Target.y = 0.0f;",
            "SV_Target.z = 0.0f;",
            "SV_Target.w = 0.5f;",
        ),
    )
    _check_tokens(
        checks,
        failures,
        name="source.scene_motion_encoding",
        source=source_path,
        text=source_text,
        tokens=(
            "SV_Target_1.x = mad(_195",
            "SV_Target_1.y = mad(_195",
            "SV_Target_1.w = _195 * 0.699999988079071044921875f;",
            "SV_Target_1.z = (_195 > 0.0f) ? 1.0f : _26_m0[7u].x;",
        ),
    )
    _check_tokens(
        checks,
        failures,
        name="source_mro_porosity_and_packed_flags",
        source=source_path,
        text=source_text,
        tokens=(
            "float _301 = mad(clamp(_26_m0[3u].w - 1.0f",
            "SV_Target_2.x = _301;",
            "float _312 = mad(_290.y",
            "SV_Target_2.y = mad(_26_m0[1u].x, _290.z - 1.0f, 1.0f);",
            "SV_Target_3.z = _312;",
            "SV_Target_2.z = mad(clamp(mad(_26_m0[4u].w, _312",
            "SV_Target_3.w = _71(_341 & 3u)",
            "SV_Target_2.w = _71(_341 >> 2u)",
        ),
    )
    _check_tokens(
        checks,
        failures,
        name="source_normal_and_base_color_lanes",
        source=source_path,
        text=source_text,
        tokens=(
            "SV_Target_3.x = mad(",
            "SV_Target_3.y = mad(",
            "SV_Target_4.x = mad(",
            "SV_Target_4.y = mad(",
            "SV_Target_4.z = mad(",
            "SV_Target_4.w = 0.0f;",
        ),
    )

    _check_tokens(
        checks,
        failures,
        name="sidecar.five_mrt_outputs",
        source=sidecar_path,
        text=sidecar_text,
        tokens=(
            "float4 sceneColor : SV_Target0;",
            "float4 sceneMotion : SV_Target1;",
            "float4 gBufferA : SV_Target2;",
            "float4 gBufferB : SV_Target3;",
            "float4 gBufferC : SV_Target4;",
        ),
    )
    _check_count(
        checks,
        failures,
        name="sidecar.source_shaped_passes",
        source=sidecar_path,
        text=sidecar_text,
        token="output.gBufferA =",
        minimum=2,
    )
    _check_tokens(
        checks,
        failures,
        name="sidecar.mro_and_porosity_lanes",
        source=sidecar_path,
        text=sidecar_text,
        tokens=(
            "float metallic = lerp(_Metallic, mro.r, 1.0);",
            "float occlusion = lerp(1.0, mro.b, _OcclusionStrength);",
            "float roughness = lerp(_RoughnessMin, _RoughnessMax, mro.g);",
            "_PorosityFactorY * roughness +",
            "metallic * _PorosityFactorZ +",
            "_PorosityFactorX",
            "output.gBufferC = float4(_BaseColor.rgb, 0.0);",
            "EncodeYUpOctNormal(input.normalWS)",
        ),
    )
    _check_tokens(
        checks,
        failures,
        name="runtime.resolver_alias_boundary",
        source=runtime_path,
        text=runtime_text,
        tokens=(
            "command.SetGlobalTexture(ResolverGBufferT23Id, gBufferC)",
            "command.SetGlobalTexture(ResolverGBufferT24Id, gBufferB)",
            "command.SetGlobalTexture(ResolverGBufferT25Id, gBufferA)",
            "command.SetGlobalTexture(ResolverSourceTextureT23Id, gBufferC)",
            "command.SetGlobalTexture(ResolverSourceTextureT24Id, gBufferB)",
            "command.SetGlobalTexture(ResolverSourceTextureT25Id, gBufferA)",
            "pass0ConsumerEnabled=false",
        ),
    )
    _check_tokens(
        checks,
        failures,
        name="material.source_mro_inputs",
        source=material_path,
        text=material_text,
        tokens=(
            "_MROMap:",
            "guid: 88ba0331b3bc79a4baf0d06d07dbdb90",
            "- _PorosityFactorX: 0.2",
            "- _PorosityFactorY: 0.4",
            "- _PorosityFactorZ: 0",
            "- _BaseColor: {r: 1, g: 1, b: 1, a: 1}",
        ),
    )

    known_gaps = [
        {
            "check": "sidecar.scene_motion",
            "status": "open",
            "evidence": "sidecar uses neutral float4(0.5, 0.5, 0.0, 0.0)",
            "meaning": "source motion equation is pinned, but live camera/deformation history is not",
        },
        {
            "check": "sidecar.packed_flags",
            "status": "open",
            "evidence": "sidecar writes zero fourth lanes",
            "meaning": "source packed-flag producer is known; live flag inputs are not",
        },
        {
            "check": "runtime.pass0_presentation",
            "status": "open",
            "evidence": "pass0ConsumerEnabled=false",
            "meaning": "aliases are diagnostic and are not admitted to the retail resolver",
        },
    ]
    return {
        "schema": "endfield.recovered-deferred-gbuffer-payload-contract.v1",
        "status": "pass" if not failures else "validation_failed",
        "checkCount": len(checks),
        "failedCount": len(failures),
        "checks": checks,
        "failures": failures,
        "knownGaps": known_gaps,
    }


def load_current() -> dict[str, object]:
    paths = {
        "source_text": SOURCE_PATH,
        "sidecar_text": SIDECAR_PATH,
        "runtime_text": RUNTIME_PATH,
        "material_text": MATERIAL_PATH,
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing payload contract input(s): " + ", ".join(missing))
    return validate_payload_contract(
        **{
            name: path.read_text(encoding="utf-8", errors="replace")
            for name, path in paths.items()
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit only the structured validation report",
    )
    args = parser.parse_args()
    report = load_current()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            "HGRP/Lit HGBuffer payload contract: "
            f"{report['status']} ({report['checkCount']} checks, "
            f"{report['failedCount']} failures)"
        )
        for failure in report["failures"][:3]:
            print(
                "  failure: "
                f"check={failure['check']}; source={failure['source']}; "
                f"expected={failure['expected']}; actual={failure['actual']}"
            )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
