"""Selected-build SkillData HideUIAction 0x00C6 framing."""
from __future__ import annotations

import hashlib
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineHideUI"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_hide_ui_native.json"
TAG = 0x00C6
@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-hide-ui-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    contexts = contract.get("genericContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != 5
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(5))
        or not isinstance(setters, list)
        or len(setters) != 1
        or len(setters[0]) != 3
        or not setters[0][1].startswith("set___")
        or not setters[0][1].endswith("__")
        or setters[0][2] != "System.Boolean"
        or not isinstance(setter_calls, list)
        or len(setter_calls) != 1
        or setter_calls[0].get("memberIndex") != 4
        or setter_calls[0].get("methodIndex") != setters[0][0]
        or not isinstance(contexts, list)
        or len(contexts) != 1
        or contexts[0].get("memberIndex") != 1
        or contexts[0].get("typeName")
        != "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority"
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xFE\x05"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    expected_fields = ["isEnable", "priorityLevel", "priorityOffset", "serverActionIndex"]
    expected_fields.append(setters[0][1].removeprefix("set___").removesuffix("__"))
    if (
        [row.get("fieldName") for row in reads] != expected_fields
        or reads[0]["readKind"] != "bool-byte"
        or reads[1]["readKind"] != "enum32"
        or any(reads[index]["readKind"] != "scalar32" for index in (2, 3))
        or reads[4]["readKind"] != "bool-byte"
    ):
        raise ValueError(f"{LABEL}.contract:read-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected route and its finite five-source reader."""
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
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if target != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    setter = contract["setterCallsites"][0]
    rva = setter["callsiteRva"]
    if not previous < rva < contract["codeWindows"][1]["endRva"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != setter["callHex"]:
        raise ValueError(f"{LABEL}.native:setter-call")
    target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
    method = image.metadata.methods[setter["methodIndex"]]
    if (
        target != setter["targetRva"]
        or image.method_pointer_va(method) != image.pe.image_base + target
    ):
        raise ValueError(f"{LABEL}.native:setter-target")
    context = contract["genericContexts"][0]
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
    if (
        argument.hex().upper() != context["argumentRawHex"]
        or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
        or image.type_name(context["typeDefinition"]) != context["typeName"]
    ):
        raise ValueError(f"{LABEL}.native:generic-type")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(contract["orderedSourceReads"]),
        "genericContextCount": len(contract["genericContexts"]),
    }


def decode_hide_ui_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume a reached HideUIAction and stop at malformed framing."""
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(1, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(5)
    reader.take(1, "HideUIAction.isEnable.byte")
    for field in ("priorityLevel", "priorityOffset", "serverActionIndex"):
        reader.take(4, f"HideUIAction.{field}.raw4")
    reader.take(1, "HideUIAction.onlyBlockInput.byte")
