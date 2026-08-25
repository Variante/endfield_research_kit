#!/usr/bin/env python3
"""Focused tests for the native callback/writeback contract."""

from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
import build_secondary_dynamics_callback_contract as builder


class SecondaryDynamicsCallbackContractTests(unittest.TestCase):
    def test_current_contract_closes_callback_and_writeback(self) -> None:
        observed = builder.build_contract()
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(observed, payload)
        self.assertEqual(payload["status"], "native_callback_writeback_closed")
        self.assertFalse(payload["secondary_dynamics_verified"])
        self.assertEqual(len(payload["callbacks"]), 7)
        self.assertEqual(payload["callbacks"][3]["playerLoopCategory"], "PreLateUpdate")
        self.assertEqual(payload["callbacks"][4]["playerLoopCategory"], "PreLateUpdate")
        self.assertFalse(payload["simulationSelectors"]["fixedUpdateRunsClothUpdate"])
        self.assertTrue(payload["simulationSelectors"]["mutuallyExclusiveWholePipeline"])
        self.assertEqual(payload["writeback"]["stages"]["transformWriteback"], [3004, 4277])
        self.assertLess(
            payload["writeback"]["orderingGates"][0]["before"],
            payload["writeback"]["orderingGates"][0]["after"],
        )

    def test_missing_native_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing"
            result = builder.build_contract(game_assembly=missing, metadata=missing)
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["secondary_dynamics_verified"])
        self.assertIn("installed GameAssembly.dll", result["validationFailures"][0])

    def test_native_gate_delegates_to_common_with_explicit_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gameassembly = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            gameassembly.write_bytes(b"game")
            metadata.write_bytes(b"metadata")
            gate_result = SimpleNamespace(
                validated=True,
                status="validated",
                detail="",
                gameassembly=gameassembly,
                metadata=metadata,
                gameassembly_sha256=builder.EXPECTED_GAME_ASSEMBLY_SHA256,
                metadata_sha256=builder.EXPECTED_METADATA_SHA256,
            )
            with patch.object(
                builder,
                "check_installed_native_inputs",
                return_value=gate_result,
            ) as check:
                observed = builder._native_gate(gameassembly, metadata)
            check.assert_called_once_with(
                builder.EXPECTED_GAME_ASSEMBLY_SHA256,
                builder.EXPECTED_METADATA_SHA256,
                gameassembly=gameassembly,
                metadata=metadata,
            )
            self.assertEqual(observed["gameAssembly"]["path"], gameassembly.as_posix())

    def test_common_gate_mismatch_is_fail_closed(self) -> None:
        result = SimpleNamespace(
            validated=False,
            status="mismatched",
            detail="GameAssembly.dll is a different build",
        )
        with patch.object(builder, "check_installed_native_inputs", return_value=result):
            with self.assertRaisesRegex(builder.ContractError, r"common\.check_installed_native_inputs \[mismatched\]"):
                builder._native_gate(None, None)

    def test_player_loop_native_call_identity_drift_is_rejected(self) -> None:
        solver = json.loads(builder.SOLVER_INPUTS.read_text(encoding="utf-8"))
        player_loop = json.loads(builder.PLAYER_LOOP_CONTRACT.read_text(encoding="utf-8"))
        player_loop["insertions"][1]["categoryName"]["value"] = "Update"
        with self.assertRaisesRegex(builder.ContractError, "category drift"):
            builder._verify_player_loop(solver, player_loop)

        player_loop = json.loads(builder.PLAYER_LOOP_CONTRACT.read_text(encoding="utf-8"))
        player_loop["insertions"][4]["before"] = True
        with self.assertRaisesRegex(builder.ContractError, "insertion flags drift"):
            builder._verify_player_loop(solver, player_loop)

    def test_player_loop_delegate_slot_drift_is_rejected(self) -> None:
        solver = json.loads(builder.SOLVER_INPUTS.read_text(encoding="utf-8"))
        player_loop = json.loads(builder.PLAYER_LOOP_CONTRACT.read_text(encoding="utf-8"))
        registration = next(
            row
            for row in solver["native_lifecycle"]["manager"]["callbacks"]
            if row["method"] == builder.CALLBACKS[1][1]
        )
        registration["delegate_slot"] = "0x20"
        with self.assertRaisesRegex(builder.ContractError, "delegate slot drift"):
            builder._verify_player_loop(solver, player_loop)

    def test_regenerated_evidence_bytes_are_accepted_but_provenance_drift_is_rejected(self) -> None:
        solver = json.loads(builder.SOLVER_INPUTS.read_text(encoding="utf-8"))
        native = json.loads(builder.DEFAULT_NATIVE.read_text(encoding="utf-8"))
        catalog = json.loads(builder.DEFAULT_METADATA_CATALOG.read_text(encoding="utf-8"))
        builder._verify_solver_sources(
            solver,
            native,
            catalog,
            builder.DEFAULT_NATIVE,
            builder.DEFAULT_METADATA_CATALOG,
        )

        native["metadata"]["gameAssemblySha256"] = "00" * 32
        with self.assertRaisesRegex(builder.ContractError, "GameAssembly hash drift"):
            builder._verify_solver_sources(
                solver,
                native,
                catalog,
                builder.DEFAULT_NATIVE,
                builder.DEFAULT_METADATA_CATALOG,
            )

    def test_method_identity_recomputes_native_body_hash(self) -> None:
        body = b"nativebody"
        lifecycle = {
            "method_bodies": [{
                "type": "T",
                "method": "M",
                "method_index": 1,
                "va": "0x100",
                "file_offset": "0x0",
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }],
        }
        native = {
            "bodyTargets": [{
                "type": "T",
                "method": "M",
                "methodIndex": 1,
                "methodPointerVa": "0x100",
                "fileOffset": "0x0",
                "scanBytes": len(body),
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "GameAssembly.dll"
            path.write_bytes(body)
            identity = builder._method_identity(lifecycle, native, "T", "M", path)
            self.assertEqual(identity["nativeBodySha256"], lifecycle["method_bodies"][0]["sha256"])
            path.write_bytes(b"different!")
            with self.assertRaisesRegex(builder.ContractError, "native body sha256 drift"):
                builder._method_identity(lifecycle, native, "T", "M", path)

    def test_all_wrapper_identities_are_source_pinned(self) -> None:
        payload = builder.build_contract()
        self.assertEqual(
            [row["method"]["methodIndex"] for row in payload["callbacks"]],
            list(range(385117, 385124)),
        )


if __name__ == "__main__":
    unittest.main()
