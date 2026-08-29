#!/usr/bin/env python3

import math
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "Assets" / "EndfieldGraphShaderLab" / "Runtime" / "Animation"
EVALUATOR = RUNTIME / "RecoveredAclPoseEvaluator.cs"
DATA = RUNTIME / "RecoveredAclClipData.cs"


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def resolve(time, rate, duration, count, wrap):
    effective = f32(max(0.0, time))
    effective = f32(effective % duration) if wrap else f32(min(effective, duration))
    sample_index = f32(effective * rate)
    lower = math.floor(sample_index)
    alpha = f32(sample_index - lower)
    if wrap:
        lower %= count
        return lower, (lower + 1) % count, alpha
    if lower >= count - 1:
        return count - 1, count - 1, 0.0
    return lower, lower + 1, alpha


def qlerp(start, end, alpha):
    dot = f32(sum(f32(a * b) for a, b in zip(start, end)))
    bias = 1.0 if dot >= 0.0 else -1.0
    value = tuple(
        f32(f32(a - f32(alpha * a)) + f32(alpha * f32(bias * b)))
        for a, b in zip(start, end)
    )
    length_squared = f32(sum(f32(v * v) for v in value))
    inverse = f32(1.0 / math.sqrt(length_squared))
    return tuple(f32(v * inverse) for v in value)


def stable_lerp(start, end, alpha):
    return f32(f32(start - f32(alpha * start)) + f32(alpha * end))


def conventional_lerp(start, end, alpha):
    return f32(start + f32(f32(end - start) * alpha))


class RecoveredAclPoseEvaluatorTests(unittest.TestCase):
    def test_clamp_window_uses_nonnegative_floor_and_terminal_clamp(self):
        self.assertEqual((0, 1, 0.0), resolve(-2.0, 60.0, 2.0, 121, False))
        self.assertEqual((3, 4, 0.5), resolve(3.5 / 60.0, 60.0, 2.0, 121, False))
        self.assertEqual((120, 120, 0.0), resolve(99.0, 60.0, 2.0, 121, False))

    def test_wrap_window_repeats_duration_and_wraps_upper_index(self):
        self.assertEqual((0, 1, 0.0), resolve(2.0, 2.0, 2.0, 4, True))
        self.assertEqual((3, 0, 0.5), resolve(1.75, 2.0, 2.0, 4, True))

    def test_wrap_boundary_uses_controller_duration_not_sample_count(self):
        # A controller may loop a 121-sample clip at its 2-second duration;
        # do not silently replace that boundary with sampleCount / sampleRate.
        self.assertEqual((0, 1, 0.0), resolve(2.0, 60.0, 2.0, 121, True))
        self.assertEqual((119, 120, f32(0.99993896484375)),
                         resolve(f32(1.999999), 60.0, 2.0, 121, True))

    def test_shortest_arc_quaternion_lerp_is_sign_invariant_and_normalized(self):
        start = (0.0, 0.0, 0.0, 1.0)
        end = (0.0, 0.8, 0.0, 0.6)
        positive = qlerp(start, end, f32(0.375))
        negative = qlerp(start, tuple(-value for value in end), f32(0.375))
        self.assertEqual(positive, negative)
        self.assertAlmostEqual(1.0, math.sqrt(sum(value * value for value in positive)), places=6)

    def test_stable_endpoint_lerp_has_native_float32_rounding(self):
        start = f32(-85512744.0)
        end = f32(7176401.0)
        alpha = f32(0.36568892002105713)
        stable = stable_lerp(start, end, alpha)
        conventional = conventional_lerp(start, end, alpha)
        self.assertEqual(-51617348.0, stable)
        self.assertEqual(-51617352.0, conventional)
        self.assertNotEqual(
            struct.pack("<f", stable),
            struct.pack("<f", conventional),
        )

    def test_runtime_source_keeps_sampling_inert_and_explicit(self):
        evaluator = EVALUATOR.read_text(encoding="utf-8")
        data = DATA.read_text(encoding="utf-8")
        for required in (
            "float sampleIndex = effectiveTime * sampleRate;",
            "effectiveTime %= duration;",
            "int lower = Mathf.FloorToInt(sampleIndex);",
            "float bias = dot >= 0f ? 1f : -1f;",
            "float inverseLength = 1f / Mathf.Sqrt(lengthSquared);",
            "(start.x - alpha * start.x) + alpha * end.x",
            "(start.x - alpha * start.x) + alpha * (bias * end.x)",
        ):
            self.assertIn(required, evaluator)
        for forbidden in (
            "GetComponent<Transform>",
            ".localPosition =",
            ".localRotation =",
            ".localScale =",
            "Animator",
        ):
            self.assertNotIn(forbidden, evaluator)
        self.assertIn("Frame-major layout", data)
        self.assertIn("sourceAclSha256", data)
        self.assertIn("decodedSamplesSha256", data)


if __name__ == "__main__":
    unittest.main()
