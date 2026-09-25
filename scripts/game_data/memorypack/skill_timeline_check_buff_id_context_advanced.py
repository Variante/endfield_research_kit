"""Selected-build SkillData CheckBuffIdInContextAdvanced action reader.

The 0x0057 wrapper stores eight ordered members. Its list element and query
profiles reuse the finite MemoryPack readers pinned by the Buff source contract.
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


LABEL = "skillTimelineCheckBuffIdInContextAdvanced"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_check_buff_id_context_advanced_native.json"
TAG = 0x0057
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "blackboardKey", "buffIdList", "checkType", "query",
)
READ_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32",
    "byte-payload", "nested-generic", "scalar32", "nested-generic",
)
NESTED_TYPES = (
    "System.Collections.Generic.List`1",
    "Beyond.Gameplay.Core.GameplayTagQuery",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-check-buff-id-context-advanced-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or contract.get("nestedSourceContract") != "buff_57_native.json"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def _nested_source() -> dict[str, Any]:
    source = json.loads((CONTRACTS_DIR / _contract()["nestedSourceContract"]).read_bytes())
    contexts = source.get("nestedContexts")
    if (
        source.get("schemaVersion") != 1
        or source.get("anonymousReadOrder", {}).get("member8") != [
            "byte", "scalar32", "scalar32", "scalar32", "byte-payload",
            "counted-paired-payloads", "scalar32", "query-profile",
        ]
        or source.get("anonymousReadOrder", {}).get("member3")
        != ["byte-payload", "byte", "byte-payload"]
        or not isinstance(contexts, list)
        or tuple(row.get("typeName") for row in contexts) != NESTED_TYPES
    ):
        raise ValueError(f"{LABEL}.contract:nested-source-shape")
    return source


def _validate_nested_context(image: Any, row: dict[str, Any]) -> None:
    cell, usage = image.nested_usage_cell(row, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != row["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:method-spec-index")
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    if list(spec) != row["methodSpec"]:
        raise ValueError(f"{LABEL}.native:method-spec-record")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:generic-arity")
    raw = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
    if raw.hex().upper() != row["argumentRawHex"] or raw[10] != row["typeKind"]:
        raise ValueError(f"{LABEL}.native:generic-type")
    generic = row["generic"]
    if generic is None:
        definition = struct.unpack_from("<Q", raw)[0]
        if definition != row["typeDefinition"] or image.type_name(definition) != row["typeName"]:
            raise ValueError(f"{LABEL}.native:nested-direct-type")
        return
    pointer = struct.unpack_from("<Q", raw)[0]
    carrier = image.pe.bytes_at_va(pointer, 32)
    base_pointer = struct.unpack_from("<Q", carrier)[0]
    base = image.pe.bytes_at_va(base_pointer, 16)
    if (
        carrier.hex().upper() != generic["carrierRawHex"]
        or base.hex().upper() != generic["baseRawHex"]
        or struct.unpack_from("<Q", base)[0] != row["typeDefinition"]
        or image.type_name(row["typeDefinition"]) != row["typeName"]
    ):
        raise ValueError(f"{LABEL}.native:nested-list-carrier")
    element_pointer = struct.unpack_from("<Q", carrier, 8)[0]
    element_instance = image.instantiations.resolve_pointer(element_pointer)
    if (
        element_instance.index != generic["elementInstantiationIndex"]
        or [argument.raw_type_record_hex for argument in element_instance.arguments]
        != generic["elementArguments"]
    ):
        raise ValueError(f"{LABEL}.native:nested-list-element")


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate selected dispatch, ordered reads, and nested type sources."""
    contract = _contract()
    source = _nested_source()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
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
    image.check_windows(source["codeWindows"], label=f"{LABEL}.nested")
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
    for context in source["nestedContexts"]:
        _validate_nested_context(image, context)
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
        "nestedContextCount": len(NESTED_TYPES),
    }


def decode_check_buff_id_context_advanced_action(
    reader: Reader, depth: int, tag: int, width: int,
) -> None:
    """Consume the selected eight-member action and its bounded child records."""
    del depth
    _contract()
    _nested_source()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(FIELD_NAMES))
    reader.take(1, "CheckBuffIdInContextAdvanced.bool-byte")
    for _ in range(3):
        reader.take(4, "CheckBuffIdInContextAdvanced.scalar32")
    reader.byte_payload()
    for _ in range(max(0, reader.count(1, reserve=5, nullable=True))):
        reader.paired_payload()
    reader.take(4, "CheckBuffIdInContextAdvanced.scalar32")
    reader.query_profile()
