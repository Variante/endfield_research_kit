#!/usr/bin/env python3
"""Contract for retaining exact suikuai (1) across focused actor rebuilds."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfOverviewEffectBindingBuilder.cs"
)
IMPORTER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfOverviewEffectImporter.cs"
)
VIEWER_CAPTURE = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfViewerPlayModeCapture.cs"
)


class EndminfSuikuaiBindingRepairContractTests(unittest.TestCase):
    def test_focused_actor_binding_repairs_exact_suikuai_first(self) -> None:
        source = BUILDER.read_text(encoding="utf-8")
        method = source.index("public static void BuildAndValidate()")
        repair = source.index(".RebuildAndValidateSuikuai1Material();", method)
        actor_load = source.index("PrefabUtility.LoadPrefabContents(Actor)", method)
        self.assertLess(repair, actor_load)
        self.assertIn("pinned suikuai (1) source material", source[method:repair])

    def test_targeted_repair_remains_fully_fail_closed(self) -> None:
        source = IMPORTER.read_text(encoding="utf-8")
        method = source.index("public static void RebuildAndValidateSuikuai1Material()")
        integration = source.index("private static void IntegrateSuikuai1RetainedRenderer", method)
        body = source[method:integration]
        for token in (
            "ValidateSuikuai1ShaderContract(shader)",
            "ValidateSuikuai1SourceMaterial(source, row)",
            "Pinned suikuai (1) BlendTex asset is missing",
            "ValidateSuikuai1ImportedMaterial(material)",
            "IntegrateSuikuai1RetainedRenderer(material)",
        ):
            self.assertIn(token, body)

    def test_targeted_integration_accepts_only_the_known_stale_boundary(self) -> None:
        source = IMPORTER.read_text(encoding="utf-8")
        integration = source.index("private static void IntegrateSuikuai1RetainedRenderer")
        validation = source.index("Retained Endminf suikuai (1) admission boundary drifted", integration)
        body = source[integration:validation]
        self.assertIn("bool staleFailClosedBoundary", body)
        self.assertIn("sourceRow.sourceRendererEnabled", body)
        self.assertIn("sourceRow.rendererFailClosedForUnrecoveredShader", body)
        self.assertIn("renderer.sharedMaterials.Length == 0", body)
        self.assertIn("!renderer.enabled", body)
        self.assertIn(
            "preIntegrationBoundary || integratedBoundary ||\n"
            "                    staleFailClosedBoundary",
            body,
        )

    def test_viewer_verifies_the_exact_eleven_row_family_and_suikuai(self) -> None:
        source = VIEWER_CAPTURE.read_text(encoding="utf-8")
        self.assertIn("endfield.endminf-viewer-playmode-sequence.v13", source)
        for token in (
            "firstEntranceFrame.litEffectBindingRowCount == 11",
            "firstEntranceFrame.primaryRockFamily.Length == 11",
            "litEffectM01Count == 7",
            "litEffectM38Count == 3",
            "litEffectM27Count == 1",
            "firstEntranceFrame.exactSuikuai1BindingReady",
            "renderer.meshCount != 4",
            "material.name == ExactSuikuai1MaterialName",
            "material.shader.name == ExactRefractShader",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
