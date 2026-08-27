from pathlib import Path
import re
import unittest


LAB_ROOT = Path(__file__).parents[1]
DIAGNOSTIC = (
    LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" /
    "CharacterRecovery" / "EndfieldEndminfRetainedSkinningDiagnostic.cs"
)
CAPTURE = (
    LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" /
    "CharacterRecovery" / "EndfieldEndminfViewerPlayModeCapture.cs"
)


class EndminfRetainedSkinningDiagnosticTests(unittest.TestCase):
    def test_probe_bakes_without_mutating_beauty_renderer(self) -> None:
        source = DIAGNOSTIC.read_text(encoding="utf-8")
        self.assertIn("renderer.BakeMesh(baked, false);", source)
        self.assertIn("renderer.localToWorldMatrix", source)
        self.assertNotIn("renderer.enabled =", source)
        self.assertNotIn("renderer.sharedMesh =", source)
        self.assertIsNone(re.search(r"renderer\.bones\s*=(?!=)", source))
        self.assertIn("renderer.isVisible", source)

    def test_probe_records_pose_bindpose_and_both_palette_spaces(self) -> None:
        source = DIAGNOSTIC.read_text(encoding="utf-8")
        self.assertIn("bone.localToWorldMatrix", source)
        self.assertIn("source.bindposes", source)
        self.assertIn("Matrix4x4 worldSkin = boneToWorld * bindpose;", source)
        self.assertIn("Matrix4x4 localSkin = worldToRenderer * worldSkin;", source)
        self.assertIn("bakedWorldVertexChecksumFnv1a64", source)
        self.assertIn("sampledWorldPositions", source)

    def test_capture_is_explicit_and_requested_time_scoped(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("ENDFIELD_ENDMINF_CAPTURE_RETAINED_SKINNING", source)
        self.assertIn("public static void RunRetainedSkinningDiagnostic()", source)
        self.assertIn("requires explicit requested", source)
        self.assertIn(
            "EndfieldEndminfRetainedSkinningDiagnostic.Capture(actor)", source)


if __name__ == "__main__":
    unittest.main()
