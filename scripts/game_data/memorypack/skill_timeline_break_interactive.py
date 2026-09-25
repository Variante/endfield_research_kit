"""Selected-build SkillData BreakInteractiveAction 0x0001 reader.

The reviewed source also pins nested InteractiveShapeFinder tag 9. Stored
fields and finite framing do not establish runtime break behavior.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index, unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineBreakInteractive"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_break_interactive_native.json"
ACTION_FIELDS = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "atkCalculation", "attacker", "damageProcessors", "damageType",
    "targetInteractives",
)
ACTION_KINDS = (
    "bool-byte", "scalar32", "scalar32", "scalar32", "calculation-profile",
    "scalar32", "damage-processor-list", "scalar32", "target-profile",
)
FINDER_FIELDS = (
    "autoSetTargetFaction", "checkAlive", "containsUnMarkable",
    "factionTarget", "targetFactionType", "angle", "angleKey", "limitAngle",
    "limitHeight", "maxHeight", "shapeData", "checkIntUnSelectableTag",
)
FINDER_KINDS = (
    "bool-byte", "bool-byte", "bool-byte", "scalar32", "scalar32",
    "float32-bits", "byte-payload", "bool-byte", "bool-byte",
    "float32-bits", "collider-shape-profile", "bool-byte",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-break-interactive-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    finder = contract.get("finder9", {})
    def reads_match(rows: Any, fields: tuple[str, ...], kinds: tuple[str, ...]) -> bool:
        return (
            isinstance(rows, list) and len(rows) == len(fields)
            and [row.get("memberIndex") for row in rows] == list(range(len(fields)))
            and tuple(row.get("fieldName") for row in rows) == fields
            and tuple(row.get("readKind") for row in rows) == kinds
        )
    if (
        contract.get("dispatcher", {}).get("unionTag") != 1
        or contract.get("serializedMemberCount") != len(ACTION_FIELDS)
        or not reads_match(contract.get("orderedSourceReads"), ACTION_FIELDS, ACTION_KINDS)
        or finder.get("dispatcher", {}).get("unionTag") != 9
        or finder.get("serializedMemberCount") != len(FINDER_FIELDS)
        or not reads_match(finder.get("orderedSourceReads"), FINDER_FIELDS, FINDER_KINDS)
        or [row.get("memberIndex") for row in contract.get("nestedContexts", [])] != [4, 6, 8]
        or [row.get("typeName") for row in contract["nestedContexts"]]
        != ["Beyond.Gameplay.Core.CalculationBase", "System.Collections.Generic.List`1", "Beyond.Gameplay.Core.TargetSettings"]
        or contract["nestedContexts"][1].get("elementTypeName") != "Beyond.Gameplay.Core.DamageProcessorBase"
        or [row.get("memberIndex") for row in finder.get("nestedContexts", [])] != [10]
        or finder["nestedContexts"][0].get("typeName") != "Beyond.Gameplay.ColliderShapeData"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def _validate_source(image: Any, section: dict[str, Any], *, label: str) -> list[int]:
    methods = [image.validate_method_row(row, label=label) for row in section["methods"]]
    image.check_windows(section["codeWindows"], label=label)
    instruction = section["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=label)
    owner = image.metadata.types[section["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=label) != section["setterMethods"]:
        raise ValueError(f"{label}.native:setter-order")
    previous = -1
    for row in section["orderedSourceReads"]:
        rva = row["sourceCallsiteRva"]
        if rva <= previous:
            raise ValueError(f"{label}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != row["sourceCallHex"]:
            raise ValueError(f"{label}.native:source-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if target != row["sourceTargetRva"]:
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


def _validate_finder_dispatch(image: Any, dispatcher: dict[str, Any]) -> None:
    entry = dispatcher["entryRva"]
    if entry != dispatcher["tableStartRva"] + dispatcher["unionTag"] * 4:
        raise ValueError(f"{LABEL}.native:finder-entry")
    raw = image.pe.bytes_at_va(image.pe.image_base + entry, 4)
    if raw.hex().upper() != dispatcher["entryHex"] or struct.unpack("<I", raw)[0] != dispatcher["targetRva"]:
        raise ValueError(f"{LABEL}.native:finder-route")
    image.check_windows([dispatcher["routeWindow"]], label=LABEL)
    load_rva = dispatcher["typeLoadRva"]
    load = image.pe.bytes_at_va(image.pe.image_base + load_rva, 7)
    if load.hex().upper() != dispatcher["typeLoadHex"] or load[:3] != b"\x48\x8b\x15":
        raise ValueError(f"{LABEL}.native:finder-type-load")
    cell = image.pe.image_base + load_rva + 7 + struct.unpack_from("<i", load, 3)[0]
    if cell - image.pe.image_base != dispatcher["usageCellRva"]:
        raise ValueError(f"{LABEL}.native:finder-type-cell")
    usage = image.pe.bytes_at_va(cell, 8)
    if usage.hex().upper() != dispatcher["usageRawHex"]:
        raise ValueError(f"{LABEL}.native:finder-type-usage")
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1, source=LABEL, offset=cell,
    )
    slot = int(image.registration["types"], 16) + index * 8
    if index != dispatcher["registeredTypeIndex"] or slot != dispatcher["typeSlotVa"]:
        raise ValueError(f"{LABEL}.native:finder-registered-type")
    pointer = struct.unpack("<Q", image.pe.bytes_at_va(slot, 8))[0]
    type_raw = image.pe.bytes_at_va(pointer, 16)
    definition = struct.unpack_from("<Q", type_raw)[0]
    if (
        pointer != dispatcher["typePointerVa"]
        or type_raw.hex().upper() != dispatcher["typeRawHex"]
        or definition != dispatcher["wrapperTypeDefinition"]
        or image.type_name(definition) != dispatcher["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:finder-wrapper")


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate both selected union readers and their dependencies."""
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
    action_methods = _validate_source(image, contract, label=LABEL)
    _validate_finder_dispatch(image, contract["finder9"]["dispatcher"])
    finder_methods = _validate_source(image, contract["finder9"], label=f"{LABEL}.finder9")
    for dependency in contract["dependencies"]:
        reviewed = json.loads((CONTRACTS_DIR / dependency["path"]).read_bytes())
        if reviewed.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:dependency-schema={dependency['path']}")
        image.check_windows(reviewed.get("codeWindows", []), label=f"{LABEL}.{dependency['path']}")
        image.check_windows(reviewed.get("dataWindows", []), gate="data-window", label=f"{LABEL}.{dependency['path']}")
    return {
        "status": "validated", "nativeInputs": expected,
        "actionMethodIndices": action_methods, "finderMethodIndices": finder_methods,
        "actionSourceReadCount": len(ACTION_KINDS), "finderSourceReadCount": len(FINDER_KINDS),
    }


class _TargetWithFinder9(Reader):
    """Reuse the settled TargetSettings parser, admitting one selected finder."""

    def selector_finder_profile(self) -> None:
        lead = self.peek()
        tag = struct.unpack_from("<H", self.data, self.pos + 1)[0] if lead == 0xFA and self.limit - self.pos >= 3 else lead
        if tag != 9:
            super().selector_finder_profile()
            return
        start = self.pos
        selected = self.nested_union_tag((9,), "finder")
        if self.peek() == 0xFF:
            self.take(1, "null-nested-finder-wrapper")
        else:
            self.header(len(FINDER_KINDS))
            for kind in FINDER_KINDS:
                if kind == "bool-byte":
                    self.take(1, "finder9.bool-byte")
                elif kind in ("scalar32", "float32-bits"):
                    self.take(4, f"finder9.{kind}")
                elif kind == "byte-payload":
                    self.byte_payload()
                else:
                    self.collider_shape_profile()
        self.records.append({"start": start, "end": self.pos, "kind": "nested-finder9-profile", "variant": selected})


def _target_profile(reader: Reader) -> None:
    part = _TargetWithFinder9(reader.data, reader.source, reader.limit)
    part.pos = reader.pos
    part.target_depth = reader.target_depth
    part.postprocessor_depth = reader.postprocessor_depth
    part.target_profile()
    reader.pos = part.pos
    reader.target_depth = part.target_depth
    reader.postprocessor_depth = part.postprocessor_depth
    reader.ranges.extend(part.ranges)
    reader.records.extend(part.records)


def decode_break_interactive_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one nine-member action, with finite nested finder 9."""
    del depth
    contract = _contract()
    if tag != contract["dispatcher"]["unionTag"] or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(ACTION_KINDS))
    reader.take(1, "BreakInteractiveAction.bool-byte")
    for _ in range(3):
        reader.take(4, "BreakInteractiveAction.scalar32")
    reader.calculation_profile()
    reader.take(4, "BreakInteractiveAction.scalar32")
    start = reader.pos
    count = reader.count(1, nullable=True)
    for _ in range(max(0, count)):
        reader.damage_processor_profile()
    reader.records.append({"start": start, "end": reader.pos, "kind": "damage-processor-list", "count": count})
    reader.take(4, "BreakInteractiveAction.scalar32")
    _target_profile(reader)
