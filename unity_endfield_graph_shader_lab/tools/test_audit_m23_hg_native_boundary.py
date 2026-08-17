#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_m23_hg_native_boundary.py")
SPEC = importlib.util.spec_from_file_location("audit_m23_hg_native_boundary", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class M23HgNativeBoundaryTests(unittest.TestCase):
    def test_pinned_installed_unityplayer_passes_without_packer_admission(self) -> None:
        report = M.audit(M.DEFAULT_UNITY_PLAYER)
        self.assertEqual(report["status"], "pass", report["failures"])
        self.assertTrue(report["admission"]["hgParticleNativeTypeIdentified"])
        self.assertFalse(report["admission"]["hgParticlePackerResolved"])
        self.assertFalse(report["initializer"]["vertexOrConstantBufferProducer"])

    def test_non_pe_input_fails_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "UnityPlayer.dll"
            path.write_bytes(b"not a PE")
            with self.assertRaisesRegex(ValueError, "not a PE"):
                M.audit(path)


if __name__ == "__main__":
    unittest.main()
