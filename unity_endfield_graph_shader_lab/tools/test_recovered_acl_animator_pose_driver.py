#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from unity_endfield_graph_shader_lab.tools.build_endminf_overview_acl_binding_contract import (
    build_contract,
    serialize_contract,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Runtime"
    / "Animation"
    / "RecoveredAclAnimatorPoseDriver.cs"
)
IMPORTER = (
    ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Editor"
    / "CharacterRecovery"
    / "RecoveredAclClipDataImporter.cs"
)
SETUP = (
    ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Editor"
    / "CharacterRecovery"
    / "EndfieldManifestCharacterSetup.cs"
)
CONTRACT = (
    ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "OriginalData"
    / "CharInfoPresentation"
    / "endminf_overview_acl_binding_asymmetry_contract.json"
)
GENERATOR = Path(__file__).with_name(
    "build_endminf_overview_acl_binding_contract.py"
)


def write_defaults_model(
    reference: tuple[str, str, str],
    sample: tuple[str, str, str],
    bound_components: int,
    all_state_components: int,
) -> tuple[str | None, str | None, str | None]:
    return tuple(
        (sample[index] if bound_components & bit else reference[index])
        if all_state_components & bit
        else None
        for index, bit in enumerate((1, 2, 4))
    )


def stale_state_mutation_model(
    prior: tuple[str, str, str],
    sample: tuple[str, str, str],
    bound_components: int,
) -> tuple[str, str, str]:
    return tuple(
        sample[index] if bound_components & bit else prior[index]
        for index, bit in enumerate((1, 2, 4))
    )


def acl_fixture(clip_name: str, bindings: list[tuple[str, int, int]]) -> str:
    lines = [
        "%YAML 1.1",
        "RecoveredAclClipData:",
        f"  sourceClipName: {clip_name}",
        "  bindings:",
    ]
    for path, track_index, components in bindings:
        lines.extend((
            f"  - transformPath: {path}",
            f"    trackIndex: {track_index}",
            f"    components: {components}",
        ))
    return "\n".join(lines) + "\n"


class RecoveredAclAnimatorPoseDriverTests(unittest.TestCase):
    def test_driver_uses_source_state_and_acl_sampling(self):
        source = SOURCE.read_text(encoding="utf-8")
        for required in (
            "Animator.StringToHash(state.fullStatePath)",
            "GetCurrentAnimatorStateInfo(0)",
            "GetNextAnimatorStateInfo(0)",
            "GetAnimatorTransitionInfo(0).normalizedTime",
            "RecoveredAclPoseEvaluator.TrySampleTrack",
            "RecoveredAclPoseEvaluator.StableVectorLerp",
            "RecoveredAclPoseEvaluator.TryStableQuaternionLerp",
            "poseRoot.Find(binding.transformPath)",
        ):
            self.assertIn(required, source)

    def test_driver_contains_no_actor_pose_or_curve_constants(self):
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "endminf",
            "overview_start",
            "overview_loop",
            "animationcurve",
            "quaternion.slerp",
            "quaternion.lerp",
            "localposition = new vector3",
            "localrotation = new quaternion",
        ):
            self.assertNotIn(forbidden, source.lower())

    def test_driver_runs_before_secondary_dynamics_late_boundary(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("[DefaultExecutionOrder(-70)]", source)
        self.assertIn("private void LateUpdate()", source)
        self.assertNotIn("PlayerLoop.SetPlayerLoop", source)

    def test_driver_applies_write_defaults_for_asymmetric_state_bindings(self):
        source = SOURCE.read_text(encoding="utf-8")
        setup = SETUP.read_text(encoding="utf-8")
        self.assertIn(
            "public RecoveredAclTransformComponentMask allStateComponents;",
            source,
        )
        self.assertIn("path.allStateComponents |= binding.components;", source)
        self.assertIn(
            "ApplyComponents(path.transform, path.allStateComponents, effective);",
            source,
        )
        self.assertIn(
            "RecoveredAclTransformComponentMask components =\n"
            "                    path.allStateComponents;",
            source,
        )
        self.assertIn("Every recovered overview Animator state has Write Defaults", source)
        single_start = source.index("private void ApplySingleState")
        transition_start = source.index("private void ApplyTransition")
        single_body = source[single_start:transition_start]
        self.assertNotIn("if (binding.trackIndex < 0)\n                    continue;", single_body)
        self.assertIn("RecoveredAclQvvSample sample = ReferenceSample(path);", single_body)
        controller_start = setup.index(
            "private static AnimatorController BuildRecoveredOverviewAnimatorController"
        )
        controller_end = setup.index(
            "private static AnimationClip SaveAnimatorClipCopy",
            controller_start,
        )
        controller_body = setup[controller_start:controller_end]
        self.assertIn("waiting.writeDefaultValues = true;", controller_body)
        self.assertIn("entrance.writeDefaultValues = true;", controller_body)
        self.assertIn("settled.writeDefaultValues = true;", controller_body)

    def test_endminf_acl_data_has_hair_cape_and_thigh_cloth_asymmetry(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        validate_contract(contract)
        self.assertEqual(
            "endfield.endminf.overview-acl-binding-asymmetry.v1",
            contract["schema"],
        )
        self.assertEqual(
            {"translation": 1, "rotation": 2, "scale": 4},
            contract["componentMask"],
        )
        self.assertEqual(
            "A_actor_endminf_ui_overview_start",
            contract["sources"]["start"]["sourceClipName"],
        )
        self.assertEqual(
            "A_actor_endminf_ui_overview_loop",
            contract["sources"]["loop"]["sourceClipName"],
        )
        for source in contract["sources"].values():
            self.assertGreater(source["size"], 0)
            self.assertEqual(64, len(source["sha256"]))
            int(source["sha256"], 16)

        start_rows = contract["startOnlyBindings"]
        loop_rows = contract["loopOnlyBindings"]
        component_rows = contract["sharedComponentDifferences"]
        summary = contract["summary"]
        self.assertEqual(summary["startOnlyBindingPathCount"], len(start_rows))
        self.assertEqual(summary["loopOnlyBindingPathCount"], len(loop_rows))
        self.assertEqual(
            summary["sharedComponentDifferenceCount"], len(component_rows)
        )
        self.assertEqual(
            contract["sources"]["start"]["bindingCount"],
            summary["sharedBindingPathCount"] + len(start_rows),
        )
        self.assertEqual(
            contract["sources"]["loop"]["bindingCount"],
            summary["sharedBindingPathCount"] + len(loop_rows),
        )
        self.assertTrue(component_rows)
        start_only = {row["transformPath"]: row["components"] for row in start_rows}
        loop_only = {row["transformPath"]: row["components"] for row in loop_rows}
        self.assertEqual(len(start_rows), len(start_only))
        self.assertEqual(len(loop_rows), len(loop_only))
        self.assertTrue(start_only)
        self.assertTrue(loop_only)

        expected_start_only = {
            "hair_L_d_01_jnt/hair_L_d_02_jnt/hair_L_d_03_jnt/"
            "hair_L_d_04_jnt/hair_L_d_05_jnt": 1,
            "clothes_pifeng_R_b_0_jnt": 2,
            "clothes_yifu_L_a_1_jnt": 2,
            "clothes_yifu_R_a_1_jnt": 2,
        }
        expected_loop_only = {
            "hair_L_a_01_jnt": 2,
            "hair_L_b_01_jnt": 2,
            "hair_L_c_01_jnt": 2,
            "hair_L_l_01_jnt/hair_L_l_02_jnt": 2,
        }
        for suffix, components in expected_start_only.items():
            matches = [path for path in start_only if path.endswith(suffix)]
            self.assertEqual([suffix], [path[-len(suffix):] for path in matches])
            self.assertEqual(components, start_only[matches[0]])
        for suffix, components in expected_loop_only.items():
            matches = [path for path in loop_only if path.endswith(suffix)]
            self.assertEqual([suffix], [path[-len(suffix):] for path in matches])
            self.assertEqual(components, loop_only[matches[0]])

        shared_hair_or_cloth = [
            row for row in component_rows
            if "hair_" in row["transformPath"] or
            "clothes_" in row["transformPath"]
        ]
        self.assertTrue(shared_hair_or_cloth)
        self.assertTrue(all(
            row["startComponents"] != row["loopComponents"]
            for row in shared_hair_or_cloth
        ))
        expected_component_differences = {
            "hair_L_d_01_jnt/hair_L_d_02_jnt": (3, 2),
            "clothes_pifeng_L_a_0_jnt": (3, 2),
        }
        for suffix, expected in expected_component_differences.items():
            matches = [
                row for row in component_rows
                if row["transformPath"].endswith(suffix)
            ]
            self.assertEqual(1, len(matches))
            self.assertEqual(
                expected,
                (matches[0]["startComponents"], matches[0]["loopComponents"]),
            )

    def test_binding_contract_generator_is_deterministic_and_check_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            start = root / "start.asset"
            loop = root / "loop.asset"
            output = root / "contract.json"
            start.write_text(acl_fixture(
                "A_actor_endminf_ui_overview_start",
                [("Root/Common", 0, 3), ("Root/StartOnly", 1, 1)],
            ), encoding="utf-8")
            loop.write_text(acl_fixture(
                "A_actor_endminf_ui_overview_loop",
                [("Root/Common", 0, 2), ("Root/LoopOnly", 1, 2)],
            ), encoding="utf-8")
            first = serialize_contract(build_contract(start, loop))
            second = serialize_contract(build_contract(start, loop))
            self.assertEqual(first, second)
            output.write_text(first, encoding="utf-8", newline="\n")

            command = [
                sys.executable,
                str(GENERATOR),
                "--start", str(start),
                "--loop", str(loop),
                "--output", str(output),
                "--check",
            ]
            checked = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(0, checked.returncode, checked.stderr)
            output.write_text(
                first.replace(
                    "source_clip_binding_asymmetry_closed",
                    "mutated",
                    1,
                ),
                encoding="utf-8",
                newline="\n",
            )
            rejected = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("invalid ACL binding contract", rejected.stderr)

    def test_binding_contract_generator_rejects_an_unparsed_source_row(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            start = root / "start.asset"
            loop = root / "loop.asset"
            start.write_text(
                acl_fixture(
                    "A_actor_endminf_ui_overview_start",
                    [("Root/Common", 0, 3), ("Root/StartOnly", 1, 1)],
                ).replace(
                    "  - transformPath: Root/StartOnly",
                    "  - transformPath: Root/SilentlyIgnored\n"
                    "    trackIndex: 99\n"
                    "    malformedComponents: 2\n"
                    "  - transformPath: Root/StartOnly",
                    1,
                ),
                encoding="utf-8",
            )
            loop.write_text(
                acl_fixture(
                    "A_actor_endminf_ui_overview_loop",
                    [("Root/Common", 0, 2), ("Root/LoopOnly", 1, 2)],
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError, "malformed or contains unparsed fields"
            ):
                build_contract(start, loop)

    def test_compact_binding_contract_self_validation_fails_closed(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        validate_contract(contract)
        attacks = []
        for mutation in (
            lambda value: value["sources"]["start"].__setitem__(
                "sha256", "not-a-sha256"
            ),
            lambda value: value["summary"].__setitem__(
                "startOnlyBindingPathCount", 0
            ),
            lambda value: value["startOnlyBindings"].append(
                dict(value["startOnlyBindings"][0])
            ),
            lambda value: value["sharedComponentDifferences"][0].__setitem__(
                "loopComponents",
                value["sharedComponentDifferences"][0]["startComponents"],
            ),
        ):
            mutated = json.loads(json.dumps(contract))
            mutation(mutated)
            attacks.append(mutated)
        for mutated in attacks:
            with self.assertRaises(ValueError):
                validate_contract(mutated)

    def test_compact_binding_contract_validate_only_needs_no_source_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "contract.json"
            output.write_text(CONTRACT.read_text(encoding="utf-8"), encoding="utf-8")
            checked = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--start", str(root / "absent-start.asset"),
                    "--loop", str(root / "absent-loop.asset"),
                    "--output", str(output),
                    "--validate-only",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, checked.returncode, checked.stderr)
            self.assertIn("validated", checked.stdout)

    def test_settled_state_defaulting_model_rejects_stale_component_mutation(self):
        reference = ("reference-position", "reference-rotation", "reference-scale")
        sample = ("sample-position", "sample-rotation", "sample-scale")
        stale = ("stale-position", "stale-rotation", "stale-scale")
        # Rotation is present in the settled state; translation and scale are
        # present elsewhere in the controller and therefore use Write Defaults.
        actual = write_defaults_model(reference, sample, 2, 1 | 2 | 4)
        mutated = stale_state_mutation_model(stale, sample, 2)
        self.assertEqual(
            ("reference-position", "sample-rotation", "reference-scale"),
            actual,
        )
        self.assertEqual(
            ("stale-position", "sample-rotation", "stale-scale"),
            mutated,
        )
        self.assertNotEqual(actual, mutated)

    def test_importer_is_job_driven_and_runtime_validated(self):
        source = IMPORTER.read_text(encoding="utf-8")
        self.assertIn("ENDFIELD_RECOVERED_ACL_IMPORT_JOB", source)
        self.assertIn("JsonUtility.FromJsonOverwrite", source)
        self.assertIn("imported.TryValidate(out string failure)", source)
        self.assertNotIn("endminf", source.lower())


if __name__ == "__main__":
    unittest.main()
