import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_tether_golden_vectors as target


class TetherGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_executes_native_core_and_matches_source_port(self):
        boundary = self.contract["boundary"]
        self.assertTrue(boundary["nativeCoreExecuted"])
        self.assertTrue(boundary["sourceTranscriptionBinary64Matched"])
        self.assertEqual(len(self.contract["vectors"]), 5)

    def test_axis_stretch_is_exactly_pinned(self):
        vector = self.contract["vectors"][0]
        self.assertEqual(vector["output"]["next"][0], 1.100000023841858)
        self.assertEqual(vector["output"]["velocityPos"][0], 1.3700000274181363)

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
