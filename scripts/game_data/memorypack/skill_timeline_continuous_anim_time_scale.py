"""Selected-build SkillData ContinuousSetAnimTimeScale 0x008B reader.

The fifth stored member is a nullable BlackboardDouble. Its payload bits
are structural evidence; the action does not show a live animation clock.
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


LABEL = "skillTimelineContinuousAnimTimeScale"
TAG = 0x008B
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_continuous_anim_time_scale_native.json"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_ContinuousSetAnimTimeScale_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.ContinuousSetAnimTimeScale+Data"
FIELD_NAMES = ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
               "timeScale")
READ_KINDS = ("bool-byte", "enum32", "scalar32", "scalar32", "blackboard-double")
PLAN = (
    ("isEnable", "fixed", 1, "bool"),
    ("priorityLevel", "fixed", 4, "scalar32"),
    ("priorityOffset", "fixed", 4, "scalar32"),
    ("serverActionIndex", "fixed", 4, "scalar32"),
    ("timeScale", "object", None, None),
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-continuous-anim-time-scale-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(setters, list) or len(setters) != 1
        or setters[0][1] != "set___timeScale__"
        or not isinstance(setter_calls, list) or len(setter_calls) != 1
        or setter_calls[0].get("memberIndex") != 4
        or setter_calls[0].get("methodIndex") != setters[0][0]
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 4]
        or [row.get("typeName") for row in contexts] != [
            "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
            "Beyond.Blackboard+BlackboardDouble",
        ]
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or contract.get("blackboardReadContract") != "buff_ec_native.json"
        or len(contract.get("methods", [])) != 2
        or len(contract.get("codeWindows", [])) != 2
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7C\x24\x38" + bytes([len(FIELD_NAMES)])
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def _dependency_windows(image: Any, contract: Mapping[str, Any]) -> None:
    primitive = json.loads((CONTRACTS_DIR / contract["primitiveReadContract"]).read_bytes())
    targets = {row["sourceTargetRva"] for row in contract["orderedSourceReads"][:4]}
    targets.add(contract["memberHeaderSourceCall"]["sourceTargetRva"])
    windows = [row for row in primitive.get("codeWindows", [])
               if row.get("startRva") in targets]
    if (primitive.get("schemaVersion") != 1
            or targets != {row["startRva"] for row in windows}
            or len(windows) != 3):
        raise ValueError(f"{LABEL}.native:primitive-source-drift")
    image.check_windows(windows, label=LABEL)
    blackboard = json.loads((CONTRACTS_DIR / contract["blackboardReadContract"]).read_bytes())
    methods = [row for row in blackboard.get("methods", [])
               if "Beyond_Blackboard_BlackboardDoubleForMemoryPack" in row[1]
               and row[2] == "Deserialize"]
    windows = [row for row in blackboard.get("codeWindows", [])
               if any(row.get("startRva") == method[3] for method in methods)]
    if blackboard.get("schemaVersion") != 1 or len(methods) != 2 or len(windows) != 2:
        raise ValueError(f"{LABEL}.native:blackboard-source-drift")
    for method in methods:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(windows, label=LABEL)


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate selected dispatch, five source calls and Double context."""
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
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    _dependency_windows(image, contract)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    reader_window = contract["codeWindows"][0]
    calls = [contract["memberHeaderSourceCall"], *contract["orderedSourceReads"]]
    previous = -1
    for call in calls:
        rva = call["sourceCallsiteRva"]
        if not reader_window["startRva"] <= rva < reader_window["endRva"] - 4 or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != call["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != call["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    setter = contract["setterCallsites"][0]
    rva = setter["callsiteRva"]
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    method = image.metadata.methods[setter["methodIndex"]]
    if (
        not calls[-1]["sourceCallsiteRva"] < rva < reader_window["endRva"] - 4
        or raw[0] != 0xE8 or raw.hex().upper() != setter["callHex"]
        or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != setter["targetRva"]
        or image.method_pointer_va(method) != image.pe.image_base + setter["targetRva"]
    ):
        raise ValueError(f"{LABEL}.native:setter-call")
    for context in contract["genericContexts"]:
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
            raise ValueError(f"{LABEL}.native:generic-type={context['memberIndex']}")
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    route = routes.get(TAG, {})
    definition = route.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    wrapper = resolver.wrappers.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated" or audit.get("routeAudit") != "validated"
        or route.get("status") != "determined" or route.get("evidenceTier") != "direct"
        or route.get("wrapperName") != WRAPPER_NAME
        or wrapper is None or wrapper.wrapped_type != TYPE_NAME
        or not isinstance(plan, tuple)
        or tuple((member.name, member.kind, member.width, member.scalar)
                 for member in plan) != PLAN
        or plan[4].ref not in resolver.wrappers
        or resolver.wrappers[plan[4].ref].wrapped_type
        != "Beyond.Blackboard+BlackboardDouble"
    ):
        raise ValueError(f"{LABEL}.native:generated-plan-drift")
    return {"status": "validated", "unionTag": TAG, "nativeInputs": expected,
            "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
            "genericContextCount": len(contract["genericContexts"])}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 1 or reader.data[reader.pos:reader.pos + 1] != bytes([TAG]):
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(len(FIELD_NAMES))
    fields = []
    for index, name in enumerate(FIELD_NAMES):
        field_start = reader.pos
        if index == 0:
            reader.take(1, name)
        elif index < 4:
            reader.take(4, name)
        else:
            reader.scalar_payload()
        fields.append({"name": name, "kind": READ_KINDS[index],
                       "start": field_start, "end": reader.pos})
    return {"status": "exact-stored-action-span", "start": start,
            "end": reader.pos, "tag": TAG, "fields": fields,
            "evidenceBoundary": "stored framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation.get("status") != "validated" or validation.get("unionTag") != TAG:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 2 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 1)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    del depth
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
