"""Selected-build SkillData StoreCurSkillExecuteFrame 0x0173 reader.

The six source reads retain the stored key and TargetSettings as distinct
bounded child spans. Runtime frame storage is outside this format contract.
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


LABEL = "skillTimelineStoreCurSkillExecuteFrame"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_store_cur_skill_execute_frame_native.json"
TAG = 0x0173
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "blackboardKey", "target",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "byte-payload",
    "target-profile",
)
GENERIC_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "Beyond.Gameplay.Core.TargetSettings",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-store-cur-skill-execute-frame-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 5]
        or tuple(row.get("typeName") for row in contexts) != GENERIC_TYPES
        or not isinstance(setters, list)
        or [row[1] for row in setters] != [
            "set___blackboardKey__", "set___target__",
        ]
        or not isinstance(setter_calls, list)
        or [row.get("memberIndex") for row in setter_calls] != [4, 5]
        or [row.get("methodIndex") for row in setter_calls] != [row[0] for row in setters]
        or [row.get("path") for row in contract.get("dependencies", ())]
        != ["buff_ec_native.json"]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xFE" + bytes([len(FIELD_NAMES)])
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected route, ordered source calls and child type."""
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
            if member + 1 < len(reads) else contract["codeWindows"][0]["endRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter-order={member}")
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != setter["callHex"]:
            raise ValueError(f"{LABEL}.native:setter-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        method = image.metadata.methods[setter["methodIndex"]]
        if target != setter["targetRva"] or image.method_pointer_va(method) != image.pe.image_base + target:
            raise ValueError(f"{LABEL}.native:setter-target={member}")
    for context in contract["genericContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
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
            or argument[10] != context["typeKind"]
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type={index}")
    dependency = json.loads((CONTRACTS_DIR / contract["dependencies"][0]["path"]).read_bytes())
    if dependency.get("schemaVersion") != 1:
        raise ValueError(f"{LABEL}.native:target-dependency-schema")
    image.check_windows(dependency["codeWindows"], label=f"{LABEL}.buff_ec_native")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
        "genericContextCount": len(GENERIC_TYPES),
    }


def decode_store_cur_skill_execute_frame_action(
    reader: Reader, depth: int, tag: int, width: int,
) -> None:
    """Consume one reached six-member action with a bounded target profile."""
    del depth
    _contract()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(FIELD_NAMES))
    reader.take(1, "StoreCurSkillExecuteFrame.isEnable.byte")
    for field in FIELD_NAMES[1:4]:
        reader.take(4, f"StoreCurSkillExecuteFrame.{field}.raw4")
    reader.byte_payload()
    reader.target_profile()
