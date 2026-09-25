"""Selected-build SkillData reader for CustomRootMotionAction union 0x0099.

The contract owns the member read order. This module reuses the bounded
MemoryPack profiles that the selected native source calls identify, and leaves
all stored values anonymous to callers. A SkillData action is exact only when
its enclosing timeline and top-level continuation independently rejoin.
"""
from __future__ import annotations

import hashlib
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


CONTRACT_PATH = CONTRACTS_DIR / "skill_custom_root_motion_native.json"
LABEL = "skillCustomRootMotion"


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-custom-root-motion-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = value.get("orderedSourceReads")
    if (
        not isinstance(reads, list)
        or not reads
        or len(reads) != value.get("serializedMemberCount")
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or value.get("dispatcher", {}).get("unionTag") != 0x0099
    ):
        raise ValueError(f"{LABEL}.contract:read-order-or-route")
    admitted = {
        "bool-byte", "int32", "enum-int32", "raw4", "byte-payload",
        "scalar-payload", "curve-profile", "target-profile",
    }
    if any(row.get("kind") not in admitted or not isinstance(row.get("fieldName"), str) for row in reads):
        raise ValueError(f"{LABEL}.contract:unsupported-read-kind")
    return value


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove route, body, source order and nested types on selected inputs."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unityplayer.is_file():
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing")
    if hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"].upper():
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:mismatched")

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

    registration = image.registration
    for context in contract["nestedContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, registration["methodSpecsCount"], source=LABEL, offset=cell
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec={context['instructionRva']:#x}")
        address = int(registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            registration["genericInstsCount"], source=LABEL, offset=address,
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


def decode_custom_root_motion_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one reached 0x0099 union; ``Reader.action`` records its range."""
    del depth  # None of the selected 24 members is a recursive action list.
    contract = _contract()
    if tag != contract["dispatcher"]["unionTag"] or width != 1 or reader.peek() != tag:
        raise ValueError(f"{LABEL}.union-tag")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(contract["orderedSourceReads"]))
    for read in contract["orderedSourceReads"]:
        kind = read["kind"]
        if kind == "bool-byte":
            reader.take(1, "anonymous-bool-byte")
        elif kind in ("int32", "enum-int32", "raw4"):
            reader.take(4, f"anonymous-{kind}")
        elif kind == "byte-payload":
            reader.byte_payload()
        elif kind == "scalar-payload":
            reader.scalar_payload()
        elif kind == "curve-profile":
            reader.curve_profile()
        elif kind == "target-profile":
            reader.target_profile()
        else:
            raise ValueError(f"{LABEL}.contract:read-kind={kind}")
