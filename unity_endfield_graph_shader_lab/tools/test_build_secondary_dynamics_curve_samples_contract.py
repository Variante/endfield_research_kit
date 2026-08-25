#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import struct
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
BUILDER = TOOLS / "build_secondary_dynamics_curve_samples_contract.py"
spec = importlib.util.spec_from_file_location("curve_samples_builder_under_test", BUILDER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load {BUILDER}")
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


EXPECTED_PACKED_SHA256 = {
    "MC_Ribbon2": {
        "dampingCurveData": "313bc52b9cc6be460b48c75c785203b699a3d6ec9369e7e329c49b56ae24d26f",
        "radiusCurveData": "dcd4023377239886082900aee768e40d68703ea3aca945d7fbba27878965514f",
        "distanceRestorationStiffness": "0fc97e2da5930d170c76547f768af1fc57c66efe8db77b0b671a831d28bf34da",
        "angleRestorationStiffness": "74b1fe2c120cbcf0793b47c3276c18eba9fa2dc243ad67698730127c0534d396",
        "angleLimit": "13e72fa2a1cdf02a5261f7aebf2ec26035301a3b5e43bcea4042ce3057719921",
    },
    "MC_Hair": {
        "dampingCurveData": "409c8270bee4310c4bcad8b480158cd1be762afb11311b29c3448e8fad240c0c",
        "radiusCurveData": "346d8e08d11a98d3b64f31385fce11588c75d4fdae0ced80c2762153a09a157e",
        "distanceRestorationStiffness": "9628e545ed3ac074e5a6cbf542a642b62482fbfca9b4cb3ea4743a1874256e37",
        "angleRestorationStiffness": "0657aaaf43a1ba56a23b769e1b5d3c791a5e5d54dbb6397476b989a81bee09ae",
        "angleLimit": "fdaeb744b0999530bc0580df3d802a5174fdf2b1c6fc577b476449572267827e",
    },
    "MC_Ribbon": {
        "dampingCurveData": "a0f31b44b405ac0becb66bd187d919294f464ac61dc33d7941c7f5a2be0390c5",
        "radiusCurveData": "ceb0fd2d32cb643f6409d614458d00f1f44b87211cb00c10c9f54eaeddd05879",
        "distanceRestorationStiffness": "0fc97e2da5930d170c76547f768af1fc57c66efe8db77b0b671a831d28bf34da",
        "angleRestorationStiffness": "b58d550b2fc021320b537367c7b4c93976ddaaf3b06a533ccbe54ca8864bc2ec",
        "angleLimit": "13e72fa2a1cdf02a5261f7aebf2ec26035301a3b5e43bcea4042ce3057719921",
    },
    "MC_Coat": {
        "dampingCurveData": "3721abf0f0099f4d0ad096b87e05fc4f3e522e4e9d18b2b9596a73854d23c227",
        "radiusCurveData": "f18cf8d09539ea880502218389d460a552468365ecb801ddfdd926235f47a949",
        "distanceRestorationStiffness": "9628e545ed3ac074e5a6cbf542a642b62482fbfca9b4cb3ea4743a1874256e37",
        "angleRestorationStiffness": "ad212b2a87e6ecd564983a4c4203414f98ec883950460c5cc370517e86babc3d",
        "angleLimit": "dc228a0a5f4e3f4a3a5dfdca6fa37c0bf2ade8e8dac331d5935437831e86d390",
    },
}


class CurveSamplesContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # The checked-in lane words were produced by the builder's two-editor
        # golden run. Focused tests intentionally do not launch another Unity
        # process or contend with the shared character-recovery project.
        cls.contract = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_generated_contract_is_bound_to_current_authored_source(self) -> None:
        source = self.contract["source"]["solverInputs"]
        self.assertEqual(source["sha256"], builder._sha256(builder.SOLVER_INPUTS))
        self.assertEqual(source["size"], builder.SOLVER_INPUTS.stat().st_size)

    def test_all_four_owners_and_twenty_buffers_are_closed(self) -> None:
        self.assertEqual(list(self.contract["owners"]), list(EXPECTED_PACKED_SHA256))
        self.assertEqual(self.contract["validation"]["allOwnerBufferCount"], 20)
        self.assertEqual(self.contract["validation"]["unresolvedDomains"], [])
        self.assertTrue(self.contract["validation"]["unityAnimationCurveExecuted"])

    def test_every_buffer_is_sixteen_binary32_lanes(self) -> None:
        for owner in self.contract["owners"].values():
            for row in owner["buffers"].values():
                self.assertEqual(len(row["samples"]), 16)
                self.assertEqual(len(row["sampleBitsHex"]), 16)
                for value, bits in zip(row["samples"], row["sampleBitsHex"]):
                    self.assertEqual(struct.pack("<f", value), struct.pack("<I", int(bits, 16)))

    def test_all_packed_golden_hashes_match(self) -> None:
        actual = {
            owner: {name: row["packedLittleEndianSha256"] for name, row in payload["buffers"].items()}
            for owner, payload in self.contract["owners"].items()
        }
        self.assertEqual(actual, EXPECTED_PACKED_SHA256)

    def test_constant_buffers_replicate_authored_binary32(self) -> None:
        for owner in self.contract["owners"].values():
            for row in owner["buffers"].values():
                if row["useCurve"]:
                    continue
                scalar_bits = struct.unpack("<I", struct.pack("<f", row["value"]))[0]
                self.assertEqual(row["sampleBitsHex"], [f"{scalar_bits:08x}"] * 16)

    def test_requested_stage_buffer_census_is_exact(self) -> None:
        self.assertEqual(self.contract["requestedStageBufferCounts"], {
            "Start": 1, "Tether": 0, "Distance": 1, "Angle": 2,
            "Point": 1, "Basic": 0, "End": 0,
        })
        for owner in self.contract["owners"].values():
            actual = {stage: 0 for stage in self.contract["requestedStageBufferCounts"]}
            for row in owner["buffers"].values():
                actual[row["consumerStage"]] += 1
            self.assertEqual(actual, self.contract["requestedStageBufferCounts"])

    def test_native_conversion_chain_is_hash_pinned(self) -> None:
        rebuilt_native = builder._native_evidence(None, None)
        self.assertEqual(rebuilt_native, self.contract["nativeGate"])
        methods = {row["methodIndex"]: row for row in rebuilt_native["methods"]}
        self.assertEqual(set(methods), set(builder.METHODS))
        self.assertEqual(methods[383686]["method"], "GetClothParameters")
        self.assertEqual(methods[384360]["method"], "ConvertFloatArray")
        self.assertEqual(methods[385965]["method"], "ConvertAnimationCurve")
        self.assertEqual(self.contract["nativeGate"]["sampleDivisor"]["bits"], "00007041")

    def test_game_version_and_dual_editor_golden_are_closed(self) -> None:
        self.assertEqual(self.contract["nativeGate"]["unityPlayer"]["unityVersion"], "2021.3.34f5")
        golden = self.contract["conversion"]["unityGolden"]
        self.assertEqual(golden["nearestPatchVersion"], "2021.3.34f1")
        self.assertEqual(golden["crosscheckVersion"], "2022.3.62f3")
        self.assertTrue(golden["allRowsExecuted"])
        self.assertTrue(golden["allLaneWordsBitIdenticalAcrossProbes"])
        self.assertEqual(golden["nearestPatchProbeSourceSha256"], golden["crosscheckProbeSourceSha256"])


if __name__ == "__main__":
    unittest.main()
