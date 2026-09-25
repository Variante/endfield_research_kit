"""Selected-build SkillData SnapToTargetWithRangeAction 0x0168 reader.

The finite member sequence comes from the selected native Deserialize body.
Nested TargetSettings, AnimationCurve and BlackboardDouble fields reuse the
existing bounded profiles. Whole-file status remains the caller's decision.
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


LABEL = "skillSnapToTargetWithRange"
CONTRACT_PATH = CONTRACTS_DIR / "skill_snap_to_target_with_range_native.json"
_READERS = {
    "bool-byte": lambda reader: reader.take(1, "SnapToTargetWithRangeAction.bool-byte"),
    "enum-int32": lambda reader: reader.take(4, "SnapToTargetWithRangeAction.enum-int32"),
    "int32": lambda reader: reader.take(4, "SnapToTargetWithRangeAction.int32"),
    "float32-bits": lambda reader: reader.take(4, "SnapToTargetWithRangeAction.float32-bits"),
    "byte-payload": lambda reader: reader.byte_payload(),
    "target-profile": lambda reader: reader.target_profile(),
    "curve-profile": lambda reader: reader.curve_profile(),
    "scalar-payload": lambda reader: reader.scalar_payload(),
}
@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-snap-to-target-with-range-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    if (
        not isinstance(reads, list)
        or len(reads) != contract.get("serializedMemberCount")
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or any(not isinstance(row.get("fieldName"), str) or row.get("kind") not in _READERS for row in reads)
        or contract.get("dispatcher", {}).get("unionTag") != 0x0168
        or not isinstance(contract.get("nestedContexts"), list)
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove route, full normal body, source reads and nested types."""
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
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_instruction_windows(
        [[contract["memberCountInstruction"]["rva"], contract["memberCountInstruction"]["hex"]]],
        label=LABEL,
    )
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
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec={context['instructionRva']:#x}")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        if list(spec) != context["methodSpec"]:
            raise ValueError(f"{LABEL}.native:method-spec-record={index}")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity={index}")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        if (
            argument.hex().upper() != context["argumentRawHex"].upper()
            or argument[10] not in (0x11, 0x12)
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type={index}")
    return {
        "status": "validated",
        "nativeInputs": expected,
        "methodIndices": methods,
        "sourceReadCount": len(contract["orderedSourceReads"]),
        "nestedContextCount": len(contract["nestedContexts"]),
    }


def decode_snap_to_target_with_range_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one 0x0168 action with only authenticated finite profiles."""
    del depth
    contract = _contract()
    if tag != contract["dispatcher"]["unionTag"] or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(contract["orderedSourceReads"]))
    for read in contract["orderedSourceReads"]:
        _READERS[read["kind"]](reader)
