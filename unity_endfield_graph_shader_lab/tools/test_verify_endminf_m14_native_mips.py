#!/usr/bin/env python3
"""Focused tests for the exact Endminf M14 native mip verifier."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_endminf_m14_native_mips.py")
SPEC = importlib.util.spec_from_file_location("verify_endminf_m14_native_mips", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class VerifyEndminfM14NativeMipsTests(unittest.TestCase):
    def make_project(self, temporary: str) -> Path:
        project = Path(temporary)
        source_root = MODULE.PROJECT / MODULE.RELATIVE_ROOT
        target_root = project / MODULE.RELATIVE_ROOT
        target_root.mkdir(parents=True)
        for name in (
            MODULE.STEM,
            MODULE.STEM + ".meta",
            MODULE.STEM + ".manifest.json",
            MODULE.STEM + ".manifest.json.meta",
        ):
            shutil.copyfile(source_root / name, target_root / name)
        importer = project / MODULE.IMPORTER
        importer.parent.mkdir(parents=True)
        shutil.copyfile(MODULE.PROJECT / MODULE.IMPORTER, importer)
        return project

    def test_accepts_pinned_payload_manifest_metas_and_importer(self):
        result = MODULE.verify(MODULE.PROJECT)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["payloadSha256"], MODULE.EXPECTED_SHA256)
        self.assertEqual(len(result["forceTrack"]), 4)

    def test_rejects_payload_and_manifest_that_drift_together(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = self.make_project(temporary)
            root = project / MODULE.RELATIVE_ROOT
            payload_path = root / MODULE.STEM
            data = bytearray(payload_path.read_bytes())
            data[123] ^= 0x80
            payload_path.write_bytes(data)
            manifest_path = root / (MODULE.STEM + ".manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["payload"]["sha256"] = MODULE.sha256(payload_path)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError, "manifest SHA-256 drifted"):
                MODULE.verify(project)

    def test_rejects_mip_offset_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = self.make_project(temporary)
            manifest_path = project / MODULE.RELATIVE_ROOT / (MODULE.STEM + ".manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["payload"]["mipDimensions"][4]["offset"] += 16
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError, "BC7 mip layout drifted"):
                MODULE.verify(project)

    def test_rejects_payload_filename_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = self.make_project(temporary)
            manifest_path = project / MODULE.RELATIVE_ROOT / (MODULE.STEM + ".manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["payload"]["file"] = "../" + MODULE.STEM
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError, "escaped its root"):
                MODULE.verify(project)

    def test_rejects_missing_force_tracked_meta(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = self.make_project(temporary)
            (project / MODULE.RELATIVE_ROOT / (MODULE.STEM + ".meta")).unlink()
            with self.assertRaisesRegex(MODULE.VerificationError, "missing force-tracked M14 meta"):
                MODULE.verify(project)

    def test_rejects_importer_without_reloaded_raw_byte_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = self.make_project(temporary)
            importer_path = project / MODULE.IMPORTER
            importer = importer_path.read_text(encoding="utf-8")
            importer_path.write_text(
                importer.replace("loaded.GetRawTextureData()", "Array.Empty<byte>()"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MODULE.VerificationError, "lost fail-closed witness"):
                MODULE.verify(project)


if __name__ == "__main__":
    unittest.main()
