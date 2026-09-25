"""Selected-build SkillData InheritCCSAction 0x00D3 storage framing.

The wrapper reads eight ordered members. The key and owner are stored inputs;
the native source proof does not establish live CCS ownership or blend effects.
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


LABEL = "skillTimelineInheritCCS"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_inherit_ccs_native.json"
TAG = 0x00D3
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_InheritCCSAction_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.InheritCCSAction+Data"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "blendOutTime", "ccsKey", "ccsOwner", "overrideBlendOut",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "float32-bits",
    "byte-payload", "target-profile", "bool-byte",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-inherit-ccs-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or len(contexts) != 1
        or contexts[0].get("memberIndex") != 6
        or contexts[0].get("typeName") != "Beyond.Gameplay.Core.TargetSettings"
        or [row[1:] for row in contract.get("setterMethods", ())] != [
            ["set___blendOutTime__", "System.Single"],
            ["set___ccsKey__", "System.String"],
            ["set___ccsOwner__", "Beyond.Gameplay.Core.TargetSettings"],
            ["set___overrideBlendOut__", "System.Boolean"],
        ]
        or contract.get("dependencies") != [
            {"path": "buff_ec_native.json", "role": "reviewed finite TargetSettings profile"}
        ]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7C\x24\x38\x08"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    catalog = json.loads((CONTRACTS_DIR / "levelscript_union_tags.json").read_bytes())
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
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected dispatch, source calls and nested target type."""
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
    catalog = json.loads((CONTRACTS_DIR / "levelscript_union_tags.json").read_bytes())
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
        or int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-build")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    previous = -1
    first_window = contract["codeWindows"][0]
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if not first_window["startRva"] <= rva < first_window["endRva"] or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    context = contract["nestedContexts"][0]
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
        raise ValueError(f"{LABEL}.native:nested-target")
    target = json.loads((CONTRACTS_DIR / "buff_ec_native.json").read_bytes())
    if target.get("schemaVersion") != 1 or "member13" not in target.get("anonymousReadOrder", {}):
        raise ValueError(f"{LABEL}.native:target-profile-schema")
    image.check_windows(target["codeWindows"], label=f"{LABEL}.buff_ec_native")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
        "nestedContextCount": len(contract["nestedContexts"]),
    }


def decode_inherit_ccs_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one selected action and retain child-profile refusal states."""
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, "InheritCCSAction.isEnable.byte")
    for field in ("priorityLevel", "priorityOffset", "serverActionIndex", "blendOutTime"):
        reader.take(4, f"InheritCCSAction.{field}.raw4")
    reader.byte_payload()
    reader.target_profile()
    reader.take(1, "InheritCCSAction.overrideBlendOut.byte")
