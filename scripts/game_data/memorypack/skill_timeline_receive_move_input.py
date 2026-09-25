"""Selected-build SkillData ReceiveMoveInputAction 0x0123 framing.

The reviewed native reader fixes twenty source reads and a nested nine-member
MoveParamData reader. BlackboardDouble and AnimationCurve children reuse
separately bounded profiles. Gameplay execution remains outside this reader.
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


LABEL = "skillTimelineReceiveMoveInput"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_receive_move_input_native.json"
TAG = 0x0123
OUTER_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "bool-byte", "bool-byte",
    "scalar-payload", "bool-byte", "scalar-payload", "enum32", "bool-byte",
    "bool-byte", "scalar-payload", "scalar-payload", "scalar-payload",
    "curve-profile", "scalar-payload", "enum32", "move-param-profile", "bool-byte",
)
OUTER_FIELDS = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "combineRootMotion", "disableCliffCheck", "duration", "faceToMoveDir",
    "inputAlongRMScale", "inputDirection", "overrideRotateSpeed",
    "recoverWhenLanding", "rootMotionScale", "rotateSpeed", "speed",
    "speedCurve", "speedScale", "speedType", "teammateParam",
    "useTeammateParam",
)
INNER_KINDS = (
    "bool-byte", "bool-byte", "enum32", "bool-byte", "scalar-payload",
    "scalar-payload", "curve-profile", "scalar-payload", "enum32",
)
INNER_FIELDS = (
    "disableDynamicPush", "faceToMoveDir", "inputDirection",
    "overrideRotateSpeed", "rotateSpeed", "speed", "speedCurve",
    "speedScale", "speedType",
)
OUTER_GENERIC_TYPES = (
    (1, "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority"),
    (6, "Beyond.Blackboard+BlackboardDouble"),
    (8, "Beyond.Blackboard+BlackboardDouble"),
    (9, "Beyond.Gameplay.Core.ReceiveMoveInputAction+DirectionType"),
    (12, "Beyond.Blackboard+BlackboardDouble"),
    (13, "Beyond.Blackboard+BlackboardDouble"),
    (14, "Beyond.Blackboard+BlackboardDouble"),
    (15, "UnityEngine.AnimationCurve"),
    (16, "Beyond.Blackboard+BlackboardDouble"),
    (17, "Beyond.Gameplay.Core.ReceiveMoveInputAction+SpeedType"),
    (18, "Beyond.Gameplay.Core.ReceiveMoveInputAction+Data+MoveParamData"),
)
INNER_GENERIC_TYPES = (
    (2, "Beyond.Gameplay.Core.ReceiveMoveInputAction+DirectionType"),
    (4, "Beyond.Blackboard+BlackboardDouble"),
    (5, "Beyond.Blackboard+BlackboardDouble"),
    (6, "UnityEngine.AnimationCurve"),
    (7, "Beyond.Blackboard+BlackboardDouble"),
    (8, "Beyond.Gameplay.Core.ReceiveMoveInputAction+SpeedType"),
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-receive-move-input-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    if contract.get("dispatcher", {}).get("unionTag") != TAG:
        raise ValueError(f"{LABEL}.contract:route")
    for key, kinds, fields, types in (
        ("outer", OUTER_KINDS, OUTER_FIELDS, OUTER_GENERIC_TYPES),
        ("moveParam", INNER_KINDS, INNER_FIELDS, INNER_GENERIC_TYPES),
    ):
        block = contract.get(key)
        if not isinstance(block, dict):
            raise ValueError(f"{LABEL}.contract:{key}-missing")
        reads = block.get("orderedSourceReads")
        contexts = block.get("genericContexts")
        if (
            block.get("serializedMemberCount") != len(kinds)
            or not isinstance(reads, list)
            or [row.get("memberIndex") for row in reads] != list(range(len(kinds)))
            or tuple(row.get("fieldName") for row in reads) != fields
            or tuple(row.get("readKind") for row in reads) != kinds
            or not isinstance(contexts, list)
            or tuple((row.get("memberIndex"), row.get("typeName")) for row in contexts)
            != types
        ):
            raise ValueError(f"{LABEL}.contract:{key}-source-shape")
    move_param = contract["moveParam"]
    if move_param.get("wrapperName") != (
        "Beyond.MemoryPack.Beyond_Gameplay_Core_ReceiveMoveInputAction_Data_MoveParamDataForMemoryPack"
    ):
        raise ValueError(f"{LABEL}.contract:move-param-wrapper")
    if [row.get("path") for row in contract.get("dependencies", ())] != [
        "buff_ec_native.json", "buff_98_native.json"
    ]:
        raise ValueError(f"{LABEL}.contract:dependencies")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove selected route, both source readers and all generic arguments."""
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
    image.check_instruction_windows(
        [[row["rva"], row["hex"]] for row in contract["memberCountInstructions"]],
        label=LABEL,
    )
    for key, definition in (("outer", contract["dispatcher"]["wrapperTypeDefinition"]), ("moveParam", contract["moveParam"]["wrapperTypeDefinition"])):
        block = contract[key]
        owner = image.metadata.types[definition]
        if key == "moveParam" and image.type_name(definition) != block["wrapperName"]:
            raise ValueError(f"{LABEL}.native:move-param-wrapper")
        if image.setter_methods(owner, parameter="typeName", label=LABEL) != block["setterMethods"]:
            raise ValueError(f"{LABEL}.native:{key}-setter-order")
        previous = -1
        for read in block["orderedSourceReads"]:
            rva = read["sourceCallsiteRva"]
            if rva <= previous:
                raise ValueError(f"{LABEL}.native:{key}-source-order")
            previous = rva
            raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
            if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
                raise ValueError(f"{LABEL}.native:{key}-source-call={rva:#x}")
            target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
            if target != read["sourceTargetRva"]:
                raise ValueError(f"{LABEL}.native:{key}-source-target={rva:#x}")
        for context in block["genericContexts"]:
            cell, usage = image.nested_usage_cell(context, label=LABEL)
            index = method_spec_usage_index(
                usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell
            )
            if index != context["methodSpecIndex"]:
                raise ValueError(f"{LABEL}.native:{key}-method-spec={context['memberIndex']}")
            address = int(image.registration["methodSpecs"], 16) + index * 12
            spec = method_spec_record(
                image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
                image.registration["genericInstsCount"], source=LABEL, offset=address,
            )
            if list(spec) != context["methodSpec"]:
                raise ValueError(f"{LABEL}.native:{key}-method-spec-record={index}")
            instance = image.instantiations.resolve(spec[2])
            if len(instance.arguments) != 1:
                raise ValueError(f"{LABEL}.native:{key}-generic-arity={index}")
            argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
            if (
                argument.hex().upper() != context["argumentRawHex"]
                or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
                or image.type_name(context["typeDefinition"]) != context["typeName"]
            ):
                raise ValueError(f"{LABEL}.native:{key}-generic-type={index}")
    for dependency in contract["dependencies"]:
        reviewed = json.loads((CONTRACTS_DIR / dependency["path"]).read_bytes())
        if reviewed.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:dependency-schema={dependency['path']}")
        image.check_windows(reviewed["codeWindows"], label=f"{LABEL}.{dependency['path']}")
    return {
        "status": "validated", "nativeInputs": expected, "methodIndices": methods,
        "outerReadCount": len(OUTER_KINDS), "moveParamReadCount": len(INNER_KINDS),
        "genericContextCount": len(OUTER_GENERIC_TYPES) + len(INNER_GENERIC_TYPES),
    }


def _move_param_profile(reader: Reader) -> None:
    start = reader.pos
    if reader.peek() == 0xFF:
        reader.take(1, "ReceiveMoveInputAction.MoveParamData.null")
    else:
        reader.header(len(INNER_KINDS))
        for _ in range(2):
            reader.take(1, "ReceiveMoveInputAction.MoveParamData.bool-byte")
        reader.take(4, "ReceiveMoveInputAction.MoveParamData.enum32")
        reader.take(1, "ReceiveMoveInputAction.MoveParamData.bool-byte")
        reader.scalar_payload()
        reader.scalar_payload()
        reader.curve_profile()
        reader.scalar_payload()
        reader.take(4, "ReceiveMoveInputAction.MoveParamData.enum32")
    reader.records.append({"start": start, "end": reader.pos, "kind": "receive-move-input-param-profile"})


def decode_receive_move_input_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one reached tag-0x0123 action, with bounded nested profiles."""
    del depth
    _contract()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(OUTER_KINDS))
    reader.take(1, "ReceiveMoveInputAction.bool-byte")
    for _ in range(3):
        reader.take(4, "ReceiveMoveInputAction.scalar32")
    for _ in range(2):
        reader.take(1, "ReceiveMoveInputAction.bool-byte")
    reader.scalar_payload()
    reader.take(1, "ReceiveMoveInputAction.bool-byte")
    reader.scalar_payload()
    reader.take(4, "ReceiveMoveInputAction.enum32")
    for _ in range(2):
        reader.take(1, "ReceiveMoveInputAction.bool-byte")
    for _ in range(3):
        reader.scalar_payload()
    reader.curve_profile()
    reader.scalar_payload()
    reader.take(4, "ReceiveMoveInputAction.enum32")
    _move_param_profile(reader)
    reader.take(1, "ReceiveMoveInputAction.bool-byte")
