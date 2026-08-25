import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("normalize_endminf_deferred_retail_hlsl.py")
SPEC = importlib.util.spec_from_file_location("normalize_retail_hlsl", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class NormalizeRetailHlslTests(unittest.TestCase):
    def test_rejects_unrecognized_header(self):
        with self.assertRaisesRegex(ValueError, "alias header"):
            MODULE.normalize("not a Ruri shader")

    def test_contract_covers_retail_slots(self):
        self.assertEqual(MODULE.TEXTURE_IDS[13], 1)
        self.assertEqual(MODULE.TEXTURE_IDS[43], 27)
        self.assertEqual(MODULE.CB_ALIASES["_103_m0"], "EndfieldCB7_f_0")
        self.assertIn("EndfieldCB9_f_0[4]", MODULE.BUFFER_HEADER)
        self.assertIn("_EndfieldBufferT0", MODULE.BUFFER_HEADER)


if __name__ == "__main__":
    unittest.main()
