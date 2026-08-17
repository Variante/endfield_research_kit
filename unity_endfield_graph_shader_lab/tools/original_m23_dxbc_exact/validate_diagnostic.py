"""Fail-closed checks for the isolated M23 exact-DXBC creation fixture."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BYTECODE = ROOT / "scratch/character_recovery/vfx_shader_variants/shader_export/Shader/HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader.bytecode"
EXPECTED = {
    "vertex": ("0138_endfield_dxbc_0.dxbc", 10720, "7d0a508f7b1e5c9aef0b89489feae97f8669a8cddaba1de0ccc0e26fd0eb2ca0"),
    "pixel": ("0139_endfield_dxbc_1.dxbc", 8100, "0ff508aa08112122c14a3ece17d12f15778eaf39ad0c639c946512dc996b6f83"),
}

def validate_blobs() -> None:
    for stage, (name, size, digest) in EXPECTED.items():
        path = BYTECODE / name
        data = path.read_bytes()
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise AssertionError(f"{stage} M23 blob drift: {path}")
        if data[:4] != b"DXBC":
            raise AssertionError(f"{stage} is not DXBC")

def validate_report(path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    required = {
        "schema": "endfield.original-m23-dxbc-creation.v1",
        "vertex_sha256": EXPECTED["vertex"][2],
        "pixel_sha256": EXPECTED["pixel"][2],
        "vs_constant_buffer_creation_mask": "0x1f",
        "ps_constant_buffer_creation_mask": "0x1f",
        "shader_resource_creation_mask": "0x1f",
        "sampler_creation_mask": "0x1f",
        "b4_high_semantics": "zero_or_sentinel_only_non_fidelity",
    }
    for key, expected in required.items():
        if report.get(key) != expected:
            raise AssertionError(f"{key}: expected {expected!r}, got {report.get(key)!r}")
    if report.get("status") != "pass":
        raise AssertionError("M23 native creation fixture did not pass")
    if report.get("binds_or_draws") is not False or report.get("visual_fidelity_claim") is not False:
        raise AssertionError("M23 creation fixture crossed its no-bind/no-draw boundary")
    return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    validate_blobs()
    if args.report:
        validate_report(args.report)
    print("M23 exact DXBC creation inputs/report valid")
