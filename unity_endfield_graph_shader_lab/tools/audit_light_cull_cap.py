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

UNITY_HGTREE_BODIES = {
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

UNITY_HGTREE_FLOAT_CONSTANTS = {
    "scaled_lod_forced_distance_squared": (0x181CF22E4, 0x3F800000),
    "scaled_lod_distance_squared_floor": (0x181D18140, 0x38D1B717),
}

UNITY_HGTREE_FIELD_NAMES = {
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
                "a separate later system may still copy or consume the view "
                "threshold outside this dispatch stage"
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
                "the later renderer/entity consumer, if any, of cull-view +0x18",
                "whether the installed zero view threshold makes that later gate unconditional",
                "target-frame runtime overrides and final survivor rows",
            ],
        },
        "verifiedBodies": bodies,
        "verifiedInstructionSlices": slices,
    }


def validate_unity_hgtree_renderer_boundary(
    image: PEImage,
    managed_hgtree_component: dict[str, object] | None = None,
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
        "registrationInternalCall": {
            "index": UNITY_HGTREE_REGISTER_BATCH_GROUP_ICALL_INDEX,
            "name": register_name,
            "targetVirtualAddress": f"0x{register_target:X}",
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
        "lodControlInternalCalls": {
            "cullingSystem": lod_bias_icalls,
            "lodStreamingSystem": lod_streaming_offset_icalls,
        },
        "callChain": [
            "0x1801D9D10 HGTreeRender::CreateRendererList binding",
            "0x18107EE40 renderer-list core",
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
                    {"offset": "0x04", "sizeBytes": 4, "source": "batchKey"},
                    {"offset": "0x08", "sizeBytes": 4, "source": "renderFlags"},
                    {"offset": "0x0C", "sizeBytes": 12, "initialValue": 0},
                ],
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
                "any separate post-dispatch copy or consumer of cull-view +0x18",
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
        "schema": "endfield.recovered-light-cull-cap.v20",
        "status": "installed_cap_component67_reserved_word_closed",
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
            "predicate; neither reads cull-view +0x18. The previously separate "
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
            "interval are now closed. The dispatch packet/payload layouts, "
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
            "Any separate post-dispatch cull-view +0x18 consumer, remaining "
            "loader-registration record +0x0C..+0x17 zero-field roles, the "
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
                "HGTreeInstance ownership and the exact 28-byte HGTreeRenderer LOD record",
                "the dedicated 729-entry HyperGryph internal-call name/function table pair",
                "the HGTreeRender CreateRendererList binding, core, scheduler, and selected runtime callbacks",
                "the HGTreeRender RegisterTreeBatchGroup binding and registration core",
                "the HGTreeRenderer serialized-to-runtime record and LOD float2 mapping",
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
                "any separate post-dispatch copy or consumer of cull-view +0x18",
                "whether the installed zero view threshold makes that later gate unconditional",
                "the loader-registration runtime record +0x0C..+0x17 zero-field roles",
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
        "scheduled cull-view layout, dispatch predicates, dedicated HGTree "
        "type identity/id-80 registration lifecycle/runtime transform, "
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
