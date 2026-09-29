"""Selected-native SkillData SetAbilityEntityDuration action 0x0146.

The selected ten-member reader stores two enums, a bool, a bounded key,
TargetSettings and BlackboardDouble after its inherited action prefix.
This is stored framing, not a runtime duration update.
"""
from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.skill_timeline_check_ability_entity_cur_duration import (
    _check_call,
    _check_context,
)


LABEL = "skillTimelineSetAbilityEntityDuration"
TAG = 0x0146
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_set_ability_entity_duration_native.json"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_SetAbilityEntityDuration_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.SetAbilityEntityDuration+Data"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "actionTargetType", "operation", "setMultipleTarget", "targetContextKey",
    "targetSettings", "value",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "enum32", "enum32",
    "bool-byte", "byte-payload", "target-profile", "blackboard-double",
)
NESTED_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "Beyond.Gameplay.ActionTargetType",
    "Beyond.Gameplay.Core.SetAbilityEntityDuration+Data+OperationType",
    "Beyond.Gameplay.Core.TargetSettings",
    "Beyond.Blackboard+BlackboardDouble",
)
SETTER_TYPES = (
    ("set___actionTargetType__", "Beyond.Gameplay.ActionTargetType"),
    ("set___operation__", "Beyond.Gameplay.Core.SetAbilityEntityDuration+Data+OperationType"),
    ("set___setMultipleTarget__", "System.Boolean"),
    ("set___targetContextKey__", "System.String"),
    ("set___targetSettings__", "Beyond.Gameplay.Core.TargetSettings"),
    ("set___value__", "Beyond.Blackboard+BlackboardDouble"),
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-set-ability-entity-duration-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 4, 5, 8, 9]
        or tuple(row.get("typeName") for row in contexts) != NESTED_TYPES
        or not isinstance(setters, list)
        or tuple(tuple(row[1:]) for row in setters) != SETTER_TYPES
        or not isinstance(setter_calls, list) or len(setter_calls) != 6
        or [row.get("memberIndex") for row in setter_calls] != list(range(4, 10))
        or [row.get("methodIndex") for row in setter_calls] != [row[0] for row in setters]
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or contract.get("nestedProfileContract") != "buff_ec_native.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or len(contract.get("methods", ())) != 2
        or len(contract.get("codeWindows", ())) != 2
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7C\x24\x38\x0A"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Reprove selected route, ten source calls and all nested types."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if (not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()
            != expected["UnityPlayer.dll"]):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or catalog.get("nativeInputs", {}).get("gameAssemblySha256") != expected["GameAssembly.dll"]
        or catalog.get("nativeInputs", {}).get("metadataSha256") != expected["global-metadata.dat"]
        or route.get("tag") != TAG or route.get("wrapperName") != WRAPPER_NAME
        or route.get("wrappedType") != TYPE_NAME
        or route.get("memberCount") != len(FIELD_NAMES)
        or switch.get("entryCount") != len(catalog["families"]["AbilityActionData"])
    ):
        raise ValueError(f"{LABEL}.native:catalog-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    if (int(switch["tableVa"], 16)
            != image.pe.image_base + contract["dispatcher"]["switchTableRva"]):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    count = contract["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")

    primitive = json.loads((CONTRACTS_DIR / contract["primitiveReadContract"]).read_bytes())
    targets = {row["sourceTargetRva"] for row in contract["orderedSourceReads"]
               if row["readKind"] in ("bool-byte", "enum32", "scalar32", "byte-payload")}
    targets.add(contract["memberHeaderSourceCall"]["sourceTargetRva"])
    windows = [row for row in primitive.get("codeWindows", ())
               if row.get("startRva") in targets]
    if primitive.get("schemaVersion") != 1 or {row["startRva"] for row in windows} != targets:
        raise ValueError(f"{LABEL}.native:primitive-source-drift")
    image.check_windows(windows, label=LABEL)
    nested = json.loads((CONTRACTS_DIR / contract["nestedProfileContract"]).read_bytes())
    if (nested.get("schemaVersion") != 1
            or len(nested.get("anonymousReadOrder", {}).get("member13", ())) != 13
            or nested.get("anonymousReadOrder", {}).get("scalar-payload")
            != ["byte-payload", "byte", "scalar32"]):
        raise ValueError(f"{LABEL}.native:nested-profile-drift")
    buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["nestedProfileContract"],
    )
    reader_window = contract["codeWindows"][0]
    previous = -1
    for call in (contract["memberHeaderSourceCall"], *contract["orderedSourceReads"]):
        rva = call["sourceCallsiteRva"]
        if not reader_window["startRva"] <= rva < reader_window["endRva"] - 4 or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        _check_call(image, call, rva_key="sourceCallsiteRva", hex_key="sourceCallHex",
                    target_key="sourceTargetRva")
    for setter in contract["setterCallsites"]:
        rva = setter["callsiteRva"]
        if not reader_window["startRva"] <= rva < reader_window["endRva"] - 4:
            raise ValueError(f"{LABEL}.native:setter-call-outside-reader")
        target = _check_call(image, setter, rva_key="callsiteRva", hex_key="callHex",
                             target_key="targetRva")
        method = image.metadata.methods[setter["methodIndex"]]
        if image.method_pointer_va(method) != image.pe.image_base + target:
            raise ValueError(f"{LABEL}.native:setter-target={rva:#x}")
    for context in contract["genericContexts"]:
        _check_context(image, context)
    return {"status": "validated", "unionTag": TAG, "nativeInputs": expected,
            "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
            "genericContextCount": len(NESTED_TYPES)}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 3 or reader.data[reader.pos:reader.pos + 3] != b"\xFA\x46\x01":
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(3, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(len(FIELD_NAMES))
    fields = []
    for name, kind in zip(FIELD_NAMES, READ_KINDS):
        field_start = reader.pos
        if kind == "bool-byte":
            reader.take(1, name)
        elif kind in ("enum32", "scalar32"):
            reader.take(4, name)
        elif kind == "byte-payload":
            reader.byte_payload()
        elif kind == "target-profile":
            reader.target_profile()
        elif kind == "blackboard-double":
            reader.scalar_payload()
        else:
            raise ValueError(f"{LABEL}.reader:unknown-kind={kind}")
        fields.append({"name": name, "kind": kind,
                       "start": field_start, "end": reader.pos})
    return {"status": "exact-stored-action-span", "tag": TAG,
            "start": start, "end": reader.pos, "fields": fields,
            "evidenceBoundary": "stored action framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation.get("status") != "validated" or validation.get("unionTag") != TAG:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 4 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 3)


def decode_set_ability_entity_duration_action(
    reader: Reader, depth: int, tag: int, width: int,
) -> None:
    del depth
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
