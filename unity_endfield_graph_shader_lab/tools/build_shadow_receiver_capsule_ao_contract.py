"""Pin the ShadowPlane capsule-AO consumer ABI from the exact ShadowReceiver DXBC.

The CharInfo presentation manifest lists a missing "shipped capsule-AO
producer". Disassembling the already-pinned `HGRP/CharacterNPR_ShadowReceiver`
fragment program shows that no separate analytic capsule producer exists: the
receiver consumes the VisibilitySH screen buffer and its log-SH LUT, and lerps
the shaded result toward `_CapsuleAoColor` by the resulting occlusion.

The lab already implements that producer as
`EndfieldRecoveredVisibilitySHProducer`, which publishes the screen buffer, the
LUT, and a readiness flag. What is genuinely missing is narrower than the
manifest states: the SH-magnitude-to-LUT encode scale/bias in fragment `cb4[3]`.

This builder re-derives the contract from the pinned bytecode so it stays
reproducible. It verifies the DXBC hash, disassembles it, asserts every
instruction landmark the conclusion rests on, and fails closed otherwise.

Usage:
    python tools/build_shadow_receiver_capsule_ao_contract.py
    python tools/build_shadow_receiver_capsule_ao_contract.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(
    PROJECT_ROOT,
    "Assets",
    "EndfieldGraphShaderLab",
    "Generated",
    "OriginalData",
    "CharInfoPresentation",
)
FRAGMENT_DXBC = os.path.join(
    EVIDENCE_DIR, "ShaderEvidence", "ShadowReceiver.fragment.dxbc.bytes"
)
CONTRACT_PATH = os.path.join(
    EVIDENCE_DIR, "shadow_receiver_capsule_ao_contract.json"
)
DISASSEMBLER = os.path.join(
    PROJECT_ROOT, "tools", "original_m23_dxbc_exact", "_disasm.exe"
)

FRAGMENT_SHA256 = (
    "88367e81d2557e26f6154a7ef2b29bb22abf1a65786d08fc7f0696df43950769"
)

# Instruction landmarks the recovered equation rests on. Each entry is a
# substring that must appear exactly once in the disassembly, so a future
# shader revision cannot silently invalidate the contract.
LANDMARKS = {
    "screen_uv_scale": "mul r0.yz, v0.xxyx, cb0[82].zzwz",
    "visibility_sh_sample": "r1.xyzw, r0.yzyy, t5.xyzw, s0",
    "significance_test": "lt r2.xyzw, l(0.000100, 0.000100, 0.000100, 0.000100), |r1.xyzw|",
    "halving_threshold": "ge r2.y, l(4.600000), r0.w",
    "lut_encode": "mad r0.y, r0.y, cb4[3].x, cb4[3].y",
    "lut_quantise": "mad r0.y, r0.y, l(255.000000), l(0.500000)",
    "lut_texel_scale": "mul r3.x, r0.y, l(0.003906)",
    "lut_sample": "r0.yz, r3.xyxx, t4.zxyw, s0",
    "gstar_scale_bias": "mad r0.yz, r0.yyzy, cb4[2].xxyx, cb4[2].zzwz",
    "band0_gain": "mul r3.x, r0.y, l(3.544908)",
    "log_exponent": "mul r0.y, r1.x, l(0.406977)",
    "sh_self_product": "mul r4.xyzw, r3.xyzw, l(0.282095, 0.282095, 0.282095, 0.282095)",
    "band_evaluation": "mul r1.xy, r3.yxyy, l(-0.325735, 0.282095, 0.000000, 0.000000)",
    "occlusion_luma_fold": "dp3 r0.w, r0.wwww, l(0.212673, 0.715152, 0.072175, 0.000000)",
    "capsule_ao_lerp": "mad o0.xyz, r0.wwww, r1.xyzx, r0.xyzx",
    "shadow_color_lerp": "mad r0.xyz, r0.xxxx, r0.yzwy, l(1.000000, 1.000000, 1.000000, 0.000000)",
}


class ContractError(RuntimeError):
    """Fail-closed contract error."""


def _sha256(path: str) -> tuple[int, str]:
    data = open(path, "rb").read()
    return len(data), hashlib.sha256(data).hexdigest()


def disassemble() -> str:
    if not os.path.isfile(DISASSEMBLER):
        raise ContractError(f"disassembler not found: {DISASSEMBLER}")
    if not os.path.isfile(FRAGMENT_DXBC):
        raise ContractError(f"pinned fragment DXBC not found: {FRAGMENT_DXBC}")

    size, digest = _sha256(FRAGMENT_DXBC)
    if digest != FRAGMENT_SHA256:
        raise ContractError(
            f"fragment DXBC sha256 changed: {digest} != {FRAGMENT_SHA256}"
        )

    result = subprocess.run(
        [DISASSEMBLER, FRAGMENT_DXBC],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ContractError(f"disassembly failed: {result.stderr.strip()}")
    return result.stdout


def verify_landmarks(disassembly: str) -> dict:
    located = {}
    for name, needle in LANDMARKS.items():
        occurrences = disassembly.count(needle)
        if occurrences != 1:
            raise ContractError(
                f"landmark '{name}' appears {occurrences} times, expected 1: {needle}"
            )
        line = None
        for candidate in disassembly.splitlines():
            if needle in candidate:
                match = re.match(r"\s*(\d+):", candidate)
                line = int(match.group(1)) if match else None
                break
        located[name] = {"instruction": line, "text": needle}
    return located


def build_contract(disassembly: str) -> dict:
    size, digest = _sha256(FRAGMENT_DXBC)
    return {
        "schema": "endfield.charinfo.shadow-receiver-capsule-ao.v1",
        "boundary": "source_closed_consumer_with_one_open_constant",
        "source": {
            "shader": "HGRP/CharacterNPR_ShadowReceiver",
            "pass": "ShadowReceiver",
            "path_id": "2521598335323475540",
            "fragment_dxbc": os.path.relpath(FRAGMENT_DXBC, PROJECT_ROOT).replace(
                "\\", "/"
            ),
            "fragment_bytes": size,
            "fragment_sha256": digest,
        },
        "finding": (
            "There is no separate analytic capsule-AO producer. The shipped "
            "ShadowReceiver consumes the VisibilitySH screen buffer plus its "
            "log-SH LUT and lerps the shaded result toward _CapsuleAoColor by "
            "the decoded occlusion. The producer the manifest calls missing is "
            "the already-implemented VisibilitySH producer."
        ),
        "consumer_abi": {
            "t4": {
                "role": "log-SH LUT",
                "lab_property": "_LogSHLutTex",
                "published_by": "EndfieldRecoveredVisibilitySHProducer",
            },
            "t5": {
                "role": "VisibilitySH screen buffer",
                "lab_property": "_EndfieldRecoveredVisibilitySH",
                "published_by": "EndfieldRecoveredVisibilitySHProducer",
                "screen_uv": "SV_Position.xy * cb0[82].zw",
            },
            "cb4[2]": {
                "role": "LUT coefficient scale/bias",
                "retail_name": "_GStarParams",
                "status": "source_closed",
                "evidence": (
                    "the lab producer already applies the identical "
                    "lut * _GStarParams.xy + _GStarParams.zw form"
                ),
            },
            "cb4[3].xy": {
                "role": "SH-magnitude to LUT-coordinate encode scale/bias",
                "status": "not_recovered_fail_closed",
                "note": (
                    "the only value still missing before the receiver can "
                    "evaluate the exact occlusion"
                ),
            },
            "cb5[2].xyz": {"role": "_ShadowColor"},
            "cb5[2].w": {"role": "shadow amount multiplier"},
            "cb5[3].xyz": {"role": "_CapsuleAoColor"},
        },
        "recovered_equation": [
            "uv = SV_Position.xy * cb0[82].zw",
            "sh = t5.SampleLevel(s0, uv, 0)",
            "if all(|sh| <= 1e-4): visibility = float2(0, 1)",
            "else: halve sh while length(sh.yzw) > 4.6, counting the halvings",
            "lutX = (length(sh.yzw) * cb4[3].x + cb4[3].y) * 255 + 0.5, scaled by 1/256",
            "lut = t4.SampleLevel(s0, float2(lutX, 0.5), 0)",
            "coefficients = lut * cb4[2].xy + cb4[2].zw",
            "band = float4(coefficients.x * 3.544908, coefficients.y * sh.yzw)",
            "band *= exp2(sh.x * 0.406977)",
            "repeat the halving count: band = SH self-product scaled by 0.282095",
            "visibility = float2(band.y * -0.325735, band.x * 0.282095)",
            "occlusion = 1 - saturate(max(visibility.x + visibility.y, 0))",
            "result = lerp(1, cb5[2].xyz, shadowTerm)",
            "output.rgb = lerp(result, cb5[3].xyz, occlusion)",
        ],
        "constants": {
            "sh_band0": 0.282095,
            "sh_band1_convolved": -0.325735,
            "band0_gain": 3.544908,
            "log_exponent_scale": 0.406977,
            "halving_threshold": 4.6,
            "significance_epsilon": 0.0001,
            "note": (
                "3.544908 is 2*sqrt(pi) and 0.282095 is 1/(2*sqrt(pi)); the DXBC "
                "exp opcode is base 2"
            ),
        },
        "landmarks": verify_landmarks(disassembly),
        "open_gap": (
            "cb4[3].xy. Until its producer is recovered the lab receiver must "
            "keep its zero capsule-AO stub rather than substituting a fitted "
            "encode."
        ),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the landmarks and the existing contract without rewriting it",
    )
    args = parser.parse_args(argv)

    try:
        disassembly = disassemble()
        contract = build_contract(disassembly)
    except ContractError as error:
        print(f"contract build failed: {error}", file=sys.stderr)
        return 2

    if args.check:
        if not os.path.isfile(CONTRACT_PATH):
            print(f"missing contract: {CONTRACT_PATH}", file=sys.stderr)
            return 2
        existing = json.load(open(CONTRACT_PATH, encoding="utf-8"))
        if existing != contract:
            print("contract differs from the pinned bytecode", file=sys.stderr)
            return 1
        print("shadow-receiver capsule-AO contract matches the pinned bytecode")
        return 0

    with open(CONTRACT_PATH, "w", encoding="utf-8") as handle:
        json.dump(contract, handle, indent=2)
        handle.write("\n")
    print(f"wrote {os.path.relpath(CONTRACT_PATH, PROJECT_ROOT)}")
    print(f"  landmarks verified: {len(contract['landmarks'])}")
    print(f"  open gap: {contract['open_gap']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
