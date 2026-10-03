"""Reuse the selected CheckPartTagMatch source grammar in Skill timelines.

The existing reviewed residual-action contract owns the dispatcher, source
windows and typed nested reads. This consumer accepts its six-member source
order only after checking the selected native image. TargetSettings and
GameplayTagQuery keep their existing bounded child grammars. Stored targets
and tag queries establish no executed condition or resolved result.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_schema import resolve_routes

LABEL = "skillTimelineCheckPartTagMatch"
TAG = 0x006C
CONTRACT_PATH = CONTRACTS_DIR / "buff_residual_actions_native.json"
SCHEMA = "endfield.buff-residual-action-native-contract.v1"
TYPE_NAME = "Beyond.Gameplay.Core.Conditions.CheckPartTagMatch+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Conditions_CheckPartTagMatch_DataForMemoryPack"
READ_KINDS = ("byte", "scalar32", "scalar32", "scalar32", "target-settings", "gameplay-tag-query")
FIELD_NAMES = ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex", "checkTarget", "query")
CHILD_TYPES = ("Beyond.Gameplay.Core.TargetSettings", "Beyond.Gameplay.Core.GameplayTagQuery")


def _contract() -> tuple[dict[str, Any], dict[str, Any]]:
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
                                         status="exact-current-build", label=LABEL)
    selected = [row for row in contract.get("actions", ()) if row.get("unionTag") == TAG]
    if len(selected) != 1:
        raise ValueError(f"{LABEL}.contract:unique-route")
    route = selected[0]
    if (route.get("serializedMemberCount") != len(READ_KINDS)
            or route.get("wrapperName") != WRAPPER_NAME
            or tuple(route.get("readOrder", ())) != READ_KINDS
            or tuple(route.get("generatedOwnFields", ())) != FIELD_NAMES[4:]
            or [row.get("profile") for row in route.get("nestedContextUsage", ())]
            != list(READ_KINDS[4:])
            or len(route.get("methods", ())) != 2 or not route.get("codeWindows")):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract, route


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Check the selected route, complete source windows and nested identities."""
    contract, route = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
                                        gameassembly=gameassembly, metadata=metadata)
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing")
    with unity.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest().upper() != expected["UnityPlayer.dll"]:
            raise ValueError(f"{LABEL}.native:UnityPlayer.dll:mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(route, label=LABEL)
    for method in route["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(route["codeWindows"], label=LABEL)
    for context, type_name, type_kind in zip(route["nestedContextUsage"], CHILD_TYPES, (0x12, 0x11)):
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell)
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
                                  image.registration["genericInstsCount"], source=LABEL, offset=address)
        arguments = image.instantiations.resolve(spec[2]).arguments
        if len(arguments) != 1:
            raise ValueError(f"{LABEL}.native:nested-arity")
        raw = bytes.fromhex(arguments[0].raw_type_record_hex)
        if raw[10] != type_kind or image.type_name(struct.unpack_from("<Q", raw)[0]) != type_name:
            raise ValueError(f"{LABEL}.native:nested-type:{context['profile']}")
    for name in ("buff_ec_native.json", "buff_b4_native.json"):
        buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
                               image.modules, image.owners, source=str(gate.gameassembly),
                               contract_path=CONTRACTS_DIR / name)
    routes, resolver, audit = resolve_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    selected = routes.get(TAG, {})
    definition = selected.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    if (audit.get("status") != "validated" or selected.get("status") != "determined"
            or selected.get("wrapperName") != WRAPPER_NAME
            or definition != route["wrapperTypeDefinition"] or not isinstance(plan, tuple)
            or tuple(member.name for member in plan) != FIELD_NAMES
            or resolver.wrappers[definition].wrapped_type != TYPE_NAME):
        raise ValueError(f"{LABEL}.native:generated-plan")
    for index, member in enumerate(plan):
        if index < 4:
            if member.kind != "fixed" or member.width != (1 if index == 0 else 4):
                raise ValueError(f"{LABEL}.native:primitive-width:{index}")
        elif (member.kind != "object" or member.ref not in resolver.wrappers
              or resolver.wrappers[member.ref].wrapped_type != CHILD_TYPES[index - 4]):
            raise ValueError(f"{LABEL}.native:child-plan:{index}")
    return {"status": "validated", "unionTag": TAG, "sourceReadCount": len(READ_KINDS),
            "nativeInputs": expected, "evidenceBoundary": "Selected stored source grammar; no runtime condition result."}


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, FIELD_NAMES[0])
    for name in FIELD_NAMES[1:4]:
        reader.take(4, name)
    reader.target_profile()
    reader.query_profile()
