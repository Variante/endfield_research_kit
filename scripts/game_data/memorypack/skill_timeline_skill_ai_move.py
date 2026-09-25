"""Selected-build SkillData SkillAIMoveAction 0x0165 reader.

The selected source reads markerInfo as an eight-byte unmanaged copy. Its
separate wrapper is not invoked on this path, so those bytes stay opaque.
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


LABEL = "skillTimelineSkillAIMove"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_skill_ai_move_native.json"
TAG = 0x0165
SECTION_SHAPES = {
    "action": (
        ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
         "mainCharLineBlockHalfAngle", "markerInfo", "maxRange", "minRange",
         "moveInnerDist", "moveOuterDist", "otherTargetMinDist", "radius",
         "skillMoveTargetType", "skillRadius", "targetRefreshInterval", "targetSettings"),
        ("bool-byte", "enum32", "scalar32", "scalar32", "float32-bits",
         "unmanaged8", "float32-bits", "float32-bits", "float32-bits",
         "float32-bits", "float32-bits", "float32-bits", "enum32",
         "float32-bits", "float32-bits", "target-profile"),
        (1, 5, 12, 15),
        ("Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
         "Beyond.Gameplay.AI.EnemyCheckAIMarker+EnemyCheckAIMarkerInfo",
         "Beyond.Gameplay.AI.SkillMoveTargetType",
         "Beyond.Gameplay.Core.TargetSettings"),
    ),
}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-skill-ai-move-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    sections = contract.get("sections")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or not isinstance(sections, dict)
        or set(sections) != set(SECTION_SHAPES)
        or [row.get("path") for row in contract.get("dependencies", ())]
        != ["buff_ec_native.json"]
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    for key, (names, kinds, nested_members, nested_types) in SECTION_SHAPES.items():
        section = sections[key]
        reads = section.get("orderedSourceReads")
        contexts = section.get("genericContexts")
        setters = section.get("setterMethods")
        if (
            section.get("serializedMemberCount") != len(names)
            or not isinstance(reads, list)
            or [row.get("memberIndex") for row in reads] != list(range(len(names)))
            or tuple(row.get("fieldName") for row in reads) != names
            or tuple(row.get("readKind") for row in reads) != kinds
            or not isinstance(contexts, list)
            or tuple(row.get("memberIndex") for row in contexts) != nested_members
            or tuple(row.get("typeName") for row in contexts) != nested_types
            or not isinstance(setters, list)
        ):
            raise ValueError(f"{LABEL}.contract:{key}:source-shape")
    if sections["action"]["wrapperTypeDefinition"] != contract["dispatcher"]["wrapperTypeDefinition"]:
        raise ValueError(f"{LABEL}.contract:route-wrapper")
    copy = contract.get("unmanagedCopy")
    if (
        not isinstance(copy, dict)
        or copy.get("byteCount") != 8
        or copy.get("sourceTargetRva") != sections["action"]["orderedSourceReads"][5]["sourceTargetRva"]
        or len(copy.get("sizeInstructions", ())) != 3
        or [row.get("hex") for row in copy["sizeInstructions"]]
        != ["83793008", "BA08000000", "BA08000000"]
    ):
        raise ValueError(f"{LABEL}.contract:unmanaged-copy-shape")
    return contract


def _validate_section(image: Any, key: str, section: dict[str, Any]) -> list[int]:
    label = f"{LABEL}.{key}"
    methods = [image.validate_method_row(row, label=label) for row in section["methods"]]
    image.check_windows(section["codeWindows"], label=label)
    instruction = section["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=label)
    owner = image.metadata.types[section["wrapperTypeDefinition"]]
    if image.type_name(section["wrapperTypeDefinition"]) != section["wrapperName"]:
        raise ValueError(f"{label}.native:wrapper-name")
    if image.setter_methods(owner, parameter="typeName", label=label) != section["setterMethods"]:
        raise ValueError(f"{label}.native:setter-order")
    previous = -1
    for read in section["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if rva <= previous:
            raise ValueError(f"{label}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{label}.native:source-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if target != read["sourceTargetRva"]:
            raise ValueError(f"{label}.native:source-target={rva:#x}")
    for context in section["genericContexts"]:
        cell, usage = image.nested_usage_cell(context, label=label)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=label, offset=cell,
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{label}.native:method-spec-index={context['memberIndex']}")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=label, offset=address,
        )
        if list(spec) != context["methodSpec"]:
            raise ValueError(f"{label}.native:method-spec-record={index}")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{label}.native:generic-arity={index}")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        if (
            argument.hex().upper() != context["argumentRawHex"]
            or argument[10] != context["typeKind"]
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{label}.native:generic-type={index}")
    return methods


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate selected dispatch and action/marker/tag source readers."""
    contract = _contract()
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
    methods = {
        key: _validate_section(image, key, section)
        for key, section in contract["sections"].items()
    }
    copy = contract["unmanagedCopy"]
    image.check_windows([copy["codeWindow"]], label=f"{LABEL}.unmanagedCopy")
    image.check_instruction_windows(
        [[row["rva"], row["hex"]] for row in copy["sizeInstructions"]],
        label=f"{LABEL}.unmanagedCopy",
    )
    dependency = json.loads((CONTRACTS_DIR / contract["dependencies"][0]["path"]).read_bytes())
    if dependency.get("schemaVersion") != 1:
        raise ValueError(f"{LABEL}.native:target-dependency-schema")
    image.check_windows(dependency["codeWindows"], label=f"{LABEL}.buff_ec_native")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods,
        "sourceReadCounts": {key: len(section["orderedSourceReads"]) for key, section in contract["sections"].items()},
        "genericContextCount": sum(len(section["genericContexts"]) for section in contract["sections"].values()),
    }


def _record(reader: Reader, key: str, depth: int) -> None:
    section = _contract()["sections"][key]
    start = reader.pos
    if reader.peek() == 0xFF:
        reader.take(1, f"{key}.null-wrapper")
        reader.records.append({"start": start, "end": reader.pos, "kind": key})
        return
    reader.header(section["serializedMemberCount"])
    for row in section["orderedSourceReads"]:
        kind = row["readKind"]
        field = row["fieldName"]
        if kind == "bool-byte":
            reader.take(1, f"{key}.{field}.byte")
        elif kind in ("enum32", "scalar32", "float32-bits"):
            reader.take(4, f"{key}.{field}.raw4")
        elif kind == "unmanaged8":
            reader.take(_contract()["unmanagedCopy"]["byteCount"], f"{key}.{field}.unmanaged8")
        elif kind == "target-profile":
            reader.target_profile()
        else:
            raise ValueError(f"{LABEL}.{key}.readKind:{kind}")
    reader.records.append({"start": start, "end": reader.pos, "kind": key})


def decode_skill_ai_move_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one selected sixteen-member AI move action and nested marker."""
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    _record(reader, "action", depth)
