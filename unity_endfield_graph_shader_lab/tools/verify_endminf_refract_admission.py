#!/usr/bin/env python3
"""Fail-closed exact-program gate for Endminf M28 VFXRefract.

The selected shader has two D3D11 ``HG_ENABLE_MV + _USE_DISSOLVE`` pairs:
0090/0091 without SRP instancing and 0624/0625 with SRP instancing. This
verifier pins all four containers, derives their stages and signatures from
DXBC, and checks Microsoft's complete normalized DXBC disassembly stream.

Program recovery and Unity admission are deliberately separate. ``--program-
only`` succeeds once the original pair contract is exact. The default mode
also audits the current Unity consumer and returns nonzero until every source,
binding, and equation gate is closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
BYTECODE_ROOT = (
    ROOT
    / "scratch/character_recovery/vfx_shader_variants/shader_export/Shader"
    / "HGRP_Effect_VFXRefract_p6BC753C54B47D1ED.shader.bytecode"
)
SOURCE_SHADER = BYTECODE_ROOT.parent / "HGRP_Effect_VFXRefract_p6BC753C54B47D1ED.shader"
SOURCE_MATERIAL = (
    ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material"
    / "M_fx_endminm_gfx_28_pBF7FEE87831B48FB.json"
)
UNITY_MATERIAL = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated"
    / "Characters/Playable/Endminf/Effects/Overview/Materials"
    / "M_fx_endminm_gfx_28_pBF7FEE87831B48FB.mat"
)
RECOVERED_SHADER = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Shaders/Recovered"
    / "EndfieldZhuangfyVFXRefractMRT.shader"
)
REPORT = ROOT / "reports/assets/character_recovery/endminf_m28_refract_program.json"

SHADER_PATH_ID = 7766268189260370413
SOURCE_MATERIAL_SHA256 = "51ae58da347abf62408380255d2abc290145642736094dedd121dc2ac8081d80"
SOURCE_SHADER_SHA256 = "2844fb198fae3c872afbffdb8575543d924cb597c597f60cd406f4f81627d82b"
UNITY_MATERIAL_SHA256 = "802d654056083863cc9d8178fa306228892bcc87e063cae4a1550285c781250c"

PROGRAMS = {
    "0090_endfield_dxbc_0.dxbc": {
        "stage": "vertex", "bytes": 5388,
        "sha256": "a88a2a22943a5db135230f01b36cf83e2219a0afc626a1c820ddbe51b7dfb798",
        "keywords": ["HG_ENABLE_MV", "_USE_DISSOLVE"],
        "normalizedDisassemblySha256": "ae5fc15717e57eaa7a6e38f4445b771f028bebeccda7781c152d4b6d950690e5",
        "constantBuffers": {0: (2, False), 1: (82, False), 2: (20, False), 3: (14, False), 4: (5, False)},
        "textures": {0: "structured:16"}, "samplers": [],
    },
    "0091_endfield_dxbc_1.dxbc": {
        "stage": "fragment", "bytes": 3592,
        "sha256": "8c449c9377e39f90af7dca4543c8be1dbd3a50c846df2015e54abaa6b6bfb241",
        "keywords": ["HG_ENABLE_MV", "_USE_DISSOLVE"],
        "normalizedDisassemblySha256": "daaeefe007f85b5d083528b7b0e9ff2497c5035784f7cc77920331296227b29e",
        "constantBuffers": {0: (28, False), 1: (104, False), 2: (5, False), 3: (11, False)},
        "textures": {0: "texture2d", 1: "texture2d", 2: "texture2d"}, "samplers": [0, 1, 2],
    },
    "0624_endfield_dxbc_0.dxbc": {
        "stage": "vertex", "bytes": 5756,
        "sha256": "7f5111cf80387beeac8aacb30aa7298d58af6d26a62c981a3e15ba9a1d7468ab",
        "keywords": ["HG_ENABLE_MV", "SRP_INSTANCING_ON", "_USE_DISSOLVE"],
        "normalizedDisassemblySha256": "41f8fefed18424cca59b2caf001bd026e302bcd3aaa6b3e528cb19ccd4eb05bb",
        "constantBuffers": {0: (2, False), 1: (82, False), 2: (20, False), 3: (4094, True), 4: (5, False)},
        "textures": {0: "structured:16"}, "samplers": [],
    },
    "0625_endfield_dxbc_1.dxbc": {
        "stage": "fragment", "bytes": 3664,
        "sha256": "a3c9bfc94f0caea930c20bd61ee49fdb95ab58ef1f2e7c64f0f19a74c7e1ea92",
        "keywords": ["HG_ENABLE_MV", "SRP_INSTANCING_ON", "_USE_DISSOLVE"],
        "normalizedDisassemblySha256": "4b7a5c1f1ce38f946e591353d56798dc5eba0ebad8175747fdd77b4974ca1300",
        "constantBuffers": {0: (28, False), 1: (104, False), 2: (4085, True), 3: (11, False)},
        "textures": {0: "texture2d", 1: "texture2d", 2: "texture2d"}, "samplers": [0, 1, 2],
    },
}

COMMON_VERTEX_INPUTS = [
    ("POSITION", 0, 0, 7, "float"), ("COLOR", 0, 1, 15, "float"),
    ("TEXCOORD", 0, 2, 15, "float"), ("TEXCOORD", 1, 3, 15, "float"),
    ("TEXCOORD", 4, 4, 15, "float"), ("BLENDWEIGHTS", 0, 5, 15, "float"),
    ("BLENDINDICES", 0, 6, 15, "uint"),
]
COMMON_VERTEX_OUTPUTS = [
    ("SV_Position", 0, 0, 15, "float"), ("TEXCOORD", 0, 1, 15, "float"),
    ("TEXCOORD", 1, 2, 15, "float"), ("TEXCOORD", 2, 3, 15, "float"),
    ("TEXCOORD", 3, 4, 7, "float"), ("TEXCOORD", 4, 5, 7, "float"),
]
COMMON_FRAGMENT_OUTPUTS = [
    ("SV_Target", 0, 0, 15, "float"), ("SV_Target", 1, 1, 15, "float"),
]
EXPECTED_SIGNATURES = {
    "0090_endfield_dxbc_0.dxbc": {"inputs": COMMON_VERTEX_INPUTS, "outputs": COMMON_VERTEX_OUTPUTS},
    "0091_endfield_dxbc_1.dxbc": {"inputs": COMMON_VERTEX_OUTPUTS, "outputs": COMMON_FRAGMENT_OUTPUTS},
    "0624_endfield_dxbc_0.dxbc": {
        "inputs": COMMON_VERTEX_INPUTS + [("SV_InstanceID", 0, 7, 1, "uint")],
        "outputs": COMMON_VERTEX_OUTPUTS + [("TEXCOORD", 5, 6, 1, "uint")],
    },
    "0625_endfield_dxbc_1.dxbc": {
        "inputs": COMMON_VERTEX_OUTPUTS + [("TEXCOORD", 5, 6, 1, "uint")],
        "outputs": COMMON_FRAGMENT_OUTPUTS,
    },
}


class VerificationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    require(len(data) >= 32 and data[:4] == b"DXBC", "not a DXBC container")
    count = struct.unpack_from("<I", data, 28)[0]
    table_end = 32 + count * 4
    require(table_end <= len(data), "DXBC chunk table exceeds container")
    result = []
    for offset in struct.unpack_from(f"<{count}I", data, 32):
        require(table_end <= offset <= len(data) - 8, "bad DXBC chunk offset")
        size = struct.unpack_from("<I", data, offset + 4)[0]
        end = offset + 8 + size
        require(end <= len(data), "DXBC chunk exceeds container")
        result.append((data[offset : offset + 4], data[offset + 8 : end]))
    return result


def signature(data: bytes, output: bool) -> list[tuple[str, int, int, int, str]]:
    wanted = (b"OSG1", b"OSGN") if output else (b"ISG1", b"ISGN")
    for fourcc, chunk in chunks(data):
        if fourcc not in wanted:
            continue
        count = struct.unpack_from("<I", chunk, 0)[0]
        record_size = 32 if fourcc.endswith(b"1") else 24
        rows = []
        for index in range(count):
            offset = 8 + index * record_size
            require(offset + 24 <= len(chunk), "short DXBC signature record")
            name_offset, semantic_index = struct.unpack_from("<II", chunk, offset)
            component_type = struct.unpack_from("<I", chunk, offset + 12)[0]
            register = struct.unpack_from("<I", chunk, offset + 16)[0]
            mask = chunk[offset + 20]
            require(name_offset < len(chunk), "bad DXBC signature semantic offset")
            name = chunk[name_offset:].split(b"\0", 1)[0].decode("ascii")
            rows.append((name, semantic_index, register, mask,
                         {1: "uint", 2: "sint", 3: "float"}.get(component_type, str(component_type))))
        return rows
    raise VerificationError("DXBC signature chunk missing")


def stage(data: bytes) -> str:
    for fourcc, chunk in chunks(data):
        if fourcc in (b"SHEX", b"SHDR"):
            require(len(chunk) >= 8, "short DXBC instruction chunk")
            program_type = struct.unpack_from("<I", chunk, 0)[0] >> 16
            require(program_type in (0, 1), f"unexpected DXBC program type {program_type}")
            return "fragment" if program_type == 0 else "vertex"
    raise VerificationError("DXBC instruction chunk missing")


def find_fxc() -> Path:
    direct = shutil.which("fxc.exe") or shutil.which("fxc")
    if direct:
        return Path(direct)
    kits = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    candidates = sorted(kits.glob("*/x64/fxc.exe"), reverse=True)
    if not candidates:
        raise VerificationError("fxc.exe is required to verify exact declaration/equation text")
    return candidates[0]


def disassemble(fxc: Path, source: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="endminf_m28_dxbc_") as temp:
        output = Path(temp) / "program.asm"
        result = subprocess.run(
            [str(fxc), "/dumpbin", "/nologo", "/Fc", str(output), str(source)],
            text=True, capture_output=True, check=False,
        )
        require(result.returncode == 0 and output.is_file(),
                f"fxc disassembly failed for {source.name}: {result.stderr.strip()}")
        return output.read_text(encoding="utf-8-sig")


def normalized_disassembly(text: str) -> str:
    lines = text.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line in ("vs_5_0", "ps_5_0"))
    except StopIteration as exc:
        raise VerificationError("fxc output has no shader-model line") from exc
    return "\n".join(
        line.strip() for line in lines[start:]
        if line.strip() and not line.strip().startswith("//")
    ) + "\n"


def declarations(text: str) -> dict[str, Any]:
    constant_buffers = {
        int(register): (int(size), "dynamicIndexed" in suffix)
        for register, size, suffix in re.findall(
            r"^dcl_constantbuffer CB(\d+)\[(\d+)\], ([^\r\n]+)$", text, re.MULTILINE
        )
    }
    textures: dict[int, str] = {}
    for register, stride in re.findall(r"^dcl_resource_structured t(\d+), (\d+)$", text, re.MULTILINE):
        textures[int(register)] = f"structured:{stride}"
    for register in re.findall(r"^dcl_resource_texture2d .* t(\d+)$", text, re.MULTILINE):
        textures[int(register)] = "texture2d"
    samplers = sorted(int(value) for value in re.findall(r"^dcl_sampler s(\d+),", text, re.MULTILINE))
    return {"constantBuffers": constant_buffers, "textures": textures, "samplers": samplers}


def metadata(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"bad metadata {path}: {exc}") from exc
    require(isinstance(value, dict), f"metadata is not an object: {path}")
    return value


def signature_json(rows: Iterable[tuple[str, int, int, int, str]]) -> list[dict[str, Any]]:
    return [
        {"semantic": name, "index": index, "register": register,
         "mask": mask, "components": mask.bit_count(), "componentType": component_type}
        for name, index, register, mask, component_type in rows
    ]


def verify_programs() -> tuple[list[dict[str, Any]], dict[str, str]]:
    fxc = find_fxc()
    require(SOURCE_SHADER.is_file(), f"missing exact source shader export: {SOURCE_SHADER}")
    require(sha256(SOURCE_SHADER) == SOURCE_SHADER_SHA256, "source ShaderLab export hash drift")
    rows = []
    assemblies: dict[str, str] = {}
    for name, expected in PROGRAMS.items():
        path = BYTECODE_ROOT / name
        meta_path = Path(str(path) + ".metadata.json")
        require(path.is_file() and meta_path.is_file(), f"missing exact sidecar pair member: {name}")
        data = path.read_bytes()
        require(len(data) == expected["bytes"], f"{name}: byte size drift")
        require(hashlib.sha256(data).hexdigest() == expected["sha256"], f"{name}: SHA-256 drift")
        actual_stage = stage(data)
        require(actual_stage == expected["stage"], f"{name}: DXBC stage drift")
        actual_inputs = signature(data, output=False)
        actual_outputs = signature(data, output=True)
        require(actual_inputs == EXPECTED_SIGNATURES[name]["inputs"], f"{name}: input signature drift")
        require(actual_outputs == EXPECTED_SIGNATURES[name]["outputs"], f"{name}: output signature drift")
        meta = metadata(meta_path)
        require(meta.get("SourcePassName") == "Refraction", f"{name}: pass drift")
        require(meta.get("SourceCompiledKeywords") == expected["keywords"], f"{name}: keyword drift")
        require(meta.get("DecodedProgramEncoding") == "DXBC", f"{name}: encoding drift")
        assembly = disassemble(fxc, path)
        normalized = normalized_disassembly(assembly)
        require(hashlib.sha256(normalized.encode()).hexdigest() == expected["normalizedDisassemblySha256"],
                f"{name}: normalized declaration/equation stream drift")
        actual_declarations = declarations(assembly)
        require(actual_declarations["constantBuffers"] == expected["constantBuffers"],
                f"{name}: constant-buffer declarations drift")
        require(actual_declarations["textures"] == expected["textures"], f"{name}: resource declarations drift")
        require(actual_declarations["samplers"] == expected["samplers"], f"{name}: sampler declarations drift")
        assemblies[name] = normalized
        rows.append({
            "file": relative(path), "metadata": relative(meta_path),
            "stageFromDxbc": actual_stage, "bytes": len(data), "sha256": expected["sha256"],
            "keywords": expected["keywords"], "inputs": signature_json(actual_inputs),
            "outputs": signature_json(actual_outputs),
            "chunks": [fourcc.decode("ascii") for fourcc, _ in chunks(data)],
            "hasRdef": any(fourcc == b"RDEF" for fourcc, _ in chunks(data)),
            "constantBuffers": [
                {"register": register, "float4Count": size, "bytes": size * 16, "dynamicIndexed": dynamic}
                for register, (size, dynamic) in sorted(actual_declarations["constantBuffers"].items())
            ],
            "resources": [{"register": register, "kind": kind}
                          for register, kind in sorted(actual_declarations["textures"].items())],
            "samplers": actual_declarations["samplers"],
            "normalizedDisassemblySha256": expected["normalizedDisassemblySha256"],
        })
    return rows, assemblies


def contains_in_order(text: str, lines: list[str]) -> bool:
    cursor = 0
    for line in lines:
        next_cursor = text.find(line, cursor)
        if next_cursor < 0:
            return False
        cursor = next_cursor + len(line)
    return True


def verify_equations(assemblies: dict[str, str]) -> dict[str, Any]:
    fragment = assemblies["0091_endfield_dxbc_1.dxbc"]
    inst_fragment = assemblies["0625_endfield_dxbc_1.dxbc"]
    checks = {
        "refractUvUsesTimeAndCustom1X": contains_in_order(fragment, [
            "mad r0.xy, cb3[7].xyxx, cb1[103].wwww, v1.xyxx",
            "mad r0.xy, cb3[7].zwzz, v2.xxxx, r0.xyxx",
        ]),
        "refractRotationRepeatSample": contains_in_order(fragment, [
            "mul r0.z, l(0.017453), cb3[4].x", "sincos",
            "sample_b_indexable(texture2d)(float,float,float,float) r0.xyz, r0.xyxx, t0.xywz, s1, cb1[26].x",
        ]),
        "bidirectionalNormalDecode": contains_in_order(fragment, [
            "mad r0.w, r0.x, r0.w, -cb3[3].y", "mul r0.x, r0.w, r0.z",
            "mad r0.xy, r0.xyxx, l(2.000000, 2.000000", "mad r0.xy, cb3[2].zzzz, r0.xyxx, r0.zwzz",
        ]),
        "strengthUsesLodTintIntensityVertexAlpha": contains_in_order(fragment, [
            "mul r1.x, cb3[2].w, cb3[3].x", "add r1.y, l(1.000000), -cb2[4].y",
            "mul r1.x, r1.y, r1.x", "mul r1.x, r1.x, v3.w",
        ]),
        "dissolveUvUsesTimeOnly": contains_in_order(fragment, [
            "mad r0.zw, cb3[10].xxxy, cb1[103].wwww, v1.xxxy",
            "mul r1.x, l(0.017453), cb3[8].x",
            "sample_b_indexable(texture2d)(float,float,float,float) r0.z, r0.zwzz, t1.yzxw, s2, cb1[26].x",
        ]),
        "dissolveThresholdExact": contains_in_order(fragment, [
            "add r0.w, v2.z, cb3[8].y", "mad r0.w, r0.w, l(2.020000), l(-1.010000)",
            "add r0.z, -r0.w, r0.z", "mul_sat r0.z, r0.z, cb3[8].z",
        ]),
        "distortionSamplesSceneTarget0": contains_in_order(fragment, [
            "mul r1.xy, v0.xyxx, cb1[0].zwzz", "mad r0.xy, r0.xyxx, r0.zzzz, r1.xyxx",
            "sample_b_indexable(texture2d)(float,float,float,float) r0.xyw, r0.xyxx, t2.xywz, s0, cb1[26].x",
            "min o0.xyz, r0.xywx, l(1000.000000",
        ]),
        "nearFadeDepthReconstructionViewZ": contains_in_order(fragment, [
            "mad r1.xyzw, cb0[24].xyzw", "mad r1.xyzw, cb0[26].xyzw, v0.zzzz",
            "div r0.xyw, r1.xyxz, r1.wwww", "add r0.xy, |r0.xxxx|, -cb3[0].ywyy",
            "ne r0.y, l(0.000000), cb3[0].x", "mul_sat o0.w, r0.z, r0.x",
        ]),
        "sceneMvSignedFourthRoot": contains_in_order(fragment, [
            "div r0.xy, v4.xyxx, r0.xxxx", "div r0.zw, v5.xxxy, r0.zzzz",
            "sqrt r0.xy, |r0.xyxx|", "sqrt r0.xy, r0.xyxx",
            "add_sat r0.z, r0.z, -cb3[2].x", "min o1.xy, r0.xyxx, l(1.000000, 1.000000",
            "mov o1.zw, l(0,0,1.000000,0)",
        ]),
        "instancedLodUsesForwardedInstanceId": contains_in_order(inst_fragment, [
            "dcl_input_ps constant v6.x", "ishl r1.x, v6.x, l(4)",
            "add r1.x, l(1.000000), -cb2[r1.x + 4].y",
        ]),
    }
    require(all(checks.values()), "one or more exact fragment equation assertions failed")
    return {
        "status": "validated_exact_fragment_equations", "checks": checks,
        "textureBindings": [
            {"register": "t0", "logicalName": "_RefractTex", "sampler": "s1 LinearRepeat"},
            {"register": "t1", "logicalName": "_DissolveTex", "sampler": "s2 LinearMirror"},
            {"register": "t2", "logicalName": "_SceneColorTexture", "sampler": "s0 LinearClamp"},
        ],
        "fragmentConstantBufferLanes": {
            "b0": "transform/view data; c24-c27 inverse-view-projection reconstruction and c0-c3 view-Z row",
            "b1": "global frame data; c0.zw inverse screen size, c26.x global mip bias, c103.w VFX time",
            "b2": "per-draw LOD; non-instanced c4.y or instanced c[SV_InstanceID*16+4].y",
            "b3": {
                "c0": ["_UseNearCameraFade", "_NearCameraFadeDistanceStart", "_NearCameraFadeDistanceEnd", "_NearCameraFadeDistanceStart2"],
                "c1.x": "_NearCameraFadeDistanceEnd2",
                "c2": ["_SurfaceType", "_EnableTransparentMV", "_RefractIsNormal", "_TintColorAlpha"],
                "c3.xy": ["_Intensity", "_Bi_Refract"], "c4.x": "_RefractTexUVRotate",
                "c5.xy": "_RefractDir.xy", "c6": "_RefractTex_ST", "c7": "_RefractUVSpeed",
                "c8": ["_DissolveUVRotate", "_DissolveScheduleOffset", "_DissolveEdgeSharp", "_DissolveAffectBlend"],
                "c9": "_DissolveTex_ST",
                "c10.xy": "_DissolveUVSpeed.xy; zw is not read by this selected variant",
            },
        },
        "outputEquation": {
            "SV_Target0": "clamped scene color sampled at screenUV + lerp(fixed refraction, decoded normal, raw RefractIsNormal) * LOD/tint/intensity/particle-alpha strength * dissolve; saturated dissolve/near-fade alpha",
            "SV_Target1": "signed fourth-root current-minus-previous NDC motion encoded to [0,1], scaled by saturate(1 + EnableTransparentMV - SurfaceType), z=1, w=0",
        },
    }


def audit_recovered_shader() -> dict[str, Any]:
    require(UNITY_MATERIAL.is_file(), f"missing retained Unity M28 material: {UNITY_MATERIAL}")
    require(sha256(UNITY_MATERIAL) == UNITY_MATERIAL_SHA256, "retained Unity M28 material hash drift")
    require(RECOVERED_SHADER.is_file(), f"missing recovered Unity shader: {RECOVERED_SHADER}")
    text = RECOVERED_SHADER.read_text(encoding="utf-8")
    gaps = []
    if "float4 uv0 : TEXCOORD0;" in text and "BLENDWEIGHTS" not in text:
        gaps.append({"gate": "vertex input/publisher parity",
                     "exact": "POSITION/COLOR/TEXCOORD0/TEXCOORD1/TEXCOORD4/BLENDWEIGHTS/BLENDINDICES; instanced also SV_InstanceID",
                     "current": "public Unity particle-instancing include and reduced source struct; no exact BLEND/TEXCOORD4 publisher"})
    if "UnityObjectToClipPos(input.vertex)" in text:
        gaps.append({"gate": "vertex transform and motion parity",
                     "exact": "optional VertexSkinMatrices branch, current/previous object transforms, camera-relative offset, non-jittered clip outputs",
                     "current": "UnityObjectToClipPos plus ComputeScreenPos"})
    if "saturate(_RefractIsNormal)" in text:
        gaps.append({"gate": "normal-selector equation parity", "exact": "lerp with raw b3.c2.z",
                     "current": "saturates RefractIsNormal", "m28FixedValue": 0.0})
    if "_DissolveUVSpeed.zw * input.custom.y" in text:
        gaps.append({"gate": "dissolve UV equation parity",
                     "exact": "uv + DissolveUVSpeed.xy*time; no speed.zw/Custom1.y read",
                     "current": "adds speed.zw*Custom1.y", "m28FixedSpeedZw": [0.0, 0.0]})
    if "DistanceFade(distance(_WorldSpaceCameraPos, input.positionWS))" in text:
        gaps.append({"gate": "near-camera fade equation parity",
                     "exact": "depth reconstruction and absolute view-space Z", "current": "Euclidean world-space distance",
                     "m28FixedUseNearCameraFade": 0.0})
    if "output.sceneMV = float4(0.0, 0.0, 1.0, 0.0);" in text:
        gaps.append({"gate": "SceneMV equation parity", "exact": "signed fourth-root current/previous NDC motion",
                     "current": "hard-coded zero XY", "m28FixedSurfaceAndEnable": [1.0, 0.0]})
    require(gaps, "recovered shader unexpectedly appears exact; extend verifier before admission")
    source_present = SOURCE_MATERIAL.is_file()
    source_hash = sha256(SOURCE_MATERIAL) if source_present else None
    source_identity = False
    if source_present and source_hash == SOURCE_MATERIAL_SHA256:
        row = json.loads(SOURCE_MATERIAL.read_text(encoding="utf-8"))
        source_identity = (row.get("m_Shader", {}).get("m_PathID") == SHADER_PATH_ID
                           and row.get("m_ValidKeywords") == ["_USE_DISSOLVE"]
                           and row.get("m_CustomRenderQueue") == 3000)
    return {
        "path": relative(RECOVERED_SHADER), "sha256": sha256(RECOVERED_SHADER),
        "equationParity": False, "gaps": gaps,
        "sourceMaterial": {"path": relative(SOURCE_MATERIAL), "present": source_present,
                           "expectedSha256": SOURCE_MATERIAL_SHA256, "actualSha256": source_hash,
                           "identityValidated": source_identity},
        "admissionReady": False,
        "reason": "Exact original programs are closed, but Unity vertex/publisher and source equations are not bytecode-equivalent; material-fixed zeros do not prove the general program or engine IA contract.",
    }


def main(program_only: bool, output: Path) -> int:
    programs, assemblies = verify_programs()
    equations = verify_equations(assemblies)
    recovered = audit_recovered_shader()
    report = {
        "schema": "endfield.endminf-m28-refract-program.v2",
        "status": "exact_program_pairs_validated_unity_admission_fail_closed",
        "shader": {"name": "HGRP/Effect/VFXRefract", "pathId": SHADER_PATH_ID,
                   "pass": "Refraction", "lightMode": "Distortion"},
        "sourceShader": {"path": relative(SOURCE_SHADER), "sha256": SOURCE_SHADER_SHA256},
        "pairs": [
            {"name": "non_instanced", "vertex": "0090_endfield_dxbc_0.dxbc", "fragment": "0091_endfield_dxbc_1.dxbc",
             "keywords": ["HG_ENABLE_MV", "_USE_DISSOLVE"],
             "selectionBoundary": "complete exact pair; no M28 retail draw capture proves this pair was selected"},
            {"name": "srp_instanced", "vertex": "0624_endfield_dxbc_0.dxbc", "fragment": "0625_endfield_dxbc_1.dxbc",
             "keywords": ["HG_ENABLE_MV", "SRP_INSTANCING_ON", "_USE_DISSOLVE"],
             "selectionBoundary": "complete exact pair; renderer GPU-instancing state alone does not prove SRP_INSTANCING_ON"},
        ],
        "programs": programs,
        "vertexResourceContract": {
            "t0": "StructuredBuffer stride 16; serialized descriptor name _VertexSkinMatrices",
            "nonInstanced": "b0[2], b1[82], b2[20], b3[14], b4[5]",
            "instanced": "same except b3[4094] dynamically indexed at SV_InstanceID*16",
            "dataflow": "optional BLEND matrix path, TEXCOORD4 alternate previous position, current/previous clip and SceneMV carriers",
        },
        "fragmentContract": equations,
        "crossPairDifference": {
            "vertex": "0624 adds SV_InstanceID, indexes b3 at instance*16, and forwards TEXCOORD5",
            "fragment": "0625 receives constant TEXCOORD5 and indexes LOD b2 at instance*16+4; remaining two-MRT equation matches 0091",
        },
        "runtimePrerequisites": [
            {
                "gate": "selected pair",
                "required": "D3D11 draw-state evidence selecting exactly 0090/0091 or 0624/0625; renderer enableGPUInstancing is not shader-keyword proof",
            },
            {
                "gate": "vertex input assembler and publisher",
                "required": "POSITION float3, COLOR float4, TEXCOORD0/1/4 float4, BLENDWEIGHTS float4, BLENDINDICES uint4; instanced path also SV_InstanceID and its exact per-instance base",
            },
            {
                "gate": "vertex resources",
                "required": "t0 StructuredBuffer stride 16 (_VertexSkinMatrices) plus exact b0-b4 uploads; the instanced path must publish the 16-float4 b3 record selected by SV_InstanceID",
            },
            {
                "gate": "fragment frame resources",
                "required": "b0 view/inverse-view-projection, b1 ScreenSize.zw/GlobalMipBias/VFXParams0.w, b2 LOD fade (per instance for 0625), and exact b3 material lane upload",
            },
            {
                "gate": "fragment textures and samplers",
                "required": "t0 RefractTex with s1 LinearRepeat, t1 DissolveTex with s2 LinearMirror, t2 pre-distortion SceneColor with s0 LinearClamp",
            },
            {
                "gate": "attachments and PSO",
                "required": "two bound color attachments accepting Target0 scene color and Target1 SceneMV, valid fragment depth for inverse-projection fade, and exact serialized target blend/depth/cull state",
            },
        ],
        "remainingGates": [
            "re-extract and hash/identity-check the exact M28 AnimeStudio Material JSON",
            "capture or otherwise prove which complete pair the retail M28 draw selects",
            "recover the engine-generated TEXCOORD4/BLEND/instance publisher and every vertex constant/resource upload",
            "make the Unity shader equations match the exact vertex and fragment programs rather than relying on M28 fixed zeros",
            "validate both M28 consumers at 60 Hz only after the program and renderer tuples are admitted",
        ],
        "bindingEvidenceBoundary": {
            "physical": "all signatures, registers, array sizes, dynamic indexing, resources, samplers, outputs, and instruction equations are exact from four hash-pinned DXBC containers",
            "logical": "common buffer fields and SceneColor come from serialized Shader metadata; material/texture aliases are assigned only where the selected property contract and exact equation make the role unique",
            "unproven": "DXBC has no RDEF, so this report does not claim a captured live descriptor table, upload producer, input publisher, or selected M28 draw variant",
        },
        "currentUnityConsumer": recovered,
        "admissionDecision": {"admitted": False, "programEvidenceComplete": True,
                              "reason": "Fail closed: actual pair selection, retail vertex publisher, current source material, and recovered-shader parity are not all closed."},
        "protectedControls": {
            "overview_02/all/shitou (1)": "M21 exact small crystal; not read or modified",
            "overview_02/all/suikuai (1)": "admitted exact refract shards; shared shader not modified",
            "overview_02/all/suikuai (2)": "M27 LitEffect; not read or modified",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"M28 exact VFXRefract pairs: validated; report={output}")
    print("Unity admission: fail closed (equation/publisher/source gates remain)")
    return 0 if program_only else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-only", action="store_true",
                        help="succeed after exact pair recovery; still report Unity admission gaps")
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args()
    try:
        raise SystemExit(main(args.program_only, args.output))
    except VerificationError as exc:
        print(f"M28 VFXRefract verification failed: {exc}")
        raise SystemExit(2)
