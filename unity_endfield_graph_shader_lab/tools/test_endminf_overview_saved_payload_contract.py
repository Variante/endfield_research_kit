#!/usr/bin/env python3
"""Source contract for Endminf's post-save native particle verification."""

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORTER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfOverviewEffectImporter.cs"
)
ANIMATION_IMPORTER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfEffectAnimationImporter.cs"
)
STAGE = ROOT / (
    "scratch/character_recovery/endminf_external_fx_rig/"
    "exact_four_root_stage"
)
ANIMATION_ROOT = ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/"
    "Effects/Overview/Animation"
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
            "ValidateGenerated(gos, transforms, systems, renderers, context);",
            animation,
        )
        self.assertLess(animation, validate)

    def test_saved_gate_identity_joins_all_game_objects_and_transforms(self) -> None:
        start = self.source.index(
            "private static void VerifySavedHierarchySourcePayloads("
        )
        end = self.source.index(
            "private static void VerifySavedSourcePayloads(", start
        )
        body = self.source[start:end]
        for token in (
            "gameObjects.TryGetValue(",
            "row.gameObjectPathId",
            "transforms.TryGetValue(",
            "row.transformPathId",
            'L.PPtrId(sourceTransform["m_GameObject"])',
            'sourceTransform["m_Father"]',
            'L.Str(sourceGameObject, "m_Name")',
            'L.Int(sourceGameObject, "m_Layer")',
            'L.Vector3Value(sourceTransform["m_LocalPosition"])',
            'L.QuaternionValue(sourceTransform["m_LocalRotation"])',
            'L.Vector3Value(sourceTransform["m_LocalScale"])',
        ):
            self.assertIn(token, body)
        self.assertIn(
            "consumedGameObjects.Count == gameObjects.Count", self.source
        )
        self.assertIn(
            "consumedTransforms.Count == transforms.Count", self.source
        )

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

    def test_renderer_sorting_fudge_alias_is_explicit_and_complete(self) -> None:
        rows = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (STAGE / "ParticleSystemRenderer").glob("*.json")
        ]
        self.assertEqual(len(rows), 70)
        self.assertTrue(all(
            float(row["m_RendererSortingFudge"]) ==
            float(row["m_SortingFudge"])
            for row in rows
        ))
        self.assertEqual(
            sum(float(row["m_SortingFudge"]) == 4.0 for row in rows), 3
        )
        self.assertIn(
            'safeRenderer.Remove("m_RendererSortingFudge")', self.source
        )
        self.assertIn(
            'safeRenderer["m_SortingFudge"] = unitySortingFudge;', self.source
        )

    def test_effect_animation_source_and_semantic_contract_are_pinned(self) -> None:
        animation_source = ANIMATION_IMPORTER.read_text(encoding="utf-8")
        expected = {
            STAGE / "AnimationClip/A_actor_endminf_ui_overview_02_p910F78E15CD34301.json":
                "22c191d15ea18dc2d890b9c6e4411e8e2985c6ea5fd6db96263b499e3d86a70d",
            STAGE / "AnimationClip/A_fx_endminf_ui_overview_04_pDB8EF20719226683.json":
                "220ae359098e5a843afdced4680265e3eead2aba79b926988c5ba46ae6d42e6f",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            self.assertIn(f'"{digest}"', animation_source)
        self.assertGreaterEqual(
            animation_source.count("ValidateExactAnimationEvidence();"), 2
        )
        self.assertNotIn("RigAnimSha256", animation_source)
        self.assertNotIn("RocksAnimSha256", animation_source)
        for token in (
            "endminf_effect_animation_source_curve_contract.json",
            "ValidateSemanticClip(",
            "AnimationUtility.GetCurveBindings(clip)",
            "AnimationUtility.GetEditorCurve(",
            "HashCurveTimeValues(curve)",
            "ValidateSourceDerivedTangents(",
        ):
            self.assertIn(token, animation_source)

    def test_shape_texture_boundary_does_not_claim_native_bc7_identity(self) -> None:
        self.assertIn(
            "hash-pinned decoded PNG content plus", self.source
        )
        self.assertIn(
            "does not claim native BC7 bytes or platform compression identity",
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
