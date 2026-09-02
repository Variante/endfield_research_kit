from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name(
    "verify_endminf_m27_global_mip_bias_session.py"
)
SPEC = importlib.util.spec_from_file_location("m27_session_verifier_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SessionBindingTests(unittest.TestCase):
    def make_session(self, root: Path) -> dict[str, object]:
        receipt = {
            "session": {
                "sessionId": "20260902T120000Z",
                "numericSessionId": 20260902120000,
                "providerMask": 1,
                "graphicsProfile": "full",
                "runtimeKind": "general",
                "runtimePackage": MODULE.RUNTIME_RELATIVE_PATH,
            }
        }
        (root / "graphics").mkdir(parents=True)
        (root / "private").mkdir(parents=True)
        (root / "collected").mkdir(parents=True)
        receipt_path = root / MODULE.RECEIPT_RELATIVE_PATH
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        runtime_path = root / MODULE.RUNTIME_RELATIVE_PATH
        runtime_path.write_bytes(b"exact runtime package")
        (root / "session.json").write_text(
            json.dumps(
                {
                    "schema": "endfieldCapture.session.v1",
                    "sessionId": "20260902T120000Z",
                    "numericSessionId": 20260902120000,
                    "providers": 1,
                    "graphicsProfile": "full",
                    "evidenceLabel": "forced-d3d11",
                    "runtimeStagedPath": str(runtime_path.resolve()),
                    "runtimeBytes": runtime_path.stat().st_size,
                    "runtimeSha256": hashlib.sha256(
                        runtime_path.read_bytes()
                    ).hexdigest(),
                }
            ),
            encoding="utf-8",
        )
        artifacts = []
        for relative in (
            MODULE.RECEIPT_RELATIVE_PATH,
            MODULE.RUNTIME_RELATIVE_PATH,
        ):
            path = root / relative
            artifacts.append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        (root / "collected" / "inventory.json").write_text(
            json.dumps(
                {
                    "schema": "endfieldCapture.collection.v1",
                    "session": "20260902T120000Z",
                    "files": len(artifacts),
                    "bytes": sum(row["bytes"] for row in artifacts),
                    "artifacts": artifacts,
                }
            ),
            encoding="utf-8",
        )
        return receipt

    def test_exact_inventory_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_session(root)
            result = MODULE.verify_inventory_binding(root, receipt)
            self.assertEqual(set(result), {
                MODULE.RECEIPT_RELATIVE_PATH,
                MODULE.RUNTIME_RELATIVE_PATH,
            })

    def test_missing_inventory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_session(root)
            (root / "collected" / "inventory.json").unlink()
            with self.assertRaises(MODULE.SessionReceiptError):
                MODULE.verify_inventory_binding(root, receipt)

    def test_runtime_hash_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_session(root)
            (root / MODULE.RUNTIME_RELATIVE_PATH).write_bytes(b"drift")
            with self.assertRaisesRegex(
                MODULE.SessionReceiptError, "inventory (size|hash) mismatch"
            ):
                MODULE.verify_inventory_binding(root, receipt)

    def test_receipt_session_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_session(root)
            receipt["session"]["numericSessionId"] = 1
            with self.assertRaisesRegex(
                MODULE.SessionReceiptError, "numeric session mismatch"
            ):
                MODULE.verify_inventory_binding(root, receipt)

    def test_session_runtime_identity_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_session(root)
            session_path = root / "session.json"
            session = json.loads(session_path.read_text(encoding="utf-8"))
            session["runtimeBytes"] += 1
            session["runtimeSha256"] = "0" * 64
            session_path.write_text(json.dumps(session), encoding="utf-8")
            with self.assertRaisesRegex(
                MODULE.SessionReceiptError, "runtime(Bytes|Sha256) mismatch"
            ):
                MODULE.verify_inventory_binding(root, receipt)

    def test_targeted_session_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.make_session(root)
            session_path = root / "session.json"
            session = json.loads(session_path.read_text(encoding="utf-8"))
            session["graphicsProfile"] = "targeted"
            session_path.write_text(json.dumps(session), encoding="utf-8")
            with self.assertRaisesRegex(
                MODULE.SessionReceiptError, "session is not Full"
            ):
                MODULE.verify_inventory_binding(root, receipt)

    def test_cli_failure_writes_structured_rejection_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_session(root)
            (root / "collected" / "inventory.json").unlink()
            output = root / "result.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("missing collection inventory", completed.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], MODULE.RESULT_SCHEMA)
            self.assertEqual(report["status"], "rejected")
            self.assertEqual(
                report["validator"],
                "verify_endminf_m27_global_mip_bias_session",
            )
            self.assertEqual(report["failedGate"], "session_receipt_validation")
            self.assertIn("missing collection inventory", report["reason"])
            self.assertLessEqual(
                len(report["reason"]), MODULE.MAX_DIAGNOSTIC_CHARS
            )


if __name__ == "__main__":
    unittest.main()
