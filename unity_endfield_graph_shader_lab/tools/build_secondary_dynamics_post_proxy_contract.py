#!/usr/bin/env python3
"""Build the pinned PostProxyMeshUpdate native scheduling contract.

The contract closes the managed/native ABI, ordered job construction, job
payload layouts, exact generic scheduling identities, the unpatched
CalcLineNormalTangent managed-worker traversal/equations, and the generated
BurstDirectCall wrapper plus its managed-fallback equivalence and exact Burst
target.  The installed local IFix payload is joined and parsed to bound its
absence of BeyondDynamicBone targets.  The selected runtime branch and live
IFix patch state remain open; no capture samples, fitted curves, or replay data
are inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DATA_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
EVIDENCE_ROOT = LAB_ROOT / "scratch/character_recovery/secondary_dynamics_owner"
DEFAULT_OUTPUT = DATA_ROOT / "secondary_dynamics_post_proxy_contract.json"
DEFAULT_METADATA_EVIDENCE = EVIDENCE_ROOT / "post_proxy_metadata.json"
DEFAULT_NATIVE_EVIDENCE = EVIDENCE_ROOT / "post_proxy_native.json"
DEFAULT_BURST_CONTRACT = DATA_ROOT / "secondary_dynamics_burst_export_contract.json"
DEFAULT_CALC_LINE_BURST_NUMERICS = (
    DATA_ROOT / "secondary_dynamics_calc_line_burst_golden_vectors.json"
)
DEFAULT_IFIX_REPORT = DATA_ROOT / "installed_ifix_patch_state.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_LIB_BURST_SHA256 = "ee8702dd63dec2db7dc29d5bc23b8acd032f0e19a0daad5f69e6c45f9d3ceb99"
EXPECTED_METADATA_EVIDENCE_SHA256 = "d1533b659e33a2e561c444cb4aec9a929dfac355a8d3409748c009e9c277a295"
EXPECTED_NATIVE_EVIDENCE_SHA256 = "3bad91ae59e34b7abc50b5f88aafb77ea9e2c1395fba1346cc503deafb982b5d"
EXPECTED_CALC_LINE_BURST_NUMERICS_SHA256 = (
    "5d2c7ea2f80243405bc2d3dd54f5a01035cc4777e8d02c64182285331caf93a1"
)
EXPECTED_CODE_REGISTRATION = 0x18B9217D0
EXPECTED_METADATA_REGISTRATION = 0x18B921C30

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    pass


POST_PROXY = {
    "methodIndex": 384785,
    "token": "0x060004da",
    "type": "BeyondDynamicBone.VirtualMeshManager",
    "method": "PostProxyMeshUpdate",
    "startVa": 0x182F8C4A0,
    "fileOffset": 0x2F8AAA0,
    "spanBytes": 0x10B0,
    "bodySha256": "5a74ebb4a44356d4114332da8ca9c4ed183ed2e7d88216637072e0ebf151bead",
    "firstRetOffset": 0xE34,
    "throughFirstRetSha256": "842cc941559ab9c9b6c7c62092ca6a30f05ca5ad7a7ea6c29e93a92e9fbc685c",
}

STAGES = (
    {
        "order": 1,
        "job": "CreatePostProxyMeshUpdateListJob",
        "jobTypeIndex": 208231,
        "setIndexCountOffset": 0x3B8,
        "setIndexCountVa": 0x183D84160,
        "getReflectionDataOffset": 0x496,
        "getReflectionDataMethodSpec": 516826,
        "reflectionPointerSlot": 483841,
        "reflectionGenericInst": 22216,
        "schedule": {"kind": "IJobParallelFor", "batchSize": 1, "methodIndex": 401866,
                     "pointerVa": 0x1876C6DC4, "methodSpec": 517373,
                     "pointerSlot": 484362},
        "crossFrame": {"methodIndex": 384474, "pointerVa": 0x187AF4C60,
                       "methodSpec": 508694, "pointerSlot": 477087},
    },
    {
        "order": 2,
        "job": "CalcLineNormalTangentJob",
        "jobTypeIndex": 208217,
        "setIndexCountOffset": 0x765,
        "setIndexCountVa": 0x183D51420,
        "getReflectionDataOffset": 0x838,
        "getReflectionDataMethodSpec": 516819,
        "reflectionPointerSlot": 483834,
        "reflectionGenericInst": 22056,
        "schedule": {"kind": "IJobParallelForDefer", "batchSize": 8, "methodIndex": 476935,
                     "pointerVa": 0x1876C6BA8, "methodSpec": 517163,
                     "pointerSlot": 484159},
        "crossFrame": {"methodIndex": 384475, "pointerVa": 0x187AF43D0,
                       "methodSpec": 508714, "pointerSlot": 477107},
    },
    {
        "order": 3,
        "job": "WriteTransformDataJob",
        "jobTypeIndex": 208234,
        "setIndexCountOffset": 0xA1B,
        "setIndexCountVa": 0x183D77850,
        "getReflectionDataOffset": 0xAE9,
        "getReflectionDataMethodSpec": 516828,
        "reflectionPointerSlot": 483843,
        "reflectionGenericInst": 22060,
        "schedule": {"kind": "IJobParallelForDefer", "batchSize": 16, "methodIndex": 476935,
                     "pointerVa": 0x1876C6BA8, "methodSpec": 517167,
                     "pointerSlot": 484163},
        "crossFrame": {"methodIndex": 384475, "pointerVa": 0x187AF773C,
                       "methodSpec": 508718, "pointerSlot": 477111},
    },
    {
        "order": 4,
        "job": "WriteTransformLocalDataJob",
        "jobTypeIndex": 208236,
        "setIndexCountOffset": 0xCD0,
        "setIndexCountVa": 0x183D52360,
        "getReflectionDataOffset": 0xDAE,
        "getReflectionDataMethodSpec": 516829,
        "reflectionPointerSlot": 483844,
        "reflectionGenericInst": 22061,
        "schedule": {"kind": "IJobParallelForDefer", "batchSize": 32, "methodIndex": 476935,
                     "pointerVa": 0x1876C6BA8, "methodSpec": 517168,
                     "pointerSlot": 484164},
        "crossFrame": {"methodIndex": 384475, "pointerVa": 0x187AF7974,
                       "methodSpec": 508719, "pointerSlot": 477112},
    },
)

JOB_FIELDS = {
    "CreatePostProxyMeshUpdateListJob": (
        48300,
        (("teamDataArray", 229882, 0x00), ("processingCounter0", 229883, 0x10),
         ("processingList0", 229884, 0x20), ("processingCounter1", 229885, 0x30),
         ("processingList1", 229886, 0x40), ("processingCounter2", 229887, 0x50),
         ("processingList2", 229888, 0x60), ("processingCounter3", 229889, 0x70),
         ("processingList3", 229890, 0x80), ("_indexCount", 229891, 0x90)),
        0xA0,
    ),
    "CalcLineNormalTangentJob": (
        48301,
        (("jobBaseLineList", 229892, 0x00), ("teamDataArray", 229893, 0x10),
         ("parameterArray", 229894, 0x20), ("attributes", 229895, 0x30),
         ("positions", 229896, 0x40), ("rotations", 229897, 0x50),
         ("vertexLocalPositions", 229898, 0x60), ("vertexLocalRotations", 229899, 0x70),
         ("parentIndices", 229900, 0x80), ("childIndexArray", 229901, 0x90),
         ("childDataArray", 229902, 0xA0), ("baseLineFlags", 229903, 0xB0),
         ("baseLineTeamIds", 229904, 0xC0), ("baseLineStartIndices", 229905, 0xD0),
         ("baseLineDataCounts", 229906, 0xE0), ("baseLineData", 229907, 0xF0),
         ("_indexCount", 229908, 0x100)),
        0x110,
    ),
    "WriteTransformDataJob": (
        48304,
        (("jobVertexIndexList", 229927, 0x00), ("teamDataArray", 229928, 0x10),
         ("transformPositionArray", 229929, 0x20), ("transformRotationArray", 229930, 0x30),
         ("teamIds", 229931, 0x40), ("positions", 229932, 0x50),
         ("rotations", 229933, 0x60), ("vertexToTransformRotations", 229934, 0x70),
         ("_indexCount", 229935, 0x80)),
        0x90,
    ),
    "WriteTransformLocalDataJob": (
        48305,
        (("jobVertexIndexList", 229936, 0x00), ("teamDataArray", 229937, 0x10),
         ("teamIds", 229938, 0x20), ("attributes", 229939, 0x30),
         ("vertexParentIndices", 229940, 0x40), ("transformPositionArray", 229941, 0x50),
         ("transformRotationArray", 229942, 0x60), ("transformScaleArray", 229943, 0x70),
         ("transformLocalPositionArray", 229944, 0x80),
         ("transformLocalRotationArray", 229945, 0x90), ("_indexCount", 229946, 0xA0)),
        0xB0,
    ),
}

COLD_SPANS = (
    ("createList.parallelSchedule", 0x184F719AD, 183, "4719cfbfbd935abeec928b9bb13817c689d15b9d0f4ec1105e084b720c643765"),
    ("createList.managedWorkerFallback", 0x184F71A64, 90, "072931d13b5e4b4ed4bf76acb4fc573a38437c91cd7198d926fd96525f8b7b7f"),
    ("calcLine.parallelSchedule", 0x184F71B5B, 172, "ef1a37914751af65e5300ee74593270555942a13a452c2a4bb606d24655ddc95"),
    ("calcLine.managedWorkerFallback", 0x184F71C07, 90, "345d0c714243e33ef822263e1ea3abdf2032de0c41e5421ee1879adbd3ed95c8"),
    ("writeWorldAndLocal.directSchedule", 0x184F71CF9, 709, "6282f4c057e37c867e134ab63218d4be2e390e0b274e93935641a7a7c8138460"),
    ("writeWorld.managedWorkerFallback", 0x184F71FBE, 166, "3b9a21353d270175e9cb543bcc950961d2d37d82b67cc9a6f0eb206c2ad92d71"),
    ("writeLocal.parallelSchedule", 0x184F720F2, 182, "5b7ef19b3b21bc5435d2bf143a029a754e584a7c437bd2fe67cd3a2359a8df13"),
    ("writeLocal.managedWorkerFallback", 0x184F721A8, 90, "93473a002a7338a223d7d2e8a8e453df5b9b04a0df3f764570442a0d636a29e4"),
)

FALLBACK_CALLS = (
    ("createList", 0x184F71AAE, 0x18674EEC0),
    ("calcLine", 0x184F71C54, 0x186746134),
    ("writeWorld", 0x184F720B1, 0x186754B30),
    ("writeLocal", 0x184F721F5, 0x186755CA8),
)

WORKER_TARGETS = (
    (384830, "CreatePostProxyMeshUpdateListKernel", 0x18674E9C4),
    (384831, "CreatePostProxyMeshUpdateListRangeKernel", 0x18674EB40),
    (384832, "CreatePostProxyMeshUpdateListKernel$BurstManaged", 0x186743868),
    (384833, "CreatePostProxyMeshUpdateListRangeKernel$BurstManaged", 0x18674EA88),
    (384854, "CalcLineNormalTangentKernel", 0x1867456E4),
    (384855, "CalcLineNormalTangentRangeKernel", 0x18674580C),
    (384856, "CalcLineNormalTangentKernel$BurstManaged", 0x186744FB0),
    (384857, "CalcLineNormalTangentRangeKernel$BurstManaged", 0x186741214),
)

CALC_LINE = {
    "methodIndex": 384856,
    "method": "CalcLineNormalTangentKernel$BurstManaged",
    "startVa": 0x186744FB0,
    "spanBytes": 1844,
    "bodySha256": "9868eee8cddc41aae648fead87025f7a53b4d158dca963865dfd2126a0f9a829",
    "throughRetBytes": 0x72B,
    "throughRetSha256": "3fd25c103794771a322506815060f2203fc2ef5d4830252122bd4b654c76df31",
}

CALC_LINE_DIRECT_CALL = {
    "kernelMethodIndex": 384854,
    "kernelStartVa": 0x1867456E4,
    "kernelSpanBytes": 0x128,
    "kernelBodySha256": "05af0def52b33451b7424296e8325c8f4819c7e27a0b64bfc1207b359431ba83",
    "getFunctionPointerDiscardMethodIndex": 384862,
    "getFunctionPointerDiscardStartVa": 0x186746378,
    "getFunctionPointerDiscardSpanBytes": 0x104,
    "getFunctionPointerDiscardBodySha256": "e01f62edf47a397a23be09da38d792201e7d14ebc2af0a2307786cb0b43cccab",
    "getFunctionPointerMethodIndex": 384863,
    "getFunctionPointerStartVa": 0x18674647C,
    "getFunctionPointerSpanBytes": 0x54,
    "getFunctionPointerBodySha256": "388ecee8eb261eb2f581b522a2bcb5d7ff521b9d7ad0d198149a345ced0eff33",
    "invokeMethodIndex": 384867,
    "invokeStartVa": 0x1867464D0,
    "invokeSpanBytes": 0x220,
    "invokeBodySha256": "3166eb9d2d86a50eb31524927b652850ffcdc6a22b5b6edd92db200959392de7",
    "fallbackStartVa": 0x186740ADC,
    "fallbackSpanBytes": 0x738,
    "fallbackBodySha256": "0a7045f6a467730b13d1b7f540cf87f258f1dd3e6f5c74bfd00af0e1d525279e",
    "fallbackThroughRetBytes": 0x731,
    "fallbackThroughRetSha256": "b1424aff822792c251bd1176f13d30a274612c86c11a0c5f19c471b363f8feeb",
}

CREATE_LIST_DIRECT_CALL = {
    "kernelMethodIndex": 384830,
    "kernelStartVa": 0x18674E9C4,
    "kernelSpanBytes": 0xC4,
    "kernelBodySha256": "aa4787dc1a16922c3df8ee11c9bd0af329558bb294115e7fe08576a7a131348b",
    "invokeMethodIndex": 384843,
    "invokeStartVa": 0x18674F118,
    "invokeSpanBytes": 0x148,
    "invokeBodySha256": "d2ddb8ea79313aad24069c05bb1226291aa68da0764874292d0fef30a5c1305d",
    "getFunctionPointerMethodIndex": 384839,
    "getFunctionPointerStartVa": 0x18674F0C4,
    "getFunctionPointerSpanBytes": 0x54,
    "getFunctionPointerBodySha256": "2da1808fbf5b4a8c322c0bdecdc727e2d755932e36010ba21a36a7defcddf897",
    "managedFallbackMethodIndex": 384832,
    "managedFallbackStartVa": 0x186743868,
    "managedFallbackSpanBytes": 0xCE4,
    "managedFallbackBodySha256": "02a0d53fed888f05f966dbe2250f59e4f2722d0cfac3928e7a2b268d39bb4bde",
}

BURST_RUNTIME_SELECTION = {
    "burstCompilerCctorMethodIndex": 489290,
    "burstCompilerCctorStartVa": 0x18495EE80,
    "burstCompilerCctorSpanBytes": 0x120,
    "burstCompilerCctorBodySha256": "efc41f828e4d160cfb3991fdcaa944cfa50e7ea7e6d8d45c944baed1cebcb41d",
    "optionsCtorMethodIndex": 489303,
    "optionsCtorStartVa": 0x18495EFA0,
    "optionsCtorSpanBytes": 0x40,
    "optionsCtorBodySha256": "b531f3a726f3a1da861a706522bc611a2a3e9894034278e693d050d2d057a64d",
    "optionsSetEnabledMethodIndex": 489306,
    "optionsSetEnabledStartVa": 0x18495EFE0,
    "optionsSetEnabledSpanBytes": 0xF0,
    "optionsSetEnabledBodySha256": "963b0bbb979e44b8caf98e75c9f618d261327f5752446fa4a9165e5b0cb68ac7",
    "optionsCctorMethodIndex": 489314,
    "optionsCctorStartVa": 0x1841A6310,
    "optionsCctorSpanBytes": 0xF0,
    "optionsCctorBodySha256": "a5b06c77510b5b7001e2d5ab9b6152899960ba2a10ffb1d63a3b9ccdc58f8532",
    "optionsCctorColdStartVa": 0x1852725C6,
    "optionsCctorColdSpanBytes": 0x58,
    "optionsCctorColdSha256": "9fed79435b6cdada18438bf51f32864c7aa7a912782d93c14f203ca533a30951",
    "checkSecondaryMethodIndex": 489315,
    "checkSecondaryStartVa": 0x1812081B0,
    "checkSecondaryThroughRetBytes": 3,
    "checkSecondaryThroughRetSha256": "01cb47d078b4841b8408ec4fe278efa83115c6f6e101972987507d2b2b57dcf0",
    "helperIsBurstEnabledMethodIndex": 489292,
    "helperIsBurstEnabledStartVa": 0x18B15C238,
    "helperIsBurstEnabledSpanBytes": 0x3C,
    "helperIsBurstEnabledBodySha256": "a6bdfecd92d02577f8f9b00f92d0a4466df234dce32751e79ed051f9aa955017",
    "helperCctorMethodIndex": 489295,
    "helperCctorStartVa": 0x183FAEB30,
    "helperCctorThroughRetBytes": 0xBB,
    "helperCctorThroughRetSha256": "e60792092fab6f83a9c61aea1d93f6cfed7d71119046ce92a749cc070da235ff",
    "helperIsCompiledMethodIndex": 489294,
    "helperIsCompiledStartVa": 0x183FB0A20,
    "helperIsCompiledThroughRetBytes": 0x58,
    "helperIsCompiledThroughRetSha256": "9e770066dac653966dcdafd1afefe2dfbcd7225903069fe10cee0aced70b18e4",
    "compileAsyncMethodIndex": 402096,
    "compileAsyncStartVa": 0x183FB1010,
    "compileAsyncSpanBytes": 0x30,
    "compileAsyncBodySha256": "b1fb4b136d839734f68531bd41b891044bccfb1dee7dd7acd505180af9626b98",
    "getAsyncMethodIndex": 402097,
    "getAsyncStartVa": 0x183FB0FD0,
    "getAsyncSpanBytes": 0x40,
    "getAsyncBodySha256": "baa29c1b316ca0b19e357d5c2706ee037fc5869dbdd673818ffea2b0a16f7254",
    "directCallCctorMethodIndex": 384866,
    "directCallCctorStartVa": 0x184D1D370,
    "directCallCctorSpanBytes": 0x10,
    "directCallCctorBodySha256": "63dd03799ed9bf5e7b69310d767e063a455475311552dfd822d46c24f2760a66",
    "directCallCtorMethodIndex": 384864,
    "directCallCtorStartVa": 0x184D1D380,
    "directCallCtorSpanBytes": 0x90,
    "directCallCtorBodySha256": "f58d1d860f35dd2a4f36061ff389e56cedde85f4a81317ca1c1ad6f2c362e0e6",
    "getIlppSpanBytes": 0x30,
    "getIlppBodySha256": "9bee5e8ec8df54600135338af3dcfb9bd658c504be3b76c5dd27f1093c44cc24",
}

IFIX_WRAPPER_BOOTSTRAP = {
    "dynamicWrapperTypeDefinitionIndex": 48629,
    "wrapperArrayFieldIndex": 231395,
    "wrapperArrayFieldName": "wrapperArray",
    "wrapperArrayCctorMethodIndex": 387376,
    "wrapperArrayCctorStartVa": 0x184D37BF0,
    "wrapperArrayCctorThroughRetBytes": 0x60,
    "wrapperArrayCctorThroughRetSha256": "5cb6d4ce87529c8c6f1fa7eac874f3ead4739a13fcb266e47994d36a9009ede4",
    "getPatchMethodIndex": 387383,
    "getPatchStartVa": 0x185396738,
    "getPatchSpanBytes": 0x64,
    "getPatchBodySha256": "db307c30bca973a0267cca2f59294c3fc59aa0bf6959b4d74eb3e7aa760f10c0",
    "isPatchedMethodIndex": 387384,
    "isPatchedStartVa": 0x182F95A30,
    "isPatchedSpanBytes": 0x90,
    "isPatchedBodySha256": "313d367c6b4d2777c831c0ef2280273536e55dbec46540925b997fc1b46f805c",
    "initWrapperArrayMethodIndex": 387387,
}

# The parameter declaration and pointee identities come from global metadata
# plus MetadataRegistration.types.  Strides/access are then independently
# demonstrated by the pinned worker body's address arithmetic.
CALC_LINE_PARAMETERS = (
    ("jobBaseLineList", 117350, "System.Int32", 0x08, None, 4, "read"),
    ("teamDataArray", 117510, "BeyondDynamicBone.TeamManager+TeamData", 0x11, 48233, 0x1D0, "read"),
    ("parameterArray", 117243, "BeyondDynamicBone.ClothParameters", 0x11, 48002, 0x328, "read"),
    ("attributes", 117438, "BeyondDynamicBone.VertexAttribute", 0x11, 48621, 1, "read"),
    ("positions", 117455, "Unity.Mathematics.double3", 0x11, 57201, 24, "read"),
    ("rotations", 117463, "Unity.Mathematics.quaternion", 0x11, 57247, 16, "readWrite"),
    ("vertexLocalPositions", 117458, "Unity.Mathematics.float3", 0x11, 57216, 12, "read"),
    ("vertexLocalRotations", 117463, "Unity.Mathematics.quaternion", 0x11, 57247, 16, "read"),
    ("parentIndices", 117350, "System.Int32", 0x08, None, 4, "unusedByMethod384856"),
    ("childIndexArray", 117409, "System.UInt32", 0x09, None, 4, "read"),
    ("childDataArray", 117406, "System.UInt16", 0x07, None, 2, "read"),
    ("baseLineFlags", 117259, "BeyondDynamicBone.ExBitFlag8", 0x11, 48538, 1, "readEntryGateThenIncomingStackSlotReused"),
    ("baseLineTeamIds", 117347, "System.Int16", 0x06, None, 2, "read"),
    ("baseLineStartIndices", 117406, "System.UInt16", 0x07, None, 2, "read"),
    ("baseLineDataCounts", 117406, "System.UInt16", 0x07, None, 2, "read"),
    ("baseLineData", 117406, "System.UInt16", 0x07, None, 2, "read"),
    ("index", 148327, "System.Int32", 0x08, None, 4, "scalar"),
)

CALC_LINE_RELEVANT_FIELDS = (
    ("BeyondDynamicBone.TeamManager+TeamData", 48233, "negativeScaleDirection", 229659, 171871, 0x68),
    ("BeyondDynamicBone.TeamManager+TeamData", 48233, "negativeScaleQuaternionValue", 229662, 171886, 0x88),
    ("BeyondDynamicBone.TeamManager+TeamData", 48233, "proxyCommonChunk", 229683, 136096, 0x124),
    ("BeyondDynamicBone.TeamManager+TeamData", 48233, "proxyVertexChildDataChunk", 229684, 136096, 0x12C),
    ("BeyondDynamicBone.TeamManager+TeamData", 48233, "baseLineDataChunk", 229691, 136096, 0x164),
    ("BeyondDynamicBone.ClothParameters", 48002, "rotationalInterpolation", 228432, 163868, 0xA0),
    ("BeyondDynamicBone.ClothParameters", 48002, "rootRotation", 228433, 163868, 0xA4),
    ("BeyondDynamicBone.DataChunk", 48536, "startIndex", 230870, 148333, 0x00),
    ("BeyondDynamicBone.DataChunk", 48536, "dataLength", 230871, 148333, 0x04),
)

CALC_LINE_TYPE_SIZES = (
    ("BeyondDynamicBone.TeamManager+TeamData", 48233, 0x1D0),
    ("BeyondDynamicBone.ClothParameters", 48002, 0x328),
    ("BeyondDynamicBone.VertexAttribute", 48621, 1),
    ("BeyondDynamicBone.ExBitFlag8", 48538, 1),
    ("BeyondDynamicBone.DataChunk", 48536, 8),
    ("Unity.Mathematics.double3", 57201, 24),
    ("Unity.Mathematics.float3", 57216, 12),
    ("Unity.Mathematics.float4", 57221, 16),
    ("Unity.Mathematics.quaternion", 57247, 16),
)

# These paired call sites were decoded offline.  The builder pins both byte
# streams and every rel32 target, so the published comparison fails closed if
# either emitted body changes.  The first offset is method 384856; the second
# is the generated DirectCall managed-fallback body at 0x186740adc.
CALC_LINE_EQUIVALENT_CALLS = (
    ("staticInitialization", 0x180035ED0, 0x085, 0x085),
    ("teamIsEnabled", 0x1837EBD60, 0x152, 0x152),
    ("teamIsCullingInvisible", 0x18673DB7C, 0x168, 0x168),
    ("float3ComponentMultiply", 0x184D886A0, 0x356, 0x35C),
    ("quaternionRotateFloat3", 0x182FACF20, 0x379, 0x37F),
    ("float3ToDouble3", 0x18415F9A0, 0x39E, 0x3A4),
    ("double3Add", 0x185F00D7C, 0x3D6, 0x3DF),
    ("runtimeClassInit", 0x1800036A0, 0x402, 0x40B),
    ("vertexAttributeMoveBit", 0x18352B760, 0x40E, 0x417),
    ("float3ToDouble3", 0x18415F9A0, 0x42F, 0x438),
    ("double3Add", 0x185F00D7C, 0x460, 0x469),
    ("double3Subtract", 0x185F00F40, 0x4A9, 0x4B2),
    ("double3Add", 0x185F00D7C, 0x4E4, 0x4ED),
    ("float3ToDouble3", 0x18415F9A0, 0x512, 0x51B),
    ("fromToRotation", 0x1866AEF20, 0x548, 0x54E),
    ("float4ComponentMultiply", 0x1830E8750, 0x597, 0x5A0),
    ("quaternionHamiltonProduct", 0x1830E8510, 0x5BD, 0x5C6),
    ("quaternionHamiltonProduct", 0x1830E8510, 0x5EC, 0x5F5),
    ("runtimeClassInit", 0x1800036A0, 0x633, 0x63C),
    ("vertexAttributeMoveBit", 0x18352B760, 0x63F, 0x648),
    ("fromToRotation", 0x1866AEF20, 0x67E, 0x684),
    ("quaternionHamiltonProduct", 0x1830E8510, 0x69B, 0x6A1),
)

CALC_LINE_HELPER_SPANS = (
    ("float3ComponentMultiply", 0x184D886A0, 0x31, "a2d2e46ffbeb6198dff49c5c0a7e4da77d367c0ab09fa9e9cc8dd8092c1e5084"),
    ("quaternionRotateFloat3", 0x182FACF20, 0x275, "03a1a80c2ead230146ab4c2988e047bad9026de6272f4481370b166e211eae16"),
    ("float3ToDouble3", 0x18415F9A0, 0x3B, "bc37b4cddfcb15deb3c2d8d3521eb30faf5bbd7c43102c1184a703f4cb4846f4"),
    ("double3Add", 0x185F00D7C, 0x38, "355bec682557efb3d846bdb78aa4e2f82fd6d1478b92dea4340a1cf025b86ceb"),
    ("vertexAttributeMoveBitHotPath", 0x18352B760, 0x2E, "2bf36191ae94ce2bae81b475e3902855e98eb859aae26d87d384161aacb79822"),
    ("VertexAttribute.IsMove", 0x1866FF05C, 0x46, "6786da000a4eeed36be726cdd30026b208a4b44008203673bf85a5d9500d70cd"),
    ("double3Subtract", 0x185F00F40, 0x38, "0a732489946664f570db7628b2e73c0f3ef7fc6e3363c25368267cff29b48200"),
    ("MathUtility.FromToRotation", 0x1866AEF20, 0x307, "64bfab4167c7dacee770dc9f680ba205e6a8f277584d0ce917b1b39870883a0f"),
    ("float4ComponentMultiply", 0x1830E8750, 0x41, "7cf87e0301a78d9cce4f3df394313d4e093798c46d0c6ac2c55024e407f6f232"),
    ("quaternionHamiltonProduct", 0x1830E8510, 0x238, "e774acaece8257a4bdb8df10ad22b9a0c60995e2b8f4e9a1cfebbb761a70aab6"),
)


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _helpers() -> tuple[Any, Any]:
    root = REPO_ROOT / "tools/endfield-il2cpp"
    return (_load("post_proxy_metadata", root / "catalog_option_flow_metadata.py"),
            _load("post_proxy_native", root / "map_body_targets_to_gameassembly.py"))


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _source(path: Path, expected_hash: str) -> dict[str, Any]:
    actual = _sha(path)
    if actual != expected_hash:
        raise ContractError(f"source drift: {_repo_path(path)} {actual} != {expected_hash}")
    return {"repoPath": _repo_path(path), "size": path.stat().st_size, "sha256": actual}


def _metadata_usage_source(pe: Any, va: int, expected_kind: int) -> int:
    encoded = pe.u64_at_va(va)
    kind = encoded >> 29
    source_index = (encoded >> 1) & 0x0FFFFFFF
    if kind != expected_kind:
        raise ContractError(
            f"metadata usage kind drift at 0x{va:x}: {kind} != {expected_kind}"
        )
    return source_index


def _metadata_usage_type(md: Any, pe: Any, registration: dict[str, Any],
                         va: int, expected_name: str) -> dict[str, Any]:
    metadata_type_index = _metadata_usage_source(pe, va, 1)
    types_table = int(registration["types"], 16)
    type_pointer = pe.u64_at_va(types_table + metadata_type_index * 8)
    type_definition_index, type_bits = struct.unpack(
        "<QI", pe.bytes_at_va(type_pointer, 12)
    )
    if type_definition_index >= len(md.types):
        raise ContractError(f"metadata usage type is not a TypeDef at 0x{va:x}")
    actual_name = md.type_full_name(md.types[type_definition_index])
    if actual_name != expected_name:
        raise ContractError(
            f"metadata usage type drift at 0x{va:x}: {actual_name} != {expected_name}"
        )
    return {
        "slotVa": f"0x{va:x}",
        "metadataTypeIndex": metadata_type_index,
        "typeDefinitionIndex": type_definition_index,
        "typeBits": f"0x{type_bits:x}",
        "type": actual_name,
    }


def _metadata_usage_string(md: Any, pe: Any, va: int,
                           expected_value: str) -> dict[str, Any]:
    literal_index = _metadata_usage_source(pe, va, 5)
    literals = md.sections["stringLiteral"]
    data = md.sections["stringLiteralData"]
    record = literals.offset + literal_index * 8
    if record < literals.offset or record + 8 > literals.offset + literals.size:
        raise ContractError(f"metadata string literal index out of bounds at 0x{va:x}")
    length, data_index = struct.unpack_from("<II", md.buf, record)
    start = data.offset + data_index
    end = start + length
    if start < data.offset or end > data.offset + data.size:
        raise ContractError(f"metadata string literal data out of bounds at 0x{va:x}")
    value = md.buf[start:end].decode("utf-8", errors="strict")
    if value != expected_value:
        raise ContractError(
            f"metadata string literal drift at 0x{va:x}: {value!r} != {expected_value!r}"
        )
    return {"slotVa": f"0x{va:x}", "literalIndex": literal_index, "value": value}


def _validate_installed_ifix_payload(
        payload: dict[str, Any], gate: dict[str, Any],
        parsed_targets: list[dict[str, Any]]) -> dict[str, Any]:
    """Join the local installed payload without promoting it to live state.

    IFix's numeric wrapper id is not an on-disk target-table key.  Therefore
    the sound static negative proof is absence of every BeyondDynamicBone
    target from the exact parsed installed table, not a search for ``0x219``.
    """
    if payload.get("schema") != "endfield.charinfo.installed-ifix-patch-state.v1":
        raise ContractError("installed IFix report schema drift")
    source_build = payload.get("source_build") or {}
    expected_build = {
        "game_assembly": gate["gameAssembly"]["sha256"],
        "global_metadata": gate["globalMetadata"]["sha256"],
    }
    for key, expected_sha in expected_build.items():
        actual_sha = str((source_build.get(key) or {}).get("sha256") or "").lower()
        if actual_sha != expected_sha.lower():
            raise ContractError(f"installed IFix report native build drift: {key}")

    targets = payload.get("targets")
    if not isinstance(targets, list) or targets != parsed_targets:
        raise ContractError("installed IFix parsed target table differs from report")
    patch_format = payload.get("patch_format") or {}
    if patch_format.get("target_count") != len(targets):
        raise ContractError("installed IFix target count differs from parsed table")
    persistent = ((payload.get("vfs_state") or {}).get("persistent_overlay") or {})
    patch_record = persistent.get("file") or {}
    refresh = payload.get("refresh") or {}
    if (not patch_record.get("sha256") or
            refresh.get("source_patch_sha256") != patch_record.get("sha256")):
        raise ContractError("installed IFix refresh/source patch identity drift")
    if persistent.get("file_count") != 1 or persistent.get("chunk_count") != 1:
        raise ContractError("installed Persistent IFix VFS census drift")
    base = ((payload.get("vfs_state") or {}).get("base_streaming_assets") or {})
    if base.get("file_count") != 0 or base.get("chunk_count") != 0:
        raise ContractError("installed base IFix VFS census drift")

    beyond_targets = [
        row for row in targets
        if str(row.get("type") or "").startswith("BeyondDynamicBone.")
    ]
    from_to_targets = [
        row for row in beyond_targets
        if row.get("type") == "BeyondDynamicBone.MathUtility" and
        row.get("method") == "FromToRotation"
    ]
    if beyond_targets:
        raise ContractError(
            "installed IFix unexpectedly targets BeyondDynamicBone: " +
            json.dumps(beyond_targets, ensure_ascii=False, sort_keys=True)
        )
    return {
        "status": "hash_pinned_installed_local_payload_excludes_beyond_dynamic_bone",
        "installedLocalPayloadFileCount": 1,
        "parsedTargetCount": len(targets),
        "beyondDynamicBoneTargetCount": len(beyond_targets),
        "fromToRotationTargetCount": len(from_to_targets),
        "sourcePatchSha256": patch_record["sha256"],
        "sourceBuild": expected_build,
        "proof": (
            "The exact parsed target table of the only installed local IFixPatchOut "
            "payload contains no BeyondDynamicBone target. Patch id 0x219 is a "
            "wrapper gate constant, not an on-disk target-table key."
        ),
        "runtimeBoundary": (
            "This disk snapshot does not prove live slot ownership or exclude a "
            "later, remote, or memory-only patch."
        ),
    }


def _installed_ifix_snapshot(path: Path, gate: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContractError(f"cannot read installed IFix report: {exc}") from exc

    verifier = _load(
        "post_proxy_installed_ifix_verifier",
        LAB_ROOT / "tools" / "verify_installed_ifix_patch_state.py",
    )
    try:
        persistent = payload["vfs_state"]["persistent_overlay"]
        verifier.check_installed_file(persistent["chunk"], "IFix VFS chunk")
        verifier.check_installed_file(
            persistent["block_catalog"], "IFix block catalog"
        )
        patch_path = verifier.check_file(
            persistent["file"], "decrypted Gameplay patch"
        )
        loader = payload["loader_recovery"]
        metadata_catalog_path = verifier.check_file(
            loader["metadata_catalog"], "IFix loader metadata catalog"
        )
        native_map_path = verifier.check_file(
            loader["native_map"], "IFix loader native map"
        )
        metadata_catalog = json.loads(metadata_catalog_path.read_text(encoding="utf-8"))
        native_map = json.loads(native_map_path.read_text(encoding="utf-8"))
        verifier.check_loader_build_provenance(payload, metadata_catalog, native_map)
        parsed_targets, observed = verifier.parse_patch(
            patch_path.read_bytes(), payload["patch_format"]
        )
    except (KeyError, OSError, ValueError, SystemExit) as exc:
        raise ContractError(f"installed IFix source validation failed: {exc}") from exc
    expected = payload["patch_format"]
    for key in ("bridge", "type_count", "target_count"):
        if observed[key] != expected[key]:
            raise ContractError(f"installed IFix parsed {key} drift")
    for key in ("type_table_end", "target_table_end", "file_end"):
        if observed[key] != int(expected[key], 16):
            raise ContractError(f"installed IFix parsed {key} drift")
    if observed["terminal"] != expected["terminal_int32"]:
        raise ContractError("installed IFix parsed terminal drift")

    result = _validate_installed_ifix_payload(payload, gate, parsed_targets)
    result["report"] = {
        "repoPath": _repo_path(path),
        "size": path.stat().st_size,
        "sha256": _sha(path),
    }
    result["parsedPatch"] = {
        "repoPath": _repo_path(patch_path),
        "size": patch_path.stat().st_size,
        "sha256": _sha(patch_path),
    }
    edge_set = {
        (edge["caller"]["methodIndex"], callee["methodIndex"])
        for edge in native_map["directCallEdges"]
        for callee in edge["callees"]
    }
    required_loader_edges = {
        (482175, 482190),
        (482190, 485545),
        (482190, 485546),
        (485545, 485543),
        (485545, 485544),
    }
    if not required_loader_edges <= edge_set:
        raise ContractError(
            "installed IFix local loader edges drift: " +
            repr(sorted(required_loader_edges - edge_set))
        )
    result["loaderEvidence"] = {
        "metadataCatalog": {
            "repoPath": _repo_path(metadata_catalog_path),
            "size": metadata_catalog_path.stat().st_size,
            "sha256": _sha(metadata_catalog_path),
        },
        "nativeMap": {
            "repoPath": _repo_path(native_map_path),
            "size": native_map_path.stat().st_size,
            "sha256": _sha(native_map_path),
        },
        "requiredDirectCallEdges": [
            {"callerMethodIndex": caller, "calleeMethodIndex": callee}
            for caller, callee in sorted(required_loader_edges)
        ],
        "payloadBridge": observed["bridge"],
        "classification": (
            "The hash-pinned local loader gets the VFS stream, unloads the prior "
            "manager, and calls IFix.Core.PatchManager.Load/readSlotInfo/getMapId. "
            "The installed bridge belongs to Gameplay.Beyond, not BeyondDynamicBone."
        ),
    }
    return result


def _gate(game_assembly: Path | None, metadata: Path | None) -> tuple[dict[str, Any], Path, Path]:
    result = check_installed_native_inputs(EXPECTED_GAME_ASSEMBLY_SHA256, EXPECTED_METADATA_SHA256,
                                           gameassembly=game_assembly, metadata=metadata)
    if not result.validated:
        raise ContractError(f"native gate [{result.status}]: {result.detail}")
    ga, md = Path(result.gameassembly), Path(result.metadata)
    gate = {
        "gameAssembly": {"path": _repo_path(ga), "size": ga.stat().st_size,
                         "sha256": result.gameassembly_sha256},
        "globalMetadata": {"path": _repo_path(md), "size": md.stat().st_size,
                           "sha256": result.metadata_sha256},
    }
    return gate, ga, md


def _call_target(pe: Any, call_va: int) -> int:
    data = pe.bytes_at_va(call_va, 5)
    if len(data) != 5 or data[0] != 0xE8:
        raise ContractError(f"expected rel32 call at 0x{call_va:x}")
    return call_va + 5 + struct.unpack_from("<i", data, 1)[0]


def _validate_call(pe: Any, call_va: int, target_va: int) -> None:
    actual = _call_target(pe, call_va)
    if actual != target_va:
        raise ContractError(f"call drift at 0x{call_va:x}: 0x{actual:x} != 0x{target_va:x}")


def _field_layout(md: Any, pe: Any, registration: dict[str, Any], job: str) -> dict[str, Any]:
    type_index, expected, size = JOB_FIELDS[job]
    typedef = md.types[type_index]
    offset_table = pe.u64_at_va(int(registration["fieldOffsets"], 16) + type_index * 8)
    fields = []
    for name, field_index, payload_offset in expected:
        ordinal = field_index - typedef.field_start
        if ordinal < 0 or ordinal >= typedef.field_count:
            raise ContractError(f"field ordinal drift for {job}.{name}")
        actual_name = md.string(md.fields[field_index].name_index)
        boxed_offset = pe.u32_at_va(offset_table + ordinal * 4)
        if actual_name != name or boxed_offset != payload_offset + 0x10:
            raise ContractError(f"field drift for {job}.{name}: {actual_name} 0x{boxed_offset:x}")
        fields.append({"name": name, "fieldIndex": field_index,
                       "nativePayloadOffset": f"0x{payload_offset:x}",
                       "boxedFieldOffset": f"0x{boxed_offset:x}"})
    return {"metadataTypeIndex": type_index, "nativePayloadBytes": size, "fields": fields}


def _signed_i32(pe: Any, va: int) -> int:
    return struct.unpack("<i", struct.pack("<I", pe.u32_at_va(va)))[0]


def _native_type_size(md: Any, pe: Any, registration: dict[str, Any],
                      type_index: int, expected_name: str, expected_size: int) -> dict[str, Any]:
    typedef = md.types[type_index]
    actual_name = md.type_full_name(typedef)
    if actual_name != expected_name:
        raise ContractError(f"native type identity drift for {expected_name}: {actual_name}")
    sizes_table = int(registration["typeDefinitionsSizes"], 16)
    sizes_pointer = pe.u64_at_va(sizes_table + type_index * 8)
    if not sizes_pointer:
        raise ContractError(f"missing native size for {expected_name}")
    instance_size = pe.u32_at_va(sizes_pointer)
    native_size = _signed_i32(pe, sizes_pointer + 4)
    if (instance_size, native_size) != (expected_size + 0x10, expected_size):
        raise ContractError(
            f"native size drift for {expected_name}: instance={instance_size} native={native_size}"
        )
    return {"name": expected_name, "metadataTypeDefinitionIndex": type_index,
            "instanceSizeBytes": instance_size, "nativeSizeBytes": native_size}


def _calc_line_parameter_layout(md: Any, pe: Any,
                                registration: dict[str, Any]) -> list[dict[str, Any]]:
    method = md.methods[CALC_LINE["methodIndex"]]
    if (md.string(method.name_index), f"0x{method.token:08x}", method.parameter_count) != (
            CALC_LINE["method"], "0x06000521", len(CALC_LINE_PARAMETERS)):
        raise ContractError("CalcLineNormalTangent managed parameter declaration drift")
    types_table = int(registration["types"], 16)
    primitive_names = {0x06: "System.Int16", 0x07: "System.UInt16",
                       0x08: "System.Int32", 0x09: "System.UInt32"}
    rows: list[dict[str, Any]] = []
    for ordinal, expected in enumerate(CALC_LINE_PARAMETERS):
        name, metadata_type_index, element_name, element_code, element_typedef, stride, access = expected
        parameter = md.parameters[method.parameter_start + ordinal]
        actual_name = md.string(parameter.name_index)
        if (actual_name, parameter.type_index) != (name, metadata_type_index):
            raise ContractError(
                f"CalcLineNormalTangent parameter {ordinal} drift: "
                f"{actual_name}/{parameter.type_index} != {name}/{metadata_type_index}"
            )
        type_pointer = pe.u64_at_va(types_table + metadata_type_index * 8)
        type_data, type_bits = struct.unpack("<QI", pe.bytes_at_va(type_pointer, 12))
        type_code = (type_bits >> 16) & 0xFF
        if ordinal == len(CALC_LINE_PARAMETERS) - 1:
            pointee_data, pointee_code = type_data, type_code
            if type_code != element_code:
                raise ContractError(f"CalcLineNormalTangent scalar type drift for {name}")
        else:
            if type_code != 0x0F:
                raise ContractError(f"CalcLineNormalTangent {name} is no longer a native pointer")
            pointee_data, pointee_bits = struct.unpack("<QI", pe.bytes_at_va(type_data, 12))
            pointee_code = (pointee_bits >> 16) & 0xFF
            if pointee_code != element_code:
                raise ContractError(f"CalcLineNormalTangent pointee type-code drift for {name}")
        if element_typedef is None:
            actual_element_name = primitive_names.get(pointee_code)
        else:
            if pointee_data != element_typedef:
                raise ContractError(f"CalcLineNormalTangent pointee TypeDef drift for {name}")
            actual_element_name = md.type_full_name(md.types[element_typedef])
        if actual_element_name != element_name:
            raise ContractError(
                f"CalcLineNormalTangent pointee identity drift for {name}: {actual_element_name}"
            )
        if ordinal < 4:
            abi_location = ("rcx", "rdx", "r8", "r9")[ordinal]
            worker_rbp_offset = None
        else:
            stack_offset = 0x28 + (ordinal - 4) * 8
            abi_location = f"entry rsp+0x{stack_offset:x}"
            worker_rbp_offset = f"0x{0x6F8 + stack_offset:x}"
        rows.append({
            "ordinal": ordinal,
            "name": name,
            "metadataParameterIndex": parameter.index,
            "metadataTypeIndex": metadata_type_index,
            "win64Location": abi_location,
            "workerRbpOffset": worker_rbp_offset,
            "elementType": element_name,
            "elementTypeCode": f"0x{element_code:x}",
            "elementTypeDefinitionIndex": element_typedef,
            "elementStrideBytes": stride,
            "access": access,
        })
    return rows


def _calc_line_relevant_layouts(md: Any, pe: Any,
                                registration: dict[str, Any]) -> dict[str, Any]:
    sizes = [
        _native_type_size(md, pe, registration, type_index, name, size)
        for name, type_index, size in CALC_LINE_TYPE_SIZES
    ]
    fields: list[dict[str, Any]] = []
    field_table = int(registration["fieldOffsets"], 16)
    for type_name, type_index, field_name, field_index, field_type_index, native_offset in CALC_LINE_RELEVANT_FIELDS:
        typedef = md.types[type_index]
        field = md.fields[field_index]
        ordinal = field_index - typedef.field_start
        offset_pointer = pe.u64_at_va(field_table + type_index * 8)
        boxed_offset = pe.u32_at_va(offset_pointer + ordinal * 4)
        actual = (md.type_full_name(typedef), md.string(field.name_index), field.type_index,
                  boxed_offset)
        expected = (type_name, field_name, field_type_index, native_offset + 0x10)
        if actual != expected:
            raise ContractError(f"CalcLineNormalTangent field layout drift for {type_name}.{field_name}")
        fields.append({
            "declaringType": type_name,
            "declaringTypeDefinitionIndex": type_index,
            "field": field_name,
            "fieldIndex": field_index,
            "metadataTypeIndex": field_type_index,
            "nativePayloadOffset": f"0x{native_offset:x}",
            "boxedFieldOffset": f"0x{boxed_offset:x}",
        })
    return {"nativeTypes": sizes, "fieldsReadByMethod384856": fields}


def _verified_helper_spans(pe: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, start, size, expected_hash in CALC_LINE_HELPER_SPANS:
        data = pe.bytes_at_va(start, size)
        actual_hash = hashlib.sha256(data).hexdigest()
        if len(data) != size or data[-1:] != b"\xc3" or actual_hash != expected_hash:
            raise ContractError(f"CalcLineNormalTangent helper drift for {name}: {actual_hash}")
        rows.append({"name": name, "startVa": f"0x{start:x}",
                     "throughRetBytes": size, "throughRetSha256": actual_hash})
    return rows


def _generic(index: dict[int, list[dict[str, Any]]], *, pointer: int, method_index: int,
             spec_index: int, slot: int, job_type_index: int, job_type: str,
             inst_index: int | None = None) -> dict[str, Any]:
    matches = [row for row in index.get(pointer, [])
               if row["methodIndex"] == method_index and row["methodSpecIndex"] == spec_index]
    if len(matches) != 1:
        raise ContractError(f"generic MethodSpec drift for {job_type}: {matches}")
    row = matches[0]
    inst = row["methodInstantiation"]
    arg = inst["arguments"][0] if len(inst.get("arguments", [])) == 1 else {}
    if (row["genericMethodPointerSlot"], arg.get("typeIndex"), arg.get("typeName")) != (
            slot, job_type_index, job_type):
        raise ContractError(f"generic identity drift for {job_type}")
    if inst_index is not None and inst.get("genericInstIndex") != inst_index:
        raise ContractError(f"generic instantiation drift for {job_type}")
    return {"methodIndex": method_index, "token": row["token"], "methodSpecIndex": spec_index,
            "genericMethodPointerSlot": slot, "methodInstantiationGenericInstIndex": inst["genericInstIndex"],
            "genericEntryVa": f"0x{pointer:x}", "jobTypeIndex": job_type_index, "jobType": job_type}


def _method_pointer_context(
    md: Any, native: Any, pe: Any, code: int
) -> tuple[list[int], list[int], int, dict[int, list[dict[str, Any]]]]:
    modules = native.parse_codegen_modules(pe, code)
    ranges = native.image_method_ranges(md)
    pointers, method_by_pointer = native.build_pointer_indexes(pe, md, modules, ranges)
    bone = pointers["BeyondDynamicBone.dll"]
    return (bone, sorted({pointer for pointer in bone if pointer}),
            ranges["BeyondDynamicBone.dll"]["methodStart"], method_by_pointer)


def _method_record(md: Any, bone: list[int], unique: list[int], method_start: int, method_index: int,
                   expected_name: str, expected_pointer: int) -> dict[str, Any]:
    pointer = bone[method_index - method_start]
    # Check the defining metadata record and codegen pointer together.
    if pointer != expected_pointer or md.string(md.methods[method_index].name_index) != expected_name:
        raise ContractError(f"worker identity drift for method {method_index}")
    end = next(value for value in unique if value > pointer)
    return {"methodIndex": method_index, "token": f"0x{md.methods[method_index].token:08x}",
            "method": expected_name, "startVa": f"0x{pointer:x}", "endVa": f"0x{end:x}",
            "spanBytes": end - pointer}


def _dependency(path: Path, expected_hash: str, schema: str) -> dict[str, Any]:
    source = _source(path, expected_hash)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != schema or payload.get("native_gate", {}).get("gameAssembly", {}).get("sha256") != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise ContractError(f"dependency contract drift: {path.name}")
    return {**source, "schema": schema, "status": payload.get("status")}


def _calc_line_burst_dependency(path: Path) -> dict[str, Any]:
    """Validate the sibling contract's exact CalcLine target, not its file hash."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if (payload.get("schema") != "endfield.charinfo.secondary-dynamics-burst-export.v1" or
            payload.get("status") != "secondary_dynamics_static_export_core_identities_partial_managed_routes_unresolved"):
        raise ContractError("CalcLine Burst dependency schema/status drift")
    gate = payload.get("native_gate", {})
    expected_gate = {
        "gameAssembly": EXPECTED_GAME_ASSEMBLY_SHA256,
        "globalMetadata": EXPECTED_METADATA_SHA256,
        "libBurstGenerated": EXPECTED_LIB_BURST_SHA256,
    }
    for key, expected in expected_gate.items():
        if gate.get(key, {}).get("sha256") != expected:
            raise ContractError(f"CalcLine Burst dependency {key} gate drift")
    target = payload.get("targets", {}).get("calcLineNormalTangent", {})
    expected = {
        "status": "static_semantic_export_and_dual_cpu_core_identity_closed_runtime_route_unobserved",
        "candidateHash": "7342567c29c434b5b924be51bd8e34b7",
        "functionPointerSlotRva": "0x3c57b0",
    }
    for key, value in expected.items():
        if target.get(key) != value:
            raise ContractError(f"CalcLine Burst dependency target {key} drift")
    if (target.get("export", {}).get("bodySha256") !=
            "17244d44dcff7f94b21b887f24ca42d662db90b81a1a1fcc2220a41e15c90328"):
        raise ContractError("CalcLine Burst dependency export body drift")
    variants = {row.get("cpuVariant"): row for row in target.get("variants", [])}
    expected_cores = {
        "x64_sse2": ("0xf4100", "d2981125e4685061134d4e7c1048efc84c33ecc9053f09d3dc9d104756282824"),
        "avx2": ("0x284c50", "fd0fd8d14052cccdcf137f7e90391faadd0bae6c88c5e199fc908f0b8fe5b07c"),
    }
    for cpu_variant, (rva, sha256) in expected_cores.items():
        core = variants.get(cpu_variant, {}).get("solverCore", {})
        if (core.get("rva"), core.get("sha256")) != (rva, sha256):
            raise ContractError(f"CalcLine Burst dependency {cpu_variant} core drift")
    create_target = payload.get("targets", {}).get("createPostProxyMeshUpdateList", {})
    if (create_target.get("status") !=
            "static_semantic_export_dual_cpu_equations_and_buffers_closed_runtime_route_unobserved" or
            create_target.get("candidateHash") !=
            "ef715c6829f8df5c4396ed6a395d3bb0" or
            create_target.get("functionPointerSlotRva") != "0x3c6a30"):
        raise ContractError("CreatePostProxy Burst dependency target drift")
    create_variants = {
        row.get("cpuVariant"): row for row in create_target.get("variants", [])
    }
    expected_create_cores = {
        "x64_sse2": ("0xf3ad0",
                      "1a032caef0f1f620f05665ab236c15e89483a43d10e6463e40adf0826b21bbda"),
        "avx2": ("0x2845d0",
                 "ac1747a45021702a7b88789dbdfdef99ac44e9df2d3d61aef30b0b04d105e734"),
    }
    for cpu_variant, (rva, sha256) in expected_create_cores.items():
        core = create_variants.get(cpu_variant, {}).get("solverCore", {})
        if (core.get("rva"), core.get("sha256")) != (rva, sha256):
            raise ContractError(
                f"CreatePostProxy Burst dependency {cpu_variant} core drift"
            )
    return {
        "repoPath": _repo_path(path),
        "size": path.stat().st_size,
        "sha256": _sha(path),
        "schema": payload["schema"],
        "status": payload["status"],
        "target": target,
        "createListTarget": create_target,
    }


def _calc_line_burst_numerics_dependency(path: Path) -> dict[str, Any]:
    source = _source(path, EXPECTED_CALC_LINE_BURST_NUMERICS_SHA256)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (payload.get("schema") !=
            "endfield.charinfo.secondary-dynamics-calc-line-burst-golden-vectors.v1" or
            payload.get("status") !=
            "dual_cpu_core_and_source_transcription_exact_for_branch_golden_cases"):
        raise ContractError("CalcLine Burst numeric dependency schema/status drift")
    gate = payload.get("nativeGate", {})
    if (gate.get("gameAssembly", {}).get("sha256") != EXPECTED_GAME_ASSEMBLY_SHA256 or
            gate.get("globalMetadata", {}).get("sha256") != EXPECTED_METADATA_SHA256 or
            gate.get("libBurstGenerated", {}).get("sha256") != EXPECTED_LIB_BURST_SHA256):
        raise ContractError("CalcLine Burst numeric dependency native gate drift")
    boundary = payload.get("boundary", {})
    if (boundary.get("nativeCpuVariantsExecuted") != ["x64_sse2", "avx2"] or
            boundary.get("sourceOnlyTranscriptionMatchedBitForBit") is not True or
            boundary.get("captureUsed") is not False or
            boundary.get("runtimeRouteSelected") is not False or
            boundary.get("managedIfixPatchStateClosed") is not False or
            boundary.get("solverImplemented") is not False or
            boundary.get("retailEquivalent") is not False):
        raise ContractError("CalcLine Burst numeric dependency boundary drift")
    if [row.get("name") for row in payload.get("vectors", [])] != [
        "parallel_move", "quarter_turn_move", "antiparallel_positive_x",
        "non_move_assignment", "two_child_parent_direction_sum",
        "empty_child_no_write", "negative_x_antiparallel_zero_axis",
    ]:
        raise ContractError("CalcLine Burst numeric dependency vector set drift")
    return {**source, "schema": payload["schema"], "status": payload["status"],
            "boundary": boundary, "equations": payload["equations"],
            "degeneracy": payload["degeneracy"]}


def build_contract(*, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
                   metadata: Path | None = DEFAULT_METADATA,
                   metadata_evidence: Path = DEFAULT_METADATA_EVIDENCE,
                   native_evidence: Path = DEFAULT_NATIVE_EVIDENCE) -> dict[str, Any]:
    gate, game_path, metadata_path = _gate(game_assembly, metadata)
    sources = {
        "metadataCatalog": _source(metadata_evidence, EXPECTED_METADATA_EVIDENCE_SHA256),
        "nativeEvidence": _source(native_evidence, EXPECTED_NATIVE_EVIDENCE_SHA256),
    }
    metadata_payload = json.loads(metadata_evidence.read_text(encoding="utf-8"))
    native_payload = json.loads(native_evidence.read_text(encoding="utf-8"))
    if metadata_payload["metadata"]["sha256"] != EXPECTED_METADATA_SHA256:
        raise ContractError("metadata evidence describes another build")
    if (native_payload["metadata"]["metadataSha256"].lower() != EXPECTED_METADATA_SHA256 or
            native_payload["metadata"]["gameAssemblySha256"].lower() != EXPECTED_GAME_ASSEMBLY_SHA256 or
            int(native_payload["settings"]["codeRegistration"], 16) != EXPECTED_CODE_REGISTRATION):
        raise ContractError("native evidence describes another build")
    evidence_method = next((row for row in native_payload["bodyTargets"]
                            if row["methodIndex"] == POST_PROXY["methodIndex"]), None)
    if evidence_method is None or (evidence_method["method"], int(evidence_method["methodPointerVa"], 16),
                                   evidence_method["scanBytes"],
                                   evidence_method["methodBodySummary"]["firstRetOffset"]) != (
            POST_PROXY["method"], POST_PROXY["startVa"], POST_PROXY["spanBytes"], POST_PROXY["firstRetOffset"]):
        raise ContractError("PostProxyMeshUpdate evidence row drift")

    catalog, native = _helpers()
    md = catalog.Metadata(metadata_path)
    pe = native.PeImage(game_path)
    names = {md.string(image.name_index) for image in md.images}
    code = native.find_code_registration(pe, names)
    meta = native.find_metadata_registration(pe, code)
    if (code, meta) != (EXPECTED_CODE_REGISTRATION, EXPECTED_METADATA_REGISTRATION):
        raise ContractError(f"registration drift: {code!r}, {meta!r}")
    registration = native.metadata_registration_summary(pe, meta)
    bone, unique, method_start, method_by_pointer = _method_pointer_context(md, native, pe, code)
    method = md.methods[POST_PROXY["methodIndex"]]
    pointer = bone[POST_PROXY["methodIndex"] - method_start]
    body = pe.bytes_at_va(pointer, POST_PROXY["spanBytes"])
    if (md.string(method.name_index), f"0x{method.token:08x}", pointer,
            pe.file_offset_for_va(pointer)[0], hashlib.sha256(body).hexdigest(), body[POST_PROXY["firstRetOffset"]]) != (
            POST_PROXY["method"], POST_PROXY["token"], POST_PROXY["startVa"], POST_PROXY["fileOffset"],
            POST_PROXY["bodySha256"], 0xC3):
        raise ContractError("authoritative PostProxyMeshUpdate body drift")
    if hashlib.sha256(body[:POST_PROXY["firstRetOffset"] + 1]).hexdigest() != POST_PROXY["throughFirstRetSha256"]:
        raise ContractError("PostProxyMeshUpdate first-return prefix drift")
    expected_entry = bytes.fromhex(
        "48 8b c4 48 89 58 10 48 89 70 18 48 89 78 20 48 89 48 08 55 41 54 41 55 41 56 41 57"
    )
    if body[:len(expected_entry)] != expected_entry or body[0x2E:0x31] != b"\x48\x8b\xda" or body[0x49:0x4C] != b"\x4d\x8b\xe0":
        raise ContractError("PostProxyMeshUpdate Win64 ABI prologue drift")
    if body[0xDFD:0xE00] != b"\x0f\x11\x00":
        raise ContractError("PostProxyMeshUpdate hidden return write drift")

    for stage in STAGES:
        _validate_call(pe, pointer + stage["setIndexCountOffset"], stage["setIndexCountVa"])
        _validate_call(pe, pointer + stage["getReflectionDataOffset"], 0x183F51D90)
    for _, call_va, target_va in FALLBACK_CALLS:
        _validate_call(pe, call_va, target_va)
    for call_va, target_va in ((0x184F71E4E, 0x186732144), (0x184F71FAA, 0x18673237C)):
        _validate_call(pe, call_va, target_va)
    for va, expected in ((0x184F719BD, b"\x41\xb9\x01\x00\x00\x00"),
                         (0x184F71BCC, b"\x41\xb9\x08\x00\x00\x00"),
                         (0x184F71E41, b"\xc7\x44\x24\x20\x10\x00\x00\x00"),
                         (0x184F71F9D, b"\xc7\x44\x24\x20\x20\x00\x00\x00")):
        if pe.bytes_at_va(va, len(expected)) != expected:
            raise ContractError(f"batch-size immediate drift at 0x{va:x}")

    cold = []
    for name, start, size, expected_hash in COLD_SPANS:
        data = pe.bytes_at_va(start, size)
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != expected_hash:
            raise ContractError(f"cold span drift for {name}: {actual_hash}")
        cold.append({"name": name, "startVa": f"0x{start:x}", "spanBytes": size,
                     "sha256": actual_hash})

    generic_index = native.build_generic_method_index(pe, md, code, meta)
    stages = []
    for raw in STAGES:
        job_type = f"BeyondDynamicBone.VirtualMeshManager+{raw['job']}"
        reflection = _generic(generic_index, pointer=0x183F51D90, method_index=401847,
                              spec_index=raw["getReflectionDataMethodSpec"],
                              slot=raw["reflectionPointerSlot"], job_type_index=raw["jobTypeIndex"],
                              job_type=job_type, inst_index=raw["reflectionGenericInst"])
        schedule_raw = raw["schedule"]
        schedule = _generic(generic_index, pointer=schedule_raw["pointerVa"],
                            method_index=schedule_raw["methodIndex"], spec_index=schedule_raw["methodSpec"],
                            slot=schedule_raw["pointerSlot"], job_type_index=raw["jobTypeIndex"],
                            job_type=job_type)
        cross_raw = raw["crossFrame"]
        cross = _generic(generic_index, pointer=cross_raw["pointerVa"],
                         method_index=cross_raw["methodIndex"], spec_index=cross_raw["methodSpec"],
                         slot=cross_raw["pointerSlot"], job_type_index=raw["jobTypeIndex"],
                         job_type=job_type)
        stages.append({"order": raw["order"], "job": raw["job"],
                       "setIndexCount": {"callOffset": f"0x{raw['setIndexCountOffset']:x}",
                                         "targetVa": f"0x{raw['setIndexCountVa']:x}"},
                       "getReflectionData": {**reflection, "callOffset": f"0x{raw['getReflectionDataOffset']:x}"},
                       "parallelSchedule": {**schedule, "kind": schedule_raw["kind"],
                                            "innerLoopBatchCount": schedule_raw["batchSize"]},
                       "crossFrameScheduleHelper": cross,
                       "jobPayload": _field_layout(md, pe, registration, raw["job"])})

    workers = []
    for method_index, name, expected_pointer in WORKER_TARGETS:
        row = _method_record(md, bone, unique, method_start, method_index, name, expected_pointer)
        data = pe.bytes_at_va(expected_pointer, row["spanBytes"])
        row["bodySha256"] = hashlib.sha256(data).hexdigest()
        workers.append(row)
    expected_worker_bodies = {
        384830: (CREATE_LIST_DIRECT_CALL["kernelSpanBytes"],
                 CREATE_LIST_DIRECT_CALL["kernelBodySha256"]),
        384832: (3300, "02a0d53fed888f05f966dbe2250f59e4f2722d0cfac3928e7a2b268d39bb4bde"),
        384854: (CALC_LINE_DIRECT_CALL["kernelSpanBytes"],
                 CALC_LINE_DIRECT_CALL["kernelBodySha256"]),
        384856: (1844, "9868eee8cddc41aae648fead87025f7a53b4d158dca963865dfd2126a0f9a829"),
    }
    for row in workers:
        expected = expected_worker_bodies.get(row["methodIndex"])
        if expected is not None and (row["spanBytes"], row["bodySha256"]) != expected:
            raise ContractError(f"worker body drift for {row['method']}")
    calc_line_kernel = next(row for row in workers if row["methodIndex"] == 384854)
    create_hot_hash = hashlib.sha256(pe.bytes_at_va(0x186743868, 0x223)).hexdigest()
    if create_hot_hash != "05248d617681f7cbce052c79fffc748936523f7230da3812c6c8bab0f3230213":
        raise ContractError(f"CreatePostProxyMeshUpdateList hot-path drift: {create_hot_hash}")
    create_invoke = _method_record(
        md, bone, unique, method_start,
        CREATE_LIST_DIRECT_CALL["invokeMethodIndex"], "Invoke",
        CREATE_LIST_DIRECT_CALL["invokeStartVa"],
    )
    create_invoke_body = pe.bytes_at_va(
        CREATE_LIST_DIRECT_CALL["invokeStartVa"], create_invoke["spanBytes"]
    )
    if (create_invoke["spanBytes"], hashlib.sha256(create_invoke_body).hexdigest()) != (
            CREATE_LIST_DIRECT_CALL["invokeSpanBytes"],
            CREATE_LIST_DIRECT_CALL["invokeBodySha256"]):
        raise ContractError("CreatePostProxy DirectCall Invoke body drift")
    create_get_pointer = _method_record(
        md, bone, unique, method_start,
        CREATE_LIST_DIRECT_CALL["getFunctionPointerMethodIndex"],
        "GetFunctionPointer", CREATE_LIST_DIRECT_CALL["getFunctionPointerStartVa"],
    )
    create_get_pointer_body = pe.bytes_at_va(
        CREATE_LIST_DIRECT_CALL["getFunctionPointerStartVa"],
        create_get_pointer["spanBytes"],
    )
    if (create_get_pointer["spanBytes"],
            hashlib.sha256(create_get_pointer_body).hexdigest()) != (
            CREATE_LIST_DIRECT_CALL["getFunctionPointerSpanBytes"],
            CREATE_LIST_DIRECT_CALL["getFunctionPointerBodySha256"]):
        raise ContractError("CreatePostProxy DirectCall pointer body drift")
    for call_va, target_va in (
        (CREATE_LIST_DIRECT_CALL["kernelStartVa"] + 0xA6,
         CREATE_LIST_DIRECT_CALL["invokeStartVa"]),
        (CREATE_LIST_DIRECT_CALL["invokeStartVa"] + 0x56, 0x18307B8D0),
        (CREATE_LIST_DIRECT_CALL["invokeStartVa"] + 0x6D,
         CREATE_LIST_DIRECT_CALL["getFunctionPointerStartVa"]),
        (CREATE_LIST_DIRECT_CALL["invokeStartVa"] + 0x12B,
         CREATE_LIST_DIRECT_CALL["managedFallbackStartVa"]),
    ):
        _validate_call(pe, call_va, target_va)
    if pe.bytes_at_va(CREATE_LIST_DIRECT_CALL["invokeStartVa"] + 0xCF, 2) != b"\xff\xd0":
        raise ContractError("CreatePostProxy DirectCall indirect pointer call drift")

    calc_line_body = pe.bytes_at_va(CALC_LINE["startVa"], CALC_LINE["spanBytes"])
    calc_line_through_ret = calc_line_body[:CALC_LINE["throughRetBytes"]]
    if (len(calc_line_body), hashlib.sha256(calc_line_body).hexdigest(),
            calc_line_through_ret[-1:], hashlib.sha256(calc_line_through_ret).hexdigest()) != (
            CALC_LINE["spanBytes"], CALC_LINE["bodySha256"], b"\xc3",
            CALC_LINE["throughRetSha256"]):
        raise ContractError("CalcLineNormalTangent managed worker body/return drift")
    direct_call_methods = []
    for method_index, name, start_key, span_key, hash_key in (
        (384862, "GetFunctionPointerDiscard", "getFunctionPointerDiscardStartVa",
         "getFunctionPointerDiscardSpanBytes", "getFunctionPointerDiscardBodySha256"),
        (384863, "GetFunctionPointer", "getFunctionPointerStartVa",
         "getFunctionPointerSpanBytes", "getFunctionPointerBodySha256"),
        (384867, "Invoke", "invokeStartVa", "invokeSpanBytes", "invokeBodySha256"),
    ):
        start = CALC_LINE_DIRECT_CALL[start_key]
        row = _method_record(md, bone, unique, method_start, method_index, name, start)
        data = pe.bytes_at_va(start, row["spanBytes"])
        row["bodySha256"] = hashlib.sha256(data).hexdigest()
        if (row["spanBytes"], row["bodySha256"]) != (
                CALC_LINE_DIRECT_CALL[span_key], CALC_LINE_DIRECT_CALL[hash_key]):
            raise ContractError(f"CalcLineNormalTangent DirectCall {name} body drift")
        direct_call_methods.append(row)

    fallback_body = pe.bytes_at_va(
        CALC_LINE_DIRECT_CALL["fallbackStartVa"], CALC_LINE_DIRECT_CALL["fallbackSpanBytes"]
    )
    fallback_through_ret = fallback_body[:CALC_LINE_DIRECT_CALL["fallbackThroughRetBytes"]]
    if (len(fallback_body), hashlib.sha256(fallback_body).hexdigest(),
            fallback_through_ret[-1:], hashlib.sha256(fallback_through_ret).hexdigest()) != (
            CALC_LINE_DIRECT_CALL["fallbackSpanBytes"],
            CALC_LINE_DIRECT_CALL["fallbackBodySha256"], b"\xc3",
            CALC_LINE_DIRECT_CALL["fallbackThroughRetSha256"]):
        raise ContractError("CalcLineNormalTangent DirectCall managed fallback body/return drift")

    equivalent_calls = []
    for name, target_va, managed_offset, fallback_offset in CALC_LINE_EQUIVALENT_CALLS:
        _validate_call(pe, CALC_LINE["startVa"] + managed_offset, target_va)
        _validate_call(pe, CALC_LINE_DIRECT_CALL["fallbackStartVa"] + fallback_offset, target_va)
        equivalent_calls.append({
            "name": name,
            "targetVa": f"0x{target_va:x}",
            "managedWorkerOffset": f"0x{managed_offset:x}",
            "directCallFallbackOffset": f"0x{fallback_offset:x}",
        })

    # Pin the generated route itself: kernel -> DirectCall.Invoke, then
    # BurstCompiler.get_IsEnabled plus a non-null returned pointer selects the
    # indirect call; either failed gate reaches the separate managed fallback.
    _validate_call(pe, CALC_LINE_DIRECT_CALL["kernelStartVa"] + 0x10A,
                   CALC_LINE_DIRECT_CALL["invokeStartVa"])
    _validate_call(pe, CALC_LINE_DIRECT_CALL["getFunctionPointerStartVa"] + 0x45,
                   CALC_LINE_DIRECT_CALL["getFunctionPointerDiscardStartVa"])
    _validate_call(pe, CALC_LINE_DIRECT_CALL["getFunctionPointerDiscardStartVa"] + 0xB5,
                   0x18474F6F0)
    _validate_call(pe, CALC_LINE_DIRECT_CALL["invokeStartVa"] + 0x59, 0x18307B8D0)
    _validate_call(pe, CALC_LINE_DIRECT_CALL["invokeStartVa"] + 0x74,
                   CALC_LINE_DIRECT_CALL["getFunctionPointerStartVa"])
    _validate_call(pe, CALC_LINE_DIRECT_CALL["invokeStartVa"] + 0x202,
                   CALC_LINE_DIRECT_CALL["fallbackStartVa"])
    if pe.bytes_at_va(CALC_LINE_DIRECT_CALL["invokeStartVa"] + 0x13B, 3) != b"\x41\xff\xd2":
        raise ContractError("CalcLineNormalTangent DirectCall indirect pointer call drift")
    if pe.bytes_at_va(CALC_LINE_DIRECT_CALL["invokeStartVa"] + 0x5E, 8) != bytes.fromhex(
            "84 c0 0f 84 dd 00 00 00"):
        raise ContractError("CalcLineNormalTangent Burst-enabled gate drift")
    if pe.bytes_at_va(CALC_LINE_DIRECT_CALL["invokeStartVa"] + 0x7C, 9) != bytes.fromhex(
            "48 85 c0 0f 84 be 00 00 00"):
        raise ContractError("CalcLineNormalTangent non-null pointer gate drift")

    def exact_global_method(pointer: int, method_index: int, type_name: str,
                            method_name: str, token: str) -> dict[str, Any]:
        rows = method_by_pointer.get(pointer, [])
        matches = [row for row in rows if row.get("methodIndex") == method_index]
        if len(matches) != 1:
            raise ContractError(f"global method pointer identity drift at 0x{pointer:x}")
        row = matches[0]
        if (row.get("type"), row.get("method"), row.get("token")) != (
                type_name, method_name, token):
            raise ContractError(f"global method declaration drift for {type_name}.{method_name}")
        return row

    def exact_body(pointer: int, method_index: int, type_name: str,
                   method_name: str, token: str, span_bytes: int,
                   expected_hash: str) -> dict[str, Any]:
        row = exact_global_method(pointer, method_index, type_name, method_name, token)
        body = pe.bytes_at_va(pointer, span_bytes)
        actual_hash = hashlib.sha256(body).hexdigest()
        if len(body) != span_bytes or actual_hash != expected_hash:
            raise ContractError(
                f"body drift for {type_name}.{method_name}: {actual_hash}"
            )
        return {
            **row,
            "startVa": f"0x{pointer:x}",
            "spanBytes": span_bytes,
            "bodySha256": actual_hash,
        }

    burst_is_enabled = exact_global_method(
        0x18307B8D0, 489283, "Unity.Burst.BurstCompiler", "get_IsEnabled", "0x0600000b"
    )
    burst_is_enabled_body = pe.bytes_at_va(0x18307B8D0, 0x66)
    if hashlib.sha256(burst_is_enabled_body).hexdigest() != (
            "7ede93cde144cea0e1a57122cafa2c367eda826992de1cc6e93eb55386d2db67"):
        raise ContractError("BurstCompiler.get_IsEnabled body drift")
    burst_get_ilpp = exact_global_method(
        0x18474F6F0, 489285, "Unity.Burst.BurstCompiler",
        "GetILPPMethodFunctionPointer2", "0x0600000d"
    )
    burst_get_ilpp_body = pe.bytes_at_va(
        0x18474F6F0, BURST_RUNTIME_SELECTION["getIlppSpanBytes"]
    )
    if (hashlib.sha256(burst_get_ilpp_body).hexdigest() !=
            BURST_RUNTIME_SELECTION["getIlppBodySha256"] or
            burst_get_ilpp_body[6:33] != bytes.fromhex(
                "48 85 c9 0f 84 e1 4e 7e 00 48 85 d2 0f 84 86 4e 7e 00 "
                "4d 85 c0 0f 84 2b 4e 7e 00"
            ) or
            burst_get_ilpp_body[33:42] != bytes.fromhex(
                "48 8b c1 48 83 c4 20 5b c3"
            )):
        raise ContractError("GetILPPMethodFunctionPointer2 identity/nullability drift")

    burst_compiler_cctor = exact_body(
        BURST_RUNTIME_SELECTION["burstCompilerCctorStartVa"],
        BURST_RUNTIME_SELECTION["burstCompilerCctorMethodIndex"],
        "Unity.Burst.BurstCompiler", ".cctor", "0x06000012",
        BURST_RUNTIME_SELECTION["burstCompilerCctorSpanBytes"],
        BURST_RUNTIME_SELECTION["burstCompilerCctorBodySha256"],
    )
    options_ctor = exact_body(
        BURST_RUNTIME_SELECTION["optionsCtorStartVa"],
        BURST_RUNTIME_SELECTION["optionsCtorMethodIndex"],
        "Unity.Burst.BurstCompilerOptions", ".ctor", "0x0600001f",
        BURST_RUNTIME_SELECTION["optionsCtorSpanBytes"],
        BURST_RUNTIME_SELECTION["optionsCtorBodySha256"],
    )
    options_set_enabled = exact_body(
        BURST_RUNTIME_SELECTION["optionsSetEnabledStartVa"],
        BURST_RUNTIME_SELECTION["optionsSetEnabledMethodIndex"],
        "Unity.Burst.BurstCompilerOptions", "set_EnableBurstCompilation",
        "0x06000022", BURST_RUNTIME_SELECTION["optionsSetEnabledSpanBytes"],
        BURST_RUNTIME_SELECTION["optionsSetEnabledBodySha256"],
    )
    options_cctor = exact_body(
        BURST_RUNTIME_SELECTION["optionsCctorStartVa"],
        BURST_RUNTIME_SELECTION["optionsCctorMethodIndex"],
        "Unity.Burst.BurstCompilerOptions", ".cctor", "0x0600002a",
        BURST_RUNTIME_SELECTION["optionsCctorSpanBytes"],
        BURST_RUNTIME_SELECTION["optionsCctorBodySha256"],
    )
    check_secondary = exact_global_method(
        BURST_RUNTIME_SELECTION["checkSecondaryStartVa"],
        BURST_RUNTIME_SELECTION["checkSecondaryMethodIndex"],
        "Unity.Burst.BurstCompilerOptions", "CheckIsSecondaryUnityProcess",
        "0x0600002b",
    )
    check_secondary_body = pe.bytes_at_va(
        BURST_RUNTIME_SELECTION["checkSecondaryStartVa"],
        BURST_RUNTIME_SELECTION["checkSecondaryThroughRetBytes"],
    )
    if (check_secondary_body != b"\x32\xc0\xc3" or
            hashlib.sha256(check_secondary_body).hexdigest() !=
            BURST_RUNTIME_SELECTION["checkSecondaryThroughRetSha256"]):
        raise ContractError("Burst secondary-process predicate drift")

    helper_is_burst_enabled = exact_body(
        BURST_RUNTIME_SELECTION["helperIsBurstEnabledStartVa"],
        BURST_RUNTIME_SELECTION["helperIsBurstEnabledMethodIndex"],
        "Unity.Burst.BurstCompiler+BurstCompilerHelper", "IsBurstEnabled",
        "0x06000014", BURST_RUNTIME_SELECTION["helperIsBurstEnabledSpanBytes"],
        BURST_RUNTIME_SELECTION["helperIsBurstEnabledBodySha256"],
    )
    helper_cctor = exact_body(
        BURST_RUNTIME_SELECTION["helperCctorStartVa"],
        BURST_RUNTIME_SELECTION["helperCctorMethodIndex"],
        "Unity.Burst.BurstCompiler+BurstCompilerHelper", ".cctor",
        "0x06000017", BURST_RUNTIME_SELECTION["helperCctorThroughRetBytes"],
        BURST_RUNTIME_SELECTION["helperCctorThroughRetSha256"],
    )
    helper_is_compiled = exact_body(
        BURST_RUNTIME_SELECTION["helperIsCompiledStartVa"],
        BURST_RUNTIME_SELECTION["helperIsCompiledMethodIndex"],
        "Unity.Burst.BurstCompiler+BurstCompilerHelper", "IsCompiledByBurst",
        "0x06000016", BURST_RUNTIME_SELECTION["helperIsCompiledThroughRetBytes"],
        BURST_RUNTIME_SELECTION["helperIsCompiledThroughRetSha256"],
    )
    compile_async = exact_body(
        BURST_RUNTIME_SELECTION["compileAsyncStartVa"],
        BURST_RUNTIME_SELECTION["compileAsyncMethodIndex"],
        "Unity.Burst.LowLevel.BurstCompilerService", "CompileAsyncDelegateMethod",
        "0x06000137", BURST_RUNTIME_SELECTION["compileAsyncSpanBytes"],
        BURST_RUNTIME_SELECTION["compileAsyncBodySha256"],
    )
    get_async = exact_body(
        BURST_RUNTIME_SELECTION["getAsyncStartVa"],
        BURST_RUNTIME_SELECTION["getAsyncMethodIndex"],
        "Unity.Burst.LowLevel.BurstCompilerService",
        "GetAsyncCompiledAsyncDelegateMethod", "0x06000138",
        BURST_RUNTIME_SELECTION["getAsyncSpanBytes"],
        BURST_RUNTIME_SELECTION["getAsyncBodySha256"],
    )
    helper_is_burst_enabled_body = pe.bytes_at_va(
        BURST_RUNTIME_SELECTION["helperIsBurstEnabledStartVa"],
        BURST_RUNTIME_SELECTION["helperIsBurstEnabledSpanBytes"],
    )
    if (helper_is_burst_enabled_body[0x35:0x3C] !=
            bytes.fromhex("32 c0 48 83 c4 28 c3")):
        raise ContractError("Burst helper managed IsBurstEnabled return drift")
    if _metadata_usage_source(pe, 0x18E3906A8, 3) != 489292:
        raise ContractError("Burst helper IsBurstEnabled delegate target drift")
    for call_va, target_va in (
        (BURST_RUNTIME_SELECTION["helperCctorStartVa"] + 0x63, 0x183FAEAA0),
        (BURST_RUNTIME_SELECTION["helperCctorStartVa"] + 0x9F,
         BURST_RUNTIME_SELECTION["helperIsCompiledStartVa"]),
        (BURST_RUNTIME_SELECTION["helperIsCompiledStartVa"] + 0x3C,
         BURST_RUNTIME_SELECTION["compileAsyncStartVa"]),
        (BURST_RUNTIME_SELECTION["helperIsCompiledStartVa"] + 0x45,
         BURST_RUNTIME_SELECTION["getAsyncStartVa"]),
    ):
        _validate_call(pe, call_va, target_va)
    if pe.bytes_at_va(
            BURST_RUNTIME_SELECTION["helperCctorStartVa"] + 0xB2, 3
    ) != bytes.fromhex("88 42 08"):
        raise ContractError("BurstCompilerHelper.IsBurstGenerated store drift")
    options_cold = pe.bytes_at_va(
        BURST_RUNTIME_SELECTION["optionsCctorColdStartVa"],
        BURST_RUNTIME_SELECTION["optionsCctorColdSpanBytes"],
    )
    if hashlib.sha256(options_cold).hexdigest() != BURST_RUNTIME_SELECTION[
            "optionsCctorColdSha256"]:
        raise ContractError("Burst options command/environment cold branches drift")
    _validate_call(pe, BURST_RUNTIME_SELECTION["burstCompilerCctorStartVa"] + 0x6E,
                   BURST_RUNTIME_SELECTION["optionsCtorStartVa"])
    _validate_call(pe, BURST_RUNTIME_SELECTION["optionsCtorStartVa"] + 0x11,
                   BURST_RUNTIME_SELECTION["optionsSetEnabledStartVa"])
    if pe.bytes_at_va(
            BURST_RUNTIME_SELECTION["optionsSetEnabledStartVa"] + 0xB7, 2
    ) != b"\x88\x18":
        raise ContractError("BurstCompiler._IsEnabled global write drift")
    if pe.bytes_at_va(
            BURST_RUNTIME_SELECTION["optionsSetEnabledStartVa"] + 0x69, 3
    ) != b"\x80\x39\x00":
        raise ContractError("ForceDisableBurstCompilation gate drift")

    burst_usage_types = {
        "BurstCompiler": _metadata_usage_type(
            md, pe, registration, 0x18E366608, "Unity.Burst.BurstCompiler"
        ),
        "BurstCompilerHelper": _metadata_usage_type(
            md, pe, registration, 0x18E390770,
            "Unity.Burst.BurstCompiler+BurstCompilerHelper"
        ),
        "BurstCompilerOptions": _metadata_usage_type(
            md, pe, registration, 0x18E390710,
            "Unity.Burst.BurstCompilerOptions"
        ),
        "CalcLineDirectCall": _metadata_usage_type(
            md, pe, registration, 0x18E2FD760,
            "BeyondDynamicBone.VirtualMeshManager+CalcLineNormalTangentJobKernels+"
            "CalcLineNormalTangentKernel_000002EA$BurstDirectCall"
        ),
    }
    burst_disable_inputs = {
        "commandLine": _metadata_usage_string(
            md, pe, 0x18E390620, "--burst-disable-compilation"
        ),
        "forceSyncCommandLine": _metadata_usage_string(
            md, pe, 0x18E390610, "--burst-force-sync-compilation"
        ),
        "environment": _metadata_usage_string(
            md, pe, 0x18E390600, "UNITY_BURST_DISABLE_COMPILATION"
        ),
        "environmentFalseValue": _metadata_usage_string(md, pe, 0x18E33B918, "0"),
    }

    direct_call_cctor = exact_body(
        BURST_RUNTIME_SELECTION["directCallCctorStartVa"],
        BURST_RUNTIME_SELECTION["directCallCctorMethodIndex"],
        "BeyondDynamicBone.VirtualMeshManager+CalcLineNormalTangentJobKernels+"
        "CalcLineNormalTangentKernel_000002EA$BurstDirectCall",
        ".cctor", "0x0600052b",
        BURST_RUNTIME_SELECTION["directCallCctorSpanBytes"],
        BURST_RUNTIME_SELECTION["directCallCctorBodySha256"],
    )
    direct_call_ctor = exact_body(
        BURST_RUNTIME_SELECTION["directCallCtorStartVa"],
        BURST_RUNTIME_SELECTION["directCallCtorMethodIndex"],
        "BeyondDynamicBone.VirtualMeshManager+CalcLineNormalTangentJobKernels+"
        "CalcLineNormalTangentKernel_000002EA$BurstDirectCall",
        "Constructor", "0x06000529",
        BURST_RUNTIME_SELECTION["directCallCtorSpanBytes"],
        BURST_RUNTIME_SELECTION["directCallCtorBodySha256"],
    )
    _validate_call(pe, BURST_RUNTIME_SELECTION["directCallCtorStartVa"] + 0x5B,
                   0x183FB0BC0)
    if (pe.bytes_at_va(BURST_RUNTIME_SELECTION["directCallCctorStartVa"], 7) !=
            bytes.fromhex("33 c9 e9 09 00 00 00") or
            pe.bytes_at_va(BURST_RUNTIME_SELECTION["directCallCtorStartVa"] + 0x86, 4) !=
            bytes.fromhex("48 89 58 08") or
            pe.bytes_at_va(CALC_LINE_DIRECT_CALL["getFunctionPointerDiscardStartVa"] + 0xC8, 3) !=
            bytes.fromhex("48 89 02")):
        raise ContractError("CalcLine DirectCall pointer initialization/store drift")
    helper_spans = _verified_helper_spans(pe)
    parameter_layout = _calc_line_parameter_layout(md, pe, registration)
    relevant_layouts = _calc_line_relevant_layouts(md, pe, registration)

    from_to = _method_record(md, bone, unique, method_start, 386226,
                             "FromToRotation", 0x1866AEF20)
    if from_to["token"] != "0x06000a7b":
        raise ContractError("MathUtility.FromToRotation token drift")
    from_to_method = md.methods[386226]
    from_to_parameters = [
        (md.string(md.parameters[index].name_index), md.parameters[index].type_index)
        for index in range(from_to_method.parameter_start,
                           from_to_method.parameter_start + from_to_method.parameter_count)
    ]
    if from_to_parameters != [("from", 114557), ("to", 114557), ("t", 137548)]:
        raise ContractError("MathUtility.FromToRotation parameter declaration drift")
    is_move = _method_record(md, bone, unique, method_start, 386730,
                             "IsMove", 0x1866FF05C)
    if is_move["token"] != "0x06000c73":
        raise ContractError("VertexAttribute.IsMove token drift")
    if pe.bytes_at_va(0x1866AEF7B, 7) != bytes.fromhex("33 d2 b9 19 02 00 00"):
        raise ContractError("MathUtility.FromToRotation IFix patch id drift")
    for call_va, target_va in ((0x1866AEF82, 0x182F95A30),
                               (0x1866AF1BB, 0x185396738),
                               (0x1866AF1E6, 0x1866C4FE4)):
        _validate_call(pe, call_va, target_va)
    constants = (
        ("one", 0x18B959238, struct.pack("<d", 1.0)),
        ("minusOne", 0x18B9594F8, struct.pack("<d", -1.0)),
        ("parallelEpsilon", 0x18DC807B8, bytes.fromhex("00 00 00 a0 f7 c6 b0 3e")),
        ("pi", 0x18DC80A70, bytes.fromhex("00 00 00 60 fb 21 09 40")),
        ("antiparallelYAxisXY", 0x18DA45B60, struct.pack("<dd", 0.0, 1.0)),
        ("antiparallelXAxisXY", 0x18DC80FC0, struct.pack("<dd", 1.0, 0.0)),
    )
    constant_rows = []
    for name, va, expected in constants:
        actual = pe.bytes_at_va(va, len(expected))
        if actual != expected:
            raise ContractError(f"MathUtility.FromToRotation constant drift for {name}")
        constant_rows.append({"name": name, "va": f"0x{va:x}", "bytes": actual.hex()})

    ifix_type = md.types[IFIX_WRAPPER_BOOTSTRAP["dynamicWrapperTypeDefinitionIndex"]]
    if (md.type_full_name(ifix_type), md.image_name_by_type_index.get(ifix_type.index)) != (
            "IFix.ILFixDynamicMethodWrapper", "BeyondDynamicBone.dll"):
        raise ContractError("BeyondDynamicBone IFix dynamic-wrapper type identity drift")
    wrapper_field = md.fields[IFIX_WRAPPER_BOOTSTRAP["wrapperArrayFieldIndex"]]
    if (wrapper_field.index - ifix_type.field_start < 0 or
            wrapper_field.index - ifix_type.field_start >= ifix_type.field_count or
            md.string(wrapper_field.name_index) !=
            IFIX_WRAPPER_BOOTSTRAP["wrapperArrayFieldName"]):
        raise ContractError("BeyondDynamicBone IFix wrapperArray field identity drift")
    ifix_usage_type = _metadata_usage_type(
        md, pe, registration, 0x18E2EA7D0, "IFix.ILFixDynamicMethodWrapper"
    )
    if ifix_usage_type["typeDefinitionIndex"] != ifix_type.index:
        raise ContractError("BeyondDynamicBone IFix wrapper metadata usage drift")
    ifix_cctor = exact_body(
        IFIX_WRAPPER_BOOTSTRAP["wrapperArrayCctorStartVa"],
        IFIX_WRAPPER_BOOTSTRAP["wrapperArrayCctorMethodIndex"],
        "IFix.ILFixDynamicMethodWrapper", ".cctor", "0x06000ef9",
        IFIX_WRAPPER_BOOTSTRAP["wrapperArrayCctorThroughRetBytes"],
        IFIX_WRAPPER_BOOTSTRAP["wrapperArrayCctorThroughRetSha256"],
    )
    ifix_get_patch = exact_body(
        IFIX_WRAPPER_BOOTSTRAP["getPatchStartVa"],
        IFIX_WRAPPER_BOOTSTRAP["getPatchMethodIndex"],
        "IFix.WrappersManagerImpl", "GetPatch", "0x06000f00",
        IFIX_WRAPPER_BOOTSTRAP["getPatchSpanBytes"],
        IFIX_WRAPPER_BOOTSTRAP["getPatchBodySha256"],
    )
    ifix_is_patched = exact_body(
        IFIX_WRAPPER_BOOTSTRAP["isPatchedStartVa"],
        IFIX_WRAPPER_BOOTSTRAP["isPatchedMethodIndex"],
        "IFix.WrappersManagerImpl", "IsPatched", "0x06000f01",
        IFIX_WRAPPER_BOOTSTRAP["isPatchedSpanBytes"],
        IFIX_WRAPPER_BOOTSTRAP["isPatchedBodySha256"],
    )
    if (pe.bytes_at_va(IFIX_WRAPPER_BOOTSTRAP["wrapperArrayCctorStartVa"] + 0x33, 2) !=
            b"\x33\xd2" or
            pe.bytes_at_va(IFIX_WRAPPER_BOOTSTRAP["wrapperArrayCctorStartVa"] + 0x48, 3) !=
            b"\x48\x89\x02" or
            pe.bytes_at_va(IFIX_WRAPPER_BOOTSTRAP["isPatchedStartVa"] + 0x66, 6) !=
            bytes.fromhex("48 83 7c d9 20 00")):
        raise ContractError("BeyondDynamicBone IFix empty-array/slot-test semantics drift")

    dependencies = {
        "callback": _dependency(DATA_ROOT / "secondary_dynamics_callback_contract.json",
                                "a6143a667a6df88f088201fe314522589f9faf5149ed2f20a1dc581cf3f27f65",
                                "endfield.charinfo.secondary-dynamics-callback-writeback.v1"),
        "transformWriteback": _dependency(DATA_ROOT / "secondary_dynamics_transform_writeback_contract.json",
                                          "f3e44da89e706cf5a43e625f774196091790b5d548ab720d35b0d8ce77c520c8",
                                          "endfield.charinfo.secondary-dynamics-transform-writeback.v1"),
        "calcLineBurstExport": _calc_line_burst_dependency(DEFAULT_BURST_CONTRACT),
        "calcLineBurstNumerics": _calc_line_burst_numerics_dependency(
            DEFAULT_CALC_LINE_BURST_NUMERICS
        ),
    }
    installed_ifix = _installed_ifix_snapshot(DEFAULT_IFIX_REPORT, gate)
    sources["dependencies"] = dependencies
    sources["installedLocalIfix"] = installed_ifix
    return {
        "schema": "endfield.charinfo.secondary-dynamics-post-proxy.v1",
        "status": "post_proxy_create_list_and_calc_line_burst_numerics_closed_runtime_selection_open",
        "manager_schedule_closed": True,
        "managed_job_payload_layout_closed": True,
        "generic_methodspec_identities_closed": True,
        "world_local_publication_equations_closed": True,
        "create_list_worker_control_flow_recovered": True,
        "create_list_directcall_route_recovered": True,
        "calc_line_entry_control_flow_recovered": True,
        "calc_line_child_traversal_recovered": True,
        "calc_line_managed_worker_equations_recovered": True,
        "calc_line_managed_worker_degeneracy_branches_recovered": True,
        "calc_line_data_layout_closed": True,
        "calc_line_kernel_wrapper_route_recovered": True,
        "calc_line_directcall_managed_fallback_equivalence_closed": True,
        "calc_line_burst_function_pointer_target_closed": True,
        "calc_line_get_ilpp_normal_return_nonnull_closed": True,
        "calc_line_get_ilpp_return_identity_closed": True,
        "burst_initial_default_conditions_closed": True,
        "from_to_rotation_installed_local_ifix_target_absent": True,
        "from_to_rotation_installed_local_ifix_bootstrap_absent": True,
        "create_list_kernel_numerics_recovered": True,
        "selected_create_list_execution_route_closed": False,
        "calc_line_normal_tangent_numerics_recovered": False,
        "calc_line_burst_numerics_recovered": True,
        "selected_calc_line_execution_route_closed": False,
        "from_to_rotation_ifix_patch_state_closed": False,
        "selected_cross_frame_route_closed": False,
        "solver_implemented": False,
        "retail_equivalent": False,
        "capture_used_as_implementation_source": False,
        "native_gate": gate,
        "sources": sources,
        "registrations": {"codeRegistrationVa": f"0x{code:x}",
                          "metadataRegistrationVa": f"0x{meta:x}"},
        "managerAbi": {
            "methodIndex": POST_PROXY["methodIndex"], "token": POST_PROXY["token"],
            "type": POST_PROXY["type"], "method": POST_PROXY["method"],
            "startVa": f"0x{pointer:x}", "fileOffset": f"0x{POST_PROXY['fileOffset']:x}",
            "spanBytes": POST_PROXY["spanBytes"], "bodySha256": POST_PROXY["bodySha256"],
            "firstRetOffset": f"0x{POST_PROXY['firstRetOffset']:x}",
            "throughFirstRetSha256": POST_PROXY["throughFirstRetSha256"],
            "win64Arguments": {"rcx": "hidden 16-byte JobHandle return buffer", "rdx": "VirtualMeshManager this",
                               "r8": "input JobHandle address", "r9": "MethodInfo (unused by unpatched body)"},
            "return": "the dependency threaded through all four stages is written to the hidden return buffer",
        },
        "stageOrder": stages,
        "dependencyFlow": "input JobHandle -> CreatePostProxyMeshUpdateList -> CalcLineNormalTangent -> WriteTransformData -> WriteTransformLocalData -> returned JobHandle",
        "createListHotControlFlow": {
            "managedWorkerMethodIndex": 384832,
            "hotSpan": {"startVa": "0x186743868", "throughRetBytes": 0x223,
                        "throughRetSha256": "05248d617681f7cbce052c79fffc748936523f7230da3812c6c8bab0f3230213"},
            "argumentBoundary": {
                "registers": {"rcx": "teamDataArray", "rdx": "processingCounter0",
                              "r8": "processingList0", "r9": "processingCounter1"},
                "stackArguments": [
                    {"rbpOffset": "0x120", "value": "processingList1"},
                    {"rbpOffset": "0x128", "value": "processingCounter2"},
                    {"rbpOffset": "0x130", "value": "processingList2"},
                    {"rbpOffset": "0x138", "value": "processingCounter3"},
                    {"rbpOffset": "0x140", "value": "processingList3"},
                    {"rbpOffset": "0x148", "value": "teamId"},
                ],
            },
            "teamDataStrideBytes": 0x1D0,
            "gates": [
                {"offset": "0x2d", "condition": "teamId != 0"},
                {"offset": "0xcb", "call": "TeamData.get_IsEnable", "required": True},
                {"offset": "0xdf", "call": "TeamData.get_IsCullingInvisible", "required": False},
            ],
            "atomicQueueAppends": [
                {"queue": 0, "sourceDataChunkPayloadOffsets": ["0x44", "0x48"],
                 "conditions": ["TeamData.get_TriangleCount() > 0", "DataChunk at payload 0x44 is valid"],
                 "atomicReserveOffset": "0x110", "appendLoopOffsets": ["0x121", "0x134"]},
                {"queue": 1, "sourceDataChunkPayloadOffsets": ["0x44", "0x48"],
                 "conditions": ["TeamData payload int at 0x38 == 3"],
                 "atomicReserveOffset": "0x143", "appendLoopOffsets": ["0x158", "0x16f"]},
                {"queue": 2, "sourceDataChunkPayloadOffsets": ["0x7c", "0x80"],
                 "conditions": ["DataChunk at payload 0x7c is valid"],
                 "atomicReserveOffset": "0x191", "appendLoopOffsets": ["0x1a6", "0x1bc"]},
                {"queue": 3, "sourceDataChunkPayloadOffsets": ["0x54", "0x58"],
                 "conditions": ["TeamData.get_TriangleCount() > 0"],
                 "atomicReserveOffset": "0x1d5", "appendLoopOffsets": ["0x1ef", "0x204"]},
            ],
            "operation": "Each accepted chunk atomically reserves count slots, then appends the contiguous indices start + i. No captured indices are stored.",
        },
        "burstRuntimeSelectionEvidence": {
            "helperManagedBody": {
                **helper_is_burst_enabled,
                "delegateMetadataUsageSlotVa": "0x18e3906a8",
                "registeredManagedReturn": False,
                "classification": (
                    "The registered IL2CPP fallback body returns false, but "
                    "BurstCompiler.get_IsEnabled does not call this body."
                ),
            },
            "helperInitialization": {
                "typeInitializer": helper_cctor,
                "isCompiledByBurst": helper_is_compiled,
                "delegateTargetMethodIndex": 489292,
                "compileAsyncCallOffset": "0x3c",
                "getAsyncCompiledCallOffset": "0x45",
                "isBurstGeneratedStoreOffset": "0xb2",
                "operation": (
                    "The helper type initializer constructs a delegate for method "
                    "489292, submits it to BurstCompilerService, and stores whether "
                    "GetAsyncCompiledAsyncDelegateMethod returned non-null in the "
                    "IsBurstGenerated byte."
                ),
            },
            "compilerService": {
                "compileAsyncDelegateMethod": compile_async,
                "getAsyncCompiledAsyncDelegateMethod": get_async,
                "runtimeBoundary": (
                    "Both methods dispatch through runtime-populated native service "
                    "pointers. The pinned files do not serialize their returned handle "
                    "or compiled delegate pointer."
                ),
            },
            "classification": (
                "The former generic service-backed boundary is now an exact, "
                "hash-pinned delegate/service/non-nullness chain. The constant-false "
                "managed helper body is not the value stored in IsBurstGenerated and "
                "therefore cannot select the managed DirectCall branch by itself."
            ),
            "selectedIsBurstGeneratedValue": "unresolved",
        },
        "createListDirectCallRoute": {
            "kernelWrapper": {
                "methodIndex": CREATE_LIST_DIRECT_CALL["kernelMethodIndex"],
                "startVa": f"0x{CREATE_LIST_DIRECT_CALL['kernelStartVa']:x}",
                "spanBytes": CREATE_LIST_DIRECT_CALL["kernelSpanBytes"],
                "bodySha256": CREATE_LIST_DIRECT_CALL["kernelBodySha256"],
                "invokeCallOffset": "0xa6",
                "invokeMethodIndex": CREATE_LIST_DIRECT_CALL["invokeMethodIndex"],
            },
            "invoke": {
                **create_invoke,
                "bodySha256": CREATE_LIST_DIRECT_CALL["invokeBodySha256"],
                "burstEnabledCallOffset": "0x56",
                "getFunctionPointerCallOffset": "0x6d",
                "indirectCallOffset": "0xcf",
                "managedFallbackCallOffset": "0x12b",
            },
            "managedFallback": {
                "methodIndex": CREATE_LIST_DIRECT_CALL["managedFallbackMethodIndex"],
                "startVa": f"0x{CREATE_LIST_DIRECT_CALL['managedFallbackStartVa']:x}",
                "spanBytes": CREATE_LIST_DIRECT_CALL["managedFallbackSpanBytes"],
                "bodySha256": CREATE_LIST_DIRECT_CALL["managedFallbackBodySha256"],
                "equations": "createListHotControlFlow",
            },
            "burstFunctionPointerTarget": dependencies["calcLineBurstExport"][
                "createListTarget"
            ],
            "numericEquivalence": (
                "Both exact Burst cores and the managed fallback perform the same "
                "four signed atomic reservations and contiguous sourceStart+i writes. "
                "SSE2/AVX2 vector blocks only batch that integer sequence."
            ),
            "selectedRuntimeRoute": "unresolved",
        },
        "calcLineEntryControlFlow": {
            "managedWorkerMethodIndex": 384856,
            "startVa": "0x186744fb0",
            "spanBytes": 1844,
            "bodySha256": "9868eee8cddc41aae648fead87025f7a53b4d158dca963865dfd2126a0f9a829",
            "throughRetBytes": 0x72B,
            "throughRetSha256": "3fd25c103794771a322506815060f2203fc2ef5d4830252122bd4b654c76df31",
            "parameterLayout": parameter_layout,
            "relevantNativeLayouts": relevant_layouts,
            "entryGates": [
                {"offset": "0x98", "operation": "baseLineIndex = jobBaseLineList[index]"},
                {"offset": "0xa3", "condition": "baseLineFlags[baseLineIndex].Value & 0x01 != 0 (bit semantic is not named by this method)"},
                {"offset": "0xb4", "operation": "teamId = baseLineTeamIds[baseLineIndex]"},
                {"offset": "0xb9", "condition": "teamId != 0"},
                {"offset": "0x152", "call": "TeamData.get_IsEnable", "required": True},
                {"offset": "0x168", "call": "TeamData.get_IsCullingInvisible", "required": False},
                {"offset": "0x1f5", "operation": "baseLineDataStart = baseLineStartIndices[baseLineIndex] + team.baseLineDataChunk.startIndex"},
                {"offset": "0x206", "operation": "baseLineEntryCount = baseLineDataCounts[baseLineIndex]"},
                {"offset": "0x20b", "condition": "baseLineEntryCount != 0"},
            ],
            "childIndexEncoding": {
                "readOffset": "0x27f",
                "packedType": "System.UInt32",
                "childCount": "packed >> 20 (upper 12 bits)",
                "localStart": "packed & 0x000fffff (lower 20 bits)",
                "absoluteStart": "localStart + team.proxyVertexChildDataChunk.startIndex",
                "childVertex": "childDataArray[absoluteStart + childOrdinal] + team.proxyCommonChunk.startIndex",
            },
            "outerTraversal": {
                "loopOffsets": ["0x245", "0x6cf"],
                "parentVertex": "baseLineData[baseLineDataStart + baseLineOrdinal] + team.proxyCommonChunk.startIndex",
                "parentPosition": "positions[parentVertex] (double3)",
                "parentRotation": "rotations[parentVertex] (quaternion, loaded once before its child loop)",
                "parentAttribute": "attributes[parentVertex].Value",
                "zeroChildBranch": "packed childCount == 0 skips this parent without a rotation write",
            },
            "childTraversal": {
                "loopOffsets": ["0x2f0", "0x61d"],
                "restVector": "double3(math.mul(parentRotation, vertexLocalPositions[childVertex] * team.negativeScaleDirection))",
                "restSum": "restSum + restVector for every child; restSum starts at double3.zero for each parentVertex",
                "parentDirectionSumInitial": "double3.zero for each parentVertex",
                "childDirectionMoveBranch": "if attributes[childVertex].Value & VertexAttribute.Flag_Move (0x02) != 0: childDirection = positions[childVertex] - parentPosition",
                "moveBitSemanticEvidence": is_move,
                "childDirectionNonMoveBranch": "otherwise: childDirection = restVector",
                "parentDirectionSum": "parentDirectionSum += childDirection after selecting the per-child value",
                "parentDirectionSumCallOffsets": {
                    "nonMoveBranch": "0x460",
                    "moveBranch": "0x4e4",
                },
                "childFromTo": "MathUtility.FromToRotation(restVector, childDirection, 1.0)",
                "childFromToCallOffset": "0x548",
                "signedLocalRotation": "quaternion(vertexLocalRotations[childVertex].value * team.negativeScaleQuaternionValue)",
                "childRotationWrite": "rotations[childVertex] = math.mul(math.mul(parentRotation, signedLocalRotation), childFromTo)",
                "writeOffsets": ["0x5f1", "0x5fe"],
            },
            "parentRotationWrite": {
                "condition": "at least one child was traversed for parentVertex",
                "interpolation": "attributes[parentVertex].Value & VertexAttribute.Flag_Move (0x02) != 0 ? parameter.rotationalInterpolation : parameter.rootRotation",
                "parentFromTo": "MathUtility.FromToRotation(restSum, parentDirectionSum, interpolation)",
                "write": "rotations[parentVertex] = math.mul(parentFromTo, parentRotation)",
                "writeOffsets": ["0x62c", "0x6b8"],
            },
            "helperSpans": helper_spans,
            "fromToRotation": {
                "methodIdentity": from_to,
                "managedUnpatchedEquation": [
                    "u = math.normalize(from); v = math.normalize(to)",
                    "dot = math.clamp(math.dot(u, v), -1.0, 1.0); angle = acos(dot); axis = math.cross(u, v)",
                    "if abs(dot + 1.0) < epsilon: angle = pi; reference = (0,1,0) when u.x > u.y and u.x > u.z, otherwise (1,0,0); axis = math.cross(u, reference)",
                    "else if abs(1.0 - dot) < epsilon: return quaternion.identity",
                    "axis = math.normalize(axis); return quaternion.AxisAngle(float3(axis), float(angle * t))",
                ],
                "constants": {"epsilon": 9.999999974752427e-07,
                              "pi": 3.1415927410125732,
                              "sourceBytes": constant_rows},
                "degeneracyBranches": {
                    "antiparallel": "abs(dot + 1.0) < epsilon selects a deterministic perpendicular axis and pi before t scaling",
                    "parallel": "abs(1.0 - dot) < epsilon returns quaternion.identity without normalizing the zero cross product",
                    "zeroOrNonFiniteInput": "no explicit guard exists before the two unconditional input normalizations; output is not claimed for zero/non-finite input",
                },
                "ifixRoute": {
                    "patchId": "0x219",
                    "patchSlot": 0,
                    "isPatchedMethodIndex": 387384,
                    "getPatchMethodIndex": 387383,
                    "dynamicWrapperMethodIndex": 386959,
                    "dynamicWrapper": "IFix.ILFixDynamicMethodWrapper.__Gen_Wrap_178",
                    "installedLocalSnapshot": "sources.installedLocalIfix",
                    "localBootstrap": {
                        "wrapperType": ifix_usage_type,
                        "wrapperArrayFieldIndex": IFIX_WRAPPER_BOOTSTRAP[
                            "wrapperArrayFieldIndex"
                        ],
                        "wrapperArrayCctor": ifix_cctor,
                        "initialArrayLength": 0,
                        "getPatch": ifix_get_patch,
                        "isPatched": ifix_is_patched,
                        "slotPredicate": (
                            "id is in range and wrapperArray[id] is non-null"
                        ),
                        "installedLocalOutcome": (
                            "The BeyondDynamicBone wrapper array starts empty, and the "
                            "only hash-pinned installed local payload uses the "
                            "Gameplay.Beyond bridge with no BeyondDynamicBone target."
                        ),
                        "runtimeBoundary": (
                            "InitWrapperArray or another later, remote, or memory-only "
                            "load can still replace/populate the live array."
                        ),
                    },
                    "selectedAtRuntime": "unresolved",
                },
            },
            "writes": ["rotations[childVertex]", "rotations[parentVertex]"],
            "normalTangentNamingBoundary": "Despite the method name, method 384856 has no normal/tangent output array. Code proves the rest/direction vectors and quaternion writes above; it does not name either vector as a separately stored normal or tangent.",
            "readOnlyInputs": [
                "jobBaseLineList", "teamDataArray", "parameterArray", "attributes",
                "positions", "vertexLocalPositions", "vertexLocalRotations",
                "childIndexArray", "childDataArray", "baseLineFlags",
                "baseLineTeamIds", "baseLineStartIndices", "baseLineDataCounts",
                "baseLineData", "index",
            ],
            "unusedParameters": ["parentIndices"],
            "numericBoundary": "The pinned unpatched managed-worker traversal/equations, generated DirectCall managed fallback, and exact dual-CPU Burst target are closed. Overall runtime numerics remain fail-closed until the selected Burst/managed branch, cross-frame/managed route, and managed-route FromToRotation IFix patch state are proven.",
        },
        "calcLineBurstNumerics": {
            "source": "sources.dependencies.calcLineBurstNumerics",
            "equations": dependencies["calcLineBurstNumerics"]["equations"],
            "degeneracy": dependencies["calcLineBurstNumerics"]["degeneracy"],
            "classification": (
                "Both pinned CPU cores match the source-only transcription bit for "
                "bit across parallel, quarter-turn, antiparallel, non-move, "
                "multi-child, empty-child, and zero-axis branch cases."
            ),
            "runtimeBoundary": (
                "This closes Burst-core numerics, not the branch selected by retail. "
                "A selected managed route can still enter live IFix patch 0x219."
            ),
        },
        "calcLineDirectCallRoute": {
            "classification": "Method 384854 is a thin generated argument-forwarding wrapper. It contains no line traversal or vector/quaternion math and calls BurstDirectCall.Invoke method 384867.",
            "kernelWrapper": {
                **calc_line_kernel,
                "instructionCount": 55,
                "invokeCallOffset": "0x10a",
                "invokeMethodIndex": 384867,
            },
            "generatedMethods": direct_call_methods,
            "staticInitialization": {
                "typeInitializer": direct_call_cctor,
                "constructor": direct_call_ctor,
                "operation": (
                    "The type initializer enters Constructor; Constructor calls "
                    "BurstCompiler.CompileILPPMethod2 and stores its return in the "
                    "DirectCall DeferredCompilation field. The first pointer lookup "
                    "passes that value to GetILPPMethodFunctionPointer2 and stores "
                    "the normal return in DirectCall.Pointer."
                ),
                "runtimeBoundary": (
                    "The exact value produced by CompileILPPMethod2 and whether "
                    "initialization completes normally remain runtime state."
                ),
            },
            "invokeSelection": {
                "burstEnabledGate": {
                    **burst_is_enabled,
                    "startVa": "0x18307b8d0",
                    "spanBytes": 0x66,
                    "bodySha256": "7ede93cde144cea0e1a57122cafa2c367eda826992de1cc6e93eb55386d2db67",
                    "invokeCallOffset": "0x59",
                    "falseBranch": "directCallManagedFallback",
                    "semantics": (
                        "returns BurstCompiler._IsEnabled && "
                        "BurstCompilerHelper.IsBurstGenerated"
                    ),
                    "initialization": {
                        "burstCompilerTypeInitializer": burst_compiler_cctor,
                        "optionsConstructor": options_ctor,
                        "enableSetter": options_set_enabled,
                        "optionsTypeInitializer": options_cctor,
                        "secondaryProcessPredicate": {
                            **check_secondary,
                            "startVa": f"0x{BURST_RUNTIME_SELECTION['checkSecondaryStartVa']:x}",
                            "throughRetBytes": BURST_RUNTIME_SELECTION[
                                "checkSecondaryThroughRetBytes"
                            ],
                            "throughRetSha256": BURST_RUNTIME_SELECTION[
                                "checkSecondaryThroughRetSha256"
                            ],
                            "pinnedReturn": False,
                        },
                        "metadataUsageTypes": burst_usage_types,
                        "recognizedInputs": burst_disable_inputs,
                        "conditionalDefault": (
                            "BurstCompiler constructs global Options(true). The setter "
                            "publishes true unless ForceDisableBurstCompilation is set; "
                            "the pinned secondary-process predicate returns false."
                        ),
                        "forceDisableSources": (
                            "the exact --burst-disable-compilation command-line token "
                            "or a non-empty, non-'0' UNITY_BURST_DISABLE_COMPILATION "
                            "environment value"
                        ),
                    },
                    "runtimeValue": "unresolved",
                    "runtimeBoundary": (
                        "The process command line/environment, the exact async "
                        "BurstCompilerService result recorded in "
                        "burstRuntimeSelectionEvidence, and any later public Options "
                        "mutation are not serialized in the pinned inputs."
                    ),
                },
                "getFunctionPointer": {
                    "methodIndex": 384863,
                    "invokeCallOffset": "0x74",
                    "resolver": {
                        **burst_get_ilpp,
                        "startVa": "0x18474f6f0",
                        "spanBytes": BURST_RUNTIME_SELECTION["getIlppSpanBytes"],
                        "bodySha256": BURST_RUNTIME_SELECTION["getIlppBodySha256"],
                        "getFunctionPointerDiscardCallOffset": "0xb5",
                        "semantics": (
                            "null-checks all three arguments, then returns the first "
                            "argument unchanged"
                        ),
                    },
                    "nullBranch": "directCallManagedFallback",
                    "nonNullBranch": "indirect call through r10 at Invoke offset 0x13b",
                    "normalReturnNonNull": True,
                    "normalReturnIdentity": (
                        "the DirectCall DeferredCompilation/Pointer value passed as "
                        "the resolver's first argument"
                    ),
                    "nullBranchBoundary": (
                        "The emitted null branch exists, but it is unreachable after "
                        "a normal resolver return: a null first argument throws before "
                        "returning rather than selecting the managed fallback."
                    ),
                },
                "managedFallbackCallOffset": "0x202",
                "operation": (
                    "BurstCompiler.get_IsEnabled false selects the managed fallback. "
                    "When it is true, a normal GetFunctionPointer resolver return is "
                    "provably non-null and reaches the indirect call; a null resolver "
                    "input throws instead of returning null."
                ),
            },
            "directCallManagedFallback": {
                "startVa": f"0x{CALC_LINE_DIRECT_CALL['fallbackStartVa']:x}",
                "metadataMethodIdentity": None,
                "identityBoundary": "This internal target is not a registered IL2CPP method pointer; its role is established by the exact method-384867 fallback call edge.",
                "spanBytes": CALC_LINE_DIRECT_CALL["fallbackSpanBytes"],
                "bodySha256": CALC_LINE_DIRECT_CALL["fallbackBodySha256"],
                "throughRetBytes": CALC_LINE_DIRECT_CALL["fallbackThroughRetBytes"],
                "throughRetSha256": CALC_LINE_DIRECT_CALL["fallbackThroughRetSha256"],
            },
            "managedFallbackComparison": {
                "managedMethodIndex": 384856,
                "classification": "separately emitted numeric body statically equivalent to method 384856 modulo stack/local layout",
                "throughFirstRetInstructionCount": 396,
                "identicalMnemonicSequence": True,
                "identicalOperandStructuralShapes": True,
                "conditionalAndUnconditionalBranchCount": 18,
                "identicalControlFlowTopologyByInstructionOrdinal": True,
                "directCallCount": len(equivalent_calls),
                "identicalDirectCallTargetsAtSameInstructionOrdinals": True,
                "pairedDirectCalls": equivalent_calls,
                "nonControlImmediateComparison": {
                    "allEqualExcept": "stack frame allocation",
                    "managedWorkerFrameBytes": "0x7c0",
                    "directCallFallbackFrameBytes": "0x7b0",
                    "numericConstantDifferenceObserved": False,
                },
                "boundary": "Stack/local displacement changes do not alter the recovered traversal, branch topology, helper targets, or numeric constants. The sibling Burst contract separately identifies the non-null target; this comparison does not prove which route was selected at runtime.",
            },
            "selectedRuntimeRoute": "unresolved",
            "burstFunctionPointerTarget": dependencies["calcLineBurstExport"]["target"],
        },
        "routeEvidence": {
            "coldSpans": cold,
            "installedLocalIfix": "sources.installedLocalIfix",
            "classification": "Both parallel/cross-frame scheduling helpers and managed-worker fallback paths are present. The CalcLine managed fallback, exact Burst target, GetILPP normal-return identity/non-nullability, conditional Burst default, exact helper delegate/service chain, empty BeyondDynamicBone IFix bootstrap, and installed-local payload absence are statically closed. The process inputs, async compiler-service result, later Options mutation, and live IFix slot ownership remain runtime values.",
        },
        "workerTargets": workers,
        "nextDisassemblyTargets": [],
        "remainingRuntimeEvidence": [
            {"boundary": "CalcLine BurstDirectCall selected route",
             "reason": "GetILPPMethodFunctionPointer2 normal-return identity/non-nullability, the conditional Burst default, and the helper's exact delegate/service/non-null chain are closed, but the actual process inputs, async compiler-service return, later Options mutation, and CompileILPPMethod2 completion/value remain runtime state"},
            {"boundary": "MathUtility.FromToRotation IFix patch 0x219 selection",
             "reason": "the BeyondDynamicBone wrapper array starts empty and the exact installed local Gameplay.Beyond payload has no BeyondDynamicBone target; InitWrapperArray and later, remote, or memory-only loaders leave live slot ownership external runtime state"},
        ],
        "nonClaims": [
            "The older 80-bone capture is not an implementation input and supplies no positions, timing, curves, or fitted constants.",
            "The exact DirectCall managed fallback and non-null Burst target identities do not establish which branch retail selected on a particular frame.",
            "The empty BeyondDynamicBone bootstrap and parsed installed local IFix absence do not establish that patch id 0x219 was absent after later runtime loading.",
            "parentIndices is present in the job ABI but is not read by method 384856. baseLineFlags is read only for the entry bit-0 gate; no stronger bit semantic is inferred.",
            "The presence of multiple schedule/fallback helpers does not establish which runtime branch is selected.",
            "This static contract is not a Unity execution or retail-equivalence result.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--metadata-evidence", type=Path, default=DEFAULT_METADATA_EVIDENCE)
    parser.add_argument("--native-evidence", type=Path, default=DEFAULT_NATIVE_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_contract(game_assembly=args.game_assembly, metadata=args.metadata,
                             metadata_evidence=args.metadata_evidence, native_evidence=args.native_evidence)
    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == encoded
        print(json.dumps({"status": payload["status"], "matches": matches, "output": str(args.output)}))
        return 0 if matches else 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError, KeyError, IndexError, StopIteration) as exc:
        print(f"secondary dynamics PostProxy unavailable: {exc}", file=sys.stderr)
        raise SystemExit(2)
