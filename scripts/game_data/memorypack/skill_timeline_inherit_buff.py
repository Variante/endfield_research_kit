"""Selected-build SkillData InheritBuffAction 0x00D2 reader.

The native wrapper fixes nine ordered reads and two generic child contexts.
The nested TargetSettings and List<string> retain their separately reviewed
finite framing; stored strings do not prove runtime skill inheritance.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data import buff_frontiers_native
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineInheritBuff"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_inherit_buff_native.json"
TAG = 0x00D2
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "buffOwner", "finishByAction", "finishWithNextSkillIfNotInherited",
    "inheritSkillIdList", "targetBuffId",
)
READ_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32", "target-profile",
    "bool-byte", "bool-byte", "string-list", "byte-payload",
)
NESTED_TYPES = (
    "Beyond.Gameplay.Core.TargetSettings", "System.Collections.Generic.List`1",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-inherit-buff-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != len(READ_KINDS)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(READ_KINDS)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [4, 7]
        or tuple(row.get("typeName") for row in contexts) != NESTED_TYPES
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    frontier = buff_frontiers_native.reviewed_contract("frontier8")
    list_route = next((row for row in frontier.get("actions", ()) if row.get("unionTag") == 9), None)
    list_context = next(
        (row for row in (list_route or {}).get("nestedContextUsage", ())
         if row.get("typeName") == NESTED_TYPES[1]), None
    )
    element_args = (list_context or {}).get("generic", {}).get("elementArguments")
    if (
        frontier.get("schema") != "endfield.buff-frontier8-native-contract.v1"
        or list_context is None
        or contexts[1].get("argumentRawHex") != list_context.get("argumentRawHex")
        or contexts[1].get("methodSpec") != list_context.get("methodSpec")
        or contexts[1].get("typeDefinition") != list_context.get("typeDefinition")
        or not isinstance(element_args, list)
        or len(element_args) != 1
        or bytes.fromhex(element_args[0])[10] != 0x0E
    ):
        raise ValueError(f"{LABEL}.contract:string-list-context")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate route, all reads, nested types, and dependent profiles."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
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
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    previous = -1
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"].upper():
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    ec = json.loads((CONTRACTS_DIR / "buff_ec_native.json").read_bytes())
    if ec.get("schemaVersion") != 1:
        raise ValueError(f"{LABEL}.native:target-profile-schema")
    image.check_windows(ec["codeWindows"], label=f"{LABEL}.buff_ec_native")
    frontier_rows, frontier_audit = buff_frontiers_native.load_rows("frontier8")
    if frontier_audit.get("status") != "validated" or 9 not in frontier_rows:
        raise ValueError(f"{LABEL}.native:string-list-profile")
    for context in contract["nestedContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell
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
        if argument.hex().upper() != context["argumentRawHex"] or argument[10] != context["typeKind"]:
            raise ValueError(f"{LABEL}.native:nested-argument")
        if context["memberIndex"] == 4 and (
            struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:target-type")
        if context["memberIndex"] == 7 and image.type_name(context["typeDefinition"]) != context["typeName"]:
            raise ValueError(f"{LABEL}.native:list-type")
    return {
        "status": "validated",
        "nativeInputs": expected,
        "methodIndices": methods,
        "sourceReadCount": len(READ_KINDS),
        "nestedContextCount": len(NESTED_TYPES),
    }


def decode_inherit_buff_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite nine-member action, preserving child stop behavior."""
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, "InheritBuffAction.bool-byte")
    for _ in range(3):
        reader.take(4, "InheritBuffAction.scalar32")
    reader.target_profile()
    reader.take(1, "InheritBuffAction.bool-byte")
    reader.take(1, "InheritBuffAction.bool-byte")
    count = reader.count(4, nullable=True)
    for _ in range(max(0, count)):
        reader.byte_payload()
    reader.byte_payload()
