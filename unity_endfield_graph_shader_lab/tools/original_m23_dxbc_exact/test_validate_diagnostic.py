import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name("validate_diagnostic.py")
SPEC = importlib.util.spec_from_file_location("m23_validate", MODULE)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

class M23DiagnosticTests(unittest.TestCase):
    def test_exact_blobs_are_pinned(self):
        VALIDATOR.validate_blobs()

    def test_masks_and_non_fidelity_gate(self):
        report = {
            "schema": "endfield.original-m23-dxbc-creation.v1",
            "vertex_sha256": VALIDATOR.EXPECTED["vertex"][2],
            "pixel_sha256": VALIDATOR.EXPECTED["pixel"][2],
            "vs_constant_buffer_creation_mask": "0x1f",
            "ps_constant_buffer_creation_mask": "0x1f",
            "shader_resource_creation_mask": "0x1f",
            "sampler_creation_mask": "0x1f",
            "b4_high_semantics": "zero_or_sentinel_only_non_fidelity",
            "status": "pass", "binds_or_draws": False,
            "visual_fidelity_claim": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(__import__("json").dumps(report), encoding="utf-8")
            self.assertEqual(VALIDATOR.validate_report(path)["status"], "pass")

if __name__ == "__main__":
    unittest.main()
