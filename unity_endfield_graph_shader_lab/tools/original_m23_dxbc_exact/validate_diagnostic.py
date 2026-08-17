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
DIAGNOSTIC_VS_SOURCE_SHA256 = "8a45e1a2462f164538430228eb5fa482e3337f6ec40189d273bc76cbd6c61e98"
DIAGNOSTIC_VS_COMPILED_SHA256 = "51f0011ff8f7fbeaa9f0dfb60d95de82f010a3cbef77c14393313d425d16e707"
EXPECTED_PS_SIGNATURE = [
    ("SV_Position", 0, 0, 0xF),
    ("TEXCOORD", 0, 1, 0xF), ("TEXCOORD", 1, 2, 0xF),
    ("TEXCOORD", 2, 3, 0xF), ("TEXCOORD", 3, 4, 0x7),
    ("TEXCOORD", 4, 5, 0xF), ("TEXCOORD", 5, 6, 0xF),
    ("TEXCOORD", 6, 7, 0x7), ("TEXCOORD", 7, 8, 0x7),
]

def _pixel_signature() -> list[tuple[str, int, int, int]]:
    data = (BYTECODE / EXPECTED["pixel"][0]).read_bytes()
    chunk = data.find(b"ISGN")
    if chunk < 0:
        raise AssertionError("0139 is missing ISGN")
    payload = chunk + 8
    count = int.from_bytes(data[payload:payload + 4], "little")
    table = int.from_bytes(data[payload + 4:payload + 8], "little")
    result = []
    for index in range(count):
        entry = payload + table + index * 24
        name_offset = int.from_bytes(data[entry:entry + 4], "little")
        semantic_index = int.from_bytes(data[entry + 4:entry + 8], "little")
        register = int.from_bytes(data[entry + 16:entry + 20], "little")
        mask_word = int.from_bytes(data[entry + 20:entry + 24], "little")
        name_end = data.find(b"\0", payload + name_offset)
        name = data[payload + name_offset:name_end].decode("ascii")
        result.append((name, semantic_index, register, mask_word & 0xFF))
    return result

def validate_blobs() -> None:
    for stage, (name, size, digest) in EXPECTED.items():
        path = BYTECODE / name
        data = path.read_bytes()
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise AssertionError(f"{stage} M23 blob drift: {path}")
        if data[:4] != b"DXBC":
            raise AssertionError(f"{stage} is not DXBC")
    if _pixel_signature() != EXPECTED_PS_SIGNATURE:
        raise AssertionError("0139 PS ISGN signature drift")

def validate_report(path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    diagnostic = report.get("mode") == "diagnostic_vs_exact_ps"
    required = {
        "schema": "endfield.original-m23-dxbc-exact.v3",
        "mode": "diagnostic_vs_exact_ps" if diagnostic else "exact_pair",
        "vertex_sha256": EXPECTED["vertex"][2],
        "pixel_sha256": EXPECTED["pixel"][2],
        "vs_constant_buffer_creation_mask": "0x1f",
        "ps_constant_buffer_creation_mask": "0x1f",
        "shader_resource_creation_mask": "0x1f",
        "sampler_creation_mask": "0x1f",
        "b4_high_semantics": "zero_or_sentinel_only_non_fidelity",
        "vs_binding_mask": "0x1",
        "ps_binding_mask": "0x1",
        "vs_constant_buffer_binding_mask": "0x1f",
        "ps_constant_buffer_binding_mask": "0x1f",
        "shader_resource_binding_mask": "0x1f",
        "sampler_binding_mask": "0x1f",
        "state_binding_mask": "0x7",
        "render_target_binding_mask": "0x1",
        "vertex_shader_resource_creation_mask": "0x0" if diagnostic else "0x1",
        "vertex_shader_resource_binding_mask": "0x0" if diagnostic else "0x1",
        "topology_binding_mask": "0x1",
        "viewport_binding_mask": "0x1",
    }
    if diagnostic:
        required.update({
            "input_layout_creation_mask": "0x0",
            "vertex_buffer_creation_mask": "0x0",
            "no_input_layout_binding_mask": "0x1",
            "no_vertex_buffer_binding_mask": "0x1",
            "diagnostic_vs_source_sha256": DIAGNOSTIC_VS_SOURCE_SHA256,
            "diagnostic_vs_compiled_sha256": DIAGNOSTIC_VS_COMPILED_SHA256,
            "diagnostic_vs_compiled_hash_mask": "0x1",
            "diagnostic_vs_signature_mask": "0x1",
            "diagnostic_vs_source_hash_mask": "0x1",
        })
    else:
        required.update({
            "input_layout_creation_mask": "0x1",
            "vertex_buffer_creation_mask": "0x1",
            "input_binding_mask": "0x1",
            "vertex_buffer_binding_mask": "0x1",
        })
    for key, expected in required.items():
        if report.get(key) != expected:
            raise AssertionError(f"{key}: expected {expected!r}, got {report.get(key)!r}")
    if report.get("status") != "pass":
        raise AssertionError("M23 native exact fixture did not pass")
    if report.get("draw_issued") != 1 or report.get("readback_finite") != 1:
        raise AssertionError("M23 draw/readback proof is incomplete")
    if report.get("visual_fidelity_claim") != 0:
        raise AssertionError("M23 fixture incorrectly claims visual fidelity")
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
