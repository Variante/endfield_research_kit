from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_m27_live_exact_abi",
    HERE / "verify_endminf_m27_live_exact_abi.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

REPO = HERE.parents[1]


def b3_source_fixture() -> tuple[
        dict[str, object], dict[str, object], dict[str, object], str, str, str]:
    mapping = json.loads((
        REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/"
        "Generated/Characters/Playable/Endminf/ExternalUiEffects/"
        "endminf_liteffect_resource_mapping.json"
    ).read_text(encoding="utf-8"))
    material = json.loads((
        REPO / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
        "json_by_type/Material/"
        "M_fx_endminm_gfx_27_pA531A88850690EB8.json"
    ).read_text(encoding="utf-8-sig"))
    frame = json.loads((
        REPO / "scratch/reverse_engineering/endfield_capture/"
        "20260829T224523Z/graphics/frames/2344/metadata.json"
    ).read_text(encoding="utf-8"))
    draw = next(
        row for row in frame["drawRecords"]
        if row.get("priorityShaderPair") and
        row.get("priorityM27Geometry"))
    shell = (
        REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/"
        "Shaders/Diagnostics/EndfieldEndminfM27GenerativeExactAbiShell.shader"
    ).read_text(encoding="utf-8")
    runtime_material = (
        REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/"
        "Generated/Characters/Playable/Endminf/Effects/Overview/Materials/"
        "M_fx_endminm_gfx_27_pA531A88850690EB8.mat"
    ).read_text(encoding="utf-8")
    compatibility_shader = (
        REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/"
        "Shaders/Recovered/EndfieldEndminfLitEffectVisualCompatibility.shader"
    ).read_text(encoding="utf-8")
    return (mapping, material, draw, shell, runtime_material,
            compatibility_shader)


def complete_observation() -> dict[str, object]:
    return {
        "schema": MODULE.LIVE_SCHEMA,
        "status": "complete",
        "observationOnly": True,
        "presentationEnabled": False,
        "capturedPacketArraysUsed": False,
        "authentication": {
            "schema": MODULE.LIVE_AUTHENTICATION_SCHEMA,
            "actualDrawRendererObserved": True,
            "staticContractFieldsSynthesized": False,
            "synchronizedDrawId": "camera:frame:draw",
            "producerReportSha256": "11" * 32,
        },
        "renderer": {
            "type": "ParticleSystemRenderer",
            "hierarchy": MODULE.HIERARCHY,
            "rendererPathId": MODULE.RENDERER_PATH_ID,
            "materialPathId": MODULE.MATERIAL_PATH_ID,
            "meshPathId": MODULE.MESH_PATH_ID,
            "activeVertexStreams": MODULE.ACTIVE_STREAMS,
            "drawRendererSubmissionCount": 1,
        },
        "compilerSubstitution": {
            "registryReady": True,
            "generativeShellPinSchema": MODULE.GENERATIVE_SHELL_PIN_SCHEMA,
            "generativeShellPinStatus":
                "independently_pinned_d3d11_callback",
            "generativeShellPinReportSha256": "22" * 32,
            "vertexSwapCount": 1,
            "pixelSwapCount": 1,
            "failureCount": 0,
            "shellVertexSha256": "33" * 32,
            "shellPixelSha256": "44" * 32,
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
            "actualParticleRecordRangeObserved": True,
            "geometryRendererPathId": MODULE.RENDERER_PATH_ID,
        },
        "target": {
            **MODULE.TARGET,
            "width": 1920,
            "height": 1080,
            "viewport": [0, 0, 1920, 1080],
        },
        "renderTargets": [
            {
                "slot": slot,
                "role": role,
                "textureFormat": texture_format,
                "viewFormat": view_format,
                "sampleCount": 1,
                "width": 1920,
                "height": 1080,
                "viewport": [0, 0, 1920, 1080],
            }
            for slot, role, texture_format, view_format in MODULE.MRT_SLOTS
        ],
        "depthTarget": {
            **MODULE.DEPTH_TARGET,
            "width": 1920,
            "height": 1080,
        },
        "fixedState": {
            "depthWriteMask": 1,
            "depthFunction": 7,
            "cullMode": 3,
            "frontCounterClockwise": True,
            "scissorEnabled": True,
        },
        "textures": [
            {
                "slot": slot, "property": prop, "width": width,
                "height": height, "dxgiFormat": dxgi, "mipCount": mips,
                "fullMipChain": True, "payloadSha256": payload_sha,
            }
            for slot, prop, width, height, dxgi, mips, payload_sha
            in MODULE.TEXTURE_SLOTS
        ] + [
            {
                "slot": slot,
                "property": prop,
                "serializedNull": True,
                "shaderDefault": "black",
                "observedFromActualDraw": True,
                "objectId": 1234,
            }
            for slot, prop in MODULE.SERIALIZED_NULL_TEXTURE_SLOTS
        ],
        "samplers": [
            {
                "slot": slot,
                "active": True,
                "observedFromActualDraw": True,
            }
            for slot in MODULE.SAMPLER_SLOTS
        ],
        "vertexResources": [
            {
                "slot": 0,
                "kind": "StructuredBuffer",
                "logicalName": "_VertexSkinMatrices",
                "stride": 16,
                "skinBranchActive": False,
                "sourceMeshSkinRows": 0,
            }
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
            "b0SelectedReadsAuthenticated": True,
            "b1SelectedReadsAuthenticated": True,
            "terrainSubsurfaceReady": True,
            "terrainSubsurfacePublisher":
                "EndfieldRecoveredTerrainSubsurfaceConstants",
            "terrainSubsurfaceNativeContractSchema":
                MODULE.TERRAIN_NATIVE_CONTRACT_SCHEMA,
            "terrainSubsurfaceSelectedFrameSchema":
                MODULE.TERRAIN_SELECTED_FRAME_SCHEMA,
            "terrainSubsurfaceProvenanceSha256": "55" * 32,
            "terrainSubsurfacePublishedValue": 0,
            "terrainSubsurfaceObservedRetailValue": 0,
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

    def test_front_ccw_fixed_state_is_required(self) -> None:
        value = complete_observation()
        value["fixedState"]["frontCounterClockwise"] = False
        self.assertEqual(
            self.first_failure(value),
            "live.fixedState.frontCounterClockwise")

    def test_ordered_mrt_slot_is_required(self) -> None:
        value = complete_observation()
        value["renderTargets"][4]["viewFormat"] = 29
        value["renderTargets"][3]["viewFormat"] = 29
        self.assertEqual(self.first_failure(value), "live.rtv3.viewFormat")

    def test_all_six_sampler_slots_are_required(self) -> None:
        value = complete_observation()
        value["samplers"] = value["samplers"][:-1]
        self.assertEqual(self.first_failure(value), "live.samplerSlots.exact")

    def test_authenticated_actual_draw_is_required(self) -> None:
        value = complete_observation()
        value["authentication"]["actualDrawRendererObserved"] = False
        self.assertEqual(
            self.first_failure(value),
            "live.authentication.actualDrawRendererObserved")

    def test_b4_published_value_must_match_fresh_retail_observation(self) -> None:
        value = complete_observation()
        value["publishers"]["terrainSubsurfaceObservedRetailValue"] = 2
        self.assertEqual(
            self.first_failure(value),
            "live.publishers.terrainSubsurfacePublishedMatchesObserved")

    def test_nonadmissible_runtime_path_is_a_static_blocker(self) -> None:
        blocker_keys = (
            "generativeShellIndependentlyPinnedFromD3D11Callback",
            "runtimePipelineTagCompileReflectionAndSetPassProven",
            "b0SelectedReadsFullySourcePopulated",
            "b1SelectedReadsFullySourcePopulated",
            "b2ActualParticleRecordRangeAndGeometryObserved",
            "vertexSkinStructuredResourceAuthenticated",
            "b3AllSelectedWordsTiedToOriginalMaterialAndLayout",
            "b4SelectedFrameProducerValueAuthenticated",
            "orderedMrtSlotsObserved",
            "activeSamplerSlotsObserved",
            "authenticatedObservationWriterAvailable",
            "admissibleGenerativeParticleRendererPathExists",
        )
        audit = {key: True for key in blocker_keys}
        audit["admissibleGenerativeParticleRendererPathExists"] = False
        with mock.patch.object(
                MODULE, "_validate_static", return_value=({}, audit)):
            report = MODULE.build_report(REPO, complete_observation())
        self.assertFalse(report["admitted"])
        self.assertEqual(
            report["staticAdmissionBlockers"],
            ["admissibleGenerativeParticleRendererPathExists"])

    def test_gap_names_only_current_static_blockers(self) -> None:
        audit = {
            "generativeShellIndependentlyPinnedFromD3D11Callback": True,
            "runtimePipelineTagCompileReflectionAndSetPassProven": True,
            "b0SelectedReadsFullySourcePopulated": True,
            "b1SelectedReadsFullySourcePopulated": False,
            "b2ActualParticleRecordRangeAndGeometryObserved": True,
            "vertexSkinStructuredResourceAuthenticated": True,
            "b3AllSelectedWordsTiedToOriginalMaterialAndLayout": True,
            "b4SelectedFrameProducerValueAuthenticated": True,
            "orderedMrtSlotsObserved": True,
            "activeSamplerSlotsObserved": True,
            "authenticatedObservationWriterAvailable": True,
            "admissibleGenerativeParticleRendererPathExists": True,
        }
        with mock.patch.object(
                MODULE, "_validate_static", return_value=({}, audit)):
            report = MODULE.build_report(REPO)
        gap = report["smallestRemainingSourceGap"]
        self.assertIn("b1SelectedReadsFullySourcePopulated", gap)
        self.assertNotIn("b0SelectedReadsFullySourcePopulated", gap)
        self.assertNotIn("b3AllSelectedWordsTiedToOriginalMaterialAndLayout", gap)


class B3MaterialSourceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        (self.mapping, self.material, self.draw, self.shell,
         self.runtime_material, self.compatibility_shader) = b3_source_fixture()

    def validate(self) -> dict[str, object]:
        return MODULE._validate_b3_material_contract(
            self.mapping,
            self.material,
            self.draw,
            self.shell)

    def validate_runtime_material(self) -> dict[str, object]:
        return MODULE._validate_runtime_b3_material_source(
            self.mapping,
            self.material,
            self.runtime_material,
            self.compatibility_shader)

    def test_selected_b3_has_complete_bit_exact_source_join(self) -> None:
        contract = self.validate()
        self.assertEqual(contract["usedWordCount"], 50)
        self.assertEqual(contract["mappedFieldCount"], 37)
        self.assertEqual(contract["bitExactMatches"], 50)
        self.assertEqual(contract["unmappedUsedWords"], [])
        self.assertFalse(contract["capturedPayloadUsedAtRuntime"])

    def test_mutated_field_offset_is_rejected(self) -> None:
        fields = self.mapping["constantBuffers"]["fragmentFieldMapping"]
        row = next(item for item in fields
                   if item.get("buffer") == "UnityPerMaterial" and
                   item.get("name") == "_ParallaxStrength")
        row["offsetBytes"] += 4
        with self.assertRaises(MODULE.VerificationError):
            self.validate()

    def test_mutated_scalar_is_rejected(self) -> None:
        self.material["m_SavedProperties"]["m_Floats"][
            "_ParallaxStrength"] += 0.125
        with self.assertRaises(MODULE.VerificationError):
            self.validate()

    def test_mutated_color_is_rejected(self) -> None:
        self.material["m_SavedProperties"]["m_Colors"][
            "_ParallaxColor"]["r"] += 1.0
        with self.assertRaises(MODULE.VerificationError):
            self.validate()

    def test_mutated_texture_st_is_rejected(self) -> None:
        self.material["m_SavedProperties"]["m_TexEnvs"][
            "_BaseColorMap"]["m_Scale"]["X"] = 2.0
        with self.assertRaises(MODULE.VerificationError):
            self.validate()

    def test_mutated_captured_word_is_rejected(self) -> None:
        row = next(item for item in self.draw["constantBuffers"]
                   if item.get("stage") == 4 and item.get("slot") == 3)
        row["dataHex"] = "01" + row["dataHex"][2:]
        with self.assertRaises(MODULE.VerificationError):
            self.validate()

    def test_march_count_must_remain_uint(self) -> None:
        self.shell = self.shell.replace(
            "uint _ParallaxMarchNum : packoffset(c24.x);",
            "float _ParallaxMarchNum : packoffset(c24.x);")
        with self.assertRaises(MODULE.VerificationError):
            self.validate()

    def test_generated_runtime_material_matches_original_b3_overrides(self) -> None:
        contract = self.validate_runtime_material()
        self.assertEqual(contract["selectedB3OverrideCount"], 9)
        self.assertTrue(contract["allEffectiveOverridesMatchOriginalMaterial"])
        self.assertFalse(contract["capturedPayloadUsedAtRuntime"])

    def test_mutated_generated_runtime_material_is_rejected(self) -> None:
        self.runtime_material = self.runtime_material.replace(
            "- _ParallaxStrength: 0.096",
            "- _ParallaxStrength: 0.5")
        with self.assertRaises(MODULE.VerificationError):
            self.validate_runtime_material()


class RepositoryGenerativeRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo = HERE.parents[1]
        root = repo / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
        cls.shell = (root / "Shaders/Diagnostics/EndfieldEndminfM27GenerativeExactAbiShell.shader").read_text(
            encoding="utf-8")
        cls.packet_shell = (root / "Shaders/Diagnostics/EndfieldEndminfM27ExactAbiShell.shader").read_text(
            encoding="utf-8")
        cls.runtime = (root / "Runtime/Rendering/EndfieldRecoveredEndminfM27GenerativeExactRuntime.cs").read_text(
            encoding="utf-8")
        cls.frame = (root / "Runtime/Rendering/EndfieldRecoveredDeferredGBufferFrame.cs").read_text(
            encoding="utf-8")
        cls.pipeline = (root / "Runtime/Rendering/HGCompatRenderPipeline.cs").read_text(
            encoding="utf-8")
        cls.terrain = (root / "Runtime/Rendering/EndfieldRecoveredTerrainSubsurfaceConstants.cs").read_text(
            encoding="utf-8")
        cls.observer = (root / "Editor/CharacterRecovery/EndfieldM27ShellHashCapture.cs").read_text(
            encoding="utf-8")
        cls.registry = (
            repo /
            "unity_endfield_graph_shader_lab/tools/original_dxbc_exact/"
            "M27SubstitutionRegistry.h"
        ).read_text(encoding="utf-8")

    def test_generative_runtime_has_no_packet_payload_dependency(self) -> None:
        for forbidden in (
            "EndfieldRecoveredM27ExactCaptureData",
            "CreateConstantBufferValues",
            "IssuePluginEvent",
            "CreateExpandedMesh",
        ):
            self.assertNotIn(forbidden, self.runtime)

    def test_source_texture_and_named_cbuffer_contract(self) -> None:
        for declaration in (
            "_BaseColorMap : register(t0)",
            "_NormalMap : register(t1)",
            "_MROMap : register(t2)",
            "_ParallaxMap : register(t3)",
            "_ParallaxMaskMap : register(t4)",
            "_ParallaxNoiseMap : register(t5)",
            "StructuredBuffer<float4> _VertexSkinMatrices : register(t0)",
            "cbuffer _TransformVariables : register(b0)",
            "cbuffer ShaderVariablesGlobal : register(b1)",
            "cbuffer UnityPerDraw : register(b2)",
            "cbuffer UnityPerMaterial : register(b3)",
            "cbuffer _TerrainSubsurfaceConstants : register(b4)",
        ):
            self.assertIn(declaration, self.shell)

    def test_immutable_packet_shell_is_separate_and_unchanged(self) -> None:
        self.assertIn("float4 _M27CB0[82]", self.packet_shell)
        self.assertIn("float4 _M27CB4[1]", self.packet_shell)
        self.assertNotIn(
            "cbuffer _TransformVariables : register(b0)",
            self.packet_shell)

    def test_generative_shell_retains_all_retail_texture_slots(self) -> None:
        self.assertIn("_ParallaxMaskMap : register(t4)", self.shell)
        self.assertIn("_ParallaxNoiseMap : register(t5)", self.shell)
        self.assertIn("sampler_ParallaxMaskMap : register(s4)", self.shell)
        self.assertIn("sampler_ParallaxNoiseMap : register(s5)", self.shell)
        self.assertIn("Retail PS DXBC declares and reads all six slots", self.shell)
        self.assertNotIn("_M27CarrierT", self.shell)
        for slot in range(6):
            self.assertIn(f"register(s{slot})", self.shell)

    def test_generative_draw_requires_authenticated_substitution(self) -> None:
        self.assertIn("bool compilerSubstitutionReady", self.runtime)
        self.assertIn("if (!compilerSubstitutionReady)", self.runtime)
        self.assertIn(
            "endminfM27Material,\n                                    false,",
            self.frame)

    def test_b0_readiness_and_b3_material_reach_the_exact_draw(self) -> None:
        connections = MODULE._validate_runtime_source_connections(
            self.pipeline,
            self.frame)
        self.assertTrue(connections["b0ReadinessReachesExactDraw"])
        self.assertTrue(connections["b3RetainedMaterialReachesExactShell"])

    def test_disconnected_b0_readiness_is_rejected(self) -> None:
        disconnected = self.frame.replace(
            "transformVariablesM27SourceReady,\n"
            "                                    shaderVariablesGlobal,",
            "false,\n"
            "                                    shaderVariablesGlobal,",
            1)
        connections = MODULE._validate_runtime_source_connections(
            self.pipeline,
            disconnected)
        self.assertFalse(connections["b0ReadinessReachesExactDraw"])

    def test_disconnected_b3_source_material_is_rejected(self) -> None:
        disconnected = self.frame.replace(
            "sourceMaterial,\n"
            "                            endminfM27Material,",
            "endminfM27Material,\n"
            "                            endminfM27Material,",
            1)
        connections = MODULE._validate_runtime_source_connections(
            self.pipeline,
            disconnected)
        self.assertFalse(connections["b3RetainedMaterialReachesExactShell"])

    def test_live_draw_fixed_state_contract_is_present(self) -> None:
        for state in ("ZTest GEqual", "ZWrite On", "Cull Back"):
            self.assertIn(state, self.shell)
        self.assertIn("command.EnableScissorRect", self.frame)
        self.assertIn("command.DisableScissorRect", self.frame)

    def test_b4_cannot_be_satisfied_by_material_default(self) -> None:
        self.assertNotIn(
            "_TerrainSubsurfaceProfileInt (\"\", Integer)",
            self.shell)
        self.assertIn(
            "incomplete captures and an empty lab registry",
            self.terrain)
        self.assertIn(
            "RequiredSelectedFrameProvenanceSchema",
            self.runtime)
        self.assertIn(
            "false,\n                                        false,\n                                        -1,",
            self.frame)

    def test_raw_shell_observer_owns_fresh_epoch_before_counter_baseline(self) -> None:
        self.assertIn("RunGenerativeObservation", self.observer)
        self.assertIn("Native.SetM27SubstitutionArmed(0)", self.observer)
        disarm = self.observer.index("Native.SetM27ObservationArmed(0)")
        baseline = self.observer.index(
            "uint callbacksBefore = Native.GetCallbackCount()")
        arm = self.observer.index("Native.SetM27ObservationArmed(1)")
        self.assertLess(disarm, arm)
        self.assertLess(arm, baseline)
        self.assertIn("newObservations", self.observer)
        self.assertIn('value.textureSlotMask == "0x0000003f"', self.observer)
        self.assertIn('value.samplerSlotMask == "0x0000003f"', self.observer)

    def test_generative_shell_pin_is_compiler_only_and_stage_hash_exact(self) -> None:
        self.assertIn("RunGenerativePinValidation", self.observer)
        self.assertIn(
            '"endfield.endminf-m27-generative-shell-pin.v1"',
            self.observer,
        )
        self.assertIn(
            "vertexSwapsAfter > vertexSwapsBefore",
            self.observer,
        )
        self.assertIn(
            "pixelSwapsAfter > pixelSwapsBefore",
            self.observer,
        )
        self.assertIn(
            "0x6b, 0x87, 0xd2, 0xcb, 0x5f, 0x1d, 0x92, 0xdd",
            self.registry,
        )
        self.assertIn(
            "0x0a, 0xd3, 0x80, 0x94, 0x9c, 0x0e, 0x8e, 0xda",
            self.registry,
        )
        self.assertIn(
            "it does not authorize draw submission or captured packet data",
            self.registry,
        )


if __name__ == "__main__":
    unittest.main()
