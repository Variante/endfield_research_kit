#!/usr/bin/env python3
"""Focused tests for the current CharacterNPR_Skin source-boundary audit."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import verify_current_character_npr_skin_export as audit


class CurrentCharacterNprSkinExportTests(unittest.TestCase):
    def test_current_boundary_is_source_closed_without_claiming_parity(self) -> None:
        result = audit.verify_current_boundary()
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["compiled_variants"]["forward_lit_unique_keyword_sets"], 141
        )
        self.assertEqual(
            result["compiled_variants"]["forward_lit_sets_without_screen_shadow_mask"],
            0,
        )
        self.assertEqual(
            result["binary_consumer"]["shadow_equations"]["character_shadow"],
            "G",
        )
        self.assertEqual(
            result["binary_consumer"]["shadow_equations"]["character_shadow_minimum"],
            "min(G, alpha, material-shadow-sample)",
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
