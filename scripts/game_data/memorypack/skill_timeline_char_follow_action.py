"""Selected-build SkillData CharFollowAction 0x0034 storage framing.

The wrapper contributes no own serialized members to the common four-field
action prefix. Stored values do not establish runtime follow behavior.
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


LABEL = "skillTimelineCharFollowAction"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_char_follow_action_native.json"
TAG = 0x0034
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_CharFollowAction_CharFollowActionDataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.CharFollowAction+CharFollowActionData"
PARENT_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
PRIORITY_TYPE = "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority"
FIELD_NAMES = ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex")
READ_KINDS = ("bool-byte", "enum32", "scalar32", "scalar32")


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-char-follow-action-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    dispatcher = contract.get("dispatcher", {})
    wrapper = contract.get("wrapper", {})
    if (
        dispatcher.get("unionTag") != TAG
        or dispatcher.get("wrapperName") != WRAPPER_NAME
        or wrapper.get("typeDefinition") != dispatcher.get("wrapperTypeDefinition")
        or wrapper.get("typeName") != WRAPPER_NAME
        or wrapper.get("parentTypeName") != PARENT_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or contract.get("setterMethods") != []
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or len(contexts) != 1
        or contexts[0].get("memberIndex") != 1
        or contexts[0].get("typeName") != PRIORITY_TYPE
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7c\x24\x38\x04"
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
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the 0x0034 route, inherited source reads and Priority join."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
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
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
        or int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-build")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    owner = image.check_wrapper_inheritance(contract["wrapper"], label=LABEL)
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != []:
        raise ValueError(f"{LABEL}.native:unexpected-setters")
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    previous = -1
    window = contract["codeWindows"][1]
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if not window["startRva"] <= rva < window["endRva"] or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
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
    argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
    if (
        argument.hex().upper() != context["argumentRawHex"]
        or argument[10] != context["typeKind"]
        or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
        or image.type_name(context["typeDefinition"]) != context["typeName"]
    ):
        raise ValueError(f"{LABEL}.native:generic-type")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
        "genericContextCount": 1,
    }


def decode_char_follow_action(
    reader: Reader, depth: int, tag: int, width: int,
) -> None:
    """Consume one finite action while preserving scalar fields as raw data."""
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(FIELD_NAMES))
    reader.take(1, "CharFollowAction.isEnable.byte")
    for field in FIELD_NAMES[1:]:
        reader.take(4, f"CharFollowAction.{field}.raw4")
