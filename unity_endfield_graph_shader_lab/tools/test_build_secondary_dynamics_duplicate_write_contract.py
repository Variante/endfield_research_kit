#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import build_secondary_dynamics_duplicate_write_contract as builder


class DuplicateWriteContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_generated_contract_rebuilds_exactly(self) -> None:
        self.assertEqual(builder.build_contract(), self.contract)

    def test_all_126_entries_are_preserved(self) -> None:
        rows = self.contract["endminf"]["orderedEntries"]
        self.assertEqual(len(rows), 126)
        self.assertEqual([row["managerIndex"] for row in rows], list(range(126)))
        self.assertEqual(Counter(row["staticWriteBranch"] for row in rows),
                         Counter({"local": 67, "none": 36, "world": 23}))

    def test_duplicates_have_no_competing_writers(self) -> None:
        summary = self.contract["endminf"]["duplicateSummary"]
        self.assertEqual((summary["uniqueTransforms"], summary["duplicateEntries"]), (100, 26))
        self.assertEqual(summary["resolutionCounts"],
                         {"sole_write_eligible_entry": 24, "no_write_eligible_entry": 2})
        self.assertEqual(summary["competingWriterPathCount"], 0)
        for group in self.contract["endminf"]["duplicateGroups"]:
            self.assertLessEqual(len(group["writeEligibleManagerIndices"]), 1)

    def test_exact_target_writer_census(self) -> None:
        groups = self.contract["endminf"]["duplicateGroups"]
        winners = Counter()
        branches = Counter()
        for group in groups:
            if group["staticallyProvenWriterManagerIndex"] is None:
                winners["none"] += 1
                continue
            member = next(row for row in group["members"]
                          if row["managerIndex"] == group["staticallyProvenWriterManagerIndex"])
            winners[member["owner"]] += 1
            branches[member["staticWriteBranch"]] += 1
        self.assertEqual(winners, Counter({"MC_Ribbon": 18, "MC_Ribbon2": 6, "none": 2}))
        self.assertEqual(branches, Counter({"local": 19, "world": 5}))

    def test_parallel_order_is_not_claimed(self) -> None:
        ordering = self.contract["ordering"]
        self.assertEqual(ordering["scheduleApi"], "ScheduleParallelForTransform_Injected")
        self.assertFalse(ordering["sourceOrderExecutionProven"])
        self.assertFalse(ordering["parallelTransformAccessOrderProven"])
        self.assertIn("immaterial", ordering["impact"])

    def test_team_and_weight_are_not_pairwise_exclusion(self) -> None:
        gates = self.contract["writeGating"]
        self.assertFalse(gates["pairwiseOwnerComparison"])
        self.assertFalse(gates["teamOrWeightMutualExclusionProven"])
        self.assertIn("not a pairwise exclusion gate", gates["weightRole"])

    def test_route_policy_is_closed_but_full_target_fails_closed(self) -> None:
        boundary = self.contract["runtimePolicyBoundary"]
        self.assertTrue(boundary["transformAccessRoutePolicyCanBeEvidenceBacked"])
        self.assertFalse(boundary["fullTargetRuntimeDuplicatePolicyCanBeEvidenceBacked"])
        self.assertFalse(boundary["staticallyProvenFullTargetWinner"])
        self.assertFalse(boundary["requiresAssumedSourceOrderWinner"])
        self.assertFalse(boundary["requiresCompatibilityPriority"])
        self.assertEqual(boundary["coatWinnerCount"], 0)
        self.assertFalse(boundary["runtimeModified"])

    def test_target_callback_route_remains_fail_closed(self) -> None:
        route = self.contract["callbackRouteBoundary"]
        self.assertEqual(route["writeTransformCallOffset"], "0xbbc")
        self.assertEqual(route["animatorWriteCallOffset"], "0x10b5")
        self.assertFalse(route["targetSelectedRouteProven"])
        self.assertIn("not promoted", route["consequence"])

    def test_native_bodies_and_call_sites_are_pinned(self) -> None:
        bodies = {row["name"]: row for row in self.contract["native"]["bodyPins"]}
        self.assertEqual(bodies["DynamicBoneTransformManager.WriteTransformJob.Execute"]["bytes"], 11452)
        self.assertEqual(bodies["DynamicBoneTransformManager.WriteTransformJob.Execute"]["sha256"],
                         "8bb838d1118e5910d0794f5790cecad8a92981c760e802799e3244189cfd4676")
        calls = {row["name"]: row for row in self.contract["native"]["callSites"]}
        self.assertEqual(calls["generic Schedule -> ScheduleParallelForTransform_Injected"]["instructionBytes"], "ff d0")
        self.assertEqual(calls["ClothUpdate -> WriteTransform"]["target"], "0x18672641c")

    def test_mutated_read_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "read.json"
            data = json.loads(builder.DEFAULT_READ.read_text(encoding="utf-8"))
            data["endminf"]["orderedEntries"][0]["sourceFlag"] = 1
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(builder.ContractError):
                builder.build_contract(read_path=path)


if __name__ == "__main__":
    unittest.main()
