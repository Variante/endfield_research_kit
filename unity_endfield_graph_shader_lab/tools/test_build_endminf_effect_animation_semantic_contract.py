from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
MODULE_PATH = HERE / "build_endminf_effect_animation_semantic_contract.py"
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_effect_animation_semantic_contract",
    MODULE_PATH,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EndminfEffectAnimationSemanticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = MODULE.build_contract()

    def actual_for(self, clip: dict) -> dict:
        return MODULE.parse_generated_curves(
            MODULE.ANIMATION_ROOT / f"{clip['name']}.anim"
        )

    def test_published_contract_is_source_derived_and_current(self) -> None:
        published = json.loads(
            MODULE.DEFAULT_OUTPUT.read_text(encoding="utf-8")
        )
        self.assertEqual(published, self.contract)
        self.assertEqual(
            self.contract["derivation"]["boundary"],
            "No cached .anim bytes or capture-fitted values participate in expected curves.",
        )
        self.assertEqual(sum(row["bindingCount"] for row in self.contract["clips"]), 58)
        for clip in self.contract["clips"]:
            MODULE.validate_actual_curves(clip, self.actual_for(clip))

    def test_generated_key_value_drift_fails(self) -> None:
        clip = self.contract["clips"][0]
        actual = self.actual_for(clip)
        binding = sorted(actual)[0]
        actual[binding][0]["value"] += 0.125
        with self.assertRaisesRegex(MODULE.SemanticError, "key time/value drifted"):
            MODULE.validate_actual_curves(clip, actual)

    def test_generated_tangent_drift_fails(self) -> None:
        clip = self.contract["clips"][1]
        actual = self.actual_for(clip)
        binding = sorted(actual)[0]
        actual[binding][1]["outTangent"] += 0.25
        with self.assertRaisesRegex(MODULE.SemanticError, "tangent drifted"):
            MODULE.validate_actual_curves(clip, actual)

    def test_missing_and_extra_binding_fail(self) -> None:
        clip = self.contract["clips"][0]
        actual = self.actual_for(clip)
        missing = copy.deepcopy(actual)
        missing.pop(sorted(missing)[0])
        with self.assertRaisesRegex(MODULE.SemanticError, "binding set drifted"):
            MODULE.validate_actual_curves(clip, missing)

        extra = copy.deepcopy(actual)
        extra[("NotSource", "m_LocalPosition.x")] = copy.deepcopy(
            actual[sorted(actual)[0]]
        )
        with self.assertRaisesRegex(MODULE.SemanticError, "binding set drifted"):
            MODULE.validate_actual_curves(clip, extra)


if __name__ == "__main__":
    unittest.main()
