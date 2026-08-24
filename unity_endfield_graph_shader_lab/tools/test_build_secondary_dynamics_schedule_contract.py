#!/usr/bin/env python3
"""Focused tests for the pinned secondary-dynamics schedule contract."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_schedule_contract as builder


class SecondaryDynamicsScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_published_boundary_is_unpatched_and_fail_closed(self) -> None:
        payload = self.payload
        self.assertEqual(payload["status"], "unpatched_schedule_and_transform_access_writeback_closed")
        self.assertTrue(payload["cross_frame_schedule_closed"])
        self.assertTrue(payload["schedule_completion_closed"])
        self.assertTrue(payload["transform_write_job_construction_closed"])
        self.assertTrue(payload["transform_access_schedule_closed"])
        self.assertFalse(payload["ifix_patched_route_closed"])
        self.assertFalse(payload["solver_numerics_recovered"])
        self.assertFalse(payload["secondary_dynamics_verified"])

    def test_authoritative_method_bounds_and_hashes(self) -> None:
        methods = {row["method"]: row for row in self.payload["authoritativeMethods"]}
        self.assertEqual((methods["SimulationStepUpdate"]["spanBytes"], methods["SimulationStepUpdate"]["firstRetOffset"]), (0x1750, "0x14eb"))
        self.assertEqual((methods["CompleteMasterJob"]["spanBytes"], methods["CompleteMasterJob"]["firstRetOffset"]), (0x120, "0x74"))
        self.assertEqual((methods["WriteTransform"]["spanBytes"], methods["WriteTransform"]["firstRetOffset"]), (0x228, "0x227"))
        self.assertEqual(methods["SimulationStepUpdate"]["bodySha256"], "5106aa8354dfe1d73e8a4ecb6a693cf8586938da5d456f7fc748267e08743335")

    def test_five_job_schedule_order_and_methodspecs(self) -> None:
        schedule = self.payload["simulationStepUpdate"]
        self.assertEqual(schedule["scheduleModeLane"], 2)
        self.assertEqual(schedule["priority"], 0)
        jobs = schedule["jobs"]
        self.assertEqual([row["jobType"].rsplit("+", 1)[-1] for row in jobs], [
            "ClearStepCounter", "CreateUpdateParticleList", "StartSimulationStepJob",
            "UpdateStepBasicPotureJob", "EndSimulationStepJob",
        ])
        self.assertEqual([row["getReflectionDataMethodSpecIndex"] for row in jobs], [516766, 516767, 516770, 516771, 516768])
        self.assertEqual([row["offsets"]["indirectScheduleCall"] for row in jobs], ["0x3b0", "0x7a1", "0xc54", "0xf8e", "0x147b"])
        self.assertEqual({row["genericEntryVa"] for row in jobs}, {"0x1837358f0", "0x1837359a0"})

    def test_master_handle_completion_and_clear(self) -> None:
        complete = self.payload["completeMasterJob"]
        self.assertEqual((complete["masterHandleObjectOffset"], complete["indirectCallOffset"], complete["clear16ByteOffset"]), ("0x38", "0x85", "0x6b"))
        self.assertEqual(complete["icallSlotVa"], "0x18f36ee28")
        self.assertEqual(complete["icallLiteralVa"], "0x18b8fb930")

    def test_write_job_uses_current_arrays_and_exact_schedule_identity(self) -> None:
        write = self.payload["writeTransform"]
        sources = {row["jobField"]: row["source"] for row in write["sources"]}
        self.assertEqual(sources["lastpositionArray"], "positionArray")
        self.assertEqual(sources["lastrotationArray"], "rotationArray")
        self.assertEqual(sources["lastlocalPositionArray"], "localPositionArray")
        self.assertEqual(sources["lastlocalRotationArray"], "localRotationArray")
        self.assertNotIn("lastpositionArray", sources.values())
        self.assertEqual(write["jobSizeBytes"], 0x70)
        self.assertEqual(write["transformAccessArrayObjectOffset"], "0x80")
        wrapper = write["concreteWrapper"]
        self.assertEqual(wrapper["bodySha256"], "84d0c36acbe0b117db909abe436a6a90e5786e7077bad4753207c2c3e628d255")
        self.assertEqual(wrapper["hiddenMethodInfoSlotVa"], "0x18e2fa2f0")
        generic = write["genericSchedule"]
        self.assertEqual((generic["methodSpecIndex"], generic["jobTypeIndex"], generic["scheduleModeLane"]), (517387, 188650, 1))
        self.assertEqual(generic["bodySha256"], "891f42acb49be0849ff45440f1b272489211db8b86220305a658fa2f4a1d3095")

    def test_builder_recomputes_published_contract(self) -> None:
        self.assertEqual(builder.build_contract(), self.payload)


if __name__ == "__main__":
    unittest.main()
