from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_liteffect_subprograms.py"
SPEC = importlib.util.spec_from_file_location("verify_endminf_liteffect_subprograms", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class LitEffectSubprogramVerifierTests(unittest.TestCase):
    def _row(self, filename: str = "sample.dxbc") -> dict:
        payload = b"sample shader bytes"
        import hashlib

        return {
            "fileName": filename,
            "encoding": "DXBC",
            "stage": "vertex",
            "serializedStage": "vertex",
            "decodedStage": "vertex",
            "sourceOffset": 32,
            "sourceSize": len(payload),
            "rawSourceOffset": 32,
            "rawSourceSize": len(payload),
            "byteCount": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "shaderCab": MODULE.EXPECTED_SHADER["cab"],
            "shaderPathId": MODULE.EXPECTED_SHADER["pathId"],
            "shaderName": MODULE.EXPECTED_SHADER["name"],
            "shaderSourceOriginalPath": MODULE.EXPECTED_SOURCE["path"],
            "shaderLOD": 600,
            "subShaderIndex": 0,
            "passIndex": 0,
            "passName": "HGBuffer",
            "subProgramIndex": 0,
            "programBlobIndex": 0,
            "platform": "d3d11",
            "programType": "EndfieldD3D11",
            "programTypeValue": 33,
            "shaderHardwareTier": -1,
            "keywords": ["_PARALLAX_MAP"],
            "localKeywords": [],
        }

    def test_valid_entry_checks_payload_length_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sample.dxbc").write_bytes(b"sample shader bytes")
            row = MODULE._validate_entry(self._row(), root, 0)
            self.assertEqual(row["decodedStage"], "vertex")

    def test_missing_source_offset_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sample.dxbc").write_bytes(b"sample shader bytes")
            row = self._row()
            del row["sourceOffset"]
            with self.assertRaisesRegex(MODULE.VerificationError, "missing fields sourceOffset"):
                MODULE._validate_entry(row, root, 0)

    def test_source_alias_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sample.dxbc").write_bytes(b"sample shader bytes")
            row = self._row()
            row["rawSourceSize"] += 1
            with self.assertRaisesRegex(MODULE.VerificationError, "rawSourceSize"):
                MODULE._validate_entry(row, root, 0)

    def test_payload_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sample.dxbc").write_bytes(b"changed bytes")
            with self.assertRaisesRegex(MODULE.VerificationError, "byteCount|SHA-256"):
                MODULE._validate_entry(self._row(), root, 0)

    def test_evidence_contains_no_raw_program_field(self) -> None:
        evidence = {
            "schema": "endfield.endminf-liteffect-subprogram-evidence.v1",
            "status": "verified",
            "manifest": {"sha256": "manifest", "entryCount": 2240},
            "source": {"sha256": "source"},
            "toolchain": {"animestudioSubmoduleCommit": "commit"},
        }
        self.assertNotIn("rawProgramBytes", json.dumps(evidence))

    def test_stale_cli_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            stale_cli = Path(temp) / "AnimeStudio.CLI.exe"
            stale_cli.write_bytes(b"stale")
            with self.assertRaisesRegex(MODULE.VerificationError, "stale CLI"):
                MODULE.verify(cli_path=stale_cli, evidence_path=None)

    def test_stale_submodule_fails_closed(self) -> None:
        original = MODULE.EXPECTED_SUBMODULE_COMMIT
        MODULE.EXPECTED_SUBMODULE_COMMIT = "0" * 40
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "submodule commit"):
                MODULE.verify(evidence_path=None)
        finally:
            MODULE.EXPECTED_SUBMODULE_COMMIT = original

    def test_stale_manifest_fails_closed(self) -> None:
        original = MODULE.EXPECTED_MANIFEST_SHA256
        MODULE.EXPECTED_MANIFEST_SHA256 = "f" * 64
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "stale manifest"):
                MODULE._validate_manifest(MODULE.DEFAULT_MANIFEST)
        finally:
            MODULE.EXPECTED_MANIFEST_SHA256 = original

    def test_stale_source_fails_closed(self) -> None:
        original = MODULE.EXPECTED_SOURCE["path"]
        MODULE.EXPECTED_SOURCE["path"] = r"D:\missing\stale-source.chk"
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "shader source path"):
                MODULE._check_source(original)
        finally:
            MODULE.EXPECTED_SOURCE["path"] = original


if __name__ == "__main__":
    unittest.main()
