"""Selected-build SkillData LogAction 0x00E5 stored-source reader.

Two bounded string payloads and eight scalars are authored bytes. Their
presence does not prove that logging or a subsequent action ran.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillTimelineLogAction"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_log_action_native.json"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "alwaysNext", "bbKey", "logBB", "logContext", "logStr", "returnValue",
)
READ_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32", "bool-byte",
    "byte-payload", "bool-byte", "bool-byte", "byte-payload", "bool-byte",
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-log-action-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    if (
        contract.get("dispatcher", {}).get("unionTag") != 0x00E5
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or len(contract.get("methods", [])) != 2
        or len(contract.get("codeWindows", [])) != 2
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate selected native inputs, route, ten calls and string reads."""
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
    reads = contract["orderedSourceReads"]
    targets = {row["sourceTargetRva"] for row in reads}
    windows = [row for row in primitive.get("codeWindows", [])
               if row.get("startRva") in targets]
    if (
        primitive.get("schemaVersion") != 1
        or targets != {row["startRva"] for row in windows}
        or len(windows) != 3
        or reads[5]["sourceTargetRva"] != reads[8]["sourceTargetRva"]
    ):
        raise ValueError(f"{LABEL}.native:primitive-source-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"] + windows, label=LABEL)
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
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    tag = contract["dispatcher"]["unionTag"]
    selected = routes.get(tag, {})
    definition = selected.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated" or audit.get("routeAudit") != "validated"
        or selected.get("status") != "determined" or selected.get("evidenceTier") != "direct"
        or selected.get("wrapperName") != contract["dispatcher"]["wrapperName"]
        or definition != contract["dispatcher"]["wrapperTypeDefinition"]
        or not isinstance(plan, tuple) or len(plan) != len(FIELD_NAMES)
        or [member.name for member in plan] != list(FIELD_NAMES)
        or [member.kind for member in plan] != [
            "fixed", "fixed", "fixed", "fixed", "fixed", "string",
            "fixed", "fixed", "string", "fixed",
        ]
        or [member.width for member in plan] != [1, 4, 4, 4, 1, None, 1, 1, None, 1]
    ):
        raise ValueError(f"{LABEL}.native:generated-plan-drift")
    return {"status": "validated", "nativeInputs": expected,
            "unionTag": tag, "methodIndices": methods,
            "sourceReadCount": len(reads)}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 1 or reader.data[reader.pos:reader.pos + width] != b"\xE5":
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
        elif kind == "scalar32":
            reader.take(4, name)
        elif kind == "byte-payload":
            reader.byte_payload()
        else:
            raise AssertionError(kind)
        fields.append({"name": name, "kind": kind, "start": field_start,
                       "end": reader.pos})
    return {"status": "exact-stored-action-span", "start": start,
            "end": reader.pos, "tag": _contract()["dispatcher"]["unionTag"],
            "fields": fields, "evidenceBoundary": "stored framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation.get("status") != "validated" or validation.get("unionTag") != 0x00E5:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 2 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 1)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Read the shared action after the composite native gate validates."""
    del depth
    if tag != 0x00E5:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
