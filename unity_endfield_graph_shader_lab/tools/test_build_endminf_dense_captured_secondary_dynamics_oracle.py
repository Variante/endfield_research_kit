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


if __name__ == "__main__":
    unittest.main()
