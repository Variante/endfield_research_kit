"""Selected-build SkillData RemoveAIMarkerAction reader.

The stored marker is a raw GameplayTag DWORD. The owner is a finite
TargetSettings profile; neither value proves live marker removal.
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
from scripts.game_data.memorypack.buff import (
    _ability_action_tag, _ability_action_tag_bytes,
)
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.formatter_native import check_formatter_windows, is_role_projection
from scripts.game_data.memorypack.skill_timeline_dependencies import validate_dependencies


LABEL = "skillTimelineRemoveAIMarker"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_remove_ai_marker_native.json"
TAG_NAME = "Core_RemoveAIMarkerAction_Data"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "marker", "markerOwner",
)
READ_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32",
    "gameplay-tag32", "target-profile",
)
NESTED_NAMES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "Beyond.Gameplay.Core.GameplayTag",
    "Beyond.Gameplay.Core.TargetSettings",
)


@lru_cache(maxsize=1)
def _contract(*, gameassembly=None, metadata=None) -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-remove-ai-marker-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != _ability_action_tag(TAG_NAME, gameassembly=gameassembly, metadata=metadata)
        or contract.get("serializedMemberCount") != len(READ_KINDS)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(READ_KINDS)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or tuple(row.get("memberIndex") for row in contexts) != (1, 4, 5)
        or tuple(row.get("typeName") for row in contexts) != NESTED_NAMES
        or [row.get("path") for row in contract.get("dependencies", [])]
        != ["memorypack_gameplay_tag_source_native.json", "buff_ec_native.json"]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7C\x24\x38\x06"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly=None, metadata=None) -> dict[str, Any]:
    """Authenticate selected dispatch, ordered source calls and nested types."""
    if (gameassembly is None) != (metadata is None):
        raise ValueError(f"{LABEL}.native:both-selected-paths-required")
    contract = _contract(gameassembly=gameassembly, metadata=metadata)
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata,
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
    check_formatter_windows(image, contract, label=LABEL)
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
        if (
            argument.hex().upper() != context["argumentRawHex"]
            or argument[10] != context["typeKind"]
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:nested-type")
    validate_dependencies(image, contract, label=LABEL)

    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(contract["orderedSourceReads"]),
        "nestedContextCount": len(contract["nestedContexts"]),
    }


def decode_remove_ai_marker_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one reached six-member action and stop on unsupported children."""
    del depth
    contract = _contract()
    if (tag != contract["dispatcher"]["unionTag"]
            or width != len(_ability_action_tag_bytes(TAG_NAME))):
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, "RemoveAIMarkerAction.isEnable.byte")
    for field in ("priorityLevel", "priorityOffset", "serverActionIndex", "marker"):
        reader.take(4, f"RemoveAIMarkerAction.{field}.raw4")
    reader.target_profile()
