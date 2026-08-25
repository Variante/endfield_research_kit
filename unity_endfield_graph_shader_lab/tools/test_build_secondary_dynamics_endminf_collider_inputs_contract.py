#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_secondary_dynamics_endminf_collider_inputs_contract as target  # noqa: E402


class EndminfColliderInputsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = target.build_contract()

    def test_managed_collider_type_table(self) -> None:
        expected = {
            (0, 1): 2, (1, 1): 3, (2, 1): 4,
            (0, 0): 5, (1, 0): 6, (2, 0): 7,
        }
        self.assertEqual({key: target.collider_type(*key) for key in expected}, expected)

    def test_type7_is_managed_but_not_core_supported(self) -> None:
        table = self.payload["managedConstruction"]["colliderTypeTable"]
        row = next(row for row in table if row["colliderType"] == 7)
        self.assertEqual((row["direction"], row["alignedOnCenter"]), (2, 0))
        self.assertFalse(row["coreCapsuleBranch"])
        self.assertNotIn(7, [row["managedMapping"]["colliderType"] for row in self.payload["endminf"]["rows"]])

    def test_flag_construction_and_reset_consumption(self) -> None:
        self.assertEqual(target.registration_flag(2, 1, 0), 0x72)
        self.assertEqual(target.registration_flag(4, 1, 0), 0x74)
        self.assertEqual(target.registration_flag(2, 1, 1), 0xF2)
        rows = self.payload["endminf"]["rows"]
        self.assertEqual({row["managedMapping"]["registrationFlag"] for row in rows}, {"0x72", "0x74"})
        self.assertEqual({row["managedMapping"]["colliderStartFlagAfterPreSimulation"] for row in rows}, {"0x32", "0x34"})

    def test_radius_separation_size_mapping(self) -> None:
        source = {"x": 0.1, "y": 0.2, "z": 0.3}
        self.assertEqual(target.size_input(source, 1), [0.1, 0.2, 0.3])
        self.assertEqual(target.size_input(source, 0), [0.1, 0.1, 0.3])
        for row in self.payload["endminf"]["rows"]:
            serialized = row["serialized"]
            expected_y = serialized["size"]["y"] if serialized["radiusSeparation"] else serialized["size"]["x"]
            self.assertEqual(row["managedMapping"]["sizeArray"][1], expected_y)

    def test_endminf_focused_counts(self) -> None:
        endminf = self.payload["endminf"]
        self.assertEqual(endminf["capsuleCount"], 10)
        self.assertEqual(endminf["directionCounts"], {"0/x": 9, "1/y": 0, "2/z": 1})
        self.assertEqual(endminf["colliderStartFlagCounts"], {"0x32": 9, "0x34": 1})
        self.assertTrue(all(row["serialized"]["alignedOnCenter"] == 1 for row in endminf["rows"]))
        self.assertTrue(all(row["serialized"]["reverseDirection"] == 0 for row in endminf["rows"]))

    def test_invalid_serialized_enums_fail_closed(self) -> None:
        with self.assertRaises(target.ContractError):
            target.collider_type(3, 1)
        with self.assertRaises(target.ContractError):
            target.collider_type(0, 2)
        with self.assertRaises(target.ContractError):
            target.size_input({"x": 1, "y": 2, "z": 3}, -1)

    def test_generated_contract_matches(self) -> None:
        generated = json.loads(target.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(generated, self.payload)


if __name__ == "__main__":
    unittest.main()
