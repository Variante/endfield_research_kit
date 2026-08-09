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
    "do_ecs_culling_body": "bcbfa96588743701a5d1992256c68f193e624dc01ead47e86b80eb0a7653151b",
    "cull_lights_injected_body": "90fe3e38d69fd29a65c4fdc3e472199d9fa0e67733d220875cff6925b4f25503",
    "cull_lights_internal_body": "552b658de9533980b813706c457551aa508c0a2d0fa30dd9817a166898c73564",
    "cull_lights_body": "457b6e62ebd5b4aab211b552da8b3f22a8156c7005a88c21c65f223903ee7245",
    "get_visible_lights_body": "f2d8a942ff09c2a07ee960760bf7e3a2c9bd878955fd7bb0d709c3e1fca3ab66",
    "setup_state_body": "76dcba4f0f93db50a7fdbf2f3fed3084229be907526ff6a33c9556496a81ceab",
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

UNITY_DISPATCH_CULL_JOBS_ICALL_INDEX = 3315
UNITY_DISPATCH_CULL_JOBS_ICALL_VA = 0x1800FAFC0
UNITY_DISPATCH_CULL_JOBS_ICALL_NAME = (
    "UnityEngine.HyperGryph.HGCullingSystem::DispatchBatchCullingJobs"
)

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
    "renderer_candidate_serializer": (
        0x18106FD70,
        0x1DC,
        "285455b0862cf34c1b0aaeb7b198489c9dc805d7e3921424b07d75239fdfe0f2",
    ),
    "renderer_candidate_deserializer": (
        0x1810701C0,
        0x26C,
        "9ad71baa660f3e2547417faad460a8667bc22e98f4c2360c7f8f8a4e2cff3d72",
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
}

UNITY_RENDERER_CANDIDATE_FIELD_NAMES = {
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


def read_native_method_bodies(game_assembly: Path = GAME_ASSEMBLY) -> dict[str, bytes]:
    bodies: dict[str, bytes] = {}
    with game_assembly.open("rb") as stream:
        for name, spec in NATIVE_METHODS.items():
            stream.seek(int(spec["fileOffset"]))
            bodies[name] = stream.read(int(spec["sizeBytes"]))
    return bodies


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
    for label, (
        virtual_address,
        size_bytes,
        expected_hash,
    ) in UNITY_SCHEDULED_CULL_BODIES.items():
        body = image.read(virtual_address, size_bytes)
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

    field_names = []
    for virtual_address, expected_name in (
        UNITY_RENDERER_CANDIDATE_FIELD_NAMES.items()
    ):
        actual_name = image.cstring(virtual_address)
        require(
            "unity_scheduled_cull_renderer_candidate_field_name",
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
        "rendererCandidateRecord": {
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
            "evidence": (
                "independent retail serializer and deserializer offsets plus "
                "embedded native field names"
            ),
            "fieldNameEvidence": field_names,
            "notCullViewRecord": True,
        },
        "evidenceBoundary": {
            "closed": [
                "DispatchBatchCullingJobs internal-call binding and native call chain",
                "camera-type predicate selection",
                "standard six-plane AABB predicate",
                "cameraType 0x80 sphere/distance predicate",
                "absence of cull-view +0x18 from those two selected predicates",
                "the distinct 28-byte renderer candidate LOD record layout",
            ],
            "open": [
                "later renderer/entity LOD comparison that combines view and candidate screen thresholds",
                "whether the installed zero view threshold makes that later gate unconditional",
                "target-frame runtime overrides and final survivor rows",
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
        "schema": "endfield.recovered-light-cull-cap.v4",
        "status": "installed_cap_cull_view_dispatch_predicates_and_capture_abi_source_closed",
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
            "predicate; neither reads cull-view +0x18. A separate 28-byte renderer "
            "candidate record owns LOD max/min squared at +0x14/+0x18. The later "
            "view/candidate screen-threshold equation, target-frame pointer/count, "
            "and unrelated live native lights remain capture-only."
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
                "the distinct 28-byte renderer candidate LOD record with max/min squared fields at +0x14/+0x18",
            ],
            "captureOnly": [
                "target-frame LightCullResult pointer, count, and 148-byte rows",
                "unrelated active native lights",
                "arbitrary/asymmetric final selected-view planes",
                "the later renderer/entity equation combining view and candidate screen-size thresholds",
                "whether the installed zero view threshold makes that later gate unconditional",
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
        "scheduled cull-view layout, dispatch predicates, distinct renderer "
        "LOD record, mask order, 16-byte result, and 148-byte capture-row ABI "
        "closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
