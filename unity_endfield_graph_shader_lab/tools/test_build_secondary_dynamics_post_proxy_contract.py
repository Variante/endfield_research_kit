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

    def test_contract_closes_managed_equations_but_fails_closed_at_runtime_routes(self) -> None:
        payload = self.payload
        self.assertEqual(
            payload["status"],
            "post_proxy_calc_line_burst_target_and_fallback_closed_runtime_selection_open",
        )
        self.assertTrue(payload["manager_schedule_closed"])
        self.assertTrue(payload["managed_job_payload_layout_closed"])
        self.assertTrue(payload["generic_methodspec_identities_closed"])
        self.assertTrue(payload["create_list_worker_control_flow_recovered"])
        self.assertTrue(payload["calc_line_entry_control_flow_recovered"])
        self.assertTrue(payload["calc_line_child_traversal_recovered"])
        self.assertTrue(payload["calc_line_managed_worker_equations_recovered"])
        self.assertTrue(payload["calc_line_managed_worker_degeneracy_branches_recovered"])
        self.assertTrue(payload["calc_line_data_layout_closed"])
        self.assertTrue(payload["calc_line_kernel_wrapper_route_recovered"])
        self.assertTrue(payload["calc_line_directcall_managed_fallback_equivalence_closed"])
        self.assertTrue(payload["calc_line_burst_function_pointer_target_closed"])
        self.assertFalse(payload["create_list_kernel_numerics_recovered"])
        self.assertFalse(payload["calc_line_normal_tangent_numerics_recovered"])
        self.assertFalse(payload["selected_calc_line_execution_route_closed"])
        self.assertFalse(payload["from_to_rotation_ifix_patch_state_closed"])
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

    def test_exact_worker_targets_and_remaining_boundaries(self) -> None:
        workers = {row["methodIndex"]: row for row in self.payload["workerTargets"]}
        self.assertEqual(workers[384832]["startVa"], "0x186743868")
        self.assertEqual(workers[384832]["bodySha256"], "02a0d53fed888f05f966dbe2250f59e4f2722d0cfac3928e7a2b268d39bb4bde")
        self.assertEqual(workers[384856]["startVa"], "0x186744fb0")
        self.assertEqual(workers[384856]["bodySha256"], "9868eee8cddc41aae648fead87025f7a53b4d158dca963865dfd2126a0f9a829")
        self.assertEqual(workers[384854]["startVa"], "0x1867456e4")
        self.assertEqual(workers[384854]["bodySha256"],
                         "05af0def52b33451b7424296e8325c8f4819c7e27a0b64bfc1207b359431ba83")
        self.assertEqual(self.payload["nextDisassemblyTargets"], [])

    def test_calc_line_directcall_wrapper_and_fallback_equivalence(self) -> None:
        route = self.payload["calcLineDirectCallRoute"]
        kernel = route["kernelWrapper"]
        self.assertEqual(
            (kernel["methodIndex"], kernel["startVa"], kernel["spanBytes"],
             kernel["instructionCount"], kernel["invokeMethodIndex"]),
            (384854, "0x1867456e4", 0x128, 55, 384867),
        )
        methods = {row["methodIndex"]: row for row in route["generatedMethods"]}
        self.assertEqual(methods[384867]["startVa"], "0x1867464d0")
        self.assertEqual(methods[384867]["bodySha256"],
                         "3166eb9d2d86a50eb31524927b652850ffcdc6a22b5b6edd92db200959392de7")

        selection = route["invokeSelection"]
        self.assertEqual(selection["burstEnabledGate"]["methodIndex"], 489283)
        self.assertEqual(selection["burstEnabledGate"]["runtimeValue"], "unresolved")
        self.assertEqual(selection["getFunctionPointer"]["resolver"]["methodIndex"], 489285)
        self.assertEqual(selection["getFunctionPointer"]["returnedPointer"],
                         "unresolved runtime value")
        self.assertEqual(route["selectedRuntimeRoute"], "unresolved")
        burst = route["burstFunctionPointerTarget"]
        self.assertEqual(
            burst["status"],
            "static_semantic_export_and_dual_cpu_core_identity_closed_runtime_route_unobserved",
        )
        self.assertEqual(burst["candidateHash"], "7342567c29c434b5b924be51bd8e34b7")
        self.assertEqual(burst["functionPointerSlotRva"], "0x3c57b0")
        variants = {row["cpuVariant"]: row for row in burst["variants"]}
        self.assertEqual(variants["x64_sse2"]["solverCore"]["rva"], "0xf4100")
        self.assertEqual(variants["avx2"]["solverCore"]["rva"], "0x284c50")

        fallback = route["directCallManagedFallback"]
        self.assertEqual((fallback["startVa"], fallback["spanBytes"],
                          fallback["throughRetBytes"]),
                         ("0x186740adc", 0x738, 0x731))
        self.assertEqual(fallback["throughRetSha256"],
                         "b1424aff822792c251bd1176f13d30a274612c86c11a0c5f19c471b363f8feeb")
        comparison = route["managedFallbackComparison"]
        self.assertEqual(comparison["throughFirstRetInstructionCount"], 396)
        self.assertTrue(comparison["identicalMnemonicSequence"])
        self.assertTrue(comparison["identicalOperandStructuralShapes"])
        self.assertTrue(comparison["identicalControlFlowTopologyByInstructionOrdinal"])
        self.assertEqual(comparison["conditionalAndUnconditionalBranchCount"], 18)
        self.assertEqual(comparison["directCallCount"], 22)
        self.assertFalse(
            comparison["nonControlImmediateComparison"]["numericConstantDifferenceObserved"]
        )

    def test_create_list_control_flow_is_code_derived(self) -> None:
        flow = self.payload["createListHotControlFlow"]
        self.assertEqual(flow["hotSpan"]["throughRetSha256"],
                         "05248d617681f7cbce052c79fffc748936523f7230da3812c6c8bab0f3230213")
        self.assertEqual(flow["teamDataStrideBytes"], 0x1D0)
        self.assertEqual([row["queue"] for row in flow["atomicQueueAppends"]], [0, 1, 2, 3])
        self.assertEqual([row["atomicReserveOffset"] for row in flow["atomicQueueAppends"]],
                         ["0x110", "0x143", "0x191", "0x1d5"])
        self.assertIn("No captured indices", flow["operation"])

    def test_calc_line_exact_abi_and_parent_indices_boundary(self) -> None:
        flow = self.payload["calcLineEntryControlFlow"]
        self.assertEqual(flow["managedWorkerMethodIndex"], 384856)
        self.assertEqual(flow["throughRetSha256"],
                         "3fd25c103794771a322506815060f2203fc2ef5d4830252122bd4b654c76df31")
        parameters = {row["name"]: row for row in flow["parameterLayout"]}
        self.assertEqual(len(parameters), 17)
        self.assertEqual((parameters["positions"]["workerRbpOffset"],
                          parameters["positions"]["elementType"],
                          parameters["positions"]["elementStrideBytes"]),
                         ("0x720", "Unity.Mathematics.double3", 24))
        self.assertEqual(parameters["rotations"]["access"], "readWrite")
        self.assertEqual(parameters["parentIndices"]["access"], "unusedByMethod384856")
        self.assertEqual(parameters["baseLineFlags"]["access"],
                         "readEntryGateThenIncomingStackSlotReused")
        self.assertEqual(flow["unusedParameters"], ["parentIndices"])

    def test_calc_line_native_field_layouts_are_exact(self) -> None:
        layouts = self.payload["calcLineEntryControlFlow"]["relevantNativeLayouts"]
        sizes = {row["name"]: row["nativeSizeBytes"] for row in layouts["nativeTypes"]}
        self.assertEqual(sizes["BeyondDynamicBone.TeamManager+TeamData"], 0x1D0)
        self.assertEqual(sizes["BeyondDynamicBone.ClothParameters"], 0x328)
        self.assertEqual(sizes["BeyondDynamicBone.DataChunk"], 8)
        fields = {(row["declaringType"], row["field"]): row["nativePayloadOffset"]
                  for row in layouts["fieldsReadByMethod384856"]}
        self.assertEqual(fields[("BeyondDynamicBone.TeamManager+TeamData",
                                 "negativeScaleDirection")], "0x68")
        self.assertEqual(fields[("BeyondDynamicBone.TeamManager+TeamData",
                                 "negativeScaleQuaternionValue")], "0x88")
        self.assertEqual(fields[("BeyondDynamicBone.TeamManager+TeamData",
                                 "proxyCommonChunk")], "0x124")
        self.assertEqual(fields[("BeyondDynamicBone.TeamManager+TeamData",
                                 "proxyVertexChildDataChunk")], "0x12c")
        self.assertEqual(fields[("BeyondDynamicBone.TeamManager+TeamData",
                                 "baseLineDataChunk")], "0x164")
        self.assertEqual(fields[("BeyondDynamicBone.ClothParameters",
                                 "rotationalInterpolation")], "0xa0")
        self.assertEqual(fields[("BeyondDynamicBone.ClothParameters",
                                 "rootRotation")], "0xa4")

    def test_calc_line_child_traversal_and_rotation_equations(self) -> None:
        flow = self.payload["calcLineEntryControlFlow"]
        self.assertIn("baseLineFlags[baseLineIndex]", flow["entryGates"][1]["condition"])
        self.assertEqual(flow["entryGates"][-1],
                         {"offset": "0x20b", "condition": "baseLineEntryCount != 0"})
        packed = flow["childIndexEncoding"]
        self.assertEqual(packed["childCount"], "packed >> 20 (upper 12 bits)")
        self.assertEqual(packed["localStart"], "packed & 0x000fffff (lower 20 bits)")
        child = flow["childTraversal"]
        self.assertIn("negativeScaleDirection", child["restVector"])
        self.assertIn("Flag_Move (0x02)", child["directionAccumulatorMoveBranch"])
        self.assertIn("directionAccumulator = restVector", child["directionAccumulatorNonMoveBranch"])
        self.assertEqual((child["moveBitSemanticEvidence"]["methodIndex"],
                          child["moveBitSemanticEvidence"]["startVa"]),
                         (386730, "0x1866ff05c"))
        self.assertEqual(
            child["childRotationWrite"],
            "rotations[childVertex] = math.mul(math.mul(parentRotation, signedLocalRotation), childFromTo)",
        )
        parent = flow["parentRotationWrite"]
        self.assertIn("parameter.rotationalInterpolation", parent["interpolation"])
        self.assertIn("parameter.rootRotation", parent["interpolation"])
        self.assertEqual(parent["write"],
                         "rotations[parentVertex] = math.mul(parentFromTo, parentRotation)")
        self.assertIn("no normal/tangent output array", flow["normalTangentNamingBoundary"])

    def test_from_to_rotation_equation_and_degeneracy_boundary(self) -> None:
        flow = self.payload["calcLineEntryControlFlow"]
        helpers = {row["name"]: row for row in flow["helperSpans"]}
        self.assertEqual(helpers["quaternionRotateFloat3"]["throughRetSha256"],
                         "03a1a80c2ead230146ab4c2988e047bad9026de6272f4481370b166e211eae16")
        self.assertEqual(helpers["quaternionHamiltonProduct"]["throughRetSha256"],
                         "e774acaece8257a4bdb8df10ad22b9a0c60995e2b8f4e9a1cfebbb761a70aab6")
        from_to = flow["fromToRotation"]
        self.assertEqual((from_to["methodIdentity"]["methodIndex"],
                          from_to["methodIdentity"]["startVa"]),
                         (386226, "0x1866aef20"))
        self.assertAlmostEqual(from_to["constants"]["epsilon"], 1.0e-6, places=12)
        self.assertAlmostEqual(from_to["constants"]["pi"], 3.1415927410125732)
        equations = " ".join(from_to["managedUnpatchedEquation"])
        self.assertIn("abs(dot + 1.0) < epsilon", equations)
        self.assertIn("abs(1.0 - dot) < epsilon", equations)
        self.assertIn("quaternion.identity", equations)
        self.assertEqual(from_to["ifixRoute"]["patchId"], "0x219")
        self.assertEqual(from_to["ifixRoute"]["selectedAtRuntime"], "unresolved")
        self.assertIn("no explicit guard", from_to["degeneracyBranches"]["zeroOrNonFiniteInput"])
        self.assertIn("runtime numerics remain fail-closed", flow["numericBoundary"])

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
