"""Selected-build SkillData ChannelingActionV2 0x0030 storage framing.

The stored ten-member source profile has no proved runtime channeling effect.
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


LABEL = "skillTimelineChannelingV2"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_channeling_v2_native.json"
TAG = 0x0030
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_ChannelingActionV2_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.ChannelingActionV2+Data"
FIELDS = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "actionOnTick", "executeEachFrame", "maxCountPerTarget", "targetSettings",
    "targetTriggerInterval", "triggerInterval",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "sequence", "bool-byte",
    "scalar32", "target-profile", "float32-bits", "float32-bits",
)
NESTED_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "Beyond.Gameplay.Core.SequenceActionData",
    "Beyond.Gameplay.Core.TargetSettings",
)
MATCHING_READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "sequence", "byte",
    "scalar32", "target-profile", "raw4", "raw4",
)
DEPENDENCIES = (
    "buff_2f_native.json", "buff_ec_native.json", "buff_b2_native.json",
    "buff_24_native.json",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-channeling-v2-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    setters = contract.get("setterMethods")
    calls = contract.get("setterCallsites")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("wrapper", {}).get("typeName") != WRAPPER_NAME
        or contract.get("wrapper", {}).get("parentTypeName")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
        or contract.get("serializedMemberCount") != len(FIELDS)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELDS)))
        or tuple(row.get("fieldName") for row in reads) != FIELDS
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 4, 7]
        or tuple(row.get("typeName") for row in contexts) != NESTED_TYPES
        or not isinstance(setters, list)
        or [row[1] for row in setters]
        != [f"set___{field}__" for field in FIELDS[4:]]
        or not isinstance(calls, list)
        or [row.get("memberIndex") for row in calls] != list(range(4, 10))
        or [row.get("methodIndex") for row in calls] != [row[0] for row in setters]
        or [row.get("path") for row in contract.get("dependencies", ())] != list(DEPENDENCIES)
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xfe\x0a"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contract = _contract()
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    rows = catalog.get("families", {}).get("AbilityActionData", ())
    route = rows[TAG] if len(rows) > TAG else {}
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    reviewed = [json.loads((CONTRACTS_DIR / path).read_bytes()) for path in DEPENDENCIES]
    sibling = reviewed[0]
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("wrappedType") != TYPE_NAME
        or route.get("wrapperName") != WRAPPER_NAME
        or route.get("memberCount") != len(FIELDS)
        or switch.get("entryCount") != len(rows)
        or switch.get("base")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
        or sibling.get("schemaVersion") != 1
        or tuple(sibling.get("anonymousReadOrder", {}).get("member10", ())) != MATCHING_READ_ORDER
        or [row.get("typeName") for row in sibling.get("nestedContexts", ())] != list(NESTED_TYPES)
        or any(row.get("schemaVersion") != 1 for row in reviewed[1:])
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    for own, other in zip(contract["genericContexts"], sibling["nestedContexts"]):
        if (
            own["methodSpecIndex"] != other["methodSpecIndex"]
            or own["methodSpec"] != other["methodSpec"]
            or own["argumentRawHex"] != other["argumentRawHex"]
            or own["typeDefinition"] != other["typeDefinition"]
        ):
            raise ValueError(f"{LABEL}.contract:nested-context")
    return catalog, reviewed


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected route, ten reads, six setters and nested types."""
    contract = _contract()
    catalog, dependencies = _dependencies()
    expected = contract["nativeInputs"]
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-inputs")
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
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
    if (
        int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    owner = image.check_wrapper_inheritance(contract["wrapper"], label=LABEL)
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_instruction_windows(
        [[contract["memberCountInstruction"]["rva"], contract["memberCountInstruction"]["hex"]]],
        label=LABEL,
    )
    for path, dependency in zip(DEPENDENCIES, dependencies):
        image.check_windows(dependency["codeWindows"], label=f"{LABEL}.{path}")
    reader_window = contract["codeWindows"][1]
    reads = contract["orderedSourceReads"]
    last = reader_window["startRva"]
    for row in reads:
        rva = row["sourceCallsiteRva"]
        if not last < rva < reader_window["endRva"]:
            raise ValueError(f"{LABEL}.native:source-order")
        last = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != row["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != row["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    for row in contract["setterCallsites"]:
        member = row["memberIndex"]
        rva = row["callsiteRva"]
        if not reads[member]["sourceCallsiteRva"] < rva < (
            reads[member + 1]["sourceCallsiteRva"] if member + 1 < len(reads)
            else reader_window["endRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter-order={member}")
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != row["callHex"]:
            raise ValueError(f"{LABEL}.native:setter-call={rva:#x}")
        method = image.metadata.methods[row["methodIndex"]]
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if target != row["targetRva"] or image.method_pointer_va(method) != image.pe.image_base + target:
            raise ValueError(f"{LABEL}.native:setter-target={member}")
    for row in contract["genericContexts"]:
        cell, usage = image.nested_usage_cell(row, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
        )
        if index != row["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index={row['memberIndex']}")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        if list(spec) != row["methodSpec"]:
            raise ValueError(f"{LABEL}.native:method-spec-record={index}")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity={index}")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        definition = struct.unpack_from("<Q", argument)[0]
        if (
            argument.hex().upper() != row["argumentRawHex"]
            or argument[10] != row["typeKind"]
            or definition != row["typeDefinition"]
            or image.type_name(definition) != row["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type={index}")
    return {
        "status": "validated", "nativeInputs": expected, "methodIndices": methods,
        "sourceReadCount": len(reads), "genericContextCount": len(contract["genericContexts"]),
    }


def decode_channeling_v2_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite ten-member action with nested sequence and target."""
    _contract()
    _dependencies()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, "ChannelingActionV2.isEnable.byte")
    for field in FIELDS[1:4]:
        reader.take(4, f"ChannelingActionV2.{field}.raw4")
    reader.sequence(depth)
    reader.take(1, "ChannelingActionV2.executeEachFrame.byte")
    reader.take(4, "ChannelingActionV2.maxCountPerTarget.raw4")
    reader.target_profile()
    for field in FIELDS[8:]:
        reader.take(4, f"ChannelingActionV2.{field}.float32-bits")
