#!/usr/bin/env python3

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name(
    "build_secondary_dynamics_session_certification_contract.py")
SPEC = importlib.util.spec_from_file_location("session_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SessionCertificationContractTests(unittest.TestCase):
    def test_pinned_capture_preserves_settings_but_rejects_owner_attribution(self):
        repo = Path(__file__).resolve().parents[2]
        session = repo / "scratch" / "reverse_engineering" / "endfield_capture" / \
            MODULE.SESSION_ID
        contract = MODULE.build(session)
        self.assertFalse(contract["targetReady"])
        self.assertEqual(
            contract["certification"],
            {
                "certified": False,
                "useRelativeTransform": False,
                "useCrossFrameJob": True,
                "useAnimatorTransform": False,
                "writebackRoute": "TransformAccess",
            },
        )
        self.assertEqual(contract["window"]["activeTeamLanesPerSettledCall"], 4)
        self.assertEqual(contract["window"]["warmupClothUpdateCalls"], 7)
        self.assertEqual(contract["window"]["relativeTrueCalls"], 0)
        self.assertFalse(contract["boundary"]["endminfFourOwnerCertification"])

    def build_synthetic_session(self, certified=True, team_count=5):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "20260825T200000Z"
        (root / "collected").mkdir(parents=True)
        (root / "secondary-dynamics").mkdir()

        session = {
            "schema": "endfieldCapture.session.v1",
            "sessionId": root.name,
            "providers": 4,
            "gameBuild": MODULE.EXPECTED_GAME_BUILD,
            "targetSha256": MODULE.EXPECTED_TARGET_SHA256,
        }
        writer = {
            "schema": "endfieldCapture.summary.v1",
            "dropped": 0,
            "invalidRecords": 0,
            "writerError": False,
            "complete": True,
        }
        provider = {
            "schema": "endfieldCapture.secondaryDynamicsSummary.v1",
            "hooksInstalled": True,
            "windowsCompleted": 1,
            "quiescentCleanup": True,
            "complete": True,
        }
        window = {
            "schema": "endfieldCapture.secondaryDynamicsWindow.v1",
            "windowId": 1,
            "startNs": 100,
            "endNs": 200,
            "clothUpdateCalls": 10,
            "crossFrameFalseCalls": 0,
            "crossFrameTrueCalls": 10,
            "crossFrameUnreadableCalls": 0,
            "crossFrameStable": True,
            "crossFrameValue": True,
            "teamDataGetterCalls": 40,
            "relativeSlotOverflow": 0,
            "teamCount": team_count,
            "allObservedRelativeFalse": True,
            "observations": [
                {
                    "teamData": f"0x{index + 1:x}",
                    "falseCalls": 40 // team_count,
                    "trueCalls": 0,
                }
                for index in range(team_count)
            ],
            "boundedComplete": True,
            "endminfCoveredByUniversalFalse": certified,
            "endminfFourOwnerCertification": certified,
        }
        paths = {
            "session.json": session,
            "collected/summary.json": writer,
            "secondary-dynamics/summary.json": provider,
        }
        for relative, value in paths.items():
            (root / relative).write_text(
                json.dumps(value) + "\n", encoding="utf-8"
            )
        (root / "secondary-dynamics/windows.jsonl").write_text(
            json.dumps(window) + "\n", encoding="utf-8"
        )
        artifacts = []
        for relative in (*paths, "secondary-dynamics/windows.jsonl"):
            path = root / relative
            artifacts.append({"path": relative, "sha256": MODULE.sha256(path)})
        (root / "collected/inventory.json").write_text(
            json.dumps({
                "schema": "endfieldCapture.collection.v1",
                "session": root.name,
                "artifacts": artifacts,
            }) + "\n",
            encoding="utf-8",
        )
        return root, window

    def test_current_universal_false_window_certifies_target(self):
        root, _ = self.build_synthetic_session()
        contract = MODULE.build(root, require_certified=True)
        self.assertTrue(contract["targetReady"])
        self.assertTrue(contract["certification"]["certified"])
        self.assertEqual(
            contract["boundary"]["certificationMode"],
            "bounded_universal_false",
        )
        self.assertEqual(contract["target"]["sessionId"], root.name)

    def test_direct_four_owner_window_records_isolation_mode(self):
        root, _ = self.build_synthetic_session(team_count=4)
        contract = MODULE.build(root, require_certified=True)
        self.assertEqual(
            contract["boundary"]["certificationMode"],
            "direct_four_owner_isolation",
        )

    def test_require_certified_rejects_old_window_semantics(self):
        root, _ = self.build_synthetic_session(certified=False)
        with self.assertRaisesRegex(ValueError, "did not certify"):
            MODULE.build(root, require_certified=True)

    def test_true_relative_lane_is_rejected_before_publication(self):
        root, window = self.build_synthetic_session()
        window["allObservedRelativeFalse"] = False
        window["observations"][0]["trueCalls"] = 1
        (root / "secondary-dynamics/windows.jsonl").write_text(
            json.dumps(window) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "useRelativeTransform=true"):
            MODULE.build(root, require_certified=True)


if __name__ == "__main__":
    unittest.main()
