"""Selected-build SkillData OverrideBornPosition 0x0103 storage framing.

The five ordered reads retain the common action prefix and one Boolean slot.
The stored name alone does not establish a runtime position or rotation change.
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


LABEL = "skillTimelineOverrideBornPosition"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_override_born_position_native.json"
TAG = 0x0103
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_OverrideBornPosition_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.OverrideBornPosition+Data"
FIELD_NAMES = ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex", "overrideRot")
READ_KINDS = ("bool-byte", "enum32", "scalar32", "scalar32", "bool-byte")
PRIORITY_TYPE = "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority"


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-override-born-position-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("wrapper", {}).get("typeName") != WRAPPER_NAME
        or contract.get("wrapper", {}).get("parentTypeName")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1]
        or [row.get("typeName") for row in contexts] != [PRIORITY_TYPE]
        or not isinstance(setters, list)
        or [row[1:] for row in setters] != [["set___overrideRot__", "System.Boolean"]]
        or not isinstance(setter_calls, list)
        or [row.get("memberIndex") for row in setter_calls] != [4]
        or [row.get("methodIndex") for row in setter_calls] != [setters[0][0]]
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xfe\x05"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    contract = _contract()
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
        or switch.get("base")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
    ):
        raise ValueError(f"{LABEL}.contract:catalog-route")
    return catalog


def _check_call(image: Any, call: dict[str, Any], *, label: str) -> None:
    rva = call["sourceCallsiteRva"] if "sourceCallsiteRva" in call else call["callsiteRva"]
    expected = call["sourceCallHex"] if "sourceCallHex" in call else call["callHex"]
    target = call["sourceTargetRva"] if "sourceTargetRva" in call else call["targetRva"]
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected:
        raise ValueError(f"{LABEL}.native:{label}-call={rva:#x}")
    if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target:
        raise ValueError(f"{LABEL}.native:{label}-target={rva:#x}")


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected route, five source reads and own Boolean setter."""
    contract = _contract()
    catalog = _catalog()
    expected = contract["nativeInputs"]
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
    if (
        int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    owner = image.check_wrapper_inheritance(contract["wrapper"], label=LABEL)
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    start = contract["codeWindows"][1]["startRva"]
    end = contract["codeWindows"][1]["endRva"]
    previous = -1
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if not start <= rva < end or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        _check_call(image, read, label="source")
    setter_call = contract["setterCallsites"][0]
    if not previous < setter_call["callsiteRva"] < end:
        raise ValueError(f"{LABEL}.native:setter-order")
    _check_call(image, setter_call, label="setter")
    context = contract["genericContexts"][0]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
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
        or struct.unpack_from("<Q", raw)[0] != context["typeDefinition"]
        or raw[10] != context["typeKind"]
        or image.type_name(context["typeDefinition"]) != context["typeName"]
    ):
        raise ValueError(f"{LABEL}.native:generic-type")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
        "nestedContextCount": 1,
    }


def decode_override_born_position_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite five-member action, preserving its raw slots."""
    del depth
    _contract()
    _catalog()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, "OverrideBornPosition.isEnable.byte")
    for field in FIELD_NAMES[1:4]:
        reader.take(4, f"OverrideBornPosition.{field}.raw4")
    reader.take(1, "OverrideBornPosition.overrideRot.byte")
