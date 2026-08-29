#!/usr/bin/env python3
"""Focused source contract for the recovered Endminf bloom layout."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
CAPTURE = ROOT / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfViewerPlayModeCapture.cs"


class EndminfBloomLayoutContractTests(unittest.TestCase):
    def test_first_mip_is_half_source_with_1080_height_cap(self) -> None:
        source = PIPELINE.read_text(encoding="utf-8")
        start = source.index("private int BuildRecoveredSceneBloomPyramid")
        end = source.index("private void LogRecoveredBloomGraphOnce", start)
        method = source[start:end]
        self.assertIn("Mathf.Min(\n                0.5f,", method)
        self.assertIn("RecoveredBloomHeightCap / Mathf.Max(sourceHeight, 1)", method)
        self.assertIn("float mipScale = 1.0f / Mathf.Pow(2.0f, i);", method)
        self.assertNotIn("float mipScale = 0.5f /", method)

        def layout(width: int, height: int) -> tuple[int, int, int]:
            scale = min(0.5, 1080.0 / max(height, 1))
            working_width = max(1, round(width * scale))
            working_height = max(1, round(height * scale))
            iterations = max(1, min(16, (max(working_width, working_height).bit_length() - 1) - 2))
            return working_width, working_height, iterations

        self.assertEqual(layout(3840, 2160), (1920, 1080, 8))
        self.assertEqual(layout(1920, 1080), (960, 540, 7))

    def test_capture_reports_and_gates_live_dimensions(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("public int endminfBloomWidth;", source)
        self.assertIn("public int endminfBloomHeight;", source)
        self.assertIn("LastRecoveredEndminfBloomWidth", source)
        self.assertIn("LastRecoveredEndminfBloomHeight", source)
        self.assertIn("half-source Endminf Uber bloom dimensions", source)


if __name__ == "__main__":
    unittest.main()
