#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import verify_endfield_shader_archive as verifier


class ShaderArchiveVerificationTests(unittest.TestCase):
    def make_archive(self, root: Path, payload: bytes = b"DXBC-test") -> Path:
        session = root / "session"
        archive = session / "graphics" / "shaders"
        archive.mkdir(parents=True)
        digest = hashlib.sha256(payload).hexdigest()
        filename = f"{digest}-s4.dxbc"
        (archive / filename).write_bytes(payload)
        manifest = {
            "schema": "endfieldCapture.shaderArchive.v1",
            "registrations": [{
                "objectId": 123,
                "stage": 4,
                "identityHash": int(digest[:16], 16),
                "bytecodeSize": len(payload),
                "sha256": digest,
                "file": filename,
            }],
            "registrationCount": 1,
            "uniqueFileCount": 1,
            "uniqueBytes": len(payload),
            "complete": True,
        }
        (archive / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        return session

    def test_complete_archive_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = verifier.build_report(
                self.make_archive(Path(temporary))
            )
        self.assertEqual(report["status"], "validated")
        self.assertEqual(report["registrationCount"], 1)
        self.assertEqual(report["uniqueFileCount"], 1)

    def test_payload_corruption_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = self.make_archive(Path(temporary))
            payload = next((session / "graphics/shaders").glob("*.dxbc"))
            payload.write_bytes(b"corrupt")
            report = verifier.build_report(session)
        self.assertEqual(report["status"], "rejected")
        self.assertTrue(any("hash mismatch" in error for error in report["errors"]))

    def test_missing_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(verifier.VerificationError):
                verifier.build_report(Path(temporary))


if __name__ == "__main__":
    unittest.main()
