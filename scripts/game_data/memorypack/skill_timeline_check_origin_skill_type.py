"""Selected-build SkillData CheckOriginSkillType 0x0048 framing.

The existing Buff action reader supplies the finite six-member wire profile.
This module independently authenticates its SkillData union route and direct
source order before it can be admitted by the shared SkillData reader.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineCheckOriginSkillType"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_check_origin_skill_type_native.json"
TAG = 0x0048
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_CheckOriginSkillType_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.CheckOriginSkillType+Data"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "attackTypeMask", "skillTypeList",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "enum32", "counted-scalar32",
)
SOURCE_READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "scalar32", "counted-scalar32",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-check-origin-skill-type-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    setters = contract.get("setterMethods")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(READ_KINDS)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(READ_KINDS)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(setters, list)
        or [row[1] for row in setters] != [
            "set___attackTypeMask__", "set___skillTypeList__",
        ]
        or contract.get("sourceContract") != "buff_48_native.json"
        or contract.get("listElementContract") != "buff_78_native.json"
        or contract.get("listCountLoopContract") != "buff_b4_native.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xfe\x06"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = _contract()
    source = json.loads((CONTRACTS_DIR / contract["sourceContract"]).read_bytes())
    element = json.loads((CONTRACTS_DIR / contract["listElementContract"]).read_bytes())
    loop = json.loads((CONTRACTS_DIR / contract["listCountLoopContract"]).read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    contexts = source.get("nestedContexts")
    element_contexts = element.get("nestedContexts")
    if (
        source.get("schemaVersion") != 1
        or tuple(source.get("anonymousReadOrder", {}).get("member6", ())) != SOURCE_READ_ORDER
        or not isinstance(source.get("methods"), list)
        or len(source["methods"]) != 2
        or source["methods"][1][1] != WRAPPER_NAME
        or source["methods"][1][2] != "Deserialize"
        or not isinstance(contexts, list)
        or [row.get("typeName") for row in contexts] != [
            "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
            "Beyond.Gameplay.Core.Conditions.CheckSkillType+AttackTypeMask",
            "System.Collections.Generic.List`1",
        ]
        or not isinstance(element_contexts, list)
        or len(element_contexts) < 3
        or contexts[2].get("generic", {}).get("elementArguments")
        != element_contexts[1].get("generic", {}).get("elementArguments")
        or element.get("schemaVersion") != 1
        or element_contexts[2].get("typeName") != "Beyond.Gameplay.SkillType"
        or loop.get("schemaVersion") != 1
        or "count/element-loop" not in loop.get("boundary", "")
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
    return source, element, loop, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected route, six source calls and SkillType list witness."""
    contract = _contract()
    source, element, loop, catalog = _dependencies()
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
    methods = [image.validate_method_row(row, label=LABEL) for row in source["methods"]]
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeIndex", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    previous = -1
    source_start = source["codeWindows"][1]["startRva"]
    source_end = source["codeWindows"][1]["endRva"]
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if not source_start <= rva < source_end or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if target != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    source_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["sourceContract"],
    )
    element_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["listElementContract"],
    )
    loop_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["listCountLoopContract"],
    )
    if (
        source_audit["anonymousReadOrder"].get("member6") != list(SOURCE_READ_ORDER)
        or "member9" not in element_audit["anonymousReadOrder"]
        or not loop_audit["codeWindows"]
    ):
        raise ValueError(f"{LABEL}.native:source-profile")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
        "nestedContextCount": len(source["nestedContexts"]),
    }


def decode_check_origin_skill_type_action(
    reader: Reader, depth: int, tag: int, width: int,
) -> None:
    """Consume the finite selected action, preserving nullable list framing."""
    _contract()
    _dependencies()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    Reader._action(reader, depth, tag, width)
