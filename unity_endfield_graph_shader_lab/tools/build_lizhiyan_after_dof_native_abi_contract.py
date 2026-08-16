#!/usr/bin/env python3
"""Pin Li Zhiyan's current-build after-DOF native scheduling/ABI boundary."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
OUTPUT = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/"
    "LiZhiyanOverviewFinger/lizhiyan_after_dof_native_abi.json"
)
SHADER_CONTRACT = OUTPUT.with_name("lizhiyan_overview_vfxbasev2_variants.json")
VIEWER_SCENE = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/"
    "CharacterRecoveryViewer.unity"
)
CODE_REGISTRATION = 0x18B9217D0
EXPECTED = {
    "gameAssembly": "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE",
    "metadata": "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E",
    "unityPlayer": "B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2",
    "shaderContract": "1191F96B45FD11C47D31C71681B25E77B3DF2CBD2179F21B4D2854D3AD90796B",
    "viewerScene": "BC9F4FBF023F76FFD06AB2AE6283A03127027A83049DB580C9678B2A7B633761",
}
METHODS = [
    (286728, "HG.Rendering.Runtime.HGCamera",
     ".ctor", 0x1837DD570, 0x1837DDD44,
     "00ACC65F4685738CB190BF536900D5AE7B421F4A2CAEDC25C3D2D0B7E2EB3162"),
    (286732, "HG.Rendering.Runtime.HGCamera",
     "DoECSCullingCPP", 0x1834502D0, 0x1834503CE,
     "56CC43CF0F18122D3DE44731D2680F6951F48104A5A2986B9F35161CC883EC7F"),
    (286733, "HG.Rendering.Runtime.HGCamera",
     "DoECSCulling", 0x189B721CC, 0x189B72A1D,
     "ECD06129C7B75CF85A127A5D5E543C956CC9FA4B23C1846A893CAE9464A3AD3E"),
    (286724, "HG.Rendering.Runtime.HGCamera",
     "get_screenCullingLayerMask", 0x183E68CB0, 0x183E68CD4,
     "0D5928FA5F343C7F072A857C5B0FE6CA8943506877C71FA9A6257EF5F2983B7E"),
    (286739, "HG.Rendering.Runtime.HGCamera",
     "Update", 0x183100120, 0x183100171,
     "B5A2AB43A40014751793CA227CD2F535AEF7470A1F3E71A93B24297ED9C40FCC"),
    (286740, "HG.Rendering.Runtime.HGCamera",
     "BeginRender", 0x189B720E0, 0x189B72162,
     "525783A3D1731620269FBA6F156031EFDE5068FFA4ACC3FAFD1B4EFD0EA0948F"),
    (286741, "HG.Rendering.Runtime.HGCamera",
     "UpdateAllViewConstants", 0x189B74308, 0x189B74387,
     "88DFB9FB0D8B0B867A507E41AB2123C6E2830262290A1AB10616FD3A55DA2421"),
    (284150, "HG.Rendering.Runtime.HGRenderPipeline",
     "GetPerObjectMotionVectorConfig", 0x189BC753C, 0x189BC759B,
     "DA8AB25AC903EEAE24FED48535F016BEA19C3BE7A21A7628C67BED63C7C83922"),
    (284093, "HG.Rendering.Runtime.HGRenderPipeline",
     ".ctor", 0x183947230, 0x1839488E2,
     "B0D85048FC518253694C8BD1FC9B9F40C7F14DAA87B95EB180419233B28DD59D"),
    (284103, "HG.Rendering.Runtime.HGRenderPipeline",
     "ConfigureKeywords", 0x189BC6A38, 0x189BC6B7E,
     "BD2E3852A86737D9F2732283AF677FA2A0F4209DD3FFB3F9476C957C67125A10"),
    (284106, "HG.Rendering.Runtime.HGRenderPipeline",
     "Render", 0x183455030, 0x18345A6E4,
     "08CA0296209FB21E02AFC9E2F5B02B06F0CA86A699A26BCD9951099D93F6926A"),
    (284111, "HG.Rendering.Runtime.HGRenderPipeline",
     "ExecuteRenderRequestCPP", 0x183106970, 0x183113581,
     "6EFA8CEFFB982A2B6E4944B79DDDEBD5853166DC3B7CD0A10E8188048E27A6E0"),
    (286702, "HG.Rendering.Runtime.HGCamera",
     "get_enableMV", 0x189B74654, 0x189B7469F,
     "8C1488DC4A09BEB9F142B4EA2DD5CB7B98770D5DE48DA545E94655EE3538B329"),
    (287999, "HG.Rendering.Runtime.HGRenderPathDeferred",
     "OnPreRendering", 0x189BF6CBC, 0x189BF7A9D,
     "E1E497BAD2F5AA44B25F7E6D0F7ECA208CD81F4C49AE8D64070A4FB1D0E6187A"),
    (478062, "UnityEngine.HyperGryph.HGMeshRender",
     "CreateRendererList", 0x18B3FA0A4, 0x18B3FA10F,
     "8C8113556AB580A5337118F93A8B5E7A38BD79A8F656128FE768CF22B727261F"),
    (288027, "HG.Rendering.Runtime.HGRenderPathScene",
     ".ctor", 0x182ED94E0, 0x182ED991D,
     "C0D8BACD8084FAA9D608A95C2F56076A9FBC3FB57AB450AA8A2F403614C11E98"),
    (288006, "HG.Rendering.Runtime.HGRenderPathForward",
     "OnPreRendering", 0x189BF7BDC, 0x189BF7F2B,
     "499191DAF06A7B6985A8684B1435D6CC8DA7ECEA1A3C0623CFBAF8EC671ABCD5"),
    (287274, "HG.Rendering.Runtime.ForwardPassUtils",
     "PrepareAfterDOFTranparentRendererList", 0x189BAB274, 0x189BAB4E2,
     "319799A95260B1717084D16AA8C2E0CCAD668CEDF3E52E9465B99A31EC44A5E0"),
    (287316, "HG.Rendering.Runtime.TransparentAfterDOFPassConstructor",
     "ConstructPass", 0x189BB2E40, 0x189BB346A,
     "D54DCF38AC17E6062573C476BF988FF8CBEE70E89F2B02FB341E5588DA3612CC"),
    (288038, "HG.Rendering.Runtime.HGRenderPathScene",
     "RenderPostProcessPhase1", 0x189BFFEB0, 0x189C009EF,
     "4695B2B6C39CB3522C067976FCC2F2677BC94692382C5611EF9E2EA743F145C5"),
    (287324, "HG.Rendering.Runtime.TransparentAfterDOFPassConstructor+<>c",
     "<.cctor>b__10_0", 0x189BB5264, 0x189BB558A,
     "D49C4DE691A7B65184532D8C9E46E1209F35AF2A76C0E23FA82B8E35593011CC"),
    (288225, "HG.Rendering.Runtime.HGRendererListUtils",
     "RenderForwardRendererList", 0x189C0A6EC, 0x189C0A7CC,
     "76DC5D1B4730F4A5BB937F3776A776DE2A8E960B4BB4A47B983BA5F264555879"),
    (288226, "HG.Rendering.Runtime.HGRendererListUtils",
     "RenderForwardECSRendererList", 0x189C0A628, 0x189C0A6EA,
     "BBA699B59C1081CDF6870E95B3B17469DD0D8791234E166D1D403D85786E6F42"),
    (288241, "HG.Rendering.Runtime.HGRendererListUtils",
     "CreateTransparentRendererListDesc", 0x189C08904, 0x189C08BC8,
     "08E90A05982967C1F0AA45950FDF24F069FA6B639238EE3F6429FEF2DE697163"),
]
CALLS = [
    (0x189BAB3C2, 0x189C08904, "PrepareAfterDOF -> CreateTransparentRendererListDesc"),
    (0x189BB3299, 0x189BAB274, "ConstructPass -> PrepareAfterDOFTranparentRendererList"),
    (0x189BB332B, 0x189B2AB5C, "ConstructPass -> CreateRendererList"),
    (0x189BB334B, 0x189B36820, "ConstructPass -> UseRendererList"),
    (0x189BB54F1, 0x189C0A6EC, "callback -> RenderForwardRendererList"),
    (0x189BB5541, 0x189C0A628, "callback -> RenderForwardECSRendererList"),
    (0x189BB5401, 0x18B2DE0CC, "callback -> DrawFullScreen"),
    (0x189C08967, 0x1832512C0, "CreateTransparentRendererListDesc -> Camera.get_cullingMask"),
    (0x189C0897E, 0x189B736B0, "CreateTransparentRendererListDesc -> RemoveWorldUILayer"),
    (0x189C089A4, 0x18B3F4A7C, "CreateTransparentRendererListDesc -> RendererListDesc.ctor"),
    (0x189C0057C, 0x183E68CB0, "Phase1 -> HGCamera.get_screenCullingLayerMask"),
    (0x189C00740, 0x189BB2E40, "Phase1 -> TransparentAfterDOF.ConstructPass"),
    (0x189BF7684, 0x189B73644, "Deferred.OnPreRendering -> RemoveWorldUILayer(-1)"),
    (0x189BF7823, 0x189B7470C, "Deferred.OnPreRendering -> get_enableTransparentAfterDOF"),
    (0x189BF789F, 0x18B3FA0A4, "Deferred.OnPreRendering -> CreateRendererList(TransparentAfterPP)"),
]


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(game_root: Path) -> dict[str, Any]:
    game_assembly = game_root / "GameAssembly.dll"
    unity_player = game_root / "UnityPlayer.dll"
    metadata = game_root / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
    for key, path in (("gameAssembly", game_assembly), ("metadata", metadata),
                      ("unityPlayer", unity_player)):
        require(path.is_file(), f"missing explicitly selected native input: {path}")
        require(sha256(path) == EXPECTED[key], f"selected native input drifted: {key}")
    require(sha256(SHADER_CONTRACT) == EXPECTED["shaderContract"],
            "Li Zhiyan shader ABI contract drifted")
    require(sha256(VIEWER_SCENE) == EXPECTED["viewerScene"],
            "selected CharacterRecoveryViewer scene drifted")
    viewer_text = VIEWER_SCENE.read_text(encoding="utf-8")
    require("--- !u!20 &1562276706" in viewer_text and
            "m_Bits: 4294967295" in viewer_text,
            "selected viewer camera identity/culling mask drifted")

    metadata_module = load_module(
        "lizhiyan_after_dof_metadata",
        REPO / "tools/endfield-il2cpp/catalog_option_flow_metadata.py")
    mapper = load_module(
        "lizhiyan_after_dof_mapper",
        REPO / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py")
    md = metadata_module.Metadata(metadata)
    pe = mapper.PeImage(game_assembly)
    unity_pe = mapper.PeImage(unity_player)
    modules = mapper.parse_codegen_modules(pe, CODE_REGISTRATION)
    image_ranges = mapper.image_method_ranges(md)
    pointers, _ = mapper.build_pointer_indexes(pe, md, modules, image_ranges)

    pdata = next(section for section in pe.sections if section["name"] == ".pdata")
    function_ends: dict[int, int] = {}
    for pos in range(pdata["rawPointer"], pdata["rawPointer"] + pdata["rawSize"] - 11, 12):
        begin_rva, end_rva, _ = struct.unpack_from("<III", pe.buf, pos)
        if begin_rva and end_rva > begin_rva:
            function_ends[pe.image_base + begin_rva] = pe.image_base + end_rva

    methods = []
    for index, expected_type, expected_name, expected_va, expected_end, expected_hash in METHODS:
        method = md.methods[index]
        owner = md.types[method.declaring_type]
        require(md.type_full_name(owner) == expected_type, f"method owner drift: {index}")
        require(md.string(method.name_index) == expected_name, f"method name drift: {index}")
        image = next(row for row in md.images
                     if row.type_start <= owner.index < row.type_start + row.type_count)
        image_name = md.string(image.name_index)
        va = pointers[image_name][index - image_ranges[image_name]["methodStart"]]
        require(va == expected_va and function_ends.get(va) == expected_end,
                f"method function span drift: {index}")
        body = pe.bytes_at_va(va, expected_end - va)
        body_hash = hashlib.sha256(body).hexdigest().upper()
        require(body_hash == expected_hash, f"method body drift: {index}")
        methods.append({
            "methodIndex": index,
            "type": expected_type,
            "name": expected_name,
            "token": f"0x{method.token:08x}",
            "va": f"0x{va:x}",
            "functionEnd": f"0x{expected_end:x}",
            "functionBytes": len(body),
            "functionSha256": body_hash,
        })

    calls = []
    for callsite, expected_target, label in CALLS:
        data = pe.bytes_at_va(callsite, 5)
        require(len(data) == 5 and data[0] == 0xE8, f"missing rel32 call: {label}")
        target = callsite + 5 + struct.unpack_from("<i", data, 1)[0]
        require(target == expected_target, f"call target drift: {label}")
        calls.append({"label": label, "callsite": f"0x{callsite:x}",
                      "target": f"0x{target:x}"})

    unity_native_spans = [
        ("HGMeshRender.CreateRendererList icall adapter", 0x1801F1E40, 0x1801F1F0E,
         "EB9B02F891CD670E726D8EF73C52D62D40FDC6756BE41BCE76ED8EA901AC153C"),
        ("HGMeshRender renderer-list request packer", 0x18104E7A0, 0x18104E856,
         "8125E686DC149173B7CB2A9FF3D0BA40E41162E72E1D9BC4353BD211ECAF1C7E"),
        ("HGMeshRender renderer-list registration core", 0x18104E300, 0x18104E7A0,
         "9FC913F47D5E88710E13D9C555F2C81F7DAAEBA22C6AEB22F2FAA969170ACC80"),
        ("HGMeshRender renderer-list resource record builder", 0x18104E920, 0x18104EC17,
         "02F2E295CF8BB8247824AA7A3EE6B4E0BAD7D58C1C06D59ECD155CAB6E3C81BD"),
    ]
    unity_native_methods = []
    for label, va, end, expected_hash in unity_native_spans:
        body = unity_pe.bytes_at_va(va, end - va)
        body_hash = hashlib.sha256(body).hexdigest().upper()
        require(body_hash == expected_hash, f"UnityPlayer native span drifted: {label}")
        unity_native_methods.append({"label": label, "va": f"0x{va:x}",
                                     "functionEnd": f"0x{end:x}",
                                     "functionBytes": len(body),
                                     "functionSha256": body_hash})

    shader = json.loads(SHADER_CONTRACT.read_text(encoding="utf-8"))
    return {
        "schema": "endfield.lizhiyan-after-dof-native-abi.v1",
        "status": "current_build_native_schedule_and_static_shader_abi_closed_live_draw_pending",
        "sources": {
            "gameAssembly": {"path": str(game_assembly), "sha256": EXPECTED["gameAssembly"]},
            "metadata": {"path": str(metadata), "sha256": EXPECTED["metadata"]},
            "unityPlayer": {"path": str(unity_player), "sha256": EXPECTED["unityPlayer"]},
            "shaderContract": {"path": SHADER_CONTRACT.relative_to(REPO).as_posix(),
                               "sha256": EXPECTED["shaderContract"]},
            "viewerScene": {"path": VIEWER_SCENE.relative_to(REPO).as_posix(),
                            "sha256": EXPECTED["viewerScene"]},
        },
        "codeRegistrationVA": f"0x{CODE_REGISTRATION:x}",
        "methods": methods,
        "unityPlayerNativeMethods": unity_native_methods,
        "decisiveCalls": calls,
        "rendererList": {
            "queue": {"first": 3660, "default": 3700, "last": 3740},
            "sortingCriteria": 87,
            "sortingSemantic": "CommonTransparent | OptimizeStateChanges | RendererPriority",
            "shaderTagsWithoutOutline": ["TransparentBackface", "ForwardOnly", "Forward",
                                          "ForwardCharacterOnly", "SRPDefaultUnlit", "Distortion"],
            "layerMask": "RemoveWorldUILayer(camera.cullingMask)",
            "stateBlock": {"hasValue": False, "source": "zero-initialized nullable"},
            "overrideMaterial": None,
            "excludeObjectMotionVectors": False,
            "perObjectData": {
                "bakedLightingConfig": 15,
                "motionVectorConfigForNonNullHGCamera": 32,
                "combined": 47,
                "expression": "m_CurrentRendererConfigurationBakedLighting | GetPerObjectMotionVectorConfig(hgCamera)",
                "normalBranchEvidence": "pipeline ctor and ConfigureKeywords write 15; get_enableMV returns true; motion helper returns 32",
                "ifixBoundary": "patch ids 568, 462, and 463 can replace the normal branches",
            },
            "screenCulling": {
                "constructorDefaults": {"ratio": 0.005, "distance": 30.0},
                "hgCameraOffsets": {"ratio": "0x9d8", "distance": "0x9dc", "layerMask": "0xa20"},
                "layerNames": ["Default", "TransparentFX", "Ignore Raycast", "Water", "UI",
                               "Walkable", "Climbable", "Trigger", "UIPP", "UIModel", "Building",
                               "UIInteract", "WorldUI", "Projectile", "AbilityEntity", "Terrain", "IK"],
                "layerMaskConstruction": "lazy LayerMask.GetMask of the 17 names",
                "ratioDistanceWriters": "HGCamera..ctor only among mapped HG.RenderPipelines.Runtime methods",
                "layerMaskWriters": [
                    "HGCamera..ctor initializes 0xffffffff",
                    "HGCamera.DoECSCullingCPP copies lightweight-camera results +0x168/+0x16c",
                    "HGCamera.DoECSCulling rewrites current/lightweight camera masks",
                    "HGRenderPipeline.Render propagates lightweight-camera results",
                ],
                "requestPropagation": "ExecuteRenderRequestCPP copies ratio/distance to request +0x68/+0x6c, then reads the layer-mask getter",
                "descriptorBoundary": "values travel through custom request/PassInput data; ordinary Unity RendererListDesc has no equivalent fields",
                "runtimeInstanceValues": "pending selected-camera observation; layer mask is runtime-mutated and cannot be assumed to remain 0xffffffff",
                "unityEquivalent": "standard DrawRenderers exposes no HG screen-culling fields",
            },
            "passInputOffsets": {
                "characterOutlineEnabled": "0x00",
                "forwardTransparentAfterDOFECSList": "0x04",
                "screenCullingLayerMask": "0x08",
                "screenCullingRatio": "0x0c",
                "screenCullingRatioDistance": "0x10",
                "bakedLightConfig": "0x14",
                "shadowResult": "0x18",
                "cullingResults": "0x58",
                "sceneColor": "0x68",
                "sceneDepth": "0x78",
                "sceneMV": "0x88",
                "hgrp": "0x98",
                "bytes": 160,
            },
            "ecsRendererListProducer": {
                "owner": "HGRenderPathDeferred.OnPreRendering",
                "field": "m_forwardTransparentAfterDOFECSList",
                "fieldOffset": "0x1388",
                "handleType": "System.UInt32",
                "constructorSentinelWriteVA": "0x182ed9507",
                "validGate": "HGGraphicsFeatureManager.forwardTransparent.enabled && hgCamera.enableTransparentAfterDOF",
                "invalidSentinel": 4294967295,
                "createCallVA": "0x189bf789f",
                "createTargetVA": "0x18b3fa0a4",
                "viewHandle": "hgCamera.cullingViewHandle",
                "renderFlagsMask": "0x4400 (TransparentAfterPP | ShadowOnly)",
                "renderFlagsValue": "0x4000 (TransparentAfterPP)",
                "lightModeMask": "0x20e0 | (characterOutlineState << 9)",
                "globalKeywords": 0,
                "multiDraw": True,
                "transparentSorting": True,
                "cullingLayerMask": "HGCamera.RemoveWorldUILayer(0xffffffff)",
                "noAlphaTest": False,
                "excludeGPUDriven": False,
                "lifecycle": "recreated or reset to 0xffffffff by deferred OnPreRendering each camera frame",
                "phase1ReadVA": "0x189c00568",
                "forwardPath": "HGRenderPathForward.OnPreRendering creates ordinary transparent/opaque/pre-Z lists but never writes 0x1388 or creates a 0x4400/0x4000 AfterPP list",
                "nativeAdapter": {
                    "icallSignature": "UnityEngine.HyperGryph.HGMeshRender::CreateRendererList(System.UInt32,System.UInt32,System.UInt32,System.UInt32,System.UInt16,System.IntPtr,System.Boolean,System.Boolean,System.UInt32,System.Boolean,System.UInt32*,System.Boolean)",
                    "registrationIndex": 395,
                    "unityPlayerVA": "0x1801f1e40",
                    "functionEnd": "0x1801f1f0e",
                    "functionBytes": 206,
                    "functionSha256": "EB9B02F891CD670E726D8EF73C52D62D40FDC6756BE41BCE76ED8EA901AC153C",
                    "requestPackerVA": "0x18104e7a0",
                    "registrationCoreVA": "0x18104e300",
                    "resourceRecordBuilderVA": "0x18104e920",
                    "behavior": "canonicalizes arguments, packs a 0x68-byte request, and registers a list handle; contains no entity iteration, survivor writes, sort loop, multi-draw dispatch, or final draw",
                    "handleTable": {
                        "vectorBaseOffset": "0x08",
                        "countOffset": "0x18",
                        "encodedCapacityOffset": "0x20",
                        "slotStride": 16,
                        "returnedHandle": "zero-based append index (old count)",
                        "slotIdOffset": "0x00",
                        "slotStatePointerOffset": "0x08",
                        "stateBytes": 48,
                        "stateCallbackVA": "0x1810398f0",
                    },
                    "invalidRequestGate": "request[0] == 0xffffffff returns 0xffffffff without appending",
                    "maskCombination": "view record +0x40/+0x48 OR request +0x50/+0x58",
                    "nextConsumerBoundary": "0x18106aae0 validates the index after AddDrawECSRendererList; survivor/order/lifetime remain downstream",
                },
            },
            "liveInputsPending": ["cullingResults", "camera", "screenCullingRatio",
                                  "screenCullingRatioDistance", "screenCullingLayerMask",
                                  "outlineEnabled", "screen-culling instance values",
                                  "survivorsAndSortOrder"],
        },
        "attachments": shader["renderScheduling"]["attachments"],
        "callbackExecution": ["profiling", "sceneColor/global texture setup", "fullscreen draw",
                              "forward renderer list", "forward ECS renderer list"],
        "rendererConsumers": {
            "opaqueArgument": False,
            "frameSettingsGate": "TransparentObjects",
            "classic": "CoreUtils.DrawRendererList(renderContext, cmd, rendererList)",
            "ecs": "HGMeshRender.DrawECSRendererList(cmd, rendererListHandle)",
            "consumerResortingOrOverride": "none; descriptor/list construction owns filtering and order",
            "survivorIdentity": "runtime renderer-list and ECS handles pending",
        },
        "shaderAbi": {
            "selectedMaterialGates": shader["selectedMaterialGates"],
            "variantCount": len(shader["variants"]),
            "constantBuffers": shader["variants"][0]["stages"]["fragment"]
                ["staticResourceSemantics"]["constantBuffers"],
            "variantResources": [
                {"materialKeywords": row["materialKeywords"],
                 "texturesAndSamplers": row["stages"]["fragment"]
                    ["staticResourceSemantics"]["texturesAndSamplers"]}
                for row in shader["variants"]
            ],
        },
        "nativeBoundary": {
            "callbackConstantBufferPublication": "not_present",
            "callbackGlobalVectorAndTexturePublication": "present",
            "serializedBindingsAreD3D12RootParameters": False,
            "pending": ["live descriptor-table handles", "root-parameter mapping",
                        "PSO overrides", "physical MRT/depth descriptors",
                        "feature-switch values", "renderer-list survivors/order",
                        "final compositing"],
        },
        "unityDecision": {
            "visibleAdmission": False,
            "vfxParams1PublicationRequiredForSelectedMaterials": False,
            "transformHistoryRequiredForSelectedMaterials": False,
            "reason": "all selected materials serialize _IsSceneEffect=0 and _EnableTransparentMV=0",
            "selectedViewerCamera": {
                "fileID": 1562276706,
                "unityCullingMask": 4294967295,
                "serializedHGScreenCullingOverrides": False,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", type=Path, required=True,
                        help="Explicit Endfield install root containing GameAssembly.dll")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(args.game_root.resolve()), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        require(OUTPUT.is_file() and OUTPUT.read_text(encoding="utf-8") == payload,
                "serialized native ABI contract drifted")
        print("Li Zhiyan after-DOF native ABI contract verified")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(payload, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}: sha256={sha256(OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
