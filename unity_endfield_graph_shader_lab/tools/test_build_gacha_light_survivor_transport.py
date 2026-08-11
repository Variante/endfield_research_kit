#!/usr/bin/env python3
"""Focused tests for the source-backed Gacha survivor transport contract."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_gacha_light_survivor_transport.py")
SPEC = importlib.util.spec_from_file_location("build_gacha_light_survivor_transport", SCRIPT)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class GachaLightSurvivorTransportTests(unittest.TestCase):
    def test_generated_contract_is_current(self) -> None:
        expected = json.dumps(
            BUILDER.build_contract(), ensure_ascii=False, indent=2
        ) + "\n"
        self.assertEqual(
            BUILDER.OUTPUT.read_text(encoding="utf-8"),
            expected,
        )

    def test_contract_preserves_setup_state_order_and_boundary(self) -> None:
        contract = BUILDER.build_contract()
        selection = contract["selection"]
        self.assertEqual(selection["knownAuthoredCount"], 17)
        self.assertEqual(selection["knownAuthoredCharacterCount"], 6)
        self.assertEqual(selection["knownAuthoredRoomCount"], 11)
        self.assertEqual(
            selection["setupStateRelativeOrder"][:6],
            [
                "SpecLight_1 (8)",
                "RimLight_2 (5)",
                "SpecLight_1 (11)",
                "Point Light_overview (2)",
                "RimLight_2 (4)",
                "FogLight_1 (2)",
            ],
        )
        self.assertEqual(
            selection["setupStateRelativeOrder"][-1], "Spot Light (10)"
        )
        self.assertTrue(contract["boundary"]["targetFrameCaptureRequired"])
        self.assertEqual(contract["boundary"]["productionPublication"],
                         "disabled; this contract does not publish a shader buffer")

    def test_schema_drift_fails_closed(self) -> None:
        population = json.loads(BUILDER.POPULATION.read_text(encoding="utf-8"))
        population["schema"] = "wrong"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "population.json"
            path.write_text(json.dumps(population), encoding="utf-8")
            with self.assertRaisesRegex(BUILDER.ContractError, "population schema drift"):
                BUILDER.build_contract(path, BUILDER.DEFERRED)


if __name__ == "__main__":
    unittest.main()
