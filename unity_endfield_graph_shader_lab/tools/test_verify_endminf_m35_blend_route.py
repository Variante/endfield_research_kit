from __future__ import annotations

import unittest
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
SHADER = (LAB / "Assets/EndfieldGraphShaderLab/Shaders/Recovered"
          / "EndfieldZhuangfyVFXBaseV2MRT.shader")
MATERIAL = (LAB / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable"
            / "Endminf/Effects/Overview/Materials"
            / "M_fx_endminm_gfx_35_p75854801AE9519E8.mat")


class M35BlendRouteTests(unittest.TestCase):
    def test_material_authors_sample2_as_the_only_blend_carrier(self) -> None:
        text = MATERIAL.read_text(encoding="utf-8")
        self.assertIn("- _SampleTex0UseWeight4: 0", text)
        self.assertIn("- _SampleTex2UseWeight4: 1", text)
        self.assertIn("- _UseBlend: 1", text)

    def test_three_sample_specialization_routes_sample2_to_blend(self) -> None:
        text = SHADER.read_text(encoding="utf-8")
        branch = text.index(
            "#if defined(_SAMPLE_TEX2) && !defined(_SAMPLE_TEX3)")
        fallback = text.index("#else", branch)
        scoped = text[branch:fallback]
        self.assertIn("remappedSample2Alpha * sample2UseWeight4", scoped)
        self.assertIn("remappedSample2Color * sample2UseWeight4", scoped)
        self.assertNotIn("remappedSample0Alpha * sample0UseWeight4", scoped)


if __name__ == "__main__":
    unittest.main()
