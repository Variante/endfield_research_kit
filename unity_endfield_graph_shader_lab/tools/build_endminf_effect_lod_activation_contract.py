#!/usr/bin/env python3
"""Build the exact four-root Endminf GameObject/LOD activation contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.common import check_installed_native_inputs  # noqa: E402

DEFAULT_STAGE = (
    LAB / "scratch/character_recovery/endminf_external_fx_rig/exact_four_root_stage"
)
DEFAULT_DUMP = (
    REPO / "tmp/animestudio/endminf_effect_lod_display/four_root_dump/GameObject"
)
OUTPUT = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects"
    / "endminf_effect_lod_activation_contract.json"
)
DEFAULT_GAMEASSEMBLY = None
DEFAULT_METADATA = None
IFIX_STATE = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
    / "installed_ifix_patch_state.json"
)
METADATA_TOOL = REPO / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"
NATIVE_MAP_TOOL = REPO / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py"
NATIVE_HASHES = {
    "gameAssembly": "c24495e51b406f03b03890c4788ee618ae022c991405be5d5b8b787cb775ae89",
    "metadata": "0076743397acadf03d3b0064343a963c7c88863b8160526d397e4b3efb96f02e",
    "ifix": "20e4244e60a47fa67c3d1bdebf9eb7722c64181abc979092498510ad7f612445",
}
CODE_REGISTRATION = 0x18A88E640
NATIVE_METHODS = (
    # key, type, type token, method, index, token, parameter names/types,
    # return type, VA, file offset, pinned scan size/hash
    ("overview_on_state_enter", "Beyond.Gameplay.AnimatorBehaviourPlayEffect",
     "0x0200021e", "OnStateEnter", 3694, "0x06000e6f",
     ("animator", "stateInfo", "layerIndex"),
     ("UnityEngine.Animator+AnimationEventCallback&",
      "UnityEngine.AnimatorStateInfo", "System.Int32"), "System.Void",
     0x183760E70, 0x375F870, 1528,
     "fe8826c696469d704c4ae4a8712e8ff63b0a499611c806fc00f4e3361876ad8e"),
    ("effect_instance_init_lod", "Beyond.Gameplay.EffectInstance", "0x02000e22",
     "InitLod", 24579, "0x06006004", (), (), "System.Void",
     0x1831F2E90, 0x31F1890, 309,
     "90af78f3b75084ede0b2fc00003fa21d4f5e370a28a5fc9711b08e7b4542d1cc"),
    ("effect_instance_set_setting", "Beyond.Gameplay.EffectInstance", "0x02000e22",
     "SetSettingLodLevel", 24549, "0x06005fe6", ("settingLodLevel", "init"),
     ("Beyond.Gameplay.SettingLodLevel", "System.Boolean"), "System.Void",
     0x1831F3C20, 0x31F2620, 227,
     "14b9e21228d65c35acfc659a8193431186c33d97fd21cd9fdab793964f80b918"),
    ("effect_instance_load_immediately", "Beyond.Gameplay.EffectInstance",
     "0x02000e22", "LoadImmediately", 24606, "0x0600601f", (), (),
     "System.Void", 0x183760A10, 0x375F410, 240,
     "58889b5b7b66255144d408c04d9c5eeb30bc116146592ab7aaa2b6f339d8b76b"),
    ("effect_instance_load_finish", "Beyond.Gameplay.EffectInstance",
     "0x02000e22", "LoadFinish", 24605, "0x0600601e",
     ("effectGameObject",), ("UnityEngine.GameObject",), "System.Void",
     0x183233430, 0x3231E30, 240,
     "66b93983a1635139653f3552ec81f551fbe422e1ab53736d2de3213b2f6ca3fb"),
    ("effect_manager_ctor", "Beyond.Gameplay.EffectManager", "0x02000e2c",
     ".ctor", 24796, "0x060060dd", (), (), "System.Void",
     0x184035580, 0x4033F80, 7542,
     "afdff33c72cd37efddfc65442d266592847d7e9fbd19c098b4f873e6bb632279"),
    ("effect_manager_get_quality", "Beyond.Gameplay.EffectManager", "0x02000e2c",
     "get_qualitySettingLodLevel", 24800, "0x060060e1", (), (),
     "Beyond.Gameplay.SettingLodLevel", 0x1831F3810, 0x31F2210, 48,
     "7ab8284069387d06350c6b9be83973771e757d71107c4b8752f74b6509ee4c85"),
    ("effect_manager_set_quality", "Beyond.Gameplay.EffectManager", "0x02000e2c",
     "SetQualitySettingLodLevel", 24823, "0x060060f8",
     ("settingLodLevel", "refresh"),
     ("Beyond.Gameplay.SettingLodLevel", "<type-index:108383>"), "System.Void",
     0x18391E330, 0x391CD30, 176,
     "1a0b79789e62a15722842a26e180fcae95ac12ba7294e51b4a35fb2585503428"),
    ("effect_manager_normalize", "Beyond.Gameplay.EffectManager", "0x02000e2c",
     "_NormalizeSingleSettingLodLevel", 24830, "0x060060ff",
     ("settingLodLevel", "fallback"),
     ("Beyond.Gameplay.SettingLodLevel", "Beyond.Gameplay.SettingLodLevel"),
     "Beyond.Gameplay.SettingLodLevel", 0x18391E3E0, 0x391CDE0, 97,
     "04dc2273e943b9a3c1a18740b4207725ef60a1336b261a3aebf1efb05be449d2"),
    ("effect_manager_create_stationary_3", "Beyond.Gameplay.EffectManager",
     "0x02000e2c", "CreateStationaryEffect", 24872, "0x06006129",
     ("name", "position", "rotation"),
     ("System.String+TrimType&", "UnityEngine.Vector3", "UnityEngine.Quaternion"),
     "<type-index:71153>", 0x18375FB40, 0x375E540, 352,
     "38e5463be2c9ab56ff4fc44d06d704d250d9d1868650deef99ef2c5a308a2042"),
    ("effect_manager_create_stationary_4", "Beyond.Gameplay.EffectManager",
     "0x02000e2c", "CreateStationaryEffect", 24873, "0x0600612a",
     ("name", "position", "rotation", "scale"),
     ("System.String+TrimType&", "UnityEngine.Vector3", "UnityEngine.Quaternion",
      "UnityEngine.Vector3"), "<type-index:71153>",
     0x18375F2C0, 0x375DCC0, 384,
     "b6a54b98bbd5805f8912bae36602147979341443c4c545f4162576f2bdf40eaa"),
    ("effect_setting_set_all_setting", "Beyond.Gameplay.EffectSetting", "0x02000e45",
     "SetAllSettingLod", 25034, "0x060061cb", ("settingLodLevel",),
     ("Beyond.Gameplay.SettingLodLevel",), "System.Void",
     0x1831F5B70, 0x31F4570, 1376,
     "b88aab7391555c735febf0cb6fa78a8abbf75dc45f0822a3498050b21aff56ff"),
    ("effect_setting_set_all_target", "Beyond.Gameplay.EffectSetting", "0x02000e45",
     "SetAllTargetLayers", 25036, "0x060061cd", ("targetLayers",),
     ("Beyond.Gameplay.EffectTargetLayers",), "System.Void",
     0x1831F4260, 0x31F2C60, 1104,
     "48572b48e9c9053ffff311cba6289a5e8b77719952e5375ce30adb4d5e6298f4"),
    ("battle_normal_refresh_guard_lod_alpha", "Beyond.Gameplay.BattleNormalEffect",
     "0x02000e24", "_RefreshGuardLodAlpha", 24673, "0x06006062",
     ("dynamicChange",), ("<type-index:108383>",), "System.Void",
     0x183237FC0, 0x32369C0, 704,
     "8651b52ed6aa970a7e57a0ff367df7fa9e4bc9a9314f49227654ebf552a86e25"),
    ("battle_normal_refresh_tower_lod", "Beyond.Gameplay.BattleNormalEffect",
     "0x02000e24", "_RefreshTowerLod", 24679, "0x06006068", (), (),
     "System.Void", 0x183237C60, 0x3236660, 592,
     "60cf6a46467202609b0cf8ea9901c27b8ee3dffc4f30d42289cfa7ebf4bff146"),
    ("effect_lod_init_data", "Beyond.Gameplay.EffectLodCfg", "0x02000e4d",
     "InitData", 25059, "0x060061e4", (), (), "System.Void",
     0x1831F69F0, 0x31F53F0, 3184,
     "e957d6825e82f4cd40c6ac0b6f3969e161026cf24e75a001c0cb805a0d5a34c0"),
    ("effect_lod_refresh", "Beyond.Gameplay.EffectLodCfg", "0x02000e4d",
     "_RefreshLod", 25063, "0x060061e8", ("isLodFade",),
     ("<type-index:108383>",), "System.Void",
     0x1831F6870, 0x31F5270, 368,
     "67887805a2c160e4413322a48f1d8762a48114a8f1c1b30687978074fd3a7189"),
    ("effect_lod_ctor", "Beyond.Gameplay.EffectLodCfg", "0x02000e4d",
     ".ctor", 25086, "0x060061ff", (), (), "System.Void",
     0x183AE45A0, 0x3AE2FA0, 799,
     "7a1999284d25a61e4e983d8bdb7ba49e82fb6ae368c8c589e31beaf4e0db4091"),
)
NORMAL_CREATION_ROUTE_METHOD_KEYS = (
    "overview_on_state_enter",
    "effect_manager_create_stationary_3",
    "effect_manager_create_stationary_4",
    "effect_instance_load_immediately",
    "effect_instance_load_finish",
    "effect_instance_init_lod",
)
TARGET_LAYER_CALLER_WINDOWS = (
    # _RefreshTowerLod retains one compiler-split cold call. Its exact call
    # and jump back into the expanded pinned hot body close method ownership.
    ("battle_normal_refresh_tower_lod_cold", 0x184D46ECE, 0x4D458CE, 135,
     "f9b3ef1f9750f4d47ae727a63482efd639f5d1e566455fc65da5160a55886111"),
)
NATIVE_FIELDS = (
    ("Beyond.Gameplay.EffectInstance", "m_settingLodLevel", "0x04005245", 0xAC),
    ("Beyond.Gameplay.EffectManager", "m_qualitySettingLodLevel", "0x040052c8", 0x120),
    ("Beyond.Gameplay.EffectSetting", "lodSetting", "0x04005351", 0xB0),
    ("Beyond.Gameplay.EffectLodCfg", "settingLodLevel", "0x0400538c", 0x40),
    ("Beyond.Gameplay.EffectLodCfg", "targetLayer", "0x0400538e", 0x48),
    ("Beyond.Gameplay.EffectLodCfg", "m_initActive", "0x04005390", 0x58),
    ("Beyond.Gameplay.EffectLodCfg", "m_curActive", "0x04005391", 0x59),
    ("Beyond.Gameplay.EffectLodCfg", "m_isShowLod", "0x04005397", 0x6D),
    ("Beyond.Gameplay.EffectLodCfg", "m_showSettingLodLevel", "0x04005398", 0x70),
    ("Beyond.Gameplay.EffectLodCfg", "m_distanceLodInfo", "0x04005399", 0x78),
    ("Beyond.Gameplay.EffectLodCfg", "m_showTargetLayers", "0x040053a2", 0xC0),
)
NATIVE_GATES = (
    ("effect_lod_ctor_defaults", 0x3AE329B,
     bytes.fromhex("c7 46 70 08 00 00 00 c7 86 c0 00 00 00 01 00 00 00"),
     "EffectLodCfg runtime show defaults are quality=8 and target=1"),
    ("effect_manager_ctor_quality_default", 0x403538B,
     bytes.fromhex("c7 83 20 01 00 00 08 00 00 00"),
     "EffectManager quality default at +0x120 is 8"),
    ("set_quality_normalize_fallback_and_store", 0x391CD78,
     bytes.fromhex("45 33 c0 ba 08 00 00 00 8b ce e8 59 00 00 00 89 83 20 01 00 00"),
     "SetQuality passes fallback 8 to Normalize and stores its result at +0x120"),
    ("normalize_quality_domain", 0x391CE02,
     bytes.fromhex("8d 47 ff 83 f8 01 74 22 85 c0 74 2c 83 e8 02 74 0c 83 f8 01 74 1b 83 ff 08 75 02 8b df 8b c3 48 8b 5c 24 30 48 83 c4 20 5f c3 bb 02 00 00 00 eb ec bb 04 00 00 00 eb e5 bb 01 00 00 00 eb de"),
     "Normalize admits 1,2,4,8 and otherwise retains fallback 8"),
    ("init_lod_get_quality_then_set", 0x31F195A,
     bytes.fromhex("33 d2 e8 af 08 00 00 45 33 c9 41 b0 01 8b d0 48 8b cb 48 83 c4 30 5b e9 aa 0c 00 00"),
     "InitLod gets manager quality and tail-enters SetSettingLodLevel(init=true)"),
    ("set_setting_to_all_rows", 0x31F26BC,
     bytes.fromhex("48 8b 8b a0 00 00 00 48 85 c9 0f 84 8a 00 00 00 45 33 c0 8b d6 e8 9a 1e 00 00"),
     "SetSettingLodLevel calls EffectSetting.SetAllSettingLod"),
    ("set_all_setting_refresh", 0x31F47E0,
     bytes.fromhex("44 89 76 70 45 33 c0 33 d2 48 8b ce e8 7f 0a 00 00"),
     "SetAllSettingLod writes m_showSettingLodLevel and calls _RefreshLod(false)"),
    ("init_data_active_self", 0x31F57F1,
     bytes.fromhex("ff d0 48 8b 5f 18 88 47 58 88 47 59"),
     "InitData copies the GameObject active getter result into m_initActive/m_curActive"),
    ("refresh_predicate_and_set_active", 0x31F52D1,
     bytes.fromhex("8b 43 70 c6 43 10 00 85 43 40 0f 84 96 00 00 00 8b 83 c0 00 00 00 b9 00 00 00 00 85 43 48 0f 97 c0 88 43 6d 48 83 7b 78 00 74 14 84 c0 74 73 48 8b 43 78 0f b6 40 14 85 c0 0f 95 c0 88 43 6d 80 7b 6d 00 74 04 0f b6 4b 58 85 c9 40 0f 95 c7 40 84 f6 75 36 48 8b 73 18 48 85 f6 0f 84 a9 00 00 00 48 8b 05 e7 81 cb 0a 48 85 c0 74 72 40 0f b6 d7 48 8b ce ff d0 40 88 7b 59"),
     "_RefreshLod intersects both masks and distance-active, ANDs m_initActive, calls GameObject.SetActive, and stores m_curActive"),
)
EXPECTED_ROOTS = {
    "P_fxui_endminm003_overview_01",
    "P_fxui_endminm003_overview_02",
    "P_fxui_endminm003_overview_03",
    "P_fxui_endminm003_overview_04",
}
NAME_RE = re.compile(r'^\s*string m_Name = "(.*)"\s*$', re.MULTILINE)
ACTIVE_RE = re.compile(r"^\s*bool m_IsActive = (True|False)\s*$", re.MULTILINE)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def path_id(path: Path) -> int:
    value = int(path.stem.rsplit("_p", 1)[1], 16)
    return value if value < (1 << 63) else value - (1 << 64)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load native evidence helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_native_window(gameassembly: Path, offset: int, size: int) -> bytes:
    with gameassembly.open("rb") as stream:
        stream.seek(offset)
        value = stream.read(size)
    require(len(value) == size, f"native window is truncated at 0x{offset:x}")
    return value


def relative_target(va: int, code: bytes, index: int) -> int:
    require(code[index] in (0xE8, 0xE9), "native relative branch opcode drifted")
    displacement = struct.unpack_from("<i", code, index + 1)[0]
    return va + index + 5 + displacement


def validate_metadata_and_pointers(gameassembly: Path, metadata: Path) -> tuple[list, list]:
    catalog = load_module("endminf_lod_activation_metadata", METADATA_TOOL)
    md = catalog.Metadata(metadata)
    types = {}
    for type_def in md.types:
        full_name = md.type_full_name(type_def)
        if full_name in {row[1] for row in NATIVE_METHODS}:
            require(full_name not in types, f"duplicate native metadata type: {full_name}")
            types[full_name] = type_def
    require(set(types) == {row[1] for row in NATIVE_METHODS},
            "required native metadata types are missing")

    identities = []
    for (key, type_name, type_token, method_name, method_index, token,
         parameter_names, parameter_types, return_type, va, *_rest) in NATIVE_METHODS:
        type_def = types[type_name]
        require(md.image_name_by_type_index[type_def.index] == "Gameplay.Beyond.dll" and
                f"0x{type_def.token:08x}" == type_token,
                f"native type identity drifted: {type_name}")
        candidates = [catalog.method_row(md, method)
                      for method in md.methods_for(type_def)]
        row = next((item for item in candidates if item["index"] == method_index), None)
        require(row is not None and row["name"] == method_name and row["token"] == token and
                tuple(row["parameters"]) == parameter_names and
                tuple(item["typeName"] for item in row["parameterDetails"]) ==
                    parameter_types and row["returnTypeName"] == return_type,
                f"native method identity drifted: {key}")
        identities.append({
            "key": key, "type": type_name, "typeToken": type_token,
            "method": method_name, "methodIndex": method_index, "token": token,
            "virtualAddress": f"0x{va:x}",
        })

    fields = []
    for type_name, field_name, token, offset in NATIVE_FIELDS:
        candidates = [catalog.field_row(md, field) for field in md.fields_for(types[type_name])]
        row = next((item for item in candidates if item["name"] == field_name), None)
        require(row is not None and row["token"] == token,
                f"native field identity drifted: {type_name}.{field_name}")
        fields.append({
            "type": type_name, "field": field_name, "token": token,
            "nativeOffset": f"0x{offset:x}",
        })

    mapper = load_module("endminf_lod_activation_mapper", NATIVE_MAP_TOOL)
    pe = mapper.PeImage(gameassembly)
    modules = mapper.parse_codegen_modules(pe, CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(md)
    pointers_by_image, _ = mapper.build_pointer_indexes(pe, md, modules, ranges)
    image_range = ranges["Gameplay.Beyond.dll"]
    pointers = pointers_by_image["Gameplay.Beyond.dll"]
    for identity, method in zip(identities, NATIVE_METHODS):
        slot = method[4] - image_range["methodStart"]
        require(0 <= slot < len(pointers) and pointers[slot] == method[9],
                f"native method pointer mapping drifted: {method[0]}")
        identity["moduleMethodSlot"] = slot
    return identities, fields


def validate_native(gameassembly: Path | None, metadata: Path | None,
                    ifix_state: Path) -> dict:
    installed = check_installed_native_inputs(
        NATIVE_HASHES["gameAssembly"], NATIVE_HASHES["metadata"],
        gameassembly=gameassembly, metadata=metadata,
    )
    require(installed.validated,
            f"installed native input gate failed closed ({installed.status}): "
            f"{installed.detail}")
    gameassembly = installed.gameassembly
    metadata = installed.metadata
    identities, fields = validate_metadata_and_pointers(gameassembly, metadata)

    bodies = []
    for method in NATIVE_METHODS:
        body = read_native_window(gameassembly, method[10], method[11])
        require(sha256_bytes(body) == method[12],
                f"native method body drifted: {method[0]}")
        bodies.append({
            "key": method[0], "virtualAddress": f"0x{method[9]:x}",
            "fileOffset": f"0x{method[10]:x}", "scanByteCount": method[11],
            "sha256": method[12],
        })
    gates = []
    for name, offset, expected, meaning in NATIVE_GATES:
        actual = read_native_window(gameassembly, offset, len(expected))
        require(actual == expected, f"native default/predicate gate drifted: {name}")
        gates.append({
            "name": name, "fileOffset": f"0x{offset:x}",
            "bytes": expected.hex(" "), "meaning": meaning,
        })

    method_by_key = {row[0]: row for row in NATIVE_METHODS}
    call_gates = (
        ("set_quality_normalize_fallback_and_store", 0x18391E378, 10,
         "effect_manager_normalize"),
        ("init_lod_get_quality", 0x1831F2F5A, 2, "effect_manager_get_quality"),
        ("init_lod_tail_set_setting", 0x1831F2F5A, 23, "effect_instance_set_setting"),
        ("set_setting_to_all_rows", 0x1831F3CBC, 21, "effect_setting_set_all_setting"),
        ("set_all_setting_refresh", 0x1831F5DE0, 12, "effect_lod_refresh"),
    )
    calls = []
    gate_by_name = {row[0]: row for row in NATIVE_GATES}
    for name, va, index, target_key in call_gates:
        gate_name = name if name in gate_by_name else "init_lod_get_quality_then_set"
        code = gate_by_name[gate_name][2]
        target = relative_target(va, code, index)
        require(target == method_by_key[target_key][9], f"native call target drifted: {name}")
        calls.append({"name": name, "target": target_key,
                      "targetVirtualAddress": f"0x{target:x}"})

    mapper = load_module("endminf_lod_activation_xref_mapper", NATIVE_MAP_TOOL)
    pe = mapper.PeImage(gameassembly)
    trigger = load_module(
        "endminf_lod_activation_xref_helper",
        LAB / "tools/build_endminf_effect_nanguan_trigger_contract.py",
    )
    target_xrefs, sections = trigger._direct_rel32_xrefs(
        pe, method_by_key["effect_setting_set_all_target"][9]
    )
    require(
        [int(row["callVirtualAddress"], 16) for row in target_xrefs] ==
        [0x183237E09, 0x183238163, 0x18323819A, 0x184D46F41],
        "SetAllTargetLayers direct-caller census drifted",
    )
    cold_windows = []
    for name, va, offset, size, expected_hash in TARGET_LAYER_CALLER_WINDOWS:
        code = read_native_window(gameassembly, offset, size)
        require(sha256_bytes(code) == expected_hash,
                f"SetAllTargetLayers caller ownership window drifted: {name}")
        cold_windows.append({
            "name": name, "virtualAddress": f"0x{va:x}",
            "fileOffset": f"0x{offset:x}", "byteCount": size,
            "sha256": expected_hash,
        })

    guard = method_by_key["battle_normal_refresh_guard_lod_alpha"]
    tower = method_by_key["battle_normal_refresh_tower_lod"]
    guard_body = read_native_window(gameassembly, guard[10], guard[11])
    cold = read_native_window(
        gameassembly, TARGET_LAYER_CALLER_WINDOWS[0][2],
        TARGET_LAYER_CALLER_WINDOWS[0][3],
    )
    for index in (0x1A3, 0x1DA):
        require(relative_target(guard[9], guard_body, index) ==
                method_by_key["effect_setting_set_all_target"][9],
                "hot SetAllTargetLayers caller edge drifted")
    require(relative_target(tower[9], read_native_window(
        gameassembly, tower[10], tower[11]), 0x1A9) ==
        method_by_key["effect_setting_set_all_target"][9],
        "hot _RefreshTowerLod SetAllTargetLayers edge drifted")
    cold_edges = ((0x73, "call"), (0x82, "return"))
    for index, kind in cold_edges:
        target = relative_target(TARGET_LAYER_CALLER_WINDOWS[0][1], cold, index)
        expected = (method_by_key["effect_setting_set_all_target"][9]
                    if kind == "call" else 0x183237D61)
        require(target == expected,
                f"cold SetAllTargetLayers caller {kind} edge drifted")
    require(tower[9] <= 0x183237D61 < tower[9] + tower[11],
            "cold _RefreshTowerLod return target left its pinned hot body")

    caller_keys = {
        "battle_normal_refresh_guard_lod_alpha",
        "battle_normal_refresh_tower_lod",
    }
    require(not caller_keys.intersection(NORMAL_CREATION_ROUTE_METHOD_KEYS),
            "SetAllTargetLayers caller entered the normal creation route")
    identity_by_key = {row["key"]: row for row in identities}
    target_layer_owners = [
        {
            "owner": identity_by_key["battle_normal_refresh_guard_lod_alpha"],
            "bodyRange": [f"0x{guard[9]:x}", f"0x{guard[9] + guard[11]:x}"],
            "callVirtualAddresses": ["0x183238163", "0x18323819a"],
            "codePlacement": "pinned hot method body",
        },
        {
            "owner": identity_by_key["battle_normal_refresh_tower_lod"],
            "bodyRange": [f"0x{tower[9]:x}", f"0x{tower[9] + tower[11]:x}"],
            "coldWindow": cold_windows[0],
            "coldReturnVirtualAddress": "0x183237d61",
            "callVirtualAddresses": ["0x183237e09", "0x184d46f41"],
            "codePlacement": "hash-pinned hot and cold blocks with an exact jump into the hot body",
        },
    ]

    require(sha256_file(ifix_state) == NATIVE_HASHES["ifix"],
            "installed IFix snapshot hash drifted")
    ifix = json.loads(ifix_state.read_text(encoding="utf-8"))
    source_build = ifix["source_build"]
    require(source_build["game_assembly"]["sha256"] == NATIVE_HASHES["gameAssembly"] and
            source_build["global_metadata"]["sha256"] == NATIVE_HASHES["metadata"] and
            str(source_build.get("code_registration", "")).lower() ==
            f"0x{CODE_REGISTRATION:x}",
            "installed IFix snapshot build join drifted")
    relevant = {(row[1], row[3]) for row in NATIVE_METHODS}
    observed = {(str(row.get("type")), str(row.get("method")))
                for row in ifix.get("targets", [])}
    require(not (relevant & observed),
            f"installed IFix snapshot replaces LOD route: {sorted(relevant & observed)}")

    return {
        "gameAssemblySha256": NATIVE_HASHES["gameAssembly"],
        "globalMetadataSha256": NATIVE_HASHES["metadata"],
        "methodIdentities": identities, "fieldIdentities": fields,
        "methodBodies": bodies, "byteGates": gates, "callGates": calls,
        "setAllTargetLayersDirectCallers": target_xrefs,
        "setAllTargetLayersCallerOwners": target_layer_owners,
        "normalCreationRouteMethodIdentities": [
            identity_by_key[key] for key in NORMAL_CREATION_ROUTE_METHOD_KEYS
        ],
        "normalCreationRouteDirectCallerExcluded": True,
        "executableSectionsScanned": [row["name"] for row in sections],
        "recordedInstalledIfixNonreplacement": True,
    }


def build(stage: Path, dump_root: Path, gameassembly: Path | None = DEFAULT_GAMEASSEMBLY,
          metadata: Path | None = DEFAULT_METADATA, ifix_state: Path = IFIX_STATE) -> dict:
    native = validate_native(gameassembly, metadata, ifix_state)
    source_rows = {}
    for path in sorted(dump_root.glob("*.txt"), key=lambda item: item.name):
        text = canonical_bytes(path).decode("utf-8")
        name_match = NAME_RE.search(text)
        active_match = ACTIVE_RE.search(text)
        require(name_match is not None, f"missing serialized GameObject name: {path}")
        require(active_match is not None, f"missing serialized m_IsActive: {path}")
        game_object_path_id = path_id(path)
        require(game_object_path_id not in source_rows,
                f"duplicate GameObject PathID: {game_object_path_id}")
        source_rows[game_object_path_id] = {
            "gameObjectPathId": game_object_path_id,
            "name": name_match.group(1),
            "authoredInitialActive": active_match.group(1) == "True",
            "typeTreeDumpSha256": sha256_bytes(canonical_bytes(path)),
        }

    staged_rows = {}
    for path in sorted((stage / "GameObject").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        staged_rows[path_id(path)] = str(payload["m_Name"])
    require(source_rows, "no original GameObject TypeTree dumps were found")
    require(set(source_rows) == set(staged_rows),
            "TypeTree/staged GameObject PathID census drifted")
    for game_object_path_id, name in staged_rows.items():
        require(source_rows[game_object_path_id]["name"] == name,
                f"TypeTree/staged GameObject name drifted: {game_object_path_id}")

    rows = [source_rows[key] for key in sorted(source_rows)]
    require(len(rows) == 101, "four-root GameObject census drifted")
    require(all(row["authoredInitialActive"] for row in rows),
            "the pinned four-root source gained an initially inactive GameObject")
    root_names = {row["name"] for row in rows if row["name"] in EXPECTED_ROOTS}
    require(root_names == EXPECTED_ROOTS, "four-root identity census drifted")
    return {
        "schema": "endfield.endminf-effect-lod-activation.v1",
        "status": "source_closed_normal_creation_defaults",
        "runtimeDefaults": {
            "qualitySettingLodLevel": 8,
            "qualityNormalizationDomain": [1, 2, 4, 8],
            "targetLayers": 1,
        },
        "nativeEvidence": native,
        "source": {
            "kind": "original Unity GameObject TypeTree Dump",
            "gameObjectCount": len(rows),
            "allAuthoredInitiallyActive": True,
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--dump-root", type=Path, default=DEFAULT_DUMP)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--ifix-state", type=Path, default=IFIX_STATE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build(args.stage, args.dump_root, args.gameassembly, args.metadata,
                    args.ifix_state)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        require(OUTPUT.read_text(encoding="utf-8") == text,
                "published Endminf LOD activation contract drifted")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print("build_endminf_effect_lod_activation_contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
