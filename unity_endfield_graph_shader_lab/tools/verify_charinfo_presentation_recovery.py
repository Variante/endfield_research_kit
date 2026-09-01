#!/usr/bin/env python3
"""Static verifier for the source-driven CharInfo presentation branch."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab"
SOURCE_ROOT = (
    ASSET_ROOT / "Generated" / "OriginalData" / "CharInfoPresentation"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_tokens(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{path}: missing required token {token!r}")


def verify_manifest() -> dict[str, object]:
    manifest_path = SOURCE_ROOT / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "endfield.charinfo.presentation.original-data.v1"
    assert manifest["complete"] is False
    blocker = manifest["blocking_gap_summary"]
    assert "HGRP/Lit" in blocker and "fail-closed" in blocker

    for record in manifest["files"]:
        path = SOURCE_ROOT / record["path"]
        assert path.is_file(), path
        assert sha256(path) == record["sha256"], path

    for variant in manifest["selected_shader_variants"]:
        for stage in ("vertex", "fragment"):
            path = SOURCE_ROOT / variant[f"{stage}_path"]
            assert path.is_file(), path
            assert sha256(path) == variant[f"{stage}_sha256"], path
            metadata_path = path.with_name(
                path.name.removesuffix(".dxbc.bytes") + ".metadata.json"
            )
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            assert metadata["SourcePassName"] == variant["pass"]
            assert metadata["SourceCompiledKeywords"] == variant["keywords"]

    outside = manifest["selected_shader_variants"][-1]
    assert outside["shader"] == "HGRP/Lit"
    assert outside["pass"] == "HGBuffer"
    assert "runtime_deferred_contract_missing" in outside["status"]
    return manifest


def verify_meshes() -> None:
    expected = {
        "Sphere.json": ("Sphere", 509, 2304, 2, 4),
        "GeoSphere001.json": ("GeoSphere001", 1028, 5400, 0, 4),
        "S_GridFar.json": ("S_GridFar", 1012, 1518, 3, 0),
    }
    for filename, (name, vertices, indices, uv1_dim, tangent_dim) in expected.items():
        payload = json.loads((SOURCE_ROOT / "Meshes" / filename).read_text())
        assert payload["m_Name"] == name
        assert payload["m_VertexCount"] == vertices
        assert len(payload["m_Vertices"]) == vertices * 3
        assert len(payload["m_Normals"]) == vertices * 3
        assert len(payload["m_UV0"]) == vertices * 2
        assert len(payload["m_UV1"] or []) == vertices * uv1_dim
        assert len(payload["m_Tangents"] or []) == vertices * tangent_dim
        assert len(payload["m_Indices"]) == indices
        assert payload["m_Colors"] in (None, [])
        assert payload["m_SubMeshes"][0]["topology"] == "Triangles"


def verify_material_sources() -> None:
    materials = SOURCE_ROOT / "Materials"
    grid = json.loads((materials / "M_GridFar.json").read_text())
    floor = json.loads(
        (materials / "M_CharInfoFloor_graph_0_material.json").read_text()
    )
    shadow = json.loads(
        (materials / "M_CharInfo_ShadowReceiver.json").read_text()
    )
    wall = json.loads((materials / "M_charInfo_wall.json").read_text())
    outside = json.loads((materials / "M_CharInfo_outside.json").read_text())

    gf = grid["m_SavedProperties"]["m_Floats"]
    assert gf["_GridLineWidth"] == 1.5
    assert gf["_AlphaClipThreshold"] == 0.049
    assert gf["_NearCameraFadeDistanceStart"] == 2.0
    assert gf["_NearCameraFadeDistanceEnd"] == 3.0
    assert gf["_NearCameraFadeDistanceStart2"] == 120.0
    assert gf["_NearCameraFadeDistanceEnd2"] == 100.0
    assert gf["_SrcBlend"] == 5.0 and gf["_DstBlend"] == 10.0

    ff = floor["m_SavedProperties"]["m_Floats"]
    assert ff["_SDFSwitchStart"] == 30.7
    assert ff["_SDFSwitchEnd"] == 14.1
    assert ff["_CullMode"] == 2.0
    sdf_env = floor["m_SavedProperties"]["m_TexEnvs"]["_BlendSDFTex"]
    assert sdf_env["m_Offset"] == {"X": 0.72, "Y": 0.45}

    sf = shadow["m_SavedProperties"]["m_Floats"]
    assert sf == {
        "_CircleFade": 1.0,
        "_CircleFadeDistance": 1.257,
        "_CircleFadeSmoothness": 2.141,
        "_DisableCharacterSelfShadow": 0.0,
        "_DisableSceneShadow": 1.0,
    }

    wf = wall["m_SavedProperties"]["m_Floats"]
    assert wf["_UseMainTexAsAlpha"] == 1.0
    assert wf["_UseLighting"] == 0.0
    assert wf["_UseFog"] == 0.0
    assert wf["_CullMode"] == 1.0

    outside_env = outside["m_SavedProperties"]["m_TexEnvs"]["_MROMap"]
    assert outside_env["m_Texture"]["m_PathID"] == -1246962829539794806
    assert outside["m_Shader"]["m_PathID"] == 5324015590718682574


def verify_ready_subset_open_state() -> None:
    state_path = SOURCE_ROOT / "ready_subset_open_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["schema"] == (
        "endfield.charinfo.presentation.ready-subset-open-state.v1"
    )
    assert state["ready_subset_complete"] is True
    assert state["grid_sample_time_seconds"] == 1.0
    assert state["floor_sample_time_seconds"] == 1.0
    assert state["grid_far_tint"] == {
        "r": 0.509434,
        "g": 0.509434,
        "b": 0.509434,
        "a": 0.6,
    }
    assert state["floor_blend_tint"] == {
        "r": 1.0,
        "g": 1.0,
        "b": 1.0,
        "a": 0.011764706,
    }
    assert state["grid_in_clip"]["path_id"] == "-4057036333109158707"
    assert state["grid_in_clip"]["animestudio_anim_sha256"] == (
        "b46ebe0c20c6d8b6ed61a3512c443a12111a74f0251dbfdb52aaf9d6d1d21cdf"
    )
    assert state["floor_in_clip"]["path_id"] == "-1947940266143670292"
    assert state["floor_in_clip"]["animestudio_anim_sha256"] == (
        "117466b10bed3bcc1c766c3e8b094638dfa7477840d206ab1b2da813ec588115"
    )
    assert state["excluded_renderers"] == ["SphereOutside", "ShadowPlane"]


def verify_implementation() -> None:
    runtime = ASSET_ROOT / "Runtime" / "Rendering" / (
        "EndfieldRecoveredCharInfoPresentation.cs"
    )
    builder = ASSET_ROOT / "Editor" / "CharacterRecovery" / (
        "EndfieldRecoveredCharInfoPresentationBuilder.cs"
    )
    recovered = ASSET_ROOT / "Shaders" / "Recovered"
    require_tokens(
        runtime,
        [
            "public bool enableRecoveredPresentation;",
            "public bool enableReadySubsetDiagnostic;",
            "public bool enableEndminfSourceBackground;",
            "public bool exactSourceAssetsReady;",
            "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC",
            "ENDFIELD_ENDMINF_SOURCE_BACKGROUND",
            "SetRendererEnabledStates(false, true, true, false, true);",
            "SetRendererEnabledStates(false, true, false, false, true);",
            "ApplySettledOpenState(openState, false);",
            "ApplySettledOpenState(openState, true);",
            "ValidateEndminfSourceBackgroundReadiness",
            "ShadowPlane final-consumer route",
            "physical-camera stencil/color-target ownership is not closed",
            "new Color(0.509434f, 0.509434f, 0.509434f, 0.6f)",
            "new Color(1.0f, 1.0f, 1.0f, 0.011764706f)",
            "sourceContent.SetActive(false);",
            "fail-closed and ReferenceBackdrop",
            "Endfield/Recovered/CharInfo/HGRPLit",
        ],
    )
    require_tokens(
        builder,
        [
            "new Vector3(-1.9700003f, 0.0f, -1.5599998f)",
            "new Quaternion(0.0f, -0.0914292f, 0.0f, 0.9958116f)",
            "new Vector3(1.8081535f, 0.0f, 2.0754473f)",
            "new Vector3(-10.53f, 1.4f, -13.4f)",
            "expectedUv1Dimension == 3",
            "SubMeshDescriptor subMesh = rebuilt.GetSubMesh(0);",
            "subMesh.bounds = importedBounds;",
            "MeshUpdateFlags.DontRecalculateBounds",
            "BoundsApproximatelyEqual(mesh.GetSubMesh(0).bounds, mesh.bounds)",
            "TextureFormat.BC7",
            "TextureFormat.DXT1",
            "UnavailableLitShaderName",
            "controller.enableRecoveredPresentation = false;",
            "controller.enableReadySubsetDiagnostic = false;",
            "controller.enableEndminfSourceBackground = false;",
            "controller.settledOpenState = readySubsetOpenState;",
        ],
    )

    runtime_source = runtime.read_text(encoding="utf-8")
    assert runtime_source.count("gridTint.a *= 0.125f;") == 1
    assert runtime_source.count("ApplySettledOpenState(openState, true);") == 1
    source_start = runtime_source.index("private void ApplyEndminfSourceBackground()")
    source_end = runtime_source.index(
        "private void ApplyReadySubsetDiagnostic()", source_start
    )
    source_path = runtime_source[source_start:source_end]
    assert "ApplySettledOpenState(openState, false);" in source_path
    assert "gridTint.a *= 0.125f;" not in source_path
    assert '"_TopColor"' not in source_path

    require_tokens(
        recovered / "EndfieldCharInfoVFXDsWriteRecovered.shader",
        [
            'Shader "Endfield/Recovered/CharInfo/VFXDsWrite"',
            "#pragma shader_feature_local _USE_GRID_LINE",
            "#pragma shader_feature_local _ALPHATEST_ON",
            "sampler_LinearClamp",
            "_NearCameraFadeDistanceStart2",
            "clip(alpha - _AlphaClipThreshold)",
            "Blend [_SrcBlend] [_DstBlend]",
        ],
    )
    require_tokens(
        recovered / "EndfieldCharInfoVFXDistanceFieldRecovered.shader",
        [
            'Shader "Endfield/Recovered/CharInfo/VFXDistanceField"',
            "ddx_coarse(sdfDistance)",
            "ddy_coarse(sdfDistance)",
            "linear_mirror_sampler",
            "linear_repeat_sampler",
            "_APPLY_COLOR_BANDING_DITHER",
        ],
    )
    require_tokens(
        recovered / "EndfieldCharInfoVFXBaseV2StaticRecovered.shader",
        [
            'Shader "Endfield/Recovered/CharInfo/VFXBaseV2Static"',
            "mainSample.r",
            "masterAlpha",
            "Cull [_CullMode]",
        ],
    )
    require_tokens(
        recovered / "EndfieldCharInfoShadowReceiverRecovered.shader",
        [
            'Shader "Endfield/Recovered/CharInfo/CharacterNPR_ShadowReceiver"',
            "EndfieldHGRPCharacterShadowCoord",
            "EndfieldHGRPSampleCharacterShadowWithStrength",
            "Blend Zero SrcColor, Zero SrcColor",
            "ReadMask 32",
            "Comp NotEqual",
            "float capsuleAo = _EndfieldRecoveredVisibilitySHReady > 0.5",
        ],
    )
    require_tokens(
        recovered / "EndfieldCharInfoHGRPLitUnavailable.shader",
        [
            'Shader "Hidden/Endfield/Recovered/CharInfo/HGRPLitUnavailable"',
            "ColorMask 0",
            "ZWrite Off",
        ],
    )
def main() -> int:
    manifest = verify_manifest()
    verify_meshes()
    verify_material_sources()
    verify_ready_subset_open_state()
    verify_implementation()
    print(
        "CharInfo presentation static verification passed: "
        f"{len(manifest['files'])} exact source files, "
        f"{len(manifest['selected_shader_variants'])} shipped shader variants; "
        "full runtime selector remains default-off/fail-closed at HGRP/Lit; "
        "ready-subset diagnostic is default-off and excludes SphereOutside/ShadowPlane; "
        "independent Endminf source background admits exact floor and Far while "
        "excluding SphereOutside, ShadowPlane, and the fitted plate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
