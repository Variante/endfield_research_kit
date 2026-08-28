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
        cls.report = MODULE.build_complete_same_session_report(
            MODULE.DEFAULT_BASE_ORACLE,
            MODULE.DEFAULT_COMPLETE_DECODED,
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

    def test_complete_same_session_replay_covers_primary_and_transparent_cape(self):
        self.assertEqual(self.report["schema"], MODULE.OUTPUT_SCHEMA)
        self.assertEqual((self.report["frameCount"], self.report["boneCount"]),
                         (144, 80))
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
        self.assertTrue(set(extension["bonePaths"]).issubset(
            self.report["frames"][0]["ownerBoneMatrices"][index]["path"]
            for index in range(self.report["boneCount"])
        ))

    def test_qpc_samples_retain_previous_current_palette_pairs(self):
        extension = self.report["transparentCapeExtension"]
        self.assertEqual(extension["sampleCount"], 144)
        frames = self.report["frames"]
        self.assertEqual(
            [row["capturePalette"] for row in frames[:2]],
            ["previous", "current"],
        )
        self.assertEqual(frames[0]["capturePresentedFrame"], 1747)
        self.assertEqual(frames[1]["capturePresentedFrame"], 1747)
        self.assertAlmostEqual(
            frames[1]["phaseSeconds"] - frames[0]["phaseSeconds"],
            1.0 / 60.0,
        )
        peak = [row for row in frames
                if row["capturePresentedFrame"] == 1977
                and row["capturePalette"] == "current"]
        self.assertEqual(len(peak), 1)
        self.assertAlmostEqual(peak[0]["phaseSeconds"], 4.35)

    def test_same_session_extension_passes_temporal_and_session_gates(self):
        extension = self.report["transparentCapeExtension"]
        self.assertTrue(extension["runtimeEligible"])
        self.assertEqual(extension["maximumSampleGapFrames"], 15)
        self.assertEqual(extension["primaryMaximumSampleGapFrames"], 15)
        self.assertTrue(extension["sameSessionPrimaryReplay"])
        self.assertEqual(extension["runtimeAdmissionFailures"], [])


if __name__ == "__main__":
    unittest.main()
