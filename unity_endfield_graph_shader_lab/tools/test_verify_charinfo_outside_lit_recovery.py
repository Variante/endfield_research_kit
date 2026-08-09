#!/usr/bin/env python3
"""Focused tests for SphereOutside recovery validator diagnostics."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "verify_charinfo_outside_lit_recovery.py"
)
MODULE_SPEC = importlib.util.spec_from_file_location(
    "verify_charinfo_outside_lit_recovery",
    MODULE_PATH,
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"cannot load verifier module: {MODULE_PATH}")
verifier = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(verifier)


class UnityLogEvidenceTests(unittest.TestCase):
    def test_exact_pinned_log_passes_without_semantic_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unity.log"
            path.write_text("exact pinned log", encoding="utf-8")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                verifier.require_unity_log(path, expected, ["not required"])
            self.assertEqual(output.getvalue(), "")

    def test_rerun_log_requires_all_semantic_success_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unity.log"
            path.write_text(
                "Verifier.BuildAndValidate\nreport written\nreturn code 0\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                verifier.require_unity_log(
                    path,
                    "0" * 64,
                    ["Verifier.BuildAndValidate", "report written", "return code 0"],
                )
            message = output.getvalue()
            self.assertIn("semantic gate passed", message)
            self.assertIn("pinned=" + "0" * 64, message)

    def test_rerun_log_reports_the_missing_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unity.log"
            path.write_text("Verifier.BuildAndValidate\n", encoding="utf-8")
            with self.assertRaisesRegex(
                AssertionError,
                "missing token 'return code 0'",
            ):
                verifier.require_unity_log(
                    path,
                    "0" * 64,
                    ["Verifier.BuildAndValidate", "return code 0"],
                )


if __name__ == "__main__":
    unittest.main()
