from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
RESOURCE_SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_liteffect_resource_mapping",
    HERE / "verify_endminf_liteffect_resource_mapping.py",
)
assert RESOURCE_SPEC and RESOURCE_SPEC.loader
RESOURCE_MODULE = importlib.util.module_from_spec(RESOURCE_SPEC)
sys.modules[RESOURCE_SPEC.name] = RESOURCE_MODULE
RESOURCE_SPEC.loader.exec_module(RESOURCE_MODULE)

SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_liteffect_visual_compatibility",
    HERE / "verify_endminf_liteffect_visual_compatibility.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EndminfLitEffectVisualCompatibilityTests(unittest.TestCase):
    def test_published_json_string_keys_equal_fresh_register_keys(self) -> None:
        fresh = {"physicalTextures": {0: "_BaseColorMap", 5: "_ParallaxNoiseMap"}}
        published = {
            "physicalTextures": {"0": "_BaseColorMap", "5": "_ParallaxNoiseMap"}
        }
        self.assertEqual(
            MODULE.canonical_json(published),
            MODULE.canonical_json(fresh),
        )

    def test_canonical_comparison_does_not_hide_value_drift(self) -> None:
        fresh = {"physicalTextures": {0: "_BaseColorMap"}}
        drifted = {"physicalTextures": {"0": "_NormalMap"}}
        self.assertNotEqual(
            MODULE.canonical_json(drifted),
            MODULE.canonical_json(fresh),
        )


if __name__ == "__main__":
    unittest.main()
