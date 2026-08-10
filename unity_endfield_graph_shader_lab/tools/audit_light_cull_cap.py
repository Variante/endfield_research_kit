#!/usr/bin/env python3
"""Audit the installed retail punctual-light shortlist and cap contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
UNITY_PLAYER = GAME_ROOT / "UnityPlayer.dll"
GLOBAL_METADATA = GAME_ROOT / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
INIT_BUNDLE_CHUNK = (
    GAME_ROOT
    / "Endfield_Data/StreamingAssets/VFS/0CE8FA57/"
    "19F0903A12BA87C0D43E67E64889B525.chk"
)
HGRP_ROOT = (
    REPO_ROOT
    / "tools/FractalMiner/Assets/Project/EndField/HGRP/packages/"
    "com.hg.render-pipelines/runtime/HG/Rendering/Runtime"
)
DEVICE_TYPE_SOURCE = HGRP_ROOT / "HGDeviceType.cs"
SETTING_HUB_SOURCE = HGRP_ROOT / "HGRenderPipelineSettingHub.cs"
SETTING_PARAMETERS_SOURCE = HGRP_ROOT / "HGSettingParameters.cs"
LIGHT_CLUSTER_SOURCE = HGRP_ROOT / "LightClusteringPassConstructor.cs"
HG_CAMERA_SOURCE = HGRP_ROOT / "HGCamera.cs"
IFIX_STATE = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/installed_ifix_patch_state.json"
)
HGMESH_RENDERER_DATA_SOURCE = (
    GAME_ROOT
    / "Endfield_Data/StreamingAssets/VFS/7064D8E2/"
    "B428C352B17C75CA29122CAACC037A59.chk"
)
HGMESH_RENDERER_DATA_INVENTORY = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/hgmesh_renderer_data_component_inventory.json"
)
HGTREE_NATIVE_SERIALIZED_TYPE_CENSUS = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/hgtree_native_serialized_type_census.json"
)
STREAMING_SCENE_V2_PAYLOAD_CENSUS = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/streaming_scene_v2_payload_census.json"
)
ANIMESTUDIO_CLASS_ID_SOURCE = (
    REPO_ROOT / "tools/AnimeStudio/AnimeStudio/ClassIDType.cs"
)
ANIMESTUDIO_ASSET_HELPER_SOURCE = (
    REPO_ROOT / "tools/AnimeStudio/AnimeStudio/AssetsHelper.cs"
)
DEFAULT_EXTRACTED_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/light_cull_cap/"
    "text_assets_selected/TextAsset"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/light_cull_cap_recovery.json"
)

EXPECTED_HASHES = {
    "game_assembly": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    "unity_player": "b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2",
    "global_metadata": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    "init_bundle_chunk": "cbc87c7d8f41d90da25af7758cf77ced7321d19c52c067f6f77a75aa5dabc380",
    "device_type_source": "8cde77dfadb6b857ceb1dc5c92eec460cac1d49eb2ccbd948619699c69ed84b5",
    "setting_hub_source": "0ab0fd1fb0fa6aaa52a2acc2544503f7379487d96b47a31bcaf4e3d525f1b761",
    "setting_parameters_source": "0ea7d61931aa014fb7ebca149380da2804fc8d5e07705e941bf6474b74a55ce9",
    "light_cluster_source": "a81ef9843339141a86c910a6915ab96e647f1f43c25631d537fe872ef4ead888",
    "hg_camera_source": "2f0e098481f25f0e77de8d203c7cae1e4d748b4521d5157af0ab1aaa1163205a",
    "ifix_state": "b9ab981b65caa0b2a16d9603812c18236ad0aa5af255cb06614e7441cdef45d1",
    "hgmesh_renderer_data_source": "af62293a829675951bbc135b0ba51444f72c8b288a0043617ed0c4300c6feae0",
    "animestudio_class_id_source": "e14cbf9403b8da5c4004a9a441512ffa6b0745d52818ace6aec8bb8645ba8c17",
    "animestudio_asset_helper_source": "474c636209d2317abcc8c26ac3646cd2a9a13795fd2493e29ce26037451ee288",
    "do_ecs_culling_body": "bcbfa96588743701a5d1992256c68f193e624dc01ead47e86b80eb0a7653151b",
    "cull_lights_injected_body": "90fe3e38d69fd29a65c4fdc3e472199d9fa0e67733d220875cff6925b4f25503",
    "cull_lights_internal_body": "552b658de9533980b813706c457551aa508c0a2d0fa30dd9817a166898c73564",
    "cull_lights_body": "457b6e62ebd5b4aab211b552da8b3f22a8156c7005a88c21c65f223903ee7245",
    "get_visible_lights_body": "f2d8a942ff09c2a07ee960760bf7e3a2c9bd878955fd7bb0d709c3e1fca3ab66",
    "setup_state_body": "76dcba4f0f93db50a7fdbf2f3fed3084229be907526ff6a33c9556496a81ceab",
    "hgtree_component_get_id_body": "6786c0e7be3bc2cc01074e814543729b15cd696fdace27b19cf9c499e8df556c",
    "render_object_lod_info_component_get_id_body": "23334c82ef0133c65cc0394d318a2637276496cb9b99f6dd580d0ee4f6c9e7b5",
    "streaming_scene_manager_ctor_body": "788d972a2946b193ca9ca3835f11bca9f8c3bead6a2423a8c788d177c00785b3",
}

NATIVE_METHODS = {
    "do_ecs_culling": {
        "method": "HG.Rendering.Runtime.HGCamera.DoECSCulling",
        "methodIndex": 286733,
        "virtualAddress": 0x189B721CC,
        "fileOffset": 0x9B707CC,
        "sizeBytes": 0x854,
    },
    "cull_lights_injected": {
        "method": "UnityEngine.HyperGryph.HGCullingSystem.CullLightsInternal_Injected",
        "methodIndex": 407492,
        "virtualAddress": 0x18B3EA710,
        "fileOffset": 0xB3E8D10,
        "sizeBytes": 0x60,
    },
    "cull_lights_internal": {
        "method": "UnityEngine.HyperGryph.HGCullingSystem.CullLightsInternal",
        "methodIndex": 407488,
        "virtualAddress": 0x18B3EA770,
        "fileOffset": 0xB3E8D70,
        "sizeBytes": 0x2C,
    },
    "cull_lights": {
        "method": "UnityEngine.HyperGryph.HGCullingSystem.CullLights",
        "methodIndex": 407487,
        "virtualAddress": 0x18B3EA79C,
        "fileOffset": 0xB3E8D9C,
        "sizeBytes": 0x7C,
    },
    "get_visible_lights": {
        "method": "UnityEngine.HyperGryph.LightCullResult.get_visibleLights",
        "methodIndex": 407475,
        "virtualAddress": 0x18B3EABD8,
        "fileOffset": 0xB3E91D8,
        "sizeBytes": 0x2C,
    },
    "setup_state": {
        "method": "HG.Rendering.Runtime.LightClusteringPassConstructor.SetupState",
        "methodIndex": 285302,
        "virtualAddress": 0x189D09F50,
        "fileOffset": 0x9D08550,
        "sizeBytes": 0x3DC,
    },
    "hgtree_component_get_id": {
        "method": "UnityEngine.HyperGryph.ECS.HGTreeComponent.get_id",
        "methodIndex": 478429,
        "token": "0x06000279",
        "virtualAddress": 0x184DBCEC0,
        "fileOffset": 0x4DBB4C0,
        "sizeBytes": 0x6,
    },
    "render_object_lod_info_component_get_id": {
        "method": (
            "UnityEngine.HyperGryph.ECS."
            "RenderObjectLODInfoComponent.get_id"
        ),
        "methodIndex": 478390,
        "token": "0x06000252",
        "virtualAddress": 0x184D9EC60,
        "fileOffset": 0x4D9D260,
        "sizeBytes": 0x6,
    },
    "streaming_scene_manager_ctor": {
        "method": (
            "UnityEngine.HyperGryph.Streaming."
            "StreamingSceneManagerScript..ctor"
        ),
        "methodIndex": 762,
        "token": "0x060002FB",
        "virtualAddress": 0x18394A2F0,
        "fileOffset": 0x39488F0,
        "sizeBytes": 0x2F60,
    },
}

UNITY_ICALL_FUNCTION_TABLE_VA = 0x1820CC000
UNITY_ICALL_NAME_TABLE_VA = 0x1820D3DB0
UNITY_CULL_LIGHTS_ICALL_INDEX = 3320
UNITY_CULL_LIGHTS_ICALL_VA = 0x1800FBCE0
UNITY_CULL_LIGHTS_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGCullingSystem::CullLightsInternal_Injected"
)

UNITY_ADD_CULL_VIEW_ICALL_INDEX = 3304
UNITY_ADD_CULL_VIEW_ICALL_VA = 0x1800F9790
UNITY_ADD_CULL_VIEW_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGCullingSystem::AddCullViewByMatrix"
)

UNITY_PARENT_LOD_BIAS_GET_ICALL_INDEX = 3300
UNITY_PARENT_LOD_BIAS_GET_ICALL_VA = 0x1800F8E00
UNITY_PARENT_LOD_BIAS_GET_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGCullingSystem::get_parentLODBias"
)
UNITY_PARENT_LOD_BIAS_SET_ICALL_INDEX = 3301
UNITY_PARENT_LOD_BIAS_SET_ICALL_VA = 0x1800F8E40
UNITY_PARENT_LOD_BIAS_SET_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGCullingSystem::set_parentLODBias"
)
UNITY_ART_TAG_LOD_BIAS_GET_ICALL_INDEX = 3302
UNITY_ART_TAG_LOD_BIAS_GET_ICALL_VA = 0x1800F9110
UNITY_ART_TAG_LOD_BIAS_GET_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGCullingSystem::GetArtTagLODBias"
)
UNITY_ART_TAG_LOD_BIAS_SET_ICALL_INDEX = 3303
UNITY_ART_TAG_LOD_BIAS_SET_ICALL_VA = 0x1800F9230
UNITY_ART_TAG_LOD_BIAS_SET_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGCullingSystem::SetArtTagLODBias"
)

UNITY_DISPATCH_CULL_JOBS_ICALL_INDEX = 3315
UNITY_DISPATCH_CULL_JOBS_ICALL_VA = 0x1800FAFC0
UNITY_DISPATCH_CULL_JOBS_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGCullingSystem::DispatchBatchCullingJobs"
)

UNITY_HG_ICALL_NAME_TABLE_VA = 0x1820E6E90
UNITY_HG_ICALL_FUNCTION_TABLE_VA = 0x1820E8560
UNITY_HG_ICALL_COUNT = 729
UNITY_HG_ICALL_NAME_TABLE_SHA256 = (
    "a4eb4b58a62abdc78570e3d7b0f7f75c77fca5927f0d5f24fe75f4d98b36c93e"
)
UNITY_HG_ICALL_FUNCTION_TABLE_SHA256 = (
    "9ecec341ec864e050d5b31bc4f98bcdea23ad3b5e7c8dd36c7952612ef09a596"
)
UNITY_BIND_MONO_COMPONENT_CONVERT_ICALL_INDEX = 677
UNITY_BIND_MONO_COMPONENT_CONVERT_ICALL_VA = 0x1801DFF50
UNITY_BIND_MONO_COMPONENT_CONVERT_ICALL_NAME = (
    "UnityEngine.HyperGryph.Streaming.HGStreamingSceneManager::"
    "BindMonoComponentConvertFuncFromScript"
)
UNITY_ECS_GET_OR_REGISTER_ENTITY_TYPE_ICALL_INDEX = 712
UNITY_ECS_GET_OR_REGISTER_ENTITY_TYPE_ICALL_VA = 0x1801E0D90
UNITY_ECS_GET_OR_REGISTER_ENTITY_TYPE_ICALL_NAME = (
    "UnityEngine.HyperGryph.ECS.EntityManager::"
    "GetOrRegisterEntityTypeImpl_Injected"
)
UNITY_HGTREE_CREATE_RENDERER_LIST_ICALL_INDEX = 564
UNITY_HGTREE_CREATE_RENDERER_LIST_ICALL_VA = 0x1801D9D10
UNITY_HGTREE_CREATE_RENDERER_LIST_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGTreeRender::CreateRendererList"
)
UNITY_HGTREE_CREATE_RENDERER_LIST_CHILD_ICALL_INDEX = 565
UNITY_HGTREE_CREATE_RENDERER_LIST_CHILD_ICALL_VA = 0x1801D9F10
UNITY_HGTREE_CREATE_RENDERER_LIST_CHILD_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGTreeRender::CreateRendererListWithChildViewHandle"
)
UNITY_HGTREE_CREATE_RENDERER_LIST_PREZ_ICALL_INDEX = 566
UNITY_HGTREE_CREATE_RENDERER_LIST_PREZ_ICALL_VA = 0x1801D9FA0
UNITY_HGTREE_CREATE_RENDERER_LIST_PREZ_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGTreeRender::CreateRendererListWithPreZ"
)
UNITY_FACTORY_CREATE_BATCHED_ENTITIES_ICALL_INDEX = 198
UNITY_FACTORY_CREATE_BATCHED_ENTITIES_ICALL_VA = 0x1801EB230
UNITY_FACTORY_CREATE_BATCHED_ENTITIES_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGFactoryRenderManager::"
    "CreateBatchedEntities_Injected"
)
UNITY_FACTORY_CREATE_BATCHED_ENTITIES_OBSOLETE_ICALL_INDEX = 215
UNITY_FACTORY_CREATE_BATCHED_ENTITIES_OBSOLETE_ICALL_VA = 0x1801EC7C0
UNITY_FACTORY_CREATE_BATCHED_ENTITIES_OBSOLETE_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGFactoryRenderManager::"
    "CreateBatchedEntitiesObsolete_Injected"
)
UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_ICALL_INDEX = 151
UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_ICALL_VA = 0x1801E8F50
UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_ICALL_NAME = (
    "UnityEngine.HyperGryph.GPUDrivenRendererV1::CreateRendererList"
)
UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_PREZ_ICALL_INDEX = 152
UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_PREZ_ICALL_VA = 0x1801E9060
UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_PREZ_ICALL_NAME = (
    "UnityEngine.HyperGryph.GPUDrivenRendererV1::CreateRendererListWithPreZ"
)
UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_ICALL_INDEX = 164
UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_ICALL_VA = 0x1801E9680
UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_ICALL_NAME = (
    "UnityEngine.HyperGryph.GPUDrivenRendererV2::CreateRendererList"
)
UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_PREZ_ICALL_INDEX = 165
UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_PREZ_ICALL_VA = 0x1801E9770
UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_PREZ_ICALL_NAME = (
    "UnityEngine.HyperGryph.GPUDrivenRendererV2::CreateRendererListWithPreZ"
)
UNITY_HG_RESOURCE_LOAD_ASYNC_ICALL_INDEX = 437
UNITY_HG_RESOURCE_LOAD_ASYNC_ICALL_VA = 0x1801F2AB0
UNITY_HG_RESOURCE_LOAD_ASYNC_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGResourceManager::LoadAsync_Injected"
)
UNITY_HG_RESOURCE_GET_ASSET_ICALL_INDEX = 440
UNITY_HG_RESOURCE_GET_ASSET_ICALL_VA = 0x1801F2B60
UNITY_HG_RESOURCE_GET_ASSET_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGResourceManager::GetAsset_Injected"
)
UNITY_HG_RESOURCE_UPDATE_HANDLE_ICALL_INDEX = 441
UNITY_HG_RESOURCE_UPDATE_HANDLE_ICALL_VA = 0x1801F2C10
UNITY_HG_RESOURCE_UPDATE_HANDLE_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGResourceManager::UpdateAssetHandle_Injected"
)
UNITY_HG_GEOMETRY_GET_HANDLE_ICALL_INDEX = 300
UNITY_HG_GEOMETRY_GET_HANDLE_ICALL_VA = 0x1801EE550
UNITY_HG_GEOMETRY_GET_HANDLE_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGGeometrySystem::GetGeometryHandle"
)
UNITY_HG_GEOMETRY_GET_MESH_ICALL_INDEX = 301
UNITY_HG_GEOMETRY_GET_MESH_ICALL_VA = 0x1801EE5D0
UNITY_HG_GEOMETRY_GET_MESH_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGGeometrySystem::GetMesh"
)
UNITY_HGTREE_REGISTER_BATCH_GROUP_ICALL_INDEX = 567
UNITY_HGTREE_REGISTER_BATCH_GROUP_ICALL_VA = 0x1801DA040
UNITY_HGTREE_REGISTER_BATCH_GROUP_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGTreeRender::RegisterTreeBatchGroup"
)
UNITY_HGTREE_UNREGISTER_BATCH_GROUP_ICALL_INDEX = 568
UNITY_HGTREE_UNREGISTER_BATCH_GROUP_ICALL_VA = 0x1801DA310
UNITY_HGTREE_UNREGISTER_BATCH_GROUP_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGTreeRender::UnregisterTreeBatchGroup"
)
UNITY_HGTREE_UNREGISTER_BATCH_GROUP_WITH_HANDLE_ICALL_INDEX = 569
UNITY_HGTREE_UNREGISTER_BATCH_GROUP_WITH_HANDLE_ICALL_VA = 0x1801DA330
UNITY_HGTREE_UNREGISTER_BATCH_GROUP_WITH_HANDLE_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGTreeRender::UnregisterTreeBatchGroupWithHandle"
)
UNITY_FACTORY_SET_ENABLED_LIGHT_MODES_ICALL_INDEX = 204
UNITY_FACTORY_SET_ENABLED_LIGHT_MODES_ICALL_VA = 0x1801EB940
UNITY_FACTORY_SET_ENABLED_LIGHT_MODES_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGFactoryRenderManager::"
    "SetEntityEnabledLightModes_Injected"
)
HG_FACTORY_RENDER_MANAGER_TYPE_INDEX = 60910
HG_FACTORY_RENDER_MANAGER_TYPE_TOKEN = 0x02000021
HG_FACTORY_SET_ENABLED_LIGHT_MODES_METHOD_INDEX = 477909
HG_FACTORY_SET_ENABLED_LIGHT_MODES_METHOD_TOKEN = 0x06000071
HG_FACTORY_SET_ENABLED_LIGHT_MODES_INJECTED_METHOD_INDEX = 477923
HG_FACTORY_SET_ENABLED_LIGHT_MODES_INJECTED_METHOD_TOKEN = 0x0600007F
HG_TREE_RENDER_TYPE_INDEX = 61017
HG_TREE_RENDER_TYPE_TOKEN = 0x0200008C
HG_TREE_CREATE_RENDERER_LIST_INJECTED_METHOD_INDEX = 478192
HG_TREE_CREATE_RENDERER_LIST_INJECTED_METHOD_TOKEN = 0x0600018C
HG_TREE_CREATE_RENDERER_LIST_INJECTED_PARAMETER_START = 534045
HG_TREE_CREATE_RENDERER_LIST_INJECTED_PARAMETERS = [
    ("viewHandle", 0x08000388, 168243),
    ("renderFlagsMask", 0x08000389, 168243),
    ("renderFlagsValue", 0x0800038A, 168243),
    ("lightModeMask", 0x0800038B, 168243),
    ("context", 0x0800038C, 148461),
    ("drawableFeedbackPtr", 0x0800038D, 117409),
    ("noAlphaTest", 0x0800038E, 130818),
]
HG_SHADER_LIGHT_MODE_TYPE_INDEX = 60993
HG_SHADER_LIGHT_MODE_TYPE_TOKEN = 0x02000074
HG_SHADER_LIGHT_MODE_FIELDS = {
    "None": (296443, 0x04000155, 0x00000000),
    "GBuffer": (296444, 0x04000156, 0x00000001),
    "GBufferMobile": (296445, 0x04000157, 0x00000002),
    "Erosion": (296446, 0x04000158, 0x00000004),
    "ErosionMobile": (296447, 0x04000159, 0x00000008),
    "ErosionClear": (296448, 0x0400015A, 0x00000010),
    "ForwardOnly": (296449, 0x0400015B, 0x00000020),
    "Forward": (296450, 0x0400015C, 0x00000040),
    "ForwardCharacterOnly": (296451, 0x0400015D, 0x00000080),
    "ForwardReflection": (296452, 0x0400015E, 0x00000100),
    "CharacterOutline": (296453, 0x0400015F, 0x00000200),
    "ShadowCaster": (296454, 0x04000160, 0x00000400),
    "DepthOnly": (296455, 0x04000161, 0x00000800),
    "DepthCharacterOnly": (296456, 0x04000162, 0x00001000),
    "SRPDefaultUnlit": (296457, 0x04000163, 0x00002000),
    "ForwardDecal": (296458, 0x04000164, 0x00004000),
    "VFXDecal": (296459, 0x04000165, 0x00008000),
    "WetnessDecal": (296460, 0x04000166, 0x00010000),
    "Distortion": (296461, 0x04000167, 0x00020000),
    "FullScreenDebug": (296462, 0x04000168, 0x00040000),
    "OccludedDisplay": (296463, 0x04000169, 0x00080000),
    "TerrainVTDecal": (296464, 0x0400016A, 0x00100000),
    "TerrainVTDecalMobile": (296465, 0x0400016B, 0x00200000),
    "RayTracingReflection": (296466, 0x0400016C, 0x00400000),
    "RayTracingReflectionCompute": (296467, 0x0400016D, 0x00800000),
    "RayTracingGI": (296468, 0x0400016E, 0x01000000),
    "StencilAlphaBlend": (296469, 0x0400016F, 0x02000000),
    "WaterMarkUI": (296470, 0x04000170, 0x04000000),
    "ForwardAfterUI": (296471, 0x04000171, 0x08000000),
    "TextureStreamingFeedback": (296472, 0x04000172, 0x10000000),
    "GPUParticleSpawn": (296473, 0x04000173, 0x20000000),
    "GPUParticleSimulate": (296474, 0x04000174, 0x40000000),
}
PER_DRAW_PASS_CONFIG_TYPE_INDEX = 50112
PER_DRAW_PASS_CONFIG_TYPE_TOKEN = 0x0200023B
PER_DRAW_PASS_APPLY_METHOD_INDEX = 396344
PER_DRAW_PASS_APPLY_METHOD_TOKEN = 0x06000CB0
PER_DRAW_PASS_PARSE_METHOD_INDEX = 396346
PER_DRAW_PASS_PARSE_METHOD_TOKEN = 0x06000CB2
PER_DRAW_LIGHT_MODE_TYPE_INDEX = 50118
PER_DRAW_LIGHT_MODE_TYPE_TOKEN = 0x02000241
PER_DRAW_LIGHT_MODE_FIELDS = {
    "None": (239168, 0x04000912, 0x00000000),
    "GBuffer": (239169, 0x04000913, 0x00000001),
    "GBufferMobile": (239170, 0x04000914, 0x00000002),
    "Erosion": (239171, 0x04000915, 0x00000004),
    "ErosionMobile": (239172, 0x04000916, 0x00000008),
    "ErosionClear": (239173, 0x04000917, 0x00000010),
    "ForwardOnly": (239174, 0x04000918, 0x00000020),
    "Forward": (239175, 0x04000919, 0x00000040),
    "ForwardCharacterOnly": (239176, 0x0400091A, 0x00000080),
    "ForwardReflection": (239177, 0x0400091B, 0x00000100),
    "CharacterOutline": (239178, 0x0400091C, 0x00000200),
    "ShadowCaster": (239179, 0x0400091D, 0x00000400),
    "DepthOnly": (239180, 0x0400091E, 0x00000800),
    "DepthCharacterOnly": (239181, 0x0400091F, 0x00001000),
    "SRPDefaultUnlit": (239182, 0x04000920, 0x00002000),
    "ForwardDecal": (239183, 0x04000921, 0x00004000),
    "VFXDecal": (239184, 0x04000922, 0x00008000),
    "Distortion": (239185, 0x04000923, 0x00010000),
    "FullScreenDebug": (239186, 0x04000924, 0x00020000),
    "OccludedDisplay": (239187, 0x04000925, 0x00040000),
    "TerrainVTDecal": (239188, 0x04000926, 0x00080000),
    "TerrainVTDecalMobile": (239189, 0x04000927, 0x00100000),
    "RayTracingReflection": (239190, 0x04000928, 0x00200000),
    "StencilAlphaBlend": (239191, 0x04000929, 0x00400000),
    "WaterMarkUI": (239192, 0x0400092A, 0x00800000),
}
ENABLED_LIGHT_MODE_GAME_ASSEMBLY_BODIES = {
    "per_draw_pass_apply": (
        0x1869F3894,
        0x069F1E94,
        0xB8,
        "6edbf189c4933e093ec0dc5b342bd0dc9fdb45f7ef65b91767cb4b584a86a981",
    ),
    "per_draw_to_hg_shader_light_mode": (
        0x1869F3A20,
        0x069F2020,
        0x1C8,
        "86eff49d965112301e8c3321a2646b8259fa34920f73fbb682bc533464d14fb6",
    ),
    "set_entity_enabled_light_modes": (
        0x18B3F9118,
        0x0B3F7718,
        0x1C,
        "9910ce5d8b4c4571068000ffe95ba0dc052fa201f835c4167d9c24fcd0550a36",
    ),
    "set_entity_enabled_light_modes_injected": (
        0x18B3F90D8,
        0x0B3F76D8,
        0x40,
        "02078f35c7e7dad3a0f7dff28e5a62190ba87328f881b74f3cb2bf6257f5d76e",
    ),
}
ENABLED_LIGHT_MODE_METHOD_POINTERS = {
    PER_DRAW_PASS_APPLY_METHOD_INDEX: (0x0E9DD018, 0x1869F3894),
    PER_DRAW_PASS_PARSE_METHOD_INDEX: (0x0E9DD028, 0x1869F3A20),
    HG_FACTORY_SET_ENABLED_LIGHT_MODES_METHOD_INDEX: (
        0x0EF00120,
        0x18B3F9118,
    ),
    HG_FACTORY_SET_ENABLED_LIGHT_MODES_INJECTED_METHOD_INDEX: (
        0x0EF00190,
        0x18B3F90D8,
    ),
}
PER_DRAW_APPLY_TO_SET_ENABLED_LIGHT_MODES_SLICE = (
    0x069F1EFA,
    bytes.fromhex("4533c089078bd0488bcbe80f58a004eb298bcde8"),
)
UNITY_ART_TAG_LOD_STREAMING_OFFSET_GET_ICALL_INDEX = 279
UNITY_ART_TAG_LOD_STREAMING_OFFSET_GET_ICALL_VA = 0x1801EDEB0
UNITY_ART_TAG_LOD_STREAMING_OFFSET_GET_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGLODStreamingSystem::GetArtTagLODStreamingOffset"
)
UNITY_ART_TAG_LOD_STREAMING_OFFSET_SET_ICALL_INDEX = 280
UNITY_ART_TAG_LOD_STREAMING_OFFSET_SET_ICALL_VA = 0x1801EDED0
UNITY_ART_TAG_LOD_STREAMING_OFFSET_SET_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGLODStreamingSystem::SetArtTagLODStreamingOffset"
)

UNITY_STREAMING_CONVERSION_BODIES = {
    "bind_mono_component_convert": (
        0x1801DFF50,
        0x112,
        "2fcc761e2fd68c04b5d42b5079571552a098613594fdedc0445a758f69bc527a",
    ),
    "register_mono_component_convert": (
        0x181170720,
        0x409,
        "fa5bd423caf3c724663f7986cde799ab45492bd115502977950a2e7fe9a1aed1",
    ),
    "streaming_scene_manager_registry_constructor": (
        0x18117B010,
        0x1A5,
        "22e3540899471c45c228b1a59d564cdf5b74439f8bc09342d3211e49d788aecd",
    ),
    "mono_component_convert_from": (
        0x181150630,
        0x19D,
        "967d3e95128b73ab4de84dcaa30414731723629518e134b196b5930122c6c4b4",
    ),
    "mono_entity_component_list_convert_from": (
        0x181161FD0,
        0x2A6,
        "6e0500b0f68e5745662de0e04513eff4ee84b12fe87776d41910cf4551d5947e",
    ),
}

STREAMING_COMPONENT_ENUM_FIELDS = {
    "None": (296626, 0x0400020C, 0),
    "Transform": (296627, 0x0400020D, 1),
    "HLODGroup": (296638, 0x04000218, 1 << 11),
    "HGTree": (296668, 0x04000236, 1 << 41),
    "Count": (296670, 0x04000238, 43),
}

MANAGED_STREAMING_COMPONENT_BINDINGS = [
    ("HGAdditionalLightData", 0x290A, 0x2914, 1 << 25),
    ("HGEnvironmentVolume", 0x2963, 0x296D, 1 << 14),
    ("HGTerrain", 0x29C8, 0x29D2, 1 << 19),
    ("HGVolumetricLocalFog", 0x2A1E, 0x2A28, 1 << 12),
    ("HGWaterGlobalConfig", 0x2A74, 0x2A83, 1 << 32),
    ("HGWindMotor", 0x2ACF, 0x2ADE, 1 << 33),
    ("LensFlareComponentSRP", 0x2B39, 0x2B43, 1 << 29),
    ("Volume", 0x2B8F, 0x2B99, 1 << 15),
    ("HGVolumetricCloud", 0x2BF4, 0x2C03, 1 << 40),
]

HGTREE_NATIVE_SERIALIZED_TYPE_ROWS = {
    "HGTree": {
        "classId": 0x2C9CB981,
        "namePointerSlot": 0x1821252E0,
        "descriptorSlot": 0x1821252F8,
        "descriptorRaw": 0x000000982C9CB981,
    },
    "HGTreeData": {
        "classId": 0x59383C91,
        "namePointerSlot": 0x182125180,
        "descriptorSlot": 0x182125198,
        "descriptorRaw": 0x0000007859383C91,
    },
    "HGMeshRenderer": {
        "classId": 0x508754A6,
        "namePointerSlot": 0x182125240,
        "descriptorSlot": 0x182125258,
        "descriptorRaw": 0x00000058508754A6,
    },
    "HGMeshRendererData": {
        "classId": 0x50F4EE0C,
        "namePointerSlot": 0x1821253B0,
        "descriptorSlot": 0x1821253C8,
        "descriptorRaw": 0x000000F850F4EE0C,
    },
}

STREAMING_SCENE_V2_CREATE_ICALL_INDEX = 621
STREAMING_SCENE_V2_CREATE_ICALL_VA = 0x1801DE220
STREAMING_SCENE_V2_CREATE_ICALL_NAME = (
    "UnityEngine.HyperGryph.Streaming.StreamingSceneV2::Create_Injected"
)
STREAMING_SCENE_V2_BINARY_BODIES = [
    (
        "UnityPlayer.dll",
        "StreamingSceneV2.Create_Injected icall wrapper",
        0x1801DE220,
        0xF6,
        "cbb1c6b2db31de3a31ea15715f48321031c667a5ce8d3b78fd96780102f3d355",
    ),
    (
        "UnityPlayer.dll",
        "StreamingSceneV2 bytes loader",
        0x18117B200,
        0x1060,
        "5b89a0f553ba1047979d0294123c351c3fdd0997fcdc70606ad3623eb71cbd8f",
    ),
    (
        "UnityPlayer.dll",
        "StreamingSceneV2 chunk path builder",
        0x181177230,
        0x107,
        "b191cd86ed35be83b1636c734593a75958fc0484b932af27931d8828bae8a4dd",
    ),
    (
        "UnityPlayer.dll",
        "StreamingSceneV2 request callback",
        0x18111ADF0,
        0x109,
        "05293c4ea0d19c88ec586a623da4370b3e1ef661f62d9132cb075a81b0f32d2a",
    ),
    (
        "UnityPlayer.dll",
        "interleaved-token LZ4 decoder",
        0x18160EAE0,
        0x382,
        "f36ef38fc92e3c21dcaed9e0ad249b5783e1ce2ca4db6fc4ba80a31842884327",
    ),
    (
        "GameAssembly.dll",
        "StreamingSceneV2.Create",
        0x1853965E0,
        0x14,
        "fdd328cd688c14626484e4cdf4eee8ef5aa30df259dfe0f0c6cd1fa4425411e8",
    ),
    (
        "GameAssembly.dll",
        "StreamingSceneV2.Create_Injected",
        0x183F01530,
        0x50,
        "0ff632a05af8380aca49643eb1dee5e6d704ca5b5844f0701c3b946b23f6b0f8",
    ),
    (
        "GameAssembly.dll",
        "BaseGameScene.CreateStreamingScene",
        0x183F01190,
        0x3A0,
        "1391e46affd12e415010bba0224ee91fc72676d15e5a5bed1ed9d3f5a29cc2fb",
    ),
    (
        "UnityPlayer.dll",
        "StreamingSceneV2 union dispatch",
        0x18117DC50,
        0xB51,
        "391f2531f5a880430e9f8ae5c84e69936298d02edfcf1851eaceedd1fa50f70e",
    ),
    (
        "UnityPlayer.dll",
        "native ECS archetype initial-data copy",
        0x1801F95E0,
        0x41A,
        "0e329dbc2ac208dbb30dd31719a92a5af1548be2c2838c44549c3a81b85cc2dd",
    ),
    (
        "UnityPlayer.dll",
        "MonoEntity tag-1 create callback",
        0x18114F380,
        0x347,
        "3c053a3579625ba22806b224eb91ad4fd52dc89a16502c6963388af04c04c2fd",
    ),
    (
        "UnityPlayer.dll",
        "MonoEntity tag-1 destroy callback",
        0x18114F6D0,
        0x9A,
        "d50fcb89d0b62b6de48a0e9ee94d6b7a2b34e0395158f085e72181e0e03a3ec4",
    ),
    (
        "UnityPlayer.dll",
        "native-ECS tag-2 create callback",
        0x18114F880,
        0x251,
        "ef8a361f6122810670bbb5683de199faf85cacacd4cbd5eb17edbf8f414dd5e6",
    ),
    (
        "UnityPlayer.dll",
        "native-ECS tag-2 destroy callback",
        0x18114FAE0,
        0x19B,
        "07e666c12dba8832556115f214d8edaa8c06206f029b5ad1b001e8a667bcbe69",
    ),
    (
        "UnityPlayer.dll",
        "Proxy tag-3 create callback",
        0x18114FEB0,
        0x175,
        "9234d6a8a44f27bd7da4bb2bb548cfc11f663ab966844c4da07d13454bd123f6",
    ),
    (
        "UnityPlayer.dll",
        "Proxy tag-3 destroy callback",
        0x181150030,
        0x9F,
        "0b2622da3ae6636116f68a0d5ab9763edecf3ec65c38e336328cc9da2b146f9b",
    ),
    (
        "UnityPlayer.dll",
        "native ECS ConvertFrom dispatcher",
        0x181152810,
        0x22E,
        "83f4aaec73d0843431805404e3ec832d6c3fcae29fff1085842fe92b5b14269a",
    ),
    (
        "UnityPlayer.dll",
        "MergedRenderCollider type-9 callback registration",
        0x18116B6AB,
        0x2F6,
        "162f141c1c1dca0fc908a44994b0396100724baa90647db52f0fb561376fe084",
    ),
    (
        "UnityPlayer.dll",
        "Render type-0 callback registration",
        0x18116B9A1,
        0x240,
        "c7f5509630888694f23799662326f637f6dd20954e1daffe11938aae79a08cf9",
    ),
    (
        "UnityPlayer.dll",
        "MergedRenderCollider type-9 transition-1 callback",
        0x181153310,
        0x5DF,
        "4435143d7cce168aa670402d64f54cd6e813160dceab5e22b01ed28a05ad3d5c",
    ),
    (
        "UnityPlayer.dll",
        "MergedRenderCollider type-9 ConvertFrom callback",
        0x181157760,
        0x7F9,
        "45633b35ac3c0bd27a71bb8464121584f185445ef18a7fe4a1e9b2808f074d63",
    ),
    (
        "UnityPlayer.dll",
        "Render type-0 transition-1 callback",
        0x181154230,
        0x6C4,
        "4ae50616400e412b8c30c649765b11ad1e4906b9f7bf3e5f64a584ddc5027789",
    ),
    (
        "UnityPlayer.dll",
        "Render type-0 ConvertFrom callback",
        0x181159010,
        0x398,
        "c1f42c8333a1f0daf613485ee1757e78bdf95899ddcdcde81b7e177027dd8247",
    ),
    (
        "UnityPlayer.dll",
        "native ECS callback-slot installer",
        0x1811701B0,
        0xFE,
        "044cba2341778c80103264855a41dd1b6e5a361641e9d5f36ef67a70f5839e6e",
    ),
]
STREAMING_UNION_DISPATCH_TABLES = {
    "create": (
        0x181E226E8,
        [0, 0x18114F380, 0x18114F880, 0x18114FEB0, 0x1811501E0],
    ),
    "destroy": (
        0x181E228A0,
        [0, 0x18114F6D0, 0x18114FAE0, 0x181150030, 0x180076890],
    ),
}
STREAMING_ECS_ENTITY_TYPE_FIELDS = {
    "Render": (296729, 0x04000273, 0),
    "Water": (296730, 0x04000274, 1),
    "ConvexCollider": (296731, 0x04000275, 2),
    "CapsuleCollider": (296732, 0x04000276, 3),
    "SphereCollider": (296733, 0x04000277, 4),
    "MeshCollider": (296734, 0x04000278, 5),
    "MultiCollider": (296735, 0x04000279, 6),
    "TerrainCollider": (296736, 0x0400027A, 7),
    "TerrainDecal": (296737, 0x0400027B, 8),
    "MergedRenderCollider": (296738, 0x0400027C, 9),
    "HGDecalProjector": (296739, 0x0400027D, 10),
    "TerrainSplineDecal": (296740, 0x0400027E, 11),
    "HGStreamingVolume": (296741, 0x0400027F, 12),
    "WaterDecal": (296742, 0x04000280, 13),
    "TypeCount": (296743, 0x04000281, 14),
}
STREAMING_PROXY_ENTITY_TYPE_FIELDS = {
    "IrradianceVolume": (296745, 0x04000283, 0),
    "AudioVolume": (296746, 0x04000284, 1),
    "AudioEmitter": (296747, 0x04000285, 2),
    "AudioRoom": (296748, 0x04000286, 3),
    "TerrainSurfaceTypeData": (296749, 0x04000287, 4),
    "AudioPortal": (296750, 0x04000288, 5),
    "SOCChunk": (296751, 0x04000289, 6),
    "GrassGrid": (296752, 0x0400028A, 7),
    "GpuClothGroup": (296753, 0x0400028B, 8),
    "TreeGrid": (296754, 0x0400028C, 9),
    "GPUParticleSystem": (296755, 0x0400028D, 10),
    "TypeCount": (296756, 0x0400028E, 11),
}
STREAMING_SCENE_V2_COMPONENT_BITS = [
    {"bit": 0, "name": "Transform", "componentCount": 66514, "fileCount": 38452},
    {"bit": 1, "name": "MeshFilter", "componentCount": 28, "fileCount": 26},
    {"bit": 2, "name": "MeshRenderer", "componentCount": 28, "fileCount": 26},
    {"bit": 4, "name": "BoxCollider", "componentCount": 136, "fileCount": 134},
    {"bit": 14, "name": "HGEnvironmentVolume", "componentCount": 40660, "fileCount": 36890},
    {"bit": 15, "name": "Volume", "componentCount": 330, "fileCount": 300},
    {"bit": 16, "name": "ReflectionProbe", "componentCount": 9924, "fileCount": 3468},
    {"bit": 17, "name": "Light", "componentCount": 15240, "fileCount": 1720},
    {"bit": 19, "name": "HGTerrain", "componentCount": 70, "fileCount": 70},
    {"bit": 25, "name": "HGAdditionalLightData", "componentCount": 15240, "fileCount": 1720},
    {"bit": 29, "name": "LensFlareComponentSRP", "componentCount": 166, "fileCount": 166},
    {"bit": 32, "name": "HGWaterGlobalConfig", "componentCount": 138, "fileCount": 110},
    {"bit": 33, "name": "HGWindMotor", "componentCount": 102, "fileCount": 56},
    {"bit": 40, "name": "HGVolumetricCloud", "componentCount": 22, "fileCount": 6},
]

HG_ASSET_TYPE_INDEX = 60980
HG_ASSET_TYPE_TOKEN = 0x02000067
HG_ASSET_TYPE_BYVAL_METADATA_TYPE = 122373
HG_RESOURCE_MANAGER_TYPE_INDEX = 60990
HG_RESOURCE_MANAGER_TYPE_TOKEN = 0x0200006E
HG_RESOURCE_LOAD_ASYNC_INJECTED_METHOD_INDEX = 478100
HG_RESOURCE_LOAD_ASYNC_INJECTED_METHOD_TOKEN = 0x06000130
HG_RESOURCE_LOAD_ASYNC_INJECTED_PARAMETER_START = 533738
HG_ASSET_TYPE_FIELDS = {
    "Invalid": (296374, 0x04000110, 0),
    "Material": (296375, 0x04000111, 1),
    "Mesh": (296376, 0x04000112, 2),
    "Texture2D": (296377, 0x04000113, 3),
    "Texture3D": (296378, 0x04000114, 4),
    "CubeMap": (296379, 0x04000115, 5),
    "ScriptableObject": (296380, 0x04000116, 6),
    "Shader": (296381, 0x04000117, 7),
    "ComputeShader": (296382, 0x04000118, 8),
    "TerrainLayer": (296383, 0x04000119, 9),
    "SubsurfaceProfile": (296384, 0x0400011A, 10),
    "Count": (296385, 0x0400011B, 11),
}

IL2CPP_METADATA_SECTION_NAMES = [
    "stringLiteral",
    "stringLiteralData",
    "string",
    "events",
    "properties",
    "methods",
    "parameterDefaultValues",
    "fieldDefaultValues",
    "fieldAndParameterDefaultValueData",
    "fieldMarshaledSizes",
    "parameters",
    "fields",
    "genericParameters",
    "genericParameterConstraints",
    "genericContainers",
    "nestedTypes",
    "interfaces",
    "vtableMethods",
    "interfaceOffsets",
    "typeDefinitions",
    "images",
    "assemblies",
    "fieldRefs",
    "referencedAssemblies",
    "attributeData",
    "attributeDataRange",
    "unresolvedVirtualCallParameterTypes",
    "unresolvedVirtualCallParameterRanges",
    "windowsRuntimeTypeNames",
    "windowsRuntimeStrings",
    "exportedTypeDefinitions",
]

UNITY_CULL_VIEW_BODIES = {
    "injected_binding": (
        0x1800F9790,
        0xF2,
        "386a7e4b825187d828baf76b7b87b9e017fd2be2cd10f431ffc2c63f56b538fd",
    ),
    "matrix_plane_core": (
        0x18104A190,
        0x289,
        "cfdc4bfdf1e258b63bcc52842fa3fd274939ef858e8860ea7dc4d9788567c060",
    ),
    "scheduled_constructor": (
        0x18104A7A0,
        0x1082,
        "e3f1d5de1f4f32ee7198d0d4a8a789b7789bf34c10b83ba3fc5281de62d1d681",
    ),
}

UNITY_CULL_VIEW_SLICES = {
    "binding_to_matrix_plane_core": (0x1800F9864, "e82709f500"),
    "matrix_plane_core_to_scheduled_constructor": (
        0x18104A3D3,
        "488d45e04c894c2448458bc8c74424400000000041b806000000"
        "c744243801000000c7442430010000004889442428488d45e0"
        "4889442420e890030000",
    ),
    "scheduled_view_header_projection": (
        0x18104A83B,
        "89388b85e0010000418945048b85e8010000410bc441894508"
        "8b85f0010000410bc44189450c",
    ),
    "scheduled_screen_camera_occlusion_projection": (
        0x18104A8DB,
        "8b8508020000f30f1085000200004189452c8b8510020000"
        "f3410f114518f30f1085400200004189453049894d104d897520"
        "458975288b15e923dd004c8d0dd774c90041b808000000"
        "f3410f114534",
    ),
    "scheduled_occlusion_allocation_gate": (
        0x18104AA66,
        "8885e0010000394424400f8444020000398518020000"
        "0f84380200003985200200000f842c020000",
    ),
    "candidate_visibility_then_culling_mask_gate": (
        0x181051FD3,
        "8b0ef6c1010f84b906000041f6410401740c8b43044185017404"
        "b001eb0232c0",
    ),
    "scheduled_constructor_return_handle": (
        0x18104B7E3,
        "488d4b38e894830eff488b4b388b44244448897b4848ffcf"
        "488b9c2470020000488d14f9488bbc24600200004885d27403"
        "4c892a4881c478020000415d5dc3",
    ),
}

UNITY_SCHEDULED_CULL_BODIES = {
    "dispatch_binding": (
        0x1800FAFC0,
        0x19,
        "5374f3351e8db1e2c98274dcc8fe4304eec2138606b4d88231fc96c7d41c391e",
    ),
    "dispatch_outer": (
        0x181053400,
        0x32E,
        "b894f16e1cc3c7bbfba8c3efed4184eebc75cc5700e4eb89b7009f3064ce3fbd",
    ),
    "dispatch_copy_and_schedule": (
        0x181053010,
        0x3E7,
        "49163e4ac499ee881865d2fb39c85faa58a7ea91d684b320e5ca3b72a29a4557",
    ),
    "scheduled_batch_core": (
        0x181053730,
        0x2CFE,
        "e98d6f1048d417b86a65a9a8328e6edf7fbc9f2d91e3c94464e4586e1bb5eb45",
    ),
    "parallel_batch_thunk": (
        0x181045F80,
        0xDE,
        "c3cdc2ccc3b96eaa31ce470f0f3a1313c795da8bef5e4b4cc3645e71b68fce0c",
    ),
    "standard_predicate_wrapper": (
        0x180FEAEB0,
        0x21,
        "8c83c911f9db7bddebde8c12e9433b63ce67479df1b141819dff9e476149a241",
    ),
    "six_plane_aabb_predicate": (
        0x181049010,
        0x9C,
        "06fe6ad29ba950c501467a9d52f7a43326795ed425ea286bb6e474523825e4fc",
    ),
    "camera_type_0x80_sphere_predicate": (
        0x180FEAEF0,
        0x60,
        "e0404f9a11a72bc0c563e51e1c55fe16c4e5df6a4740a7f07501c32ec09254f5",
    ),
}

UNITY_SCHEDULED_CULL_SLICES = {
    "view_predicate_selection": (
        0x181053A14,
        "4d8b34c04c8d3d9174f9ff488d05ca74f9ff41817e2c80000000"
        "4c0f44f8",
    ),
    "view_predicate_call": (
        0x181053C41,
        "418b4e28498b4538f7d1448b04064423c1498bce44890406"
        "4c8d420c41ffd784c07406418b4e28eb03418bcc498b4538"
        "0b0c30890c06",
    ),
    "camera_type_0x80_equation": (
        0x180FEAEF0,
        "488b41104f8d14c9f30f1012f30f105a04f3410f1008"
        "f3420f5c5c901cf3410f5f4804f3420f5c549018f30f104208"
        "f3420f5c449020f30f59dbf3410f5f4808f30f59d2f30f59c0"
        "f30f584934f30f58daf30f59c9f30f58d80f2fcb0f93c0c3",
    ),
    "parent_lod_bias_to_batch_core": (
        0x181053351,
        "4d8d8e84010000f3410f1086800100004d8d8684050000458b5e48452b9e78"
        "0100004c8d14c84c89bc2420010000410fb64604488bcf88442460488d842420"
        "0100004889542458418bd54c894424504d8b86d80000004c894c2448458b8ee8"
        "000000f30f11442440895c2438488944243044895c24284c89542420e85f030000",
    ),
    "batch_core_parent_lod_bias_ingress": (
        0x1810537F0,
        "f30f10bd201200008d7e0148c1e704488d35efe5c800f30f11bd9c020000",
    ),
    "parallel_batch_parent_lod_bias_projection": (
        0x181054665,
        "8888ac010000488b8530010000488b8d28120000f30f11b8b0010000",
    ),
}

UNITY_CULL_VIEW_SURFACE_ICALLS = {
    "add_by_matrix": (
        3304,
        0x1800F9790,
        "UnityEngine.HyperGryph.HGCullingSystem::AddCullViewByMatrix",
    ),
    "register_unique_id": (
        3306,
        0x1800F9A00,
        "UnityEngine.HyperGryph.HGCullingSystem::RegisterCullViewUniqueId",
    ),
    "unregister_unique_id": (
        3307,
        0x1800F9D80,
        "UnityEngine.HyperGryph.HGCullingSystem::UnregisterCullViewUniqueId",
    ),
    "add_by_planes": (
        3313,
        0x1800FA6D0,
        "UnityEngine.HyperGryph.HGCullingSystem::AddCullViewByPlanes",
    ),
    "add_child_by_planes": (
        3314,
        0x1800FAB60,
        "UnityEngine.HyperGryph.HGCullingSystem::AddCullChildViewByPlanes",
    ),
    "dispatch": (
        3315,
        0x1800FAFC0,
        "UnityEngine.HyperGryph.HGCullingSystem::DispatchBatchCullingJobs",
    ),
    "reset": (
        3316,
        0x1800FB050,
        "UnityEngine.HyperGryph.HGCullingSystem::ResetCullViews",
    ),
    "get_fence": (
        3317,
        0x1800FB080,
        "UnityEngine.HyperGryph.HGCullingSystem::GetCullingViewFence_Injected",
    ),
}

UNITY_CULL_VIEW_CONSUMER_BODIES = {
    "register_unique_id": (
        0x1800F9A00,
        0x37F,
        "2d2e10aa276ab4ad8691241ef4316280ac9f05168800152e81e74d392bd07d91",
    ),
    "unregister_unique_id": (
        0x1800F9D80,
        0x38,
        "6f865394d930552af24a12a4cf66bcf1110a4c5f26d6ad6dc00f12dea7eaf7ff",
    ),
    "add_by_planes_binding": (
        0x1800FA6D0,
        0x111,
        "bc8a821533e2f1f84f955113ff5bc2bdc2e91f57052033c33c97a990ac418ceb",
    ),
    "add_by_planes_core": (
        0x18104A670,
        0x12C,
        "99d4566263996bd9685db4eebbcd47c3d90244633d7314eec37a60203304563e",
    ),
    "add_child_by_planes_binding": (
        0x1800FAB60,
        0x5A,
        "9ca7af1e05bd12d5db6513505ddd44a53b441fed5064a95945823683b43bca29",
    ),
    "add_child_by_planes_core": (
        0x181049F30,
        0x257,
        "7893975401f4269467d6d9585b35ca65af3d06db6fab5462367bc010c41b9e8c",
    ),
    "scheduled_view_loop": (
        0x181053A10,
        0x267,
        "a92c993243184d53636a9cf06d93aa538095b433332cbe648d9030b2879743be",
    ),
    "reset_binding": (
        0x1800FB050,
        0x24,
        "e64dff0c1216346e1ffe5298d493bba40e855c11b0eb5704715c44d601d1c89d",
    ),
    "reset_core": (
        0x18105EE10,
        0xEBC,
        "b1ecb2e9a5c80fb5e7a29beb758f70a59448070a2a6745f71ce97866d9d9462e",
    ),
    "get_fence_binding": (
        0x1800FB080,
        0x39,
        "12896d9eb77f48059166b67700482135cbb451dff6f8dc04055a2ed4163e3716",
    ),
    "get_fence_leaf": (
        0x181057740,
        0x3E,
        "eee8e419bf97b8e45e8bab130050662479869fc0fc97ac62ad0a7484f2d95879",
    ),
}

UNITY_CULL_VIEW_CONSUMER_SLICES = {
    "batch_view_pointer_ingress_and_predicate_selection": (
        0x1810539DD,
        "4c8b85001200008b188bcbb801000000895d1048d3e0ffc8488945688bc7"
        "498b0cc04c8b69204c896d7885db0f84ab02000090418d043c4d8b34c0"
        "4c8d3d9174f9ff488d05ca74f9ff41817e2c800000004c0f44f8",
    ),
    "batch_view_fields_and_predicate_call": (
        0x181053BBD,
        "418b46540fa3c87217498b4538418b4e28f7d18b140623d1891406e99a"
        "000000418b4654ba0100000048d3e248ffca4823d0488b07f34c0fb8caf6"
        "00017505498bd4eb3bf34c0fb800f3490fb8c485c0750d488b07428d1485"
        "00000000eb1c8d1485fcffffff488b07488b48088b140a428d0c85000000"
        "004803d1480350084885d27436418b4e28498b4538f7d1448b04064423c1"
        "498bce448904064c8d420c41ffd784c07406418b4e28eb03418bcc498b45"
        "380b0c30890c06",
    ),
    "reset_view_pointer_vector": (
        0x18105F0D9,
        "488b4638488b4e48488bd84c8d34c8493bc6744a0f1f00488b3b41b9fc"
        "1300008b1501dcdb004d8bc7488b4f38488b09e8624d2aff488b4f384885"
        "c9741341b9fd1300004d8bc7bab4000000e8464d2aff4883c3084c896738"
        "493bde75b948837e3800740e0fb64650f6d0a80174044c896648",
    ),
    "child_view_separate_vector": (
        0x18104A099,
        "498b7f68498d5f58488b431848ffc74c8bbc2430010000488bac24580100"
        "0048d1e8483bf87608488bcbe8586a0100488b134869cfe800000048897b"
        "1048",
    ),
}

UNITY_HGTREE_BODIES = {
    "hg_geometry_get_handle_binding": (
        0x1801EE550,
        0x7E,
        "bfdbb4dbb93d629ad18b25f75fe3f602686f82de66010d64425b7abfd5dcfb70",
    ),
    "hg_geometry_get_mesh_binding": (
        0x1801EE5D0,
        0x85,
        "b4af1acfe29b1d2021c372940fa737e40a90ac0ae7b7f0fd2b6d61878cb85f72",
    ),
    "hg_geometry_instance_map_insert": (
        0x1810941F0,
        0x278,
        "3ebda9f858ab8adb9d8122784663a8ca3833c6793ebae7e18e1dfe6f1190023c",
    ),
    "hg_geometry_slot_populate_and_handle_build": (
        0x18108B1C0,
        0x396,
        "5e602aefe660993deb394eab88c3a175ff610ba604a2c51851e3a94bb8098e1e",
    ),
    "hg_geometry_instance_map_remove": (
        0x181099980,
        0x16C,
        "ab1d3695b2e0b6540fae244f600930de4f2d7e93eecc93cc90cbc7b4288ce3de",
    ),
    "mesh_geometry_registration_site": (
        0x1813727B0,
        0xA5,
        "ca1af751d26340d67069a6fe864ecbac8a0ce615231e8c17720bb295f30bcce1",
    ),
    "mesh_geometry_unregistration_site": (
        0x1813773B0,
        0x1D5,
        "8c5d5a5cdc033247aaf5a4c5d7bcde76acb698b61fd60ba996f8ccdfeb447d39",
    ),
    "hgmesh_renderer_data_serialized_fields": (
        0x1810A9120,
        0x23A,
        "6fb27222e41b8456d54b4708eccd476c46e90f623a117a563cabd3c600b4c383",
    ),
    "hgmesh_renderer_data_runtime_record_initializer": (
        0x181088D80,
        0x35E,
        "e97ae32dba96720c667983b53657782f599cb1fab260922aae04b57d0c9d153f",
    ),
    "instance_serializer": (
        0x18106F9A0,
        0x3C9,
        "be21b07910174f9d037140711484fbfe345baae4d785b7ef5e035bd1d12195f9",
    ),
    "renderer_serializer": (
        0x18106FD70,
        0x1DC,
        "285455b0862cf34c1b0aaeb7b198489c9dc805d7e3921424b07d75239fdfe0f2",
    ),
    "renderer_deserializer": (
        0x1810701C0,
        0x26C,
        "9ad71baa660f3e2547417faad460a8667bc22e98f4c2360c7f8f8a4e2cff3d72",
    ),
    "create_renderer_list_binding": (
        0x1801D9D10,
        0x82,
        "078046e5e67d9dba899cbc152434a3e00be20ac993d14d834098c056a300067b",
    ),
    "create_renderer_list_core": (
        0x18107EE40,
        0x462,
        "d7877c2aa90cc5eea0c2801515128b8fec5216ec3dc0a260e63da762769ae2dd",
    ),
    "create_renderer_list_child_binding": (
        0x1801D9F10,
        0x84,
        "3f16d5e542e73ed61ce0a5349aded395548bb88f03eef4b482931409cb519833",
    ),
    "create_renderer_list_child_core": (
        0x18107FCF0,
        0x491,
        "295fb7f0faf287da2f29ee92bf78422fb0e29ecd2c01e3b36c6122dd6b0c93ba",
    ),
    "create_renderer_list_prez_binding": (
        0x1801D9FA0,
        0x95,
        "d2a73c8e9d8e795b13e2cc975ae4eb31fcba259e4609a4ba0ee338b24a4c04f8",
    ),
    "create_renderer_list_prez_core": (
        0x181080190,
        0x59C,
        "ec78e01c7478fed1a5feaedc34b9881519416c5e4b78d5852287fd579c10705d",
    ),
    "renderer_list_job_scheduler": (
        0x181080730,
        0x225,
        "f040106075938864fdea07782309fd910c853db82e739a19738ce0cdbe5d2beb",
    ),
    "register_tree_batch_group_binding": (
        0x1801DA040,
        0x13B,
        "03e9b1da96000390744e123ad2c35b8feed1e17f4618b9ae092b375338c5ee4d",
    ),
    "register_tree_batch_group_core": (
        0x181086050,
        0x273,
        "1bafbffc56bfaa42445fea8f10bac1047ab44712ee7361456efc281e07196dc3",
    ),
    "unregister_tree_batch_group_binding": (
        0x1801DA310,
        0x20,
        "0a176eaa3e84d0c92ce36fe4f77b93b3a774a2822512f73916b6988fd26af886",
    ),
    "unregister_tree_batch_group_with_handle_binding": (
        0x1801DA330,
        0x2E,
        "6b0c7fa81825b727436e1ae3203c53c6dca1c446eea090ada743f03cdf3e2109",
    ),
    "unregister_tree_batch_group_core": (
        0x181087D30,
        0xC8,
        "f23cd4db139cf289446d8314f11cdfb7bd6d5be5b2c14d175e58adb50b02b9e9",
    ),
    "unregister_tree_batch_group_with_handle_core": (
        0x181087E00,
        0x86,
        "310d8984fc3225999df49d84d74137d4add2ff1b69927950d77f375d1afde7c8",
    ),
    "runtime_transform_owner_cleanup": (
        0x1810BCE00,
        0x48A,
        "32f463461d5bca2ca0458400bc608e1fde2b8e80b493653159565bad8304e43f",
    ),
    "lod_ecs_component_67_accessor": (
        0x181038D00,
        0x6C,
        "9fd401ef957830896aca114bc591187a39e5772b41b2300439ef3f8f8f4a1699",
    ),
    "lod_ecs_component_67_indexed_accessor_hot": (
        0x1811648A0,
        0x31,
        "7b39be54e8af8b957fbdba2495db8f6604a068f327a6cf503a233a3d1fdc77c2",
    ),
    "lod_ecs_component_67_indexed_accessor_tail": (
        0x181164985,
        0x84,
        "956019335a64fb5538d947ba107a385515085c041a9923b1069f9caf9025c883",
    ),
    "lod_ecs_initial_completion_writer": (
        0x181159010,
        0x398,
        "c1f42c8333a1f0daf613485ee1757e78bdf95899ddcdcde81b7e177027dd8247",
    ),
    "lod_ecs_direct_availability_initializer": (
        0x181157760,
        0x7F9,
        "45633b35ac3c0bd27a71bb8464121584f185445ef18a7fe4a1e9b2808f074d63",
    ),
    "ecs_entity_type_component_mask_binding": (
        0x1801E0D90,
        0x1A3,
        "790978a58b50cb40e3ee3b5378de0e1497a836627faaf0db2ced6f06ed886219",
    ),
    "ecs_entity_type_registration_core": (
        0x1801FAEC0,
        0x425,
        "feae1be83909416dd7f79384c1367aac1fc33e88dbda9c9fcb04dc5273b6fa24",
    ),
    "component_proxy_registration": (
        0x1807EEEE0,
        0x2A,
        "9e408f57aab1474c955e8b1efd201ac40b59de546ba2229a71705c0ef6269246",
    ),
    "component_native_type_initializer": (
        0x1807EC5E0,
        0x59,
        "9ae5e42bb98364eb2881612c57bcf0c7a8d3562398a7aeb42f66347f1bf9e8c6",
    ),
    "lod_ecs_availability_writer": (
        0x1810842E0,
        0x835,
        "b40cfccfcea9e2c91b65fba6ac51fa681f27b7fb6cdc89ae9539a0924b500418",
    ),
    "parent_lod_bias_getter": (
        0x1800F8E00,
        0x38,
        "73b6639e35051f978ff90c95633128fb4d2f546587aa9fd3b5d50442991520cb",
    ),
    "parent_lod_bias_setter": (
        0x1800F8E40,
        0x2E,
        "32acbd119ef72da1c87a12550fa6540bea21fa32f85d546a135f4530c5f93120",
    ),
    "art_tag_lod_bias_getter": (
        0x1800F9110,
        0x11A,
        "82d7c9c109821cb8fc2d6b94e67a026d8943a8b0373458f4bd849865ea91ef48",
    ),
    "art_tag_lod_bias_setter": (
        0x1800F9230,
        0x14C,
        "b9e6d0ecdea960846b74895c3b96c756a369faeabde473e38a536bca1907e77c",
    ),
    "art_tag_lod_streaming_offset_getter": (
        0x1801EDEB0,
        0x20,
        "a2d4580b70a05dbe4b0745a131a9efd0c6656bbd9e4f9f783d1163dfe76e8916",
    ),
    "art_tag_lod_streaming_offset_setter": (
        0x1801EDED0,
        0x69,
        "623e351a79c9f7a6d3073e3c583ab3d4a1c160c34d5c8629477e1668da8c0186",
    ),
    "lod_dispatch_payload_builder": (
        0x18106EAD0,
        0x8A0,
        "ff7781d15ccf49a3a904fc22a61b6a21a70288776d9b9daca1896b2c7855470c",
    ),
    "lod_dispatch_callback_wrapper": (
        0x181060E60,
        0x2F,
        "10c4bc6310d3b34d29874f0f08ca7641bd52a18013b29e31dc0fab4b752cde58",
    ),
    "lod_dispatcher": (
        0x181079C10,
        0x590,
        "78c1178d47a48db4ee56a95f643f54b90be0a7e13ac357f3ec83afbbf5bef5b0",
    ),
    "serialized_to_runtime_transform": (
        0x1810C5F30,
        0x6BC,
        "0c9b3d4fe4a444b49e4dd0b161f35e72de8244546639fac61d98bd2974ee4332",
    ),
    "particle_renderer_record_0x08_flags_mode_2": (
        0x1810416A0,
        0x1CE,
        "86ec5e76acda8b910c87262bf7b6e79449b25ec958908965e9d904a322b18943",
    ),
    "particle_renderer_record_0x08_flags_mode_3": (
        0x181041870,
        0xA5,
        "24e11d4a25438887b99d22c6d202c0689c023b789f52b56ce0ca84b79d462dde",
    ),
    "particle_renderer_record_0x08_flags_mode_4": (
        0x181041920,
        0xA5,
        "ad13ada20c1382a9697c6423f40b898a76934d22932c80eae4e76c0225d3fe31",
    ),
    "particle_renderer_record_0x08_flags_mode_5": (
        0x1810419D0,
        0xA5,
        "c7b18e76b010f26a0f8ce7d9f09f38e1b2a759097a41de17ec86d8081a5c1163",
    ),
    "renderer_runtime_property_flag_sync": (
        0x180432CD0,
        0x1ED,
        "b265d127f02af8b6f7995ed24b5d29cffe3b36d0e6fd2cfcce2b429ca4490f8a",
    ),
    "generic_renderer_runtime_record_constructor": (
        0x180BCB760,
        0x92E,
        "bc9b51e5ec3b9f43cd26faf384f92658cf591ca119df1b173cf19912eadd016f",
    ),
    "renderer_base_constructor": (
        0x18042BF10,
        0x1A9,
        "aca47837fe54b12c2989c7803b5a52ad446350033342d40948294a0913b91929",
    ),
    "generic_renderer_runtime_record_input_builder": (
        0x180BCCB60,
        0x3ED,
        "1c1bc9178df20b45ad8a09c41a06b60133c2285706310b097bb13cb1f2aa020d",
    ),
    "factory_set_enabled_light_modes_binding": (
        0x1801EB940,
        0x2C,
        "0314610b9e94875c57bdd8fd1dfababbce7a805827dc9526940b6d26b1aa7e9f",
    ),
    "factory_set_enabled_light_modes_core": (
        0x1810D9110,
        0x5F,
        "79406081e2a52bc1cffaf23600ab6c734af8a0363a57cea61b1213f54b0a5abe",
    ),
    "runtime_record_blob_header_stack_spill_a": (
        0x1810CF36D,
        0x1FD,
        "eb9c311dada0796035df8d157335a699b79dc3f61c6ac7ac1bbcc5be87b46f4d",
    ),
    "runtime_record_blob_header_stack_spill_b": (
        0x1810D0725,
        0x1FF,
        "c9457062254ed9f3047b3dd1d1a629554423fa0effc07b91f2f71d1d1a78199c",
    ),
    "renderer_resource_slot_release": (
        0x180FBF6B0,
        0x119,
        "2afaddb9131b06e00ce20914992c37e1dcef0eb21a40feadfbef57786b95d1e0",
    ),
    "hg_resource_load_async_binding": (
        0x1801F2AB0,
        0x5A,
        "25b1324b6a8c25e3b51fd709a20825199f94afc08b31beff9d0e9909edd90792",
    ),
    "hg_resource_get_asset_binding": (
        0x1801F2B60,
        0xA8,
        "06af25eb0373cedee0f92863a57f400cb82fc3747333320a74c0a6ec1341be7e",
    ),
    "hg_resource_update_handle_binding": (
        0x1801F2C10,
        0x97,
        "91413130ea3650e6ed9592f585cdd605dd0ad271729550814ebefcbe6857e250",
    ),
    "renderer_resource_slot_acquire": (
        0x180FBFC60,
        0x224,
        "a3ce5ba53a311f4034772239e66a0b4258863e53a6985e273e27bbd8cb4e124d",
    ),
    "renderer_resource_slot_lookup": (
        0x1801F7410,
        0xDD,
        "644c1c7bc0c39844a8332babd6ad747a26bbe10c262b83b09575cfbf0ea22f9c",
    ),
    "runtime_record_scheduled_flag_consumer": (
        0x181064100,
        0x108D,
        "212141070fd1bb2189fe1ded35316a29f7805e4dd5b8f455fb34b213698f17dc",
    ),
    "renderer_entry_pass_mask_builder_a": (
        0x18109BE90,
        0xB33,
        "19720af63265ded47bc1d4fa1a4c474462409a2adc981a1a3544b4f12bd9be6a",
    ),
    "renderer_entry_pass_mask_builder_b": (
        0x18109C9D0,
        0xB03,
        "2e9108fc57e9b01f2b9b3f00b6dac9a092fdb5c84ed57397bcd66a83f2403f70",
    ),
    "runtime_record_blob_consumer_a": (
        0x181129E0D,
        0x53D,
        "85615fb8d3d99c9a395ae8a4ac749370301fc99c20c3860e14bee360b3c03d5b",
    ),
    "runtime_record_blob_consumer_b": (
        0x18113781A,
        0x55C,
        "8501dd4e046749d9aac8c90f9c9e790d1404441236fbca10655e7785e283b6f0",
    ),
    "runtime_record_blob_consumer_component_grouping": (
        0x18112A790,
        0x67E,
        "c18fa00a08895f70768e17736f7572cd66b79355a9715d9cdfd383894827c753",
    ),
    "runtime_record_batch_flag_classifier": (
        0x181131FC0,
        0xDD,
        "9e10b56296296a7cc7f6fc0cc5cc68eb16d4e084a641576f1bc8eae9c954db59",
    ),
    "runtime_record_blob_zero_initializer": (
        0x181CA0040,
        0x388,
        "ce960c33c8b79d15520559d78ace1a20770c9492363a9d2852578962e1ffa782",
    ),
    "runtime_record_full_blob_copy": (
        0x1810CE280,
        0x143,
        "cf1d0755ae2c40041eefd389ac80cc1f3cf0c436c8bb5a9a26dbda1fdb7eafc6",
    ),
    "factory_batched_entity_copy_current": (
        0x1810CE510,
        0x6A1,
        "aca0f9bae4d74c5797d6d868e1b7f4b03937bd831371687ccd520c94ded9a004",
    ),
    "factory_batched_entity_copy_obsolete": (
        0x1810CEBC0,
        0x6A1,
        "64d7e311baa06261b3de0d6b0f25b943bf6a64e72159abb18317b072e07aebfa",
    ),
    "renderer_list_callback_a": (
        0x181067A70,
        0x9E5,
        "9cb08eacc6c0fe3450579d040e87e2568a4d96975e45308b160c81f142ad4357",
    ),
    "ecs_archetype_bit_127_column_accessor": (
        0x181038D70,
        0x6C,
        "b2145b1812564195995ee12a388cbad16d0cf3648112304e1e7b1a79f97d7a43",
    ),
    "ecs_archetype_bit_126_column_accessor": (
        0x181038DE0,
        0x6C,
        "41479eb2db746f3c230bdc1c9c1a05489fd5ba6f4f852f0888d808d731d91630",
    ),
    "lod_direct_origin_0": (
        0x18106D7F0,
        0x295,
        "07812bfe77c8ad07f24945e15df36867949a23df4398058d3812b64f333bb2d5",
    ),
    "lod_direct_origin_0x18": (
        0x18106DA90,
        0x290,
        "f820d2511082cd529db74501b375f87d11142ba0567807800e1adfeda909769d",
    ),
    "lod_scaled_origin_0": (
        0x18106E0E0,
        0x31B,
        "6df30b7cd628d99341223e6b6ff877b7cd0d4044b4ea88788c786e2aebfdf571",
    ),
    "lod_scaled_origin_0x18": (
        0x18106E400,
        0x316,
        "bb50e7feb0003b53e5478cbb99c1054f6bf1906b16b27ca925e3fc6df2602e8f",
    ),
    "lod_job_dispatch_segment": (
        0x181079FB1,
        0x1B3,
        "5a7dc27ff07a05134333e3443828a6ba4f64f807de74198dba4181a494cc499c",
    ),
}

UNITY_GPU_DRIVEN_RENDERER_BODIES = {
    "v1_create_renderer_list_binding": (
        0x1801E8F50,
        0x104,
        "8f653840882c9756001ac93d29dcd065523823f2848fc2499b59ae5415554458",
    ),
    "v1_create_renderer_list_prez_binding": (
        0x1801E9060,
        0x116,
        "6df01bd3ee5e675b0e1ee35e44963448ceab49308826a47ac4fc1d04b45486dc",
    ),
    "v2_create_renderer_list_binding": (
        0x1801E9680,
        0xE3,
        "cf5891e6f6091f3a83596385d73f89e555ddc49f9479d0f1c772f0457742926b",
    ),
    "v2_create_renderer_list_prez_binding": (
        0x1801E9770,
        0xF5,
        "9056d3206f70a5113f1dd23e5005c9f79b8ca5beb2da3d348e211a51cb7a0996",
    ),
    "v1_create_renderer_list_core": (
        0x1810F0A80,
        0x650,
        "9d920cd0013b365aace2e42228906eedcabb5bbe67570f31d9cd56441858f552",
    ),
    "v1_create_renderer_list_prez_core": (
        0x1810F10D0,
        0x8B0,
        "b17a07bc42692440c890fcf84fc9e3ed383847fe775829388c464755565af5d9",
    ),
    "v2_create_renderer_list_core": (
        0x1810FD1B0,
        0x620,
        "f03ea39b9579a5986994c7b4fd3fdd95d67cfffc4b346b8eceb1e8b7a2082920",
    ),
    "v2_create_renderer_list_prez_core": (
        0x1810FD7D0,
        0x950,
        "6d5d6d96174ba1d37e00738ebb202f808e001797a3c06774d86b16200e7a7ff0",
    ),
    "v1_create_renderer_list_job_builder": (
        0x1810F0E70,
        0x25C,
        "2995b540f8d19c9c351719a7f02149889e08f35dc67e590c809eaf346cc0e429",
    ),
    "v1_create_renderer_list_prez_job_builder": (
        0x1810F1580,
        0x24A,
        "6cded6f20f818caf39282ec79a0de60ff73c4f55136bcfc5b494fbec44a6eccb",
    ),
    "v2_create_renderer_list_job_builder": (
        0x1810FD580,
        0x24C,
        "6195d27aca98386541cbf3b0c07fe141c30c679feff9582e3d956064209a42f7",
    ),
    "v2_create_renderer_list_prez_job_builder": (
        0x1810FDD40,
        0x246,
        "db075b6a31cef92704386f7d2b510db9e9d913010b258932a16d19480ab5b4cb",
    ),
    "v1_renderer_list_callback": (
        0x1810E6980,
        0x38C,
        "15da76527454166cffc89948c965d21913730d1224eee9411e223fbd3b63c37b",
    ),
    "v1_renderer_list_prez_callback": (
        0x1810E65F0,
        0x38C,
        "4c413f0f04cbb13dd7f990d9ee6ada5bcecb1123e0542580673f4aaca205e08d",
    ),
    "v2_renderer_list_callback": (
        0x1810F3970,
        0x38C,
        "ee36748b687e4e00102b5227b99158406b9fda5f9d32ebba55dd0b1249d8de2f",
    ),
    "v2_renderer_list_prez_callback": (
        0x1810F3560,
        0x40E,
        "f02fb9a0fe31c7331ed0815ddac7c2a11bb420314f79d5b8d31fb6bb844e56fa",
    ),
    "v1_record_consumer": (
        0x1810E87E0,
        0xA30,
        "3dd76e34c8ea1ae3cf3568472d98bcddb99d1f83202b90e736aef04ef2b7b7ed",
    ),
    "v1_prez_record_consumer": (
        0x1810E9AD0,
        0xDC0,
        "f00c103b05016298943c30bdd5f982a9340c5e5318f2c5f48c59d2efe4129310",
    ),
    "v2_record_consumer": (
        0x1810F58F0,
        0xA20,
        "eed2040a15f41aab2b236daed6b6f1495cad8de5f5c568798d00989f5ffdfd90",
    ),
    "v2_prez_record_consumer": (
        0x1810F6BC0,
        0xDA0,
        "883b74e0921779332e377abe17bae779ba9189fea4dc96bcf7c2c4f5469d22e5",
    ),
}

UNITY_RENDERER_BLOB_LOOKUP_VA = 0x180424C30
UNITY_RENDERER_BLOB_LOOKUP_CALL_SITES = [
    0x18042A407,
    0x18042AE1D,
    0x18042FF4D,
    0x1804300AA,
    0x18043076D,
    0x18043080D,
    0x1804308ED,
    0x180430D76,
    0x180431B22,
    0x180431C20,
    0x180432795,
    0x180432DB2,
    0x180BCBA50,
    0x180BCBEDC,
    0x1810416D9,
    0x18104189B,
    0x18104194B,
    0x1810419FB,
    0x181077CF1,
    0x181083941,
    0x181083DB6,
    0x181088E0D,
    0x1810C60E0,
    0x1810C7B3C,
    0x1810CAE29,
    0x1810CAE49,
    0x1810CB3D4,
    0x1810CE37D,
    0x1810CE38E,
    0x1810CF41D,
    0x1810D07D0,
    0x1810D8C9E,
    0x1810D8D2A,
    0x1810D8ED3,
    0x1810D8EE4,
    0x1810D9097,
    0x1810D9142,
    0x1810D9258,
    0x181129EF8,
    0x181129FAC,
    0x18112A4CF,
    0x18112A588,
    0x18112A87A,
    0x18112A92F,
    0x1811372EE,
    0x18113786B,
    0x18113788F,
    0x181153351,
    0x181154273,
    0x1811577B4,
    0x181159051,
    0x18115BCFB,
    0x18115C01B,
]
UNITY_RENDERER_BLOB_EXACT_0X7F00_CALL_SITES = [
    0x18042A407,
    0x18042AE1D,
    0x1804300AA,
    0x18043076D,
    0x18043080D,
    0x1804308ED,
    0x180430D76,
    0x180431B22,
    0x180431C20,
    0x180432795,
    0x180432DB2,
    0x180BCBA50,
    0x180BCBEDC,
    0x1810416D9,
    0x18104189B,
    0x18104194B,
    0x1810419FB,
    0x181077CF1,
    0x181088E0D,
    0x1810C60E0,
    0x1810C7B3C,
    0x1810CAE29,
    0x1810CB3D4,
    0x1810CE37D,
    0x1810CE38E,
    0x1810CF41D,
    0x1810D07D0,
    0x1810D8C9E,
    0x1810D8D2A,
    0x1810D8ED3,
    0x1810D8EE4,
    0x1810D9097,
    0x1810D9142,
    0x1810D9258,
    0x181129EF8,
    0x18112A4CF,
    0x18112A87A,
    0x18113786B,
    0x181153351,
    0x181154273,
    0x1811577B4,
    0x181159051,
    0x18115BCFB,
    0x18115C01B,
]
UNITY_RENDERER_BLOB_NON_0X7F00_CALL_SITES = [
    0x18042FF4D,
    0x181083941,
    0x181083DB6,
    0x1810CAE49,
    0x181129FAC,
    0x18112A588,
    0x18112A92F,
    0x1811372EE,
    0x18113788F,
]
UNITY_RENDERER_BLOB_EXACT_0X7F00_ENTRY_CFGS = [
    0x18042A130,
    0x18042AB50,
    0x180430082,
    0x18043073C,
    0x1804307DC,
    0x1804308BC,
    0x180430D39,
    0x180431AF1,
    0x180431BDF,
    0x180432750,
    0x180432CF5,
    0x180BCB760,
    0x1810416A0,
    0x181041870,
    0x181041920,
    0x1810419D0,
    0x181077CC3,
    0x181088DA5,
    0x1810C5F30,
    0x1810C7B0E,
    0x1810CAD13,
    0x1810CB2C0,
    0x1810CE280,
    0x1810CF36D,
    0x1810D0725,
    0x1810D8C60,
    0x1810D8D00,
    0x1810D8D40,
    0x1810D9050,
    0x1810D9110,
    0x1810D9220,
    0x181129E0D,
    0x18112A3DD,
    0x18112A790,
    0x18113781A,
    0x181153310,
    0x181154230,
    0x181157760,
    0x181159010,
    0x18115BC9B,
    0x18115BFC0,
]
UNITY_RENDERER_LIST_SCHEDULER_VA = 0x181080730
UNITY_RENDERER_LIST_SCHEDULER_CALL_SITES = [
    0x1810793C8,
    0x18107957E,
    0x18107AE3B,
    0x18107F258,
    0x18108012E,
    0x1810806E4,
]
UNITY_FACTORY_BATCHED_ENTITY_COPY_CALL_SITES = {
    0x1810CE510: [0x1801EB71A],
    0x1810CEBC0: [0x1801ECCB5],
}

UNITY_COMPONENT67_ACCESSOR_TARGETS = {
    "archetype": 0x181038D00,
    "indexed": 0x1811648A0,
}
UNITY_COMPONENT67_ACCESSOR_CALL_SITES = {
    "archetype": [
        0x181000F82,
        0x181001C42,
        0x181002D82,
        0x18106D886,
        0x18106DB26,
        0x18106DD63,
        0x18106DF43,
        0x18106E175,
        0x18106E495,
        0x18107873F,
        0x18107885A,
        0x181078A6E,
        0x181078B93,
        0x181078DB1,
        0x181078EFC,
        0x181079132,
        0x1810791FF,
        0x181084377,
    ],
    "indexed": [
        0x181153382,
        0x1811542A5,
        0x1811577EC,
        0x181159085,
        0x18115BD2E,
        0x18115C04C,
        0x18115C8F5,
    ],
}
UNITY_COMPONENT67_DIRECT_CALLER_BODIES = [
    (0x181000F10, 0xC70, "087217be9a67927ec8ec6931103bf140ced2b977869621c1af64257dd0730790"),
    (0x181001B80, 0x1140, "23d94a20fff2046551da81c97ab46cf693fb50b74a08263c4d32a9122f506270"),
    (0x181002CC0, 0xFC0, "31291eda4ed32ffa323564e97631849880347ab8542ca3bbe1249d98037bb46b"),
    (0x18106D7F0, 0x295, "07812bfe77c8ad07f24945e15df36867949a23df4398058d3812b64f333bb2d5"),
    (0x18106DA90, 0x290, "f820d2511082cd529db74501b375f87d11142ba0567807800e1adfeda909769d"),
    (0x18106DD28, 0x62, "f749da526577127d3c65b0ecfbce90b1dd7dfb102026a67db9e84aaaf6049218"),
    (0x18106DF08, 0x62, "cd685ce6a95e416cbe50580b2ea1f97139174e490480d6e6ef2c00ff31672780"),
    (0x18106E0E0, 0x31B, "6df30b7cd628d99341223e6b6ff877b7cd0d4044b4ea88788c786e2aebfdf571"),
    (0x18106E400, 0x316, "bb50e7feb0003b53e5478cbb99c1054f6bf1906b16b27ca925e3fc6df2602e8f"),
    (0x1810786B0, 0x32F, "d2d161fbd3a0e2a9e098459be320ce678f78bacf271aa4550eda9d793f25d276"),
    (0x1810789E0, 0x338, "fe20a855258edc7ce1f6f03b8707097f9f5f0bf5032a5dba555eda010237512f"),
    (0x181078D20, 0x389, "e08ec2badf29afcb7495d6852101f01018a576e343d46fa370390eca08e2a7f3"),
    (0x1810790B0, 0x26D, "b6a8c234cd19ae28af59b693462bc22508cb2c3de608e66a24e35c5eb490b7dc"),
    (0x1810842E0, 0x835, "b40cfccfcea9e2c91b65fba6ac51fa681f27b7fb6cdc89ae9539a0924b500418"),
    (0x181153310, 0x5DF, "4435143d7cce168aa670402d64f54cd6e813160dceab5e22b01ed28a05ad3d5c"),
    (0x181154230, 0x6C4, "4ae50616400e412b8c30c649765b11ad1e4906b9f7bf3e5f64a584ddc5027789"),
    (0x181157760, 0x7F9, "45633b35ac3c0bd27a71bb8464121584f185445ef18a7fe4a1e9b2808f074d63"),
    (0x181159010, 0x398, "c1f42c8333a1f0daf613485ee1757e78bdf95899ddcdcde81b7e177027dd8247"),
    (0x18115BC9B, 0x1DF, "677862bb3c6fd7276593230173875eb6469c8dcfbba30b91d10e23e3aefffa0a"),
    (0x18115BFC0, 0x196, "4564e22adf8397fb1c98654a17f014f26b9e170273db05e835c0ca0b534cc31f"),
    (0x18115C8A0, 0x13E, "c92e3ad737722d1bf874b259e5e871ae5365c61b20ae1dc1a51ae7a1a07ba723"),
]

UNITY_HGTREE_COMPONENT_TYPE_STRINGS = {
    "proxy_name": (
        0x181DA5EA0,
        "::Scripting::UnityEngine::HyperGryph::ECS::HGTreeComponentProxy",
    ),
    "native_type_name": (0x181DA5338, "HGTreeComponent"),
    "managed_namespace": (0x181D25758, "UnityEngine.HyperGryph.ECS"),
    "module_name": (0x181D25730, "UnityEngine.HGGraphicsModule.dll"),
}

UNITY_HGTREE_SLICES = {
    "create_renderer_list_render_flag_parameter_handoff": (
        0x1801D9D24,
        "418bd9418bf88bf28be9e82dc1de0080bc249000000000448bcf48c744244000"
        "000000448bc68bd5488b88c00000000f95c088442438488b842488000000488944"
        "2430488b8424800000004889442428895c2420",
    ),
    "create_renderer_list_core_render_flag_stack_handoff": (
        0x18107F1F7,
        "488b85c800000048898424880000008b85c0000000898424800000008b85b800"
        "0000894424788b85b00000008944247044896424684c8964246044895424584489"
        "5c245048895c244848897c2440897424384c897424304c896424284c897c2420e8"
        "d3140000",
    ),
    "renderer_list_scheduler_render_flag_descriptor_copy": (
        0x1810807BE,
        "8b8424d80000008943388b8424e000000089433c8b8424e80000008943408b84"
        "24f0000000894344486384",
    ),
    "shadow_proxy_geometry_handle_render_flag_filter": (
        0x181064B66,
        "418b451c8541440f84720300008b443204410b451823413c3b41400f855e030000",
    ),
    "hg_geometry_handle_encoding": (
        0x18108B51E,
        "0fb747064c8d9c24d0000000498b5b3866ffc0498b7340b9ff0000006623c10f"
        "b7c066894706c1e018410bc5",
    ),
    "hg_geometry_get_mesh_handle_decode": (
        0x1801EE5E5,
        "488b80a000000081e3ffffff00448bc3448bcb8b4840488b502849d3e88b4844"
        "ffc94923c94a8b04c2486bc9388b0401488d4c24",
    ),
    "hg_geometry_map_insert_handoff": (
        0x181094416,
        "4d8bc78bd5488bcfe89d6dffff488d4f08898424c00000004c8d8c24c0000000"
        "4c8d8424b0000000488d542430e8782b16ff4c8bbc248000",
    ),
    "hg_geometry_map_remove_handle_decode": (
        0x1810999DC,
        "8b4e40488dbec80000008b4308488b562825ffffff00448bc049d3e88b4e4444"
        "8bc8ffc94923c948896c24504a8b04c2486bc938",
    ),
    "mesh_geometry_registration_call": (
        0x181372830,
        "807b7c007519e82536c5ff8b5308488b88a00000004883c4205be9a119d2ff",
    ),
    "mesh_geometry_unregistration_call": (
        0x1813773C4,
        "488bf1e894eac4ff8b5608488b88a0000000e8a525d2ff33ed4839ae",
    ),
    "hgmesh_runtime_resource_fields_and_maps": (
        0x181088DB2,
        "e8a9d0f3ff488b583848895c2430e89bd0f3ff4c8bb0a0000000e88fd0f3ff"
        "498b5550488b889000000048898c24b8000000488bcbe8844c3aff448b004181"
        "e0007f00000f84cb020000498b5550488bcb48897c24704c897c2458e81ebe39"
        "ff498b4d484533ff498b7d484883c15848898c24a80000004883c778498b4d48"
        "4881c1980000004889bc24b000000048894c2420",
    ),
    "hgmesh_runtime_material_map_write": (
        0x181088F75,
        "8946fc488b074963cf488d0c88",
    ),
    "hgmesh_runtime_main_mesh_map_write": (
        0x181088FEF,
        "488b5c242089064963cf488b03488d0c88",
    ),
    "hgmesh_runtime_shadow_proxy_map_write_and_stride": (
        0x181089063,
        "8b4008eb0233c089460441ffc74883c61848ffc54983c404",
    ),
    "hgmesh_serialized_materials_field": (
        0x1810A919B,
        "488d1516decb00c644242001488bcbe8d12473ff85c0743183f8017c114533c0"
        "488d5758488bcbe8790d38ffeb",
    ),
    "hgmesh_serialized_meshes_field": (
        0x1810A91F0,
        "488d158965d700c644242001488bcbe87c2473ff85c0743183f8017c114533c0"
        "488d5778488bcbe84480fcffeb",
    ),
    "hgmesh_serialized_shadow_proxy_meshes_field": (
        0x1810A9245,
        "488d154465d700c644242001488bcbe8272473ff85c0743783f8017c144533c0"
        "488d9798000000488bcbe8ec7ffcffeb1648",
    ),
    "merged_renderer_second_mesh_slot_acquire": (
        0x1811534FE,
        "4c392f0f84ed000000488b1f488d55504c8bc3668944242041b902000000498bcc"
        "e83cc7e6ff8b455089471448895d",
    ),
    "renderer_second_mesh_slot_acquire": (
        0x1811546C6,
        "48833f000f84f3000000488b1f488d556f4c8bc3668944242041b902000000498bcf"
        "e873b5e6ff8b456f894714",
    ),
    "merged_renderer_mesh_filter_word_resolve": (
        0x1811579C1,
        "498b45288b0e48c1e1050f1004010f104c01100f114560660f7ec83c017567418b"
        "4710498d4f084883c004660f73d9084c8d4111660f7e8d70010000488d95700100"
        "00488d1c40480319e800fa09ff488bd0483bc3730e833afe72094883c20c483bd372"
        "f2418b47104883c004488d0c4049034f08483bca750433c0eb038b42084189443e0c",
    ),
    "renderer_mesh_filter_word_resolve": (
        0x18115919F,
        "488b43288b0e48c1e1050f104c0110660f7ec83c017567418b4510498d4d084883"
        "c004660f73d9084c8d4111660f7e8c24c0000000488d9424c0000000488d3c4048"
        "0339e828e209ff488bd0483bc7730e833afe72094883c20c483bd772f2418b451048"
        "83c004488d0c408bc549034d08483bca74038b4208438944260c",
    ),
    "gpu_driven_callbacks_request_mask_0x54": (
        0x1810E69C9,
        "8b4954488985a00000000fb6c20fa3c17308ffc741881049ffc0fec280fa1f72e9",
    ),
    "gpu_driven_v1_prez_callback_request_mask_0x54": (
        0x1810E6639,
        "8b4954488985a00000000fb6c20fa3c17308ffc741881049ffc0fec280fa1f72e9",
    ),
    "gpu_driven_v2_callback_request_mask_0x54": (
        0x1810F39B9,
        "8b4954488985a00000000fb6c20fa3c17308ffc741881049ffc0fec280fa1f72e9",
    ),
    "gpu_driven_v2_prez_callback_request_mask_0x54": (
        0x1810F35A8,
        "8b4954488985a00000000fb6c20fa3c17308ffc741881049ffc0fec280fa1f72e9",
    ),
    "gpu_driven_v1_record_base": (
        0x1810E8C2F,
        "4c8b742448498bc2488945284983c60c90",
    ),
    "gpu_driven_v1_enabled_light_modes_filter": (
        0x1810E8E63,
        "48837f28004c8b4424400f84c0020000458b6608440b6718418b4054440be685471c"
        "0f84a1020000418b40484123c4413b404c0f8590",
    ),
    "gpu_driven_v1_record_stride": (
        0x1810E9133,
        "488b7c2438488b45284983c61848ffc04883eb014889452848895d30",
    ),
    "gpu_driven_v1_prez_record_base": (
        0x1810E9FCA,
        "4c8d59104c895c24",
    ),
    "gpu_driven_v1_prez_enabled_light_modes_filter": (
        0x1810EA245,
        "418b7304410b76180b75608b4754897424444185461c0f844b0500008b474823c6"
        "3b474c0f853d",
    ),
    "gpu_driven_v1_prez_record_stride": (
        0x1810EA7B5,
        "488b85900000004983c31848ffc04c895c24484883ad980000000148898590000000",
    ),
    "gpu_driven_v2_record_base": (
        0x1810F5D46,
        "4c8d7a0c48894538",
    ),
    "gpu_driven_v2_enabled_light_modes_filter": (
        0x1810F5F6F,
        "48837f28004c8b4424400f84c3020000458b6708440b6718418b4054440be68547"
        "1c0f84a4020000418b40484123c4413b40",
    ),
    "gpu_driven_v2_record_stride": (
        0x1810F6242,
        "488b7c2438488b45384983c71848ffc048836d400148894538",
    ),
    "gpu_driven_v2_prez_record_base": (
        0x1810F70D9,
        "4c8d51104c895424",
    ),
    "gpu_driven_v2_prez_enabled_light_modes_filter": (
        0x1810F7337,
        "448bcb410fbae90f4885f6440f44cb49837d280044894c24340f842b050000418b72"
        "04410b75180b75588b4754897424444185451c0f840b0500008b474823c63b474c0f85",
    ),
    "gpu_driven_v2_prez_record_stride": (
        0x1810F7881,
        "4c8b5c2438488b45704983c21848ffc04c8954244848836d780148894570",
    ),
    "instance_renderer_array_to_nested_serializer": (
        0x18106FAE2,
        "896c24204c8d050b59cb00488bce488d15658ace00e884b976ff"
        "488bd6488d4c2430e867020000",
    ),
    "renderer_lod_offsets_write": (
        0x18106FEB6,
        "4c8b05934dcf004c8d4f14488d1540e7da00896c2420"
        "488bcee8acb576ff488b4640488b564848c1e205488b08"
        "c7440a0c04000000488bcee8edc276ff4c8b05564dcf00"
        "4c8d4f18488d151be7da00896c2420488bcee86fb576ff",
    ),
    "renderer_lod_offsets_read": (
        0x1810703F1,
        "488d57144533c94c8d0509e2da00488bcbe8c9bd26ff"
        "488d57184533c94c8d050be2da00488bcb",
    ),
    "create_renderer_list_to_core": (
        0x1801D9D2E,
        "e82dc1de0080bc249000000000448bcf48c744244000000000"
        "448bc68bd5488b88c00000000f95c088442438488b842488000000"
        "4889442430488b8424800000004889442428895c2420e8c350ea00"
        "488b5c2460",
    ),
    "renderer_list_job_callback_selection": (
        0x1810808D0,
        "7504498d6e080f104500488d058f71feff4d85ff4c8d05a548feff"
        "4c8bcb4c0f44c0488d4c24",
    ),
    "renderer_list_light_mode_mask_job_store": (
        0x1810807D0,
        "433c8b8424e80000008943408b8424f000000089434448638424a8000000"
        "488bc8894348",
    ),
    "renderer_list_callback_a_entry_light_mode_test": (
        0x181067FFF,
        "478b2426440b6718440ba5880100008b471c418bd481e20000060041854544",
    ),
    "renderer_list_callback_b_entry_light_mode_test": (
        0x181064B66,
        "418b451c854144",
    ),
    "renderer_entry_pass_mask_build_a": (
        0x18109C349,
        "c7471c00000000498b4f10e8379a5bff32db4c8d35ce29d80048634858488b00"
        "488b34c80f1f000fb6d3488d8d500a000041b8ffffffff498b14d6e827e353ff"
        "8b95500a000080fb0b752d498b8718010000498b8f280100004c8d0488493bc0"
        "74160f1f44000039100f84c90000004883c004493bc075ef498b871801000049"
        "8b8f280100004c8d0488493bc0741139100f84b30000004883c004493bc075ef"
        "488bcee82f3e58ff0fb6cb8844393084c0780c8b4f1c0fb6c30fabc1894f1cfe"
        "c380fb1f0f82",
    ),
    "renderer_entry_pass_mask_build_b": (
        0x18109CE57,
        "89771c498b4f10e82d8f5bff32db4c8d2dc41ed80048634858488b00488b34c8"
        "660f1f8400000000000fb6d3488d8d500a000041b8ffffffff498b54d500e816"
        "d853ff8b95500a000080fb0b752c498b8718010000498b8f280100004c8d0488"
        "493bc074150f1f400039100f84c20000004883c004493bc075ef498b87180100"
        "00498b8f280100004c8d0488493bc0741139100f84ac0000004883c004493bc0"
        "75ef488bcee81f3358ff0fb6cb8844393084c0780c8b4f1c0fb6c30fabc1894f"
        "1cfec380fb1f0f82",
    ),
    "runtime_record_lookup_a": (
        0x181129EEE,
        "488b4f084d8bc6488bd3e833ad2fff448b384c8d7004",
    ),
    "hg_resource_load_async_forwards_asset_type": (
        0x1801F2AC5,
        "4d8bf1410fb7d88bfa488bf1e88a33dd00448bcf66895c24204c8bc6488d542458"
        "488b4848e871d1dc00",
    ),
    "merged_render_third_resource_acquire_as_mesh": (
        0x1811535F4,
        "4c396f080f84f0000000488b5f08488d55584c8bc366c74424200f00"
        "41b902000000498bcce842c6e6ff8b4558",
    ),
    "render_third_resource_acquire_as_mesh": (
        0x1811547C3,
        "48837f08000f84f6000000488b5f08488d55774c8bc366c74424200f00"
        "41b902000000498bcfe872b4e6ff8b4577",
    ),
    "merged_render_third_resource_to_runtime_0x0c": (
        0x181157A47,
        "48837ef4000f8484000000498b45288b4e0448c1e1050f100401"
        "0f104c01100f114560660f7ec83c017564418b4710498d4f084883c004"
        "660f73d9084c8d4111660f7e8d70010000488d9570010000488d1c40"
        "480319e86ef909ff483bc3730e8338fe72094883c00c483bc372f2"
        "418b4f104883c104488d144949035708483bd0750433c0eb038b4008"
        "4189443e10",
    ),
    "render_third_resource_to_runtime_0x0c": (
        0x18115921D,
        "48396ef40f847e000000488b43288b4e0448c1e1050f104c0110"
        "660f7ec83c017566418b4510498d4d084883c004"
        "660f73d9084c8d4111660f7e8c24c0000000488d9424c0000000488d3c40"
        "480339e89fe109ff483bc7730e8338fe72094883c00c483bc772f2"
        "418b4d104883c104488d144949035508483bd075048bc5eb038b4008"
        "4389442610",
    ),
    "runtime_record_escape_a": (
        0x18112A243,
        "488b557f413bf7488b4f108bd8440f4cfe4533c0458bcf"
        "e8617d0000488b75af88",
    ),
    "runtime_record_lookup_b": (
        0x181137858,
        "8b4e08488bd3488b384c8bc74181e0007f0000e8c0d32eff"
        "488b4e0849b80000000000c003004c23c7488bd3448b204c8d7004",
    ),
    "runtime_record_escape_b_first": (
        0x181137B6A,
        "488b557f453bf4488b4e108bf8450f4ce64533c0458bcce8"
        "3aa4ffff41884504",
    ),
    "runtime_record_escape_b_second": (
        0x181137C6D,
        "488b557f453bf4488b4e108bf8450f4ce64533c0458bcce8"
        "37a3ffff4188450441c64505",
    ),
    "runtime_record_batch_flag_classifier_loop": (
        0x181131FDC,
        "488d5a044d63c04f8d0c404a8d1ccb0f1f440000448b1b4585db0f8481000000"
        "8b5644458bcb8b4e40ffca4c8b46284181e1ffffff004923d1458bd149d3ea48"
        "8d14524b8b0cd048c1e205440fb7441126418bcbc1e91866443bc175448b5644"
        "4181e3ffffff008b4e40ffca4c8b4628458bcb4923d1458bd349d3ea488d0c52"
        "48c1e1054b030cd0f74118007a000074040c04eb0cf641181074040c02eb020c01"
        "4883c3184883ef01",
    ),
    "renderer_list_callback_a_ecs_column_projection": (
        0x181067D14,
        "488bcbe85410fdff488bcb4c8be8e8b910fdff488b0b4c8be0",
    ),
    "renderer_list_callback_a_component_float_read": (
        0x181067E9E,
        "498d542408488b5dc04d8d4d14448ba5800100004983c60c418bc74d2bc24889"
        "45f04c8b7df0488b45c84c894424304c894d00488955084c89742438660f1f44"
        "00004c8bad700100004485248b0f84aa0400004c8b5d28418b41f02504000600"
        "898588010000488b45d8f3420f104c9818f3460f1044981cf3440f5c42fcf342"
        "0f10449820496346f4488945e8f30f5c4af8f3450f59c0f30f5c02f30f59c9"
        "f30f59c0f3440f58c1f3440f58c0f3450f5801",
    ),
    "renderer_list_callback_a_component_stride": (
        0x181068393,
        "4c8b5dd0488b45c848ffc14983c1184d03d748894df8",
    ),
    "register_tree_batch_group_to_core": (
        0x1801DA12F,
        "e82cbdde00488b4c2430488bb8c0000000e8cba55800488b4c2448"
        "8bd8e8bfa55800448bcb6689742420448bc08bd5488bcfe8eabeea00",
    ),
    "compact_job_runtime_record_steps": (
        0x181068345,
        "4c8b7424384c8b442430488b45e0488345b81848ffc048836de801"
        "4c8b65b8488945e00f8502fcffff488b7c2460488b4df8488b5508"
        "4c8b4d004c8b542458488b5dc04c8b7df0448ba5800100004c8b5d"
        "d0488b45c848ffc14983c1184d03d748894df84d03f34c894d0048"
        "83c2144c895424584883c7604c897424384889550848897c2460483b"
        "c8",
    ),
    "transform_capacity_buckets": (
        0x1810C60E5,
        "486395c000000089104c8d600483fa017f07b91c000000eb36"
        "83fa027f07b934000000eb2a83fa047f07b964000000eb1e83fa"
        "087f07b9c4000000eb1283fa10b90403000041b884010000410f"
        "4ec84803c1",
    ),
    "transform_record_and_lod_mapping": (
        0x1810C6160,
        "498b7f2066894c2460488b8d980000000fb7443e10448b4c3e08"
        "448b443e0c8b143e6689442420e8c4fefbff668944246233c98b"
        "043e488d761c894424644d8d6424188b443ee88944246848894c"
        "246c0f10442460894c2474f20f104c2470410f114424e8f2410f"
        "114c24f8f30f10443ef8f30f104c3efcf30f1185b0000000f30f"
        "118db4000000488b85b00000004a8904f349ffc64d3bf5",
    ),
    "transform_direct_caller": (
        0x1810C9663,
        "4c8bc744897c2430498bcc48896c242848895c2420488b9c24b0"
        "0000004c8bcbe8a8c8ffff",
    ),
    "transform_owner_cleanup_handle_key_loop": (
        0x1810BD080,
        "440fb747fe498bce8b17e871adfcff488d7f184883ee0175e74533f6",
    ),
    "renderer_base_enabled_light_modes_default": (
        0x18042C018,
        "66c78748020000010089874c020000488b0572a2930148898768020000"
        "c78750020000ffffffff89b7540200004889b7580200004889b760020000",
    ),
    "renderer_record_enabled_light_modes_copy_path_a": (
        0x18042AA88,
        "8b442440488bcf8946088b44244489460c8856020fb68744020000884603"
        "488b07ff900801000066090641ffc68b461049ffc725fdfb01f0410bc48946"
        "108b87500200008946144883c6184d3bfd",
    ),
    "renderer_record_enabled_light_modes_copy_path_b": (
        0x18042B498,
        "8b442440488bcf8946088b44244489460c8856020fb68744020000884603"
        "488b07ff900801000066090641ffc68b461049ffc725fdfb01f0410bc48946"
        "108b87500200008946144883c6184d3bfd",
    ),
    "generic_renderer_enabled_light_modes_input_handoff": (
        0x180BCCD76,
        "498b064889442448418b855002000089442450488b014889742430ff5018"
        "8bc8b801000000d3e0498b4d30894583e8d73175ff48894587498b45304c"
        "896da70fb64855410fb7854402000066894593488b457f48894597498b4708"
        "4889459f498d4760894d8f488d4c2430488945afe876e9ffff",
    ),
    "generic_renderer_enabled_light_modes_record_copy": (
        0x180BCBE79,
        "8b431025fdfb01f00b85880000008943108b46208943144883c3184963c5483bc2",
    ),
    "lod_ecs_availability_unload_clear": (
        0x1810845E0,
        "410fb6c68bcd2bc8ba0100000048d3e28bc8410fb6400448ffca48d3e2"
        "410fb6cf48f7d2492150080fb3c841884004410fb640050fb3c841884005",
    ),
    "lod_ecs_availability_complete_transition": (
        0x18108491A,
        "498b400848ffca48d3e24823c2483bc27520410fb64804410fb6c10fb3c1"
        "410fb6c141884804410fb648050fabc141884805",
    ),
    "lod_ecs_availability_request_set": (
        0x181084A65,
        "4c8b442450400fb6c6410fb648040fabc18d45ff41884804",
    ),
    "lod_ecs_initial_completion_transition": (
        0x18115907C,
        "488bd3488bce488bf8e816b800004d8b561033ed4d8b6e184c899424c8000000"
        "80780401751f410fb6cfba0100000048d3e24532c048ffca66c74004000132c9"
        "4532c9eb10b1084532ff440fb6c1440fb6c9488bd54488480144884002884803"
        "48895008",
    ),
    "lod_direct_interval_equation": (
        0x18106D8F0,
        "f30f104bf832c9f30f1053fcf3410f5c542404f3410f5c0c24"
        "f30f1003f3410f5c442408438b44280ef30f59d2f30f59c9448b"
        "1c86f30f59c0f30f58d1f30f58d0413848fe7645450fb648fe0f"
        "1f400084c9750432d2eb090fb6c1420fb654000d0fb6c1423a54"
        "000e741a0fb6c2f3410f1004c20f2fc2720c410f2f54c2040f87"
        "9c000000fec1413ac972c4",
    ),
    "lod_scaled_interval_equation": (
        0x18106E210,
        "41807e3500418b4c000ef3410f105e28f3410f10648d00f3410f"
        "102c8c448b148f74050f28d7eb34f30f104df8f30f1055fcf341"
        "0f5c5604f3410f5c0ef30f104500f3410f5c4608f30f59d2f30f"
        "59c9f30f59c0f30f58d1f30f58d0f30f595d04410f28c032c9"
        "f30f5fc2f30f5ed8413848fe765b450fb648fe660f1f44000084c9"
        "750432d2eb090fb6c1420fb654000d0fb6c1423a54000e742e0fb6"
        "c20f28cc0f2f74c304f30f590cc376050f28c5eb030f28c40f2f"
        "cbf30f5944c30472090f2fd80f87ae000000fec1413ac972b0",
    ),
    "lod_job_variant_dispatch": (
        0x181079FCC,
        "40387b3c0f84b300000085c90f8e56010000448bf70f1f400066"
        "66660f1f840000000000488b034c8bce4c8b50084d03d6498b02"
        "8b501848c1ea0bf6c201488b137428488b034883c2184889542428"
        "48052c080000488d530848894424204c8bc5498bcae8cb3effffeb"
        "3b4c8b034883c218488b48104981c02c08000048c1e93a48895424"
        "28f6c1014c89442420488d53084c8bc5498bca7407e8253affffeb"
        "05e88e43ffff488b03ffc74983c6103b78100f8c6cffffffe9ab00"
        "000085c90f8ea30000004c8bf70f1f40000f1f840000000000488b"
        "034c8bce4c8b50084d03d6498b028b501848c1ea0bf6c201488b13"
        "7428488b034883c218488954242848052c080000488d530848894424"
        "204c8bc5498bcae83b3cffffeb3b4c8b034883c218488b48104981"
        "c02c08000048c1e93a4889542428f6c1014c89442420488d53084c"
        "8bc5498bca7407e8d536ffffeb05e8be3fffff",
    ),
}

UNITY_RENDERER_ENTRY_PASS_NAME_TABLE_VA = 0x181E1ED30

UNITY_HGTREE_FLOAT_CONSTANTS = {
    "scaled_lod_forced_distance_squared": (0x181CF22E4, 0x3F800000),
    "scaled_lod_distance_squared_floor": (0x181D18140, 0x38D1B717),
}

UNITY_HGTREE_FIELD_NAMES = {
    0x181E1F768: "m_EntityComponentData",
    0x181D66FB8: "m_Materials",
    0x181E1F780: "m_Meshes",
    0x181E1F790: "m_ShadowProxyMeshes",
    0x181E1F7A8: "m_ColliderData",
    0x181E1F7B8: "m_ColliderMeshes",
    0x181D253F8: "HGTreeRenderer",
    0x181D25408: "HGTreeInstance",
    0x181E1E4F4: "bounds",
    0x181E1E560: "rendererHalfSize",
    0x181E1E578: "objectFlags",
    0x181D774E8: "renderers",
    0x181E1E588: "rendererOffsets",
    0x181E1E598: "colliderData",
    0x181E1E5A8: "colliderMeshes",
    0x181E1E5B8: "objectToWorld",
    0x181E1E5C8: "param0",
    0x181E1E5D0: "param1",
    0x181E1E5D8: "batchKey",
    0x181E1E5E8: "renderFlags",
    0x181CF20A0: "mesh",
    0x181CF2268: "material",
    0x181E1E5F8: "subMeshIndex",
    0x181E1E608: "lodScreenSizeMaxSquared",
    0x181E1E620: "lodScreenSizeMinSquared",
}

UNITY_CULLING_SLICES = {
    "binding_to_result_wrapper": (0x1800FBD2B, "e89052f500"),
    "result_wrapper_to_candidate_core": (0x18105104A, "e8f1090000"),
    "fallback_mode_gate_manager_9d8": (0x181051A5E, "80b9d809000000"),
    "pc_device_tier_gate": (
        0x1810520A0,
        "8b95c002000085d2782eb888130000663987ee00000075043bd07d1c0fb787ec0000003bc27f0b0fb787ee0000003bc27d0644893e418bcf",
    ),
    "maximum_culling_distance_gate": (
        0x181052124,
        "44387ff27414f30f10472cf30f59c00f2ff87606418bcf44893e",
    ),
    "minimum_far_show_distance_gate": (
        0x18105213E,
        "4438bfe10000007416f30f108724010000f30f59c00f2fc7760544893eeb5c",
    ),
    "explicit_obb_gate_and_builder": (
        0x181052161,
        "44387ff07452f3410f10064c8d4710f3410f104e04488d5704f3410f1056084c8d8dd0000000f30f5847f8f30f584ffcf30f5817488d8d80000000f30f118580000000f30f118d84000000f30f119588000000e8b7a0ffff",
    ),
    "light_type_geometry_branches": (
        0x1810521C2,
        "4183fc010f842d0300004585e40f84b10000004183fc020f854a01000048",
    ),
    "spot_frustum_helper_call": (
        0x1810522FF,
        "f30f5905f1ffc900f3410f59c7f30f11442428f30f1047acf30f11442420e8aef3ffff84c0750344893e",
    ),
    "occlusion_query_and_result_bit": (0x18105261B, "e880e50600f60601"),
    "native_distance_sort_call": (0x18105280C, "e81f10ffff"),
    "native_output_max_count_cap": (0x181052830, "443ba5b00200007351"),
    "candidate_pointer_distance2_row": (0x181052913, "f20f1102f30f117a08"),
    "ascending_float_sort_comparison": (
        0x181043948,
        "f30f1047084803c7f20f1033488bd366410f6ece0f2fc10f86fc010000",
    ),
}

TEXT_ASSETS = {
    "SettingFiles": (
        "SettingFiles_pA5D65C734C247CA7.txt",
        "6031cb98e345cd347830658d3661067af0a6b34ca58f92bc5f9ee6f0ed75d14c",
        "0xA5D65C734C247CA7",
    ),
    "HGRenderPipelineSettings": (
        "HGRenderPipelineSettings_p0EA7FF83EAC093AD.txt",
        "05a4fb96d13a4766757c965df6c5c2a478964ab40d8d2df31659a39e6b710abf",
        "0x0EA7FF83EAC093AD",
    ),
    "CommonSettings": (
        "CommonSettings_p2936E10EDCE2C9E4.txt",
        "aed529949a67769c9066ead730aea1f4144cc8f9ecd63d5debf6e59670649049",
        "0x2936E10EDCE2C9E4",
    ),
    "DesktopSettings": (
        "DesktopSettings_p99C7C961A15A8994.txt",
        "a4a0b652162a13e5c5cad39e7c290641dd83116b984d884e246cacf7991f1f10",
        "0x99C7C961A15A8994",
    ),
    "CloudDesktopOverride": (
        "CloudDesktopOverride_p4CDB7A1FBABEC323.txt",
        "439af33ecca9b7b400a6b92b17ca279b488d47652b04296d95d868b85a7be7f4",
        "0x4CDB7A1FBABEC323",
    ),
    "ConsoleSettings": (
        "ConsoleSettings_p6DB117C9F26E1FCE.txt",
        "0d077462addf6478a90abf6584f6e0844c8b3ef0ff929465dc6c04c6b2e3ea69",
        "0x6DB117C9F26E1FCE",
    ),
    "MobileSettings": (
        "MobileSettings_p883CA7EF83FC2F7C.txt",
        "f9f3388bf3ddb6c0dfbecdac952244044589acb4bb6d7231f0e41a968e463a72",
        "0x883CA7EF83FC2F7C",
    ),
    "CinematicSettings": (
        "CinematicSettings_p02A48AAA604195BF.txt",
        "c0cd749dd829222aab2a2761e0ca7e61ed0d72e87dd2d294a3c65e2bc9358c73",
        "0x02A48AAA604195BF",
    ),
}

EXPECTED_SETTING_FILES = [
    "CommonSettings.ini",
    "ConsoleSettings.ini",
    "DesktopSettings.ini",
    "CloudDesktopOverride.ini",
    "MobileSettings.ini",
    "CinematicSettings.ini",
    "HGRenderPipelineSettings.ini",
]

EXPECTED_INCLUDE_ROUTES = {
    "Common": "CommonSettings.ini",
    "Handheld": "MobileSettings.ini",
    "Desktop": "DesktopSettings.ini",
    "Desktop.Cloud": "CloudDesktopOverride.ini",
    "Console": "ConsoleSettings.ini",
    "Cinematic": "CinematicSettings.ini",
}

EXPECTED_CAP_DEFINITIONS = {
    "ConsoleSettings": [256],
    "DesktopSettings": [256],
    "MobileSettings": [32],
}

EXPECTED_SCREEN_THRESHOLD_DEFINITIONS = {
    "MobileSettings": [0.0, 0.0, 0.0],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(check: str, actual: object, expected: object, source: Path | str) -> None:
    if actual != expected:
        raise AssertionError(
            "Light-cull cap audit failed: "
            f"validator=light_cull_cap; check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verified_hash(name: str, path: Path) -> str:
    require(f"{name}_exists", path.is_file(), True, path)
    actual = sha256(path)
    require(f"{name}_sha256", actual, EXPECTED_HASHES[name], path)
    return actual


class PEImage:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        require("unity_player_pe_signature", self.data[pe : pe + 4], b"PE\0\0", path)
        section_count = struct.unpack_from("<H", self.data, pe + 6)[0]
        optional_size = struct.unpack_from("<H", self.data, pe + 20)[0]
        optional = pe + 24
        require(
            "unity_player_pe32_plus",
            struct.unpack_from("<H", self.data, optional)[0],
            0x20B,
            path,
        )
        self.image_base = struct.unpack_from("<Q", self.data, optional + 24)[0]
        self.sections: list[tuple[int, int, int, int]] = []
        cursor = optional + optional_size
        for _ in range(section_count):
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
                "<IIII", self.data, cursor + 8
            )
            self.sections.append(
                (virtual_address, max(virtual_size, raw_size), raw_offset, raw_size)
            )
            cursor += 40

    def file_offset(self, virtual_address: int) -> int:
        relative = virtual_address - self.image_base
        for section_va, span, raw_offset, raw_size in self.sections:
            if section_va <= relative < section_va + span:
                delta = relative - section_va
                require(
                    f"unity_player_va_{virtual_address:X}_file_backed",
                    delta < raw_size,
                    True,
                    self.path,
                )
                return raw_offset + delta
        raise AssertionError(
            "Light-cull cap audit failed: "
            f"validator=light_cull_cap; check=unity_player_va_mapping; "
            f"source={self.path}; expected='file-backed VA'; actual='0x{virtual_address:X}'"
        )

    def read(self, virtual_address: int, size: int) -> bytes:
        offset = self.file_offset(virtual_address)
        return self.data[offset : offset + size]

    def u64(self, virtual_address: int) -> int:
        return struct.unpack("<Q", self.read(virtual_address, 8))[0]

    def cstring(self, virtual_address: int) -> str:
        offset = self.file_offset(virtual_address)
        end = self.data.index(0, offset)
        return self.data[offset:end].decode("utf-8")


def relative_call_target(body: bytes, method_va: int, offset: int) -> int:
    require(
        f"native_call_{method_va + offset:X}_opcode",
        body[offset],
        0xE8,
        GAME_ASSEMBLY,
    )
    displacement = struct.unpack_from("<i", body, offset + 1)[0]
    return method_va + offset + 5 + displacement


def count_legacy_movss_disp_loads(body: bytes, displacement: int) -> int:
    """Count legacy MOVSS scalar loads using an exact memory displacement.

    This intentionally covers the legacy F3 0F 10 encoding emitted throughout
    the pinned UnityPlayer culling bodies.  It is used only as a transparent
    negative boundary inside an already hash-pinned function body.
    """

    count = 0
    cursor = 0
    while cursor < len(body):
        if body[cursor] != 0xF3:
            cursor += 1
            continue
        opcode_offset = cursor + 1
        if opcode_offset < len(body) and 0x40 <= body[opcode_offset] <= 0x4F:
            opcode_offset += 1
        if (
            opcode_offset + 2 >= len(body)
            or body[opcode_offset : opcode_offset + 2] != b"\x0F\x10"
        ):
            cursor += 1
            continue
        modrm_offset = opcode_offset + 2
        modrm = body[modrm_offset]
        mode = modrm >> 6
        memory_form = mode != 3
        rm = modrm & 7
        displacement_offset = modrm_offset + 1
        if memory_form and rm == 4:
            displacement_offset += 1
        if mode == 1 and displacement_offset < len(body):
            actual = struct.unpack_from("<b", body, displacement_offset)[0]
            count += actual == displacement
        elif mode == 2 and displacement_offset + 4 <= len(body):
            actual = struct.unpack_from("<i", body, displacement_offset)[0]
            count += actual == displacement
        cursor += 1
    return count


def find_relative_call_sites(image: PEImage, target: int) -> list[int]:
    """Find every file-backed E8 rel32 byte sequence resolving to target."""

    call_sites = []
    for section_va, _span, raw_offset, raw_size in image.sections:
        body = image.data[raw_offset : raw_offset + raw_size]
        cursor = body.find(b"\xE8")
        while cursor >= 0 and cursor + 5 <= len(body):
            displacement = struct.unpack_from("<i", body, cursor + 1)[0]
            virtual_address = image.image_base + section_va + cursor
            if virtual_address + 5 + displacement == target:
                call_sites.append(virtual_address)
            cursor = body.find(b"\xE8", cursor + 1)
    return sorted(call_sites)


def read_native_method_bodies(game_assembly: Path = GAME_ASSEMBLY) -> dict[str, bytes]:
    bodies: dict[str, bytes] = {}
    with game_assembly.open("rb") as stream:
        for name, spec in NATIVE_METHODS.items():
            stream.seek(int(spec["fileOffset"]))
            bodies[name] = stream.read(int(spec["sizeBytes"]))
    return bodies


def validate_managed_streaming_component_bindings(
    body: bytes,
) -> dict[str, object]:
    """Close the complete managed Mono-component binding set in the ctor."""

    spec = NATIVE_METHODS["streaming_scene_manager_ctor"]
    method_va = int(spec["virtualAddress"])
    bind_target = 0x18394A190
    direct_call_offsets = [
        offset
        for offset in range(len(body) - 4)
        if body[offset] == 0xE8
        and relative_call_target(body, method_va, offset) == bind_target
    ]
    expected_call_offsets = [row[2] for row in MANAGED_STREAMING_COMPONENT_BINDINGS]
    require(
        "managed_streaming_component_bind_calls",
        direct_call_offsets,
        expected_call_offsets,
        GAME_ASSEMBLY,
    )

    bindings = []
    for name, constant_offset, call_offset, expected_value in (
        MANAGED_STREAMING_COMPONENT_BINDINGS
    ):
        if body[constant_offset : constant_offset + 2] == b"\x48\xB9":
            actual_value = struct.unpack_from("<Q", body, constant_offset + 2)[0]
            instruction = "movabs rcx, imm64"
        else:
            require(
                f"managed_streaming_{name}_constant_opcode",
                body[constant_offset],
                0xB9,
                GAME_ASSEMBLY,
            )
            actual_value = struct.unpack_from("<I", body, constant_offset + 1)[0]
            instruction = "mov ecx, imm32"
        require(
            f"managed_streaming_{name}_component_type",
            actual_value,
            expected_value,
            GAME_ASSEMBLY,
        )
        require(
            f"managed_streaming_{name}_bind_target",
            relative_call_target(body, method_va, call_offset),
            bind_target,
            GAME_ASSEMBLY,
        )
        bindings.append(
            {
                "name": name,
                "value": actual_value,
                "bitIndex": actual_value.bit_length() - 1,
                "constantOffset": f"0x{constant_offset:X}",
                "callOffset": f"0x{call_offset:X}",
                "constantInstruction": instruction,
            }
        )

    bound_values = [row["value"] for row in bindings]
    require(
        "managed_streaming_hgtree_bit41_absent",
        (1 << 41) not in bound_values,
        True,
        GAME_ASSEMBLY,
    )
    return {
        "owner": spec["method"],
        "ownerVirtualAddress": f"0x{method_va:X}",
        "ownerSizeBytes": spec["sizeBytes"],
        "bindMethodVirtualAddress": f"0x{bind_target:X}",
        "directCallCount": len(direct_call_offsets),
        "bindings": bindings,
        "hgtreeBitIndex": 41,
        "hgtreeManagedBindingPresent": False,
        "boundary": (
            "the complete hash-pinned constructor has nine direct managed "
            "Mono-component bindings and none selects StreamingComponentType "
            "HGTree (bit 41); the constructor therefore does not register "
            "HGTree through its managed delegate path"
        ),
    }


def validate_hgmesh_renderer_data_inventory(
    inventory: dict[str, object] | None = None,
    *,
    verify_source_hash: bool = True,
) -> dict[str, object]:
    """Validate the compact inventory derived from all installed HGMeshRendererData."""

    source = HGMESH_RENDERER_DATA_INVENTORY
    data = (
        inventory
        if inventory is not None
        else json.loads(source.read_text(encoding="utf-8"))
    )
    expected_counts = {
        "0": 117,
        "1": 117,
        "2": 117,
        "3": 117,
        "4": 117,
        "5": 117,
        "6": 117,
        "7": 117,
        "8": 60,
        "9": 20,
        "10": 29,
        "11": 8,
        "18": 117,
        "29": 117,
        "44": 45,
        "46": 63,
        "47": 53,
        "48": 1,
    }
    expected_sizes = {
        "0": [4],
        "1": [4],
        "2": [4],
        "3": [4],
        "4": [4],
        "5": [4],
        "6": [20],
        "7": [24],
        "8": [36],
        "9": [68],
        "10": [132],
        "11": [260],
        "18": [256],
        "29": [1],
        "44": [16],
        "46": [8],
        "47": [20],
        "48": [68],
    }
    source_record = data.get("source") or {}
    corpus = data.get("corpus") or {}
    component67 = data.get("component67") or {}
    for check, actual, expected in (
        (
            "schema",
            data.get("schema"),
            "endfield.hgmesh-renderer-data-component-inventory.v1",
        ),
        (
            "source_path",
            source_record.get("vfsRelativePath"),
            "7064D8E2/B428C352B17C75CA29122CAACC037A59.chk",
        ),
        ("source_size", source_record.get("sizeBytes"), 1_258_089_569),
        (
            "source_sha256",
            source_record.get("sha256"),
            EXPECTED_HASHES["hgmesh_renderer_data_source"],
        ),
        ("object_type", corpus.get("serializedObjectType"), "HGMeshRendererData"),
        ("object_count", corpus.get("objectCount"), 117),
        ("descriptor_count", corpus.get("entityDescriptorCount"), 1_449),
        ("payload_bytes", corpus.get("entityPayloadBytes"), 49_805),
        ("blob_bytes", corpus.get("entityBlobBytes"), 61_865),
        ("descriptor_count_range", corpus.get("descriptorCountRange"), [12, 13]),
        ("serialized_offsets", corpus.get("serializedDescriptorOffsets"), [0]),
        ("component_counts", corpus.get("componentIdCounts"), expected_counts),
        ("component_sizes", corpus.get("componentSizes"), expected_sizes),
        (
            "source_object_digest_algorithm",
            corpus.get("sourceObjectDigestAlgorithm"),
            "sha256(sorted sourceFile|pathId|sourceOffset|rawDataSha256|"
            "descriptorCount|blobBytes)",
        ),
        (
            "source_object_digest",
            corpus.get("sourceObjectDigest"),
            "f40f399f7daa190312036fe2322f3cc1c4675217cc7f9a2388d1ce92c08c043b",
        ),
        ("layout_failure_count", corpus.get("layoutFailureCount"), 0),
        ("component67_descriptor_count", component67.get("descriptorCount"), 0),
        ("component67_present", component67.get("present"), False),
    ):
        require(f"hgmesh_renderer_data_{check}", actual, expected, source)
    if verify_source_hash:
        require(
            "hgmesh_renderer_data_source_exists",
            HGMESH_RENDERER_DATA_SOURCE.is_file(),
            True,
            HGMESH_RENDERER_DATA_SOURCE,
        )
        require(
            "hgmesh_renderer_data_installed_source_sha256",
            sha256(HGMESH_RENDERER_DATA_SOURCE),
            EXPECTED_HASHES["hgmesh_renderer_data_source"],
            HGMESH_RENDERER_DATA_SOURCE,
        )
    return data


def validate_hgtree_native_serialized_type_census(
    image: PEImage,
    census: dict[str, object] | None = None,
) -> dict[str, object]:
    """Close native class IDs and the controlled top-level VFS object census."""

    require("unity_player_image_base", image.image_base, 0x180000000, image.path)
    rows = []
    for name, expected in HGTREE_NATIVE_SERIALIZED_TYPE_ROWS.items():
        name_pointer = image.u64(expected["namePointerSlot"])
        actual_name = image.cstring(name_pointer)
        descriptor_raw = image.u64(expected["descriptorSlot"])
        class_id = descriptor_raw & 0xFFFFFFFF
        require(
            f"hgtree_native_serialized_type_{name}_name",
            actual_name,
            name,
            image.path,
        )
        require(
            f"hgtree_native_serialized_type_{name}_descriptor_raw",
            descriptor_raw,
            expected["descriptorRaw"],
            image.path,
        )
        require(
            f"hgtree_native_serialized_type_{name}_class_id",
            class_id,
            expected["classId"],
            image.path,
        )
        rows.append(
            {
                "name": name,
                "classId": class_id,
                "classIdHex": f"0x{class_id:08X}",
                "namePointer": f"0x{name_pointer:X}",
                "namePointerSlot": f"0x{expected['namePointerSlot']:X}",
                "descriptorSlot": f"0x{expected['descriptorSlot']:X}",
                "descriptorRaw": f"0x{descriptor_raw:016X}",
            }
        )

    source = HGTREE_NATIVE_SERIALIZED_TYPE_CENSUS
    data = (
        census
        if census is not None
        else json.loads(source.read_text(encoding="utf-8"))
    )
    installed = data.get("installedStreamingAssets") or {}
    report_rows = data.get("nativeSerializedTypes") or []
    scan = data.get("controlledFullScan") or {}
    gate = data.get("mapLoadExportGate") or {}
    tool = data.get("animestudioSource") or {}
    expected_report_rows = [
        {
            "name": row["name"],
            "classId": row["classId"],
            "classIdHex": row["classIdHex"],
            "unityPlayerNamePointerSlot": row["namePointerSlot"],
            "unityPlayerDescriptorSlot": row["descriptorSlot"],
        }
        for row in rows
    ]
    expected_type_counts = {
        "HGMeshRendererData": 117,
        "HGTree": 0,
        "HGTreeData": 0,
    }
    for check, actual, expected in (
        (
            "schema",
            data.get("schema"),
            "endfield.hgtree-native-serialized-type-census.v1",
        ),
        ("streaming_file_count", installed.get("fileCount"), 966),
        ("streaming_total_bytes", installed.get("totalBytes"), 57_058_764_239),
        (
            "streaming_suffix_counts",
            installed.get("suffixCounts"),
            {".blc": 17, ".chk": 947, ".json": 2},
        ),
        (
            "streaming_file_set_digest",
            installed.get("relativePathAndSizeSha256"),
            "5c82f20f1e24ab5b1deb8df3b34081fb1223d637875229505080b113bd4415f8",
        ),
        ("native_rows", report_rows, expected_report_rows),
        (
            "selected_types",
            scan.get("selectedTypes"),
            ["HGMeshRendererData", "HGTree", "HGTreeData"],
        ),
        ("map_entry_count", scan.get("mapEntryCount"), 117),
        ("map_type_counts", scan.get("typeCounts"), expected_type_counts),
        (
            "map_unique_physical_count",
            scan.get("uniquePhysicalIdentityCount"),
            117,
        ),
        ("map_unique_path_id_count", scan.get("uniquePathIdCount"), 117),
        ("map_source_chunk_count", scan.get("sourceChunkCount"), 1),
        (
            "map_source_chunks",
            scan.get("sourceChunks"),
            ["7064D8E2/B428C352B17C75CA29122CAACC037A59.chk"],
        ),
        (
            "map_identity_digest",
            scan.get("normalizedIdentitySha256"),
            "4eb8b092940129454b06549eaecce4e4fe29248b8c9ce16c1f5869033f781331",
        ),
        (
            "map_raw_digest",
            scan.get("rawMapSha256"),
            "f2d30900574b4af68973d8fcdbb9e169f2bc5a9f390eb20b14434be09706002b",
        ),
        ("export_object_count", gate.get("jsonObjectCount"), 117),
        ("export_type_counts", gate.get("typeCounts"), expected_type_counts),
        ("export_class_ids", gate.get("classIds"), [0x50F4EE0C]),
        (
            "export_unique_physical_count",
            gate.get("uniquePhysicalIdentityCount"),
            117,
        ),
        ("map_export_identity_equality", gate.get("mapAndExportIdentitiesEqual"), True),
        (
            "animestudio_class_id_source_hash",
            tool.get("classIdTypeSha256"),
            EXPECTED_HASHES["animestudio_class_id_source"],
        ),
        (
            "animestudio_asset_helper_source_hash",
            tool.get("assetsHelperSha256"),
            EXPECTED_HASHES["animestudio_asset_helper_source"],
        ),
    ):
        require(f"hgtree_native_serialized_census_{check}", actual, expected, source)

    return {
        "nativeDescriptorRows": rows,
        "installedStreamingAssets": installed,
        "controlledFullScan": scan,
        "mapLoadExportGate": gate,
        "hgtreeTopLevelObjectCount": 0,
        "hgtreeDataTopLevelObjectCount": 0,
        "boundary": data.get("boundary"),
    }


def validate_streaming_byte_enum_fields(
    raw_metadata: bytes,
    source: Path,
    prefix: str,
    expected_fields: dict[str, tuple[int, int, int]],
) -> list[dict[str, object]]:
    """Validate byte-backed IL2CPP enum fields from the installed metadata."""

    require(
        f"{prefix}_metadata_magic",
        struct.unpack_from("<I", raw_metadata, 0)[0],
        0xFAB11BAF,
        source,
    )
    sections = {}
    for section_index, section_name in enumerate(IL2CPP_METADATA_SECTION_NAMES):
        sections[section_name] = struct.unpack_from(
            "<Ii", raw_metadata, 8 + section_index * 8
        )
    string_offset, string_size = sections["string"]
    fields_offset, fields_size = sections["fields"]
    defaults_offset, defaults_size = sections["fieldDefaultValues"]
    values_offset, values_size = sections["fieldAndParameterDefaultValueData"]
    defaults = {}
    for position in range(defaults_offset, defaults_offset + defaults_size, 12):
        field_index, type_index, data_index = struct.unpack_from(
            "<iii", raw_metadata, position
        )
        defaults[field_index] = (type_index, data_index)
    rows = []
    for expected_name, (field_index, expected_token, expected_value) in (
        expected_fields.items()
    ):
        record_offset = fields_offset + field_index * 12
        require(
            f"{prefix}_{expected_name}_field_in_bounds",
            record_offset + 12 <= fields_offset + fields_size,
            True,
            source,
        )
        name_index, _, token = struct.unpack_from(
            "<iii", raw_metadata, record_offset
        )
        name_start = string_offset + name_index
        require(
            f"{prefix}_{expected_name}_name_in_bounds",
            string_offset <= name_start < string_offset + string_size,
            True,
            source,
        )
        name_end = raw_metadata.index(0, name_start, string_offset + string_size)
        actual_name = raw_metadata[name_start:name_end].decode("utf-8")
        require(
            f"{prefix}_{expected_name}_field_name",
            actual_name,
            expected_name,
            source,
        )
        require(
            f"{prefix}_{expected_name}_field_token",
            token,
            expected_token,
            source,
        )
        require(
            f"{prefix}_{expected_name}_default_exists",
            field_index in defaults,
            True,
            source,
        )
        default_type_index, data_index = defaults[field_index]
        require(
            f"{prefix}_{expected_name}_default_type",
            default_type_index,
            131229,
            source,
        )
        require(
            f"{prefix}_{expected_name}_default_in_bounds",
            0 <= data_index < values_size,
            True,
            source,
        )
        value = raw_metadata[values_offset + data_index]
        require(
            f"{prefix}_{expected_name}_value",
            value,
            expected_value,
            source,
        )
        rows.append(
            {
                "name": actual_name,
                "fieldIndex": field_index,
                "token": f"0x{token:08X}",
                "value": value,
            }
        )
    return rows


def decode_il2cpp_compressed_uint32(
    data: bytes, offset: int, end: int
) -> tuple[int, int]:
    """Decode the unsigned integer form used by IL2CPP metadata defaults."""

    require(
        "il2cpp_compressed_uint32_start_in_bounds",
        offset < end,
        True,
        GLOBAL_METADATA,
    )
    first = data[offset]
    if first & 0x80 == 0:
        return first, 1
    if first & 0xC0 == 0x80:
        require(
            "il2cpp_compressed_uint32_two_byte_in_bounds",
            offset + 2 <= end,
            True,
            GLOBAL_METADATA,
        )
        return ((first & 0x3F) << 8) | data[offset + 1], 2
    if first & 0xE0 == 0xC0:
        require(
            "il2cpp_compressed_uint32_four_byte_in_bounds",
            offset + 4 <= end,
            True,
            GLOBAL_METADATA,
        )
        return (
            ((first & 0x1F) << 24)
            | (data[offset + 1] << 16)
            | (data[offset + 2] << 8)
            | data[offset + 3],
            4,
        )
    if first == 0xF0:
        require(
            "il2cpp_compressed_uint32_five_byte_in_bounds",
            offset + 5 <= end,
            True,
            GLOBAL_METADATA,
        )
        return int.from_bytes(data[offset + 1 : offset + 5], "little"), 5
    if first == 0xFF:
        return 0xFFFFFFFF, 1
    raise AssertionError(
        "Light-cull cap audit failed: validator=light_cull_cap; "
        "check=il2cpp_compressed_uint32_prefix; "
        f"source={GLOBAL_METADATA}; expected='supported prefix'; "
        f"actual=0x{first:02X}"
    )


def validate_hg_resource_asset_type_metadata(
    raw_metadata: bytes,
    source: Path = GLOBAL_METADATA,
) -> dict[str, object]:
    """Pin HGResourceManager.LoadAsync to the installed HyperGryph AssetType."""

    require(
        "hg_resource_asset_type_metadata_magic",
        struct.unpack_from("<I", raw_metadata, 0)[0],
        0xFAB11BAF,
        source,
    )
    require(
        "hg_resource_asset_type_metadata_version",
        struct.unpack_from("<I", raw_metadata, 4)[0],
        29,
        source,
    )
    sections = {
        section_name: struct.unpack_from(
            "<Ii", raw_metadata, 8 + section_index * 8
        )
        for section_index, section_name in enumerate(
            IL2CPP_METADATA_SECTION_NAMES
        )
    }
    string_offset, string_size = sections["string"]
    method_offset, method_size = sections["methods"]
    parameter_offset, parameter_size = sections["parameters"]
    field_offset, field_size = sections["fields"]
    default_offset, default_size = sections["fieldDefaultValues"]
    value_offset, value_size = sections["fieldAndParameterDefaultValueData"]
    type_offset, type_size = sections["typeDefinitions"]

    def metadata_string(index: int, check: str) -> str:
        start = string_offset + index
        require(
            f"hg_resource_asset_type_{check}_string_start_in_bounds",
            string_offset <= start < string_offset + string_size,
            True,
            source,
        )
        end = raw_metadata.find(b"\0", start, string_offset + string_size)
        require(
            f"hg_resource_asset_type_{check}_string_end_in_bounds",
            end >= start,
            True,
            source,
        )
        return raw_metadata[start:end].decode("utf-8")

    def validate_type(
        check: str,
        index: int,
        expected_name: str,
        expected_namespace: str,
        expected_token: int,
        expected_byval_type: int | None = None,
    ) -> dict[str, object]:
        position = type_offset + index * 92
        require(
            f"hg_resource_asset_type_{check}_type_in_bounds",
            position + 92 <= type_offset + type_size,
            True,
            source,
        )
        name_index, namespace_index, byval_type = struct.unpack_from(
            "<iii", raw_metadata, position
        )
        token = struct.unpack_from("<I", raw_metadata, position + 88)[0]
        name = metadata_string(name_index, f"{check}_name")
        namespace = metadata_string(namespace_index, f"{check}_namespace")
        require(f"hg_resource_asset_type_{check}_name", name, expected_name, source)
        require(
            f"hg_resource_asset_type_{check}_namespace",
            namespace,
            expected_namespace,
            source,
        )
        require(f"hg_resource_asset_type_{check}_token", token, expected_token, source)
        if expected_byval_type is not None:
            require(
                f"hg_resource_asset_type_{check}_byval_metadata_type",
                byval_type,
                expected_byval_type,
                source,
            )
        return {
            "typeIndex": index,
            "token": f"0x{token:08X}",
            "fullName": f"{namespace}.{name}",
            "byvalMetadataTypeIndex": byval_type,
        }

    asset_type = validate_type(
        "enum",
        HG_ASSET_TYPE_INDEX,
        "AssetType",
        "UnityEngine.HyperGryph",
        HG_ASSET_TYPE_TOKEN,
        HG_ASSET_TYPE_BYVAL_METADATA_TYPE,
    )
    resource_manager = validate_type(
        "manager",
        HG_RESOURCE_MANAGER_TYPE_INDEX,
        "HGResourceManager",
        "UnityEngine.HyperGryph",
        HG_RESOURCE_MANAGER_TYPE_TOKEN,
    )

    defaults = {}
    for position in range(default_offset, default_offset + default_size, 12):
        field_index, type_index, data_index = struct.unpack_from(
            "<iii", raw_metadata, position
        )
        defaults[field_index] = (type_index, data_index)

    literals = []
    for expected_name, (field_index, expected_token, expected_value) in (
        HG_ASSET_TYPE_FIELDS.items()
    ):
        position = field_offset + field_index * 12
        require(
            f"hg_resource_asset_type_{expected_name}_field_in_bounds",
            position + 12 <= field_offset + field_size,
            True,
            source,
        )
        name_index, literal_type, token = struct.unpack_from(
            "<iiI", raw_metadata, position
        )
        name = metadata_string(name_index, f"{expected_name}_field_name")
        require(f"hg_resource_asset_type_{expected_name}_name", name, expected_name, source)
        require(f"hg_resource_asset_type_{expected_name}_token", token, expected_token, source)
        require(
            f"hg_resource_asset_type_{expected_name}_literal_type",
            literal_type,
            122375,
            source,
        )
        require(
            f"hg_resource_asset_type_{expected_name}_default_exists",
            field_index in defaults,
            True,
            source,
        )
        default_type, data_index = defaults[field_index]
        require(
            f"hg_resource_asset_type_{expected_name}_default_type",
            default_type,
            148327,
            source,
        )
        require(
            f"hg_resource_asset_type_{expected_name}_default_in_bounds",
            0 <= data_index < value_size,
            True,
            source,
        )
        encoded_value, encoded_size = decode_il2cpp_compressed_uint32(
            raw_metadata,
            value_offset + data_index,
            value_offset + value_size,
        )
        value = (encoded_value >> 1) ^ -(encoded_value & 1)
        require(
            f"hg_resource_asset_type_{expected_name}_value",
            value,
            expected_value,
            source,
        )
        literals.append(
            {
                "name": name,
                "fieldIndex": field_index,
                "token": f"0x{token:08X}",
                "value": value,
                "encodedSizeBytes": encoded_size,
            }
        )

    method_position = (
        method_offset + HG_RESOURCE_LOAD_ASYNC_INJECTED_METHOD_INDEX * 32
    )
    require(
        "hg_resource_load_async_injected_method_in_bounds",
        method_position + 32 <= method_offset + method_size,
        True,
        source,
    )
    (
        method_name_index,
        declaring_type,
        return_type,
        parameter_start,
        generic_container,
        method_token,
        method_flags,
        method_iflags,
        method_slot,
        parameter_count,
    ) = struct.unpack_from("<iiiiiIHHHH", raw_metadata, method_position)
    require(
        "hg_resource_load_async_injected_method_name",
        metadata_string(method_name_index, "load_async_injected_method"),
        "LoadAsync_Injected",
        source,
    )
    for check, actual, expected in (
        ("declaring_type", declaring_type, HG_RESOURCE_MANAGER_TYPE_INDEX),
        ("return_type", return_type, 170022),
        ("parameter_start", parameter_start, HG_RESOURCE_LOAD_ASYNC_INJECTED_PARAMETER_START),
        ("generic_container", generic_container, -1),
        ("token", method_token, HG_RESOURCE_LOAD_ASYNC_INJECTED_METHOD_TOKEN),
        ("flags", method_flags, 0x0091),
        ("iflags", method_iflags, 0x1000),
        ("slot", method_slot, 0xFFFF),
        ("parameter_count", parameter_count, 4),
    ):
        require(f"hg_resource_load_async_injected_{check}", actual, expected, source)

    expected_parameters = [
        ("assetHash", 0x08000255, 148369),
        ("type", 0x08000256, HG_ASSET_TYPE_BYVAL_METADATA_TYPE),
        ("priority", 0x08000257, 122366),
        ("ret", 0x08000258, 103721),
    ]
    parameters = []
    for relative_index, (expected_name, expected_token, expected_type) in enumerate(
        expected_parameters
    ):
        parameter_index = parameter_start + relative_index
        position = parameter_offset + parameter_index * 12
        require(
            f"hg_resource_load_async_injected_{expected_name}_parameter_in_bounds",
            position + 12 <= parameter_offset + parameter_size,
            True,
            source,
        )
        name_index, token, parameter_type = struct.unpack_from(
            "<iIi", raw_metadata, position
        )
        name = metadata_string(name_index, f"load_async_injected_{expected_name}")
        require(f"hg_resource_load_async_injected_{expected_name}_name", name, expected_name, source)
        require(f"hg_resource_load_async_injected_{expected_name}_token", token, expected_token, source)
        require(f"hg_resource_load_async_injected_{expected_name}_type", parameter_type, expected_type, source)
        parameters.append(
            {
                "name": name,
                "token": f"0x{token:08X}",
                "metadataTypeIndex": parameter_type,
            }
        )

    return {
        "metadataVersion": 29,
        "assetType": {**asset_type, "literals": literals},
        "resourceManager": resource_manager,
        "loadAsyncInjected": {
            "methodIndex": HG_RESOURCE_LOAD_ASYNC_INJECTED_METHOD_INDEX,
            "token": f"0x{method_token:08X}",
            "parameters": parameters,
        },
    }


def validate_hgtree_renderer_list_metadata(
    raw_metadata: bytes,
    source: Path = GLOBAL_METADATA,
) -> dict[str, object]:
    """Pin the UInt32 renderFlags mask/value ABI used by HGTree jobs."""

    require(
        "hgtree_renderer_list_metadata_magic",
        struct.unpack_from("<I", raw_metadata, 0)[0],
        0xFAB11BAF,
        source,
    )
    require(
        "hgtree_renderer_list_metadata_version",
        struct.unpack_from("<I", raw_metadata, 4)[0],
        29,
        source,
    )
    sections = {
        section_name: struct.unpack_from(
            "<Ii", raw_metadata, 8 + section_index * 8
        )
        for section_index, section_name in enumerate(
            IL2CPP_METADATA_SECTION_NAMES
        )
    }
    string_offset, string_size = sections["string"]
    method_offset, method_size = sections["methods"]
    parameter_offset, parameter_size = sections["parameters"]
    type_offset, type_size = sections["typeDefinitions"]

    def metadata_string(index: int, check: str) -> str:
        start = string_offset + index
        require(
            f"hgtree_renderer_list_{check}_string_start_in_bounds",
            string_offset <= start < string_offset + string_size,
            True,
            source,
        )
        end = raw_metadata.find(b"\0", start, string_offset + string_size)
        require(
            f"hgtree_renderer_list_{check}_string_end_in_bounds",
            end >= start,
            True,
            source,
        )
        return raw_metadata[start:end].decode("utf-8")

    type_position = type_offset + HG_TREE_RENDER_TYPE_INDEX * 92
    require(
        "hgtree_renderer_list_type_in_bounds",
        type_position + 92 <= type_offset + type_size,
        True,
        source,
    )
    type_name_index, namespace_index = struct.unpack_from(
        "<ii", raw_metadata, type_position
    )
    type_token = struct.unpack_from("<I", raw_metadata, type_position + 88)[0]
    type_name = metadata_string(type_name_index, "type_name")
    namespace = metadata_string(namespace_index, "type_namespace")
    for check, actual, expected in (
        ("type_name", type_name, "HGTreeRender"),
        ("type_namespace", namespace, "UnityEngine.HyperGryph"),
        ("type_token", type_token, HG_TREE_RENDER_TYPE_TOKEN),
    ):
        require(f"hgtree_renderer_list_{check}", actual, expected, source)

    method_position = (
        method_offset + HG_TREE_CREATE_RENDERER_LIST_INJECTED_METHOD_INDEX * 32
    )
    require(
        "hgtree_renderer_list_method_in_bounds",
        method_position + 32 <= method_offset + method_size,
        True,
        source,
    )
    (
        method_name_index,
        declaring_type,
        return_type,
        parameter_start,
        _generic_container,
        method_token,
        _flags,
        _iflags,
        _slot,
        parameter_count,
    ) = struct.unpack_from("<iiiiiIHHHH", raw_metadata, method_position)
    method_name = metadata_string(method_name_index, "method_name")
    for check, actual, expected in (
        ("method_name", method_name, "CreateRendererList"),
        ("method_declaring_type", declaring_type, HG_TREE_RENDER_TYPE_INDEX),
        ("method_return_type", return_type, 168243),
        (
            "method_parameter_start",
            parameter_start,
            HG_TREE_CREATE_RENDERER_LIST_INJECTED_PARAMETER_START,
        ),
        (
            "method_token",
            method_token,
            HG_TREE_CREATE_RENDERER_LIST_INJECTED_METHOD_TOKEN,
        ),
        (
            "method_parameter_count",
            parameter_count,
            len(HG_TREE_CREATE_RENDERER_LIST_INJECTED_PARAMETERS),
        ),
    ):
        require(f"hgtree_renderer_list_{check}", actual, expected, source)

    parameters = []
    for relative_index, (expected_name, expected_token, expected_type) in enumerate(
        HG_TREE_CREATE_RENDERER_LIST_INJECTED_PARAMETERS
    ):
        position = parameter_offset + (parameter_start + relative_index) * 12
        require(
            f"hgtree_renderer_list_{expected_name}_parameter_in_bounds",
            position + 12 <= parameter_offset + parameter_size,
            True,
            source,
        )
        name_index, token, metadata_type = struct.unpack_from(
            "<iIi", raw_metadata, position
        )
        name = metadata_string(name_index, f"{expected_name}_parameter_name")
        for check, actual, expected in (
            ("name", name, expected_name),
            ("token", token, expected_token),
            ("type", metadata_type, expected_type),
        ):
            require(
                f"hgtree_renderer_list_{expected_name}_{check}",
                actual,
                expected,
                source,
            )
        parameters.append(
            {
                "name": name,
                "token": f"0x{token:08X}",
                "metadataTypeIndex": metadata_type,
            }
        )

    return {
        "declaringType": {
            "typeIndex": HG_TREE_RENDER_TYPE_INDEX,
            "fullName": f"{namespace}.{type_name}",
            "token": f"0x{type_token:08X}",
        },
        "method": {
            "methodIndex": HG_TREE_CREATE_RENDERER_LIST_INJECTED_METHOD_INDEX,
            "name": method_name,
            "token": f"0x{method_token:08X}",
            "returnMetadataTypeIndex": return_type,
            "parameters": parameters,
        },
    }


def validate_enabled_light_modes_metadata(
    raw_metadata: bytes,
    source: Path = GLOBAL_METADATA,
) -> dict[str, object]:
    """Close enabledLightModes signatures and pass bits from IL2CPP metadata."""

    require(
        "enabled_light_modes_metadata_magic",
        struct.unpack_from("<I", raw_metadata, 0)[0],
        0xFAB11BAF,
        source,
    )
    require(
        "enabled_light_modes_metadata_version",
        struct.unpack_from("<I", raw_metadata, 4)[0],
        29,
        source,
    )
    sections = {}
    for section_index, section_name in enumerate(IL2CPP_METADATA_SECTION_NAMES):
        sections[section_name] = struct.unpack_from(
            "<Ii", raw_metadata, 8 + section_index * 8
        )
    string_offset, string_size = sections["string"]
    method_offset, method_size = sections["methods"]
    parameter_offset, parameter_size = sections["parameters"]
    field_offset, field_size = sections["fields"]
    default_offset, default_size = sections["fieldDefaultValues"]
    values_offset, values_size = sections["fieldAndParameterDefaultValueData"]
    type_offset, type_size = sections["typeDefinitions"]
    for label, actual_size, stride in (
        ("method", method_size, 32),
        ("parameter", parameter_size, 12),
        ("field", field_size, 12),
        ("field_default", default_size, 12),
        ("type", type_size, 92),
    ):
        require(
            f"enabled_light_modes_{label}_record_alignment",
            actual_size % stride,
            0,
            source,
        )

    def metadata_string(index: int, check: str) -> str:
        start = string_offset + index
        require(
            f"enabled_light_modes_{check}_string_start_in_bounds",
            string_offset <= start < string_offset + string_size,
            True,
            source,
        )
        end = raw_metadata.find(b"\0", start, string_offset + string_size)
        require(
            f"enabled_light_modes_{check}_string_end_in_bounds",
            end >= start,
            True,
            source,
        )
        return raw_metadata[start:end].decode("utf-8")

    def validate_type(
        check: str,
        index: int,
        expected_name: str,
        expected_namespace: str,
        expected_token: int,
    ) -> dict[str, object]:
        position = type_offset + index * 92
        require(
            f"enabled_light_modes_{check}_type_in_bounds",
            position + 92 <= type_offset + type_size,
            True,
            source,
        )
        name_index, namespace_index = struct.unpack_from(
            "<ii", raw_metadata, position
        )
        token = struct.unpack_from("<I", raw_metadata, position + 88)[0]
        name = metadata_string(name_index, f"{check}_type_name")
        namespace = metadata_string(
            namespace_index, f"{check}_type_namespace"
        )
        require(f"enabled_light_modes_{check}_type_name", name, expected_name, source)
        require(
            f"enabled_light_modes_{check}_type_namespace",
            namespace,
            expected_namespace,
            source,
        )
        require(
            f"enabled_light_modes_{check}_type_token",
            token,
            expected_token,
            source,
        )
        return {
            "typeIndex": index,
            "token": f"0x{token:08X}",
            "fullName": f"{namespace}.{name}",
        }

    def validate_method(
        check: str,
        index: int,
        expected_name: str,
        expected_declaring_type: int,
        expected_return_type: int,
        expected_parameter_start: int,
        expected_token: int,
        expected_parameters: list[tuple[str, int, int]],
    ) -> dict[str, object]:
        position = method_offset + index * 32
        require(
            f"enabled_light_modes_{check}_method_in_bounds",
            position + 32 <= method_offset + method_size,
            True,
            source,
        )
        (
            name_index,
            declaring_type,
            return_type,
            parameter_start,
            _generic_container,
            token,
            _flags,
            _iflags,
            _slot,
            parameter_count,
        ) = struct.unpack_from("<iiiiiIHHHH", raw_metadata, position)
        name = metadata_string(name_index, f"{check}_method_name")
        for field_name, actual, expected in (
            ("name", name, expected_name),
            ("declaring_type", declaring_type, expected_declaring_type),
            ("return_type", return_type, expected_return_type),
            ("parameter_start", parameter_start, expected_parameter_start),
            ("token", token, expected_token),
            ("parameter_count", parameter_count, len(expected_parameters)),
        ):
            require(
                f"enabled_light_modes_{check}_method_{field_name}",
                actual,
                expected,
                source,
            )
        parameters = []
        for relative_index, (
            expected_param_name,
            expected_param_token,
            expected_type,
        ) in enumerate(expected_parameters):
            param_index = parameter_start + relative_index
            param_position = parameter_offset + param_index * 12
            require(
                f"enabled_light_modes_{check}_{expected_param_name}_parameter_in_bounds",
                param_position + 12 <= parameter_offset + parameter_size,
                True,
                source,
            )
            param_name_index, param_token, param_type = struct.unpack_from(
                "<iIi", raw_metadata, param_position
            )
            param_name = metadata_string(
                param_name_index, f"{check}_{expected_param_name}_parameter_name"
            )
            for field_name, actual, expected in (
                ("name", param_name, expected_param_name),
                ("token", param_token, expected_param_token),
                ("type", param_type, expected_type),
            ):
                require(
                    f"enabled_light_modes_{check}_{expected_param_name}_{field_name}",
                    actual,
                    expected,
                    source,
                )
            parameters.append(
                {
                    "name": param_name,
                    "token": f"0x{param_token:08X}",
                    "metadataTypeIndex": param_type,
                }
            )
        return {
            "methodIndex": index,
            "token": f"0x{token:08X}",
            "name": name,
            "returnMetadataTypeIndex": return_type,
            "parameters": parameters,
        }

    defaults = {}
    for position in range(default_offset, default_offset + default_size, 12):
        field_index, type_index, data_index = struct.unpack_from(
            "<iii", raw_metadata, position
        )
        defaults[field_index] = (type_index, data_index)

    def validate_enum(
        check: str,
        expected_fields: dict[str, tuple[int, int, int]],
        expected_literal_type: int,
    ) -> list[dict[str, object]]:
        rows = []
        for expected_name, (field_index, expected_token, expected_value) in (
            expected_fields.items()
        ):
            position = field_offset + field_index * 12
            require(
                f"enabled_light_modes_{check}_{expected_name}_field_in_bounds",
                position + 12 <= field_offset + field_size,
                True,
                source,
            )
            name_index, literal_type, token = struct.unpack_from(
                "<iiI", raw_metadata, position
            )
            name = metadata_string(name_index, f"{check}_{expected_name}_field_name")
            for field_name, actual, expected in (
                ("name", name, expected_name),
                ("token", token, expected_token),
                ("literal_type", literal_type, expected_literal_type),
                ("default_exists", field_index in defaults, True),
            ):
                require(
                    f"enabled_light_modes_{check}_{expected_name}_{field_name}",
                    actual,
                    expected,
                    source,
                )
            default_type, data_index = defaults[field_index]
            require(
                f"enabled_light_modes_{check}_{expected_name}_default_type",
                default_type,
                168243,
                source,
            )
            require(
                f"enabled_light_modes_{check}_{expected_name}_default_in_bounds",
                0 <= data_index < values_size,
                True,
                source,
            )
            value, encoded_size = decode_il2cpp_compressed_uint32(
                raw_metadata,
                values_offset + data_index,
                values_offset + values_size,
            )
            require(
                f"enabled_light_modes_{check}_{expected_name}_value",
                value,
                expected_value,
                source,
            )
            rows.append(
                {
                    "name": name,
                    "fieldIndex": field_index,
                    "token": f"0x{token:08X}",
                    "value": f"0x{value:08X}",
                    "bit": value.bit_length() - 1 if value else None,
                    "encodedSizeBytes": encoded_size,
                }
            )
        return rows

    types = {
        "factoryRenderManager": validate_type(
            "factory_render_manager",
            HG_FACTORY_RENDER_MANAGER_TYPE_INDEX,
            "HGFactoryRenderManager",
            "UnityEngine.HyperGryph",
            HG_FACTORY_RENDER_MANAGER_TYPE_TOKEN,
        ),
        "shaderLightMode": validate_type(
            "shader_light_mode",
            HG_SHADER_LIGHT_MODE_TYPE_INDEX,
            "HGShaderLightMode",
            "UnityEngine.HyperGryph",
            HG_SHADER_LIGHT_MODE_TYPE_TOKEN,
        ),
        "perDrawPassConfig": validate_type(
            "per_draw_pass_config",
            PER_DRAW_PASS_CONFIG_TYPE_INDEX,
            "PerDrawPassConfig",
            "Beyond.Gameplay.Factory",
            PER_DRAW_PASS_CONFIG_TYPE_TOKEN,
        ),
        "perDrawLightMode": validate_type(
            "per_draw_light_mode",
            PER_DRAW_LIGHT_MODE_TYPE_INDEX,
            "PerDrawLightMode",
            "Beyond.Gameplay.Factory",
            PER_DRAW_LIGHT_MODE_TYPE_TOKEN,
        ),
    }
    methods = {
        "setEntityEnabledLightModes": validate_method(
            "set_entity_enabled_light_modes",
            HG_FACTORY_SET_ENABLED_LIGHT_MODES_METHOD_INDEX,
            "SetEntityEnabledLightModes",
            HG_FACTORY_RENDER_MANAGER_TYPE_INDEX,
            170022,
            533364,
            HG_FACTORY_SET_ENABLED_LIGHT_MODES_METHOD_TOKEN,
            [
                ("rendererEntity", 0x080000DF, 139403),
                ("lightModeMask", 0x080000E0, 168243),
            ],
        ),
        "setEntityEnabledLightModesInjected": validate_method(
            "set_entity_enabled_light_modes_injected",
            HG_FACTORY_SET_ENABLED_LIGHT_MODES_INJECTED_METHOD_INDEX,
            "SetEntityEnabledLightModes_Injected",
            HG_FACTORY_RENDER_MANAGER_TYPE_INDEX,
            170022,
            533398,
            HG_FACTORY_SET_ENABLED_LIGHT_MODES_INJECTED_METHOD_TOKEN,
            [
                ("rendererEntity", 0x08000101, 109842),
                ("lightModeMask", 0x08000102, 168243),
            ],
        ),
        "perDrawApply": validate_method(
            "per_draw_apply",
            PER_DRAW_PASS_APPLY_METHOD_INDEX,
            "Apply",
            PER_DRAW_PASS_CONFIG_TYPE_INDEX,
            170022,
            442637,
            PER_DRAW_PASS_APPLY_METHOD_TOKEN,
            [
                ("rendererEntity", 0x08000C86, 139403),
                ("currentLightMode", 0x08000C87, 114269),
            ],
        ),
        "perDrawParser": validate_method(
            "per_draw_parser",
            PER_DRAW_PASS_PARSE_METHOD_INDEX,
            "_ParseToHGShaderLightMode",
            PER_DRAW_PASS_CONFIG_TYPE_INDEX,
            145179,
            442641,
            PER_DRAW_PASS_PARSE_METHOD_TOKEN,
            [("value", 0x08000C8A, 157254)],
        ),
    }
    shader_rows = validate_enum(
        "shader_light_mode", HG_SHADER_LIGHT_MODE_FIELDS, 145180
    )
    per_draw_rows = validate_enum(
        "per_draw_light_mode", PER_DRAW_LIGHT_MODE_FIELDS, 157255
    )
    shader_values = {row["name"]: row["value"] for row in shader_rows}
    crosswalk = [
        {
            "name": row["name"],
            "perDrawValue": row["value"],
            "shaderLightModeValue": shader_values[row["name"]],
        }
        for row in per_draw_rows
    ]
    return {
        "metadataVersion": 29,
        "types": types,
        "methods": methods,
        "shaderLightMode": {
            "underlyingMaskType": "System.UInt32",
            "literalCount": len(shader_rows),
            "nonzeroBitRange": [0, 30],
            "combinedMask": "0x7FFFFFFF",
            "literals": shader_rows,
        },
        "perDrawLightMode": {
            "literalCount": len(per_draw_rows),
            "crosswalk": crosswalk,
            "unavailableInPerDrawConfig": [
                name
                for name in HG_SHADER_LIGHT_MODE_FIELDS
                if name not in PER_DRAW_LIGHT_MODE_FIELDS
            ],
        },
    }


def validate_enabled_light_modes_game_assembly(
    source: Path = GAME_ASSEMBLY,
) -> dict[str, object]:
    """Pin the managed pass-mask producer, parser, wrapper, and icall stub."""

    bodies = []
    with source.open("rb") as stream:
        for label, (virtual_address, file_offset, size_bytes, expected_hash) in (
            ENABLED_LIGHT_MODE_GAME_ASSEMBLY_BODIES.items()
        ):
            stream.seek(file_offset)
            body = stream.read(size_bytes)
            require(
                f"enabled_light_modes_{label}_size",
                len(body),
                size_bytes,
                source,
            )
            actual_hash = hashlib.sha256(body).hexdigest()
            require(
                f"enabled_light_modes_{label}_sha256",
                actual_hash,
                expected_hash,
                source,
            )
            bodies.append(
                {
                    "label": label,
                    "virtualAddress": f"0x{virtual_address:X}",
                    "fileOffset": f"0x{file_offset:X}",
                    "sizeBytes": size_bytes,
                    "sha256": actual_hash,
                }
            )
        method_pointers = []
        for method_index, (file_offset, expected_pointer) in (
            ENABLED_LIGHT_MODE_METHOD_POINTERS.items()
        ):
            stream.seek(file_offset)
            actual_pointer = struct.unpack("<Q", stream.read(8))[0]
            require(
                f"enabled_light_modes_method_{method_index}_pointer",
                actual_pointer,
                expected_pointer,
                source,
            )
            method_pointers.append(
                {
                    "methodIndex": method_index,
                    "pointerFileOffset": f"0x{file_offset:X}",
                    "bodyVirtualAddress": f"0x{actual_pointer:X}",
                }
            )
        slice_offset, expected_slice = PER_DRAW_APPLY_TO_SET_ENABLED_LIGHT_MODES_SLICE
        stream.seek(slice_offset)
        actual_slice = stream.read(len(expected_slice))
    require(
        "enabled_light_modes_per_draw_apply_call_slice",
        actual_slice,
        expected_slice,
        source,
    )
    call_instruction_offset = 10
    call_site = 0x1869F38FA + call_instruction_offset
    displacement = struct.unpack_from(
        "<i", actual_slice, call_instruction_offset + 1
    )[0]
    call_target = call_site + 5 + displacement
    require(
        "enabled_light_modes_per_draw_apply_call_target",
        call_target,
        0x18B3F9118,
        source,
    )
    return {
        "verifiedBodies": bodies,
        "methodPointers": method_pointers,
        "perDrawApplyCall": {
            "virtualAddress": f"0x{call_site:X}",
            "targetVirtualAddress": f"0x{call_target:X}",
            "dataflow": (
                "parsed HGShaderLightMode mask in eax is stored into "
                "currentLightMode, copied to edx, then passed with "
                "rendererEntity to SetEntityEnabledLightModes"
            ),
        },
    }


def validate_streaming_scene_v2_payload_census(
    unity_image: PEImage,
    game_image: PEImage,
    census: dict[str, object] | None = None,
    metadata: bytes | None = None,
) -> dict[str, object]:
    """Pin the retail StreamingSceneV2 route and its scanned payload surfaces."""

    source = STREAMING_SCENE_V2_PAYLOAD_CENSUS
    require(
        "streaming_scene_v2_unity_image_base",
        unity_image.image_base,
        0x180000000,
        unity_image.path,
    )
    require(
        "streaming_scene_v2_game_image_base",
        game_image.image_base,
        0x180000000,
        game_image.path,
    )
    name_pointer = unity_image.u64(
        UNITY_HG_ICALL_NAME_TABLE_VA + STREAMING_SCENE_V2_CREATE_ICALL_INDEX * 8
    )
    require(
        "streaming_scene_v2_create_icall_name",
        unity_image.cstring(name_pointer),
        STREAMING_SCENE_V2_CREATE_ICALL_NAME,
        unity_image.path,
    )
    require(
        "streaming_scene_v2_create_icall_function",
        unity_image.u64(
            UNITY_HG_ICALL_FUNCTION_TABLE_VA
            + STREAMING_SCENE_V2_CREATE_ICALL_INDEX * 8
        ),
        STREAMING_SCENE_V2_CREATE_ICALL_VA,
        unity_image.path,
    )

    binary_rows = []
    for image_name, name, virtual_address, size, expected_hash in (
        STREAMING_SCENE_V2_BINARY_BODIES
    ):
        image = unity_image if image_name == "UnityPlayer.dll" else game_image
        actual_hash = hashlib.sha256(image.read(virtual_address, size)).hexdigest()
        require(
            f"streaming_scene_v2_{name.lower().replace(' ', '_').replace('.', '_')}_sha256",
            actual_hash,
            expected_hash,
            image.path,
        )
        binary_rows.append(
            {
                "image": image_name,
                "name": name,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": size,
                "sha256": actual_hash,
            }
        )

    dispatch_tables = {}
    for label, (virtual_address, expected_entries) in (
        STREAMING_UNION_DISPATCH_TABLES.items()
    ):
        actual_entries = [
            unity_image.u64(virtual_address + index * 8)
            for index in range(len(expected_entries))
        ]
        require(
            f"streaming_scene_v2_{label}_dispatch_table",
            actual_entries,
            expected_entries,
            unity_image.path,
        )
        dispatch_tables[label] = {
            "virtualAddress": f"0x{virtual_address:X}",
            "entries": [f"0x{entry:X}" for entry in actual_entries],
        }

    raw_metadata = metadata if metadata is not None else GLOBAL_METADATA.read_bytes()
    entity_type_enums = {
        "ecs": validate_streaming_byte_enum_fields(
            raw_metadata,
            GLOBAL_METADATA,
            "streaming_ecs_entity_type",
            STREAMING_ECS_ENTITY_TYPE_FIELDS,
        ),
        "proxy": validate_streaming_byte_enum_fields(
            raw_metadata,
            GLOBAL_METADATA,
            "streaming_proxy_entity_type",
            STREAMING_PROXY_ENTITY_TYPE_FIELDS,
        ),
    }
    native_entity_dispatch = {
        "runtimeRecordStrideBytes": 56,
        "tables": dispatch_tables,
        "tags": [
            {"tag": 1, "name": "MonoEntity"},
            {"tag": 2, "name": "NativeECS"},
            {"tag": 3, "name": "Proxy"},
        ],
        "nativeEcsConvertFromVirtualAddress": "0x181152810",
        "nativeEcsRegistry": {
            "slotCount": 14,
            "slotStrideBytes": 648,
            "callbackSlotInstallerVirtualAddress": "0x1811701B0",
        },
    }
    component67_owners = {
        "componentId": 67,
        "recordStrideBytes": 24,
        "entityTypes": [
            {
                "value": 0,
                "name": "Render",
                "registrationRange": ["0x18116B9A1", "0x18116BBE1"],
                "transition1": "0x181154230",
                "convertFrom": "0x181159010",
            },
            {
                "value": 9,
                "name": "MergedRenderCollider",
                "registrationRange": ["0x18116B6AB", "0x18116B9A1"],
                "transition1": "0x181153310",
                "convertFrom": "0x181157760",
            },
        ],
        "boundary": (
            "native ECS entity ownership is closed for Render and "
            "MergedRenderCollider; the standalone native component type name "
            "remains open"
        ),
    }
    component67_initial_data = {
        "rootFields": {
            "nativeEntityIdGroups": 6,
            "nativeArchetypeDescriptions": 7,
            "descriptionComponentDescriptors": 3,
            "descriptionInitialData": 4,
            "initialDataBytes": 0,
        },
        "descriptorLayout": {
            "strideBytes": 8,
            "componentId": {"offset": 0, "type": "Int16"},
            "elementSize": {"offset": 2, "type": "Int16"},
            "auxiliary": {"offset": 4, "type": "UInt32"},
            "component67": {"componentId": 67, "elementSize": 24},
        },
        "runtimeProducer": {
            "rootFieldSetupRange": ["0x18117E110", "0x18117E42B"],
            "archetypeInitialDataCopy": "0x1801F95E0",
            "behavior": (
                "allocate native ECS archetype storage, then copy each "
                "entityCount*elementSize component slice from serialized "
                "initialData bytes"
            ),
        },
        "fullScan": {
            "fileCount": 51012,
            "filesWithNativeArchetypes": 5838,
            "filesWithComponent67": 2769,
            "nativeArchetypeGroupCount": 17281,
            "nativeEntityCount": 1466711,
            "component67EntityOccurrenceCount": 1305818,
            "unionType0Or9EntityOccurrenceCount": 2611636,
            "distinctComponent67EntityCountByMapScope": 1230041,
            "distinctUnionType0Or9EntityCountByMapScope": 1230041,
            "mapScopeCount": 83,
            "largestScopeComponent67EntityCount": 388047,
            "component67OwnerSetExactPerMapScope": True,
            "repeatedInitialDataByteExactPerMapEntity": True,
            "normalizedSourceSha256": (
                "6911a86a785c84334b98b7226e915a320f83989f203da641dd207d1f5637ae5b"
            ),
        },
        "initialState": {
            "lodCountCounts": {
                "1": 351082,
                "2": 273576,
                "3": 327499,
                "4": 228398,
                "5": 104480,
                "6": 20783,
            },
            "stateBytes": [8, 8, 8, 0, 0],
            "stateByteEntityCount": 1305818,
            "reservedWordAt0x06": 0,
            "reservedWordEntityCount": 1305818,
            "readiness": 0,
            "readinessEntityCount": 1305818,
            "rangeEndpointPatternCount": 102,
            "maximumLodCount": 6,
        },
        "companionComponents": [
            {"componentId": 68, "elementSize": 48, "entityCount": 331405},
            {"componentId": 69, "elementSize": 88, "entityCount": 246293},
            {"componentId": 70, "elementSize": 168, "entityCount": 415221},
            {"componentId": 71, "elementSize": 328, "entityCount": 233440},
            {"componentId": 72, "elementSize": 648, "entityCount": 66202},
            {"componentId": 73, "elementSize": 1288, "entityCount": 13257},
        ],
        "boundary": (
            "component 67 lodCount, zero reserved word, and cumulative "
            "renderer ranges are exact serialized game-binary initial data "
            "copied into native ECS storage; the standalone native component "
            "type name remains open"
        ),
    }

    data = (
        census
        if census is not None
        else json.loads(source.read_text(encoding="utf-8"))
    )
    inputs = data.get("installedInputs") or {}
    managed = data.get("managedBridge") or {}
    native = data.get("nativeLoader") or {}
    entity_dispatch = data.get("nativeEntityDispatch") or {}
    enums = data.get("entityTypeEnums") or {}
    owners = data.get("component67Owners") or {}
    initial_data = data.get("component67InitialData") or {}
    configs = data.get("serializedMapConfigs") or {}
    vfs = data.get("installedVfs") or {}
    blocks = vfs.get("blocks") or {}
    families = vfs.get("families") or {}
    payloads = data.get("streamingPayloads") or {}
    dynamic = data.get("dynamicStreaming") or {}
    dynamic_union = dynamic.get("initAndStreaming") or {}
    dynamic_main = dynamic.get("fbMain") or {}
    expected_parameter = {
        "sizeBytes": 40,
        "fields": {
            "mapName": 0,
            "regionHandle": 8,
            "streamingRootObject": 16,
            "streamingDataPathRoot": 24,
            "isDev": 32,
        },
    }
    expected_native_paths = [
        "{0}/[dev]{1}.bytes",
        "{0}/{1}.bytes",
        "{0}/{1}{2}ChunkData_Global_{3}_{4}.bytes",
        "{0}/{1}{2}ChunkData_{3}_{4}_{5}_{6}.bytes",
    ]
    expected_base_scene_offsets = {
        "streamingSceneV2": 72,
        "layerEnabledInDefaultArea": 88,
        "streamingRootObject": 112,
        "streamingMapConfig": 192,
    }
    expected_map_config_offsets = {
        "mapName": 24,
        "exportScenePathRoot": 32,
        "streamingDataPathRoot": 40,
        "isDev": 48,
        "mapSceneName": 56,
        "lowMemory": 64,
    }
    checks = (
        (
            "schema",
            data.get("schema"),
            "endfield.streaming-scene-v2-payload-census.v4",
        ),
        (
            "unity_player_hash",
            inputs.get("unityPlayerSha256"),
            EXPECTED_HASHES["unity_player"],
        ),
        (
            "game_assembly_hash",
            inputs.get("gameAssemblySha256"),
            EXPECTED_HASHES["game_assembly"],
        ),
        (
            "global_metadata_hash",
            inputs.get("globalMetadataSha256"),
            EXPECTED_HASHES["global_metadata"],
        ),
        (
            "managed_type_index",
            managed.get("streamingSceneV2TypeDefinitionIndex"),
            61041,
        ),
        ("managed_type_token", managed.get("streamingSceneV2TypeToken"), "0x020000A4"),
        ("managed_create_index", managed.get("createMethodIndex"), 478285),
        ("managed_create_token", managed.get("createMethodToken"), "0x060001E9"),
        (
            "managed_create_injected_index",
            managed.get("createInjectedMethodIndex"),
            478303,
        ),
        (
            "managed_create_injected_token",
            managed.get("createInjectedMethodToken"),
            "0x060001FB",
        ),
        (
            "managed_base_scene_create_index",
            managed.get("baseGameSceneCreateStreamingSceneMethodIndex"),
            49416,
        ),
        (
            "managed_base_scene_create_token",
            managed.get("baseGameSceneCreateStreamingSceneMethodToken"),
            "0x0600C109",
        ),
        (
            "managed_parameter_layout",
            managed.get("streamingSceneParameter"),
            expected_parameter,
        ),
        (
            "managed_base_scene_offsets",
            managed.get("baseGameSceneFieldOffsets"),
            expected_base_scene_offsets,
        ),
        (
            "managed_map_config_offsets",
            managed.get("streamingMapConfigFieldOffsets"),
            expected_map_config_offsets,
        ),
        ("native_icall_index", native.get("createInjectedIcallIndex"), 621),
        (
            "native_icall_name",
            native.get("createInjectedIcallName"),
            STREAMING_SCENE_V2_CREATE_ICALL_NAME,
        ),
        (
            "native_icall_function",
            native.get("createInjectedIcallFunction"),
            "0x1801DE220",
        ),
        ("native_path_formats", native.get("pathFormats"), expected_native_paths),
        (
            "native_compression",
            native.get("compression"),
            "uint32 little-endian decompressed size followed by Unity "
            "interleaved-token LZ4 with big-endian match offsets",
        ),
        ("native_binary_bodies", native.get("binaryBodies"), binary_rows),
        ("native_entity_dispatch", entity_dispatch, native_entity_dispatch),
        ("entity_type_enums", enums, entity_type_enums),
        ("component67_owners", owners, component67_owners),
        (
            "component67_initial_data",
            initial_data,
            component67_initial_data,
        ),
        (
            "map_object_index_hash",
            configs.get("objectIndexObjectsGzipSha256"),
            "6f59db82177cd1abd027bfed385145337403a5b0791bcb628287b53e1ad341cd",
        ),
        (
            "map_schema_index_hash",
            configs.get("objectIndexSchemasGzipSha256"),
            "52b320d7e9933c64d6ab95a3572802f2f1bec96038b6bacfcae3b61780de407d",
        ),
        ("map_config_count", configs.get("configCount"), 83),
        ("map_unique_identity_count", configs.get("uniqueIdentityCount"), 83),
        (
            "map_normalized_digest",
            configs.get("normalizedConfigSha256"),
            "0ddc044ba3cf18e417f0c265ff1db74a84267cfbf753a39d72ca9fd64eb1a19e",
        ),
        ("map_chunk_info_root_count", configs.get("chunkInfoRootCount"), 83),
        ("map_missing_roots", configs.get("missingChunkInfoRoots"), 0),
        ("map_extra_roots", configs.get("extraChunkInfoRoots"), 0),
        ("vfs_file_count", vfs.get("fileCount"), 53206),
        ("vfs_chunk_count", vfs.get("chunkCount"), 89),
        ("vfs_total_bytes", vfs.get("totalBytes"), 752851287),
        (
            "vfs_file_digest",
            vfs.get("normalizedFileRecordsSha256"),
            "9ce5d487f7eee9b46a2af6b5995e1fa0d499db30a9bb8146501d1bf68d10dc0e",
        ),
        (
            "vfs_chunk_digest",
            vfs.get("normalizedChunksSha256"),
            "76a03a03b5bc32a083a373bd0d2959731ddf81b7dd0268608d7240f5883a9653",
        ),
        (
            "vfs_block_digest",
            vfs.get("normalizedBlocksSha256"),
            "7e9cdd8b5b9e4c0bf96977f278dec7dbc89a7353b304cde2b891fac3b17edcd8",
        ),
        (
            "vfs_streaming_block",
            blocks.get("Streaming"),
            {"fileCount": 51095, "chunkCount": 65, "totalBytes": 700205610},
        ),
        (
            "vfs_dynamic_block",
            blocks.get("DynamicStreaming"),
            {"fileCount": 2111, "chunkCount": 24, "totalBytes": 52645677},
        ),
        (
            "vfs_chunk_info_count",
            (families.get("StreamingChunkInfo") or {}).get("fileCount"),
            83,
        ),
        (
            "vfs_init_chunk_count",
            (families.get("InitChunkData") or {}).get("fileCount"),
            25506,
        ),
        (
            "vfs_streaming_chunk_count",
            (families.get("StreamingChunkData") or {}).get("fileCount"),
            25506,
        ),
        ("payload_file_count", payloads.get("fileCount"), 51012),
        ("payload_compressed_bytes", payloads.get("compressedBytes"), 699441638),
        (
            "payload_decompressed_bytes",
            payloads.get("decompressedBytes"),
            3088714060,
        ),
        (
            "payload_union_record_count",
            payloads.get("unionRecordCount"),
            3084834,
        ),
        (
            "payload_tag_counts",
            payloads.get("recordTagCounts"),
            {"1": 66514, "2": 2933422, "3": 84898},
        ),
        (
            "payload_source_digest",
            payloads.get("normalizedSourceSha256"),
            "6911a86a785c84334b98b7226e915a320f83989f203da641dd207d1f5637ae5b",
        ),
        (
            "payload_component_bits",
            payloads.get("componentBits"),
            STREAMING_SCENE_V2_COMPONENT_BITS,
        ),
        (
            "payload_ecs_entity_types",
            payloads.get("ecsEntityTypes"),
            [
                {"value": 0, "name": "Render", "entityCount": 34672, "fileCount": 1384},
                {"value": 1, "name": "Water", "entityCount": 3976, "fileCount": 118},
                {"value": 2, "name": "ConvexCollider", "entityCount": 4002, "fileCount": 1238},
                {"value": 5, "name": "MeshCollider", "entityCount": 5110, "fileCount": 3098},
                {"value": 6, "name": "MultiCollider", "entityCount": 205656, "fileCount": 7878},
                {"value": 7, "name": "TerrainCollider", "entityCount": 13600, "fileCount": 3646},
                {"value": 8, "name": "TerrainDecal", "entityCount": 4488, "fileCount": 428},
                {"value": 9, "name": "MergedRenderCollider", "entityCount": 2576964, "fileCount": 4720},
                {"value": 10, "name": "HGDecalProjector", "entityCount": 83976, "fileCount": 1338},
                {"value": 12, "name": "HGStreamingVolume", "entityCount": 326, "fileCount": 172},
                {"value": 13, "name": "WaterDecal", "entityCount": 652, "fileCount": 22},
            ],
        ),
        (
            "payload_proxy_entity_types",
            payloads.get("proxyEntityTypes"),
            [
                {"value": 0, "name": "IrradianceVolume", "entityCount": 166, "fileCount": 166},
                {"value": 1, "name": "AudioVolume", "entityCount": 17238, "fileCount": 2750},
                {"value": 2, "name": "AudioEmitter", "entityCount": 24020, "fileCount": 2362},
                {"value": 3, "name": "AudioRoom", "entityCount": 8560, "fileCount": 2852},
                {"value": 4, "name": "TerrainSurfaceTypeData", "entityCount": 9856, "fileCount": 9856},
                {"value": 5, "name": "AudioPortal", "entityCount": 3560, "fileCount": 956},
                {"value": 6, "name": "SOCChunk", "entityCount": 6864, "fileCount": 2348},
                {"value": 7, "name": "GrassGrid", "entityCount": 8968, "fileCount": 1256},
                {"value": 8, "name": "GpuClothGroup", "entityCount": 4278, "fileCount": 652},
                {"value": 9, "name": "TreeGrid", "entityCount": 1388, "fileCount": 94},
            ],
        ),
        (
            "payload_hlod_bit11_count",
            payloads.get("hlodGroupBit11ComponentCount"),
            0,
        ),
        (
            "payload_hgtree_bit41_count",
            payloads.get("hgtreeBit41ComponentCount"),
            0,
        ),
        ("dynamic_union_file_count", dynamic_union.get("fileCount"), 1576),
        (
            "dynamic_union_compressed_bytes",
            dynamic_union.get("compressedBytes"),
            42598293,
        ),
        (
            "dynamic_union_decompressed_bytes",
            dynamic_union.get("decompressedBytes"),
            239185352,
        ),
        ("dynamic_union_record_count", dynamic_union.get("unionRecordCount"), 289786),
        (
            "dynamic_union_tag_counts",
            dynamic_union.get("recordTagCounts"),
            {"2": 289786},
        ),
        (
            "dynamic_union_component_count",
            dynamic_union.get("componentEntryCount"),
            0,
        ),
        (
            "dynamic_union_source_digest",
            dynamic_union.get("normalizedSourceSha256"),
            "7db9adf49d748ecf68cfe87f063c90d9d184b5f41c6968783b5f4ee8e292f33b",
        ),
        ("dynamic_main_file_count", dynamic_main.get("fileCount"), 457),
        ("dynamic_main_source_bytes", dynamic_main.get("sourceBytes"), 10035624),
        ("dynamic_main_grid_count", dynamic_main.get("gridCount"), 4710),
        (
            "dynamic_main_source_digest",
            dynamic_main.get("normalizedSourceSha256"),
            "e78970ca470d8ad42ee2c1c254ec76b0d25f812dcca2be3bd7a8f90e7fce23f7",
        ),
        (
            "dynamic_main_tree_root_count",
            dynamic_main.get("treeRootCompCount"),
            2828,
        ),
        (
            "dynamic_main_tree_root_file_count",
            dynamic_main.get("treeRootCompFileCount"),
            84,
        ),
        (
            "dynamic_main_nature_resource_count",
            dynamic_main.get("natureResourceCompCount"),
            2828,
        ),
        (
            "dynamic_main_lod_grid_count",
            dynamic_main.get("lodGridResourceCount"),
            2771,
        ),
        (
            "dynamic_main_tree_system_value",
            dynamic_main.get("dynamicSystemTreeValue"),
            11,
        ),
        (
            "dynamic_main_tree_data_value",
            dynamic_main.get("dynamicSceneDataTreeRootCompValue"),
            64,
        ),
        (
            "dynamic_main_tree_fields",
            dynamic_main.get("treeRootCompFields"),
            {"tid": "Int32", "normalModel": "Int64"},
        ),
    )
    for check, actual, expected in checks:
        require(f"streaming_scene_v2_census_{check}", actual, expected, source)

    return {
        "managedBridge": managed,
        "nativeLoader": native,
        "nativeEntityDispatch": entity_dispatch,
        "entityTypeEnums": enums,
        "component67Owners": owners,
        "component67InitialData": initial_data,
        "serializedMapConfigs": configs,
        "installedVfs": vfs,
        "streamingPayloads": payloads,
        "dynamicStreaming": dynamic,
        "boundary": data.get("boundary"),
    }


def validate_native_handoff(
    bodies: dict[str, bytes], *, verify_hashes: bool = True
) -> dict[str, object]:
    for name, spec in NATIVE_METHODS.items():
        body = bodies[name]
        require(
            f"{name}_body_size",
            len(body),
            spec["sizeBytes"],
            GAME_ASSEMBLY,
        )
        if verify_hashes:
            require(
                f"{name}_body_sha256",
                hashlib.sha256(body).hexdigest(),
                EXPECTED_HASHES[f"{name}_body"],
                GAME_ASSEMBLY,
            )

    managed_streaming_bindings = validate_managed_streaming_component_bindings(
        bodies["streaming_scene_manager_ctor"]
    )

    getter = bodies["get_visible_lights"]
    require(
        "light_cull_result_native_array_projection",
        getter,
        bytes.fromhex(
            "4883ec18488b028b52084889042489542408c744240c010000000f100424"
            "0f1101488bc14883c418c3cccccc"
        ),
        GAME_ASSEMBLY,
    )

    cull = bodies["cull_lights"]
    require(
        "cull_lights_internal_call",
        relative_call_target(cull, int(NATIVE_METHODS["cull_lights"]["virtualAddress"]), 0x63),
        NATIVE_METHODS["cull_lights_internal"]["virtualAddress"],
        GAME_ASSEMBLY,
    )
    require(
        "cull_lights_sret_zero",
        cull[0x32:0x35],
        bytes.fromhex("0f1101"),
        GAME_ASSEMBLY,
    )
    require(
        "cull_lights_sret_copy_and_return",
        cull[0x68:0x74],
        bytes.fromhex("0f10442450f30f7f03488bc3"),
        GAME_ASSEMBLY,
    )

    internal = bodies["cull_lights_internal"]
    require(
        "cull_lights_injected_call",
        relative_call_target(
            internal,
            int(NATIVE_METHODS["cull_lights_internal"]["virtualAddress"]),
            0x1F,
        ),
        NATIVE_METHODS["cull_lights_injected"]["virtualAddress"],
        GAME_ASSEMBLY,
    )
    require(
        "cull_lights_injected_tail_jump",
        bodies["cull_lights_injected"][0x3E:0x60],
        bytes.fromhex(
            "448bc78bcd448bcb488bd6488b5c2440488b6c2448488b7424504883c4305f48ffe0"
        ),
        GAME_ASSEMBLY,
    )

    do_cull = bodies["do_ecs_culling"]
    do_cull_va = int(NATIVE_METHODS["do_ecs_culling"]["virtualAddress"])
    for offset in (0x63E, 0x7E4):
        require(
            f"do_ecs_culling_call_{offset:X}",
            relative_call_target(do_cull, do_cull_va, offset),
            NATIVE_METHODS["cull_lights"]["virtualAddress"],
            GAME_ASSEMBLY,
        )
    require(
        "do_ecs_culling_normal_arguments",
        do_cull[0x618:0x63E],
        bytes.fromhex(
            "4c896424304c8d459089442428488d4da041b90001000089742420"
            "8bd3f20f11759044897598"
        ),
        GAME_ASSEMBLY,
    )
    require(
        "do_ecs_culling_ui_arguments",
        do_cull[0x7BF:0x7E4],
        bytes.fromhex(
            "4c897424304c8d459089442428488d4da041b900010000897c2420"
            "8bd3f20f117590897598"
        ),
        GAME_ASSEMBLY,
    )
    require(
        "do_ecs_culling_normal_result_copy",
        do_cull[0x643:0x64E],
        bytes.fromhex("33c90f1000f3410f7f4728"),
        GAME_ASSEMBLY,
    )
    require(
        "do_ecs_culling_ui_result_copy",
        do_cull[0x7E9:0x7F2],
        bytes.fromhex("0f1000f3410f7f4728"),
        GAME_ASSEMBLY,
    )

    setup = bodies["setup_state"]
    require(
        "setup_state_result_projection_arguments",
        setup[0x56:0x6C],
        bytes.fromhex("488d4df7448b470841b901000000488b174889442420"),
        GAME_ASSEMBLY,
    )
    require(
        "setup_state_native_count_cap",
        setup[0x75:0x9C],
        bytes.fromhex(
            "488d55f7b800010000660f7f75f7660f6fc6488d4de7660f73d808"
            "66410f7ec1443bc8440f4fc8"
        ),
        GAME_ASSEMBLY,
    )
    require(
        "setup_state_punctual_type_filter",
        setup[0x138:0x142],
        bytes.fromhex("833f027435833f007430"),
        GAME_ASSEMBLY,
    )
    require(
        "setup_state_world_position_offsets",
        setup[0x181:0x18D],
        bytes.fromhex("f20f1047744c8d45b78b477c"),
        GAME_ASSEMBLY,
    )
    require(
        "setup_state_priority_and_stride",
        setup[0x1C7:0x1EF],
        bytes.fromhex(
            "488b43208b4f70f30f1145ebf20f1045e7f20f110406894c0608"
            "41ffc74881c7940000004883c60c"
        ),
        GAME_ASSEMBLY,
    )

    hgtree_component_get_id = bodies["hgtree_component_get_id"]
    require(
        "hgtree_component_get_id_body",
        hgtree_component_get_id,
        bytes.fromhex("b850000000c3"),
        GAME_ASSEMBLY,
    )
    hgtree_component_id = struct.unpack_from(
        "<I", hgtree_component_get_id, 1
    )[0]
    require(
        "hgtree_component_get_id_value",
        hgtree_component_id,
        80,
        GAME_ASSEMBLY,
    )
    require(
        "hgtree_component_is_not_component_67",
        hgtree_component_id != 67,
        True,
        GAME_ASSEMBLY,
    )
    render_object_lod_info_get_id = bodies[
        "render_object_lod_info_component_get_id"
    ]
    require(
        "render_object_lod_info_component_get_id_body",
        render_object_lod_info_get_id,
        bytes.fromhex("b806000000c3"),
        GAME_ASSEMBLY,
    )
    render_object_lod_info_component_id = struct.unpack_from(
        "<I", render_object_lod_info_get_id, 1
    )[0]
    require(
        "render_object_lod_info_component_get_id_value",
        render_object_lod_info_component_id,
        6,
        GAME_ASSEMBLY,
    )
    require(
        "render_object_lod_info_component_is_not_component_67",
        render_object_lod_info_component_id != 67,
        True,
        GAME_ASSEMBLY,
    )

    return {
        "resultAbi": {
            "type": "UnityEngine.HyperGryph.LightCullResult",
            "sizeBytes": 16,
            "fields": {
                "visibleLightsPtr": {"offset": 0, "sizeBytes": 8},
                "visibleLightCount": {"offset": 8, "sizeBytes": 4},
                "tailPadding": {"offset": 12, "sizeBytes": 4},
            },
            "nativeArrayProjection": {
                "sizeBytes": 16,
                "bufferOffset": 0,
                "lengthOffset": 8,
                "allocatorLabelOffset": 12,
                "allocatorLabel": 1,
            },
        },
        "managedCallSites": {
            "caller": NATIVE_METHODS["do_ecs_culling"]["method"],
            "offsets": ["0x63E", "0x7E4"],
            "hiddenSret": "rcx=&[rbp-0x60]",
            "viewHandle": "edx=ebx",
            "cameraPosition": "r8=&[rbp-0x70]",
            "maxCount": 256,
            "cameraInstanceId": "stack+0x20",
            "currentDeviceTier": "stack+0x28",
            "resultCopy": "16 bytes to culling output +0x28",
        },
        "captureRowContract": {
            "elementType": "UnityEngine.Rendering.VisibleLight",
            "elementStrideBytes": 148,
            "minimumRawBytesEquation": "visibleLightCount * 148",
            "validatedConsumerOffsets": {
                "lightType": "0x00",
                "lightPriority": "0x70",
                "worldPosition": "0x74..0x7F",
            },
            "setupStateInputCap": 256,
            "acceptedPunctualTypes": [0, 2],
        },
        "managedHGTreeComponent": {
            "type": "UnityEngine.HyperGryph.ECS.HGTreeComponent",
            "method": "get_id",
            "metadataMethodIndex": NATIVE_METHODS[
                "hgtree_component_get_id"
            ]["methodIndex"],
            "metadataToken": NATIVE_METHODS[
                "hgtree_component_get_id"
            ]["token"],
            "virtualAddress": (
                f"0x{NATIVE_METHODS['hgtree_component_get_id']['virtualAddress']:X}"
            ),
            "componentId": hgtree_component_id,
            "archetypeMask": {
                "bank": hgtree_component_id >> 6,
                "bit": hgtree_component_id & 63,
                "highQwordMask": "0x0000000000010000",
            },
            "component67Match": False,
            "proof": (
                "the hash-pinned six-byte IL2CPP body is mov eax, 0x50; "
                "ret, so HGTreeComponent is component id 80 rather than 67"
            ),
        },
        "managedRenderObjectLODInfoComponent": {
            "type": (
                "UnityEngine.HyperGryph.ECS.RenderObjectLODInfoComponent"
            ),
            "method": "get_id",
            "metadataMethodIndex": NATIVE_METHODS[
                "render_object_lod_info_component_get_id"
            ]["methodIndex"],
            "metadataToken": NATIVE_METHODS[
                "render_object_lod_info_component_get_id"
            ]["token"],
            "virtualAddress": (
                "0x"
                f"{NATIVE_METHODS['render_object_lod_info_component_get_id']['virtualAddress']:X}"
            ),
            "componentId": render_object_lod_info_component_id,
            "component67Match": False,
            "proof": (
                "the hash-pinned six-byte IL2CPP body is mov eax, 6; ret, "
                "so this managed LOD-info component is not native component id 67"
            ),
        },
        "managedStreamingComponentBindings": managed_streaming_bindings,
        "methodBodies": [
            {
                "name": name,
                "method": spec["method"],
                "methodIndex": spec["methodIndex"],
                "virtualAddress": f"0x{int(spec['virtualAddress']):X}",
                "fileOffset": f"0x{int(spec['fileOffset']):X}",
                "sizeBytes": spec["sizeBytes"],
                "sha256": hashlib.sha256(bodies[name]).hexdigest(),
            }
            for name, spec in NATIVE_METHODS.items()
        ],
    }


def validate_unity_native_producer(image: PEImage) -> dict[str, object]:
    require("unity_player_image_base", image.image_base, 0x180000000, image.path)
    target = image.u64(
        UNITY_ICALL_FUNCTION_TABLE_VA + UNITY_CULL_LIGHTS_ICALL_INDEX * 8
    )
    name_pointer = image.u64(
        UNITY_ICALL_NAME_TABLE_VA + UNITY_CULL_LIGHTS_ICALL_INDEX * 8
    )
    name = image.cstring(name_pointer)
    require("unity_cull_lights_icall_target", target, UNITY_CULL_LIGHTS_ICALL_VA, image.path)
    require("unity_cull_lights_icall_name", name, UNITY_CULL_LIGHTS_ICALL_NAME, image.path)

    slices = []
    for label, (virtual_address, expected_hex) in UNITY_CULLING_SLICES.items():
        expected = bytes.fromhex(expected_hex)
        actual = image.read(virtual_address, len(expected))
        require(f"unity_{label}", actual, expected, image.path)
        slices.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": len(actual),
                "sha256": hashlib.sha256(actual).hexdigest(),
            }
        )
    return {
        "internalCall": {
            "index": UNITY_CULL_LIGHTS_ICALL_INDEX,
            "name": name,
            "targetVirtualAddress": f"0x{target:X}",
        },
        "callChain": [
            "0x1800FBCE0 injected binding",
            "0x181050FC0 result/lifetime wrapper",
            "0x181051A40 native candidate core",
        ],
        "candidateRecord": {
            "sizeBytes": 12,
            "fields": ["native light pointer (8 bytes)", "camera distanceSquared (4 bytes)"],
        },
        "closedBehavior": [
            "PC device-tier min/max gate",
            "maximum culling-distance gate",
            "minimum far-show-distance gate",
            "authored OBB gate and builder call",
            "directional/Spot/Point geometry branches",
            "Spot/frustum helper call",
            "occlusion result-bit consumption",
            "ascending distance sort call and comparator",
            "maxCount output cap",
        ],
        "verifiedInstructionSlices": slices,
    }


def validate_streaming_component_conversion(
    image: PEImage,
    metadata: bytes | None = None,
    *,
    metadata_source: Path = GLOBAL_METADATA,
    managed_component_ids: dict[str, int] | None = None,
) -> dict[str, object]:
    """Close the hash-pinned StreamingComponentType-to-converter boundary."""

    require("unity_player_image_base", image.image_base, 0x180000000, image.path)
    require(
        "unity_bind_mono_component_convert_icall_index_in_bounds",
        UNITY_BIND_MONO_COMPONENT_CONVERT_ICALL_INDEX < UNITY_HG_ICALL_COUNT,
        True,
        image.path,
    )
    index = UNITY_BIND_MONO_COMPONENT_CONVERT_ICALL_INDEX
    name_pointer = image.u64(UNITY_HG_ICALL_NAME_TABLE_VA + index * 8)
    target = image.u64(UNITY_HG_ICALL_FUNCTION_TABLE_VA + index * 8)
    name = image.cstring(name_pointer)
    require(
        "unity_bind_mono_component_convert_icall_name",
        name,
        UNITY_BIND_MONO_COMPONENT_CONVERT_ICALL_NAME,
        image.path,
    )
    require(
        "unity_bind_mono_component_convert_icall_target",
        target,
        UNITY_BIND_MONO_COMPONENT_CONVERT_ICALL_VA,
        image.path,
    )

    bodies = []
    body_bytes: dict[str, bytes] = {}
    for label, (virtual_address, size_bytes, expected_hash) in (
        UNITY_STREAMING_CONVERSION_BODIES.items()
    ):
        body = image.read(virtual_address, size_bytes)
        actual_hash = hashlib.sha256(body).hexdigest()
        require(
            f"unity_streaming_{label}_sha256",
            actual_hash,
            expected_hash,
            image.path,
        )
        body_bytes[label] = body
        bodies.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": size_bytes,
                "sha256": actual_hash,
            }
        )

    binding = body_bytes["bind_mono_component_convert"]
    require(
        "unity_streaming_bind_to_registry_call",
        relative_call_target(binding, 0x1801DFF50, 0xFD),
        0x181170720,
        image.path,
    )
    slices = {
        "register_mask_to_slot": (
            0x181170AD6,
            "480fbcc64981c630400000488d95700600004869c8080300004903cee8b97f08ff",
        ),
        "construct_43_converter_slots": (
            0x18117B143,
            "b92b000000498d82d83f0000904889104889504048899080000000488990c0000000"
            "488990000100004889904001000048899080010000488990c001000048899000020000"
            "4889904002000048899080020000488990c002000048899000030000488d8008030000"
            "4883e901759f",
        ),
        "convert_type_mask_to_descriptor": (
            0x181150673,
            "480fbcc14869d8080300004881c3d83f00004803df4c",
        ),
        "require_nonempty_component_list": (
            0x18116202A,
            "488d3dc4fdb7004439380f85800000004c8bcfc7442420670000004c8d05f419",
        ),
        "require_transform_first": (
            0x1811620E0,
            "8b48044883c0044803c841bd04000000488bd1486301482bd066443b2a73140f"
            "b742046685c0740b48833c08010f8480000000",
        ),
    }
    validated_slices = []
    for label, (virtual_address, expected_hex) in slices.items():
        expected = bytes.fromhex(expected_hex)
        actual = image.read(virtual_address, len(expected))
        require(
            f"unity_streaming_{label}",
            actual,
            expected,
            image.path,
        )
        validated_slices.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": len(actual),
                "sha256": hashlib.sha256(actual).hexdigest(),
            }
        )

    diagnostic_strings = {
        "componentListNotEmpty": (
            0x181E23A68,
            "!fbMonoEntityData->componentDataList()->empty()'",
        ),
        "transformFirst": (
            0x181E23AC8,
            "fbMonoEntityData->componentDataList()->Get(0)->type() == "
            "kComponentTypeTransform'",
        ),
        "unsupportedType": (
            0x181E23CB8,
            "Unsupported component type %u to ConvertFrom",
        ),
    }
    validated_strings = {}
    for label, (virtual_address, expected) in diagnostic_strings.items():
        actual = image.cstring(virtual_address)
        require(
            f"unity_streaming_{label}_string",
            actual,
            expected,
            image.path,
        )
        validated_strings[label] = {
            "virtualAddress": f"0x{virtual_address:X}",
            "value": actual,
        }

    raw_metadata = metadata if metadata is not None else metadata_source.read_bytes()
    require(
        "streaming_component_metadata_magic",
        struct.unpack_from("<I", raw_metadata, 0)[0],
        0xFAB11BAF,
        metadata_source,
    )
    require(
        "streaming_component_metadata_version",
        struct.unpack_from("<I", raw_metadata, 4)[0],
        29,
        metadata_source,
    )
    sections = {}
    for section_index, section_name in enumerate(IL2CPP_METADATA_SECTION_NAMES):
        offset, size = struct.unpack_from(
            "<Ii", raw_metadata, 8 + section_index * 8
        )
        sections[section_name] = (offset, size)
    string_offset, string_size = sections["string"]
    fields_offset, fields_size = sections["fields"]
    defaults_offset, defaults_size = sections["fieldDefaultValues"]
    values_offset, values_size = sections["fieldAndParameterDefaultValueData"]
    require(
        "streaming_component_field_record_alignment",
        fields_size % 12,
        0,
        metadata_source,
    )
    require(
        "streaming_component_default_record_alignment",
        defaults_size % 12,
        0,
        metadata_source,
    )
    defaults = {}
    for position in range(defaults_offset, defaults_offset + defaults_size, 12):
        field_index, type_index, data_index = struct.unpack_from(
            "<iii", raw_metadata, position
        )
        defaults[field_index] = (type_index, data_index)

    enum_fields = {}
    for expected_name, (field_index, expected_token, expected_value) in (
        STREAMING_COMPONENT_ENUM_FIELDS.items()
    ):
        record_offset = fields_offset + field_index * 12
        require(
            f"streaming_component_{expected_name}_field_in_bounds",
            record_offset + 12 <= fields_offset + fields_size,
            True,
            metadata_source,
        )
        name_index, field_type_index, token = struct.unpack_from(
            "<iii", raw_metadata, record_offset
        )
        name_start = string_offset + name_index
        require(
            f"streaming_component_{expected_name}_name_in_bounds",
            string_offset <= name_start < string_offset + string_size,
            True,
            metadata_source,
        )
        name_end = raw_metadata.index(0, name_start, string_offset + string_size)
        actual_name = raw_metadata[name_start:name_end].decode("utf-8")
        require(
            f"streaming_component_{expected_name}_field_name",
            actual_name,
            expected_name,
            metadata_source,
        )
        require(
            f"streaming_component_{expected_name}_field_token",
            token,
            expected_token,
            metadata_source,
        )
        require(
            f"streaming_component_{expected_name}_field_type",
            field_type_index,
            165209,
            metadata_source,
        )
        require(
            f"streaming_component_{expected_name}_default_exists",
            field_index in defaults,
            True,
            metadata_source,
        )
        default_type_index, data_index = defaults[field_index]
        require(
            f"streaming_component_{expected_name}_default_type",
            default_type_index,
            168269,
            metadata_source,
        )
        require(
            f"streaming_component_{expected_name}_default_in_bounds",
            0 <= data_index <= values_size - 8,
            True,
            metadata_source,
        )
        value = struct.unpack_from(
            "<Q", raw_metadata, values_offset + data_index
        )[0]
        require(
            f"streaming_component_{expected_name}_value",
            value,
            expected_value,
            metadata_source,
        )
        enum_fields[expected_name] = {
            "fieldIndex": field_index,
            "token": f"0x{token:08X}",
            "underlyingDefaultTypeIndex": default_type_index,
            "value": value,
            "bitIndex": (
                value.bit_length() - 1
                if value and value & (value - 1) == 0
                else None
            ),
        }

    component_ids = managed_component_ids or {
        "HGTreeComponent": 80,
        "RenderObjectLODInfoComponent": 6,
    }
    require(
        "streaming_component_hgtree_managed_id",
        component_ids.get("HGTreeComponent"),
        80,
        metadata_source,
    )
    require(
        "streaming_component_render_object_lod_info_managed_id",
        component_ids.get("RenderObjectLODInfoComponent"),
        6,
        metadata_source,
    )

    return {
        "internalCall": {
            "index": index,
            "name": name,
            "targetVirtualAddress": f"0x{target:X}",
        },
        "streamingComponentType": {
            "metadataType": (
                "UnityEngine.HyperGryph.Streaming.StreamingComponentType"
            ),
            "underlyingStorage": "UInt64 field-default payloads",
            "selectedFields": enum_fields,
            "slotCount": enum_fields["Count"]["value"],
            "hgtreeBitIndex": enum_fields["HGTree"]["bitIndex"],
            "hlodGroupBitIndex": enum_fields["HLODGroup"]["bitIndex"],
        },
        "conversionContract": {
            "typeToSlotEquation": "bsf(componentTypeMask)",
            "slotStrideBytes": 0x308,
            "slotArrayOffset": "manager + 0x3FD8",
            "constructorSlotCount": 43,
            "componentListMustBeNonEmpty": True,
            "firstComponentType": "Transform (value 1 / bit 0)",
        },
        "managedComponentDisambiguation": {
            "HGTreeComponentId": component_ids["HGTreeComponent"],
            "RenderObjectLODInfoComponentId": component_ids[
                "RenderObjectLODInfoComponent"
            ],
            "component67MatchesEither": False,
            "boundary": (
                "StreamingComponentType HGTree is a serialized converter bit, "
                "not an ECS component id. Managed HGTreeComponent is id 80 and "
                "RenderObjectLODInfoComponent is id 6; native ECS id 67 remains unnamed."
            ),
        },
        "methodBodies": bodies,
        "validatedSlices": validated_slices,
        "diagnosticStrings": validated_strings,
    }


def validate_unity_cull_view_constructor(image: PEImage) -> dict[str, object]:
    require("unity_player_image_base", image.image_base, 0x180000000, image.path)
    target = image.u64(
        UNITY_ICALL_FUNCTION_TABLE_VA + UNITY_ADD_CULL_VIEW_ICALL_INDEX * 8
    )
    name_pointer = image.u64(
        UNITY_ICALL_NAME_TABLE_VA + UNITY_ADD_CULL_VIEW_ICALL_INDEX * 8
    )
    name = image.cstring(name_pointer)
    require(
        "unity_add_cull_view_icall_target",
        target,
        UNITY_ADD_CULL_VIEW_ICALL_VA,
        image.path,
    )
    require(
        "unity_add_cull_view_icall_name",
        name,
        UNITY_ADD_CULL_VIEW_ICALL_NAME,
        image.path,
    )

    bodies = []
    for label, (virtual_address, size_bytes, expected_hash) in UNITY_CULL_VIEW_BODIES.items():
        body = image.read(virtual_address, size_bytes)
        actual_hash = hashlib.sha256(body).hexdigest()
        require(
            f"unity_cull_view_{label}_sha256",
            actual_hash,
            expected_hash,
            image.path,
        )
        bodies.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": size_bytes,
                "sha256": actual_hash,
            }
        )

    slices = []
    for label, (virtual_address, expected_hex) in UNITY_CULL_VIEW_SLICES.items():
        expected = bytes.fromhex(expected_hex)
        actual = image.read(virtual_address, len(expected))
        require(f"unity_cull_view_{label}", actual, expected, image.path)
        slices.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": len(actual),
                "sha256": hashlib.sha256(actual).hexdigest(),
            }
        )

    return {
        "internalCall": {
            "index": UNITY_ADD_CULL_VIEW_ICALL_INDEX,
            "name": name,
            "targetVirtualAddress": f"0x{target:X}",
        },
        "callChain": [
            "0x1800F9790 injected binding and 16-argument repack",
            "0x18104A190 six-plane extraction from the supplied culling matrix",
            "0x18104A7A0 scheduled cull-view constructor",
        ],
        "managedInputContract": {
            "sceneCullingMask": {
                "argumentIndex": 2,
                "scheduledStackSlot": "entry+0x50 / rbp+0x1D8",
                "constructorRead": False,
                "boundary": (
                    "forwarded by the binding/core but not read by the complete "
                    "hash-pinned scheduled-constructor body"
                ),
            },
            "cameraCullingMask": {
                "argumentIndex": 3,
                "scheduledStackSlot": "entry+0x58 / rbp+0x1E0",
                "viewRecordOffset": "0x04",
            },
            "screenSizeMinimum": {
                "argumentIndex": 7,
                "managedTransform": "cullingViewScreenSizeMin squared",
                "scheduledStackSlot": "entry+0x78 / rbp+0x200",
                "viewRecordOffset": "0x18",
                "storage": "verbatim squared float",
                "installedDesktopDefaultBeforeRuntimeOverride": 0.0,
            },
            "occlusionDimensions": {
                "argumentIndices": [10, 11],
                "scheduledStackSlots": [
                    "entry+0x90 / rbp+0x218",
                    "entry+0x98 / rbp+0x220",
                ],
                "allocationGate": "instanceId != 0 && width != 0 && height != 0",
            },
            "occlusionScreenSizeMinimum": {
                "argumentIndex": 15,
                "managedTransform": "ocScreenSizeMin squared",
                "scheduledStackSlot": "entry+0xC0 / rbp+0x248",
                "viewRecordOffset": "0x34",
            },
        },
        "viewRecord": {
            "instanceIdOffset": "0x00",
            "cameraCullingMaskOffset": "0x04",
            "forcedBit0Words": ["0x08", "0x0C"],
            "lodCrossFadeDataOffset": "0x10",
            "screenSizeMinimumSquaredOffset": "0x18",
            "cameraTypeOffset": "0x2C",
            "uniqueIdOffset": "0x30",
            "occlusionScreenSizeMinimumSquaredOffset": "0x34",
            "planeCountOffset": "0x58",
            "normalizedPlaneArrayOffset": "0x5C",
            "planeCount": 6,
        },
        "candidateGateOrder": [
            "candidate synchronous visibility/AABB-plane result bit 0",
            "candidate mask-enabled flag bit 0",
            "view cameraCullingMask & candidate layer mask != 0",
        ],
        "evidenceBoundary": {
            "closed": [
                "managed-to-native 16-argument repack",
                "six culling-matrix plane extraction and normalization",
                "scheduled view field projection",
                "occlusion allocation gate",
                "generic visibility then culling-mask evaluation order",
            ],
            "open": [
                "later renderer/entity screen-size threshold equation",
                "a separate consumer, if any, for the forwarded sceneCullingMask slot",
                "target-frame runtime overrides and final survivor rows",
            ],
        },
        "verifiedBodies": bodies,
        "verifiedInstructionSlices": slices,
    }


def validate_unity_scheduled_culling_boundary(
    image: PEImage,
) -> dict[str, object]:
    require("unity_player_image_base", image.image_base, 0x180000000, image.path)
    target = image.u64(
        UNITY_ICALL_FUNCTION_TABLE_VA
        + UNITY_DISPATCH_CULL_JOBS_ICALL_INDEX * 8
    )
    name_pointer = image.u64(
        UNITY_ICALL_NAME_TABLE_VA
        + UNITY_DISPATCH_CULL_JOBS_ICALL_INDEX * 8
    )
    name = image.cstring(name_pointer)
    require(
        "unity_dispatch_cull_jobs_icall_target",
        target,
        UNITY_DISPATCH_CULL_JOBS_ICALL_VA,
        image.path,
    )
    require(
        "unity_dispatch_cull_jobs_icall_name",
        name,
        UNITY_DISPATCH_CULL_JOBS_ICALL_NAME,
        image.path,
    )

    bodies = []
    body_bytes: dict[str, bytes] = {}
    for label, (
        virtual_address,
        size_bytes,
        expected_hash,
    ) in UNITY_SCHEDULED_CULL_BODIES.items():
        body = image.read(virtual_address, size_bytes)
        body_bytes[label] = body
        actual_hash = hashlib.sha256(body).hexdigest()
        require(
            f"unity_scheduled_cull_{label}_sha256",
            actual_hash,
            expected_hash,
            image.path,
        )
        bodies.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": size_bytes,
                "sha256": actual_hash,
            }
        )

    scheduled_core_disp18_movss_loads = count_legacy_movss_disp_loads(
        body_bytes["scheduled_batch_core"], 0x18
    )
    require(
        "unity_scheduled_cull_batch_core_direct_movss_disp18_load_count",
        scheduled_core_disp18_movss_loads,
        0,
        image.path,
    )

    slices = []
    for label, (
        virtual_address,
        expected_hex,
    ) in UNITY_SCHEDULED_CULL_SLICES.items():
        expected = bytes.fromhex(expected_hex)
        actual = image.read(virtual_address, len(expected))
        require(f"unity_scheduled_cull_{label}", actual, expected, image.path)
        slices.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": len(actual),
                "sha256": hashlib.sha256(actual).hexdigest(),
            }
        )

    return {
        "internalCall": {
            "index": UNITY_DISPATCH_CULL_JOBS_ICALL_INDEX,
            "name": name,
            "targetVirtualAddress": f"0x{target:X}",
        },
        "callChain": [
            "0x1800FAFC0 internal-call binding",
            "0x181053400 outer dispatch",
            "0x181053010 copy/schedule path",
            "0x181053730 scheduled batch core",
        ],
        "perViewVisibilityPredicate": {
            "selection": (
                "cameraType == 0x80 selects 0x180FEAEF0; all other values "
                "select 0x180FEAEB0 -> 0x181049010"
            ),
            "standard": (
                "six normalized view planes at +0x58/+0x5C test the candidate "
                "AABB center and extent"
            ),
            "cameraType0x80": (
                "distanceSquared <= (max(candidateExtent) + "
                "view.occlusionScreenSizeMinimumSquared@+0x34)^2"
            ),
            "screenSizeMinimumSquaredAt0x18Read": False,
            "boundary": (
                "the two complete hash-pinned predicates selected by this "
                "dispatch stage do not read cull-view +0x18; this does not "
                "prove that later renderer/entity jobs omit the threshold"
            ),
        },
        "screenSizeMinimumSquaredDataflow": {
            "viewRecordOffset": "0x18",
            "scheduledBatchCoreDirectMovssDisplacement0x18Loads": (
                scheduled_core_disp18_movss_loads
            ),
            "dispatchStageConclusion": (
                "the complete hash-pinned scheduled batch core has no legacy "
                "scalar-float load at displacement +0x18; its selected view "
                "predicates also omit the view field"
            ),
            "independentParentLODBiasSquaredFlow": [
                "0x181053358 reads HGCullingSystem state+0x180",
                "0x1810533B3 projects it to the batch-core stack argument",
                "0x1810537F0 reloads it at core entry",
                "0x181054679 forwards it to child-job payload+0x1B0",
                "0x181045F8E reloads the callback-visible payload+0x3C",
            ],
            "nonEquivalence": (
                "parentLODBiasSquared is an independent HGCullingSystem state "
                "value and is not evidence of a cull-view +0x18 read"
            ),
            "openBoundary": (
                "this dispatch-only validator is paired with the separate "
                "CullView consumer-surface validator"
            ),
        },
        "evidenceBoundary": {
            "closed": [
                "DispatchBatchCullingJobs internal-call binding and native call chain",
                "camera-type predicate selection",
                "standard six-plane AABB predicate",
                "cameraType 0x80 sphere/distance predicate",
                "absence of cull-view +0x18 from those two selected predicates",
                "absence of any direct legacy MOVSS +0x18 load from the complete scheduled batch core",
                "the independent parentLODBiasSquared batch/child-job forwarding chain",
            ],
            "open": [
                "target-frame runtime overrides and final survivor rows",
            ],
        },
        "verifiedBodies": bodies,
        "verifiedInstructionSlices": slices,
    }


def validate_unity_cull_view_consumer_surface(
    image: PEImage,
) -> dict[str, object]:
    """Close the installed CullView pointer-container consumer surface."""

    require("unity_player_image_base", image.image_base, 0x180000000, image.path)
    internal_calls = []
    for label, (index, expected_target, expected_name) in (
        UNITY_CULL_VIEW_SURFACE_ICALLS.items()
    ):
        target = image.u64(UNITY_ICALL_FUNCTION_TABLE_VA + index * 8)
        name_pointer = image.u64(UNITY_ICALL_NAME_TABLE_VA + index * 8)
        name = image.cstring(name_pointer)
        require(
            f"unity_cull_view_surface_{label}_target",
            target,
            expected_target,
            image.path,
        )
        require(
            f"unity_cull_view_surface_{label}_name",
            name,
            expected_name,
            image.path,
        )
        internal_calls.append(
            {
                "label": label,
                "index": index,
                "name": name,
                "targetVirtualAddress": f"0x{target:X}",
            }
        )

    bodies = []
    for label, (
        virtual_address,
        size_bytes,
        expected_hash,
    ) in UNITY_CULL_VIEW_CONSUMER_BODIES.items():
        body = image.read(virtual_address, size_bytes)
        actual_hash = hashlib.sha256(body).hexdigest()
        require(
            f"unity_cull_view_consumer_{label}_sha256",
            actual_hash,
            expected_hash,
            image.path,
        )
        bodies.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": size_bytes,
                "sha256": actual_hash,
            }
        )

    slices = []
    for label, (
        virtual_address,
        expected_hex,
    ) in UNITY_CULL_VIEW_CONSUMER_SLICES.items():
        expected = bytes.fromhex(expected_hex)
        actual = image.read(virtual_address, len(expected))
        require(f"unity_cull_view_consumer_{label}", actual, expected, image.path)
        slices.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": len(actual),
                "sha256": hashlib.sha256(actual).hexdigest(),
            }
        )

    return {
        "internalCallSurface": {
            "entries": internal_calls,
            "boundedToCullViewNamedOperations": True,
        },
        "pointerContainerFlow": [
            "0x18104B814 appends the scheduled view pointer to manager+0x38",
            "0x181053373 passes manager+0x38+start*8 directly as batch-core argument 5",
            "0x1810539DD reloads that pointer array and 0x181053A14 selects one view pointer",
            "the 0x181053A10..0x181053C76 view loop reads +0x20/+0x28/+0x2C/+0x54 and calls the selected predicate with the original pointer",
        ],
        "consumerCensus": {
            "screenSizeMinimumSquaredOffset": "0x18",
            "consumerFound": False,
            "scheduledViewLoopReadOffsets": ["0x20", "0x28", "0x2C", "0x54"],
            "selectedPredicateReadOffsets": {
                "standardSixPlane": ["0x58", "0x5C"],
                "cameraType0x80": ["0x10", "0x34"],
            },
            "getFence": "reads only view+0x20 before returning its 16-byte fence payload",
            "reset": "iterates manager+0x38 and frees only the nested allocation at view+0x38",
            "uniqueIdRegistry": (
                "Register/UnregisterCullViewUniqueId operate on the separate "
                "manager+0x158 integer free-list/registry and never receive a "
                "scheduled-view pointer"
            ),
            "childViewSeparation": (
                "AddCullChildViewByPlanes appends a separate 0xE8-byte record "
                "to manager+0x58; it does not copy the scheduled view+0x18 word"
            ),
            "postDispatchPacketCopy": False,
        },
        "installedConclusion": (
            "screenSizeMinimumSquared at scheduled view+0x18 is written by the "
            "installed constructors but is not consumed by the complete "
            "CullView-named API surface, batch view loop, selected predicates, "
            "fence lookup, or reset lifecycle"
        ),
        "evidenceBoundary": {
            "closed": [
                "all installed CullView-named internal-call entries from add through fence lookup",
                "the manager+0x38 scheduled-view pointer container and direct batch-core handoff",
                "the complete per-view batch loop and its direct view-field reads",
                "the two selected predicate field sets",
                "the reset and fence consumers of the same pointer container",
                "the separate CullView unique-id free-list/registry",
                "the separate manager+0x58 child-view record path",
                "absence of a post-dispatch packet copy or installed consumer of scheduled view+0x18 on this surface",
            ],
            "open": [
                "future or separately delivered native patches that change the pinned installed bodies",
                "target-frame survivor rows and unrelated runtime/custom culling inputs",
            ],
        },
        "verifiedBodies": bodies,
        "verifiedInstructionSlices": slices,
    }


def validate_unity_hgtree_renderer_boundary(
    image: PEImage,
    managed_hgtree_component: dict[str, object] | None = None,
    metadata: bytes | None = None,
) -> dict[str, object]:
    """Pin HGTreeRenderer ownership without merging it into scheduled culling."""

    if managed_hgtree_component is None:
        managed_hgtree_component = validate_native_handoff(
            read_native_method_bodies()
        )["managedHGTreeComponent"]
    require("unity_player_image_base", image.image_base, 0x180000000, image.path)
    require(
        "managed_hgtree_component_id",
        managed_hgtree_component.get("componentId"),
        80,
        GAME_ASSEMBLY,
    )
    require(
        "managed_hgtree_component_component_67_match",
        managed_hgtree_component.get("component67Match"),
        False,
        GAME_ASSEMBLY,
    )
    require(
        "unity_hg_icall_create_renderer_list_index_in_bounds",
        UNITY_HGTREE_CREATE_RENDERER_LIST_ICALL_INDEX < UNITY_HG_ICALL_COUNT,
        True,
        image.path,
    )
    require(
        "unity_hg_icall_get_or_register_entity_type_index_in_bounds",
        (
            UNITY_ECS_GET_OR_REGISTER_ENTITY_TYPE_ICALL_INDEX
            < UNITY_HG_ICALL_COUNT
        ),
        True,
        image.path,
    )
    require(
        "unity_hg_icall_register_batch_group_index_in_bounds",
        UNITY_HGTREE_REGISTER_BATCH_GROUP_ICALL_INDEX < UNITY_HG_ICALL_COUNT,
        True,
        image.path,
    )
    require(
        "unity_hg_icall_unregister_batch_group_index_in_bounds",
        UNITY_HGTREE_UNREGISTER_BATCH_GROUP_ICALL_INDEX < UNITY_HG_ICALL_COUNT,
        True,
        image.path,
    )
    require(
        "unity_hg_icall_unregister_batch_group_with_handle_index_in_bounds",
        (
            UNITY_HGTREE_UNREGISTER_BATCH_GROUP_WITH_HANDLE_ICALL_INDEX
            < UNITY_HG_ICALL_COUNT
        ),
        True,
        image.path,
    )
    require(
        "unity_hg_icall_set_enabled_light_modes_index_in_bounds",
        UNITY_FACTORY_SET_ENABLED_LIGHT_MODES_ICALL_INDEX < UNITY_HG_ICALL_COUNT,
        True,
        image.path,
    )
    require(
        "unity_gpu_driven_renderer_icall_indices_in_bounds",
        max(
            UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_ICALL_INDEX,
            UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_PREZ_ICALL_INDEX,
            UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_ICALL_INDEX,
            UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_PREZ_ICALL_INDEX,
        )
        < UNITY_HG_ICALL_COUNT,
        True,
        image.path,
    )
    table_size = UNITY_HG_ICALL_COUNT * 8
    name_table = image.read(UNITY_HG_ICALL_NAME_TABLE_VA, table_size)
    function_table = image.read(UNITY_HG_ICALL_FUNCTION_TABLE_VA, table_size)
    require(
        "unity_hg_icall_name_table_sha256",
        hashlib.sha256(name_table).hexdigest(),
        UNITY_HG_ICALL_NAME_TABLE_SHA256,
        image.path,
    )
    require(
        "unity_hg_icall_function_table_sha256",
        hashlib.sha256(function_table).hexdigest(),
        UNITY_HG_ICALL_FUNCTION_TABLE_SHA256,
        image.path,
    )
    require(
        "unity_hg_icall_name_table_separator",
        image.u64(UNITY_HG_ICALL_NAME_TABLE_VA + table_size),
        0,
        image.path,
    )
    require(
        "unity_hg_icall_function_table_end_boundary",
        image.u64(UNITY_HG_ICALL_FUNCTION_TABLE_VA + table_size),
        0x4120000042000000,
        image.path,
    )

    def resolve_hg_icall(index: int) -> tuple[str, int]:
        name_pointer = image.u64(UNITY_HG_ICALL_NAME_TABLE_VA + index * 8)
        target = image.u64(UNITY_HG_ICALL_FUNCTION_TABLE_VA + index * 8)
        return image.cstring(name_pointer), target

    name, target = resolve_hg_icall(
        UNITY_HGTREE_CREATE_RENDERER_LIST_ICALL_INDEX
    )
    resource_load_name, resource_load_target = resolve_hg_icall(
        UNITY_HG_RESOURCE_LOAD_ASYNC_ICALL_INDEX
    )
    resource_get_asset_name, resource_get_asset_target = resolve_hg_icall(
        UNITY_HG_RESOURCE_GET_ASSET_ICALL_INDEX
    )
    resource_update_handle_name, resource_update_handle_target = resolve_hg_icall(
        UNITY_HG_RESOURCE_UPDATE_HANDLE_ICALL_INDEX
    )
    geometry_get_handle_name, geometry_get_handle_target = resolve_hg_icall(
        UNITY_HG_GEOMETRY_GET_HANDLE_ICALL_INDEX
    )
    geometry_get_mesh_name, geometry_get_mesh_target = resolve_hg_icall(
        UNITY_HG_GEOMETRY_GET_MESH_ICALL_INDEX
    )
    entity_type_name, entity_type_target = resolve_hg_icall(
        UNITY_ECS_GET_OR_REGISTER_ENTITY_TYPE_ICALL_INDEX
    )
    require(
        "unity_ecs_get_or_register_entity_type_icall_target",
        entity_type_target,
        UNITY_ECS_GET_OR_REGISTER_ENTITY_TYPE_ICALL_VA,
        image.path,
    )
    require(
        "unity_ecs_get_or_register_entity_type_icall_name",
        entity_type_name,
        UNITY_ECS_GET_OR_REGISTER_ENTITY_TYPE_ICALL_NAME,
        image.path,
    )
    require(
        "unity_hgtree_create_renderer_list_icall_target",
        target,
        UNITY_HGTREE_CREATE_RENDERER_LIST_ICALL_VA,
        image.path,
    )
    require(
        "unity_hgtree_create_renderer_list_icall_name",
        name,
        UNITY_HGTREE_CREATE_RENDERER_LIST_ICALL_NAME,
        image.path,
    )
    renderer_list_variants = [
        {
            "variant": "default",
            "index": UNITY_HGTREE_CREATE_RENDERER_LIST_ICALL_INDEX,
            "name": name,
            "targetVirtualAddress": f"0x{target:X}",
            "coreVirtualAddress": "0x18107EE40",
            "schedulerCallVirtualAddress": "0x18107F258",
        }
    ]
    for (
        label,
        index,
        expected_name,
        expected_target,
        core,
        scheduler_call,
    ) in (
        (
            "child_view",
            UNITY_HGTREE_CREATE_RENDERER_LIST_CHILD_ICALL_INDEX,
            UNITY_HGTREE_CREATE_RENDERER_LIST_CHILD_ICALL_NAME,
            UNITY_HGTREE_CREATE_RENDERER_LIST_CHILD_ICALL_VA,
            0x18107FCF0,
            0x18108012E,
        ),
        (
            "pre_z",
            UNITY_HGTREE_CREATE_RENDERER_LIST_PREZ_ICALL_INDEX,
            UNITY_HGTREE_CREATE_RENDERER_LIST_PREZ_ICALL_NAME,
            UNITY_HGTREE_CREATE_RENDERER_LIST_PREZ_ICALL_VA,
            0x181080190,
            0x1810806E4,
        ),
    ):
        actual_name, actual_target = resolve_hg_icall(index)
        require(
            f"unity_hgtree_create_renderer_list_{label}_icall_name",
            actual_name,
            expected_name,
            image.path,
        )
        require(
            f"unity_hgtree_create_renderer_list_{label}_icall_target",
            actual_target,
            expected_target,
            image.path,
        )
        renderer_list_variants.append(
            {
                "variant": label,
                "index": index,
                "name": actual_name,
                "targetVirtualAddress": f"0x{actual_target:X}",
                "coreVirtualAddress": f"0x{core:X}",
                "schedulerCallVirtualAddress": f"0x{scheduler_call:X}",
            }
        )

    gpu_driven_renderer_list_variants = []
    for (
        generation,
        variant,
        index,
        expected_name,
        expected_target,
        core,
        job_builder,
        callback,
        record_consumer,
    ) in (
        (
            "V1",
            "default",
            UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_ICALL_INDEX,
            UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_ICALL_NAME,
            UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_ICALL_VA,
            0x1810F0A80,
            0x1810F0E70,
            0x1810E6980,
            0x1810E87E0,
        ),
        (
            "V1",
            "pre_z",
            UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_PREZ_ICALL_INDEX,
            UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_PREZ_ICALL_NAME,
            UNITY_GPU_DRIVEN_V1_CREATE_RENDERER_LIST_PREZ_ICALL_VA,
            0x1810F10D0,
            0x1810F1580,
            0x1810E65F0,
            0x1810E9AD0,
        ),
        (
            "V2",
            "default",
            UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_ICALL_INDEX,
            UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_ICALL_NAME,
            UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_ICALL_VA,
            0x1810FD1B0,
            0x1810FD580,
            0x1810F3970,
            0x1810F58F0,
        ),
        (
            "V2",
            "pre_z",
            UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_PREZ_ICALL_INDEX,
            UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_PREZ_ICALL_NAME,
            UNITY_GPU_DRIVEN_V2_CREATE_RENDERER_LIST_PREZ_ICALL_VA,
            0x1810FD7D0,
            0x1810FDD40,
            0x1810F3560,
            0x1810F6BC0,
        ),
    ):
        actual_name, actual_target = resolve_hg_icall(index)
        require(
            f"unity_gpu_driven_renderer_{generation}_{variant}_icall_name",
            actual_name,
            expected_name,
            image.path,
        )
        require(
            f"unity_gpu_driven_renderer_{generation}_{variant}_icall_target",
            actual_target,
            expected_target,
            image.path,
        )
        gpu_driven_renderer_list_variants.append(
            {
                "generation": generation,
                "variant": variant,
                "index": index,
                "name": actual_name,
                "targetVirtualAddress": f"0x{actual_target:X}",
                "coreVirtualAddress": f"0x{core:X}",
                "jobBuilderVirtualAddress": f"0x{job_builder:X}",
                "callbackVirtualAddress": f"0x{callback:X}",
                "representativeRecordConsumerVirtualAddress": (
                    f"0x{record_consumer:X}"
                ),
            }
        )

    factory_batched_copy_icalls = []
    for label, index, expected_name, expected_target, copy_core, call_site in (
        (
            "current",
            UNITY_FACTORY_CREATE_BATCHED_ENTITIES_ICALL_INDEX,
            UNITY_FACTORY_CREATE_BATCHED_ENTITIES_ICALL_NAME,
            UNITY_FACTORY_CREATE_BATCHED_ENTITIES_ICALL_VA,
            0x1810CE510,
            0x1801EB71A,
        ),
        (
            "obsolete",
            UNITY_FACTORY_CREATE_BATCHED_ENTITIES_OBSOLETE_ICALL_INDEX,
            UNITY_FACTORY_CREATE_BATCHED_ENTITIES_OBSOLETE_ICALL_NAME,
            UNITY_FACTORY_CREATE_BATCHED_ENTITIES_OBSOLETE_ICALL_VA,
            0x1810CEBC0,
            0x1801ECCB5,
        ),
    ):
        actual_name, actual_target = resolve_hg_icall(index)
        require(
            f"unity_factory_create_batched_entities_{label}_icall_name",
            actual_name,
            expected_name,
            image.path,
        )
        require(
            f"unity_factory_create_batched_entities_{label}_icall_target",
            actual_target,
            expected_target,
            image.path,
        )
        factory_batched_copy_icalls.append(
            {
                "variant": label,
                "index": index,
                "name": actual_name,
                "targetVirtualAddress": f"0x{actual_target:X}",
                "copyCoreVirtualAddress": f"0x{copy_core:X}",
                "copyCoreCallVirtualAddress": f"0x{call_site:X}",
            }
        )
    require(
        "unity_hg_resource_load_async_icall_target",
        resource_load_target,
        UNITY_HG_RESOURCE_LOAD_ASYNC_ICALL_VA,
        image.path,
    )
    require(
        "unity_hg_resource_load_async_icall_name",
        resource_load_name,
        UNITY_HG_RESOURCE_LOAD_ASYNC_ICALL_NAME,
        image.path,
    )
    require(
        "unity_hg_resource_get_asset_icall_target",
        resource_get_asset_target,
        UNITY_HG_RESOURCE_GET_ASSET_ICALL_VA,
        image.path,
    )
    require(
        "unity_hg_resource_get_asset_icall_name",
        resource_get_asset_name,
        UNITY_HG_RESOURCE_GET_ASSET_ICALL_NAME,
        image.path,
    )
    require(
        "unity_hg_resource_update_handle_icall_target",
        resource_update_handle_target,
        UNITY_HG_RESOURCE_UPDATE_HANDLE_ICALL_VA,
        image.path,
    )
    require(
        "unity_hg_resource_update_handle_icall_name",
        resource_update_handle_name,
        UNITY_HG_RESOURCE_UPDATE_HANDLE_ICALL_NAME,
        image.path,
    )
    require(
        "unity_hg_geometry_get_handle_icall_target",
        geometry_get_handle_target,
        UNITY_HG_GEOMETRY_GET_HANDLE_ICALL_VA,
        image.path,
    )
    require(
        "unity_hg_geometry_get_handle_icall_name",
        geometry_get_handle_name,
        UNITY_HG_GEOMETRY_GET_HANDLE_ICALL_NAME,
        image.path,
    )
    require(
        "unity_hg_geometry_get_mesh_icall_target",
        geometry_get_mesh_target,
        UNITY_HG_GEOMETRY_GET_MESH_ICALL_VA,
        image.path,
    )
    require(
        "unity_hg_geometry_get_mesh_icall_name",
        geometry_get_mesh_name,
        UNITY_HG_GEOMETRY_GET_MESH_ICALL_NAME,
        image.path,
    )
    register_name, register_target = resolve_hg_icall(
        UNITY_HGTREE_REGISTER_BATCH_GROUP_ICALL_INDEX
    )
    require(
        "unity_hgtree_register_batch_group_icall_target",
        register_target,
        UNITY_HGTREE_REGISTER_BATCH_GROUP_ICALL_VA,
        image.path,
    )
    require(
        "unity_hgtree_register_batch_group_icall_name",
        register_name,
        UNITY_HGTREE_REGISTER_BATCH_GROUP_ICALL_NAME,
        image.path,
    )
    unregister_name, unregister_target = resolve_hg_icall(
        UNITY_HGTREE_UNREGISTER_BATCH_GROUP_ICALL_INDEX
    )
    require(
        "unity_hgtree_unregister_batch_group_icall_target",
        unregister_target,
        UNITY_HGTREE_UNREGISTER_BATCH_GROUP_ICALL_VA,
        image.path,
    )
    require(
        "unity_hgtree_unregister_batch_group_icall_name",
        unregister_name,
        UNITY_HGTREE_UNREGISTER_BATCH_GROUP_ICALL_NAME,
        image.path,
    )
    (
        unregister_with_handle_name,
        unregister_with_handle_target,
    ) = resolve_hg_icall(
        UNITY_HGTREE_UNREGISTER_BATCH_GROUP_WITH_HANDLE_ICALL_INDEX
    )
    require(
        "unity_hgtree_unregister_batch_group_with_handle_icall_target",
        unregister_with_handle_target,
        UNITY_HGTREE_UNREGISTER_BATCH_GROUP_WITH_HANDLE_ICALL_VA,
        image.path,
    )
    require(
        "unity_hgtree_unregister_batch_group_with_handle_icall_name",
        unregister_with_handle_name,
        UNITY_HGTREE_UNREGISTER_BATCH_GROUP_WITH_HANDLE_ICALL_NAME,
        image.path,
    )
    (
        enabled_light_modes_name,
        enabled_light_modes_target,
    ) = resolve_hg_icall(UNITY_FACTORY_SET_ENABLED_LIGHT_MODES_ICALL_INDEX)
    require(
        "unity_hgtree_set_enabled_light_modes_icall_target",
        enabled_light_modes_target,
        UNITY_FACTORY_SET_ENABLED_LIGHT_MODES_ICALL_VA,
        image.path,
    )
    require(
        "unity_hgtree_set_enabled_light_modes_icall_name",
        enabled_light_modes_name,
        UNITY_FACTORY_SET_ENABLED_LIGHT_MODES_ICALL_NAME,
        image.path,
    )

    def resolve_main_icall(index: int) -> tuple[str, int]:
        name_pointer = image.u64(UNITY_ICALL_NAME_TABLE_VA + index * 8)
        target = image.u64(UNITY_ICALL_FUNCTION_TABLE_VA + index * 8)
        return image.cstring(name_pointer), target

    lod_bias_icalls = []
    for label, index, expected_name, expected_target in (
        (
            "parentLODBias.get",
            UNITY_PARENT_LOD_BIAS_GET_ICALL_INDEX,
            UNITY_PARENT_LOD_BIAS_GET_ICALL_NAME,
            UNITY_PARENT_LOD_BIAS_GET_ICALL_VA,
        ),
        (
            "parentLODBias.set",
            UNITY_PARENT_LOD_BIAS_SET_ICALL_INDEX,
            UNITY_PARENT_LOD_BIAS_SET_ICALL_NAME,
            UNITY_PARENT_LOD_BIAS_SET_ICALL_VA,
        ),
        (
            "artTagLODBias.get",
            UNITY_ART_TAG_LOD_BIAS_GET_ICALL_INDEX,
            UNITY_ART_TAG_LOD_BIAS_GET_ICALL_NAME,
            UNITY_ART_TAG_LOD_BIAS_GET_ICALL_VA,
        ),
        (
            "artTagLODBias.set",
            UNITY_ART_TAG_LOD_BIAS_SET_ICALL_INDEX,
            UNITY_ART_TAG_LOD_BIAS_SET_ICALL_NAME,
            UNITY_ART_TAG_LOD_BIAS_SET_ICALL_VA,
        ),
    ):
        actual_name, actual_target = resolve_main_icall(index)
        require(
            f"unity_hgtree_{label}_icall_name",
            actual_name,
            expected_name,
            image.path,
        )
        require(
            f"unity_hgtree_{label}_icall_target",
            actual_target,
            expected_target,
            image.path,
        )
        lod_bias_icalls.append(
            {
                "label": label,
                "index": index,
                "name": actual_name,
                "targetVirtualAddress": f"0x{actual_target:X}",
            }
        )

    lod_streaming_offset_icalls = []
    for label, index, expected_name, expected_target in (
        (
            "artTagLODStreamingOffset.get",
            UNITY_ART_TAG_LOD_STREAMING_OFFSET_GET_ICALL_INDEX,
            UNITY_ART_TAG_LOD_STREAMING_OFFSET_GET_ICALL_NAME,
            UNITY_ART_TAG_LOD_STREAMING_OFFSET_GET_ICALL_VA,
        ),
        (
            "artTagLODStreamingOffset.set",
            UNITY_ART_TAG_LOD_STREAMING_OFFSET_SET_ICALL_INDEX,
            UNITY_ART_TAG_LOD_STREAMING_OFFSET_SET_ICALL_NAME,
            UNITY_ART_TAG_LOD_STREAMING_OFFSET_SET_ICALL_VA,
        ),
    ):
        actual_name, actual_target = resolve_hg_icall(index)
        require(
            f"unity_hgtree_{label}_icall_name",
            actual_name,
            expected_name,
            image.path,
        )
        require(
            f"unity_hgtree_{label}_icall_target",
            actual_target,
            expected_target,
            image.path,
        )
        lod_streaming_offset_icalls.append(
            {
                "label": label,
                "index": index,
                "name": actual_name,
                "targetVirtualAddress": f"0x{actual_target:X}",
            }
        )

    bodies = []
    for label, (virtual_address, size_bytes, expected_hash) in (
        UNITY_HGTREE_BODIES.items()
    ):
        body = image.read(virtual_address, size_bytes)
        actual_hash = hashlib.sha256(body).hexdigest()
        require(
            f"unity_hgtree_{label}_sha256",
            actual_hash,
            expected_hash,
            image.path,
        )
        bodies.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": size_bytes,
                "sha256": actual_hash,
            }
        )

    gpu_driven_bodies = []
    for label, (virtual_address, size_bytes, expected_hash) in (
        UNITY_GPU_DRIVEN_RENDERER_BODIES.items()
    ):
        body = image.read(virtual_address, size_bytes)
        actual_hash = hashlib.sha256(body).hexdigest()
        require(
            f"unity_gpu_driven_renderer_{label}_sha256",
            actual_hash,
            expected_hash,
            image.path,
        )
        gpu_driven_bodies.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": size_bytes,
                "sha256": actual_hash,
            }
        )

    renderer_blob_lookup_call_sites = find_relative_call_sites(
        image, UNITY_RENDERER_BLOB_LOOKUP_VA
    )
    require(
        "unity_hgtree_renderer_blob_lookup_call_sites",
        renderer_blob_lookup_call_sites,
        UNITY_RENDERER_BLOB_LOOKUP_CALL_SITES,
        image.path,
    )
    require(
        "unity_hgtree_renderer_blob_lookup_partition",
        sorted(
            UNITY_RENDERER_BLOB_EXACT_0X7F00_CALL_SITES
            + UNITY_RENDERER_BLOB_NON_0X7F00_CALL_SITES
        ),
        renderer_blob_lookup_call_sites,
        image.path,
    )
    require(
        "unity_hgtree_renderer_blob_exact_cfg_count",
        len(UNITY_RENDERER_BLOB_EXACT_0X7F00_ENTRY_CFGS),
        41,
        image.path,
    )
    require(
        "unity_hgtree_renderer_blob_exact_lookup_call_count",
        len(UNITY_RENDERER_BLOB_EXACT_0X7F00_CALL_SITES),
        44,
        image.path,
    )
    renderer_list_scheduler_call_sites = find_relative_call_sites(
        image, UNITY_RENDERER_LIST_SCHEDULER_VA
    )
    require(
        "unity_hgtree_renderer_list_scheduler_call_sites",
        renderer_list_scheduler_call_sites,
        UNITY_RENDERER_LIST_SCHEDULER_CALL_SITES,
        image.path,
    )
    factory_batched_copy_call_sites = {}
    for copy_core, expected_sites in (
        UNITY_FACTORY_BATCHED_ENTITY_COPY_CALL_SITES.items()
    ):
        actual_sites = find_relative_call_sites(image, copy_core)
        require(
            f"unity_factory_batched_entity_copy_{copy_core:X}_call_sites",
            actual_sites,
            expected_sites,
            image.path,
        )
        factory_batched_copy_call_sites[f"0x{copy_core:X}"] = [
            f"0x{site:X}" for site in actual_sites
        ]

    component67_caller_bodies = []
    for virtual_address, size_bytes, expected_hash in (
        UNITY_COMPONENT67_DIRECT_CALLER_BODIES
    ):
        body = image.read(virtual_address, size_bytes)
        actual_hash = hashlib.sha256(body).hexdigest()
        require(
            f"unity_component67_direct_caller_{virtual_address:X}_sha256",
            actual_hash,
            expected_hash,
            image.path,
        )
        component67_caller_bodies.append(
            {
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": size_bytes,
                "sha256": actual_hash,
            }
        )

    component67_call_sites = {}
    for label, accessor_target in UNITY_COMPONENT67_ACCESSOR_TARGETS.items():
        actual_sites = find_relative_call_sites(image, accessor_target)
        expected_sites = UNITY_COMPONENT67_ACCESSOR_CALL_SITES[label]
        require(
            f"unity_component67_{label}_accessor_call_sites",
            actual_sites,
            expected_sites,
            image.path,
        )
        component67_call_sites[label] = {
            "targetVirtualAddress": f"0x{accessor_target:X}",
            "callSites": [f"0x{site:X}" for site in actual_sites],
        }

    slices = []
    for label, (virtual_address, expected_hex) in UNITY_HGTREE_SLICES.items():
        expected = bytes.fromhex(expected_hex)
        actual = image.read(virtual_address, len(expected))
        require(f"unity_hgtree_{label}", actual, expected, image.path)
        slices.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": len(actual),
                "sha256": hashlib.sha256(actual).hexdigest(),
            }
        )

    float_constants = []
    for label, (virtual_address, expected_bits) in (
        UNITY_HGTREE_FLOAT_CONSTANTS.items()
    ):
        actual_bits = struct.unpack("<I", image.read(virtual_address, 4))[0]
        require(
            f"unity_hgtree_{label}",
            actual_bits,
            expected_bits,
            image.path,
        )
        float_constants.append(
            {
                "label": label,
                "virtualAddress": f"0x{virtual_address:X}",
                "ieee754Bits": f"0x{actual_bits:08X}",
            }
        )

    field_names = []
    for virtual_address, expected_name in UNITY_HGTREE_FIELD_NAMES.items():
        actual_name = image.cstring(virtual_address)
        require(
            "unity_hgtree_field_name",
            actual_name,
            expected_name,
            image.path,
        )
        field_names.append(
            {
                "virtualAddress": f"0x{virtual_address:X}",
                "name": actual_name,
            }
        )

    component_type_strings = {}
    for label, (
        virtual_address,
        expected_value,
    ) in UNITY_HGTREE_COMPONENT_TYPE_STRINGS.items():
        actual_value = image.cstring(virtual_address)
        require(
            f"unity_hgtree_component_{label}",
            actual_value,
            expected_value,
            image.path,
        )
        component_type_strings[label] = {
            "virtualAddress": f"0x{virtual_address:X}",
            "value": actual_value,
        }

    metadata_bytes = metadata if metadata is not None else GLOBAL_METADATA.read_bytes()
    renderer_list_metadata = validate_hgtree_renderer_list_metadata(
        metadata_bytes
    )
    enabled_light_modes_metadata = validate_enabled_light_modes_metadata(
        metadata_bytes
    )
    resource_asset_type_metadata = validate_hg_resource_asset_type_metadata(
        metadata if metadata is not None else GLOBAL_METADATA.read_bytes()
    )
    expected_renderer_entry_pass_names = [
        name
        for name, (_field_index, _token, value) in (
            HG_SHADER_LIGHT_MODE_FIELDS.items()
        )
        if value
    ]
    renderer_entry_pass_names = [
        image.cstring(
            image.u64(UNITY_RENDERER_ENTRY_PASS_NAME_TABLE_VA + index * 8)
        )
        for index in range(len(expected_renderer_entry_pass_names))
    ]
    require(
        "unity_hgtree_renderer_entry_pass_name_table",
        renderer_entry_pass_names,
        expected_renderer_entry_pass_names,
        image.path,
    )
    enabled_light_modes_game_assembly = (
        validate_enabled_light_modes_game_assembly()
    )

    return {
        "internalCall": {
            "table": "dedicated HyperGryph native internal calls",
            "entryCount": UNITY_HG_ICALL_COUNT,
            "nameTableVirtualAddress": f"0x{UNITY_HG_ICALL_NAME_TABLE_VA:X}",
            "functionTableVirtualAddress": (
                f"0x{UNITY_HG_ICALL_FUNCTION_TABLE_VA:X}"
            ),
            "nameTableSha256": UNITY_HG_ICALL_NAME_TABLE_SHA256,
            "functionTableSha256": UNITY_HG_ICALL_FUNCTION_TABLE_SHA256,
            "index": UNITY_HGTREE_CREATE_RENDERER_LIST_ICALL_INDEX,
            "name": name,
            "targetVirtualAddress": f"0x{target:X}",
            "managedParameters": [
                "viewHandle",
                "renderFlagsMask",
                "renderFlagsValue",
                "lightModeMask",
                "context",
                "drawableFeedbackPtr",
                "noAlphaTest",
            ],
        },
        "rendererListVariants": {
            "entries": renderer_list_variants,
            "managedContract": renderer_list_metadata,
            "sharedSchedulerVirtualAddress": (
                f"0x{UNITY_RENDERER_LIST_SCHEDULER_VA:X}"
            ),
            "allSchedulerCallSites": [
                f"0x{site:X}" for site in renderer_list_scheduler_call_sites
            ],
            "allHGTreeVariantsReachSharedScheduler": True,
            "selectedCallbacks": ["0x181067A70", "0x181064190"],
            "enabledLightModesBoundary": (
                "default, child-view, and PreZ entry points converge on the "
                "same scheduler and therefore do not expose a separate "
                "uninspected callback family for runtime record+0x14"
            ),
            "renderFlagsFilterAbi": {
                "bindingVirtualAddress": "0x1801D9D10",
                "coreVirtualAddress": "0x18107EE40",
                "schedulerVirtualAddress": "0x181080730",
                "callbackDescriptorBiasBytes": 4,
                "descriptorRenderFlagsMaskOffset": "0x40",
                "descriptorRenderFlagsValueOffset": "0x44",
                "descriptorLightModeMaskOffset": "0x48",
                "callbackRenderFlagsMaskOffset": "0x3C",
                "callbackRenderFlagsValueOffset": "0x40",
                "callbackLightModeMaskOffset": "0x44",
                "consumerVirtualAddress": "0x181064B73",
                "equation": (
                    "((shadowProxyGeometryHandle | rendererEntryFlags) & "
                    "renderFlagsMask) == renderFlagsValue"
                ),
                "interpretation": (
                    "record+0x0C is not a standalone filter bitfield: the "
                    "CreateRendererList ABI intentionally folds the shadow-"
                    "proxy GeometryHandle into the HGTree renderFlags "
                    "mask/value comparison"
                ),
            },
        },
        "gpuDrivenRendererList": {
            "entries": gpu_driven_renderer_list_variants,
            "descriptorSizeBytes": 0xA0,
            "requestLightModeMaskOffset": "0x54",
            "rendererFamilyMask": "0x7F00",
            "rendererPassMask": "0x60000",
            "recordStrideBytes": 24,
            "enabledLightModesRecordOffset": "0x14",
            "enabledLightModesReadObserved": True,
            "representativeReadSites": [
                {
                    "generation": "V1",
                    "variant": "default",
                    "recordBaseVirtualAddress": "0x1810E8C2F",
                    "readVirtualAddress": "0x1810E8E73",
                    "strideVirtualAddress": "0x1810E913C",
                },
                {
                    "generation": "V1",
                    "variant": "pre_z",
                    "recordBaseVirtualAddress": "0x1810E9FCA",
                    "readVirtualAddress": "0x1810EA245",
                    "strideVirtualAddress": "0x1810EA7BC",
                },
                {
                    "generation": "V2",
                    "variant": "default",
                    "recordBaseVirtualAddress": "0x1810F5D46",
                    "readVirtualAddress": "0x1810F5F7F",
                    "strideVirtualAddress": "0x1810F624B",
                },
                {
                    "generation": "V2",
                    "variant": "pre_z",
                    "recordBaseVirtualAddress": "0x1810F70D9",
                    "readVirtualAddress": "0x1810F7356",
                    "strideVirtualAddress": "0x1810F788A",
                },
            ],
            "filterEquation": (
                "combinedFlags = record[+0x14] | candidatePass[+0x18] | "
                "callbackDerivedFlags; "
                "(combinedFlags & job[+0x48]) == job[+0x4C]"
            ),
            "requestEquation": (
                "candidatePass[+0x1C] & job[+0x54] != 0"
            ),
            "interpretation": (
                "all four GPUDrivenRenderer V1/V2 default/PreZ routes "
                "carry the requested light-mode mask into job+0x54, select "
                "the 0x7F00 renderer ECS column, and read each 0x18-byte "
                "record's enabledLightModes word at +0x14. The record word "
                "participates in the combined render-feature filter at "
                "job+0x48/+0x4C, while the requested light-mode mask is "
                "tested separately against candidatePass+0x1C."
            ),
            "verifiedBodies": gpu_driven_bodies,
        },
        "registrationInternalCall": {
            "index": UNITY_HGTREE_REGISTER_BATCH_GROUP_ICALL_INDEX,
            "name": register_name,
            "targetVirtualAddress": f"0x{register_target:X}",
        },
        "resourceLoadInternalCall": {
            "index": UNITY_HG_RESOURCE_LOAD_ASYNC_ICALL_INDEX,
            "name": resource_load_name,
            "targetVirtualAddress": f"0x{resource_load_target:X}",
            "acquireCoreVirtualAddress": "0x180FBFC60",
            "lookupVirtualAddress": "0x1801F7410",
            "managedContract": resource_asset_type_metadata,
        },
        "resourceHandleInternalCalls": {
            "getAsset": {
                "index": UNITY_HG_RESOURCE_GET_ASSET_ICALL_INDEX,
                "name": resource_get_asset_name,
                "targetVirtualAddress": f"0x{resource_get_asset_target:X}",
                "assetInstanceIdSlotOffset": "0x18",
            },
            "updateAssetHandle": {
                "index": UNITY_HG_RESOURCE_UPDATE_HANDLE_ICALL_INDEX,
                "name": resource_update_handle_name,
                "targetVirtualAddress": f"0x{resource_update_handle_target:X}",
                "stateSlotOffset": "0x10",
                "assetInstanceIdSlotOffset": "0x18",
            },
        },
        "geometrySystemInternalCalls": {
            "getGeometryHandle": {
                "index": UNITY_HG_GEOMETRY_GET_HANDLE_ICALL_INDEX,
                "name": geometry_get_handle_name,
                "targetVirtualAddress": f"0x{geometry_get_handle_target:X}",
                "input": "Mesh Unity instance ID",
                "output": "UInt32 GeometryHandle",
            },
            "getMesh": {
                "index": UNITY_HG_GEOMETRY_GET_MESH_ICALL_INDEX,
                "name": geometry_get_mesh_name,
                "targetVirtualAddress": f"0x{geometry_get_mesh_target:X}",
                "input": "UInt32 GeometryHandle",
                "output": "Mesh Unity object",
            },
            "handleEncoding": {
                "indexBits": "0..23",
                "generationBits": "24..31",
                "indexMask": "0x00FFFFFF",
                "slotGenerationOffset": "0x06",
                "slotStrideBytes": 56,
                "equation": (
                    "GeometryHandle = ((slotGeneration + 1) & 0xFF) << 24 "
                    "| slotIndex"
                ),
                "builderVirtualAddress": "0x18108B1C0",
                "encodingVirtualAddress": "0x18108B51E",
            },
            "lifecycle": {
                "instanceMapOffset": "singleton+0xA0",
                "instanceMapEntryStrideBytes": 12,
                "instanceMapKey": "Mesh Unity instance ID",
                "instanceMapValue": "UInt32 GeometryHandle",
                "insertVirtualAddress": "0x1810941F0",
                "removeVirtualAddress": "0x181099980",
                "meshRegistrationCallVirtualAddress": "0x181372836",
                "meshUnregistrationCallVirtualAddress": "0x1813773D6",
            },
        },
        "unregistrationInternalCalls": [
            {
                "index": UNITY_HGTREE_UNREGISTER_BATCH_GROUP_ICALL_INDEX,
                "name": unregister_name,
                "targetVirtualAddress": f"0x{unregister_target:X}",
                "coreVirtualAddress": "0x181087D30",
            },
            {
                "index": (
                    UNITY_HGTREE_UNREGISTER_BATCH_GROUP_WITH_HANDLE_ICALL_INDEX
                ),
                "name": unregister_with_handle_name,
                "targetVirtualAddress": (
                    f"0x{unregister_with_handle_target:X}"
                ),
                "coreVirtualAddress": "0x181087E00",
            },
        ],
        "enabledLightModesInternalCall": {
            "index": UNITY_FACTORY_SET_ENABLED_LIGHT_MODES_ICALL_INDEX,
            "name": enabled_light_modes_name,
            "targetVirtualAddress": f"0x{enabled_light_modes_target:X}",
            "writerCoreVirtualAddress": "0x1810D9110",
            "managedContract": enabled_light_modes_metadata,
            "gameAssemblyContract": enabled_light_modes_game_assembly,
        },
        "factoryBatchedEntityCopyInternalCalls": {
            "entries": factory_batched_copy_icalls,
            "copyCoreCallSites": factory_batched_copy_call_sites,
            "interpretation": (
                "both current and obsolete CreateBatchedEntities routes "
                "invoke the same complete renderer-blob copy helper through "
                "parallel hash-pinned copy cores"
            ),
        },
        "lodControlInternalCalls": {
            "cullingSystem": lod_bias_icalls,
            "lodStreamingSystem": lod_streaming_offset_icalls,
        },
        "callChain": [
            "HGTreeRender CreateRendererList variants at indices 564/565/566",
            "cores 0x18107EE40/0x18107FCF0/0x181080190",
            "0x181080730 runtime job descriptor/scheduler",
            "0x181067A70 or 0x181064190 scheduled batch job",
        ],
        "registrationChain": [
            "0x1801DA040 HGTreeRender::RegisterTreeBatchGroup binding",
            "managed object-handle extraction",
            "0x181086050 runtime batch-group registration core",
        ],
        "unregistrationChain": [
            "0x1810BCE00 loader/runtime-transform owner cleanup",
            "owner vector pointer@+0x78 with element count@+0x88",
            "blob count@+0x00; records@+0x04 stride 0x18",
            "record handle word@+0x02 and batchKey dword@+0x04",
            "0x181087E00 UnregisterTreeBatchGroupWithHandle core",
            "0x1801DA330 public binding at dedicated HG table index 569",
        ],
        "runtimeJobs": {
            "callbacks": ["0x181067A70", "0x181064190"],
            "serializedRecordStrideObservedInPinnedJobSlices": False,
            "runtimeRecordStrideObserved": "0x18",
            "boundary": (
                "the scheduled callbacks consume transformed runtime batch/SoA "
                "data; their 0x18 record stride and positional offsets are not "
                "the serialized HGTreeRenderer +0x18 LOD field"
            ),
        },
        "runtimeTransform": {
            "functionVirtualAddress": "0x1810C5F30",
            "directCallerVirtualAddress": "0x1810C9610",
            "directCallSiteVirtualAddress": "0x1810C9683",
            "structureIdentity": (
                "loader-owned registration blob; distinct from the 24-byte "
                "ECS LOD state component"
            ),
            "sourceRecord": {
                "strideBytes": 28,
                "fieldsConsumed": [
                    {
                        "source": "batchKey@+0x00",
                        "destination": "runtimeRecord@+0x04",
                        "registrationArgument": True,
                    },
                    {
                        "source": "renderFlags@+0x04",
                        "destination": "runtimeRecord@+0x08",
                    },
                    {
                        "source": "mesh PPtr@+0x08",
                        "destination": "RegisterTreeBatchGroup argument r9d",
                    },
                    {
                        "source": "material PPtr@+0x0C",
                        "destination": "RegisterTreeBatchGroup argument r8d",
                    },
                    {
                        "source": "subMeshIndex word@+0x10",
                        "destination": "RegisterTreeBatchGroup stack argument",
                    },
                    {
                        "source": "lodScreenSizeMaxSquared@+0x14",
                        "destination": "lodFloat2[index].x",
                    },
                    {
                        "source": "lodScreenSizeMinSquared@+0x18",
                        "destination": "lodFloat2[index].y",
                    },
                ],
            },
            "outputLayout": {
                "countOffset": "0x00",
                "runtimeRecordBaseOffset": "0x04",
                "runtimeRecordStrideBytes": 24,
                "capacityBuckets": [1, 2, 4, 8, 16, 32],
                "lodArrayOffsetEquation": "4 + 24 * capacity",
                "lodArrayOffsets": [
                    "0x1C",
                    "0x34",
                    "0x64",
                    "0xC4",
                    "0x184",
                    "0x304",
                ],
                "lodFloat2StrideBytes": 8,
                "runtimeRecordInitialFields": [
                    {"offset": "0x00", "sizeBytes": 2, "initialValue": 0},
                    {
                        "offset": "0x02",
                        "sizeBytes": 2,
                        "value": "RegisterTreeBatchGroup 16-bit return handle",
                    },
                    {
                        "offset": "0x04",
                        "sizeBytes": 4,
                        "source": "batchKey or mapped m_Materials instance ID",
                    },
                    {
                        "offset": "0x08",
                        "sizeBytes": 4,
                        "source": "renderFlags or mapped m_Meshes instance ID",
                    },
                    {
                        "offset": "0x0C",
                        "sizeBytes": 4,
                        "initialValue": 0,
                        "meaning": (
                            "m_ShadowProxyMeshes UInt32 GeometryHandle"
                        ),
                    },
                    {
                        "offset": "0x10",
                        "sizeBytes": 4,
                        "initialValue": 0,
                        "meaning": "renderer property flags",
                    },
                    {
                        "offset": "0x14",
                        "sizeBytes": 4,
                        "initialValue": 0,
                        "meaning": "enabledLightModes",
                    },
                ],
                "hgmeshRendererDataResourceMapping": {
                    "producerClosed": True,
                    "serializedFieldFunctionVirtualAddress": "0x1810A9120",
                    "runtimeInitializerVirtualAddress": "0x181088D80",
                    "runtimeBlobHeaderBytes": 4,
                    "runtimeRecordStrideBytes": 24,
                    "singletonVirtualAddress": "0x180FC5E60",
                    "maps": {
                        "materialInstanceIdToWord": "singleton+0x90",
                        "meshInstanceIdToGeometryHandle": "singleton+0xA0",
                    },
                    "serializedFields": [
                        {
                            "name": "m_Materials",
                            "nativeOffset": "0x58",
                            "map": "materialInstanceIdToWord",
                            "blobWriteOffset": "0x08",
                            "recordWriteOffset": "0x04",
                            "directWriteVirtualAddress": "0x181088F75",
                            "availabilityWriteVirtualAddresses": [
                                "0x1811579B1",
                                "0x181159190",
                            ],
                            "cleanupWriteVirtualAddress": "0x18115C0D7",
                        },
                        {
                            "name": "m_Meshes",
                            "nativeOffset": "0x78",
                            "map": "meshInstanceIdToGeometryHandle",
                            "blobWriteOffset": "0x0C",
                            "recordWriteOffset": "0x08",
                            "directWriteVirtualAddress": "0x181088FEF",
                            "availabilityWriteVirtualAddresses": [
                                "0x181157A42",
                                "0x181159218",
                            ],
                            "cleanupWriteVirtualAddress": "0x18115C0F3",
                        },
                        {
                            "name": "m_ShadowProxyMeshes",
                            "nativeOffset": "0x98",
                            "map": "meshInstanceIdToGeometryHandle",
                            "blobWriteOffset": "0x10",
                            "recordWriteOffset": "0x0C",
                            "directWriteVirtualAddress": "0x18108906A",
                            "availabilityWriteVirtualAddresses": [
                                "0x181157AD1",
                                "0x1811592A0",
                            ],
                            "cleanupWriteVirtualAddress": "0x18115C110",
                        },
                    ],
                    "excludedField": {
                        "name": "m_ColliderMeshes",
                        "nativeOffset": "0xD8",
                        "rendererBlobWriteObserved": False,
                    },
                    "proof": (
                        "the hash-pinned HGMeshRendererData serializer binds "
                        "m_Materials/m_Meshes/m_ShadowProxyMeshes to native "
                        "+0x58/+0x78/+0x98. The independent resource "
                        "initializer resolves those arrays through singleton "
                        "Material and Mesh-instance-ID-to-GeometryHandle maps "
                        "at +0x90/+0xA0 and "
                        "writes blob+0x08/+0x0C/+0x10. Because runtime records "
                        "begin at blob+0x04, the true record destinations are "
                        "+0x04/+0x08/+0x0C. The availability writers and "
                        "cleanup use the same three blob offsets and order."
                    ),
                },
                "runtimeRecordFieldLifecycle": {
                    "materialMapWordAt0x04": {
                        "resourceSourceClosed": True,
                        "resourceField": "m_Materials",
                        "resourceFieldNativeOffset": "0x58",
                        "directWriterVirtualAddress": "0x181088F75",
                        "availabilityWriterVirtualAddresses": [
                            "0x1811579B1",
                            "0x181159190",
                        ],
                        "cleanupWriteVirtualAddress": "0x18115C0D7",
                    },
                    "mutableRenderFlagsAt0x08": {
                        "roleClosed": True,
                        "initialSource": "serialized HGTreeRenderer.renderFlags",
                        "hgmeshResourceSource": "m_Meshes GeometryHandle",
                        "hgmeshResourceFieldNativeOffset": "0x78",
                        "hgmeshDirectWriterVirtualAddress": "0x181088FEF",
                        "hgmeshAvailabilityWriterVirtualAddresses": [
                            "0x181157A42",
                            "0x181159218",
                        ],
                        "hgmeshCleanupWriteVirtualAddress": "0x18115C0F3",
                        "particleWriterVirtualAddresses": [
                            "0x1810416A0",
                            "0x181041870",
                            "0x181041920",
                            "0x1810419D0",
                        ],
                        "particleModes": [2, 3, 4, 5],
                        "writtenValue": "0x00100000",
                        "consumerVirtualAddress": "0x181067FFF",
                        "consumerEquation": (
                            "record[+0x08] | rendererEntry[+0x18] "
                            "| callbackDerivedFlags"
                        ),
                        "proof": (
                            "all four particle setup variants select the same "
                            "0x7F00 renderer-component family, advance from "
                            "blob+0x0C (record+0x08), write bit 20 at stride "
                            "0x18, and select modes 2..5; a scheduled callback "
                            "ORs record+0x08 into its render flags"
                        ),
                    },
                    "shadowProxyGeometryHandleAt0x0C": {
                        "consumerRoleClosed": True,
                        "producerClosed": True,
                        "engineIdentityClosed": True,
                        "handleEncodingClosed": True,
                        "assetClassClosed": True,
                        "assetHandleContractClosed": True,
                        "assetType": "UnityEngine.HyperGryph.AssetType.Mesh",
                        "assetTypeValue": 2,
                        "resourceField": "m_ShadowProxyMeshes",
                        "resourceFieldNativeOffset": "0x98",
                        "directResourceWriterVirtualAddress": "0x18108906A",
                        "engineType": "UInt32 GeometryHandle",
                        "getGeometryHandleInternalCallIndex": (
                            UNITY_HG_GEOMETRY_GET_HANDLE_ICALL_INDEX
                        ),
                        "getGeometryHandleInternalCallName": (
                            geometry_get_handle_name
                        ),
                        "getMeshInternalCallIndex": (
                            UNITY_HG_GEOMETRY_GET_MESH_ICALL_INDEX
                        ),
                        "getMeshInternalCallName": geometry_get_mesh_name,
                        "handleIndexMask": "0x00FFFFFF",
                        "handleIndexBits": "0..23",
                        "handleGenerationBits": "24..31",
                        "handleSlotGenerationOffset": "0x06",
                        "handleSlotStrideBytes": 56,
                        "initialValue": 0,
                        "acquisitionPaths": [
                            {
                                "ownerType": "MergedRenderCollider",
                                "transitionFunctionVirtualAddress": "0x181153310",
                                "sourcePointerReadVirtualAddress": "0x1811535FE",
                                "acquireCallVirtualAddress": "0x181153619",
                                "ownerHandleWriteVirtualAddress": "0x181153621",
                                "ownerHandleOffset": "0x18",
                                "assetTypeImmediate": 2,
                            },
                            {
                                "ownerType": "Render",
                                "transitionFunctionVirtualAddress": "0x181154230",
                                "sourcePointerReadVirtualAddress": "0x1811547CE",
                                "acquireCallVirtualAddress": "0x1811547E9",
                                "ownerHandleWriteVirtualAddress": "0x1811547F1",
                                "ownerHandleOffset": "0x18",
                                "assetTypeImmediate": 2,
                            },
                        ],
                        "writerPaths": [
                            {
                                "functionVirtualAddress": "0x181157760",
                                "writeVirtualAddress": "0x181157AD1",
                            },
                            {
                                "functionVirtualAddress": "0x181159010",
                                "writeVirtualAddress": "0x1811592A0",
                            },
                        ],
                        "cleanupVirtualAddress": "0x18115BFC0",
                        "cleanupWriteVirtualAddress": "0x18115C110",
                        "releaseCoreVirtualAddress": "0x180FBF6B0",
                        "loadAsyncInternalCallIndex": (
                            UNITY_HG_RESOURCE_LOAD_ASYNC_ICALL_INDEX
                        ),
                        "loadAsyncInternalCallName": resource_load_name,
                        "loadAsyncBindingVirtualAddress": (
                            f"0x{resource_load_target:X}"
                        ),
                        "acquireCoreVirtualAddress": "0x180FBFC60",
                        "lookupVirtualAddress": "0x1801F7410",
                        "updateHandleInternalCallIndex": (
                            UNITY_HG_RESOURCE_UPDATE_HANDLE_ICALL_INDEX
                        ),
                        "updateHandleInternalCallName": resource_update_handle_name,
                        "getAssetInternalCallIndex": (
                            UNITY_HG_RESOURCE_GET_ASSET_ICALL_INDEX
                        ),
                        "getAssetInternalCallName": resource_get_asset_name,
                        "handleSlotStrideBytes": 32,
                        "handleStateOffset": "0x10",
                        "handleAssetInstanceIdOffset": "0x18",
                        "mappingEntryStrideBytes": 12,
                        "mappingKey": "Unity asset instance ID",
                        "mappingValueOffset": "0x08",
                        "recordStrideBytes": 24,
                        "consumerVirtualAddress": "0x181064B73",
                        "consumerEquation": (
                            "(record[+0x0C] | rendererEntry[+0x18]) "
                            "& filterMask == filterValue"
                        ),
                        "proof": (
                            "both owner transition callbacks acquire their "
                            "third renderer resource with native kind 2; the "
                            "dedicated HyperGryph internal-call table maps the "
                            "same acquire wrapper to HGResourceManager::"
                            "LoadAsync_Injected, whose IL2CPP type parameter is "
                            "the installed AssetType enum with value 2=Mesh. "
                            "UpdateAssetHandle writes readiness to each 32-byte "
                            "handle slot at +0x10 and a Unity asset instance ID "
                            "at +0x18; GetAsset consumes that same +0x18 word as "
                            "an object-registry key. Both LOD availability "
                            "initializers gate on ready==1, resolve the third "
                            "Mesh slot's instance ID through a separate 12-byte "
                            "entry map, and write entry+0x08 to record+0x0C. "
                            "HGGeometrySystem internal-call entries 300/301 "
                            "name the map value GeometryHandle and provide the "
                            "forward instance-ID lookup and reverse GetMesh "
                            "route. Its builder packs the low 24-bit slot index "
                            "with the incremented 8-bit slot generation in bits "
                            "24..31. The independent HGMeshRendererData initializer "
                            "names the source field m_ShadowProxyMeshes and "
                            "writes the same mapped word to record+0x0C. "
                            "Cleanup releases owner handle +0x18 and clears "
                            "record+0x0C; the scheduled callback consumes the "
                            "resolved word directly as its masked supplemental "
                            "filter overlay"
                        ),
                        "proofBoundary": (
                            "asset class, handle/index separation, instance-ID "
                            "production, GeometryHandle identity and packing, "
                            "mapped-value resolution, release, and masked "
                            "consumption and the CreateRendererList renderFlags "
                            "mask/value ABI are closed; the concrete per-pass "
                            "callers and values supplied to that ABI remain open"
                        ),
                    },
                    "rendererPropertyFlagsAt0x10": {
                        "roleClosed": True,
                        "initialValue": 0,
                        "resourceInitializerSeedObserved": False,
                        "writerVirtualAddress": "0x180432CD0",
                        "writerLoopVirtualAddress": "0x180432DD0",
                        "preserveMask": "0xFC07FBFD",
                        "recordStrideBytes": 24,
                        "proof": (
                            "record+0x10 is blob+0x14, beyond all three "
                            "resource-map writes. The Renderer state "
                            "synchronizer selects the same "
                            "0x7F00 family, advances from blob+0x14 "
                            "(record+0x10), preserves the masked bits, and ORs "
                            "property-derived flags into every record"
                        ),
                    },
                    "enabledLightModesAt0x14": {
                        "roleClosed": True,
                        "downstreamConsumerClosed": True,
                        "passBitMeaningsClosed": True,
                        "nativeInitializationProducerClosed": True,
                        "hgtreeInitialValue": 0,
                        "rendererObjectFieldOffset": "0x250",
                        "rendererObjectDefault": "0xFFFFFFFF",
                        "internalCallIndex": (
                            UNITY_FACTORY_SET_ENABLED_LIGHT_MODES_ICALL_INDEX
                        ),
                        "internalCallName": enabled_light_modes_name,
                        "bindingVirtualAddress": "0x1801EB940",
                        "writerCoreVirtualAddress": "0x1810D9110",
                        "writerLoopVirtualAddress": "0x1810D9153",
                        "recordStrideBytes": 24,
                        "genericConstructorVirtualAddress": "0x180BCB760",
                        "genericConstructorSource": "constructor input +0x20",
                        "nativeInitializationPaths": [
                            {
                                "builderVirtualAddress": "0x18042A130",
                                "readVirtualAddress": "0x18042AAC6",
                                "writeVirtualAddress": "0x18042AACC",
                                "equation": (
                                    "record[+0x14] = renderer[+0x250]"
                                ),
                            },
                            {
                                "builderVirtualAddress": "0x18042AB50",
                                "readVirtualAddress": "0x18042B4D6",
                                "writeVirtualAddress": "0x18042B4DC",
                                "equation": (
                                    "record[+0x14] = renderer[+0x250]"
                                ),
                            },
                            {
                                "inputBuilderVirtualAddress": "0x180BCCB60",
                                "sourceReadVirtualAddress": "0x180BCCD7E",
                                "constructorVirtualAddress": "0x180BCB760",
                                "recordWriteVirtualAddress": "0x180BCBE8A",
                                "equation": (
                                    "constructorInput[+0x20] = "
                                    "renderer[+0x250]; "
                                    "record[+0x14] = constructorInput[+0x20]"
                                ),
                            },
                        ],
                        "downstreamSearchBoundary": {
                            "requestMaskJobOffset": "0x44",
                            "hgtreeRequestMaskJobOffset": "0x44",
                            "gpuDrivenRequestMaskJobOffset": "0x54",
                            "callbackAddresses": [
                                "0x181067A70",
                                "0x181064190",
                            ],
                            "testedRendererEntryOffset": "0x1C",
                            "projectionHypothesisRetracted": True,
                            "distinctMaskRoleClosed": True,
                            "rendererEntryMask": {
                                "meaning": "shader-supported light modes",
                                "entryStrideBytes": 96,
                                "fieldOffset": "0x1C",
                                "builderVirtualAddresses": [
                                    "0x18109BE90",
                                    "0x18109C9D0",
                                ],
                                "passNameTableVirtualAddress": (
                                    f"0x{UNITY_RENDERER_ENTRY_PASS_NAME_TABLE_VA:X}"
                                ),
                                "passNames": renderer_entry_pass_names,
                                "equation": (
                                    "entry[+0x1C] starts at zero; for each "
                                    "HGShaderLightMode bit 0..30, query the "
                                    "renderer material/shader for the matching "
                                    "pass name and set that bit when supported"
                                ),
                            },
                            "interpretation": (
                                "both inspected renderer-list callbacks test "
                                "the requested lightModeMask stored at job+0x44 "
                                "against a separate 0x60-stride renderer-entry "
                                "word at +0x1C. Two hash-pinned entry builders "
                                "independently derive that word from the "
                                "renderer material/shader's supported pass "
                                "names, so it is not a projection of runtime "
                                "record+0x14"
                            ),
                            "runtimeRecordPointerBoundary": {
                                "exactLookupVirtualAddress": (
                                    f"0x{UNITY_RENDERER_BLOB_LOOKUP_VA:X}"
                                ),
                                "familyMask": "0x00007F00",
                                "recordStrideBytes": 24,
                                "allDirectLookupCallCount": len(
                                    renderer_blob_lookup_call_sites
                                ),
                                "exactFamilyLookupCallCount": len(
                                    UNITY_RENDERER_BLOB_EXACT_0X7F00_CALL_SITES
                                ),
                                "exactFamilyEntryCfgCount": len(
                                    UNITY_RENDERER_BLOB_EXACT_0X7F00_ENTRY_CFGS
                                ),
                                "nonFamilyLookupCallCount": len(
                                    UNITY_RENDERER_BLOB_NON_0X7F00_CALL_SITES
                                ),
                                "exactFamilyLookupCallSites": [
                                    f"0x{site:X}"
                                    for site in (
                                        UNITY_RENDERER_BLOB_EXACT_0X7F00_CALL_SITES
                                    )
                                ],
                                "exactFamilyEntryCfgs": [
                                    f"0x{entry:X}"
                                    for entry in (
                                        UNITY_RENDERER_BLOB_EXACT_0X7F00_ENTRY_CFGS
                                    )
                                ],
                                "hotColdCfgTraversal": {
                                    "enabled": True,
                                    "windowBytesPerEntry": 0x20000,
                                    "directControlFlowFollowed": True,
                                    "stackSlotOverlapInvalidation": True,
                                    "memoryOperandWidthOverlapChecked": True,
                                    "recordBaseNonStackMemoryStoreSites": [],
                                    "recordBaseReturnSites": [],
                                    "enabledLightModesReadSites": [],
                                    "boundedControlFlowEscape": {
                                        "virtualAddress": "0x1810CE3BE",
                                        "targetVirtualAddress": "0x181C9F9A0",
                                        "role": (
                                            "tail memcpy of one complete exact-"
                                            "family renderer blob into another"
                                        ),
                                    },
                                },
                                "stackPointerBoundary": {
                                    "blobHeaderStoreCount": 4,
                                    "recordBaseStoreCount": 3,
                                    "addressTakenSites": [],
                                    "stores": [
                                        {
                                            "storeVirtualAddress": (
                                                "0x180BCBEE4"
                                            ),
                                            "pointerOffset": "blob+0x00",
                                            "reloadVirtualAddresses": [
                                                "0x180BCBF7F"
                                            ],
                                        },
                                        {
                                            "storeVirtualAddress": (
                                                "0x1810CF426"
                                            ),
                                            "pointerOffset": "blob+0x00",
                                            "reloadVirtualAddresses": [],
                                        },
                                        {
                                            "storeVirtualAddress": (
                                                "0x1810D07D8"
                                            ),
                                            "pointerOffset": "blob+0x00",
                                            "reloadVirtualAddresses": [],
                                        },
                                        {
                                            "storeVirtualAddress": (
                                                "0x181129F0E"
                                            ),
                                            "pointerOffset": "blob+0x04",
                                            "reloadVirtualAddresses": [
                                                "0x18112A027",
                                                "0x18112A10C",
                                                "0x18112A243",
                                            ],
                                        },
                                        {
                                            "storeVirtualAddress": (
                                                "0x18112A886"
                                            ),
                                            "pointerOffset": "blob+0x04",
                                            "reloadVirtualAddresses": [
                                                "0x18112AADB",
                                                "0x18112AC65",
                                            ],
                                            "slotLaterPartiallyOverwritten": (
                                                True
                                            ),
                                        },
                                        {
                                            "storeVirtualAddress": (
                                                "0x18113788B"
                                            ),
                                            "pointerOffset": "blob+0x04",
                                            "reloadVirtualAddresses": [
                                                "0x181137913",
                                                "0x1811379F7",
                                                "0x181137B6A",
                                                "0x181137C6D",
                                            ],
                                        },
                                        {
                                            "storeVirtualAddress": (
                                                "0x1811577D6"
                                            ),
                                            "pointerOffset": "blob+0x00",
                                            "reloadVirtualAddresses": [
                                                "0x1811578F4",
                                                "0x181157F2B",
                                            ],
                                        },
                                    ],
                                    "interpretation": (
                                        "all exact-family result pointers "
                                        "written to stack are local spills or "
                                        "slot reuse; no stored pointer slot is "
                                        "address-taken as a nested job or "
                                        "descriptor payload"
                                    ),
                                },
                                "fullBlobCopy": {
                                    "functionVirtualAddress": "0x1810CE280",
                                    "sourceLookupCallVirtualAddress": (
                                        "0x1810CE37D"
                                    ),
                                    "destinationLookupCallVirtualAddress": (
                                        "0x1810CE38E"
                                    ),
                                    "tailMemcpyVirtualAddress": "0x1810CE3BE",
                                    "memcpyVirtualAddress": "0x181C9F9A0",
                                    "byteCountEquation": (
                                        "4 + 32 * (familyMask >> 8)"
                                    ),
                                    "layoutEquation": (
                                        "4-byte count + 24*capacity runtime "
                                        "records + 8*capacity LOD float2 pairs"
                                    ),
                                    "enabledLightModesBehavior": (
                                        "record+0x14 is copied verbatim but not "
                                        "read or interpreted"
                                    ),
                                    "factoryCreateBatchedEntityRoutes": [
                                        {
                                            "internalCallIndex": (
                                                UNITY_FACTORY_CREATE_BATCHED_ENTITIES_ICALL_INDEX
                                            ),
                                            "internalCallName": (
                                                UNITY_FACTORY_CREATE_BATCHED_ENTITIES_ICALL_NAME
                                            ),
                                            "copyCoreVirtualAddress": (
                                                "0x1810CE510"
                                            ),
                                            "copyHelperCallVirtualAddress": (
                                                "0x1810CE853"
                                            ),
                                        },
                                        {
                                            "internalCallIndex": (
                                                UNITY_FACTORY_CREATE_BATCHED_ENTITIES_OBSOLETE_ICALL_INDEX
                                            ),
                                            "internalCallName": (
                                                UNITY_FACTORY_CREATE_BATCHED_ENTITIES_OBSOLETE_ICALL_NAME
                                            ),
                                            "copyCoreVirtualAddress": (
                                                "0x1810CEBC0"
                                            ),
                                            "copyHelperCallVirtualAddress": (
                                                "0x1810CEF03"
                                            ),
                                        },
                                    ],
                                },
                                "consumerFunctions": [
                                    "0x181129E0D",
                                    "0x18112A790",
                                    "0x18113781A",
                                ],
                                "directConsumerRecordReads": [
                                    {
                                        "functionVirtualAddress": (
                                            "0x181129E0D"
                                        ),
                                        "recordOffsets": [
                                            "0x00",
                                            "0x04",
                                            "0x08",
                                        ],
                                    },
                                    {
                                        "functionVirtualAddress": (
                                            "0x18112A790"
                                        ),
                                        "role": (
                                            "component-K / ray-tracing-K "
                                            "record grouping"
                                        ),
                                        "recordOffsets": [
                                            "0x00",
                                            "0x04",
                                            "0x08",
                                            "0x10",
                                        ],
                                        "assertionStrings": [
                                            "componentMaskForK is one bit",
                                            (
                                                "componentMaskForRayTracingK "
                                                "is one bit"
                                            ),
                                        ],
                                    },
                                    {
                                        "functionVirtualAddress": (
                                            "0x18113781A"
                                        ),
                                        "recordOffsets": [
                                            "0x00",
                                            "0x04",
                                            "0x08",
                                        ],
                                    },
                                ],
                                "recordBaseZeroInitializationCallSites": [
                                    "0x18042A497",
                                    "0x18042AEAD",
                                    "0x180BCBAEC",
                                ],
                                "zeroInitializerVirtualAddress": (
                                    "0x181CA0040"
                                ),
                                "recordBaseEscapeCallSites": [
                                    "0x18112A25A",
                                    "0x181137B81",
                                    "0x181137C84",
                                ],
                                "escapeTargetVirtualAddress": "0x181131FC0",
                                "escapeTargetRecordReads": ["0x00"],
                                "escapeTargetRendererEntryReads": [
                                    "0x18",
                                    "0x26",
                                ],
                                "enabledLightModesReadObserved": False,
                                "scope": (
                                    "direct renderer-blob lookup CFGs only; "
                                    "GPU-driven renderer-list jobs receive the "
                                    "same 0x7F00 component column through "
                                    "their ECS query context"
                                ),
                                "callbackAFalsePositive": {
                                    "candidateReadVirtualAddress": (
                                        "0x181067F4B"
                                    ),
                                    "candidateStrideVirtualAddress": (
                                        "0x18106839E"
                                    ),
                                    "candidateFieldOffset": "0x14",
                                    "rejectedAsRuntimeRecord": True,
                                    "componentColumnAccessors": [
                                        {
                                            "virtualAddress": "0x181038D70",
                                            "archetypeBit": 127,
                                        },
                                        {
                                            "virtualAddress": "0x181038DE0",
                                            "archetypeBit": 126,
                                        },
                                    ],
                                    "equation": (
                                        "r13/r12 = archetype component-column "
                                        "base + rankOffset * elementSize; the "
                                        "callback then reads float@r13+0x14 "
                                        "and advances by 0x18"
                                    ),
                                    "interpretation": (
                                        "the matching offset and stride belong "
                                        "to an ECS component column selected by "
                                        "archetype bits 127/126, not to the "
                                        "0x7F00 renderer runtime-record blob"
                                    ),
                                },
                                "interpretation": (
                                    "all 53 direct calls to the blob lookup are "
                                    "pinned and partitioned into 44 exact "
                                    "0x7F00-family calls across 41 entry CFGs "
                                    "plus nine other-family calls. Register/"
                                    "stack taint follows direct hot/cold CFG "
                                    "edges. The six direct blob+0x04 call "
                                    "escapes are three zero-initializer calls "
                                    "and three calls to one hash-pinned "
                                    "classifier. The classifier reads only "
                                    "record+0x00. One additional blob+0x00 "
                                    "tail memcpy copies the complete count, "
                                    "runtime-record, and LOD-pair layout between "
                                    "two exact-family blobs, carrying +0x14 "
                                    "verbatim without interpreting it. The "
                                    "current and obsolete Factory "
                                    "CreateBatchedEntities internal calls both "
                                    "reach that helper through parallel copy "
                                    "cores. A third "
                                    "direct grouping "
                                    "consumer reads record+0x00/+0x04/+0x08/"
                                    "+0x10, while no exact-family path reads "
                                    "record+0x14, stores the record-base "
                                    "pointer outside the stack, returns it, "
                                    "or takes the address of one of its seven "
                                    "local stack spill slots. A same-offset, "
                                    "same-stride callback-A candidate remains "
                                    "independently rejected by its ECS column "
                                    "accessor provenance"
                                ),
                            },
                            "gpuDrivenRendererConsumer": {
                                "closed": True,
                                "generations": ["V1", "V2"],
                                "variants": ["default", "pre_z"],
                                "rendererFamilyMask": "0x7F00",
                                "recordStrideBytes": 24,
                                "recordOffset": "0x14",
                                "requestMaskJobOffset": "0x54",
                                "combinedFilterMaskJobOffset": "0x48",
                                "combinedFilterValueJobOffset": "0x4C",
                                "candidatePassLightModeOffset": "0x1C",
                                "representativeReadSites": [
                                    "0x1810E8E73",
                                    "0x1810EA245",
                                    "0x1810F5F7F",
                                    "0x1810F7356",
                                ],
                                "equations": [
                                    (
                                        "combinedFlags = record[+0x14] | "
                                        "candidatePass[+0x18] | "
                                        "callbackDerivedFlags"
                                    ),
                                    (
                                        "(combinedFlags & job[+0x48]) == "
                                        "job[+0x4C]"
                                    ),
                                    (
                                        "candidatePass[+0x1C] & "
                                        "job[+0x54] != 0"
                                    ),
                                ],
                            },
                        },
                        "maskType": "System.UInt32",
                        "shaderLightModeLiteralCount": 32,
                        "shaderLightModeCombinedMask": "0x7FFFFFFF",
                        "businessProducer": {
                            "type": "Beyond.Gameplay.Factory.PerDrawPassConfig",
                            "method": "Apply",
                            "parser": "_ParseToHGShaderLightMode",
                            "callVirtualAddress": "0x1869F3904",
                        },
                        "proof": (
                            "dedicated HyperGryph internal-call entry 204 names "
                            "SetEntityEnabledLightModes_Injected; its wrapper "
                            "reaches a core that selects the 0x7F00 renderer "
                            "family and writes the supplied UInt32 mask to "
                            "every record+0x14 at stride 0x18; IL2CPP metadata "
                            "defines HGShaderLightMode as bits 0..30, while "
                            "PerDrawPassConfig.Apply parses its gameplay pass "
                            "enum and calls the managed wrapper directly. The "
                            "Renderer base constructor initializes native field "
                            "+0x250 to 0xFFFFFFFF; two direct record builders "
                            "copy that field to record+0x14, and the generic "
                            "builder passes the same field through constructor "
                            "input+0x20 before the identical record write. "
                            "GPUDrivenRenderer V1/V2 default and PreZ jobs "
                            "then read record+0x14 from the selected 0x7F00 "
                            "ECS column and feed it into their combined "
                            "render-feature filter"
                        ),
                        "proofBoundary": (
                            "the exact downstream native consumer is closed "
                            "for GPUDrivenRenderer V1/V2 default and PreZ "
                            "renderer-list routes. All 53 direct blob-lookup "
                            "calls are "
                            "partitioned; 44 exact 0x7F00 calls across 41 "
                            "hot/cold entry CFGs expose no record+0x14 read, "
                            "non-stack record-base pointer store, record-base "
                            "return, or address-taken stack spill. "
                            "Their six direct blob+0x04 call escapes are three "
                            "memset-style zero initializers and three calls to "
                            "a classifier that reads only record+0x00. The "
                            "one blob+0x00 tail escape is a full-blob memcpy "
                            "that copies +0x14 verbatim without interpreting "
                            "it, and both Factory CreateBatchedEntities routes "
                            "are pinned to that helper. All three HGTree "
                            "CreateRendererList variants converge on the same "
                            "scheduler/callback family. The third direct "
                            "grouping consumer reads only +0x00/"
                            "+0x04/+0x08/+0x10, and the callback-A +0x14/"
                            "0x18-stride lookalike is an unrelated ECS "
                            "component-column float. Separately, four "
                            "GPU-driven renderer-list callbacks select the "
                            "0x7F00 ECS column and their V1/V2 default/PreZ "
                            "consumers read record+0x14. That word feeds the "
                            "job+0x48/+0x4C combined-flags filter, while "
                            "job+0x54 is tested independently against "
                            "candidatePass+0x1C"
                        ),
                    },
                },
            },
            "ownerCleanup": {
                "functionVirtualAddress": "0x1810BCE00",
                "ownerVectorPointerOffset": "0x78",
                "ownerVectorCountOffset": "0x88",
                "recordHandleOffset": "0x02",
                "recordBatchKeyOffset": "0x04",
                "unregisterCoreVirtualAddress": "0x181087E00",
                "proof": (
                    "cleanup iterates the blob count and 0x18-byte records, "
                    "passes dword@+0x04 as batchKey and word@+0x02 as handle "
                    "to UnregisterTreeBatchGroupWithHandle"
                ),
            },
        },
        "lodSelection": {
            "dispatcherVirtualAddress": "0x181079C10",
            "dispatcherSegmentVirtualAddress": "0x181079FB1",
            "callbackWrapperVirtualAddress": "0x181060E60",
            "payloadBuilderVirtualAddress": "0x18106EAD0",
            "directDistanceJobs": ["0x18106D7F0", "0x18106DA90"],
            "scaledMetricJobs": ["0x18106E0E0", "0x18106E400"],
            "positionOrigins": ["view +0x00", "view +0x18"],
            "ecsStateRecord": {
                "archetypeComponentBitIndex": 67,
                "accessorVirtualAddress": "0x181038D00",
                "indexedAccessorVirtualAddress": "0x1811648A0",
                "strideBytes": 24,
                "sentinelLodIndex": 8,
                "fields": [
                    {
                        "offset": "0x00",
                        "sizeBytes": 1,
                        "meaning": "LOD count consumed by all selection jobs",
                        "producerClosed": False,
                    },
                    {
                        "offset": "0x01",
                        "sizeBytes": 1,
                        "meaning": "mathematically selected/desired LOD index",
                    },
                    {
                        "offset": "0x02",
                        "sizeBytes": 1,
                        "meaning": "availability-resolved LOD index",
                    },
                    {
                        "offset": "0x03",
                        "sizeBytes": 1,
                        "meaning": (
                            "transition/output history byte; origin-0 jobs copy "
                            "the current resolved index, while origin-0x18 jobs "
                            "snapshot the prior resolved index"
                        ),
                    },
                    {
                        "offset": "0x04",
                        "sizeBytes": 1,
                        "meaning": "requested or pending LOD bit mask",
                    },
                    {
                        "offset": "0x05",
                        "sizeBytes": 1,
                        "meaning": "fully available LOD bit mask",
                    },
                    {
                        "offset": "0x06",
                        "sizeBytes": 2,
                        "meaning": (
                            "reserved/alignment word: serialized as zero and "
                            "not independently read or written on the complete "
                            "direct accessor-derived runtime surface"
                        ),
                    },
                    {
                        "offset": "0x08",
                        "sizeBytes": 8,
                        "meaning": "per-renderer/subresource readiness bits",
                    },
                    {
                        "offset": "0x10",
                        "sizeBytes": 8,
                        "meaning": (
                            "eight cumulative renderer-range end indices, one "
                            "per logical LOD"
                        ),
                    },
                ],
                "directAccessorClosure": {
                    "targets": component67_call_sites,
                    "directCallCount": sum(
                        len(row["callSites"])
                        for row in component67_call_sites.values()
                    ),
                    "logicalCallerCount": len(component67_caller_bodies),
                    "callerBodies": component67_caller_bodies,
                    "offlineControlFlowDataflow": {
                        "recordStrideBytes": 24,
                        "fieldOffsetsModuloStride": [0, 1, 2, 3, 4, 5, 8, 15, 16],
                        "recordPointerRegisterArgumentEscapeCount": 0,
                        "reservedWordStandaloneAccessCount": 0,
                        "reservedWordWriteCount": 0,
                        "note": (
                            "32-bit reads rooted at +0x04 include +0x06/+0x07 "
                            "physically, but runtime writers only update the "
                            "lower pending/available bytes; the reserved high "
                            "word remains the serialized zero value"
                        ),
                    },
                    "boundary": (
                        "all 25 direct rel32 calls to the two component-67 "
                        "accessors are enumerated and their 21 logical caller "
                        "bodies are hash-pinned; this closes the reserved word "
                        "on that accessor-derived surface, not hypothetical "
                        "inlined or unrelated component storage"
                    ),
                },
                "availabilityWriter": {
                    "virtualAddress": "0x1810842E0",
                    "request": "set the corresponding bit in record+0x04",
                    "complete": (
                        "when every renderer/subresource bit in the LOD range "
                        "is ready, clear record+0x04 and set record+0x05"
                    ),
                    "unload": (
                        "clear the LOD range in record+0x08 and clear the "
                        "corresponding bits in record+0x04 and record+0x05"
                    ),
                },
                "initialCompletionWriter": {
                    "virtualAddress": "0x181159010",
                    "normalEntryCondition": "record+0x04 == 1 (LOD0 pending)",
                    "normalTransition": {
                        "desiredLodAt0x01": 0,
                        "resolvedLodAt0x02": 0,
                        "historyLodAt0x03": 0,
                        "pendingMaskAt0x04": 0,
                        "availableMaskAt0x05": 1,
                        "readinessBitsAt0x08": (
                            "(1 << companion renderer/subresource count) - 1"
                        ),
                    },
                    "fallbackTransition": {
                        "desiredLodAt0x01": 8,
                        "resolvedLodAt0x02": 8,
                        "historyLodAt0x03": 8,
                        "readinessBitsAt0x08": 0,
                        "maskFieldsAt0x04And0x05": "left unchanged",
                    },
                    "closedBoundary": (
                        "this closes the initial LOD0 completion/fallback state "
                        "transition; it does not write record+0x00 or the "
                        "cumulative ranges at record+0x10..+0x17"
                    ),
                },
                "directAvailabilityInitializer": {
                    "virtualAddress": "0x181157760",
                    "allLodsBranch": {
                        "desiredResolvedHistoryAt0x01To0x03": [0, 0, 0],
                        "pendingMaskAt0x04": 0,
                        "availableMaskAt0x05": "(1 << lodCount) - 1",
                        "readinessBitsAt0x08": (
                            "(1 << companion renderer/subresource count) - 1"
                        ),
                    },
                    "terminalLodBranch": {
                        "lodIndex": "lodCount - 1",
                        "desiredResolvedHistory": "lodCount - 1",
                        "pendingMaskAt0x04": 0,
                        "availableMaskAt0x05": "1 << (lodCount - 1)",
                        "rangeStart": (
                            "0 for LOD0, otherwise cumulativeRange[lodIndex - 1]"
                        ),
                        "rangeEnd": "cumulativeRange[lodIndex]",
                        "readinessBitsAt0x08": (
                            "((1 << (rangeEnd - rangeStart)) - 1) << rangeStart"
                        ),
                    },
                    "closedBoundary": (
                        "this closes the direct all-LOD or terminal-LOD "
                        "available-state initializer and independently "
                        "confirms cumulative range consumption; it does not "
                        "produce lodCount or the cumulative endpoints"
                    ),
                },
                "componentIdMaskRegistration": {
                    "internalCallIndex": (
                        UNITY_ECS_GET_OR_REGISTER_ENTITY_TYPE_ICALL_INDEX
                    ),
                    "internalCallName": entity_type_name,
                    "bindingVirtualAddress": f"0x{entity_type_target:X}",
                    "componentIdInput": (
                        "signed 16-bit component id at stride 8"
                    ),
                    "componentCountLimit": 64,
                    "maskEquation": {
                        "bank": "componentId >> 6",
                        "bit": "componentId & 63",
                        "operation": "mask[bank] |= 1 << bit",
                    },
                    "archetypeMaskOffsets": ["0x10", "0x18"],
                    "component67Result": {
                        "bank": 1,
                        "bit": 3,
                        "highQwordMask": "0x0000000000000008",
                    },
                    "hgtreeComponent80Result": {
                        "bank": 1,
                        "bit": 16,
                        "highQwordMask": "0x0000000000010000",
                    },
                    "boundary": (
                        "this closes how numeric component ids become "
                        "archetype bits; the installed HGTreeComponent "
                        "get_id body independently returns 80, so this "
                        "component-67 record is not HGTreeComponent"
                    ),
                },
                "archetypeDescriptorRegistrationCore": {
                    "virtualAddress": "0x1801FAEC0",
                    "descriptorStrideBytes": 8,
                    "descriptorFields": [
                        {
                            "offset": "0x00",
                            "sizeBytes": 2,
                            "meaning": "signed component id",
                        },
                        {
                            "offset": "0x02",
                            "sizeBytes": 2,
                            "meaning": "component size in bytes",
                        },
                        {
                            "offset": "0x04",
                            "sizeBytes": 4,
                            "meaning": "cumulative component byte offset",
                        },
                    ],
                    "firstComponentDataOffsetBytes": 8,
                    "archetypeSizeLookupOffset": "0x42 + 8 * rank",
                    "archetypeDataOffsetLookupOffset": "0x44 + 8 * rank",
                    "component67Implication": (
                        "the 24-byte state must enter through a runtime "
                        "descriptor row or copied descriptor source; the "
                        "installed code contains no direct (id=67,size=24) "
                        "descriptor immediate"
                    ),
                    "boundary": (
                        "descriptor layout and cumulative storage placement "
                        "are closed; the native producer supplying the id-67 "
                        "row and its initial lodCount/ranges remains open"
                    ),
                },
                "excludedProducerRoutes": {
                    "hgmeshRendererData": {
                        "objectCount": 117,
                        "descriptorCount": 1449,
                        "component67DescriptorCount": 0,
                        "inventory": HGMESH_RENDERER_DATA_INVENTORY.relative_to(
                            LAB_ROOT
                        ).as_posix(),
                    },
                    "managedHGTreeConverterBinding": {
                        "completeConstructorBindingCount": 9,
                        "hgtreeBitIndex": 41,
                        "hgtreeBindingPresent": False,
                    },
                    "topLevelNativeSerializedObjects": {
                        "HGTreeClassId": "0x2C9CB981",
                        "HGTreeDataClassId": "0x59383C91",
                        "controlledPositiveType": "HGMeshRendererData",
                        "controlledPositiveCount": 117,
                        "HGTreeCount": 0,
                        "HGTreeDataCount": 0,
                    },
                    "boundary": (
                        "these hash-pinned source families and the controlled "
                        "top-level Unity-serialized HGTree/HGTreeData surface "
                        "are excluded. Streaming tag 1 component vectors are "
                        "also excluded, but tag 2 is now positively identified "
                        "as native ECS and contains the active Render and "
                        "MergedRenderCollider owner paths"
                    ),
                },
                "structureBoundary": (
                    "this pointer is resolved from archetype component bit 67; "
                    "it is not the loader-owned registration blob stored in "
                    "the runtime-transform owner's +0x78 vector, and it is "
                    "not the managed/native scripting HGTreeComponent at id 80"
                ),
                "nativeScriptingTypeIdentity": {
                    "proxyToNativeTypeNameClosed": True,
                    "proxyRegistrationVirtualAddress": "0x1807EEEE0",
                    "nativeTypeInitializerVirtualAddress": "0x1807EC5E0",
                    "unregisterThunkVirtualAddress": "0x1807EAF70",
                    "strings": component_type_strings,
                    "registrationFlow": [
                        (
                            "0x1807EEEE0 registers the decorated proxy name "
                            "with initializer 0x1807EC5E0 and unregister "
                            "thunk 0x1807EAF70"
                        ),
                        (
                            "0x1807EC5E0 resolves HGTreeComponent in "
                            "UnityEngine.HyperGryph.ECS from "
                            "UnityEngine.HGGraphicsModule.dll"
                        ),
                    ],
                    "managedGetId": managed_hgtree_component,
                    "boundary": (
                        "the scripting proxy/type identity and IL2CPP get_id "
                        "body are both closed: HGTreeComponent is id 80 "
                        "(high-qword bit 16), which disproves the former "
                        "candidate link to the separate id-67 LOD-state record"
                    ),
                },
                "managedHGTreeComponentIdMappingClosed": True,
                "managedHGTreeComponentId": 80,
                "component67MatchesHGTreeComponent": False,
                "nativeEntityOwnershipClosed": True,
                "nativeEntityOwners": ["Render", "MergedRenderCollider"],
                "component67NativeIdentityClosed": False,
            },
            "dispatchPacket": {
                "sizeBytes": 64,
                "payloadPointerOffset": "0x00",
                "lodCrossFadeConfigOffset": "0x08",
                "lodCrossFadeConfigSizeBytes": 56,
                "metadataFieldOrder": [
                    "cameraPosition",
                    "c0",
                    "c1",
                    "fraction",
                    "currMaxProjFactorSquared",
                    "maxProjFactorSquared0",
                    "maxProjFactorSquared1",
                    "enableDither",
                    "isOrtho",
                    "lodBias",
                ],
                "enableDitherPacketOffset": "0x3C",
                "lodBiasPacketOffset": "0x3E",
            },
            "payload": {
                "sizeBytes": 3120,
                "parentLODBiasSquaredOffset": "0x28",
                "artTagLODBiasSquaredOffset": "0x2C",
                "artTagLODBiasSecondaryEncodingOffset": "0x42C",
                "artTagLODStreamingOffsetOffset": "0x82C",
                "artTagEntryCount": 256,
                "sourceCopies": [
                    "payload+0x28 <- HGCullingSystem state+0x180",
                    "payload+0x2C <- HGCullingSystem state+0x184 (0x400 bytes)",
                    "payload+0x42C <- HGCullingSystem state+0x584 (0x400 bytes)",
                    "payload+0x82C <- HGLODStreamingSystem state+0x74 (0x400 bytes)",
                ],
            },
            "lodBiasEncoding": {
                "parentSetter": "state+0x180 = parentLODBias^2",
                "parentGetter": "sqrt(state+0x180)",
                "artTagPrimarySetter": (
                    "state+0x184+4*i = artTagLODBias[i]^2"
                ),
                "artTagPrimaryGetter": "sqrt(state+0x184+4*i)",
                "artTagSecondarySetter": (
                    "state+0x584+4*i = -artTagLODBias[i]^2 when "
                    "artTagLODBias[i]^2 < 1; otherwise 255"
                ),
                "viewLodBiasMultiplier": (
                    "when LODCrossFadeConfig.lodBias != 0, both 256-float "
                    "ArtTag tables are copied and multiplied by "
                    "(1 + lodBias / 255)^2"
                ),
            },
            "artTagLODStreamingOffset": {
                "getter": "HGLODStreamingSystem state+0x74+4*i",
                "setter": "HGLODStreamingSystem state+0x74+4*i",
                "selectionUse": (
                    "add the signed per-ArtTag offset to the selected LOD "
                    "index, then clamp to [0, lodCount-1]"
                ),
            },
            "directDistanceEquation": (
                "distanceSquared = dx*dx + dy*dy + dz*dz; select when "
                "lodFloat2.y < distanceSquared <= lodFloat2.x"
            ),
            "scaledMetricEquation": (
                "metric = (viewFactor * instanceScale) / "
                "max(0.0001, distanceSquared); select when "
                "lodFloat2.y * lowerScale < metric <= "
                "lodFloat2.x * upperScale"
            ),
            "scaledLowerScaleSelection": (
                "the lower bound uses the secondary ArtTag encoding when "
                "lodFloat2.y > 0, otherwise the primary squared-bias table"
            ),
            "selectionBoundary": "lower bound exclusive; upper bound inclusive",
            "verifiedFloatConstants": float_constants,
        },
        "treeInstance": {
            "nativeTypeName": "HGTreeInstance",
            "rendererArrayField": "renderers",
            "rendererElementType": "HGTreeRenderer",
            "otherFields": [
                "bounds",
                "rendererHalfSize",
                "objectFlags",
                "rendererOffsets",
                "colliderData",
                "colliderMeshes",
                "objectToWorld",
                "param0",
                "param1",
            ],
        },
        "rendererRecord": {
            "nativeTypeName": "HGTreeRenderer",
            "sizeBytes": 28,
            "fields": [
                {"name": "batchKey", "offset": "0x00", "sizeBytes": 4},
                {"name": "renderFlags", "offset": "0x04", "sizeBytes": 4},
                {"name": "mesh", "offset": "0x08", "sizeBytes": 4},
                {"name": "material", "offset": "0x0C", "sizeBytes": 4},
                {"name": "subMeshIndex", "offset": "0x10", "sizeBytes": 4},
                {
                    "name": "lodScreenSizeMaxSquared",
                    "offset": "0x14",
                    "sizeBytes": 4,
                },
                {
                    "name": "lodScreenSizeMinSquared",
                    "offset": "0x18",
                    "sizeBytes": 4,
                },
            ],
            "fieldNameEvidence": field_names,
        },
        "separationFromScheduledCulling": {
            "separateEntryAndOwnershipProven": True,
            "reason": (
                "the record is nested under HGTreeInstance.renderers and its "
                "renderer-list entry is a separate HGTreeRender internal call; "
                "the pinned DispatchBatchCullingJobs predicates do not reference "
                "this serializer lineage"
            ),
            "doesNotCloseCullViewScreenThresholdEquation": True,
        },
        "correctedPreviousBinding": {
            "retractedIndex": 10320,
            "retractedTargetVirtualAddress": "0x180175A10",
            "retractedManagerVirtualAddress": "0x180A5E320",
            "reason": (
                "index 10320 exceeded the dedicated 729-entry HyperGryph "
                "internal-call table; the resulting addresses belong to an "
                "unrelated Animator path and provide no HGTree evidence"
            ),
        },
        "evidenceBoundary": {
            "closed": [
                "HGTreeInstance owns a renderers array of HGTreeRenderer",
                "the exact 28-byte HGTreeRenderer serialized layout",
                "the dedicated 729-entry HyperGryph internal-call table pair",
                "HGTreeRender::CreateRendererList binding, core, and job scheduler",
                "HGTreeRender::RegisterTreeBatchGroup binding and registration core",
                "both HGTreeRender unregister bindings and native cores",
                "the owner cleanup's exact batchKey + registration-handle lifecycle",
                "the two selected runtime batch-job callback addresses",
                "the exact serialized-record to runtime-record and LOD float2 mapping",
                "the 1/2/4/8/16/32 runtime capacity buckets and LOD-array offsets",
                "the separate component-bit-67 24-byte ECS LOD state layout",
                "component-67 +0x06/+0x07 as a zero reserved/alignment word on the complete direct accessor surface",
                "StreamingSceneV2 tag 2 as the native ECS union variant",
                "component 67 ownership by Render and MergedRenderCollider entity paths",
                "the complete installed ECSEntityType/ProxyEntityType payload census",
                "pending, available, and per-renderer readiness mask transitions",
                "the separation between the loader registration blob and ECS LOD state",
                "the direct squared-distance LOD interval equation",
                "the scaled-metric LOD interval equation and its 0.0001 floor",
                "the six-way LOD job dispatch segment",
                "the 64-byte dispatch packet and 0xC30-byte payload layouts",
                "LODCrossFadeConfig enableDither/lodBias packet offsets",
                "parent and per-ArtTag LOD-bias squared runtime encodings",
                "the exact per-view lodBias threshold multiplier",
                "ArtTag LODStreamingOffset production, payload copy, add, and clamp",
                "the correction that the old 10320/Animator binding was invalid",
                "HGTreeRenderer is not evidence for the scheduled cull-view +0x18 equation",
            ],
            "open": [
                "semantic roles for the loader registration blob's remaining initially zero bytes",
                "the standalone native component type name for archetype bit 67",
            ],
        },
        "verifiedBodies": bodies,
        "verifiedInstructionSlices": slices,
    }


def _read_text_assets(
    extracted_root: Path, *, verify_hashes: bool
) -> tuple[dict[str, str], list[dict[str, object]]]:
    texts: dict[str, str] = {}
    records: list[dict[str, object]] = []
    for logical_name, (file_name, expected_hash, path_id_hex) in TEXT_ASSETS.items():
        path = extracted_root / file_name
        require(f"{logical_name}_exists", path.is_file(), True, path)
        actual_hash = sha256(path)
        if verify_hashes:
            require(
                f"{logical_name}_sha256",
                actual_hash,
                expected_hash,
                path,
            )
        texts[logical_name] = path.read_text(encoding="utf-8-sig")
        records.append(
            {
                "name": logical_name,
                "pathIdHex": path_id_hex,
                "fileName": file_name,
                "sizeBytes": path.stat().st_size,
                "sha256": actual_hash,
            }
        )
    return texts, records


def _parse_include_routes(text: str) -> dict[str, str]:
    section = ""
    routes: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"\[IncludeSettings(?:@([^]]+))?\]", line)
        if match:
            section = match.group(1) or "Common"
            continue
        match = re.fullmatch(r"includeSettings\s*=\s*(\S+)", line)
        if match and section:
            routes[section] = match.group(1)
    return routes


def validate_settings_payloads(
    extracted_root: Path, *, verify_hashes: bool = True
) -> tuple[list[dict[str, object]], dict[str, list[int]]]:
    texts, records = _read_text_assets(
        extracted_root, verify_hashes=verify_hashes
    )
    setting_files = [
        line.strip()
        for line in texts["SettingFiles"].splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(
        "setting_file_list",
        setting_files,
        EXPECTED_SETTING_FILES,
        extracted_root / TEXT_ASSETS["SettingFiles"][0],
    )
    include_routes = _parse_include_routes(texts["HGRenderPipelineSettings"])
    require(
        "include_routes",
        include_routes,
        EXPECTED_INCLUDE_ROUTES,
        extracted_root / TEXT_ASSETS["HGRenderPipelineSettings"][0],
    )

    cap_pattern = re.compile(
        r"^\s*PunctualLightMaxCount\s*=\s*(-?\d+)\s*$",
        re.MULTILINE,
    )
    cap_definitions = {
        name: [int(value) for value in cap_pattern.findall(text)]
        for name, text in texts.items()
        if cap_pattern.search(text)
    }
    require(
        "cap_definitions",
        cap_definitions,
        EXPECTED_CAP_DEFINITIONS,
        extracted_root,
    )
    screen_threshold_pattern = re.compile(
        r"^\s*CullingViewScreenSizeMin\s*=\s*(-?(?:\d+(?:\.\d*)?|\.\d+))\s*$",
        re.MULTILINE,
    )
    screen_threshold_definitions = {
        name: [float(value) for value in screen_threshold_pattern.findall(text)]
        for name, text in texts.items()
        if screen_threshold_pattern.search(text)
    }
    require(
        "screen_threshold_definitions",
        screen_threshold_definitions,
        EXPECTED_SCREEN_THRESHOLD_DEFINITIONS,
        extracted_root,
    )
    return records, cap_definitions


def _require_source_contracts() -> dict[str, str]:
    paths = {
        "device_type_source": DEVICE_TYPE_SOURCE,
        "setting_hub_source": SETTING_HUB_SOURCE,
        "setting_parameters_source": SETTING_PARAMETERS_SOURCE,
        "light_cluster_source": LIGHT_CLUSTER_SOURCE,
        "hg_camera_source": HG_CAMERA_SOURCE,
    }
    texts = {name: path.read_text(encoding="utf-8-sig") for name, path in paths.items()}
    snippets = {
        "device_type_source": ["Handheld", "Console", "Desktop", "Cinematic"],
        "setting_hub_source": [
            "UnityEngine::SystemInfo::GetDeviceType(0LL)",
            "_currentDeviceType_k__BackingField = overrideDeviceType",
        ],
        "setting_parameters_source": [
            "SettingParameter::Create<int>(",
            "//                                                           256,",
            '(String *)"PunctualLightMaxCount"',
            "this.fields._cullingViewScreenSizeMin_k__BackingField = HG::Rendering::Runtime::SettingParameter::Create<float>(",
            '(String *)"CullingViewScreenSizeMin"',
        ],
        "light_cluster_source": [
            "*(_DWORD *)m_Buffer == 2 || !*(_DWORD *)m_Buffer",
            "System::Single::CompareTo((Single *)&this.distance, other.distance",
            "System::Int32::CompareTo((Int32 *)&other.priority, this.priority",
            "if ( v12 < (int)v42 )",
            "this.fields.m_punctualLightCount = v42",
        ],
        "hg_camera_source": [
            "settingParameters.fields._cullingViewScreenSizeMin_k__BackingField",
            "v21 = HG::Rendering::Runtime::SettingParameter<float>::op_Implicit",
            "SceneCullingMaskFromCamera = HG::Rendering::Runtime::HGUtils::GetSceneCullingMaskFromCamera",
            "v31 = useOcclusionCulling ? 0x140 : 0",
            "v32 = useOcclusionCulling ? 0xA0 : 0",
            "HGCullingSystem::AddCullViewByMatrix(UnityEngine.Matrix4x4&",
        ],
    }
    for name, required in snippets.items():
        for snippet in required:
            require(
                f"{name}_snippet",
                snippet in texts[name],
                True,
                paths[name],
            )
    return texts


def build_audit(extracted_root: Path) -> dict[str, object]:
    hashes = {
        "game_assembly": verified_hash("game_assembly", GAME_ASSEMBLY),
        "unity_player": verified_hash("unity_player", UNITY_PLAYER),
        "global_metadata": verified_hash("global_metadata", GLOBAL_METADATA),
        "init_bundle_chunk": verified_hash(
            "init_bundle_chunk", INIT_BUNDLE_CHUNK
        ),
        "device_type_source": verified_hash(
            "device_type_source", DEVICE_TYPE_SOURCE
        ),
        "setting_hub_source": verified_hash(
            "setting_hub_source", SETTING_HUB_SOURCE
        ),
        "setting_parameters_source": verified_hash(
            "setting_parameters_source", SETTING_PARAMETERS_SOURCE
        ),
        "light_cluster_source": verified_hash(
            "light_cluster_source", LIGHT_CLUSTER_SOURCE
        ),
        "hg_camera_source": verified_hash("hg_camera_source", HG_CAMERA_SOURCE),
        "ifix_state": verified_hash("ifix_state", IFIX_STATE),
        "hgmesh_renderer_data_source": verified_hash(
            "hgmesh_renderer_data_source", HGMESH_RENDERER_DATA_SOURCE
        ),
        "animestudio_class_id_source": verified_hash(
            "animestudio_class_id_source", ANIMESTUDIO_CLASS_ID_SOURCE
        ),
        "animestudio_asset_helper_source": verified_hash(
            "animestudio_asset_helper_source", ANIMESTUDIO_ASSET_HELPER_SOURCE
        ),
    }
    _require_source_contracts()
    asset_records, cap_definitions = validate_settings_payloads(extracted_root)
    native_handoff = validate_native_handoff(read_native_method_bodies())
    unity_native_producer = validate_unity_native_producer(PEImage(UNITY_PLAYER))
    unity_cull_view_constructor = validate_unity_cull_view_constructor(
        PEImage(UNITY_PLAYER)
    )
    unity_scheduled_culling_boundary = (
        validate_unity_scheduled_culling_boundary(PEImage(UNITY_PLAYER))
    )
    unity_cull_view_consumer_surface = (
        validate_unity_cull_view_consumer_surface(PEImage(UNITY_PLAYER))
    )
    unity_hgtree_renderer_boundary = validate_unity_hgtree_renderer_boundary(
        PEImage(UNITY_PLAYER), native_handoff["managedHGTreeComponent"]
    )
    unity_streaming_component_conversion = validate_streaming_component_conversion(
        PEImage(UNITY_PLAYER),
        managed_component_ids={
            "HGTreeComponent": native_handoff[
                "managedHGTreeComponent"
            ]["componentId"],
            "RenderObjectLODInfoComponent": native_handoff[
                "managedRenderObjectLODInfoComponent"
            ]["componentId"],
        },
    )
    hgmesh_renderer_data_inventory = validate_hgmesh_renderer_data_inventory(
        verify_source_hash=False
    )
    hgtree_native_serialized_type_census = (
        validate_hgtree_native_serialized_type_census(PEImage(UNITY_PLAYER))
    )
    streaming_scene_v2_payload_census = (
        validate_streaming_scene_v2_payload_census(
            PEImage(UNITY_PLAYER), PEImage(GAME_ASSEMBLY)
        )
    )

    ifix = json.loads(IFIX_STATE.read_text(encoding="utf-8"))
    require(
        "ifix_target_count",
        ifix["patch_format"]["target_count"],
        30,
        IFIX_STATE,
    )
    hgrp_targets = [
        f"{row['type']}.{row['method']}"
        for row in ifix["targets"]
        if row["type"].startswith("HG.Rendering.Runtime")
    ]
    require("ifix_hgrp_targets", hgrp_targets, [], IFIX_STATE)

    return {
        "schema": "endfield.recovered-light-cull-cap.v36",
        "status": "hgtree_shadow_proxy_render_flags_abi_resolved",
        "outcome": (
            "The installed Windows desktop route resolves PunctualLightMaxCount "
            "to 256. SetupState accepts only VisibleLight types 0/2, sorts by "
            "priority descending then squared distance ascending, and applies "
            "min(survivorCount, cap). Because HGCullingSystem.CullLights already "
            "receives maxCount=256, the desktop settings cap cannot further "
            "truncate that native result. The GameAssembly handoff, UnityPlayer "
            "native candidate gates, 16-byte LightCullResult, and 148-byte "
            "VisibleLight capture stride are source-closed. AddCullViewByMatrix "
            "also closes the scheduled view layout and visibility-then-camera-mask "
            "gate. DispatchBatchCullingJobs selects an exact six-plane AABB "
            "predicate, except cameraType 0x80 selects an exact sphere/distance "
            "predicate; neither reads cull-view +0x18. "
            "The complete installed CullView-named internal-call surface is now "
            "closed as well. AddCullViewByPlanes shares the same scheduled "
            "constructor; DispatchBatchCullingJobs passes the manager+0x38 "
            "view-pointer array directly into the batch core; the complete "
            "per-view loop, both selected predicates, GetCullingViewFence, and "
            "ResetCullViews do not read +0x18. AddCullChildViewByPlanes writes a "
            "separate manager+0x58 array of 0xE8-byte records. The installed "
            "screenSizeMinimumSquared field is therefore write-only on this "
            "closed native surface, with no post-dispatch packet copy or gate. "
            "The previously separate "
            "28-byte record is now identified exactly as HGTreeRenderer nested "
            "under HGTreeInstance.renderers, and its CreateRendererList entry "
            "is paired at local index 564 in the dedicated 729-entry HyperGryph "
            "internal-call tables. The binding reaches the renderer-list core, "
            "job scheduler, and two runtime batch-job callbacks; batch-group "
            "registration is independently paired at index 567. The paired "
            "unregister entries at 568/569 and the owner cleanup prove that "
            "the loader record's +0x02 word is the registration handle and "
            "+0x04 is batchKey. The loader's "
            "exact 28-byte serialized input, 24-byte runtime records, bucketed "
            "LOD float2 array, registration argument mapping, six-way LOD job "
            "dispatch, direct squared-distance interval, and scaled metric "
            "interval are now closed. Runtime record +0x08 has a mutable "
            "renderFlags lifecycle: four particle setup variants replace it "
            "with bit 20 and a scheduled callback ORs it into render flags. "
            "The prior resource-to-record offsets were four bytes high because "
            "writer targets were measured from the blob header while runtime "
            "records begin at blob+0x04. A newly hash-pinned independent "
            "HGMeshRendererData initializer closes the correction: native "
            "m_Materials/m_Meshes/m_ShadowProxyMeshes at +0x58/+0x78/+0x98 "
            "resolve through singleton Material and Mesh GeometryHandle maps at "
            "+0x90/+0xA0 and write record +0x04/+0x08/+0x0C. The availability "
            "writers and cleanup use the same three destinations. Record "
            "+0x0C is therefore the m_ShadowProxyMeshes GeometryHandle, not the "
            "main Mesh word or a property-flag seed. Both owner transitions "
            "acquire that third resource handle with kind 2. "
            "HyperGryph internal-call entry 437 names "
            "the forwarding wrapper HGResourceManager::LoadAsync_Injected, "
            "and its IL2CPP signature plus AssetType literals close kind 2 as "
            "Mesh. Entries 440/441 close the handle-slot +0x18 word as a Unity "
            "asset instance ID: UpdateAssetHandle writes it and GetAsset uses "
            "it to recover the Unity object. The availability writers gate on "
            "slot+0x10 ready==1, map that instance ID through a separate "
            "12-byte table, and copy entry+0x08 to record+0x0C. Cleanup releases "
            "the third handle and clears the same field; the scheduled callback "
            "consumes it in a combined masked filter overlay. HyperGryph "
            "internal-call entries 300/301 name the value exactly through "
            "HGGeometrySystem::GetGeometryHandle/GetMesh. The hash-pinned slot "
            "builder closes bits 0..23 as the slot index and bits 24..31 as an "
            "8-bit generation incremented at slot +0x06. The engine identity and "
            "bit packing are therefore closed. Installed metadata then names "
            "the upstream CreateRendererList UInt32 arguments renderFlagsMask, "
            "renderFlagsValue, and lightModeMask. The binding, core, and "
            "scheduler preserve them into descriptor +0x40/+0x44/+0x48; the "
            "callback's +0x04 descriptor bias exposes them at +0x3C/+0x40/+0x44. "
            "Thus the GeometryHandle is intentionally folded into the HGTree "
            "renderFlags mask/value ABI rather than being a standalone filter "
            "bitfield. Concrete per-pass callers and supplied values remain open. "
            "Record +0x10 "
            "is not seeded by any of the three resource maps; "
            "it remains Renderer property flags maintained at blob+0x14 by the "
            "common state synchronizer. Dedicated HyperGryph internal-"
            "call entry 204 names record +0x14 exactly as enabledLightModes; "
            "its hash-pinned core writes the supplied UInt32 value to every "
            "record. IL2CPP metadata closes HGShaderLightMode as 31 named "
            "render-pass bits spanning 0..30, and the hash-pinned gameplay "
            "PerDrawPassConfig parser and Apply method pass that mask through "
            "the managed wrapper. The Renderer base constructor also defaults "
            "native field +0x250 to 0xFFFFFFFF; two direct record builders copy "
            "it to record +0x14, while the generic path carries it through "
            "constructor input +0x20 before the same write. The two HGTree "
            "renderer-list callbacks compare job+0x44 against a separate "
            "renderer-entry +0x1C word. Two hash-pinned entry builders clear "
            "that word, query all 31 installed HGShaderLightMode pass names "
            "against the renderer material/shader, and set the supported "
            "bits. The entry word is therefore a shader-supported-pass mask, "
            "not a projection of record +0x14. Separately, HyperGryph "
            "internal-call entries 151/152 and 164/165 close "
            "GPUDrivenRenderer V1/V2 default/PreZ renderer-list routes. Their "
            "four job callbacks carry the request mask in descriptor +0x54, "
            "select the 0x7F00 ECS renderer column, and their representative "
            "V1/V2 default/PreZ consumers read record +0x14 at stride 0x18. "
            "That enabledLightModes word is ORed with candidate-pass and "
            "callback-derived flags before job+0x48/+0x4C mask/value "
            "filtering; the requested mask is independently intersected with "
            "candidate-pass +0x1C. All 53 direct calls to the "
            "renderer-blob lookup are now pinned and partitioned into 44 "
            "exact 0x7F00-family calls across 41 entry CFGs and nine "
            "other-family calls. Cross-hot/cold CFG taint finds no exact-path "
            "record +0x14 read, non-stack record-base pointer store, record-"
            "base return, or address-taken stack spill. The seven exact-result "
            "stack stores are local spills or reused slots. The six direct "
            "blob+0x04 call escapes are three zero "
            "initializers and three calls to one classifier that reads only "
            "record +0x00 and renderer-entry flags. One additional blob+0x00 "
            "tail memcpy copies the complete count/runtime-record/LOD-pair "
            "layout between exact-family blobs, carrying +0x14 verbatim "
            "without interpreting it. The current and obsolete Factory "
            "CreateBatchedEntities internal calls both reach that helper "
            "through parallel hash-pinned copy cores. The three HGTree "
            "CreateRendererList internal calls (default, child-view, and "
            "PreZ) independently converge on the same scheduler and selected "
            "callback family, excluding an alternate variant-specific +0x14 "
            "consumer. A third direct component-"
            "grouping consumer reads only record +0x00/+0x04/+0x08/+0x10; "
            "the apparent callback-A +0x14/0x18-stride read is separately "
            "proven to be an unrelated ECS component-column float. The exact "
            "downstream GPU-driven render-stage consumer of record +0x14 is "
            "therefore closed outside the direct blob-lookup surface. The "
            "dispatch packet/"
            "payload layouts, "
            "LODCrossFadeConfig enableDither/lodBias controls, parent and "
            "per-ArtTag bias encodings, and ArtTag LODStreamingOffset add/clamp "
            "path are now source-closed as well. A separate component-bit-67 "
            "24-byte ECS record closes the desired/resolved/history LOD bytes, "
            "pending and available LOD masks, 64-bit renderer-readiness mask, "
            "the zero reserved/alignment word at +0x06, and eight cumulative "
            "renderer-range endpoints. All 25 direct calls to its two "
            "accessors and 21 logical caller bodies are pinned. Its indexed "
            "accessor and initial LOD0 completion/fallback writer are pinned "
            "as well. The installed native scripting registration now closes "
            "HGTreeComponentProxy to the HGTreeComponent type name, namespace, "
            "and HGGraphics module. EntityManager's registered internal call "
            "closes the numeric-component-id to two-qword archetype-mask "
            "equation, including id 67 -> high-qword bit 3. A second state "
            "initializer closes the all-LOD and terminal-LOD directly "
            "available branches while consuming the cumulative ranges. The "
            "hash-pinned IL2CPP HGTreeComponent.get_id body returns 80, "
            "mapping it to high-qword bit 16 and disproving the former "
            "candidate link between HGTreeComponent and the separate "
            "component-67 LOD-state record. Raw UInt64 metadata defaults now "
            "close StreamingComponentType HLODGroup as bit 11 and HGTree as "
            "bit 41, with Count=43. The registered conversion path maps each "
            "single-bit type through bsf into a 0x308-byte descriptor slot, "
            "requires a non-empty list, and requires Transform first. The "
            "similarly named managed RenderObjectLODInfoComponent independently "
            "returns id 6, so neither managed candidate names id 67. The native "
            "entity-type registration core now closes each 8-byte descriptor "
            "as component id, component size, and cumulative data offset, with "
            "component storage starting at byte 8. No direct id-67/size-24 "
            "descriptor immediate exists, which narrowed the producer search "
            "to copied StreamingSceneV2 data. The complete installed "
            "117-object HGMeshRendererData corpus contains 1,449 valid ECS "
            "descriptors, but none has id 67, excluding that serialized blob "
            "family as the producer. The complete hash-pinned managed "
            "StreamingSceneManagerScript constructor binds nine Mono converter "
            "bits but not HGTree bit 41, excluding that managed delegate route "
            "from the static constructor source set as well. The UnityPlayer "
            "native serialized-type table now closes HGTree/HGTreeData class "
            "IDs as 0x2C9CB981/0x59383C91. A controlled complete "
            "StreamingAssets scan uses the 117 HGMeshRendererData objects as a "
            "positive map-and-export gate but finds zero top-level HGTree or "
            "HGTreeData objects. Their static Unity-serialized object surface "
            "is therefore excluded. The exact StreamingSceneV2 managed/native "
            "Create route, 83 serialized map roots, path construction, request "
            "callback, and interleaved-token LZ4 decoder are now pinned. A full "
            "scan of 51,012 main Streaming payloads (3,088,714,060 decoded "
            "bytes and 3,084,834 union records) finds no HGTree bit-41 or "
            "HLODGroup bit-11 tag-1 component entry. The native dispatch "
            "tables close tag 1 as MonoEntity, tag 2 as native ECS, and tag 3 "
            "as Proxy. Installed metadata closes all ECSEntityType and "
            "ProxyEntityType values. The native type-0 Render and type-9 "
            "MergedRenderCollider callback slots both access component 67, "
            "closing its entity ownership to a shared native render/merged-"
            "render-collider LOD-streaming path. The full scan contains "
            "34,672 Render and 2,576,964 MergedRenderCollider records. "
            "StreamingSceneV2 root fields 6/7 now close the paired native "
            "entity groups and archetype descriptions. Each 8-byte descriptor "
            "contains an Int16 component id, Int16 element size, and UInt32 "
            "auxiliary value; component 67 is serialized with size 24. The "
            "hash-pinned native copier at 0x1801F95E0 copies each "
            "entityCount*elementSize initial-data slice directly into native "
            "ECS storage. Across all 83 map scopes, the 1,230,041 distinct "
            "component-67 entity ids exactly equal the distinct type-0/type-9 "
            "owner set. All 1,305,818 serialized occurrences initialize "
            "lodCount in 1..6, state bytes 8/8/8/0/0, a zero reserved word at "
            "+0x06, zero readiness, and one of 102 cumulative renderer-range "
            "patterns. Duplicate map/entity "
            "records are byte-identical. Thus the LOD count and range producer "
            "is the original game-binary initial-data blob, not a later "
            "ConvertFrom inference. All "
            "1,576 DynamicStreaming "
            "init/stream payloads contain only union tag 2 and no component "
            "entry. Its 457 fb_main files do contain 2,828 gameplay "
            "FBDynamicSceneTreeRootComp rows, but managed enum values Tree=11 "
            "and TreeRootComp=64 prove that this destructible-tree normal-model "
            "route is separate from both StreamingComponentType HGTree bit 41 "
            "and ECS component id 67. The standalone native component name "
            "remains open. The "
            "old index "
            "10320 and manager/virtual-slot path are retracted because that "
            "index crossed the table boundary into unrelated Animator code. "
            "The concrete per-pass callers and values supplied to HGTree "
            "CreateRendererList's renderFlagsMask/renderFlagsValue ABI, the "
            "component-67 standalone native type name, "
            "target-frame pointer/count, and unrelated live native lights "
            "remain open."
        ),
        "installedInputs": {
            "gameAssembly": {
                "sizeBytes": GAME_ASSEMBLY.stat().st_size,
                "sha256": hashes["game_assembly"],
            },
            "unityPlayer": {
                "sizeBytes": UNITY_PLAYER.stat().st_size,
                "sha256": hashes["unity_player"],
            },
            "globalMetadata": {
                "sizeBytes": GLOBAL_METADATA.stat().st_size,
                "sha256": hashes["global_metadata"],
            },
            "initBundleChunk": {
                "vfsRelativePath": (
                    "0CE8FA57/19F0903A12BA87C0D43E67E64889B525.chk"
                ),
                "blockType": "InitBundle",
                "sizeBytes": INIT_BUNDLE_CHUNK.stat().st_size,
                "sha256": hashes["init_bundle_chunk"],
                "serializedFileOffset": 157608586,
            },
            "installedIfixState": {
                "path": IFIX_STATE.relative_to(LAB_ROOT).as_posix(),
                "sha256": hashes["ifix_state"],
                "targetCount": 30,
                "hgrpSettingOrLightClusterTargets": [],
            },
            "hgmeshRendererDataSource": {
                "vfsRelativePath": (
                    "7064D8E2/B428C352B17C75CA29122CAACC037A59.chk"
                ),
                "sizeBytes": HGMESH_RENDERER_DATA_SOURCE.stat().st_size,
                "sha256": hashes["hgmesh_renderer_data_source"],
                "inventoryPath": HGMESH_RENDERER_DATA_INVENTORY.relative_to(
                    LAB_ROOT
                ).as_posix(),
            },
            "hgtreeNativeSerializedTypeCensus": {
                "path": HGTREE_NATIVE_SERIALIZED_TYPE_CENSUS.relative_to(
                    LAB_ROOT
                ).as_posix(),
                "streamingAssetsFileCount": 966,
                "streamingAssetsTotalBytes": 57_058_764_239,
                "controlledPositiveCount": 117,
                "hgtreeCount": 0,
                "hgtreeDataCount": 0,
            },
            "streamingSceneV2PayloadCensus": {
                "path": STREAMING_SCENE_V2_PAYLOAD_CENSUS.relative_to(
                    LAB_ROOT
                ).as_posix(),
                "serializedMapConfigCount": 83,
                "installedVfsFileCount": 53_206,
                "mainPayloadFileCount": 51_012,
                "mainPayloadDecompressedBytes": 3_088_714_060,
                "hgtreeBit41ComponentCount": 0,
                "component67DistinctEntityCountByMapScope": 1_230_041,
                "component67OwnerSetExactPerMapScope": True,
                "component67InitialDataOccurrenceCount": 1_305_818,
                "dynamicUnionComponentCount": 0,
                "dynamicGameplayTreeRootCompCount": 2_828,
            },
        },
        "settingTextAssets": asset_records,
        "settingRoute": {
            "entry": "HGRenderPipelineSettings.ini",
            "settingFiles": EXPECTED_SETTING_FILES,
            "includeRoutes": EXPECTED_INCLUDE_ROUTES,
            "installedPlayer": "Windows desktop",
            "deviceSelection": (
                "HGRenderPipelineSettings.PopulateDeviceInfo uses "
                "UnityEngine.SystemInfo.GetDeviceType when no override is supplied"
            ),
            "desktopCloudInheritance": (
                "CloudDesktopOverride contains no PunctualLightMaxCount and "
                "inherits DesktopSettings"
            ),
            "screenSizeMinimum": {
                "constructorDefault": 0.0,
                "desktopOrCloudOverride": None,
                "onlyExtractedOverrides": EXPECTED_SCREEN_THRESHOLD_DEFINITIONS,
                "managedInput": "square before AddCullViewByMatrix",
            },
        },
        "capDefinitions": cap_definitions,
        "resolvedInstalledDesktopCap": 256,
        "nativeContract": {
            "settingDefault": {
                "method": "HG.Rendering.Runtime.HGSettingParameters..ctor",
                "methodIndex": 288533,
                "virtualAddress": "0x1836590A0",
                "value": 256,
            },
            "setupState": {
                "method": (
                    "HG.Rendering.Runtime.LightClusteringPassConstructor.SetupState"
                ),
                "methodIndex": 285302,
                "virtualAddress": "0x189D09F50",
                "acceptedVisibleLightTypes": [0, 2],
                "sortOrder": [
                    "priority descending",
                    "squared camera distance ascending",
                ],
                "finalCountEquation": "min(punctualSurvivorCount, punctualLightMaxCount)",
            },
            "upstreamCull": {
                "method": "HG.Rendering.Runtime.HGCullingSystem.CullLights",
                "directCaller": "HG.Rendering.Runtime.HGCamera.DoECSCulling",
                "directCallSiteCount": 2,
                "maxCount": 256,
            },
            "gameAssemblyHandoff": native_handoff,
            "unityPlayerCandidateProducer": unity_native_producer,
            "unityPlayerCullViewConstructor": unity_cull_view_constructor,
            "unityPlayerScheduledCullingBoundary": (
                unity_scheduled_culling_boundary
            ),
            "unityPlayerCullViewConsumerSurface": (
                unity_cull_view_consumer_surface
            ),
            "unityPlayerHGTreeRendererBoundary": unity_hgtree_renderer_boundary,
            "unityPlayerStreamingComponentConversion": (
                unity_streaming_component_conversion
            ),
            "hgmeshRendererDataComponentInventory": (
                hgmesh_renderer_data_inventory
            ),
            "hgtreeNativeSerializedTypeCensus": (
                hgtree_native_serialized_type_census
            ),
            "streamingSceneV2PayloadCensus": (
                streaming_scene_v2_payload_census
            ),
            "desktopNoSecondTruncation": True,
        },
        "sourceFiles": {
            name: {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "sha256": hashes[name],
            }
            for name, path in {
                "device_type_source": DEVICE_TYPE_SOURCE,
                "setting_hub_source": SETTING_HUB_SOURCE,
                "setting_parameters_source": SETTING_PARAMETERS_SOURCE,
                "light_cluster_source": LIGHT_CLUSTER_SOURCE,
                "hg_camera_source": HG_CAMERA_SOURCE,
                "animestudio_class_id_source": ANIMESTUDIO_CLASS_ID_SOURCE,
                "animestudio_asset_helper_source": ANIMESTUDIO_ASSET_HELPER_SOURCE,
            }.items()
        },
        "evidenceBoundary": {
            "sourceClosed": [
                "installed Windows desktop cap value 256",
                "type 0/2 punctual filter",
                "priority/distance shortlist order",
                "min survivor/cap final-count rule",
                "desktop cap cannot truncate the upstream max-256 cull result",
                "the unique UnityPlayer CullLightsInternal_Injected binding and native candidate gate chain",
                "both GameAssembly DoECSCulling call sites and their exact input/result registers",
                "the 16-byte LightCullResult pointer/count ABI and NativeArray projection",
                "the 148-byte VisibleLight capture stride plus SetupState type, priority, and world-position offsets",
                "the AddCullViewByMatrix binding, six-plane constructor, view layout, and generic visibility/mask gate order",
                "the DispatchBatchCullingJobs binding, camera-type predicate split, and exact selected predicates",
                "the complete installed CullView-named internal-call surface, manager+0x38 pointer-container handoff, per-view batch loop, fence/reset lifecycle, separate child-view array, and absence of a screenSizeMinimumSquared +0x18 consumer or post-dispatch packet copy",
                "HGTreeInstance ownership and the exact 28-byte HGTreeRenderer LOD record",
                "the dedicated 729-entry HyperGryph internal-call name/function table pair",
                "the HGTreeRender CreateRendererList binding, core, scheduler, and selected runtime callbacks",
                "the HGTreeRender RegisterTreeBatchGroup binding and registration core",
                "the HGTreeRenderer serialized-to-runtime record and LOD float2 mapping",
                "loader runtime record +0x08 mutable renderFlags lifecycle, including particle bit-20 writers and scheduled consumption",
                "the hash-pinned HGMeshRendererData m_Materials/m_Meshes/m_ShadowProxyMeshes native field layout and independent Material/GeometryHandle map initializer into runtime record +0x04/+0x08/+0x0C",
                "HGGeometrySystem GetGeometryHandle/GetMesh internal-call entries 300/301, Mesh instance-ID map insertion/removal, 24-bit slot-index plus 8-bit generation handle packing, and reverse lookup",
                "loader runtime record +0x0C as the m_ShadowProxyMeshes GeometryHandle, including LoadAsync/GetAsset/UpdateAssetHandle internal-call bindings, ready/instance-ID handle-slot layout, direct and availability map-resolution writers, cleanup, and masked consumption",
                "the HGTree CreateRendererList UInt32 renderFlagsMask/renderFlagsValue/lightModeMask metadata contract and its binding/core/scheduler/callback descriptor-offset propagation",
                "loader runtime record +0x10 as Renderer property flags with no resource-map seed and its common state-synchronization writer",
                "loader runtime record +0x14 as enabledLightModes through dedicated internal-call entry 204 and its all-record writer",
                "the UInt32 enabledLightModes signature, all 31 named HGShaderLightMode pass bits, and the PerDrawPassConfig parser/Apply producer chain",
                "the Renderer +0x250 enabledLightModes default and all three hash-pinned native record-initialization paths",
                "GPUDrivenRenderer V1/V2 default and PreZ internal-call bindings, cores, 0xA0-byte job builders, callbacks, and representative consumers that read 0x7F00 record+0x14 at stride 0x18",
                "the split GPU-driven filtering contract: record+0x14 joins candidate-pass/callback flags for job+0x48/+0x4C mask-value filtering, while job+0x54 independently intersects candidate-pass+0x1C light-mode support",
                "the independent renderer-entry +0x1C shader-supported-pass mask, both native builders, and its exact 31-name pass table",
                "all three HGTree CreateRendererList variants and their convergence on one shared scheduler/callback family",
                "the bounded runtime-record lookup surface: all 53 direct lookup calls, the 44-call exact 0x7F00 partition across 41 width-aware hot/cold entry CFGs, all seven local stack pointer stores with no address-taken descriptor escape, all six direct blob+0x04 call escapes, both Factory CreateBatchedEntities routes into the full-blob copy path, the third component-grouping consumer, zero direct +0x14 reads/non-stack pointer stores/returns, and rejection of callback A's ECS-column +0x14 lookalike",
                "the direct-distance and scaled-metric HGTree LOD interval equations",
                "the six-way HGTree LOD job dispatch segment",
                "the HGTree LOD dispatch packet and payload layouts",
                "the parent/per-ArtTag LOD-bias encodings and per-view lodBias multiplier",
                "the ArtTag LODStreamingOffset producer, payload copy, signed add, and clamp",
                "the HGTreeComponentProxy-to-native-type name, namespace, and module identity",
                "the IL2CPP HGTreeComponent.get_id return value 80 and its separation from component id 67",
                "the UInt64 StreamingComponentType values HLODGroup=bit11, HGTree=bit41, and Count=43",
                "the 43-slot Streaming converter registry, bsf(typeMask) lookup, and 0x308-byte slot stride",
                "the complete nine-call managed Mono-component binding set and the absence of HGTree bit 41",
                "the 117-object installed HGMeshRendererData corpus, its 1,449 descriptors, and the absence of component id 67",
                "the UnityPlayer native serialized class IDs for HGTree, HGTreeData, HGMeshRenderer, and HGMeshRendererData",
                "the controlled full-VFS 117-object positive gate and zero top-level HGTree/HGTreeData object census",
                "the StreamingSceneV2 managed/native Create route, icall 621, path builder, request callback, and interleaved-token LZ4 decoder",
                "all 83 StreamingMapConfig roots and their one-to-one StreamingChunkInfo coverage",
                "the full 51,012-file main Streaming payload census and absence of HGTree bit 41 and HLODGroup bit 11",
                "StreamingSceneV2 native entity/archetype root fields 6/7 and their descriptor/initial-data layout",
                "the hash-pinned generic native ECS archetype initial-data copy at 0x1801F95E0",
                "the exact 83-map component-67/type-0-or-9 owner sets and byte-identical repeated initial records",
                "all component-67 serialized lodCount values and 102 cumulative renderer-range patterns",
                "all 1,305,818 component-67 +0x06 reserved words serialized as zero",
                "all 25 direct component-67 accessor calls, 21 logical caller bodies, and the reserved-word access boundary",
                "the 1,576-file DynamicStreaming init/stream census with only tag-2 records and no component entries",
                "the separate DynamicStreaming gameplay-tree route with 2,828 TreeRootComp rows and enum identities Tree=11/TreeRootComp=64",
                "the IL2CPP RenderObjectLODInfoComponent.get_id return value 6 and its separation from component id 67",
                "the ECS numeric-component-id to two-qword archetype-mask equation",
                "the direct all-LOD or terminal-LOD HGTree availability initializer",
                "the retraction of the out-of-range index 10320 Animator misbinding",
                "the correction that HGTreeRenderer is not evidence for the scheduled cull-view +0x18 equation",
            ],
            "captureOnly": [
                "target-frame LightCullResult pointer, count, and 148-byte rows",
                "unrelated active native lights",
                "arbitrary/asymmetric final selected-view planes",
                "the concrete per-pass callers and values supplied to HGTree CreateRendererList's renderFlagsMask/renderFlagsValue ABI",
                "the standalone native component type name for component 67",
                "any separate consumer of the forwarded sceneCullingMask slot",
                "future or separately delivered IFix/settings payloads",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--extracted-root",
        type=Path,
        default=DEFAULT_EXTRACTED_ROOT,
        help="AnimeStudio TextAsset output containing the targeted settings files",
    )
    args = parser.parse_args()

    rendered = json.dumps(build_audit(args.extracted_root), indent=2) + "\n"
    if args.check:
        require("generated_output_exists", OUTPUT.is_file(), True, OUTPUT)
        require(
            "generated_output",
            OUTPUT.read_text(encoding="utf-8"),
            rendered,
            OUTPUT,
        )
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        "Light-cull audit passed: desktop cap=256; native producer/handoff, "
        "scheduled cull-view layout, complete CullView consumer surface with "
        "write-only screen threshold, dispatch predicates, dedicated HGTree "
        "type identity/id-80 registration lifecycle/runtime transform, "
        "HGMeshRendererData Material/main-Mesh/shadow-proxy map fields, "
        "shadow-proxy GeometryHandle packing/lookup and CreateRendererList "
        "renderFlags ABI, and separate property flags, "
        "enabledLightModes producer/default/initializers and GPUDrivenRenderer "
        "V1/V2 default/PreZ consumer/filter routes, HGTree renderer-list variants, "
        "Factory blob-copy routes, independent renderer-entry pass mask, and "
        "complete direct renderer-blob lookup/escape census, "
        "Streaming HGTree bit-41/43-slot converter registry, managed LOD-info id 6, "
        "component-67 separation and native Render/MergedRenderCollider ownership, "
        "serialized LOD-count/range/reserved-word initial-data production and native copy, "
        "managed-converter, HGMeshRendererData, and top-level HGTree/HGTreeData exclusions, "
        "ECS component mask and LOD-state equations, "
        "LODCrossFadeConfig "
        "bias packet, ArtTag LOD bias/streaming-offset controls, mask order, "
        "16-byte result, and 148-byte capture-row ABI closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
