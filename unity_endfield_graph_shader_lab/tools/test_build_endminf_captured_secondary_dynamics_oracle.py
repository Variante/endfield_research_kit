import importlib.util
import math
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "build_endminf_captured_secondary_dynamics_oracle.py"
)
SPEC = importlib.util.spec_from_file_location("captured_dynamics_oracle", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CapturedSecondaryDynamicsOracleTests(unittest.TestCase):
    def test_matrix_inverse_round_trip(self):
        matrix = [
            [0.0, -1.0, 0.0, 2.0],
            [1.0, 0.0, 0.0, 3.0],
            [0.0, 0.0, 1.0, 4.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        result = MODULE.multiply(matrix, MODULE.inverse(matrix))
        for row in range(4):
            for column in range(4):
                self.assertAlmostEqual(
                    result[row][column], 1.0 if row == column else 0.0
                )

    def test_parses_unity_bind_pose_rows(self):
        values = [1.0 if row == column else 0.0
                  for row in range(4) for column in range(4)]
        lines = ["  m_BindPose:"]
        for index, value in enumerate(values):
            row, column = divmod(index, 4)
            prefix = "  - " if index == 0 else "    "
            lines.append(f"{prefix}e{row}{column}: {value}")
        lines.append("  m_BoneNameHashes: 00")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mesh.asset"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            matrices = MODULE.parse_bindposes(path)
        self.assertEqual(matrices, [[
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]])

    def test_reports_translation_and_rotation_motion(self):
        previous = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        current = [
            [0.0, -1.0, 0.0, 3.0],
            [1.0, 0.0, 0.0, 4.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        translation, rotation = MODULE.motion_delta(current, previous)
        self.assertAlmostEqual(translation, 5.0)
        self.assertAlmostEqual(rotation, 90.0)
        self.assertLess(MODULE.orthonormality_error(current), 1e-12)

    def test_reference_alignment_preserves_presented_frame_delta(self):
        self.assertEqual(MODULE.reference_source_frame(1887), 117)
        self.assertEqual(MODULE.reference_source_frame(1905), 135)
        self.assertEqual(MODULE.reference_source_frame(2561), 791)


if __name__ == "__main__":
    unittest.main()
