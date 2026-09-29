"""Selected-native SkillData ChangeSpecificLayerAction action 0x002E.

This closes stored action framing only; it does not prove a runtime layer
transition or selected entity.
"""
from __future__ import annotations

import hashlib
import json
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


LABEL = "skillTimelineChangeSpecificLayer"
TAG = 0x002E
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_change_specific_layer_native.json"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_ChangeSpecificLayerAction_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.ChangeSpecificLayerAction+Data"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "originLayerMask", "targetLayerMask", "targetSettings",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "layer-mask-raw4",
    "layer-mask-raw4", "target-profile",
)
NESTED_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "UnityEngine.LayerMask", "UnityEngine.LayerMask",
    "Beyond.Gameplay.Core.TargetSettings",
)
SETTER_TYPES = (
    ("set___originLayerMask__", "UnityEngine.LayerMask"),
    ("set___targetLayerMask__", "UnityEngine.LayerMask"),
    ("set___targetSettings__", "Beyond.Gameplay.Core.TargetSettings"),
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-change-specific-layer-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    instructions = contract.get("layerMaskReadInstructions")
    advance = contract.get("layerMaskAdvanceCall")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or reads[4]["sourceTargetRva"] != reads[5]["sourceTargetRva"]
        or not isinstance(contexts, list) or len(contexts) != 4
        or [row.get("memberIndex") for row in contexts] != [1, 4, 5, 6]
        or tuple(row.get("typeName") for row in contexts) != NESTED_TYPES
        or not isinstance(setters, list)
        or tuple(tuple(row[1:]) for row in setters) != SETTER_TYPES
        or not isinstance(setter_calls, list) or len(setter_calls) != 3
        or [row.get("memberIndex") for row in setter_calls] != [4, 5, 6]
        or [row.get("methodIndex") for row in setter_calls] != [row[0] for row in setters]
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or contract.get("advanceReadContract") != "buff_e0_native.json"
        or contract.get("nestedProfileContract") != "buff_ec_native.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or len(contract.get("methods", ())) != 2
        or len(contract.get("codeWindows", ())) != 3
        or contract["codeWindows"][2].get("startRva") != reads[4]["sourceTargetRva"]
        or contract.get("memberCountInstruction", {}).get("hex") != "807C243807"
        or not isinstance(instructions, list) or len(instructions) != 2
        or [row.get("hex") for row in instructions] != ["83793004", "BA04000000"]
        or not isinstance(advance, Mapping)
        or advance.get("targetRva") is None
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Reprove all seven source calls and the four-byte LayerMask helper."""
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
    image.check_instruction_windows(
        [[row["rva"], row["hex"]] for row in contract["layerMaskReadInstructions"]],
        label=LABEL,
    )
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")

    primitive = json.loads((CONTRACTS_DIR / contract["primitiveReadContract"]).read_bytes())
    targets = {row["sourceTargetRva"] for row in contract["orderedSourceReads"]
               if row["readKind"] in ("bool-byte", "enum32", "scalar32")}
    targets.add(contract["memberHeaderSourceCall"]["sourceTargetRva"])
    windows = [row for row in primitive.get("codeWindows", ())
               if row.get("startRva") in targets]
    if primitive.get("schemaVersion") != 1 or {row["startRva"] for row in windows} != targets:
        raise ValueError(f"{LABEL}.native:primitive-source-drift")
    image.check_windows(windows, label=LABEL)
    advance_contract = json.loads((CONTRACTS_DIR / contract["advanceReadContract"]).read_bytes())
    advance_target = contract["layerMaskAdvanceCall"]["targetRva"]
    advance_windows = [row for row in advance_contract.get("codeWindows", ())
                       if row.get("startRva") == advance_target]
    if advance_contract.get("schemaVersion") != 1 or len(advance_windows) != 1:
        raise ValueError(f"{LABEL}.native:layer-mask-advance-drift")
    image.check_windows(advance_windows, label=LABEL)
    _check_call(image, contract["layerMaskAdvanceCall"], rva_key="callsiteRva",
                hex_key="callHex", target_key="targetRva")
    nested = json.loads((CONTRACTS_DIR / contract["nestedProfileContract"]).read_bytes())
    if (nested.get("schemaVersion") != 1
            or len(nested.get("anonymousReadOrder", {}).get("member13", ())) != 13):
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
            "genericContextCount": len(NESTED_TYPES), "layerMaskWidth": 4}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 1 or reader.data[reader.pos:reader.pos + 1] != b"\x2e":
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(1, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(len(FIELD_NAMES))
    fields = []
    for name, kind in zip(FIELD_NAMES, READ_KINDS):
        field_start = reader.pos
        if kind == "bool-byte":
            reader.take(1, name)
        elif kind in ("enum32", "scalar32", "layer-mask-raw4"):
            reader.take(4, name)
        elif kind == "target-profile":
            reader.target_profile()
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
    if type(offset) is not int or offset < 0 or offset + 2 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 1)


def decode_change_specific_layer_action(reader: Reader, depth: int, tag: int,
                                        width: int) -> None:
    del depth
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
