import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("audit_endminf_m27_particle_abi.py")
SPEC = importlib.util.spec_from_file_location("audit_endminf_m27_particle_abi", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EndminfM27ParticleAbiTests(unittest.TestCase):
    def test_normalizes_fxc_instruction_stream(self):
        text = "// header\nvs_5_0\n// declaration\n dcl_temps 1 \n ret\n"
        self.assertEqual(MODULE.normalized_disassembly(text), "vs_5_0\ndcl_temps 1\nret\n")

    def test_accepts_single_instance_expanded_fifteen_particle_capture(self):
        capture = {
            "status": "ok",
            "litEffectInstancedParallax": {
                "subProgramIndex": 113,
                "drawTopology": {
                    "instanceCount": 1,
                    "startInstanceLocation": 0,
                    "sourceRockIndexCount": 72,
                    "expandedMeshCopiesByCapture": {
                        "FrameAnalysis-2026-08-24-182850": 15,
                    },
                },
            },
        }
        source = {
            "mesh": {"indexCount": 72},
            "particleSystem": {"burst": {"count": 15.0}},
        }
        result = MODULE.validate_capture(capture, source)
        self.assertEqual(result["lateCaptureIndexCount"], 1080)
        self.assertEqual(result["allDrawsInstanceCount"], 1)

    def test_rejects_procedural_multi_instance_interpretation(self):
        capture = {
            "status": "ok",
            "litEffectInstancedParallax": {
                "subProgramIndex": 113,
                "drawTopology": {
                    "instanceCount": 15,
                    "startInstanceLocation": 0,
                    "sourceRockIndexCount": 72,
                    "expandedMeshCopiesByCapture": {
                        "FrameAnalysis-2026-08-24-182850": 15,
                    },
                },
            },
        }
        source = {
            "mesh": {"indexCount": 72},
            "particleSystem": {"burst": {"count": 15.0}},
        }
        with self.assertRaisesRegex(MODULE.AuditError, "instance count"):
            MODULE.validate_capture(capture, source)


if __name__ == "__main__":
    unittest.main()
