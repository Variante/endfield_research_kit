import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredCharInfoPresentation.cs"
)
SHADER = ROOT / "Assets/EndfieldGraphShaderLab/Shaders/ReferenceBackdrop.shader"


class EndminfBackdropContractTests(unittest.TestCase):
    def test_endminf_plate_uses_measured_neutral_grade(self):
        source = PRESENTATION.read_text(encoding="utf-8")
        for token in (
            "new Color(0.61f, 0.61f, 0.605f, 1.0f)",
            "new Color(0.85f, 0.85f, 0.845f, 1.0f)",
            '"_BottomVignette", 0.58f',
            '"_BottomVignetteFloor", 0.13f',
            '"_BottomVignetteHeight", 0.27f',
        ):
            self.assertIn(token, source)

    def test_bottom_rolloff_is_screen_space_not_actor_bounds_uv(self):
        source = SHADER.read_text(encoding="utf-8")
        self.assertIn("o.screenPos = ComputeScreenPos(o.pos);", source)
        self.assertIn(
            "float2 screenUv = i.screenPos.xy / max(i.screenPos.w, 1.0e-6);",
            source,
        )
        self.assertIn("screenUv.y)) *", source)
        self.assertNotIn("0.02, max(_BottomVignetteHeight", source)


if __name__ == "__main__":
    unittest.main()
