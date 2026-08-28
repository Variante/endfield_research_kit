import importlib.util
import math
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "build_endminf_dense_captured_secondary_dynamics_oracle.py"
)
SPEC = importlib.util.spec_from_file_location("dense_oracle", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DenseCapturedSecondaryDynamicsOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = MODULE.build_report(
            MODULE.DEFAULT_BASE_ORACLE,
            MODULE.DEFAULT_DENSE_DECODED,
            MODULE.DEFAULT_REFERENCE_MATCHED_DECODED,
            MODULE.DEFAULT_TRANSPARENT_CAPE_DECODED,
        )

    def test_pose_matrix_round_trip(self):
        matrix = [
            [0.0, -1.0, 0.0, 2.0],
            [1.0, 0.0, 0.0, 3.0],
            [0.0, 0.0, 1.0, 4.0],
        ]
        result = MODULE.pose_matrix(MODULE.matrix_pose(matrix))
        for row in range(3):
            for column in range(4):
                self.assertAlmostEqual(result[row][column], matrix[row][column])

    def test_interpolation_uses_position_and_shortest_rotation(self):
        identity = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
        half_turn = ((2.0, 4.0, 6.0), (0.0, 0.0, 1.0, 0.0))
        pose = MODULE.interpolate([(10, identity), (20, half_turn)], 15)
        self.assertEqual(pose[0], (1.0, 2.0, 3.0))
        self.assertAlmostEqual(abs(pose[1][2]), math.sqrt(0.5))
        self.assertAlmostEqual(abs(pose[1][3]), math.sqrt(0.5))

    def test_interpolation_rejects_extrapolation(self):
        pose = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
        with self.assertRaisesRegex(MODULE.DenseOracleError, "outside"):
            MODULE.interpolate([(10, pose), (20, pose)], 9)

    def test_capture_splits_at_largest_gap(self):
        first, second = MODULE.split_bursts(
            list(range(100, 500, 8)) + list(range(800, 1200, 8))
        )
        self.assertEqual((len(first), len(second)), (50, 50))

    def test_transparent_cape_extension_is_classified_without_primary_drift(self):
        self.assertEqual(self.report["schema"], MODULE.OUTPUT_SCHEMA)
        self.assertEqual((self.report["frameCount"], self.report["boneCount"]),
                         (145, 74))
        extension = self.report["transparentCapeExtension"]
        self.assertEqual(extension["weightedBoneAccounting"], {
            "meshBoneCount": 29,
            "primaryReplay": 19,
            "transparentCapeExtension": 6,
            "animatorBody": 4,
        })
        self.assertEqual(
            [path.rsplit("/", 1)[-1] for path in extension["bonePaths"]],
            MODULE.TRANSPARENT_CAPE_BONE_NAMES,
        )
        self.assertFalse(set(extension["bonePaths"]).intersection(
            self.report["frames"][0]["ownerBoneMatrices"][index]["path"]
            for index in range(self.report["boneCount"])
        ))

    def test_transparent_cape_samples_retain_explicit_two_replay_mapping(self):
        extension = self.report["transparentCapeExtension"]
        expected_sources = sorted(
            source + delta
            for source in MODULE.TRANSPARENT_CAPE_CURRENT_SOURCE_FRAMES.values()
            for delta in (-1, 0)
        )
        self.assertEqual(
            [row["playbackSourceFrame"] for row in extension["samples"]],
            expected_sources,
        )
        for row in extension["samples"]:
            self.assertEqual(len(row["boneLocalMatrices"]), 6)
            for bone, parent in zip(
                row["boneLocalMatrices"], extension["parentPaths"]
            ):
                self.assertEqual(bone["parentPath"], parent)
                self.assertEqual(len(bone["localSpace3x4"]), 3)
                self.assertTrue(all(len(matrix_row) == 4
                                    for matrix_row in bone["localSpace3x4"]))

    def test_sparse_extension_fails_closed_on_temporal_and_session_gates(self):
        extension = self.report["transparentCapeExtension"]
        self.assertFalse(extension["runtimeEligible"])
        self.assertEqual(extension["maximumSampleGapFrames"], 96)
        self.assertEqual(extension["primaryMaximumSampleGapFrames"], 33)
        self.assertFalse(extension["sameSessionPrimaryReplay"])
        self.assertEqual(len(extension["runtimeAdmissionFailures"]), 3)


if __name__ == "__main__":
    unittest.main()
