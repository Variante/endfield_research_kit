"""Selected-build SkillData UltimateTimeAction 0x0194 framing.

The list uses the reviewed nullable List<TargetSettings> profile. Stored
target, tag and float bits remain structural evidence only.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import (
    generic_type_carrier,
    method_spec_record,
    method_spec_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineUltimateTime"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_ultimate_time_native.json"
TAG = 0x0194
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32",
    "target-list", "gameplay-tag32", "float32-bits",
)
@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-ultimate-time-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    contexts = contract.get("genericContexts")
    dependencies = contract.get("dependencies")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != len(READ_KINDS)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(READ_KINDS)))
        or not isinstance(setters, list)
        or len(setters) != 3
        or not isinstance(setter_calls, list)
        or [row.get("memberIndex") for row in setter_calls] != [4, 5, 6]
        or [row.get("methodIndex") for row in setter_calls] != [row[0] for row in setters]
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 4, 5]
        or [row.get("typeName") for row in contexts]
        != [
            "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
            "System.Collections.Generic.List`1",
            "Beyond.Gameplay.Core.GameplayTag",
        ]
        or not isinstance(dependencies, list)
        or [row.get("path") for row in dependencies]
        != ["buff_ea_native.json", "buff_ec_native.json", "buff_fe_native.json"]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xFE" + bytes([len(READ_KINDS)])
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    fields = ["isEnable", "priorityLevel", "priorityOffset", "serverActionIndex"]
    for setter in setters:
        if not setter[1].startswith("set___") or not setter[1].endswith("__"):
            raise ValueError(f"{LABEL}.contract:setter-name")
        fields.append(setter[1].removeprefix("set___").removesuffix("__"))
    if (
        [row.get("fieldName") for row in reads] != fields
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or contexts[1].get("typeKind") != 0x15
        or contexts[1].get("generic", {}).get("elementArguments")
        != ["28280000000000000000120000000000"]
    ):
        raise ValueError(f"{LABEL}.contract:read-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected action, list type, source order and child helpers."""
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
    reads = contract["orderedSourceReads"]
    previous = -1
    for read in reads:
        rva = read["sourceCallsiteRva"]
        if rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if target != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    for setter in contract["setterCallsites"]:
        member = setter["memberIndex"]
        rva = setter["callsiteRva"]
        if not reads[member]["sourceCallsiteRva"] < rva < (
            reads[member + 1]["sourceCallsiteRva"]
            if member + 1 < len(reads) else contract["codeWindows"][1]["endRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter-order={member}")
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != setter["callHex"]:
            raise ValueError(f"{LABEL}.native:setter-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        method = image.metadata.methods[setter["methodIndex"]]
        if (
            target != setter["targetRva"]
            or image.method_pointer_va(method) != image.pe.image_base + target
        ):
            raise ValueError(f"{LABEL}.native:setter-target={member}")
    for context in contract["genericContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index={context['memberIndex']}")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        if list(spec) != context["methodSpec"]:
            raise ValueError(f"{LABEL}.native:method-spec-record={index}")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity={index}")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        if argument.hex().upper() != context["argumentRawHex"]:
            raise ValueError(f"{LABEL}.native:generic-argument={index}")
        if context["typeKind"] == 0x15:
            carrier_pointer = struct.unpack_from("<Q", argument)[0]
            carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
            base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
            base_raw = image.pe.bytes_at_va(base_pointer, 16)
            carrier = generic_type_carrier(
                argument, carrier_raw, base_raw,
                type_pointer=instance.arguments[0].type_pointer_va,
                type_count=len(image.metadata.types), source=LABEL,
            )
            generic = context["generic"]
            nested = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
            if (
                carrier_raw.hex().upper() != generic["carrierRawHex"]
                or base_raw.hex().upper() != generic["baseRawHex"]
                or nested.index != generic["elementInstantiationIndex"]
                or [a.raw_type_record_hex for a in nested.arguments] != generic["elementArguments"]
                or carrier["baseDefinitionIndex"] != context["typeDefinition"]
            ):
                raise ValueError(f"{LABEL}.native:list-carrier")
        elif struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]:
            raise ValueError(f"{LABEL}.native:generic-type={index}")
        if image.type_name(context["typeDefinition"]) != context["typeName"]:
            raise ValueError(f"{LABEL}.native:generic-name={index}")
    for dependency in contract["dependencies"]:
        reviewed = json.loads((CONTRACTS_DIR / dependency["path"]).read_bytes())
        if reviewed.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:dependency-schema={dependency['path']}")
        image.check_windows(reviewed["codeWindows"], label=f"{LABEL}.{dependency['path']}")
    existing_list = json.loads((CONTRACTS_DIR / "buff_ea_native.json").read_bytes())
    previous_list = next(row for row in existing_list["nestedContexts"] if row["typeName"] == "System.Collections.Generic.List`1")
    selected_list = contract["genericContexts"][1]
    if (
        selected_list["methodSpecIndex"] != previous_list["methodSpecIndex"]
        or selected_list["argumentRawHex"] != previous_list["argumentRawHex"]
        or selected_list["generic"] != previous_list["generic"]
    ):
        raise ValueError(f"{LABEL}.native:target-list-dependency")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(reads),
        "genericContextCount": len(contract["genericContexts"]),
    }


def decode_ultimate_time_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one reached UltimateTimeAction using finite target elements."""
    del depth
    _contract()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(7)
    reader.take(1, "UltimateTimeAction.isEnable.byte")
    for field in ("priorityLevel", "priorityOffset", "serverActionIndex"):
        reader.take(4, f"UltimateTimeAction.{field}.raw4")
    start = reader.pos
    for _ in range(max(0, reader.count(1, reserve=8, nullable=True))):
        reader.target_profile()
    reader.records.append(dict(start=start, end=reader.pos, kind="UltimateTimeAction.target-list"))
    reader.take(4, "UltimateTimeAction.timeDilationPriority.raw4")
    reader.take(4, "UltimateTimeAction.timeScale.float32-bits")
