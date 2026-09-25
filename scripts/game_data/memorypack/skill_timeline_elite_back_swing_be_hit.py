"""Selected-build SkillData EliteBackSwingBeHit 0x00A5 framing."""
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


LABEL = "skillTimelineEliteBackSwingBeHit"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_elite_back_swing_be_hit_native.json"
TAG = 0x00A5
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32",
    "scalar-payload", "bool-byte", "scalar-payload",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-elite-back-swing-be-hit-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    contexts = contract.get("genericContexts")
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
        or [row.get("memberIndex") for row in contexts] != [1, 4, 6]
        or [row.get("typeName") for row in contexts]
        != [
            "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
            "Beyond.Blackboard+BlackboardDouble",
            "Beyond.Blackboard+BlackboardInt",
        ]
        or [row.get("path") for row in contract.get("dependencies", ())]
        != ["buff_ec_native.json"]
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
        or [row[2] for row in setters]
        != ["Beyond.Blackboard+BlackboardDouble", "System.Boolean", "Beyond.Blackboard+BlackboardInt"]
    ):
        raise ValueError(f"{LABEL}.contract:read-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected route, seven source calls and two scalar profiles."""
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
        if (
            argument.hex().upper() != context["argumentRawHex"]
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type={index}")
    dependency = json.loads((CONTRACTS_DIR / contract["dependencies"][0]["path"]).read_bytes())
    if dependency.get("schemaVersion") != 1:
        raise ValueError(f"{LABEL}.native:scalar-dependency-schema")
    image.check_windows(dependency["codeWindows"], label=f"{LABEL}.buff_ec_native")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(reads),
        "genericContextCount": len(contract["genericContexts"]),
    }


def decode_elite_back_swing_be_hit_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one reached EliteBackSwingBeHit with finite scalar profiles."""
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(7)
    reader.take(1, "EliteBackSwingBeHit.isEnable.byte")
    for field in ("priorityLevel", "priorityOffset", "serverActionIndex"):
        reader.take(4, f"EliteBackSwingBeHit.{field}.raw4")
    reader.scalar_payload()
    reader.take(1, "EliteBackSwingBeHit.finishByAction.byte")
    reader.scalar_payload()
