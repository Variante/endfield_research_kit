#!/usr/bin/env python3
"""Focused tests for the pinned Burst export candidate contract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_burst_export_contract as builder


class SecondaryDynamicsBurstExportTests(unittest.TestCase):
    def test_published_report_is_pinned_and_fail_closed(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "secondary_dynamics_static_export_core_identities_partial_managed_routes_unresolved")
        self.assertEqual(payload["native_gate"]["gameAssembly"]["sha256"], builder.EXPECTED_GAME_ASSEMBLY_SHA256)
        self.assertEqual(payload["native_gate"]["globalMetadata"]["sha256"], builder.EXPECTED_METADATA_SHA256)
        self.assertEqual(payload["native_gate"]["libBurstGenerated"]["sha256"], builder.EXPECTED_LIB_BURST_SHA256)
        self.assertEqual(payload["pe"]["totalNamedExportCount"], 3141)
        self.assertEqual(payload["pe"]["hashedExportCount"], 628)
        self.assertEqual(payload["pe"]["hashedExportNamesSha256"], "3575fa430f691be98c1f2b6cadfb71e74854f422eed7fce767215d974ac332c9")
        self.assertEqual(payload["functionBoundary"]["rule"], "Capstone-decoded-instructions-through-first-real-ret")
        self.assertEqual(
            payload["targets"]["simulationStartRange"]["candidates"][0]["hash"],
            "c7e2be088565d3ff7a6e7ba86d23fd51",
        )
        self.assertEqual(
            [row["hash"] for row in payload["targets"]["colliderStartRange"]["candidates"]],
            [
                "4aa6773b1eaf6055e0feb9593e092585",
                "7342567c29c434b5b924be51bd8e34b7",
                "8b3d2761aaaac71a35d4a2557d570456",
            ],
        )
        self.assertEqual(
            [row["hash"] for row in payload["targets"]["colliderEndRange"]["candidates"]],
            ["b44b8d6a5416f62541c69d9812961578"],
        )
        self.assertEqual(
            [row["hash"] for row in payload["targets"]["colliderEndRange"]["abiShapeFalseCandidates"]],
            [
                "5d15fdfe5676d33316f2415a1f41d523",
                "e6aec003f0525fe127cd9c0ccb59b1e2",
            ],
        )
        unresolved = " ".join(payload["unresolved"])
        self.assertIn("GetProcAddress", unresolved)
        self.assertIn("hash bytes", unresolved)

    def test_direct_call_identity_and_parameter_contracts_are_explicit(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        simulation = payload["targets"]["simulationStartRange"]
        start = payload["targets"]["colliderStartRange"]
        end = payload["targets"]["colliderEndRange"]
        self.assertEqual(simulation["directInvokeMethodIndex"], 385570)
        self.assertEqual(simulation["parameterContract"]["parameterCount"], 29)
        self.assertEqual(simulation["parameterContract"]["directInvokeNativeArrayParameterCount"], 24)
        self.assertEqual(simulation["parameterContract"]["sourceJobNativeArrayFieldCount"], 23)
        self.assertEqual(simulation["parameterContract"]["sourceJobNativeReferenceFieldCount"], 1)
        self.assertEqual((start["directInvokeMethodIndex"], start["directInvokeVa"]), (385416, "0x186762cc0"))
        self.assertEqual((end["directInvokeMethodIndex"], end["directInvokeVa"]), (385317, "0x18675b0cc"))
        self.assertEqual(start["parameterContract"]["parameterCount"], 17)
        self.assertEqual(end["parameterContract"]["parameterCount"], 6)
        self.assertEqual(end["parameterContract"]["directInvokeNativeArrayParameterCount"], 6)
        self.assertEqual(end["parameterContract"]["sourceJobNativeArrayFieldCount"], 5)
        self.assertEqual(end["parameterContract"]["sourceJobNativeReferenceFieldCount"], 1)

    def test_simulation_semantic_fingerprint_is_closed_at_runtime_boundary(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        fingerprint = payload["targets"]["simulationStartRange"]["semanticFingerprint"]
        self.assertEqual(fingerprint["status"], "export_thunk_and_dual_cpu_solver_core_closed_managed_route_unobserved")
        self.assertEqual(fingerprint["candidateHash"], "c7e2be088565d3ff7a6e7ba86d23fd51")
        self.assertEqual(fingerprint["export"]["rva"], "0x3616e0")
        self.assertEqual(fingerprint["export"]["bodySha256"], "38e122699775a7bc42cb1277028ece1430c467c9112510aa29948ee8d3f2e45d")
        self.assertEqual(fingerprint["abi"]["directInvokeNativeArrayParameterCount"], 24)
        self.assertEqual(fingerprint["abi"]["sourceJobNativeArrayFieldCount"], 23)
        self.assertEqual(fingerprint["abi"]["sourceJobNativeReferenceFieldCount"], 1)
        self.assertEqual(len(fingerprint["abi"]["stackInputLoads"]), 25)
        self.assertEqual(len(fingerprint["abi"]["stackOutputStores"]), 25)
        self.assertEqual(fingerprint["abi"]["directCalls"], [])
        self.assertEqual(fingerprint["abi"]["tailTransfers"], [])
        target = fingerprint["indirectTarget"]
        self.assertEqual((target["targetRva"], target["section"], target["fileBacked"]), ("0x3c6390", ".data", False))
        self.assertEqual(target["diskState"], "zero_fill_bss_no_on_disk_pointer")
        self.assertEqual(target["runtimeValue"], "statically_assigned_by_burst.initialize_per_cpu_variant")
        self.assertEqual(fingerprint["internalCfg"]["status"], "slot_entry_range_and_solver_core_graph_closed")
        self.assertEqual(fingerprint["internalCfg"]["recursionBound"], {"maxDepth": 4, "maxNodes": 128, "maxEdges": 256})
        self.assertEqual(fingerprint["internalCfg"]["seedTargetRva"], "0x3c6390")
        self.assertEqual(fingerprint["jobPayload"]["status"], "solver_core_identity_closed_complete_numeric_decode_pending")
        self.assertEqual(fingerprint["jobPayload"]["nativeArrayFieldAccesses"], [])
        self.assertEqual(fingerprint["jobPayload"]["strideBytes"], [4, 464, 808])
        self.assertEqual(fingerprint["jobPayload"]["constants"], [])
        self.assertEqual(fingerprint["jobPayload"]["writebacks"], [])
        exact = fingerprint["exactCoreIdentity"]
        self.assertEqual(exact["status"], "static_slot_entry_range_and_dual_cpu_solver_core_closed")
        variants = {row["cpuVariant"]: row for row in exact["variants"]}
        self.assertEqual(variants["x64_sse2"]["entry"]["rva"], "0xd3c20")
        self.assertEqual(variants["x64_sse2"]["rangeLoop"]["rva"], "0xd3db0")
        self.assertEqual(variants["x64_sse2"]["solverCore"]["rva"], "0xc6f10")
        self.assertEqual(variants["avx2"]["entry"]["rva"], "0x26a370")
        self.assertEqual(variants["avx2"]["rangeLoop"]["rva"], "0x26a440")
        self.assertEqual(variants["avx2"]["solverCore"]["rva"], "0x25e830")
        self.assertEqual(fingerprint["identityBoundary"], "export_and_core_identity_closed_managed_route_unresolved")
        self.assertEqual(fingerprint["sourcePins"]["libBurstGeneratedSha256"], builder.EXPECTED_LIB_BURST_SHA256)
        self.assertEqual(payload["contractComparison"]["burstWrapperProvenance"]["fileSha256"], builder._sha256(builder.REPO_ROOT / payload["contractComparison"]["burstWrapperProvenance"]["path"]))

    def test_simulation_update_and_end_exact_dual_cpu_core_graphs_are_closed(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        update = payload["targets"]["simulationUpdateBasicPostureRange"]
        self.assertEqual(
            update["status"],
            "static_semantic_export_identity_and_dual_cpu_cores_closed_managed_wrapper_route_unobserved",
        )
        self.assertEqual(update["candidates"][0]["hash"], "a8df0cddc9889e0c46f8bec650d8b959")
        self.assertEqual(
            [row["hash"] for row in update["abiShapeFalseCandidates"]],
            ["56d6e448a273fb14345051fc02058afe", "6a5470d135bde394bed7e7182cdf7c65"],
        )
        self.assertEqual(
            update["parameterContract"]["managedFallbackElementStridesBytes"],
            [4, 464, 1, 4, 12, 16, 2, 2, 2, 24, 16, 24, 16, 4],
        )
        update_exact = update["exactCoreIdentity"]
        self.assertEqual(update_exact["functionPointerSlotRva"], "0x3c5ed0")
        update_variants = {row["cpuVariant"]: row for row in update_exact["variants"]}
        self.assertEqual(update_variants["x64_sse2"]["solverCore"]["rva"], "0xa5670")
        self.assertEqual(update_variants["avx2"]["solverCore"]["rva"], "0x241aa0")

        end = payload["targets"]["simulationEndRange"]
        self.assertEqual(end["candidates"][0]["hash"], "41ab6c9cba7b13c1177cc44fe548d030")
        self.assertEqual(
            [row["hash"] for row in end["abiShapeFalseCandidates"]],
            ["226261a75cb450326f01659bdc8cb2d5", "62061c35abfe0d5ed4fb4b9019361071"],
        )
        self.assertEqual(
            end["parameterContract"]["canonicalStructureStridesBytes"],
            {"TeamData": 464, "ClothParameters": 808, "CenterData": 696},
        )
        end_exact = end["exactCoreIdentity"]
        self.assertEqual(end_exact["functionPointerSlotRva"], "0x3c4fb0")
        end_variants = {row["cpuVariant"]: row for row in end_exact["variants"]}
        self.assertEqual(end_variants["x64_sse2"]["solverCore"]["rva"], "0xb5450")
        self.assertEqual(end_variants["avx2"]["solverCore"]["rva"], "0x24fa60")

    def test_managed_cross_check_preserves_native_reference_boundary(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        managed = payload["targets"]["simulationStartRange"]["semanticFingerprint"]["managedCrossCheck"]
        self.assertEqual((managed["fieldCount"], managed["nativeArrayCount"], managed["nativeReferenceCount"]), (26, 23, 1))
        self.assertEqual(managed["managedNativeContainerCount"], 24)
        self.assertEqual(managed["nativeReferenceArgumentIndexes"], [28])
        self.assertEqual(managed["nativeReferenceFields"][0]["name"], "_indexCount")
        direct = managed["managedDirectInvokeContract"]
        self.assertEqual(
            (direct["parameterCount"], direct["directInvokeNativeArrayParameterCount"],
             direct["sourceJobNativeArrayFieldCount"],
             direct["sourceJobNativeReferenceFieldCount"],
             direct["lengthPointerArgumentIndex"]),
            (29, 24, 23, 1, 28),
        )
        self.assertIn("corresponding managed job field is NativeReference", direct["boundary"])
        end = managed["endSimulation"]
        self.assertEqual((end["fieldCount"], end["nativeArrayCount"], end["nativeReferenceCount"]), (17, 15, 1))
        self.assertEqual(end["nativeReferenceFields"][0]["name"], "_indexCount")

    def test_collider_end_static_audit_closes_exact_export_and_rejects_false_candidates(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        audit = payload["targets"]["colliderEndRange"]["candidateAudit"]
        self.assertEqual(payload["targets"]["colliderEndRange"]["status"], "static_semantic_export_identity_closed_managed_wrapper_route_unobserved")
        self.assertEqual(audit["status"], "static_semantic_export_identity_closed_managed_wrapper_route_unobserved")
        self.assertEqual(audit["comparison"]["candidateCount"], 2)
        self.assertEqual(audit["comparison"]["semanticCompatibleCandidateCount"], 1)
        self.assertTrue(audit["comparison"]["sameWrapperCfg"])
        self.assertTrue(audit["comparison"]["sameParameterForwarding"])
        self.assertFalse(audit["comparison"]["fieldOffsetsPresentInCandidateThunk"])
        self.assertTrue(audit["comparison"]["staticInitializerSlotIdentityDiscriminates"])
        self.assertTrue(audit["comparison"]["wrapperSlotsDistinct"])
        self.assertFalse(audit["comparison"]["runtimeSelectedPointerObserved"])
        self.assertEqual(
            [row["name"] for row in audit["parameterContract"]["parameters"]],
            ["jobColliderIndexList", "nowPositions", "nowRotations", "oldPositions", "oldRotations", "_indexCount"],
        )
        self.assertEqual(
            [(row["name"], row["jobOffset"], row["strideBytes"])
             for row in audit["managedFallbackComparison"]["fields"]],
            [
                ("nowPositions", "0x10", 24),
                ("nowRotations", "0x20", 16),
                ("oldPositions", "0x30", 24),
                ("oldRotations", "0x40", 16),
            ],
        )
        self.assertEqual(
            audit["managedFallbackComparison"]["stateCarryForward"],
            [
                {
                    "sourceField": "nowPositions",
                    "destinationField": "oldPositions",
                    "elementType": "Unity.Mathematics.double3",
                    "widthBytes": 24,
                },
                {
                    "sourceField": "nowRotations",
                    "destinationField": "oldRotations",
                    "elementType": "Unity.Mathematics.quaternion",
                    "widthBytes": 16,
                },
            ],
        )
        exact = audit["exactSemanticExport"]
        self.assertEqual(exact["status"], "static_export_slot_and_dual_cpu_core_identity_closed")
        self.assertEqual(exact["hash"], "b44b8d6a5416f62541c69d9812961578")
        self.assertEqual(exact["ordinal"], 421)
        self.assertEqual(exact["export"]["rva"], "0x358a20")
        self.assertEqual(exact["export"]["functionPointerSlotRva"], "0x3c6060")
        variants = {row["cpuVariant"]: row for row in exact["variants"]}
        self.assertEqual(variants["x64_sse2"]["entry"]["rva"], "0xae190")
        self.assertEqual(variants["x64_sse2"]["core"]["rva"], "0xae300")
        self.assertEqual(variants["avx2"]["entry"]["rva"], "0x24a030")
        self.assertEqual(variants["avx2"]["core"]["rva"], "0x24a1a0")
        self.assertEqual(exact["payload"]["positionStrideBytes"], 24)
        self.assertEqual(exact["payload"]["rotationStrideBytes"], 16)
        for candidate in audit["candidates"]:
            self.assertEqual(candidate["wrapper"]["branchCount"], 0)
            self.assertEqual(candidate["wrapper"]["incomingGprPreserved"], ["rcx", "rdx", "r8", "r9"])
            self.assertEqual(candidate["wrapper"]["decodedForwardingParameterNames"], ["jobColliderIndexList", "nowPositions", "nowRotations", "oldPositions", "oldRotations", "_indexCount"])
            self.assertEqual(candidate["wrapper"]["payloadAccesses"], [])
            self.assertEqual(candidate["wrapper"]["payloadDereferenceCount"], 0)
            self.assertEqual(candidate["wrapper"]["payloadWritebackCount"], 0)
            self.assertEqual(len(candidate["wrapper"]["stackParameterForwarding"]), 2)
            self.assertEqual(len(candidate["wrapper"]["outgoingStackForwarding"]), 2)
            self.assertEqual(candidate["runtimeFunctionPointerSlot"]["initializers"]["statics"][0]["staticSelectorConstants"], ["0xedfccb8b263b8f83"])
            for row in candidate["runtimeFunctionPointerSlot"]["initializers"]["externals"]:
                self.assertEqual(row["candidateWrapperSlotStoreMatches"], [])
                self.assertGreater(row["resolverCallCount"], 0)
            for row in candidate["runtimeFunctionPointerSlot"]["initializers"]["statics"]:
                self.assertEqual(row["candidateWrapperSlotStoreMatches"], [])
        semantics = {row["hash"]: row["semanticCompatibility"] for row in audit["candidates"]}
        self.assertEqual(semantics["5d15fdfe5676d33316f2415a1f41d523"]["status"], "incompatible_with_canonical_job_element_strides")
        self.assertEqual(semantics["e6aec003f0525fe127cd9c0ccb59b1e2"]["status"], "incompatible_with_direct_invoke_container_abi")
        self.assertEqual(
            [variant["bodySha256"] for variant in semantics["5d15fdfe5676d33316f2415a1f41d523"]["coreVariants"]],
            ["2c13d41676b518db37f84558a675726189ca29ffc4fadb757af6f8ef921bc0e1",
             "fa0774f9c385ab162d8e03093ee29d2bbd3af70ab544b99fd943f447bd8c25e6"],
        )
        for row in payload["targets"]["simulationStartRange"]["semanticFingerprint"]["initializerExports"]:
            if row["initializerRole"] == "statics":
                self.assertEqual((row["sharedMemoryKey"], row["sharedMemorySizeBytes"], row["sharedMemoryAlignmentBytes"]), ("0xedfccb8b263b8f83", "0x80000", 16))
        self.assertIn("runtime GetProcAddress", audit["comparison"]["requiredNextEvidence"])
        self.assertEqual(audit["provenance"]["solver"]["fileSha256"], builder._sha256(builder.REPO_ROOT / audit["provenance"]["solver"]["path"]))

    def test_canonical_installed_dll_and_export_set(self) -> None:
        dll = Path(json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))["native_gate"]["libBurstGenerated"]["path"])
        self.assertTrue(dll.is_file())
        self.assertEqual(builder._sha256(dll), builder.EXPECTED_LIB_BURST_SHA256)
        parsed = builder._pe_exports(dll)
        names = sorted(row["name"] for row in parsed["hashed"])
        self.assertEqual(len(names), 628)
        self.assertEqual(
            __import__("hashlib").sha256("\n".join(names).encode()).hexdigest(),
            "3575fa430f691be98c1f2b6cadfb71e74854f422eed7fce767215d974ac332c9",
        )

    def test_zero_fill_function_pointer_slot_is_not_file_backed(self) -> None:
        dll = Path(json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))["native_gate"]["libBurstGenerated"]["path"])
        parsed = builder._pe_exports(dll)
        section = builder._section_record(parsed, 0x3C6390, 8)
        self.assertIsNotNone(section)
        assert section is not None
        self.assertEqual(section["name"], ".data")
        self.assertFalse(section["fileBacked"])
        with self.assertRaisesRegex(builder.ContractError, "zero-fill"):
            builder._rva_file_offset(parsed, 0x3C6390, 8)

    def test_sibling_provenance_rejects_tampered_status(self) -> None:
        gate = {
            "gameAssembly": {"sha256": builder.EXPECTED_GAME_ASSEMBLY_SHA256},
            "globalMetadata": {"sha256": builder.EXPECTED_METADATA_SHA256},
            "libBurstGenerated": {"sha256": builder.EXPECTED_LIB_BURST_SHA256},
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sibling = root / "sibling.json"
            sibling.write_text(json.dumps({
                "schema": "test.schema.v1", "status": "tampered",
                "nativeGate": {"gameAssembly": {"sha256": builder.EXPECTED_GAME_ASSEMBLY_SHA256},
                                "globalMetadata": {"sha256": builder.EXPECTED_METADATA_SHA256}},
            }), encoding="utf-8")
            with patch.object(builder, "DEFAULT_OUTPUT", root / "out.json"):
                with self.assertRaisesRegex(builder.ContractError, "schema/status drift"):
                    builder._sibling_provenance("sibling.json", gate, "test.schema.v1", "expected")

    def test_collider_wrapper_evidence_rejects_gpr_payload_and_order_tampering(self) -> None:
        payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        wrapper = payload["targets"]["colliderEndRange"]["candidateAudit"]["candidates"][0]["wrapper"]
        expected = wrapper["decodedForwardingParameterNames"]
        for key, value, message in (
            ("incomingGprPreserved", ["rcx", "rdx", "r8"], "GPR"),
            ("payloadDereferenceCount", 1, "payload"),
            ("payloadWritebackCount", 1, "payload"),
            ("decodedForwardingParameterNames", list(reversed(expected)), "order"),
        ):
            tampered = dict(wrapper)
            tampered[key] = value
            with self.assertRaisesRegex(builder.ContractError, message):
                builder._validate_collider_wrapper_evidence(tampered, expected)

    def test_stack_feature_decoder_preserves_width_and_offsets(self) -> None:
        body = bytes.fromhex(
            "f3 0f 11 64 24 20 "
            "48 89 44 24 28 "
            "4c 89 84 24 80 00 00 00 c3"
        )
        decoded_body, instructions = builder._decode_body(body, 0x180000000)
        self.assertEqual(
            builder._stack_writes_from_instructions(instructions),
            [
                {"offset": 32, "widthBytes": 4, "kind": "xmm"},
                {"offset": 40, "widthBytes": 8},
                {"offset": 128, "widthBytes": 8},
            ],
        )

    def test_export_parser_rejects_non_pe_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lib_burst_generated.dll"
            path.write_bytes(b"0" * 128)
            with self.assertRaisesRegex(builder.ContractError, "not a PE image"):
                builder._pe_exports(path)

    def test_missing_burst_dll_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gameassembly = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            gameassembly.write_bytes(b"game")
            metadata.write_bytes(b"metadata")
            result = SimpleNamespace(
                validated=True,
                status="validated",
                detail="",
                gameassembly=gameassembly,
                metadata=metadata,
                gameassembly_sha256=builder.EXPECTED_GAME_ASSEMBLY_SHA256,
                metadata_sha256=builder.EXPECTED_METADATA_SHA256,
            )
            with patch.object(builder, "check_installed_native_inputs", return_value=result):
                with self.assertRaisesRegex(builder.ContractError, "missing pinned lib_burst_generated"):
                    builder._native_gate(gameassembly, metadata)


if __name__ == "__main__":
    unittest.main()
