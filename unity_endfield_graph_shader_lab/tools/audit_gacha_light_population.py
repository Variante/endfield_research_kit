#!/usr/bin/env python3
"""Audit the installed Zhuangfy gacha authored-light population boundary."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import struct
import subprocess
import tempfile
import winreg
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
UNITY_PLAYER = GAME_ROOT / "UnityPlayer.dll"
GLOBAL_METADATA = GAME_ROOT / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
GLOBAL_GAME_MANAGERS = GAME_ROOT / "Endfield_Data/globalgamemanagers"
ROOM_CHUNK = (
    GAME_ROOT
    / "Endfield_Data/StreamingAssets/VFS/7064D8E2/"
    "8B805A424FFA2FC7F4DE0BC016C09009.chk"
)
CHARINFO_CHUNK = (
    GAME_ROOT
    / "Endfield_Data/StreamingAssets/VFS/7064D8E2/"
    "62EB15DCD74A3348E244B9B068AB9694.chk"
)
LUA_SOURCE = (
    REPO_ROOT
    / "scratch/animestudio/gacha_light_population/lua_dump/Lua/Data/LuaScripts/"
    "UI/Panels/GachaChar/GachaCharCtrl.lua"
)
UI_CONST_SOURCE = (
    REPO_ROOT
    / "scratch/animestudio/gacha_aspect_constraints/lua_dump/Lua/Data/LuaScripts/"
    "Const/UIConst.lua"
)
CHARACTER_TABLE = (
    REPO_ROOT / "export_full/structured/StreamingAssets/Table/CharacterTable.json"
)
GACHA_CHAR_TABLE = (
    REPO_ROOT / "export_full/structured/StreamingAssets/Table/GachaCharInfoTable.json"
)
ROOM_HIERARCHY = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_room_lights/room_light_hierarchy.json"
)
ROOM_LIGHT_ROOT = (
    REPO_ROOT / "scratch/animestudio/zhuangfy_gacha_room_lights/json/Light"
)
CHAR_JSON_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/gacha_light_population/character_light_json"
)
CHAR_DUMP_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/gacha_light_population/character_light_dump"
)
OPERATOR_LIGHTS = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "RenderParameters/operator_lights.json"
)
NATIVE_CULL_REPORT = (
    REPO_ROOT
    / "scratch/reverse_engineering/clustered_light_native_culling/report.json"
)
GACHA_CULL_VIEW_AUDIT = (
    REPO_ROOT / "scratch/reverse_engineering/gacha_light_cull_view/audit.json"
)
GACHA_SELECTED_LIST_AUDIT = (
    REPO_ROOT / "scratch/reverse_engineering/gacha_light_selected_list/audit.json"
)
ACTOR_TIMELINE_AUDIT = (
    REPO_ROOT
    / "scratch/reverse_engineering/zhuangfy_gacha_actor_timeline/"
    "actor_timeline_audit.json"
)
ZHUANGFY_MANIFEST = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/"
    "zhuangfy_ui_recovery_manifest.json"
)
ACTOR_TIMELINE_JSON_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_actor_timeline/"
    "full_timeline_export_json/MonoBehaviour"
)
ACTOR_TRACK = ACTOR_TIMELINE_JSON_ROOT / "Animation Track_pC647253461C288D6.json"
ACTOR_PLAYABLE_ENTRANCE = (
    ACTOR_TIMELINE_JSON_ROOT / "AnimationPlayableAsset_pA69BB75A314C88D6.json"
)
ACTOR_PLAYABLE_LOOP = (
    ACTOR_TIMELINE_JSON_ROOT / "AnimationPlayableAsset_p1E75C442588C88D6.json"
)
ACTOR_ANIMATION_ROOT = (
    REPO_ROOT
    / "scratch/character_ui_import/characters/chr_0030_zhuangfy/"
    "animation_scopes/all-ui"
)
ACTOR_CLIP_ENTRANCE = (
    ACTOR_ANIMATION_ROOT
    / "animation_clips/AnimationClip/A_actor_zhuangfy_gacha_pE87492C48C117993.json"
)
ACTOR_CLIP_LOOP = (
    ACTOR_ANIMATION_ROOT
    / "animation_clips/AnimationClip/"
    "A_actor_zhuangfy_ui_overview_loop_01_pDCA810D9F64A7993.json"
)
ACTOR_SAMPLE_ENTRANCE = ACTOR_ANIMATION_ROOT / "samples/A_actor_zhuangfy_gacha.json"
ACTOR_SAMPLE_LOOP = (
    ACTOR_ANIMATION_ROOT / "samples/A_actor_zhuangfy_ui_overview_loop_01.json"
)
GACHA_ROOM_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_start_order/gacharoom_raw_dump/"
    "GameObject/GachaRoom_p6BA6C284A446ADE0.json"
)
TIMELINE_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_start_order/gacharoom_raw_dump/"
    "GameObject/TimelineRoot_p0D60F289A5FBADE0.json"
)
ACTOR_PREFAB_TRANSFORM_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_start_order/"
    "zhuangfy_prefab_dump_tree/Transform"
)
ACTOR_PREFAB_TRANSFORMS = {
    "gacha_char_zhuangfy": ACTOR_PREFAB_TRANSFORM_ROOT / "Transform#525_pCD407D5AEAC4AD17.txt",
    "Actor": ACTOR_PREFAB_TRANSFORM_ROOT / "Transform#612_pD95B4B7B5557AD17.txt",
    "chr_0030_zhuangfy_uimodel": ACTOR_PREFAB_TRANSFORM_ROOT / "Transform#1228_p340F1304A6CFAD17.txt",
    "Root": ACTOR_PREFAB_TRANSFORM_ROOT / "Transform#1596_p6A9DD478123EAD17.txt",
}
ACL_SAMPLER = REPO_ROOT / "tools/endfield_acl_sampler/bin/endfield_acl_sampler.exe"
ACL_SAMPLER_SOURCE = REPO_ROOT / "tools/endfield_acl_sampler/endfield_acl_sampler.cpp"
ROTATEHOUSE = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_start_order/gacharoom_raw_dump/"
    "GameObject/rotatehouse_pB2306755E2A9ADE0.json"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/gacha_light_population_recovery.json"
)

EXPECTED_HASHES = {
    "gameAssembly": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    "unityPlayer": "b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2",
    "globalMetadata": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    "globalGameManagers": "191619377ff312b785aae10faec8a75e39caf1ba60016ad08eff040b8c54f20d",
    "roomChunk": "4b4ae868dc333fd5b22fc30e667d3156675178bfffd57b93e0e4b625c89f0b26",
    "charInfoChunk": "db94219ee4f522a824c32ec979c2dc5bfd7b1013b4e45c18b77fb3ae4809694e",
    "gachaLua": "94815321515ebf7d4067f60f2f6e2a1d25611bc2e40f712e22cd40a6d159ae19",
    "uiConstLua": "a2b5798cbf4500e0a3e12e2747ab04b412efe1789b3198d19557f868415e7ea5",
    "characterTable": "50392af8d8c93854b99e5342b4b70c049b68d2da306e366325d749ba77bf4779",
    "gachaCharTable": "05c1b414bab1f3fbb7a9a983c7193c40ccf0884d6cb50edf7469d8ee05dd50fb",
    "roomHierarchy": "bf26b44919a7563bd6c7ee137346d7f8880bb1a32911a8972c586b2bb0c87db9",
    "operatorLights": "706f66b89aa209371df50956e9f1525026ce4a8a1f19a85210fc35d3b2c23ac8",
    "nativeCullReport": "f7b6e9b6407bb26555491c13f9895b712a9219218c19ac07efd56d7c947d7d7e",
    "gachaCullViewAudit": "4717ddd564f0eee2e1742024660e233e09865b4a301a4b7566aaca6844011dc4",
    "gachaSelectedListAudit": "7b3624526a77102fb075cdc1ad98277eb6746b5a1853faa1fd2ad2032951e1b3",
    "rotatehouse": "3cac5172e91bb3cddf1a8c6db8e8550620abbfb0c957905f39538b8c97baded4",
    "actorTimelineAudit": "575b8b4967cf3458e93b6e883679a19bb985b0888a1d8fde5f81876bf14dfdee",
    "zhuangfyManifest": "63bd1cbc2de2acfa8cb507d1186dec736cbdbaacf4c861e803b802a04b1e8ae9",
    "actorTrack": "2b37d07f4a2b6964a7cf66d10de2bd41211af8e78ceba1ce03c2647eecfece31",
    "actorPlayableEntrance": "55b80868b750786b07c38dff5bc71fa0517b950acbb669d8f68acf1d22461e1e",
    "actorPlayableLoop": "2b24eed5a1488a722e516730fa557e904259213f3f655b79240749aa1f558bed",
    "actorClipEntrance": "5a977b29300ba8991bad2c5bdad82eed99c38d07722ebaa2b649061818dc0803",
    "actorClipLoop": "387593a1d02d8d02232101839c1e8e73f0dc30788e5f17deb2798cb2ce5048f7",
    "actorSampleEntrance": "5271fee6c466d8a87a743d65c9ab9944c10e16ea9ebab2fe7aab070bea3fc2d5",
    "actorSampleLoop": "3bd36a3968fb043e1221aa9f54932a40100c8c9f7f2df533c3df1f28f410a80e",
    "gachaRoomRoot": "4b90b2c1b0cf270b19d44a48d07216d072548e10c3b49e9a0759d0a0faa1ae8f",
    "timelineRoot": "7af46240c5880c8f38b71df0cf3a743b888827704cfdc4357240cc3561fd37b2",
    "actorPrefabRoot": "bd22ee727957046e5ddcfa49f82e8c2a461745ac10289914d329afabafe22a88",
    "actorContainer": "28f697ca93516ed65065f6925b546dbc0c46fc9f4d7b45d47356596d1320782e",
    "actorModel": "5a68fb202e1dfd72d41f8247d3d2f54a46bbed6f53ada7638a97dc95650283bb",
    "actorSkeletonRoot": "4a98c8341b807f830f7ec13c1a8c325e2910f9bc9dd155313b455d02ab80563d",
    "aclSampler": "2805096f5df56d7a0f3790ded815955fc4227f2f8decf941d4a1e88e1ab586df",
    "aclSamplerSource": "c44bd1a08ecbf3ea4f46107d6faf084218fee7df33616fd59d44aaa4a797d1e2",
}

REGISTRY_KEY = r"Software\Hypergryph\Endfield"
RESOLUTION_VALUES = {
    "screenWidth": "Screenmanager Resolution Width_h182942802",
    "screenHeight": "Screenmanager Resolution Height_h2627697771",
    "videoWidth": "video_resolution_width_h583690364",
    "videoHeight": "video_resolution_height_h2517654917",
}

UNITY_NATIVE_REGIONS = {
    "initial_light_aabb_frustum_test": (
        0x181050470,
        0x3F1,
        "0f2359a78c27699a894d4106fa9bb5b1277d021a6c75d3e9a2fec41252f450e5",
    ),
    "spot_cone_aabb_builder": (
        0x18034CE46,
        0x740,
        "eb5c9bd7f97cfaa2bf560af4ed6e5d795362731514ebba0dcbda106aef6af7f8",
    ),
    "authored_obb_corner_builder": (
        0x18104C270,
        0x612,
        "ef5638a695fb5007113b432037bd23d9b56e3acd96a802a69441d475d1c7dd32",
    ),
    "spot_cone_plane_test": (
        0x1810516D0,
        0x34D,
        "eb053dc111374f16a856b187471298699f3df4189928ea5ecfda778d0c70fc20",
    ),
    "authored_obb_plane_test": (
        0x181052329,
        0x1D1,
        "39240124eedac93d1dce993460270242f39c73582027ba247775211decb17550",
    ),
}

GAME_NATIVE_REGIONS = {
    "GameSetting._AddScreenResolution": (
        0x184498160,
        0x130,
        "17f0b8cf9ea2d13f740342cca50ca3fe68cf51bccead7a0e7cdaa6f459f90fcd",
    ),
    "GameSetting._AddScreenResolution_portrait_swap": (
        0x1852BFA54,
        8,
        "56e0c82b57c29be8ec5add44328d1e313b0a2f507df6ea39ad7968b97adcf9d3",
    ),
}

ROOM_SURVIVOR_SUBSEQUENCE = [
    "Spot Light (12)",
    "Spot Light (19)",
    "Linear Light (12)",
    "Linear Light (13)",
    "Linear Light (14)",
    "Spot Light (17)",
    "Linear Light (15)",
    "Spot Light (18)",
    "Spot Light (9)",
    "Spot Light (11)",
    "Spot Light (10)",
]

CHARACTER_SURVIVORS = [
    "FogLight_1 (2)",
    "Point Light_overview (2)",
    "RimLight_2 (4)",
    "SpecLight_1 (8)",
    "RimLight_2 (5)",
    "SpecLight_1 (11)",
]

KNOWN_AUTHORED_SURVIVOR_ORDER = [
    "SpecLight_1 (8)",
    "RimLight_2 (5)",
    "SpecLight_1 (11)",
    "Point Light_overview (2)",
    "RimLight_2 (4)",
    "FogLight_1 (2)",
    *ROOM_SURVIVOR_SUBSEQUENCE,
]

EXPECTED_LAYERS = [
    "Default", "TransparentFX", "Ignore Raycast", "Fog", "Water", "UI",
    "Walkable", "Climbable", "PostProcessVolume", "Trigger", "UIPP",
    "Character", "Enemy", "UIModel", "Building", "UIInteract", "WorldUI",
    "Projectile", "AbilityEntity", "Interactive", "Terrain", "IK", "NPC", "",
    "UltimateShow", "BattleShape", "Physics", "DropItem", "Hide", "Liquid",
    "Gacha", "",
]

NATIVE_METHODS = {
    "CharUIModelMono.InitLightFollower": {
        "methodIndex": 49713,
        "virtualAddress": "0x186C25FA0",
        "fileOffset": 0x6C245A0,
        "sizeBytes": 220,
        "sha256": "9259bd577548c38e5eb44b1c6b02d5379a448048d888ff646a866a398d7cb4a1",
    },
    "CharUIModelMono._GetFollowableNode": {
        "methodIndex": 49714,
        "virtualAddress": "0x186C29FD0",
        "fileOffset": 0x6C285D0,
        "sizeBytes": 116,
        "sha256": "c0f00babeb5c1f6d717788a099c5cfc6d824a0e633149b1805f16e7e15ef817f",
    },
    "CharInfoLightFollower.InitCharLightFollower": {
        "methodIndex": 16388,
        "virtualAddress": "0x1872ECF0C",
        "fileOffset": 0x72EB50C,
        "sizeBytes": 220,
        "sha256": "fd263394528933a30655f5a52b42c790dbce0f91ed2475619a01ccff25f80379",
    },
    "CharInfoLightFollower.LateTick": {
        "methodIndex": 16387,
        "virtualAddress": "0x1872ECFE8",
        "fileOffset": 0x72EB5E8,
        "sizeBytes": 188,
        "sha256": "d274f9b13d6f0275e4791bee11ba6a34980fc30391dfcfbe6f12369e57707bd8",
    },
    "CharInfoLightFollower._FollowWithFixedOffset": {
        "methodIndex": 16389,
        "virtualAddress": "0x1872ED108",
        "fileOffset": 0x72EB708,
        "sizeBytes": 264,
        "sha256": "0eaa0ce1b9c6aa70feb71d85175be340ab7598bbfa1d4ba05644b252297cbc12",
    },
    "CharInfoLightFollower._FollowWithParent": {
        "methodIndex": 16390,
        "virtualAddress": "0x1872ED210",
        "fileOffset": 0x72EB810,
        "sizeBytes": 504,
        "sha256": "27fdafe4771dd013713e4ae37a2132e102e949a47f0047843d48d6092c01821d",
    },
}

EXPECTED_GROUPS = {
    "light_document": (114660774365865291, True, 6, 4, 6, {"0": 2, "2": 4}),
    "light_equip": (-4122620703443081909, False, 6, 1, 6, {"0": 2, "2": 4}),
    "light_overview": (-1840922393885432501, False, 6, 4, 6, {"0": 2, "2": 4}),
    "light_skill": (-736313027726760629, False, 8, 0, 7, {"0": 3, "2": 5}),
    "light_upgrade": (7162434402683692363, False, 7, 5, 7, {"0": 2, "2": 5}),
    "light_weapon": (-2373901316435892917, False, 11, 0, 11, {"0": 1, "2": 10}),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(check: str, actual: object, expected: object, source: Path | str) -> None:
    if actual != expected:
        raise AssertionError(
            "Gacha light-population audit failed: "
            f"validator=gacha_light_population; check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verified_hash(name: str, path: Path) -> dict[str, object]:
    require(f"{name}_exists", path.is_file(), True, path)
    actual = sha256(path)
    require(f"{name}_sha256", actual, EXPECTED_HASHES[name], path)
    return {"sizeBytes": path.stat().st_size, "sha256": actual}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def float_evidence(value: float) -> dict[str, object]:
    rounded = f32(value)
    return {
        "value": rounded,
        "bits": f"0x{struct.unpack('<I', struct.pack('<f', rounded))[0]:08X}",
    }


class PEImage:
    def __init__(self, path: Path) -> None:
        self.data = path.read_bytes()
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        require("pe_signature", self.data[pe : pe + 4], b"PE\0\0", path)
        count = struct.unpack_from("<H", self.data, pe + 6)[0]
        optional_size = struct.unpack_from("<H", self.data, pe + 20)[0]
        optional = pe + 24
        require("pe64_magic", struct.unpack_from("<H", self.data, optional)[0], 0x20B, path)
        self.image_base = struct.unpack_from("<Q", self.data, optional + 24)[0]
        cursor = optional + optional_size
        self.sections: list[tuple[int, int, int, int]] = []
        for _ in range(count):
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
                "<IIII", self.data, cursor + 8
            )
            self.sections.append((virtual_address, virtual_size, raw_offset, raw_size))
            cursor += 40

    def read(self, virtual_address: int, size: int) -> bytes:
        rva = virtual_address - self.image_base
        for section_va, virtual_size, raw_offset, raw_size in self.sections:
            if section_va <= rva < section_va + max(virtual_size, raw_size):
                delta = rva - section_va
                require("pe_region_in_raw_section", delta + size <= raw_size, True, hex(virtual_address))
                return self.data[raw_offset + delta : raw_offset + delta + size]
        raise AssertionError(
            "Gacha light-population audit failed: "
            "validator=gacha_light_population; check=pe_virtual_address; "
            f"source={virtual_address:#x}; expected='mapped section'; actual='unmapped'"
        )


def validate_native_regions(path: Path, regions: dict[str, tuple[int, int, str]]) -> list[dict[str, object]]:
    image = PEImage(path)
    rows = []
    for name, (virtual_address, size, expected_hash) in regions.items():
        body = image.read(virtual_address, size)
        actual = hashlib.sha256(body).hexdigest()
        require(f"native_region_{name}_sha256", actual, expected_hash, path)
        rows.append(
            {
                "name": name,
                "virtualAddress": f"0x{virtual_address:X}",
                "sizeBytes": size,
                "sha256": actual,
            }
        )
    return rows


def validate_installed_resolution(values: dict[str, int], source: Path | str) -> dict[str, object]:
    expected = {name: 3840 if "Width" in name else 2160 for name in values}
    require("installed_resolution_values", values, expected, source)
    require("installed_resolution_pairs_match", (values["screenWidth"], values["screenHeight"]), (values["videoWidth"], values["videoHeight"]), source)
    width = values["videoWidth"]
    height = values["videoHeight"]
    return {
        "source": f"HKCU\\{REGISTRY_KEY}",
        "valueNames": RESOLUTION_VALUES,
        "screenManager": {"width": values["screenWidth"], "height": values["screenHeight"]},
        "gameVideo": {"width": width, "height": height},
        "aspect": float_evidence(width / height),
        "scope": "read-only selected state for this installed-client fixture, not a universal supported-aspect claim",
    }


def read_installed_resolution() -> dict[str, object]:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        values = {name: int(winreg.QueryValueEx(key, value_name)[0]) for name, value_name in RESOLUTION_VALUES.items()}
    return validate_installed_resolution(values, f"HKCU\\{REGISTRY_KEY}")


def vector_values(rows: list[dict[str, object]]) -> list[float]:
    return [float(row["value"]) for row in rows]


def quaternion_multiply(a: list[float], b: list[float]) -> list[float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [
        f32(aw * bx + ax * bw + ay * bz - az * by),
        f32(aw * by - ax * bz + ay * bw + az * bx),
        f32(aw * bz + ax * by - ay * bx + az * bw),
        f32(aw * bw - ax * bx - ay * by - az * bz),
    ]


def quaternion_rotate(q: list[float], value: list[float]) -> list[float]:
    x, y, z, w = q
    vx, vy, vz = value
    return [
        f32((1.0 - 2.0 * (y * y + z * z)) * vx + 2.0 * (x * y - z * w) * vy + 2.0 * (x * z + y * w) * vz),
        f32(2.0 * (x * y + z * w) * vx + (1.0 - 2.0 * (x * x + z * z)) * vy + 2.0 * (y * z - x * w) * vz),
        f32(2.0 * (x * z - y * w) * vx + 2.0 * (y * z + x * w) * vy + (1.0 - 2.0 * (x * x + y * y)) * vz),
    ]


def vector_add(left: list[float], right: list[float]) -> list[float]:
    return [f32(left[index] + right[index]) for index in range(3)]


def vector_scale_components(left: list[float], right: list[float]) -> list[float]:
    return [f32(left[index] * right[index]) for index in range(3)]


def compose_transform(
    parent: tuple[list[float], list[float], list[float]],
    local: tuple[list[float], list[float], list[float]],
) -> tuple[list[float], list[float], list[float]]:
    parent_position, parent_rotation, parent_scale = parent
    local_position, local_rotation, local_scale = local
    scaled = vector_scale_components(parent_scale, local_position)
    return (
        vector_add(parent_position, quaternion_rotate(parent_rotation, scaled)),
        quaternion_multiply(parent_rotation, local_rotation),
        vector_scale_components(parent_scale, local_scale),
    )


def dot(a: list[float], b: list[float]) -> float:
    return f32(a[0] * b[0] + a[1] * b[1] + a[2] * b[2])


def settled_frustum_planes(camera: dict[str, Any], aspect: float) -> list[tuple[str, list[float], float]]:
    position = vector_values(camera["position"])
    right = vector_values(camera["axes"]["right"])
    up = vector_values(camera["axes"]["up"])
    forward = vector_values(camera["axes"]["forward"])
    vertical_scale = float(camera["verticalProjectionScale"]["value"])
    horizontal_scale = f32(vertical_scale / aspect)
    normals = [
        ("left", [f32(forward[i] + horizontal_scale * right[i]) for i in range(3)]),
        ("right", [f32(forward[i] - horizontal_scale * right[i]) for i in range(3)]),
        ("bottom", [f32(forward[i] + vertical_scale * up[i]) for i in range(3)]),
        ("top", [f32(forward[i] - vertical_scale * up[i]) for i in range(3)]),
    ]
    planes = [(name, normal, f32(-dot(normal, position))) for name, normal in normals]
    base = f32(-dot(forward, position))
    planes.append(("near", forward, f32(base - float(camera["near"]["value"]))))
    planes.append(("far", [f32(-value) for value in forward], f32(-base + float(camera["far"]["value"]))))
    return planes


def zxy_rotation_axes(degrees: dict[str, float]) -> list[list[float]]:
    # Unity rotation order 4: Z, then X, then Y (R = Ry * Rx * Rz).
    z, x, y = [math.radians(float(degrees[key])) for key in ("z", "x", "y")]
    cz, sz = math.cos(z), math.sin(z)
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    rz = [[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]]
    rx = [[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]]
    ry = [[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]]

    def multiply(left: list[list[float]], right_matrix: list[list[float]]) -> list[list[float]]:
        return [[f32(sum(left[row][k] * right_matrix[k][column] for k in range(3))) for column in range(3)] for row in range(3)]

    return multiply(ry, multiply(rx, rz))


def aabb_margin(plane: tuple[str, list[float], float], center: list[float], extents: list[float]) -> float:
    _, normal, distance = plane
    return f32(dot(normal, center) + distance + sum(abs(normal[i]) * extents[i] for i in range(3)))


def obb_margin(plane: tuple[str, list[float], float], center: list[float], half: list[float], axes: list[list[float]]) -> float:
    _, normal, distance = plane
    support = sum(abs(sum(normal[i] * axes[i][column] for i in range(3))) * half[column] for column in range(3))
    return f32(dot(normal, center) + distance + support)


def sphere_margin(plane: tuple[str, list[float], float], center: list[float], radius: float) -> float:
    _, normal, distance = plane
    return f32(dot(normal, center) + distance + radius * math.sqrt(dot(normal, normal)))


def cone_margin(plane: tuple[str, list[float], float], apex: list[float], forward: list[float], length: float, half_angle_degrees: float) -> float:
    _, normal, distance = plane
    apex_signed = f32(dot(normal, apex) + distance)
    base_center = [f32(apex[i] + forward[i] * length) for i in range(3)]
    axis_dot = dot(normal, forward)
    perpendicular = math.sqrt(max(0.0, dot(normal, normal) - axis_dot * axis_dot))
    radius = length * math.tan(math.radians(half_angle_degrees))
    rim_signed = f32(dot(normal, base_center) + distance + radius * perpendicular)
    return max(apex_signed, rim_signed)


def validate_room_survivor_names(
    admitted: list[str], rejected: list[str], source: Path | str
) -> None:
    require("selected_aspect_room_survivors", admitted, ROOM_SURVIVOR_SUBSEQUENCE, source)
    require("selected_aspect_room_rejections", rejected, ["Spot Light (20)"], source)


def validate_character_survivor_names(
    admitted: list[str], rejected: list[str], source: Path | str
) -> None:
    require("selected_aspect_character_survivors", admitted, CHARACTER_SURVIVORS, source)
    require("selected_aspect_character_rejections", rejected, [], source)


def parse_aligned_string_array(data: bytes, offset: int) -> list[str]:
    require("layer_array_count_bounds", offset + 4 <= len(data), True, GLOBAL_GAME_MANAGERS)
    count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    rows = []
    for index in range(count):
        require(
            f"layer_{index}_length_bounds",
            offset + 4 <= len(data),
            True,
            GLOBAL_GAME_MANAGERS,
        )
        size = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        require(
            f"layer_{index}_data_bounds",
            offset + size <= len(data),
            True,
            GLOBAL_GAME_MANAGERS,
        )
        rows.append(data[offset : offset + size].decode("utf-8"))
        offset = (offset + size + 3) & ~3
    return rows


def validate_gacha_layer(
    ui_const_text: str,
    global_game_managers: Path,
    selected: dict[str, Any],
) -> dict[str, object]:
    compact = re.sub(r"\s+", " ", ui_const_text)
    require(
        "ui_const_gacha_layer",
        bool(re.search(r'GACHA_LAYER = Unity\.LayerMask\.NameToLayer\("Gacha"\)', compact)),
        True,
        UI_CONST_SOURCE,
    )
    layers = parse_aligned_string_array(global_game_managers.read_bytes(), 42220)
    require("installed_layer_names", layers, EXPECTED_LAYERS, global_game_managers)
    layer = layers.index("Gacha")
    record_mask = 1 << layer
    selected_mask = int(
        str(selected["recoveredNativeLayout"]["selectedCullView"]["cameraMask"]),
        16,
    )
    generic_record = selected["recoveredNativeLayout"]["genericRecord"]
    active_flags = int(str(generic_record["activeRoomInitializer"]["flags"]), 16)
    require(
        "generic_record_layer_mask_formula",
        generic_record["activeRoomInitializer"]["maskFormula"],
        "1 << GameObject.layer",
        GACHA_SELECTED_LIST_AUDIT,
    )
    require(
        "generic_record_active_flag",
        bool(active_flags & 1),
        True,
        GACHA_SELECTED_LIST_AUDIT,
    )
    require("gacha_layer_index", layer, 30, global_game_managers)
    require("gacha_layer_mask_gate", bool(record_mask & selected_mask), True, GACHA_SELECTED_LIST_AUDIT)
    return {
        "name": "Gacha",
        "index": layer,
        "recordMask": f"0x{record_mask:08X}",
        "activeRecordFlags": f"0x{active_flags:08X}",
        "selectedViewMask": f"0x{selected_mask:08X}",
        "maskGatePasses": True,
        "installedLayerArrayOffset": 42220,
        "installedLayerCount": len(layers),
    }


def validate_lua_contract(text: str, source: Path | str) -> dict[str, object]:
    compact = re.sub(r"\s+", " ", text)
    checks = {
        "characterLightPath": (
            r'LoadGameObject\(string\.format\("Assets/Beyond/DynamicAssets/Gameplay/'
            r'Prefabs/CharInfo/AdditionalLights/light_%s\.prefab", charId\)\)'
        ),
        "overviewSelector": r'local isTarget = childTrans\.name == "light_overview"',
        "childActivation": r"childTrans\.gameObject:SetActive\(isTarget\)",
        "followerInitialization": r"uiModelMono:InitLightFollower\(childTrans\)",
        "rarity6": r"sceneLight6Rarity\.gameObject:SetActive\(rarity >= 6\)",
        "rarity5": r"sceneLight5Rarity\.gameObject:SetActive\(rarity == 5\)",
        "rarity4": r"sceneLight4Rarity\.gameObject:SetActive\(rarity <= 4\)",
        "characterCreation": (
            r"local charObj = CSUtils\.CreateObject\(prefab, "
            r"self\.m_phase\.m_roomObjItem\.view\.timelineRoot\)"
        ),
        "lightParent": r"local lightObj = CSUtils\.CreateObject\(lightPrefab, charObj\.transform\)",
        "recursiveGachaLayer": r"charObj:SetLayerRecursive\(UIConst\.GACHA_LAYER\)",
    }
    for name, pattern in checks.items():
        require(f"lua_{name}", bool(re.search(pattern, compact)), True, source)
    selector_block = re.search(
        r'local isTarget = childTrans\.name == "light_overview" '
        r"childTrans\.gameObject:SetActive\(isTarget\) if isTarget then "
        r"uiModelMono:InitLightFollower\(childTrans\) end",
        compact,
    )
    require("lua_selector_block_order", bool(selector_block), True, source)
    hierarchy_order = re.search(
        r"local charObj = CSUtils\.CreateObject\(prefab, "
        r"self\.m_phase\.m_roomObjItem\.view\.timelineRoot\).*?"
        r"local lightObj = CSUtils\.CreateObject\(lightPrefab, charObj\.transform\).*?"
        r"uiModelMono:InitLightFollower\(childTrans\).*?"
        r"charObj:SetLayerRecursive\(UIConst\.GACHA_LAYER\)",
        compact,
    )
    require("lua_character_light_layer_order", bool(hierarchy_order), True, source)
    return {
        "characterLightPrefabEquation": (
            "Assets/Beyond/DynamicAssets/Gameplay/Prefabs/CharInfo/"
            "AdditionalLights/light_<charId>.prefab"
        ),
        "selectedChild": "light_overview",
        "otherDirectChildrenActive": False,
        "selectedChildActive": True,
        "initLightFollowerOnSelectedChild": True,
        "characterParent": "GachaRoom/TimelineRoot",
        "lightPrefabParent": "character root",
        "recursiveLayerAssignment": "UIConst.GACHA_LAYER after follower initialization",
        "roomRarityRules": {
            "SceneLight6Rarity": "rarity >= 6",
            "SceneLight5Rarity": "rarity == 5",
            "SceneLight4Rarity": "rarity <= 4",
        },
    }


def path_id_from_name(path: Path) -> int:
    match = re.search(r"_p([0-9A-Fa-f]{16})\.", path.name)
    if not match:
        raise AssertionError(
            "Gacha light-population audit failed: "
            f"validator=gacha_light_population; check=path_id_suffix; source={path}; "
            "expected='16 hexadecimal digits'; actual='missing'"
        )
    value = int(match.group(1), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def load_folder(root: Path, name: str) -> dict[int, tuple[Path, dict[str, Any]]]:
    result = {}
    for path in sorted((root / name).glob("*.json")):
        result[path_id_from_name(path)] = (path, load_json(path))
    return result


def read_active_self(path: Path) -> bool:
    match = re.search(
        r"^\s*bool m_IsActive = (True|False)\s*$",
        path.read_text(encoding="utf-8-sig"),
        re.M,
    )
    require("game_object_active_self_present", bool(match), True, path)
    return match.group(1) == "True" if match else False


def analyze_character_prefab(
    json_root: Path, dump_root: Path
) -> tuple[dict[str, object], list[dict[str, object]]]:
    game_objects = load_folder(json_root, "GameObject")
    transforms = load_folder(json_root, "Transform")
    lights = load_folder(json_root, "Light")
    behaviours = load_folder(json_root, "MonoBehaviour")
    require("character_game_object_count", len(game_objects), 51, json_root)
    require("character_transform_count", len(transforms), 51, json_root)
    require("character_light_count", len(lights), 44, json_root)
    require("character_behaviour_count", len(behaviours), 65, json_root)

    go_by_transform = {
        transform_id: int(data["m_GameObject"]["m_PathID"])
        for transform_id, (_, data) in transforms.items()
    }
    parent_by_go = {}
    transform_by_go = {}
    for transform_id, (_, data) in transforms.items():
        go_id = go_by_transform[transform_id]
        parent_by_go[go_id] = go_by_transform.get(int(data["m_Father"]["m_PathID"]))
        transform_by_go[go_id] = (transform_id, data)
    name_by_go = {go_id: data["m_Name"] for go_id, (_, data) in game_objects.items()}
    active_by_go = {}
    for go_id, (path, _) in game_objects.items():
        active_by_go[go_id] = read_active_self(
            dump_root / "GameObject" / path.with_suffix(".txt").name
        )

    def lineage(go_id: int) -> list[int]:
        result = []
        seen = set()
        while go_id is not None:
            require("character_transform_cycle", go_id in seen, False, json_root)
            seen.add(go_id)
            result.append(go_id)
            go_id = parent_by_go.get(go_id)
        return result

    def group_for(go_id: int) -> str:
        for ancestor in lineage(go_id):
            name = name_by_go[ancestor]
            if name.startswith("light_") and name != "light_chr_0030_zhuangfy":
                return name
        return "<root>"

    behaviour_by_go: dict[int, list[dict[str, Any]]] = defaultdict(list)
    behaviour_counts = Counter()
    for _, (_, data) in behaviours.items():
        fields = data["$animestudio"]["typeTreeFieldPaths"]
        if "followType:int" in fields:
            kind = "CharInfoLightFollower"
        elif "m_LightCharacterOnly:UInt8" in fields:
            kind = "HGLightExtension"
        else:
            kind = "other"
        behaviour_counts[kind] += 1
        behaviour_by_go[int(data["m_GameObject"]["m_PathID"])].append(
            {"kind": kind, "data": data}
        )
    require(
        "character_behaviour_kinds",
        dict(behaviour_counts),
        {"CharInfoLightFollower": 14, "HGLightExtension": 44, "other": 7},
        json_root,
    )

    group_counts: dict[str, Counter] = defaultdict(Counter)
    rows = []
    for light_id, (path, data) in lights.items():
        go_id = int(data["m_GameObject"]["m_PathID"])
        group = group_for(go_id)
        followers = [x for x in behaviour_by_go[go_id] if x["kind"] == "CharInfoLightFollower"]
        extensions = [x for x in behaviour_by_go[go_id] if x["kind"] == "HGLightExtension"]
        require("single_light_extension", len(extensions), 1, path)
        character_only = bool(extensions[0]["data"]["m_LightCharacterOnly"])
        row = {
            "pathId": light_id,
            "name": name_by_go[go_id],
            "group": group,
            "type": int(data["m_Type"]),
            "enabled": bool(data["m_Enabled"]),
            "cookiePathId": int(data["m_Cookie"]["m_PathID"]),
            "priority": int(data["m_LightPriority"]),
            "characterOnly": character_only,
            "hasFollower": bool(followers),
        }
        rows.append(row)
        counts = group_counts[group]
        counts["lights"] += 1
        counts["enabled"] += row["enabled"]
        counts["followers"] += row["hasFollower"]
        counts["characterOnly"] += character_only
        counts[f"type_{row['type']}"] += 1

    groups = []
    for name, expected in EXPECTED_GROUPS.items():
        group_ids = [go_id for go_id, go_name in name_by_go.items() if go_name == name]
        require(f"{name}_unique", len(group_ids), 1, json_root)
        group_id = group_ids[0]
        counts = group_counts[name]
        actual = (
            group_id,
            active_by_go[group_id],
            counts["lights"],
            counts["followers"],
            counts["characterOnly"],
            {key.removeprefix("type_"): value for key, value in counts.items() if key.startswith("type_")},
        )
        require(f"{name}_contract", actual, expected, json_root)
        require(f"{name}_enabled", counts["enabled"], counts["lights"], json_root)
        groups.append(
            {
                "name": name,
                "pathId": group_id,
                "serializedActiveSelf": active_by_go[group_id],
                "lightCount": counts["lights"],
                "followerCount": counts["followers"],
                "characterOnlyCount": counts["characterOnly"],
                "typeCounts": actual[-1],
            }
        )
    require("character_groups_only", set(group_counts), set(EXPECTED_GROUPS), json_root)
    selected = sorted(
        (row for row in rows if row["group"] == "light_overview"),
        key=lambda row: row["pathId"],
    )
    identity_nodes = []
    for name in ("light_chr_0030_zhuangfy", "light_overview"):
        matches = [go_id for go_id, value in name_by_go.items() if value == name]
        require(f"{name}_identity_unique", len(matches), 1, json_root)
        transform_id, transform = transform_by_go[matches[0]]
        position = transform["m_LocalPosition"]
        rotation = transform["m_LocalRotation"]
        scale = transform["m_LocalScale"]
        require(
            f"{name}_identity_transform",
            (
                [float(position[key]) for key in ("X", "Y", "Z")],
                [float(rotation[key]) for key in ("X", "Y", "Z", "W")],
                [float(scale[key]) for key in ("X", "Y", "Z")],
            ),
            ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], [1.0, 1.0, 1.0]),
            json_root,
        )
        identity_nodes.append({"name": name, "transformPathId": transform_id})
    return {
        "root": "light_chr_0030_zhuangfy",
        "totalLightCount": len(lights),
        "groups": groups,
        "selectedHierarchyIdentity": identity_nodes,
    }, selected


def validate_room_population(
    hierarchy: dict[str, Any], light_root: Path
) -> list[dict[str, object]]:
    require("room_light_count", int(hierarchy["lightCount"]), 34, ROOM_HIERARCHY)
    require(
        "room_rarity_counts",
        hierarchy["rarityCounts"],
        {"SceneLight4Rarity": 11, "SceneLight5Rarity": 11, "SceneLight6Rarity": 12},
        ROOM_HIERARCHY,
    )
    selected = [row for row in hierarchy["lights"] if row["rarityGroup"] == "SceneLight6Rarity"]
    require("room_selected_count", len(selected), 12, ROOM_HIERARCHY)
    rows = []
    for row in selected:
        path_id = int(row["lightPathId"])
        path_hex = f"{path_id & ((1 << 64) - 1):016X}"
        matches = list(light_root.glob(f"*p{path_hex}.json"))
        require(f"room_light_{path_hex}_file_count", len(matches), 1, light_root)
        path = matches[0]
        data = load_json(path)
        require(f"room_light_{path_hex}_enabled", bool(data["m_Enabled"]), True, path)
        require(f"room_light_{path_hex}_layer", int(data["m_RenderingLayerMask"]), 1, path)
        require(f"room_light_{path_hex}_cookie", int(data["m_Cookie"]["m_PathID"]), 0, path)
        require(
            f"room_light_{path_hex}_shadow",
            int(data["m_Shadows"]["m_PlatformSpecificType"]["defaultParam"]),
            0,
            path,
        )
        rows.append(
            {
                "pathId": path_id,
                "name": row["name"],
                "type": int(data["m_Type"]),
                "range": float(data["m_Range"]),
                "spotAngle": float(data["m_SpotAngle"]),
                "priority": int(data["m_LightPriority"]),
                "enabled": True,
                "renderingLayerMask": 1,
                "cookiePathId": 0,
                "shadowType": 0,
                "enableOBBCullingBox": bool(data["m_EnableOBBCullingBox"]),
                "cullingBoxRelativePosition": data["m_CullingBoxRelativePosition"],
                "cullingBoxHalfExtents": data["m_CullingBoxHalfExtents"],
                "cullingBoxOrientation": data["m_CullingBoxOrientation"],
                "localRotation": row["localRotation"],
                "sourceRawSha256": data["$animestudio"]["rawDataSha256"],
            }
        )
    require("room_selected_type_counts", Counter(row["type"] for row in rows), Counter({2: 11, 0: 1}), light_root)
    return sorted(rows, key=lambda row: row["pathId"])


def validate_room_geometry(
    view: dict[str, Any],
    room_rows: list[dict[str, object]],
    resolution: dict[str, object],
) -> dict[str, object]:
    camera = view["settledCamera"]
    aspect = float(resolution["aspect"]["value"])
    parent_rotation_data = load_json(ROTATEHOUSE)["m_Transform"]["m_LocalRotation"]
    parent_rotation = [float(parent_rotation_data[key]) for key in ("X", "Y", "Z", "W")]
    source_rows = view["authoredRoomRowsInStrictNativeDistanceOrder"]
    source_by_name = {row["name"]: row for row in source_rows}
    room_by_name = {str(row["name"]): row for row in room_rows}
    require("geometry_room_membership", set(source_by_name), set(room_by_name), GACHA_CULL_VIEW_AUDIT)

    def evaluate(row: dict[str, object], selected_aspect: float) -> dict[str, object]:
        source = source_by_name[str(row["name"])]
        world = vector_values(source["worldPosition"])
        planes = settled_frustum_planes(camera, selected_aspect)
        light_type = int(row["type"])
        light_range = float(row["range"])

        if light_type == 2:
            bounds_center = world
            bounds_extents = [light_range, light_range, light_range]
            forward = None
        else:
            local_rotation_data = row["localRotation"]
            local_rotation = [float(local_rotation_data[key]) for key in ("X", "Y", "Z", "W")]
            world_rotation = quaternion_multiply(parent_rotation, local_rotation)
            forward = quaternion_rotate(world_rotation, [0.0, 0.0, 1.0])
            cone_radius = light_range * math.tan(math.radians(float(row["spotAngle"]) * 0.5))
            base_center = [f32(world[i] + forward[i] * light_range) for i in range(3)]
            minimum = []
            maximum = []
            for axis in range(3):
                disk_extent = cone_radius * math.sqrt(max(0.0, 1.0 - forward[axis] * forward[axis]))
                minimum.append(min(world[axis], base_center[axis] - disk_extent))
                maximum.append(max(world[axis], base_center[axis] + disk_extent))
            bounds_center = [f32((minimum[i] + maximum[i]) * 0.5) for i in range(3)]
            bounds_extents = [f32((maximum[i] - minimum[i]) * 0.5) for i in range(3)]

        initial = [(plane[0], aabb_margin(plane, bounds_center, bounds_extents)) for plane in planes]
        initial_min = min(initial, key=lambda item: item[1])

        if bool(row["enableOBBCullingBox"]):
            relative = row["cullingBoxRelativePosition"]
            half_data = row["cullingBoxHalfExtents"]
            center = [f32(world[i] + float(relative[key])) for i, key in enumerate(("x", "y", "z"))]
            half = [float(half_data[key]) for key in ("x", "y", "z")]
            axes = zxy_rotation_axes(row["cullingBoxOrientation"])
            obb = [(plane[0], obb_margin(plane, center, half, axes)) for plane in planes]
            obb_min = min(obb, key=lambda item: item[1])
            obb_pass = obb_min[1] >= 0.0
        else:
            obb_min = ("disabled", math.inf)
            obb_pass = True

        if light_type == 2:
            geometry = [(plane[0], sphere_margin(plane, world, light_range)) for plane in planes]
            geometry_kind = "point_sphere"
        else:
            assert forward is not None
            geometry = [
                (
                    plane[0],
                    cone_margin(
                        plane,
                        world,
                        forward,
                        light_range,
                        float(row["spotAngle"]) * 0.5,
                    ),
                )
                for plane in planes
            ]
            geometry_kind = "spot_cone"
        geometry_min = min(geometry, key=lambda item: item[1])
        admitted = initial_min[1] >= 0.0 and obb_pass and geometry_min[1] >= 0.0
        return {
            "admitted": admitted,
            "initialAabbMinimum": initial_min,
            "authoredObbMinimum": obb_min,
            "typeGeometryKind": geometry_kind,
            "typeGeometryMinimum": geometry_min,
            "forward": forward,
        }

    ordered = []
    for source in source_rows:
        row = room_by_name[source["name"]]
        result = evaluate(row, aspect)
        threshold = None
        if source["name"] != "Spot Light (20)":
            low, high = 0.1, aspect
            require(f"geometry_{source['name']}_selected_aspect_admitted", result["admitted"], True, RESOLUTION_VALUES["videoWidth"])
            if evaluate(row, low)["admitted"]:
                threshold = {"atOrBelowSearchFloor": float_evidence(low)}
            else:
                for _ in range(40):
                    middle = (low + high) * 0.5
                    if evaluate(row, middle)["admitted"]:
                        high = middle
                    else:
                        low = middle
                threshold = {"numericalRoot": float_evidence(high)}
        ordered.append(
            {
                "name": source["name"],
                "lightPathId": int(row["pathId"]),
                "type": int(row["type"]),
                "selectedAspectAdmitted": bool(result["admitted"]),
                "minimumAspectApprox": threshold,
                "initialAabb": {
                    "result": result["initialAabbMinimum"][1] >= 0.0,
                    "minimumPlane": result["initialAabbMinimum"][0],
                    "minimumSupportMargin": float_evidence(result["initialAabbMinimum"][1]),
                },
                "authoredObb": {
                    "enabled": bool(row["enableOBBCullingBox"]),
                    "result": result["authoredObbMinimum"][1] >= 0.0 if bool(row["enableOBBCullingBox"]) else "skipped",
                    "minimumPlane": result["authoredObbMinimum"][0],
                    "minimumSupportMargin": float_evidence(result["authoredObbMinimum"][1]) if bool(row["enableOBBCullingBox"]) else None,
                    "orientationOrder": "Unity ZXY" if bool(row["enableOBBCullingBox"]) else None,
                },
                "typeGeometry": {
                    "kind": result["typeGeometryKind"],
                    "result": result["typeGeometryMinimum"][1] >= 0.0,
                    "minimumPlane": result["typeGeometryMinimum"][0],
                    "minimumSupportMargin": float_evidence(result["typeGeometryMinimum"][1]),
                },
            }
        )

    admitted = [row["name"] for row in ordered if row["selectedAspectAdmitted"]]
    rejected = [row["name"] for row in ordered if not row["selectedAspectAdmitted"]]
    validate_room_survivor_names(admitted, rejected, GACHA_CULL_VIEW_AUDIT)
    require("selected_aspect_initial_aabb_all", all(row["initialAabb"]["result"] for row in ordered), True, GACHA_CULL_VIEW_AUDIT)
    require("selected_aspect_obb_all_enabled", all(row["authoredObb"]["result"] in (True, "skipped") for row in ordered), True, GACHA_CULL_VIEW_AUDIT)
    return {
        "selectedResolution": resolution,
        "cameraSampleTime": camera["time"],
        "verticalFovDegrees": camera["verticalFovDegrees"],
        "nativePlaneConvention": "inside when signed support is nonnegative",
        "roomRowsInNativeDistanceOrder": ordered,
        "exactSelectedAspectRoomSurvivors": admitted,
        "exactSelectedAspectRoomRejections": rejected,
        "exactSelectedAspectRoomContributionCount": len(admitted),
        "precisionBoundary": (
            "Thresholds are float32 numerical roots for diagnostics; the selected 16:9 "
            "margins are well separated from zero and own the pass/fail claims."
        ),
    }


def validate_operator_population(
    payload: dict[str, Any], prefab_rows: list[dict[str, object]]
) -> list[dict[str, object]]:
    actor = payload["actors"]["zhuangfy"]
    require("operator_group", actor["group_name"], "light_overview", OPERATOR_LIGHTS)
    require("operator_root", actor["root_name"], "light_chr_0030_zhuangfy", OPERATOR_LIGHTS)
    require("operator_light_count", int(actor["count"]), 6, OPERATOR_LIGHTS)
    rows = []
    for row in actor["lights"]:
        follower = row["follower"]
        rows.append(
            {
                "pathId": int(row["light_path_id"]),
                "name": row["name"],
                "type": int(row["light_type"]),
                "range": float(row["range"]),
                "spotAngle": float(row["outer_spot_angle"]),
                "priority": int(row["priority"]),
                "enabled": bool(row["enabled"]),
                "cookiePathId": int(row["cookie_path_id"]),
                "shadowType": int(row["shadow_type"]),
                "characterOnly": bool(row["character_only"]),
                "enableOBBCullingBox": bool(row["enable_obb_culling_box"]),
                "serializedPosition": [float(value) for value in row["position"]],
                "serializedRotation": [float(value) for value in row["rotation_xyzw"]],
                "serializedForward": [float(value) for value in row["forward"]],
                "hasFollower": follower is not None,
                "follower": None
                if follower is None
                else {
                    "componentPathId": int(follower["component_path_id"]),
                    "followType": int(follower["follow_type"]),
                    "followableNodeType": int(follower["followable_node_type"]),
                    "followableNodeName": follower["followable_node_name"],
                    "positionOffset": [float(value) for value in follower["position_offset"]],
                    "localPosition": [float(value) for value in follower["local_position"]],
                    "localRotationEulerDegrees": [
                        float(value) for value in follower["local_rotation_euler_degrees"]
                    ],
                    "sourceRawSha256": follower["source"]["raw_data_sha256"],
                },
            }
        )
    require("operator_all_enabled", all(row["enabled"] for row in rows), True, OPERATOR_LIGHTS)
    require("operator_all_character_only", all(row["characterOnly"] for row in rows), True, OPERATOR_LIGHTS)
    require("operator_cookie_count", sum(bool(row["cookiePathId"]) for row in rows), 0, OPERATOR_LIGHTS)
    require("operator_shadow_count", sum(bool(row["shadowType"]) for row in rows), 1, OPERATOR_LIGHTS)
    require("operator_follower_count", sum(row["hasFollower"] for row in rows), 4, OPERATOR_LIGHTS)
    require("operator_obb_disabled", any(row["enableOBBCullingBox"] for row in rows), False, OPERATOR_LIGHTS)
    prefab_membership = [(row["pathId"], row["name"], row["type"]) for row in prefab_rows]
    operator_membership = sorted((row["pathId"], row["name"], row["type"]) for row in rows)
    require("operator_prefab_membership", operator_membership, prefab_membership, OPERATOR_LIGHTS)
    return rows


def parse_transform_dump(path: Path) -> dict[str, list[float]]:
    text = path.read_text(encoding="utf-8-sig")
    rows: dict[str, list[float]] = {}
    specs = (
        ("localRotation", "Quaternionf m_LocalRotation", ("x", "y", "z", "w")),
        ("localPosition", "Vector3f m_LocalPosition", ("x", "y", "z")),
        ("localScale", "Vector3f m_LocalScale", ("x", "y", "z")),
    )
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
    for output_name, marker, axes in specs:
        start = text.find(marker)
        require(f"transform_dump_{output_name}_marker", start >= 0, True, path)
        values = []
        cursor = start + len(marker)
        for axis in axes:
            match = re.search(rf"float\s+{axis}\s*=\s*({number})", text[cursor:])
            require(f"transform_dump_{output_name}_{axis}", bool(match), True, path)
            assert match is not None
            values.append(float(match.group(1)))
            cursor += match.end()
        rows[output_name] = values
    return rows


def validate_actor_placement() -> dict[str, object]:
    identity = ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], [1.0, 1.0, 1.0])
    room_rows = []
    for name, path in (("GachaRoom", GACHA_ROOM_ROOT), ("TimelineRoot", TIMELINE_ROOT)):
        data = load_json(path)
        require(f"{name}_name", data["m_Name"], name, path)
        transform = data["m_Transform"]
        actual = (
            [float(transform["m_LocalPosition"][key]) for key in ("X", "Y", "Z")],
            [float(transform["m_LocalRotation"][key]) for key in ("X", "Y", "Z", "W")],
            [float(transform["m_LocalScale"][key]) for key in ("X", "Y", "Z")],
        )
        require(f"{name}_identity", actual, identity, path)
        room_rows.append({"name": name, "identity": True})

    prefab_rows = []
    for name, path in ACTOR_PREFAB_TRANSFORMS.items():
        transform = parse_transform_dump(path)
        require(f"{name}_position", transform["localPosition"], identity[0], path)
        require(f"{name}_scale", transform["localScale"], identity[2], path)
        if name == "Root":
            rotation = transform["localRotation"]
            require(
                "actor_skeleton_root_near_identity",
                abs(rotation[0]) < 1.0e-6
                and rotation[1] == 0.0
                and rotation[2] == 0.0
                and rotation[3] == 1.0,
                True,
                path,
            )
        else:
            require(f"{name}_rotation", transform["localRotation"], identity[1], path)
        prefab_rows.append({"name": name, "identity": True})
    return {
        "roomToTimelineRoot": room_rows,
        "characterPrefabChain": prefab_rows,
        "worldPlacement": "identity before Animation Track evaluation",
    }


def decode_root_motion(
    clip: dict[str, Any],
    source: Path,
    expected_samples: int,
) -> dict[str, object]:
    acl = clip["m_AclCompressedBuffer"]
    require("root_motion_track_count", int(acl["RootTrackCount"]), 21, source)
    require("root_motion_position_index", int(acl["RootPosIndex"]), 0, source)
    require("root_motion_rotation_index", int(acl["RootRotIndex"]), 0, source)
    require("root_motion_scale_index", int(acl["RootScaleIndex"]), 65535, source)
    raw = base64.b64decode(str(acl["RootMotionBufferData"]), validate=True)
    require("root_motion_buffer_size", len(raw), 176, source)
    with tempfile.TemporaryDirectory(prefix="endfield-gacha-root-motion-") as temp_name:
        temp = Path(temp_name)
        acl_path = temp / "RootMotionBufferData.acl"
        output_path = temp / "RootMotionBufferData.json"
        acl_path.write_bytes(raw)
        completed = subprocess.run(
            [str(ACL_SAMPLER), str(acl_path), str(output_path)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        require("acl_sampler_return_code", completed.returncode, 0, ACL_SAMPLER)
        decoded = load_json(output_path)
    require("root_motion_acl_ok", decoded["ok"], True, source)
    require("root_motion_acl_hash_ok", decoded["hash_ok"], True, source)
    require("root_motion_decoded_tracks", int(decoded["num_tracks"]), 21, source)
    require("root_motion_decoded_samples", int(decoded["num_samples"]), expected_samples, source)
    require("root_motion_sample_rate", float(decoded["sample_rate"]), 60.0, source)
    start = clip["m_MuscleClip"]["m_StartX"]
    base = [
        f32(float(start["t"][key])) for key in ("X", "Y", "Z")
    ] + [f32(float(start["q"][key])) for key in ("X", "Y", "Z", "W")]
    expected = base * 3
    stop = clip["m_MuscleClip"]["m_StopX"]
    stop_values = [
        f32(float(stop["t"][key])) for key in ("X", "Y", "Z")
    ] + [f32(float(stop["q"][key])) for key in ("X", "Y", "Z", "W")]
    require("root_motion_stop_matches_start", stop_values, base, source)
    first_values = [float(track["value"]) for track in decoded["frames"][0]["tracks"]]
    require(
        "root_motion_start_transform_error",
        max(abs(actual - wanted) for actual, wanted in zip(first_values, expected)) < 1.0e-12,
        True,
        source,
    )
    varying = []
    for frame in decoded["frames"]:
        values = [float(track["value"]) for track in frame["tracks"]]
        if values != first_values:
            varying.append(int(frame["index"]))
            if len(varying) >= 8:
                break
    require("root_motion_constant_start_transform", varying, [], source)
    return {
        "compressedBytes": len(raw),
        "compressedSha256": hashlib.sha256(raw).hexdigest(),
        "trackCount": 21,
        "sampleCount": expected_samples,
        "sampleRate": 60.0,
        "constantTransform": {
            "translation": first_values[:3],
            "rotation": first_values[3:7],
        },
        "removeStartOffsetResult": "identity for every decoded sample",
    }


def validate_actor_pose_sources() -> tuple[dict[str, object], dict[str, Any]]:
    audit = load_json(ACTOR_TIMELINE_AUDIT)
    require("actor_timeline_audit_passed", audit["passed"], True, ACTOR_TIMELINE_AUDIT)
    require("actor_timeline_visual_admission", audit["visualAdmission"], False, ACTOR_TIMELINE_AUDIT)
    require(
        "actor_track_binding",
        audit["tracks"][0]["autoBindingPath"],
        "Actor/chr_0030_zhuangfy_uimodel",
        ACTOR_TIMELINE_AUDIT,
    )
    timeline_clips = {row["displayName"]: row for row in audit["clips"]}
    require("actor_entrance_start", float(timeline_clips["A_actor_zhuangfy_gacha"]["start"]), 0.0, ACTOR_TIMELINE_AUDIT)
    require("actor_entrance_duration", float(timeline_clips["A_actor_zhuangfy_gacha"]["duration"]), 10.7, ACTOR_TIMELINE_AUDIT)
    require("actor_loop_start", float(timeline_clips["A_actor_zhuangfy_ui_overview_loop_01"]["start"]), 10.7, ACTOR_TIMELINE_AUDIT)

    track = load_json(ACTOR_TRACK)
    require("actor_track_offset_mode", int(track["m_TrackOffset"]), 0, ACTOR_TRACK)
    require("actor_track_position", track["m_Position"], {"x": 0.0, "y": 0.0, "z": 0.0}, ACTOR_TRACK)
    require("actor_track_euler", track["m_EulerAngles"], {"x": 0.0, "y": 0.0, "z": 0.0}, ACTOR_TRACK)
    require("actor_track_avatar_mask", int(track["m_AvatarMask"]["m_PathID"]), 0, ACTOR_TRACK)

    for path in (ACTOR_PLAYABLE_ENTRANCE, ACTOR_PLAYABLE_LOOP):
        playable = load_json(path)
        require("actor_playable_position", playable["m_Position"], {"x": 0.0, "y": 0.0, "z": 0.0}, path)
        require("actor_playable_euler", playable["m_EulerAngles"], {"x": 0.0, "y": 0.0, "z": 0.0}, path)
        require("actor_playable_rotation", playable["m_Rotation"], {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}, path)
        require("actor_playable_track_match", int(playable["m_UseTrackMatchFields"]), 1, path)
        require("actor_playable_remove_start", int(playable["m_RemoveStartOffset"]), 1, path)

    manifest = load_json(ZHUANGFY_MANIFEST)
    clip_manifest = {row["name"]: row for row in manifest["clips"]}
    head_local_rows = [row for row in manifest["transforms"] if row["name"] == "Head_Local"]
    require("head_local_unique", len(head_local_rows), 1, ZHUANGFY_MANIFEST)
    head_local = head_local_rows[0]
    expected_head_path = (
        "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/"
        "Bip001_Spine2/Bip001_Neck/Bip001_Head/Head_Local"
    )
    require("head_local_path", head_local["path"], expected_head_path, ZHUANGFY_MANIFEST)

    clip_specs = (
        ("A_actor_zhuangfy_gacha", ACTOR_CLIP_ENTRANCE, ACTOR_SAMPLE_ENTRANCE, 643, 642),
        ("A_actor_zhuangfy_ui_overview_loop_01", ACTOR_CLIP_LOOP, ACTOR_SAMPLE_LOOP, 201, 200),
    )
    pose_clips = {}
    report_clips = []
    required_paths = [
        "Root",
        "Root/Bip001",
        "Root/Bip001/Bip001_Pelvis",
        "Root/Bip001/Bip001_Pelvis/Bip001_Spine",
        "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1",
        "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2",
        "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2/Bip001_Neck",
        "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2/Bip001_Neck/Bip001_Head",
    ]
    for name, clip_path, sample_path, frame_count, root_frame_count in clip_specs:
        clip = load_json(clip_path)
        sample = load_json(sample_path)
        manifest_row = clip_manifest[name]
        require(f"{name}_sample_ok", sample["ok"], True, sample_path)
        require(f"{name}_sample_hash_ok", sample["hash_ok"], True, sample_path)
        require(f"{name}_sample_source", manifest_row["sample_source"], "acl_transform_buffer", ZHUANGFY_MANIFEST)
        require(f"{name}_frame_count", int(sample["num_samples"]), frame_count, sample_path)
        require(f"{name}_track_count", int(sample["num_tracks"]), 437, sample_path)
        require(f"{name}_matched_tracks", int(manifest_row["matched_transform_count"]), 437, ZHUANGFY_MANIFEST)
        require(f"{name}_missing_tracks", int(manifest_row["missing_transform_count"]), 0, ZHUANGFY_MANIFEST)
        index_array = [int(value) for value in clip["m_MuscleClip"]["m_IndexArray"]]
        mapped = [(index, value) for index, value in enumerate(index_array) if value >= 0]
        require(f"{name}_motion_root_only_mapping", mapped, [(index, 3059 + index) for index in range(14)], clip_path)
        mapping = {row["path"]: int(row["track_index"]) for row in manifest_row["bones"]}
        require(f"{name}_follower_chain_tracks", [mapping[path] for path in required_paths], list(range(8)), ZHUANGFY_MANIFEST)
        for frame in sample["frames"]:
            require(
                f"{name}_root_qvv_identity_frame_{frame['index']}",
                frame["tracks"][0],
                {
                    "rotation": [0, 0, 0, 1],
                    "translation": [0, 0, 0],
                    "scale": [1, 1, 1],
                },
                sample_path,
            )
        root_motion = decode_root_motion(clip, clip_path, root_frame_count)
        pose_clips[name] = {
            "frames": sample["frames"],
            "mapping": mapping,
            "requiredPaths": required_paths,
            "sourcePath": str(sample_path),
        }
        report_clips.append(
            {
                "name": name,
                "qvvFrameCount": frame_count,
                "qvvTrackCount": 437,
                "directFollowerChainTrackIndices": list(range(8)),
                "mappedMuscleClipInputs": "Motion/Root 0..13 only; no muscle lanes",
                "rootMotion": root_motion,
            }
        )
    return (
        {
            "bindingPath": "Actor/chr_0030_zhuangfy_uimodel",
            "trackOffsetMode": "ApplyTransformOffsets",
            "trackPosition": [0.0, 0.0, 0.0],
            "trackRotation": [0.0, 0.0, 0.0, 1.0],
            "removeStartOffset": True,
            "settledLoopStart": 10.7,
            "headLocalStaticTransform": {
                "path": head_local["path"],
                "position": head_local["local_pos"],
                "rotation": head_local["local_rot"],
                "scale": head_local["local_scale"],
            },
            "clips": report_clips,
        },
        {
            "clips": pose_clips,
            "headLocal": (
                [float(value) for value in head_local["local_pos"]],
                [float(value) for value in head_local["local_rot"]],
                [float(value) for value in head_local["local_scale"]],
            ),
        },
    )


def follower_nodes_for_frame(
    frame: dict[str, Any], pose_source: dict[str, Any], head_local: tuple[list[float], list[float], list[float]]
) -> dict[str, tuple[list[float], list[float], list[float]]]:
    transforms: dict[str, tuple[list[float], list[float], list[float]]] = {}
    for path in pose_source["requiredPaths"]:
        track = frame["tracks"][pose_source["mapping"][path]]
        local = (
            [float(value) for value in track["translation"]],
            [float(value) for value in track["rotation"]],
            [float(value) for value in track["scale"]],
        )
        if "/" not in path:
            transforms[path] = local
        else:
            transforms[path] = compose_transform(transforms[path.rsplit("/", 1)[0]], local)
    head_path = pose_source["requiredPaths"][-1]
    transforms[head_path + "/Head_Local"] = compose_transform(transforms[head_path], head_local)
    return {
        "BIP001": transforms["Root/Bip001"],
        "HEAD_LOCAL": transforms[head_path + "/Head_Local"],
    }


def evaluate_character_light(
    row: dict[str, object],
    nodes: dict[str, tuple[list[float], list[float], list[float]]],
    planes: list[tuple[str, list[float], float]],
    camera_position: list[float],
) -> dict[str, object]:
    follower = row["follower"]
    if follower is None:
        world = list(row["serializedPosition"])
        position_equation = "serialized static transform under identity light root"
    else:
        node = nodes[str(follower["followableNodeName"])]
        if int(follower["followType"]) == 0:
            world = vector_add(node[0], list(follower["positionOffset"]))
            position_equation = "target.worldPosition + positionOffset"
        else:
            require("parent_follower_mode", int(follower["followType"]), 1, OPERATOR_LIGHTS)
            world = vector_add(node[0], quaternion_rotate(node[1], list(follower["localPosition"])))
            position_equation = "target.worldPosition + target.worldRotation * localPosition"

    light_type = int(row["type"])
    light_range = float(row["range"])
    forward = list(row["serializedForward"])
    if light_type == 2:
        bounds_center = world
        bounds_extents = [light_range, light_range, light_range]
    else:
        cone_radius = light_range * math.tan(math.radians(float(row["spotAngle"]) * 0.5))
        base_center = [f32(world[index] + forward[index] * light_range) for index in range(3)]
        minimum = []
        maximum = []
        for axis in range(3):
            disk_extent = cone_radius * math.sqrt(max(0.0, 1.0 - forward[axis] * forward[axis]))
            minimum.append(min(world[axis], base_center[axis] - disk_extent))
            maximum.append(max(world[axis], base_center[axis] + disk_extent))
        bounds_center = [f32((minimum[index] + maximum[index]) * 0.5) for index in range(3)]
        bounds_extents = [f32((maximum[index] - minimum[index]) * 0.5) for index in range(3)]
    initial = [(plane[0], aabb_margin(plane, bounds_center, bounds_extents)) for plane in planes]
    initial_min = min(initial, key=lambda item: item[1])
    if light_type == 2:
        geometry = [(plane[0], sphere_margin(plane, world, light_range)) for plane in planes]
        kind = "point_sphere"
    else:
        geometry = [
            (
                plane[0],
                cone_margin(plane, world, forward, light_range, float(row["spotAngle"]) * 0.5),
            )
            for plane in planes
        ]
        kind = "spot_cone"
    geometry_min = min(geometry, key=lambda item: item[1])
    delta = [f32(world[index] - camera_position[index]) for index in range(3)]
    return {
        "admitted": initial_min[1] >= 0.0 and geometry_min[1] >= 0.0,
        "worldPosition": world,
        "positionEquation": position_equation,
        "initialAabbMinimum": initial_min,
        "typeGeometryKind": kind,
        "typeGeometryMinimum": geometry_min,
        "cameraDistanceSquared": f32(dot(delta, delta)),
    }


def validate_character_geometry(
    view: dict[str, Any],
    resolution: dict[str, object],
    operator_rows: list[dict[str, object]],
    pose_sources: dict[str, Any],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    camera = view["settledCamera"]
    camera_position = vector_values(camera["position"])
    planes = settled_frustum_planes(camera, float(resolution["aspect"]["value"]))
    per_clip = []
    target_results = None
    for clip_name, pose_source in pose_sources["clips"].items():
        worst = {
            row["name"]: {"initial": ("", math.inf), "geometry": ("", math.inf)}
            for row in operator_rows
        }
        for frame in pose_source["frames"]:
            nodes = follower_nodes_for_frame(frame, pose_source, pose_sources["headLocal"])
            results = [
                evaluate_character_light(row, nodes, planes, camera_position)
                for row in operator_rows
            ]
            for row, result in zip(operator_rows, results):
                current = worst[row["name"]]
                if result["initialAabbMinimum"][1] < current["initial"][1]:
                    current["initial"] = result["initialAabbMinimum"]
                if result["typeGeometryMinimum"][1] < current["geometry"][1]:
                    current["geometry"] = result["typeGeometryMinimum"]
            require(
                f"{clip_name}_all_character_lights_admitted_frame_{frame['index']}",
                all(result["admitted"] for result in results),
                True,
                pose_source["sourcePath"],
            )
            if clip_name == "A_actor_zhuangfy_ui_overview_loop_01" and int(frame["index"]) == 0:
                target_results = results
        per_clip.append(
            {
                "name": clip_name,
                "frameCount": len(pose_source["frames"]),
                "allSixAdmitted": True,
                "worstMargins": [
                    {
                        "name": row["name"],
                        "initialAabb": {
                            "plane": worst[row["name"]]["initial"][0],
                            "margin": float_evidence(worst[row["name"]]["initial"][1]),
                        },
                        "typeGeometry": {
                            "plane": worst[row["name"]]["geometry"][0],
                            "margin": float_evidence(worst[row["name"]]["geometry"][1]),
                        },
                    }
                    for row in operator_rows
                ],
            }
        )
    require("settled_loop_target_present", target_results is not None, True, ACTOR_SAMPLE_LOOP)
    assert target_results is not None
    admitted = [row["name"] for row, result in zip(operator_rows, target_results) if result["admitted"]]
    rejected = [row["name"] for row, result in zip(operator_rows, target_results) if not result["admitted"]]
    validate_character_survivor_names(admitted, rejected, ACTOR_SAMPLE_LOOP)
    target_rows = []
    for row, result in zip(operator_rows, target_results):
        target_rows.append(
            {
                "name": row["name"],
                "lightPathId": row["pathId"],
                "type": row["type"],
                "priority": row["priority"],
                "hasFollower": row["hasFollower"],
                "worldPosition": [float_evidence(value) for value in result["worldPosition"]],
                "positionEquation": result["positionEquation"],
                "cameraDistanceSquared": float_evidence(result["cameraDistanceSquared"]),
                "selectedAspectAdmitted": result["admitted"],
                "initialAabb": {
                    "result": result["initialAabbMinimum"][1] >= 0.0,
                    "minimumPlane": result["initialAabbMinimum"][0],
                    "minimumSupportMargin": float_evidence(result["initialAabbMinimum"][1]),
                },
                "typeGeometry": {
                    "kind": result["typeGeometryKind"],
                    "result": result["typeGeometryMinimum"][1] >= 0.0,
                    "minimumPlane": result["typeGeometryMinimum"][0],
                    "minimumSupportMargin": float_evidence(result["typeGeometryMinimum"][1]),
                },
            }
        )
    return (
        {
            "cameraSampleTime": camera["time"],
            "targetActorClip": "A_actor_zhuangfy_ui_overview_loop_01",
            "targetActorFrame": 0,
            "targetClipLocalTime": 0.0,
            "selectedAspectSurvivors": admitted,
            "selectedAspectRejections": rejected,
            "exactSelectedAspectCharacterContributionCount": len(admitted),
            "allEntranceAndLoopFrames": per_clip,
            "characterRows": target_rows,
            "precisionBoundary": (
                "Claims use float32-style source equations; every target and all-frame "
                "minimum is separated from zero. Parent-mode light rotations are not "
                "needed because both selected parent followers are point lights."
            ),
        },
        target_rows,
    )


def validate_native_methods(game_assembly: Path) -> list[dict[str, object]]:
    data = game_assembly.read_bytes()
    rows = []
    for name, spec in NATIVE_METHODS.items():
        offset = int(spec["fileOffset"])
        size = int(spec["sizeBytes"])
        actual = hashlib.sha256(data[offset : offset + size]).hexdigest()
        require(f"native_{name}_sha256", actual, spec["sha256"], game_assembly)
        rows.append({"method": name, **spec})
    return rows


def validate_native_cull_boundary(
    native: dict[str, Any],
    view: dict[str, Any],
    selected: dict[str, Any],
    room_rows: list[dict[str, object]],
) -> dict[str, object]:
    require(
        "native_cull_status",
        native["status"],
        "native candidate producer substantially source-closed; scheduled generic cull-view internals remain bounded open",
        NATIVE_CULL_REPORT,
    )
    require(
        "normal_path_fallback",
        view["nativeProof"]["fallbackMode"][
            "useFallbackLightCullingOnSourceClosedShippedRoute"
        ],
        False,
        GACHA_CULL_VIEW_AUDIT,
    )
    require(
        "gacha_occlusion_dimensions",
        view["nativeProof"]["occlusion"]["addCullViewDimensions"],
        [0, 0],
        GACHA_CULL_VIEW_AUDIT,
    )
    strongest = view["strongestExactOutput"]
    require(
        "room_native_maximum",
        int(strongest["authoredRoomMaximumContributionCount"]),
        11,
        GACHA_CULL_VIEW_AUDIT,
    )
    require(
        "room_exact_exclusion",
        strongest["excludedAuthoredRoomRows"],
        ["Spot Light (20)"],
        GACHA_CULL_VIEW_AUDIT,
    )
    require(
        "room_survivor_subsequence",
        strongest["remainingAuthoredRoomOrderIsExactSubsequenceOf"],
        ROOM_SURVIVOR_SUBSEQUENCE,
        GACHA_CULL_VIEW_AUDIT,
    )
    selected_output = selected["strongestExactOutput"]
    require(
        "selected_generic_gate",
        selected_output["genericFlagMaskGateClosedForAll12"],
        True,
        GACHA_SELECTED_LIST_AUDIT,
    )
    require(
        "selected_exact_exclusion",
        selected_output["guaranteedAbsent"],
        ["Spot Light (20)"],
        GACHA_SELECTED_LIST_AUDIT,
    )
    require(
        "selected_survivor_subsequence",
        selected_output["remainingStrictRelativeOrderIfAdmitted"],
        ROOM_SURVIVOR_SUBSEQUENCE,
        GACHA_SELECTED_LIST_AUDIT,
    )
    require(
        "room_excluded_row_membership",
        "Spot Light (20)" in {row["name"] for row in room_rows},
        True,
        ROOM_HIERARCHY,
    )
    for source, audit in (
        (GACHA_CULL_VIEW_AUDIT, view),
        (GACHA_SELECTED_LIST_AUDIT, selected),
    ):
        require(
            f"{source.parent.name}_offline_only",
            set(audit["noRuntimeLaunches"].values()),
            {False},
            source,
        )
    return {
        "shippedCandidateCore": "normal; useFallbackLightCulling=false",
        "gachaOcclusionDimensions": [0, 0],
        "gachaOcclusionActive": False,
        "genericFlagMaskGateClosedForAll12RoomLights": True,
        "guaranteedAbsentRoomLights": ["Spot Light (20)"],
        "authoredRoomMaximumContributionCount": 11,
        "preCharacterEvaluationKnownAuthoredUpperBound": 17,
        "remainingRoomOrderIfAdmitted": ROOM_SURVIVOR_SUBSEQUENCE,
        "nativeOutputOrder": (
            "accepted non-directionals sort by ascending camera distance squared; "
            "SetupState then sorts types 0/2 by priority descending and distance ascending"
        ),
        "firstOpenBoundary": (
            "the synchronous AABB/plane result for the other eleven room rows depends "
            "on live horizontal planes derived from final render-target aspect"
        ),
    }


def build_report(*, verify_hashes: bool = True) -> dict[str, object]:
    source_paths = {
        "gameAssembly": GAME_ASSEMBLY,
        "unityPlayer": UNITY_PLAYER,
        "globalMetadata": GLOBAL_METADATA,
        "globalGameManagers": GLOBAL_GAME_MANAGERS,
        "roomChunk": ROOM_CHUNK,
        "charInfoChunk": CHARINFO_CHUNK,
        "gachaLua": LUA_SOURCE,
        "uiConstLua": UI_CONST_SOURCE,
        "characterTable": CHARACTER_TABLE,
        "gachaCharTable": GACHA_CHAR_TABLE,
        "roomHierarchy": ROOM_HIERARCHY,
        "operatorLights": OPERATOR_LIGHTS,
        "nativeCullReport": NATIVE_CULL_REPORT,
        "gachaCullViewAudit": GACHA_CULL_VIEW_AUDIT,
        "gachaSelectedListAudit": GACHA_SELECTED_LIST_AUDIT,
        "rotatehouse": ROTATEHOUSE,
        "actorTimelineAudit": ACTOR_TIMELINE_AUDIT,
        "zhuangfyManifest": ZHUANGFY_MANIFEST,
        "actorTrack": ACTOR_TRACK,
        "actorPlayableEntrance": ACTOR_PLAYABLE_ENTRANCE,
        "actorPlayableLoop": ACTOR_PLAYABLE_LOOP,
        "actorClipEntrance": ACTOR_CLIP_ENTRANCE,
        "actorClipLoop": ACTOR_CLIP_LOOP,
        "actorSampleEntrance": ACTOR_SAMPLE_ENTRANCE,
        "actorSampleLoop": ACTOR_SAMPLE_LOOP,
        "gachaRoomRoot": GACHA_ROOM_ROOT,
        "timelineRoot": TIMELINE_ROOT,
        "actorPrefabRoot": ACTOR_PREFAB_TRANSFORMS["gacha_char_zhuangfy"],
        "actorContainer": ACTOR_PREFAB_TRANSFORMS["Actor"],
        "actorModel": ACTOR_PREFAB_TRANSFORMS["chr_0030_zhuangfy_uimodel"],
        "actorSkeletonRoot": ACTOR_PREFAB_TRANSFORMS["Root"],
        "aclSampler": ACL_SAMPLER,
        "aclSamplerSource": ACL_SAMPLER_SOURCE,
    }
    source_hashes = (
        {name: verified_hash(name, path) for name, path in source_paths.items()}
        if verify_hashes
        else {}
    )
    lua_contract = validate_lua_contract(
        LUA_SOURCE.read_text(encoding="utf-8-sig"), LUA_SOURCE
    )
    selected_audit = load_json(GACHA_SELECTED_LIST_AUDIT)
    gacha_layer = validate_gacha_layer(
        UI_CONST_SOURCE.read_text(encoding="utf-8-sig"),
        GLOBAL_GAME_MANAGERS,
        selected_audit,
    )
    character_table = load_json(CHARACTER_TABLE)
    gacha_table = load_json(GACHA_CHAR_TABLE)
    character_row = character_table["chr_0030_zhuangfy"]
    gacha_row = gacha_table["chr_0030_zhuangfy"]
    require("zhuangfy_rarity", int(character_row["rarity"]), 6, CHARACTER_TABLE)
    require("zhuangfy_timeline", gacha_row["timelineAssetName"], "gacha_char_zhuangfy", GACHA_CHAR_TABLE)

    prefab, prefab_rows = analyze_character_prefab(CHAR_JSON_ROOT, CHAR_DUMP_ROOT)
    operator_rows = validate_operator_population(load_json(OPERATOR_LIGHTS), prefab_rows)
    actor_placement = validate_actor_placement()
    actor_pose, pose_sources = validate_actor_pose_sources()
    room_rows = validate_room_population(load_json(ROOM_HIERARCHY), ROOM_LIGHT_ROOT)
    native_rows = validate_native_methods(GAME_ASSEMBLY)
    native_geometry_regions = {
        "unityPlayer": validate_native_regions(UNITY_PLAYER, UNITY_NATIVE_REGIONS),
        "gameAssembly": validate_native_regions(GAME_ASSEMBLY, GAME_NATIVE_REGIONS),
    }
    installed_resolution = read_installed_resolution()
    cull_view = load_json(GACHA_CULL_VIEW_AUDIT)
    native_cull_boundary = validate_native_cull_boundary(
        load_json(NATIVE_CULL_REPORT),
        cull_view,
        selected_audit,
        room_rows,
    )
    room_geometry = validate_room_geometry(cull_view, room_rows, installed_resolution)
    character_geometry, character_target_rows = validate_character_geometry(
        cull_view,
        installed_resolution,
        operator_rows,
        pose_sources,
    )
    native_cull_boundary["selectedAspectRoomGeometry"] = room_geometry
    native_cull_boundary["selectedAspectCharacterGeometry"] = character_geometry
    native_cull_boundary["exactKnownAuthoredSurvivorCount"] = 17
    native_cull_boundary["firstOpenBoundary"] = (
        "all known authored room and character-light geometry is closed for the selected "
        "installed-client 3840x2160 state; runtime/custom carry-in and the native target-frame "
        "pointer/count remain open"
    )
    union = room_rows + operator_rows
    type_counts = Counter(row["type"] for row in union)
    require("authored_union_count", len(union), 18, "room + character overview")
    require("authored_union_types", type_counts, Counter({2: 15, 0: 3}), "room + character overview")
    require("authored_union_cookie_count", sum(bool(row["cookiePathId"]) for row in union), 0, "room + character overview")

    camera_position = vector_values(cull_view["settledCamera"]["position"])
    room_by_name = {row["name"]: row for row in room_rows}
    room_position_by_name = {
        row["name"]: vector_values(row["worldPosition"])
        for row in cull_view["authoredRoomRowsInStrictNativeDistanceOrder"]
    }
    known_authored = []
    for name in room_geometry["exactSelectedAspectRoomSurvivors"]:
        position = room_position_by_name[name]
        delta = [f32(position[index] - camera_position[index]) for index in range(3)]
        known_authored.append(
            {
                "name": name,
                "source": "SceneLight6Rarity",
                "priority": int(room_by_name[name]["priority"]),
                "cameraDistanceSquared": f32(dot(delta, delta)),
            }
        )
    for row in character_target_rows:
        known_authored.append(
            {
                "name": row["name"],
                "source": "light_overview",
                "priority": int(row["priority"]),
                "cameraDistanceSquared": float(row["cameraDistanceSquared"]["value"]),
            }
        )
    known_authored.sort(
        key=lambda row: (-int(row["priority"]), float(row["cameraDistanceSquared"]))
    )
    require("known_authored_survivor_count", len(known_authored), 17, "room + character overview")
    known_authored_order = [row["name"] for row in known_authored]
    require(
        "known_authored_survivor_order",
        known_authored_order,
        KNOWN_AUTHORED_SURVIVOR_ORDER,
        "room + character overview",
    )

    return {
        "schema": "endfield.gacha-light-population-recovery.v4",
        "status": "zhuangfy_gacha_selected_aspect_known_authored_survivors_source_closed",
        "runtimeReady": False,
        "outcome": (
            "Installed Lua selects only light_overview from light_chr_0030_zhuangfy, "
            "initializes its four CharInfoLightFollower components, and selects the "
            "12-light SceneLight6Rarity room group for rarity 6. The resulting known "
            "serialized Unity-Light candidate union is exactly 18 enabled lights: "
            "3 type 0 and 15 type 2, with no authored cookies and one character-light "
            "shadow request. The shipped normal native path disables fallback and Gacha "
            "occlusion. The selected installed-client state is independently stored as "
            "3840x2160 by Unity and the game. At that 16:9 aspect, native AABB, authored "
            "OBB, and type-specific geometry admit exactly 11 room rows and reject only "
            "Spot Light (20). Installed layer data, identity placement, two decoded ACL "
            "pose streams, constant root motion, and the native follower equations admit "
            "all six character rows at the settled loop boundary and throughout both "
            "authored clips. The exact known authored contribution is therefore 17. This "
            "still does not close runtime/custom carry-in, the target-frame LightCullResult "
            "pointer/count, whole-list order, or retail lightCount."
        ),
        "installedInputs": source_hashes,
        "selection": {
            "characterId": "chr_0030_zhuangfy",
            "rarity": 6,
            "timelineAssetName": "gacha_char_zhuangfy",
            **lua_contract,
            "gachaLayer": gacha_layer,
            "activeRoomGroup": "SceneLight6Rarity",
        },
        "actorPlacement": actor_placement,
        "actorPose": actor_pose,
        "serializedCharacterPrefab": prefab,
        "knownActiveAuthoredCandidates": {
            "count": 18,
            "typeCounts": {str(key): value for key, value in sorted(type_counts.items())},
            "cookieCount": 0,
            "shadowRequestCount": 1,
            "room": {"group": "SceneLight6Rarity", "count": 12, "lights": room_rows},
            "character": {"group": "light_overview", "count": 6, "lights": operator_rows},
        },
        "nativeFollowerContract": {
            "methods": native_rows,
            "enumeration": (
                "InitLightFollower calls GetComponentsInChildren<CharInfoLightFollower>(true), "
                "maps followableNodeType 0 to Bip001 and 1 to Head_Local, then initializes "
                "each component with that transform."
            ),
            "lateTickModes": {
                "0": {
                    "position": "target.worldPosition + positionOffset",
                    "rotation": "unchanged",
                },
                "1": {
                    "position": "target.worldPosition + target.worldRotation * localPosition",
                    "rotation": "target.worldRotation * Quaternion.Euler(localRotationEuler)",
                },
            },
            "selectedFollowerCount": 4,
        },
        "nativeGeometryMethods": native_geometry_regions,
        "nativeCullBoundary": native_cull_boundary,
        "exactKnownAuthoredSelectedAspectSurvivors": {
            "count": len(known_authored),
            "setupStateRelativeOrder": known_authored_order,
            "rows": [
                {
                    **row,
                    "cameraDistanceSquared": float_evidence(row["cameraDistanceSquared"]),
                }
                for row in known_authored
            ],
            "scope": (
                "exact relative order of the 17 known authored survivors only; unknown "
                "persistent/global or runtime-created records may interleave"
            ),
        },
        "evidenceBoundary": {
            "closed": [
                "installed Lua prefab path and direct-child activation rule",
                "rarity-6 GachaRoom group selection",
                "all 44 serialized character-prefab Unity Lights and six page groups",
                "six selected light_overview rows and four follower records",
                "twelve selected SceneLight6Rarity room rows",
                "known 18-row authored type/cookie/shadow census",
                "installed native follower traversal, node selection, and transform modes",
                "installed Gacha layer index 30, recursive assignment, and selected-view mask gate",
                "identity GachaRoom/TimelineRoot, character prefab, model, and light-root placement",
                "entrance and loop direct QVV pose chains with no mapped muscle lanes",
                "constant decoded ACL root-motion streams and remove-start-offset identity result",
                "shipped normal candidate core with fallback and Gacha occlusion disabled",
                "generic room layer/mask gate for all twelve room rows",
                "read-only installed-client 3840x2160 selection from matching Unity and game registry values",
                "selected-aspect initial AABB, authored OBB, and type-specific geometry for all twelve room rows",
                "exact 11-row selected-aspect room subset and Spot Light (20) rejection",
                "exact six-row selected-aspect character subset at the settled loop boundary and across all 844 decoded QVV frames",
                "exact 17-row known authored contribution and its internal priority/distance order",
            ],
            "open": [
                "target-frame HGCullingSystem.CullLights pointer/count and survivors",
                "room outcomes for display aspects other than this installed-client 16:9 selection",
                "persistent/global carry-in or runtime-created custom lights",
                "whole-list priority/distance order, LightDataBuffer rows, and lightCount",
            ],
            "decision": (
                "Use 18 as the exact known serialized input population, 11 as the exact "
                "selected-aspect authored room contribution, six as the exact character "
                "contribution, and 17 as the exact known authored survivor contribution. "
                "Do not publish those 17 rows as the complete retail survivor array or "
                "enable deferred pass 0 until runtime/custom carry-in and the native "
                "target-frame result are captured or otherwise source-closed."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate that the committed generated contract is current without rewriting it.",
    )
    parser.add_argument("--skip-hash-pins", action="store_true")
    args = parser.parse_args()
    report = build_report(verify_hashes=not args.skip_hash_pins)
    serialized = json.dumps(report, indent=2) + "\n"
    if args.check:
        require(
            "generatedOutputExists",
            args.output.exists(),
            True,
            args.output,
        )
        actual = args.output.read_text(encoding="utf-8")
        require(
            "generatedOutputCurrent",
            hashlib.sha256(actual.encode("utf-8")).hexdigest(),
            hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            args.output,
        )
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(report["outcome"])
    print(f"{'checked' if args.check else 'wrote'} {args.output}")


if __name__ == "__main__":
    main()
