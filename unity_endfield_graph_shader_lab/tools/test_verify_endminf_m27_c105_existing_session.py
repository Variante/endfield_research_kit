from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("verify_endminf_m27_c105_existing_session.py")
SPEC = importlib.util.spec_from_file_location("m27_c105_existing_session_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExistingSessionAuthorityTests(unittest.TestCase):
    def make_contract(self, root: Path) -> Path:
        path = root / "contract.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "endfield.charinfo.endminf-anchor-wave-bright-contract.v1",
                    "nativeContractClosed": True,
                    "selectedFrameValueClosed": False,
                    "safeToInventSelectedFrameValue": False,
                    "nativeGate": {
                        "status": "validated",
                        "gameAssembly": {"sha256": MODULE.EXPECTED_GAME_ASSEMBLY_SHA256},
                        "globalMetadata": {"sha256": MODULE.EXPECTED_METADATA_SHA256},
                    },
                    "getterContract": {
                        "value": [
                            "m_anchorPosition.x",
                            "m_anchorPosition.y",
                            "m_anchorRadius",
                            "m_anchorBrightIntensity * (m_anchorBrightFlag ? 1.0 : 0.0)",
                        ]
                    },
                    "shaderVariablesGlobalPublisher": {
                        "method": "HG.Rendering.Runtime.HGRenderPathBase.UpdateShaderVariablesGlobalVFX",
                        "destinationByteOffset": "0x690",
                        "destinationRegister": "c105",
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def make_session(self, root: Path) -> tuple[Path, Path, dict[str, str]]:
        session = {
            "schema": "endfieldCapture.session.v1",
            "sessionId": MODULE.EXPECTED_SESSION_ID,
            "numericSessionId": MODULE.EXPECTED_NUMERIC_SESSION_ID,
            "providers": 1,
            "graphicsProfile": "targeted",
            "evidenceLabel": "forced-d3d11",
            "gameBuild": MODULE.EXPECTED_GAME_BUILD,
            "targetSha256": MODULE.EXPECTED_TARGET_SHA256,
        }
        (root / "session.json").write_text(json.dumps(session), encoding="utf-8")
        status = {
            "schema": "endfieldCapture.runtimeStatus.v1",
            "runtimeMode": "d3d11-proxy",
            "graphicsSelected": True,
            "graphicsProfile": "targeted",
            "graphicsHooksInstalled": True,
            "graphicsAttached": True,
            "graphicsSequenceFrames": 49,
            "graphicsDropped": 0,
            "framePending": False,
            "frameCompleted": True,
            "frameIncomplete": False,
            "frameFailed": False,
        }
        (root / "runtime.status.json").write_text(json.dumps(status), encoding="utf-8")
        (root / "collected").mkdir()
        (root / "collected" / "summary.json").write_text(
            json.dumps(
                {
                    "schema": "endfieldCapture.summary.v1",
                    "complete": True,
                    "dropped": 0,
                    "invalidRecords": 0,
                    "writerError": False,
                }
            ),
            encoding="utf-8",
        )
        metadata_path = root / MODULE.METADATA_RELATIVE_PATH
        metadata_path.parent.mkdir(parents=True)
        payload = b"\0" * (106 * 16)
        draw = {
            "count": MODULE.EXPECTED_INDEX_COUNT,
            "instanceCount": MODULE.EXPECTED_INSTANCE_COUNT,
            "indexedInstanced": True,
            "priorityShaderPair": True,
            "priorityM27Geometry": True,
            "startInstance": 0,
            "shaders": [
                {
                    "stage": 0,
                    "identityHash": MODULE.EXPECTED_VERTEX_IDENTITY,
                    "bytecodeSize": MODULE.EXPECTED_VERTEX_BYTES,
                },
                {
                    "stage": 4,
                    "identityHash": MODULE.EXPECTED_PIXEL_IDENTITY,
                    "bytecodeSize": MODULE.EXPECTED_PIXEL_BYTES,
                },
            ],
            "constantBuffers": [
                {
                    "stage": 4,
                    "slot": 1,
                    "firstConstant": 4432,
                    "numConstants": 208,
                    "capturedConstants": 106,
                    "truncated": True,
                    "rangeValid": True,
                    "metadataValid": True,
                    "dataHex": payload.hex(),
                }
            ],
        }
        metadata_path.write_text(
            json.dumps(
                {
                    "frame": MODULE.EXPECTED_FRAME,
                    "captureIncomplete": False,
                    "captureFailed": False,
                    "drawRecordsTruncated": False,
                    "resourceSelectionTruncated": False,
                    "droppedEvents": 0,
                    "readbackHresult": 0,
                    "readbackFailure": 0,
                    "drawRecords": [draw],
                }
            ),
            encoding="utf-8",
        )
        for relative, data in (
            (MODULE.RUNTIME_RELATIVE_PATH, b"archived proxy"),
            ("private/runtime.conf", b"exact config"),
            ("private/proxy.loaded", b"proxy loaded"),
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        alignment_path = root / MODULE.ALIGNMENT_RELATIVE_PATH
        alignment_path.write_text(
            json.dumps(
                {
                    "schema": "endfield.endminf-m27-c105-source-frame-alignment.v1",
                    "authoritative": True,
                    "sessionId": MODULE.EXPECTED_SESSION_ID,
                    "runtimeFrame": MODULE.EXPECTED_FRAME,
                    "sessionSha256": sha256(root / "session.json"),
                    "metadataSha256": sha256(metadata_path),
                    "reference": {
                        "path": "videos/reference.mkv",
                        "frame": 384,
                        "sha256": "1" * 64,
                    },
                    "method": "bounded exact animation epoch alignment",
                }
            ),
            encoding="utf-8",
        )
        artifacts = []
        for relative in (
            "session.json",
            "runtime.status.json",
            "collected/summary.json",
            MODULE.RUNTIME_RELATIVE_PATH,
            "private/runtime.conf",
            "private/proxy.loaded",
            MODULE.METADATA_RELATIVE_PATH,
            MODULE.ALIGNMENT_RELATIVE_PATH,
        ):
            path = root / relative
            artifacts.append(
                {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}
            )
        (root / "collected" / "inventory.json").write_text(
            json.dumps(
                {
                    "schema": "endfieldCapture.collection.v1",
                    "session": MODULE.EXPECTED_SESSION_ID,
                    "files": len(artifacts),
                    "artifacts": artifacts,
                }
            ),
            encoding="utf-8",
        )
        pinned = {
            row["path"]: row["sha256"]
            for row in artifacts
            if row["path"] != MODULE.ALIGNMENT_RELATIVE_PATH
        }
        return self.make_contract(root), metadata_path, pinned

    def test_exact_synthetic_session_admits_draw_local_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract, _metadata, pinned = self.make_session(root)
            result = MODULE.verify(
                root, contract, expected_artifact_hashes=pinned
            )
            self.assertEqual(result["status"], "admitted_draw_local_validation_receipt")
            self.assertEqual(result["drawLocalObservation"]["c105Bits"], [0, 0, 0, 0])
            self.assertTrue(result["authority"]["drawLocalC105Receipt"])
            self.assertFalse(result["authority"]["capturedConstantsUsedAsProducerSource"])
            self.assertFalse(result["authority"]["liveHGVFXManagerSourceClosed"])
            self.assertFalse(result["authority"]["canonicalM27PublisherCanBePopulated"])

    def test_missing_inventory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract, _metadata, pinned = self.make_session(root)
            (root / "collected" / "inventory.json").unlink()
            with self.assertRaisesRegex(MODULE.AuthorityError, "missing collection inventory") as raised:
                MODULE.verify(root, contract, expected_artifact_hashes=pinned)
            self.assertEqual(raised.exception.gate, "inventory_binding")

    def test_missing_alignment_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract, _metadata, pinned = self.make_session(root)
            (root / MODULE.ALIGNMENT_RELATIVE_PATH).unlink()
            with self.assertRaises(MODULE.AuthorityError) as raised:
                MODULE.verify(root, contract, expected_artifact_hashes=pinned)
            self.assertEqual(raised.exception.gate, "inventory_binding")

    def test_dropped_runtime_events_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract, _metadata, pinned = self.make_session(root)
            path = root / "runtime.status.json"
            status = json.loads(path.read_text(encoding="utf-8"))
            status["graphicsDropped"] = 1
            path.write_text(json.dumps(status), encoding="utf-8")
            with self.assertRaises(MODULE.AuthorityError) as raised:
                MODULE.verify(root, contract, expected_artifact_hashes=pinned)
            self.assertEqual(raised.exception.gate, "runtime_status")

    def test_reinventoried_runtime_drift_fails_archived_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract, _metadata, pinned = self.make_session(root)
            runtime_path = root / MODULE.RUNTIME_RELATIVE_PATH
            runtime_path.write_bytes(b"different archived proxy")
            inventory_path = root / "collected" / "inventory.json"
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            for row in inventory["artifacts"]:
                if row["path"] == MODULE.RUNTIME_RELATIVE_PATH:
                    row["bytes"] = runtime_path.stat().st_size
                    row["sha256"] = sha256(runtime_path)
            inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
            with self.assertRaises(MODULE.AuthorityError) as raised:
                MODULE.verify(root, contract, expected_artifact_hashes=pinned)
            self.assertEqual(raised.exception.gate, "archived_artifact_identity")

    def test_shader_identity_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract, metadata_path, pinned = self.make_session(root)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["drawRecords"][0]["shaders"][1]["identityHash"] = 1
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            # Rebind both the alignment and inventory so the draw gate, rather
            # than a stale hash, is the deterministic first failure.
            alignment_path = root / MODULE.ALIGNMENT_RELATIVE_PATH
            alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
            alignment["metadataSha256"] = sha256(metadata_path)
            alignment_path.write_text(json.dumps(alignment), encoding="utf-8")
            inventory_path = root / "collected" / "inventory.json"
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            for row in inventory["artifacts"]:
                path = root / row["path"]
                row["bytes"] = path.stat().st_size
                row["sha256"] = sha256(path)
            inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
            pinned[MODULE.METADATA_RELATIVE_PATH] = sha256(metadata_path)
            with self.assertRaises(MODULE.AuthorityError) as raised:
                MODULE.verify(root, contract, expected_artifact_hashes=pinned)
            self.assertEqual(raised.exception.gate, "draw_identity")

    def test_cli_inventory_rejection_includes_validation_only_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract, _metadata, _pinned = self.make_session(root)
            (root / "collected" / "inventory.json").unlink()
            output = root / "rejected.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(root),
                    "--contract",
                    str(contract),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "rejected")
            self.assertEqual(report["failedGate"], "inventory_binding")
            self.assertIn("missing collection inventory", report["reason"])
            self.assertEqual(
                report["validationOnlyObservation"]["c105Bits"], [0, 0, 0, 0]
            )
            self.assertFalse(report["authority"]["drawLocalC105Receipt"])
            self.assertLessEqual(len(report["reason"]), MODULE.MAX_DIAGNOSTIC_CHARS)


if __name__ == "__main__":
    unittest.main()
