from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_m27_live_exact_abi",
    HERE / "verify_endminf_m27_live_exact_abi.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def complete_observation() -> dict[str, object]:
    return {
        "schema": MODULE.LIVE_SCHEMA,
        "status": "complete",
        "observationOnly": True,
        "presentationEnabled": False,
        "capturedPacketArraysUsed": False,
        "renderer": {
            "type": "ParticleSystemRenderer",
            "hierarchy": MODULE.HIERARCHY,
            "rendererPathId": MODULE.RENDERER_PATH_ID,
            "materialPathId": MODULE.MATERIAL_PATH_ID,
            "meshPathId": MODULE.MESH_PATH_ID,
            "activeVertexStreams": MODULE.ACTIVE_STREAMS,
        },
        "compilerSubstitution": {
            "registryReady": True,
            "vertexSwapCount": 1,
            "pixelSwapCount": 1,
            "failureCount": 0,
            "shellVertexSha256": MODULE.SHELL_VS_SHA256,
            "shellPixelSha256": MODULE.SHELL_PS_SHA256,
        },
        "shader": {
            "vertexSha256": MODULE.VS_SHA256,
            "pixelSha256": MODULE.PS_SHA256,
            "vertexIdentity": MODULE.VS_IDENTITY,
            "pixelIdentity": MODULE.PS_IDENTITY,
        },
        "inputAssembler": {
            "vertexStride": 68,
            "fromParticleSystemRenderer": True,
        },
        "target": dict(MODULE.TARGET),
        "depthTarget": dict(MODULE.DEPTH_TARGET),
        "textures": [
            {
                "slot": slot, "property": prop, "width": width,
                "height": height, "dxgiFormat": dxgi, "mipCount": mips,
                "fullMipChain": True, "payloadSha256": payload_sha,
            }
            for slot, prop, width, height, dxgi, mips, payload_sha
            in MODULE.TEXTURE_SLOTS
        ],
        "constantBuffers": [
            {
                "slot": slot, "logicalName": name,
                "fullPublisherOrLogicalBytes": full_bytes,
                "exactUsedPrefixBytes": used_bytes, "producer": producer,
            }
            for slot, name, full_bytes, used_bytes, producer in MODULE.CBUFFERS
        ],
        "publishers": {
            "transformVariablesReady": True,
            "transformVariablesBytes": 1312,
            "shaderVariablesGlobalReady": True,
            "shaderVariablesGlobalBytes": 3200,
        },
    }


class LiveExactAbiChecksTests(unittest.TestCase):
    def assert_complete(self, value: dict[str, object]) -> None:
        failures = [row for row in MODULE._live_checks(value) if not row["passed"]]
        self.assertEqual(failures, [])

    def first_failure(self, value: dict[str, object]) -> str:
        failures = [row for row in MODULE._live_checks(value) if not row["passed"]]
        self.assertTrue(failures)
        return failures[0]["name"]

    def test_complete_live_particle_renderer_observation_passes(self) -> None:
        self.assert_complete(complete_observation())

    def test_missing_observation_fails_closed(self) -> None:
        checks = MODULE._live_checks(None)
        self.assertEqual(checks[0]["name"], "live.observation")
        self.assertFalse(checks[0]["passed"])

    def test_packet_arrays_are_rejected(self) -> None:
        value = complete_observation()
        value["capturedPacketArraysUsed"] = True
        self.assertEqual(
            self.first_failure(value), "live.capturedPacketArraysUsed")

    def test_wrong_shader_identity_is_rejected(self) -> None:
        value = complete_observation()
        value["shader"]["vertexSha256"] = "00" * 32
        self.assertEqual(
            self.first_failure(value), "live.shader.vertexSha256")

    def test_stride_outside_60_68_is_rejected(self) -> None:
        value = complete_observation()
        value["inputAssembler"]["vertexStride"] = 136
        self.assertEqual(
            self.first_failure(value), "live.inputAssembler.vertexStride")

    def test_obsolete_texture_slot_order_is_rejected(self) -> None:
        value = complete_observation()
        value["textures"][0]["property"] = "_ParallaxMap"
        self.assertEqual(self.first_failure(value), "live.t0.property")

    def test_partial_mip_chain_is_rejected(self) -> None:
        value = complete_observation()
        value["textures"][3]["mipCount"] = 1
        self.assertEqual(self.first_failure(value), "live.t3.mipCount")

    def test_b3_identity_is_rejected_when_wrong(self) -> None:
        value = complete_observation()
        value["constantBuffers"][3]["logicalName"] = "EndfieldM27CB3"
        self.assertEqual(self.first_failure(value), "live.b3.logicalName")

    def test_full_global_publisher_size_is_required(self) -> None:
        value = complete_observation()
        value["publishers"]["shaderVariablesGlobalBytes"] = 2512
        self.assertEqual(
            self.first_failure(value),
            "live.publishers.shaderVariablesGlobalBytes")

    def test_five_mrt_descriptor_is_required(self) -> None:
        value = complete_observation()
        value["target"]["renderTargetCount"] = 4
        self.assertEqual(
            self.first_failure(value), "live.target.renderTargetCount")


if __name__ == "__main__":
    unittest.main()
