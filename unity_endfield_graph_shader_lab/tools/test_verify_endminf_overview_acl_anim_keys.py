import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_endminf_overview_acl_anim_keys.py")
SPEC = importlib.util.spec_from_file_location("overview_validator", MODULE_PATH)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


def anim_yaml(name, second_x=0.0):
    def key(time, value):
        return f"""      - serializedVersion: 3
        time: {time}
        value: {{x: {value[0]}, y: {value[1]}, z: {value[2]}, w: {value[3]}}}
        inSlope: {{x: 0, y: 0, z: 0, w: 0}}
        outSlope: {{x: 0, y: 0, z: 0, w: 0}}
"""
    return f"""%YAML 1.1
AnimationClip:
  m_Name: {name}
  m_RotationCurves:
  - curve:
      serializedVersion: 2
      m_Curve:
{key(0, (0, 0, 0, 1))}{key(1, (second_x, 0, 0, 1))}      m_PreInfinity: 2
    path: Root/Bone
  m_CompressedRotationCurves: []
  m_EulerCurves: []
  m_PositionCurves: []
  m_ScaleCurves: []
  m_FloatCurves: []
"""


class OverviewValidatorTests(unittest.TestCase):
    def make_fixture(self, root, *, bad_value=False):
        clips = []
        animation_dir = root / "Animations"
        animation_dir.mkdir()
        for name in validator.TARGETS:
            sample = root / f"{name}.json"
            frames = [
                {"index": 0, "time": 0, "tracks": [{"rotation": [0, 0, 0, 1], "translation": [0, 0, 0], "scale": [1, 1, 1]}]},
                {"index": 1, "time": 1, "tracks": [{"rotation": [0, 0, 0, 1], "translation": [0, 0, 0], "scale": [1, 1, 1]}]},
            ]
            sample.write_text(json.dumps({"ok": True, "hash_ok": True, "track_type": "qvvf", "num_samples": 2, "frames": frames}), encoding="utf-8")
            clips.append({"name": name, "sample_json": str(sample), "frame_count": 2, "duration": 1, "loop": False, "unity_preview_stride": 1,
                          "bones": [{"path": "Root/Bone", "track_index": 0, "rot_animated": True, "pos_animated": False, "scale_animated": False}]})
            (animation_dir / f"{name}.anim").write_text(anim_yaml(name, 0.25 if bad_value and name == validator.TARGETS[0] else 0), encoding="utf-8")
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"clips": clips}), encoding="utf-8")
        return manifest, animation_dir

    def test_exact_keys_and_fractional_report_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest, animation_dir = self.make_fixture(Path(temporary))
            report = validator.build_report(manifest, animation_dir)
            self.assertTrue(report["ok"])
            self.assertTrue(report["fractional_error_is_diagnostic_only"])
            self.assertIsNone(report["fractional_error_limit_degrees"])
            self.assertEqual([2, 2], [row["exact_key_values_checked"] for row in report["clips"]])
            self.assertEqual([1, 1], [row["fractional_rotation_intervals_checked"] for row in report["clips"]])

    def test_value_mismatch_is_actionable(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest, animation_dir = self.make_fixture(Path(temporary), bad_value=True)
            report = validator.build_report(manifest, animation_dir)
            self.assertFalse(report["ok"])
            self.assertIn("value[0]", "\n".join(report["clips"][0]["failures"]))


if __name__ == "__main__":
    unittest.main()
