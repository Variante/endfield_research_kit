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
        "vertexSkinningControl": {
            "observedFromActualDraw": True,
            "synchronizedDrawId": "camera:frame:draw",
            "constantBufferSlot": MODULE.VERTEX_SKIN_CB_SLOT,
            "recordIndex": MODULE.VERTEX_SKIN_RECORD_INDEX,
            "recordStrideFloat4": MODULE.VERTEX_SKIN_RECORD_STRIDE_FLOAT4,
            "flagRegisterOffset": MODULE.VERTEX_SKIN_FLAG_REGISTER_OFFSET,
            "flagLane": MODULE.VERTEX_SKIN_FLAG_LANE,
            "flagMask": MODULE.VERTEX_SKIN_FLAG_MASK,
            "flagRaw": 0,
            "skinBranchActive": False,
            "sourceMeshSkinRows": 0,
        },
        "vertexResources": [
            {
                "slot": 0,
                "observedFromActualDraw": True,
                "synchronizedDrawId": "camera:frame:draw",
                "bound": True,
                "kind": "StructuredBuffer",
                "logicalName": "_VertexSkinMatrices",
                "objectId": 1234,
                "viewId": 5678,
                "descriptorHash": 9012,
                "byteSize": MODULE.VERTEX_SKIN_BUFFER_BYTES,
                "viewDimension": MODULE.VERTEX_SKIN_VIEW_DIMENSION,
                "bindFlags": MODULE.VERTEX_SKIN_BIND_FLAGS,
                "miscFlags": MODULE.VERTEX_SKIN_MISC_FLAGS,
                "stride": 16,
                "viewFirstElement": 0,
                "viewNumElements": MODULE.VERTEX_SKIN_BUFFER_ELEMENTS,
                "payloadBytes": MODULE.VERTEX_SKIN_BUFFER_BYTES,
                "payloadSha256": "66" * 32,
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

    def test_active_skin_bit_is_rejected_before_t0_outcome_admission(self) -> None:
        value = complete_observation()
        value["vertexSkinningControl"]["flagRaw"] = MODULE.VERTEX_SKIN_FLAG_MASK
        value["vertexSkinningControl"]["skinBranchActive"] = True
        self.assertEqual(
            self.first_failure(value),
            "live.vertexSkinningControl.skinFlagClear")

    def test_fabricated_identity_skin_buffer_is_rejected(self) -> None:
        value = complete_observation()
        value["vertexResources"][0].update({
            "byteSize": 16,
            "viewNumElements": 1,
            "payloadBytes": 16,
        })
        self.assertEqual(self.first_failure(value), "live.vertex.t0.byteSize")

    def test_explicit_unbound_skin_resource_is_accepted(self) -> None:
        value = complete_observation()
        value["vertexResources"] = [{
            "slot": 0,
            "observedFromActualDraw": True,
            "synchronizedDrawId": "camera:frame:draw",
            "bound": False,
            "objectId": 0,
            "viewId": 0,
        }]
        self.assert_complete(value)

    def test_bound_skin_resource_requires_payload_hash(self) -> None:
        value = complete_observation()
        del value["vertexResources"][0]["payloadSha256"]
        self.assertEqual(
            self.first_failure(value), "live.vertex.t0.payloadSha256")

    def test_bound_skin_resource_requires_complete_descriptor(self) -> None:
        value = complete_observation()
        del value["vertexResources"][0]["miscFlags"]
        self.assertEqual(
            self.first_failure(value), "live.vertex.t0.miscFlags")

    def test_nonadmissible_runtime_path_is_a_static_blocker(self) -> None:
        blocker_keys = (
            "generativeShellIndependentlyPinnedFromD3D11Callback",
            "runtimePipelineTagCompileReflectionAndSetPassProven",
            "b0SelectedReadsFullySourcePopulated",
            "b1SelectedReadsFullySourcePopulated",
            "b2ActualParticleRecordRangeAndGeometryObserved",
            "vertexSkinDrawLocalT0OutcomeAuthenticated",
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
            "vertexSkinDrawLocalT0OutcomeAuthenticated": True,
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
        cls.global_contract = (root / "Runtime/Rendering/EndfieldRecoveredShaderVariablesGlobalContract.cs").read_text(
            encoding="utf-8")
        cls.global_owner = (root / "Runtime/Rendering/EndfieldRecoveredShaderVariablesGlobal.cs").read_text(
            encoding="utf-8")
        cls.mip_bias_source = (root / "Runtime/Rendering/EndfieldRecoveredM27GlobalMipBiasSource.cs").read_text(
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

    def test_b1_partial_runtime_owners_reach_publisher_but_stay_closed(
            self) -> None:
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            self.pipeline,
            self.mip_bias_source)
        self.assertTrue(contract["sourceOwnedInputContractComplete"])
        self.assertTrue(contract["defaultRuntimeFailsClosed"])
        self.assertTrue(contract["explicitInputsReachRuntimePublisher"])
        self.assertFalse(contract["allSelectedReadsRuntimeSourcePopulated"])
        self.assertFalse(contract["capturedValuesAuthorized"])
        self.assertTrue(all(contract["readinessBits"].values()))
        self.assertTrue(all(contract["sourceEquations"].values()))
        self.assertEqual(
            contract["populatedSelectedReads"],
            ["c0.zw", "c4.w", "c26.xy", "c27.y", "c103.xyzw"],
        )
        self.assertFalse(contract["runtimeReadConnections"]["c19.zw"])
        self.assertTrue(contract["runtimeReadConnections"]["c26.xy"])
        self.assertFalse(contract["runtimeReadConnections"]["c105.xyzw"])
        connection = contract["runtimeSourceInputConnection"]
        self.assertTrue(connection["namedSourceInputExpression"])
        self.assertTrue(connection["partialFactoryAudited"])
        self.assertTrue(connection["sourceClosedManualExposureReturnAudited"])
        self.assertTrue(connection["sourceClosedManualExposureGateAudited"])
        self.assertTrue(connection["exposureLaneAudited"])
        self.assertTrue(connection["vfxLiveLabCarrierLaneAudited"])
        self.assertTrue(connection["assignmentOrderAudited"])
        self.assertTrue(all(
            connection["uniqueAssignmentShapesAudited"].values()))
        self.assertTrue(connection["partialPipelineJoinAudited"])
        self.assertTrue(connection["partialSourceJoinAudited"])
        self.assertTrue(connection["namedSourceOwnerContractAudited"])
        self.assertTrue(
            connection["m27GlobalMipBiasSource"]["connectionAudited"])
        self.assertFalse(
            connection["m27GlobalMipBiasSource"]["resourceRequiredAtAuditTime"])
        self.assertIn(
            "retail_selected_frame_HGVFX_player_identity_unproven",
            contract["runtimeSourceSemantics"]["c103.xyzw"],
        )

    def test_b1_missing_halton_readiness_bit_invalidates_contract(self) -> None:
        mutated = self.global_contract.replace(
            "public readonly bool taaJitterReady;",
            "public readonly bool removedTaaJitterReady;",
            1)
        contract = MODULE._validate_b1_source_contract(
            mutated,
            self.global_owner,
            self.pipeline,
            self.mip_bias_source)
        self.assertFalse(contract["readinessBits"]["c19.zw"])
        self.assertFalse(contract["sourceOwnedInputContractComplete"])

    def test_b1_c26_source_schema_drift_fails_only_c26_connection(self) -> None:
        mutated = self.mip_bias_source.replace(
            MODULE.M27_MIP_BIAS_SOURCE_SCHEMA,
            "endfield.invalid-m27-mip-source.v1",
            1)
        self.assertNotEqual(mutated, self.mip_bias_source)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            self.pipeline,
            mutated)
        source = contract["runtimeSourceInputConnection"][
            "m27GlobalMipBiasSource"]
        self.assertFalse(source["checks"]["namedSourceOwner"])
        self.assertFalse(source["connectionAudited"])
        self.assertFalse(contract["runtimeReadConnections"]["c26.xy"])
        self.assertTrue(contract["runtimeReadConnections"]["c27.y"])

    def test_b1_c26_source_hash_gate_drift_fails_closed(self) -> None:
        mutated = self.mip_bias_source.replace(
            "8952d381680d3f5ad53d6376d9f7e3982fc6959c29a40926934d761a152e3e0e",
            "0" * 64,
            1)
        self.assertNotEqual(mutated, self.mip_bias_source)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            self.pipeline,
            mutated)
        source = contract["runtimeSourceInputConnection"][
            "m27GlobalMipBiasSource"]
        self.assertFalse(source["checks"]["hashIdentityGate"])
        self.assertFalse(contract["runtimeReadConnections"]["c26.xy"])

    def test_b1_c26_authority_gate_drift_fails_closed(self) -> None:
        mutated = self.mip_bias_source.replace(
            "payload.presentationAuthority)",
            "false)",
            1)
        self.assertNotEqual(mutated, self.mip_bias_source)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            self.pipeline,
            mutated)
        source = contract["runtimeSourceInputConnection"][
            "m27GlobalMipBiasSource"]
        self.assertFalse(source["checks"]["authorityGate"])
        self.assertFalse(contract["runtimeReadConnections"]["c26.xy"])

    def test_b1_c26_pipeline_overlay_bypass_fails_closed(self) -> None:
        mutated = self.pipeline.replace(
            "m27SourceInputs.WithPhysicalCameraGlobalMipBias(",
            "m27SourceInputs.WithUnauditedGlobalMipBias(",
            1)
        self.assertNotEqual(mutated, self.pipeline)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        source = contract["runtimeSourceInputConnection"][
            "m27GlobalMipBiasSource"]
        self.assertFalse(source["checks"]["exactTwoStageAssignment"])
        self.assertFalse(contract["runtimeReadConnections"]["c26.xy"])

    def test_b1_c26_overlay_must_preserve_other_source_lanes(self) -> None:
        mutated = self.global_contract.replace(
            "                    vfxPlayerPosition,\n"
            "                    vfxClockSeconds,\n"
            "                    vfxParams0Ready,\n"
            "                    vfxParams2,",
            "                    Vector3.zero,\n"
            "                    vfxClockSeconds,\n"
            "                    vfxParams0Ready,\n"
            "                    vfxParams2,",
            1)
        self.assertNotEqual(mutated, self.global_contract)
        contract = MODULE._validate_b1_source_contract(
            mutated,
            self.global_owner,
            self.pipeline,
            self.mip_bias_source)
        source = contract["runtimeSourceInputConnection"][
            "m27GlobalMipBiasSource"]
        self.assertFalse(source["checks"]["overlayPreservesOtherSources"])
        self.assertFalse(contract["runtimeReadConnections"]["c26.xy"])

    def test_b1_default_runtime_input_cannot_claim_source_owner(self) -> None:
        mutated = self.pipeline.replace(
            "                                    m27SourceInputs,\n",
            "                                    default(\n"
            "                                        EndfieldRecoveredShaderVariablesGlobalContract.M27SourceInputs),\n",
            1)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertEqual(connection["argumentCount"], 8)
        self.assertTrue(connection["inlineDefaultRejected"])
        self.assertFalse(connection["namedSourceOwnerContractAudited"])
        self.assertFalse(contract["explicitInputsReachRuntimePublisher"])
        self.assertFalse(contract["allSelectedReadsRuntimeSourcePopulated"])

    def test_b1_hardcoded_runtime_input_cannot_claim_source_owner(self) -> None:
        constructor = (
            "new EndfieldRecoveredShaderVariablesGlobalContract.M27SourceInputs("
            "true, true, Vector4.zero, true, -1.0f, true, 1.0f, true, "
            "Vector3.zero, 0.0f, true, Vector4.zero, true)")
        mutated = self.pipeline.replace(
            "                                    m27SourceInputs,\n",
            f"                                    {constructor},\n",
            1)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertEqual(connection["argumentCount"], 8)
        self.assertTrue(connection["inlineConstructorRejected"])
        self.assertFalse(connection["namedSourceOwnerContractAudited"])
        self.assertFalse(contract["explicitInputsReachRuntimePublisher"])
        self.assertFalse(contract["allSelectedReadsRuntimeSourcePopulated"])

    def test_b1_named_but_unaudited_source_owner_stays_closed(self) -> None:
        mutated = self.pipeline.replace(
            "                                    m27SourceInputs,\n",
            "                                    recoveredM27ShaderVariablesSourceOwner.CurrentM27SourceInputs,\n",
            1)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertEqual(connection["argumentCount"], 8)
        self.assertTrue(connection["namedSourceOwnerExpression"])
        self.assertFalse(connection["namedSourceOwnerContractAudited"])
        self.assertFalse(contract["explicitInputsReachRuntimePublisher"])
        self.assertFalse(contract["allSelectedReadsRuntimeSourcePopulated"])

    def test_b1_partial_join_rejects_non_camera_exposure_source(self) -> None:
        mutated = self.pipeline.replace(
            "? liveAutoExposureState.CurrentExposure",
            "? 1.0f",
            1)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertFalse(connection["partialPipelineJoinAudited"])
        self.assertFalse(connection["partialSourceJoinAudited"])
        self.assertFalse(contract["explicitInputsReachRuntimePublisher"])
        self.assertEqual(contract["populatedSelectedReads"], [])

    def test_b1_partial_join_rejects_non_engine_vfx_clock(self) -> None:
        mutated = self.pipeline.replace(
            "? Time.time",
            "? 0.0f",
            1)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertFalse(connection["partialPipelineJoinAudited"])
        self.assertFalse(connection["partialSourceJoinAudited"])
        self.assertFalse(contract["explicitInputsReachRuntimePublisher"])
        self.assertEqual(contract["populatedSelectedReads"], [])

    def test_b1_partial_join_rejects_forced_vfx_readiness(self) -> None:
        mutated = self.pipeline.replace(
            "            bool recoveredVFXParams0Ready =\n"
            "                recoveredVFXPlayerCenterReady &&",
            "            bool recoveredVFXParams0Ready = true;\n"
            "            // rejected stale expression\n"
            "            bool ignoredRecoveredVFXParams0Ready =\n"
            "                recoveredVFXPlayerCenterReady &&",
            1)
        self.assertNotEqual(mutated, self.pipeline)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertFalse(
            connection["uniqueAssignmentShapesAudited"]
            ["recoveredVFXParams0Ready"])
        self.assertFalse(connection["vfxLiveLabCarrierLaneAudited"])
        self.assertFalse(connection["partialSourceJoinAudited"])

    def test_b1_partial_join_rejects_intervening_position_overwrite(self) -> None:
        mutated = self.pipeline.replace(
            "                : Vector3.zero;\n"
            "            float recoveredVFXClockSeconds",
            "                : Vector3.zero;\n"
            "            recoveredVFXPlayerPosition = Vector3.one;\n"
            "            float recoveredVFXClockSeconds",
            1)
        self.assertNotEqual(mutated, self.pipeline)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertFalse(
            connection["uniqueAssignmentShapesAudited"]
            ["recoveredVFXPlayerPosition"])
        self.assertFalse(connection["vfxLiveLabCarrierLaneAudited"])
        self.assertFalse(connection["partialSourceJoinAudited"])

    def test_b1_partial_join_rejects_diagnostic_exposure_selector(self) -> None:
        mutated = self.pipeline.replace(
            "                !recoveredLiveCharInfoAutoExposureRequested &&",
            "                recoveredLiveCharInfoAutoExposureRequested &&",
            1)
        self.assertNotEqual(mutated, self.pipeline)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertFalse(connection["exposureLaneAudited"])
        self.assertFalse(connection["partialSourceJoinAudited"])

    def test_b1_partial_join_rejects_non_source_closed_manual_gate(self) -> None:
        mutated = self.pipeline.replace(
            "                    recoveredSourceClosedManualExposureRequested);",
            "                    true);",
            1)
        self.assertNotEqual(mutated, self.pipeline)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertFalse(connection["sourceClosedManualExposureGateAudited"])
        self.assertFalse(connection["exposureLaneAudited"])
        self.assertFalse(connection["partialSourceJoinAudited"])

    def test_b1_partial_join_rejects_non_manual_state_return(self) -> None:
        mutated = self.pipeline.replace(
            "                state.AdvanceSourceClosedNeutralProfile(deltaTime);",
            "                state.Advance(deltaTime, Time.frameCount);",
            1)
        self.assertNotEqual(mutated, self.pipeline)
        contract = MODULE._validate_b1_source_contract(
            self.global_contract,
            self.global_owner,
            mutated,
            self.mip_bias_source)
        connection = contract["runtimeSourceInputConnection"]
        self.assertFalse(connection["sourceClosedManualExposureReturnAudited"])
        self.assertFalse(connection["exposureLaneAudited"])
        self.assertFalse(connection["partialSourceJoinAudited"])

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
