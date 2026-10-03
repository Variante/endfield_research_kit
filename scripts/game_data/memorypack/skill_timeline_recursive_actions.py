"""Stored RepeatAction and SetMultiTimesWeakness readers.

The two native routes compose independently reviewed Int, Double and sequence
children. Double's scalar occupies four wire bytes. Lists retain null/empty
states and each child's own framing; runtime repetition and weakness effects
are outside this stored-format evidence.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import (
    generic_type_carrier,
    method_spec_record, method_spec_usage_index,
)
from scripts.game_data.il2cpp.context_audit_memorypack import (
    buff_action_read_order, buff_sequence_read_order, nested_reader_context,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR

LABEL = "skillTimelineRecursiveActions"
SCHEMA = "endfield.skill-timeline-recursive-actions-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_recursive_actions_native.json"
FIELD_NAMES = {
    0x012E: ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
             "key", "outputIndexToBlackBoard", "repeatCount", "sequenceActionData"),
    0x0155: ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
             "alertEffectDuration", "alertEffectScaleList", "canConvertToInterruptibleWeakness",
             "triggerActions", "triggerWeaknessCount", "useWeakerTriggerEffect", "whiteAlertEffectDuration"),
}
READ_KINDS = {
    0x012E: ("bool-byte", "enum32", "scalar32", "scalar32", "byte-payload",
             "bool-byte", "blackboard-int", "sequence-profile"),
    0x0155: ("bool-byte", "enum32", "scalar32", "scalar32", "blackboard-double",
             "nullable-list-blackboard-double", "bool-byte", "sequence-profile",
             "blackboard-int", "bool-byte", "blackboard-double"),
}
CHILD_TYPES = {
    "blackboard-int": "Beyond.Blackboard+BlackboardInt",
    "blackboard-double": "Beyond.Blackboard+BlackboardDouble",
    "sequence-profile": "Beyond.Gameplay.Core.SequenceActionData",
    "nullable-list-blackboard-double": "System.Collections.Generic.List`1<Beyond.Blackboard+BlackboardDouble>",
}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, label=LABEL,
                                         status="exact-current-build")
    routes = contract.get("routes", [])
    if (len(routes) != len(READ_KINDS)
            or {r.get("tag") for r in routes} != {f"0x{t:04X}" for t in READ_KINDS}
            or contract.get("catalogContract") != "levelscript_union_tags.json"
            or contract.get("primitiveReadContract") != "skill_timeline_do_once_native.json"
            or contract.get("stringReadContract") != "skill_timeline_log_action_native.json"
            or contract.get("childContracts") != ["buff_16b_native.json", "buff_ec_native.json", "buff_b4_native.json"]
            or contract.get("sequenceContract") != "il2cpp_context_audit_native.json"):
        raise ValueError(f"{LABEL}.contract:routes-or-dependencies")
    for route in routes:
        tag = int(route["tag"], 16)
        reads = route.get("orderedSourceReads", [])
        count = len(READ_KINDS[tag])
        nested = [i for i, kind in enumerate(READ_KINDS[tag]) if kind in CHILD_TYPES]
        if (route.get("serializedMemberCount") != count
                or route.get("dispatcher", {}).get("unionTag") != tag
                or [r.get("memberIndex") for r in reads] != list(range(count))
                or tuple(r.get("fieldName") for r in reads) != FIELD_NAMES[tag]
                or tuple(r.get("readKind") for r in reads) != READ_KINDS[tag]
                or [r.get("memberIndex") for r in route.get("nestedContexts", [])] != nested
                or [r.get("memberIndex") for r in route.get("setterCallsites", [])] != list(range(4, count))
                or [r.get("methodIndex") for r in route["setterCallsites"]]
                != [r[0] for r in route.get("setterMethods", [])]
                or bytes.fromhex(route.get("memberCountInstruction", {}).get("hex", ""))[-1:] != bytes((count,))):
            raise ValueError(f"{LABEL}.contract:source-shape:{tag:#x}")
    return contract


def _call(image: Any, rva: int, raw_hex: str, target: int, *, jump: bool = False) -> None:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if (raw[0] != (0xE9 if jump else 0xE8) or raw.hex().upper() != raw_hex.upper()
            or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target):
        raise ValueError(f"{LABEL}.native:call={rva:#x}")


def _context(image: Any, row: dict[str, Any], expected_type: str) -> None:
    cell, usage = image.nested_usage_cell(row, label=LABEL)
    reg, pe, metadata = image.registration, image.pe, image.metadata
    index = method_spec_usage_index(usage, reg["methodSpecsCount"], source=LABEL, offset=cell)
    address = int(reg["methodSpecs"], 16) + index * 12
    spec = method_spec_record(pe.bytes_at_va(address, 12), len(metadata.methods),
                              reg["genericInstsCount"], source=LABEL, offset=address)
    method = metadata.methods[spec[0]]
    expected_method = "ReadPackable" if expected_type.startswith("System.Collections.Generic.List") else "ReadValue"
    if (index != row["methodSpecIndex"] or list(spec) != row["methodSpec"] or spec[1] != -1
            or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
            or metadata.string(method.name_index) != expected_method):
        raise ValueError(f"{LABEL}.native:child-method-spec")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:child-arity")
    argument = instance.arguments[0]
    proof = row["arguments"][0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if (raw.hex().upper() != proof["raw"].upper()
            or runtime_type_name(pe, metadata, argument.type_pointer_va) != expected_type):
        raise ValueError(f"{LABEL}.native:child-type")
    if expected_method == "ReadPackable":
        pointer = struct.unpack_from("<Q", raw)[0]
        carrier_raw = pe.bytes_at_va(pointer, 32)
        base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
        carrier = generic_type_carrier(raw, carrier_raw, pe.bytes_at_va(base_pointer, 16),
            type_pointer=argument.type_pointer_va, type_count=len(metadata.types), source=LABEL)
        nested = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
        nested_identity = nested.as_dict()
        nested_identity["arguments"] = list(nested_identity["arguments"])
        if (carrier != proof["carrier"] or nested_identity != proof["nested"]
                or len(nested.arguments) != 1
                or runtime_type_name(pe, metadata, nested.arguments[0].type_pointer_va)
                != CHILD_TYPES["blackboard-double"]):
            raise ValueError(f"{LABEL}.native:list-element")


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict[str, Any]:
    """Authenticate both routes and reused children against selected native files."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
                                        gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    primitive = json.loads((CONTRACTS_DIR / contract["primitiveReadContract"]).read_bytes())
    strings = json.loads((CONTRACTS_DIR / contract["stringReadContract"]).read_bytes())
    context_contract = json.loads((CONTRACTS_DIR / contract["sequenceContract"]).read_bytes())
    if (primitive["nativeInputs"] != expected or strings["nativeInputs"] != expected
            or context_contract["nativeInputs"] != expected
            or catalog["nativeInputs"]["gameAssemblySha256"] != expected["GameAssembly.dll"]
            or catalog["nativeInputs"]["metadataSha256"] != expected["global-metadata.dat"]):
        raise ValueError(f"{LABEL}.native:dependency-inputs")
    image.check_windows(primitive["codeWindows"], label=LABEL)
    image.check_windows(strings["codeWindows"], label=LABEL)
    for name in contract["childContracts"]:
        buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
            image.modules, image.owners, source=str(gate.gameassembly), contract_path=CONTRACTS_DIR / name)
    sequence = buff_sequence_read_order(image.pe, image.metadata, image.modules, image.owners,
                                       source=str(gate.gameassembly))
    image.check_windows([sequence["rootCodeWindow"]], label=LABEL)
    # These direct shared consumers are not closed-type generic code-table
    # entries. Reuse their reviewed context propagation and caller targets;
    # never turn an absent code candidate into an invented provider selection.
    nested_reader_context(image.pe, image.metadata, image.modules, image.owners,
        image.registration, image.instantiations, source=str(gate.gameassembly),
        metadata_source=str(gate.metadata))
    shared_targets = context_contract["pins"]["selectedSkillDataReaderOrder"]
    summaries = []
    for route in contract["routes"]:
        tag = int(route["tag"], 16)
        selected = catalog["families"]["AbilityActionData"][tag]
        if (selected["tag"] != tag or selected["wrappedType"] != route["typeName"]
                or selected["wrapperName"] != route["dispatcher"]["wrapperName"]
                or selected["memberCount"] != route["serializedMemberCount"]):
            raise ValueError(f"{LABEL}.native:catalog-route:{tag:#x}")
        image.validate_dispatcher(route["dispatcher"], label=LABEL)
        for method in route["methods"]:
            image.validate_method_row(method, label=LABEL)
        image.check_windows(route["codeWindows"], label=LABEL)
        count = route["memberCountInstruction"]
        image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
        owner = image.metadata.types[route["dispatcher"]["wrapperTypeDefinition"]]
        if image.setter_methods(owner, parameter="typeName", label=LABEL) != route["setterMethods"]:
            raise ValueError(f"{LABEL}.native:setter-order:{tag:#x}")
        forward = route["formatterForwarding"]
        if forward["targetRva"] != route["methods"][0][3]:
            raise ValueError(f"{LABEL}.native:formatter-target")
        _call(image, forward["rva"], forward["hex"], forward["targetRva"], jump=True)
        previous = count["rva"]
        for read in route["orderedSourceReads"]:
            rva, target = read["sourceCallsiteRva"], read["sourceTargetRva"]
            if not previous < rva or not any(w["startRva"] <= rva and rva + 5 <= w["endRva"] for w in route["codeWindows"]):
                raise ValueError(f"{LABEL}.native:source-order:{tag:#x}")
            previous = rva
            _call(image, rva, read["sourceCallHex"], target)
            kind = read["readKind"]
            if kind == "bool-byte" and target != primitive["orderedSourceReads"][0]["sourceTargetRva"]:
                raise ValueError(f"{LABEL}.native:byte-helper")
            if kind in ("enum32", "scalar32") and target != primitive["orderedSourceReads"][1]["sourceTargetRva"]:
                raise ValueError(f"{LABEL}.native:scalar-helper")
            if kind == "byte-payload" and target != next(r["sourceTargetRva"] for r in strings["orderedSourceReads"] if r["readKind"] == kind):
                raise ValueError(f"{LABEL}.native:payload-helper")
        for setter in route["setterCallsites"]:
            index = setter["memberIndex"]
            following = route["orderedSourceReads"][index + 1]["sourceCallsiteRva"] if index + 1 < len(route["orderedSourceReads"]) else max(w["endRva"] for w in route["codeWindows"])
            if not route["orderedSourceReads"][index]["sourceCallsiteRva"] < setter["callsiteRva"] < following:
                raise ValueError(f"{LABEL}.native:setter-source-order")
            _call(image, setter["callsiteRva"], setter["callHex"], setter["targetRva"])
            if image.method_pointer_va(image.metadata.methods[setter["methodIndex"]]) != image.pe.image_base + setter["targetRva"]:
                raise ValueError(f"{LABEL}.native:setter-target")
        for context in route["nestedContexts"]:
            read = route["orderedSourceReads"][context["memberIndex"]]
            if not context["instructionRva"] < read["sourceCallsiteRva"]:
                raise ValueError(f"{LABEL}.native:context-order")
            target_key = "readPackableTargetRva" if read["readKind"] == "nullable-list-blackboard-double" else "readValueTargetRva"
            if read["sourceTargetRva"] != int(shared_targets[target_key], 16):
                raise ValueError(f"{LABEL}.native:shared-reader-target")
            _context(image, context, CHILD_TYPES[read["readKind"]])
        summaries.append({"tag": route["tag"], "sourceReadCount": len(route["orderedSourceReads"]),
                          "nestedContextCount": len(route["nestedContexts"])})
    return {"status": "validated", "nativeInputs": expected, "routes": summaries}


def decode_recursive_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Read one reviewed extended action; enclosing sequence owns its union record."""
    _contract()
    if tag not in READ_KINDS or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS[tag]))
    for field, kind in zip(FIELD_NAMES[tag], READ_KINDS[tag]):
        if kind == "sequence-profile":
            reader.sequence(depth)
        elif kind in ("blackboard-int", "blackboard-double"):
            reader.scalar_payload()
        elif kind == "nullable-list-blackboard-double":
            # Remaining flag/sequence/Int/flag/Double each requires >=1 byte.
            for _ in range(max(0, reader.count(1, reserve=5, nullable=True))):
                reader.scalar_payload()
        elif kind == "byte-payload":
            reader.byte_payload()
        else:
            reader.take(1 if kind == "bool-byte" else 4, f"{field}.{kind}")
