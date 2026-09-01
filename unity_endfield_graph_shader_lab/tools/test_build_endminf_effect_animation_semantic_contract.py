from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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


def source_available() -> bool:
    return all((MODULE.STAGE / spec["source"]).is_file()
               for spec in MODULE.SPECS)


def generated_available() -> bool:
    return all((MODULE.ANIMATION_ROOT / f"{spec['name']}.anim").is_file()
               for spec in MODULE.SPECS)


class EndminfEffectAnimationSemanticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # This is deliberately the clean-checkout path: no ignored source JSON
        # or generated AnimationClip cache is needed to validate the payload.
        cls.contract = MODULE.load_published_contract()

    def actual_for(self, clip: dict) -> dict:
        return MODULE.parse_generated_curves(
            MODULE.ANIMATION_ROOT / f"{clip['name']}.anim"
        )

    def test_published_contract_is_complete_and_clean_checkout_safe(self) -> None:
        self.assertEqual(
            self.contract["schema"],
            "endfield.endminf-effect-animation-source-curves.v2",
        )
        self.assertEqual(
            self.contract["status"],
            "source_derived_rebuildable_curve_contract",
        )
        self.assertEqual(sum(row["bindingCount"] for row in self.contract["clips"]), 58)
        self.assertEqual(
            sum(curve["keyCount"]
                for clip in self.contract["clips"] for curve in clip["curves"]),
            17_984,
        )
        for clip in self.contract["clips"]:
            self.assertEqual(len(clip["keyTimes"]), clip["keyCountPerBinding"])
            self.assertEqual(len(clip["curves"]), clip["bindingCount"])
            for curve in clip["curves"]:
                self.assertEqual(len(curve["values"]), curve["keyCount"])
                self.assertEqual(len(curve["inTangents"]), curve["keyCount"])
                self.assertEqual(len(curve["outTangents"]), curve["keyCount"])

        missing = Path("Z:/definitely-missing-endminf-animation-evidence")
        with mock.patch.object(MODULE, "STAGE", missing), \
                mock.patch.object(MODULE, "ANIMATION_ROOT", missing):
            self.assertEqual(MODULE.load_published_contract(), self.contract)

    @unittest.skipUnless(source_available(), "ignored exact source JSON is unavailable")
    def test_explicit_source_rederivation_is_current(self) -> None:
        self.assertEqual(MODULE.build_contract(), self.contract)
        self.assertEqual(
            self.contract["derivation"]["boundary"],
            "Tracked payload is rederived only from exact serialized AnimationClip JSON; "
            "no cached .anim bytes or capture-fitted values participate.",
        )

    @unittest.skipUnless(source_available(), "ignored exact source JSON is unavailable")
    def test_write_and_source_check_do_not_consult_generated_anim_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "contract.json"
            missing_cache = Path(temp) / "missing-generated-cache"
            with mock.patch.object(MODULE, "ANIMATION_ROOT", missing_cache), \
                    mock.patch.object(
                        MODULE,
                        "verify_generated",
                        side_effect=AssertionError("generated cache was consulted"),
                    ), contextlib.redirect_stdout(io.StringIO()):
                with mock.patch.object(
                    sys,
                    "argv",
                    [str(MODULE_PATH), "--write", "--output", str(output)],
                ):
                    self.assertEqual(MODULE.main(), 0)
                with mock.patch.object(
                    sys,
                    "argv",
                    [str(MODULE_PATH), "--check-source", "--output", str(output)],
                ):
                    self.assertEqual(MODULE.main(), 0)

    @unittest.skipUnless(source_available(), "ignored exact source JSON is unavailable")
    def test_source_identity_hash_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            for spec in MODULE.SPECS:
                shutil.copyfile(
                    MODULE.STAGE / spec["source"],
                    stage / spec["source"],
                )
            first = stage / MODULE.SPECS[0]["source"]
            first.write_bytes(first.read_bytes() + b"\n")
            with mock.patch.object(MODULE, "STAGE", stage):
                with self.assertRaisesRegex(
                    MODULE.SemanticError,
                    "source AnimationClip hash drifted",
                ):
                    MODULE.build_contract()

    def test_tracked_value_and_tangent_mutations_fail_digest_gate(self) -> None:
        for field in ("values", "inTangents", "outTangents"):
            mutated = copy.deepcopy(self.contract)
            mutated["clips"][0]["curves"][0][field][1] = MODULE.f32(
                mutated["clips"][0]["curves"][0][field][1] + 0.125
            )
            with self.subTest(field=field), self.assertRaisesRegex(
                MODULE.SemanticError,
                "curve digest drifted",
            ):
                MODULE.validate_contract(mutated)

    @unittest.skipUnless(generated_available(), "ignored generated .anim cache is unavailable")
    def test_generated_clips_match_exact_tracked_payload(self) -> None:
        for clip in self.contract["clips"]:
            MODULE.validate_actual_curves(clip, self.actual_for(clip))

    @unittest.skipUnless(generated_available(), "ignored generated .anim cache is unavailable")
    def test_generated_key_and_tangent_drift_fail(self) -> None:
        clip = self.contract["clips"][0]
        actual = self.actual_for(clip)
        binding = sorted(actual)[0]
        actual[binding][0]["value"] += 0.125
        with self.assertRaisesRegex(MODULE.SemanticError, "key time/value drifted"):
            MODULE.validate_actual_curves(clip, actual)

        actual = self.actual_for(clip)
        actual[binding][1]["outTangent"] += 0.25
        with self.assertRaisesRegex(MODULE.SemanticError, "tangent drifted"):
            MODULE.validate_actual_curves(clip, actual)

    @unittest.skipUnless(generated_available(), "ignored generated .anim cache is unavailable")
    def test_missing_and_extra_generated_binding_fail(self) -> None:
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
