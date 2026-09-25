"""Selected-build finite SkillData JumpToTarget 0x00DA reader.

The native source pins eleven ordered fields. Its two TargetSettings, one BlackboardVector3 and two
BlackboardDouble children reuse independently reviewed finite profiles.
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


LABEL = "skillTimelineJumpToTarget"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_jump_to_target_native.json"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "jumpSource", "jumpToPosition", "jumpToTarget", "maxHeight", "time",
    "useMaxHeight", "useWorldPosition",
)
READ_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32", "target-profile",
    "blackboard-vector3", "target-profile", "blackboard-scalar", "blackboard-scalar",
    "bool-byte", "bool-byte",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-jump-to-target-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != 0x00DA
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [4, 5, 6, 7, 8]
        or [row.get("typeName") for row in contexts] != [
            "Beyond.Gameplay.Core.TargetSettings",
            "Beyond.Blackboard+BlackboardVector3",
            "Beyond.Gameplay.Core.TargetSettings",
            "Beyond.Blackboard+BlackboardDouble",
            "Beyond.Blackboard+BlackboardDouble",
        ]
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected route, eleven source reads and nested types."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]
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
    for dependency in contract["dependencies"]:
        reviewed = json.loads((CONTRACTS_DIR / dependency["path"]).read_bytes())
        if reviewed.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:dependency-schema={dependency['path']}")
        image.check_windows(reviewed.get("codeWindows", []), label=f"{LABEL}.{dependency['path']}")
        image.check_windows(reviewed.get("dataWindows", []), gate="data-window", label=f"{LABEL}.{dependency['path']}")
    for context in contract["nestedContexts"]:
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
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        definition = struct.unpack_from("<Q", argument)[0]
        if (
            argument.hex().upper() != context["argumentRawHex"]
            or argument[10] != context["typeKind"]
            or definition != context["typeDefinition"]
            or image.type_name(definition) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:nested-type")
    return {
        "status": "validated", "nativeInputs": expected, "methodIndices": methods,
        "sourceReadCount": len(READ_KINDS), "nestedContextCount": len(contract["nestedContexts"]),
    }


def decode_jump_to_target_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite eleven-member JumpToTarget action."""
    del depth
    contract = _contract()
    if tag != contract["dispatcher"]["unionTag"] or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    for kind in READ_KINDS:
        if kind == "bool-byte":
            reader.take(1, "JumpToTarget.bool-byte")
        elif kind == "scalar32":
            reader.take(4, "JumpToTarget.scalar32")
        elif kind == "blackboard-scalar":
            reader.scalar_payload()
        elif kind == "blackboard-vector3":
            reader.vector_payload()
        else:
            reader.target_profile()
