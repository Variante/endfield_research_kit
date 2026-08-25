#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name(
    "build_secondary_dynamics_session_certification_contract.py")
SPEC = importlib.util.spec_from_file_location("session_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SessionCertificationContractTests(unittest.TestCase):
    def test_pinned_capture_certifies_expected_route(self):
        repo = Path(__file__).resolve().parents[2]
        session = repo / "scratch" / "reverse_engineering" / "endfield_capture" / \
            MODULE.SESSION_ID
        contract = MODULE.build(session)
        self.assertTrue(contract["targetReady"])
        self.assertEqual(
            contract["certification"],
            {
                "certified": True,
                "useRelativeTransform": False,
                "useCrossFrameJob": True,
                "useAnimatorTransform": False,
                "writebackRoute": "TransformAccess",
            },
        )
        self.assertEqual(contract["window"]["activeTeamLanesPerSettledCall"], 4)
        self.assertEqual(contract["window"]["warmupClothUpdateCalls"], 7)
        self.assertEqual(contract["window"]["relativeTrueCalls"], 0)


if __name__ == "__main__":
    unittest.main()
