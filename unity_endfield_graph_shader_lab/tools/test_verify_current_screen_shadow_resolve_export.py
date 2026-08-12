#!/usr/bin/env python3
"""Focused tests for the current original screen-shadow resolve audit."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import verify_current_screen_shadow_resolve_export as audit


class CurrentScreenShadowResolveExportTests(unittest.TestCase):
    def test_current_boundary_pins_character_g_producer_without_parity_claim(self) -> None:
        result = audit.verify_current_boundary()
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["character_metadata"]["pass"],
            "ScreenSpaceShadowResolve_Character",
        )
        self.assertEqual(
            result["character_g_producer"]["g_channel"]["filter"],
            "16 GatherRed taps with depth comparison",
        )
        self.assertEqual(result["interpretation"]["retail_frame_parity"], "not asserted")

    def test_missing_artifact_reports_path_and_expected_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.spv"
            with self.assertRaisesRegex(
                AssertionError,
                r"missing test sidecar: .*missing\.spv",
            ):
                audit.require_file(missing, 12, "0" * 64, "test sidecar")


if __name__ == "__main__":
    unittest.main()
