"""Selected-build SkillData TryToTeleportSquadAction 0x018C stored reader.

Its inherited four fields close one action only. Later actions in the Wulfa
ultimate source remain separate first stops.
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


LABEL = "skillTimelineTryTeleportSquad"
TAG = 0x018C
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_try_teleport_squad_native.json"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_TryToTeleportSquadAction_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.TryToTeleportSquadAction+Data"
FIELD_NAMES = ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex")
READ_KINDS = ("bool-byte", "enum32", "scalar32", "scalar32")
PLAN = (
    ("isEnable", "fixed", 1, "bool"),
    ("priorityLevel", "fixed", 4, "scalar32"),
    ("priorityOffset", "fixed", 4, "scalar32"),
    ("serverActionIndex", "fixed", 4, "scalar32"),
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-try-teleport-squad-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or contract.get("setterMethods") != []
        or not isinstance(contexts, list) or len(contexts) != 1
        or contexts[0].get("memberIndex") != 1
        or contexts[0].get("typeName")
        != "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority"
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or len(contract.get("methods", [])) != 2
        or len(contract.get("codeWindows", [])) != 2
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7C\x24\x38\x04"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate selected dispatcher, source calls and Priority context."""
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
    header_call = contract["memberHeaderSourceCall"]
    targets = {row["sourceTargetRva"] for row in contract["orderedSourceReads"]}
    targets.add(header_call["sourceTargetRva"])
    primitive_windows = [row for row in primitive.get("codeWindows", [])
                         if row.get("startRva") in targets]
    if (
        primitive.get("schemaVersion") != 1
        or targets != {row["startRva"] for row in primitive_windows}
        or len(primitive_windows) != 3
    ):
        raise ValueError(f"{LABEL}.native:primitive-source-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"] + primitive_windows, label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    header_rva = header_call["sourceCallsiteRva"]
    header_raw = image.pe.bytes_at_va(image.pe.image_base + header_rva, 5)
    if (
        not contract["codeWindows"][0]["startRva"] <= header_rva
        < contract["codeWindows"][0]["endRva"] - 4
        or header_raw[0] != 0xE8
        or header_raw.hex().upper() != header_call["sourceCallHex"]
        or header_rva + 5 + struct.unpack_from("<i", header_raw, 1)[0]
        != header_call["sourceTargetRva"]
    ):
        raise ValueError(f"{LABEL}.native:member-header-source")
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != []:
        raise ValueError(f"{LABEL}.native:setter-order")
    previous = -1
    reader_window = contract["codeWindows"][0]
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if not reader_window["startRva"] <= rva < reader_window["endRva"] - 4 or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    context = contract["genericContexts"][0]
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
        raise ValueError(f"{LABEL}.native:generic-type")
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    route = routes.get(TAG, {})
    definition = route.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    wrapper = resolver.wrappers.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated" or audit.get("routeAudit") != "validated"
        or route.get("status") != "determined"
        or route.get("evidenceTier") != "direct"
        or route.get("wrapperName") != WRAPPER_NAME
        or wrapper is None or wrapper.wrapped_type != TYPE_NAME
        or not isinstance(plan, tuple)
        or tuple((member.name, member.kind, member.width, member.scalar)
                 for member in plan) != PLAN
    ):
        raise ValueError(f"{LABEL}.native:generated-plan-drift")
    return {"status": "validated", "unionTag": TAG, "nativeInputs": expected,
            "methodIndices": methods, "sourceReadCount": len(READ_KINDS)}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 3 or reader.data[reader.pos:reader.pos + width] != b"\xFA\x8C\x01":
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(len(FIELD_NAMES))
    fields = []
    for index, (name, kind) in enumerate(zip(FIELD_NAMES, READ_KINDS)):
        field_start = reader.pos
        reader.take(1 if index == 0 else 4, name)
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
    del depth
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
