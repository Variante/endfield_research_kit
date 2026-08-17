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
            "schema": "endfield.original-m23-dxbc-exact.v2",
            "vertex_sha256": VALIDATOR.EXPECTED["vertex"][2],
            "pixel_sha256": VALIDATOR.EXPECTED["pixel"][2],
            "vs_constant_buffer_creation_mask": "0x1f",
            "ps_constant_buffer_creation_mask": "0x1f",
            "shader_resource_creation_mask": "0x1f",
            "sampler_creation_mask": "0x1f",
            "b4_high_semantics": "zero_or_sentinel_only_non_fidelity",
            "vs_binding_mask": "0x1", "ps_binding_mask": "0x1",
            "input_binding_mask": "0x1", "vertex_buffer_binding_mask": "0x1",
            "vs_constant_buffer_binding_mask": "0x1f",
            "ps_constant_buffer_binding_mask": "0x1f",
            "shader_resource_binding_mask": "0x1f", "sampler_binding_mask": "0x1f",
            "state_binding_mask": "0x7", "render_target_binding_mask": "0x1",
            "vertex_shader_resource_creation_mask": "0x1",
            "vertex_shader_resource_binding_mask": "0x1",
            "topology_binding_mask": "0x1", "viewport_binding_mask": "0x1",
            "status": "pass", "draw_issued": 1, "readback_finite": 1,
            "visual_fidelity_claim": 0,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(__import__("json").dumps(report), encoding="utf-8")
            self.assertEqual(VALIDATOR.validate_report(path)["status"], "pass")

if __name__ == "__main__":
    unittest.main()
