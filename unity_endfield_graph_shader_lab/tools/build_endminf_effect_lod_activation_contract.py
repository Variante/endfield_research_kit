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
LIFECYCLE_AUDIT = REPO / "reports/assets/endminf_effect_lifecycle_native_audit.json"
METADATA_TOOL = REPO / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"
NATIVE_MAP_TOOL = REPO / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py"
NATIVE_HASHES = {
    "gameAssembly": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    "metadata": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    "ifix": "71eaa80479920463835ef5fabc7697dfeea5fef9f287c109e994fca7edcdb9af",
    "lifecycleAudit": "1414f67ae318e8afbca752eb45a8dda615be0198f88d60e66ea1331ee182d438",
}
NATIVE_METHODS = (
    # key, type, type token, method, index, token, parameter names/types,
    # return type, VA, file offset, pinned scan size/hash
    ("overview_on_state_enter", "Beyond.Gameplay.AnimatorBehaviourPlayEffect",
     "0x02000210", "OnStateEnter", 3566, "0x06000def",
     ("animator", "stateInfo", "layerIndex"),
     ("UnityEngine.Animator+AnimationEventCallback&",
      "UnityEngine.AnimatorStateInfo", "System.Int32"), "System.Void",
     0x186B85E54, 0x6B84454, 1528,
     "ece99aba984d97b01f050e3b5b4ae512a1df5dc26d0fd0388a1abb5e994f7f0e"),
    ("effect_instance_init_lod", "Beyond.Gameplay.EffectInstance", "0x02000d8e",
     "InitLod", 23218, "0x06005ab3", (), (), "System.Void",
     0x1834F7FB0, 0x34F65B0, 309,
     "f2232ed06251f2d5c70374c51581c07aaf1c5a3cb5ecc7033d1ce31b964b4094"),
    ("effect_instance_set_setting", "Beyond.Gameplay.EffectInstance", "0x02000d8e",
     "SetSettingLodLevel", 23188, "0x06005a95", ("settingLodLevel", "init"),
     ("Beyond.Gameplay.SettingLodLevel", "System.Boolean"), "System.Void",
     0x1834F98C0, 0x34F7EC0, 227,
     "f668ea4c2e5fc43a6edb56aa3a2b5de7011b214e130a2430b1faa05d5cee27ae"),
    ("effect_instance_load_immediately", "Beyond.Gameplay.EffectInstance",
     "0x02000d8e", "LoadImmediately", 23245, "0x06005ace", (), (),
     "System.Void", 0x183B76030, 0x3B74630, 240,
     "64183251a8b5de49da081bfeaef247da8d2e9d59ebd69da3136ccde6ab19a5bb"),
    ("effect_instance_load_finish", "Beyond.Gameplay.EffectInstance",
     "0x02000d8e", "LoadFinish", 23244, "0x06005acd",
     ("effectGameObject",), ("UnityEngine.GameObject",), "System.Void",
     0x183963320, 0x3961920, 240,
     "57bb65439641fc8c51f86b29aa9f55803480d536fee3e19494a890bdd91c69ab"),
    ("effect_manager_ctor", "Beyond.Gameplay.EffectManager", "0x02000d98",
     ".ctor", 23430, "0x06005b87", (), (), "System.Void",
     0x1840E6020, 0x40E4620, 1120,
     "468ef91bda0ddc521e7fc4642080c8960564d9d32474cef68c8e4935f18b53b7"),
    ("effect_manager_get_quality", "Beyond.Gameplay.EffectManager", "0x02000d98",
     "get_qualitySettingLodLevel", 23434, "0x06005b8b", (), (),
     "Beyond.Gameplay.SettingLodLevel", 0x1834F80F0, 0x34F66F0, 48,
     "8addebd709c459ad542000c7e889693f2d2b91b1a5479193d44054878986f07c"),
    ("effect_manager_set_quality", "Beyond.Gameplay.EffectManager", "0x02000d98",
     "SetQualitySettingLodLevel", 23457, "0x06005ba2",
     ("settingLodLevel", "refresh"),
     ("Beyond.Gameplay.SettingLodLevel", "<type-index:130844>"), "System.Void",
     0x183F92910, 0x3F90F10, 176,
     "4ab4d06af5a49c3ee913d57fbb956422d5f58070db01f225ea5e9e22b3647f68"),
    ("effect_manager_normalize", "Beyond.Gameplay.EffectManager", "0x02000d98",
     "_NormalizeSingleSettingLodLevel", 23464, "0x06005ba9",
     ("settingLodLevel", "fallback"),
     ("Beyond.Gameplay.SettingLodLevel", "Beyond.Gameplay.SettingLodLevel"),
     "Beyond.Gameplay.SettingLodLevel", 0x183F929C0, 0x3F90FC0, 64,
     "31be9f58e68c86724d59ba9b8e023aa79ca30a37911cfc19a5b5d778699a1de9"),
    ("effect_manager_create_stationary_3", "Beyond.Gameplay.EffectManager",
     "0x02000d98", "CreateStationaryEffect", 23505, "0x06005bd2",
     ("name", "position", "rotation"),
     ("System.String+TrimType&", "UnityEngine.Vector3", "UnityEngine.Quaternion"),
     "<type-index:84351>", 0x183287D20, 0x3286320, 352,
     "cada808963deaa752d22161d1aee57d7e1193e159b1f73866329c39b15cc5f30"),
    ("effect_manager_create_stationary_4", "Beyond.Gameplay.EffectManager",
     "0x02000d98", "CreateStationaryEffect", 23506, "0x06005bd3",
     ("name", "position", "rotation", "scale"),
     ("System.String+TrimType&", "UnityEngine.Vector3", "UnityEngine.Quaternion",
      "UnityEngine.Vector3"), "<type-index:84351>",
     0x1833D1300, 0x33CF900, 384,
     "e0394fde17f20729ceadb855619a26c29776bece98b049bf6866fc4a7f49d376"),
    ("effect_setting_set_all_setting", "Beyond.Gameplay.EffectSetting", "0x02000db1",
     "SetAllSettingLod", 23665, "0x06005c72", ("settingLodLevel",),
     ("Beyond.Gameplay.SettingLodLevel",), "System.Void",
     0x18339B920, 0x3399F20, 1376,
     "17eb415f3ef38bd3e3a9b81fbe9de848d96d2b52818eb84c07111e740348bc48"),
    ("effect_setting_set_all_target", "Beyond.Gameplay.EffectSetting", "0x02000db1",
     "SetAllTargetLayers", 23667, "0x06005c74", ("targetLayers",),
     ("Beyond.Gameplay.EffectTargetLayers",), "System.Void",
     0x1834FC030, 0x34FA630, 1104,
     "71849fe5fd0029f26a2ff5d12c26159073ccebff73faec3aa84f39231fef4a2f"),
    ("battle_normal_refresh_guard_lod_alpha", "Beyond.Gameplay.BattleNormalEffect",
     "0x02000d90", "_RefreshGuardLodAlpha", 23312, "0x06005b11",
     ("dynamicChange",), ("<type-index:130844>",), "System.Void",
     0x1834FAC90, 0x34F9290, 704,
     "717b3738f2628eb90fcf1a6303dc23c60f382558def12cc80518d63fd9b0ec7c"),
    ("battle_normal_refresh_tower_lod", "Beyond.Gameplay.BattleNormalEffect",
     "0x02000d90", "_RefreshTowerLod", 23318, "0x06005b17", (), (),
     "System.Void", 0x1834FAAF0, 0x34F90F0, 272,
     "d4d44ea96f75b55d10b70393c4a5fdc91e006264cc997967d0d65110a69dfdd3"),
    ("effect_lod_init_data", "Beyond.Gameplay.EffectLodCfg", "0x02000db9",
     "InitData", 23690, "0x06005c8b", (), (), "System.Void",
     0x18339D940, 0x339BF40, 3184,
     "b8608c742c988a67fd3a813355673e6a9d9319ce2c7f37fd00afc6825352b6e4"),
    ("effect_lod_refresh", "Beyond.Gameplay.EffectLodCfg", "0x02000db9",
     "_RefreshLod", 23694, "0x06005c8f", ("isLodFade",),
     ("<type-index:130844>",), "System.Void",
     0x18339D7D0, 0x339BDD0, 368,
     "fb68df2db8aa3bf21590207f6079d54809b4f82888b9cb9cac3134367741d1a7"),
    ("effect_lod_ctor", "Beyond.Gameplay.EffectLodCfg", "0x02000db9",
     ".ctor", 23717, "0x06005ca6", (), (), "System.Void",
     0x183C2F600, 0x3C2DC00, 288,
     "6dcd0766663144c3ee19571a633601344f3719d5811e4094cfa9825ff86fb6fe"),
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
    # _RefreshTowerLod has compiler-split cold blocks. The exact calls and
    # jumps back into its pinned hot body close their method ownership.
    ("battle_normal_refresh_tower_lod_cold", 0x185090C80, 0x508F280, 218,
     "ba2305de6d6800dd541efb86a3ae7ac44ab184e5f7ad6dcc01c2717cbdc2ae4b"),
)
NATIVE_FIELDS = (
    ("Beyond.Gameplay.EffectInstance", "m_settingLodLevel", "0x04004de1", 0x8C),
    ("Beyond.Gameplay.EffectManager", "m_qualitySettingLodLevel", "0x04004e63", 0x120),
    ("Beyond.Gameplay.EffectSetting", "lodSetting", "0x04004eec", 0xB0),
    ("Beyond.Gameplay.EffectLodCfg", "settingLodLevel", "0x04004f27", 0x40),
    ("Beyond.Gameplay.EffectLodCfg", "targetLayer", "0x04004f29", 0x48),
    ("Beyond.Gameplay.EffectLodCfg", "m_initActive", "0x04004f2b", 0x58),
    ("Beyond.Gameplay.EffectLodCfg", "m_curActive", "0x04004f2c", 0x59),
    ("Beyond.Gameplay.EffectLodCfg", "m_isShowLod", "0x04004f32", 0x6D),
    ("Beyond.Gameplay.EffectLodCfg", "m_showSettingLodLevel", "0x04004f33", 0x70),
    ("Beyond.Gameplay.EffectLodCfg", "m_distanceLodInfo", "0x04004f34", 0x78),
    ("Beyond.Gameplay.EffectLodCfg", "m_showTargetLayers", "0x04004f3d", 0xC0),
)
NATIVE_GATES = (
    ("effect_lod_ctor_defaults", 0x3C2DCE7,
     bytes.fromhex("c7 43 70 08 00 00 00 c7 83 c0 00 00 00 01 00 00 00"),
     "EffectLodCfg runtime show defaults are quality=8 and target=1"),
    ("effect_manager_ctor_quality_default", 0x40E4A4D,
     bytes.fromhex("c7 83 20 01 00 00 08 00 00 00"),
     "EffectManager quality default at +0x120 is 8"),
    ("set_quality_normalize_fallback_and_store", 0x3F90F58,
     bytes.fromhex("45 33 c0 ba 08 00 00 00 8b ce e8 59 00 00 00 89 83 20 01 00 00"),
     "SetQuality passes fallback 8 to Normalize and stores its result at +0x120"),
    ("normalize_quality_hot", 0x3F90FE2,
     bytes.fromhex("8d 57 ff 83 fa 03 0f 85 46 4d 2a 01 bb 04 00 00 00"),
     "Normalize admits 4 in the hot body and branches every other input to the cold body"),
    ("normalize_quality_cold", 0x5235D34,
     bytes.fromhex("85 d2 74 28 83 ea 01 74 19 83 fa 01 0f 84 ad b2 d5 fe 83 ff 08 0f 85 a4 b2 d5 fe 8b df e9 9d b2 d5 fe bb 02 00 00 00 e9 93 b2 d5 fe bb 01 00 00 00"),
     "Normalize admits 1,2,8 and otherwise retains fallback 8"),
    ("init_lod_get_quality_then_set", 0x34F667A,
     bytes.fromhex("33 d2 e8 6f 00 00 00 45 33 c9 41 b0 01 8b d0 48 8b cb 48 83 c4 30 5b e9 2a 18 00 00"),
     "InitLod gets manager quality and tail-enters SetSettingLodLevel(init=true)"),
    ("set_setting_to_all_rows", 0x34F7F33,
     bytes.fromhex("48 8b 8b 80 00 00 00 48 85 c9 74 5e 45 33 c0 8b d6 e8 d7 1f ea ff"),
     "SetSettingLodLevel calls EffectSetting.SetAllSettingLod"),
    ("set_all_setting_refresh", 0x339A0D0,
     bytes.fromhex("44 89 76 70 45 33 c0 33 d2 48 8b ce e8 ef 1c 00 00"),
     "SetAllSettingLod writes m_showSettingLodLevel and calls _RefreshLod(false)"),
    ("init_data_active_self", 0x339C2C1,
     bytes.fromhex("ff d0 48 8b 5f 18 88 47 58 88 47 59"),
     "InitData copies the GameObject active getter result into m_initActive/m_curActive"),
    ("refresh_predicate_and_set_active", 0x339BE31,
     bytes.fromhex("8b 43 70 c6 43 10 00 85 43 40 0f 84 8e 00 00 00 8b 83 c0 00 00 00 b9 00 00 00 00 85 43 48 0f 97 c0 88 43 6d 48 83 7b 78 00 74 14 84 c0 74 78 48 8b 43 78 0f b6 40 14 85 c0 0f 95 c0 88 43 6d 80 7b 6d 00 74 04 0f b6 4b 58 85 c9 40 0f 95 c7 40 84 f6 75 32 48 8b 73 18 48 85 f6 74 6d 48 8b 05 cb 23 fd 0b 48 85 c0 74 78 40 0f b6 d7 48 8b ce ff d0 40 88 7b 59"),
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
    code_registration = 0x18B9217D0
    modules = mapper.parse_codegen_modules(pe, code_registration)
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
        ("set_quality_normalize_fallback_and_store", 0x183F92958, 10,
         "effect_manager_normalize"),
        ("init_lod_get_quality", 0x1834F807A, 2, "effect_manager_get_quality"),
        ("init_lod_tail_set_setting", 0x1834F807A, 23, "effect_instance_set_setting"),
        ("set_setting_to_all_rows", 0x1834F9933, 17, "effect_setting_set_all_setting"),
        ("set_all_setting_refresh", 0x18339BAD0, 12, "effect_lod_refresh"),
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
        [0x1834FADCE, 0x1834FAEC9, 0x185090CD2, 0x185090D45],
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
    for index in (0x13E, 0x239):
        require(relative_target(guard[9], guard_body, index) ==
                method_by_key["effect_setting_set_all_target"][9],
                "hot SetAllTargetLayers caller edge drifted")
    cold_edges = ((0x52, "call"), (0x62, "return"),
                  (0xC5, "call"), (0xD4, "return"))
    for index, kind in cold_edges:
        target = relative_target(TARGET_LAYER_CALLER_WINDOWS[0][1], cold, index)
        expected = (method_by_key["effect_setting_set_all_target"][9]
                    if kind == "call" else 0x1834FABC6)
        require(target == expected,
                f"cold SetAllTargetLayers caller {kind} edge drifted")
    require(tower[9] <= 0x1834FABC6 < tower[9] + tower[11],
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
            "callVirtualAddresses": ["0x1834fadce", "0x1834faec9"],
            "codePlacement": "pinned hot method body",
        },
        {
            "owner": identity_by_key["battle_normal_refresh_tower_lod"],
            "bodyRange": [f"0x{tower[9]:x}", f"0x{tower[9] + tower[11]:x}"],
            "coldWindow": cold_windows[0],
            "coldReturnVirtualAddress": "0x1834fabc6",
            "callVirtualAddresses": ["0x185090cd2", "0x185090d45"],
            "codePlacement": "hash-pinned cold blocks with exact jumps into hot body",
        },
    ]

    require(sha256_file(ifix_state) == NATIVE_HASHES["ifix"],
            "installed IFix snapshot hash drifted")
    ifix = json.loads(ifix_state.read_text(encoding="utf-8"))
    source_build = ifix["source_build"]
    require(source_build["game_assembly"]["sha256"] == NATIVE_HASHES["gameAssembly"] and
            source_build["global_metadata"]["sha256"] == NATIVE_HASHES["metadata"],
            "installed IFix snapshot build join drifted")
    relevant = {(row[1], row[3]) for row in NATIVE_METHODS}
    observed = {(str(row.get("type")), str(row.get("method")))
                for row in ifix.get("targets", [])}
    require(not (relevant & observed),
            f"installed IFix snapshot replaces LOD route: {sorted(relevant & observed)}")

    require(sha256_file(LIFECYCLE_AUDIT) == NATIVE_HASHES["lifecycleAudit"],
            "pinned lifecycle native audit hash drifted")
    lifecycle = json.loads(LIFECYCLE_AUDIT.read_text(encoding="utf-8"))
    refresh = next(row for row in lifecycle["methods"]
                   if row.get("type") == "Beyond.Gameplay.EffectLodCfg" and
                   row.get("method") == "_RefreshLod")
    require(refresh["virtualAddress"] == "0x18339d7d0" and
            refresh["calls"] == ["Beyond.Gameplay.EffectLodCfg.InitData",
                                 "UnityEngine.GameObject.SetActive"],
            "pinned _RefreshLod GameObject.SetActive identity drifted")
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
        "lifecycleAuditSha256": NATIVE_HASHES["lifecycleAudit"],
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
