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
import build_secondary_dynamics_transform_read_contract as builder


class TransformReadContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_generated_contract_rebuilds_exactly(self) -> None:
        self.assertEqual(builder.build_contract(), self.contract)

    def test_126_entries_and_owner_ranges(self) -> None:
        endminf = self.contract["endminf"]
        self.assertEqual(len(endminf["orderedEntries"]), 126)
        self.assertEqual([x["managerIndex"] for x in endminf["orderedEntries"]], list(range(126)))
        self.assertEqual([(x["owner"], x["bindingCount"]) for x in endminf["owners"]],
                         [("MC_Ribbon2", 6), ("MC_Hair", 30), ("MC_Ribbon", 20), ("MC_Coat", 70)])
        self.assertEqual([x["orderedStart"] for x in endminf["owners"]], [0, 6, 36, 56])

    def test_source_flags_are_exact_attribute_mapping(self) -> None:
        entries = self.contract["endminf"]["orderedEntries"]
        expected = {0: (0x01, 0x11), 1: (0x0B, 0x1B), 2: (0x0D, 0x1D)}
        for row in entries:
            self.assertEqual((row["sourceFlag"], row["activeManagerFlag"]), expected[row["attribute"]])
            self.assertEqual(len(row["readChannels"]), 6)
        self.assertEqual(Counter(row["sourceFlag"] for row in entries), Counter({0x0D: 67, 0x01: 36, 0x0B: 23}))

    def test_duplicates_remain_distinct(self) -> None:
        duplicate = self.contract["endminf"]["duplicates"]
        self.assertEqual((duplicate["bindingEntries"], duplicate["uniqueTransforms"], duplicate["duplicateEntries"]),
                         (126, 100, 26))
        self.assertEqual(duplicate["duplicatePathCount"], 26)
        self.assertTrue(duplicate["preservedAsDistinctManagerEntries"])

    def test_base_input_uses_world_matrix_not_local_channels(self) -> None:
        publication = self.contract["baseInputPublication"]
        self.assertIn("localToWorldMatrixArray", publication["managerInput"])
        self.assertIn("do not directly feed", publication["localChannelRole"])
        self.assertEqual(publication["simulationStartMapping"]["authoredPosition"],
                         "proxy.positions[ownerProxyChunk.start + ownerLocalIndex]")

    def test_current_last_equations_and_boundary(self) -> None:
        lifecycle = self.contract["managerLifecycle"]
        self.assertEqual(len(lifecycle["copyDoubleBufferJob"]), 4)
        self.assertEqual(lifecycle["copyDoubleBufferCadence"]["callsPerClothUpdate"], 0)
        self.assertEqual(lifecycle["readTransformJobActiveWrites"]["lastArrays"], "not written by ReadTransformJob")
        boundary = self.contract["executionBoundary"]
        self.assertTrue(boundary["orderedSourceFlagsClosed"])
        self.assertTrue(boundary["endminfOneBoneProxyMappingClosed"])
        self.assertTrue(boundary["copyDoubleBufferActiveCadenceClosed"])
        self.assertTrue(boundary["animatorBufferBranchClosed"])
        self.assertFalse(boundary["targetReady"])
        self.assertFalse(boundary["unityRuntimeModified"])
        self.assertTrue(any("useRelativeTransform" in row for row in boundary["unresolved"]))

    def test_source_static_animator_route_and_cross_frame_boundary(self) -> None:
        branch = self.contract["managerLifecycle"]["sourceStaticBranch"]
        self.assertIs(branch["UseAnimatorTransform"]["value"], False)
        self.assertIn("ReadAnimatorBufferData is skipped", branch["UseAnimatorTransform"]["selectedRoute"])
        self.assertIs(branch["UseCrossFrameJob"]["cctorDefault"], True)
        self.assertFalse(branch["UseCrossFrameJob"]["targetLiveValueClosed"])
        audit = self.contract["native"]["routeAudit"]
        self.assertEqual(audit["magicaManagerStaticFields"]["useAnimatorTransformCompiledWriterVas"],
                         ["0x184cf5449"])
        self.assertEqual(audit["directCalls"]["ReadAnimatorBufferData"]["sourceVas"],
                         ["0x182f91e60"])

    def test_copy_double_buffer_has_no_active_call_site(self) -> None:
        calls = self.contract["native"]["routeAudit"]["directCalls"]
        self.assertEqual(calls["CopyDoubleBuffer"]["directCallCount"], 0)
        self.assertEqual(calls["CopyDoubleBuffer"]["sourceVas"], [])
        self.assertEqual(calls["ReadTransform"]["sourceVas"], ["0x182f91d47", "0x182f91ffb"])

    def test_relative_transform_initial_value_is_closed_but_live_value_is_not(self) -> None:
        relative = self.contract["teamRelativeTransform"]
        self.assertIs(relative["initialValue"], False)
        self.assertFalse(relative["targetLiveValueClosed"])
        self.assertEqual([row["value"] for row in relative["compiledMutators"]], [True, False, True])
        boundary = self.contract["executionBoundary"]
        self.assertTrue(boundary["useRelativeTransformInitialValueClosed"])
        self.assertFalse(boundary["useRelativeTransformTargetLiveValueClosed"])
        self.assertFalse(boundary["useCrossFrameJobTargetLiveValueClosed"])

    def test_native_spans_are_pinned(self) -> None:
        rows = {row["methodIndex"]: row for row in self.contract["native"]["pinnedSpans"]}
        rows_by_name = {row["name"]: row for row in self.contract["native"]["pinnedSpans"]}
        self.assertEqual(rows[384537]["sha256"], "96309abe74a2726bd30e849cb6571f0b2867f655fcb847a61ae634b610e323bf")
        self.assertEqual(rows[385042]["bytes"], 1760)
        self.assertEqual(rows_by_name["MagicaManager..cctor through static defaults"]["bytes"], 171)
        self.assertEqual(rows_by_name["DynamicBoneTransformManager.CopyDoubleBuffer active body"]["bytes"], 335)

    def test_mutated_payload_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            data = json.loads(builder.DEFAULT_PAYLOAD.read_text(encoding="utf-8"))
            data["actors"]["endminf"]["cloths"][0]["proxy_mesh_arrays"]["attributes"]["values"][0] = 2
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(builder.ContractError):
                builder.build_contract(payload_path=path)


if __name__ == "__main__":
    unittest.main()
