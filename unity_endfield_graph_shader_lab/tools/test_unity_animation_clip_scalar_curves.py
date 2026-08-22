import unittest

from unity_animation_clip_scalar_curves import decode_scalar_curves


class ScalarCurveDecoderTests(unittest.TestCase):
    def test_streamed_gameobject_active_curves(self):
        # -max sentinel, t=0, t=1.5, +inf sentinel; key record is
        # curve index + cubic coefficients, whose fourth coefficient is value.
        clip = {
            "m_ClipBindingConstant": {"genericBindings": [
                {"path": 11, "attribute": 2086281974, "typeID": "GameObject"},
                {"path": 22, "attribute": 2086281974, "typeID": "GameObject"},
            ]},
            "m_MuscleClip": {"m_Clip": {
                "m_StreamedClip": {"curveCount": 2, "data": [
                    4286578687, 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1065353216,
                    0, 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1065353216,
                    1069547520, 1, 1, 0, 0, 0, 0,
                    2139095040, 0,
                ]},
                "m_DenseClip": {"m_CurveCount": 0},
                "m_ConstantClip": {"data": []},
            }},
        }
        curves = decode_scalar_curves(clip)
        self.assertEqual([key["value"] for key in curves[0]["keys"]], [0.0])
        self.assertEqual(curves[1]["keys"], [
            {"time": 0.0, "value": 1.0}, {"time": 1.5, "value": 0.0}
        ])

    def test_rejects_binding_storage_count_drift(self):
        clip = {"m_ClipBindingConstant": {"genericBindings": [{"typeID": "GameObject"}]},
                "m_MuscleClip": {"m_Clip": {"m_StreamedClip": {"curveCount": 0},
                "m_DenseClip": {"m_CurveCount": 0}, "m_ConstantClip": {"data": []}}}}
        with self.assertRaisesRegex(ValueError, "scalar count"):
            decode_scalar_curves(clip)


if __name__ == "__main__":
    unittest.main()
