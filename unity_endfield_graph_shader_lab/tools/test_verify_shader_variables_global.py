#!/usr/bin/env python3

from __future__ import annotations

import json
import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_shader_variables_global.py")
SPEC = importlib.util.spec_from_file_location(
    "verify_shader_variables_global",
    MODULE_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load verifier: {MODULE_PATH}")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class ShaderVariablesGlobalVerifierTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> None:
        report = {
            "valid": True,
            "defaultOff": True,
            "pass0ConsumerEnabled": False,
            "sourceAuditHashMatches": True,
            "sourceAuditSha256": "audit",
            "publicationReturnedReady": True,
            "readyObserved": True,
            "canonicalWordsMatch": True,
            "d3d11BridgeWordsMatch": True,
            "selectedConsumerWordsMatch": True,
            "unresolvedRegistersZero": True,
            "bufferBytes": 3200,
            "vectorCount": 200,
            "d3d11SelectedBytes": 2512,
            "selectedVectorCount": 32,
            "selectedDefaultSHWords": verifier.EXPECTED_SH_WORDS,
            "failClosedGates": [
                {"rejected": True, "diagnosticMatched": True}
                for _ in range(6)
            ],
            "failures": [],
        }
        for api in ("d3d11", "d3d12"):
            (root / f"gpu_validation_{api}.json").write_text(
                json.dumps(report),
                encoding="utf-8",
            )
            (root / f"unity_frame_{api}.log").write_text(
                verifier.ACTIVATION_TOKEN,
                encoding="utf-8",
            )
            (root / f"wulfa_beauty_{api}.png").write_bytes(
                b"d3d11 beauty" if api == "d3d11" else b"d3d12 beauty"
            )
        (root / "unity_fail_closed_d3d12.log").write_text(
            verifier.FAIL_CLOSED_TOKEN,
            encoding="utf-8",
        )
        (root / "wulfa_beauty_fail_closed_d3d12.png").write_bytes(
            b"d3d12 beauty"
        )

    def test_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_fixture(root)
            result = verifier.verify(root)
            self.assertTrue(result["valid"])
            self.assertTrue(result["sameFrameActivation"])

    def test_missing_activation_has_actionable_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_fixture(root)
            (root / "unity_frame_d3d12.log").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "d3d12_frame_activation"):
                verifier.verify(root)

    def test_fail_closed_activation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_fixture(root)
            (root / "unity_fail_closed_d3d12.log").write_text(
                verifier.FAIL_CLOSED_TOKEN + verifier.ACTIVATION_TOKEN,
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AssertionError, "fail_closed_no_activation"):
                verifier.verify(root)

    def test_fail_closed_beauty_change_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_fixture(root)
            (root / "wulfa_beauty_fail_closed_d3d12.png").write_bytes(
                b"changed beauty"
            )
            with self.assertRaisesRegex(
                AssertionError,
                "d3d12_fail_closed_beauty",
            ):
                verifier.verify(root)


if __name__ == "__main__":
    unittest.main()
