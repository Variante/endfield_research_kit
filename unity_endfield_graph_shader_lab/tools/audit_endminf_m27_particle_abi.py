#!/usr/bin/env python3
"""Audit the captured M27 LitEffect particle and SRP per-draw ABI.

This verifier is intentionally fail closed. It distinguishes Endfield's
engine-expanded particle geometry from UnityStandardParticleInstancing and
does not admit the renderer until active constant-buffer ranges and the
five-MRT deferred publication path are recovered.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
UNITY = REPO / "unity_endfield_graph_shader_lab"
SOURCE_CONTRACT = REPO / "reports/assets/character_recovery/endminf_m27_suikuai_source_contract.json"
PROGRAM_CONTRACT = REPO / "reports/assets/character_recovery/endminf_m27_liteffect_program_recovery.json"
CAPTURE_CONTRACT = REPO / "reports/assets/character_recovery/endminf_deferred_pass0_frame_analysis.json"
UNITY_PROBE = REPO / "reports/assets/character_recovery/endminf_m27_particle_abi_unity_probe.json"
RESOURCE_MAPPING = (
    UNITY
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/ExternalUiEffects/"
    "endminf_liteffect_resource_mapping.json"
)
BYTECODE_ROOT = (
    REPO
    / "scratch/animestudio/endminf_liteffect_shader/sidecars/Shader/"
    "HGRP_LitEffect_p5936F49FA93F14DD.shader.bytecode"
)
VERTEX_DXBC = BYTECODE_ROOT / "0678_endfield_dxbc_0.dxbc"
FRAGMENT_DXBC = BYTECODE_ROOT / "0679_endfield_dxbc_1.dxbc"
UNITY_PARTICLE_INCLUDE = Path(
    "D:/Program Files/2022.3.62f3/Editor/Data/CGIncludes/"
    "UnityStandardParticleInstancing.cginc"
)
OUTPUT = REPO / "reports/assets/character_recovery/endminf_m27_particle_abi.json"

EXPECTED = {
    "vertex_dxbc": "c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c",
    "fragment_dxbc": "92d80a93add9c714daeb265a66d3fe6e841c32825728d6af4268cede13c0c44e",
    "vertex_asm": "541a0c7c4a876e4cf1966ba0e8a59aede16b3ef9fe7a2f2910ca5e9858649e0d",
    "fragment_asm": "1f7acf87b70bc26555dee6dcde157274ac230402cb5d43951a503fece8ab45f7",
    "unity_particle_include": "19ca894b59456951060791e3f79884aab16e4a7ffd64baf028a7389411c51c0f",
    "mesh_json": "55dd5a73380a0b64b8fc173cb636f58b0178e377e7fd4445362a4a6c0de2f58d",
    "particle_raw": "8954241756066faa9de14c4d73da702c7adf07037346fd743ce5f6625730efd5",
    "renderer_raw": "9d782b66bb7bf6375ddf80ab9c776c35bb0718af154c41a574b1c29be98aae9c",
}


class AuditError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read {path}: {exc}") from exc


def sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise AuditError(f"cannot hash {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def find_fxc() -> Path:
    direct = shutil.which("fxc.exe") or shutil.which("fxc")
    if direct:
        return Path(direct)
    kits = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    candidates = sorted(kits.glob("*/x64/fxc.exe"), reverse=True)
    if not candidates:
        raise AuditError("fxc.exe is required to verify the captured DXBC equations")
    return candidates[0]


def disassemble(fxc: Path, source: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="endminf_m27_dxbc_") as temp:
        output = Path(temp) / "program.asm"
        result = subprocess.run(
            [str(fxc), "/dumpbin", "/nologo", "/Fc", str(output), str(source)],
            text=True, capture_output=True, check=False,
        )
        require(
            result.returncode == 0 and output.is_file(),
            f"fxc disassembly failed for {source.name}: {result.stderr.strip()}",
        )
        return output.read_text(encoding="utf-8-sig")


def normalized_disassembly(text: str) -> str:
    lines = text.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line in ("vs_5_0", "ps_5_0"))
    except StopIteration as exc:
        raise AuditError("fxc output has no shader-model line") from exc
    return "\n".join(
        line.strip() for line in lines[start:]
        if line.strip() and not line.strip().startswith("//")
    ) + "\n"


def require_markers(text: str, markers: tuple[str, ...], label: str) -> None:
    missing = [marker for marker in markers if marker not in text]
    require(not missing, f"{label} disassembly markers drifted: {missing}")


def validate_programs() -> dict[str, Any]:
    fxc = find_fxc()
    rows = []
    assemblies: dict[str, str] = {}
    for stage, path in (("vertex", VERTEX_DXBC), ("fragment", FRAGMENT_DXBC)):
        expected_hash = EXPECTED[f"{stage}_dxbc"]
        require(sha256(path) == expected_hash, f"captured {stage} DXBC hash drifted")
        metadata = load_json(path.with_name(path.name + ".metadata.json"))
        require(metadata.get("SourcePassName") == "HGBuffer", f"{stage} pass drifted")
        require(metadata.get("SourceSubProgramIndex") == 113, f"{stage} subprogram drifted")
        require(metadata.get("DecodedProgramStage") == stage, f"{stage} decoded stage drifted")
        require(
            metadata.get("SourceCompiledKeywords") ==
            ["HG_ENABLE_MV", "SRP_INSTANCING_ON", "_PARALLAX_MAP"],
            f"{stage} keyword set drifted",
        )
        assembly = normalized_disassembly(disassemble(fxc, path))
        require(
            hashlib.sha256(assembly.encode()).hexdigest() == EXPECTED[f"{stage}_asm"],
            f"captured {stage} normalized DXBC disassembly drifted",
        )
        assemblies[stage] = assembly
        rows.append({
            "stage": stage,
            "path": relative(path),
            "bytes": path.stat().st_size,
            "sha256": expected_hash,
            "normalizedDisassemblySha256": EXPECTED[f"{stage}_asm"],
        })

    vertex = assemblies["vertex"]
    fragment = assemblies["fragment"]
    require_markers(vertex, (
        "dcl_constantbuffer CB2[4091], dynamicIndexed",
        "dcl_resource_structured t0, 16",
        "dcl_input_sgv v9.x, instance_id",
        "ishl r1.z, v9.x, l(4)",
        "and r2.xy, l(32, -49, 0, 0), cb2[r1.z + 4].wwww",
        "iadd r2.xz, l(3, 0, 3, 0), cb2[r1.z + 5].xxyx",
        "mov o7.x, v9.x",
    ), "vertex")
    require_markers(fragment, (
        "dcl_constantbuffer CB2[4085], dynamicIndexed",
        "dcl_input_ps constant v7.x",
        "ishl r1.y, v7.x, l(4)",
        "add r1.z, cb2[r1.y + 3].y, cb2[r1.y + 3].x",
        "ishl r0.y, v7.x, l(4)",
        "max r0.y, cb2[r0.y + 4].z, cb2[r0.y + 4].y",
    ), "fragment")
    require(len(re.findall(r"^ld_structured_indexable", vertex, re.MULTILINE)) == 30,
            "captured vertex t0 load count drifted")
    return {
        "programs": rows,
        "instanceRecordFloat4Count": 16,
        "instanceRecordBytes": 256,
        "instanceCapacity": 256,
        "vertexDynamicCbuffer": "b2[4091]",
        "fragmentDynamicCbuffer": "b2[4085]",
        "vertexSkinBuffer": "t0 structured stride 16 (_VertexSkinMatrices)",
        "instanceIndexPath": "SV_InstanceID << 4; vertex forwards the same uint through TEXCOORD7",
    }


def validate_capture(capture: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    require(capture.get("status") == "ok", "deferred frame-analysis report is not current")
    selected = capture.get("litEffectInstancedParallax", {})
    require(selected.get("subProgramIndex") == 113, "captured LitEffect subprogram drifted")
    topology = selected.get("drawTopology", {})
    require(topology.get("instanceCount") == 1, "captured LitEffect instance count drifted")
    require(topology.get("startInstanceLocation") == 0, "captured LitEffect start instance drifted")
    require(topology.get("sourceRockIndexCount") == source["mesh"]["indexCount"] == 72,
            "captured/source rock index count drifted")
    copies = topology.get("expandedMeshCopiesByCapture", {})
    require(copies.get("FrameAnalysis-2026-08-24-182850") == 15,
            "late captured expanded-mesh count drifted")
    require(source["particleSystem"]["burst"]["count"] == 15.0,
            "M27 source burst count drifted")
    return {
        "report": relative(CAPTURE_CONTRACT),
        "selectedSubProgram": 113,
        "allDrawsInstanceCount": 1,
        "allDrawsStartInstanceLocation": 0,
        "sourceMeshIndexCount": 72,
        "lateCaptureIndexCount": 1080,
        "lateCaptureExpandedCopies": 15,
        "sourceBurstCount": 15,
        "equation": "1080 indices = 15 authored particles * 72 source-mesh indices",
        "conclusion": (
            "The retail particle publisher expands mesh copies into the dynamic "
            "vertex/index stream. SRP_INSTANCING_ON selects per-draw record 0; "
            "it is not evidence for UnityStandardParticleInstancing."
        ),
    }


def main(output: Path, unity_particle_include: Path) -> dict[str, Any]:
    source = load_json(SOURCE_CONTRACT)
    representative_program = load_json(PROGRAM_CONTRACT)
    capture = load_json(CAPTURE_CONTRACT)
    unity_probe = load_json(UNITY_PROBE)
    mapping = load_json(RESOURCE_MAPPING)

    require(source["mesh"]["json"]["sha256"] == EXPECTED["mesh_json"], "M27 mesh JSON hash drifted")
    require(source["particleSystem"]["rawDataSha256"] == EXPECTED["particle_raw"], "M27 particle raw hash drifted")
    require(source["renderer"]["rawDataSha256"] == EXPECTED["renderer_raw"], "M27 renderer raw hash drifted")
    require(unity_probe.get("status") == "ok" and unity_probe.get("unityVersion") == "2022.3.62f3",
            "current Unity M27 probe did not pass")
    require(mapping.get("bindChannels", {}).get("status") == "gap",
            "ParserBindChannels gap unexpectedly changed")
    require(representative_program["selectedProgram"]["compiledKeywords"] ==
            ["HG_ENABLE_MV", "_PARALLAX_MAP"],
            "non-instanced representative program drifted")

    expected_streams = ["Position", "Normal", "Color", "UV", "UV2", "Custom1XYZW"]
    require(source["renderer"]["customVertexStreams"]["names"] == expected_streams,
            "serialized M27 streams drifted")
    require(unity_probe["activeVertexStreams"] == expected_streams,
            "current Unity active M27 streams drifted")
    require(unity_probe["enableGPUInstancing"] is True, "current Unity lost M27 source flag")
    require(unity_probe["rendererEnabled"] is False and
            unity_probe["retainedMaterialCount"] == 0 and
            unity_probe["retainedMeshAssigned"] is False,
            "M27 fail-closed Unity boundary drifted")
    require(unity_probe["exactMeshBoneWeightCount"] == 0 and
            unity_probe["exactMeshBindPoseCount"] == 0 and
            unity_probe["exactMeshBonesPerVertexInfluenceSum"] == 0,
            "M27 source mesh unexpectedly contains skinning")

    include_hash = sha256(unity_particle_include)
    require(include_hash == EXPECTED["unity_particle_include"], "Unity particle include hash drifted")
    include = unity_particle_include.read_text(encoding="utf-8")
    for marker in (
        "struct DefaultParticleInstanceData",
        "float3x4 transform;",
        "StructuredBuffer<UNITY_PARTICLE_INSTANCE_DATA> unity_ParticleInstanceData;",
        "UNITY_PROCEDURAL_INSTANCING_ENABLED",
    ):
        require(marker in include, f"Unity standard particle ABI drifted: {marker}")

    programs = validate_programs()
    captured_topology = validate_capture(capture, source)
    report = {
        "schema": "endfield.endminf-m27-particle-abi.v2",
        "status": "fail_closed_active_cb_ranges_and_deferred_publication_unresolved",
        "scope": "P_fxui_endminm003_overview_02/all/suikuai (2) only",
        "selectedRetailProgram": {
            "shader": "HGRP/LitEffect",
            "pass": "HGBuffer",
            "subProgramIndex": 113,
            "compiledKeywords": ["HG_ENABLE_MV", "SRP_INSTANCING_ON", "_PARALLAX_MAP"],
            **programs,
        },
        "capturedParticlePublication": captured_topology,
        "exactSerializedConsumer": {
            "particlePathId": source["particleSystem"]["pathId"],
            "particleRawSha256": source["particleSystem"]["rawDataSha256"],
            "rendererPathId": source["renderer"]["pathId"],
            "rendererRawSha256": source["renderer"]["rawDataSha256"],
            "renderMode": source["renderer"]["renderMode"]["name"],
            "enableGPUInstancingSerialized": True,
            "activeVertexStreams": expected_streams,
            "meshPathId": source["mesh"]["pathId"],
            "meshJsonSha256": source["mesh"]["json"]["sha256"],
            "meshVertexCount": source["mesh"]["vertexCount"],
            "meshIndexCount": source["mesh"]["indexCount"],
            "meshSkinRows": 0,
        },
        "currentUnityProbe": {
            "path": relative(UNITY_PROBE),
            "unityVersion": unity_probe["unityVersion"],
            "status": "renderer remains disabled with no material or mesh binding",
            "standardParticleInstancingInclude": {
                "path": str(unity_particle_include.resolve()),
                "sha256": include_hash,
                "contract": "procedural float3x4 transform/color/animation-frame buffer",
                "retailMismatch": (
                    "Retail submits one instance and expanded particle geometry, "
                    "then indexes a 256-byte SRP per-draw record."
                ),
            },
        },
        "closedConclusions": [
            "The selected retail pair is subprogram 113, not representative non-instanced subprogram 19.",
            "Every selected draw uses InstanceCount 1 and StartInstanceLocation 0.",
            "The 1080-index late draw is exactly the authored 15-particle burst expanded from the 72-index source mesh.",
            "UnityStandardParticleInstancing is not the retail transport and must not be enabled for this compatibility shader.",
            "BLEND inputs remain the optional _VertexSkinMatrices path; the unskinned source mesh does not author those values.",
        ],
        "remainingBlockers": [
            {
                "gate": "active constant-buffer ranges",
                "gap": (
                    "The five frames dump whole 4 MiB ring allocations but log pointer "
                    "addresses rather than numeric pFirstConstant/pNumConstants values. "
                    "The active b2 record-0 bytes and material/global slices are not isolated."
                ),
                "required": "one range-logging frame at the M27 15-particle late window",
            },
            {
                "gate": "optional skin branch and generated auxiliary stream",
                "gap": (
                    "The captured input layout closes physical slots, including the "
                    "20-byte stride-zero BLEND/TANGENT buffer, but the active b2 flags "
                    "that decide whether t0 is read remain outside the unresolved range."
                ),
                "required": "decode b2 record 0 and t0 only if the bit-5 skin gate is active",
            },
            {
                "gate": "exact deferred publication",
                "gap": (
                    "The current compatibility shader is a ForwardOnly approximation; "
                    "retail subprogram 113 writes five HGBuffer/SceneMV targets and depth."
                ),
                "required": "port the hash-pinned equations and publish the exact five-MRT contract",
            },
        ],
        "implementationDecision": {
            "admitted": False,
            "reason": (
                "Particle expansion and shader selection are closed, but numeric active "
                "constant ranges and the exact deferred target contract remain unresolved."
            ),
            "doNotUse": [
                "UnityStandardParticleInstancing procedural setup",
                "a guessed identity _VertexSkinMatrices buffer",
                "the ForwardOnly compatibility material as an exact renderer",
            ],
        },
        "protectedBoundary": (
            "M21 overview_02/all/shitou (1) and M28 overview renderers were not "
            "modified or used as M27 substitutes."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--unity-particle-include", type=Path, default=UNITY_PARTICLE_INCLUDE)
    args = parser.parse_args()
    result = main(args.output, args.unity_particle_include)
    print(f"validated Endminf M27 captured particle ABI boundary: {args.output}")
    print(result["status"])
