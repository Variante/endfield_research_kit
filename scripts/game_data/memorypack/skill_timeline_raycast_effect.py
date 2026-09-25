"""Selected-build SkillData RayCastEffectAction 0x0121 source reader.

Five selected source readers pin the action and its four ray-data records.
Nested EffectActionCfg, TargetSettings, curves and blackboard vectors reuse
separately reviewed finite profiles. Framing does not imply runtime ray hits.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineRayCastEffect"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_raycast_effect_native.json"
SECTION_COUNTS = {
    "action": 33,
    "curveRayData": 8,
    "mountPointRayData": 3,
    "pointToPointRayData": 13,
    "raycastData": 6,
}
NESTED_FIELDS = {
    ("action", 6): ("curveRayData", "curveRayData"),
    ("action", 13): ("mountPointRayData", "mountPointRayData"),
    ("action", 15): ("pointToPointRayData", "pointToPointRayData"),
    ("action", 16): ("raycastDataList", "raycastDataList"),
    ("action", 17): ("rayEffect", "effectConfiguration"),
    ("action", 18): ("rayHitEffect", "effectConfiguration"),
    ("action", 23): ("sourceSettings", "targetSettings"),
    ("action", 28): ("targetSettings", "targetSettings"),
    ("curveRayData", 1): ("progressCurve", "animationCurve"),
    ("curveRayData", 5): ("xCurve", "animationCurve"),
    ("curveRayData", 6): ("yCurve", "animationCurve"),
    ("curveRayData", 7): ("zCurve", "animationCurve"),
    ("pointToPointRayData", 0): ("endPosBB", "blackboardVector3"),
}
PLAIN_KINDS = {
    "bool-byte": 1,
    "scalar32": 4,
    "float32-bits": 4,
    "layer-mask-raw4": 4,
    "audio-id-raw4": 4,
    "vector3-raw12": 12,
}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-raycast-effect-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    sections = contract.get("sections")
    if contract.get("dispatcher", {}).get("unionTag") != 0x0121 or not isinstance(sections, dict) or set(sections) != set(SECTION_COUNTS):
        raise ValueError(f"{LABEL}.contract:source-shape")
    for key, count in SECTION_COUNTS.items():
        section = sections[key]
        reads = section.get("orderedSourceReads")
        if (
            section.get("serializedMemberCount") != count
            or not isinstance(reads, list) or len(reads) != count
            or [row.get("memberIndex") for row in reads] != list(range(count))
        ):
            raise ValueError(f"{LABEL}.contract:{key}:source-shape")
        for index, row in enumerate(reads):
            selected = NESTED_FIELDS.get((key, index))
            kind = row.get("readKind")
            if selected:
                expected_kind = "list-generic" if selected[1] == "raycastDataList" else "nested-generic"
                if row.get("fieldName") != selected[0] or kind != expected_kind:
                    raise ValueError(f"{LABEL}.contract:{key}:nested={index}")
            elif kind not in PLAIN_KINDS and kind != "byte-payload":
                raise ValueError(f"{LABEL}.contract:{key}:kind={index}")
    if sections["action"]["wrapperTypeDefinition"] != contract["dispatcher"]["wrapperTypeDefinition"]:
        raise ValueError(f"{LABEL}.contract:route-wrapper")
    return contract


def _validate_source(image: Any, section: dict[str, Any], *, label: str) -> list[int]:
    methods = [image.validate_method_row(row, label=label) for row in section["methods"]]
    image.check_windows(section["codeWindows"], label=label)
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
    for row in section["nestedContexts"]:
        cell, usage = image.nested_usage_cell(row, label=label)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=label, offset=cell,
        )
        if index != row["methodSpecIndex"]:
            raise ValueError(f"{label}.native:method-spec-index")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=label, offset=address,
        )
        if list(spec) != row["methodSpec"]:
            raise ValueError(f"{label}.native:method-spec-record")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{label}.native:generic-arity")
        argument = instance.arguments[0]
        raw = bytes.fromhex(argument.raw_type_record_hex)
        if raw.hex().upper() != row["argumentRawHex"] or raw[10] != row["typeKind"]:
            raise ValueError(f"{label}.native:generic-type")
        if raw[10] in (0x11, 0x12):
            definition = struct.unpack_from("<Q", raw)[0]
            if definition != row["typeDefinition"] or image.type_name(definition) != row["typeName"]:
                raise ValueError(f"{label}.native:generic-direct-type")
        elif raw[10] == 0x15:
            pointer = struct.unpack_from("<Q", raw)[0]
            carrier_raw = image.pe.bytes_at_va(pointer, 32)
            base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
            base_raw = image.pe.bytes_at_va(base_pointer, 16)
            carrier = generic_type_carrier(
                raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
                type_count=len(image.metadata.types), source=label,
            )
            if carrier != row["classCarrier"] or image.type_name(carrier["baseDefinitionIndex"]) != row["typeName"]:
                raise ValueError(f"{label}.native:generic-list-carrier")
            child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
            child_record = child.as_dict()
            child_record["arguments"] = list(child_record["arguments"])
            if len(child.arguments) != 1 or child_record != row["classInstantiation"]:
                raise ValueError(f"{label}.native:generic-list-instantiation")
            element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
            definition = struct.unpack_from("<Q", element)[0]
            if (
                element.hex().upper() != row["elementRawHex"]
                or element[10] not in (0x11, 0x12)
                or definition != row["elementTypeDefinition"]
                or image.type_name(definition) != row["elementTypeName"]
            ):
                raise ValueError(f"{label}.native:generic-list-element")
        else:
            raise ValueError(f"{label}.native:generic-kind")
    return methods


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate selected dispatcher, five readers and nested profiles."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unityplayer.is_file() or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = {
        key: _validate_source(image, section, label=f"{LABEL}.{key}")
        for key, section in contract["sections"].items()
    }
    for dependency in contract["dependencies"]:
        reviewed = json.loads((CONTRACTS_DIR / dependency["path"]).read_bytes())
        if reviewed.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:dependency-schema={dependency['path']}")
        image.check_windows(reviewed.get("codeWindows", []), label=f"{LABEL}.{dependency['path']}")
        image.check_windows(reviewed.get("dataWindows", []), gate="data-window", label=f"{LABEL}.{dependency['path']}")
    return {
        "status": "validated", "nativeInputs": expected,
        "sourceReadCounts": {key: len(section["orderedSourceReads"]) for key, section in contract["sections"].items()},
        "methodIndices": methods,
    }


def _record(reader: Reader, section_key: str) -> None:
    section = _contract()["sections"][section_key]
    start = reader.pos
    if reader.peek() == 0xFF:
        reader.take(1, f"{section_key}.null-wrapper")
        reader.records.append({"start": start, "end": reader.pos, "kind": section_key})
        return
    reader.header(section["serializedMemberCount"])
    for row in section["orderedSourceReads"]:
        index = row["memberIndex"]
        kind = row["readKind"]
        nested = NESTED_FIELDS.get((section_key, index))
        if nested:
            profile = nested[1]
            if profile == "raycastDataList":
                count_start = reader.pos
                count = reader.count(1, nullable=True)
                for _ in range(max(0, count)):
                    _record(reader, "raycastData")
                reader.records.append({"start": count_start, "end": reader.pos, "kind": "raycastDataList", "count": count})
            elif profile in SECTION_COUNTS:
                _record(reader, profile)
            elif profile == "effectConfiguration":
                reader.effect_configuration_profile()
            elif profile == "targetSettings":
                reader.target_profile()
            elif profile == "animationCurve":
                reader.curve_profile()
            else:
                reader.vector_payload()
        elif kind == "byte-payload":
            reader.byte_payload()
        else:
            reader.take(PLAIN_KINDS[kind], f"{section_key}.{kind}")
    reader.records.append({"start": start, "end": reader.pos, "kind": section_key})


def decode_raycast_effect_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite selected 0x0121 action and its nested records."""
    del depth
    contract = _contract()
    if tag != contract["dispatcher"]["unionTag"] or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    _record(reader, "action")
