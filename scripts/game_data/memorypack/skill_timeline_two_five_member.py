"""Selected SkillData five-member action readers with exact native sources.

These routes share four inherited action fields. Their final member is a
TargetSettings object, string, byte, or float. The selected native bodies and
generated setter order prove each stored shape; they do not establish runtime
behavior.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillTimelineFiveMember"
ROUTES = {
    0x0148: {
        "contract": "skill_timeline_set_ability_entity_main_char_native.json",
        "schema": "endfield.skill-timeline-set-ability-entity-main-char-native-contract.v1",
        "type": "Beyond.Gameplay.Core.SetAbilityEntityToMainChar+Data",
        "wrapper": "Beyond.MemoryPack.Beyond_Gameplay_Core_SetAbilityEntityToMainChar_DataForMemoryPack",
        "fields": ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex", "contextKey"),
        "kinds": ("bool-byte", "scalar32", "scalar32", "scalar32", "byte-payload"),
        "planKind": "string",
        "header": b"\x40\x80\xFE\x05",
        "width": 3,
        "setterType": "System.String",
    },
    0x00E6: {
        "contract": "skill_timeline_look_at_native.json",
        "schema": "endfield.skill-timeline-look-at-native-contract.v1",
        "type": "Beyond.Gameplay.Core.LookAtAction+LookAtActionData",
        "wrapper": "Beyond.MemoryPack.Beyond_Gameplay_Core_LookAtAction_LookAtActionDataForMemoryPack",
        "fields": ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex", "targetSettings"),
        "kinds": ("bool-byte", "scalar32", "scalar32", "scalar32", "target-profile"),
        "planKind": "object",
        "header": b"\x80\x7C\x24\x38\x05",
        "width": 1,
        "setterType": "Beyond.Gameplay.Core.TargetSettings",
    },
}

# Format declarations carry no selected-build addresses or hashes. Those are
# reviewed in each route's contract and rechecked against the selected image.
for _tag, _stem, _type, _field, _kind, _setter_type, _header in (
    (0x007F, "check_target_in_screen", "Conditions.CheckTargetInScreen+Data",
     "targetSettings", "target-profile", "Beyond.Gameplay.Core.TargetSettings", b"\x80\x7C\x24\x38\x05"),
    (0x008D, "convert_weakness_to_interruptible", "ConvertWeaknessToInterruptible+Data",
     "converter", "target-profile", "Beyond.Gameplay.Core.TargetSettings", b"\x40\x80\xFE\x05"),
    (0x010B, "patrol_refresh_check_point", "PatrolRefreshCheckPoint+Data",
     "dis", "float32-bits", "System.Single", b"\x40\x80\xFE\x05"),
    (0x0117, "play_normal_dash_anim", "PlayNormalDashAnimAction+Data",
     "isDashBack", "bool-byte", "System.Boolean", b"\x40\x80\xFE\x05"),
    (0x018F, "typhoea_clear_missile", "TyphoeaArcheryClearMissileAction+Data",
     "skipDieDisplay", "bool-byte", "System.Boolean", b"\x80\x7C\x24\x38\x05"),
    (0x0190, "typhoea_get_phantom_pos", "TyphoeaArcheryGetPhantomPosAction+Data",
     "targetGroupKey", "byte-payload", "System.String", b"\x80\x7C\x24\x38\x05"),
):
    _plan_kind, _plan_width, _plan_scalar = {
        "target-profile": ("object", None, None),
        "byte-payload": ("string", None, None),
        "bool-byte": ("fixed", 1, "bool"),
        "float32-bits": ("fixed", 4, "float32"),
    }[_kind]
    ROUTES[_tag] = {
        "contract": f"skill_timeline_{_stem}_native.json",
        "schema": f"endfield.skill-timeline-{_stem.replace('_', '-')}-native-contract.v1",
        "type": "Beyond.Gameplay.Core." + _type,
        "wrapper": "Beyond.MemoryPack.Beyond_Gameplay_Core_" + _type.replace(".", "_").replace("+", "_") + "ForMemoryPack",
        "fields": ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex", _field),
        "kinds": ("bool-byte", "scalar32", "scalar32", "scalar32", _kind),
        "planKind": _plan_kind, "planWidth": _plan_width, "planScalar": _plan_scalar,
        "setterType": _setter_type, "header": _header,
        "width": 3 if _tag >= 0xFA else 1, "setterCall": True,
    }


@lru_cache(maxsize=16)
def _contract(tag: int) -> tuple[dict[str, Any], dict[str, Any]]:
    route = ROUTES.get(tag)
    if route is None:
        raise ValueError(f"{LABEL}.contract:unsupported-tag={tag:#x}")
    contract, _digest = read_reviewed_contract(
        CONTRACTS_DIR / route["contract"], schema=route["schema"],
        status="exact-current-build", label=LABEL,
    )
    catalog = json.loads((CONTRACTS_DIR / "levelscript_union_tags.json").read_bytes())
    family = catalog.get("families", {}).get("AbilityActionData")
    selected = family[tag] if isinstance(family, list) and tag < len(family) else None
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    reads = contract.get("orderedSourceReads")
    windows = contract.get("codeWindows")
    if (
        contract.get("dispatcher", {}).get("unionTag") != tag
        or contract["dispatcher"].get("wrapperName") != route["wrapper"]
        or contract.get("serializedMemberCount") != 5
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or contract.get("memberCountInstruction", {}).get("hex") != route["header"].hex().upper()
        or not isinstance(reads, list) or len(reads) != 5
        or [row.get("memberIndex") for row in reads] != list(range(5))
        or tuple(row.get("fieldName") for row in reads) != route["fields"]
        or tuple(row.get("readKind") for row in reads) != route["kinds"]
        or not isinstance(windows, list) or len(windows) < 2
        or not isinstance(contract.get("methods"), list) or len(contract["methods"]) != 2
        or [row[2] for row in contract["methods"]] != ["Deserialize", "Deserialize"]
        or contract["methods"][0][1] != route["wrapper"]
        or not contract["methods"][1][1].startswith(route["wrapper"] + "+")
        or not isinstance(contract.get("setterMethods"), list)
        or len(contract["setterMethods"]) != 1
        or contract["setterMethods"][0][1] != "set___" + route["fields"][-1] + "__"
        or contract["setterMethods"][0][2]
        != route["setterType"]
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or not isinstance(selected, dict) or selected.get("tag") != tag
        or selected.get("memberCount") != 5
        or selected.get("wrappedType") != route["type"]
        or selected.get("wrapperName") != route["wrapper"]
        or switch.get("entryCount") != len(family)
        or switch.get("base")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape={tag:#x}")
    if route["planKind"] == "object":
        child = contract.get("nestedContext")
        if (
            not isinstance(child, dict) or child.get("memberIndex") != 4
            or child.get("typeName") != "Beyond.Gameplay.Core.TargetSettings"
            or child.get("typeKind") != 0x12
            or contract.get("targetProfileContract") != "buff_ec_native.json"
        ):
            raise ValueError(f"{LABEL}.contract:target-child")
    elif "nestedContext" in contract or "targetProfileContract" in contract:
        raise ValueError(f"{LABEL}.contract:unexpected-child")
    if route.get("setterCall"):
        setter = contract.get("setterCallsite", {})
        if (setter.get("memberIndex") != 4
                or setter.get("methodIndex") != contract["setterMethods"][0][0]
                or contract.get("primitiveReadContract")
                != "skill_timeline_check_hit_collider_options_native.json"):
            raise ValueError(f"{LABEL}.contract:setter-source={tag:#x}")
    return contract, catalog


@lru_cache(maxsize=4)
def _body_index(
    gameassembly: Path, metadata: Path, gameassembly_sha256: str, metadata_sha256: str,
) -> BodyIndex:
    """Reuse one native method index only for the same selected build bytes."""
    del gameassembly_sha256, metadata_sha256
    return BodyIndex(open_native_image(gameassembly, metadata))


def validate_current_native_contract(
    tag: int, *, gameassembly: Path | None = None, metadata: Path | None = None,
) -> dict[str, Any]:
    """Reprove the selected route, whole source and ordered child reads."""
    contract, catalog = _contract(tag)
    route = ROUTES[tag]
    expected = contract["nativeInputs"]
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-inputs={tag:#x}")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    dispatcher = contract["dispatcher"]
    if (
        int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + dispatcher["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table={tag:#x}")
    image.validate_dispatcher(dispatcher, label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    if contract.get("primitiveReadContract"):
        primitive, _ = read_reviewed_contract(
            CONTRACTS_DIR / contract["primitiveReadContract"],
            schema="endfield.skill-timeline-check-hit-collider-options-native-contract.v1",
            status="exact-current-build", label=LABEL,
        )
        if (primitive.get("nativeInputs") != expected
                or [row["sourceTargetRva"] for row in contract["orderedSourceReads"][:4]]
                != [row["sourceTargetRva"] for row in primitive["orderedSourceReads"][:4]]):
            raise ValueError(f"{LABEL}.native:primitive-source-join={tag:#x}")
        image.check_windows(primitive["codeWindows"], label=LABEL)
    image.check_instruction_windows([
        [contract["memberCountInstruction"]["rva"], contract["memberCountInstruction"]["hex"]]
    ], label=LABEL)
    source_ptr = image.method_pointer_va(image.metadata.methods[methods[0]])
    formatter_ptr = image.method_pointer_va(image.metadata.methods[methods[1]])
    source_windows = contract["codeWindows"][:-1]
    formatter_window = contract["codeWindows"][-1]
    extents = image.mapper.pdata_function_extents(image.pe)
    if (
        source_windows[0]["startRva"] != source_ptr - image.pe.image_base
        or source_windows[0]["endRva"] != extents.get(source_ptr, 0) - image.pe.image_base
        or formatter_window["startRva"] != formatter_ptr - image.pe.image_base
        or formatter_window["endRva"] != extents.get(formatter_ptr, 0) - image.pe.image_base
    ):
        raise ValueError(f"{LABEL}.native:method-extents={tag:#x}")
    fragments = _body_index(
        gate.gameassembly, gate.metadata, gate.gameassembly_sha256, gate.metadata_sha256,
    ).chained_fragments.get(source_ptr, ())
    observed_fragments = [
        (start - image.pe.image_base, start + size - image.pe.image_base)
        for start, size in fragments
    ]
    recorded_fragments = [(row["startRva"], row["endRva"]) for row in source_windows[1:]]
    if recorded_fragments != observed_fragments:
        raise ValueError(f"{LABEL}.native:source-fragments={tag:#x}")
    owner = image.metadata.types[dispatcher["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order={tag:#x}")
    header = contract["memberCountInstruction"]["rva"]
    source_ranges = [(row["startRva"], row["endRva"]) for row in source_windows]
    if not any(start <= header < end for start, end in source_ranges):
        raise ValueError(f"{LABEL}.native:header-outside-source={tag:#x}")
    previous = header
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if rva <= previous or not any(start <= rva < end for start, end in source_ranges):
            raise ValueError(f"{LABEL}.native:source-order={tag:#x}:{rva:#x}")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={tag:#x}:{rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={tag:#x}:{rva:#x}")
    reads = contract["orderedSourceReads"]
    if (
        len({reads[index]["sourceTargetRva"] for index in (1, 2, 3)}) != 1
        or reads[0]["sourceTargetRva"] == reads[1]["sourceTargetRva"]
        or reads[4]["sourceTargetRva"] == reads[1]["sourceTargetRva"]
    ):
        raise ValueError(f"{LABEL}.native:read-helper-shape={tag:#x}")
    if route.get("setterCall"):
        setter = contract["setterCallsite"]
        rva = setter["callsiteRva"]
        pointer = image.method_pointer_va(image.metadata.methods[setter["methodIndex"]])
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if (not any(start <= rva < end - 4 for start, end in source_ranges)
                or rva <= reads[4]["sourceCallsiteRva"]
                or raw[0] != 0xE8 or raw.hex().upper() != setter["callHex"]
                or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != setter["targetRva"]
                or pointer - image.pe.image_base != setter["targetRva"]):
            raise ValueError(f"{LABEL}.native:setter-call={tag:#x}")
    if route["planKind"] == "object":
        context = contract["nestedContext"]
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:target-method-spec-index")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:target-generic-arity")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        if (
            list(spec) != context["methodSpec"]
            or argument.hex().upper() != context["argumentRawHex"]
            or argument[10] != context["typeKind"]
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
            or not reads[3]["sourceCallsiteRva"] < context["instructionRva"] < reads[4]["sourceCallsiteRva"]
        ):
            raise ValueError(f"{LABEL}.native:target-generic-type")
        target_profile = json.loads((CONTRACTS_DIR / contract["targetProfileContract"]).read_bytes())
        if target_profile.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:target-profile-schema")
        image.check_windows(target_profile["codeWindows"], label=f"{LABEL}.targetProfile")
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    selected = routes.get(tag, {})
    definition = selected.get("wrapperTypeDefinition")
    wrapper = resolver.wrappers.get(definition) if resolver and isinstance(definition, int) else None
    plan = resolver.plans.get(definition) if resolver and isinstance(definition, int) else None
    expected_plan = (
        ("isEnable", "fixed", 1, "bool"),
        ("priorityLevel", "fixed", 4, "scalar32"),
        ("priorityOffset", "fixed", 4, "scalar32"),
        ("serverActionIndex", "fixed", 4, "scalar32"),
        (route["fields"][-1], route["planKind"], route.get("planWidth"), route.get("planScalar")),
    )
    child = (
        resolver.wrappers.get(plan[-1].ref)
        if resolver and plan and isinstance(plan[-1].ref, int) else None
    )
    if (
        audit.get("status") != "validated"
        or selected.get("status") != "determined"
        or selected.get("wrapperTypeDefinition") != dispatcher["wrapperTypeDefinition"]
        or selected.get("wrapperName") != route["wrapper"]
        or wrapper is None or wrapper.wrapped_type != route["type"]
        or tuple((m.name, m.kind, m.width, m.scalar) for m in plan or ()) != expected_plan
        or (route["planKind"] == "object" and (child is None or child.wrapped_type != "Beyond.Gameplay.Core.TargetSettings"))
    ):
        raise ValueError(f"{LABEL}.native:derived-plan={tag:#x}")
    return {
        "status": "validated", "nativeInputs": expected, "unionTag": tag,
        "methodIndices": methods, "sourceReadCount": 5,
        "sourceFragmentCount": len(fragments),
    }


def decode_five_member_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one selected action and leave later records to the caller."""
    del depth
    route = ROUTES.get(tag)
    if route is None or width != route["width"]:
        raise ValueError(f"{LABEL}.unionTag:unsupported={tag:#x}:{width}")
    _contract(tag)
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(5)
    reader.take(1, "anonymous-bool-byte")
    for _ in range(3):
        reader.take(4, "anonymous-scalar32")
    final_kind = route["kinds"][-1]
    if final_kind == "byte-payload":
        reader.byte_payload()
    elif final_kind == "target-profile":
        reader.target_profile()
    else:
        reader.take(1 if final_kind == "bool-byte" else 4, final_kind)
