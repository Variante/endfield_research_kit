"""Selected-build SkillData MoveToDirectionAction 0x00F7 source reader.

The source fixes nineteen ordered reads and five nested generic contexts.
Stored motion fields are structural evidence, not runtime movement proof.
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


LABEL = "skillTimelineMoveToDirection"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_move_to_direction_native.json"
TAG = 0x00F7
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "directionType", "ignoreAllCollision", "ignoreCollisionLayer",
    "ignoreNavmesh", "maxDistance", "moveSpeed", "moveTo",
    "overrideMoveSpeed", "overrideRotateRate", "overrideStepOffset",
    "rotateRate", "speedCurve", "stepOffset", "stopByCliff", "useSpeedCurve",
)
READ_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32", "scalar32",
    "bool-byte", "layer-mask-raw4", "bool-byte", "float32-bits",
    "float32-bits", "target-profile", "bool-byte", "bool-byte",
    "bool-byte", "float32-bits", "curve-profile", "float32-bits",
    "bool-byte", "bool-byte",
)
_READERS = {
    "bool-byte": lambda reader: reader.take(1, "MoveToDirectionAction.bool-byte"),
    "scalar32": lambda reader: reader.take(4, "MoveToDirectionAction.scalar32"),
    "float32-bits": lambda reader: reader.take(4, "MoveToDirectionAction.float32-bits"),
    "layer-mask-raw4": lambda reader: reader.take(4, "MoveToDirectionAction.LayerMask-raw4"),
    "target-profile": lambda reader: reader.target_profile(),
    "curve-profile": lambda reader: reader.curve_profile(),
}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-move-to-direction-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list)
        or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 4, 6, 10, 15]
        or [row.get("typeName") for row in contexts] != [
            "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
            "Beyond.Gameplay.Core.MoveToDirectionAction+DirectionType",
            "UnityEngine.LayerMask", "Beyond.Gameplay.Core.TargetSettings",
            "UnityEngine.AnimationCurve",
        ]
        or [row.get("path") for row in contract.get("dependencies", ())]
        != ["buff_1f_native.json", "buff_ec_native.json", "buff_98_native.json"]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7c\x24\x38" + bytes([len(FIELD_NAMES)])
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate selected route, nineteen reads and five generic types."""
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
        image.check_windows(reviewed["codeWindows"], label=f"{LABEL}.{dependency['path']}")
    for context in contract["nestedContexts"]:
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
            raise ValueError(f"{LABEL}.native:method-spec-record={context['memberIndex']}")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity={context['memberIndex']}")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        definition = struct.unpack_from("<Q", argument)[0]
        if (
            argument.hex().upper() != context["argumentRawHex"]
            or argument[10] != context["typeKind"]
            or definition != context["typeDefinition"]
            or image.type_name(definition) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:nested-type={context['memberIndex']}")
    return {
        "status": "validated", "nativeInputs": expected, "methodIndices": methods,
        "sourceReadCount": len(READ_KINDS), "nestedContextCount": len(contract["nestedContexts"]),
    }


def decode_move_to_direction_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one nineteen-member action with reviewed finite nested profiles."""
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
        _READERS[kind](reader)
