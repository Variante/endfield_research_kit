from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUNTIME_BINDING = HERE.parent / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldEndminfLitEffectCompatibilityBinding.cs"
)
RESOURCE_SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_liteffect_resource_mapping",
    HERE / "verify_endminf_liteffect_resource_mapping.py",
)
assert RESOURCE_SPEC and RESOURCE_SPEC.loader
RESOURCE_MODULE = importlib.util.module_from_spec(RESOURCE_SPEC)
sys.modules[RESOURCE_SPEC.name] = RESOURCE_MODULE
RESOURCE_SPEC.loader.exec_module(RESOURCE_MODULE)

SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_liteffect_visual_compatibility",
    HERE / "verify_endminf_liteffect_visual_compatibility.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EndminfLitEffectVisualCompatibilityTests(unittest.TestCase):
    def test_published_json_string_keys_equal_fresh_register_keys(self) -> None:
        fresh = {"physicalTextures": {0: "_BaseColorMap", 5: "_ParallaxNoiseMap"}}
        published = {
            "physicalTextures": {"0": "_BaseColorMap", "5": "_ParallaxNoiseMap"}
        }
        self.assertEqual(
            MODULE.canonical_json(published),
            MODULE.canonical_json(fresh),
        )

    def test_canonical_comparison_does_not_hide_value_drift(self) -> None:
        fresh = {"physicalTextures": {0: "_BaseColorMap"}}
        drifted = {"physicalTextures": {"0": "_NormalMap"}}
        self.assertNotEqual(
            MODULE.canonical_json(drifted),
            MODULE.canonical_json(fresh),
        )

    def test_material_contract_is_source_derived_not_generated_hash_pinned(self) -> None:
        builder = MODULE.BUILDER.read_text(encoding="utf-8")
        for stale_hash in (
            "626dc677675fea1a3a0f2f0079c9755455d37336cfe8cd682e3332669606f509",
            "b52f21342f56dd8b7801fe31217cc806a88553f5cba1cc688084dd229edcd38a",
            "696bf7dc65d7b4e4a591980ad95faeec80077faed0213ccc74ea5bc539eab8a7",
        ):
            self.assertNotIn(stale_hash, builder)
        self.assertIn("ValidateSourceMaterial(material01, Material01PathId)", builder)
        self.assertIn("SourceTextureFields", builder)
        self.assertIn("HasSerializedMaterialProperty(", builder)

    def test_source_material_fields_cover_all_used_stone_controls(self) -> None:
        self.assertTrue({
            "_BaseColorTintCover", "_BaseColorBrighterScale",
            "_NormalScale", "_RoughnessMin", "_RoughnessMax",
            "_OcclusionStrength", "_TwoSidedNormal", "_Metallic",
            "_BaseTextureMapCount",
            "_BaseUVSet", "_BasePbrMapUVSet", "_ParallaxMapUVType",
            "_ParallaxNoiseMapTilling", "_ParallaxFresnelStrength",
            "_ParallaxStrength", "_ParallaxTilling", "_ParallaxMarchNum",
            "_ParallaxMinBrightness", "_ParallaxIntensity",
        }.issubset(set(MODULE.SOURCE_FLOATS)))
        self.assertEqual(
            set(MODULE.SOURCE_COLORS),
            {"_BaseColor", "_ParallaxColor", "_ParallaxColorDark"},
        )

    def test_shader_uses_live_source_mip_and_material_decode(self) -> None:
        source = MODULE.SHADER.read_text(encoding="utf-8")
        for token in (
            "sampler_LinearClamp, baseUV, _GlobalMipBias",
            "sampler_LinearRepeat, pbrUV, _GlobalMipBias",
            "sampler_LinearMirror, pbrUV, _GlobalMipBias",
            "ddx_coarse(input.uv0) * _GlobalMipBiasPow2",
            "ddy_coarse(input.uv0) * _GlobalMipBiasPow2",
            "float3 sourceBaseColor = lerp(",
            "float sourceMetallic = lerp(",
            "float sourceOcclusion = mad(",
            "if (_TwoSidedNormal > 0.0 && !isFrontFace)",
        ):
            self.assertIn(token, source)
        self.assertNotIn("sampler_LinearClamp, baseUV, 0.0", source)
        self.assertNotIn("sampler_LinearRepeat, pbrUV, 0.0", source)

    def test_shader_uses_only_the_serialized_scene_light_direction(self) -> None:
        shader = MODULE.SHADER.read_text(encoding="utf-8")
        volume = MODULE.LIGHT_VOLUME.read_text(encoding="utf-8")
        for token in (
            "float4 _EndfieldCharSceneLightDirection;",
            "float _EndfieldCharSourceMainLightReady;",
            "clip(_EndfieldCharSourceMainLightReady - 0.5);",
            "float3 l = normalize(_EndfieldCharSceneLightDirection.xyz);",
        ):
            self.assertIn(token, shader)
        self.assertNotIn("normalize(float3(-0.35, 0.8, 0.45))", shader)
        for token in (
            'Shader.PropertyToID("_EndfieldCharSourceMainLightReady")',
            "IsUsableDirectionalLight(sceneMainLight)",
            "mainLight == sceneMainLight",
            "sourceMainLightReady ? 1.0f : 0.0f",
            "Shader.SetGlobalFloat(SourceMainLightReadyId, 0.0f)",
        ):
            self.assertIn(token, volume)

    def test_runtime_binding_rejoins_rows_to_the_exact_v2_source_marker(self) -> None:
        source = RUNTIME_BINDING.read_text(encoding="utf-8")
        validator = source[source.index(
            "public bool TryValidateForRecoveryAudit("
        ):source.index("public static bool Requested")]
        for token in (
            "contractSchema,",
            "ContractSchema,",
            "GetComponent<EndfieldRecoveredParticleEffectSource>()",
            "TryValidateEndminfV2MarkerForRecoveryAudit(",
            "sourceByRendererPathId.TryGetValue(",
            "node.generatedRenderer != row.renderer",
            "node.materialPathIds[0] != row.materialPathId",
            "node.meshPathIds[0] != row.meshPathId",
            "node.resolvedSourceMaterials[0] != row.material",
            "node.resolvedSourceMeshes[0] != row.mesh",
            "material01Count != 7",
            "material38Count != 3",
            "material27Count != 1",
            "admittedRendererIds.Contains(M27RendererPathId)",
        ):
            self.assertIn(token, validator)

    def test_runtime_validates_the_whole_binding_before_enabling_any_row(self) -> None:
        source = RUNTIME_BINDING.read_text(encoding="utf-8")
        on_enable = source[source.index("private void OnEnable()"):
                           source.index("public bool TryValidateForRecoveryAudit(")]
        self.assertLess(
            on_enable.index("TryValidateForRecoveryAudit("),
            on_enable.index("foreach (Row row in rows)"),
        )
        self.assertIn("return;", on_enable)
        self.assertEqual(on_enable.count("row.renderer.enabled = true;"), 1)

    def test_runtime_binding_restores_every_mutated_renderer_field(self) -> None:
        source = RUNTIME_BINDING.read_text(encoding="utf-8")
        MODULE.validate_runtime_binding_source(source)

    def test_runtime_binding_lifecycle_mutations_fail_closed(self) -> None:
        source = RUNTIME_BINDING.read_text(encoding="utf-8")
        attacks = (
            source.replace(
                "() => renderer.gameObject.layer = state.layer);",
                "() => renderer.gameObject.layer = ExactM27Layer);",
                1,
            ),
            source.replace(
                "() => renderer.SetMeshes(state.meshes, state.meshes.Length));",
                "() => renderer.SetMeshes(new[] { state.row.mesh }, 1));",
                1,
            ),
            source.replace(
                "() => renderer.sharedMaterials = state.sharedMaterials);",
                "() => renderer.sharedMaterials = new[] { state.row.material });",
                1,
            ),
            source.replace(
                "() => renderer.enabled = state.enabled);",
                "() => renderer.enabled = true);",
                1,
            ),
            source.replace(
                "() => renderer.enabled = state.enabled);",
                "() => renderer.enabled = state.enabled);\n"
                "                renderer.gameObject.layer = ExactM27Layer;",
                1,
            ),
            source.replace(
                "() => renderer.enabled = state.enabled);",
                "renderer.sortingFudge = 99f;\n"
                "                () => renderer.enabled = state.enabled);",
                1,
            ),
            source.replace(
                "CaptureRuntimeState(row);",
                "runtimeStates.Clear();",
                1,
            ),
            source.replace(
                "private void OnDisable()\n        {\n            RestoreRuntimeState();",
                "private void OnDisable()\n        {",
                1,
            ),
            source.replace(
                "private void OnDisable()\n        {\n"
                "            RestoreRuntimeState();\n        }",
                "private void OnDisable()\n        {\n"
                "            RestoreRuntimeState();\n"
                "            renderer.gameObject.layer = ExactM27Layer;\n"
                "        }",
                1,
            ),
        )
        for mutated in attacks:
            self.assertNotEqual(mutated, source, "test mutation did not alter C#")
            with self.assertRaises(MODULE.RuntimeBindingVerificationError):
                MODULE.validate_runtime_binding_source(mutated)


if __name__ == "__main__":
    unittest.main()
