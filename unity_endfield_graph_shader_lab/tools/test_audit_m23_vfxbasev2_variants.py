#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_m23_vfxbasev2_variants.py")
SPEC = importlib.util.spec_from_file_location("audit_m23_vfxbasev2_variants", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class M23VfxBaseV2VariantTests(unittest.TestCase):
    def test_current_export_has_two_exact_keyword_pairs_and_no_stock_fit(self) -> None:
        report = M.build_report(M.DEFAULT_ROOT)
        self.assertEqual(report["status"], "pass", report["failures"])
        self.assertEqual(report["summary"]["d3d11Pairs"], 1358)
        self.assertEqual(report["summary"]["targetPairs"], 2)
        self.assertEqual(report["summary"]["targetCompatiblePairs"], 0)
        targets = {row["sidecarIndex"]: row for row in report["targetPairs"]}
        self.assertEqual(targets[138]["sourceBlobIndex"], 1277)
        self.assertEqual(targets[4212]["sourceBlobIndex"], 1956)
        self.assertNotIn("SRP_INSTANCING_ON", targets[138]["keywords"])
        self.assertIn("SRP_INSTANCING_ON", targets[4212]["keywords"])

    def test_empty_variant_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = M.build_report(Path(temporary))
        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["failures"])


if __name__ == "__main__":
    unittest.main()
