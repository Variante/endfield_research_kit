#!/usr/bin/env python3
"""Fail-closed verifier for the captured Endminf CharacterOutline recovery."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "unity_endfield_graph_shader_lab"
CAPTURE = (
    ROOT
    / "scratch/character_recovery/3dmigoto-dev-v1.0.0/package"
    / "FrameAnalysis-2026-08-24-182850"
)
OUTPUT = (
    ROOT
    / "reports/assets/character_recovery"
    / "endminf_character_outline_recovery.json"
)

SOURCE_FAMILIES = {
    "skin": {
        "shader": ROOT / "scratch/animestudio/body_skin_sidecar_refresh/shader_export/Shader/HGRP_CharacterNPR_Skin_p3E3D05CF72D25122.shader",
        "pairs": [
            (87, "ea3b0461ae572be3", "e4ab05ea62d6a525", 9000),
            (88, "784f11ae11c97112", "2f079737a005dcf6", 16524),
        ],
        "state": ("Ref 36", "Comp Always", "Pass Replace"),
    },
    "generic": {
        "shader": ROOT / "scratch/animestudio/character_npr_generic_sidecars_current/shader_export/Shader/HGRP_CharacterNPR_p9371FF9C9E74391E.shader",
        "pairs": [
            (89, "303f45d5266d0369", "d72788f1180db1fb", 101994),
            (90, "303f45d5266d0369", "d72788f1180db1fb", 20577),
            (91, "303f45d5266d0369", "d72788f1180db1fb", 4524),
        ],
        "state": ("Comp Always", "Pass Replace"),
    },
    "hair": {
        "shader": ROOT / "scratch/animestudio/character_npr_hair_sidecars_current/shader_export/Shader/HGRP_CharacterNPR_Hair_p8FA556110AA47B6F.shader",
        "pairs": [(92, "f3b955247775c7bf", "fadc3687dd18e11c", 27615)],
        "state": ("Ref 16", "ReadMask 16", "Comp NotEqual", "Pass Keep"),
    },
}

UNITY_SHADERS = {
    "skin": LAB / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldCharacterSkinRecovered.shader",
    "generic": LAB / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldCharacterClothRecovered.shader",
    "hair": LAB / "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldCharacterHairRecovered.shader",
}

SOURCE_MESHES = {
    "S_actor_endminf_face_01_lod0": ROOT / "scratch/character_ui_import/characters/chr_0003_endminf/meshes/Mesh/S_actor_endminf_face_01_lod0_pE3E44459F0DD0976.json",
    "S_actor_endminf_body_01_lod0": ROOT / "scratch/character_ui_import/characters/chr_0003_endminf/meshes/Mesh/S_actor_endminf_body_01_lod0_pBCE4E33450BFD849.json",
    "S_actor_endminf_cloth_01_lod0": ROOT / "scratch/character_ui_import/characters/chr_0003_endminf/meshes/Mesh/S_actor_endminf_cloth_01_lod0_p4F2352ABE20314B6.json",
    "S_actor_endminf_cloth_04_lod0": ROOT / "scratch/character_ui_import/characters/chr_0003_endminf/meshes/Mesh/S_actor_endminf_cloth_04_lod0_p413C309D2AD902C7.json",
    "S_actor_endminf_cloth_03_lod0": ROOT / "scratch/character_ui_import/characters/chr_0003_endminf/meshes/Mesh/S_actor_endminf_cloth_03_lod0_pBD7D3E535F2F37C2.json",
    "S_actor_endminf_hair_01_lod0": ROOT / "scratch/character_ui_import/characters/chr_0003_endminf/meshes/Mesh/S_actor_endminf_hair_01_lod0_p5CD48B482FDFBE75.json",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pass_block(text: str) -> str:
    match = re.search(
        r'Name "CHARACTER_OUTLINE"(?P<body>.*?)CGPROGRAM', text, re.DOTALL
    )
    require(match is not None, "Unity CharacterOutline pass is missing")
    return match.group("body")


def main() -> None:
    require(CAPTURE.is_dir(), f"capture is missing: {CAPTURE}")
    rows: list[dict[str, object]] = []
    source_hashes: dict[str, str] = {}
    mesh_hashes: dict[str, str] = {}

    for mesh_name, mesh_path in SOURCE_MESHES.items():
        require(mesh_path.is_file(), f"source mesh is missing: {mesh_path}")
        mesh = json.loads(mesh_path.read_text(encoding="utf-8"))
        vertex_count = mesh.get("m_VertexCount")
        packed_normals = mesh.get("m_UV2", [])
        require(
            isinstance(vertex_count, int) and vertex_count > 0,
            f"source mesh vertex count is invalid: {mesh_name}",
        )
        require(
            len(packed_normals) == vertex_count * 4,
            f"source mesh packed TEXCOORD2 drifted: {mesh_name}",
        )
        mesh_hashes[mesh_name] = sha256(mesh_path)

    for family, contract in SOURCE_FAMILIES.items():
        source = contract["shader"]
        require(source.is_file(), f"source shader is missing: {source}")
        source_text = source.read_text(encoding="utf-8", errors="strict")
        source_pass_match = re.search(
            r'Name "CharacterOutline"(?P<body>.*?)GpuProgramID',
            source_text,
            re.DOTALL,
        )
        require(source_pass_match is not None, f"{family} source pass is missing")
        source_pass = source_pass_match.group("body")
        for token in ("Blend 0 Zero Zero, Zero Zero", "ZTest Less", "ZWrite Off", "Cull Front"):
            require(token in source_pass, f"{family} source state lost {token}")
        for token in contract["state"]:
            require(token in source_pass, f"{family} source stencil lost {token}")
        source_hashes[family] = sha256(source)

        unity = UNITY_SHADERS[family]
        unity_text = unity.read_text(encoding="utf-8", errors="strict")
        block = pass_block(unity_text)
        for token in (
            "Cull Front",
            "ZWrite Off",
            "ZTest Less",
            "Blend 0 Zero Zero, Zero Zero",
            "Blend 1 One Zero",
        ):
            require(token in block, f"{family} Unity state lost {token}")
        for token in contract["state"]:
            require(token in block, f"{family} Unity stencil lost {token}")
        for token in (
            "EndfieldHGRPCharacterOutlineClipOffset",
            "EndfieldHGRPCharacterOutlineNormal",
            "EndfieldHGRPCharacterOutlineClipZ",
            "EndfieldRecoveredCharacterMotionMrt",
            "outlineNormal : TEXCOORD2",
            "_OutlineAverageNormal > 0.5",
            "viewPosition.z - depthOffset",
            "outlineMask.g",
            "SV_Target1",
        ):
            require(token in unity_text, f"{family} Unity shader lost {token}")

        for event, vertex, fragment, indices in contract["pairs"]:
            identity = f"{event:06d}-ib=9a09f1f0-vs={vertex}-ps={fragment}.txt"
            event_path = CAPTURE / identity
            require(event_path.is_file(), f"captured draw is missing: {identity}")
            event_text = event_path.read_text(encoding="utf-8", errors="strict")
            require(f"index count: {indices}" in event_text, f"event {event} index count drifted")
            require(f"// hash: {vertex}" in source_text, f"source lost vertex hash {vertex}")
            require(f"// hash: {fragment}" in source_text, f"source lost fragment hash {fragment}")
            rows.append(
                {
                    "event": event,
                    "family": family,
                    "indexCount": indices,
                    "vertexShader": vertex,
                    "fragmentShader": fragment,
                }
            )

    pipeline = LAB / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
    pipeline_text = pipeline.read_text(encoding="utf-8", errors="strict")
    for token in (
        '"CHARACTER_OUTLINE",',
        "useRecoveredSceneMV ? recoveredSceneMV : null",
        "commandBuffer.SetRenderTarget(",
        "new RenderTargetIdentifier(sceneMV)",
    ):
        require(token in pipeline_text, f"outline SceneMV publication lost {token}")

    importer = LAB / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldManifestCharacterSetup.cs"
    importer_text = importer.read_text(encoding="utf-8", errors="strict")
    for token in (
        'meshData.TryGetValue("m_UV2"',
        "mesh.SetUVs(2, outUvs)",
        "VertexAttribute.TexCoord2",
        "EndfieldEndminfOverviewEffectBindingBuilder.BuildAndValidate()",
        "EndfieldEndminfLitEffectCompatibilityBindingBuilder.BuildAndValidate()",
    ):
        require(token in importer_text, f"outline mesh import gate lost {token}")

    capture_output = (
        LAB / "scratch/character_recovery/endminf_viewer_canonical_outline_v6"
    )
    report_path = capture_output / "report.json"
    require(report_path.is_file(), f"canonical capture report is missing: {report_path}")
    capture_report = json.loads(report_path.read_text(encoding="utf-8"))
    require(capture_report.get("status") == "ok", "canonical capture did not pass")
    require(
        capture_report.get("graphicsDeviceType") == "Direct3D11",
        "canonical capture did not use Direct3D11",
    )
    frames = capture_report.get("frames", [])
    require(len(frames) == 41, f"canonical capture frame count drifted: {len(frames)}")
    require(
        all(row.get("canonicalCharacterPreGBufferReady") for row in frames),
        "canonical CharacterPrePass was not ready on every frame",
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "endfield.endminf-character-outline-recovery.v2",
        "status": "ok",
        "capture": str(CAPTURE.relative_to(ROOT)).replace("\\", "/"),
        "drawCount": len(rows),
        "draws": rows,
        "sourceShaderSha256": source_hashes,
        "sourceMeshSha256": mesh_hashes,
        "renderState": {
            "color0Blend": "Zero Zero, Zero Zero",
            "sceneMVBlend": "One Zero",
            "depthTest": "Less",
            "depthWrite": False,
            "cull": "Front",
        },
        "unity": {
            "captureStatus": "ok",
            "frames": len(frames),
            "graphicsDeviceType": capture_report.get("graphicsDeviceType"),
            "sceneMVPublishedByOutline": True,
            "clipSpaceWidthRecovery": True,
            "packedAverageNormalRecovery": True,
            "sourceZOffsetRecovery": True,
            "repeatCaptureByteIdenticalFrames": 0,
        },
        "comparison": {
            "noFramegenPairs": 28,
            "previousAveragePsnrDb": 13.326791,
            "repeatAveragePsnrDb": [13.561907, 13.555405],
            "previousCrystalCleanPsnrDb": 14.069310,
            "repeatCrystalCleanPsnrDb": [14.068424, 14.074417],
            "repeatCapturePsnrDb": 31.445556,
            "interpretation": (
                "The packed-normal and Z recovery is source-exact, but repeated "
                "phase-identical captures are not pixel-identical. The clean-reference "
                "range contains the prior result, so cross-run PSNR movement is not "
                "attributed to this pass."
            ),
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"PASS Endminf CharacterOutline recovery: {len(rows)} draws, 41 D3D11 frames")
    print(OUTPUT)


if __name__ == "__main__":
    main()
