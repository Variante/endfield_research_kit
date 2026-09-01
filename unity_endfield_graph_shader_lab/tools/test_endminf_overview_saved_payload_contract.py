#!/usr/bin/env python3
"""Source contract for Endminf's post-save native particle verification."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORTER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfOverviewEffectImporter.cs"
)


class EndminfOverviewSavedPayloadContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = IMPORTER.read_text(encoding="utf-8")

    def test_saved_payload_gate_runs_after_effect_animation_rebuild(self) -> None:
        build = self.source.index("public static void BuildAndValidate()")
        animation = self.source.index(
            "EndfieldEndminfEffectAnimationImporter.BuildAndValidate();", build
        )
        validate = self.source.index(
            "ValidateGenerated(systems, renderers, context);", animation
        )
        self.assertLess(animation, validate)

    def test_saved_gate_identity_joins_source_rows_to_direct_components(self) -> None:
        start = self.source.index("private static void VerifySavedSourcePayloads(")
        end = self.source.index("private static bool ValidateMoveWithTransform(", start)
        body = self.source[start:end]
        for token in (
            "systems.TryGetValue(",
            "node.particleSystemPathId",
            "renderers.TryGetValue(",
            "node.particleRendererPathId",
            'L.PPtrId(sourceSystem["m_GameObject"])',
            'L.PPtrId(sourceRenderer["m_GameObject"])',
            "node.generatedParticleSystem",
            "node.generatedRenderer",
            "VerifyFullParticlePayload(",
            "VerifyFullRendererPayload(",
        ):
            self.assertIn(token, body)

    def test_safe_payload_helpers_are_shared_by_import_and_saved_gate(self) -> None:
        self.assertGreaterEqual(self.source.count("BuildSafeParticlePayload("), 3)
        self.assertGreaterEqual(self.source.count("BuildSafeRendererPayload("), 3)
        self.assertGreaterEqual(self.source.count("VerifyFullParticlePayload("), 3)
        self.assertGreaterEqual(self.source.count("VerifyFullRendererPayload("), 3)

    def test_renderer_excludes_only_intentional_dependency_overrides(self) -> None:
        safe_start = self.source.index(
            "private static Dictionary<string, object> BuildSafeRendererPayload("
        )
        verify_start = self.source.index(
            "private static void VerifyFullRendererPayload(", safe_start
        )
        safe_body = self.source[safe_start:verify_start]
        self.assertIn('safeRenderer.Remove("m_Materials")', safe_body)
        self.assertIn('key.StartsWith(\n                    "m_Mesh"', safe_body)
        self.assertNotIn('safeRenderer.Remove("m_Enabled")', safe_body)

        saved_start = verify_start
        saved_end = self.source.index("private static void ValidateGenerated(", saved_start)
        saved_body = self.source[saved_start:saved_end]
        self.assertEqual(saved_body.count('expected.Remove("m_Enabled")'), 1)
        self.assertNotIn('expected.Remove("m_RenderMode")', saved_body)


if __name__ == "__main__":
    unittest.main()
