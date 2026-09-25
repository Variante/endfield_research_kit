"""Selected-build SkillData ChannelingDamageAction 0x0032 storage framing.

The route adds one float32 slot to the independently reviewed DamageAction
member-eleven source profile. Nested objects retain their existing bounded
readers; stored values do not prove channeling or damage behavior.
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


LABEL = "skillTimelineChannelingDamage"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_channeling_damage_native.json"
TAG = 0x0032
TYPE_NAME = "Beyond.Gameplay.Core.ChannelingDamageAction+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_ChannelingDamageAction_DataForMemoryPack"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "alwaysNext", "attacker", "damageUnits", "effectSource", "hitEnvData",
    "hitEnvironment", "targetSettings", "triggerInterval",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "bool-byte",
    "enum32", "counted-damage-unit", "target-profile",
    "hit-environment-profile", "bool-byte", "target-profile", "float32",
)
PARENT_READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "byte", "scalar32",
    "counted-member33", "target", "member4", "byte", "target",
)
NESTED_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "Beyond.Gameplay.ActionTargetType",
    "System.Collections.Generic.List`1",
    "Beyond.Gameplay.Core.TargetSettings",
    "Beyond.Gameplay.Core.DamageAction+HitEnvData",
    "Beyond.Gameplay.Core.TargetSettings",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-channeling-damage-native-contract.v1",
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
        or [row.get("memberIndex") for row in contexts] != [1, 5, 6, 7, 8, 10]
        or tuple(row.get("typeName") for row in contexts) != NESTED_TYPES
        or [row[1:] for row in contract.get("setterMethods", ())]
        != [["set___triggerInterval__", "System.Single"]]
        or [row.get("path") for row in contract.get("dependencies", ())]
        != ["buff_9a_native.json", "buff_damage_lists_native.json"]
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7c\x24\x38\x0c"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = _contract()
    parent = json.loads((CONTRACTS_DIR / "buff_9a_native.json").read_bytes())
    lists = json.loads((CONTRACTS_DIR / "buff_damage_lists_native.json").read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    parent_list = parent.get("nestedContexts", [])[0]
    own_list = contract["genericContexts"][2]
    if (
        parent.get("schemaVersion") != 1
        or tuple(parent.get("anonymousReadOrder", {}).get("member11", ())) != PARENT_READ_ORDER
        or lists.get("schemaVersion") != 1
        or parent_list.get("methodSpecIndex") != own_list.get("methodSpecIndex")
        or parent_list.get("argumentRawHex") != own_list.get("argumentRawHex")
        or parent_list.get("generic") != own_list.get("generic")
        or parent_list.get("typeDefinition") != own_list.get("typeDefinition")
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
    return parent, lists, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected route, source calls and nested generic arguments."""
    contract = _contract()
    parent, lists, catalog = _dependencies()
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
    image.check_instruction_windows(
        [[contract["memberCountInstruction"]["rva"],
          contract["memberCountInstruction"]["hex"]]], label=LABEL,
    )
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
        if raw.hex().upper() != context["argumentRawHex"]:
            raise ValueError(f"{LABEL}.native:generic-argument={index}")
        if context["memberIndex"] == 6:
            if context["generic"] != parent["nestedContexts"][0]["generic"]:
                raise ValueError(f"{LABEL}.native:damage-unit-list")
        elif (
            struct.unpack_from("<Q", raw)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type={index}")
    parent_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / "buff_9a_native.json",
    )
    if tuple(parent_audit["anonymousReadOrder"].get("member11", ())) != PARENT_READ_ORDER:
        raise ValueError(f"{LABEL}.native:parent-profile")
    image.check_windows(lists["codeWindows"], label=f"{LABEL}.damage-lists")
    return {
        "status": "validated", "nativeInputs": expected, "methodIndices": methods,
        "sourceReadCount": len(contract["orderedSourceReads"]),
        "nestedContextCount": len(contract["genericContexts"]),
    }


def decode_channeling_damage_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one finite selected action and its bounded DamageAction children."""
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
    reader.take(1, "ChannelingDamageAction.bool-byte")
    for _ in range(3):
        reader.take(4, "ChannelingDamageAction.scalar32")
    reader.take(1, "ChannelingDamageAction.bool-byte")
    reader.take(4, "ChannelingDamageAction.enum32")
    count = reader.count(1, reserve=8, nullable=True)
    for _ in range(max(0, count)):
        reader.damage_unit_profile()
    reader.target_profile()
    reader.hit_environment_profile()
    reader.take(1, "ChannelingDamageAction.bool-byte")
    reader.target_profile()
    reader.take(4, "ChannelingDamageAction.float32-bits")
