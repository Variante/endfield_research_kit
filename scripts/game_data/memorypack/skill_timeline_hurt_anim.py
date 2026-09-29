"""Selected-build SkillData HurtAnimAction 0x00C8 stored-source reader.

The ten-member wrapper ends in a finite TargetSettings child. The stored
fields do not establish a live animation or target selection.
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


LABEL = "skillTimelineHurtAnim"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_hurt_anim_native.json"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "blendDuration", "hurtType", "maxWeight", "speed", "startFrame", "target",
)
READ_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32", "float32-bits",
    "scalar32", "float32-bits", "float32-bits", "scalar32", "target-profile",
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-hurt-anim-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("nestedContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != 0x00C8
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list) or len(contexts) != 1
        or contexts[0].get("memberIndex") != 9
        or contexts[0].get("typeName") != "Beyond.Gameplay.Core.TargetSettings"
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or contract.get("targetReadContract") != "buff_ec_native.json"
        or len(contract.get("methods", [])) != 2
        or len(contract.get("codeWindows", [])) != 2
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate selected native inputs, action reads and target context."""
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
    reads = contract["orderedSourceReads"]
    targets = {row["sourceTargetRva"] for row in reads[:9]}
    primitive_windows = [row for row in primitive.get("codeWindows", [])
                         if row.get("startRva") in targets]
    if (
        primitive.get("schemaVersion") != 1 or target.get("schemaVersion") != 1
        or targets != {row["startRva"] for row in primitive_windows}
        or len(primitive_windows) != 3
        or not target.get("codeWindows")
        or reads[9]["sourceTargetRva"] == reads[8]["sourceTargetRva"]
    ):
        raise ValueError(f"{LABEL}.native:dependency-source-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(
        contract["codeWindows"] + primitive_windows + target["codeWindows"], label=LABEL,
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
    context = contract["nestedContexts"][0]
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
    tag = contract["dispatcher"]["unionTag"]
    selected = routes.get(tag, {})
    definition = selected.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated" or audit.get("routeAudit") != "validated"
        or selected.get("status") != "determined"
        or selected.get("wrapperName") != contract["dispatcher"]["wrapperName"]
        or definition != contract["dispatcher"]["wrapperTypeDefinition"]
        or not isinstance(plan, tuple) or len(plan) != len(FIELD_NAMES)
        or [member.name for member in plan] != list(FIELD_NAMES)
        or [member.width for member in plan[:9]] != [1, 4, 4, 4, 4, 4, 4, 4, 4]
        or plan[9].kind != "object" or plan[9].ref not in resolver.wrappers
        or resolver.wrappers[plan[9].ref].wrapped_type
        != "Beyond.Gameplay.Core.TargetSettings"
    ):
        raise ValueError(f"{LABEL}.native:generated-plan-drift")
    return {"status": "validated", "nativeInputs": expected,
            "unionTag": tag, "methodIndices": methods,
            "sourceReadCount": len(reads), "nestedContextCount": 1}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 1 or reader.data[reader.pos:reader.pos + width] != b"\xC8":
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(1, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(len(READ_KINDS))
    fields = []
    for name, kind in zip(FIELD_NAMES, READ_KINDS):
        field_start = reader.pos
        if kind == "bool-byte":
            reader.take(1, name)
        elif kind in ("scalar32", "float32-bits"):
            reader.take(4, name)
        elif kind == "target-profile":
            reader.target_profile()
        else:
            raise AssertionError(kind)
        fields.append({"name": name, "kind": kind, "start": field_start,
                       "end": reader.pos})
    return {"status": "exact-stored-action-span", "start": start,
            "end": reader.pos, "tag": _contract()["dispatcher"]["unionTag"],
            "fields": fields, "evidenceBoundary": "stored framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation.get("status") != "validated" or validation.get("unionTag") != 0x00C8:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 2 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 1)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Read the shared action after the composite native gate validates."""
    del depth
    if tag != 0x00C8:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
