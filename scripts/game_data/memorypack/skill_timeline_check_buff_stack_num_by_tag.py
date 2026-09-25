"""Selected-build SkillData CheckBuffStackNumByTag 0x0059 framing.

The nine stored members and their nested profiles are a byte-level claim.
They do not establish when a runtime condition evaluates true.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineCheckBuffStackNumByTag"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_check_buff_stack_num_by_tag_native.json"
TAG = 0x0059
TYPE_NAME = "Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Conditions_CheckBuffStackNumByTag_DataForMemoryPack"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "buffStackNumType", "checkTarget", "compareType", "tagQuery", "value",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "enum32",
    "target-profile", "enum32", "query-profile", "scalar-payload",
)
CONTEXT_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "Beyond.Gameplay.Core.BuffStackNumType",
    "Beyond.Gameplay.Core.TargetSettings",
    "Beyond.CompareType",
    "Beyond.Gameplay.Core.GameplayTagQuery",
    "Beyond.Blackboard+BlackboardDouble",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-check-buff-stack-num-by-tag-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or contract.get("nestedProfileContract") != "buff_b4_native.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 4, 5, 6, 7, 8]
        or tuple(row.get("typeName") for row in contexts) != CONTEXT_TYPES
        or not isinstance(setters, list)
        or [row[1:] for row in setters] != [
            ["set___buffStackNumType__", CONTEXT_TYPES[1]],
            ["set___checkTarget__", CONTEXT_TYPES[2]],
            ["set___compareType__", CONTEXT_TYPES[3]],
            ["set___tagQuery__", CONTEXT_TYPES[4]],
            ["set___value__", CONTEXT_TYPES[5]],
        ]
        or not isinstance(setter_calls, list)
        or [row.get("memberIndex") for row in setter_calls] != [4, 5, 6, 8]
        or [row.get("methodIndex") for row in setter_calls]
        != [setters[index][0] for index in (0, 1, 2, 4)]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xfe\x09"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _contract()
    nested = json.loads((CONTRACTS_DIR / contract["nestedProfileContract"]).read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    orders = nested.get("anonymousReadOrder", {})
    if (
        nested.get("schemaVersion") != 1
        or "target-profile" not in orders.get("member13", [])
        or "scalar-payload" not in orders.get("member13", [])
        or tuple(orders.get("query-profile", ())) != ("scalar32", "counted-scalar32")
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("wrappedType") != TYPE_NAME
        or route.get("wrapperName") != WRAPPER_NAME
        or route.get("memberCount") != len(FIELD_NAMES)
        or catalog.get("switches", {}).get("AbilityActionData", {}).get("entryCount")
        != len(catalog["families"]["AbilityActionData"])
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    return nested, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate dispatch, source calls, nested types and bounded codecs."""
    contract = _contract()
    nested, catalog = _dependencies()
    expected = contract["nativeInputs"]
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-inputs")
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
    if (
        int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    image.check_windows([contract["directQueryStoreWindow"]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    previous = -1
    source_window = contract["codeWindows"][1]
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if not source_window["startRva"] <= rva < source_window["endRva"] or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    for setter in contract["setterCallsites"]:
        rva = setter["callsiteRva"]
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        method = image.metadata.methods[setter["methodIndex"]]
        if (
            raw[0] != 0xE8
            or raw.hex().upper() != setter["callHex"]
            or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != setter["targetRva"]
            or image.method_pointer_va(method) != image.pe.image_base + setter["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter-call={rva:#x}")
    for context in contract["genericContexts"]:
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
        if (
            argument.hex().upper() != context["argumentRawHex"]
            or argument[10] != context["typeKind"]
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type")
    nested_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["nestedProfileContract"],
    )
    if (
        tuple(nested_audit["anonymousReadOrder"].get("query-profile", ()))
        != ("scalar32", "counted-scalar32")
        or len(nested.get("nestedContexts", [])) == 0
    ):
        raise ValueError(f"{LABEL}.native:nested-profile")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
        "genericContextCount": len(CONTEXT_TYPES),
    }


def decode_check_buff_stack_num_by_tag_action(
    reader: Reader, depth: int, tag: int, width: int,
) -> None:
    """Consume one reached action with bounded target, query and scalar child."""
    del depth
    _contract()
    _dependencies()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, "CheckBuffStackNumByTag.isEnable.byte")
    for field in FIELD_NAMES[1:5]:
        reader.take(4, f"CheckBuffStackNumByTag.{field}.raw4")
    reader.target_profile()
    reader.take(4, "CheckBuffStackNumByTag.compareType.raw4")
    reader.query_profile()
    reader.scalar_payload()
