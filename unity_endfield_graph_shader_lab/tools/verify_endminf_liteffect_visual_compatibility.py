"""Static opt-in contract for the non-exact Endminf LitEffect visual path."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

from verify_endminf_liteffect_resource_mapping import (
    REPORT_PATH as RESOURCE_MAPPING_REPORT,
    VerificationError as ResourceMappingVerificationError,
    build_report as build_resource_mapping_report,
)

ROOT = Path(__file__).resolve().parents[2]
IMPORTER = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfOverviewEffectImporter.cs"
SHADER = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldEndminfLitEffectVisualCompatibility.shader"
LIGHT_VOLUME = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldHGRPCharacterLightingVolume.cs"
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
        None,
    ),
    "M38": (
        ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_38_pAFCE491DD7BC5724.mat",
        None,
    ),
    "M27": (
        ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_27_pA531A88850690EB8.mat",
        None,
    ),
    "rockMesh": (
        ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Meshes/S_rock_small_1_017_02_lod2_p8EC9950E5461C8D9.obj",
        "e3bbdc9973e5f9dfb2d499fb440be36f99a525b525a22af8ce63b9c48402f8a7",
    ),
}
SOURCE_MATERIAL_ROOT = (
    ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material"
)
SOURCE_MATERIALS = {
    "M01": (
        SOURCE_MATERIAL_ROOT / "M_fx_endminm_gfx_01_p5A6341E8A834E421.json",
        "247e90600649b896249bdb4884abaa9d89aaa961d3a76d826cad9159a420426d",
    ),
    "M27": (
        SOURCE_MATERIAL_ROOT / "M_fx_endminm_gfx_27_pA531A88850690EB8.json",
        "bf067450ab4bfd747747bc7b0f15b0c865fdc042cc1ef119646e8bec6af22b46",
    ),
    "M38": (
        SOURCE_MATERIAL_ROOT / "M_fx_endminm_gfx_38_pAFCE491DD7BC5724.json",
        "3581bdfd934d8c8e3d3cdbdfdbe7188dd38f2a1b951f8114a6a47a7da34aa8f6",
    ),
}
SOURCE_FLOATS = (
    "_BaseColorTintCover", "_BaseColorBrighterScale",
    "_NormalScale", "_RoughnessMin", "_RoughnessMax",
    "_OcclusionStrength", "_TwoSidedNormal", "_Metallic",
    "_BaseTextureMapCount",
    "_BaseUVSet", "_BasePbrMapUVSet", "_ParallaxMapUVType",
    "_ParallaxNoiseMapTilling", "_ParallaxFresnelStrength",
    "_ParallaxStrength", "_ParallaxTilling", "_ParallaxMarchNum",
    "_ParallaxMinBrightness", "_ParallaxIntensity",
)
SOURCE_COLORS = ("_BaseColor", "_ParallaxColor", "_ParallaxColorDark")

def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def canonical_json(value: object) -> str:
    """Compare reports through their serialized JSON representation.

    JSON object keys are strings, while the freshly built mapping intentionally
    uses integer physical-register keys.  Normalizing both sides prevents that
    representational difference from making a current published report look
    stale without weakening any value or ordering gate.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class RuntimeBindingVerificationError(ValueError):
    pass


def _strip_csharp_comments_and_literals(source: str) -> str:
    """Remove non-code text while preserving enough spacing for token gates."""
    pattern = re.compile(
        r"/\*.*?\*/|//[^\r\n]*|@\"(?:\"\"|[^\"])*\"|"
        r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
        re.DOTALL,
    )
    return pattern.sub(lambda match: "\n" * match.group(0).count("\n") or " ", source)


def validate_runtime_binding_source(source: str) -> None:
    """Keep the opt-in renderer mutation transaction fully reversible.

    This is a bounded source contract rather than a C# parser. It intentionally
    covers every Renderer/GameObject field written by OnEnable and requires the
    snapshot to precede the first write, fail-path rollback, and idempotent
    disable/destroy restoration with visibility restored last.
    """
    code = _strip_csharp_comments_and_literals(source)
    try:
        on_enable_start = code.index("private void OnEnable()")
        on_disable_start = code.index("private void OnDisable()")
        on_destroy_start = code.index("private void OnDestroy()")
        capture_start = code.index("private void CaptureRuntimeState(")
        restore_start = code.index("private void RestoreRuntimeState()")
        validator_start = code.index("public bool TryValidateForRecoveryAudit(")
        on_enable = code[on_enable_start:on_disable_start]
        on_disable = code[on_disable_start:on_destroy_start]
        on_destroy = code[on_destroy_start:capture_start]
        capture = code[capture_start:restore_start]
        restore = code[restore_start:validator_start]
    except ValueError as exc:
        raise RuntimeBindingVerificationError(
            "runtime binding lifecycle method is missing") from exc

    required_capture = (
        "new Mesh[row.renderer.meshCount]",
        "row.renderer.GetMeshes(meshes)",
        "layer = row.renderer.gameObject.layer",
        "enabled = row.renderer.enabled",
        "renderMode = row.renderer.renderMode",
        "sharedMaterials = (Material[])row.renderer.sharedMaterials.Clone()",
        "meshes = meshes",
    )
    required_restore = (
        "renderer.enabled = false",
        "renderer.gameObject.layer = state.layer",
        "renderer.renderMode = state.renderMode",
        "renderer.SetMeshes(state.meshes, state.meshes.Length)",
        "renderer.sharedMaterials = state.sharedMaterials",
        "renderer.enabled = state.enabled",
        "runtimeStates.Clear()",
    )
    missing_capture = [token for token in required_capture if token not in capture]
    missing_restore = [token for token in required_restore if token not in restore]
    if missing_capture or missing_restore:
        raise RuntimeBindingVerificationError(
            "runtime binding snapshot/restore coverage drifted: "
            f"capture={missing_capture!r} restore={missing_restore!r}")

    write_pattern = re.compile(
        r"\b((?:row\.)?renderer(?:\.gameObject)?\.[A-Za-z_]\w*)\s*"
        r"(?:[+\-*/%&|^]=|=(?!=)|\+\+|--)",
    )
    call_pattern = re.compile(
        r"\b((?:row\.)?renderer)\.([A-Za-z_]\w*)\s*\(",
    )

    def mutation_inventory(body: str) -> tuple[list[str], list[str]]:
        return (
            [match.group(1) for match in write_pattern.finditer(body)],
            [f"{match.group(1)}.{match.group(2)}"
             for match in call_pattern.finditer(body)],
        )

    expected_mutations = {
        "OnEnable": (
            [
                "row.renderer.renderMode",
                "row.renderer.sharedMaterials",
                "row.renderer.gameObject.layer",
                "row.renderer.enabled",
            ],
            ["row.renderer.SetMeshes"],
        ),
        "CaptureRuntimeState": (
            [],
            ["row.renderer.GetMeshes"],
        ),
        "RestoreRuntimeState": (
            [
                "renderer.enabled",
                "renderer.gameObject.layer",
                "renderer.renderMode",
                "renderer.sharedMaterials",
                "renderer.enabled",
            ],
            ["renderer.SetMeshes"],
        ),
    }
    actual_mutations = {
        "OnEnable": mutation_inventory(on_enable),
        "OnDisable": mutation_inventory(on_disable),
        "OnDestroy": mutation_inventory(on_destroy),
        "CaptureRuntimeState": mutation_inventory(capture),
        "RestoreRuntimeState": mutation_inventory(restore),
    }
    expected_mutations["OnDisable"] = ([], [])
    expected_mutations["OnDestroy"] = ([], [])
    for method, expected in expected_mutations.items():
        actual = actual_mutations[method]
        if actual != expected:
            raise RuntimeBindingVerificationError(
                "runtime binding renderer mutation inventory drifted: "
                f"method={method} expected={expected!r} actual={actual!r}")
    try:
        snapshot_position = on_enable.index("CaptureRuntimeState(row)")
        first_mutation_position = on_enable.index(
            "row.renderer.renderMode = ParticleSystemRenderMode.Mesh")
        catch_start = on_enable.index("catch (Exception exception)")
    except ValueError as exc:
        raise RuntimeBindingVerificationError(
            "runtime binding snapshot/mutation transaction drifted") from exc
    if snapshot_position > first_mutation_position:
        raise RuntimeBindingVerificationError(
            "runtime binding mutates a renderer before snapshot")
    if "RestoreRuntimeState();" not in on_enable[catch_start:]:
        raise RuntimeBindingVerificationError(
            "runtime binding exception path does not restore its snapshot")
    if "RestoreRuntimeState();" not in on_disable or \
            "RestoreRuntimeState();" not in on_destroy:
        raise RuntimeBindingVerificationError(
            "runtime binding disable/destroy path is not reversible")
    normalized_disable = re.sub(r"\s+", " ", on_disable).strip()
    normalized_destroy = re.sub(r"\s+", " ", on_destroy).strip()
    if normalized_disable != (
            "private void OnDisable() { RestoreRuntimeState(); }") or \
            normalized_destroy != (
                "private void OnDestroy() { RestoreRuntimeState(); }"):
        raise RuntimeBindingVerificationError(
            "runtime binding disable/destroy bodies contain extra behavior")
    restore_order = [restore.index(token) for token in required_restore[:-1]]
    if restore_order != sorted(restore_order):
        raise RuntimeBindingVerificationError(
            "runtime binding restoration order drifted")
    if actual_mutations["RestoreRuntimeState"][0][-1] != "renderer.enabled":
        raise RuntimeBindingVerificationError(
            "runtime binding does not restore visibility last")


def parsed_material_yaml(path: Path) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    floats: dict[str, float] = {}
    colors: dict[str, dict[str, float]] = {}
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "    m_Floats:":
            section = "floats"
            continue
        if line == "    m_Colors:":
            section = "colors"
            continue
        if not line.startswith("    - "):
            if line.startswith("  ") and not line.startswith("      "):
                section = ""
            continue
        key, _, raw = line[6:].partition(":")
        if not key or not raw:
            continue
        if section == "floats":
            floats[key] = float(raw.strip())
        elif section == "colors":
            match = re.fullmatch(
                r"\s*\{r: ([^,]+), g: ([^,]+), b: ([^,]+), a: ([^}]+)\}",
                raw,
            )
            if match:
                colors[key] = dict(zip(
                    ("r", "g", "b", "a"),
                    (float(value) for value in match.groups()),
                ))
    return floats, colors


def validate_material_yaml(
    name: str,
    material_path: Path,
    source_path: Path,
    expected_source_sha256: str,
) -> tuple[dict, list[str]]:
    failures: list[str] = []
    if not material_path.is_file():
        failures.append(f"generated material is missing {name}")
        return ({
            "sourcePath": str(source_path.relative_to(ROOT)),
            "sourceSha256": sha256(source_path),
            "expectedSourceSha256": expected_source_sha256,
            "validated": False,
        }, failures)
    actual_source_sha256 = sha256(source_path)
    if actual_source_sha256 != expected_source_sha256:
        failures.append(f"source material hash drifted {name}")
        return ({
            "sourcePath": str(source_path.relative_to(ROOT)),
            "sourceSha256": actual_source_sha256,
            "expectedSourceSha256": expected_source_sha256,
            "validated": False,
        }, failures)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source_saved = source.get("m_SavedProperties") or {}
    source_floats = source_saved.get("m_Floats") or {}
    source_colors = source_saved.get("m_Colors") or {}
    material_floats, material_colors = parsed_material_yaml(material_path)
    for field in SOURCE_FLOATS:
        if field not in source_floats or field not in material_floats or abs(
            float(source_floats[field]) - material_floats[field]
        ) > 1.0e-6:
            failures.append(f"material source float drifted {name}.{field}")
    for field in SOURCE_COLORS:
        expected_color = source_colors.get(field) or {}
        actual_color = material_colors.get(field) or {}
        if set(expected_color) != {"r", "g", "b", "a"} or any(
            abs(float(expected_color[channel]) -
                float(actual_color.get(channel, 1.0e30))) > 1.0e-6
            for channel in ("r", "g", "b", "a")
        ):
            failures.append(f"material source color drifted {name}.{field}")
    material_text = material_path.read_text(encoding="utf-8")
    if "_RecoveredParallaxCompatibilityScale" in material_text:
        failures.append(f"material retains capture-fitted scale {name}")
    return ({
        "sourcePath": str(source_path.relative_to(ROOT)),
        "sourceSha256": actual_source_sha256,
        "expectedSourceSha256": expected_source_sha256,
        "sourceFields": list(SOURCE_FLOATS) + list(SOURCE_COLORS),
        "validated": not failures,
    }, failures)

def main() -> int:
    importer = IMPORTER.read_text(encoding="utf-8")
    shader = SHADER.read_text(encoding="utf-8")
    light_volume = LIGHT_VOLUME.read_text(encoding="utf-8")
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
        '_BaseColorMap', '_MROMap', '_NormalMap', '_ParallaxMap',
        '_ParallaxNoiseMap', '_ParallaxColor',
        'SamplerState sampler_LinearClamp;',
        'SamplerState sampler_LinearRepeat;',
        'SamplerState sampler_LinearMirror;',
        'SamplerState sampler_LinearMirrorOnce;',
        'SamplerState sampler_PointRepeat;',
        '_ParallaxNoiseMap.SampleGrad(',
        '_ParallaxMap.SampleBias(',
        'float _GlobalMipBias;',
        'float _GlobalMipBiasPow2;',
        'float4 _EndfieldCharSceneLightDirection;',
        'float _EndfieldCharSourceMainLightReady;',
        'clip(_EndfieldCharSourceMainLightReady - 0.5);',
        'float3 l = normalize(_EndfieldCharSceneLightDirection.xyz);',
        'float3 sourceBaseColor = lerp(',
        'float sourceMetallic = lerp(',
        'float sourceRoughness = lerp(',
        'float sourceOcclusion = mad(',
        '_RoughnessMax,',
        'mro.g);',
        'mro.b - 1.0,',
    ]
    failures = ["importer missing " + value for value in required_importer if value not in importer]
    failures += ["shader missing " + value for value in required_shader if value not in shader]
    forbidden_shader = [
        'float roughness = clamp(mro.r',
        'float metallic = saturate(mro.g)',
        '_ParallaxMap.SampleGrad(',
        '_ParallaxNoiseMap.SampleBias(',
        '_RecoveredParallaxCompatibilityScale',
        'normalize(float3(-0.35, 0.8, 0.45))',
    ]
    failures += ["shader retains disproven/fitted transport " + value
                 for value in forbidden_shader if value in shader]
    required_light_owner = [
        'Shader.PropertyToID("_EndfieldCharSourceMainLightReady")',
        'IsUsableDirectionalLight(sceneMainLight)',
        'mainLight == sceneMainLight',
        'sourceMainLightReady ? 1.0f : 0.0f',
        'Shader.SetGlobalFloat(SourceMainLightReadyId, 0.0f)',
    ]
    failures += ["source light owner missing " + value
                 for value in required_light_owner if value not in light_volume]
    required_runtime = [
        "endfield.endminf-liteffect-runtime-binding.v1",
        "TryValidateForRecoveryAudit",
        "TryValidateEndminfV2MarkerForRecoveryAudit",
        "sourceByRendererPathId.TryGetValue",
        "node.generatedRenderer != row.renderer",
        "node.materialPathIds[0] != row.materialPathId",
        "node.meshPathIds[0] != row.meshPathId",
        "node.resolvedSourceMaterials[0] != row.material",
        "node.resolvedSourceMeshes[0] != row.mesh",
        "ParticleSystemRenderMode.Mesh",
        "row.renderer.SetMeshes",
        "row.renderer.sharedMaterials",
        "if (!compatibility && !exactM27 && !liveHGBuffer &&",
    ]
    required_builder = [
        "Material01PathId = 0x5A6341E8A834E421L",
        "0xA531A88850690EB8UL",
        "0xAFCE491DD7BC5724UL",
        "0x8EC9950E5461C8D9UL",
        "rows.Count == 10 && material01Count == 7 && material38Count == 3",
        "renderer.enabled = false",
        "renderer.sharedMaterials = Array.Empty<Material>()",
        "ValidateSourceMaterial(material01, Material01PathId)",
        "ValidateSourceMaterial(material27, Material27PathId)",
        "ValidateSourceMaterial(material38, Material38PathId)",
        "HasSerializedMaterialProperty(",
        "TryValidateForRecoveryAudit(out string bindingFailure)",
        "TryValidateForRecoveryAudit(out string m27BindingFailure)",
    ]
    failures += ["runtime binding missing " + value for value in required_runtime if value not in runtime]
    try:
        validate_runtime_binding_source(runtime)
    except RuntimeBindingVerificationError as exc:
        failures.append(str(exc))
    failures += ["binding builder missing " + value for value in required_builder if value not in builder]
    forbidden_builder = [
        "ExpectedSha256",
        "626dc677675fea1a3a0f2f0079c9755455d37336cfe8cd682e3332669606f509",
        "b52f21342f56dd8b7801fe31217cc806a88553f5cba1cc688084dd229edcd38a",
        "696bf7dc65d7b4e4a591980ad95faeec80077faed0213ccc74ea5bc539eab8a7",
    ]
    failures += ["binding builder retains stale generated material hash " + value
                 for value in forbidden_builder if value in builder]
    failures += ["focused rebuild missing binding builder invocation"
                 for _ in [0] if "EndfieldEndminfLitEffectCompatibilityBindingBuilder.BuildAndValidate()" not in setup_source]
    failures += ["canonical Endminf launcher does not enable the retained LitEffect owners"
                 for _ in [0] if 'set "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1"' not in open_wrapper]
    required_lifecycle = [
        "StartRecoveredLegacyAnimations(",
        "animation.playAutomatically",
        "animation.Rewind(animation.clip.name)",
        "animation.Play(animation.clip.name)",
    ]
    failures += ["effect lifecycle missing " + value
                 for value in required_lifecycle if value not in spawner]
    forbidden_lifecycle = [
        "EndminfCompositeRockClipDelaySeconds",
        "PlayRecoveredLegacyAnimationAfterDelay",
    ]
    failures += ["effect lifecycle still contains capture-fitted delay " + value
                 for value in forbidden_lifecycle if value in spawner]

    resource_mapping_evidence = {
        "path": str(RESOURCE_MAPPING_REPORT.relative_to(ROOT)),
        "sha256": sha256(RESOURCE_MAPPING_REPORT),
        "current": False,
        "status": None,
    }
    try:
        fresh_mapping = build_resource_mapping_report()
        published_mapping = json.loads(
            RESOURCE_MAPPING_REPORT.read_text(encoding="utf-8")
        ) if RESOURCE_MAPPING_REPORT.is_file() else None
        mapping_is_current = (
            published_mapping is not None and
            canonical_json(published_mapping) == canonical_json(fresh_mapping)
        )
        resource_mapping_evidence["current"] = mapping_is_current
        resource_mapping_evidence["status"] = fresh_mapping.get("status")
        source_subgraph = (
            fresh_mapping.get("unityTransportPorts", {})
            .get("sourceProvenSubgraph", {})
        )
        mapping_valid = (
            mapping_is_current and
            fresh_mapping.get("schema") ==
                "endfield.endminf-liteffect-resource-mapping.v1" and
            fresh_mapping.get("status") ==
                "verified_with_selected_variant_material_offsets_and_consumer_gaps" and
            source_subgraph.get("mroChannels") == {
                "r": "metallic", "g": "roughness", "b": "occlusion"
            } and
            "_ParallaxNoiseMap.r" in source_subgraph.get("parallax", "") and
            "_ParallaxMap.g" in source_subgraph.get("parallax", "")
        )
        if not mapping_valid:
            failures.append(
                "fresh verified LitEffect resource mapping is absent or stale"
            )
    except (OSError, ValueError, ResourceMappingVerificationError) as error:
        resource_mapping_evidence["failure"] = str(error)
        failures.append("LitEffect resource mapping verification failed")

    asset_evidence = {}
    for name, (path, expected) in ASSETS.items():
        actual = sha256(path)
        asset_evidence[name] = {"path": str(path.relative_to(ROOT)), "sha256": actual,
                                "expectedSha256": expected,
                                "validated": actual is not None and
                                    (expected is None or actual == expected)}
        if actual is None or (expected is not None and actual != expected):
            failures.append(f"asset hash drifted {name}")
    material_source_evidence = {}
    for name, (source_path, expected_source_sha256) in SOURCE_MATERIALS.items():
        evidence, material_failures = validate_material_yaml(
            name,
            ASSETS[name][0],
            source_path,
            expected_source_sha256,
        )
        material_source_evidence[name] = evidence
        asset_evidence[name]["validated"] = bool(evidence.get("validated"))
        asset_evidence[name]["validationBasis"] = (
            "source hash and serialized material fields"
        )
        failures.extend(material_failures)

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
        "schema": "endfield.endminf-liteffect-visual-compatibility.v3",
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
        "resourceMappingEvidence": resource_mapping_evidence,
        "materialSourceEvidence": material_source_evidence,
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
                             "recovered texture identities", "hash-gated serialized colors/floats",
                             "fresh verified PackedBinding physical t0..t5 mapping artifact",
                             "fresh verified static sampler pairing",
                             "fresh verified metallic/roughness/occlusion stores in MRO R/G/B",
                             "fresh verified noise-height march then ParallaxMap.g sample",
                             "serialized CharInfo sceneMainLight direct-reference direction"],
        "approximated": ["converted PNG texture derivatives where native payloads are absent",
                         "forward BRDF and light intensity", "particle phase/brightness",
                         "HGBuffer/deferred replacement"],
        "measurementBoundary": "Restoring physical amber geometry is a completeness correction. Whole-frame ROI MAE is not an acceptance gate because this explicitly non-exact forward shader and the authored moving crystal occupy the compared pixels.",
        "failures": failures,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"], OUT)
    return 1 if failures else 0

if __name__ == "__main__": raise SystemExit(main())
