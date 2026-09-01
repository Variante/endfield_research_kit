from __future__ import annotations

import json
import unittest
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
SETUP = (
    LAB / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldManifestCharacterSetup.cs"
)
ORIGINAL = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
)


class EndminfSecondaryDynamicsBuildGateTests(unittest.TestCase):
    def test_canonical_all_character_build_verifies_generated_binding(self) -> None:
        source = SETUP.read_text(encoding="utf-8")
        start = source.index("public static void BuildAllCharacterModelViewer()")
        end = source.index("[MenuItem(", start + 1)
        body = source[start:end]
        build = body.index("BuildCharacterViewer(")
        verify = body.index(
            "EndfieldSecondaryDynamicsBindingBuilder."
            "VerifyGeneratedEndminfBinding();"
        )
        complete_log = body.index("All-character model viewer complete")
        self.assertLess(build, verify)
        self.assertLess(verify, complete_log)

    def test_builder_and_runtime_captured_replay_defaults_are_off(self) -> None:
        builder = (
            LAB / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldSecondaryDynamicsBindingBuilder.cs"
        ).read_text(encoding="utf-8")
        runtime = (
            LAB / "Assets/EndfieldGraphShaderLab/Runtime/Animation"
            / "EndfieldCapturedSecondaryDynamicsReplay.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("replay.useCapturedReplay = false;", builder)
        self.assertIn("public bool useCapturedReplay = false;", runtime)

    def test_exact_calc_line_inputs_are_bound_but_runtime_route_stays_disconnected(self) -> None:
        data_source = (
            LAB / "Assets/EndfieldGraphShaderLab/Runtime/Animation"
            / "EndfieldSecondaryDynamicsData.cs"
        ).read_text(encoding="utf-8")
        builder = (
            LAB / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldSecondaryDynamicsBindingBuilder.cs"
        ).read_text(encoding="utf-8")
        owner_solver = (
            LAB / "Assets/EndfieldGraphShaderLab/Runtime/Animation"
            / "EndfieldSecondaryDynamicsOwnerSolver.cs"
        ).read_text(encoding="utf-8")
        runtime = (
            LAB / "Assets/EndfieldGraphShaderLab/Runtime/Animation"
            / "EndfieldSecondaryDynamicsRuntime.cs"
        ).read_text(encoding="utf-8")

        for declaration in (
            "public uint[] vertexChildIndexArray;",
            "public ushort[] vertexChildDataArray;",
            "public float rotationalInterpolation;",
            "public float rootRotation;",
        ):
            self.assertIn(declaration, data_source)
        for binding in (
            'UIntArray(\n                    arrays, "vertexChildIndexArray", ownerPath)',
            'UShortArray(\n                    arrays, "vertexChildDataArray", ownerPath)',
            'parameters, "rotationalInterpolation", ownerPath',
            'Float(parameters, "rootRotation", ownerPath)',
            "ValidateChildTopology(",
        ):
            self.assertIn(binding, builder)
        self.assertNotIn("EndfieldSecondaryDynamicsCalcLineManagedEquations", owner_solver)
        self.assertIn("HashMatches(data.solverInputs, data.solverInputsSha256)", runtime)
        self.assertIn("HashMatches(data.payloadDecode, data.payloadDecodeSha256)", runtime)

    def test_endminf_preserves_serialized_child_order_and_authored_rotation_scalars(self) -> None:
        payload = json.loads(
            (ORIGINAL / "secondary_dynamics_payload_decode.json").read_text(
                encoding="utf-8"
            )
        )
        solver = json.loads(
            (ORIGINAL / "secondary_dynamics_solver_inputs.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(payload["source"]["hashes_match"])
        self.assertFalse(payload["implementation_boundary"]["solver_implemented"])
        self.assertFalse(solver["implementation_boundary"]["solver_implemented"])

        payload_by_owner = {
            row["game_object_path"]: row
            for row in payload["actors"]["endminf"]["cloths"]
        }
        solver_by_owner = {
            row["game_object_path"]: row
            for row in solver["actors"]["endminf"]["cloths"]
        }
        self.assertEqual(set(payload_by_owner), set(solver_by_owner))

        for owner, row in payload_by_owner.items():
            arrays = row["proxy_mesh_arrays"]
            parent_indices = arrays["vertexParentIndices"]["values"]
            packed_indices = arrays["vertexChildIndexArray"]["values"]
            child_data = arrays["vertexChildDataArray"]["values"]
            self.assertEqual(arrays["vertexChildIndexArray"]["semantic"], "System.UInt32")
            self.assertEqual(arrays["vertexChildDataArray"]["semantic"], "System.UInt16")
            self.assertEqual(len(packed_indices), len(parent_indices))

            cursor = 0
            seen: set[int] = set()
            for parent, packed in enumerate(packed_indices):
                self.assertEqual(packed & 0x000FFFFF, cursor)
                count = packed >> 20
                children = child_data[cursor:cursor + count]
                self.assertEqual(len(children), count)
                for child in children:
                    self.assertEqual(parent_indices[child], parent)
                    self.assertNotIn(child, seen)
                    seen.add(child)
                cursor += count
            self.assertEqual(cursor, len(child_data))
            self.assertEqual(
                seen,
                {index for index, parent in enumerate(parent_indices) if parent >= 0},
            )

            parameters = solver_by_owner[owner]["solver_input"]["parameters"]
            self.assertEqual(parameters["rotationalInterpolation"], 0.5)
            self.assertEqual(parameters["rootRotation"], 0.5)

        # MC_Hair's branch at parent 17 is serialized as 19 then 18. This
        # source ordering is behaviorally relevant because the native worker
        # mutates its accumulator per child; sorting by vertex index is invalid.
        hair = payload_by_owner["MC_Hair"]["proxy_mesh_arrays"]
        packed = hair["vertexChildIndexArray"]["values"][17]
        start, count = packed & 0x000FFFFF, packed >> 20
        self.assertEqual(hair["vertexChildDataArray"]["values"][start:start + count], [19, 18])


if __name__ == "__main__":
    unittest.main()
