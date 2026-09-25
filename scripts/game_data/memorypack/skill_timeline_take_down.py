"""Selected-build SkillData TakeDownAction 0x017A storage framing.

The nested BlackboardDouble, DirectionSettings and TargetSettings members
reuse finite reviewed profiles. Stored fields do not establish live takedown
behavior or an enclosing SkillData EOF.
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


LABEL = "skillTimelineTakeDown"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_take_down_native.json"
TAG = 0x017A
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_TakeDownAction_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.TakeDownAction+Data"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "deadOption", "duration", "faceDirection", "immobilizedTime",
    "returnTrueWhen", "source", "targetSettings", "teammateBigStagger",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "enum32",
    "blackboard-double", "direction-settings", "float32", "enum32",
    "target-settings", "target-settings", "bool-byte",
)
GENERIC_TYPES = {
    1: "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    4: "Beyond.Gameplay.ControlledStateDeadOption",
    5: "Beyond.Blackboard+BlackboardDouble",
    6: "Beyond.Gameplay.Core.DirectionSettings",
    8: "Beyond.Gameplay.Core.AbilityAction+ReturnTrueMethod",
    9: "Beyond.Gameplay.Core.TargetSettings",
    10: "Beyond.Gameplay.Core.TargetSettings",
}
OWN_FIELDS = FIELD_NAMES[4:]


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-take-down-native-contract.v1",
        label=LABEL, status="exact-current-build",
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
        or [row.get("memberIndex") for row in contexts] != list(GENERIC_TYPES)
        or [row.get("typeName") for row in contexts] != list(GENERIC_TYPES.values())
        or not isinstance(setters, list) or len(setters) != len(OWN_FIELDS)
        or [row[1] for row in setters]
        != [f"set___{field}__" for field in sorted(OWN_FIELDS)]
        or not isinstance(setter_calls, list)
        or [row.get("memberIndex") for row in setter_calls] != list(range(4, 12))
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xFE\x0C"
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
        or switch.get("base")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
        or catalog.get("nativeInputs", {}).get("gameAssemblySha256")
        != contract["nativeInputs"]["GameAssembly.dll"]
        or catalog.get("nativeInputs", {}).get("metadataSha256")
        != contract["nativeInputs"]["global-metadata.dat"]
    ):
        raise ValueError(f"{LABEL}.contract:catalog-route")
    return contract


def _check_call(image: Any, call: dict[str, Any], *, setter: bool = False) -> None:
    rva = call["callsiteRva"] if setter else call["sourceCallsiteRva"]
    expected = call["callHex"] if setter else call["sourceCallHex"]
    target = call["targetRva"] if setter else call["sourceTargetRva"]
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected:
        raise ValueError(f"{LABEL}.native:{'setter' if setter else 'source'}-call={rva:#x}")
    if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target:
        raise ValueError(f"{LABEL}.native:call-target={rva:#x}")


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected dispatch, ordered reads, setters and generic types."""
    contract = _contract()
    expected = contract["nativeInputs"]
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
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    if (
        int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    owner = image.check_wrapper_inheritance(contract["wrapper"], label=LABEL)
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    member = contract["memberCountInstruction"]
    image.check_instruction_windows([[member["rva"], member["hex"]]], label=LABEL)
    body = contract["codeWindows"][0]
    previous = -1
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if not body["startRva"] <= rva < body["endRva"] or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        _check_call(image, read)
        previous = rva
    setters = {row[0]: row for row in contract["setterMethods"]}
    for call in contract["setterCallsites"]:
        index = call["memberIndex"]
        if call["methodIndex"] not in setters:
            raise ValueError(f"{LABEL}.native:unreviewed-setter")
        row = setters[call["methodIndex"]]
        if row[1] != f"set___{FIELD_NAMES[index]}__":
            raise ValueError(f"{LABEL}.native:setter-field-order")
        next_source = (
            contract["orderedSourceReads"][index + 1]["sourceCallsiteRva"]
            if index + 1 < len(FIELD_NAMES) else body["endRva"]
        )
        if not contract["orderedSourceReads"][index]["sourceCallsiteRva"] < call["callsiteRva"] < next_source:
            raise ValueError(f"{LABEL}.native:setter-call-order")
        _check_call(image, call, setter=True)
        image.validate_method_row([row[0], WRAPPER_NAME, row[1], call["targetRva"]], label=LABEL)
    for context in contract["genericContexts"]:
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
        definition = struct.unpack_from("<Q", raw)[0]
        if (
            raw.hex().upper() != context["argumentRawHex"]
            or raw[10] != context["typeKind"]
            or definition != context["typeDefinition"]
            or image.type_name(definition) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type")
    for dependency in contract["dependencies"]:
        reviewed = json.loads((CONTRACTS_DIR / dependency["path"]).read_bytes())
        if reviewed.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:dependency-schema")
        image.check_windows(reviewed["codeWindows"], label=f"{LABEL}.{dependency['path']}")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(FIELD_NAMES),
        "nestedContextCount": len(GENERIC_TYPES),
    }


def decode_take_down_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite twelve-member action, preserving raw scalar bits."""
    del depth
    _contract()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(FIELD_NAMES))
    reader.take(1, "TakeDownAction.isEnable.byte")
    for field in FIELD_NAMES[1:5]:
        reader.take(4, f"TakeDownAction.{field}.raw4")
    reader.scalar_payload()
    reader.direction_profile()
    reader.take(4, "TakeDownAction.immobilizedTime.raw4")
    reader.take(4, "TakeDownAction.returnTrueWhen.raw4")
    reader.target_profile()
    reader.target_profile()
    reader.take(1, "TakeDownAction.teammateBigStagger.byte")
