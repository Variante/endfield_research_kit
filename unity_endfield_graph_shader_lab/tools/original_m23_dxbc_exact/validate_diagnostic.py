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
M23_MATERIAL_SHA256 = "81b920be11d13b3662a97851c97c8a41ef98333478578eacd2a164d4befe98fa"
M23_CONTRACT_SHA256 = "41402be441ad98c7823d021fb86c1fc3e48ecd6515a58d46eedfd0be6eea7eeb"
NAMED_LOW_COMPONENT_MAP = ("cb4[0].x=1,cb4[0].y=0,cb4[0].z=0,cb4[0].w=0;"
    "cb4[1].x=1,cb4[1].y=0,cb4[1].z=4,cb4[1].w=4.14;"
    "cb4[2].y=1,cb4[2].z=0,cb4[2].w=0;cb4[3].x=1,cb4[3].y=0;"
    "cb4[4]=(0.3080313,0.83496046,0.9547169,1);"
    "cb4[5].x=0,cb4[5].y=0,cb4[5].z=1;cb4[6]=(0,0,1,0);"
    "cb4[7]=(-1,8.742278e-08,-8.742278e-08,-1);cb4[8]=(1,0,0,0);"
    "cb4[9]=(-1,1.5,0.82,-0.1)")
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
    mode = report.get("mode")
    named_low = mode == "diagnostic_vs_exact_ps_named_low"
    diagnostic = isinstance(mode, str) and mode.startswith("diagnostic_vs_exact_ps")
    exact_textures = mode in {
        "diagnostic_vs_exact_ps_exact_textures_named_low",
        "diagnostic_vs_exact_ps_exact_textures_high_neutral",
        "diagnostic_vs_exact_ps_exact_textures_high_neutral_rgb_gate",
    }
    required = {
        "schema": "endfield.original-m23-dxbc-exact.v3",
        "mode": mode,
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
    if diagnostic and not exact_textures:
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
    if named_low:
        required.update({
            "named_low_material_sha256": M23_MATERIAL_SHA256,
            "named_low_contract_sha256": M23_CONTRACT_SHA256,
            "named_low_material_hash_mask": "0x1",
            "named_low_contract_hash_mask": "0x1",
            "named_low_component_map_mask": "0x1",
            "named_low_component_map": NAMED_LOW_COMPONENT_MAP,
        })
    if mode == "diagnostic_vs_exact_ps_high_probe":
        required.update({"high_probe_execution_mask": "0x1"})
    if mode == "diagnostic_vs_exact_ps_high_baseline":
        required.update({
            "input_layout_creation_mask": "0x0", "vertex_buffer_creation_mask": "0x0",
            "no_input_layout_binding_mask": "0x1", "no_vertex_buffer_binding_mask": "0x1",
            "diagnostic_vs_source_sha256": DIAGNOSTIC_VS_SOURCE_SHA256,
            "diagnostic_vs_compiled_sha256": DIAGNOSTIC_VS_COMPILED_SHA256,
            "diagnostic_vs_compiled_hash_mask": "0x1", "diagnostic_vs_signature_mask": "0x1",
            "diagnostic_vs_source_hash_mask": "0x1", "high_baseline_value_mask": "0x1",
            "high_probe_execution_mask": "0x1", "diagnostic_b2_gate_mask": "0x1",
        })
    if mode == "diagnostic_vs_exact_ps_high_neutral":
        required.update({
            "high_neutral_domain_mask": "0x1", "diagnostic_b2_gate_mask": "0x1",
            "synthetic_t0_readback_mask": "0x1", "synthetic_t0_hash_mask": "0x1",
        })
    if mode == "diagnostic_vs_exact_ps_high_neutral_override":
        required.update({
            "high_neutral_domain_mask": "0x1", "diagnostic_b2_gate_mask": "0x1",
            "synthetic_t0_readback_mask": "0x1", "synthetic_t0_hash_mask": "0x1",
        })
        if report.get("high_neutral_override_mask") not in {"0x1", "0x2", "0x3"}:
            raise AssertionError("invalid high-neutral override mask")
    if exact_textures:
        required.update({
            "input_layout_creation_mask": "0x0", "vertex_buffer_creation_mask": "0x0",
            "no_input_layout_binding_mask": "0x1", "no_vertex_buffer_binding_mask": "0x1",
            "exact_texture_source_hash_mask": "0x1f", "exact_texture_decode_mask": "0x1f",
            "exact_texture_widths": [128, 256, 1024, 512, 512],
            "exact_texture_heights": [128, 256, 1024, 512, 512],
            "exact_texture_vs_signature_mask": "0x1",
            "exact_texture_vs_source_hash_mask": "0x1",
            "exact_texture_vs_compiled_hash_mask": "0x1",
            "exact_texture_grid_size": 16,
            "exact_texture_grid_finite_pixels": 256,
            "exact_texture_color_space_assumption": "WIC 32bpp RGBA uploaded as UNORM; no sRGB transform",
        })
        if mode == "diagnostic_vs_exact_ps_exact_textures_high_neutral_rgb_gate":
            required["exact_texture_causal_override_mask"] = "0x1"
    if not diagnostic:
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
