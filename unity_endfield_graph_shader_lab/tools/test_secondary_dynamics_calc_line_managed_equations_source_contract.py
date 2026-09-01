import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Animation"
EDITOR = ROOT / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
CONTRACT = (
    ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
    / "secondary_dynamics_post_proxy_contract.json"
)
HELPER = RUNTIME / "EndfieldSecondaryDynamicsCalcLineManagedEquations.cs"
VERIFIER = EDITOR / "EndfieldSecondaryDynamicsCalcLineManagedEquationsVerifier.cs"
TYPE_NAME = "EndfieldSecondaryDynamicsCalcLineManagedEquations"


class CalcLineManagedEquationsSourceContractTests(unittest.TestCase):
    def test_native_contract_keeps_runtime_route_fail_closed(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertTrue(contract["calc_line_child_traversal_recovered"])
        self.assertTrue(contract["calc_line_managed_worker_equations_recovered"])
        self.assertTrue(contract["calc_line_managed_worker_degeneracy_branches_recovered"])
        self.assertTrue(contract["calc_line_kernel_wrapper_route_recovered"])
        self.assertTrue(
            contract["calc_line_directcall_managed_fallback_equivalence_closed"]
        )
        # The exact SSE2/AVX2 Burst target identity is now statically closed.
        # The broader normal/tangent numeric claim and the branch selected for
        # a retail frame are not, so the runtime route and its IFix-dependent
        # FromToRotation state must remain fail closed.
        self.assertFalse(contract["calc_line_normal_tangent_numerics_recovered"])
        self.assertTrue(contract["calc_line_burst_function_pointer_target_closed"])
        self.assertFalse(contract["selected_calc_line_execution_route_closed"])
        self.assertFalse(contract["from_to_rotation_ifix_patch_state_closed"])
        self.assertFalse(contract["solver_implemented"])
        self.assertFalse(contract["retail_equivalent"])
        self.assertFalse(contract["capture_used_as_implementation_source"])

    def test_helper_transcribes_closed_equation_tokens(self):
        source = HELPER.read_text(encoding="utf-8")
        required = (
            "public const byte FlagMove = 0x02;",
            "public const uint ChildLocalStartMask = 0x000fffffU;",
            "public const int ChildCountShift = 20;",
            "directionAccumulator = restVector;",
            "MultiplyQuaternionBinary32(parent.rotation, signedLocalRotation)",
            "MultiplyQuaternionBinary32(parentFromTo, parent.rotation)",
            "u.x > u.y && u.x > u.z",
            "Math.Abs(dot + 1.0) < ParallelEpsilon",
            "Math.Abs(1.0 - dot) < ParallelEpsilon",
            "float halfAngle = MultiplyBinary32(scaledAngle, 0.5f);",
            "K.FloatSinCosBinary32(halfAngle, out float sine, out float cosine);",
            "[MethodImpl(MethodImplOptions.NoInlining)]",
        )
        for token in required:
            self.assertIn(token, source)
        self.assertIn("value = default;\n                    return false;", source)
        for forbidden in (
            "using UnityEngine",
            "MonoBehaviour",
            "GameObject",
            "FrameCoordinator",
            "OwnerSolver",
            "LateUpdate(",
        ):
            self.assertNotIn(forbidden, source)

    def test_helper_is_not_connected_to_runtime_or_generated_assets(self):
        unexpected_runtime_references = []
        for path in RUNTIME.glob("*.cs"):
            if path == HELPER:
                continue
            if TYPE_NAME in path.read_text(encoding="utf-8"):
                unexpected_runtime_references.append(path.name)
        self.assertEqual(unexpected_runtime_references, [])

        generated_root = ROOT / "Assets/EndfieldGraphShaderLab/Generated"
        unexpected_assets = []
        for suffix in ("*.prefab", "*.unity", "*.asset"):
            for path in generated_root.rglob(suffix):
                if TYPE_NAME in path.read_text(encoding="utf-8", errors="ignore"):
                    unexpected_assets.append(str(path.relative_to(ROOT)))
        self.assertEqual(unexpected_assets, [])

    def test_verifier_covers_golden_properties_and_fail_closed_boundary(self):
        source = VERIFIER.read_text(encoding="utf-8")
        for method in (
            "VerifyPackedChildIndex",
            "VerifyParallelAndQuarterTurnGoldenCases",
            "VerifyAntiparallelAxisSelection",
            "VerifyBinary32HelperGrouping",
            "VerifyParentAndChildEquations",
            "VerifyNonMoveAssignmentProperty",
            "VerifyEmptyAndUndefinedBranchesFailClosed",
        ):
            self.assertIn(method + "();", source)
        self.assertIn("zero FromTo input must fail closed", source)
        self.assertIn("negative-X antiparallel zero-axis branch must fail closed", source)
        self.assertIn("non-move assigns direction accumulator", source)
        self.assertIn("0x3f3504f4U, 0x3f3504f3U", source)
        self.assertIn("BitConverter.SingleToInt32Bits", source)
        self.assertNotIn("Tolerance", source)
        self.assertNotIn("Mathf.Abs", source)


if __name__ == "__main__":
    unittest.main()
