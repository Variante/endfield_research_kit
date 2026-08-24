#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_endminf_offline_recovery_boundary.py")
SPEC = importlib.util.spec_from_file_location("build_endminf_offline_recovery_boundary", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
parse_census = MODULE.parse_census
require_row = MODULE.require_row


class OfflineRecoveryBoundaryTests(unittest.TestCase):
    def test_parses_renderer_census_row(self) -> None:
        rows = parse_census(
            "[Endfield capture census] path=root/all/Particle System (10); "
            "material=<null>; active=True; enabled=False; "
            "particleTime=0.320262; particleCount=1\n"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["particleCount"], 1)
        self.assertAlmostEqual(rows[0]["particleTime"], 0.320262)
        self.assertFalse(rows[0]["enabled"])
        self.assertEqual(require_row(rows, "Particle System (10)", "<null>"), rows[0])

    def test_rejects_material_drift(self) -> None:
        rows = parse_census(
            "[Endfield capture census] path=root/shitou (1); "
            "material=wrong; active=True; enabled=True; "
            "particleTime=0; particleCount=0\n"
        )
        with self.assertRaisesRegex(ValueError, "expected material"):
            require_row(rows, "shitou (1)", "M_fx_endminm_gfx_21")


if __name__ == "__main__":
    unittest.main()
