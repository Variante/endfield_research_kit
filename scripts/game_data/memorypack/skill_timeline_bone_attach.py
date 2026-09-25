"""Selected-build SkillData BoneAttachAction 0x0000 framing.

Zero is an ordinary physical union route in the selected dispatcher. The
thirteen stored members include one raw twelve-byte Vector3 and one finite
TargetSettings child; gameplay attachment semantics are not inferred.
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


LABEL = "skillTimelineBoneAttach"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_bone_attach_native.json"
TAG = 0x0000
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "alwaysFollowRotation", "anchorSlot", "isAddRotation", "isLerp",
    "lerpTime", "rotateAnchor", "rotateAngles", "subSlot", "targetSettings",
)
READ_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32", "bool-byte",
    "scalar32", "bool-byte", "bool-byte", "raw-float32-bits", "scalar32",
    "raw-vector3-12", "scalar32", "target-profile",
)
SETTER_NAMES = (
    "set___alwaysFollowRotation__", "set___anchorSlot__", "set___isAddRotation__",
    "set___isLerp__", "set___lerpTime__", "set___rotateAnchor__",
    "set___rotateAngles__", "set___subSlot__", "set___targetSettings__",
)
SETTER_TYPES = (
    "System.Boolean", "Beyond.Gameplay.MountPoint", "System.Boolean",
    "System.Boolean", "System.Single", "Beyond.Gameplay.BoneAttachAction+RotateAnchor",
    "UnityEngine.Vector3", "Beyond.Gameplay.MountPoint",
    "Beyond.Gameplay.Core.TargetSettings",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-bone-attach-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    setters = contract.get("setterMethods")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != len(READ_KINDS)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(READ_KINDS)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [12]
        or [row.get("typeName") for row in contexts]
        != ["Beyond.Gameplay.Core.TargetSettings"]
        or not isinstance(setters, list)
        or tuple(row[1] for row in setters) != SETTER_NAMES
        or tuple(row[2] for row in setters) != SETTER_TYPES
        or [row.get("path") for row in contract.get("dependencies", ())]
        != ["buff_16a_native.json", "buff_ec_native.json"]
        or [row.get("memberIndex") for row in contract.get("sourceHelperWindows", ())] != [8]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xFE" + bytes([len(READ_KINDS)])
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate dispatch, ordered source reads, raw12 and TargetSettings."""
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
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"].upper():
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    float_helper = contract["sourceHelperWindows"][0]
    if float_helper["startRva"] != contract["orderedSourceReads"][8]["sourceTargetRva"]:
        raise ValueError(f"{LABEL}.native:float-helper")
    image.check_windows([float_helper], label=f"{LABEL}.float")
    context = contract["nestedContexts"][0]
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
        or context["consumerCallRva"] != contract["orderedSourceReads"][12]["sourceCallsiteRva"]
        or context["consumerTargetRva"] != contract["orderedSourceReads"][12]["sourceTargetRva"]
    ):
        raise ValueError(f"{LABEL}.native:nested-type")
    vector = json.loads((CONTRACTS_DIR / "buff_16a_native.json").read_bytes())
    target = json.loads((CONTRACTS_DIR / "buff_ec_native.json").read_bytes())
    if vector.get("schemaVersion") != 1 or target.get("schemaVersion") != 1:
        raise ValueError(f"{LABEL}.native:child-schema")
    vector_window = next(
        (row for row in vector["codeWindows"]
         if row["startRva"] == contract["orderedSourceReads"][10]["sourceTargetRva"]),
        None,
    )
    if vector_window is None or "Vector3 source length" not in vector_window["boundary"]:
        raise ValueError(f"{LABEL}.native:vector-helper")
    image.check_windows([vector_window], label=f"{LABEL}.vector")
    image.check_windows(target["codeWindows"], label=f"{LABEL}.target")
    return {
        "status": "validated", "nativeInputs": expected, "methodIndices": methods,
        "sourceReadCount": len(READ_KINDS), "nestedContextCount": 1,
    }


def decode_bone_attach_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite BoneAttachAction while preserving anonymous values."""
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, "BoneAttachAction.bool-byte")
    for _ in range(3):
        reader.take(4, "BoneAttachAction.scalar32")
    reader.take(1, "BoneAttachAction.alwaysFollowRotation.bool-byte")
    reader.take(4, "BoneAttachAction.anchorSlot.scalar32")
    reader.take(1, "BoneAttachAction.isAddRotation.bool-byte")
    reader.take(1, "BoneAttachAction.isLerp.bool-byte")
    reader.take(4, "BoneAttachAction.lerpTime.raw-float32-bits")
    reader.take(4, "BoneAttachAction.rotateAnchor.scalar32")
    reader.take(12, "BoneAttachAction.rotateAngles.raw-vector3-12")
    reader.take(4, "BoneAttachAction.subSlot.scalar32")
    reader.target_profile()
