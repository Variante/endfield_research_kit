#!/usr/bin/env python3
"""Focused offline tests for the pinned PostProxyMeshUpdate contract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_post_proxy_contract as builder


class SecondaryDynamicsPostProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_contract_is_fail_closed_at_numeric_workers(self) -> None:
        payload = self.payload
        self.assertEqual(
            payload["status"],
            "post_proxy_schedule_and_create_list_control_closed_calc_line_vectors_open",
        )
        self.assertTrue(payload["manager_schedule_closed"])
        self.assertTrue(payload["managed_job_payload_layout_closed"])
        self.assertTrue(payload["generic_methodspec_identities_closed"])
        self.assertTrue(payload["create_list_worker_control_flow_recovered"])
        self.assertTrue(payload["calc_line_entry_control_flow_recovered"])
        self.assertFalse(payload["create_list_kernel_numerics_recovered"])
        self.assertFalse(payload["calc_line_normal_tangent_numerics_recovered"])
        self.assertFalse(payload["selected_cross_frame_route_closed"])
        self.assertFalse(payload["solver_implemented"])
        self.assertFalse(payload["retail_equivalent"])
        self.assertFalse(payload["capture_used_as_implementation_source"])

    def test_exact_manager_abi_and_dependency_order(self) -> None:
        abi = self.payload["managerAbi"]
        self.assertEqual((abi["methodIndex"], abi["token"], abi["startVa"]),
                         (384785, "0x060004da", "0x182f8c4a0"))
        self.assertEqual(abi["bodySha256"], "5a74ebb4a44356d4114332da8ca9c4ed183ed2e7d88216637072e0ebf151bead")
        self.assertEqual(abi["firstRetOffset"], "0xe34")
        self.assertEqual(abi["win64Arguments"]["rcx"], "hidden 16-byte JobHandle return buffer")
        self.assertEqual([stage["job"] for stage in self.payload["stageOrder"]], [
            "CreatePostProxyMeshUpdateListJob", "CalcLineNormalTangentJob",
            "WriteTransformDataJob", "WriteTransformLocalDataJob",
        ])

    def test_exact_set_count_reflection_and_schedule_identities(self) -> None:
        stages = self.payload["stageOrder"]
        self.assertEqual([row["setIndexCount"]["callOffset"] for row in stages],
                         ["0x3b8", "0x765", "0xa1b", "0xcd0"])
        self.assertEqual([row["getReflectionData"]["callOffset"] for row in stages],
                         ["0x496", "0x838", "0xae9", "0xdae"])
        self.assertEqual([row["getReflectionData"]["methodSpecIndex"] for row in stages],
                         [516826, 516819, 516828, 516829])
        self.assertEqual([row["parallelSchedule"]["methodSpecIndex"] for row in stages],
                         [517373, 517163, 517167, 517168])
        self.assertEqual([row["parallelSchedule"]["innerLoopBatchCount"] for row in stages],
                         [1, 8, 16, 32])
        self.assertEqual([row["crossFrameScheduleHelper"]["methodSpecIndex"] for row in stages],
                         [508694, 508714, 508718, 508719])

    def test_job_payload_shapes(self) -> None:
        stages = {row["job"]: row["jobPayload"] for row in self.payload["stageOrder"]}
        self.assertEqual([stages[name]["nativePayloadBytes"] for name in (
            "CreatePostProxyMeshUpdateListJob", "CalcLineNormalTangentJob",
            "WriteTransformDataJob", "WriteTransformLocalDataJob")], [0xA0, 0x110, 0x90, 0xB0])
        self.assertEqual(stages["CalcLineNormalTangentJob"]["fields"][-1]["nativePayloadOffset"], "0x100")
        self.assertEqual(stages["WriteTransformLocalDataJob"]["fields"][-1]["name"], "_indexCount")

    def test_open_boundary_names_exact_worker_targets(self) -> None:
        workers = {row["methodIndex"]: row for row in self.payload["openWorkerTargets"]}
        self.assertEqual(workers[384832]["startVa"], "0x186743868")
        self.assertEqual(workers[384832]["bodySha256"], "02a0d53fed888f05f966dbe2250f59e4f2722d0cfac3928e7a2b268d39bb4bde")
        self.assertEqual(workers[384856]["startVa"], "0x186744fb0")
        self.assertEqual(workers[384856]["bodySha256"], "9868eee8cddc41aae648fead87025f7a53b4d158dca963865dfd2126a0f9a829")
        self.assertEqual([row["methodIndex"] for row in self.payload["nextDisassemblyTargets"]], [384856])

    def test_create_list_control_flow_is_code_derived(self) -> None:
        flow = self.payload["createListHotControlFlow"]
        self.assertEqual(flow["hotSpan"]["throughRetSha256"],
                         "05248d617681f7cbce052c79fffc748936523f7230da3812c6c8bab0f3230213")
        self.assertEqual(flow["teamDataStrideBytes"], 0x1D0)
        self.assertEqual([row["queue"] for row in flow["atomicQueueAppends"]], [0, 1, 2, 3])
        self.assertEqual([row["atomicReserveOffset"] for row in flow["atomicQueueAppends"]],
                         ["0x110", "0x143", "0x191", "0x1d5"])
        self.assertIn("No captured indices", flow["operation"])

    def test_calc_line_boundary_stops_before_vector_math(self) -> None:
        flow = self.payload["calcLineEntryControlFlow"]
        self.assertEqual(flow["managedWorkerMethodIndex"], 384856)
        self.assertEqual(flow["entryGates"][-1], {"offset": "0x20b", "condition": "childCount != 0"})
        self.assertIn("remain code-only disassembly targets", flow["numericBoundary"])

    def test_evidence_hash_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drifted.json"
            path.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(builder.ContractError):
                builder._source(path, "0" * 64)

    def test_builder_recomputes_published_contract(self) -> None:
        self.assertEqual(builder.build_contract(), self.payload)


if __name__ == "__main__":
    unittest.main()
