"""Selected-build SkillData TargetPostProcessorAction 0x017B framing."""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineTargetPostprocessor"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_target_postprocessor_native.json"
TAG = 0x017B
FIELDS = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "centerPos", "direction", "postProcessorData", "source", "target",
    "targetGroupKey", "validatorData",
)
KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32", "nested-generic",
    "nested-generic", "list-generic", "nested-generic", "nested-generic",
    "string", "list-generic",
)
NESTED = {
    1: "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    4: "Beyond.Gameplay.Core.TargetSettings",
    5: "Beyond.Gameplay.Core.DirectionSettings",
    6: "Beyond.Gameplay.Core.Selector+PostProcessor+Data",
    7: "Beyond.Gameplay.Core.TargetSettings",
    8: "Beyond.Gameplay.Core.TargetSettings",
    10: "Beyond.Gameplay.Core.Selector+Validator+Data",
}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-target-postprocessor-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != len(FIELDS)
        or not isinstance(reads, list) or len(reads) != len(FIELDS)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELDS)))
        or tuple(row.get("fieldName") for row in reads) != FIELDS
        or tuple(row.get("readKind") for row in reads) != KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != list(NESTED)
        or [row.get("elementTypeName", row.get("typeName")) for row in contexts] != list(NESTED.values())
        or [row.get("path") for row in contract.get("dependencies", ())]
        != ["buff_b2_native.json", "buff_ec_native.json"]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xFE\x0B"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate selected dispatch, eleven calls, and generic arguments."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unityplayer.is_file() or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
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
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    for row in contract["nestedContexts"]:
        cell, usage = image.nested_usage_cell(row, label=LABEL)
        index = method_spec_usage_index(usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell)
        if index != row["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        if list(spec) != row["methodSpec"]:
            raise ValueError(f"{LABEL}.native:method-spec-record")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity")
        argument = instance.arguments[0]
        raw = bytes.fromhex(argument.raw_type_record_hex)
        if raw.hex().upper() != row["argumentRawHex"] or raw[10] != row["typeKind"]:
            raise ValueError(f"{LABEL}.native:generic-type")
        if raw[10] in (0x11, 0x12):
            definition = struct.unpack_from("<Q", raw)[0]
            if definition != row["typeDefinition"] or image.type_name(definition) != row["typeName"]:
                raise ValueError(f"{LABEL}.native:generic-direct-type")
        elif raw[10] == 0x15:
            pointer = struct.unpack_from("<Q", raw)[0]
            carrier_raw = image.pe.bytes_at_va(pointer, 32)
            base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
            base_raw = image.pe.bytes_at_va(base_pointer, 16)
            carrier = generic_type_carrier(
                raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
                type_count=len(image.metadata.types), source=LABEL,
            )
            if carrier != row["classCarrier"] or image.type_name(carrier["baseDefinitionIndex"]) != row["typeName"]:
                raise ValueError(f"{LABEL}.native:generic-list-carrier")
            child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
            child_record = child.as_dict()
            child_record["arguments"] = list(child_record["arguments"])
            if len(child.arguments) != 1 or child_record != row["classInstantiation"]:
                raise ValueError(f"{LABEL}.native:generic-list-instantiation")
            element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
            definition = struct.unpack_from("<Q", element)[0]
            if element.hex().upper() != row["elementRawHex"] or definition != row["elementTypeDefinition"] or image.type_name(definition) != row["elementTypeName"]:
                raise ValueError(f"{LABEL}.native:generic-list-element")
        else:
            raise ValueError(f"{LABEL}.native:generic-kind")
    for dependency in contract["dependencies"]:
        reviewed = json.loads((CONTRACTS_DIR / dependency["path"]).read_bytes())
        if reviewed.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:dependency-schema")
        image.check_windows(reviewed["codeWindows"], label=f"{LABEL}.{dependency['path']}")
    return {"status": "validated", "nativeInputs": expected, "methodIndices": methods,
            "sourceReadCount": len(FIELDS), "nestedContextCount": len(NESTED)}


def decode_target_postprocessor_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite eleven-member action with bounded selector lists."""
    del depth
    _contract()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(FIELDS))
    reader.take(1, "TargetPostProcessorAction.isEnable.byte")
    for field in FIELDS[1:4]:
        reader.take(4, f"TargetPostProcessorAction.{field}.raw4")
    reader.target_profile()
    reader.direction_profile()
    for _ in range(max(0, reader.count(1, nullable=True))):
        reader.selector_postprocessor_profile()
    reader.target_profile()
    reader.target_profile()
    reader.byte_payload()
    for _ in range(max(0, reader.count(1, nullable=True))):
        reader.selector_validator_profile()
