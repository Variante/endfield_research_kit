#!/usr/bin/env python3
"""Focused tests for the static secondary-dynamics input contract."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_solver_inputs as builder  # noqa: E402


class SecondaryDynamicsSolverInputTests(unittest.TestCase):
    @staticmethod
    def _endminf_fixture() -> tuple[dict, dict[int, dict]]:
        owner = builder.load_json(builder.OWNER_CONTRACT)
        actor = owner["actors"]["endminf"]
        objects = builder._object_index(
            builder.EVIDENCE_ROOT / "endminf_postmodel_export/MonoBehaviour"
        )
        return actor, objects

    def test_parameter_and_constraint_views_preserve_authored_values(self) -> None:
        # Use the real source field names so this test catches accidental
        # renaming of the contract projection.
        parameter_names = (
            "clothType",
            "connectionMode",
            "rotationalInterpolation",
            "rootRotation",
            "updateMode",
            "clothAnimatorAbilityLODThreshold",
            "clothAnimatorLODThreshold",
            "clothLodFadeTime",
            "clothSimulateWeight",
            "resetSimulationToAnimationPoseWhenWeightLow",
            "resetSimulationToAnimationPoseWeightThreshold",
            "animationPoseRatio",
            "reductionSetting",
            "customSkinningSetting",
            "normalAlignmentSetting",
            "cullingSettings",
            "normalAxis",
            "gravity",
            "gravityDirection",
            "gravityFalloff",
            "stablizationTimeAfterReset",
            "blendWeight",
        )
        constraint_names = (
            "damping",
            "radius",
            "inertiaConstraint",
            "tetherConstraint",
            "distanceConstraint",
            "triangleBendingConstraint",
            "angleRestorationConstraint",
            "angleLimitConstraint",
            "motionConstraint",
            "colliderCollisionConstraint",
            "selfCollisionConstraint",
            "wind",
            "springConstraint",
        )
        serialized = {name: {"authored": name} for name in parameter_names + constraint_names}
        original = copy.deepcopy(serialized)
        self.assertEqual(builder._parameter_view(serialized), {name: serialized[name] for name in parameter_names})
        self.assertEqual(builder._constraint_view(serialized), {name: serialized[name] for name in constraint_names})
        self.assertEqual(serialized, original)

    def test_proxy_transform_bindings_are_exact_and_fail_closed(self) -> None:
        serialized2 = {
            "preBuildData": {
                "uniquePreBuildData": {
                    "proxyMesh": {
                        "transformData": {
                            "transformArray": [
                                {"m_FileID": 0, "m_PathID": 11},
                                {"m_FileID": 0, "m_PathID": 0},
                                {"m_FileID": 0, "m_PathID": 22},
                            ]
                        }
                    }
                }
            }
        }
        self.assertEqual(
            builder._proxy_transform_bindings(
                serialized2,
                {11: "Root/A", 22: "Root/B"},
            ),
            [
                {"array_index": 0, "path_id": 11, "path": "Root/A"},
                {"array_index": 2, "path_id": 22, "path": "Root/B"},
            ],
        )

        unknown = copy.deepcopy(serialized2)
        unknown["preBuildData"]["uniquePreBuildData"]["proxyMesh"][
            "transformData"
        ]["transformArray"][2]["m_PathID"] = 33
        with self.assertRaisesRegex(ValueError, "unknown path ID 33"):
            builder._proxy_transform_bindings(unknown, {11: "Root/A"})

        duplicate = copy.deepcopy(serialized2)
        duplicate["preBuildData"]["uniquePreBuildData"]["proxyMesh"][
            "transformData"
        ]["transformArray"][2]["m_PathID"] = 11
        with self.assertRaisesRegex(ValueError, "repeats path ID 11"):
            builder._proxy_transform_bindings(duplicate, {11: "Root/A"})

        empty = copy.deepcopy(serialized2)
        empty["preBuildData"]["uniquePreBuildData"]["proxyMesh"][
            "transformData"
        ]["transformArray"] = []
        with self.assertRaisesRegex(ValueError, "empty or malformed"):
            builder._proxy_transform_bindings(empty, {})

    def test_real_endminf_proxy_transforms_resolve_to_hierarchy(self) -> None:
        actor, objects = self._endminf_fixture()
        transform_paths, _ = builder._manifest_maps(actor)
        observed_counts = []
        for row in actor["cloths"]:
            payload = objects[int(row["path_id"])]
            bindings = builder._proxy_transform_bindings(
                payload["serializeData2"],
                transform_paths,
            )
            observed_counts.append(len(bindings))
            self.assertEqual(
                [binding["array_index"] for binding in bindings],
                list(range(len(bindings))),
            )
        self.assertEqual(observed_counts, [7, 31, 21, 71])

    def test_generated_contract_exposes_three_targets_and_is_fail_closed(self) -> None:
        observed = builder.build_contract()
        raw_output = builder.OUTPUT.read_bytes()
        self.assertLess(len(raw_output), 1_500_000)
        payload = json.loads(raw_output.decode("utf-8"))
        self.assertEqual(observed, payload)
        self.assertEqual(
            set(payload["actors"]),
            {"endminf", "pelica", "chen"},
        )
        self.assertFalse(payload["implementation_boundary"]["solver_implemented"])
        self.assertFalse(payload["implementation_boundary"]["retail_equivalent"])
        self.assertEqual(payload["native_lifecycle"]["player_loop"]["status"], "partial_unresolved_first_system_anchor")
        self.assertEqual(
            {name: len(actor["cloths"]) for name, actor in payload["actors"].items()},
            {"endminf": 4, "pelica": 7, "chen": 6},
        )
        for actor in payload["actors"].values():
            self.assertTrue(actor["colliders"])
            for cloth in actor["cloths"]:
                solver_input = cloth["solver_input"]
                self.assertTrue(solver_input["selection_data"]["positions"])
                self.assertIn("gravity", solver_input["parameters"])
                self.assertIn("springConstraint", solver_input["constraints"])
                self.assertIn("preBuildData", solver_input["prebuild_data"])
                transform_array = solver_input["prebuild_data"][
                    "uniquePreBuildData"
                ]["proxyMesh"]["transformData"]["transformArray"]
                expected_ids = [
                    (index, int(value["m_PathID"]))
                    for index, value in enumerate(transform_array)
                    if int(value["m_PathID"]) != 0
                ]
                bindings = solver_input["proxy_transform_bindings"]
                self.assertEqual(
                    [(row["array_index"], row["path_id"]) for row in bindings],
                    expected_ids,
                )
                self.assertEqual(cloth["proxy_transform_bindings"], bindings)
                self.assertFalse(solver_input.get("solver_implemented", False))

    def test_owner_path_root_and_collider_drift_is_rejected(self) -> None:
        actor, objects = self._endminf_fixture()

        owner_drift = copy.deepcopy(actor)
        owner_drift["cloths"][0]["game_object_path"] = "not-a-real-owner"
        with self.assertRaisesRegex(ValueError, "owner GameObject path/PPtr drift"):
            builder._validate_actor_rows("endminf", owner_drift, objects)

        root_drift = copy.deepcopy(actor)
        root_drift["cloths"][0]["root_bones"][0]["path"] = "not-a-real-root"
        with self.assertRaisesRegex(ValueError, "hierarchy root evidence drift"):
            builder._validate_actor_rows("endminf", root_drift, objects)

        ignored_drift = copy.deepcopy(actor)
        ignored_drift["cloths"][0]["ignored_root_bones"] = [{"path_id": 1, "path": "fake"}]
        with self.assertRaisesRegex(ValueError, "ignored-root PPtr list drift"):
            builder._validate_actor_rows("endminf", ignored_drift, objects)

        collider_drift = copy.deepcopy(actor)
        collider_drift["cloths"][0]["colliders"] = []
        with self.assertRaisesRegex(ValueError, "collider PPtr list drift"):
            builder._validate_actor_rows("endminf", collider_drift, objects)

    def test_unknown_dynamic_script_is_rejected(self) -> None:
        actor, objects = self._endminf_fixture()
        mutated = copy.deepcopy(objects)
        cloth_id = int(actor["cloths"][0]["path_id"])
        mutated[cloth_id]["m_Script"]["m_PathID"] = 123456789
        with self.assertRaisesRegex(ValueError, "owner drift in dynamic path IDs"):
            builder._validate_actor_rows("endminf", actor, mutated)

        collider_id = int(actor["colliders"][0]["path_id"])
        mutated = copy.deepcopy(objects)
        mutated[collider_id]["m_Script"]["m_PathID"] = 987654321
        with self.assertRaisesRegex(ValueError, "owner drift in dynamic path IDs"):
            builder._validate_actor_rows("endminf", actor, mutated)

    def test_playerloop_source_hash_mismatch_is_rejected(self) -> None:
        owner = builder.load_json(builder.OWNER_CONTRACT)
        player_loop = builder.load_json(builder.PLAYER_LOOP_CONTRACT)
        player_loop["sourceHashes"]["GameAssembly.dll"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "GameAssembly hash"):
            builder._validate_player_loop(owner, player_loop)

        player_loop = builder.load_json(builder.PLAYER_LOOP_CONTRACT)
        player_loop["sourceHashes"]["global-metadata.dat"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "metadata hash"):
            builder._validate_player_loop(owner, player_loop)

        player_loop = builder.load_json(builder.PLAYER_LOOP_CONTRACT)
        player_loop["source"]["nativeEvidence"] = "runtime_native.json"
        with self.assertRaisesRegex(ValueError, "source path spoof"):
            builder._validate_player_loop(owner, player_loop)

        player_loop = builder.load_json(builder.PLAYER_LOOP_CONTRACT)
        player_loop["schema"] = "spoofed.schema"
        with self.assertRaisesRegex(ValueError, "unexpected PlayerLoop schema"):
            builder._validate_player_loop(owner, player_loop)

        player_loop = builder.load_json(builder.PLAYER_LOOP_CONTRACT)
        player_loop["status"] = "validated"
        with self.assertRaisesRegex(ValueError, "unexpected PlayerLoop status"):
            builder._validate_player_loop(owner, player_loop)

        player_loop = builder.load_json(builder.PLAYER_LOOP_CONTRACT)
        player_loop["evidenceHashes"]["playerloop_metadata.json"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "evidence hash drift"):
            builder._validate_player_loop(owner, player_loop)

    def test_target_filter_hash_and_pathid_drift_is_rejected(self) -> None:
        actor, objects = self._endminf_fixture()
        drift = copy.deepcopy(actor)
        drift["target_filter"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "target filter hash/size drift"):
            builder._validate_actor_rows("endminf", drift, objects)

        drift = copy.deepcopy(actor)
        drift["target_filter"]["repo_path"] = "runtime_native.json"
        with self.assertRaisesRegex(ValueError, "target filter path spoof/drift"):
            builder._validate_actor_rows("endminf", drift, objects)

        drift = copy.deepcopy(actor)
        drift["hierarchy_name_map"]["repo_path"] = (
            "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/"
            "Generated/Characters/Playable/Pelica/pelica_ui_recovery_manifest.json"
        )
        with self.assertRaisesRegex(ValueError, "hierarchy evidence character drift"):
            builder._validate_actor_rows("endminf", drift, objects)


if __name__ == "__main__":
    unittest.main()
