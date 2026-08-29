#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Runtime"
    / "Animation"
    / "RecoveredAclAnimatorPoseDriver.cs"
)


class RecoveredAclAnimatorPoseDriverTests(unittest.TestCase):
    def test_driver_uses_source_state_and_acl_sampling(self):
        source = SOURCE.read_text(encoding="utf-8")
        for required in (
            "Animator.StringToHash(state.fullStatePath)",
            "GetCurrentAnimatorStateInfo(0)",
            "GetNextAnimatorStateInfo(0)",
            "GetAnimatorTransitionInfo(0).normalizedTime",
            "RecoveredAclPoseEvaluator.TrySampleTrack",
            "RecoveredAclPoseEvaluator.StableVectorLerp",
            "RecoveredAclPoseEvaluator.TryStableQuaternionLerp",
            "poseRoot.Find(binding.transformPath)",
        ):
            self.assertIn(required, source)

    def test_driver_contains_no_actor_pose_or_curve_constants(self):
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "endminf",
            "overview_start",
            "overview_loop",
            "animationcurve",
            "quaternion.slerp",
            "quaternion.lerp",
            "localposition = new vector3",
            "localrotation = new quaternion",
        ):
            self.assertNotIn(forbidden, source.lower())

    def test_driver_runs_before_secondary_dynamics_late_boundary(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("[DefaultExecutionOrder(-70)]", source)
        self.assertIn("private void LateUpdate()", source)
        self.assertNotIn("PlayerLoop.SetPlayerLoop", source)


if __name__ == "__main__":
    unittest.main()
