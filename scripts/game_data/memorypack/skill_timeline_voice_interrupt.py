"""Selected-native SkillData VoiceInterruptAction action 0x0197.

This reader proves the stored six-member action span, not a voice event or an
executed interruption. The shared SkillData parser admits this route only
under its reviewed native and source-shape gates.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.skill_timeline_check_ability_entity_cur_duration import (
    _check_call,
    _check_context,
)


LABEL = "skillTimelineVoiceInterrupt"
TAG = 0x0197
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_voice_interrupt_native.json"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_VoiceInterruptAction_VoiceInterruptActionDataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.VoiceInterruptAction+VoiceInterruptActionData"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "_canInterruptTimeMs", "_interruptImmediately",
)
READ_KINDS = ("bool-byte", "enum32", "scalar32", "scalar32", "scalar32", "bool-byte")
PRIORITY_TYPE = "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority"
SETTER_TYPES = (
    ("set____canInterruptTimeMs__", "System.Int32"),
    ("set____interruptImmediately__", "System.Boolean"),
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-voice-interrupt-native-contract.v1",
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
        or not isinstance(contexts, list) or len(contexts) != 1
        or contexts[0].get("memberIndex") != 1
        or contexts[0].get("typeName") != PRIORITY_TYPE
        or not isinstance(setters, list)
        or tuple(tuple(row[1:]) for row in setters) != SETTER_TYPES
        or not isinstance(setter_calls, list) or len(setter_calls) != 2
        or [row.get("memberIndex") for row in setter_calls] != [4, 5]
        or [row.get("methodIndex") for row in setter_calls] != [row[0] for row in setters]
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or len(contract.get("methods", ())) != 2
        or len(contract.get("codeWindows", ())) != 2
        or contract.get("memberCountInstruction", {}).get("hex") != "4080FE06"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Reprove the selected route and ordered primitive calls on explicit inputs."""
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
    targets = {row["sourceTargetRva"] for row in contract["orderedSourceReads"]}
    targets.add(contract["memberHeaderSourceCall"]["sourceTargetRva"])
    windows = [row for row in primitive.get("codeWindows", ())
               if row.get("startRva") in targets]
    if primitive.get("schemaVersion") != 1 or {row["startRva"] for row in windows} != targets:
        raise ValueError(f"{LABEL}.native:primitive-source-drift")
    image.check_windows(windows, label=LABEL)
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
    _check_context(image, contract["genericContexts"][0])
    return {"status": "validated", "unionTag": TAG, "nativeInputs": expected,
            "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
            "genericContextCount": 1}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 3 or reader.data[reader.pos:reader.pos + 3] != b"\xFA\x97\x01":
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
        reader.take(1 if kind == "bool-byte" else 4, name)
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


def decode_voice_interrupt_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    del depth
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
