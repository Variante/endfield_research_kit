#!/usr/bin/env python3
"""Fail-closed audit for the narrow Endminf overview BaseV2 admission."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
MATERIALS = REPO / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material"
VARIANTS = REPO / "scratch/character_recovery/vfx_shader_variants/shader_export/Shader/HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader.bytecode"
RECOVERED_SHADER = LAB / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldZhuangfyVFXBaseV2MRT.shader"
SHADER_ID = -1430105248647086886
M14_CAPTURED_VERTEX_HASH = "b47cd6d240be5068"
M14_CAPTURED_FRAGMENT_HASH = "2d090c0ebba1b49c"
M14_CAPTURED_SIDECAR_INDEX = 4914
M20_VARIANT_PAIRS = {
    876: ("e8f38f2f7519383d", "fea38543389b6ff4"),
    4950: ("4bef98c73ca34880", "246a0f4f2d3c34f4"),
}
ROWS = {
    "M_fx_endminm_gfx_12_p13C3BA85865CFBD0.json": ("2692ba4895cbac3a6c773835bb9f748435c527177ff8e4a6e37af9f0dc92dc9f", ["_SAMPLE_TEX0"]),
    "M_fx_endminm_gfx_13_p57A25F1386F7012F.json": ("1a878e7f9d441e9685028836e89f10f0da0b5d1299afe38261bbd451dec2a42a", ["_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2", "_SAMPLE_TEX3", "_USE_POLARUV", "_USE_SCREENUV"]),
    "M_fx_endminm_gfx_15_p418FE5EF54286417.json": ("21ef63866f7aa566eae136153c5a3a57ed731ddf293cc71cb3171bfd15e14109", ["_SAMPLE_TEX0", "_USE_POLARUV", "_USE_SCREENUV"]),
    "M_fx_endminm_gfx_17_p392693FCB1EC4C68.json": ("7b1d19150c565eedbe213b72cae988532cb5db6b22054770689c104c59c2f5cc", []),
    "M_fx_endminm_gfx_19_pF43088E31E25D24A.json": ("833c16f936b6fcffdf2c321d4579dc581ff928932e730ed0ed89670b285a7b4b", ["_SAMPLE_TEX0"]),
    "M_fx_endminm_gfx_22_pEC97B180E0A82AB7.json": ("c06a90a3ce249606e01a8603cec2318bd6a6a9c1e3a10db1bddc988194610234", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_31_p602883BD6BB1831B.json": ("bfc0bdb1643c84a9095fa2b28ae149970dc139557f846b4f7f42a9bbf6043f50", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_39_pBF692EC36800069D.json": ("974e7c2369223840d03b59d67800b768f32ea2439a2475f7fe931919a5d35da1", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_40_p26EC2259AEC716E7.json": ("e4ce1fc973e0c93e4df8eaa70145742b88405a2ba1d57bdddbf4a6960597d029", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_14_pF6DCA5E6B2122169.json": ("eb20e4b35085aed91c0756fb95f3896b7b0694e6bcc96bb8674570d26f80c5b6", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_16_pF1C3F38D51FA67EF.json": ("b2a1e5ba51f0f4b36e95740bbd6546a2d03aa545c9e5660812862aa2c759abea", ["_SAMPLE_TEX0"]),
    "M_fx_endminm_gfx_18_p7010821E75C0A247.json": ("7a5f4f452d0e446d3907dfd33a88a69bc478ee5c3840a62977035a0d30ece3c1", ["_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2", "_SAMPLE_TEX3"]),
    "M_fx_endminm_gfx_20_pEE9E2589EB9513AE.json": ("0b6538aa3fb4f0e432537587cc388c26e9b22c6a04ea5bbfd7267d18433b4ec5", ["_SAMPLE_TEX0", "_SAMPLE_TEX1", "_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_21_p8EE22B791F9A2753.json": ("8c82096377201d927539b18500bcc34104a160c670e801b749a01df5ecf97def", ["_USE_FRESNEL"]),
    "M_fx_endminm_gfx_26_p364397B467C89F2E.json": ("f96a771e7f4b1615f0f8a840907a33b9419766694e13b3f3e7b67df47d56daab", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_05_p3409DAC8F2A1253D.json": ("b95b05852b05491f5132257918c59b7491b25bc9a3594c48f2cf4b94a4237f55", []),
    "M_fx_endminm_gfx_08_p014C92101D852EC4.json": ("43daa1bcbc22bbb8c7fb833d3130d931b1d8bf4e24f33e8c03cd1986f4abf0cf", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_09_p632B1622242536EC.json": ("7ae117bb32cbae3b5050dfa691416616579c21ae07b2b8a1036896b356e3495c", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_36_p655CC24C5B0D67F2.json": ("659c5e84ad48c7bba69f104a5fd01c47bd8e738de500ea93d95a48dd3b65f823", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_41_pB17322AF98845218.json": ("d4341d6866be34ad4be2ed77431825edc7153d5b27ec5763e88eb999aa688106", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_45_pE744767C80FE8433.json": ("b29fbdc088a7a7851e47722e934a1901995c52f9986206af3830d00d4e08499c", ["_SAMPLE_TEX0", "_SAMPLE_TEX1"]),
    "M_fx_endminm_gfx_46_p5D8517046749BD84.json": ("f2fc9eba631d1c958d8337558d00f0a3869380f12a509bd76d6444e2bc952c1f", ["_SAMPLE_TEX0", "_SAMPLE_TEX1"]),
    "M_map_interact_04_04_p9914E0CD5285A586.json": ("c6d2d98876f136cb10916ecf166aa0eeba51ba308e0d8701c1c05ed038bb2045", []),
    "M_ui_wind_901_pA55BF26D14F133FE.json": ("1d82f98a62b1c78eaa2df32d72a7e5bcd3a8393ea31e6d69b6b81af7d6a8f045", ["_SAMPLE_TEX0", "_SAMPLE_TEX1", "_USE_POLARUV", "_USE_SCREENUV"]),
    "M_fx_endminm_gfx_10_p2FE0832EAEFAA074.json": ("5d507e124fbafbc03136ae7c1df7d0691ef666322dabc0171f89282a14d9bd86", ["_USE_SOFTBLEND"]),
    "M_ui_glow_901_p5F6E5795FD9FD4B6.json": ("d8c4103c13c0c52f9222204efbf629f3ef4a307b58d2ea01d6a0728c1da913d5", ["_SAMPLE_TEX0"]),
    "M_ui_lizi_901_p3AF64D68AFB748E7.json": ("711de644f4f8dfae82f476944b354b64a6b9a82ee132786af79b009cf07bd038", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_29_p7BCC4552203800A8.json": ("bb8249224fdd3a6844f783a801c1566bf90d1dbd8b003bc1abc846b153f59cfb", ["_SAMPLE_TEX0", "_SAMPLE_TEX1"]),
    "M_fx_endminm_gfx_24_p65C0CDA093B23305.json": ("03b74a0a2db30c548244c6ef0bdbb32337a60cce614fb9a2606cf5719d256997", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_32_p75A3068776F01BCF.json": ("b154d46bc6ba4df11cd9990e1ea8addef3b5d9b5b7b54d01f1b218a533696021", ["_SAMPLE_TEX0", "_USE_POLARUV", "_USE_SCREENUV"]),
    "M_fx_endminm_gfx_35_p75854801AE9519E8.json": ("3503dd757c00a431b7f419d6263a119b0063504fefe73bd8e719ebd9f903c688", ["_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2", "_USE_VERTOFFSET"]),
    "M_fx_endminm_gfx_34_pAE712D0FF5A7A00A.json": ("fb00a820d29e8d46b4bd177dce54d488abd92461bc9a9d6b5a6124c653fde902", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_42_p49DDD5599C166F6B.json": ("41e783e9064af453c48f4a3a17ec27188a23a3b2a897d342030c61b678662565", ["_SAMPLE_TEX0", "_USE_POLARUV", "_USE_SCREENUV"]),
    "M_fx_endminm_gfx_30_p5FE318FDDD817ADA.json": ("f6d1e7e0c6b7f8041d074edff22b75c35f132c8263d40f179f24f5a7679acc63", ["_USE_SOFTBLEND"]),
    "M_fx_endminm_gfx_43_p73D80B62F5BA886F.json": ("37ee84b3ca175663bc9136eceea5b086ee3b7a375ec95dc00c017d9b07039e03", ["_USE_SOFTBLEND"]),
    "M_endminf_ui_overview_01_rock_03_p9EBBC39832869160.json": ("f467cbb003de0048d8ca4bbe8eca9c4a16ab0e19d2c70c49f32ff937218c4bf9", []),
}

QUEUE_OVERRIDES = {
    "M_fx_endminm_gfx_31_p602883BD6BB1831B.json": 2999,
    "M_fx_endminm_gfx_43_p73D80B62F5BA886F.json": 2999,
    "M_endminf_ui_overview_01_rock_03_p9EBBC39832869160.json": 3700,
}


def pptr_id(value: object) -> int:
    return int(value.get("m_PathID", 0)) if isinstance(value, dict) else 0


def fnv1_64(data: bytes) -> str:
    value = 0
    for byte in data:
        value = ((value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF) ^ byte
    return f"{value:016x}"


def main() -> int:
    failures: list[str] = []
    recovered_shader = RECOVERED_SHADER.read_text(encoding="utf-8")
    base_main_linear_clamp_tokens = (
        "#elif !defined(_SAMPLE_TEX0) && !defined(_SAMPLE_TEX1)",
        "!defined(_USE_SOFTBLEND)",
        "Exact BASE fragment 0001",
        "sampler_LinearClamp, uv, bias + _GlobalMipBias",
    )
    base_main_linear_clamp = all(
        token in recovered_shader for token in base_main_linear_clamp_tokens)
    if not base_main_linear_clamp:
        failures.append(
            "recovered no-keyword BASE MainTex path is not statically LinearClamp")
    m20_sampler_tokens = (
        "Exact M20 fragments 0877/4951 bind Main t1",
        "sampler_LinearRepeat, uv, bias + _GlobalMipBias",
        "Exact M20 fragments 0877/4951 bind Sample0 t2",
        "sampler_LinearMirror, uv, bias + _GlobalMipBias",
        "Exact M20 fragments 0877/4951 bind Sample1 t3",
        "sampler_LinearMirrorOnce, uv, bias + _GlobalMipBias",
        "Exact M20 fragments 0877/4951 use the static",
        "sampler_LinearClamp, particlePixelUV, 0.0",
    )
    m20_static_samplers = all(
        token in recovered_shader for token in m20_sampler_tokens)
    if not m20_static_samplers:
        failures.append(
            "recovered M20 path does not retain the exact 0877/4951 static sampler ABI")
    variant_sets: dict[tuple[str, ...], list[str]] = {}
    for path in sorted(VARIANTS.glob("*_dxbc_0.dxbc.metadata.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        local = tuple(k for k in meta.get("SourceCompiledKeywords", []) if k.startswith("_"))
        variant_sets.setdefault(local, []).append(path.name)
    evidence = []
    for name, (expected_hash, expected_keywords) in ROWS.items():
        path = MATERIALS / name
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        row = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        keywords = row.get("m_ValidKeywords", [])
        variants = variant_sets.get(tuple(keywords), [])
        checks = {
            "exists": path.is_file(), "sha256": actual_hash == expected_hash,
            "shaderPathId": pptr_id(row.get("m_Shader")) == SHADER_ID,
            "orderedKeywords": keywords == expected_keywords,
            "renderQueue": row.get("m_CustomRenderQueue") == QUEUE_OVERRIDES.get(name, 3000),
            "originalD3D11Variant": len(variants) == 2,
        }
        if not all(checks.values()): failures.append(name + ": " + ", ".join(k for k, ok in checks.items() if not ok))
        evidence.append({"material": name, "checks": checks, "keywords": keywords, "variantMetadata": variants})
    captured_pairs = []
    for vertex in sorted(VARIANTS.glob("*_endfield_dxbc_0.dxbc")):
        sidecar_index = int(vertex.name[:4])
        fragment = VARIANTS / f"{sidecar_index + 1:04d}_endfield_dxbc_1.dxbc"
        if (fragment.is_file() and
                fnv1_64(vertex.read_bytes()) == M14_CAPTURED_VERTEX_HASH and
                fnv1_64(fragment.read_bytes()) == M14_CAPTURED_FRAGMENT_HASH):
            metadata = json.loads(
                (VARIANTS / (vertex.name + ".metadata.json")).read_text(
                    encoding="utf-8"))
            captured_pairs.append({
                "sidecarIndex": sidecar_index,
                "vertex": vertex.name,
                "fragment": fragment.name,
                "keywords": metadata.get("SourceCompiledKeywords", []),
                "debugName": metadata.get("DebugName"),
            })
    expected_keywords = ["HG_ENABLE_MV", "SRP_INSTANCING_ON", "_USE_SOFTBLEND"]
    if (len(captured_pairs) != 1 or
            captured_pairs[0]["sidecarIndex"] != M14_CAPTURED_SIDECAR_INDEX or
            captured_pairs[0]["keywords"] != expected_keywords):
        failures.append(
            "M14 captured shader pair does not resolve uniquely to sidecar 4914/4915")
    m20_pairs = []
    for sidecar_index, (expected_vertex, expected_fragment) in M20_VARIANT_PAIRS.items():
        vertex = VARIANTS / f"{sidecar_index:04d}_endfield_dxbc_0.dxbc"
        fragment = VARIANTS / f"{sidecar_index + 1:04d}_endfield_dxbc_1.dxbc"
        metadata_path = VARIANTS / (vertex.name + ".metadata.json")
        checks = {
            "vertexExists": vertex.is_file(),
            "fragmentExists": fragment.is_file(),
            "metadataExists": metadata_path.is_file(),
            "vertexIdentity": vertex.is_file() and fnv1_64(vertex.read_bytes()) == expected_vertex,
            "fragmentIdentity": fragment.is_file() and fnv1_64(fragment.read_bytes()) == expected_fragment,
        }
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) \
            if metadata_path.is_file() else {}
        checks["keywords"] = [
            key for key in metadata.get("SourceCompiledKeywords", [])
            if key.startswith("_")
        ] == ["_SAMPLE_TEX0", "_SAMPLE_TEX1", "_USE_SOFTBLEND"]
        if not all(checks.values()):
            failures.append(
                f"M20 sidecar {sidecar_index}/{sidecar_index + 1}: " +
                ", ".join(key for key, ok in checks.items() if not ok))
        m20_pairs.append({
            "sidecarIndex": sidecar_index,
            "vertexUnseededFnv1": expected_vertex,
            "fragmentUnseededFnv1": expected_fragment,
            "keywords": metadata.get("SourceCompiledKeywords", []),
            "checks": checks,
        })

    report = {
        "schema": "endfield.endminf-basev2-admission.v1",
        "status": "validated" if not failures else "failed",
        "shaderPathId": SHADER_ID,
        "recoveredBaseMainLinearClamp": {
            "shader": str(RECOVERED_SHADER.relative_to(REPO)),
            "fragmentSidecar": 1,
            "validated": base_main_linear_clamp,
            "boundary": (
                "The installed BASE fragment binds static LinearClamp even when "
                "the source Texture2D is Repeat; Unity's paired sampler is not equivalent."
            ),
        },
        "materialCount": len(ROWS),
        "m14CapturedPair": {
            "frameAnalysisDraw": 115,
            "vertexUnseededFnv1": M14_CAPTURED_VERTEX_HASH,
            "fragmentUnseededFnv1": M14_CAPTURED_FRAGMENT_HASH,
            "matches": captured_pairs,
            "selectionBoundary": (
                "The captured SRP_INSTANCING_ON keyword selects a per-draw "
                "record. It is not Unity ParticleSystem procedural instancing."
            ),
        },
        "m20SourceCompiledPairs": {
            "pairs": m20_pairs,
            "staticSamplerTranslationValidated": m20_static_samplers,
            "samplerAbi": [
                "t0 SceneDepth / s0 LinearClamp",
                "t1 MainTex / s1 LinearRepeat",
                "t2 SampleTex0 / s2 LinearMirror",
                "t3 SampleTex1 / s3 LinearMirrorOnce",
            ],
            "boundary": (
                "The source-compiled variants prove the static sampler ABI. "
                "The next automatic runtime capture must still identify the live route."
            ),
        },
        "evidence": evidence,
        "failures": failures,
    }
    output = REPO / "reports/assets/endminf_basev2_admission.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Endminf BaseV2 admission: {report['status']}; materials={len(ROWS)}; failures={len(failures)}")
    print(output.relative_to(REPO))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
