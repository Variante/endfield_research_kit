from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_secondary_dynamics_trajectory_capture.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_secondary_dynamics_trajectory_capture", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_capture(root: Path, overflow: int = 0, omit_last_coat: bool = False) -> None:
    directory = root / "secondary-dynamics"
    directory.mkdir(parents=True)
    sample_count = sum(MODULE.OWNER_LENGTHS.values()) * 2 - (1 if omit_last_coat else 0)
    window = {
        "schema": "endfieldCapture.secondaryDynamicsWindow.v4",
        "windowId": 1,
        "automaticTriggerPriorPresent": 100,
        "automaticTriggerGraphicsPresent": 101,
        "automaticTriggerComplete": True,
        "trajectoryComplete": overflow == 0,
        "transformScheduledCalls": 2,
        "transformCompletedCalls": 2,
        "transformWriteCalls": 2,
        "endminfTrajectoryFourChunkCandidateCoverage": True,
        "endminfTrajectoryFourOwnerCoverage": False,
        "registrationLifecycleJoinComplete": True,
        "effectivePostJobPoseComplete": True,
        "registrationHierarchyIdentityComplete": True,
        "transformWriteUnreadableCalls": 0,
        "transformSampleOverflow": overflow,
        "transformSampleCount": sample_count,
    }
    (directory / "windows.jsonl").write_text(
        json.dumps(window) + "\n", encoding="utf-8")
    summary = {
        "schema": "endfieldCapture.secondaryDynamicsSummary.v4",
        "hooksInstalled": True,
        "clothUpdateHookInstalled": True,
        "alwaysTeamUpdateHookInstalled": True,
        "writeTransformHookInstalled": True,
        "completeMasterJobHookInstalled": True,
        "addClothHookInstalled": True,
        "removeClothHookInstalled": True,
        "addTransformHookInstalled": True,
        "removeTransformHookInstalled": True,
        "hierarchyIdentityGettersPinned": True,
        "mainWindowThreadId": 123,
        "registrationCallbackThreadId": 123,
        "registrationCallbackThreadMismatches": 0,
        "registrationCallbackThreadUnresolved": 0,
        "registrationLifecycleFailures": 0,
        "hierarchyIdentityBusyFailures": 0,
        "hierarchyIdentityCaptureFailures": 0,
        "hierarchyIdentityRecordCapacityFailures": 0,
        "hierarchyIdentityArenaCapacityFailures": 0,
        "windowsCompleted": 1,
        "windowsFailed": 0,
        "evidenceCompleteWindows": 1,
        "evidenceIncompleteWindows": 0,
        "automaticTriggerArmFailures": 0,
        "automaticTriggerLifecycleFailures": 0,
        "automaticTriggerCallbackQuiescent": True,
        "quiescentCleanup": True,
        "complete": True,
    }
    (directory / "summary.json").write_text(
        json.dumps(summary) + "\n", encoding="utf-8")
    animator = root / "graphics/endminf_animator"
    animator.mkdir(parents=True)
    (animator / "metadata.json").write_text(json.dumps({
        "schema": "endfieldCapture.endminfAnimatorTimeline.v3",
        "characterId": "chr_0003_endminf",
        "sequenceComplete": True,
        "complete": True,
        "stableIdentity": True,
        "stateHashesValid": True,
        "classifiedIdentitySegments": 1,
        "completeIdentitySegments": 1,
        "selectedIdentitySegment": 0,
        "selectedSegmentOffset": 0,
        "selectedSegmentSampleCount": 1,
        "indices": {"firstWrap": 0},
        "stateHashes": {
            "startFullPath": MODULE.OVERVIEW_START_FULL_PATH_HASH,
            "loopFullPath": MODULE.OVERVIEW_LOOP_FULL_PATH_HASH,
        },
        "samples": [{"qpcTick": 1150, "qpcFrequency": 1_000_000_000,
                     "threadId": 123, "owner": "0x100",
                     "animator": "0x200"}],
    }) + "\n", encoding="utf-8")
    with (directory / "trajectories.jsonl").open("w", encoding="utf-8") as output:
        expected_paths = MODULE.load_expected_owner_paths()
        expected_hierarchy_paths = MODULE.load_expected_owner_hierarchy_paths()
        instance_by_path = {
            digest: 1000 + index for index, digest in enumerate(dict.fromkeys(
                digest for paths in expected_paths.values() for digest in paths))
        }
        start = 0
        for owner_index, (owner, length) in enumerate(MODULE.OWNER_LENGTHS.items(), 1):
            for writeback in (1, 2):
                for local in range(length):
                    if omit_last_coat and owner == "Coat" and writeback == 2 and local == length - 1:
                        continue
                    output.write(json.dumps({
                        "schema": "endfieldCapture.secondaryDynamicsTransform.v4",
                        "windowId": 1,
                        "writebackId": writeback,
                        "timestampNs": 1000 + writeback * 100,
                        "transformIndex": start + local,
                        "teamId": owner_index,
                        "componentId": owner_index * 10,
                        "proxyTransformStart": start,
                        "proxyTransformLength": length,
                        "endminfOwnerCandidate": owner,
                        "position": [1.0, 2.0, 3.0],
                        "rotation": [0.0, 0.0, 0.0, 1.0],
                        "localPosition": [0.1, 0.2, 0.3],
                        "localRotation": [0.0, 0.0, 0.0, 1.0],
                        "registrationJoined": True,
                        "clothProcess": f"0x{0x1000 + owner_index:x}",
                        "clothComponent": f"0x{0x2000 + owner_index:x}",
                        "clothTransform": f"0x{0x3000 + owner_index:x}",
                        "registeredTransform": f"0x{0x4000 + start + local:x}",
                        "liveTransform": f"0x{0x8000 + start + local:x}",
                        "clothInstanceId": 100 + owner_index,
                        "clothTransformInstanceId": 200 + owner_index,
                        "registeredTransformInstanceId": instance_by_path[
                            expected_paths[owner][local]],
                        "liveTransformInstanceId": instance_by_path[
                            expected_paths[owner][local]],
                        "clothRegistrationGeneration": 200 + owner_index,
                        "transformRegistrationGeneration": 5000 + start + local,
                        "hierarchyIdentityRecordId": 6000 + start + local,
                        "clothNameRecordId": 7000 + owner_index,
                        "registrationStart": start + local,
                        "registrationLength": 1,
                        "clothParentInstanceId": 900,
                        "hierarchyRootInstanceId": 901,
                        "hierarchyActorParentInstanceId": 900,
                        "hierarchyIdentityReadable": True,
                        "hierarchyPathSha256": expected_paths[owner][local],
                        "clothNameSha256": MODULE.sha256_text(
                            MODULE.STATIC_OWNER_NAMES[owner]),
                        "hierarchyPath": expected_hierarchy_paths[owner][local],
                        "clothName": MODULE.STATIC_OWNER_NAMES[owner],
                        "effectivePoseReadable": True,
                        "effectivePosition": [1.0, 2.0, 3.0],
                        "effectiveRotation": [0.0, 0.0, 0.0, 1.0],
                        "effectiveLocalPosition": [0.1, 0.2, 0.3],
                        "effectiveLocalRotation": [0.0, 0.0, 0.0, 1.0],
                    }) + "\n")
            start += length


class TrajectoryCaptureTests(unittest.TestCase):
    def test_complete_four_owner_window_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            report = MODULE.build_report(root, minimum_writebacks=2)
            self.assertEqual(
                report["status"],
                "validated_four_static_owner_path_joined_post_job_trajectories")
            self.assertEqual(report["writebackCount"], 2)
            self.assertEqual(report["sampleCount"], 252)

    def test_overflow_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root, overflow=1)
            with self.assertRaisesRegex(MODULE.VerificationError, "complete trajectory"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_unjoined_automatic_trigger_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/windows.jsonl"
            window = json.loads(path.read_text(encoding="utf-8"))
            window["automaticTriggerGraphicsPresent"] = 103
            window["automaticTriggerComplete"] = False
            path.write_text(json.dumps(window) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "Animator/graphics trigger"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_incomplete_provider_summary_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/summary.json"
            summary = json.loads(path.read_text(encoding="utf-8"))
            summary["completeMasterJobHookInstalled"] = False
            summary["complete"] = False
            path.write_text(json.dumps(summary) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "completeMasterJobHookInstalled"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_unmatched_transform_chronology_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/windows.jsonl"
            window = json.loads(path.read_text(encoding="utf-8"))
            window["transformCompletedCalls"] = 1
            path.write_text(json.dumps(window) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "writebacks differ"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_trajectory_must_reach_first_loop_wrap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "graphics/endminf_animator/metadata.json"
            metadata = json.loads(path.read_text(encoding="utf-8"))
            metadata["samples"][0]["qpcTick"] = 1250
            path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "first settled loop wrap"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_incomplete_owner_writeback_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root, omit_last_coat=True)
            with self.assertRaisesRegex(MODULE.VerificationError, "Coat"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_missing_registration_join_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            rows[0]["registrationJoined"] = False
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "registration lifecycle join"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_missing_effective_pose_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            rows[0]["effectivePoseReadable"] = False
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "effective post-job pose"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_live_transform_instance_identity_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            rows[0]["liveTransformInstanceId"] += 1
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "identity differs"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_degenerate_effective_quaternion_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            rows[0]["effectiveRotation"] = [0.0, 0.0, 0.0, 0.0]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "effectiveRotation is degenerate"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_hierarchy_component_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            rows[0]["hierarchyPath"] += "_drift"
            rows[0]["hierarchyPathSha256"] = MODULE.sha256_text(
                rows[0]["hierarchyPath"])
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "complete team candidates"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_cloth_name_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                if row["proxyTransformLength"] == 6:
                    row["clothName"] = "MC_Wrong"
                    row["clothNameSha256"] = MODULE.sha256_text("MC_Wrong")
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "cloth name"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_cross_owner_duplicate_instance_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            target_digest = rows[0]["hierarchyPathSha256"]
            changed = False
            for row in rows:
                if (row["hierarchyPathSha256"] == target_digest and
                        row["proxyTransformLength"] == 70):
                    row["registeredTransformInstanceId"] += 10000
                    row["liveTransformInstanceId"] = row[
                        "registeredTransformInstanceId"]
                    changed = True
            self.assertTrue(changed)
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "100-path/26-duplicate"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_registration_thread_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/summary.json"
            summary = json.loads(path.read_text(encoding="utf-8"))
            summary["registrationCallbackThreadMismatches"] = 1
            path.write_text(json.dumps(summary) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "main window thread"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_animator_thread_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "graphics/endminf_animator/metadata.json"
            metadata = json.loads(path.read_text(encoding="utf-8"))
            metadata["samples"][0]["threadId"] = 456
            path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "main window thread"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_cloth_parent_actor_association_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                if row["proxyTransformLength"] == 6:
                    row["clothParentInstanceId"] = 902
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "share one actor parent"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_immutable_hierarchy_record_reuse_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                if row["transformIndex"] == 1:
                    row["hierarchyIdentityRecordId"] = 6000
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "record IDs are reused"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_registration_generation_reuse_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            path = root / "secondary-dynamics/trajectories.jsonl"
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                if row["transformIndex"] == 1:
                    row["transformRegistrationGeneration"] = 5000
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "stale, reused, or incomplete"):
                MODULE.build_report(root, minimum_writebacks=2)


if __name__ == "__main__":
    unittest.main()
