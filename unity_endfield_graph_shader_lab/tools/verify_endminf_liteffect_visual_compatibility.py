"""Static opt-in contract for the non-exact Endminf LitEffect visual path."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMPORTER = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfOverviewEffectImporter.cs"
SHADER = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldEndminfLitEffectVisualCompatibility.shader"
RUNTIME = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldEndminfLitEffectCompatibilityBinding.cs"
BUILDER = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfLitEffectCompatibilityBindingBuilder.cs"
CAPTURE_SOURCE = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfViewerPlayModeCapture.cs"
SETUP_SOURCE = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldManifestCharacterSetup.cs"
OPEN_WRAPPER = ROOT / "unity_endfield_graph_shader_lab/open_character_recovery_lab.bat"
SPAWNER = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredCharEffectSpawner.cs"
CAPTURE_REPORT = ROOT / "unity_endfield_graph_shader_lab/scratch/character_recovery/endminf_actor_only_m27_crystal_41/report.json"
OUT = ROOT / "reports/assets/character_recovery/endminf_liteffect_visual_compatibility.json"
ASSETS = {
    "M01": (
        ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_01_p5A6341E8A834E421.mat",
        "626dc677675fea1a3a0f2f0079c9755455d37336cfe8cd682e3332669606f509",
    ),
    "M38": (
        ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_38_pAFCE491DD7BC5724.mat",
        "b52f21342f56dd8b7801fe31217cc806a88553f5cba1cc688084dd229edcd38a",
    ),
    "M27": (
        ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_27_pA531A88850690EB8.mat",
        "696bf7dc65d7b4e4a591980ad95faeec80077faed0213ccc74ea5bc539eab8a7",
    ),
    "rockMesh": (
        ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Meshes/S_rock_small_1_017_02_lod2_p8EC9950E5461C8D9.obj",
        "e3bbdc9973e5f9dfb2d499fb440be36f99a525b525a22af8ce63b9c48402f8a7",
    ),
}

def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def main() -> int:
    importer = IMPORTER.read_text(encoding="utf-8")
    shader = SHADER.read_text(encoding="utf-8")
    runtime = RUNTIME.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    capture_source = CAPTURE_SOURCE.read_text(encoding="utf-8")
    setup_source = SETUP_SOURCE.read_text(encoding="utf-8")
    open_wrapper = OPEN_WRAPPER.read_text(encoding="utf-8")
    spawner = SPAWNER.read_text(encoding="utf-8")
    required_importer = [
        'ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT',
        '0x5A6341E8A834E421L', '0xA531A88850690EB8UL',
        '0xAFCE491DD7BC5724UL',
        'LitEffectShaderPathId = 6428594484694422749L',
        'keywords.SequenceEqual(new[] { "_PARALLAX_MAP" })',
        'L.Int(row, "m_CustomRenderQueue") == 2000',
        'ConfigureLitEffectCompatibilityTexture(',
        'TextureImporterType.NormalMap',
    ]
    required_shader = [
        'Hidden/Endfield/Compatibility/Endminf/LitEffectParallax',
        'VISUAL COMPATIBILITY ONLY', '"LightMode"="ForwardOnly"',
        '_BaseColorMap', '_MROMap', '_NormalMap', '_ParallaxMap', '_ParallaxColor',
    ]
    failures = ["importer missing " + value for value in required_importer if value not in importer]
    failures += ["shader missing " + value for value in required_shader if value not in shader]
    required_runtime = [
        "endfield.endminf-liteffect-runtime-binding.v1",
        "ParticleSystemRenderMode.Mesh",
        "row.renderer.SetMeshes",
        "row.renderer.sharedMaterials",
        "if (!compatibility && !exactM27)",
    ]
    required_builder = [
        "Material01PathId = 0x5A6341E8A834E421L",
        "0xA531A88850690EB8UL",
        "0xAFCE491DD7BC5724UL",
        "0x8EC9950E5461C8D9UL",
        "rows.Count == 10 && material01Count == 7 && material38Count == 3",
        "renderer.enabled = false",
        "renderer.sharedMaterials = Array.Empty<Material>()",
    ]
    failures += ["runtime binding missing " + value for value in required_runtime if value not in runtime]
    failures += ["binding builder missing " + value for value in required_builder if value not in builder]
    failures += ["focused rebuild missing binding builder invocation"
                 for _ in [0] if "EndfieldEndminfLitEffectCompatibilityBindingBuilder.BuildAndValidate()" not in setup_source]
    failures += ["canonical Endminf launcher does not enable the retained LitEffect owners"
                 for _ in [0] if 'set "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1"' not in open_wrapper]
    required_lifecycle = [
        "StartRecoveredLegacyAnimations(instance)",
        "animation.playAutomatically",
        'EndminfCompositeRockClipName =',
        '"A_fx_endminf_ui_overview_03_04"',
        "EndminfCompositeRockClipDelaySeconds = 2.7666667f",
        "animation.Rewind(animation.clip.name)",
        "animation.Play(animation.clip.name)",
    ]
    failures += ["effect lifecycle missing " + value
                 for value in required_lifecycle if value not in spawner]
    asset_evidence = {}
    for name, (path, expected) in ASSETS.items():
        actual = sha256(path)
        asset_evidence[name] = {"path": str(path.relative_to(ROOT)), "sha256": actual,
                                "expectedSha256": expected, "validated": actual == expected}
        if actual != expected:
            failures.append(f"asset hash drifted {name}")

    capture = json.loads(CAPTURE_REPORT.read_text(encoding="utf-8")) if CAPTURE_REPORT.is_file() else {}
    first = next((row for row in capture.get("frames", []) if row.get("effectRootCount") == 4), {})
    blocked = first.get("blockedRendererIdentities") or []
    capture_valid = (
        capture.get("schema") == "endfield.endminf-viewer-playmode-sequence.v4"
        and capture.get("status") == "ok"
        and capture.get("observedPrimaryRockCompatibilityBinding") is True
        and first.get("admittedRenderers") == 68
        and len(blocked) == 2
    )
    if not capture_valid:
        failures.append("canonical capture did not validate the eleven-row binding/two-row boundary")
    report = {
        "schema": "endfield.endminf-liteffect-visual-compatibility.v2",
        "status": "verified_non_exact" if not failures else "failed",
        "classification": "visual_compatibility_not_source_exact",
        "defaultMode": "disabled_fail_closed",
        "optInEnvironment": "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1",
        "scope": {"shaderPathId": 6428594484694422749,
                  "materials": ["M_fx_endminm_gfx_01", "M_fx_endminm_gfx_27",
                                "M_fx_endminm_gfx_38"],
                  "mesh": "S_rock_small_1_017_02_lod2",
                  "expectedRendererCount": 11,
                  "materialRendererCounts": {"M_fx_endminm_gfx_01": 7,
                                             "M_fx_endminm_gfx_27": 1,
                                             "M_fx_endminm_gfx_38": 3}},
        "assetEvidence": asset_evidence,
        "runtimeBinding": {
            "schema": "endfield.endminf-liteffect-runtime-binding.v1",
            "policy": "eleven direct renderer/material/mesh references across two prefabs; no runtime hierarchy/name search",
            "default": "renderers remain disabled with empty material arrays",
        },
        "canonicalCapture": {
            "path": str(CAPTURE_REPORT.relative_to(ROOT)),
            "validated": capture_valid,
            "admittedRenderersDuringEntrance": first.get("admittedRenderers"),
            "remainingBlockedRendererCount": len(blocked),
            "remainingBoundary": "two non-LitEffect renderers remain separate",
        },
        "sourceInputsUsed": ["material identities", "_PARALLAX_MAP keyword", "queue 2000",
                             "recovered texture identities", "serialized colors/floats"],
        "approximated": ["converted PNG texture derivatives where native payloads are absent",
                         "forward lighting", "emission scale", "HGBuffer/deferred replacement"],
        "measurementBoundary": "Restoring physical amber geometry is a completeness correction. Whole-frame ROI MAE is not an acceptance gate because this explicitly non-exact forward shader and the authored moving crystal occupy the compared pixels.",
        "failures": failures,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"], OUT)
    return 1 if failures else 0

if __name__ == "__main__": raise SystemExit(main())
