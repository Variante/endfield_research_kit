#!/usr/bin/env python3
"""Pin Li Zhiyan's three exact material-selected VFXBaseV2 DXBC pairs."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
EFFECT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_finger_effect.json"
SOURCE = REPO / "export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type/Shader/HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader"
SOURCE_SHA256 = "F0E2D0C0B486621EC1B88D2B12D65AB07DD7C375CE53268116E8568DFFA903CD"
SIDECARS = REPO / "scratch/character_recovery/lizhiyan_persistent_vfxbasev2/Shader/HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader.bytecode"
HLSL_ROOT = REPO / "scratch/character_recovery/lizhiyan_persistent_vfxbasev2/selected_hlsl"
SHADER_CHUNK = Path(r"D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\0CE8FA57\36243F039A1BFD05676B5D323B50D4AA.chk")
SHADER_CHUNK_SHA256 = "BDB0DD43442A795FE67D0722667D0F3B9A33AFBD42BC477C5DA63CC4391CA556"
OUT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/LiZhiyanOverviewFinger"
CONTRACT = OUT / "lizhiyan_overview_vfxbasev2_variants.json"
SHADER_PATH_ID = -1430105248647086886
VARIANT_FILES = {
    "": {"slug": "base", "hlsl": "base", "vertex": "0000", "fragment": "0001"},
    "_USE_SOFTBLEND": {"slug": "use_softblend", "hlsl": "use_softblend", "vertex": "0846", "fragment": "0847"},
    "_SAMPLE_TEX0+_USE_SOFTBLEND": {
        "slug": "sample_tex0___use_softblend", "hlsl": "sample_tex0_use_softblend",
        "vertex": "0864", "fragment": "0865"
    },
}
RUNTIME_ROOT = (
    REPO / "tools/FractalMiner/Assets/Project/EndField/HGRP/packages/"
    "com.hg.render-pipelines/runtime/HG/Rendering/Runtime"
)
RUNTIME_SOURCES = {
    "ForwardPassUtils.cs": "6964668B3FF26E783F60241B243385B18154CEBFF465D2FACA5A3EC331F6360F",
    "TransparentAfterDOFPassConstructor.cs": "C183F3F41443491319AA99D5EAF87ED9FE5014EA1B5DD13FD0161703462E97F0",
    "HGRenderQueue.cs": "320D0445EB16D11104FA4ACAF96BF04303F29CFBEA8808BEAECA953D91B8B047",
}


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def signature(values: list[str]) -> str:
    return "+".join(sorted(values))


def copy_artifact(source: Path, name: str) -> dict[str, Any]:
    target = OUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return {
        "path": target.resolve().relative_to(REPO.resolve()).as_posix(),
        "bytes": target.stat().st_size,
        "sha256": sha256(target),
    }


def hlsl_signature(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="strict")
    resources = [
        {"kind": kind, "name": name, "register": register}
        for kind, name, register in re.findall(
            r"^(Texture\w*<[^>]+>|SamplerState)\s+(\w+)\s*:\s*register\(([^)]+)\);",
            text,
            re.MULTILINE,
        )
    ]
    cbuffers = [
        {"name": name, "register": register}
        for name, register in re.findall(
            r"^cbuffer\s+(\w+)\s*:\s*register\(([^)]+)\)", text, re.MULTILINE
        )
    ]
    return {
        "resources": resources,
        "constantBuffers": cbuffers,
        "sampleCalls": len(re.findall(r"\.Sample(?:Bias|Level|Grad)?\(", text)),
        "outputs": sorted(set(re.findall(r"SV_Target(?:_\d+)?", text))),
        "hasDiscard": bool(re.search(r"\b(?:discard|clip)\b", text)),
    }


def main() -> int:
    require(sha256(SOURCE) == SOURCE_SHA256, "Persistent VFXBaseV2 shader export drifted")
    require(sha256(SHADER_CHUNK) == SHADER_CHUNK_SHA256, "Persistent shader CHK drifted")
    shader_text = SOURCE.read_text(encoding="utf-8-sig", errors="strict")
    require('Name "ForwardOnly"' in shader_text and "GpuProgramID 59433" in shader_text,
            "Persistent VFXBaseV2 pass identity drifted")
    metadata_census: Counter[tuple[str, str]] = Counter()
    for path in SIDECARS.glob("*_endfield_dxbc_*.dxbc.metadata.json"):
        row = load(path)
        metadata_census[(signature(row.get("SourceCompiledKeywords") or []),
                         str(row.get("DecodedProgramStage") or ""))] += 1
    require(len(metadata_census) == 2720 and set(metadata_census.values()) == {1},
            "Persistent DXBC metadata uniqueness drifted")
    effect = load(EFFECT)
    require(effect.get("schema") == "endfield.lizhiyan-overview-finger-effect.v2", "effect schema drifted")
    require(effect["summary"]["materials"] == 6, "Li Zhiyan material census drifted")
    require({int(row["shaderPathID"]) for row in effect["materials"]} == {SHADER_PATH_ID}, "shader identity drifted")
    runtime_artifacts = []
    for name, expected in RUNTIME_SOURCES.items():
        path = RUNTIME_ROOT / name
        require(sha256(path) == expected, f"native render-path source drifted: {name}")
        runtime_artifacts.append({
            "path": path.resolve().relative_to(REPO.resolve()).as_posix(),
            "sha256": expected,
        })
    forward_text = (RUNTIME_ROOT / "ForwardPassUtils.cs").read_text(encoding="utf-8-sig")
    after_dof_text = (RUNTIME_ROOT / "TransparentAfterDOFPassConstructor.cs").read_text(encoding="utf-8-sig")
    queue_text = (RUNTIME_ROOT / "HGRenderQueue.cs").read_text(encoding="utf-8-sig")
    for token in (
        "k_RenderQueue_AfterPostProcessTransparent",
        "allTransparentPassAfterDOFNames",
        "PrepareAfterDOFTranparentRendererList",
    ):
        require(token in forward_text, f"after-DOF renderer-list token drifted: {token}")
    for token in (
        '"Forward Transparent After DOF"',
        "SetColorAttachment(",
        "&input.sceneMV,",
        "SetDepthAttachment(",
        "&input.sceneDepth,",
        "DepthAccess__Enum_Read,",
    ):
        require(token in after_dof_text, f"after-DOF attachment token drifted: {token}")
    require("AfterPostprocessTransparentFirst = 3660" in queue_text and
            "AfterPostprocessTransparentLast = 3740" in queue_text,
            "after-DOF queue interval drifted")

    materials_by_signature: dict[str, list[dict[str, Any]]] = {}
    for row in effect["materials"]:
        key = signature(list(row.get("validKeywords") or []))
        materials_by_signature.setdefault(key, []).append(row)
    require(set(materials_by_signature) == {"", "_USE_SOFTBLEND", "_SAMPLE_TEX0+_USE_SOFTBLEND"},
            "selected Li Zhiyan keyword signatures drifted")

    output_variants = []
    for key, material_rows in sorted(materials_by_signature.items()):
        files = VARIANT_FILES[key]
        slug = files["slug"]
        runtime_keywords = sorted([item for item in key.split("+") if item] + ["HG_ENABLE_MV"])
        runtime = signature(runtime_keywords)
        require(runtime == signature(([item for item in key.split("+") if item] + ["HG_ENABLE_MV"])),
                f"runtime keyword join drifted for {key or 'BASE'}")
        instanced_keywords = sorted(runtime_keywords + ["SRP_INSTANCING_ON"])
        instanced = signature(instanced_keywords)
        for stage in ("vertex", "fragment"):
            require(metadata_census[(runtime, stage)] == 1 and
                    metadata_census[(instanced, stage)] == 1,
                    f"compiled stage pairing drifted for {key or 'BASE'} {stage}")
        stages = {}
        for stage in ("vertex", "fragment"):
            stem = files[stage] + f"_endfield_dxbc_{0 if stage == 'vertex' else 1}.dxbc"
            binary = SIDECARS / stem
            metadata = SIDECARS / (stem + ".metadata.json")
            require(binary.is_file() and metadata.is_file(), f"missing Persistent {stage} sidecar")
            meta = load(metadata)
            require(meta.get("DecodedProgramStage") == stage, f"{stage} metadata stage drifted")
            require(signature(meta.get("SourceCompiledKeywords") or []) == runtime, f"{stage} keywords drifted")
            stages[stage] = {
                "dxbc": copy_artifact(binary, f"{slug}.{stage}.dxbc.bytes"),
                "metadata": copy_artifact(metadata, f"{slug}.{stage}.metadata.json"),
                "decodedProgramStage": stage,
                "sourcePass": meta.get("SourcePassName"),
                "compiledKeywords": meta.get("SourceCompiledKeywords"),
                "debugName": meta.get("DebugName"),
                "descriptorReflectionBoundary": "serialized metadata is partial; live D3D descriptor-table contents are not captured",
            }
        hlsl = HLSL_ROOT / f"{files['hlsl']}.fragment.hlsl"
        require(hlsl.is_file(), "Persistent Ruri output is missing")
        stages["fragment"]["ruriHlsl"] = copy_artifact(hlsl, f"{slug}.fragment.ruri.hlsl.txt")
        stages["fragment"]["registerSignature"] = hlsl_signature(hlsl)
        output_variants.append({
            "materialKeywords": [item for item in key.split("+") if item],
            "materials": [
                {"name": row["name"], "pathID": row["pathID"]}
                for row in sorted(material_rows, key=lambda value: value["name"])
            ],
            "nonInstancedCompiledKeywords": runtime_keywords,
            "instancedCompiledKeywords": instanced_keywords,
            "stages": stages,
        })

    contract = {
        "schema": "endfield.lizhiyan-overview-vfxbasev2-variants.v1",
        "status": "material_to_compiled_variant_closed_live_draw_and_descriptor_table_pending",
        "shader": {"name": "HGRP/Effect/VFXBaseV2", "pathID": SHADER_PATH_ID,
                   "pass": "ForwardOnly", "gpuProgramID": 59433},
        "source": {
            "effectContract": EFFECT.resolve().relative_to(REPO.resolve()).as_posix(),
            "effectContractSha256": sha256(EFFECT),
            "persistentShaderExport": SOURCE.resolve().relative_to(REPO.resolve()).as_posix(),
            "persistentShaderExportSha256": sha256(SOURCE),
            "shaderChunk": str(SHADER_CHUNK),
            "shaderChunkSha256": sha256(SHADER_CHUNK),
            "overlaySelection": "Persistent VFS overrides the same StreamingAssets Shader PathID for the installed client",
        },
        "summary": {"materials": 6, "compiledKeywordSignatures": 1360,
                    "materialKeywordSignatures": 3, "exactNonInstancedDxbcPairs": 3,
                    "verifiedInstancedDxbcPairs": 3},
        "variants": output_variants,
        "renderScheduling": {
            "sourceArtifacts": runtime_artifacts,
            "materialQueue": 3700,
            "queueRange": {"first": 3660, "last": 3740},
            "pass": "ForwardOnly in Forward Transparent After DOF",
            "attachments": {
                "color0": "new sceneColor clone, store",
                "color1": "incoming sceneMV when valid, load/store",
                "depth": "incoming sceneDepth, read",
            },
            "status": "native_static_after_dof_renderer_list_and_attachment_contract_closed_live_handles_pending",
        },
        "executionBoundary": "Each serialized material keyword set now resolves uniquely to an exact ForwardOnly vertex/fragment DXBC pair and an SRP-instanced signature. This does not identify a retail draw or capture its live descriptor table, PSO overrides, MRT/depth attachments, ordering, or compositing; Unity materials remain fail-closed.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    CONTRACT.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {CONTRACT}: variants=3 materials=6 sha256={sha256(CONTRACT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
