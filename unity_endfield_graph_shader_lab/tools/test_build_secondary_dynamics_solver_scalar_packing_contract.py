#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parent
BUILDER = TOOLS / "build_secondary_dynamics_solver_scalar_packing_contract.py"
spec = importlib.util.spec_from_file_location("solver_scalar_packing_builder_under_test", BUILDER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load {BUILDER}")
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


EXPECTED_OWNER_BITS = {
    "MC_Ribbon2": ("3dcac083", "00000000"),
    "MC_Hair": ("3ecccccd", "3d4ccccd"),
    "MC_Ribbon": ("3dcac083", "3e4ccccd"),
    "MC_Coat": ("3ef4bc6a", "3e5f3b64"),
}


class SolverScalarPackingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_source_is_exactly_hash_pinned(self) -> None:
        source = self.contract["source"]["solverInputs"]
        self.assertEqual(source["size"], builder.EXPECTED_SOLVER_INPUTS_SIZE)
        self.assertEqual(source["sha256"], builder.EXPECTED_SOLVER_INPUTS_SHA256)
        self.assertEqual(source["sha256"], builder._sha256(builder.SOLVER_INPUTS))
        self.assertTrue(source["hashPinned"])

    def test_all_four_endminf_owner_values_are_exact(self) -> None:
        self.assertEqual(list(self.contract["owners"]), list(EXPECTED_OWNER_BITS))
        for name, (compression, friction) in EXPECTED_OWNER_BITS.items():
            row = self.contract["owners"][name]
            self.assertEqual(row["tetherCompressionLimit"]["bitsHex"], compression)
            self.assertEqual(row["tetherStretchLimit"]["bitsHex"], "3cf5c28f")
            self.assertEqual(row["distanceVelocityAttenuation"]["bitsHex"], "3e99999a")
            self.assertEqual(row["collisionDynamicFriction"]["bitsHex"], friction)
            self.assertEqual(row["collisionStaticFriction"]["bitsHex"], friction)

    def test_output_offsets_and_helper_destinations_are_closed(self) -> None:
        packing = self.contract["packing"]
        self.assertEqual(packing["tether"]["helperDestinationOffset"], "0xec")
        self.assertEqual(packing["distance"]["helperDestinationOffset"], "0xf4")
        self.assertEqual(packing["collision"]["helperDestinationOffset"], "0x264")
        self.assertIn("ClothParameters+0xf0", packing["tether"]["writes"]["+0x4"])
        self.assertIn("ClothParameters+0x134", packing["distance"]["writes"]["+0x40"])
        self.assertIn("ClothParameters+0x268", packing["collision"]["writes"]["+0x4"])
        self.assertIn("ClothParameters+0x26c", packing["collision"]["writes"]["+0x8"])

    def test_method_and_helper_spans_are_exact(self) -> None:
        native = self.contract["nativeGate"]
        method = native["method"]
        self.assertEqual((method["va"], method["bytes"], method["sha256"]), (
            "0x18308a880", 784, "3310b78bf6c6eb495e70f7ae1ca93885f9689da0a3f4bdb9c7805826e1998380"))
        expected = {
            "tether": ("0x18308bed0", 0x60, "de1bb3e10bd618d7d1c46a099328a6cc23268bf52586b5ddfdcef8be2a78ba75"),
            "distance": ("0x18308bd30", 0x90, "5020ac4ebe1770a881b20ec3677b552e6ad979600768c30601638e72e7c97bcd"),
            "collision": ("0x18308bf90", 0x70, "bde9cd3c0ada86a62e538e50352a759935a1b1ddf2ed8762f7d9c359937c2708"),
        }
        self.assertEqual({name: (row["va"], row["bytes"], row["sha256"]) for name, row in native["helpers"].items()}, expected)

    def test_exact_calls_prove_sources_destinations_and_targets(self) -> None:
        calls = self.contract["nativeGate"]["calls"]
        self.assertEqual(calls["tether"]["serializedPointerSource"], "ClothSerializeData+0xc8")
        self.assertEqual(calls["distance"]["serializedPointerSource"], "ClothSerializeData+0xd0")
        self.assertEqual(calls["collision"]["serializedPointerSource"], "ClothSerializeData+0xf8")
        for name in ("tether", "distance", "collision"):
            self.assertEqual(calls[name]["targetVa"], self.contract["nativeGate"]["helpers"][name]["va"])
        self.assertEqual([calls[name]["clothParametersDestinationOffset"] for name in calls], ["0xec", "0xf4", "0x264"])

    def test_helper_body_equations_pin_required_scalar_stores(self) -> None:
        proof = self.contract["nativeGate"]["helperBodyProof"]
        self.assertIn("0x3cf5c28f", " ".join(proof["tether"]["equations"]))
        self.assertIn("0x3e99999a", " ".join(proof["distance"]["equations"]))
        collision = " ".join(proof["collision"]["equations"])
        self.assertIn("destination+0x4", collision)
        self.assertIn("destination+0x8", collision)
        self.assertEqual(collision.count("serializedCollision+0x14"), 2)

    def test_native_evidence_rebuild_matches_generated_contract(self) -> None:
        self.assertEqual(builder._native_evidence(None, None), self.contract["nativeGate"])

    def test_native_gate_fails_closed(self) -> None:
        result = type("Gate", (), {"status": "mismatched", "detail": "test drift"})()
        with patch.object(builder, "check_installed_native_inputs", return_value=result):
            with self.assertRaisesRegex(builder.ContractError, r"common\.check_installed_native_inputs \[mismatched\]"):
                builder._native_evidence(None, None)


if __name__ == "__main__":
    unittest.main()
