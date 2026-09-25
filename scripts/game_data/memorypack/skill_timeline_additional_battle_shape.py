"""Selected-build SkillData CreateAdditionalBattleShape 0x0091 storage reader.

The generated wrapper has ten stored slots. ColliderShapeData and
TargetSettings reuse separately reviewed finite profiles. These bytes do not
prove that a battle shape is created or retained at runtime.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineAdditionalBattleShape"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_additional_battle_shape_native.json"
TAG = 0x0091
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_CreateAdditionalBattleShape_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.CreateAdditionalBattleShape+Data"
PARENT_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "duration", "followTargetPosition", "followTargetRotation",
    "releaseByAction", "shapeData", "targetSettings",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "float32-bits",
    "bool-byte", "bool-byte", "bool-byte", "collider-shape-profile",
    "target-profile",
)
CONTEXT_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "Beyond.Gameplay.ColliderShapeData",
    "Beyond.Gameplay.Core.TargetSettings",
)
SETTER_NAMES = (
    "set___duration__", "set___followTargetPosition__",
    "set___followTargetRotation__", "set___releaseByAction__",
    "set___shapeData__", "set___targetSettings__",
)
SETTER_TYPES = (
    "System.Single", "System.Boolean", "System.Boolean", "System.Boolean",
    "Beyond.Gameplay.ColliderShapeData", "Beyond.Gameplay.Core.TargetSettings",
)
CHILD_CONTRACTS = ("buff_7c_native.json", "buff_ec_native.json", "buff_b2_native.json")


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-additional-battle-shape-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("wrapper", {}).get("typeName") != WRAPPER_NAME
        or contract.get("wrapper", {}).get("parentTypeName") != PARENT_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or contract.get("readerContract") != "buff_91_native.json"
        or [row.get("path") for row in contract.get("dependencies", [])] != list(CHILD_CONTRACTS)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or tuple(row.get("typeName") for row in contexts) != CONTEXT_TYPES
        or not isinstance(setters, list)
        or tuple(row[1] for row in setters) != SETTER_NAMES
        or tuple(row[2] for row in setters) != SETTER_TYPES
        or not isinstance(setter_calls, list)
        or [row.get("memberIndex") for row in setter_calls] != list(range(4, 10))
        or [row.get("methodIndex") for row in setter_calls] != [row[0] for row in setters]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xfe\x0a"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("wrappedType") != TYPE_NAME
        or route.get("wrapperName") != WRAPPER_NAME
        or route.get("memberCount") != len(FIELD_NAMES)
        or switch.get("entryCount") != len(catalog["families"]["AbilityActionData"])
        or switch.get("base") != PARENT_NAME
    ):
        raise ValueError(f"{LABEL}.contract:catalog-route")
    reader_contract = json.loads((CONTRACTS_DIR / contract["readerContract"]).read_bytes())
    if (
        reader_contract.get("schemaVersion") != 1
        or reader_contract.get("methods") != contract["methods"]
        or reader_contract.get("nestedContexts") != contexts
        or reader_contract.get("anonymousReadOrder", {}).get("member10") != [
            "byte", "scalar32", "scalar32", "scalar32", "raw4",
            "byte", "byte", "byte", "collider-shape-profile", "target-profile",
        ]
    ):
        raise ValueError(f"{LABEL}.contract:reader-dependency")
    return contract


def _check_call(image: Any, call: dict[str, Any], *, kind: str) -> None:
    rva = call["sourceCallsiteRva"] if kind == "source" else call["callsiteRva"]
    expected = call["sourceCallHex"] if kind == "source" else call["callHex"]
    target = call["sourceTargetRva"] if kind == "source" else call["targetRva"]
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if (
        raw[0] != 0xE8
        or raw.hex().upper() != expected
        or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target
    ):
        raise ValueError(f"{LABEL}.native:{kind}-call={rva:#x}")


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate selected Skill dispatch, ten reads and child profiles."""
    contract = _contract()
    expected = contract["nativeInputs"]
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-inputs")
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    if int(catalog["switches"]["AbilityActionData"]["tableVa"], 16) != image.pe.image_base + contract["dispatcher"]["switchTableRva"]:
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    owner = image.check_wrapper_inheritance(contract["wrapper"], label=LABEL)
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    reader_contract = json.loads((CONTRACTS_DIR / contract["readerContract"]).read_bytes())
    image.check_windows(reader_contract["codeWindows"], label=f"{LABEL}.reader")
    start = reader_contract["codeWindows"][1]["startRva"]
    end = reader_contract["codeWindows"][1]["endRva"]
    previous = -1
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if not start <= rva < end or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        _check_call(image, read, kind="source")
    previous_setter = -1
    for call in contract["setterCallsites"]:
        rva = call["callsiteRva"]
        if not start <= rva < end or rva <= previous_setter:
            raise ValueError(f"{LABEL}.native:setter-source-order")
        previous_setter = rva
        # Setter calls interleave source reads; each must follow its own read
        # and precede the next member's source call.
        member = call["memberIndex"]
        after = contract["orderedSourceReads"][member]["sourceCallsiteRva"]
        before = contract["orderedSourceReads"][member + 1]["sourceCallsiteRva"] if member + 1 < len(FIELD_NAMES) else end
        if not after < rva < before:
            raise ValueError(f"{LABEL}.native:setter-precedes-source")
        _check_call(image, call, kind="setter")
        method = image.metadata.methods[call["methodIndex"]]
        if image.method_pointer_va(method) != image.pe.image_base + call["targetRva"]:
            raise ValueError(f"{LABEL}.native:setter-method={call['methodIndex']}")
    for context in contract["nestedContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell)
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        if list(spec) != context["methodSpec"]:
            raise ValueError(f"{LABEL}.native:method-spec-record")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity")
        raw = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        if (
            raw.hex().upper() != context["argumentRawHex"]
            or raw[10] != context["typeKind"]
            or struct.unpack_from("<Q", raw)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type")
    for dependency in contract["dependencies"]:
        reviewed = json.loads((CONTRACTS_DIR / dependency["path"]).read_bytes())
        if reviewed.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:dependency-schema={dependency['path']}")
        image.check_windows(reviewed.get("codeWindows", []), label=f"{LABEL}.{dependency['path']}")
        image.check_windows(reviewed.get("dataWindows", []), gate="data-window", label=f"{LABEL}.{dependency['path']}")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(FIELD_NAMES),
        "setterCount": len(SETTER_NAMES), "nestedContextCount": len(CONTEXT_TYPES),
    }


def decode_additional_battle_shape_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one selected 0x0091 stored action with finite child profiles."""
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(FIELD_NAMES))
    for name, kind in zip(FIELD_NAMES, READ_KINDS):
        if kind == "collider-shape-profile":
            reader.collider_shape_profile()
        elif kind == "target-profile":
            reader.target_profile()
        else:
            reader.take(1 if kind == "bool-byte" else 4, f"CreateAdditionalBattleShape.{name}.{kind}")
