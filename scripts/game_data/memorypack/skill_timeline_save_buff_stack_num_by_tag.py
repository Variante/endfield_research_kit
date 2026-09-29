"""Selected-build SkillData SaveBuffStackNumByTag 0x0137 stored reader.

The eight fields close stored framing only. Neither a buff stack nor a live
target is inferred from their values.
"""
from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillTimelineSaveBuffStackNumByTag"
TAG = 0x0137
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_save_buff_stack_num_by_tag_native.json"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "buffStackNumType", "checkTarget", "key", "tagQuery",
)
READ_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32", "scalar32",
    "target-profile", "byte-payload", "query-profile",
)
CONTEXT_TYPES = (
    "Beyond.Gameplay.Core.TargetSettings",
    "Beyond.Gameplay.Core.GameplayTagQuery",
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-save-buff-stack-num-by-tag-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [5, 7]
        or tuple(row.get("typeName") for row in contexts) != CONTEXT_TYPES
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or contract.get("targetReadContract") != "buff_ec_native.json"
        or contract.get("queryReadContract") != "buff_b4_native.json"
        or len(contract.get("methods", [])) != 2
        or len(contract.get("codeWindows", [])) != 3
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate selected inputs, dispatcher, ordered calls and child types."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (not unityplayer.is_file()
            or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
            != expected["UnityPlayer.dll"]):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    primitive = json.loads((CONTRACTS_DIR / contract["primitiveReadContract"]).read_bytes())
    target = json.loads((CONTRACTS_DIR / contract["targetReadContract"]).read_bytes())
    query = json.loads((CONTRACTS_DIR / contract["queryReadContract"]).read_bytes())
    reads = contract["orderedSourceReads"]
    primitive_targets = {row["sourceTargetRva"] for row in reads[:5]}
    primitive_targets.add(reads[6]["sourceTargetRva"])
    primitive_windows = [row for row in primitive.get("codeWindows", [])
                         if row.get("startRva") in primitive_targets]
    query_windows = [row for row in query.get("codeWindows", [])
                     if row.get("boundary", "").startswith("query ")]
    if (
        primitive.get("schemaVersion") != 1
        or target.get("schemaVersion") != 1
        or query.get("schemaVersion") != 1
        or primitive_targets != {row["startRva"] for row in primitive_windows}
        or len(primitive_windows) != 3
        or not target.get("codeWindows")
        or len(query_windows) != 2
        or tuple(query.get("anonymousReadOrder", {}).get("query-profile", ()))
        != ("scalar32", "counted-scalar32")
        or reads[5]["sourceTargetRva"] == reads[7]["sourceTargetRva"]
        or reads[7]["sourceTargetRva"] != contract["codeWindows"][2]["startRva"]
    ):
        raise ValueError(f"{LABEL}.native:dependency-source-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(
        contract["codeWindows"] + primitive_windows + target["codeWindows"] + query_windows,
        label=LABEL,
    )
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    reader_window = contract["codeWindows"][0]
    previous = -1
    for read in reads:
        rva = read["sourceCallsiteRva"]
        if not reader_window["startRva"] <= rva < reader_window["endRva"] - 4 or rva <= previous:
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
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
        )
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        definition = struct.unpack_from("<Q", argument)[0]
        if (
            index != context["methodSpecIndex"] or list(spec) != context["methodSpec"]
            or argument.hex().upper() != context["argumentRawHex"]
            or argument[10] != context["typeKind"]
            or definition != context["typeDefinition"]
            or image.type_name(definition) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:nested-type")
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    selected = routes.get(TAG, {})
    definition = selected.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated" or audit.get("routeAudit") != "validated"
        or selected.get("status") != "determined"
        or selected.get("wrapperName") != contract["dispatcher"]["wrapperName"]
        or definition != contract["dispatcher"]["wrapperTypeDefinition"]
        or not isinstance(plan, tuple) or len(plan) != len(FIELD_NAMES)
        or [member.name for member in plan] != list(FIELD_NAMES)
        or [member.width for member in plan[:5]] != [1, 4, 4, 4, 4]
        or [plan[index].kind for index in (5, 7)] != ["object", "object"]
        or any(plan[index].ref not in resolver.wrappers for index in (5, 7))
        or tuple(resolver.wrappers[plan[index].ref].wrapped_type for index in (5, 7))
        != CONTEXT_TYPES
        or plan[6].kind != "string"
    ):
        raise ValueError(f"{LABEL}.native:generated-plan-drift")
    return {"status": "validated", "nativeInputs": expected,
            "unionTag": TAG, "methodIndices": methods,
            "sourceReadCount": len(reads), "nestedContextCount": len(CONTEXT_TYPES)}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 3 or reader.data[reader.pos:reader.pos + width] != b"\xFA\x37\x01":
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(len(READ_KINDS))
    fields = []
    for name, kind in zip(FIELD_NAMES, READ_KINDS):
        field_start = reader.pos
        if kind == "bool-byte":
            reader.take(1, name)
        elif kind == "scalar32":
            reader.take(4, name)
        elif kind == "target-profile":
            reader.target_profile()
        elif kind == "byte-payload":
            reader.byte_payload()
        elif kind == "query-profile":
            reader.query_profile()
        else:
            raise AssertionError(kind)
        fields.append({"name": name, "kind": kind, "start": field_start,
                       "end": reader.pos})
    return {"status": "exact-stored-action-span", "start": start,
            "end": reader.pos, "tag": TAG, "fields": fields,
            "evidenceBoundary": "stored framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation.get("status") != "validated" or validation.get("unionTag") != TAG:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 4 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 3)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Read one shared action after the composite native gate validates."""
    del depth
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
