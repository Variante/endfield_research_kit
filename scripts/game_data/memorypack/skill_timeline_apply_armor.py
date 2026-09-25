"""Selected-build SkillData ApplyArmor action 0x0013 storage framing.

The selected five-member source path reads a byte, three four-byte slots and
one TargetSettings child. Stored fields do not establish armor behavior.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineApplyArmor"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_apply_armor_native.json"
TAG = 0x0013
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_ApplyArmor_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.ApplyArmor+Data"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex", "applyTo",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "target-profile",
)
SOURCE_READ_ORDER = ("byte", "scalar32", "scalar32", "scalar32", "target")
NESTED_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "Beyond.Gameplay.Core.TargetSettings",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-apply-armor-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 4]
        or tuple(row.get("typeName") for row in contexts) != NESTED_TYPES
        or [row[1:] for row in contract.get("setterMethods", ())]
        != [["set___applyTo__", NESTED_TYPES[1]]]
        or contract.get("sourceContract") != "buff_26_native.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xfe\x05"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _contract()
    source = json.loads((CONTRACTS_DIR / contract["sourceContract"]).read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    if (
        source.get("schemaVersion") != 1
        or tuple(source.get("anonymousReadOrder", {}).get("member5", ())) != SOURCE_READ_ORDER
        or tuple(row.get("typeName") for row in source.get("nestedContexts", ())) != NESTED_TYPES
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("wrappedType") != TYPE_NAME
        or route.get("wrapperName") != WRAPPER_NAME
        or route.get("memberCount") != len(FIELD_NAMES)
        or switch.get("entryCount") != len(catalog["families"]["AbilityActionData"])
        or switch.get("base")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    for own, existing in zip(contract["genericContexts"], source["nestedContexts"]):
        for key in ("usageRawHex", "methodSpecIndex", "methodSpec", "argumentRawHex", "typeName", "typeDefinition"):
            if own.get(key) != existing.get(key):
                raise ValueError(f"{LABEL}.contract:generic-dependency:{key}")
    return source, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected route, five source reads and generic child types."""
    contract = _contract()
    source, catalog = _dependencies()
    expected = contract["nativeInputs"]
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-inputs")
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
    if (
        int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    start = contract["codeWindows"][0]["startRva"]
    end = contract["codeWindows"][0]["endRva"]
    previous = -1
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if not start <= rva < end or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if target != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    for context in contract["genericContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index={context['memberIndex']}")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        if list(spec) != context["methodSpec"]:
            raise ValueError(f"{LABEL}.native:method-spec-record={index}")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity={index}")
        raw = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        if (
            raw.hex().upper() != context["argumentRawHex"]
            or struct.unpack_from("<Q", raw)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type={index}")
    source_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["sourceContract"],
    )
    if (
        tuple(source_audit["anonymousReadOrder"].get("member5", ())) != SOURCE_READ_ORDER
        or tuple(row["typeName"] for row in source_audit["nestedContexts"]) != NESTED_TYPES
    ):
        raise ValueError(f"{LABEL}.native:source-profile")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
        "nestedContextCount": len(contract["genericContexts"]),
    }


def decode_apply_armor_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite selected action and its bounded TargetSettings child."""
    del depth
    _contract()
    _dependencies()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, "ApplyArmor.bool-byte")
    for _ in range(3):
        reader.take(4, "ApplyArmor.scalar32")
    reader.target_profile()
