#!/usr/bin/env python3
"""Build the fail-closed Endminf effect_nanguan owner/trigger contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
OUTPUT = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects"
    / "endminf_effect_nanguan_trigger_contract.json"
)
STAGE = REPO / "scratch/character_recovery/endminf_overview_effect_stage"
EFFECT_SETTING = STAGE / "MonoBehaviour/MonoBehaviour#299_pEE47385E2B7F6C79.json"
EFFECT_GO = STAGE / "GameObject/effect_nanguan_p3E1E69C789E16C79.json"
EFFECT_ANIMATOR = STAGE / "Animator/effect_nanguan_pA68268B3E2D06C79.json"
OVERVIEW_ROOT_ANIMATOR = (
    STAGE / "Animator/P_fxui_endminm003_overview_01_pB1AA2926B7D06C79.json"
)
CLIP_03 = STAGE / "AnimationClip/A_fx_endminf_ui_overview_03_p74482923CB70A4E8.json"
CLIP_04 = STAGE / "AnimationClip/A_fx_endminf_ui_overview_04_pDB8EF20719226683.json"
CONTROLLER = (
    REPO
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type"
    / "AnimatorController/AnimatorController#3596353_pE864B694E2337D78.json"
)
ASSET_MAP = (
    REPO
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps"
    / "endfield_streamingassets_assets.json"
)
ASSET_MAP_FILTER = (
    STAGE
    / "filters/external_ui_effects_001_98E51B76A48F5BEF8D07BDFD3E4DA7ED.json"
)
METADATA_CATALOG_TOOL = (
    REPO / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"
)
NATIVE_MAP_TOOL = REPO / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py"

SOURCE_HASHES = {
    EFFECT_SETTING: "f6fc9bb6515773524430750eda8e4b836ec582c70a3bd12c25994e86d98da7ea",
    EFFECT_GO: "07b3c0594bb31e0287414195b08563ba72fb26c52b45d4a18cd1c09417f74de7",
    EFFECT_ANIMATOR: "01d9c44f9de1f38c9fa75c4063e53ca0383b83ac385309710cbd8773ff30d829",
    OVERVIEW_ROOT_ANIMATOR: "a7061f60874b100ff2c095b21a55b2c4ce9c8af3d1117710c2ca0f6fd927cd5e",
    CONTROLLER: "a680e895100485bb57c1467f08ed3da926ce791dc4fa576a5f4437fc1e747e3d",
    CLIP_03: "81ee25bc86197850e8c9fbf45e23d99a77da958ac9c0258e0ebfede1ab421426",
    CLIP_04: "220ae359098e5a843afdced4680265e3eead2aba79b926988c5ba46ae6d42e6f",
    ASSET_MAP_FILTER: "98d12d6f6598436605a3f48d5db863542d41d6a06d5e482c079dd8e2e90c177a",
}
ASSET_MAP_SHA256 = "148415835f911fc94a634925c50c2d8b9a1cd4f5f141412f956cbb143805b6f3"
ASSET_MAP_EXPECTED_ROWS = {
    "A_fx_endminf_ui_overview_03": {
        "Name": "A_fx_endminf_ui_overview_03",
        "Container": (
            "assets/beyond/dynamicassets/gameplay/effects/prefabs/"
            "p_fxui_endminm003_overview_02.prefab"
        ),
        "Source": (
            r"D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS"
            r"\7064D8E2\98E51B76A48F5BEF8D07BDFD3E4DA7ED.chk"
        ),
        "PathID": 8378992340436559080,
        "Type": "AnimationClip",
        "Hash": "c558743aacd8a0f7",
        "Offset": 373845082,
    },
    "A_fx_endminf_ui_overview_04": {
        "Name": "A_fx_endminf_ui_overview_04",
        "Container": (
            "assets/beyond/dynamicassets/gameplay/effects/prefabs/"
            "p_fxui_endminm003_overview_01.prefab"
        ),
        "Source": (
            r"D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS"
            r"\7064D8E2\98E51B76A48F5BEF8D07BDFD3E4DA7ED.chk"
        ),
        "PathID": -2625895420410042749,
        "Type": "AnimationClip",
        "Hash": "cb429ac9f1afe11",
        "Offset": 772927267,
    },
    "effect_nanguan": {
        "Name": "effect_nanguan",
        "Container": (
            "assets/beyond/dynamicassets/gameplay/effects/prefabs/"
            "p_fxui_endminm003_overview_01.prefab"
        ),
        "Source": (
            r"D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS"
            r"\7064D8E2\98E51B76A48F5BEF8D07BDFD3E4DA7ED.chk"
        ),
        "PathID": -6448476594627384199,
        "Type": "Animator",
        "Hash": "6b9e501d73e9ca28",
        "Offset": 772927267,
    },
}
NATIVE_INPUT_HASHES = {
    "gameAssembly": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    "metadata": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
}
NATIVE_METHODS = (
    ("Beyond.Gameplay.EffectInstance._ReadCfgData", "0x183963e40", 0x3962440, 144,
     "81a63414ffa5d3968059951ba619d93a0a635ce8bc66afdaac7654a836b4b9fa"),
    ("Beyond.Gameplay.EffectInstance.Start", "0x183028ee0", 0x30274E0, 3024,
     "bd85708e13c4bb1206126168df46bf50c2c24c5c14d571db321d1c7c16c44564"),
    ("Beyond.Gameplay.EffectInstance.SetActive", "0x18302a920", 0x3028F20, 672,
     "ac853001b71f10be0c349c3da9959f21a142dc49e80bc8f486f1feac4637cec1"),
    ("Beyond.Gameplay.EffectInstance.SetEffectPlayState", "0x18743eba0", 0x743D1A0, 392,
     "367374b2c9ad06bf88b0d6a4f6edd999e9c9c8161a7eb54abf12f2f3ec32a489"),
    ("Beyond.Gameplay.EffectSetting.PlayEffect", "0x1834fc4d0", 0x34FAAD0, 272,
     "7c98c6cc65e25d96d4adda5293efd6ec9103fb8ad49fbb3c6482e5549738a724"),
    ("Beyond.Gameplay.EffectLodCfg.Play", "0x1834fc5e0", 0x34FABE0, 656,
     "b2fa3784d165047b376844a63ff0cd06bf6a37d68912f572596116d0ea162b1a"),
)
NATIVE_IDENTITIES = (
    ("Beyond.Gameplay.EffectInstance", "Gameplay.Beyond.dll", "0x02000d8e",
     "_ReadCfgData", 23176, "0x06005a89", (), ()),
    ("Beyond.Gameplay.EffectInstance", "Gameplay.Beyond.dll", "0x02000d8e",
     "Start", 23178, "0x06005a8b", (), ()),
    ("Beyond.Gameplay.EffectInstance", "Gameplay.Beyond.dll", "0x02000d8e",
     "SetActive", 23200, "0x06005aa1", ("active",), ("System.Boolean",)),
    ("Beyond.Gameplay.EffectInstance", "Gameplay.Beyond.dll", "0x02000d8e",
     "SetEffectPlayState", 23201, "0x06005aa2", ("play",), ("System.Boolean",)),
    ("Beyond.Gameplay.EffectSetting", "Gameplay.Beyond.dll", "0x02000db1",
     "PlayEffect", 23675, "0x06005c7c", (), ()),
    ("Beyond.Gameplay.EffectLodCfg", "Gameplay.Beyond.dll", "0x02000db9",
     "Play", 23709, "0x06005c9e", (), ()),
    ("UnityEngine.Behaviour", "UnityEngine.CoreModule.dll", "0x02000180",
     "set_enabled", 405973, "0x0600105c", ("value",), ("System.Boolean",)),
    ("UnityEngine.Animator", "UnityEngine.AnimationModule.dll", "0x0200002a",
     "Play", 475603, "0x06000212", ("stateNameHash",), ("System.Int32",)),
)
NATIVE_FIELD_IDENTITIES = (
    ("Beyond.Gameplay.EffectInstance", "m_delayTime", "0x04004deb"),
    ("Beyond.Gameplay.EffectInstance", "m_animator", "0x04004dfb"),
    ("Beyond.Gameplay.EffectInstance", "m_hasAnimator", "0x04004dfc"),
)
NATIVE_METHOD_VAS = {
    "Beyond.Gameplay.EffectInstance._ReadCfgData": 0x183963E40,
    "Beyond.Gameplay.EffectInstance.Start": 0x183028EE0,
    "Beyond.Gameplay.EffectInstance.SetActive": 0x18302A920,
    "Beyond.Gameplay.EffectInstance.SetEffectPlayState": 0x18743EBA0,
    "Beyond.Gameplay.EffectSetting.PlayEffect": 0x1834FC4D0,
    "Beyond.Gameplay.EffectLodCfg.Play": 0x1834FC5E0,
    "UnityEngine.Behaviour.set_enabled": 0x1834369A0,
    "UnityEngine.Animator.Play(System.Int32)": 0x1834FCD00,
}
NATIVE_CONTROL_FLOW = (
    {
        "name": "read_cfg_delay_copy",
        "caller": "Beyond.Gameplay.EffectInstance._ReadCfgData",
        "offset": 0x48,
        "bytes": bytes.fromhex(
            "48 8B 83 98 00 00 00 48 85 C0 74 35 80 78 18 00 75 0F "
            "8B 40 1C 89 83 C8 00 00 00 48 83 C4 20 5B C3"
        ),
        "semantic": "copies non-random EffectLogicCfg.delay into EffectInstance.m_delayTime",
    },
    {
        "name": "zero_delay_start_animator_enable",
        "caller": "Beyond.Gameplay.EffectInstance.Start",
        "offset": 0x412,
        "bytes": bytes.fromhex(
            "F3 0F 10 8E C8 00 00 00 0F 57 C0 0F 2F C8 0F 87 CF 00 00 00 "
            "88 9E CC 00 00 00 38 9E 40 01 00 00 0F 84 A0 00 00 00 "
            "48 8B 8E 38 01 00 00 48 85 C9 0F 84 F7 06 00 00 "
            "45 33 C0 B2 01 E8 6E D6 40 00"
        ),
        "callIndex": 59,
        "target": "UnityEngine.Behaviour.set_enabled",
        "branchIndex": 14,
        "branchTargetOffset": 0x4F5,
        "semantic": (
            "delay > 0 branches to delayed deactivation; zero delay falls through and, only "
            "when EffectInstance.m_hasAnimator is true and EffectInstance.m_animator is non-null, "
            "enables that runtime EffectInstance animator"
        ),
    },
    {
        "name": "set_active_to_play_effect",
        "caller": "Beyond.Gameplay.EffectInstance.SetActive",
        "offset": 0x178,
        "bytes": bytes.fromhex("48 85 C9 74 67 33 D2 E8 2C 1A 4D 00"),
        "callIndex": 7,
        "target": "Beyond.Gameplay.EffectSetting.PlayEffect",
        "semantic": "SetActive true path calls EffectSetting.PlayEffect",
    },
    {
        "name": "play_effect_to_lod_play",
        "caller": "Beyond.Gameplay.EffectSetting.PlayEffect",
        "offset": 0x85,
        "bytes": bytes.fromhex(
            "48 8B 5C 24 50 48 85 DB 74 68 33 D2 48 8B CB E8 77 00 00 00"
        ),
        "callIndex": 15,
        "target": "Beyond.Gameplay.EffectLodCfg.Play",
        "semantic": "PlayEffect enumerator row calls EffectLodCfg.Play",
    },
    {
        "name": "lod_play_to_animator_play",
        "caller": "Beyond.Gameplay.EffectLodCfg.Play",
        "offset": 0x1B9,
        "bytes": bytes.fromhex(
            "48 8B 8B A8 00 00 00 48 85 C9 74 BE 45 33 C0 33 D2 E8 51 05 00 00"
        ),
        "callIndex": 17,
        "target": "UnityEngine.Animator.Play(System.Int32)",
        "semantic": "EffectLodCfg.Play calls Animator.Play(stateNameHash=0)",
    },
)
def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing source evidence: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"source evidence is not an object: {path}")
    return value


def load_json_list(path: Path) -> list[dict[str, Any]]:
    require(path.is_file(), f"missing source evidence: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, list) and all(isinstance(row, dict) for row in value),
            f"source evidence is not an object list: {path}")
    return value


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def validate_exact_asset_map_rows(rows_by_name: dict[str, list[dict[str, Any]]]) -> None:
    for name, expected in ASSET_MAP_EXPECTED_ROWS.items():
        rows = rows_by_name.get(name, [])
        if name == "effect_nanguan":
            require(expected in rows,
                    "exact original AssetMap Animator owner row drifted: effect_nanguan")
        else:
            require(rows == [expected],
                    f"exact original AssetMap source clip row drifted: {name}")
    require(not rows_by_name.get("A_fx_endminf_ui_overview_03_04"),
            "fabricated composite unexpectedly appeared in original AssetMap")


def validate_asset_map() -> dict[str, Any]:
    require(ASSET_MAP.is_file(), f"missing original AssetMap: {ASSET_MAP}")
    names = tuple(ASSET_MAP_EXPECTED_ROWS) + ("A_fx_endminf_ui_overview_03_04",)
    needles = {name: f'"Name": "{name}"'.encode("utf-8") for name in names}
    rows_by_name: dict[str, list[dict[str, Any]]] = {name: [] for name in names}
    digest = hashlib.sha256()
    byte_count = 0
    record: list[bytes] | None = None
    record_matches: set[str] = set()
    with ASSET_MAP.open("rb") as stream:
        for line in stream:
            byte_count += len(line)
            digest.update(line)
            if line.startswith(b"    {"):
                record = [line]
                record_matches = set()
                continue
            if record is None:
                continue
            record.append(line)
            for name, needle in needles.items():
                if needle in line:
                    record_matches.add(name)
            if line.startswith(b"    }"):
                if record_matches:
                    raw = b"".join(record).strip().rstrip(b",")
                    row = json.loads(raw.decode("utf-8"))
                    require(isinstance(row, dict), "original AssetMap row is not an object")
                    for name in record_matches:
                        require(row.get("Name") == name,
                                f"original AssetMap row name marker drifted: {name}")
                        rows_by_name[name].append(row)
                record = None
                record_matches = set()
    require(digest.hexdigest() == ASSET_MAP_SHA256,
            "original AssetMap hash drifted")
    validate_exact_asset_map_rows(rows_by_name)
    return {
        "path": rel(ASSET_MAP),
        "sha256": ASSET_MAP_SHA256,
        "byteCount": byte_count,
        "exactNameRowCounts": {name: len(rows) for name, rows in rows_by_name.items()},
        "exactRows": [ASSET_MAP_EXPECTED_ROWS[name] for name in ASSET_MAP_EXPECTED_ROWS],
    }


def validate_metadata_identities(
    metadata: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Any]:
    spec = importlib.util.spec_from_file_location(
        "endminf_effect_metadata_catalog", METADATA_CATALOG_TOOL
    )
    require(spec is not None and spec.loader is not None,
            f"cannot load metadata catalog parser: {METADATA_CATALOG_TOOL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    md = module.Metadata(metadata)

    required_types = {row[0] for row in NATIVE_IDENTITIES}
    types: dict[str, Any] = {}
    for type_def in md.types:
        full_name = md.type_full_name(type_def)
        if full_name in required_types:
            require(full_name not in types, f"duplicate metadata type: {full_name}")
            types[full_name] = type_def
    require(set(types) == required_types, "required native metadata types are missing")

    identities: list[dict[str, Any]] = []
    for (type_name, image, type_token, method_name, method_index, token,
         parameter_names, parameter_types) in NATIVE_IDENTITIES:
        type_def = types[type_name]
        require(md.image_name_by_type_index.get(type_def.index) == image and
                f"0x{type_def.token:08x}" == type_token,
                f"native metadata type identity drifted: {type_name}")
        candidates = []
        for method in md.methods_for(type_def):
            row = module.method_row(md, method)
            if row["name"] == method_name:
                candidates.append(row)
        row = next((candidate for candidate in candidates
                    if candidate["index"] == method_index), None)
        require(row is not None and row["token"] == token and
                tuple(row["parameters"]) == parameter_names and
                tuple(detail["typeName"] for detail in row["parameterDetails"]) ==
                parameter_types and row["returnTypeName"] == "System.Void",
                f"native metadata method identity drifted: {type_name}.{method_name}")
        identities.append({
            "type": type_name,
            "image": image,
            "typeToken": type_token,
            "method": method_name,
            "methodIndex": method_index,
            "token": token,
            "parameters": [
                {"name": name, "type": parameter_type}
                for name, parameter_type in zip(parameter_names, parameter_types)
            ],
            "returnType": "System.Void",
        })

    fields: list[dict[str, Any]] = []
    for type_name, field_name, token in NATIVE_FIELD_IDENTITIES:
        candidates = [module.field_row(md, field) for field in md.fields_for(types[type_name])]
        row = next((candidate for candidate in candidates if candidate["name"] == field_name), None)
        require(row is not None and row["token"] == token,
                f"native metadata field identity drifted: {type_name}.{field_name}")
        fields.append({"type": type_name, "field": field_name, "token": token})
    return identities, fields, md


def validate_method_pointer_mapping(gameassembly: Path, md: Any) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "endminf_effect_native_mapper", NATIVE_MAP_TOOL
    )
    require(spec is not None and spec.loader is not None,
            f"cannot load native mapper: {NATIVE_MAP_TOOL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    pe = module.PeImage(gameassembly)
    code_registration = 0x18B9217D0
    summary = module.code_registration_summary(pe, code_registration)
    modules = module.parse_codegen_modules(pe, code_registration)
    ranges = module.image_method_ranges(md)
    require(summary["codeGenModulesCount"] == len(md.images) == len(modules) and
            set(modules) == set(ranges),
            "pinned CodeRegistration module table does not match current metadata images")
    pointers_by_image, _ = module.build_pointer_indexes(pe, md, modules, ranges)

    rows: list[dict[str, Any]] = []
    for (type_name, image, type_token, method_name, method_index, token,
         parameter_names, parameter_types) in NATIVE_IDENTITIES:
        label = f"{type_name}.{method_name}"
        if type_name == "UnityEngine.Animator":
            label += "(System.Int32)"
        image_range = ranges[image]
        slot = method_index - image_range["methodStart"]
        pointers = pointers_by_image[image]
        require(0 <= slot < len(pointers),
                f"native method slot is outside its image: {label}")
        pointer = pointers[slot]
        require(pointer == NATIVE_METHOD_VAS[label],
                f"metadata method pointer mapping drifted: {label}")
        rows.append({
            "method": label,
            "methodIndex": method_index,
            "token": token,
            "image": image,
            "moduleMethodSlot": slot,
            "methodPointerVa": f"0x{pointer:x}",
        })
    return {
        "codeRegistrationVa": f"0x{code_registration:x}",
        "codeGenModuleCount": len(modules),
        "status": "validated_from_current_metadata_and_codegen_module_tables",
        "methods": rows,
    }


def _relative_call_target(caller_va: int, relative_offset: int,
                          code: bytes, call_index: int) -> int:
    require(code[call_index] == 0xE8, "expected a relative CALL opcode")
    displacement = int.from_bytes(
        code[call_index + 1:call_index + 5], "little", signed=True
    )
    return caller_va + relative_offset + call_index + 5 + displacement


def _relative_call_offsets(caller_va: int, code: bytes, target_va: int) -> list[int]:
    offsets = []
    for index in range(0, len(code) - 4):
        if code[index] != 0xE8:
            continue
        displacement = int.from_bytes(code[index + 1:index + 5], "little", signed=True)
        if caller_va + index + 5 + displacement == target_va:
            offsets.append(index)
    return offsets


def validate_native(gameassembly: Path, metadata: Path) -> dict[str, Any]:
    require(gameassembly.is_file(), f"missing GameAssembly.dll: {gameassembly}")
    require(metadata.is_file(), f"missing global-metadata.dat: {metadata}")
    require(sha256(gameassembly) == NATIVE_INPUT_HASHES["gameAssembly"],
            "GameAssembly.dll does not match the pinned Endfield build")
    require(sha256(metadata) == NATIVE_INPUT_HASHES["metadata"],
            "global-metadata.dat does not match the pinned Endfield build")

    identities, fields, md = validate_metadata_identities(metadata)
    pointer_mapping = validate_method_pointer_mapping(gameassembly, md)
    rows: list[dict[str, Any]] = []
    method_file_offsets: dict[str, int] = {}
    method_bodies: dict[str, bytes] = {}
    with gameassembly.open("rb") as stream:
        for name, va, offset, size, expected_hash in NATIVE_METHODS:
            stream.seek(offset)
            body = stream.read(size)
            require(len(body) == size, f"native method body is truncated: {name}")
            require(hashlib.sha256(body).hexdigest() == expected_hash,
                    f"native method body hash drifted: {name}")
            rows.append({
                "name": name,
                "virtualAddress": va,
                "fileOffset": f"0x{offset:x}",
                "byteCount": size,
                "sha256": expected_hash,
            })
            method_file_offsets[name] = offset
            method_bodies[name] = body

        control_flow: list[dict[str, Any]] = []
        for expected in NATIVE_CONTROL_FLOW:
            caller = str(expected["caller"])
            offset = int(expected["offset"])
            code = bytes(expected["bytes"])
            require(caller in method_file_offsets and caller in NATIVE_METHOD_VAS,
                    f"native control-flow caller is not mapped: {caller}")
            stream.seek(method_file_offsets[caller] + offset)
            require(stream.read(len(code)) == code,
                    f"native control-flow bytes drifted: {expected['name']}")
            row = {
                "name": expected["name"],
                "caller": caller,
                "offset": f"0x{offset:x}",
                "bytes": code.hex(" "),
                "semantic": expected["semantic"],
            }
            if "callIndex" in expected:
                target = str(expected["target"])
                target_va = _relative_call_target(
                    NATIVE_METHOD_VAS[caller], offset, code, int(expected["callIndex"])
                )
                require(target_va == NATIVE_METHOD_VAS[target],
                        f"native call target drifted: {expected['name']}")
                row.update({
                    "callIndex": int(expected["callIndex"]),
                    "target": target,
                    "targetVirtualAddress": f"0x{target_va:x}",
                })
            if "branchIndex" in expected:
                branch_index = int(expected["branchIndex"])
                require(code[branch_index:branch_index + 2] == b"\x0f\x87",
                        "EffectInstance.Start delay branch opcode drifted")
                displacement = int.from_bytes(
                    code[branch_index + 2:branch_index + 6], "little", signed=True
                )
                target_offset = offset + branch_index + 6 + displacement
                require(target_offset == int(expected["branchTargetOffset"]),
                        "EffectInstance.Start delayed branch target drifted")
                row.update({
                    "branchOpcode": "JA",
                    "branchMeaning": "delay > 0",
                    "branchTargetOffset": f"0x{target_offset:x}",
                    "fallthroughMeaning": (
                        "delay == 0 falls through to a conditional enable of the runtime "
                        "EffectInstance.m_animator at +0x138 only when m_hasAnimator at +0x140 "
                        "is true and that animator is non-null"
                    ),
                })
            control_flow.append(row)
    require(_relative_call_offsets(
                NATIVE_METHOD_VAS["Beyond.Gameplay.EffectInstance.Start"],
                method_bodies["Beyond.Gameplay.EffectInstance.Start"],
                NATIVE_METHOD_VAS["Beyond.Gameplay.EffectSetting.PlayEffect"],
            ) == [],
            "EffectInstance.Start unexpectedly gained a direct PlayEffect call")
    return {
        "methodIdentities": identities,
        "fieldIdentities": fields,
        "methodPointerMapping": pointer_mapping,
        "methodBodies": rows,
        "controlFlow": control_flow,
        "negativeEdges": [{
            "caller": "Beyond.Gameplay.EffectInstance.Start",
            "target": "Beyond.Gameplay.EffectSetting.PlayEffect",
            "directRelativeCallOffsets": [],
            "meaning": (
                "No direct Start -> PlayEffect edge exists in the pinned method body; the "
                "zero-delay Start proof is only the separate conditional enable of "
                "EffectInstance.m_animator. It does not identify the LOD-owned child Animator."
            ),
        }],
    }


def _pointer(value: Any) -> int:
    require(isinstance(value, dict), "expected a serialized PPtr object")
    return int(value.get("m_PathID"))


def _filename_path_id(path: Path) -> int:
    encoded = path.stem.rsplit("_p", 1)[-1]
    unsigned = int(encoded, 16)
    return unsigned if unsigned < (1 << 63) else unsigned - (1 << 64)


def build(gameassembly: Path, metadata: Path) -> dict[str, Any]:
    source_payloads: dict[Path, dict[str, Any]] = {}
    for path, expected_hash in SOURCE_HASHES.items():
        require(sha256(path) == expected_hash, f"source evidence hash drifted: {rel(path)}")
        if path != ASSET_MAP_FILTER:
            source_payloads[path] = load_json(path)

    setting = source_payloads[EFFECT_SETTING]
    effect_go = source_payloads[EFFECT_GO]
    animator = source_payloads[EFFECT_ANIMATOR]
    overview_root_animator = source_payloads[OVERVIEW_ROOT_ANIMATOR]
    controller = source_payloads[CONTROLLER]
    clip03 = source_payloads[CLIP_03]
    clip04 = source_payloads[CLIP_04]
    filtered_asset_rows = load_json_list(ASSET_MAP_FILTER)

    logic = setting.get("effectLogicCfg") or {}
    require(setting.get("m_Enabled") == 1, "EffectSetting is not enabled")
    require(logic.get("delay") == 0.0 and logic.get("randomDelay") == 0,
            "EffectSetting no longer has authored zero/non-random delay")
    require(logic.get("isLoop") == 0 and logic.get("duration") == 9.0,
            "EffectSetting authored loop/duration fields drifted")

    lod_rows = setting.get("lodSetting") or []
    require(len(lod_rows) > 30, "EffectSetting lodSetting[30] is missing")
    lod = lod_rows[30]
    require(_pointer(lod.get("gameobject")) == 4476131385385512057,
            "EffectSetting lodSetting[30] GameObject owner drifted")
    require(_pointer(lod.get("animator")) == -6448476594627384199,
            "EffectSetting lodSetting[30] Animator owner drifted")
    require(lod.get("particle", {}).get("m_PathID") == 0 and
            lod.get("renderer", {}).get("m_PathID") == 0,
            "EffectSetting lodSetting[30] component kind drifted")
    require(lod.get("_distanceLodInfos") == [{"speedPercent": 1.0, "isActive": 1}],
            "EffectSetting lodSetting[30] activation row drifted")

    require(effect_go.get("m_Name") == "effect_nanguan", "effect GameObject name drifted")
    require(effect_go.get("m_Animation") is None, "source effect_nanguan gained Animation")
    require(_pointer((effect_go.get("m_Animator") or {}).get("m_Controller")) ==
            -1701034008672764552, "effect_nanguan controller pointer drifted")
    require(animator.get("m_Enabled") == 1 and
            _pointer(animator.get("m_GameObject")) == 4476131385385512057 and
            _pointer(animator.get("m_Controller")) == -1701034008672764552,
            "effect_nanguan Animator identity drifted")
    require(_filename_path_id(EFFECT_ANIMATOR) ==
            ASSET_MAP_EXPECTED_ROWS["effect_nanguan"]["PathID"],
            "effect_nanguan staged Animator PathID marker drifted")
    require(overview_root_animator.get("Name") == "P_fxui_endminm003_overview_01" and
            overview_root_animator.get("m_Enabled") == 1 and
            _pointer(overview_root_animator.get("m_GameObject")) == 644358100928130169 and
            _pointer(overview_root_animator.get("m_Controller")) == 0,
            "overview root Animator null-controller identity drifted")

    require(controller.get("m_Name") == "A_fx_endminf_ui_overview_04",
            "effect_nanguan AnimatorController name drifted")
    machines = (controller.get("m_Controller") or {}).get("m_StateMachineArray") or []
    require(len(machines) == 1, "effect_nanguan state-machine census drifted")
    machine = machines[0]["data"]
    require(machine.get("m_DefaultState") == 0, "effect_nanguan default state drifted")
    states = machine.get("m_StateConstantArray") or []
    require(len(states) == 1 and states[0]["data"].get("m_Loop") is False,
            "effect_nanguan default state loop/census drifted")
    nodes = states[0]["data"]["m_BlendTreeConstantArray"][0]["data"]["m_NodeArray"]
    require(len(nodes) == 1 and nodes[0]["data"].get("m_ClipID") == 0,
            "effect_nanguan default state clip index drifted")
    selectors = machine.get("m_SelectorStateConstantArray") or []
    entry = selectors[0]["data"]
    transitions = entry.get("m_TransitionConstantArray") or []
    require(entry.get("m_IsEntry") is True and len(transitions) == 1 and
            transitions[0]["data"].get("m_Destination") == 0 and
            transitions[0]["data"].get("m_ConditionConstantArray") == [],
            "effect_nanguan unconditional entry transition drifted")
    clips = controller.get("m_AnimationClips") or []
    require(len(clips) == 1 and _pointer(clips[0]) == -2625895420410042749,
            "effect_nanguan controller clip pointer drifted")

    muscle = clip04.get("m_MuscleClip") or {}
    bindings = (clip04.get("m_ClipBindingConstant") or {}).get("genericBindings") or []
    require(clip04.get("m_Name") == "A_fx_endminf_ui_overview_04" and
            clip04.get("m_SampleRate") == 60.0 and
            muscle.get("m_StartTime") == 0.0 and
            muscle.get("m_StopTime") == 4.366667 and
            muscle.get("m_LoopTime") is False and len(bindings) == 8,
            "exact source clip 04 identity/timing/binding census drifted")

    require(clip03.get("m_Name") == "A_fx_endminf_ui_overview_03",
            "source clip 03 identity drifted")

    expected_asset_rows = ASSET_MAP_EXPECTED_ROWS
    rows_by_name: dict[str, list[dict[str, Any]]] = {}
    for row in filtered_asset_rows:
        rows_by_name.setdefault(str(row.get("Name") or ""), []).append(row)
    for name, expected in expected_asset_rows.items():
        require(rows_by_name.get(name) == [expected],
                f"exact filtered original AssetMap row drifted: {name}")
    require("A_fx_endminf_ui_overview_03_04" not in rows_by_name,
            "fabricated composite unexpectedly appeared in exact AssetMap filter")
    for path, clip, expected in (
        (CLIP_03, clip03, expected_asset_rows["A_fx_endminf_ui_overview_03"]),
        (CLIP_04, clip04, expected_asset_rows["A_fx_endminf_ui_overview_04"]),
    ):
        require(clip.get("m_Name") == expected["Name"] and
                _filename_path_id(path) == expected["PathID"],
                f"stage clip identity/PathID markers drifted: {expected['Name']}")

    asset_map_evidence = validate_asset_map()

    native = validate_native(gameassembly, metadata)
    artifacts = [
        {"path": rel(path), "sha256": expected_hash}
        for path, expected_hash in SOURCE_HASHES.items()
    ]
    return {
        "schema": "endfield.endminf-effect-nanguan-trigger.v3",
        "scope": (
            "separate source-closed EffectInstance delay behavior, LOD-owned child Animator "
            "definition, native play code path, and non-retail lab transport; no cross-owner "
            "timing join"
        ),
        "evidence": {
            "serializedArtifacts": artifacts,
            "originalAssetMap": asset_map_evidence,
            "exactAssetMapFilter": {
                "path": rel(ASSET_MAP_FILTER),
                "sha256": SOURCE_HASHES[ASSET_MAP_FILTER],
                "rows": [
                    expected_asset_rows["A_fx_endminf_ui_overview_03"],
                    expected_asset_rows["A_fx_endminf_ui_overview_04"],
                ],
            },
            "nativeBuildGate": {
                "status": "validated",
                "gameAssemblySha256": NATIVE_INPUT_HASHES["gameAssembly"],
                "globalMetadataSha256": NATIVE_INPUT_HASHES["metadata"],
            },
            "native": native,
            "effectSetting": {
                "enabled": True,
                "isLoop": False,
                "durationSeconds": 9.0,
                "randomDelay": False,
                "delaySeconds": 0.0,
                "lodIndex": 30,
                "gameObjectPathId": 4476131385385512057,
                "animatorPathId": -6448476594627384199,
                "settingLodLevel": int(lod["settingLodLevel"]),
                "platformLayer": int(lod["platformLayer"]),
                "targetLayer": int(lod["targetLayer"]),
                "speedPercent": 1.0,
                "serializedDistanceLodActiveFlag": True,
                "runtimeGameObjectActivationProven": False,
            },
            "lodOwnedChildAnimator": {
                "gameObject": "effect_nanguan",
                "assetMapOwnerRow": expected_asset_rows["effect_nanguan"],
                "controllerPathId": -1701034008672764552,
                "controllerName": "A_fx_endminf_ui_overview_04",
                "defaultState": 0,
                "unconditionalEntryDestination": 0,
                "clipPathId": -2625895420410042749,
                "clipName": "A_fx_endminf_ui_overview_04",
                "clipStartSeconds": 0.0,
                "clipStopSeconds": 4.366667,
                "sampleRate": 60.0,
                "loop": False,
                "serializedGenericBindingCount": 8,
                "relationshipToEffectInstanceRuntimeAnimatorProven": False,
                "clipStartRelativeToEffectInstanceStartProven": False,
            },
            "overviewRootAnimator": {
                "gameObject": "P_fxui_endminm003_overview_01",
                "gameObjectPathId": 644358100928130169,
                "enabled": True,
                "controllerPathId": 0,
                "controllerIsNull": True,
            },
            "nativeDelayBranch": {
                "effectInstanceDelayFieldOffset": "0xc8",
                "comparison": "EffectInstance.Start enters delayed deactivation only when delay > 0",
                "zeroDelayResult": (
                    "fallthrough to a conditional Behaviour.set_enabled(true) on the runtime "
                    "EffectInstance.m_animator at +0x138 when m_hasAnimator at +0x140 is true "
                    "and the animator is non-null"
                ),
                "controlFlowEvidence": "zero_delay_start_animator_enable",
                "childAnimatorIdentityProven": False,
            },
        },
        "rejectedComposite": {
            "name": "A_fx_endminf_ui_overview_03_04",
            "originalAssetMapExactNameRowCount": 0,
            "reason": (
                "The serialized controller points only to source clip 04; clip 03 belongs to a "
                "different source effect prefab, so grafting its visibility curves is not source-closed."
            ),
            "clip03Container": expected_asset_rows["A_fx_endminf_ui_overview_03"]["Container"],
            "clip04Container": expected_asset_rows["A_fx_endminf_ui_overview_04"]["Container"],
        },
        "conclusions": {
            "effectInstanceDelayAndOwnAnimatorEnable": {
                "sourceClosed": True,
                "relativeAnchor": "EffectInstance.Start",
                "provenChain": [
                    "EffectInstance._ReadCfgData copies authored delay=0 to m_delayTime",
                    "EffectInstance.Start takes the zero-delay fallthrough",
                    (
                        "when m_hasAnimator is true and m_animator is non-null, "
                        "Behaviour.set_enabled(true) is called on that EffectInstance animator"
                    ),
                ],
                "nonclaim": (
                    "This code path does not identify EffectInstance.m_animator as the separately "
                    "serialized LOD-owned effect_nanguan child Animator and therefore does not "
                    "establish any clip start relative to EffectInstance.Start."
                ),
            },
            "lodOwnedChildAnimatorDefinitionAndPlayCodePath": {
                "definitionSourceClosed": True,
                "nativeCodePathSourceClosed": True,
                "runtimeInvocationForThisLodRowSourceClosed": False,
                "clipStartRelativeToEffectInstanceStartSourceClosed": False,
                "serializedOwnerChain": [
                    "EffectSetting.lodSetting[30]",
                    "effect_nanguan Animator",
                    "A_fx_endminf_ui_overview_04 AnimatorController",
                    "unconditional default state 0",
                    "A_fx_endminf_ui_overview_04",
                ],
                "nativeCodePath": [
                    "EffectSetting.PlayEffect",
                    "EffectLodCfg.Play",
                    "Animator.Play(stateNameHash=0)",
                ],
                "nonclaim": (
                    "The serialized child ownership and generic native play chain are exact, but "
                    "no exact call binds that chain to LOD row 30 at EffectInstance.Start."
                ),
            },
            "effectInstanceAnimatorToChildAnimatorRelationship": {
                "sourceClosed": False,
                "status": "unresolved",
                "nonclaim": (
                    "The EffectInstance.m_animator pointer used by Start is not proven to be the "
                    "LOD-owned effect_nanguan child Animator. The exact overview-root Animator "
                    "has a null controller, while the child Animator is owned separately by "
                    "lodSetting[30]."
                ),
            },
            "effectSettingLodGameObjectActivation": {
                "sourceClosed": False,
                "status": "unresolved",
                "knownRuntimePath": [
                    "EffectInstance.SetActive(true)",
                    "EffectSetting.PlayEffect",
                    "EffectLodCfg.Play",
                    "Animator.Play(stateNameHash=0)",
                ],
                "nonclaim": (
                    "The serialized LOD row identifies effect_nanguan and carries isActive=1, and "
                    "the native PlayEffect chain is exact, but no exact invocation of "
                    "SetGameObjectActive(true) for this owner transition has been established. "
                    "GameObject/LOD activation is not claimed."
                ),
            },
            "overviewStateToEffectInstanceStart": {
                "sourceClosed": False,
                "status": "unresolved",
                "nonclaim": (
                    "No exact source link yet establishes when the outer Endminf overview state "
                    "creates or starts this EffectInstance; no absolute character-timeline offset "
                    "or retail-canonical overview timing is claimed."
                ),
            },
            "labPlayback": {
                "sourceOwner": "Animator",
                "labTransport": "Legacy Animation",
                "retailOwnerExact": False,
                "retailTimingExact": False,
                "labStartPolicy": "start exact clip 04 when the lab effect root is instantiated",
                "rule": (
                    "Bind the exact exported A_fx_endminf_ui_overview_04 clip and start it when the "
                    "lab instantiates its recovered effect root. This is a transport mapping, not "
                    "a retail EffectInstance or child-Animator timing claim. Do not graft clip 03 "
                    "or add a fitted delay."
                ),
            },
        },
    }


def encode(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = encode(build(args.gameassembly, args.metadata))
    if args.check:
        require(OUTPUT.is_file(), f"published contract is missing: {OUTPUT}")
        require(OUTPUT.read_bytes() == data, "published contract drifted; rebuild it")
        print(f"build_endminf_effect_nanguan_trigger_contract: OK {OUTPUT}")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(data)
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
